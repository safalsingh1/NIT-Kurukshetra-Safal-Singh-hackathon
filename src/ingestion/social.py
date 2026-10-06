"""
src/ingestion/social.py
========================
Social-finance sentiment ingestion (historical datasets only).

We deliberately avoid live social-media APIs (Twitter/X, Reddit real-time)
because they are fragile, rate-limited, and unsuitable for a reproducible demo.

Instead we load a curated historical Reddit r/wallstreetbets + r/investing
dataset that is included in data/social/.

References:
  - SentimentArrow Reddit Finance dataset (public, CC-BY)
  - Kaggle "Reddit WallStreetBets Posts" dataset
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parents[2] / "data" / "social"

SCHEMA = [
    "id",
    "timestamp",
    "platform",    # "reddit" | "twitter_historical"
    "author",
    "subreddit",
    "title",
    "body",
    "score",       # upvotes / engagement score
    "entities",    # tickers mentioned ($NVDA etc.)
    "mode",
]


def fetch_social(
    tickers: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """
    Load historical social-finance posts.

    Parameters
    ----------
    tickers : Filter to posts mentioning any of these tickers
    start   : ISO date string (inclusive)
    end     : ISO date string (inclusive)

    Returns
    -------
    pd.DataFrame with SCHEMA columns
    """
    csv_files = list(DATA_DIR.glob("*.csv"))
    if not csv_files:
        logger.warning("No social data CSVs found in %s", DATA_DIR)
        return _empty_frame()

    frames = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(frames, ignore_index=True)

    for col in SCHEMA:
        if col not in df.columns:
            df[col] = "" if col != "score" else 0

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["mode"] = "demo"

    if start:
        df = df[df["timestamp"] >= pd.Timestamp(start, tz="UTC")]
    if end:
        df = df[df["timestamp"] <= pd.Timestamp(end, tz="UTC")]

    if tickers:
        pattern = "|".join(tickers)
        mask = (
            df["entities"].str.contains(pattern, case=False, na=False)
            | df["title"].str.contains(pattern, case=False, na=False)
            | df["body"].str.contains(pattern, case=False, na=False)
        )
        df = df[mask]

    return df[SCHEMA].reset_index(drop=True)


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMA)
