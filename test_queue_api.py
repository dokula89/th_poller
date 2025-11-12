#!/usr/bin/env python3
"""
Test the queue API endpoint to verify it works.
"""

import requests
import json

API_URL = "https://api.trustyhousing.com/manual_upload/queue_website_api.php"

def test_api(table="queue_websites", status="queued", limit=10):
    """Test the API with given parameters."""
    
    url = f"{API_URL}?table={table}&status={status}&limit={limit}"
    print(f"\n{'='*60}")
    print(f"Testing API: {url}")
    print(f"{'='*60}\n")
    
    try:
        print("Sending request...")
        response = requests.get(url, timeout=30)
        print(f"✓ Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Request successful\n")
            
            # Try to parse JSON
            try:
                data = response.json()
                print("✓ JSON parsed successfully")
                print(f"\nResponse type: {type(data)}")
                
                # Extract rows
                if isinstance(data, dict):
                    rows = data.get('data', []) or data.get('rows', [])
                    if 'error' in data:
                        print(f"\n⚠ API returned error: {data['error']}")
                        return
                elif isinstance(data, list):
                    rows = data
                else:
                    print(f"\n⚠ Unexpected response type: {type(data)}")
                    return
                
                print(f"\nTotal records: {len(rows)}")
                
                if rows:
                    print(f"\nFirst record:")
                    print(json.dumps(rows[0], indent=2))
                    
                    print(f"\nAll record IDs:")
                    for row in rows[:20]:  # Show first 20
                        print(f"  - ID {row.get('id')}: {row.get('link', row.get('name', 'N/A'))[:50]}")
                    
                    if len(rows) > 20:
                        print(f"  ... and {len(rows) - 20} more")
                else:
                    print(f"\n⚠ No {status} records found in {table}")
                    
            except json.JSONDecodeError as e:
                print(f"\n✗ Failed to parse JSON: {e}")
                print(f"\nResponse text (first 500 chars):")
                print(response.text[:500])
        else:
            print(f"\n✗ Request failed with status {response.status_code}")
            print(f"\nResponse text (first 500 chars):")
            print(response.text[:500])
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out after 30 seconds")
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("QUEUE API TESTER")
    print("="*60)
    
    # Test counts endpoint first
    print("\n" + "="*60)
    print("TESTING COUNTS ENDPOINT")
    print("="*60)
    
    counts_url = f"{API_URL}?table=queue_websites&counts=1"
    print(f"\nURL: {counts_url}")
    
    try:
        response = requests.get(counts_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Counts response: {json.dumps(data, indent=2)}")
        else:
            print(f"✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test different combinations
    print("\n" + "="*60)
    print("TESTING DATA ENDPOINTS")
    print("="*60)
    
    tests = [
        ("queue_websites", "queued"),
        ("queue_websites", "running"),
        ("queue_websites", "done"),
        ("listing_networks", "queued"),
    ]
    
    for table, status in tests:
        test_api(table=table, status=status, limit=10)
        print("\n")
    
    print("\n" + "="*60)
    print("Testing complete!")
    print("="*60)
