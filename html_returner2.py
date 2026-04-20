import requests
from bs4 import BeautifulSoup, Comment
import sys

def get_table_blueprint(url, table_id, max_rows=3):
    """
    Fetches a URL, finds a specific table by ID, extracts column names,
    and returns a minimized HTML snippet for scraper development.
    """
    
    # 1. Setup Request with Headers (Crucial for financial sites like QuiverQuant)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        print(f"Fetching {url}...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}", []

    soup = BeautifulSoup(response.text, 'html.parser')

    # 2. Find the Table
    target_table = soup.find(id=table_id)

    if not target_table:
        # Fallback: Sometimes users mistake a class for an ID, or the ID is on a wrapper div
        print(f"Warning: Exact ID '{table_id}' not found. Searching for partial matches or classes...")
        target_table = soup.find(attrs={"class": table_id}) or soup.find(lambda tag: tag.name == 'table' and table_id in str(tag.get('id', '')))
        
        if not target_table:
            return (f"ERROR: Table with ID '{table_id}' could not be found in the static HTML.\n"
                    f"Note: If the website uses JavaScript to load data (SSR), 'requests' cannot see it.\n"
                    f"You may need Selenium or Playwright."), []

    # 3. Extract Column Names
    # Logic: Look for <th> inside <thead> or the first <tr>
    headers = []
    header_row = target_table.find('thead')
    
    if header_row:
        headers_tags = header_row.find_all('th')
    else:
        # If no thead, check the first tr for th
        first_row = target_table.find('tr')
        if first_row:
            headers_tags = first_row.find_all(['th', 'td'])
        else:
            headers_tags = []

    column_names = [tag.get_text(strip=True) for tag in headers_tags]

    # 4. Truncate Rows (Keep HTML structure but remove bulk)
    # Find all rows in the body
    tbody = target_table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr', recursive=False)
    else:
        # If no tbody, find all tr, skipping the first one if we think it's a header
        rows = target_table.find_all('tr', recursive=False)
        if header_row or (rows and rows[0].find('th')):
            rows = rows[1:]

    # Remove rows beyond max_rows
    if len(rows) > max_rows:
        removed_count = len(rows) - max_rows
        for row in rows[max_rows:]:
            row.decompose()
        
        # Append a comment for clarity
        if tbody:
            tbody.append(Comment(f" ... {removed_count} rows removed for brevity ... "))
        else:
            target_table.append(Comment(f" ... {removed_count} rows removed for brevity ... "))

    return target_table.prettify(), column_names

# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    # Configuration
    target_url = "https://www.quiverquant.com/insiders/"
    target_table_id = "recentInsiderTransactionsTable"

    print(f"Analying table '{target_table_id}' from {target_url}...\n")

    html_snippet, columns = get_table_blueprint(target_url, target_table_id)

    print("-" * 30)
    print("DETECTED COLUMNS:")
    print("-" * 30)
    if columns:
        for i, col in enumerate(columns):
            print(f"{i}: {col}")
    else:
        print("No specific column headers detected (check HTML output).")
    
    print("\n" + "-" * 30)
    print("MINIMAL HTML FOR SCRAPER:")
    print("-" * 30)
    
    # Print the HTML (or save to file)
    print(html_snippet[:3000]) # Limit print to 2000 chars for console readability
