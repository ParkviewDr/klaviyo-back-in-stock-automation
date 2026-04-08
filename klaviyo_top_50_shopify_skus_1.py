#!/usr/bin/env python3
"""
Klaviyo Back-in-Stock: Specific SKUs Email Export
Retrieves back-in-stock subscribers for your top 50 SKUs from Shopify
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import sys
import time

# Configuration
KLAVIYO_API_KEY = "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE"  # Replace with your pk_* key
OUTPUT_FILENAME = f"klaviyo_top_50_skus_subscribers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
MAX_RECORDS = 2500  # Cap the export at this many records

# Date filter: Get events from the past 2 years
TWO_YEARS_AGO = datetime.now() - timedelta(days=730)

# Your top 50 SKUs from Shopify
TARGET_SKUS = [
    "WUSDS0022",
    "WUSDSDP0094",
    "WUSDSST0186",
    "WUSPDCZ0001",
    "WUSDSPD0792",
    "WUSDSAB154",
    "WUSDSPD0427",
    "WUSW22B6696-DS",
    "WUSYL-W22091",
    "WUS45880-DS",
    "WUSPDCE001M",
    "WUSDSPD0485",
    "WUSDS0032",
    "WUSMA0092M",
    "WUSDSPD0561",
    "WUSDSPD0629",
    "WUSP001",
    "WUSDSAB401PLY",
    "WUS48188",
    "WUSDSPD0357",
    "WUSYL-W230857",
    "WUSYX24Z6031",
    "WUS1726941-942"
]

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
                print(f"✓ Found metric ID: {metric_id}")
                return metric_id
        
        print(f"\n❌ Could not find metric '{metric_name}'")
        return None
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def get_events_for_metric(metric_id):
    """Fetch all events"""
    all_events = []
    url = f"{BASE_URL}/events/"
    
    date_filter = TWO_YEARS_AGO.strftime('%Y-%m-%dT%H:%M:%S')
    
    params = {
        "filter": f"equals(metric_id,\"{metric_id}\"),greater-than(datetime,{date_filter})",
        "page[size]": 100,
    }
    
    print(f"\nFetching events from past 2 years...")
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
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    
    print(f"\n✓ Total events retrieved: {len(all_events)}")
    return all_events


def extract_target_sku_subscribers(events, target_skus):
    """Extract emails for only the specified SKUs"""
    print(f"\nFiltering for your {len(target_skus)} target SKUs...")
    
    data = []
    sku_matches = {}
    
    for event in events:
        attributes = event.get('attributes', {})
        event_properties = attributes.get('event_properties', {})
        
        # Get email
        email = event_properties.get('$email') or event_properties.get('email') or ''
        
        # Get SKU (variant ID) - try multiple possible fields
        sku = (event_properties.get('$variant_id') or 
               event_properties.get('variant') or 
               event_properties.get('variant_id') or 
               event_properties.get('sku') or '')
        
        # Check if this SKU matches any of our target SKUs
        if email and sku:
            # Check for exact match or case-insensitive match
            for target_sku in target_skus:
                if sku.upper() == target_sku.upper():
                    data.append({
                        'SKU': target_sku,  # Use the original format from your list
                        'Email': email
                    })
                    
                    # Track matches
                    if target_sku not in sku_matches:
                        sku_matches[target_sku] = 0
                    sku_matches[target_sku] += 1
                    break
    
    print(f"\n✓ Found subscribers for {len(sku_matches)} of your {len(target_skus)} SKUs")
    print(f"  Total email-SKU pairs: {len(data)}")
    
    # Show which SKUs have subscribers
    if sku_matches:
        print(f"\n  SKUs with subscribers:")
        sorted_matches = sorted(sku_matches.items(), key=lambda x: x[1], reverse=True)
        for sku, count in sorted_matches[:10]:  # Show top 10
            print(f"    {sku}: {count} subscribers")
        if len(sorted_matches) > 10:
            print(f"    ... and {len(sorted_matches) - 10} more")
    
    # Show SKUs with NO subscribers found
    skus_without_subscribers = [sku for sku in target_skus if sku not in sku_matches]
    if skus_without_subscribers:
        print(f"\n  ⚠️  {len(skus_without_subscribers)} SKUs had no back-in-stock subscribers:")
        for sku in skus_without_subscribers[:5]:
            print(f"    {sku}")
        if len(skus_without_subscribers) > 5:
            print(f"    ... and {len(skus_without_subscribers) - 5} more")
    
    return data


def export_to_excel(data, filename, max_records=500):
    """Export to Excel with a cap on number of records"""
    if not data:
        print("\n⚠️  No data to export - none of your target SKUs have back-in-stock subscribers")
        return
    
    df = pd.DataFrame(data)
    
    # Remove duplicates (same email + SKU combination)
    df = df.drop_duplicates()
    
    # Sort by SKU, then by Email
    df = df.sort_values(['SKU', 'Email'])
    
    # Cap at max_records
    total_records = len(df)
    if total_records > max_records:
        print(f"\n⚠️  Found {total_records} records, capping at {max_records}")
        df = df.head(max_records)
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Back in Stock Subscribers')
        
        worksheet = writer.sheets['Back in Stock Subscribers']
        
        # Auto-adjust column widths
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            col_letter = chr(65 + idx)
            worksheet.column_dimensions[col_letter].width = min(max_length, 60)
    
    print(f"\n✓ Excel file created: {filename}")
    print(f"  Total email-SKU pairs exported: {len(df)}")
    if total_records > max_records:
        print(f"  (Capped from {total_records} total records)")
    print(f"  Unique SKUs with subscribers: {df['SKU'].nunique()}")
    print(f"  Unique emails: {df['Email'].nunique()}")


def main():
    print("=" * 70)
    print("Klaviyo Back-in-Stock: Top 50 SKUs from Shopify")
    print("=" * 70)
    print(f"Searching for back-in-stock subscribers for {len(TARGET_SKUS)} SKUs")
    print()
    
    if KLAVIYO_API_KEY == "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE":
        print("❌ Please set your Klaviyo API key")
        sys.exit(1)
    
    metric_id = get_metric_id(BACK_IN_STOCK_METRIC)
    if not metric_id:
        sys.exit(1)
    
    events = get_events_for_metric(metric_id)
    if not events:
        print("\n⚠️  No events found")
        return
    
    target_data = extract_target_sku_subscribers(events, TARGET_SKUS)
    
    export_to_excel(target_data, OUTPUT_FILENAME, max_records=MAX_RECORDS)
    
    print("\n" + "=" * 70)
    print("✓ Export complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
