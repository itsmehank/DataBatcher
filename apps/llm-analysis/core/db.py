"""
DB 연결 유틸리티 — engine + session factory.

DATABASE_URL 우선순위:
  1. 셸 환경 변수 (이미 설정된 경우)
  2. DataBatcher 루트 .env
  3. apps/llm-analysis/.env

SessionLocal을 모듈 임포트 시점에 생성하지 않음 — DATABASE_URL 미설정 환경에서
임포트 실패를 방지하기 위해 lazy 초기화.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_APP_ROOT = Path(__file__).parent.parent        # apps/llm-analysis/
_REPO_ROOT = _APP_ROOT.parent.parent            # DataBatcher/

# 루트 .env 우선 — 실제 자격증명. 앱 로컬 .env는 루트에 없는 키만 추가.
for _env_path in [_REPO_ROOT / ".env", _APP_ROOT / ".env"]:
    if _env_path.exists():
        load_dotenv(_env_path, override=False)


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise EnvironmentError(
            "DATABASE_URL environment variable not set. "
            "Set it in DataBatcher/.env or apps/llm-analysis/.env."
        )
    return url


def make_engine(database_url: str | None = None):
    """SQLAlchemy Engine을 생성한다."""
    return create_engine(database_url or get_database_url(), pool_pre_ping=True)


def make_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """SQLAlchemy Session factory를 생성한다."""
    engine = make_engine(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)
