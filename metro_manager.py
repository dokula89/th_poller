"""
NordVPN Metro Connection Manager
Manages VPN connections to different metro areas with status tracking
"""

import json
import time
from nordvpn_controller import NordVPNController
from datetime import datetime


class MetroConnectionManager:
    """Manages VPN connections to different metropolitan areas"""
    
    # Common US metro areas
    METROS = {
        'seattle': 'Seattle',
        'los_angeles': 'Los Angeles',
        'san_francisco': 'San Francisco',
        'chicago': 'Chicago',
        'new_york': 'New York',
        'dallas': 'Dallas',
        'atlanta': 'Atlanta',
        'miami': 'Miami',
        'denver': 'Denver',
        'phoenix': 'Phoenix',
    }
    
    def __init__(self):
        self.controller = NordVPNController()
        self.current_metro = None
        self.connection_log = []
    
    def connect_to_metro(self, metro_key: str) -> dict:
        """
        Connect to a specific metro area
        Returns: {'success': bool, 'metro': str, 'ip': str, 'location': str, 'timestamp': str}
        """
        metro_name = self.METROS.get(metro_key.lower())
        if not metro_name:
            return {
                'success': False,
                'error': f'Unknown metro: {metro_key}',
                'available_metros': list(self.METROS.keys())
            }
        
        print(f"Connecting to {metro_name}...")
        success = self.controller.connect_to_location(metro_name)
        
        if success:
            # Wait for connection to establish
            time.sleep(5)
            
            # Get connection status
            status = self.controller.get_connection_status()
            
            result = {
                'success': status['connected'],
                'metro': metro_name,
                'metro_key': metro_key,
                'ip': status.get('ip', 'Unknown'),
                'location': status.get('location', 'Unknown'),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if status['connected']:
                self.current_metro = metro_key
                self.connection_log.append(result)
            
            return result
        
        return {
            'success': False,
            'error': 'Failed to initiate connection'
        }
    
    def disconnect(self) -> bool:
        """Disconnect from current VPN"""
        success = self.controller.disconnect()
        if success:
            self.current_metro = None
        return success
    
    def get_status(self) -> dict:
        """Get current connection status"""
        status = self.controller.get_connection_status()
        status['current_metro'] = self.current_metro
        return status
    
    def list_metros(self) -> dict:
        """List all available metro areas"""
        return self.METROS
    
    def get_connection_history(self, limit: int = 5) -> list:
        """Get recent connection history"""
        return self.connection_log[-limit:]


def main():
    """CLI for metro connection manager"""
    import sys
    
    manager = MetroConnectionManager()
    
    if len(sys.argv) < 2:
        print("Metro Connection Manager")
        print("\nUsage:")
        print("  python metro_manager.py status              - Check current status")
        print("  python metro_manager.py connect <metro>     - Connect to metro")
        print("  python metro_manager.py disconnect          - Disconnect")
        print("  python metro_manager.py list                - List available metros")
        print("  python metro_manager.py history             - Show connection history")
        print("\nAvailable metros:")
        for key, name in manager.METROS.items():
            print(f"  {key:<20} - {name}")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'status':
        status = manager.get_status()
        print("\nVPN Status:")
        print(f"  Connected: {status['connected']}")
        if status['connected']:
            print(f"  IP: {status.get('ip', 'Unknown')}")
            print(f"  Location: {status.get('location', 'Unknown')}")
            print(f"  Metro: {status.get('current_metro', 'Unknown')}")
        else:
            print(f"  Status: {status['status']}")
    
    elif command == 'connect':
        if len(sys.argv) < 3:
            print("Error: Metro name required")
            print("Use 'python metro_manager.py list' to see available metros")
            return
        
        metro = sys.argv[2]
        result = manager.connect_to_metro(metro)
        
        if result['success']:
            print(f"\n✓ Connected to {result['metro']}")
            print(f"  IP: {result['ip']}")
            print(f"  Location: {result['location']}")
        else:
            print(f"\n✗ Connection failed: {result.get('error', 'Unknown error')}")
    
    elif command == 'disconnect':
        print("Disconnecting...")
        if manager.disconnect():
            print("✓ Disconnected")
        else:
            print("✗ Disconnect failed")
    
    elif command == 'list':
        print("\nAvailable Metro Areas:")
        for key, name in manager.METROS.items():
            print(f"  {key:<20} - {name}")
    
    elif command == 'history':
        history = manager.get_connection_history()
        if history:
            print("\nConnection History:")
            for entry in history:
                print(f"  [{entry['timestamp']}] {entry['metro']} - {entry['ip']}")
        else:
            print("\nNo connection history")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
