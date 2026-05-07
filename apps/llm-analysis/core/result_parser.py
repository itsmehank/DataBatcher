"""
LLM 응답 → Pydantic 모델 변환·검증.

책임:
  - JSON 파싱 (markdown fence는 anthropic_client가 이미 제거)
  - AnalysisResult / EntryParams 스키마 검증
  - 파싱/검증 실패 시 ParseError 발생 (호출자가 재시도 결정)
  - v1 (6) 응답 → v1.1 스키마 legacy 매핑 (robustness)
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


def _apply_v1_to_v1_1_legacy_mapping(data: dict) -> None:
    """
    v1 EntryParams 스키마 응답을 v1.1로 매핑한다 (robustness).

    수행 항목:
      1. legacy `stop_loss_pct` → `stop_loss_pct_from_pivot` (rename, v1 → v1.1).
      2. `stop_loss_pct_from_current_price` 누락 + (stop_loss_price + current_price)
         있으면 derive.
      3. `trigger_price` 누락 + pivot_price 있으면 round(pivot * 1.001, 2)로 derive.

    in-place mutation.
    """
    # 1. stop_loss_pct (legacy v1 단일 키) → stop_loss_pct_from_pivot
    if "stop_loss_pct" in data and "stop_loss_pct_from_pivot" not in data:
        data["stop_loss_pct_from_pivot"] = data.pop("stop_loss_pct")

    # 2. stop_loss_pct_from_current_price derive (필요 데이터 있을 때만)
    if "stop_loss_pct_from_current_price" not in data:
        stop_price = data.get("stop_loss_price")
        current_price = data.get("current_price")
        if stop_price is not None and current_price is not None:
            try:
                stop_f = float(stop_price)
                current_f = float(current_price)
                if current_f > 0:
                    pct = (stop_f - current_f) / current_f * 100.0
                    data["stop_loss_pct_from_current_price"] = round(pct, 2)
            except (TypeError, ValueError):
                pass

    # 3. trigger_price derive (pivot 기준 0.1% 버퍼 default)
    if "trigger_price" not in data:
        pivot = data.get("pivot_price")
        if pivot is not None:
            try:
                pivot_f = float(pivot)
                data["trigger_price"] = round(pivot_f * 1.001, 2)
            except (TypeError, ValueError):
                pass


def parse_entry_params_response(text: str):
    """
    LLM 텍스트 응답을 EntryParams (v1.1)로 파싱·검증한다.

    프롬프트 v1.1은 known_warnings + other_warnings 두 키를 분리 출력하도록 명시.
    LLM이 단일 parameter_warnings 키로 출력한 경우 (legacy/실수) 자동 분기 처리:
      - whitelist 코드와 일치하면 known_warnings로
      - 그 외 자유 텍스트는 other_warnings로

    legacy v1 → v1.1 매핑 (Phase 1.3.0 추가):
      - stop_loss_pct (단일) → stop_loss_pct_from_pivot
      - stop_loss_pct_from_current_price 누락 시 (stop_loss_price + current_price)에서 derive
      - trigger_price 누락 시 pivot_price * 1.001에서 derive

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

    # v1 → v1.1 legacy field mapping
    _apply_v1_to_v1_1_legacy_mapping(data)

    # known_warnings/other_warnings 누락 시 빈 list 기본값
    data.setdefault("known_warnings", [])
    data.setdefault("other_warnings", [])

    try:
        return EntryParams(**data)
    except (ValidationError, TypeError) as exc:
        raise ParseError(f"EntryParams 스키마 검증 실패: {exc}") from exc
