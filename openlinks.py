#!/usr/bin/env python3
import webbrowser

# Define your 4 custom links here
urls = [
    "https://fintel.io/i/blackrock",
    "https://fintel.io/i/vanguard-group", 
    "https://fintel.io/i/state-street", 
]

for url in urls:
    webbrowser.open(url)
