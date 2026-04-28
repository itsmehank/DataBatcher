"""
llm_call_recorder.py 단위 테스트.

SQLite in-memory DB를 사용해 실제 INSERT 동작을 검증.
LLM 호출 없음 — backend는 MockBackend로 대체.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core.anthropic_client import LLMBackend, LLMResponse
from core.llm_call_recorder import _check_daily_call_limit, call_and_record
from models.db_models import Base, LlmCall


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
    """성공 1회: INSERT 1건, 반환 id가 양수."""
    session = _make_sqlite_session()
    backend = MockBackend([_ok_response()])

    response, call_id = call_and_record(
        backend, session, "prompt", "claude-sonnet-4-6", 100, "analysis_5_kr",
        retry_delay_seconds=0,
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
    """첫 시도 실패 + 재시도 성공: INSERT 2건, 반환은 두 번째 응답."""
    session = _make_sqlite_session()
    backend = MockBackend([_error_response("network error"), _ok_response()])

    response, call_id = call_and_record(
        backend, session, "prompt", "claude-sonnet-4-6", 100, "analysis_5_kr",
        max_retries=2, retry_delay_seconds=0,
    )

    assert response.error is None
    assert backend.call_count == 2

    rows = session.query(LlmCall).order_by(LlmCall.id).all()
    assert len(rows) == 2
    assert rows[0].error == "network error"   # 첫 시도 실패 기록
    assert rows[1].error is None              # 재시도 성공 기록
    assert call_id == rows[1].id
    session.close()


def test_all_attempts_fail():
    """모든 시도 실패: max_retries+1 건 INSERT, response.error != None."""
    session = _make_sqlite_session()
    max_retries = 2
    backend = MockBackend([_error_response(f"fail_{i}") for i in range(max_retries + 1)])

    response, call_id = call_and_record(
        backend, session, "prompt", "claude-sonnet-4-6", 100, "analysis_5_kr",
        max_retries=max_retries, retry_delay_seconds=0,
    )

    assert response.error is not None
    assert backend.call_count == max_retries + 1

    rows = session.query(LlmCall).all()
    assert len(rows) == max_retries + 1
    session.close()


def test_empty_text_triggers_retry():
    """text=="" + error=None → 재시도 발생."""
    session = _make_sqlite_session()
    empty_response = LLMResponse(
        text="",
        model="claude-sonnet-4-6",
        duration_ms=300,
        request_payload={},
        error=None,          # 에러 없음, 빈 text
    )
    backend = MockBackend([empty_response, _ok_response()])

    response, _ = call_and_record(
        backend, session, "prompt", "claude-sonnet-4-6", 100, "analysis_5_kr",
        max_retries=2, retry_delay_seconds=0,
    )

    assert backend.call_count == 2
    assert response.text == '{"signal": "ok"}'
    rows = session.query(LlmCall).all()
    assert len(rows) == 2
    session.close()


def test_daily_call_limit_exceeded():
    """daily_call_limits hook False: INSERT 0건, error 메시지 반환."""
    from unittest.mock import patch

    session = _make_sqlite_session()
    backend = MockBackend([_ok_response()])

    with patch("core.llm_call_recorder._check_daily_call_limit", return_value=False):
        response, call_id = call_and_record(
            backend, session, "prompt", "claude-sonnet-4-6", 100, "analysis_5_kr",
            retry_delay_seconds=0,
        )

    assert response.error == "daily call limit exceeded"
    assert call_id == 0
    assert backend.call_count == 0

    rows = session.query(LlmCall).all()
    assert len(rows) == 0
    session.close()


if __name__ == "__main__":
    tests = [
        test_success_single_attempt,
        test_first_fail_retry_success,
        test_all_attempts_fail,
        test_empty_text_triggers_retry,
        test_daily_call_limit_exceeded,
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
