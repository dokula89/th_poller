# PowerShell script to keep AnyDesk always running
$anydeskPath = "C:\Users\Public\Desktop\AnyDesk.lnk"
$checkInterval = 5  # seconds

while ($true) {
    $running = Get-Process -Name "AnyDesk" -ErrorAction SilentlyContinue
    if (-not $running) {
        Write-Host "AnyDesk not running. Starting..."
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c start \"\" \"$anydeskPath\""
    }
    Start-Sleep -Seconds $checkInterval
}
