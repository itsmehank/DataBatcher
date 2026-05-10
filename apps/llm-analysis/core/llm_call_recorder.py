"""
LLM 호출 wrapper — 재시도 + llm_calls 영구 기록 + 모니터링 hook.

헌법 §2.5: 모든 LLM 호출은 llm_calls 테이블에 영구 보존.
brief §7.5: 재시도 정책 (max_retries=2, 총 3회 시도).

책임 범위:
  - backend.call() 호출 (LLMBackend Protocol 사용)
  - 실패 시 재시도
  - 각 시도마다 llm_calls INSERT (이력 보존)
  - 호출 전: cost_tracker.check_daily_limit (ADR-012 §3.1, hard_stop 시 raise)
  - 호출 후: 토큰 폭증 감지 (1.1.7 후속, ADR-012 §3.2) + 약관 위반 징후 감지 (ADR-012 §3.3)

책임 밖:
  - 프롬프트 빌드 (prompt_builder)
  - 응답 파싱 (result_parser)
  - 비용 임계값 (cost_alerts) — 별도 점검 도구
"""
from __future__ import annotations

import time
from typing import Optional

from sqlalchemy.orm import Session

from core.anthropic_client import LLMBackend, LLMResponse
from core.cost_tracker import (
    DailyCallLimitExceeded,
    check_daily_limit,
    check_terms_violation_signals,
    record_sync_log,
    record_terms_violation_signal,
    _module_to_region,
)
from models.db_models import LlmCall


# 토큰 폭증 감지 임계값: settings.input_data 추정의 N배 (1.1.7 후속).
# input_data 추정이 8,000~12,000이라 2배 = 24,000으로 잡으면 정상 운영을 거의
# 막지 않으면서 CLAUDE.md auto-load 같은 사고 (66,873)는 catch.
_TOKEN_SPIKE_THRESHOLD: int = 24_000


def _post_call_monitoring(
    db_session: Session,
    response: LLMResponse,
    module: str,
) -> None:
    """
    호출 후 모니터링 hook — sync_log WARN 기록 path 두 가지 (idempotent).

    1) 토큰 폭증 (prompt_tokens > _TOKEN_SPIKE_THRESHOLD)
    2) 약관 위반 징후 (response.text 또는 response.error 패턴 매치)
    """
    region = _module_to_region(module) or "BOTH"

    # 1) 토큰 폭증
    if response.prompt_tokens and response.prompt_tokens > _TOKEN_SPIKE_THRESHOLD:
        try:
            record_sync_log(
                db_session,
                job_name="llm_token_spike",
                market=region,
                status="WARN",
                message=(
                    f"prompt_tokens={response.prompt_tokens} > threshold={_TOKEN_SPIKE_THRESHOLD} "
                    f"(module={module}); investigate prompt size"
                ),
            )
        except Exception:
            # 모니터링 실패가 본 호출 결과를 가리지 않게 swallow
            pass

    # 2) 약관 위반 징후 — response.text + response.error 양쪽 검사
    for source_label, blob in (
        ("cli_response_text", response.text),
        ("cli_error_message", response.error),
    ):
        try:
            signals = check_terms_violation_signals(blob)
            if signals:
                record_terms_violation_signal(
                    db_session,
                    region=region,
                    signals=signals,
                    source=source_label,
                    snippet=(blob[:400] if blob else None),
                )
        except Exception:
            pass


def call_and_record(
    backend: LLMBackend,
    db_session: Session,
    prompt: str,
    model: str,
    max_tokens: int,
    module: str,
    *,
    max_retries: int = 2,
    retry_delay_seconds: float = 1.0,
    settings: Optional[dict] = None,
) -> tuple[LLMResponse, int]:
    """
    Backend를 호출하고 결과를 llm_calls 테이블에 영구 보존한다.

    Args:
        backend:              LLMBackend 구현체 (CLI 또는 API).
        db_session:           SQLAlchemy Session (호출자가 생명주기 관리).
        prompt:               완성된 프롬프트 텍스트.
        model:                모델 식별자.
        max_tokens:           최대 출력 토큰.
        module:               llm_calls.module 값 (예: "analysis_5_kr").
        max_retries:          재시도 최대 횟수 (기본 2 = 총 3회 시도).
        retry_delay_seconds:  재시도 사이 대기 시간(초).
        settings:             settings.yaml 내용. None이면 자동 로드. cost_tracker
                              .check_daily_limit + 모니터링이 사용.

    Returns:
        (LLMResponse, llm_call_id).
        성공·실패 모두 INSERT됨. 실패 시 LLMResponse.error에 메시지.

    Raises:
        DailyCallLimitExceeded — settings.daily_call_limits.hard_stop_on_exceed=true
        + 한도 도달 시. 호출자(run_daily_analysis)가 catch하고 종료.
    """
    if settings is None:
        from core.config import load_settings
        settings = load_settings()

    # ADR-012 §3.1 — 호출 직전 일일 상한 체크
    check_daily_limit(db_session, module, settings)
    # check_daily_limit은 정상 시 True, soft warning 시 False, hard_stop 시 raise.
    # False여도 본 호출은 진행 (soft warning은 sync_log에만 기록).

    last_response: LLMResponse = LLMResponse(
        text="", model=model, duration_ms=0, request_payload={},
        error="call_and_record: no attempt executed",
    )
    last_id: int = 0

    total_attempts = max_retries + 1
    for attempt in range(total_attempts):
        if attempt > 0:
            time.sleep(retry_delay_seconds)

        try:
            response = backend.call(prompt=prompt, model=model, max_tokens=max_tokens)
        except Exception as exc:
            response = LLMResponse(
                text="",
                model=model,
                duration_ms=0,
                request_payload={"prompt": prompt, "model": model},
                error=f"backend.call() raised: {exc}",
            )

        record = LlmCall(
            module=module,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            cost_usd=float(response.cost_usd) if response.cost_usd is not None else None,
            request_payload=response.request_payload,
            response_payload=response.response_payload,
            duration_ms=response.duration_ms,
            error=response.error,
        )
        db_session.add(record)
        db_session.flush()
        db_session.commit()
        last_id = record.id
        last_response = response

        # 모니터링 hook (각 시도 후, idempotent)
        _post_call_monitoring(db_session, response, module)

        if response.error is None and response.text:
            break

    return last_response, last_id
