"""
EntryParams Pydantic 모델 — calculate_entry_params() (6) 응답 검증.

본 모델은 prompts/calculate_entry_params_v1_1.md 의 §9 Output Schema 와
§Validation ranges 를 코드로 강제한다. v1.1 기준 17개 필드.

v1 → v1.1 변경 (Phase 1.3.0, NVST B.5.5 1차 Evaluator 평가 반영):
  1. stop_loss_pct → stop_loss_pct_from_pivot (rename) + stop_loss_pct_from_current_price (new)
     - 매수가 기준 손절 거리를 별도 필드로 분리. 7.5% 초과 시 known_warning 자동 발행.
  2. trigger_price (new): pivot_price 와 trigger 버퍼를 schema-level로 분리
     ((5)/(6) pivot 표기 일치성 fix).
  3. observed_breakout_volume_ratio (new, optional): breakout이 이미 발생한 케이스의
     실제 관측 거래량 ratio. 선택된 breakout_volume_requirement 임계값 미달 시
     known_warning 자동 발행.
  4. current_price (new): payload current_metrics.close 의 echo. dual stop_pct
     일관성 검증의 기준값.
  5. KnownWarning enum 2종 추가:
     - stop_distance_from_current_price_exceeds_book_limit (auto-emit)
     - breakout_volume_below_requirement (auto-emit)

검증:
  - field-level: Literal enum, 범위, 정규식 등
  - cross-field: stop_loss_price < pivot_price, target > pivot_price,
    pct ↔ price 일관성, warnings 합산 길이 ≤ 6, trigger_price ∈ (pivot, pivot*1.005]
  - auto-emit: model_validator가 두 known_warning을 조건 시 자동 추가

GLOSSARY Part B.2 entry_params JSON 스키마 (v1.1).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

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
    # v1 codes (10)
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
    # v1.1 codes (2 new, auto-emit)
    "stop_distance_from_current_price_exceeds_book_limit",
    "breakout_volume_below_requirement",
]


VALID_PATTERNS: frozenset[str] = frozenset({
    "flat_base", "cup_with_handle", "vcp", "double_bottom", "3c_cheat",
})

VALID_BREAKOUT_VOLUME_REQUIREMENTS: frozenset[str] = frozenset({
    "ge_1.3x_50day_avg", "ge_1.4x_50day_avg", "ge_1.5x_50day_avg",
})

VALID_KNOWN_WARNINGS: frozenset[str] = frozenset({
    # v1 codes
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
    # v1.1 codes
    "stop_distance_from_current_price_exceeds_book_limit",
    "breakout_volume_below_requirement",
})

# 매수가 기준 손절 거리 자동 경고 임계값 (절대값, %)
STOP_DISTANCE_FROM_CURRENT_PRICE_WARNING_THRESHOLD: float = 7.5

# breakout_volume_requirement → 실제 임계 ratio 매핑 (auto-warning 비교용)
_BREAKOUT_VOLUME_THRESHOLD: dict[str, float] = {
    "ge_1.3x_50day_avg": 1.3,
    "ge_1.4x_50day_avg": 1.4,
    "ge_1.5x_50day_avg": 1.5,
}


# ── 모델 ──────────────────────────────────────────────────────────────────────

class EntryParams(BaseModel):
    """
    calculate_entry_params() (6) 출력. v1.1 기준 17개 필드.

    - 가격 필드는 Decimal (2 decimal places)
    - pct 필드는 float (1 decimal place 허용)
    - cross-field validation으로 가격↔pct 일관성, dual stop_pct 일관성 강제
    - 두 known_warning은 model_validator가 조건 시 자동 추가
    """

    model_config = ConfigDict(extra="forbid")

    # 가격 (raw + 버퍼)
    pivot_price:                Decimal = Field(gt=0)
    trigger_price:              Decimal = Field(gt=0)        # v1.1 NEW: pivot 버퍼
    current_price:              Decimal = Field(gt=0)        # v1.1 NEW: payload echo

    # 손절 (price + dual pct)
    stop_loss_price:            Decimal = Field(gt=0)
    stop_loss_pct_from_pivot:   float   = Field(ge=-10.0, le=-5.0)   # v1 stop_loss_pct rename
    stop_loss_pct_from_current_price: float = Field(ge=-15.0, le=-3.0)  # v1.1 NEW

    # 사이즈 + 타겟
    suggested_weight_pct:       float   = Field(ge=3.0,   le=25.0)
    expected_target_price:      Decimal = Field(gt=0)
    expected_target_pct:        float   = Field(ge=15.0,  le=50.0)

    # 패턴 + 운영 가드
    pattern_basis:              PatternBasis
    entry_window_days:          int     = Field(ge=1, le=5)
    max_chase_pct_from_pivot:   float   = Field(ge=0.0, le=5.0)
    breakout_volume_requirement: BreakoutVolumeRequirement
    observed_breakout_volume_ratio: Optional[float] = Field(default=None, ge=0.0, le=20.0)  # v1.1 NEW

    # 자유 텍스트 + 경고
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
    def _check_cross_field_and_auto_emit(self) -> "EntryParams":
        pivot = float(self.pivot_price)
        trigger = float(self.trigger_price)
        current = float(self.current_price)
        stop = float(self.stop_loss_price)
        target = float(self.expected_target_price)

        # 1) stop_loss_price < pivot_price * 0.999
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

        # 3) stop_loss_pct_from_pivot ↔ stop_loss_price/pivot 일관성 (tolerance 0.1%)
        implied_pivot_pct = (stop - pivot) / pivot * 100.0
        if abs(implied_pivot_pct - self.stop_loss_pct_from_pivot) > 0.1:
            raise ValueError(
                f"stop_loss_pct_from_pivot ({self.stop_loss_pct_from_pivot}) inconsistent "
                f"with stop_loss_price/pivot_price: implied {implied_pivot_pct:.3f}% (tolerance 0.1)"
            )

        # 4) stop_loss_pct_from_current_price ↔ stop_loss_price/current_price 일관성
        implied_current_pct = (stop - current) / current * 100.0
        if abs(implied_current_pct - self.stop_loss_pct_from_current_price) > 0.1:
            raise ValueError(
                f"stop_loss_pct_from_current_price ({self.stop_loss_pct_from_current_price}) "
                f"inconsistent with stop_loss_price/current_price: "
                f"implied {implied_current_pct:.3f}% (tolerance 0.1)"
            )

        # 5) expected_target_pct ↔ price 일관성 (tolerance 0.1%)
        implied_target_pct = (target - pivot) / pivot * 100.0
        if abs(implied_target_pct - self.expected_target_pct) > 0.1:
            raise ValueError(
                f"expected_target_pct ({self.expected_target_pct}) inconsistent with "
                f"expected_target_price/pivot_price: implied {implied_target_pct:.3f}% (tolerance 0.1)"
            )

        # 6) trigger_price ∈ (pivot, pivot*1.005] — 버퍼 합리성
        if trigger <= pivot:
            raise ValueError(
                f"trigger_price ({trigger}) must be strictly greater than pivot_price ({pivot})"
            )
        if trigger > pivot * 1.005:
            raise ValueError(
                f"trigger_price ({trigger}) must be ≤ pivot_price * 1.005 ({pivot * 1.005:.4f}) — "
                f"buffer should not exceed ~0.5%"
            )

        # 7) v1.1 auto-emit: stop_distance_from_current_price_exceeds_book_limit
        #    매수가 기준 손절 거리가 7.5% 초과 (절대값) 시 자동 추가
        warning_code_stop = "stop_distance_from_current_price_exceeds_book_limit"
        if abs(self.stop_loss_pct_from_current_price) > STOP_DISTANCE_FROM_CURRENT_PRICE_WARNING_THRESHOLD:
            if warning_code_stop not in self.known_warnings:
                self.known_warnings.append(warning_code_stop)

        # 8) v1.1 auto-emit: breakout_volume_below_requirement
        #    observed ratio 가 선택된 requirement 임계값 미달 시 자동 추가
        warning_code_vol = "breakout_volume_below_requirement"
        if self.observed_breakout_volume_ratio is not None:
            req_threshold = _BREAKOUT_VOLUME_THRESHOLD.get(self.breakout_volume_requirement)
            if req_threshold is not None and self.observed_breakout_volume_ratio < req_threshold:
                if warning_code_vol not in self.known_warnings:
                    self.known_warnings.append(warning_code_vol)

        # 9) warnings 합산 길이 sanity bound ≤ 6 (auto-emit 후 검증)
        total_warnings = len(self.known_warnings) + len(self.other_warnings)
        if total_warnings > 6:
            raise ValueError(
                f"len(known_warnings) + len(other_warnings) must be ≤ 6, got {total_warnings} "
                f"(after auto-emit)"
            )

        return self
