"""Update process_all_addresses to check for saved images first"""

with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the process_all_addresses method
method_start = None
for i, line in enumerate(lines):
    if 'def process_all_addresses(self):' in line:
        method_start = i
        break

if method_start is None:
    print("ERROR: Could not find process_all_addresses method")
    exit(1)

# Replace the method body
new_method = '''    def process_all_addresses(self):
        """Process all parcels in batch - now checks for saved images"""
        if self.is_running:
            return

        # Check if we should process saved images instead
        from pathlib import Path
        parcels_dir = Path("Captures/parcels")
        unprocessed_images = list(parcels_dir.glob("parcels_*.png"))
        unprocessed_images = [img for img in unprocessed_images if not img.stem.endswith('_processed')]
        
        if unprocessed_images:
            self.log_activity(f"Found {len(unprocessed_images)} saved parcel images")
            self.log_activity("Processing saved images instead of live automation...")
            
            # Process saved images based on extraction method
            self.process_parcel_images_batch()
            return

        # Otherwise, run normal batch automation
        self.is_running = True
        self.process_all_btn.config(state=tk.DISABLED)
        self.stop_batch_btn.config(state=tk.NORMAL)

        # Update label
        self.batch_progress_label.config(text=f"Processed: 0 / {len(self.all_parcels)}")
        self.batch_progress_var.set(0)

        # Run batch automation in background thread
        thread = threading.Thread(target=self.run_batch_automation, daemon=True)
        thread.start()

'''

# Find the end of the method (next def or class)
method_end = method_start + 1
while method_end < len(lines):
    if lines[method_end].strip().startswith('def ') and not lines[method_end].strip().startswith('def process_all_addresses'):
        break
    method_end += 1

# Replace the method
lines = lines[:method_start] + [new_method] + lines[method_end:]

with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Updated process_all_addresses to check for saved images first")
print("  Now processes saved images based on selected extraction method")
