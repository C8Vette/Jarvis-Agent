$root = Split-Path -Parent $PSScriptRoot

Start-Process -WindowStyle Hidden -FilePath "powershell.exe" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "$root\scripts\start_control_center.ps1"
Start-Process -WindowStyle Hidden -FilePath "powershell.exe" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "$root\scripts\start_jarvis_voice.ps1"

Write-Output "Started Jarvis Control Center and voice mode."
