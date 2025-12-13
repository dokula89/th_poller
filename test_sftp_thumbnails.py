"""Test SFTP connection and check remote thumbnails folder"""
import paramiko
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from config_helpers import SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASS

print(f"Connecting to SFTP: {SFTP_HOST}:{SFTP_PORT}")
print(f"User: {SFTP_USER}")

try:
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    sftp = paramiko.SFTPClient.from_transport(transport)
    print("✅ SFTP connected!")
    
    remote_dir = "/home/daniel/assets/trustyhousing.com/thumbnails"
    print(f"\nChecking remote folder: {remote_dir}")
    
    try:
        files = sftp.listdir(remote_dir)
        print(f"✅ Found {len(files)} files on server")
        
        # Get modification times for most recent files
        file_details = []
        for f in files[:20]:  # Check first 20
            try:
                attrs = sftp.stat(f"{remote_dir}/{f}")
                file_details.append((f, attrs.st_mtime))
            except:
                pass
        
        # Sort by modification time (newest first)
        file_details.sort(key=lambda x: x[1], reverse=True)
        
        print("\nMost recent 10 files:")
        from datetime import datetime
        for name, mtime in file_details[:10]:
            dt = datetime.fromtimestamp(mtime)
            print(f"  {name}: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
    except Exception as e:
        print(f"❌ Error listing folder: {e}")
    
    sftp.close()
    transport.close()
    
except Exception as e:
    print(f"❌ SFTP connection failed: {e}")
