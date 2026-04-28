"""
LLM 응답 → AnalysisResult 변환 및 Pydantic 검증.

책임:
  - JSON 파싱 (markdown fence는 anthropic_client가 이미 제거)
  - AnalysisResult 스키마 검증
  - 파싱/검증 실패 시 ParseError 발생 (호출자가 재시도 결정)
"""
from __future__ import annotations

import json
import re


class ParseError(Exception):
    """JSON 파싱 또는 스키마 검증 실패."""


def parse_analysis_result(text: str):
    """
    LLM 텍스트 응답을 AnalysisResult로 파싱·검증한다.

    Args:
        text: LLM 응답 텍스트 (markdown fence 없음 — anthropic_client가 제거).

    Returns:
        AnalysisResult 인스턴스.

    Raises:
        ParseError: JSON 파싱 실패 또는 스키마 검증 실패.
    """
    from models.analysis_result import AnalysisResult
    from pydantic import ValidationError

    stripped = text.strip()

    # anthropic_client._strip_markdown_fences 이후에도 혹시 남아있는 fence 재제거
    stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.MULTILINE)
    stripped = re.sub(r"\s*```$", "", stripped, flags=re.MULTILINE)
    stripped = stripped.strip()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ParseError(f"JSON 파싱 실패: {exc}. 원문(앞 200자): {stripped[:200]!r}") from exc

    if not isinstance(data, dict):
        raise ParseError(f"응답이 JSON 객체가 아님: {type(data).__name__}")

    try:
        return AnalysisResult(**data)
    except (ValidationError, TypeError) as exc:
        raise ParseError(f"스키마 검증 실패: {exc}") from exc
