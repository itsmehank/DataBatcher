-- Migration: add_daily_analysis_and_llm_calls
-- Alembic revision: 20260428_000001
-- Down revision: 20260424_000001
-- ADR-009 (스키마 정의), ADR-010 (마이그레이션 3종 산출물 — 이 파일은 ② raw SQL)
-- Date: 2026-04-28
--
-- Phase 1 LLM 분석 레이어를 위한 신규 테이블 3종:
--   - daily_analysis_kr / daily_analysis_us: LLM 차트 분석 결과 저장
--   - llm_calls: 모든 LLM 호출 영구 기록 (헌법 §2.5)
--
-- 대응 Alembic 파일:
--   db/migrations/versions/20260428_000001_add_daily_analysis_and_llm_calls.py
--
-- 적용 방법 (DEV):
--   alembic -c db/migrations/alembic.ini upgrade head
--
-- 적용 방법 (PROD, raw SQL 직접):
--   Get-Content db\migrations\sql\20260428_000001_add_daily_analysis_and_llm_calls.sql |
--     docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" trade
--
-- 롤백:
--   DROP TABLE IF EXISTS llm_calls;
--   DROP TABLE IF EXISTS daily_analysis_us;
--   DROP TABLE IF EXISTS daily_analysis_kr;

-- ============================================================
-- 1. daily_analysis_kr
--    KR 주식 LLM 차트 분석 결과
--    market: 'KOSPI' | 'KOSDAQ' | 'ETF'
--    classification: 'entry' | 'watch' | 'ignore'
-- ============================================================
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 2. daily_analysis_us
--    US 주식 LLM 차트 분석 결과 (daily_analysis_kr과 동일 구조)
--    market: 'NYSE' | 'NASDAQ' | 'ETF'
-- ============================================================
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 3. llm_calls
--    모든 LLM 호출 영구 기록 (헌법 §2.5)
--    cost_usd: CLI 백엔드(Max 플랜)에서는 NULL (ADR-011 §3)
-- ============================================================
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
