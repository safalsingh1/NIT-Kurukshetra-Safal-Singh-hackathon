// src/Toast.jsx — institutional notification center & lightweight toast engine
import { useState, useEffect, useCallback, useRef } from 'react';
import { X, AlertTriangle, TrendingUp, TrendingDown, Bell, BellOff, CheckCheck, Trash2, Sliders } from 'lucide-react';

const ICON_MAP = {
  confirm: TrendingUp,
  sell:    TrendingDown,
  alert:   AlertTriangle,
  info:    Bell,
};

const COLOR_MAP = {
  confirm: { border: 'rgba(72,187,120,0.5)',  bg: 'rgba(72,187,120,0.08)',  text: '#48bb78', badge: 'rgba(72,187,120,0.15)' },
  sell:    { border: 'rgba(252,129,129,0.5)', bg: 'rgba(252,129,129,0.08)', text: '#fc8181', badge: 'rgba(252,129,129,0.15)' },
  alert:   { border: 'rgba(236,201,75,0.5)',  bg: 'rgba(236,201,75,0.08)',  text: '#ecc94b', badge: 'rgba(236,201,75,0.15)' },
  info:    { border: 'rgba(99,179,237,0.5)',   bg: 'rgba(99,179,237,0.08)',  text: '#63b3ed', badge: 'rgba(99,179,237,0.15)' },
};

// Global state store for toasts & history
let _listeners = new Set();
let _activeToasts = [];
let _history = [];
let _isMuted = false;
let _unreadCount = 0;

function notifyListeners() {
  _listeners.forEach(cb => cb({
    toasts: [..._activeToasts],
    history: [..._history],
    isMuted: _isMuted,
    unreadCount: _unreadCount,
  }));
}

export function toast(message, opts = {}) {
  const { type = 'info', title = '', duration = 3800 } = opts;
  const id = Date.now() + Math.random();
  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  const item = { id, message, type, title, duration, timeStr, read: false };

  // Always log to history (up to 40 items)
  _history = [item, ..._history.slice(0, 39)];
  _unreadCount += 1;

  // If not muted, push to active on-screen toasts (max 2 at a time to prevent blocking)
  if (!_isMuted) {
    _activeToasts = [..._activeToasts.slice(-1), item];
    if (duration > 0) {
      setTimeout(() => {
        _activeToasts = _activeToasts.filter(t => t.id !== id);
        notifyListeners();
      }, duration);
    }
  }

  notifyListeners();
}

export function dismissToast(id) {
  _activeToasts = _activeToasts.filter(t => t.id !== id);
  notifyListeners();
}

export function dismissAllToasts() {
  _activeToasts = [];
  notifyListeners();
}

export function toggleMutePopups() {
  _isMuted = !_isMuted;
  if (_isMuted) {
    _activeToasts = [];
  }
  notifyListeners();
  return _isMuted;
}

export function clearAlertHistory() {
  _history = [];
  _unreadCount = 0;
  _activeToasts = [];
  notifyListeners();
}

export function markAllAsRead() {
  _history = _history.map(h => ({ ...h, read: true }));
  _unreadCount = 0;
  notifyListeners();
}

/**
 * Top-Right Compact Toast Container
 * Positioned at top: 72px (below header) to completely avoid blocking bottom graphs
 */
export function ToastContainer() {
  const [state, setState] = useState({
    toasts: _activeToasts,
    isMuted: _isMuted,
  });

  useEffect(() => {
    const handler = (s) => setState({ toasts: s.toasts, isMuted: s.isMuted });
    _listeners.add(handler);
    return () => { _listeners.delete(handler); };
  }, []);

  if (state.isMuted || !state.toasts.length) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 72,
      right: 20,
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      pointerEvents: 'none',
      width: 'auto',
      maxWidth: 360,
    }}>
      {/* Mini Controls Bar when 2 toasts are active */}
      {state.toasts.length > 1 && (
        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 12,
          pointerEvents: 'all',
          padding: '2px 4px',
        }}>
          <button
            onClick={dismissAllToasts}
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
              background: 'rgba(15,23,42,0.8)',
              border: '1px solid rgba(148,163,184,0.15)',
              padding: '2px 8px',
              borderRadius: 10,
              cursor: 'pointer',
              backdropFilter: 'blur(8px)',
            }}
          >
            Clear all ({state.toasts.length})
          </button>
          <button
            onClick={toggleMutePopups}
            style={{
              fontSize: '0.7rem',
              color: 'var(--yellow)',
              background: 'rgba(15,23,42,0.8)',
              border: '1px solid rgba(236,201,75,0.2)',
              padding: '2px 8px',
              borderRadius: 10,
              cursor: 'pointer',
              backdropFilter: 'blur(8px)',
            }}
          >
            Mute popups
          </button>
        </div>
      )}

      {state.toasts.map(t => {
        const colors = COLOR_MAP[t.type] || COLOR_MAP.info;
        const Icon   = ICON_MAP[t.type]  || Bell;

        return (
          <div
            key={t.id}
            style={{
              pointerEvents: 'all',
              background:    'rgba(13, 18, 36, 0.94)',
              border:        `1px solid ${colors.border}`,
              borderLeft:    `3px solid ${colors.text}`,
              borderRadius:  10,
              padding:       '10px 14px',
              width:         340,
              maxWidth:      '90vw',
              display:       'flex',
              alignItems:    'flex-start',
              gap:           10,
              boxShadow:     '0 10px 30px rgba(0,0,0,0.6)',
              animation:     'toastTopIn 0.28s cubic-bezier(0.16,1,0.3,1) forwards',
              backdropFilter:'blur(16px)',
              position:      'relative',
              overflow:      'hidden',
            }}
          >
            <div style={{
              flexShrink: 0,
              marginTop: 1,
              padding: '4px',
              borderRadius: 6,
              background: colors.badge,
            }}>
              <Icon size={14} style={{ color: colors.text, display: 'block' }} />
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                {t.title && (
                  <span style={{
                    fontWeight: 700,
                    fontSize: '0.74rem',
                    letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                    color: colors.text,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}>
                    {t.title}
                  </span>
                )}
                <span style={{ fontSize: '0.68rem', color: '#64748b', fontFamily: 'JetBrains Mono', marginLeft: 6 }}>
                  {t.timeStr}
                </span>
              </div>
              <div style={{
                fontSize: '0.78rem',
                color: '#e2e8f0',
                lineHeight: 1.4,
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}>
                {t.message}
              </div>
            </div>

            <button
              onClick={() => dismissToast(t.id)}
              title="Dismiss alert"
              style={{
                flexShrink: 0,
                color: '#64748b',
                cursor: 'pointer',
                padding: '2px',
                marginTop: -2,
                marginRight: -4,
                borderRadius: 4,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'color 0.15s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.color = '#fff'}
              onMouseLeave={e => e.currentTarget.style.color = '#64748b'}
            >
              <X size={13} />
            </button>

            {/* Subtle auto-dismiss countdown bar */}
            {t.duration > 0 && (
              <div style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                height: 2,
                background: colors.text,
                opacity: 0.6,
                animation: `toastCountdown ${t.duration}ms linear forwards`,
              }} />
            )}
          </div>
        );
      })}

      <style>{`
        @keyframes toastTopIn {
          from { opacity: 0; transform: translateY(-16px) scale(0.96); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes toastCountdown {
          from { width: 100%; }
          to   { width: 0%; }
        }
      `}</style>
    </div>
  );
}

/**
 * Institutional Notification Center Bell & Dropdown
 * Lives in the header, stores all alerts, and lets the user view past alerts or mute popups.
 */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState({
    history: _history,
    unreadCount: _unreadCount,
    isMuted: _isMuted,
  });

  const dropdownRef = useRef(null);

  useEffect(() => {
    const handler = (s) => setState({
      history: s.history,
      unreadCount: s.unreadCount,
      isMuted: s.isMuted,
    });
    _listeners.add(handler);
    return () => { _listeners.delete(handler); };
  }, []);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const clickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', clickOutside);
    return () => document.removeEventListener('mousedown', clickOutside);
  }, [open]);

  const handleToggleOpen = () => {
    const next = !open;
    setOpen(next);
    if (next) {
      markAllAsRead();
    }
  };

  return (
    <div ref={dropdownRef} style={{ position: 'relative' }}>
      {/* Bell Button */}
      <button
        id="notification-bell-btn"
        onClick={handleToggleOpen}
        title={state.isMuted ? 'Alert popups muted (click to view live feed)' : 'View live event alert feed'}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          background: open ? 'rgba(99,179,237,0.18)' : 'rgba(15, 23, 42, 0.75)',
          border: `1px solid ${state.isMuted ? 'rgba(236,201,75,0.4)' : open ? 'rgba(99,179,237,0.5)' : 'rgba(148, 163, 184, 0.18)'}`,
          borderRadius: 20,
          padding: '5px 11px',
          color: state.isMuted ? 'var(--yellow)' : '#cbd5e1',
          cursor: 'pointer',
          fontSize: '0.78rem',
          fontWeight: 600,
          transition: 'all 0.2s ease',
          outline: 'none',
        }}
      >
        {state.isMuted ? (
          <BellOff size={14} style={{ color: 'var(--yellow)' }} />
        ) : (
          <Bell size={14} style={{ color: state.unreadCount > 0 ? 'var(--green)' : '#94a3b8' }} />
        )}

        <span style={{ fontSize: '0.74rem' }}>
          {state.isMuted ? 'Muted' : 'Alerts'}
        </span>

        {state.history.length > 0 && (
          <span style={{
            fontSize: '0.68rem',
            padding: '1px 6px',
            borderRadius: 10,
            background: state.unreadCount > 0 ? 'var(--green)' : 'rgba(148,163,184,0.18)',
            color: state.unreadCount > 0 ? '#0f172a' : '#94a3b8',
            fontWeight: 800,
          }}>
            {state.history.length}
          </span>
        )}
      </button>

      {/* Dropdown Menu */}
      {open && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 8px)',
          right: 0,
          width: 380,
          maxWidth: '92vw',
          maxHeight: 460,
          background: '#0d1224',
          border: '1px solid rgba(99,179,237,0.25)',
          borderRadius: 12,
          boxShadow: '0 16px 40px rgba(0,0,0,0.7)',
          zIndex: 10000,
          display: 'flex',
          flexDirection: 'column',
          backdropFilter: 'blur(16px)',
          animation: 'toastTopIn 0.2s cubic-bezier(0.16,1,0.3,1) forwards',
        }}>
          {/* Header */}
          <div style={{
            padding: '12px 16px',
            borderBottom: '1px solid rgba(148,163,184,0.12)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontWeight: 700, fontSize: '0.82rem', color: '#f1f5f9' }}>
                Live Risk Alert Feed
              </span>
              <span style={{
                fontSize: '0.68rem',
                background: 'rgba(72,187,120,0.12)',
                color: 'var(--green)',
                padding: '2px 7px',
                borderRadius: 10,
                border: '1px solid rgba(72,187,120,0.25)',
              }}>
                {state.history.length} events
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <button
                onClick={toggleMutePopups}
                title={state.isMuted ? 'Enable on-screen popups' : 'Mute on-screen popups (events still log here)'}
                style={{
                  fontSize: '0.72rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  background: state.isMuted ? 'rgba(236,201,75,0.15)' : 'rgba(148,163,184,0.08)',
                  color: state.isMuted ? 'var(--yellow)' : 'var(--text-muted)',
                  border: `1px solid ${state.isMuted ? 'rgba(236,201,75,0.4)' : 'rgba(148,163,184,0.15)'}`,
                  padding: '3px 8px',
                  borderRadius: 6,
                  cursor: 'pointer',
                }}
              >
                {state.isMuted ? <BellOff size={11} /> : <Bell size={11} />}
                {state.isMuted ? 'Popups Muted' : 'Popups On'}
              </button>

              {state.history.length > 0 && (
                <button
                  onClick={clearAlertHistory}
                  title="Clear alert feed history"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#64748b',
                    cursor: 'pointer',
                    padding: 4,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          </div>

          {/* Alert List */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '8px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}>
            {state.history.length === 0 ? (
              <div style={{ padding: '32px 16px', textAlign: 'center', color: '#64748b', fontSize: '0.8rem' }}>
                <CheckCheck size={24} style={{ margin: '0 auto 8px', opacity: 0.5 }} />
                No alerts recorded yet. Streaming live headlines...
              </div>
            ) : (
              state.history.map((item) => {
                const colors = COLOR_MAP[item.type] || COLOR_MAP.info;
                const Icon   = ICON_MAP[item.type]  || Bell;

                return (
                  <div
                    key={item.id}
                    style={{
                      background: 'rgba(15, 23, 42, 0.6)',
                      border: `1px solid ${colors.border}`,
                      borderLeft: `3px solid ${colors.text}`,
                      borderRadius: 8,
                      padding: '8px 10px',
                      display: 'flex',
                      gap: 10,
                      alignItems: 'flex-start',
                    }}
                  >
                    <div style={{
                      marginTop: 2,
                      padding: 3,
                      borderRadius: 4,
                      background: colors.badge,
                      flexShrink: 0,
                    }}>
                      <Icon size={12} style={{ color: colors.text }} />
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                        <span style={{
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          color: colors.text,
                          letterSpacing: '0.04em',
                          textTransform: 'uppercase',
                        }}>
                          {item.title || 'Signal Detected'}
                        </span>
                        <span style={{ fontSize: '0.68rem', color: '#64748b', fontFamily: 'JetBrains Mono' }}>
                          {item.timeStr}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: 1.35 }}>
                        {item.message}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div style={{
            padding: '8px 14px',
            borderTop: '1px solid rgba(148,163,184,0.1)',
            fontSize: '0.72rem',
            color: '#64748b',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'rgba(10, 14, 28, 0.6)',
          }}>
            <span>Toasts pop at top-right without blocking graphs</span>
            <span style={{ color: 'var(--blue)', cursor: 'pointer' }} onClick={() => setOpen(false)}>
              Close
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
