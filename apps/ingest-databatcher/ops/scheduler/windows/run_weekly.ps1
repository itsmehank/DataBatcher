Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"

$repoRoot = Get-RepoRoot
$envFile = Join-Path $PSScriptRoot "scheduler.env"
$logDir = Join-Path $repoRoot "logs\scheduler"
Ensure-Directory -Path $logDir

$startAt = Get-Date
$logFile = Join-Path $logDir ("weekly_{0}.log" -f $startAt.ToString("yyyyMMdd_HHmmss"))

Load-SchedulerEnv -EnvFile $envFile
$batchPython = Get-BatchPythonExe
Write-RunLog -Message "[WEEKLY] job started" -LogFile $logFile

$mutex = Acquire-SchedulerMutex -Name "Global\DataBatcherWeeklyLock"
if ($null -eq $mutex) {
    Write-RunLog -Message "[WEEKLY] skipped: another weekly job is running" -LogFile $logFile
    Send-AppriseNotification -Title "[DataBatcher][WEEKLY] SKIPPED" -Body "Another weekly run is already active.`nLog: $logFile" -LogFile $logFile
    exit 0
}

try {
    if (-not (Test-BatchPythonRuntime -PythonExe $batchPython -LogFile $logFile)) {
        Send-AppriseNotification -Title "[DataBatcher][WEEKLY] FAILED" -Body "Batch Python runtime check failed.`nPython: $batchPython`nLog: $logFile" -LogFile $logFile
        exit 1
    }

    $healthcheckScript = Join-Path $repoRoot "scripts\healthcheck_db.py"
    if (-not (Test-Path -LiteralPath $healthcheckScript)) {
        throw "Missing script: $healthcheckScript"
    }
    Write-RunLog -Message "[WEEKLY] DB healthcheck start" -LogFile $logFile
    & $batchPython $healthcheckScript 2>&1 | ForEach-Object { Write-RunLog -Message $_ -LogFile $logFile }
    if ($LASTEXITCODE -ne 0) {
        Write-RunLog -Message "[WEEKLY] DB healthcheck failed (exit=$LASTEXITCODE)" -LogFile $logFile
        Send-AppriseNotification -Title "[DataBatcher][WEEKLY] FAILED" -Body "DB healthcheck failed (exit=$LASTEXITCODE).`nLog: $logFile" -LogFile $logFile
        exit 1
    }

    $gitBash = [System.Environment]::GetEnvironmentVariable("GIT_BASH_EXE", "Process")
    if (-not $gitBash) {
        $gitBash = "C:\Program Files\Git\bin\bash.exe"
    }
    if (-not (Test-Path -LiteralPath $gitBash)) {
        throw "Git Bash not found: $gitBash"
    }

    $repoPosix = Convert-ToPosixPath -WindowsPath $repoRoot
    $pythonForBash = $batchPython
    if (Test-Path -LiteralPath $batchPython) {
        $pythonForBash = Convert-ToPosixPath -WindowsPath $batchPython
    }
    $cmd = "cd '$repoPosix' && PYTHON_BIN='$pythonForBash' bash apps/ingest-databatcher/ops/shell/weekly_all.sh"
    Write-RunLog -Message "[WEEKLY] execute: $cmd" -LogFile $logFile

    & $gitBash -lc $cmd 2>&1 | ForEach-Object { Write-RunLog -Message $_ -LogFile $logFile }
    $exitCode = $LASTEXITCODE
    $elapsed = [int]((Get-Date) - $startAt).TotalSeconds

    if ($exitCode -eq 0) {
        Write-RunLog -Message "[WEEKLY] completed successfully (${elapsed}s)" -LogFile $logFile
        Send-AppriseNotification -Title "[DataBatcher][WEEKLY] SUCCESS" -Body "ExitCode: 0`nElapsed: ${elapsed}s`nLog: $logFile" -LogFile $logFile
        exit 0
    }

    Write-RunLog -Message "[WEEKLY] failed (exit=${exitCode}, ${elapsed}s)" -LogFile $logFile
    Send-AppriseNotification -Title "[DataBatcher][WEEKLY] FAILED" -Body "ExitCode: $exitCode`nElapsed: ${elapsed}s`nLog: $logFile" -LogFile $logFile
    exit $exitCode
} catch {
    Write-RunLog -Message "[WEEKLY] fatal: $($_.Exception.Message)" -LogFile $logFile
    Send-AppriseNotification -Title "[DataBatcher][WEEKLY] FAILED" -Body "Fatal error: $($_.Exception.Message)`nLog: $logFile" -LogFile $logFile
    exit 1
} finally {
    Release-SchedulerMutex -Mutex $mutex
}
