#!/usr/bin/env python3
"""
Klaviyo Back-in-Stock: ALL SKUs from Past Year
Retrieves back-in-stock subscribers for ALL products from the past 365 days
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import sys
import time

# Configuration
KLAVIYO_API_KEY = "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE"  # Replace with your pk_* key
OUTPUT_FILENAME = f"klaviyo_all_skus_past_year_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
MAX_RECORDS = 500  # Cap the export at this many records

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
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    
    print(f"\n✓ Total events retrieved: {len(all_events)}")
    return all_events


def extract_all_sku_subscribers(events):
    """Extract emails and SKUs for ALL back-in-stock events"""
    print(f"\nExtracting ALL SKUs from events...")
    
    data = []
    
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
        
        # Include if both email and SKU exist
        if email and sku:
            data.append({
                'SKU': sku,
                'Email': email
            })
    
    print(f"\n✓ Extracted {len(data)} email-SKU pairs")
    
    if not data:
        return []
    
    # Show statistics
    df_temp = pd.DataFrame(data)
    unique_skus = df_temp['SKU'].nunique()
    unique_emails = df_temp['Email'].nunique()
    
    print(f"  Unique SKUs: {unique_skus}")
    print(f"  Unique emails: {unique_emails}")
    
    # Show top 10 SKUs by subscriber count
    print(f"\n  Top 10 SKUs by subscriber count:")
    sku_counts = df_temp.groupby('SKU').size().reset_index(name='Count')
    sku_counts = sku_counts.sort_values('Count', ascending=False)
    
    for i, row in sku_counts.head(10).iterrows():
        print(f"    {row['SKU']}: {row['Count']} subscribers")
    
    return data


def export_to_excel(data, filename, max_records=500):
    """Export to Excel with a cap on number of records"""
    if not data:
        print("\n!! No data to export - no back-in-stock subscribers found")
        return
    
    df = pd.DataFrame(data)
    
    # Remove duplicates (same email + SKU combination)
    df = df.drop_duplicates()
    
    # Sort by SKU, then by Email
    df = df.sort_values(['SKU', 'Email'])
    
    # Cap at max_records
    total_records = len(df)
    if total_records > max_records:
        print(f"\n!! Found {total_records} records, capping at {max_records}")
        df = df.head(max_records)
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='All Back in Stock')
        
        worksheet = writer.sheets['All Back in Stock']
        
        # Auto-adjust column widths
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            col_letter = chr(65 + idx)
            worksheet.column_dimensions[col_letter].width = min(max_length, 60)
    
    print(f"\nSUCCESS! Excel file created: {filename}")
    print(f"  Total email-SKU pairs exported: {len(df)}")
    if total_records > max_records:
        print(f"  (Capped from {total_records} total records)")
    print(f"  Unique SKUs: {df['SKU'].nunique()}")
    print(f"  Unique emails: {df['Email'].nunique()}")


def main():
    print("=" * 70)
    print("Klaviyo Back-in-Stock: ALL SKUs from Past Year")
    print("=" * 70)
    print("Retrieving ALL back-in-stock subscribers (past 365 days)")
    print()
    
    if KLAVIYO_API_KEY == "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE":
        print("ERROR: Please set your Klaviyo API key")
        sys.exit(1)
    
    metric_id = get_metric_id(BACK_IN_STOCK_METRIC)
    if not metric_id:
        sys.exit(1)
    
    events = get_events_for_metric(metric_id)
    if not events:
        print("\n!! No events found")
        return
    
    all_data = extract_all_sku_subscribers(events)
    
    export_to_excel(all_data, OUTPUT_FILENAME, max_records=MAX_RECORDS)
    
    print("\n" + "=" * 70)
    print("EXPORT COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
