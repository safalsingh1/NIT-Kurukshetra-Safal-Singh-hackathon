// src/Toast.jsx — lightweight self-contained toast engine (no 3rd-party lib)
import { useState, useEffect, useCallback } from 'react';
import { X, AlertTriangle, TrendingUp, TrendingDown, Bell } from 'lucide-react';

let _dispatch = null;

export function toast(message, opts = {}) {
  if (_dispatch) _dispatch({ message, ...opts });
}

const ICON_MAP = {
  confirm: TrendingUp,
  sell:    TrendingDown,
  alert:   AlertTriangle,
  info:    Bell,
};

const COLOR_MAP = {
  confirm: { border: 'rgba(72,187,120,0.4)',  bg: 'rgba(72,187,120,0.08)',  text: '#48bb78' },
  sell:    { border: 'rgba(252,129,129,0.4)', bg: 'rgba(252,129,129,0.08)', text: '#fc8181' },
  alert:   { border: 'rgba(236,201,75,0.4)',  bg: 'rgba(236,201,75,0.08)',  text: '#ecc94b' },
  info:    { border: 'rgba(99,179,237,0.4)',   bg: 'rgba(99,179,237,0.08)',  text: '#63b3ed' },
};

export function ToastContainer() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    _dispatch = ({ message, type = 'info', title = '', duration = 5000 }) => {
      const id = Date.now() + Math.random();
      setToasts(prev => [...prev.slice(-4), { id, message, type, title, duration }]);
      if (duration > 0) {
        setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), duration);
      }
    };
    return () => { _dispatch = null; };
  }, []);

  const dismiss = useCallback((id) => setToasts(p => p.filter(t => t.id !== id)), []);

  if (!toasts.length) return null;

  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
      display: 'flex', flexDirection: 'column', gap: 10, pointerEvents: 'none',
    }}>
      {toasts.map(t => {
        const colors  = COLOR_MAP[t.type] || COLOR_MAP.info;
        const Icon    = ICON_MAP[t.type]  || Bell;
        return (
          <div
            key={t.id}
            style={{
              pointerEvents: 'all',
              background:    '#0d1224',
              border:        `1px solid ${colors.border}`,
              borderLeft:    `4px solid ${colors.text}`,
              borderRadius:  12,
              padding:       '12px 16px',
              minWidth:      300,
              maxWidth:      400,
              display:       'flex',
              alignItems:    'flex-start',
              gap:           12,
              boxShadow:     '0 8px 32px rgba(0,0,0,0.6)',
              animation:     'toastIn 0.3s cubic-bezier(0.34,1.56,0.64,1) forwards',
              backdropFilter:'blur(12px)',
            }}
          >
            <div style={{ flexShrink: 0, marginTop: 2 }}>
              <Icon size={16} style={{ color: colors.text }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              {t.title && (
                <div style={{ fontWeight: 700, fontSize: '0.78rem', letterSpacing: '0.06em', textTransform: 'uppercase', color: colors.text, marginBottom: 3 }}>
                  {t.title}
                </div>
              )}
              <div style={{ fontSize: '0.82rem', color: '#e2e8f0', lineHeight: 1.5 }}>{t.message}</div>
            </div>
            <button
              onClick={() => dismiss(t.id)}
              style={{ flexShrink: 0, color: '#4a5568', cursor: 'pointer', padding: 2, marginTop: -2 }}
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
      <style>{`
        @keyframes toastIn {
          from { opacity: 0; transform: translateX(40px) scale(0.95); }
          to   { opacity: 1; transform: translateX(0) scale(1); }
        }
      `}</style>
    </div>
  );
}
