# core/config_loader.py
from __future__ import annotations
import os
from pathlib import Path
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


def _candidate_config_paths() -> tuple[list[Path], list[Path]]:
    """Return candidate config paths for base/dev in priority order.

    Supports both:
    - repo root style: apps/ingest-databatcher/config/settings*.yaml
    - app-contained style: apps/ingest-databatcher/apps/ingest-databatcher/config/settings*.yaml
    """
    here = Path(__file__).resolve()
    app_root = here.parents[1]
    repo_root = here.parents[3]

    base_candidates = [
        repo_root / "config" / "settings.yaml",
        app_root / "config" / "settings.yaml",
        Path("apps/ingest-databatcher/config/settings.yaml"),
    ]
    dev_candidates = [
        repo_root / "config" / "settings.dev.yaml",
        app_root / "config" / "settings.dev.yaml",
        Path("apps/ingest-databatcher/config/settings.dev.yaml"),
    ]
    return base_candidates, dev_candidates


def _first_existing(paths: list[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


def load_settings() -> Dict[str, Any]:
    """Load configuration with the following precedence:
    1) Environment variable DATABASE_URL (overrides database.url)
    2) apps/ingest-databatcher/config/settings.dev.yaml if exists and has include: settings.yaml
    3) apps/ingest-databatcher/config/settings.yaml (base)
    Returns a merged dictionary.
    """
    # Load .env into os.environ if available.
    # - override=False: existing OS env vars win (CI/systemd/exported vars take priority).
    if callable(load_dotenv):
        load_dotenv(override=False)

    base_candidates, dev_candidates = _candidate_config_paths()
    base_path = _first_existing(base_candidates)
    dev_path = _first_existing(dev_candidates)

    cfg: Dict[str, Any] = {}
    if base_path is not None:
        cfg = _load_yaml(str(base_path))

    if dev_path is not None:
        dev = _load_yaml(str(dev_path))
        # Optional include mechanism
        cfg = merge_dict(cfg, dev)

    # Env override
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        cfg.setdefault("database", {})
        cfg["database"]["url"] = db_url

    return cfg
