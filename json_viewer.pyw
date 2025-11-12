#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON Viewer - Simple viewer for extracted apartment listings
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys


class JSONViewer(tk.Tk):
    def __init__(self, json_file: Path):
        super().__init__()
        self.title(f"JSON Viewer - {json_file.name}")
        self.geometry("1000x600")
        
        self.json_file = json_file
        self.data = None
        
        self._build_ui()
        self._load_data()
        
    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#2C3E50")
        header.pack(fill="x", pady=(0, 8))
        
        tk.Label(header, text="📊 Extracted Listings Preview", 
                fg="white", bg="#2C3E50", font=("Segoe UI", 12, "bold"),
                padx=12, pady=10).pack(side="left")
        
        self.lbl_count = tk.Label(header, text="", fg="#95A5A6", bg="#2C3E50", 
                                 font=("Segoe UI", 9))
        self.lbl_count.pack(side="left", padx=12)
        
        # Buttons
        btn_frame = tk.Frame(header, bg="#2C3E50")
        btn_frame.pack(side="right", padx=12)
        
        tk.Button(btn_frame, text="Refresh", command=self._load_data,
                 bg="#3498DB", fg="white", font=("Segoe UI", 9),
                 relief="flat", padx=12, pady=4).pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="Close", command=self.destroy,
                 bg="#E74C3C", fg="white", font=("Segoe UI", 9),
                 relief="flat", padx=12, pady=4).pack(side="left", padx=4)
        
        # Treeview
        container = tk.Frame(self)
        container.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        columns = ("id", "title", "bedrooms", "bathrooms", "sqft", "price", "address", "network")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")
        
        # Column headers
        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="Title")
        self.tree.heading("bedrooms", text="Beds")
        self.tree.heading("bathrooms", text="Baths")
        self.tree.heading("sqft", text="Sqft")
        self.tree.heading("price", text="Price")
        self.tree.heading("address", text="Address")
        self.tree.heading("network", text="Network")
        
        # Column widths
        self.tree.column("id", width=140, minwidth=100)
        self.tree.column("title", width=220, minwidth=150)
        self.tree.column("bedrooms", width=60, minwidth=50)
        self.tree.column("bathrooms", width=60, minwidth=50)
        self.tree.column("sqft", width=70, minwidth=50)
        self.tree.column("price", width=80, minwidth=60)
        self.tree.column("address", width=250, minwidth=150)
        self.tree.column("network", width=100, minwidth=80)
        
        # Scrollbars
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        
        # Details panel
        details_frame = tk.LabelFrame(self, text="Details", font=("Segoe UI", 9, "bold"), padx=8, pady=8)
        details_frame.pack(fill="x", padx=12, pady=(0, 12))
        
        self.txt_details = tk.Text(details_frame, height=8, wrap="word", font=("Consolas", 9))
        self.txt_details.pack(fill="both", expand=True)
        
        # Bind selection
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
    
    def _load_data(self):
        """Load and display JSON data"""
        try:
            if not self.json_file.exists():
                messagebox.showerror("Error", f"File not found: {self.json_file}")
                return
            
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Populate tree
            if isinstance(self.data, list):
                for listing in self.data:
                    values = (
                        listing.get('id', 'N/A'),
                        listing.get('title', 'N/A'),
                        listing.get('bedrooms', 'N/A'),
                        listing.get('bathrooms', 'N/A'),
                        listing.get('sqft', 'N/A'),
                        listing.get('price', 'N/A'),
                        listing.get('full_address', 'N/A'),
                        listing.get('network', 'N/A')
                    )
                    self.tree.insert("", "end", values=values)
                
                self.lbl_count.config(text=f"{len(self.data)} listings")
            else:
                messagebox.showwarning("Warning", "JSON data is not a list of listings")
                self.lbl_count.config(text="Invalid data format")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {e}")
            self.lbl_count.config(text="Error loading data")
    
    def _on_select(self, event=None):
        """Show details when a listing is selected"""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get selected item index
        item = selection[0]
        idx = self.tree.index(item)
        
        if self.data and isinstance(self.data, list) and idx < len(self.data):
            listing = self.data[idx]
            
            # Format details
            details = json.dumps(listing, indent=2, ensure_ascii=False)
            
            self.txt_details.delete("1.0", "end")
            self.txt_details.insert("1.0", details)


def view_json(json_file: Path):
    """Open JSON viewer for a file"""
    try:
        viewer = JSONViewer(json_file)
        viewer.mainloop()
    except Exception as e:
        print(f"Error opening JSON viewer: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_path = Path(sys.argv[1])
        view_json(json_path)
    else:
        # Default to looking for extracted_listings.json
        script_dir = Path(__file__).resolve().parent
        captures_base = script_dir / "Captures"
        
        # Find most recent folder
        folders = sorted([f for f in captures_base.iterdir() 
                         if f.is_dir() and f.name.startswith('202')], reverse=True)
        
        if folders:
            json_file = folders[0] / "extracted_listings.json"
            if json_file.exists():
                view_json(json_file)
            else:
                print(f"No extracted_listings.json found in {folders[0]}")
        else:
            print("No capture folders found")
