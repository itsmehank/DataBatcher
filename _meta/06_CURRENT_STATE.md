# 현재 진행 상황

> 이 문서는 프로젝트의 현재 상태를 한 페이지로 요약한다.  
> **새 AI 세션을 시작할 때 가장 먼저 읽는 문서**다.  
> Phase 종료 시, 또는 큰 변경 시 갱신한다. 가능한 한 짧게 유지한다.

---

## 현재 위치

**완료된 Phase**: Phase 0 + P0 정합성 검토 (governance setup)

**진행 중인 Phase**: 없음 (Phase 1 brief 작성 대기)

**다음 시작할 Phase**: **Phase 1 — LLM 분석 레이어 구축**

**Phase 1 시작 조건**:
1. 사용자가 Architect 세션에서 `_meta/phases/phase1_brief.md` 작성 요청
2. brief 확정 후, ADR-009의 스키마 변경(스크리너 개편 + `daily_analysis_*` + `llm_calls` 생성) 실행
3. 그 후 Builder(Claude Code CLI) 세션에서 본 구현 시작

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
- 현재는 통과 종목만 저장, `conditions_met` 필드 없음
- **Phase 1 착수 전에 개편 예정** (ADR-009)

**시각화 백엔드 + 프론트엔드** (계층 3 (4) 일부)
- FastAPI 백엔드 (auth/rate_limit/region 라우팅 포함)
- React + TypeScript + Vite 프론트엔드
- Dashboard, ChartView, ListView, Login 페이지
- `minervini_list_selection` 테이블 + API로 focus/action/pass 선택 상태 관리
- region (KR/US) × market × list_category 조회 지원

**데이터**
- 로컬 MySQL (Docker Compose)
- 배치 주기: 일간(daily_*_update.sh) + 주간(weekly_*_update.sh)
- Cron/Windows Task Scheduler로 자동화 구성됨

---

## P0 정합성 검토에서 결정된 것 (2026-04-24)

`project_snapshot_phase0.md`와 `_meta/` 설계 문서 간 차이를 검토하여 다음을 확정:

1. **기존 DB/테이블 구조 유지 원칙**: 없는 필드만 추가, 새 테이블만 생성. 기존 ETL·백엔드·프론트에 영향 최소화.
2. **`daily_analysis`는 시장별 분리** (`daily_analysis_kr`, `daily_analysis_us`, PK `(symbol, date)`) → ADR-009
3. **스크리너 개편을 Phase 1 전에 수행** (옵션 C): `conditions_met` JSON 컬럼 추가 + 8조건 완전 구현 + 통과 종목만 저장 정책 유지 → ADR-009
4. **`llm_calls` 테이블 신설** (헌법 §2.5) → ADR-009
5. **ADR-006/007/008 소급 기록**: Phase 0에서 내려진 결정(long-form 인디케이터, 시장별 분리, screen_config_hash)을 문서화

상세 검토는 `_meta/phases/phase0_alignment_review.md` 참조.

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
- ADR-009: `daily_analysis` 시장별 분리 + 스크리너 `conditions_met` 추가 + `llm_calls` 신설

전체 ADR은 `04_DECISIONS.md` 참조.

---

## Phase 1 시작 전 해야 할 일 (체크리스트)

### 이미 완료된 것
- [x] `_meta/` 거버넌스 문서 셋 구성 (00~06 + phases/phase0_alignment_review.md)
- [x] 루트 `CLAUDE.md`에 `_meta/` 우선 읽기 지침 추가
- [x] 루트 `README.md`에 프로젝트 거버넌스 섹션 추가
- [x] 설계 결정 확정 (ADR-006 ~ ADR-009)

### Phase 1 brief 작성 시 확인 필요
- [ ] LLM 분석 모듈이 사용할 입력 범위 확정 (일봉만? 주봉도? 인디케이터 범위는?)
  - 결정: **주봉 포함**
- [ ] 52주 고가/저가, volume_ma20을 인디케이터로 영구화할지, 호출 시 즉석 계산할지
- [ ] (5) `analyze_chart`의 JSON 출력 스키마 프롬프트 초안
- [ ] (6) `calculate_entry_params`의 JSON 출력 스키마 프롬프트 초안
- [ ] 새 앱 디렉토리 구조 (`apps/llm-analysis/` 또는 유사)

### Phase 1 brief 확정 후 (본 구현 시작 전)
- [ ] DB 마이그레이션 SQL 파일 생성 (`db/migrations/YYYYMMDD_phase1_schema.sql` 또는 ad-hoc migration 파일)
  - `conditions_met` 컬럼 추가 (KR/US)
  - `daily_analysis_kr`, `daily_analysis_us`, `llm_calls` 생성
- [ ] `indicators/minervini/trend_template.py` 리팩토링 (8조건 완전 구현)
- [ ] `kr_minervini_update.py`, `us_minervini_update.py` 수정 (`conditions_met` 저장)
- [ ] 기존 데이터 재백필 (이전 설정으로 돌려 `conditions_met` 채우기) 또는 당일부터 적용할지 결정

---

## 미해결 이슈 / 주의 사항

- **52주 고가/저가·volume_ma20 영구화 여부**: 현재 스크리너 내부 즉석 계산. Phase 1 LLM 분석이 이 값을 입력으로 쓰는 방식을 결정하며 함께 정리.
- **`watchlist_items` vs `minervini_list_selection`**: 전자는 legacy(미사용), 후자가 현역. Phase 6에서 `order_reservations` 설계 시 `watchlist_items` 제거 검토.
- **ADR-009 마이그레이션 실행 타이밍**: Phase 1 brief 확정 직후, 본 구현 시작 전. Builder 세션 첫 작업으로 수행.

---

## 환경 / 설정 상태

- **개발 PC**: 사용자 로컬 PC, 24시간 가동 가능
- **DB**: 로컬 MySQL (Docker Compose, Phase 0에서 셋업됨)
- **외부 접속**: 미설정 (Phase 3에서 Cloudflare Tunnel 또는 Tailscale 도입 예정)
- **Anthropic API 키**: Phase 1 시작 시 발급/등록 필요
- **배치 스케줄러**: cron (Linux/macOS) + Windows Task Scheduler (Phase 0에서 구성됨)

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

**실무 참조**:
- 빌드/실행/테스트: `CLAUDE.md`, `README.md`
- 코드베이스 탐색: `apps/ingest-databatcher/`, `apps/trading-view-project/`

---

*마지막 업데이트: 2026-04-24 (P0 정합성 검토 완료, Phase 1 brief 작성 대기)*