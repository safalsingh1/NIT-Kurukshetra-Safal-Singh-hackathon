"""
src/risk/evidence.py
====================
Multi-Source Evidence & Corroboration Scorer — Availability-Aware.

Core Concept:
  One random source + low social volume + no SEC confirmation
    -> Evidence Score = ~30/100  -> WATCH (no action)

  GDELT negative + Social negative + SEC confirmed
    -> Evidence Score = ~92/100  -> CONFIRMED (portfolio action permitted)

KEY DESIGN: Availability-Aware Renormalisation
  Not every event will have all three source types present.
  Example: An NVDA product launch may have News + Social but NO SEC filing.
  We must NOT penalise this as if SEC = 0.

  Instead:
    1. Identify which source types are AVAILABLE for this event
    2. Renormalise weights across only available sources
    3. Score = weighted average over available sources only

  So:
    News + Social (no SEC)  ->  weights renorm to 0.60/0.20/0.20
    News only               ->  weights renorm to 1.00
    All three               ->  full original weights applied

  Source diversity and agreement are always available (calculated from
  whatever sources exist) and keep their fixed 0.10 / 0.10 weight.

Canonical weights (before renorm):
  w_news      = 0.40  (GDELT coverage, highest weight after SEC)
  w_sec       = 0.30  (SEC EDGAR official disclosure - only when present)
  w_social    = 0.10  (social sentiment agreement)

  Fixed:
  w_diversity = 0.10  (number of distinct domains)
  w_agreement = 0.10  (directional agreement across sources)

Action Thresholds:
  < 40   -> WATCH     - Rumour / insufficient corroboration
  40-69  -> DEVELOPING - Monitor, no portfolio action
  70+    -> CONFIRMED  - Portfolio action permitted
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Base weights for each source TYPE (before availability renorm)
# ---------------------------------------------------------------------------
W_NEWS_BASE      = 0.40
W_SEC_BASE       = 0.30
W_SOCIAL_BASE    = 0.10

# Fixed weights (always present — derived from whatever sources exist)
W_DIVERSITY      = 0.10
W_AGREEMENT      = 0.10

# Total variable weight budget = 1 - W_DIVERSITY - W_AGREEMENT = 0.80
VARIABLE_BUDGET  = 1.0 - W_DIVERSITY - W_AGREEMENT

WATCH_THRESHOLD       = 40.0
DEVELOPING_THRESHOLD  = 70.0
MAX_SOURCES_FOR_DIVERSITY = 20


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EvidenceInput:
    ticker: str

    # News (GDELT)
    news_count: int = 0
    news_sources: int = 0                  # distinct domain count
    news_sentiment: Optional[float] = None # mean sentiment

    # SEC
    sec_confirmed: bool = False

    # Social
    social_count: int = 0
    social_sentiment: Optional[float] = None

    # Manual override (for testing / historical events)
    manual_evidence_override: Optional[float] = None


@dataclass
class EvidenceResult:
    ticker: str
    evidence_score: float          # [0, 100]
    status: str                    # WATCH | DEVELOPING | CONFIRMED
    status_emoji: str
    allow_action: bool
    components: dict               # for explainability
    available_sources: list[str]   # which source types contributed
    weight_breakdown: dict         # effective weights used


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_evidence(inp: EvidenceInput) -> EvidenceResult:
    """
    Compute availability-aware evidence score.

    Steps:
      1. Score each available source type to [0, 1]
      2. Identify which source types are present
      3. Renormalise variable weights over available sources only
      4. Compute diversity and agreement scores
      5. Final score = (variable_component + diversity + agreement) * 100
    """
    if inp.manual_evidence_override is not None:
        score = float(np.clip(inp.manual_evidence_override, 0, 100))
        return _build_result(inp.ticker, score, {}, [], {})

    # ── Score each source type ────────────────────────────────────────────

    # NEWS score: combination of coverage volume and source count
    news_score, news_present = _score_news(inp.news_count, inp.news_sources)

    # SEC score: binary (confirmed or not); only present if event is SEC-type
    sec_score, sec_present = _score_sec(inp.sec_confirmed)

    # SOCIAL score: volume + sentiment alignment
    social_score, social_present = _score_social(inp.social_count, inp.social_sentiment)

    # ── Availability-aware weight renormalisation ─────────────────────────
    available_types   = []
    available_bases   = []
    available_scores  = []

    if news_present:
        available_types.append("News")
        available_bases.append(W_NEWS_BASE)
        available_scores.append(news_score)
    if sec_present:
        available_types.append("SEC")
        available_bases.append(W_SEC_BASE)
        available_scores.append(sec_score)
    if social_present:
        available_types.append("Social")
        available_bases.append(W_SOCIAL_BASE)
        available_scores.append(social_score)

    if not available_types:
        # No sources at all — minimum score
        return _build_result(inp.ticker, 5.0, {}, [], {})

    # Renormalise base weights so they sum to VARIABLE_BUDGET (0.80)
    base_sum = sum(available_bases)
    renorm_weights = [b / base_sum * VARIABLE_BUDGET for b in available_bases]

    # Variable component
    variable_score = sum(w * s for w, s in zip(renorm_weights, available_scores))

    # ── Diversity score ───────────────────────────────────────────────────
    total_sources  = inp.news_sources + (1 if inp.sec_confirmed else 0) + (1 if inp.social_count > 0 else 0)
    diversity_score = float(min(total_sources / MAX_SOURCES_FOR_DIVERSITY, 1.0))

    # ── Agreement score ───────────────────────────────────────────────────
    agreement_score = _score_agreement(inp.news_sentiment, inp.social_sentiment)

    # ── Final score ───────────────────────────────────────────────────────
    final_raw = variable_score + W_DIVERSITY * diversity_score + W_AGREEMENT * agreement_score
    final_score = float(np.clip(final_raw * 100.0, 0.0, 100.0))

    components = {
        "variable_component": round(variable_score, 4),
        "diversity_score":    round(diversity_score, 4),
        "agreement_score":    round(agreement_score, 4),
    }
    for name, score in zip(available_types, available_scores):
        components[f"{name.lower()}_score"] = round(score, 4)

    weight_breakdown = {
        name: round(w, 4)
        for name, w in zip(available_types, renorm_weights)
    }
    weight_breakdown["diversity"] = W_DIVERSITY
    weight_breakdown["agreement"] = W_AGREEMENT

    return _build_result(inp.ticker, final_score, components, available_types, weight_breakdown)


def quick_evidence(
    ticker: str,
    news_count: int = 0,
    news_sources: int = 0,
    sec_confirmed: bool = False,
    social_count: int = 0,
    news_sentiment: Optional[float] = None,
    social_sentiment: Optional[float] = None,
) -> EvidenceResult:
    """Convenience wrapper for quick evidence computation."""
    return compute_evidence(EvidenceInput(
        ticker=ticker,
        news_count=news_count,
        news_sources=news_sources,
        news_sentiment=news_sentiment,
        sec_confirmed=sec_confirmed,
        social_count=social_count,
        social_sentiment=social_sentiment,
    ))


# ---------------------------------------------------------------------------
# Source scorers
# ---------------------------------------------------------------------------

def _score_news(count: int, sources: int) -> tuple[float, bool]:
    """
    Score news coverage [0, 1].
    Present if count >= 1.
    """
    if count < 1:
        return 0.0, False

    # Volume: saturates at 100 articles
    vol_score = float(min(count / 100.0, 1.0))
    # Source diversity component (within news): saturates at 15 domains
    src_score = float(min(sources / 15.0, 1.0))
    score = 0.6 * vol_score + 0.4 * src_score
    return float(np.clip(score, 0, 1)), True


def _score_sec(confirmed: bool) -> tuple[float, bool]:
    """
    SEC score: 1.0 if confirmed filing exists, else NOT present.
    We treat absent SEC as 'not available' rather than 'evidence = 0'.
    """
    if confirmed:
        return 1.0, True
    return 0.0, False   # Not present — excluded from renorm


def _score_social(count: int, sentiment: Optional[float]) -> tuple[float, bool]:
    """
    Score social coverage [0, 1].
    Present if count >= 5.
    """
    if count < 5:
        return 0.0, False

    vol_score = float(min(count / 500.0, 1.0))
    # Sentiment boost: high |sentiment| + high volume = stronger signal
    if sentiment is not None:
        sent_boost = float(abs(sentiment))
    else:
        sent_boost = 0.5
    score = 0.7 * vol_score + 0.3 * sent_boost
    return float(np.clip(score, 0, 1)), True


def _score_agreement(
    news_sentiment: Optional[float],
    social_sentiment: Optional[float],
) -> float:
    """
    Agreement score: do available sources agree on direction?
    1.0 = full directional agreement, 0.0 = contradiction.
    """
    sentiments = [s for s in [news_sentiment, social_sentiment] if s is not None]
    if len(sentiments) < 2:
        return 0.5   # only one source → neutral agreement

    signs = [np.sign(s) for s in sentiments if s != 0]
    if not signs:
        return 0.5
    n_pos = sum(1 for s in signs if s > 0)
    n_neg = sum(1 for s in signs if s < 0)
    total = n_pos + n_neg
    if total == 0:
        return 0.5
    majority = max(n_pos, n_neg)
    return float(majority / total)


def _build_result(
    ticker: str,
    score: float,
    components: dict,
    available_sources: list,
    weight_breakdown: dict,
) -> EvidenceResult:
    if score >= DEVELOPING_THRESHOLD:
        status, emoji, allow = "CONFIRMED", "\U0001f534", True
    elif score >= WATCH_THRESHOLD:
        status, emoji, allow = "DEVELOPING", "\U0001f7e1", False
    else:
        status, emoji, allow = "WATCH", "\u26aa", False

    return EvidenceResult(
        ticker=ticker,
        evidence_score=round(score, 1),
        status=status,
        status_emoji=emoji,
        allow_action=allow,
        components=components,
        available_sources=available_sources,
        weight_breakdown=weight_breakdown,
    )


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Evidence Score — Availability-Aware Demo")
    print("=" * 60)

    cases = [
        ("Rumour (News only, 1 source)",
         dict(ticker="NVDA", news_count=1, news_sources=1)),
        ("Developing (News+Social, no SEC)",
         dict(ticker="NVDA", news_count=40, news_sources=10,
              social_count=200, news_sentiment=-0.6, social_sentiment=-0.5)),
        ("Confirmed (All 3 sources)",
         dict(ticker="NVDA", news_count=85, news_sources=18,
              sec_confirmed=True, social_count=400,
              news_sentiment=0.82, social_sentiment=0.71)),
        ("Product launch (News+Social, SEC N/A — should NOT be penalised)",
         dict(ticker="AAPL", news_count=60, news_sources=12,
              social_count=300, news_sentiment=0.70, social_sentiment=0.65)),
    ]

    for label, kwargs in cases:
        r = quick_evidence(**kwargs)
        src_str = "+".join(r.available_sources) if r.available_sources else "none"
        print(f"\n{label}")
        print(f"  Sources:  {src_str}")
        print(f"  Weights:  {r.weight_breakdown}")
        print(f"  Score:    {r.evidence_score:.1f}/100  [{r.status}]  allow={r.allow_action}")
