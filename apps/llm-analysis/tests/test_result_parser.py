"""
result_parser.py + AnalysisResult 단위 테스트 (v2 taxonomy 기준).
LLM 호출 없음 — 텍스트 입력으로 파싱만 검증.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

from core.result_parser import ParseError, parse_analysis_result
from models.analysis_result import AnalysisResult, VALID_PATTERNS, VALID_RISK_FLAGS


def _make_json(**kwargs) -> str:
    base = {
        "classification": "entry",
        "confidence": 0.85,
        "reasoning": "12-week flat base. Volume contracting. RS Rating 89.",
        "pattern": "flat_base",
        "risk_flags": [],
    }
    base.update(kwargs)
    return json.dumps(base)


def _assert_raises(fn, exc_type, match=None):
    try:
        fn()
        raise AssertionError(f"Expected {exc_type.__name__} but no exception raised")
    except exc_type as e:
        if match and match not in str(e):
            raise AssertionError(f"Exception message {str(e)!r} does not contain {match!r}")


# ── 정상 파싱 ──────────────────────────────────────────────────────────────────

def test_parse_entry():
    result = parse_analysis_result(_make_json(classification="entry"))
    assert isinstance(result, AnalysisResult)
    assert result.classification == "entry"
    assert result.confidence == 0.85
    assert result.pattern == "flat_base"
    assert result.risk_flags == []


def test_parse_watch():
    result = parse_analysis_result(_make_json(classification="watch", confidence=0.40))
    assert result.classification == "watch"


def test_parse_ignore():
    result = parse_analysis_result(_make_json(classification="ignore"))
    assert result.classification == "ignore"


def test_parse_with_risk_flags():
    # v2 taxonomy flags
    result = parse_analysis_result(_make_json(risk_flags=["climax_run", "extended_from_ma"]))
    assert "climax_run" in result.risk_flags
    assert "extended_from_ma" in result.risk_flags


def test_parse_all_valid_patterns():
    # v2 pattern names: cup_with_handle and vcp (not cup_handle / VCP)
    for pattern in ("flat_base", "cup_with_handle", "vcp", "double_bottom", "none"):
        result = parse_analysis_result(_make_json(pattern=pattern))
        assert result.pattern == pattern


def test_parse_strips_leftover_fences():
    wrapped = "```json\n" + _make_json() + "\n```"
    result = parse_analysis_result(wrapped)
    assert result.classification == "entry"


# ── 파싱 실패 ─────────────────────────────────────────────────────────────────

def test_invalid_json_raises():
    _assert_raises(lambda: parse_analysis_result("not json at all"), ParseError, "JSON 파싱 실패")


def test_empty_string_raises():
    _assert_raises(lambda: parse_analysis_result(""), ParseError)


def test_invalid_classification_raises():
    _assert_raises(lambda: parse_analysis_result(_make_json(classification="buy")), ParseError)


def test_confidence_out_of_range_raises():
    _assert_raises(lambda: parse_analysis_result(_make_json(confidence=1.5)), ParseError)


def test_invalid_pattern_raises():
    _assert_raises(lambda: parse_analysis_result(_make_json(pattern="w_base")), ParseError, "pattern must be one of")


def test_invalid_risk_flag_raises():
    _assert_raises(lambda: parse_analysis_result(_make_json(risk_flags=["unknown_flag"])), ParseError, "Invalid risk_flags")


def test_missing_required_field_raises():
    data = {"classification": "entry", "confidence": 0.8, "pattern": "none"}
    _assert_raises(lambda: parse_analysis_result(json.dumps(data)), ParseError)


# ── v2 taxonomy 검증 ─────────────────────────────────────────────────────────

def test_v1_flag_high_rs_rating_is_rejected():
    _assert_raises(
        lambda: parse_analysis_result(_make_json(risk_flags=["high_rs_rating"])),
        ParseError, "Invalid risk_flags"
    )


def test_v1_flag_extended_from_ma50_is_rejected():
    _assert_raises(
        lambda: parse_analysis_result(_make_json(risk_flags=["extended_from_ma50"])),
        ParseError, "Invalid risk_flags"
    )


def test_v1_flag_thin_base_is_rejected():
    _assert_raises(
        lambda: parse_analysis_result(_make_json(risk_flags=["thin_base"])),
        ParseError, "Invalid risk_flags"
    )


def test_v1_flag_low_volume_is_rejected():
    _assert_raises(
        lambda: parse_analysis_result(_make_json(risk_flags=["low_volume"])),
        ParseError, "Invalid risk_flags"
    )


def test_v1_pattern_cup_handle_is_rejected():
    _assert_raises(
        lambda: parse_analysis_result(_make_json(pattern="cup_handle")),
        ParseError, "pattern must be one of"
    )


def test_v1_pattern_VCP_uppercase_is_rejected():
    _assert_raises(
        lambda: parse_analysis_result(_make_json(pattern="VCP")),
        ParseError, "pattern must be one of"
    )


def test_etf_mismatch_flag_accepted():
    result = parse_analysis_result(_make_json(
        classification="ignore",
        pattern="none",
        risk_flags=["etf_methodology_mismatch"]
    ))
    assert "etf_methodology_mismatch" in result.risk_flags


def test_reverse_split_distortion_flag_accepted():
    result = parse_analysis_result(_make_json(
        classification="ignore",
        pattern="none",
        risk_flags=["reverse_split_distortion"]
    ))
    assert "reverse_split_distortion" in result.risk_flags


def test_climax_run_flag_accepted():
    result = parse_analysis_result(_make_json(
        classification="ignore",
        pattern="none",
        risk_flags=["climax_run"]
    ))
    assert "climax_run" in result.risk_flags


def test_all_twelve_v2_flags_individually_valid():
    for flag in VALID_RISK_FLAGS:
        result = parse_analysis_result(_make_json(pattern="none", risk_flags=[flag]))
        assert flag in result.risk_flags, f"Flag '{flag}' was rejected but should be valid"


def test_all_five_v2_patterns_individually_valid():
    for pattern in VALID_PATTERNS:
        result = parse_analysis_result(_make_json(pattern=pattern))
        assert result.pattern == pattern, f"Pattern '{pattern}' was rejected but should be valid"


def test_etf_ignore_full_response_parses():
    etf_response = json.dumps({
        "classification": "ignore",
        "confidence": 1.0,
        "reasoning": "ETF — Minervini/O'Neil methodology targets individual leadership stocks. Recommend upstream screener filter.",
        "pattern": "none",
        "risk_flags": ["etf_methodology_mismatch"],
    })
    result = parse_analysis_result(etf_response)
    assert result.classification == "ignore"
    assert result.confidence == 1.0
    assert result.risk_flags == ["etf_methodology_mismatch"]


if __name__ == "__main__":
    tests = [
        test_parse_entry, test_parse_watch, test_parse_ignore,
        test_parse_with_risk_flags, test_parse_all_valid_patterns,
        test_parse_strips_leftover_fences,
        test_invalid_json_raises, test_empty_string_raises,
        test_invalid_classification_raises, test_confidence_out_of_range_raises,
        test_invalid_pattern_raises, test_invalid_risk_flag_raises,
        test_missing_required_field_raises,
        # v2
        test_v1_flag_high_rs_rating_is_rejected,
        test_v1_flag_extended_from_ma50_is_rejected,
        test_v1_flag_thin_base_is_rejected,
        test_v1_flag_low_volume_is_rejected,
        test_v1_pattern_cup_handle_is_rejected,
        test_v1_pattern_VCP_uppercase_is_rejected,
        test_etf_mismatch_flag_accepted,
        test_reverse_split_distortion_flag_accepted,
        test_climax_run_flag_accepted,
        test_all_twelve_v2_flags_individually_valid,
        test_all_five_v2_patterns_individually_valid,
        test_etf_ignore_full_response_parses,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  FAIL  {t.__name__}: {exc}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
