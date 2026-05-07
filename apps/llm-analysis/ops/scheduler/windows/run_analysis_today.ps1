# Phase 1 LLM 분석 자동·수동 진입점 (ADR-012 §2)
# brief §8.3.1 — Windows Task Scheduler가 매일 정시에 호출하는 wrapper.
#
# Usage:
#   .\run_analysis_today.ps1                  # 그날 region 모두 (KR + US)
#   .\run_analysis_today.ps1 -Region KR       # 한 region만
#   .\run_analysis_today.ps1 -Region US -DryRun           # 호출 안 하고 대상만 확인
#   .\run_analysis_today.ps1 -ForceRecompute              # 캐시 무시 재계산
#   .\run_analysis_today.ps1 -Date 2026-05-08             # 특정 날짜
#
# 통제권 메커니즘 (ADR-012 §5):
#   1) 일시 중단:  Disable-ScheduledTask -TaskName "LLMAnalysis_US" / "LLMAnalysis_KR"
#   2) 킬 스위치: settings.yaml의 modules.{analyze_chart, calculate_entry_params}=false
#   3) 부분 비활성화: settings.yaml의 daily_call_limits.{kr,us} 값을 0으로
#   4) 매매 게이트 부재 (헌법 §2.1) — 본 스크립트는 분석만 수행, 주문 없음

param(
    [ValidateSet("KR", "US", "BOTH")]
    [string]$Region = "BOTH",
    [string]$Date = "",
    [switch]$DryRun,
    [switch]$ForceRecompute,
    [int]$Limit = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# Repo root 결정 (본 파일은 apps/llm-analysis/ops/scheduler/windows/ 에 위치)
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\..")).Path

# Python 인터프리터: llm-analysis venv 우선, 없으면 시스템 python
$venvPython = Join-Path $repoRoot "apps\llm-analysis\venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "python"
}

# 로그 디렉토리
$logDir = Join-Path $repoRoot "logs\scheduler"
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$startedAt = Get-Date
$dateStr = if ($Date) { $Date } else { $startedAt.ToString("yyyy-MM-dd") }
$logFile = Join-Path $logDir ("llm_analysis_{0}_{1}.log" -f $Region.ToLower(), $startedAt.ToString("yyyyMMdd_HHmmss"))

function Write-Log {
    param([string]$Msg)
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $Msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Write-Log "===== LLMAnalysis wrapper start ====="
Write-Log "repoRoot=$repoRoot"
Write-Log "pythonExe=$pythonExe"
Write-Log "Region=$Region Date=$dateStr DryRun=$DryRun ForceRecompute=$ForceRecompute Limit=$Limit"

# run_daily_analysis.py 실행
$scriptPath = Join-Path $repoRoot "apps\llm-analysis\scripts\run_daily_analysis.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    Write-Log "[ERROR] run_daily_analysis.py not found: $scriptPath"
    exit 1
}

$pyArgs = @(
    $scriptPath,
    "--region", $Region,
    "--date", $dateStr
)
if ($DryRun) { $pyArgs += "--dry-run" }
if ($ForceRecompute) { $pyArgs += "--force-recompute" }
if ($Limit -gt 0) { $pyArgs += "--limit"; $pyArgs += "$Limit" }

Write-Log "exec: $pythonExe $($pyArgs -join ' ')"

# Stdout/stderr를 로그에 모두 캡처. 종료 코드는 그대로 propagate.
& $pythonExe @pyArgs 2>&1 | Tee-Object -FilePath $logFile -Append
$exitCode = $LASTEXITCODE
Write-Log "run_daily_analysis exit=$exitCode"

# 결과 요약 출력 (실패해도 best-effort)
$summaryScript = Join-Path $repoRoot "apps\llm-analysis\scripts\show_cost_summary.py"
if (Test-Path -LiteralPath $summaryScript) {
    Write-Log "===== cost summary (last 1 day) ====="
    & $pythonExe $summaryScript --days 1 2>&1 | Tee-Object -FilePath $logFile -Append
}

$elapsed = ((Get-Date) - $startedAt).TotalSeconds
Write-Log "===== LLMAnalysis wrapper end exit=$exitCode elapsed=${elapsed}s ====="

exit $exitCode
