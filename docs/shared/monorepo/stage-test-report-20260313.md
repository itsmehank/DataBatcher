# 모노레포 전환 단계 테스트 보고서 (2026-03-13)

## 대상 단계

- 2단계(DB 도메인 분리 준비)
- 3단계(소규모 파이프라인 검증)

## 테스트 환경

- 테스트 DB: `DATABASE_URL=...:3307/trade`
- 기동 방식: `MYSQL_PORT=3307` 런타임 오버라이드
- 코드/설정 파일의 3307 고정 변경 없음

## 2단계 테스트 결과

- `apps/ingest-databatcher/scripts/init_db.py` 실행 성공
- Alembic baseline 적용 성공
  - revision: `20260313_000001`
  - `alembic_version` 테이블 생성 확인
- 스키마 테이블 수 확인: 42 (기존 41 + alembic_version 1)

## 3단계 소규모 테스트 결과

- KR 최소 파이프라인 성공
  - `sync_symbol_master.py`
  - `kr_index_sync_master.py`
  - `bulk_update.py --top 1 --workers 1 --start=end=1일`
  - `daily_update.py --top 1`
  - `weekly_update.py --top 1`
- DB 적재 검증
  - `stock_prices`: 19
  - `stock_indicators`: 8
  - `stock_prices_weekly`: 4
  - 최신 샘플: `(000020, 2026-03-13)`

## 종료 검증

- 테스트용 3307 컨테이너/볼륨/네트워크 제거 완료
- 기존 3306 MySQL(`grafana-with-db-mysql`) 정상 유지 확인

## 추가 검증 (2026-03-14)

- 코드 이관 후 신규 경로 실행 검증
  - `python apps/ingest-databatcher/scripts/init_db.py`
  - `python apps/ingest-databatcher/scripts/sync_symbol_master.py`
  - `python apps/ingest-databatcher/scripts/bulk_update.py --top 1 --workers 1 --start=end=1일`
  - `python apps/ingest-databatcher/scripts/daily_update.py --all --market KOSPI --top 1`
  - `python apps/ingest-databatcher/scripts/weekly_update.py --all --market KOSPI --top 1`
- DB 적재 재검증(3307)
  - `stock_prices`: 19
  - `stock_indicators`: 4
  - `stock_prices_weekly`: 5
  - 최신 샘플: `(000020, 2026-03-13)`
- Alembic env import 경로 보정 후 baseline 적용 정상 확인

## 추가 검증 (2026-03-14, 경로 고정 보완)

- config 탐색 로직 고정 후 테스트
  - `apps/ingest-databatcher/core/config_loader.py`의 다중 경로 후보 탐색 정상 동작
- schema 경로 정책 변경 테스트
  - `db/init/01_schema.sql` 기준으로 `init_db.py`/`init_test_db.py` 실행 성공
  - legacy fallback(`db/init/01_schema.sql`)은 호환용으로 유지
- compose 경로 통일 테스트
  - `db/compose/mysql-standalone/docker-compose-mysql.yaml`에서 `../db/init/01_schema.sql` 마운트 정상
  - `db/compose/mysql-standalone/docker-compose-mysql.yaml`에서 `../db/init` 마운트 정상
- 3307 통합 검증
  - `init_db -> init_test_db -> alembic -> sync -> bulk(top1,1일) -> daily(top1) -> weekly(top1)` 성공
  - row count: `stock_prices=19`, `stock_indicators=4`, `stock_prices_weekly=5`
  - 종료 후 `MYSQL_PORT=3307 ... down -v` 수행 및 3306 기존 DB 유지 확인
