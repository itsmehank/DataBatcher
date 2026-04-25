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
- **DB**: MySQL (Docker Compose 또는 native, 사용자가 명시)
- **MySQL 자격증명**: `.env`로 관리. PowerShell에서 `Get-Content .env`로 확인.
- **접속 방법**: 직접 / 원격 데스크톱 / SSH (사용자가 명시)

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

### Q-001: P0.5 마이그레이션 적용 (등록: 2026-04-24)

**관련 commit**: `phase0_5/screener-refactor` 머지 commit (main에 반영됨)  
**관련 ADR**: ADR-009 (스크리너 개편 + `conditions_met` 컬럼 추가)  
**위험도**: 중간 (DB 변경, 다음 cron 영향)  
**예상 소요**: 5~10분  
**타이밍 윈도우 (KST)**:
- KR daily cron이 16:30 시작 → 18:00 KST 이전 또는 21:00 이후 권장
- US daily cron이 22:00 시작 → 22:00 직전 회피
- **안전 시각: 18:00~22:00 KST 또는 다음날 새벽**

**해야 할 작업** (PowerShell, 운영 환경에서 실행):

```powershell
# 0. DataBatcher 경로로 이동
cd C:\path\to\DataBatcher    # 실제 경로로 치환

# 1. 작업 트리 깨끗한지 확인
git status
git branch                   # main 브랜치인지

# 2. 코드 pull
git pull

# 3. DB 백업 (안전 조치) — 자격증명은 .env에서 가져오거나 직접 입력
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
mysqldump -u $env:DB_USER -p"$env:DB_PASSWORD" trade > "C:\temp\trade_backup_${timestamp}.sql"
Get-Item "C:\temp\trade_backup_${timestamp}.sql" | Select-Object Name, Length

# 4. 현재 스키마 확인 (적용 전 상태)
mysql -u $env:DB_USER -p"$env:DB_PASSWORD" -e "DESCRIBE trade.minervini_screen_results_kr;" | Select-String "conditions_met"
# → 결과 없음 (컬럼 미존재) 이어야 함

# 5. 마이그레이션 적용 (raw SQL)
Get-Content apps\ingest-databatcher\scripts\migrations\add_conditions_met_column.sql | mysql -u $env:DB_USER -p"$env:DB_PASSWORD" trade

# 6. 적용 확인
mysql -u $env:DB_USER -p"$env:DB_PASSWORD" -e "DESCRIBE trade.minervini_screen_results_kr;" | Select-String "conditions_met"
mysql -u $env:DB_USER -p"$env:DB_PASSWORD" -e "DESCRIBE trade.minervini_screen_results_us;" | Select-String "conditions_met"
# → 두 명령 모두 'conditions_met JSON' 보여야 함
```

**주의 사항**:
- Alembic은 이번에 다루지 않음. ADR-010 결정 후 일괄 처리 예정 (Q5=A).
- 백업 파일은 적어도 1주 이상 보관. 다음 daily cron이 정상 종료되면 삭제 가능.
- PowerShell의 `mysqldump`/`mysql` 명령어가 `PATH`에 없으면 MySQL bin 폴더를 PATH에 추가하거나 절대 경로로 실행.
- 환경 변수가 `.env`에서 자동 로드되지 않으면, PowerShell에서 직접 export:
```powershell
  $env:DB_USER = "your_user"
  $env:DB_PASSWORD = "your_password"
```

**완료 기준**:
- `DESCRIBE` 결과에 KR/US 모두 `conditions_met JSON` 컬럼 보임
- 다음 KR cron(`kr_minervini_update.py`) 실행 후 `SELECT conditions_met FROM trade.minervini_screen_results_kr WHERE date = (가장 최근 날짜) LIMIT 1`에서 8개 키를 가진 JSON 반환
- 다음 US cron 실행 후 동일 검증

**완료 후 추가 작업**:
- 본 항목을 "완료된 작업" 섹션으로 이동
- 완료일·검증 결과 기록
- ADR-010이 그 사이에 확정되었다면, 추가로 alembic stamp 작업 필요 여부 확인

---

(추후 새 작업 항목이 추가되면 위쪽에 등록)

---

## 완료된 작업

(완료된 항목을 여기로 옮김. 작업일과 검증 결과 함께)

---

*이 문서는 ADR-010이 정의하는 큐 운영 절차의 SSoT다.*