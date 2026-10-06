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
  const [apiLive, setApiLive]   = useState(false)
  const [toggling, setToggling] = useState(false)
  const [apiOk, setApiOk]       = useState(false)
  const seenAlerts              = useRef(new Set())

  // Check API health on mount
  useEffect(() => {
    api.health().then(r => setApiOk(!!r))
  }, [])

  // ── Real-time event alert polling (every 15s when live) ──────────────
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
    const interval = setInterval(poll, 15_000)
    return () => clearInterval(interval)
  }, [apiLive])

  const handleModeToggle = useCallback(async () => {
    if (toggling) return
    setToggling(true)
    if (!apiLive) {
      const h = await api.health()
      setApiOk(!!h)
      if (!h) {
        setToggling(false)
        toast('Backend not reachable — start uvicorn on port 8000 first.', { title: 'Connection Failed', type: 'alert', duration: 5000 })
        return
      }
      toast('Live mode activated — monitoring GDELT & SEC EDGAR for confirmed events.', { title: '🟢 Live Mode On', type: 'confirm', duration: 4000 })
    } else {
      toast('Switched to demo mode.', { title: '🔵 Demo Mode', type: 'info', duration: 3000 })
    }
    setApiLive(v => !v)
    setToggling(false)
  }, [apiLive, toggling])

  const ActivePage = NAV.find(n => n.id === page)?.comp ?? MarketRadar

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

          {/* ── Live / Demo toggle ── */}
          <button
            id="mode-toggle-btn"
            onClick={handleModeToggle}
            disabled={toggling}
            title={apiLive ? 'Switch to Demo mode' : apiOk ? 'Switch to Live mode' : 'Backend unavailable — start uvicorn first'}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 7,
              padding: '5px 14px',
              borderRadius: 20,
              border: `1px solid ${apiLive ? 'rgba(72,187,120,0.5)' : 'rgba(99,179,237,0.3)'}`,
              background: apiLive
                ? 'rgba(72,187,120,0.12)'
                : 'rgba(99,179,237,0.08)',
              color: apiLive ? 'var(--green)' : 'var(--blue)',
              cursor: toggling ? 'wait' : 'pointer',
              fontSize: '0.78rem',
              fontWeight: 700,
              letterSpacing: '0.06em',
              transition: 'all 0.25s ease',
              outline: 'none',
              opacity: toggling ? 0.6 : 1,
            }}
          >
            {/* pulse dot */}
            <span style={{
              width: 7, height: 7, borderRadius: '50%',
              background: apiLive ? 'var(--green)' : 'var(--blue)',
              boxShadow: apiLive
                ? '0 0 0 0 rgba(72,187,120,0.4)'
                : '0 0 0 0 rgba(99,179,237,0.4)',
              animation: apiLive ? 'pulse-live 1.5s infinite' : 'none',
              display: 'inline-block',
              flexShrink: 0,
            }}/>
            {toggling ? 'CONNECTING…' : apiLive ? 'LIVE' : 'DEMO'}
          </button>
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
              : <>Pre-saved demo data<br/>Click <strong>DEMO</strong> button to go live</>
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
