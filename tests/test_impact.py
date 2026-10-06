"""
tests/test_impact.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest
from src.risk.impact import compute_impact, compute_impact_from_dict


def test_impact_in_range():
    result = compute_impact(
        ticker="NVDA", sentiment=0.83, sentiment_confidence=0.94,
        event_type="Product/Partnership", event_weight=0.70,
        novelty=0.91, spike=6.2, evidence=94.0, hist_vol_pct=0.78,
    )
    assert 1.0 <= result.impact_score <= 10.0


def test_high_signal_gives_high_impact():
    high = compute_impact("NVDA", 0.95, 0.99, "M&A", 0.95, 1.0, 15.0, 95.0, 0.9)
    low  = compute_impact("NVDA", 0.10, 0.50, "Other", 0.3, 0.1, 1.1, 25.0, 0.1)
    assert high.impact_score > low.impact_score


def test_zero_sentiment_not_zero_impact():
    """Event type and evidence alone should give some impact."""
    result = compute_impact("JPM", 0.0, 0.5, "Earnings", 0.90, 0.8, 3.0, 70.0, 0.5)
    assert result.impact_score > 1.0


def test_impact_from_dict():
    d = {
        "ticker": "TSLA", "sentiment_score": -0.72, "sentiment_confidence": 0.88,
        "event_type": "Regulatory", "event_weight": 0.80,
        "novelty_score": 0.85, "spike_multiplier": 4.1,
        "evidence_score": 82.0, "hist_vol_pct": 0.85,
    }
    result = compute_impact_from_dict(d)
    assert 1 <= result.impact_score <= 10
    assert result.ticker == "TSLA"


def test_explanation_is_string():
    result = compute_impact("AAPL", 0.5, 0.8, "Earnings", 0.9, 0.7, 2.5, 65.0, 0.4)
    assert isinstance(result.explanation, str)
    assert len(result.explanation) > 10
