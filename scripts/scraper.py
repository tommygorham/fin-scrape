import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import re
import json

def fetch_table(url, selector):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    return soup.select_one(selector)

def fetch_insider_json(url):
    """Fetch insider trading data from embedded JSON in page."""
    import ast
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    
    # Extract the data from the JavaScript variable
    match = re.search(r'let recentInsiderTransactionsData = (\[.*?\]);', resp.text, re.DOTALL)
    if match:
        try:
            # Use ast.literal_eval since data uses Python-style single quotes
            return ast.literal_eval(match.group(1))
        except (ValueError, SyntaxError) as e:
            print(f"Parse error: {e}", file=__import__('sys').stderr)
            return None
    return None

def count_insider_transactions_from_json(data):
    """Count insider transactions from JSON data."""
    counts = defaultdict(lambda: [0, 0])
    
    for item in data:
        ticker = item.get('issuerTradingSymbol')
        if not ticker or ticker == '-':
            continue
        
        transaction_code = item.get('transactionCode', '').lower()
        if transaction_code == 'sale':
            counts[ticker][0] += 1
        else:
            counts[ticker][1] += 1
    
    return {k: tuple(v) for k, v in counts.items()}

def parse_rows(table, columns_map):
    data = []
    for tr in table.find_all('tr'):
        cells = tr.find_all('td')
        if not cells:
            continue
        item = {
            name: cells[idx].get_text(strip=True)
            for name, idx in columns_map.items()
        }
        data.append(item)
    return data

def count_transactions(table, ticker_extractor, sale_detector):
    """
    Count sales and purchases by ticker.
    
    Args:
        table: BeautifulSoup table element
        ticker_extractor: Function to extract ticker from a row
        sale_detector: Function to determine if a row is a sale
        
    Returns:
        dict mapping ticker -> (sales_count, purchases_count)
    """
    counts = defaultdict(lambda: [0, 0])
    
    tbody = table.find('tbody')
    if not tbody:
        return {}
        
    for row in tbody.find_all('tr'):
        ticker = ticker_extractor(row)
        if not ticker:
            continue
            
        if sale_detector(row):
            counts[ticker][0] += 1
        else:
            counts[ticker][1] += 1
    
    return {k: tuple(v) for k, v in counts.items()}

# Extractor functions for different sites
def congress_ticker_extractor(row):
    """Extract ticker from congress trading row"""
    tds = row.find_all('td', recursive=False)
    if len(tds) < 1:
        return None
    
    span = (tds[0].find('span', class_='positive') or 
            tds[0].find('span', class_='negative') or 
            tds[0].find('span'))
    
    if not span:
        return None
        
    ticker = span.get_text(strip=True)
    return ticker if ticker != '-' else None

def congress_sale_detector(row):
    """Detect if congress row is a sale"""
    tds = row.find_all('td', recursive=False)
    return len(tds) > 1 and tds[1].find('span', class_='sale') is not None

def insider_ticker_extractor(row):
    """Extract ticker from insider trading row"""
    tds = row.find_all('td')
    if len(tds) >= 2:
        return tds[1].get_text(strip=True)
    return None

def insider_sale_detector(row):
    """Detect if insider row is a sale"""
    tds = row.find_all('td')
    if len(tds) >= 3:
        action_text = tds[2].get_text(strip=True).lower()
        return action_text == 'sale'
    return False
