"""
llm_call_recorder.py 단위 테스트.

SQLite in-memory DB를 사용해 실제 INSERT 동작을 검증.
LLM 호출 없음 — backend는 MockBackend로 대체.

Phase 1.3.2 갱신: cost_tracker wire-up 후 contract 변경 반영.
  - daily_call_limits hard_stop 시 DailyCallLimitExceeded raise
  - settings 파라미터 추가 (None이면 disk 로드 — 테스트는 명시 dict 전달)
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core.anthropic_client import LLMBackend, LLMResponse
from core.cost_tracker import DailyCallLimitExceeded
from core.llm_call_recorder import call_and_record
from models.db_models import Base, LlmCall


# 한도 미적용 + 자동 트리거 모니터링 hook은 동작 — 테스트는 이 settings로 호출
_TEST_SETTINGS = {"daily_call_limits": {"enabled": False}}


# ── 공통 픽스처 ────────────────────────────────────────────────────────────────

def _make_sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return Session()


def _ok_response(text: str = '{"signal": "ok"}') -> LLMResponse:
    return LLMResponse(
        text=text,
        model="claude-sonnet-4-6",
        prompt_tokens=100,
        completion_tokens=20,
        cost_usd=0.001,
        duration_ms=1000,
        request_payload={"prompt": "...", "token_source": "cli_json"},
        response_payload={"is_error": False},
    )


def _error_response(msg: str = "timeout") -> LLMResponse:
    return LLMResponse(
        text="",
        model="claude-sonnet-4-6",
        duration_ms=500,
        request_payload={"prompt": "..."},
        error=msg,
    )


class MockBackend(LLMBackend):
    """각 call()마다 responses 리스트에서 순서대로 반환."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = iter(responses)
        self.call_count = 0

    def call(self, prompt: str, model: str, max_tokens: int) -> LLMResponse:
        self.call_count += 1
        return next(self._responses)


# ── 테스트 ─────────────────────────────────────────────────────────────────────

def test_success_single_attempt():
    session = _make_sqlite_session()
    backend = MockBackend([_ok_response()])

    response, call_id = call_and_record(
        backend, session, "prompt", "claude-sonnet-4-6", 100, "analysis_5_kr",
        retry_delay_seconds=0, settings=_TEST_SETTINGS,
    )

    assert response.error is None
    assert response.text == '{"signal": "ok"}'
    assert call_id > 0
    assert backend.call_count == 1

    rows = session.query(LlmCall).all()
    assert len(rows) == 1
    assert rows[0].module == "analysis_5_kr"
    assert rows[0].error is None
    session.close()


def test_first_fail_retry_success():
    session = _make_sqlite_session()
    backend = MockBackend([_error_response("network error"), _ok_response()])

    response, call_id = call_and_record(
        backend, session, "prompt", "claude-sonnet-4-6", 100, "analysis_5_kr",
        max_retries=2, retry_delay_seconds=0, settings=_TEST_SETTINGS,
    )

    assert response.error is None
    assert backend.call_count == 2

    rows = session.query(LlmCall).order_by(LlmCall.id).all()
    assert len(rows) == 2
    assert rows[0].error == "network error"
    assert rows[1].error is None
    assert call_id == rows[1].id
    session.close()


def test_all_attempts_fail():
    session = _make_sqlite_session()
    max_retries = 2
    backend = MockBackend([_error_response(f"fail_{i}") for i in range(max_retries + 1)])

    response, call_id = call_and_record(
        backend, session, "prompt", "claude-sonnet-4-6", 100, "analysis_5_kr",
        max_retries=max_retries, retry_delay_seconds=0, settings=_TEST_SETTINGS,
    )

    assert response.error is not None
    assert backend.call_count == max_retries + 1

    rows = session.query(LlmCall).all()
    assert len(rows) == max_retries + 1
    session.close()


def test_empty_text_triggers_retry():
    session = _make_sqlite_session()
    empty_response = LLMResponse(
        text="",
        model="claude-sonnet-4-6",
        duration_ms=300,
        request_payload={},
        error=None,
    )
    backend = MockBackend([empty_response, _ok_response()])

    response, _ = call_and_record(
        backend, session, "prompt", "claude-sonnet-4-6", 100, "analysis_5_kr",
        max_retries=2, retry_delay_seconds=0, settings=_TEST_SETTINGS,
    )

    assert backend.call_count == 2
    assert response.text == '{"signal": "ok"}'
    rows = session.query(LlmCall).all()
    assert len(rows) == 2
    session.close()


def test_daily_call_limit_hard_stop_raises():
    """ADR-012 §3.1 — hard_stop_on_exceed=True + 한도 도달 → DailyCallLimitExceeded raise."""
    from datetime import datetime
    session = _make_sqlite_session()
    # 미리 5건 INSERT (오늘 분으로)
    for _ in range(5):
        session.add(LlmCall(module="analysis_5_us", timestamp=datetime.now(), duration_ms=100, error=None))
    session.commit()

    settings = {"daily_call_limits": {"enabled": True, "us": 5, "hard_stop_on_exceed": True}}
    backend = MockBackend([_ok_response()])

    raised = False
    try:
        call_and_record(
            backend, session, "prompt", "claude-sonnet-4-6", 100, "analysis_5_us",
            retry_delay_seconds=0, settings=settings,
        )
    except DailyCallLimitExceeded as exc:
        raised = True
        assert exc.region == "US"
    assert raised, "DailyCallLimitExceeded not raised"
    # backend.call() 호출 안 됨
    assert backend.call_count == 0
    session.close()


def test_daily_call_limit_soft_warn_proceeds():
    """hard_stop_on_exceed=False + 한도 도달 → 경고만 + 호출 진행."""
    from datetime import datetime
    session = _make_sqlite_session()
    for _ in range(5):
        session.add(LlmCall(module="analysis_5_us", timestamp=datetime.now(), duration_ms=100, error=None))
    session.commit()

    settings = {"daily_call_limits": {"enabled": True, "us": 5, "hard_stop_on_exceed": False}}
    backend = MockBackend([_ok_response()])

    response, call_id = call_and_record(
        backend, session, "prompt", "claude-sonnet-4-6", 100, "analysis_5_us",
        retry_delay_seconds=0, settings=settings,
    )
    assert response.error is None
    assert backend.call_count == 1
    # sync_log에 WARN 기록 확인
    rows = session.execute(text("SELECT status FROM sync_log WHERE job_name='llm_daily_call_limit'")).fetchall()
    assert rows and rows[0][0] == "WARN"
    session.close()


if __name__ == "__main__":
    tests = [
        test_success_single_attempt,
        test_first_fail_retry_success,
        test_all_attempts_fail,
        test_empty_text_triggers_retry,
        test_daily_call_limit_hard_stop_raises,
        test_daily_call_limit_soft_warn_proceeds,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            import traceback
            print(f"  FAIL  {t.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
    if passed != len(tests):
        sys.exit(1)
