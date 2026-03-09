# savers/indicator_saver.py
from __future__ import annotations
import pandas as pd
from sqlalchemy.engine import Engine
from core.db_manager import DBManager


class IndicatorSaver:
    """Minimal saver for indicator long-form storage.
    v5 범위에서는 long 모드만 지원합니다 (추후 wide/hybrid 확장 가능).
    """

    def __init__(self, engine: Engine, table_long: str = "stock_indicators"):
        self.engine = engine
        self.table_long = table_long

    def save_long(self, df_long: pd.DataFrame, mode: str = "upsert") -> int:
        """
        Save indicator data to database in long-form format.

        Args:
            df_long: DataFrame with columns: symbol, date, indicator, params_hash, value, market, source
            mode: "upsert" (default, overwrites) or "insert_only" (preserves existing)

        Returns:
            Number of rows processed
        """
        if df_long is None or df_long.empty:
            return 0
        return DBManager.upsert_dataframe(
            self.engine,
            df_long,
            table=self.table_long,
            unique_keys=("symbol", "date", "indicator", "params_hash"),
            mode=mode,
        )
