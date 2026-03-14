Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"

$repoRoot = Get-RepoRoot
$envFile = Join-Path $PSScriptRoot "scheduler.env"
$logDir = Join-Path $repoRoot "logs\scheduler"
Ensure-Directory -Path $logDir

$started = Get-Date
$runLog = Join-Path $logDir ("cleanup_{0}.log" -f $started.ToString("yyyyMMdd_HHmmss"))

Load-SchedulerEnv -EnvFile $envFile

$retentionDaysRaw = [System.Environment]::GetEnvironmentVariable("LOG_RETENTION_DAYS", "Process")
$retentionDays = 14
if ($retentionDaysRaw -and ($retentionDaysRaw -as [int])) {
    $retentionDays = [int]$retentionDaysRaw
}

$threshold = (Get-Date).AddDays(-1 * $retentionDays)
$deleted = 0

Write-RunLog -Message "[CLEANUP] start retention=${retentionDays}d threshold=$($threshold.ToString('yyyy-MM-dd HH:mm:ss'))" -LogFile $runLog

Get-ChildItem -LiteralPath $logDir -File -Filter "*.log" |
    Where-Object { $_.LastWriteTime -lt $threshold } |
    ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Force
        $deleted++
    }

$elapsed = [int]((Get-Date) - $started).TotalSeconds
Write-RunLog -Message "[CLEANUP] complete deleted=${deleted} elapsed=${elapsed}s" -LogFile $runLog

$title = "[DataBatcher][LOG-CLEANUP] SUCCESS"
$body = "RetentionDays: $retentionDays`nDeleted: $deleted`nElapsed: ${elapsed}s`nLog: $runLog"
Send-AppriseNotification -Title $title -Body $body -LogFile $runLog

exit 0
