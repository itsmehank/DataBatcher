Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
    [string]$BaseDailyAt = "18:00"
)

. "$PSScriptRoot\common.ps1"

$projectRoot = Get-ProjectRoot
$powershellExe = Join-Path $PSHOME "powershell.exe"
$runnerScript = Join-Path $PSScriptRoot "run_dashboard_download.ps1"

if (-not (Test-Path -LiteralPath $runnerScript)) {
    throw "Missing script: $runnerScript"
}

$baseTime = [datetime]::ParseExact($BaseDailyAt, "HH:mm", [System.Globalization.CultureInfo]::InvariantCulture)

$jobs = @(
    @{ JobName = "US-NASDAQ"; EnvFile = Join-Path $PSScriptRoot "scheduler.us-nasdaq.env"; OffsetMinutes = 0 },
    @{ JobName = "US-NYSE"; EnvFile = Join-Path $PSScriptRoot "scheduler.us-nyse.env"; OffsetMinutes = 5 },
    @{ JobName = "KR-KOSPI"; EnvFile = Join-Path $PSScriptRoot "scheduler.kr-kospi.env"; OffsetMinutes = 10 },
    @{ JobName = "KR-KOSDAQ"; EnvFile = Join-Path $PSScriptRoot "scheduler.kr-kosdaq.env"; OffsetMinutes = 15 }
)

foreach ($job in $jobs) {
    if (-not (Test-Path -LiteralPath $job.EnvFile)) {
        throw "Missing env file: $($job.EnvFile)"
    }

    $runTime = $baseTime.AddMinutes([int]$job.OffsetMinutes).ToString("HH:mm")
    $actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runnerScript`" -EnvFile `"$($job.EnvFile)`" -JobName `"$($job.JobName)`""
    $action = New-ScheduledTaskAction -Execute $powershellExe -Argument $actionArgs -WorkingDirectory $projectRoot
    $trigger = New-ScheduledTaskTrigger -Daily -At $runTime
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours 12)

    $task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings
    $taskName = "DataBatcher-TradingView-DashboardDownload-{0}" -f $job.JobName

    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }

    Register-ScheduledTask -TaskName $taskName -InputObject $task | Out-Null
    Write-Host "Registered task: $taskName at $runTime using $($job.EnvFile)"
}
