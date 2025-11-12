#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import traceback
from pathlib import Path

def setup_environment():
    """Set up the Python environment for running the worker"""
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # Add script directory to Python path
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    
    return script_dir

def main():
    """Main entry point"""
    script_dir = setup_environment()
    error_log = script_dir / "poller_error.log"
    
    try:
        # Try importing required modules
        print("Importing worker module...")
        import worker
        print("Importing config_utils...")
        import config_utils
        
        # Start the worker
        print("Starting worker main function...")
        worker.main()
        
    except Exception as e:
        error_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}\n"
        error_msg += f"Traceback:\n{traceback.format_exc()}\n"
        
        # Log error to file
        with open(error_log, "a") as f:
            f.write(error_msg)
        
        print(f"\nError occurred: {e}")
        print(f"Full error details written to {error_log}")
        raise

if __name__ == "__main__":
    main()