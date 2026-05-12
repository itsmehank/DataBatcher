"""
Unit tests for scripts.check_dispatch_health.

Phase 2 Phase 6 — phase2_progress.md §6 / ADR-016 C급.

Coverage:
1. read_recent_records — present / missing_file / empty + region/date filters
2. latest_status_per_date — picks newest timestamp per date
3. build_region_report — sent / failed / missing day classification with mocked DB
4. format_report — output lines for healthy / failed / missing / no-log cases
5. CLI main — exit code 0 (healthy) vs 1 (failure)
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from scripts import check_dispatch_health as cdh
from exporters.email_sender import EmailDispatchRecord, append_dispatch_log


def _record(
    *,
    region: str,
    date_str: str,
    timestamp: str,
    status: str = "sent",
    error: str | None = None,
    retry: int = 0,
) -> EmailDispatchRecord:
    return EmailDispatchRecord(
        timestamp=timestamp,
        region=region,
        date=date_str,
        recipient="r@test",
        subject="s",
        attached_filename="x.xlsx",
        attached_size_bytes=1,
        status=status,
        smtp_response=None if status != "sent" else "ok",
        error_message=error,
        retry_count=retry,
    )


# ── 1. read_recent_records ──────────────────────────────────────────────────


class TestReadRecentRecords:
    def test_missing_file(self, tmp_path):
        records, status = cdh.read_recent_records(
            tmp_path / "absent.jsonl", "kr", date(2026, 5, 1), date(2026, 5, 12)
        )
        assert records == []
        assert status == "missing_file"

    def test_empty_file(self, tmp_path):
        log = tmp_path / "logs" / "d.jsonl"
        log.parent.mkdir(parents=True)
        log.write_text("", encoding="utf-8")
        records, status = cdh.read_recent_records(
            log, "kr", date(2026, 5, 1), date(2026, 5, 12)
        )
        assert records == []
        assert status == "empty"

    def test_filters_region_and_window(self, tmp_path):
        log = tmp_path / "d.jsonl"
        append_dispatch_log(_record(region="kr", date_str="2026-05-04", timestamp="2026-05-04T22:00:00+09:00"), log)
        append_dispatch_log(_record(region="us", date_str="2026-05-07", timestamp="2026-05-07T17:00:00+09:00"), log)
        append_dispatch_log(_record(region="kr", date_str="2026-04-20", timestamp="2026-04-20T22:00:00+09:00"), log)

        records, status = cdh.read_recent_records(
            log, "kr", date(2026, 5, 1), date(2026, 5, 12)
        )
        assert status == "present"
        assert len(records) == 1
        assert records[0].region == "kr"
        assert records[0].date == "2026-05-04"

    def test_unparseable_lines_skipped(self, tmp_path):
        log = tmp_path / "d.jsonl"
        log.write_text(
            "not-json\n"
            + json.dumps({"region": "kr", "unknown_field": True}) + "\n"
            + json.dumps(_record(region="kr", date_str="2026-05-04", timestamp="2026-05-04T22:00:00+09:00").to_jsonable())
            + "\n",
            encoding="utf-8",
        )
        records, status = cdh.read_recent_records(
            log, "kr", date(2026, 5, 1), date(2026, 5, 12)
        )
        assert status == "present"
        assert len(records) == 1


# ── 2. latest_status_per_date ───────────────────────────────────────────────


class TestLatestStatusPerDate:
    def test_picks_newer_timestamp(self):
        recs = [
            _record(region="kr", date_str="2026-05-04", timestamp="2026-05-04T22:00:00+09:00", status="failed", error="boom"),
            _record(region="kr", date_str="2026-05-04", timestamp="2026-05-04T22:30:00+09:00", status="sent"),
        ]
        latest = cdh.latest_status_per_date(recs)
        assert latest[date(2026, 5, 4)].status == "sent"

    def test_distinct_dates_kept(self):
        recs = [
            _record(region="kr", date_str="2026-05-03", timestamp="2026-05-03T22:00:00+09:00"),
            _record(region="kr", date_str="2026-05-04", timestamp="2026-05-04T22:00:00+09:00"),
        ]
        latest = cdh.latest_status_per_date(recs)
        assert set(latest.keys()) == {date(2026, 5, 3), date(2026, 5, 4)}


# ── 3. build_region_report ──────────────────────────────────────────────────


class TestBuildRegionReport:
    def test_healthy_no_missing_no_failed(self, tmp_path):
        log = tmp_path / "d.jsonl"
        append_dispatch_log(_record(region="kr", date_str="2026-05-04", timestamp="2026-05-04T22:00:00+09:00"), log)
        append_dispatch_log(_record(region="kr", date_str="2026-05-05", timestamp="2026-05-05T22:00:00+09:00"), log)

        def fake_db(_region, _start, _end):
            return {date(2026, 5, 4), date(2026, 5, 5)}

        report = cdh.build_region_report(
            "kr", days=7, today=date(2026, 5, 10), log_path=log, db_fetch=fake_db
        )
        assert report.is_healthy()
        assert report.dispatched_dates == {date(2026, 5, 4), date(2026, 5, 5)}
        assert report.failed_records == []
        assert report.missing_dates == set()

    def test_missing_day_detected(self, tmp_path):
        log = tmp_path / "d.jsonl"
        append_dispatch_log(_record(region="kr", date_str="2026-05-04", timestamp="2026-05-04T22:00:00+09:00"), log)
        # 5월 5일 분석 행은 있지만 발송 기록 없음

        def fake_db(_region, _start, _end):
            return {date(2026, 5, 4), date(2026, 5, 5)}

        report = cdh.build_region_report(
            "kr", days=7, today=date(2026, 5, 10), log_path=log, db_fetch=fake_db
        )
        assert not report.is_healthy()
        assert report.missing_dates == {date(2026, 5, 5)}

    def test_failed_records_collected(self, tmp_path):
        log = tmp_path / "d.jsonl"
        append_dispatch_log(
            _record(
                region="kr", date_str="2026-05-04",
                timestamp="2026-05-04T22:00:00+09:00",
                status="failed", error="SMTPAuth", retry=0,
            ),
            log,
        )

        def fake_db(_region, _start, _end):
            return {date(2026, 5, 4)}

        report = cdh.build_region_report(
            "kr", days=7, today=date(2026, 5, 10), log_path=log, db_fetch=fake_db
        )
        assert len(report.failed_records) == 1
        assert report.failed_records[0].error_message == "SMTPAuth"
        # 실패 record는 attempted로 간주 → missing 아님
        assert report.missing_dates == set()
        assert not report.is_healthy()

    def test_db_unreachable_skips_missing_check(self, tmp_path):
        log = tmp_path / "d.jsonl"
        append_dispatch_log(_record(region="kr", date_str="2026-05-04", timestamp="2026-05-04T22:00:00+09:00"), log)
        report = cdh.build_region_report(
            "kr", days=7, today=date(2026, 5, 10), log_path=log,
            db_fetch=lambda *_: None,
        )
        assert report.analysis_dates is None
        assert report.missing_dates == set()
        assert report.is_healthy()  # 누락 점검 skip 시 healthy로 간주

    def test_failed_then_resent_same_date_is_healthy(self, tmp_path):
        """직전 실패 후 같은 거래일 재발송 성공 시 healthy로 간주."""
        log = tmp_path / "d.jsonl"
        append_dispatch_log(
            _record(region="kr", date_str="2026-05-04",
                    timestamp="2026-05-04T22:00:00+09:00",
                    status="failed", error="net"),
            log,
        )
        append_dispatch_log(
            _record(region="kr", date_str="2026-05-04",
                    timestamp="2026-05-04T23:00:00+09:00", status="sent"),
            log,
        )

        def fake_db(_r, _s, _e):
            return {date(2026, 5, 4)}

        report = cdh.build_region_report(
            "kr", days=7, today=date(2026, 5, 10), log_path=log, db_fetch=fake_db,
        )
        assert report.failed_records == []
        assert report.dispatched_dates == {date(2026, 5, 4)}
        assert report.is_healthy()


# ── 4. format_report ────────────────────────────────────────────────────────


class TestFormatReport:
    def _healthy_report(self) -> cdh.RegionReport:
        return cdh.RegionReport(
            region="kr",
            days=7,
            window_start=date(2026, 5, 4),
            window_end=date(2026, 5, 10),
            dispatched_dates={date(2026, 5, 4), date(2026, 5, 5)},
            failed_records=[],
            analysis_dates={date(2026, 5, 4), date(2026, 5, 5)},
            missing_dates=set(),
            log_status="present",
        )

    def test_healthy_summary(self):
        lines = cdh.format_report(self._healthy_report(), Path("/log"))
        text = "\n".join(lines)
        assert "[KR] 최근 7일" in text
        assert "성공/dry_run 2건" in text
        assert "실패 0건" in text
        assert "누락 0건" in text

    def test_missing_file_line(self, tmp_path):
        report = self._healthy_report()
        report.log_status = "missing_file"
        lines = cdh.format_report(report, tmp_path / "absent.jsonl")
        assert "JSONL 파일 없음" in "\n".join(lines)

    def test_empty_file_line(self):
        report = self._healthy_report()
        report.log_status = "empty"
        lines = cdh.format_report(report, Path("/log"))
        assert "JSONL 비어있음" in "\n".join(lines)

    def test_failure_listed(self):
        report = self._healthy_report()
        report.failed_records = [
            _record(region="kr", date_str="2026-05-05",
                    timestamp="2026-05-05T22:00:00+09:00",
                    status="failed", error="boom", retry=2),
        ]
        lines = cdh.format_report(report, Path("/log"))
        out = "\n".join(lines)
        assert "실패 내역" in out
        assert "2026-05-05" in out
        assert "boom" in out
        assert "retry=2" in out

    def test_missing_listed(self):
        report = self._healthy_report()
        report.missing_dates = {date(2026, 5, 5), date(2026, 5, 6)}
        lines = cdh.format_report(report, Path("/log"))
        out = "\n".join(lines)
        assert "누락 거래일" in out
        assert "2026-05-05" in out
        assert "2026-05-06" in out

    def test_db_unreachable_shows_skip(self):
        report = self._healthy_report()
        report.analysis_dates = None
        lines = cdh.format_report(report, Path("/log"))
        assert "DB 미연결" in "\n".join(lines)


# ── 5. main entry ──────────────────────────────────────────────────────────


class TestMain:
    def test_healthy_exit_zero(self, tmp_path, monkeypatch, capsys):
        log = tmp_path / "d.jsonl"
        append_dispatch_log(_record(region="kr", date_str="2026-05-04", timestamp="2026-05-04T22:00:00+09:00"), log)
        monkeypatch.setattr(cdh, "fetch_analysis_dates", lambda *_: {date(2026, 5, 4)})

        rc = cdh.main(["--days", "7", "--region", "kr",
                       "--log-path", str(log), "--today", "2026-05-10"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "[KR] 최근 7일" in out

    def test_failure_exit_one(self, tmp_path, monkeypatch, capsys):
        log = tmp_path / "d.jsonl"
        append_dispatch_log(
            _record(region="us", date_str="2026-05-07",
                    timestamp="2026-05-07T17:00:00+09:00",
                    status="failed", error="boom"),
            log,
        )
        monkeypatch.setattr(cdh, "fetch_analysis_dates", lambda *_: {date(2026, 5, 7)})
        rc = cdh.main(["--days", "7", "--region", "us",
                       "--log-path", str(log), "--today", "2026-05-10"])
        assert rc == 1
        assert "boom" in capsys.readouterr().out

    def test_missing_log_exit_one(self, tmp_path, capsys):
        rc = cdh.main(["--days", "7", "--region", "kr",
                       "--log-path", str(tmp_path / "absent.jsonl"),
                       "--today", "2026-05-10"])
        assert rc == 1
        assert "JSONL 파일 없음" in capsys.readouterr().out

    def test_both_regions_two_blocks(self, tmp_path, monkeypatch, capsys):
        log = tmp_path / "d.jsonl"
        append_dispatch_log(_record(region="kr", date_str="2026-05-04", timestamp="2026-05-04T22:00:00+09:00"), log)
        append_dispatch_log(_record(region="us", date_str="2026-05-07", timestamp="2026-05-07T17:00:00+09:00"), log)
        monkeypatch.setattr(
            cdh, "fetch_analysis_dates",
            lambda region, _s, _e: {date(2026, 5, 4)} if region == "kr" else {date(2026, 5, 7)},
        )
        rc = cdh.main(["--days", "7", "--region", "both",
                       "--log-path", str(log), "--today", "2026-05-10"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "[KR]" in out and "[US]" in out

    def test_days_must_be_positive(self, capsys):
        rc = cdh.main(["--days", "0", "--region", "kr"])
        assert rc == 1
        assert "--days" in capsys.readouterr().err
