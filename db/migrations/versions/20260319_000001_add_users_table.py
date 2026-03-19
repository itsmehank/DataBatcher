"""add users table for authentication

Revision ID: 20260319_000001
Revises: 20260313_000001
Create Date: 2026-03-19 12:00:00
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260319_000001"
down_revision = "20260313_000001"
branch_labels = None
depends_on = None

_USERS_DDL = """\
CREATE TABLE IF NOT EXISTS users (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  username            VARCHAR(64)     NOT NULL,
  password_hash       VARCHAR(255)    NOT NULL,
  role                VARCHAR(16)     NOT NULL DEFAULT 'viewer'
                      COMMENT 'viewer | editor',
  is_active           TINYINT(1)      NOT NULL DEFAULT 1,
  created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                      ON UPDATE CURRENT_TIMESTAMP,
  last_login_at       DATETIME        NULL,
  failed_login_count  INT UNSIGNED    NOT NULL DEFAULT 0,
  locked_until        DATETIME        NULL,
  password_changed_at DATETIME        NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username),
  CONSTRAINT chk_user_role CHECK (role IN ('viewer', 'editor'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
"""


def upgrade() -> None:
    op.execute(_USERS_DDL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users")
