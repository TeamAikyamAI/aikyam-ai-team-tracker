<#
Nightly backup of the database and uploaded BRDs, keeping the last 14.
  Schedule (elevated PowerShell):
    schtasks /Create /TN "AikyamAITracker Backup" /SC DAILY /ST 02:30 /RU SYSTEM /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"<full path>\deploy\windows\backup.ps1\""
Set PGPASSWORD in the environment, or use a %APPDATA%\postgresql\pgpass.conf entry, so pg_dump does not prompt.
#>
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$BackupDir = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { Join-Path $Root "backups" }
$DbName = if ($env:DB_NAME) { $env:DB_NAME } else { "aikyam_ai_tracker" }
$Keep = 14
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$pgDump = Get-Command pg_dump.exe -ErrorAction SilentlyContinue
if (-not $pgDump) { $pgDump = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\pg_dump.exe" -ErrorAction SilentlyContinue | Select-Object -Last 1 }
if (-not $pgDump) { throw "pg_dump.exe not found - add PostgreSQL\bin to PATH" }
$exe = if ($pgDump.Source) { $pgDump.Source } else { $pgDump.FullName }

& $exe --format=custom --file="$BackupDir\db-$Stamp.dump" --username=postgres --host=localhost $DbName
Compress-Archive -Path (Join-Path $Root "backend\uploads\*") -DestinationPath "$BackupDir\uploads-$Stamp.zip" -Force

Get-ChildItem "$BackupDir\db-*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -Skip $Keep | Remove-Item -Force
Get-ChildItem "$BackupDir\uploads-*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -Skip $Keep | Remove-Item -Force
Write-Host "backup ok: $BackupDir\db-$Stamp.dump"
# Restore:  pg_restore --clean --if-exists -U postgres -d aikyam_ai_tracker db-<stamp>.dump
