"""
JSON Analyzer GUI - Visual JSON file analysis with detailed statistics
"""
import json
import os
from pathlib import Path
from collections import defaultdict
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

class JsonAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON Analyzer - Detailed Statistics")
        self.root.geometry("1200x800")
        self.root.configure(bg="#2C3E50")
        
        # Create UI
        self.create_ui()
        
    def create_ui(self):
        """Create the user interface"""
        # Top frame - File selection
        top_frame = tk.Frame(self.root, bg="#2C3E50")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(top_frame, text="📁 JSON File:", bg="#2C3E50", fg="#ECF0F1", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        
        self.filepath_var = tk.StringVar()
        tk.Entry(top_frame, textvariable=self.filepath_var, width=80, bg="#34495E", fg="#ECF0F1", insertbackground="#ECF0F1").pack(side="left", padx=5)
        
        tk.Button(top_frame, text="Browse...", command=self.browse_file, bg="#3498DB", fg="#fff", font=("Segoe UI", 9, "bold"), padx=15).pack(side="left", padx=5)
        tk.Button(top_frame, text="🔍 Analyze", command=self.analyze, bg="#2ECC71", fg="#fff", font=("Segoe UI", 9, "bold"), padx=15).pack(side="left", padx=5)
        
        # Info frame
        info_frame = tk.Frame(self.root, bg="#34495E")
        info_frame.pack(fill="x", padx=10, pady=5)
        
        self.info_label = tk.Label(info_frame, text="Select a JSON file to analyze", bg="#34495E", fg="#ECF0F1", font=("Segoe UI", 9), anchor="w")
        self.info_label.pack(fill="x", padx=10, pady=5)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Summary tab
        summary_frame = tk.Frame(self.notebook, bg="#2C3E50")
        self.notebook.add(summary_frame, text="📊 Summary")
        
        self.summary_text = scrolledtext.ScrolledText(summary_frame, bg="#34495E", fg="#ECF0F1", insertbackground="#ECF0F1", font=("Consolas", 9), wrap="word")
        self.summary_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Field Statistics tab
        fields_frame = tk.Frame(self.notebook, bg="#2C3E50")
        self.notebook.add(fields_frame, text="🔑 Field Statistics")
        
        self.fields_text = scrolledtext.ScrolledText(fields_frame, bg="#34495E", fg="#ECF0F1", insertbackground="#ECF0F1", font=("Consolas", 9), wrap="word")
        self.fields_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Entries tab
        entries_frame = tk.Frame(self.notebook, bg="#2C3E50")
        self.notebook.add(entries_frame, text="📋 All Entries")
        
        self.entries_text = scrolledtext.ScrolledText(entries_frame, bg="#34495E", fg="#ECF0F1", insertbackground="#ECF0F1", font=("Consolas", 9), wrap="word")
        self.entries_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Raw JSON tab
        raw_frame = tk.Frame(self.notebook, bg="#2C3E50")
        self.notebook.add(raw_frame, text="📄 Raw JSON")
        
        self.raw_text = scrolledtext.ScrolledText(raw_frame, bg="#34495E", fg="#ECF0F1", insertbackground="#ECF0F1", font=("Consolas", 9), wrap="word")
        self.raw_text.pack(fill="both", expand=True, padx=5, pady=5)
        
    def browse_file(self):
        """Open file dialog to select JSON file"""
        filepath = filedialog.askopenfilename(
            title="Select JSON file to analyze",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ],
            initialdir=os.path.dirname(__file__)
        )
        
        if filepath:
            self.filepath_var.set(filepath)
            
    def analyze(self):
        """Analyze the selected JSON file"""
        filepath = self.filepath_var.get()
        
        if not filepath:
            self.info_label.config(text="⚠️ Please select a JSON file first")
            return
        
        if not os.path.exists(filepath):
            self.info_label.config(text=f"❌ File not found: {filepath}")
            return
        
        try:
            # Clear all tabs
            self.summary_text.delete("1.0", "end")
            self.fields_text.delete("1.0", "end")
            self.entries_text.delete("1.0", "end")
            self.raw_text.delete("1.0", "end")
            
            self.info_label.config(text="⏳ Analyzing JSON file...")
            self.root.update()
            
            # Load JSON
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Show raw JSON
            self.raw_text.insert("1.0", json.dumps(data, indent=2, ensure_ascii=False))
            
            # Handle different JSON structures
            if isinstance(data, list):
                entries = data
            elif isinstance(data, dict):
                # Check common array keys
                if 'data' in data and isinstance(data['data'], list):
                    entries = data['data']
                elif 'listings' in data and isinstance(data['listings'], list):
                    entries = data['listings']
                elif 'results' in data and isinstance(data['results'], list):
                    entries = data['results']
                else:
                    # Treat dict as single entry
                    entries = [data]
            else:
                self.info_label.config(text=f"⚠️ Unexpected JSON type: {type(data)}")
                return
            
            total_entries = len(entries)
            
            if total_entries == 0:
                self.info_label.config(text="⚠️ No entries found in JSON file")
                return
            
            # Analyze fields
            field_stats = defaultdict(lambda: {
                'count': 0,
                'non_empty': 0,
                'unique_values': set(),
                'sample_values': [],
                'value_types': defaultdict(int)
            })
            
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                
                for field_name, field_value in entry.items():
                    stats = field_stats[field_name]
                    stats['count'] += 1
                    
                    # Track value type
                    value_type = type(field_value).__name__
                    stats['value_types'][value_type] += 1
                    
                    # Check if non-empty
                    if field_value is not None and field_value != "" and field_value != []:
                        stats['non_empty'] += 1
                    
                    # Track unique values (for small sets)
                    value_str = str(field_value)[:100]
                    if len(stats['unique_values']) < 100:
                        stats['unique_values'].add(value_str)
                    
                    # Collect sample values (first 5)
                    if len(stats['sample_values']) < 5:
                        stats['sample_values'].append(field_value)
            
            # Build Summary
            summary = []
            summary.append("="*80)
            summary.append(f"📄 File: {os.path.basename(filepath)}")
            summary.append("="*80)
            summary.append(f"📊 Total Entries: {total_entries}")
            summary.append(f"🔑 Total Fields: {len(field_stats)}")
            summary.append(f"📁 File Size: {os.path.getsize(filepath):,} bytes")
            summary.append("="*80)
            summary.append("")
            summary.append("🔑 FIELD LIST:")
            summary.append("")
            for idx, field_name in enumerate(sorted(field_stats.keys()), 1):
                stats = field_stats[field_name]
                summary.append(f"{idx:3d}. {field_name:40s} - {stats['count']:5d} occurrences ({stats['non_empty']:5d} non-empty)")
            
            self.summary_text.insert("1.0", "\n".join(summary))
            
            # Build Field Statistics
            fields = []
            fields.append("="*80)
            fields.append("🔍 DETAILED FIELD STATISTICS")
            fields.append("="*80)
            fields.append("")
            
            for field_name in sorted(field_stats.keys()):
                stats = field_stats[field_name]
                fields.append(f"📌 {field_name}")
                fields.append(f"{'─'*80}")
                fields.append(f"   Total occurrences: {stats['count']}/{total_entries} ({stats['count']*100//total_entries}%)")
                fields.append(f"   Non-empty values: {stats['non_empty']}/{stats['count']} ({stats['non_empty']*100//stats['count'] if stats['count'] > 0 else 0}%)")
                fields.append(f"   Unique values: {len(stats['unique_values'])}")
                
                # Show value types
                if stats['value_types']:
                    fields.append(f"   Value types:")
                    for vtype, count in sorted(stats['value_types'].items()):
                        fields.append(f"      - {vtype}: {count}")
                
                # Show sample values
                if stats['sample_values']:
                    fields.append(f"   Sample values:")
                    for i, sample in enumerate(stats['sample_values'], 1):
                        # Format based on type
                        if isinstance(sample, (list, dict)):
                            display_value = json.dumps(sample, ensure_ascii=False)[:100]
                        elif sample is None:
                            display_value = "NULL"
                        elif sample == "":
                            display_value = "(empty string)"
                        else:
                            display_value = str(sample)[:100]
                        
                        if len(str(sample)) > 100:
                            display_value += "..."
                        fields.append(f"      {i}. {display_value}")
                fields.append("")
            
            self.fields_text.insert("1.0", "\n".join(fields))
            
            # Build Entries view
            entries_view = []
            entries_view.append("="*80)
            entries_view.append(f"📋 ALL ENTRIES ({total_entries} total)")
            entries_view.append("="*80)
            entries_view.append("")
            
            for idx, entry in enumerate(entries, 1):
                if not isinstance(entry, dict):
                    entries_view.append(f"Entry #{idx}: {str(entry)[:200]}")
                    entries_view.append("")
                    continue
                
                entries_view.append(f"{'─'*80}")
                entries_view.append(f"Entry #{idx} of {total_entries}")
                entries_view.append(f"{'─'*80}")
                
                for field_name in sorted(entry.keys()):
                    field_value = entry[field_name]
                    
                    # Format value based on type
                    if isinstance(field_value, (list, dict)):
                        value_str = json.dumps(field_value, ensure_ascii=False)[:300]
                        if len(json.dumps(field_value, ensure_ascii=False)) > 300:
                            value_str += "..."
                    elif field_value is None:
                        value_str = "NULL"
                    elif field_value == "":
                        value_str = "(empty string)"
                    else:
                        value_str = str(field_value)[:300]
                        if len(str(field_value)) > 300:
                            value_str += "..."
                    
                    entries_view.append(f"  {field_name}: {value_str}")
                entries_view.append("")
            
            self.entries_text.insert("1.0", "\n".join(entries_view))
            
            # Update info
            self.info_label.config(text=f"✅ Analysis complete - {total_entries} entries, {len(field_stats)} fields found")
            
        except json.JSONDecodeError as e:
            self.info_label.config(text=f"❌ JSON parsing error: {e}")
        except Exception as e:
            self.info_label.config(text=f"❌ Error analyzing file: {e}")

def main():
    root = tk.Tk()
    app = JsonAnalyzerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
