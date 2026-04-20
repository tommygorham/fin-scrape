"""
This script fetches Vanguard Group Inc’s portfolio holdings from Quiver Quantitative.

You need a Quiver API token (sign up at https://api.quiverquant.com).
Set the token in the QUIVER_API_TOKEN environment variable or pass it to
get_vanguard_holdings().  The script queries the live SEC13F endpoint and
converts the JSON response into a pandas DataFrame.
"""

import os
import pandas as pd
import requests

def get_vanguard_holdings(token=None) -> pd.DataFrame:
    api_token = token or os.environ.get("QUIVER_API_TOKEN")
    if not api_token:
        raise RuntimeError(
            "Please supply a Quiver API token. Sign up at https://api.quiverquant.com."
        )

    owner = "VANGUARD GROUP INC"
    url = f"https://api.quiverquant.com/beta/live/sec13f?owner={owner.replace(' ', '%20')}"
    headers = {"Accept": "application/json",
               "Authorization": f"Bearer {api_token}"}

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()  # list of holdings dictionaries

    df = pd.DataFrame(data)
    # convert numeric columns and filing date if present
    for col in [c for c in df.columns if c.lower() in {"shares", "marketvalue", "weight"}]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "FilingDate" in df.columns:
        df["FilingDate"] = pd.to_datetime(df["FilingDate"])
    return df

if __name__ == "__main__":
    df = get_vanguard_holdings()
    print(f"Retrieved {len(df)} holdings.")
    print(df.head())

