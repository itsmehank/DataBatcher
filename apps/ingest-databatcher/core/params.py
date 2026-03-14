# core/params.py
from __future__ import annotations
import hashlib
import json
from typing import Dict, Any


def params_hash(name: str, params: Dict[str, Any]) -> str:
    payload = json.dumps({"name": name, "params": params}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()
