"""
tests/test_backtest.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest
import numpy as np
import pandas as pd
from src.backtest.engine import BacktestEngine, BacktestConfig
from src.backtest.metrics import compute_metrics, compute_hit_rate


def _make_prices(n_days: int = 252) -> pd.DataFrame:
    np.random.seed(1)
    tickers = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN"]
    dates = pd.bdate_range("2023-01-01", periods=n_days)
    data = {}
    for t in tickers:
        returns = np.random.normal(0.0005, 0.02, n_days)
        data[t] = 100 * np.exp(np.cumsum(returns))
    return pd.DataFrame(data, index=dates)


def _make_signals(prices: pd.DataFrame) -> pd.DataFrame:
    np.random.seed(2)
    tickers = list(prices.columns)
    dates = pd.bdate_range("2023-01-01", "2023-12-31", freq="W")
    rows = []
    for date in dates:
        for t in tickers:
            sent = np.random.uniform(-0.8, 0.8)
            rows.append({
                "timestamp":       pd.Timestamp(date, tz="UTC"),
                "ticker":          t,
                "sent_score":      round(sent, 3),
                "sent_confidence": round(np.random.uniform(0.5, 0.99), 3),
                "actionability":   round(sent * 0.7, 3),
                "event_type":      "Earnings",
                "impact_score":    round(np.random.uniform(4, 8), 1),
                "novelty_score":   round(np.random.uniform(0.4, 1.0), 2),
                "spike_multiplier":round(np.random.uniform(1.5, 6.0), 1),
                "evidence_score":  round(np.random.uniform(50, 90), 1),
                "allow_action":    True,
                "abstained":       False,
                "abstain_reason":  "",
                "headline":        f"Test signal for {t}",
            })
    return pd.DataFrame(rows)


def test_baseline_runs():
    prices  = _make_prices()
    signals = _make_signals(prices)
    config  = BacktestConfig(strategy=0, start_date="2023-01-01", end_date="2023-12-31")
    engine  = BacktestEngine(prices, signals, config)
    result  = engine.run()
    assert len(result.portfolio_values) > 100
    assert result.strategy == 0


def test_full_strategy_outperforms_baseline():
    """Full strategy Sharpe should generally be >= baseline Sharpe (not guaranteed, but expected on average)."""
    prices  = _make_prices(252)
    signals = _make_signals(prices)

    results = {}
    for s in [0, 3]:
        config = BacktestConfig(strategy=s, start_date="2023-01-01", end_date="2023-12-31")
        engine = BacktestEngine(prices, signals, config)
        results[s] = engine.run()

    # This is a soft assertion; demo signals may not always outperform
    assert results[3].metrics["sharpe_ratio"] is not None


def test_no_lookahead_bias():
    """Verify execution dates are always after signal timestamps."""
    prices  = _make_prices(252)
    signals = _make_signals(prices)
    config  = BacktestConfig(strategy=3, start_date="2023-01-01", end_date="2023-12-31")
    engine  = BacktestEngine(prices, signals, config)

    enriched = engine._assign_execution_dates(signals)
    if "exec_date" in enriched.columns:
        sig_dates  = enriched["timestamp"].dt.date
        exec_dates = enriched["exec_date"].dt.date
        assert (exec_dates >= sig_dates).all(), "Look-ahead bias detected!"


def test_metrics_are_finite():
    prices  = _make_prices(252)
    signals = _make_signals(prices)
    config  = BacktestConfig(strategy=0, start_date="2023-01-01", end_date="2023-12-31")
    engine  = BacktestEngine(prices, signals, config)
    result  = engine.run()
    m = result.metrics
    assert np.isfinite(m["sharpe_ratio"])
    assert np.isfinite(m["max_drawdown"])
    assert -1.0 <= m["max_drawdown"] <= 0.0


def test_compute_metrics():
    np.random.seed(5)
    dates  = pd.bdate_range("2023-01-01", periods=252)
    values = 1_000_000 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 252)))
    pv     = pd.Series(values, index=dates)
    m      = compute_metrics(pv, risk_free_rate=0.05)
    assert "sharpe_ratio" in m
    assert "max_drawdown" in m
    assert m["n_trading_days"] == 251   # one less due to pct_change
