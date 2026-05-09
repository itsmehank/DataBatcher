# 운영 환경 작업 큐 (Operational Queue)

> 로컬에서 변경되었고 운영 환경(집 PC)에서도 적용이 필요한 작업을 기록한다.  
> 개발 환경과 운영 환경이 분리되어 있으므로, 코드 변경(git pull로 자동 반영)과 별개로 **DB 스키마·외부 설정·수동 마이그레이션** 등은 명시적으로 적용해야 한다.  
> 운영 환경에서 작업을 마치면 해당 항목을 "완료" 섹션으로 옮긴다.  
> 새 항목은 항상 "대기" 섹션 맨 위에 추가한다(최신순).
>
> 이 큐의 운영 방식은 ADR-010에서 정의된다.

---

## 환경 정보

### 개발 환경 (DEV)
- **디바이스**: Mac 노트북
- **OS**: macOS
- **셸**: bash / zsh
- **DataBatcher 경로**: (사용자가 채워넣을 것 — 예: `~/work/DataBatcher`)
- **DB**: 로컬 MySQL (Docker)
- **용도**: 코드 작성, 테스트 DB 검증, `_meta/` 문서 관리

### 운영 환경 (PROD)
- **디바이스**: 집 PC (24시간 가동)
- **OS**: Windows
- **셸**: PowerShell
- **스케줄러**: Windows Task Scheduler (`apps/ingest-databatcher/ops/scheduler/windows/*.ps1`)
- **DataBatcher 경로**: (사용자가 채워넣을 것 — 예: `C:\work\DataBatcher`)
- **DB**: MySQL 8.4.8 (Docker 컨테이너 — 컨테이너명 `mysql-standalone-mysql`)
  - 호스트에 `mysql`/`mysqldump` 클라이언트 없음 → 명령은 `docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" ...` 형태로 실행
- **MySQL 자격증명**: `.env`의 `MYSQL_ROOT_PASSWORD` 사용 (Q-001 적용 시 확인됨, 2026-04-26)
- **접속 방법**: 직접 / 원격 데스크톱 / SSH (사용자가 명시)
- **Daily cron 시각**:
  - US daily: 매일 08:00 KST 시작, 최대 6시간 소요 (~14:00 종료)
  - KR daily: 매일 19:00 KST 시작, 최대 30분 소요 (~19:30 종료)

> 비어 있는 항목은 처음 운영 환경 작업할 때 채워넣고 commit한다.

---

## 큐 운영 규칙

1. **새 항목은 "대기" 섹션 맨 위에 추가**. 형식은 Q-001을 템플릿으로 사용.
2. **위험도** 표시: 낮음(코드만, DB 무관) / 중간(DB 변경, 롤백 가능) / 높음(데이터 손실 가능, 백업 필수).
3. **타이밍 윈도우** 명시: cron 충돌 시간을 피해야 하는 작업은 안전 시각 명시.
4. **완료 후 이동**: 작업 완료 시 항목을 "완료" 섹션으로 이동, 완료일·확인 결과 추가.
5. **삭제 금지**: 완료된 항목도 삭제하지 않음. 운영 이력으로 남김.

---

## 대기 중인 작업

### Q-004: us_symbol_master ETF 정정 12건 — symbol_type STOCK→ETF 정정 (등록: 2026-05-08)

**배경**: ADR-013은 Minervini 스크리너에서 ETF를 upstream 필터로 제외하나, us_symbol_master에서 12개 종목이 `symbol_type='STOCK'`으로 잘못 분류되어 필터를 우회함. LLM Pre-Check가 `etf_methodology_mismatch` (conf=1.00)로 안전망 역할을 수행 중 — 즉각 위험 없음. 1.3.10 정성 평가 중 발견 (§10.4 1번 예외로 Builder 직접 등록).  
**관련 ADR**: ADR-013 (ETF 제외 정책) + **ADR-015 (Fund Vehicle 4 카테고리 명확화 + us_symbol_master 정확성 보강, 2026-05-09 채택)**. 본 큐는 ADR-015 §3에 따라 일괄 ETF 처리하고, Phase 2B sprint에서 LEVERAGED_ETF/CEF로 세분화 정정 가능.  
**위험도**: 낮음 (UPDATE — 12행 symbol_type 변경, 롤백 가능)  
**예상 소요**: 5분 미만 (SQL 1건 + 미너비니 스크리너 재실행 확인)  
**우선순위**: 보통 (LLM Pre-Check 안전망 작동 중이므로 즉시 처리 불필요; Phase 2 sprint 진입 전 또는 sprint 내 처리)  
**타이밍 윈도우**: US cron(08:00~14:00) 직후를 피하면 어느 시각이든 안전

**대상 종목 (12건)**:

| 심볼 | 현재 symbol_type | 정정 후 |
|---|---|---|
| VRTL | STOCK | ETF |
| SOXL | STOCK | ETF |
| MVLL | STOCK | ETF |
| MUU | STOCK | ETF |
| MULL | STOCK | ETF |
| AMDG | STOCK | ETF |
| AMDL | STOCK | ETF |
| AMUU | STOCK | ETF |
| KORU | STOCK | ETF |
| INTW | STOCK | ETF |
| DLLL | STOCK | ETF |
| BWET | STOCK | ETF |

**적용 절차**:

```powershell
# 1. 사전 확인 — 12건 STOCK 분류 현황
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "SELECT symbol, symbol_type FROM trade.us_symbol_master WHERE symbol IN ('VRTL','SOXL','MVLL','MUU','MULL','AMDG','AMDL','AMUU','KORU','INTW','DLLL','BWET') ORDER BY symbol;"

# 2. UPDATE 실행
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" trade `
  -e "UPDATE us_symbol_master SET symbol_type = 'ETF' WHERE symbol IN ('VRTL','SOXL','MVLL','MUU','MULL','AMDG','AMDL','AMUU','KORU','INTW','DLLL','BWET') AND symbol_type = 'STOCK';"

# 3. 적용 후 확인 — 12건 모두 ETF로 변경됨 확인
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "SELECT symbol, symbol_type FROM trade.us_symbol_master WHERE symbol IN ('VRTL','SOXL','MVLL','MUU','MULL','AMDG','AMDL','AMUU','KORU','INTW','DLLL','BWET') ORDER BY symbol;"

# 4. (선택) Minervini 스크리너 재실행 — 12건이 스크리너 결과에서 제외되는지 확인
#    Phase 2 Architect 세션에서 ADR-013 확장 정책 확정 후 지시에 따라 실행
```

**완료 기준**:
- 12건 `symbol_type` 모두 `ETF`로 변경됨 (SELECT 결과 확인)
- (선택) `us_minervini_update.py` 재실행 후 12건이 Minervini 스크리너 대상에서 제외됨

**롤백 방법**:

```powershell
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" trade `
  -e "UPDATE us_symbol_master SET symbol_type = 'STOCK' WHERE symbol IN ('VRTL','SOXL','MVLL','MUU','MULL','AMDG','AMDL','AMUU','KORU','INTW','DLLL','BWET') AND symbol_type = 'ETF';"
```

**메모**:
- 발견 경위: 1.3.10 정성 평가 중 daily_analysis_us에서 `etf_methodology_mismatch` warn 12건 확인. LLM Pre-Check가 conf=1.00으로 정확히 포착 — ADR-013 안전망 작동 중.
- 근본 원인: us_sync_symbol_master.py가 외부 소스(FDR/yfinance)에서 가져온 데이터에서 ETF가 STOCK으로 잘못 분류됨. **ADR-015 §2에 따라 us_sync_symbol_master.py 보강(다중 소스 cross-check + 휴리스틱 + override 테이블 신설)이 Phase 2B sprint로 등록됨** — 재발 방지 예정.
- B.5.5 발견 6건(EMF, RMT, CEE, KF, CAF — closed-end fund 계열)은 본 Q-004 처리 후 별도 점검 큐로 처리 (ADR-015 §3 후속 정밀화에 포함).
- 본 큐 항목은 §10.4 1번 예외에 따라 1.3 단계 한정으로 Builder가 직접 등록.

---

(추가 항목은 위쪽으로 — 최신순)

---

## 완료된 작업

### Q-003: Phase 1 LLM 분석 모듈 운영 환경 적용 — Task Scheduler 등록 + 첫 자동 실행 검증 ✅ (등록: 2026-05-07, 완료: 2026-05-08)

**관련 ADR**: ADR-009 (스키마), ADR-011 (CLI 백엔드), ADR-012 (자동 트리거 + 모니터링 4종)
**관련 commit**: `phase1/1.3-daily-analysis` 브랜치, anthropic_client.py Windows 호환 fix 포함
**적용 일시**: 2026-05-08 KST

**수행 내역**:
1. `apps/llm-analysis/.env` 생성 — 루트 `.env`의 `DATABASE_URL` 복사 (gitignored)
2. `apps/llm-analysis/venv` 생성 + 의존성 설치 (pydantic, PyYAML, anthropic, SQLAlchemy, PyMySQL, python-dotenv)
3. dry-run 성공 (`--dry-run`, exit=0)
4. 첫 실제 실행 성공 (`--region US --date 2026-05-05 --limit 1`)
   - AMDG → ignore (conf=1.0), `daily_analysis_us` 행 생성, `llm_calls` id=7 기록, `sync_log` success
5. `install_task.ps1` 실행 → LLMAnalysis_US(16:00 KST) + LLMAnalysis_KR(21:00 KST) 등록, State=Ready
6. Windows 호환 버그 fix: `anthropic_client.py` `ClaudeCodeCLIBackend` — Windows에서 `claude`가 `.cmd` 파일이라 `subprocess.run(['claude', ...])` 실패 + 프롬프트가 길어 cmd 명령줄 한계 초과. `cmd /c claude ... -p` + `input=prompt` (stdin) 방식으로 수정.

**검증 결과**:
- ✅ `daily_analysis_us` 행 1개 생성 (AMDG, 2026-05-05, ignore, conf=1.0)
- ✅ `llm_calls` id=7 기록 (analysis_5_us, 22864 prompt tokens, 323 completion, error=NULL)
- ✅ `sync_log` `llm_analysis_us` status='success'
- ✅ `Get-ScheduledTask LLMAnalysis_*` — US/KR 두 작업 State=Ready
- ✅ `NextRunTime`: LLMAnalysis_US=2026-05-08 16:00, LLMAnalysis_KR=2026-05-08 21:00
- ⏳ 첫 자동 실행 (`LastRunResult=0`) — 2026-05-08 16:00 KST 이후 확인 예정

**작업 환경**:
- PROD (Windows + PowerShell, `C:\Users\sengo\project\github\DataBatcher`)

**메모**:
- `requirements.txt` 인코딩 문제(cp949 + UTF-8 한글 주석)로 `pip install -r` 실패 → 패키지 직접 지정 설치.
- Windows에서 `anthropic_client.py` 코드 fix 발생 (예상 못 했던 작업). commit에 포함.
- ADR-011 §4 + ADR-012 §3.3 약관 위반 징후 발생 시 즉시 사용자에 보고 + ADR-012 §4 절차로 API 백엔드 전환 검토.

---

### Q-002: Phase 1 DB 마이그레이션 적용 — daily_analysis_kr, daily_analysis_us, llm_calls ✅ (등록: 2026-04-28, 완료: 2026-05-07)

**관련 commit**: `phase1/1.3-daily-analysis` 브랜치 HEAD `57b6d48` 기준 적용  
**관련 ADR**: ADR-009 (LLM 분석 테이블 설계), ADR-010 (마이그레이션 3종 산출물)  
**Alembic revision**: `20260428_000001` (down_revision: `20260424_000001`)  
**raw SQL 파일**: `db/migrations/sql/20260428_000001_add_daily_analysis_and_llm_calls.sql`  
**적용 일시**: 2026-05-07 KST  
**적용 방식**: raw SQL 직접 실행 (`Get-Content ... | docker exec -i mysql-standalone-mysql mysql ...`)  
**Alembic**: 이번에도 생략 (미해결 이슈 §G — PROD `alembic_version` 동기화 미해결). raw SQL만 적용.

**검증 결과**:
- ✅ `daily_analysis_kr` DESCRIBE: symbol/date(PK), market, classification, confidence, reasoning, pattern, risk_flags(JSON), entry_params(JSON), screen_config_hash, llm_call_id, created_at — phase1_brief §4.1 스키마 일치
- ✅ `daily_analysis_us` DESCRIBE: 동일 구조 — phase1_brief §4.2 스키마 일치
- ✅ `llm_calls` DESCRIBE: id(PK AUTO_INCREMENT), timestamp, module, model, prompt_tokens, completion_tokens, cost_usd, request_payload(JSON), response_payload(JSON), duration_ms, error — phase1_brief §4.3 스키마 일치

**작업 환경**:
- PROD (Windows + PowerShell, `C:\Users\sengo\project\github\DataBatcher`)
- DB: `mysql-standalone-mysql` Docker 컨테이너 (MySQL 8.4.8)

**메모**:
- Q-003 선행 조건 충족 완료.

---

### Q-001: P0.5 마이그레이션 적용 ✅ (등록: 2026-04-24, 완료: 2026-04-26)

**관련 commit**: `phase0_5/screener-refactor` 머지 commit (`410b5ac feat(screener): add conditions_met JSON per ADR-009 (P0.5)`)  
**관련 ADR**: ADR-009 (스크리너 개편 + `conditions_met` 컬럼 추가)  
**적용 일시**: 2026-04-26 18:18 KST (일요일)  
**적용 시점 HEAD**: `af28f9f docs(meta): add ADR-011 (Phase 1 CLI backend with conditional exception)`  
**적용 방식**: `docker exec -i mysql-standalone-mysql mysql -u root ...` (호스트 mysql 클라이언트 부재로 컨테이너 내부 실행)  
**자격증명**: `.env`의 `MYSQL_ROOT_PASSWORD` 사용  
**백업**: 생략 (사용자 지시, ADD COLUMN ... NULL의 멱등성 신뢰)  
**적용 소요**: 1.5초 (MySQL 8.4.8 INSTANT ADD COLUMN)

**검증 결과**:
- ✅ DESCRIBE 검증: KR/US 두 테이블 모두 `conditions_met JSON` 컬럼 확인
  - 위치: `AFTER is_blue_dot`
  - 타입: json, NULL 허용
  - COMMENT: `"ADR-009: per-condition pass/fail map"`
- ✅ ALTER 중 cron 충돌: 없음 (일요일이라 영향 cron 없음)
- ⏳ 추가 검증 (예정): 다음 KR/US daily cron 실행 후 `conditions_met` JSON에 8개 키가 채워지는지 확인 (별도 시점 검증 — Phase 1 1.1 단계 시작 직전)

**작업 환경**:
- PROD (Windows + PowerShell)
- DB: `mysql-standalone-mysql` Docker 컨테이너 (MySQL 8.4.8)

**메모**:
- Alembic은 이번에 다루지 않음. ADR-010 §5에 따라 운영 환경에 `alembic_version` 테이블 미생성. DEV·PROD `alembic_version` 동기화는 추후 별도 큐 항목으로 다룸.

---

*이 문서는 ADR-010이 정의하는 큐 운영 절차의 SSoT다.*