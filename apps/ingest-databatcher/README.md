# ingest-databatcher

KR/US/Crypto 시장 데이터를 수집하고, 지표를 계산해 MySQL(`trade`)에 적재하는 배치 애플리케이션입니다.

> 아래 명령은 별도 설명이 없으면 모노레포 루트(`DataBatcher/`)에서 실행하는 기준입니다.

## 주요 기능

- 한국/미국 주식 일봉/주봉 수집
- 한국/미국 지수 일봉/주봉 수집
- Crypto 일봉/주봉 수집
- SMA/EMA/RS/Minervini 관련 후처리 및 적재
- 초기 스키마 생성, 백업/복구, 배치 스케줄링 보조 스크립트 제공

## 프로젝트 구조

- `scripts/`: 수집/갱신/초기화/유틸 CLI 스크립트
- `core/`: 설정 로더, DB 매니저 등 공용 런타임 코드
- `collectors/`, `indicators/`, `savers/`: 수집/지표/저장 로직
- `config/`: `settings.yaml`, `settings.dev.yaml` 설정 파일
- `ops/shell/`: 일일/주간 배치, 백업/복구 스크립트
- `tests/`, `scripts/tests/`: pytest + 스크립트형 검증

## 실행 전 설정 파일 가이드

이 프로젝트는 두 가지 설정 경로를 지원합니다.

### 권장: 루트 `.env` 사용

모노레포 루트 `.env`에 `DATABASE_URL`을 두면 `core/config_loader.py`와 `scripts/init_db.py`가 이를 최우선으로 사용합니다.

준비 방법:

```bash
cp .env.example .env
```

필수 값:

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_DATABASE` (`trade` 권장)
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_PORT`
- `DATABASE_URL` 예: `mysql+pymysql://<user>:<password>@127.0.0.1:3306/trade?charset=utf8mb4`

공용 MySQL bootstrap까지 함께 사용할 경우:

```bash
docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml --env-file .env up -d
```

이때 `MYSQL_DATABASE`와 `DATABASE_URL`의 DB 이름은 같게 맞춰야 합니다.

### 대안: 앱 설정 파일 사용

환경변수 주입이 어렵다면 `apps/ingest-databatcher/config/settings.dev.yaml`에서 `database.url`을 지정할 수 있습니다.

예시:

```yaml
database:
  url: mysql+pymysql://YOUR_DB_USER:YOUR_DB_PASSWORD@127.0.0.1:3306/trade?charset=utf8mb4
```

우선순위는 다음과 같습니다.

1. `DATABASE_URL` 환경변수
2. `apps/ingest-databatcher/config/settings.dev.yaml`
3. `apps/ingest-databatcher/config/settings.yaml`

## 빠른 시작

### 1) 가상환경 및 의존성 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) DB 스키마 초기화

```bash
python apps/ingest-databatcher/scripts/init_db.py
```

이 스크립트는 `db/init/*.sql`을 순서대로 적용합니다.

### 3) 대표 실행 예시

```bash
python apps/ingest-databatcher/scripts/daily_update.py --all
python apps/ingest-databatcher/scripts/weekly_update.py --all
python apps/ingest-databatcher/scripts/us_daily_update.py --all --with-indicators
python apps/ingest-databatcher/scripts/crypto_daily_update.py --all --with-indicators
```

### 4) 배치 셸 스크립트 예시

```bash
bash apps/ingest-databatcher/ops/shell/daily_all.sh
bash apps/ingest-databatcher/ops/shell/weekly_all.sh
```

## 테스트 및 검증

빠른 pytest 실행:

```bash
pytest -q apps/ingest-databatcher/tests apps/ingest-databatcher/scripts/tests
```

단일 테스트 예시:

```bash
pytest -q apps/ingest-databatcher/tests/test_pykrx_adapter.py::test_normalize_price_columns_basic
```

문법 검증 예시:

```bash
python -m compileall apps/ingest-databatcher/core apps/ingest-databatcher/collectors apps/ingest-databatcher/indicators apps/ingest-databatcher/savers apps/ingest-databatcher/scripts apps/ingest-databatcher/tests
```

## 추가 문서

- 루트 `README.md`: 모노레포 공용 DB/bootstrap 가이드
- `apps/ingest-databatcher/docs/windows_scheduler_guide.md`: Windows 스케줄러 설정
- `apps/ingest-databatcher/docs/guides/`: 시장별 실행 가이드
