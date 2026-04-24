-- Date: 2026-04-24
-- ADR-009: Add conditions_met JSON column to store per-condition pass/fail
-- for Minervini trend template screening results.
-- Rationale: Phase 1 LLM analysis needs to know WHICH conditions a stock
-- passed to produce meaningful reasoning.

ALTER TABLE minervini_screen_results_kr
  ADD COLUMN conditions_met JSON NULL COMMENT 'ADR-009: per-condition pass/fail map'
  AFTER is_blue_dot;

ALTER TABLE minervini_screen_results_us
  ADD COLUMN conditions_met JSON NULL COMMENT 'ADR-009: per-condition pass/fail map'
  AFTER is_blue_dot;