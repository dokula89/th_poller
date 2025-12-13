#!/bin/bash
# Queue Poller - MacOS Start Script
# Run this script to start the Queue Poller application on Mac

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "╔════════════════════════════════════════╗"
echo "║     🚀 Queue Poller for Mac           ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "📁 Working directory: $SCRIPT_DIR"
echo ""

cd "$SCRIPT_DIR"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    echo ""
    echo "To install Python 3, run:"
    echo "  brew install python3"
    echo ""
    echo "If Homebrew is not installed, first run:"
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo ""
    # Open the setup guide
    if [ -f "MAC_SETUP_GUIDE.txt" ]; then
        echo "Opening setup guide..."
        open "MAC_SETUP_GUIDE.txt"
    fi
    read -p "Press Enter to exit..."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        echo "Try: brew install python3"
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📥 Checking dependencies..."
    pip install -r requirements.txt --quiet 2>/dev/null
fi

# Install required packages if not present
echo "🔍 Checking required packages..."
python3 -c "import mysql.connector" 2>/dev/null || {
    echo "   Installing mysql-connector-python..."
    pip install mysql-connector-python --quiet
}

python3 -c "import requests" 2>/dev/null || {
    echo "   Installing requests..."
    pip install requests --quiet
}

python3 -c "import PIL" 2>/dev/null || {
    echo "   Installing Pillow..."
    pip install Pillow --quiet
}

python3 -c "import pyautogui" 2>/dev/null || {
    echo "   Installing pyautogui..."
    pip install pyautogui --quiet
}

# Check for tkinter
python3 -c "import tkinter" 2>/dev/null || {
    echo ""
    echo "⚠️  tkinter not found!"
    echo "   On Mac, try: brew install python-tk"
    echo ""
    read -p "Press Enter to continue anyway..."
}

# Check for Tesseract
if ! command -v tesseract &> /dev/null; then
    echo ""
    echo "⚠️  Tesseract OCR not found (needed for parcel automation)"
    echo "   To install: brew install tesseract"
    echo ""
fi

echo ""
echo "▶️  Launching Queue Poller..."
echo "════════════════════════════════════════"
echo ""

# Run the application
python3 run_poller.py

# Capture exit code
EXIT_CODE=$?

# Deactivate venv on exit
deactivate

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Application exited with error code: $EXIT_CODE"
    echo "   Check poller_log.txt for details"
    read -p "Press Enter to exit..."
fi
