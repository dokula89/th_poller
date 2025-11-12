#!/usr/bin/env python3
import subprocess
import sys

# Database credentials
REMOTE_HOST = "172.104.206.182"
REMOTE_USER = "seattlelisted_usr"
REMOTE_PASS = "T@5z6^pl}"
DB_NAME = "offta"

LOCAL_HOST = "127.0.0.1"
LOCAL_USER = "root"
LOCAL_PASS = ""

MYSQL_BIN = r"C:\xampp\mysql\bin"

print("Starting database copy...")
print(f"Remote: {REMOTE_HOST} -> Local: {LOCAL_HOST}")

# Dump remote database
dump_cmd = [
    f"{MYSQL_BIN}\\mysqldump.exe",
    "-h", REMOTE_HOST,
    "-u", REMOTE_USER,
    f"-p{REMOTE_PASS}",
    "--default-auth=mysql_native_password",
    "--single-transaction",
    "--quick",
    "--skip-lock-tables",
    DB_NAME
]

# Import to local database
import_cmd = [
    f"{MYSQL_BIN}\\mysql.exe",
    "-h", LOCAL_HOST,
    "-u", LOCAL_USER,
    DB_NAME
]

try:
    print("Dumping remote database...")
    dump_process = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    print("Importing to local database...")
    import_process = subprocess.Popen(import_cmd, stdin=dump_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    dump_process.stdout.close()
    
    import_output, import_error = import_process.communicate()
    dump_output, dump_error = dump_process.communicate()
    
    if dump_process.returncode != 0:
        print(f"Dump error: {dump_error.decode('utf-8', errors='ignore')}")
        sys.exit(1)
    
    if import_process.returncode != 0:
        print(f"Import error: {import_error.decode('utf-8', errors='ignore')}")
        sys.exit(1)
    
    print("Database copy completed successfully!")
    
    # Verify tables were copied
    verify_cmd = [
        f"{MYSQL_BIN}\\mysql.exe",
        "-h", LOCAL_HOST,
        "-u", LOCAL_USER,
        "-e", f"SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = '{DB_NAME}'",
        DB_NAME
    ]
    
    result = subprocess.run(verify_cmd, capture_output=True, text=True)
    print(f"\nVerification:\n{result.stdout}")
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
