# 외부 프로젝트 병합 가이드 (Monorepo Phase 4)

이 문서는 DataBatcher 모노레포에 **외부 프로젝트를 병합**할 때 참고하는 실행 가이드다.

대상 독자:
- 다음 세션에서 외부 레포를 병합할 작업자
- 병합 후 경로/테스트/릴리즈 검증을 수행할 작업자

---

## 0) 병합 원칙

- 저장소는 하나여도 앱은 독립적으로 유지한다.
- 공통 자산만 루트(`db/`, `packages/`, `docs/shared/`)에 둔다.
- 앱 전용 자산은 반드시 `apps/<project-name>/` 아래로 넣는다.
- 병합 직후에도 기존 앱(DataBatcher) 동작이 깨지지 않아야 한다.

권장 디렉토리 구조:

```text
apps/
  ingest-databatcher/
  <external-project-a>/
  <external-project-b>/
db/
packages/
docs/shared/
```

---

## 1) 사전 준비 체크리스트

### 1.1 병합 대상 정보 정리

- 레포 URL / 기본 브랜치
- 런타임 언어/버전
- 필수 ENV 목록
- DB 의존 여부(테이블, 마이그레이션, 읽기/쓰기)
- 배포 방식(수동/CI/CD)

### 1.2 충돌 가능성 사전 점검

- 동일 파일명/디렉토리명 충돌 여부
- 공통 포트 충돌 여부
- `.env` 키 중복/충돌 여부
- DB 스키마 충돌 여부(테이블명/컬럼명)

### 1.3 브랜치 전략

- 작업 브랜치: `merge/<project-name>-into-monorepo`
- 병합 단위를 1개 프로젝트씩 분리

### 1.4 작업 시작 전 안전 체크

- `git status --short`가 비어있는지 확인
- 작업 브랜치가 `merge/<project-name>-into-monorepo`인지 확인
- 복구 지점 확보를 위해 태그 생성

```bash
git tag pre-merge-<project-name>-$(date +%Y%m%d)
```

---

## 2) 병합 방식 선택

### 옵션 A: 히스토리 보존 병합 (권장)

히스토리 추적이 필요할 때 사용.

예시 흐름:

```bash
git remote add ext-foo <external_repo_url>
git fetch ext-foo
git subtree add --prefix apps/<project-name> ext-foo <branch>
```

### 옵션 B: 스쿼시 병합

히스토리보다 빠른 통합이 필요할 때 사용.

예시 흐름:

```bash
git remote add ext-foo <external_repo_url>
git fetch ext-foo
git subtree add --prefix apps/<project-name> ext-foo <branch> --squash
```

주의:
- 어떤 방식을 쓰든 `apps/<project-name>/` prefix를 강제한다.
- 병합 후 로컬 remote 정리 권장:

```bash
git remote remove ext-foo
```

---

## 3) 병합 직후 정리 작업

### 3.1 경로/명령 정합화

- 문서의 `python scripts/...` 같은 구명령을 `apps/<project-name>/...` 기준으로 수정
- 운영 스크립트 경로를 `apps/<project-name>/ops/...`로 맞춤
- 스케줄러 파일이 있으면 `apps/<project-name>/ops/scheduler/...`로 배치

### 3.2 설정 정리

- 앱 설정은 `apps/<project-name>/config/`에 배치
- 루트 `.env`와 키 충돌 시 접두어 네이밍 규칙 도입
  - 예: `FOO_DB_URL`, `BAR_DB_URL`

### 3.3 DB 계약 정리

- 외부 프로젝트가 DB를 쓰면 아래 중 하나를 선택
  1) 기존 `db/migrations`에 migration 추가
  2) 프로젝트 전용 schema/table namespace를 명확히 분리

---

## 4) 테스트 전략 (필수)

### 4.1 공통 규칙

- DB 통합 테스트는 임시 포트(예: `3307`) 런타임 오버라이드로만 수행
- 코드/설정 파일에 테스트 포트 고정 금지
- 테스트 종료 후 임시 DB `down -v` 필수
- 포트 충돌 시 `3308` 등으로 대체 가능(문서/코드에는 고정 반영 금지)

### 4.2 최소 스모크 시나리오

1. DB 기동(3307)
2. 스키마 초기화 + migration 적용
3. 외부 프로젝트 핵심 진입 명령 1~2개 실행
4. DB 적재/조회 검증(row count, 샘플 1건)
5. 임시 DB 종료

예시 명령:

```bash
MYSQL_PORT=3307 docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml --env-file .env up -d
DATABASE_URL='mysql+pymysql://<user>:<pass>@127.0.0.1:3307/<db>?charset=utf8mb4' python apps/ingest-databatcher/scripts/init_db.py
DATABASE_URL='mysql+pymysql://<user>:<pass>@127.0.0.1:3307/<db>?charset=utf8mb4' alembic -c db/migrations/alembic.ini upgrade head
DATABASE_URL='mysql+pymysql://<user>:<pass>@127.0.0.1:3307/<db>?charset=utf8mb4' python apps/<project-name>/scripts/<entry>.py
MYSQL_PORT=3307 docker compose -f db/compose/mysql-standalone/docker-compose-mysql.yaml --env-file .env down -v
```

---

## 5) 커밋/롤백 전략

병합 작업은 아래 단위로 쪼개서 커밋한다.

1. `chore: <project-name> 소스 병합`
2. `refactor: 경로/설정/ops 정합화`
3. `test: 통합 스모크 결과 반영`
4. `docs: 사용 가이드 업데이트`

이유:
- 실패 시 특정 단계만 `revert` 가능
- 코드 리뷰 범위가 명확해짐

---

## 6) 병합 완료 판정 (Definition of Done)

- [ ] 외부 프로젝트 코드가 `apps/<project-name>/` 아래에만 위치
- [ ] 실행/설정/스케줄러 경로 정합화 완료
- [ ] 문서 명령이 실제 경로 기준으로 동작
- [ ] 3307 통합 스모크 테스트 통과
- [ ] 임시 DB 정리 + 기존 3306 서비스 비침범 확인
- [ ] 기존 `apps/ingest-databatcher` 회귀 스모크 테스트 통과
- [ ] 단계별 커밋으로 롤백 가능 상태 확보

---

## 7) 자주 발생하는 실수

- 루트에 외부 프로젝트 파일을 직접 풀어놓음
- 문서는 바뀌었는데 스케줄러/ops 경로는 미반영
- 테스트 포트(3307)를 코드에 하드코딩함
- DB migration 없이 테이블을 수동 생성함
- 한 커밋에 병합/리팩토링/문서/테스트를 다 섞음

---

## 8) 권장 후속 문서

- `docs/shared/monorepo/NEXT_SESSION_HANDOFF.md`
- `docs/shared/monorepo/phase-execution-checklist.md`
- 외부 프로젝트별로 `apps/<project-name>/README.md` 신규 작성
