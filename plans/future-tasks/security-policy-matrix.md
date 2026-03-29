# Security Policy Matrix

> 마지막 검토일: 2026-03-19

## 목적

- 서비스별 공개 범위, 인증 필요 여부, DB 접근 방식, 우선 보완 항목을 한눈에 정리한다.

## 정책 표

| 대상 | 외부 공개 여부 | 인바운드 포트 | 인증 필요 여부 | DB 권한 원칙 | 우선 조치 |
| --- | --- | --- | --- | --- | --- |
| `db/` MySQL | 비공개 | 내부 `3306`만 | 사용자 인증이 아니라 DB 계정 인증 | root/app/test 계정 분리, 최소 권한 | 공인 노출 차단, host 제한, 계정 분리 |
| `apps/ingest-databatcher/` | 비공개 | 없음 | 외부 진입점이 없으므로 앱 로그인 불필요 | 배치 전용 쓰기 계정, 필요 시 읽기/쓰기 구분 | 인바운드 차단, 시크릿 분리, 실행 계정 최소권한 |
| `apps/my-insight-archieve/` | 공개 | `80/443` | 필요 | Mongo 앱 전용 계정 | 쿠키 기반 인증, CORS 고정, rate limit |
| `apps/trading-view-project/` | 공개 또는 내부 제한 공개 | `80/443` | 쓰기 API는 반드시 필요 | 읽기/쓰기 최소 권한 계정 또는 기능별 분리 | 쓰기 API 보호, 역할 분리, 접근 정책 결정 |

## 현재 상태 (as-is)

### `db/` MySQL
- 호스트 포트 바인딩 `3306:3306` 활성화 상태
- root/app/test 계정 분리 구현됨
- 월간 백업 스크립트만 존재, MongoDB 백업 로직 없음

### `apps/ingest-databatcher/`
- 배치 프로세스 중심, HTTP 서버 없음
- DB 계정 기반 접근 제어만 존재
- 환경변수 파일 `.env` 사용 중

### `apps/my-insight-archieve/`
- MongoDB 27017 외부 노출 상태
- JWT 인증 구조 존재 (localStorage 토큰 저장)
- CORS 설정: origin:true (모든 origin 허용)
- 관리자 단일 계정 운영 방식

### `apps/trading-view-project/`
- 읽기 API: 인증 없음 (공개)
- 쓰기 API: 인증 없음 (무방비 상태)
- DB 공유 구조 (trade DB 직접 접근)
- CORS 설정: ALLOWED_ORIGINS 환경변수로 제어

## 서비스별 메모

### `db/`
- 호스트 포트 바인딩이 존재하므로 운영에서는 private 접근만 허용해야 한다.

### `apps/ingest-databatcher/`
- 배치 프로세스 중심이므로 웹 로그인은 필요 없고, VM 접근 통제와 DB 계정 최소 권한이 핵심이다.

### `apps/my-insight-archieve/`
- JWT 인증 구조는 있으나 운영 보안 수준으로 보강이 필요하다.

### `apps/trading-view-project/`
- **DB 공유 토폴로지**: `trade` 데이터베이스를 ingest-databatcher의 `market` 데이터베이스와 공유하므로, 배치 전용 계정(읽기만)과 대시보드 전용 계정(쓰기 제한) 분리 설계 필수

## 공통 원칙

- 공개 서비스는 reverse proxy 뒤에서 `80/443`만 연다.
- 백엔드/DB 포트는 외부에 직접 노출하지 않는다.
- 환경변수 파일은 Git에서 제외하고, 운영에서는 Secret Manager 사용을 우선 검토한다.
- DB 계정은 공용 계정 하나로 합치지 말고 서비스 목적별로 분리한다.
- 민감 기능에는 인증뿐 아니라 rate limit, 감사 로그, 실패 모니터링을 함께 둔다.
- 쿠키 기반 인증을 쓰는 서비스는 CSRF 방어 전략까지 함께 설계한다.

### 백업 정책 (결정 필요)

- **MySQL 백업**: 월간 full 백업 스크립트만 존재 (`db_backup_monthly.sh`), 일일 증분 또는 주간 full 백업 추가 검토 필요
- **MongoDB 백업**: 현재 백업 로직 없음, mongodump 기반 정기 백업 스크립트 구현 필요
- **백업 디렉토리 접근 권한**: 배치 실행 계정 소유, 운영 담당자만 읽기 (600/640 권한), my-insight 백업은 `./backups:/app/backups` 볼륨 마운트로 호스트 접근 가능
- **백업 검증**: 월간 복구 테스트 및 무결성 체크(checksum) 권장
- **백업 데이터 암호화 및 보관 기간**: 백업 데이터 암호화 여부와 보관 정책(보관 기간, 삭제 규칙) 결정 필요

## 착수 전 체크리스트

- 각 서비스가 외부 공개인지 내부 전용인지 최종 확정
- 방화벽 정책에서 허용할 소스 대역 또는 IAP 사용 여부 확정
- DB 계정 분리안을 서비스별로 작성
- 인증 적용 범위(전체 API vs 쓰기 API만)를 서비스별로 확정

## 완료 기준

- 서비스별 공개 범위와 인바운드 포트가 확정됨
- 서비스별 인증 방식과 권한 모델이 확정됨
- DB 계정/권한 원칙이 서비스별로 문서화됨
- 즉시 조치 항목과 추후 조치 항목이 구분됨

## 관련 문서

- `plans/future-tasks/trading-view-auth-plan.md`: trading-view 인증 설계 및 구현 계획
- `plans/future-tasks/my-insight-security-hardening-plan.md`: my-insight 보안 강화 계획
- `plans/future-tasks/gcp-deployment-architecture.md`: GCP 배포 구조 및 네트워크 정책
- `db/compose/mysql-standalone/README.md`: MySQL 백업/복구 가이드
- `apps/my-insight-archieve/docs/BACKUP_RESTORE.md`: MongoDB 백업 복구 문서
- `AGENTS.md`: 배치 프로젝트 운영 규칙
