-- Migration: Add sector/industry columns to symbol_master and us_symbol_master
-- Date: 2026-02-08
-- Description: Adds sector classification, symbol_type, and tracking columns

-- symbol_master (한국)
ALTER TABLE symbol_master
  ADD COLUMN symbol_type       VARCHAR(16) NULL AFTER market,
  ADD COLUMN sector            VARCHAR(128) NULL AFTER status,
  ADD COLUMN sector_detail     VARCHAR(256) NULL AFTER sector,
  ADD COLUMN industry          VARCHAR(512) NULL AFTER sector_detail,
  ADD COLUMN sector_source     VARCHAR(32) NULL AFTER industry,
  ADD COLUMN sector_updated_at TIMESTAMP NULL AFTER sector_source;

-- us_symbol_master (미국) - sector, industry already exist
ALTER TABLE us_symbol_master
  ADD COLUMN symbol_type       VARCHAR(16) NULL AFTER market,
  ADD COLUMN sector_source     VARCHAR(32) NULL AFTER industry,
  ADD COLUMN sector_updated_at TIMESTAMP NULL AFTER sector_source;
