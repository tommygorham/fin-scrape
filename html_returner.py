import requests
from bs4 import BeautifulSoup, Comment
from collections import Counter

def get_scraper_skeleton(url, max_repeats=3):
    """
    Fetches a URL and returns a minimized HTML structure for scraper development.
    
    Args:
        url (str): The target website URL.
        max_repeats (int): The number of identical sibling tags to keep (default 3).
                           e.g., keep first 3 <li> in a <ul>, or first 3 <tr> in a <table>.
    
    Returns:
        str: Minimized HTML.
    """
    
    # 1. Fetch the content with a generic User-Agent to avoid immediate blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}"

    soup = BeautifulSoup(response.text, 'html.parser')

    # 2. Remove Noise (Scripts, Styles, SVGs, Meta)
    # Scrapers rarely need these unless data is embedded in a specific script variable.
    noise_tags = ['script', 'style', 'noscript', 'meta', 'link', 'svg', 'path', 'iframe']
    for tag in soup(noise_tags):
        tag.decompose()

    # 3. Truncate Repeating Elements
    # We iterate over all elements that have children
    for parent in soup.find_all():
        if not parent.contents:
            continue
            
        # Count occurrences of child tags (e.g., {'li': 50, 'div': 2})
        child_tags = [child.name for child in parent.find_all(recursive=False) if child.name]
        tag_counts = Counter(child_tags)
        
        # Track what we've seen so far in this loop
        seen_counter = Counter()
        
        # Create a snapshot of children to iterate safely while modifying the tree
        children = list(parent.contents)
        
        items_removed = 0
        
        for child in children:
            if child.name is None: # Skip NavigableStrings (text nodes)
                continue
                
            seen_counter[child.name] += 1
            
            # If we have seen this tag type more than `max_repeats` times inside this parent
            if seen_counter[child.name] > max_repeats:
                child.decompose()
                items_removed += 1
        
        # Optional: Add a comment indicating data was removed (helps context)
        if items_removed > 0:
            parent.append(Comment(f" ... {items_removed} repeating elements removed for brevity ... "))

    # 4. Clean empty text nodes (whitespace) to make prettify look better
    # This removes empty newlines left over from deletions
    for txt in soup.find_all(text=True):
        if txt.strip() == "":
            txt.extract()

    return soup.prettify()

# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    # Example: Wikipedia's list of countries (a very long table)
    target_url = "https://www.quiverquant.com/insiders/"
    print(f"Fetching minimal HTML from: {target_url}...\n")
    
    minimal_html = get_scraper_skeleton(target_url)
    
    # Save to file or print
    with open("scraper_blueprint.html", "w", encoding="utf-8") as f:
        f.write(minimal_html)
        
    print("Done! Check 'scraper_blueprint.html'.")
    
    # Just printing a snippet to console to demonstrate
    print("\n--- Snippet of the Output ---")
    print(minimal_html[:1500]) # Print first 1500 chars
