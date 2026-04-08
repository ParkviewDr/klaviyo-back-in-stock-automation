#!/usr/bin/env python3
"""
Klaviyo Back-in-Stock Subscription Extractor
Fetches back-in-stock subscription data from Klaviyo API and exports to Excel
"""

import requests
import pandas as pd
import datetime
import json
import sys

# Configuration
KLAVIYO_API_KEY = "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE"  # Replace with your pk_* key
OUTPUT_FILENAME = f"klaviyo_back_in_stock_past_year_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

# Date filter: Only get subscriptions from the past year
ONE_YEAR_AGO = datetime.datetime.now() - datetime.timedelta(days=365)

# Klaviyo API Configuration
BASE_URL = "https://a.klaviyo.com/api"
HEADERS = {
    "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
    "revision": "2024-10-15",
    "Accept": "application/json"
}


def get_back_in_stock_subscriptions():
    """
    Fetch back-in-stock subscriptions from Klaviyo (past year only)
    """
    all_subscriptions = []
    url = f"{BASE_URL}/back-in-stock-subscriptions/"
    
    # Format the date filter for Klaviyo API (ISO 8601 format)
    date_filter = ONE_YEAR_AGO.strftime('%Y-%m-%dT%H:%M:%S')
    
    params = {
        "page[size]": 100,  # Max page size
        "filter": f"greater-than(created,{date_filter})"  # Only subscriptions created after this date
    }
    
    print(f"Fetching back-in-stock subscriptions from past year (since {ONE_YEAR_AGO.strftime('%Y-%m-%d')})...")
    page_count = 0
    
    while url:
        try:
            response = requests.get(url, headers=HEADERS, params=params if page_count == 0 else None)
            response.raise_for_status()
            
            data = response.json()
            subscriptions = data.get('data', [])
            all_subscriptions.extend(subscriptions)
            
            page_count += 1
            print(f"  Retrieved page {page_count}: {len(subscriptions)} subscriptions")
            
            # Check for next page
            next_link = data.get('links', {}).get('next')
            url = next_link if next_link else None
            params = None  # Clear params for subsequent requests (use full URL)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("\n❌ Authentication failed. Please check your API key.")
                print("   Make sure you're using a Private API Key (starts with 'pk_')")
            elif e.response.status_code == 403:
                print("\n❌ Access forbidden. Your API key may not have the required permissions.")
            else:
                print(f"\n❌ HTTP Error: {e}")
                print(f"   Response: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error fetching data: {e}")
            sys.exit(1)
    
    print(f"\n✓ Total subscriptions retrieved: {len(all_subscriptions)}")
    return all_subscriptions


def parse_subscription_data(subscriptions):
    """
    Parse subscription data into a clean format for Excel
    """
    parsed_data = []
    
    for sub in subscriptions:
        attributes = sub.get('attributes', {})
        relationships = sub.get('relationships', {})
        
        # Extract profile email (if included)
        profile_data = relationships.get('profile', {}).get('data', {})
        profile_id = profile_data.get('id', '')
        
        # Extract variant data (if included)
        variant_data = relationships.get('variant', {}).get('data', {})
        variant_id = variant_data.get('id', '')
        
        row = {
            'Subscription ID': sub.get('id', ''),
            'Email': attributes.get('email', ''),
            'Phone Number': attributes.get('phone_number', ''),
            'Product Variant ID': variant_id,
            'Channels': ', '.join(attributes.get('channels', [])),
            'Created At': attributes.get('created_at', ''),
            'Updated At': attributes.get('updated_at', ''),
            'Profile ID': profile_id,
            'Custom Metadata': json.dumps(attributes.get('custom_metadata', {})) if attributes.get('custom_metadata') else ''
        }
        
        parsed_data.append(row)
    
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
    date_columns = ['Created At', 'Updated At']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Sort by created date (newest first)
    if 'Created At' in df.columns:
        df = df.sort_values('Created At', ascending=False)
    
    # Write to Excel with formatting
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Back in Stock')
        
        # Get the worksheet
        worksheet = writer.sheets['Back in Stock']
        
        # Auto-adjust column widths
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            ) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
    
    print(f"\n✓ Excel file created: {filename}")
    print(f"  Total rows: {len(df)}")
    print(f"  Date range: {df['Created At'].min()} to {df['Created At'].max()}")


def main():
    """
    Main execution function
    """
    print("=" * 60)
    print("Klaviyo Back-in-Stock Subscription Extractor")
    print("=" * 60)
    print(f"Date Range: {ONE_YEAR_AGO.strftime('%Y-%m-%d')} to {datetime.datetime.now().strftime('%Y-%m-%d')}")
    print()
    
    # Validate API key is set
    if KLAVIYO_API_KEY == "YOUR_KLAVIYO_PRIVATE_API_KEY_HERE":
        print("❌ Please set your Klaviyo API key in the script")
        print("   Edit the KLAVIYO_API_KEY variable at the top of the file")
        sys.exit(1)
    
    # Fetch subscriptions
    subscriptions = get_back_in_stock_subscriptions()
    
    if not subscriptions:
        print("\n⚠️  No back-in-stock subscriptions found")
        return
    
    # Parse the data
    print("\nParsing subscription data...")
    parsed_data = parse_subscription_data(subscriptions)
    
    # Export to Excel
    print("\nExporting to Excel...")
    export_to_excel(parsed_data, OUTPUT_FILENAME)
    
    print("\n" + "=" * 60)
    print("✓ Export complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
