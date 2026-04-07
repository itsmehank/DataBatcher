# Windows Dashboard Download Scheduler Guide

이 문서는 Git Bash 기반으로 `Dashboard`의 `Download Checked` 자동화를 Windows Task Scheduler에 4개 시장 작업으로 등록하는 방법을 설명합니다.

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

## 3) 시장별 env 파일 작성

아래 4개 예시 파일을 각각 실제 env 파일로 복사합니다.

```powershell
copy .\apps\trading-view-project\ops\scheduler\windows\scheduler.us-nasdaq.env.example .\apps\trading-view-project\ops\scheduler\windows\scheduler.us-nasdaq.env
copy .\apps\trading-view-project\ops\scheduler\windows\scheduler.us-nyse.env.example .\apps\trading-view-project\ops\scheduler\windows\scheduler.us-nyse.env
copy .\apps\trading-view-project\ops\scheduler\windows\scheduler.kr-kospi.env.example .\apps\trading-view-project\ops\scheduler\windows\scheduler.kr-kospi.env
copy .\apps\trading-view-project\ops\scheduler\windows\scheduler.kr-kosdaq.env.example .\apps\trading-view-project\ops\scheduler\windows\scheduler.kr-kosdaq.env
```

각 env 파일에서 공통으로 확인할 값:

- `GIT_BASH_EXE`
- `NODE_BIN`
- `FRONTEND_URL`
- `HEADLESS`

시장별 기본값은 이미 파일에 들어 있습니다.

- `scheduler.us-nasdaq.env` -> `REGION=US`, `MARKET=NASDAQ`
- `scheduler.us-nyse.env` -> `REGION=US`, `MARKET=NYSE`
- `scheduler.kr-kospi.env` -> `REGION=KR`, `MARKET=KOSPI`
- `scheduler.kr-kosdaq.env` -> `REGION=KR`, `MARKET=KOSDAQ`

선택값:

- `LIST_CATEGORY` (기본 `all`)
- `DATE` (비우면 `/api/options/dates`의 첫 번째 값, 즉 최신 가격 날짜 사용)
- `OUTPUT_DIR` (기본 예시는 시장별 하위 디렉터리)

`DATE`를 비웠는데 해당 최신 가격 날짜에 Minervini 결과가 없으면 작업은 명시적인 에러로 종료됩니다. 이 경우 `DATE`를 직접 지정하세요.

## 4) 수동 실행

작업 등록 전에 먼저 시장별로 1회 수동 실행합니다.

아래 명령은 모노레포 루트에서 실행하는 기준입니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\trading-view-project\ops\scheduler\windows\run_dashboard_download.ps1 -EnvFile .\apps\trading-view-project\ops\scheduler\windows\scheduler.us-nasdaq.env -JobName "US-NASDAQ"
powershell -ExecutionPolicy Bypass -File .\apps\trading-view-project\ops\scheduler\windows\run_dashboard_download.ps1 -EnvFile .\apps\trading-view-project\ops\scheduler\windows\scheduler.us-nyse.env -JobName "US-NYSE"
powershell -ExecutionPolicy Bypass -File .\apps\trading-view-project\ops\scheduler\windows\run_dashboard_download.ps1 -EnvFile .\apps\trading-view-project\ops\scheduler\windows\scheduler.kr-kospi.env -JobName "KR-KOSPI"
powershell -ExecutionPolicy Bypass -File .\apps\trading-view-project\ops\scheduler\windows\run_dashboard_download.ps1 -EnvFile .\apps\trading-view-project\ops\scheduler\windows\scheduler.kr-kosdaq.env -JobName "KR-KOSDAQ"
```

로그는 `apps\trading-view-project\automation\logs\windows_scheduler_<job>_*.log`에 남습니다.

## 5) Task Scheduler 등록

아래 등록 명령은 관리자 권한 PowerShell에서 실행하는 것이 안전합니다.

기본 등록은 4개 작업을 아래 순서로 나눠 등록합니다.

- `US-NASDAQ` -> `18:00`
- `US-NYSE` -> `18:05`
- `KR-KOSPI` -> `18:10`
- `KR-KOSDAQ` -> `18:15`

기본 등록:

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\trading-view-project\ops\scheduler\windows\register_tasks.ps1
```

기준 시각 변경:

```powershell
powershell -ExecutionPolicy Bypass -File .\apps\trading-view-project\ops\scheduler\windows\register_tasks.ps1 -BaseDailyAt "18:30"
```

위 명령은 `18:30`, `18:35`, `18:40`, `18:45`로 4개 작업을 등록합니다.

등록 확인:

```powershell
Get-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload-*"
```

수동 시작:

```powershell
Start-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload-US-NASDAQ"
Start-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload-US-NYSE"
Start-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload-KR-KOSPI"
Start-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload-KR-KOSDAQ"
```

삭제:

```powershell
Unregister-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload-US-NASDAQ" -Confirm:$false
Unregister-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload-US-NYSE" -Confirm:$false
Unregister-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload-KR-KOSPI" -Confirm:$false
Unregister-ScheduledTask -TaskName "DataBatcher-TradingView-DashboardDownload-KR-KOSDAQ" -Confirm:$false
```

## 6) 동작 방식

- Task Scheduler는 `run_dashboard_download.ps1`를 실행합니다.
- PowerShell 래퍼는 job별 env 파일을 로드합니다.
- Git Bash로 `ops/shell/run_dashboard_download.sh`를 실행합니다.
- `.sh`가 Playwright 자동화를 실행해 ZIP을 저장합니다.
- ZIP 안에는 선택된 각 심볼별 `jpg + daily csv + weekly csv + rs csv`가 함께 들어갑니다.
- 시장별 기본 `OUTPUT_DIR`를 분리해서 ZIP도 시장별 디렉터리에 저장합니다.

## 7) 장애 확인 포인트

- `scheduler.us-nasdaq.env`, `scheduler.us-nyse.env`, `scheduler.kr-kospi.env`, `scheduler.kr-kosdaq.env`가 실제로 존재하는지 확인합니다.
- `GIT_BASH_EXE`, `NODE_BIN` 경로가 실제 파일인지 확인합니다.
- `FRONTEND_URL/api/health`가 성공하는지 확인합니다.
- `FRONTEND_URL/api/health/db?region=REGION`이 성공하는지 확인합니다.
- `MARKET` 값이 실제 대시보드에서 지원되는지 확인합니다.
- `DATE`를 비운 경우 최신 가격 날짜에 Minervini rows가 실제로 있는지 확인합니다.
- `automation\logs\windows_scheduler_<job>_*.log`와 `automation\logs\dashboard_download_*.log`를 확인합니다.
