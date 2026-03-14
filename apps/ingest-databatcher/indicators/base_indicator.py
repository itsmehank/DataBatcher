# indicators/base_indicator.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd


@dataclass(frozen=True)
class IndicatorParams:
    name: str
    params: Dict[str, Any]


class BaseIndicator(ABC):
    name: str  # registry key

    @abstractmethod
    def required_columns(self, p: IndicatorParams) -> list[str]:
        ...

    @abstractmethod
    def warmup(self, p: IndicatorParams) -> int:
        ...

    @abstractmethod
    def compute(self, df: pd.DataFrame, p: IndicatorParams):
        """Return a pandas Series or a dict[str, Series] with the same index as df."""
        ...
