# Phase 2 Sprint 3 — 일일 메일 발송 Task Scheduler 등록 (ADR-016 C급).
# brief §3 Sprint 3.
#
# 운영 환경(집 PC)에서 한 번 실행해 EmailSend_KR / EmailSend_US 작업을 등록한다.
# install_task.ps1 (Phase 1 LLMAnalysis_*) 양식 계승.
#
# Usage (운영 환경 PowerShell):
#   .\install_email_task.ps1                                # repo root 자동 추정
#   .\install_email_task.ps1 -ProjectRoot "C:\path\to\DataBatcher"
#   .\install_email_task.ps1 -UsTime "17:30" -KrTime "22:30"  # 시각 조정
#
# 시각 기본값: LLMAnalysis_*의 1시간 뒤로 둠 (분석 완료 + 안전 마진).
#   - LLMAnalysis_US 16:00 KST → EmailSend_US 17:00 KST
#   - LLMAnalysis_KR 21:00 KST → EmailSend_KR 22:00 KST
#
# 통제권 메커니즘 — 등록 후 표준 명령:
#   Disable-ScheduledTask -TaskName "EmailSend_US"
#   Disable-ScheduledTask -TaskName "EmailSend_KR"
#   Enable-ScheduledTask  -TaskName "EmailSend_US"
#   Enable-ScheduledTask  -TaskName "EmailSend_KR"
#   Unregister-ScheduledTask -TaskName "EmailSend_US" -Confirm:$false
#   Unregister-ScheduledTask -TaskName "EmailSend_KR" -Confirm:$false
#   Get-ScheduledTask -TaskName "EmailSend_*"
#   Get-ScheduledTaskInfo -TaskName "EmailSend_US"

param(
    [string]$ProjectRoot = "",
    [string]$UsTime = "17:00",
    [string]$KrTime = "22:00"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\..")).Path
}

$wrapperPath = Join-Path $ProjectRoot "apps\llm-analysis\ops\scheduler\windows\run_email_today.ps1"
if (-not (Test-Path -LiteralPath $wrapperPath)) {
    Write-Error "wrapper not found: $wrapperPath"
    exit 1
}

Write-Host "ProjectRoot = $ProjectRoot" -ForegroundColor Cyan
Write-Host "Wrapper     = $wrapperPath" -ForegroundColor Cyan
Write-Host "EmailSend_US trigger = $UsTime KST" -ForegroundColor Cyan
Write-Host "EmailSend_KR trigger = $KrTime KST" -ForegroundColor Cyan

# 기존 작업이 있으면 제거 (idempotent re-install)
foreach ($name in @("EmailSend_US", "EmailSend_KR")) {
    if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
        Write-Host "[INFO] removing existing task: $name" -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
    }
}

# US 발송
$usAction = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$wrapperPath`" -Region US"
$usTrigger = New-ScheduledTaskTrigger -Daily -At $UsTime
$usSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName "EmailSend_US" `
    -Action $usAction -Trigger $usTrigger -Settings $usSettings `
    -Description "Phase 2 Sprint 3 — daily email dispatch for US region (recommended 17:00 KST)"

# KR 발송
$krAction = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$wrapperPath`" -Region KR"
$krTrigger = New-ScheduledTaskTrigger -Daily -At $KrTime
$krSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName "EmailSend_KR" `
    -Action $krAction -Trigger $krTrigger -Settings $krSettings `
    -Description "Phase 2 Sprint 3 — daily email dispatch for KR region (recommended 22:00 KST)"

Write-Host "`n=== Task Scheduler 등록 완료 ===" -ForegroundColor Green
Get-ScheduledTask -TaskName "EmailSend_*" |
    Format-Table TaskName, State, @{Name="NextRun"; Expression={(Get-ScheduledTaskInfo $_).NextRunTime}}
