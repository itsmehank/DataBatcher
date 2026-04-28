# Phase 1 — LLM 분석 레이어 구축 진행 기록

> 작성: Builder (Claude Code CLI)
> 브랜치: `phase1/1.1-llm-analysis-skeleton`
> 시작 일시: 2026-04-28

---

## 단계 1.1 — DB 마이그레이션 + (5) 분석 함수 구현 + 백엔드 추상화 검증

### 1.1 시작 (2026-04-28)

| 항목 | 상태 | 비고 |
|---|---|---|
| 1.1.1 DB 마이그레이션 3종 산출물 | ✅ 완료 | Alembic + raw SQL(db/migrations/sql/) + Q-002 텍스트. DEV DB upgrade 완료. |
| 1.1.2 운영 환경 마이그레이션 적용 | ⏳ 대기 | 사용자 직접 — Q-002 완료 처리 |
| 1.1.3 apps/llm-analysis/ 디렉토리 골격 | ✅ 완료 | 25파일, brief §5.2 구조 일치. pyproject.toml 생략(requirements.txt로 충분). |
| 1.1.4 LLMBackend 추상화 인터페이스 정의 | ✅ 완료 | core/anthropic_client.py. CLI sanity check + CLAUDE.md 탐색 진단 후 확정. |
| 1.1.5 CLI 백엔드 구현 | ✅ 완료 | ClaudeCodeCLIBackend. cwd=tempfile.gettempdir(). |
| 1.1.6 API 백엔드 구현 | ✅ 완료 | AnthropicAPIBackend (84줄). 단위 테스트(mock) 통과. 실제 SDK 호출 미수행 — 사용자 결정. |
| 1.1.7 llm_calls 기록 wrapper | ✅ 완료 | core/llm_call_recorder.py. 재시도 + INSERT. daily_call_limits hook placeholder 포함. |
| 1.1.8 (5) 프롬프트 v1 작성 | ⏳ 대기 | prompts/analyze_chart_v1.md |
| 1.1.9 data_loader.py 구현 | ⏳ 대기 | |
| 1.1.10 prompt_builder.py 구현 | ⏳ 대기 | |
| 1.1.11 result_parser.py + AnalysisResult 모델 | ⏳ 대기 | |
| 1.1.12 run_single_symbol.py CLI | ⏳ 대기 | |
| 1.1.13 단일 종목 검증 (CLI 백엔드, 5종목) | ⏳ 대기 | |
| 1.1.14 단일 종목 검증 (API 백엔드, 1회) | ⏳ 대기 | |
| 1.1.15 프롬프트 튜닝 + v1 확정 | ⏳ 대기 | |

---

## 1.1 종료 시 Architect에 인계할 후속 작업

- [ARCHITECTURE.md §5] LLM 외부 의존성 표를 "Anthropic API or Claude Code CLI (ADR-011)"로 갱신 필요
  - 현재: "Anthropic API — Claude Code CLI는 약관·안정성 문제로 운영 환경에 부적합 (ADR-003)"
  - 변경 후: "Anthropic API or Claude Code CLI (Phase 1 기본: CLI + Max 플랜, ADR-011)"

- [ADR-010 §1] 마이그레이션 3종 산출물의 raw SQL 위치를 `apps/ingest-databatcher/scripts/migrations/`에서 `db/migrations/sql/`으로 갱신 필요
  - Phase 1 1.1 결정 사례 (2026-04-28): `db/migrations/sql/20260428_000001_add_daily_analysis_and_llm_calls.sql`
  - 결정 근거: ADR-010 §2 정신 부합 + Alembic 파일과 물리적 근접 + 앱 독립성 유지
  - ADR-010 §1 본문의 "apps/ingest-databatcher/scripts/migrations/" 표기를 `db/migrations/sql/`으로 수정 필요

- [alembic.ini 자격증명] `db/migrations/alembic.ini`의 `sqlalchemy.url` placeholder("root:root@...")가 실제 DEV 자격증명(`.env` DATABASE_URL "hank:1234!")과 불일치.
  현재는 DATABASE_URL 환경변수 override로 정상 동작 중이므로 영향 없음. 다음 결정 필요:
  - (a) alembic.ini의 url을 env 참조 방식으로 변경 (예: `%(DATABASE_URL)s`)
  - (b) placeholder 유지 + README/CLAUDE.md에 "DATABASE_URL이 SSoT" 명시
  PROD의 alembic.ini 상태도 함께 점검 필요. Phase 1.1 종료 시 Architect 세션에서 판단.

- [ADR-011 §3] cost_usd 처리 표 갱신: CLI 모드에서 참고값 저장 가능.
  NULL "허용"이지 "강제"가 아님을 명시. cost_source/max_plan_billing 메타 사용 명시.

- [phase1_brief.md §9.1] 1.1 게이트의 "CLI/API 양 백엔드로 같은 종목 호출 검증" 항목을 다음으로 갱신 필요:
  - "CLI 백엔드: 표본 5종목 호출 검증 (필수)"
  - "API 백엔드: 단위 테스트(mock)로 추상화 검증 완료. 실제 SDK 호출은 (a) Phase 1 후반 사용자 결정 또는 (b) ADR-012 §3.3 약관 위반 징후 시 또는 (c) ADR-013 백엔드 전환 결정 시 수행."
  갱신 사유: ADR-011·ADR-012의 운영 백엔드가 CLI이고 API는 fallback이라, 실제 SDK 검증 시점을 전환 결정 시로 미루는 게 비용·위험 측면에서 합리적.

- [1.1.7 wrapper / ADR-012 §3.2] 프롬프트 토큰 폭증 감지 로직 추가 필요.
  근거: Phase 1.1.4-b 진단에서 CLAUDE.md auto-load 변동으로 66,873 토큰 단발 사고 확인 (정상 ~8,000).
  구현: settings.yaml input_data 추정 토큰 대비 2배 이상 시 sync_log WARN 기록.
  위치: core/llm_call_recorder.py (call_and_record 내 또는 cost_tracker와 함께, 1.3 구현 시점).


---

## Q-002 등록 대기

> 아래 텍스트는 `_meta/operational_queue.md`의 "대기 중인 작업" 섹션에 등록할 내용이다.
> Builder가 직접 수정할 수 없는 문서이므로 (ADR-005), 1.1 종료 시 Architect 세션이 옮겨 적는다.

---

### Q-002: Phase 1 DB 마이그레이션 적용 — daily_analysis_kr, daily_analysis_us, llm_calls (등록: 2026-04-28, 완료: 미정)

**관련 commit**: `phase1/1.1-llm-analysis-skeleton` 브랜치 머지 commit (머지 후 hash 기입 예정)
**관련 ADR**: ADR-009 (LLM 분석 테이블 설계), ADR-010 (마이그레이션 3종 산출물)
**Alembic revision**: `20260428_000001` (down_revision: `20260424_000001`)
**raw SQL 파일**: `db/migrations/sql/20260428_000001_add_daily_analysis_and_llm_calls.sql`
**위험도**: 중간 (DB 변경 — CREATE TABLE 3개, 롤백 가능)
**예상 소요**: 5분 미만 (CREATE TABLE 3개, 기존 테이블 없음)
**타이밍 윈도우**: KR cron(19:00) · US cron(08:00) 각각 직전 30분을 피하면 어느 시각이든 안전

**적용 전 사전 확인**:

```powershell
# 1. git pull 상태 확인
cd C:\path\to\DataBatcher
git log --oneline -3

# 2. 대상 테이블 미존재 확인 (둘 다 빈 결과여야 함)
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "SHOW TABLES FROM trade LIKE 'daily_analysis%';"
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "SHOW TABLES FROM trade LIKE 'llm_calls';"
```

**적용 (raw SQL 직접 실행 — 이번에도 Alembic 미사용, 이슈 §G 유지)**:

```powershell
cd C:\path\to\DataBatcher
git pull

Get-Content db\migrations\sql\20260428_000001_add_daily_analysis_and_llm_calls.sql | `
  docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" trade
```

**적용 후 검증 (세 테이블 DESCRIBE)**:

```powershell
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.daily_analysis_kr;"
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.daily_analysis_us;"
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.llm_calls;"
```

**완료 기준**: 세 테이블의 DESCRIBE 결과가 `_meta/phases/phase1_brief.md` §4.1·§4.2·§4.3 스키마와 일치

**백업**: 생략 (Q-001과 동일 사유 — CREATE TABLE은 기존 데이터 무영향)

**롤백 방법**:

```powershell
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" trade `
  -e "DROP TABLE IF EXISTS llm_calls; DROP TABLE IF EXISTS daily_analysis_us; DROP TABLE IF EXISTS daily_analysis_kr;"
```

**메모**:
- Alembic 적용은 이번에도 생략 (이슈 §G — PROD `alembic_version` 동기화 미해결). raw SQL만 적용.
- 이슈 §G 해소 시점(별도 결정)에 PROD stamp + upgrade head 일괄 처리 예정.

---

## 1.1.4-a 설계 보고 메모 (2026-04-28)

LLMBackend 추상화 설계 확정 (코드 없음):
- LLMResponse Pydantic 모델 (9 필드: text, model, prompt/completion_tokens, cost_usd, duration_ms, request_payload, response_payload, error)
- LLMBackend Protocol (call 메서드 단일)
- ClaudeCodeCLIBackend / AnthropicAPIBackend 두 구현체 계획
- 단일 책임 원칙: Backend = 단일 호출만. 재시도·DB INSERT는 wrapper(1.1.7)에서.
- ADR-011 §3 결정: cost_usd는 CLI에서 NULL 허용 (당시) → 1.1.4-b 이후 β안으로 변경(참고값 저장).

## 1.1.4-d 완료 메모 (2026-04-29)

- models/db_models.py: LlmCall(10필드), DailyAnalysisKR(11필드), DailyAnalysisUS(11필드). SQLAlchemy 2.0 스타일.
  - 비고: LlmCall.id는 `Integer`(SQLite 호환) 사용. MySQL 본番은 migration SQL이 BIGINT AUTO_INCREMENT로 생성하므로 ORM과 불일치 없음.
- core/db.py: make_engine() + make_session_factory(). .env 로드 순서: 루트 → 앱 로컬(override=False).
- core/llm_call_recorder.py: call_and_record() 62줄. _check_daily_call_limit() placeholder.
  - daily_call_limits hook 인터페이스: `(db_session: Session, module: str) -> bool`. 1.3 cost_tracker로 교체 시 시그니처 그대로.
- 단위 테스트 5개 (SQLite in-memory), 통합 검증 1건 (DEV MySQL INSERT/SELECT/DELETE) 모두 통과.

## 1.1.4-c 결정 메모 (2026-04-29)

API 백엔드 표본 호출(실제 SDK 호출) 건너뜀 — 사용자 결정.

근거: 운영 백엔드는 CLI(Max 플랜). API는 fallback 또는 Phase 5 전환 옵션.
본 Phase 운영 중 API 호출 발생 안 함. 키 발급·관리·노출 위험 회피.
검증 수단: 단위 테스트(mock) 16/16 통과. get_backend factory cli/api/unknown 분기 검증.
실제 SDK 호출 검증: (a) 사용자 결정으로 Phase 1 후반 / (b) ADR-012 §3.3 약관 위반 징후 시 / (c) ADR-013 전환 결정 시.
잔존 위험: SDK 응답 객체 구조·에러 클래스명이 가정과 다를 수 있음. 전환 시점에 발견·수정.

## 1.1.4-b 진단 메모 (2026-04-28)

CLI sanity check 및 CLAUDE.md 탐색 범위 진단 결과:

- `claude -p --output-format json`은 cwd + 상위 디렉토리를 탐색해 CLAUDE.md를 자동 로드함.
  DataBatcher 루트에서 실행 시 ~16,000 토큰 / 시스템 temp에서 실행 시 ~7,900 토큰 (49% 절감).
- ClaudeCodeCLIBackend의 `cwd=tempfile.gettempdir()`로 CLAUDE.md/메모리 로드 차단.
- CLAUDE.md 로드 상태에서 단발성 66,873 토큰 사고 1회 발생 (auto-memory 변동 추정). 재현 불가.
- **후속 (1.1.7 wrapper 시점)**: 프롬프트 토큰 폭증 감지 — input_data 추정 대비 2배 이상 시 sync_log WARN. ADR-012 §3.2 항목.

## 주간 운영 메모

(Phase 1.3 시작 후부터 ADR-012 §3.4 호출 로그 점검 결과를 기록)

---

*이 기록은 `_meta/00_CONSTITUTION.md` §5에 따라 Builder가 작성한 Phase 진행 로그다.*