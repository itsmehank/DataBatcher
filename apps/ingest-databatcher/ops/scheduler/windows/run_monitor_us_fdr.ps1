Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"

$repoRoot = Get-RepoRoot
$envFile = Join-Path $PSScriptRoot "scheduler.env"
$logDir = Join-Path $repoRoot "logs\scheduler"
Ensure-Directory -Path $logDir

$startAt = Get-Date
$logFile = Join-Path $logDir ("monitor_us_fdr_{0}.log" -f $startAt.ToString("yyyyMMdd_HHmmss"))

Load-SchedulerEnv -EnvFile $envFile
$batchPython = Get-BatchPythonExe
$titlePrefix = "[DataBatcher][MONITOR-US-FDR]"
$mutexName = "Global\DataBatcherMonitorUsFdrLock"

Write-RunLog -Message "[MONITOR-US-FDR] job started" -LogFile $logFile

$mutex = Acquire-SchedulerMutex -Name $mutexName
if ($null -eq $mutex) {
    Write-RunLog -Message "[MONITOR-US-FDR] skipped: another monitor job is running" -LogFile $logFile
    exit 0
}

try {
    if (-not (Test-BatchPythonRuntime -PythonExe $batchPython -LogFile $logFile)) {
        exit 1
    }

    $scriptPath = Join-Path $repoRoot "apps\ingest-databatcher\scripts\monitor_us_fdr_freshness.py"
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        throw "Missing script: $scriptPath"
    }

    $exitCode = Invoke-LoggedProcess -FilePath $batchPython -ArgumentList @($scriptPath) -LogFile $logFile -WorkingDirectory $repoRoot
    $elapsed = [int]((Get-Date) - $startAt).TotalSeconds

    if ($exitCode -eq 0) {
        Write-RunLog -Message "[MONITOR-US-FDR] completed successfully (${elapsed}s)" -LogFile $logFile
        exit 0
    }

    Write-RunLog -Message "[MONITOR-US-FDR] failed (exit=${exitCode}, ${elapsed}s)" -LogFile $logFile
    exit $exitCode
} catch {
    Write-RunLog -Message "[MONITOR-US-FDR] fatal: $($_.Exception.Message)" -LogFile $logFile
    exit 1
} finally {
    Release-SchedulerMutex -Mutex $mutex
}
