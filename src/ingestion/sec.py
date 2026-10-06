"""
src/ingestion/sec.py
====================
SEC EDGAR ingestion layer.

Fetches 8-K, 10-Q, and 10-K filings via the official SEC EDGAR API:
  https://efts.sec.gov/LATEST/search-index?...
  https://data.sec.gov/submissions/CIK{cik}.json

SEC evidence is the "confirmation layer": when a corporate event appears in
GDELT *and* is confirmed by an SEC filing, Evidence Score rises substantially.

Modes: LIVE (SEC API) and DEMO (data/sec/*.csv)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEC_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_HEADER = {"User-Agent": "FinRiskAI research@finriskai.io"}
DATA_DIR = Path(__file__).parents[2] / "data" / "sec"

FORM_TYPES = ["8-K", "10-Q", "10-K"]

SCHEMA = [
    "id",           # accession number
    "timestamp",    # filing date (UTC)
    "ticker",       # resolved ticker
    "cik",          # SEC CIK
    "company",      # company name
    "form_type",    # 8-K | 10-Q | 10-K
    "description",  # form description / item
    "url",          # SEC filing URL
    "mode",         # "live" | "demo"
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_filings(
    tickers: list[str] | None = None,
    form_types: list[str] | None = None,
    days: int = 7,
    demo: bool = False,
) -> pd.DataFrame:
    """
    Fetch recent SEC filings.

    Parameters
    ----------
    tickers    : List of ticker symbols to filter on (None = all available)
    form_types : ['8-K', '10-Q', '10-K'] or subset
    days       : How many days back to search
    demo       : Use pre-saved CSVs

    Returns
    -------
    pd.DataFrame with SCHEMA columns
    """
    if form_types is None:
        form_types = FORM_TYPES

    if demo:
        return _load_demo(tickers, form_types)

    try:
        return _fetch_edgar(tickers, form_types, days)
    except Exception as exc:
        logger.warning("SEC EDGAR live fetch failed (%s) – falling back to demo", exc)
        return _load_demo(tickers, form_types)


def get_cik(ticker: str) -> str | None:
    """Resolve a ticker to its SEC CIK number."""
    url = "https://efts.sec.gov/LATEST/search-index?q=%22{}%22&dateRange=custom&startdt={}&enddt={}&forms=10-K".format(
        ticker, "2020-01-01", datetime.now().strftime("%Y-%m-%d")
    )
    try:
        resp = requests.get(url, headers=SEC_HEADER, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        if hits:
            return hits[0]["_source"].get("entity_id", None)
    except Exception as exc:
        logger.debug("CIK lookup failed for %s: %s", ticker, exc)
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_edgar(tickers: list[str] | None, form_types: list[str], days: int) -> pd.DataFrame:
    """Use EDGAR full-text search API to get recent filings."""
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    query = " OR ".join(f'"{t}"' for t in (tickers or []))
    params = {
        "q": query or "*",
        "dateRange": "custom",
        "startdt": start_date,
        "enddt": end_date,
        "forms": ",".join(form_types),
        "_source": "file_date,entity_name,file_num,period_of_report,form_type,display_names",
        "hits.hits._source": 1,
        "hits.hits.total": 1,
    }

    resp = requests.get(
        "https://efts.sec.gov/LATEST/search-index",
        params=params,
        headers=SEC_HEADER,
        timeout=30,
    )
    resp.raise_for_status()
    hits = resp.json().get("hits", {}).get("hits", [])

    rows = []
    for h in hits:
        src = h.get("_source", {})
        rows.append({
            "id":          h.get("_id", ""),
            "timestamp":   src.get("file_date", ""),
            "ticker":      "",       # needs entity resolver
            "cik":         src.get("entity_id", ""),
            "company":     src.get("entity_name", ""),
            "form_type":   src.get("form_type", ""),
            "description": src.get("period_of_report", ""),
            "url":         f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={src.get('entity_id','')}&type={src.get('form_type','')}&dateb=&owner=include&count=40",
            "mode":        "live",
        })

    df = pd.DataFrame(rows, columns=SCHEMA)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df


def _load_demo(tickers: list[str] | None, form_types: list[str]) -> pd.DataFrame:
    """Load pre-saved SEC filing CSVs from data/sec/."""
    csv_files = list(DATA_DIR.glob("*.csv"))
    if not csv_files:
        logger.warning("No demo SEC CSVs found in %s – returning empty frame", DATA_DIR)
        return _empty_frame()

    frames = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(frames, ignore_index=True)

    for col in SCHEMA:
        if col not in df.columns:
            df[col] = ""
    df["mode"] = "demo"
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

    if tickers:
        df = df[df["ticker"].isin(tickers) | df["company"].str.upper().isin([t.upper() for t in tickers])]
    if form_types:
        df = df[df["form_type"].isin(form_types)]

    return df[SCHEMA]


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMA)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SEC EDGAR ingestion CLI")
    parser.add_argument("--tickers", nargs="+", default=None)
    parser.add_argument("--form",    default="8-K")
    parser.add_argument("--days",    type=int, default=7)
    parser.add_argument("--demo",    action="store_true")
    args = parser.parse_args()

    df = fetch_filings(args.tickers, [args.form], args.days, args.demo)
    print(df.head(10).to_string())
    print(f"\nTotal filings: {len(df)}")
