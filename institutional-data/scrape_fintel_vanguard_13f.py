#!/usr/bin/env python3
"""
Fintel.io Vanguard 13F Holdings Scraper
=======================================

Scrapes the "13F and Fund Filings" table from:
https://fintel.io/i/vanguard-group

Uses Playwright with realistic browser headers to handle Cloudflare protection.

Expected Columns (based on Fintel.io layout):
- Security (Ticker / Company Name)
- Type
- Avg Share Price
- Shares (MM)
- ΔShares (%)
- Value ($MM)
- ΔShares (%)
- Portfolio (%)
- ΔPortfolio (%)

Installation:
    pip install playwright pandas
    playwright install chromium

Usage:
    python scrape_fintel_vanguard_13f.py

Output:
    - fintel_vanguard_13f.csv (raw data)
    - fintel_vanguard_13f_cleaned.csv (numeric columns converted)

Note: This scraper uses stealth techniques to bypass Cloudflare protection.
      Run on your local machine for best results.

Author: Generated with Claude
Date: February 2026
"""

import pandas as pd
from playwright.sync_api import sync_playwright
import time
from typing import Optional


def scrape_fintel_vanguard(max_retries: int = 3) -> Optional[pd.DataFrame]:
    """
    Scrape Vanguard 13F holdings from Fintel.io

    Args:
        max_retries: Number of retry attempts

    Returns:
        pd.DataFrame with holdings data, or None if scraping fails
    """

    print("=" * 60)
    print("Fintel.io Vanguard 13F Holdings Scraper")
    print("=" * 60)

    for attempt in range(max_retries):
        print(f"\nAttempt {attempt + 1}/{max_retries}")
        print("Starting Playwright browser...")

        try:
            with sync_playwright() as p:
                # Launch browser with stealth settings
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                    ]
                )

                # Create context with realistic browser fingerprint
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/New_York',
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Cache-Control': 'max-age=0',
                    }
                )

                page = context.new_page()

                # Remove webdriver property to avoid detection
                page.add_init_script("""
                    // Remove webdriver property
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });

                    // Mock plugins
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });

                    // Mock languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                """)

                url = "https://fintel.io/i/vanguard-group"
                print(f"Navigating to: {url}")

                # Navigate with longer timeout
                response = page.goto(url, wait_until='domcontentloaded', timeout=60000)
                print(f"Response status: {response.status if response else 'No response'}")

                # Wait for page to fully load
                print("Waiting for page to load...")
                page.wait_for_timeout(5000)

                # Check for Cloudflare challenge
                page_content = page.content()
                if 'challenge' in page_content.lower() or 'cloudflare' in page_content.lower():
                    print("⚠ Cloudflare challenge detected, waiting for resolution...")
                    page.wait_for_timeout(15000)
                    # Check again
                    page_content = page.content()

                # Wait for the table to appear
                print("Looking for 13F table...")
                try:
                    # Look for table with holdings data - try multiple selectors
                    page.wait_for_selector("table", timeout=30000)
                    print("✓ Table found!")
                except Exception as e:
                    print(f"⚠ Table not found with primary selector: {e}")
                    # Try waiting longer
                    page.wait_for_timeout(10000)

                page.wait_for_timeout(3000)

                # Extract table headers - try multiple approaches
                print("\nExtracting table headers...")
                headers = page.eval_on_selector_all(
                    "table thead th",
                    "elements => elements.map(e => e.textContent.trim().replace(/\\s+/g, ' '))"
                )

                if not headers or len(headers) == 0:
                    # Alternative: look for th in first row
                    headers = page.eval_on_selector_all(
                        "table tr:first-child th",
                        "elements => elements.map(e => e.textContent.trim().replace(/\\s+/g, ' '))"
                    )

                if not headers or len(headers) == 0:
                    # Another alternative
                    headers = page.eval_on_selector_all(
                        "table th",
                        "elements => elements.map(e => e.textContent.trim().replace(/\\s+/g, ' '))"
                    )

                print(f"✓ Found {len(headers)} headers: {headers}")

                # Extract row data
                print("Extracting table rows...")
                rows = page.eval_on_selector_all(
                    "table tbody tr",
                    """elements => elements.map(row => {
                        const cells = row.querySelectorAll('td');
                        return Array.from(cells).map(cell => {
                            // Get text content, handling nested elements
                            return cell.textContent.trim().replace(/\\s+/g, ' ');
                        });
                    })"""
                )

                if not rows or len(rows) == 0:
                    # Alternative: get all tr elements after the header
                    rows = page.eval_on_selector_all(
                        "table tr:not(:first-child)",
                        """elements => elements.map(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length === 0) return [];
                            return Array.from(cells).map(cell => {
                                return cell.textContent.trim().replace(/\\s+/g, ' ');
                            });
                        })"""
                    )

                browser.close()

                # Filter out empty rows
                rows = [row for row in rows if row and any(row)]
                print(f"✓ Extracted {len(rows)} rows")

                if not rows:
                    print("⚠ No data rows found")
                    if attempt < max_retries - 1:
                        print("Retrying...")
                        time.sleep(5)
                        continue
                    return None

                # Create DataFrame
                if headers and rows:
                    # Check if headers match row length
                    if len(headers) != len(rows[0]):
                        print(f"⚠ Header count ({len(headers)}) != column count ({len(rows[0])})")
                        # Try to use as many headers as we have columns
                        if len(headers) > len(rows[0]):
                            headers = headers[:len(rows[0])]
                        else:
                            # Add generic headers for extra columns
                            headers = headers + [f"Column_{i}" for i in range(len(headers), len(rows[0]))]

                    df = pd.DataFrame(rows, columns=headers)
                else:
                    df = pd.DataFrame(rows)

                return df

        except Exception as e:
            print(f"✗ Error on attempt {attempt + 1}: {e}")
            import traceback
            traceback.print_exc()
            if attempt < max_retries - 1:
                wait_time = 10 * (attempt + 1)
                print(f"  Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print("All retries exhausted.")
                return None

    return None


def clean_fintel_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and convert scraped data to proper numeric types.

    Handles:
    - Dollar signs ($)
    - Commas in numbers
    - Percentage values
    - Lock icons (🔒) indicating premium data
    """
    df = df.copy()

    for col in df.columns:
        col_lower = col.lower()

        # Skip text columns
        if 'security' in col_lower or col_lower == 'type':
            continue

        print(f"  Cleaning: {col}")

        # Convert to string and remove formatting
        df[col] = (df[col]
                   .astype(str)
                   .str.replace('$', '', regex=False)
                   .str.replace(',', '', regex=False)
                   .str.replace('%', '', regex=False)
                   .str.replace('+', '', regex=False)
                   .str.replace('🔒', '', regex=False)
                   .str.replace('nan', '', regex=False)
                   .str.strip())

        # Convert to numeric
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def main():
    """Main entry point."""

    df = scrape_fintel_vanguard()

    if df is None or df.empty:
        print("\n✗ No data was scraped.")
        print("\nTroubleshooting tips:")
        print("  1. Make sure you're running this on your local machine")
        print("  2. Try running with headless=False to see what's happening")
        print("  3. The site may have rate limiting - wait a few minutes and try again")
        print("  4. Check if fintel.io is accessible in your browser")
        return None

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nTotal rows scraped: {len(df):,}")
    print(f"Columns: {list(df.columns)}")

    print("\nFirst 15 rows:")
    print(df.head(15).to_string())

    if len(df) > 15:
        print("\nLast 10 rows:")
        print(df.tail(10).to_string())

    # Save raw data
    raw_file = "fintel_vanguard_13f.csv"
    df.to_csv(raw_file, index=False)
    print(f"\n✓ Raw data saved to: {raw_file}")

    # Clean and save
    print("\nCleaning numeric columns...")
    df_clean = clean_fintel_dataframe(df)
    clean_file = "fintel_vanguard_13f_cleaned.csv"
    df_clean.to_csv(clean_file, index=False)
    print(f"✓ Cleaned data saved to: {clean_file}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Try to show top holdings by value
    value_cols = [col for col in df_clean.columns if 'value' in col.lower() or 'mm' in col.lower()]
    if value_cols and 'Security' in df_clean.columns:
        print(f"\nTop 5 holdings by {value_cols[0]}:")
        print(df[['Security', value_cols[0]]].head(5).to_string(index=False))

    return df


if __name__ == "__main__":
    main()
