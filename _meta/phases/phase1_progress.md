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
| 1.1.8 (5) 프롬프트 v1 작성 | ✅ 완료 | prompts/analyze_chart_v1.md. brief §6.2 본문 그대로. |
| 1.1.9 data_loader.py 구현 | ✅ 완료 | core/data_loader.py. 일봉 60행 + 주봉 52주 + 인디케이터 + conditions_met(NULL 허용). |
| 1.1.10 prompt_builder.py 구현 | ✅ 완료 | core/prompt_builder.py. 템플릿 로드 + JSON 페이로드 결합. |
| 1.1.11 result_parser.py + AnalysisResult 모델 | ✅ 완료 | core/result_parser.py + models/analysis_result.py. 단위 테스트 13/13 통과. |
| 1.1.12 run_single_symbol.py CLI | ✅ 완료 | scripts/run_single_symbol.py. --symbol/--region/--date/--backend/--dry-run/--force-recompute 지원. |
| 1.1.13 단일 종목 검증 (CLI 백엔드, 5종목) | ✅ 완료 | AAOI/ABVX/ADV/BWET/CLSM (US) 5종목 실호출 성공. daily_analysis_us 5행 + llm_calls 기록 확인. |
| 1.1.14 단일 종목 검증 (API 백엔드, 1회) | ⏸ 연기 | 1.1.4-c 결정 그대로 유지. CLI가 운영 백엔드. |
| 1.1.15 프롬프트 튜닝 + v1 확정 | 🔄 진행 중 | 외부 평가 완료. 약점 7가지 진단. v2 작성 + Pydantic 갱신 + 테스트 25/25. 5종목 재호출 승인 대기. |

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

- [HIGH / ADR 후보] 미너비니 스크리너에서 ETF 제외 필요.
  근거: 1.1.13 표본 5종목 중 2개(BWET, CLSM)가 ETF(market='ETF')였음.
  문제: 스크리너가 ETF를 거르지 않으면 분석 LLM이 매일 ETF에 대해 호출되어 비용·한도 낭비.
  v1에서 CLSM(ETF)을 "entry"로 분류하는 사용자 정책 위반이 발생함.
  해결 방향: minervini_screen_results_us 집계 시 us_symbol_master.symbol_type = 'ETF' 행 제외 (JOIN 조건 추가),
  또는 run_daily_analysis.py 호출 목록에서 ETF 필터링. ADR로 설계 결정 기록 필요.

- [ADR 후보] daily_analysis 테이블에 prompt_version 컬럼 추가 + PK 확장 검토.
  근거: v2 force-recompute 시 DELETE+INSERT 방식으로 v1 결과가 overwrite됨.
  개선안: (symbol, date, prompt_version)을 PK로 확장하면 v1/v2 행을 동시에 보존 가능.
  현재 우회: eval_input.json + llm_calls 테이블로 v1 결과 보존. 운영 부담 없으면 현행 유지도 가능.
  Phase 1 게이트 통과 후 Architect 세션에서 판단.

[1.3 검증 시 우선순위 항목]
- [v2.1 후보] AAOI reverse_split 누락 — price_data_notes의 split 정보를 deterministic하게 소비하도록 v3 prompt 보강 검토.
  평가 LLM 지적: "작은 ratio(~1.65:1) + 오래된 split도 일관되게 flag되어야 함."
  현재 v2는 split ratio threshold에 암묵적 의존. 명시적 조건 추가 시 개선 가능.
- [1.3 모니터링] completion 토큰 폭증 (v1 평균 ~1,800 → v2 평균 ~3,000, 60% 증가).
  ignore 케이스용 "tight reasoning" 지시 검토. ADR-012 §3.4 호출 로그 점검에서 cost 영향 확인.
- [1.3 검증 배치] entry 후보 5~10종목 별도 검증으로 pivot/breakout 정확도 (약점 F) 검증.
  현재 표본 5종목은 all-ignore/ETF라 F 항목이 untestable. 1.3 누적 데이터 활용.
- [1.3 자동화] reasoning 사실 정확성 sanity check — reasoning의 구체 숫자(volume, % 수치)가 source data와 일치하는지 자동 비교.
- [1.3 taxonomy 검토] 추가 flag 후보: `late_stage_base`, `distribution_days`, `reversal_off_high` (평가 LLM 제안). 1.3 운영 빈도 확인 후 추가 결정.

---

## 단계 1.2 — calculate_entry_params 구현

### 1.2.0-A — ADR-013 구현 (2026-05-03)

- **ETF 제외 필터**: `us_minervini_update.py`, `kr_minervini_update.py`에 ADR-013 option (a) 적용
  - `load_symbols_with_details` / `load_us_symbols_with_details` 에 `symbol_type` 필드 추가 (backward-compatible)
  - 종목 목록 로드 후 `d.get("symbol_type") != "ETF"` 조건으로 ETF 제외
  - `prices_wide` 에서도 non_etf_symbols 집합으로 ETF 컬럼 drop
- **KR/US 동일 정책**: 두 시장 모두 `symbol_type = 'ETF'` 기준으로 제외 (market='ETF'와 100% 일치 확인)
- **기존 행 보존** (ADR-013 §4.i 채택): `minervini_screen_results_us` ETF 177,065행 / `_kr` ETF 77,353행 그대로 보존
- **단위 테스트**: `scripts/tests/test_minervini_etf_exclusion.py` — 9/9 통과
  - US/KR ETF 제외 검증, symbol_type=NULL 처리, prices_wide 컬럼 제거, end-to-end pass_mask 검증
- **브랜치**: `phase1/1.2-entry-params`
- **다음**: 1.2.1 calculate_entry_params 프롬프트 v1 작성

### 1.2 후속 작업 등록

- [후속 검토] KR 시장 KONEX 종목의 미너비니 스크리닝 포함 여부 — ADR-013 사전 점검(2026-05-03) 시 발견.
  KONEX 110종목이 symbol_master에 ACTIVE이나 현재 minervini_screen_results_kr에는 0건(자연 통과 없음).
  KONEX 포함/제외 정책을 명시할지 사용자 결정 필요. ADR-013 구현 후에도 KONEX는 현행 동작(포함 가능 상태) 유지.


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

## 1.1.8~1.1.13 완료 메모 (2026-04-28)

### 구현 파일
- `prompts/analyze_chart_v1.md`: brief §6.2 프롬프트 본문. "## Input Payload" 섹션으로 끝남 — prompt_builder가 JSON을 이어붙임.
- `models/analysis_result.py`: `AnalysisResult` Pydantic 모델. `classification`, `confidence`, `pattern`, `risk_flags` 화이트리스트 검증 포함.
- `core/result_parser.py`: `parse_analysis_result()` + `ParseError`. markdown fence 재제거 + JSON 파싱 + Pydantic 검증.
- `core/data_loader.py`: `load_symbol_payload()` + `get_screened_symbols()`. 일봉 60행 / 주봉 52주 / 인디케이터 pivot / 52주 고가·저가·volume_ma20 계산. `conditions_met` NULL 허용(P0.5 이전 데이터 대응).
- `core/prompt_builder.py`: `build_analyze_chart_prompt()` + `build_entry_params_prompt()`. 템플릿 로드 + JSON 직렬화 결합.
- `scripts/run_single_symbol.py`: 완전한 CLI. --symbol/--region/--date/--backend/--dry-run/--force-recompute. ParseError 발생 시 1회 LLM 재호출.

### 데이터 수정 사항
- `us_symbol_master`에 `sector_detail` 열 없음 → `sector, industry` 쿼리로 수정 (KR/US 공통).

### 1.1.13 검증 결과 (2026-04-28, DEV DB, US 5종목)

| symbol | classification | confidence | pattern | risk_flags |
|---|---|---|---|---|
| AAOI | ignore | 0.95 | none | high_rs_rating, extended_from_ma50 |
| ABVX | ignore | 0.80 | cup_handle | high_rs_rating, low_volume |
| ADV | ignore | 0.95 | none | high_rs_rating, thin_base, low_volume |
| BWET | ignore | 0.95 | none | high_rs_rating, extended_from_ma50, thin_base |
| CLSM | entry | 0.72 | flat_base | high_rs_rating |

- 응답 품질: 각 종목의 클라이맥스 런·리버스스플릿·베이스 패턴을 정확히 식별. CLSM은 22주 flat base + 브레이크아웃 직후를 `entry`로 올바르게 판단.
- 토큰: 약 21,000 input / 1,400~2,100 output. 프롬프트 길이 ~30,700자.
- 비용: 호출당 $0.05~$0.12 (cli 모드, Max 플랜 참고값 — 실제 청구는 Max 구독료).
- `daily_analysis_us` 5행, `llm_calls` 7행 (기존 1행 포함) DEV DB에 기록 확인.

### 1.1.15 사용자 검토 포인트
- 응답 품질이 이미 안정적이면 → v1 확정 + 1.2로 이동.
- 추가 튜닝 필요 시 → `prompts/analyze_chart_v1.md` 수정 후 `--force-recompute`로 재검증. 큰 변경만 v2.
- 1.1.13 결과에서 주목할 점: `ignore` 4건 / `entry` 1건. 상위 RS 종목이 과열된 2026-04 시장 상황 반영. 정상.

## 1.1.15 v2 작성 메모 (2026-05-01)

### v1 결과 백업 현황

`_save_result()`는 DELETE+INSERT 방식 — `--force-recompute` 실행 시 `daily_analysis_us`의 v1 행이 overwrite됨.
v1 결과 보존 경로:
- `/tmp/eval_export/*.json` + `/Users/hank.es/Downloads/` (eval_input.json 5종목)
- `llm_calls` 테이블 (request_payload + LLM 원본 응답 보존): id 2=AAOI, 4=ABVX, 5=ADV, 6=BWET, 8=CLSM

### 외부 평가 진단 (Architect → Builder) — 약점 7가지

| ID | 우선순위 | 약점 | 근거 |
|---|---|---|---|
| A | HIGH | risk_flags 카테고리 에러 | 5/5에서 `high_rs_rating` 포함 — RS 99는 양성 신호인데 위험으로 분류 |
| B | HIGH | reasoning ↔ risk_flags 불일치 | reasoning에 "climax run", "wide-and-loose" 명시했지만 해당 flag 없음 |
| C | HIGH | reverse split 미탐지 | price_data_notes에 corporate action 있어도 `reverse_split_distortion` flag 없음 |
| D | HIGH | ETF 탐지 부재 | BWET을 개별 주식처럼 분석. 정책: ETF면 즉시 ignore + etf_methodology_mismatch |
| E | MEDIUM | pattern naming discipline 부족 | ABVX를 cup_handle로 명명, 실제 구조 부재 |
| F | MEDIUM | pivot/breakout 정확도 | CLSM pivot $24.00 (실제 $24.50), breakout date 1주 어긋남 |
| G | LOW | liquidity 보고 | US ADV < $5M → thin_liquidity_us_only (informational), KR은 평가 안 함 |

### v1 → v2 주요 변경 사항

| 약점 | 수정 위치 | 내용 |
|---|---|---|
| A+B+C | §5 Risk Flags | 12개 taxonomy로 제한. "Trend Template 양성 특성은 NEVER risk_flags" 명시. reasoning↔flags 일관성 규칙. `reverse_split_distortion` 트리거 조건 명시. |
| D | Pre-Check (프롬프트 최상단) | `market == "ETF"` 또는 fund vehicle 감지 시 즉시 ignore+etf_methodology_mismatch 반환 |
| E | §4 Base Pattern | 패턴별 textbook 정의 표 추가. "구조 부재 시 none 사용" 명시. `cup_handle`→`cup_with_handle`, `VCP`→`vcp` |
| F | §6 Pivot & Breakout | pivot = max(weekly.high) + $0.10 명시. breakout_date 정의. 실제 데이터 불일치 시 confidence -0.2 |
| G | §5 Rule 3 | thin_liquidity_us_only: US 개별주만, volume_ma20×price < $5M. KR은 평가 안 함. |
| 수정 6 | §7 Confidence | calibration 규칙 4개 명시 (reasoning 품질, pattern-data 불일치, multi-flag, high confidence 조건) |

### Pydantic 모델 변경 (models/analysis_result.py)

VALID_PATTERNS (v1 → v2):
- 제거: `cup_handle`, `VCP`
- 추가: `cup_with_handle`, `vcp`
- 유지: `flat_base`, `double_bottom`, `none`

VALID_RISK_FLAGS (v1 → v2):
- 제거: `high_rs_rating`, `extended_from_ma50`, `low_volume`, `thin_base`, `earnings_imminent`, `market_weakness`, `sector_overconcentration`
- 추가: `climax_run`, `late_stage_base`, `extended_from_ma`, `faulty_pivot`, `low_volume_breakout`, `narrow_base`, `wide_and_loose`, `thin_liquidity_us_only`, `prior_uptrend_insufficient`, `volume_contraction_on_advance`, `reverse_split_distortion`, `etf_methodology_mismatch`

단위 테스트: 25/25 통과 (기존 13 갱신 + v2 신규 12)

### v1 결과 백업 (2026-05-02)

- 파일: `/tmp/eval_export/v1_results_backup.json` (4,629B) + Downloads 복사
- 5종목 포함 확인. llm_call_ids: AAOI=2, ABVX=4, ADV=5, BWET=6, CLSM=8
- 중요 발견: BWET + CLSM 모두 `market='ETF'` — 5종목 중 2개가 ETF

### v2 5종목 재호출 완료 (2026-05-02)

settings.yaml timeout_seconds 60→120 조정 (v2 프롬프트 길어져 AAOI 첫 시도 timeout).

| symbol | type | v1 날짜 | v2 날짜 | v1 분류 | v2 분류 | v1 risk_flags | v2 risk_flags | 핵심 변화 |
|---|---|---|---|---|---|---|---|---|
| AAOI | stock | 04-10 | 04-27 | ignore (0.95) | ignore (0.90) | high_rs_rating, extended_from_ma50 | climax_run, extended_from_ma, wide_and_loose | flag 교정 |
| ABVX | stock | 04-10 | 04-17 | ignore (0.80) | ignore (0.75) | high_rs_rating, low_volume | climax_run, wide_and_loose, reverse_split_distortion | cup_handle→none, split flag |
| ADV | stock | 04-10 | 04-27 | ignore (0.95) | ignore (0.90) | high_rs_rating, thin_base, low_volume | reverse_split_distortion, climax_run, wide_and_loose, thin_liquidity_us_only | split + liquidity flag |
| BWET | ETF | 04-10 | 04-27 | ignore (0.95) | ignore (1.0) | high_rs_rating, extended_from_ma50, thin_base | etf_methodology_mismatch | Pre-Check 9초 즉시 종료 |
| CLSM | ETF | 04-10 | 04-27 | **entry (0.72)** | **ignore (1.0)** | high_rs_rating | etf_methodology_mismatch | **분류 반전** ✓ |

핵심 검증 결과:
- ETF 탐지 (BWET, CLSM 2/2): ✅ confidence=1.0, etf_methodology_mismatch, 각 9·11초 즉시 종료
- CLSM 분류 반전 (entry→ignore): ✅ v2 핵심 교정 확인
- high_rs_rating 제거 (5/5): ✅ v2에서 단 1건도 없음
- reverse_split_distortion 자동 포함: ✅ ABVX(~Jul 2025), ADV(2026-03-26) 정확 탐지. AAOI는 price_data_notes의 이벤트가 모멘텀 급등으로 판단 (합리적 — vol_ratio 역전 없음)
- thin_liquidity_us_only: ✅ ADV $3.2M daily dollar volume 직접 계산해 적용
- taxonomy 외 flag 출력: 0건 ✅ (단위 테스트 whitelist 통과)
- pattern naming: ✅ ABVX cup_handle → none 교정

prompt_tokens: 22,617~22,756 (평균 22,715, v1 평균 21,451 대비 +1,264 — v2 프롬프트 길이 증가)
duration_ms: AAOI 77s, ABVX 70s, ADV 64s, BWET 9s, CLSM 11s

export 파일 (Downloads + /tmp/eval_export/):
- 5종목 _eval_input_v2.json (v2 결과 eval_input 포맷)
- 5종목 _v1_v2_comparison.json (v1 vs v2 key_differences)
- v1_results_backup.json

⚠️ 주의: v2 분석 날짜가 v1(2026-04-10)과 다름 — `--date` 미지정 시 MAX(date) 사용. 비교 시 데이터 시차 혼재. `_v1_v2_comparison.json`에 note 기재.

## 1.1 게이트 체크리스트 (2026-05-02)

phase1_brief.md §9.1 기준:

| # | 항목 | 결과 | 비고 |
|---|---|---|---|
| 1 | daily_analysis_kr, daily_analysis_us, llm_calls 테이블 DEV 존재 | ✅ | Alembic 마이그레이션 적용 완료, llm_calls 18건 기록 확인 |
| 2 | Q-002 운영 큐 항목 등록됨 | ✅ | 텍스트 작성 완료. 운영 적용은 Architect 영역 (PROD 접근 필요) |
| 3 | apps/llm-analysis/ 디렉토리 구조 §5.2와 일치 | ✅ | 1.1.3에서 25파일 구조 검증 |
| 4 | LLMBackend 인터페이스 + CLI·API 두 구현체 | ✅ | core/anthropic_client.py. mock 단위 테스트 통과 |
| 5 | 표본 5종목 CLI 백엔드 (5) 호출 성공 (실패 ≤ 1건) | ✅ | v1 5종목 + v2 5종목 = 총 10건. timeout 재시도 포함 최종 실패 0건 |
| 6 | 표본 1종목 API 백엔드 (5) 호출 성공 | ⏭️ | 사용자 결정으로 미룸 (1.1.4-c). mock 단위 테스트로 추상화 검증. 전환 결정 시 수행 |
| 7 | AnalysisResult 스키마 준수 | ✅ | v2 whitelist 25/25 통과. v2 5종목 실호출 parse 성공, taxonomy 위반 0건 |
| 8 | llm_calls 테이블 호출 로그 기록 | ✅ | 18건 기록 (v1 7건 + v2 5건 + timeout 재시도 포함) |
| 9 | daily_analysis_us에 결과 행 생성 | ✅ | v2 5종목 결과 행 존재 |
| 10 | (5) 프롬프트 v1 확정 commit | ✅→v2 | v1 보존, v2를 production prompt로 lock. 외부 평가 production-ready 판정 |
| 11 | phase1_progress.md에 1.1 종료 보고 작성 | ✅ | 이 섹션 |

**결과: 10/11 통과 (⏭️ 1건 — 사용자 승인 결정으로 미룸. Phase 1 진행에 영향 없음)**

---

## 1.1 단계 종료 보고 (2026-05-02)

**종료 일시**: 2026-05-02

### 단계별 완료 현황

| 항목 | 상태 |
|---|---|
| 1.1.1 DB 마이그레이션 3종 산출물 | ✅ 완료 |
| 1.1.2 운영 환경 마이그레이션 적용 | ⏳ 사용자 직접 (Q-002) |
| 1.1.3 apps/llm-analysis/ 골격 | ✅ 완료 |
| 1.1.4 LLMBackend 인터페이스 | ✅ 완료 |
| 1.1.5 CLI 백엔드 | ✅ 완료 |
| 1.1.6 API 백엔드 | ✅ 완료 (mock 검증) |
| 1.1.7 llm_calls 기록 wrapper | ✅ 완료 |
| 1.1.8 프롬프트 v1 작성 | ✅ 완료 (v1 보존, v2로 승계) |
| 1.1.9 data_loader.py | ✅ 완료 |
| 1.1.10 prompt_builder.py | ✅ 완료 |
| 1.1.11 result_parser + AnalysisResult | ✅ 완료 (v2 taxonomy 갱신) |
| 1.1.12 run_single_symbol.py CLI | ✅ 완료 |
| 1.1.13 단일 종목 검증 5종목 | ✅ 완료 |
| 1.1.14 API 백엔드 단일 종목 검증 | ⏭️ 미룸 (사용자 결정) |
| 1.1.15 프롬프트 튜닝 v2 + 외부 평가 | ✅ 완료 |

### v1 → v2 전환 완료

**production prompt = `prompts/analyze_chart_v2.md`** (settings.yaml `prompts.analyze_chart: "v2"`)
v1은 `prompts/analyze_chart_v1.md`로 보존.

### 외부 평가 결과 (Web Claude Minervini Evaluator, Opus 4.7)

| 약점 | 차원 | 결과 |
|---|---|---|
| A (risk_flags 카테고리 에러) | HIGH | ✅ improved — high_rs_rating 5/5 제거 |
| B (reasoning↔flag 불일치) | HIGH | ✅ improved — climax_run 등 flag 일관성 확보 |
| C (reverse_split 미탐지) | HIGH | ⚠️ partial — ABVX/ADV 자동 감지, AAOI 누락 (ratio 작고 시기 오래됨) |
| D (ETF 탐지 부재) | HIGH | ✅ improved — BWET/CLSM 2/2 즉시 감지, CLSM entry→ignore 반전 |
| E (pattern naming discipline) | MEDIUM | ✅ improved — ABVX cup_handle→none 교정 |
| F (pivot/breakout 정확도) | MEDIUM | ⏭️ untestable — 표본 5종목 모두 ignore/ETF, entry 후보 없음 |
| G (liquidity 정책) | LOW | ✅ improved — ADV thin_liquidity_us_only $3.2M 자동 계산 |

**평가 최종 판정: production-ready (5종목 evaluator_verdict: agree)**

### 1.1 게이트 통과

10/11 ✅ (API 백엔드 실호출 1건 ⏭️ — 사용자 결정)

### 다음 단계

**1.2**: `calculate_entry_params()` — entry 후보 종목에 대한 진입 파라미터 산출
- `prompts/calculate_entry_params_v1.md` 작성
- `EntryParams` Pydantic 모델
- `run_single_symbol.py --with-entry-params`
- 표본 entry 종목 5건 이상 검증

## 주간 운영 메모

(Phase 1.3 시작 후부터 ADR-012 §3.4 호출 로그 점검 결과를 기록)

---

*이 기록은 `_meta/00_CONSTITUTION.md` §5에 따라 Builder가 작성한 Phase 진행 로그다.*