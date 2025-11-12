#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

SCRIPT_DIR = Path(__file__).resolve().parent
MAPPINGS_PATH = SCRIPT_DIR / "field_mappings.json"

"""
Map Editor with value preview
Enhancements:
- Detects element-based mappings (index -> { field, path, ... }) and shows a value preview per row
- Lets you edit the saved CSS path and destination field per element
- Provides a Refresh Preview button that extracts values from the latest capture HTML
"""

# Try to import helpers from parser_core; fallback gracefully
APARTMENT_LISTING_FIELDS = []
extract_element_paths_from_first_row = None
extract_element_paths_from_nth_result = None
count_listings_in_html = None
resolve_value_by_path = None
current_capture_path = None
try:
    sys.path.insert(0, str(SCRIPT_DIR))
    from parser_core import (
        APARTMENT_LISTING_FIELDS as _ALF,  # type: ignore
        extract_element_paths_from_first_row as _extract_first,  # type: ignore
        extract_element_paths_from_nth_result as _extract_nth,  # type: ignore
        count_listings_in_html as _count_listings,  # type: ignore
    )
    # Internal names in parser_core use a leading underscore; import through wrapper lambdas
    from parser_core import _resolve_value_by_path as _resolve  # type: ignore
    from parser_core import _current_capture_path as _cur_cap  # type: ignore
    APARTMENT_LISTING_FIELDS = list(_ALF)
    extract_element_paths_from_first_row = _extract_first
    extract_element_paths_from_nth_result = _extract_nth
    count_listings_in_html = _count_listings
    resolve_value_by_path = _resolve
    current_capture_path = _cur_cap
except Exception:
    # Fallbacks - apartment_listings table columns
    APARTMENT_LISTING_FIELDS = [
        "id", "user_id", "active", "appfolio_id", "propertyType", "type", "unit_number", "deal", 
        "title", "Lease_Length", "Pool", "Gym", "MFTE", "Managed", "s_65", "s_55", 
        "Credit_Score", "Application_Fee", "Deposit_Amount", "name", "bedrooms", "bathrooms", 
        "sqft", "price", "price_change", "img_urls", "floorplan_url", "available", 
        "other_details", "details", "available_date", "time_created", "time_updated", "network", 
        "amenities", "Balcony", "Cats", "Dogs", "Parking", "parking_fee", "Text", 
        "description", "Building_Name", "Latitude", "Longitude", "suburb", "street", 
        "full_address", "city", "state", "country", "listing_website", "apply_now_link", 
        "details_processed", "phone_contact", "email_contact", "name_contact", 
        "google_addresses_id", "google_places_id"
    ]

# Utilities

def load_mappings() -> dict:
    if not MAPPINGS_PATH.exists():
        return {}
    try:
        with open(MAPPINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load field_mappings.json: {e}")
        return {}

def save_mappings(data: dict) -> bool:
    try:
        with open(MAPPINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save field_mappings.json: {e}")
        return False

def ensure_html_mappings_exist(mappings: dict, captures_dir: Path) -> bool:
    """
    Scan for all .html files in captures_dir and subfolders.
    For each file, if a mapping key does not exist, add it.
    Returns True if any new mapping was added.
    """
    added = False
    for root, dirs, files in os.walk(captures_dir):
        for fname in files:
            if fname.endswith('.html'):
                key = fname.rsplit('.', 1)[0]  # e.g., networks_1
                if key not in mappings:
                    mappings[key] = {}
                    added = True
    return added

class MapEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Field Mapping Editor")
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass
        self.geometry("940x520")
        
        self.mappings = load_mappings()
        self.current_key = None
        # Track UI mode: 'legacy' (src->dest) or 'elements' (index->{field,path})
        self.current_mode = "legacy"
        # Storage for element-mode widgets
        self._elem_rows = []
        # Cache source URL for current mapping
        self._source_url = None
        # Result navigation
        self._current_result_index = 0
        self._total_results = 1

        # For image preview
        self._img_label = None
        self._img_tk = None
        
        # For cancellation support
        self._cancel_operation = False
        self._running_threads = []

        self._build_ui()
        self._populate_keys()
        
        # Bind ESC key globally to cancel operations
        self.bind("<Escape>", self._on_escape_pressed)
        
        # Bind Left/Right arrow keys for result navigation
        self.bind("<Left>", lambda e: self._nav_prev_result())
        self.bind("<Right>", lambda e: self._nav_next_result())

    # UI
    def _build_ui(self):
        root = self
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(0, weight=1)
        root.rowconfigure(1, weight=0)

        # Left: keys list and controls
        left = tk.Frame(root)
        left.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        tk.Label(left, text="Mappings (job keys)").grid(row=0, column=0, sticky="w")
        self.list_keys = tk.Listbox(left, exportselection=False)
        self.list_keys.grid(row=1, column=0, sticky="nsew")
        self.list_keys.bind("<<ListboxSelect>>", self._on_select_key)

        btns = tk.Frame(left)
        btns.grid(row=2, column=0, sticky="ew", pady=(6,0))
        for i in range(5): btns.columnconfigure(i, weight=1)
        tk.Button(btns, text="New", command=self._new_map).grid(row=0, column=0, sticky="ew", padx=2)
        tk.Button(btns, text="Duplicate", command=self._dup_map).grid(row=0, column=1, sticky="ew", padx=2)
        tk.Button(btns, text="Rename", command=self._rename_map).grid(row=0, column=2, sticky="ew", padx=2)
        tk.Button(btns, text="Delete", command=self._delete_map).grid(row=0, column=3, sticky="ew", padx=2)
        tk.Button(btns, text="Save All", command=self._save_all).grid(row=0, column=4, sticky="ew", padx=2)


        # Right: mapping editor (dynamic area)
        right = tk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew", padx=(0,8), pady=8)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        hdr = tk.Frame(right)
        hdr.grid(row=0, column=0, sticky="ew")
        self.lbl_key = tk.Label(hdr, text="Key: -", font=("Segoe UI", 10, "bold"))
        self.lbl_key.pack(side="left")

        # Secondary header for element mode (includes source URL and navigation)
        self.hdr_info = tk.Frame(right)
        self.hdr_info.grid(row=1, column=0, sticky="ew")
        self.lbl_capture = tk.Label(self.hdr_info, text="Capture: -", fg="#7a7f87", anchor="w")
        self.lbl_capture.pack(side="left", fill="x", expand=True)
        self.lbl_source_url = tk.Label(self.hdr_info, text="", fg="#58A6FF", anchor="e", cursor="hand2", font=("Segoe UI", 8))
        self.lbl_source_url.pack(side="left", padx=(6,0))
        self.lbl_source_url.bind("<Button-1>", self._copy_source_url)
        # Right-side actions
        self.btn_refresh = tk.Button(self.hdr_info, text="Refresh Preview", command=self._refresh_element_preview)
        self.btn_refresh.pack(side="right")
        self.btn_generate = tk.Button(self.hdr_info, text="Generate from Capture", command=self._generate_from_capture)
        self.btn_generate.pack(side="right", padx=(0,6))

        # Result navigation controls (shown in element mode)
        self.nav_frame = tk.Frame(self.hdr_info)
        self.nav_frame.pack(side="right", padx=(0,6))
        self.btn_prev_result = tk.Button(self.nav_frame, text="◀ Prev", width=7, command=self._prev_result)
        self.btn_prev_result.pack(side="left", padx=2)
        self.lbl_result_counter = tk.Label(self.nav_frame, text="1/1", font=("Segoe UI", 9, "bold"))
        self.lbl_result_counter.pack(side="left", padx=4)
        self.btn_next_result = tk.Button(self.nav_frame, text="Next ▶", width=7, command=self._next_result)
        self.btn_next_result.pack(side="left", padx=2)

        # Mapping grid: Treeview with scrollbars
        container = tk.Frame(right)
        container.grid(row=2, column=0, sticky="nsew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(container, columns=("value", "field", "path", "tag"), show="headings", selectmode="browse")
        self.tree.heading("value", text="Value (preview)")
        self.tree.heading("field", text="Assign to Field")
        self.tree.heading("path", text="CSS Path")
        self.tree.heading("tag", text="Tag")
        self.tree.column("value", width=320, minwidth=120, stretch=True)
        self.tree.column("field", width=160, minwidth=80, stretch=True)
        self.tree.column("path", width=200, minwidth=80, stretch=True)
        self.tree.column("tag", width=80, minwidth=40, stretch=True)
        vsb = tk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = tk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        # Allow single-click to edit field with dropdown, double-click for path
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        # Add hover tooltip for value column
        self.tree.bind("<Motion>", self._on_tree_motion)
        self.tree.bind("<Leave>", self._on_tree_leave)
        self._tooltip = None
        self._tooltip_id = None
        # Inline editing combobox
        self._edit_combo = None
        self._editing_row = None
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Add image preview label below the mapping grid
        self._img_label = tk.Label(right, text="", borderwidth=2, relief="groove")
        self._img_label.grid(row=3, column=0, sticky="ew", pady=(8,0))

        # Add image preview label below the mapping grid
        self._img_label = tk.Label(right, text="", borderwidth=2, relief="groove")
        self._img_label.grid(row=3, column=0, sticky="ew", pady=(8,0))

        # Bottom actions
        bottom = tk.Frame(root)
        bottom.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0,8))
        bottom.columnconfigure(0, weight=1)
        tk.Button(bottom, text="Open JSON…", command=self._open_json_location).pack(side="left")
        tk.Button(bottom, text="Reload", command=self._reload_all).pack(side="left", padx=(6,0))
        tk.Button(bottom, text="Save Current", command=self._save_current).pack(side="right")
    tk.Button(bottom, text="Sync with queue_websites", command=self._sync_with_queued_websites).pack(side="right", padx=(0,6))

    # Data operations
    def _populate_keys(self):
        # Ensure every HTML file in Captures has a mapping key
        captures_dir = SCRIPT_DIR / "Captures"
        if ensure_html_mappings_exist(self.mappings, captures_dir):
            save_mappings(self.mappings)
        
        self.list_keys.delete(0, tk.END)
        for k in sorted(self.mappings.keys(), key=lambda s: str(s)):
            self.list_keys.insert(tk.END, k)

    def _split_value(self, value: str) -> str:
        """Split value if it contains ' / ' separator and return all parts joined with newlines"""
        if not value:
            return value
        if ' / ' in value:
            # Return all parts, each on a new line
            parts = [part.strip() for part in value.split(' / ') if part.strip()]
            return '\n'.join(parts)
        return value
    
    @staticmethod
    def _split_value_static(value: str) -> str:
        """Static version for thread-safe splitting - returns all parts joined with newlines"""
        if not value:
            return value
        if ' / ' in value:
            # Return all parts, each on a new line
            parts = [part.strip() for part in value.split(' / ') if part.strip()]
            return '\n'.join(parts)
        return value

    def _on_select_key(self, _evt=None):
        sel = self.list_keys.curselection()
        if not sel:
            return
        key = self.list_keys.get(sel[0])
        self._load_key(key)

    def _load_key(self, key: str):
        self.current_key = key
        self.lbl_key.config(text=f"Key: {key}")  # Will be updated by _update_navigation_and_key_label
        mapping = self.mappings.get(key, {}) or {}
        # Reset UI area
        self._clear_grid()
        # Detect mode
        if self._is_element_mapping(mapping):
            self.current_mode = "elements"
            # Load element grid in thread to avoid freezing
            self._run_in_thread(self._build_element_grid_async, mapping)
        else:
            self.current_mode = "legacy"
            self._build_legacy_grid(mapping)
        # Update headers visibility
        self._sync_header_controls()

    def _collect_current_mapping(self) -> dict:
        if self.current_mode == "elements":
            out = {}
            for iid in self.tree.get_children():
                try:
                    idx = int(iid)
                except Exception:
                    continue
                vals = self.tree.item(iid, "values")
                value = vals[0] if len(vals) > 0 else ""
                field = vals[1].strip() if len(vals) > 1 else ""
                path = vals[2].strip() if len(vals) > 2 else ""
                tag = vals[3].strip() if len(vals) > 3 else ""
                if field:
                    out[idx] = {"field": field, "path": path, "tag": tag, "original_text": value}
            return out
        # Legacy mapping (simple source->dest dict)
        # Read from tree if populated, otherwise return empty
        mapping = {}
        for iid in self.tree.get_children():
            vals = self.tree.item(iid, "values")
            if len(vals) >= 2:
                src = vals[0].strip() if vals[0] else ""
                dest = vals[1].strip() if vals[1] else ""
                if src and dest:
                    mapping[src] = dest
        return mapping

    def _save_current(self):
        if not self.current_key:
            messagebox.showinfo("Save Current", "No mapping selected.")
            return
        # Always save to the current key, no prompt
        self.mappings[self.current_key] = self._collect_current_mapping()
        if save_mappings(self.mappings):
            messagebox.showinfo("Saved", f"Saved mapping for '{self.current_key}'.")
            self._populate_keys()
            try:
                idx = list(sorted(self.mappings.keys(), key=lambda s: str(s))).index(self.current_key)
                self.list_keys.selection_clear(0, tk.END)
                self.list_keys.selection_set(idx)
            except Exception:
                pass

    def _save_all(self):
        if save_mappings(self.mappings):
            messagebox.showinfo("Saved", "All mappings saved.")

    def _new_map(self):
        key = self._prompt_text("New mapping key", "Enter new mapping key (e.g., 'queue_websites:123'):")
        if not key:
            return
        if key in self.mappings:
            messagebox.showerror("Exists", "A mapping with that key already exists.")
            return
        self.mappings[key] = {}
        self._populate_keys()
        # select it
        idx = list(sorted(self.mappings.keys())).index(key)
        self.list_keys.selection_clear(0, tk.END); self.list_keys.selection_set(idx)
        self._load_key(key)

    def _dup_map(self):
        if not self.current_key:
            messagebox.showinfo("Duplicate", "Select a mapping to duplicate.")
            return
        new_key = self._prompt_text("Duplicate mapping", f"Enter new key for copy of '{self.current_key}':")
        if not new_key:
            return
        if new_key in self.mappings:
            messagebox.showerror("Exists", "A mapping with that key already exists.")
            return
        self.mappings[new_key] = dict(self.mappings.get(self.current_key, {}))
        self._populate_keys()

    def _rename_map(self):
        if not self.current_key:
            messagebox.showinfo("Rename", "Select a mapping to rename.")
            return
        new_key = self._prompt_text("Rename mapping", f"Enter new key for '{self.current_key}':")
        if not new_key:
            return
        if new_key in self.mappings:
            messagebox.showerror("Exists", "A mapping with that key already exists.")
            return
        self.mappings[new_key] = self.mappings.pop(self.current_key)
        self.current_key = new_key
        self._populate_keys()
        self._load_key(new_key)
        # Save immediately after renaming to persist the change
        if save_mappings(self.mappings):
            messagebox.showinfo("Renamed", f"Mapping renamed to '{new_key}' and saved.")
        else:
            messagebox.showerror("Error", "Failed to save mappings after renaming.")

    def _delete_map(self):
        if not self.current_key:
            return
        if not messagebox.askyesno("Delete", f"Delete mapping '{self.current_key}'?"):
            return
        self.mappings.pop(self.current_key, None)
        save_mappings(self.mappings)
        self.current_key = None
        self._populate_keys()
        self._load_key("")

    def _reload_all(self):
        self.mappings = load_mappings()
        self._populate_keys()
        self.current_key = None
        self._load_key("")

    def _open_json_location(self):
        try:
            os.startfile(str(SCRIPT_DIR))  # Windows open folder
        except Exception:
            filedialog.askopenfilename(initialdir=str(SCRIPT_DIR), title="Open folder…")

    def _prompt_text(self, title: str, prompt: str):
        win = tk.Toplevel(self)
        win.transient(self)
        win.grab_set()
        win.title(title)
        tk.Label(win, text=prompt).pack(padx=10, pady=(10,4))
        entry = tk.Entry(win, width=50)
        entry.pack(padx=10, pady=4)
        entry.focus_set()
        ans = {"value": None}
        def ok():
            ans["value"] = entry.get().strip()
            win.destroy()
        def cancel():
            win.destroy()
        btns = tk.Frame(win); btns.pack(pady=(6,10))
        tk.Button(btns, text="OK", width=10, command=ok).pack(side="left", padx=4)
        tk.Button(btns, text="Cancel", width=10, command=cancel).pack(side="left", padx=4)
        self.wait_window(win)
        return ans["value"]

    # ---- Helpers for mode management ----
    def _is_element_mapping(self, mapping: dict) -> bool:
        if not isinstance(mapping, dict):
            return False
        # Empty mappings are treated as element-based (ready for generation)
        if not mapping:
            return True
        # Any value is a dict with 'field' key OR key is int-like
        for k, v in mapping.items():
            if isinstance(v, dict) and "field" in v:
                return True
            if isinstance(k, int):
                return True
            if isinstance(k, str) and k.isdigit():
                return True
        return False

    def _clear_grid(self):
        # Clear tree rows
        try:
            for iid in list(self.tree.get_children()):
                self.tree.delete(iid)
        except Exception:
            pass
        self._elem_rows.clear()

    def _sync_header_controls(self):
        # Toggle controls depending on mode
        if self.current_mode == "elements":
            # Show capture path info
            cap = None
            try:
                if current_capture_path:
                    cap = current_capture_path()
            except Exception:
                cap = None
            self.lbl_capture.config(text=f"Capture: {str(cap) if cap else '-'}")
            # Show source URL if available
            if self._source_url:
                url_display = self._source_url[:60] + "..." if len(self._source_url) > 60 else self._source_url
                self.lbl_source_url.config(text=f"🔗 {url_display}")
            else:
                self.lbl_source_url.config(text="")
            self.hdr_info.grid()  # show
        else:
            # Legacy mode
            self.hdr_info.grid_remove()

    def _copy_source_url(self, event=None):
        if self._source_url:
            try:
                self.clipboard_clear()
                self.clipboard_append(self._source_url)
                self.update()
            except Exception:
                pass

    def _prev_result(self):
        """Navigate to the previous result/listing"""
        if self.current_mode != "elements":
            return
        if self._current_result_index > 0:
            self._current_result_index -= 1
            self._update_result_display()

    def _next_result(self):
        """Navigate to the next result/listing"""
        if self.current_mode != "elements":
            return
        if self._current_result_index < self._total_results - 1:
            self._current_result_index += 1
            self._update_result_display()

    def _update_result_display(self):
        """Update the tree to show values from the current result index"""
        if self.current_mode != "elements":
            return
        
        # Update counter label
        self.lbl_result_counter.config(text=f"{self._current_result_index + 1}/{self._total_results}")
        
        # Update button states
        self.btn_prev_result.config(state="disabled" if self._current_result_index == 0 else "normal")
        self.btn_next_result.config(state="disabled" if self._current_result_index >= self._total_results - 1 else "normal")
        
        # Extract elements in background to avoid freezing
        self._run_in_thread(self._update_result_display_async)
    
    def _update_result_display_async(self):
        """Background thread for updating result display"""
        # Extract elements from the current result
        elements = []
        try:
            if extract_element_paths_from_nth_result and current_capture_path:
                cap = current_capture_path()
                if cap and Path(cap).exists():
                    html = Path(cap).read_text(encoding="utf-8", errors="ignore")
                    if self._check_cancel():
                        return
                    elements = extract_element_paths_from_nth_result(html, self._current_result_index) or []
        except Exception as e:
            print(f"Error extracting elements: {e}")
            elements = []
        
        if self._check_cancel():
            return
        
        # Update UI on main thread
        def update_tree():
            try:
                for iid in self.tree.get_children():
                    if self._check_cancel():
                        return
                    try:
                        idx = int(iid)
                    except Exception:
                        continue
                    vals = list(self.tree.item(iid, "values"))
                    if len(vals) < 4:
                        continue
                    
                    # Try to get value from elements at current result index
                    value = ""
                    elem = next((e for e in elements if e.get('index') == idx), None)
                    if elem:
                        raw_value = elem.get('text') or elem.get('href') or elem.get('src') or ""
                        value = MapEditor._split_value_static(raw_value)
                    
                    # Update the tree row with new value
                    vals[0] = value
                    self.tree.item(iid, values=vals)
            except Exception as e:
                print(f"Error in update_tree: {e}")
        
        self.after(0, update_tree)

    def _build_legacy_grid(self, mapping: dict):
        # Build rows for legacy mapping using Treeview
        # Configure tree for simple two-column view (source -> destination)
        try:
            for iid in list(self.tree.get_children()):
                self.tree.delete(iid)
        except Exception:
            pass
        
        # Reconfigure tree columns for legacy mode (just source and dest)
        self.tree.configure(columns=("source", "destination"))
        self.tree.heading("source", text="Source Field")
        self.tree.heading("destination", text="Destination Field")
        self.tree.column("source", width=300, minwidth=150, stretch=True)
        self.tree.column("destination", width=300, minwidth=150, stretch=True)
        
        # Populate rows
        for idx, (src, dest) in enumerate(mapping.items()):
            self.tree.insert("", "end", iid=str(idx), values=(src, dest))

    def _build_element_grid(self, mapping: dict):
        # Populate the Treeview with the mapping rows
        try:
            for iid in list(self.tree.get_children()):
                self.tree.delete(iid)
        except Exception:
            pass
        
        # Reconfigure tree for element mode (four columns)
        self.tree.configure(columns=("value", "field", "path", "tag"))
        self.tree.heading("value", text="Value (preview)")
        self.tree.heading("field", text="Assign to Field")
        self.tree.heading("path", text="CSS Path")
        self.tree.heading("tag", text="Tag")
        self.tree.column("value", width=320, minwidth=120, stretch=True)
        self.tree.column("field", width=160, minwidth=80, stretch=True)
        self.tree.column("path", width=200, minwidth=80, stretch=True)
        self.tree.column("tag", width=80, minwidth=40, stretch=True)
        
        # Count total results in the capture and reset navigation
        self._current_result_index = 0
        self._total_results = 1
        self.after(0, self._update_navigation_and_key_label)
        
        # Just populate from mapping without loading HTML (async will handle HTML)
        def parse_idx(k):
            try:
                return int(k)
            except Exception:
                return 0

        for key in sorted(mapping.keys(), key=parse_idx):
            if self._check_cancel():
                return
            info = mapping.get(key) or {}
            try:
                idx = int(key)
            except Exception:
                continue
            field = info.get("field") if isinstance(info, dict) else ""
            path = info.get("path") if isinstance(info, dict) else ""
            tag = info.get("tag") if isinstance(info, dict) else ""
            original_text = info.get("original_text") if isinstance(info, dict) else ""
            # Insert into tree with empty value initially
            self.tree.insert("", "end", iid=str(idx), values=("", field, path, tag))
            self._elem_rows.append({"index": idx, "field": field, "path": path, "tag": tag, "original_text": original_text})

        # Bind selection event for image preview
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _build_element_grid_async(self, mapping: dict):
        """Build element grid in background thread with HTML parsing"""
        # First, update UI with basic structure (no HTML parsing yet)
        self.after(0, lambda: self._build_element_grid(mapping))
        
        if self._check_cancel():
            return
        
        # Now load HTML in background
        try:
            if count_listings_in_html and current_capture_path:
                cap = current_capture_path()
                if cap and Path(cap).exists():
                    html = Path(cap).read_text(encoding="utf-8", errors="ignore")
                    if self._check_cancel():
                        return
                    total = count_listings_in_html(html)
                    def set_total_and_update():
                        self._total_results = total
                        self._update_navigation_and_key_label()
                    self.after(0, set_total_and_update)
        except Exception:
            pass
        
        if self._check_cancel():
            return
        
        # Extract elements and update values
        elements = []
        try:
            if extract_element_paths_from_nth_result and current_capture_path:
                cap = current_capture_path()
                if cap and Path(cap).exists():
                    html = Path(cap).read_text(encoding="utf-8", errors="ignore")
                    if self._check_cancel():
                        return
                    elements = extract_element_paths_from_nth_result(html, self._current_result_index) or []
        except Exception:
            elements = []
        
        if self._check_cancel():
            return
        
        # Update tree with values
        def update_tree_values():
            try:
                for iid in self.tree.get_children():
                    if self._check_cancel():
                        return
                    try:
                        idx = int(iid)
                        elem = next((e for e in elements if e.get('index') == idx), None)
                        if elem:
                            raw_value = elem.get('text') or elem.get('href') or elem.get('src') or ""
                            value = MapEditor._split_value_static(raw_value)
                            vals = list(self.tree.item(iid, "values"))
                            vals[0] = value
                            self.tree.item(iid, values=vals)
                    except Exception as e:
                        print(f"Error updating tree item {iid}: {e}")
                # Update navigation controls
                self.lbl_result_counter.config(text=f"{self._current_result_index + 1}/{self._total_results}")
                self.btn_prev_result.config(state="disabled" if self._current_result_index == 0 else "normal")
                self.btn_next_result.config(state="disabled" if self._current_result_index >= self._total_results - 1 else "normal")
            except Exception as e:
                print(f"Error in update_tree_values: {e}")
        
        self.after(0, update_tree_values)

    def _on_tree_select(self, event=None):
        # Show image preview if the selected row is an image
        sel = self.tree.selection()
        if not sel:
            self._img_label.config(image='', text='')
            self._img_tk = None
            return
        iid = sel[0]
        vals = self.tree.item(iid, "values")
        value = vals[0] if len(vals) > 0 else ""
        # Try to detect if value is an image file or URL
        if isinstance(value, str) and (value.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')) or value.startswith('http')):
            # Try to load image (requires Pillow)
            try:
                from PIL import Image, ImageTk
                import io, requests
                img = None
                try:
                    if value.startswith('http'):
                        resp = requests.get(value, timeout=5)
                        img = Image.open(io.BytesIO(resp.content))
                    else:
                        img = Image.open(value)
                    img.thumbnail((220, 220))
                    self._img_tk = ImageTk.PhotoImage(img)
                    self._img_label.config(image=self._img_tk, text='')
                except Exception as e:
                    self._img_label.config(image='', text=f'[Image load failed: {e}]')
                    self._img_tk = None
            except ImportError:
                self._img_label.config(image='', text='[Install Pillow to view images: pip install pillow]')
                self._img_tk = None
        else:
            self._img_label.config(image='', text='')
            self._img_tk = None
    # --- Threading helpers to prevent UI freeze ---
    def _run_in_thread(self, func, *args, **kwargs):
        import threading
        def wrapper():
            try:
                func(*args, **kwargs)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Thread Error", f"Background operation failed: {e}"))
        thread = threading.Thread(target=wrapper, daemon=True)
        self._running_threads.append(thread)
        thread.start()
    
    def _on_escape_pressed(self, event=None):
        """Cancel all running operations and hide inline combo"""
        self._cancel_operation = True
        self._hide_edit_combo()
        self.title("Field Mapping Editor - Cancelling...")
        # Reset cancel flag after a brief delay
        self.after(500, self._reset_cancel_flag)
    
    def _reset_cancel_flag(self):
        self._cancel_operation = False
        self.title("Field Mapping Editor")
    
    def _check_cancel(self):
        """Check if operation should be cancelled"""
        return self._cancel_operation

    def _generate_from_capture(self):
        # Ask if user wants AI-powered mapping
        use_ai = messagebox.askyesno(
            "Generate from Capture",
            "Use AI to automatically map fields?\n\n"
            "YES: ChatGPT will analyze the HTML and suggest field mappings\n"
            "NO: Manual mapping (extract elements only)",
            default='yes'
        )
        # Run the actual generation in a thread
        self._run_in_thread(self._generate_from_capture_thread, use_ai)

    def _generate_from_capture_thread(self, use_ai=False):
        # Original _generate_from_capture logic moved here (see previous implementation)
        try:
            if not (extract_element_paths_from_first_row and current_capture_path):
                self.after(0, lambda: messagebox.showerror("Unavailable", "Parser helpers are unavailable. Can't generate."))
                return
            cap = current_capture_path()
            if not (cap and Path(cap).exists()):
                self.after(0, lambda: messagebox.showerror("No Capture", "No capture HTML found. Run the poller once to create network_6.html."))
                return
            html = Path(cap).read_text(encoding="utf-8", errors="ignore")
            # Extract source URL from the HTML comment if present
            source_url = None
            import re
            m = re.search(r'<!-- saved .+ from (.+?) -->', html)
            if m:
                source_url = m.group(1).strip()
            elements = extract_element_paths_from_first_row(html) or []
            if not elements:
                self.after(0, lambda: messagebox.showwarning("No Elements", "Couldn't detect a first-row to extract elements from."))
                return
            if not self.current_key:
                capture_name = Path(cap).stem
                temp_key = f"temp_{capture_name}"
                self.current_key = temp_key
                if self.current_key not in self.mappings:
                    self.mappings[self.current_key] = {}
                self.after(0, self._populate_keys)
                try:
                    idx = list(sorted(self.mappings.keys(), key=lambda s: str(s))).index(self.current_key)
                    self.after(0, lambda: self.list_keys.selection_clear(0, tk.END))
                    self.after(0, lambda: self.list_keys.selection_set(idx))
                except Exception:
                    pass
            existing_map = self.mappings.get(self.current_key, {})
            assigned = []
            unassigned = {}
            for idx, m in existing_map.items():
                if m.get("field"):
                    assigned.append((idx, m))
            for elem in elements:
                idx = elem.get("index")
                if not idx:
                    continue
                idx = str(idx)
                if idx in existing_map and existing_map[idx].get("field"):
                    continue
                unassigned[idx] = {
                    "field": "",
                    "path": elem.get("path") or "",
                    "tag": elem.get("tag") or "",
                    "original_text": elem.get("text") or "",
                }
            
            # AI-powered field mapping if requested
            if use_ai and unassigned:
                try:
                    ai_mappings = self._ai_map_fields(html, unassigned)
                    if ai_mappings:
                        for idx, field in ai_mappings.items():
                            if idx in unassigned and field:
                                unassigned[idx]["field"] = field
                except Exception as e:
                    print(f"AI mapping failed: {e}")
                    self.after(0, lambda: messagebox.showwarning("AI Mapping Failed", f"Could not complete AI mapping: {e}\nFalling back to manual mapping."))
            
            new_map = {}
            for idx, m in assigned:
                new_map[idx] = m
            for idx in unassigned:
                new_map[idx] = unassigned[idx]
            self.mappings[self.current_key] = new_map
            self._source_url = source_url
            self.after(0, lambda: self._load_key(self.current_key))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to generate from capture: {e}"))

    def _ai_map_fields(self, html: str, unassigned: dict) -> dict:
        """Use OpenAI to automatically map HTML elements to database fields"""
        try:
            import openai
            import os
            
            # Get API key from environment
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                raise Exception("OPENAI_API_KEY environment variable not set")
            
            # Prepare element data for AI
            elements_info = []
            for idx, elem in unassigned.items():
                elements_info.append({
                    "index": idx,
                    "value": elem.get("original_text", "")[:200],  # Limit text length
                    "path": elem.get("path", ""),
                    "tag": elem.get("tag", "")
                })
            
            # Create prompt for AI
            prompt = f"""You are analyzing an apartment listing HTML page to map extracted elements to database fields.

Available database fields:
{', '.join(APARTMENT_LISTING_FIELDS)}

Extracted elements from HTML:
{json.dumps(elements_info, indent=2)}

For each element, determine the most appropriate database field based on its value, CSS path, and HTML tag.
Return a JSON object mapping element index to field name. Only include mappings you're confident about.
If an element doesn't match any field well, omit it.

Example response format:
{{
  "1": "listing_website",
  "2": "img_urls",
  "4": "price",
  "10": "sqft"
}}

Return ONLY the JSON object, no other text."""

            # Call OpenAI API
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing HTML structure and mapping data fields for apartment listings."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            mappings = json.loads(response_text)
            return mappings
            
        except Exception as e:
            print(f"AI mapping error: {e}")
            raise

    def _on_tree_click(self, event):
        """Handle single-click to show inline dropdown for field column"""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            self._hide_edit_combo()
            return
        
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row or not col:
            self._hide_edit_combo()
            return
        
        col_idx = int(col.replace('#','')) - 1
        
        # Only show inline combobox for field column (index 1) in element mode
        if col_idx == 1 and self.current_mode == "elements":
            self._show_inline_combo(row, col, event)
        else:
            self._hide_edit_combo()

    def _show_inline_combo(self, row, col, event):
        """Show an inline combobox for editing the field assignment"""
        # Hide any existing combo
        self._hide_edit_combo()
        
        # Get current value
        vals = list(self.tree.item(row, "values"))
        current_value = vals[1].strip() if len(vals) > 1 and vals[1] else ""
        
        # Get list of already-assigned fields (excluding current row)
        assigned_fields = set()
        for iid in self.tree.get_children():
            if iid == row:
                continue
            item_vals = self.tree.item(iid, "values")
            if len(item_vals) > 1 and item_vals[1]:
                field = item_vals[1].strip()
                if field:
                    assigned_fields.add(field)
        
        # Filter available fields
        available_fields = [""] + [f for f in APARTMENT_LISTING_FIELDS if f not in assigned_fields]
        if current_value and current_value not in available_fields:
            available_fields.insert(1, current_value)
        
        # Get cell bounding box
        bbox = self.tree.bbox(row, col)
        if not bbox:
            return

        x, y, width, height = bbox

        # Create combobox (allow typing for filtering)
        self._edit_combo = ttk.Combobox(self.tree, values=available_fields, state="normal", height=15)
        self._edit_combo.set(current_value)
        self._editing_row = row
        self._edit_combo.place(x=x, y=y, width=width, height=height)
        
        # Bind events BEFORE setting focus
        self._edit_combo.bind("<<ComboboxSelected>>", lambda e: self._save_inline_combo())
        self._edit_combo.bind("<FocusOut>", lambda e: self._hide_edit_combo())
        self._edit_combo.bind("<Escape>", lambda e: self._hide_edit_combo())
        self._edit_combo.bind("<Return>", lambda e: self._save_inline_combo())
        
        # Set focus and select all text for easy typing
        self._edit_combo.focus_set()
        self._edit_combo.selection_range(0, 'end')
        self._edit_combo.icursor('end')

    def _save_inline_combo(self):
        """Save the value from inline combobox to tree"""
        if not self._edit_combo or not self._editing_row:
            return
        
        new_value = self._edit_combo.get().strip()
        vals = list(self.tree.item(self._editing_row, "values"))
        if len(vals) > 1:
            vals[1] = new_value
            self.tree.item(self._editing_row, values=vals)
        
        self._hide_edit_combo()

    def _hide_edit_combo(self):
        """Hide and destroy the inline combobox"""
        if self._edit_combo:
            try:
                self._edit_combo.destroy()
            except Exception:
                pass
            self._edit_combo = None
            self._editing_row = None

    def _on_tree_double_click(self, event):
        # Identify row and column
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row or not col:
            return
        col_idx = int(col.replace('#','')) - 1
        vals = list(self.tree.item(row, "values"))
        if col_idx == 1:
            # Field column - single click now handles this with inline dropdown
            return
        elif col_idx == 2:
            # Edit CSS path
            newp = self._prompt_text("Edit CSS Path", "Enter CSS selector or table path (e.g., tr[1]/td[2]):")
            if newp is None:
                return
            vals[2] = newp
            self.tree.item(row, values=vals)
        else:
            # do not edit other columns inline
            return

    def _prompt_field_dropdown(self, title: str, current_value: str, editing_row: str):
        """Show a dropdown dialog for field selection, filtering out already-assigned fields"""
        # Get list of already-assigned fields (excluding the current row)
        assigned_fields = set()
        for iid in self.tree.get_children():
            if iid == editing_row:
                continue  # Skip the row we're editing
            vals = self.tree.item(iid, "values")
            if len(vals) > 1 and vals[1]:
                field = vals[1].strip()
                if field:
                    assigned_fields.add(field)
        
        # Filter available fields
        available_fields = [""] + [f for f in APARTMENT_LISTING_FIELDS if f not in assigned_fields]
        # If current value is assigned, add it back to the list
        if current_value and current_value not in available_fields:
            available_fields.insert(1, current_value)
        
        # Create dialog
        win = tk.Toplevel(self)
        win.transient(self)
        win.grab_set()
        win.title(title)
        win.geometry("400x150")
        
        tk.Label(win, text="Select field to assign this value to:").pack(padx=10, pady=(10,4))
        
        combo_var = tk.StringVar(value=current_value)
        combo = ttk.Combobox(win, textvariable=combo_var, values=available_fields, state="readonly", width=50)
        combo.pack(padx=10, pady=4)
        combo.focus_set()
        
        # Show info about filtered fields
        if assigned_fields:
            info_text = f"({len(assigned_fields)} field(s) already assigned and hidden)"
            tk.Label(win, text=info_text, fg="#666", font=("Segoe UI", 8)).pack(pady=2)
        
        ans = {"value": None}
        def ok():
            ans["value"] = combo_var.get().strip()
            win.destroy()
        def cancel():
            win.destroy()
        
        btns = tk.Frame(win)
        btns.pack(pady=(10,10))
        tk.Button(btns, text="OK", width=10, command=ok).pack(side="left", padx=4)
        tk.Button(btns, text="Cancel", width=10, command=cancel).pack(side="left", padx=4)
        tk.Button(btns, text="Clear", width=10, command=lambda: combo_var.set("")).pack(side="left", padx=4)
        
        self.wait_window(win)
        return ans["value"]

    def _on_tree_motion(self, event):
        """Show tooltip on hover over value column"""
        # Cancel any pending tooltip
        if self._tooltip_id:
            self.after_cancel(self._tooltip_id)
            self._tooltip_id = None
        # Identify what's under the cursor
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            self._hide_tooltip()
            return
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row or not col:
            self._hide_tooltip()
            return
        col_idx = int(col.replace('#','')) - 1
        # Only show tooltip for value column (index 0)
        if col_idx != 0 or self.current_mode != "elements":
            self._hide_tooltip()
            return
        # Schedule tooltip after a short delay, and check if mouse is still over the same cell
        def show_if_still_here():
            # Only show if mouse is still over the same cell
            x, y = self.tree.winfo_pointerxy()
            widget = self.tree.winfo_containing(x, y)
            if widget is self.tree:
                region_now = self.tree.identify("region", x - self.tree.winfo_rootx(), y - self.tree.winfo_rooty())
                row_now = self.tree.identify_row(y - self.tree.winfo_rooty())
                col_now = self.tree.identify_column(x - self.tree.winfo_rootx())
                if region_now == "cell" and row_now == row and col_now == col:
                    self._show_tooltip(event, row)
        self._tooltip_id = self.after(500, show_if_still_here)

    def _on_tree_leave(self, event):
        """Hide tooltip when mouse leaves the tree"""
        if self._tooltip_id:
            self.after_cancel(self._tooltip_id)
            self._tooltip_id = None
        self._hide_tooltip()

    def _hide_tooltip(self):
        """Hide the tooltip window"""
        if self._tooltip:
            try:
                self._tooltip.destroy()
            except Exception:
                pass
            self._tooltip = None

    def _show_tooltip(self, event, row):
        """Show tooltip with aggregated values from all results"""
        if self.current_mode != "elements":
            return
        
        try:
            idx = int(row)
        except Exception:
            return
        
        # Get current value
        vals = self.tree.item(row, "values")
        current_value = vals[0] if len(vals) > 0 else ""
        
        # Collect values from all results for this element index
        all_values = []
        try:
            if extract_element_paths_from_nth_result and current_capture_path:
                cap = current_capture_path()
                if cap and Path(cap).exists():
                    html = Path(cap).read_text(encoding="utf-8", errors="ignore")
                    
                    for result_idx in range(self._total_results):
                        elements = extract_element_paths_from_nth_result(html, result_idx) or []
                        elem = next((e for e in elements if e.get('index') == idx), None)
                        if elem:
                            raw_value = elem.get('text') or elem.get('href') or elem.get('src') or "(empty)"
                            value = MapEditor._split_value_static(raw_value)
                            all_values.append(f"Result {result_idx + 1}: {value}")
                        else:
                            all_values.append(f"Result {result_idx + 1}: (not found)")
        except Exception as e:
            all_values = [f"Error: {e}"]
        
        if not all_values:
            return
        
        # Create tooltip window
        self._hide_tooltip()  # Hide any existing tooltip
        self._tooltip = tk.Toplevel(self)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_attributes("-topmost", True)
        
        # Position tooltip near cursor
        x = event.x_root + 10
        y = event.y_root + 10
        self._tooltip.wm_geometry(f"+{x}+{y}")
        
        # Create tooltip content
        frame = tk.Frame(self._tooltip, background="#FFFFE0", borderwidth=1, relief="solid")
        frame.pack()
        
        # Header with element ID
        header_text = f"Element #{idx} - Values across all results:"
        header = tk.Label(frame, text=header_text, background="#FFFFE0", 
                         font=("Segoe UI", 9, "bold"), anchor="w", justify="left")
        header.pack(padx=6, pady=(4,2), fill="x")
        
        # Separator
        sep = tk.Frame(frame, height=1, background="#999")
        sep.pack(fill="x", padx=6, pady=2)
        
        # Show all values (limit to first 10 results to avoid huge tooltips)
        display_values = all_values[:10]
        for val_line in display_values:
            # Highlight current result
            is_current = val_line.startswith(f"Result {self._current_result_index + 1}:")
            font_style = ("Segoe UI", 8, "bold") if is_current else ("Segoe UI", 8)
            bg_color = "#FFFFCC" if is_current else "#FFFFE0"
            
            lbl = tk.Label(frame, text=val_line, background=bg_color, 
                          font=font_style, anchor="w", justify="left")
            lbl.pack(padx=6, pady=1, fill="x")
        
        if len(all_values) > 10:
            more = tk.Label(frame, text=f"... and {len(all_values) - 10} more", 
                           background="#FFFFE0", font=("Segoe UI", 8, "italic"), 
                           anchor="w", justify="left")
            more.pack(padx=6, pady=(1,4))

    def _refresh_element_preview(self):
        if self.current_mode != "elements":
            return
        # Run in background to avoid freezing
        self._run_in_thread(self._refresh_element_preview_async)
    
    def _refresh_element_preview_async(self):
        """Background thread for refreshing element preview"""
        # Recompute previews for all rows from the current result index
        elements = []
        try:
            if extract_element_paths_from_nth_result and current_capture_path:
                cap = current_capture_path()
                if cap and Path(cap).exists():
                    html = Path(cap).read_text(encoding="utf-8", errors="ignore")
                    if self._check_cancel():
                        return
                    elements = extract_element_paths_from_nth_result(html, self._current_result_index) or []
        except Exception:
            elements = []
        
        if self._check_cancel():
            return
        
        # Update tree values on main thread
        def update_tree():
            try:
                for iid in self.tree.get_children():
                    if self._check_cancel():
                        return
                    try:
                        idx = int(iid)
                    except Exception:
                        continue
                    vals = list(self.tree.item(iid, "values"))
                    if len(vals) < 4:
                        continue
                    
                    # Try to get updated value from elements
                    value = ""
                    elem = next((e for e in elements if e.get('index') == idx), None)
                    if elem:
                        raw_value = elem.get('text') or elem.get('href') or elem.get('src') or ""
                        value = MapEditor._split_value_static(raw_value)
                    
                    # Update the tree row with new value
                    vals[0] = value
                    self.tree.item(iid, values=vals)
            except Exception as e:
                print(f"Error in update_tree (refresh): {e}")
        
        self.after(0, update_tree)

    def _sync_with_queued_websites(self):
        """Ensure there is a mapping for every row in queue_websites table."""
        import mysql.connector as mysql
        try:
            from config_utils import CFG
            conn = mysql.connect(
                host=CFG["MYSQL_HOST"],
                port=CFG["MYSQL_PORT"],
                user=CFG["MYSQL_USER"],
                password=CFG["MYSQL_PASSWORD"],
                database=CFG["MYSQL_DB"]
            )
            cur = conn.cursor()
            cur.execute("SELECT id FROM queue_websites ORDER BY id ASC")
            ids = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("DB Error", f"Failed to fetch queue_websites: {e}")
            return
        # Add missing mappings
        added = 0
        for job_id in ids:
            key = f"queue_websites:{job_id}"
            if key not in self.mappings:
                self.mappings[key] = {}
                added += 1
        if added:
            save_mappings(self.mappings)
            self._populate_keys()
            messagebox.showinfo("Sync Complete", f"Added {added} blank mappings for queue_websites.")
        else:
            messagebox.showinfo("Sync Complete", "All queue_websites already have mappings.")

    def _update_navigation_and_key_label(self):
        # Update navigation controls and Key label
        self.lbl_result_counter.config(text=f"{self._current_result_index + 1}/{self._total_results}")
        self.btn_prev_result.config(state="disabled" if self._current_result_index == 0 else "normal")
        self.btn_next_result.config(state="disabled" if self._current_result_index >= self._total_results - 1 else "normal")
        # Show count in Key label if in element mode and more than 1 result
        if getattr(self, 'current_mode', None) == "elements" and getattr(self, '_total_results', 1) > 1:
            self.lbl_key.config(text=f"Key: {self.current_key}  ({self._total_results} listings)")
        else:
            self.lbl_key.config(text=f"Key: {self.current_key}")


if __name__ == "__main__":
    import traceback
    try:
        app = MapEditor()
        app.mainloop()
    except Exception as e:
        print(f"Fatal error in MapEditor: {e}")
        traceback.print_exc()
        try:
            messagebox.showerror("Fatal Error", f"Application crashed:\n{e}\n\nSee console for details.")
        except:
            pass
