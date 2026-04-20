"""Find top-N tickers across all data/ snapshots by combined congress + insider buys."""
import re
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent
TOP_N = 5
TIME_RE = re.compile(r"_(\d{2}-\d{2}-\d{2})\.csv$")


def latest_file(paths):
    return max(paths, key=lambda p: (TIME_RE.search(p.name).group(1)
                                     if TIME_RE.search(p.name) else ""))


def collect():
    congress = defaultdict(int)   # ticker -> total purchases
    insider = defaultdict(int)
    c_days = defaultdict(set)
    i_days = defaultdict(set)
    politicians = defaultdict(set)

    for date_dir in sorted(DATA_DIR.iterdir()):
        if not date_dir.is_dir():
            continue

        cfs = list(date_dir.glob("congress_purchases_only_*.csv"))
        if cfs:
            try:
                df = pd.read_csv(latest_file(cfs))
                if not df.empty and "Stock" in df.columns:
                    for t, g in df.groupby("Stock"):
                        congress[t] += len(g)
                        c_days[t].add(date_dir.name)
                        if "Politician" in g.columns:
                            politicians[t].update(g["Politician"].dropna().unique())
            except pd.errors.EmptyDataError:
                pass

        ifs = list(date_dir.glob("insider_trading_data_*.csv"))
        if ifs:
            try:
                df = pd.read_csv(latest_file(ifs))
                if not df.empty and "ticker" in df.columns:
                    for _, r in df.iterrows():
                        t = r["ticker"]
                        n = int(r["purchases"])
                        if n > 0:
                            insider[t] += n
                            i_days[t].add(date_dir.name)
            except pd.errors.EmptyDataError:
                pass

    return congress, insider, c_days, i_days, politicians


def main():
    congress, insider, c_days, i_days, politicians = collect()

    tickers = set(congress) | set(insider)
    # drop obvious non-ticker rows (CUSIPs etc.) — keep alpha tickers up to 5 chars
    tickers = {t for t in tickers if isinstance(t, str) and t.isalpha() and len(t) <= 5}

    rows = []
    for t in tickers:
        c = congress.get(t, 0)
        i = insider.get(t, 0)
        rows.append({
            "Ticker": t,
            "Congress Buys": c,
            "Insider Buys": i,
            "Combined": c + i,
            "Congress Days": len(c_days.get(t, set())),
            "Insider Days": len(i_days.get(t, set())),
            "Unique Politicians": len(politicians.get(t, set())),
        })

    df = pd.DataFrame(rows).sort_values("Combined", ascending=False).reset_index(drop=True)
    top = df.head(TOP_N).copy()

    print("\n" + "=" * 78)
    print(f"TOP {TOP_N} TICKERS — combined congress + insider buy signals")
    print("=" * 78)
    print(top.to_string(index=False))

    df.head(25).to_csv(OUT_DIR / "top_combined_buys.csv", index=False)
    print(f"\nSaved table (top 25): {OUT_DIR / 'top_combined_buys.csv'}")

    # ---- Figure ----
    top_sorted = top.sort_values("Combined", ascending=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
    fig.suptitle(f"Top {TOP_N} Tickers — Combined Buy Signals (congress + insider)",
                 fontsize=15, fontweight="bold")

    y = np.arange(len(top_sorted))
    ax1.barh(y, top_sorted["Congress Buys"], color="#2E86AB", label="Congress buys")
    ax1.barh(y, top_sorted["Insider Buys"],
             left=top_sorted["Congress Buys"], color="#A23B72", label="Insider buys")
    ax1.set_yticks(y)
    ax1.set_yticklabels(top_sorted["Ticker"])
    ax1.set_xlabel("Buy signals")
    ax1.set_title("Stacked buys by source")
    ax1.legend(loc="lower right")
    ax1.grid(axis="x", alpha=0.3)
    for i, tot in enumerate(top_sorted["Combined"]):
        ax1.text(tot + 1, i, str(tot), va="center", fontweight="bold", fontsize=10)

    width = 0.38
    x = np.arange(len(top_sorted))
    ax2.bar(x - width/2, top_sorted["Congress Days"], width,
            color="#2E86AB", label="Congress active days")
    ax2.bar(x + width/2, top_sorted["Insider Days"], width,
            color="#A23B72", label="Insider active days")
    ax2.set_xticks(x)
    ax2.set_xticklabels(top_sorted["Ticker"])
    ax2.set_ylabel("Distinct snapshot days with ≥1 buy")
    ax2.set_title("Signal breadth over time")
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out_png = OUT_DIR / "top_combined_buys.png"
    plt.savefig(out_png, dpi=130, bbox_inches="tight")
    print(f"Saved figure:         {out_png}")

    plt.show()


if __name__ == "__main__":
    main()
