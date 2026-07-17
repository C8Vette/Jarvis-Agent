$root = "C:\Users\tsmgr\Documents\jarvis-agent"
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell

function New-JarvisShortcut {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string]$Description
    )

    $shortcutPath = Join-Path $desktop "$Name.lnk"
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`""
    $shortcut.WorkingDirectory = $root
    $shortcut.Description = $Description
    $shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,220"
    $shortcut.Save()

    if (-not (Test-Path $shortcutPath)) {
        throw "Failed to create shortcut: $shortcutPath"
    }

    Write-Output "Created $shortcutPath"
}

New-JarvisShortcut `
    -Name "Start Jarvis" `
    -ScriptPath "$root\scripts\start_jarvis_background.ps1" `
    -Description "Start Jarvis Control Center and voice mode in the background."

New-JarvisShortcut `
    -Name "Stop Jarvis" `
    -ScriptPath "$root\scripts\stop_jarvis_background.ps1" `
    -Description "Stop Jarvis background services."

New-JarvisShortcut `
    -Name "Jarvis Control Center" `
    -ScriptPath "$root\scripts\start_control_center.ps1" `
    -Description "Start the Jarvis Control Center."

Write-Output "Jarvis shortcuts installed on the Desktop."
