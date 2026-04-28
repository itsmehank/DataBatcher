"""AnalysisResult Pydantic 모델 — analyze_chart() LLM 응답 검증."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

VALID_PATTERNS: frozenset[str] = frozenset({"flat_base", "VCP", "cup_handle", "double_bottom", "none"})
VALID_RISK_FLAGS: frozenset[str] = frozenset({
    "high_rs_rating",
    "extended_from_ma50",
    "low_volume",
    "thin_base",
    "earnings_imminent",
    "market_weakness",
    "sector_overconcentration",
})


class AnalysisResult(BaseModel):
    classification: Literal["entry", "watch", "ignore"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    pattern: str
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        if v not in VALID_PATTERNS:
            raise ValueError(f"pattern must be one of {sorted(VALID_PATTERNS)}, got '{v}'")
        return v

    @field_validator("risk_flags")
    @classmethod
    def validate_risk_flags(cls, v: list[str]) -> list[str]:
        invalid = [f for f in v if f not in VALID_RISK_FLAGS]
        if invalid:
            raise ValueError(f"Invalid risk_flags: {invalid}. Valid: {sorted(VALID_RISK_FLAGS)}")
        return v
