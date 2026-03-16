## trading-view-project 병합 후 검증 리포트 (2026-03-16)

### 범위
- 대상: `apps/trading-view-project`
- 목적: 모노레포 경로 정합성, Docker 실행성, 백엔드/프론트 테스트 통과, 기존 ingest 회귀 최소 확인

### 이번 변경점
- `apps/trading-view-project/docker-compose.yml`
  - backend 환경 변수 주입을 `environment`에서 `env_file`(`./backend/.env`) 기반으로 전환
  - 포트 매핑을 `BACKEND_PORT`, `FRONTEND_PORT` 기반으로 변경
- `apps/trading-view-project/backend/.env.example`
  - `BACKEND_PORT`, `FRONTEND_PORT` 추가
  - `STARTUP_DB_CHECK` 추가, Docker 접속용 `DATABASE_URL` 예시 주석 보강
- `apps/trading-view-project/backend/app/config.py`
  - 컨테이너 환경에서 부모 경로 깊이 가정(`parents[3]`) 제거
  - 상위 디렉터리 순회 방식으로 `.env` 탐색하도록 보강
- `apps/trading-view-project/backend/app/main.py`
  - FastAPI lifespan에서 startup DB 연결 체크(`STARTUP_DB_CHECK=true` 기본)
- `apps/trading-view-project/backend/app/db.py`
  - startup fail-fast용 DB 연결 검증 함수 추가
- `apps/trading-view-project/backend/tests/conftest.py`
  - 테스트에서는 `STARTUP_DB_CHECK=false`로 startup check 비활성화
- `apps/trading-view-project/README.md`
  - 모노레포 루트 기준 실행 명령으로 정리
  - Docker 실행/중지 및 포트 충돌 대응 안내 추가
  - DB 계정 권한 부여 SQL / 권한 확인 / 필수 객체 점검 쿼리 추가

### 실행한 검증
1. Compose 정합성
   - 명령: `docker compose -f apps/trading-view-project/docker-compose.yml config`
   - 결과: 정상 출력, `${DATABASE_URL}` 경고 없음

2. Docker 기동/재기동
   - 명령: `docker compose -f apps/trading-view-project/docker-compose.yml up -d --build`
   - 결과: backend/frontend 컨테이너 정상 기동

3. 런타임 헬스 체크
    - 명령: `curl -I -sS http://localhost:5173`
    - 결과: `HTTP/1.1 200 OK`
    - 명령: `curl -sS "http://localhost:8000/api/health/db?region=US"`
    - 결과: `status=ok` 확인
    - 명령: `curl -sS "http://localhost:8000/api/options/markets?region=US"`
    - 결과: `200 OK` + 시장 목록(`ETF`, `NASDAQ`, `NYSE`) 확인

4. 백엔드 테스트
   - 위치: `apps/trading-view-project/backend`
   - 명령: `./.venv/bin/pytest -q`
   - 결과: `10 passed`

5. 프론트엔드 테스트/타입체크/빌드
   - 위치: `apps/trading-view-project/frontend`
   - 명령: `npm run test -- --run && npm run typecheck && npm run build`
   - 결과: 테스트 6 passed, typecheck 통과, build 통과

6. ingest-databatcher 최소 회귀
   - 명령: `pytest -q apps/ingest-databatcher/tests/test_pykrx_adapter.py::test_normalize_price_columns_basic`
   - 결과: `1 passed`

### 메모
- Docker 백엔드에서 `DATABASE_URL` host를 `127.0.0.1`로 두면 컨테이너 자기 자신을 가리켜 DB 연결이 실패함.
- 실제 실행 환경에서는 `host.docker.internal`(호스트 DB) 또는 동일 Docker 네트워크 서비스명(DB 컨테이너)을 사용해야 함.
