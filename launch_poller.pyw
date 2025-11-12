#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
from pathlib import Path

# Get the absolute path to the script's directory
script_dir = Path(__file__).resolve().parent

# Add the script directory to Python path and change to it
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

try:
    import worker
    print("Starting worker...")
    # Write a PID file so you can find this process in Task Manager easily
    try:
        pid_file = script_dir / "poller.pid"
        with open(pid_file, "w", encoding="utf-8") as pf:
            pf.write(str(os.getpid()))
    except Exception:
        pass
    worker.main()
except Exception as e:
    # Log any startup errors
    error_log = script_dir / "poller_error.log"
    with open(error_log, "a") as f:
        f.write(f"[{time.ctime()}] Startup error: {e}\n")