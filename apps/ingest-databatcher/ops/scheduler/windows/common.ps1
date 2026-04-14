Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\.."))
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
        [object]$Message,
        [Parameter(Mandatory = $true)]
        [string]$LogFile
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $([string]$Message)"
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

function Get-BatchPythonExe {
    $batchPython = [System.Environment]::GetEnvironmentVariable("BATCH_PYTHON_EXE", "Process")
    if (-not $batchPython) {
        $batchPython = [System.Environment]::GetEnvironmentVariable("SCHEDULER_PYTHON_EXE", "Process")
    }
    if (-not $batchPython) {
        $batchPython = "python"
    }

    $batchPython = $batchPython.Trim()
    $looksLikePath = $batchPython.Contains("\\") -or $batchPython.Contains("/") -or $batchPython.Contains(":")
    if ($looksLikePath -and -not (Test-Path -LiteralPath $batchPython)) {
        throw "Batch Python not found: $batchPython"
    }

    return $batchPython
}

function Test-BatchPythonRuntime {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [Parameter(Mandatory = $true)]
        [string]$LogFile
    )

    try {
        & $PythonExe -c "import pandas, sqlalchemy, pymysql, yaml, dotenv" 2>&1 | ForEach-Object { Write-RunLog -Message $_ -LogFile $LogFile }
        if ($LASTEXITCODE -ne 0) {
            Write-RunLog -Message "Batch Python runtime check failed (exit=$LASTEXITCODE)" -LogFile $LogFile
            return $false
        }
        return $true
    } catch {
        Write-RunLog -Message "Batch Python runtime check error: $($_.Exception.Message)" -LogFile $LogFile
        return $false
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
        $pythonExe = [System.Environment]::GetEnvironmentVariable("BATCH_PYTHON_EXE", "Process")
    }
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

function Invoke-LoggedProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $false)]
        [string[]]$ArgumentList = @(),
        [Parameter(Mandatory = $true)]
        [string]$LogFile,
        [Parameter(Mandatory = $false)]
        [string]$WorkingDirectory = ""
    )

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $FilePath
        $quotedArgs = @()
        foreach ($arg in $ArgumentList) {
            if ($null -eq $arg) {
                $quotedArgs += '""'
            } else {
                $escaped = ([string]$arg).Replace('"', '\"')
                if ($escaped.IndexOfAny([char[]]' "') -ge 0) {
                    $quotedArgs += ('"{0}"' -f $escaped)
                } else {
                    $quotedArgs += $escaped
                }
            }
        }
        $startInfo.Arguments = ($quotedArgs -join ' ')
        if ($WorkingDirectory) {
            $startInfo.WorkingDirectory = $WorkingDirectory
        }
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.CreateNoWindow = $true

        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $startInfo
        $stdoutWriter = [System.IO.StreamWriter]::new($stdoutPath, $false, [System.Text.Encoding]::UTF8)
        $stderrWriter = [System.IO.StreamWriter]::new($stderrPath, $false, [System.Text.Encoding]::UTF8)

        try {
            $process.Start() | Out-Null
            while (-not $process.HasExited) {
                while (-not $process.StandardOutput.EndOfStream) {
                    $line = $process.StandardOutput.ReadLine()
                    $stdoutWriter.WriteLine($line)
                    Write-RunLog -Message $line -LogFile $LogFile
                }
                while (-not $process.StandardError.EndOfStream) {
                    $line = $process.StandardError.ReadLine()
                    $stderrWriter.WriteLine($line)
                    Write-RunLog -Message $line -LogFile $LogFile
                }
                Start-Sleep -Milliseconds 100
            }

            while (-not $process.StandardOutput.EndOfStream) {
                $line = $process.StandardOutput.ReadLine()
                $stdoutWriter.WriteLine($line)
                Write-RunLog -Message $line -LogFile $LogFile
            }
            while (-not $process.StandardError.EndOfStream) {
                $line = $process.StandardError.ReadLine()
                $stderrWriter.WriteLine($line)
                Write-RunLog -Message $line -LogFile $LogFile
            }

            $process.WaitForExit()
            return $process.ExitCode
        } finally {
            $stdoutWriter.Dispose()
            $stderrWriter.Dispose()
            $process.Dispose()
        }
    } finally {
        Remove-Item -LiteralPath $stdoutPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }
}
