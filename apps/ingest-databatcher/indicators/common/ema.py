# indicators/common/ema.py
from __future__ import annotations
import pandas as pd
from indicators.base_indicator import BaseIndicator, IndicatorParams
from indicators.registry import IndicatorRegistry


@IndicatorRegistry.register
class EMA(BaseIndicator):
    name = "ema"

    def required_columns(self, p: IndicatorParams) -> list[str]:
        return [p.params.get("column", "close")]

    def warmup(self, p: IndicatorParams) -> int:
        # 보수적 워밍업: window * 3 (v5 범위에선 단순 적용)
        return int(p.params.get("window", 14)) * 3

    def compute(self, df: pd.DataFrame, p: IndicatorParams) -> pd.Series:
        col = p.params.get("column", "close")
        win = int(p.params.get("window", 14))
        s = df[col].ewm(span=win, adjust=False).mean()
        s.name = f"ema_{win}_{col}"
        return s
