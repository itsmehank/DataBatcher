"""
EntryParams Pydantic 모델 — calculate_entry_params() (6) 응답 검증.

본 모델은 prompts/calculate_entry_params_v1.md 의 §9 Output Schema 와
§Validation ranges 를 코드로 강제한다. 13개 필드 (parameter_warnings 분리: known + other).

검증:
  - field-level: Literal enum, 범위, 정규식 등
  - cross-field: stop_loss_price < pivot_price, target > pivot_price,
    pct ↔ price 일관성, warnings 합산 길이 ≤ 6 등

GLOSSARY Part B.2 entry_params JSON 스키마, ADR-013 (3c_cheat 패턴 포함).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ── Enum (Literal) 정의 ────────────────────────────────────────────────────────

PatternBasis = Literal[
    "flat_base", "cup_with_handle", "vcp", "double_bottom", "3c_cheat",
]

BreakoutVolumeRequirement = Literal[
    "ge_1.3x_50day_avg",  # tight VCP only
    "ge_1.4x_50day_avg",  # default
    "ge_1.5x_50day_avg",  # 3c_cheat
]

KnownWarning = Literal[
    "absolute_stop_used_due_to_wide_handle",
    "logical_stop_exceeded_absolute_floor",
    "size_floored_due_to_multiple_flags",
    "size_reduced_due_to_late_stage",
    "size_reduced_due_to_thin_liquidity",
    "pattern_basis_inferred_from_data",
    "pattern_refined_to_3c_cheat",
    "extended_from_pivot_already",
    "breakout_volume_requirement_relaxed",
    "stop_buffer_increased_for_shake_protection",
]


VALID_PATTERNS: frozenset[str] = frozenset({
    "flat_base", "cup_with_handle", "vcp", "double_bottom", "3c_cheat",
})

VALID_BREAKOUT_VOLUME_REQUIREMENTS: frozenset[str] = frozenset({
    "ge_1.3x_50day_avg", "ge_1.4x_50day_avg", "ge_1.5x_50day_avg",
})

VALID_KNOWN_WARNINGS: frozenset[str] = frozenset({
    "absolute_stop_used_due_to_wide_handle",
    "logical_stop_exceeded_absolute_floor",
    "size_floored_due_to_multiple_flags",
    "size_reduced_due_to_late_stage",
    "size_reduced_due_to_thin_liquidity",
    "pattern_basis_inferred_from_data",
    "pattern_refined_to_3c_cheat",
    "extended_from_pivot_already",
    "breakout_volume_requirement_relaxed",
    "stop_buffer_increased_for_shake_protection",
})


# ── 모델 ──────────────────────────────────────────────────────────────────────

class EntryParams(BaseModel):
    """
    calculate_entry_params() (6) 출력. 13개 필드.

    - 가격 필드는 Decimal (2 decimal places)
    - pct 필드는 float (1 decimal place 허용; -10.0 ~ 50.0 범위)
    - cross-field validation으로 가격↔pct 일관성 강제
    """

    model_config = ConfigDict(extra="forbid")

    pivot_price:                Decimal = Field(gt=0)
    stop_loss_price:            Decimal = Field(gt=0)
    stop_loss_pct:              float   = Field(ge=-10.0, le=-5.0)
    suggested_weight_pct:       float   = Field(ge=3.0,   le=25.0)
    expected_target_price:      Decimal = Field(gt=0)
    expected_target_pct:        float   = Field(ge=15.0,  le=50.0)
    pattern_basis:              PatternBasis
    entry_window_days:          int     = Field(ge=1, le=5)
    max_chase_pct_from_pivot:   float   = Field(ge=0.0, le=5.0)
    breakout_volume_requirement: BreakoutVolumeRequirement
    notes:                      str     = Field(min_length=50, max_length=600)
    known_warnings:             list[KnownWarning] = Field(default_factory=list)
    other_warnings:             list[str]          = Field(default_factory=list)

    # ── field-level validators ─────────────────────────────────────────────

    @field_validator("known_warnings")
    @classmethod
    def _no_duplicate_known_warnings(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError(f"known_warnings has duplicates: {v}")
        return v

    @field_validator("other_warnings")
    @classmethod
    def _other_warnings_length_constraints(cls, v: list[str]) -> list[str]:
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise ValueError(f"other_warnings[{i}] must be a string, got {type(item).__name__}")
            if len(item) < 5 or len(item) > 200:
                raise ValueError(
                    f"other_warnings[{i}] length must be 5..200 characters, got {len(item)}: {item!r}"
                )
        return v

    # ── cross-field model validator ─────────────────────────────────────────

    @model_validator(mode="after")
    def _check_cross_field_consistency(self) -> "EntryParams":
        pivot = float(self.pivot_price)
        stop = float(self.stop_loss_price)
        target = float(self.expected_target_price)

        # 1) stop_loss_price < pivot_price * 0.999 (strictly below pivot with margin)
        if stop >= pivot * 0.999:
            raise ValueError(
                f"stop_loss_price ({stop}) must be strictly less than pivot_price * 0.999 "
                f"({pivot * 0.999:.4f})"
            )

        # 2) expected_target_price > pivot_price * 1.001
        if target <= pivot * 1.001:
            raise ValueError(
                f"expected_target_price ({target}) must be strictly greater than pivot_price * 1.001 "
                f"({pivot * 1.001:.4f})"
            )

        # 3) stop_loss_pct ↔ stop_loss_price 일관성 (tolerance 0.1%)
        implied_stop_pct = (stop - pivot) / pivot * 100.0
        if abs(implied_stop_pct - self.stop_loss_pct) > 0.1:
            raise ValueError(
                f"stop_loss_pct ({self.stop_loss_pct}) inconsistent with stop_loss_price/pivot_price: "
                f"implied {implied_stop_pct:.3f}% (tolerance 0.1)"
            )

        # 4) expected_target_pct ↔ expected_target_price 일관성 (tolerance 0.1%)
        implied_target_pct = (target - pivot) / pivot * 100.0
        if abs(implied_target_pct - self.expected_target_pct) > 0.1:
            raise ValueError(
                f"expected_target_pct ({self.expected_target_pct}) inconsistent with "
                f"expected_target_price/pivot_price: implied {implied_target_pct:.3f}% (tolerance 0.1)"
            )

        # 5) warnings 합산 길이 sanity bound ≤ 6
        total_warnings = len(self.known_warnings) + len(self.other_warnings)
        if total_warnings > 6:
            raise ValueError(
                f"len(known_warnings) + len(other_warnings) must be ≤ 6, got {total_warnings}"
            )

        return self
