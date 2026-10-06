"""
src/nlp/entity.py
==================
Entity & Ticker Resolution Module.

Input:  "Nvidia's Blackwell demand continues to exceed expectations."
Output: Company="NVIDIA Corporation"  Ticker="NVDA"  Sector="Semiconductors"

Pipeline:
  1. spaCy NER  → extract ORG mentions
  2. Fuzzy match against a curated ticker→company→sector lookup table
  3. Dollar-sign ticker detection ($NVDA) as high-confidence fast path
  4. Returns top-1 match with confidence score

The resolved ticker becomes the JOIN key between the NLP layer and the
portfolio engine.

Prototype Universe (15 stocks):
  The prototype uses PROTOTYPE_UNIVERSE — a 15-stock diversified large-cap
  universe designed for reproducible evaluation. Each ticker has complete:
  entity mapping, historical prices, SEC CIK mapping, sector classification,
  and news retrieval coverage. The full TICKER_DB supports future expansion
  to 50/100 stocks without code changes.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
from fuzzywuzzy import process as fw_process

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prototype universe: 15 diversified large-cap stocks
# Chosen for: reliable entity mapping, SEC CIK coverage, sector diversity
# Extensible: add tickers to TICKER_DB to expand without code changes
# ---------------------------------------------------------------------------
PROTOTYPE_UNIVERSE: list[str] = [
    "AAPL",   # Technology
    "MSFT",   # Technology
    "NVDA",   # Semiconductors
    "AMZN",   # Consumer Discretionary
    "GOOGL",  # Technology
    "META",   # Technology
    "TSLA",   # Consumer Discretionary
    "JPM",    # Financials
    "BAC",    # Financials
    "XOM",    # Energy
    "JNJ",    # Healthcare
    "WMT",    # Consumer Staples
    "V",      # Financials
    "AVGO",   # Semiconductors
    "COST",   # Consumer Staples
]

# ---------------------------------------------------------------------------
# Full ticker database (extended for future 50/100-stock expansion)
# ---------------------------------------------------------------------------
TICKER_DB: dict[str, dict] = {
    "AAPL":  {"company": "Apple Inc.",              "sector": "Technology"},
    "MSFT":  {"company": "Microsoft Corporation",   "sector": "Technology"},
    "NVDA":  {"company": "NVIDIA Corporation",      "sector": "Semiconductors"},
    "GOOGL": {"company": "Alphabet Inc.",            "sector": "Technology"},
    "AMZN":  {"company": "Amazon.com Inc.",          "sector": "Consumer Discretionary"},
    "META":  {"company": "Meta Platforms Inc.",      "sector": "Technology"},
    "TSLA":  {"company": "Tesla Inc.",               "sector": "Consumer Discretionary"},
    "BRK.B": {"company": "Berkshire Hathaway",       "sector": "Financials"},
    "JPM":   {"company": "JPMorgan Chase & Co.",     "sector": "Financials"},
    "JNJ":   {"company": "Johnson & Johnson",        "sector": "Healthcare"},
    "V":     {"company": "Visa Inc.",                "sector": "Financials"},
    "PG":    {"company": "Procter & Gamble Co.",     "sector": "Consumer Staples"},
    "UNH":   {"company": "UnitedHealth Group",       "sector": "Healthcare"},
    "HD":    {"company": "Home Depot Inc.",          "sector": "Consumer Discretionary"},
    "MA":    {"company": "Mastercard Inc.",          "sector": "Financials"},
    "XOM":   {"company": "Exxon Mobil Corporation", "sector": "Energy"},
    "BAC":   {"company": "Bank of America Corp.",   "sector": "Financials"},
    "ABBV":  {"company": "AbbVie Inc.",              "sector": "Healthcare"},
    "CVX":   {"company": "Chevron Corporation",     "sector": "Energy"},
    "KO":    {"company": "Coca-Cola Company",       "sector": "Consumer Staples"},
    "PFE":   {"company": "Pfizer Inc.",             "sector": "Healthcare"},
    "AVGO":  {"company": "Broadcom Inc.",           "sector": "Semiconductors"},
    "MRK":   {"company": "Merck & Co. Inc.",        "sector": "Healthcare"},
    "DIS":   {"company": "Walt Disney Company",     "sector": "Communication Services"},
    "CSCO":  {"company": "Cisco Systems Inc.",      "sector": "Technology"},
    "WMT":   {"company": "Walmart Inc.",            "sector": "Consumer Staples"},
    "ACN":   {"company": "Accenture plc",           "sector": "Technology"},
    "MCD":   {"company": "McDonald's Corporation",  "sector": "Consumer Discretionary"},
    "NFLX":  {"company": "Netflix Inc.",            "sector": "Communication Services"},
    "AMD":   {"company": "Advanced Micro Devices",  "sector": "Semiconductors"},
    "INTC":  {"company": "Intel Corporation",       "sector": "Semiconductors"},
    "MU":    {"company": "Micron Technology",       "sector": "Semiconductors"},
    "CRM":   {"company": "Salesforce Inc.",         "sector": "Technology"},
    "ORCL":  {"company": "Oracle Corporation",      "sector": "Technology"},
    "IBM":   {"company": "IBM Corporation",         "sector": "Technology"},
    "GS":    {"company": "Goldman Sachs Group",     "sector": "Financials"},
    "MS":    {"company": "Morgan Stanley",          "sector": "Financials"},
    "GE":    {"company": "GE Aerospace",            "sector": "Industrials"},
    "BA":    {"company": "Boeing Company",          "sector": "Industrials"},
    "CAT":   {"company": "Caterpillar Inc.",        "sector": "Industrials"},
    "UPS":   {"company": "United Parcel Service",   "sector": "Industrials"},
    "MMM":   {"company": "3M Company",              "sector": "Industrials"},
    "LMT":   {"company": "Lockheed Martin",         "sector": "Defense"},
    "RTX":   {"company": "RTX Corporation",         "sector": "Defense"},
    "AMGN":  {"company": "Amgen Inc.",              "sector": "Healthcare"},
    "GILD":  {"company": "Gilead Sciences",         "sector": "Healthcare"},
    "BMY":   {"company": "Bristol-Myers Squibb",    "sector": "Healthcare"},
    "COST":  {"company": "Costco Wholesale",        "sector": "Consumer Staples"},
    "TGT":   {"company": "Target Corporation",      "sector": "Consumer Discretionary"},
    "LOW":   {"company": "Lowe's Companies",        "sector": "Consumer Discretionary"},
    "SBUX":  {"company": "Starbucks Corporation",   "sector": "Consumer Discretionary"},
}

# Build reverse maps for fuzzy matching
_COMPANY_TO_TICKER: dict[str, str] = {
    info["company"].lower(): ticker for ticker, info in TICKER_DB.items()
}
_COMPANY_NAMES: list[str] = list(_COMPANY_TO_TICKER.keys())

# Common aliases / abbreviations
_ALIASES: dict[str, str] = {
    "nvidia":     "NVDA",
    "apple":      "AAPL",
    "microsoft":  "MSFT",
    "alphabet":   "GOOGL",
    "google":     "GOOGL",
    "amazon":     "AMZN",
    "meta":       "META",
    "facebook":   "META",
    "tesla":      "TSLA",
    "jpmorgan":   "JPM",
    "chase":      "JPM",
    "netflix":    "NFLX",
    "broadcom":   "AVGO",
    "amd":        "AMD",
    "intel":      "INTC",
    "micron":     "MU",
    "salesforce": "CRM",
    "oracle":     "ORCL",
    "boeing":     "BA",
    "lockheed":   "LMT",
    "pfizer":     "PFE",
    "abbvie":     "ABBV",
    "amgen":      "AMGN",
    "gilead":     "GILD",
    "walmart":    "WMT",
    "costco":     "COST",
    "target":     "TGT",
    "starbucks":  "SBUX",
    "disney":     "DIS",
    "cisco":      "CSCO",
    "ibm":        "IBM",
    "goldman":    "GS",
    "morgan":     "MS",
    "caterpillar":"CAT",
    "blackwell":  "NVDA",  # product → company
    "h100":       "NVDA",
    "iphone":     "AAPL",
    "azure":      "MSFT",
    "copilot":    "MSFT",
    "aws":        "AMZN",
    "android":    "GOOGL",
    "starlink":   "TSLA",  # simplified
}

# Regex for $TICKER mentions
_DOLLAR_TICKER_RE = re.compile(r'\$([A-Z]{1,5}(?:\.[A-Z])?)\b')


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EntityMatch:
    text: str           # original mention
    ticker: str         # resolved ticker
    company: str        # full company name
    sector: str         # GICS sector
    confidence: float   # 0.0–1.0
    method: str         # "dollar_sign" | "alias" | "fuzzy" | "spacy_fuzzy"


@dataclass
class EntityResult:
    text: str
    matches: list[EntityMatch] = field(default_factory=list)

    @property
    def best(self) -> Optional[EntityMatch]:
        return max(self.matches, key=lambda m: m.confidence) if self.matches else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_entities(text: str) -> list[EntityMatch]:
    """
    Extract and resolve all company/ticker mentions in *text*.

    Returns a list of EntityMatch objects (may be empty), sorted by confidence.
    """
    matches: list[EntityMatch] = []
    seen_tickers: set[str] = set()

    # 1. Dollar-sign tickers – highest confidence
    for m in _DOLLAR_TICKER_RE.finditer(text):
        ticker = m.group(1).upper()
        if ticker in TICKER_DB and ticker not in seen_tickers:
            info = TICKER_DB[ticker]
            matches.append(EntityMatch(
                text=m.group(0), ticker=ticker,
                company=info["company"], sector=info["sector"],
                confidence=0.98, method="dollar_sign",
            ))
            seen_tickers.add(ticker)

    # 2. Alias lookup (case-insensitive)
    text_lower = text.lower()
    for alias, ticker in _ALIASES.items():
        if alias in text_lower and ticker not in seen_tickers:
            info = TICKER_DB.get(ticker, {})
            if info:
                matches.append(EntityMatch(
                    text=alias, ticker=ticker,
                    company=info["company"], sector=info["sector"],
                    confidence=0.90, method="alias",
                ))
                seen_tickers.add(ticker)

    # 3. spaCy NER + fuzzy match (if spaCy is available)
    try:
        nlp_matches = _spacy_ner_match(text, seen_tickers)
        matches.extend(nlp_matches)
    except Exception as exc:
        logger.debug("spaCy NER failed: %s", exc)

    # Sort by confidence descending
    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches


def resolve_primary(text: str) -> Optional[EntityMatch]:
    """Return only the single best entity match for a piece of text."""
    matches = resolve_entities(text)
    return matches[0] if matches else None


def ticker_info(ticker: str) -> dict:
    """Return sector and company for a known ticker."""
    return TICKER_DB.get(ticker.upper(), {"company": "Unknown", "sector": "Unknown"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_spacy_nlp():
    """Lazy-load spaCy model."""
    import spacy
    try:
        return spacy.load("en_core_web_lg")
    except OSError:
        return spacy.load("en_core_web_sm")


def _spacy_ner_match(text: str, already_found: set[str]) -> list[EntityMatch]:
    """Use spaCy to find ORG entities then fuzzy-match to our ticker DB."""
    nlp = _get_spacy_nlp()
    doc = nlp(text)
    org_mentions = [ent.text for ent in doc.ents if ent.label_ == "ORG"]

    matches = []
    for mention in org_mentions:
        mention_lower = mention.lower()
        result = fw_process.extractOne(mention_lower, _COMPANY_NAMES, score_cutoff=75)
        if result:
            company_name, score, _ = result
            ticker = _COMPANY_TO_TICKER[company_name]
            if ticker not in already_found:
                info = TICKER_DB[ticker]
                confidence = score / 100.0 * 0.85   # scale down vs direct match
                matches.append(EntityMatch(
                    text=mention, ticker=ticker,
                    company=info["company"], sector=info["sector"],
                    confidence=round(confidence, 3),
                    method="spacy_fuzzy",
                ))
                already_found.add(ticker)
    return matches


# ---------------------------------------------------------------------------
# Batch helper
# ---------------------------------------------------------------------------

def resolve_dataframe(df: pd.DataFrame, text_col: str = "headline") -> pd.DataFrame:
    """
    Apply entity resolution to each row of a DataFrame.
    Adds columns: ticker, company, sector, entity_confidence, entity_method.
    """
    results = df[text_col].fillna("").apply(resolve_primary)
    df = df.copy()
    df["ticker"]            = results.apply(lambda r: r.ticker if r else "")
    df["company"]           = results.apply(lambda r: r.company if r else "")
    df["sector"]            = results.apply(lambda r: r.sector if r else "")
    df["entity_confidence"] = results.apply(lambda r: r.confidence if r else 0.0)
    df["entity_method"]     = results.apply(lambda r: r.method if r else "none")
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    samples = [
        "Nvidia's Blackwell demand continues to exceed expectations.",
        "$TSLA surges after record delivery numbers beat Wall Street.",
        "Apple and Microsoft announce joint cloud infrastructure deal.",
        "JPMorgan raises price target on Amazon amid AWS growth.",
        "Boeing faces new FAA regulatory scrutiny over 737 MAX inspections.",
    ]
    for s in samples:
        match = resolve_primary(s)
        if match:
            print(f"Text:    {s[:60]}")
            print(f"Ticker:  {match.ticker}  ({match.company})")
            print(f"Sector:  {match.sector}  [conf={match.confidence:.2f}, method={match.method}]")
            print()
