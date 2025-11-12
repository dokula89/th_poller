#!/usr/bin/env python3
"""
Test if PHP server is running and accessible
"""
import requests
import sys
from pathlib import Path

# Load PHP base URL from config
PHP_BASE_URL = "http://localhost:8000"
try:
    config_path = Path(__file__).parent / "php_config.env"
    if config_path.exists():
        with open(config_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == "PHP_BASE_URL":
                        PHP_BASE_URL = value.strip()
                        break
except Exception as e:
    print(f"Warning: Could not load php_config.env: {e}")

print(f"Testing PHP server at: {PHP_BASE_URL}")
print("-" * 60)

# Test endpoints
endpoints = [
    "/index.php",
    "/step5/get_major_metros.php?only=names",
    "/functions.php",
]

all_ok = True
for endpoint in endpoints:
    url = f"{PHP_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✓ {endpoint} - OK")
        else:
            print(f"✗ {endpoint} - HTTP {response.status_code}")
            all_ok = False
    except requests.exceptions.ConnectionError:
        print(f"✗ {endpoint} - Connection refused (server not running?)")
        all_ok = False
    except Exception as e:
        print(f"✗ {endpoint} - Error: {e}")
        all_ok = False

print("-" * 60)
if all_ok:
    print("✓ All tests passed! PHP server is working correctly.")
    sys.exit(0)
else:
    print("✗ Some tests failed. Make sure:")
    print("  1. PHP server is running (run start_php_server.bat)")
    print("  2. PHP is installed and in PATH")
    print("  3. MySQL is running")
    sys.exit(1)
