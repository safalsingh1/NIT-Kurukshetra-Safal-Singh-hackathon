"""
src/risk/attention.py
=====================
News Attention Spike Detector — Statistically-Grounded Baseline.

Core Concept:
  Beyond sentiment, the volume of coverage signals market attention.
  A stock normally mentioned 12 times/hour suddenly appearing 84 times/hour
  indicates something significant is happening.

UPGRADED BASELINE (fixes weekend/intraday distortion):
  Old approach: rolling 30-day hourly mean (distorted by weekends + intraday patterns)

  New approach: expected volume = median count for the same
      (hour-of-day, day-of-week) bucket over the historical window.
  This removes systematic intraday and weekly seasonality.

  Then compute a z-score:
      z = (actual - expected) / std_of_same_bucket

  This is statistically meaningful and interpretable:
      z = 3 means "3 standard deviations above normal for this time slot"

  For display, we still report a human-readable spike multiplier:
      spike_multiplier = actual / max(expected, MIN_BASELINE)

  Both are reported; the impact formula uses attention_norm derived from z-score.

  Note: GDELT's DOC API exposes 15-min coverage timelines and
  normalized volume concepts that align with this approach.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WINDOW_HOURS     = 1          # Current observation window
BASELINE_DAYS    = 30         # Historical window for baseline
MIN_BASELINE     = 2.0        # Minimum expected count (avoids divide-by-zero)
MIN_STD          = 1.0        # Minimum std dev (avoids near-zero std)
SPIKE_CAP        = 50.0       # Cap raw spike multiplier at 50x
Z_DISPLAY_CAP    = 10.0       # Cap z-score for normalisation display


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AttentionResult:
    ticker: str
    current_count: int           # articles in current window
    expected_count: float        # seasonality-adjusted expected count
    spike_multiplier: float      # current / expected  (for display)
    z_score: float               # (actual - expected) / std  (for stats)
    attention_norm: float        # z-score normalised to [0, 1]
    attention_score: float       # alias for attention_norm (backward compat)
    alert: str                   # NORMAL | ELEVATED | SPIKE | EXTREME
    bucket_label: str            # e.g. "Tue 14:00" — the time bucket used


# ---------------------------------------------------------------------------
# AttentionMonitor class
# ---------------------------------------------------------------------------

class AttentionMonitor:
    """
    Maintains a rolling history of per-ticker article counts bucketed
    by (hour-of-day, day-of-week) to remove seasonal distortions.

    Usage:
        monitor = AttentionMonitor()
        monitor.ingest(df)                         # feed historical + live articles
        result = monitor.compute_attention("NVDA") # get spike for current window
    """

    def __init__(
        self,
        window_hours: int  = WINDOW_HOURS,
        baseline_days: int = BASELINE_DAYS,
    ):
        self.window_hours  = window_hours
        self.baseline_days = baseline_days
        # _history[ticker][(hour_of_day, day_of_week)] = [count, count, ...]
        self._history: dict[str, dict[tuple[int, int], list[int]]] = {}
        # Raw timestamped records for current-window counting
        self._raw: dict[str, list[datetime]] = {}

    def ingest(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        ticker_col: str = "ticker",
    ) -> None:
        """
        Feed a DataFrame of articles into the monitor.
        Must be called before compute_attention.
        Handles both historical baseline building and live ingestion.
        """
        df = df.copy()
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")
        df = df.dropna(subset=[timestamp_col, ticker_col])
        df = df[df[ticker_col].astype(str) != ""]

        # Floor to hour for bucketing
        df["_hour_ts"]   = df[timestamp_col].dt.floor("h")
        df["_hour_of_day"] = df["_hour_ts"].dt.hour
        df["_day_of_week"] = df["_hour_ts"].dt.dayofweek   # 0=Mon, 6=Sun

        counts_df = df.groupby([ticker_col, "_hour_ts", "_hour_of_day", "_day_of_week"]).size().reset_index(name="_cnt")

        for _, row in counts_df.iterrows():
            ticker  = str(row[ticker_col])
            bucket  = (int(row["_hour_of_day"]), int(row["_day_of_week"]))
            cnt     = int(row["_cnt"])
            ts      = row["_hour_ts"].to_pydatetime()

            if ticker not in self._history:
                self._history[ticker] = {}
                self._raw[ticker] = []

            if bucket not in self._history[ticker]:
                self._history[ticker][bucket] = []
            self._history[ticker][bucket].append(cnt)
            self._raw[ticker].append(ts)

    def ingest_article(
        self,
        ticker: str,
        timestamp: datetime,
    ) -> None:
        """Ingest a single article (for live/streaming mode)."""
        ts = _ensure_tz(timestamp).replace(minute=0, second=0, microsecond=0)
        bucket = (ts.hour, ts.weekday())

        if ticker not in self._history:
            self._history[ticker] = {}
            self._raw[ticker] = []

        if bucket not in self._history[ticker]:
            self._history[ticker][bucket] = []
        self._history[ticker][bucket].append(1)
        self._raw[ticker].append(ts)

    def compute_attention(
        self,
        ticker: str,
        at_time: Optional[datetime] = None,
    ) -> AttentionResult:
        """
        Compute statistically-grounded attention spike for *ticker* at *at_time*.

        Uses (hour-of-day, day-of-week) baseline to remove seasonal effects.
        Reports both raw spike multiplier (display) and z-score (analytics).
        """
        if at_time is None:
            at_time = datetime.now(timezone.utc)
        at_time = _ensure_tz(at_time)

        bucket = (at_time.hour, at_time.weekday())
        bucket_label = f"{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][bucket[1]]} {bucket[0]:02d}:00"

        if ticker not in self._history:
            return _empty_result(ticker, bucket_label)

        # Current window count
        window_start = at_time - timedelta(hours=self.window_hours)
        current_count = sum(
            1 for ts in self._raw.get(ticker, [])
            if window_start <= _ensure_tz(ts) <= at_time
        )

        # Historical observations for the SAME (hour, dow) bucket
        bucket_history = self._history[ticker].get(bucket, [])
        # Also look at adjacent hours (+/-1) for more data if sparse
        if len(bucket_history) < 5:
            for h_offset in [-1, 1]:
                adj_bucket = ((bucket[0] + h_offset) % 24, bucket[1])
                bucket_history = bucket_history + self._history[ticker].get(adj_bucket, [])

        if not bucket_history:
            expected = MIN_BASELINE
            std_dev  = MIN_STD
        else:
            expected = max(float(np.median(bucket_history)), MIN_BASELINE)
            std_dev  = max(float(np.std(bucket_history)), MIN_STD)

        # Raw spike multiplier (for display)
        spike = float(min(current_count / expected, SPIKE_CAP))

        # Z-score (statistically meaningful)
        z_score = float((current_count - expected) / std_dev)
        z_score = float(np.clip(z_score, -3.0, Z_DISPLAY_CAP))

        # Normalise z-score to [0, 1] for use in impact formula
        # z=0 → 0.0, z=3 → 0.60, z=6 → 0.86, z=10 → 1.0
        attention_norm = float(np.clip(z_score / Z_DISPLAY_CAP, 0, 1))

        return AttentionResult(
            ticker=ticker,
            current_count=current_count,
            expected_count=round(expected, 1),
            spike_multiplier=round(spike, 2),
            z_score=round(z_score, 2),
            attention_norm=round(attention_norm, 4),
            attention_score=round(attention_norm, 4),
            alert=_classify_alert(spike),
            bucket_label=bucket_label,
        )

    def compute_all_tickers(self, at_time: Optional[datetime] = None) -> dict[str, AttentionResult]:
        """Compute attention for every tracked ticker."""
        return {t: self.compute_attention(t, at_time) for t in self._history}


# ---------------------------------------------------------------------------
# Stateless convenience function
# ---------------------------------------------------------------------------

def compute_spike_scores(df: pd.DataFrame, at_time: Optional[datetime] = None) -> pd.DataFrame:
    """
    Compute attention spike scores for every unique ticker in *df*.

    Parameters
    ----------
    df      : DataFrame with 'timestamp' and 'ticker' columns
    at_time : Reference time (default = max timestamp in df)

    Returns
    -------
    DataFrame: ticker, expected_count, spike_multiplier, z_score,
               attention_norm, alert
    """
    monitor = AttentionMonitor()
    monitor.ingest(df)

    if at_time is None:
        raw_max = df["timestamp"].max()
        at_time = raw_max.to_pydatetime() if hasattr(raw_max, "to_pydatetime") else raw_max

    tickers = df["ticker"].dropna().unique()
    rows = []
    for ticker in tickers:
        if str(ticker) == "":
            continue
        r = monitor.compute_attention(ticker, at_time)
        rows.append({
            "ticker":            r.ticker,
            "current_count":     r.current_count,
            "expected_count":    r.expected_count,
            "spike_multiplier":  r.spike_multiplier,
            "z_score":           r.z_score,
            "attention_norm":    r.attention_norm,
            "attention_alert":   r.alert,
            "bucket":            r.bucket_label,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _classify_alert(spike: float) -> str:
    if spike <= 1.5:
        return "NORMAL"
    elif spike <= 3.0:
        return "ELEVATED"
    elif spike <= 7.0:
        return "SPIKE"
    else:
        return "EXTREME"


def _empty_result(ticker: str, bucket_label: str) -> AttentionResult:
    return AttentionResult(
        ticker=ticker, current_count=0,
        expected_count=MIN_BASELINE, spike_multiplier=0.0,
        z_score=0.0, attention_norm=0.0, attention_score=0.0,
        alert="NORMAL", bucket_label=bucket_label,
    )


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import random
    NOW = datetime.now(timezone.utc)

    rows = []
    # 30 days of baseline: simulate Mon-Fri 9-17 business hours (12/hr avg)
    for d in range(30):
        base_ts = NOW - timedelta(days=d + 1)
        for h in range(9, 18):
            ts = base_ts.replace(hour=h, minute=0)
            for _ in range(random.randint(8, 16)):
                rows.append({"timestamp": ts + timedelta(minutes=random.randint(0, 59)),
                             "ticker": "NVDA"})

    # Simulate current-hour spike: 84 articles (same hour-of-day)
    spike_hour = NOW.replace(minute=0, second=0, microsecond=0)
    for i in range(84):
        rows.append({"timestamp": spike_hour + timedelta(minutes=random.randint(0, 59)),
                     "ticker": "NVDA"})

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    monitor = AttentionMonitor()
    monitor.ingest(df)
    result = monitor.compute_attention("NVDA", NOW)

    print(f"Ticker:           {result.ticker}")
    print(f"Current count:    {result.current_count} articles/hr")
    print(f"Expected ({result.bucket_label}): {result.expected_count:.1f} articles/hr")
    print(f"Spike multiplier: {result.spike_multiplier:.1f}x")
    print(f"Z-score:          {result.z_score:.2f} (std devs above normal)")
    print(f"Attention norm:   {result.attention_norm:.4f}  [0,1]")
    print(f"Alert level:      {result.alert}")
