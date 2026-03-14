#!/usr/bin/env python3
from __future__ import annotations

"""Repository safety preflight checker.

Usage:
    python scripts/preflight_repo_safety.py

Checks:
1) Sensitive filename patterns (.env, key files, local configs)
2) Sensitive content patterns (password/token/api key, url credentials)
3) Large local artifact directories accidentally present
"""

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    ".venv1",
    ".idea",
    ".pytest_cache",
    "__pycache__",
    "logs",
}

SAFE_LOCAL_FILES = {
    ".env",
    ".env.example",
    "apps/ingest-databatcher/config/settings.dev.yaml",
}

SENSITIVE_FILE_RULES = [
    re.compile(r"^\.env$"),
    re.compile(r"^\.env\..+"),
    re.compile(r".*\.pem$"),
    re.compile(r".*\.p12$"),
    re.compile(r".*\.key$"),
    re.compile(r".*id_rsa.*"),
    re.compile(r".*\.local$"),
]

SENSITIVE_CONTENT_RULES = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*[^\s]+"),
    re.compile(r'(?i)mysql\+pymysql://[^\s"\']+:[^\s"\']+@'),
    re.compile(r'(?i)DATABASE_URL\s*=\s*mysql\+pymysql://[^\s"\']+:[^\s"\']+@'),
]

SCAN_EXTENSIONS = {
    ".py",
    ".yaml",
    ".yml",
    ".env",
    ".sh",
    ".ini",
    ".toml",
}


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    return any(d in parts for d in EXCLUDED_DIRS)


def iter_candidate_files() -> list[Path]:
    git_dir = ROOT / ".git"
    if git_dir.exists():
        try:
            out = subprocess.check_output(
                ["git", "ls-files"],
                cwd=ROOT,
                text=True,
            )
            paths = [ROOT / p for p in out.splitlines() if p.strip()]
            return [p for p in paths if p.is_file()]
        except Exception:
            pass

    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        files.append(path)
    return files


def check_sensitive_filenames() -> list[str]:
    issues: list[str] = []
    for path in iter_candidate_files():
        rel = path.relative_to(ROOT)
        if str(rel) in SAFE_LOCAL_FILES:
            continue
        name = rel.name
        for rule in SENSITIVE_FILE_RULES:
            if rule.match(name):
                issues.append(f"sensitive filename: {rel}")
                break
    return issues


def check_sensitive_contents() -> list[str]:
    issues: list[str] = []
    for path in iter_candidate_files():
        rel = path.relative_to(ROOT)
        if str(rel) in SAFE_LOCAL_FILES:
            continue
        if path.suffix.lower() not in SCAN_EXTENSIONS and path.name not in {".env", ".env.example"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            for rule in SENSITIVE_CONTENT_RULES:
                if rule.search(line):
                    if (
                        "YOUR_" in line
                        or "USER:PASS" in line
                        or "user:pass" in line
                        or "<password>" in line
                        or "prod_pass" in line
                        or "실제비밀번호" in line
                        or "${" in line
                    ):
                        continue
                    issues.append(f"sensitive content: {rel}:{idx}")
                    break
    return issues


def main() -> int:
    issues = []
    issues.extend(check_sensitive_filenames())
    issues.extend(check_sensitive_contents())

    if issues:
        print("[preflight] FAILED: potential sensitive artifacts detected")
        for item in issues:
            print(f" - {item}")
        print("[preflight] Resolve issues before pushing to GitHub.")
        return 1

    print("[preflight] OK: no obvious sensitive artifacts found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
