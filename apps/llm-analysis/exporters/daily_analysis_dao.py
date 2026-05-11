"""
DAO for daily_analysis_kr / daily_analysis_us tables.

Phase 2 Sprint 1 — Step 1.B.1.
ExcelExporter의 read-only 입력 어댑터. JSON 컬럼은 dict로 파싱하여 반환.

세션 사용 패턴은 apps/llm-analysis/scripts/run_daily_analysis.py 계승:
  session_factory = make_session_factory()
  s = session_factory()
  try:
      rows = list(fetch_daily_analysis(s, target_date, region))
  finally:
      s.close()
"""

from __future__ import annotations

import json
from datetime import date as date_cls
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from .excel_exporter import DailyAnalysisRow, Region


_SELECT_COLUMNS = (
    "symbol, date, market, classification, confidence, reasoning, pattern, "
    "risk_flags, entry_params, screen_config_hash, llm_call_id"
)


def _parse_json(value) -> dict | None:
    """MySQL JSON 컬럼을 dict로 반환. PyMySQL은 보통 자동 파싱하나 안전망 유지."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        return json.loads(s)
    return value


def _query_one_region(
    session: Session,
    table: str,
    target_date: date_cls,
    region: Region,
) -> list[DailyAnalysisRow]:
    sql = text(
        f"SELECT {_SELECT_COLUMNS} FROM {table} "
        "WHERE date = :target_date "
        "ORDER BY "
        "  CASE classification "
        "    WHEN 'entry' THEN 0 WHEN 'watch' THEN 1 WHEN 'ignore' THEN 2 ELSE 3 END, "
        "  symbol"
    )
    result = session.execute(sql, {"target_date": target_date}).mappings().all()

    rows: list[DailyAnalysisRow] = []
    for r in result:
        rows.append(
            DailyAnalysisRow(
                symbol=r["symbol"],
                date=r["date"],
                market=r["market"],
                classification=r["classification"],
                confidence=float(r["confidence"]) if r["confidence"] is not None else None,
                reasoning=r["reasoning"],
                pattern=r["pattern"],
                risk_flags=_parse_json(r["risk_flags"]),
                entry_params=_parse_json(r["entry_params"]),
                screen_config_hash=r["screen_config_hash"],
                llm_call_id=r["llm_call_id"],
                region=region,
            )
        )
    return rows


def fetch_daily_analysis(
    session: Session,
    target_date: date_cls,
    region: Region,
) -> Iterable[DailyAnalysisRow]:
    """Fetch rows from daily_analysis_kr / daily_analysis_us for the target date.

    Args:
        session: SQLAlchemy session (caller manages lifecycle).
        target_date: 분석 거래일.
        region: 'kr' | 'us' | 'both'.

    Returns:
        Iterable of DailyAnalysisRow. region='both'인 경우 kr 먼저, us 다음 순서.
        각 region 내부는 classification(entry > watch > ignore) + symbol 정렬.
    """
    if region == "kr":
        return _query_one_region(session, "daily_analysis_kr", target_date, "kr")
    if region == "us":
        return _query_one_region(session, "daily_analysis_us", target_date, "us")
    if region == "both":
        kr = _query_one_region(session, "daily_analysis_kr", target_date, "kr")
        us = _query_one_region(session, "daily_analysis_us", target_date, "us")
        return [*kr, *us]
    raise ValueError(f"Unknown region: {region!r}. Expected 'kr' | 'us' | 'both'.")
