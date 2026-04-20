#!/usr/bin/env python3
"""
Fintel.io Vanguard 13F Holdings Scraper
=======================================

Scrapes the "13F and Fund Filings" table from:
https://fintel.io/i/vanguard-group

Installation:
    pip install playwright pandas playwright-stealth
    playwright install chromium

Usage:
    python scrape_fintel_vanguard_13f.py
"""

import pandas as pd
from playwright.sync_api import sync_playwright
import time
from typing import Optional

##############################################################################
# CONFIGURATION
##############################################################################

HEADLESS_MODE = True   # Set False to see browser & solve Cloudflare manually
MAX_RETRIES = 3

##############################################################################

# Import playwright-stealth properly
STEALTH_AVAILABLE = False
StealthClass = None

try:
    from playwright_stealth import Stealth
    StealthClass = Stealth
    STEALTH_AVAILABLE = True
    print("✓ playwright-stealth Stealth class loaded")
except ImportError as e:
    print(f"⚠️  playwright-stealth not available: {e}")

print("=" * 60)
print("ENVIRONMENT CHECK")
print("=" * 60)
print(f"playwright-stealth available: {STEALTH_AVAILABLE}")
print(f"Headless mode requested: {HEADLESS_MODE}")

if HEADLESS_MODE and not STEALTH_AVAILABLE:
    print("\n⚠️  WARNING: Headless mode requires playwright-stealth")
    print("   Falling back to non-headless mode")
    HEADLESS_MODE = False

print(f"Actual headless mode: {HEADLESS_MODE}")
print("=" * 60)


def scrape_fintel_vanguard() -> Optional[pd.DataFrame]:
    """Scrape Vanguard 13F holdings from Fintel.io"""

    print("\n" + "=" * 60)
    print("Fintel.io Vanguard 13F Holdings Scraper")
    print("=" * 60)

    for attempt in range(MAX_RETRIES):
        print(f"\n--- Attempt {attempt + 1}/{MAX_RETRIES} ---")
        print("Starting browser...")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=HEADLESS_MODE,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                    ]
                )

                # Create context normally
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/New_York',
                )

                # Create page
                page = context.new_page()

                # Apply stealth to the page if available
                if STEALTH_AVAILABLE and StealthClass:
                    print("Applying stealth to page...")
                    stealth_instance = StealthClass()
                    stealth_instance.apply_stealth_sync(page)
                    print("✓ Stealth applied")

                url = "https://fintel.io/i/vanguard-group"
                print(f"Navigating to: {url}")

                response = page.goto(url, wait_until='domcontentloaded', timeout=60000)
                print(f"Response status: {response.status if response else 'None'}")

                page.wait_for_timeout(5000)

                # Check for Cloudflare
                content = page.content().lower()
                if 'cloudflare' in content or 'challenge' in content or 'please unblock' in content:
                    print("\n⚠️  Cloudflare challenge detected!")

                    if HEADLESS_MODE:
                        print("Cannot solve in headless mode.")
                        print("Edit script: set HEADLESS_MODE = False")
                        browser.close()
                        return None
                    else:
                        print(">>> Solve the challenge in the browser window <<<")
                        print("Waiting up to 2 minutes...")
                        try:
                            page.wait_for_selector("table", timeout=120000)
                            print("✓ Challenge solved!")
                        except:
                            print("✗ Timeout")
                            browser.close()
                            continue

                # Wait for table
                print("Looking for table...")
                try:
                    page.wait_for_selector("table", timeout=30000)
                    print("✓ Table found!")
                except:
                    print("✗ Table not found")
                    browser.close()
                    continue

                page.wait_for_timeout(2000)

                # Extract headers
                print("Extracting headers...")
                headers = page.eval_on_selector_all(
                    "table thead th",
                    "els => els.map(e => e.textContent.trim().replace(/\\s+/g, ' '))"
                )
                print(f"Headers ({len(headers)}): {headers}")

                # Extract rows
                print("Extracting rows...")
                rows = page.eval_on_selector_all(
                    "table tbody tr",
                    """els => els.map(row => {
                        const cells = row.querySelectorAll('td');
                        return Array.from(cells).map(c => c.textContent.trim().replace(/\\s+/g, ' '));
                    })"""
                )

                browser.close()

                rows = [r for r in rows if r and any(r)]
                print(f"✓ Extracted {len(rows)} rows")

                if not rows:
                    continue

                if headers and len(headers) == len(rows[0]):
                    df = pd.DataFrame(rows, columns=headers)
                else:
                    df = pd.DataFrame(rows)

                return df

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            if attempt < MAX_RETRIES - 1:
                time.sleep(10)

    return None


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean numeric columns"""
    df = df.copy()
    for col in df.columns:
        if 'security' in col.lower() or col.lower() == 'type':
            continue
        df[col] = (df[col].astype(str)
                   .str.replace(r'[$,%+🔒]', '', regex=True)
                   .str.replace(',', '')
                   .str.strip())
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def main():
    df = scrape_fintel_vanguard()

    if df is None or df.empty:
        print("\n✗ No data scraped.")
        return

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print("\nFirst 15 rows:")
    print(df.head(15).to_string())

    df.to_csv("fintel_vanguard_13f.csv", index=False)
    print("\n✓ Saved: fintel_vanguard_13f.csv")

    df_clean = clean_dataframe(df)
    df_clean.to_csv("fintel_vanguard_13f_cleaned.csv", index=False)
    print("✓ Saved: fintel_vanguard_13f_cleaned.csv")


if __name__ == "__main__":
    main()
