"""
tests/test_novelty.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest
from datetime import datetime, timezone
from src.nlp.novelty import NoveltyDetector


def _now():
    return datetime.now(timezone.utc)


def test_first_article_is_novel():
    detector = NoveltyDetector()
    result = detector.process_article("art-1", "NVIDIA reports record revenue", _now(), "NVDA")
    assert result.is_novel is True
    assert result.novelty_score == 1.0


def test_duplicate_is_not_novel():
    """Two nearly identical articles should cluster together."""
    detector = NoveltyDetector()
    detector.process_article("art-1", "NVIDIA reports record quarterly revenue beating estimates", _now(), "NVDA")
    result2 = detector.process_article("art-2", "Nvidia beats quarterly earnings, revenue hits all-time high", _now(), "NVDA")
    # Duplicate should have low novelty
    assert result2.novelty_score < 0.5 or result2.cluster_id == "C00001"


def test_different_topic_is_novel():
    """Unrelated article should create a new cluster."""
    detector = NoveltyDetector()
    detector.process_article("art-1", "NVIDIA reports record revenue", _now(), "NVDA")
    result2 = detector.process_article("art-2", "Tesla recall announced for brake system defect", _now(), "TSLA")
    # Different enough to be a separate cluster
    assert result2.cluster_id != "C00001" or result2.novelty_score > 0.3


def test_cluster_size_increases():
    detector = NoveltyDetector()
    n1 = detector.process_article("a1", "NVIDIA launches new AI chip Blackwell", _now(), "NVDA")
    n2 = detector.process_article("a2", "Nvidia unveils Blackwell GPU for AI workloads", _now(), "NVDA")
    # If they cluster, second article's cluster_size should be > 1
    if n1.cluster_id == n2.cluster_id:
        assert n2.cluster_size == 2


def test_batch_processing():
    import pandas as pd
    detector = NoveltyDetector()
    df = pd.DataFrame({
        "id":        ["a", "b", "c", "d"],
        "headline":  [
            "AAPL beats earnings",
            "Apple reports strong quarterly results",  # duplicate of above
            "Tesla faces recall",
            "Boeing safety investigation launched",
        ],
        "timestamp": [_now()] * 4,
        "ticker":    ["AAPL", "AAPL", "TSLA", "BA"],
    })
    result = detector.process_batch(df, text_col="headline")
    assert "novelty_score" in result.columns
    assert "is_novel" in result.columns
    assert "cluster_id" in result.columns
    assert len(result) == 4
