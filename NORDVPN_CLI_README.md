# NordVPN CLI Controller for Windows

A Python-based command-line interface to control NordVPN on Windows programmatically.

## Features

- ✅ Check connection status
- ✅ Start/Stop NordVPN application
- ✅ Connect/Disconnect (via keyboard automation)
- ✅ View settings
- ✅ Process monitoring

## Installation

The controller is already set up in this directory. Required dependencies:
- Python 3.12+
- psutil (already installed)

## Usage

### Windows Batch File (Easiest)

```batch
# Check status
nordvpn.bat status

# Start NordVPN app
nordvpn.bat start

# Stop NordVPN app
nordvpn.bat stop

# Show settings
nordvpn.bat settings

# Connect to VPN
nordvpn.bat connect

# Disconnect from VPN
nordvpn.bat disconnect
```

### PowerShell

```powershell
# Check status
.\nordvpn.ps1 status

# Connect
.\nordvpn.ps1 connect
```

### Direct Python

```powershell
# Using venv python
.\.venv\Scripts\python.exe nordvpn_controller.py status
```

## Python API

You can also import and use the controller in your Python scripts:

```python
from nordvpn_controller import NordVPNController

# Create controller instance
vpn = NordVPNController()

# Check if NordVPN is running
if vpn.is_running():
    print("NordVPN is running")

# Get connection status
status = vpn.get_connection_status()
print(f"Connected: {status['connected']}")
print(f"Status: {status['status']}")

# Start the app
vpn.start_app()

# Connect (triggers quick connect)
vpn.connect_quick()

# Disconnect
vpn.disconnect()

# Get settings
settings = vpn.get_settings()
print(settings)
```

## Commands

| Command | Description |
|---------|-------------|
| `status` | Check current connection status |
| `connect` | Quick connect to VPN |
| `disconnect` | Disconnect from VPN |
| `start` | Start NordVPN application |
| `stop` | Stop NordVPN application |
| `settings` | Display NordVPN settings |

## Limitations

- **Windows GUI Required**: The NordVPN Windows app must be installed
- **Keyboard Automation**: Connect/disconnect use keyboard simulation (may not work if app window is not responsive)
- **No Server Selection**: Quick connect only (cannot specify country/server via this CLI)
- **Settings**: Some settings are read-only from registry

## Advanced Features

### Kill Switch
Kill switch must be enabled/disabled manually in the NordVPN app settings. The CLI cannot control this feature directly without additional UI automation.

### Meshnet
Meshnet features are accessible through the NordVPN app GUI only.

## Troubleshooting

### "Module not found: psutil"
```powershell
.\.venv\Scripts\pip.exe install psutil
```

### "NordVPN app not found"
Make sure NordVPN is installed at: `C:\Program Files\NordVPN\NordVPN.exe`

### Connect/Disconnect not working
The app must be running and responsive. The controller uses keyboard automation which requires the app window to accept input.

## Technical Details

- **Process Detection**: Uses `psutil` to detect running NordVPN processes
- **Network Adapter Detection**: Checks for NordVPN network adapter status
- **Registry Access**: Reads settings from Windows registry
- **Keyboard Automation**: Uses PowerShell COM objects to send keystrokes

## Integration Example

Use in your automation scripts:

```python
import time
from nordvpn_controller import NordVPNController

vpn = NordVPNController()

# Ensure VPN is connected before sensitive operation
if not vpn.get_connection_status()['connected']:
    print("Connecting to VPN...")
    vpn.connect_quick()
    time.sleep(5)  # Wait for connection

# Do your work here
# ...

# Disconnect when done
vpn.disconnect()
```

## Future Enhancements

Potential improvements:
- Direct API integration (if NordVPN provides Windows API)
- Server/country selection
- Protocol selection
- Auto-connect on startup
- Connection monitoring with callbacks
- UI automation for advanced settings

## License

Part of the th_poller project.
