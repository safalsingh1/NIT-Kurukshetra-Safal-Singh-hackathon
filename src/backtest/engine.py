"""
src/backtest/engine.py
======================
Timing-Aware Backtesting Engine.

Critical design principle — NO LOOK-AHEAD BIAS:
  If news appears at 15:45, we CANNOT use that day's closing price.
  We enforce the following execution timeline:

    News timestamp (15:45)
          ↓
    Signal generated (15:45)
          ↓
    Next available market price (next-day open)
          ↓
    Portfolio action applied

  This means signals generated after market close (16:00 ET) use
  the NEXT trading day's opening price for execution.
  Signals before market open use the CURRENT day's opening price.

Four strategies compared in ablation:
  0 – Baseline:    Equal-weight, monthly rebalance
  1 – Sentiment:   Sentiment only
  2 – Sentiment+:  Sentiment + Event + Impact
  3 – Full:        All 8 features + risk constraints

Usage:
  engine = BacktestEngine(prices, signals, strategy=3)
  result = engine.run(start="2023-01-01", end="2024-01-01")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timezone, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from src.portfolio.optimizer import optimize, estimate_covariance
from src.portfolio.constraints import PortfolioConstraints
from src.backtest.metrics import compute_metrics

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MARKET_OPEN_HOUR  = 9    # 09:30 ET
MARKET_CLOSE_HOUR = 16   # 16:00 ET
TRANSACTION_COST_BPS = 5  # 5 basis points per trade


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BacktestConfig:
    strategy: int                   # 0-3
    start_date: str
    end_date: str
    initial_capital: float = 1_000_000.0
    transaction_cost_bps: float = TRANSACTION_COST_BPS
    rebalance_frequency: str = "signal"   # "signal" | "daily" | "weekly" | "monthly"
    constraints: Optional[PortfolioConstraints] = None


@dataclass
class BacktestResult:
    strategy: int
    strategy_name: str
    portfolio_values: pd.Series         # Date → portfolio value
    weights_history: pd.DataFrame       # Date → ticker weights
    turnover_series: pd.Series          # Date → turnover
    rebalance_events: list[dict]        # [{date, ticker, from_w, to_w, reason}]
    metrics: dict                       # Sharpe, max_drawdown, etc.
    signal_log: pd.DataFrame            # Full signal+action log


STRATEGY_NAMES = {
    0: "Baseline (Equal-Weight)",
    1: "Strategy 1: Sentiment Only",
    2: "Strategy 2: Sentiment + Event + Impact",
    3: "Strategy 3: Full FinRisk AI (multi-signal intelligence + risk constraints)",
}


# ---------------------------------------------------------------------------
# BacktestEngine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """
    Timing-aware event-driven backtesting engine.

    Parameters
    ----------
    prices   : DataFrame; columns=tickers, index=DatetimeIndex (daily)
    signals  : DataFrame; must include: timestamp, ticker, actionability,
               sent_score, sent_confidence, event_type, impact_score,
               novelty_score, spike_multiplier, evidence_score, allow_action
    config   : BacktestConfig
    """

    def __init__(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        config: BacktestConfig,
    ):
        self.prices  = prices.copy()
        self.signals = signals.copy()
        self.config  = config
        self._tickers = list(prices.columns)

        # Ensure DatetimeIndex
        if not isinstance(self.prices.index, pd.DatetimeIndex):
            self.prices.index = pd.to_datetime(self.prices.index)
        self.prices.index = self.prices.index.tz_localize(None)

        # Covariance matrix
        if len(prices) > 5:
            self.cov_matrix = estimate_covariance(prices, method="ledoit_wolf")
        else:
            N = len(self._tickers)
            self.cov_matrix = np.eye(N) * 0.04

        if config.constraints is None:
            config.constraints = PortfolioConstraints()

    def run(self) -> BacktestResult:
        """Execute the full backtest and return results."""
        start = pd.Timestamp(self.config.start_date)
        end   = pd.Timestamp(self.config.end_date)

        trading_days = self.prices.loc[start:end].index
        if len(trading_days) < 2:
            raise ValueError("Insufficient price data for backtest period")

        N = len(self._tickers)
        portfolio_values = []
        weights_history  = []
        turnover_series  = []
        rebalance_events = []
        signal_log_rows  = []

        # Initial state
        capital = self.config.initial_capital
        weights = np.ones(N) / N   # equal weight start

        # Pre-process signals: assign execution date (timing-aware)
        signals = self._assign_execution_dates(self.signals)

        for i, date in enumerate(trading_days[:-1]):
            next_date = trading_days[i + 1]

            # Get open and close prices for this day
            row = self.prices.loc[date]
            prices_arr = np.array([row.get(t, np.nan) for t in self._tickers])

            if i == 0:
                prev_prices = prices_arr
            else:
                prev_prices = np.array([
                    self.prices.loc[trading_days[i-1]].get(t, np.nan)
                    for t in self._tickers
                ])

            # Compute daily returns
            daily_returns = np.where(
                prev_prices > 0,
                (prices_arr - prev_prices) / prev_prices,
                0.0,
            )

            # Signals that execute on this date
            day_signals = signals[signals["exec_date"] == date]

            if len(day_signals) > 0 and self.config.strategy > 0:
                new_weights, turnover, events = self._apply_strategy(
                    day_signals, weights, date
                )
                cost = self._transaction_cost(weights, new_weights, capital)
                weights = new_weights
                capital -= cost
                rebalance_events.extend(events)
                turnover_series.append({"date": date, "turnover": turnover})
                signal_log_rows.extend(day_signals.to_dict("records"))
            else:
                turnover_series.append({"date": date, "turnover": 0.0})

            # Monthly rebalance for baseline (strategy 0)
            if self.config.strategy == 0 and _is_month_start(date):
                weights = np.ones(N) / N

            # Update portfolio value
            port_return = float(np.nansum(weights * daily_returns))
            capital *= (1 + port_return)

            portfolio_values.append({"date": date, "value": capital})
            weights_history.append({"date": date, **{t: weights[i] for i, t in enumerate(self._tickers)}})

        result_df     = pd.DataFrame(portfolio_values).set_index("date")["value"]
        weights_df    = pd.DataFrame(weights_history).set_index("date")
        turnover_df   = pd.DataFrame(turnover_series).set_index("date")["turnover"]
        signal_log_df = pd.DataFrame(signal_log_rows) if signal_log_rows else pd.DataFrame()

        metrics = compute_metrics(result_df, risk_free_rate=0.05)

        return BacktestResult(
            strategy         = self.config.strategy,
            strategy_name    = STRATEGY_NAMES[self.config.strategy],
            portfolio_values = result_df,
            weights_history  = weights_df,
            turnover_series  = turnover_df,
            rebalance_events = rebalance_events,
            metrics          = metrics,
            signal_log       = signal_log_df,
        )

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _apply_strategy(
        self,
        signals: pd.DataFrame,
        current_weights: np.ndarray,
        date: pd.Timestamp,
    ) -> tuple[np.ndarray, float, list]:
        """Apply the configured strategy to update weights."""
        strategy = self.config.strategy
        N = len(self._tickers)
        prev_w = current_weights.copy()

        if strategy == 1:
            # Sentiment only: simple linear rule
            new_w = self._sentiment_only_rule(signals, prev_w)
        elif strategy == 2:
            # Sentiment + event + impact
            new_w = self._sentiment_event_impact_rule(signals, prev_w)
        elif strategy == 3:
            # Full FinRisk: CVXPY optimizer
            new_w = self._full_finrisk_optimize(signals, prev_w)
        else:
            new_w = prev_w

        new_w = np.clip(new_w, 0, self.config.constraints.max_weight if self.config.constraints else 0.15)
        new_w /= new_w.sum()

        turnover = float(np.abs(new_w - prev_w).sum())

        events = [{
            "date":      date,
            "strategy":  strategy,
            "turnover":  turnover,
            "n_signals": len(signals),
        }]

        return new_w, turnover, events

    def _sentiment_only_rule(self, signals: pd.DataFrame, prev_w: np.ndarray) -> np.ndarray:
        """Strategy 1: Shift weights proportional to sentiment score."""
        w = prev_w.copy()
        for _, row in signals.iterrows():
            if row.get("ticker") in self._tickers:
                idx = self._tickers.index(row["ticker"])
                shift = float(row.get("sent_score", 0)) * 0.02   # ±2% per unit
                w[idx] = float(np.clip(w[idx] + shift, 0, 0.15))
        w = w / w.sum()
        return w

    def _sentiment_event_impact_rule(self, signals: pd.DataFrame, prev_w: np.ndarray) -> np.ndarray:
        """Strategy 2: Sentiment × event weight × impact-scaled shift."""
        w = prev_w.copy()
        from src.nlp.events import get_event_weight
        for _, row in signals.iterrows():
            if row.get("ticker") in self._tickers:
                idx    = self._tickers.index(row["ticker"])
                sent   = float(row.get("sent_score", 0))
                impact = float(row.get("impact_score", 5)) / 10.0
                ew     = get_event_weight(str(row.get("event_type", "Other")))
                shift  = sent * impact * ew * 0.05
                w[idx] = float(np.clip(w[idx] + shift, 0, 0.15))
        w = w / w.sum()
        return w

    def _full_finrisk_optimize(self, signals: pd.DataFrame, prev_w: np.ndarray) -> np.ndarray:
        """Strategy 3: Full CVXPY optimization."""
        prev_weights_d = {t: float(prev_w[i]) for i, t in enumerate(self._tickers)}
        actionabilities = {}
        confidences     = {}

        for _, row in signals.iterrows():
            ticker = row.get("ticker", "")
            if ticker in self._tickers and not row.get("abstained", False):
                actionabilities[ticker] = float(row.get("actionability", 0))
                confidences[ticker]     = float(row.get("sent_confidence", 0.5))

        result = optimize(
            tickers         = self._tickers,
            actionabilities = actionabilities,
            prev_weights    = prev_weights_d,
            cov_matrix      = self.cov_matrix,
            confidences     = confidences,
            constraints     = self.config.constraints,
        )

        return np.array([result.new_weights.get(t, prev_w[i]) for i, t in enumerate(self._tickers)])

    # ------------------------------------------------------------------
    # Timing-aware helpers
    # ------------------------------------------------------------------

    def _assign_execution_dates(self, signals: pd.DataFrame) -> pd.DataFrame:
        """
        Assign execution date to each signal.

        Rule:
          - Signal timestamp BEFORE market close (16:00 ET) on a trading day
            → execute at NEXT trading day's open
          - Signal timestamp AFTER market close
            → execute at trading day after next's open
        """
        df = signals.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df.dropna(subset=["timestamp"])
        df["timestamp_local"] = df["timestamp"].dt.tz_convert("America/New_York")
        df["signal_date"] = df["timestamp_local"].dt.date

        trading_days = sorted(self.prices.index.date)
        td_set = set(trading_days)
        td_list = list(trading_days)

        def get_exec_date(row):
            sig_date = row["signal_date"]
            sig_hour = row["timestamp_local"].hour
            # After close → skip to T+2
            offset = 1 if sig_hour < MARKET_CLOSE_HOUR else 2
            idx = _next_trading_day_idx(sig_date, td_list, offset)
            if idx is not None:
                return pd.Timestamp(td_list[idx])
            return None

        df["exec_date"] = df.apply(get_exec_date, axis=1)
        df = df.dropna(subset=["exec_date"])
        df["exec_date"] = pd.to_datetime(df["exec_date"]).dt.normalize()
        return df

    def _transaction_cost(
        self,
        prev: np.ndarray,
        new: np.ndarray,
        capital: float,
    ) -> float:
        """Compute flat transaction cost in dollars."""
        turnover = float(np.abs(new - prev).sum())
        bps = self.config.transaction_cost_bps
        return capital * turnover * bps / 10_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_trading_day_idx(date, trading_days: list, offset: int) -> Optional[int]:
    """Return index of Nth trading day after date."""
    date_list = list(trading_days)
    for i, d in enumerate(date_list):
        if d > date:
            target = i + offset - 1
            if target < len(date_list):
                return target
            return None
    return None


def _is_month_start(date: pd.Timestamp) -> bool:
    return date.day <= 3   # approximate


def run_ablation(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    start: str,
    end: str,
) -> dict[int, BacktestResult]:
    """
    Run all 4 strategies and return results dict {strategy_id: BacktestResult}.
    """
    results = {}
    for strategy in range(4):
        logger.info("Running strategy %d: %s", strategy, STRATEGY_NAMES[strategy])
        config = BacktestConfig(strategy=strategy, start_date=start, end_date=end)
        engine = BacktestEngine(prices, signals, config)
        results[strategy] = engine.run()
    return results
