"""
LLMBackend 추상화 인터페이스 + ClaudeCodeCLIBackend / AnthropicAPIBackend 구현체.

ADR-011 §2: 호출자는 백엔드 구현을 알지 못하며, settings.yaml의
llm_analysis.backend 값("cli" | "api")으로 런타임에 선택된다.

ADR-011 §3 갱신 (Phase 1.1): CLI 모드에서 --output-format json이 total_cost_usd를
반환하므로 참고값으로 저장. Max 플랜 실제 청구액 아님 — request_payload에 메타 명시.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from typing import Optional

import anthropic as anthropic_sdk
from pydantic import BaseModel


class LLMResponse(BaseModel):
    text: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    duration_ms: int
    request_payload: dict
    response_payload: Optional[dict] = None
    error: Optional[str] = None


class LLMBackend:
    """Protocol-style base class. 호출자는 이 인터페이스만 사용한다."""

    def call(self, prompt: str, model: str, max_tokens: int) -> LLMResponse:
        raise NotImplementedError


def _strip_markdown_fences(text: str) -> str:
    """````json ... ```` 또는 ```` ``` ... ```` 펜스를 제거하고 내용만 반환."""
    stripped = text.strip()
    for prefix in ("```json\n", "```\n"):
        if stripped.startswith(prefix) and stripped.endswith("\n```"):
            return stripped[len(prefix) : -4].strip()
        if stripped.startswith(prefix) and stripped.endswith("```"):
            return stripped[len(prefix) : -3].strip()
    return stripped


class ClaudeCodeCLIBackend(LLMBackend):
    """
    claude CLI (-p) 를 subprocess로 호출하는 백엔드.

    ADR-011 §3: Max 플랜 OAuth 세션 사용. --bare 미사용.
    max_tokens 파라미터는 CLI가 지원하지 않아 무시됨 (API 백엔드와의 인터페이스 통일 목적).
    """

    def __init__(self, temperature: int = 0, timeout_seconds: int = 60) -> None:
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        # CLI는 cwd 및 상위 디렉토리를 탐색해 CLAUDE.md/메모리를 자동 로드한다.
        # 시스템 temp에서 실행하면 프로젝트 컨텍스트를 차단하고 토큰 ~49% 절감.
        # (진단 근거: Phase 1.1.4-b, ADR-012 §3.2 토큰 폭증 안전망 전제)
        self._cwd = tempfile.gettempdir()

    def call(self, prompt: str, model: str, max_tokens: int) -> LLMResponse:
        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--tools", "",
            "--model", model,
        ]

        request_payload = {
            "prompt": prompt,
            "model": model,
            "cost_source": "cli_reference",
            "max_plan_billing": True,
            "token_source": "cli_json",
        }

        wall_start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout_seconds,
                cwd=self._cwd,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - wall_start) * 1000)
            return LLMResponse(
                text="",
                model=model,
                duration_ms=duration_ms,
                request_payload=request_payload,
                error=f"CLI timeout after {self.timeout_seconds}s",
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - wall_start) * 1000)
            return LLMResponse(
                text="",
                model=model,
                duration_ms=duration_ms,
                request_payload=request_payload,
                error=f"subprocess error: {exc}",
            )

        duration_ms = int((time.monotonic() - wall_start) * 1000)

        try:
            cli_json: dict = json.loads(proc.stdout.strip())
        except json.JSONDecodeError:
            return LLMResponse(
                text="",
                model=model,
                duration_ms=duration_ms,
                request_payload=request_payload,
                response_payload=None,
                error=f"JSON parse error — stdout: {proc.stdout[:200]!r}",
            )

        if cli_json.get("is_error") or proc.returncode != 0:
            return LLMResponse(
                text="",
                model=model,
                duration_ms=duration_ms,
                request_payload=request_payload,
                response_payload=cli_json,
                error=cli_json.get("result", f"CLI error (rc={proc.returncode})"),
            )

        raw_text = cli_json.get("result", "")
        text = _strip_markdown_fences(raw_text)

        try:
            usage = cli_json.get("usage", {})
            prompt_tokens = (
                (usage.get("input_tokens") or 0)
                + (usage.get("cache_read_input_tokens") or 0)
                + (usage.get("cache_creation_input_tokens") or 0)
            )
            completion_tokens = usage.get("output_tokens")
        except Exception:
            prompt_tokens = None
            completion_tokens = None

        try:
            cost_usd = cli_json.get("total_cost_usd")
            if cost_usd is not None:
                cost_usd = float(cost_usd)
        except Exception:
            cost_usd = None

        return LLMResponse(
            text=text,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            request_payload=request_payload,
            response_payload=cli_json,
        )


class AnthropicAPIBackend(LLMBackend):
    """
    Anthropic Python SDK를 통한 API 직접 호출 백엔드.

    ADR-011 §3: prompt_tokens, completion_tokens, cost_usd 모두 정확값.
    pricing 미설정 시 cost_usd=None 반환.
    """

    def __init__(
        self,
        api_key: str,
        temperature: float = 0,
        timeout_seconds: int = 60,
        pricing: dict | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("AnthropicAPIBackend: api_key가 비어있음.")
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.pricing = pricing
        self._client = anthropic_sdk.Anthropic(api_key=api_key, timeout=timeout_seconds)

    def call(self, prompt: str, model: str, max_tokens: int) -> LLMResponse:
        request_payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "token_source": "anthropic_api",
            "cost_source": "anthropic_api_calculated",
        }

        wall_start = time.monotonic()
        try:
            resp = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic_sdk.APIError as exc:
            duration_ms = int((time.monotonic() - wall_start) * 1000)
            return LLMResponse(
                text="",
                model=model,
                duration_ms=duration_ms,
                request_payload=request_payload,
                error=f"anthropic APIError: {exc}",
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - wall_start) * 1000)
            return LLMResponse(
                text="",
                model=model,
                duration_ms=duration_ms,
                request_payload=request_payload,
                error=f"unexpected error: {exc}",
            )

        duration_ms = int((time.monotonic() - wall_start) * 1000)

        raw_text = resp.content[0].text if resp.content else ""
        text = _strip_markdown_fences(raw_text)

        input_tokens = resp.usage.input_tokens
        output_tokens = resp.usage.output_tokens

        cost_usd: Optional[float] = None
        if self.pricing:
            try:
                cost_usd = (
                    input_tokens / 1000 * self.pricing["input_per_1k_tokens"]
                    + output_tokens / 1000 * self.pricing["output_per_1k_tokens"]
                )
            except (KeyError, TypeError):
                pass

        try:
            response_payload = {
                "id": resp.id,
                "type": resp.type,
                "model": resp.model,
                "role": resp.role,
                "content": [{"type": b.type, "text": b.text} for b in resp.content],
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
                "stop_reason": resp.stop_reason,
            }
        except Exception:
            response_payload = {"raw": str(resp)}

        return LLMResponse(
            text=text,
            model=model,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            request_payload=request_payload,
            response_payload=response_payload,
        )


def get_backend(config: dict) -> LLMBackend:
    """
    settings.yaml 전체 dict를 받아 LLMBackend 구현체를 반환한다.

    Args:
        config: load_settings()가 반환한 전체 dict.

    Raises:
        ValueError: 알 수 없는 backend 값.
        EnvironmentError: backend='api'인데 ANTHROPIC_API_KEY 미설정.
    """
    backend_type = config.get("llm_analysis", {}).get("backend", "cli")
    anthropic_cfg = config.get("anthropic", {})
    temperature = anthropic_cfg.get("temperature", 0)
    timeout_seconds = anthropic_cfg.get("timeout_seconds", 60)

    if backend_type == "cli":
        return ClaudeCodeCLIBackend(
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
    elif backend_type == "api":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "backend='api' requires ANTHROPIC_API_KEY environment variable."
            )
        return AnthropicAPIBackend(
            api_key=api_key,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            pricing=anthropic_cfg.get("pricing"),
        )
    else:
        raise ValueError(f"Unknown backend: '{backend_type}'. Expected 'cli' or 'api'.")
