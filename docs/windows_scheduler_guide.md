# Windows Scheduler Guide (원스톱)

이 문서는 **처음 clone한 Windows 사용자**가 이 문서만 보고,
설정 작성부터 Task Scheduler 등록까지 끝낼 수 있도록 작성되었습니다.

완료 상태(이 문서의 목표):
- DB 연결 설정 완료
- `scheduler/windows/scheduler.env` 작성 완료
- `DataBatcher-Daily-KR`, `DataBatcher-Daily-US`, `DataBatcher-Weekly`, `DataBatcher-LogCleanup` 등록 완료
- 수동 검증 1회 완료

## 0) 전체 흐름 요약 (처음 사용자용)
1. 필수 도구 설치
2. 프로젝트 clone + Python 가상환경 + 의존성 설치
3. DB 준비(로컬 Docker 또는 원격 DB)
4. DB 연결 설정(`DATABASE_URL` 또는 `config/settings.dev.yaml`)
5. `scheduler.env` 작성
6. 작업 스케줄 등록
7. 수동 실행으로 검증

## 1) 사전 준비
### 필수
- Git for Windows (Git Bash 포함)
- Python 3.10+

### 선택
- Docker Desktop (로컬 MySQL 컨테이너를 쓸 때)

## 2) 프로젝트 clone 및 Python 환경 준비
```powershell
git clone <YOUR_REPO_URL>
cd DataBatcher
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install apprise
```

## 3) DB 준비
### A안: 로컬 Docker MySQL 사용
```powershell
copy .env.example .env
docker compose -f docker/docker-compose.yml up -d
```

### B안: 원격 DB 사용
- DB 서버 접근 가능(방화벽/계정/포트) 상태인지 먼저 확인합니다.

## 4) DB 연결 설정 (둘 중 하나 선택)
프로젝트는 아래 우선순위로 DB 타겟을 결정합니다.
1. `DATABASE_URL` 환경변수
2. `config/settings.dev.yaml`
3. `config/settings.yaml`

### 권장: `scheduler.env`의 `DATABASE_URL` 사용
스케줄러 실행 프로세스에서만 적용되어 운영 관리가 쉽습니다.

### 대안: `config/settings.dev.yaml` 작성
`config/settings.dev.yaml` 파일을 만들고 아래처럼 입력:

```yaml
database:
  url: mysql+pymysql://YOUR_DB_USER:YOUR_DB_PASSWORD@127.0.0.1:3306/market?charset=utf8mb4
```

## 5) 스키마 초기화 (최초 1회)
```powershell
python scripts/init_db.py
```

## 6) scheduler.env 작성
샘플 복사:

```powershell
copy .\scheduler\windows\scheduler.env.example .\scheduler\windows\scheduler.env
```

`scheduler.env`에서 아래 키를 채웁니다.

- `BATCH_PYTHON_EXE` (필수)
  - 예: `C:\Users\YOUR_USER\PythonProject\DataBatcher\.venv\Scripts\python.exe`
- `SCHEDULER_PYTHON_EXE` (선택)
  - 비우면 `BATCH_PYTHON_EXE`를 알림에도 사용
- `GIT_BASH_EXE` (필수)
  - 예: `C:\Program Files\Git\bin\bash.exe`
- `DATABASE_URL` (권장)
  - 예: `mysql+pymysql://user:pass@127.0.0.1:3306/market?charset=utf8mb4`
- `LOG_RETENTION_DAYS` (선택, 기본 14)
- `APPRISE_URLS` (권장)
  - 예: `tgram://BOT_TOKEN/CHAT_ID`

주의:
- 스케줄러는 실행 전 `scripts/healthcheck_db.py`로 실제 DB 연결(`SELECT 1`)을 검사합니다.
- 컨테이너 실행 여부 자체를 체크하지 않습니다.

## 7) Task Scheduler 등록
기본 권장 시각:
- KR Daily: 18:00
- US Daily: 08:00
- Weekly(토요일): 08:00
- Log cleanup: 03:30

등록:
```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\register_tasks.ps1
```

시각 커스터마이즈:
```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\register_tasks.ps1 -KrDailyAt "18:10" -UsDailyAt "08:10" -WeeklyAt "08:30" -CleanupAt "04:00"
```

등록 확인:
```powershell
Get-ScheduledTask -TaskName "DataBatcher-*"
```

## 8) 최초 수동 검증 (필수)
아래 4개를 1회 수동 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\run_daily.ps1 -Target KR
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\run_daily.ps1 -Target US
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\run_weekly.ps1
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\cleanup_logs.ps1
```

로그 확인 경로:
- `logs/scheduler/daily_kr_*.log`
- `logs/scheduler/daily_us_*.log`
- `logs/scheduler/weekly_*.log`
- `logs/scheduler/cleanup_*.log`

로그에서 확인할 핵심 문자열:
- `DB healthcheck start`
- `DB connection OK`
- `completed successfully`

## 9) 실패 시 빠른 점검
1. `BATCH_PYTHON_EXE` 경로가 실제 존재하는지 확인
2. `"<BATCH_PYTHON_EXE>" -m pip install -r requirements.txt` 재실행
3. `DATABASE_URL` 값 재확인 (계정/비밀번호/호스트/포트/DB명)
4. DB 접속 권한 및 네트워크(방화벽) 확인
5. 같은 명령 재실행 후 로그 비교

## 10) 종료코드/알림 동작
- `daily_kr.sh`, `daily_us.sh`, `weekly_all.sh`는 실패가 있으면 `exit 1`
- PowerShell 래퍼는 종료코드를 기반으로 Apprise SUCCESS/FAILED/SKIPPED 알림 전송

## 11) 보안 수칙
- `scheduler/windows/scheduler.env`는 로컬 전용 파일(커밋 금지)
- 토큰/비밀번호는 코드/문서 하드코딩 금지

업로드 전 점검:

```powershell
python scripts/preflight_repo_safety.py
git add -n .
git check-ignore -v .env .\scheduler\windows\scheduler.env config\settings.dev.yaml
```

## 12) 추가 참고
- 수동 운영 검증 확장판: `docs/operations_validation_manual.md`
