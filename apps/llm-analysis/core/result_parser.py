"""
LLM 응답 → Pydantic 모델 변환·검증.

책임:
  - JSON 파싱 (markdown fence는 anthropic_client가 이미 제거)
  - AnalysisResult / EntryParams 스키마 검증
  - 파싱/검증 실패 시 ParseError 발생 (호출자가 재시도 결정)
"""
from __future__ import annotations

import json
import re


class ParseError(Exception):
    """JSON 파싱 또는 스키마 검증 실패."""


def _extract_json_dict(text: str) -> dict:
    """LLM 응답 텍스트에서 JSON dict를 추출한다. fence 제거 + 파싱."""
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

    return data


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

    data = _extract_json_dict(text)

    try:
        return AnalysisResult(**data)
    except (ValidationError, TypeError) as exc:
        raise ParseError(f"스키마 검증 실패: {exc}") from exc


def parse_entry_params_response(text: str):
    """
    LLM 텍스트 응답을 EntryParams로 파싱·검증한다.

    프롬프트는 known_warnings + other_warnings 두 키를 분리 출력하도록 명시되어 있다.
    LLM이 단일 parameter_warnings 키로 출력한 경우 (실수) 자동 분기 처리:
      - whitelist 코드와 일치하면 known_warnings로
      - 그 외 자유 텍스트는 other_warnings로
    이 fallback은 파싱 robustness 보장용이며, 정상 출력은 두 키를 분리해야 한다.

    Args:
        text: LLM 응답 텍스트 (markdown fence 없음).

    Returns:
        EntryParams 인스턴스.

    Raises:
        ParseError: JSON 파싱 실패 또는 스키마 검증 실패.
    """
    from models.entry_params import EntryParams, VALID_KNOWN_WARNINGS
    from pydantic import ValidationError

    data = _extract_json_dict(text)

    # parameter_warnings (legacy/실수) → known + other 자동 분기
    if "parameter_warnings" in data and "known_warnings" not in data and "other_warnings" not in data:
        legacy = data.pop("parameter_warnings")
        if not isinstance(legacy, list):
            raise ParseError(
                f"legacy parameter_warnings는 list여야 함, got {type(legacy).__name__}"
            )
        known: list[str] = []
        other: list[str] = []
        for item in legacy:
            if isinstance(item, str) and item in VALID_KNOWN_WARNINGS:
                known.append(item)
            elif isinstance(item, str):
                other.append(item)
            else:
                raise ParseError(
                    f"parameter_warnings 항목이 string이 아님: {type(item).__name__}"
                )
        data["known_warnings"] = known
        data["other_warnings"] = other

    # known_warnings/other_warnings 누락 시 빈 list 기본값
    data.setdefault("known_warnings", [])
    data.setdefault("other_warnings", [])

    try:
        return EntryParams(**data)
    except (ValidationError, TypeError) as exc:
        raise ParseError(f"EntryParams 스키마 검증 실패: {exc}") from exc
