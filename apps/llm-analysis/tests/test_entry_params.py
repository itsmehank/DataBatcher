"""
EntryParams Pydantic 모델 + parse_entry_params_response() 단위 테스트 (v1.1).

LLM 호출 없음 — 텍스트 입력으로 검증만.

v1.1 변경 사항 (Phase 1.3.0):
  - stop_loss_pct → stop_loss_pct_from_pivot (rename)
  - stop_loss_pct_from_current_price + current_price + trigger_price + observed_breakout_volume_ratio (NEW)
  - KnownWarning 2종 추가 + auto-emit
  - legacy v1 → v1.1 mapping 테스트
"""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.result_parser import ParseError, parse_entry_params_response
from models.entry_params import (
    EntryParams,
    VALID_BREAKOUT_VOLUME_REQUIREMENTS,
    VALID_KNOWN_WARNINGS,
    VALID_PATTERNS,
)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _valid_payload(**overrides) -> dict:
    """검증을 통과하는 기본 EntryParams payload (v1.1)."""
    base = {
        "pivot_price": 192.50,
        "trigger_price": 192.69,             # pivot * 1.001 ≈ 192.6925 → round 192.69
        "current_price": 192.30,             # 매수가 echo (pivot 근처)
        "stop_loss_price": 178.96,           # → -7.0% from pivot
        "stop_loss_pct_from_pivot": -7.0,
        "stop_loss_pct_from_current_price": -6.9,  # (178.96 - 192.30)/192.30 = -6.94 → -6.9
        "suggested_weight_pct": 10.0,
        "expected_target_price": 231.00,     # → +20.0%
        "expected_target_pct": 20.0,
        "pattern_basis": "flat_base",
        "entry_window_days": 3,
        "max_chase_pct_from_pivot": 5.0,
        "breakout_volume_requirement": "ge_1.4x_50day_avg",
        "observed_breakout_volume_ratio": None,
        "notes": "Flat base 7 weeks. Stop bound by absolute -7%. Size standard tier 10% with no flags. Target 20% default.",
        "known_warnings": [],
        "other_warnings": [],
    }
    base.update(overrides)
    return base


def _make_json(**overrides) -> str:
    return json.dumps(_valid_payload(**overrides))


def _assert_raises(fn, exc_type, match=None):
    try:
        fn()
        raise AssertionError(f"Expected {exc_type.__name__} but no exception raised")
    except exc_type as e:
        if match and match not in str(e):
            raise AssertionError(f"Exception message {str(e)!r} does not contain {match!r}")


# ── 정상 케이스 ────────────────────────────────────────────────────────────────

def test_valid_default():
    result = parse_entry_params_response(_make_json())
    assert isinstance(result, EntryParams)
    assert result.pattern_basis == "flat_base"
    assert result.stop_loss_pct_from_pivot == -7.0
    assert result.stop_loss_pct_from_current_price == -6.9
    assert result.suggested_weight_pct == 10.0
    assert result.known_warnings == []
    assert result.other_warnings == []


def test_valid_3c_cheat():
    payload = _valid_payload(
        pattern_basis="3c_cheat",
        stop_loss_pct_from_pivot=-5.5,
        stop_loss_price=181.86,        # 192.50 * (1 - 0.055)
        stop_loss_pct_from_current_price=-5.4,  # (181.86-192.30)/192.30 = -5.43
        suggested_weight_pct=3.0,
        expected_target_pct=15.0,
        expected_target_price=221.38,  # 192.50 * 1.15
        entry_window_days=2,
        breakout_volume_requirement="ge_1.5x_50day_avg",
        known_warnings=["pattern_refined_to_3c_cheat"],
        notes="Cheat entry within cup. Absolute -5.5 (3c_cheat tighter rule). Size 3.0 floored from 3c_cheat tier × multiple multipliers.",
    )
    result = parse_entry_params_response(json.dumps(payload))
    assert result.pattern_basis == "3c_cheat"
    assert "pattern_refined_to_3c_cheat" in result.known_warnings


def test_valid_with_other_warning():
    payload = _valid_payload(
        other_warnings=["base low coincides with prior IPO offering price, atypical support level"],
    )
    result = parse_entry_params_response(json.dumps(payload))
    assert len(result.other_warnings) == 1


def test_valid_with_both_warning_lists():
    payload = _valid_payload(
        known_warnings=["size_reduced_due_to_late_stage", "extended_from_pivot_already"],
        other_warnings=["unusual gap up on day before breakout"],
    )
    result = parse_entry_params_response(json.dumps(payload))
    assert len(result.known_warnings) == 2
    assert len(result.other_warnings) == 1


# ── 가격↔pct 일관성 검증 ────────────────────────────────────────────────────────

def test_stop_pct_from_pivot_inconsistent_with_price():
    """stop_loss_pct_from_pivot이 stop_loss_price와 0.1% 초과로 어긋나면 거부."""
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            stop_loss_price=178.96,
            stop_loss_pct_from_pivot=-8.0,   # 실제는 -7.0%인데 -8.0 보고
        )),
        ParseError,
        match="inconsistent",
    )


def test_stop_pct_from_current_price_inconsistent():
    """stop_loss_pct_from_current_price가 stop_loss_price/current_price와 어긋나면 거부."""
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            stop_loss_pct_from_current_price=-3.0,  # 실제 -6.9%
        )),
        ParseError,
        match="inconsistent",
    )


def test_target_pct_inconsistent_with_price():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            expected_target_price=231.00,
            expected_target_pct=22.0,
        )),
        ParseError,
        match="inconsistent",
    )


def test_stop_price_above_pivot_rejected():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            stop_loss_price=192.49,
            stop_loss_pct_from_pivot=-0.005,
            stop_loss_pct_from_current_price=0.099,  # consistent에 맞춰 dummy
        )),
        ParseError,
    )


def test_target_price_below_pivot_rejected():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            expected_target_price=192.51,
            expected_target_pct=0.005,
        )),
        ParseError,
    )


# ── trigger_price 검증 (v1.1 NEW) ──────────────────────────────────────────────

def test_trigger_price_must_exceed_pivot():
    """trigger_price <= pivot_price → reject."""
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(trigger_price=192.50)),
        ParseError,
        match="strictly greater than pivot_price",
    )


def test_trigger_price_buffer_too_large():
    """trigger_price > pivot * 1.005 → reject (0.5% buffer ceiling)."""
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(trigger_price=193.50)),  # 192.50 * 1.0052 (>0.5%)
        ParseError,
        match="≤ pivot_price",
    )


def test_trigger_price_at_buffer_ceiling():
    """trigger_price == pivot * 1.005 → OK (boundary)."""
    payload = _valid_payload(trigger_price=193.46)  # 192.50 * 1.005 = 193.4625
    result = parse_entry_params_response(json.dumps(payload))
    assert float(result.trigger_price) == 193.46


# ── 범위 검증 ─────────────────────────────────────────────────────────────────

def test_stop_loss_pct_from_pivot_below_floor():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            stop_loss_pct_from_pivot=-11.0,
            stop_loss_price=171.33,
            stop_loss_pct_from_current_price=-10.9,
        )),
        ParseError,
    )


def test_stop_loss_pct_from_pivot_above_ceiling():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            stop_loss_pct_from_pivot=-4.0,
            stop_loss_price=184.80,
            stop_loss_pct_from_current_price=-3.9,
        )),
        ParseError,
    )


def test_suggested_weight_below_min():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(suggested_weight_pct=2.0)),
        ParseError,
    )


def test_suggested_weight_above_max():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(suggested_weight_pct=26.0)),
        ParseError,
    )


def test_target_pct_below_min():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            expected_target_pct=10.0,
            expected_target_price=211.75,
        )),
        ParseError,
    )


def test_entry_window_days_below_min():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(entry_window_days=0)),
        ParseError,
    )


def test_entry_window_days_above_max():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(entry_window_days=6)),
        ParseError,
    )


def test_max_chase_pct_above_max():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(max_chase_pct_from_pivot=6.0)),
        ParseError,
    )


# ── enum 검증 ─────────────────────────────────────────────────────────────────

def test_pattern_basis_invalid():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(pattern_basis="ascending_triangle")),
        ParseError,
    )


def test_pattern_basis_none_rejected():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(pattern_basis="none")),
        ParseError,
    )


def test_breakout_volume_invalid():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(breakout_volume_requirement="ge_2.0x_50day_avg")),
        ParseError,
    )


def test_breakout_volume_freeform_rejected():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            breakout_volume_requirement="strong volume on breakout"
        )),
        ParseError,
    )


# ── known_warnings 검증 ────────────────────────────────────────────────────────

def test_known_warnings_invalid_code():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(known_warnings=["my_made_up_warning"])),
        ParseError,
    )


def test_known_warnings_duplicate_rejected():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            known_warnings=["size_reduced_due_to_late_stage", "size_reduced_due_to_late_stage"],
        )),
        ParseError,
        match="duplicates",
    )


def test_all_known_warnings_valid_individually():
    """12개 known warning enum 각각 검증 통과 (v1.1: 10 + 2 신규)."""
    for code in VALID_KNOWN_WARNINGS:
        result = parse_entry_params_response(_make_json(known_warnings=[code]))
        assert code in result.known_warnings


def test_known_warning_count_v11():
    """v1.1 enum count is 12 (v1: 10 + 2 신규)."""
    assert len(VALID_KNOWN_WARNINGS) == 12
    assert "stop_distance_from_current_price_exceeds_book_limit" in VALID_KNOWN_WARNINGS
    assert "breakout_volume_below_requirement" in VALID_KNOWN_WARNINGS


# ── other_warnings 검증 ────────────────────────────────────────────────────────

def test_other_warnings_too_short():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(other_warnings=["abc"])),
        ParseError,
        match="length must be 5..200",
    )


def test_other_warnings_too_long():
    long_text = "x" * 201
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(other_warnings=[long_text])),
        ParseError,
        match="length must be 5..200",
    )


def test_other_warnings_at_min_length():
    result = parse_entry_params_response(_make_json(other_warnings=["abcde"]))
    assert result.other_warnings == ["abcde"]


def test_other_warnings_at_max_length():
    text = "y" * 200
    result = parse_entry_params_response(_make_json(other_warnings=[text]))
    assert result.other_warnings[0] == text


# ── 합산 길이 sanity (≤ 6) ─────────────────────────────────────────────────────

def test_warnings_sum_at_limit():
    """known 4 + other 2 = 6 → OK"""
    payload = _valid_payload(
        known_warnings=[
            "size_reduced_due_to_late_stage",
            "extended_from_pivot_already",
            "absolute_stop_used_due_to_wide_handle",
            "size_reduced_due_to_thin_liquidity",
        ],
        other_warnings=["unusual gap up on day before breakout", "earnings in 2 days"],
    )
    result = parse_entry_params_response(json.dumps(payload))
    assert len(result.known_warnings) + len(result.other_warnings) == 6


def test_warnings_sum_over_limit():
    """known 4 + other 3 = 7 → reject"""
    payload = _valid_payload(
        known_warnings=[
            "size_reduced_due_to_late_stage",
            "extended_from_pivot_already",
            "absolute_stop_used_due_to_wide_handle",
            "size_reduced_due_to_thin_liquidity",
        ],
        other_warnings=["A" * 10, "B" * 10, "C" * 10],
    )
    _assert_raises(
        lambda: parse_entry_params_response(json.dumps(payload)),
        ParseError,
        match="≤ 6",
    )


# ── notes 검증 ────────────────────────────────────────────────────────────────

def test_notes_too_short():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(notes="too short")),
        ParseError,
    )


def test_notes_too_long():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(notes="x" * 601)),
        ParseError,
    )


# ── parser robustness ────────────────────────────────────────────────────────

def test_parse_with_markdown_fence():
    payload = _valid_payload()
    text = "```json\n" + json.dumps(payload) + "\n```"
    result = parse_entry_params_response(text)
    assert isinstance(result, EntryParams)


def test_parse_legacy_parameter_warnings_split():
    """LLM이 단일 parameter_warnings 키로 출력한 경우 known/other 자동 분기."""
    payload = _valid_payload()
    payload.pop("known_warnings")
    payload.pop("other_warnings")
    payload["parameter_warnings"] = [
        "size_reduced_due_to_late_stage",
        "novel free text describing situation",
    ]
    result = parse_entry_params_response(json.dumps(payload))
    assert "size_reduced_due_to_late_stage" in result.known_warnings
    assert "novel free text describing situation" in result.other_warnings


def test_parse_invalid_json():
    _assert_raises(
        lambda: parse_entry_params_response("not json at all"),
        ParseError,
    )


def test_parse_extra_field_rejected():
    """extra='forbid' — 미정의 필드 거부."""
    payload = _valid_payload()
    payload["unknown_field"] = "something"
    _assert_raises(
        lambda: parse_entry_params_response(json.dumps(payload)),
        ParseError,
    )


def test_parse_missing_required_field():
    payload = _valid_payload()
    del payload["pivot_price"]
    _assert_raises(
        lambda: parse_entry_params_response(json.dumps(payload)),
        ParseError,
    )


# ── v1.1 NEW: legacy v1 → v1.1 매핑 ──────────────────────────────────────────

def test_v11_legacy_v1_stop_loss_pct_renamed():
    """v1 단일 stop_loss_pct → stop_loss_pct_from_pivot 자동 rename."""
    payload = _valid_payload()
    # v1 형식 시뮬레이션: stop_loss_pct_from_pivot 제거하고 stop_loss_pct 추가
    payload.pop("stop_loss_pct_from_pivot")
    payload["stop_loss_pct"] = -7.0
    result = parse_entry_params_response(json.dumps(payload))
    assert result.stop_loss_pct_from_pivot == -7.0


def test_v11_legacy_v1_full_response_minimal():
    """v1 raw response (current_price + trigger_price + stop_loss_pct_from_current_price + observed 누락) → result_parser가 derive."""
    # v1 시절 응답 형식 (8 fields short of v1.1 required)
    v1_payload = {
        "pivot_price": 192.50,
        "stop_loss_price": 178.96,
        "stop_loss_pct": -7.0,                     # legacy 단일
        "current_price": 192.30,                   # v1.1 미포함이지만 derive에 필요 → 이 케이스에선 함께 emit 가정
        "suggested_weight_pct": 10.0,
        "expected_target_price": 231.00,
        "expected_target_pct": 20.0,
        "pattern_basis": "flat_base",
        "entry_window_days": 3,
        "max_chase_pct_from_pivot": 5.0,
        "breakout_volume_requirement": "ge_1.4x_50day_avg",
        "notes": "Flat base 7 weeks. Stop bound by absolute -7%. Size standard tier 10%.",
        "known_warnings": [],
        "other_warnings": [],
    }
    # parser는 (1) stop_loss_pct → stop_loss_pct_from_pivot rename
    #         (2) trigger_price ← round(pivot * 1.001, 2) = 192.69 derive
    #         (3) stop_loss_pct_from_current_price ← derive from stop+current
    #         (4) observed_breakout_volume_ratio ← default None
    result = parse_entry_params_response(json.dumps(v1_payload))
    assert result.stop_loss_pct_from_pivot == -7.0
    assert float(result.trigger_price) == 192.69
    assert result.observed_breakout_volume_ratio is None
    # derive: (178.96 - 192.30) / 192.30 * 100 = -6.94 → round 2dp = -6.94
    assert abs(result.stop_loss_pct_from_current_price - (-6.94)) < 0.05


# ── v1.1 NEW: auto-emit known_warnings ──────────────────────────────────────

def test_v11_auto_emit_stop_distance_warning():
    """abs(stop_loss_pct_from_current_price) > 7.5 → known_warnings에 자동 추가."""
    # NVST-style: pivot 22.67, current 23.23, stop 21.47 → -7.58% from current price
    payload = _valid_payload(
        pivot_price=22.67,
        trigger_price=22.69,
        current_price=23.23,
        stop_loss_price=21.47,
        stop_loss_pct_from_pivot=-5.3,             # (21.47-22.67)/22.67 = -5.295
        stop_loss_pct_from_current_price=-7.6,     # (21.47-23.23)/23.23 = -7.58 → -7.6 (round 1dp)
        expected_target_price=27.20,               # 22.67 * 1.20
        expected_target_pct=20.0,
        pattern_basis="cup_with_handle",
        notes="NVST-style late entry: pivot 22.67, current 23.23. Stop bound by absolute -7%, but from current 23.23 the realized loss is -7.6% (exceeds book 7.5% limit → auto-warning).",
        known_warnings=[],   # 빈 list로 emit — 자동 추가 확인
    )
    result = parse_entry_params_response(json.dumps(payload))
    assert "stop_distance_from_current_price_exceeds_book_limit" in result.known_warnings


def test_v11_auto_emit_stop_distance_idempotent():
    """LLM이 이미 명시 emit해도 중복 추가하지 않음."""
    payload = _valid_payload(
        pivot_price=22.67,
        trigger_price=22.69,
        current_price=23.23,
        stop_loss_price=21.47,
        stop_loss_pct_from_pivot=-5.3,
        stop_loss_pct_from_current_price=-7.6,
        expected_target_price=27.20,
        expected_target_pct=20.0,
        pattern_basis="cup_with_handle",
        notes="NVST-style late entry — stop distance from current price already exceeds book limit. Warning manually emitted.",
        known_warnings=["stop_distance_from_current_price_exceeds_book_limit"],
    )
    result = parse_entry_params_response(json.dumps(payload))
    assert result.known_warnings.count("stop_distance_from_current_price_exceeds_book_limit") == 1


def test_v11_no_auto_emit_stop_distance_at_threshold():
    """abs(stop_loss_pct_from_current_price) == 7.5 → 자동 추가 안 함 (strict >)."""
    payload = _valid_payload(
        # 임의로 stop을 7.5% from current로 만들기: current 100, stop 92.5
        pivot_price=100.00,
        trigger_price=100.10,
        current_price=100.00,
        stop_loss_price=92.50,
        stop_loss_pct_from_pivot=-7.5,
        stop_loss_pct_from_current_price=-7.5,    # 정확히 임계
        expected_target_price=120.00,
        expected_target_pct=20.0,
        notes="Boundary case: stop 7.5% from current price exactly. No auto-warning expected (strict greater-than threshold).",
    )
    result = parse_entry_params_response(json.dumps(payload))
    assert "stop_distance_from_current_price_exceeds_book_limit" not in result.known_warnings


def test_v11_auto_emit_breakout_volume_below_requirement():
    """observed_breakout_volume_ratio < requirement threshold → auto-emit."""
    # requirement 1.4×, observed 1.03× → 미달
    payload = _valid_payload(
        observed_breakout_volume_ratio=1.03,
        breakout_volume_requirement="ge_1.4x_50day_avg",
        notes="Breakout already occurred at 1.03× 50-day avg, below 1.4× requirement → auto-warning expected.",
    )
    result = parse_entry_params_response(json.dumps(payload))
    assert "breakout_volume_below_requirement" in result.known_warnings


def test_v11_no_auto_emit_breakout_volume_when_meets_requirement():
    """observed >= requirement → no auto-emit."""
    payload = _valid_payload(
        observed_breakout_volume_ratio=1.85,
        breakout_volume_requirement="ge_1.4x_50day_avg",
        notes="Breakout occurred at 1.85× 50-day avg, well above 1.4× requirement. No auto-warning.",
    )
    result = parse_entry_params_response(json.dumps(payload))
    assert "breakout_volume_below_requirement" not in result.known_warnings


def test_v11_no_auto_emit_breakout_volume_when_observed_null():
    """observed is None (no breakout yet) → no auto-emit regardless of requirement."""
    payload = _valid_payload(
        observed_breakout_volume_ratio=None,
        breakout_volume_requirement="ge_1.4x_50day_avg",
    )
    result = parse_entry_params_response(json.dumps(payload))
    assert "breakout_volume_below_requirement" not in result.known_warnings


def test_v11_dual_auto_emit_combined():
    """두 auto-warning 동시 발생 — NVST의 실제 케이스 시뮬레이션."""
    payload = _valid_payload(
        pivot_price=22.67,
        trigger_price=22.69,
        current_price=23.23,
        stop_loss_price=21.47,
        stop_loss_pct_from_pivot=-5.3,
        stop_loss_pct_from_current_price=-7.6,
        expected_target_price=27.20,
        expected_target_pct=20.0,
        pattern_basis="cup_with_handle",
        observed_breakout_volume_ratio=1.03,
        breakout_volume_requirement="ge_1.4x_50day_avg",
        notes="NVST: late entry above pivot + breakout volume below requirement. Both auto-warnings expected.",
        known_warnings=[],
    )
    result = parse_entry_params_response(json.dumps(payload))
    assert "stop_distance_from_current_price_exceeds_book_limit" in result.known_warnings
    assert "breakout_volume_below_requirement" in result.known_warnings


def test_v11_auto_emit_then_warnings_sum_check():
    """auto-emit 후에도 합산 ≤ 6 검증."""
    # 미리 5개 known_warning을 emit하고 auto-emit이 6번째로 추가되는 케이스 — OK
    payload = _valid_payload(
        pivot_price=22.67,
        trigger_price=22.69,
        current_price=23.23,
        stop_loss_price=21.47,
        stop_loss_pct_from_pivot=-5.3,
        stop_loss_pct_from_current_price=-7.6,
        expected_target_price=27.20,
        expected_target_pct=20.0,
        pattern_basis="cup_with_handle",
        notes="Five manual warnings + one auto-emit = exactly 6, at the sanity bound limit.",
        known_warnings=[
            "size_reduced_due_to_late_stage",
            "extended_from_pivot_already",
            "absolute_stop_used_due_to_wide_handle",
            "size_reduced_due_to_thin_liquidity",
            "size_floored_due_to_multiple_flags",
        ],
    )
    result = parse_entry_params_response(json.dumps(payload))
    # 5개 명시 + 1개 자동 = 6 (auto stop_distance만 발생, breakout_volume은 observed=None이라 skip)
    assert len(result.known_warnings) + len(result.other_warnings) == 6
    assert "stop_distance_from_current_price_exceeds_book_limit" in result.known_warnings


def test_v11_auto_emit_pushes_over_limit_rejected():
    """이미 6개 warning이 있는데 auto-emit이 7번째로 추가되는 케이스 → reject."""
    payload = _valid_payload(
        pivot_price=22.67,
        trigger_price=22.69,
        current_price=23.23,
        stop_loss_price=21.47,
        stop_loss_pct_from_pivot=-5.3,
        stop_loss_pct_from_current_price=-7.6,
        expected_target_price=27.20,
        expected_target_pct=20.0,
        pattern_basis="cup_with_handle",
        notes="Edge case: six manual warnings + one auto-emit = 7, exceeds sanity bound.",
        known_warnings=[
            "size_reduced_due_to_late_stage",
            "extended_from_pivot_already",
            "absolute_stop_used_due_to_wide_handle",
            "size_reduced_due_to_thin_liquidity",
            "size_floored_due_to_multiple_flags",
            "pattern_refined_to_3c_cheat",
        ],
    )
    _assert_raises(
        lambda: parse_entry_params_response(json.dumps(payload)),
        ParseError,
        match="≤ 6",
    )


# ── 직접 모델 인스턴스 생성 (Decimal 입력) ──────────────────────────────────────

def test_direct_decimal_construction():
    """JSON 우회 — Decimal 직접 입력."""
    params = EntryParams(
        pivot_price=Decimal("100.00"),
        trigger_price=Decimal("100.10"),
        current_price=Decimal("100.00"),
        stop_loss_price=Decimal("93.00"),
        stop_loss_pct_from_pivot=-7.0,
        stop_loss_pct_from_current_price=-7.0,
        suggested_weight_pct=10.0,
        expected_target_price=Decimal("120.00"),
        expected_target_pct=20.0,
        pattern_basis="flat_base",
        entry_window_days=3,
        max_chase_pct_from_pivot=5.0,
        breakout_volume_requirement="ge_1.4x_50day_avg",
        notes="A" * 50,
    )
    assert params.pivot_price == Decimal("100.00")


# ── 메인 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import inspect

    test_funcs = [
        (name, obj) for name, obj in inspect.getmembers(sys.modules[__name__])
        if inspect.isfunction(obj) and name.startswith("test_")
    ]

    passed = 0
    failed: list[tuple[str, Exception]] = []
    for name, fn in test_funcs:
        try:
            fn()
            print(f"  ok  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
            failed.append((name, e))

    total = len(test_funcs)
    print(f"\n{'OK' if not failed else 'FAILED'}: {passed}/{total} passed")
    if failed:
        sys.exit(1)
