"""
분석 대상 종목·차트 데이터 DB 조회 — analyze_chart() 입력 페이로드 구성.

읽는 테이블 (읽기 전용, ingest-databatcher가 쓴 데이터):
  - minervini_screen_results_kr/us  : 스크리닝 통과 종목 + conditions_met
  - stock_prices / us_stock_prices  : 일봉 OHLCV
  - stock_prices_weekly / us_stock_prices_weekly : 주봉 OHLCV
  - stock_indicators / us_stock_indicators : SMA/RS 지표
  - symbol_master / us_symbol_master : 섹터 정보
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

_DAILY_SEND = 60    # LLM에 전달할 일봉 행 수
_WEEKLY_SEND = 52   # LLM에 전달할 주봉 행 수

_INDICATOR_NAME_MAP: dict[str, str] = {
    "sma_50_close": "sma_50",
    "sma_150_close": "sma_150",
    "sma_200_close": "sma_200",
    "rs_line": "rs_line",
}


def _tables(region: str) -> dict[str, str]:
    kr = region.upper() == "KR"
    return {
        "screen": "minervini_screen_results_kr" if kr else "minervini_screen_results_us",
        "prices": "stock_prices" if kr else "us_stock_prices",
        "prices_weekly": "stock_prices_weekly" if kr else "us_stock_prices_weekly",
        "indicators": "stock_indicators" if kr else "us_stock_indicators",
        "master": "symbol_master" if kr else "us_symbol_master",
    }


def get_screened_symbols(
    db_session: Session,
    target_date: date,
    region: str,
) -> list[dict]:
    """
    특정 날짜의 미너비니 통과 종목 목록을 반환한다.

    Returns:
        [{"symbol": ..., "market": ..., "rs_rating": ..., "screen_config_hash": ...}, ...]
    """
    tbl = _tables(region)
    rows = db_session.execute(text(
        f"SELECT symbol, market, rs_rating, screen_config_hash "
        f"FROM {tbl['screen']} WHERE date = :dt ORDER BY rs_rating DESC"
    ), {"dt": target_date}).fetchall()

    return [
        {
            "symbol": r[0],
            "market": r[1],
            "rs_rating": float(r[2]) if r[2] is not None else None,
            "screen_config_hash": r[3],
        }
        for r in rows
    ]


def load_symbol_payload(
    db_session: Session,
    symbol: str,
    target_date: date,
    region: str,
    settings: dict,
) -> Optional[dict]:
    """
    단일 종목의 LLM 입력 페이로드를 구성한다.

    Args:
        db_session: SQLAlchemy Session.
        symbol:     종목 코드.
        target_date: 분석 날짜 (= 스크리닝 날짜).
        region:     "KR" 또는 "US".
        settings:   settings.yaml 내용 (config.load_settings() 결과).

    Returns:
        페이로드 dict. 필수 데이터 미존재 시 None.
    """
    region = region.upper()
    if region not in ("KR", "US"):
        raise ValueError(f"region must be 'KR' or 'US', got '{region}'")

    tbl = _tables(region)
    cfg = settings.get("input_data", {})
    daily_lookback = cfg.get("daily_lookback_days", 252)
    weekly_lookback = cfg.get("weekly_lookback_weeks", 156)
    include_indicators = cfg.get(
        "include_indicators",
        ["sma_50_close", "sma_150_close", "sma_200_close", "rs_line"],
    )

    # 1. 스크리너 행 — 해당 (symbol, date)의 가장 최근 hash 기준
    screen_row = db_session.execute(text(
        f"SELECT market, rs_rating, is_blue_dot, conditions_met, screen_config_hash "
        f"FROM {tbl['screen']} WHERE symbol = :sym AND date = :dt "
        f"ORDER BY created_at DESC LIMIT 1"
    ), {"sym": symbol, "dt": target_date}).fetchone()

    if screen_row is None:
        return None

    # 2. 섹터 정보 — symbol_master(KR)는 sector+industry, us_symbol_master는 sector+industry
    master_row = db_session.execute(text(
        f"SELECT sector, industry FROM {tbl['master']} WHERE symbol = :sym LIMIT 1"
    ), {"sym": symbol}).fetchone()

    sector: Optional[str] = master_row[0] if master_row else None
    industry: Optional[str] = master_row[1] if master_row else None

    # 3. 일봉 — 252 거래일 버퍼 (주말·휴일 감안해 1.5배 calendar days)
    daily_from = target_date - timedelta(days=int(daily_lookback * 1.5))
    daily_rows = db_session.execute(text(
        f"SELECT date, open, high, low, close, volume "
        f"FROM {tbl['prices']} "
        f"WHERE symbol = :sym AND date <= :dt AND date >= :from_dt "
        f"ORDER BY date ASC"
    ), {"sym": symbol, "dt": target_date, "from_dt": daily_from}).fetchall()

    if not daily_rows:
        return None

    # current_metrics 계산 (전체 조회 범위 기준)
    w52_rows = daily_rows[-252:] if len(daily_rows) >= 252 else daily_rows
    high_52w = max(float(r[2]) for r in w52_rows)
    low_52w = min(float(r[3]) for r in w52_rows)
    current_close = float(daily_rows[-1][4])
    volumes = [int(r[5]) for r in daily_rows]
    vol_slice = volumes[-20:] if len(volumes) >= 20 else volumes
    vol_ma20 = sum(vol_slice) / len(vol_slice)
    current_volume = volumes[-1]

    pct_from_52w_high = round((current_close - high_52w) / high_52w * 100, 2) if high_52w else None
    pct_above_52w_low = round((current_close - low_52w) / low_52w * 100, 2) if low_52w else None
    volume_ratio = round(current_volume / vol_ma20, 2) if vol_ma20 > 0 else None

    current_metrics = {
        "close": current_close,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "pct_from_52w_high": pct_from_52w_high,
        "pct_above_52w_low": pct_above_52w_low,
        "volume_ma20": int(vol_ma20),
        "volume_today": current_volume,
        "volume_ratio": volume_ratio,
    }

    # LLM에 전달할 일봉 (최근 _DAILY_SEND 행)
    send_daily = daily_rows[-_DAILY_SEND:]
    daily_ohlcv = [
        {
            "date": str(r[0]),
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "volume": int(r[5]),
        }
        for r in send_daily
    ]

    # 4. 주봉 (최근 _WEEKLY_SEND 주)
    weekly_from = target_date - timedelta(weeks=weekly_lookback + 4)
    weekly_rows = db_session.execute(text(
        f"SELECT week_start, open, high, low, close, volume "
        f"FROM {tbl['prices_weekly']} "
        f"WHERE symbol = :sym AND week_start <= :dt AND week_start >= :from_dt "
        f"ORDER BY week_start ASC"
    ), {"sym": symbol, "dt": target_date, "from_dt": weekly_from}).fetchall()

    send_weekly = weekly_rows[-_WEEKLY_SEND:] if weekly_rows else []
    weekly_ohlcv = [
        {
            "week_start": str(r[0]),
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "volume": int(r[5]),
        }
        for r in send_weekly
    ]

    # 5. 인디케이터 (일봉 전송 구간과 동일한 날짜 범위)
    earliest_daily = send_daily[0][0] if send_daily else target_date
    ind_placeholders = ", ".join(f":ind_{i}" for i in range(len(include_indicators)))
    ind_params: dict = {f"ind_{i}": name for i, name in enumerate(include_indicators)}
    ind_params.update({"sym": symbol, "dt": target_date, "from_dt": earliest_daily})

    ind_rows = db_session.execute(text(
        f"SELECT date, indicator, value "
        f"FROM {tbl['indicators']} "
        f"WHERE symbol = :sym AND date >= :from_dt AND date <= :dt "
        f"AND indicator IN ({ind_placeholders}) "
        f"ORDER BY date ASC, indicator ASC"
    ), ind_params).fetchall()

    ind_by_date: dict[str, dict] = {}
    for r in ind_rows:
        d = str(r[0])
        field = _INDICATOR_NAME_MAP.get(r[1], r[1])
        ind_by_date.setdefault(d, {})[field] = float(r[2]) if r[2] is not None else None

    indicators_recent = []
    for row in send_daily:
        d = str(row[0])
        entry: dict = {"date": d}
        entry.update(ind_by_date.get(d, {}))
        indicators_recent.append(entry)

    # 6. conditions_met (ADR-009 / P0.5 이후 신규 행에만 있음 — NULL 허용)
    conditions_met: Optional[dict] = None
    if cfg.get("include_conditions_met", True):
        raw = screen_row[3]
        if isinstance(raw, str):
            try:
                conditions_met = json.loads(raw)
            except json.JSONDecodeError:
                conditions_met = None
        elif isinstance(raw, dict):
            conditions_met = raw

    # 페이로드 조립
    payload: dict = {
        "task": "minervini_chart_analysis",
        "symbol": symbol,
        "market": screen_row[0],
        "date": str(target_date),
        "sector": sector,
        "screen_config_hash": screen_row[4],
        "rs_rating": float(screen_row[1]) if screen_row[1] is not None else None,
        "is_blue_dot": bool(screen_row[2]) if screen_row[2] is not None else None,
        "current_metrics": current_metrics,
        "daily_ohlcv": daily_ohlcv,
        "weekly_ohlcv": weekly_ohlcv,
        "indicators_recent": indicators_recent,
    }

    if conditions_met is not None:
        payload["conditions_met"] = conditions_met
    if industry:
        payload["industry"] = industry

    return payload
