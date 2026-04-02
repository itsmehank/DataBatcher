# DataBatcher

KR/US/Crypto 데이터 배치 수집기와 보조 웹앱들을 함께 관리하는 모노레포입니다.

## 무엇을 하는 프로젝트인가
- KR 주식/ETF, US 주식/ETF, KR/US 지수, Crypto(Binance Spot) 데이터 수집
- 일봉/주봉 가격 적재 + 지표 계산(SMA 등)
- RS/Minervini 관련 후처리 스크립트 지원
- `apps/ingest-databatcher/scripts/` 단위 실행과 `apps/ingest-databatcher/ops/shell/` 통합 실행 래퍼 제공

## 프로젝트 구조
- `apps/`: 앱 단위 디렉토리 (`ingest-databatcher`, `trading-view-project`, `my-insight-archieve`, `real-estate-project`)
- `apps/ingest-databatcher/scripts/`: 시장별 수집/업데이트/초기화 엔트리포인트
- `apps/ingest-databatcher/ops/shell/`: bulk/daily/weekly 통합 실행 스크립트
- `apps/ingest-databatcher/core/`, `apps/ingest-databatcher/collectors/`, `apps/ingest-databatcher/indicators/`, `apps/ingest-databatcher/savers/`: 핵심 로직
- `apps/ingest-databatcher/config/`: 런타임 설정(`settings.yaml`, `settings.dev.yaml`)
- `apps/real-estate-project/`: 부동산 실거래 수집/분석/Flask 웹 시각화 앱
- `db/`: 공통 DB 자산(Compose/Init/Migrations)
- `apps/ingest-databatcher/tests/`: 테스트 코드 및 테스트 DB 가이드

## 빠른 시작
### 1) 의존성 설치
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) 로컬 DB 실행(Docker)
```bash
cp .env.example .env
# .env에서 값 수정 (MYSQL_* / DATABASE_URL / REAL_ESTATE_*)
docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml up -d
```

`db/compose/mysql-standalone/docker-compose-mysql.yaml`은 **루트 `.env`만** 사용해 공용 MySQL 인스턴스와 기본 DB bootstrap을 구성합니다.
여기에는 `MYSQL_DATABASE` 계열과 `REAL_ESTATE_*` 계열이 함께 들어가며, 앱 런타임용 개별 `.env`는 각 앱 디렉토리에서 별도로 관리합니다.

MySQL 월간 백업/복구는 `apps/ingest-databatcher/ops/shell/db_backup_monthly.sh`, `apps/ingest-databatcher/ops/shell/db_restore_full.sh`를 사용하세요.
이 스크립트는 공용 주 DB와 `real_estate` DB를 함께 다룹니다.

### 3) 스키마 초기화
```bash
python apps/ingest-databatcher/scripts/init_db.py
```

## DB 연결 설정 (중요)
이 저장소는 DB 관련 환경 파일을 두 층으로 나눕니다.

- 루트 `.env`: 공용 MySQL bootstrap, 기본 `DATABASE_URL`, real-estate DB/user 생성 정보
- 앱별 `.env`: 각 앱의 실제 런타임 접속 정보와 앱 전용 시크릿

`apps/ingest-databatcher`는 실행 시점에 어떤 DB로 적재할지 다음 우선순위로 결정합니다.

1. `DATABASE_URL` 환경변수 (최우선)
2. `apps/ingest-databatcher/config/settings.dev.yaml`의 `database.url`
3. `apps/ingest-databatcher/config/settings.yaml`의 `database.url`

즉, **bulk/daily/weekly 모두 현재 프로세스의 `DATABASE_URL` 값이 적재 대상 DB를 결정**합니다.

### 권장 방식: `.env`에 `DATABASE_URL` 설정
`.env.example`을 복사해 `.env`를 만들고 값을 채웁니다.

```env
MYSQL_ROOT_PASSWORD=YOUR_ROOT_PASSWORD
MYSQL_DATABASE=trade
MYSQL_USER=YOUR_DB_USER
MYSQL_PASSWORD=YOUR_DB_PASSWORD
MYSQL_PORT=3306
REAL_ESTATE_DB_NAME=real_estate
REAL_ESTATE_TEST_DB_NAME=real_estate_test
REAL_ESTATE_DB_USER=YOUR_RE_DB_USER
REAL_ESTATE_DB_PASSWORD=YOUR_RE_DB_PASSWORD

DATABASE_URL=mysql+pymysql://YOUR_DB_USER:YOUR_DB_PASSWORD@127.0.0.1:3306/trade?charset=utf8mb4
```

- `username`: `YOUR_DB_USER` 위치
- `password`: `YOUR_DB_PASSWORD` 위치
- `url` 전체 형식: `mysql+pymysql://<user>:<password>@<host>:<port>/<db>?charset=utf8mb4`

### 대안 방식: `apps/ingest-databatcher/config/settings.dev.yaml` 사용
실행 환경에서 환경변수 주입이 어렵다면 다음 키를 사용합니다.

```yaml
database:
  url: mysql+pymysql://YOUR_DB_USER:YOUR_DB_PASSWORD@127.0.0.1:3306/trade?charset=utf8mb4
```

> 보안 권장: 실제 비밀번호 하드코딩 대신 `.env` + `DATABASE_URL` 사용을 권장합니다.

### DB 타겟 전환 예시
- 운영 DB로 실행:
  ```bash
  export DATABASE_URL="mysql+pymysql://user:pass@127.0.0.1:3306/trade?charset=utf8mb4"
  bash apps/ingest-databatcher/ops/shell/daily_all.sh
  ```
- 테스트 DB로 실행:
  ```bash
  export DATABASE_URL="mysql+pymysql://user:pass@127.0.0.1:3306/trade_test?charset=utf8mb4"
  bash apps/ingest-databatcher/ops/shell/daily_all.sh
  ```

`apps/real-estate-project`는 루트 `DATABASE_URL` 대신 앱 내부 `.env`의 `RE_DB_*`를 사용합니다.

## 실행 가이드
### Bulk (초기 대량 적재)
```bash
bash apps/ingest-databatcher/ops/shell/bulk_all.sh
```
- 전체 시장을 순차 실행
- 재실행 안전성 확보를 위해 insert-only 정책 사용

경량 점검용:
```bash
bash apps/ingest-databatcher/ops/shell/bulk_all_test.sh
```

### Daily (일일 증분)
```bash
bash apps/ingest-databatcher/ops/shell/daily_all.sh
```
- 내부적으로 KR/US/Crypto 일일 업데이트를 순서대로 수행

### Weekly (주간 증분)
```bash
bash apps/ingest-databatcher/ops/shell/weekly_all.sh
```
- 종목 마스터 동기화 + 지수/주식/Crypto 주봉 업데이트 수행

## 테스트
전체 pytest:
```bash
pytest -q apps/ingest-databatcher/tests apps/ingest-databatcher/scripts/tests
```

단일 테스트 예시:
```bash
pytest -q apps/ingest-databatcher/tests/test_pykrx_adapter.py::test_normalize_price_columns_basic
```

테스트 DB 가이드:
- `apps/ingest-databatcher/tests/README_TEST_DB.md`

## GitHub 업로드 전 보안 체크
민감정보가 실수로 올라가지 않도록 아래 순서를 권장합니다.

```bash
python apps/ingest-databatcher/scripts/preflight_repo_safety.py
git add -n .
git check-ignore -v .env apps/ingest-databatcher/config/settings.dev.yaml logs/bulk_update_failed.log
```

추가 원칙:
- `.env`, 개인 키, 로컬 자격증명 파일은 커밋 금지
- 공개 문서에는 반드시 플레이스홀더(`YOUR_DB_PASSWORD` 등) 사용

## 상세 문서
- `apps/ingest-databatcher/docs/guides/전체_Bulk_수집_가이드.md`
- `apps/ingest-databatcher/docs/guides/전체_Daily_Weekly_업데이트_가이드.md`
- `apps/ingest-databatcher/docs/guides/DB_데이터_가이드.md`
- `apps/ingest-databatcher/docs/windows_scheduler_guide.md`
- `apps/ingest-databatcher/docs/operations_validation_manual.md`
- `apps/ingest-databatcher/docs/database_schema.md`
