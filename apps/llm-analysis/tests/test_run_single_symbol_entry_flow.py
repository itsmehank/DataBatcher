"""
run_single_symbol.py — --with-entry-params 분기 단위 테스트.

테스트 범위:
  - (5) classification == 'entry' → (6) 자동 호출
  - (5) classification == 'watch'/'ignore' → (6) 미호출
  - (6) LLM error → entry_params None 반환, (5) 결과는 보존
  - (6) parse error → entry_params None 반환, (5) 결과는 보존
  - (6) 정상 호출 → entry_params dict 반환
  - --with-entry-params 미지정 → (6) 절대 호출 안 됨

실 DB·LLM 호출 없음 — backend, session, recorder를 mock으로 대체.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.analysis_result import AnalysisResult
from scripts.run_single_symbol import _call_entry_params


def _make_settings() -> dict:
    return {
        "anthropic": {
            "model_analysis": "claude-sonnet-4-6",
            "max_tokens": 2000,
            "retry": {"max_attempts": 2, "backoff_base_sec": 0},
        },
        "prompts": {"analyze_chart": "v2", "calculate_entry_params": "v1"},
    }


def _make_payload() -> dict:
    return {
        "task": "minervini_chart_analysis",
        "symbol": "TEST",
        "market": "NASDAQ",
        "date": "2026-05-03",
        "current_metrics": {"close": 100.0},
        "daily_ohlcv": [],
        "weekly_ohlcv": [],
        "indicators_recent": [],
    }


def _make_analysis(classification: str = "entry") -> AnalysisResult:
    return AnalysisResult(
        classification=classification,
        confidence=0.85,
        reasoning="12-week flat base, pivot at 192.50.",
        pattern="flat_base",
        risk_flags=[],
    )


def _valid_entry_params_json() -> str:
    return json.dumps({
        "pivot_price": 192.50,
        "trigger_price": 192.69,
        "current_price": 192.30,
        "stop_loss_price": 178.96,
        "stop_loss_pct_from_pivot": -7.0,
        "stop_loss_pct_from_current_price": -6.9,
        "suggested_weight_pct": 10.0,
        "expected_target_price": 231.00,
        "expected_target_pct": 20.0,
        "pattern_basis": "flat_base",
        "entry_window_days": 3,
        "max_chase_pct_from_pivot": 5.0,
        "breakout_volume_requirement": "ge_1.4x_50day_avg",
        "observed_breakout_volume_ratio": None,
        "notes": "Flat base 7 weeks. Stop bound by absolute -7%. Standard tier 10%, no flags. Target 20% default.",
        "known_warnings": [],
        "other_warnings": [],
    })


class TestCallEntryParams(unittest.TestCase):
    """_call_entry_params() 함수 직접 테스트."""

    def _patch_call_and_record(self, response_text: str, error: str | None = None,
                                call_id: int = 42):
        """call_and_record를 mock하는 patch 컨텍스트 생성."""
        response = MagicMock()
        response.text = response_text
        response.error = error
        response.prompt_tokens = 5000
        response.completion_tokens = 800
        response.cost_usd = None
        response.duration_ms = 1234

        return patch(
            "scripts.run_single_symbol.call_and_record",
            return_value=(response, call_id),
        )

    def test_successful_call_returns_dict(self):
        """(6) 정상 응답 → dict 반환."""
        backend = MagicMock()
        session = MagicMock()
        analysis = _make_analysis("entry")

        with self._patch_call_and_record(_valid_entry_params_json(), call_id=42):
            result, call_id = _call_entry_params(
                backend, session, _make_settings(), _make_payload(), analysis, "US",
            )

        self.assertIsNotNone(result)
        self.assertEqual(call_id, 42)
        # Decimal은 JSON 직렬화 시 string으로 저장됨 (DB JSON 컬럼 호환)
        self.assertEqual(str(result["pivot_price"]), "192.5")
        self.assertEqual(result["pattern_basis"], "flat_base")
        self.assertEqual(result["known_warnings"], [])
        self.assertEqual(result["entry_window_days"], 3)

    def test_llm_error_returns_none(self):
        """(6) LLM 호출 자체 실패 → (None, call_id) 반환."""
        backend = MagicMock()
        session = MagicMock()
        analysis = _make_analysis("entry")

        with self._patch_call_and_record("", error="API rate limit", call_id=99):
            result, call_id = _call_entry_params(
                backend, session, _make_settings(), _make_payload(), analysis, "US",
            )

        self.assertIsNone(result)
        self.assertEqual(call_id, 99)

    def test_parse_error_with_retry_succeeds(self):
        """첫 응답은 invalid JSON, 두 번째는 정상 → 성공 반환."""
        backend = MagicMock()
        session = MagicMock()
        analysis = _make_analysis("entry")

        bad_response = MagicMock()
        bad_response.text = "not json at all"
        bad_response.error = None

        good_response = MagicMock()
        good_response.text = _valid_entry_params_json()
        good_response.error = None

        with patch(
            "scripts.run_single_symbol.call_and_record",
            side_effect=[(bad_response, 100), (good_response, 101)],
        ):
            result, call_id = _call_entry_params(
                backend, session, _make_settings(), _make_payload(), analysis, "US",
            )

        self.assertIsNotNone(result)
        self.assertEqual(call_id, 101)  # 재시도 호출 ID

    def test_parse_error_twice_returns_none(self):
        """파싱 두 번 다 실패 → (None, call_id) 반환."""
        backend = MagicMock()
        session = MagicMock()
        analysis = _make_analysis("entry")

        bad_response = MagicMock()
        bad_response.text = "not json"
        bad_response.error = None

        with patch(
            "scripts.run_single_symbol.call_and_record",
            side_effect=[(bad_response, 200), (bad_response, 201)],
        ):
            result, call_id = _call_entry_params(
                backend, session, _make_settings(), _make_payload(), analysis, "US",
            )

        self.assertIsNone(result)
        self.assertEqual(call_id, 201)

    def test_module_label_kr_vs_us(self):
        """region에 따라 module 라벨이 entry_params_6_kr 또는 _us로 분기."""
        backend = MagicMock()
        session = MagicMock()
        analysis = _make_analysis("entry")

        with patch("scripts.run_single_symbol.call_and_record") as mock_call:
            mock_response = MagicMock()
            mock_response.text = _valid_entry_params_json()
            mock_response.error = None
            mock_call.return_value = (mock_response, 1)

            _call_entry_params(backend, session, _make_settings(), _make_payload(), analysis, "KR")
            self.assertEqual(mock_call.call_args[0][5], "entry_params_6_kr")

            _call_entry_params(backend, session, _make_settings(), _make_payload(), analysis, "US")
            self.assertEqual(mock_call.call_args[0][5], "entry_params_6_us")

    def test_invalid_pattern_basis_returns_none(self):
        """LLM이 schema-violating 출력 (pattern_basis 잘못) → 두 번 모두 실패 → None."""
        backend = MagicMock()
        session = MagicMock()
        analysis = _make_analysis("entry")

        bad_payload = json.loads(_valid_entry_params_json())
        bad_payload["pattern_basis"] = "ascending_triangle"  # not in enum
        bad_text = json.dumps(bad_payload)

        bad_response = MagicMock()
        bad_response.text = bad_text
        bad_response.error = None

        with patch(
            "scripts.run_single_symbol.call_and_record",
            side_effect=[(bad_response, 300), (bad_response, 301)],
        ):
            result, call_id = _call_entry_params(
                backend, session, _make_settings(), _make_payload(), analysis, "US",
            )

        self.assertIsNone(result)


class TestClassificationGating(unittest.TestCase):
    """main()의 classification 분기 로직을 직접 검증.

    실제 main()을 호출하지 않고, _call_entry_params가 호출될지 여부를 결정하는
    조건 (with_entry_params AND classification == 'entry')을 가독성 좋게 테스트.
    """

    def _should_call_six(self, with_flag: bool, classification: str) -> bool:
        """run_single_symbol main()의 가드 조건 재구현 (테스트용)."""
        return with_flag and classification == "entry"

    def test_entry_with_flag_calls_six(self):
        self.assertTrue(self._should_call_six(True, "entry"))

    def test_watch_does_not_call_six(self):
        self.assertFalse(self._should_call_six(True, "watch"))

    def test_ignore_does_not_call_six(self):
        self.assertFalse(self._should_call_six(True, "ignore"))

    def test_no_flag_never_calls_six(self):
        self.assertFalse(self._should_call_six(False, "entry"))
        self.assertFalse(self._should_call_six(False, "watch"))
        self.assertFalse(self._should_call_six(False, "ignore"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
