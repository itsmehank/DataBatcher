# 모노레포 전환 작업 인수인계 (다음 OpenCode 세션용)

이 문서는 현재까지의 작업 결과와 다음 작업 우선순위를 정리한 인수인계 문서다.
다음 세션에서는 이 파일만 읽고 이어서 진행할 수 있도록 맥락/제약/검증 방법을 포함한다.

---

## 1) 프로젝트/목표 요약

- 현재 레포: `DataBatcher` (Python 배치 + MySQL)
- 목표: 모노레포 전환(외부 프로젝트 병합은 보류)
- 이번 전환 범위:
  - 진행: 0~3단계 + 5단계 최소셋
  - 보류: 4단계(외부 프로젝트 병합)

핵심 원칙:

- DB는 공통 도메인(`db/`)으로 승격
- DB 변경은 migration-first
- migration 도구는 Alembic으로 고정
- 테스트 DB는 런타임 오버라이드로만 `3307` 사용
- 코드/설정 파일에 `3307` 고정값 반영 금지
- 테스트 종료 시 `3307` 컨테이너 제거, 기존 `3306`은 비침범 유지

---

## 2) 현재까지 완료된 작업

### A. 계획/정책 문서화 완료

- `docs/make_mono_repo_plan.md`
- `docs/monorepo/adr-001-repo-structure.md`
- `docs/monorepo/adr-002-db-governance.md`
- `docs/monorepo/phase-execution-checklist.md`

요약:

- 단계별 계획(0~3,5) 확정
- Alembic baseline 선행 정책 확정
- 레거시 래퍼 미사용, 구경로 참조 전수 수정 정책 확정

### B. 골격 구조 생성 완료(1단계)

- `apps/README.md`
- `apps/ingest-databatcher/README.md`
- `db/README.md`
- `db/compose/.gitkeep`
- `db/init/.gitkeep`
- `db/migrations/.gitkeep`
- `db/docs/.gitkeep`
- `packages/README.md`
- `packages/shared-db-client/.gitkeep`

### C. Alembic baseline 도입 완료(2단계 준비)

- `requirements.txt`에 `alembic>=1.13.2` 추가
- `db/migrations/alembic.ini`
- `db/migrations/env.py`
- `db/migrations/script.py.mako`
- `db/migrations/README.md`
- `db/migrations/versions/20260313_000001_baseline_schema.py`

중요:

- baseline revision: `20260313_000001`
- baseline은 “현재 스키마 기준점 고정” 목적이며 `upgrade()/downgrade()`는 no-op

### D. 단계 테스트 및 보고 완료

- 보고서: `docs/monorepo/stage-test-report-20260313.md`
- 3307 테스트에서 확인한 것:
  - `init_db.py` 성공
  - alembic upgrade head 성공
  - `alembic_version` 생성 및 revision 기록 확인
  - KR 최소 파이프라인(bulk/daily/weekly 소규모) 실행 및 DB 적재 확인

### E. 거버넌스 최소셋 초안 완료

- `docs/monorepo/codeowners-proposal.md` (참고용)
- `docs/monorepo/pr-checklist-template.md` (참고용)

---

## 3) 이미 반영된 커밋

최신순이 아니라 전환 단계순:

1. `0675da5` 모노레포 전환 기준 문서/체크리스트 확정
2. `c52f56e` 1단계 골격 디렉토리/안내 문서 추가
3. `7df9b43` Alembic baseline 도입
4. `eeef17b` 2~3단계 테스트 결과 문서화
5. `8ce3c66` CODEOWNERS/PR 체크리스트 초안 문서화

참고:

- 커밋 메시지에 `Alebmic` 오타가 포함된 커밋이 있음(`7df9b43`)
- 기능 영향은 없고 메시지 오타만 존재

---

## 4) 현재 상태 요약

- 코드/문서 변경: 위 커밋들로 반영 완료
- 외부 프로젝트 병합: 아직 시작하지 않음(의도적 보류)
- DataBatcher 실제 코드 이관(`apps/ingest-databatcher`로 파일 이동): 완료
- 운영 스크립트/핵심 문서 경로 교체: 1차 완료
- `.github/CODEOWNERS` 실파일 반영: 개인 프로젝트 기준 미사용(삭제)
- PR 템플릿 실파일 반영: 개인 프로젝트 기준 미사용(삭제)

업데이트:

- 개인 프로젝트 기준으로 `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`는 제거
- `docs/monorepo/path-reference-inventory.md` 생성 완료

실행 시작 전 확인 권장:

- 브랜치: `main`
- 워킹트리: clean 상태인지 먼저 확인(`git status --short`)
- Python 환경: `.venv` 활성화 후 작업
- 기존 운영 DB(3306) 상태: `grafana-with-db-mysql` 유지

---

## 5) 다음 세션에서 해야 할 작업 (우선순위)

### P0. 경로 참조 인벤토리 갱신

목표: 남은 구경로 참조를 재분류해 잔여 수정 범위를 확정

- 검색 대상
  - `apps/ingest-databatcher/ops/shell/`
  - `scheduler/`
  - `README.md`, `docs/`
  - 테스트/CI 설정 파일
- 찾을 패턴 예시
  - `apps/ingest-databatcher/scripts/`
  - `core/`, `collectors/`, `indicators/`, `savers/`, `config/`의 상대 경로 의존
- 산출물
  - `docs/monorepo/path-reference-inventory.md` (기존 파일 업데이트)

바로 실행용 명령 예시:

```bash
grep -RIn "apps/ingest-databatcher/scripts/\|core/\|collectors/\|indicators/\|savers/\|config/" shell_scripts scheduler docs README.md .github tests
```

### P1. 잔여 호출 경로 정리

- 남아있는 `scripts/`/`tests/` 구경로를 문서/가이드 중심으로 정리
- 운영에 영향을 주는 파일(스케줄러, 실행 스크립트, README)을 우선 처리

### P2. CI/테스트 명령 경로 동기화

- pytest/스크립트 테스트 명령을 `apps/ingest-databatcher/...` 기준으로 통일
- `AGENTS.md`, `README.md`, 운영 가이드의 명령어 일치 여부 점검

검증 명령 예시:

```bash
grep -RIn "apps/ingest-databatcher/scripts/\|core/\|collectors/\|indicators/\|savers/\|config/" shell_scripts scheduler docs README.md .github tests
```

주의: 과거 회고/분석 문서의 문자열은 false positive로 분리해 관리한다.

### P3. 거버넌스 적용 방식 결정

- 개인 프로젝트면 문서 템플릿만 유지하고 `.github/*` 적용은 생략
- 팀 프로젝트로 전환 시 아래를 재적용
  - `docs/monorepo/codeowners-proposal.md` 기반 `.github/CODEOWNERS`
  - `docs/monorepo/pr-checklist-template.md` 기반 `.github/PULL_REQUEST_TEMPLATE.md`

상태: 개인 프로젝트 기준 생략

추가 후속(팀 전환 시):

- CODEOWNERS owner를 실제 GitHub 사용자/팀으로 치환

---

## 6) 테스트 실행 규칙 (다음 세션 필수 준수)

### 3307 테스트 규칙

- DB 필요 테스트는 아래 방식으로만 수행

```bash
MYSQL_PORT=3307 docker compose -f mysql-standalone/docker-compose-mysql.yaml --env-file .env up -d
DATABASE_URL="mysql+pymysql://hank:1234!@127.0.0.1:3307/trade?charset=utf8mb4" <테스트 명령>
```

- 절대 금지
  - `.env`의 `MYSQL_PORT`/`DATABASE_URL`를 3307로 저장
  - 코드 파일에 3307 하드코딩

### 소규모 테스트 기준

- bulk: `--top 1 --workers 1 --start=end(1일)`
- daily/weekly: 심볼 1개 또는 top 1
- 검증은 실행 성공만이 아니라 DB 적재 확인까지 수행
  - row count
  - 샘플 최신 레코드 조회

### 종료 절차

```bash
MYSQL_PORT=3307 docker compose -f mysql-standalone/docker-compose-mysql.yaml --env-file .env down -v
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

- `grafana-with-db-mysql`(3306) 유지 여부 확인 필수

---

## 7) 리스크/주의사항

- 3단계는 경로 이관 영향도가 높음
  - import 경로/스크립트 실행 위치/스케줄러 호출 경로 깨질 수 있음
- 전수 수정 누락 시 야간 배치 실패 가능
- DB 관련 변경은 반드시 backward-compatible 원칙 유지

이미 관측된 실패 패턴(정상/비정상 구분용):

- `sync_symbol_master.py` 실행 시 pykrx 실패 후 KIND fallback은 발생 가능(치명적 아님)
- `*_minervini_update.py`는 RS rating 데이터 부족 시 실패할 수 있음
  - 원인: 최소 테스트(1심볼/1일)에서 rs_rating 필터 조건 미충족
  - 대응: 테스트 목적에서는 expected failure로 분류하거나, RS 데이터 확보 후 재실행

롤백 원칙:

- 2단계 실패: migration/DB 구조 변경만 롤백
- 3단계 실패: 경로 이관 변경만 롤백
- 공통: 3307 테스트 자원은 항상 `down -v`로 정리

권장 순서:

1) 인벤토리 작성
2) 소규모 단위 이동 + 테스트
3) 전체 경로 교체
4) 3307 통합 스모크
5) 문서/CI 최종 정리

---

## 8) 참고 문서

- `docs/make_mono_repo_plan.md`
- `docs/monorepo/adr-001-repo-structure.md`
- `docs/monorepo/adr-002-db-governance.md`
- `docs/monorepo/phase-execution-checklist.md`
- `docs/monorepo/stage-test-report-20260313.md`
- `docs/monorepo/codeowners-proposal.md`
- `docs/monorepo/pr-checklist-template.md`

---

## 9) 다음 세션 시작용 빠른 루틴

아래 순서로 시작하면 컨텍스트 누락 없이 이어서 진행 가능:

1. `git log --oneline -8`로 최근 전환 커밋 확인
2. `git status --short`로 워킹트리 clean 확인
3. 본 문서의 P0 인벤토리부터 수행
4. DB 테스트 필요 시 3307 임시 기동 후 소규모 테스트
5. 종료 시 3307 정리 + 3306 생존 확인
