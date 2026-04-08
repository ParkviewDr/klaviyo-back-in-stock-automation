#!/usr/bin/env python3
"""
Klaviyo Back-in-Stock: Top 25 SKUs Email Export
Finds the 25 SKUs with the MOST back-in-stock subscribers and exports their emails
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import sys
import time

# Configuration
KLAVIYO_API_KEY = "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE"  # Replace with your pk_* key
OUTPUT_FILENAME = f"klaviyo_top_25_skus_emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

# Date filter: Get events from the past 2 years
TWO_YEARS_AGO = datetime.now() - timedelta(days=730)

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


def extract_email_sku(events):
    """Extract email and SKU, then find the top 25 SKUs and return their subscribers"""
    print("\nExtracting email and SKU data...")
    
    data = []
    
    for event in events:
        attributes = event.get('attributes', {})
        event_properties = attributes.get('event_properties', {})
        
        # Get email
        email = event_properties.get('$email') or event_properties.get('email') or ''
        
        # Get SKU (variant ID)
        sku = event_properties.get('$variant_id') or event_properties.get('variant') or ''
        
        # Only include if both email and SKU exist
        if email and sku:
            data.append({
                'Email': email,
                'SKU': sku
            })
    
    if not data:
        return None
    
    df = pd.DataFrame(data)
    
    # Remove duplicates (same email + SKU combination)
    df = df.drop_duplicates()
    
    print(f"✓ Extracted {len(df)} email-SKU pairs")
    
    # Find the top 25 SKUs with the most subscribers
    print("\nAnalyzing SKUs to find the top 25...")
    sku_counts = df.groupby('SKU').size().reset_index(name='Subscriber Count')
    sku_counts = sku_counts.sort_values('Subscriber Count', ascending=False)
    
    if len(sku_counts) == 0:
        return None
    
    # Get the top 25 SKUs
    top_25_skus = sku_counts.head(25)['SKU'].tolist()
    
    print(f"\n✓ Top 25 SKUs found:")
    for i, row in sku_counts.head(25).iterrows():
        print(f"  {row['SKU']}: {row['Subscriber Count']} subscribers")
    
    print(f"\n  Total SKUs in top 25: {len(top_25_skus)}")
    
    # Filter data to only include the top 25 SKUs
    top_skus_data = df[df['SKU'].isin(top_25_skus)].copy()
    
    # Sort by SKU for better organization
    top_skus_data = top_skus_data.sort_values('SKU')
    
    return top_skus_data


def export_to_excel(df, filename):
    """Export to Excel"""
    if df is None or len(df) == 0:
        print("\n⚠️  No data to export")
        return
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Top 25 SKUs')
        
        worksheet = writer.sheets['Top 25 SKUs']
        
        # Auto-adjust column widths
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            col_letter = chr(65 + idx)
            worksheet.column_dimensions[col_letter].width = min(max_length, 60)
    
    print(f"\n✓ Excel file created: {filename}")
    print(f"  Total email-SKU pairs: {len(df)}")
    print(f"  Unique SKUs: {df['SKU'].nunique()}")
    print(f"  Unique emails: {df['Email'].nunique()}")


def main():
    print("=" * 60)
    print("Klaviyo Back-in-Stock: Top 25 SKUs Email Export")
    print("=" * 60)
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
    
    top_skus_data = extract_email_sku(events)
    if top_skus_data is None or len(top_skus_data) == 0:
        print("\n⚠️  No email-SKU pairs found")
        return
    
    export_to_excel(top_skus_data, OUTPUT_FILENAME)
    
    print("\n" + "=" * 60)
    print("✓ Export complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
