"""prompt_builder.py 단위 테스트."""
from __future__ import annotations

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.prompt_builder import build_analyze_chart_prompt, build_entry_params_prompt


def _minimal_payload() -> dict:
    return {
        "task": "minervini_chart_analysis",
        "symbol": "TEST",
        "market": "NASDAQ",
        "date": "2026-04-25",
        "rs_rating": 89.0,
        "current_metrics": {"close": 100.0},
        "daily_ohlcv": [],
        "weekly_ohlcv": [],
        "indicators_recent": [],
    }


def _default_settings() -> dict:
    return {"prompts": {"analyze_chart": "v1", "calculate_entry_params": "v1"}}


def test_analyze_chart_prompt_contains_template():
    prompt = build_analyze_chart_prompt(_minimal_payload(), _default_settings())
    assert "Mark Minervini" in prompt
    assert "entry|watch|ignore" in prompt


def test_analyze_chart_prompt_contains_payload_json():
    payload = _minimal_payload()
    prompt = build_analyze_chart_prompt(payload, _default_settings())
    assert '"symbol": "TEST"' in prompt
    assert '"task": "minervini_chart_analysis"' in prompt


def test_analyze_chart_prompt_ends_with_json_block():
    prompt = build_analyze_chart_prompt(_minimal_payload(), _default_settings())
    assert prompt.rstrip().endswith("```")


def test_entry_params_prompt_contains_prior_analysis():
    payload = _minimal_payload()
    prior = {"classification": "entry", "confidence": 0.8, "pattern": "flat_base", "reasoning": "Good base."}
    prompt = build_entry_params_prompt(payload, prior, _default_settings())
    assert "prior_analysis" in prompt
    assert "entry" in prompt


def test_entry_params_prompt_contains_payload():
    payload = _minimal_payload()
    prior = {"classification": "entry", "confidence": 0.75, "pattern": "VCP", "reasoning": "VCP."}
    prompt = build_entry_params_prompt(payload, prior, _default_settings())
    assert '"symbol": "TEST"' in prompt
    assert '"pattern": "VCP"' in prompt


if __name__ == "__main__":
    tests = [
        test_analyze_chart_prompt_contains_template,
        test_analyze_chart_prompt_contains_payload_json,
        test_analyze_chart_prompt_ends_with_json_block,
        test_entry_params_prompt_contains_prior_analysis,
        test_entry_params_prompt_contains_payload,
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
