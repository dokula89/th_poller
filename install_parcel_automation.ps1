# Install Parcel Automation Dependencies
# Run this script to install all required packages for parcel automation

Write-Host "Installing parcel automation dependencies..." -ForegroundColor Cyan
Write-Host ""

# Upgrade pip first
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install all requirements
Write-Host ""
Write-Host "Installing packages from requirements.txt..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "✓ Python packages installed!" -ForegroundColor Green
Write-Host ""

# Check for Tesseract OCR
Write-Host "Checking for Tesseract OCR..." -ForegroundColor Yellow
$tesseractPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"

if (Test-Path $tesseractPath) {
    Write-Host "✓ Tesseract OCR found at: $tesseractPath" -ForegroundColor Green
    # Set user environment variable for Python to auto-detect
    try {
        [System.Environment]::SetEnvironmentVariable("TESSERACT_PATH", $tesseractPath, "User")
        Write-Host "Set TESSERACT_PATH user env var to: $tesseractPath" -ForegroundColor Green
        Write-Host "You may need to restart apps for env var to take effect." -ForegroundColor Yellow
    } catch {
        Write-Host "Could not set TESSERACT_PATH env var: $_" -ForegroundColor Red
    }
} else {
    Write-Host "⚠ Tesseract OCR not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Tesseract OCR:" -ForegroundColor Yellow
    Write-Host "1. Download from: https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor White
    Write-Host "2. Run the installer" -ForegroundColor White
    Write-Host "3. Install to: C:\Program Files\Tesseract-OCR\" -ForegroundColor White
    Write-Host "4. Re-run this script to set TESSERACT_PATH automatically" -ForegroundColor White
    Write-Host ""
}

# Check for Chrome
Write-Host ""
Write-Host "Checking for Google Chrome..." -ForegroundColor Yellow
$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

$chromeFound = $false
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        Write-Host "✓ Chrome found at: $path" -ForegroundColor Green
        $chromeFound = $true
        break
    }
}

if (-not $chromeFound) {
    Write-Host "⚠ Chrome not found!" -ForegroundColor Red
    Write-Host "Please install Google Chrome from: https://www.google.com/chrome/" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Setup Status:" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

if ($chromeFound -and (Test-Path $tesseractPath)) {
    Write-Host "✓ All dependencies ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now use the 'Start Parcel Capture' button" -ForegroundColor White
    Write-Host "in the Empty Parcels window to automate data collection." -ForegroundColor White
} else {
    Write-Host "⚠ Manual installation required (see above)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "See PARCEL_AUTOMATION_SETUP.md for detailed instructions" -ForegroundColor White
}

Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
