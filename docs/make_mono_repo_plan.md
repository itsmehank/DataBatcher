# DataBatcher 모노레포 전환 최종 계획

이 문서는 현재 DataBatcher를 기준으로 모노레포 전환을 실행하기 위한 최종 계획이다.

## 1) 범위

- 이번 범위: 0~3단계 + 5단계 최소셋
- 보류: 4단계(외부 프로젝트 병합)
- 테스트 DB 원칙: 코드/설정 파일을 변경하지 않고 `DATABASE_URL`/`MYSQL_PORT` 런타임 오버라이드로만 `3307` 사용

## 2) 핵심 결정

- 모노레포 구조는 `apps/`, `db/`, `packages/`, `apps/ingest-databatcher/scripts/`를 기준으로 설계한다.
- DB는 특정 앱 소속이 아닌 공통 도메인으로 승격한다.
- DB 변경은 migration-first로 운영한다.
- 마이그레이션 도구는 Alembic으로 고정한다.
- 3단계에서 레거시 경로 래퍼는 두지 않고, 기존 경로 참조를 전수 수정한다.

## 3) 단계별 실행 계획

### 0단계: 의사결정 고정

- ADR 문서 2개 확정
  - `docs/monorepo/adr-001-repo-structure.md`
  - `docs/monorepo/adr-002-db-governance.md`
- 확정 항목
  - 디렉토리 책임 경계
  - DB 변경 승인/리뷰 정책
  - 배포 정책(저장소 단일, 릴리즈 앱 단위)

완료 기준
- ADR 승인 완료

### 1단계: 골격 구축

- 골격 디렉토리 정의
  - `apps/ingest-databatcher/`
  - `db/compose/`, `db/init/`, `db/migrations/`, `db/docs/`
  - `packages/shared-db-client/`
- 루트 `.env` 단일 소스 원칙을 문서에 고정
- CI path-based 실행 규칙 설계

완료 기준
- 골격/문서/CI 설계안 반영, 기존 로직 영향 없음

### 2단계: DB 도메인 분리

- 순서 고정
  1) baseline migration 생성
  2) DB 자산 정리(`mysql-standalone`, init 스키마, 운영 스크립트)
  3) `db/` 기준 실행 흐름 통일
- baseline 의미
  - 현재 스키마를 기준점으로 고정해 이후 변경 이력을 마이그레이션으로 관리

완료 기준
- `db` 도메인만으로 기동/초기화/마이그레이션/백업/복구가 가능

### 3단계: DataBatcher 이관

- 코드와 엔트리포인트를 `apps/ingest-databatcher/` 기준으로 재배치
- 기존 경로 참조를 전수 스캔해 새 경로로 일괄 변경
  - 대상: `apps/ingest-databatcher/ops/shell/`, `scheduler/`, `docs/`, `README`, 테스트, CI
- 레거시 래퍼는 두지 않는다

완료 기준
- 구경로 참조 0건
- 소규모 daily/weekly/bulk 테스트 통과

### 5단계: 거버넌스/품질 최소셋

- CODEOWNERS 정책 초안
- PR 템플릿(스키마 변경 체크리스트)
- DB 변경 정책(backward-compatible: 확장 -> 전환 -> 정리)

완료 기준
- DB 변경 시 승인 기준과 체크리스트가 문서/절차로 고정

## 4) 테스트 원칙 (필수)

- DB 필요 테스트는 `3307`만 사용
- 코드/설정값에 `3307` 저장 금지
- 테스트는 실행 성공 외에 DB 적재 검증까지 수행
  - row count
  - 샘플 데이터 조회
  - 최신 날짜/주차 확인
- 테스트 종료 후 `3307` 컨테이너 down, 기존 `3306`은 비침범 유지

## 5) 단계 게이트 실패 시 처리

- 2단계 실패: DB 도메인 변경만 롤백, 3단계 진행 금지
- 3단계 실패: 경로 이관 변경만 롤백, 구경로 참조 0건 재검증 후 재시도

## 6) 참고 문서

- `docs/monorepo/adr-001-repo-structure.md`
- `docs/monorepo/adr-002-db-governance.md`
- `docs/monorepo/phase-execution-checklist.md`
