param(
    [string]$KrDailyAt = "18:00",
    [string]$UsDailyAt = "08:00",
    [string]$WeeklyAt = "08:00",
    [string]$CleanupAt = "03:30"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"

$repoRoot = Get-RepoRoot
$powershellExe = Join-Path $PSHOME "powershell.exe"

function New-TaskActionForScript {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [Parameter(Mandatory = $false)]
        [string]$ExtraArguments = ""
    )

    $quoted = '"{0}"' -f $ScriptPath
    $args = "-NoProfile -ExecutionPolicy Bypass -File $quoted"
    if ($ExtraArguments) {
        $args = "$args $ExtraArguments"
    }
    return New-ScheduledTaskAction -Execute $powershellExe -Argument $args -WorkingDirectory $repoRoot
}

function Register-OrUpdateTask {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TaskName,
        [Parameter(Mandatory = $true)]
        [Microsoft.Management.Infrastructure.CimInstance]$Trigger,
        [Parameter(Mandatory = $true)]
        [Microsoft.Management.Infrastructure.CimInstance]$Action
    )

    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours 8)

    $task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $settings

    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    Register-ScheduledTask -TaskName $TaskName -InputObject $task | Out-Null
    Write-Host "Registered task: $TaskName"
}

$dailyScript = Join-Path $PSScriptRoot "run_daily.ps1"
$weeklyScript = Join-Path $PSScriptRoot "run_weekly.ps1"
$cleanupScript = Join-Path $PSScriptRoot "cleanup_logs.ps1"

if (-not (Test-Path -LiteralPath $dailyScript)) { throw "Missing script: $dailyScript" }
if (-not (Test-Path -LiteralPath $weeklyScript)) { throw "Missing script: $weeklyScript" }
if (-not (Test-Path -LiteralPath $cleanupScript)) { throw "Missing script: $cleanupScript" }

$krDailyTrigger = New-ScheduledTaskTrigger -Daily -At $KrDailyAt
$usDailyTrigger = New-ScheduledTaskTrigger -Daily -At $UsDailyAt
$weeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At $WeeklyAt
$cleanupTrigger = New-ScheduledTaskTrigger -Daily -At $CleanupAt

Register-OrUpdateTask -TaskName "DataBatcher-Daily-KR" -Trigger $krDailyTrigger -Action (New-TaskActionForScript -ScriptPath $dailyScript -ExtraArguments "-Target KR")
Register-OrUpdateTask -TaskName "DataBatcher-Daily-US" -Trigger $usDailyTrigger -Action (New-TaskActionForScript -ScriptPath $dailyScript -ExtraArguments "-Target US")
Register-OrUpdateTask -TaskName "DataBatcher-Weekly" -Trigger $weeklyTrigger -Action (New-TaskActionForScript -ScriptPath $weeklyScript)
Register-OrUpdateTask -TaskName "DataBatcher-LogCleanup" -Trigger $cleanupTrigger -Action (New-TaskActionForScript -ScriptPath $cleanupScript)

Write-Host "Done. Daily(KR)=$KrDailyAt Daily(US)=$UsDailyAt Weekly(Sat)=$WeeklyAt Cleanup=$CleanupAt"
