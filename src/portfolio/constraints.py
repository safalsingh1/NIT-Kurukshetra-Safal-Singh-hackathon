"""
src/portfolio/constraints.py
=============================
Portfolio Constraint Definitions.

Defines all hard and soft constraints used by the optimizer:

Hard constraints (feasibility):
  1. Weights sum to 1
  2. No short selling: 0 ≤ w_i ≤ MAX_WEIGHT
  3. Sector exposure ≤ SECTOR_CAP

Soft constraints (penalised in objective):
  4. Turnover ≤ MAX_TURNOVER  (L1 penalty)
  5. Risk (variance) ≤ risk budget (quadratic penalty)
  6. Confidence abstention: if confidence < threshold, lock weight
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Default constraint parameters
# ---------------------------------------------------------------------------
MAX_WEIGHT       = 0.15    # Maximum single stock weight (15%)
MIN_WEIGHT       = 0.00    # No short selling
MAX_TURNOVER     = 0.10    # Maximum total turnover per rebalance (10%)
MAX_SECTOR_WEIGHT= 0.30    # Maximum total weight in any single sector (30%)
LAMBDA_RISK      = 2.0     # Quadratic risk penalty coefficient
LAMBDA_TURNOVER  = 0.05    # L1 turnover penalty coefficient (5 bps slippage/friction)
MIN_CONFIDENCE   = 0.50    # Below this, weight is locked to previous


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PortfolioConstraints:
    """
    All constraint parameters for a single rebalancing call.
    """
    max_weight:        float = MAX_WEIGHT
    min_weight:        float = MIN_WEIGHT
    max_turnover:      float = MAX_TURNOVER
    max_sector_weight: float = MAX_SECTOR_WEIGHT
    lambda_risk:       float = LAMBDA_RISK
    lambda_turnover:   float = LAMBDA_TURNOVER
    min_confidence:    float = MIN_CONFIDENCE
    sector_caps:       dict[str, float] = field(default_factory=dict)
    locked_tickers:    list[str] = field(default_factory=list)
    max_active_bets:   Optional[int] = None   # max N stocks with weight != benchmark

    def get_sector_cap(self, sector: str) -> float:
        """Return sector-specific cap or default."""
        return self.sector_caps.get(sector, self.max_sector_weight)


@dataclass
class WeightBounds:
    """Per-ticker lower and upper bounds on weights."""
    ticker: str
    lb: float   # lower bound
    ub: float   # upper bound
    locked: bool = False   # if True, ub = lb = current_weight


# ---------------------------------------------------------------------------
# Constraint builder
# ---------------------------------------------------------------------------

def build_weight_bounds(
    tickers: list[str],
    prev_weights: dict[str, float],
    confidences: dict[str, float],
    constraints: PortfolioConstraints,
) -> list[WeightBounds]:
    """
    Build per-ticker weight bounds, incorporating:
    - Global min/max weight
    - Locked tickers (low confidence → lock to previous weight)

    Parameters
    ----------
    tickers       : List of tickers in the universe
    prev_weights  : Current portfolio weights {ticker: weight}
    confidences   : Signal confidence per ticker {ticker: confidence}
    constraints   : PortfolioConstraints object

    Returns
    -------
    List of WeightBounds (same order as tickers)
    """
    bounds = []
    for t in tickers:
        conf    = confidences.get(t, 1.0)
        prev_w  = prev_weights.get(t, 1.0 / len(tickers))
        locked  = (t in constraints.locked_tickers) or (conf < constraints.min_confidence)

        if locked:
            bounds.append(WeightBounds(ticker=t, lb=prev_w, ub=prev_w, locked=True))
        else:
            bounds.append(WeightBounds(
                ticker=t,
                lb=constraints.min_weight,
                ub=constraints.max_weight,
                locked=False,
            ))
    return bounds


def get_sector_groups(
    tickers: list[str],
    ticker_info: dict[str, dict],
) -> dict[str, list[int]]:
    """
    Return {sector: [index_in_tickers]} mapping for use in CVXPY constraints.
    """
    groups: dict[str, list[int]] = {}
    for i, t in enumerate(tickers):
        sector = ticker_info.get(t, {}).get("sector", "Unknown")
        groups.setdefault(sector, []).append(i)
    return groups


def validate_weights(
    weights: np.ndarray,
    tickers: list[str],
    bounds: list[WeightBounds],
    constraints: PortfolioConstraints,
    sector_groups: dict[str, list[int]],
    prev_weights: np.ndarray,
    tol: float = 1e-5,
) -> list[str]:
    """
    Validate that optimised weights satisfy all constraints.

    Returns a list of violation messages (empty if all OK).
    """
    violations = []

    # Sum to 1
    if abs(weights.sum() - 1.0) > tol:
        violations.append(f"Weights sum to {weights.sum():.6f} (expected 1.0)")

    # Individual bounds
    for i, (w, b) in enumerate(zip(weights, bounds)):
        if w < b.lb - tol:
            violations.append(f"{b.ticker}: weight {w:.4f} < lb {b.lb:.4f}")
        if w > b.ub + tol:
            violations.append(f"{b.ticker}: weight {w:.4f} > ub {b.ub:.4f}")

    # Sector caps
    for sector, indices in sector_groups.items():
        sector_w = weights[indices].sum()
        cap = constraints.get_sector_cap(sector)
        if sector_w > cap + tol:
            violations.append(f"Sector '{sector}': {sector_w:.4f} > cap {cap:.4f}")

    # Turnover
    turnover = float(np.abs(weights - prev_weights).sum())
    if turnover > constraints.max_turnover + tol:
        violations.append(f"Turnover {turnover:.4f} > max {constraints.max_turnover:.4f}")

    return violations
