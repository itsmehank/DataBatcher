# core/us_symbol_loader.py
"""
US 종목 목록 로딩 공통 유틸리티

us_symbol_master 테이블에서 다양한 조건으로 종목 목록을 조회하는 헬퍼 함수 제공

패턴: core/symbol_loader.py (KR 주식) 참고
"""
from __future__ import annotations
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


# 유효한 market 값 정의
VALID_US_MARKETS = {'NYSE', 'NASDAQ', 'ETF', 'ALL'}


def load_us_symbols_from_master(
    engine: Engine,
    market: str = "ALL",
    top: Optional[int] = None,
    status: str = "ACTIVE"
) -> List[str]:
    """
    us_symbol_master에서 종목 코드 로드

    Args:
        engine: SQLAlchemy engine
        market: NYSE/NASDAQ/ETF/ALL (default: ALL)
        top: 상위 N개만 (default: None = 전체)
        status: 종목 상태 (default: ACTIVE)

    Returns:
        ["AAPL", "MSFT", ...] 종목코드 리스트

    Raises:
        ValueError: market 값이 유효하지 않은 경우

    Example:
        >>> engine = DBManager.get_engine(db_cfg)
        >>> symbols = load_us_symbols_from_master(engine, market="NASDAQ", top=100)
        >>> print(f"Loaded {len(symbols)} NASDAQ symbols")
    """
    # 검증: market 값이 유효한지 확인
    if market not in VALID_US_MARKETS:
        raise ValueError(
            f"Invalid market value: '{market}'. "
            f"Must be one of {sorted(VALID_US_MARKETS)}"
        )

    sql = """
        SELECT symbol FROM us_symbol_master
        WHERE status = :status
    """
    params: dict[str, object] = {"status": status}

    if market and market != "ALL":
        sql += " AND market = :market"
        params["market"] = market

    # 상위 N개는 symbol 정렬 기준
    sql += " ORDER BY symbol"

    if top:
        sql += " LIMIT :top"
        params["top"] = int(top)

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        return [row[0] for row in result]


def load_us_symbols_with_details(
    engine: Engine,
    market: str = "ALL",
    top: Optional[int] = None,
    status: str = "ACTIVE"
) -> List[dict]:
    """
    us_symbol_master에서 종목 상세 정보 로드

    Args:
        engine: SQLAlchemy engine
        market: NYSE/NASDAQ/ETF/ALL
        top: 상위 N개만
        status: 종목 상태

    Returns:
        [{"symbol": "AAPL", "name": "Apple Inc.", "market": "NASDAQ"}, ...]

    Raises:
        ValueError: market 값이 유효하지 않은 경우
    """
    # 검증: market 값이 유효한지 확인
    if market not in VALID_US_MARKETS:
        raise ValueError(
            f"Invalid market value: '{market}'. "
            f"Must be one of {sorted(VALID_US_MARKETS)}"
        )

    sql = """
        SELECT symbol, name, market, symbol_type FROM us_symbol_master
        WHERE status = :status
    """
    params: dict[str, object] = {"status": status}

    if market and market != "ALL":
        sql += " AND market = :market"
        params["market"] = market

    # 상위 N개는 symbol 정렬 기준
    sql += " ORDER BY symbol"

    if top:
        sql += " LIMIT :top"
        params["top"] = int(top)

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        return [
            {"symbol": row[0], "name": row[1], "market": row[2], "symbol_type": row[3]}
            for row in result
        ]
