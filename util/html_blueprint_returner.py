# This script will launch a headless Chrome browser, wait for the table to load, and then generate the minimal HTML blueprint
# The blueprint is useful for web scraping, ie, you can pass the blueprint to the scraper 
# 
# DIRECTIONS 
# 1. Set the variable target_url at the bottom of this script 
# 2. Set the variable target_table_id at the bottom of this script
# 3. Run python html_blueprint_returner.py 
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup, Comment

def get_dynamic_table_blueprint(url, table_selector, max_rows=3):
    """
    Launches a headless browser to fetch dynamic JS-loaded tables
    Returns the minimal HTML and extracted data
    """
    
    # 1. Setup Headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run without opening a window
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") # Hide generic selenium signature
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    print(f"Launching browser to fetch {url}...")
    
    # Initialize Driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    html_content = ""
    try:
        driver.get(url)
        
        # 2. Wait 15 sec for the table to populate
        print("Waiting for JavaScript to load the table...")
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f"#{table_selector} tbody tr"))
            )
        except Exception:
            print("Warning: Timed out waiting for rows. The table might be empty or blocked.")

        # 3. Get the fully rendered HTML
        html_content = driver.page_source
        
    except Exception as e:
        return f"Error: {e}", [], []
    finally:
        driver.quit()

    # 4. Parse with BeautifulSoup (Same logic as before, now with populated data)
    soup = BeautifulSoup(html_content, 'html.parser')
    target_table = soup.find(id=table_selector)
    
    if not target_table:
        return "Table not found in rendered HTML.", [], []

    # --- Extract Headers ---
    headers = [th.get_text(strip=True) for th in target_table.find_all('th')]

    # --- Extract & Truncate Rows ---
    tbody = target_table.find('tbody')
    rows = tbody.find_all('tr', recursive=False) if tbody else target_table.find_all('tr', recursive=False)[1:]
    
    # Capture text data for the user before we delete nodes
    captured_data = []
    for row in rows[:max_rows]:
        cols = row.find_all(['td', 'th'])
        captured_data.append([col.get_text(strip=True) for col in cols])

    # Clean up HTML for the "Blueprint"
    if len(rows) > max_rows:
        removed_count = len(rows) - max_rows
        for row in rows[max_rows:]:
            row.decompose()
        
        if tbody:
            tbody.append(Comment(f" ... {removed_count} rows removed for brevity ... "))

    return target_table.prettify(), headers, captured_data

# --- USAGE ---
if __name__ == "__main__":
    target_url = "https://www.quiverquant.com/insiders/"
    target_table_id = "recentInsiderTransactionsTable"

    html_snippet, columns, rows_data = get_dynamic_table_blueprint(target_url, target_table_id)

    print("-" * 30)
    print("DETECTED DATA (First 3 Rows):")
    print("-" * 30)
    
    # Print Columns
    print(f"HEADERS: {columns}\n")
    
    # Print Rows
    for i, row in enumerate(rows_data):
        print(f"ROW {i+1}: {row}")

    print("\n" + "-" * 30)
    print("MINIMAL HTML FOR SCRAPER:")
    print("-" * 30)
    print(html_snippet[:2500])
