"""AnalysisResult Pydantic 모델 — analyze_chart() LLM 응답 검증 (v2 taxonomy)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

VALID_PATTERNS: frozenset[str] = frozenset({
    "flat_base", "cup_with_handle", "vcp", "double_bottom", "none",
})

VALID_RISK_FLAGS: frozenset[str] = frozenset({
    "climax_run",
    "late_stage_base",
    "extended_from_ma",
    "faulty_pivot",
    "low_volume_breakout",
    "narrow_base",
    "wide_and_loose",
    "thin_liquidity_us_only",
    "prior_uptrend_insufficient",
    "volume_contraction_on_advance",
    "reverse_split_distortion",
    "etf_methodology_mismatch",
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
