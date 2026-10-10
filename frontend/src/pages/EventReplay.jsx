// src/pages/EventReplay.jsx
import { useState, useEffect, useMemo, useRef } from 'react';
import { PlayCircle, Activity, Radio, RefreshCw, Zap, Pause, Play } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';
import { REPLAY_SCENARIOS } from '../demoData';
import { api } from '../api';

const SCENARIO_KEYS = Object.keys(REPLAY_SCENARIOS);

const STATUS_CONFIG = {
  watch:      { dotCls: 'watch',      label: 'HOLD',     color: 'var(--text-muted)',   icon: '⚪' },
  developing: { dotCls: 'developing', label: 'MONITOR',  color: 'var(--yellow)',        icon: '🟡' },
  rebalance:  { dotCls: 'rebalance',  label: 'BUY',      color: 'var(--green)',         icon: '🟢' },
  sell:       { dotCls: 'sell',       label: 'SELL',      color: 'var(--red)',           icon: '🔴' },
};

function formatSignalToStep(s, i, prevWeight = 8.0) {
  const timeStr = s.timestamp
    ? new Date(s.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : `T+${i + 1}`;
  
  const dir = s.signal?.direction || 'HOLD';
  const evScore = Math.round(s.evidence?.score ?? 0);
  const actionability = s.signal?.actionability || 0;
  
  let status = 'watch';
  let action = 'HOLD';
  if (dir === 'BUY') {
    status = 'rebalance';
    action = 'REBALANCE — BUY';
  } else if (dir === 'SELL') {
    status = 'sell';
    action = 'REBALANCE — SELL';
  } else if (evScore >= 40) {
    status = 'developing';
    action = 'MONITOR';
  }

  const weightDelta = dir === 'BUY' ? +1.2 : dir === 'SELL' ? -1.5 : 0;
  const weightAfter = Math.max(1.0, Math.min(20.0, +(prevWeight + weightDelta).toFixed(1)));

  return {
    time: timeStr,
    source: s.source ? `${s.source} (${s.ticker})` : `${s.ticker} Live Stream`,
    ticker: s.ticker || 'MARKET',
    status,
    action,
    headline: s.text || `${s.ticker} signal detected`,
    sentiment: +(s.sentiment?.score || 0).toFixed(2),
    novelty: +(s.novelty?.score || 1.0).toFixed(2),
    evidence: evScore,
    impact: +(s.impact?.score || 0).toFixed(1),
    abstained: !!s.signal?.abstained,
    abstainReason: s.signal?.abstain_reason || (evScore < 40 ? `Evidence ${evScore}/100 < 40 threshold` : ''),
    actionability: +(actionability).toFixed(3),
    weightBefore: prevWeight,
    weightAfter: weightAfter,
  };
}

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
  if (!steps || steps.length === 0) return null;
  const data = steps.map((s) => ({ time: s.time, weight: s.weightBefore }));
  data.push({ time: 'Current', weight: steps[steps.length - 1].weightAfter });

  const initial = steps[0].weightBefore;
  const final   = steps[steps.length - 1].weightAfter;
  const isUp    = final >= initial;

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
            {step.ticker && (
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--blue)', background: 'rgba(99,179,237,0.1)', padding: '2px 6px', borderRadius: 4 }}>
                {step.ticker}
              </span>
            )}
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
          <div style={{ padding: '8px 12px', background: 'rgba(236,201,75,0.07)', border: '1px solid rgba(236,201,75,0.2)', borderRadius: 8, fontSize: '0.78rem', color: 'var(--yellow)', marginTop: 8 }}>
            ⚠ ABSTAINED: {step.abstainReason}
          </div>
        )}

        {step.action.includes('REBALANCE') && (
          <div className={`replay-action ${step.action.includes('BUY') ? 'buy' : 'sell'}`} style={{ marginTop: 8 }}>
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

const LIVE_STREAM_SCENARIO_KEY = '🔴 Live Stream (Real-Time)';

export default function EventReplay({ apiLive = false }) {
  const [liveSignals, setLiveSignals] = useState([]);
  const [scenario, setScenario] = useState(() => (apiLive ? LIVE_STREAM_SCENARIO_KEY : SCENARIO_KEYS[0]));
  const [stepIdx, setStepIdx] = useState(1);
  const [autoFollow, setAutoFollow] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const prevStepCountRef = useRef(0);

  // Poll live signals continuously when in Live mode
  useEffect(() => {
    if (!apiLive) return;

    let mounted = true;
    const fetchLive = async () => {
      try {
        const res = await api.signals();
        if (!mounted || !res) return;
        const sigs = Array.isArray(res) ? res : (res?.data ?? res?.signals ?? []);
        if (Array.isArray(sigs) && sigs.length > 0) {
          setLiveSignals(sigs);
          setLastUpdated(new Date().toLocaleTimeString());
        }
      } catch {
        // network silent
      }
    };

    fetchLive();
    const timer = setInterval(fetchLive, 1500);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [apiLive]);

  // When switching modes, set default scenario
  useEffect(() => {
    if (apiLive) {
      setScenario(LIVE_STREAM_SCENARIO_KEY);
      setAutoFollow(true);
    } else {
      setScenario(SCENARIO_KEYS[0]);
    }
  }, [apiLive]);

  // Build dynamic scenario lists with Live Stream first when in live mode
  const scenariosData = useMemo(() => {
    const map = {};

    if (apiLive) {
      // 1. Full chronologically ordered live stream scenario (accumulate up to recent 25 signals)
      if (liveSignals.length > 0) {
        const recent = [...liveSignals].slice(-25);
        let runningWeight = 8.0;
        map[LIVE_STREAM_SCENARIO_KEY] = recent.map((s, idx) => {
          const step = formatSignalToStep(s, idx, runningWeight);
          runningWeight = step.weightAfter;
          return step;
        });

        // 2. Individual live ticker series for tickers with multiple updates
        const byTicker = {};
        liveSignals.forEach(s => {
          if (!s.ticker) return;
          if (!byTicker[s.ticker]) byTicker[s.ticker] = [];
          byTicker[s.ticker].push(s);
        });

        Object.entries(byTicker).forEach(([tick, sigs]) => {
          if (sigs.length >= 2) {
            const key = `🟢 ${tick} (Live Series)`;
            let tw = 8.0;
            map[key] = sigs.slice(-10).map((s, idx) => {
              const step = formatSignalToStep(s, idx, tw);
              tw = step.weightAfter;
              return step;
            });
          }
        });
      } else {
        // Initial empty live stream placeholder while loading first signals
        map[LIVE_STREAM_SCENARIO_KEY] = [];
      }
    }

    // Historical benchmark scenarios
    SCENARIO_KEYS.forEach(key => {
      map[key] = REPLAY_SCENARIOS[key];
    });

    return map;
  }, [apiLive, liveSignals]);

  const liveScenarioKeys = useMemo(() => {
    return Object.keys(scenariosData).filter(k => k.includes('Live') || k.includes('🔴') || k.includes('🟢'));
  }, [scenariosData]);

  // Current steps
  const steps = scenariosData[scenario] || scenariosData[LIVE_STREAM_SCENARIO_KEY] || scenariosData[SCENARIO_KEYS[0]] || [];
  const latestTimestamp = steps[steps.length - 1]?.time;

  // Auto-follow: if autoFollow is active or new step arrives, update stepIdx to latest
  useEffect(() => {
    if (steps.length === 0) return;
    if (autoFollow || stepIdx > steps.length || prevStepCountRef.current === 0) {
      setStepIdx(steps.length);
    }
    prevStepCountRef.current = steps.length;
  }, [steps.length, latestTimestamp, autoFollow]);

  const visible   = steps.slice(0, stepIdx);
  const ticker    = scenario.includes('Live') ? (visible[visible.length - 1]?.ticker || 'PORTFOLIO') : scenario.split(' ')[0];
  const lastStep  = steps[steps.length - 1] || { evidence: 0, impact: 0, action: 'HOLD' };
  const currentStep = visible[visible.length - 1] || lastStep;

  const handleScenario = (s) => {
    setScenario(s);
    const count = scenariosData[s]?.length || 1;
    setStepIdx(count);
    if (s.includes('Live')) {
      setAutoFollow(true);
    }
  };

  const handleSliderChange = (e) => {
    const val = +e.target.value;
    setStepIdx(val);
    if (val < steps.length && scenario.includes('Live')) {
      setAutoFollow(false); // pause auto-follow while scrubbing past events
    }
  };

  return (
    <div className="animate-fadeup">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <PlayCircle size={22} style={{ color: 'var(--purple)' }}/>
            Event Replay
            {apiLive && (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                fontSize: '0.72rem',
                color: 'var(--green)',
                background: 'rgba(72,187,120,0.12)',
                border: '1px solid rgba(72,187,120,0.3)',
                padding: '3px 9px',
                borderRadius: 16,
                fontWeight: 600,
                letterSpacing: '0.04em'
              }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 8px var(--green)' }}/>
                LIVE REPLAY STREAMING
              </span>
            )}
          </div>
          <div className="page-subtitle">
            Reconstruct signal evolution from initial rumour to confirmed portfolio action
            {apiLive ? (
              <span style={{ marginLeft: 8, color: 'var(--text-secondary)' }}>
                · Streaming live signals in real-time {lastUpdated && `(last update ${lastUpdated})`}
              </span>
            ) : (
              <span style={{ marginLeft: 8, fontSize: '0.75rem', color: 'var(--blue)', background: 'rgba(99,179,237,0.1)', border: '1px solid rgba(99,179,237,0.25)', padding: '2px 8px', borderRadius: 12 }}>
                Deterministic Scenario Simulator
              </span>
            )}
          </div>
        </div>

        {/* Live controls toolbar */}
        {apiLive && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              className="btn btn-outline"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: '0.78rem',
                padding: '5px 12px',
                borderColor: autoFollow ? 'rgba(72,187,120,0.4)' : 'rgba(236,201,75,0.4)',
                color: autoFollow ? 'var(--green)' : 'var(--yellow)',
                background: autoFollow ? 'rgba(72,187,120,0.08)' : 'rgba(236,201,75,0.08)',
              }}
              onClick={() => {
                const next = !autoFollow;
                setAutoFollow(next);
                if (next) setStepIdx(steps.length);
              }}
            >
              {autoFollow ? <Play size={13} fill="currentColor"/> : <Pause size={13} fill="currentColor"/>}
              {autoFollow ? 'Auto-Following Live' : 'Paused (Click to Follow)'}
            </button>
            <button
              className="btn btn-outline"
              style={{ fontSize: '0.78rem', padding: '5px 10px' }}
              onClick={() => {
                setStepIdx(steps.length);
                setAutoFollow(true);
              }}
              title="Jump slider to latest incoming event"
            >
              Latest Step ⏭
            </button>
          </div>
        )}
      </div>

      {/* Banner if viewing static benchmark while in Live mode */}
      {apiLive && !scenario.includes('Live') && (
        <div style={{
          padding: '10px 16px',
          background: 'rgba(99,179,237,0.08)',
          border: '1px solid rgba(99,179,237,0.25)',
          borderRadius: 8,
          marginBottom: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 10
        }}>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            ℹ You are currently inspecting a <strong>static benchmark scenario</strong> ({scenario}). Real-time live market events stream in the <strong>Live Stream</strong> view.
          </span>
          <button
            className="btn btn-primary"
            style={{ padding: '5px 12px', fontSize: '0.78rem', background: 'var(--green)', borderColor: 'var(--green)' }}
            onClick={() => handleScenario(LIVE_STREAM_SCENARIO_KEY)}
          >
            🔴 Switch to Live Stream Replay
          </button>
        </div>
      )}

      {/* Informational intro */}
      <div style={{
        background: apiLive ? 'rgba(72,187,120,0.04)' : 'rgba(99,179,237,0.04)',
        border: `1px solid ${apiLive ? 'rgba(72,187,120,0.18)' : 'rgba(99,179,237,0.1)'}`,
        borderRadius: 10,
        padding: '12px 16px',
        marginBottom: 20,
        fontSize: '0.82rem',
        color: 'var(--text-secondary)'
      }}>
        {apiLive ? (
          <>
            <strong>🔴 Live Event Replay Active:</strong> Ingesting signals from the live pipeline. The timeline and charts advance in real time as each piece of news is evaluated for evidence corroboration, sentiment, and actionability.
          </>
        ) : (
          <>
            Select a benchmark scenario below. Drag the slider to replay step-by-step how FinRisk AI processed each piece of information — <strong>when it held back</strong> (insufficient evidence), and <strong>when confirmation triggered a portfolio decision</strong>.
          </>
        )}
      </div>

      {/* Scenario selectors */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20 }}>
        {apiLive && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--green)', letterSpacing: '0.04em' }}>
              ● LIVE REPLAY:
            </span>
            {liveScenarioKeys.map(key => (
              <button
                key={key}
                className={`btn ${scenario === key ? 'btn-primary' : 'btn-outline'}`}
                style={{
                  borderColor: scenario === key ? 'var(--green)' : 'rgba(72,187,120,0.3)',
                  color: scenario === key ? '#fff' : 'var(--green)',
                  background: scenario === key ? 'var(--green)' : 'transparent',
                }}
                onClick={() => handleScenario(key)}
              >
                {key} {scenariosData[key]?.length > 0 && `(${scenariosData[key].length} steps)`}
              </button>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
            📚 BENCHMARKS:
          </span>
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
      </div>

      {/* Step slider */}
      <div className="card mb-24">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>Showing step <strong style={{ color: 'var(--text-primary)' }}>{stepIdx}</strong> of {steps.length}</span>
            {scenario.includes('Live') && autoFollow && (
              <span style={{ fontSize: '0.72rem', color: 'var(--green)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <Radio size={12} className="animate-pulse" /> Auto-stepping as new signals arrive
              </span>
            )}
            {scenario.includes('Live') && !autoFollow && (
              <span style={{ fontSize: '0.72rem', color: 'var(--yellow)', cursor: 'pointer' }} onClick={() => { setStepIdx(steps.length); setAutoFollow(true); }}>
                (Scrubbing history · click to resume auto-follow)
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn btn-outline"
              style={{ padding: '5px 10px', fontSize: '0.75rem' }}
              onClick={() => {
                setStepIdx(Math.max(1, stepIdx - 1));
                if (scenario.includes('Live')) setAutoFollow(false);
              }}
              disabled={stepIdx <= 1}
            >
              ← Prev
            </button>
            <button
              className="btn btn-outline"
              style={{ padding: '5px 10px', fontSize: '0.75rem' }}
              onClick={() => {
                const next = Math.min(steps.length, stepIdx + 1);
                setStepIdx(next);
                if (next === steps.length && scenario.includes('Live')) setAutoFollow(true);
              }}
              disabled={stepIdx >= steps.length}
            >
              Next →
            </button>
          </div>
        </div>
        <input
          type="range"
          min={1}
          max={Math.max(1, steps.length)}
          value={stepIdx}
          onChange={handleSliderChange}
          className="styled-slider"
        />
      </div>

      {/* Timeline Steps */}
      <div className="section">
        {visible.length === 0 ? (
          <div className="card text-center" style={{ padding: 40, color: 'var(--text-muted)' }}>
            <Activity size={32} style={{ margin: '0 auto 12px', opacity: 0.5 }}/>
            <div>Waiting for incoming stream signals...</div>
          </div>
        ) : (
          visible.map((step, i) => (
            <ReplayStep
              key={i}
              step={step}
              stepNum={i + 1}
              total={steps.length}
              isActive={i === stepIdx - 1}
            />
          ))
        )}
      </div>

      {/* Summary metrics for current/inspected step */}
      <div className="grid-3 mb-24">
        <div className="metric-card">
          <div className="metric-label">{stepIdx === steps.length ? 'Latest Evidence' : `Step ${stepIdx} Evidence`}</div>
          <div className={`metric-value text-${currentStep.evidence >= 70 ? 'green' : currentStep.evidence >= 40 ? 'yellow' : 'muted'}`}>
            {currentStep.evidence}<span style={{ fontSize: '1rem' }}>/100</span>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">{stepIdx === steps.length ? 'Latest Impact' : `Step ${stepIdx} Impact`}</div>
          <div className="metric-value text-red">{currentStep.impact}<span style={{ fontSize: '1rem' }}>/10</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Decision Outcome</div>
          <div className="metric-value" style={{ fontSize: '1rem', color: currentStep.action.includes('BUY') ? 'var(--green)' : currentStep.action.includes('SELL') ? 'var(--red)' : 'var(--text-muted)' }}>
            {currentStep.action.split(' — ')[0]}
          </div>
        </div>
      </div>

      {/* Charts */}
      {visible.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          <div className="card">
            <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>SIGNAL EVOLUTION</span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{visible.length} points</span>
            </div>
            <SignalEvolutionChart steps={visible}/>
          </div>
          <div className="card">
            <div className="card-title">{ticker} SIMULATED WEIGHT EVOLUTION</div>
            <WeightChart steps={visible} ticker={ticker}/>
            <div style={{ marginTop: 12, fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center' }}>
              {visible[0].weightBefore.toFixed(1)}% → {currentStep.weightAfter.toFixed(1)}%
              <span style={{ color: currentStep.weightAfter >= visible[0].weightBefore ? 'var(--green)' : 'var(--red)', marginLeft: 8, fontWeight: 700 }}>
                ({currentStep.weightAfter >= visible[0].weightBefore ? '+' : ''}{(currentStep.weightAfter - visible[0].weightBefore).toFixed(1)}pp)
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

