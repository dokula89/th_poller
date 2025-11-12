# PowerShell script to always restart the poller if it closes
$scriptPath = Join-Path $PSScriptRoot 'launch_poller.pyw'
$pythonExe = 'pythonw.exe'

while ($true) {
    Write-Host "[Watchdog] Starting poller..."
    $proc = Start-Process -FilePath $pythonExe -ArgumentList $scriptPath -PassThru
    $proc.WaitForExit()
    Write-Host "[Watchdog] Poller exited. Restarting in 2 seconds..."
    Start-Sleep -Seconds 2
}
