def get_fidelity_options_url(ticker):
    """
    Returns Fidelity options chain URL for a given stock ticker.
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        str: Fidelity options research URL
    """
    return f"https://digital.fidelity.com/ftgw/digital/options-research/option-chain?symbol={ticker}&oarchain=true"

# Test the function
ticker = input("Enter a stock ticker: ")
url = get_fidelity_options_url(ticker)
print(url)
