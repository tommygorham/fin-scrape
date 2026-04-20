"""Top-5 tickers by combined buys, requiring ≥2 congress AND ≥2 insider buys."""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from top_combined_buys import collect  # reuse the scanner

OUT_DIR = Path(__file__).resolve().parent
MIN_CONGRESS = 2
MIN_INSIDER = 2
TOP_N = 5


def main():
    c, i, cd, idd, pol = collect()
    tickers = {t for t in (set(c) | set(i))
               if isinstance(t, str) and t.isalpha() and len(t) <= 5}

    rows = []
    for t in tickers:
        cb, ib = c.get(t, 0), i.get(t, 0)
        if cb >= MIN_CONGRESS and ib >= MIN_INSIDER:
            rows.append({
                "Ticker": t,
                "Congress Buys": cb,
                "Insider Buys": ib,
                "Combined": cb + ib,
                "Congress Days": len(cd.get(t, set())),
                "Insider Days": len(idd.get(t, set())),
                "Unique Politicians": len(pol.get(t, set())),
            })

    df = pd.DataFrame(rows).sort_values("Combined", ascending=False).reset_index(drop=True)
    top = df.head(TOP_N).copy()

    print("\n" + "=" * 78)
    print(f"TOP {TOP_N} — combined buys, filtered: ≥{MIN_CONGRESS} congress AND ≥{MIN_INSIDER} insider")
    print("=" * 78)
    print(top.to_string(index=False))
    print(f"\nQualifying tickers: {len(df)}")

    df.head(25).to_csv(OUT_DIR / "top_combined_buys_both.csv", index=False)

    top_sorted = top.sort_values("Combined", ascending=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
    fig.suptitle(f"Top {TOP_N} Tickers — combined buys (≥{MIN_CONGRESS} congress AND ≥{MIN_INSIDER} insider)",
                 fontsize=14, fontweight="bold")

    y = np.arange(len(top_sorted))
    ax1.barh(y, top_sorted["Congress Buys"], color="#2E86AB", label="Congress buys")
    ax1.barh(y, top_sorted["Insider Buys"],
             left=top_sorted["Congress Buys"], color="#A23B72", label="Insider buys")
    ax1.set_yticks(y); ax1.set_yticklabels(top_sorted["Ticker"])
    ax1.set_xlabel("Buy signals"); ax1.set_title("Stacked buys by source")
    ax1.legend(loc="lower right"); ax1.grid(axis="x", alpha=0.3)
    for idx, tot in enumerate(top_sorted["Combined"]):
        ax1.text(tot + 1, idx, str(tot), va="center", fontweight="bold", fontsize=10)

    width = 0.38
    x = np.arange(len(top_sorted))
    ax2.bar(x - width/2, top_sorted["Congress Days"], width,
            color="#2E86AB", label="Congress active days")
    ax2.bar(x + width/2, top_sorted["Insider Days"], width,
            color="#A23B72", label="Insider active days")
    ax2.set_xticks(x); ax2.set_xticklabels(top_sorted["Ticker"])
    ax2.set_ylabel("Distinct snapshot days with ≥1 buy")
    ax2.set_title("Signal breadth over time")
    ax2.legend(); ax2.grid(axis="y", alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out_png = OUT_DIR / "top_combined_buys_both.png"
    plt.savefig(out_png, dpi=130, bbox_inches="tight")
    print(f"Saved figure: {out_png}")
    print(f"Saved table:  {OUT_DIR / 'top_combined_buys_both.csv'}")
    plt.show()


if __name__ == "__main__":
    main()
