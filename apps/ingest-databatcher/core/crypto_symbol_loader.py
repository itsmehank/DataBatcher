# core/crypto_symbol_loader.py
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


def load_crypto_symbols(engine: Engine, symbols: Optional[List[str]] = None, all_active: bool = False) -> List[str]:
    """코인 심볼 목록 로더.

    우선순위(호출부에서 결정):
      1) all_active=True -> crypto_symbol_master의 ACTIVE 전체
      2) symbols=[...] -> 입력된 심볼만

    여기서는 all_active 또는 symbols 중 하나가 들어온다고 가정.

    Returns:
      대문자로 정규화된 symbol 리스트
    """

    if all_active:
        sql = text(
            """
            SELECT symbol
            FROM crypto_symbol_master
            WHERE status='ACTIVE'
            ORDER BY symbol
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [str(r[0]).upper() for r in rows]

    if symbols:
        return [s.upper().strip() for s in symbols if s and s.strip()]

    return []
