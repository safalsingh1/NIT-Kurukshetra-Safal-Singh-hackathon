// src/pages/MacroStressTest.jsx
import { useState, useEffect } from 'react';
import { ShieldAlert, RefreshCw, TrendingDown, AlertTriangle, BarChart2 } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, Legend, Cell, ReferenceLine,
} from 'recharts';
import { api } from '../api.js';

// ─── Demo data for offline mode ─────────────────────────────────────────────
const DEMO_SCENARIOS = {
  rate_shock_150bps:  { label: 'Rate Shock +150 bps', icon: '📈' },
  equity_crash_10pct: { label: 'Equity Crash −10%',   icon: '📉' },
  credit_crisis:      { label: 'Credit Spread +100 bps', icon: '🏦' },
  geopolitical_shock: { label: 'Geopolitical Risk Spike', icon: '🌐' },
};

const DEMO_BOOK = [
  { name: 'Investment Grade Bonds', asset_class: 'Fixed Income',  notional: 42_000_000, pnl: -390_600, pnl_pct: -0.93 },
  { name: 'High Yield Bonds',       asset_class: 'Fixed Income',  notional: 18_000_000, pnl: -267_300, pnl_pct: -1.49 },
  { name: 'Corporate Loans (Term A)',asset_class: 'Loans',         notional: 35_000_000, pnl: -192_500, pnl_pct: -0.55 },
  { name: 'Revolving Credit Fac.',  asset_class: 'Loans',         notional: 12_000_000, pnl: -54_000,  pnl_pct: -0.45 },
  { name: 'IR Swap (Pay Fixed)',     asset_class: 'Derivatives',   notional: 25_000_000, pnl: -262_500, pnl_pct: -1.05 },
  { name: 'CDS Protection Bought',  asset_class: 'Derivatives',   notional: 10_000_000, pnl:  135_000, pnl_pct:  1.35 },
  { name: 'Equity Portfolio',       asset_class: 'Equities',       notional: 28_000_000, pnl: -2_240_000,pnl_pct:-8.00 },
  { name: 'Government Bonds (10Y)', asset_class: 'Fixed Income',  notional: 20_000_000, pnl:   91_000, pnl_pct:  0.46 },
];

const DEMO_CLASS = [
  { asset_class: 'Fixed Income', before: 100_000_000, after: 99_433_100, loss: -566_900, loss_pct: -0.57 },
  { asset_class: 'Loans',        before:  47_000_000, after: 46_753_500, loss: -246_500, loss_pct: -0.52 },
  { asset_class: 'Derivatives',  before:  35_000_000, after: 34_872_500, loss: -127_500, loss_pct: -0.36 },
  { asset_class: 'Equities',     before:  28_000_000, after: 25_760_000, loss:-2_240_000, loss_pct:-8.00 },
];

const CLASS_COLORS = {
  'Fixed Income': '#63b3ed',
  'Loans':        '#9f7aea',
  'Derivatives':  '#ecc94b',
  'Equities':     '#fc8181',
};

function fmt(n) {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${n < 0 ? '-' : '+'}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000)    return `${n < 0 ? '-' : '+'}$${(abs / 1_000).toFixed(0)}K`;
  return `${n < 0 ? '-' : '+'}$${abs.toFixed(0)}`;
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#0d1224', border: '1px solid rgba(99,179,237,0.2)', borderRadius: 8, padding: '10px 14px', fontSize: '0.8rem' }}>
      <div style={{ color: '#94a3b8', marginBottom: 6 }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.value < 0 ? '#fc8181' : '#48bb78', marginBottom: 3 }}>
          {p.name}: <strong>{fmt(p.value)}</strong> ({(p.value < 0 ? '' : '+') + (p.value / (p.payload.before || 1) * 100).toFixed(2)}%)
        </div>
      ))}
    </div>
  );
};

export default function MacroStressTest({ apiLive = false }) {
  const [scenario, setScenario]   = useState('rate_shock_150bps');
  const [result, setResult]       = useState(null);
  const [loading, setLoading]     = useState(false);

  const fetchStress = async (s) => {
    if (!apiLive) { setResult(null); return; }
    setLoading(true);
    const r = await api.stress(s);
    if (r?.data) setResult(r.data);
    setLoading(false);
  };

  useEffect(() => { fetchStress(scenario); }, [apiLive, scenario]);

  const data       = result ?? null;
  const assets     = data?.assets ?? DEMO_BOOK;
  const byClass    = data?.by_class ?? DEMO_CLASS;
  const totalLoss  = data?.total_loss  ?? DEMO_BOOK.reduce((s, a) => s + a.pnl, 0);
  const totalBefore= data?.total_before ?? 190_000_000;
  const totalAfter = data?.total_after  ?? totalBefore + totalLoss;
  const lossPct    = data?.loss_pct ?? (totalLoss / totalBefore * 100).toFixed(2);
  const var99      = data?.var_99 ?? -2_240_000;
  const label      = data?.label ?? DEMO_SCENARIOS[scenario]?.label;
  const description= data?.description ?? 'Select a scenario to run the shock simulation.';
  const trigger    = data?.trigger ?? '';
  const shocks     = data?.shocks ?? {};
  const scenarioMeta = data?.scenario_meta ?? DEMO_SCENARIOS;

  // Chart data for Before / After bars per asset class
  const classChartData = byClass.map(c => ({
    name:  c.asset_class,
    Before: c.before / 1_000_000,
    After:  c.after  / 1_000_000,
    loss:   c.loss,
  }));

  // Per-asset P&L bar
  const assetPnlData = assets.map(a => ({
    name: a.name.replace('Investment Grade', 'IG').replace('Corporate Loans', 'Corp Loans').replace('Revolving Credit Fac.', 'Revolver').replace('Government Bonds (10Y)', 'Govt Bonds'),
    PnL:  a.pnl / 1_000,
    asset_class: a.asset_class,
  }));

  return (
    <div className="animate-fadeup">
      <div className="page-header">
        <div className="page-title">
          <ShieldAlert size={22} style={{ color: 'var(--red)' }} /> Macro Stress Test
          {loading && <RefreshCw size={14} style={{ color: 'var(--text-muted)', animation: 'spin 1s linear infinite', marginLeft: 8 }} />}
        </div>
        <div className="page-subtitle">
          {apiLive
            ? '🟢 Live stress simulation — wholesale banking book'
            : '🔵 Demo mode — synthetic fixed-income + loans + derivatives + equities portfolio'}
        </div>
      </div>

      {/* Trigger banner */}
      {trigger && (
        <div style={{ background: 'rgba(252,129,129,0.07)', border: '1px solid rgba(252,129,129,0.2)', borderRadius: 10, padding: '10px 16px', marginBottom: 20, fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: 10 }}>
          <AlertTriangle size={15} style={{ color: 'var(--red)', flexShrink: 0 }} />
          <span><strong style={{ color: 'var(--red)' }}>Triggered by: </strong>{trigger}</span>
        </div>
      )}

      {/* Scenario selector */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 24, flexWrap: 'wrap' }}>
        {Object.entries(scenarioMeta).map(([key, meta]) => (
          <button
            key={key}
            onClick={() => { setScenario(key); fetchStress(key); }}
            style={{
              padding: '8px 16px', borderRadius: 20, fontSize: '0.78rem', fontWeight: 600,
              border: `1px solid ${scenario === key ? 'rgba(252,129,129,0.5)' : 'rgba(255,255,255,0.1)'}`,
              background: scenario === key ? 'rgba(252,129,129,0.12)' : 'rgba(255,255,255,0.04)',
              color: scenario === key ? 'var(--red)' : 'var(--text-secondary)',
              cursor: 'pointer', transition: 'all 0.2s',
            }}
          >
            {meta.icon} {meta.label}
          </button>
        ))}
      </div>

      {/* Scenario description */}
      <div style={{ background: 'rgba(236,201,75,0.06)', border: '1px solid rgba(236,201,75,0.15)', borderRadius: 10, padding: '12px 16px', marginBottom: 24, fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
        <strong style={{ color: 'var(--yellow)' }}>{data?.icon ?? DEMO_SCENARIOS[scenario]?.icon} {label}</strong>
        <span style={{ marginLeft: 10 }}>{description}</span>
        {Object.keys(shocks).length > 0 && (
          <div style={{ marginTop: 8, display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            {shocks.equity_drop   !== 0 && <span style={{ fontFamily: 'JetBrains Mono', fontSize: '0.78rem', color: 'var(--red)' }}>Equity Δ: {(shocks.equity_drop * 100).toFixed(0)}%</span>}
            {shocks.rate_rise_bps !== 0 && <span style={{ fontFamily: 'JetBrains Mono', fontSize: '0.78rem', color: 'var(--blue)' }}>Rates: +{shocks.rate_rise_bps} bps</span>}
            {shocks.credit_spread_bps !== 0 && <span style={{ fontFamily: 'JetBrains Mono', fontSize: '0.78rem', color: 'var(--yellow)' }}>Credit Spread: +{shocks.credit_spread_bps} bps</span>}
          </div>
        )}
      </div>

      {/* KPI Row */}
      <div className="grid-3 mb-24">
        <div className="metric-card">
          <div className="metric-label">Total Expected Loss</div>
          <div className="metric-value text-red">{fmt(totalLoss)}</div>
          <div className="metric-sub">{lossPct}% of book</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Book Value (After Shock)</div>
          <div className="metric-value text-blue">${(totalAfter / 1_000_000).toFixed(1)}M</div>
          <div className="metric-sub">vs ${(totalBefore / 1_000_000).toFixed(1)}M pre-shock</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">99% VaR (Worst Asset)</div>
          <div className="metric-value text-yellow">{fmt(var99)}</div>
          <div className="metric-sub">Single asset worst-case</div>
        </div>
      </div>

      {/* Before vs After by Asset Class */}
      <div className="card mb-24">
        <div className="card-title mb-16">BEFORE vs AFTER — BY ASSET CLASS</div>
        <div style={{ height: 260 }}>
          <ResponsiveContainer>
            <BarChart data={classChartData} margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tickFormatter={v => `$${v.toFixed(0)}M`} tick={{ fill: '#4a5568', fontSize: 10 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '0.78rem', paddingTop: 8 }} />
              <Bar dataKey="Before" fill="rgba(99,179,237,0.35)" stroke="#63b3ed" strokeWidth={1} radius={[4, 4, 0, 0]} />
              <Bar dataKey="After"  fill="rgba(252,129,129,0.45)" stroke="#fc8181" strokeWidth={1} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Per-Asset P&L bars */}
      <div className="card mb-24">
        <div className="card-title mb-16">P&L IMPACT PER ASSET (US$K)</div>
        <div style={{ height: 260 }}>
          <ResponsiveContainer>
            <BarChart data={assetPnlData} layout="vertical" margin={{ top: 4, right: 60, bottom: 4, left: 8 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={v => `$${v.toFixed(0)}K`} tick={{ fill: '#4a5568', fontSize: 10 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} width={140} />
              <Tooltip formatter={(v) => [`${v < 0 ? '-' : '+'}$${Math.abs(v).toFixed(0)}K`, 'P&L']} contentStyle={{ background: '#0d1224', border: '1px solid rgba(99,179,237,0.2)', borderRadius: 8, fontSize: '0.8rem' }} />
              <ReferenceLine x={0} stroke="rgba(255,255,255,0.15)" />
              <Bar dataKey="PnL" radius={[0, 4, 4, 0]}>
                {assetPnlData.map((entry, i) => (
                  <Cell key={i} fill={entry.PnL >= 0 ? 'rgba(72,187,120,0.6)' : 'rgba(252,129,129,0.6)'} stroke={entry.PnL >= 0 ? '#48bb78' : '#fc8181'} strokeWidth={1} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Per-Asset Detail Table */}
      <div className="card">
        <div className="card-title mb-16">ASSET-LEVEL STRESS DETAILS</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="portfolio-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Class</th>
                <th className="text-right">Notional</th>
                <th className="text-right">Stressed P&L</th>
                <th className="text-right">P&L %</th>
                <th>Impact</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((a, i) => {
                const isLoss = a.pnl < 0;
                const severity = Math.abs(a.pnl_pct) > 3 ? 'red' : Math.abs(a.pnl_pct) > 1 ? 'yellow' : 'text-muted';
                return (
                  <tr key={a.name ?? i} className="animate-slidein" style={{ animationDelay: `${i * 30}ms` }}>
                    <td style={{ fontWeight: 600, fontSize: '0.85rem' }}>{a.name}</td>
                    <td>
                      <span style={{ fontSize: '0.72rem', padding: '2px 8px', borderRadius: 12, background: `${CLASS_COLORS[a.asset_class] || '#63b3ed'}18`, color: CLASS_COLORS[a.asset_class] || '#63b3ed', border: `1px solid ${CLASS_COLORS[a.asset_class] || '#63b3ed'}40` }}>
                        {a.asset_class}
                      </span>
                    </td>
                    <td className="mono text-right" style={{ color: 'var(--text-secondary)' }}>${(a.notional / 1_000_000).toFixed(1)}M</td>
                    <td className="mono text-right" style={{ color: isLoss ? 'var(--red)' : 'var(--green)', fontWeight: 700 }}>{fmt(a.pnl)}</td>
                    <td className={`mono text-right ${isLoss ? 'text-red' : 'text-green'}`}>{a.pnl_pct > 0 ? '+' : ''}{a.pnl_pct.toFixed(2)}%</td>
                    <td>
                      <div style={{ width: '100%', height: 4, background: 'rgba(255,255,255,0.05)', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ width: `${Math.min(100, Math.abs(a.pnl_pct) * 12)}%`, height: '100%', background: isLoss ? 'var(--red)' : 'var(--green)', borderRadius: 2 }} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div style={{ marginTop: 16, padding: '10px 14px', background: 'rgba(252,129,129,0.05)', border: '1px solid rgba(252,129,129,0.15)', borderRadius: 8, fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
          <strong style={{ color: 'var(--red)' }}>Methodology:</strong> Rate impact = −Duration × ΔRate × Notional. Credit impact = −CS_Sensitivity × ΔSpread × Notional. Equity impact = Beta × ΔEquity × Notional. CDS protection provides partial offset (negative beta to credit spread).
        </div>
      </div>
    </div>
  );
}
