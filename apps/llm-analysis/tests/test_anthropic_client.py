"""
anthropic_client.py 단위 테스트.

LLM 호출 없이 _strip_markdown_fences(), LLMResponse 모델, ClaudeCodeCLIBackend
초기화 및 subprocess cwd 전달을 검증한다.
ClaudeCodeCLIBackend.call() 통합 테스트는 1.1.13 표본 호출 단계에서 수행.
"""
import sys
import os
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.anthropic_client import (
    AnthropicAPIBackend,
    ClaudeCodeCLIBackend,
    LLMResponse,
    get_backend,
    _strip_markdown_fences,
)


# ── _strip_markdown_fences ──────────────────────────────────────────────────

def test_strip_json_fence():
    raw = '```json\n{"key": "value"}\n```'
    assert _strip_markdown_fences(raw) == '{"key": "value"}'


def test_strip_plain_fence():
    raw = '```\n{"key": "value"}\n```'
    assert _strip_markdown_fences(raw) == '{"key": "value"}'


def test_no_fence_passthrough():
    raw = '{"key": "value"}'
    assert _strip_markdown_fences(raw) == '{"key": "value"}'


def test_strip_trims_whitespace():
    raw = '  ```json\n{"key": "value"}\n```  '
    assert _strip_markdown_fences(raw) == '{"key": "value"}'


def test_multiline_json_fence():
    raw = '```json\n{\n  "a": 1,\n  "b": 2\n}\n```'
    assert _strip_markdown_fences(raw) == '{\n  "a": 1,\n  "b": 2\n}'


# ── LLMResponse 모델 ─────────────────────────────────────────────────────────

def test_llmresponse_minimal():
    r = LLMResponse(
        text="hello",
        model="claude-sonnet-4-6",
        duration_ms=500,
        request_payload={"prompt": "hi"},
    )
    assert r.text == "hello"
    assert r.cost_usd is None
    assert r.error is None
    assert r.prompt_tokens is None


def test_llmresponse_full():
    r = LLMResponse(
        text='{"signal": "BUY"}',
        model="claude-sonnet-4-6",
        prompt_tokens=15730,
        completion_tokens=42,
        cost_usd=0.005348,
        duration_ms=2100,
        request_payload={
            "prompt": "...",
            "model": "claude-sonnet-4-6",
            "cost_source": "cli_reference",
            "max_plan_billing": True,
            "token_source": "cli_json",
        },
        response_payload={"is_error": False},
        error=None,
    )
    assert r.cost_usd == 0.005348
    assert r.prompt_tokens == 15730
    assert r.completion_tokens == 42
    assert r.error is None


def test_llmresponse_error_state():
    r = LLMResponse(
        text="",
        model="claude-sonnet-4-6",
        duration_ms=100,
        request_payload={},
        error="CLI timeout after 60s",
    )
    assert r.error is not None
    assert r.text == ""


# ── ClaudeCodeCLIBackend 초기화 ───────────────────────────────────────────────

def test_cli_backend_cwd_is_tempdir():
    backend = ClaudeCodeCLIBackend()
    assert backend._cwd == tempfile.gettempdir()


def test_cli_backend_cwd_passed_to_subprocess():
    backend = ClaudeCodeCLIBackend(timeout_seconds=30)
    fake_result = MagicMock()
    fake_result.stdout = '{"type":"result","subtype":"success","is_error":false,"result":"{\\"signal\\":\\"ok\\"}","duration_ms":100,"total_cost_usd":0.001,"usage":{"input_tokens":10,"cache_read_input_tokens":0,"cache_creation_input_tokens":0,"output_tokens":5},"modelUsage":{}}'
    fake_result.returncode = 0

    with patch("subprocess.run", return_value=fake_result) as mock_run:
        backend.call(prompt="test prompt", model="claude-sonnet-4-6", max_tokens=100)
        _, kwargs = mock_run.call_args
        assert kwargs.get("cwd") == tempfile.gettempdir()


# ── AnthropicAPIBackend 초기화 ────────────────────────────────────────────────

def test_api_backend_empty_api_key_raises():
    try:
        AnthropicAPIBackend(api_key="")
        assert False, "ValueError expected"
    except ValueError:
        pass


def test_api_backend_none_api_key_raises():
    try:
        AnthropicAPIBackend(api_key=None)
        assert False, "ValueError expected"
    except (ValueError, TypeError):
        pass


# ── get_backend factory ───────────────────────────────────────────────────────

def test_get_backend_cli():
    config = {"llm_analysis": {"backend": "cli"}}
    backend = get_backend(config)
    assert isinstance(backend, ClaudeCodeCLIBackend)


def test_get_backend_api_no_key_raises():
    config = {"llm_analysis": {"backend": "api"}}
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            get_backend(config)
            assert False, "EnvironmentError expected"
        except EnvironmentError:
            pass


def test_get_backend_api_with_key():
    config = {
        "llm_analysis": {"backend": "api"},
        "anthropic": {"temperature": 0, "timeout_seconds": 30},
    }
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"}):
        with patch("core.anthropic_client.anthropic_sdk.Anthropic"):
            backend = get_backend(config)
            assert isinstance(backend, AnthropicAPIBackend)


def test_get_backend_unknown_raises():
    config = {"llm_analysis": {"backend": "unknown_backend"}}
    try:
        get_backend(config)
        assert False, "ValueError expected"
    except ValueError:
        pass


if __name__ == "__main__":
    tests = [
        test_strip_json_fence,
        test_strip_plain_fence,
        test_no_fence_passthrough,
        test_strip_trims_whitespace,
        test_multiline_json_fence,
        test_llmresponse_minimal,
        test_llmresponse_full,
        test_llmresponse_error_state,
        test_cli_backend_cwd_is_tempdir,
        test_cli_backend_cwd_passed_to_subprocess,
        test_api_backend_empty_api_key_raises,
        test_api_backend_none_api_key_raises,
        test_get_backend_cli,
        test_get_backend_api_no_key_raises,
        test_get_backend_api_with_key,
        test_get_backend_unknown_raises,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
