# [최종 설계서] 하이브리드 종목 마스터 및 섹터 정보 동기화

## 1. 수집 원칙: Anchor & Enrichment

각 시장의 특성에 맞춰 **진실의 원천(Source of Truth)**을 지정하고, 부가 정보(Sector)를 결합하는 구조를 확정합니다.

* **한국(KRX)**: `pykrx`를 **Anchor(진실의 원천)**로 삼아 종목 리스트를 확정하고, `FinanceDataReader(FDR)`를 **Enrichment(정보 보완)** 레이어로 활용합니다.
* **미국(US)**: `FDR`을 **Anchor**로 삼아 종목 리스트와 섹터 정보를 동시에 수집하되, `yfinance`를 보조 Enrichment 소스로 활용합니다.

---

## 2. 시장별 상세 공정

### 2.1 한국 시장 (KRX): 정합성 및 속도 최적화

가격 데이터 수집 대상인 종목이 단 하나도 누락되지 않도록 설계합니다.

1. **Anchor 확보**: `pykrx`의 배치 함수를 통해 전 종목 티커와 명칭을 확보합니다.
* **주식**: `get_market_cap` 또는 `get_market_ticker_list` 활용.
* **ETF**: `get_etf_ticker_list` 전용 함수를 통해 별도 식별.


2. **Enrichment 결합**: `FDR`의 `StockListing('KRX')` 데이터를 **Left Join** 합니다.
* `pykrx`에는 있으나 `FDR`에 없는 신규 종목은 섹터가 `NULL`로 처리되어도 가격 수집 대상에는 포함됩니다.


3. **유형 지정**: `pykrx` 수집 경로에 따라 `symbol_type`을 `STOCK` 또는 `ETF`로 명확히 지정합니다.

### 2.2 미국 시장 (US): 데이터 보존 및 정규화

기존의 유실되던 데이터를 복구하고 수집 안정성을 확보합니다.

1. **배치 수집**: `FDR`을 통해 NYSE, NASDAQ, ETF/US 데이터를 호출합니다.
2. **데이터 정규화**: `normalize_listing_df` 함수를 통해 가변적인 컬럼명을 시스템 표준(`symbol`, `name`, `sector`, `industry`)으로 변환합니다.
3. **유형 할당**: 수집 소스 명칭에 'ETF' 포함 여부에 따라 `symbol_type`을 분류합니다.

---

## 3. 운영 고도화를 위한 데이터 모델 (반영 사항)

단순 정보 저장을 넘어, 데이터의 신뢰도를 추적하기 위한 메타데이터 컬럼을 포함합니다.

| 추가 컬럼 | 설명 | 도입 목적 |
| --- | --- | --- |
| **symbol_type** | STOCK / ETF / ETN 등 | 자산군별 분석 및 수집 로직 분기 |
| **sector_source** | 'FDR' / 'YFINANCE' / 'MANUAL' | 데이터의 출처를 기록하여 신뢰도 관리 |
| **sector_updated_at** | 섹터 정보가 마지막으로 갱신된 시점 | 신규 상장주의 섹터 업데이트 추적 |

### 3.1 상장폐지(DELISTED) 판정 기준 확립

시점 불일치로 인한 오판을 막기 위해 각 시장의 **Anchor 소스**를 기준으로만 상태를 변경합니다.

* **한국**: `pykrx` 리스트에 존재하지 않을 경우 `DELISTED` 처리.
* **미국**: `FDR` 리스트에 존재하지 않을 경우 `DELISTED` 처리.

---

## 4. 향후 실행 주기 및 파이프라인 관리

* **가격 동기화 (Daily)**: 매일 장 마감 후 `pykrx`와 `FDR`을 통해 시세를 수집합니다.
* **마스터 동기화 (Weekly)**: 주 1회 본 계획서의 로직을 가동하여 신규 상장, 섹터 변경, 상장 폐지 내역을 DB에 반영합니다.
* **결측치 패치 (Monthly)**: 섹터 정보가 `NULL`이거나 `sector_source`가 오래된 종목을 대상으로 `yfinance` 정밀 수집을 수행합니다.
