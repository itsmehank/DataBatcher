# Probes

간단한 라이브러리 응답/스키마 확인을 위한 개별 실행 스크립트 모음입니다.

## 1) FDR 주식 데이터 프로브
```
python scripts/probes/fdr_stock_probe.py --symbol 005930 --start 2020-01-01 --end 2020-12-31
```
- 출력: 컬럼 목록, 상위 5행, 레코드 수/기간, 결측치 통계
- 심볼 예시: 005930(삼성전자), 000660(SK하이닉스)

환경 준비:
- `pip install -r requirements.txt`
- (선택) `.env` 작성 후 `docker compose up -d`로 로컬 MySQL 실행 가능(프로브 자체는 DB 불필요)
