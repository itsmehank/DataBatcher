"""
Unit tests for exporters.email_sender.

Phase 2 Sprint 2 — phase2_brief.md §3 Sprint 2 / ADR-016 §6 (C급).

Coverage map (matches phase2_brief Sprint 2 §D.7):
1. SMTPConfig.from_env (정상 / fallback / 누락 / 비정수)
2. build_email_body (entry 0/1/3/5 × watch 0/3/5/10, truncation, subject 매칭)
3. send_email mock (정상 / 1회 실패 후 재시도 / max_retries 후 실패 /
   SMTPAuthenticationError 즉시 / 첨부 부재 / backoff sleep)
4. append_dispatch_log (신규 / append / UTF-8 / 디스크 실패 RuntimeError)
5. dispatch_daily_email (정상 / dry_run)
6. CLI 인자 파싱 (필수 / fallback / --dry-run / region='both')

모든 SMTP·DB 호출은 mock — 실 SMTP 발송 0건.
"""
from __future__ import annotations

import json
import smtplib
import socket
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from exporters.email_sender import (
    DEFAULT_LOG_PATH,
    EmailDispatchRecord,
    SMTPConfig,
    _build_message,
    append_dispatch_log,
    build_email_body,
    build_prior_failure_warning,
    dispatch_daily_email,
    read_last_dispatch_for_region,
    send_email,
)
from exporters.excel_exporter import DailyAnalysisRow


# ── helpers ──────────────────────────────────────────────────────────────────


def _row(
    symbol: str,
    *,
    classification: str = "entry",
    confidence: float | None = 0.8,
    reasoning: str | None = "기준 패턴 명확. 거래량 확인됨.",
    entry_params: dict | None = None,
    region: str = "us",
) -> DailyAnalysisRow:
    if entry_params is None:
        entry_params = {
            "pivot_price": 100.0,
            "stop_loss_price": 95.0,
            "expected_target_price": 130.0,
            "suggested_weight_pct": 5,
        }
    return DailyAnalysisRow(
        symbol=symbol,
        date=date(2026, 5, 6),
        market="NASDAQ" if region == "us" else "KOSPI",
        classification=classification,
        confidence=confidence,
        reasoning=reasoning,
        pattern="VCP",
        risk_flags=None,
        entry_params=entry_params,
        screen_config_hash="abc",
        llm_call_id=1,
        region=region,
    )


@pytest.fixture
def smtp_env(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "tester@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)
    monkeypatch.delenv("SMTP_USE_STARTTLS", raising=False)
    monkeypatch.delenv("SMTP_USE_SSL", raising=False)
    return monkeypatch


# ── 1. SMTPConfig.from_env ──────────────────────────────────────────────────


class TestSMTPConfigFromEnv:
    def test_defaults_applied(self, smtp_env):
        cfg = SMTPConfig.from_env()
        assert cfg.host == "smtp.gmail.com"
        assert cfg.port == 587
        assert cfg.user == "tester@example.com"
        assert cfg.password == "secret"
        assert cfg.sender == "tester@example.com"  # fallback to SMTP_USER
        assert cfg.use_starttls is True
        assert cfg.use_ssl is False

    def test_explicit_overrides(self, smtp_env):
        smtp_env.setenv("SMTP_HOST", "smtp.acme.test")
        smtp_env.setenv("SMTP_PORT", "465")
        smtp_env.setenv("SMTP_FROM", "alert@acme.test")
        smtp_env.setenv("SMTP_USE_STARTTLS", "false")
        smtp_env.setenv("SMTP_USE_SSL", "true")
        cfg = SMTPConfig.from_env()
        assert cfg.host == "smtp.acme.test"
        assert cfg.port == 465
        assert cfg.sender == "alert@acme.test"
        assert cfg.use_starttls is False
        assert cfg.use_ssl is True

    def test_missing_user_raises(self, smtp_env):
        smtp_env.delenv("SMTP_USER")
        with pytest.raises(ValueError, match="SMTP_USER"):
            SMTPConfig.from_env()

    def test_missing_password_raises(self, smtp_env):
        smtp_env.delenv("SMTP_PASSWORD")
        with pytest.raises(ValueError, match="SMTP_PASSWORD"):
            SMTPConfig.from_env()

    def test_non_integer_port_raises(self, smtp_env):
        smtp_env.setenv("SMTP_PORT", "five-eighty-seven")
        with pytest.raises(ValueError, match="SMTP_PORT"):
            SMTPConfig.from_env()

    def test_ssl_and_starttls_mutually_exclusive(self, smtp_env):
        smtp_env.setenv("SMTP_USE_SSL", "true")
        smtp_env.setenv("SMTP_USE_STARTTLS", "true")
        cfg = SMTPConfig.from_env()
        assert cfg.use_ssl is True
        assert cfg.use_starttls is False


# ── 2. build_email_body ─────────────────────────────────────────────────────


class TestBuildEmailBody:
    def test_subject_matches_counts(self):
        entries = [_row("AAA"), _row("BBB"), _row("CCC")]
        watches = [_row(f"W{i:02d}", classification="watch") for i in range(5)]
        subject, _ = build_email_body(
            region="us",
            target_date=date(2026, 5, 6),
            entry_candidates=entries,
            watch_candidates=watches,
            attached_filename="daily_analysis_2026-05-06_us.xlsx",
        )
        assert subject == (
            "[StockAlert] 2026-05-06 US 분석 결과 (entry 3, watch 5)"
        )

    def test_empty_entry_message(self):
        _, body = build_email_body(
            region="kr",
            target_date=date(2026, 5, 6),
            entry_candidates=[],
            watch_candidates=[_row("000001", classification="watch", region="kr")],
            attached_filename="x.xlsx",
        )
        assert "Entry 후보 없음" in body
        assert "Entry 후보: 0건" in body

    def test_empty_watch_message(self):
        _, body = build_email_body(
            region="us",
            target_date=date(2026, 5, 6),
            entry_candidates=[_row("AAA")],
            watch_candidates=[],
            attached_filename="x.xlsx",
        )
        assert "Watch 후보 없음" in body
        assert "전체 0건" in body

    def test_watch_top_three_only(self):
        watches = [
            _row("W01", classification="watch", confidence=0.10),
            _row("W02", classification="watch", confidence=0.50),
            _row("W03", classification="watch", confidence=0.90),
            _row("W04", classification="watch", confidence=0.40),
            _row("W05", classification="watch", confidence=0.95),
            _row("W06", classification="watch", confidence=0.20),
            _row("W07", classification="watch", confidence=0.30),
            _row("W08", classification="watch", confidence=0.15),
            _row("W09", classification="watch", confidence=0.05),
            _row("W10", classification="watch", confidence=0.01),
        ]
        _, body = build_email_body(
            region="us",
            target_date=date(2026, 5, 6),
            entry_candidates=[],
            watch_candidates=watches,
            attached_filename="x.xlsx",
        )
        # Top 3 by confidence DESC: W05, W03, W02
        assert "W05" in body and "W03" in body and "W02" in body
        # W01 has lower confidence — must not appear in the body
        assert "W01" not in body
        assert "전체 10건" in body
        assert "상위 3건" in body

    def test_long_reasoning_truncation(self):
        long_text = "리" * 500
        _, body = build_email_body(
            region="us",
            target_date=date(2026, 5, 6),
            entry_candidates=[_row("AAA", reasoning=long_text)],
            watch_candidates=[
                _row("W01", classification="watch", reasoning=long_text)
            ],
            attached_filename="x.xlsx",
        )
        # entry block truncated to 200 chars + ellipsis
        assert "리" * 200 + "..." in body
        # watch block truncated to 150 chars + ellipsis
        assert "리" * 150 + "..." in body

    def test_company_names_used(self):
        _, body = build_email_body(
            region="us",
            target_date=date(2026, 5, 6),
            entry_candidates=[_row("AAA")],
            watch_candidates=[],
            attached_filename="x.xlsx",
            company_names={"AAA": "Acme Co."},
        )
        assert "AAA (Acme Co.)" in body

    def test_invalid_region_raises(self):
        with pytest.raises(ValueError, match="region"):
            build_email_body(
                region="jp",  # type: ignore[arg-type]
                target_date=date(2026, 5, 6),
                entry_candidates=[],
                watch_candidates=[],
                attached_filename="x.xlsx",
            )

    def test_entry_block_includes_params(self):
        _, body = build_email_body(
            region="us",
            target_date=date(2026, 5, 6),
            entry_candidates=[_row("AAA")],
            watch_candidates=[],
            attached_filename="x.xlsx",
        )
        assert "Pivot:" in body and "Stop:" in body
        assert "Target:" in body and "Size:" in body
        assert "17필드" in body  # references to full Excel


# ── 3. send_email ──────────────────────────────────────────────────────────


def _make_config() -> SMTPConfig:
    return SMTPConfig(
        host="smtp.test", port=587,
        user="u@test", password="pw", sender="u@test",
        use_starttls=True, use_ssl=False,
    )


class TestSendEmail:
    def test_success_first_attempt(self, tmp_path):
        attach = tmp_path / "x.xlsx"
        attach.write_bytes(b"PK\x03\x04demo")
        sender = MagicMock(return_value="SMTP ok")
        record = send_email(
            config=_make_config(),
            recipient="r@test",
            subject="s",
            body="b",
            attachment_path=attach,
            region="us",
            target_date=date(2026, 5, 6),
            sender_fn=sender,
            sleeper=lambda _: None,
        )
        assert record.status == "sent"
        assert record.retry_count == 0
        assert record.smtp_response == "SMTP ok"
        assert record.attached_filename == "x.xlsx"
        assert record.attached_size_bytes == len(b"PK\x03\x04demo")
        assert sender.call_count == 1

    def test_retry_then_success(self, tmp_path):
        attach = tmp_path / "x.xlsx"
        attach.write_bytes(b"data")
        sender = MagicMock(
            side_effect=[smtplib.SMTPServerDisconnected("temp"), "SMTP ok"]
        )
        sleeps: list[float] = []
        record = send_email(
            config=_make_config(),
            recipient="r@test",
            subject="s",
            body="b",
            attachment_path=attach,
            region="us",
            target_date=date(2026, 5, 6),
            sender_fn=sender,
            sleeper=sleeps.append,
        )
        assert record.status == "sent"
        assert record.retry_count == 1
        assert sender.call_count == 2
        assert sleeps == [2.0]  # initial_backoff * (factor ** 0)

    def test_max_retries_then_failed(self, tmp_path):
        attach = tmp_path / "x.xlsx"
        attach.write_bytes(b"data")
        sender = MagicMock(side_effect=socket.timeout("nope"))
        sleeps: list[float] = []
        record = send_email(
            config=_make_config(),
            recipient="r@test",
            subject="s",
            body="b",
            attachment_path=attach,
            region="us",
            target_date=date(2026, 5, 6),
            max_retries=3,
            initial_backoff=1.0,
            exponential_factor=2.0,
            sender_fn=sender,
            sleeper=sleeps.append,
        )
        assert record.status == "failed"
        assert record.retry_count == 2  # attempts 1,2,3 → final retry_count=2
        assert sender.call_count == 3
        # Two backoffs between three attempts: 1.0, 2.0
        assert sleeps == [1.0, 2.0]
        assert record.error_message and "timeout" in record.error_message.lower()

    def test_auth_error_immediate_failure(self, tmp_path):
        attach = tmp_path / "x.xlsx"
        attach.write_bytes(b"data")
        sender = MagicMock(
            side_effect=smtplib.SMTPAuthenticationError(535, b"bad creds")
        )
        sleeps: list[float] = []
        record = send_email(
            config=_make_config(),
            recipient="r@test",
            subject="s",
            body="b",
            attachment_path=attach,
            region="us",
            target_date=date(2026, 5, 6),
            sender_fn=sender,
            sleeper=sleeps.append,
        )
        assert record.status == "failed"
        assert sender.call_count == 1
        assert sleeps == []
        assert "SMTPAuthenticationError" in (record.error_message or "")

    def test_missing_attachment(self):
        sender = MagicMock(return_value="SMTP ok")
        record = send_email(
            config=_make_config(),
            recipient="r@test",
            subject="s",
            body="b",
            attachment_path=None,
            region="us",
            target_date=date(2026, 5, 6),
            sender_fn=sender,
            sleeper=lambda _: None,
        )
        assert record.status == "sent"
        assert record.attached_filename == ""
        assert record.attached_size_bytes == 0

    def test_backoff_caps_at_max(self, tmp_path):
        attach = tmp_path / "x.xlsx"
        attach.write_bytes(b"data")
        sender = MagicMock(side_effect=smtplib.SMTPServerDisconnected("nope"))
        sleeps: list[float] = []
        send_email(
            config=_make_config(),
            recipient="r@test",
            subject="s",
            body="b",
            attachment_path=attach,
            region="us",
            target_date=date(2026, 5, 6),
            max_retries=4,
            initial_backoff=10.0,
            exponential_factor=10.0,
            max_backoff=15.0,
            sender_fn=sender,
            sleeper=sleeps.append,
        )
        # raw values would be 10, 100, 1000 — all capped to 15 after first
        assert sleeps == [10.0, 15.0, 15.0]

    def test_build_message_has_attachment_and_subject(self, tmp_path):
        attach = tmp_path / "x.xlsx"
        attach.write_bytes(b"PK")
        msg = _build_message(_make_config(), "r@test", "subj", "body", attach)
        assert msg["Subject"] == "subj"
        assert msg["From"] == "u@test"
        assert msg["To"] == "r@test"
        parts = list(msg.iter_attachments())
        assert len(parts) == 1
        assert parts[0].get_filename() == "x.xlsx"


# ── 4. append_dispatch_log ──────────────────────────────────────────────────


class TestAppendDispatchLog:
    def _record(self, **overrides) -> EmailDispatchRecord:
        base = dict(
            timestamp="2026-05-06T22:00:00+09:00",
            region="us",
            date="2026-05-06",
            recipient="r@test",
            subject="[StockAlert] 한글 제목",
            attached_filename="x.xlsx",
            attached_size_bytes=4,
            status="sent",
            smtp_response="SMTP ok",
            error_message=None,
            retry_count=0,
        )
        base.update(overrides)
        return EmailDispatchRecord(**base)

    def test_creates_directory_and_writes(self, tmp_path):
        log_path = tmp_path / "logs" / "email_dispatch.jsonl"
        append_dispatch_log(self._record(), log_path)
        assert log_path.exists()
        line = log_path.read_text(encoding="utf-8").strip()
        parsed = json.loads(line)
        assert parsed["recipient"] == "r@test"
        assert parsed["region"] == "us"
        assert parsed["subject"] == "[StockAlert] 한글 제목"

    def test_append_mode(self, tmp_path):
        log_path = tmp_path / "logs" / "email_dispatch.jsonl"
        append_dispatch_log(self._record(status="dry_run"), log_path)
        append_dispatch_log(self._record(status="sent"), log_path)
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["status"] == "dry_run"
        assert json.loads(lines[1])["status"] == "sent"

    def test_utf8_preserved(self, tmp_path):
        log_path = tmp_path / "logs" / "email_dispatch.jsonl"
        record = self._record(error_message="네트워크 끊김 — 재시도 실패")
        append_dispatch_log(record, log_path)
        content = log_path.read_text(encoding="utf-8")
        assert "네트워크 끊김 — 재시도 실패" in content

    def test_disk_failure_escalates(self, tmp_path, monkeypatch):
        log_path = tmp_path / "logs" / "email_dispatch.jsonl"

        def boom(*_args, **_kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(Path, "mkdir", boom)
        with pytest.raises(RuntimeError, match="dispatch log"):
            append_dispatch_log(self._record(), log_path)


# ── 5. dispatch_daily_email ────────────────────────────────────────────────


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def __call__(self):
        return self

    def close(self):
        pass


class TestDispatchDailyEmail:
    @pytest.fixture
    def excel_file(self, tmp_path):
        path = tmp_path / "daily_analysis_2026-05-06_us.xlsx"
        path.write_bytes(b"PK\x03\x04demo")
        return path

    def test_dry_run_writes_log_without_send(self, excel_file, tmp_path, monkeypatch):
        from exporters import email_sender as mod

        rows = [_row("AAA"), _row("WWW", classification="watch")]

        def fake_fetch(_session, _target_date, _region):
            return rows

        def fake_names(_session, _symbols, _region):
            return {"AAA": "Acme Co."}

        monkeypatch.setattr(mod, "fetch_daily_analysis", fake_fetch)
        monkeypatch.setattr(mod, "fetch_company_names", fake_names)

        log_path = tmp_path / "logs" / "dispatch.jsonl"
        session = _FakeSession(rows)
        record = dispatch_daily_email(
            region="us",
            target_date=date(2026, 5, 6),
            recipient="r@test",
            excel_path=excel_file,
            dry_run=True,
            session_factory=lambda: session,
            log_path=log_path,
        )
        assert record.status == "dry_run"
        assert record.attached_filename == excel_file.name
        # log written
        assert log_path.exists()
        logged = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert logged["status"] == "dry_run"

    def test_send_path_uses_send_email(self, excel_file, tmp_path, monkeypatch):
        from exporters import email_sender as mod

        monkeypatch.setattr(mod, "fetch_daily_analysis", lambda *_a, **_k: [_row("AAA")])
        monkeypatch.setattr(mod, "fetch_company_names", lambda *_a, **_k: {})

        captured = {}

        def fake_send_email(**kwargs):
            captured.update(kwargs)
            return EmailDispatchRecord(
                timestamp="2026-05-06T22:00:00+09:00",
                region=kwargs["region"],
                date=kwargs["target_date"].isoformat(),
                recipient=kwargs["recipient"],
                subject=kwargs["subject"],
                attached_filename=Path(kwargs["attachment_path"]).name,
                attached_size_bytes=Path(kwargs["attachment_path"]).stat().st_size,
                status="sent",
                smtp_response="ok",
                error_message=None,
                retry_count=0,
            )

        monkeypatch.setattr(mod, "send_email", fake_send_email)

        log_path = tmp_path / "logs" / "dispatch.jsonl"
        record = dispatch_daily_email(
            region="us",
            target_date=date(2026, 5, 6),
            recipient="r@test",
            excel_path=excel_file,
            dry_run=False,
            smtp_config=_make_config(),
            session_factory=lambda: _FakeSession([]),
            log_path=log_path,
        )
        assert record.status == "sent"
        assert captured["recipient"] == "r@test"
        assert captured["region"] == "us"
        assert captured["attachment_path"] == excel_file
        assert log_path.exists()

    def test_missing_excel_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            dispatch_daily_email(
                region="us",
                target_date=date(2026, 5, 6),
                recipient="r@test",
                excel_path=tmp_path / "nope.xlsx",
                dry_run=True,
                session_factory=lambda: _FakeSession([]),
                log_path=tmp_path / "logs" / "x.jsonl",
            )

    def test_invalid_region(self, excel_file, tmp_path):
        with pytest.raises(ValueError):
            dispatch_daily_email(
                region="jp",  # type: ignore[arg-type]
                target_date=date(2026, 5, 6),
                recipient="r@test",
                excel_path=excel_file,
                dry_run=True,
                session_factory=lambda: _FakeSession([]),
                log_path=tmp_path / "logs" / "x.jsonl",
            )


# ── 5b. graceful fallback (Sprint 3) ────────────────────────────────────────


def _failed_record(region: str, ts: str, error: str = "boom") -> EmailDispatchRecord:
    return EmailDispatchRecord(
        timestamp=ts,
        region=region,
        date="2026-05-06",
        recipient="r@test",
        subject="prev",
        attached_filename="prev.xlsx",
        attached_size_bytes=1,
        status="failed",
        smtp_response=None,
        error_message=error,
        retry_count=2,
    )


def _sent_record(region: str, ts: str) -> EmailDispatchRecord:
    return EmailDispatchRecord(
        timestamp=ts,
        region=region,
        date="2026-05-06",
        recipient="r@test",
        subject="prev",
        attached_filename="prev.xlsx",
        attached_size_bytes=1,
        status="sent",
        smtp_response="ok",
        error_message=None,
        retry_count=0,
    )


class TestReadLastDispatchForRegion:
    def test_missing_log_returns_none(self, tmp_path):
        assert read_last_dispatch_for_region("us", tmp_path / "absent.jsonl") is None

    def test_returns_latest_for_region(self, tmp_path):
        log = tmp_path / "d.jsonl"
        append_dispatch_log(_sent_record("us", "2026-05-10T00:00:00+09:00"), log)
        append_dispatch_log(_failed_record("us", "2026-05-11T00:00:00+09:00"), log)
        append_dispatch_log(_sent_record("kr", "2026-05-11T22:00:00+09:00"), log)
        rec = read_last_dispatch_for_region("us", log)
        assert rec is not None
        assert rec.status == "failed"
        assert rec.timestamp == "2026-05-11T00:00:00+09:00"

    def test_other_region_returns_none(self, tmp_path):
        log = tmp_path / "d.jsonl"
        append_dispatch_log(_sent_record("us", "2026-05-10T00:00:00+09:00"), log)
        assert read_last_dispatch_for_region("kr", log) is None

    def test_unparseable_lines_skipped(self, tmp_path):
        log = tmp_path / "d.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "not-json\n"
            + json.dumps({"region": "us", "garbage": True}) + "\n"
            + json.dumps(_sent_record("us", "2026-05-10T00:00:00+09:00").to_jsonable())
            + "\n",
            encoding="utf-8",
        )
        rec = read_last_dispatch_for_region("us", log)
        assert rec is not None
        assert rec.status == "sent"


class TestBuildPriorFailureWarning:
    def test_none_input(self):
        assert build_prior_failure_warning(None) is None

    def test_sent_returns_none(self):
        assert build_prior_failure_warning(_sent_record("us", "2026-05-10T00:00:00+09:00")) is None

    def test_dry_run_returns_none(self):
        rec = EmailDispatchRecord(
            timestamp="2026-05-10T00:00:00+09:00",
            region="us",
            date="2026-05-10",
            recipient="r@test",
            subject="s",
            attached_filename="x.xlsx",
            attached_size_bytes=1,
            status="dry_run",
            smtp_response=None,
            error_message=None,
            retry_count=0,
        )
        assert build_prior_failure_warning(rec) is None

    def test_failed_emits_warning(self):
        rec = _failed_record("us", "2026-05-10T00:00:00+09:00", error="SMTPAuthError")
        line = build_prior_failure_warning(rec)
        assert line is not None
        assert "직전 발송 실패" in line
        assert "SMTPAuthError" in line
        assert "2026-05-10T00:00:00+09:00" in line

    def test_failed_without_error_message(self):
        rec = _failed_record("us", "2026-05-10T00:00:00+09:00")
        rec.error_message = None
        line = build_prior_failure_warning(rec)
        assert line is not None
        assert "원인 미상" in line


class TestDispatchFallbackIntegration:
    @pytest.fixture
    def excel_file(self, tmp_path):
        path = tmp_path / "daily_analysis_2026-05-06_us.xlsx"
        path.write_bytes(b"PK")
        return path

    def test_prior_failed_warning_prepended_to_body(
        self, excel_file, tmp_path, monkeypatch
    ):
        from exporters import email_sender as mod

        monkeypatch.setattr(mod, "fetch_daily_analysis", lambda *_a, **_k: [_row("AAA")])
        monkeypatch.setattr(mod, "fetch_company_names", lambda *_a, **_k: {})

        log_path = tmp_path / "logs" / "dispatch.jsonl"
        append_dispatch_log(
            _failed_record("us", "2026-05-10T00:00:00+09:00", error="timeout"),
            log_path,
        )

        captured_body: dict = {}

        def fake_send(**kwargs):
            captured_body["body"] = kwargs["body"]
            return EmailDispatchRecord(
                timestamp="2026-05-11T00:00:00+09:00",
                region="us",
                date=kwargs["target_date"].isoformat(),
                recipient=kwargs["recipient"],
                subject=kwargs["subject"],
                attached_filename=Path(kwargs["attachment_path"]).name,
                attached_size_bytes=Path(kwargs["attachment_path"]).stat().st_size,
                status="sent",
                smtp_response="ok",
                error_message=None,
                retry_count=0,
            )

        monkeypatch.setattr(mod, "send_email", fake_send)

        dispatch_daily_email(
            region="us",
            target_date=date(2026, 5, 6),
            recipient="r@test",
            excel_path=excel_file,
            smtp_config=_make_config(),
            session_factory=lambda: _FakeSession([]),
            log_path=log_path,
        )
        body = captured_body["body"]
        assert body.startswith("⚠️ 직전 발송 실패: timeout")
        assert "(2026-05-10T00:00:00+09:00)" in body

    def test_prior_sent_no_warning(self, excel_file, tmp_path, monkeypatch):
        from exporters import email_sender as mod

        monkeypatch.setattr(mod, "fetch_daily_analysis", lambda *_a, **_k: [_row("AAA")])
        monkeypatch.setattr(mod, "fetch_company_names", lambda *_a, **_k: {})

        log_path = tmp_path / "logs" / "dispatch.jsonl"
        append_dispatch_log(_sent_record("us", "2026-05-10T00:00:00+09:00"), log_path)

        captured_body: dict = {}

        def fake_send(**kwargs):
            captured_body["body"] = kwargs["body"]
            return EmailDispatchRecord(
                timestamp="2026-05-11T00:00:00+09:00",
                region="us",
                date=kwargs["target_date"].isoformat(),
                recipient=kwargs["recipient"],
                subject=kwargs["subject"],
                attached_filename=Path(kwargs["attachment_path"]).name,
                attached_size_bytes=Path(kwargs["attachment_path"]).stat().st_size,
                status="sent",
                smtp_response="ok",
                error_message=None,
                retry_count=0,
            )

        monkeypatch.setattr(mod, "send_email", fake_send)

        dispatch_daily_email(
            region="us",
            target_date=date(2026, 5, 6),
            recipient="r@test",
            excel_path=excel_file,
            smtp_config=_make_config(),
            session_factory=lambda: _FakeSession([]),
            log_path=log_path,
        )
        assert "직전 발송 실패" not in captured_body["body"]

    def test_other_region_failure_does_not_warn(
        self, excel_file, tmp_path, monkeypatch
    ):
        from exporters import email_sender as mod

        monkeypatch.setattr(mod, "fetch_daily_analysis", lambda *_a, **_k: [])
        monkeypatch.setattr(mod, "fetch_company_names", lambda *_a, **_k: {})

        log_path = tmp_path / "logs" / "dispatch.jsonl"
        # KR previously failed — US dispatch must NOT carry the warning.
        append_dispatch_log(_failed_record("kr", "2026-05-10T22:00:00+09:00"), log_path)

        captured_body: dict = {}

        def fake_send(**kwargs):
            captured_body["body"] = kwargs["body"]
            return EmailDispatchRecord(
                timestamp="2026-05-11T17:00:00+09:00",
                region="us",
                date=kwargs["target_date"].isoformat(),
                recipient=kwargs["recipient"],
                subject=kwargs["subject"],
                attached_filename=Path(kwargs["attachment_path"]).name,
                attached_size_bytes=Path(kwargs["attachment_path"]).stat().st_size,
                status="sent",
                smtp_response="ok",
                error_message=None,
                retry_count=0,
            )

        monkeypatch.setattr(mod, "send_email", fake_send)

        dispatch_daily_email(
            region="us",
            target_date=date(2026, 5, 6),
            recipient="r@test",
            excel_path=excel_file,
            smtp_config=_make_config(),
            session_factory=lambda: _FakeSession([]),
            log_path=log_path,
        )
        assert "직전 발송 실패" not in captured_body["body"]


# ── 6. CLI argument parsing ────────────────────────────────────────────────


class TestCLIArgs:
    def test_required_flags(self):
        from run_email_send import _parse_args

        with pytest.raises(SystemExit):
            _parse_args([])  # neither --date nor --region

    def test_date_and_region_parsed(self):
        from run_email_send import _parse_args

        args = _parse_args(["--date", "2026-05-06", "--region", "kr"])
        assert args.date == date(2026, 5, 6)
        assert args.region == "kr"
        assert args.dry_run is False
        assert args.to is None

    def test_dry_run_flag(self):
        from run_email_send import _parse_args

        args = _parse_args(["--date", "2026-05-06", "--region", "us", "--dry-run"])
        assert args.dry_run is True

    def test_to_fallback_to_env(self, monkeypatch):
        from run_email_send import _resolve_recipient

        monkeypatch.setenv("SMTP_TO_DEFAULT", "fallback@test")
        assert _resolve_recipient(None) == "fallback@test"
        assert _resolve_recipient("explicit@test") == "explicit@test"

    def test_to_missing_raises(self, monkeypatch):
        from run_email_send import _resolve_recipient

        monkeypatch.delenv("SMTP_TO_DEFAULT", raising=False)
        with pytest.raises(SystemExit):
            _resolve_recipient(None)

    def test_region_both_creates_two_dispatches(self, monkeypatch, tmp_path):
        # Build two excel files and assert dispatch called twice.
        for region in ("kr", "us"):
            (tmp_path / f"daily_analysis_2026-05-06_{region}.xlsx").write_bytes(b"PK")

        import run_email_send as cli

        called: list[tuple[str, str]] = []

        def fake_dispatch(**kwargs):
            called.append((kwargs["region"], kwargs["recipient"]))
            return EmailDispatchRecord(
                timestamp="2026-05-06T22:00:00+09:00",
                region=kwargs["region"],
                date=kwargs["target_date"].isoformat(),
                recipient=kwargs["recipient"],
                subject="s",
                attached_filename="x.xlsx",
                attached_size_bytes=1,
                status="dry_run",
                smtp_response=None,
                error_message=None,
                retry_count=0,
            )

        monkeypatch.setattr(cli, "dispatch_daily_email", fake_dispatch)

        rc = cli.main([
            "--date", "2026-05-06",
            "--region", "both",
            "--to", "me@test",
            "--dry-run",
            "--excel-dir", str(tmp_path),
        ])
        assert rc == 0
        assert [c[0] for c in called] == ["kr", "us"]
        assert all(c[1] == "me@test" for c in called)

    def test_main_exit_code_on_failure(self, monkeypatch, tmp_path):
        (tmp_path / "daily_analysis_2026-05-06_us.xlsx").write_bytes(b"PK")
        import run_email_send as cli

        def fake_dispatch(**kwargs):
            return EmailDispatchRecord(
                timestamp="2026-05-06T22:00:00+09:00",
                region=kwargs["region"],
                date=kwargs["target_date"].isoformat(),
                recipient=kwargs["recipient"],
                subject="s",
                attached_filename="x.xlsx",
                attached_size_bytes=1,
                status="failed",
                smtp_response=None,
                error_message="boom",
                retry_count=2,
            )

        monkeypatch.setattr(cli, "dispatch_daily_email", fake_dispatch)
        rc = cli.main([
            "--date", "2026-05-06",
            "--region", "us",
            "--to", "me@test",
            "--dry-run",
            "--excel-dir", str(tmp_path),
        ])
        assert rc == 1
