"""
src/ingestion/gdelt.py
======================
GDELT news ingestion layer.

Supports two modes:
  - LIVE: fetches from the GDELT 2.0 REST API / gdeltdoc library
  - DEMO: reads pre-saved CSVs from data/news/

GDELT provides global event/news data updated every 15 minutes.
We use it for: breaking news, company mentions, geopolitical events,
macro events, M&A, supply-chain, and leadership stories.
"""

from __future__ import annotations

import os
import time
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
DATA_DIR = Path(__file__).parents[2] / "data" / "news"

# Columns we normalise every row to
SCHEMA = [
    "id",           # unique article id
    "timestamp",    # ISO-8601 publication time (UTC)
    "url",          # article URL
    "source",       # domain / outlet name
    "headline",     # article headline
    "body",         # article body text (may be empty for GDELT)
    "entities",     # comma-separated companies / tickers mentioned
    "tone",         # GDELT tone score (-100 to +100) – raw
    "mode",         # "live" | "demo"
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_news(
    query: str,
    lookback_hours: int = 24,
    max_records: int = 250,
    demo: bool = False,
) -> pd.DataFrame:
    """
    Fetch news articles related to *query*.

    Parameters
    ----------
    query          : Free-text query string (e.g. "NVIDIA earnings")
    lookback_hours : How many hours back to search (max 3 months for GDELT)
    max_records    : Maximum number of articles to return
    demo           : If True, load from local CSVs instead of calling API

    Returns
    -------
    pd.DataFrame with columns matching SCHEMA
    """
    if demo:
        return _load_demo()

    try:
        return _fetch_gdelt_doc(query, lookback_hours, max_records)
    except Exception as exc:
        logger.warning("GDELT live fetch failed (%s) – falling back to demo data", exc)
        return _load_demo()


def fetch_bulk_for_tickers(
    tickers: list[str],
    lookback_hours: int = 24,
    demo: bool = False,
) -> pd.DataFrame:
    """Fetch news for a list of tickers and concatenate results."""
    frames = []
    for ticker in tickers:
        df = fetch_news(ticker, lookback_hours=lookback_hours, demo=demo)
        frames.append(df)
        if not demo:
            time.sleep(0.5)   # be kind to the GDELT API
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["url"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_gdelt_doc(query: str, lookback_hours: int, max_records: int) -> pd.DataFrame:
    """
    Call GDELT Document 2.0 API.
    API docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
    """
    start_dt = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": min(max_records, 250),   # GDELT hard limit
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "format": "json",
        "sort": "DateDesc",
    }
    resp = requests.get(GDELT_DOC_API, params=params, timeout=3)
    resp.raise_for_status()
    data = resp.json()

    articles = data.get("articles", [])
    if not articles:
        return _empty_frame()

    rows = []
    for art in articles:
        rows.append({
            "id":        art.get("url", ""),
            "timestamp": art.get("seendate", ""),
            "url":       art.get("url", ""),
            "source":    art.get("domain", ""),
            "headline":  art.get("title", ""),
            "body":      "",          # GDELT artlist doesn't include body
            "entities":  "",          # filled by entity resolver downstream
            "tone":      float(art.get("tone", 0)),
            "mode":      "live",
        })

    df = pd.DataFrame(rows, columns=SCHEMA)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df


def _load_demo() -> pd.DataFrame:
    """Load pre-saved GDELT sample data from data/news/."""
    csv_files = list(DATA_DIR.glob("*.csv"))
    if not csv_files:
        logger.warning("No demo news CSVs found in %s – returning empty frame", DATA_DIR)
        return _empty_frame()

    frames = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(frames, ignore_index=True)

    # Ensure schema compliance
    for col in SCHEMA:
        if col not in df.columns:
            df[col] = "" if col != "tone" else 0.0

    df["mode"] = "demo"
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df[SCHEMA]


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMA)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GDELT ingestion CLI")
    parser.add_argument("--query",   default="S&P 500 earnings")
    parser.add_argument("--lookback", type=int, default=24)
    parser.add_argument("--demo",    action="store_true")
    args = parser.parse_args()

    df = fetch_news(args.query, lookback_hours=args.lookback, demo=args.demo)
    print(df.head(10).to_string())
    print(f"\nTotal articles: {len(df)}")
