# Phase 2 Sprint 3 — 일일 메일 발송 wrapper (ADR-016 C급).
# brief §3 Sprint 3 — Windows Task Scheduler가 매일 정시에 호출하는 wrapper.
#
# Usage:
#   .\run_email_today.ps1                       # 그날 region 모두 (KR + US)
#   .\run_email_today.ps1 -Region KR            # 한 region만
#   .\run_email_today.ps1 -Region US -DryRun    # SMTP skip, 본문/JSONL만
#   .\run_email_today.ps1 -Date 2026-05-12      # 특정 거래일
#   .\run_email_today.ps1 -To other@example.com # 수신자 지정
#
# 통제권 메커니즘 (ADR-016 §4.1 / 헌법 §4):
#   1) 일시 중단: Disable-ScheduledTask -TaskName "EmailSend_US" / "EmailSend_KR"
#   2) 자격증명 회수: apps/llm-analysis/.env의 SMTP_PASSWORD 삭제 또는 변경
#   3) 발송 기록: apps/llm-analysis/logs/email_dispatch.jsonl (append-only, JSONL)
#   4) 매매 게이트 부재 (헌법 §2.1) — 본 스크립트는 메일 발송만, 주문 없음

param(
    [ValidateSet("KR", "US", "BOTH")]
    [string]$Region = "BOTH",
    [string]$Date = "",
    [string]$To = "",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# Repo root 결정 (본 파일은 apps/llm-analysis/ops/scheduler/windows/ 에 위치)
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\..")).Path

# Python 인터프리터: llm-analysis venv 우선, 없으면 시스템 python
$venvPython = Join-Path $repoRoot "apps\llm-analysis\venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "python"
}

# 로그 디렉터리 (Phase 1 양식 계승)
$logDir = Join-Path $repoRoot "logs\scheduler"
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$startedAt = Get-Date
$dateStr = if ($Date) { $Date } else { $startedAt.ToString("yyyy-MM-dd") }
$logFile = Join-Path $logDir ("email_send_{0}_{1}.log" -f $Region.ToLower(), $startedAt.ToString("yyyyMMdd_HHmmss"))

function Write-Log {
    param([string]$Msg)
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $Msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Write-Log "===== EmailSend wrapper start ====="
Write-Log "repoRoot=$repoRoot"
Write-Log "pythonExe=$pythonExe"
Write-Log "Region=$Region Date=$dateStr DryRun=$DryRun To=$To"

$scriptPath = Join-Path $repoRoot "apps\llm-analysis\run_email_send.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    Write-Log "[ERROR] run_email_send.py not found: $scriptPath"
    exit 1
}

# run_email_send.py 인자 — region은 소문자 (kr|us|both)
$pyArgs = @(
    $scriptPath,
    "--date", $dateStr,
    "--region", $Region.ToLower()
)
if ($To)     { $pyArgs += "--to";  $pyArgs += $To }
if ($DryRun) { $pyArgs += "--dry-run" }

Write-Log "exec: $pythonExe $($pyArgs -join ' ')"

& $pythonExe @pyArgs 2>&1 | Tee-Object -FilePath $logFile -Append
$exitCode = $LASTEXITCODE
Write-Log "run_email_send exit=$exitCode"

$elapsed = ((Get-Date) - $startedAt).TotalSeconds
Write-Log "===== EmailSend wrapper end exit=$exitCode elapsed=${elapsed}s ====="

exit $exitCode
