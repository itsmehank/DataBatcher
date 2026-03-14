# 모노레포 전환 실행 체크리스트

## 공통 테스트 변수

```bash
TEST_DB_URL="mysql+pymysql://hank:1234!@127.0.0.1:3307/trade?charset=utf8mb4"
```

## 0단계

- [ ] ADR-001 승인
- [ ] ADR-002 승인

## 1단계

- [ ] 골격 구조 반영(`apps/`, `db/`, `packages/`)
- [ ] 루트 `.env` 단일 소스 원칙 문서 반영
- [ ] CI path-based 설계 문서 반영

## 2단계

- [ ] baseline migration 생성
- [ ] DB 자산 `db/` 도메인으로 정리
- [ ] 백업/복구 경로 통일

DB 테스트(3307)

```bash
MYSQL_PORT=3307 docker compose -f mysql-standalone/docker-compose-mysql.yaml --env-file .env up -d
DATABASE_URL="$TEST_DB_URL" python apps/ingest-databatcher/scripts/init_db.py
DATABASE_URL="$TEST_DB_URL" bash shell_scripts/db_backup_monthly.sh
```

검증(예시)

```bash
DATABASE_URL="$TEST_DB_URL" python - <<'PY'
from sqlalchemy import create_engine, text
import os
e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    print(c.execute(text("SELECT COUNT(*) FROM stock_prices")).scalar())
PY
```

## 3단계

- [ ] `apps/ingest-databatcher` 이관
- [ ] 구경로 참조 전수 변경(문서/스크립트/스케줄러/CI/테스트)
- [ ] 구경로 참조 0건 검증

소규모 실행 테스트(3307)

```bash
DATABASE_URL="$TEST_DB_URL" python apps/ingest-databatcher/scripts/bulk_update.py --start 2026-03-12 --end 2026-03-12 --market KOSPI --top 1 --workers 1
DATABASE_URL="$TEST_DB_URL" python apps/ingest-databatcher/scripts/daily_update.py --all --market KOSPI --top 1
DATABASE_URL="$TEST_DB_URL" python apps/ingest-databatcher/scripts/weekly_update.py --all --market KOSPI --top 1
```

## 5단계 최소셋 (옵션)

- [ ] 팀 프로젝트라면 CODEOWNERS 정책 반영
- [ ] 팀 프로젝트라면 PR 체크리스트 반영
- [ ] DB 변경 정책 문서화

## 종료 절차(항상)

```bash
MYSQL_PORT=3307 docker compose -f mysql-standalone/docker-compose-mysql.yaml --env-file .env down -v
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

- [ ] 테스트용 `3307` 정리 완료
- [ ] 기존 `3306` 서비스 정상 유지 확인
