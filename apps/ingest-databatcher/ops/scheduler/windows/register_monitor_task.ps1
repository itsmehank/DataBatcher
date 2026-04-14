param(
    [string]$StartAt = "00:00"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"

$repoRoot = Get-RepoRoot
$powershellExe = Join-Path $PSHOME "powershell.exe"
$taskName = "DataBatcher-Monitor-US-FDR"
$scriptPath = Join-Path $PSScriptRoot "run_monitor_us_fdr.ps1"

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$quotedScript = '"{0}"' -f $scriptPath
$taskRun = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File $quotedScript"

schtasks /Create /TN $taskName /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST $StartAt /RI 60 /DU 23:59 /TR $taskRun /F | Out-Null
Write-Host "Registered task: $taskName (weekdays hourly from $StartAt)"
