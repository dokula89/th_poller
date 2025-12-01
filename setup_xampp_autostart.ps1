# Add XAMPP startup script to Windows startup folder
# Run this once to automatically start XAMPP on every boot

$scriptDir = $PSScriptRoot
$startupBat = Join-Path $scriptDir "start_xampp.bat"

# Get Windows startup folder
$startupFolder = [Environment]::GetFolderPath("Startup")

# Create shortcut in startup folder
$WshShell = New-Object -ComObject WScript.Shell
$shortcutPath = Join-Path $startupFolder "Start XAMPP.lnk"
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $startupBat
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = "Start XAMPP Apache and MySQL on startup"
$shortcut.Save()

Write-Host "✅ XAMPP startup shortcut created in:"
Write-Host "   $shortcutPath"
Write-Host ""
Write-Host "XAMPP will now start automatically on every system boot."
Write-Host "To remove: Delete the shortcut from your Startup folder"
Write-Host "Location: $startupFolder"
