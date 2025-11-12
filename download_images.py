"""
Image Downloader - Download all images from extracted JSON files
Downloads images from img_urls field and names them using listing_id
"""
import json
import os
import requests
from pathlib import Path
from urllib.parse import urlparse
import time

def download_image(url, save_path, timeout=30):
    """Download a single image from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        print(f"   ❌ Failed to download: {e}")
        return False

def process_json_file(json_path):
    """Process a JSON file and download all images"""
    print(f"\n{'='*80}")
    print(f"📄 Processing: {os.path.basename(json_path)}")
    print(f"{'='*80}")
    
    try:
        # Load JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            listings = data
        elif isinstance(data, dict):
            if 'data' in data and isinstance(data['data'], list):
                listings = data['data']
            elif 'listings' in data and isinstance(data['listings'], list):
                listings = data['listings']
            else:
                listings = [data]
        else:
            print(f"⚠️ Unexpected JSON type: {type(data)}")
            return
        
        total_listings = len(listings)
        print(f"📊 Found {total_listings} listings")
        
        # Create output folder based on JSON filename
        json_dir = os.path.dirname(json_path)
        json_filename = os.path.basename(json_path)
        # Remove .json extension and use as folder name
        folder_name = json_filename.replace('.json', '')
        output_dir = os.path.join(json_dir, folder_name)
        
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 Output folder: {output_dir}")
        
        # Process each listing
        downloaded = 0
        skipped = 0
        failed = 0
        
        for idx, listing in enumerate(listings, 1):
            if not isinstance(listing, dict):
                continue
            
            # Get listing_id for unique naming
            listing_id = listing.get('listing_id', f'unknown_{idx}')
            
            # Get image URLs
            img_urls = listing.get('img_urls', '')
            
            if not img_urls:
                print(f"[{idx}/{total_listings}] ⚠️ No images for listing: {listing_id}")
                skipped += 1
                continue
            
            # img_urls can be a single URL or comma-separated URLs
            if isinstance(img_urls, str):
                urls = [url.strip() for url in img_urls.split(',') if url.strip()]
            elif isinstance(img_urls, list):
                urls = img_urls
            else:
                urls = [str(img_urls)]
            
            print(f"\n[{idx}/{total_listings}] 📷 Listing: {listing_id}")
            print(f"   Found {len(urls)} image(s)")
            
            # Download each image
            for img_idx, url in enumerate(urls, 1):
                # Get file extension from URL
                parsed_url = urlparse(url)
                path_parts = parsed_url.path.split('/')
                original_filename = path_parts[-1] if path_parts else 'image.jpg'
                
                # Get extension (default to .jpg if not found)
                ext = os.path.splitext(original_filename)[1]
                if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    ext = '.jpg'
                
                # Create unique filename using listing_id
                if len(urls) > 1:
                    # Multiple images: listing_id_1.jpg, listing_id_2.jpg, etc.
                    filename = f"{listing_id}_{img_idx}{ext}"
                else:
                    # Single image: listing_id.jpg
                    filename = f"{listing_id}{ext}"
                
                save_path = os.path.join(output_dir, filename)
                
                # Skip if already exists
                if os.path.exists(save_path):
                    print(f"   ✓ Already exists: {filename}")
                    skipped += 1
                    continue
                
                # Download image
                print(f"   ⬇️ Downloading: {filename}")
                print(f"      URL: {url[:80]}...")
                
                if download_image(url, save_path):
                    file_size = os.path.getsize(save_path)
                    print(f"   ✅ Saved: {filename} ({file_size:,} bytes)")
                    downloaded += 1
                else:
                    failed += 1
                
                # Small delay to avoid overwhelming the server
                time.sleep(0.3)
        
        # Summary
        print(f"\n{'='*80}")
        print(f"📊 SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Downloaded: {downloaded}")
        print(f"⏭️ Skipped: {skipped}")
        print(f"❌ Failed: {failed}")
        print(f"📁 Output folder: {output_dir}")
        print(f"{'='*80}")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    import sys
    from tkinter import Tk, filedialog
    
    print("="*80)
    print("IMAGE DOWNLOADER - Extract images from JSON files")
    print("="*80)
    
    # Check if file was provided as argument
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    else:
        # Open file dialog
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        json_path = filedialog.askopenfilename(
            title="Select JSON file with listings",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ],
            initialdir=os.path.join(os.path.dirname(__file__), 'Captures')
        )
        root.destroy()
    
    if not json_path:
        print("⚠️ No file selected")
        return
    
    if not os.path.exists(json_path):
        print(f"❌ File not found: {json_path}")
        return
    
    # Process the file
    process_json_file(json_path)
    
    print("\n\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    main()
