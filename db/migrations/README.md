# Alembic Migrations

이 디렉토리는 DataBatcher 공통 DB 스키마 변경 이력을 관리한다.

- baseline: 현재 스키마 기준점(초기 마이그레이션)
- 이후 변경: `versions/`에 순차 추가

실행 예시(루트에서):

```bash
DATABASE_URL="mysql+pymysql://user:pass@127.0.0.1:3307/trade?charset=utf8mb4" alembic -c db/migrations/alembic.ini upgrade head
```
