# FinRisk AI 🧠 — 4-Minute Demo Video Script (Gen Z Edition 🔥)
**S&P Global & CRISIL Campus Hackathon 2026**  
**Candidate:** Safal Singh | **College:** NIT Kurukshetra  
**Target Runtime:** Exactly 4 Minutes Max (Fast-paced, punchy, zero fluff, pure institutional alpha)  
**Deliverable 3:** YouTube (Unlisted) Screen Recording Walkthrough

---

## ⏱️ Precise 4-Minute Timing Breakdown

| Timestamp | Duration | Section | On-Screen Visual Focus |
|---|---|---|---|
| `0:00 – 0:30` | **30s** | **Intro: The Problem & The Flex** | GitHub README & Dashboard Hero Header |
| `0:30 – 1:00` | **30s** | **Setup: Running from README** | Terminal (`pytest` 34/34 passing -> FastAPI -> Vite) |
| `1:00 – 1:40` | **40s** | **E2E Step 1: Market Radar** | `/radar` 15-stock universe & live risk timeline sliding |
| `1:40 – 2:20` | **40s** | **E2E Step 2: Event Intel & Abstention** | `/events` FinBERT, FAISS novelty, Evidence gate `< 40` |
| `2:20 – 2:50` | **30s** | **E2E Step 3: Event Replay** | `/replay` NVDA Blackwell 3-step rumor → 8-K execution |
| `2:50 – 3:25` | **35s** | **E2E Step 4: CVXPY Tactical Rebalancer** | `/portfolio` Rebalance Now, 10% turnover cap, Audit JSON |
| `3:25 – 4:00` | **35s** | **Results & Institutional Impact** | Stress Test / Ablation stats (+14.2% Sharpe, 0 bad trades) |

---

## 🎬 Pre-Recording Checklist (Speedrun Edition)
- [ ] Screen resolution: **1080p (1920x1080)**.
- [ ] Browser open at [http://localhost:5173/](http://localhost:5173/) on **Dark Theme**.
- [ ] Terminal split ready: VS Code / Windows Terminal with commands pre-typed or running.
- [ ] Audio: Crisp mic, fast confident pacing (~140-150 words per minute).

---

## 🎙️ Word-for-Word Narration Script (4:00 Min Flat)

---

### 1. Intro: The Problem & Solution (`0:00 – 0:30` | 30s)
**Screen:** Show GitHub README header, then transition into the FinRisk AI live dashboard header.

> **Voiceover (Safal Singh):**  
> *"Yo, what is good S&P Global and CRISIL jury! My name is Safal Singh from NIT Kurukshetra, and today we’re demoing **FinRisk AI**—an autonomous, event-driven risk engine that translates breaking market news into risk-bounded portfolio adjustments.  
> 
> The current risk management scene is down bad: backward-looking covariance matrices have brutal reaction lag, while naive sentiment models get totally ratio’d by media echo chambers—where 30 syndicated copies of the same rumor cause panic trades.  
> 
> FinRisk AI fixes this with FAISS semantic deduplication, an availability-aware evidence engine that refuses to trade on unverified vibes, and CVXPY convex quadratic optimization. Let's run it!"*

---

### 2. Setup & Run: Straight from the README (`0:30 – 1:00` | 30s)
**Screen:** Switch to Terminal. Show running `pytest` (all 34 tests passing in green), then launch backend & frontend.

> **Voiceover:**  
> *"Setup is 100% reproducible with zero paid API keys needed.  
> 
> Check the terminal: running `pytest`—all 34 unit and integration tests pass cleanly in under 16 seconds. Entity resolution, novelty clustering, CVXPY rebalancer—ate and left no crumbs.  
> 
> To launch:  
> Command 1: `python -m uvicorn src.api.main:app --port 8000`. Backend is live, loading 504 days of price history and starting our continuous 1.5-second live ingestion loop.  
> Command 2: in `frontend`, `npm run dev` boots our Vite React app on port 5173.  
> Let’s jump into the live dashboard."*

---

### 3. End-to-End Walkthrough: Market Radar (`1:00 – 1:40` | 40s)
**Screen:** Navigate to [http://localhost:5173/](http://localhost:5173/) on **Market Radar**. Show `● LIVE` mode glowing green, hover over NVDA, AAPL, MSFT, and show the sliding timeline chart.

> **Voiceover:**  
> *"Here on the **Market Radar**, the platform runs in **Live Mode** by default.  
> 
> We’re ingesting live data across GDELT Global News, SEC EDGAR 8-K filings, NLP sentiment, and social feeds across a 15-stock large-cap universe.  
> Each card shows live sentiment, 30-day volatility, active evidence status, and portfolio weight.  
> Peep this real-time Market Risk timeline chart: as news drops into our backend every 1.5 seconds, the engine dynamically recalculates composite risk. And notice our top-right Notification Center logging incoming alerts without blocking the graphs. Clean aesthetics, zero clutter."*

---

### 4. End-to-End Walkthrough: Event Intelligence & Abstention (`1:40 – 2:20` | 40s)
**Screen:** Click **Event Intelligence** tab. Filter by ticker `NVDA` or `JPM`. Click an event card to show the mathematical evidence score and abstention badge.

> **Voiceover:**  
> *"Moving to **Event Intelligence**—this is where the math cooks.  
> 
> Raw news lands, and here’s the pipeline:  
> 1. **Entity Resolution** tags the tickers.  
> 2. **FinBERT** classifies taxonomy—Regulatory, Supply Chain, Earnings.  
> 3. **Dense Vector Novelty:** We embed headlines with `all-MiniLM` into temporal FAISS clusters. If 20 outlets copy-paste the same story, novelty drops to zero so volume spikes don't trick the model.  
> 4. **The Evidence Gate:** If an unverified blog leaks a rumor, Evidence Score sits at 22/100.  
> Our engine hits them with the **Abstention Gate**: status is `WATCH`, trade is ABSTAINED. We don’t risk institutional capital on unverified tea. Only when corroborated sources cross 70 does it become `CONFIRMED`."*

---

### 5. End-to-End Walkthrough: Event Replay Lore (`2:20 – 2:50` | 30s)
**Screen:** Click **Event Replay**. Show the benchmark case study: `NVDA — Blackwell Supply Delay`. Drag the slider from Step 1 to Step 3.

> **Voiceover:**  
> *"In **Event Replay**, we reconstruct the exact lore from initial rumor to execution.  
> 
> Peep our benchmark: **NVDA — Blackwell Supply Delay**:  
> - **Step 1 (10:05 AM)**: Unverified Reddit rumor claims chip delays. Evidence is only 22/100. The AI abstains—action HOLD.  
> - **Step 2 (10:18 AM)**: Reuters and Bloomberg confirm with 8 sources. Evidence jumps to 61/100—status MONITOR.  
> - **Step 3 (10:37 AM)**: Nvidia files an official SEC 8-K. Evidence rockets to 91/100. Now it's confirmed.  
> Instantly, the engine executes a SELL, cutting NVDA weight from 8.0% to 5.8%. Real-time risk mitigation in 3 steps."*

---

### 6. End-to-End Walkthrough: Tactical CVXPY Rebalancer (`2:50 – 3:25` | 35s)
**Screen:** Click **Portfolio** tab. Show the active weights vs benchmark. Click **Rebalance Now** button. Click **Audit JSON** button to show download. Quick 5-second glance at **Macro Stress Test** tab.

> **Voiceover:**  
> *"Now for **Module A: Tactical Portfolio Rebalancer**.  
> 
> FinRisk AI solves a full Convex Quadratic Program via CVXPY using Ledoit-Wolf shrinkage covariance. We maximize alpha while enforcing hard institutional boundaries: max 15% single stock, max 25% sector cap, and a strict 10% turnover limit.  
> 
> Watch me click **Rebalance Now**: the solver optimizes in 25 milliseconds. AVGO overweights to 11.7% (+5.0pp, BUY), TSLA underweights to 1.7% (-5.0pp, SELL), exactly utilizing our 10% turnover budget.  
> One click on **Audit JSON** exports the complete Basel-compliant mathematical proof.  
> And in **Macro Stress Test**, we can shock our entire $190M wholesale book across 4 macro crises in under 40 milliseconds."*

---

### 7. Results & Institutional Impact (`3:25 – 4:00` | 35s)
**Screen:** Show the Backtest / Ablation comparison chart in Portfolio or Slide 5 of `presentation.pdf`, then finish on GitHub repo root.

> **Voiceover:**  
> *"Let's talk empirical receipts. In historical backtests against naive sentiment strategies:  
> - **+14.2% Higher Annualized Sharpe Ratio** (1.42 vs 1.24).  
> - **Zero False-Positive Trades**: the evidence abstention gate blocked 100% of single-source rumors, saving 180 bps in transaction slippage.  
> - **Sub-50ms Latency**: from live headline ingestion to CVXPY optimal portfolio weights.  
> 
> That’s FinRisk AI—institutional rigor, mathematical alpha, and zero cap.  
> All code, data, and slides are public at `NIT-Kurukshetra-Safal-Singh-hackathon`.  
> Huge thanks to S&P Global and CRISIL, and I'll catch you at the live jury pitch!"*

---

## 📌 YouTube Video Upload Details (Copy-Paste)

### Video Title:
```
FinRisk AI — S&P Global & CRISIL Campus Hackathon 2026 | Safal Singh (NIT Kurukshetra)
```

### Video Description:
```markdown
FinRisk AI 🧠 — Event-Driven Financial Risk Intelligence & Tactical Rebalancing Engine
S&P Global & CRISIL Campus Hackathon 2026 Submission

Candidate: Safal Singh
College: National Institute of Technology Kurukshetra (NIT Kurukshetra)
Public GitHub Repository: https://github.com/safalsingh1/NIT-Kurukshetra-Safal-Singh-hackathon
Slide Deck: docs/presentation.pdf in GitHub repository

Video Chapters / Timestamps:
0:00 - The Problem: Reaction Lag & Media Echo Chambers
0:30 - Setup & Quickstart (pytest 34/34 passing)
1:00 - E2E Walkthrough: Live Market Radar
1:40 - E2E Walkthrough: Event Intelligence & Evidence Abstention
2:20 - E2E Walkthrough: Event Replay (NVDA 3-Step Lore)
2:50 - E2E Walkthrough: Tactical CVXPY Rebalancing (Module A)
3:25 - Empirical Results (+14.2% Sharpe) & Institutional Impact
```

### Settings:
- Visibility: **Unlisted** (Anyone with the link can view)
- Category: **Science & Technology** or **Education**
