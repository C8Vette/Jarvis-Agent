$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$logDir = Join-Path (Get-Location) "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$stdout = Join-Path $logDir "control-center-stdout.log"
$stderr = Join-Path $logDir "control-center-stderr.log"

& ".\.venv\Scripts\python.exe" "main.py" "--control-center" *> $stdout 2> $stderr
