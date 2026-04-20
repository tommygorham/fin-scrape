#!/usr/bin/env python3
"""
QuiverQuant Vanguard Portfolio Holdings Scraper - FULL VERSION
==============================================================

Scrapes ALL 4000+ holdings from the "Portfolio Stock Holdings - VANGUARD GROUP INC" table:
https://www.quiverquant.com/institutions/VANGUARD%20GROUP%20INC/

Uses Playwright with infinite scroll handling to load all data.

Installation:
    pip install playwright pandas
    playwright install chromium

Usage:
    python scrape_quiverquant_vanguard_full.py

Output:
    - vanguard_holdings_full.csv (raw data with all holdings)
    - vanguard_holdings_full_cleaned.csv (numeric columns converted)

Author: Generated with Claude
Date: February 2026
"""

import pandas as pd
from playwright.sync_api import sync_playwright
import time
from typing import Optional


def scrape_vanguard_all_holdings(max_retries: int = 3) -> Optional[pd.DataFrame]:
    """
    Scrape ALL Vanguard portfolio holdings by scrolling to trigger lazy loading.

    The website loads data dynamically as you scroll. This function continuously
    scrolls until no more new rows appear.

    Args:
        max_retries: Number of retry attempts if connection fails

    Returns:
        pd.DataFrame with all holdings, or None if scraping fails
    """

    print("=" * 60)
    print("QuiverQuant Vanguard Holdings Scraper (Full - Infinite Scroll)")
    print("=" * 60)

    for attempt in range(max_retries):
        print(f"\nAttempt {attempt + 1}/{max_retries}")
        print("Starting Playwright browser...")

        try:
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()

                url = "https://www.quiverquant.com/institutions/VANGUARD%20GROUP%20INC/"
                print(f"Navigating to: {url}")

                # Load page
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                print("Page loaded, waiting for initial table data...")
                page.wait_for_timeout(8000)

                # Wait for table
                try:
                    page.wait_for_selector("table tbody tr td", timeout=30000)
                    print("✓ Table found!")
                except Exception:
                    print("⚠ Table not found immediately, waiting longer...")
                    page.wait_for_timeout(5000)

                # Extract headers
                print("\nExtracting table headers...")
                headers = page.eval_on_selector_all(
                    "table thead th",
                    "elements => elements.map(e => e.textContent.trim())"
                )
                print(f"✓ Found headers: {headers}")

                # Infinite scroll to load all data
                print("\n" + "-" * 40)
                print("SCROLLING TO LOAD ALL DATA")
                print("(This may take a few minutes for 4000+ rows)")
                print("-" * 40)

                previous_row_count = 0
                scroll_attempts = 0
                max_scroll_attempts = 1000  # Allow many scrolls for 4000+ rows
                no_change_count = 0
                start_time = time.time()

                while scroll_attempts < max_scroll_attempts:
                    # Get current row count
                    current_row_count = page.eval_on_selector_all(
                        "table tbody tr",
                        "elements => elements.length"
                    )

                    if current_row_count > previous_row_count:
                        # Only print every 100 rows or significant changes
                        if current_row_count % 100 < 20 or current_row_count - previous_row_count > 50:
                            elapsed = time.time() - start_time
                            print(f"  {current_row_count:,} rows loaded... ({elapsed:.0f}s elapsed)")
                        previous_row_count = current_row_count
                        no_change_count = 0
                    else:
                        no_change_count += 1

                    # If no new rows after several scrolls, we're done
                    if no_change_count >= 15:
                        elapsed = time.time() - start_time
                        print(f"\n✓ All data loaded! Final count: {current_row_count:,} rows ({elapsed:.0f}s)")
                        break

                    # Multiple scroll strategies for reliability
                    page.evaluate("""
                        // Strategy 1: Scroll window
                        window.scrollBy(0, 800);

                        // Strategy 2: Scroll table container if it exists
                        const table = document.querySelector('table');
                        if (table) {
                            let container = table.closest('div[style*="overflow"], div[class*="scroll"], .table-responsive');
                            if (container) {
                                container.scrollTop += 500;
                            }
                        }
                    """)

                    # Strategy 3: Scroll last row into view
                    page.evaluate("""
                        const rows = document.querySelectorAll('table tbody tr');
                        if (rows.length > 0) {
                            rows[rows.length - 1].scrollIntoView({ block: 'end' });
                        }
                    """)

                    page.wait_for_timeout(200)  # Brief wait between scrolls
                    scroll_attempts += 1

                    # Progress update every 200 scrolls
                    if scroll_attempts % 200 == 0:
                        elapsed = time.time() - start_time
                        print(f"  Progress: {current_row_count:,} rows after {scroll_attempts} scrolls ({elapsed:.0f}s)...")

                # Final wait to ensure everything is rendered
                page.wait_for_timeout(3000)

                # Extract all row data
                print("\nExtracting all table data...")
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
                print(f"✓ Extracted {len(rows):,} total rows")

                # Create DataFrame
                if headers and rows:
                    if len(headers) == len(rows[0]):
                        df = pd.DataFrame(rows, columns=headers)
                    else:
                        print(f"⚠ Header count mismatch")
                        df = pd.DataFrame(rows)
                else:
                    df = pd.DataFrame(rows)

                return df

        except Exception as e:
            print(f"✗ Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 10 * (attempt + 1)  # Increasing backoff
                print(f"  Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print("All retries exhausted.")
                return None

    return None


def clean_holdings_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and convert scraped data to proper numeric types.

    Handles:
    - Dollar signs ($)
    - Commas in numbers
    - Percentage signs (%)
    - Plus/minus signs
    - B/M/K suffixes (billions/millions/thousands)
    """
    df = df.copy()

    for col in df.columns:
        if col == 'Stock':
            continue

        print(f"  Cleaning: {col}")

        # Remove formatting characters
        df[col] = (df[col]
                   .astype(str)
                   .str.replace('$', '', regex=False)
                   .str.replace(',', '', regex=False)
                   .str.replace('%', '', regex=False)
                   .str.replace('+', '', regex=False)
                   .str.strip())

        # Handle B/M/K suffixes
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
    """Main entry point."""

    df = scrape_vanguard_all_holdings()

    if df is None or df.empty:
        print("\n✗ No data was scraped. Please try again later.")
        return None

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nTotal rows scraped: {len(df):,}")
    print(f"Columns: {list(df.columns)}")

    print("\nFirst 10 rows:")
    print(df.head(10).to_string())

    print("\nLast 10 rows:")
    print(df.tail(10).to_string())

    # Save raw data
    raw_file = "vanguard_holdings_full.csv"
    df.to_csv(raw_file, index=False)
    print(f"\n✓ Raw data saved to: {raw_file}")

    # Clean and save
    print("\nCleaning numeric columns...")
    df_clean = clean_holdings_dataframe(df)
    clean_file = "vanguard_holdings_full_cleaned.csv"
    df_clean.to_csv(clean_file, index=False)
    print(f"✓ Cleaned data saved to: {clean_file}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if 'Holdings (USD)' in df_clean.columns:
        total_val = df_clean['Holdings (USD)'].sum()
        print(f"\nTotal portfolio value: ${total_val:,.0f}")

    if '% of Portfolio' in df_clean.columns:
        pct_coverage = df_clean['% of Portfolio'].sum()
        print(f"Portfolio coverage: {pct_coverage:.2f}%")

    print(f"\nTop 5 holdings:")
    print(df[['Stock', 'Holdings (USD)', '% of Portfolio']].head(5).to_string(index=False))

    return df


if __name__ == "__main__":
    main()
