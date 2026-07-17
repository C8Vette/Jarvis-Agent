$processes = Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
    Where-Object { $_.CommandLine -like "*jarvis-agent*" -and $_.CommandLine -like "*main.py --control-center*" }

foreach ($process in $processes) {
    Stop-Process -Id $process.ProcessId -Force
}

if (-not $processes) {
    Write-Output "No Jarvis Control Center process was running."
} else {
    Write-Output "Stopped Jarvis Control Center."
}
