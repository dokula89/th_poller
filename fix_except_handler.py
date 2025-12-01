"""
Final comprehensive fix - manually replace the exception handler
"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the problematic except block and replace it
in_except_block = False
except_start = -1
for i, line in enumerate(lines):
    if 'def upload_all_to_database(self):' in line:
        func_start = i
    if i > 1200 and 'except Exception as e:' in line and not in_except_block:
        # Found the exception handler
        except_start = i
        in_except_block = True
        # Find the end of this except block (next def or class)
        for j in range(i+1, min(i+50, len(lines))):
            if lines[j].startswith('    def ') or lines[j].startswith('def '):
                # Found the next function
                # Replace everything between except_start and j
                new_except = '''        except Exception as e:
            import traceback
            full_error = traceback.format_exc()
            logging.error(f"DATABASE UPLOAD FAILED: {e}")
            logging.error("Full traceback:")
            logging.error(full_error)
            
            # Show detailed error in activity log
            self.window.after(0, lambda: self.append_log("=== UPLOAD FAILED ==="))
            self.window.after(0, lambda err=str(e): self.append_log(f"Error: {err}"))
            self.window.after(0, lambda: self.append_log("Traceback:"))
            
            # Show last 5 lines of traceback in UI
            tb_lines = [line for line in full_error.split('\\n') if line.strip()]
            for tb_line in tb_lines[-5:]:
                self.window.after(0, lambda l=tb_line: self.append_log(f"  {l}"))
            
            error_msg = str(e)[:200]
            self.window.after(0, lambda err=error_msg: self.update_status(f"Upload error: {err}"))

'''
                # Replace the lines
                lines[except_start:j] = [new_except]
                print(f"Replaced except block from line {except_start+1} to {j+1}")
                break
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Fixed exception handler!")
