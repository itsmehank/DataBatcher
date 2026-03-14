# ADR-001: 모노레포 구조

## 상태

승인(Approved)

## 결정

저장소를 아래 논리 구조로 운영한다.

- `apps/`: 실행 애플리케이션
- `db/`: 공통 DB 자산(compose/init/migrations/docs)
- `packages/`: 공통 코드
- `apps/ingest-databatcher/scripts/`: 운영/개발 스크립트

초기 전환 범위는 `apps/ingest-databatcher` 중심이며, 외부 프로젝트 병합은 후속 단계로 분리한다.

## 근거

- 스키마 변경과 앱 변경을 하나의 PR 단위로 관리 가능
- AI-assisted 개발에서 전체 문맥 추적 효율 증가
- DB 소유권을 특정 앱에서 분리해 공통 도메인으로 승격 가능

## 비결정 항목

- 외부 프로젝트 병합 시점/방법은 별도 ADR에서 결정

## 영향

- 문서/CI/실행 경로가 새 구조를 기준으로 정렬되어야 함
- 3단계에서 기존 경로 참조를 일괄 교체해야 함
