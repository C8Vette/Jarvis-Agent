$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$logDir = Join-Path (Get-Location) "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$stdout = Join-Path $logDir "voice-stdout.log"
$stderr = Join-Path $logDir "voice-stderr.log"

$running = Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
    Where-Object { $_.CommandLine -like "*jarvis-agent*" -and $_.CommandLine -like "*main.py --voice*" }

if ($running) {
    Write-Output "Jarvis voice mode is already running."
    exit 0
}

& ".\.venv\Scripts\python.exe" "main.py" "--voice" *> $stdout 2> $stderr
