# FinRisk AI 🧠 — Architecture Document

**S&P Global & CRISIL Campus Hackathon 2026**

---

## Table of Contents

1. [High Level Design (HLD)](#high-level-design-hld)
   - [System Overview](#system-overview)
   - [Layer Architecture](#layer-architecture)
   - [End-to-End Data Flow](#end-to-end-data-flow)
   - [Deployment Topology](#deployment-topology)
2. [Low Level Design (LLD)](#low-level-design-lld)
   - [Module Dependency Graph](#module-dependency-graph)
   - [NLP Pipeline — Class Diagram](#nlp-pipeline--class-diagram)
   - [Risk & Portfolio Engine — Class Diagram](#risk--portfolio-engine--class-diagram)
   - [FastAPI Endpoint Flow](#fastapi-endpoint-flow)
   - [Frontend Component Tree](#frontend-component-tree)
   - [Backtest Engine — Sequence Diagram](#backtest-engine--sequence-diagram)
   - [Optimizer — Decision Flow](#optimizer--decision-flow)
   - [Evidence Gate — State Machine](#evidence-gate--state-machine)

---

## High Level Design (HLD)

### System Overview

FinRisk AI is a **5-layer autonomous platform** that converts raw unstructured financial event streams into risk-bounded, explainable portfolio decisions in near-real time.

```mermaid
graph TD
    subgraph External["🌐 External Data Sources"]
        G["GDELT 2.0\nGlobal News DOC/GKG"]
        S["SEC EDGAR\ndata.sec.gov 8-K Feed"]
        P["Historical Price Cache\n15-Stock GBM Universe"]
    end

    subgraph L1["Layer 1 — Ingestion"]
        GI["GDELTIngester\n15-min polling + retry"]
        SI["SECIngester\nCIK lookup + item filter"]
        PI["PriceLoader\nCSV cache + refresh"]
    end

    subgraph L2["Layer 2 — NLP Intelligence"]
        ER["EntityResolver\nFuzzy + regex → ticker"]
        ND["NoveltyDetector\nFAISS cosine clustering"]
        EC["EventClassifier\nBART zero-shot (12 classes)"]
        SS["SentimentScorer\nFinBERT [-1, +1]"]
        EV["EvidenceGater\nMulti-source (0-100)"]
    end

    subgraph L3["Layer 3 — Risk Engine"]
        AS["AttentionSpike\nZ-score seasonality"]
        IS["ImpactScorer\n6-factor [1-10]"]
        SF["SignalFuser\nActionability [-1, +1]"]
        PO["PortfolioOptimizer\nCVXPY Quadratic Program"]
        MS["MacroStressEngine\n4 scenarios x 8 assets"]
    end

    subgraph L4["Layer 4 — API Gateway"]
        FA["FastAPI (Uvicorn)\n12 async REST endpoints"]
    end

    subgraph L5["Layer 5 — Dashboard"]
        RD["React 18 + Vite\n5 Specialized Tabs"]
    end

    G --> GI
    S --> SI
    P --> PI
    GI --> ER
    SI --> ER
    PI --> PO
    ER --> ND & SS & EC
    ND --> EV
    SS --> EV
    EC --> EV
    EV --> AS --> IS --> SF --> PO
    PO --> FA
    MS --> FA
    FA --> RD
```

---

### Layer Architecture

```mermaid
graph LR
    subgraph "Layer 1 — Ingestion"
        direction TB
        A1["GDELT Ingester"]
        A2["SEC Ingester"]
        A3["Price Loader"]
    end

    subgraph "Layer 2 — NLP Pipeline"
        direction TB
        B1["Entity Resolver"]
        B2["FinBERT Sentiment"]
        B3["BART Event Classifier"]
        B4["FAISS Novelty Detector"]
        B5["Evidence Gater"]
    end

    subgraph "Layer 3 — Risk Engine"
        direction TB
        C1["Attention Spike Z-score"]
        C2["Impact Scorer 6-factor formula"]
        C3["Signal Fuser Actionability"]
        C4["CVXPY Optimizer Ledoit-Wolf"]
        C5["Macro Stress 4 scenarios"]
    end

    subgraph "Layer 4 — API Gateway"
        direction TB
        D1["12 REST Endpoints"]
        D2["Async Uvicorn Loop"]
        D3["60s Result Cache"]
    end

    subgraph "Layer 5 — React Dashboard"
        direction TB
        E1["Market Radar"]
        E2["Event Intelligence"]
        E3["Event Replay"]
        E4["Portfolio Optimizer"]
        E5["Macro Stress Test"]
    end

    A1 & A2 & A3 --> B1
    B1 --> B2 & B3 & B4
    B2 & B3 & B4 --> B5
    B5 --> C1 --> C2 --> C3 --> C4
    C4 & C5 --> D1
    D1 --> D2 --> D3
    D3 --> E1 & E2 & E3 & E4 & E5
```

---

### End-to-End Data Flow

```mermaid
sequenceDiagram
    participant GDELT as GDELT API
    participant SEC as SEC EDGAR
    participant ING as Ingestion Layer
    participant NLP as NLP Pipeline
    participant RISK as Risk Engine
    participant OPT as CVXPY Optimizer
    participant API as FastAPI
    participant UI as React Dashboard

    GDELT-->>ING: Raw articles (JSON, every 15 min)
    SEC-->>ING: 8-K filings (CIK lookup)
    ING->>NLP: RawEvent (ticker, headline, source, ts)
    Note over NLP: Entity Resolve → FinBERT → BART → FAISS Novelty → Evidence Gate
    NLP->>RISK: ProcessedSignal (ticker, sentiment, event_type, novelty, evidence, abstain?)
    alt Evidence >= 40 (DEVELOPING / CONFIRMED)
        RISK->>OPT: ActionabilitySignal (ticker, score in [-1,+1])
        OPT->>OPT: Solve QP max(alpha^T w - lambda_risk*w^T*Sigma*w - lambda_turn*norm(delta_w,1))
        OPT->>API: OptimizeResult (weights, trades, turnover)
    else Evidence < 40 (WATCH — Abstain)
        RISK->>API: AbstentionRecord (ticker, evidence, reason)
    end
    API->>UI: JSON response (< 200ms demo / < 2s live)
    UI->>UI: Render portfolio update + toast alert
```

---

### Deployment Topology

```mermaid
graph TD
    subgraph Dev["Local Development"]
        subgraph Backend["Backend port 8000"]
            UV["uvicorn src.api.main:app"]
            PY["Python 3.11 Runtime"]
            ML["ML Models Cache ~1.2GB"]
        end
        subgraph Frontend["Frontend port 5173"]
            VT["Vite Dev Server npm run dev"]
            RX["React 18 App"]
        end
    end

    subgraph Data["Local Data"]
        CSV["data/prices.csv 504 days x 15 tickers"]
        NEWS["data/news/ GDELT cache CSVs"]
        SEC2["data/sec/ EDGAR 8-K CSVs"]
    end

    subgraph External2["Live APIs (optional)"]
        GDELT2["api.gdeltproject.org (rate-limited, public)"]
        EDGAR2["data.sec.gov (public, User-Agent only)"]
        GEMINI["generativelanguage.googleapis.com (optional)"]
    end

    UV --> PY --> ML
    VT --> RX
    RX -->|"HTTP fetch port 8000"| UV
    UV -->|reads| CSV & NEWS & SEC2
    UV -->|"live mode"| GDELT2 & EDGAR2 & GEMINI
```

---

## Low Level Design (LLD)

### Module Dependency Graph

```mermaid
graph TD
    subgraph api["src/api/main.py"]
        MAIN["FastAPI App 12 endpoints"]
    end

    subgraph portfolio["src/portfolio/"]
        OPT2["optimizer.py PortfolioOptimizer"]
        REB["rebalancer.py ConstraintRebalancer"]
        CON["constraints.py WeightRules"]
    end

    subgraph backtest["src/backtest/"]
        BTE["engine.py BacktestEngine"]
        MET["metrics.py MetricBundle"]
    end

    subgraph risk["src/risk/"]
        ATT["attention.py AttentionSpike"]
        EVI["evidence.py EvidenceScorer"]
        IMP["impact.py ImpactScorer"]
        SIG["signal.py SignalFuser"]
    end

    subgraph nlp["src/nlp/"]
        ENT["entity.py EntityResolver"]
        SEN["sentiment.py SentimentScorer"]
        EVT["events.py EventClassifier"]
        NOV["novelty.py NoveltyDetector"]
    end

    subgraph ingestion["src/ingestion/"]
        GDI["gdelt.py GDELTIngester"]
        SEI["sec.py SECIngester"]
        SOI["social.py SocialIngester"]
    end

    MAIN --> OPT2 & BTE & ATT & EVI & IMP & SIG
    MAIN --> GDI & SEI
    OPT2 --> CON
    REB --> CON
    OPT2 --> MET
    BTE --> MET
    SIG --> IMP --> ATT & EVI
    EVI --> NOV & SEN & EVT
    NOV --> ENT
    SEN --> ENT
    EVT --> ENT
    GDI --> ENT
    SEI --> ENT
```

---

### NLP Pipeline — Class Diagram

```mermaid
classDiagram
    class EntityResolver {
        +TICKER_DB dict
        +resolve(text) List_Tuple
        -_fuzzy_match(text) str
        -_regex_match(text) str
        +get_ticker_info(ticker) dict
    }

    class SentimentScorer {
        -_pipeline Pipeline
        -MODEL "ProsusDE/finbert"
        +score(text) SentimentResult
        +score_batch(texts) List
    }

    class EventClassifier {
        -_classifier Pipeline
        -LABELS List_str
        -MODEL "facebook/bart-large-mnli"
        +classify(text) EventResult
    }

    class NoveltyDetector {
        -_indices dict
        -_encoder SentenceTransformer
        -SIMILARITY_THRESHOLD 0.85
        -WINDOW_HOURS 24
        +compute(text, ticker, event_class) float
        +clear_expired(cutoff_ts) void
        -_get_scope_key(ticker, event_class) str
    }

    class SentimentResult {
        +score float
        +label str
        +confidence float
    }

    class EventResult {
        +label str
        +score float
    }

    EntityResolver --> SentimentScorer
    EntityResolver --> EventClassifier
    EntityResolver --> NoveltyDetector
    SentimentScorer --> SentimentResult
    EventClassifier --> EventResult
```

---

### Risk & Portfolio Engine — Class Diagram

```mermaid
classDiagram
    class EvidenceScorer {
        +WATCH_THRESHOLD 40
        +CONFIRMED_THRESHOLD 70
        +compute(news_score, sec_score, social_score, available_sources) EvidenceResult
        -_renormalize_weights(available_sources) dict
        -_compute_diversity(sources) float
        -_compute_agreement(scores) float
    }

    class AttentionSpike {
        -_history dict
        +compute(ticker, timestamp) AttentionResult
        -_get_baseline(ticker, hour, dow) Tuple
    }

    class ImpactScorer {
        -WEIGHTS dict
        -CALIBRATION dict
        +compute(sentiment, event_label, novelty, attention_z, evidence, hist_vol_pct) ImpactResult
        +explain() str
    }

    class SignalFuser {
        +fuse(sentiment, impact, novelty, attention_norm, evidence, hist_vol_pct) SignalResult
        -_compute_M(sentiment, impact, novelty, attention, evidence) float
        -_compute_R(hist_vol_pct) float
    }

    class PortfolioOptimizer {
        +lambda_risk 0.5
        +lambda_turnover 0.3
        +max_weight 0.15
        +sector_cap 0.25
        +max_turnover 0.10
        +evidence_gate 40
        +optimize(signals, prev_weights, prices_df) OptimizeResult
        -_build_covariance(prices_df) ndarray
        -_apply_abstention(signals, prev_weights) dict
    }

    class MacroStressEngine {
        +SCENARIOS dict
        +BANKING_BOOK List
        +run(scenario_id) StressResult
        -_compute_pnl(asset, scenario) float
        -_compute_var99(losses) float
    }

    class OptimizeResult {
        +weights dict
        +trades DataFrame
        +sharpe_est float
        +turnover float
        +solve_time_ms float
        +status str
    }

    EvidenceScorer --> AttentionSpike
    ImpactScorer --> AttentionSpike
    ImpactScorer --> EvidenceScorer
    SignalFuser --> ImpactScorer
    PortfolioOptimizer --> SignalFuser
    PortfolioOptimizer --> OptimizeResult
```

---

### FastAPI Endpoint Flow

```mermaid
flowchart TD
    REQ(["HTTP Request"])

    REQ --> R3["POST /analyze"]
    REQ --> R4["POST /rebalance"]
    REQ --> R5["GET /backtest/ablation"]
    REQ --> R6["GET /stress?scenario=id"]
    REQ --> R7["GET /explain/narrative/ticker"]

    R3 --> P1["EntityResolver.resolve()"]
    P1 --> P2["SentimentScorer.score()"]
    P2 --> P3["EventClassifier.classify()"]
    P3 --> P4["NoveltyDetector.compute()"]
    P4 --> P5["EvidenceScorer.compute()"]
    P5 --> P6["AttentionSpike.compute()"]
    P6 --> P7["ImpactScorer.compute()"]
    P7 --> P8["SignalFuser.fuse()"]
    P8 --> CACHE[("Result Cache sha256 keyed 60s TTL")]

    R4 --> OPT["PortfolioOptimizer.optimize()"]
    OPT --> CACHE

    R5 --> BE["BacktestEngine.run x4"]
    BE --> MET2["compute_metrics()"]

    R6 --> MSE["MacroStressEngine.run()"]

    R7 --> LLM{"GOOGLE_API_KEY set?"}
    LLM -->|Yes| GEM["Gemini 1.5 Flash API call"]
    LLM -->|No| TMPL["Deterministic Template fallback"]

    CACHE --> RESP(["JSON Response"])
    MET2 & MSE & GEM & TMPL --> RESP
```

---

### Frontend Component Tree

```mermaid
graph TD
    APP["App.jsx\nstate: mode, toasts, backendHealthy\neffect: healthPoll()"]

    APP --> HDR["Header.jsx Live/Demo toggle Pulse animation"]
    APP --> TOAST["ToastEngine self-contained zero npm deps"]

    APP --> TAB1["MarketRadar.jsx"]
    APP --> TAB2["EventIntelligence.jsx"]
    APP --> TAB3["EventReplay.jsx"]
    APP --> TAB4["Portfolio.jsx"]
    APP --> TAB5["MacroStressTest.jsx"]

    TAB1 --> HM["StockHeatmap 15 tickers x actionability"]
    TAB1 --> RI["RiskIndexChart intraday timeline"]
    TAB1 --> SB["SectorBreakdown BarChart"]

    TAB2 --> EF["EventFeed Filterable list evidence cards"]
    TAB2 --> SC["SignalCard abstention banner evidence bars"]

    TAB3 --> RP["ReplaySlider 3 scenarios step-by-step"]
    TAB3 --> EV2["EvidenceEvolution LineChart"]

    TAB4 --> WD["WeightDeltaBars BUY/SELL badges"]
    TAB4 --> AB["AblationChart 4 equity curves"]
    TAB4 --> NM["NarrativeModal LLM 2-bullet popup"]
    TAB4 --> AJ["AuditJSONExport Client-side download"]

    TAB5 --> SC2["ScenarioSelector 4 pill buttons"]
    TAB5 --> BC["BeforeAfterBarChart GroupedBar"]
    TAB5 --> WF["PnLWaterfall horizontal per asset"]
```

---

### Backtest Engine — Sequence Diagram

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant BTE as BacktestEngine
    participant MET as MetricBundle
    participant OPT3 as PortfolioOptimizer

    API->>BTE: run(strategy_id=3, start, end, prices_df, events_df)
    BTE->>BTE: Filter events in [start, end]
    loop For each trading day t
        BTE->>BTE: Load events on day t (timestamp <= close)
        alt Strategy 0 Baseline
            BTE->>BTE: Equal-weight monthly rebalance
        else Strategy 1 Sentiment Only
            BTE->>OPT3: optimize(sentiment_signals, prev_w)
        else Strategy 2 Sent + Event
            BTE->>OPT3: optimize(sentiment+event_signals, prev_w)
        else Strategy 3 Full FinRisk AI
            BTE->>OPT3: optimize(all_signals + evidence_gate, prev_w)
        end
        OPT3-->>BTE: new_weights
        Note over BTE: T+1 execution apply weights at open(t+1)
        BTE->>BTE: Compute daily return Apply 5bps transaction cost
    end
    BTE->>MET: compute_metrics(returns_series)
    MET-->>BTE: sharpe, max_dd, volatility, cum_return, hit_rate
    BTE-->>API: BacktestResult strategy_0 to strategy_3
```

---

### Optimizer — Decision Flow

```mermaid
flowchart TD
    START(["PortfolioOptimizer.optimize() called"])

    START --> LOAD["Load signals dict ticker to actionability"]
    LOAD --> CHECK{"Evidence gate check per ticker"}

    CHECK -->|"evidence < 40 WATCH"| FREEZE["Freeze position w_i = w_prev_i log abstention"]
    CHECK -->|"evidence >= 40"| INCLUDE["Include in QP variable"]

    INCLUDE --> COV["Compute Sigma_LW Ledoit-Wolf fit on returns_matrix"]
    COV --> BUILD["Build CVXPY Problem Objective + Constraints"]
    BUILD --> CONS["Constraints: Sum(w)=1, w<=15%, Sector<=25%, Turnover<=10%"]
    CONS --> SOLVE{"Solve with Clarabel"}

    SOLVE -->|OPTIMAL| OUT["Return OptimizeResult weights + trades"]
    SOLVE -->|INFEASIBLE| FALL["Fallback to OSQP solver"]
    FALL --> OUT

    FREEZE --> OUT
    OUT --> TRADES["Build trade list ticker from to delta action"]
    TRADES --> END(["Return to API"])
```

---

### Evidence Gate — State Machine

```mermaid
stateDiagram-v2
    [*] --> INCOMING : RawEvent received
    INCOMING --> ENTITY_RESOLVE : EntityResolver maps to ticker
    ENTITY_RESOLVE --> DUPLICATE_CHECK : NoveltyDetector FAISS
    DUPLICATE_CHECK --> SUPPRESSED : cosine_sim >= 0.85 duplicate detected
    DUPLICATE_CHECK --> SCORE_SOURCES : cosine_sim < 0.85 novel event
    SUPPRESSED --> [*] : Event discarded cluster centroid updated
    SCORE_SOURCES --> COMPUTE_EVIDENCE : S_news S_sec S_social renormalized
    COMPUTE_EVIDENCE --> WATCH : score < 40 Abstain gate triggered
    COMPUTE_EVIDENCE --> DEVELOPING : 40 <= score < 70 Signal queued
    COMPUTE_EVIDENCE --> CONFIRMED : score >= 70 Full signal dispatched
    WATCH --> ABSTENTION_LOG : Record in Event Intelligence No portfolio change
    DEVELOPING --> IMPACT_SCORE : Feed to ImpactScorer SignalFuser Optimizer
    CONFIRMED --> IMPACT_SCORE
    CONFIRMED --> TOAST_ALERT : Fire React toast notification
    IMPACT_SCORE --> OPTIMIZER : ActionabilitySignal in [-1 +1]
    OPTIMIZER --> PORTFOLIO_UPDATE : New weights computed
    PORTFOLIO_UPDATE --> AUDIT_LOG : JSON trace generated
    AUDIT_LOG --> [*]
```

---

## Summary Tables

### HLD Layer Responsibilities

| Layer | Technology | Responsibility | Key SLA |
|:------|:-----------|:---------------|:--------|
| **L1 — Ingestion** | Python requests, CSV | GDELT + SEC EDGAR polling, local cache, retry | ~15 min freshness |
| **L2 — NLP** | PyTorch, FAISS, HuggingFace | Entity resolution, dedup, sentiment, classification, evidence gate | < 50ms per event |
| **L3 — Risk Engine** | CVXPY, NumPy, Scikit-Learn | Signal fusion, QP optimization, macro stress simulation | < 150ms per optimize |
| **L4 — API Gateway** | FastAPI, Uvicorn | Async REST, 60s result cache, LLM narrative endpoint | < 200ms p95 |
| **L5 — Dashboard** | React 18, Vite, Recharts | Live/Demo UI, 5 tabs, toast alerts, offline fallback | Instant (demo data) |

### LLD Key Design Decisions

| Component | Choice | Rationale |
|:----------|:-------|:----------|
| Embedding model | all-MiniLM-L6-v2 (384d) | 5x faster than FinBERT; sufficient for deduplication |
| Vector index | FAISS IndexFlatIP | Zero infrastructure dependency, sub-5ms local search |
| Covariance estimator | Ledoit-Wolf shrinkage | Numerically stable for N=15 stocks, T=504 days |
| QP solver | CVXPY + Clarabel to OSQP fallback | Constraint-first formulation, deterministic solve |
| Frontend state | React hooks only | Sufficient at this scale, zero added dependency |
| LLM integration | Gemini 1.5 Flash + deterministic fallback | Free tier; fallback ensures demo always works |
| Evidence gate threshold | 40 / 70 (Watch / Confirmed) | Calibrated to suppress ~60% of duplicate/unconfirmed noise |

---

*FinRisk AI — Built for the S&P Global & CRISIL Campus Hackathon 2026*
