"""add conditions_met JSON column to minervini screen results

Revision ID: 20260424_000001
Revises: 20260319_000001
Create Date: 2026-04-24 00:00:00

ADR-009: Phase 1 LLM analysis needs to know which Minervini conditions
a stock passed. Adds conditions_met JSON NULL to both KR and US tables.
"""
from __future__ import annotations

from alembic import op

revision = "20260424_000001"
down_revision = "20260319_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE minervini_screen_results_kr
          ADD COLUMN IF NOT EXISTS conditions_met JSON NULL
          COMMENT 'ADR-009: per-condition pass/fail map'
          AFTER is_blue_dot
    """)
    op.execute("""
        ALTER TABLE minervini_screen_results_us
          ADD COLUMN IF NOT EXISTS conditions_met JSON NULL
          COMMENT 'ADR-009: per-condition pass/fail map'
          AFTER is_blue_dot
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE minervini_screen_results_kr DROP COLUMN IF EXISTS conditions_met")
    op.execute("ALTER TABLE minervini_screen_results_us DROP COLUMN IF EXISTS conditions_met")