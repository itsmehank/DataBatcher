# 시스템 아키텍처

> 이 문서는 시스템의 구조를 정의한다.  
> 헌법(00_CONSTITUTION.md)의 설계 원칙을 구체화한 것이다.  
> 큰 변경이 있을 때만 수정하며, 변경 시 의사결정 로그(04_DECISIONS.md)에 사유를 남긴다.

---

## 1. 아키텍처 개요

본 시스템은 **4개의 계층**으로 구성된다. 데이터는 위에서 아래로 흐르며, 각 계층은 명확한 책임을 가진다.

```
┌─────────────────────────────────────────────────────────────┐
│  외부 데이터 소스                                              │
│  pykrx · FDR · yfinance · Binance · 증권사 API · 사용자         │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  계층 1 · 결정론적 코어 (LLM 호출 없음)                          │
│  (1) 일봉·주봉 적재  (2) 인디케이터  (3) 템플릿 필터               │
│  (9) 자동 주문 엔진  (10) 포트폴리오 업데이트                     │
│  (12) 매매 통계                                               │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  계층 2 · LLM 분석 (단발 호출, 구조화 출력)                       │
│  (5) 차트 분석·분류    (6) 진입 파라미터 산출                     │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  계층 3 · 자동화 파이프라인                                      │
│  (7) 엑셀 + 메일    (4) 백엔드 API + 프론트엔드 대시보드           │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  계층 4 · 에이전트 (대화형, 도구 사용)                            │
│  (8) Q&A 에이전트    (11) 포트폴리오 매니저 에이전트                │
└─────────────────────────────────────────────────────────────┘

  ※ LLM/에이전트 → 자동 주문 사이에는 반드시 사용자 승인 게이트가 존재
```

## 2. 계층별 상세

### 계층 1: 결정론적 코어

**책임**: 데이터의 수집·가공·저장, 규칙 기반 필터링, 주문 실행, 포트폴리오 상태 관리

**원칙**:
- LLM을 호출하지 않는다.
- 모든 동작이 결정론적이다(같은 입력 → 같은 출력).
- 가장 안쪽에서 시스템의 신뢰성을 책임진다.

**구성 요소**:

| ID  | 모듈명           | 입력                    | 출력 (논리명 / 실제 테이블)                  | 트리거           |
| --- | ---------------- | ----------------------- | ---------------------------------------- | ---------------- |
| (1) | 일봉·주봉 적재   | pykrx, FDR, Binance API | 논리: `daily_ohlcv` / 실제: `stock_prices`, `us_stock_prices`, `kr_index_prices`, `us_index_prices`, `crypto_prices_daily` + 각 `_weekly` | Cron, 장 마감 후 |
| (2) | 인디케이터 계산  | (1)의 가격 테이블         | 논리: `daily_indicators` / 실제: `stock_indicators`, `us_stock_indicators`, `kr_index_indicators`, `us_index_indicators`, `crypto_indicators_daily` + 각 `_weekly` (모두 long-form) | (1) 직후         |
| (3) | 템플릿 필터      | (2)의 인디케이터 + 뷰     | 논리: `template_pass` / 실제: `minervini_screen_results_kr`, `minervini_screen_results_us` | (2) 직후         |
| (9) | 자동 주문 엔진   | 예약 조건, 실시간 시세  | 증권사 API 호출 (Phase 6에서 구축)           | 장 시간 내 상시  |
| (10) | 포트폴리오 업데이트 | 체결 이벤트          | `portfolio` (Phase 6에서 구축)              | 체결 콜백        |
| (12) | 매매 통계        | `trade_history`         | `statistics` (Phase 8에서 구축)             | 일/주 단위 cron  |

**논리명 vs 실제 테이블**:  
초기 설계 단계에서는 `daily_ohlcv`·`daily_indicators`·`template_pass` 같은 단일 논리 테이블을 상정했으나, Phase 0 구현에서 시장별 분리(ADR-007)와 인디케이터 long-form(ADR-006)을 채택했다. 실제 테이블의 정확한 스키마는 `05_GLOSSARY.md` Part B.1 참조.

### 계층 2: LLM 분석 레이어

**책임**: 차트 패턴 인식, 진입 파라미터 산출

**원칙**:
- 단발 LLM 호출(에이전트가 아닌 함수)로 구현한다.
- temperature=0, 구조화 JSON 출력 강제.
- 모든 호출은 캐싱하고 영구 보존한다 (헌법 §2.5).

**구성 요소**:

| ID  | 모듈명           | 입력                                    | 출력 (JSON 스키마는 GLOSSARY.md 참조)        |
| --- | ---------------- | --------------------------------------- | -------------------------------------------- |
| (5) | 차트 분석·분류   | 일봉/주봉/인디케이터/거래량, `conditions_met` | `classification: entry/watch/ignore` + 근거 |
| (6) | 진입 파라미터    | (5)의 결과 + 차트                        | 진입가, 손절가, 제안 비중, 패턴 정보         |

**호출 패턴** (Phase 1에서 구축):
- (3)의 결과(`minervini_screen_results_*`의 최신 통과 종목)에 대해서만 (5)를 호출한다.
- (5)에서 "entry" 판정된 종목에만 (6)을 호출한다.
- 일일 배치로 실행, 결과는 `daily_analysis_kr` / `daily_analysis_us` 테이블에 저장 (ADR-009).
- 모든 LLM 호출은 `llm_calls` 테이블에 기록 (헌법 §2.5).

### 계층 3: 자동화 파이프라인

**책임**: 분석 결과의 사용자 전달, 시각화 인터페이스 제공

**원칙**:
- 결정론적 코드로만 구현한다.
- 하위 계층(1, 2)의 데이터를 읽기만 하며, 직접 변경하지 않는다.

**구성 요소**:

| ID  | 모듈명         | 입력                              | 출력                        | 상태 |
| --- | -------------- | --------------------------------- | --------------------------- | ---- |
| (7) | 엑셀 + 메일    | `daily_analysis_*`, `minervini_screen_results_*` | 엑셀 파일, SMTP 발송         | Phase 2에서 구축 |
| (4) | 백엔드 API     | DB 전체                           | REST API (조회 전용)        | Phase 0에서 구축 완료 (Phase 3에서 확장) |
| (4) | 프론트엔드 UI  | 백엔드 API                        | 웹 대시보드                  | Phase 0에서 구축 완료 (Phase 3에서 확장) |

**(4)의 Phase 0 완료 범위**:
- `apps/trading-view-project/` (FastAPI + React + TypeScript + Vite)
- region(KR/US) × market × list_category(focus/action/pass) 조회 지원
- 차트 뷰 (일봉/주봉 + SMA + RS Line)
- 인증(auth) · 레이트 리미팅(rate_limit) 구현 완료
- Phase 3에서 "AI 판단 카드", "질문하기 버튼", "진입 예약 버튼" 등을 추가 확장

### 계층 4: 에이전트 레이어

**책임**: 사용자와의 대화형 상호작용, 동적 도구 사용

**원칙**:
- 진짜 에이전트(도구 사용 + 동적 판단)로 구현한다.
- 모든 도구는 **읽기 전용**이다.
- 어떤 행동도 사용자 승인 게이트를 거쳐 계층 1로 전달된다.

**구성 요소**:

| ID   | 모듈명               | 도구 세트 (모두 읽기 전용)                                |
| ---- | -------------------- | --------------------------------------------------------- |
| (8)  | Q&A 에이전트         | 종목 데이터 조회, 분석 이력 조회, 유사 패턴 검색, 지표 조회 |
| (11) | 포트폴리오 매니저    | 포트폴리오 스냅샷, 섹터 익스포저, 거래 이력, 리스크 지표    |

## 3. 데이터 저장소

**선택**: MySQL (로컬, Docker Compose)

**테이블 그룹 구조** (Phase 0 실제 구현 기준):

```
[가격 데이터 그룹]       시장·타임프레임별 분리
  stock_prices            stock_prices_weekly
  us_stock_prices         us_stock_prices_weekly
  kr_index_prices         kr_index_prices_weekly
  us_index_prices         us_index_prices_weekly
  crypto_prices_daily     crypto_prices_weekly

[인디케이터 그룹]        long-form, 시장·타임프레임별 분리
  stock_indicators        stock_indicators_weekly
  us_stock_indicators     us_stock_indicators_weekly
  kr_index_indicators     kr_index_indicators_weekly
  us_index_indicators     us_index_indicators_weekly
  crypto_indicators_daily crypto_indicators_weekly

  + wide-form 조회용 뷰:
  v_stock_price_with_ma, v_us_stock_price_with_ma,
  v_kr_index_price_with_ma, v_us_index_price_with_ma 등

[심볼 마스터 그룹]       시장별 분리
  symbol_master (KR 주식)
  us_symbol_master
  kr_index_master, us_index_master
  crypto_symbol_master

[스크리닝 결과 그룹]     screen_config_hash로 버전 관리
  minervini_screen_results_kr
  minervini_screen_results_us

[LLM 분석 그룹]          Phase 1에서 신설
  daily_analysis_kr
  daily_analysis_us
  llm_calls

[사용자 선택 그룹]
  minervini_list_selection (현역)
  watchlist_items          (legacy, 미사용)

[운영 / 로그]
  sync_log
  kr_sector_snapshot

[Phase 6 이후 도입 예정]
  portfolio, order_reservations, trade_history, statistics
```

각 테이블의 정확한 스키마는 `05_GLOSSARY.md` Part B.1에서 정의한다.

## 4. 사용자 승인 게이트

LLM/에이전트의 판단이 실제 매매로 이어지는 모든 경로에는 사용자 승인 게이트가 존재한다.

**게이트 1: 진입 승인**
- 위치: (6) 진입 파라미터 → (9) 자동 주문 엔진
- 형태: 대시보드 또는 모바일 앱의 "진입 예약" 버튼
- 사용자는 LLM 제안값(비중 등)을 수정할 수 있다.
- Phase 0 현재: `minervini_list_selection` 테이블이 이 게이트의 원형으로 기능 중 (list_type: focus/action/pass, trigger_price, stop_price). Phase 6에서 `order_reservations`와의 관계 정리 예정.

**게이트 2: 비중 조정 승인**
- 위치: (11) 포트폴리오 매니저 조언 → (9) 자동 주문 엔진
- 형태: 대시보드의 "조언 적용" 버튼

**게이트 3: 전략 룰 수정**
- 위치: (12) 통계 기반 제안 → (3) 템플릿 필터 파라미터
- 형태: 대시보드의 "전략 업데이트" 버튼

## 5. 외부 의존성

| 영역           | 선택                          | 사유 / 대안 |
| -------------- | ----------------------------- | ----------- |
| 시세 데이터    | pykrx (KR), FDR (US), yfinance (보조), Binance API (크립토) | 무료, 각 시장 커버 |
| 증권사 API     | 미정 (Phase 6 진입 시 결정)   | 한국투자증권 KIS, 키움 등 |
| LLM            | Anthropic API or Claude Code CLI (Phase 1 기본: CLI + Max 플랜, ADR-011) | API는 ADR-003 원칙. Phase 1은 비용 절감 목적의 조건부 예외로 CLI를 기본 백엔드로 채택 (ADR-011). API 백엔드도 추상화로 지원하며 약관 위반 징후 시 즉시 전환 가능 (ADR-012 §3.3). 2026-10-24 또는 사용자 판단 시 재검토. |
| DB             | MySQL (Docker)                | Phase 0에서 구축 완료 |
| 이메일         | SMTP (Gmail 앱 비밀번호)     | 무료, 신뢰성 |
| 외부 접속      | Cloudflare Tunnel 또는 Tailscale | 포트포워딩 불필요, 보안 (Phase 3에서 도입) |

## 6. 배포 환경

**대상 환경**: 개인 소유 로컬 PC 또는 저전력 미니PC, 24시간 가동

**가동 시간 요구사항**:
- 한국 시간 기준 09:00~15:30 (한국 장)
- 한국 시간 기준 22:30~05:00 (미국 장)
- 그 외 시간: 배치 작업, 분석, 대시보드 서비스만 동작

**현재 배치 스케줄링** (Phase 0 구축 완료):
- Linux/macOS: cron
- Windows: Task Scheduler (`ops/scheduler/windows/*.ps1`)
- 구체적인 crontab은 `CLAUDE.md`의 "Production Cron Schedule" 섹션 참조

**선택적 클라우드 사용**:
- 외부 접속이 필요한 부분(대시보드 외부 노출)은 Cloudflare Tunnel 또는 Tailscale로 처리 (Phase 3)
- LLM 호출은 Anthropic 클라우드 API 또는 Claude Code CLI 사용 (Phase 1 기본: CLI + Max 플랜, ADR-011)

---

*이 문서는 "무엇을 만들 것인가"를 정의한다. "어떻게 만들 것인가"는 ROADMAP.md와 각 Phase의 brief에서 정의한다.*