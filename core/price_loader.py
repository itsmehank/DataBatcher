# core/price_loader.py
from __future__ import annotations
from datetime import date
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text


def load_price_data(
    engine: Engine,
    symbol: str,
    start_date: date,
    end_date: date,
    table: str = "stock_prices",
    columns: list[str] | None = None
) -> pd.DataFrame:
    """
    DB에서 특정 종목의 가격 데이터 조회.

    다양한 테이블 지원:
    - KR 주식: table="stock_prices" (기본값)
    - US 주식: table="us_stock_prices"
    - KR 지수: table="kr_index_prices", columns=["date","open","high","low","close","volume"]

    Args:
        engine: SQLAlchemy engine
        symbol: 종목코드
        start_date: 시작일
        end_date: 종료일
        table: 테이블명 (기본: stock_prices)
        columns: SELECT할 컬럼 목록 (기본: date,open,high,low,close,adj_close,volume)

    Returns:
        DataFrame with specified columns
        (지표 계산에 필요한 형식, 날짜 오름차순 정렬)
        데이터가 없으면 빈 DataFrame 반환
    """
    if columns is None:
        columns = ["date", "open", "high", "low", "close", "adj_close", "volume"]
    cols_str = ", ".join(columns)

    sql = text(f"""
        SELECT {cols_str}
        FROM {table}
        WHERE symbol = :symbol
          AND date >= :start_date
          AND date <= :end_date
        ORDER BY date ASC
    """)

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params={
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date
        })

    return df