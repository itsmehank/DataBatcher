"""
SQLAlchemy 2.0 ORM 모델 — llm_calls, daily_analysis_kr, daily_analysis_us.

마이그레이션은 db/migrations/versions/20260428_000001_*.py 및
db/migrations/sql/20260428_000001_*.sql에서 이미 적용됨.
본 파일은 Python-side ORM 매핑만 담당.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# SQLite は BIGINT PRIMARY KEY でのオートインクリメントをサポートしないため
# id 列は Integer (Python int = arbitrary precision) を使用する。
# MySQL 本番は migration SQL で BIGINT AUTO_INCREMENT として作成済み — ORM は読み書きのみ担当。


class Base(DeclarativeBase):
    pass


class LlmCall(Base):
    """llm_calls 테이블 ORM 모델. 헌법 §2.5 — 모든 LLM 호출 영구 보존."""

    __tablename__ = "llm_calls"

    id:                Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp:         Mapped[datetime]        = mapped_column(DateTime, nullable=False, server_default=func.now())
    module:            Mapped[Optional[str]]   = mapped_column(String(50))
    model:             Mapped[Optional[str]]   = mapped_column(String(50))
    prompt_tokens:     Mapped[Optional[int]]   = mapped_column(Integer)
    completion_tokens: Mapped[Optional[int]]   = mapped_column(Integer)
    cost_usd:          Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    request_payload:   Mapped[Optional[dict]]  = mapped_column(JSON)
    response_payload:  Mapped[Optional[dict]]  = mapped_column(JSON)
    duration_ms:       Mapped[Optional[int]]   = mapped_column(Integer)
    error:             Mapped[Optional[str]]   = mapped_column(Text)


class DailyAnalysisKR(Base):
    """daily_analysis_kr 테이블 ORM 모델. KR 주식 LLM 차트 분석 결과."""

    __tablename__ = "daily_analysis_kr"

    symbol:             Mapped[str]            = mapped_column(String(32), primary_key=True, nullable=False)
    date:               Mapped[date]           = mapped_column(Date, primary_key=True, nullable=False)
    market:             Mapped[str]            = mapped_column(String(16), nullable=False)
    classification:     Mapped[str]            = mapped_column(String(20), nullable=False)
    confidence:         Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    reasoning:          Mapped[Optional[str]]  = mapped_column(Text)
    pattern:            Mapped[Optional[str]]  = mapped_column(String(50))
    risk_flags:         Mapped[Optional[dict]] = mapped_column(JSON)
    entry_params:       Mapped[Optional[dict]] = mapped_column(JSON)
    screen_config_hash: Mapped[Optional[str]]  = mapped_column(String(40))
    llm_call_id:        Mapped[Optional[int]]  = mapped_column(BigInteger)
    created_at:         Mapped[datetime]       = mapped_column(DateTime, nullable=False, server_default=func.now())


class DailyAnalysisUS(Base):
    """daily_analysis_us 테이블 ORM 모델. US 주식 LLM 차트 분석 결과."""

    __tablename__ = "daily_analysis_us"

    symbol:             Mapped[str]            = mapped_column(String(32), primary_key=True, nullable=False)
    date:               Mapped[date]           = mapped_column(Date, primary_key=True, nullable=False)
    market:             Mapped[str]            = mapped_column(String(16), nullable=False)
    classification:     Mapped[str]            = mapped_column(String(20), nullable=False)
    confidence:         Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    reasoning:          Mapped[Optional[str]]  = mapped_column(Text)
    pattern:            Mapped[Optional[str]]  = mapped_column(String(50))
    risk_flags:         Mapped[Optional[dict]] = mapped_column(JSON)
    entry_params:       Mapped[Optional[dict]] = mapped_column(JSON)
    screen_config_hash: Mapped[Optional[str]]  = mapped_column(String(40))
    llm_call_id:        Mapped[Optional[int]]  = mapped_column(BigInteger)
    created_at:         Mapped[datetime]       = mapped_column(DateTime, nullable=False, server_default=func.now())


class SyncLog(Base):
    """
    sync_log 테이블 ORM 모델 (read+write).

    ingest-databatcher의 결정론 코어가 사용하는 같은 테이블에 LLM 분석 레이어가
    write-only로 합류한다 (헌법 §2.2 — DB는 공유, 함수 import 안 함).

    ADR-012 §3.2: 일일 상한 초과·이상 이벤트를 sync_log에 status='WARN'/'ERROR' 기록.
    job_name 컨벤션:
      - 'llm_analysis_kr' / 'llm_analysis_us'                 — run_daily_analysis 작업 마커
      - 'llm_daily_call_limit'                                 — 한도 초과 이벤트
      - 'llm_terms_violation_signal'                           — ADR-012 §3.3 경고 패턴 감지
      - 'llm_token_spike'                                      — 1.1.7 후속 (프롬프트 토큰 폭증)
    """
    __tablename__ = "sync_log"

    # Integer (Python int = arbitrary precision) for SQLite autoincrement compat;
    # MySQL prod is BIGINT AUTO_INCREMENT (created by ingest-databatcher migrations).
    id:             Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_name:       Mapped[str]            = mapped_column(String(64), nullable=False)
    market:         Mapped[str]            = mapped_column(String(16), nullable=False)
    symbol:         Mapped[Optional[str]]  = mapped_column(String(32))
    start_time:     Mapped[datetime]       = mapped_column(DateTime, nullable=False)
    end_time:       Mapped[Optional[datetime]] = mapped_column(DateTime)
    rows_processed: Mapped[Optional[int]]  = mapped_column(Integer, default=0)
    status:         Mapped[str]            = mapped_column(String(16), nullable=False)
    message:        Mapped[Optional[str]]  = mapped_column(String(1024))
    created_at:     Mapped[datetime]       = mapped_column(DateTime, nullable=False, server_default=func.now())
