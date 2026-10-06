"""
src/api/main.py
===============
FastAPI REST API for FinRisk AI.

Endpoints:
  GET  /health                     → health check
  GET  /tickers                    → list of universe tickers
  POST /analyze                    → run full NLP + risk pipeline on text
  GET  /signals                    → get current ticker signals
  GET  /portfolio                  → current portfolio weights
  POST /rebalance                  → trigger rebalancing
  GET  /portfolio/history          → portfolio value history
  GET  /events                     → recent event intelligence
  POST /backtest                   → run backtest for date range + strategy
  GET  /explain/{ticker}           → explainability card for ticker

All responses follow a consistent JSON schema with status, data, timestamp.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Internal modules
from src.nlp.entity import resolve_primary, TICKER_DB, PROTOTYPE_UNIVERSE
from src.nlp.sentiment import score_text
from src.nlp.events import classify_keyword_fallback
from src.nlp.novelty import NoveltyDetector
from src.risk.evidence import quick_evidence
from src.risk.impact import compute_impact_from_dict
from src.risk.signal import compute_signal
from src.portfolio.rebalancer import Rebalancer, format_decision_card
from src.portfolio.constraints import PortfolioConstraints
from src.backtest.engine import BacktestEngine, BacktestConfig, STRATEGY_NAMES, run_ablation
from src.backtest.metrics import compare_strategies

logger = logging.getLogger(__name__)
DATA_DIR = Path(__file__).parents[2] / "data"

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="FinRisk AI",
    description="Event-Driven Financial Risk Intelligence & Tactical Index Rebalancing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global state (in-memory for demo; replace with DB in production)
# ---------------------------------------------------------------------------
_novelty_detector = NoveltyDetector()
_rebalancer: Optional[Rebalancer] = None
_prices: Optional[pd.DataFrame] = None
_signals_cache: list[dict] = []


def _get_rebalancer() -> Rebalancer:
    global _rebalancer, _prices
    if _rebalancer is None:
        _load_prices()
        tickers = PROTOTYPE_UNIVERSE
        _rebalancer = Rebalancer(
            tickers=tickers,
            prices=_prices,
            constraints=PortfolioConstraints(),
        )
    return _rebalancer


def _load_prices() -> pd.DataFrame:
    global _prices
    if _prices is not None:
        return _prices
    prices_path = DATA_DIR / "prices.csv"
    if prices_path.exists():
        _prices = pd.read_csv(prices_path, index_col=0, parse_dates=True)
    else:
        _prices = _generate_synthetic_prices()
    return _prices


@app.on_event("startup")
async def startup():
    _load_prices()
    logger.info("FinRisk AI API started")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="News headline or body text to analyze")
    news_count: int = Field(1, ge=1)
    news_sources: int = Field(1, ge=1)
    sec_confirmed: bool = False
    social_count: int = Field(0, ge=0)
    spike: float = Field(1.0, ge=0)


class RebalanceRequest(BaseModel):
    signals: list[dict] = Field(default_factory=list)
    timestamp: Optional[str] = None


class BacktestRequest(BaseModel):
    strategy: int = Field(3, ge=0, le=3)
    start_date: str = "2023-01-01"
    end_date: str = "2024-01-01"


def _response(data: Any, message: str = "OK") -> dict:
    return {
        "status": "success",
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return _response({"status": "healthy", "version": "1.0.0"})


@app.get("/tickers")
def get_tickers():
    return _response([
        {"ticker": k, "company": v["company"], "sector": v["sector"]}
        for k, v in TICKER_DB.items()
    ])


@app.get("/universe")
def get_universe():
    """
    Return the 15-stock prototype universe with current signal data merged in.
    If no live signals exist yet, synthetic baseline scores are returned so
    the heatmap always renders.
    """
    import random, math

    # Build a lookup from the recent signals cache (last signal per ticker)
    signal_by_ticker: dict[str, dict] = {}
    for s in _signals_cache:
        ticker = s.get("ticker", "")
        if ticker:
            signal_by_ticker[ticker] = s

    rows = []
    rng = random.Random(42)   # deterministic seed so demo values are stable

    for ticker in PROTOTYPE_UNIVERSE:
        info = TICKER_DB.get(ticker, {})
        sig  = signal_by_ticker.get(ticker)

        if sig:
            actionability = sig.get("signal", {}).get("actionability", 0.0)
            impact        = sig.get("impact", {}).get("score", 5.0)
            evidence      = sig.get("evidence", {}).get("score", 50.0)
        else:
            # Synthetic baseline — small non-zero values so heatmap tiles render
            actionability = round(rng.uniform(-0.12, 0.18), 3)
            impact        = round(rng.uniform(3.5, 7.0), 1)
            evidence      = round(rng.uniform(40, 80), 1)

        rows.append({
            "ticker":        ticker,
            "company":       info.get("company", ticker),
            "sector":        info.get("sector", "Unknown"),
            "actionability": actionability,
            "impact":        impact,
            "evidence":      evidence,
            "live":          ticker in signal_by_ticker,
        })

    return _response(rows)


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """Run the full NLP + risk analysis pipeline on a piece of text."""
    text = req.text

    # Entity resolution
    entity = resolve_primary(text)
    if entity is None:
        ticker = "UNK"
        company = "Unknown"
        sector = "Unknown"
    else:
        ticker  = entity.ticker
        company = entity.company
        sector  = entity.sector

    # Sentiment
    sent = score_text(text)

    # Event classification
    event = classify_keyword_fallback(text)

    # Novelty
    novelty_result = _novelty_detector.process_article(
        article_id=str(hash(text)),
        text=text,
        ticker=ticker,
    )

    # Evidence
    evidence = quick_evidence(
        news_count=req.news_count,
        news_sources=req.news_sources,
        sec_confirmed=req.sec_confirmed,
        social_count=req.social_count,
        news_sentiment=sent.sentiment_score,
        ticker=ticker,
    )

    # Impact
    impact = compute_impact_from_dict({
        "ticker":              ticker,
        "sentiment_score":     sent.sentiment_score,
        "sentiment_confidence":sent.confidence,
        "event_type":          event.event_type,
        "event_weight":        event.event_weight,
        "novelty_score":       novelty_result.novelty_score,
        "spike_multiplier":    req.spike,
        "evidence_score":      evidence.evidence_score,
        "hist_vol_pct":        0.5,
    })

    # Actionability signal
    signal = compute_signal(
        ticker               = ticker,
        sentiment            = sent.sentiment_score,
        sentiment_confidence = sent.confidence,
        impact_score         = impact.impact_score,
        novelty              = novelty_result.novelty_score,
        spike                = req.spike,
        evidence_score       = evidence.evidence_score,
        allow_action         = evidence.allow_action,
    )

    result = {
        "ticker":       ticker,
        "company":      company,
        "sector":       sector,
        "sentiment": {
            "score":      sent.sentiment_score,
            "confidence": sent.confidence,
            "label":      sent.label,
        },
        "event": {
            "type":       event.event_type,
            "weight":     event.event_weight,
            "confidence": event.confidence,
        },
        "novelty": {
            "score":      novelty_result.novelty_score,
            "is_novel":   novelty_result.is_novel,
            "cluster_id": novelty_result.cluster_id,
            "cluster_size": novelty_result.cluster_size,
        },
        "evidence": {
            "score":  evidence.evidence_score,
            "status": evidence.status,
            "emoji":  evidence.status_emoji,
            "allow_action": evidence.allow_action,
        },
        "impact": {
            "score":       impact.impact_score,
            "explanation": impact.explanation,
        },
        "signal": {
            "actionability":   signal.actionability,
            "direction":       signal.signal_direction,
            "abstained":       signal.abstained,
            "abstain_reason":  signal.abstain_reason,
        },
    }

    _signals_cache.append({**result, "timestamp": datetime.now(timezone.utc).isoformat(), "text": text[:200]})
    return _response(result)


@app.get("/signals")
def get_signals(limit: int = Query(50, ge=1, le=500)):
    """Return recent signal history."""
    return _response(_signals_cache[-limit:])


@app.get("/events")
def get_events(
    ticker:    Optional[str] = Query(None),
    event_type: Optional[str] = Query(None, alias="type"),
    limit:     int = Query(50, ge=1, le=500),
):
    """
    Return recent event intelligence records formatted for the UI.
    Pulls from _signals_cache; if empty, returns synthetic demo events
    so the Event Intelligence page always renders.
    """
    import random

    # ── pull from live cache ──────────────────────────────────────────
    events: list[dict] = []
    for s in reversed(_signals_cache[-limit * 2:]):
        if ticker and s.get("ticker") != ticker.upper():
            continue
        evt_type = s.get("event", {}).get("type", "Other")
        if event_type and evt_type != event_type:
            continue

        ev_score = s.get("evidence", {}).get("score", 50.0)
        status   = "CONFIRMED" if ev_score >= 70 else ("DEVELOPING" if ev_score >= 40 else "WATCH")
        sig      = s.get("signal", {})

        events.append({
            "id":          str(hash(s.get("text", s.get("ticker", "")) + s.get("timestamp", ""))),
            "ticker":      s.get("ticker", "UNK"),
            "company":     s.get("company", ""),
            "sector":      s.get("sector", ""),
            "headline":    s.get("text", "")[:120] or f"{s.get('ticker')} — {evt_type} event",
            "ts":          str(s.get("timestamp", ""))[:16],
            "event_type":  evt_type,
            "status":      status,
            "sentiment":   s.get("sentiment", {}).get("score", 0.0),
            "confidence":  s.get("sentiment", {}).get("confidence", 0.5),
            "novelty":     s.get("novelty", {}).get("score", 0.5),
            "spike":       s.get("spike_multiplier", 1.0),
            "evidence":    ev_score,
            "impact":      s.get("impact", {}).get("score", 5.0),
            "action":      sig.get("direction", "HOLD"),
            "abstained":   sig.get("abstained", False),
            "abstain_reason": sig.get("abstain_reason", ""),
            "mode":        "live",
        })
        if len(events) >= limit:
            break

    # ── synthetic demo fallback (cache is empty) ──────────────────────
    if not events:
        rng = random.Random(99)
        demo_tickers = PROTOTYPE_UNIVERSE[:8]
        evt_types    = ["Earnings", "M&A", "Regulatory", "Product/Partnership",
                        "Supply Chain", "Legal", "Cybersecurity", "Macroeconomic"]
        headlines    = [
            "{co} beats Q3 earnings estimates — revenue up 18% YoY",
            "{co} acquires rival in $4.2B all-stock deal",
            "{co} faces FTC antitrust inquiry into cloud practices",
            "{co} unveils next-gen chip architecture at keynote",
            "{co} reports semiconductor supply constraints into Q4",
            "{co} settles IP lawsuit for $380M",
            "{co} discloses data breach affecting 2.1M users",
            "{co} cuts revenue guidance amid macro headwinds",
        ]
        for i, t in enumerate(demo_tickers):
            info     = TICKER_DB.get(t, {})
            ev_score = round(rng.uniform(35, 95), 1)
            status   = "CONFIRMED" if ev_score >= 70 else ("DEVELOPING" if ev_score >= 40 else "WATCH")
            sent     = round(rng.uniform(-0.8, 0.9), 2)
            impact   = round(rng.uniform(4, 9), 1)
            evt      = evt_types[i % len(evt_types)]
            hl       = headlines[i % len(headlines)].format(co=info.get("company", t).split()[0])
            events.append({
                "id":          f"demo-{i}",
                "ticker":      t,
                "company":     info.get("company", t),
                "sector":      info.get("sector", "Unknown"),
                "headline":    hl,
                "ts":          datetime.now(timezone.utc).strftime("%H:%M"),
                "event_type":  evt,
                "status":      status,
                "sentiment":   sent,
                "confidence":  round(rng.uniform(0.65, 0.98), 2),
                "novelty":     round(rng.uniform(0.4, 0.95), 2),
                "spike":       round(rng.uniform(1.5, 7.0), 1),
                "evidence":    ev_score,
                "impact":      impact,
                "action":      "BUY" if sent > 0.2 else ("SELL" if sent < -0.2 else "HOLD"),
                "abstained":   ev_score < 40,
                "abstain_reason": "Evidence below 40/100 threshold" if ev_score < 40 else "",
                "mode":        "live-demo",
            })

    return _response(events)


@app.get("/portfolio")
def get_portfolio():
    """Return current portfolio weights."""
    rb = _get_rebalancer()
    weights = rb.current_weights
    rows = []
    for t, w in sorted(weights.items(), key=lambda x: -x[1]):
        pct = round(w * 100, 1)
        rows.append({
            "ticker":  t,
            "company": TICKER_DB.get(t, {}).get("company", t),
            "sector":  TICKER_DB.get(t, {}).get("sector", "Unknown"),
            "weight":  pct,
            "prev":    pct,
            "next":    pct,
            "delta":   0.0,
            "action":  "HOLD",
        })
    return _response(rows)


@app.post("/rebalance")
def trigger_rebalance(req: Optional[RebalanceRequest] = None):
    """Trigger a portfolio rebalancing based on provided or cached signals."""
    rb = _get_rebalancer()

    if req and req.signals:
        signals_df = pd.DataFrame(req.signals)
    elif _signals_cache:
        flattened = []
        for s in _signals_cache:
            sig = s.get("signal", {})
            ev = s.get("evidence", {})
            sent = s.get("sentiment", {})
            imp = s.get("impact", {})
            nov = s.get("novelty", {})
            evt = s.get("event", {})
            flattened.append({
                "ticker": s.get("ticker", "UNK"),
                "actionability": sig.get("actionability", 0.0),
                "sent_confidence": sent.get("confidence", 0.5),
                "impact_score": imp.get("score", 5.0),
                "novelty_score": nov.get("score", 0.5),
                "spike_multiplier": s.get("spike_multiplier", 1.0),
                "evidence_score": ev.get("score", 50.0),
                "event_type": evt.get("type", "Other"),
                "abstained": sig.get("abstained", False),
                "abstain_reason": sig.get("abstain_reason", ""),
                "headline": s.get("text", ""),
                "timestamp": s.get("timestamp", datetime.now(timezone.utc).isoformat()),
            })
        signals_df = pd.DataFrame(flattened)
    else:
        # Fallback signals for prototype universe
        import random
        rng = random.Random(42)
        rows = []
        for t in PROTOTYPE_UNIVERSE:
            act = round(rng.uniform(-0.15, 0.25), 3)
            rows.append({
                "ticker": t,
                "actionability": act,
                "sent_confidence": round(rng.uniform(0.6, 0.95), 2),
                "impact_score": round(rng.uniform(4, 8), 1),
                "novelty_score": round(rng.uniform(0.3, 0.9), 2),
                "spike_multiplier": round(rng.uniform(1.2, 5.0), 1),
                "evidence_score": round(rng.uniform(45, 90), 1),
                "event_type": rng.choice(["Earnings", "Product/Partnership", "M&A", "Regulatory"]),
                "abstained": False,
                "abstain_reason": "",
                "headline": f"Signal for {t}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        signals_df = pd.DataFrame(rows)

    event = rb.rebalance(signals_df)

    portfolio_rows = []
    for d in event.decisions:
        delta = round(d.delta * 100, 1)
        action = "BUY" if delta > 0.05 else ("SELL" if delta < -0.05 else "HOLD")
        portfolio_rows.append({
            "ticker":        d.ticker,
            "company":       d.company,
            "sector":        TICKER_DB.get(d.ticker, {}).get("sector", "Unknown"),
            "prev":          round(d.from_weight * 100, 1),
            "next":          round(d.to_weight * 100, 1),
            "delta":         delta,
            "action":        action,
            "actionability": d.actionability,
            "abstained":     d.abstained,
            "explanation":   format_decision_card(d),
        })

    return _response({
        "timestamp":    event.timestamp.isoformat(),
        "turnover":     round(event.turnover * 100, 1),
        "n_acted":      event.n_acted,
        "n_abstained":  event.n_abstained,
        "prev_weights": {k: round(v * 100, 2) for k, v in event.prev_weights.items()},
        "new_weights":  {k: round(v * 100, 2) for k, v in event.new_weights.items()},
        "portfolio":    portfolio_rows,
        "decisions": [
            {
                "ticker":        d.ticker,
                "company":       d.company,
                "from_weight":   d.from_weight,
                "to_weight":     d.to_weight,
                "delta":         d.delta,
                "direction":     d.direction,
                "actionability": d.actionability,
                "abstained":     d.abstained,
                "explanation":   format_decision_card(d),
            }
            for d in event.decisions
        ],
    })


@app.post("/backtest")
def run_backtest(req: BacktestRequest):
    """Run a backtest for specified strategy and date range."""
    prices = _load_prices()
    if prices is None or prices.empty:
        raise HTTPException(status_code=500, detail="No price data available")

    # Load signals from cache or demo
    if _signals_cache:
        signals_df = pd.DataFrame(_signals_cache)
    else:
        signals_df = _generate_demo_signals(prices, req.start_date, req.end_date)

    config = BacktestConfig(
        strategy=req.strategy,
        start_date=req.start_date,
        end_date=req.end_date,
    )
    engine = BacktestEngine(prices, signals_df, config)
    result = engine.run()

    return _response({
        "strategy":       result.strategy,
        "strategy_name":  result.strategy_name,
        "metrics":        result.metrics,
        "portfolio_values": {
            str(k.date()): round(v, 2)
            for k, v in result.portfolio_values.items()
        },
    })


@app.get("/backtest/ablation")
def run_ablation_endpoint(
    start: str = Query(None),
    end:   str = Query(None),
):
    """Run all 4 strategies and return comparison table."""
    try:
        prices = _load_prices()
        if prices is None or prices.empty:
            raise HTTPException(status_code=500, detail="No price data available")

        # Clamp to actual available price range so demo always works
        price_start = str(prices.index[0].date())
        price_end   = str(prices.index[-1].date())

        # Use inner 80% of the date range by default (leaves room for warm-up)
        n = len(prices.index)
        default_start = str(prices.index[int(n * 0.10)].date())
        default_end   = str(prices.index[int(n * 0.90)].date())

        use_start = start or default_start
        use_end   = end   or default_end

        # Clamp user-supplied dates to available range
        use_start = max(use_start, price_start)
        use_end   = min(use_end,   price_end)

        signals_df = _generate_demo_signals(prices, use_start, use_end)
        results    = run_ablation(prices, signals_df, use_start, use_end)
        comparison = compare_strategies(results)

        return _response({
            "comparison":   comparison.to_dict("records"),
            "date_range":   {"start": use_start, "end": use_end},
            "strategies": {
                str(k): {
                    "name":    v.strategy_name,
                    "metrics": v.metrics,
                }
                for k, v in results.items()
            },
        })
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Ablation endpoint error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/explain/{ticker}")
def explain_ticker(ticker: str):
    """Return the latest explainability card for a ticker."""
    ticker = ticker.upper()
    # Find most recent signal for this ticker
    relevant = [s for s in reversed(_signals_cache) if s.get("ticker") == ticker]
    if not relevant:
        raise HTTPException(status_code=404, detail=f"No signals found for {ticker}")
    return _response(relevant[0])


# ---------------------------------------------------------------------------
# Stress Testing — Module B
# ---------------------------------------------------------------------------

STRESS_SCENARIOS = {
    "rate_shock_150bps": {
        "label": "Rate Shock +150 bps",
        "description": "Central bank emergency hike of 150 bps — triggered by CPI surprise.",
        "shocks": {"equity_drop": -0.08, "rate_rise_bps": 150, "credit_spread_bps": 50, "fx_usd_strength": 0.04},
        "trigger": "Geopolitical / Macroeconomic event with Impact Score > 7.0",
        "icon": "📈",
    },
    "equity_crash_10pct": {
        "label": "Equity Crash −10%",
        "description": "Broad market correction driven by earnings season collapse.",
        "shocks": {"equity_drop": -0.10, "rate_rise_bps": 0, "credit_spread_bps": 80, "fx_usd_strength": 0.02},
        "trigger": "Earnings / Macro shock — multiple constituents miss guidance.",
        "icon": "📉",
    },
    "credit_crisis": {
        "label": "Credit Spread +100 bps",
        "description": "Systemic credit event — widening IG and HY spreads.",
        "shocks": {"equity_drop": -0.05, "rate_rise_bps": -25, "credit_spread_bps": 100, "fx_usd_strength": -0.01},
        "trigger": "Regulatory / Legal events — systemically important institution.",
        "icon": "🏦",
    },
    "geopolitical_shock": {
        "label": "Geopolitical Risk Spike",
        "description": "Escalation in a major geopolitical conflict — energy and supply chain disruption.",
        "shocks": {"equity_drop": -0.06, "rate_rise_bps": 30, "credit_spread_bps": 60, "fx_usd_strength": 0.03},
        "trigger": "Supply Chain / Geopolitical — energy sector 8-K disclosures.",
        "icon": "🌐",
    },
}

BANKING_BOOK = [
    {"id": "INV_GRADE_BONDS",  "name": "Investment Grade Bonds",       "asset_class": "Fixed Income",  "notional": 42_000_000, "duration": 6.2,  "beta":  0.15, "credit_spread_sens": 0.35},
    {"id": "HY_BONDS",         "name": "High Yield Bonds",             "asset_class": "Fixed Income",  "notional": 18_000_000, "duration": 4.1,  "beta":  0.45, "credit_spread_sens": 0.60},
    {"id": "CORP_LOANS",       "name": "Corporate Loans (Term A)",     "asset_class": "Loans",         "notional": 35_000_000, "duration": 3.0,  "beta":  0.20, "credit_spread_sens": 0.50},
    {"id": "REVOLVER",         "name": "Revolving Credit Facility",    "asset_class": "Loans",         "notional": 12_000_000, "duration": 1.5,  "beta":  0.10, "credit_spread_sens": 0.30},
    {"id": "IR_SWAP_PAY",      "name": "IR Swap (Pay Fixed)",          "asset_class": "Derivatives",   "notional": 25_000_000, "duration": 7.0,  "beta":  0.00, "credit_spread_sens": 0.05},
    {"id": "CDS_PROTECTION",   "name": "CDS Protection Bought",        "asset_class": "Derivatives",   "notional": 10_000_000, "duration": 5.0,  "beta": -0.30, "credit_spread_sens":-0.90},
    {"id": "EQUITY_PORTFOLIO", "name": "Equity Portfolio (Large Cap)", "asset_class": "Equities",      "notional": 28_000_000, "duration": None, "beta":  1.00, "credit_spread_sens": 0.10},
    {"id": "GOVT_BONDS",       "name": "Government Bonds (10Y)",       "asset_class": "Fixed Income",  "notional": 20_000_000, "duration": 9.1,  "beta": -0.05, "credit_spread_sens": 0.02},
]


def _compute_stress_loss(asset: dict, shocks: dict) -> float:
    notional    = asset["notional"]
    duration    = asset.get("duration") or 0.0
    beta        = asset.get("beta", 0.0)
    cs_sens     = asset.get("credit_spread_sens", 0.0)
    rate_bps    = shocks.get("rate_rise_bps", 0) / 10_000
    credit_bps  = shocks.get("credit_spread_bps", 0) / 10_000
    equity_drop = shocks.get("equity_drop", 0.0)
    fx          = shocks.get("fx_usd_strength", 0.0)
    rate_pnl    = -duration * rate_bps * notional
    credit_pnl  = -cs_sens * credit_bps * notional
    equity_pnl  = beta * equity_drop * notional
    fx_pnl      = -fx * 0.05 * notional
    return round(rate_pnl + credit_pnl + equity_pnl + fx_pnl, 0)


@app.get("/stress")
def run_stress_test(scenario: str = Query("rate_shock_150bps")):
    """Run a macro stress test on the synthetic wholesale banking book."""
    if scenario not in STRESS_SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario. Options: {list(STRESS_SCENARIOS.keys())}")

    cfg    = STRESS_SCENARIOS[scenario]
    shocks = cfg["shocks"]

    assets = []
    for asset in BANKING_BOOK:
        loss = _compute_stress_loss(asset, shocks)
        assets.append({
            "id":           asset["id"],
            "name":         asset["name"],
            "asset_class":  asset["asset_class"],
            "notional":     asset["notional"],
            "pnl":          loss,
            "pnl_pct":      round(loss / asset["notional"] * 100, 2),
            "before_value": asset["notional"],
            "after_value":  asset["notional"] + loss,
        })

    total_before = sum(a["notional"] for a in BANKING_BOOK)
    total_loss   = sum(a["pnl"] for a in assets)
    total_after  = total_before + total_loss

    by_class: dict[str, dict] = {}
    for r in assets:
        cls = r["asset_class"]
        if cls not in by_class:
            by_class[cls] = {"asset_class": cls, "before": 0, "after": 0, "loss": 0}
        by_class[cls]["before"] += r["before_value"]
        by_class[cls]["after"]  += r["after_value"]
        by_class[cls]["loss"]   += r["pnl"]
    class_chart = [{**v, "loss_pct": round(v["loss"] / v["before"] * 100, 2)} for v in by_class.values()]

    losses = [a["pnl"] for a in assets]
    var_99 = round(float(np.percentile(losses, 1)), 0)

    return _response({
        "scenario":     scenario,
        "label":        cfg["label"],
        "description":  cfg["description"],
        "trigger":      cfg["trigger"],
        "icon":         cfg["icon"],
        "shocks":       shocks,
        "assets":       assets,
        "by_class":     class_chart,
        "total_before": total_before,
        "total_after":  total_after,
        "total_loss":   round(total_loss, 0),
        "loss_pct":     round(total_loss / total_before * 100, 2),
        "var_99":       var_99,
        "scenario_meta": {k: {"label": v["label"], "icon": v["icon"]} for k, v in STRESS_SCENARIOS.items()},
    })


# ---------------------------------------------------------------------------
# LLM Executive Narrative Summaries
# ---------------------------------------------------------------------------

def _build_narrative(ticker: str, signals: list[dict]) -> dict:
    import os
    if not signals:
        return {"ticker": ticker, "bullets": [], "source": "template"}

    latest         = signals[0]
    sent           = latest.get("sentiment", {})
    sig            = latest.get("signal", {})
    ev             = latest.get("evidence", {})
    imp            = latest.get("impact", {})
    evt            = latest.get("event", {})
    sent_score     = sent.get("score", 0.0)
    sent_label     = "bullish" if sent_score > 0.1 else ("bearish" if sent_score < -0.1 else "neutral")
    ev_score       = ev.get("score", 50)
    action         = sig.get("direction", "HOLD")
    abstained      = sig.get("abstained", False)
    actionability  = sig.get("actionability", 0.0)
    impact_score   = imp.get("score", 5.0)
    event_type     = evt.get("type", "Unknown")
    headlines      = [s.get("text", "")[:120] for s in signals[:3] if s.get("text")]
    rb             = _get_rebalancer()
    prev_w         = rb.current_weights.get(ticker, 1/15)
    prev_pp        = round(prev_w * 100, 1)
    delta_pp       = round(actionability * 2.5, 1)
    new_pp         = round(prev_pp + delta_pp, 1)

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if api_key:
        try:
            import urllib.request, json as _json
            hl_text = "\n".join(f"  - {h}" for h in headlines) or "  - No specific headlines."
            prompt = (
                f"You are a senior financial risk officer. Write exactly 2 bullet points (start each with •) "
                f"as an executive summary for {ticker}. Max 30 words per bullet. No disclaimers.\n\n"
                f"Ticker: {ticker}\nEvent: {event_type}\nSentiment: {sent_label} ({sent_score:+.2f})\n"
                f"Evidence: {ev_score}/100\nImpact: {impact_score:.1f}/10\nAction: {action}\n"
                f"Weight: {prev_pp}% → {new_pp}%\nHeadlines:\n{hl_text}"
            )
            payload = _json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 180, "temperature": 0.3},
            }).encode()
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
                data=payload, headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = _json.loads(resp.read())
            raw     = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            bullets = [b.strip().lstrip("•").strip() for b in raw.split("\n") if b.strip().startswith("•")]
            if bullets:
                return {"ticker": ticker, "bullets": bullets, "source": "gemini-1.5-flash",
                        "weight_change": {"from": prev_pp, "to": new_pp, "delta": delta_pp}}
        except Exception as e:
            logger.warning(f"Gemini narrative failed for {ticker}: {e}")

    # Template fallback
    b1 = (
        f"{'Abstained on' if abstained else action + ' on'} {ticker}: "
        f"weight {prev_pp}% → {new_pp}% (Δ{delta_pp:+.1f}pp) — "
        f"{event_type} event, {sent_label} sentiment ({sent_score:+.2f}), impact {impact_score:.1f}/10."
    ) if not abstained else (
        f"ABSTAINED on {ticker} — evidence {ev_score}/100 below 40-point gate; "
        f"position held at {prev_pp}% pending corroboration from SEC or additional news sources."
    )
    nov = latest.get("novelty", {})
    b2 = (
        f"Evidence {ev_score}/100 across {len(signals)} signals; "
        f"novelty {nov.get('score', 0.5):.2f} — "
        f"{'novel event requiring elevated attention.' if nov.get('is_novel') else 'corroborated signal; moderate position adjustment.'}"
    )
    return {
        "ticker": ticker, "bullets": [b1, b2], "source": "template",
        "weight_change": {"from": prev_pp, "to": new_pp, "delta": delta_pp},
    }


@app.get("/explain/narrative/{ticker}")
def explain_narrative(ticker: str):
    """2-bullet plain-English executive summary (Gemini or template fallback)."""
    ticker   = ticker.upper()
    relevant = [s for s in reversed(_signals_cache) if s.get("ticker") == ticker]
    if not relevant:
        info = TICKER_DB.get(ticker, {})
        return _response({
            "ticker": ticker,
            "bullets": [
                f"No confirmed signals for {ticker} yet — evidence gate requires ≥ 40/100 across multiple sources.",
                f"Monitoring {info.get('sector', 'Unknown')} events via GDELT and SEC EDGAR. Position held at baseline.",
            ],
            "source": "template",
        })
    return _response(_build_narrative(ticker, relevant[:5]))


# ---------------------------------------------------------------------------
# Demo data generators

# ---------------------------------------------------------------------------

def _generate_synthetic_prices(
    tickers: Optional[list] = None,
    n_days: int = 504,
) -> pd.DataFrame:
    """Generate GBM synthetic prices for demo mode."""
    if tickers is None:
        tickers = list(TICKER_DB.keys())[:20]

    np.random.seed(42)
    dates = pd.bdate_range(end=datetime.today(), periods=n_days)
    prices = {}
    for t in tickers:
        s0     = np.random.uniform(50, 500)
        mu     = np.random.uniform(0.05, 0.25) / 252
        sigma  = np.random.uniform(0.15, 0.45) / np.sqrt(252)
        shocks = np.random.normal(mu, sigma, n_days)
        prices[t] = s0 * np.exp(np.cumsum(shocks))
    return pd.DataFrame(prices, index=dates)


def _generate_demo_signals(
    prices: pd.DataFrame,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Generate synthetic signals for demo backtesting."""
    np.random.seed(123)
    tickers = list(prices.columns)[:10]
    dates = pd.bdate_range(start, end, freq="W")   # weekly signals

    rows = []
    for date in dates:
        for t in tickers:
            sent = np.random.uniform(-1, 1)
            rows.append({
                "timestamp":       pd.Timestamp(date, tz="UTC"),
                "ticker":          t,
                "sent_score":      round(sent, 3),
                "sent_confidence": round(np.random.uniform(0.5, 0.99), 3),
                "actionability":   round(sent * np.random.uniform(0.5, 0.9), 3),
                "event_type":      np.random.choice(["Earnings", "M&A", "Regulatory", "Other"]),
                "impact_score":    round(np.random.uniform(3, 9), 2),
                "novelty_score":   round(np.random.uniform(0.3, 1.0), 3),
                "spike_multiplier":round(np.random.uniform(1, 8), 2),
                "evidence_score":  round(np.random.uniform(30, 95), 1),
                "allow_action":    bool(np.random.random() > 0.2),
                "abstained":       bool(np.random.random() < 0.1),
                "abstain_reason":  "",
                "headline":        f"Simulated signal for {t}",
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
