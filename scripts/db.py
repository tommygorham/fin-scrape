"""Local DuckDB helpers for the stocks pipeline.

The database lives at <repo_root>/stocks.duckdb (gitignored). Every scraper
writes a row-set tagged with a `scraped_at` TIMESTAMP so history is queryable.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("STOCKS_DB_PATH", REPO_ROOT / "stocks.duckdb"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS insider_trades (
    scraped_at TIMESTAMP NOT NULL,
    ticker     VARCHAR   NOT NULL,
    purchases  INTEGER   NOT NULL,
    PRIMARY KEY (scraped_at, ticker)
);

CREATE TABLE IF NOT EXISTS congress_purchases (
    scraped_at  TIMESTAMP NOT NULL,
    stock       VARCHAR,
    transaction VARCHAR,
    politician  VARCHAR,
    party       VARCHAR,
    chamber     VARCHAR,
    amount      VARCHAR,
    traded      DATE,
    filed       DATE
);
CREATE INDEX IF NOT EXISTS idx_congress_scraped_at ON congress_purchases(scraped_at);
CREATE INDEX IF NOT EXISTS idx_congress_stock      ON congress_purchases(stock);

CREATE TABLE IF NOT EXISTS zacks_tickers (
    scraped_at TIMESTAMP NOT NULL,
    ticker     VARCHAR   NOT NULL,
    category   VARCHAR   NOT NULL,
    PRIMARY KEY (scraped_at, ticker, category)
);
"""


def connect() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(str(DB_PATH))
    conn.execute(SCHEMA)
    return conn


def insert_insider_trades(df: pd.DataFrame, scraped_at: datetime | None = None) -> int:
    if df is None or df.empty:
        return 0
    scraped_at = scraped_at or datetime.now()
    rows = df[["ticker", "purchases"]].copy()
    rows = rows.dropna(subset=["ticker", "purchases"])
    rows = rows[rows["ticker"].astype(str).str.strip() != ""]
    rows = rows.drop_duplicates(subset=["ticker"], keep="last")
    if rows.empty:
        return 0
    rows.insert(0, "scraped_at", scraped_at)
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO insider_trades SELECT * FROM rows"
        )
    return len(rows)


def insert_congress_purchases(df: pd.DataFrame, scraped_at: datetime | None = None) -> int:
    if df is None or df.empty:
        return 0
    scraped_at = scraped_at or datetime.now()
    cols = ["Stock", "Transaction", "Politician", "Party", "Chamber", "Amount", "Traded", "Filed"]
    rows = df.reindex(columns=cols).copy()
    rows.columns = ["stock", "transaction", "politician", "party", "chamber", "amount", "traded", "filed"]
    rows.insert(0, "scraped_at", scraped_at)
    with connect() as conn:
        conn.execute("INSERT INTO congress_purchases SELECT * FROM rows")
    return len(rows)


def insert_zacks_tickers(
    tickers: Iterable[str],
    category: str,
    scraped_at: datetime | None = None,
) -> int:
    tickers = [t.strip() for t in tickers if t and t.strip()]
    if not tickers:
        return 0
    scraped_at = scraped_at or datetime.now()
    rows = pd.DataFrame(
        {"scraped_at": scraped_at, "ticker": tickers, "category": category}
    )
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO zacks_tickers SELECT * FROM rows")
    return len(rows)
