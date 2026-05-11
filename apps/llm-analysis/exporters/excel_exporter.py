"""
Excel exporter for daily LLM analysis results.

Phase 2 Sprint 1 — phase2_brief.md §3 Sprint 1.

Generates a 3-sheet workbook:
- Sheet 1 "Entry 후보": classification='entry' + entry_params (CORE 7 + CONTEXTUAL 8 + EXTRA 2)
- Sheet 2 "Watch 후보": classification='watch' + reasoning + revisit clues
- Sheet 3 "전체 분석": KR + US all results (classification, confidence, key_facts)

Inputs:
- daily_analysis_kr / daily_analysis_us tables (date filter, via DAO)
- 05_GLOSSARY Part B.1.7 schema + Part B.2 entry_params (실제 17필드)

CLI: apps/llm-analysis/run_excel_export.py --date YYYY-MM-DD --region kr|us|both
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Literal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet


Region = Literal["kr", "us", "both"]

# ── 상수 ──────────────────────────────────────────────────────────────────────

_HEADER_FILL = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
_HEADER_FONT = Font(bold=True)
_EMPTY_FILL = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
_WRAP_TOP = Alignment(wrap_text=True, vertical="top")

# Sheet 1 컬럼 width 디폴트 (가독성 우선)
_SHEET1_COL_WIDTHS = {
    "symbol": 12, "pivot_price": 12, "trigger_price": 12, "current_price": 12,
    "stop_loss_price": 12, "suggested_weight_pct": 14,
    "expected_target_price": 14, "entry_window_days": 12,
    "known_warnings": 36, "other_warnings": 36, "confidence": 10, "reasoning": 60,
    "stop_loss_pct_from_pivot": 18, "stop_loss_pct_from_current_price": 22,
    "expected_target_pct": 14, "max_chase_pct_from_pivot": 18,
    "breakout_volume_requirement": 22, "observed_breakout_volume_ratio": 22,
    "pattern_basis": 14, "notes": 50,
}


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
    risk_flags: dict | list | None
    entry_params: dict | None
    screen_config_hash: str | None
    llm_call_id: int | None
    region: Region  # 'kr' | 'us' (DAO가 채움)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _style_header(ws: Worksheet, ncols: int) -> None:
    """Row 1 header bold + 옅은 회색 배경."""
    for col_idx in range(1, ncols + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(vertical="center")


def _apply_col_widths(ws: Worksheet, headers: list[str]) -> None:
    for idx, name in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = _SHEET1_COL_WIDTHS.get(name, 16)


def _format_warnings_list(items: list | None) -> str:
    """known_warnings / other_warnings 리스트 → multi-line cell."""
    if not items:
        return ""
    return "\n".join(str(x) for x in items)


def _format_risk_flags_multiline(rf: dict | list | None) -> str:
    """Sheet 2: risk_flags 전체를 multi-line으로 가독성 위주 표기."""
    if not rf:
        return ""
    if isinstance(rf, list):
        return "\n".join(str(x) for x in rf)
    if isinstance(rf, dict):
        return "\n".join(f"{k}: {v}" if v not in (None, "", True) else str(k) for k, v in rf.items())
    return str(rf)


def _format_risk_flags_summary(rf: dict | list | None) -> str:
    """Sheet 3: risk_flags 요약 — '{count}건: {top1}, {top2}'."""
    if not rf:
        return ""
    if isinstance(rf, list):
        keys = [str(x) for x in rf]
    elif isinstance(rf, dict):
        keys = [str(k) for k in rf.keys()]
    else:
        return str(rf)
    if not keys:
        return ""
    head = ", ".join(keys[:2])
    return f"{len(keys)}건: {head}" if len(keys) > 2 else head


def _truncate_reasoning(text: str | None, limit: int = 200) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


# ── 메인 클래스 ───────────────────────────────────────────────────────────────

class ExcelExporter:
    """3-sheet workbook generator.

    Usage:
        exporter = ExcelExporter(rows=..., target_date=date(2026,5,11), region='us')
        path = exporter.export(out_dir=Path("./out"))
    """

    # Sheet 1 핵심 컬럼 (frozen, 8: symbol + entry_params 7개)
    ENTRY_CORE_COLS = [
        "symbol", "pivot_price", "trigger_price", "current_price",
        "stop_loss_price", "suggested_weight_pct",
        "expected_target_price", "entry_window_days",
    ]
    # Sheet 1 확장 (frozen 영역에 같이 표시): entry_params 경고 2 + DB 메타 2
    ENTRY_EXTRA_COLS = ["known_warnings", "other_warnings", "confidence", "reasoning"]
    # Sheet 1 contextual (hidden, entry_params 8개)
    ENTRY_CONTEXTUAL_COLS = [
        "stop_loss_pct_from_pivot", "stop_loss_pct_from_current_price",
        "expected_target_pct", "max_chase_pct_from_pivot",
        "breakout_volume_requirement", "observed_breakout_volume_ratio",
        "pattern_basis", "notes",
    ]

    # entry_params 17필드 set (cell 값 채울 때 entry_params None 처리용)
    _ENTRY_PARAMS_FIELDS = frozenset(
        ENTRY_CORE_COLS[1:]   # symbol 제외
        + ENTRY_CONTEXTUAL_COLS
        + ["known_warnings", "other_warnings"]
    )

    SHEET2_COLS = [
        "symbol", "market", "confidence", "reasoning", "pattern",
        "risk_flags", "classification_change_signal",
    ]
    SHEET3_COLS = [
        "symbol", "region", "market", "classification", "confidence",
        "pattern", "risk_flags", "reasoning",
    ]

    def __init__(
        self,
        rows: Iterable[DailyAnalysisRow],
        target_date: date,
        region: Region,
    ):
        self.rows = list(rows)
        self.target_date = target_date
        self.region = region

    # ── public API ────────────────────────────────────────────────────────────

    def export(self, out_dir: Path) -> Path:
        """Generates the workbook and returns the file path.

        Output filename: daily_analysis_YYYY-MM-DD_{region}.xlsx
        """
        out_dir.mkdir(parents=True, exist_ok=True)

        wb = Workbook()
        # 기본 sheet 제거 → 명시적으로 3 sheet 생성
        wb.remove(wb.active)

        ws1 = wb.create_sheet(title="Entry 후보")
        self._build_sheet_entry(ws1)

        ws2 = wb.create_sheet(title="Watch 후보")
        self._build_sheet_watch(ws2)

        ws3 = wb.create_sheet(title="전체 분석")
        self._build_sheet_all(ws3)

        filename = f"daily_analysis_{self.target_date.isoformat()}_{self.region}.xlsx"
        out_path = out_dir / filename
        wb.save(out_path)
        return out_path

    # ── Sheet 1: Entry 후보 ───────────────────────────────────────────────────

    def _build_sheet_entry(self, ws: Worksheet) -> None:
        headers = self.ENTRY_CORE_COLS + self.ENTRY_EXTRA_COLS + self.ENTRY_CONTEXTUAL_COLS
        ws.append(headers)
        _style_header(ws, len(headers))
        _apply_col_widths(ws, headers)

        entry_rows = [r for r in self.rows if r.classification == "entry"]

        if not entry_rows:
            # 안내 행 분기 — 데이터 행과 시각 구분 위해 회색 fill 적용
            empty_row = ["본 거래일 entry 후보 없음"] + [""] * (len(headers) - 1)
            ws.append(empty_row)
            for col_idx in range(1, len(headers) + 1):
                ws.cell(row=2, column=col_idx).fill = _EMPTY_FILL
        else:
            # entry 행 분기
            for row in entry_rows:
                ws.append(self._render_entry_row(row, headers))

            # entry_params None 종목 회색 fill (전체 row)
            for excel_row_idx, dao_row in enumerate(entry_rows, start=2):
                if dao_row.entry_params is None:
                    for col_idx in range(1, len(headers) + 1):
                        ws.cell(row=excel_row_idx, column=col_idx).fill = _EMPTY_FILL

            # multi-line/wrap_text 적용 (known_warnings, other_warnings, reasoning, notes)
            wrap_cols = {"known_warnings", "other_warnings", "reasoning", "notes"}
            for col_idx, name in enumerate(headers, start=1):
                if name not in wrap_cols:
                    continue
                for excel_row_idx in range(2, len(entry_rows) + 2):
                    ws.cell(row=excel_row_idx, column=col_idx).alignment = _WRAP_TOP

        # 공통 후처리 — entry 유무와 무관하게 hidden + freeze 적용 (시각 속성 일관성)
        hidden_start = len(self.ENTRY_CORE_COLS) + len(self.ENTRY_EXTRA_COLS) + 1
        for i in range(len(self.ENTRY_CONTEXTUAL_COLS)):
            letter = get_column_letter(hidden_start + i)
            ws.column_dimensions[letter].hidden = True
        ws.freeze_panes = "B2"

    def _render_entry_row(self, row: DailyAnalysisRow, headers: list[str]) -> list:
        """entry row 1건 → header 순서대로 cell 값 리스트 반환."""
        ep = row.entry_params or {}
        cells: list = []
        for name in headers:
            if name == "symbol":
                cells.append(row.symbol)
            elif name == "confidence":
                cells.append(row.confidence)
            elif name == "reasoning":
                cells.append(row.reasoning or "")
            elif name == "known_warnings":
                cells.append(_format_warnings_list(ep.get("known_warnings")))
            elif name == "other_warnings":
                cells.append(_format_warnings_list(ep.get("other_warnings")))
            elif name in self._ENTRY_PARAMS_FIELDS:
                cells.append(ep.get(name) if ep else "")
            else:
                cells.append("")
        return cells

    # ── Sheet 2: Watch 후보 ───────────────────────────────────────────────────

    def _build_sheet_watch(self, ws: Worksheet) -> None:
        headers = self.SHEET2_COLS
        ws.append(headers)
        _style_header(ws, len(headers))

        # 컬럼 width (가독성)
        widths = {
            "symbol": 12, "market": 10, "confidence": 10,
            "reasoning": 60, "pattern": 18, "risk_flags": 36,
            "classification_change_signal": 36,
        }
        for idx, name in enumerate(headers, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = widths.get(name, 16)

        watch_rows = [r for r in self.rows if r.classification == "watch"]

        if not watch_rows:
            ws.append(["본 거래일 watch 후보 없음"] + [""] * (len(headers) - 1))
            ws.freeze_panes = "A2"
            return

        for row in watch_rows:
            ws.append([
                row.symbol,
                row.market,
                row.confidence,
                row.reasoning or "",
                row.pattern or "",
                _format_risk_flags_multiline(row.risk_flags),
                "",  # classification_change_signal — Sprint 1에서는 빈 cell (후속 sprint 정밀화)
            ])

        # wrap_text on reasoning / risk_flags / classification_change_signal
        wrap_cols = {"reasoning", "risk_flags", "classification_change_signal"}
        for col_idx, name in enumerate(headers, start=1):
            if name not in wrap_cols:
                continue
            for excel_row_idx in range(2, len(watch_rows) + 2):
                ws.cell(row=excel_row_idx, column=col_idx).alignment = _WRAP_TOP

        ws.freeze_panes = "A2"

    # ── Sheet 3: 전체 분석 ────────────────────────────────────────────────────

    def _build_sheet_all(self, ws: Worksheet) -> None:
        headers = self.SHEET3_COLS
        ws.append(headers)
        _style_header(ws, len(headers))

        widths = {
            "symbol": 12, "region": 8, "market": 10, "classification": 12,
            "confidence": 10, "pattern": 18, "risk_flags": 30, "reasoning": 60,
        }
        for idx, name in enumerate(headers, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = widths.get(name, 16)

        if not self.rows:
            ws.append(["본 거래일 분석 결과 없음"] + [""] * (len(headers) - 1))
            ws.freeze_panes = "A2"
            return

        for row in self.rows:
            ws.append([
                row.symbol,
                row.region,
                row.market,
                row.classification,
                row.confidence,
                row.pattern or "",
                _format_risk_flags_summary(row.risk_flags),
                _truncate_reasoning(row.reasoning, limit=200),
            ])

        # wrap_text only on reasoning (요약 컬럼은 짧음)
        reasoning_col = headers.index("reasoning") + 1
        for excel_row_idx in range(2, len(self.rows) + 2):
            ws.cell(row=excel_row_idx, column=reasoning_col).alignment = _WRAP_TOP

        ws.freeze_panes = "A2"
