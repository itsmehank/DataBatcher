# 현재 진행 상황

> 이 문서는 프로젝트의 현재 상태를 한 페이지로 요약한다.  
> **새 AI 세션을 시작할 때 가장 먼저 읽는 문서**다.  
> Phase 종료 시, 또는 큰 변경 시 갱신한다. 가능한 한 짧게 유지한다.

---

## 현재 위치

**완료된 Phase**: Phase 0 + P0 정합성 검토 + P0.5 스크리너 개편 + **Phase 1 완료**

**진행 중인 Phase**: **Phase 2 (Sprint 1 완료, Sprint F·Sprint 2 진입 준비)**

**다음 시작할 단계**: Sprint 1 main 통합 머지 완료 (commit `6733778`, 2026-05-11). 다음 — **Sprint F (운영 부수 정리) 또는 Sprint 2 (SMTP 발송)**. 진행 순서는 `phase2_brief.md` §4 권고 따름.

---

## Phase 1 종료 시점 (2026-05-08)

**§9.1 게이트 14/14 통과** (`phase1_progress.md` "Phase 1 종료 보고" §1.3.11 게이트):
1. ✅ `run_daily_analysis.py` 작동 (KR/US 분리, 상한, 캐싱, dry-run, force-recompute)
2. ✅ `run_analysis_today.ps1` 래퍼 스크립트 작동
3. ✅ 일일 호출 상한 정확히 작동 (hard stop)
4. ✅ 캐싱 정확히 작동 (재실행 시 skip)
5. ✅ 부분 실패 처리 작동 (실패 종목 스킵, 나머지 진행)
6. ✅ `show_cost_summary.py` 작동
7. ✅ Q-003 PROD 적용 완료 (commit `14d6877`, merge `b806a5e`)
8. ✅ 7거래일 누적 167행 (KR 70 + US 97), 기준 50행의 3.3배
9. ✅ 사용자 정성 평가 "쓸만하다" + Evaluator 1차 7건 100% 합리
10. ✅ 헌법 §2.1 위배 없음 (LLM 직접 주문 실행 금지)
11. ✅ 헌법 §2.2 위배 없음 (결정론 코어·LLM 물리적 분리)
12. ✅ 헌법 §2.5 위배 없음 (모든 LLM 출력 영구 보존)
13. ✅ Q-001/Q-002/Q-003 모두 "완료된 작업" 섹션 이동
14. ✅ `phase1_progress.md` Phase 1 종료 보고 작성 (Builder 2026-05-08)

**Phase 1.3 시작 조건 (모두 충족)**:
- [x] 거버넌스 드리프트 6건 갱신 commit `92a8b77` (2026-05-07 봉인)
- [x] 1.3 시작 프롬프트 작성 (Architect 세션, 산출물 (a) Builder 인계 프롬프트 + (b) Q-003 운영 큐 텍스트 초안)
- [x] (6) v1.1 fix 3가지 구현 (Builder 세션 1.3.0, commit `c2114f7`)
- [x] Q-002 운영 환경 적용 (PROD에 daily_analysis_kr/us, llm_calls 테이블 생성, 2026-05-07)

**§9.2 정성 평가 운용적 완화**:
- entry 0건 (B.5.5 자연 발생률 0.25% × 167행 expected 0~1건 정합) → 대체 평가 7건 100% 합리 (Evaluator 객관 검증)
- 정식 §9.2 기준 1 (entry 10개 70%+) 충족은 Phase 2 entry-side sprint에서 자연 누적 후 처리 예정

**Phase 1 종료 시점 봉인**:
- Builder 작업 commit: 1.3.11 종료 보고 (`phase1/1.3-daily-analysis` 브랜치)
- _meta/만 main 사전 머지: commit `eb09b80` (Web Claude 동기화 정합성 확보)
- 코드 (apps/, db/) 통합 머지: commit `5125d71` (main, 2026-05-10) — Auditor PASS 후 완료
- Q-004 PROD 자연 완료: commit `0da41cd` (운영 큐 "완료된 작업" 이동 + Sprint F #6 PROD=main 원칙 명문화 동반)

---

## Phase 2 시작 조건

**선행 조건 (Architect 세션, 본 세션 산출)**:
- [x] ADR-014 (ADR 갱신 정책 명문화) 채택
- [x] ADR-015 (ADR-013 정책 확장 + us_symbol_master 보강) 채택
- [x] 거버넌스 드리프트 일괄 갱신 (06_CURRENT_STATE / 05_GLOSSARY B.2 / phase1_brief §6.3·§11.4-bis / operational_queue Q-004)
- [x] Phase 2 brief 작성 (`_meta/phases/phase2_brief.md`) — Phase 2A 메일+엑셀 + Phase 2B Phase 1 인계 sprint

**Phase 2 진입 직전 조건** (모두 충족, 2026-05-11 봉인):
- [x] Auditor 세션 PASS (헌법 §2.1·§2.2·§2.5·§3.1·§4 점검 — phase1_brief §9.3 5종) — `phase1_audit.md` + `phase1_audit_addendum.md` (F-1·F-2 모두 PASS 전환)
- [x] Auditor 산출물 `_meta/phases/phase1_audit.md` commit — 2026-05-10
- [x] Phase 1 코드 머지 (apps/, db/) — commit `5125d71` (main, 2026-05-10)
- [x] Phase 2 brief 사용자 승인 — 2026-05-11 Architect 세션에서 사용자 명시 승인
- [x] Q-004 적용 — commit `0da41cd` (자연 완료, 운영 큐 "완료된 작업" 이동)
- [x] Sprint 1 main 통합 머지 완료 (2026-05-11, merge commit `6733778`; phase2/sprint1-excel 9 commit 통합)

---

## Phase 0에서 완료된 것 (실제 스냅샷 기준)

**데이터 수집 및 적재** (계층 1 (1))
- KR 주식·ETF (KOSPI/KOSDAQ, pykrx)
- US 주식·ETF (NYSE/NASDAQ, FinanceDataReader)
- KR 지수, US 지수
- 크립토 (Binance Spot, USDT pairs)
- 일봉 + 주봉 모두 지원
- 심볼 마스터, sync_log, 섹터 스냅샷까지 구축

**인디케이터 계산** (계층 1 (2))
- SMA (50/100/150/200 기본 + backfill 확장 가능)
- EMA
- IBD RS Rating (3m/6m/9m/12m 가중 cross-sectional 백분위)
- RS Line (vs KOSPI / vs S&P 500)
- Blue Dot (RS 신고가 + 가격 비신고가)
- Long-form 저장 + wide-form 뷰(`v_*_price_with_ma`) 제공 (ADR-006)

**미너비니 템플릿 필터링** (계층 1 (3))
- KR/US 시장별 분리 스크리닝
- `screen_config_hash`로 설정 버전 관리 (ADR-008)
- **P0.5 완료**: 8조건 완전 구현 + `conditions_met` JSON 저장 (ADR-009)
- **Phase 1.2 트랙 A**: ADR-013 ETF upstream 필터 적용 (option a, commit `abbaeb2`)

**시각화 백엔드 + 프론트엔드** (계층 3 (4) 일부)
- FastAPI 백엔드 (auth/rate_limit/region 라우팅 포함)
- React + TypeScript + Vite 프론트엔드
- Dashboard, ChartView, ListView, Login 페이지
- `minervini_list_selection` 테이블 + API로 focus/action/pass 선택 상태 관리
- region (KR/US) × market × list_category 조회 지원

---

## Phase 1에서 완료된 것 (2026-04-28 ~ 2026-05-08, 약 11일)

**LLM 분석 레이어 (계층 2)**:
- (5) `analyze_chart()` v2 production lock — `apps/llm-analysis/prompts/analyze_chart_v2.md`
- (6) `calculate_entry_params()` v1.1 production lock — `apps/llm-analysis/prompts/calculate_entry_params_v1_1.md`
  - 17필드 (rename 1 + new 4: `current_price`, `trigger_price`, `stop_loss_pct_from_current_price`, `observed_breakout_volume_ratio`)
  - KnownWarning enum 12종 (auto-emit 2종: `stop_distance_from_current_price_exceeds_book_limit`, `breakout_volume_below_requirement`)

**DB 스키마 (Q-002 PROD 적용 완료)**:
- `daily_analysis_kr`, `daily_analysis_us` 신설 (ADR-009)
- `llm_calls` 신설 (헌법 §2.5 준수)

**LLM 백엔드 추상화 (ADR-011·ADR-012)**:
- `LLMBackend` interface + `ClaudeCodeCLIBackend` (Max 플랜) + `AnthropicAPIBackend` (fallback)
- Windows 호환 fix (`anthropic_client.py` cmd stdin 방식, Q-003 적용 시점 발견)

**자동 운영 (Phase 1.3, ADR-012)**:
- `run_daily_analysis.py` 메인 진입점 (KR/US 분리, hard stop 상한, 캐싱, dry-run, force-recompute, 부분 실패 스킵)
- `show_cost_summary.py` 비용·호출 보고
- Windows Task Scheduler `LLMAnalysis_US`(16:00 KST) + `LLMAnalysis_KR`(21:00 KST) 등록 (Q-003)
- 모니터링 4종 (sync_log, 일일 상한, 약관 위반 징후 카운터, 호출 로그 주간 점검)

**검증**:
- B.5.5 sample (n=400) 정량 검증 + NVST entry_params Evaluator 2회 검토
- 7거래일 누적 167행 + Evaluator 1차 평가 (7건 표본 100% 합리적, "쓸만한 수준 Yes")

상세 진행 기록: `_meta/phases/phase1_progress.md` (1645 라인, Phase 1.1 ~ 1.3.11 종료 보고)

---

## P0.5에서 완료된 것 (2026-04-24)

스크리너 개편 (ADR-009 실행):
- `minervini_screen_results_kr/us`에 `conditions_met JSON` 컬럼 추가
- `indicators/minervini/trend_template.py` 리팩토링 — `_compute_condition_masks()` 헬퍼 분리, 8조건 각각 독립 평가
- `kr_minervini_update.py`, `us_minervini_update.py` 수정 — `conditions_met` JSON 저장 로직 추가
- 테스트 DB 검증 완료 (KR 95건, US 78건, 8개 키 모두 `true`)
- 프로덕션 DB 마이그레이션 적용 완료
- Alembic 버전 파일까지 함께 작성 (`20260424_000001_add_conditions_met_column`)
- 프로덕션 `alembic_version` 테이블도 이번에 처음 생성됨 (stamp: `20260424_000001 (head)`)

상세 진행 기록: `_meta/phases/phase0_5_progress.md`

---

## 주요 결정 사항 (최근 / 중요한 것만)

- ADR-001: 4계층 아키텍처 채택
- ADR-002: LLM은 직접 주문 실행 안 함
- ADR-003: LLM 호출은 Anthropic API 사용 (Claude Code CLI 미사용)
- ADR-004: LLM 분석은 일일 배치만 (장중 실시간 미포함)
- ADR-005: 영속 문서 기반 거버넌스 + SSoT = 로컬 Git
- ADR-006: 인디케이터 long-form 저장 (소급)
- ADR-007: OHLCV·스크리닝 결과 시장별 분리 (소급)
- ADR-008: `screen_config_hash`로 스크리너 설정 버전 관리 (소급)
- ADR-009: `daily_analysis` 시장별 분리 + 스크리너 `conditions_met` 추가 + `llm_calls` 신설 → **P0.5에서 스크리너 개편 부분 실행 완료, Phase 1에서 LLM 분석 테이블 신설 완료**
- ADR-010: 마이그레이션 일원화 + 운영 작업 큐 도입
- ADR-011: Phase 1은 Max 플랜 + Claude Code CLI를 기본 백엔드로 (ADR-003 조건부 예외, §1은 ADR-012로 부분 개정, 2026-10-24 재검토)
- ADR-012: Phase 1 LLM 분석 자동 트리거 허용 (Windows Task Scheduler, US 16:00 / KR 21:00 KST, 모니터링 4종 가동)
- ADR-013: 미너비니 스크리너에서 ETF 제외 (사용자 정책 명문화, Phase 1.1.15 외부 평가 반영, §1·§4는 ADR-015로 확장됨)
- **ADR-014**: ADR 갱신 정책 — 본문 수정의 경계 명문화 (4 카테고리 허용 + 변경 이력 표기 의무, 2026-05-09)
- **ADR-015**: ADR-013 정책 확장 — Fund Vehicle 분류 4 카테고리 명확화 + us_symbol_master 정확성 보강 (2026-05-09)

전체 ADR은 `04_DECISIONS.md` 참조.

---

## Phase 1 시작 전 남은 일 (체크리스트, 모두 완료)

### 이미 완료된 것
- [x] `_meta/` 거버넌스 문서 셋 구성
- [x] 루트 `CLAUDE.md`, `README.md`에 `_meta/` 참조 추가
- [x] 설계 결정 확정 (ADR-006 ~ ADR-009)
- [x] `_meta/phases/phase0_alignment_review.md` 작성
- [x] `_meta/phases/phase0_5_screener_refactor.md` 작성
- [x] P0.5 스크리너 개편 실행 (`conditions_met` 컬럼 + 8조건 완전 구현)
- [x] P0.5 PR 머지 (`phase0_5/screener-refactor` → `main`)
- [x] **Daily cron 정상화 확인** (이슈 C 해소, 2026-04-26)
- [x] **운영 환경 Q-001 적용 완료** (2026-04-26 18:18 KST, P0.5 마이그레이션)
- [x] **`_meta/phases/phase1_brief.md` 작성 완료** (Architect 세션, 2026-04-26)
- [x] **ADR-011 확정** (CLI 백엔드 + Max 플랜)
- [x] **ADR-012 확정** (자동 트리거 + 모니터링 4종)

### Phase 1 진행 중 모두 완료
- [x] **ADR-013 구현** (ETF 스크리너 제외 — 1.2 트랙 A, commit `abbaeb2`, 2026-05-03)
- [x] **(6) v1.1 fix 3가지** (1.3.0, commit `c2114f7`, 2026-05-07) — stop_pct dual reporting / breakout_volume mismatch auto-warning / pivot vs trigger schema-level reconcile
- [x] **Q-002 운영 환경 적용** (2026-05-07, daily_analysis_kr/us + llm_calls)
- [x] **1.2: `calculate_entry_params()` 구현 + EntryParams Pydantic + 정량 검증** (commit `dd09e2d`, 2026-05-05)
- [x] **1.3: `run_daily_analysis.py` + 모니터링·안전장치 + Q-003 적용 + 7거래일 누적 검증** (commit `b806a5e`, 2026-05-08)
- [x] **alembic.ini 자격증명 변경** — Phase 1 종료 시점에 보류 결정 (별도 큐 또는 Phase 2 sprint에서 처리)

---

## 미해결 이슈

### A. 마이그레이션 관리 이원화 문제 (P0.5 발견 → ADR-010으로 처리됨, 해소)

**현상**: `scripts/migrations/*.sql` 8개 파일이 Alembic 체계 밖에 있었음. `alembic upgrade head`만으로는 프로덕션과 동일 스키마에 도달할 수 없는 상태.

**처리**: **ADR-010(2026-04-24)으로 결정 완료**. 향후 모든 새 스키마 변경은 ① Alembic ② raw SQL ③ 운영 큐 항목 3종 산출물을 함께 작성. 기존 `scripts/migrations/*.sql`은 보존(과거 이력)하되 새 raw SQL은 그 디렉토리에 추가하지 않음. 본 항목은 **해소**.

**남은 후속 작업**: DEV·PROD `alembic_version` 동기화 — 추후 별도 큐 항목으로 다룸 (ADR-010 §5, 미해결 이슈 §G).

### B. 테스트 DB 스키마 드리프트 (P0.5 발견, 우선순위 낮음)

**현상**: `trade_test.stock_prices`에 `currency` 컬럼이 남아있음. 프로덕션에는 없음.

**영향**: 테스트 DB → 프로덕션 데이터 복사 시 `SELECT *` 사용 불가.

**처리**: `scripts/migrations/remove_currency_column.sql`을 테스트 DB에 적용. 일회성 작업, 별도 결정 불필요.

### C. ~~Daily cron 상태 불명~~ (해소, 2026-04-26)

**처리**: 운영 환경 점검 결과 cron 정상 동작 확인. **해소**.

**확정된 cron 시각** (operational_queue.md 환경 정보에도 반영):
- US daily: 매일 08:00 KST 시작, 최대 6시간 소요 (~14:00 종료)
- KR daily: 매일 19:00 KST 시작, 최대 30분 소요 (~19:30 종료)

이 시각은 ADR-012의 자동 트리거 시각(US 16:00 / KR 21:00) 산정 근거가 됨.

### D. `watchlist_items` vs `minervini_list_selection` (Phase 6 예정)

전자는 legacy(미사용), 후자가 현역. Phase 6에서 `order_reservations` 설계 시 `watchlist_items` 제거 검토.

### E. ADR-011 / ADR-012 재검토 일정 (2026-10-24 또는 사용자 판단 시점)

**현상**: 
- ADR-011: Phase 1 LLM 백엔드를 Claude Code CLI(Max 플랜)로 운영. 약관 회색 지대 + 비용 메트릭 부실 등 트레이드오프 수용.
- ADR-012: ADR-011 §1을 부분 개정하여 Windows Task Scheduler 자동 트리거 허용. 모니터링 4종 가동.

**Phase 1 운영 결과**: ADR-012 §3 모니터링 4종 모두 정상 가동. 약관 위반 징후 관측 0건. Phase 1 7거래일 운영 무사 종료.

**재검토 트리거 (ADR-011 §5 + ADR-012 §6)**:
- (a) Phase 5 백테스트 결과
- (b) 2026-10-24 시점 도달 (ADR-011 채택 후 6개월)
- (c) Anthropic 정책 변경
- (d) 사용자 판단
- (e) ADR-012 §3.3의 약관 위반 징후 관측 시 — 즉시 재검토 + API 전환

재검토 결과는 새 ADR로 기록 (ADR-016 또는 후속).

### F. US daily 소요 시간 최적화 (별도 백로그)

**현상**: US daily 적재가 매 회 약 6시간 소요 (08:00~14:00 KST). 사용자가 "오래 걸리는 것 같다"고 식별.

**영향**: 
- ADR-012의 자동 트리거 안전 마진(US 14:00 종료 + ~1h50m → 16:00) 산정에 직접 영향
- US daily가 더 빨라지면 LLM 트리거 시각도 앞당길 수 있음 (사용자가 결과를 더 일찍 검토 가능)

**처리**: Phase 1 범위 밖. 별도 시점에 다룸. Phase 1 운영 중에는 현 6시간 가정 유지.

### G. DEV·PROD `alembic_version` 동기화 (ADR-010 §5에서 예고됨)

**현상**:
- DEV (Mac): `alembic_version` 테이블 존재, `20260428_000001 (head)` stamp 완료 (Phase 1 1.1 마이그레이션 후)
- PROD (Win): Q-001/Q-002 적용 시 `alembic_version` 테이블 미생성 (raw SQL만 적용)

**영향**: 향후 신규 마이그레이션 적용 시 PROD에 `alembic_version`을 어떻게 도입할지 결정 필요.

**처리**: Phase 2 sprint에서 결정. ADR-010 §6에서 alembic.ini 자격증명을 env 참조 방식으로 단일화하기로 결정 (코드 변경은 별도 작업, Phase 2에서 처리).

### H. 1.1.15 외부 평가 후속 작업 (Phase 2 prompt v3 sprint에서 처리)

**배경**: Phase 1.1.15 외부 평가(Web Claude Minervini Evaluator 프로젝트)에서 v2 production-ready 판정과 함께 다음 5가지 후속 검증 항목이 도출됨.

**항목**:
1. AAOI reverse_split 누락 — price_data_notes의 split 정보를 deterministic하게 소비하도록 v3 prompt 보강 검토
2. completion 토큰 폭증 (v1 평균 ~1,800 → v2 평균 ~3,000, 60% 증가) — ignore 케이스용 "tight reasoning" 지시 검토
3. entry 후보 5~10종목 별도 검증 배치로 pivot/breakout 정확도 (약점 F) 검증 — 1.3 누적 데이터 활용
4. reasoning 사실 정확성 sanity check — 구체 숫자(volume, % 수치)가 source data와 일치하는지 자동 비교
5. 추가 taxonomy 후보: `late_stage_base`, `distribution_days`, `reversal_off_high` (평가 LLM 제안)

**Phase 1.3 운영 결과 추가 발견** (Evaluator 1차 평가 약점 6종):
6. entry-side 검증 부재 — 167행 entry 0건이라 실질적 entry 정확도 미검증 (Phase 2 entry-side 평가 sprint)
7. watch reasoning 모호성 — ALTO 5/1 "Monitor for pullback/base"가 ignore와 경계 불명확
8. boundary 결정성 부족 — "얼마나 확장되어야 extended_from_ma인가" 등 정량 경계 미명시
9. VCP 정량화 미비 — VCP 패턴 인식 정량 기준 부재

**처리**: Phase 2B Sprint "(5) prompt v3 + (6) prompt v1.2" 항목으로 통합. Phase 2 brief 참조.

### I. daily_analysis 테이블의 prompt_version 컬럼 추가 검토 (ADR 후보)

**현상**: Phase 1.1.15에서 v1 → v2 force-recompute 시 DELETE+INSERT 방식으로 v1 결과가 overwrite됨. 비교 검증을 위해 v1 결과를 별도 백업 파일과 llm_calls 테이블에 의존.

**개선안**: `daily_analysis_kr/us`에 `prompt_version` 컬럼 추가 + PK를 (symbol, date, prompt_version)로 확장. v1/v2 결과 동시 보존 가능.

**처리**: Phase 2 prompt v3 sprint 진입 직전 Architect 세션에서 운영 부담 vs 가치 판단. 운영 부담 작으면 현행 유지(eval_input.json + llm_calls로 복원 가능). ADR 후보.

### J. ETF 잘못 통과 — ADR-015로 처리됨 (해소)

**현상 (Phase 1 관측)**:
- B.5.5 sample 추출 시 6건 (EMF, RMT, CEE×2, KF, CAF) — 모두 closed-end fund 계열
- 1.3.10 자연 운영 12건 (VRTL, SOXL, MVLL, MUU, MULL, AMDG, AMDL, AMUU, KORU, INTW, DLLL, BWET) — leveraged ETF 다수

**처리 (2026-05-09)**: **ADR-015 채택**으로 정책 명문화 — Fund Vehicle 4 카테고리(ETF / Leveraged ETF / CEF / ADR) 명확화 + us_symbol_master 정확성 보강 정책 확정.

**남은 작업**:
- Q-004 (1.3.10 12건) 운영 큐 적용 — Phase 2 sprint 진입 전 또는 sprint 내 처리
- B.5.5 6건 점검 후 추가 큐 등록 (필요 시)
- us_sync_symbol_master.py 보강 + override 테이블 신설 — Phase 2B Sprint "ADR-015 구현" 항목

### K. (5) v2 분류 보수성 — Phase 1.3 결과 평가

**Phase 1.3 결과 (2026-05-08)**:
- 167행 entry 0건 — froth 시장 환경 + B.5.5 자연 발생률(0.25%) 통계와 정합
- systemic 보수성 문제로 결론 짓기 어려움
- Evaluator 1차 평가: ignore reasoning 품질 우수 (구체 수치 + 미너비니 원칙 명시), risk_flag 12종 whitelist 일관 적용
- 단, entry-side 정량 검증은 표본 부재로 미실시

**처리**: Phase 2B Sprint "entry-side 평가" + "(5) prompt v3 검토"로 이관. v3 작업은 자연 누적 데이터(Phase 2 시장 환경에서 entry 자연 발생) 후 systemic 평가 → v3 작업 여부 결정.

### L. (6) 함수 v1.1 fix 3가지 — 완료 (해소)

**Phase 1.3.0 처리 (commit `c2114f7`, 2026-05-07)**:
1. ✅ `stop_loss_pct_from_pivot` rename + `stop_loss_pct_from_current_price` NEW + auto-emit
2. ✅ `trigger_price` schema-level 분리 (pivot_price raw + trigger_price buffered)
3. ✅ `observed_breakout_volume_ratio` NEW + `breakout_volume_below_requirement` auto-emit

EntryParams 필드 13 → 16, KnownWarning enum 10 → 12. 단위 테스트 53/53 통과 + NVST 합성 검증 6/6 OK. 본 항목은 **해소**.

### M. 분류 불안정 — Phase 1.3에서 추가 사례 관찰

**Phase 1.3 누적 결과**:
- ALTO 4시점 toggle (4/28 ignore conf=0.75 → 5/1 watch 0.75 → 5/4 ignore 0.80 → 5/6 ignore 0.90)
- NVST 추가 사례 (B.5.5 entry → 2026-05-07 ignore, 1.3.0 v1.1 검증 시점 합성 호출)
- EA (1.2 트랙 B) 3시점 toggle (1/13 watch → 1/14 ignore → 1/15 timeout)

**해석 가능성**:
- 시장 변화로 실제 분류 변동 (정상)
- v2 응답 일관성 부족 (LLM 자체 노이즈)
- 분류 경계 정량화 미흡 — phase1_classification_logic_review §1.2 "watch vs ignore 경계 모호 케이스" 정합

**처리**: Phase 2B Sprint "분류 안정성 모니터링" — 자연 누적 데이터에서 multi-evaluated 종목의 분류 일관성 정량 측정 (예: revisit_condition 필드 추가 검토, watch ↔ ignore toggle 빈도 통계).

### N. database_schema.md 드리프트 (Phase 1.3 자동 발견, 1.3 세션 내 즉시 처리)

**현상 (2026-05-07 발견)**: `apps/ingest-databatcher/docs/database_schema.md` (Last Updated 2026-02-26)가 운영 DB 실제 상태와 불일치. 누락 테이블: `daily_analysis_kr`, `daily_analysis_us`, `llm_calls`, `users`, `minervini_list_selection`, `alembic_version`. 삭제된 테이블 `metrics`가 문서에 잔존. 신규 컬럼 `conditions_met` 누락. `kr_sector_snapshot` 설명 잘못됨.

**처리 (2026-05-07 Phase 1.3 세션 내)**: TOC + Table Summary 갱신, LLM Analysis Tables / Auth & User Tables 신규 섹션 추가, `conditions_met` 컬럼 + 8 키 명시, `metrics` 제거 (historical note만 잔존), `sync_log` "ETL + LLM 모니터링" 갱신, `kr_sector_snapshot` "테이블 존재" 정정, Scripts mapping에 LLM Analysis 추가. 1125 → 1325 lines. **해소**.

**Phase 2 갱신 의무 명문화**: Phase 2 brief에 "Phase별 종료 시 database_schema.md 동기화 의무" 명시 — 향후 sprint별 자동 점검 항목.

---

## 환경 / 설정 상태

- **개발 환경 (DEV)**: Mac 노트북 (macOS, bash/zsh)
- **운영 환경 (PROD)**: 집 PC 24시간 가동 (Windows + PowerShell + Task Scheduler)
- **DB**: MySQL 8.4.8 — DEV 로컬 Docker / PROD `mysql-standalone-mysql` Docker 컨테이너
- **외부 접속**: 미설정 (Phase 3에서 Cloudflare Tunnel 또는 Tailscale 도입 예정)
- **Anthropic 자격증명**: 
  - Phase 1 운영 중: CLI 백엔드 (Max 플랜 로그인)
  - API 백엔드 mock 검증 완료 (Phase 1.1.4-c 결정으로 실 SDK 호출은 ADR-011/013 전환 시점까지 미룸). ANTHROPIC_API_KEY는 그때 셋업.
- **배치 스케줄러**: 
  - Daily cron: cron (Linux/macOS) + Windows Task Scheduler (Phase 0에서 구성, 정상 동작 확인 — 2026-04-26)
  - LLM 분석 자동 트리거 (Phase 1.3에서 도입): Windows Task Scheduler에 `LLMAnalysis_US`(매일 16:00 KST) / `LLMAnalysis_KR`(매일 21:00 KST) 등록 완료 (Q-003, ADR-012)
- **Alembic**: 
  - DEV: P0.5에서 `20260424_000001` stamp + Phase 1.1에서 `20260428_000001 (head)` 갱신
  - PROD: Q-001/Q-002 적용 시 raw SQL만 적용, `alembic_version` 테이블 미생성 (ADR-010 §5). 동기화는 Phase 2 sprint — 미해결 이슈 §G 참조.

---

## 빠른 참조 링크

**거버넌스**:
- 헌법: `_meta/00_CONSTITUTION.md`
- 아키텍처: `_meta/01_ARCHITECTURE.md`
- 시나리오: `_meta/02_SCENARIO.md`
- 로드맵: `_meta/03_ROADMAP.md`
- 의사결정: `_meta/04_DECISIONS.md`
- 인터페이스: `_meta/05_GLOSSARY.md`

**Phase 문서**:
- Phase 0 정합성 검토: `_meta/phases/phase0_alignment_review.md`
- P0.5 스크리너 개편 가이드: `_meta/phases/phase0_5_screener_refactor.md`
- P0.5 진행 기록: `_meta/phases/phase0_5_progress.md`
- **Phase 1 brief**: `_meta/phases/phase1_brief.md`
- **Phase 1 진행 기록 + 종료 보고**: `_meta/phases/phase1_progress.md` (1645 라인)
- **Phase 1 분류 로직 조사 보고서**: `_meta/phases/phase1_classification_logic_review.md` (482 라인, Builder 자체 작성, Phase 2 분류 체계 개편 입력)
- **Phase 2 brief**: `_meta/phases/phase2_brief.md` (현재 SSoT, 2026-05-09 작성)

**운영**:
- 운영 작업 큐: `_meta/operational_queue.md` (Q-004 대기 중, Q-001~003 완료)

**실무 참조**:
- 빌드/실행/테스트: `CLAUDE.md`, `README.md`
- 코드베이스 탐색: `apps/ingest-databatcher/`, `apps/llm-analysis/`, `apps/trading-view-project/`

---

*마지막 업데이트: 2026-05-09 (Phase 1 종료 + Phase 2 진입 준비 완료 — Architect 세션. ADR-014 (ADR 갱신 정책) + ADR-015 (ADR-013 확장) 채택. 거버넌스 6건 일괄 갱신. Phase 2 brief 작성 완료. Auditor 세션 + Phase 2 sprint 진입 대기.)*
