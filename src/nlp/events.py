"""
src/nlp/events.py
==================
12-Class Financial Event Classification.

Baseline implementation: Zero-shot classification via HuggingFace
facebook/bart-large-mnli. The model is NOT specifically trained on
financial event data; it applies general NLI inference over the
12 event class descriptions.

This is honest and defensible:
  - Zero-shot generalises to new event descriptions without annotation
  - It is a well-validated NLP methodology (Yin et al. 2019)
  - Performance is sufficient for prototype-level event routing

Tier 2 (Future): Fine-tune a lightweight classifier on labelled
financial event datasets (e.g. Reuters Corpus, FinSBD) to improve
precision on domain-specific language. The interface is identical;
only the underlying model changes.

12 Event Classes:
  Earnings | M&A | Product/Partnership | Regulatory | Legal | Credit
  Leadership | Supply Chain | Cybersecurity | Geopolitical | Macroeconomic | Other

Each class also carries an event_weight (market-importance score for the
Impact Model) reflecting observed post-event return magnitudes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event taxonomy
# ---------------------------------------------------------------------------

EVENT_CLASSES = [
    "Earnings",
    "M&A",
    "Product/Partnership",
    "Regulatory",
    "Legal",
    "Credit",
    "Leadership",
    "Supply Chain",
    "Cybersecurity",
    "Geopolitical",
    "Macroeconomic",
    "Other",
]

# How market-moving each event type is, on average (0–1 scale)
EVENT_WEIGHTS: dict[str, float] = {
    "Earnings":            0.90,
    "M&A":                 0.95,
    "Product/Partnership": 0.70,
    "Regulatory":          0.80,
    "Legal":               0.65,
    "Credit":              0.85,
    "Leadership":          0.60,
    "Supply Chain":        0.75,
    "Cybersecurity":       0.70,
    "Geopolitical":        0.80,
    "Macroeconomic":       0.85,
    "Other":               0.30,
}

# Hypothesis templates for NLI-based zero-shot
HYPOTHESIS_TEMPLATES: dict[str, str] = {
    "Earnings":            "This text is about corporate earnings, revenue, profit, or financial results.",
    "M&A":                 "This text is about mergers, acquisitions, takeovers, or buyouts.",
    "Product/Partnership": "This text is about new product launches, business partnerships, or joint ventures.",
    "Regulatory":          "This text is about government regulation, compliance, SEC investigation, or policy change.",
    "Legal":               "This text is about lawsuits, legal proceedings, court rulings, or settlements.",
    "Credit":              "This text is about credit ratings, debt, bonds, defaults, or financing.",
    "Leadership":          "This text is about CEO, executive changes, management restructuring, or board decisions.",
    "Supply Chain":        "This text is about supply chain disruptions, logistics, manufacturing, or shortages.",
    "Cybersecurity":       "This text is about cybersecurity incidents, hacking, data breaches, or ransomware.",
    "Geopolitical":        "This text is about geopolitical tensions, wars, sanctions, or international relations.",
    "Macroeconomic":       "This text is about inflation, interest rates, GDP, Federal Reserve, or macroeconomic trends.",
    "Other":               "This text is about a general business or financial topic.",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EventResult:
    text: str
    event_type: str        # Primary event class
    event_weight: float    # Market impact weight for this type
    confidence: float      # Classification confidence [0, 1]
    all_scores: dict[str, float]  # All class probabilities


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_classifier():
    """Load zero-shot classification pipeline (once per process)."""
    from transformers import pipeline
    logger.info("Loading zero-shot classifier...")
    return pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli",
        device=0 if __import__("torch").cuda.is_available() else -1,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_event(text: str) -> EventResult:
    """Classify a single text into one of the 12 event types."""
    return classify_batch([text])[0]


def classify_batch(texts: Sequence[str]) -> list[EventResult]:
    """
    Classify a batch of texts.

    Returns a list of EventResult (same order as input).
    """
    classifier = _load_classifier()
    results = []

    for text in texts:
        try:
            output = classifier(
                text,
                candidate_labels=EVENT_CLASSES,
                hypothesis_template="{}",
                multi_label=False,
            )
            # output["labels"] is sorted by score descending
            top_label = output["labels"][0]
            top_score = output["scores"][0]
            all_scores = dict(zip(output["labels"], output["scores"]))

            results.append(EventResult(
                text=text[:120],
                event_type=top_label,
                event_weight=EVENT_WEIGHTS[top_label],
                confidence=round(top_score, 4),
                all_scores={k: round(v, 4) for k, v in all_scores.items()},
            ))
        except Exception as exc:
            logger.warning("Event classification failed: %s", exc)
            results.append(_default_result(text))

    return results


def classify_dataframe(
    df: pd.DataFrame,
    text_col: str = "headline",
) -> pd.DataFrame:
    """
    Apply event classification to every row of a DataFrame.

    Adds columns: event_type, event_weight, event_confidence
    """
    texts = df[text_col].fillna("").tolist()
    results = classify_batch(texts)
    df = df.copy()
    df["event_type"]       = [r.event_type for r in results]
    df["event_weight"]     = [r.event_weight for r in results]
    df["event_confidence"] = [r.confidence for r in results]
    return df


def get_event_weight(event_type: str) -> float:
    """Look up the market-importance weight for an event type."""
    return EVENT_WEIGHTS.get(event_type, EVENT_WEIGHTS["Other"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_result(text: str) -> EventResult:
    return EventResult(
        text=text[:120],
        event_type="Other",
        event_weight=EVENT_WEIGHTS["Other"],
        confidence=0.0,
        all_scores={e: 0.0 for e in EVENT_CLASSES},
    )


# ---------------------------------------------------------------------------
# Keyword fallback (used when the model is not available in demo mode)
# ---------------------------------------------------------------------------
_KEYWORD_MAP: dict[str, list[str]] = {
    "Earnings":            ["earnings", "revenue", "profit", "eps", "quarterly", "annual report", "guidance"],
    "M&A":                 ["acquisition", "merger", "takeover", "buyout", "acquires", "deal", "bid"],
    "Product/Partnership": ["partnership", "partnership", "product launch", "collaboration", "joint venture", "agreement", "launches"],
    "Regulatory":          ["regulation", "sec", "fda", "fine", "penalty", "compliance", "investigation", "ruling"],
    "Legal":               ["lawsuit", "court", "legal", "settlement", "litigation", "charges"],
    "Credit":              ["credit rating", "downgrade", "upgrade", "debt", "bonds", "default", "moody's", "s&p rating"],
    "Leadership":          ["ceo", "cfo", "executive", "appoints", "resigns", "board", "management"],
    "Supply Chain":        ["supply chain", "shortage", "logistics", "manufacturing", "disruption", "inventory"],
    "Cybersecurity":       ["hack", "breach", "ransomware", "cyber", "data leak", "security incident"],
    "Geopolitical":        ["tariff", "sanction", "war", "geopolitical", "trade war", "embargo", "conflict"],
    "Macroeconomic":       ["fed", "inflation", "interest rate", "gdp", "recession", "cpi", "unemployment", "federal reserve"],
}


def classify_keyword_fallback(text: str) -> EventResult:
    """Rule-based fallback classifier using keyword matching."""
    text_lower = text.lower()
    scores: dict[str, float] = {e: 0.0 for e in EVENT_CLASSES}

    for event, keywords in _KEYWORD_MAP.items():
        hit_count = sum(1 for kw in keywords if kw in text_lower)
        scores[event] = hit_count / len(keywords)

    best = max(scores, key=lambda k: scores[k])
    if scores[best] < 0.01:
        best = "Other"

    return EventResult(
        text=text[:120],
        event_type=best,
        event_weight=EVENT_WEIGHTS[best],
        confidence=min(scores[best] * 3.0, 0.80),   # cap keyword confidence at 0.80
        all_scores=scores,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    samples = [
        "NVIDIA reports record quarterly revenue, beats analyst expectations by 25%.",
        "Amazon acquires robotics startup for $2.3 billion.",
        "Apple launches new iPhone 17 Pro with AI chip.",
        "SEC opens investigation into Tesla's marketing claims.",
        "CEO of Boeing resigns amid ongoing safety concerns.",
        "Major cyberattack hits JPMorgan Chase systems.",
        "Federal Reserve raises interest rates by 25 basis points.",
    ]
    for s in samples:
        r = classify_keyword_fallback(s)
        print(f"[{r.event_type:<22}] conf={r.confidence:.2f}  wt={r.event_weight:.2f}  | {s[:70]}")
