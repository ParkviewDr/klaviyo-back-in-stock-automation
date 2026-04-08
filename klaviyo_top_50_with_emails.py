#!/usr/bin/env python3
"""
Klaviyo Back-in-Stock: Top 50 SKUs with Subscriber Emails
Exports SKU + Email for the 50 most-demanded products
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import sys
import time

# Configuration
KLAVIYO_API_KEY = "pk_1983c84a03bab53573a145b739a2b83cb1"  # Replace with your pk_* key
OUTPUT_FILENAME = f"klaviyo_top_50_skus_emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
TOP_N_SKUS = 50  # Number of top SKUs to include

# Date filter: Get events from the past 1 year
ONE_YEAR_AGO = datetime.now() - timedelta(days=365)

# Klaviyo API Configuration
BASE_URL = "https://a.klaviyo.com/api"
HEADERS = {
    "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
    "revision": "2024-10-15",
    "Accept": "application/json"
}

BACK_IN_STOCK_METRIC = "Subscribed to Back in Stock"


def get_metric_id(metric_name):
    """Get the metric ID"""
    url = f"{BASE_URL}/metrics/"
    
    print(f"Looking up metric: '{metric_name}'...")
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        data = response.json()
        metrics = data.get('data', [])
        
        for metric in metrics:
            if metric.get('attributes', {}).get('name') == metric_name:
                metric_id = metric.get('id')
                print(f"SUCCESS: Found metric ID: {metric_id}")
                return metric_id
        
        print(f"\nERROR: Could not find metric '{metric_name}'")
        return None
        
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


def get_profile_email(profile_id):
    """Fetch email for a specific profile ID"""
    url = f"{BASE_URL}/profiles/{profile_id}"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        data = response.json()
        profile_data = data.get('data', {})
        attributes = profile_data.get('attributes', {})
        
        return attributes.get('email', '')
    except:
        return ''


def get_events_for_metric(metric_id):
    """Fetch all events"""
    all_events = []
    url = f"{BASE_URL}/events/"
    
    date_filter = ONE_YEAR_AGO.strftime('%Y-%m-%dT%H:%M:%S')
    
    params = {
        "filter": f"equals(metric_id,\"{metric_id}\"),greater-than(datetime,{date_filter})",
        "page[size]": 100,
    }
    
    print(f"\nFetching events from past year...")
    page_count = 0
    
    while url:
        try:
            response = requests.get(url, headers=HEADERS, params=params if page_count == 0 else None)
            response.raise_for_status()
            
            data = response.json()
            events = data.get('data', [])
            all_events.extend(events)
            
            page_count += 1
            print(f"  Page {page_count}: {len(all_events)} events total")
            
            next_link = data.get('links', {}).get('next')
            url = next_link if next_link else None
            params = None
            
            if url:
                time.sleep(0.1)
            
        except Exception as e:
            print(f"\nERROR: {e}")
            sys.exit(1)
    
    print(f"\nSUCCESS: Total events retrieved: {len(all_events)}")
    return all_events


def get_top_skus(events, top_n):
    """Identify the top N SKUs by subscriber count"""
    print(f"\nIdentifying top {top_n} most-demanded SKUs...")
    
    sku_counts = {}
    
    for event in events:
        attributes = event.get('attributes', {})
        event_properties = attributes.get('event_properties', {})
        sku = event_properties.get('SKU', '')
        
        if sku:
            if sku not in sku_counts:
                sku_counts[sku] = 0
            sku_counts[sku] += 1
    
    # Sort by count and get top N
    sorted_skus = sorted(sku_counts.items(), key=lambda x: x[1], reverse=True)
    top_skus = [sku for sku, count in sorted_skus[:top_n]]
    
    print(f"\nTop {len(top_skus)} SKUs identified:")
    for i, (sku, count) in enumerate(sorted_skus[:10], 1):
        print(f"  #{i}: {sku} - {count} subscribers")
    if len(sorted_skus) > 10:
        print(f"  ... and {len(sorted_skus) - 10} more")
    
    return top_skus


def extract_emails_for_top_skus(events, top_skus):
    """Extract SKU + Email pairs for only the top SKUs"""
    print(f"\nExtracting emails for top {len(top_skus)} SKUs...")
    
    data = []
    profile_cache = {}
    processed = 0
    
    for idx, event in enumerate(events):
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(events)} events... ({len(data)} matches found)")
        
        attributes = event.get('attributes', {})
        event_properties = attributes.get('event_properties', {})
        
        # Get SKU
        sku = event_properties.get('SKU', '')
        
        # Only process if this SKU is in our top list
        if sku not in top_skus:
            continue
        
        # Get profile ID
        relationships = event.get('relationships', {})
        profile_data = relationships.get('profile', {}).get('data', {})
        profile_id = profile_data.get('id', '')
        
        if not profile_id:
            continue
        
        # Get email from profile (use cache)
        if profile_id in profile_cache:
            email = profile_cache[profile_id]
        else:
            email = get_profile_email(profile_id)
            profile_cache[profile_id] = email
            time.sleep(0.05)  # Rate limit protection
        
        # Add to results
        if email and sku:
            data.append({
                'SKU': sku,
                'Email': email
            })
            processed += 1
    
    print(f"\nSUCCESS: Extracted {len(data)} email-SKU pairs for top {len(top_skus)} SKUs")
    return data


def export_to_excel(data, filename):
    """Export to Excel in simple SKU | Email format"""
    if not data:
        print("\n!! No data to export")
        return
    
    df = pd.DataFrame(data)
    
    # Remove duplicates
    df = df.drop_duplicates()
    
    # Sort by SKU
    df = df.sort_values(['SKU', 'Email'])
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Top 50 SKUs Subscribers')
        
        worksheet = writer.sheets['Top 50 SKUs Subscribers']
        
        # Auto-adjust column widths
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            col_letter = chr(65 + idx)
            worksheet.column_dimensions[col_letter].width = min(max_length, 60)
    
    print(f"\nSUCCESS! Excel file created: {filename}")
    print(f"  Total rows: {len(df)}")
    print(f"  Unique SKUs: {df['SKU'].nunique()}")
    print(f"  Unique emails: {df['Email'].nunique()}")


def run_preflight_check():
    """
    Pre-flight diagnostic check - tests everything with a small sample
    Catches issues early before processing all 85K+ events
    """
    print("=" * 70)
    print("PRE-FLIGHT DIAGNOSTIC CHECK")
    print("=" * 70)
    print("Testing API connection and data structure with 10 sample events...")
    print()
    
    # Test 1: API Key Format
    print("[1/5] Checking API key format...")
    if not KLAVIYO_API_KEY.startswith('pk_'):
        print("  WARNING: API key should start with 'pk_'")
    else:
        print("  PASS: API key format looks correct")
    
    # Test 2: Get Metric ID
    print("\n[2/5] Testing metric lookup...")
    try:
        metric_id = get_metric_id(BACK_IN_STOCK_METRIC)
        if not metric_id:
            print("  FAIL: Could not find 'Subscribed to Back in Stock' metric")
            return False
        print(f"  PASS: Found metric ID: {metric_id}")
    except Exception as e:
        print(f"  FAIL: Error getting metric - {e}")
        return False
    
    # Test 3: Fetch Sample Events
    print("\n[3/5] Testing event retrieval (10 samples)...")
    try:
        url = f"{BASE_URL}/events/"
        params = {
            "filter": f"equals(metric_id,\"{metric_id}\")",
            "page[size]": 10,
        }
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        sample_events = data.get('data', [])
        
        if not sample_events:
            print("  FAIL: No events found - back-in-stock may not be active")
            return False
        print(f"  PASS: Retrieved {len(sample_events)} sample events")
    except Exception as e:
        print(f"  FAIL: Error fetching events - {e}")
        return False
    
    # Test 4: Check Data Structure
    print("\n[4/5] Testing data structure...")
    try:
        sku_found = False
        profile_found = False
        
        for event in sample_events[:3]:
            attributes = event.get('attributes', {})
            event_properties = attributes.get('event_properties', {})
            sku = event_properties.get('SKU', '')
            
            relationships = event.get('relationships', {})
            profile_data = relationships.get('profile', {}).get('data', {})
            profile_id = profile_data.get('id', '')
            
            if sku:
                sku_found = True
            if profile_id:
                profile_found = True
        
        if not sku_found:
            print("  FAIL: SKU field not found in events")
            return False
        if not profile_found:
            print("  FAIL: Profile ID not found in events")
            return False
        
        print("  PASS: SKU and Profile ID fields found")
    except Exception as e:
        print(f"  FAIL: Error checking data structure - {e}")
        return False
    
    # Test 5: Test Email Retrieval
    print("\n[5/5] Testing email retrieval from profile...")
    try:
        test_event = sample_events[0]
        relationships = test_event.get('relationships', {})
        profile_data = relationships.get('profile', {}).get('data', {})
        profile_id = profile_data.get('id', '')
        
        if profile_id:
            email = get_profile_email(profile_id)
            if email:
                print(f"  PASS: Successfully retrieved email (hidden for privacy)")
            else:
                print("  WARNING: Profile ID found but email is empty")
        else:
            print("  FAIL: No profile ID to test")
            return False
    except Exception as e:
        print(f"  FAIL: Error retrieving email - {e}")
        return False
    
    # All tests passed!
    print("\n" + "=" * 70)
    print("ALL PRE-FLIGHT CHECKS PASSED!")
    print("=" * 70)
    print("\nProceeding with full data extraction...")
    print()
    time.sleep(1)
    return True


def main():
    print("=" * 70)
    print("Klaviyo Back-in-Stock: Top 50 SKUs with Emails")
    print("=" * 70)
    print()
    
    if KLAVIYO_API_KEY == "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE":
        print("ERROR: Please set your Klaviyo API key")
        sys.exit(1)
    
    # RUN PRE-FLIGHT CHECK FIRST
    if not run_preflight_check():
        print("\n" + "=" * 70)
        print("PRE-FLIGHT CHECK FAILED")
        print("=" * 70)
        print("\nPlease fix the issues above before continuing.")
        print("Run diagnose_klaviyo.py for more detailed diagnostics.")
        sys.exit(1)
    
    metric_id = get_metric_id(BACK_IN_STOCK_METRIC)
    if not metric_id:
        sys.exit(1)
    
    events = get_events_for_metric(metric_id)
    if not events:
        print("\n!! No events found")
        return
    
    # Step 1: Identify top 50 SKUs
    top_skus = get_top_skus(events, TOP_N_SKUS)
    
    if not top_skus:
        print("\n!! No SKUs found")
        return
    
    # Step 2: Get emails for those top 50 SKUs only
    email_data = extract_emails_for_top_skus(events, top_skus)
    
    # Step 3: Export
    export_to_excel(email_data, OUTPUT_FILENAME)
    
    print("\n" + "=" * 70)
    print("EXPORT COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
