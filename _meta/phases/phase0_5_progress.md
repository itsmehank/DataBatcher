# P0.5 — 미너비니 스크리너 개편 진행 기록

> 작성: Builder (Claude Code CLI)  
> 날짜: 2026-04-24  
> 브랜치: `phase0_5/screener-refactor`  
> 커밋: `410b5ac`

---

## 1. 작업 결과 요약

### 완료된 것

| 항목 | 상태 | 비고 |
|---|---|---|
| 브랜치 `phase0_5/screener-refactor` 생성 | ✅ | |
| SQL 마이그레이션 파일 작성 | ✅ | `scripts/migrations/add_conditions_met_column.sql` |
| Alembic 버전 파일 작성 | ✅ | `db/migrations/versions/20260424_000001_add_conditions_met_column.py` |
| `trend_template.py` 리팩토링 | ✅ | `_compute_condition_masks()` 추가, 3-tuple 반환으로 변경 |
| `kr_minervini_update.py` 수정 | ✅ | `conditions_met` JSON 저장 |
| `us_minervini_update.py` 수정 | ✅ | `conditions_met` JSON 저장 |
| 테스트 DB 마이그레이션 적용 | ✅ | `trade_test` |
| 테스트 DB 실행 검증 | ✅ | KR 95건, US 78건 저장 확인. 8개 키 모두 `true` |
| 기존 pytest 47개 통과 | ✅ | 4개 에러는 pre-existing fixture 문제 |
| `trading-view-project` 영향 없음 확인 | ✅ | 정적 분석: 명시적 컬럼 SELECT로 신규 컬럼 무영향 |
| 프로덕션 DB 마이그레이션 적용 | ✅ | `trade.minervini_screen_results_kr/us` |
| 프로덕션 Alembic stamp | ✅ | `20260424_000001 (head)` |
| 프로덕션 1일치 재실행 | ⏳ | 기존 레코드는 INSERT ONLY로 스킵됨 (아래 설명 참조) |
| 커밋 완료 | ✅ | `phase0_5/screener-refactor` 브랜치 |

### ⏳ "1일치 신규 데이터 conditions_met 채움" 상태

`--days 1` 실행 결과 KR/US 모두 `conditions_met IS NULL`. 원인:

- 프로덕션 DB의 최신 가격·RS 데이터가 KR 2026-04-02, US 2026-04-10까지만 적재돼 있음 (daily cron이 그 이후 미실행)
- `INSERT ONLY` 모드는 `(symbol, date, screen_config_hash)` PK가 이미 존재하면 스킵
- 따라서 마이그레이션 이전에 적재된 레코드는 `conditions_met = NULL`로 남음

**이는 brief §1.4 "기존 데이터 소급 백필 하지 않음" 정책에 따른 정상 결과**다.  
다음 daily cron(`kr_rs_update.py` → `kr_minervini_update.py`)이 실행되는 날부터 신규 레코드에 `conditions_met`가 채워진다.

---

## 2. 변경된 파일 목록

```
apps/ingest-databatcher/indicators/minervini/trend_template.py   (수정)
apps/ingest-databatcher/scripts/kr_minervini_update.py           (수정)
apps/ingest-databatcher/scripts/us_minervini_update.py           (수정)
apps/ingest-databatcher/scripts/migrations/add_conditions_met_column.sql  (신규)
db/migrations/versions/20260424_000001_add_conditions_met_column.py       (신규)
```

---

## 3. 코드 변경 핵심 내용

### `trend_template.py`

- `_compute_condition_masks()` 신규 추가: 8조건을 각각 독립 boolean DataFrame으로 계산
- `screen_minervini_trend_template()` 반환값을 `(pass_mask, failed_reasons)` 2-tuple → `(pass_mask, failed_reasons, conditions)` 3-tuple로 확장
- `pass_mask`는 기존과 동일하게 filter toggle을 반영. `conditions` dict는 toggle 무관하게 항상 8개 키를 포함 (LLM이 전체 구조를 볼 수 있도록)
- 기존 `ma_ordering` 필터가 합쳐서 평가하던 4개 조건(`price > sma50 > sma150 > sma200`)을 분해:
  - `price_above_ma150_ma200`
  - `ma150_above_ma200`
  - `ma50_above_ma150_ma200`
  - `price_above_ma50`

### `kr/us_minervini_update.py`

- `screen_minervini_trend_template()` 호출을 3-tuple 언팩킹으로 변경
- `_build_conditions_met()` 헬퍼 함수 추가: 각 `(symbol, date)` 쌍에 대해 8개 조건 pass/fail을 JSON 문자열로 직렬화
- `result_df`에 `conditions_met` 컬럼 추가

### 스키마 변경

```sql
ALTER TABLE minervini_screen_results_kr
  ADD COLUMN conditions_met JSON NULL COMMENT 'ADR-009: per-condition pass/fail map'
  AFTER is_blue_dot;

ALTER TABLE minervini_screen_results_us
  ADD COLUMN conditions_met JSON NULL COMMENT 'ADR-009: per-condition pass/fail map'
  AFTER is_blue_dot;
```

---

## 4. 발견된 불일치 사항 (수정 없이 보고)

작업 중 `_meta/` 문서 및 실제 환경과의 불일치를 발견했다. ADR-005에 따라 수정하지 않고 기록만 한다.

### 4-1. 테스트 DB `stock_prices`에 `currency` 컬럼 잔존

- **현상**: `trade_test.stock_prices`에 `currency VARCHAR(8)` 컬럼이 존재. 프로덕션(`trade.stock_prices`)에는 없음.
- **원인**: `scripts/migrations/remove_currency_column.sql`이 테스트 DB에 미적용.
- **영향**: 테스트 DB로 프로덕션 데이터를 `SELECT *`로 복사 시 컬럼 수 불일치 에러 발생. 컬럼 명시로 우회 가능.

### 4-2. `scripts/migrations/*.sql` 파일이 Alembic 체인 밖에 있음

- **현상**: `scripts/migrations/`에는 KR 지수, US 지수, 섹터 컬럼 추가, currency 제거 등 다수의 SQL 파일이 있지만, `db/migrations/versions/`에 대응 파이썬 파일이 없음.
- **영향**: `alembic upgrade head`만으로는 이 파일들의 변경이 적용되지 않음. 새 환경 셋업 시 수동 SQL 실행이 필요한지 여부가 불명확.
- **이번 작업**: P0.5 마이그레이션은 두 파일을 동시에 작성하는 방식으로 처리.

### 4-3. 기존 설치 환경의 Alembic 미추적 상태

- **현상**: 이번 작업 전 프로덕션 DB에 `alembic_version` 테이블이 없었음. Alembic 체계가 있음에도 프로덕션이 추적되지 않은 상태.
- **조치**: 수동으로 `alembic stamp 20260424_000001` 실행. 이후 `current` = `20260424_000001 (head)` 확인.
- **의미**: 다른 환경(윈도우 PC 등)에서 git pull 후 `alembic upgrade head`를 실행하면 `alembic_version` 테이블이 없어 baseline부터 재실행을 시도할 수 있음.

---

## 5. 마이그레이션 관리 제안

### 현재 체계 (As-Is)

```
scripts/migrations/*.sql   ← 수동 실행. 적용 여부 추적 없음.
db/migrations/versions/*.py ← Alembic. DB의 alembic_version 테이블로 추적.
```

두 시스템이 **분리·비연동** 상태. 어느 SQL 파일이 어느 환경에 적용됐는지 알 수 없다.

### 권장 방향 (To-Be)

**원칙: 스키마 변경은 Alembic 파일 하나로 일원화.**  
`scripts/migrations/*.sql`은 참고용(사람이 읽기 쉬운 raw SQL)으로 유지하되, 실제 적용은 항상 Alembic으로 한다.

```
┌─────────────────────────────┐
│  스키마 변경 필요             │
└────────────┬────────────────┘
             │
             ▼
  scripts/migrations/YYYYMMDD_xxx.sql   ← 사람이 검토할 raw SQL (선택)
  db/migrations/versions/YYYYMMDD_NNN_xxx.py  ← Alembic 버전 (필수)
             │
             ▼
  alembic upgrade head  ← 모든 환경에서 동일 명령으로 적용
```

### 새 환경 셋업 표준 절차 (제안)

```bash
# 1. 코드 클론 또는 pull
git clone <repo> && cd DataBatcher

# 2. DB 초기화 (init_db.py가 baseline 스키마 생성)
python apps/ingest-databatcher/scripts/init_db.py

# 3. Alembic으로 이후 변경 적용
DATABASE_URL="mysql+pymysql://USER:PASS@HOST:3306/trade?charset=utf8mb4" \
  alembic -c db/migrations/alembic.ini upgrade head
```

### 기존 환경(미추적) 마이그레이션 수동 stamp 절차

```bash
# 현재 추적 상태 확인
alembic -c db/migrations/alembic.ini current

# 아무것도 안 나오면 → 현재 스키마에 맞는 revision을 stamp
# baseline만 있는 환경 (users 테이블 없음):
alembic -c db/migrations/alembic.ini stamp 20260313_000001
# users 테이블 있지만 conditions_met 없는 환경:
alembic -c db/migrations/alembic.ini stamp 20260319_000001
# conditions_met까지 있는 환경 (최신):
alembic -c db/migrations/alembic.ini stamp 20260424_000001

# 그 후 누락된 마이그레이션만 적용
alembic -c db/migrations/alembic.ini upgrade head
```

### README/CLAUDE.md 보완 제안

`CLAUDE.md`의 "Environment Setup" 섹션에 아래를 추가하면 새 기여자가 바로 따라올 수 있다:

```bash
# 스키마 마이그레이션 (DB 초기화 이후 또는 git pull 이후)
DATABASE_URL="..." alembic -c db/migrations/alembic.ini upgrade head
```

---

## 6. 다음 단계

1. **PR 머지**: `phase0_5/screener-refactor` → `main` (사용자 직접 또는 CLI에서 요청)
2. **`_meta/06_CURRENT_STATE.md` 갱신**: "P0.5 완료" 기록 — Architect 세션에서 수행
3. **마이그레이션 관리 개선 결정**: 4-2, 4-3 불일치 사항 처리 여부 — Architect 세션에서 ADR 형태로 결정
4. **테스트 DB currency 컬럼 정리**: `remove_currency_column.sql`을 테스트 DB에 적용 여부 — 별도 결정
5. **Phase 1 brief 작성**: Architect 세션에서 시작

---

*이 기록은 `_meta/00_CONSTITUTION.md` §5에 따라 Builder가 작성한 Phase 진행 로그다.*