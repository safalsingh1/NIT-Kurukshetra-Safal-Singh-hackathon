// src/api.js — centralised API client
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function req(path, opts = {}) {
  try {
    const res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  } catch {
    return null;
  }
}

export const api = {
  health:    ()         => req('/health'),
  tickers:   ()         => req('/tickers'),
  universe:  ()         => req('/universe'),
  signals:   ()         => req('/signals'),
  events:    (params)   => req('/events?' + new URLSearchParams(params)),
  portfolio: ()         => req('/portfolio'),
  explain:   (ticker)   => req(`/explain/${ticker}`),
  narrative: (ticker)   => req(`/explain/narrative/${ticker}`),
  analyze:   (body)     => req('/analyze', { method: 'POST', body: JSON.stringify(body) }),
  rebalance: (body)     => req('/rebalance', { method: 'POST', body: JSON.stringify(body || {}) }),
  ablation:  (params)   => req('/backtest/ablation?' + new URLSearchParams(params || {})),
  stress:    (scenario) => req(`/stress?scenario=${scenario || 'rate_shock_150bps'}`),
};
