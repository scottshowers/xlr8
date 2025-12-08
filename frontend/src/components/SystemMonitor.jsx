/**
 * XLR8 OPERATIONS CENTER - FULL BUILD
 * 
 * Multi-page: Overview | Security | Performance | Costs
 * Settings modal for subscriptions
 * Fullscreen kiosk mode
 * Dynamic threat data structure
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';

// =============================================================================
// THEMES
// =============================================================================
const THEMES = {
  dark: {
    name: 'dark',
    bg: '#1a1f2e',
    panel: '#242938',
    panelLight: '#2a3042',
    panelBorder: '#3d4559',
    text: '#e2e8f0',
    textDim: '#8892a6',
    textBright: '#ffffff',
    green: '#00e676',
    greenDim: '#00c853',
    greenBg: 'rgba(0, 230, 118, 0.1)',
    red: '#ff5252',
    redDim: '#ff1744',
    redBg: 'rgba(255, 82, 82, 0.12)',
    yellow: '#ffc107',
    yellowDim: '#ffab00',
    yellowBg: 'rgba(255, 193, 7, 0.1)',
    blue: '#448aff',
    blueDim: '#2979ff',
    cyan: '#18ffff',
    cyanDim: '#00e5ff',
    purple: '#b388ff',
    orange: '#ff6e40',
    shadow: 'rgba(0,0,0,0.3)',
  },
  light: {
    name: 'light',
    bg: '#f0f4f8',
    panel: '#ffffff',
    panelLight: '#f8fafc',
    panelBorder: '#e2e8f0',
    text: '#1e293b',
    textDim: '#64748b',
    textBright: '#0f172a',
    green: '#059669',
    greenDim: '#10b981',
    greenBg: 'rgba(5, 150, 105, 0.08)',
    red: '#dc2626',
    redDim: '#ef4444',
    redBg: 'rgba(220, 38, 38, 0.08)',
    yellow: '#d97706',
    yellowDim: '#f59e0b',
    yellowBg: 'rgba(217, 119, 6, 0.08)',
    blue: '#2563eb',
    blueDim: '#3b82f6',
    cyan: '#0891b2',
    cyanDim: '#06b6d4',
    purple: '#7c3aed',
    orange: '#ea580c',
    shadow: 'rgba(0,0,0,0.08)',
  },
};

// =============================================================================
// THREAT DATA (would come from API in production)
// =============================================================================
const THREAT_DATA = {
  api: { 
    level: 2, 
    label: 'API GATEWAY', 
    component: 'api',
    category: 'infrastructure',
    issues: [
      { id: 1, issue: 'Rate limiting not enforced', severity: 'high', status: 'open', detected: '2024-12-01' },
      { id: 2, issue: 'Input validation needed on /upload', severity: 'medium', status: 'open', detected: '2024-12-03' },
      { id: 3, issue: 'CORS allows wildcard origin', severity: 'low', status: 'open', detected: '2024-12-05' },
    ], 
    action: 'Implement rate limiting and input validation',
    lastScan: '2024-12-07 14:30:00',
  },
  duckdb: { 
    level: 2, 
    label: 'STRUCTURED DB', 
    component: 'duckdb',
    category: 'data',
    issues: [
      { id: 4, issue: 'PII fields (SSN, DOB) not masked', severity: 'high', status: 'open', detected: '2024-12-01' },
      { id: 5, issue: 'Query audit logging disabled', severity: 'medium', status: 'open', detected: '2024-12-02' },
      { id: 6, issue: 'No row-level access controls', severity: 'medium', status: 'in_progress', detected: '2024-12-04' },
    ], 
    action: 'Enable data masking for sensitive fields',
    lastScan: '2024-12-07 14:30:00',
  },
  chromadb: { 
    level: 1, 
    label: 'VECTOR STORE', 
    component: 'chromadb',
    category: 'data',
    issues: [
      { id: 7, issue: 'Embeddings may contain PII fragments', severity: 'medium', status: 'open', detected: '2024-12-05' },
      { id: 8, issue: 'No collection-level permissions', severity: 'low', status: 'open', detected: '2024-12-06' },
    ], 
    action: 'Audit chunk content for sensitive data',
    lastScan: '2024-12-07 14:30:00',
  },
  claude: { 
    level: 2, 
    label: 'CLOUD AI (CLAUDE)', 
    component: 'claude',
    category: 'ai',
    issues: [
      { id: 9, issue: 'Data transmitted to external API', severity: 'medium', status: 'acknowledged', detected: '2024-12-01' },
      { id: 10, issue: 'Prompt injection vulnerability', severity: 'high', status: 'open', detected: '2024-12-03' },
      { id: 11, issue: 'Response logging incomplete', severity: 'low', status: 'open', detected: '2024-12-06' },
    ], 
    action: 'Implement prompt sanitization layer',
    lastScan: '2024-12-07 14:30:00',
  },
  supabase: { 
    level: 0, 
    label: 'AUTHENTICATION', 
    component: 'supabase',
    category: 'infrastructure',
    issues: [], 
    action: '',
    lastScan: '2024-12-07 14:30:00',
  },
  runpod: { 
    level: 0, 
    label: 'LOCAL AI (RUNPOD)', 
    component: 'runpod',
    category: 'ai',
    issues: [], 
    action: '',
    lastScan: '2024-12-07 14:30:00',
  },
  rag: { 
    level: 1, 
    label: 'RAG ENGINE', 
    component: 'rag',
    category: 'ai',
    issues: [
      { id: 12, issue: 'Context window may include sensitive docs', severity: 'medium', status: 'open', detected: '2024-12-04' },
    ], 
    action: 'Implement document classification filter',
    lastScan: '2024-12-07 14:30:00',
  },
};

// =============================================================================
// UTILITY COMPONENTS
// =============================================================================

const AccentText = ({ children, color, size = '1rem', mono = false, glow = false, T }) => (
  <span style={{
    color: color || T.green,
    fontSize: size,
    fontFamily: mono ? "'JetBrains Mono', 'Fira Code', monospace" : 'inherit',
    fontWeight: 600,
    textShadow: glow && T.name === 'dark' ? `0 0 10px ${color || T.green}50` : 'none',
  }}>{children}</span>
);

const StatusDot = ({ status, size = 8, T }) => {
  const color = status === 2 ? T.red : status === 1 ? T.yellow : T.green;
  return (
    <span style={{
      display: 'inline-block',
      width: size,
      height: size,
      borderRadius: '50%',
      background: color,
      boxShadow: T.name === 'dark' ? `0 0 ${size}px ${color}` : `0 0 0 2px ${color}25`,
    }} />
  );
};

const Panel = ({ children, title, status, action, style = {}, T }) => (
  <div style={{
    background: T.panel,
    border: `1px solid ${T.panelBorder}`,
    borderRadius: 8,
    overflow: 'hidden',
    boxShadow: `0 2px 8px ${T.shadow}`,
    ...style,
  }}>
    {title && (
      <div style={{
        padding: '0.6rem 0.875rem',
        borderBottom: `1px solid ${T.panelBorder}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: T.panelLight,
      }}>
        <span style={{ 
          fontSize: '0.7rem', 
          fontWeight: 600, 
          color: T.textDim, 
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          fontFamily: "'JetBrains Mono', monospace",
        }}>{title}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {action}
          {status !== undefined && <StatusDot status={status} size={6} T={T} />}
        </div>
      </div>
    )}
    <div style={{ padding: '0.875rem' }}>{children}</div>
  </div>
);

const Button = ({ children, onClick, variant = 'default', size = 'md', T, style = {} }) => {
  const variants = {
    default: { bg: T.panelLight, border: T.panelBorder, color: T.text },
    primary: { bg: T.blue, border: T.blue, color: '#fff' },
    danger: { bg: T.redBg, border: T.redDim, color: T.red },
    success: { bg: T.greenBg, border: T.greenDim, color: T.green },
  };
  const sizes = {
    sm: { padding: '0.25rem 0.5rem', fontSize: '0.65rem' },
    md: { padding: '0.4rem 0.75rem', fontSize: '0.75rem' },
    lg: { padding: '0.5rem 1rem', fontSize: '0.85rem' },
  };
  const v = variants[variant];
  const s = sizes[size];
  
  return (
    <button
      onClick={onClick}
      style={{
        background: v.bg,
        border: `1px solid ${v.border}`,
        borderRadius: 4,
        color: v.color,
        cursor: 'pointer',
        fontFamily: 'monospace',
        fontWeight: 500,
        ...s,
        ...style,
      }}
    >
      {children}
    </button>
  );
};

// =============================================================================
// NAV TABS
// =============================================================================

function NavTabs({ active, onChange, T }) {
  const tabs = [
    { id: 'overview', label: 'OVERVIEW', icon: '◉' },
    { id: 'security', label: 'SECURITY', icon: '🛡️' },
    { id: 'performance', label: 'PERFORMANCE', icon: '⚡' },
    { id: 'costs', label: 'COSTS', icon: '💰' },
  ];

  return (
    <div style={{ display: 'flex', gap: '0.25rem' }}>
      {tabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          style={{
            background: active === tab.id ? T.panel : 'transparent',
            border: `1px solid ${active === tab.id ? T.panelBorder : 'transparent'}`,
            borderBottom: active === tab.id ? `1px solid ${T.panel}` : `1px solid ${T.panelBorder}`,
            borderRadius: '6px 6px 0 0',
            padding: '0.5rem 1rem',
            color: active === tab.id ? T.text : T.textDim,
            cursor: 'pointer',
            fontFamily: 'monospace',
            fontSize: '0.7rem',
            fontWeight: 600,
            letterSpacing: '0.05em',
            marginBottom: -1,
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
          }}
        >
          <span>{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// =============================================================================
// THEME TOGGLE
// =============================================================================

function ThemeToggle({ theme, onToggle }) {
  return (
    <button
      onClick={onToggle}
      style={{
        background: theme.panelLight,
        border: `1px solid ${theme.panelBorder}`,
        borderRadius: 20,
        padding: '0.3rem',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        width: 52,
      }}
      title={`Switch to ${theme.name === 'dark' ? 'light' : 'dark'} mode`}
    >
      <div style={{
        width: 20,
        height: 20,
        borderRadius: '50%',
        background: theme.name === 'dark' ? theme.yellow : theme.blue,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '0.7rem',
        transform: theme.name === 'dark' ? 'translateX(24px)' : 'translateX(0)',
        transition: 'transform 0.2s ease',
        boxShadow: `0 0 8px ${theme.name === 'dark' ? theme.yellow : theme.blue}50`,
      }}>
        {theme.name === 'dark' ? '🌙' : '☀️'}
      </div>
    </button>
  );
}

// =============================================================================
// SETTINGS MODAL
// =============================================================================

function SettingsModal({ open, onClose, T, onSave }) {
  const [subscriptions, setSubscriptions] = useState([
    { name: 'Claude Team', cost: 25, quantity: 7 },
    { name: 'Railway', cost: 20, quantity: 1 },
    { name: 'Supabase', cost: 25, quantity: 1 },
    { name: 'RunPod', cost: 0.06, quantity: 1, unit: 'per hour' },
  ]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      // Fetch current settings from API
      api.get('/status/costs/fixed').then(res => {
        if (res.data && Array.isArray(res.data)) {
          const subs = res.data.filter(i => i.category === 'subscription');
          if (subs.length > 0) {
            setSubscriptions(subs.map(s => ({
              name: s.name,
              cost: s.cost_per_unit,
              quantity: s.quantity,
              unit: s.unit_type,
            })));
          }
        }
      }).catch(() => {});
    }
  }, [open]);

  if (!open) return null;

  const updateSub = (idx, field, value) => {
    setSubscriptions(prev => {
      const updated = [...prev];
      updated[idx] = { ...updated[idx], [field]: field === 'quantity' ? parseInt(value) || 0 : parseFloat(value) || 0 };
      return updated;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      for (const sub of subscriptions) {
        await api.put(`/status/costs/fixed/${encodeURIComponent(sub.name)}`, null, {
          params: { cost_per_unit: sub.cost, quantity: sub.quantity }
        });
      }
      onSave && onSave();
      onClose();
    } catch (e) {
      console.error('Save failed:', e);
    }
    setSaving(false);
  };

  const total = subscriptions.reduce((sum, s) => sum + (s.cost * s.quantity), 0);

  return (
    <div 
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div 
        style={{
          background: T.panel,
          borderRadius: 12,
          width: 480,
          maxHeight: '80vh',
          overflow: 'hidden',
          boxShadow: `0 20px 40px ${T.shadow}`,
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{
          padding: '1rem 1.25rem',
          borderBottom: `1px solid ${T.panelBorder}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: T.text }}>⚙️ Settings</div>
            <div style={{ fontSize: '0.7rem', color: T.textDim, marginTop: '0.2rem' }}>Manage subscriptions and costs</div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: T.textDim, cursor: 'pointer', fontSize: '1.2rem' }}>✕</button>
        </div>

        <div style={{ padding: '1.25rem', overflowY: 'auto', maxHeight: 'calc(80vh - 140px)' }}>
          <div style={{ fontSize: '0.7rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '0.75rem' }}>
            MONTHLY SUBSCRIPTIONS
          </div>
          
          {subscriptions.map((sub, idx) => (
            <div key={sub.name} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '0.75rem',
              background: T.panelLight,
              borderRadius: 6,
              marginBottom: '0.5rem',
            }}>
              <div style={{ flex: 1, fontSize: '0.85rem', color: T.text }}>{sub.name}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span style={{ color: T.textDim, fontSize: '0.8rem' }}>$</span>
                <input
                  type="number"
                  value={sub.cost}
                  onChange={e => updateSub(idx, 'cost', e.target.value)}
                  step="0.01"
                  style={{
                    width: 70,
                    padding: '0.4rem',
                    borderRadius: 4,
                    border: `1px solid ${T.panelBorder}`,
                    background: T.panel,
                    color: T.text,
                    fontSize: '0.85rem',
                    fontFamily: 'monospace',
                  }}
                />
                <span style={{ color: T.textDim, fontSize: '0.8rem' }}>×</span>
                <input
                  type="number"
                  value={sub.quantity}
                  onChange={e => updateSub(idx, 'quantity', e.target.value)}
                  style={{
                    width: 50,
                    padding: '0.4rem',
                    borderRadius: 4,
                    border: `1px solid ${T.panelBorder}`,
                    background: T.panel,
                    color: T.text,
                    fontSize: '0.85rem',
                    fontFamily: 'monospace',
                  }}
                />
                <span style={{ color: T.green, fontSize: '0.8rem', fontFamily: 'monospace', minWidth: 60, textAlign: 'right' }}>
                  ${(sub.cost * sub.quantity).toFixed(2)}
                </span>
              </div>
            </div>
          ))}

          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            padding: '0.75rem',
            background: T.greenBg,
            borderRadius: 6,
            marginTop: '1rem',
          }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: T.text }}>TOTAL MONTHLY</span>
            <AccentText size="1rem" color={T.green} mono glow={T.name === 'dark'} T={T}>
              ${total.toFixed(2)}
            </AccentText>
          </div>
        </div>

        <div style={{
          padding: '1rem 1.25rem',
          borderTop: `1px solid ${T.panelBorder}`,
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '0.5rem',
        }}>
          <Button onClick={onClose} T={T}>Cancel</Button>
          <Button onClick={handleSave} variant="primary" T={T}>{saving ? 'Saving...' : 'Save Changes'}</Button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// METRIC CARDS
// =============================================================================

function MetricCard({ label, value, unit, sublabel, trend, status, T, onClick }) {
  return (
    <Panel status={status} T={T} style={{ cursor: onClick ? 'pointer' : 'default' }} onClick={onClick}>
      <div style={{ fontSize: '0.65rem', color: T.textDim, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.4rem', fontFamily: 'monospace' }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.3rem' }}>
        <AccentText 
          size="1.75rem" 
          color={status === 2 ? T.red : status === 1 ? T.yellow : T.green} 
          mono 
          glow={T.name === 'dark'}
          T={T}
        >
          {value}
        </AccentText>
        {unit && <span style={{ fontSize: '0.8rem', color: T.textDim }}>{unit}</span>}
      </div>
      {(sublabel || trend !== undefined) && (
        <div style={{ marginTop: '0.3rem', fontSize: '0.65rem', color: T.textDim, display: 'flex', gap: '0.5rem' }}>
          {sublabel && <span>{sublabel}</span>}
          {trend !== undefined && (
            <span style={{ color: trend >= 0 ? T.green : T.red, fontWeight: 600 }}>
              {trend >= 0 ? '▲' : '▼'} {Math.abs(trend)}%
            </span>
          )}
        </div>
      )}
    </Panel>
  );
}

function SpendBreakdown({ data, T }) {
  const items = [
    { label: 'SUBSCRIPTIONS', value: data.fixed || 0, color: T.purple },
    { label: 'CLAUDE API', value: data.claude || 0, color: T.cyan },
    { label: 'LOCAL LLM', value: data.runpod || 0, color: T.green },
    { label: 'TEXTRACT', value: data.textract || 0, color: T.orange },
  ];
  const max = Math.max(...items.map(i => i.value), 1);

  return (
    <Panel title="COST ALLOCATION" T={T}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
        {items.map(item => (
          <div key={item.label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
              <span style={{ fontSize: '0.65rem', color: T.textDim, fontFamily: 'monospace' }}>{item.label}</span>
              <AccentText size="0.75rem" color={item.color} mono T={T}>${item.value.toFixed(2)}</AccentText>
            </div>
            <div style={{ height: 4, background: T.panelBorder, borderRadius: 2 }}>
              <div style={{
                height: '100%',
                width: `${(item.value / max) * 100}%`,
                background: item.color,
                borderRadius: 2,
                boxShadow: T.name === 'dark' ? `0 0 6px ${item.color}60` : 'none',
              }} />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

// =============================================================================
// ZOOMABLE TOPOLOGY
// =============================================================================

function SystemTopology({ flow, onNodeClick, selectedNode, T, fullWidth = false }) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [startPan, setStartPan] = useState({ x: 0, y: 0 });

  const nodes = {
    user: { x: 60, y: 140, icon: '◉', label: 'USER', color: T.blue },
    api: { x: 180, y: 140, icon: '⬡', label: 'API', color: T.blue, encrypted: true, threat: THREAT_DATA.api },
    supabase: { x: 180, y: 240, icon: '◈', label: 'AUTH', color: T.purple, encrypted: true, threat: THREAT_DATA.supabase },
    duckdb: { x: 340, y: 70, icon: '▣', label: 'STRUCT', color: T.purple, encrypted: true, threat: THREAT_DATA.duckdb },
    rag: { x: 340, y: 140, icon: '◎', label: 'RAG', color: T.orange, threat: THREAT_DATA.rag },
    chromadb: { x: 340, y: 210, icon: '◇', label: 'VECTOR', color: T.cyan, threat: THREAT_DATA.chromadb },
    router: { x: 480, y: 140, icon: '⬢', label: 'ROUTER', color: T.yellow },
    claude: { x: 620, y: 80, icon: '●', label: 'CLAUDE', color: T.cyan, threat: THREAT_DATA.claude },
    llama: { x: 580, y: 200, icon: '○', label: 'LLAMA', color: T.green, threat: THREAT_DATA.runpod },
    mistral: { x: 650, y: 200, icon: '○', label: 'MISTRAL', color: T.green },
    deepseek: { x: 720, y: 200, icon: '○', label: 'DEEP', color: T.green },
  };

  const connections = [
    { from: 'user', to: 'api', color: T.blue, active: flow.user },
    { from: 'api', to: 'supabase', color: T.purple, active: flow.auth },
    { from: 'api', to: 'duckdb', color: T.purple, active: flow.struct, label: 'SQL' },
    { from: 'api', to: 'rag', color: T.orange, active: flow.semantic, label: 'SEMANTIC' },
    { from: 'rag', to: 'chromadb', color: T.cyan, active: flow.vector },
    { from: 'rag', to: 'router', color: T.yellow, active: flow.llm },
    { from: 'router', to: 'claude', color: T.cyan, active: flow.cloud, label: 'CLOUD' },
    { from: 'router', to: 'llama', color: T.green, active: flow.local, label: 'LOCAL' },
    { from: 'llama', to: 'mistral', color: T.green, active: flow.local },
    { from: 'mistral', to: 'deepseek', color: T.green, active: flow.local },
  ];

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(z => Math.min(Math.max(z + delta, 0.5), 3));
  }, []);

  const handleMouseDown = (e) => {
    if (e.button === 0 && e.target.tagName === 'svg') {
      setIsPanning(true);
      setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e) => {
    if (isPanning) {
      setPan({ x: e.clientX - startPan.x, y: e.clientY - startPan.y });
    }
  };

  const handleMouseUp = () => setIsPanning(false);
  const resetView = () => { setZoom(1); setPan({ x: 0, y: 0 }); };

  const Node = ({ id, data }) => {
    const isSelected = selectedNode === id;
    const threat = data.threat;
    const threatLevel = threat?.level || 0;
    
    return (
      <g 
        transform={`translate(${data.x}, ${data.y})`} 
        style={{ cursor: 'pointer' }}
        onClick={(e) => { e.stopPropagation(); onNodeClick(id); }}
      >
        {threatLevel > 0 && (
          <circle r={28} fill="none" stroke={threatLevel === 2 ? T.red : T.yellow} strokeWidth={2} strokeDasharray="4,4" opacity={0.6}>
            <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="10s" repeatCount="indefinite" />
          </circle>
        )}
        <circle
          r={isSelected ? 24 : 20}
          fill={T.panel}
          stroke={isSelected ? T.textBright : data.color}
          strokeWidth={isSelected ? 2.5 : 2}
          style={{ filter: T.name === 'dark' && isSelected ? `drop-shadow(0 0 12px ${data.color})` : 'none', transition: 'all 0.2s ease' }}
        />
        <text y={4} textAnchor="middle" fontSize={14} fill={data.color} style={{ fontFamily: 'monospace' }}>{data.icon}</text>
        <text y={38} textAnchor="middle" fontSize={8} fill={T.textDim} style={{ fontFamily: 'monospace', letterSpacing: '0.05em' }}>{data.label}</text>
        {data.encrypted && (
          <g transform="translate(14, -14)">
            <circle r={7} fill={T.panel} stroke={T.yellow} strokeWidth={1.5} />
            <text y={3} textAnchor="middle" fontSize={7} fill={T.yellow}>🔒</text>
          </g>
        )}
        <circle cx={-14} cy={-14} r={4} fill={threatLevel === 2 ? T.red : threatLevel === 1 ? T.yellow : T.green}
          style={{ filter: T.name === 'dark' ? `drop-shadow(0 0 4px ${threatLevel === 2 ? T.red : threatLevel === 1 ? T.yellow : T.green})` : 'none' }}
        />
      </g>
    );
  };

  return (
    <Panel title="SYSTEM TOPOLOGY" style={{ gridColumn: fullWidth ? 'span 5' : 'span 2', position: 'relative' }} T={T}>
      <div style={{ position: 'absolute', top: 48, right: 12, display: 'flex', flexDirection: 'column', gap: 4, zIndex: 5 }}>
        <button onClick={() => setZoom(z => Math.min(z + 0.2, 3))} style={{ width: 28, height: 28, borderRadius: 4, border: `1px solid ${T.panelBorder}`, background: T.panelLight, color: T.text, cursor: 'pointer', fontSize: '1rem' }}>+</button>
        <button onClick={() => setZoom(z => Math.max(z - 0.2, 0.5))} style={{ width: 28, height: 28, borderRadius: 4, border: `1px solid ${T.panelBorder}`, background: T.panelLight, color: T.text, cursor: 'pointer', fontSize: '1rem' }}>−</button>
        <button onClick={resetView} style={{ width: 28, height: 28, borderRadius: 4, border: `1px solid ${T.panelBorder}`, background: T.panelLight, color: T.textDim, cursor: 'pointer', fontSize: '0.6rem', fontFamily: 'monospace' }}>⟲</button>
      </div>
      <div style={{ position: 'absolute', bottom: 12, right: 12, fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', background: T.panelLight, padding: '2px 6px', borderRadius: 3, border: `1px solid ${T.panelBorder}` }}>
        {Math.round(zoom * 100)}%
      </div>
      <div
        style={{ overflow: 'hidden', cursor: isPanning ? 'grabbing' : 'grab' }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <svg width="100%" height="280" viewBox="0 0 780 280"
          style={{ transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`, transformOrigin: 'center center', transition: isPanning ? 'none' : 'transform 0.1s ease-out' }}
        >
          <rect x="550" y="40" width="220" height="80" rx={6} fill={T.cyan} opacity={0.08} stroke={T.cyan} strokeWidth={1} strokeOpacity={0.3} />
          <text x="560" y={55} fontSize={8} fill={T.cyanDim} style={{ fontFamily: 'monospace' }}>CLOUD ZONE</text>
          <rect x="550" y="140" width="220" height="100" rx={6} fill={T.green} opacity={0.08} stroke={T.green} strokeWidth={1} strokeOpacity={0.3} />
          <text x="560" y={155} fontSize={8} fill={T.greenDim} style={{ fontFamily: 'monospace' }}>LOCAL ZONE</text>
          {connections.map((conn, i) => {
            const from = nodes[conn.from];
            const to = nodes[conn.to];
            const mx = (from.x + to.x) / 2;
            const my = (from.y + to.y) / 2;
            return (
              <g key={i}>
                <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={conn.active ? conn.color : T.panelBorder} strokeWidth={conn.active ? 2.5 : 1.5} opacity={conn.active ? 1 : 0.4}
                  style={{ filter: conn.active && T.name === 'dark' ? `drop-shadow(0 0 4px ${conn.color})` : 'none', transition: 'all 0.3s ease' }} />
                {conn.label && <text x={mx} y={my - 6} textAnchor="middle" fontSize={6} fill={T.textDim} style={{ fontFamily: 'monospace' }}>{conn.label}</text>}
              </g>
            );
          })}
          {Object.entries(nodes).map(([id, data]) => <Node key={id} id={id} data={data} />)}
          <g transform="translate(20, 260)">
            <circle cx={5} cy={0} r={4} fill={T.green} /><text x={14} y={3} fontSize={7} fill={T.textDim}>SECURE</text>
            <circle cx={70} cy={0} r={4} fill={T.yellow} /><text x={79} y={3} fontSize={7} fill={T.textDim}>REVIEW</text>
            <circle cx={130} cy={0} r={4} fill={T.red} /><text x={139} y={3} fontSize={7} fill={T.textDim}>ACTION</text>
            <g transform="translate(190, -3)"><circle r={5} fill="none" stroke={T.yellow} strokeWidth={1.5} strokeDasharray="2,2" /></g>
            <text x={200} y={3} fontSize={7} fill={T.textDim}>THREAT</text>
            <text x={260} y={3} fontSize={7} fill={T.textDim}>SCROLL TO ZOOM • DRAG TO PAN</text>
          </g>
        </svg>
      </div>
    </Panel>
  );
}

// =============================================================================
// THREAT PANEL (Slide-out)
// =============================================================================

function ThreatPanel({ nodeId, onClose, T }) {
  const threat = THREAT_DATA[nodeId];
  if (!threat) return null;

  const severityColor = (sev) => sev === 'high' ? T.red : sev === 'medium' ? T.yellow : T.green;
  const statusLabel = (s) => s === 'open' ? 'OPEN' : s === 'in_progress' ? 'IN PROGRESS' : 'ACKNOWLEDGED';

  return (
    <div style={{
      position: 'absolute', right: 0, top: 0, bottom: 0, width: 360,
      background: T.panel, borderLeft: `1px solid ${T.panelBorder}`,
      display: 'flex', flexDirection: 'column', zIndex: 10, boxShadow: `-4px 0 20px ${T.shadow}`,
    }}>
      <div style={{ padding: '1rem', borderBottom: `1px solid ${T.panelBorder}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: T.panelLight }}>
        <div>
          <div style={{ fontSize: '0.7rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '0.2rem' }}>THREAT ASSESSMENT</div>
          <div style={{ fontSize: '1rem', color: T.text, fontWeight: 600 }}>{threat.label}</div>
        </div>
        <button onClick={onClose} style={{ background: T.panelLight, border: `1px solid ${T.panelBorder}`, borderRadius: 4, color: T.textDim, padding: '0.25rem 0.5rem', cursor: 'pointer', fontFamily: 'monospace', fontSize: '0.7rem' }}>✕</button>
      </div>

      <div style={{ padding: '1rem', flex: 1, overflowY: 'auto' }}>
        <div style={{ padding: '0.75rem', background: threat.level === 2 ? T.redBg : threat.level === 1 ? T.yellowBg : T.greenBg, borderRadius: 6, marginBottom: '1rem', border: `1px solid ${threat.level === 2 ? T.redDim : threat.level === 1 ? T.yellowDim : T.greenDim}30` }}>
          <div style={{ fontSize: '0.6rem', color: T.textDim, marginBottom: '0.3rem', fontFamily: 'monospace' }}>RISK LEVEL</div>
          <AccentText size="1.2rem" color={threat.level === 2 ? T.red : threat.level === 1 ? T.yellow : T.green} mono glow={T.name === 'dark'} T={T}>
            {threat.level === 2 ? 'HIGH' : threat.level === 1 ? 'MEDIUM' : 'LOW'}
          </AccentText>
          <div style={{ fontSize: '0.6rem', color: T.textDim, marginTop: '0.5rem' }}>Last scan: {threat.lastScan}</div>
        </div>

        {threat.issues.length > 0 && (
          <>
            <div style={{ fontSize: '0.6rem', color: T.textDim, marginBottom: '0.5rem', fontFamily: 'monospace' }}>
              IDENTIFIED ISSUES ({threat.issues.length})
            </div>
            {threat.issues.map((issue) => (
              <div key={issue.id} style={{ padding: '0.6rem', background: T.panelLight, borderRadius: 6, marginBottom: '0.5rem', borderLeft: `3px solid ${severityColor(issue.severity)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.3rem' }}>
                  <div style={{ fontSize: '0.75rem', color: T.text }}>{issue.issue}</div>
                  <span style={{ fontSize: '0.55rem', padding: '2px 4px', background: severityColor(issue.severity) + '20', color: severityColor(issue.severity), borderRadius: 3, fontFamily: 'monospace' }}>
                    {issue.severity.toUpperCase()}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: T.textDim }}>
                  <span>Detected: {issue.detected}</span>
                  <span style={{ color: issue.status === 'open' ? T.yellow : T.green }}>{statusLabel(issue.status)}</span>
                </div>
              </div>
            ))}
          </>
        )}

        {threat.issues.length === 0 && (
          <div style={{ padding: '2rem', textAlign: 'center', color: T.textDim }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>✓</div>
            <div style={{ fontSize: '0.8rem' }}>No issues detected</div>
          </div>
        )}

        {threat.action && (
          <div style={{ marginTop: '1rem' }}>
            <div style={{ fontSize: '0.6rem', color: T.textDim, marginBottom: '0.5rem', fontFamily: 'monospace' }}>RECOMMENDED ACTION</div>
            <div style={{ padding: '0.75rem', background: T.greenBg, borderRadius: 6, borderLeft: `3px solid ${T.green}` }}>
              <div style={{ fontSize: '0.75rem', color: T.green, fontWeight: 500 }}>{threat.action}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// ACTIVITY LOG
// =============================================================================

function ActivityLog({ entries, T, style = {} }) {
  return (
    <Panel title="ACTIVITY LOG" style={{ flex: 1, ...style }} T={T}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: 200, overflowY: 'auto' }}>
        {entries.length === 0 ? (
          <div style={{ color: T.textDim, fontSize: '0.7rem', fontFamily: 'monospace', textAlign: 'center', padding: '1rem' }}>AWAITING DATA...</div>
        ) : (
          entries.slice(0, 10).map((entry, i) => (
            <div key={entry.id || i} style={{ display: 'flex', gap: '0.5rem', padding: '0.4rem 0.5rem', background: i === 0 ? T.panelLight : 'transparent', borderRadius: 4 }}>
              <span style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', minWidth: 55 }}>{entry.time}</span>
              <StatusDot status={entry.status} size={6} T={T} />
              <span style={{ fontSize: '0.7rem', color: T.text, fontFamily: 'monospace' }}>{entry.message}</span>
              {entry.cost && <span style={{ fontSize: '0.65rem', color: T.green, fontFamily: 'monospace', marginLeft: 'auto', fontWeight: 600 }}>${entry.cost.toFixed(4)}</span>}
            </div>
          ))
        )}
      </div>
    </Panel>
  );
}

// =============================================================================
// SECURITY PAGE
// =============================================================================

function SecurityPage({ T, onNodeClick }) {
  const allIssues = Object.values(THREAT_DATA).flatMap(t => t.issues.map(i => ({ ...i, component: t.label })));
  const openIssues = allIssues.filter(i => i.status === 'open');
  const highSeverity = openIssues.filter(i => i.severity === 'high');
  const components = Object.values(THREAT_DATA);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
      {/* Summary cards */}
      <MetricCard label="TOTAL ISSUES" value={allIssues.length} status={allIssues.length > 5 ? 2 : allIssues.length > 0 ? 1 : 0} T={T} />
      <MetricCard label="OPEN ISSUES" value={openIssues.length} status={openIssues.length > 3 ? 2 : openIssues.length > 0 ? 1 : 0} T={T} />
      <MetricCard label="HIGH SEVERITY" value={highSeverity.length} status={highSeverity.length > 0 ? 2 : 0} T={T} />
      <MetricCard label="COMPONENTS AT RISK" value={components.filter(c => c.level > 0).length} sublabel={`of ${components.length}`} status={0} T={T} />

      {/* Component grid */}
      <Panel title="COMPONENT STATUS" style={{ gridColumn: 'span 2' }} T={T}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
          {components.map(comp => (
            <div
              key={comp.component}
              onClick={() => onNodeClick(comp.component)}
              style={{
                padding: '0.75rem',
                background: T.panelLight,
                borderRadius: 6,
                cursor: 'pointer',
                borderLeft: `3px solid ${comp.level === 2 ? T.red : comp.level === 1 ? T.yellow : T.green}`,
                transition: 'background 0.2s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.background = T.panel}
              onMouseLeave={e => e.currentTarget.style.background = T.panelLight}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: T.text, fontWeight: 500 }}>{comp.label}</span>
                <StatusDot status={comp.level} size={8} T={T} />
              </div>
              <div style={{ fontSize: '0.65rem', color: T.textDim, marginTop: '0.3rem' }}>
                {comp.issues.length} issue{comp.issues.length !== 1 ? 's' : ''} • {comp.category}
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Open issues list */}
      <Panel title="OPEN ISSUES" style={{ gridColumn: 'span 2' }} T={T}>
        <div style={{ maxHeight: 300, overflowY: 'auto' }}>
          {openIssues.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: T.textDim }}>
              <div style={{ fontSize: '2rem' }}>✓</div>
              <div>No open issues</div>
            </div>
          ) : (
            openIssues.map(issue => (
              <div key={issue.id} style={{
                padding: '0.6rem',
                borderBottom: `1px solid ${T.panelBorder}`,
                display: 'flex',
                gap: '0.75rem',
                alignItems: 'flex-start',
              }}>
                <div style={{
                  width: 6, height: 6, borderRadius: '50%', marginTop: 6,
                  background: issue.severity === 'high' ? T.red : issue.severity === 'medium' ? T.yellow : T.green,
                }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.75rem', color: T.text }}>{issue.issue}</div>
                  <div style={{ fontSize: '0.6rem', color: T.textDim, marginTop: '0.2rem' }}>
                    {issue.component} • Detected {issue.detected}
                  </div>
                </div>
                <span style={{
                  fontSize: '0.55rem', padding: '2px 6px', borderRadius: 3, fontFamily: 'monospace',
                  background: issue.severity === 'high' ? T.redBg : issue.severity === 'medium' ? T.yellowBg : T.greenBg,
                  color: issue.severity === 'high' ? T.red : issue.severity === 'medium' ? T.yellow : T.green,
                }}>
                  {issue.severity.toUpperCase()}
                </span>
              </div>
            ))
          )}
        </div>
      </Panel>

      {/* Risk by category */}
      <Panel title="RISK BY CATEGORY" style={{ gridColumn: 'span 2' }} T={T}>
        {['infrastructure', 'data', 'ai'].map(cat => {
          const catComps = components.filter(c => c.category === cat);
          const catIssues = catComps.reduce((sum, c) => sum + c.issues.length, 0);
          const maxLevel = Math.max(...catComps.map(c => c.level), 0);
          return (
            <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.5rem 0', borderBottom: `1px solid ${T.panelBorder}` }}>
              <StatusDot status={maxLevel} size={10} T={T} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.75rem', color: T.text, textTransform: 'uppercase' }}>{cat}</div>
                <div style={{ fontSize: '0.6rem', color: T.textDim }}>{catComps.length} components</div>
              </div>
              <div style={{ fontSize: '0.8rem', color: T.textDim, fontFamily: 'monospace' }}>{catIssues} issues</div>
            </div>
          );
        })}
      </Panel>

      {/* Recommendations */}
      <Panel title="TOP RECOMMENDATIONS" style={{ gridColumn: 'span 2' }} T={T}>
        {components.filter(c => c.action).slice(0, 4).map((comp, i) => (
          <div key={comp.component} style={{
            padding: '0.6rem',
            background: i === 0 ? T.greenBg : 'transparent',
            borderRadius: 4,
            marginBottom: '0.4rem',
            borderLeft: `3px solid ${T.green}`,
          }}>
            <div style={{ fontSize: '0.65rem', color: T.textDim, marginBottom: '0.2rem' }}>{comp.label}</div>
            <div style={{ fontSize: '0.75rem', color: T.green }}>{comp.action}</div>
          </div>
        ))}
      </Panel>
    </div>
  );
}

// =============================================================================
// PERFORMANCE PAGE
// =============================================================================

function PerformancePage({ T, data }) {
  const [perfData] = useState({
    avgResponse: 1.2,
    p95Response: 2.8,
    p99Response: 4.1,
    successRate: 99.2,
    errorRate: 0.8,
    throughput: 847,
    activeConnections: 12,
    queueDepth: 0,
    cpuUsage: 34,
    memoryUsage: 62,
    diskUsage: 41,
    networkIn: 124,
    networkOut: 89,
  });

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.75rem' }}>
      {/* Response times */}
      <MetricCard label="AVG RESPONSE" value={`${perfData.avgResponse}s`} status={perfData.avgResponse < 2 ? 0 : perfData.avgResponse < 5 ? 1 : 2} T={T} />
      <MetricCard label="P95 RESPONSE" value={`${perfData.p95Response}s`} status={perfData.p95Response < 3 ? 0 : perfData.p95Response < 6 ? 1 : 2} T={T} />
      <MetricCard label="P99 RESPONSE" value={`${perfData.p99Response}s`} status={perfData.p99Response < 5 ? 0 : perfData.p99Response < 10 ? 1 : 2} T={T} />
      <MetricCard label="SUCCESS RATE" value={`${perfData.successRate}%`} status={perfData.successRate > 99 ? 0 : perfData.successRate > 95 ? 1 : 2} T={T} />
      <MetricCard label="THROUGHPUT" value={perfData.throughput} sublabel="req/min" status={0} T={T} />

      {/* Resource usage */}
      <Panel title="RESOURCE USAGE" style={{ gridColumn: 'span 2' }} T={T}>
        {[
          { label: 'CPU', value: perfData.cpuUsage, color: T.blue },
          { label: 'MEMORY', value: perfData.memoryUsage, color: T.purple },
          { label: 'DISK', value: perfData.diskUsage, color: T.orange },
        ].map(r => (
          <div key={r.label} style={{ marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
              <span style={{ fontSize: '0.65rem', color: T.textDim, fontFamily: 'monospace' }}>{r.label}</span>
              <span style={{ fontSize: '0.75rem', color: r.value > 80 ? T.red : r.value > 60 ? T.yellow : T.green, fontFamily: 'monospace' }}>{r.value}%</span>
            </div>
            <div style={{ height: 6, background: T.panelBorder, borderRadius: 3 }}>
              <div style={{
                height: '100%',
                width: `${r.value}%`,
                background: r.value > 80 ? T.red : r.value > 60 ? T.yellow : r.color,
                borderRadius: 3,
                transition: 'width 0.3s ease',
              }} />
            </div>
          </div>
        ))}
      </Panel>

      {/* Network */}
      <Panel title="NETWORK I/O" style={{ gridColumn: 'span 1' }} T={T}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace' }}>INBOUND</div>
            <AccentText size="1.2rem" color={T.cyan} mono glow={T.name === 'dark'} T={T}>{perfData.networkIn}</AccentText>
            <span style={{ fontSize: '0.7rem', color: T.textDim }}> MB/s</span>
          </div>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace' }}>OUTBOUND</div>
            <AccentText size="1.2rem" color={T.orange} mono glow={T.name === 'dark'} T={T}>{perfData.networkOut}</AccentText>
            <span style={{ fontSize: '0.7rem', color: T.textDim }}> MB/s</span>
          </div>
        </div>
      </Panel>

      {/* Connections */}
      <Panel title="CONNECTIONS" style={{ gridColumn: 'span 2' }} T={T}>
        <div style={{ display: 'flex', gap: '2rem' }}>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace' }}>ACTIVE</div>
            <AccentText size="1.5rem" color={T.green} mono glow={T.name === 'dark'} T={T}>{perfData.activeConnections}</AccentText>
          </div>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace' }}>QUEUE</div>
            <AccentText size="1.5rem" color={perfData.queueDepth > 10 ? T.red : perfData.queueDepth > 0 ? T.yellow : T.green} mono glow={T.name === 'dark'} T={T}>
              {perfData.queueDepth}
            </AccentText>
          </div>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace' }}>ERRORS</div>
            <AccentText size="1.5rem" color={perfData.errorRate > 1 ? T.red : perfData.errorRate > 0 ? T.yellow : T.green} mono glow={T.name === 'dark'} T={T}>
              {perfData.errorRate}%
            </AccentText>
          </div>
        </div>
      </Panel>

      {/* Component latency */}
      <Panel title="COMPONENT LATENCY" style={{ gridColumn: 'span 3' }} T={T}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          {[
            { name: 'API', latency: 45, color: T.blue },
            { name: 'DuckDB', latency: 120, color: T.purple },
            { name: 'ChromaDB', latency: 85, color: T.cyan },
            { name: 'RAG', latency: 340, color: T.orange },
            { name: 'Claude', latency: 1200, color: T.cyan },
            { name: 'Local LLM', latency: 890, color: T.green },
          ].map(c => (
            <div key={c.name} style={{ textAlign: 'center', minWidth: 70 }}>
              <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '0.25rem' }}>{c.name}</div>
              <AccentText size="1rem" color={c.color} mono T={T}>{c.latency}</AccentText>
              <div style={{ fontSize: '0.55rem', color: T.textDim }}>ms</div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Uptime */}
      <Panel title="UPTIME" style={{ gridColumn: 'span 2' }} T={T}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <AccentText size="2rem" color={T.green} mono glow={T.name === 'dark'} T={T}>99.9%</AccentText>
          <div>
            <div style={{ fontSize: '0.7rem', color: T.textDim }}>Last 30 days</div>
            <div style={{ fontSize: '0.6rem', color: T.green }}>43m downtime</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 2, marginTop: '0.75rem' }}>
          {Array(30).fill(0).map((_, i) => (
            <div key={i} style={{
              flex: 1,
              height: 16,
              background: i === 12 ? T.yellow : T.green,
              borderRadius: 2,
              opacity: 0.8,
            }} title={`Day ${30 - i}`} />
          ))}
        </div>
      </Panel>
    </div>
  );
}

// =============================================================================
// COSTS PAGE
// =============================================================================

function CostsPage({ T, data, onSettingsClick }) {
  const [dailyCosts, setDailyCosts] = useState([]);

  useEffect(() => {
    api.get('/status/costs/daily?days=14').then(res => {
      if (Array.isArray(res.data)) setDailyCosts(res.data);
    }).catch(() => {});
  }, []);

  const breakdown = {
    fixed: data.month.fixed || 0,
    claude: data.usage.claude || 0,
    runpod: data.usage.runpod || 0,
    textract: data.usage.textract || 0,
  };

  const total = data.month.total || 0;
  const apiTotal = breakdown.claude + breakdown.runpod + breakdown.textract;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
      {/* Summary */}
      <MetricCard label="TOTAL SPEND" value={`$${total.toFixed(0)}`} sublabel={data.month.month_name || 'This month'} status={0} T={T} />
      <MetricCard label="SUBSCRIPTIONS" value={`$${breakdown.fixed.toFixed(0)}`} sublabel="Monthly fixed" T={T} onClick={onSettingsClick} />
      <MetricCard label="API USAGE" value={`$${apiTotal.toFixed(2)}`} sublabel={`${data.usage.calls || 0} calls`} T={T} />
      <MetricCard label="COST/DOC" value={`$${data.stats.files > 0 ? (apiTotal / data.stats.files).toFixed(4) : '0.00'}`} sublabel={`${data.stats.files.toLocaleString()} docs`} T={T} />

      {/* Breakdown */}
      <Panel title="COST BREAKDOWN" style={{ gridColumn: 'span 2' }} T={T}>
        {[
          { label: 'Subscriptions', value: breakdown.fixed, color: T.purple, pct: (breakdown.fixed / total * 100) || 0 },
          { label: 'Claude API', value: breakdown.claude, color: T.cyan, pct: (breakdown.claude / total * 100) || 0 },
          { label: 'Local LLM (RunPod)', value: breakdown.runpod, color: T.green, pct: (breakdown.runpod / total * 100) || 0 },
          { label: 'Textract (OCR)', value: breakdown.textract, color: T.orange, pct: (breakdown.textract / total * 100) || 0 },
        ].map(item => (
          <div key={item.label} style={{ marginBottom: '0.6rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
              <span style={{ fontSize: '0.7rem', color: T.text }}>{item.label}</span>
              <div>
                <AccentText size="0.8rem" color={item.color} mono T={T}>${item.value.toFixed(2)}</AccentText>
                <span style={{ fontSize: '0.6rem', color: T.textDim, marginLeft: '0.5rem' }}>{item.pct.toFixed(1)}%</span>
              </div>
            </div>
            <div style={{ height: 6, background: T.panelBorder, borderRadius: 3 }}>
              <div style={{ height: '100%', width: `${item.pct}%`, background: item.color, borderRadius: 3 }} />
            </div>
          </div>
        ))}
      </Panel>

      {/* Daily trend */}
      <Panel title="14-DAY TREND" style={{ gridColumn: 'span 2' }} T={T}>
        {dailyCosts.length > 0 ? (
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 100 }}>
            {dailyCosts.slice(0, 14).reverse().map((d, i) => {
              const max = Math.max(...dailyCosts.map(x => x.total || 0), 0.01);
              const h = Math.max(((d.total || 0) / max) * 80, 4);
              return (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <div style={{ width: '100%', height: h, background: T.cyan, borderRadius: 2 }} title={`$${(d.total || 0).toFixed(4)}`} />
                  <span style={{ fontSize: '0.5rem', color: T.textDim, marginTop: 4 }}>
                    {new Date(d.date + 'T12:00:00').toLocaleDateString('en-US', { day: 'numeric' })}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ height: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', color: T.textDim }}>
            Loading...
          </div>
        )}
      </Panel>

      {/* Cloud vs Local */}
      <Panel title="CLOUD VS LOCAL" style={{ gridColumn: 'span 2' }} T={T}>
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.7rem', color: T.cyan }}>Cloud (Claude)</span>
              <span style={{ fontSize: '0.7rem', color: T.green }}>Local (RunPod)</span>
            </div>
            <div style={{ height: 20, background: T.panelBorder, borderRadius: 4, display: 'flex', overflow: 'hidden' }}>
              <div style={{ width: '38%', background: T.cyan }} />
              <div style={{ width: '62%', background: T.green }} />
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <AccentText size="1.5rem" color={T.green} mono glow={T.name === 'dark'} T={T}>62%</AccentText>
            <div style={{ fontSize: '0.6rem', color: T.textDim }}>Local</div>
          </div>
        </div>
      </Panel>

      {/* Projections */}
      <Panel title="PROJECTIONS" style={{ gridColumn: 'span 2' }} T={T}>
        <div style={{ display: 'flex', gap: '1.5rem' }}>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace' }}>END OF MONTH</div>
            <AccentText size="1.2rem" color={T.text} mono T={T}>${(total * 1.1).toFixed(0)}</AccentText>
          </div>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace' }}>QUARTERLY</div>
            <AccentText size="1.2rem" color={T.text} mono T={T}>${(total * 3.2).toFixed(0)}</AccentText>
          </div>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace' }}>ANNUAL</div>
            <AccentText size="1.2rem" color={T.text} mono T={T}>${(total * 12.5).toFixed(0)}</AccentText>
          </div>
        </div>
      </Panel>
    </div>
  );
}

// =============================================================================
// OVERVIEW PAGE
// =============================================================================

function OverviewPage({ T, data, flow, selectedNode, onNodeClick, activity }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.75rem' }}>
      <MetricCard label={`${data.month.month_name || 'DEC'} SPEND`} value={`$${(data.month.total || 0).toFixed(0)}`} sublabel="Total" T={T} />
      <MetricCard label="API USAGE" value={`$${(data.usage.total || 0).toFixed(2)}`} sublabel={`${data.usage.calls || 0} calls`} status={0} T={T} />
      <MetricCard label="DOCUMENTS" value={(data.stats.files || 0).toLocaleString()} sublabel="Processed" status={0} T={T} />
      <MetricCard label="LOCAL %" value="62%" sublabel="Cost savings" status={0} T={T} />
      <MetricCard label="UPTIME" value="99.9%" sublabel="30 days" status={0} T={T} />

      <SpendBreakdown data={{ fixed: data.month.fixed, claude: data.usage.claude, runpod: data.usage.runpod, textract: data.usage.textract }} T={T} />
      <SystemTopology flow={flow} onNodeClick={onNodeClick} selectedNode={selectedNode} T={T} />

      <Panel title="STORAGE" style={{ gridColumn: 'span 2' }} T={T}>
        <div style={{ display: 'flex', gap: '1.5rem' }}>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '0.3rem' }}>STRUCTURED</div>
            <AccentText size="1.2rem" color={T.purple} mono glow={T.name === 'dark'} T={T}>{(data.stats.rows || 0).toLocaleString()}</AccentText>
            <div style={{ fontSize: '0.6rem', color: T.textDim }}>rows</div>
          </div>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '0.3rem' }}>VECTOR</div>
            <AccentText size="1.2rem" color={T.cyan} mono glow={T.name === 'dark'} T={T}>{(data.stats.chunks || 0).toLocaleString()}</AccentText>
            <div style={{ fontSize: '0.6rem', color: T.textDim }}>chunks</div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '0.3rem' }}>RATIO</div>
            <div style={{ height: 6, background: T.panelBorder, borderRadius: 3, marginTop: '0.5rem' }}>
              <div style={{ height: '100%', width: '60%', background: `linear-gradient(90deg, ${T.purple}, ${T.cyan})`, borderRadius: 3 }} />
            </div>
          </div>
        </div>
      </Panel>

      <ActivityLog entries={activity} T={T} />
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function SystemMonitor() {
  const [themeName, setThemeName] = useState(() => localStorage.getItem('xlr8-theme') || 'dark');
  const [activePage, setActivePage] = useState('overview');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [time, setTime] = useState(new Date());
  const [flow, setFlow] = useState({});
  const [activity, setActivity] = useState([]);
  const containerRef = useRef(null);

  const T = THEMES[themeName];

  const [data, setData] = useState({
    month: { total: 0, fixed: 0, api: 0, month_name: 'DEC' },
    usage: { total: 0, claude: 0, runpod: 0, textract: 0, calls: 0 },
    stats: { files: 0, rows: 0, chunks: 0 },
  });

  const toggleTheme = () => {
    const newTheme = themeName === 'dark' ? 'light' : 'dark';
    setThemeName(newTheme);
    localStorage.setItem('xlr8-theme', newTheme);
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [monthRes, usageRes, structRes] = await Promise.all([
          api.get('/status/costs/month').catch(() => ({ data: {} })),
          api.get('/status/costs?days=30').catch(() => ({ data: {} })),
          api.get('/status/structured').catch(() => ({ data: {} })),
        ]);
        setData({
          month: { total: monthRes.data?.total || 0, fixed: monthRes.data?.fixed_costs || 0, api: monthRes.data?.api_usage || 0, month_name: monthRes.data?.month_name?.toUpperCase()?.slice(0, 3) || 'DEC' },
          usage: { total: usageRes.data?.total_cost || 0, claude: usageRes.data?.by_service?.claude || 0, runpod: usageRes.data?.by_service?.runpod || 0, textract: usageRes.data?.by_service?.textract || 0, calls: usageRes.data?.record_count || 0 },
          stats: { files: structRes.data?.total_files || 0, rows: structRes.data?.total_rows || 0, chunks: 0 },
        });
      } catch (err) { console.error('Fetch error:', err); }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const animate = () => {
      const flows = ['user', 'auth', 'struct', 'semantic', 'vector', 'llm', 'cloud', 'local'];
      const active = {};
      flows.forEach(f => active[f] = Math.random() > 0.5);
      setFlow(active);
    };
    const interval = setInterval(animate, 2500);
    animate();
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const messages = [
      { message: 'CLAUDE: Response generated', status: 0, cost: 0.0034 },
      { message: 'DUCKDB: Query executed', status: 0 },
      { message: 'RAG: Context retrieved', status: 0 },
      { message: 'LLAMA: Inference complete', status: 0, cost: 0.0012 },
      { message: 'AUTH: Session validated', status: 0 },
      { message: 'VECTOR: Similarity search', status: 0 },
    ];
    const addEntry = () => {
      const msg = messages[Math.floor(Math.random() * messages.length)];
      setActivity(prev => [{ ...msg, time: new Date().toLocaleTimeString('en-US', { hour12: false }), id: Date.now() }, ...prev].slice(0, 20));
    };
    const interval = setInterval(addEntry, 3000);
    return () => clearInterval(interval);
  }, []);

  const threatCount = Object.values(THREAT_DATA).filter(t => t.level > 0).length;

  return (
    <div ref={containerRef} style={{ background: T.bg, minHeight: '100vh', color: T.text, fontFamily: "'Inter', -apple-system, sans-serif", position: 'relative', transition: 'background 0.3s ease' }}>
      {/* Header */}
      <div style={{ padding: '0.75rem 1rem', borderBottom: `1px solid ${T.panelBorder}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: T.panel }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', letterSpacing: '0.15em' }}>XLR8 PLATFORM</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: T.textBright }}>OPERATIONS CENTER</div>
          </div>
          <div style={{ padding: '0.4rem 0.75rem', background: threatCount > 0 ? T.yellowBg : T.greenBg, borderRadius: 6, border: `1px solid ${threatCount > 0 ? T.yellowDim : T.greenDim}30` }}>
            <AccentText size="0.7rem" color={threatCount > 0 ? T.yellow : T.green} mono glow={T.name === 'dark'} T={T}>
              {threatCount > 0 ? `${threatCount} ITEMS NEED REVIEW` : 'ALL SYSTEMS NOMINAL'}
            </AccentText>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Button onClick={() => setShowSettings(true)} size="sm" T={T}>⚙️ Settings</Button>
          <Button onClick={toggleFullscreen} size="sm" T={T}>{isFullscreen ? '⊙ Exit' : '⛶ Kiosk'}</Button>
          <ThemeToggle theme={T} onToggle={toggleTheme} />
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '1.2rem', fontFamily: 'monospace', color: T.green, fontWeight: 600 }}>{time.toLocaleTimeString('en-US', { hour12: false })}</div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace' }}>{time.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase()}</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ padding: '0.5rem 1rem 0', background: T.panel, borderBottom: `1px solid ${T.panelBorder}` }}>
        <NavTabs active={activePage} onChange={setActivePage} T={T} />
      </div>

      {/* Content */}
      <div style={{ padding: '1rem', paddingRight: selectedNode && activePage === 'overview' ? '380px' : '1rem', transition: 'padding-right 0.3s ease' }}>
        {activePage === 'overview' && <OverviewPage T={T} data={data} flow={flow} selectedNode={selectedNode} onNodeClick={setSelectedNode} activity={activity} />}
        {activePage === 'security' && <SecurityPage T={T} onNodeClick={setSelectedNode} />}
        {activePage === 'performance' && <PerformancePage T={T} data={data} />}
        {activePage === 'costs' && <CostsPage T={T} data={data} onSettingsClick={() => setShowSettings(true)} />}
      </div>

      {/* Threat panel */}
      {selectedNode && <ThreatPanel nodeId={selectedNode} onClose={() => setSelectedNode(null)} T={T} />}

      {/* Settings modal */}
      <SettingsModal open={showSettings} onClose={() => setShowSettings(false)} T={T} />
    </div>
  );
}
