#!/usr/bin/env python3
"""CLI for running reports against stocks.duckdb.

Usage:
    ./reports.py --help
    ./reports.py tables
    ./reports.py insider-movers --days 7 --limit 20
    ./reports.py insider-delta
    ./reports.py congress-top --days 7
    ./reports.py congress-recent --days 7
    ./reports.py overlap --days 7
"""
from __future__ import annotations

import os
from pathlib import Path

import click
import duckdb

REPO_ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("STOCKS_DB_PATH", REPO_ROOT / "stocks.duckdb"))


def _run(sql: str, params: tuple = (), max_rows: int = 40) -> None:
    with duckdb.connect(str(DB_PATH), read_only=True) as conn:
        conn.sql(sql, params=params).show(max_rows=max_rows)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option("0.1.0")
def cli() -> None:
    """Reports over the local DuckDB (insider / congress / zacks data)."""


@cli.command()
def tables() -> None:
    """List tables and row counts in the DB."""
    with duckdb.connect(str(DB_PATH), read_only=True) as conn:
        conn.sql("SHOW TABLES").show()
        for (name,) in conn.sql("SHOW TABLES").fetchall():
            n = conn.sql(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            click.echo(f"  {name}: {n:,} rows")


@cli.command("insider-movers")
@click.option("--days", "-d", default=7, show_default=True, help="Window size in days.")
@click.option("--limit", "-l", default=20, show_default=True, help="Max rows.")
def insider_movers(days: int, limit: int) -> None:
    """Top insider-purchase movers over the last N days."""
    _run(
        f"""
        SELECT ticker,
               SUM(purchases) AS purchases,
               COUNT(*)       AS scrapes
        FROM insider_trades
        WHERE scraped_at >= now() - INTERVAL {days} DAY
        GROUP BY ticker
        ORDER BY purchases DESC
        LIMIT {limit}
        """,
        max_rows=limit,
    )


@cli.command("insider-delta")
@click.option("--limit", "-l", default=20, show_default=True, help="Max rows.")
def insider_delta(limit: int) -> None:
    """Week-over-week change in insider purchases (this week vs prior week)."""
    _run(
        f"""
        WITH w AS (
          SELECT ticker,
                 SUM(CASE WHEN scraped_at >= now() - INTERVAL 7 DAY
                          THEN purchases ELSE 0 END) AS wk1,
                 SUM(CASE WHEN scraped_at <  now() - INTERVAL 7 DAY
                           AND scraped_at >= now() - INTERVAL 14 DAY
                          THEN purchases ELSE 0 END) AS wk0
          FROM insider_trades
          WHERE scraped_at >= now() - INTERVAL 14 DAY
          GROUP BY ticker
        )
        SELECT ticker, wk0, wk1, wk1 - wk0 AS delta
        FROM w
        WHERE wk1 > 0
        ORDER BY delta DESC
        LIMIT {limit}
        """,
        max_rows=limit,
    )


@cli.command("congress-top")
@click.option("--days", "-d", default=7, show_default=True, help="Window size in days.")
@click.option("--limit", "-l", default=20, show_default=True, help="Max rows.")
def congress_top(days: int, limit: int) -> None:
    """Top congress-bought tickers over the last N days."""
    _run(
        f"""
        SELECT stock,
               COUNT(*)                  AS trades,
               COUNT(DISTINCT politician) AS politicians
        FROM congress_purchases
        WHERE scraped_at >= now() - INTERVAL {days} DAY
          AND transaction ILIKE '%purchase%'
        GROUP BY stock
        ORDER BY trades DESC
        LIMIT {limit}
        """,
        max_rows=limit,
    )


@cli.command("congress-recent")
@click.option("--days", "-d", default=7, show_default=True, help="Window size in days.")
@click.option("--limit", "-l", default=50, show_default=True, help="Max rows.")
def congress_recent(days: int, limit: int) -> None:
    """Raw congress buy filings from the last N days."""
    _run(
        f"""
        SELECT filed, stock, politician, party, chamber, amount
        FROM congress_purchases
        WHERE filed >= current_date - INTERVAL {days} DAY
          AND transaction ILIKE '%purchase%'
        ORDER BY filed DESC
        LIMIT {limit}
        """,
        max_rows=limit,
    )


@cli.command()
@click.option("--days", "-d", default=7, show_default=True, help="Window size in days.")
@click.option("--limit", "-l", default=20, show_default=True, help="Max rows.")
def overlap(days: int, limit: int) -> None:
    """Tickers appearing in BOTH insider buys AND congress buys this window."""
    _run(
        f"""
        WITH i AS (
          SELECT ticker, SUM(purchases) AS insider_purchases
          FROM insider_trades
          WHERE scraped_at >= now() - INTERVAL {days} DAY
          GROUP BY ticker
        ),
        c AS (
          SELECT stock AS ticker, COUNT(*) AS congress_trades
          FROM congress_purchases
          WHERE scraped_at >= now() - INTERVAL {days} DAY
            AND transaction ILIKE '%purchase%'
          GROUP BY stock
        )
        SELECT i.ticker, insider_purchases, congress_trades
        FROM i JOIN c USING (ticker)
        ORDER BY insider_purchases + congress_trades DESC
        LIMIT {limit}
        """,
        max_rows=limit,
    )


@cli.command()
@click.argument("sql")
def query(sql: str) -> None:
    """Run an arbitrary read-only SQL query."""
    _run(sql, max_rows=200)


if __name__ == "__main__":
    cli()
