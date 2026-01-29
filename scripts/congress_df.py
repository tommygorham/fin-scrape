#!/usr/bin/env python3
"""
Congress Trading Data Extractor
This script fetches the congress trading table from QuiverQuant and converts it
to a pandas DataFrame with key information about each transaction
"""
import argparse
import pandas as pd
import requests
import re
import ast


def fetch_congress_json():
    """
    Fetch congress trading data from embedded JSON in page.

    Returns:
        list: Raw JSON data or None if failed
    """
    url = 'https://www.quiverquant.com/congresstrading/'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching congress data: {e}")
        return None

    # Extract JSON data from page
    # Data format: list of lists with structure:
    # [0]=Ticker, [1]=Company, [2]=Type, [3]=Transaction, [4]=Amount, [5]=Politician,
    # [6]=Chamber, [7]=Party, [8]=FiledDate, [9]=TradeDate, [10]=Notes, ...
    match = re.search(r'let recentTradesData = (\[.*?\]);', resp.text, re.DOTALL)
    if not match:
        print("Could not find congress trades data in page")
        return None

    try:
        return ast.literal_eval(match.group(1))
    except (ValueError, SyntaxError) as e:
        print(f"Parse error: {e}")
        return None


def get_congress_dataframe(purchases_only=False, sort_by_recent_purchases=False):
    """
    Fetch congress trading data and return as DataFrame

    Args:
        purchases_only (bool): If True, filter out all sales transactions
        sort_by_recent_purchases (bool): If True, sort by most recent purchases first

    Returns:
        pandas.DataFrame: Congress trading data
    """
    data = fetch_congress_json()

    if not data:
        return pd.DataFrame()

    # Convert to DataFrame with named columns
    columns = ['Stock', 'Company', 'Type', 'Transaction', 'Amount', 'Politician',
               'Chamber', 'Party', 'Filed', 'Traded', 'Notes', 'ID',
               'Return', 'PoliticianName', 'ImageURL', 'MemberID']
    df = pd.DataFrame(data, columns=columns[:len(data[0])] if data else columns)

    # Keep only relevant columns
    df = df[['Stock', 'Transaction', 'Politician', 'Party', 'Chamber', 'Amount', 'Traded', 'Filed']]

    # Additional processing
    if not df.empty:
        # Convert dates to datetime
        df['Traded'] = pd.to_datetime(df['Traded'], errors='coerce')
        df['Filed'] = pd.to_datetime(df['Filed'], errors='coerce')

        # Filter out invalid tickers
        df = df[df['Stock'].notna() & (df['Stock'] != '-') & (df['Stock'] != '')]

        # Filter out sales if requested
        if purchases_only:
            df = df[df['Transaction'].str.lower() == 'purchase']

        # Sort by most recent trades first if requested
        if sort_by_recent_purchases and not df.empty:
            df = df.sort_values(by='Traded', ascending=False)

    return df

def main():
    """Main function to run the script"""
    parser = argparse.ArgumentParser(description='Extract Congress trading data to DataFrame')
    parser.add_argument('--output', '-o', help='Output CSV file path')
    parser.add_argument('--preview', '-p', action='store_true', help='Preview first 10 rows')
    parser.add_argument('--purchases-only', '-P', action='store_true', 
                        help='Filter out all sales transactions')
    parser.add_argument('--recent-first', '-r', action='store_true', 
                        help='Sort by most recent trades first')
    args = parser.parse_args()
    
    print("Fetching Congress trading data...")
    df = get_congress_dataframe(
        purchases_only=args.purchases_only,
        sort_by_recent_purchases=args.recent_first
    )
    
    if df.empty:
        print("No data found or error occurred.")
        return
        
    print(f"Retrieved {len(df)} Congress trading records.")
    
    if args.purchases_only:
        print("Showing purchases only (sales filtered out).")
    
    if args.recent_first:
        print("Data sorted with most recent trades at the top.")
    
    if args.preview:
        print("\nPreview of data:")
        print(df.head(10))
    
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"Data saved to {args.output}")
    
    return df

if __name__ == '__main__':
    main()
