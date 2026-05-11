"""
CLI entrypoint for Phase 2 Sprint 2 — daily analysis email dispatch.

Usage:
    python run_email_send.py --date 2026-05-06 --region us --to me@example.com
    python run_email_send.py --date 2026-05-06 --region both --dry-run

Reads SMTP credentials from environment (.env loaded automatically). Attaches
the Sprint 1 Excel artifact at ``<excel-dir>/daily_analysis_<date>_<region>.xlsx``
unless ``--excel-path`` is given.

Phase 2 Sprint 2 — phase2_brief.md §3 Sprint 2 / ADR-016 §6 (C급).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

_APP_ROOT = Path(__file__).parent
sys.path.insert(0, str(_APP_ROOT))

from dotenv import load_dotenv

from exporters.email_sender import (
    EmailDispatchRecord,
    SMTPConfig,
    dispatch_daily_email,
)

_REPO_ROOT = _APP_ROOT.parent.parent
_DEFAULT_EXCEL_DIR = _APP_ROOT / "out"


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid date {s!r}, expected YYYY-MM-DD"
        ) from exc


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Daily LLM analysis email dispatcher — Phase 2 Sprint 2"
    )
    parser.add_argument("--date", required=True, type=_parse_date, help="분석 거래일 YYYY-MM-DD")
    parser.add_argument(
        "--region", required=True, choices=["kr", "us", "both"],
        help="발송 region (kr | us | both — both 시 2회 발송)",
    )
    parser.add_argument(
        "--to", default=None,
        help="수신자 이메일. 미지정 시 SMTP_TO_DEFAULT 환경 변수 사용.",
    )
    parser.add_argument(
        "--excel-path", default=None, type=Path,
        help="첨부 엑셀 경로. 미지정 시 <excel-dir>/daily_analysis_<date>_<region>.xlsx 추정.",
    )
    parser.add_argument(
        "--excel-dir", default=_DEFAULT_EXCEL_DIR, type=Path,
        help=f"엑셀 자동 추정 시 기준 디렉터리 (기본 {_DEFAULT_EXCEL_DIR.relative_to(_REPO_ROOT)}).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="SMTP 발송 skip. 본문 생성·JSONL 기록만.",
    )
    return parser.parse_args(argv)


def _resolve_recipient(cli_to: str | None) -> str:
    if cli_to:
        return cli_to
    env_to = os.environ.get("SMTP_TO_DEFAULT", "").strip()
    if env_to:
        return env_to
    raise SystemExit(
        "[error] 수신자 미지정: --to 인자 또는 SMTP_TO_DEFAULT 환경 변수 중 하나 필요."
    )


def _resolve_excel_path(
    region: str, target_date: date, cli_path: Path | None, excel_dir: Path
) -> Path:
    if cli_path is not None:
        if not cli_path.exists():
            raise SystemExit(f"[error] --excel-path 파일이 존재하지 않습니다: {cli_path}")
        return cli_path
    guessed = excel_dir / f"daily_analysis_{target_date.isoformat()}_{region}.xlsx"
    if not guessed.exists():
        raise SystemExit(
            f"[error] 자동 추정 엑셀 파일이 없습니다: {guessed}\n"
            "        먼저 run_excel_export.py로 엑셀을 생성하거나 --excel-path를 지정하세요."
        )
    return guessed


def _print_summary(record: EmailDispatchRecord) -> None:
    print(
        f"[{record.status}] {record.region} {record.date} → {record.recipient} "
        f"(retry={record.retry_count}, attach={record.attached_filename})"
    )
    if record.error_message:
        print(f"  error: {record.error_message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    # apps/llm-analysis/.env 또는 root /.env 로드 (core.db와 동일 패턴)
    for env_path in [_REPO_ROOT / ".env", _APP_ROOT / ".env"]:
        if env_path.exists():
            load_dotenv(env_path, override=False)

    recipient = _resolve_recipient(args.to)

    regions: list[str] = ["kr", "us"] if args.region == "both" else [args.region]

    smtp_config: SMTPConfig | None = None
    if not args.dry_run:
        try:
            smtp_config = SMTPConfig.from_env()
        except ValueError as exc:
            print(f"[error] SMTP 설정 누락: {exc}", file=sys.stderr)
            return 1

    exit_code = 0
    for region in regions:
        excel_path = _resolve_excel_path(region, args.date, args.excel_path, args.excel_dir)
        try:
            record = dispatch_daily_email(
                region=region,
                target_date=args.date,
                recipient=recipient,
                excel_path=excel_path,
                dry_run=args.dry_run,
                smtp_config=smtp_config,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {region} 발송 실패: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        _print_summary(record)
        if record.status == "failed":
            exit_code = 1

    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
