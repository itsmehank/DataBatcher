Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
    [ValidateSet("KR", "US")]
    [string]$Target = "KR"
)

. "$PSScriptRoot\common.ps1"

$repoRoot = Get-RepoRoot
$envFile = Join-Path $PSScriptRoot "scheduler.env"
$logDir = Join-Path $repoRoot "logs\scheduler"
Ensure-Directory -Path $logDir

$startAt = Get-Date
$logFile = Join-Path $logDir ("daily_{0}_{1}.log" -f $Target.ToLower(), $startAt.ToString("yyyyMMdd_HHmmss"))

Load-SchedulerEnv -EnvFile $envFile
$scriptByTarget = @{
    "KR" = "shell_scripts/daily_kr.sh"
    "US" = "shell_scripts/daily_us.sh"
}
$mutexByTarget = @{
    "KR" = "Global\DataBatcherDailyKrLock"
    "US" = "Global\DataBatcherDailyUsLock"
}

$targetScript = $scriptByTarget[$Target]
$mutexName = $mutexByTarget[$Target]
$titlePrefix = "[DataBatcher][DAILY-$Target]"

Write-RunLog -Message "[DAILY-$Target] job started" -LogFile $logFile

$mutex = Acquire-SchedulerMutex -Name $mutexName
if ($null -eq $mutex) {
    Write-RunLog -Message "[DAILY-$Target] skipped: another daily-$Target job is running" -LogFile $logFile
    Send-AppriseNotification -Title "$titlePrefix SKIPPED" -Body "Another daily-$Target run is already active.`nLog: $logFile" -LogFile $logFile
    exit 0
}

try {
    $containerName = [System.Environment]::GetEnvironmentVariable("DOCKER_MYSQL_CONTAINER", "Process")
    if (-not $containerName) {
        $containerName = "databatche_db"
    }

    if (-not (Test-DockerMySqlContainer -ContainerName $containerName)) {
        Write-RunLog -Message "[DAILY-$Target] docker mysql container not running: $containerName" -LogFile $logFile
        Send-AppriseNotification -Title "$titlePrefix FAILED" -Body "MySQL container is not running: $containerName`nLog: $logFile" -LogFile $logFile
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
    $cmd = "cd '$repoPosix' && bash $targetScript"
    Write-RunLog -Message "[DAILY-$Target] execute: $cmd" -LogFile $logFile

    & $gitBash -lc $cmd 2>&1 | ForEach-Object { Write-RunLog -Message $_ -LogFile $logFile }
    $exitCode = $LASTEXITCODE
    $elapsed = [int]((Get-Date) - $startAt).TotalSeconds

    if ($exitCode -eq 0) {
        Write-RunLog -Message "[DAILY-$Target] completed successfully (${elapsed}s)" -LogFile $logFile
        Send-AppriseNotification -Title "$titlePrefix SUCCESS" -Body "ExitCode: 0`nElapsed: ${elapsed}s`nLog: $logFile" -LogFile $logFile
        exit 0
    }

    Write-RunLog -Message "[DAILY-$Target] failed (exit=${exitCode}, ${elapsed}s)" -LogFile $logFile
    Send-AppriseNotification -Title "$titlePrefix FAILED" -Body "ExitCode: $exitCode`nElapsed: ${elapsed}s`nLog: $logFile" -LogFile $logFile
    exit $exitCode
} catch {
    Write-RunLog -Message "[DAILY-$Target] fatal: $($_.Exception.Message)" -LogFile $logFile
    Send-AppriseNotification -Title "$titlePrefix FAILED" -Body "Fatal error: $($_.Exception.Message)`nLog: $logFile" -LogFile $logFile
    exit 1
} finally {
    Release-SchedulerMutex -Mutex $mutex
}
