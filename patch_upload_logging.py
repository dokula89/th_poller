"""
Patch parcel_automation.py to add better logging to upload_all_to_database
"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the upload_all_to_database function (around line 1203)
for i, line in enumerate(lines):
    if 'def upload_all_to_database(self):' in line:
        print(f"Found upload_all_to_database at line {i+1}")
        
        # Add logging right at the start of the try block
        # Find the first "try:" after the function definition
        for j in range(i, min(i+20, len(lines))):
            if 'if not json_path.exists():' in lines[j]:
                # Insert logging before this check
                indent = '        '
                log_line = indent + 'self.window.after(0, lambda: self.append_log("=== STARTING DATABASE UPLOAD ===\"))\n'
                lines.insert(j, log_line)
                print(f"Added start logging at line {j+1}")
                break
        
        # Find where JSON is loaded and add logging
        for j in range(i, min(i+40, len(lines))):
            if 'with open(json_path' in lines[j] and 'r' in lines[j]:
                # Add logging before opening file
                indent = '            '
                log_line = indent + 'self.window.after(0, lambda p=str(json_path): self.append_log(f"Opening JSON file: {p}"))\n'
                lines.insert(j, log_line)
                print(f"Added JSON open logging at line {j+1}")
                break
        
        # Find the main exception handler and add detailed logging
        for j in range(i, min(i+200, len(lines))):
            if 'except Exception as e:' in lines[j] and 'Database upload error' in lines[j+1]:
                # This is the main exception handler - add more detailed logging
                indent = '            '
                new_lines = [
                    indent + 'import traceback\n',
                    indent + 'full_error = traceback.format_exc()\n',
                    indent + 'logging.error(f"DATABASE UPLOAD FAILED: {e}")\n',
                    indent + 'logging.error(f"Full traceback: {full_error}")\n',
                    indent + 'self.window.after(0, lambda: self.append_log("=== UPLOAD FAILED ===\"))\n',
                    indent + f'self.window.after(0, lambda err=str(e): self.append_log(f"Error: {{err}}\"))\n',
                    indent + '# Show first line of traceback in UI\n',
                    indent + 'tb_lines = full_error.split("\\n")\n',
                    indent + 'for tb_line in tb_lines[-5:]:\n',
                    indent + '    if tb_line.strip():\n',
                    indent + '        self.window.after(0, lambda l=tb_line: self.append_log(f"  {l}"))\n',
                ]
                # Remove old logging lines
                lines[j+1] = ''  # Remove old logging.error
                if 'import traceback' in lines[j+2]:
                    lines[j+2] = ''
                if 'logging.error(traceback' in lines[j+3]:
                    lines[j+3] = ''
                
                # Insert new logging after the except line
                for idx, new_line in enumerate(new_lines):
                    lines.insert(j+1+idx, new_line)
                print(f"Enhanced exception logging at line {j+1}")
                break
        
        break

# Write the patched file
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Patching complete!")
