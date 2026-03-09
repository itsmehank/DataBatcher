# indicators/registry.py
from __future__ import annotations
from typing import Dict, Type
from .base_indicator import BaseIndicator


class IndicatorRegistry:
    _reg: Dict[str, Type[BaseIndicator]] = {}

    @classmethod
    def register(cls, ind_cls: Type[BaseIndicator]):
        cls._reg[ind_cls.name] = ind_cls
        return ind_cls

    @classmethod
    def get(cls, name: str) -> Type[BaseIndicator]:
        if name not in cls._reg:
            raise KeyError(f"Indicator not found: {name}")
        return cls._reg[name]

    @classmethod
    def list(cls):
        return list(cls._reg.keys())
