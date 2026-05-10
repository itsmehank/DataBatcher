"""
입력 페이로드 → LLM 프롬프트 문자열 직렬화.

책임:
  - prompts/*.md 템플릿 로드
  - payload dict → JSON 직렬화
  - 템플릿 + 페이로드 결합 → 최종 프롬프트 문자열
"""
from __future__ import annotations

import json
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_template(name: str, version: str) -> str:
    """prompts/{name}_{version}.md 파일을 읽어 반환한다."""
    path = _PROMPTS_DIR / f"{name}_{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"프롬프트 파일 없음: {path}")
    return path.read_text(encoding="utf-8")


def build_analyze_chart_prompt(payload: dict, settings: dict) -> str:
    """
    analyze_chart() 호출용 프롬프트를 생성한다.

    Args:
        payload:  data_loader.load_symbol_payload() 반환 dict.
        settings: settings.yaml 내용.

    Returns:
        최종 프롬프트 문자열 (템플릿 + JSON 페이로드).
    """
    version = settings.get("prompts", {}).get("analyze_chart", "v1")
    template = _load_template("analyze_chart", version)
    payload_json = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    return f"{template}\n\n```json\n{payload_json}\n```"


def build_entry_params_prompt(payload: dict, prior_analysis: dict, settings: dict) -> str:
    """
    calculate_entry_params() 호출용 프롬프트를 생성한다.

    Args:
        payload:        data_loader.load_symbol_payload() 반환 dict.
        prior_analysis: AnalysisResult.model_dump() 결과.
        settings:       settings.yaml 내용.

    Returns:
        최종 프롬프트 문자열.
    """
    version = settings.get("prompts", {}).get("calculate_entry_params", "v1")
    template = _load_template("calculate_entry_params", version)

    combined = dict(payload)
    combined["prior_analysis"] = prior_analysis

    payload_json = json.dumps(combined, indent=2, ensure_ascii=False, default=str)
    return f"{template}\n\n```json\n{payload_json}\n```"
