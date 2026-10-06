"""
src/nlp/sentiment.py
====================
Financial Sentiment Scoring using FinBERT.

Model: ProsusAI/finbert  (fine-tuned on financial communications)
Output: sentiment_score ∈ [-1, +1]  and  confidence ∈ [0, 1]

Design decisions:
  - We return a continuous numeric score, NOT just "Positive/Negative".
    A score of +0.83 with confidence 0.94 is actionable downstream.
  - We batch inference for efficiency (configurable batch_size).
  - We cache the model load (loaded once per process).
  - If GPU is unavailable we fall back to CPU automatically.

Reference: Araci, 2019 — FinBERT: Financial Sentiment Analysis with BERT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

import torch
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

MODEL_NAME = "ProsusAI/finbert"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# FinBERT label ordering: positive=0, negative=1, neutral=2
_LABEL_SIGN = {0: 1.0, 1: -1.0, 2: 0.0}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SentimentResult:
    text: str
    label: str            # "positive" | "negative" | "neutral"
    sentiment_score: float  # [-1, +1]; positive = bullish
    confidence: float     # probability of the predicted label [0, 1]
    positive_prob: float
    negative_prob: float
    neutral_prob: float


# ---------------------------------------------------------------------------
# Model loading (cached)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_model():
    """Load FinBERT tokenizer and model (once per process)."""
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    logger.info("Loading FinBERT model from HuggingFace: %s", MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    model.to(DEVICE)
    model.eval()
    return tokenizer, model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_text(text: str) -> SentimentResult:
    """Score a single piece of text."""
    return score_batch([text])[0]


def score_batch(texts: Sequence[str], batch_size: int = 32) -> list[SentimentResult]:
    """
    Score a list of texts in batches.

    Parameters
    ----------
    texts      : List of article headlines or body text
    batch_size : Inference batch size

    Returns
    -------
    List of SentimentResult objects (same order as input)
    """
    tokenizer, model = _load_model()
    all_results: list[SentimentResult] = []

    for i in range(0, len(texts), batch_size):
        batch = list(texts[i : i + batch_size])
        inputs = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        ).to(DEVICE)

        with torch.no_grad():
            logits = model(**inputs).logits

        probs = torch.softmax(logits, dim=-1).cpu().numpy()  # (B, 3)

        for j, text in enumerate(batch):
            p = probs[j]
            pred_label_idx = int(np.argmax(p))
            labels = ["positive", "negative", "neutral"]
            label = labels[pred_label_idx]
            confidence = float(p[pred_label_idx])

            # Continuous score: weighted sum of positive and negative probs
            # Neutral has no directional contribution
            sentiment_score = float(p[0]) - float(p[1])   # positive - negative

            all_results.append(SentimentResult(
                text=text[:120],
                label=label,
                sentiment_score=round(sentiment_score, 4),
                confidence=round(confidence, 4),
                positive_prob=round(float(p[0]), 4),
                negative_prob=round(float(p[1]), 4),
                neutral_prob=round(float(p[2]), 4),
            ))

    return all_results


def score_dataframe(
    df: pd.DataFrame,
    text_col: str = "headline",
    prefix: str = "sent",
) -> pd.DataFrame:
    """
    Apply sentiment scoring to every row of a DataFrame.

    Adds columns:
      {prefix}_score      : float [-1, +1]
      {prefix}_confidence : float [0, 1]
      {prefix}_label      : str
    """
    texts = df[text_col].fillna("").tolist()
    results = score_batch(texts)
    df = df.copy()
    df[f"{prefix}_score"]      = [r.sentiment_score for r in results]
    df[f"{prefix}_confidence"] = [r.confidence for r in results]
    df[f"{prefix}_label"]      = [r.label for r in results]
    return df


# ---------------------------------------------------------------------------
# Aggregate sentiment across multiple articles about the same company/event
# ---------------------------------------------------------------------------

def aggregate_sentiment(results: list[SentimentResult]) -> dict:
    """
    Aggregate multiple sentiment scores (e.g. all articles about NVDA today).

    Returns:
      mean_score       : confidence-weighted mean sentiment
      std_score        : score standard deviation (disagreement measure)
      consensus_label  : dominant label
      article_count    : number of articles
    """
    if not results:
        return {"mean_score": 0.0, "std_score": 0.0, "consensus_label": "neutral", "article_count": 0}

    scores = np.array([r.sentiment_score for r in results])
    weights = np.array([r.confidence for r in results])
    mean_score = float(np.average(scores, weights=weights))
    std_score  = float(np.std(scores))

    # Plurality vote
    from collections import Counter
    label_counts = Counter(r.label for r in results)
    consensus_label = label_counts.most_common(1)[0][0]

    return {
        "mean_score":      round(mean_score, 4),
        "std_score":       round(std_score,  4),
        "consensus_label": consensus_label,
        "article_count":   len(results),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    samples = [
        "NVIDIA reports record quarterly revenue, beats analyst expectations by 25%.",
        "Tesla faces recall of 200,000 vehicles over brake software defect.",
        "Apple and Microsoft announce strategic cloud partnership.",
        "Boeing shares fall as FAA orders fresh safety audit.",
        "Federal Reserve signals interest rates to remain elevated.",
    ]
    results = score_batch(samples)
    for r in results:
        sign = "+" if r.sentiment_score >= 0 else ""
        print(f"[{r.label.upper():<8}] score={sign}{r.sentiment_score:+.3f}  conf={r.confidence:.3f}  | {r.text[:70]}")
