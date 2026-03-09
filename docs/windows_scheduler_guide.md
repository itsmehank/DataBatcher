# Windows Scheduler Guide

이 문서는 Windows 노트북에서 DataBatcher KR/US daily 배치와 weekly 배치를 자동 실행하는 방법을 설명합니다.

## 1) 설계 요약
- 스케줄러: Windows Task Scheduler
- 실행 래퍼: PowerShell (`scheduler/windows/*.ps1`)
- 배치 본체:
  - KR Daily: `shell_scripts/daily_kr.sh`
  - US Daily: `shell_scripts/daily_us.sh`
  - Weekly: `shell_scripts/weekly_all.sh`
- `daily_crypto.sh`는 스케줄 대상에서 제외
- 중복 실행 방지: Named Mutex + Task Scheduler `IgnoreNew`
- 알림: Apprise (Telegram/Email 등)
- 로그 정리: `cleanup_logs.ps1`가 14일 초과 로그 삭제

## 2) 사전 준비
### 필수 설치
- Git for Windows (Git Bash 포함)
- Python + venv (`pip install -r requirements.txt`)
- Docker Desktop

### 프로젝트 준비
```powershell
git clone <YOUR_REPO_URL>
cd DataBatcher
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install apprise
```

## 3) 스케줄러 설정 파일 생성
샘플 파일을 복사해서 로컬 설정 파일을 만듭니다.

```powershell
copy .\scheduler\windows\scheduler.env.example .\scheduler\windows\scheduler.env
```

`scheduler.env`에서 아래 키를 반드시 확인하세요.
- `SCHEDULER_PYTHON_EXE`
- `GIT_BASH_EXE`
- `DOCKER_MYSQL_CONTAINER` (기본: `databatche_db`)
- `LOG_RETENTION_DAYS` (기본: `14`)
- `APPRISE_URLS` (Telegram/Email)

DB 타겟 관련:
- `DOCKER_MYSQL_CONTAINER`는 컨테이너 실행 여부 확인용입니다.
- 실제 적재 대상 DB는 `DATABASE_URL`(우선) 또는 `config/settings*.yaml`로 결정됩니다.
- 로컬 Docker DB를 쓰려면 `DATABASE_URL`을 해당 DB로 맞추세요.

## 4) Task Scheduler 등록
기본 시간(권장):
- KR Daily: 18:00
- US Daily: 08:00
- Weekly(토요일): 08:00
- Log cleanup: 03:30

```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\register_tasks.ps1
```

시간을 바꾸려면:
```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\register_tasks.ps1 -KrDailyAt "18:10" -UsDailyAt "08:10" -WeeklyAt "08:30" -CleanupAt "04:00"
```

등록 후 작업 확인:
```powershell
Get-ScheduledTask -TaskName "DataBatcher-*"
```

## 5) 수동 테스트 (강력 권장)
```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\run_daily.ps1 -Target KR
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\run_daily.ps1 -Target US
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\run_weekly.ps1
powershell -ExecutionPolicy Bypass -File .\scheduler\windows\cleanup_logs.ps1
```

로그 확인:
- `logs/scheduler/daily_kr_*.log`
- `logs/scheduler/daily_us_*.log`
- `logs/scheduler/weekly_*.log`
- `logs/scheduler/cleanup_*.log`

## 6) 종료코드/알림 동작
- `daily_kr.sh`, `daily_us.sh`는 실패 건수가 있으면 `exit 1`
- `weekly_all.sh`도 동일하게 실패 건수가 있으면 `exit 1`
- PowerShell 래퍼는 종료코드를 받아 Apprise로 SUCCESS/FAILED/SKIPPED 알림 전송

## 7) 보안 수칙
- `scheduler/windows/scheduler.env`는 로컬 전용 파일입니다. 커밋 금지.
- 토큰/비밀번호는 `scheduler.env`에만 저장하고 문서/코드에 하드코딩 금지.
- 업로드 전 점검:

```powershell
python scripts/preflight_repo_safety.py
git add -n .
git check-ignore -v .env .\scheduler\windows\scheduler.env config\settings.dev.yaml
```

## 8) 운영 팁 (노트북 환경)
- 절전/최대절전으로 인해 스케줄 누락 가능 -> 전원 정책 조정 권장
- Docker Desktop 자동 시작 + 컨테이너 재시작 정책 유지
- 월 1회 이상 백업 복원 테스트 권장
