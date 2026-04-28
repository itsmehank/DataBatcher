"""
LLM 호출 wrapper — 재시도 + llm_calls 영구 기록.

헌법 §2.5: 모든 LLM 호출은 llm_calls 테이블에 영구 보존.
brief §7.5: 재시도 정책 (max_retries=2, 총 3회 시도).

책임 범위:
  - backend.call() 호출 (LLMBackend Protocol 사용)
  - 실패 시 재시도
  - 각 시도마다 llm_calls INSERT (이력 보존)
  - daily_call_limits 체크 hook (Phase 1.3에서 채울 placeholder)

책임 밖:
  - 프롬프트 빌드 (prompt_builder, 1.1.10)
  - 응답 파싱 (result_parser, 1.1.11)
  - 비용 임계값 체크 (cost_tracker, 1.3)
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from core.anthropic_client import LLMBackend, LLMResponse
from models.db_models import LlmCall


def _check_daily_call_limit(db_session: Session, module: str) -> bool:
    """
    일일 호출 한도 체크 hook.

    Phase 1.3에서 cost_tracker 모듈의 실제 구현으로 교체.
    인터페이스:
      입력: db_session (Session), module (str)
      출력: bool — True=허용, False=한도 초과
      예외: 발생 안 함
    """
    return True


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

    Returns:
        (LLMResponse, llm_call_id).
        성공·실패 모두 INSERT됨. 실패 시 LLMResponse.error에 메시지.
        daily call limit 초과 시 id=0 반환.

    Raises:
        없음. 모든 예외를 LLMResponse.error에 기록.
    """
    if not _check_daily_call_limit(db_session, module):
        over_limit_response = LLMResponse(
            text="",
            model=model,
            duration_ms=0,
            request_payload={"module": module, "reason": "daily_call_limit_exceeded"},
            error="daily call limit exceeded",
        )
        return over_limit_response, 0

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

        if response.error is None and response.text:
            break

    return last_response, last_id
