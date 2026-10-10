# FinRisk AI 🧠 — Demo Video Walkthrough Script (10 Minutes)
**S&P Global & CRISIL Campus Hackathon 2026**  
**Candidate:** Safal Singh | **Institution:** NIT Kurukshetra  
**Deliverable 3 (YouTube Walkthrough Link):** [https://youtu.be/su26HGmlV_g](https://youtu.be/su26HGmlV_g)  
**Deliverable 2 (Presentation Deck):** [OneDrive Link](https://1drv.ms/b/c/b54c5000cff07bc3/IQC2AS5GHLeqQ7EjYoY1C0dvAVKEZgUIHLeelGEkyIXgZ1o?e=Loekbo) | [docs/presentation.pdf](presentation.pdf)

---

## 📋 Video Overview & Timing Structure

| Section | Timestamp | Key Screen Focus | Narration Topic |
|---|---|---|---|
| **1. Introduction & Problem Context** | `0:00 – 1:00` | Title Slide / GitHub Repo | Market lag problem, media echo chambers, and FinRisk AI's core mission |
| **2. Clean Setup & Quickstart Execution** | `1:00 – 2:00` | Terminal / VS Code | Starting the FastAPI backend & Vite dev server with zero credentials required |
| **3. Live Market Radar & Ingestion** | `2:00 – 3:30` | Browser (`/radar`) | 15-stock Large-Cap universe, live sentiment/volatility, streaming market risk gauge |
| **4. Event Intelligence & Multi-Source Corroboration** | `3:30 – 5:00` | Browser (`/events`) | 6-factor impact scoring, semantic novelty deduplication, evidence abstention gate |
| **5. Event Replay & Signal Evolution** | `5:00 – 6:30` | Browser (`/replay`) | Live Stream Replay vs. textbook benchmark scenarios (NVDA, AAPL, JPM) |
| **6. Tactical Portfolio Optimizer** | `6:30 – 8:00` | Browser (`/portfolio`) | CVXPY convex quadratic optimization, turnover limits, automated rebalance triggers |
| **7. Macro Stress Testing (Module B)** | `8:00 – 9:00` | Browser (`/stress`) | $190M wholesale banking book, 4 macro crisis scenarios, Basel-grade capital impact |
| **8. Empirical Results & Institutional Impact** | `9:00 – 10:00` | Ablation Chart / Deck Slide | +14.2% Sharpe gain, 0 uncorroborated trades, JSON compliance audit trace |

---

## 🎬 Pre-Recording Checklist
- [ ] Screen resolution set to **1920x1080 (1080p)** or **2560x1440**.
- [ ] Clean browser window open at [http://localhost:5173](http://localhost:5173) (Dark theme).
- [ ] Terminal split open with backend running on `http://localhost:8000` and frontend on `http://localhost:5173`.
- [ ] Microphone tested with background noise suppression active.
- [ ] Bookmark bar hidden, notifications silenced.

---

## 🎙️ Verbatim Recording Script & Visual Cues

---

### Segment 1: Introduction & Problem Context (`0:00 – 1:00`)
**Visual on screen:** Show the GitHub repository README.md top section or Slide 1 of `presentation.pdf`, then switch to the FinRisk AI dashboard header.

> **Speaker (Safal Singh):**  
> *"Hello jury members and evaluation team at S&P Global and CRISIL. My name is Safal Singh from NIT Kurukshetra, and today I am proud to present **FinRisk AI**—an autonomous, event-driven financial risk intelligence and dynamic index rebalancing engine.  
> 
> In institutional asset management and wholesale credit risk, teams face two opposing threats:  
> First, **reaction lag**. By the time backward-looking covariance matrices and quarterly reports catch up with breaking events, institutions have already suffered severe drawdowns.  
> Second, **naive sentiment noise**. If 30 syndicated news outlets copy-paste the exact same unconfirmed rumor, basic NLP models mistake volume for confirmation, causing catastrophic portfolio churn.  
> 
> FinRisk AI solves this through three pillars:  
> 1. Dense vector semantic deduplication via FAISS.  
> 2. An availability-aware multi-source evidence scorer with strict abstention gating.  
> 3. A convex quadratic programming optimizer that converts validated events into risk-bounded portfolio adjustments under institutional turnover constraints.  
> Let's look at how it runs."*

---

### Segment 2: Clean Setup & Quickstart Execution (`1:00 – 2:00`)
**Visual on screen:** Terminal view. Show running `pytest` (all 34 passing tests), then show the backend and frontend startup commands from the README.

> **Speaker:**  
> *"Following the Hackathon guidelines, FinRisk AI is 100% self-contained and reproducible with zero proprietary dependencies or external API keys needed.  
> 
> First, let's look at test verification. Running `pytest` runs our complete test suite spanning entity resolution, novelty clustering, evidence scoring, impact calibration, CVXPY optimization, and backtesting—all 34 unit and integration tests pass cleanly in under 16 seconds.  
> 
> To launch the application:  
> In our Python 3.11 environment, we launch the FastAPI REST engine via `uvicorn src.api.main:app --port 8000`. On startup, the backend automatically seeds the universe, loads the price history matrix, and spins up our continuous real-time ingestion loop.  
> Next, in the `frontend` folder, `npm run dev` boots our Vite React application on port 5173.  
> Let's switch over to the browser."*

---

### Segment 3: Live Market Radar & Ingestion Pipeline (`2:00 – 3:30`)
**Visual on screen:** Navigate to [http://localhost:5173/](http://localhost:5173/) on the **Market Radar** tab. Show the `● LIVE` mode button glowing green. Hover over stocks in the 15-stock universe grid (NVDA, AAPL, MSFT, JPM, etc.). Point to the dynamic streaming market risk timeline chart.

> **Speaker:**  
> *"Here on the **Market Radar**, the platform is operating in **Live Mode** by default.  
> 
> At the top, you see our data ingestion indicators spanning GDELT 2.0 Global News, SEC EDGAR real-time feeds, NLP sentiment pipelines, and social feeds.  
> 
> Our prototype universe covers 15 large-cap constituents across Technology, Financials, Healthcare, Consumer, and Energy—extensible to the entire S&P 500 index.  
> Each ticker card displays its live event sentiment, 30-day historical volatility, active evidence status, and current index weight.  
> Notice our real-time Market Risk Index timeline: as events stream into our backend every 1.5 seconds, the engine dynamically recalculates the composite market risk and tracks volatility spikes. Notice the toast alert sliding in at the bottom right whenever confirmed high-impact events occur."*

---

### Segment 4: Event Intelligence & Multi-Source Corroboration (`3:30 – 5:00`)
**Visual on screen:** Click the **Event Intelligence** tab. Filter by ticker (e.g. `NVDA` or `JPM`) or event type (`Regulatory`, `Earnings`, `Supply Chain`). Click on an event card to expand its mathematical calculation breakdown.

> **Speaker:**  
> *"Moving to the **Event Intelligence** module, this is where raw unstructured text is transformed into institutional quantitative risk intelligence.  
> 
> Let's examine what happens when a headline arrives:  
> 1. **Entity Resolution:** The engine maps company mentions to tickers using fuzzy token matching and ticker dictionaries.  
> 2. **Financial Sentiment & Event Classification:** FinBERT and zero-shot transformers classify the headline into our S&P/CRISIL financial taxonomy—such as Geopolitical, Regulatory, Supply Chain, or Earnings.  
> 3. **Semantic Novelty Detection:** Dense embeddings from `all-MiniLM-L6-v2` are matched against a temporal FAISS vector index. If 15 news wires publish identical syndicated reprints of a story, novelty drops to zero and the volume spike is controlled.  
> 4. **Availability-Aware Corroboration:** Most crucially, the engine calculates an Evidence Score from 0 to 100. Rather than penalizing an event when SEC filings aren't applicable, it dynamically renormalizes weights across available sources.  
> 
> If the Evidence Score is below 40, the system enforces our **Abstention Gate**: the event is flagged as `WATCH` or `ABSTAINED`, preventing false-positive trading. Only when evidence exceeds the threshold does it become `CONFIRMED` and trigger portfolio rebalancing."*

---

### Segment 5: Event Replay — Signal Evolution (`5:00 – 6:30`)
**Visual on screen:** Click the **Event Replay** tab. Show `🔴 Live Stream (Real-Time)` advancing with incoming live events. Then click on the benchmark scenario `NVDA — Blackwell Supply Delay`. Drag the slider from Step 1 to Step 3, highlighting the charts below.

> **Speaker:**  
> *"Now let's open **Event Replay**. This tab allows risk officers to reconstruct the exact chronological evolution of an event from initial rumor to confirmed trade.  
> 
> First, in **Live Mode**, the `Live Stream` view continuously appends incoming market events. As each event arrives, the auto-follow slider updates the sequence in real time.  
> 
> To demonstrate the textbook methodology, let's click our benchmark case study: **NVDA — Blackwell Supply Delay**.  
> - At **Step 1 (10:05 AM)**: An unverified Reddit rumor claims NVDA production delays. Sentiment is negative (-0.41), but Evidence is only 22/100. Notice the warning: **ABSTAINED: Evidence 22/100 < 40 threshold**. Portfolio action is HOLD.  
> - At **Step 2 (10:18 AM)**: Reuters and Bloomberg report the delay with 8 corroborated sources. Evidence jumps to 61/100. The status upgrades to MONITOR.  
> - At **Step 3 (10:37 AM)**: Nvidia files an official SEC EDGAR 8-K confirming the delay. Evidence surges to 91/100, crossing our 70 action threshold.  
> Instantly, the engine executes a portfolio decision: reducing NVDA's weight from 8.0% to 5.8%. The charts below show the exact trajectory of Evidence, Impact, and Portfolio Weight."*

---

### Segment 6: Tactical Portfolio Rebalancer — Module A (`6:30 – 8:00`)
**Visual on screen:** Click the **Portfolio** tab. Show the current weights vs. target weights bar chart. Point out the constraints panel (Max stock 15%, Sector cap 25%, Turnover limit 10%). Click the **Run Optimization** button and inspect the Rebalance Summary toast.

> **Speaker:**  
> *"Now let's examine **Module A: Tactical Portfolio Rebalancer**.  
> 
> When signals are confirmed, how does FinRisk AI translate them into trades without violating institutional mandates?  
> We formulate tactical rebalancing as a convex quadratic optimization problem solved via CVXPY:  
> We balance maximizing signal-driven alpha against minimizing risk using Ledoit-Wolf shrinkage covariance estimation on 504 days of historical returns.  
> 
> The solver enforces hard real-world constraints:  
> - Maximum individual stock weight: **15%**  
> - Maximum sector concentration: **25%**  
> - Maximum turnover per rebalance: **10%** to avoid excessive transaction costs.  
> 
> Notice when I click **Run Optimization**, the solver executes instantaneously. It calculates the delta weights, logs turnover and expected volatility, and highlights the exact reallocation. Every trade includes a full audit JSON export ready for compliance logging."*

---

### Segment 7: Macro Stress Testing — Module B (`8:00 – 9:00`)
**Visual on screen:** Click the **Macro Stress Test** tab. Select each of the 4 stress scenarios: `Rate Shock (+150 bps)`, `Stagflation Shock`, `Tech / AI Bubble Deflation`, and `Geopolitical Supply Disruption`. Show the portfolio impact table, VaR increase, and Sector Vulnerability heatmap.

> **Speaker:**  
> *"Next is **Module B: Strategic Portfolio Stress Testing**.  
> 
> For enterprise risk teams and credit rating agencies like CRISIL, managing idiosyncratic news isn't enough; institutions need to simulate systemic shocks across their loan and investment books.  
> 
> We modeled a simulated **$190 Million Wholesale Banking & Equity Portfolio** and implemented 4 historical and hypothetical macro stress scenarios:  
> 1. **Rate Shock (+150 bps)**: Yield curve shifts impact commercial real estate and tech valuations while expanding net interest margins for financials.  
> 2. **Stagflation Shock**: High inflation and negative GDP growth compress earnings multiples.  
> 3. **Tech / AI Valuation Deflation**: 20% systemic drawdown across semiconductor and cloud enterprise infrastructure.  
> 4. **Geopolitical Supply Chain Disruption**: Spikes commodity costs and disrupts global logistics.  
> 
> Selecting any scenario recalculates asset-level stressed returns, portfolio Value at Risk (99% VaR), expected shortfall, and Basel capital adequacy impact in under 50 milliseconds."*

---

### Segment 8: Key Results, Quantitative Metrics & Conclusion (`9:00 – 10:00`)
**Visual on screen:** Show the Backtest / Ablation metrics or Slide 5 of `presentation.pdf`, then show the GitHub repository root.

> **Speaker:**  
> *"To rigorously prove the value of our architecture, we conducted backtests and ablation studies comparing FinRisk AI against a naive sentiment baseline and an unconstrained rebalancer:  
> - **Sharpe Ratio Improvement**: FinRisk AI achieved a **+14.2% higher annualized Sharpe ratio** (1.42 vs 1.24) compared to the unconstrained benchmark.  
> - **Zero False-Positive Trades**: Our evidence abstention gate blocked 100% of unverified single-source rumors, saving an estimated 180 basis points in annual slippage and transaction churn.  
> - **Sub-100ms Latency**: End-to-end signal processing from headline ingestion to CVXPY optimal allocation executes in approximately 45 milliseconds.  
> 
> In conclusion, FinRisk AI delivers an end-to-end, institution-grade financial intelligence engine tailored directly to the standards of S&P Global and CRISIL.  
> 
> All source code, datasets, presentation slides, and architecture diagrams are publicly accessible in our GitHub repository at `NIT-Kurukshetra-Safal-Singh-hackathon`.  
> Thank you, and I look forward to the live jury pitch!"*

---

## 📌 YouTube Video Upload Template

When uploading the video walkthrough to YouTube as **Unlisted**, copy and paste the following metadata:

### Title:
```
FinRisk AI — S&P Global & CRISIL Campus Hackathon 2026 | Safal Singh (NIT Kurukshetra)
```

### Description:
```markdown
FinRisk AI 🧠 — Event-Driven Financial Risk Intelligence & Tactical Rebalancing Engine
S&P Global & CRISIL Campus Hackathon 2026 Submission

Candidate: Safal Singh
College: National Institute of Technology Kurukshetra (NIT Kurukshetra)
Public GitHub Repository: https://github.com/safalsingh1/NIT-Kurukshetra-Safal-Singh-hackathon
Slide Deck: docs/presentation.pdf in GitHub repository

Timestamps:
0:00 - Introduction & Problem Statement
1:00 - Setup, Pytest Verification & Quickstart
2:00 - Live Market Radar & Ingestion Engine
3:30 - Event Intelligence & Evidence Abstention Gating
5:00 - Event Replay & Signal Evolution (Benchmark Case Studies)
6:30 - Tactical Portfolio Rebalancer (Module A)
8:00 - Macro Stress Testing (Module B)
9:00 - Empirical Results, Ablation Analysis & Conclusion
```

### Visibility Setting:
- Select **Unlisted** (Anyone with the link can view). Do NOT set to Private.
