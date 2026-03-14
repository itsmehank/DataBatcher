# core/bulk_price_loader.py
"""
전 종목 가격 일괄 로드 유틸리티

IBD RS Rating 등 횡단면(cross-sectional) 계산에 필요한
전 종목 가격을 wide-format(pivot)으로 로드한다.
"""
from __future__ import annotations

from datetime import date
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def load_all_prices_wide(
    engine: Engine,
    start_date: date,
    end_date: date,
    table: str = "stock_prices",
    market: str | None = None,
    price_column: str = "close",
) -> pd.DataFrame:
    """
    전 종목 가격을 wide-format으로 로드.

    Args:
        engine: SQLAlchemy engine
        start_date: 시작일
        end_date: 종료일
        table: 가격 테이블명 (stock_prices / us_stock_prices)
        market: 시장 필터 (None이면 전체). KOSPI/KOSDAQ/ETF 또는 NYSE/NASDAQ/ETF
        price_column: 가격 컬럼 선택 ("close" | "adj_close")
            - "close": close 사용
            - "adj_close": COALESCE(adj_close, close) 사용 (adj_close NULL fallback)
            - 주의: adj_close 경로는 해당 컬럼이 있는 테이블에서만 사용해야 함

    Returns:
        DataFrame: index=dates(DatetimeIndex), columns=symbols, values=price
    """
    if price_column not in {"close", "adj_close"}:
        raise ValueError(f"Unsupported price_column: {price_column}. Expected 'close' or 'adj_close'.")

    price_expr = "close AS price" if price_column == "close" else "COALESCE(adj_close, close) AS price"
    sql = f"""
        SELECT symbol, date, {price_expr}
        FROM `{table}`
        WHERE date >= :start_date AND date <= :end_date
    """
    params: dict = {"start_date": start_date, "end_date": end_date}

    if market and market != "ALL":
        sql += " AND market = :market"
        params["market"] = market

    sql += " ORDER BY date ASC, symbol ASC"

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)

    if df.empty:
        return pd.DataFrame()

    # pivot to wide format
    df["date"] = pd.to_datetime(df["date"])
    wide = df.pivot(index="date", columns="symbol", values="price")

    return wide


def load_index_close(
    engine: Engine,
    index_symbol: str,
    start_date: date,
    end_date: date,
    table: str = "us_index_prices",
) -> pd.Series:
    """
    벤치마크 지수 close 가격 로드.

    Args:
        engine: SQLAlchemy engine
        index_symbol: 지수 심볼 (예: "US500", "1001")
        start_date: 시작일
        end_date: 종료일
        table: 지수 가격 테이블 (us_index_prices / kr_index_prices)

    Returns:
        Series: index=dates(DatetimeIndex), values=close
    """
    sql = text(f"""
        SELECT date, close
        FROM `{table}`
        WHERE symbol = :symbol
          AND date >= :start_date
          AND date <= :end_date
        ORDER BY date ASC
    """)

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params={
            "symbol": index_symbol,
            "start_date": start_date,
            "end_date": end_date,
        })

    if df.empty:
        return pd.Series(dtype=float)

    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)

    return df["close"]


def load_indicators_wide(
    engine: Engine,
    indicator: str,
    params_hash_val: str,
    start_date: date,
    end_date: date,
    table: str = "stock_indicators",
    market: str | None = None,
) -> pd.DataFrame:
    """
    특정 지표를 wide-format으로 로드.

    Args:
        engine: SQLAlchemy engine
        indicator: 지표명 (예: "ibd_rs_rating", "blue_dot")
        params_hash_val: 파라미터 해시 (고정값)
        start_date: 시작일
        end_date: 종료일
        table: 지표 테이블명 (stock_indicators / us_stock_indicators)
        market: 시장 필터 (None이면 전체)

    Returns:
        DataFrame: index=dates(DatetimeIndex), columns=symbols, values=value
    """
    sql = f"""
        SELECT symbol, date, value
        FROM `{table}`
        WHERE indicator = :indicator
          AND params_hash = :params_hash
          AND date >= :start_date
          AND date <= :end_date
    """
    params: dict = {
        "indicator": indicator,
        "params_hash": params_hash_val,
        "start_date": start_date,
        "end_date": end_date,
    }

    if market and market != "ALL":
        sql += " AND market = :market"
        params["market"] = market

    sql += " ORDER BY date ASC, symbol ASC"

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)

    if df.empty:
        return pd.DataFrame()

    # pivot to wide format
    df["date"] = pd.to_datetime(df["date"])
    wide = df.pivot(index="date", columns="symbol", values="value")

    return wide
