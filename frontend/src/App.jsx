// src/App.jsx — App Shell: header + sidebar + routing
import { useState, useEffect, useCallback, useRef } from 'react'
import { Activity, Zap, PlayCircle, BarChart2, ShieldAlert } from 'lucide-react'
import MarketRadar       from './pages/MarketRadar.jsx'
import EventIntelligence from './pages/EventIntelligence.jsx'
import EventReplay       from './pages/EventReplay.jsx'
import Portfolio         from './pages/Portfolio.jsx'
import MacroStressTest   from './pages/MacroStressTest.jsx'
import { api } from './api.js'
import { ToastContainer, toast } from './Toast.jsx'

const NAV = [
  { id:'radar',   label:'Market Radar',       icon: Activity,    comp: MarketRadar       },
  { id:'events',  label:'Event Intelligence',  icon: Zap,         comp: EventIntelligence },
  { id:'replay',  label:'Event Replay',        icon: PlayCircle,  comp: EventReplay       },
  { id:'portfolio',label:'Portfolio',          icon: BarChart2,   comp: Portfolio         },
  { id:'stress',  label:'Macro Stress Test',   icon: ShieldAlert, comp: MacroStressTest   },
]

const STATUS_SOURCES = ['GDELT', 'SEC', 'NLP', 'Social']

export default function App() {
  const [page, setPage]         = useState('radar')
  const [apiLive, setApiLive]   = useState(true)
  const [toggling, setToggling] = useState(false)
  const [apiOk, setApiOk]       = useState(true)
  const seenAlerts              = useRef(new Set())

  // Check API health on mount and start live stream ingestion
  useEffect(() => {
    api.health().then(async r => {
      setApiOk(!!r)
      if (r) {
        await api.liveStart()
      }
    })
  }, [])

  // ── Real-time event alert polling (every 6s when live) ──────────────
  useEffect(() => {
    if (!apiLive) return
    const poll = async () => {
      const r = await api.events({ limit: 20 })
      if (!r?.data) return
      r.data.forEach(evt => {
        const key = evt.id ?? `${evt.ticker}-${evt.ts}`
        if (seenAlerts.current.has(key)) return
        seenAlerts.current.add(key)
        if (evt.status === 'CONFIRMED' && !evt.abstained) {
          toast(
            `${evt.ticker} — ${evt.headline?.slice(0, 90) ?? 'Confirmed event detected'}`,
            {
              title: `🟢 CONFIRMED: ${evt.action} Signal`,
              type:  evt.action === 'SELL' ? 'sell' : 'confirm',
              duration: 7000,
            }
          )
        } else if (evt.impact >= 8 && evt.status !== 'WATCH') {
          toast(
            `${evt.ticker} high-impact event (${evt.impact}/10) — ${evt.event_type}`,
            { title: '⚠ High Impact Alert', type: 'alert', duration: 6000 }
          )
        }
      })
    }
    poll()
    const interval = setInterval(poll, 2_000)
    return () => clearInterval(interval)
  }, [apiLive])

  const handleSelectDemo = useCallback(() => {
    if (!apiLive) return;
    setApiLive(false);
    toast('Switched to Demo mode — using curated baseline dataset.', {
      title: '🔵 Demo Mode Active',
      type: 'info',
      duration: 3000,
    });
  }, [apiLive]);

  const handleSelectLive = useCallback(async () => {
    if (apiLive) return;
    if (toggling) return;
    setToggling(true);
    const h = await api.health();
    setApiOk(!!h);
    if (!h) {
      setToggling(false);
      toast('Backend not reachable — start uvicorn on port 8000 first.', {
        title: 'Connection Failed',
        type: 'alert',
        duration: 5000,
      });
      return;
    }
    await api.liveStart();
    setApiLive(true);
    setToggling(false);
    toast('Live mode activated — continuous market risk stream active.', {
      title: '🟢 Live Mode Active',
      type: 'confirm',
      duration: 4000,
    });
  }, [apiLive, toggling]);

  const ActivePage = NAV.find(n => n.id === page)?.comp ?? MarketRadar;

  return (
    <div className="app-shell">
      {/* ── Toast container (global) ── */}
      <ToastContainer />

      {/* ── Header ── */}
      <header className="header">
        <div className="header-logo">FinRisk AI</div>
        <div className="header-tagline">Event-Driven Financial Risk Intelligence</div>
        <div className="header-spacer"/>
        <div className="header-status">
          {STATUS_SOURCES.map((s, i) => (
            <span key={s} className={`status-dot ${i === 3 ? 'warn' : ''}`}>{s}</span>
          ))}

          {/* ── Two separate buttons: DEMO and LIVE ── */}
          <div
            id="mode-selector-container"
            style={{
              display: 'flex',
              alignItems: 'center',
              background: 'rgba(15, 23, 42, 0.75)',
              border: '1px solid rgba(148, 163, 184, 0.18)',
              borderRadius: 24,
              padding: '3px',
              gap: 4,
            }}
          >
            {/* DEMO BUTTON */}
            <button
              id="select-demo-btn"
              onClick={handleSelectDemo}
              title="Select Demo mode (offline baseline data)"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '5px 13px',
                borderRadius: 20,
                border: !apiLive
                  ? '1px solid rgba(99, 179, 237, 0.65)'
                  : '1px solid transparent',
                background: !apiLive
                  ? 'rgba(99, 179, 237, 0.2)'
                  : 'transparent',
                color: !apiLive ? '#63b3ed' : '#94a3b8',
                cursor: 'pointer',
                fontSize: '0.78rem',
                fontWeight: 700,
                letterSpacing: '0.04em',
                transition: 'all 0.2s ease',
                outline: 'none',
                boxShadow: !apiLive ? '0 0 10px rgba(99,179,237,0.25)' : 'none',
              }}
            >
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  background: !apiLive ? '#63b3ed' : '#64748b',
                  display: 'inline-block',
                }}
              />
              DEMO
            </button>

            {/* LIVE BUTTON */}
            <button
              id="select-live-btn"
              onClick={handleSelectLive}
              disabled={toggling}
              title="Select Live mode (real-time streaming market risk)"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '5px 13px',
                borderRadius: 20,
                border: apiLive
                  ? '1px solid rgba(72, 187, 120, 0.65)'
                  : '1px solid transparent',
                background: apiLive
                  ? 'rgba(72, 187, 120, 0.2)'
                  : 'transparent',
                color: apiLive ? '#48bb78' : '#94a3b8',
                cursor: toggling ? 'wait' : 'pointer',
                fontSize: '0.78rem',
                fontWeight: 700,
                letterSpacing: '0.04em',
                transition: 'all 0.2s ease',
                outline: 'none',
                boxShadow: apiLive ? '0 0 12px rgba(72,187,120,0.3)' : 'none',
              }}
            >
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  background: apiLive ? '#48bb78' : '#64748b',
                  boxShadow: apiLive
                    ? '0 0 0 0 rgba(72,187,120,0.5)'
                    : 'none',
                  animation: apiLive ? 'pulse-live 1.5s infinite' : 'none',
                  display: 'inline-block',
                }}
              />
              {toggling ? 'CONNECTING…' : 'LIVE'}
            </button>
          </div>
        </div>
      </header>

      {/* ── Sidebar ── */}
      <nav className="sidebar">
        <div className="sidebar-section-label">Navigation</div>
        {NAV.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`nav-item ${page === id ? 'active' : ''}`}
            onClick={() => setPage(id)}
            style={id === 'stress' ? { borderTop: '1px solid rgba(252,129,129,0.12)', marginTop: 6, paddingTop: 14 } : {}}
          >
            <Icon className="nav-icon" style={id === 'stress' ? { color: 'var(--red)' } : {}} />
            {label}
          </button>
        ))}

        <div className="sidebar-footer">
          {/* Mode info card */}
          <div className="universe-badge" style={{
            borderColor: apiLive ? 'rgba(72,187,120,0.25)' : 'rgba(99,179,237,0.15)',
          }}>
            <strong style={{ color: apiLive ? 'var(--green)' : 'var(--blue)' }}>
              {apiLive ? '🟢 Live Mode' : '🔵 Demo Mode'}
            </strong>
            <br/>
            {apiLive
              ? <>Data from live APIs<br/>Backend: <span style={{color:'var(--green)'}}>connected</span></>
              : <>Pre-saved demo data<br/>Select <strong>LIVE</strong> button to stream</>
            }
          </div>
          <div className="universe-badge" style={{marginTop:10}}>
            <strong>Prototype Universe</strong>
            15 large-cap stocks<br/>
            Extensible to 50/100
          </div>
        </div>
      </nav>

      {/* ── Main ── */}
      <main className="main-content">
        <ActivePage apiLive={apiLive} />
      </main>
    </div>
  )
}
