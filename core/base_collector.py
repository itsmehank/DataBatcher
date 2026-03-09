# core/base_collector.py
from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd


class BaseCollector(ABC):
    """Minimal abstract base for data collectors.
    v5 범위에서는 fetch/validate/save 세 가지 인터페이스만 둡니다.
    """

    category: str = ""

    @abstractmethod
    def fetch(self, symbol: str, start, end, market: str) -> pd.DataFrame:
        """Fetch raw price data for a symbol between [start, end]."""
        raise NotImplementedError

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """간단한 기본 검증: 가격/거래량의 비정상 값 제거.
        복잡한 정합성 검증은 후속 단계에서 추가합니다.
        """
        if df is None or df.empty:
            return df

        # Convert pd.NA to None for MySQL compatibility
        df = df.astype(object).where(pd.notna(df), None)

        # 기대 컬럼: open/high/low/close/volume
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(set(df.columns)):
            return df
        mask = (
            (pd.to_numeric(df["open"], errors="coerce").fillna(0) > 0)
            & (pd.to_numeric(df["high"], errors="coerce").fillna(0) > 0)
            & (pd.to_numeric(df["low"], errors="coerce").fillna(0) > 0)
            & (pd.to_numeric(df["close"], errors="coerce").fillna(0) > 0)
            & (pd.to_numeric(df["low"], errors="coerce") <= pd.to_numeric(df["high"], errors="coerce"))
            & (pd.to_numeric(df["volume"], errors="coerce").fillna(0) >= 0)
        )
        return df.loc[mask]

    @abstractmethod
    def save(self, df: pd.DataFrame, symbol: str) -> int:
        """Persist fetched data into database. Returns affected rows."""
        raise NotImplementedError
