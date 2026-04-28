"""add daily_analysis_kr, daily_analysis_us, llm_calls tables

Revision ID: 20260428_000001
Revises: 20260424_000001
Create Date: 2026-04-28 00:00:00

ADR-009: Phase 1 LLM 분석 레이어 구축을 위한 신규 테이블 3종.
  - daily_analysis_kr / daily_analysis_us: LLM 차트 분석 결과 저장
    PK(symbol, date), classification/confidence/reasoning/pattern/risk_flags/entry_params
  - llm_calls: 모든 LLM 호출 영구 기록 (헌법 §2.5)

ADR-010: 마이그레이션 3종 산출물 중 ① Alembic 파일.
  ② raw SQL 파일: db/migrations/sql/20260428_000001_add_daily_analysis_and_llm_calls.sql
  ③ 운영 큐 항목: phase1_progress.md "Q-002 등록 대기" 섹션 참조
"""
from __future__ import annotations

from alembic import op

revision = "20260428_000001"
down_revision = "20260424_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS daily_analysis_kr (
          symbol             VARCHAR(32)  NOT NULL,
          date               DATE         NOT NULL,
          market             VARCHAR(16)  NOT NULL,
          classification     VARCHAR(20)  NOT NULL,
          confidence         DECIMAL(3,2) NULL,
          reasoning          TEXT         NULL,
          pattern            VARCHAR(50)  NULL,
          risk_flags         JSON         NULL,
          entry_params       JSON         NULL,
          screen_config_hash CHAR(40)     NULL,
          llm_call_id        BIGINT       NULL,
          created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (symbol, date),
          KEY idx_date_class (date, classification),
          KEY idx_date_market (date, market)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS daily_analysis_us (
          symbol             VARCHAR(32)  NOT NULL,
          date               DATE         NOT NULL,
          market             VARCHAR(16)  NOT NULL,
          classification     VARCHAR(20)  NOT NULL,
          confidence         DECIMAL(3,2) NULL,
          reasoning          TEXT         NULL,
          pattern            VARCHAR(50)  NULL,
          risk_flags         JSON         NULL,
          entry_params       JSON         NULL,
          screen_config_hash CHAR(40)     NULL,
          llm_call_id        BIGINT       NULL,
          created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (symbol, date),
          KEY idx_date_class (date, classification),
          KEY idx_date_market (date, market)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS llm_calls (
          id                BIGINT        NOT NULL AUTO_INCREMENT,
          timestamp         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
          module            VARCHAR(50)   NULL,
          model             VARCHAR(50)   NULL,
          prompt_tokens     INT           NULL,
          completion_tokens INT           NULL,
          cost_usd          DECIMAL(10,6) NULL,
          request_payload   JSON          NULL,
          response_payload  JSON          NULL,
          duration_ms       INT           NULL,
          error             TEXT          NULL,
          PRIMARY KEY (id),
          KEY idx_timestamp (timestamp),
          KEY idx_module_timestamp (module, timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_calls")
    op.execute("DROP TABLE IF EXISTS daily_analysis_us")
    op.execute("DROP TABLE IF EXISTS daily_analysis_kr")