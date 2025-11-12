#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Imports, constants, logging
Extracted from config_utils.py (lines 1-68)
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, time, json, logging, sys, threading, queue
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from mimetypes import guess_extension
from urllib.parse import urlparse
import traceback as tb
import time
import tkinter as tk
from tkinter import ttk

# Third-party deps
import requests
import paramiko
# Database connection not needed - using API instead

# Load environment variables if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Load PHP server configuration
PHP_BASE_URL = "http://localhost"  # Default to XAMPP
try:
    php_config_path = Path(__file__).parent / "php_config.env"
    if php_config_path.exists():
        with open(php_config_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == "PHP_BASE_URL":
                        PHP_BASE_URL = value.strip()
                        break
except Exception as e:
    print(f"Warning: Could not load php_config.env: {e}")

# ----------------------------
# DEBUG LOG FILE SETUP
# ----------------------------
DEBUG_LOG_FILE = Path(__file__).parent / "debug_queue.log"

def log_to_file(msg):
    """Write debug message to log file with timestamp."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except Exception as e:
        print(f"Failed to write to log: {e}")

def log_exception(label="EXCEPTION"):
    """Log current exception with full traceback to file."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"[{timestamp}] {label}\n")
            f.write(f"{'='*80}\n")
            tb.print_exc(file=f)
            f.write(f"{'='*80}\n\n")
    except Exception as e:
        print(f"Failed to log exception: {e}")

# Initialize log file
try:
    with open(DEBUG_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"{'='*80}\n")
        f.write(f"DEBUG LOG STARTED: {datetime.now()}\n")
        f.write(f"Log file: {DEBUG_LOG_FILE}\n")
        f.write(f"{'='*80}\n\n")
    print(f"\n{'='*80}")
    print(f"DEBUG LOGGING ENABLED")
    print(f"Log file: {DEBUG_LOG_FILE}")
    print(f"{'='*80}\n")
except Exception as e:
    print(f"Failed to initialize debug log: {e}")

# ----------------------------
# Base directories
# ----------------------------
PKG_DIR = Path(__file__).parent
BASE_DIR = Path(os.getenv("BASE_DIR", str(PKG_DIR / "Captures")))

def ensure_dir(path):
    """Ensure directory exists"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log_to_file(f"[Queue] Failed to create directory {path}: {e}")

def php_url(path):
    """Build PHP URL using configured base URL"""
    if path.startswith("/"):
        path = path[1:]
    return f"{PHP_BASE_URL}/{path}"

# ----------------------------

