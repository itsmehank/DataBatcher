# Probes

간단한 라이브러리 응답/스키마 확인을 위한 개별 실행 스크립트 모음입니다.

## 1) FDR 주식 데이터 프로브
```
python scripts/probes/fdr_stock_probe.py --symbol 005930 --start 2020-01-01 --end 2020-12-31
```
- 출력: 컬럼 목록, 상위 5행, 레코드 수/기간, 결측치 통계
- 심볼 예시: 005930(삼성전자), 000660(SK하이닉스)

## 2) yfinance US 주식 데이터 프로브
```
python scripts/probes/yfinance_us_stock_probe.py --symbol AAPL --start 2025-12-01 --end 2025-12-10
```
- 출력: 원본 컬럼, flatten 후 컬럼, 날짜 범위, 정규화 미리보기
- 심볼 예시: AAPL, SPY, BRK-B

## 3) yfinance US 지수 데이터 프로브
```
python scripts/probes/yfinance_us_index_probe.py --symbol US500 --start 2025-12-01 --end 2025-12-10
python scripts/probes/yfinance_us_index_probe.py --all-indices --start 2025-12-01 --end 2025-12-10
```
- 출력: 내부 심볼 -> yfinance ticker 매핑, 원본 컬럼, flatten 후 컬럼, 정규화 미리보기
- 지원 심볼: US500, DJI, IXIC

환경 준비:
- `pip install -r requirements.txt`
- (선택) `.env` 작성 후 `docker compose up -d`로 로컬 MySQL 실행 가능(프로브 자체는 DB 불필요)
