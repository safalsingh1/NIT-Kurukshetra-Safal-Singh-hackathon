// src/pages/EventIntelligence.jsx
import { useState, useEffect } from 'react';
import { Zap, Filter, RefreshCw } from 'lucide-react';
import { DEMO_EVENTS } from '../demoData';
import { api } from '../api.js';

const EVENT_TYPES = ['All', 'Earnings', 'M&A', 'Regulatory', 'Supply Chain', 'Product/Partnership', 'Legal', 'Cybersecurity'];

function ScoreBar({ value, max = 100, colorClass }) {
  return (
    <div className="score-bar-wrap">
      <div className="score-bar-track">
        <div className={`score-bar-fill ${colorClass}`} style={{ width: `${(value / max) * 100}%` }}/>
      </div>
      <span className={`score-val text-${colorClass === 'green' ? 'green' : colorClass === 'red' ? 'red' : 'blue'}`}>
        {value}{max === 10 ? '' : ''}
      </span>
    </div>
  );
}

function EventCard({ event, expanded, onToggle }) {
  const statusCls = event.status === 'CONFIRMED' ? 'confirmed' : event.status === 'DEVELOPING' ? 'developing' : 'watch';
  const actionBadge = event.abstained ? 'abstain' : event.action === 'BUY' ? 'buy' : event.action === 'SELL' ? 'sell' : 'hold';

  return (
    <div className="event-item animate-slidein" style={{ flexDirection: 'column', cursor: 'pointer' }} onClick={onToggle}>
      <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
        <span className={`event-dot ${statusCls}`} style={{ marginTop: 6 }}/>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 6 }}>
            <span style={{ fontWeight: 700, color: 'var(--blue)', marginRight: 8, fontSize: '0.9rem' }}>{event.ticker}</span>
            <span className={`badge badge-${statusCls}`}>{event.status}</span>
          </div>
          <div className="event-headline">{event.headline}</div>
          <div className="event-meta">
            <span><span className={`badge badge-type`}>{event.event_type}</span></span>
            <span style={{ fontFamily: 'JetBrains Mono', fontSize: '0.72rem' }}>{event.ts}</span>
            {event.abstained && <span className="badge badge-abstain">ABSTAINED</span>}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 5, flexShrink: 0 }}>
          <span className={`badge badge-${actionBadge}`}>{event.abstained ? 'HOLD' : event.action}</span>
          <span style={{ fontFamily: 'JetBrains Mono', fontSize: '0.75rem', color: event.impact >= 7 ? 'var(--red)' : 'var(--yellow)' }}>
            {event.impact}/10
          </span>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.06)' }} className="animate-fadeup">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 14 }}>
            {[
              { label: 'Evidence', value: event.evidence, max: 100, bar: true, colorClass: event.evidence >= 70 ? 'green' : event.evidence >= 40 ? 'yellow' : 'red' },
              { label: 'Novelty',  value: +(event.novelty * 100).toFixed(0), max: 100, bar: true, colorClass: 'blue' },
              { label: 'Attention Spike', value: event.spike + '×', max: null, bar: false },
            ].map(({ label, value, max, bar, colorClass }) => (
              <div key={label}>
                <div style={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
                {bar ? <ScoreBar value={value} max={max} colorClass={colorClass} /> : (
                  <div style={{ fontFamily: 'JetBrains Mono', fontWeight: 700, fontSize: '1rem', color: 'var(--yellow)' }}>{value}</div>
                )}
              </div>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            {[
              { label: 'Sentiment', value: (event.sentiment > 0 ? '+' : '') + event.sentiment.toFixed(2), color: event.sentiment > 0 ? 'var(--green)' : 'var(--red)' },
              { label: 'Confidence', value: (event.confidence * 100).toFixed(0) + '%', color: 'var(--blue)' },
              { label: 'Impact', value: event.impact + '/10', color: event.impact >= 7 ? 'var(--red)' : 'var(--yellow)' },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <div style={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
                <div style={{ fontFamily: 'JetBrains Mono', fontWeight: 700, fontSize: '1rem', color }}>{value}</div>
              </div>
            ))}
          </div>

          {event.abstained && (
            <div style={{ marginTop: 12, padding: '8px 14px', background: 'rgba(236,201,75,0.08)', border: '1px solid rgba(236,201,75,0.2)', borderRadius: 8, fontSize: '0.8rem', color: 'var(--yellow)' }}>
              ⚠ ABSTAINED — Evidence below 40/100 threshold. No portfolio action taken.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function EventIntelligence({ apiLive = false }) {
  const [expanded, setExpanded]       = useState(null);
  const [typeFilter, setTypeFilter]   = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [minImpact, setMinImpact]     = useState(0);
  const [liveEvents, setLiveEvents]   = useState(null);
  const [loading, setLoading]         = useState(false);

  useEffect(() => {
    if (!apiLive) { setLiveEvents(null); return; }
    const fetchEvents = (showLoader = false) => {
      if (showLoader) setLoading(true);
      api.events({}).then(r => setLiveEvents(r?.data ?? null)).finally(() => setLoading(false));
    };
    fetchEvents(true);
    // Refresh continuously every 1.5 seconds in live mode
    const interval = setInterval(() => fetchEvents(false), 1_500);
    return () => clearInterval(interval);
  }, [apiLive]);

  const allEvents = liveEvents ?? DEMO_EVENTS;

  const filtered = allEvents.filter(e =>
    (typeFilter === 'All' || e.event_type === typeFilter) &&
    (statusFilter === 'All' || e.status === statusFilter) &&
    e.impact >= minImpact
  );

  const confirmed = allEvents.filter(e => e.status === 'CONFIRMED').length;
  const developing = allEvents.filter(e => e.status === 'DEVELOPING').length;
  const watches = allEvents.filter(e => e.status === 'WATCH').length;

  return (
    <div className="animate-fadeup">
      <div className="page-header">
        <div className="page-title">
          <Zap size={22} style={{ color: 'var(--yellow)' }}/> Event Intelligence
          {loading && <RefreshCw size={14} style={{ color:'var(--text-muted)', animation:'spin 1s linear infinite', marginLeft:8 }}/>}
        </div>
        <div className="page-subtitle">
          {apiLive ? '🟢 Live events from GDELT + SEC EDGAR' : '🔵 Demo mode — Sentiment · Event Classification · Novelty · Attention Spike · Evidence · Impact'}
        </div>
      </div>

      {/* Status counts */}
      <div className="grid-3 mb-24">
        {[
          { label: 'CONFIRMED', count: confirmed, desc: 'Evidence ≥ 70/100 · Portfolio action permitted', cls: 'green' },
          { label: 'DEVELOPING', count: developing, desc: 'Evidence 40-69 · Monitor only · No action', cls: 'yellow' },
          { label: 'WATCH', count: watches, desc: 'Evidence < 40 · System ABSTAINED', cls: 'text-muted' },
        ].map(({ label, count, desc, cls }) => (
          <div key={label} className="metric-card">
            <div className="metric-label">{label}</div>
            <div className={`metric-value text-${cls}`}>{count}</div>
            <div className="metric-sub text-muted" style={{ fontSize: '0.75rem' }}>{desc}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <Filter size={15} style={{ color: 'var(--text-muted)' }}/>
        <select className="filter-select" value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
          {EVENT_TYPES.map(t => <option key={t}>{t}</option>)}
        </select>
        <select className="filter-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          {['All', 'CONFIRMED', 'DEVELOPING', 'WATCH'].map(s => <option key={s}>{s}</option>)}
        </select>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Min Impact: {minImpact}</span>
          <input type="range" min={0} max={9} step={0.5} value={minImpact} onChange={e => setMinImpact(+e.target.value)} className="styled-slider" style={{ width: 100 }}/>
        </div>
        <span style={{ marginLeft: 'auto', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{filtered.length} events</span>
      </div>

      {/* Event list */}
      <div>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>No events match the current filters</div>
        ) : (
          filtered.map(e => (
            <EventCard
              key={e.id}
              event={e}
              expanded={expanded === e.id}
              onToggle={() => setExpanded(expanded === e.id ? null : e.id)}
            />
          ))
        )}
      </div>

      {/* Pipeline note */}
      <div className="card" style={{ marginTop: 24, background: 'rgba(99,179,237,0.03)', borderColor: 'rgba(99,179,237,0.1)' }}>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
          <strong style={{ color: 'var(--blue)' }}>Evidence Gate:</strong> The system computes an availability-aware evidence score across News (GDELT), SEC EDGAR filings, and Social. Sources are renormalised based on what's available — a product launch (no SEC filing) is NOT penalised for missing SEC data.
          Scores below 40/100 trigger automatic abstention, preventing rumours from influencing portfolio weights.
        </div>
      </div>
    </div>
  );
}
