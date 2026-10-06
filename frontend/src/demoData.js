// src/demoData.js — self-contained demo data for offline mode
export const UNIVERSE = [
  { ticker:'AAPL',  company:'Apple Inc.',              sector:'Technology',            actionability: 0.42, impact: 6.8, evidence: 78 },
  { ticker:'MSFT',  company:'Microsoft Corporation',   sector:'Technology',            actionability: 0.31, impact: 5.9, evidence: 65 },
  { ticker:'NVDA',  company:'NVIDIA Corporation',      sector:'Semiconductors',        actionability: 0.77, impact: 8.4, evidence: 91 },
  { ticker:'AMZN',  company:'Amazon.com Inc.',         sector:'Consumer Discretionary',actionability:-0.22, impact: 5.1, evidence: 54 },
  { ticker:'GOOGL', company:'Alphabet Inc.',           sector:'Technology',            actionability: 0.18, impact: 4.7, evidence: 48 },
  { ticker:'META',  company:'Meta Platforms Inc.',     sector:'Technology',            actionability: 0.55, impact: 7.2, evidence: 82 },
  { ticker:'TSLA',  company:'Tesla Inc.',              sector:'Consumer Discretionary',actionability:-0.61, impact: 7.9, evidence: 87 },
  { ticker:'JPM',   company:'JPMorgan Chase & Co.',   sector:'Financials',            actionability:-0.38, impact: 6.5, evidence: 73 },
  { ticker:'BAC',   company:'Bank of America Corp.',  sector:'Financials',            actionability:-0.12, impact: 3.9, evidence: 31 },
  { ticker:'XOM',   company:'Exxon Mobil Corporation',sector:'Energy',                actionability: 0.09, impact: 3.2, evidence: 28 },
  { ticker:'JNJ',   company:'Johnson & Johnson',      sector:'Healthcare',            actionability: 0.05, impact: 2.8, evidence: 22 },
  { ticker:'WMT',   company:'Walmart Inc.',           sector:'Consumer Staples',      actionability: 0.23, impact: 4.4, evidence: 55 },
  { ticker:'V',     company:'Visa Inc.',              sector:'Financials',            actionability: 0.15, impact: 3.7, evidence: 42 },
  { ticker:'AVGO',  company:'Broadcom Inc.',          sector:'Semiconductors',        actionability: 0.62, impact: 7.5, evidence: 84 },
  { ticker:'COST',  company:'Costco Wholesale',       sector:'Consumer Staples',      actionability: 0.11, impact: 3.1, evidence: 39 },
];

export const DEMO_EVENTS = [
  { id:'e1', ticker:'NVDA', headline:'NVDA files 8-K: Blackwell ramp accelerated, Q3 guidance raised significantly',
    event_type:'Supply Chain', sentiment:0.83, confidence:0.94, novelty:0.91, spike:9.2,
    evidence:91, status:'CONFIRMED', action:'BUY', impact:8.4, abstained:false, ts:'10:37' },
  { id:'e2', ticker:'TSLA', headline:'NHTSA expands recall investigation to 480,000 Tesla vehicles over autopilot failures',
    event_type:'Regulatory', sentiment:-0.78, confidence:0.91, novelty:0.87, spike:7.4,
    evidence:87, status:'CONFIRMED', action:'SELL', impact:7.9, abstained:false, ts:'09:12' },
  { id:'e3', ticker:'META', headline:'Meta reports Q3 EPS $5.16 vs $4.82 est; AI engagement metrics beat on all verticals',
    event_type:'Earnings', sentiment:0.81, confidence:0.96, novelty:0.45, spike:11.3,
    evidence:96, status:'CONFIRMED', action:'BUY', impact:9.1, abstained:false, ts:'16:30' },
  { id:'e4', ticker:'JPM', headline:'OCC issues formal consent order against JPMorgan Chase over risk management lapses',
    event_type:'Regulatory', sentiment:-0.72, confidence:0.89, novelty:0.81, spike:8.7,
    evidence:73, status:'CONFIRMED', action:'SELL', impact:6.5, abstained:false, ts:'15:10' },
  { id:'e5', ticker:'AVGO', headline:'Broadcom announces $12B AI networking partnership with three hyperscalers',
    event_type:'Product/Partnership', sentiment:0.76, confidence:0.88, novelty:0.92, spike:6.8,
    evidence:84, status:'CONFIRMED', action:'BUY', impact:7.5, abstained:false, ts:'11:22' },
  { id:'e6', ticker:'AAPL', headline:'Apple supplier Foxconn reports 18% YoY increase in iPhone 16 production volume',
    event_type:'Supply Chain', sentiment:0.61, confidence:0.82, novelty:0.74, spike:5.1,
    evidence:78, status:'CONFIRMED', action:'BUY', impact:6.8, abstained:false, ts:'08:45' },
  { id:'e7', ticker:'BAC', headline:'Unverified rumour: Bank of America exploring fintech acquisition',
    event_type:'M&A', sentiment:0.48, confidence:0.61, novelty:0.96, spike:1.8,
    evidence:22, status:'WATCH', action:'HOLD', impact:3.2, abstained:true, ts:'14:05' },
  { id:'e8', ticker:'XOM', headline:'ExxonMobil reports Q3 cash flows in-line; maintains dividend guidance',
    event_type:'Earnings', sentiment:0.12, confidence:0.74, novelty:0.38, spike:2.3,
    evidence:58, status:'DEVELOPING', action:'HOLD', impact:3.8, abstained:false, ts:'17:00' },
];

export const DEMO_PORTFOLIO = [
  { ticker:'NVDA',  prev: 8.0, next:10.7, delta:+2.7, sector:'Semiconductors', action:'BUY' },
  { ticker:'AVGO',  prev: 6.5, next: 8.1, delta:+1.6, sector:'Semiconductors', action:'BUY' },
  { ticker:'META',  prev: 9.0, next:11.2, delta:+2.2, sector:'Technology',      action:'BUY' },
  { ticker:'AAPL',  prev:12.0, next:13.4, delta:+1.4, sector:'Technology',      action:'BUY' },
  { ticker:'MSFT',  prev:10.0, next:10.8, delta:+0.8, sector:'Technology',      action:'BUY' },
  { ticker:'GOOGL', prev: 7.0, next: 7.3, delta:+0.3, sector:'Technology',      action:'HOLD'},
  { ticker:'WMT',   prev: 5.5, next: 5.5, delta: 0.0, sector:'Consumer Staples',action:'HOLD'},
  { ticker:'COST',  prev: 4.5, next: 4.5, delta: 0.0, sector:'Consumer Staples',action:'HOLD'},
  { ticker:'V',     prev: 5.0, next: 5.0, delta: 0.0, sector:'Financials',      action:'HOLD'},
  { ticker:'BAC',   prev: 5.5, next: 5.5, delta: 0.0, sector:'Financials',      action:'HOLD'},
  { ticker:'JNJ',   prev: 4.0, next: 4.0, delta: 0.0, sector:'Healthcare',      action:'HOLD'},
  { ticker:'XOM',   prev: 4.5, next: 4.5, delta: 0.0, sector:'Energy',          action:'HOLD'},
  { ticker:'JPM',   prev: 8.0, next: 5.8, delta:-2.2, sector:'Financials',      action:'SELL'},
  { ticker:'TSLA',  prev: 7.5, next: 5.1, delta:-2.4, sector:'Consumer Discretionary',action:'SELL'},
  { ticker:'AMZN',  prev: 7.5, next: 6.2, delta:-1.3, sector:'Consumer Discretionary',action:'SELL'},
];

// 252-day backtest equity curves
export function genBacktest() {
  const n = 252;
  const configs = [
    { id:0, name:'Baseline (Equal-Weight)',              mu:0.12, sigma:0.18, color:'#718096', sharpe:0.42 },
    { id:1, name:'Strategy 1: Sentiment Only',           mu:0.15, sigma:0.20, color:'#63b3ed', sharpe:0.51 },
    { id:2, name:'Strategy 2: +Event +Impact',           mu:0.19, sigma:0.19, color:'#9f7aea', sharpe:0.75 },
    { id:3, name:'Full FinRisk AI (multi-signal)',        mu:0.24, sigma:0.17, color:'#48bb78', sharpe:1.12 },
  ];
  const seed = (s) => { let x = s; return () => { x = (x*9301+49297)%233280; return x/233280; }; };
  return configs.map(c => {
    const r = seed(c.id * 999 + 42);
    let v = 1_000_000;
    const dates = [], values = [];
    const dailyMu = c.mu/252, dailySig = c.sigma/Math.sqrt(252);
    for (let i = 0; i < n; i++) {
      const u1 = r(), u2 = r();
      const z = Math.sqrt(-2*Math.log(u1+0.001)) * Math.cos(2*Math.PI*u2);
      v *= Math.exp(dailyMu + dailySig*z);
      const d = new Date(2023, 0, 1);
      d.setDate(d.getDate() + i + Math.floor(i/5)*2);
      dates.push(d.toISOString().slice(0,10));
      values.push(Math.round(v));
    }
    const cum = values[n-1]/1_000_000 - 1;
    return { ...c, dates, values, cumReturn: cum, maxDD: -(0.05 + r()*0.12) };
  });
}

export const REPLAY_SCENARIOS = {
  'NVDA — Blackwell Supply Delay': [
    { time:'10:05', source:'Reddit r/wallstreetbets', status:'watch', action:'HOLD',
      headline:'Unverified: NVDA Blackwell production facing major delays',
      sentiment:-0.41, confidence:0.62, novelty:0.95, spike:1.8, evidence:22, impact:3.8,
      abstained:true, abstainReason:'Evidence 22/100 < 40 threshold',
      weightBefore:8.0, weightAfter:8.0, actionability:0.0 },
    { time:'10:18', source:'Reuters, Bloomberg, FT (8 sources)', status:'developing', action:'MONITOR',
      headline:'Multiple outlets confirm NVDA Blackwell ramp delayed by one quarter',
      sentiment:-0.71, confidence:0.88, novelty:0.65, spike:6.4, evidence:61, impact:6.8,
      abstained:false, abstainReason:'', weightBefore:8.0, weightAfter:8.0, actionability:0.0 },
    { time:'10:37', source:'SEC EDGAR 8-K Filing', status:'sell', action:'REBALANCE — SELL',
      headline:'NVDA files 8-K: Blackwell ramp delayed one quarter, guidance lowered',
      sentiment:-0.82, confidence:0.94, novelty:0.32, spike:9.2, evidence:91, impact:8.4,
      abstained:false, abstainReason:'', weightBefore:8.0, weightAfter:5.8, actionability:-0.612 },
  ],
  'AAPL — Earnings Beat Q1 2024': [
    { time:'16:05', source:'Twitter / X (analyst leaks)', status:'watch', action:'HOLD',
      headline:'Rumour: AAPL Q1 EPS significantly above consensus',
      sentiment:0.55, confidence:0.58, novelty:0.91, spike:2.1, evidence:18, impact:4.2,
      abstained:true, abstainReason:'Evidence 18/100 < 40 threshold',
      weightBefore:12.0, weightAfter:12.0, actionability:0.0 },
    { time:'16:30', source:'Apple IR Press Release + 10-Q', status:'rebalance', action:'REBALANCE — BUY',
      headline:'Apple Q1 EPS $2.18 vs $2.10 est; revenue $124B vs $118B est',
      sentiment:0.87, confidence:0.97, novelty:0.45, spike:11.3, evidence:96, impact:9.1,
      abstained:false, abstainReason:'', weightBefore:12.0, weightAfter:14.8, actionability:0.748 },
  ],
  'JPM — Regulatory Action': [
    { time:'14:22', source:'Reuters (1 source)', status:'watch', action:'HOLD',
      headline:'Report: Federal regulators reviewing JPM risk management practices',
      sentiment:-0.68, confidence:0.71, novelty:0.88, spike:3.4, evidence:31, impact:5.1,
      abstained:true, abstainReason:'Single unverified source — Evidence 31/100 < 40',
      weightBefore:7.5, weightAfter:7.5, actionability:0.0 },
    { time:'15:10', source:'OCC Official Announcement', status:'sell', action:'REBALANCE — SELL',
      headline:'OCC issues formal consent order against JPMorgan Chase',
      sentiment:-0.79, confidence:0.95, novelty:0.41, spike:8.7, evidence:94, impact:8.9,
      abstained:false, abstainReason:'', weightBefore:7.5, weightAfter:5.1, actionability:-0.583 },
  ],
};
