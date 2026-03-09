Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
}

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-RunLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [Parameter(Mandatory = $true)]
        [string]$LogFile
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Load-SchedulerEnv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EnvFile
    )

    if (-not (Test-Path -LiteralPath $EnvFile)) {
        throw "scheduler env file not found: $EnvFile"
    }

    Get-Content -LiteralPath $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { return }
        $key = $line.Substring(0, $idx).Trim()
        $value = $line.Substring($idx + 1).Trim()
        [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}

function Convert-ToPosixPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WindowsPath
    )

    $full = (Resolve-Path $WindowsPath).Path
    $replaced = $full.Replace("\", "/")
    if ($replaced -match "^([A-Za-z]):/(.*)$") {
        $drive = $matches[1].ToLower()
        $rest = $matches[2]
        return "/$drive/$rest"
    }
    return $replaced
}

function Acquire-SchedulerMutex {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $createdNew = $false
    $mutex = New-Object System.Threading.Mutex($true, $Name, [ref]$createdNew)
    if (-not $createdNew) {
        $mutex.Dispose()
        return $null
    }
    return $mutex
}

function Release-SchedulerMutex {
    param(
        [Parameter(Mandatory = $false)]
        [System.Threading.Mutex]$Mutex
    )

    if ($null -ne $Mutex) {
        try {
            $Mutex.ReleaseMutex() | Out-Null
        } catch {
        } finally {
            $Mutex.Dispose()
        }
    }
}

function Send-AppriseNotification {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [Parameter(Mandatory = $true)]
        [string]$Body,
        [Parameter(Mandatory = $true)]
        [string]$LogFile
    )

    $pythonExe = [System.Environment]::GetEnvironmentVariable("SCHEDULER_PYTHON_EXE", "Process")
    if (-not $pythonExe) {
        $pythonExe = "python"
    }

    $appriseUrlsRaw = [System.Environment]::GetEnvironmentVariable("APPRISE_URLS", "Process")
    if (-not $appriseUrlsRaw) {
        Write-RunLog -Message "APPRISE_URLS not set. Skip notification." -LogFile $LogFile
        return
    }

    $urls = $appriseUrlsRaw.Split(";", [System.StringSplitOptions]::RemoveEmptyEntries)
    if ($urls.Count -eq 0) {
        Write-RunLog -Message "APPRISE_URLS is empty. Skip notification." -LogFile $LogFile
        return
    }

    $args = @("-m", "apprise", "-t", $Title, "-b", $Body)
    foreach ($url in $urls) {
        $args += "-u"
        $args += $url.Trim()
    }

    try {
        & $pythonExe @args | Out-Null
        Write-RunLog -Message "Notification sent via Apprise." -LogFile $LogFile
    } catch {
        Write-RunLog -Message "Notification failed: $($_.Exception.Message)" -LogFile $LogFile
    }
}

function Test-DockerMySqlContainer {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ContainerName
    )

    $output = & docker ps --format "{{.Names}}" 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    return $output -contains $ContainerName
}
