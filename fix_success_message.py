"""
Fix success message to reflect actual upload status
"""

with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the completion message to show failure if no records uploaded
old_completion = '''            logging.info(f"✓ Uploaded {uploaded_count}/{total_records} records to database")
            self.window.after(0, lambda u=uploaded_count, t=total_records: self.append_log(f"✓ Upload complete! {u}/{t} records saved"))
            self.window.after(0, lambda u=uploaded_count, t=total_records: self.update_status(f"✓ Upload complete! {u}/{t} records saved", 9))'''

new_completion = '''            logging.info(f"Uploaded {uploaded_count}/{total_records} records to database")
            
            if uploaded_count == 0:
                self.window.after(0, lambda t=total_records: self.append_log(f"✗ UPLOAD FAILED! 0/{t} records saved - check errors above"))
                self.window.after(0, lambda t=total_records: self.update_status(f"✗ Upload failed: 0/{t} records saved", 9))
            elif uploaded_count < total_records:
                self.window.after(0, lambda u=uploaded_count, t=total_records: self.append_log(f"⚠ Partial upload: {u}/{t} records saved"))
                self.window.after(0, lambda u=uploaded_count, t=total_records: self.update_status(f"⚠ Partial upload: {u}/{t} records saved", 9))
            else:
                self.window.after(0, lambda u=uploaded_count, t=total_records: self.append_log(f"✓ Upload complete! {u}/{t} records saved"))
                self.window.after(0, lambda u=uploaded_count, t=total_records: self.update_status(f"✓ Upload complete! {u}/{t} records saved", 9))'''

content = content.replace(old_completion, new_completion)

with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed success messages to reflect actual upload results:")
print("  - 0 records: ✗ UPLOAD FAILED!")
print("  - Partial: ⚠ Partial upload")
print("  - All records: ✓ Upload complete!")
