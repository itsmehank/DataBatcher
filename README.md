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

## 빠른 시작 (백엔드 + 프론트 동시 실행)

프로젝트 루트(`minervini-lwc-dashboard`)에서:

```bash
chmod +x run-dev.sh
./run-dev.sh
```

기본 주소:

- 백엔드 API: `http://localhost:8000`
- 프론트엔드 UI: `http://localhost:5173`
- FastAPI Swagger: `http://localhost:8000/docs`

## 수동 실행 방법

### 1) 백엔드 실행

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

`backend/.env`에서 `DATABASE_URL`을 실제 환경에 맞게 설정하세요.

백엔드 테스트 실행:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

### 2) 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
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

`backend/.env.example` 기준:

- `DATABASE_URL`: MySQL 연결 문자열  
  예) `mysql+pymysql://<db_user>:<db_password>@127.0.0.1:3306/<db_name>?charset=utf8mb4`
- `ALLOWED_ORIGINS`: CORS 허용 Origin(쉼표로 여러 개 지정 가능)  
  예) `http://localhost:5173`

## 구현된 MVP 범위

- US 우선 워크플로우(Region 스위치로 KR도 연동)
- Date / Market / Category / Ticker 필터링
- Minervini 통과 종목 테이블
- 일봉 캔들 + 거래량 + SMA(50/100/150/200)
- 주봉 캔들 + 거래량 + SMA(20/50/100/200) + EMA(21)
- 일봉 RS 라인 패널
- URL 쿼리 동기화 (`region`, `date`, `market`, `category`, `symbol`)

## 문서

- API 계약: `docs/API.md`
- 회귀 체크리스트: `docs/REGRESSION_CHECKLIST.md`
- 외부 DB 배포 가이드: `docs/DEPLOY_EXTERNAL_DB.md`
- 동시 실행 가이드: `docs/RUN_DEV.md`
- DB 스키마(루트): `../database_schema.md`
- DB 데이터 가이드(루트): `../DB_데이터_가이드.md`

## 참고

- 이 앱은 기존 DB 뷰/테이블을 기반으로 동작합니다.
- 데이터 최신성 및 일부 지표의 결측치 처리 품질은 DB 데이터 상태에 의존합니다.
