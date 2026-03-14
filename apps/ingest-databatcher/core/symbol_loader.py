# core/symbol_loader.py
"""
종목 목록 로딩 공통 유틸리티

symbol_master 테이블에서 다양한 조건으로 종목 목록을 조회하는 헬퍼 함수 제공
"""
from __future__ import annotations
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


# 유효한 market 값 정의
VALID_MARKETS = {'KOSPI', 'KOSDAQ', 'KONEX', 'ETF', 'ALL'}


def load_symbols_from_master(
    engine: Engine,
    market: str = "ALL",
    top: Optional[int] = None,
    status: str = "ACTIVE"
) -> List[str]:
    """
    symbol_master에서 종목 코드 로드

    Args:
        engine: SQLAlchemy engine
        market: KOSPI/KOSDAQ/KONEX/ALL (default: ALL)
        top: 시가총액 상위 N개만 (default: None = 전체)
        status: 종목 상태 (default: ACTIVE)

    Returns:
        ["005930", "000660", ...] 종목코드 리스트

    Raises:
        ValueError: market 값이 유효하지 않은 경우

    Example:
        >>> engine = DBManager.get_engine(db_cfg)
        >>> symbols = load_symbols_from_master(engine, market="KOSPI", top=100)
        >>> print(f"Loaded {len(symbols)} KOSPI symbols")
    """
    # 검증: market 값이 유효한지 확인
    if market not in VALID_MARKETS:
        raise ValueError(
            f"Invalid market value: '{market}'. "
            f"Must be one of {sorted(VALID_MARKETS)}"
        )

    sql = f"""
        SELECT symbol FROM symbol_master
        WHERE status = '{status}'
    """

    if market and market != "ALL":
        sql += f" AND market = '{market}'"

    sql += " ORDER BY symbol"

    if top:
        sql += f" LIMIT {top}"

    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return [row[0] for row in result]


def load_symbols_with_details(
    engine: Engine,
    market: str = "ALL",
    top: Optional[int] = None,
    status: str = "ACTIVE"
) -> List[dict]:
    """
    symbol_master에서 종목 상세 정보 로드

    Args:
        engine: SQLAlchemy engine
        market: KOSPI/KOSDAQ/KONEX/ALL
        top: 상위 N개만
        status: 종목 상태

    Returns:
        [{"symbol": "005930", "name": "삼성전자", "market": "KOSPI"}, ...]

    Raises:
        ValueError: market 값이 유효하지 않은 경우
    """
    # 검증: market 값이 유효한지 확인
    if market not in VALID_MARKETS:
        raise ValueError(
            f"Invalid market value: '{market}'. "
            f"Must be one of {sorted(VALID_MARKETS)}"
        )

    sql = f"""
        SELECT symbol, name, market FROM symbol_master
        WHERE status = '{status}'
    """

    if market and market != "ALL":
        sql += f" AND market = '{market}'"

    sql += " ORDER BY symbol"

    if top:
        sql += f" LIMIT {top}"

    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return [
            {"symbol": row[0], "name": row[1], "market": row[2]}
            for row in result
        ]