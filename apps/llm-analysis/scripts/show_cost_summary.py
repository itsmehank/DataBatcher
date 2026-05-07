"""
LLM 호출 통계 리포트 — Phase 1.3.6 / ADR-012 §3.4.

기능:
  - 일/주/월 호출 수·실패율·평균 duration·토큰 합계
  - 모듈별 통계 (analysis_5_kr/us, entry_params_6_kr/us 등)
  - sync_log의 'llm_*' WARN/ERROR 카운트
  - daily_call_limits 한도 대비 잔여 비교
  - 약관 위반 징후 (sync_log 'llm_terms_violation_signal') 최근 발생 이력

사용:
  python apps/llm-analysis/scripts/show_cost_summary.py [--days 7] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

_APP_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_APP_ROOT))

from sqlalchemy import text

from core.config import load_settings
from core.cost_tracker import count_calls_today, get_cost_summary
from core.db import make_session_factory


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LLM 호출 통계 리포트")
    p.add_argument("--days", type=int, default=7, help="윈도우 일수 (기본 7)")
    p.add_argument("--json", action="store_true", help="JSON 출력 (기본은 사람-가독 표)")
    return p.parse_args()


def _format_table(rows: list[dict], cols: list[tuple[str, str]]) -> str:
    """간단 표 포매터. cols=[(key, label), ...]."""
    if not rows:
        return "  (no data)"
    headers = [label for _, label in cols]
    widths = [len(h) for h in headers]
    str_rows: list[list[str]] = []
    for r in rows:
        row_strs = []
        for i, (key, _) in enumerate(cols):
            v = r.get(key)
            s = "—" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))
            row_strs.append(s)
            widths[i] = max(widths[i], len(s))
        str_rows.append(row_strs)

    sep = "  ".join("-" * w for w in widths)
    out = ["  " + "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    out.append("  " + sep)
    for rs in str_rows:
        out.append("  " + "  ".join(rs[i].ljust(widths[i]) for i in range(len(rs))))
    return "\n".join(out)


def main() -> int:
    args = _parse_args()
    settings = load_settings()
    sf = make_session_factory()
    s = sf()
    try:
        summary = get_cost_summary(s, days=args.days)

        # 오늘 누적 (limit 비교)
        kr_today = count_calls_today(s, "KR")
        us_today = count_calls_today(s, "US")
        limits_cfg = settings.get("daily_call_limits", {}) or {}

        # 최근 약관 위반 / 토큰 폭증 / 한도 초과 이벤트
        since = datetime.now() - timedelta(days=args.days)
        events = s.execute(text("""
            SELECT start_time, job_name, market, status, message
            FROM sync_log
            WHERE start_time >= :since
              AND job_name IN ('llm_daily_call_limit', 'llm_terms_violation_signal', 'llm_token_spike')
            ORDER BY start_time DESC
            LIMIT 30
        """), {"since": since}).fetchall()

        events_list = [
            {
                "time": str(r[0]),
                "job_name": r[1],
                "market": r[2],
                "status": r[3],
                "message": (r[4] or "")[:200],
            }
            for r in events
        ]

        report = {
            "window_days": args.days,
            "today": {
                "kr_calls": kr_today,
                "us_calls": us_today,
                "kr_limit": limits_cfg.get("kr"),
                "us_limit": limits_cfg.get("us"),
                "kr_remaining": (limits_cfg.get("kr") or 0) - kr_today if limits_cfg.get("enabled", True) else None,
                "us_remaining": (limits_cfg.get("us") or 0) - us_today if limits_cfg.get("enabled", True) else None,
                "hard_stop": limits_cfg.get("hard_stop_on_exceed", True),
            },
            "by_module": summary["by_module"],
            "daily": summary["daily"],
            "warnings_in_sync_log": summary["warnings_in_sync_log"],
            "recent_events": events_list,
        }

        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
            return 0

        # 사람-가독 출력
        print(f"\n=== LLM Cost Summary (last {args.days} days) ===\n")

        print("[Today's call usage vs limits]")
        t = report["today"]
        print(f"  KR: {t['kr_calls']}/{t['kr_limit']} (remaining {t['kr_remaining']})")
        print(f"  US: {t['us_calls']}/{t['us_limit']} (remaining {t['us_remaining']})")
        print(f"  hard_stop_on_exceed = {t['hard_stop']}")

        print("\n[By module]")
        print(_format_table(
            report["by_module"],
            [
                ("module", "module"),
                ("calls", "calls"),
                ("errors", "errors"),
                ("avg_duration_ms", "avg_dur_ms"),
                ("total_tokens", "total_tokens"),
                ("cost_usd_sum", "cost_usd"),
            ],
        ))

        print("\n[Daily totals]")
        print(_format_table(
            report["daily"],
            [
                ("date", "date"),
                ("calls", "calls"),
                ("errors", "errors"),
            ],
        ))

        print(f"\n[sync_log llm_* WARN/ERROR count] {report['warnings_in_sync_log']}")

        if report["recent_events"]:
            print("\n[Recent monitoring events]")
            for e in report["recent_events"]:
                print(f"  {e['time']}  [{e['status']:<7}] {e['job_name']:<30} {e['market']:<5} {e['message']}")
        else:
            print("\n[Recent monitoring events] (none)")

        return 0
    finally:
        s.close()


if __name__ == "__main__":
    sys.exit(main())
