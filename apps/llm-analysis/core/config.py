"""
settings.yaml 로더.

get_backend(), cost_tracker, daily_call_limits 등 여러 모듈이 공유.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml


def load_settings(path: Optional[str] = None) -> dict:
    """
    settings.yaml을 읽어 dict로 반환한다.

    Args:
        path: 명시적 경로. None이면 config/settings.yaml 기본 (이 파일 기준).
    """
    if path is None:
        resolved = Path(__file__).parent.parent / "config" / "settings.yaml"
    else:
        resolved = Path(path)

    with resolved.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
