"""
CLI entrypoint for Phase 2 Sprint 1 — daily Excel report generation.

Usage:
    python run_excel_export.py --date 2026-05-06 --region us
    python run_excel_export.py --date 2026-05-06 --region both --out-dir ./out

Phase 2 Sprint 1 — phase2_brief.md §3 Sprint 1.
Reads daily_analysis_kr / daily_analysis_us via DAO and writes a 3-sheet Excel.
"""
from __future__ import annotations

import argparse
import sys
import traceback
from datetime import date
from pathlib import Path

# apps/llm-analysis/ 를 sys.path에 추가 (run_daily_analysis.py 양식 계승)
_APP_ROOT = Path(__file__).parent
sys.path.insert(0, str(_APP_ROOT))

from core.db import make_session_factory
from exporters.daily_analysis_dao import fetch_daily_analysis
from exporters.excel_exporter import ExcelExporter


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"invalid date {s!r}, expected YYYY-MM-DD") from e


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Daily LLM analysis Excel exporter — Phase 2 Sprint 1"
    )
    parser.add_argument("--date", required=True, type=_parse_date, help="분석 거래일 YYYY-MM-DD")
    parser.add_argument(
        "--region", required=True, choices=["kr", "us", "both"],
        help="분석 region (kr | us | both)",
    )
    parser.add_argument(
        "--out-dir", default="./out", type=Path,
        help="출력 디렉토리 (기본 ./out, mkdir parents=True exist_ok=True)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    try:
        session_factory = make_session_factory()
    except EnvironmentError as e:
        print(f"[error] DB 연결 설정 실패: {e}", file=sys.stderr)
        return 1

    session = session_factory()
    try:
        try:
            rows = list(fetch_daily_analysis(session, args.date, args.region))
        except Exception:
            print("[error] daily_analysis 조회 실패:", file=sys.stderr)
            traceback.print_exc()
            return 1
    finally:
        session.close()

    if not rows:
        print(
            f"[warn] {args.date} ({args.region}) 분석 결과 0건 — "
            f"빈 sheet 안내 행 포함된 엑셀 생성",
            file=sys.stderr,
        )

    exporter = ExcelExporter(rows=rows, target_date=args.date, region=args.region)
    try:
        out_path = exporter.export(out_dir=args.out_dir)
    except Exception:
        print("[error] 엑셀 생성 실패:", file=sys.stderr)
        traceback.print_exc()
        return 1

    print(f"Excel written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
