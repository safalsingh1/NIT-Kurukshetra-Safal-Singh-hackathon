"""
scripts/download_live_data.py
==============================
Download live data from:
  1. GDELT Doc 2.0 API  (free, no key, news articles)
  2. SEC EDGAR API      (free, no key, 8-K filings for our 15 tickers)

Saves results to:
  data/news/live_news.csv
  data/sec/live_sec.csv

Usage:
  python scripts/download_live_data.py
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

# ── make sure project root is on path ────────────────────────────────────────
ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("download")

# ── Our 15-stock prototype universe ──────────────────────────────────────────
UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "JPM", "BAC", "WMT",
    "XOM", "JNJ", "UNH", "V", "MA",
]

# SEC CIK map for our universe (avoids a lookup API call)
CIK_MAP = {
    "AAPL":  "0000320193",
    "MSFT":  "0000789019",
    "NVDA":  "0001045810",
    "AMZN":  "0001018724",
    "GOOGL": "0001652044",
    "META":  "0001326801",
    "TSLA":  "0001318605",
    "JPM":   "0000019617",
    "BAC":   "0000070858",
    "WMT":   "0000104169",
    "XOM":   "0000034088",
    "JNJ":   "0000200406",
    "UNH":   "0000731766",
    "V":     "0001403161",
    "MA":    "0001391690",
}

DATA_DIR = ROOT / "data"


# ─────────────────────────────────────────────────────────────────────────────
# 1. GDELT
# ─────────────────────────────────────────────────────────────────────────────

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_SCHEMA = ["id", "timestamp", "url", "source", "headline", "body",
                "entities", "tone", "mode"]


def _gdelt_query(query: str, hours: int = 48) -> pd.DataFrame:
    start_dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    params = {
        "query":         query,
        "mode":          "artlist",
        "maxrecords":    250,
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "format":        "json",
        "sort":          "DateDesc",
    }
    resp = requests.get(GDELT_API, params=params, timeout=30)
    resp.raise_for_status()
    articles = resp.json().get("articles", [])
    rows = []
    for a in articles:
        rows.append({
            "id":        a.get("url", ""),
            "timestamp": a.get("seendate", ""),
            "url":       a.get("url", ""),
            "source":    a.get("domain", ""),
            "headline":  a.get("title", ""),
            "body":      "",
            "entities":  query,
            "tone":      float(a.get("tone", 0)),
            "mode":      "live",
        })
    return pd.DataFrame(rows, columns=GDELT_SCHEMA) if rows else pd.DataFrame(columns=GDELT_SCHEMA)


def download_gdelt():
    log.info("=" * 55)
    log.info("GDELT -- Downloading news for %d tickers (48h lookback)", len(UNIVERSE))
    log.info("=" * 55)

    all_frames = []
    batches = [
        "NVIDIA OR Apple OR Microsoft OR Amazon",
        "Google OR Meta OR Tesla OR JPMorgan",
        "Bank of America OR Walmart OR ExxonMobil",
        "Johnson & Johnson OR UnitedHealth OR Visa OR Mastercard",
        "S&P 500 earnings financial risk",
    ]

    for i, q in enumerate(batches, 1):
        log.info("  [%d/%d] Query: %s", i, len(batches), q[:60])
        try:
            df = _gdelt_query(q, hours=48)
            all_frames.append(df)
            log.info("        -> %d articles", len(df))
        except Exception as e:
            log.warning("        -> FAILED: %s", e)
        if i < len(batches):
            time.sleep(1.5)   # GDELT rate limit: <=1 req/sec

    if all_frames:
        result = pd.concat(all_frames, ignore_index=True)
        result = result.drop_duplicates(subset=["url"])
        result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")

        out = DATA_DIR / "news" / "live_news.csv"
        result.to_csv(out, index=False)
        log.info("GDELT done -- %d unique articles saved -> %s", len(result), out)
        return result
    else:
        log.warning("No GDELT articles downloaded.")
        return pd.DataFrame(columns=GDELT_SCHEMA)


# ─────────────────────────────────────────────────────────────────────────────
# 2. SEC EDGAR
# ─────────────────────────────────────────────────────────────────────────────

SEC_HEADER = {"User-Agent": "FinRiskAI research@finriskai.io"}
SEC_SCHEMA = ["id", "timestamp", "ticker", "cik", "company",
              "form_type", "description", "url", "mode"]


def _sec_fetch_recent(ticker: str, cik: str, days: int = 30) -> pd.DataFrame:
    """Fetch recent filings for one ticker from SEC submissions endpoint."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=SEC_HEADER, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    company = data.get("name", ticker)
    filings = data.get("filings", {}).get("recent", {})

    form_types   = filings.get("form", [])
    dates        = filings.get("filingDate", [])
    accessions   = filings.get("accessionNumber", [])
    descriptions = filings.get("primaryDocument", [])

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = []
    for ft, dt, acc, desc in zip(form_types, dates, accessions, descriptions):
        if ft not in ("8-K", "10-Q", "10-K"):
            continue
        if dt < cutoff:
            continue
        rows.append({
            "id":          acc,
            "timestamp":   dt,
            "ticker":      ticker,
            "cik":         cik,
            "company":     company,
            "form_type":   ft,
            "description": desc,
            "url":         f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={ft}&dateb=&owner=include&count=10",
            "mode":        "live",
        })

    return pd.DataFrame(rows, columns=SEC_SCHEMA) if rows else pd.DataFrame(columns=SEC_SCHEMA)


def download_sec():
    log.info("=" * 55)
    log.info("SEC EDGAR -- Downloading filings for %d tickers (30d)", len(CIK_MAP))
    log.info("=" * 55)

    all_frames = []
    for i, (ticker, cik) in enumerate(CIK_MAP.items(), 1):
        log.info("  [%02d/%02d] %s (CIK %s)", i, len(CIK_MAP), ticker, cik)
        try:
            df = _sec_fetch_recent(ticker, cik, days=30)
            all_frames.append(df)
            log.info("          -> %d filings", len(df))
        except Exception as e:
            log.warning("          -> FAILED: %s", e)
        if i < len(CIK_MAP):
            time.sleep(0.15)  # ~7 req/sec -- well within SEC limits

    if all_frames:
        result = pd.concat(all_frames, ignore_index=True)
        result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
        result = result.sort_values("timestamp", ascending=False).reset_index(drop=True)

        out = DATA_DIR / "sec" / "live_sec.csv"
        result.to_csv(out, index=False)
        log.info("SEC done -- %d filings saved -> %s", len(result), out)
        return result
    else:
        log.warning("No SEC filings downloaded.")
        return pd.DataFrame(columns=SEC_SCHEMA)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("FinRisk AI -- Live Data Download")
    log.info("Time: %s UTC", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
    log.info("")

    gdelt_df = download_gdelt()
    log.info("")
    sec_df   = download_sec()

    log.info("")
    log.info("=" * 55)
    log.info("SUMMARY")
    log.info("  GDELT articles : %d", len(gdelt_df))
    log.info("  SEC filings    : %d", len(sec_df))
    log.info("")
    if not sec_df.empty:
        log.info("Recent SEC filings:")
        for _, row in sec_df.head(10).iterrows():
            log.info("  %-6s  %-6s  %s", row['ticker'], row['form_type'], str(row['timestamp'])[:10])
    log.info("=" * 55)
    log.info("Done! Saved to data/news/live_news.csv and data/sec/live_sec.csv")
