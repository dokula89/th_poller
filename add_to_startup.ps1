# PowerShell script to add always_restart_poller.ps1 to Windows startup
$script = "c:\Users\dokul\Desktop\robot\th_poller\always_restart_poller.ps1"
$shortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\AlwaysRestartPoller.lnk"
$wshell = New-Object -ComObject WScript.Shell
$sc = $wshell.CreateShortcut($shortcut)
$sc.TargetPath = "powershell.exe"
$sc.Arguments = "-ExecutionPolicy Bypass -File `"$script`""
$sc.WorkingDirectory = [System.IO.Path]::GetDirectoryName($script)
$sc.Save()
