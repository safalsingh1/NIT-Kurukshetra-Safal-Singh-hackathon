"""
scripts/generate_demo_data.py
==============================
Generate realistic demo datasets for all data/ directories.
Run this once before presenting the dashboard in demo mode.

Output:
  data/news/news.csv      - 500 synthetic GDELT-style news articles
  data/sec/sec.csv        - 100 synthetic SEC filings
  data/social/social.csv  - 300 synthetic Reddit posts
  data/prices.csv         - 2 years of synthetic stock prices (15-stock universe)
  data/sources.csv        - Data provenance manifest

Universe: 15 diversified large-cap stocks (PROTOTYPE_UNIVERSE)
This matches the entity resolution, backtesting, and portfolio layers.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

from src.nlp.entity import TICKER_DB, PROTOTYPE_UNIVERSE

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

DATA_DIR = ROOT / "data"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rand_dt(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


# Use the 15-stock prototype universe for all demo data generation
TICKERS = PROTOTYPE_UNIVERSE
EVENT_TYPES = ["Earnings", "M&A", "Product/Partnership", "Regulatory",
               "Legal", "Supply Chain", "Cybersecurity", "Leadership",
               "Geopolitical", "Macroeconomic", "Other"]
DOMAINS = [
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com", "cnbc.com",
    "marketwatch.com", "seekingalpha.com", "businessinsider.com",
    "thestreet.com", "barrons.com", "fortune.com", "techcrunch.com",
]
HEADLINES = [
    "{t} reports quarterly earnings that beat analyst expectations by {pct}%",
    "{t} announces strategic partnership with {partner} for AI development",
    "SEC opens preliminary investigation into {t} over disclosure claims",
    "{t} CEO {name} unexpectedly steps down; board to begin search",
    "{t} raises annual guidance following strong demand environment",
    "Analysts upgrade {t} to Buy, raise price target to ${price}",
    "{t} acquires {target} for ${deal}B in all-stock deal",
    "Supply chain disruption hits {t} manufacturing, Q4 outlook uncertain",
    "{t} receives FDA/FCC regulatory approval for key new product",
    "{t} reports data breach affecting {n}M customers",
    "Federal Reserve decision impacts {t} and broader market outlook",
    "{t} to launch next-gen AI chip, orders reportedly exceed supply",
    "{t} stock falls on weaker-than-expected revenue guidance",
    "{t} announces $5B share buyback program, dividend increase",
    "Geopolitical tensions raise concerns for {t} supply chain exposure",
]
PARTNERS = ["Google", "Microsoft", "Amazon", "NVIDIA", "Qualcomm", "Samsung"]
NAMES = ["John Smith", "Sarah Chen", "Robert Walsh", "Elena Martinez", "David Kim"]
TARGETS = ["TechStart AI", "DataCore Inc.", "CloudLogix", "SafeGuard Systems"]


def gen_headline(ticker: str) -> str:
    tmpl = random.choice(HEADLINES)
    return tmpl.format(
        t=ticker,
        pct=random.randint(3, 28),
        partner=random.choice(PARTNERS),
        name=random.choice(NAMES),
        price=random.randint(100, 900),
        deal=round(random.uniform(0.5, 12), 1),
        target=random.choice(TARGETS),
        n=random.randint(1, 50),
    )


# ---------------------------------------------------------------------------
# 1. News data
# ---------------------------------------------------------------------------

def generate_news(n: int = 500) -> pd.DataFrame:
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=365)
    rows  = []
    for i in range(n):
        ticker = random.choice(TICKERS)
        sent   = round(random.gauss(0, 0.5), 3)
        sent   = max(-1.0, min(1.0, sent))
        ts     = rand_dt(start, end)
        rows.append({
            "id":       f"news-{i:05d}",
            "timestamp":ts.isoformat(),
            "url":      f"https://{random.choice(DOMAINS)}/article/{i}",
            "source":   random.choice(DOMAINS),
            "headline": gen_headline(ticker),
            "body":     "",
            "entities": ticker,
            "tone":     round(sent * 5, 2),
            "mode":     "demo",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. SEC filing data
# ---------------------------------------------------------------------------

def generate_sec(n: int = 100) -> pd.DataFrame:
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=365)
    form_types = ["8-K", "10-Q", "10-K", "8-K", "8-K"]   # 8-K most common

    rows = []
    for i in range(n):
        ticker = random.choice(TICKERS)
        info   = TICKER_DB[ticker]
        ts     = rand_dt(start, end)
        form   = random.choice(form_types)
        rows.append({
            "id":          f"SEC-{i:06d}",
            "timestamp":   ts.isoformat(),
            "ticker":      ticker,
            "cik":         f"{random.randint(100000, 999999):010d}",
            "company":     info["company"],
            "form_type":   form,
            "description": f"Period of report: {(ts - timedelta(days=90)).strftime('%Y-%m-%d')}",
            "url":         f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={i}&type={form}",
            "mode":        "demo",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Social data
# ---------------------------------------------------------------------------

def generate_social(n: int = 300) -> pd.DataFrame:
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=365)
    subreddits = ["wallstreetbets", "investing", "stocks", "finance", "StockMarket"]
    titles = [
        "Anyone else holding {t}? Earnings play looks interesting",
        "{t} DD: Why I think this is a 10-bagger",
        "Sold {t} today, here's why",
        "{t} earnings tomorrow – what's your position?",
        "Hot take: {t} is overvalued at current prices",
        "Just bought {t} calls for the first time, nervous",
        "{t} is about to moon based on these signals",
        "{t} CEO news — thoughts?",
    ]
    rows = []
    for i in range(n):
        ticker = random.choice(TICKERS)
        ts     = rand_dt(start, end)
        sent   = round(random.gauss(0.1, 0.6), 3)
        rows.append({
            "id":           f"social-{i:05d}",
            "timestamp":    ts.isoformat(),
            "platform":     "reddit",
            "author":       f"user_{random.randint(1000, 99999)}",
            "subreddit":    random.choice(subreddits),
            "title":        random.choice(titles).format(t=ticker),
            "body":         "",
            "score":        random.randint(0, 5000),
            "entities":     ticker,
            "mode":         "demo",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. Prices
# ---------------------------------------------------------------------------

def generate_prices(tickers: list[str], n_days: int = 504) -> pd.DataFrame:
    """GBM synthetic price series."""
    dates  = pd.bdate_range(end=datetime.today(), periods=n_days)
    prices = {}
    for t in tickers:
        s0    = random.uniform(80, 600)
        mu    = random.uniform(0.05, 0.30) / 252
        sigma = random.uniform(0.15, 0.50) / np.sqrt(252)
        shocks= np.random.normal(mu, sigma, n_days)
        prices[t] = np.round(s0 * np.exp(np.cumsum(shocks)), 2)
    df = pd.DataFrame(prices, index=dates)
    df.index.name = "date"
    return df


# ---------------------------------------------------------------------------
# 5. Sources provenance
# ---------------------------------------------------------------------------

def generate_sources() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "dataset":     "news.csv",
            "origin":      "GDELT Project (gdeltproject.org) — synthetic sample",
            "type":        "News articles",
            "license":     "GDELT is open/public domain",
            "n_records":   500,
            "date_range":  "2023-10 to 2024-10",
        },
        {
            "dataset":     "sec.csv",
            "origin":      "SEC EDGAR API (data.sec.gov) — synthetic sample",
            "type":        "SEC filings (8-K, 10-Q, 10-K)",
            "license":     "Public domain (U.S. Government)",
            "n_records":   100,
            "date_range":  "2023-10 to 2024-10",
        },
        {
            "dataset":     "social.csv",
            "origin":      "Historical Reddit r/wallstreetbets & r/investing — synthetic sample",
            "type":        "Social media posts",
            "license":     "For research / demo use only",
            "n_records":   300,
            "date_range":  "2023-10 to 2024-10",
        },
        {
            "dataset":     "prices.csv",
            "origin":      "Synthetic GBM price series — no real market data",
            "type":        "Daily OHLCV (close prices)",
            "license":     "Generated for demo",
            "n_records":   504,
            "date_range":  "2022-10 to 2024-10",
        },
    ])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating demo data...")

    # News
    news = generate_news(500)
    (DATA_DIR / "news").mkdir(parents=True, exist_ok=True)
    news.to_csv(DATA_DIR / "news" / "news.csv", index=False)
    print(f"[OK] news.csv: {len(news)} rows")

    # SEC
    sec = generate_sec(100)
    (DATA_DIR / "sec").mkdir(parents=True, exist_ok=True)
    sec.to_csv(DATA_DIR / "sec" / "sec.csv", index=False)
    print(f"[OK] sec.csv: {len(sec)} rows")

    # Social
    social = generate_social(300)
    (DATA_DIR / "social").mkdir(parents=True, exist_ok=True)
    social.to_csv(DATA_DIR / "social" / "social.csv", index=False)
    print(f"[OK] social.csv: {len(social)} rows")

    # Prices
    prices = generate_prices(TICKERS, n_days=504)
    prices.to_csv(DATA_DIR / "prices.csv")
    print(f"[OK] prices.csv: {len(prices)} trading days x {len(TICKERS)} tickers")

    # Sources
    sources = generate_sources()
    sources.to_csv(DATA_DIR / "sources.csv", index=False)
    print(f"[OK] sources.csv: {len(sources)} entries")

    print("\nAll demo data generated in data/")


if __name__ == "__main__":
    main()
