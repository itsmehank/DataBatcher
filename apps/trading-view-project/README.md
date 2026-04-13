# Minervini Lightweight Charts 대시보드

Grafana 기반 Minervini 워크플로우를 React + Lightweight Charts + FastAPI 웹앱으로 대체한 로컬 대시보드 프로젝트입니다.

## 기술 스택

- 프론트엔드: React + Vite + TypeScript + lightweight-charts
- 백엔드: FastAPI + SQLAlchemy Core + PyMySQL
- 데이터베이스: MySQL (`trade` DB, `DATABASE_URL` 사용)

## 프로젝트 구조

```text
minervini-lwc-dashboard/
  backend/
    app/
  frontend/
    src/
  docs/
    API.md
    RUN_DEV.md
  run-dev.sh
```

## 사전 준비

- Python 3.11 이상
- Node.js 20 이상
- `trade` 데이터베이스에 접근 가능한 MySQL 인스턴스(예: Docker)

## 공용 MySQL bootstrap과 앱 runtime 설정

- 루트 `.env`: 공용 MySQL bootstrap 계약. 기본 DataBatcher/trading-view DB 이름은 `trade`다.
- `apps/trading-view-project/backend/.env`: trading-view runtime 연결 정보. `DATABASE_URL`은 실제로 사용할 DB를 가리킨다.
- 공용 bootstrap을 사용할 때는 보통 루트 `.env`에서 만든 `trade` DB와 앱 `DATABASE_URL`의 DB 이름을 같게 맞춘다.

## 실행 전 설정 파일 가이드

실행 전 확인할 파일은 아래 두 개다.

- `apps/trading-view-project/backend/.env`
- `apps/trading-view-project/frontend/.env` (선택: export CSV 기간 조정용)

준비 방법:

```bash
cp apps/trading-view-project/backend/.env.example apps/trading-view-project/backend/.env
cp apps/trading-view-project/frontend/.env.example apps/trading-view-project/frontend/.env
```

필수 값:

- `DATABASE_URL`: trading-view가 접속할 MySQL URL
- `ALLOWED_ORIGINS`: 프론트엔드 Origin (로컬 기본값 `http://localhost:5173`)

상황별 추가 값:

- `SECRET_KEY`: 로그인/권한 기능을 사용할 때 필수
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`: startup 시 editor 계정 bootstrap이 필요할 때 둘 다 설정
- `STARTUP_DB_CHECK`: 시작 시 DB readiness 확인 여부
- `BACKEND_PORT`, `FRONTEND_PORT`: 포트 충돌 시 조정

기본 예시:

```env
DATABASE_URL=mysql+pymysql://<db_user>:<db_password>@127.0.0.1:3306/trade?charset=utf8mb4
ALLOWED_ORIGINS=http://localhost:5173
STARTUP_DB_CHECK=true
SECRET_KEY=CHANGE_ME_RANDOM_SECRET_AT_LEAST_32_CHARS
```

## 빠른 시작 (백엔드 + 프론트 동시 실행)

모노레포 루트(`DataBatcher`)에서:

```bash
chmod +x apps/trading-view-project/run-dev.sh
./apps/trading-view-project/run-dev.sh
```

기본 주소:

- 백엔드 API: `http://localhost:8000`
- 프론트엔드 UI: `http://localhost:5173`
- FastAPI Swagger: `http://localhost:8000/docs`

## 수동 실행 방법

### 1) 백엔드 실행

```bash
cd apps/trading-view-project/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

`apps/trading-view-project/backend/.env`에서 `DATABASE_URL`을 실제 환경에 맞게 설정하세요.
모노레포 공용 bootstrap을 함께 쓰는 경우, 이 값은 일반적으로 루트 `.env`가 준비한 `trade` DB를 가리켜야 합니다.

백엔드 테스트 실행:

```bash
cd apps/trading-view-project/backend
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

### 1.5) 인증 설정 (선택)

인증 기능을 사용하려면:

```bash
# 1. users 테이블 생성 (DB에 직접 실행하거나 init 스크립트 사용)
mysql -u root -p < db/init/02_auth_schema.sql

# 2. .env에 SECRET_KEY 설정
echo 'SECRET_KEY=your-random-secret-key-at-least-32-chars' >> apps/trading-view-project/backend/.env

# 3. 관리자 bootstrap 설정(권장)
cat <<'EOF' >> apps/trading-view-project/backend/.env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=yourpassword
EOF
```

`STARTUP_DB_CHECK=true`일 때 백엔드 startup이 `ADMIN_USERNAME` / `ADMIN_PASSWORD`를 읽어 `users` 테이블의 editor 계정을 생성 또는 필요한 경우 갱신합니다.

둘 중 하나만 설정하면 bootstrap은 실행되지 않고 warning만 남깁니다.

자동 bootstrap을 쓰지 않거나 수동 복구가 필요하면 기존 CLI도 계속 사용할 수 있습니다.

```bash
cd apps/trading-view-project/backend
source .venv/bin/activate
python -m scripts.create_user --username admin --password yourpassword --role editor
```

인증 미설정 시에도 모든 읽기 API는 정상 동작합니다. 쓰기 API만 401을 반환합니다.

### 2) 프론트엔드 실행

```bash
cd apps/trading-view-project/frontend
npm install
npm run dev
```

프론트엔드 선택 설정 파일:

```bash
cd apps/trading-view-project/frontend
cp .env.example .env
```

지원 값:

- `VITE_EXPORT_DAILY_DAYS`: daily CSV에 포함할 최근 거래일 수 (기본 `90`)
- `VITE_EXPORT_WEEKLY_WEEKS`: weekly CSV에 포함할 최근 주 수 (기본 `52`)
- `VITE_EXPORT_RS_DAYS`: RS CSV에 포함할 최근 거래일 수 (기본 `90`)

예시:

```env
VITE_EXPORT_DAILY_DAYS=120
VITE_EXPORT_WEEKLY_WEEKS=78
VITE_EXPORT_RS_DAYS=120
```

프론트엔드는 `http://localhost:5173`에서 실행되며 `/api` 요청을 백엔드(`http://localhost:8000`)로 프록시합니다.

프론트엔드 검증 실행:

```bash
cd frontend
npm run test
npm run typecheck
npm run build
```

## 환경 변수

### Frontend (`frontend/.env`)

- `VITE_EXPORT_DAILY_DAYS`: ZIP/Files export의 daily CSV 기간
- `VITE_EXPORT_WEEKLY_WEEKS`: ZIP/Files export의 weekly CSV 기간
- `VITE_EXPORT_RS_DAYS`: ZIP/Files export의 RS CSV 기간

`backend/.env.example` 기준:

- `DATABASE_URL`: MySQL 연결 문자열  
  예) `mysql+pymysql://<db_user>:<db_password>@127.0.0.1:3306/trade?charset=utf8mb4`
  (Docker 백엔드 컨테이너에서 호스트 MySQL에 접속할 때는 `127.0.0.1` 대신 `host.docker.internal` 사용)
- `ALLOWED_ORIGINS`: CORS 허용 Origin(쉼표로 여러 개 지정 가능)  
  예) `http://localhost:5173`
- `STARTUP_DB_CHECK`: 서버 시작 시 DB 연결 체크 수행 여부 (`true`/`false`, 기본 `true`)
- `SECRET_KEY`: JWT 서명 키(인증 사용 시 필수)
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`: startup 시 `users` 테이블의 editor 계정을 bootstrap할 때 사용하는 값(둘 다 설정해야 동작)

## DB 사전 준비 (권한/객체 점검)

앱은 `STARTUP_DB_CHECK=true`일 때 DB 연결 실패 시 서버 시작 단계에서 실패하도록 동작합니다.
아래 SQL을 사전에 수행해 앱 계정 권한과 필수 객체를 점검하세요.

### 1) 앱 계정 생성 및 권한 부여

```sql
CREATE USER IF NOT EXISTS 'dashboard_app'@'%' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';

GRANT SELECT ON trade.us_symbol_master TO 'dashboard_app'@'%';
GRANT SELECT ON trade.symbol_master TO 'dashboard_app'@'%';
GRANT SELECT ON trade.minervini_screen_results_us TO 'dashboard_app'@'%';
GRANT SELECT ON trade.minervini_screen_results_kr TO 'dashboard_app'@'%';
GRANT SELECT ON trade.us_stock_prices TO 'dashboard_app'@'%';
GRANT SELECT ON trade.stock_prices TO 'dashboard_app'@'%';
GRANT SELECT ON trade.us_index_prices TO 'dashboard_app'@'%';
GRANT SELECT ON trade.kr_index_prices TO 'dashboard_app'@'%';
GRANT SELECT ON trade.v_us_stock_price_with_ma TO 'dashboard_app'@'%';
GRANT SELECT ON trade.v_us_stock_price_weekly_with_ma TO 'dashboard_app'@'%';
GRANT SELECT ON trade.v_stock_price_with_ma TO 'dashboard_app'@'%';
GRANT SELECT ON trade.v_stock_price_weekly_with_ma TO 'dashboard_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON trade.minervini_list_selection TO 'dashboard_app'@'%';

FLUSH PRIVILEGES;
```

### 2) 권한 확인

```sql
SHOW GRANTS FOR 'dashboard_app'@'%';
```

### 3) 필수 객체 존재 확인

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'trade'
  AND table_name IN (
    'us_symbol_master',
    'symbol_master',
    'minervini_screen_results_us',
    'minervini_screen_results_kr',
    'us_stock_prices',
    'stock_prices',
    'us_index_prices',
    'kr_index_prices',
    'v_us_stock_price_with_ma',
    'v_us_stock_price_weekly_with_ma',
    'v_stock_price_with_ma',
    'v_stock_price_weekly_with_ma',
    'minervini_list_selection'
  )
ORDER BY table_name;
```

### 4) Docker 백엔드에서 외부 MySQL 접속 시 DATABASE_URL 예시

```env
DATABASE_URL=mysql+pymysql://dashboard_app:CHANGE_ME_STRONG_PASSWORD@host.docker.internal:3306/trade?charset=utf8mb4
STARTUP_DB_CHECK=true
```

루트 `.env`로 공용 MySQL bootstrap을 수행했다면, `MYSQL_DATABASE=trade`와 위 `DATABASE_URL`의 DB 이름 `trade`가 서로 일치해야 합니다.

## 구현된 MVP 범위

- US 우선 워크플로우(Region 스위치로 KR도 연동)
- Dashboard: Date / Market / List Type 필터 + Minervini 통과 종목 테이블
- Chart View: Region / Market / Category / Ticker 필터 + 종목명 표시
- List View: Region / Date / List Category 필터 + 선택 종목 하단 차트
- 일봉 캔들 + 거래량 + SMA(50/100/150/200)
- 주봉 캔들 + 거래량 + SMA(20/50/100/200) + EMA(21)
- 일봉 RS 라인 패널
- Dashboard URL 쿼리 동기화 (`region`, `date`, `market`, `listCategory`, `symbol`)

## 문서

- API 계약: `docs/API.md`
- 회귀 체크리스트: `docs/REGRESSION_CHECKLIST.md`
- 외부 DB 배포 가이드: `docs/DEPLOY_EXTERNAL_DB.md`
- 동시 실행 가이드: `docs/RUN_DEV.md`
- DB 스키마(모노레포): `apps/ingest-databatcher/docs/database_schema.md`
- DB 데이터 가이드(모노레포): `apps/ingest-databatcher/docs/guides/DB_데이터_가이드.md`

## 참고

- 이 앱은 기존 DB 뷰/테이블을 기반으로 동작합니다.
- 데이터 최신성 및 일부 지표의 결측치 처리 품질은 DB 데이터 상태에 의존합니다.

## Docker 실행 (모노레포 루트 기준)

```bash
cp apps/trading-view-project/backend/.env.example apps/trading-view-project/backend/.env
docker compose -f apps/trading-view-project/docker-compose.yml up --build -d
```

기본 주소:

- 백엔드 API: `http://localhost:8000`
- 프론트엔드 UI: `http://localhost:5173`

중지:

```bash
docker compose -f apps/trading-view-project/docker-compose.yml down
```

포트 충돌 시 `apps/trading-view-project/backend/.env`에서 아래 값을 조정하세요.

- `BACKEND_PORT`
- `FRONTEND_PORT`
