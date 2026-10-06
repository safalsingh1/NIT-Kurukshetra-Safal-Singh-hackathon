// src/pages/EventReplay.jsx
import { useState } from 'react';
import { PlayCircle, ChevronRight } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';
import { REPLAY_SCENARIOS } from '../demoData';

const SCENARIO_KEYS = Object.keys(REPLAY_SCENARIOS);

const STATUS_CONFIG = {
  watch:      { dotCls: 'watch',      label: 'HOLD',     color: 'var(--text-muted)',   icon: '⚪' },
  developing: { dotCls: 'developing', label: 'MONITOR',  color: 'var(--yellow)',        icon: '🟡' },
  rebalance:  { dotCls: 'rebalance',  label: 'BUY',      color: 'var(--green)',         icon: '🟢' },
  sell:       { dotCls: 'sell',       label: 'SELL',      color: 'var(--red)',           icon: '🔴' },
};

function SignalEvolutionChart({ steps }) {
  const data = steps.map(s => ({
    time:     s.time,
    Evidence: s.evidence,
    Impact:   +(s.impact * 10).toFixed(1),
    Novelty:  +(s.novelty * 100).toFixed(0),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: -16 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3"/>
        <XAxis dataKey="time" tick={{ fill: '#4a5568', fontSize: 11 }}/>
        <YAxis domain={[0, 105]} tick={{ fill: '#4a5568', fontSize: 10 }}/>
        <Tooltip contentStyle={{ background: '#0d1224', border: '1px solid rgba(99,179,237,0.2)', borderRadius: 8, fontSize: '0.8rem' }}/>
        <Legend wrapperStyle={{ fontSize: '0.78rem', paddingTop: 8 }}/>
        <ReferenceLine y={70} stroke="rgba(72,187,120,0.5)" strokeDasharray="5 5" label={{ value: 'Action Threshold (70)', fill: '#48bb78', fontSize: 10, position: 'insideBottomRight' }}/>
        <ReferenceLine y={40} stroke="rgba(236,201,75,0.35)" strokeDasharray="5 5" label={{ value: 'Developing (40)', fill: '#ecc94b', fontSize: 10, position: 'insideBottomRight' }}/>
        <Line type="monotone" dataKey="Evidence" stroke="#48bb78" strokeWidth={2.5} dot={{ r: 5, strokeWidth: 2 }}/>
        <Line type="monotone" dataKey="Impact"   stroke="#fc8181" strokeWidth={2}   dot={{ r: 4, strokeWidth: 2 }}/>
        <Line type="monotone" dataKey="Novelty"  stroke="#9f7aea" strokeWidth={2}   dot={{ r: 4, strokeWidth: 2 }}/>
      </LineChart>
    </ResponsiveContainer>
  );
}

function WeightChart({ steps, ticker }) {
  const data = steps.map((s, i) => ({ time: s.time, weight: s.weightBefore }));
  data.push({ time: 'Final', weight: steps[steps.length - 1].weightAfter });

  const initial = steps[0].weightBefore;
  const final   = steps[steps.length - 1].weightAfter;
  const isUp    = final > initial;

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: -16 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3"/>
        <XAxis dataKey="time" tick={{ fill: '#4a5568', fontSize: 11 }}/>
        <YAxis domain={[0, 20]} tick={{ fill: '#4a5568', fontSize: 10 }}/>
        <Tooltip
          formatter={v => [v.toFixed(1) + '%', `${ticker} Weight`]}
          contentStyle={{ background: '#0d1224', border: '1px solid rgba(99,179,237,0.2)', borderRadius: 8, fontSize: '0.8rem' }}
        />
        <ReferenceLine y={initial} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4" label={{ value: 'Initial', fill: '#718096', fontSize: 9 }}/>
        <Line
          type="monotone"
          dataKey="weight"
          stroke={isUp ? '#48bb78' : '#fc8181'}
          strokeWidth={2.5}
          dot={(props) => {
            const isLast = props.index === data.length - 1;
            return <circle key={props.index} cx={props.cx} cy={props.cy} r={isLast ? 7 : 4} fill={isUp ? '#48bb78' : '#fc8181'} stroke="white" strokeWidth={2}/>;
          }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function ReplayStep({ step, stepNum, total, isActive }) {
  const cfg = STATUS_CONFIG[step.status] || STATUS_CONFIG.watch;

  return (
    <div className="replay-step">
      <div className={`replay-dot ${step.status}`}>{cfg.icon}</div>
      <div className={`replay-card ${isActive ? 'active' : ''}`}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <span style={{ fontFamily: 'JetBrains Mono', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Step {stepNum}/{total} · {step.time}
            </span>
            <span className="badge badge-type">{step.action.split(' ')[0]}</span>
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{step.source}</span>
        </div>

        <div className="replay-headline">"{step.headline}"</div>

        <div className="replay-signals">
          {[
            { label: 'Sentiment',  value: (step.sentiment > 0 ? '+' : '') + step.sentiment.toFixed(2), color: step.sentiment > 0 ? 'var(--green)' : 'var(--red)' },
            { label: 'Novelty',    value: step.novelty.toFixed(2),   color: 'var(--purple)' },
            { label: 'Evidence',   value: step.evidence + '/100',    color: step.evidence >= 70 ? 'var(--green)' : step.evidence >= 40 ? 'var(--yellow)' : 'var(--text-muted)' },
            { label: 'Impact',     value: step.impact + '/10',       color: step.impact >= 7 ? 'var(--red)' : 'var(--yellow)' },
            { label: 'Action',     value: step.action.split(' ')[0], color: cfg.color },
          ].map(({ label, value, color }) => (
            <div key={label} className="replay-signal-item">
              <div className="replay-signal-label">{label}</div>
              <div className="replay-signal-value" style={{ color }}>{value}</div>
            </div>
          ))}
        </div>

        {step.abstained && (
          <div style={{ padding: '8px 12px', background: 'rgba(236,201,75,0.07)', border: '1px solid rgba(236,201,75,0.2)', borderRadius: 8, fontSize: '0.78rem', color: 'var(--yellow)' }}>
            ⚠ ABSTAINED: {step.abstainReason}
          </div>
        )}

        {step.action.includes('REBALANCE') && (
          <div className={`replay-action ${step.action.includes('BUY') ? 'buy' : 'sell'}`}>
            <span>Portfolio Decision: weight {step.weightBefore.toFixed(1)}% → <strong>{step.weightAfter.toFixed(1)}%</strong></span>
            <span style={{ fontFamily: 'JetBrains Mono' }}>
              Actionability: {step.actionability > 0 ? '+' : ''}{step.actionability.toFixed(3)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function EventReplay({ apiLive = false }) {
  const [scenario, setScenario] = useState(SCENARIO_KEYS[0]);
  const [stepIdx, setStepIdx] = useState(() => REPLAY_SCENARIOS[SCENARIO_KEYS[0]].length);

  const steps     = REPLAY_SCENARIOS[scenario];
  const visible   = steps.slice(0, stepIdx);
  const ticker    = scenario.split(' ')[0];
  const lastStep  = steps[steps.length - 1];

  const handleScenario = (s) => {
    setScenario(s);
    setStepIdx(REPLAY_SCENARIOS[s].length);
  };

  return (
    <div className="animate-fadeup">
      <div className="page-header">
        <div className="page-title"><PlayCircle size={22} style={{ color: 'var(--purple)' }}/> Event Replay</div>
        <div className="page-subtitle">
          Reconstruct signal evolution from initial rumour to confirmed portfolio action
          {apiLive && <span style={{ marginLeft: 8, fontSize: '0.75rem', color: 'var(--purple)', background: 'rgba(159,122,234,0.12)', border: '1px solid rgba(159,122,234,0.3)', padding: '2px 8px', borderRadius: 12 }}>Deterministic Scenario Simulator</span>}
        </div>
      </div>

      <div style={{ background: 'rgba(99,179,237,0.04)', border: '1px solid rgba(99,179,237,0.1)', borderRadius: 10, padding: '12px 16px', marginBottom: 24, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
        Select a scenario below. Drag the slider to replay step-by-step how FinRisk AI processed each piece of information — <strong>when it held back</strong> (insufficient evidence), and <strong>when confirmation triggered a portfolio decision</strong>.
      </div>

      {/* Scenario selector */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 24, flexWrap: 'wrap' }}>
        {SCENARIO_KEYS.map(key => (
          <button
            key={key}
            className={`btn ${scenario === key ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => handleScenario(key)}
          >
            {key}
          </button>
        ))}
      </div>

      {/* Step slider */}
      <div className="card mb-24">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Showing step <strong style={{ color: 'var(--text-primary)' }}>{stepIdx}</strong> of {steps.length}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-outline" style={{ padding: '5px 10px', fontSize: '0.75rem' }} onClick={() => setStepIdx(Math.max(1, stepIdx - 1))} disabled={stepIdx <= 1}>← Prev</button>
            <button className="btn btn-outline" style={{ padding: '5px 10px', fontSize: '0.75rem' }} onClick={() => setStepIdx(Math.min(steps.length, stepIdx + 1))} disabled={stepIdx >= steps.length}>Next →</button>
          </div>
        </div>
        <input
          type="range" min={1} max={steps.length} value={stepIdx}
          onChange={e => setStepIdx(+e.target.value)}
          className="styled-slider"
        />
      </div>

      {/* Timeline */}
      <div className="section">
        {visible.map((step, i) => (
          <ReplayStep key={i} step={step} stepNum={i + 1} total={steps.length} isActive={i === stepIdx - 1}/>
        ))}
      </div>

      {/* Summary metrics */}
      <div className="grid-3 mb-24">
        <div className="metric-card">
          <div className="metric-label">Final Evidence</div>
          <div className={`metric-value text-${lastStep.evidence >= 70 ? 'green' : 'yellow'}`}>{lastStep.evidence}<span style={{ fontSize: '1rem' }}>/100</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Final Impact</div>
          <div className="metric-value text-red">{lastStep.impact}<span style={{ fontSize: '1rem' }}>/10</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Portfolio Decision</div>
          <div className="metric-value" style={{ fontSize: '1rem', color: lastStep.action.includes('BUY') ? 'var(--green)' : lastStep.action.includes('SELL') ? 'var(--red)' : 'var(--text-muted)' }}>
            {lastStep.action.split(' — ')[0]}
          </div>
        </div>
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div className="card">
          <div className="card-title">SIGNAL EVOLUTION</div>
          <SignalEvolutionChart steps={visible.length > 0 ? visible : steps}/>
        </div>
        <div className="card">
          <div className="card-title">{ticker} PORTFOLIO WEIGHT</div>
          <WeightChart steps={steps} ticker={ticker}/>
          <div style={{ marginTop: 12, fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center' }}>
            {steps[0].weightBefore.toFixed(1)}% → {lastStep.weightAfter.toFixed(1)}%
            <span style={{ color: lastStep.weightAfter > steps[0].weightBefore ? 'var(--green)' : 'var(--red)', marginLeft: 8, fontWeight: 700 }}>
              ({lastStep.weightAfter > steps[0].weightBefore ? '+' : ''}{(lastStep.weightAfter - steps[0].weightBefore).toFixed(1)}pp)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
