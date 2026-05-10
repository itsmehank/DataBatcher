"""
일일 LLM 분석 배치 메인 진입점 — Phase 1.3.1.

Windows Task Scheduler (ADR-012)가 매일 정시에 호출:
  KR: 21:00 KST (KR daily 19:00 + 미너비니 ~19:40 + 안전 마진)
  US: 16:00 KST (US daily 08:00 + 미너비니 ~14:10 + 안전 마진)

기능 (1.3.1~1.3.5):
  - --region {KR, US, BOTH}, --date, --limit, --force-recompute, --dry-run, --backend
  - 분석 대상 (= 해당 날짜 minervini_screen_results_{region} 통과 종목) 조회
  - skip_if_exists 캐싱 (--force-recompute로 무시)
  - 일일 호출 상한 (cost_tracker.check_daily_limit, ADR-012 §3.1)
  - 개별 종목 실패는 sync_log per-symbol 기록 후 계속 (§7.6 partial failure tolerance)
  - DailyCallLimitExceeded raise 시 즉시 종료 + sync_log job summary
  - 모듈 킬 스위치 (settings.modules.{analyze_chart, calculate_entry_params})

사용 예:
  python apps/llm-analysis/scripts/run_daily_analysis.py --region BOTH
  python apps/llm-analysis/scripts/run_daily_analysis.py --region US --date 2026-01-13 --limit 5
  python apps/llm-analysis/scripts/run_daily_analysis.py --region KR --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# apps/llm-analysis/ 를 sys.path에 추가
_APP_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_APP_ROOT))

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.anthropic_client import get_backend, LLMBackend
from core.config import load_settings
from core.cost_tracker import (
    DailyCallLimitExceeded,
    record_sync_log,
)
from core.data_loader import get_screened_symbols, load_symbol_payload
from core.db import make_session_factory
from core.llm_call_recorder import call_and_record
from core.prompt_builder import build_analyze_chart_prompt, build_entry_params_prompt
from core.result_parser import (
    ParseError,
    parse_analysis_result,
    parse_entry_params_response,
)
from models.db_models import DailyAnalysisKR, DailyAnalysisUS


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="일일 LLM 분석 배치 — Phase 1.3 메인 진입점"
    )
    parser.add_argument("--region", required=True, choices=["KR", "US", "BOTH"],
                        help="시장 구역. BOTH는 KR + US 순차 처리")
    parser.add_argument("--date", default=None,
                        help="분석 날짜 YYYY-MM-DD (기본: 각 region별 스크리닝 최신일)")
    parser.add_argument("--limit", type=int, default=None,
                        help="처리 종목 수 상한 override (settings.daily_call_limits보다 우선)")
    parser.add_argument("--force-recompute", action="store_true",
                        help="같은 (symbol, date) 캐시 무시")
    parser.add_argument("--dry-run", action="store_true",
                        help="LLM 호출 없이 대상 종목 리스트만 출력")
    parser.add_argument("--backend", choices=["cli", "api"], default=None,
                        help="LLM 백엔드 override (settings.llm_analysis.backend 보다 우선)")
    return parser.parse_args()


def _resolve_date(db_session: Session, region: str, date_str: Optional[str]) -> Optional[date]:
    """분석 날짜 결정: 인자 있으면 파싱, 없으면 region 스크리닝 최신일."""
    if date_str:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    tbl = "minervini_screen_results_kr" if region == "KR" else "minervini_screen_results_us"
    row = db_session.execute(text(f"SELECT MAX(date) FROM {tbl}")).fetchone()
    if row and row[0]:
        return row[0]
    return None


def _already_exists(db_session: Session, symbol: str, target_date: date, region: str) -> bool:
    tbl = "daily_analysis_kr" if region == "KR" else "daily_analysis_us"
    count = db_session.execute(text(
        f"SELECT COUNT(*) FROM {tbl} WHERE symbol = :sym AND date = :dt"
    ), {"sym": symbol, "dt": target_date}).scalar()
    return (count or 0) > 0


def _save_result(
    db_session: Session,
    symbol: str,
    target_date: date,
    region: str,
    analysis,
    payload: dict,
    llm_call_id: Optional[int],
    entry_params: Optional[dict] = None,
) -> None:
    """daily_analysis 행 저장 (force-recompute 시 DELETE+INSERT)."""
    tbl = "daily_analysis_kr" if region == "KR" else "daily_analysis_us"
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
        entry_params=entry_params,
        screen_config_hash=payload.get("screen_config_hash"),
        llm_call_id=llm_call_id or None,
    )
    db_session.add(row)
    db_session.commit()


def _call_with_parse_retry(
    backend: LLMBackend,
    db_session: Session,
    settings: dict,
    prompt: str,
    model: str,
    max_tokens: int,
    module: str,
    parse_fn,
    *,
    max_retries: int,
    retry_delay: float,
) -> tuple[Optional[object], Optional[int], Optional[str]]:
    """
    LLM 호출 + 1회 파싱 재시도 fallback. 부분 실패 친화.

    Returns:
        (parsed_result | None, llm_call_id | None, error_message | None)
    """
    response, call_id = call_and_record(
        backend, db_session, prompt, model, max_tokens, module,
        max_retries=max_retries, retry_delay_seconds=retry_delay,
        settings=settings,
    )
    if response.error:
        return None, call_id, f"LLM 호출 실패: {response.error}"

    # 1회 파싱 재시도 fallback
    last_parse_error: Optional[str] = None
    for attempt in range(2):
        try:
            parsed = parse_fn(response.text)
            return parsed, call_id, None
        except ParseError as exc:
            last_parse_error = f"parse 실패: {exc}"
            if attempt == 0:
                response, call_id = call_and_record(
                    backend, db_session, prompt, model, max_tokens, module,
                    max_retries=0, retry_delay_seconds=0,
                    settings=settings,
                )
                if response.error:
                    return None, call_id, f"재시도 LLM 호출 실패: {response.error}"
    return None, call_id, last_parse_error


def _process_symbol(
    db_session: Session,
    backend: LLMBackend,
    settings: dict,
    symbol: str,
    target_date: date,
    region: str,
    *,
    force_recompute: bool,
) -> dict:
    """
    한 종목 분석 — (5) → (entry이면) (6). 결과 dict 반환 (요약).

    DailyCallLimitExceeded는 caller로 전파. 그 외 에러는 모두 catch하여
    {"status": "failed", ...} 반환 (부분 실패 허용).
    """
    summary: dict = {"symbol": symbol, "status": "skipped", "classification": None}

    # 캐싱
    caching = settings.get("caching", {}) or {}
    if not force_recompute and caching.get("skip_if_exists", True):
        if _already_exists(db_session, symbol, target_date, region):
            summary["status"] = "cached"
            return summary

    try:
        payload = load_symbol_payload(db_session, symbol, target_date, region, settings)
        if payload is None:
            summary.update(status="failed", error="payload load failed (price/screening data missing)")
            return summary

        # 모듈 킬 스위치
        modules_cfg = settings.get("modules", {}) or {}
        if not modules_cfg.get("analyze_chart", True):
            summary.update(status="skipped", error="modules.analyze_chart disabled")
            return summary

        # (5) analyze_chart
        anthropic_cfg = settings.get("anthropic", {}) or {}
        retry_cfg = anthropic_cfg.get("retry", {}) or {}
        model = anthropic_cfg.get("model_analysis", "claude-sonnet-4-5")
        max_tokens = int(anthropic_cfg.get("max_tokens", 2000))
        max_retries = max(0, int(retry_cfg.get("max_attempts", 3)) - 1)
        backoff = float(retry_cfg.get("backoff_base_sec", 2))

        prompt5 = build_analyze_chart_prompt(payload, settings)
        module5 = "analysis_5_kr" if region == "KR" else "analysis_5_us"
        analysis, call_id, err = _call_with_parse_retry(
            backend, db_session, settings, prompt5, model, max_tokens, module5,
            parse_analysis_result,
            max_retries=max_retries, retry_delay=backoff,
        )
        if analysis is None:
            summary.update(status="failed", error=err or "analyze_chart returned None", llm_call_id=call_id)
            return summary

        # (6) calculate_entry_params — entry 분류 시
        entry_params_dict: Optional[dict] = None
        entry_call_id: Optional[int] = None
        entry_err: Optional[str] = None
        if analysis.classification == "entry":
            if not modules_cfg.get("calculate_entry_params", True):
                entry_err = "modules.calculate_entry_params disabled"
            else:
                model_e = anthropic_cfg.get("model_entry", model)
                prompt6 = build_entry_params_prompt(payload, analysis.model_dump(), settings)
                module6 = "entry_params_6_kr" if region == "KR" else "entry_params_6_us"
                entry, entry_call_id, entry_err = _call_with_parse_retry(
                    backend, db_session, settings, prompt6, model_e, max_tokens, module6,
                    parse_entry_params_response,
                    max_retries=max_retries, retry_delay=backoff,
                )
                if entry is not None:
                    entry_params_dict = entry.model_dump(mode="json")

        # 저장
        _save_result(
            db_session, symbol, target_date, region,
            analysis, payload, call_id, entry_params=entry_params_dict,
        )

        summary.update(
            status="ok",
            classification=analysis.classification,
            confidence=float(analysis.confidence),
            llm_call_id=call_id,
            entry_params_call_id=entry_call_id,
            entry_params_err=entry_err,
        )
        return summary

    except DailyCallLimitExceeded:
        # 호출자(_process_region)가 catch
        raise
    except Exception as exc:
        summary.update(status="failed", error=f"unhandled: {exc}", traceback=traceback.format_exc())
        return summary


def _process_region(
    db_session: Session,
    backend: LLMBackend,
    settings: dict,
    region: str,
    target_date: date,
    *,
    limit: Optional[int],
    force_recompute: bool,
    dry_run: bool,
) -> dict:
    """
    한 region 일괄 처리.

    Returns 요약 dict. caller가 종합 후 stdout/sync_log에 기록.
    """
    job_start = datetime.now()
    job_name = "llm_analysis_kr" if region == "KR" else "llm_analysis_us"

    # job 시작 마커
    record_sync_log(
        db_session,
        job_name=job_name,
        market=region,
        status="running",
        message=f"start target_date={target_date} dry_run={dry_run} force={force_recompute}",
        start_time=job_start,
    )

    symbols_meta = get_screened_symbols(db_session, target_date, region)
    total_screened = len(symbols_meta)

    # ETF 제외는 minervini_update 단계에서 ADR-013 필터로 처리됨.
    # 여기서는 추가 ETF 필터링 없이 스크리닝 결과를 그대로 사용.

    # limit 적용 (RS rating DESC 정렬은 이미 get_screened_symbols에서 적용)
    effective_limit = limit
    if effective_limit is not None and effective_limit > 0:
        symbols_meta = symbols_meta[:effective_limit]

    print(f"[{region}] target_date={target_date}, screened={total_screened}, "
          f"to_process={len(symbols_meta)}, dry_run={dry_run}, force={force_recompute}")

    if dry_run:
        for m in symbols_meta:
            print(f"  - {m['symbol']:<8} ({m.get('market','?')}) RS={m.get('rs_rating')!r}")
        end_time = datetime.now()
        record_sync_log(
            db_session, job_name=job_name, market=region, status="success",
            message=f"dry_run end target_date={target_date} listed={len(symbols_meta)}",
            start_time=job_start, end_time=end_time, rows_processed=len(symbols_meta),
        )
        return {
            "region": region, "target_date": str(target_date),
            "screened": total_screened, "listed": len(symbols_meta),
            "dry_run": True,
        }

    # 실제 처리
    counters = {"ok": 0, "cached": 0, "failed": 0, "skipped": 0}
    classifications = {"entry": 0, "watch": 0, "ignore": 0}
    failed_symbols: list[dict] = []
    halted: bool = False
    halt_reason: Optional[str] = None

    for idx, m in enumerate(symbols_meta, start=1):
        symbol = m["symbol"]
        try:
            summary = _process_symbol(
                db_session, backend, settings,
                symbol, target_date, region,
                force_recompute=force_recompute,
            )
        except DailyCallLimitExceeded as exc:
            halted = True
            halt_reason = str(exc)
            print(f"[{region}] {idx}/{len(symbols_meta)} {symbol}: HALT — {halt_reason}")
            break

        status = summary["status"]
        counters[status] = counters.get(status, 0) + 1
        if status == "ok":
            classification = summary.get("classification")
            if classification in classifications:
                classifications[classification] += 1
            print(f"[{region}] {idx}/{len(symbols_meta)} {symbol}: ok ({classification}, conf={summary.get('confidence')!r})")
        elif status == "cached":
            print(f"[{region}] {idx}/{len(symbols_meta)} {symbol}: cached")
        elif status == "failed":
            failed_symbols.append({"symbol": symbol, "error": summary.get("error")})
            print(f"[{region}] {idx}/{len(symbols_meta)} {symbol}: FAILED — {summary.get('error')}", file=sys.stderr)
            # 개별 실패도 sync_log per-symbol 기록 (§7.6)
            try:
                record_sync_log(
                    db_session, job_name=f"{job_name}_symbol_failure",
                    market=region, symbol=symbol, status="failed",
                    message=f"{summary.get('error', 'unknown')}"[:1024],
                )
            except Exception:
                pass
        else:
            print(f"[{region}] {idx}/{len(symbols_meta)} {symbol}: {status} ({summary.get('error', '-')})")

    end_time = datetime.now()
    job_status = "success"
    if halted:
        job_status = "ERROR"
    elif counters["failed"] > 0:
        job_status = "WARN"  # 부분 실패 (§7.6) — WARN으로 기록

    summary_msg = (
        f"target_date={target_date} screened={total_screened} processed={sum(counters.values())} "
        f"ok={counters['ok']} cached={counters['cached']} failed={counters['failed']} skipped={counters['skipped']} "
        f"entry={classifications['entry']} watch={classifications['watch']} ignore={classifications['ignore']}"
    )
    if halted:
        summary_msg = f"HALT ({halt_reason}) | " + summary_msg

    record_sync_log(
        db_session, job_name=job_name, market=region, status=job_status,
        message=summary_msg[:1024],
        start_time=job_start, end_time=end_time, rows_processed=counters["ok"],
    )

    return {
        "region": region,
        "target_date": str(target_date),
        "screened": total_screened,
        "listed": len(symbols_meta),
        "counters": counters,
        "classifications": classifications,
        "failed_symbols": failed_symbols,
        "halted": halted,
        "halt_reason": halt_reason,
        "duration_seconds": (end_time - job_start).total_seconds(),
    }


def main() -> int:
    args = _parse_args()
    settings = load_settings()

    if args.backend:
        settings.setdefault("llm_analysis", {})["backend"] = args.backend

    backend = get_backend(settings)
    session_factory = make_session_factory()

    regions = ["KR", "US"] if args.region == "BOTH" else [args.region]
    overall: dict = {"regions": []}

    for region in regions:
        s = session_factory()
        try:
            target_date = _resolve_date(s, region, args.date)
            if target_date is None:
                print(f"[{region}] 분석 날짜 결정 실패 — 스크리닝 데이터 없음", file=sys.stderr)
                overall["regions"].append({"region": region, "error": "no screening data"})
                continue
            region_summary = _process_region(
                s, backend, settings, region, target_date,
                limit=args.limit,
                force_recompute=args.force_recompute,
                dry_run=args.dry_run,
            )
            overall["regions"].append(region_summary)
        finally:
            s.close()

    print("\n=== overall ===")
    print(json.dumps(overall, indent=2, ensure_ascii=False, default=str))

    # 종료 코드: 어느 region이라도 halted면 2, 부분 실패만 있으면 1, 정상 0
    halted_any = any(r.get("halted") for r in overall["regions"])
    failed_any = any(
        (r.get("counters", {}) or {}).get("failed", 0) > 0
        for r in overall["regions"]
    )
    if halted_any:
        return 2
    if failed_any:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
