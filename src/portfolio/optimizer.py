"""
src/portfolio/optimizer.py
==========================
Risk-Aware Constrained Portfolio Optimizer using CVXPY.

Optimization Problem:
  maximize:   Σ_i actionability_i * w_i
            - lambda_risk * w^T Σ w
            - lambda_turn * ||w - w_prev||_1

  subject to:
    Σ w_i = 1                                  (full investment)
    0 ≤ w_i ≤ 0.15                             (max single stock 15%)
    Σ_{i ∈ sector_k} w_i ≤ sector_cap_k       (sector cap)
    ||w - w_prev||_1 ≤ max_turnover            (turnover ≤ 10%)
    w_i = w_prev_i   if confidence_i < 0.50   (abstention)

This is a Quadratic Program (QP) due to the w^T Σ w term.
CVXPY dispatches to OSQP or ECOS solvers automatically.

Why not naive "if signal > 0: weight += 2%"?
  Because a strong positive signal on a highly correlated,
  volatile stock may actually increase portfolio risk more
  than it improves expected return. The QP balances both.

Output:
  NVDA signal = +0.81 → was 8.0% → becomes 10.7% (not blindly 15%)
  TSLA signal = -0.67 → was 10.0% → becomes 6.9%
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from src.portfolio.constraints import (
    PortfolioConstraints,
    build_weight_bounds,
    get_sector_groups,
    validate_weights,
)
from src.nlp.entity import TICKER_DB

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class OptimizationResult:
    tickers: list[str]
    prev_weights: dict[str, float]
    new_weights: dict[str, float]
    turnover: float
    portfolio_variance: float
    objective_value: float
    status: str                      # "optimal" | "infeasible" | "fallback"
    violations: list[str]
    trades: pd.DataFrame             # ticker, from_weight, to_weight, delta


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def optimize(
    tickers: list[str],
    actionabilities: dict[str, float],           # {ticker: [-1, +1]}
    prev_weights: dict[str, float],              # {ticker: weight}
    cov_matrix: np.ndarray,                     # (N, N) covariance matrix (daily returns)
    confidences: Optional[dict[str, float]] = None,
    constraints: Optional[PortfolioConstraints] = None,
) -> OptimizationResult:
    """
    Run the constrained portfolio optimization.

    Parameters
    ----------
    tickers         : Ordered list of tickers (defines index ordering)
    actionabilities : Signal scores {ticker: float}
    prev_weights    : Current portfolio weights
    cov_matrix      : Covariance matrix of daily returns (annualised)
    confidences     : Signal confidence per ticker (triggers abstention)
    constraints     : PortfolioConstraints (uses defaults if None)

    Returns
    -------
    OptimizationResult
    """
    import cvxpy as cp

    if constraints is None:
        constraints = PortfolioConstraints()
    if confidences is None:
        confidences = {t: 1.0 for t in tickers}

    N = len(tickers)
    idx = {t: i for i, t in enumerate(tickers)}

    # Ensure equal weight for missing tickers
    equal_w = 1.0 / N
    prev_w_arr = np.array([prev_weights.get(t, equal_w) for t in tickers])
    prev_w_arr = prev_w_arr / prev_w_arr.sum()   # normalise

    act_arr = np.array([actionabilities.get(t, 0.0) for t in tickers])

    # ── Build bounds ──────────────────────────────────────────────────────
    bounds = build_weight_bounds(tickers, prev_weights, confidences, constraints)
    lb_arr = np.array([b.lb for b in bounds])
    ub_arr = np.array([b.ub for b in bounds])

    # ── Sector groups ─────────────────────────────────────────────────────
    ticker_info = {t: TICKER_DB.get(t, {"sector": "Unknown"}) for t in tickers}
    sector_groups = get_sector_groups(tickers, ticker_info)

    # ── CVXPY variables ───────────────────────────────────────────────────
    w = cp.Variable(N, name="weights")

    # ── Objective: signal benefit – risk penalty – turnover penalty ───────
    signal_benefit = act_arr @ w
    risk_penalty   = constraints.lambda_risk * cp.quad_form(w, cov_matrix)
    turnover_pen   = constraints.lambda_turnover * cp.norm1(w - prev_w_arr)

    objective = cp.Maximize(signal_benefit - risk_penalty - turnover_pen)

    # ── Constraints ───────────────────────────────────────────────────────
    cvxpy_constraints = [
        cp.sum(w) == 1,
        w >= lb_arr,
        w <= ub_arr,
        cp.norm1(w - prev_w_arr) <= constraints.max_turnover,
    ]

    # Sector caps
    for sector, indices in sector_groups.items():
        cap = constraints.get_sector_cap(sector)
        cvxpy_constraints.append(cp.sum(w[indices]) <= cap)

    # ── Solve ─────────────────────────────────────────────────────────────
    prob = cp.Problem(objective, cvxpy_constraints)
    try:
        prob.solve(solver=cp.OSQP, warm_start=True, verbose=False)
    except Exception:
        try:
            prob.solve(solver=cp.ECOS, verbose=False)
        except Exception as e:
            logger.warning("Optimization failed: %s – returning equal-weight", e)
            return _fallback_result(tickers, prev_w_arr, equal_w)

    if w.value is None or prob.status not in ("optimal", "optimal_inaccurate"):
        logger.warning("Optimizer status: %s – returning previous weights", prob.status)
        return _fallback_result(tickers, prev_w_arr, equal_w)

    new_w_arr = np.array(w.value).flatten()
    new_w_arr = np.clip(new_w_arr, 0, constraints.max_weight)
    new_w_arr = new_w_arr / new_w_arr.sum()   # re-normalise after clip

    new_weights = {t: float(new_w_arr[i]) for i, t in enumerate(tickers)}
    turnover = float(np.abs(new_w_arr - prev_w_arr).sum())
    portfolio_variance = float(new_w_arr @ cov_matrix @ new_w_arr)

    # ── Validation ────────────────────────────────────────────────────────
    violations = validate_weights(
        new_w_arr, tickers, bounds, constraints, sector_groups, prev_w_arr
    )
    if violations:
        logger.warning("Constraint violations detected: %s", violations)

    # ── Build trades DataFrame ────────────────────────────────────────────
    trades = _build_trades_df(tickers, prev_w_arr, new_w_arr)

    return OptimizationResult(
        tickers=tickers,
        prev_weights={t: float(prev_w_arr[i]) for i, t in enumerate(tickers)},
        new_weights=new_weights,
        turnover=round(turnover, 4),
        portfolio_variance=round(portfolio_variance, 6),
        objective_value=round(float(prob.value) if prob.value else 0.0, 6),
        status=prob.status or "unknown",
        violations=violations,
        trades=trades,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_trades_df(
    tickers: list[str],
    prev: np.ndarray,
    new: np.ndarray,
) -> pd.DataFrame:
    rows = []
    for i, t in enumerate(tickers):
        delta = new[i] - prev[i]
        rows.append({
            "ticker":       t,
            "from_weight":  round(float(prev[i]), 4),
            "to_weight":    round(float(new[i]),  4),
            "delta":        round(float(delta),   4),
            "direction":    "▲" if delta > 0.001 else ("▼" if delta < -0.001 else "–"),
        })
    return pd.DataFrame(rows).sort_values("delta", ascending=False)


def _fallback_result(tickers, prev_w_arr, equal_w) -> OptimizationResult:
    prev_weights_d = {t: float(prev_w_arr[i]) for i, t in enumerate(tickers)}
    return OptimizationResult(
        tickers=tickers,
        prev_weights=prev_weights_d,
        new_weights=prev_weights_d,
        turnover=0.0,
        portfolio_variance=0.0,
        objective_value=0.0,
        status="fallback",
        violations=["Optimization failed – returning previous weights"],
        trades=_build_trades_df(tickers, prev_w_arr, prev_w_arr),
    )


# ---------------------------------------------------------------------------
# Covariance estimation utilities
# ---------------------------------------------------------------------------

def estimate_covariance(
    prices: pd.DataFrame,
    method: str = "sample",
    annualize: bool = True,
) -> np.ndarray:
    """
    Estimate covariance matrix from historical price data.

    Parameters
    ----------
    prices  : DataFrame with tickers as columns, dates as index
    method  : "sample" | "ledoit_wolf" (shrinkage)
    annualize: If True, multiply by 252

    Returns
    -------
    np.ndarray of shape (N, N)
    """
    returns = prices.pct_change().dropna()
    if method == "ledoit_wolf":
        from sklearn.covariance import LedoitWolf
        lw = LedoitWolf()
        lw.fit(returns)
        cov = lw.covariance_
    else:
        cov = returns.cov().values

    if annualize:
        cov = cov * 252
    return cov


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import random
    np.random.seed(42)

    tickers = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "META", "GOOGL", "JPM", "JNJ", "XOM"]
    N = len(tickers)

    # Simulated equal start weights
    prev_weights = {t: 1/N for t in tickers}

    # Simulated actionability signals
    actionabilities = {
        "NVDA": +0.81, "AAPL": +0.22, "MSFT": +0.48, "TSLA": -0.67,
        "AMZN": +0.35, "META": +0.55, "GOOGL": +0.40, "JPM": -0.20,
        "JNJ":  +0.10, "XOM":  -0.15,
    }

    # Simulated covariance (random positive-definite)
    A = np.random.randn(N, N) * 0.01
    cov_matrix = A @ A.T + np.eye(N) * 0.001

    result = optimize(tickers, actionabilities, prev_weights, cov_matrix)

    print(f"\nOptimizer status: {result.status}")
    print(f"Turnover: {result.turnover:.2%}")
    print(f"Portfolio variance: {result.portfolio_variance:.6f}")
    print(f"\n{'Ticker':<6}  {'From':>7}  {'To':>7}  {'Delta':>8}  Dir")
    print("-" * 40)
    for _, row in result.trades.iterrows():
        print(f"{row['ticker']:<6}  {row['from_weight']:>7.2%}  {row['to_weight']:>7.2%}  {row['delta']:>+8.2%}  {row['direction']}")
