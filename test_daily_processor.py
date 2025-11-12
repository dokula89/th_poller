#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for daily capture processor
Dry-run mode to test without database writes
"""

import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from process_daily_captures import (
    get_todays_capture_folder,
    process_html_file,
    extract_unique_id_from_url,
    save_json_backup
)

def test_url_extraction():
    """Test unique ID extraction from various URL formats"""
    print("=" * 60)
    print("Testing URL ID Extraction")
    print("=" * 60)
    
    test_urls = [
        "https://example.com/listings/detail/ba786613-8954-447d-8b6c-c5942b3c218b",
        "https://example.com/property/12345",
        "https://rentals.com/detail/apartment-downtown-seattle",
        "https://example.com/listings/unit-a-123",
    ]
    
    for url in test_urls:
        unique_id = extract_unique_id_from_url(url)
        print(f"URL: {url}")
        print(f"  → ID: {unique_id}\n")


def test_extraction():
    """Test HTML processing without database write"""
    print("\n" + "=" * 60)
    print("Testing HTML Extraction (Dry Run)")
    print("=" * 60)
    
    # Get today's folder
    today_folder = get_todays_capture_folder()
    if not today_folder:
        # Try using a known folder for testing
        print("\nNo today's folder found. Looking for any recent folder...")
        captures_base = SCRIPT_DIR / "Captures"
        folders = sorted([f for f in captures_base.iterdir() if f.is_dir() and f.name.startswith('202')], reverse=True)
        if folders:
            today_folder = folders[0]
            print(f"Using folder: {today_folder}")
        else:
            print("No capture folders found!")
            return
    
    # Find HTML files
    html_files = list(today_folder.glob("*.html"))
    if not html_files:
        print(f"No HTML files in {today_folder}")
        return
    
    print(f"\nFound {len(html_files)} HTML file(s)")
    
    # Process first file only (for testing)
    html_file = html_files[0]
    print(f"\nProcessing: {html_file.name} (DRY RUN)")
    
    listings = process_html_file(html_file)
    
    if listings:
        print(f"\n✅ Extracted {len(listings)} listings")
        print("\nFirst listing preview:")
        print("-" * 60)
        first = listings[0]
        for key in ['id', 'title', 'bedrooms', 'bathrooms', 'price', 'full_address', 'listing_website']:
            value = first.get(key, 'N/A')
            print(f"  {key}: {value}")
        
        # Save to temp JSON
        output = SCRIPT_DIR / "test_extraction_output.json"
        import json
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(listings, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Full output saved to: {output}")
    else:
        print("\n❌ No listings extracted")


if __name__ == "__main__":
    print("\n🧪 Daily Capture Processor - Test Mode\n")
    
    # Test URL extraction
    test_url_extraction()
    
    # Test HTML extraction (requires OpenAI API key)
    api_key = input("\nEnter OpenAI API key to test extraction (or press Enter to skip): ").strip()
    if api_key:
        import os
        os.environ['OPENAI_API_KEY'] = api_key
        test_extraction()
    else:
        print("\n⏭ Skipping extraction test (no API key provided)")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
