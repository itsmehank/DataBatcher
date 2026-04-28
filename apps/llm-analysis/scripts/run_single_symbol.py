"""
단일 종목 LLM 분석 디버깅 진입점.

사용법:
  python apps/llm-analysis/scripts/run_single_symbol.py \\
      --symbol AAPL --region US [--date 2026-04-25] \\
      [--backend cli|api] [--dry-run] [--force-recompute]

결과는 stdout에 JSON으로 출력하고 daily_analysis_us/kr 테이블에 저장한다.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

# apps/llm-analysis/ 를 sys.path에 추가
_APP_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_APP_ROOT))

from sqlalchemy import text

from core.anthropic_client import get_backend
from core.config import load_settings
from core.data_loader import get_screened_symbols, load_symbol_payload
from core.db import make_session_factory
from core.llm_call_recorder import call_and_record
from core.prompt_builder import build_analyze_chart_prompt
from core.result_parser import ParseError, parse_analysis_result
from models.db_models import DailyAnalysisKR, DailyAnalysisUS


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="단일 종목 LLM 차트 분석")
    parser.add_argument("--symbol", required=True, help="종목 코드 (예: AAPL, 005930)")
    parser.add_argument("--region", required=True, choices=["KR", "US"], help="시장 구역")
    parser.add_argument("--date", default=None, help="분석 날짜 YYYY-MM-DD (기본: 스크리닝 최신일)")
    parser.add_argument("--backend", choices=["cli", "api"], default=None,
                        help="LLM 백엔드 override (기본: settings.yaml llm_analysis.backend)")
    parser.add_argument("--dry-run", action="store_true",
                        help="LLM 호출 없이 페이로드 구성·출력만 수행")
    parser.add_argument("--force-recompute", action="store_true",
                        help="이미 결과 있어도 재호출 (캐시 무시)")
    return parser.parse_args()


def _resolve_date(db_session, symbol: str, region: str, date_str: str | None) -> date | None:
    """분석 날짜 결정: 인자 있으면 파싱, 없으면 스크리닝 최신일."""
    if date_str:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    tbl = "minervini_screen_results_kr" if region == "KR" else "minervini_screen_results_us"
    row = db_session.execute(text(
        f"SELECT MAX(date) FROM {tbl} WHERE symbol = :sym"
    ), {"sym": symbol}).fetchone()
    if row and row[0]:
        return row[0]
    return None


def _already_exists(db_session, symbol: str, target_date: date, region: str) -> bool:
    """daily_analysis 테이블에 (symbol, date) 행이 이미 있는지 확인."""
    tbl = "daily_analysis_kr" if region == "KR" else "daily_analysis_us"
    count = db_session.execute(text(
        f"SELECT COUNT(*) FROM {tbl} WHERE symbol = :sym AND date = :dt"
    ), {"sym": symbol, "dt": target_date}).scalar()
    return (count or 0) > 0


def _save_result(db_session, symbol: str, target_date: date, region: str,
                 analysis, payload: dict, llm_call_id: int) -> None:
    """분석 결과를 daily_analysis_kr/us에 저장 (upsert — 기존 행 삭제 후 재삽입)."""
    tbl = "daily_analysis_kr" if region == "KR" else "daily_analysis_us"
    # 기존 행 삭제 (force-recompute 시)
    db_session.execute(text(
        f"DELETE FROM {tbl} WHERE symbol = :sym AND date = :dt"
    ), {"sym": symbol, "dt": target_date})

    ModelClass = DailyAnalysisKR if region == "KR" else DailyAnalysisUS
    row = ModelClass(
        symbol=symbol,
        date=target_date,
        market=payload.get("market", ""),
        classification=analysis.classification,
        confidence=float(analysis.confidence),
        reasoning=analysis.reasoning,
        pattern=analysis.pattern,
        risk_flags=analysis.risk_flags or None,
        entry_params=None,
        screen_config_hash=payload.get("screen_config_hash"),
        llm_call_id=llm_call_id or None,
    )
    db_session.add(row)
    db_session.commit()


def main() -> None:
    args = _parse_args()
    settings = load_settings()

    # backend override
    if args.backend:
        settings.setdefault("llm_analysis", {})["backend"] = args.backend

    session_factory = make_session_factory()
    db_session = session_factory()

    try:
        target_date = _resolve_date(db_session, args.symbol, args.region, args.date)
        if target_date is None:
            print(f"[ERROR] {args.symbol}의 스크리닝 데이터 없음. --date로 날짜를 지정하거나 kr_minervini_update.py를 먼저 실행하세요.", file=sys.stderr)
            sys.exit(1)

        print(f"[INFO] {args.symbol} ({args.region}) @ {target_date}")

        # 캐시 확인
        if not args.force_recompute and not args.dry_run:
            caching = settings.get("caching", {})
            if caching.get("skip_if_exists", True) and _already_exists(db_session, args.symbol, target_date, args.region):
                print(f"[SKIP] 이미 결과 존재 — --force-recompute 로 재실행 가능")
                sys.exit(0)

        # 페이로드 로드
        payload = load_symbol_payload(db_session, args.symbol, target_date, args.region, settings)
        if payload is None:
            print(f"[ERROR] 페이로드 구성 실패 — 가격·스크리닝 데이터 부족", file=sys.stderr)
            sys.exit(1)

        # dry-run: 페이로드만 출력
        if args.dry_run:
            print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
            return

        # 프롬프트 구성
        prompt = build_analyze_chart_prompt(payload, settings)

        # LLM 백엔드
        backend = get_backend(settings)

        # 모델·토큰 설정
        anthropic_cfg = settings.get("anthropic", {})
        model = anthropic_cfg.get("model_analysis", "claude-sonnet-4-6")
        max_tokens = anthropic_cfg.get("max_tokens", 2000)

        # LLM 호출 + llm_calls INSERT (재시도 포함)
        retry_cfg = anthropic_cfg.get("retry", {})
        max_retries = retry_cfg.get("max_attempts", 3) - 1  # call_and_record은 max_retries=추가시도수
        backoff = retry_cfg.get("backoff_base_sec", 2)

        response, call_id = call_and_record(
            backend, db_session, prompt, model, max_tokens, "analysis_5_kr" if args.region == "KR" else "analysis_5_us",
            max_retries=max_retries,
            retry_delay_seconds=backoff,
        )

        if response.error:
            print(f"[ERROR] LLM 호출 실패: {response.error}", file=sys.stderr)
            sys.exit(1)

        # 파싱 (실패 시 1회 재시도 — 다른 LLM 호출로)
        analysis = None
        for attempt in range(2):
            try:
                analysis = parse_analysis_result(response.text)
                break
            except ParseError as exc:
                if attempt == 0:
                    print(f"[WARN] 파싱 실패, 1회 재시도: {exc}", file=sys.stderr)
                    response, call_id = call_and_record(
                        backend, db_session, prompt, model, max_tokens,
                        "analysis_5_kr" if args.region == "KR" else "analysis_5_us",
                        max_retries=0, retry_delay_seconds=0,
                    )
                    if response.error:
                        print(f"[ERROR] 재시도 LLM 호출 실패: {response.error}", file=sys.stderr)
                        sys.exit(1)
                else:
                    print(f"[ERROR] 파싱 2회 실패 — skip. {exc}", file=sys.stderr)
                    sys.exit(1)

        if analysis is None:
            sys.exit(1)

        # 결과 저장
        _save_result(db_session, args.symbol, target_date, args.region, analysis, payload, call_id)

        # stdout 출력
        result_dict = analysis.model_dump()
        result_dict["llm_call_id"] = call_id
        result_dict["symbol"] = args.symbol
        result_dict["date"] = str(target_date)
        result_dict["prompt_tokens"] = response.prompt_tokens
        result_dict["completion_tokens"] = response.completion_tokens
        result_dict["cost_usd"] = float(response.cost_usd) if response.cost_usd else None
        result_dict["duration_ms"] = response.duration_ms
        print(json.dumps(result_dict, indent=2, ensure_ascii=False, default=str))

    finally:
        db_session.close()


if __name__ == "__main__":
    main()
