"""
src/portfolio/rebalancer.py
============================
Constraint-Aware Portfolio Rebalancer.

Orchestrates the full rebalancing pipeline:
  1. Receive aggregated ticker signals (actionability scores)
  2. Determine which tickers trigger abstention (low evidence/confidence)
  3. Call the optimizer to get new weights
  4. Generate explainability cards for each portfolio change
  5. Return RebalanceEvent with before/after weights and explanations

This module is the bridge between the risk/signal layer and the optimizer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from src.portfolio.optimizer import optimize, OptimizationResult, estimate_covariance
from src.portfolio.constraints import PortfolioConstraints

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TradingDecision:
    """Explainability card for a single portfolio trade."""
    ticker: str
    company: str
    from_weight: float
    to_weight: float
    delta: float
    direction: str                # "Increase" | "Decrease" | "Hold"
    signal_direction: str         # "BUY" | "SELL" | "HOLD"
    actionability: float

    # Signal factors for explainability
    event_type: str
    sentiment: float
    impact_score: float
    novelty: float
    spike: float
    evidence_score: float
    confidence: float
    abstained: bool
    abstain_reason: str
    source_headlines: list[str] = field(default_factory=list)


@dataclass
class RebalanceEvent:
    """Result of a single rebalancing operation."""
    timestamp: datetime
    prev_weights: dict[str, float]
    new_weights: dict[str, float]
    turnover: float
    decisions: list[TradingDecision]
    optimizer_status: str
    portfolio_variance: float
    n_abstained: int
    n_acted: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class Rebalancer:
    """
    Orchestrates signal → constraint → optimize → explain pipeline.
    """

    def __init__(
        self,
        tickers: list[str],
        prices: Optional[pd.DataFrame] = None,
        constraints: Optional[PortfolioConstraints] = None,
        cov_method: str = "ledoit_wolf",
    ):
        """
        Parameters
        ----------
        tickers     : Universe of stocks
        prices      : Historical price DataFrame (tickers as columns)
                      If None, uses diagonal identity covariance
        constraints : PortfolioConstraints (defaults if None)
        cov_method  : "sample" | "ledoit_wolf"
        """
        self.tickers     = tickers
        self.constraints = constraints or PortfolioConstraints()
        N = len(tickers)

        if prices is not None and len(prices) > 5:
            # Align columns to universe
            price_cols = [t for t in tickers if t in prices.columns]
            self.cov_matrix = estimate_covariance(
                prices[price_cols], method=cov_method
            )
            if len(price_cols) < N:
                # Pad missing tickers with diagonal variance 0.04 (20% vol)
                full_cov = np.eye(N) * 0.04
                idx_map = {t: i for i, t in enumerate(price_cols)}
                for i, ti in enumerate(tickers):
                    for j, tj in enumerate(tickers):
                        if ti in idx_map and tj in idx_map:
                            full_cov[i, j] = self.cov_matrix[idx_map[ti], idx_map[tj]]
                self.cov_matrix = full_cov
        else:
            self.cov_matrix = np.eye(N) * 0.04   # default: 20% vol, uncorrelated

        # Track current weights
        self._current_weights: dict[str, float] = {t: 1.0 / N for t in tickers}

    def rebalance(
        self,
        signals: pd.DataFrame,
        ticker_metadata: Optional[dict] = None,
        timestamp: Optional[datetime] = None,
    ) -> RebalanceEvent:
        """
        Execute a rebalancing based on current signals.

        Parameters
        ----------
        signals         : DataFrame with columns: ticker, actionability,
                          signal_direction, sent_score, sent_confidence,
                          event_type, impact_score, novelty_score,
                          spike_multiplier, evidence_score, allow_action,
                          abstained, abstain_reason, headline (optional)
        ticker_metadata : {ticker: {company, sector, ...}}
        timestamp       : Rebalancing timestamp (default=now)

        Returns
        -------
        RebalanceEvent
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        if ticker_metadata is None:
            from src.nlp.entity import TICKER_DB
            ticker_metadata = TICKER_DB

        # ── Aggregate multiple signals per ticker ─────────────────────────
        agg = self._aggregate_signals(signals)

        actionabilities = dict(zip(agg["ticker"], agg["actionability"]))
        confidences     = dict(zip(agg["ticker"], agg.get("sent_confidence", {1.0})))

        # ── Run optimizer ─────────────────────────────────────────────────
        opt: OptimizationResult = optimize(
            tickers         = self.tickers,
            actionabilities = actionabilities,
            prev_weights    = self._current_weights,
            cov_matrix      = self.cov_matrix,
            confidences     = confidences,
            constraints     = self.constraints,
        )

        # ── Build explainability cards ────────────────────────────────────
        decisions = self._build_decisions(opt, agg, signals, ticker_metadata)

        n_abstained = sum(1 for d in decisions if d.abstained)
        n_acted     = sum(1 for d in decisions if abs(d.delta) > 0.001)

        # ── Update state ──────────────────────────────────────────────────
        self._current_weights = opt.new_weights

        return RebalanceEvent(
            timestamp         = timestamp,
            prev_weights      = opt.prev_weights,
            new_weights       = opt.new_weights,
            turnover          = opt.turnover,
            decisions         = decisions,
            optimizer_status  = opt.status,
            portfolio_variance= opt.portfolio_variance,
            n_abstained       = n_abstained,
            n_acted           = n_acted,
        )

    @property
    def current_weights(self) -> dict[str, float]:
        return dict(self._current_weights)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _aggregate_signals(self, signals: pd.DataFrame) -> pd.DataFrame:
        """Aggregate multiple signals per ticker using impact-weighted mean."""
        if signals.empty:
            return pd.DataFrame(columns=["ticker", "actionability", "sent_confidence"])

        grp = signals.groupby("ticker")
        rows = []
        for ticker, group in grp:
            weights = group.get("impact_score", pd.Series([1.0]*len(group))).values
            weights = np.maximum(weights, 1.0)

            def wavg(col):
                if col not in group.columns:
                    return 0.0
                return float(np.average(group[col].fillna(0).values, weights=weights))

            rows.append({
                "ticker":          ticker,
                "actionability":   float(np.clip(wavg("actionability"), -1, 1)),
                "sent_confidence": wavg("sent_confidence"),
                "impact_score":    wavg("impact_score"),
                "novelty_score":   wavg("novelty_score"),
                "spike_multiplier":wavg("spike_multiplier"),
                "evidence_score":  wavg("evidence_score"),
                "event_type":      group["event_type"].mode()[0] if "event_type" in group.columns else "Other",
                "abstained":       bool(group.get("abstained", pd.Series([False]*len(group))).all()),
                "abstain_reason":  group.get("abstain_reason", pd.Series([""]))[group.index[0]],
                "headlines":       list(group.get("headline", pd.Series([])).dropna().values[:3]),
            })
        return pd.DataFrame(rows)

    def _build_decisions(
        self,
        opt: OptimizationResult,
        agg: pd.DataFrame,
        raw_signals: pd.DataFrame,
        ticker_metadata: dict,
    ) -> list[TradingDecision]:
        decisions = []
        agg_idx = {row["ticker"]: row for _, row in agg.iterrows()}

        for _, trade_row in opt.trades.iterrows():
            ticker = trade_row["ticker"]
            sig    = agg_idx.get(ticker, {})
            meta   = ticker_metadata.get(ticker, {})
            delta  = trade_row["delta"]

            direction = "Increase" if delta > 0.001 else ("Decrease" if delta < -0.001 else "Hold")

            decisions.append(TradingDecision(
                ticker         = ticker,
                company        = meta.get("company", ticker),
                from_weight    = trade_row["from_weight"],
                to_weight      = trade_row["to_weight"],
                delta          = round(delta, 4),
                direction      = direction,
                signal_direction = (
                    sig.get("actionability", 0) > 0.05 and "BUY" or
                    sig.get("actionability", 0) < -0.05 and "SELL" or
                    "HOLD"
                ),
                actionability  = round(float(sig.get("actionability", 0)), 4),
                event_type     = str(sig.get("event_type", "Other")),
                sentiment      = round(float(sig.get("actionability", 0)), 3),
                impact_score   = round(float(sig.get("impact_score", 5)), 2),
                novelty        = round(float(sig.get("novelty_score", 0.5)), 3),
                spike          = round(float(sig.get("spike_multiplier", 1)), 2),
                evidence_score = round(float(sig.get("evidence_score", 50)), 1),
                confidence     = round(float(sig.get("sent_confidence", 0.5)), 3),
                abstained      = bool(sig.get("abstained", False)),
                abstain_reason = str(sig.get("abstain_reason", "")),
                source_headlines = list(sig.get("headlines", [])),
            ))
        return decisions


def format_decision_card(d: TradingDecision) -> str:
    """Format a TradingDecision as a human-readable explainability card."""
    lines = [
        f"━━━ {d.ticker} ({d.company}) ━━━",
        f"Action:        {d.direction} Weight",
        f"Portfolio:     {d.from_weight:.2%} → {d.to_weight:.2%}  (Δ {d.delta:+.2%})",
        "",
        "WHY DID THE SYSTEM ACT?",
        f"  Event type:      {d.event_type}",
        f"  Sentiment:       {d.sentiment:+.3f}",
        f"  Impact:          {d.impact_score:.1f}/10",
        f"  Novelty:         {d.novelty:.2f}",
        f"  Attention spike: {d.spike:.1f}×",
        f"  Evidence:        {d.evidence_score:.1f}/100",
        f"  Confidence:      {d.confidence:.2f}",
        f"  Actionability:   {d.actionability:+.4f}",
    ]
    if d.abstained:
        lines += ["", f"  ⚠️  ABSTAINED: {d.abstain_reason}"]
    if d.source_headlines:
        lines += ["", "  Source headlines:"]
        for h in d.source_headlines[:3]:
            lines.append(f"    • {h[:80]}")
    return "\n".join(lines)
