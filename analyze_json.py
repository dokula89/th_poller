"""
JSON Analyzer - Summarize JSON files with field statistics
"""
import json
import os
from pathlib import Path
from collections import defaultdict
from tkinter import Tk, filedialog

def analyze_json_file(filepath):
    """Analyze a JSON file and return comprehensive statistics"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
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
            print(f"⚠️ Unexpected JSON type: {type(data)}")
            return None
        
        total_entries = len(entries)
        
        if total_entries == 0:
            print("\n" + "="*80)
            print(f"📄 File: {os.path.basename(filepath)}")
            print("="*80)
            print("⚠️ No entries found in JSON file")
            return None
        
        # Analyze fields
        field_stats = defaultdict(lambda: {
            'count': 0,
            'non_empty': 0,
            'unique_values': set(),
            'sample_values': []
        })
        
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            
            for field_name, field_value in entry.items():
                stats = field_stats[field_name]
                stats['count'] += 1
                
                # Check if non-empty
                if field_value is not None and field_value != "" and field_value != []:
                    stats['non_empty'] += 1
                
                # Track unique values (for small sets)
                value_str = str(field_value)[:100]  # Limit length
                if len(stats['unique_values']) < 50:  # Only track first 50 unique
                    stats['unique_values'].add(value_str)
                
                # Collect sample values (first 3)
                if len(stats['sample_values']) < 3:
                    stats['sample_values'].append(value_str)
        
        # Print Summary
        print("\n" + "="*80)
        print(f"📄 File: {os.path.basename(filepath)}")
        print("="*80)
        print(f"📊 Total Entries: {total_entries}")
        print(f"🔑 Total Fields: {len(field_stats)}")
        print("="*80)
        
        # Print field statistics
        print("\n🔍 FIELD STATISTICS:\n")
        
        for field_name in sorted(field_stats.keys()):
            stats = field_stats[field_name]
            print(f"📌 {field_name}:")
            print(f"   ├─ Total occurrences: {stats['count']}/{total_entries} ({stats['count']*100//total_entries}%)")
            print(f"   ├─ Non-empty values: {stats['non_empty']}/{stats['count']} ({stats['non_empty']*100//stats['count'] if stats['count'] > 0 else 0}%)")
            print(f"   ├─ Unique values: {len(stats['unique_values'])}")
            
            if stats['sample_values']:
                print(f"   └─ Sample values:")
                for i, sample in enumerate(stats['sample_values'], 1):
                    # Truncate long values
                    display_value = sample[:60] + "..." if len(sample) > 60 else sample
                    print(f"      {i}. {display_value}")
            print()
        
        # Print entry details
        print("="*80)
        print(f"\n📋 INDIVIDUAL ENTRIES (showing all {total_entries} entries):\n")
        
        for idx, entry in enumerate(entries, 1):
            if not isinstance(entry, dict):
                print(f"Entry #{idx}: {str(entry)[:100]}")
                continue
            
            print(f"{'─'*80}")
            print(f"Entry #{idx}:")
            print(f"{'─'*80}")
            
            for field_name in sorted(entry.keys()):
                field_value = entry[field_name]
                
                # Format value based on type
                if isinstance(field_value, (list, dict)):
                    value_str = json.dumps(field_value, ensure_ascii=False)[:200]
                    if len(json.dumps(field_value, ensure_ascii=False)) > 200:
                        value_str += "..."
                elif field_value is None:
                    value_str = "NULL"
                elif field_value == "":
                    value_str = "(empty string)"
                else:
                    value_str = str(field_value)[:200]
                    if len(str(field_value)) > 200:
                        value_str += "..."
                
                print(f"  {field_name}: {value_str}")
            print()
        
        print("="*80)
        print(f"✅ Analysis complete - {total_entries} entries processed")
        print("="*80)
        
        return {
            'total_entries': total_entries,
            'field_count': len(field_stats),
            'field_stats': dict(field_stats)
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error analyzing file: {e}")
        return None

def select_json_file():
    """Open file dialog to select JSON file"""
    root = Tk()
    root.withdraw()  # Hide the main window
    root.attributes('-topmost', True)  # Bring dialog to front
    
    filepath = filedialog.askopenfilename(
        title="Select JSON file to analyze",
        filetypes=[
            ("JSON files", "*.json"),
            ("All files", "*.*")
        ],
        initialdir=os.path.dirname(__file__)
    )
    
    root.destroy()
    return filepath

def main():
    """Main function"""
    print("="*80)
    print("JSON ANALYZER - Comprehensive JSON File Analysis")
    print("="*80)
    
    # Ask user to select file
    filepath = select_json_file()
    
    if not filepath:
        print("⚠️ No file selected")
        return
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return
    
    # Analyze the file
    analyze_json_file(filepath)
    
    print("\n\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    main()
