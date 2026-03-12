# DataBatcher

KR/US/Crypto 데이터를 배치로 수집하고 지표를 계산해 MySQL에 적재하는 프로젝트입니다.

## 무엇을 하는 프로젝트인가
- KR 주식/ETF, US 주식/ETF, KR/US 지수, Crypto(Binance Spot) 데이터 수집
- 일봉/주봉 가격 적재 + 지표 계산(SMA 등)
- RS/Minervini 관련 후처리 스크립트 지원
- `scripts/` 단위 실행과 `shell_scripts/` 통합 실행 래퍼 제공

## 프로젝트 구조
- `scripts/`: 시장별 수집/업데이트/초기화 엔트리포인트
- `shell_scripts/`: bulk/daily/weekly 통합 실행 스크립트
- `core/`, `collectors/`, `indicators/`, `savers/`: 핵심 로직
- `config/`: 런타임 설정(`settings.yaml`, `settings.dev.yaml`)
- `docker/`: 로컬 MySQL 구성
- `tests/`: 테스트 코드 및 테스트 DB 가이드

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
# .env에서 값 수정 (MYSQL_* / DATABASE_URL)
docker compose -f docker/docker-compose.yml up -d
```

### 3) 스키마 초기화
```bash
python scripts/init_db.py
```

## DB 연결 설정 (중요)
이 프로젝트는 실행 시점에 어떤 DB로 적재할지 다음 우선순위로 결정합니다.

1. `DATABASE_URL` 환경변수 (최우선)
2. `config/settings.dev.yaml`의 `database.url`
3. `config/settings.yaml`의 `database.url`

즉, **bulk/daily/weekly 모두 현재 프로세스의 `DATABASE_URL` 값이 적재 대상 DB를 결정**합니다.

### 권장 방식: `.env`에 `DATABASE_URL` 설정
`.env.example`을 복사해 `.env`를 만들고 값을 채웁니다.

```env
MYSQL_ROOT_PASSWORD=YOUR_ROOT_PASSWORD
MYSQL_DATABASE=market
MYSQL_USER=YOUR_DB_USER
MYSQL_PASSWORD=YOUR_DB_PASSWORD
MYSQL_PORT=3306

DATABASE_URL=mysql+pymysql://YOUR_DB_USER:YOUR_DB_PASSWORD@127.0.0.1:3306/market?charset=utf8mb4
```

- `username`: `YOUR_DB_USER` 위치
- `password`: `YOUR_DB_PASSWORD` 위치
- `url` 전체 형식: `mysql+pymysql://<user>:<password>@<host>:<port>/<db>?charset=utf8mb4`

### 대안 방식: `config/settings.dev.yaml` 사용
실행 환경에서 환경변수 주입이 어렵다면 다음 키를 사용합니다.

```yaml
database:
  url: mysql+pymysql://YOUR_DB_USER:YOUR_DB_PASSWORD@127.0.0.1:3306/market?charset=utf8mb4
```

> 보안 권장: 실제 비밀번호 하드코딩 대신 `.env` + `DATABASE_URL` 사용을 권장합니다.

### DB 타겟 전환 예시
- 운영 DB로 실행:
  ```bash
  export DATABASE_URL="mysql+pymysql://user:pass@127.0.0.1:3306/market?charset=utf8mb4"
  bash shell_scripts/daily_all.sh
  ```
- 테스트 DB로 실행:
  ```bash
  export DATABASE_URL="mysql+pymysql://user:pass@127.0.0.1:3306/trade_test?charset=utf8mb4"
  bash shell_scripts/daily_all.sh
  ```

## 실행 가이드
### Bulk (초기 대량 적재)
```bash
bash shell_scripts/bulk_all.sh
```
- 전체 시장을 순차 실행
- 재실행 안전성 확보를 위해 insert-only 정책 사용

경량 점검용:
```bash
bash shell_scripts/bulk_all_test.sh
```

### Daily (일일 증분)
```bash
bash shell_scripts/daily_all.sh
```
- 내부적으로 KR/US/Crypto 일일 업데이트를 순서대로 수행

### Weekly (주간 증분)
```bash
bash shell_scripts/weekly_all.sh
```
- 종목 마스터 동기화 + 지수/주식/Crypto 주봉 업데이트 수행

## 테스트
전체 pytest:
```bash
pytest -q tests scripts/tests
```

단일 테스트 예시:
```bash
pytest -q tests/test_pykrx_adapter.py::test_normalize_price_columns_basic
```

테스트 DB 가이드:
- `tests/README_TEST_DB.md`

## GitHub 업로드 전 보안 체크
민감정보가 실수로 올라가지 않도록 아래 순서를 권장합니다.

```bash
python scripts/preflight_repo_safety.py
git add -n .
git check-ignore -v .env config/settings.dev.yaml logs/bulk_update_failed.log
```

추가 원칙:
- `.env`, 개인 키, 로컬 자격증명 파일은 커밋 금지
- 공개 문서에는 반드시 플레이스홀더(`YOUR_DB_PASSWORD` 등) 사용

## 상세 문서
- `guides/전체_Bulk_수집_가이드.md`
- `guides/전체_Daily_Weekly_업데이트_가이드.md`
- `guides/DB_데이터_가이드.md`
- `docs/windows_scheduler_guide.md`
- `docs/operations_validation_manual.md`
- `docs/database_schema.md`
