"""
cost_tracker 단위 테스트 — Phase 1.3.2.

LLM 호출 없음. SQLite in-memory DB로 llm_calls + sync_log 동작 검증.

검증 범위:
  - check_daily_limit hard_stop=True → DailyCallLimitExceeded raise
  - check_daily_limit hard_stop=False → False 반환 (sync_log WARN 기록)
  - check_daily_limit enabled=False / module suffix 없음 → True (no-op)
  - count_calls_today → 모듈+region 기준 카운트
  - check_terms_violation_signals → 9개 패턴 매치
  - record_sync_log → 1024 truncate 동작
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core.cost_tracker import (
    DailyCallLimitExceeded,
    check_daily_limit,
    check_terms_violation_signals,
    count_calls_today,
    record_sync_log,
)
from models.db_models import Base, LlmCall


def _make_session():
    """SQLite in-memory + 모든 테이블 생성."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _insert_llm_calls(s, *, module: str, count: int, today: date | None = None):
    """오늘 날짜로 N개 llm_calls 삽입."""
    today = today or datetime.now().date()
    for _ in range(count):
        s.add(LlmCall(
            module=module,
            timestamp=datetime.combine(today, datetime.min.time().replace(hour=12)),
            duration_ms=100,
            error=None,
        ))
    s.commit()


# ── count_calls_today ────────────────────────────────────────────────────────

def test_count_calls_today_empty():
    s = _make_session()
    assert count_calls_today(s, "KR") == 0
    assert count_calls_today(s, "US") == 0


def test_count_calls_today_kr_only():
    s = _make_session()
    _insert_llm_calls(s, module="analysis_5_kr", count=3)
    _insert_llm_calls(s, module="entry_params_6_kr", count=2)
    _insert_llm_calls(s, module="analysis_5_us", count=1)
    assert count_calls_today(s, "KR") == 5
    assert count_calls_today(s, "US") == 1


def test_count_calls_today_includes_errors():
    s = _make_session()
    s.add(LlmCall(module="analysis_5_us", timestamp=datetime.now(), duration_ms=120000, error="timeout"))
    s.add(LlmCall(module="analysis_5_us", timestamp=datetime.now(), duration_ms=100, error=None))
    s.commit()
    assert count_calls_today(s, "US") == 2


# ── check_daily_limit ────────────────────────────────────────────────────────

def test_check_daily_limit_disabled_returns_true():
    s = _make_session()
    settings = {"daily_call_limits": {"enabled": False, "us": 50, "hard_stop_on_exceed": True}}
    _insert_llm_calls(s, module="analysis_5_us", count=100)  # 한도 초과지만 disabled
    assert check_daily_limit(s, "analysis_5_us", settings) is True


def test_check_daily_limit_under_limit_returns_true():
    s = _make_session()
    settings = {"daily_call_limits": {"enabled": True, "us": 50, "hard_stop_on_exceed": True}}
    _insert_llm_calls(s, module="analysis_5_us", count=10)
    assert check_daily_limit(s, "analysis_5_us", settings) is True


def test_check_daily_limit_at_limit_hard_stop_raises():
    s = _make_session()
    settings = {"daily_call_limits": {"enabled": True, "us": 5, "hard_stop_on_exceed": True}}
    _insert_llm_calls(s, module="analysis_5_us", count=5)
    raised = False
    try:
        check_daily_limit(s, "analysis_5_us", settings)
    except DailyCallLimitExceeded as exc:
        raised = True
        assert exc.region == "US"
        assert exc.used == 5
        assert exc.limit == 5
    assert raised, "DailyCallLimitExceeded not raised"
    # sync_log에 ERROR 기록 확인
    rows = s.execute(text("SELECT job_name, status, message FROM sync_log")).fetchall()
    assert any(r[0] == "llm_daily_call_limit" and r[1] == "ERROR" for r in rows)


def test_check_daily_limit_at_limit_soft_warn_returns_false():
    s = _make_session()
    settings = {"daily_call_limits": {"enabled": True, "us": 5, "hard_stop_on_exceed": False}}
    _insert_llm_calls(s, module="analysis_5_us", count=5)
    result = check_daily_limit(s, "analysis_5_us", settings)
    assert result is False
    rows = s.execute(text("SELECT status FROM sync_log WHERE job_name='llm_daily_call_limit'")).fetchall()
    assert rows and rows[0][0] == "WARN"


def test_check_daily_limit_module_no_region_suffix_returns_true():
    """module이 _kr / _us 접미사 없으면 한도 미적용 (예: agent_8)."""
    s = _make_session()
    settings = {"daily_call_limits": {"enabled": True, "kr": 1, "us": 1, "hard_stop_on_exceed": True}}
    assert check_daily_limit(s, "agent_8", settings) is True


def test_check_daily_limit_zero_limit_returns_true():
    """limit=0이면 한도 미적용 (소프트 disable)."""
    s = _make_session()
    settings = {"daily_call_limits": {"enabled": True, "kr": 0, "us": 50, "hard_stop_on_exceed": True}}
    _insert_llm_calls(s, module="analysis_5_kr", count=100)
    assert check_daily_limit(s, "analysis_5_kr", settings) is True


# ── check_terms_violation_signals ───────────────────────────────────────────

def test_terms_violation_empty_input():
    assert check_terms_violation_signals(None) == []
    assert check_terms_violation_signals("") == []
    assert check_terms_violation_signals("normal LLM response") == []


def test_terms_violation_rate_limit_pattern():
    signals = check_terms_violation_signals("Error: rate limit exceeded for the day")
    assert "rate_limit" in signals


def test_terms_violation_5h_window_pattern():
    signals = check_terms_violation_signals("You have hit the 5-hour window limit")
    assert "5h_window_warning" in signals


def test_terms_violation_account_warning():
    signals = check_terms_violation_signals("Your account has been suspended due to terms of service violation")
    # both account_warning and tos_warning should match (regex requires lowercase 'terms of service')
    assert "account_warning" in signals
    assert "tos_warning" in signals


def test_terms_violation_max_plan_limit():
    signals = check_terms_violation_signals("You have reached the Max plan limit for this period")
    assert "max_plan_limit" in signals


def test_terms_violation_no_duplicates():
    """같은 패턴 여러 번 매치 시 코드는 한 번만 emit."""
    signals = check_terms_violation_signals("rate limit and rate-limit again")
    assert signals.count("rate_limit") == 1


# ── record_sync_log ─────────────────────────────────────────────────────────

def test_record_sync_log_basic():
    s = _make_session()
    sid = record_sync_log(
        s, job_name="llm_test", market="US",
        status="WARN", message="hello world",
    )
    assert isinstance(sid, int) and sid > 0
    row = s.execute(text("SELECT job_name, market, status, message FROM sync_log WHERE id=:i"),
                    {"i": sid}).fetchone()
    assert row[0] == "llm_test" and row[1] == "US" and row[2] == "WARN"
    assert row[3] == "hello world"


def test_record_sync_log_message_truncation():
    s = _make_session()
    long_msg = "x" * 2000
    sid = record_sync_log(
        s, job_name="llm_test", market="US",
        status="WARN", message=long_msg,
    )
    row = s.execute(text("SELECT message FROM sync_log WHERE id=:i"), {"i": sid}).fetchone()
    assert len(row[0]) == 1024


# ── 메인 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import inspect

    test_funcs = [
        (name, obj) for name, obj in inspect.getmembers(sys.modules[__name__])
        if inspect.isfunction(obj) and name.startswith("test_")
    ]

    passed = 0
    failed = []
    for name, fn in test_funcs:
        try:
            fn()
            print(f"  ok  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
            import traceback as tb
            tb.print_exc()
            failed.append((name, e))

    total = len(test_funcs)
    print(f"\n{'OK' if not failed else 'FAILED'}: {passed}/{total} passed")
    if failed:
        sys.exit(1)
