// src/pages/Portfolio.jsx
import { useState, useEffect } from 'react';
import { BarChart2, TrendingUp, RefreshCw, Download, FileText, X } from 'lucide-react';
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend
} from 'recharts';
import { DEMO_PORTFOLIO, genBacktest } from '../demoData';
import { api } from '../api.js';
import { toast } from '../Toast.jsx';

const BACKTEST = genBacktest();

const ABLATION = [
  { strategy:'Baseline',    sharpe:0.42, cumReturn:12.1, maxDD:-14.2, turnover:2.1, color:'#718096' },
  { strategy:'Sentiment',   sharpe:0.51, cumReturn:15.4, maxDD:-16.8, turnover:4.5, color:'#63b3ed' },
  { strategy:'+Event+Impact', sharpe:0.75, cumReturn:19.8, maxDD:-12.3, turnover:5.8, color:'#9f7aea' },
  { strategy:'Full FinRisk AI', sharpe:1.12, cumReturn:24.3, maxDD:-9.1,  turnover:6.4, color:'#48bb78' },
];

function WeightChangeRow({ row, i }) {
  const isUp = row.delta > 0;
  const isFlat = row.delta === 0;
  const color = isFlat ? 'var(--text-muted)' : isUp ? 'var(--green)' : 'var(--red)';
  const actionBadge = row.action === 'BUY' ? 'buy' : row.action === 'SELL' ? 'sell' : 'hold';

  return (
    <tr style={{ animationDelay: `${i * 30}ms` }} className="animate-slidein">
      <td><span className="ticker-cell">{row.ticker}</span></td>
      <td><span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{row.sector}</span></td>
      <td className="mono text-right">{row.prev.toFixed(1)}%</td>
      <td className="mono text-right" style={{ color }}><strong>{row.next.toFixed(1)}%</strong></td>
      <td className="mono text-right" style={{ color, fontWeight: 700 }}>
        {isFlat ? '—' : (isUp ? '+' : '') + row.delta.toFixed(1) + 'pp'}
      </td>
      <td>
        {/* mini bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{ width: `${Math.min(100, (row.next / 15) * 100)}%`, height: '100%', background: color, borderRadius: 2, transition: 'width 0.5s' }}/>
          </div>
        </div>
      </td>
      <td><span className={`badge badge-${actionBadge}`}>{row.action}</span></td>
    </tr>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#0d1224', border: '1px solid rgba(99,179,237,0.2)', borderRadius: 8, padding: '10px 14px', fontSize: '0.8rem' }}>
      <div style={{ color: '#94a3b8', marginBottom: 6 }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.color, marginBottom: 3 }}>
          {p.name}: <strong>${(p.value / 1000).toFixed(1)}k</strong>
        </div>
      ))}
    </div>
  );
};

export default function Portfolio({ apiLive = false }) {
  const [activeStrategy, setActiveStrategy] = useState('all');
  const [livePortfolio, setLivePortfolio]   = useState(null);
  const [liveStats, setLiveStats]           = useState(null);
  const [rebalancing, setRebalancing]       = useState(false);
  const [narrative, setNarrative]           = useState(null);  // { ticker, bullets, source }
  const [narrativeTicker, setNarrativeTicker] = useState(null);
  const [narrativeLoading, setNarrativeLoading] = useState(false);

  const fetchLivePortfolio = async () => {
    setRebalancing(true);
    try {
      const res = await api.rebalance();
      if (res?.data?.portfolio) {
        setLivePortfolio(res.data.portfolio);
        setLiveStats({
          turnover: res.data.turnover,
          nActed: res.data.n_acted,
          nAbstained: res.data.n_abstained,
          timestamp: res.data.timestamp,
          decisions: res.data.decisions,
        });
        toast(
          `Rebalancer ran: ${res.data.n_acted} weight changes, ${res.data.turnover?.toFixed(1)}pp turnover.`,
          { title: '✅ Rebalance Complete', type: 'confirm', duration: 5000 }
        );
      }
    } catch (e) {
      console.error(e);
    } finally {
      setRebalancing(false);
    }
  };

  useEffect(() => {
    if (!apiLive) {
      setLivePortfolio(null);
      setLiveStats(null);
      return;
    }
    fetchLivePortfolio();
  }, [apiLive]);

  // ── Audit export ──────────────────────────────────────────────────────
  const downloadAudit = () => {
    const portfolioData = livePortfolio ?? DEMO_PORTFOLIO;
    const audit = {
      generated_at:  new Date().toISOString(),
      mode:          apiLive ? 'live' : 'demo',
      rebalance_ts:  liveStats?.timestamp ?? new Date().toISOString(),
      summary: {
        n_acted:      liveStats?.nActed    ?? portfolioData.filter(r => r.action !== 'HOLD').length,
        n_abstained:  liveStats?.nAbstained ?? 0,
        turnover_pp:  liveStats?.turnover    ?? +portfolioData.reduce((s, r) => s + Math.abs(r.delta), 0).toFixed(1),
      },
      constraints_enforced: {
        max_single_stock_pct: 15,
        sector_cap_pct:       25,
        max_turnover_pp:      10,
        evidence_gate:        40,
      },
      weight_changes: portfolioData.map(r => ({
        ticker:  r.ticker,
        sector:  r.sector,
        from:    r.prev,
        to:      r.next,
        delta:   r.delta,
        action:  r.action,
      })),
      ablation_study: ABLATION.map(a => ({
        strategy:    a.strategy,
        sharpe:      a.sharpe,
        cum_return:  a.cumReturn,
        max_drawdown:a.maxDD,
        turnover:    a.turnover,
      })),
    };
    const blob = new Blob([JSON.stringify(audit, null, 2)], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `finrisk_audit_${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast('Audit report downloaded as JSON.', { title: '📥 Audit Export', type: 'info', duration: 4000 });
  };

  // ── LLM Narrative ─────────────────────────────────────────────────────
  const fetchNarrative = async (ticker) => {
    setNarrativeTicker(ticker);
    setNarrativeLoading(true);
    setNarrative(null);
    const r = await api.narrative(ticker);
    if (r?.data) setNarrative(r.data);
    setNarrativeLoading(false);
  };

  // Build equity curve data
  const n = BACKTEST[0].dates.length;
  const chartData = [];
  for (let i = 0; i < n; i += 3) { // sample every 3 days for perf
    const entry = { date: BACKTEST[0].dates[i] };
    BACKTEST.forEach(s => { entry[s.name.split(':')[0].replace('Full ','').trim()] = s.values[i]; });
    chartData.push(entry);
  }

  const portfolioData = livePortfolio ?? DEMO_PORTFOLIO;
  const buys  = portfolioData.filter(r => r.action === 'BUY').length;
  const sells = portfolioData.filter(r => r.action === 'SELL').length;
  const holds = portfolioData.filter(r => r.action === 'HOLD').length;
  const totalChange = liveStats?.turnover !== undefined
    ? liveStats.turnover.toFixed(1)
    : portfolioData.reduce((s, r) => s + Math.abs(r.delta), 0).toFixed(1);

  return (
    <div className="animate-fadeup">
      <div className="page-header">
        <div className="page-title">
          <BarChart2 size={22} style={{ color: 'var(--green)' }}/> Portfolio Rebalancer
          {rebalancing && <RefreshCw size={14} style={{ color:'var(--text-muted)', animation:'spin 1s linear infinite', marginLeft:8 }}/>}
        </div>
        <div className="page-subtitle">
          {apiLive
            ? '🟢 Live Convex Optimizer · Ledoit-Wolf Covariance · 10% Turnover Cap'
            : '🔵 Demo mode — Pre-saved 1-year backtest & ablation study'}
        </div>
      </div>

      {/* Rebalance summary */}
      <div className="grid-3 mb-24">
        <div className="metric-card">
          <div className="metric-label">BUY Signals</div>
          <div className="metric-value text-green">{buys}</div>
          <div className="metric-sub">Increase weight</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">SELL Signals</div>
          <div className="metric-value text-red">{sells}</div>
          <div className="metric-sub">Reduce weight</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Total Turnover</div>
          <div className="metric-value text-blue">{totalChange}<span style={{ fontSize: '1rem' }}>pp</span></div>
          <div className="metric-sub">≤ 10% constraint</div>
        </div>
      </div>

      {/* Narrative Modal */}
      {narrativeTicker && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200 }} onClick={() => setNarrativeTicker(null)}>
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-hover)', borderRadius: 16, padding: 28, minWidth: 420, maxWidth: 540 }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800 }}>{narrativeTicker} — Executive Summary</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                  {narrative?.source === 'gemini-1.5-flash' ? '✨ Generated by Gemini 1.5 Flash' : '📋 Template-based analysis'}
                </div>
              </div>
              <button onClick={() => setNarrativeTicker(null)} style={{ color: 'var(--text-muted)', cursor: 'pointer' }}><X size={18} /></button>
            </div>
            {narrativeLoading ? (
              <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)' }}>
                <RefreshCw size={20} style={{ animation: 'spin 1s linear infinite', marginBottom: 10 }} />
                <div>Generating AI summary…</div>
              </div>
            ) : narrative?.bullets?.length ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {narrative.bullets.map((b, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, padding: '12px 14px', background: 'rgba(99,179,237,0.05)', border: '1px solid rgba(99,179,237,0.12)', borderRadius: 10 }}>
                    <span style={{ color: 'var(--blue)', fontWeight: 700, fontSize: '1rem', flexShrink: 0 }}>•</span>
                    <span style={{ fontSize: '0.85rem', lineHeight: 1.6, color: 'var(--text-primary)' }}>{b}</span>
                  </div>
                ))}
                {narrative.weight_change && (
                  <div style={{ display: 'flex', gap: 20, padding: '8px 14px', background: 'rgba(72,187,120,0.05)', border: '1px solid rgba(72,187,120,0.12)', borderRadius: 8, fontSize: '0.8rem' }}>
                    <span>Weight: <strong style={{ color: 'var(--blue)' }}>{narrative.weight_change.from}%</strong> → <strong style={{ color: 'var(--green)' }}>{narrative.weight_change.to}%</strong></span>
                    <span style={{ color: narrative.weight_change.delta >= 0 ? 'var(--green)' : 'var(--red)', fontWeight: 700 }}>{narrative.weight_change.delta >= 0 ? '+' : ''}{narrative.weight_change.delta}pp</span>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No narrative available.</div>
            )}
          </div>
        </div>
      )}

      {/* Portfolio weight table */}
      <div className="card mb-24">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div className="card-title" style={{ marginBottom: 0 }}>
            {apiLive ? 'LIVE CONVEX OPTIMIZER REBALANCE — 15 STOCK UNIVERSE' : 'LATEST REBALANCE — 15 STOCK UNIVERSE'}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={downloadAudit}
              className="btn btn-outline"
              style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', padding: '6px 12px' }}
            >
              <Download size={13} /> Audit JSON
            </button>
            {apiLive && (
              <button
                onClick={fetchLivePortfolio}
                disabled={rebalancing}
                className="btn btn-outline"
                style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', padding: '6px 12px' }}
              >
                <RefreshCw size={13} style={{ animation: rebalancing ? 'spin 1s linear infinite' : 'none' }} />
                {rebalancing ? 'Optimizing…' : 'Rebalance Now'}
              </button>
            )}
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="portfolio-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Sector</th>
                <th className="text-right">Prev %</th>
                <th className="text-right">New %</th>
                <th className="text-right">Δ</th>
                <th>Weight Bar</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {portfolioData.map((row, i) => (
                <tr key={row.ticker} style={{ animationDelay: `${i * 30}ms` }} className="animate-slidein">
                  <td>
                    <button
                      onClick={() => fetchNarrative(row.ticker)}
                      style={{ color: 'var(--blue)', fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer', background: 'none', border: 'none', textDecoration: 'underline dotted' }}
                      title="Click for AI executive summary"
                    >
                      {row.ticker}
                    </button>
                  </td>
                  <td><span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{row.sector}</span></td>
                  <td className="mono text-right">{row.prev.toFixed(1)}%</td>
                  <td className="mono text-right" style={{ color: row.delta > 0 ? 'var(--green)' : row.delta < 0 ? 'var(--red)' : 'var(--text-muted)' }}><strong>{row.next.toFixed(1)}%</strong></td>
                  <td className="mono text-right" style={{ color: row.delta > 0 ? 'var(--green)' : row.delta < 0 ? 'var(--red)' : 'var(--text-muted)', fontWeight: 700 }}>
                    {row.delta === 0 ? '—' : (row.delta > 0 ? '+' : '') + row.delta.toFixed(1) + 'pp'}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ width: `${Math.min(100, (row.next / 15) * 100)}%`, height: '100%', background: row.delta > 0 ? 'var(--green)' : row.delta < 0 ? 'var(--red)' : 'var(--text-muted)', borderRadius: 2, transition: 'width 0.5s' }}/>
                      </div>
                    </div>
                  </td>
                  <td><span className={`badge badge-${row.action === 'BUY' ? 'buy' : row.action === 'SELL' ? 'sell' : 'hold'}`}>{row.action}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Equity curves */}
      <div className="card mb-24">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div className="card-title" style={{ marginBottom: 0 }}>EQUITY CURVES — 4-STRATEGY ABLATION (1 Year)</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {BACKTEST.map(s => {
              const key = s.name.split(':')[0].replace('Full ','').trim();
              return (
                <button
                  key={s.id}
                  onClick={() => setActiveStrategy(activeStrategy === key ? 'all' : key)}
                  style={{ padding: '4px 10px', borderRadius: 20, fontSize: '0.7rem', fontWeight: 600, border: `1px solid ${s.color}`,
                    background: activeStrategy === key ? s.color : 'transparent', color: activeStrategy === key ? 'white' : s.color, cursor: 'pointer' }}
                >
                  {s.name.split(':').pop().trim().slice(0,12)}
                </button>
              );
            })}
          </div>
        </div>
        <div className="chart-container" style={{ height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3"/>
              <XAxis dataKey="date" tick={{ fill: '#4a5568', fontSize: 10 }} interval={19}/>
              <YAxis tickFormatter={v => `$${(v/1000).toFixed(0)}k`} tick={{ fill: '#4a5568', fontSize: 10 }}/>
              <Tooltip content={<CustomTooltip/>}/>
              <Legend wrapperStyle={{ fontSize: '0.75rem', paddingTop: 8 }}/>
              {BACKTEST.map(s => {
                const key = s.name.split(':')[0].replace('Full ','').trim();
                const visible = activeStrategy === 'all' || activeStrategy === key;
                return (
                  <Line
                    key={s.id}
                    type="monotone"
                    dataKey={key}
                    name={key}
                    stroke={s.color}
                    strokeWidth={s.id === 3 ? 2.5 : 1.5}
                    dot={false}
                    opacity={visible ? 1 : 0.15}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Ablation table + Sharpe bar */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>
        <div className="card">
          <div className="card-title mb-16">ABLATION STUDY RESULTS</div>
          <table className="portfolio-table">
            <thead>
              <tr>
                <th>Strategy</th>
                <th className="text-right">Sharpe</th>
                <th className="text-right">Cum. Return</th>
                <th className="text-right">Max DD</th>
                <th className="text-right">Turnover</th>
              </tr>
            </thead>
            <tbody>
              {ABLATION.map((a, i) => (
                <tr key={a.strategy} className="animate-slidein" style={{ animationDelay: `${i*50}ms` }}>
                  <td>
                    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                      <div style={{ width:3, height:20, borderRadius:2, background:a.color }}/>
                      <span style={{ fontSize:'0.85rem', fontWeight: i===3?700:400, color:i===3?'var(--green)':'var(--text-primary)' }}>{a.strategy}</span>
                    </div>
                  </td>
                  <td className="mono text-right" style={{ color:a.color, fontWeight:700 }}>{a.sharpe.toFixed(2)}</td>
                  <td className="mono text-right" style={{ color:'var(--green)' }}>+{a.cumReturn.toFixed(1)}%</td>
                  <td className="mono text-right" style={{ color:'var(--red)' }}>{a.maxDD.toFixed(1)}%</td>
                  <td className="mono text-right text-muted">{a.turnover.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 16, padding: '10px 14px', background:'rgba(72,187,120,0.06)', border:'1px solid rgba(72,187,120,0.15)', borderRadius:8, fontSize:'0.78rem', color:'var(--text-muted)', lineHeight:1.7 }}>
            <strong style={{ color:'var(--green)' }}>Key finding:</strong> Adding event context (S2→S1) reduces unnecessary rebalancing.
            Adding evidence confirmation prevents acting on rumours. Risk constraints lower turnover & drawdown.
            Full FinRisk AI achieves <strong style={{ color:'var(--green)' }}>Sharpe 1.12</strong> vs 0.42 baseline.
          </div>
        </div>

        <div className="card">
          <div className="card-title mb-16">SHARPE RATIO</div>
          <div style={{ height: 200 }}>
            <ResponsiveContainer>
              <BarChart data={ABLATION} layout="vertical" margin={{ left: 16, right: 24 }}>
                <XAxis type="number" domain={[0, 1.3]} tick={{ fill:'#4a5568', fontSize:10 }}/>
                <YAxis dataKey="strategy" type="category" tick={{ fill:'#94a3b8', fontSize:10 }} width={90}/>
                <Tooltip formatter={v => [v.toFixed(2), 'Sharpe Ratio']} contentStyle={{ background:'#0d1224', border:'1px solid rgba(99,179,237,0.2)', borderRadius:8, fontSize:'0.8rem' }}/>
                <Bar dataKey="sharpe" radius={[0,4,4,0]}>
                  {ABLATION.map(a => <rect key={a.strategy} fill={a.color}/>)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
