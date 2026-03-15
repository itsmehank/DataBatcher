# API 명세

기본 prefix: `/api`

## Auth

- `POST /auth/login`
  - body: `{ "username": string, "password": string }`
  - response: `{ accessToken, admin }`

- `GET /auth/me`
  - header: `Authorization: Bearer <token>`
  - response: 관리자 정보

## Categories

- `GET /categories`
- `POST /categories` (admin)
- `PATCH /categories/:id` (admin)
- `DELETE /categories/:id` (admin)

삭제 시 해당 카테고리의 엔트리는 `미분류` 카테고리로 이동됩니다.

## Entries

- `GET /entries?categoryId=&q=&source=`
- `GET /entries/:id`
- `POST /entries` (admin)
- `PATCH /entries/:id` (admin)
- `DELETE /entries/:id` (admin)

- `POST /entries/:id/comments` (admin)
  - body: `{ "content": string }`
  - 설명: 댓글 추가 (작성자는 로그인 사용자)

- `PATCH /entries/:id/comments/:commentId` (admin)
  - body: `{ "content": string }`
  - 설명: 본인 댓글만 수정 가능

`source` 예시: `chatgpt`, `claude`, `gemini`, `other`

## Templates

- `GET /templates?q=&tag=`
- `GET /templates/:id`
- `POST /templates` (admin)
- `PATCH /templates/:id` (admin)
- `DELETE /templates/:id` (admin)

## Backup

- `POST /admin/backup/export` (admin)
  - MongoDB 전체 컬렉션 데이터를 gzip 아카이브로 export
  - 기존 백업 제거 후 최신 파일 1개만 유지

- `GET /admin/backup/status` (admin)
  - 최신 백업 파일 정보와 마지막 실행 결과 조회

## Health

- `GET /health`
