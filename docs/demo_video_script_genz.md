# FinRisk AI 🧠 — 2.5-Minute Demo Video Script (Gen Z Edition 🔥)
**S&P Global & CRISIL Campus Hackathon 2026**  
**Candidate:** Safal Singh | **College:** NIT Kurukshetra  
**Deliverable 3 (YouTube Link):** [https://youtu.be/su26HGmlV_g](https://youtu.be/su26HGmlV_g)  
**Deliverable 2 (Presentation Deck):** [OneDrive Link](https://1drv.ms/b/c/b54c5000cff07bc3/IQC2AS5GHLeqQ7EjYoY1C0dvAVKEZgUIHLeelGEkyIXgZ1o?e=Loekbo) | [docs/presentation.pdf](presentation.pdf)

---

## ⏱️ Exact 2.5-Minute Timing Grid

| Timestamp | Duration | Section | On-Screen Visual Focus |
|---|---|---|---|
| `0:00 – 0:18` | **18s** | **Intro: The Problem & The Flex** | GitHub README header → Dashboard Hero header |
| `0:18 – 0:35` | **17s** | **Setup: Running from README** | Terminal (`pytest` 34/34 green → FastAPI & Vite live) |
| `0:35 – 0:50` | **15s** | **Step 1: Market Radar** | `/radar` 15-stock universe & live streaming ticker |
| `0:50 – 1:10` | **20s** | **Step 2: Event Intel & Abstention** | `/events` FinBERT + FAISS dedup + Evidence Gate `< 40` |
| `1:10 – 1:30` | **20s** | **Step 3: Event Replay Lore** | `/replay` NVDA 3-step: Rumor → Corroboration → SEC 8-K |
| `1:30 – 1:52` | **22s** | **Step 4: CVXPY Rebalance & Audit** | `/portfolio` Click "Rebalance Now", 10% cap, Audit JSON |
| `1:52 – 2:08` | **16s** | **Step 5: Macro Stress Test** | `/stress-test` 2008 Lehman / Tech Crash shock simulation |
| `2:08 – 2:30` | **22s** | **Receipts & Closing Impact** | Benchmark stats (+14.2% Sharpe, 0 bad trades) & sign-off |

---

## 🎬 Pre-Recording Checklist
- [ ] Screen resolution: **1080p (1920x1080)**.
- [ ] Browser open at `http://localhost:5173/` on **Dark Theme** in **LIVE** mode.
- [ ] Split screen or fast alt-tab to Terminal with test run pre-loaded.
- [ ] Tone: High energy, confident, fast, clear, zero fluff.

---

## 🎙️ Word-for-Word Narration Script (150 Seconds Flat)

---

### 1. Intro: The Problem & The Flex (`0:00 – 0:18` | 18s)
**Visual:** Show GitHub repo, then cut straight into the sleek FinRisk AI dashboard at `http://localhost:5173/`.

> **Voiceover (Safal Singh):**  
> *"What's good S&P Global and CRISIL jury! I'm Safal Singh from NIT Kurukshetra, and this is **FinRisk AI**—an autonomous, event-driven risk engine that turns live financial news into risk-bounded portfolio execution.  
> 
> Backward-looking covariance misses sudden shocks, while naive NLP gets totally ratio'd by recycled rumors. FinRisk AI brings institutional rigor with zero cap. Let's run it!"*

---

### 2. Setup: Running from README (`0:18 – 0:35` | 17s)
**Visual:** Switch to Terminal. Show `pytest tests/` passing 34/34 tests, then the running backend and frontend logs.

> **Voiceover:**  
> *"Setup is 100% reproducible—zero paid API keys required.  
> 
> In the terminal: running `pytest`—all 34 unit and integration tests pass cleanly in 16 seconds.  
> 
> One command spins up our FastAPI backend loading 504 days of historical data, and `npm run dev` launches our Vite frontend. Everything is self-contained and ready to ship out of the box."*

---

### 3. Step 1: Live Market Radar (`0:35 – 0:50` | 15s)
**Visual:** Switch to browser. Open `/radar`. Show the 15-stock universe cards (NVDA, AAPL, MSFT, etc.) updating live.

> **Voiceover:**  
> *"Here's our **Market Radar**, monitoring a 15-asset mega-cap portfolio in real time.  
> 
> In live streaming mode, updates ingest every 1.5 seconds. For each stock, the system tracks real-time sentiment, market beta, and composite risk index without lagging the UI."*

---

### 4. Step 2: Event Intel & Abstention Gate (`0:50 – 1:10` | 20s)
**Visual:** Click `/events`. Highlight an unverified rumor showing **ABSTAIN / HALT**, then contrast with a verified SEC 8-K event.

> **Voiceover:**  
> *"Next, **Event Intelligence**. When breaking news hits, FinBERT embeds the text, and FAISS vector deduplication filters out 30 reposted copies of the same story.  
> 
> Most importantly: when the **Evidence Score** falls below 40, the system hits the brakes and **ABSTAINS**. It refuses to trade on unverified vibes, saving capital from false breakout traps."*

---

### 5. Step 3: Event Replay Lore (`1:10 – 1:30` | 20s)
**Visual:** Click `/replay`. Drag through the 3-step benchmark: `NVDA — Blackwell Supply Delay`.

> **Voiceover:**  
> *"In **Event Replay**, we reconstruct the exact timeline from initial rumor to execution.  
> 
> Watch this NVDA Blackwell case study:  
> At 10:05 AM, an unverified social rumor drops—evidence is only 22/100, so the AI abstains.  
> At 10:18 AM, Bloomberg confirms—evidence hits 61.  
> At 10:37 AM, Nvidia files an official SEC 8-K—evidence surges to 91, instantly triggering a risk-reducing sell before the market dumps."*

---

### 6. Step 4: CVXPY Rebalancing & Audit Trail (`1:30 – 1:52` | 22s)
**Visual:** Click `/portfolio`. Click **Rebalance Now**. Show weights shifting, the 10% turnover bar, and open the Audit JSON preview.

> **Voiceover:**  
> *"Over in the **Portfolio Rebalancer**, when verified alpha triggers an adjustment, our CVXPY convex optimizer recalibrates asset weights.  
> 
> It strictly enforces a 10% turnover budget, preventing portfolio churn. And every single trade decision exports an immutable compliance JSON detailing exact mathematically provable rationale for risk auditors."*

---

### 7. Step 5: Macro Stress Testing (`1:52 – 2:08` | 16s)
**Visual:** Click `/stress-test`. Select "2008 GFC" or "Tech Crash" and watch the correlation matrix and VaR recalculate instantly.

> **Voiceover:**  
> *"In the **Stress Test Studio**, risk managers can subject the active book to historical macro shocks like 2008 Lehman or a Tech Drawdown.  
> 
> The engine warps the covariance matrix and recalculates conditional VaR in under 50 milliseconds, giving PMs instant scenario visibility."*

---

### 8. Results & Institutional Impact (`2:08 – 2:30` | 22s)
**Visual:** Scroll through backtest performance metrics or show the presentation deck summary slide.

> **Voiceover:**  
> *"Let's talk receipts: across 504 market sessions, FinRisk AI delivered a **+14.2% higher Sharpe ratio**, cut maximum drawdown by **3.8%**, and recorded **zero uncorroborated panic trades**.  
> 
> Full source code, test suites, and slides are live in the GitHub repo. Thanks for tuning in, S&P Global and CRISIL team—let's build the future of risk!"*

---

## 📊 Summary of 2.5-Minute Script Specs
- **Total Spoken Words:** ~365 words
- **Speaking Speed:** 146 words per minute (confident, energetic, perfectly natural for Gen Z demos)
- **Total Duration:** 150 seconds (2 mins 30 secs)
- **Checklist Compliance:** 
  - Problem & Solution: ✅ 18s
  - Setup & Run from README: ✅ 17s
  - End-to-End Walkthrough: ✅ 93s (Radar 15s + Events 20s + Replay 20s + Rebalancer 22s + Stress Test 16s)
  - Results & Impact: ✅ 22s

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
0:18 - Setup & Quickstart (pytest 34/34 passing)
0:35 - E2E Walkthrough: Live Market Radar
0:50 - E2E Walkthrough: Event Intelligence & Evidence Abstention Gate
1:10 - E2E Walkthrough: Event Replay (NVDA Blackwell 3-Step Lore)
1:30 - E2E Walkthrough: Tactical CVXPY Rebalancing & Audit JSON
1:52 - E2E Walkthrough: Macro Stress Testing
2:08 - Empirical Results (+14.2% Sharpe) & Institutional Impact
```

### Settings:
- Visibility: **Unlisted** (Publicly accessible via direct URL)
- Category: **Science & Technology** or **Education**
