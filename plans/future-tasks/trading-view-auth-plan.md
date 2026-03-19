# Trading View Project Auth Plan

> 마지막 검토일: 2026-03-19

## 대상

- `apps/trading-view-project/`

## 관련 구현 위치

- 백엔드 진입점: `apps/trading-view-project/backend/app/main.py`
- 쓰기 API: `apps/trading-view-project/backend/app/routers/minervini.py`
- DB 설정: `apps/trading-view-project/backend/app/config.py`
- 배포 참고: `apps/trading-view-project/docs/DEPLOY_EXTERNAL_DB.md`

## 배경

- 현재 백엔드는 CORS 설정은 있으나 별도 인증 계층이 없다.
- 특히 아래 쓰기 API는 인증 없이 외부 호출 가능하면 위험하다.
  - `POST /api/minervini/list-type`
  - `PATCH /api/list-view/item`

## 목표

- 읽기 API는 기존 사용성을 최대한 유지한다.
- 쓰기 API는 최소 인증을 적용한다.
- 이후 필요 시 `viewer`/`editor`/`admin` 구조로 확장 가능하게 만든다.

## 1차 권장 방향

### 운영 모델 선택

#### A. 내부 도구형

- GCP IAP 또는 VPN 뒤에 배치
- 앱 내부 로그인 없이도 시작 가능
- 다만 백엔드에서 신뢰 가능한 사용자 식별 헤더를 검증해 쓰기 권한을 제한한다.

#### B. 외부 공개형

- 앱 자체 로그인 도입
- 백엔드에서 JWT 또는 서버 세션 기반 인증 수행
- 권한이 없는 사용자는 읽기만 허용

### 현재 기준 추천

- 우선은 `외부 공개 가능성도 고려한 앱 로그인 방식`으로 설계한다.
- 이유:
  - 이미 웹 UI와 쓰기 API가 존재한다.
  - 추후 외부 공개 여부가 바뀌어도 구조를 재사용하기 쉽다.

## 최소 설계

### 역할

- `viewer`: 조회만 가능
- `editor`: 조회 + 쓰기 API 호출 가능

### 보호 대상

- 인증 필수
  - `POST /api/minervini/list-type`
  - `PATCH /api/list-view/item`
- 비인증 허용 가능
  - `GET /api/health`
  - `GET /api/health/db` (운영에서는 내부 제한 검토)
  - 조회용 GET API

### 인증 저장 방식

- 운영 기준 권장: `HttpOnly Secure SameSite` 쿠키
- 개발 편의가 더 중요하면 초기에 Bearer token도 가능하지만, 최종 운영 목표는 쿠키 기반으로 둔다.
- 쿠키 기반으로 갈 경우 `SameSite` 정책만으로 충분한지 검토하고, 필요 시 CSRF 토큰 또는 double-submit cookie 방식을 추가한다.

## 구현 단계

### Phase 1. 인증 기반 도입

- 사용자/역할 모델 추가
- 로그인/로그아웃/현재 사용자 확인 API 추가
- 백엔드 인증 dependency 또는 middleware 추가
- 쓰기 API에 `editor` 권한 적용
- 파이썬 인증 의존성 추가: `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`

### Phase 2. 프론트 연동

- 로그인 화면 추가 또는 최소 관리자 로그인 UI 추가
- 수정 가능 UI는 인증 + 권한 보유 사용자에게만 노출
- 인증 실패 시 재로그인 유도
- 프론트 인증 상태 관리(React Context 또는 상태 라이브러리 추가) 결정 필요

### Phase 3. 운영 보강

- 로그인 rate limit
- CORS 허용 origin 고정
- 감사 로그(누가 어떤 심볼/메모를 수정했는지) 추가
- 헬스체크/Swagger 노출 범위 점검
- 쿠키 인증 채택 시 CSRF 방어 추가

## 데이터 모델 초안

- `users`
  - `id`
  - `username`
  - `password_hash`
  - `role`
  - `is_active`
  - `created_at`
  - `updated_at`
  - `last_login_at`
  - `failed_login_count`
  - `locked_until`
  - `password_changed_at`

## 테스트 기준

- 비로그인 상태에서 쓰기 API 호출 시 `401` 또는 `403`
- `viewer`는 쓰기 실패
- `editor`는 쓰기 성공
- 잘못된 토큰/만료 세션 처리 확인
- 프론트에서 로그인 상태에 따라 버튼 노출이 달라지는지 확인

## 구현 전 결정 필요 항목

- 내부 도구형인지 외부 공개형인지
- 인증 저장 방식을 쿠키로 바로 갈지, 1차는 Bearer token으로 갈지
- users 테이블 저장 위치: trading-view 자체 MySQL 스키마 또는 공용 DB에 저장할지 결정
  - 현재: trading-view는 DataBatcher의 `market` DB를 외부 연결로 공유 사용 중
  - 주의: users 테이블을 같은 `market` DB에 넣으면 배치 계정이 users 데이터까지 접근 가능
  - 검토 필요: 별도 DB 또는 별도 스키마/계정 권한 분리 방안
- 쿠키 인증 시 CSRF 대응 방식: SameSite 정책만 적용할지, 또는 CSRF 토큰을 추가로 도입할지 결정

## 우선순위

1. 쓰기 API 보호
2. 역할 분리
3. 로그인 UX
4. 감사 로그

## 다음 세션 실행 메모

- 첫 구현은 `쓰기 API 보호`만 완료해도 보안 수준이 크게 개선된다.
- 새 세션에서는 먼저 내부 도구형/A안 또는 외부 공개형/B안을 선택한 뒤 작업을 시작한다.
- 결정이 안 되어 있으면, 기본값은 `외부 공개형을 견딜 수 있는 앱 로그인 구조`로 잡는다.

## 완료 기준

- 쓰기 API가 비인증 사용자에게 더 이상 열려 있지 않음
- 최소 `viewer`/`editor` 권한 구분이 백엔드에서 강제됨
- 프론트 UI가 인증 상태와 권한에 맞게 수정 가능 기능을 제어함
- 인증 실패/권한 부족/세션 만료에 대한 테스트가 존재함

## 관련 문서

- `apps/trading-view-project/README.md` - 프로젝트 개요 및 환경 설정
- `apps/trading-view-project/AGENTS.md` - 코드 스타일 및 구현 규칙
- `apps/trading-view-project/docs/API.md` - API 계약 정의
- `apps/trading-view-project/docs/DEPLOY_EXTERNAL_DB.md` - 외부 DB 배포 가이드
- `plans/future-tasks/my-insight-security-hardening-plan.md` - my-insight 보안 강화 계획 참고
- `plans/future-tasks/security-policy-matrix.md` - 전체 서비스 보안 정책
- `plans/future-tasks/gcp-deployment-architecture.md` - 배포 구조 참고
