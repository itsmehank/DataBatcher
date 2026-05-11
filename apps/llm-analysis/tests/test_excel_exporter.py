"""
Unit tests for exporters.excel_exporter.

Phase 2 Sprint 1 — Step 1.B.3.

검증 범위:
1. 3 sheet 생성·이름·순서
2. Sheet 1 컬럼 구성 (CORE 8 + EXTRA 4 + CONTEXTUAL 8 = 20) + hidden M~T + freeze B2
3. Sheet 1 entry 행 entry_params 17필드 값 정합 (NVST sample 기반)
4. Sheet 2 watch 행 컬럼 + classification_change_signal 빈 cell
5. Sheet 3 전체 행 카운트 + 정렬 (entry > watch > ignore)
6. region 시나리오 (kr / us / both) — 파일명 + Sheet 3 region 컬럼
7. 빈 entry/watch 안내 행
8. Sheet 3 reasoning 200자 컷 + '...' suffix
9. entry_params None 행 회색 fill (#F2F2F2)

원 명세는 "16필드"였으나 코드 SSoT 발견으로 17필드로 검증 (Architect 결정).
"""

from __future__ import annotations

from datetime import date

import pytest
from openpyxl import load_workbook

from exporters.excel_exporter import (
    ExcelExporter,
    DailyAnalysisRow,
)


# ── Sample fixtures ───────────────────────────────────────────────────────────


def _nvst_entry_params() -> dict:
    """05_GLOSSARY Part B.2 NVST sample entry_params (17필드)."""
    return {
        "pivot_price": 22.67,
        "trigger_price": 22.69,
        "current_price": 23.23,
        "stop_loss_price": 21.47,
        "stop_loss_pct_from_pivot": -5.3,
        "stop_loss_pct_from_current_price": -7.6,
        "suggested_weight_pct": 4.9,
        "expected_target_price": 27.20,
        "expected_target_pct": 20.0,
        "entry_window_days": 3,
        "max_chase_pct_from_pivot": 5.0,
        "breakout_volume_requirement": "ge_1.4x_50day_avg",
        "observed_breakout_volume_ratio": 1.02,
        "pattern_basis": "cup_with_handle",
        "notes": "Position size reduced 0.7x due to low_volume_breakout flag.",
        "known_warnings": [
            "stop_distance_from_current_price_exceeds_book_limit",
            "breakout_volume_below_requirement",
        ],
        "other_warnings": [],
    }


def _nvst_entry_row() -> DailyAnalysisRow:
    return DailyAnalysisRow(
        symbol="NVST",
        date=date(2026, 5, 11),
        market="NYSE",
        classification="entry",
        confidence=0.85,
        reasoning="Cup-with-handle breakout with constructive volume.",
        pattern="cup_with_handle",
        risk_flags={"low_volume_breakout": True, "overbought": 0.6},
        entry_params=_nvst_entry_params(),
        screen_config_hash="abc1234",
        llm_call_id=42,
        region="us",
    )


def _watch_row(symbol: str = "ALTO", reasoning: str = "Forming handle but volume light.") -> DailyAnalysisRow:
    return DailyAnalysisRow(
        symbol=symbol,
        date=date(2026, 5, 11),
        market="NASDAQ",
        classification="watch",
        confidence=0.72,
        reasoning=reasoning,
        pattern="cup_with_handle",
        risk_flags=["needs_volume", "tight_base"],
        entry_params=None,
        screen_config_hash="hh",
        llm_call_id=7,
        region="us",
    )


def _ignore_row(symbol: str = "005930", region="kr") -> DailyAnalysisRow:
    return DailyAnalysisRow(
        symbol=symbol,
        date=date(2026, 5, 11),
        market="KOSPI" if region == "kr" else "NYSE",
        classification="ignore",
        confidence=1.0,
        reasoning="Not in stage 2 uptrend.",
        pattern=None,
        risk_flags=None,
        entry_params=None,
        screen_config_hash=None,
        llm_call_id=None,
        region=region,
    )


def _entry_row_no_params(symbol: str = "XXX") -> DailyAnalysisRow:
    """entry classification이지만 entry_params=None (회색 fill 검증용)."""
    return DailyAnalysisRow(
        symbol=symbol,
        date=date(2026, 5, 11),
        market="NYSE",
        classification="entry",
        confidence=0.5,
        reasoning="r",
        pattern="p",
        risk_flags=None,
        entry_params=None,
        screen_config_hash=None,
        llm_call_id=None,
        region="us",
    )


# ── 1. 3 sheet 생성 ───────────────────────────────────────────────────────────


def test_workbook_has_three_sheets_in_order(tmp_path):
    rows = [_nvst_entry_row(), _watch_row(), _ignore_row()]
    exp = ExcelExporter(rows=rows, target_date=date(2026, 5, 11), region="us")
    out = exp.export(out_dir=tmp_path)
    wb = load_workbook(out)
    assert wb.sheetnames == ["Entry 후보", "Watch 후보", "전체 분석"]


# ── 2. Sheet 1 컬럼 구성 ──────────────────────────────────────────────────────


def test_sheet1_columns_layout_and_freeze(tmp_path):
    rows = [_nvst_entry_row()]
    exp = ExcelExporter(rows=rows, target_date=date(2026, 5, 11), region="us")
    out = exp.export(out_dir=tmp_path)
    wb = load_workbook(out)
    ws = wb["Entry 후보"]

    expected_headers = (
        ExcelExporter.ENTRY_CORE_COLS
        + ExcelExporter.ENTRY_EXTRA_COLS
        + ExcelExporter.ENTRY_CONTEXTUAL_COLS
    )
    actual_headers = [ws.cell(row=1, column=i).value for i in range(1, len(expected_headers) + 1)]
    assert actual_headers == expected_headers
    assert len(expected_headers) == 20  # CORE 8 + EXTRA 4 + CONTEXTUAL 8

    # Hidden: M~T (CONTEXTUAL 8개, 13~20번 컬럼)
    visible = {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"}
    hidden = {"M", "N", "O", "P", "Q", "R", "S", "T"}
    for letter in visible:
        assert ws.column_dimensions[letter].hidden is False, f"{letter} should be visible"
    for letter in hidden:
        assert ws.column_dimensions[letter].hidden is True, f"{letter} should be hidden"

    # Freeze pane B2 (header + symbol 열 고정)
    assert ws.freeze_panes == "B2"


# ── 3. Sheet 1 entry 행 17필드 값 정합 ────────────────────────────────────────


def test_sheet1_entry_row_renders_17_entry_params_fields(tmp_path):
    rows = [_nvst_entry_row()]
    exp = ExcelExporter(rows=rows, target_date=date(2026, 5, 11), region="us")
    out = exp.export(out_dir=tmp_path)
    wb = load_workbook(out)
    ws = wb["Entry 후보"]

    headers = [ws.cell(row=1, column=i).value for i in range(1, 21)]
    values = [ws.cell(row=2, column=i).value for i in range(1, 21)]
    cell_map = dict(zip(headers, values))

    ep = _nvst_entry_params()
    # entry_params 17필드 모두 셀에 표기되는지 검증 (known/other_warnings는 \n join)
    assert cell_map["symbol"] == "NVST"
    assert cell_map["pivot_price"] == pytest.approx(22.67)
    assert cell_map["trigger_price"] == pytest.approx(22.69)
    assert cell_map["current_price"] == pytest.approx(23.23)
    assert cell_map["stop_loss_price"] == pytest.approx(21.47)
    assert cell_map["suggested_weight_pct"] == pytest.approx(4.9)
    assert cell_map["expected_target_price"] == pytest.approx(27.20)
    assert cell_map["entry_window_days"] == 3
    # CONTEXTUAL 8
    assert cell_map["stop_loss_pct_from_pivot"] == pytest.approx(-5.3)
    assert cell_map["stop_loss_pct_from_current_price"] == pytest.approx(-7.6)
    assert cell_map["expected_target_pct"] == pytest.approx(20.0)
    assert cell_map["max_chase_pct_from_pivot"] == pytest.approx(5.0)
    assert cell_map["breakout_volume_requirement"] == "ge_1.4x_50day_avg"
    assert cell_map["observed_breakout_volume_ratio"] == pytest.approx(1.02)
    assert cell_map["pattern_basis"] == "cup_with_handle"
    assert cell_map["notes"] == ep["notes"]
    # 경고 2종 multi-line
    assert cell_map["known_warnings"] == "\n".join(ep["known_warnings"])
    assert cell_map["other_warnings"] in ("", None)  # 빈 리스트 — openpyxl는 빈 cell을 None으로 반환
    # DB 메타
    assert cell_map["confidence"] == pytest.approx(0.85)
    assert "breakout" in cell_map["reasoning"].lower()


# ── 4. Sheet 2 watch 행 ───────────────────────────────────────────────────────


def test_sheet2_watch_row(tmp_path):
    rows = [_nvst_entry_row(), _watch_row()]
    exp = ExcelExporter(rows=rows, target_date=date(2026, 5, 11), region="us")
    out = exp.export(out_dir=tmp_path)
    wb = load_workbook(out)
    ws = wb["Watch 후보"]

    headers = [ws.cell(row=1, column=i).value for i in range(1, 8)]
    assert headers == ExcelExporter.SHEET2_COLS

    row2 = [ws.cell(row=2, column=i).value for i in range(1, 8)]
    assert row2[0] == "ALTO"                  # symbol
    assert row2[1] == "NASDAQ"                # market
    assert row2[2] == pytest.approx(0.72)     # confidence
    assert "handle" in row2[3].lower()        # reasoning
    assert row2[4] == "cup_with_handle"       # pattern
    assert "needs_volume" in row2[5]          # risk_flags multi-line
    assert "tight_base" in row2[5]
    assert "\n" in row2[5]
    assert row2[6] == "" or row2[6] is None   # classification_change_signal — 빈 cell


# ── 5. Sheet 3 전체 행 카운트 + 정렬 ──────────────────────────────────────────


def test_sheet3_row_count_and_sort_order(tmp_path):
    rows = [
        _ignore_row(),
        _nvst_entry_row(),
        _watch_row(),
    ]
    exp = ExcelExporter(rows=rows, target_date=date(2026, 5, 11), region="both")
    out = exp.export(out_dir=tmp_path)
    wb = load_workbook(out)
    ws = wb["전체 분석"]

    # Sheet 3는 self.rows 그대로 사용 — 입력 순서 유지 (DAO에서 정렬 의무).
    # 본 테스트는 입력에 entry-watch-ignore 정렬을 주지 않고 들어온 행을 그대로 표기하는지 검증.
    assert ws.max_row == 4   # header + 3 rows
    classifications = [ws.cell(row=i, column=4).value for i in range(2, 5)]
    assert classifications == ["ignore", "entry", "watch"]  # 입력 순서 유지


# ── 6. region 시나리오 (kr / us / both) ───────────────────────────────────────


@pytest.mark.parametrize("region,filename_suffix", [("kr", "_kr"), ("us", "_us"), ("both", "_both")])
def test_filename_includes_region(tmp_path, region, filename_suffix):
    exp = ExcelExporter(rows=[], target_date=date(2026, 5, 11), region=region)
    out = exp.export(out_dir=tmp_path)
    assert out.name == f"daily_analysis_2026-05-11{filename_suffix}.xlsx"


def test_region_both_sheet3_includes_both_regions(tmp_path):
    rows = [
        _ignore_row(symbol="005930", region="kr"),
        _nvst_entry_row(),                            # region='us'
    ]
    exp = ExcelExporter(rows=rows, target_date=date(2026, 5, 11), region="both")
    out = exp.export(out_dir=tmp_path)
    wb = load_workbook(out)
    ws = wb["전체 분석"]
    regions = [ws.cell(row=i, column=2).value for i in range(2, ws.max_row + 1)]
    assert set(regions) == {"kr", "us"}


# ── 7. 빈 entry / watch 안내 행 ───────────────────────────────────────────────


def test_empty_entry_shows_guidance_row(tmp_path):
    rows = [_watch_row(), _ignore_row()]  # entry 0건
    exp = ExcelExporter(rows=rows, target_date=date(2026, 5, 11), region="us")
    out = exp.export(out_dir=tmp_path)
    wb = load_workbook(out)
    ws = wb["Entry 후보"]
    assert ws.cell(row=2, column=1).value == "본 거래일 entry 후보 없음"


def test_empty_watch_shows_guidance_row(tmp_path):
    rows = [_nvst_entry_row(), _ignore_row()]  # watch 0건
    exp = ExcelExporter(rows=rows, target_date=date(2026, 5, 11), region="us")
    out = exp.export(out_dir=tmp_path)
    wb = load_workbook(out)
    ws = wb["Watch 후보"]
    assert ws.cell(row=2, column=1).value == "본 거래일 watch 후보 없음"


# ── 8. Sheet 3 reasoning 200자 컷 ─────────────────────────────────────────────


def test_sheet3_reasoning_truncated_to_200_chars_plus_ellipsis(tmp_path):
    long_text = "X" * 250
    row = _watch_row(reasoning=long_text)
    exp = ExcelExporter(rows=[row], target_date=date(2026, 5, 11), region="us")
    out = exp.export(out_dir=tmp_path)
    wb = load_workbook(out)
    ws = wb["전체 분석"]
    reasoning_cell = ws.cell(row=2, column=8).value
    assert reasoning_cell.endswith("...")
    assert len(reasoning_cell) == 203  # 200 + "..."


def test_sheet3_reasoning_under_limit_not_truncated(tmp_path):
    short = "Short reason."
    row = _watch_row(reasoning=short)
    exp = ExcelExporter(rows=[row], target_date=date(2026, 5, 11), region="us")
    out = exp.export(out_dir=tmp_path)
    wb = load_workbook(out)
    ws = wb["전체 분석"]
    assert ws.cell(row=2, column=8).value == short


# ── 9. entry_params None 행 회색 fill ─────────────────────────────────────────


def test_entry_params_none_row_has_gray_fill(tmp_path):
    """entry classification이지만 entry_params=None인 행은 회색 fill(#F2F2F2)."""
    rows = [_entry_row_no_params(symbol="XXX")]
    exp = ExcelExporter(rows=rows, target_date=date(2026, 5, 11), region="us")
    out = exp.export(out_dir=tmp_path)
    wb = load_workbook(out)
    ws = wb["Entry 후보"]

    fill_colors = []
    for col_idx in range(1, 21):
        cell = ws.cell(row=2, column=col_idx)
        # PatternFill.fgColor.rgb는 보통 "00F2F2F2" 형식
        rgb = cell.fill.fgColor.rgb if cell.fill and cell.fill.fgColor else None
        fill_colors.append(rgb)
    # 모든 cell 동일 회색 fill 적용 — F2F2F2 hex가 rgb에 포함되어야 함
    assert all(c and "F2F2F2" in str(c).upper() for c in fill_colors), \
        f"entry_params=None 행 회색 fill 미적용: {fill_colors}"
