# Frontend Baseline (Stage 0)

리팩토링 전 기준 동작을 고정하기 위한 문서.

## 핵심 사용자 시나리오

1. 로그인
- `/login`에서 아이디/비밀번호 입력
- 성공 시 `/`로 이동
- 네비게이션 우측 상태가 `로그인` -> `로그아웃`으로 변경

2. 아카이브 작성/조회
- `/`에서 `남기기`로 기록 생성
- 목록 카드에서 `읽기`로 상세 진입
- 상세 페이지에서 댓글 확인 가능

3. 댓글
- 상세 페이지에서 댓글 추가
- 본인 댓글만 수정 버튼 노출

4. 카드 삭제 모드
- 카드 롱프레스 시 삭제 모드 진입
- 본인 글만 `x` 버튼 노출
- 비본인 글은 약한 안내 토스트 노출
- 삭제 모드는 3초 후 자동 해제

5. 템플릿
- `/templates`에서 검색/사용 케이스 필터
- `비우기`로 검색/필터 초기화
- 템플릿 추가/복사 동작

## API 계약 기준

- `POST /api/auth/login`
  - request: `{ "username": string, "password": string }`
  - response: `{ accessToken, admin: { id, username } }`

- `GET /api/auth/me`
  - response: `{ adminId, username }`

- `GET /api/entries`
  - response item 필수 필드: `_id`, `title`, `content`, `source`, `conversationUrl`, `tags`, `createdBy`

- `GET /api/entries/:id`
  - response 필수 필드: `_id`, `title`, `content`, `comments[]`

- `POST /api/entries/:id/comments`
  - request: `{ "content": string }`
  - response: 업데이트된 entry (comments 포함)

- `PATCH /api/entries/:id/comments/:commentId`
  - request: `{ "content": string }`
  - response: 업데이트된 entry (comments 포함)

- `DELETE /api/entries/:id`
  - 권한: 본인 작성 글만 가능

- `GET /api/templates`
  - response item 필수 필드: `_id`, `name`, `content`, `useCase`, `tags`

## 검증 기준

- `frontend npm run build`
- `backend npm run build`
- 라우트 확인: `/`, `/templates`, `/entries/[id]`, `/login`, `/admin`
- 브라우저 콘솔 치명 에러 없음
