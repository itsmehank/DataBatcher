# 현재 진행 상황

> 이 문서는 프로젝트의 현재 상태를 한 페이지로 요약한다.  
> **새 AI 세션을 시작할 때 가장 먼저 읽는 문서**다.  
> Phase 종료 시, 또는 큰 변경 시 갱신한다. 가능한 한 짧게 유지한다.

---

## 현재 위치

**완료된 Phase**: Phase 0 + P0 정합성 검토 + **P0.5 스크리너 개편**

**진행 중인 Phase**: 없음 (Phase 1 brief 작성 대기)

**다음 시작할 Phase**: **Phase 1 — LLM 분석 레이어 구축**

**Phase 1 시작 조건**:
1. Daily cron 정상화 확인 (아래 미해결 이슈 참조)
2. 마이그레이션 관리 체계 정리 방향 결정 (ADR 후보)
3. `_meta/phases/phase1_brief.md` 작성 (Architect 세션)

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

### Phase 1 시작 직전 해결 필요
- [ ] **Daily cron 점검** — 최신 적재가 KR 2026-04-02, US 2026-04-10에서 멈춰 있음. 원인 확인 후 재가동 또는 catch-up.
- [ ] **마이그레이션 관리 방향 결정** — ADR로 논의 필요 (P0.5 발견 이슈). 아래 "미해결 이슈" §A 참조.
- [ ] **다른 환경의 `alembic_version` 동기화** — 만약 다른 PC(윈도우 스케줄러 등)에서 이 DB를 공유한다면, 해당 환경에서도 `alembic stamp 20260424_000001` 실행 필요.

### Phase 1 brief 작성 시 결정할 것
- [ ] (5) `analyze_chart`의 JSON 출력 스키마 프롬프트 초안
- [ ] (6) `calculate_entry_params`의 JSON 출력 스키마 프롬프트 초안
- [ ] 52주 고가/저가, volume_ma20 처리 방식 (즉석 계산 vs 인디케이터 영구화)
- [ ] 새 앱 디렉토리 명명 및 구조 (`apps/llm-analysis/` 등)
- [ ] 배치 통합 방식 (기존 cron에 어떻게 끼워넣을지)

### Phase 1 Builder 세션 첫 작업
- [ ] `daily_analysis_kr`, `daily_analysis_us`, `llm_calls` 테이블 생성 (Alembic 버전 파일)
- [ ] `apps/llm-analysis/` (또는 합의된 이름) 신설
- [ ] `analyze_chart()`, `calculate_entry_params()` 구현
- [ ] 일일 배치 통합

---

## 미해결 이슈

### A. 마이그레이션 관리 이원화 문제 (P0.5 발견, 우선순위 중간)

**현상**: `scripts/migrations/*.sql` 8개 파일(KR 지수, US 지수, 섹터 컬럼, currency 제거 등)이 Alembic 체계 밖에 있음. `alembic upgrade head`만으로는 프로덕션과 동일 스키마에 도달할 수 없음.

**영향**: 새 환경 셋업, 서버 이전, 재해 복구 시 수동 SQL 실행이 필요하며, 어느 파일을 실행해야 하는지 불명확.

**Builder 제안**: Alembic으로 일원화. `scripts/migrations/*.sql`은 참고용 raw SQL로 유지, 실제 적용은 Alembic. 상세는 `phase0_5_progress.md` §5.

**처리 방향 결정 필요**: 
- 지금 ADR 작성하고 정리할지
- Phase 1 이후로 미룰지

### B. 테스트 DB 스키마 드리프트 (P0.5 발견, 우선순위 낮음)

**현상**: `trade_test.stock_prices`에 `currency` 컬럼이 남아있음. 프로덕션에는 없음.

**영향**: 테스트 DB → 프로덕션 데이터 복사 시 `SELECT *` 사용 불가.

**처리**: `scripts/migrations/remove_currency_column.sql`을 테스트 DB에 적용. 일회성 작업, 별도 결정 불필요.

### C. Daily cron 상태 불명 (즉시 확인 필요)

**현상**: KR 2026-04-02, US 2026-04-10 이후 데이터 적재 없음. 오늘은 2026-04-24.

**영향**: Phase 1은 일일 배치 기반(ADR-004). cron이 정상화되지 않으면 Phase 1 LLM 분석도 작동 불가.

**확인 필요**: 고의 중단인지, 오류인지, PC 가동 상태인지. 재가동 시 수동 catch-up 필요 여부.

### D. `watchlist_items` vs `minervini_list_selection` (Phase 6 예정)

전자는 legacy(미사용), 후자가 현역. Phase 6에서 `order_reservations` 설계 시 `watchlist_items` 제거 검토.

---

## 환경 / 설정 상태

- **개발 PC**: 사용자 로컬 PC, 24시간 가동 가능
- **DB**: 로컬 MySQL (Docker Compose, Phase 0에서 셋업됨)
- **외부 접속**: 미설정 (Phase 3에서 Cloudflare Tunnel 또는 Tailscale 도입 예정)
- **Anthropic API 키**: Phase 1 시작 시 발급/등록 필요
- **배치 스케줄러**: cron (Linux/macOS) + Windows Task Scheduler (Phase 0에서 구성됨, 현재 상태 확인 필요 — §미해결 이슈 C)
- **Alembic**: Phase 0 당시 체계는 있었으나 프로덕션 DB 추적 안 됨. P0.5에서 `20260424_000001`로 stamp 완료.

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

**실무 참조**:
- 빌드/실행/테스트: `CLAUDE.md`, `README.md`
- 코드베이스 탐색: `apps/ingest-databatcher/`, `apps/trading-view-project/`

---

*마지막 업데이트: 2026-04-24 (P0.5 완료, Phase 1 brief 작성 대기)*