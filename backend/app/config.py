from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env_files() -> None:
    here = Path(__file__).resolve()
    backend_root = here.parents[1]
    repo_root = here.parents[3]

    load_dotenv(backend_root / ".env", override=False)
    load_dotenv(repo_root / ".env", override=False)


_load_env_files()


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "")
        self.allowed_origins = [
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ]

        if not self.database_url:
            raise ValueError("DATABASE_URL is required")


settings = Settings()
