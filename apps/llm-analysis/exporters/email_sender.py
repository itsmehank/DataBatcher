"""
SMTP email dispatcher for daily LLM analysis report.

Phase 2 Sprint 2 — phase2_brief.md §3 Sprint 2 / ADR-016 §6 (C급).

Reads `daily_analysis_kr` / `daily_analysis_us` via the existing DAO, formats a
brief Korean email body listing entry candidates and top watch candidates, and
sends it through SMTP (Gmail by default) with the Sprint 1 Excel as attachment.

The full Sprint 1 Excel is the canonical artifact; this email is a summary +
delivery vehicle. Every dispatch attempt is recorded to an append-only JSONL
log at ``apps/llm-analysis/logs/email_dispatch.jsonl``.

Constitutional posture (ADR-016 §4.1):
- §2.1 (LLM 직접 주문 실행): not touched — SMTP only, no LLM invocation.
- §2.2 (결정론 코어·LLM 분리): not touched — layer 3 post-processing.
- §2.5 (LLM 출력 영구 보존): not touched — dispatch log is operational metadata,
  not the LLM output preservation medium (that remains `llm_calls` /
  `daily_analysis_*`).
"""
from __future__ import annotations

import json
import os
import smtplib
import socket
import time
from dataclasses import asdict, dataclass, field
from datetime import date as date_cls, datetime
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path
from typing import Callable, Iterable, Literal, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from .daily_analysis_dao import fetch_daily_analysis
from .excel_exporter import DailyAnalysisRow, Region

DEFAULT_LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "email_dispatch.jsonl"
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF_SEC = 2.0
DEFAULT_EXPONENTIAL_FACTOR = 2.0
DEFAULT_MAX_BACKOFF_SEC = 30.0

ENTRY_REASONING_LIMIT = 200
WATCH_REASONING_LIMIT = 150
WATCH_TOP_N = 3

DispatchStatus = Literal["sent", "failed", "dry_run"]


# ── env / config ──────────────────────────────────────────────────────────────


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(
            f"Required environment variable {name!r} is not set. "
            "See apps/llm-analysis/.env.example for the expected keys."
        )
    return value


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"Environment variable {name!r} must be an integer, got {raw!r}.") from exc


@dataclass(frozen=True)
class SMTPConfig:
    """SMTP credentials and transport options."""

    host: str
    port: int
    user: str
    password: str
    sender: str
    use_starttls: bool = True
    use_ssl: bool = False

    @classmethod
    def from_env(cls) -> "SMTPConfig":
        """Build from environment variables.

        Required: ``SMTP_USER``, ``SMTP_PASSWORD``.
        Defaults: ``SMTP_HOST=smtp.gmail.com``, ``SMTP_PORT=587``,
        ``SMTP_FROM=SMTP_USER``, ``SMTP_USE_STARTTLS=true``,
        ``SMTP_USE_SSL=false``.

        Raises ``ValueError`` with the specific missing key.
        """
        user = _required_env("SMTP_USER")
        password = _required_env("SMTP_PASSWORD")
        host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip() or "smtp.gmail.com"
        port = _int_env("SMTP_PORT", 587)
        sender = os.environ.get("SMTP_FROM", "").strip() or user
        use_starttls = _bool_env("SMTP_USE_STARTTLS", True)
        use_ssl = _bool_env("SMTP_USE_SSL", False)
        if use_ssl and use_starttls:
            # STARTTLS on an SSL connection is invalid; prefer SSL.
            use_starttls = False
        return cls(
            host=host,
            port=port,
            user=user,
            password=password,
            sender=sender,
            use_starttls=use_starttls,
            use_ssl=use_ssl,
        )


# ── dispatch record ──────────────────────────────────────────────────────────


@dataclass
class EmailDispatchRecord:
    timestamp: str
    region: Region
    date: str
    recipient: str
    subject: str
    attached_filename: str
    attached_size_bytes: int
    status: DispatchStatus
    smtp_response: str | None = None
    error_message: str | None = None
    retry_count: int = 0

    def to_jsonable(self) -> dict:
        return asdict(self)


# ── body composition ──────────────────────────────────────────────────────────


_SEPARATOR = "=" * 42


def _truncate(text_value: str | None, limit: int) -> str:
    if not text_value:
        return ""
    if len(text_value) <= limit:
        return text_value
    return text_value[:limit] + "..."


def _format_money(value) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number == int(number):
        return f"{int(number):,}"
    return f"{number:,.4f}".rstrip("0").rstrip(".")


def _format_size(value) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number}%" if number <= 1.0 * 100 else f"{number}"


def _company_label(symbol: str, names: Mapping[str, str] | None) -> str:
    if not names:
        return symbol
    name = names.get(symbol)
    return f"{symbol} ({name})" if name else symbol


def _format_entry_block(
    idx: int, row: DailyAnalysisRow, names: Mapping[str, str] | None
) -> str:
    params = row.entry_params or {}
    pivot = _format_money(params.get("pivot_price"))
    stop = _format_money(params.get("stop_loss_price"))
    target = _format_money(params.get("expected_target_price"))
    size = _format_size(params.get("suggested_weight_pct"))
    confidence = (
        f"{row.confidence:.2f}" if isinstance(row.confidence, (int, float)) else "-"
    )
    return (
        f"{idx}. {_company_label(row.symbol, names)}\n"
        f"   분류 확신도: {confidence}\n"
        f"   핵심 reasoning: {_truncate(row.reasoning, ENTRY_REASONING_LIMIT)}\n"
        f"   Entry params:\n"
        f"     - Pivot: {pivot}\n"
        f"     - Stop: {stop}\n"
        f"     - Target: {target}\n"
        f"     - Size: {size}\n"
        "   (전체 entry_params 17필드는 첨부 엑셀 참조)"
    )


def _format_watch_block(
    idx: int, row: DailyAnalysisRow, names: Mapping[str, str] | None
) -> str:
    confidence = (
        f"{row.confidence:.2f}" if isinstance(row.confidence, (int, float)) else "-"
    )
    return (
        f"{idx}. {_company_label(row.symbol, names)}\n"
        f"   분류 확신도: {confidence}\n"
        f"   핵심 reasoning: {_truncate(row.reasoning, WATCH_REASONING_LIMIT)}"
    )


def _sort_for_email(rows: Sequence[DailyAnalysisRow]) -> list[DailyAnalysisRow]:
    """Sort by confidence DESC, then symbol ASC. None confidence sinks last."""

    def key(r: DailyAnalysisRow):
        conf = r.confidence if isinstance(r.confidence, (int, float)) else float("-inf")
        return (-conf, r.symbol)

    return sorted(rows, key=key)


def build_email_body(
    region: Region,
    target_date: date_cls,
    entry_candidates: Sequence[DailyAnalysisRow],
    watch_candidates: Sequence[DailyAnalysisRow],
    attached_filename: str,
    company_names: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> tuple[str, str]:
    """Return (subject, body). KR/US share the same structure; the only
    region-specific element is the market label.
    """
    if region not in ("kr", "us"):
        raise ValueError(f"region must be 'kr' or 'us', got {region!r}")

    entries_sorted = _sort_for_email(entry_candidates)
    watches_sorted = _sort_for_email(watch_candidates)
    top_watches = watches_sorted[:WATCH_TOP_N]

    region_label = "KR" if region == "kr" else "US"
    market_label = "KR 시장" if region == "kr" else "US 시장"
    date_str = target_date.isoformat()

    subject = (
        f"[StockAlert] {date_str} {region_label} 분석 결과 "
        f"(entry {len(entries_sorted)}, watch {len(watches_sorted)})"
    )

    lines: list[str] = [
        f"{date_str} 일일 분석 결과 ({market_label})",
        "",
        _SEPARATOR,
        f"Entry 후보: {len(entries_sorted)}건",
        _SEPARATOR,
    ]
    if entries_sorted:
        for idx, row in enumerate(entries_sorted, start=1):
            lines.append(_format_entry_block(idx, row, company_names))
    else:
        lines.append("Entry 후보 없음. Watch 후보 또는 첨부 엑셀 참조.")

    lines.extend(
        [
            "",
            _SEPARATOR,
            f"Watch 후보 상위 {len(top_watches)}건 (전체 {len(watches_sorted)}건)",
            _SEPARATOR,
        ]
    )
    if top_watches:
        for idx, row in enumerate(top_watches, start=1):
            lines.append(_format_watch_block(idx, row, company_names))
    else:
        lines.append("Watch 후보 없음.")

    lines.extend(
        [
            "",
            _SEPARATOR,
            f"첨부: {attached_filename}",
            _SEPARATOR,
            "",
            f"자동 생성: {(now or datetime.now().astimezone()).isoformat(timespec='seconds')}",
        ]
    )

    return subject, "\n".join(lines)


# ── SMTP send ────────────────────────────────────────────────────────────────


_RETRYABLE = (
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPConnectError,
    smtplib.SMTPHeloError,
    smtplib.SMTPDataError,
    socket.timeout,
    ConnectionError,
    TimeoutError,
)


def _build_message(
    config: SMTPConfig,
    recipient: str,
    subject: str,
    body: str,
    attachment_path: Path | None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.sender
    msg["To"] = recipient
    msg["Message-ID"] = make_msgid(domain="stockalert.local")
    msg.set_content(body, subtype="plain", charset="utf-8")
    if attachment_path is not None:
        attachment_path = Path(attachment_path)
        data = attachment_path.read_bytes()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=attachment_path.name,
        )
    return msg


def _smtp_send_once(config: SMTPConfig, msg: EmailMessage) -> str:
    """Open an SMTP connection, authenticate, send. Returns server response string."""
    if config.use_ssl:
        with smtplib.SMTP_SSL(config.host, config.port, timeout=30) as client:
            client.login(config.user, config.password)
            client.send_message(msg)
            return f"SMTP_SSL ok host={config.host}:{config.port}"
    with smtplib.SMTP(config.host, config.port, timeout=30) as client:
        if config.use_starttls:
            client.starttls()
        client.login(config.user, config.password)
        client.send_message(msg)
        suffix = " starttls" if config.use_starttls else ""
        return f"SMTP ok host={config.host}:{config.port}{suffix}"


def send_email(
    config: SMTPConfig,
    recipient: str,
    subject: str,
    body: str,
    attachment_path: Path | None,
    region: Region,
    target_date: date_cls,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_backoff: float = DEFAULT_INITIAL_BACKOFF_SEC,
    exponential_factor: float = DEFAULT_EXPONENTIAL_FACTOR,
    max_backoff: float = DEFAULT_MAX_BACKOFF_SEC,
    sleeper: Callable[[float], None] = time.sleep,
    sender_fn: Callable[[SMTPConfig, EmailMessage], str] = _smtp_send_once,
    now: datetime | None = None,
) -> EmailDispatchRecord:
    """Send the email with retry on transient SMTP failures.

    Auth errors fail immediately. The dispatch record always carries the final
    outcome — exceptions are absorbed and reflected in ``status``/``error_message``.
    """
    if max_retries < 1:
        raise ValueError("max_retries must be >= 1")

    msg = _build_message(config, recipient, subject, body, attachment_path)
    attached_filename = (
        Path(attachment_path).name if attachment_path is not None else ""
    )
    attached_size_bytes = (
        Path(attachment_path).stat().st_size if attachment_path is not None else 0
    )

    last_error: Exception | None = None
    smtp_response: str | None = None
    attempts = 0
    for attempt in range(max_retries):
        attempts = attempt + 1
        try:
            smtp_response = sender_fn(config, msg)
            return EmailDispatchRecord(
                timestamp=(now or datetime.now().astimezone()).isoformat(timespec="seconds"),
                region=region,
                date=target_date.isoformat(),
                recipient=recipient,
                subject=subject,
                attached_filename=attached_filename,
                attached_size_bytes=attached_size_bytes,
                status="sent",
                smtp_response=smtp_response,
                error_message=None,
                retry_count=attempt,
            )
        except smtplib.SMTPAuthenticationError as exc:
            last_error = exc
            break
        except _RETRYABLE as exc:
            last_error = exc
            if attempt == max_retries - 1:
                break
            delay = min(initial_backoff * (exponential_factor ** attempt), max_backoff)
            sleeper(delay)
            continue
        except Exception as exc:  # noqa: BLE001 — surface unexpected as failed
            last_error = exc
            break

    return EmailDispatchRecord(
        timestamp=(now or datetime.now().astimezone()).isoformat(timespec="seconds"),
        region=region,
        date=target_date.isoformat(),
        recipient=recipient,
        subject=subject,
        attached_filename=attached_filename,
        attached_size_bytes=attached_size_bytes,
        status="failed",
        smtp_response=smtp_response,
        error_message=f"{type(last_error).__name__}: {last_error}" if last_error else None,
        retry_count=max(attempts - 1, 0),
    )


# ── JSONL log ────────────────────────────────────────────────────────────────


def append_dispatch_log(
    record: EmailDispatchRecord,
    log_path: Path | str = DEFAULT_LOG_PATH,
) -> None:
    """Append the dispatch record to an append-only JSONL file (UTF-8).

    Creates the parent directory on first call. Disk write failures escalate as
    ``RuntimeError`` — the caller is the authoritative dispatcher and silent
    log loss is unacceptable.
    """
    log_path = Path(log_path)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record.to_jsonable(), ensure_ascii=False))
            fp.write("\n")
    except OSError as exc:
        raise RuntimeError(f"Failed to append dispatch log to {log_path}: {exc}") from exc


def read_last_dispatch_for_region(
    region: Region,
    log_path: Path | str = DEFAULT_LOG_PATH,
) -> EmailDispatchRecord | None:
    """Return the most recent dispatch record for ``region`` from the JSONL log.

    Returns ``None`` if the log is missing, empty, or has no record for the
    region. Unparseable lines are skipped silently — the log is operational
    metadata, not authoritative state.
    """
    log_path = Path(log_path)
    if not log_path.exists():
        return None
    last: EmailDispatchRecord | None = None
    try:
        with log_path.open("r", encoding="utf-8") as fp:
            for raw in fp:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if data.get("region") != region:
                    continue
                try:
                    last = EmailDispatchRecord(**data)
                except TypeError:
                    continue
    except OSError:
        return None
    return last


def build_prior_failure_warning(prior: EmailDispatchRecord | None) -> str | None:
    """Return a one-line warning if the prior dispatch for this region failed.

    Returns ``None`` for sent/dry_run/None — only ``failed`` triggers a warning.
    """
    if prior is None or prior.status != "failed":
        return None
    err = prior.error_message or "원인 미상"
    return f"⚠️ 직전 발송 실패: {err} ({prior.timestamp})"


# ── company-name lookup (optional, falls back to symbol-only) ────────────────


def fetch_company_names(
    session: Session,
    symbols: Iterable[str],
    region: Region,
) -> dict[str, str]:
    """Look up company names from ``symbol_master`` / ``us_symbol_master``.

    Returns an empty dict on empty input or on any DB error (best-effort
    enrichment — the email is still sendable without company names).
    """
    symbols = [s for s in symbols if s]
    if not symbols:
        return {}
    table = "symbol_master" if region == "kr" else "us_symbol_master"
    placeholders = {f"s{i}": sym for i, sym in enumerate(symbols)}
    keys = ", ".join(f":{k}" for k in placeholders)
    sql = text(f"SELECT symbol, name FROM {table} WHERE symbol IN ({keys})")
    try:
        rows = session.execute(sql, placeholders).mappings().all()
    except Exception:
        return {}
    out: dict[str, str] = {}
    for r in rows:
        name = r.get("name")
        if name:
            out[r["symbol"]] = name
    return out


# ── high-level dispatch ──────────────────────────────────────────────────────


_SessionFactory = Callable[[], Session]


def dispatch_daily_email(
    region: Region,
    target_date: date_cls,
    recipient: str,
    excel_path: Path | str,
    *,
    dry_run: bool = False,
    smtp_config: SMTPConfig | None = None,
    session_factory: _SessionFactory | None = None,
    log_path: Path | str = DEFAULT_LOG_PATH,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_backoff: float = DEFAULT_INITIAL_BACKOFF_SEC,
    exponential_factor: float = DEFAULT_EXPONENTIAL_FACTOR,
    now: datetime | None = None,
) -> EmailDispatchRecord:
    """Fetch rows, build body, send (or skip), and log."""
    if region not in ("kr", "us"):
        raise ValueError(f"region must be 'kr' or 'us', got {region!r}")
    excel_path = Path(excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel attachment not found: {excel_path}")

    if session_factory is None:
        from core.db import make_session_factory  # local import — DB optional in tests

        session_factory = make_session_factory()

    session = session_factory()
    try:
        rows = list(fetch_daily_analysis(session, target_date, region))
        entries = [r for r in rows if r.classification == "entry"]
        watches = [r for r in rows if r.classification == "watch"]
        symbols = {r.symbol for r in entries} | {r.symbol for r in watches}
        company_names = fetch_company_names(session, symbols, region)
    finally:
        session.close()

    subject, body = build_email_body(
        region=region,
        target_date=target_date,
        entry_candidates=entries,
        watch_candidates=watches,
        attached_filename=excel_path.name,
        company_names=company_names,
        now=now,
    )

    # Graceful fallback (Sprint 3) — prepend a warning if the prior dispatch
    # for this region failed, so the next sent email surfaces the gap.
    prior = read_last_dispatch_for_region(region, log_path=log_path)
    warning = build_prior_failure_warning(prior)
    if warning:
        body = f"{warning}\n\n{body}"

    if dry_run:
        record = EmailDispatchRecord(
            timestamp=(now or datetime.now().astimezone()).isoformat(timespec="seconds"),
            region=region,
            date=target_date.isoformat(),
            recipient=recipient,
            subject=subject,
            attached_filename=excel_path.name,
            attached_size_bytes=excel_path.stat().st_size,
            status="dry_run",
            smtp_response=None,
            error_message=None,
            retry_count=0,
        )
    else:
        if smtp_config is None:
            smtp_config = SMTPConfig.from_env()
        record = send_email(
            config=smtp_config,
            recipient=recipient,
            subject=subject,
            body=body,
            attachment_path=excel_path,
            region=region,
            target_date=target_date,
            max_retries=max_retries,
            initial_backoff=initial_backoff,
            exponential_factor=exponential_factor,
            now=now,
        )

    append_dispatch_log(record, log_path=log_path)
    return record


__all__ = [
    "SMTPConfig",
    "EmailDispatchRecord",
    "build_email_body",
    "send_email",
    "append_dispatch_log",
    "read_last_dispatch_for_region",
    "build_prior_failure_warning",
    "dispatch_daily_email",
    "fetch_company_names",
    "DEFAULT_LOG_PATH",
]
