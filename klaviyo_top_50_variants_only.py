#!/usr/bin/env python3
"""
Klaviyo Top 50 Back-in-Stock Variants
Fetches back-in-stock events and exports ONLY the top 50 most-requested variants
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import sys
import time

# Configuration
KLAVIYO_API_KEY = "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE"
OUTPUT_FILENAME = f"klaviyo_top_50_variants_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

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
    """Get the metric ID for 'Subscribed to Back in Stock'"""
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
        print(f"\n❌ Error fetching metrics: {e}")
        sys.exit(1)


def get_events_for_metric(metric_id):
    """Fetch all events for the metric"""
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


def analyze_top_variants(events, top_n=50):
    """Analyze events and return top N variants by subscriber count"""
    print("\nAnalyzing variant data...")
    
    variant_data = []
    
    for event in events:
        attributes = event.get('attributes', {})
        event_properties = attributes.get('event_properties', {})
        
        variant_id = event_properties.get('$variant_id') or event_properties.get('variant') or ''
        
        if variant_id:
            variant_data.append({
                'Variant ID': variant_id,
                'Product Name': event_properties.get('ProductName') or event_properties.get('$product_title') or '',
                'Product ID': event_properties.get('$product_id') or event_properties.get('product_id') or '',
                'Variant Title': event_properties.get('VariantTitle') or event_properties.get('$variant_title') or '',
                'Email': event_properties.get('$email') or event_properties.get('email') or '',
            })
    
    if not variant_data:
        print("⚠️  No variant data found")
        return None
    
    df = pd.DataFrame(variant_data)
    
    # Group by variant and count
    variant_counts = df.groupby('Variant ID').agg({
        'Email': 'count',
        'Product Name': 'first',
        'Product ID': 'first',
        'Variant Title': 'first',
    }).reset_index()
    
    variant_counts.columns = ['Variant ID', 'Subscriber Count', 'Product Name', 'Product ID', 'Variant Title']
    
    # Sort by subscriber count
    variant_counts = variant_counts.sort_values('Subscriber Count', ascending=False)
    
    # Get top N
    top_variants = variant_counts.head(top_n)
    
    # Add rank
    top_variants.insert(0, 'Rank', range(1, len(top_variants) + 1))
    
    print(f"\n✓ Top {len(top_variants)} variants identified:")
    print(f"  #1: {top_variants.iloc[0]['Subscriber Count']} subscribers - {top_variants.iloc[0]['Variant ID']}")
    if len(top_variants) > 1:
        print(f"  #2: {top_variants.iloc[1]['Subscriber Count']} subscribers - {top_variants.iloc[1]['Variant ID']}")
    if len(top_variants) > 2:
        print(f"  #3: {top_variants.iloc[2]['Subscriber Count']} subscribers - {top_variants.iloc[2]['Variant ID']}")
    
    return top_variants


def export_to_excel(df, filename):
    """Export to Excel"""
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Top 50 Variants')
        
        worksheet = writer.sheets['Top 50 Variants']
        
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            col_letter = chr(65 + idx) if idx < 26 else chr(64 + idx // 26) + chr(65 + idx % 26)
            worksheet.column_dimensions[col_letter].width = min(max_length, 50)
    
    print(f"\n✓ Excel file created: {filename}")


def main():
    print("=" * 60)
    print("Klaviyo Top 50 Back-in-Stock Variants")
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
    
    top_variants = analyze_top_variants(events, top_n=50)
    if top_variants is None or len(top_variants) == 0:
        print("\n⚠️  No variant data to export")
        return
    
    export_to_excel(top_variants, OUTPUT_FILENAME)
    
    print("\n" + "=" * 60)
    print("✓ Export complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
