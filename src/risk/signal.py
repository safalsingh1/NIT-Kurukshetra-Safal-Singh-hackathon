"""
src/risk/signal.py
==================
Actionability Score Fusion — the final signal consumed by the portfolio engine.

Formula:
  actionability = S_i * M_i * R_i

where:
  S_i = sign(sentiment)                    — direction: +1 bullish / -1 bearish
  M_i = magnitude of the signal [0, 1]     — weighted composite
  R_i = risk_adjustment in (0, 1]          — attenuates position for volatile stocks

Magnitude:
  M = w1 * sentiment_confidence * |sentiment|   (quality-adjusted direction)
    + w2 * (impact / 10)                         (overall event importance)
    + w3 * novelty                               (new information premium)
    + w4 * attention_norm                        (market attention)
    + w5 * (evidence / 100)                      (corroboration)

Weights (sum to 1.0):
  w1 = 0.25, w2 = 0.30, w3 = 0.20, w4 = 0.15, w5 = 0.10

Risk Adjustment:
  R = 1 / (1 + normalised_volatility)
  This ensures:
    - positive signal + high volatility -> still positive -> but smaller
    - negative signal + high volatility -> still negative -> but smaller
    - It NEVER reverses direction, only attenuates magnitude

  Compared to the previous formula (subtracting vol), this correctly
  preserves the signal direction while reducing position size.

Confidence-Aware Abstention:
  If evidence.allow_action is False OR evidence < ABSTAIN_THRESHOLD,
  actionability = 0.0 and portfolio weight is locked.

Sector Spillover:
  A fraction of actionability propagates to co-sector stocks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from src.nlp.entity import TICKER_DB

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Weights (sum to 1.0)
# ---------------------------------------------------------------------------
W1 = 0.25   # sentiment × confidence
W2 = 0.30   # impact / 10
W3 = 0.20   # novelty
W4 = 0.15   # attention (normalised)
W5 = 0.10   # evidence / 100

assert abs(W1 + W2 + W3 + W4 + W5 - 1.0) < 1e-9, "Magnitude weights must sum to 1.0"

ABSTAIN_EVIDENCE_THRESHOLD  = 40.0
ABSTAIN_CONFIDENCE_THRESHOLD = 0.50
SECTOR_SPILLOVER_FRACTION    = 0.25


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class SignalResult:
    ticker: str
    actionability: float          # [-1, +1]
    signal_direction: str         # "BUY" | "SELL" | "HOLD"
    abstained: bool
    abstain_reason: str

    # Decomposition for explainability
    direction_sign: float         # +1 or -1
    magnitude: float              # [0, 1] before risk adjustment
    risk_adjustment: float        # R in (0, 1]
    sentiment: float
    sentiment_confidence: float
    impact_score: float
    novelty: float
    attention_norm: float         # normalised attention [0, 1]
    evidence_score: float
    hist_vol_pct: float
    allow_action: bool
    spillover: dict[str, float]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_signal(
    ticker: str,
    sentiment: float,
    sentiment_confidence: float,
    impact_score: float,
    novelty: float,
    spike: float,
    evidence_score: float,
    allow_action: bool,
    hist_vol_pct: float = 0.5,
    attention_norm: Optional[float] = None,
    apply_spillover: bool = True,
) -> SignalResult:
    """
    Compute the final actionability signal for a single ticker/event.

    actionability = sign(sentiment) * magnitude * risk_adjustment

    Parameters
    ----------
    ticker               : Stock ticker
    sentiment            : FinBERT score [-1, +1]
    sentiment_confidence : FinBERT confidence [0, 1]
    impact_score         : Market impact [1, 10]
    novelty              : Novelty score [0, 1]
    spike                : Raw attention spike multiplier
    evidence_score       : Evidence score [0, 100]
    allow_action         : From EvidenceResult.allow_action
    hist_vol_pct         : Historical volatility percentile [0, 1]
    attention_norm       : Pre-normalised attention [0, 1]; if None, derived from spike
    apply_spillover      : Whether to propagate to sector peers

    Returns
    -------
    SignalResult
    """
    # ── Abstention check ──────────────────────────────────────────────────
    if not allow_action or evidence_score < ABSTAIN_EVIDENCE_THRESHOLD:
        return _abstain(
            ticker, sentiment, sentiment_confidence, impact_score,
            novelty, spike, evidence_score, allow_action, hist_vol_pct,
            reason=f"evidence={evidence_score:.0f}/100 < threshold={ABSTAIN_EVIDENCE_THRESHOLD:.0f}",
        )
    if sentiment_confidence < ABSTAIN_CONFIDENCE_THRESHOLD:
        return _abstain(
            ticker, sentiment, sentiment_confidence, impact_score,
            novelty, spike, evidence_score, allow_action, hist_vol_pct,
            reason=f"sentiment_confidence={sentiment_confidence:.2f} < {ABSTAIN_CONFIDENCE_THRESHOLD:.2f}",
        )

    # ── Direction: sign of sentiment ──────────────────────────────────────
    direction = np.sign(sentiment) if sentiment != 0 else 1.0

    # ── Attention normalisation ───────────────────────────────────────────
    if attention_norm is None:
        # Derive from raw spike: log-scale → [0, 1]
        attention_norm = float(np.clip(np.log1p(max(spike - 1, 0)) / np.log1p(49), 0, 1))

    # ── Magnitude M in [0, 1] ────────────────────────────────────────────
    M = (
        W1 * float(abs(sentiment)) * float(sentiment_confidence)
        + W2 * float(impact_score / 10.0)
        + W3 * float(np.clip(novelty, 0, 1))
        + W4 * float(np.clip(attention_norm, 0, 1))
        + W5 * float(np.clip(evidence_score / 100.0, 0, 1))
    )
    M = float(np.clip(M, 0, 1))

    # ── Risk Adjustment R in (0, 1] ───────────────────────────────────────
    # R = 1 / (1 + normalised_vol)
    # High volatility → R closer to 0.5, attenuating (not reversing) signal.
    R = float(1.0 / (1.0 + float(np.clip(hist_vol_pct, 0, 1))))

    # ── Actionability: direction × magnitude × risk_adjustment ───────────
    actionability = float(np.clip(direction * M * R, -1.0, 1.0))

    signal_direction = (
        "BUY"  if actionability > 0.05 else
        "SELL" if actionability < -0.05 else
        "HOLD"
    )

    # ── Sector spillover ──────────────────────────────────────────────────
    spillover: dict[str, float] = {}
    if apply_spillover and abs(actionability) > 0.1:
        sector = TICKER_DB.get(ticker, {}).get("sector", "")
        if sector:
            for t, info in TICKER_DB.items():
                if t != ticker and info.get("sector") == sector:
                    spillover[t] = round(actionability * SECTOR_SPILLOVER_FRACTION, 4)

    return SignalResult(
        ticker=ticker,
        actionability=round(actionability, 4),
        signal_direction=signal_direction,
        abstained=False,
        abstain_reason="",
        direction_sign=float(direction),
        magnitude=round(M, 4),
        risk_adjustment=round(R, 4),
        sentiment=round(sentiment, 4),
        sentiment_confidence=round(sentiment_confidence, 4),
        impact_score=round(impact_score, 2),
        novelty=round(novelty, 4),
        attention_norm=round(attention_norm, 4),
        evidence_score=round(evidence_score, 1),
        hist_vol_pct=round(hist_vol_pct, 4),
        allow_action=allow_action,
        spillover=spillover,
    )


def compute_signals_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply signal computation to every row of a pre-enriched DataFrame."""
    results = []
    for _, row in df.iterrows():
        r = compute_signal(
            ticker               = str(row.get("ticker", "UNK")),
            sentiment            = float(row.get("sent_score", 0.0)),
            sentiment_confidence = float(row.get("sent_confidence", 0.5)),
            impact_score         = float(row.get("impact_score", 5.0)),
            novelty              = float(row.get("novelty_score", 0.5)),
            spike                = float(row.get("spike_multiplier", 1.0)),
            evidence_score       = float(row.get("evidence_score", 50.0)),
            allow_action         = bool(row.get("allow_action", True)),
            hist_vol_pct         = float(row.get("hist_vol_pct", 0.5)),
            attention_norm       = row.get("attention_norm", None),
        )
        results.append(r)

    df = df.copy()
    df["actionability"]    = [r.actionability for r in results]
    df["signal_direction"] = [r.signal_direction for r in results]
    df["abstained"]        = [r.abstained for r in results]
    df["abstain_reason"]   = [r.abstain_reason for r in results]
    df["magnitude"]        = [r.magnitude for r in results]
    df["risk_adjustment"]  = [r.risk_adjustment for r in results]
    return df


def aggregate_ticker_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate multiple signals per ticker via impact-weighted mean."""
    if "ticker" not in df.columns or "actionability" not in df.columns:
        return df
    rows = []
    for ticker, group in df.groupby("ticker"):
        weights = np.maximum(group.get("impact_score", pd.Series([1.0]*len(group))).values, 1.0)
        agg_act = float(np.clip(np.average(group["actionability"].values, weights=weights), -1, 1))
        rows.append({
            "ticker":          ticker,
            "actionability":   round(agg_act, 4),
            "signal_direction":"BUY" if agg_act > 0.05 else ("SELL" if agg_act < -0.05 else "HOLD"),
            "signal_count":    len(group),
            "abstained_count": int(group.get("abstained", pd.Series([False]*len(group))).sum()),
        })
    return pd.DataFrame(rows).sort_values("actionability", ascending=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _abstain(
    ticker, sentiment, confidence, impact, novelty,
    spike, evidence, allow_action, hist_vol_pct, reason
) -> SignalResult:
    return SignalResult(
        ticker=ticker, actionability=0.0, signal_direction="HOLD",
        abstained=True, abstain_reason=reason,
        direction_sign=float(np.sign(sentiment)) if sentiment != 0 else 0.0,
        magnitude=0.0, risk_adjustment=1.0,
        sentiment=sentiment, sentiment_confidence=confidence,
        impact_score=impact, novelty=novelty, attention_norm=0.0,
        evidence_score=evidence, hist_vol_pct=hist_vol_pct,
        allow_action=allow_action, spillover={},
    )


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Actionability Signal Demo")
    print("  Formula: A = sign(sent) * M * R")
    print("  R = 1 / (1 + vol_pct)  [never reverses direction]")
    print()
    scenarios = [
        dict(ticker="NVDA", sentiment=0.83, sentiment_confidence=0.94,
             impact_score=8.4, novelty=0.91, spike=6.2,
             evidence_score=94.0, allow_action=True, hist_vol_pct=0.78),
        dict(ticker="NVDA_highvol", sentiment=0.83, sentiment_confidence=0.94,
             impact_score=8.4, novelty=0.91, spike=6.2,
             evidence_score=94.0, allow_action=True, hist_vol_pct=0.99),  # extreme vol
        dict(ticker="TSLA_rumour", sentiment=-0.82, sentiment_confidence=0.88,
             impact_score=8.0, novelty=0.75, spike=4.1,
             evidence_score=29.0, allow_action=False, hist_vol_pct=0.90),  # abstain
        dict(ticker="MSFT", sentiment=0.60, sentiment_confidence=0.82,
             impact_score=6.5, novelty=0.70, spike=3.0,
             evidence_score=78.0, allow_action=True, hist_vol_pct=0.50),
    ]
    print(f"{'Ticker':<15}  {'Action':>7}  {'Dir':<5}  {'Mag':>5}  {'R':>5}  {'Abstain'}")
    print("-" * 60)
    for s in scenarios:
        r = compute_signal(**s)
        print(f"{r.ticker:<15}  {r.actionability:>+7.4f}  {r.signal_direction:<5}  "
              f"{r.magnitude:>5.3f}  {r.risk_adjustment:>5.3f}  {r.abstained}")
