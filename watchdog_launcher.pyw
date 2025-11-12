#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import time
import os
from pathlib import Path

POLL_INTERVAL = 2  # seconds to wait before restart

script_dir = Path(__file__).parent
poller_script = script_dir / "launch_poller.pyw"

while True:
    try:
        # Use pythonw to avoid console window
        proc = subprocess.Popen([
            sys.executable.replace("python.exe", "pythonw.exe"),
            str(poller_script)
        ], cwd=str(script_dir))
        proc.wait()
    except Exception as e:
        # Optionally log to a file on Desktop
        try:
            with open(str(Path.home() / "Desktop" / "poller_watchdog.log"), "a", encoding="utf-8") as f:
                f.write(f"[{time.ctime()}] Poller crashed: {e}\n")
        except Exception:
            pass
    time.sleep(POLL_INTERVAL)  # Wait before restarting
