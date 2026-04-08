#!/usr/bin/env python3
"""
Klaviyo Back-in-Stock Event Extractor
Fetches "Subscribed to Back in Stock" events from the past 2 years and exports to Excel
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import sys
import time

# Configuration
KLAVIYO_API_KEY = "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE"  # Replace with your pk_* key
OUTPUT_FILENAME = f"klaviyo_back_in_stock_past_2_years_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

# Date filter: Get events from the past 2 years
TWO_YEARS_AGO = datetime.now() - timedelta(days=730)

# Klaviyo API Configuration
BASE_URL = "https://a.klaviyo.com/api"
HEADERS = {
    "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
    "revision": "2024-10-15",
    "Accept": "application/json"
}

# The metric name for back-in-stock subscriptions
BACK_IN_STOCK_METRIC = "Subscribed to Back in Stock"



def get_metric_id(metric_name):
    """
    Get the metric ID for "Subscribed to Back in Stock"
    """
    url = f"{BASE_URL}/metrics/"
    
    print(f"Looking up metric: '{metric_name}'...")
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        data = response.json()
        metrics = data.get('data', [])
        
        # Find the back-in-stock metric
        for metric in metrics:
            if metric.get('attributes', {}).get('name') == metric_name:
                metric_id = metric.get('id')
                print(f"✓ Found metric ID: {metric_id}")
                return metric_id
        
        print(f"\n❌ Could not find metric '{metric_name}'")
        print("   Make sure you have back-in-stock subscriptions in your Klaviyo account")
        return None
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("\n❌ Authentication failed. Please check your API key.")
            print("   Make sure you're using a Private API Key (starts with 'pk_')")
        else:
            print(f"\n❌ HTTP Error: {e}")
            print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error fetching metrics: {e}")
        sys.exit(1)


def get_events_for_metric(metric_id):
    """
    Fetch all events for the "Subscribed to Back in Stock" metric from the past 2 years
    """
    all_events = []
    url = f"{BASE_URL}/events/"
    
    # Format the date filter for Klaviyo API (ISO 8601 format)
    date_filter = TWO_YEARS_AGO.strftime('%Y-%m-%dT%H:%M:%S')
    
    params = {
        "filter": f"equals(metric_id,\"{metric_id}\"),greater-than(datetime,{date_filter})",
        "page[size]": 100,  # Max page size
        "include": "metric,profile"  # Include related data
    }
    
    print(f"\nFetching back-in-stock events from past 2 years (since {TWO_YEARS_AGO.strftime('%Y-%m-%d')})...")
    page_count = 0
    
    while url:
        try:
            response = requests.get(url, headers=HEADERS, params=params if page_count == 0 else None)
            response.raise_for_status()
            
            data = response.json()
            events = data.get('data', [])
            all_events.extend(events)
            
            page_count += 1
            print(f"  Retrieved page {page_count}: {len(events)} events (Total so far: {len(all_events)})")
            
            # Check for next page
            next_link = data.get('links', {}).get('next')
            url = next_link if next_link else None
            params = None  # Clear params for subsequent requests (use full URL)
            
            # Add a small delay to respect rate limits
            if url:
                time.sleep(0.1)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("\n❌ Authentication failed. Please check your API key.")
                print("   Make sure you're using a Private API Key (starts with 'pk_')")
            elif e.response.status_code == 403:
                print("\n❌ Access forbidden. Your API key may not have the required permissions.")
            elif e.response.status_code == 429:
                print("\n⚠️  Rate limit hit. Waiting 60 seconds before retrying...")
                time.sleep(60)
                continue
            else:
                print(f"\n❌ HTTP Error: {e}")
                print(f"   Response: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error fetching data: {e}")
            sys.exit(1)
    
    print(f"\n✓ Total events retrieved: {len(all_events)}")
    return all_events


def get_profile_details(profile_id):
    """
    Get profile details including email and phone
    """
    url = f"{BASE_URL}/profiles/{profile_id}"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        data = response.json()
        profile_data = data.get('data', {})
        attributes = profile_data.get('attributes', {})
        
        return {
            'email': attributes.get('email', ''),
            'phone': attributes.get('phone_number', ''),
            'first_name': attributes.get('first_name', ''),
            'last_name': attributes.get('last_name', '')
        }
    except:
        return {
            'email': '',
            'phone': '',
            'first_name': '',
            'last_name': ''
        }


def parse_event_data(events):
    """
    Parse event data into a clean format for Excel
    """
    parsed_data = []
    
    print("\nParsing event data and fetching profile details...")
    for idx, event in enumerate(events):
        if (idx + 1) % 50 == 0:
            print(f"  Processed {idx + 1}/{len(events)} events...")
        
        attributes = event.get('attributes', {})
        event_properties = attributes.get('event_properties', {})
        
        # Get profile ID
        relationships = event.get('relationships', {})
        profile_data = relationships.get('profile', {}).get('data', {})
        profile_id = profile_data.get('id', '')
        
        # Extract common back-in-stock properties
        variant_id = event_properties.get('$variant_id') or event_properties.get('variant') or ''
        product_id = event_properties.get('$product_id') or event_properties.get('product_id') or ''
        product_name = event_properties.get('ProductName') or event_properties.get('$product_title') or ''
        variant_title = event_properties.get('VariantTitle') or event_properties.get('$variant_title') or ''
        
        row = {
            'Event ID': event.get('id', ''),
            'Email': event_properties.get('$email') or event_properties.get('email') or '',
            'Phone Number': event_properties.get('$phone_number') or '',
            'Subscription Date': attributes.get('datetime') or attributes.get('timestamp', ''),
            'Product ID': product_id,
            'Product Name': product_name,
            'Variant ID': variant_id,
            'Variant Title': variant_title,
            'Profile ID': profile_id,
            'All Event Properties': json.dumps(event_properties, indent=2)
        }
        
        parsed_data.append(row)
        
        # Small delay every 100 requests to avoid rate limits
        if (idx + 1) % 100 == 0:
            time.sleep(0.5)
    
    print(f"✓ Parsed {len(parsed_data)} events")
    return parsed_data


def export_to_excel(data, filename):
    """
    Export data to Excel with formatting
    """
    if not data:
        print("\n⚠️  No data to export")
        return
    
    df = pd.DataFrame(data)
    
    # Convert timestamp columns to datetime for better Excel formatting
    if 'Subscription Date' in df.columns:
        df['Subscription Date'] = pd.to_datetime(df['Subscription Date'], errors='coerce')
    
    # Sort by subscription date (newest first)
    if 'Subscription Date' in df.columns:
        df = df.sort_values('Subscription Date', ascending=False)
    
    # Remove the 'All Event Properties' column for the main sheet (too verbose)
    df_main = df.drop(columns=['All Event Properties'], errors='ignore')
    
    # Write to Excel with formatting
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Main sheet with clean data
        df_main.to_excel(writer, index=False, sheet_name='Back in Stock Subscriptions')
        
        # Raw data sheet with all properties
        df.to_excel(writer, index=False, sheet_name='Raw Event Data')
        
        # Get the main worksheet
        worksheet = writer.sheets['Back in Stock Subscriptions']
        
        # Auto-adjust column widths
        for idx, col in enumerate(df_main.columns):
            max_length = max(
                df_main[col].astype(str).apply(len).max(),
                len(col)
            ) + 2
            # Convert column index to Excel column letter
            col_letter = chr(65 + idx) if idx < 26 else chr(64 + idx // 26) + chr(65 + idx % 26)
            worksheet.column_dimensions[col_letter].width = min(max_length, 50)
    
    print(f"\n✓ Excel file created: {filename}")
    print(f"  Total rows: {len(df)}")
    if 'Subscription Date' in df.columns:
        print(f"  Date range: {df['Subscription Date'].min()} to {df['Subscription Date'].max()}")
    
    # Print summary statistics
    if 'Email' in df.columns:
        unique_emails = df['Email'].nunique()
        print(f"  Unique subscribers: {unique_emails}")
    
    if 'Product Name' in df.columns:
        unique_products = df[df['Product Name'] != '']['Product Name'].nunique()
        print(f"  Unique products: {unique_products}")
    
    if 'Variant ID' in df.columns:
        unique_variants = df[df['Variant ID'] != '']['Variant ID'].nunique()
        print(f"  Unique variants: {unique_variants}")


def main():
    """
    Main execution function
    """
    print("=" * 60)
    print("Klaviyo Back-in-Stock Event Extractor")
    print("=" * 60)
    print(f"Date Range: {TWO_YEARS_AGO.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
    print()
    
    # Validate API key is set
    if KLAVIYO_API_KEY == "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE":
        print("❌ Please set your Klaviyo API key in the script")
        print("   Edit the KLAVIYO_API_KEY variable at the top of the file")
        sys.exit(1)
    
    # Step 1: Get the metric ID
    metric_id = get_metric_id(BACK_IN_STOCK_METRIC)
    if not metric_id:
        sys.exit(1)
    
    # Step 2: Fetch all events for this metric
    events = get_events_for_metric(metric_id)
    
    if not events:
        print("\n⚠️  No back-in-stock events found in the past 2 years")
        return
    
    # Step 3: Parse the events
    parsed_data = parse_event_data(events)
    
    # Step 4: Export to Excel
    print("\nExporting to Excel...")
    export_to_excel(parsed_data, OUTPUT_FILENAME)
    
    print("\n" + "=" * 60)
    print("✓ Export complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
