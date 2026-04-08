#!/usr/bin/env python3
"""
View Klaviyo Export Results
Prints all records from your export file to the command line
"""

import pandas as pd
import glob
import os

def find_latest_export():
    """Find the most recent export file"""
    # Look for Excel files matching the pattern
    files = glob.glob("klaviyo_top_50_skus_subscribers_*.xlsx")
    
    if not files:
        print("ERROR: No export files found in this directory")
        print("   Looking for: klaviyo_top_50_skus_subscribers_*.xlsx")
        return None
    
    # Get the most recent file
    latest_file = max(files, key=os.path.getctime)
    return latest_file


def view_records(filename):
    """Read and display all records from the Excel file"""
    print("=" * 80)
    print(f"Reading file: {filename}")
    print("=" * 80)
    print()
    
    # Read the Excel file
    df = pd.read_excel(filename)
    
    # Display summary
    print(f"Total Records: {len(df)}")
    print(f"Columns: {', '.join(df.columns.tolist())}")
    print()
    
    # Count by SKU
    if 'SKU' in df.columns:
        sku_counts = df['SKU'].value_counts()
        print("Breakdown by SKU:")
        for sku, count in sku_counts.items():
            print(f"  {sku}: {count} subscribers")
        print()
    
    print("=" * 80)
    print("ALL RECORDS:")
    print("=" * 80)
    print()
    
    # Print all records with nice formatting
    # Set pandas to display all rows
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    
    print(df.to_string(index=False))
    
    print()
    print("=" * 80)
    print(f"End of file - Total records shown: {len(df)}")
    print("=" * 80)


def main():
    print()
    print("Klaviyo Export Viewer")
    print()
    
    # Find the latest export file
    filename = find_latest_export()
    
    if not filename:
        print("\nMake sure you're in the same directory as your export file!")
        return
    
    # Display the records
    view_records(filename)


if __name__ == "__main__":
    main()
