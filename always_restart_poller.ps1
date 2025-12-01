# PowerShell script to always restart the poller if it closes
# Also ensures PHP server is running

$scriptPath = Join-Path $PSScriptRoot 'launch_poller.pyw'
$pythonExe = 'pythonw.exe'
$phpPath = 'C:\xampp\php\php.exe'
$webRoot = Join-Path $PSScriptRoot 'htdocs'
$phpPort = 8000

# Function to check if PHP server is running
function Test-PhpServerRunning {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$phpPort" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        return $true
    } catch {
        return $false
    }
}

# Function to start PHP server
function Start-PhpServer {
    $phpProcess = Get-Process -Name php -ErrorAction SilentlyContinue
    if (-not $phpProcess) {
        Write-Host "[Watchdog] Starting PHP server on port $phpPort..."
        Start-Process -FilePath $phpPath `
            -ArgumentList "-S localhost:$phpPort" `
            -WorkingDirectory $webRoot `
            -WindowStyle Hidden
        Start-Sleep -Seconds 2
        
        if (Test-PhpServerRunning) {
            Write-Host "[Watchdog] ✓ PHP server started successfully"
        } else {
            Write-Host "[Watchdog] ⚠ PHP server may not be responding"
        }
    }
}

# Start PHP server initially
Start-PhpServer

# Main watchdog loop
while ($true) {
    # Check PHP server every loop iteration
    if (-not (Test-PhpServerRunning)) {
        Write-Host "[Watchdog] PHP server not responding, restarting..."
        Stop-Process -Name php -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        Start-PhpServer
    }
    
    # Start/restart poller
    Write-Host "[Watchdog] Starting poller..."
    $proc = Start-Process -FilePath $pythonExe -ArgumentList $scriptPath -PassThru
    $proc.WaitForExit()
    Write-Host "[Watchdog] Poller exited. Restarting in 2 seconds..."
    Start-Sleep -Seconds 2
}
