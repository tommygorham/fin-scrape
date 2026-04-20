# Python script that can return recent insider or congress purchases 
# USAGE: python scrape.py congress
#        python scrape.py insider
# 
import argparse
from scraper import (
    fetch_table, count_transactions,
    congress_ticker_extractor, congress_sale_detector,
    insider_ticker_extractor, insider_sale_detector,
    fetch_insider_json, count_insider_transactions_from_json,
    aggregate_insider_values_from_json,
)

CONFIG = {
    'congress': {
        'url': 'https://www.quiverquant.com/congresstrading/',
        'selector': 'table.table-congress.table-politician',
        'ticker_extractor': congress_ticker_extractor,
        'sale_detector': congress_sale_detector,
        'use_json': False,
    },
    'insider': {
        'url': 'https://www.quiverquant.com/insiders/', 
        'selector': 'table#recentInsiderTransactionsTable',
        'ticker_extractor': insider_ticker_extractor,
        'sale_detector': insider_sale_detector,
        'use_json': True,
    },
}

def main():
    p = argparse.ArgumentParser(description='Scrape and count trading transactions.')
    p.add_argument('source', choices=CONFIG.keys(), help='Which dataset to scrape')
    p.add_argument('--values', action='store_true',
                   help='Output dollar volume per ticker (insider only). '
                        'Columns: TICKER PURCHASES PURCHASE_$ SALES SALE_$')
    p.add_argument('--tickers', help='Comma-separated tickers to filter (e.g. GPUS,SOFI)')
    args = p.parse_args()

    cfg = CONFIG[args.source]
    ticker_filter = None
    if args.tickers:
        ticker_filter = {t.strip().upper() for t in args.tickers.split(',') if t.strip()}

    if args.values:
        if not cfg.get('use_json'):
            print(f"Error: --values is only supported for sources with dollar data (insider).")
            return
        data = fetch_insider_json(cfg['url'])
        if not data:
            print(f"Error: Could not fetch JSON data for {args.source}")
            return
        agg = aggregate_insider_values_from_json(data)

        rows = [
            (t, v['purchase_count'], v['purchase_value'], v['sale_count'], v['sale_value'])
            for t, v in agg.items()
            if (ticker_filter is None and v['purchase_value'] > 0)
            or (ticker_filter is not None and t in ticker_filter)
        ]
        rows.sort(key=lambda r: r[2], reverse=True)

        print(f"--- {args.source.capitalize()} Purchase $ Volume ---")
        print(f"{'TICKER':<8}{'PURCHASES':>10}{'PURCHASE_$':>16}{'SALES':>8}{'SALE_$':>16}")
        for ticker, pc, pv, sc, sv in rows:
            print(f"{ticker:<8}{pc:>10}{pv:>16,.0f}{sc:>8}{sv:>16,.0f}")

        if ticker_filter:
            missing = ticker_filter - {r[0] for r in rows}
            if missing:
                print(f"\nNot found in current snapshot: {', '.join(sorted(missing))}")
        return

    # Use JSON extraction for insider data (page loads dynamically)
    if cfg.get('use_json'):
        data = fetch_insider_json(cfg['url'])
        if not data:
            print(f"Error: Could not fetch JSON data for {args.source}")
            return
        counts = count_insider_transactions_from_json(data)
    else:
        table = fetch_table(cfg['url'], cfg['selector'])
        if not table:
            print(f"Error: Could not find table for {args.source}")
            return

        counts = count_transactions(
            table,
            cfg['ticker_extractor'],
            cfg['sale_detector']
        )

    print(f"--- {args.source.capitalize()} Purchases ---")
    purchase_threshold = 1 if args.source == 'congress' else 0

    for ticker in sorted(counts):
        if ticker_filter and ticker not in ticker_filter:
            continue
        sales, purchases = counts[ticker]
        if purchases > purchase_threshold:
            print(f"{ticker} {purchases}")

if __name__ == '__main__':
    main()
