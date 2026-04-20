"""Backfill the local DuckDB from historical CSVs under data/MM-DD-YYYY/.

Filenames follow two patterns we care about:
  - insider_trading_data_HH-MM-SS.csv       -> insider_trades
  - congress_purchases_only_HH-MM-SS.csv    -> congress_purchases
Empty CSVs and the congress_trading_data_*.csv files (which are almost always
empty or redundant) are skipped.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DIR_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{4})$")                      # MM-DD-YYYY
TIME_RE = re.compile(r"_(\d{2})-(\d{2})-(\d{2})\.csv$")                # _HH-MM-SS.csv


def parse_scraped_at(day_dir: Path, fname: str) -> datetime | None:
    m_dir = DIR_RE.match(day_dir.name)
    m_time = TIME_RE.search(fname)
    if not (m_dir and m_time):
        return None
    mo, dd, yy = map(int, m_dir.groups())
    hh, mm, ss = map(int, m_time.groups())
    return datetime(yy, mo, dd, hh, mm, ss)


def load_insider(path: Path, scraped_at: datetime) -> int:
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return 0
    if df.empty or not {"ticker", "purchases"}.issubset(df.columns):
        return 0
    return db.insert_insider_trades(df, scraped_at=scraped_at)


def load_congress(path: Path, scraped_at: datetime) -> int:
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return 0
    if df.empty:
        return 0
    return db.insert_congress_purchases(df, scraped_at=scraped_at)


def main() -> int:
    p = argparse.ArgumentParser(description="Backfill DuckDB from historical CSVs")
    p.add_argument("--data-dir", default=str(DATA_DIR), help="Root data directory")
    p.add_argument("--dry-run", action="store_true", help="Report what would load; write nothing")
    args = p.parse_args()

    root = Path(args.data_dir)
    if not root.is_dir():
        print(f"No data directory at {root}", file=sys.stderr)
        return 1

    print(f"DB: {db.DB_PATH}")
    print(f"Scanning: {root}")

    totals = {"insider_files": 0, "insider_rows": 0, "congress_files": 0, "congress_rows": 0, "skipped": 0}

    for day_dir in sorted(p for p in root.iterdir() if p.is_dir() and DIR_RE.match(p.name)):
        for csv_path in sorted(day_dir.glob("*.csv")):
            scraped_at = parse_scraped_at(day_dir, csv_path.name)
            if scraped_at is None:
                totals["skipped"] += 1
                continue
            if csv_path.name.startswith("insider_trading_data_"):
                if args.dry_run:
                    totals["insider_files"] += 1
                    continue
                n = load_insider(csv_path, scraped_at)
                if n:
                    totals["insider_files"] += 1
                    totals["insider_rows"] += n
            elif csv_path.name.startswith("congress_purchases_only_"):
                if args.dry_run:
                    totals["congress_files"] += 1
                    continue
                n = load_congress(csv_path, scraped_at)
                if n:
                    totals["congress_files"] += 1
                    totals["congress_rows"] += n
            else:
                totals["skipped"] += 1

    print(
        f"insider:  {totals['insider_files']} files, {totals['insider_rows']} rows\n"
        f"congress: {totals['congress_files']} files, {totals['congress_rows']} rows\n"
        f"skipped:  {totals['skipped']} files"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
