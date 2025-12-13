# NordVPN PowerShell Wrapper
# Provides easy command-line access to NordVPN controller

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$Argument = ""
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "nordvpn_controller.py"

# Check if virtual environment exists
$VenvPath = Join-Path $ScriptDir ".venv"
$PythonExe = if (Test-Path $VenvPath) {
    Join-Path $VenvPath "Scripts\python.exe"
} else {
    "python"
}

# Execute the Python controller
if ($Argument) {
    & $PythonExe $PythonScript $Command $Argument
} else {
    & $PythonExe $PythonScript $Command
}
