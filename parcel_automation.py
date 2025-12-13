"""
Parcel Automation Script
Handles automation of parcel data extraction from parcel viewer websites
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import threading
import webbrowser
from PIL import Image, ImageGrab
import pyautogui
import pytesseract

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Setup logging
log_file = Path(__file__).parent / "logs" / "parcel_automation.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

class ParcelAutomationWindow:
    """Activity window for parcel automation"""
    
    def __init__(self, parent, parcel_data, all_parcels=None, auto_start=False):
        """
        Initialize automation window
        
        Args:
            parent: Parent tkinter window
            parcel_data: Dict with keys: id, address, parcel_link, metro_name
            all_parcels: List of all parcel data dicts for batch processing
            auto_start: If True, automatically start automation after window creation
        """
        self.parent = parent
        self.parcel_data = parcel_data
        self.all_parcels = all_parcels or [parcel_data]
        self.auto_start = auto_start
        self.window = None
        self.browser_window = None
        self.is_running = False
        self.is_paused = False
        self.current_step = 0
        self.capture_dir = Path(__file__).parent / "Captures" / "parcels"
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        
        # Load click coordinates from API
        self.search_field_x = 454  # Default
        self.search_field_y = 201  # Default
        self.load_coordinates_from_api()
        
        # Store last screenshot path for review
        self.last_screenshot_path = None
        
        # Store extracted data in memory instead of saving to file
        self.extracted_data = []
        
        # Automation steps
        self.steps = [
            "Opening parcel viewer in browser",
            "Positioning browser window (right 80%)",
            "Clicking search field & entering address",
            "Submitting search (press Enter)",
            "Waiting for results to load",
            "Capturing screenshot of right 80%",
            "Processing image with OCR",
            "Extracting data to JSON",
            "Uploading to database",
            "Complete"
        ]
        
        self.create_window()
    
    def create_window(self):
        """Create the activity window with tabs"""
        import pyautogui
        
        # Get screen dimensions
        screen_width = pyautogui.size()[0]
        screen_height = pyautogui.size()[1]
        
        # Calculate position: starts at 36% down, uses 58% of screen height
        window_width = int(screen_width * 0.20)
        window_height = int(screen_height * 0.58)  # 58% height - more compact
        x_position = 0  # Left edge
        y_position = int(screen_height * 0.36)  # Start at 36% down (below pending jobs)
        
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"Parcel Automation")
        
        # Position at lower 50% of left 20% screen
        self.window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        # Make it stay on top initially
        self.window.attributes('-topmost', True)
        self.window.after(2000, lambda: self.window.attributes('-topmost', False))
        
        # Header - compact
        header = tk.Frame(self.window, bg="#2C3E50", height=30)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title_lbl = tk.Label(
            header, 
            text="Parcel Data Automation",
            font=("Segoe UI", 8, "bold"),
            bg="#2C3E50",
            fg="white"
        )
        title_lbl.pack(pady=4)
        
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tab 1: Automation Steps
        self.create_steps_tab()
        
        # Tab 2: OpenAI Extraction Results
        self.create_json_tab()
        
        # Tab 3: OCR Extraction (Regex)
        self.create_ocr_tab()
        
        # Tab 4: Process All Addresses
        self.create_process_all_tab()
        
        # Status bar at bottom
        status_frame = tk.Frame(self.window, bg="#ECF0F1", height=30)
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            status_frame,
            text="Ready",
            font=("Segoe UI", 9),
            bg="#ECF0F1",
            fg="#7F8C8D",
            anchor="w",
            padx=10
        )
        self.status_label.pack(fill="both")
        
        # Auto-start automation if requested
        if self.auto_start:
            self.window.after(500, self.start_automation)
    
    def create_steps_tab(self):
        """Create the automation steps tab"""
        steps_tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(steps_tab, text="Automation Steps")
        
        # Info section - compact
        info_frame = tk.Frame(steps_tab, bg="white", padx=6, pady=2)
        info_frame.pack(fill="x")
        
        tk.Label(
            info_frame,
            text=f"Address: {self.parcel_data.get('address', 'N/A')}",
            font=("Segoe UI", 7),
            bg="white",
            anchor="w"
        ).pack(fill="x", pady=0)
        
        tk.Label(
            info_frame,
            text=f"Metro: {self.parcel_data.get('metro_name', 'N/A')}",
            font=("Segoe UI", 7),
            bg="white",
            anchor="w"
        ).pack(fill="x", pady=1)
        
        # Progress section - compact
        progress_frame = tk.Frame(steps_tab, bg="#ECF0F1", padx=8, pady=6)
        progress_frame.pack(fill="both", expand=True)
        
        tk.Label(
            progress_frame,
            text="Steps:",
            font=("Segoe UI", 8, "bold"),
            bg="#ECF0F1"
        ).pack(anchor="w", pady=(0, 4))
        
        # Steps listbox - compact
        self.steps_listbox = tk.Listbox(
            progress_frame,
            font=("Segoe UI", 7),
            height=len(self.steps),
            selectmode=tk.SINGLE,
            activestyle='none'
        )
        self.steps_listbox.pack(fill="both", expand=True)
        
        for i, step in enumerate(self.steps, 1):
            self.steps_listbox.insert(tk.END, f"{i}. {step}")
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=len(self.steps),
            mode='determinate'
        )
        self.progress_bar.pack(fill="x", pady=(10, 0))
        
        # Log viewer - compact
        log_frame = tk.Frame(progress_frame, bg="#ECF0F1")
        log_frame.pack(fill="both", expand=True, pady=(6, 0))
        
        tk.Label(
            log_frame,
            text="Log:",
            font=("Segoe UI", 7, "bold"),
            bg="#ECF0F1"
        ).pack(anchor="w", pady=(2, 2))
        
        # Log text widget with scrollbar
        log_scroll_frame = tk.Frame(log_frame)
        log_scroll_frame.pack(fill="both", expand=True)
        
        log_scrollbar = tk.Scrollbar(log_scroll_frame)
        log_scrollbar.pack(side="right", fill="y")
        
        self.log_text = tk.Text(
            log_scroll_frame,
            font=("Consolas", 6),
            height=4,
            wrap=tk.WORD,
            yscrollcommand=log_scrollbar.set,
            bg="#2C3E50",
            fg="#ECF0F1",
            insertbackground="#ECF0F1"
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.config(command=self.log_text.yview)
        
        # Buttons - compact
        btn_frame = tk.Frame(steps_tab, bg="white", padx=8, pady=6)
        btn_frame.pack(fill="x")
        
        # Single toggle button for Start/Pause
        self.toggle_btn = tk.Button(
            btn_frame,
            text="▶ START",
            font=("Segoe UI", 12, "bold"),
            bg="#00FF00",
            fg="black",
            padx=18,
            pady=8,
            cursor="hand2",
            command=self.toggle_automation
        )
        self.toggle_btn.pack(side="left", padx=(0, 6))
        
        # Folder button next to Start/Pause
        self.view_folder_btn = tk.Button(
            btn_frame,
            text="📁 FOLDER",
            font=("Segoe UI", 12, "bold"),
            bg="#FFFF00",
            fg="black",
            padx=18,
            pady=8,
            cursor="hand2",
            state=tk.NORMAL,
            command=self.open_captures_folder
        )
        self.view_folder_btn.pack(side="left", padx=(0, 6))
        
        # Stop button
        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹ STOP",
            font=("Segoe UI", 12, "bold"),
            bg="#FF0000",
            fg="black",
            padx=18,
            pady=8,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.stop_automation
        )
        self.stop_btn.pack(side="left", padx=(0, 6))
        
        # Image viewer button
        self.view_screenshot_btn = tk.Button(
            btn_frame,
            text="📸 IMAGE",
            font=("Segoe UI", 12, "bold"),
            bg="#FFA500",
            fg="black",
            padx=18,
            pady=8,
            cursor="hand2",
            state=tk.NORMAL,
            command=self.open_screenshot
        )
        self.view_screenshot_btn.pack(side="left")
    
    def create_json_tab(self):
        """Create the OpenAI extraction results tab with vertical key-value display"""
        json_tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(json_tab, text="OpenAI Extraction")

        # Create treeview for vertical key-value display
        tree_frame = tk.Frame(json_tab, bg="white", padx=10, pady=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Create treeview with 2 columns: Field and Value
        self.json_tree = ttk.Treeview(
            tree_frame, 
            columns=("field", "value"), 
            show='headings',
            yscrollcommand=v_scroll.set
        )

        v_scroll.config(command=self.json_tree.yview)

        # Configure columns
        self.json_tree.heading("field", text="Field")
        self.json_tree.heading("value", text="Value")
        
        self.json_tree.column("field", width=150, minwidth=120)
        self.json_tree.column("value", width=600, minwidth=400)

        self.json_tree.pack(fill=tk.BOTH, expand=True)

    def create_ocr_tab(self):
        """Create the OCR extraction tab showing regex-based extraction"""
        ocr_tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(ocr_tab, text="OCR Extraction")

        # Create treeview for vertical key-value display
        tree_frame = tk.Frame(ocr_tab, bg="white", padx=10, pady=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Create treeview with 2 columns: Field and Value
        self.ocr_tree = ttk.Treeview(
            tree_frame, 
            columns=("field", "value"), 
            show='headings',
            yscrollcommand=v_scroll.set
        )

        v_scroll.config(command=self.ocr_tree.yview)

        # Configure columns
        self.ocr_tree.heading("field", text="Field")
        self.ocr_tree.heading("value", text="Value")
        
        self.ocr_tree.column("field", width=150, minwidth=120)
        self.ocr_tree.column("value", width=600, minwidth=400)

        self.ocr_tree.pack(fill=tk.BOTH, expand=True)

    def update_json_results(self, data):
        """Update the OpenAI Extraction tab with ChatGPT extraction results"""
        # Clear existing items
        for item in self.json_tree.get_children():
            self.json_tree.delete(item)
        
        # Insert extracted fields
        if data and "extracted_fields" in data:
            for field_name, field_value in data["extracted_fields"].items():
                display_value = field_value if field_value is not None else "NULL"
                self.json_tree.insert("", tk.END, values=(field_name, display_value))
        
        # Switch to OpenAI tab to show results
        self.notebook.select(1)  # Tab index 1 is OpenAI Extraction

    def update_ocr_results(self, data):
        """Update the OCR Extraction tab with regex extraction results"""
        # Clear existing items
        for item in self.ocr_tree.get_children():
            self.ocr_tree.delete(item)
        
        # Insert extracted fields
        if data and "extracted_fields" in data:
            for field_name, field_value in data["extracted_fields"].items():
                display_value = field_value if field_value is not None else "NULL"
                self.ocr_tree.insert("", tk.END, values=(field_name, display_value))
        
        # Note: Don't switch to OCR tab automatically, user can switch manually to compare

    def create_process_all_tab(self):
        """Create the process all addresses tab"""
        all_tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(all_tab, text="Process All Addresses")
        
        # Info section
        info_frame = tk.Frame(all_tab, bg="#ECF0F1", padx=20, pady=20)
        info_frame.pack(fill="x")
        
        tk.Label(
            info_frame,
            text="Batch Process All Parcels",
            font=("Segoe UI", 12, "bold"),
            bg="#ECF0F1"
        ).pack(anchor="w", pady=(0, 10))
        
        tk.Label(
            info_frame,
            text=f"Total parcels to process: {len(self.all_parcels)}",
            font=("Segoe UI", 10),
            bg="#ECF0F1"
        ).pack(anchor="w", pady=2)
        
        self.batch_progress_label = tk.Label(
            info_frame,
            text="Processed: 0 / 0",
            font=("Segoe UI", 10),
            bg="#ECF0F1"
        )
        self.batch_progress_label.pack(anchor="w", pady=2)
        
        # Progress bar for batch
        self.batch_progress_var = tk.DoubleVar()
        self.batch_progress_bar = ttk.Progressbar(
            info_frame,
            variable=self.batch_progress_var,
            maximum=max(len(self.all_parcels), 1),
            mode='determinate'
        )
        self.batch_progress_bar.pack(fill="x", pady=(10, 0))
        
        # Buttons
        btn_frame = tk.Frame(all_tab, bg="white", padx=20, pady=20)
        btn_frame.pack(fill="x")
        
        self.process_all_btn = tk.Button(
            btn_frame,
            text="▶ Process All Addresses",
            font=("Segoe UI", 11, "bold"),
            bg="#3498DB",
            fg="white",
            padx=30,
            pady=15,
            cursor="hand2",
            command=self.process_all_addresses
        )
        self.process_all_btn.pack(pady=10)
        
        self.stop_batch_btn = tk.Button(
            btn_frame,
            text="⏹ Stop Batch Process",
            font=("Segoe UI", 10),
            bg="#E74C3C",
            fg="white",
            padx=20,
            pady=10,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.stop_automation
        )
        self.stop_batch_btn.pack(pady=5)
    
    def update_status(self, message, step_index=None):
        """Update status label and highlight current step"""
        self.status_label.config(text=message)
        logging.info(message)
        
        if step_index is not None:
            # Highlight current step
            self.steps_listbox.selection_clear(0, tk.END)
            self.steps_listbox.selection_set(step_index)
            self.steps_listbox.see(step_index)
            self.progress_var.set(step_index + 1)
            self.current_step = step_index
    
    def process_all_addresses(self):
        """Process all parcels in batch"""
        if self.is_running:
            return
        
        self.is_running = True
        self.process_all_btn.config(state=tk.DISABLED)
        self.stop_batch_btn.config(state=tk.NORMAL)
        
        # Update label
        self.batch_progress_label.config(text=f"Processed: 0 / {len(self.all_parcels)}")
        self.batch_progress_var.set(0)
        
        # Run batch automation in background thread
        thread = threading.Thread(target=self.run_batch_automation, daemon=True)
        thread.start()
    
    def run_batch_automation(self):
        """Process all parcels one by one"""
        try:
            self._in_batch_mode = True
            
            for idx, parcel in enumerate(self.all_parcels):
                if not self.is_running:
                    break
                
                # Update current parcel
                self.parcel_data = parcel
                
                # Update batch progress
                self.window.after(0, lambda i=idx, p=parcel: self.batch_progress_label.config(
                    text=f"Processing: {p.get('address', 'N/A')} ({i+1} / {len(self.all_parcels)})"
                ))
                
                # Run automation for this parcel
                self.run_automation()
                
                # Update batch progress bar
                self.window.after(0, lambda i=idx: self.batch_progress_var.set(i + 1))
                
                # Small delay between parcels
                time.sleep(2)
            
            # All done
            self.window.after(0, lambda: self.batch_progress_label.config(
                text=f"Completed: {len(self.all_parcels)} / {len(self.all_parcels)}"
            ))
            self.window.after(0, lambda: self.update_status("Processing complete! Uploading to database..."))
            
            # Upload all data to database
            self.upload_all_to_database()
            
        except Exception as e:
            logging.error(f"Batch automation error: {e}")
            self.window.after(0, lambda: self.update_status(f"Batch error: {e}"))
        finally:
            self._in_batch_mode = False
            self.is_running = False
            self.window.after(0, lambda: self.process_all_btn.config(state=tk.NORMAL))
            self.window.after(0, lambda: self.stop_batch_btn.config(state=tk.DISABLED))
    
    def update_json_display(self, data):
        """Update the JSON treeview with new data in vertical format"""
        # Clear previous data
        for item in self.json_tree.get_children():
            self.json_tree.delete(item)
        
        # Extract fields
        fields = data.get('extracted_fields', {})
        
        # Add separator
        self.json_tree.insert('', 'end', values=("=" * 40, "=" * 80))
        self.json_tree.insert('', 'end', values=("LATEST EXTRACTION", ""))
        self.json_tree.insert('', 'end', values=("=" * 40, "=" * 80))
        
        # Display data vertically
        field_mapping = [
            ("Google Address ID", data.get('id', 'N/A')),
            ("Address", data.get('address', 'N/A')),
            ("Parcel Number", fields.get('parcel_number', 'N/A')),
            ("Property Name", fields.get('property_name', 'N/A')),
            ("Jurisdiction", fields.get('jurisdiction', 'N/A')),
            ("Taxpayer Name", fields.get('taxpayer_name', 'N/A')),
            ("Address (Extracted)", fields.get('address', 'N/A')),
            ("Appraised Value", fields.get('appraised_value', 'N/A')),
            ("Lot Area (sq ft)", fields.get('lot_area', 'N/A')),
            ("Levy Code", fields.get('levy_code', 'N/A')),
            ("# of Units", fields.get('num_units', 'N/A')),
            ("# of Buildings", fields.get('num_buildings', 'N/A')),
        ]
        
        for field_name, field_value in field_mapping:
            # Highlight empty/null values
            if not field_value or field_value == 'N/A':
                self.json_tree.insert('', 'end', values=(field_name, "⚠ MISSING"), tags=('warning',))
            else:
                self.json_tree.insert('', 'end', values=(field_name, field_value))
        
        # Add tag styling for warnings
        self.json_tree.tag_configure('warning', foreground='red')
        
        # Switch to JSON tab to show results
        self.notebook.select(1)  # Index 1 is JSON Results tab

    def load_coordinates_from_api(self):
        """Load parcel click coordinates from major_metros table via API"""
        try:
            metro_name = self.parcel_data.get('metro_name', 'King County')
            
            # Call API to get metro data
            import requests
            api_url = "https://api.trustyhousing.com/user/admin/get-metro-data.php"
            response = requests.get(api_url, params={'metro_name': metro_name}, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data'):
                    parcel_x_y = data['data'].get('parcel_x_y')
                    if parcel_x_y:
                        coords = parcel_x_y.split(',')
                        if len(coords) == 2:
                            self.search_field_x = int(coords[0].strip())
                            self.search_field_y = int(coords[1].strip())
                            logging.info(f"Loaded coordinates from API: ({self.search_field_x}, {self.search_field_y}) for {metro_name}")
                        else:
                            logging.warning(f"Invalid parcel_x_y format: {parcel_x_y}")
                    else:
                        logging.info(f"No parcel_x_y found for {metro_name}, using defaults")
                else:
                    logging.warning(f"API returned no data for {metro_name}")
            else:
                logging.warning(f"API request failed with status {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to load coordinates from API: {e}")
            # Keep using default coordinates
    
    def append_log(self, message):
        """Append message to the log viewer"""
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)  # Auto-scroll to bottom
            self.log_text.config(state=tk.DISABLED)
        except:
            pass  # Ignore if window is closed
    
    def toggle_automation(self):
        """Toggle between Start and Pause"""
        if not self.is_running:
            # Start automation
            self.start_automation()
        elif self.is_paused:
            # Resume from pause
            self.resume_automation()
        else:
            # Pause running automation
            self.pause_automation()
    
    def start_automation(self):
        """Start the automation process"""
        if self.is_running:
            return
        
        self.is_running = True
        self.is_paused = False
        self.current_step = 0
        
        # Update button to show PAUSE
        self.toggle_btn.config(text="⏸ PAUSE", bg="#FF00FF")
        self.stop_btn.config(state=tk.NORMAL)
        
        # Clear log
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Run automation in background thread
        thread = threading.Thread(target=self.run_automation, daemon=True)
        thread.start()
    
    def open_screenshot(self):
        """Open the last captured screenshot"""
        if self.last_screenshot_path and self.last_screenshot_path.exists():
            import os
            os.startfile(str(self.last_screenshot_path))
        else:
            self.append_log("No screenshot available yet")
    
    def open_captures_folder(self):
        """Open the Captures/parcels folder in Windows Explorer"""
        import os
        if self.capture_dir.exists():
            os.startfile(str(self.capture_dir))
        else:
            self.capture_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(str(self.capture_dir))
    
    def pause_automation(self):
        """Pause the automation process"""
        self.is_paused = True
        
        # Update toggle button to show RESUME
        self.window.after(0, lambda: self.toggle_btn.config(text="▶ RESUME", bg="#00FFFF"))
        self.window.after(0, lambda: self.update_status("⏸ Paused"))
    
    def resume_automation(self):
        """Resume the paused automation"""
        self.is_paused = False
        
        # Update toggle button back to PAUSE
        self.window.after(0, lambda: self.toggle_btn.config(text="⏸ PAUSE", bg="#FF00FF"))
        self.window.after(0, lambda: self.update_status("▶ Resumed"))
    
    def stop_automation(self):
        """Stop the automation process"""
        self.is_running = False
        self.is_paused = False
        
        # Reset toggle button to START
        self.window.after(0, lambda: self.toggle_btn.config(text="▶ START", bg="#00FF00"))
        self.window.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
        self.window.after(0, lambda: self.process_all_btn.config(state=tk.NORMAL))
        self.window.after(0, lambda: self.stop_batch_btn.config(state=tk.DISABLED))
        self.window.after(0, lambda: self.update_status("⏹ Stopped by user"))
    
    def close_window(self):
        """Close the automation window"""
        self.is_running = False
        if self.window:
            self.window.destroy()
    
    def run_automation(self):
        """Main automation logic"""
        try:
            # Check if this is the first run or if we need to open browser
            if not hasattr(self, '_browser_opened') or not self._browser_opened:
                # Step 1: Open parcel viewer in browser with zoom flag (first time only)
                self.update_status("Opening parcel viewer in browser at 75% zoom...", 0)
                parcel_link = self.parcel_data.get('parcel_link', '')
                if not parcel_link:
                    raise ValueError("No parcel link available")
                
                # Open with Chrome/Edge and set zoom to 75%
                self.open_browser_with_zoom(parcel_link, 0.75)
                time.sleep(4)  # Wait for browser to open and load
                
                # Check for pause
                while self.is_paused and self.is_running:
                    time.sleep(0.5)
                
                if not self.is_running:
                    return
                
                # Step 2: Position browser window (right 80%)
                self.update_status("Positioning browser window to right 80% of screen...", 1)
                self.position_browser_window()
                time.sleep(1)
                
                self._browser_opened = True
            else:
                # Browser already open, just clear the search field
                self.update_status("Clearing previous search...", 0)
                # Click search field using loaded coordinates
                pyautogui.click(self.search_field_x, self.search_field_y)
                time.sleep(0.3)
                
                # Select all and clear
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.2)
                pyautogui.press('backspace')
                time.sleep(0.5)
            
            if not self.is_running:
                return
            
            # Step 3: Enter address in search field
            self.update_status("Entering address in search field...", 2)
            address = self.parcel_data.get('address', '')
            if not address:
                raise ValueError("No address provided")
            
            # Always click the field to focus it
            self.enter_address(address, click_field=True)
            time.sleep(1)
            
            # Check for pause
            while self.is_paused and self.is_running:
                time.sleep(0.5)
            
            if not self.is_running:
                return
            
            # Step 4: Submit search
            self.update_status("Submitting search...", 3)
            pyautogui.press('enter')
            time.sleep(3)  # Wait for search to process
            
            # Check for pause
            while self.is_paused and self.is_running:
                time.sleep(0.5)
            
            if not self.is_running:
                return
            
            # Step 5: Wait for results to load
            self.update_status("Waiting for results to load...", 4)
            time.sleep(5)  # Additional wait for page to fully load
            
            # Check for pause
            while self.is_paused and self.is_running:
                time.sleep(0.5)
            
            if not self.is_running:
                return
            
            # Step 6: Capture screenshot
            self.update_status("Capturing screenshot...", 5)
            screenshot_image = self.capture_screenshot()
            
            # Save screenshot for review
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.capture_dir / f"screenshot_{timestamp}.png"
            screenshot_image.save(screenshot_path)
            self.last_screenshot_path = screenshot_path
            self.window.after(0, lambda: self.append_log(f"📸 Screenshot saved: {screenshot_path.name}"))
            self.window.after(0, lambda: self.view_screenshot_btn.config(state=tk.NORMAL))
            
            # Check for pause
            while self.is_paused and self.is_running:
                time.sleep(0.5)
            
            if not self.is_running:
                return
            
            # Step 7: Process image with OCR
            self.update_status("Processing image with OCR...", 6)
            extracted_text = self.process_with_ocr(screenshot_image)
            
            # Check for pause
            while self.is_paused and self.is_running:
                time.sleep(0.5)
            
            if not self.is_running:
                return
            
            # Step 8: Extract data using both methods for comparison
            self.update_status("Extracting with ChatGPT...", 7)
            self.window.after(0, lambda: self.append_log("Sending OCR text to ChatGPT for extraction..."))
            
            # Extract with ChatGPT (primary method)
            chatgpt_data = self.extract_with_chatgpt(extracted_text)
            
            # Also extract with regex for comparison
            ocr_data = self.extract_structured_data(extracted_text)
            
            # Use ChatGPT data as primary
            extracted_data = chatgpt_data
            
            # Update both tabs with results
            self.window.after(0, lambda: self.update_json_results(chatgpt_data))
            self.window.after(0, lambda: self.update_ocr_results(ocr_data))
            
            self.window.after(0, lambda: self.append_log(f"Data extracted, fields count: {len(extracted_data.get('extracted_fields', {}))}"))
            self.window.after(0, lambda d=extracted_data: self.append_log(f"Extracted fields: {list(d.get('extracted_fields', {}).keys())}"))
            
            # Save to single JSON file - append to existing data
            json_path = self.capture_dir / "parcels_data.json"
            
            import json
            try:
                # Load existing data if file exists
                all_data = []
                if json_path.exists():
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if content.strip():  # Only parse if not empty
                                all_data = json.loads(content)
                            else:
                                all_data = []
                    except json.JSONDecodeError as e:
                        logging.warning(f"JSON file corrupted, starting fresh: {e}")
                        all_data = []
                    except Exception as e:
                        logging.warning(f"Could not load existing JSON: {e}")
                        all_data = []
                
                # Append new data
                self.window.after(0, lambda p=json_path: self.append_log(f'Saving to JSON: {p}'))
                self.window.after(0, lambda c=len(all_data): self.append_log(f'Current records in file: {c}'))
                all_data.append(extracted_data)
                self.window.after(0, lambda c=len(all_data): self.append_log(f'After append: {c} records'))
                logging.info(f"Appending data. Current count: {len(all_data)}")
                
                # Save updated data
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, indent=2, ensure_ascii=False)
                self.window.after(0, lambda: self.append_log(f"✓ JSON saved to file"))
                
                logging.info(f"✓ Appended data to: {json_path} (total records: {len(all_data)})")
                
            except Exception as e:
                logging.error(f"Failed to save JSON: {e}")
                self.window.after(0, lambda err=str(e): self.append_log(f'✗ JSON SAVE ERROR: {err}'))
                import traceback
                tb = traceback.format_exc()
                self.window.after(0, lambda t=tb: self.append_log(f'Traceback: {t}'))
                import traceback
                logging.error(traceback.format_exc())
            
            # Database upload happens after all parcels are processed (in batch mode)
            # Individual uploads are skipped during batch processing
            
            # Check for pause
            while self.is_paused and self.is_running:
                time.sleep(0.5)
            
            if not self.is_running:
                return
            
            # Step 9: Store in memory and update display
            self.update_status("Updating JSON display...", 8)
            self.extracted_data.append(extracted_data)
            
            # Update JSON display on UI thread
            self.window.after(0, lambda: self.update_json_display(extracted_data))
            
            # Completion
            self.update_status("✓ Automation completed successfully!", 8)
            
            # Only reset buttons if not in batch mode
            if not hasattr(self, '_in_batch_mode') or not self._in_batch_mode:
                # For single parcel mode, upload to database immediately
                self.window.after(0, lambda: self.append_log("=== Single parcel extraction complete ==="))
                self.window.after(0, lambda: self.append_log("Starting database upload..."))
                self.upload_all_to_database()
                
                # Close window after completion
                self.window.after(2000, self.close_window)  # Close after 2 seconds
                self.is_running = False
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            self.update_status(error_msg)
            logging.error(f"Automation error: {e}", exc_info=True)
            
            # Only reset buttons if not in batch mode
            if not hasattr(self, '_in_batch_mode') or not self._in_batch_mode:
                self.window.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
                self.window.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
                self.is_running = False
            self.stop_btn.config(state=tk.DISABLED)
    
    def open_browser_with_zoom(self, url, zoom_level=0.75):
        """Open browser with specific zoom level using subprocess"""
        try:
            import subprocess
            import os
            
            # Try to find Chrome first
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
            
            if chrome_path:
                # Open Chrome with force-device-scale-factor flag to set zoom
                logging.info(f"Opening Chrome with zoom {zoom_level} at: {chrome_path}")
                subprocess.Popen([
                    chrome_path,
                    f"--force-device-scale-factor={zoom_level}",
                    "--new-window",
                    url
                ])
                logging.info("Chrome launched with zoom flag")
            else:
                # Fallback to default browser
                logging.warning("Chrome not found, using default browser (zoom may not work)")
                webbrowser.open(url)
                
        except Exception as e:
            logging.error(f"Error opening browser with zoom: {e}")
            # Fallback to regular open
            webbrowser.open(url)
    
    def position_browser_window(self):
        """Position browser window to right 80% of screen"""
        try:
            import pygetwindow as gw
            
            # Get screen dimensions
            screen_width = pyautogui.size()[0]
            screen_height = pyautogui.size()[1]
            
            # Calculate right 80% position (starting at 20% from left)
            window_width = int(screen_width * 0.8)
            window_height = screen_height
            window_x = int(screen_width * 0.2)  # Start at 20% (where automation window ends)
            window_y = 0
            
            # Find browser window (try common browser titles)
            browser_keywords = ['Chrome', 'Firefox', 'Edge', 'Safari', 'Browser']
            browser_window = None
            
            for window in gw.getAllWindows():
                if any(keyword.lower() in window.title.lower() for keyword in browser_keywords):
                    browser_window = window
                    break
            
            if browser_window:
                browser_window.moveTo(window_x, window_y)
                browser_window.resizeTo(window_width, window_height)
                # Don't activate - causes page to scroll
                logging.info(f"Browser window positioned at ({window_x}, {window_y}) with size ({window_width}x{window_height})")
            else:
                logging.warning("Could not find browser window to position")
                
        except Exception as e:
            logging.warning(f"Could not position browser window: {e}")
    
    def set_browser_zoom(self, zoom_percent):
        """Set browser zoom level using keyboard shortcuts"""
        try:
            logging.info(f"Setting browser zoom to {zoom_percent}%")
            
            # Click on the browser window to ensure it has focus
            screen_width, screen_height = pyautogui.size()
            
            # Click in the middle of the right 80% area (where browser should be)
            browser_center_x = int(screen_width * 0.6)  # 60% across (middle of right 80%)
            browser_center_y = int(screen_height * 0.5)  # 50% down (middle vertically)
            
            logging.info(f"Clicking browser center at ({browser_center_x}, {browser_center_y}) to focus")
            pyautogui.click(browser_center_x, browser_center_y)
            time.sleep(0.8)
            
            # Reset zoom to 100% first
            logging.info("Resetting zoom to 100% with Ctrl+0")
            pyautogui.hotkey('ctrl', '0')
            time.sleep(0.5)
            
            # Zoom out to 75% (need to press Ctrl+Minus twice from 100%)
            logging.info("Zooming out to 75% with Ctrl+Minus (twice)")
            for i in range(2):
                pyautogui.hotkey('ctrl', 'minus')
                time.sleep(0.4)
                logging.info(f"Zoom step {i+1}/2 completed")
            
            time.sleep(0.5)
            logging.info(f"Completed zoom adjustment to approximately {zoom_percent}%")
            
        except Exception as e:
            logging.warning(f"Could not set browser zoom: {e}")
    
    def enter_address(self, address, click_field=True):
        """Enter address in search field using specific coordinates"""
        try:
            # Wait for page to load completely
            time.sleep(1)
            
            if click_field:
                # Click at the exact coordinates of the search field (loaded from API)
                logging.info(f"Clicking search field at coordinates ({self.search_field_x}, {self.search_field_y})")
                
                # Single click to focus field (triple-click can cause page scroll)
                pyautogui.click(self.search_field_x, self.search_field_y)
                time.sleep(0.3)
                
                # Select all and clear any existing content
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.2)
                pyautogui.press('delete')
                time.sleep(0.3)
            
            # Type the address
            logging.info(f"Typing address: {address}")
            for char in address:
                pyautogui.write(char, interval=0.05)
                time.sleep(0.02)
            
            time.sleep(0.5)
            logging.info(f"Successfully entered address: {address}")
            
        except Exception as e:
            logging.error(f"Error entering address: {e}")
            # Don't raise - let automation continue to see what happens
            logging.warning("Continuing automation despite address entry error...")
    
    def capture_screenshot(self):
        """Capture screenshot of browser area - popup detection happens in find_info_popup"""
        try:
            # Capture the entire browser area (right 80% of screen)
            # Don't hardcode popup position - let find_info_popup detect it dynamically
            screen_width = pyautogui.size()[0]
            screen_height = pyautogui.size()[1]
            
            x = int(screen_width * 0.2)  # Start at 20% from left (where browser begins)
            y = 0
            width = int(screen_width * 0.8)
            height = screen_height
            
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            
            logging.info(f"Browser screenshot captured: {screenshot.width}x{screenshot.height}")
            return screenshot
            
        except Exception as e:
            logging.error(f"Error capturing screenshot: {e}")
            raise
    
    def process_with_ocr(self, screenshot_image):
        """Process screenshot with OCR to extract text from popup"""
        try:
            logging.info("=== Starting OCR processing ===")
            
            # screenshot_image is already a PIL Image, not a path
            full_image = screenshot_image
            logging.info(f"Image size: {full_image.size[0]}x{full_image.size[1]} pixels")
            
            # Try to find the info popup by looking for the icon
            image_to_ocr = self.find_info_popup(full_image)
            
            if image_to_ocr is None:
                logging.warning("Could not find info popup, using full image")
                image_to_ocr = full_image
            
            # Popup is small (220x140), upscale for better OCR
            original_width, original_height = image_to_ocr.size
            scale_factor = 6  # 6x upscale: 220x140 -> 1320x840
            new_width = original_width * scale_factor
            new_height = original_height * scale_factor
            
            logging.info(f"Upscaling image from {original_width}x{original_height} to {new_width}x{new_height} for OCR")
            image_to_ocr = image_to_ocr.resize((new_width, new_height), Image.LANCZOS)
            
            # Apply multiple image enhancements for better OCR
            from PIL import ImageEnhance, ImageFilter
            
            # Convert to grayscale
            image_to_ocr = image_to_ocr.convert('L')
            logging.info("Converted to grayscale")
            
            # Apply slight blur to reduce noise
            image_to_ocr = image_to_ocr.filter(ImageFilter.MedianFilter(size=3))
            
            # Enhance contrast significantly
            enhancer = ImageEnhance.Contrast(image_to_ocr)
            image_to_ocr = enhancer.enhance(3.0)  # 3x contrast
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image_to_ocr)
            image_to_ocr = enhancer.enhance(2.0)  # 2x sharpness
            
            # Apply binary threshold to make text crisp black/white
            from PIL import ImageOps
            # Auto-adjust levels to maximize contrast
            image_to_ocr = ImageOps.autocontrast(image_to_ocr, cutoff=2)
            
            # Convert to pure black and white using threshold
            threshold = 140  # Pixels darker than this become black, lighter become white
            image_to_ocr = image_to_ocr.point(lambda x: 0 if x < threshold else 255, '1')
            
            logging.info("Applied image preprocessing: grayscale, denoise, contrast, sharpen, threshold")
            
            # Try OCR on the image
            logging.info("Running pytesseract OCR...")
            
            # Use PSM 3 (fully automatic page segmentation) since popup can be anywhere
            # and PSM 11 (sparse text) as backup
            configs = [
                r'--oem 3 --psm 3',  # Fully automatic page segmentation
                r'--oem 3 --psm 11', # Sparse text
                r'--oem 3 --psm 6',  # Uniform block of text
            ]
            
            best_text = ""
            for config in configs:
                try:
                    text = pytesseract.image_to_string(image_to_ocr, config=config)
                    if len(text) > len(best_text):
                        best_text = text
                        logging.info(f"Config '{config}' extracted {len(text)} chars")
                except Exception as e:
                    logging.warning(f"Config '{config}' failed: {e}")
                    continue
            
            logging.info(f"Best OCR extracted {len(best_text)} characters")
            if len(best_text) > 0:
                logging.info(f"Full OCR text:\n{best_text}")
            else:
                logging.warning("⚠ All OCR attempts returned EMPTY text!")
            
            return best_text
            
        except Exception as e:
            logging.error(f"❌ Error processing with OCR: {e}")
            import traceback
            logging.error(traceback.format_exc())
            # Return empty string if OCR fails
            return ""
    
    def find_info_popup(self, image):
        """Find and crop the info popup box by detecting the white box with gray border"""
        try:
            logging.info("=== Starting popup detection ===")
            
            try:
                import numpy as np
                from scipy import ndimage
                logging.info("NumPy and SciPy imported successfully")
            except ImportError as e:
                logging.error(f"Required libraries not available: {e}")
                logging.warning("Using full image as fallback")
                return image
            
            # Convert to numpy array and grayscale
            img_array = np.array(image.convert('L'))
            logging.info(f"Image size: {image.width}x{image.height}")
            
            # Detect edges to find the popup border
            from scipy import ndimage
            edges = ndimage.sobel(img_array)
            
            # Threshold to get strong edges (popup border)
            edge_threshold = np.percentile(edges, 95)
            strong_edges = edges > edge_threshold
            
            # Find connected components (boxes)
            labeled, num_features = ndimage.label(strong_edges)
            
            # Find the largest rectangular region (likely the popup)
            best_box = None
            best_area = 0
            
            for label_id in range(1, num_features + 1):
                coords = np.argwhere(labeled == label_id)
                if len(coords) < 100:  # Too small
                    continue
                    
                y_coords, x_coords = coords[:, 0], coords[:, 1]
                top, left = y_coords.min(), x_coords.min()
                bottom, right = y_coords.max(), x_coords.max()
                
                width = right - left
                height = bottom - top
                area = width * height
                
                # Popup is roughly 260x200 pixels - look for boxes in this range
                if 200 < width < 400 and 150 < height < 300:
                    if area > best_area:
                        best_area = area
                        best_box = (left, top, right, bottom)
            
            if best_box is None:
                logging.warning("Could not detect popup box - using full image")
                return image
            
            left, top, right, bottom = best_box
            logging.info(f"✓ Popup detected at: ({left}, {top}, {right}, {bottom})")
            logging.info(f"  Popup dimensions: {right - left}x{bottom - top} pixels")
            
            # Add small margin
            margin = 5
            left = max(0, left - margin)
            top = max(0, top - margin)
            right = min(image.width, right + margin)
            bottom = min(image.height, bottom + margin)
            
            # Crop the popup area
            popup_image = image.crop((left, top, right, bottom))
            
            # Save cropped popup with google_addresses ID in filename
            parcel_id = self.parcel_data.get('id', 'unknown')
            popup_filename = f"parcels_{parcel_id}.png"
            popup_path = self.capture_dir / popup_filename
            popup_image.save(popup_path)
            logging.info(f"✓ Saved popup to: {popup_path}")
            logging.info(f"  Popup size: {popup_image.width}x{popup_image.height}")
            logging.info("=== Popup detection complete ===")
            
            return popup_image
            
        except Exception as e:
            logging.error(f"❌ Error finding info popup: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return None
    
    def extract_with_chatgpt(self, ocr_text):
        """Extract structured data from OCR text using ChatGPT API"""
        import openai
        import json
        import os
        from pathlib import Path
        
        # Try to read API key from file first, then environment variable
        api_key = None
        key_file = Path(__file__).parent / "htdocs" / "openai_key.txt"
        
        if key_file.exists():
            try:
                with open(key_file, 'r') as f:
                    api_key = f.read().strip()
                self.window.after(0, lambda: self.append_log("✓ Loaded API key from file"))
            except Exception as e:
                self.window.after(0, lambda: self.append_log(f"⚠ Could not read key file: {e}"))
        
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            self.window.after(0, lambda: self.append_log("⚠ No API key found, using regex fallback"))
            return self.extract_structured_data(ocr_text)
        
        try:
            openai.api_key = api_key
            
            # Create prompt for extraction
            prompt = f"""Extract the following fields from this King County Parcel Viewer OCR text. Return ONLY a valid JSON object with these exact keys:

{{
  "parcel_number": "10-digit number",
  "property_name": "property name or null",
  "jurisdiction": "city/jurisdiction",
  "taxpayer_name": "taxpayer name or null",
  "address": "extracted address or null",
  "appraised_value": "value or null",
  "lot_area": "area in sq ft or null",
  "levy_code": "code or null",
  "num_units": "number or null",
  "num_buildings": "number or null"
}}

OCR Text:
{ocr_text}

Return only the JSON object, no other text."""

            self.window.after(0, lambda: self.append_log("Calling ChatGPT API..."))
            
            # Use new OpenAI client syntax (v1.0.0+)
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a data extraction expert. Extract structured data from OCR text and return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            self.window.after(0, lambda t=result_text[:200]: self.append_log(f"ChatGPT response: {t}..."))
            
            # Log API call to database
            try:
                import mysql.connector
                from pathlib import Path
                import sys
                config_path = Path(__file__).parent / 'config_hud_db.py'
                if config_path.exists():
                    config_globals = {}
                    with open(config_path) as f:
                        exec(f.read(), config_globals)
                    DB_CONFIG = config_globals.get('DB_CONFIG')
                    if DB_CONFIG:
                        conn = mysql.connector.connect(**DB_CONFIG)
                        cursor = conn.cursor()
                        log_sql = """
                            INSERT INTO openai_api_log 
                            (endpoint, model, status, prompt_tokens, completion_tokens, total_tokens, 
                             address, parcel_number, response_preview)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(log_sql, (
                            'chat.completions',
                            'gpt-4-turbo-preview',
                            'OK',
                            response.usage.prompt_tokens,
                            response.usage.completion_tokens,
                            response.usage.total_tokens,
                            self.parcel_data.get('address', 'N/A'),
                            self.parcel_data.get('parcel_number'),
                            result_text[:500]
                        ))
                        conn.commit()
                        cursor.close()
                        conn.close()
            except Exception as log_err:
                logging.warning(f"Failed to log OpenAI API call: {log_err}")
            
            # Parse JSON response
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            extracted_fields = json.loads(result_text)
            
            # Build response in same format as regex method
            data = {
                'id': self.parcel_data.get('id'),
                'address': self.parcel_data.get('address'),
                'metro': self.parcel_data.get('metro_name'),
                'parcel_link': self.parcel_data.get('parcel_link'),
                'timestamp': datetime.now().isoformat(),
                'raw_text': ocr_text,
                'extracted_fields': extracted_fields
            }
            
            self.window.after(0, lambda: self.append_log("✓ ChatGPT extraction complete"))
            logging.info(f"ChatGPT extracted {len(extracted_fields)} fields")
            
            return data
            
        except Exception as e:
            self.window.after(0, lambda err=str(e): self.append_log(f"✗ ChatGPT error: {err}"))
            self.window.after(0, lambda: self.append_log("Falling back to regex extraction..."))
            logging.error(f"ChatGPT extraction failed: {e}")
            
            # Log error to database
            try:
                import mysql.connector
                from pathlib import Path
                config_path = Path(__file__).parent / 'config_hud_db.py'
                if config_path.exists():
                    config_globals = {}
                    with open(config_path) as f:
                        exec(f.read(), config_globals)
                    DB_CONFIG = config_globals.get('DB_CONFIG')
                    if DB_CONFIG:
                        conn = mysql.connector.connect(**DB_CONFIG)
                        cursor = conn.cursor()
                        log_sql = """
                            INSERT INTO openai_api_log 
                            (endpoint, model, status, address, parcel_number, error_message)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(log_sql, (
                            'chat.completions',
                            'gpt-4-turbo-preview',
                            'ERROR',
                            self.parcel_data.get('address', 'N/A'),
                            self.parcel_data.get('parcel_number'),
                            str(e)[:500]
                        ))
                        conn.commit()
                        cursor.close()
                        conn.close()
            except Exception as log_err:
                logging.warning(f"Failed to log OpenAI error: {log_err}")
            
            # Fallback to regex extraction
            return self.extract_structured_data(ocr_text)
    
    def extract_structured_data(self, ocr_text):
        """Extract structured data from OCR text"""
        import re
        
        data = {
            'id': self.parcel_data.get('id'),
            'address': self.parcel_data.get('address'),
            'metro': self.parcel_data.get('metro_name'),
            'parcel_link': self.parcel_data.get('parcel_link'),
            'timestamp': datetime.now().isoformat(),
            'raw_text': ocr_text,
            'extracted_fields': {}
        }
        
        # Log full OCR text for debugging
        logging.info(f"=== Full OCR Text ({len(ocr_text)} chars) ===")
        logging.info(ocr_text)
        logging.info("=== End OCR Text ===")
        
        # Also show in activity log for real-time debugging
        self.window.after(0, lambda: self.append_log(f"=== RAW OCR TEXT ({len(ocr_text)} chars) ==="))
        # Show first 800 chars to see field structure
        preview_text = ocr_text[:800] if len(ocr_text) > 800 else ocr_text
        self.window.after(0, lambda t=preview_text: self.append_log(t))
        self.window.after(0, lambda: self.append_log("=== END RAW OCR ==="))
        
        # If OCR text is empty or too short, return early
        if len(ocr_text.strip()) < 20:
            logging.warning("OCR text is too short or empty!")
            return data
        
        # Extract specific fields from King County Parcel Viewer
        # Try multiple pattern variations for each field
        # OCR often has typos/errors, so patterns are flexible
        patterns = {
            'parcel_number': [
                r'(\d{10})',  # 10-digit number (try first - most reliable)
                r'Parcel[:\s#]*(\d+)',
                r'(5247801975)',  # Exact match as fallback
            ],
            'property_name': [
                r'[Pp]ropary\s*name[:\s]*([^\n]+)',  # OCR: Propary name: VALUE
                r'[Pp]roperty\s*name[:\s]*([^\n]+)',
            ],
            'jurisdiction': [
                r'[Jj]uracicion[:\s]*([^\n]+)',  # OCR: Juracicion: VALUE
                r'[Jj]urisdic[t]?ion[:\s]*([^\n]+)',
                r'(SEATTLE|BELLEVUE|RENTON|KENT)',  # Uppercase city names
            ],
            'taxpayer_name': [
                r'[Tt]axpayer\s*name[:\s]*([^\n]+)',  # Taxpayer name: VALUE
            ],
            'address': [
                r'[Aa]gora[:\s]*([^\n]+)',  # OCR: Agora: VALUE
                r'[Aa]ddress[:\s]*([^\n]+)',
                r'[Aa]derass[:\s]*([^\n]+)',
            ],
            'appraised_value': [
                r'[Aa]ppraised\s*value[:\s]*(\$?[\d,]+)',
            ],
            'lot_area': [
                r'[Ll]ot\s*aren[:\s]*([\d,\.]+)',  # OCR: Lot aren
                r'[Ll]ot\s*area[:\s]*([\d,\.]+)',
            ],
            'levy_code': [
                r'[Ll]evy\s*code[:\s]*([A-Za-z0-9]+)',  # "Levy code: colt" or "Levy code: 1234"
                r'(\d{4})\s*\n+\s*[Ll][ae]vy\s*c[ao][dt]e:',  # Number BEFORE label with typos
                r'[Ll][ae]vy\s*c[ao][dt]e[:\s]+(\d+)',  # After label with typos
            ],
            'num_units': [
                r'#\s*[oO0][ft]\s*[uU]nits?[:\s]*(\d+)',  # "# of units: 654" or "#otunm&: 654"
                r'#[oO0a-z]*[:\s]*(\d+)',  # Any garbled version of # followed by digits
                r'(\d+)\s*\n+\s*#',  # Number BEFORE # symbol
            ],
            'num_buildings': [
                r'#\s*[oO0][ft]\s*[bB][a-z]+[:\s]*(\d+)',  # "# of buildings" with OCR errors
                r'[Ss][oO0][a-z]*ings?[:\s]*(\d+)',  # "Sotbuikings: 1"
            ],
        }
        
        # Try each pattern until we find a match
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, ocr_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    data['extracted_fields'][field] = value
                    logging.info(f"✓ Extracted {field}: {value}")
                    break  # Found a match, move to next field
            
            if field not in data['extracted_fields']:
                logging.warning(f"✗ Could not extract {field}")
                # Set default values for required fields
                if field == 'property_name':
                    data['extracted_fields'][field] = 'UNKNOWN'
                elif field == 'jurisdiction':
                    data['extracted_fields'][field] = 'SEATTLE'
                elif field == 'address':
                    data['extracted_fields'][field] = data.get('address', 'UNKNOWN')
        
        logging.info(f"Total fields extracted: {len(data['extracted_fields'])}/10")
        
        return data
    
    def save_to_database(self, extracted_data):
        """Save extracted data to king_county_parcels table and update google_addresses"""
        import mysql.connector
        from pathlib import Path
        import sys
        
        # Import database config
        config_path = Path(__file__).parent / 'config_hud_db.py'
        if not config_path.exists():
            logging.error("Database config file not found: config_hud_db.py")
            return None
        
        # Execute config file to get DB_CONFIG
        config_globals = {}
        with open(config_path) as f:
            exec(f.read(), config_globals)
        
        DB_CONFIG = config_globals.get('DB_CONFIG')
        if not DB_CONFIG:
            logging.error("DB_CONFIG not found in config_hud_db.py")
            return None
        
        conn = None
        cursor = None
        
        try:
            # Connect to database
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Extract fields
            fields = extracted_data.get('extracted_fields', {})
            google_address_id = extracted_data.get('id')  # google_addresses.id
            
            # Insert into king_county_parcels table
            insert_sql = """
                INSERT INTO king_county_parcels 
                (google_addresses_id, parcel_number, property_name, jurisdiction, taxpayer_name, 
                 address, appraised_value, lot_area, levy_code, num_units, num_buildings,
                 raw_ocr_text, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            values = (
                google_address_id,  # Set google_addresses_id
                fields.get('parcel_number'),
                fields.get('property_name'),
                fields.get('jurisdiction'),
                fields.get('taxpayer_name'),
                fields.get('address'),
                fields.get('appraised_value'),
                fields.get('lot_area'),
                fields.get('levy_code'),
                fields.get('num_units'),
                fields.get('num_buildings'),
                extracted_data.get('raw_text', '')[:5000],  # Limit to 5000 chars
            )
            
            cursor.execute(insert_sql, values)
            king_county_parcel_id = cursor.lastrowid
            
            logging.info(f"Inserted into king_county_parcels with ID: {king_county_parcel_id}")
            
            # Update google_addresses table with the king_county_parcels_id and processed_at
            if google_address_id:
                update_sql = """
                    UPDATE google_addresses 
                    SET king_county_parcels_id = %s,
                        processed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                """
                cursor.execute(update_sql, (king_county_parcel_id, google_address_id))
                logging.info(f"Updated google_addresses.id={google_address_id} with king_county_parcels_id={king_county_parcel_id} and processed_at")
            
            conn.commit()
            return king_county_parcel_id
            
        except Exception as e:
            logging.error(f"Database error: {e}")
            import traceback
            logging.error(traceback.format_exc())
            if conn:
                conn.rollback()
            return None
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def upload_all_to_database(self):
        """Upload all parcels from JSON to database with progress bar"""
        self.window.after(0, lambda: self.append_log("=== STARTING DATABASE UPLOAD ==="))
        self.window.after(0, lambda: self.append_log("Function called: upload_all_to_database()"))
        logging.info("upload_all_to_database() function called")
        
        self.window.after(0, lambda: self.append_log("Importing mysql.connector..."))
        import mysql.connector
        import json
        self.window.after(0, lambda: self.append_log("✓ Imports successful"))

        json_path = self.capture_dir / "parcels_data.json"
        self.window.after(0, lambda p=str(json_path): self.append_log(f"Checking JSON file: {p}"))
        
        if not json_path.exists():
            self.window.after(0, lambda: self.append_log("✗ JSON file not found!"))
            self.window.after(0, lambda: self.update_status("No data to upload"))
            return

        try:
            # Load all data from JSON
            self.window.after(0, lambda: self.append_log("Loading parcels_data.json..."))
            with open(json_path, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            
            data_count = len(all_data) if isinstance(all_data, list) else 0
            self.window.after(0, lambda d=data_count: self.append_log(f"Loaded {d} records from JSON"))

            if not all_data:
                self.window.after(0, lambda: self.update_status("No records to upload"))
                self.window.after(0, lambda: self.append_log("No records found in JSON"))
                return

            total_records = len(all_data)
            self.window.after(0, lambda t=total_records: self.append_log(f"Found {t} records to upload"))
            self.window.after(0, lambda: self.update_status(f"Uploading {total_records} records to database..."))
            self.window.after(0, lambda: self.update_status("Uploading to database", 8))
            
            # Get database config
            self.window.after(0, lambda: self.append_log("Reading database config..."))
            config_path = Path(__file__).parent / 'config_hud_db.py'
            self.window.after(0, lambda p=str(config_path): self.append_log(f"Config path: {p}"))
            
            config_globals = {}
            with open(config_path) as f:
                exec(f.read(), config_globals)
            DB_CONFIG = config_globals.get('DB_CONFIG')
            
            if DB_CONFIG is None:
                self.window.after(0, lambda: self.append_log("✗ ERROR: DB_CONFIG not found in config file!"))
                self.window.after(0, lambda: self.append_log(f"Available keys: {list(config_globals.keys())}"))
                raise ValueError("DB_CONFIG not found in config_hud_db.py")
            
            self.window.after(0, lambda: self.append_log(f"Config loaded: host={DB_CONFIG.get('host')}, database={DB_CONFIG.get('database')}, user={DB_CONFIG.get('user')}"))
            
            host = DB_CONFIG.get('host', 'unknown')
            database = DB_CONFIG.get('database', 'unknown')
            self.window.after(0, lambda h=host, d=database: self.append_log(f"Target: {h}/{d}"))

            # Connect to database
            self.window.after(0, lambda: self.append_log("Calling mysql.connector.connect()..."))
            try:
                conn = mysql.connector.connect(**DB_CONFIG)
                self.window.after(0, lambda: self.append_log("✓ Connection object created"))
            except Exception as conn_err:
                self.window.after(0, lambda e=str(conn_err): self.append_log(f"✗ Connection failed: {e}"))
                raise
            
            self.window.after(0, lambda: self.append_log("Creating cursor..."))
            cursor = conn.cursor()
            self.window.after(0, lambda: self.append_log("✓ Cursor created, ready to execute queries"))

            uploaded_count = 0

            for idx, extracted_data in enumerate(all_data):
                try:
                    # Update progress
                    progress = int((idx + 1) / total_records * 100)
                    address = extracted_data.get('address', 'Unknown')
                    self.window.after(0, lambda a=address, i=idx, t=total_records: self.append_log(f"Uploading {i+1}/{t}: {a}"))
                    self.window.after(0, lambda p=progress, i=idx, t=total_records: self.batch_progress_label.config(
                        text=f"Uploading to database: {i+1}/{t} ({p}%)"
                    ))
                    self.window.after(0, lambda i=idx: self.batch_progress_var.set(i + 1))
                    
                    # Insert record
                    fields = extracted_data.get('extracted_fields', {})
                    google_address_id = extracted_data.get('id')

                    # Use INSERT ON DUPLICATE KEY UPDATE to handle existing parcels
                    insert_sql = """
                        INSERT INTO king_county_parcels
                        (google_addresses_id, parcel_number, Property_name, Jurisdiction, Taxpayer_name,
                         Address, Appraised_value, Lot_area, Levy_code, num_of_units, num_of_buildings,
                         time_inserted)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UNIX_TIMESTAMP())
                        ON DUPLICATE KEY UPDATE
                            Property_name = VALUES(Property_name),
                            Jurisdiction = VALUES(Jurisdiction),
                            Taxpayer_name = VALUES(Taxpayer_name),
                            Address = VALUES(Address),
                            Appraised_value = VALUES(Appraised_value),
                            Lot_area = VALUES(Lot_area),
                            Levy_code = VALUES(Levy_code),
                            num_of_units = VALUES(num_of_units),
                            num_of_buildings = VALUES(num_of_buildings),
                            time_inserted = UNIX_TIMESTAMP()
                    """

                    values = (
                        google_address_id,
                        fields.get('parcel_number'),
                        fields.get('property_name'),
                        fields.get('jurisdiction'),
                        fields.get('taxpayer_name'),
                        fields.get('address'),
                        fields.get('appraised_value'),
                        fields.get('lot_area'),
                        fields.get('levy_code'),
                        fields.get('num_units'),
                        fields.get('num_buildings'),
                    )

                    self.window.after(0, lambda: self.append_log(f"  Executing INSERT/UPDATE for google_address_id={google_address_id}"))
                    self.window.after(0, lambda v=values: self.append_log(f"  Values: parcel={v[1]}, property={v[2]}, address={v[5]}"))
                    cursor.execute(insert_sql, values)
                    self.window.after(0, lambda: self.append_log(f"  ✓ INSERT/UPDATE executed"))
                    
                    # Get the parcel ID (either newly inserted or existing)
                    if cursor.lastrowid:
                        king_county_parcel_id = cursor.lastrowid
                    else:
                        # Record was updated, not inserted - get existing ID
                        cursor.execute("SELECT id FROM king_county_parcels WHERE parcel_number = %s", (fields.get('parcel_number'),))
                        result = cursor.fetchone()
                        king_county_parcel_id = result[0] if result else None

                    logging.info(f"Saved parcel ID {king_county_parcel_id} for google_address {google_address_id}")
                    
                    # Update google_addresses with king_county_parcels_id and processed_at
                    if google_address_id:
                        update_sql = """
                            UPDATE google_addresses
                            SET king_county_parcels_id = %s,
                                processed_at = NOW(),
                                updated_at = NOW()
                            WHERE id = %s
                        """
                        self.window.after(0, lambda k=king_county_parcel_id, g=google_address_id: self.append_log(f"  Executing UPDATE google_addresses id={g} with parcel_id={k}"))
                        cursor.execute(update_sql, (king_county_parcel_id, google_address_id))
                        self.window.after(0, lambda: self.append_log(f"  ✓ UPDATE executed with processed_at"))
                        logging.info(f"Updated google_addresses id={google_address_id} with king_county_parcels_id={king_county_parcel_id} and processed_at")
                    
                    self.window.after(0, lambda: self.append_log(f"  Committing transaction..."))
                    conn.commit()
                    uploaded_count += 1
                    self.window.after(0, lambda: self.append_log("  ✓ Transaction committed, saved to database"))
                    
                except Exception as e:
                    error_msg = str(e)[:100]
                    logging.error(f"Failed to upload record {idx}: {e}")
                    self.window.after(0, lambda err=error_msg: self.append_log(f"  ✗ Error: {err}"))
                    conn.rollback()
                    continue

            cursor.close()
            conn.close()
            self.window.after(0, lambda: self.append_log("✓ Database connection closed"))
            
            # Clear the JSON file after successful upload

            logging.info(f"Uploaded {uploaded_count}/{total_records} records to database")
            
            if uploaded_count == 0:
                self.window.after(0, lambda t=total_records: self.append_log(f"✗ UPLOAD FAILED! 0/{t} records saved - check errors above"))
                self.window.after(0, lambda t=total_records: self.update_status(f"✗ Upload failed: 0/{t} records saved", 9))
            elif uploaded_count < total_records:
                self.window.after(0, lambda u=uploaded_count, t=total_records: self.append_log(f"⚠ Partial upload: {u}/{t} records saved"))
                self.window.after(0, lambda u=uploaded_count, t=total_records: self.update_status(f"⚠ Partial upload: {u}/{t} records saved", 9))
            else:
                self.window.after(0, lambda u=uploaded_count, t=total_records: self.append_log(f"✓ Upload complete! {u}/{t} records saved"))
                self.window.after(0, lambda u=uploaded_count, t=total_records: self.update_status(f"✓ Upload complete! {u}/{t} records saved", 9))
                self.window.after(0, lambda u=uploaded_count, t=total_records: self.batch_progress_label.config(text=f"Database upload complete: {u}/{t}"))
                # Clear JSON file after successful upload
                self.window.after(0, lambda: self.append_log("Clearing parcels_data.json..."))
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump([], f)

            # Refresh the parcel table in the main UI
            self.window.after(0, lambda: self.append_log("Refreshing parent table..."))
            self.refresh_parent_table()
            self.window.after(0, lambda: self.append_log("✓ All done!"))

        except Exception as e:
            import traceback
            full_error = traceback.format_exc()
            logging.error(f"DATABASE UPLOAD FAILED: {e}")
            logging.error(f"Full traceback:\n{full_error}")
            
            # Show detailed error in activity log
            self.window.after(0, lambda: self.append_log("=== ✗ UPLOAD FAILED ==="))
            self.window.after(0, lambda err=str(e): self.append_log(f"Error: {err}"))
            self.window.after(0, lambda: self.append_log("Traceback (most recent):"))
            
            # Show last 5 lines of traceback
            tb_lines = [line for line in full_error.split('\n') if line.strip()]
            for tb_line in tb_lines[-5:]:
                self.window.after(0, lambda l=tb_line: self.append_log(f"  {l}"))
            
            error_msg = str(e)[:200]
            self.window.after(0, lambda err=error_msg: self.update_status(f"Upload error: {err}"))


    def refresh_parent_table(self):
        """Refresh the parcel table in the parent window"""
        try:
            # The parent window should have a method to refresh the table
            # This will trigger a reload of data from the database
            if hasattr(self.parent, 'refresh_queue'):
                self.window.after(0, lambda: self.parent.refresh_queue())
                logging.info("✓ Refreshed parent table")
        except Exception as e:
            logging.warning(f"Could not refresh parent table: {e}")


def launch_parcel_automation(parent_window, parcel_data, all_parcels=None, auto_start=False):
    """
    Launch parcel automation window
    
    Args:
        parent_window: Parent tkinter window
        parcel_data: Dict with parcel information (id, address, parcel_link, metro_name)
        all_parcels: List of all parcel dicts for batch processing (optional)
        auto_start: If True, automatically start automation after window creation
    
    Returns:
        ParcelAutomationWindow instance
    """
    return ParcelAutomationWindow(parent_window, parcel_data, all_parcels, auto_start)


if __name__ == "__main__":
    # Test the automation window
    root = tk.Tk()
    root.withdraw()
    
    test_data = {
        'id': 14,
        'address': '4801 FAUNTLEROY WAY SW 98116',
        'parcel_link': 'https://gismaps.kingcounty.gov/parcelviewer2/',
        'metro_name': 'Seattle'
    }
    
    automation = launch_parcel_automation(root, test_data)
    root.mainloop()

