"""
Batch Processor for Parcel Images
Run this to process accumulated images with OpenAI or OCR
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from extraction_methods import (
    count_unprocessed_images,
    process_with_openai,
    process_with_beautifulsoup
)

class BatchProcessorGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Parcel Image Batch Processor")
        self.window.geometry("600x500")
        self.window.configure(bg="white")
        
        self.parcels_dir = Path("Captures/parcels")
        self.parcels_dir.mkdir(parents=True, exist_ok=True)
        
        self.create_ui()
        self.update_status()
        
    def create_ui(self):
        # Header
        header = tk.Frame(self.window, bg="#3498db", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="📦 Parcel Image Batch Processor",
            font=("Segoe UI", 16, "bold"),
            bg="#3498db",
            fg="white"
        ).pack(expand=True)
        
        # Main content
        content = tk.Frame(self.window, bg="white", padx=30, pady=20)
        content.pack(fill="both", expand=True)
        
        # Status section
        status_frame = tk.LabelFrame(
            content,
            text="Status",
            font=("Segoe UI", 10, "bold"),
            bg="white",
            padx=15,
            pady=15
        )
        status_frame.pack(fill="x", pady=(0, 20))
        
        self.status_label = tk.Label(
            status_frame,
            text="Checking images...",
            font=("Segoe UI", 10),
            bg="white",
            fg="#2c3e50",
            justify="left"
        )
        self.status_label.pack(anchor="w")
        
        # Method selection
        method_frame = tk.LabelFrame(
            content,
            text="Extraction Method",
            font=("Segoe UI", 10, "bold"),
            bg="white",
            padx=15,
            pady=15
        )
        method_frame.pack(fill="x", pady=(0, 20))
        
        self.method_var = tk.StringVar(value="openai")
        
        openai_frame = tk.Frame(method_frame, bg="white")
        openai_frame.pack(fill="x", pady=5)
        
        tk.Radiobutton(
            openai_frame,
            text="🤖 OpenAI Vision API",
            variable=self.method_var,
            value="openai",
            font=("Segoe UI", 10, "bold"),
            bg="white",
            command=self.on_method_change
        ).pack(anchor="w")
        
        tk.Label(
            openai_frame,
            text="• Waits for 20 images minimum\n• 99%+ accuracy\n• Cost: ~$0.07 per 20 images\n• Batch processing",
            font=("Segoe UI", 8),
            bg="white",
            fg="#7f8c8d",
            justify="left"
        ).pack(anchor="w", padx=20)
        
        ocr_frame = tk.Frame(method_frame, bg="white")
        ocr_frame.pack(fill="x", pady=5)
        
        tk.Radiobutton(
            ocr_frame,
            text="🔍 OCR Pattern Matching",
            variable=self.method_var,
            value="beautifulsoup",
            font=("Segoe UI", 10, "bold"),
            bg="white",
            command=self.on_method_change
        ).pack(anchor="w")
        
        tk.Label(
            ocr_frame,
            text="• Processes immediately\n• Free\n• ~85% accuracy\n• Single image processing",
            font=("Segoe UI", 8),
            bg="white",
            fg="#7f8c8d",
            justify="left"
        ).pack(anchor="w", padx=20)
        
        # Process button
        self.process_btn = tk.Button(
            content,
            text="🚀 Process Images",
            font=("Segoe UI", 12, "bold"),
            bg="#27ae60",
            fg="white",
            padx=20,
            pady=10,
            command=self.process_images,
            cursor="hand2"
        )
        self.process_btn.pack(pady=10)
        
        # Log section
        log_frame = tk.LabelFrame(
            content,
            text="Processing Log",
            font=("Segoe UI", 10, "bold"),
            bg="white",
            padx=10,
            pady=10
        )
        log_frame.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(
            log_frame,
            font=("Consolas", 8),
            bg="#f8f9fa",
            height=8,
            wrap="word"
        )
        self.log_text.pack(fill="both", expand=True)
        
    def update_status(self):
        """Update the status display"""
        count, images = count_unprocessed_images(self.parcels_dir)
        
        method = self.method_var.get() if hasattr(self, 'method_var') else "openai"
        
        if method == "openai":
            if count >= 20:
                status_text = f"✅ Ready to process!\n📸 {count} unprocessed images found\n🎯 Will process first 20 images with OpenAI"
                self.process_btn.config(state="normal", bg="#27ae60")
            else:
                status_text = f"⏳ Waiting for more images...\n📸 {count} unprocessed images\n🎯 Need {20 - count} more for OpenAI batch (minimum 20)"
                self.process_btn.config(state="disabled", bg="#95a5a6")
        else:
            if count > 0:
                status_text = f"✅ Ready to process!\n📸 {count} unprocessed images found\n🎯 Will process all images with OCR"
                self.process_btn.config(state="normal", bg="#27ae60")
            else:
                status_text = f"❌ No images to process\n📸 All images have been processed"
                self.process_btn.config(state="disabled", bg="#95a5a6")
        
        self.status_label.config(text=status_text)
        
    def on_method_change(self):
        """Handle method selection change"""
        self.update_status()
        
    def log(self, message):
        """Add message to log"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.window.update()
        
    def process_images(self):
        """Process images with selected method"""
        method = self.method_var.get()
        self.log_text.delete("1.0", "end")
        self.log("="*60)
        self.log(f"Starting processing with {method.upper()}...")
        self.log("="*60)
        
        try:
            if method == "openai":
                # Redirect print to log
                import sys
                from io import StringIO
                old_stdout = sys.stdout
                sys.stdout = StringIO()
                
                result = process_with_openai(self.parcels_dir, min_batch_size=20)
                
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                
                self.log(output)
                
                if result:
                    messagebox.showinfo("Success", f"✅ Processed {result} parcels with OpenAI!")
                else:
                    messagebox.showwarning("Waiting", "⏳ Need 20 images to process batch")
                    
            else:  # beautifulsoup/OCR
                self.log("❌ OCR method not yet integrated into batch processor")
                self.log("Use the main automation window for single-image OCR processing")
                messagebox.showinfo("Info", "OCR method processes images individually during automation.\nUse the main parcel automation window.")
                
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            messagebox.showerror("Error", f"Processing failed: {str(e)}")
        
        finally:
            self.update_status()
            
    def run(self):
        """Start the GUI"""
        self.window.mainloop()

if __name__ == "__main__":
    app = BatchProcessorGUI()
    app.run()
