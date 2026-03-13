"""baseline schema

Revision ID: 20260313_000001
Revises:
Create Date: 2026-03-13 16:15:00
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260313_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Baseline revision.

    현재 스키마는 `scripts/init_db.py` / `01_schema.sql`이 생성한다.
    이 baseline은 Alembic 이력 시작점을 고정하기 위한 용도다.
    """
    pass


def downgrade() -> None:
    pass
