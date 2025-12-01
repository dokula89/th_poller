"""
Fix upload_all_to_database logging to be more transparent
"""
import re

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1: Add logging at the very start
old_pattern1 = r'(def upload_all_to_database\(self\):.*?"""Upload all parcels from JSON to database with progress bar""")\s+(import mysql\.connector)'
new_text1 = r'\1\n        self.window.after(0, lambda: self.append_log("=== UPLOAD TO DATABASE STARTED ==="))\n        \2'
content = re.sub(old_pattern1, new_text1, content, flags=re.DOTALL)

# Pattern 2: Add logging before checking if JSON exists
old_pattern2 = r'(json_path = self\.capture_dir / "parcels_data\.json")\s+(if not json_path\.exists\(\):)'
new_text2 = r'\1\n        self.window.after(0, lambda p=str(json_path): self.append_log(f"Checking for JSON file: {p}"))\n        \2'
content = re.sub(old_pattern2, new_text2, content)

# Pattern 3: Add logging when JSON doesn't exist
old_pattern3 = r'(if not json_path\.exists\(\):)\s+(self\.window\.after\(0, lambda: self\.update_status\("No data to upload"\)\))'
new_text3 = r'\1\n            self.window.after(0, lambda: self.append_log("✗ JSON file not found!"))\n            \2'
content = re.sub(old_pattern3, new_text3, content)

# Pattern 4: Add logging before loading JSON
old_pattern4 = r'(self\.window\.after\(0, lambda: self\.append_log\("Loading parcels_data\.json\.\.\."\)\))\s+(with open\(json_path, \'r\', encoding=\'utf-8\'\) as f:)'
new_text4 = r'\1\n            self.window.after(0, lambda: self.append_log("Opening file for reading..."))\n            \2'
content = re.sub(old_pattern4, new_text4, content)

# Pattern 5: Add logging after loading JSON
old_pattern5 = r'(all_data = json\.load\(f\))\s+(if not all_data:)'
new_text5 = r'\1\n                self.window.after(0, lambda d=len(all_data) if isinstance(all_data, list) else 0: self.append_log(f"JSON loaded: {d} items found"))\n\n            \2'
content = re.sub(old_pattern5, new_text5, content)

# Pattern 6: Add logging before database connection
old_pattern6 = r'(self\.window\.after\(0, lambda: self\.append_log\("Connecting to database\.\.\."\)\))\s+(config_path = Path\(__file__\)\.parent / \'config_hud_db\.py\')'
new_text6 = r'\1\n            self.window.after(0, lambda: self.append_log("Reading database config..."))\n            \2'
content = re.sub(old_pattern6, new_text6, content)

# Pattern 7: Add logging after reading config
old_pattern7 = r'(DB_CONFIG = config_globals\.get\(\'DB_CONFIG\'\))\s+(# Connect to database)'
new_text7 = r'\1\n            self.window.after(0, lambda: self.append_log(f"Config loaded, connecting to {DB_CONFIG.get(\'host\', \'unknown\')}"))\n\n            \2'
content = re.sub(old_pattern7, new_text7, content)

# Pattern 8: Enhance the main exception handler
old_pattern8 = r'except Exception as e:\s+logging\.error\(f"Database upload error: \{e\}"\)\s+import traceback\s+logging\.error\(traceback\.format_exc\(\)\)'
new_text8 = '''except Exception as e:
            import traceback
            full_error = traceback.format_exc()
            logging.error(f"DATABASE UPLOAD FAILED: {e}")
            logging.error(f"Full traceback:\\n{full_error}")
            
            # Show detailed error in activity log
            self.window.after(0, lambda: self.append_log("=== ✗ UPLOAD FAILED ==="))
            self.window.after(0, lambda err=str(e): self.append_log(f"Error: {err}"))
            self.window.after(0, lambda: self.append_log("Traceback (most recent):"))
            
            # Show last 5 lines of traceback
            tb_lines = [line for line in full_error.split('\\n') if line.strip()]
            for tb_line in tb_lines[-5:]:
                self.window.after(0, lambda l=tb_line: self.append_log(f"  {l}"))'''
content = re.sub(old_pattern8, new_text8, content)

# Write the fixed file
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Enhanced logging added to upload_all_to_database!")
print("✓ The activity log will now show:")
print("  - Start of upload process")
print("  - JSON file check and loading")
print("  - Database connection steps")
print("  - Detailed error messages with traceback")
