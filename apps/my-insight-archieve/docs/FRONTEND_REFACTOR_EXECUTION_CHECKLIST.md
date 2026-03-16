# Frontend Refactor Execution Checklist

이 문서는 프론트 구조 분리 리팩토링을 **단계별로 안전하게** 진행하기 위한 실행 체크리스트다.
각 단계는 "작업 → 검증 → 통과 게이트" 순서로 진행하고, 통과 전 다음 단계로 이동하지 않는다.

---

## 공통 실행 규칙

- 한 단계에서 구조 변경과 동작 변경을 동시에 크게 하지 않는다.
- 단계 종료 시 아래 6개 고정 검증을 수행한다.
  1. `frontend`: `npm run build`
  2. `backend`: `npm run build`
  3. 핵심 라우트 확인: `/`, `/templates`, `/entries/[id]`, `/login`, `/admin`
  4. 브라우저 콘솔 치명 에러 여부 확인
  5. 서버 로그 치명 에러 여부 확인
  6. 이전 단계 핵심 시나리오 1개 재실행 (회귀 확인)
- 실패 시 즉시 해당 단계 변경만 롤백하고 원인 분리 후 재시도한다.

---

## Stage 0. Baseline 고정

### 작업
- 현재 동작 기준 시나리오 문서화
  - 로그인/로그아웃
  - 아카이브 글 생성/삭제(작성자 제한)
  - 롱프레스 3초 자동 해제
  - 댓글 추가/수정(본인만)
  - 템플릿 검색/필터/복사/생성
- API 계약 스냅샷(요청/응답 필드)
  - `/auth/login`, `/auth/me`
  - `/entries`, `/entries/:id`, `/entries/:id/comments`, `/entries/:id/comments/:commentId`
  - `/templates`

### 단계 검증
- `frontend npm run build`
- `backend npm run build`
- 핵심 라우트 수동 확인

### 통과 게이트
- 빌드 성공, 콘솔/로그 치명 에러 없음, 시나리오 문서화 완료

---

## Stage 1. 타입/유틸 분리

### 작업
- `frontend/types` 생성: `entry.ts`, `template.ts`, `category.ts`, `auth.ts`
- 공통 함수를 `frontend/lib`로 이동
  - 날짜 포맷
  - 주간/이전 그룹 계산
  - 권한 판별 유틸
- 페이지 파일 내 중복 타입 정의 제거

### 영향 가능 로직
- 타입 정합성 깨짐으로 빌드 실패
- import 경로 실수

### 단계 검증
- 빌드 2종(frontend/backend)
- `/`, `/templates`, `/entries/[id]` 렌더 확인

### 통과 게이트
- 페이지 동작 동일, 타입 오류 0

---

## Stage 2. 아카이브 로직 hooks 분리

### 작업
- `frontend/features/archive/hooks` 생성
  - `use-archive-data.ts`
  - `use-archive-filters.ts`
  - `use-card-delete-mode.ts`
- `app/page.tsx`의 상태/핸들러를 hooks로 이동

### 영향 가능 로직
- 삭제모드 타이머 누수/중복
- 작성자 권한 조건 누락
- 주간/이전 그룹 계산 오류

### 단계 검증 (필수 시나리오)
- 본인 글 롱프레스: 흔들림 + `x` 노출 + 삭제 성공
- 비본인 글 롱프레스: `x` 미노출 + 약한 안내 문구
- 3초 후 자동 고정 복귀
- ESC/바깥 탭으로 삭제 모드 종료
- 필터/정렬/비우기 후 그룹 유지

### 통과 게이트
- 삭제/그룹/필터 동작 동일, 타이머 관련 에러 없음

---

## Stage 3. 아카이브 UI 컴포넌트 분리

### 작업
- `frontend/features/archive/components` 생성
  - `ArchiveHero`
  - `ArchiveToolbar`
  - `EntryGroupSection`
  - `EntryCard`
  - `EntryComposerDrawer`
  - `ArchiveStatusMessages`
- `app/page.tsx`를 조립 전용으로 축소

### 영향 가능 로직
- props 누락으로 버튼/링크 동작 실패
- 카드별 이벤트(onPointerDown 등) 누락

### 단계 검증
- 생성/삭제/읽기/원문 링크 전부 확인
- 비우기 버튼 동작(검색+필터 초기화)
- 에러/피드백 메시지 노출 확인

### 통과 게이트
- 아카이브 핵심 플로우 회귀 없음

---

## Stage 4. 템플릿 페이지 분리

### 작업
- `frontend/features/templates/hooks`
  - `use-templates-data.ts`
  - `use-templates-filters.ts`
- `frontend/features/templates/components`
  - `TemplatesHero`
  - `TemplatesToolbar`
  - `TemplateCardList`
  - `TemplateComposerDrawer`

### 영향 가능 로직
- 검색/사용 케이스 필터 누락
- 복사 피드백 누락

### 단계 검증
- 검색/필터/비우기
- 템플릿 생성 후 목록 반영
- 복사 버튼 동작

### 통과 게이트
- 템플릿 기능 회귀 없음

---

## Stage 5. 스타일 분리

### 작업
- `globals.css`는 토큰/공통 레이아웃 중심으로 축소
- 페이지별 스타일 분리
  - `features/archive/archive.css`
  - `features/templates/templates.css`
  - `features/entry-detail/entry-detail.css`

### 영향 가능 로직
- 클래스 충돌
- 모바일 레이아웃 깨짐
- 삭제 흔들림/힌트 위치 깨짐

### 단계 검증
- 데스크톱/모바일 레이아웃
- 카드 스태거/약한 구분선/삭제 모드/힌트 노출 확인
- 상세 댓글 UI 스타일 확인

### 통과 게이트
- 시각 회귀 없음, CSS 충돌 없음

---

## Stage 6. 최종 회귀 + GitHub 업로드 전 점검

### 작업
- dead code/unused import 정리
- README/docs 경로 및 구조 업데이트
- 민감정보 점검

### 민감정보 체크리스트
- `.env`가 Git 추적 대상이 아닌지 확인
- `backups/`, `.next/`, `dist/`, `node_modules/` 미추적 확인
- 코드 내 하드코딩 secret/fallback 점검

### 최종 검증 시나리오
- 로그인 성공 후 홈 이동 + 네비 상태 토글
- 아카이브 생성 → 상세 진입 → 댓글 추가/수정
- 본인/비본인 삭제 권한 확인
- 템플릿 생성/필터/복사

### 통과 게이트
- 빌드 성공, 핵심 시나리오 전부 정상, 민감정보 유출 위험 없음

---

## 롤백 포인트

- Stage 단위로 커밋/태그를 남겨서 즉시 되돌릴 수 있게 유지
- 권장 태그 예시
  - `refactor-stage-0-baseline`
  - `refactor-stage-1-types`
  - `refactor-stage-2-archive-hooks`
  - `refactor-stage-3-archive-components`
  - `refactor-stage-4-templates`
  - `refactor-stage-5-styles`
