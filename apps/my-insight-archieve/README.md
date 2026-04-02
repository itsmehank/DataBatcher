# My Insight Archive

AI 대화에서 다시 볼 가치가 있는 내용을 카테고리별로 아카이브하고, 템플릿을 별도 보관하며, MongoDB 전체 데이터를 백업할 수 있는 개인용 웹 서비스입니다.

## 주요 기능

- 카테고리(기본 + 사용자 커스텀) 관리
- 아카이브 엔트리 CRUD (대화 링크 URL + 출처 저장)
- 템플릿 보관 페이지 (재사용 템플릿 CRUD)
- 관리자 로그인 기반 백업 API
- MongoDB 전체 데이터 export (최신 백업 1개만 유지)

## 프로젝트 구조

- `frontend`: Next.js 웹 UI
- `backend`: NestJS API 서버
- `docs`: API/백업복구/보안 문서
- `docker-compose.yml`: 앱 서비스(backend/frontend) 실행

## 공용 Mongo bootstrap과 앱 runtime 설정

- 루트 `.env`: 공용 Mongo bootstrap 계약
- `db/compose/mongo-standalone/`: shared Mongo 기동/사용자/권한 provisioning
- `apps/my-insight-archieve/.env`: 앱 runtime 연결 정보
- 앱은 `MONGODB_URI`만 받아 Mongo에 연결하고, 관리자 계정/기본 카테고리 seed는 앱이 계속 책임집니다.

## 빠른 시작 (Docker)

> 아래 명령은 **DataBatcher 모노레포 루트**에서 실행 기준입니다.

1. 공용 Mongo bootstrap 준비

```bash
cp .env.example .env
docker compose -f db/compose/mongo-standalone/docker-compose-mongo.yaml --env-file .env up -d
```

2. 앱 환경 변수 파일 생성

```bash
cp apps/my-insight-archieve/.env.example apps/my-insight-archieve/.env
```

3. Docker Compose 실행

```bash
docker compose -f apps/my-insight-archieve/docker-compose.yml --env-file apps/my-insight-archieve/.env up --build -d
```

4. 접속

- 프론트엔드: `http://localhost:3000`
- 백엔드 헬스체크: `http://localhost:4000/api/health`

중지:

```bash
docker compose -f apps/my-insight-archieve/docker-compose.yml --env-file apps/my-insight-archieve/.env down
```

## 포트/컨테이너 충돌 해결

다른 프로젝트가 같은 포트를 사용 중이라면 `apps/my-insight-archieve/.env` 또는 루트 `.env`에서 아래 값을 변경하세요.

- `MONGO_PORT` (공용 Mongo, 기본 27017)
- `BACKEND_PORT` (기본 4000)
- `FRONTEND_PORT` (기본 3000)

컨테이너 이름 충돌 시:

- `INSIGHT_ARCHIVE_STACK` 값을 프로젝트별로 다르게 지정하세요.
  - 예: `INSIGHT_ARCHIVE_STACK=insight-archive-v2`

## 실행 전 설정 파일 가이드

이 프로젝트는 공용 Mongo bootstrap용 루트 `.env`와 앱 runtime용 `apps/my-insight-archieve/.env`를 분리해서 사용합니다.

1. 루트 `.env`
   - 공용 Mongo 인스턴스/bootstrap 계약
   - `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD`, `MONGO_APP_DB_NAME`, `MONGO_APP_USERNAME`, `MONGO_APP_PASSWORD`, `MONGO_PORT`
2. `apps/my-insight-archieve/.env`
   - 앱 runtime 설정
   - `MONGODB_URI`, `JWT_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `NEXT_PUBLIC_API_BASE_URL` 등

준비 방법:

```bash
cp .env.example .env
cp apps/my-insight-archieve/.env.example apps/my-insight-archieve/.env
```

필수 값:

- `MONGODB_URI`: 백엔드가 접속할 MongoDB URI
- `JWT_SECRET`: 백엔드 인증 서명 키

루트 `.env`에서 자주 확인할 값:

- `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD`, `MONGO_APP_DB_NAME`
- `MONGO_APP_USERNAME`, `MONGO_APP_PASSWORD`
- `MONGO_PORT`

앱 `.env`에서 자주 확인할 값:

- `BACKEND_PORT`, `FRONTEND_PORT`
- `NEXT_PUBLIC_API_BASE_URL`

운영/관리 기능용 값:

- `ADMIN_USERNAME`, `ADMIN_PASSWORD`: 기본 관리자 계정 bootstrap
- `BACKUP_DIR`, `BACKUP_FILE_NAME`: 백업 저장 경로/이름
- `CORS_ORIGIN`: 백엔드 허용 Origin

주의:

- Docker app stack에서는 `.env.example`의 `MONGODB_URI`처럼 `shared-mongo` 호스트를 사용한다.
- 로컬 비-Docker 실행 시에는 보통 `localhost` 기준 URI로 바꿔야 한다.

## 로컬 개발 실행 (비 Docker)

> 아래 명령도 **모노레포 루트** 기준입니다.

1. 의존성 설치

```bash
npm --prefix apps/my-insight-archieve/frontend install
npm --prefix apps/my-insight-archieve/backend install
```

2. 환경 변수 준비

- `apps/my-insight-archieve/.env`를 사용합니다.
- 필수: `JWT_SECRET`, `MONGODB_URI`
- 참고: `.env.example`의 `MONGODB_URI`는 shared Mongo Docker 기준(`shared-mongo` 호스트)입니다.
  로컬에서 직접 실행할 때는 보통 `localhost` URI를 사용해야 합니다.

예시:

```env
MONGODB_URI=mongodb://insight_app:change-this-app-password@localhost:27017/insight_archive?authSource=insight_archive
JWT_SECRET=change-this-secret
```

3. 개발 서버 실행

```bash
npm --prefix apps/my-insight-archieve/backend run start:dev
npm --prefix apps/my-insight-archieve/frontend run dev
```

4. 확인

- 프론트엔드: `http://localhost:3000`
- 백엔드 헬스체크: `http://localhost:4000/api/health`

## 프로덕션 실행

### Frontend (Next standalone)

```bash
npm --prefix apps/my-insight-archieve/frontend run build
PORT=3000 npm --prefix apps/my-insight-archieve/frontend run start
```

> 이 저장소는 `output: "standalone"` 설정을 사용하므로, `next start` 직접 실행 대신 위 스크립트를 사용하세요.

### Backend

```bash
npm --prefix apps/my-insight-archieve/backend run build
npm --prefix apps/my-insight-archieve/backend run start
```

## 빌드 확인

```bash
npm --prefix apps/my-insight-archieve/frontend run build
npm --prefix apps/my-insight-archieve/backend run build
```

현재 기본 테스트 스크립트는 구성되어 있지 않습니다.

## 기본 관리자 계정

- 아이디: `.env`의 `ADMIN_USERNAME`
- 비밀번호: `.env`의 `ADMIN_PASSWORD`

앱 시작 시 관리자 계정이 없으면 자동 생성됩니다.

## 개발 참고

- 백업 파일은 서버의 `backups/latest.archive.gz`에 저장됩니다.
- 기존 백업은 제거되고 최신 1개만 유지됩니다.
- 백엔드 라우트는 `/api` prefix를 사용합니다.
- 상세 API는 `docs/API.md`를 확인하세요.
