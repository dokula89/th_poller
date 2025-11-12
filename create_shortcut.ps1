$WshShell = New-Object -comObject WScript.Shell

# Get the paths
$scriptPath = Join-Path $PSScriptRoot "launch_poller.pyw"
$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Queue Poller.lnk"
$pythonwPath = "pythonw.exe"  # Will use pythonw from PATH

# Create the shortcut
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = "`"$scriptPath`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = "TrustyHousing Queue Poller"

# Set a nice icon - using Python's icon
$pythonPath = (Get-Command python).Source
$shortcut.IconLocation = $pythonPath + ",0"

# Save the shortcut
$shortcut.Save()

Write-Host "Shortcut created on your desktop: 'Queue Poller'"