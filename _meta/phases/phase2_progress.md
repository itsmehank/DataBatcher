# Phase 2 진행 기록

> Phase 2 sprint별 작업 기록. `phase2_brief.md`이 SSoT, 본 문서는 진행 상황.
> 양식 계승: `phase1_progress.md`

---

## Sprint 1: 엑셀 템플릿 + 생성 함수 (`phase2/sprint1-excel` 브랜치)

**시작**: 2026-05-11
**완료**: <Sprint 1 머지일>

### 1.A 구조 + 의존성 + 골격 (commit `d3abc1a`)

- `apps/llm-analysis/exporters/` 패키지 신설 + `__init__.py`
- `excel_exporter.py` 골격 — `ExcelExporter` 클래스 stub + `DailyAnalysisRow` dataclass (DAO 출력 모델)
- Sheet 1 컬럼 구성 — `ENTRY_CORE_COLS` 8 + `ENTRY_CONTEXTUAL_COLS` 8 + `ENTRY_EXTRA_COLS` 4
- `openpyxl>=3.1.0,<4.0` 의존성 추가 (`apps/llm-analysis/requirements.txt`)

### SSoT 점검 발견 사항 (Step 1.A 진입 시)

**EntryParams 16→17 필드 카운트 오류**:
- 코드 SSoT: `apps/llm-analysis/models/entry_params.py` 실제 17필드
- 거버넌스 문서 카운트: 16필드로 표기 (5 위치 — L5 backlog 별도, phase1_audit 봉인 위치 1건 정정 불가)
  - L1 `apps/llm-analysis/models/entry_params.py` docstring "16개 필드" (line 5 module + line 107 class)
  - L2 `_meta/05_GLOSSARY.md` Part B.2 "필드 정의 (16필드)"
  - L3 `_meta/05_GLOSSARY.md` Part B.2 "v1.1 (16필드)"
  - L4 `_meta/06_CURRENT_STATE.md` "Phase 1에서 완료된 것" 16필드 (Architect 2026-05-11 사후 발견)
  - L6 `_meta/phases/phase2_brief.md` Sprint 1 명세 line 100·111 "entry_params 16필드" (Builder 2026-05-11 commit 1 진행 중 추가 발견 — 사용자 결정에 따라 commit 1 일괄 포함)
  - L5 (backlog) `_meta/phases/phase1_brief.md` §6.3·§11.4-bis.2 — phase1_brief 봉인 보존 우선, 차후 갱신 동반 처리
  - (정정 불가) `_meta/phases/phase1_audit.md` line 74 — Auditor 산출물 시간적 봉인 (§6.3 + addendum 동일 정신). 사실 자체만 본 위치에 기록
- 발견 경위: Phase 2 Sprint 1 1.A 진입 시 Builder SSoT 점검 (phase2_brief §11.2 정신 직접 적용)
- 컬럼 스킴 영향 없음 — Sprint 1 ENTRY 컬럼 스킴이 17필드 모두 cover (CORE 7 + CONTEXTUAL 8 + warnings 2 = 17)
- 카테고리: ADR-014 §1 (a) Implementation Detail 정밀화 (코드 실제 17, 문서 카운트만 오류 — 결정 본질 불변)
- 처리: Sprint F #7-a로 정정 완료 (2026-05-11, 4 위치 일괄) — phase2_brief Sprint F #7 본문 참조

**DB 세션 import path 정정** (Step 1.A 진입 시):
- Architect 원 명령: `from db.session import get_session`
- 코드 SSoT 채택: `from core.db import make_session_factory`
- Step 1.B.1 DAO + 1.C.1 CLI에서 정정된 path 사용

### 1.B 본체 구현 (commit `2ac48b2`, `976eab6`, `be7a907`, `d87c18f`)

**1.B.1 DAO** (`2ac48b2`):
- `exporters/daily_analysis_dao.py` — `fetch_daily_analysis(session, target_date, region)`
- `_parse_json()` MySQL JSON 컬럼 dict 파싱 안전망 (PyMySQL 자동 파싱 + bytes/str 대응)
- region='both' → kr + us 통합 반환 (kr 우선)
- 정렬: `CASE classification WHEN 'entry' THEN 0 WHEN 'watch' THEN 1 WHEN 'ignore' THEN 2` + symbol
- 세션 lifecycle caller 책임 (`run_daily_analysis.py` 양식 계승)

**1.B.2-a Sheet 1 'Entry 후보'** (`976eab6`):
- `__init__` region 인자 추가 — 파일명 `daily_analysis_{date}_{region}.xlsx`
- `export()`: Workbook 생성 + 3 sheet (Sheet 2/3 intermediate placeholder)
- Sheet 1: header(CORE 8+EXTRA 4+CONTEXTUAL 8=20) + frozen B2 + hidden M~T + entry_params None 회색 fill(F2F2F2) + warnings multi-line + wrap_text
- 헬퍼: `_style_header`, `_apply_col_widths`, `_format_warnings_list`, `_format_risk_flags_multiline`, `_format_risk_flags_summary`, `_truncate_reasoning`

**1.B.2-b Sheet 2/3** (`be7a907`):
- Sheet 2: 7컬럼 + classification='watch' 필터 + classification_change_signal 빈 cell (후속 정밀화) + wrap_text
- Sheet 3: 8컬럼 + 전체 rows + risk_flags 요약("N건: top1, top2") + reasoning 200자 컷("...")

**1.B.3 단위 테스트 14건** (`d87c18f`):
- `tests/test_excel_exporter.py` — 9 검증 케이스를 함수 단위 14건으로 세분화 + `@pytest.mark.parametrize`
- NVST sample(05_GLOSSARY Part B.2) 17필드 정합 검증
- 회귀 0건 — 전체 pytest **146 passed** (132 베이스라인 + 14 신규)

### 1.C CLI + 시각 검증 + 본 문서 (commit `8d66cd7`, `<1.C.3 commit>`)

**1.C.1 CLI** (`8d66cd7`):
- `apps/llm-analysis/run_excel_export.py` 신규 — `--date`, `--region`, `--out-dir`
- `sys.path` 추가 + `from core.db import make_session_factory` (Architect 결정 B)
- 세션 lifecycle try/finally, 에러 시 traceback + exit 1
- 빈 결과 stderr 안내 + 빈 sheet 엑셀 그대로 생성
- `.gitignore`에 `apps/llm-analysis/out/` 추가

**1.C.2 sample 시각 검증** (commit 없음 — sample 파일은 `out/` 봉인):
- `out/daily_analysis_2026-05-01_us.xlsx` — Sheet 3: watch 1 + ignore 9 (= 10행)
- `out/daily_analysis_2026-05-06_us.xlsx` — Sheet 3: watch 1 + ignore 121 (= 122행)
- `out/daily_analysis_2026-05-04_both.xlsx` — Sheet 3: ignore 20 (kr 10 + us 10)
- 모든 sample에서 Entry 0건 안내 행 정합 (Phase 1.3 167행 표본에 entry 없음)
- 사용자 시각 검증 항목:
  - Sheet 1 안내 행, hidden columns M~T, frozen B2, 컬럼 width
  - Sheet 2 ALTO watch 행 reasoning wrap, risk_flags multi-line
  - Sheet 3 region 컬럼, classification 정렬, reasoning 200자 컷

**1.C.3 phase2_progress.md** (본 commit):
- 본 문서 신규 작성

### 1.D 시각 검증 발견 사항 수정 (commit `54c2627`)

Architect 세션(2026-05-11)에서 openpyxl 정밀 점검 시각 검증 시 발견:
- Sheet 1 안내 행 케이스에서 hidden M~T + freeze B2 미적용 (entry 0건 sample 3건 모두)
- Builder smoke test는 mock entry 있는 케이스에서 정상 동작 → 단위 테스트 커버리지 부족 신호 (안내 행 분기 시각 속성 미커버)

원인:
- `_build_sheet_entry()` 안내 행 분기에서 `ws.freeze_panes = "A2"; return` early return으로 hidden/freeze 적용 코드 skip
- entry 행 분기에서만 hidden + `freeze = "B2"` 적용

수정 (`_build_sheet_entry()`):
- early return 제거, 두 분기 모두 메서드 끝까지 흐르도록 if/else 구조 변경
- hidden(M~T) + `freeze = "B2"`를 두 분기 공통 후처리로 이동
- 안내 행 cell 20개 전체 회색 fill(#F2F2F2) 적용 — 데이터 행 부재 시각 단서 (Builder 결정, 명세 모호 부분)

단위 테스트 3건 추가 (`tests/test_excel_exporter.py`):
- `test_sheet1_empty_entry_has_hidden_contextual_columns` — 안내 행 케이스에서 M~T hidden + A~L visible
- `test_sheet1_empty_entry_has_freeze_B2` — 빈 rows 케이스 freeze_panes == "B2"
- `test_sheet1_empty_entry_guidance_row_has_gray_fill` — 안내 행 20 cell #F2F2F2

회귀 점검: 전체 pytest **149 passed** (146 베이스라인 + 3 신규, 회귀 0건).

sample 재생성 후 시각 속성 직접 검증 (3개 모두 정합):
- `freeze=B2, hidden=['M','N','O','P','Q','R','S','T']`
- 안내 행 cell A2: `fill=00F2F2F2`, `value='본 거래일 entry 후보 없음'`

### 완료 기준 (phase2_brief §3 Sprint 1)

- [x] 임의 거래일 엑셀 생성 성공 (sample 3건)
- [x] 사용자 시각 검증 통과 — Web Claude Architect 세션 openpyxl 정밀 점검 (2026-05-11). 발견 사항 2건 1.D commit으로 해소.
- [x] entry_params 17필드 모두 표기 (CORE 7 frozen + EXTRA 2 frozen + CONTEXTUAL 8 hidden + warnings 2 frozen)
- [x] 단위 테스트 17/17 통과 + 회귀 0건 (149 total passed)

### Sprint 1 commit 트레일

```
54c2627  phase2 sprint1.D: Sheet 1 안내 행 시각 속성 일관성 수정
32a1dba       phase2 sprint1.C.3: phase2_progress.md 신규 작성
8d66cd7       phase2 sprint1.C.1: run_excel_export.py CLI 진입점
d87c18f       phase2 sprint1.B.3: ExcelExporter 단위 테스트 14건
be7a907       phase2 sprint1.B.2-b: Sheet 2 'Watch 후보' + Sheet 3 '전체 분석' 빌더
976eab6       phase2 sprint1.B.2-a: Sheet 1 'Entry 후보' 빌더 + export() + 헬퍼
2ac48b2       phase2 sprint1.B.1: daily_analysis DAO
d3abc1a       phase2 sprint1.A: excel_exporter 골격 + openpyxl 의존성
```

### 외부 평가 / 결정

(Sprint 1 진행 중 발생 시 추가)

---

## Sprint 2: SMTP 메일 발송 (`sprint2-email-sender` 브랜치 → main ff push)

**시작**: 2026-05-12
**완료**: 2026-05-12 (main 머지 commit `181e985`)
**등급**: C급 (ADR-016 §6)

### 2.A 산출물 (commit `181e985`, +1,467 lines / 5 files)

**`apps/llm-analysis/exporters/email_sender.py`** (신규):
- `SMTPConfig` (`from_env()` — `SMTP_USER`/`SMTP_PASSWORD` 필수, host/port/sender/STARTTLS/SSL 기본값 + 필수 누락 시 어느 변수인지 명시 ValueError)
- `EmailDispatchRecord` (11 필드 dataclass: timestamp/region/date/recipient/subject/attached_filename/attached_size_bytes/status/smtp_response/error_message/retry_count)
- `build_email_body(region, date, entry, watch, attached_filename, company_names, now)` → (subject, body). 본문 양식: subject `[StockAlert] {date} {KR|US} 분석 결과 (entry N, watch M)`, entry 후보 전체 (reasoning 200자 컷), watch top-3 (confidence DESC, reasoning 150자 컷)
- `send_email(...)` SMTP 발송 + retry/exponential backoff. retryable: `SMTPServerDisconnected/Connect/Helo/Data`, `socket.timeout`, `ConnectionError`. `SMTPAuthenticationError`는 즉시 실패 (no retry). 예외 흡수 → `status`/`error_message` 필드로 표기
- `append_dispatch_log(record, log_path)` JSONL append-only (UTF-8). 디스크 실패 시 `RuntimeError`로 escalate (silent loss 금지)
- `dispatch_daily_email(...)` 고수준 통합 함수 — DB 조회 + body 빌드 + send (or dry-run) + JSONL 기록
- `fetch_company_names(session, symbols, region)` `symbol_master`/`us_symbol_master`의 `name` 컬럼 best-effort 조회 (실패 시 빈 dict)
- JSONL 경로: `DEFAULT_LOG_PATH = apps/llm-analysis/logs/email_dispatch.jsonl`

**`apps/llm-analysis/run_email_send.py`** (신규):
- CLI: `--date YYYY-MM-DD` (필수), `--region kr|us|both` (필수), `--to` (선택, env `SMTP_TO_DEFAULT` fallback), `--excel-path` (선택), `--excel-dir` (기본 `apps/llm-analysis/out`), `--dry-run`
- `region='both'` 시 kr/us 2회 dispatch
- exit code: 모두 sent/dry_run = 0, 1건이라도 failed = 1
- excel 자동 추정: `<excel-dir>/daily_analysis_<date>_<region>.xlsx`, 부재 시 명시 에러로 `--excel-path` 요구

**`apps/llm-analysis/tests/test_email_sender.py`** (신규, +701 lines, 36 케이스):
- `TestSMTPConfigFromEnv` 6건 (defaults/overrides/missing user/missing password/non-int port/SSL-STARTTLS 상호배타)
- `TestBuildEmailBody` 8건 (subject 매칭/entry 0건/watch 0건/watch top-3/truncation/company names/region 검증/entry block 필드)
- `TestSendEmail` 7건 (성공 1회/retry then success/max retries/auth error 즉시/missing attach/backoff cap/message 구조)
- `TestAppendDispatchLog` 4건 (디렉터리 자동 생성/append 모드/UTF-8/디스크 실패 RuntimeError)
- `TestDispatchDailyEmail` 4건 (dry_run/send 경로/missing excel/invalid region)
- `TestCLIArgs` 7건 (필수 인자/dry-run/`--to` fallback/누락 raise/both 2회 호출/실패 exit code)

**`.env.example`**: SMTP_* 자격증명 키 8종 추가 (DB·Anthropic 키 보존)

**`.gitignore`**: Phase 2 Sprint 2 주석 추가 (실 패턴 변경 없음 — root `.env`/`logs/` 규칙이 이미 커버)

### 2.B 사용자 검증 (2026-05-12)

DEV `.env` 작성 (Gmail 16자 앱 비밀번호) → 다음 검증 수행:
- KR dry-run 2026-05-04 (10 ignore) — `[dry_run]` exit=0, JSONL 1건 기록
- US dry-run 2026-05-07 (174 ignore + 2 watch: CGON 0.75, SHIP 0.72) — exit=0, JSONL 1건 기록
- US 실 발송 2026-05-07 — `[sent]` SMTP ok, attach 27,450 bytes, retry=0
- KR 실 발송 2026-05-04 — `[sent]` SMTP ok, attach 8,532 bytes, retry=0 (entry/watch 0건 케이스 본문 정합 확인)
- 사용자 정성 평가: US/KR 양쪽 메일 수신 + 본문 가독성 + 첨부 엑셀 정상 → **PASS**

### 2.C 단위 테스트

- 회귀 점검: 전체 pytest **185 passed** (149 베이스라인 + 36 신규, 회귀 0건)

### 2.D ADR-016 §4.1 사후 review

§2.1·§2.2·§2.5 비건드림 확인 ✓ (commit `181e985` body 명시):
- §2.1: SMTP 발송, LLM 호출 0건, 주문 실행 무관
- §2.2: 계층 3 후처리. `daily_analysis_kr/us`를 read-only DAO로 소비
- §2.5: JSONL은 운영 추적용. LLM 출력 보존 매체는 그대로 `llm_calls`/`daily_analysis_*`

### Sprint 2 commit 트레일

```
181e985  feat(phase2): Sprint 2 (C급) — SMTP 메일 발송 + 단위 테스트
```

---

## Sprint 3: 자동 발송 스케줄 (`sprint3-auto-email-schedule` 브랜치 → main ff push)

**시작**: 2026-05-12
**완료**: 2026-05-12 (main 머지 commit `e9bde20`)
**등급**: C급 (ADR-016 §6)

### 3.A 산출물 (commit `e9bde20`, +471 lines / 4 files)

**`apps/llm-analysis/ops/scheduler/windows/run_email_today.ps1`** (신규):
- PowerShell wrapper, `run_analysis_today.ps1` 양식 계승
- 인자: `-Region {KR|US|BOTH}`, `-Date YYYY-MM-DD`, `-To`, `-DryRun`
- `apps\llm-analysis\venv\Scripts\python.exe` 우선, 없으면 시스템 `python`
- 로그: `logs/scheduler/email_send_<region>_<yyyymmdd_hhmmss>.log` (Phase 1 `LLMAnalysis_*` 로그 디렉터리 공유)
- region 소문자 변환 + exit code propagate

**`apps/llm-analysis/ops/scheduler/windows/install_email_task.ps1`** (신규):
- Task Scheduler 등록 (`install_task.ps1` 양식 계승)
- 기본 시각: `EmailSend_US 17:00 KST` / `EmailSend_KR 22:00 KST` — `LLMAnalysis_*` 종료 + 안전 마진. `-UsTime`/`-KrTime` 파라미터로 시각 조정 가능
- idempotent re-install (`Get-ScheduledTask -ErrorAction SilentlyContinue` 후 `Unregister-ScheduledTask`)
- `ExecutionTimeLimit` 30분 (메일 발송 작업 특성상 분석보다 짧음)
- 통제권 메커니즘 명시 (`Disable-ScheduledTask`/`Enable-ScheduledTask`/`Unregister-ScheduledTask`)

**`apps/llm-analysis/exporters/email_sender.py`** (수정, +55 lines): graceful fallback
- `read_last_dispatch_for_region(region, log_path)` — JSONL 마지막 region 매칭 record 반환. 부재/빈 파일/파싱 실패 모두 `None` 안전 처리
- `build_prior_failure_warning(prior)` — `status='failed'`인 경우만 `"⚠️ 직전 발송 실패: {error} ({timestamp})"` 1줄 반환. `sent`/`dry_run`/`None`은 `None` 반환
- `dispatch_daily_email()`이 body 빌드 직후·send 직전에 prepend (sent/dry-run 양쪽 경로 동일 적용)

**`apps/llm-analysis/tests/test_email_sender.py`** (수정, +248 lines, 12 케이스):
- `TestReadLastDispatchForRegion` 4건 (missing log/latest for region/other region/unparseable lines skipped)
- `TestBuildPriorFailureWarning` 5건 (None/sent/dry_run/failed emits/failed without error_message)
- `TestDispatchFallbackIntegration` 3건 (prior failed warning prepended/prior sent no warning/other region failure 무영향)

### 3.B 단위 테스트

- 회귀 점검: 전체 pytest **197 passed** (185 베이스라인 + 12 신규, 회귀 0건)

### 3.C ADR-016 §4.1 사후 review

§2.1·§2.2·§2.5 비건드림 확인 ✓ (commit `e9bde20` body 명시):
- §2.1: Task Scheduler 발송 자동화, LLM 호출 0건
- §2.2: 계층 3 운영 자동화. 계층 1·2 코드 미수정
- §2.5: ADR-012 자동 트리거 패턴 계승. `llm_calls`/`daily_analysis_*` 보존 매체 변경 없음. JSONL은 별도 운영 추적 (§4 사용자 통제권 부수)

### Sprint 3 commit 트레일

```
e9bde20  feat(phase2): Sprint 3 (C급) — 자동 발송 스케줄 + graceful fallback
```

---

## Phase 5: PROD Task Scheduler 등록 + wrapper fix (commit `7c02db1`)

**시작·완료**: 2026-05-12 (사용자 PROD Windows 환경에서 진행, DEV 동기화 완료)
**등급**: C급 (ADR-016 §2)

### 5.A PROD Task Scheduler 등록

- `install_email_task.ps1` 실행 → `EmailSend_KR 22:35` / `EmailSend_US 18:45` 등록 (기본 22:00/17:00에서 `-KrTime`/`-UsTime` 조정)
- PROD 검증: KR/US dry-run 양쪽 exit=0, EmailSend KR dry-run(2026-05-11) 전체 exit=0
- `EmailSend_KR`은 `LLMAnalysis_KR 21:00` 종료 + 1h35m 마진, `EmailSend_US`는 `LLMAnalysis_US 16:00` 종료 + 2h45m 마진. ADR-016 §6 발송 자동화 영역 정합

### 5.B PROD 환경 특이 결함 5건 수정 (commit `7c02db1`, +74/-7 lines / 3 files)

PROD Task Scheduler 점검 중 발견된 5건 일괄 수정.

**`run_analysis_today.ps1` (3건)**:

1. **US `--date today_KST` 강제 버그** — wrapper가 KST 오늘 날짜를 강제 전달 → ET 기준 데이터 미존재로 매일 `screened=0`. 수정: `-Date` 미명시 시 `--date` 인자 자체 미전달, `_resolve_date`가 region별 최신 screen 자동 선택
2. **cp949 UnicodeEncodeError** — KR 한도 도달 시 em dash(`—`) 출력이 Windows cp949에서 인코딩 실패 → wrapper `exit=1`. 수정: `$env:PYTHONIOENCODING = "utf-8"` wrapper 시작점 설정
3. **DATABASE_URL 미정** — Task Scheduler 셸이 사용자 환경 미상속. 수정: `apps\llm-analysis\.env` 파일 wrapper에서 명시적 파싱 → `Set-Item env:` (key=value 라인, 주석/공백 skip, 양 따옴표 strip)

**`run_email_today.ps1` (1건 + 환경/인코딩 동일 패치)**:

4. **Excel 사전 생성 누락** — 기존 wrapper는 `run_email_send.py`만 호출. 자동 트리거 환경에서 `out/daily_analysis_<date>_<region>.xlsx` 부재 시 exit 1. 수정: Step 1 `run_excel_export.py` 호출 → Step 2 `run_email_send.py` 호출. Step 1 실패 시 `[WARN]` 후에도 Step 2 진행 (`run_email_send.py` 자체 에러 처리에 위임)

**`config/settings.yaml` (1건)**:

5. **`daily_call_limits.us` 500 → 100** — KR 실측 평균 ~76s/건 기준 100건 ≈ 127분으로 `LLMAnalysis_US` Task `ExecutionTimeLimit(2h)` 내 완주. 500건 ~10.5h로 한도 초과 확실. 2026-05-12 인라인 주석 보존

### 5.C DEV-PROD 환경 사각지대 메타 인계

본 5건 모두 DEV(Mac) 단위 테스트로 사전 차단 불가능한 카테고리:

| # | 사각지대 |
|---|---|
| 1 | US 시장 시간대 차이로 인한 가용 거래일 mismatch (KST vs ET) |
| 2 | Windows cp949 코드페이지 (Mac UTF-8과 무관) |
| 3 | Task Scheduler 환경 상속 부재 (사용자 셸과 분리) |
| 4 | PROD 자동 트리거에서의 산출물 부재 (DEV 수동 실행은 단계 분리됨) |
| 5 | 사용자별 처리 시간 실측 (LLM 호출 시간 환경 차이) |

향후 Sprint 진행 시 PROD 검증 단계의 가치 인식. C급 작업이라도 DEV-PROD 환경 영향 산출물(`.ps1`, `settings.yaml` 시각/한도 등)은 PROD smoke test 1회 권고. 본 항목은 ADR-016 운영 메모로 보존, 별도 ADR화는 패턴 누적 후 검토.

### 5.D ADR-016 §4.1 사후 review

§2.1·§2.2·§2.5 비건드림 확인 ✓:
- §2.1: 메일 발송·분석 자동화는 정보 전달, 주문 실행 아님
- §2.2: wrapper 보강·설정값 조정, 계층 1·2 코드 미수정
- §2.5: 신규 LLM 호출 0건, `daily_analysis_*`·`llm_calls` 테이블 미수정

### Phase 5 commit 트레일

```
7c02db1  fix(phase2): LLMAnalysis/EmailSend wrapper 결함 5건 보강
```

---

## Phase 6: 모니터링 점검 스크립트 (commit `9bf9abc`)

**시작·완료**: 2026-05-12
**등급**: C급 (ADR-016 §6)

### 6.A 산출물 (commit `9bf9abc`, +650 lines / 2 files)

**`apps/llm-analysis/scripts/check_dispatch_health.py`** (신규):
- JSONL(`apps/llm-analysis/logs/email_dispatch.jsonl`) 최근 N일 status 점검
- `daily_analysis_kr/us` 테이블을 ground truth로 사용 — 분석 행이 없는 날은 발송 대상 아님 → 시장 calendar 의존성 회피 + 정확한 누락 감지
- 같은 거래일 retry 시 최신 timestamp record로 status 판정 (실패 후 재발송 성공은 healthy 처리)
- DB 미연결 시 누락 점검만 skip하고 JSONL 기반 status 보고는 유지
- CLI: `--days N` (기본 7), `--region kr|us|both` (기본 both), `--log-path PATH`, `--today YYYY-MM-DD` (테스트용)
- exit code: healthy 0 / 실패·누락·log 부재 시 1

**출력 예시**:
```
[KR] 최근 7일 (2026-05-06 ~ 2026-05-12)
  성공/dry_run 5건, 실패 0건, 누락 0건

[US] 최근 7일 (2026-05-06 ~ 2026-05-12)
  성공/dry_run 5건, 실패 0건, 누락 0건
```

실패·누락 발견 시:
```
  실패 내역:
    - 2026-05-07 (retry=2): SMTPAuthenticationError: ...
  누락 거래일 (분석 행 존재, 발송 기록 부재):
    - 2026-05-08
```

**`apps/llm-analysis/tests/test_check_dispatch_health.py`** (신규, 22건):
- `TestReadRecentRecords` 4건 (missing/empty/region·window filter/unparseable lines skipped)
- `TestLatestStatusPerDate` 2건 (timestamp 갱신/distinct 보존)
- `TestBuildRegionReport` 5건 (healthy/missing day/failed/DB unreachable/retry resent)
- `TestFormatReport` 6건 (healthy/missing file/empty file/failure listed/missing listed/DB skip)
- `TestMain` 5건 (healthy 0/failure 1/missing log 1/both regions/days 검증)

### 6.B 단위 테스트

- 회귀 점검: 전체 pytest **219 passed** (197 베이스라인 + 22 신규, 회귀 0건)

### 6.C 사용 권고

- 7거래일 모니터링 기간 동안 매일 1회 또는 주간 1회 실행
- 기본 `--days 7 --region both`로 충분
- exit code 1 발생 시 출력의 실패 내역·누락 거래일 확인 후 즉시 사용자 대응

### 6.D ADR-016 §4.1 사후 review

§2.1·§2.2·§2.5 비건드림 확인 ✓:
- §2.1: read-only 보고 도구, 주문 실행 무관
- §2.2: 계층 3 운영 도구, 계층 1·2 미터치
- §2.5: 신규 LLM 호출 0건. `daily_analysis_*`·`llm_calls` 테이블은 SELECT만, 변경 없음. JSONL은 발송 기록 운영 추적 (§4 사용자 통제권 부수)

### Phase 6 commit 트레일

```
9bf9abc  feat(phase2): Phase 6 (C급) — dispatch health 모니터링 스크립트
```

---

## Phase 7: Phase 2A 본질 코드 작업 완료 보고

**작성 시점**: 2026-05-12 (Builder 자체 보고, ADR-016 §3 조건부 Auditor 면제)

### 7.A 산출물 요약 (Sprint 1·2·3 + Phase 5·6)

| 항목 | commit | 등급 | 비고 |
|---|---|---|---|
| Sprint 1 엑셀 | merge `6733778` | C급 (소급) | openpyxl, 3 sheet, 17필드 |
| Sprint 2 SMTP | `181e985` | C급 | 단위 테스트 36건 (149 → 185) |
| Sprint 3 자동 발송 | `e9bde20` | C급 | PowerShell + graceful fallback (185 → 197) |
| Phase 5 PROD 등록 + wrapper fix | `7c02db1` | C급 | DEV-PROD 환경 사각지대 5건 |
| Phase 6 모니터링 스크립트 | `9bf9abc` | C급 | check_dispatch_health.py (197 → 219) |

누계 단위 테스트: 132 (Phase 1 종료) → 149 (Sprint 1) → 185 (Sprint 2) → 197 (Sprint 3) → 219 (Phase 6). 회귀 0건 누적.

### 7.B 7거래일 모니터링 시작 안내

- **시작일**: 첫 PROD 자동 발송 거래일 (KR `EmailSend_KR 22:35` 또는 US `EmailSend_US 18:45` 중 먼저)
- **종료일**: 누적 7거래일 (KR·US 합산 또는 region별 분리는 사용자 결정)
- **점검 방법**: 매일 또는 주간 1회 `./apps/llm-analysis/venv/bin/python apps/llm-analysis/scripts/check_dispatch_health.py --days 7 --region both`
- **PASS 기준**: 모든 region에서 실패 0건 + 누락 0건 (exit code 0)
- **FAIL 시 대응**: 출력의 `error_message` 또는 누락 거래일 확인 후 사용자 시점 (`run_email_send.py --to ...` 수동 재발송 또는 PROD wrapper 점검)

### 7.C 7거래일 중 병행 작업 정책 (A안 채택)

Architect 세션 2026-05-12 결정: **A안 (보수, 거버넌스 정합)** 채택.

- 7거래일 모니터링 기간 중 다른 코드 작업 정지
- maintenance backlog (Sprint A·B·C·D·E·F) 및 Phase 3 본격 진입 모두 7거래일 PASS 후
- Sprint A (entry-side 자연 누적)는 `LLMAnalysis_*` 자동 가동 중이라 자연 누적 — 별도 코드 작업 아님, A안과 충돌 없음
- **예외**: 7거래일 중 PROD 결함 추가 발견 시 즉시 우선순위 변경 (병행 정책 일시 정지, wrapper fix 처리)

### 7.D Phase 2A 종료 게이트 점검 (phase2_brief §9.1 차단 조건)

ADR-016 채택 후 4개 조건:

1. [⏳] Sprint 1·2·3 production 가동 + 7거래일 자동 발송 검증 — **진행 중** (PROD 가동 완료, 7거래일 누적 대기)
2. [✅] 헌법 §2.1·§2.2·§2.5 위배 없음 (C급 ADR-016 §3 조건부 면제) — Sprint 1·2·3·Phase 5·6 모두 §4.1 사후 review 통과
3. [⏳] `phase2_progress.md` Phase 2A 종료 보고 작성 — **7거래일 누적 후 Architect 세션에서 작성**
4. [✅] 단위 테스트 회귀 0건 (132 → 219 누적, 회귀 0건)

### 7.E 7거래일 PASS 후 사용자 행동 가이드

1. `check_dispatch_health.py --days 7 --region both` 실행 결과 PASS 확인 (exit 0)
2. Web Claude Architect 세션 의뢰 — Phase 2A 종료 보고 (B급)
   - Architect 의뢰 시 산출물: 7거래일 모니터링 PASS 증빙(스크립트 출력) + 본 `phase2_progress.md`
3. 본 종료 보고 작성 시:
   - `06_CURRENT_STATE.md` Phase 2A 완료 반영
   - `phase2_brief.md` §9.1 차단 조건 4건 모두 ✅ 처리
   - Phase 3 진입 brief 또는 ADR 작업 (헌법 §2.1·§2.2 영역 진입 여부에 따라 A급 가능성 — 별도 평가)

### 7.F maintenance backlog 상태 (ADR-016 §9.1-bis)

| Sprint | 등급 | 만료일·후행 처리 | 현재 상태 |
|---|---|---|---|
| Sprint A (entry 자연 누적) | B급 | 2026-06-08 강제 결정 | LLMAnalysis_* 자동 가동 중, 자연 누적 진행 |
| Sprint B (Evaluator 6종) | B급 | Phase 3 시작 후 1개월 | 미진행 |
| Sprint C (ADR-015 fund vehicle) | B급 | Phase 3 종료 시까지 | 미진행 |
| Sprint D (분류 안정성) | B급 | Phase 3 종료 시 | 미진행 |
| Sprint E (prompt v3) | B급 | A·B·D 결과 후 결정 | 조건부 |
| Sprint F (운영 부수) | C급 | Phase 3 진입 전 | 일부 진행 (Sprint F #7 완료, 나머지는 사용자 시점) |

7거래일 모니터링 종료 + Phase 2A 종료 보고 후 maintenance backlog 본격 처리 또는 Phase 3 진입 결정.

### 7.G ADR-016 §4.1 사후 review (Phase 6·7 통합)

§2.1·§2.2·§2.5 비건드림 확인 ✓:
- §2.1: 모니터링 스크립트 read-only, 보고 작성 read-only. 주문 실행 무관
- §2.2: 계층 3 외부 운영 도구·문서. 계층 1·2 미터치
- §2.5: 신규 LLM 호출 0건. `daily_analysis_*`·`llm_calls` 미수정. JSONL은 발송 기록 운영 추적 (§4 사용자 통제권 부수)

---

(이후 Sprint A·B·C·D·E·F maintenance backlog는 ADR-016 §9.1-bis 만료일·후행 처리에 따라 별도 진행 시 본 문서에 누적)
