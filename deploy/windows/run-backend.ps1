# Starts the backend the way production should run it: one worker, no reload.
# Used by install-service.ps1; you can also run it by hand.
$ErrorActionPreference = "Stop"
$Backend = Resolve-Path (Join-Path $PSScriptRoot "..\..\backend")
Set-Location $Backend
& "$Backend\venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8002 --workers 1
