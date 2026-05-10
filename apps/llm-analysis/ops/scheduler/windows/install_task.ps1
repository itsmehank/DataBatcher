# Phase 1 LLM 분석 — Windows Task Scheduler 등록 (ADR-012 §2, brief §8.3.2)
#
# 운영 환경(집 PC)에서 한 번 실행해 LLMAnalysis_KR / LLMAnalysis_US 작업을 등록한다.
# Q-003 운영 큐 항목으로 사용자가 직접 실행.
#
# Usage (운영 환경 PowerShell):
#   .\install_task.ps1                                 # repo root 자동 추정
#   .\install_task.ps1 -ProjectRoot "C:\path\to\DataBatcher"
#
# 통제권 메커니즘 (ADR-012 §5) — 등록 후 표준 명령:
#   Disable-ScheduledTask -TaskName "LLMAnalysis_US"
#   Disable-ScheduledTask -TaskName "LLMAnalysis_KR"
#   Enable-ScheduledTask  -TaskName "LLMAnalysis_US"
#   Enable-ScheduledTask  -TaskName "LLMAnalysis_KR"
#   Unregister-ScheduledTask -TaskName "LLMAnalysis_US" -Confirm:$false
#   Unregister-ScheduledTask -TaskName "LLMAnalysis_KR" -Confirm:$false
#   Get-ScheduledTask -TaskName "LLMAnalysis_*"
#   Get-ScheduledTaskInfo -TaskName "LLMAnalysis_US"

param(
    [string]$ProjectRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ProjectRoot 자동 추정 (본 파일이 apps/llm-analysis/ops/scheduler/windows/ 에 위치)
if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\..")).Path
}

$wrapperPath = Join-Path $ProjectRoot "apps\llm-analysis\ops\scheduler\windows\run_analysis_today.ps1"
if (-not (Test-Path -LiteralPath $wrapperPath)) {
    Write-Error "wrapper not found: $wrapperPath"
    exit 1
}

Write-Host "ProjectRoot = $ProjectRoot" -ForegroundColor Cyan
Write-Host "Wrapper     = $wrapperPath" -ForegroundColor Cyan

# 기존 작업이 있으면 제거 (idempotent re-install)
foreach ($name in @("LLMAnalysis_US", "LLMAnalysis_KR")) {
    if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
        Write-Host "[INFO] removing existing task: $name" -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
    }
}

# US 분석 — 매일 16:00 KST (US daily 08:00~14:00 + 미너비니 ~14:10 + 안전 마진)
$usAction = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$wrapperPath`" -Region US"
$usTrigger = New-ScheduledTaskTrigger -Daily -At 16:00
$usSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName "LLMAnalysis_US" `
    -Action $usAction -Trigger $usTrigger -Settings $usSettings `
    -Description "Phase 1 LLM analysis for US region (ADR-012, recommended 16:00 KST)"

# KR 분석 — 매일 21:00 KST (KR daily 19:00~19:30 + 미너비니 ~19:40 + 안전 마진)
$krAction = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$wrapperPath`" -Region KR"
$krTrigger = New-ScheduledTaskTrigger -Daily -At 21:00
$krSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName "LLMAnalysis_KR" `
    -Action $krAction -Trigger $krTrigger -Settings $krSettings `
    -Description "Phase 1 LLM analysis for KR region (ADR-012, recommended 21:00 KST)"

Write-Host "`n=== Task Scheduler 등록 완료 ===" -ForegroundColor Green
Get-ScheduledTask -TaskName "LLMAnalysis_*" |
    Format-Table TaskName, State, @{Name="NextRun"; Expression={(Get-ScheduledTaskInfo $_).NextRunTime}}
