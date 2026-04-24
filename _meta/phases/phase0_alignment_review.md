# Phase 0 정합성 검토 (Phase 1 착수 전)

> 작성일: 2026-04-24  
> 범위: `project_snapshot_phase0.md` ↔ `_meta/` 목표 설계 문서  
> 목적: Phase 1(LLM 분석 레이어) 착수 전 인터페이스 합의

---

## 요약 (TL;DR)

헌법의 **절대 원칙을 위배하는 구현은 없다**. 현재 코드는 계층 1(결정론적 코어)의 (1)(2)(3)과 계층 3의 (4) 일부를 충실히 구현했다. 다만 이름/구조가 목표 설계와 상당히 다르고, 이는 **거의 대부분 현재 구현이 더 합리적** — 실제 멀티마켓(KR/US/Crypto)·멀티타임프레임(daily/weekly)을 돌려보며 쌓인 결정들이기 때문이다.

사용자의 명시적 방향 (2026-04-24): **기존 DB/테이블 구조를 유지하고, 필요한 필드만 추가하거나 새 테이블을 생성한다**. 기존 ETL·백엔드·프론트에 영향을 최소화하는 것이 최우선.

이 방향에 따라 Phase 0과 `_meta/` 설계 사이의 차이를 정리하고, Phase 1 착수를 위한 해결 항목들을 ADR-006 ~ ADR-009로 확정했다.

---

## 1. 정합성 매핑

### 1.1 아키텍처 (1)(2)(3)(4) ↔ 현재 코드

| 목표 모듈 | 현재 구현 위치 | 정합성 |
|---|---|---|
| **(1) 일봉 적재** | `apps/ingest-databatcher/collectors/{kr_stock,kr_etf,kr_index,us_stock,us_index,crypto_binance}.py` + `core/price_loader.py`, `bulk_price_loader.py`, `pykrx_adapter.py`, `fdr_sector_loader.py` + `scripts/kr_daily_update.py` 류 + `ops/shell/*.sh`, `ops/scheduler/windows/*.ps1` | ✅ **상위 호환** — 설계가 상상한 것보다 훨씬 넓음. KR/US/Crypto 세 시장, Daily/Weekly 두 타임프레임 모두 커버. `sync_log`, `symbol_master`·`us_symbol_master` 관리, rate limiter, 재시도 로직까지 있음. |
| **(2) 인디케이터 계산** | `indicators/common/{sma,ema}.py`, `indicators/ibd/{rs_rating,rs_line,blue_dot}.py`, `indicators/pipeline.py`, `indicators/registry.py`, `savers/indicator_saver.py` | ✅ **상위 호환** — pipeline/registry 아키텍처로 인디케이터 플러그인화. IBD RS Rating은 3m/6m/9m/12m 가중 횡단면 백분위로 정확히 구현. Blue Dot까지 구현됨. 단 52주 고가/저가와 volume_ma20는 스크리너 내부에서 즉석 계산 (영구 저장 안 함). |
| **(3) 템플릿 필터** | `indicators/minervini/trend_template.py` + `scripts/kr_minervini_update.py`, `us_minervini_update.py` + config의 `minervini_kr`, `minervini_us` 섹션 | ⚠️ **구조는 대응, 개편 필요** — 8조건 중 6개 정도를 구현. 저장도 `template_pass` 대신 `minervini_screen_results_kr/us`로 시장 분리, 통과 조건 boolean 리스트(`conditions_met` JSON)는 저장 안 함. **ADR-009로 Phase 1 시작 전 개편 확정**. |
| **(4) 백엔드 API + 프론트엔드** | `trading-view-project/backend/` (FastAPI: routers `auth/chart/minervini/options`) + `trading-view-project/frontend/` (React+TS+Vite: Dashboard/ChartView/ListView/Login pages) | ✅ **충실히 구현됨** — 인증·레이트리밋까지 갖춘 실사용 가능 대시보드. GLOSSARY에는 (4)의 API 스펙이 없었는데, 현재 코드는 region(KR/US) × list_category(focus/action/pass/all) × minervini 결과 조회 API를 갖고 있음. |

### 1.2 DB 테이블 ↔ GLOSSARY 원안

| GLOSSARY 원안 | 현재 실제 테이블 | 관계 |
|---|---|---|
| `daily_ohlcv` (단일) | `stock_prices`, `us_stock_prices`, `kr_index_prices`, `us_index_prices`, `crypto_prices_daily` + 각 weekly | **구조 다름** — 시장별·타임프레임별로 분리 (ADR-007). PK는 모두 `(symbol, date)` 또는 `(symbol, week_start)` 패턴. 컬럼명 `ticker`→`symbol`. `adj_close`, `source`, `etl_loaded_at` 등 부가 필드 존재. |
| `daily_indicators` (wide) | `stock_indicators`, `us_stock_indicators`, `kr_index_indicators`, `us_index_indicators`, `crypto_indicators_daily` + 각 weekly (**all long-form**) | **구조 근본적으로 다름** (ADR-006) — 원안은 컬럼 고정 wide, 실제는 long-form. Wide 조회는 뷰(`v_*_price_with_ma`)가 제공. |
| `template_pass` | `minervini_screen_results_kr`, `minervini_screen_results_us` | **이름 다르고, 시장 분리, 추가 필드 보유** — `rs_rating`, `is_blue_dot`, `screen_config_hash`(ADR-008)까지 저장. `conditions_met` JSON은 현재 미구현, ADR-009로 추가 예정. |
| `daily_analysis` ⭐ | 미존재 | Phase 1에서 `daily_analysis_kr`, `daily_analysis_us` 두 개로 분리 생성 (ADR-009) |
| `portfolio` | 미존재 | Phase 6~7 |
| `order_reservations` | **부분 존재** — `minervini_list_selection`(region×date×market×symbol, focus/action/pass, trigger_price, stop_price)이 승인 게이트의 원형으로 사용 중 | Phase 6에서 통합·정리 예정 |
| `trade_history` | 미존재 | Phase 6 |
| `statistics` | 미존재 | Phase 8 |
| `llm_calls` | 미존재 | Phase 1에서 생성 (ADR-009) |
| (GLOSSARY 누락) | `symbol_master`, `us_symbol_master`, `crypto_symbol_master`, `kr_index_master`, `us_index_master`, `sync_log`, `kr_sector_snapshot`, `watchlist_items`, `minervini_list_selection`, auth 관련 테이블 | **설계 문서 누락** — 05_GLOSSARY.md 개정에 반영됨 |

### 1.3 추가 확인 결과 (2026-04-24)

사용자 확인으로 확정된 사실들:

1. **`minervini_screen_results_*.failed_reason`은 dead column**. 통과 종목만 INSERT하는 정책이므로 값이 들어가지 않음. 컬럼은 스키마에 남아있으나 실질 미사용.
2. **`watchlist_items`는 legacy, 미사용**. `minervini_list_selection`이 현역 (trading-view-project 전용).
3. **52주 고가/저가·volume_ma20는 영구 저장 안 함**. 스크리너가 호출 시마다 즉석 계산.
4. **Phase 1 LLM은 일봉 + 주봉 모두 입력으로 받아야 함**.

### 1.4 핵심 관찰

- **이름만 다르고 구조 동일**: 거의 없음. `ticker` vs `symbol`은 이름 차이지만 테이블 분할은 구조 차이.
- **구조 자체가 다른 것**: ① 인디케이터의 wide vs long-form, ② OHLCV 테이블의 통합 vs 시장별 분리, ③ template_pass의 통합 vs 시장별 분리 + 조건 저장 방식.
- **설계에 아예 없는 것**: 심볼 마스터, sync 로그, 섹터 스냅샷, 사용자 선택·워치리스트. 전부 실사용에 필수.

---

## 2. 차이점 분석 및 확정 결과

### A. 설계 문서가 잘못된 것 → GLOSSARY 수정으로 해결

| # | 차이점 | 해결 |
|---|---|---|
| **A-1** | 인디케이터 long-form 저장 | **ADR-006**으로 소급 기록. GLOSSARY Part B.1.2에 long-form 스키마 명시. |
| **A-2** | OHLCV 시장별 분리 | **ADR-007**로 소급 기록. GLOSSARY Part B.1.1에 5개 테이블 모두 명시. |
| **A-3** | 템플릿 통과 결과 시장별 분리 + 설정 해시 | **ADR-008**로 소급 기록. GLOSSARY Part B.1.5에 반영. |
| **A-4** | 컬럼명 `ticker` → `symbol` | GLOSSARY Part A "Symbol vs Ticker" 통일 규칙 추가. 모든 스키마 `symbol`로 통일. |
| **A-5** | `symbol_master`, `sync_log` 등 운영 필수 테이블 누락 | GLOSSARY Part B.1.3, B.1.4에 추가. |
| **A-6** | (4) 백엔드 API 스펙 누락 | Phase 3 확장 시 GLOSSARY에 추가 예정. 현재 구현은 CLAUDE.md·README.md로 참조 가능. |

### B. 현재 구현이 리팩토링 필요 → Phase 1 시작 전 해결

| # | 차이점 | 해결 |
|---|---|---|
| **B-1** | 미너비니 8조건 중 일부 누락 | **ADR-009**: 옵션 C 채택. `trend_template.py` 리팩토링으로 8조건 완전 구현 + `conditions_met` JSON 저장. |
| **B-2** | `minervini_screen_results_*`의 조건별 정보 부재 | **ADR-009**: `conditions_met JSON NULL` 컬럼 추가 (ALTER TABLE). 통과 종목만 저장하는 정책은 유지. |
| **B-3** | `llm_calls` 테이블 부재 | **ADR-009**: Phase 1 첫 작업으로 신설. 헌법 §2.5 절대 원칙 충족. |
| **B-4** | region/market 용어 혼용 | GLOSSARY Part A에 "Region vs Market" 구분 규칙 추가. region=KR/US, market=KOSPI/KOSDAQ/NYSE/NASDAQ/ETF로 통일. |

### C. 둘 다 괜찮음 → 한쪽으로 통일

| # | 차이점 | 결정 |
|---|---|---|
| **C-1** | `ticker` vs `symbol` | **`symbol`으로 통일** (현재 구현 유지). GLOSSARY Part A에 동의어 규칙 명시. |
| **C-2** | `daily_ohlcv` 같은 단일 개념 vs 시장별 분리 | **개념과 실체 구분**. ARCHITECTURE는 논리명, GLOSSARY는 실제 테이블 모두 나열. |
| **C-3** | `DECIMAL(15,4)` vs 실제 precision | **현재 precision 유지** — 주식 18,4 / 크립토 28,10. GLOSSARY에 명시. |
| **C-4** | (3) 출력 테이블명 `template_pass` vs `minervini_screen_results_*` | **현재 이름 유지**. `template_pass`는 논리 개념, 실제 이름은 더 명시적. |

### 헌법 위배 여부

**없음**. §2.1(LLM 주문 금지), §2.2(결정론 코어 분리), §2.5(LLM 로그)는 현재 구현이 모두 충족하거나 Phase 1에서 충족되도록 설계됨. §4.2(이해) 관점에서 약점이었던 "조건별 통과 설명"은 ADR-009로 해결.

---

## 3. Phase 1 착수 전 해결 항목 (우선순위와 현재 상태)

### P0: `_meta/` 거버넌스 셋업 (완료)
- [x] `_meta/00_CONSTITUTION.md` ~ `06_CURRENT_STATE.md` 배치
- [x] ADR-006 ~ ADR-009 문서화
- [x] `CLAUDE.md`, `README.md`에 `_meta/` 참조 추가
- [x] `_meta/phases/phase0_alignment_review.md` 작성 (이 문서)

### P1: Phase 1 brief 작성 (다음 단계)
- [ ] `_meta/phases/phase1_brief.md` 작성 (Architect 세션에서)
  - (5) `analyze_chart` 함수 설계 및 프롬프트 초안
  - (6) `calculate_entry_params` 함수 설계 및 프롬프트 초안
  - 입력 범위 확정 (일봉 + 주봉 + 어느 인디케이터까지?)
  - 52주 고가/저가·volume_ma20 처리 방식 결정 (즉석 계산 vs 영구화)
  - 새 앱 디렉토리 명명 및 구조
  - 배치 통합 방식 (기존 cron에 어떻게 끼워넣을지)

### P2: Builder 세션 첫 작업 (Phase 1 brief 확정 후)
- [ ] DB 마이그레이션 SQL 실행
  - `minervini_screen_results_kr/us`에 `conditions_met JSON` 컬럼 추가
  - `daily_analysis_kr`, `daily_analysis_us` 생성
  - `llm_calls` 생성
- [ ] 스크리너 리팩토링
  - `indicators/minervini/trend_template.py`: 8조건 완전 구현 + 조건별 매트릭스 반환
  - `kr_minervini_update.py`, `us_minervini_update.py`: `conditions_met` 저장
  - 백필 여부 결정 (소급 채우기 vs 당일부터만)

### P3: Phase 1 본 구현
- [ ] `apps/llm-analysis/` (또는 합의된 이름) 신설
- [ ] `analyze_chart()`, `calculate_entry_params()` 구현
- [ ] `llm_calls` 기록 래퍼
- [ ] 일일 배치 통합
- [ ] 결과 검토 (최소 일주일 누적)

---

## 4. 문서 업데이트 완료 내역

### `_meta/05_GLOSSARY.md`
- Part A: Symbol vs Ticker 규칙, Region vs Market 규칙, Screen Config Hash 용어 추가
- Part B.1: 실제 DB 스키마 전면 반영 (가격·인디케이터·심볼 마스터·스크리닝·LLM 분석·사용자 선택·운영 로그 그룹 구조)
- Part B.2: `conditions_met` JSON 스키마 확정 (8조건 키명)
- Part B.3: 모듈 함수 시그니처 `market` 파라미터 반영

### `_meta/04_DECISIONS.md`
- ADR-006 추가: 인디케이터 long-form 저장 (소급)
- ADR-007 추가: OHLCV·스크리닝 결과 시장별 분리 (소급)
- ADR-008 추가: `screen_config_hash`로 설정 버전 관리 (소급)
- ADR-009 추가: `daily_analysis` 시장별 분리 + 스크리너 개편 + `llm_calls` 신설
- ADR-005 갱신: SSoT = 로컬 Git, Builder 수정 가능 문서 범위 명시

### `_meta/06_CURRENT_STATE.md`
- Phase 0 실제 완료 범위 반영 (Crypto, Weekly, 대시보드 등)
- P0 정합성 검토 결과 요약
- Phase 1 시작 전 체크리스트
- 미해결 이슈 목록

### `_meta/01_ARCHITECTURE.md`
- 계층 1 구성 요소 표에 논리명과 실제 테이블명 병기
- (4)가 Phase 0에서 이미 구축 완료됨을 명시
- 데이터 저장소 섹션에 실제 테이블 그룹 구조 반영
- 외부 의존성에 pykrx/FDR/yfinance/Binance 실제 구성 명시

### `CLAUDE.md`, `README.md`
- 기존 내용 유지한 채 `_meta/` 거버넌스 참조 섹션 추가

---

## 5. 후속 Phase에서 다룰 항목

다음은 Phase 1 범위 밖이나, 향후 잊지 않도록 기록:

- **Phase 3 확장 시**: 백엔드 API 스펙을 GLOSSARY에 정식 기재
- **Phase 6 시작 시**: `watchlist_items`(legacy) 제거 여부 결정 + `minervini_list_selection`과 `order_reservations`의 관계 정의 (별도 ADR)
- **Phase 6 이후**: `failed_reason` 컬럼 활용 여부 재검토 (스크리너 정책을 "탈락 종목도 저장"으로 바꿀 가치가 있는지)
- **Phase 5 (백테스트) 시**: 52주 고가/저가·volume_ma20을 인디케이터로 영구화할지 재검토 (과거 시점 복원 편의성)

---

*이 리뷰는 Phase 1 착수 전의 정지점이며, 여기서 나온 P1/P2/P3 항목은 Phase 1 brief의 첫 번째 섹션이 되어야 한다.*