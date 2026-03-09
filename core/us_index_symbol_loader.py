# core/us_index_symbol_loader.py
"""
US Index 마스터 로딩 유틸리티

us_index_master 테이블에서 지수 목록을 조회하는 헬퍼 함수 제공
"""
from __future__ import annotations
from typing import List

from sqlalchemy import text
from sqlalchemy.engine import Engine


VALID_US_INDEX_MARKETS = {'SP500', 'DJI', 'IXIC', 'ALL'}


def load_us_index_symbols(
    engine: Engine,
    market: str = "ALL",
    status: str = "ACTIVE"
) -> List[str]:
    """
    us_index_master에서 지수 코드 로드

    Args:
        engine: SQLAlchemy engine
        market: SP500/DJI/IXIC/ALL (default: ALL)
        status: 상태 (default: ACTIVE)

    Returns:
        ["US500", "DJI", "IXIC"] 지수코드 리스트
    """
    if market not in VALID_US_INDEX_MARKETS:
        raise ValueError(
            f"Invalid market value: '{market}'. "
            f"Must be one of {sorted(VALID_US_INDEX_MARKETS)}"
        )

    sql = """
        SELECT symbol FROM us_index_master
        WHERE status = :status
    """
    params = {"status": status}

    if market and market != "ALL":
        sql += " AND market = :market"
        params["market"] = market

    # 안정적인 실행/테스트를 위해 symbol 기준 고정 정렬
    sql += " ORDER BY symbol"

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        return [row[0] for row in result]


def load_us_index_symbols_with_details(
    engine: Engine,
    market: str = "ALL",
    status: str = "ACTIVE"
) -> List[dict]:
    """
    us_index_master에서 지수 상세 정보 로드

    Args:
        engine: SQLAlchemy engine
        market: SP500/DJI/IXIC/ALL
        status: 상태

    Returns:
        [{"symbol": "US500", "name": "S&P 500", "market": "SP500"}, ...]
    """
    if market not in VALID_US_INDEX_MARKETS:
        raise ValueError(
            f"Invalid market value: '{market}'. "
            f"Must be one of {sorted(VALID_US_INDEX_MARKETS)}"
        )

    sql = """
        SELECT symbol, name, market FROM us_index_master
        WHERE status = :status
    """
    params = {"status": status}

    if market and market != "ALL":
        sql += " AND market = :market"
        params["market"] = market

    # 안정적인 실행/테스트를 위해 symbol 기준 고정 정렬
    sql += " ORDER BY symbol"

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        return [
            {"symbol": row[0], "name": row[1], "market": row[2]}
            for row in result
        ]
