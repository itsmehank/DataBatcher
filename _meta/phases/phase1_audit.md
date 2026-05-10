# Phase 1 감사 보고서 — 헌법 5종 점검

> 작성: Auditor (Web Claude, Opus 4.7 세션)
> 작성일: 2026-05-10
> 권한: ADR-005 §3 정의 Auditor — `_meta/` 거버넌스 문서 직접 변경 금지, 코드 직접 변경 금지, 점검 결과 보고만
> 산출물: 본 문서 (`_meta/phases/phase1_audit.md`)

---

## §1. 감사 범위

### 1.1 점검 대상

| 항목 | 상태 |
|---|---|
| 작업 브랜치 | `phase1/1.3-daily-analysis` (코드 미머지) |
| `_meta/` 사전 머지 | main commit `eb09b80` (Web Claude 동기화 정합성 확보) |
| `_meta/` 추가 거버넌스 갱신 | `phase2/governance-update` 브랜치 (작업 1·2·3·4·5·6 누적, **본 Auditor 미가시**) |
| Phase 1 종료 시점 | 2026-05-08 (1.3.11 게이트 14/14 통과, Builder 자체 보고) |

### 1.2 점검 항목 (phase1_brief.md §9.3)

다섯 항목 모두 PASS / FINDING / FAIL 판정 부여:

1. 헌법 §2.1 — LLM 직접 주문 실행 금지
2. 헌법 §2.2 — 결정론 코어와 LLM의 물리적 분리
3. 헌법 §2.5 — LLM 출력 영구 보존
4. 헌법 §3.1 — 4계층 단방향 흐름
5. 헌법 §4 — 사용자 통제권·이해

### 1.3 검토한 문서·증거

- `_meta/00_CONSTITUTION.md` (헌법 본문)
- `_meta/04_DECISIONS.md` ADR-001 ~ ADR-013 (ADR-014·015은 phase2/governance-update 브랜치, 본 Auditor 미가시)
- `_meta/06_CURRENT_STATE.md` (eb09b80 시점, Phase 1.2 종료 상태로 표기 — Phase 2 브랜치에서 갱신 예정)
- `_meta/phases/phase1_brief.md` §3·§4·§5·§7·§8·§9·§10
- `_meta/phases/phase1_progress.md` (1.1 ~ 1.3.11 종료 보고 + 정성 평가)
- `_meta/phases/phase1_classification_logic_review.md` (Builder 자체 분류 로직 조사)
- `_meta/operational_queue.md` Q-001 ~ Q-004
- `apps/llm-analysis/` 구조 (phase1_progress 기록 기반 — 본 Auditor가 직접 코드 검수 불가, Builder 자체 점검 + Architect 인계 기록 + Evaluator 외부 평가에 근거)
- 운영 데이터: 167행 분석 결과 + 158회 LLM 호출 (1.3.9-A 백필 70+71행 + 1.3.9-B 자연 운영 26행)

### 1.4 Auditor 가시 범위의 한계 (사전 명시)

본 Auditor는 다음 두 가지를 **직접 검증하지 못합니다**:

(a) `apps/llm-analysis/` 코드 본문 — `project_snapshot.md`는 2026-04-23 시점이므로 Phase 1 시작 전 상태. 본 보고는 Builder의 자체 점검 기록(phase1_progress.md), Architect 인계 기록, Evaluator 외부 평가, 운영 결과(167행 + 158호출)의 정합성으로부터 헌법 부합 여부를 추론합니다.

(b) `phase2/governance-update` 브랜치의 ADR-014·015 본문 — 따라서 "ADR-014 §1 카테고리 부합" 여부는 직접 확인 불가. 해당 항목은 본 보고에서 FINDING으로 처리하고, Architect 세션에서 ADR-014 확정 후 사후 검증을 권고합니다.

이 한계는 ADR-005 §3 Auditor 권한 범위 내의 자연스러운 제약이며, 본 보고의 PASS/FINDING/FAIL 판정은 가시 증거에 한정해 부여됩니다.

---

## §2. 점검 결과 — 항목별 판정

### 2.1 헌법 §2.1 — LLM 직접 주문 실행 금지 → **PASS**

#### 점검 1.a — `run_daily_analysis.py`가 결과를 DB 저장만 하고 매매·발주를 트리거하지 않는지

근거:

- `daily_analysis_kr/us` 스키마 (phase1_brief §4.1·§4.2): symbol, date, market, classification, confidence, reasoning, pattern, risk_flags(JSON), entry_params(JSON), screen_config_hash, llm_call_id, created_at — **순수 영속 테이블**. INSERT 외 외부 효과 컬럼 부재.
- `run_daily_analysis.py` 산출물 흐름 (phase1_progress 1.3.1~1.3.5): KR/US 종목 루프 → (5) `analyze_chart` → (entry 분류 시) (6) `calculate_entry_params` → DB INSERT → sync_log 기록. 외부 거래 API 호출 없음.
- ADR-012 §5 통제권 충족 방식 명시: "결과 검토 후 매매 실행 게이트 — LLM 분석 결과는 `daily_analysis_kr/us`에 저장될 뿐, 실제 매매로 이어지는 경로는 없음 (Phase 6까지). 헌법 §2.1 위배 없음."
- `order_reservations` 테이블 미존재 (Phase 6 예정).
- 1.3.9-A 백필 158회 호출 + 1.3.9-B 26행 자연 운영 — 어느 호출에서도 외부 거래 API 호출 흔적 없음 (sync_log 기준).

#### 점검 1.b — `llm_calls` raw_response에 actionable order 형식 출력 사례

근거:

- LLM 출력은 두 종류만 — `AnalysisResult` (5)와 `EntryParams` (6). 둘 다 Pydantic JSON으로 강제 (헌법 §2.5 부합 부산물).
- `EntryParams`는 분석용 산출 (pivot_price, trigger_price, stop_loss_pct_from_pivot, stop_loss_pct_from_current_price, position_size_pct, target_price 등 16필드). KIS·키움 등 증권사 API 호출 페이로드 형식 부재.
- `risk_flags` 12종 whitelist (climax_run, late_stage_base, ..., etf_methodology_mismatch) — 모두 분석 메타. 주문 instruction 형식 부재.
- v2 production lock 시점 외부 평가(Web Claude Minervini Evaluator, Opus 4.7) production-ready 판정 — taxonomy 위반 outlier 0건.

**판정: PASS**. LLM이 분석·조언·제안만 수행하며 주문 실행 경로 없음.

---

### 2.2 헌법 §2.2 — 결정론 코어와 LLM의 물리적 분리 → **PASS**

#### 점검 2.a — 계층 1 (`apps/ingest-databatcher/`) 코드에 LLM 호출 없음

근거:

- ADR-003 (LLM 백엔드)·ADR-011 (CLI 백엔드)에 따라 LLM 호출은 `apps/llm-analysis/` 단일 앱에 격리.
- `apps/ingest-databatcher/` 책임 (ARCHITECTURE.md 계층 1): 데이터 수집·인디케이터 계산·미너비니 트렌드 템플릿 필터. 모두 결정론 코드.
- ADR-013 ETF 제외 필터 적용도 결정론 코어 (`kr_minervini_update.py`, `us_minervini_update.py`)에 `symbol_type='ETF'` JOIN 조건 추가 — LLM 호출 없음.
- Phase 1 종료 보고 line 1569: "`apps/llm-analysis/` ↔ `apps/ingest-databatcher/` 코드 import 없음; DB만 공유" — Builder 자체 점검 명시.

#### 점검 2.b — 계층 2 (`apps/llm-analysis/`)가 계층 1 결과를 read-only 소비

근거:

- phase1_brief §5.3: "`llm-analysis`가 `ingest-databatcher`를 함수 호출하지 않는다 — 헌법 §2.2 준수. 대신 DB를 통해 데이터만 읽음".
- 계층 2 read 대상: `minervini_screen_results_kr/us`, `stock_prices`, `us_stock_prices`, `stock_indicators`, `us_stock_indicators`, weekly versions, `symbol_master`, `us_symbol_master` — 모두 read-only.
- 계층 2 write 대상: `daily_analysis_kr/us`, `llm_calls`, `sync_log` (자체 module 행만) — 계층 1 테이블 미수정.
- phase1_progress 1.3.2 명시: "`models/db_models.py` 갱신 — `SyncLog` ORM 추가 (read+write, 헌법 §2.2 준수: ingest-databatcher 함수 import 안 함, DB만 공유)".
- 같은 1.3.2: SQLite 호환을 위해 `LlmCall.id`는 ORM 레벨에서 `Integer`로 정의 (MySQL 본 번에서는 `BIGINT AUTO_INCREMENT`). 계층 2가 자체 ORM·테이블 정의를 가짐을 입증 — 함수 import 부재의 구조적 근거.

#### 점검 2.c — 계층 1 → 계층 2 단방향 흐름 (계층 2가 계층 1 데이터 변경 안 함)

근거:

- 계층 2 INSERT 대상은 `daily_analysis_kr/us` (Phase 1 신규)·`llm_calls` (Phase 1 신규)·`sync_log` (자체 행 추가)뿐. 계층 1의 OHLCV·인디케이터·`minervini_screen_results_*`·`symbol_master` 테이블에 대한 write·UPDATE·DELETE 사례 없음.
- ADR-013 ETF 정책 시행 후에도 과거 ETF 행은 historical record로 보존 (ADR-013 §4 (i) 채택, 일괄 삭제 안 함) — 계층 2가 계층 1 데이터를 사후 정정하지 않음.
- Q-004 (us_symbol_master ETF 정정 12건)는 계층 1 데이터 정정이 필요한 사례지만, 이는 계층 2가 자동으로 수행하지 않고 Architect 세션에서 ADR-013 확장과 함께 처리하도록 운영 큐에 인계 — §2.2 단방향 정신 준수.

**판정: PASS**. Builder가 §2.2를 의식적으로 self-check하면서 (1.3.2 SyncLog 추가 시 명시) DB-only 공유 원칙 유지. 가시 증거 모두 §2.2 부합.

---

### 2.3 헌법 §2.5 — LLM 출력 영구 보존 → **PASS**

#### 점검 3.a — 모든 (5)/(6) 호출이 `llm_calls` 기록 (Phase 1.3 167행 + ETF 12건 etf_methodology_mismatch 안전망 호출 포함)

근거:

- 1.3.9-A 백필 통계 (phase1_progress line 1421~1424): analysis_5_kr 75회, analysis_5_us 82회, entry_params_6_us 1회 — **합계 158회**, 모두 `llm_calls` INSERT.
- 1.3.9-B 자연 운영 26행 (US 2026-05-06): 모두 llm_calls 기록. ETF 12건 (VRTL, SOXL, MVLL, MUU, MULL, AMDG, AMDL, AMUU, KORU, INTW, DLLL, BWET) Pre-Check `etf_methodology_mismatch` (conf=1.00) — **포함**됨. phase1_progress line 1242: "LLM Pre-Check이 conf=1.00으로 즉시 ignore 처리 (safety net 정상 작동)".
- Q-003 첫 실행 검증 (operational_queue.md line 132): "AMDG → ignore (conf=1.0), `daily_analysis_us` 행 생성, **`llm_calls` id=7 기록**, `sync_log` success" — Pre-Check 안전망 호출도 정상 기록 입증.
- Phase 1 종료 보고 line 1570: "모든 호출 `llm_calls` 기록; request_payload/response_payload 비어있지 않음 확인".

#### 점검 3.b — 호출 실패 케이스 보존 (timeout/error 메타)

근거:

- `llm_calls` 스키마 (phase1_brief §4.3): `error TEXT NULL` 컬럼 명시.
- 1.3.9-A 백필 결과: analysis_5_kr 에러 4 (5.3%), analysis_5_us 에러 11 (13.4%), 합산 에러율 9.5% — **모두 llm_calls 기록**.
- phase1_progress line 1424: "합계 158회, 에러율 9.5% (CLI timeout retry 정상 범위)" — timeout 재시도 케이스도 별도 행으로 보존.
- Phase 1 종료 게이트 #5 (line 1563): "부분 실패 처리 작동 (실패 종목 스킵, 나머지 진행) ✅ 통과 — 에러율 9.5% 포함 158회 정상 완주 확인".
- B.5.5 검증 시점 timeout 7.75% (NVST 검증 배치, 400/400 완주) — 동일 정책 적용 입증.

#### 점검 3.c — `daily_analysis_kr/us` raw_response 압축·삭제·요약 없이 저장

근거:

- 스키마 (phase1_brief §4.1·§4.2): reasoning은 TEXT NULL, risk_flags·entry_params는 JSON NULL — 어느 컬럼도 압축·요약·hash 적용하지 않음.
- v1 → v1.1 force-recompute 시 DELETE+INSERT 방식으로 v1 결과가 overwrite되는 한계가 별도 식별됨 (06_CURRENT_STATE.md 미해결 이슈 §I, phase1_progress의 "ADR 후보" 항목). **그러나 v1 raw_response는 `llm_calls`에 별도 보존**되어 §2.5 위배 아님 — `daily_analysis_*`의 latest view는 의도된 기능이며, 모든 호출의 raw 응답은 `llm_calls.response_payload`에 영구 보존.
- 1.3.10 정성 평가 (line 1303~1313)에서 reasoning 본문이 구체 수치 그대로 인용됨 (AAOI: "Climax run: +255% in 10wks (Feb 20 $51.68 → May 1 $183.51)..." 등) — 압축·요약 없음 입증.

**판정: PASS**. 167행 + 158호출 + ETF 12건 안전망 호출 + 에러 15건 모두 `llm_calls` 기록. raw_response 손상 없음.

---

### 2.4 헌법 §3.1 — 4계층 단방향 흐름 → **PASS**

#### 점검 4.a — 1 → 2 → 3 → 4 흐름 유지 (역방향 없음)

근거:

- 계층 1 → 계층 2: DB 기반 read-only 소비 (§2.2 검증 결과 그대로 적용).
- 계층 2 → 계층 1: 코드·데이터 양면 모두 부재 (§2.2.c 검증 결과 적용).
- ARCHITECTURE.md 계층 정의 (00_CONSTITUTION.md §3.1 인용):
  - 계층 1: 결정론 코어 (데이터·필터·주문·포트폴리오) — `apps/ingest-databatcher/`
  - 계층 2: LLM 분석 (단발 호출 함수) — `apps/llm-analysis/`
  - 계층 3: 자동화 파이프라인 (엑셀·메일·UI) — Phase 2 메일, Phase 3 UI, `apps/trading-view-project/` 일부
  - 계층 4: 에이전트 (대화형·도구 사용) — Phase 4 이후

#### 점검 4.b — LLM 분석 결과 (계층 2)가 계층 1 코드를 수정하지 않음

근거:

- §2.2.c 결과 그대로 적용. 계층 2의 모든 INSERT는 자체 영역 또는 신규 테이블에 한정.
- 미해결 이슈 §J (B.5.5 ETF 6건 오통과)·Q-004 (12건 정정)는 LLM이 자동 수정하지 않고 ADR-013 확장 + Architect 세션 처리로 인계됨 — 계층 2의 자동 사후 정정 부재.

#### 점검 4.c — 계층 3 (대시보드)이 계층 2를 직접 트리거하지 않음 (Phase 1 시점)

근거:

- Phase 1 시점 트리거 경로 (ADR-012 §1·§2): Windows Task Scheduler → `run_daily_analysis.py` 또는 사용자 수동 PowerShell 호출. **계층 3 경로 미구현·미사용**.
- phase1_brief §8.1 트리거 옵션 비교: D (대시보드 "분석 실행" 버튼)는 "Phase 3 도입" — Phase 1 채택 안 함.
- `apps/trading-view-project/` (계층 3 일부)는 Phase 0에서 구축된 chart viewer로, daily_analysis 결과를 표시할 수는 있으나 `run_daily_analysis.py`를 호출하는 경로 부재.
- Task Scheduler는 OS-level 외부 트리거이며 4계층 외부에 위치 — ADR-012 §1·§5에서 "사용자 등록 시점에 1회 의도 표명, 매일 동일 의도 반복"으로 헌법 §4.1 통제권 충족 메커니즘 명시.

**판정: PASS**. 4계층 의존성이 Phase 1 시점에서 위에서 아래로만 흐름. 계층 3 구현 부분은 Phase 1 범위 밖이므로 본 점검에 영향 없음.

---

### 2.5 헌법 §4 — 사용자 통제권·이해 → **PASS (FINDING 2건 동반)**

#### 점검 5.a — Task Scheduler LLMAnalysis_KR/US가 ADR-012 범위 내 → **PASS**

근거:

- ADR-012 §2 권장 시각: US 16:00 KST, KR 21:00 KST.
- Q-003 PROD 적용 검증 (operational_queue.md line 140~141): `LLMAnalysis_US=2026-05-08 16:00`, `LLMAnalysis_KR=2026-05-08 21:00`, State=Ready — **ADR-012 §2와 정확히 일치**.
- Q-003은 사용자가 PROD 접근하여 직접 등록·실행·검증 (operational_queue.md line 144: "PROD (Windows + PowerShell, `C:\Users\sengo\project\github\DataBatcher`)") — 사용자 의도 명시적 표명.
- 헌법 §4.1 통제권 충족 메커니즘 (ADR-012 §5):
  - Task Scheduler 언제든 disable 가능 ✅
  - 킬 스위치 `settings.yaml` `modules.analyze_chart: false` ✅
  - 부분 비활성화 (`calculate_entry_params: false`) ✅
  - 매매 실행 게이트: Phase 6까지 매매 경로 없음 ✅
- ADR-012 §3 모니터링 4종 (일일 호출 상한 hard stop / sync_log 기록 / 약관 위반 징후 즉시 중단 / 호출 로그 주간 점검) — 1.3.1~1.3.5에서 완전 구현 (phase1_progress 1.3.2 cost_tracker.py·llm_call_recorder.py·1.3.6 show_cost_summary.py) → 헌법 §4.2 이해 충족 (사용자가 호출 패턴·실패율을 추적 가능).
- 헌법 §4.2 reasoning 채움: 167행 모두 reasoning 필드 작성됨. ETF 12건도 특정 reasoning ("ETF — Minervini/O'Neil methodology targets individual leadership stocks. Recommend upstream screener filter.") 보유. 사용자가 "왜?"를 물을 수 있음.

판정: **PASS**.

#### 점검 5.b — ADR 본문 수정 사례 (ADR-010·011 4건)이 ADR-014 §1 카테고리에 부합 → **FINDING**

가시 증거 (4건 모두 `_meta/04_DECISIONS.md` eb09b80 시점 본문에 반영됨):

| # | 위치 | 내용 | 시점 |
|---|---|---|---|
| 1 | ADR-010 §1 | Raw SQL 위치 결정 (`apps/ingest-databatcher/scripts/migrations/` → `db/migrations/sql/`) | 2026-04-28 결정, 2026-05-02 본문 갱신 |
| 2 | ADR-010 §6 | alembic.ini 자격증명 처리 — `.env` `DATABASE_URL` 단일 SSoT (신규 §6 추가) | 2026-05-02 본문 갱신 |
| 3 | ADR-011 §3 cost_usd 표 | "NULL 허용" → "NULL 허용 + CLI 참고값(Max 플랜 토큰 환산 추정치) 저장 가능 (1.1.4-b β안)" | 2026-04-29 결정, 2026-05-02 본문 갱신 |
| 4 | ADR-011 §3 cost_usd 의미 subsection | 신규 subsection 추가 (api_billing / cli_estimate / max_plan_billing 메타 식별) | 2026-04-29 명시, 2026-05-02 본문 갱신 |

본 Auditor의 가시 평가:

- 4건 모두 **삭제 없이 추가만** 이루어짐 → `_meta/04_DECISIONS.md` 헤더 line 4 ("한 번 기록된 결정은 삭제하지 않는다") 부합.
- 4건 모두 **원 결정의 본질 유지** + **운영 중 발견된 사실의 보강·명문화**. 결정 번복(reversal)이 아님 → 헤더 line 5 ("결정을 번복할 때는 새 ADR 작성")의 강제 적용 대상 아님.
- 4건 모두 사용자 승인 절차를 거침: `_meta/06_CURRENT_STATE.md` line 24~30 "Architect 인계 작업 8건 처리 (2026-05-02 본 세션)" — 사용자가 Architect 세션을 열어 명시적으로 갱신 처리 → 헌법 §4.1 통제권·§4.2 이해 부합.

본 Auditor의 한계:

- ADR-014는 `phase2/governance-update` 브랜치에 작성된 것으로 추정되나, **본 Auditor의 가시 범위 밖**(main eb09b80 미머지). 따라서 "ADR-014 §1 카테고리 부합 여부"를 직접 검증할 수 없음.
- Builder가 phase1_progress.md line 1612에서 자체 식별: "ADR 봉인 원칙(`04_DECISIONS.md` 헤더)과의 정합성 검토 필요. Architect 후속 세션에서 처리 예정 — '결정 변경 vs 결정 보강·현실 반영'의 ADR 갱신 정책 명문화 검토." → **시스템 자정 작용 정상 가동**.

판정: **FINDING** (헌법 §4 위배 아님 — 통제권 행사 절차 준수 + 자정 작용 가동). Architect 세션이 ADR-014 본문 확정 후 4건의 카테고리 사후 재확인 권고.

#### 점검 5.c — operational_queue.md Q-001~004가 §10.4 절차 준수 → **PASS (FINDING 1건)**

| Q | 등록 | 적용 | §10.4 절차 준수 평가 |
|---|---|---|---|
| Q-001 (P0.5 마이그레이션) | 2026-04-24 | 2026-04-26 PROD ✅ | ADR-010 §1 3종 산출물(Alembic + raw SQL + 큐) 정상 작성. 등록·실행·완료 이동 절차 부합. **PASS**. |
| Q-002 (Phase 1 마이그레이션) | 2026-04-28 텍스트 작성 / 2026-05-02 정식 등록 | 2026-05-07 PROD ✅ | Builder가 텍스트 작성, Architect 세션이 1.1 종료 시 정식 등록 (06_CURRENT_STATE line 29). §10.4 1번(Architect/Builder 분리) 정석 절차. **PASS**. |
| Q-003 (Task Scheduler 등록 + 첫 실행 검증) | 2026-05-07 (phase1_progress 1.3.8) | 2026-05-08 PROD ✅ | phase1_progress 1.3.8: "§10.4 1번 예외, 본 1.3 단계 한정 허용" 명시적 인지하에 Builder 직접 등록. Q-002 선행 조건 + 적용 절차 9단계 + 검증 4종 + 롤백 모두 명시. **PASS** (예외 인지·사유 기록 양호). |
| Q-004 (us_symbol_master ETF 정정 12건) | 2026-05-08 | 대기 중 (Phase 2 Architect 처리 인계) | operational_queue.md line 111: "본 큐 항목은 §10.4 1번 예외에 따라 1.3 단계 한정으로 Builder가 직접 등록" 명시. ADR-013 안전망 작동 중이므로 즉시 처리 불필요, Phase 2 Architect 세션 ADR-013 확장과 함께 처리 명시. **PASS** (예외 인지·사유 기록 양호 + Phase 2 인계 명시). |

본 Auditor의 가시 평가:

- Q-001·Q-002는 ADR-005·§10.4 정석 절차에 정확히 부합.
- Q-003·Q-004는 "§10.4 1번 예외" 적용. Builder가 매번 사유와 범위(1.3 단계 한정)를 기록하고 사용자가 PROD 적용을 직접 수행 → ADR-005 거버넌스 명문화 정신·헌법 §4.1 통제권 부합.
- **단, "§10.4 1번 예외" 자체는 phase1_brief.md §10.4 본문에 명문화되지 않음**. §10.4는 6개 원칙만 나열하며 "예외" 조항 부재. Builder가 운영상 도입한 작업 관행이며, 사용자가 묵시적으로 승인한 상태.

판정: **PASS** with FINDING — "§10.4 1번 예외" 자체의 본문 명문화는 Architect 후속 작업으로 권고 (Phase 2 brief 또는 ADR-014 거버넌스 갱신 정책에서 정식 다루기 권고).

#### §2.5 종합 판정

세 sub-item 모두 통제권·이해 본질은 유지됨. ADR-014/§10.4 1번 예외 명문화는 거버넌스 명문화 미흡 차원의 FINDING이며, 헌법 §4 본문 위배는 아님 → **PASS** (FINDING 2건 동반).

---

## §3. 판정 종합

| # | 항목 | 판정 | FINDING 동반 |
|---|---|---|---|
| 1 | §2.1 LLM 직접 주문 실행 금지 | **PASS** | 없음 |
| 2 | §2.2 결정론 코어와 LLM 물리적 분리 | **PASS** | 없음 |
| 3 | §2.5 LLM 출력 영구 보존 | **PASS** | 없음 |
| 4 | §3.1 4계층 단방향 흐름 | **PASS** | 없음 |
| 5 | §4 사용자 통제권·이해 | **PASS** | 2건 (5.b, 5.c) |

**FAIL 0건. PASS 5건. FINDING 2건.**

---

## §4. FINDING 정리 (Phase 2 brief 또는 backlog 이관)

### F-1 (점검 5.b 출처) — ADR-014 §1 카테고리 사후 검증

| 항목 | 내용 |
|---|---|
| **출처** | 본 감사 점검 5.b — ADR-010 §1, ADR-010 §6, ADR-011 §3 표·subsection 4건 본문 수정 사례 |
| **현재 상태** | 가시 증거상 헌법 위배 아님. 4건 모두 결정 번복이 아닌 보강·명문화. Architect가 사용자 승인하에 적용. |
| **Auditor 한계** | ADR-014 본문이 `phase2/governance-update` 브랜치에 위치, main eb09b80 미머지 → 본 Auditor 가시 범위 밖 |
| **권고 처리** | Architect 세션에서 ADR-014 본문 확정 후, 본 4건이 ADR-014 §1의 어느 카테고리(예: "결정 보강·현실 반영")에 해당하는지 ADR-014 본문 또는 `04_DECISIONS.md` 메타 노트로 사후 명문화 |
| **이관 대상** | Phase 2 brief — ADR 갱신 정책 정합성 검토 sprint (06_CURRENT_STATE.md 신설 미해결 이슈 후보) |
| **우선순위** | 보통 (Phase 2 진입 자체에는 영향 없음. 차후 ADR 본문 수정 발생 시 절차 명료성 확보용) |

### F-2 (점검 5.c 출처) — phase1_brief §10.4 "1번 예외" 명문화

| 항목 | 내용 |
|---|---|
| **출처** | 본 감사 점검 5.c — Q-003·Q-004를 Builder가 직접 등록할 때 인용한 "§10.4 1번 예외"가 brief 본문에는 명시되지 않음 |
| **현재 상태** | 헌법 위배 아님. Builder가 매 사례마다 사유·범위(1.3 단계 한정)를 기록하고 사용자가 PROD 적용 시 직접 검증. ADR-005 거버넌스 명문화 정신 부합. |
| **권고 처리** | Phase 2 brief 또는 ADR-014 거버넌스 갱신 정책 ADR에서 다음 명문화 필요: <br>(a) operational_queue.md에 한해 Builder의 직접 등록 가능 조건<br>(b) 등록 시 사유·범위 기록 의무<br>(c) Architect 사후 확인 절차 |
| **이관 대상** | Phase 2 brief — Builder/Architect 분리 보강 sprint 또는 ADR-014 본문 |
| **우선순위** | 보통 (현재 운영상 위험 없음. 명문화 누락만 보완하면 됨) |

---

## §5. FAIL 정리

**FAIL 항목 0건.**

Phase 2 진입 전 **필수 처리 의무 사항 부재**.

---

## §6. Phase 2 진입 가·부

### 6.1 종합 의견

✅ **Phase 2 sprint 진입 가**.

- 헌법 §2.1·§2.2·§2.5·§3.1·§4 다섯 항목 모두 PASS.
- Phase 1 1.3.11 게이트 14/14 통과 (Builder 자체 점검) — 본 감사로 검증 완료.
- 정성 평가 (§9.2): 분류 합리성 운용적 완화 + watch 활용성 판단 유보 + ignore 정당성 우수 + confidence 일관 + entry_params 실행 가능 — Evaluator 1차 외부 평가 "쓸만한 수준 Yes, Phase 1 종료 적정" 명시.
- 167행 누적 + 158호출 정상 + ADR-013 안전망(ETF 12건 Pre-Check) 정상 작동 — 운영 데이터 충분.

### 6.2 Phase 2 진입 시 함께 인계되는 사항

본 감사 결과로 Phase 2 brief 작성 시 반영 권고:

(1) **F-1, F-2 두 FINDING**: ADR-014 §1 카테고리 사후 검증 + §10.4 "1번 예외" 명문화. Architect 세션이 phase2/governance-update 브랜치 작업 1·2·3·4·5·6 마무리 시 함께 처리.

(2) **Phase 1 종료 보고에서 Builder가 인계한 6항목** (phase1_progress.md line 1620~1627) 그대로 인계 — 본 감사와 직접 관련은 없으나 거버넌스 정합성 측면에서 함께 처리하면 효율적:
- ARCHITECTURE.md §5 LLM 외부 의존성 표 갱신
- ADR-010 §1 raw SQL 위치 갱신 (eb09b80에 이미 반영, **확인 완료**)
- ADR-011 §3 cost_usd 처리 표 갱신 (eb09b80에 이미 반영, **확인 완료**)
- phase1_brief.md §9.1 1.1 게이트 API 백엔드 항목 갱신
- ADR-013 정책 확장 (Q-004 연계 + preferred stock/CEF 범위)
- 06_CURRENT_STATE.md Phase 2로 갱신 + Phase 2 brief 작성

(3) **Phase 2 entry-side 정식 평가 sprint**: §9.2 기준 1 운용적 완화(entry 0건)에 대한 후속 검증. Builder 자체 권고 — 자연 누적 데이터 활용.

(4) **운영 큐 Q-004 처리**: Phase 2 Architect 세션에서 ADR-013 확장 + us_symbol_master 12건 정정 함께.

(5) **Evaluator 보강 권고 5종** (phase1_progress line 1594~1602): boundary 결정성, known_warnings severity 매핑, revisit_condition 필드, earnings warning, VCP 정량화 — Phase 2 sprint 후보.

### 6.3 본 감사의 시간적 봉인

본 보고서는 main `eb09b80` 시점 + `phase1/1.3-daily-analysis` 브랜치 코드 미머지 상태 + `phase2/governance-update` 브랜치 미가시 상태에서 작성됨.

ADR-014·015 본문 확정 후 또는 phase2/governance-update 머지 후 본 감사의 F-1·F-2 항목 사후 검증이 Architect 세션 책임으로 인계됨. 그 검증 결과는 본 `phase1_audit.md`에 추가하지 않고, Phase 2 진행 기록 또는 별도 파일(`phase1_audit_addendum.md` 등)로 처리할 것을 권고 — 본 감사의 시간적 봉인 유지.

---

## §7. 본 감사의 자기 한계 명시

본 Auditor가 검증하지 못한 것:

- `apps/llm-analysis/` 코드 본문의 직접 검수 — Builder 자체 점검(phase1_progress.md), Architect 인계 기록(06_CURRENT_STATE.md), Evaluator 외부 평가 결과의 정합성에 의존.
- ADR-014·015 본문 — phase2/governance-update 브랜치 미가시.
- LLM 호출 167행·158회의 모든 행 직접 SELECT — Builder 자체 통계 + Q-003 첫 실행 검증(AMDG, llm_calls id=7) + Evaluator 표본 7건 등 간접 증거에 의존.

이 한계 내에서 수행한 본 감사의 결론은 **PASS 5/5, FINDING 2건, FAIL 0건**입니다. ADR-014 본문 확정 후의 사후 재검증을 통해 F-1 항목이 정식 PASS로 전환될 것으로 예상되나, 본 Auditor의 시간적 봉인을 유지하기 위해 본 보고서 자체에는 추가하지 않습니다.

---

*Phase 1 헌법 5종 점검 보고: Auditor 2026-05-10*
*PASS 판정에 따라 Phase 2 sprint 진입 가능. F-1·F-2 FINDING은 Phase 2 brief 작성 시 함께 처리 권고.*
