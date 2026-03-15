# GitHub 업로드 전 최종 체크리스트

## 1) 민감 정보
- `.env` 파일은 절대 커밋하지 않는다.
- `.gitignore`에 아래 항목이 포함되어 있는지 확인한다.
  - `.env`, `.env.*`, `node_modules/`, `.next/`, `dist/`, `backups/`
- `JWT_SECRET`은 필수 환경변수로 설정한다. (코드 기본값 사용 금지)

## 2) 빌드/기본 동작
- backend: `npm run build`
- frontend: `npm run build`
- frontend 프로덕션 실행: `PORT=3000 npm --prefix frontend run start`
- 주요 라우트 확인
  - `/`, `/templates`, `/login`, `/admin`
  - `/api/health`

## 3) 핵심 기능 스모크
- 로그인 후 홈 이동 + 네비게이션 로그아웃 표시
- 아카이브 기록 생성/조회/삭제(본인 글만)
- 상세 페이지 댓글 추가/수정(본인 댓글만)
- 템플릿 생성/검색/필터/복사

## 4) 배포 전 점검
- `docker compose up -d --build`로 컨테이너 재생성 후 동일 시나리오 재검증
- README 실행 방법/포트 정보 최신화 확인
