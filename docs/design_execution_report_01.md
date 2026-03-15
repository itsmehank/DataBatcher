# 디자인 개선 실행 보고서 (design_guide_01 기반)

## 1) 실행 개요

- 실행 일시: 2026-03-12
- 기준 문서: `docs/design_guide_01.md`
- 목표: 기능 중심 화면을 제품 인상 중심 화면으로 전환
- 적용 범위:
  - `frontend/app/globals.css`
  - `frontend/app/layout.tsx`
  - `frontend/app/page.tsx`
  - `frontend/app/templates/page.tsx`
  - `frontend/app/login/page.tsx`
  - `frontend/app/admin/page.tsx`

## 2) 단계별 실행 내용

### 단계 A. 디자인 토큰/전역 규칙 정비

적용 파일: `frontend/app/globals.css`

- 컬러 토큰 체계 재정의
  - `--bg-primary`, `--bg-secondary`, `--text-primary`, `--text-secondary`, `--accent`, `--border-soft` 등 추가
- 형태 토큰 정리
  - radius(`--radius-page-card`, `--radius-card`, `--radius-control`), shadow(`--shadow-soft`, `--shadow-hover`) 정의
- spacing scale 통일
  - 4/8/12/16/24/32/48/72/96 스케일 기반 변수 추가
- 타이포/레이아웃 기반 재정의
  - hero/section/card에 맞는 텍스트 크기와 line-height 규칙 적용
  - 전역 컨테이너 `--container-max` 기반 `.page-shell` 적용
- 인터랙션 규칙 추가
  - hover 시 카드 `translateY(-2px)`
  - focus halo 적용
  - 페이지 진입 애니메이션(`page-enter`) 적용

### 단계 B. 레이아웃/네비게이션 셸 재구성

적용 파일: `frontend/app/layout.tsx`, `frontend/app/globals.css`

- 상단 네비게이션 구조를 브랜드형 헤더로 교체
  - 로고 마크 + 워드마크
  - 핵심 메뉴(아카이브/템플릿/어드민/로그인) 재배치
- 헤더 스타일 개선
  - sticky + blur + 반투명 배경
  - 넓은 클릭 영역과 pill 형태 링크 적용
- 메인 래퍼 구조 통일
  - 기존 단순 `container`에서 `page-shell` + `page` 구조로 변경

### 단계 C. 아카이브 메인 페이지 구조 전환

적용 파일: `frontend/app/page.tsx`

- Hero 영역 신설
  - 제품 정체성 헤드라인
  - 설명 문구
  - CTA 2개(새 항목 작성/아카이브 보기)
  - 우측 preview 카드 구성
- 탐색 바 재구성
  - 검색, 카테고리 필터, 출처 필터, 정렬, 보기 전환(grid/list)
  - sticky 탐색 바 적용
- Featured Insight 구역 추가
  - 필터된 결과의 대표 항목 1개 강조 노출
- Recent Archive Grid 구역 추가
  - 기본 3열, 반응형 2열/1열
  - list/grid 토글 지원
- Secondary 구역 추가
  - 자주 쓰는 태그
  - 최근 출처
  - 빠른 액션(새 항목/필터 초기화)
- 데이터 기반 상태 처리
  - 검색/필터/정렬 결과 반영
  - 빈 상태 메시지 제공

### 단계 D. 템플릿 페이지 역할 분리(생산성 중심)

적용 파일: `frontend/app/templates/page.tsx`

- 페이지 헤더 재구성
  - 제목/설명 + 즉시 추가 버튼
- 탐색 도구 구성
  - 템플릿 검색, useCase 필터, 필터 초기화
- 콘텐츠 구조 분리
  - 상단: 자주 쓰는 템플릿(Featured)
  - 하단: 카테고리별 템플릿
- 템플릿 카드 개선
  - 제목/설명/본문/태그/복사 버튼 중심
  - 본문 길이 clamp 적용으로 과도한 노출 방지
- 작성 drawer 유지 및 스타일 통일

### 단계 E. 로그인/어드민 화면 신뢰 중심 전환

적용 파일: `frontend/app/login/page.tsx`, `frontend/app/admin/page.tsx`

- 로그인 화면
  - 중앙 정렬 카드형 레이아웃
  - 불필요 장식 제거, 명확한 폼 구조
- 어드민 화면
  - 관리 목적 중심의 단순 레이아웃
  - 백업 상태를 table-like 정보 블록으로 표현
  - 로그인 필요 상태 분기 유지

## 3) 공통 컴포넌트/패턴 정리

`frontend/app/globals.css`에 다음 공통 패턴 정의:

- `surface-card`, `panel`, `card`, `featured`
- `toolbar`, `grid-cards`, `secondary-grid`
- `chip`, `chip-strong`, `meta-row`, `card-actions`
- `fab`, `drawer`, `drawer-backdrop`
- `page-center`, `table-like`, `table-row`

## 4) 반응형 대응 내용

- Desktop: hero 2열, card 3열
- Tablet: toolbar 2열, card 2열
- Mobile: 단일 컬럼 전환, drawer bottom-sheet 전환, CTA/액션 세로 스택

## 5) 가이드 반영 체크

- 컬러 최소화: 무채색 중심 + 단일 포인트 컬러
- 경계선 남발 축소: 면/간격/그림자 중심 분리
- 타이포 위계 강화: Hero > Section > Card > Meta
- 화면 역할 분리: 아카이브/템플릿/관리 화면의 목적 분화
- 모션 절제: 과한 애니메이션 제거, 미세 인터랙션 중심

## 6) 남은 확인 항목

- 실제 백엔드 데이터 길이 편차(아주 긴 제목/본문)에서 추가 줄바꿈 보정 여부
- 네비게이션 active 상태 표시를 경로 기반으로 세분화할지 여부
- 접근성 점검(키보드 탭 순서, 대비 비율) 추가 검증

## 7) 변경 파일 목록

- `frontend/app/globals.css` (대규모 개편)
- `frontend/app/layout.tsx` (네비/페이지 셸 개선)
- `frontend/app/page.tsx` (아카이브 메인 구조 재설계)
- `frontend/app/templates/page.tsx` (템플릿 페이지 재설계)
- `frontend/app/login/page.tsx` (로그인 UI 정비)
- `frontend/app/admin/page.tsx` (관리자 UI 정비)

---

## 8) 후속 보완 작업 (2차 실행)

실행 일시: 2026-03-12

### A. 네비게이션 active 상태 보완

적용 파일:

- `frontend/app/components/main-nav.tsx` (신규)
- `frontend/app/layout.tsx`

적용 내용:

- `usePathname()` 기반 현재 경로 감지 적용
- `/`, `/templates`, `/admin`, `/login` 메뉴 active 스타일 자동 반영
- layout은 서버 컴포넌트 유지, 클라이언트 로직은 `MainNav`로 분리

영향 범위:

- 기존 라우팅/렌더링 로직 영향 없음 (헤더 표시 상태만 개선)

### B. 인증 필요 액션 UX 보강

적용 파일:

- `frontend/app/page.tsx`
- `frontend/app/templates/page.tsx`

적용 내용:

- 작성 버튼 클릭 시 토큰 유무(`getToken`) 사전 확인
- 비로그인 상태면 drawer 대신 로그인 유도 패널 표시
- 생성 API 401/Unauthorized 응답 시 로그인 안내 메시지와 `/login` 이동 경로 제공

영향 범위:

- 백엔드 권한 정책은 그대로 유지
- 프론트의 실패 처리 UX만 강화

### C. Loading/Empty/Error 상태 분리 + Skeleton 추가

적용 파일:

- `frontend/app/page.tsx`
- `frontend/app/templates/page.tsx`
- `frontend/app/globals.css`

적용 내용:

- 페이지 상태를 `loading | ready | error`로 분리
- 초기 로딩 시 skeleton 카드 렌더링
- API 실패 시 오류 패널 + 재시도 버튼 제공
- 검색 결과 없음(empty)과 로딩 상태를 분리해 혼동 방지

영향 범위:

- 데이터 조회/필터 로직 자체 변화 없음
- 상태 표현 계층(UI)만 확장

### D. 접근성/시맨틱 보완

적용 파일:

- `frontend/app/page.tsx`
- `frontend/app/globals.css`

적용 내용:

- `a` 안에 `button` 중첩 구조 제거
- 링크형 CTA를 `button-link` 스타일 클래스로 분리
- 긴 단어/URL 대비를 위해 카드 제목/본문 `overflow-wrap` 보완

영향 범위:

- 동작 기능은 동일
- 마크업 시맨틱과 키보드/스크린리더 친화성 개선

### E. 추가 스타일 자산

적용 파일:

- `frontend/app/globals.css`

추가 클래스/애니메이션:

- `button-link`, `secondary-link`
- `skeleton-card`, `skeleton-line*`
- `grid-cards-featured`
- `@keyframes skeleton-shimmer`

### F. 2차 실행 변경 파일 목록

- `frontend/app/components/main-nav.tsx` (신규)
- `frontend/app/layout.tsx`
- `frontend/app/page.tsx`
- `frontend/app/templates/page.tsx`
- `frontend/app/globals.css`

---

## 9) 잔여 단계 실행 (3차 실행 - 상세 페이지 확장)

실행 일시: 2026-03-12

### A. 아카이브 상세 페이지 추가

적용 파일:

- `frontend/app/entries/[id]/page.tsx` (신규)

적용 내용:

- `GET /entries/:id`로 항목 상세 데이터 조회
- 상세 본문, 메모, 태그, 원문 대화 링크를 구조화해 표시
- 카테고리 기반 관련 항목(최대 4개) 사이드 섹션 제공
- 상세 상단에서 아카이브 복귀 CTA 제공

영향 범위:

- 기존 목록/생성/수정 API 로직 변경 없음
- 조회 전용 화면 추가로 탐색 동선만 확장

### B. 카드 액션에 내부 상세 동선 연결

적용 파일:

- `frontend/app/page.tsx`

적용 내용:

- Featured 카드 및 Recent 카드에 `항목 열기/열기` 링크 추가
- 외부 원문 링크와 내부 상세 링크를 분리해 행동 명확화

영향 범위:

- 기존 원문 링크 동작 유지
- 카드 액션 확장으로 사용자 탐색 경로 증가

### C. 상세 페이지 스타일 보강

적용 파일:

- `frontend/app/globals.css`

적용 내용:

- `detail-layout`, `detail-main`, `detail-side` 등 상세 전용 레이아웃 클래스 추가
- 긴 문장/URL 대응(`overflow-wrap`)과 본문 가독성(white-space/line-height) 강화
- 관련 항목 리스트의 hover/focus 가시성 개선
- 모바일에서 1열로 자연스럽게 전환되도록 반응형 규칙 추가

### D. 3차 실행 변경 파일 목록

- `frontend/app/entries/[id]/page.tsx` (신규)
- `frontend/app/page.tsx`
- `frontend/app/globals.css`

---

## 10) 템플릿 empty-state 정렬 이슈 수정 (4차 실행)

실행 일시: 2026-03-12

### A. 문제

- 템플릿 empty-state에서 안내 요소가 분리되어 보이는 시각적 이슈 발생
- 같은 맥락 UI가 좌/우 다른 박스로 인식되어 레이아웃 깨짐처럼 보임

### B. 수정 내용

적용 파일:

- `frontend/app/templates/page.tsx`
- `frontend/app/globals.css`

변경 사항:

- empty 상태에서 안내 영역을 단일 `empty-state-card`로 통합
- 인증 안내(`needsLoginHint`)의 중복 노출을 empty 상태에서는 억제
- 툴바 우측 카운트 뱃지는 empty 상태에서 안내 문구(`empty-toolbar-note`)로 대체
- empty 상태 액션(`첫 템플릿 추가`, `관리자 로그인`)을 한 그룹으로 정렬
- 모바일에서는 세로 스택으로 전환되도록 반응형 규칙 추가

### C. 영향 범위

- 데이터/인증/복사 기능 로직 변경 없음
- 템플릿 empty 상태의 배치/가독성만 개선

### D. 검증

- `npm run build` 성공

---

## 11) 마감 단계 보완 (5차 실행 - 계획 보강/문서화)

실행 일시: 2026-03-12

### A. 범위 잠금 및 측정 지표 정의

신규 문서:

- `docs/design_scope_freeze_01.md`

핵심 내용:

- In/Out Scope 분리
- DoD를 측정 가능한 형태로 고정
- 단계별 게이트(서버 재시작, 강력 새로고침, 빌드, 문서 기록) 정의

### B. 레퍼런스/무드보드 기록

신규 문서:

- `docs/design_reference_01.md`
- `docs/design_moodboard_01.md`

핵심 내용:

- Apple/Linear/Notion 차용/배제 기준 명시
- 화면 톤, 타이포, 컴포넌트 인상, 배제 효과 정리

### C. 시스템 운영 규칙 및 QA 보고서

신규 문서:

- `docs/design_system_rules_01.md`
- `docs/design_qa_report_01.md`

핵심 내용:

- 토큰 사용 규칙, 상태표, 반응형 규칙 정의
- 접근성/반응형/상태 분리 검증 체크리스트 작성

### D. 5차 실행 변경 파일 목록

- `docs/design_scope_freeze_01.md` (신규)
- `docs/design_reference_01.md` (신규)
- `docs/design_moodboard_01.md` (신규)
- `docs/design_system_rules_01.md` (신규)
- `docs/design_qa_report_01.md` (신규)
- `docs/design_execution_report_01.md`

---

## 12) design_guide_02 반영 리디자인 (6차 실행)

실행 일시: 2026-03-12

### A. 톤앤매너 전환 (차가운 SaaS 인상 완화)

적용 파일:

- `frontend/app/globals.css`

적용 내용:

- 컬러 토큰을 웜 톤 기반으로 재조정
  - 배경: 쿨그레이 중심 -> 아이보리/웜그레이 중심
  - 텍스트: 순검정 계열 -> 딥 차콜 계열
  - 포인트: 선명 블루 -> 채도 낮은 잉크 블루 계열
- 버튼/링크 CTA의 대비 강도를 낮추고 초대형 톤으로 완화
- 카드/featured/drawer/skeleton 등 전반 질감을 따듯한 표면감으로 조정

### B. 아카이브 메인 카피 및 구조 톤 수정

적용 파일:

- `frontend/app/page.tsx`

적용 내용:

- Hero 문구를 기능 설명형에서 기록 경험형 문장으로 교체
- CTA 라벨을 기록장 톤으로 교체 (`기록 남기기`, `기록 둘러보기`)
- preview를 수치 요약 중심에서 문장 중심 톤으로 조정
- 섹션명 교체
  - `Featured Insight` -> `다시 꺼내보고 싶은 기록`
  - `Recent Archive` -> `최근 남긴 생각`
  - `자주 쓰는 탐색 키` -> `자주 머무는 키워드`
- 검색/필터 영역 앞에 설명 문장을 추가해 기능 UI 노출 템포를 한 단계 완화

### C. 템플릿 페이지 감성화

적용 파일:

- `frontend/app/templates/page.tsx`

적용 내용:

- 페이지 제목/설명을 기록장 문맥으로 전환
  - `바로 쓰는 템플릿 라이브러리` -> `기록을 시작하는 문장들`
- 상단 CTA 강도 완화 (`문장 더하기`)
- 필터/정렬/상태 문구를 기능 중심에서 문장 중심 카피로 정리
- 카드 액션 문구를 도구형에서 기록형으로 정리 (`문장 복사`, `문장 꺼내기`)
- empty-state 메시지와 액션 문구를 기록 시작 맥락으로 강화

### D. 시스템 상태 노출 조용화

적용 파일:

- `frontend/app/page.tsx`
- `frontend/app/templates/page.tsx`

적용 내용:

- error 상태 패널의 시각 강도를 낮추고 설명 중심으로 축소
- 재시도 액션을 작은 보조 버튼 스타일로 조정 (`다시 읽기`)
- 기록 콘텐츠보다 상태 UI가 먼저 보이지 않도록 우선순위 하향

### E. 로그인/관리 페이지 카피 톤 정렬

적용 파일:

- `frontend/app/login/page.tsx`
- `frontend/app/admin/page.tsx`

적용 내용:

- 로그인/관리 화면 카피를 기록장 정체성에 맞게 조정
- 강한 관리도구 어조를 완화하고 안전한 기록 보관 맥락으로 표현

### F. 6차 실행 변경 파일 목록

- `frontend/app/globals.css`
- `frontend/app/page.tsx`
- `frontend/app/templates/page.tsx`
- `frontend/app/login/page.tsx`
- `frontend/app/admin/page.tsx`
- `docs/design_execution_report_01.md`
