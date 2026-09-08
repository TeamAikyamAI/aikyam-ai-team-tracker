<#
Registers the tracker as a Windows service that starts with the machine.

  Run in an *elevated* PowerShell from the project root:
    powershell -ExecutionPolicy Bypass -File deploy\windows\install-service.ps1

Uses NSSM (https://nssm.cc) if it is on PATH or in this folder - it is the
most reliable way to run a Python process as a service. If NSSM is not
available, it falls back to a Task Scheduler job that runs at startup.

Before running: backend\venv exists with requirements installed, backend\.env
is filled in, `alembic upgrade head` has been run, and `npm run build` has been
run in frontend\ so the backend can serve the UI on http://localhost:8002.
#>
$ErrorActionPreference = "Stop"
$ServiceName = "AikyamAITracker"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Backend = Join-Path $Root "backend"
$Uvicorn = Join-Path $Backend "venv\Scripts\uvicorn.exe"
$LogDir = Join-Path $Backend "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if (-not (Test-Path $Uvicorn)) { throw "Not found: $Uvicorn - create the venv and pip install -r requirements.txt first" }
if (-not (Test-Path (Join-Path $Backend ".env"))) { throw "backend\.env is missing" }

$nssm = Get-Command nssm.exe -ErrorAction SilentlyContinue
if (-not $nssm -and (Test-Path (Join-Path $PSScriptRoot "nssm.exe"))) { $nssm = Get-Item (Join-Path $PSScriptRoot "nssm.exe") }

if ($nssm) {
    $exe = $nssm.Source ?? $nssm.FullName
    & $exe stop $ServiceName 2>$null | Out-Null
    & $exe remove $ServiceName confirm 2>$null | Out-Null
    & $exe install $ServiceName $Uvicorn "app.main:app --host 127.0.0.1 --port 8002 --workers 1"
    & $exe set $ServiceName AppDirectory $Backend
    & $exe set $ServiceName AppStdout (Join-Path $LogDir "backend.out.log")
    & $exe set $ServiceName AppStderr (Join-Path $LogDir "backend.err.log")
    & $exe set $ServiceName AppRotateFiles 1
    & $exe set $ServiceName AppRotateBytes 10485760
    & $exe set $ServiceName Start SERVICE_AUTO_START
    & $exe set $ServiceName AppRestartDelay 3000
    & $exe start $ServiceName
    Write-Host "Service '$ServiceName' installed and started (NSSM). Logs: $LogDir"
} else {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-backend.ps1`""
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
    Register-ScheduledTask -TaskName $ServiceName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -User "SYSTEM" -Force | Out-Null
    Start-ScheduledTask -TaskName $ServiceName
    Write-Host "NSSM not found - registered Task Scheduler job '$ServiceName' (runs at startup, restarts on failure)."
    Write-Host "For a proper service, download nssm.exe into deploy\windows and re-run this script."
}
Write-Host "Check: http://localhost:8002/api/health"
