# My Insight Archive Security Hardening Plan

> 마지막 검토일: 2026-03-19

## 대상

- `apps/my-insight-archieve/`

## 관련 구현 위치

- 백엔드 진입점: `apps/my-insight-archieve/backend/src/main.ts`
- 인증 컨트롤러: `apps/my-insight-archieve/backend/src/auth/auth.controller.ts`
- 인증 서비스: `apps/my-insight-archieve/backend/src/auth/auth.service.ts`
- JWT 전략: `apps/my-insight-archieve/backend/src/auth/jwt.strategy.ts`
- 프론트 인증 상태: `apps/my-insight-archieve/frontend/lib/use-auth.ts`
- 배포 설정: `apps/my-insight-archieve/docker-compose.yml`

## 현재 상태 요약

- JWT 인증 구조는 이미 존재한다.
- 관리자 비밀번호는 bcrypt 해시로 저장한다.
- 다만 운영 환경 기준으로는 아래 보강이 필요하다.
  - 프론트 토큰 저장이 `localStorage` 기반
  - CORS가 너무 넓게 허용됨
  - 로그인 rate limit 부재
  - MongoDB 포트 직접 노출 가능
  - 앱이 Mongo root 계정 예시를 사용 중

## 목표

- 기존 로그인 구조를 유지하되 운영 보안 수준으로 강화한다.
- 인증 토큰 탈취 위험과 관리자 기능 오남용 가능성을 줄인다.

## 우선순위

1. `localStorage` 토큰 제거
2. 쿠키 기반 인증으로 전환
3. CORS 화이트리스트 고정
4. 로그인 rate limit 추가
5. Mongo 접근 축소 및 앱 전용 계정 사용
6. 관리자 계정 운영 절차 정리

## 개선 계획

### Phase 1. 인증 저장 방식 개선

- 로그인 성공 시 access token을 응답 body 대신 `HttpOnly Secure SameSite` 쿠키로 발급
- 프론트에서 직접 토큰을 저장/삭제하지 않도록 변경
- `/auth/me`는 쿠키 기반 세션 확인으로 유지
- 로그아웃 시 쿠키 무효화 엔드포인트 추가
- 상태 변경 API가 많으므로 쿠키 전환 시 CSRF 방어 전략을 함께 적용
- **사전 검토**: 현재 JWT_EXPIRES_IN=7일(`.env.example` 기본값)인데, 운영 환경에서는 다음을 결정해야 한다:
  - Access token 수명: 현재보다 단축(예: 15분) 여부
  - Refresh token 재발급 정책(refresh token 유효기간): 필요 여부 및 갱신 전략
  - 강제 로그아웃/세션 폐기 정책: 관리자 권한 박탈 시 기존 토큰 무효화 메커니즘
  - 토큰 블랙리스트: DB/Redis 기반 폐지된 토큰 추적 필요성 검토

### Phase 2. 백엔드 보호 강화

- CORS를 `origin: true`에서 운영 도메인 화이트리스트 기반으로 변경
- 로그인 시도 rate limit 추가
- reverse proxy 환경을 고려한 secure cookie 설정 검토
- 필요 시 보안 헤더 추가
- **보안 헤더**: 아래 헤더를 response에 추가하는 것을 검토한다:
  - `Content-Security-Policy`: XSS 방지(예: `default-src 'self'`)
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY` (clickjacking 방지)
  - `Strict-Transport-Security` (HTTPS 강제, 필요 시)

### Phase 3. DB 및 운영 환경 강화

- MongoDB 포트 외부 노출 제거
- Mongo root 계정 대신 앱 전용 계정 사용
- 백업 디렉토리 접근 권한 점검
- 관리자 초기 계정 생성 절차를 문서화
- 초기 관리자 계정 자동 생성 방식을 유지할지, 1회 부트스트랩 후 수동 관리로 전환할지 결정
- **MongoDB 백업 인프라 현황**: 현재 MySQL 백업 스크립트(`db_backup_monthly.sh`, `db_restore_full.sh`)만 존재하고 MongoDB 백업 로직이 전무하므로, 다음을 점검한다:
  - MongoDB 백업 정기 자동화: 주기/저장소/복구 테스트
  - 백업 스토리지: 로컬 디렉토리만 사용 중, 클라우드 동기화 필요성 검토
  - 복구 프로세스: 긴급 상황에서 빠른 복구 가능성 확인
- **운영 배포 전 기본 비밀번호 변경 필수**: `.env.example`에 기본 관리자 비밀번호가 포함되어 있으므로, 운영 환경 배포 전에 반드시 변경해야 한다. 가능하다면 Phase 1 쿠키 전환과 병행하여 조기 처리를 권장한다.

## 체크리스트

### 인증/프론트

- `localStorage` 사용 제거
- 쿠키 기반 로그인/로그아웃 적용
- 인증 상태 확인 로직 재정리
- 인증 실패 시 로그인 이동 흐름 점검

### 백엔드

- CORS 허용 도메인 환경변수화
- rate limit 적용
- 운영 모드에서 secure cookie 강제
- 불필요한 상세 오류 메시지 노출 여부 점검

### 인프라

- Mongo 외부 포트 제거
- Mongo 계정 분리
- `.env` 대신 Secret Manager 사용 검토
- HTTPS 종료 지점과 proxy 설정 점검

## 검증 기준

- 로그인 후 새로고침 시 인증 상태 유지
- XSS 상황에서도 JS로 토큰을 직접 읽을 수 없음
- 비로그인 상태에서 관리자 API 접근 차단
- 반복 로그인 실패에 대한 제한 동작 확인
- 운영 도메인 외 origin 요청 차단 확인

## 구현 전 확인 항목

- **CSRF 방어 수준 결정** (최우선): 쿠키 기반 인증 전환 시 CSRF 대응 전략
  - `SameSite=Strict` 단독 사용 여부
  - 별도 CSRF 토큰(더블 서밋 패턴, 토큰 기반) 도입 여부
- 프론트와 백엔드 도메인 구성을 단일 도메인/서브도메인 중 무엇으로 갈지
- reverse proxy 또는 LB에서 HTTPS 종료를 어디서 할지
- 관리자 단일 계정 유지 여부 또는 다중 계정 지원 여부

## 다음 세션 실행 메모

- 첫 구현은 `localStorage 제거 + 쿠키 전환 + CORS 고정`까지만 해도 체감 보안 개선이 크다.
- Mongo 계정 분리와 외부 포트 제거는 앱 수정과 인프라 수정이 함께 필요하므로 별도 커밋으로 분리하는 것이 안전하다.

## 완료 기준

- 프론트에서 토큰을 직접 저장하지 않음
- 관리자 API가 쿠키 기반 인증으로 정상 동작함
- CORS가 운영 도메인만 허용하도록 고정됨
- 로그인 시도 제한과 Mongo 노출 축소 정책이 반영됨

## 관련 문서

- `apps/my-insight-archieve/.env.example`: JWT_EXPIRES_IN, MONGODB_URI, 관리자 자격증명 예시
- `apps/my-insight-archieve/backend/src/auth/jwt.strategy.ts`: Bearer token 기반 JWT 전략
- `apps/my-insight-archieve/backend/src/auth/auth.controller.ts`: 로그인/로그아웃 엔드포인트
- `apps/my-insight-archieve/frontend/lib/use-auth.ts`: 프론트 인증 상태 관리
- `plans/future-tasks/trading-view-auth-plan.md`: 다른 프로젝트 인증 계획 참고
- `plans/future-tasks/security-policy-matrix.md`: 전체 서비스 보안 정책 매트릭스
- `plans/future-tasks/gcp-deployment-architecture.md`: GCP 배포 구조 및 인프라 설계
