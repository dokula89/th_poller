def extract_links_and_text(html: str) -> list:
    """
    Extract all links (anchor hrefs) and visible text nodes from the HTML, number them, and return as a list of (index, value, type, extra_info).
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []
    # Extract all anchor tags with href, including their tr/td/a index location
    for tr_idx, tr in enumerate(soup.find_all("tr"), 1):
        for td_idx, td in enumerate(tr.find_all("td"), 1):
            for a_idx, a in enumerate(td.find_all("a", href=True), 1):
                text = a.get_text(strip=True)
                href = a["href"]
                if text or href:
                    results.append({
                        "type": "link",
                        "value": href,
                        "text": text,
                        "location": f"tr[{tr_idx}]/td[{td_idx}]/a[{a_idx}]"
                    })
    # Also extract links outside tables
    for a in soup.find_all("a", href=True):
        if not a.find_parent("tr"):
            text = a.get_text(strip=True)
            href = a["href"]
            if text or href:
                results.append({
                    "type": "link",
                    "value": href,
                    "text": text,
                    "location": f"a (no tr)"
                })
    # Extract all visible text nodes (not inside script/style), with tr/td location if present
    def visible_texts(soup):
        blacklist = ["style", "script", "head", "title", "meta", "[document]", "noscript"]
        for element in soup.find_all(text=True):
            if element.parent.name not in blacklist:
                txt = element.strip()
                if txt:
                    # Find tr/td parent if any
                    tr = element.find_parent("tr")
                    td = element.find_parent("td")
                    loc = None
                    if tr and td:
                        tr_idx = list(tr.parent.find_all("tr")).index(tr) + 1 if tr.parent else 1
                        td_idx = list(tr.find_all("td")).index(td) + 1
                        loc = f"tr[{tr_idx}]/td[{td_idx}]"
                    elif tr:
                        tr_idx = list(tr.parent.find_all("tr")).index(tr) + 1 if tr.parent else 1
                        loc = f"tr[{tr_idx}]"
                    results.append({
                        "type": "text",
                        "value": txt,
                        "text": None,
                        "location": loc or "(no tr)"
                    })
    visible_texts(soup)
    # Number them
    for idx, item in enumerate(results, 1):
        item["index"] = idx
    return results
import tkinter as tk
from tkinter import ttk, simpledialog
import threading
import json as _json
from pathlib import Path

# Apartment listings fields (from sample JSON)
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

MAPPINGS_PATH = str(Path(__file__).parent / "field_mappings.json")

def load_field_mappings():
    try:
        with open(MAPPINGS_PATH, "r", encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {}

def save_field_mappings(mappings):
    with open(MAPPINGS_PATH, "w", encoding="utf-8") as f:
        _json.dump(mappings, f, indent=2)

def prompt_field_mapping(job_id, row_fields):
    # If row_fields is a tuple and the first element is '__HTML_ELEMENTS__', use element-based mapping UI
    if isinstance(row_fields, tuple) and row_fields and row_fields[0] == "__HTML_ELEMENTS__":
        elements = row_fields[1]
        network_id = row_fields[2] if len(row_fields) > 2 else None
        website = row_fields[3] if len(row_fields) > 3 else None
        result = {}
        done = threading.Event()
        def show_dialog():
            win = tk.Tk()
            title_parts = [f"HTML Element Mapping for Job {job_id}"]
            if network_id is not None:
                title_parts.append(f"Network ID: {network_id}")
            if website:
                title_parts.append(f"Link: {website}")
            win.title(" | ".join(title_parts))

            # Show link as a small, copyable label under the header
            if website:
                link_row = tk.Frame(scrollable_frame)
                link_row.pack(fill="x", padx=10, pady=(6,0))
                link_lbl = tk.Label(link_row, text=f"Link: {website}", font=("Consolas", 8), fg="#A0A6AD")
                link_lbl.pack(side="left", anchor="w")
                def _copy_link(_e=None):
                    try:
                        win.clipboard_clear(); win.clipboard_append(str(website)); win.update()
                    except Exception:
                        pass
                copy_btn = tk.Button(link_row, text="Copy", command=_copy_link, font=("Segoe UI", 8))
                copy_btn.pack(side="left", padx=(6,0))
            
            # Make window scrollable for many elements
            canvas = tk.Canvas(win, width=900, height=600)
            scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            tk.Label(scrollable_frame, text="Map HTML elements to apartment_listings.json fields:", 
                    font=("Segoe UI", 10, "bold")).pack(pady=8)
            
            frame = tk.Frame(scrollable_frame)
            frame.pack(padx=10, pady=5, fill="both", expand=True)
            
            # Header row - VALUE first, then field assignment
            tk.Label(frame, text="Value from First Row", font=("Segoe UI", 9, "bold"), 
                    anchor="w", width=50).grid(row=0, column=0, sticky="w", pady=2)
            tk.Label(frame, text="Assign to Field", font=("Segoe UI", 9, "bold"), 
                    anchor="w", width=25).grid(row=0, column=1, sticky="w", pady=2)
            tk.Label(frame, text="Source Path", font=("Segoe UI", 9, "bold"), 
                    anchor="w", width=15).grid(row=0, column=2, sticky="w", pady=2)
            
            dropdowns = {}
            path_labels = {}  # Track path labels for editing
            
            def edit_path(elem_index):
                """Allow user to edit the CSS path for an element"""
                elem = next((e for e in elements if e['index'] == elem_index), None)
                if not elem:
                    return
                
                current_path = elem.get('path', '')
                new_path = simpledialog.askstring(
                    "Edit CSS Path",
                    f"Edit CSS selector path for element [{elem_index}]:",
                    initialvalue=current_path,
                    parent=win
                )
                
                if new_path is not None and new_path.strip():
                    # Update the element's path
                    elem['path'] = new_path.strip()
                    
                    # Update the path button text
                    if elem_index in path_labels:
                        path_labels[elem_index].config(text=f"📝 {new_path.strip()[:20]}...")
            
            for i, elem in enumerate(elements, 1):
                # Get the actual value (text, href, or src)
                text = elem.get('text', '')
                href = elem.get('href', '')
                src = elem.get('src', '')
                path = elem.get('path', 'unknown')
                
                # Primary value to display (what the user will assign)
                if text:
                    primary_value = text
                    value_type = "Text"
                elif href:
                    primary_value = href
                    value_type = "Link"
                elif src:
                    primary_value = src
                    value_type = "Image"
                else:
                    primary_value = "(empty)"
                    value_type = "Empty"
                
                # Display format: [index] VALUE (type)
                display_text = f"[{elem['index']}] {primary_value[:80]}"
                if len(primary_value) > 80:
                    display_text += "..."
                
                # Show VALUE prominently
                lbl = tk.Label(frame, text=display_text, anchor="w", width=50, 
                        wraplength=450, justify="left", font=("Segoe UI", 9), fg="#E8EAED")
                lbl.grid(row=i, column=0, sticky="w", pady=2)
                
                # Dropdown to assign field name
                var = tk.StringVar()
                cb = ttk.Combobox(frame, textvariable=var, values=APARTMENT_LISTING_FIELDS, 
                                state="readonly", width=28)
                cb.grid(row=i, column=1, sticky="w", pady=2, padx=5)
                dropdowns[elem['index']] = var
                
                # Show/Edit Path button (compact)
                path_btn = tk.Button(frame, text=f"📝 {path[:20]}..." if len(path) > 20 else f"📝 {path}", 
                                    command=lambda idx=elem['index']: edit_path(idx),
                                    font=("Segoe UI", 7), fg="#58A6FF", bg="#1A1D20", 
                                    relief="flat", cursor="hand2")
                path_btn.grid(row=i, column=2, sticky="w", pady=2, padx=5)
                path_labels[elem['index']] = path_btn

            
            def on_ok():
                # Save both the field mapping and the element paths
                for elem in elements:
                    field_name = dropdowns[elem['index']].get()
                    if field_name:  # Only save if a field was selected
                        result[elem['index']] = {
                            'field': field_name,
                            'path': elem.get('path', ''),
                            'tag': elem.get('tag', ''),
                            'original_text': elem.get('text', '')
                        }
                win.destroy()
                done.set()
            
            btn = tk.Button(scrollable_frame, text="Save Mapping", command=on_ok, 
                          font=("Segoe UI", 10, "bold"))
            btn.pack(pady=10)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            win.mainloop()
        
        t = threading.Thread(target=show_dialog)
        t.start()
        done.wait()
        return result
    
    # If row_fields is a tuple and the first element is '__EXTRACTED_VALUES__', use the new mapping UI
    if isinstance(row_fields, tuple) and row_fields and row_fields[0] == "__EXTRACTED_VALUES__":
        extracted_values = row_fields[1]
        network_id = row_fields[2] if len(row_fields) > 2 else None
        website = row_fields[3] if len(row_fields) > 3 else None
        result = {}
        done = threading.Event()
        def show_dialog():
            win = tk.Tk()
            title_parts = [f"First Run Mapping for Job {job_id}"]
            if network_id is not None:
                title_parts.append(f"Network ID: {network_id}")
            if website:
                title_parts.append(f"Website: {website}")
            win.title(" | ".join(title_parts))
            win.geometry("800x{}".format(100 + 40 * len(extracted_values)))
            win.resizable(False, False)
            tk.Label(win, text="Map each extracted value to apartment_listings.json fields:", font=("Segoe UI", 10, "bold")).pack(pady=8)
            frame = tk.Frame(win)
            frame.pack(padx=10, pady=5, fill="x")
            dropdowns = {}
            for i, item in enumerate(extracted_values):
                label_text = f"[{item['index']}] {item['type'].upper()}: {item['value']}"
                if item.get('text'):
                    label_text += f" (text: {item['text']})"
                tk.Label(frame, text=label_text, anchor="w", width=60, wraplength=500, justify="left").grid(row=i, column=0, sticky="w", pady=2)
                var = tk.StringVar()
                cb = ttk.Combobox(frame, textvariable=var, values=APARTMENT_LISTING_FIELDS, state="readonly", width=28)
                cb.grid(row=i, column=1, sticky="w", pady=2)
                dropdowns[item['index']] = var
            def on_ok():
                for item in extracted_values:
                    result[item['index']] = dropdowns[item['index']].get()
                win.destroy()
                done.set()
            btn = tk.Button(win, text="Save Mapping", command=on_ok)
            btn.pack(pady=10)
            win.mainloop()
        t = threading.Thread(target=show_dialog)
        t.start()
        done.wait()
        return result
    # Otherwise, use the original mapping UI
    result = {}
    done = threading.Event()
    if isinstance(row_fields, tuple) and len(row_fields) >= 2:
        field_names, first_record = row_fields[:2]
        network_id = row_fields[2] if len(row_fields) > 2 else None
        website = row_fields[3] if len(row_fields) > 3 else None
    else:
        field_names = row_fields
        first_record = None
        network_id = None
        website = None
    def show_dialog():
        win = tk.Tk()
        title_parts = [f"Field Mapping for Job {job_id}"]
        if network_id is not None:
            title_parts.append(f"Network ID: {network_id}")
        if website:
            title_parts.append(f"Website: {website}")
        win.title(" | ".join(title_parts))
        win.geometry("600x{}".format(80 + 40 * len(field_names)))
        win.resizable(False, False)
        tk.Label(win, text="Map each field value to apartment_listings.json fields:", font=("Segoe UI", 10, "bold")).pack(pady=8)
        frame = tk.Frame(win)
        frame.pack(padx=10, pady=5, fill="x")
        dropdowns = {}
        for i, field in enumerate(field_names):
            value = None
            if first_record and field in first_record:
                value = str(first_record[field])
            label_text = f"{field}: {value}" if value is not None else field
            tk.Label(frame, text=label_text, anchor="w", width=40, wraplength=350, justify="left").grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            cb = ttk.Combobox(frame, textvariable=var, values=APARTMENT_LISTING_FIELDS, state="readonly", width=28)
            cb.grid(row=i, column=1, sticky="w", pady=2)
            dropdowns[field] = var
        def on_ok():
            for field, var in dropdowns.items():
                result[field] = var.get()
            win.destroy()
            done.set()
        btn = tk.Button(win, text="Save Mapping", command=on_ok)
        btn.pack(pady=10)
        win.mainloop()
    t = threading.Thread(target=show_dialog)
    t.start()
    done.wait()
    return result
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re, json, time, os
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup
import requests

from config_utils import (
    CFG, BASE_DIR, GLOBAL_JSON_PATH, IMAGES_DIR,
    log_file, hud_push, ensure_dir,
    load_global_json, save_global_json,
    http_get, sanitize_ext, _send_telegram_text,
    # SFTP for uploads
    sftp_upload_file, sftp_upload_dir,
    SFTP_ENABLED, SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASS,
    REMOTE_JSON_DIR, REMOTE_IMAGES_PARENT,
)
from config_helpers import launch_manual_browser

# -----------------------------------------------------------------------------
# Capture paths (support both names) + (optional) sentinel
# -----------------------------------------------------------------------------
PRIMARY_CAPTURE = BASE_DIR / "network_6.html"     # canonical target (singular)
ALT_CAPTURE     = BASE_DIR / "networks_6.html"    # alternate (plural) accepted
OPEN_SENTINEL   = BASE_DIR / ".opened_once"       # unused for gating now (open once per run)

def _current_capture_path() -> Path:
    """Return whichever capture exists & is non-empty; otherwise default to PRIMARY."""
    try:
        if ALT_CAPTURE.exists() and ALT_CAPTURE.stat().st_size > 0:
            return ALT_CAPTURE
    except Exception:
        pass
    return PRIMARY_CAPTURE

# ---------- HTML subtree helpers ----------
def css_from_term(term: str) -> Optional[str]:
    if not term:
        return None
    t = term.strip()
    if any(ch in t for ch in ".#[]>:,"):
        return t
    toks = [x for x in re.split(r"\s+", t) if x]
    if not toks:
        return None
    if all(re.match(r"^[A-Za-z0-9_-]+$", x) for x in toks):
        return "." + ".".join(toks)
    return t

def first_match_subtree_html(page_html: str, base_url: str, the_css: str) -> str:
    soup = BeautifulSoup(page_html, "html.parser")
    selector = css_from_term(the_css or "")
    node = None
    if selector:
        try:
            node = soup.select_one(selector)
        except Exception:
            node = None
    if node is None:
        for sel in [".js-listings-container", ".all-listings", ".listings",
                    "[id*='listings']", "[class*='listings']", "body"]:
            try:
                node = soup.select_one(sel)
                if node:
                    break
            except Exception:
                continue
    if not node:
        return page_html
    return str(node)

# ---------- GLOBAL JSON helpers ----------
def upsert_global_source(base_name: str, link: str, saved_html: Path,
                         images_dir: Path, listings: List[Dict[str, Any]]):
    doc = load_global_json(GLOBAL_JSON_PATH)
    if "sources" not in doc or not isinstance(doc["sources"], dict):
        doc = {"last_updated": None, "sources": {}}
    doc["sources"][base_name] = {
        "source_url": link,
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "html_file": str(saved_html),
        "images_dir": str(images_dir),
        "listings": listings or []
    }
    save_global_json(GLOBAL_JSON_PATH, doc)

def _as_map_by_url(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in records or []:
        if isinstance(r, dict):
            url = r.get("listing_url")
            if url:
                out[url] = r
    return out

def compute_deltas(previous: List[Dict[str, Any]], current: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    prev_map = _as_map_by_url(previous)
    curr_map = _as_map_by_url(current)
    prev_urls = set(prev_map.keys())
    curr_urls = set(curr_map.keys())
    new_urls = curr_urls - prev_urls
    removed_urls = prev_urls - curr_urls
    price_updates = 0
    for url in (prev_urls & curr_urls):
        try:
            prev_rent = prev_map[url].get("rent_amount")
            curr_rent = curr_map[url].get("rent_amount")
            if prev_rent is not None and curr_rent is not None and prev_rent != curr_rent:
                price_updates += 1
        except Exception:
            continue
    return (len(new_urls), price_updates, len(removed_urls))

def _resolve_value_by_path(html: str, path: str, base_url: str) -> Optional[str]:
    """
    Given raw HTML and a saved path, attempt to resolve a single value.
    Supported path formats:
      - "tr[1]/td[2]" (1-based indices; our table-cell shorthand)
      - Any CSS selector supported by BeautifulSoup.select_one
    Value preference order: href > src > text
    """
    if not path:
        return None
    try:
        soup = BeautifulSoup(html, "html.parser")
        node = None
        # Table shorthand like tr[1]/td[2]
        m = re.match(r"^tr\[(\d+)\]/(td|th)\[(\d+)\]$", path.strip(), re.I)
        if m:
            tr_idx = int(m.group(1))
            cell_tag = m.group(2).lower()
            td_idx = int(m.group(3))
            trs = soup.find_all("tr")
            if 0 < tr_idx <= len(trs):
                tr = trs[tr_idx - 1]
                cells = tr.find_all(cell_tag)
                if 0 < td_idx <= len(cells):
                    node = cells[td_idx - 1]
        else:
            try:
                node = soup.select_one(path)
            except Exception:
                node = None
        if not node:
            return None
        # Prefer href, then src, then text
        href = node.get("href") if hasattr(node, "get") else None
        src  = node.get("src") if hasattr(node, "get") else None
        if href:
            return urljoin(base_url, href)
        if src:
            return urljoin(base_url, src)
        # Text
        try:
            txt = node.get_text(strip=True)
            return _norm(txt) if txt else None
        except Exception:
            return None
    except Exception:
        return None

def send_telegram_counts(new_count: int, price_updates: int, removed_count: int,
                         base_name: str, link: str):
    today = datetime.now().strftime("%B %d, %Y, %I:%M %p")
    # Count all found field values in the current listings
    doc = load_global_json(GLOBAL_JSON_PATH)
    listings = (doc.get("sources", {}).get(base_name, {}).get("listings") or [])
    field_counts = {}
    if listings and isinstance(listings, list):
        for rec in listings:
            if not isinstance(rec, dict):
                continue
            for k, v in rec.items():
                if v not in (None, "", [], {}):
                    field_counts[k] = field_counts.get(k, 0) + 1
    # Format field counts for Telegram
    if field_counts:
        field_lines = [f"<b>{k}</b>: {v}" for k, v in sorted(field_counts.items())]
        field_counts_str = "\n".join(field_lines)
    else:
        field_counts_str = "No fields found."

    message = (
        f"🏠 <b>Listing Update</b> — <code>{base_name}</code>\n"
        f"🔗 <a href=\"{link or ''}\">Source</a>\n\n"
        f"🆕 New listings: <b>{new_count}</b>\n"
        f"💲 Price updates: <b>{price_updates}</b>\n"
        f"📉 Removed: <b>{removed_count}</b>\n\n"
        f"<b>Field Value Counts:</b>\n{field_counts_str}\n\n"
        f"<i>{today}</i>"
    )
    hud_push(f"Δ {base_name}: +{new_count} ${price_updates} −{removed_count}")
    _send_telegram_text(message, parse_mode="HTML")

# ---------- Image downloading ----------
def download_images(image_urls: List[str], dest_dir: Path, base_name: str) -> List[str]:
    ensure_dir(dest_dir)
    saved_paths: List[str] = []
    idx = 1
    for url in image_urls:
        if not url:
            continue
        try:
            # If a file for this index already exists with any common extension, reuse it and skip download
            prefix = f"{base_name}-{idx:03d}"
            for_try_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp")
            existing_path = None
            for ex in for_try_exts:
                cand = dest_dir / f"{prefix}{ex}"
                if cand.exists():
                    try:
                        if cand.stat().st_size > 0:
                            existing_path = cand
                            break
                    except Exception:
                        pass
            if existing_path is not None:
                saved_paths.append(str(existing_path))
                idx += 1
                continue

            resp = requests.get(url, timeout=CFG["HTTP_TIMEOUT"], stream=True, headers={"User-Agent": CFG["HTTP_UA"]})
            resp.raise_for_status()
            ext = sanitize_ext(url, resp.headers.get("Content-Type"))
            fname = f"{prefix}{ext}"
            fpath = dest_dir / fname
            with open(fpath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
            saved_paths.append(str(fpath))
            idx += 1
        except Exception as e:
            log_file(f"Image download failed ({url}): {e}")
            continue
    if saved_paths:
        hud_push(f"↓ Images saved: {len(saved_paths)}")
    return saved_paths

# ---------- Parser helpers ----------
def _norm(s: Optional[str]) -> Optional[str]:
    return re.sub(r"\s+", " ", (s or "").strip()) or None

def _parse_money_int(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    m = re.search(r'[\$£€]\s*([0-9][0-9,]*)', text)
    return int(m.group(1).replace(',', '')) if m else None

def _parse_bed_bath(text: Optional[str]) -> Tuple[Optional[int], Optional[float]]:
    if not text:
        return (None, None)
    s = _norm(text) or ""
    m_bed  = re.search(r'(\d+)\s*(?:bed(?:room)?s?|bd|br|bdrm)s?\b', s, re.I)
    m_bath = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath(?:room)?s?|ba|bth)s?\b', s, re.I)
    beds  = int(m_bed.group(1)) if m_bed else None
    baths = float(m_bath.group(1)) if m_bath else None
    if beds is None or baths is None:
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:bd|br|bdrm)\s*(?:[/|,]|\s+)\s*(\d+(?:\.\d+)?)\s*(?:ba|bath|bth)\b', s, re.I)
        if m:
            if beds  is None: beds  = int(float(m.group(1)))
            if baths is None: baths = float(m.group(2))
    if beds is None or baths is None:
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:ba|bath|bth)\s*(?:[/|,]|\s+)\s*(\d+(?:\.\d+)?)\s*(?:bd|br|bdrm)\b', s, re.I)
        if m:
            if baths is None: baths = float(m.group(1))
            if beds  is None: beds  = int(float(m.group(2)))
    return (beds, baths)

def _parse_sqft(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    s = _norm(text) or ""
    m = re.search(r'(?:square\s*feet|sq(?:uare)?\s*\.?\s*ft\.?|sqft|sf)\s*[:\-]?\s*([0-9][0-9,]*)\b', s, re.I)
    if m:
        try:
            return int(m.group(1).replace(',', ''))
        except Exception:
            pass
    m = re.search(r'\b([0-9][0-9,]*)\s*(?:sq(?:uare)?\s*\.?\s*ft\.?|sqft|sf)\b', s, re.I)
    if m:
        try:
            return int(m.group(1).replace(',', ''))
        except Exception:
            pass
    m = re.search(r'\b([0-9][0-9,]{2,})\b(?:\s*(?:sq|sf|ft|feet)\b)', s, re.I)
    if m:
        try:
            return int(m.group(1).replace(',', ''))
        except Exception:
            pass
    return None

def _extract_external_id(details_link: Optional[str], apply_link: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    # AppFolio detail UUID in path
    if details_link:
        m = re.search(r"/listings/detail/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b", details_link, re.I)
        if m:
            return ("appfolio", m.group(1))
    # AppFolio apply listable_uid
    if apply_link:
        try:
            q = urlparse(apply_link)
            qs = parse_qs(q.query)
            uid = (qs.get("listable_uid") or [None])[0]
            if uid and re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", uid, re.I):
                return ("appfolio", uid)
        except Exception:
            pass
    return (None, None)

def _parse_pets(text: Optional[str]) -> Tuple[Optional[bool], Optional[bool]]:
    if not text:
        return (None, None)
    s = (text or "").lower()
    cats_allowed = dogs_allowed = None
    if re.search(r"\b(cat|cats)\s*(allowed|ok|okay|welcome|friendly)\b", s):
        cats_allowed = True
    if re.search(r"\b(dog|dogs)\s*(allowed|ok|okay|welcome|friendly)\b", s):
        dogs_allowed = True
    if re.search(r"\b(no\s*cats|cats?\s*not\s*allowed|cats?\s*prohibited)\b", s):
        cats_allowed = False
    if re.search(r"\b(no\s*dogs|dogs?\s*not\s*allowed|dogs?\s*prohibited)\b", s):
        dogs_allowed = False
    return (cats_allowed, dogs_allowed)

def _has_affirmative(text: Optional[str], include_patterns: List[str], exclude_patterns: Optional[List[str]] = None) -> Optional[bool]:
    if not text:
        return None
    s = (text or "").lower()
    neg_tokens = [
        r"\bno\s+(?:parking\s+on\s+site|on-?site\s+parking)\b",
        r"\bno\s+balcony\b",
        r"\bno\s+patio\b",
        r"\bno\s+deck\b",
        r"\bno\s+controlled\s+access\b",
        r"\bno\s+storage\b",
    ]
    for pat in neg_tokens + (exclude_patterns or []):
        if re.search(pat, s):
            return False
    for pat in include_patterns:
        if re.search(pat, s):
            return True
    return None

# ---------- Wix-specific listing extraction ----------
def extract_element_paths_from_first_row(html: str) -> List[Dict[str, Any]]:
    """
    Extract individual elements from the first listing item.
    Priority:
      1) AppFolio listing-item card → extract ALL meaningful descendant elements
      2) First <table>'s first <tr> with <td>/<th> cells → one element per cell
      3) Wix repeater first card → walk child elements
      4) First generic <tr>
      5) First card-like <div>
    Returns a list of dicts: {index, path, tag, classes, text, href, src, element_html}
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1) AppFolio listing-item card (comprehensive extraction)
    appfolio_card = soup.select_one("div.listing-item, div[class*='listing-item']")
    if appfolio_card:
        elements: List[Dict[str, Any]] = []
        idx = 1
        # Walk all descendants and capture meaningful data
        for elem in appfolio_card.find_all(True):
            if elem.name in ['script', 'style', 'meta', 'link', 'noscript']:
                continue
            
            # Get direct text (not from children), href, src
            # Use get_text with strip=True to get direct text, but check if it has meaningful child tags
            direct_text = elem.find(text=True, recursive=False)
            direct_text = _norm(direct_text.strip()) if direct_text and direct_text.strip() else None
            
            # For elements with meaningful text content, prefer leaf nodes
            # Skip if this element only contains text from child elements (not direct text)
            has_text_children = any(child.name and child.get_text(strip=True) for child in elem.children if hasattr(child, 'name'))
            
            # Get full text only if no text children or this is a leaf
            if has_text_children and not direct_text:
                # Skip this element, we'll get the child instead
                full_text = None
            else:
                full_text = _norm(elem.get_text(strip=True)) if elem.get_text(strip=True) else None
            
            href = elem.get('href')
            src = elem.get('src') or elem.get('data-original')  # AppFolio uses data-original for lazy images
            
            # Skip if no meaningful data
            if not full_text and not href and not src:
                continue
            
            # Build CSS path using class names and tag
            classes = elem.get('class', [])
            tag = elem.name
            # Use first 2 most specific classes
            if classes:
                css_path = f"{tag}.{'.'.join(classes[:2])}"
            else:
                css_path = tag
            
            elements.append({
                "index": idx,
                "path": css_path,
                "tag": tag,
                "classes": " ".join(classes),
                "text": full_text,
                "href": href,
                "src": src,
                "element_html": str(elem)[:200]
            })
            idx += 1
        
        if elements:
            return elements

    # 2) Prefer table row cells
    try:
        table = soup.find("table")
        if table:
            tr = table.find("tr")
            if tr:
                cells = tr.find_all(["td", "th"], recursive=False)
                if not cells:
                    cells = tr.find_all(["td", "th"], recursive=True)
                elements: List[Dict[str, Any]] = []
                for i, td in enumerate(cells, 1):
                    text = _norm(td.get_text(strip=True)) or None
                    a = td.find("a", href=True)
                    img = td.find("img", src=True)
                    href = a.get("href") if a else None
                    src = img.get("src") if img else None
                    if not text and not href and not src:
                        continue
                    elements.append({
                        "index": i,
                        "path": f"tr[1]/{td.name}[{i}]",
                        "tag": td.name,
                        "classes": " ".join(td.get('class', [])),
                        "text": text,
                        "href": href,
                        "src": src,
                        "element_html": str(td)[:200]
                    })
                if elements:
                    return elements
    except Exception:
        pass

    # 3) Wix repeater first card
    cards = soup.select("div.wixui-repeater__item")
    if not cards:
        wrapper = soup.select_one("[class*='wixui-repeater'], [data-testid*='repeater']")
        if wrapper:
            cards = wrapper.select("div.wixui-repeater__item")

    # 4) Fallback to any tr
    if not cards:
        tr_list = soup.select("tr")
        if tr_list:
            first_tr = tr_list[0]
            elements: List[Dict[str, Any]] = []
            cells = first_tr.find_all(["td", "th"]) or []
            for i, td in enumerate(cells, 1):
                text = _norm(td.get_text(strip=True)) or None
                a = td.find("a", href=True)
                img = td.find("img", src=True)
                href = a.get("href") if a else None
                src = img.get("src") if img else None
                if not text and not href and not src:
                    continue
                elements.append({
                    "index": i,
                    "path": f"tr[1]/{td.name}[{i}]",
                    "tag": td.name,
                    "classes": " ".join(td.get('class', [])),
                    "text": text,
                    "href": href,
                    "src": src,
                    "element_html": str(td)[:200]
                })
            if elements:
                return elements

    # 5) Card-like divs
    if not cards:
        cards = soup.select("div[class*='card'], div[class*='item'], div[class*='listing']")
    if not cards:
        return []

    first_card = cards[0]
    elements: List[Dict[str, Any]] = []
    idx = 1
    for elem in first_card.find_all(True):
        if elem.name in ['script', 'style', 'meta', 'link']:
            continue
        
        # Get direct text (not from children)
        direct_text = elem.find(text=True, recursive=False)
        direct_text = _norm(direct_text.strip()) if direct_text and direct_text.strip() else None
        
        # For elements with meaningful text content, prefer leaf nodes
        has_text_children = any(child.name and child.get_text(strip=True) for child in elem.children if hasattr(child, 'name'))
        
        # Get full text only if no text children or this is a leaf
        if has_text_children and not direct_text:
            full_text = None
        else:
            full_text = _norm(elem.get_text(strip=True)) if elem.get_text(strip=True) else None
        
        href = elem.get('href')
        src = elem.get('src')
        if not full_text and not href and not src:
            continue
        # Lightweight path
        classes = elem.get('class', [])
        tag = elem.name
        css_path = f"{tag}.{'.'.join(classes[:2])}" if classes else tag
        elements.append({
            "index": idx,
            "path": css_path,
            "tag": tag,
            "classes": " ".join(classes),
            "text": full_text,
            "href": href,
            "src": src,
            "element_html": str(elem)[:200]
        })
        idx += 1
    return elements

def count_listings_in_html(html: str) -> int:
    """
    Count how many listing items/results are in the HTML.
    Returns the total number of listings found.
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # AppFolio: count listing-item cards
    appfolio_cards = soup.select("div.listing-item, div[class*='listing-item']")
    if appfolio_cards and len(appfolio_cards) > 0:
        return len(appfolio_cards)
    
    # Table: count rows (skip header)
    table = soup.find("table")
    if table:
        rows = table.find_all("tr")
        if rows:
            # Assume first row might be header
            return max(1, len(rows) - 1) if len(rows) > 1 else len(rows)
    
    # Wix repeater: count repeater items
    wix_repeater = soup.select_one('[id*="comp-"][id*="repeater"], div[class*="repeater"]')
    if wix_repeater:
        cards = wix_repeater.find_all("div", recursive=False)
        if cards:
            return len(cards)
    
    # Generic cards
    cards = soup.select("div[class*='card'], div[class*='item'], div[class*='listing']")
    if cards:
        return len(cards)
    
    return 1  # Default to 1 if nothing found

def extract_element_paths_from_nth_result(html: str, result_index: int = 0) -> List[Dict[str, Any]]:
    """
    Extract individual elements from the Nth listing item (0-indexed).
    Similar to extract_element_paths_from_first_row but targets a specific result.
    
    Args:
        html: The HTML to parse
        result_index: Zero-based index of which result to extract (0 = first, 1 = second, etc.)
    
    Returns:
        List of dicts with {index, path, tag, classes, text, href, src, element_html}
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1) AppFolio listing-item cards
    appfolio_cards = soup.select("div.listing-item, div[class*='listing-item']")
    if appfolio_cards and result_index < len(appfolio_cards):
        card = appfolio_cards[result_index]
        elements: List[Dict[str, Any]] = []
        idx = 1
        for elem in card.find_all(True):
            if elem.name in ['script', 'style', 'meta', 'link', 'noscript']:
                continue
            
            # Get direct text (not from children)
            direct_text = elem.find(text=True, recursive=False)
            direct_text = _norm(direct_text.strip()) if direct_text and direct_text.strip() else None
            
            # For elements with meaningful text content, prefer leaf nodes
            has_text_children = any(child.name and child.get_text(strip=True) for child in elem.children if hasattr(child, 'name'))
            
            # Get full text only if no text children or this is a leaf
            if has_text_children and not direct_text:
                full_text = None
            else:
                full_text = _norm(elem.get_text(strip=True)) if elem.get_text(strip=True) else None
            
            href = elem.get('href')
            src = elem.get('src') or elem.get('data-original')
            
            if not full_text and not href and not src:
                continue
            
            classes = elem.get('class', [])
            tag = elem.name
            css_path = f"{tag}.{'.'.join(classes[:2])}" if classes else tag
            
            elements.append({
                "index": idx,
                "path": css_path,
                "tag": tag,
                "classes": " ".join(classes),
                "text": full_text,
                "href": href,
                "src": src,
                "element_html": str(elem)[:200]
            })
            idx += 1
        
        if elements:
            return elements

    # 2) Table rows
    table = soup.find("table")
    if table:
        rows = table.find_all("tr")
        # Skip header row assumption: if result_index=0, use row 1 (or 0 if only one row)
        actual_index = result_index + (1 if len(rows) > 1 else 0)
        if actual_index < len(rows):
            tr = rows[actual_index]
            cells = tr.find_all(["td", "th"], recursive=False) or tr.find_all(["td", "th"], recursive=True)
            elements: List[Dict[str, Any]] = []
            for i, td in enumerate(cells, 1):
                text = _norm(td.get_text(strip=True)) or None
                a = td.find("a", href=True)
                img = td.find("img", src=True)
                href = a.get("href") if a else None
                src = img.get("src") or img.get("data-original") if img else None
                classes = " ".join(td.get("class", []))
                
                elements.append({
                    "index": i,
                    "path": f"tr[{actual_index+1}]/td[{i}]",
                    "tag": td.name,
                    "classes": classes,
                    "text": text,
                    "href": href,
                    "src": src,
                    "element_html": str(td)[:200]
                })
            if elements:
                return elements

    # 3) Wix repeater cards
    wix_repeater = soup.select_one('[id*="comp-"][id*="repeater"], div[class*="repeater"]')
    if wix_repeater:
        cards = wix_repeater.find_all("div", recursive=False)
        if cards and result_index < len(cards):
            card = cards[result_index]
            elements: List[Dict[str, Any]] = []
            idx = 1
            for elem in card.find_all(True):
                if elem.name in ['script', 'style']:
                    continue
                
                # Get direct text (not from children)
                direct_text = elem.find(text=True, recursive=False)
                direct_text = _norm(direct_text.strip()) if direct_text and direct_text.strip() else None
                
                # For elements with meaningful text content, prefer leaf nodes
                has_text_children = any(child.name and child.get_text(strip=True) for child in elem.children if hasattr(child, 'name'))
                
                # Get full text only if no text children or this is a leaf
                if has_text_children and not direct_text:
                    full_text = None
                else:
                    full_text = _norm(elem.get_text(strip=True)) or None
                
                href = elem.get('href')
                src = elem.get('src')
                if not full_text and not href and not src:
                    continue
                
                classes = elem.get('class', [])
                tag = elem.name
                css_path = f"{tag}.{'.'.join(classes[:2])}" if classes else tag
                
                elements.append({
                    "index": idx,
                    "path": css_path,
                    "tag": tag,
                    "classes": " ".join(classes),
                    "text": full_text,
                    "href": href,
                    "src": src,
                    "element_html": str(elem)[:200]
                })
                idx += 1
            if elements:
                return elements

    # 4) Generic cards/items
    cards = soup.select("div[class*='card'], div[class*='item'], div[class*='listing']")
    if cards and result_index < len(cards):
        card = cards[result_index]
        elements: List[Dict[str, Any]] = []
        idx = 1
        for elem in card.find_all(True):
            if elem.name in ['script', 'style']:
                continue
            
            # Get direct text (not from children)
            direct_text = elem.find(text=True, recursive=False)
            direct_text = _norm(direct_text.strip()) if direct_text and direct_text.strip() else None
            
            # For elements with meaningful text content, prefer leaf nodes
            has_text_children = any(child.name and child.get_text(strip=True) for child in elem.children if hasattr(child, 'name'))
            
            # Get full text only if no text children or this is a leaf
            if has_text_children and not direct_text:
                full_text = None
            else:
                full_text = _norm(elem.get_text(strip=True)) or None
            
            href = elem.get('href')
            src = elem.get('src')
            if not full_text and not href and not src:
                continue
            
            classes = elem.get('class', [])
            tag = elem.name
            css_path = f"{tag}.{'.'.join(classes[:2])}" if classes else tag
            
            elements.append({
                "index": idx,
                "path": css_path,
                "tag": tag,
                "classes": " ".join(classes),
                "text": full_text,
                "href": href,
                "src": src,
                "element_html": str(elem)[:200]
            })
            idx += 1
        if elements:
            return elements

    # Fallback: return empty
    return []

def extract_all_listings_locally(html: str, base_url: str) -> List[Dict[str, Any]]:
    """
    Parse Wix repeater cards from the saved HTML.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Wix "All Properties" page uses a repeater; each card is a repeater item.
    cards = soup.select("div.wixui-repeater__item")
    if not cards:
        # fallback: try other repeater patterns
        wrapper = soup.select_one("[class*='wixui-repeater'], [data-testid*='repeater']")
        if wrapper:
            cards = wrapper.select("div.wixui-repeater__item")
    if not cards:
        # Absolute fallback: nothing matched
        cards = []

    out: List[Dict[str, Any]] = []

    for it in cards:
        # Title (usually h2 inside the card)
        title_el = it.select_one("h1, h2, h3, [class*='title']")
        title = _norm(title_el.get_text() if title_el else None)

        # Detail link: anchor to /properties/<slug>
        a_img = it.select_one("a[href*='/properties/']")
        detail_link = urljoin(base_url, a_img.get("href")) if a_img and a_img.get("href") else None

        # Beds
        beds_text_el = None
        for cand in it.select("p, h2, h3, div, span"):
            txt = _norm(getattr(cand, "get_text", lambda: "")())
            if not txt:
                continue
            if re.search(r"\bBR\b", txt) or re.search(r"\bbed\b", txt, re.I):
                beds_text_el = cand
                break
        beds_text = _norm(beds_text_el.get_text()) if beds_text_el else None
        beds: Optional[int] = None
        if beds_text:
            nums = [int(n) for n in re.findall(r"\b(\d+)\s*BR\b", beds_text)]
            if nums:
                beds = max(nums)
            elif re.search(r"\bstudio", beds_text, re.I):
                beds = 0  # studios only

        # Baths
        baths: Optional[float] = None
        bath_label = None
        for cand in it.select("p, h2, h3, div, span"):
            txt = _norm(getattr(cand, "get_text", lambda: "")())
            if txt and re.search(r"\bbath\b", txt, re.I):
                bath_label = cand
                break
        if bath_label:
            sibs = bath_label.find_all_next(True, limit=3)
            for s in sibs:
                val = _norm(getattr(s, "get_text", lambda: "")())
                if val and re.search(r"^\d+(?:\.\d+)?$", val):
                    baths = float(val)
                    break

        # Neighborhood guess (short capitalized phrases not containing BR/Bath)
        neighborhood = None
        for cand in it.select("h2, h3, p, span"):
            txt = _norm(getattr(cand, "get_text", lambda: "")())
            if txt and not re.search(r"\b(BR|Bath)\b", txt) and 2 <= len(txt) <= 30:
                if re.search(r"\b(Hill|Downtown|Fremont|Greenwood|Queen|District|Anne|Side|Seattle)\b", txt):
                    neighborhood = txt
                    break

        # Availability flag
        avail = None
        for cand in it.select("p, span, div"):
            txt = _norm(getattr(cand, "get_text", lambda: "")())
            if txt and re.search(r"\bavailable\b", txt, re.I):
                avail = "Available"
                break

        # Price (rare on list page; try anyway)
        rent = None
        whole_text = _norm(it.get_text()) or ""
        mprice = re.search(r"\$[\d,]+", whole_text)
        if mprice:
            try:
                rent = int(mprice.group(0).replace("$", "").replace(",", ""))
            except Exception:
                pass

        # Images (dedup)
        imgs = []
        for img in it.select("img[src]"):
            src = img.get("src")
            if src:
                imgs.append(urljoin(base_url, src))
        uniq_imgs = []
        seen = set()
        for u in imgs:
            if u not in seen:
                uniq_imgs.append(u)
                seen.add(u)

        if any([title, detail_link, uniq_imgs]):
            out.append({
                "listing_title": title,
                "address": None,
                "city": None, "state": None, "zip": None,
                "rent_amount": rent,
                "beds": beds,
                "baths": baths,
                "sqft": None,
                "availability_date": avail,
                "listing_url": detail_link,
                "details_link": detail_link,
                "apply_now_link": None,
                "external_provider": None,
                "external_id": None,
                "cats_allowed": None,
                "dogs_allowed": None,
                "parking_on_site": None,
                "near_schools": None,
                "balcony_patio_deck": None,
                "controlled_access_building": None,
                "additional_storage_available": None,
                "image_urls": uniq_imgs,
                "local_image_paths": [],
                "description": None,
                "neighborhood": neighborhood
            })

    return out

# ---------- Orchestration pieces used by worker ----------
class NoListingsParsed(Exception):
    pass

REQUEUE_EMPTY_PARSE = "__REQUEUE_EMPTY_PARSE__"

def save_html_fixed(html: str, url: str, source_id: int = 6) -> Path:
    """Save HTML to dated folder as Captures/YYYY-MM-DD/networks_{source_id}.html"""
    date_dir = BASE_DIR / datetime.now().strftime("%Y-%m-%d")
    ensure_dir(date_dir)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"<!-- saved {stamp} from {url} -->\n{html}"
    dated_path = date_dir / f"networks_{source_id}.html"
    dated_path.write_text(content, encoding="utf-8")
    return dated_path

def load_previous_listings_for_base(base_name: str) -> List[Dict[str, Any]]:
    doc = load_global_json(GLOBAL_JSON_PATH)
    try:
        return (doc.get("sources", {}).get(base_name, {}).get("listings")) or []
    except Exception:
        return []

def _fetch_once_or_reuse(url: str, source_id: int = 6) -> Path:
    """
    Check if today's dated capture exists (Captures/YYYY-MM-DD/networks_{source_id}.html).
    If it exists, reuse it. Otherwise fetch and save to dated folder.
    ALWAYS trigger PHP processor after determining the HTML path.
    """
    date_dir = BASE_DIR / datetime.now().strftime("%Y-%m-%d")
    ensure_dir(date_dir)
    dated_path = date_dir / f"networks_{source_id}.html"
    
    file_existed = False
    try:
        if dated_path.exists() and dated_path.stat().st_size > 0:
            log_file(f"Using existing dated capture: {dated_path}")
            file_existed = True
    except Exception:
        pass
    
    if not file_existed:
        # Fetch and save to dated folder
        page_html = http_get(url, timeout=CFG["HTTP_TIMEOUT"])
        dated_path = save_html_fixed(page_html, url, source_id)
        log_file(f"Saved capture → {dated_path}")
    
    # ALWAYS trigger PHP processor (whether new or existing file)
    try:
        log_file(f"[Parser] Triggering PHP processor for HTML: {dated_path}")
        # Import here to avoid circular dependency
        from worker import run_php_processor_for_html
        run_php_processor_for_html(source_id=source_id, html_path=str(dated_path))
    except Exception as e:
        log_file(f"[Parser] PHP processor trigger failed: {e}")
    
    return dated_path

def _stat_tuple(p: Path) -> Tuple[int, float]:
    try:
        st = p.stat()
        return (st.st_size, st.st_mtime)
    except Exception:
        return (0, 0.0)

def _wait_for_capture_update(timeout_sec: int = 120, poll_sec: float = 2.0) -> Optional[Path]:
    """
    After opening Chrome for manual capture, wait up to timeout for either
    PRIMARY_CAPTURE or ALT_CAPTURE to change (size or mtime).
    Returns the path that was updated, or None if unchanged.
    """
    hud_push(f"Waiting up to {timeout_sec}s for updated capture …")
    before_primary = _stat_tuple(PRIMARY_CAPTURE)
    before_alt     = _stat_tuple(ALT_CAPTURE)
    deadline = time.time() + timeout_sec

    while time.time() < deadline:
        time.sleep(poll_sec)
        cur_primary = _stat_tuple(PRIMARY_CAPTURE)
        cur_alt     = _stat_tuple(ALT_CAPTURE)
        if cur_primary != before_primary and cur_primary[0] > 0:
            hud_push("Detected updated network_6.html")
            return PRIMARY_CAPTURE
        if cur_alt != before_alt and cur_alt[0] > 0:
            hud_push("Detected updated networks_6.html")
            return ALT_CAPTURE
    hud_push("No updated capture detected within timeout")
    return None

def run_capture_and_extract(url: str, find_term: str,
                            source_table: Optional[str], source_id: Optional[int],
                            fallback_job_id: int) -> str:
    """
    Behavior:
      1) Save to Captures/YYYY-MM-DD/networks_{source_id}.html (or reuse if exists).
      2) Parse locally with BeautifulSoup (Wix-aware).
      3) If FIRST parse returns 0:
           - Open Chrome for manual capture
           - Wait for capture file to be updated (mtime/size)
           - Re-parse from the updated file
      4) Create/update JSON.
      5) Upload JSON + images via SFTP (even if count is still 0 after retry).
    """
    base_name = f"{(source_table or '').strip() or 'queue_websites'}_{int(source_id if source_id is not None else fallback_job_id)}"
    sid = int(source_id) if source_id is not None else int(fallback_job_id)

    ensure_dir(BASE_DIR); ensure_dir(IMAGES_DIR)
    log_file(f"=== Run started (LOCAL HTML) (url={url}, find='{find_term}', job={base_name}) ===")
    hud_push(f"Run: {base_name}")

    # Step 1: Ensure local dated capture exists (fetch only if missing)
    try:
        capture_path = _fetch_once_or_reuse(url, sid)
    except Exception as e:
        from config_utils import notify_telegram_error
        notify_telegram_error(title="Capture retrieval failed", details=str(e), context=f"{base_name} {url}", throttle=False)
        raise RuntimeError(f"Capture retrieval failed: {e}")

    # Step 2: Read local HTML (optionally select subtree, but still from local file)
    try:
        page_html = capture_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        from config_utils import notify_telegram_error
        notify_telegram_error(title="Local file read failed", details=str(e), context=str(capture_path))
        raise

    try:
        subtree_html = first_match_subtree_html(page_html, url, find_term or "")
    except Exception as e:
        from config_utils import notify_telegram_error
        notify_telegram_error(title="Subtree selection failed", details=str(e), context=base_name)
        subtree_html = page_html

    # Step 3: Parse listings from local HTML (Wix repeater)
    try:
        records = extract_all_listings_locally(subtree_html, url)
    except Exception as e:
        from config_utils import notify_telegram_error
        log_file(f"Local parse error: {e}")
        notify_telegram_error(title="Local HTML parse error", details=str(e), context=base_name)
        hud_push("[ERR] Parse failed")
        raise

    # --- FIELD MAPPING UI ---
    # Always key mappings by the queued job id to avoid collisions between rows that share source_table/source_id
    job_id = int(fallback_job_id)
    job_source = (source_table or 'queue_websites').strip() or 'queue_websites'
    mappings = load_field_mappings()
    job_key = f"{job_source}:{job_id}"
    
    # On first run, if no mapping exists, extract HTML elements from first row and prompt for mapping
    if job_key not in mappings:
        network_id = None
        website = url  # show the queued link explicitly in the UI
        
        # Extract individual HTML elements from the first result row
        try:
            elements = extract_element_paths_from_first_row(subtree_html)
            if elements:
                # Get metadata for the UI
                if records and isinstance(records[0], dict):
                    first_record = records[0]
                    network_id = first_record.get("external_id") or first_record.get("network_id")
                
                # Show HTML element mapping UI
                mapping = prompt_field_mapping(job_id, ("__HTML_ELEMENTS__", elements, network_id, website))
                mappings[job_key] = mapping
                save_field_mappings(mappings)
                
                # Apply element-based mapping to build first record
                mapped = {k: None for k in APARTMENT_LISTING_FIELDS}
                for elem_index, mapping_data in mapping.items():
                    if isinstance(elem_index, int):
                        if isinstance(mapping_data, dict):
                            dest_field = mapping_data.get('field')
                            saved_path = (mapping_data.get('path') or '').strip()
                            value = None
                            if dest_field:
                                if saved_path:
                                    value = _resolve_value_by_path(subtree_html, saved_path, url)
                                if not value:
                                    elem = next((e for e in elements if e['index'] == elem_index), None)
                                    if elem:
                                        value = elem.get('text') or elem.get('href') or elem.get('src')
                                if value:
                                    mapped[dest_field] = value
                        else:
                            # Legacy format: mapping_data is just the field name
                            dest_field = mapping_data
                            if dest_field:
                                elem = next((e for e in elements if e['index'] == elem_index), None)
                                if elem:
                                    value = elem.get('text') or elem.get('href') or elem.get('src')
                                    if value:
                                        mapped[dest_field] = value
                records = [mapped]
            else:
                # Fallback to old field-based mapping if element extraction fails
                if records and isinstance(records[0], dict):
                    first_record = records[0]
                    network_id = first_record.get("external_id") or first_record.get("network_id")
                    website = first_record.get("listing_url") or first_record.get("details_link") or first_record.get("apply_now_link")
                    row_fields = list(first_record.keys())
                else:
                    first_record = None
                    row_fields = []
                mapping = prompt_field_mapping(job_id, (row_fields, first_record, network_id, website))
                mappings[job_key] = mapping
                save_field_mappings(mappings)
                # Apply mapping to the first record only
                mapped = {k: None for k in APARTMENT_LISTING_FIELDS}
                for src_field, dest_field in mapping.items():
                    if dest_field:
                        mapped[dest_field] = first_record.get(src_field) if first_record else None
                records = [mapped]
        except Exception as e:
            log_file(f"Element extraction failed, using fallback: {e}")
            # Fallback to original approach
            if records and isinstance(records[0], dict):
                first_record = records[0]
                network_id = first_record.get("external_id") or first_record.get("network_id")
                website = first_record.get("listing_url") or first_record.get("details_link") or first_record.get("apply_now_link")
                row_fields = list(first_record.keys())
            else:
                first_record = None
                row_fields = []
            mapping = prompt_field_mapping(job_id, (row_fields, first_record, network_id, website))
            mappings[job_key] = mapping
            save_field_mappings(mappings)
            mapped = {k: None for k in APARTMENT_LISTING_FIELDS}
            for src_field, dest_field in mapping.items():
                if dest_field:
                    mapped[dest_field] = first_record.get(src_field) if first_record else None
            records = [mapped]
    else:
        mapping = mappings.get(job_key, {})
        # Check if mapping uses element indices (integer keys) or field names (string keys)
        has_element_indices = any(isinstance(k, int) or (isinstance(k, str) and k.isdigit()) for k in mapping.keys())
        
        if has_element_indices:
            # Element-based mapping: prefer saved CSS path resolution; fallback to index
            try:
                elements = extract_element_paths_from_first_row(subtree_html)
                mapped_records = []
                # For now, only map the first result (can extend to all rows later)
                mapped = {k: None for k in APARTMENT_LISTING_FIELDS}
                for elem_index_str, mapping_data in mapping.items():
                    elem_index = int(elem_index_str) if isinstance(elem_index_str, str) else elem_index_str
                    
                    # New dict format with 'field' and 'path'
                    if isinstance(mapping_data, dict):
                        dest_field = mapping_data.get('field')
                        saved_path = (mapping_data.get('path') or '').strip()
                        value = None
                        if dest_field:
                            # Try path-based resolution first
                            if saved_path:
                                value = _resolve_value_by_path(subtree_html, saved_path, url)
                            # Fallback to index-based element value
                            if not value:
                                elem = next((e for e in elements if e['index'] == elem_index), None)
                                if elem:
                                    value = elem.get('text') or elem.get('href') or elem.get('src')
                            if value:
                                mapped[dest_field] = value
                    else:
                        # Legacy: mapping_data is just the field name
                        dest_field = mapping_data
                        if dest_field:
                            elem = next((e for e in elements if e['index'] == elem_index), None)
                            if elem:
                                value = elem.get('text') or elem.get('href') or elem.get('src')
                                if value:
                                    mapped[dest_field] = value
                mapped_records.append(mapped)
                records = mapped_records
            except Exception as e:
                log_file(f"Element-based mapping application failed: {e}")
                # Keep original records
        else:
            # Legacy field-based mapping
            mapped_records = []
            for rec in (records or []):
                mapped = {k: None for k in APARTMENT_LISTING_FIELDS}
                for src_field, dest_field in mapping.items():
                    if dest_field:
                        mapped[dest_field] = rec.get(src_field)
                mapped_records.append(mapped)
            records = mapped_records

    # Step 3b: If empty, OPEN CHROME (once per run), wait for updated capture, then retry parse
    if not isinstance(records, list) or not records:
        hud_push("[WARN] Initial parse: 0 listings")
        log_file("Parser returned 0 records on first attempt.")
        try:
            launch_manual_browser(url)  # open Chrome/default to let you capture the element
        except Exception:
            pass

        updated = _wait_for_capture_update(timeout_sec=120, poll_sec=2.0)
        if updated:
            try:
                page_html = updated.read_text(encoding="utf-8", errors="ignore")
                subtree_html = first_match_subtree_html(page_html, url, find_term or "")
                records = extract_all_listings_locally(subtree_html, url)
                hud_push(f"Retry parse → {len(records)} listings")
            except Exception as e:
                from config_utils import notify_telegram_error
                log_file(f"Retry parse error: {e}")
                notify_telegram_error(title="Retry parse error", details=str(e), context=base_name)

    # Step 4: Download images and wire local paths (no-op if no images)
    all_urls: List[str] = []
    for rec in (records or []):
        if isinstance(rec, dict):
            urls = rec.get("image_urls") or []
            for u in urls:
                if u:
                    all_urls.append(u)
    dedup_urls: List[str] = []; seen = set()
    for u in all_urls:
        if u not in seen:
            dedup_urls.append(u); seen.add(u)
    saved_image_paths = download_images(dedup_urls, IMAGES_DIR, base_name) if dedup_urls else []
    ptr = 0
    for rec in (records or []):
        if not isinstance(rec, dict):
            continue
        want = len([u for u in (rec.get("image_urls") or []) if u])
        rec["local_image_paths"] = saved_image_paths[ptr:ptr+want]
        ptr += want

    # Step 5: Deltas, upsert, notify — record which capture we used
    capture_path = _current_capture_path()
    previous = load_previous_listings_for_base(base_name)
    new_count, price_updates, removed_count = compute_deltas(previous, records or [])
    upsert_global_source(base_name=base_name, link=url, saved_html=capture_path, images_dir=IMAGES_DIR, listings=(records or []))
    send_telegram_counts(new_count, price_updates, removed_count, base_name, url)

    # Step 6: Upload JSON + images via SFTP (ALWAYS upload after this flow, even if 0)
    if SFTP_ENABLED:
        try:
            sftp_upload_file(
                local_path=Path(GLOBAL_JSON_PATH),
                host=SFTP_HOST, port=SFTP_PORT, user=SFTP_USER, password=SFTP_PASS,
                remote_dir=REMOTE_JSON_DIR,
                remote_name="apartment_listings.json"
            )
        except Exception as e:
            log_file(f"SFTP JSON upload error: {e}")
        try:
            sftp_upload_dir(
                local_dir=IMAGES_DIR,
                host=SFTP_HOST, port=SFTP_PORT, user=SFTP_USER, password=SFTP_PASS,
                remote_dir=REMOTE_IMAGES_PARENT,
                remote_subdir="img"
            )
        except Exception as e:
            log_file(f"SFTP IMAGES upload error: {e}")
    else:
        log_file("SFTP is disabled — skipping uploads (set SFTP_ENABLED=1 to enable).")

    log_file("=== Run completed ===")
    hud_push("✓ Run completed (uploaded)")
    return str(GLOBAL_JSON_PATH.resolve())

# CLI for ad-hoc testing
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description=("Parse listings from local Captures/network_6.html (or networks_6.html). "
                     "If first parse is empty, open Chrome, wait for updated capture, retry, then upload via SFTP.")
    )
    ap.add_argument("url", help="Target source URL (used for absolute links and one-time initial fetch).")
    ap.add_argument("--find", default="", help="CSS selector or term for the listings container.")
    args = ap.parse_args()

    ensure_dir(BASE_DIR); ensure_dir(IMAGES_DIR)
    _fetch_once_or_reuse(args.url)
    path = run_capture_and_extract(args.url, args.find, "cli", None, 0)
    print(json.dumps({"global_json": path}, indent=2))
