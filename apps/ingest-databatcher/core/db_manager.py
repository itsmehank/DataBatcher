# core/db_manager.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import pandas as pd


@dataclass
class DBConfig:
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_recycle: int = 1800
    pool_pre_ping: bool = True


class DBManager:
    """Singleton-style holder for SQLAlchemy Engine and common helpers."""
    _engine: Optional[Engine] = None

    @classmethod
    def get_engine(cls, cfg: DBConfig | None = None) -> Engine:
        if cls._engine is None:
            if cfg is None:
                raise ValueError("DBConfig must be provided on first engine creation")
            cls._engine = create_engine(
                cfg.url,
                pool_size=cfg.pool_size,
                max_overflow=cfg.max_overflow,
                pool_recycle=cfg.pool_recycle,
                pool_pre_ping=cfg.pool_pre_ping,
                future=True,
            )
        return cls._engine

    @classmethod
    def dispose_engine(cls) -> None:
        """Dispose and reset the singleton engine.

        Useful for test runners/one-off scripts so the process can exit cleanly.
        """
        if cls._engine is not None:
            try:
                cls._engine.dispose()
            finally:
                cls._engine = None

    @classmethod
    def get_latest_date(cls, engine: Engine, table: str, symbol: str) -> Optional[pd.Timestamp]:
        sql = text(f"SELECT MAX(`date`) AS max_date FROM `{table}` WHERE `symbol`=:symbol")
        with engine.connect() as conn:
            row = conn.execute(sql, {"symbol": symbol}).mappings().first()
            if row and row["max_date"]:
                # Return as pandas Timestamp for convenience
                return pd.to_datetime(row["max_date"])
            return None

    @classmethod
    def upsert_dataframe(
        cls,
        engine: Engine,
        df: pd.DataFrame,
        table: str,
        unique_keys: Tuple[str, ...] = ("symbol", "date"),
        mode: str = "upsert",
    ) -> int:
        """
        Perform bulk insert/upsert using MySQL syntax.

        Args:
            engine: SQLAlchemy engine
            df: DataFrame to insert/upsert
            table: Target table name
            unique_keys: Columns that form the unique constraint
            mode: Insert/update behavior
                - "upsert" (default): INSERT ... ON DUPLICATE KEY UPDATE (overwrites existing)
                - "insert_only": INSERT IGNORE (skips existing, preserves original data)

        Returns:
            Number of rows processed

        Notes:
            - "upsert" mode: Updates existing rows with new values
            - "insert_only" mode: Ignores duplicates, only inserts new rows
        """
        if df is None or df.empty:
            return 0

        # MySQL(Python driver)에서는 NaN/inf를 바인딩할 수 없으므로 NULL(None)로 치환
        # - numpy.nan, pandas.NA, +/-inf 모두 대상
        # - object dtype으로 바꿔도 NaN이 남는 케이스가 있어, 안전하게 replace를 수행
        df = df.copy()
        df = df.replace({pd.NA: None, pd.NaT: None})
        try:
            import numpy as np  # local import to avoid mandatory dependency at import time

            df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
        except Exception:
            # numpy가 없거나 기타 문제 시에도 최소 치환은 동작하도록
            pass

        # Ensure column order is stable
        cols = list(df.columns)
        placeholders = ",".join(["%s"] * len(cols))
        cols_escaped = ",".join([f"`{c}`" for c in cols])

        if mode == "insert_only":
            # INSERT IGNORE: Skip duplicates, preserve existing data
            sql = f"""
            INSERT IGNORE INTO `{table}` ({cols_escaped}) VALUES ({placeholders})
            """
        elif mode == "upsert":
            # ON DUPLICATE KEY UPDATE: Overwrite existing data
            update_clause = ",".join([f"`{c}`=VALUES(`{c}`)" for c in cols if c not in unique_keys])
            sql = f"""
            INSERT INTO `{table}` ({cols_escaped}) VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
            """
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'upsert' or 'insert_only'")

        # Convert DataFrame to list of tuples (preserve order)
        data = [tuple(row[c] for c in cols) for _, row in df.iterrows()]

        # Batch insert to reduce lock duration (avoids InnoDB lock wait timeout
        # when multiple workers insert into the same table concurrently)
        batch_size = 500
        for i in range(0, len(data), batch_size):
            chunk = data[i : i + batch_size]
            with engine.begin() as conn:
                conn.exec_driver_sql(sql, chunk)
        return len(data)
