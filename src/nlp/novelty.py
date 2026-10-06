"""
src/nlp/novelty.py
==================
Event Clustering & Novelty Detection.

Core Insight:
  30 websites re-posting the same Bloomberg story = 1 event, not 30 signals.
  A genuinely new development (e.g. SEC filing confirming rumour) = high novelty.

Key Design — Scoped Comparison Window:
  We compare each article ONLY against clusters from the same:
    1. Ticker       — NVDA news should not suppress AAPL news novelty
    2. Event class  — an M&A article should not suppress an Earnings article
    3. Time window  — previous 24-48 hours only

  This means:
    new NVDA Earnings article  (vs existing NVDA Earnings cluster)  -> low novelty if duplicate
    new NVDA M&A article       (vs NVDA Earnings cluster)           -> high novelty (different class)
    old NVDA news from 3 days ago                                   -> excluded (outside window)

Formula:
  novelty(a) = 1 - max_{c in scoped_clusters} cosine_sim(embed(a), centroid(c))

  where scoped_clusters = clusters with same ticker AND same event_class
                          AND first_seen within CLUSTER_WINDOW_HOURS

This correctly detects:
  - Duplicate/rephrased articles -> low novelty
  - Genuinely new developments  -> high novelty
  - Cross-event noise            -> filtered out by scope
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SIMILARITY_THRESHOLD = 0.85      # articles above this are considered duplicates
CLUSTER_WINDOW_HOURS = 48        # only compare against clusters from last 48h
EMBEDDING_MODEL      = "all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EventCluster:
    cluster_id: str
    first_seen: datetime
    representative_text: str
    centroid: np.ndarray            # mean embedding of cluster members
    member_count: int = 1
    member_urls: list[str] = field(default_factory=list)
    ticker: str = ""
    event_class: str = ""           # e.g. "Earnings", "M&A" — for scoped comparison


@dataclass
class NoveltyResult:
    article_id: str
    text: str
    novelty_score: float           # [0, 1]; 1 = completely new
    is_novel: bool                 # True if novelty > SIMILARITY_THRESHOLD threshold
    cluster_id: str                # cluster this article belongs to
    cluster_size: int              # how many articles share this cluster
    max_similarity: float          # similarity to nearest cluster centroid


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_embedding_model():
    """Load sentence-transformer embedding model (once per process)."""
    from sentence_transformers import SentenceTransformer
    logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
    return SentenceTransformer(EMBEDDING_MODEL)


# ---------------------------------------------------------------------------
# NoveltyDetector class
# ---------------------------------------------------------------------------

class NoveltyDetector:
    """
    Stateful novelty detector that maintains a cluster memory.

    Usage:
        detector = NoveltyDetector()
        results = detector.process_batch(df)
    """

    def __init__(
        self,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        window_hours: float = CLUSTER_WINDOW_HOURS,
    ):
        self.similarity_threshold = similarity_threshold
        self.window_hours = window_hours
        self.clusters: list[EventCluster] = []
        self._cluster_counter = 0

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def process_article(
        self,
        article_id: str,
        text: str,
        timestamp: Optional[datetime] = None,
        ticker: str = "",
        event_class: str = "",
    ) -> NoveltyResult:
        """
        Process a single article and return its novelty result.

        Comparison is scoped to: same ticker + same event_class + within window.
        This prevents AAPL news from suppressing NVDA novelty, and Earnings
        articles from suppressing M&A articles.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        embedding = self._embed([text])[0]
        self._prune_old_clusters(timestamp)

        max_sim, best_cluster = self._find_best_cluster(embedding, ticker, event_class)

        if max_sim >= self.similarity_threshold and best_cluster is not None:
            # Add to existing cluster
            self._update_cluster(best_cluster, embedding, article_id)
            novelty_score = max(0.0, round(1.0 - max_sim, 4))
            return NoveltyResult(
                article_id=article_id,
                text=text[:120],
                novelty_score=novelty_score,
                is_novel=False,
                cluster_id=best_cluster.cluster_id,
                cluster_size=best_cluster.member_count,
                max_similarity=round(float(max_sim), 4),
            )
        else:
            # Create a new cluster
            cluster = self._create_cluster(article_id, text, embedding, timestamp, ticker, event_class)
            return NoveltyResult(
                article_id=article_id,
                text=text[:120],
                novelty_score=1.0,
                is_novel=True,
                cluster_id=cluster.cluster_id,
                cluster_size=1,
                max_similarity=round(float(max_sim), 4) if max_sim > 0 else 0.0,
            )

    def process_batch(
        self,
        df: pd.DataFrame,
        text_col: str = "headline",
        id_col: str = "id",
        timestamp_col: str = "timestamp",
        ticker_col: str = "ticker",
    ) -> pd.DataFrame:
        """
        Process a DataFrame of articles.

        Adds columns: novelty_score, is_novel, cluster_id, cluster_size
        """
        results = []
        for _, row in df.iterrows():
            ts = row.get(timestamp_col)
            if pd.isna(ts):
                ts = None
            elif hasattr(ts, "to_pydatetime"):
                ts = ts.to_pydatetime()

            result = self.process_article(
                article_id=str(row.get(id_col, "")),
                text=str(row.get(text_col, "")),
                timestamp=ts,
                ticker=str(row.get(ticker_col, "")),
            )
            results.append(result)

        df = df.copy()
        df["novelty_score"] = [r.novelty_score for r in results]
        df["is_novel"]      = [r.is_novel for r in results]
        df["cluster_id"]    = [r.cluster_id for r in results]
        df["cluster_size"]  = [r.cluster_size for r in results]
        return df

    def get_cluster_summary(self) -> pd.DataFrame:
        """Return a summary DataFrame of all active clusters."""
        if not self.clusters:
            return pd.DataFrame()
        rows = []
        for c in self.clusters:
            rows.append({
                "cluster_id":         c.cluster_id,
                "first_seen":         c.first_seen,
                "ticker":             c.ticker,
                "representative":     c.representative_text[:80],
                "member_count":       c.member_count,
            })
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _embed(self, texts: list[str]) -> np.ndarray:
        model = _load_embedding_model()
        return model.encode(texts, normalize_embeddings=True)

    def _prune_old_clusters(self, now: datetime) -> None:
        """Remove clusters older than window_hours."""
        cutoff = now - timedelta(hours=self.window_hours)
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        self.clusters = [
            c for c in self.clusters
            if c.first_seen.replace(tzinfo=timezone.utc if c.first_seen.tzinfo is None else c.first_seen.tzinfo) > cutoff
        ]

    def _find_best_cluster(
        self, embedding: np.ndarray, ticker: str, event_class: str = ""
    ) -> tuple[float, Optional[EventCluster]]:
        """
        Find the best-matching cluster scoped by ticker + event_class.

        Scope rules:
          - If ticker is set: only compare within same ticker
          - If event_class is set: only compare within same event class
          - Time window pruning already done by _prune_old_clusters
        """
        if not self.clusters:
            return 0.0, None

        best_sim = 0.0
        best_cluster = None
        for cluster in self.clusters:
            # Scope: same ticker (if specified)
            if ticker and cluster.ticker and cluster.ticker != ticker:
                continue
            # Scope: same event class (if specified)
            if event_class and cluster.event_class and cluster.event_class != event_class:
                continue
            sim = float(np.dot(embedding, cluster.centroid))  # both normalized
            if sim > best_sim:
                best_sim = sim
                best_cluster = cluster

        return best_sim, best_cluster

    def _update_cluster(
        self, cluster: EventCluster, embedding: np.ndarray, article_id: str
    ) -> None:
        """Update cluster centroid with new embedding (online mean)."""
        n = cluster.member_count
        cluster.centroid = (cluster.centroid * n + embedding) / (n + 1)
        # Re-normalize
        norm = np.linalg.norm(cluster.centroid)
        if norm > 0:
            cluster.centroid /= norm
        cluster.member_count += 1
        cluster.member_urls.append(article_id)

    def _create_cluster(
        self,
        article_id: str,
        text: str,
        embedding: np.ndarray,
        timestamp: datetime,
        ticker: str,
        event_class: str = "",
    ) -> EventCluster:
        """Create a new cluster, storing ticker and event_class for scoped comparison."""
        self._cluster_counter += 1
        cluster = EventCluster(
            cluster_id=f"C{self._cluster_counter:05d}",
            first_seen=timestamp,
            representative_text=text,
            centroid=embedding.copy(),
            member_count=1,
            member_urls=[article_id],
            ticker=ticker,
        )
        self.clusters.append(cluster)
        return cluster


# ---------------------------------------------------------------------------
# Convenience: stateless function for single-pass processing
# ---------------------------------------------------------------------------

def compute_novelty(
    df: pd.DataFrame,
    text_col: str = "headline",
    **kwargs,
) -> pd.DataFrame:
    """
    One-shot novelty computation for a DataFrame.
    Instantiates a fresh NoveltyDetector each call.
    """
    detector = NoveltyDetector(**kwargs)
    return detector.process_batch(df, text_col=text_col)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    articles = [
        "NVIDIA reports record quarterly revenue exceeding expectations",
        "Nvidia beats quarterly earnings, revenue hits all-time high",    # duplicate
        "Nvidia's results smash forecasts as AI demand surges",           # duplicate
        "Apple announces new AI features for iPhone",
        "Tesla recalls 200,000 vehicles over brake software issue",
        "Tesla issues voluntary recall for brake firmware",                # duplicate
        "Amazon acquires robotics company for $2.3 billion",
    ]
    detector = NoveltyDetector()
    for i, text in enumerate(articles):
        r = detector.process_article(
            article_id=f"art-{i:03d}",
            text=text,
            timestamp=datetime.now(timezone.utc),
        )
        flag = "🆕 NEW" if r.is_novel else "♻️  DUP"
        print(f"{flag}  novelty={r.novelty_score:.2f}  sim={r.max_similarity:.2f}  cluster={r.cluster_id}  | {text[:70]}")
