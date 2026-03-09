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
Write-RunLog -Message "[WEEKLY] job started" -LogFile $logFile

$mutex = Acquire-SchedulerMutex -Name "Global\DataBatcherWeeklyLock"
if ($null -eq $mutex) {
    Write-RunLog -Message "[WEEKLY] skipped: another weekly job is running" -LogFile $logFile
    Send-AppriseNotification -Title "[DataBatcher][WEEKLY] SKIPPED" -Body "Another weekly run is already active.`nLog: $logFile" -LogFile $logFile
    exit 0
}

try {
    $containerName = [System.Environment]::GetEnvironmentVariable("DOCKER_MYSQL_CONTAINER", "Process")
    if (-not $containerName) {
        $containerName = "databatche_db"
    }

    if (-not (Test-DockerMySqlContainer -ContainerName $containerName)) {
        Write-RunLog -Message "[WEEKLY] docker mysql container not running: $containerName" -LogFile $logFile
        Send-AppriseNotification -Title "[DataBatcher][WEEKLY] FAILED" -Body "MySQL container is not running: $containerName`nLog: $logFile" -LogFile $logFile
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
    $cmd = "cd '$repoPosix' && bash shell_scripts/weekly_all.sh"
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
