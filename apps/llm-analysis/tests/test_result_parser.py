"""
result_parser.py + AnalysisResult 단위 테스트.
LLM 호출 없음 — 텍스트 입력으로 파싱만 검증.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

from core.result_parser import ParseError, parse_analysis_result
from models.analysis_result import AnalysisResult


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
    result = parse_analysis_result(_make_json(risk_flags=["high_rs_rating", "extended_from_ma50"]))
    assert "high_rs_rating" in result.risk_flags
    assert "extended_from_ma50" in result.risk_flags


def test_parse_all_valid_patterns():
    for pattern in ("flat_base", "VCP", "cup_handle", "double_bottom", "none"):
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


if __name__ == "__main__":
    tests = [
        test_parse_entry, test_parse_watch, test_parse_ignore,
        test_parse_with_risk_flags, test_parse_all_valid_patterns,
        test_parse_strips_leftover_fences,
        test_invalid_json_raises, test_empty_string_raises,
        test_invalid_classification_raises, test_confidence_out_of_range_raises,
        test_invalid_pattern_raises, test_invalid_risk_flag_raises,
        test_missing_required_field_raises,
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
