# 디자인 QA 보고서 (Phase 5)

## 검증 범위

- 페이지: `/`, `/templates`, `/entries/[id]`, `/login`, `/admin`
- 기준: `docs/design_guide_01.md`, `docs/design_scope_freeze_01.md`

## 체크리스트 결과

### 1) 레이아웃/반응형

- [x] 3열/2열/1열 전환 규칙 유지
- [x] 템플릿 empty-state 분리 노출 제거
- [x] 모바일에서 액션 그룹 세로 정렬

### 2) 인터랙션/상태

- [x] loading/ready/error 상태 분리
- [x] skeleton 노출 시 레이아웃 점프 최소화
- [x] empty-state에서 메시지 + CTA 그룹 일관화

### 3) 접근성/시맨틱

- [x] 링크 내부 button 중첩 제거
- [x] 주요 입력/버튼 focus halo 노출
- [x] 키보드 탐색 가능한 CTA 배치

### 4) 인증 UX

- [x] 로그인 없는 작성 시 로그인 안내 제공
- [x] 401 응답 시 재로그인 안내 처리

## 빌드 검증

- [x] `npm run build` 성공

## 후속 권장(선택)

- 실제 디바이스(모바일 Safari/Chrome)에서 터치 타겟 QA
- 라이트하우스 기반 대비/접근성 추가 점검
