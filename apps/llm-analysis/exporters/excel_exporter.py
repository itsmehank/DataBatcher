"""
Excel exporter for daily LLM analysis results.

Phase 2 Sprint 1 — phase2_brief.md §3 Sprint 1.

Generates a 3-sheet workbook:
- Sheet 1 "Entry 후보": classification='entry' + entry_params 16 fields
- Sheet 2 "Watch 후보": classification='watch' + reasoning + revisit clues
- Sheet 3 "전체 분석": KR + US all results (classification, confidence, key_facts)

Inputs:
- daily_analysis_kr / daily_analysis_us tables (date filter)
- 05_GLOSSARY Part B.1.7 schema + Part B.2 entry_params 16 fields

CLI: apps/llm-analysis/run_excel_export.py --date YYYY-MM-DD --region kr|us|both
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Literal

# openpyxl imports (실제 구현 시 채움)
# from openpyxl import Workbook
# from openpyxl.styles import ...


Region = Literal["kr", "us", "both"]


@dataclass(frozen=True)
class DailyAnalysisRow:
    """daily_analysis_kr/us 행 도메인 모델 (read-only DAO 출력)."""
    symbol: str
    date: date
    market: str
    classification: str
    confidence: float | None
    reasoning: str | None
    pattern: str | None
    risk_flags: dict | None
    entry_params: dict | None
    screen_config_hash: str | None
    llm_call_id: int | None
    region: Region  # 'kr' | 'us' (DAO가 채움)


class ExcelExporter:
    """3-sheet workbook generator.

    Usage:
        exporter = ExcelExporter(rows=..., target_date=date(2026,5,11))
        path = exporter.export(out_dir=Path("..."))
    """

    # Sheet 1 핵심 컬럼 (frozen, 8필드 + 메타)
    ENTRY_CORE_COLS = [
        "symbol", "pivot_price", "trigger_price", "current_price",
        "stop_loss_price", "suggested_weight_pct",
        "expected_target_price", "entry_window_days",
    ]
    # Sheet 1 contextual 컬럼 (hidden, 8필드)
    ENTRY_CONTEXTUAL_COLS = [
        "stop_loss_pct_from_pivot", "stop_loss_pct_from_current_price",
        "expected_target_pct", "max_chase_pct_from_pivot",
        "breakout_volume_requirement", "observed_breakout_volume_ratio",
        "pattern_basis", "notes",
    ]
    # Sheet 1 추가 컬럼 (확장)
    ENTRY_EXTRA_COLS = ["known_warnings", "other_warnings", "confidence", "reasoning"]

    def __init__(self, rows: Iterable[DailyAnalysisRow], target_date: date):
        self.rows = list(rows)
        self.target_date = target_date

    def export(self, out_dir: Path) -> Path:
        """Generates the workbook and returns the file path.

        Output filename: daily_analysis_YYYY-MM-DD_{region}.xlsx
        """
        raise NotImplementedError("Step 1.B에서 구현")

    # --- Sheet builders (Step 1.B에서 구현) ---
    def _build_sheet_entry(self, ws) -> None:
        raise NotImplementedError

    def _build_sheet_watch(self, ws) -> None:
        raise NotImplementedError

    def _build_sheet_all(self, ws) -> None:
        raise NotImplementedError
