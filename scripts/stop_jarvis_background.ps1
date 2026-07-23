$root = Split-Path -Parent $PSScriptRoot

& "$root\scripts\stop_jarvis_voice.ps1"
& "$root\scripts\stop_control_center.ps1"

Write-Output "Jarvis background services stopped."
