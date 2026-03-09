# indicators/common/sma.py
from __future__ import annotations
import pandas as pd
from indicators.base_indicator import BaseIndicator, IndicatorParams
from indicators.registry import IndicatorRegistry


@IndicatorRegistry.register
class SMA(BaseIndicator):
    name = "sma"

    def required_columns(self, p: IndicatorParams) -> list[str]:
        return [p.params.get("column", "close")]

    def warmup(self, p: IndicatorParams) -> int:
        return int(p.params.get("window", 14))

    def compute(self, df: pd.DataFrame, p: IndicatorParams) -> pd.Series:
        col = p.params.get("column", "close")
        win = int(p.params.get("window", 14))
        s = df[col].rolling(win, min_periods=win).mean()
        s.name = f"sma_{win}_{col}"
        return s
