"""
tests/test_entity.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest
from src.nlp.entity import resolve_primary, resolve_entities, ticker_info, TICKER_DB


def test_dollar_sign_resolution():
    result = resolve_primary("$NVDA surges after record earnings beat")
    assert result is not None
    assert result.ticker == "NVDA"
    assert result.confidence >= 0.95
    assert result.method == "dollar_sign"


def test_alias_resolution():
    result = resolve_primary("Nvidia's Blackwell demand continues to exceed expectations")
    assert result is not None
    assert result.ticker == "NVDA"


def test_product_alias():
    """Product names should resolve to their parent company."""
    result = resolve_primary("iPhone 17 sales disappoint in Asian markets")
    assert result is not None
    assert result.ticker == "AAPL"


def test_multiple_entities():
    results = resolve_entities("Apple and Microsoft announce cloud partnership")
    tickers = [r.ticker for r in results]
    assert "AAPL" in tickers or "MSFT" in tickers


def test_unknown_text():
    result = resolve_primary("The quick brown fox jumps over the lazy dog")
    # Should return None or very low confidence
    if result:
        assert result.confidence < 0.5


def test_ticker_info():
    info = ticker_info("NVDA")
    assert info["company"] == "NVIDIA Corporation"
    assert info["sector"] == "Semiconductors"


def test_ticker_db_coverage():
    """All tickers in TICKER_DB should have company and sector."""
    for ticker, info in TICKER_DB.items():
        assert "company" in info, f"{ticker} missing company"
        assert "sector" in info,  f"{ticker} missing sector"


def test_confidence_ordering():
    """Dollar-sign matches should have higher confidence than alias matches."""
    dollar = resolve_primary("$AAPL earnings beat expectations")
    alias  = resolve_primary("Apple earnings beat expectations")
    if dollar and alias:
        assert dollar.confidence >= alias.confidence
