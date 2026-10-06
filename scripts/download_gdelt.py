"""
scripts/download_gdelt.py
==========================
Retry GDELT download with exponential backoff and longer delays.
GDELT free API: max 1 request / 5 seconds recommended (strict per-IP limit).

Usage:
  python scripts/download_gdelt.py
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("gdelt")

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
SCHEMA = ["id", "timestamp", "url", "source", "headline", "body",
          "entities", "tone", "mode"]
DATA_DIR = ROOT / "data" / "news"


def _gdelt_query_with_retry(query: str, hours: int = 72, max_retries: int = 4) -> pd.DataFrame:
    """Query GDELT with exponential backoff on 429."""
    start_dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    params = {
        "query":         query,
        "mode":          "artlist",
        "maxrecords":    250,
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "format":        "json",
        "sort":          "DateDesc",
    }

    delay = 10  # start at 10 seconds
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(GDELT_API, params=params, timeout=40)
            if resp.status_code == 429:
                wait = delay * (2 ** (attempt - 1))
                log.warning("    429 rate-limited. Waiting %ds before retry %d/%d...", wait, attempt, max_retries)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles", [])
            rows = [{
                "id":        a.get("url", ""),
                "timestamp": a.get("seendate", ""),
                "url":       a.get("url", ""),
                "source":    a.get("domain", ""),
                "headline":  a.get("title", ""),
                "body":      "",
                "entities":  query,
                "tone":      float(a.get("tone", 0)),
                "mode":      "live",
            } for a in articles]
            return pd.DataFrame(rows, columns=SCHEMA) if rows else pd.DataFrame(columns=SCHEMA)
        except Exception as e:
            wait = delay * (2 ** (attempt - 1))
            log.warning("    Error: %s. Waiting %ds...", e, wait)
            time.sleep(wait)

    log.error("    All %d retries exhausted for query: %s", max_retries, query[:50])
    return pd.DataFrame(columns=SCHEMA)


# Simpler, one-term queries are less likely to be throttled
QUERIES = [
    ("NVIDIA stock",          "NVDA"),
    ("Apple earnings",        "AAPL"),
    ("Microsoft Azure",       "MSFT"),
    ("Amazon AWS",            "AMZN"),
    ("Tesla electric vehicle","TSLA"),
    ("JPMorgan bank",         "JPM"),
    ("Meta Facebook AI",      "META"),
    ("Google Alphabet",       "GOOGL"),
    ("financial market risk", "MARKET"),
    ("S&P 500 index",         "SPX"),
]

INTER_QUERY_DELAY = 12  # seconds between queries — well above GDELT's 1 req/s limit


def main():
    log.info("GDELT Retry Download (with backoff)")
    log.info("Time: %s UTC", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
    log.info("Inter-query delay: %ds", INTER_QUERY_DELAY)
    log.info("")

    all_frames = []
    for i, (query, label) in enumerate(QUERIES, 1):
        log.info("[%02d/%02d] %s — '%s'", i, len(QUERIES), label, query)
        df = _gdelt_query_with_retry(query, hours=72)
        if not df.empty:
            all_frames.append(df)
            log.info("         -> %d articles", len(df))
        else:
            log.warning("         -> 0 articles")

        if i < len(QUERIES):
            log.info("         (sleeping %ds...)", INTER_QUERY_DELAY)
            time.sleep(INTER_QUERY_DELAY)

    if all_frames:
        result = pd.concat(all_frames, ignore_index=True)
        result = result.drop_duplicates(subset=["url"])
        result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
        result = result.sort_values("timestamp", ascending=False).reset_index(drop=True)

        out = DATA_DIR / "live_news.csv"
        result.to_csv(out, index=False)
        log.info("")
        log.info("DONE: %d unique articles saved -> %s", len(result), out)

        # Print sample
        log.info("")
        log.info("Sample headlines:")
        for _, row in result.head(8).iterrows():
            log.info("  [%s] %s", row.get('source','?')[:20], str(row.get('headline',''))[:80])
    else:
        log.warning("No articles downloaded after all retries.")
        log.warning("GDELT may be temporarily throttling this IP.")
        log.warning("Try again in 30+ minutes, or use demo data (DEMO_MODE=true in .env).")


if __name__ == "__main__":
    main()
