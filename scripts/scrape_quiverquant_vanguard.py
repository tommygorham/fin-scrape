#!/usr/bin/env python3
"""
QuiverQuant Vanguard Portfolio Holdings Scraper
==============================================

Scrapes the "Portfolio Stock Holdings - VANGUARD GROUP INC" table from:
https://www.quiverquant.com/institutions/VANGUARD%20GROUP%20INC/

Uses Playwright for browser automation since the table data is loaded
dynamically via JavaScript.

Installation:
    pip install playwright pandas
    playwright install chromium

Usage:
    python scrape_quiverquant_vanguard.py

Output:
    - vanguard_holdings.csv (raw data)
    - vanguard_holdings_cleaned.csv (with numeric columns converted)

Note: The website displays the top 100 holdings by default. For the full
4000+ holdings, you may need to explore their API or premium features.

Author: Generated with Claude
Date: February 2026
"""

import pandas as pd
from playwright.sync_api import sync_playwright
import sys
from typing import Optional


def scrape_vanguard_holdings() -> Optional[pd.DataFrame]:
    """
    Scrape Vanguard portfolio holdings from QuiverQuant.

    Returns:
        pd.DataFrame: DataFrame containing the portfolio holdings data,
                      or None if scraping fails.

    Columns returned:
        - Stock: Ticker symbol
        - Holdings (Shares): Number of shares held
        - Holdings (USD): Dollar value of holdings
        - % of Portfolio: Percentage of total portfolio
        - Change (Shares): Change in shares from previous filing
        - Change (USD): Change in dollar value
        - % Change: Percentage change
    """

    print("=" * 60)
    print("QuiverQuant Vanguard Holdings Scraper")
    print("=" * 60)
    print("\nStarting Playwright browser...")

    with sync_playwright() as p:
        # Launch headless Chrome
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        url = "https://www.quiverquant.com/institutions/VANGUARD%20GROUP%20INC/"
        print(f"Navigating to: {url}")

        try:
            # Navigate and wait for network to settle
            page.goto(url, wait_until='networkidle', timeout=60000)
            print("Page loaded, waiting for table data...")

            # Initial wait for JavaScript to execute
            page.wait_for_timeout(5000)

            # Wait for table data
            try:
                page.wait_for_selector("table tbody tr td", timeout=30000)
                print("✓ Table found!")
            except Exception:
                print("⚠ Table not found immediately, continuing...")
                page.wait_for_timeout(3000)

            # Extra wait for data to fully render
            page.wait_for_timeout(3000)

            # Extract headers
            print("Extracting table headers...")
            headers = page.eval_on_selector_all(
                "table thead th",
                "elements => elements.map(e => e.textContent.trim())"
            )
            print(f"✓ Found {len(headers)} columns: {headers}")

            # Extract all row data
            print("Extracting table rows...")
            rows = page.eval_on_selector_all(
                "table tbody tr",
                """elements => elements.map(row => {
                    const cells = row.querySelectorAll('td');
                    return Array.from(cells).map(cell => cell.textContent.trim());
                })"""
            )

            browser.close()

            # Filter out empty rows
            rows = [row for row in rows if any(row)]
            print(f"✓ Extracted {len(rows)} rows")

            # Create DataFrame
            if headers and rows:
                if len(headers) == len(rows[0]):
                    df = pd.DataFrame(rows, columns=headers)
                else:
                    print(f"⚠ Header count mismatch, using default columns")
                    df = pd.DataFrame(rows)
            else:
                df = pd.DataFrame(rows)

            return df

        except Exception as e:
            print(f"✗ Error during scraping: {e}")
            browser.close()
            return None


def clean_holdings_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and convert scraped data to proper numeric types.

    Args:
        df: Raw DataFrame from scraper

    Returns:
        pd.DataFrame: Cleaned DataFrame with numeric columns converted
    """

    df = df.copy()

    # Skip the Stock column
    for col in df.columns:
        if col == 'Stock':
            continue

        print(f"  Cleaning column: {col}")

        # Convert to string and remove formatting
        df[col] = (df[col]
                   .astype(str)
                   .str.replace('$', '', regex=False)
                   .str.replace(',', '', regex=False)
                   .str.replace('%', '', regex=False)
                   .str.replace('+', '', regex=False)
                   .str.strip())

        # Handle B/M/K suffixes (billions, millions, thousands)
        def convert_suffix(val):
            if pd.isna(val) or val in ['', 'nan', 'None']:
                return None
            val = str(val).strip()
            try:
                if val.endswith('B'):
                    return float(val[:-1]) * 1e9
                elif val.endswith('M'):
                    return float(val[:-1]) * 1e6
                elif val.endswith('K'):
                    return float(val[:-1]) * 1e3
                else:
                    return float(val)
            except ValueError:
                return None

        df[col] = df[col].apply(convert_suffix)

    return df


def main():
    """Main entry point for the scraper."""

    # Run the scraper
    df = scrape_vanguard_holdings()

    if df is None or df.empty:
        print("\n✗ No data was scraped. Exiting.")
        sys.exit(1)

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nTotal rows scraped: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print("\nFirst 20 rows:")
    print(df.head(20).to_string())

    # Save raw data
    raw_output = "vanguard_holdings.csv"
    df.to_csv(raw_output, index=False)
    print(f"\n✓ Raw data saved to: {raw_output}")

    # Clean and save
    print("\nCleaning data...")
    df_clean = clean_holdings_dataframe(df)
    clean_output = "vanguard_holdings_cleaned.csv"
    df_clean.to_csv(clean_output, index=False)
    print(f"✓ Cleaned data saved to: {clean_output}")

    # Summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nTop 5 holdings by USD value:")
    print(df[['Stock', 'Holdings (USD)']].head(5).to_string(index=False))

    print(f"\nTotal portfolio value (top {len(df)} holdings):")
    if 'Holdings (USD)' in df_clean.columns:
        total_val = df_clean['Holdings (USD)'].sum()
        print(f"  ${total_val:,.0f}")

    return df


if __name__ == "__main__":
    main()
