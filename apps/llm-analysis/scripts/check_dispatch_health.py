"""
Daily-email dispatch health monitor.

Phase 2 Phase 6 — phase2_progress.md §6 / ADR-016 C급.

Reports the recent dispatch state of the Sprint 2/3 SMTP pipeline so the user
can scan a 7-trading-day window without grepping JSONL or eyeballing Gmail.

Sources of truth:
- ``apps/llm-analysis/logs/email_dispatch.jsonl`` — append-only dispatch log
  written by ``exporters.email_sender.append_dispatch_log``.
- ``daily_analysis_kr`` / ``daily_analysis_us`` tables — the set of dates that
  *should* have a dispatch (no row → no analysis → no dispatch expected). This
  avoids a market-calendar dependency and is correct by construction.

Exit code 0 when no failures and no missing analysis dates; 1 otherwise.

Constitutional posture (ADR-016 §4.1):
- §2.1 (LLM 직접 주문 실행): not touched — read-only reporting.
- §2.2 (결정론 코어·LLM 분리): not touched — layer 3 ops tool.
- §2.5 (LLM 출력 영구 보존): not touched — no LLM call, no write to
  ``llm_calls`` / ``daily_analysis_*``. JSONL is operational metadata.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Literal

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from exporters.email_sender import DEFAULT_LOG_PATH, EmailDispatchRecord

Region = Literal["kr", "us"]
ALL_REGIONS: tuple[Region, ...] = ("kr", "us")


@dataclass
class RegionReport:
    region: Region
    days: int
    window_start: date
    window_end: date
    dispatched_dates: set[date]
    failed_records: list[EmailDispatchRecord]
    analysis_dates: set[date] | None  # None when DB unreachable
    missing_dates: set[date]
    log_status: Literal["present", "missing_file", "empty"]

    @property
    def sent_count(self) -> int:
        return sum(1 for d in self.dispatched_dates if d not in {r.date for r in self.failed_records if _to_date(r.date) in self.dispatched_dates})

    def is_healthy(self) -> bool:
        return not self.failed_records and not self.missing_dates


# ── helpers ───────────────────────────────────────────────────────────────────


def _to_date(value) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise TypeError(f"unsupported date value: {value!r}")


def _iter_jsonl_records(log_path: Path) -> Iterable[EmailDispatchRecord]:
    if not log_path.exists():
        return
    with log_path.open("r", encoding="utf-8") as fp:
        for raw in fp:
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            try:
                yield EmailDispatchRecord(**data)
            except TypeError:
                continue


def read_recent_records(
    log_path: Path,
    region: Region,
    window_start: date,
    window_end: date,
) -> tuple[list[EmailDispatchRecord], Literal["present", "missing_file", "empty"]]:
    """Return records for ``region`` in ``[window_start, window_end]`` + log status."""
    if not log_path.exists():
        return [], "missing_file"
    records: list[EmailDispatchRecord] = []
    any_lines = False
    for rec in _iter_jsonl_records(log_path):
        any_lines = True
        if rec.region != region:
            continue
        try:
            rec_date = _to_date(rec.date)
        except (TypeError, ValueError):
            continue
        if window_start <= rec_date <= window_end:
            records.append(rec)
    status = "empty" if not any_lines else "present"
    return records, status


def fetch_analysis_dates(
    region: Region, window_start: date, window_end: date
) -> set[date] | None:
    """Return analysis dates in window from ``daily_analysis_<region>``.

    Returns ``None`` if the DB is unreachable — the caller treats that as
    "missing-day check skipped" rather than an error.
    """
    try:
        from core.db import make_session_factory
        from sqlalchemy import text
    except Exception:
        return None
    try:
        factory = make_session_factory()
    except Exception:
        return None
    table = f"daily_analysis_{region}"
    session = factory()
    try:
        rows = session.execute(
            text(
                f"SELECT DISTINCT date FROM {table} "
                "WHERE date BETWEEN :start AND :end"
            ),
            {"start": window_start, "end": window_end},
        ).all()
    except Exception:
        return None
    finally:
        session.close()
    out: set[date] = set()
    for (d,) in rows:
        try:
            out.add(_to_date(d))
        except (TypeError, ValueError):
            continue
    return out


# ── core logic ────────────────────────────────────────────────────────────────


def latest_status_per_date(
    records: list[EmailDispatchRecord],
) -> dict[date, EmailDispatchRecord]:
    """Pick the most-recent record per analysis date (by timestamp)."""
    latest: dict[date, EmailDispatchRecord] = {}
    for rec in records:
        rec_date = _to_date(rec.date)
        prev = latest.get(rec_date)
        if prev is None or rec.timestamp > prev.timestamp:
            latest[rec_date] = rec
    return latest


def build_region_report(
    region: Region,
    days: int,
    today: date,
    log_path: Path,
    db_fetch=None,
) -> RegionReport:
    # Late-binding default so module-level monkeypatching of
    # ``fetch_analysis_dates`` is honored by callers that pass no override.
    if db_fetch is None:
        db_fetch = fetch_analysis_dates
    window_end = today
    window_start = today - timedelta(days=days - 1)
    records, log_status = read_recent_records(log_path, region, window_start, window_end)
    latest = latest_status_per_date(records)

    dispatched_dates: set[date] = set()
    failed_records: list[EmailDispatchRecord] = []
    for d, rec in latest.items():
        if rec.status in ("sent", "dry_run"):
            dispatched_dates.add(d)
        elif rec.status == "failed":
            failed_records.append(rec)

    analysis_dates = db_fetch(region, window_start, window_end)
    if analysis_dates is None:
        missing_dates: set[date] = set()
    else:
        attempted = dispatched_dates | {_to_date(r.date) for r in failed_records}
        missing_dates = analysis_dates - attempted

    return RegionReport(
        region=region,
        days=days,
        window_start=window_start,
        window_end=window_end,
        dispatched_dates=dispatched_dates,
        failed_records=failed_records,
        analysis_dates=analysis_dates,
        missing_dates=missing_dates,
        log_status=log_status,
    )


def format_report(report: RegionReport, log_path: Path) -> list[str]:
    region_label = report.region.upper()
    header = (
        f"[{region_label}] 최근 {report.days}일 "
        f"({report.window_start.isoformat()} ~ {report.window_end.isoformat()})"
    )
    lines = [header]

    if report.log_status == "missing_file":
        lines.append(
            f"  JSONL 파일 없음 (경로: {log_path}) — 자동 발송 미가동 또는 첫 실행 전"
        )
        return lines
    if report.log_status == "empty":
        lines.append(f"  JSONL 비어있음 (경로: {log_path})")
        return lines

    sent_count = len(report.dispatched_dates)
    failed_count = len(report.failed_records)
    if report.analysis_dates is None:
        missing_repr = "DB 미연결 (점검 skip)"
    else:
        missing_repr = f"{len(report.missing_dates)}건"
    lines.append(
        f"  성공/dry_run {sent_count}건, 실패 {failed_count}건, 누락 {missing_repr}"
    )

    if report.failed_records:
        lines.append("  실패 내역:")
        for rec in sorted(report.failed_records, key=lambda r: r.timestamp):
            err = rec.error_message or "원인 미상"
            lines.append(f"    - {rec.date} (retry={rec.retry_count}): {err}")

    if report.missing_dates:
        lines.append("  누락 거래일 (분석 행 존재, 발송 기록 부재):")
        for d in sorted(report.missing_dates):
            lines.append(f"    - {d.isoformat()}")
    return lines


# ── CLI ──────────────────────────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Daily-email dispatch health monitor — Phase 2 Phase 6"
    )
    parser.add_argument("--days", type=int, default=7, help="점검 윈도우 일수 (기본 7)")
    parser.add_argument(
        "--region",
        choices=["kr", "us", "both"],
        default="both",
        help="점검 region (기본 both)",
    )
    parser.add_argument(
        "--log-path",
        default=DEFAULT_LOG_PATH,
        type=Path,
        help=f"JSONL 발송 기록 경로 (기본 {DEFAULT_LOG_PATH})",
    )
    parser.add_argument(
        "--today",
        default=None,
        type=lambda s: date.fromisoformat(s),
        help="윈도우 종료일 (테스트용, 기본 오늘 KST 로컬 일자)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.days < 1:
        print("[error] --days must be >= 1", file=sys.stderr)
        return 1
    today = args.today or datetime.now().astimezone().date()
    regions: tuple[Region, ...] = ALL_REGIONS if args.region == "both" else (args.region,)

    overall_healthy = True
    for idx, region in enumerate(regions):
        report = build_region_report(region, args.days, today, args.log_path)
        for line in format_report(report, args.log_path):
            print(line)
        if not report.is_healthy() or report.log_status != "present":
            overall_healthy = False
        if idx < len(regions) - 1:
            print()

    return 0 if overall_healthy else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
