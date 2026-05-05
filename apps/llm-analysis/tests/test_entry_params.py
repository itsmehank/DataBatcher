"""
EntryParams Pydantic 모델 + parse_entry_params_response() 단위 테스트.

LLM 호출 없음 — 텍스트 입력으로 검증만.
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
    """검증을 통과하는 기본 EntryParams payload."""
    base = {
        "pivot_price": 192.50,
        "stop_loss_price": 178.96,           # → -7.0%
        "stop_loss_pct": -7.0,
        "suggested_weight_pct": 10.0,
        "expected_target_price": 231.00,     # → +20.0%
        "expected_target_pct": 20.0,
        "pattern_basis": "flat_base",
        "entry_window_days": 3,
        "max_chase_pct_from_pivot": 5.0,
        "breakout_volume_requirement": "ge_1.4x_50day_avg",
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
    assert result.stop_loss_pct == -7.0
    assert result.suggested_weight_pct == 10.0
    assert result.known_warnings == []
    assert result.other_warnings == []


def test_valid_3c_cheat():
    payload = _valid_payload(
        pattern_basis="3c_cheat",
        stop_loss_pct=-5.5,
        stop_loss_price=181.86,        # 192.50 * (1 - 0.055)
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

def test_stop_pct_inconsistent_with_price():
    """stop_loss_pct가 stop_loss_price와 0.1% 초과로 어긋나면 거부."""
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            stop_loss_price=178.96,
            stop_loss_pct=-8.0,   # 실제는 -7.0%인데 -8.0 보고
        )),
        ParseError,
        match="inconsistent",
    )


def test_target_pct_inconsistent_with_price():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            expected_target_price=231.00,   # 실제 +20%
            expected_target_pct=22.0,        # 보고는 +22%
        )),
        ParseError,
        match="inconsistent",
    )


def test_stop_price_above_pivot_rejected():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            stop_loss_price=192.49,  # 거의 pivot과 같음 (>= pivot * 0.999 위반)
            stop_loss_pct=-0.005,
        )),
        ParseError,
    )


def test_target_price_below_pivot_rejected():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            expected_target_price=192.51,  # pivot * 1.001 미만
            expected_target_pct=0.005,
        )),
        ParseError,
    )


# ── 범위 검증 ─────────────────────────────────────────────────────────────────

def test_stop_loss_pct_below_floor():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            stop_loss_pct=-11.0,
            stop_loss_price=171.33,
        )),
        ParseError,
    )


def test_stop_loss_pct_above_ceiling():
    _assert_raises(
        lambda: parse_entry_params_response(_make_json(
            stop_loss_pct=-4.0,
            stop_loss_price=184.80,
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
    """v2 (5) 'none' 패턴은 (6) pattern_basis enum에 없음 — 거부 (프롬프트 §1 edge case로 처리되어야 함)"""
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
    """10개 known warning enum 각각 검증 통과."""
    for code in VALID_KNOWN_WARNINGS:
        result = parse_entry_params_response(_make_json(known_warnings=[code]))
        assert code in result.known_warnings


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
        "size_reduced_due_to_late_stage",   # → known
        "novel free text describing situation",  # → other
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
    """필수 필드 누락 → 거부."""
    payload = _valid_payload()
    del payload["pivot_price"]
    _assert_raises(
        lambda: parse_entry_params_response(json.dumps(payload)),
        ParseError,
    )


# ── 직접 모델 인스턴스 생성 (Decimal 입력) ──────────────────────────────────────

def test_direct_decimal_construction():
    """JSON 우회 — Decimal 직접 입력."""
    params = EntryParams(
        pivot_price=Decimal("100.00"),
        stop_loss_price=Decimal("93.00"),
        stop_loss_pct=-7.0,
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
