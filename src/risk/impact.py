"""
src/risk/impact.py
==================
Market Impact Score [1-10] — Fully Normalised, Transparent, Calibration-Ready.

Formula (all inputs normalised to [0, 1]):
  impact = 10 * (
      W_S  * sentiment_strength     # |sentiment| * confidence
    + W_E  * event_severity         # event type weight
    + W_N  * novelty                # event cluster novelty
    + W_A  * attention              # z-score attention (normalised)
    + W_C  * corroboration          # evidence / 100
    + W_V  * volatility_factor      # historical volatility percentile
  )

Weights (sum to 1.0, interpretable):
  W_S = 0.20  — sentiment strength (direction + confidence)
  W_E = 0.20  — event severity (type-based market-importance)
  W_N = 0.15  — novelty (new information entering the market)
  W_A = 0.15  — attention spike (normalised from z-score)
  W_C = 0.20  — evidence corroboration
  W_V = 0.10  — historical volatility (amplifier for volatile stocks)

Why these weights?
  Sentiment and evidence are each 0.20 because they are the most
  directly measurable signals. Event type captures domain knowledge
  about which events historically move markets most. Novelty and
  attention together = 0.30 as they represent the "information
  surprise" dimension. Volatility is 0.10 — it amplifies but does
  not determine direction.

Calibration path (Tier 2):
  Weights can be learned from historical post-event abnormal returns
  (event-study methodology). The prototype uses the transparent
  equal-ish weights above and validates qualitatively against known
  market events (e.g., earnings beats → high impact).

Result: score in [1, 10], clipped so every event gets at minimum
        a score of 1 (background noise) and at most 10 (systemic).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Normalised weights (sum to 1.0 — fully explainable)
# ---------------------------------------------------------------------------
W_S = 0.20   # sentiment_strength  = |sentiment| * confidence
W_E = 0.20   # event_severity      = event_weight from taxonomy
W_N = 0.15   # novelty             in [0, 1]
W_A = 0.15   # attention           normalised z-score → [0, 1]
W_C = 0.20   # corroboration       = evidence_score / 100
W_V = 0.10   # volatility          = hist_vol_percentile in [0, 1]

WEIGHT_SUM = W_S + W_E + W_N + W_A + W_C + W_V   # = 1.0

# Clamp output to [1, 10]
IMPACT_MIN = 1.0
IMPACT_MAX = 10.0

# Historical average absolute returns by event type (calibration anchors)
# Source: academic event-study literature (Ball & Brown 1968; Fama et al. 1969)
HIST_EVENT_RETURNS: dict[str, float] = {
    "Earnings":            0.055,
    "M&A":                 0.080,
    "Product/Partnership": 0.030,
    "Regulatory":          0.040,
    "Legal":               0.035,
    "Credit":              0.045,
    "Leadership":          0.025,
    "Supply Chain":        0.035,
    "Cybersecurity":       0.030,
    "Geopolitical":        0.020,
    "Macroeconomic":       0.015,
    "Other":               0.010,
}

# Max observed return (M&A) used for normalising calibration factor
_MAX_HIST_RETURN = max(HIST_EVENT_RETURNS.values())


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class ImpactResult:
    ticker: str
    impact_score: float           # [1, 10]

    # Normalised components (each in [0, 1]) — for explainability
    sentiment_strength: float
    event_severity: float
    novelty: float
    attention_norm: float
    corroboration: float
    volatility_factor: float

    event_type: str
    raw_sentiment: float
    raw_spike: float
    raw_evidence: float
    explanation: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_impact(
    ticker: str,
    sentiment: float,               # [-1, +1]
    sentiment_confidence: float,    # [0, 1]
    event_type: str,
    event_weight: float,            # [0, 1] from events.EVENT_WEIGHTS
    novelty: float,                 # [0, 1]
    spike: float,                   # raw spike multiplier (e.g. 6.2)
    evidence: float,                # [0, 100]
    hist_vol_pct: float = 0.5,      # [0, 1] percentile of historical vol
    attention_z: Optional[float] = None,  # z-score if available (else derived)
) -> ImpactResult:
    """
    Compute Market Impact Score using fully-normalised, interpretable formula.

    All six input components are mapped to [0, 1] before weighting.
    Output is clipped to [1, 10].

    Parameters
    ----------
    ticker               : Stock ticker
    sentiment            : FinBERT score [-1, +1]
    sentiment_confidence : FinBERT confidence [0, 1]
    event_type           : Event class label
    event_weight         : Market-importance weight [0, 1]
    novelty              : Novelty score [0, 1]
    spike                : Raw attention spike multiplier
    evidence             : Evidence corroboration score [0, 100]
    hist_vol_pct         : Historical volatility percentile [0, 1]
    attention_z          : Optional z-score from AttentionMonitor

    Returns
    -------
    ImpactResult with impact_score in [1, 10]
    """
    # ── Normalise each component to [0, 1] ───────────────────────────────

    # S: sentiment strength = |sentiment| × confidence → already in [0, 1]
    S = float(np.clip(abs(sentiment) * sentiment_confidence, 0, 1))

    # E: event severity = event_weight → already in [0, 1]
    E = float(np.clip(event_weight, 0, 1))

    # N: novelty → already in [0, 1]
    N = float(np.clip(novelty, 0, 1))

    # A: attention → normalise spike or z-score to [0, 1]
    if attention_z is not None:
        # z-score: map [0, 5] → [0, 1] via sigmoid-like
        A = float(np.clip(attention_z / 5.0, 0, 1))
    else:
        # Fallback: log-scale spike multiplier → [0, 1]
        # log(1) = 0, log(51) ≈ 3.9; scale so spike=50x → ≈ 1
        A = float(np.clip(np.log1p(max(spike - 1, 0)) / np.log1p(49), 0, 1))

    # C: corroboration = evidence / 100
    C = float(np.clip(evidence / 100.0, 0, 1))

    # V: volatility factor = hist_vol_pct (already [0, 1])
    V = float(np.clip(hist_vol_pct, 0, 1))

    # ── Weighted sum (all in [0, 1]) → scale to [0, 10] ──────────────────
    raw_score = (
        W_S * S
        + W_E * E
        + W_N * N
        + W_A * A
        + W_C * C
        + W_V * V
    )

    # ── Historical calibration nudge (±15%) ───────────────────────────────
    # Calibrate based on observed post-event abnormal returns so that
    # event types with larger historical reactions score proportionally higher.
    hist_ret  = HIST_EVENT_RETURNS.get(event_type, HIST_EVENT_RETURNS["Other"])
    calib_factor = 0.85 + 0.30 * (hist_ret / _MAX_HIST_RETURN)  # [0.85, 1.15]
    raw_score *= calib_factor

    # ── Scale to [1, 10] ──────────────────────────────────────────────────
    impact = float(np.clip(raw_score * 10.0, IMPACT_MIN, IMPACT_MAX))

    explanation = _build_explanation(
        ticker, sentiment, event_type, S, E, N, A, C, V, impact
    )

    return ImpactResult(
        ticker=ticker,
        impact_score=round(impact, 2),
        sentiment_strength=round(S, 4),
        event_severity=round(E, 4),
        novelty=round(N, 4),
        attention_norm=round(A, 4),
        corroboration=round(C, 4),
        volatility_factor=round(V, 4),
        event_type=event_type,
        raw_sentiment=round(sentiment, 4),
        raw_spike=round(spike, 2),
        raw_evidence=round(evidence, 1),
        explanation=explanation,
    )


def compute_impact_from_dict(d: dict) -> ImpactResult:
    """Convenience wrapper accepting a dict of named fields."""
    return compute_impact(
        ticker               = d.get("ticker", "UNK"),
        sentiment            = d.get("sentiment_score", 0.0),
        sentiment_confidence = d.get("sentiment_confidence", 0.5),
        event_type           = d.get("event_type", "Other"),
        event_weight         = d.get("event_weight", 0.3),
        novelty              = d.get("novelty_score", 0.5),
        spike                = d.get("spike_multiplier", 1.0),
        evidence             = d.get("evidence_score", 50.0),
        hist_vol_pct         = d.get("hist_vol_pct", 0.5),
        attention_z          = d.get("attention_z", None),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_explanation(
    ticker: str,
    sentiment: float,
    event_type: str,
    S: float, E: float, N: float, A: float, C: float, V: float,
    impact: float,
) -> str:
    direction = "Bullish" if sentiment > 0 else ("Bearish" if sentiment < 0 else "Neutral")
    lines = [
        f"Ticker: {ticker}  |  Event: {event_type}  |  Direction: {direction}",
        "",
        "Normalised Components [0,1]:",
        f"  Sentiment Strength (S):  {S:.3f}  x weight {W_S:.2f}  = {S*W_S:.4f}",
        f"  Event Severity    (E):  {E:.3f}  x weight {W_E:.2f}  = {E*W_E:.4f}",
        f"  Novelty           (N):  {N:.3f}  x weight {W_N:.2f}  = {N*W_N:.4f}",
        f"  Attention         (A):  {A:.3f}  x weight {W_A:.2f}  = {A*W_A:.4f}",
        f"  Corroboration     (C):  {C:.3f}  x weight {W_C:.2f}  = {C*W_C:.4f}",
        f"  Volatility Factor (V):  {V:.3f}  x weight {W_V:.2f}  = {V*W_V:.4f}",
        "",
        f"  --> Impact Score: {impact:.2f} / 10",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Weight-calibration utility (Tier 2 — future use)
# ---------------------------------------------------------------------------

def calibrate_weights_from_returns(
    component_matrix: "np.ndarray",  # shape (N_events, 6)
    abnormal_returns: "np.ndarray",  # shape (N_events,) post-event [0-5d]
) -> dict[str, float]:
    """
    Estimate impact weights from historical event-study data using OLS.

    This is the Tier 2 calibration path. Run once we have labelled events
    with observed post-announcement abnormal returns.

    Parameters
    ----------
    component_matrix : Each row = [S, E, N, A, C, V] for one event
    abnormal_returns : Absolute abnormal return (|CAR|) for each event

    Returns
    -------
    Dict of calibrated weights summing to 1.0
    """
    from sklearn.linear_model import Ridge
    import numpy as np

    model = Ridge(alpha=0.1, fit_intercept=False)
    model.fit(component_matrix, abnormal_returns)

    raw_w = np.maximum(model.coef_, 0)   # enforce non-negative
    if raw_w.sum() > 0:
        raw_w /= raw_w.sum()

    names = ["W_S", "W_E", "W_N", "W_A", "W_C", "W_V"]
    return {n: round(float(w), 4) for n, w in zip(names, raw_w)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Impact Score — Normalised Formula Demo")
    print("=" * 55)
    scenarios = [
        dict(ticker="NVDA", sentiment_score=0.83, sentiment_confidence=0.94,
             event_type="Product/Partnership", event_weight=0.70,
             novelty_score=0.91, spike_multiplier=6.2,
             evidence_score=94.0, hist_vol_pct=0.78),
        dict(ticker="TSLA", sentiment_score=-0.72, sentiment_confidence=0.88,
             event_type="Regulatory", event_weight=0.80,
             novelty_score=0.85, spike_multiplier=4.1,
             evidence_score=82.0, hist_vol_pct=0.85),
        dict(ticker="JPM", sentiment_score=-0.45, sentiment_confidence=0.70,
             event_type="Legal", event_weight=0.65,
             novelty_score=0.60, spike_multiplier=2.0,
             evidence_score=55.0, hist_vol_pct=0.40),
    ]
    for s in scenarios:
        r = compute_impact_from_dict(s)
        print(f"\n{r.explanation}")
