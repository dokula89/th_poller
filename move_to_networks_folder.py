"""
Move existing HTML and JSON files from Captures/date/ to Captures/date/Networks/
"""
from pathlib import Path
import shutil

BASE_DIR = Path(__file__).parent / "Captures"

def move_files_to_networks():
    """Move all networks_*.html and networks_*.json files to Networks subfolder"""
    
    if not BASE_DIR.exists():
        print(f"Captures directory not found: {BASE_DIR}")
        return
    
    # Get all date folders
    date_folders = [d for d in BASE_DIR.iterdir() if d.is_dir() and d.name != "images"]
    
    print(f"Found {len(date_folders)} date folders")
    
    for date_folder in date_folders:
        print(f"\nProcessing: {date_folder.name}")
        
        # Create Networks subfolder if it doesn't exist
        networks_folder = date_folder / "Networks"
        networks_folder.mkdir(exist_ok=True)
        print(f"  Created/verified: {networks_folder}")
        
        # Find all networks_* files in the root of the date folder
        html_files = list(date_folder.glob("networks_*.html"))
        json_files = list(date_folder.glob("networks_*.json"))
        
        all_files = html_files + json_files
        
        if not all_files:
            print(f"  No files to move")
            continue
        
        print(f"  Found {len(html_files)} HTML files and {len(json_files)} JSON files")
        
        # Move each file
        moved = 0
        for file in all_files:
            dest = networks_folder / file.name
            
            # Skip if already exists in destination
            if dest.exists():
                print(f"  Skipped (already exists): {file.name}")
                continue
            
            try:
                shutil.move(str(file), str(dest))
                print(f"  Moved: {file.name} -> Networks/{file.name}")
                moved += 1
            except Exception as e:
                print(f"  ERROR moving {file.name}: {e}")
        
        print(f"  Total moved: {moved} files")

if __name__ == "__main__":
    print("="*80)
    print("Moving files to Networks subfolders")
    print("="*80)
    move_files_to_networks()
    print("\n" + "="*80)
    print("Done!")
    print("="*80)
