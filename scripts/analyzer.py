import sys
import os
import pandas as pd
from collections import defaultdict
import argparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import ast

CONFIG = {
    'insider': {
        'title': 'insider',
        'prefix': 'insider_trading',
        'csv': 'insider_trading_data.csv'
    },
    'congress': {
        'title': 'congress',
        'prefix': 'congress_trading',
        'csv': 'congress_trading_data.csv'
    }
}

def make_qq_links(tickers):
    clickable_tickers = []
    for ticker in tickers:
        clean_ticker = ticker.strip()
        url = f"https://www.quiverquant.com/stock/{clean_ticker}"
        clickable = f"\033]8;;{url}\033\\{clean_ticker}\033]8;;\033\\"
        clickable_tickers.append(clickable)
    return clickable_tickers

def make_yahoo_finance_links(tickers):
    """
    Convert a list of ticker symbols into clickable terminal links to Yahoo Finance.
    
    Args:
        tickers: List of ticker symbols (strings)
        
    Returns:
        List of formatted strings with clickable links for terminals that support 
        OSC 8 hyperlink escape sequences.
    """
    clickable_tickers = []
    
    for ticker in tickers:
        # Clean the ticker symbol (remove any whitespace)
        clean_ticker = ticker.strip()
        
        # Yahoo Finance URL format
        #url = f"https://finance.yahoo.com/quote/{clean_ticker}"
        url = f"https://www.quiverquant.com/stock/{clean_ticker}"
        # OSC 8 escape sequence format for terminal hyperlinks
        # Format: \033]8;;URL\033\\TEXT\033]8;;\033\\
        clickable = f"\033]8;;{url}\033\\{clean_ticker}\033]8;;\033\\"
        
        clickable_tickers.append(clickable)
    
    return clickable_tickers

def make_yahoo_finance_link(ticker):
    """
    Convert a single ticker symbol into a clickable terminal link to Yahoo Finance.
    """
    clean_ticker = ticker.strip()
    #url = f"https://finance.yahoo.com/quote/{clean_ticker}"
    url = f"https://www.quiverquant.com/stock/{clean_ticker}"
    return f"\033]8;;{url}\033\\{clean_ticker}\033]8;;\033\\"

def fetch_table(url, selector):
    """Fetch HTML table from URL"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        return soup.select_one(selector)
    except Exception as e:
        print(f"Error fetching table: {e}", file=sys.stderr)
        return None

def extract_congress_data(table):
    """
    Extract data from congress trading table into structured format.
    
    Returns:
        List of dictionaries containing transaction data
    """
    data = []
    
    if not table:
        return data
        
    tbody = table.find('tbody')
    if not tbody:
        return data
    
    for row in tbody.find_all('tr'):
        try:
            cells = row.find_all('td', recursive=False)
            if len(cells) < 5:  # Ensure we have enough cells
                continue
                
            # Extract ticker
            ticker_span = (cells[0].find('span', class_='positive') or 
                          cells[0].find('span', class_='negative') or 
                          cells[0].find('span'))
            ticker = ticker_span.get_text(strip=True) if ticker_span else None
            if ticker == '-' or not ticker:
                continue
                
            # Extract transaction type
            transaction_span = cells[1].find('span')
            transaction = transaction_span.get_text(strip=True) if transaction_span else None
            
            # Extract politician name
            politician = cells[2].get_text(strip=True)
            
            # Extract filing date
            filed_date = cells[3].get_text(strip=True)
            
            # Extract trade date
            trade_date = cells[4].get_text(strip=True)
            
            # Create data entry
            entry = {
                'Stock': ticker,
                'Transaction': transaction,
                'Politician': politician,
                'Filed': filed_date,
                'Traded': trade_date
            }
            
            data.append(entry)
            
        except Exception as e:
            print(f"Error parsing row: {e}", file=sys.stderr)
            continue
            
    return data

def fetch_insider_purchases_df(sort_by='trade', dedup=True):
    """
    Fetch recent insider purchases as a DataFrame, sorted by date (most recent
    first) and optionally deduplicated by ticker.

    Args:
        sort_by: 'trade' for transaction date, 'file' for filing date
        dedup: If True, keep only the most recent transaction per ticker

    Returns:
        pandas.DataFrame: Insider purchase rows (empty if fetch/parse failed)
    """
    url = 'https://www.quiverquant.com/insiders/'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching insider data: {e}", file=sys.stderr)
        return pd.DataFrame()

    # Extract JSON data from page
    match = re.search(r'let recentInsiderTransactionsData = (\[.*?\]);', resp.text, re.DOTALL)
    if not match:
        print("Could not find insider transactions data", file=sys.stderr)
        return pd.DataFrame()

    try:
        data = ast.literal_eval(match.group(1))
    except (ValueError, SyntaxError) as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return pd.DataFrame()

    # Filter for purchases only
    purchases = [item for item in data if item.get('transactionCode', '').lower() == 'purchase']

    if not purchases:
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(purchases)

    # Parse dates
    df['transactionDate'] = pd.to_datetime(df['transactionDate'], format='%b %d, %Y', errors='coerce')
    # fileDate format: "Jan 26, 2026 (02:46 PM)" - extract just the date part
    df['fileDate'] = df['fileDate'].str.extract(r'^([A-Za-z]+ \d+, \d+)')[0]
    df['fileDate'] = pd.to_datetime(df['fileDate'], format='%b %d, %Y', errors='coerce')

    # Sort by selected date column (most recent first)
    sort_col = 'transactionDate' if sort_by == 'trade' else 'fileDate'
    df = df.sort_values(by=sort_col, ascending=False)

    # Deduplicate by ticker if requested (keep most recent)
    if dedup:
        df = df.drop_duplicates(subset=['issuerTradingSymbol'], keep='first')

    return df


def format_insider_purchases(df):
    """
    Format the top insider purchases into clickable terminal display lines.

    Args:
        df: DataFrame returned by fetch_insider_purchases_df()

    Returns:
        List of formatted strings for recent insider purchases
    """
    if df is None or df.empty:
        return []

    # Get recent purchases (top 20)
    recent_purchases = []
    for _, row in df.head(20).iterrows():
        ticker = row['issuerTradingSymbol']
        if not ticker or ticker == '-':
            continue

        # Format the date
        try:
            if pd.notna(row['transactionDate']):
                formatted_date = row['transactionDate'].strftime('%Y-%m-%d')
            else:
                formatted_date = 'Unknown'
        except:
            formatted_date = 'Unknown'

        # Create clickable ticker link
        clickable_ticker = make_yahoo_finance_link(ticker)

        # Format owner name (truncate if too long)
        owner = row.get('rptOwnerName', 'Unknown')[:30]

        # Format transaction value
        value = pd.to_numeric(row.get('transactionValue', 0), errors='coerce')
        if pd.notna(value) and value > 0:
            formatted_value = f"${value:,.0f}"
        else:
            formatted_value = "N/A"

        formatted_line = f"{clickable_ticker:<8} {formatted_value:>15}    {owner:<30}    {formatted_date}"
        recent_purchases.append(formatted_line)

    return recent_purchases


def get_recent_insider_purchases(sort_by='trade', dedup=True):
    """
    Fetch recent insider purchases sorted by transaction or file date.

    Args:
        sort_by: 'trade' for transaction date, 'file' for filing date
        dedup: If True, show only the most recent transaction per ticker

    Returns:
        List of formatted strings for recent insider purchases
    """
    return format_insider_purchases(fetch_insider_purchases_df(sort_by=sort_by, dedup=dedup))


def write_insider_tickers(df):
    """
    Write all scraped insider purchase tickers to data/insidertickers.txt.

    Tickers are written on a single line, separated by one space, ordered by
    trade date (most recent first, matching the DataFrame order) and
    deduplicated. Overwrites the file if it already exists. Does nothing when
    the DataFrame is empty so a failed scrape never wipes a good file.

    Args:
        df (pandas.DataFrame): Insider purchases DataFrame with an
            'issuerTradingSymbol' column.
    """
    if df is None or df.empty:
        return

    # Drop blank/placeholder tickers, then dedup while preserving order.
    tickers = [t for t in df['issuerTradingSymbol'].tolist() if t and t != '-']
    tickers = list(dict.fromkeys(tickers))

    # data/ lives one level up from this script's scripts/ directory,
    # so the path is correct regardless of the caller's working directory.
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, 'insidertickers.txt')

    with open(out_path, 'w') as f:
        f.write(' '.join(tickers) + '\n')

    print(f"Wrote {len(tickers)} insider tickers to {out_path}", file=sys.stderr)


def get_recent_congress_purchases(sort_by='trade', dedup=True):
    """
    Fetch recent congress purchases from embedded JSON data.

    Args:
        sort_by: 'trade' for trade date, 'file' for filing date
        dedup: If True, show only the most recent transaction per ticker

    Returns:
        List of formatted strings for recent congress purchases
    """
    url = 'https://www.quiverquant.com/congresstrading/'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching congress data: {e}", file=sys.stderr)
        return []

    # Extract JSON data from page
    # Data format: list of lists with structure:
    # [0]=Ticker, [1]=Company, [2]=Type, [3]=Transaction, [4]=Amount, [5]=Politician,
    # [6]=Chamber, [7]=Party, [8]=FiledDate, [9]=TradeDate, [10]=Notes, ...
    match = re.search(r'let recentTradesData = (\[.*?\]);', resp.text, re.DOTALL)
    if not match:
        print("Could not find congress trades data", file=sys.stderr)
        return []

    try:
        data = ast.literal_eval(match.group(1))
    except (ValueError, SyntaxError) as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return []

    if not data:
        return []

    # Convert to DataFrame with named columns
    columns = ['Ticker', 'Company', 'Type', 'Transaction', 'Amount', 'Politician',
               'Chamber', 'Party', 'FiledDate', 'TradeDate', 'Notes', 'ID',
               'Return', 'PoliticianName', 'ImageURL', 'MemberID']
    df = pd.DataFrame(data, columns=columns[:len(data[0])] if data else columns)

    # Filter for purchases only
    df = df[df['Transaction'].str.lower() == 'purchase']

    if df.empty:
        return []

    # Parse dates
    df['TradeDate'] = pd.to_datetime(df['TradeDate'], errors='coerce')
    df['FiledDate'] = pd.to_datetime(df['FiledDate'], errors='coerce')

    # Sort by selected date column (most recent first)
    sort_col = 'TradeDate' if sort_by == 'trade' else 'FiledDate'
    df = df.sort_values(by=sort_col, ascending=False)

    # Deduplicate by ticker if requested (keep most recent)
    if dedup:
        df = df.drop_duplicates(subset=['Ticker'], keep='first')

    # Get recent purchases (top 20)
    recent_purchases = []
    for _, row in df.head(20).iterrows():
        ticker = row['Ticker']
        if not ticker or ticker == '-':
            continue

        # Format the date
        try:
            if pd.notna(row['TradeDate']):
                formatted_date = row['TradeDate'].strftime('%Y-%m-%d')
            else:
                formatted_date = 'Unknown'
        except:
            formatted_date = 'Unknown'

        # Create clickable ticker link
        clickable_ticker = make_yahoo_finance_link(ticker)

        # Format politician name (truncate if too long)
        politician = str(row.get('Politician', 'Unknown'))[:25]

        # Format amount range
        amount = row.get('Amount', 'N/A')

        # Include party affiliation
        party = row.get('Party', '')
        party_str = f"({party})" if party else ""

        formatted_line = f"{clickable_ticker:<8} {amount:<25} {politician:<25} {party_str:<4} {formatted_date}"
        recent_purchases.append(formatted_line)

    return recent_purchases

def parse_ticker_data(input_file=None):
    """Parse ticker data from file or stdin and return as a dictionary."""
    ticker_data = []
    
    # Read from file if specified, otherwise from stdin
    lines = []
    if input_file:
        with open(input_file, 'r') as f:
            lines = f.readlines()
    else:
        lines = sys.stdin.readlines()
    
    # Process each line
    for line in lines:
        try:
            line = line.strip()
            if not line or line.startswith("---") or line.startswith("python"):
                continue
                
            # Parse the line: ticker purchases
            parts = line.split()
            
            if len(parts) == 2:
                # Standard case: ticker purchases
                ticker = parts[0]
                purchases = int(parts[1])
            else:
                # Handle tickers with spaces
                if parts and parts[-1].isdigit():
                    ticker = ' '.join(parts[:-1])
                    purchases = int(parts[-1])
                else:
                    print(f"Warning: Invalid format in line: {line}", file=sys.stderr)
                    continue
                
            ticker_data.append({
                'ticker': ticker,
                'purchases': purchases
            })
        except ValueError as e:
            print(f"Warning: Could not parse numbers in line: {line} - {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Warning: Error processing line: {line} - {e}", file=sys.stderr)
            continue
    
    return ticker_data

def analyze_ticker_data(ticker_data):
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(ticker_data)
    
    if df.empty:
        return {
            'dataframe': df,
            'total_purchases': 0,
            'most_purchases': None,
            'purchases_sorted': df
        }
    
    # Calculate totals
    total_purchases = df['purchases'].sum()
    
    # Find ticker with most purchases
    most_purchases = df.loc[df['purchases'].idxmax()] if not df['purchases'].empty else None
    
    # Sort by purchases
    purchases_sorted = df.sort_values('purchases', ascending=False)
    
    return {
        'dataframe': df,
        'total_purchases': total_purchases,
        'most_purchases': most_purchases,
        'purchases_sorted': purchases_sorted
    }

def print_summary(analysis, cfg):
    """Print a summary of the analysis with clickable Yahoo Finance links."""
    # Get current date and format as MM-DD-YYYY
    current_date = datetime.now().strftime("%m-%d-%Y")

    # Get sort and dedup options from config
    sort_by = cfg.get('sort_by', 'trade')
    dedup = cfg.get('dedup', True)

    sort_label = "by trade date" if sort_by == 'trade' else "by file date"
    dedup_label = "" if dedup else " (all transactions)"

    print(f"--- Recent {cfg['title'].capitalize()} Purchases {sort_label}{dedup_label} ({current_date}) ---")

    if cfg['title'] == 'congress':
        recent_purchases = get_recent_congress_purchases(sort_by=sort_by, dedup=dedup)
    else:
        # Fetch once: persist all scraped insider tickers, then display the top rows.
        insider_df = fetch_insider_purchases_df(sort_by=sort_by, dedup=dedup)
        write_insider_tickers(insider_df)
        recent_purchases = format_insider_purchases(insider_df)

    for purchase in recent_purchases:
        print(purchase)

def export_data(analysis, cfg):
    """Export the analyzed data to a CSV file."""
    output_file = cfg['csv']
    analysis['dataframe'].to_csv(output_file, index=False)
    #print(f"\nData exported to {output_file}")

def main():
    """Main function to run the analysis."""
    p = argparse.ArgumentParser(description='Analyze trading purchase data')
    p.add_argument('source', choices=CONFIG.keys(), help='Which dataset to analyze')
    p.add_argument('input_file', nargs='?', help='Input file (reads from stdin if not provided)')
    p.add_argument('--sort-by', choices=['trade', 'file'], default='trade',
                   help='Sort by trade date or file date (default: trade)')
    p.add_argument('--no-dedup', action='store_true',
                   help='Show all transactions (do not deduplicate by ticker)')
    args = p.parse_args()
    cfg = CONFIG[args.source]
    cfg['sort_by'] = args.sort_by
    cfg['dedup'] = not args.no_dedup
    
    if args.input_file:
        ticker_data = parse_ticker_data(args.input_file)
    else:
        ticker_data = parse_ticker_data()
    
    analysis = analyze_ticker_data(ticker_data)
    print_summary(analysis, cfg)
    
    try:
        export_data(analysis, cfg)
    except Exception as e:
        print(f"Error exporting data: {e}", file=sys.stderr)
        print("Summary analysis completed without data export.", file=sys.stderr)

if __name__ == "__main__":
    main()
