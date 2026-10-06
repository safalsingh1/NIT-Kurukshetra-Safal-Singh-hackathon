"""
src/backtest/metrics.py
========================
Portfolio Performance Metrics.

Computes all metrics required for the ablation study:
  - Cumulative Return
  - Annualized Return
  - Sharpe Ratio (annualized)
  - Maximum Drawdown
  - Annualized Volatility
  - Turnover (mean per rebalance)
  - Hit Rate (fraction of rebalances that were profitable)
  - Calmar Ratio
  - Sortino Ratio (downside deviation)
  - Beta / Alpha vs S&P 500 (if benchmark provided)
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_metrics(
    portfolio_values: pd.Series,
    risk_free_rate: float = 0.05,
    benchmark: Optional[pd.Series] = None,
    turnover_series: Optional[pd.Series] = None,
) -> dict:
    """
    Compute comprehensive performance metrics.

    Parameters
    ----------
    portfolio_values : Series of portfolio NAV (indexed by date)
    risk_free_rate   : Annual risk-free rate (default 5%)
    benchmark        : Optional benchmark NAV series for alpha/beta
    turnover_series  : Optional daily turnover series

    Returns
    -------
    dict with all computed metrics
    """
    pv = portfolio_values.dropna()
    if len(pv) < 2:
        return _empty_metrics()

    returns = pv.pct_change().dropna()

    cum_return     = _cumulative_return(pv)
    ann_return     = _annualised_return(returns)
    ann_vol        = _annualised_volatility(returns)
    sharpe         = _sharpe_ratio(returns, risk_free_rate)
    sortino        = _sortino_ratio(returns, risk_free_rate)
    max_dd         = _max_drawdown(pv)
    calmar         = ann_return / abs(max_dd) if abs(max_dd) > 0 else np.nan

    metrics = {
        "cumulative_return":    round(cum_return,  4),
        "annualised_return":    round(ann_return,  4),
        "annualised_volatility":round(ann_vol,     4),
        "sharpe_ratio":         round(sharpe,      4),
        "sortino_ratio":        round(sortino,     4),
        "max_drawdown":         round(max_dd,      4),
        "calmar_ratio":         round(calmar,      4) if not np.isnan(calmar) else None,
        "n_trading_days":       len(returns),
    }

    if turnover_series is not None:
        metrics["mean_turnover"]  = round(float(turnover_series.mean()), 4)
        metrics["total_turnover"] = round(float(turnover_series.sum()),  4)

    if benchmark is not None:
        alpha, beta = _alpha_beta(returns, benchmark)
        metrics["alpha"]      = round(alpha, 4)
        metrics["beta"]       = round(beta,  4)
        metrics["information_ratio"] = round(_information_ratio(returns, benchmark), 4)

    return metrics


def compute_hit_rate(
    rebalance_events: list[dict],
    prices: pd.DataFrame,
) -> float:
    """
    Compute the fraction of rebalancing trades that were directionally correct.

    A trade is "correct" if:
    - An increase in weight was followed by a positive return in the next N days
    - A decrease in weight was followed by a negative return in the next N days

    Returns hit_rate ∈ [0, 1]
    """
    if not rebalance_events:
        return 0.5

    hits = 0
    total = 0
    forward_window = 5   # 5 trading days

    for event in rebalance_events:
        ticker    = event.get("ticker")
        date      = pd.Timestamp(event.get("date"))
        direction = event.get("direction", "Hold")

        if direction == "Hold" or ticker not in prices.columns:
            continue

        try:
            price_now  = prices.loc[date, ticker]
            future_idx = prices.index.get_loc(date) + forward_window
            if future_idx >= len(prices):
                continue
            price_future = prices.iloc[future_idx][ticker]
            fwd_return   = (price_future - price_now) / price_now
        except (KeyError, IndexError):
            continue

        hit = (direction == "Increase" and fwd_return > 0) or \
              (direction == "Decrease" and fwd_return < 0)
        hits += int(hit)
        total += 1

    return round(hits / total, 4) if total > 0 else 0.5


def format_metrics_table(metrics: dict) -> pd.DataFrame:
    """Format metrics dict as a display-ready DataFrame."""
    labels = {
        "cumulative_return":     "Cumulative Return",
        "annualised_return":     "Annualised Return",
        "annualised_volatility": "Annualised Volatility",
        "sharpe_ratio":          "Sharpe Ratio",
        "sortino_ratio":         "Sortino Ratio",
        "max_drawdown":          "Max Drawdown",
        "calmar_ratio":          "Calmar Ratio",
        "mean_turnover":         "Mean Turnover (per event)",
        "alpha":                 "Alpha (vs benchmark)",
        "beta":                  "Beta (vs benchmark)",
        "information_ratio":     "Information Ratio",
    }
    rows = []
    for key, label in labels.items():
        val = metrics.get(key)
        if val is None:
            continue
        is_pct = key in ("cumulative_return", "annualised_return",
                         "annualised_volatility", "max_drawdown", "mean_turnover")
        formatted = f"{val:.2%}" if is_pct else f"{val:.4f}"
        rows.append({"Metric": label, "Value": formatted})
    return pd.DataFrame(rows)


def compare_strategies(results: dict) -> pd.DataFrame:
    """
    Create a comparison table across strategies.

    Parameters
    ----------
    results : {strategy_id: BacktestResult}

    Returns
    -------
    DataFrame with strategies as rows, metrics as columns
    """
    rows = []
    for strat_id, result in results.items():
        row = {"Strategy": result.strategy_name}
        row.update({
            "Cum. Return":  f"{result.metrics.get('cumulative_return', 0):.2%}",
            "Ann. Return":  f"{result.metrics.get('annualised_return', 0):.2%}",
            "Sharpe":       f"{result.metrics.get('sharpe_ratio', 0):.3f}",
            "Max DD":       f"{result.metrics.get('max_drawdown', 0):.2%}",
            "Volatility":   f"{result.metrics.get('annualised_volatility', 0):.2%}",
            "Mean Turnover":f"{result.metrics.get('mean_turnover', 0):.2%}",
        })
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Internal metric functions
# ---------------------------------------------------------------------------

def _cumulative_return(pv: pd.Series) -> float:
    return float((pv.iloc[-1] / pv.iloc[0]) - 1.0)


def _annualised_return(returns: pd.Series) -> float:
    n = len(returns)
    if n < 2:
        return 0.0
    total = float((1 + returns).prod())
    return float(total ** (TRADING_DAYS_PER_YEAR / n) - 1.0)


def _annualised_volatility(returns: pd.Series) -> float:
    return float(returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def _sharpe_ratio(returns: pd.Series, rf: float) -> float:
    ann_ret = _annualised_return(returns)
    ann_vol = _annualised_volatility(returns)
    return (ann_ret - rf) / ann_vol if ann_vol > 0 else 0.0


def _sortino_ratio(returns: pd.Series, rf: float) -> float:
    ann_ret  = _annualised_return(returns)
    downside = returns[returns < 0].std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    return (ann_ret - rf) / downside if downside > 0 else 0.0


def _max_drawdown(pv: pd.Series) -> float:
    roll_max = pv.cummax()
    drawdown = (pv - roll_max) / roll_max
    return float(drawdown.min())


def _alpha_beta(portfolio_returns: pd.Series, benchmark: pd.Series) -> tuple[float, float]:
    bench_returns = benchmark.pct_change().dropna()
    # Align
    aligned = pd.concat([portfolio_returns, bench_returns], axis=1).dropna()
    if len(aligned) < 10:
        return 0.0, 1.0
    port_r, bench_r = aligned.iloc[:, 0], aligned.iloc[:, 1]

    cov_matrix = np.cov(port_r, bench_r)
    beta  = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] > 0 else 1.0
    alpha = float(port_r.mean() - beta * bench_r.mean()) * TRADING_DAYS_PER_YEAR
    return alpha, beta


def _information_ratio(portfolio_returns: pd.Series, benchmark: pd.Series) -> float:
    bench_returns = benchmark.pct_change().dropna()
    aligned = pd.concat([portfolio_returns, bench_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 0.0
    active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    return float(active.mean() / active.std() * np.sqrt(TRADING_DAYS_PER_YEAR)) if active.std() > 0 else 0.0


def _empty_metrics() -> dict:
    return {
        "cumulative_return": 0.0,
        "annualised_return": 0.0,
        "annualised_volatility": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown": 0.0,
    }
