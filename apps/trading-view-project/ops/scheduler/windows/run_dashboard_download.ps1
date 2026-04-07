Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
    [string]$EnvFile = (Join-Path $PSScriptRoot "scheduler.us-nasdaq.env"),
    [string]$JobName = "US-NASDAQ"
)

. "$PSScriptRoot\common.ps1"

$projectRoot = Get-ProjectRoot
$logDir = Join-Path $projectRoot "automation\logs"
Ensure-Directory -Path $logDir

$startAt = Get-Date
$jobSlug = $JobName.ToLower().Replace(" ", "-").Replace("_", "-")
$logFile = Join-Path $logDir ("windows_scheduler_{0}_{1}.log" -f $jobSlug, $startAt.ToString("yyyyMMdd_HHmmss"))
$mutex = $null

try {
    Load-SchedulerEnv -EnvFile $envFile

    $mutex = Acquire-SchedulerMutex -Name ("Global\DataBatcherTradingViewDashboardDownload-{0}" -f $jobSlug)
    if ($null -eq $mutex) {
        Write-RunLog -Message ("[WINDOWS-SCHEDULER][{0}] skipped: another dashboard download job is running" -f $JobName) -LogFile $logFile
        exit 0
    }

    $gitBash = [System.Environment]::GetEnvironmentVariable("GIT_BASH_EXE", "Process")
    if (-not $gitBash) {
        throw "GIT_BASH_EXE is not set"
    }
    if (-not (Test-Path -LiteralPath $gitBash)) {
        throw "Git Bash not found: $gitBash"
    }

    $nodeBin = [System.Environment]::GetEnvironmentVariable("NODE_BIN", "Process")
    if (-not $nodeBin) {
        throw "NODE_BIN is not set"
    }
    if (-not (Test-Path -LiteralPath $nodeBin)) {
        throw "Node executable not found: $nodeBin"
    }

    $scriptPath = Join-Path $projectRoot "ops\shell\run_dashboard_download.sh"
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        throw "Missing script: $scriptPath"
    }

    $projectPosix = Convert-ToPosixPath -WindowsPath $projectRoot
    $scriptPosix = Convert-ToPosixPath -WindowsPath $scriptPath
    $nodePosix = Convert-ToPosixPath -WindowsPath $nodeBin

    $frontendUrl = [System.Environment]::GetEnvironmentVariable("FRONTEND_URL", "Process")
    $region = [System.Environment]::GetEnvironmentVariable("REGION", "Process")
    $market = [System.Environment]::GetEnvironmentVariable("MARKET", "Process")
    $listCategory = [System.Environment]::GetEnvironmentVariable("LIST_CATEGORY", "Process")
    $headless = [System.Environment]::GetEnvironmentVariable("HEADLESS", "Process")
    $dateValue = [System.Environment]::GetEnvironmentVariable("DATE", "Process")
    $outputDir = [System.Environment]::GetEnvironmentVariable("OUTPUT_DIR", "Process")

    if (-not $frontendUrl) { $frontendUrl = "http://127.0.0.1:5173" }
    if (-not $region) { $region = "US" }
    if (-not $listCategory) { $listCategory = "all" }
    if (-not $headless) { $headless = "true" }
    if (-not $market) {
        throw "MARKET is not set"
    }

    $envPairs = @(
        "NODE_BIN=$(Convert-ToBashLiteral -Value $nodePosix)",
        "FRONTEND_URL=$(Convert-ToBashLiteral -Value $frontendUrl)",
        "REGION=$(Convert-ToBashLiteral -Value $region)",
        "MARKET=$(Convert-ToBashLiteral -Value $market)",
        "LIST_CATEGORY=$(Convert-ToBashLiteral -Value $listCategory)",
        "HEADLESS=$(Convert-ToBashLiteral -Value $headless)"
    )

    if ($dateValue) {
        $envPairs += "DATE=$(Convert-ToBashLiteral -Value $dateValue)"
    }

    if ($outputDir) {
        Ensure-Directory -Path $outputDir
        $outputPosix = Convert-ToPosixPath -WindowsPath $outputDir
        $envPairs += "OUTPUT_DIR=$(Convert-ToBashLiteral -Value $outputPosix)"
    }

    $cmd = "cd $(Convert-ToBashLiteral -Value $projectPosix) && $($envPairs -join ' ') bash $(Convert-ToBashLiteral -Value $scriptPosix)"

    Write-RunLog -Message ("[WINDOWS-SCHEDULER][{0}] env_file={1}" -f $JobName, $EnvFile) -LogFile $logFile
    Write-RunLog -Message ("[WINDOWS-SCHEDULER][{0}] execute: {1}" -f $JobName, $cmd) -LogFile $logFile
    & $gitBash -lc $cmd 2>&1 | ForEach-Object { Write-RunLog -Message $_ -LogFile $logFile }
    $exitCode = $LASTEXITCODE
    $elapsed = [int]((Get-Date) - $startAt).TotalSeconds

    if ($exitCode -eq 0) {
        Write-RunLog -Message ("[WINDOWS-SCHEDULER][{0}] completed successfully ({1}s)" -f $JobName, $elapsed) -LogFile $logFile
        exit 0
    }

    Write-RunLog -Message ("[WINDOWS-SCHEDULER][{0}] failed (exit={1}, {2}s)" -f $JobName, $exitCode, $elapsed) -LogFile $logFile
    exit $exitCode
} catch {
    Write-RunLog -Message ("[WINDOWS-SCHEDULER][{0}] fatal: {1}" -f $JobName, $_.Exception.Message) -LogFile $logFile
    exit 1
} finally {
    Release-SchedulerMutex -Mutex $mutex
}
