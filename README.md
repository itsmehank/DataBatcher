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
- `docker-compose.yml`: 전체 서비스 실행

## 빠른 시작 (Docker)

1. 환경 변수 파일 생성

```bash
cp .env.example .env
```

2. Docker Compose 실행

```bash
docker compose up --build
```

3. 접속

- 프론트엔드: `http://localhost:3000`
- 백엔드 헬스체크: `http://localhost:4000/api/health`

## 로컬 개발 실행 (비 Docker)

1. 의존성 설치

```bash
npm --prefix frontend install
npm --prefix backend install
```

2. 환경 변수 준비

- `.env`를 사용합니다.
- 필수: `JWT_SECRET`, `MONGODB_URI`
- 참고: `.env.example`의 `MONGODB_URI`는 Docker 기준(`mongodb` 호스트)입니다.
  로컬에서 직접 실행할 때는 보통 `localhost` URI를 사용해야 합니다.

예시:

```env
MONGODB_URI=mongodb://admin:adminpassword@localhost:27017/insight_archive?authSource=admin
JWT_SECRET=change-this-secret
```

3. 개발 서버 실행

```bash
npm --prefix backend run start:dev
npm --prefix frontend run dev
```

4. 확인

- 프론트엔드: `http://localhost:3000`
- 백엔드 헬스체크: `http://localhost:4000/api/health`

## 프로덕션 실행

### Frontend (Next standalone)

```bash
npm --prefix frontend run build
PORT=3000 npm --prefix frontend run start
```

> 이 저장소는 `output: "standalone"` 설정을 사용하므로, `next start` 직접 실행 대신 위 스크립트를 사용하세요.

### Backend

```bash
npm --prefix backend run build
npm --prefix backend run start
```

## 빌드 확인

```bash
npm --prefix frontend run build
npm --prefix backend run build
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
