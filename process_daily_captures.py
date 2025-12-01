#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Capture Processor
Processes HTML files from today's Captures folder, uses ChatGPT to extract apartment listings,
downloads images, and inserts/updates records in the apartment_listings database.
"""

import json
import os
import sys
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import hashlib
from urllib.parse import urlparse, urljoin

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
CAPTURES_BASE = SCRIPT_DIR / "Captures"
IMAGES_DIR = SCRIPT_DIR / "Captures" / "images"

# Ensure images directory exists
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Import config utilities
try:
    from config_utils import CFG
    import mysql.connector as mysql
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    sys.exit(1)


def get_todays_capture_folder() -> Optional[Path]:
    """Get today's date folder in Captures"""
    today = datetime.now().strftime("%Y-%m-%d")
    folder = CAPTURES_BASE / today
    if folder.exists() and folder.is_dir():
        return folder
    return None


def extract_unique_id_from_url(url: str) -> str:
    """Extract a unique identifier from a listing URL"""
    if not url:
        return hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:16]
    
    # Try to extract UUID or unique ID from URL
    # Common patterns: /listings/12345, /detail/uuid-here, etc.
    patterns = [
        r'/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',  # UUID
        r'/(\d{5,})',  # Numeric ID (5+ digits)
        r'/detail/([a-zA-Z0-9_-]+)',  # Detail page ID
        r'/listings?/([a-zA-Z0-9_-]+)',  # Listings ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Fallback: hash the URL
    return hashlib.md5(url.encode()).hexdigest()[:16]


def download_image(url: str, listing_id: str) -> Optional[str]:
    """Download an image and save it to the images folder. Returns filename with extension only."""
    if not url or not url.startswith('http'):
        return None
    
    try:
        # Get file extension from URL
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix.lower()
        # Validate extension, default to .jpg if invalid
        if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            ext = '.jpg'
        
        # Filename is just listing_id + extension
        filename = f"{listing_id}{ext}"
        filepath = IMAGES_DIR / filename
        
        # Skip if already exists
        if filepath.exists():
            return filename
        
        # Download
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        # Save
        filepath.write_bytes(response.content)
        print(f"  ✓ Downloaded image: {filename}")
        return filename
        
    except Exception as e:
        print(f"  ✗ Failed to download image {url}: {e}")
        return None


def extract_listings_with_ai(html_content: str, source_file: str) -> List[Dict]:
    """Use ChatGPT to extract apartment listings from HTML"""
    try:
        import openai
        
        # Get API key
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise Exception("OPENAI_API_KEY environment variable not set")
        
        # Truncate HTML if too large (keep first 50k chars for context)
        if len(html_content) > 50000:
            html_content = html_content[:50000] + "\n... [truncated]"
        
        # Create prompt
        prompt = f"""Extract all apartment listings from this HTML page.

HTML Content:
{html_content}

Return a JSON array of listing objects with these fields (use null if not found):
- listing_website: The listing detail page URL
- title: Listing title/name
- bedrooms: Number of bedrooms (as string, e.g. "1", "2", "Studio")
- bathrooms: Number of bathrooms (as string, e.g. "1", "1.5", "2")
- sqft: Square footage (number only, no commas)
- price: Monthly rent price (e.g. "$1,650" or "1650")
- img_urls: Main image URL (just one URL as string)
- full_address: Complete address
- street: Street address only
- city: City name
- state: State abbreviation
- description: Short description or features
- available_date: When available (YYYY-MM-DD format if parseable)
- phone_contact: Contact phone
- email_contact: Contact email
- apply_now_link: Application URL

Return ONLY the JSON array, no other text. Example:
[
  {{
    "listing_website": "https://...",
    "title": "Spacious 1BR Apartment",
    "bedrooms": "1",
    "bathrooms": "1",
    "sqft": "650",
    "price": "$1,650",
    "img_urls": "https://...",
    "full_address": "123 Main St, Seattle, WA 98101",
    "street": "123 Main St",
    "city": "Seattle",
    "state": "WA",
    "description": "Beautiful apartment with parking",
    "available_date": "2025-11-01",
    "phone_contact": null,
    "email_contact": null,
    "apply_now_link": "https://..."
  }}
]"""

        print(f"  → Sending HTML to ChatGPT for analysis...", flush=True)
        print(f"  → Using model: gpt-4o-mini", flush=True)
        print(f"  → HTML size: {len(html_content)} characters", flush=True)
        
        client = openai.OpenAI(api_key=api_key)
        
        print(f"  → Waiting for ChatGPT response...", flush=True)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert at extracting structured data from apartment listing HTML pages. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        print(f"  ✓ Received response from ChatGPT!", flush=True)
        
        # Parse response
        response_text = response.choices[0].message.content.strip()
        
        print(f"  → Response length: {len(response_text)} characters", flush=True)
        print(f"  → Parsing JSON response...", flush=True)
        
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()
        
        listings = json.loads(response_text)
        print(f"  ✓ ChatGPT extracted {len(listings)} listings from HTML!", flush=True)
        return listings
        
    except Exception as e:
        print(f"  ✗ AI extraction failed: {e}")
        return []


def process_html_file(html_file: Path) -> List[Dict]:
    """Process a single HTML file and extract listings"""
    print(f"\n📄 Processing: {html_file.name}", flush=True)
    
    try:
        # Read HTML
        html_content = html_file.read_text(encoding='utf-8', errors='ignore')
        
        # Extract source URL from HTML comment if present
        source_url = None
        m = re.search(r'<!-- saved .+ from (.+?) -->', html_content)
        if m:
            source_url = m.group(1).strip()
            print(f"  📍 Source URL: {source_url}", flush=True)
        
        # Use AI to extract listings
        listings = extract_listings_with_ai(html_content, str(html_file))
        
        if not listings:
            print(f"  ⚠ No listings extracted")
            return []
        
        # Process each listing
        processed = []
        for idx, listing in enumerate(listings, 1):
            # Use listing_id from JSON if available, otherwise extract from URL
            unique_id = listing.get('listing_id')
            if not unique_id:
                listing_url = listing.get('listing_website') or listing.get('apply_now_link') or ''
                unique_id = extract_unique_id_from_url(listing_url)
            
            # Handle thumbnail_url from existing image_filename or download new image
            if listing.get('image_filename'):
                # Use existing image_filename as thumbnail_url
                listing['thumbnail_url'] = listing['image_filename']
                listing['image_url'] = f"images/{listing['image_filename']}"
            else:
                # Download image if present
                original_img_url = listing.get('img_urls')
                if original_img_url:
                    # Download and get filename with extension (e.g., "listing_id.jpg")
                    thumbnail_filename = download_image(original_img_url, unique_id)
                    if thumbnail_filename:
                        # Store just the filename in thumbnail_url
                        listing['thumbnail_url'] = thumbnail_filename
                        # Keep the remote URL in img_urls (don't add thumbnail to it)
                        listing['img_urls'] = original_img_url
                        # Also set image_url for backward compatibility
                        listing['image_url'] = f"images/{thumbnail_filename}"
            
            # Add metadata (use unique_id as the database id)
            listing['id'] = unique_id
            listing['network'] = html_file.stem  # e.g., "networks_1"
            listing['time_created'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            listing['time_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Set default values for missing fields
            defaults = {
                'user_id': None,
                'active': 1,
                'appfolio_id': None,
                'propertyType': None,
                'type': None,
                'unit_number': None,
                'deal': None,
                'Lease_Length': None,
                'Pool': None,
                'Gym': None,
                'MFTE': None,
                'Managed': None,
                's_65': None,
                's_55': None,
                'Credit_Score': None,
                'Application_Fee': None,
                'Deposit_Amount': None,
                'name': listing.get('title'),
                'price_change': None,
                'floorplan_url': None,
                'available': listing.get('available_date'),
                'other_details': None,
                'details': None,
                'amenities': None,
                'image_url': None,
                'thumbnail_url': None,
                'Balcony': None,
                'Cats': None,
                'Dogs': None,
                'Parking': None,
                'parking_fee': None,
                'Text': None,
                'Building_Name': None,
                'Latitude': None,
                'Longitude': None,
                'suburb': None,
                'country': 'USA',
                'details_processed': 0,
                'name_contact': None,
                'google_addresses_id': None,
                'google_places_id': None,
            }
            
            # Merge defaults
            for key, value in defaults.items():
                if key not in listing or listing[key] is None:
                    listing[key] = value
            
            processed.append(listing)
            print(f"  ✓ Listing {idx}: {listing.get('title', 'N/A')} - ID: {unique_id}")
        
        return processed
        
    except Exception as e:
        print(f"  ✗ Error processing file: {e}")
        import traceback
        traceback.print_exc()
        return []


def upsert_listings_to_db(listings: List[Dict]) -> int:
    """Insert or update listings in the apartment_listings table"""
    if not listings:
        return 0
    
    print(f"\n💾 Upserting {len(listings)} listings to database...")
    
    try:
        # Connect to MySQL
        conn = mysql.connect(
            host=CFG["MYSQL_HOST"],
            port=CFG["MYSQL_PORT"],
            user=CFG["MYSQL_USER"],
            password=CFG["MYSQL_PASSWORD"],
            database=CFG["MYSQL_DB"]
        )
        cursor = conn.cursor()
        
        # Get table columns
        cursor.execute("SHOW COLUMNS FROM apartment_listings")
        valid_columns = {row[0] for row in cursor.fetchall()}
        
        inserted = 0
        updated = 0
        
        for listing in listings:
            # Filter to only valid columns
            filtered = {k: v for k, v in listing.items() if k in valid_columns}
            
            # Check if exists
            cursor.execute("SELECT id FROM apartment_listings WHERE id = %s", (filtered['id'],))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing
                set_clause = ", ".join([f"{k} = %s" for k in filtered.keys() if k != 'id'])
                values = [v for k, v in filtered.items() if k != 'id']
                values.append(filtered['id'])
                
                sql = f"UPDATE apartment_listings SET {set_clause} WHERE id = %s"
                cursor.execute(sql, values)
                updated += 1
                print(f"  ↻ Updated: {filtered.get('title', 'N/A')} (ID: {filtered['id']})")
            else:
                # Insert new
                columns = ", ".join(filtered.keys())
                placeholders = ", ".join(["%s"] * len(filtered))
                values = list(filtered.values())
                
                sql = f"INSERT INTO apartment_listings ({columns}) VALUES ({placeholders})"
                cursor.execute(sql, values)
                inserted += 1
                print(f"  ✓ Inserted: {filtered.get('title', 'N/A')} (ID: {filtered['id']})")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n✅ Database updated: {inserted} inserted, {updated} updated")
        return inserted + updated
        
    except Exception as e:
        print(f"\n❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def save_json_backup(listings: List[Dict], folder: Path):
    """Save listings to a JSON backup file"""
    try:
        output_file = folder / "extracted_listings.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(listings, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved backup: {output_file}")
    except Exception as e:
        print(f"\n⚠ Failed to save JSON backup: {e}")


def main():
    """Main processing pipeline"""
    print("=" * 60, flush=True)
    print("Daily Capture Processor", flush=True)
    print("=" * 60, flush=True)
    
    # Get today's folder
    today_folder = get_todays_capture_folder()
    if not today_folder:
        today_str = datetime.now().strftime("%Y-%m-%d")
        print(f"\n❌ No captures folder found for today ({today_str})", flush=True)
        print(f"Expected: {CAPTURES_BASE / today_str}", flush=True)
        return
    
    print(f"\n📁 Processing folder: {today_folder}", flush=True)
    
    # Find all HTML files
    html_files = list(today_folder.glob("*.html"))
    if not html_files:
        print(f"\n⚠ No HTML files found in {today_folder}", flush=True)
        return
    
    print(f"Found {len(html_files)} HTML file(s)", flush=True)
    
    # Process each file
    all_listings = []
    for html_file in html_files:
        listings = process_html_file(html_file)
        all_listings.extend(listings)
    
    if not all_listings:
        print(f"\n⚠ No listings extracted from any files", flush=True)
        return
    
    # Save JSON backup
    save_json_backup(all_listings, today_folder)
    
    # Upsert to database
    count = upsert_listings_to_db(all_listings)
    
    print("\n" + "=" * 60, flush=True)
    print(f"✅ Processing complete: {count} listings processed", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
