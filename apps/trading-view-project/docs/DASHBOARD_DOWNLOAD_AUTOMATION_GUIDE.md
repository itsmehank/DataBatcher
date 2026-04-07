# Dashboard Download Automation Guide

이 문서는 `Dashboard` 화면의 `Download Checked` 흐름을 브라우저 자동화로 실행하고, macOS `launchd`에 등록하는 방법을 설명합니다.

## 1) 범위

- 기존 `frontend/src` / `backend/app` 비즈니스 로직은 수정하지 않습니다.
- 자동화 코드는 `apps/trading-view-project/automation/` 아래에 별도로 둡니다.
- 실행 래퍼는 `apps/trading-view-project/ops/shell/run_dashboard_download.sh`를 사용합니다.
- 스케줄 등록 파일은 `apps/trading-view-project/ops/scheduler/macos/com.databatcher.tradingview.dashboard-download.plist`입니다.

## 2) 사전 준비

앱은 먼저 실행 중이어야 합니다.

- 이 자동화는 앱 기동까지 책임지지 않습니다.
- 현재 읽기/다운로드 흐름은 로그인 없이 동작합니다.

```bash
cd /Users/hank.es/PythonProject/DataBatcher/apps/trading-view-project
./run-dev.sh
```

자동화 의존성을 설치합니다.

```bash
cd /Users/hank.es/PythonProject/DataBatcher/apps/trading-view-project/automation
npm install
npx playwright install chromium
```

## 3) 수동 실행

최소 필수 환경값은 `MARKET`입니다.

```bash
MARKET=NASDAQ \
REGION=US \
LIST_CATEGORY=all \
bash /Users/hank.es/PythonProject/DataBatcher/apps/trading-view-project/ops/shell/run_dashboard_download.sh
```

선택적으로 `DATE`를 직접 고정할 수 있습니다.

```bash
MARKET=NASDAQ \
REGION=US \
DATE=2026-04-06 \
LIST_CATEGORY=all \
bash /Users/hank.es/PythonProject/DataBatcher/apps/trading-view-project/ops/shell/run_dashboard_download.sh
```

기본값:

- `FRONTEND_URL=http://127.0.0.1:5173`
- `REGION=US`
- `LIST_CATEGORY=all`
- `HEADLESS=true`
- `OUTPUT_DIR=/Users/hank.es/PythonProject/DataBatcher/apps/trading-view-project/automation/output`

`DATE`를 비워두면 `/api/options/dates`의 첫 번째 값, 즉 현재 대시보드가 기본으로 잡는 최신 가격 날짜를 사용합니다. 이 날짜에 Minervini 결과가 없으면 자동화는 명시적인 에러로 종료됩니다. 그런 경우 `DATE`를 직접 지정해서 실행하세요.

실행 로그는 `apps/trading-view-project/automation/logs/` 아래에 쌓입니다.

## 4) macOS 스케줄 등록

먼저 plist 파일의 아래 값을 실제 값으로 수정합니다.

- `ProgramArguments` 안의 스크립트 절대경로
- `WorkingDirectory`
- `PATH`
- `NODE_BIN`
- `MARKET`
- 실행 시각 (`Hour`, `Minute`)
- 필요 시 `REGION`, `LIST_CATEGORY`, `OUTPUT_DIR`, `StandardOutPath`, `StandardErrorPath`

로그 디렉토리를 먼저 만듭니다.

```bash
mkdir -p /Users/hank.es/PythonProject/DataBatcher/apps/trading-view-project/automation/logs
```

LaunchAgent를 등록합니다.

```bash
cp /Users/hank.es/PythonProject/DataBatcher/apps/trading-view-project/ops/scheduler/macos/com.databatcher.tradingview.dashboard-download.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.databatcher.tradingview.dashboard-download.plist >/dev/null 2>&1 || true
launchctl load ~/Library/LaunchAgents/com.databatcher.tradingview.dashboard-download.plist
launchctl list | grep com.databatcher.tradingview.dashboard-download
```

해제:

```bash
launchctl unload ~/Library/LaunchAgents/com.databatcher.tradingview.dashboard-download.plist
rm -f ~/Library/LaunchAgents/com.databatcher.tradingview.dashboard-download.plist
```

## 5) 동작 방식

- 브라우저 자동화는 `/dashboard`에 직접 진입합니다.
- `region`, `market`, `listCategory`, `date`는 URL 쿼리로 전달합니다.
- 표가 로드되면 `Select all rows for download` 체크박스를 선택합니다.
- `Download Checked` 버튼을 눌러 ZIP 다운로드를 저장합니다.
- ZIP 안에는 선택된 각 심볼별 `jpg + daily csv + weekly csv + rs csv`가 함께 들어갑니다.

## 6) 장애 확인 포인트

- `curl http://127.0.0.1:5173/api/health`가 성공하는지 확인합니다.
- `curl 'http://127.0.0.1:5173/api/health/db?region=US'`가 성공하는지 확인합니다.
- `automation/node_modules`가 있는지 확인합니다.
- `npx playwright install chromium`를 실행했는지 확인합니다.
- `MARKET` 값이 실제 대시보드에서 지원되는지 확인합니다.
- `DATE`를 비운 경우 최신 가격 날짜에 Minervini rows가 실제로 있는지 확인합니다.
- `automation/logs/`의 최신 로그 파일과 `launchd_stdout.log`, `launchd_stderr.log`를 확인합니다.
