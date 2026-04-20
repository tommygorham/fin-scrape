"""Aggregate congress + insider buy signals for a watchlist across data/ snapshots."""
import os
import re
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent
TICKERS = ["IONQ", "NEE", "SHOP", "USB", "NKE", "SCHW", "IREN", "CRWD", "CRWV"]

TIME_RE = re.compile(r"_(\d{2}-\d{2}-\d{2})\.csv$")


def latest_file(paths):
    """Pick the file with the latest HH-MM-SS timestamp in the filename."""
    def key(p):
        m = TIME_RE.search(p.name)
        return m.group(1) if m else ""
    return max(paths, key=key)


def collect():
    congress_by_day = defaultdict(int)   # {(date, ticker): count}
    insider_by_day = defaultdict(int)
    congress_politicians = defaultdict(set)  # ticker -> {politicians}
    congress_amount_buckets = defaultdict(lambda: defaultdict(int))  # ticker -> bucket -> count

    for date_dir in sorted(DATA_DIR.iterdir()):
        if not date_dir.is_dir():
            continue
        congress_files = list(date_dir.glob("congress_purchases_only_*.csv"))
        insider_files = list(date_dir.glob("insider_trading_data_*.csv"))

        if congress_files:
            f = latest_file(congress_files)
            try:
                df = pd.read_csv(f)
                if not df.empty and "Stock" in df.columns:
                    sub = df[df["Stock"].isin(TICKERS)]
                    for t, g in sub.groupby("Stock"):
                        congress_by_day[(date_dir.name, t)] = len(g)
                        if "Politician" in g.columns:
                            congress_politicians[t].update(g["Politician"].dropna().unique())
                        if "Amount" in g.columns:
                            for amt in g["Amount"].dropna():
                                congress_amount_buckets[t][amt] += 1
            except pd.errors.EmptyDataError:
                pass

        if insider_files:
            f = latest_file(insider_files)
            try:
                df = pd.read_csv(f)
                if not df.empty and "ticker" in df.columns:
                    sub = df[df["ticker"].isin(TICKERS)]
                    for _, row in sub.iterrows():
                        insider_by_day[(date_dir.name, row["ticker"])] = int(row["purchases"])
            except pd.errors.EmptyDataError:
                pass

    return congress_by_day, insider_by_day, congress_politicians, congress_amount_buckets


def main():
    congress_by_day, insider_by_day, politicians, amount_buckets = collect()

    rows = []
    for t in TICKERS:
        c_total = sum(v for (_, tk), v in congress_by_day.items() if tk == t)
        c_days = sum(1 for (_, tk), v in congress_by_day.items() if tk == t and v > 0)
        i_total = sum(v for (_, tk), v in insider_by_day.items() if tk == t)
        i_days = sum(1 for (_, tk), v in insider_by_day.items() if tk == t and v > 0)
        rows.append({
            "Ticker": t,
            "Congress Purchases": c_total,
            "Congress Active Days": c_days,
            "Unique Politicians": len(politicians[t]),
            "Insider Purchases": i_total,
            "Insider Active Days": i_days,
            "Total Buy Signals": c_total + i_total,
        })

    df = pd.DataFrame(rows).sort_values("Total Buy Signals", ascending=True).reset_index(drop=True)

    print("\n" + "=" * 78)
    print("BUY SIGNAL SUMMARY — congress purchases + insider purchases across data/")
    print("=" * 78)
    print(df.to_string(index=False))

    # ---- Figure ----
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle("Buy Signal Analysis — Watchlist (aggregated across data/ snapshots)",
                 fontsize=15, fontweight="bold")

    # (1) Stacked horizontal bar: congress vs insider purchases
    ax = axes[0, 0]
    y = np.arange(len(df))
    ax.barh(y, df["Congress Purchases"], color="#2E86AB", label="Congress purchases")
    ax.barh(y, df["Insider Purchases"], left=df["Congress Purchases"],
            color="#A23B72", label="Insider purchases")
    ax.set_yticks(y)
    ax.set_yticklabels(df["Ticker"])
    ax.set_xlabel("Total purchase signals")
    ax.set_title("Total buy signals by source")
    ax.legend(loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    for i, tot in enumerate(df["Total Buy Signals"]):
        ax.text(tot + 0.5, i, str(tot), va="center", fontsize=9, fontweight="bold")

    # (2) Total buy signals ranking
    ax = axes[0, 1]
    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.85, len(df)))
    ax.barh(df["Ticker"], df["Total Buy Signals"], color=colors)
    ax.set_xlabel("Total buy signals (congress + insider)")
    ax.set_title("Ranking — most buy signals at top")
    ax.grid(axis="x", alpha=0.3)
    for i, v in enumerate(df["Total Buy Signals"]):
        ax.text(v + 0.3, i, str(v), va="center", fontsize=10, fontweight="bold")

    # (3) Active days coverage
    ax = axes[1, 0]
    width = 0.38
    x = np.arange(len(df))
    ax.bar(x - width/2, df["Congress Active Days"], width,
           color="#2E86AB", label="Congress active days")
    ax.bar(x + width/2, df["Insider Active Days"], width,
           color="#A23B72", label="Insider active days")
    ax.set_xticks(x)
    ax.set_xticklabels(df["Ticker"], rotation=30)
    ax.set_ylabel("Days with ≥1 purchase signal")
    ax.set_title("Breadth — how many snapshot days showed buys")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # (4) Unique politicians buying
    ax = axes[1, 1]
    order = df.sort_values("Unique Politicians", ascending=True)
    ax.barh(order["Ticker"], order["Unique Politicians"], color="#F18F01")
    ax.set_xlabel("Distinct politicians with ≥1 purchase")
    ax.set_title("Congress diversity — unique politicians buying")
    ax.grid(axis="x", alpha=0.3)
    for i, v in enumerate(order["Unique Politicians"]):
        ax.text(v + 0.05, i, str(v), va="center", fontsize=10, fontweight="bold")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_png = OUT_DIR / "buy_signals_watchlist.png"
    plt.savefig(out_png, dpi=130, bbox_inches="tight")
    print(f"\nSaved figure: {out_png}")

    df.sort_values("Total Buy Signals", ascending=False).to_csv(
        OUT_DIR / "buy_signals_watchlist.csv", index=False)
    print(f"Saved table:  {OUT_DIR / 'buy_signals_watchlist.csv'}")

    top = df.sort_values("Total Buy Signals", ascending=False).iloc[0]
    print(f"\n>>> Most buy signals: {top['Ticker']} "
          f"({top['Total Buy Signals']} total; "
          f"{top['Congress Purchases']} congress, {top['Insider Purchases']} insider)")

    plt.show()


if __name__ == "__main__":
    main()
