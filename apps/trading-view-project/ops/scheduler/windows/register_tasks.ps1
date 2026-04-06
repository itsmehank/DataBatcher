Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
    [string]$DailyAt = "18:00"
)

. "$PSScriptRoot\common.ps1"

$projectRoot = Get-ProjectRoot
$powershellExe = Join-Path $PSHOME "powershell.exe"
$runnerScript = Join-Path $PSScriptRoot "run_dashboard_download.ps1"

if (-not (Test-Path -LiteralPath $runnerScript)) {
    throw "Missing script: $runnerScript"
}

$actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runnerScript`""
$action = New-ScheduledTaskAction -Execute $powershellExe -Argument $actionArgs -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $DailyAt
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 12)

$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings
$taskName = "DataBatcher-TradingView-DashboardDownload"

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask -TaskName $taskName -InputObject $task | Out-Null
Write-Host "Registered task: $taskName at $DailyAt"
