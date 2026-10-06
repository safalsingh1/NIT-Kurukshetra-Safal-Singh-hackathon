// src/pages/MarketRadar.jsx
import { useState, useEffect } from 'react';
import { Activity, TrendingUp, TrendingDown, Zap, RefreshCw } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { UNIVERSE, DEMO_EVENTS } from '../demoData';
import { api } from '../api.js';

const SECTOR_COLORS = {
  Technology: '#63b3ed', Semiconductors: '#9f7aea', Financials: '#48bb78',
  'Consumer Discretionary': '#fc8181', Energy: '#f6ad55', Healthcare: '#76e4f7',
  'Consumer Staples': '#68d391',
};

function riskTimeline() {
  const points = [];
  let risk = 5.2;
  for (let i = 0; i < 48; i++) {
    risk += (Math.random() - 0.48) * 0.5;
    risk = Math.max(1, Math.min(10, risk));
    const h = 9 + Math.floor(i / 2);
    const m = i % 2 === 0 ? '00' : '30';
    points.push({ time: `${h}:${m}`, risk: +risk.toFixed(2), spike: Math.random() > 0.85 ? risk + 1 : null });
  }
  return points;
}

function HeatmapTile({ stock, onClick }) {
  const bull = stock.actionability > 0.05;
  const bear = stock.actionability < -0.05;
  const cls = bull ? 'bull' : bear ? 'bear' : 'neutral';
  const pct = ((stock.actionability) * 100).toFixed(1);

  return (
    <div className={`heatmap-tile ${cls} animate-fadeup`} onClick={() => onClick(stock)}>
      <div className="tile-ticker">{stock.ticker}</div>
      <div className="tile-change" style={{ color: bull ? '#9ae6b4' : bear ? '#feb2b2' : '#94a3b8' }}>
        {stock.actionability > 0 ? '+' : ''}{pct}%
      </div>
      <div className="tile-signal" style={{ color: SECTOR_COLORS[stock.sector] || '#63b3ed' }}>
        {stock.sector.split(' ')[0].toUpperCase().slice(0,4)}
      </div>
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#0d1224', border: '1px solid rgba(99,179,237,0.2)', borderRadius: 8, padding: '10px 14px', fontSize: '0.8rem' }}>
      <div style={{ color: '#94a3b8', marginBottom: 4 }}>{label}</div>
      <div style={{ color: '#63b3ed', fontWeight: 700 }}>Risk Index: {payload[0]?.value}</div>
    </div>
  );
};

export default function MarketRadar({ apiLive = false }) {
  const [selected, setSelected] = useState(null);
  const [timeline] = useState(riskTimeline);
  const [liveSignals, setLiveSignals] = useState(null);
  const [liveEvents, setLiveEvents]   = useState(null);
  const [loading, setLoading]         = useState(false);

  useEffect(() => {
    if (!apiLive) { setLiveSignals(null); setLiveEvents(null); return; }
    setLoading(true);
    Promise.all([api.universe(), api.events({})])
      .then(([uni, evts]) => {
        // /universe always returns all 15 stocks — safe for heatmap
        setLiveSignals(Array.isArray(uni?.data) && uni.data.length > 0 ? uni.data : null);
        setLiveEvents(evts?.data ?? null);
      })
      .finally(() => setLoading(false));
  }, [apiLive]);

  const events   = liveEvents   ?? DEMO_EVENTS;
  const universe = liveSignals  ?? UNIVERSE;

  const confirmed = events.filter(e => e.status === 'CONFIRMED').length;
  const abstained = events.filter(e => e.abstained).length;
  const avgImpact = (events.reduce((s, e) => s + (e.impact ?? 0), 0) / Math.max(events.length, 1)).toFixed(1);

  return (
    <div className="animate-fadeup">
      <div className="page-header">
        <div className="page-title">
          <Activity size={22} style={{ color: 'var(--blue)' }} />
          Market Radar
          {loading && <RefreshCw size={14} style={{ color:'var(--text-muted)', animation:'spin 1s linear infinite', marginLeft:8 }}/>}
        </div>
        <div className="page-subtitle">
          {apiLive ? '🟢 Live data from GDELT + SEC EDGAR APIs' : '🔵 Demo mode — pre-saved data · click DEMO to go live'}
        </div>
      </div>

      {/* KPI row */}
      <div className="grid-3 mb-24">
        <div className="metric-card">
          <div className="metric-label">Active Signals</div>
          <div className="metric-value" style={{ background: 'var(--gradient-brand)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            {confirmed}
          </div>
          <div className="metric-sub text-green"><TrendingUp size={14}/> CONFIRMED events</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Avg Impact Score</div>
          <div className="metric-value text-red">{avgImpact}<span style={{ fontSize:'1rem', color:'var(--text-muted)', fontWeight:500 }}>/10</span></div>
          <div className="metric-sub text-muted">Across active events today</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Abstentions</div>
          <div className="metric-value text-yellow">{abstained}</div>
          <div className="metric-sub text-muted">Evidence below 40/100 threshold</div>
        </div>
      </div>

      {/* Heatmap + Risk Timeline */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20, marginBottom: 28 }}>
        <div className="card">
          <div className="card-title"><Zap size={14}/> SIGNAL HEATMAP — 15 STOCKS</div>
          <div className="heatmap-grid">
            {universe.map(s => <HeatmapTile key={s.ticker} stock={s} onClick={setSelected} />)}
          </div>
        </div>

        <div className="card">
          <div className="card-title"><Activity size={14}/> RISK TIMELINE — TODAY</div>
          <div className="chart-container" style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeline} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#63b3ed" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#63b3ed" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3"/>
                <XAxis dataKey="time" tick={{ fill:'#4a5568', fontSize:10 }} interval={7}/>
                <YAxis domain={[0, 10]} tick={{ fill:'#4a5568', fontSize:10 }}/>
                <Tooltip content={<CustomTooltip/>}/>
                <Area type="monotone" dataKey="risk" stroke="#63b3ed" strokeWidth={2} fill="url(#riskGrad)"/>
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div style={{ marginTop: 8, borderTop:'1px solid var(--border)', paddingTop:10 }}>
            <div className="flex items-center gap-8 mb-8">
              <div style={{ width:8,height:8,borderRadius:'50%',background:'var(--red)',boxShadow:'0 0 6px var(--red)' }}/>
              <span className="text-muted" style={{fontSize:'0.75rem'}}>Risk Threshold (7.0)</span>
            </div>
            {/* mini event list */}
            {events.filter(e=>e.status==='CONFIRMED').slice(0,3).map(e => (
              <div key={e.id} className="flex items-center gap-8" style={{ padding:'5px 0', borderBottom:'1px solid rgba(255,255,255,0.04)' }}>
                <span className={`event-dot ${e.status.toLowerCase()}`}/>
                <span style={{ fontSize:'0.75rem', color:'var(--text-secondary)', flex:1, overflow:'hidden', whiteSpace:'nowrap', textOverflow:'ellipsis' }}>{e.ticker}: {(e.headline||'').slice(0,50)}…</span>
                <span style={{ fontSize:'0.72rem', color:'var(--text-muted)' }}>{e.ts}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sector breakdown */}
      <div className="card">
        <div className="card-title">SECTOR SIGNAL BREAKDOWN</div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(7,1fr)', gap:12 }}>
          {Object.entries(SECTOR_COLORS).map(([sector, color]) => {
            const stocks = universe.filter(s => s.sector === sector);
            if (!stocks.length) return null;
            const avg = stocks.reduce((s,u)=>s+u.actionability,0)/stocks.length;
            return (
              <div key={sector} style={{ textAlign:'center' }}>
                <div style={{ fontSize:'0.65rem', color:'var(--text-muted)', marginBottom:6, lineHeight:1.3 }}>{sector.split(' ').map(w=>w.slice(0,4)).join(' ')}</div>
                <div style={{ height:60, display:'flex', alignItems:'flex-end', justifyContent:'center', marginBottom:4 }}>
                  <div style={{ width:28, borderRadius:'4px 4px 0 0', background:avg>0?'rgba(72,187,120,0.4)':'rgba(252,129,129,0.4)', height:`${Math.abs(avg)*100}%`, minHeight:4, border:`1px solid ${color}`, transition:'height 0.5s' }}/>
                </div>
                <div style={{ fontSize:'0.78rem', fontWeight:700, color: avg>0.05?'var(--green)':avg<-0.05?'var(--red)':'var(--text-muted)', fontFamily:'JetBrains Mono,monospace' }}>
                  {avg>0?'+':''}{(avg*100).toFixed(0)}%
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Selected stock modal */}
      {selected && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.6)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:100 }} onClick={()=>setSelected(null)}>
          <div style={{ background:'var(--bg-surface)', border:'1px solid var(--border-hover)', borderRadius:16, padding:28, minWidth:380, maxWidth:480 }} onClick={e=>e.stopPropagation()}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
              <div>
                <div style={{ fontSize:'1.4rem', fontWeight:800 }}>{selected.ticker}</div>
                <div style={{ fontSize:'0.8rem', color:'var(--text-muted)' }}>{selected.company}</div>
              </div>
              <button onClick={()=>setSelected(null)} style={{ color:'var(--text-muted)', fontSize:'1.2rem', fontWeight:700, cursor:'pointer' }}>✕</button>
            </div>
            {[
              ['Actionability', selected.actionability > 0 ? '+' + (selected.actionability*100).toFixed(1)+'%' : (selected.actionability*100).toFixed(1)+'%', selected.actionability > 0 ? 'green' : selected.actionability < 0 ? 'red' : 'text-muted'],
              ['Evidence Score', selected.evidence + '/100', 'blue'],
              ['Impact Score',   selected.impact + '/10', 'red'],
              ['Sector',         selected.sector, 'text-muted'],
            ].map(([label, val, colorCls]) => (
              <div key={label} style={{ display:'flex', justifyContent:'space-between', padding:'10px 0', borderBottom:'1px solid rgba(255,255,255,0.04)' }}>
                <span style={{ color:'var(--text-muted)', fontSize:'0.85rem' }}>{label}</span>
                <span className={colorCls} style={{ fontWeight:700, fontFamily:'JetBrains Mono,monospace', fontSize:'0.9rem' }}>{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
