import yfinance as yf

def format_market_cap(mc):
    if mc is None:
        return "N/A"
    if mc >= 1_000_000_000_000:
        return f"{mc / 1_000_000_000_000:.2f}T"
    elif mc >= 1_000_000_000:
        return f"{mc / 1_000_000_000:.2f}B"
    else:
        return f"{mc / 1_000_000:.2f}M"

tickers = ["NVDA", "AMD", "MSFT"]

for symbol in tickers:
    t = yf.Ticker(symbol)
    info = t.info

    print(f"\n=== {symbol} ===")

    print("Price:", info.get("currentPrice"))
    print("Market Cap:", format_market_cap(info.get("marketCap")))

    print("\nRecommendations:")
    print(t.recommendations.head())

#ticker = yf.Ticker("AAPL")
# 1) Historical price data
#price_history = ticker.history(period="1mo")
#print("HISTORICAL PRICES")
#print(price_history.head(), end="\n\n")

# 2) Basic company info
#info = ticker.info
#print("BASIC INFO")
#print("Current price:", info.get("currentPrice"))
#print("Market cap:", info.get("marketCap"))
#print("PE ratio:", info.get("trailingPE"))
#print("Sector:", info.get("sector"))
#print("Industry:", info.get("industry"), end="\n\n")

# 3) Financial statements
#print("INCOME STATEMENT")
#print(ticker.financials, end="\n\n")

#print("BALANCE SHEET")
#print(ticker.balance_sheet, end="\n\n")

#print("CASH FLOW")
#print(ticker.cashflow, end="\n\n")

# 4) Earnings dates
#print("EARNINGS DATES")
#print(ticker.earnings_dates.head(), end="\n\n")

# 5) Analyst recommendations
#print("ANALYST RECOMMENDATIONS")
#print(ticker.recommendations.head(), end="\n\n")

