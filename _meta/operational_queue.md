# 운영 환경 작업 큐 (Operational Queue)

> 로컬에서 변경되었고 운영 환경(집 PC)에서도 적용이 필요한 작업을 기록한다.  
> 개발 환경과 운영 환경이 분리되어 있으므로, 코드 변경(git pull로 자동 반영)과 별개로 **DB 스키마·외부 설정·수동 마이그레이션** 등은 명시적으로 적용해야 한다.  
> 운영 환경에서 작업을 마치면 해당 항목을 "완료" 섹션으로 옮긴다.  
> 새 항목은 항상 "대기" 섹션 맨 위에 추가한다(최신순).
>
> 이 큐의 운영 방식은 ADR-010에서 정의된다.

---

## 환경 정보

### 개발 환경 (DEV)
- **디바이스**: Mac 노트북
- **OS**: macOS
- **셸**: bash / zsh
- **DataBatcher 경로**: (사용자가 채워넣을 것 — 예: `~/work/DataBatcher`)
- **DB**: 로컬 MySQL (Docker)
- **용도**: 코드 작성, 테스트 DB 검증, `_meta/` 문서 관리

### 운영 환경 (PROD)
- **디바이스**: 집 PC (24시간 가동)
- **OS**: Windows
- **셸**: PowerShell
- **스케줄러**: Windows Task Scheduler (`apps/ingest-databatcher/ops/scheduler/windows/*.ps1`)
- **DataBatcher 경로**: (사용자가 채워넣을 것 — 예: `C:\work\DataBatcher`)
- **DB**: MySQL 8.4.8 (Docker 컨테이너 — 컨테이너명 `mysql-standalone-mysql`)
  - 호스트에 `mysql`/`mysqldump` 클라이언트 없음 → 명령은 `docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" ...` 형태로 실행
- **MySQL 자격증명**: `.env`의 `MYSQL_ROOT_PASSWORD` 사용 (Q-001 적용 시 확인됨, 2026-04-26)
- **접속 방법**: 직접 / 원격 데스크톱 / SSH (사용자가 명시)
- **Daily cron 시각**:
  - US daily: 매일 08:00 KST 시작, 최대 6시간 소요 (~14:00 종료)
  - KR daily: 매일 19:00 KST 시작, 최대 30분 소요 (~19:30 종료)

> 비어 있는 항목은 처음 운영 환경 작업할 때 채워넣고 commit한다.

---

## 큐 운영 규칙

1. **새 항목은 "대기" 섹션 맨 위에 추가**. 형식은 Q-001을 템플릿으로 사용.
2. **위험도** 표시: 낮음(코드만, DB 무관) / 중간(DB 변경, 롤백 가능) / 높음(데이터 손실 가능, 백업 필수).
3. **타이밍 윈도우** 명시: cron 충돌 시간을 피해야 하는 작업은 안전 시각 명시.
4. **완료 후 이동**: 작업 완료 시 항목을 "완료" 섹션으로 이동, 완료일·확인 결과 추가.
5. **삭제 금지**: 완료된 항목도 삭제하지 않음. 운영 이력으로 남김.

---

## 대기 중인 작업

### Q-003: Phase 1 LLM 분석 모듈 운영 환경 적용 — Task Scheduler 등록 + 첫 자동 실행 검증 (등록: 2026-05-07)

**관련 commit**: `phase1/1.3-daily-analysis` 브랜치 머지 commit (머지 후 hash 기입). 1.3 작업 진입 시점 HEAD = `2ba0ef4`. 1.3.0~1.3.8 commits include `c2114f7` (v1.1 fix), `2ba0ef4` (progress 기록), 1.3.1~1.3.8 후속 commit.
**관련 ADR**: ADR-009 (스키마), ADR-011 (CLI 백엔드), ADR-012 (자동 트리거 + 모니터링 4종)
**선행 조건**: Q-002 PROD 적용 완료 (daily_analysis_kr/us, llm_calls 테이블 존재) — Q-002 미적용 시 본 항목도 진행 불가
**위험도**: 중간 (코드 변경 + Task Scheduler 등록 + 첫 자동 실행 시 LLM 호출 + DB write)
**예상 소요**: 30~60분 (등록 5분 + 첫 수동 dry-run 1분 + 첫 수동 소규모 실행 5~10분 + 다음 자동 트리거 시각 관찰 대기)
**타이밍 윈도우**: KR cron(19:00) · US cron(08:00 ~ 14:00 종료) 직후 30분을 피하면 어느 시각이든 안전. Task Scheduler 등록은 시각과 무관.

**사전 확인 (Q-002 적용 여부)**:

```powershell
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.daily_analysis_kr;"
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.daily_analysis_us;"
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.llm_calls;"
```

세 테이블 DESCRIBE이 phase1_brief §4.1·§4.2·§4.3 스키마와 일치해야 함. 미존재 시 Q-002부터 처리.

**적용 절차**:

```powershell
# 1. git pull
cd C:\path\to\DataBatcher    # 운영 PC 실제 경로로 치환
git checkout main
git pull origin main          # phase1 머지 후 main 기준; 미머지면 phase1/1.3-daily-analysis 직접 checkout

# 2. apps/llm-analysis/ 의존성 설치 (venv 생성 포함)
python -m venv apps\llm-analysis\venv
.\apps\llm-analysis\venv\Scripts\Activate.ps1
pip install -r apps\llm-analysis\requirements.txt
deactivate

# 3. apps/llm-analysis/.env 설정 (DATABASE_URL 등)
#    CLI 백엔드(default): Max 플랜 로그인 상태 확인 (claude code 설치 + 로그인)
#    API 백엔드(전환 시): ANTHROPIC_API_KEY 환경 변수 셋업

# 4. config/settings.yaml 검토 (Phase 1 production-ready 설정)
#    - llm_analysis.backend: "cli"
#    - daily_call_limits.enabled: true (필수, ADR-012 §3.1)
#    - daily_call_limits.hard_stop_on_exceed: true (필수)
#    - prompts.analyze_chart: "v2"
#    - prompts.calculate_entry_params: "v1_1"  (Phase 1.3.0 v1.1 production lock)
#    - modules.{analyze_chart, calculate_entry_params}: true

# 5. 첫 dry-run (Task Scheduler 등록 전 sanity check)
.\apps\llm-analysis\ops\scheduler\windows\run_analysis_today.ps1 -Region US -DryRun

# 6. 첫 소규모 실제 실행 (1~5종목, 비용·시간 인지)
.\apps\llm-analysis\ops\scheduler\windows\run_analysis_today.ps1 -Region US -Limit 1
#    또는 직접 호출:
.\apps\llm-analysis\venv\Scripts\python.exe `
  apps\llm-analysis\scripts\run_daily_analysis.py --region US --limit 1
#    완료 후 daily_analysis_us 신규 행 + llm_calls 호출 로그 + sync_log 'llm_analysis_us' running/success 행 확인

# 7. Task Scheduler 등록
.\apps\llm-analysis\ops\scheduler\windows\install_task.ps1
#    출력 표에 LLMAnalysis_KR, LLMAnalysis_US 두 작업 + State=Ready + NextRun 시각이 보여야 함

# 8. 등록 확인
Get-ScheduledTask -TaskName "LLMAnalysis_*"
Get-ScheduledTaskInfo -TaskName "LLMAnalysis_US"
Get-ScheduledTaskInfo -TaskName "LLMAnalysis_KR"

# 9. (관찰) 다음 자동 트리거 시각에 실제 실행 확인
#    US 16:00 KST 또는 KR 21:00 KST 도달 후:
Get-ScheduledTaskInfo -TaskName "LLMAnalysis_US"   # LastRunResult = 0 (성공) 확인
.\apps\llm-analysis\venv\Scripts\python.exe apps\llm-analysis\scripts\show_cost_summary.py --days 1
#    sync_log WARN/ERROR 없는지 확인 (있으면 즉시 보고)
```

**적용 후 검증 (체크리스트, ADR-012 §3 모니터링 4종 가동 확인)**:

```powershell
# 1) daily_call_limits hard_stop 작동 (수동 시뮬은 어려움 — settings.yaml에서 한도 0으로 일시 변경 후
#    소규모 실행 → DailyCallLimitExceeded 에러 + sync_log ERROR 기록 → 한도 원복)
# 2) sync_log 이상 기록 path 확인:
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "SELECT job_name, COUNT(*) FROM trade.sync_log WHERE job_name LIKE 'llm_%' GROUP BY job_name;"
# 3) 약관 위반 징후: show_cost_summary가 'Recent monitoring events' 섹션에 표시 (해당 기간 이벤트 없으면 (none))
# 4) 호출 로그 주간 점검:
.\apps\llm-analysis\venv\Scripts\python.exe apps\llm-analysis\scripts\show_cost_summary.py --days 7
```

**완료 기준**:
- Q-002 PROD 적용 완료 (선행 조건)
- LLMAnalysis_US, LLMAnalysis_KR 두 작업이 Task Scheduler에 등록됨 (`Get-ScheduledTask`로 확인)
- 첫 자동 실행이 정상 종료됨 (`Get-ScheduledTaskInfo`의 `LastRunResult = 0`)
- `daily_analysis_kr` 또는 `daily_analysis_us`에 결과 행 1개 이상 생성됨
- `llm_calls`에 호출 로그 1개 이상 남음
- `sync_log`에 `'llm_analysis_*' status='success'` 마커 1개 이상 남고, `WARN`/`ERROR` 없음 (또는 알려진 이상만)

**롤백 방법** (긴급 시):

```powershell
# (1) 일시 중단 (가장 가벼운 통제권 행사 — ADR-012 §5 메커니즘 1)
Disable-ScheduledTask -TaskName "LLMAnalysis_US"
Disable-ScheduledTask -TaskName "LLMAnalysis_KR"

# (2) 완전 삭제 (Q-003 자체를 되돌림)
Unregister-ScheduledTask -TaskName "LLMAnalysis_US" -Confirm:$false
Unregister-ScheduledTask -TaskName "LLMAnalysis_KR" -Confirm:$false

# (3) settings.yaml 킬 스위치 (작업은 트리거되되 LLM 호출 차단 — 메커니즘 2)
#     modules.analyze_chart: false  +  modules.calculate_entry_params: false
```

**메모**:
- Phase 1.3.0 v1.1 production lock 반영. (6) 프롬프트 v1.1 사용 — `stop_loss_pct_from_pivot`, `stop_loss_pct_from_current_price`, `trigger_price`, `observed_breakout_volume_ratio` 4 신규 필드 + auto-emit known_warnings 2종 (`stop_distance_from_current_price_exceeds_book_limit`, `breakout_volume_below_requirement`).
- 본 큐 항목은 §10.4 1번 예외에 따라 1.3 단계 한정으로 Builder가 직접 등록 (commit hash는 머지 시점에 갱신).
- ADR-011 §4 + ADR-012 §3.3 약관 위반 징후 발생 시 즉시 사용자에 보고 + ADR-012 §4 절차로 API 백엔드 전환 검토.

---

### Q-002: Phase 1 DB 마이그레이션 적용 — daily_analysis_kr, daily_analysis_us, llm_calls (등록: 2026-04-28)

**관련 commit**: `phase1/1.1-llm-analysis-skeleton` 브랜치 머지 commit (머지 후 hash 기입 예정)  
**관련 ADR**: ADR-009 (LLM 분석 테이블 설계), ADR-010 (마이그레이션 3종 산출물)  
**Alembic revision**: `20260428_000001` (down_revision: `20260424_000001`)  
**raw SQL 파일**: `db/migrations/sql/20260428_000001_add_daily_analysis_and_llm_calls.sql`  
**위험도**: 중간 (DB 변경 — CREATE TABLE 3개, 롤백 가능)  
**예상 소요**: 5분 미만 (CREATE TABLE 3개, 기존 테이블 없음)  
**타이밍 윈도우**: KR cron(19:00) · US cron(08:00) 각각 직전 30분을 피하면 어느 시각이든 안전

**적용 전 사전 확인**:

```powershell
# 1. git pull 상태 확인
cd C:\path\to\DataBatcher
git log --oneline -3

# 2. 대상 테이블 미존재 확인 (둘 다 빈 결과여야 함)
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "SHOW TABLES FROM trade LIKE 'daily_analysis%';"
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "SHOW TABLES FROM trade LIKE 'llm_calls';"
```

**적용 (raw SQL 직접 실행 — 이번에도 Alembic 미사용, 미해결 이슈 §G 유지)**:

```powershell
cd C:\path\to\DataBatcher
git pull

Get-Content db\migrations\sql\20260428_000001_add_daily_analysis_and_llm_calls.sql | `
  docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" trade
```

**적용 후 검증 (세 테이블 DESCRIBE)**:

```powershell
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.daily_analysis_kr;"
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.daily_analysis_us;"
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" `
  -e "DESCRIBE trade.llm_calls;"
```

**완료 기준**: 세 테이블의 DESCRIBE 결과가 `_meta/phases/phase1_brief.md` §4.1·§4.2·§4.3 스키마와 일치

**백업**: 생략 (Q-001과 동일 사유 — CREATE TABLE은 기존 데이터 무영향)

**롤백 방법**:

```powershell
docker exec -i mysql-standalone-mysql mysql -u root -p"$env:MYSQL_ROOT_PASSWORD" trade `
  -e "DROP TABLE IF EXISTS llm_calls; DROP TABLE IF EXISTS daily_analysis_us; DROP TABLE IF EXISTS daily_analysis_kr;"
```

**메모**:
- Alembic 적용은 이번에도 생략 (미해결 이슈 §G — PROD `alembic_version` 동기화 미해결). raw SQL만 적용.
- 미해결 이슈 §G 해소 시점(별도 결정)에 PROD stamp + upgrade head 일괄 처리 예정.
- 본 큐 항목의 텍스트 출처: `_meta/phases/phase1_progress.md` §"Q-002 등록 대기" (Builder가 작성, Architect가 본 운영 큐로 이동, 2026-05-02).

---

(추가 항목은 위쪽으로 — 최신순)

---

## 완료된 작업

### Q-001: P0.5 마이그레이션 적용 ✅ (등록: 2026-04-24, 완료: 2026-04-26)

**관련 commit**: `phase0_5/screener-refactor` 머지 commit (`410b5ac feat(screener): add conditions_met JSON per ADR-009 (P0.5)`)  
**관련 ADR**: ADR-009 (스크리너 개편 + `conditions_met` 컬럼 추가)  
**적용 일시**: 2026-04-26 18:18 KST (일요일)  
**적용 시점 HEAD**: `af28f9f docs(meta): add ADR-011 (Phase 1 CLI backend with conditional exception)`  
**적용 방식**: `docker exec -i mysql-standalone-mysql mysql -u root ...` (호스트 mysql 클라이언트 부재로 컨테이너 내부 실행)  
**자격증명**: `.env`의 `MYSQL_ROOT_PASSWORD` 사용  
**백업**: 생략 (사용자 지시, ADD COLUMN ... NULL의 멱등성 신뢰)  
**적용 소요**: 1.5초 (MySQL 8.4.8 INSTANT ADD COLUMN)

**검증 결과**:
- ✅ DESCRIBE 검증: KR/US 두 테이블 모두 `conditions_met JSON` 컬럼 확인
  - 위치: `AFTER is_blue_dot`
  - 타입: json, NULL 허용
  - COMMENT: `"ADR-009: per-condition pass/fail map"`
- ✅ ALTER 중 cron 충돌: 없음 (일요일이라 영향 cron 없음)
- ⏳ 추가 검증 (예정): 다음 KR/US daily cron 실행 후 `conditions_met` JSON에 8개 키가 채워지는지 확인 (별도 시점 검증 — Phase 1 1.1 단계 시작 직전)

**작업 환경**:
- PROD (Windows + PowerShell)
- DB: `mysql-standalone-mysql` Docker 컨테이너 (MySQL 8.4.8)

**메모**:
- Alembic은 이번에 다루지 않음. ADR-010 §5에 따라 운영 환경에 `alembic_version` 테이블 미생성. DEV·PROD `alembic_version` 동기화는 추후 별도 큐 항목으로 다룸.

---

*이 문서는 ADR-010이 정의하는 큐 운영 절차의 SSoT다.*