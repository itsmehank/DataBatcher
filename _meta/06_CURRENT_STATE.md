# 현재 진행 상황

> 이 문서는 프로젝트의 현재 상태를 한 페이지로 요약한다.  
> **새 AI 세션을 시작할 때 가장 먼저 읽는 문서**다.  
> Phase 종료 시, 또는 큰 변경 시 갱신한다. 가능한 한 짧게 유지한다.

---

## 현재 위치

**완료된 Phase**: Phase 0 + P0 정합성 검토 + **P0.5 스크리너 개편**

**진행 중인 Phase**: 없음 (**Phase 1 brief 작성 완료, Builder 세션 진입 대기**)

**다음 시작할 Phase**: **Phase 1 — LLM 분석 레이어 구축**

**Phase 1 시작 조건**:
1. ✅ `_meta/phases/phase1_brief.md` 작성 완료 (Architect 세션, 2026-04-26)
2. ✅ ADR-011, ADR-012 확정 (CLI 백엔드 + 자동 트리거)
3. ✅ 운영 환경 Q-001 적용 완료 (P0.5 마이그레이션, 2026-04-26 18:18 KST)
4. ⏳ 사용자가 Phase 1 brief 최종 검토 후 Builder 세션 시작 (DEV 환경, Mac)

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

**시각화 백엔드 + 프론트엔드** (계층 3 (4) 일부)
- FastAPI 백엔드 (auth/rate_limit/region 라우팅 포함)
- React + TypeScript + Vite 프론트엔드
- Dashboard, ChartView, ListView, Login 페이지
- `minervini_list_selection` 테이블 + API로 focus/action/pass 선택 상태 관리
- region (KR/US) × market × list_category 조회 지원

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
- ADR-009: `daily_analysis` 시장별 분리 + 스크리너 `conditions_met` 추가 + `llm_calls` 신설 → **P0.5에서 스크리너 개편 부분 실행 완료**
- ADR-010: 마이그레이션 일원화 + 운영 작업 큐 도입
- ADR-011: Phase 1은 Max 플랜 + Claude Code CLI를 기본 백엔드로 (ADR-003 조건부 예외, §1은 ADR-012로 부분 개정, 2026-10-24 재검토)
- ADR-012: Phase 1 LLM 분석 자동 트리거 허용 (Windows Task Scheduler, US 16:00 / KR 21:00 KST, 모니터링 4종 가동)

전체 ADR은 `04_DECISIONS.md` 참조.

---

## Phase 1 시작 전 남은 일 (체크리스트)

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

### Phase 1 brief 작성 시 결정된 것 (모두 완료)
- [x] (5) `analyze_chart`의 JSON 출력 스키마 프롬프트 v1 (brief §6.2)
- [x] (6) `calculate_entry_params`의 JSON 출력 스키마 프롬프트 v1 (brief §6.3)
- [x] 52주 고가/저가, volume_ma20 처리 방식: LLM 호출부에서 즉석 계산 (brief §2.2)
- [x] 새 앱 디렉토리: `apps/llm-analysis/` (brief §5)
- [x] 배치 통합 방식: Windows Task Scheduler 자동 트리거, US 16:00 / KR 21:00 KST (brief §8, ADR-012)

### Phase 1 Builder 세션 첫 작업 (1.1 단계)
- [ ] Q-002 등록 + 적용 (`daily_analysis_kr/us`, `llm_calls` 테이블 마이그레이션 3종 산출물: Alembic + raw SQL + 운영 큐)
- [ ] `apps/llm-analysis/` 디렉토리 골격 (brief §5.2 구조)
- [ ] `LLMBackend` 추상화 + CLI/API 두 구현체 (ADR-011 §2)
- [ ] `analyze_chart()` 구현 + 프롬프트 v1 튜닝 + 단일 종목 검증
- [ ] 1.1 게이트 체크리스트 통과 (brief §9.1)

### Phase 1 Builder 세션 후속 (1.2, 1.3 단계)
- [ ] 1.2: `calculate_entry_params()` 구현 + EntryParams Pydantic + 정량 검증
- [ ] 1.3: `run_daily_analysis.py` 메인 진입점 + 모니터링·안전장치 구현 (ADR-012 §3) + Q-003 등록·적용 (Task Scheduler) + 7거래일 누적 검증

---

## 미해결 이슈

### A. 마이그레이션 관리 이원화 문제 (P0.5 발견 → ADR-010으로 처리됨)

**현상**: `scripts/migrations/*.sql` 8개 파일이 Alembic 체계 밖에 있었음. `alembic upgrade head`만으로는 프로덕션과 동일 스키마에 도달할 수 없는 상태.

**처리**: **ADR-010(2026-04-24)으로 결정 완료**. 향후 모든 새 스키마 변경은 ① Alembic ② raw SQL ③ 운영 큐 항목 3종 산출물을 함께 작성. 기존 `scripts/migrations/*.sql`은 보존(과거 이력)하되 새 raw SQL은 그 디렉토리에 추가하지 않음. 본 항목은 **해소**.

**남은 후속 작업**: DEV·PROD `alembic_version` 동기화 — 추후 별도 큐 항목으로 다룸 (ADR-010 §5).

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

**재검토 트리거 (ADR-011 §5 + ADR-012 §6)**:
- (a) Phase 5 백테스트 결과
- (b) 2026-10-24 시점 도달 (ADR-011 채택 후 6개월)
- (c) Anthropic 정책 변경
- (d) 사용자 판단
- (e) ADR-012 §3.3의 약관 위반 징후 관측 시 — 즉시 재검토 + API 전환

재검토 결과는 새 ADR로 기록 (예: ADR-013).

### F. US daily 소요 시간 최적화 (별도 백로그)

**현상**: US daily 적재가 매 회 약 6시간 소요 (08:00~14:00 KST). 사용자가 "오래 걸리는 것 같다"고 식별.

**영향**: 
- ADR-012의 자동 트리거 안전 마진(US 14:00 종료 + ~1h50m → 16:00) 산정에 직접 영향
- US daily가 더 빨라지면 LLM 트리거 시각도 앞당길 수 있음 (사용자가 결과를 더 일찍 검토 가능)

**처리**: Phase 1 범위 밖. 별도 시점에 다룸. Phase 1 진행 중에는 현 6시간 가정 유지.

### G. DEV·PROD `alembic_version` 동기화 (ADR-010 §5에서 예고됨)

**현상**:
- DEV (Mac): `alembic_version` 테이블 존재, `20260424_000001 (head)` stamp 완료
- PROD (Win): Q-001 적용 시 `alembic_version` 테이블 미생성 (raw SQL만 적용)

**영향**: 향후 Q-002 (Phase 1 마이그레이션) 적용 시 PROD에 `alembic_version`을 어떻게 도입할지 결정 필요.

**처리**: Phase 1 1.1 단계 Q-002 등록 시점에 함께 결정. 새 큐 항목으로 분리 가능.

---

## 환경 / 설정 상태

- **개발 환경 (DEV)**: Mac 노트북 (macOS, bash/zsh)
- **운영 환경 (PROD)**: 집 PC 24시간 가동 (Windows + PowerShell + Task Scheduler)
- **DB**: MySQL 8.4.8 — DEV 로컬 Docker / PROD `mysql-standalone-mysql` Docker 컨테이너
- **외부 접속**: 미설정 (Phase 3에서 Cloudflare Tunnel 또는 Tailscale 도입 예정)
- **Anthropic 자격증명**: 
  - Phase 1 기본은 CLI 백엔드 (Max 플랜 로그인)
  - API 백엔드는 Phase 1 안에 추상화·검증 (전환 대비). ANTHROPIC_API_KEY는 그때 셋업.
- **배치 스케줄러**: 
  - Daily cron: cron (Linux/macOS) + Windows Task Scheduler (Phase 0에서 구성, 정상 동작 확인 — 2026-04-26)
  - LLM 분석 자동 트리거 (Phase 1.3에서 도입): Windows Task Scheduler에 `LLMAnalysis_US`(매일 16:00 KST) / `LLMAnalysis_KR`(매일 21:00 KST) 등록 예정 (ADR-012)
- **Alembic**: 
  - DEV: P0.5에서 `20260424_000001 (head)`로 stamp 완료
  - PROD: Q-001 적용 시 raw SQL만 적용, `alembic_version` 테이블 미생성 (ADR-010 §5). 동기화는 별도 작업 — 미해결 이슈 §G 참조.

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
- **Phase 1 brief**: `_meta/phases/phase1_brief.md` (현재 SSoT)

**운영**:
- 운영 작업 큐: `_meta/operational_queue.md`

**실무 참조**:
- 빌드/실행/테스트: `CLAUDE.md`, `README.md`
- 코드베이스 탐색: `apps/ingest-databatcher/`, `apps/trading-view-project/`

---

*마지막 업데이트: 2026-04-26 (Phase 1 brief 작성 완료, ADR-012 채택, Q-001 운영 환경 적용 완료, Builder 세션 진입 대기)*