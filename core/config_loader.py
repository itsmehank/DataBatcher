# core/config_loader.py
from __future__ import annotations
import os
import yaml
from typing import Any, Dict, Optional, Callable

# .env 자동 로드(선택)
try:
    from dotenv import load_dotenv as _load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    _load_dotenv = None  # type: ignore

# mypy/IDE 타입 경고 방지용 래퍼
load_dotenv: Optional[Callable[..., bool]] = _load_dotenv  # type: ignore[assignment]


def _load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge_dict(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def load_settings() -> Dict[str, Any]:
    """Load configuration with the following precedence:
    1) Environment variable DATABASE_URL (overrides database.url)
    2) config/settings.dev.yaml if exists and has include: settings.yaml
    3) config/settings.yaml (base)
    Returns a merged dictionary.
    """
    # Load .env into os.environ if available.
    # - override=False: existing OS env vars win (CI/systemd/exported vars take priority).
    if callable(load_dotenv):
        load_dotenv(override=False)

    base_path = os.path.join("config", "settings.yaml")
    dev_path = os.path.join("config", "settings.dev.yaml")

    cfg: Dict[str, Any] = {}
    if os.path.exists(base_path):
        cfg = _load_yaml(base_path)

    if os.path.exists(dev_path):
        dev = _load_yaml(dev_path)
        # Optional include mechanism
        cfg = merge_dict(cfg, dev)

    # Env override
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        cfg.setdefault("database", {})
        cfg["database"]["url"] = db_url

    return cfg
