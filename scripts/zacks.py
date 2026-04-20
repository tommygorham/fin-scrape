import requests
import bs4
import sys
from datetime import datetime
from typing import List, Optional

def make_yahoo_finance_link(ticker: str) -> str:
    """
    Convert a ticker symbol into a clickable terminal link to Yahoo Finance.
    
    Args:
        ticker: Ticker symbol (string)
        
    Returns:
        Formatted string with clickable link for terminals that support 
        OSC 8 hyperlink escape sequences.
    """
    # Clean the ticker symbol (remove any whitespace)
    clean_ticker = ticker.strip()
    
    # Yahoo Finance URL format
    url = f"https://finance.yahoo.com/quote/{clean_ticker}"
    
    # OSC 8 escape sequence format for terminal hyperlinks
    # Format: \033]8;;URL\033\\TEXT\033]8;;\033\\
    clickable = f"\033]8;;{url}\033\\{clean_ticker}\033]8;;\033\\"
    
    return clickable

def fetch_page_content(url: str) -> Optional[str]:
    # Using a User-Agent header is crucial to mimic a browser and avoid being blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}", file=sys.stderr)
        return None

def extract_zacks_tickers(html_content: str) -> List[str]:
    soup = bs4.BeautifulSoup(html_content, "html.parser")
    tickers = []
    target_section = soup.find("section", id="zacks_number_one_rank_additions")
    if not target_section:
        print("Could not find the 'zacks_number_one_rank_additions' section.", file=sys.stderr)
        return []
    # Find all 'a' tags with a 'rel' attribute within the target section.
    ticker_links = target_section.select("a.hoverquote-container-od[rel]")
    for link in ticker_links:
        rel_value = link.get("rel")
        if rel_value:
            # The 'rel' attribute value is a list; we want the first element.
            tickers.append(rel_value[0])
    return tickers

def extract_top_movers(html_content: str) -> List[str]:
    """
    Extract the 5 tickers from the Zacks #1 Rank Top Movers table.
    
    Args:
        html_content: HTML content of the page
        
    Returns:
        List of ticker symbols from the top movers table
    """
    soup = bs4.BeautifulSoup(html_content, "html.parser")
    tickers = []
    
    # Find the top movers section
    top_movers_section = soup.find("section", id="zacks_rank_top_movers")
    if not top_movers_section:
        print("Could not find the 'zacks_rank_top_movers' section.", file=sys.stderr)
        return []
    
    # Find the visible tab (usually the first one - "Value")
    # Look for the div with id="topmovers_value" which is the default visible tab
    value_tab = top_movers_section.find("div", id="topmovers_value")
    if not value_tab:
        # If not found, try to find any visible tab (one without display:none)
        tabs = top_movers_section.find_all("div", class_="ui-tabs-panel")
        for tab in tabs:
            style = tab.get("style", "")
            if "display: none" not in style:
                value_tab = tab
                break
    
    if not value_tab:
        print("Could not find visible tab in top movers section.", file=sys.stderr)
        return []
    
    # Find all ticker links in the table
    ticker_links = value_tab.select("a.hoverquote-container-od[rel]")
    for link in ticker_links[:5]:  # Get only the first 5
        rel_value = link.get("rel")
        if rel_value:
            if isinstance(rel_value, list):
                tickers.append(rel_value[0])
            else:
                tickers.append(rel_value)
    
    return tickers

if __name__ == "__main__":
    ZACKS_URL = "https://www.zacks.com/"
    html_content = fetch_page_content(ZACKS_URL)
    if html_content:
        # Get current date and format as MM-DD-YYYY
        current_date = datetime.now().strftime("%m-%d-%Y")
        scraped_at = datetime.now()

        # Extract and display #1 Rank Additions
        extracted_tickers = extract_zacks_tickers(html_content)
        if extracted_tickers:
            print(f"\n--- Zacks #1 Rank Additions ({current_date}) ---")
            # Sort tickers alphabetically and convert to clickable links
            sorted_tickers = sorted(extracted_tickers)
            for ticker in sorted_tickers:
                clickable_ticker = make_yahoo_finance_link(ticker)
                print(clickable_ticker)
        else:
            print("\nCould not find any tickers in the additions section.")

        # Extract and display Top Movers
        top_movers_tickers = extract_top_movers(html_content)
        if top_movers_tickers:
            print(f"--- Zacks #1 Rank Top Movers ({current_date}) ---")
            # Sort tickers alphabetically and convert to clickable links
            sorted_movers = sorted(top_movers_tickers)
            for ticker in sorted_movers:
                clickable_ticker = make_yahoo_finance_link(ticker)
                print(clickable_ticker)
        else:
            print("\nCould not find any tickers in the top movers section.")

        try:
            import db
            db.insert_zacks_tickers(extracted_tickers, "rank1_addition", scraped_at)
            db.insert_zacks_tickers(top_movers_tickers, "top_mover", scraped_at)
        except Exception as e:
            print(f"Warning: zacks DB insert failed: {e}", file=sys.stderr)
    else:
        print("\nFailed to retrieve webpage. Cannot extract tickers.")
