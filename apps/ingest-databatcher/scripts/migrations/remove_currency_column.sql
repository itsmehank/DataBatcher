-- ============================================================================
-- Migration: Remove currency column from stock_prices table
-- Date: 2026-01-28
-- Reason: pykrx does not provide currency information (all KRX stocks are KRW)
-- ============================================================================

-- Remove currency column from stock_prices table
ALTER TABLE stock_prices DROP COLUMN IF EXISTS currency;

-- Verify the change
DESCRIBE stock_prices;