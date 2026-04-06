# Windows Dashboard Download Scheduler Guide

이 문서는 Git Bash 기반으로 `Dashboard`의 `Download Checked` 자동화를 Windows Task Scheduler에 등록하는 방법을 설명합니다.

## 1) 범위

- 자동화 본체는 `apps/trading-view-project/automation/run-dashboard-download.mjs`를 사용합니다.
- 실행 래퍼는 `apps/trading-view-project/ops/shell/run_dashboard_download.sh`를 사용합니다.
- Windows 전용 파일은 `apps/trading-view-project/ops/scheduler/windows/` 아래에 둡니다.

## 2) 사전 준비

필수 프로그램:

- Git for Windows (Git Bash 포함)
- Node.js
- PowerShell

앱은 먼저 실행 중이어야 합니다. 예시는 프런트가 `http://127.0.0.1:5173`에서 동작한다고 가정합니다.

- 이 스케줄러는 앱 기동까지 책임지지 않습니다.
- 현재 읽기/다운로드 흐름은 로그인 없이 동작합니다.

자동화 의존성 설치:

```powershell
cd C:\Users\YOUR_USER\PythonProject\DataBatcher\apps\trading-view-project\automation
npm install
npx playwright install chromium
```

## 3) scheduler.env 작성

샘플 복사:

```powershell
copy .\apps\trading-view-project\ops\scheduler\windows\scheduler.env.example .\apps\trading-view-project\ops\scheduler\windows\scheduler.env
```

필수 수정값:

- `GIT_BASH_EXE`
- `NODE_BIN`
- `FRONTEND_URL`
- `MARKET`

선택값:

- `REGION` (기본 `US`)
- `LIST_CATEGORY` (기본 `all`)
- `DATE` (비우면 `/api/options/dates`의 첫 번째 값, 즉 최신 가격 날짜 사용)
- `HEADLESS` (기본 `true`)
- `OUTPUT_DIR` (비우면 `automation/output` 사용)

`DATE`를 비웠는데 해당 최신 가격 날짜에 Minervini 결과가 없으면 작업은 명시적인 에러로 종료됩니다. 이 경우 `DATE`를 직접 지정하세요.

## 4) 수동 실행

작업 등록 전에 먼저 1회 수동 실행합니다.

아래 명령은 모노레포 루트에서 실행하는 기준입니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\trading-view-project\ops\scheduler\windows\run_dashboard_download.ps1
```

로그는 `apps\trading-view-project\automation\logs\windows_scheduler_*.log`에 남습니다.

## 5) Task Scheduler 등록

기본 등록:

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\trading-view-project\ops\scheduler\windows\register_tasks.ps1
```

시간 변경:

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\trading-view-project\ops\scheduler\windows\register_tasks.ps1 -DailyAt "18:30"
```

등록 확인:

```powershell
Get-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload"
```

수동 시작:

```powershell
Start-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload"
```

삭제:

```powershell
Unregister-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload" -Confirm:$false
```

## 6) 동작 방식

- Task Scheduler는 `run_dashboard_download.ps1`를 실행합니다.
- PowerShell 래퍼는 `scheduler.env`를 로드합니다.
- Git Bash로 `ops/shell/run_dashboard_download.sh`를 실행합니다.
- `.sh`가 Playwright 자동화를 실행해 ZIP을 저장합니다.

## 7) 장애 확인 포인트

- `scheduler.env`가 실제로 존재하는지 확인합니다.
- `GIT_BASH_EXE`, `NODE_BIN` 경로가 실제 파일인지 확인합니다.
- `FRONTEND_URL/api/health`가 성공하는지 확인합니다.
- `FRONTEND_URL/api/health/db?region=REGION`이 성공하는지 확인합니다.
- `MARKET` 값이 실제 대시보드에서 지원되는지 확인합니다.
- `DATE`를 비운 경우 최신 가격 날짜에 Minervini rows가 실제로 있는지 확인합니다.
- `automation\logs\windows_scheduler_*.log`와 `automation\logs\dashboard_download_*.log`를 확인합니다.
