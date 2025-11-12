#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add a local image path field (image_url) to extracted_listings.json while preserving existing img_urls.
- image_url: relative local path under Captures/images where the image would be saved
- img_urls: kept as-is (original remote URL string or list)

This tool does NOT download the images; it only sets a stable local path.
"""
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
CAPTURES_DIR = SCRIPT_DIR / "Captures"
IMAGES_DIR = CAPTURES_DIR / "images"

# Infer today's default JSON path if none provided
DEFAULT_JSON = CAPTURES_DIR / datetime.now().strftime("%Y-%m-%d") / "extracted_listings.json"


def _ext_from_url(url: str, fallback: str = ".jpg") -> str:
    try:
        path = urlparse(url).path
        ext = Path(path).suffix
        return ext if ext else fallback
    except Exception:
        return fallback


def _safe_filename(listing: dict) -> str:
    """Build a local filename using listing_id and image file hints to avoid collisions."""
    listing_id = (listing.get("listing_id") or listing.get("id") or "item")
    # Use image_filename if present, else derive from img_urls
    image_filename = listing.get("image_filename")
    if image_filename:
        return f"{listing_id}_{image_filename}"
    img_url = listing.get("img_urls")
    if isinstance(img_url, str) and img_url:
        return f"{listing_id}{_ext_from_url(img_url)}"
    return f"{listing_id}.jpg"


def main():
    if len(sys.argv) > 1:
        json_path = Path(sys.argv[1]).resolve()
    else:
        json_path = DEFAULT_JSON

    if not json_path.exists():
        print(f"❌ JSON file not found: {json_path}")
        print("Provide a path, e.g.: python fix_images_in_json.py Captures/2025-10-29/extracted_listings.json")
        sys.exit(1)

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to read/parse JSON: {e}")
        sys.exit(1)

    if not isinstance(data, list):
        print("❌ JSON root must be a list of listings")
        sys.exit(1)

    updated = 0
    for listing in data:
        if not isinstance(listing, dict):
            continue
        # Preserve img_urls as-is; add image_url if missing or empty
        image_url = listing.get("image_url")
        if not image_url:
            fname = _safe_filename(listing)
            listing["image_url"] = f"images/{fname}"
            updated += 1

    # Write back
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Updated {updated} listings with image_url in {json_path}")
    print(f"ℹ Local images directory: {IMAGES_DIR}")


if __name__ == "__main__":
    main()
