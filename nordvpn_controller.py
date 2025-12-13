"""
NordVPN Controller for Windows
Provides CLI-like functionality to control NordVPN Windows app programmatically
"""

import subprocess
import time
import psutil
import winreg
from typing import Optional, Dict, List
import json


class NordVPNController:
    """Control NordVPN Windows application programmatically"""
    
    def __init__(self):
        self.app_path = r"C:\Program Files\NordVPN\NordVPN.exe"
        self.process_name = "NordVPN.exe"
        
    def is_running(self) -> bool:
        """Check if NordVPN app is running"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] == self.process_name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    
    def start_app(self) -> bool:
        """Start NordVPN application"""
        try:
            if not self.is_running():
                subprocess.Popen([self.app_path], shell=True)
                time.sleep(3)  # Wait for app to start
                return True
            return True
        except Exception as e:
            print(f"Error starting NordVPN: {e}")
            return False
    
    def stop_app(self) -> bool:
        """Stop NordVPN application"""
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] == self.process_name:
                    proc.terminate()
                    proc.wait(timeout=5)
            return True
        except Exception as e:
            print(f"Error stopping NordVPN: {e}")
            return False
    
    def get_connection_status(self) -> Dict:
        """
        Get current connection status including IP address
        Note: This checks if NordVPN service is running and connected
        """
        try:
            # Check if nordvpn-service is running
            service_running = False
            for proc in psutil.process_iter(['name']):
                if 'nordvpn-service' in proc.info['name'].lower():
                    service_running = True
                    break
            
            # Try to get network adapter info
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-NetAdapter | Where-Object {$_.InterfaceDescription -like "*NordVPN*"} | Select-Object Status, LinkSpeed | ConvertTo-Json'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            is_connected = False
            if result.returncode == 0 and result.stdout.strip():
                try:
                    adapter_info = json.loads(result.stdout)
                    if adapter_info and adapter_info.get('Status') == 'Up':
                        is_connected = True
                except json.JSONDecodeError:
                    pass
            
            # Get public IP address if connected
            ip_address = None
            location = None
            if is_connected:
                try:
                    import requests
                    # Get IP from ipify API
                    ip_response = requests.get('https://api.ipify.org?format=json', timeout=3)
                    if ip_response.status_code == 200:
                        ip_address = ip_response.json().get('ip')
                    
                    # Get location info
                    if ip_address:
                        loc_response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=3)
                        if loc_response.status_code == 200:
                            loc_data = loc_response.json()
                            city = loc_data.get('city', '')
                            region = loc_data.get('region', '')
                            country = loc_data.get('country_name', '')
                            location = f"{city}, {region}, {country}" if city else country
                except:
                    pass
            
            if is_connected:
                return {
                    'connected': True,
                    'status': 'Connected',
                    'ip': ip_address or 'Unknown',
                    'location': location or 'Unknown'
                }
            
            return {
                'connected': False,
                'status': 'Disconnected' if service_running else 'Service not running',
                'ip': None,
                'location': None
            }
            
        except Exception as e:
            return {
                'connected': False,
                'status': f'Error: {str(e)}',
                'ip': None,
                'location': None
            }
    
    def connect_quick(self) -> bool:
        """
        Trigger quick connect using keyboard automation
        This simulates opening the app and clicking connect
        """
        try:
            if not self.is_running():
                self.start_app()
            
            # Use PowerShell to send keys to NordVPN window
            ps_script = """
            Add-Type -AssemblyName System.Windows.Forms
            $wshell = New-Object -ComObject wscript.shell
            $wshell.AppActivate('NordVPN')
            Start-Sleep -Milliseconds 500
            $wshell.SendKeys('{ENTER}')
            """
            
            subprocess.run(['powershell', '-Command', ps_script], 
                         capture_output=True, timeout=5)
            return True
            
        except Exception as e:
            print(f"Error connecting: {e}")
            return False
    
    def connect_to_location(self, location: str) -> bool:
        """
        Connect to a specific location/city using search
        Args:
            location: City or country name (e.g., 'Seattle', 'United States')
        """
        try:
            if not self.is_running():
                self.start_app()
                time.sleep(2)
            
            # Use PowerShell with UIAutomation to search and connect
            ps_script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            $wshell = New-Object -ComObject wscript.shell
            
            # Activate NordVPN window
            $wshell.AppActivate('NordVPN')
            Start-Sleep -Milliseconds 800
            
            # Press Ctrl+F or click search (try Ctrl+K for search)
            $wshell.SendKeys('^k')
            Start-Sleep -Milliseconds 500
            
            # Type the location
            $wshell.SendKeys('{location}')
            Start-Sleep -Milliseconds 800
            
            # Press Enter to select first result
            $wshell.SendKeys('{{ENTER}}')
            Start-Sleep -Milliseconds 500
            
            # Press Enter again to connect
            $wshell.SendKeys('{{ENTER}}')
            """
            
            subprocess.run(['powershell', '-Command', ps_script], 
                         capture_output=True, timeout=10)
            
            print(f"Connection to {location} initiated...")
            return True
            
        except Exception as e:
            print(f"Error connecting to {location}: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect VPN using keyboard automation
        """
        try:
            if not self.is_running():
                return False
            
            # Use PowerShell to send disconnect command
            ps_script = """
            Add-Type -AssemblyName System.Windows.Forms
            $wshell = New-Object -ComObject wscript.shell
            $wshell.AppActivate('NordVPN')
            Start-Sleep -Milliseconds 500
            $wshell.SendKeys('d')
            """
            
            subprocess.run(['powershell', '-Command', ps_script], 
                         capture_output=True, timeout=5)
            return True
            
        except Exception as e:
            print(f"Error disconnecting: {e}")
            return False
    
    def get_settings(self) -> Dict:
        """
        Get NordVPN settings from registry (if available)
        """
        try:
            settings = {}
            
            # Try to read from registry
            reg_path = r"SOFTWARE\NordVPN"
            
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        settings[name] = value
                        i += 1
                    except WindowsError:
                        break
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass
            
            # Try local app data
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        settings[name] = value
                        i += 1
                    except WindowsError:
                        break
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass
            
            return settings
            
        except Exception as e:
            return {'error': str(e)}
    
    def enable_killswitch(self) -> bool:
        """
        Enable kill switch (requires app automation or API)
        Note: This is a placeholder - actual implementation requires UI automation
        """
        print("Kill switch must be enabled manually in NordVPN app settings")
        return False
    
    def disable_killswitch(self) -> bool:
        """
        Disable kill switch (requires app automation or API)
        Note: This is a placeholder - actual implementation requires UI automation
        """
        print("Kill switch must be disabled manually in NordVPN app settings")
        return False


def main():
    """CLI interface for NordVPN controller"""
    import sys
    
    controller = NordVPNController()
    
    if len(sys.argv) < 2:
        print("NordVPN Controller CLI")
        print("\nUsage:")
        print("  python nordvpn_controller.py status              - Check connection status")
        print("  python nordvpn_controller.py connect             - Quick connect")
        print("  python nordvpn_controller.py connect <location>  - Connect to specific location")
        print("  python nordvpn_controller.py disconnect          - Disconnect")
        print("  python nordvpn_controller.py start               - Start NordVPN app")
        print("  python nordvpn_controller.py stop                - Stop NordVPN app")
        print("  python nordvpn_controller.py settings            - Show settings")
        print("\nExamples:")
        print("  python nordvpn_controller.py connect seattle")
        print("  python nordvpn_controller.py connect \"United States\"")
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        status = controller.get_connection_status()
        print("NordVPN Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
    
    elif command == "connect":
        # Check if location is provided
        if len(sys.argv) > 2:
            location = " ".join(sys.argv[2:])  # Join all remaining args as location
            print(f"Connecting to NordVPN ({location})...")
            if controller.connect_to_location(location):
                print("Connection initiated (check app for confirmation)")
            else:
                print("Failed to connect")
        else:
            print("Connecting to NordVPN (Quick Connect)...")
            if controller.connect_quick():
                print("Connection initiated (check app for confirmation)")
            else:
                print("Failed to connect")
    
    elif command == "disconnect":
        print("Disconnecting from NordVPN...")
        if controller.disconnect():
            print("Disconnect initiated")
        else:
            print("Failed to disconnect")
    
    elif command == "start":
        print("Starting NordVPN app...")
        if controller.start_app():
            print("NordVPN app started")
        else:
            print("Failed to start app")
    
    elif command == "stop":
        print("Stopping NordVPN app...")
        if controller.stop_app():
            print("NordVPN app stopped")
        else:
            print("Failed to stop app")
    
    elif command == "settings":
        settings = controller.get_settings()
        print("NordVPN Settings:")
        if settings:
            for key, value in settings.items():
                print(f"  {key}: {value}")
        else:
            print("  No settings found in registry")
    
    else:
        print(f"Unknown command: {command}")
        print("Use 'python nordvpn_controller.py' to see available commands")


if __name__ == "__main__":
    main()
