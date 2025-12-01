#!/bin/bash
# Queue Poller Startup Script for macOS/Linux

echo "Starting Queue Poller..."
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -f ".venv/bin/activate" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        echo "Please ensure Python 3 is installed"
        read -p "Press enter to exit..."
        exit 1
    fi
fi

# Activate virtual environment
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment"
    read -p "Press enter to exit..."
    exit 1
fi

# Check if dependencies are installed
python -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        read -p "Press enter to exit..."
        exit 1
    fi
fi

# Start the application
echo ""
echo "Starting Queue Poller..."
python config_hud.py

# Check exit status
if [ $? -ne 0 ]; then
    echo ""
    echo "Error: Application exited with error code $?"
    read -p "Press enter to exit..."
fi
