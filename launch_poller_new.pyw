#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path
import importlib.util

def import_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Get absolute paths
script_dir = Path(__file__).resolve().parent
worker_path = script_dir / 'worker.py'

# Change to script directory and add to Python path
os.chdir(script_dir)
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

try:
    # Import worker module dynamically
    worker = import_from_path('worker', worker_path)
    print("Starting worker via dynamic import...")
    worker.main()
except Exception as e:
    # Log any errors
    error_path = script_dir / 'poller_error.log'
    with open(error_path, 'a') as f:
        f.write(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] Error starting worker: {e}\n')