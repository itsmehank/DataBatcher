"""
일일 호출 수·비용 집계 + 일일 상한 + 모니터링 4종.

ADR-012 §3:
  §3.1 daily_call_limits.hard_stop_on_exceed=true 강제 (자동 트리거 환경)
  §3.2 sync_log에 WARN/ERROR 기록
  §3.3 약관 위반 징후 감지 (CLI 백엔드 경고 패턴)
  §3.4 호출 로그 주간 점검 (별도 스크립트)

본 모듈은 Phase 1.3.2에서 구현. llm_call_recorder.call_and_record가 호출 전
check_daily_limit을 invoke하고, 한도 초과 시 DailyCallLimitExceeded raise.
run_daily_analysis가 catch → sync_log WARN + 즉시 종료.
"""
from __future__ import annotations

import re
from datetime import date as _date_t, datetime, timedelta
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session


# ── Exceptions ───────────────────────────────────────────────────────────────

class DailyCallLimitExceeded(Exception):
    """ADR-012 §3.1 — 일일 호출 한도 초과. hard_stop_on_exceed=true 시 raise."""

    def __init__(self, region: str, used: int, limit: int):
        self.region = region
        self.used = used
        self.limit = limit
        super().__init__(
            f"daily call limit exceeded for region={region}: used={used} >= limit={limit}"
        )


# ── settings 헬퍼 ────────────────────────────────────────────────────────────

def _module_to_region(module: str) -> Optional[str]:
    """
    llm_calls.module 값에서 region을 유도한다.

    예:
      analysis_5_kr / entry_params_6_kr → 'KR'
      analysis_5_us / entry_params_6_us → 'US'
      그 외 (agent_8 등) → None
    """
    if module.endswith("_kr"):
        return "KR"
    if module.endswith("_us"):
        return "US"
    return None


# ── 일일 호출 카운트 ─────────────────────────────────────────────────────────

def count_calls_today(db_session: Session, region: str, today: Optional[_date_t] = None) -> int:
    """
    오늘 (서버 local time 기준) region의 LLM 호출 수를 센다.

    counted modules: analysis_5_{region}, entry_params_6_{region} (소문자).
    error 여부와 무관하게 모든 시도를 포함 (한도 보호용 — 실패도 토큰 소비).

    Returns:
        int — 오늘 region별 누적 호출 수.
    """
    today = today or datetime.now().date()
    suffix = f"_{region.lower()}"
    rows = db_session.execute(text("""
        SELECT COUNT(*) FROM llm_calls
        WHERE module IN (:m5, :m6)
          AND DATE(timestamp) = :today
    """), {
        "m5": f"analysis_5{suffix}",
        "m6": f"entry_params_6{suffix}",
        "today": today,
    }).scalar()
    return int(rows or 0)


# ── 일일 상한 체크 ─────────────────────────────────────────────────────────

def check_daily_limit(db_session: Session, module: str, settings: dict) -> bool:
    """
    호출 직전 일일 상한 체크. ADR-012 §3.1.

    settings.daily_call_limits.enabled=false 또는 hard_stop_on_exceed=false 시
    경고만 로깅하고 True 반환 (호출 허용).

    settings.daily_call_limits.{kr,us} 한도 도달 시:
      - hard_stop_on_exceed=true → DailyCallLimitExceeded raise
      - false → sync_log WARN 기록 + True 반환

    Args:
        db_session: SQLAlchemy Session.
        module:     llm_calls.module 값 (예: 'analysis_5_us'). region 유도용.
        settings:   settings.yaml 내용.

    Returns:
        bool — True=호출 허용, False=hard_stop 아닌 한도 초과(soft warning만).

    Raises:
        DailyCallLimitExceeded — hard_stop_on_exceed=true + 한도 도달 시.
    """
    cfg = settings.get("daily_call_limits", {}) or {}
    if not cfg.get("enabled", True):
        return True

    region = _module_to_region(module)
    if region is None:
        # 모듈에서 region 유도 불가 — 한도 미적용
        return True

    limit_key = region.lower()
    limit = int(cfg.get(limit_key, 0))
    if limit <= 0:
        return True

    used = count_calls_today(db_session, region)
    if used < limit:
        return True

    # 한도 도달
    hard_stop = bool(cfg.get("hard_stop_on_exceed", True))
    record_sync_log(
        db_session,
        job_name="llm_daily_call_limit",
        market=region,
        status=("ERROR" if hard_stop else "WARN"),
        message=f"region={region} used={used} >= limit={limit} (hard_stop={hard_stop})",
    )
    if hard_stop:
        raise DailyCallLimitExceeded(region=region, used=used, limit=limit)
    return False


# ── sync_log 기록 헬퍼 ──────────────────────────────────────────────────────

def record_sync_log(
    db_session: Session,
    *,
    job_name: str,
    market: str,
    status: str,
    message: str,
    symbol: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    rows_processed: Optional[int] = None,
) -> int:
    """
    sync_log에 한 줄 기록한다 (헌법 §2.2 — write-only, 함수 import 없음).

    ADR-012 §3.2: status='WARN'|'ERROR'로 모니터링 이벤트 영구 보존.
    Args:
        status: 'success' | 'failed' | 'running' | 'WARN' | 'ERROR'
        message: 1024자 이내. 길면 자동 truncate.

    Returns:
        sync_log.id (BIGINT).
    """
    from models.db_models import SyncLog

    now = datetime.now()
    record = SyncLog(
        job_name=job_name[:64],
        market=market[:16],
        symbol=(symbol[:32] if symbol else None),
        start_time=(start_time or now),
        end_time=end_time,
        rows_processed=(rows_processed if rows_processed is not None else 0),
        status=status[:16],
        message=(message[:1024] if message else None),
    )
    db_session.add(record)
    db_session.flush()
    db_session.commit()
    return record.id


# ── ADR-012 §3.3: 약관 위반 징후 감지 ──────────────────────────────────────

# CLI 응답 텍스트 / error 메시지에서 잡아낼 약관 위반·계정 경고 패턴
_TERMS_VIOLATION_PATTERNS: list[tuple[str, str]] = [
    (r"rate[\s_-]?limit", "rate_limit"),
    (r"usage[\s_-]?limit", "usage_limit"),
    (r"plan[\s_-]?limit", "plan_limit"),
    (r"policy violation", "policy_violation"),
    (r"terms of service", "tos_warning"),
    (r"account[\s_\-\w]{0,40}?\s(suspended|warning|restricted|disabled)", "account_warning"),
    (r"5[\s-]?hour[\s_-]?(window|limit|usage)", "5h_window_warning"),
    (r"max plan limit", "max_plan_limit"),
    (r"automated[\s_-]?(usage|access).*?(detected|blocked|violation)", "automation_violation"),
]


def check_terms_violation_signals(text_blob: Optional[str]) -> list[str]:
    """
    CLI 응답 또는 error 메시지에서 약관 위반·계정 경고 징후 패턴을 추출한다.

    ADR-012 §3.3 — 자동 트리거 환경(Max 플랜 + CLI 백엔드)은 약관 회색 지대.
    Anthropic의 사용량 제한·계정 경고 메시지가 응답 텍스트나 stderr에 노출될 수 있다.
    감지 시 sync_log에 WARN 기록 + 사용자 알림 → ADR-012 §4 절차로 API 백엔드 전환 검토.

    Args:
        text_blob: CLI 응답 텍스트 또는 error 메시지 (None 허용).

    Returns:
        매치된 signal 코드 리스트. 빈 리스트면 정상.
    """
    if not text_blob:
        return []
    blob_lower = text_blob.lower()
    matched: list[str] = []
    for pattern, code in _TERMS_VIOLATION_PATTERNS:
        if re.search(pattern, blob_lower):
            if code not in matched:
                matched.append(code)
    return matched


def record_terms_violation_signal(
    db_session: Session,
    *,
    region: str,
    signals: list[str],
    source: str,
    snippet: Optional[str] = None,
) -> int:
    """
    감지된 약관 위반 징후를 sync_log에 기록.

    Args:
        region: 'KR' | 'US' | 'BOTH'
        signals: check_terms_violation_signals() 반환값
        source: 어디서 감지됐는지 (예: 'cli_response_text', 'cli_error_message')
        snippet: 매치된 텍스트 일부 (메시지 truncate 전)

    Returns:
        sync_log.id
    """
    msg_parts = [f"signals={','.join(signals)}", f"source={source}"]
    if snippet:
        msg_parts.append(f"snippet={snippet[:400]!r}")
    return record_sync_log(
        db_session,
        job_name="llm_terms_violation_signal",
        market=region,
        status="WARN",
        message=" | ".join(msg_parts),
    )


# ── ADR-012 §3.4: 호출 로그 점검 (show_cost_summary가 호출) ────────────────

def get_cost_summary(
    db_session: Session,
    days: int = 7,
) -> dict:
    """
    최근 N일 LLM 호출 통계 — show_cost_summary 백엔드.

    Returns:
        {
          "window_days": int,
          "by_module": [{"module": str, "calls": int, "errors": int, "avg_duration_ms": float, "total_tokens": int, "cost_usd_sum": float | None}, ...],
          "daily": [{"date": str, "calls": int, "errors": int}, ...],
          "warnings_in_sync_log": int,
        }
    """
    since = datetime.now() - timedelta(days=days)

    by_module_rows = db_session.execute(text("""
        SELECT module,
               COUNT(*) AS calls,
               SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) AS errors,
               AVG(duration_ms) AS avg_dur,
               SUM(COALESCE(prompt_tokens,0) + COALESCE(completion_tokens,0)) AS total_tokens,
               SUM(COALESCE(cost_usd, 0)) AS cost_sum
        FROM llm_calls
        WHERE timestamp >= :since
        GROUP BY module
        ORDER BY calls DESC
    """), {"since": since}).fetchall()

    by_module = [
        {
            "module": r[0],
            "calls": int(r[1] or 0),
            "errors": int(r[2] or 0),
            "avg_duration_ms": float(r[3]) if r[3] is not None else None,
            "total_tokens": int(r[4] or 0),
            "cost_usd_sum": float(r[5]) if r[5] is not None else None,
        }
        for r in by_module_rows
    ]

    daily_rows = db_session.execute(text("""
        SELECT DATE(timestamp) AS d,
               COUNT(*) AS calls,
               SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) AS errors
        FROM llm_calls
        WHERE timestamp >= :since
        GROUP BY DATE(timestamp)
        ORDER BY d DESC
    """), {"since": since}).fetchall()

    daily = [
        {"date": str(r[0]), "calls": int(r[1] or 0), "errors": int(r[2] or 0)}
        for r in daily_rows
    ]

    warn_count = db_session.execute(text("""
        SELECT COUNT(*) FROM sync_log
        WHERE start_time >= :since
          AND job_name LIKE 'llm_%'
          AND status IN ('WARN', 'ERROR')
    """), {"since": since}).scalar()

    return {
        "window_days": days,
        "by_module": by_module,
        "daily": daily,
        "warnings_in_sync_log": int(warn_count or 0),
    }
