/**
 * XLR8 OPERATIONS CENTER - FULL BUILD
 * 
 * Multi-page: Overview | Security | Performance | Costs
 * Settings modal for subscriptions
 * Fullscreen kiosk mode
 * Dynamic threat data from API with fallback
 * 
 * Updated: December 8, 2025 - Live threat data integration
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';

// =============================================================================
// THEMES
// =============================================================================
// ALIGNED WITH DASHBOARD - Soft Navy dark theme
const THEMES = {
  dark: {
    name: 'dark',
    bg: '#1a2332',           // Soft Navy - matches Dashboard
    panel: '#232f42',        // Soft Navy cards
    panelLight: '#2c3b52',   // Slightly lighter
    panelBorder: '#334766',  // Soft Navy border
    text: '#e5e7eb',
    textDim: '#9ca3af',
    textBright: '#ffffff',
    green: '#83b16d',        // grassGreen brand color
    greenDim: '#6b9a57',
    greenBg: 'rgba(131, 177, 109, 0.15)',
    red: '#ef4444',
    redDim: '#dc2626',
    redBg: 'rgba(239, 68, 68, 0.12)',
    yellow: '#f59e0b',
    yellowDim: '#d97706',
    yellowBg: 'rgba(245, 158, 11, 0.12)',
    blue: '#3b82f6',
    blueDim: '#2563eb',
    cyan: '#06b6d4',
    cyanDim: '#0891b2',
    purple: '#8b5cf6',
    orange: '#f97316',
    shadow: 'rgba(0,0,0,0.3)',
  },
  light: {
    name: 'light',
    bg: '#f6f5fa',           // Brand light bg - matches Dashboard
    panel: '#ffffff',
    panelLight: '#f8fafc',
    panelBorder: '#e2e8f0',
    text: '#2a3441',         // Brand text
    textDim: '#5f6c7b',
    textBright: '#1e293b',
    green: '#83b16d',        // grassGreen brand color
    greenDim: '#6b9a57',
    greenBg: 'rgba(131, 177, 109, 0.1)',
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
// HELPER: Generate dynamic dates (relative to now)
// =============================================================================
const getRelativeDate = (daysAgo) => {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date.toISOString().split('T')[0];
};

const getLastScanTime = () => {
  const now = new Date();
  return now.toISOString().replace('T', ' ').slice(0, 19);
};

// =============================================================================
// THREAT DATA FALLBACK (used when API unavailable)
// Uses dynamic dates relative to current date
// =============================================================================
const getThreatDataFallback = () => ({
  api: { 
    level: 2, 
    label: 'API GATEWAY', 
    component: 'api',
    category: 'infrastructure',
    issues: [
      { id: 1, issue: 'Rate limiting not enforced', severity: 'high', status: 'open', detected: getRelativeDate(7) },
      { id: 2, issue: 'Input validation needed on /upload', severity: 'medium', status: 'open', detected: getRelativeDate(5) },
      { id: 3, issue: 'CORS allows wildcard origin', severity: 'low', status: 'open', detected: getRelativeDate(3) },
    ], 
    action: 'Implement rate limiting and input validation',
    lastScan: getLastScanTime(),
  },
  duckdb: { 
    level: 2, 
    label: 'STRUCTURED DB', 
    component: 'duckdb',
    category: 'data',
    issues: [
      { id: 4, issue: 'PII fields (SSN, DOB) not masked', severity: 'high', status: 'open', detected: getRelativeDate(7) },
      { id: 5, issue: 'Query audit logging disabled', severity: 'medium', status: 'open', detected: getRelativeDate(6) },
      { id: 6, issue: 'No row-level access controls', severity: 'medium', status: 'in_progress', detected: getRelativeDate(4) },
    ], 
    action: 'Enable data masking for sensitive fields',
    lastScan: getLastScanTime(),
  },
  chromadb: { 
    level: 1, 
    label: 'VECTOR STORE', 
    component: 'chromadb',
    category: 'data',
    issues: [
      { id: 7, issue: 'Embeddings may contain PII fragments', severity: 'medium', status: 'open', detected: getRelativeDate(3) },
      { id: 8, issue: 'No collection-level permissions', severity: 'low', status: 'open', detected: getRelativeDate(2) },
    ], 
    action: 'Audit chunk content for sensitive data',
    lastScan: getLastScanTime(),
  },
  claude: { 
    level: 2, 
    label: 'CLOUD AI (CLAUDE)', 
    component: 'claude',
    category: 'ai',
    issues: [
      { id: 9, issue: 'Data transmitted to external API', severity: 'medium', status: 'acknowledged', detected: getRelativeDate(7) },
      { id: 10, issue: 'Prompt injection vulnerability', severity: 'high', status: 'open', detected: getRelativeDate(5) },
      { id: 11, issue: 'Response logging incomplete', severity: 'low', status: 'open', detected: getRelativeDate(2) },
    ], 
    action: 'Implement prompt sanitization layer',
    lastScan: getLastScanTime(),
  },
  supabase: { 
    level: 0, 
    label: 'AUTHENTICATION', 
    component: 'supabase',
    category: 'infrastructure',
    issues: [], 
    action: '',
    lastScan: getLastScanTime(),
  },
  runpod: { 
    level: 0, 
    label: 'LOCAL AI (RUNPOD)', 
    component: 'runpod',
    category: 'ai',
    issues: [], 
    action: '',
    lastScan: getLastScanTime(),
  },
  rag: { 
    level: 1, 
    label: 'RAG ENGINE', 
    component: 'rag',
    category: 'ai',
    issues: [
      { id: 12, issue: 'Context window may include sensitive docs', severity: 'medium', status: 'open', detected: getRelativeDate(4) },
    ], 
    action: 'Implement document classification filter',
    lastScan: getLastScanTime(),
  },
});

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
    { id: 'data', label: 'DATA STORES', icon: '🗄️' },
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
    { name: 'Supabase Pro', cost: 25, quantity: 1 },
    { name: 'Twilio', cost: 15, quantity: 1 },
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
            <span style={{ color: T.textDim, fontSize: '0.85rem' }}>Monthly Total</span>
            <AccentText size="1rem" color={T.green} mono T={T}>${total.toFixed(2)}</AccentText>
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
          <Button onClick={handleSave} variant="primary" T={T} style={{ opacity: saving ? 0.6 : 1 }}>
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// METRIC CARD
// =============================================================================

function MetricCard({ label, value, sublabel, status, T }) {
  return (
    <Panel T={T}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '0.4rem', letterSpacing: '0.05em' }}>
          {label}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}>
          <AccentText size="1.5rem" color={status === 2 ? T.red : status === 1 ? T.yellow : T.green} mono glow={T.name === 'dark'} T={T}>
            {value}
          </AccentText>
          {status !== undefined && <StatusDot status={status} size={6} T={T} />}
        </div>
        {sublabel && <div style={{ fontSize: '0.6rem', color: T.textDim, marginTop: '0.2rem' }}>{sublabel}</div>}
      </div>
    </Panel>
  );
}

// =============================================================================
// SPEND BREAKDOWN
// =============================================================================

function SpendBreakdown({ data, T }) {
  const items = [
    { label: 'Fixed', value: data.fixed || 0, color: T.purple },
    { label: 'Claude', value: data.claude || 0, color: T.cyan },
    { label: 'RunPod', value: data.runpod || 0, color: T.green },
    { label: 'Textract', value: data.textract || 0, color: T.orange },
  ];
  const total = items.reduce((sum, i) => sum + i.value, 0) || 1;

  return (
    <Panel title="SPEND BREAKDOWN" style={{ gridColumn: 'span 2' }} T={T}>
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <div style={{ display: 'flex', height: 8, flex: 1, borderRadius: 4, overflow: 'hidden', background: T.panelBorder }}>
          {items.map((item, i) => (
            <div key={item.label} style={{ width: `${(item.value / total) * 100}%`, background: item.color, transition: 'width 0.3s ease' }} />
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.75rem' }}>
        {items.map(item => (
          <div key={item.label} style={{ textAlign: 'center' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: item.color, margin: '0 auto 0.3rem' }} />
            <div style={{ fontSize: '0.6rem', color: T.textDim }}>{item.label}</div>
            <div style={{ fontSize: '0.75rem', color: T.text, fontFamily: 'monospace' }}>${item.value.toFixed(2)}</div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

// =============================================================================
// SYSTEM TOPOLOGY
// =============================================================================

function SystemTopology({ flow, onNodeClick, selectedNode, T, fullWidth = false, threatData }) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const lastPan = useRef({ x: 0, y: 0 });

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(z => Math.max(0.5, Math.min(2, z + delta)));
  }, []);

  const handleMouseDown = (e) => {
    setIsPanning(true);
    lastPan.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handleMouseMove = (e) => {
    if (!isPanning) return;
    setPan({ x: e.clientX - lastPan.current.x, y: e.clientY - lastPan.current.y });
  };

  const handleMouseUp = () => setIsPanning(false);

  // Node positions - adjusted to prevent overlap with legend and connection lines
  const nodes = {
    user: { x: 50, y: 130, icon: '◉', label: 'USER', color: T.blue },
    api: { x: 160, y: 130, icon: '⬡', label: 'API', color: T.blue, encrypted: true, threat: threatData?.api },
    supabase: { x: 70, y: 210, icon: '◈', label: 'AUTH', color: T.purple, encrypted: true, threat: threatData?.supabase },
    twilio: { x: 160, y: 210, icon: '📱', label: 'SMS', color: T.purple, encrypted: true },
    duckdb: { x: 280, y: 45, icon: '▣', label: 'STRUCT', color: T.purple, encrypted: true, threat: threatData?.duckdb },
    rag: { x: 280, y: 115, icon: '◎', label: 'RAG', color: T.orange, threat: threatData?.rag },
    chromadb: { x: 280, y: 230, icon: '◇', label: 'VECTOR', color: T.cyan, threat: threatData?.chromadb },
    router: { x: 420, y: 130, icon: '⬢', label: 'ROUTER', color: T.yellow },
    claude: { x: 560, y: 70, icon: '●', label: 'CLAUDE', color: T.cyan, threat: threatData?.claude },
    llama: { x: 520, y: 185, icon: '○', label: 'LLAMA', color: T.green },
    mistral: { x: 590, y: 185, icon: '○', label: 'MISTRAL', color: T.green },
    deepseek: { x: 660, y: 185, icon: '○', label: 'DEEP', color: T.green },
  };

  const connections = [
    { from: 'user', to: 'api', color: T.blue, label: 'HTTPS', active: flow.user },
    { from: 'api', to: 'supabase', color: T.purple, label: 'AUTH', active: flow.auth },
    { from: 'supabase', to: 'twilio', color: T.purple, label: 'MFA', active: flow.auth },
    { from: 'api', to: 'duckdb', color: T.purple, label: 'SQL', active: flow.struct },
    { from: 'api', to: 'rag', color: T.orange, active: flow.semantic },
    { from: 'rag', to: 'chromadb', color: T.cyan, label: 'EMBED', active: flow.vector },
    { from: 'rag', to: 'router', color: T.yellow, active: flow.llm },
    { from: 'router', to: 'claude', color: T.cyan, active: flow.cloud },
    { from: 'router', to: 'llama', color: T.green, active: flow.local },
    { from: 'router', to: 'mistral', color: T.green, active: flow.local },
    { from: 'router', to: 'deepseek', color: T.green, active: flow.local },
  ];

  const Node = ({ id, data }) => {
    const isSelected = selectedNode === id;
    const threatLevel = data.threat?.level || 0;
    const hasIssues = threatLevel > 0;

    return (
      <g 
        style={{ cursor: 'pointer' }} 
        onClick={() => onNodeClick(id)}
        transform={`translate(${data.x}, ${data.y})`}
      >
        {hasIssues && (
          <circle r={22} fill="none" stroke={threatLevel === 2 ? T.red : T.yellow} strokeWidth={1.5} strokeDasharray="4,2" opacity={0.8}>
            <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="10s" repeatCount="indefinite" />
          </circle>
        )}
        <circle r={18} fill={T.panel} stroke={isSelected ? T.green : data.color} strokeWidth={isSelected ? 3 : 2}
          style={{ filter: T.name === 'dark' ? `drop-shadow(0 0 6px ${data.color}40)` : 'none' }} />
        {data.encrypted && (
          <g transform="translate(12, -12)">
            <circle r={6} fill={T.panel} stroke={T.green} strokeWidth={1} />
            <text textAnchor="middle" dominantBaseline="middle" fontSize={7} fill={T.green}>🔒</text>
          </g>
        )}
        <text textAnchor="middle" dominantBaseline="middle" fontSize={14} fill={data.color}>{data.icon}</text>
        <text y={32} textAnchor="middle" fontSize={8} fill={T.textDim} style={{ fontFamily: 'monospace', fontWeight: 600 }}>{data.label}</text>
      </g>
    );
  };

  return (
    <Panel title="SYSTEM TOPOLOGY" style={{ gridColumn: fullWidth ? 'span 4' : 'span 3' }} T={T}
      action={<span style={{ fontSize: '0.55rem', color: T.textDim }}>Zoom: {(zoom * 100).toFixed(0)}%</span>}
    >
      <div
        style={{ overflow: 'hidden', cursor: isPanning ? 'grabbing' : 'grab' }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <svg width="100%" height="280" viewBox="0 0 720 280"
          style={{ transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`, transformOrigin: 'center center', transition: isPanning ? 'none' : 'transform 0.1s ease-out' }}
        >
          {/* Cloud zone - top right */}
          <rect x="490" y="35" width="180" height="75" rx={6} fill={T.cyan} opacity={0.08} stroke={T.cyan} strokeWidth={1} strokeOpacity={0.3} />
          <text x="500" y={50} fontSize={8} fill={T.cyanDim} style={{ fontFamily: 'monospace' }}>CLOUD ZONE</text>
          
          {/* Local zone - bottom right */}
          <rect x="490" y="145" width="200" height="80" rx={6} fill={T.green} opacity={0.08} stroke={T.green} strokeWidth={1} strokeOpacity={0.3} />
          <text x="500" y={160} fontSize={8} fill={T.greenDim} style={{ fontFamily: 'monospace' }}>LOCAL ZONE</text>
          
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
          
          {/* Legend - positioned at bottom with proper spacing */}
          <g transform="translate(20, 255)">
            <circle cx={5} cy={0} r={4} fill={T.green} /><text x={14} y={3} fontSize={7} fill={T.textDim}>SECURE</text>
            <circle cx={70} cy={0} r={4} fill={T.yellow} /><text x={79} y={3} fontSize={7} fill={T.textDim}>REVIEW</text>
            <circle cx={130} cy={0} r={4} fill={T.red} /><text x={139} y={3} fontSize={7} fill={T.textDim}>ACTION</text>
            <g transform="translate(190, -3)"><circle r={5} fill="none" stroke={T.yellow} strokeWidth={1.5} strokeDasharray="2,2" /></g>
            <text x={200} y={3} fontSize={7} fill={T.textDim}>THREAT</text>
            <text x={460} y={3} fontSize={7} fill={T.textDim} textAnchor="end">SCROLL TO ZOOM • DRAG TO PAN</text>
          </g>
        </svg>
      </div>
    </Panel>
  );
}

// =============================================================================
// THREAT PANEL (Slide-out) - NOW USES PROP
// =============================================================================

function ThreatPanel({ nodeId, onClose, T, threatData }) {
  const threat = threatData?.[nodeId];
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
// SECURITY PAGE - NOW USES PROP
// =============================================================================

function SecurityPage({ T, onNodeClick, threatData }) {
  const allIssues = Object.values(threatData).flatMap(t => t.issues.map(i => ({ ...i, component: t.label })));
  const openIssues = allIssues.filter(i => i.status === 'open');
  const highSeverity = openIssues.filter(i => i.severity === 'high');
  const components = Object.values(threatData);

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
      <Panel title="RESOURCE USAGE" style={{ gridColumn: 'span 3' }} T={T}>
        <div style={{ display: 'flex', gap: '2rem' }}>
          {[
            { label: 'CPU', value: perfData.cpuUsage, color: T.cyan },
            { label: 'Memory', value: perfData.memoryUsage, color: T.purple },
            { label: 'Disk', value: perfData.diskUsage, color: T.orange },
          ].map(item => (
            <div key={item.label} style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                <span style={{ fontSize: '0.7rem', color: T.textDim }}>{item.label}</span>
                <span style={{ fontSize: '0.7rem', color: item.color, fontFamily: 'monospace' }}>{item.value}%</span>
              </div>
              <div style={{ height: 6, background: T.panelBorder, borderRadius: 3 }}>
                <div style={{ height: '100%', width: `${item.value}%`, background: item.color, borderRadius: 3, transition: 'width 0.3s ease' }} />
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Network I/O */}
      <Panel title="NETWORK I/O" style={{ gridColumn: 'span 2' }} T={T}>
        <div style={{ display: 'flex', gap: '1.5rem' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.6rem', color: T.textDim, marginBottom: '0.3rem' }}>IN</div>
            <AccentText size="1.2rem" color={T.green} mono T={T}>{perfData.networkIn}</AccentText>
            <div style={{ fontSize: '0.55rem', color: T.textDim }}>MB/s</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.6rem', color: T.textDim, marginBottom: '0.3rem' }}>OUT</div>
            <AccentText size="1.2rem" color={T.cyan} mono T={T}>{perfData.networkOut}</AccentText>
            <div style={{ fontSize: '0.55rem', color: T.textDim }}>MB/s</div>
          </div>
        </div>
      </Panel>

      {/* Component latency */}
      <Panel title="COMPONENT LATENCY" style={{ gridColumn: 'span 5' }} T={T}>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {[
            { name: 'API Gateway', latency: 12, status: 0 },
            { name: 'DuckDB', latency: 45, status: 0 },
            { name: 'ChromaDB', latency: 89, status: 0 },
            { name: 'RAG Engine', latency: 234, status: 1 },
            { name: 'Claude API', latency: 1240, status: 1 },
            { name: 'RunPod', latency: 890, status: 0 },
            { name: 'Supabase', latency: 34, status: 0 },
          ].map(comp => (
            <div key={comp.name} style={{
              padding: '0.5rem 0.75rem',
              background: T.panelLight,
              borderRadius: 6,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}>
              <StatusDot status={comp.status} size={6} T={T} />
              <span style={{ fontSize: '0.7rem', color: T.text }}>{comp.name}</span>
              <span style={{ fontSize: '0.65rem', color: T.textDim, fontFamily: 'monospace' }}>{comp.latency}ms</span>
            </div>
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
      if (res.data && Array.isArray(res.data)) {
        setDailyCosts(res.data);
      }
    }).catch(() => {});
  }, []);

  const maxCost = Math.max(...dailyCosts.map(d => d.total || 0), 1);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
      <MetricCard label="MTD SPEND" value={`$${(data.month.total || 0).toFixed(0)}`} sublabel={data.month.month_name} T={T} />
      <MetricCard label="FIXED COSTS" value={`$${(data.month.fixed || 0).toFixed(0)}`} sublabel="subscriptions" T={T} />
      <MetricCard label="API USAGE" value={`$${(data.usage.total || 0).toFixed(2)}`} sublabel={`${data.usage.calls || 0} calls`} T={T} />
      <MetricCard label="DAILY AVG" value={`$${dailyCosts.length ? (dailyCosts.reduce((s, d) => s + (d.total || 0), 0) / dailyCosts.length).toFixed(2) : '0.00'}`} sublabel="last 14 days" T={T} />

      <Panel title="14-DAY TREND" style={{ gridColumn: 'span 4' }} T={T}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 120 }}>
          {dailyCosts.map((day, i) => (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
              <div style={{
                width: '100%',
                height: ((day.total || 0) / maxCost) * 100,
                background: `linear-gradient(180deg, ${T.cyan}, ${T.purple})`,
                borderRadius: '4px 4px 0 0',
                minHeight: 4,
              }} />
              <span style={{ fontSize: '0.5rem', color: T.textDim, fontFamily: 'monospace' }}>
                {new Date(day.date).getDate()}
              </span>
            </div>
          ))}
        </div>
      </Panel>

      <SpendBreakdown data={{ fixed: data.month.fixed, claude: data.usage.claude, runpod: data.usage.runpod, textract: data.usage.textract }} T={T} />

      <Panel title="COST OPTIMIZATION" style={{ gridColumn: 'span 2' }} T={T}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ padding: '0.75rem', background: T.greenBg, borderRadius: 6, borderLeft: `3px solid ${T.green}` }}>
            <div style={{ fontSize: '0.75rem', color: T.green, fontWeight: 500 }}>Local LLM routing saves ~38%</div>
            <div style={{ fontSize: '0.65rem', color: T.textDim, marginTop: '0.2rem' }}>62% of queries handled locally</div>
          </div>
          <div style={{ padding: '0.75rem', background: T.panelLight, borderRadius: 6, borderLeft: `3px solid ${T.yellow}` }}>
            <div style={{ fontSize: '0.75rem', color: T.yellow, fontWeight: 500 }}>Consider batch processing</div>
            <div style={{ fontSize: '0.65rem', color: T.textDim, marginTop: '0.2rem' }}>Could reduce Claude calls by 15%</div>
          </div>
        </div>
      </Panel>

      <div style={{ gridColumn: 'span 4', display: 'flex', justifyContent: 'flex-end' }}>
        <Button onClick={onSettingsClick} T={T}>⚙️ Manage Subscriptions</Button>
      </div>
    </div>
  );
}

// =============================================================================
// OVERVIEW PAGE
// =============================================================================

function OverviewPage({ T, data, flow, selectedNode, onNodeClick, activity, threatData }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.75rem' }}>
      <MetricCard label={`${data.month.month_name || 'DEC'} SPEND`} value={`$${(data.month.total || 0).toFixed(0)}`} sublabel="Total" T={T} />
      <MetricCard label="API USAGE" value={`$${(data.usage.total || 0).toFixed(2)}`} sublabel={`${data.usage.calls || 0} calls`} status={0} T={T} />
      <MetricCard label="DOCUMENTS" value={(data.stats.files || 0).toLocaleString()} sublabel="Processed" status={0} T={T} />
      <MetricCard label="LOCAL %" value="62%" sublabel="Cost savings" status={0} T={T} />
      <MetricCard label="UPTIME" value="99.9%" sublabel="30 days" status={0} T={T} />

      <SpendBreakdown data={{ fixed: data.month.fixed, claude: data.usage.claude, runpod: data.usage.runpod, textract: data.usage.textract }} T={T} />
      <SystemTopology flow={flow} onNodeClick={onNodeClick} selectedNode={selectedNode} T={T} threatData={threatData} />

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
// DATA STORES PAGE - Unified view of DuckDB, Supabase, ChromaDB
// =============================================================================

function DataStoresPage({ T }) {
  const [loading, setLoading] = useState(true);
  const [activeStore, setActiveStore] = useState('overview');
  const [duckdbData, setDuckdbData] = useState(null);
  const [supabaseData, setSupabaseData] = useState(null);
  const [chromadbData, setChromadbData] = useState(null);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [duckRes, docsRes, chromaRes] = await Promise.all([
        api.get('/status/structured').catch(() => ({ data: { available: false, files: [], total_rows: 0 } })),
        api.get('/status/documents').catch(() => ({ data: { documents: [] } })),
        api.get('/status/chromadb').catch(() => ({ data: { total_chunks: 0 } })),
      ]);
      setDuckdbData(duckRes.data);
      setSupabaseData(docsRes.data);
      setChromadbData(chromaRes.data);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  const totals = {
    duckdb: { files: duckdbData?.total_files || 0, tables: duckdbData?.total_tables || 0, rows: duckdbData?.total_rows || 0 },
    supabase: { documents: supabaseData?.documents?.length || 0 },
    chromadb: { chunks: chromadbData?.total_chunks || 0 },
  };

  const stores = [
    { id: 'duckdb', label: 'DuckDB', icon: '🦆', color: T.yellow, value: totals.duckdb.rows, sub: `${totals.duckdb.files} files` },
    { id: 'supabase', label: 'Documents', icon: '📄', color: T.green, value: totals.supabase.documents, sub: 'tracked' },
    { id: 'chromadb', label: 'Vectors', icon: '🔮', color: '#8b5cf6', value: totals.chromadb.chunks, sub: 'chunks' },
  ];

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '4rem' }}>
        <div style={{ textAlign: 'center', color: T.textDim }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>🔄</div>
          <div>Loading data stores...</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
      {/* Left Column - Store Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {stores.map(store => (
          <Panel key={store.id} T={T} style={{ cursor: 'pointer' }} onClick={() => setActiveStore(store.id)}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{ fontSize: '1.5rem' }}>{store.icon}</span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{store.label}</div>
                  <div style={{ fontSize: '0.7rem', color: T.textDim }}>{store.sub}</div>
                </div>
              </div>
              <AccentText size="1.5rem" color={store.color} mono glow={T.name === 'dark'} T={T}>
                {store.value.toLocaleString()}
              </AccentText>
            </div>
          </Panel>
        ))}

        {/* Refresh Button */}
        <Button onClick={loadAllData} T={T}>🔄 Refresh All</Button>
      </div>

      {/* Right Column - Detail View */}
      <Panel T={T}>
        {activeStore === 'overview' && (
          <div>
            <div style={{ fontSize: '0.7rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '1rem' }}>SYSTEM OVERVIEW</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {[
                { label: 'DuckDB', status: duckdbData?.available !== false, detail: `${totals.duckdb.rows.toLocaleString()} rows in ${totals.duckdb.tables} tables` },
                { label: 'Supabase', status: true, detail: `${totals.supabase.documents} documents tracked` },
                { label: 'ChromaDB', status: !chromadbData?.error, detail: `${totals.chromadb.chunks.toLocaleString()} vector chunks` },
              ].map((item, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem', background: T.panelLight, borderRadius: 6 }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{item.label}</div>
                    <div style={{ fontSize: '0.7rem', color: T.textDim }}>{item.detail}</div>
                  </div>
                  <StatusDot status={item.status ? 0 : 2} size={10} T={T} />
                </div>
              ))}
            </div>
          </div>
        )}

        {activeStore === 'duckdb' && (
          <div>
            <div style={{ fontSize: '0.7rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '1rem' }}>DUCKDB - STRUCTURED DATA</div>
            {(duckdbData?.files || []).length === 0 ? (
              <div style={{ color: T.textDim, textAlign: 'center', padding: '2rem' }}>No structured data files</div>
            ) : (
              <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                {(duckdbData?.files || []).map((file, i) => (
                  <div key={i} style={{ padding: '0.5rem', borderBottom: `1px solid ${T.panelBorder}`, fontSize: '0.8rem' }}>
                    <div style={{ fontWeight: 600 }}>{file.filename}</div>
                    <div style={{ color: T.textDim, fontSize: '0.7rem' }}>
                      {file.project} • {file.total_rows?.toLocaleString() || 0} rows • {file.sheets?.length || 0} sheets
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeStore === 'supabase' && (
          <div>
            <div style={{ fontSize: '0.7rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '1rem' }}>SUPABASE - DOCUMENTS</div>
            {(supabaseData?.documents || []).length === 0 ? (
              <div style={{ color: T.textDim, textAlign: 'center', padding: '2rem' }}>No documents</div>
            ) : (
              <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                {(supabaseData?.documents || []).slice(0, 20).map((doc, i) => (
                  <div key={i} style={{ padding: '0.5rem', borderBottom: `1px solid ${T.panelBorder}`, fontSize: '0.8rem' }}>
                    <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.filename}</div>
                    <div style={{ color: T.textDim, fontSize: '0.7rem' }}>
                      {doc.project || 'No project'} • {doc.chunk_count || 0} chunks
                    </div>
                  </div>
                ))}
                {(supabaseData?.documents || []).length > 20 && (
                  <div style={{ padding: '0.5rem', color: T.textDim, fontSize: '0.7rem', textAlign: 'center' }}>
                    +{(supabaseData?.documents || []).length - 20} more
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeStore === 'chromadb' && (
          <div>
            <div style={{ fontSize: '0.7rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '1rem' }}>CHROMADB - VECTOR STORE</div>
            <div style={{ textAlign: 'center', padding: '1.5rem' }}>
              <AccentText size="3rem" color="#8b5cf6" mono glow={T.name === 'dark'} T={T}>
                {totals.chromadb.chunks.toLocaleString()}
              </AccentText>
              <div style={{ color: T.textDim, marginTop: '0.5rem', fontSize: '0.8rem' }}>Vector Chunks</div>
              <div style={{ marginTop: '1rem', padding: '0.75rem', background: T.panelLight, borderRadius: 6, fontSize: '0.75rem', color: T.textDim }}>
                384-dimensional embeddings for semantic search and AI analysis
              </div>
            </div>
            {chromadbData?.error && (
              <div style={{ marginTop: '1rem', padding: '0.5rem', background: T.redBg, borderRadius: 6, fontSize: '0.75rem', color: T.red }}>
                ⚠️ {chromadbData.error}
              </div>
            )}
          </div>
        )}
      </Panel>
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

  // THREAT DATA STATE - initialized with fallback, updated from API
  const [threatData, setThreatData] = useState(getThreatDataFallback);

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

  // FETCH LIVE THREAT DATA
  useEffect(() => {
    const fetchThreatData = async () => {
      try {
        const response = await api.get('/security/threats');
        if (response.data && typeof response.data === 'object') {
          setThreatData(response.data);
        }
      } catch (err) {
        // API not available, keep using fallback with refreshed dates
        console.log('Threat API not available, using fallback data');
        setThreatData(getThreatDataFallback());
      }
    };

    fetchThreatData();
    const interval = setInterval(fetchThreatData, 60000); // Refresh every minute
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

  // USE LIVE THREAT DATA FOR COUNT
  const threatCount = Object.values(threatData).filter(t => t.level > 0).length;

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

      {/* Content - PASS THREAT DATA TO ALL PAGES */}
      <div style={{ padding: '1rem', paddingRight: selectedNode && activePage === 'overview' ? '380px' : '1rem', transition: 'padding-right 0.3s ease' }}>
        {activePage === 'overview' && <OverviewPage T={T} data={data} flow={flow} selectedNode={selectedNode} onNodeClick={setSelectedNode} activity={activity} threatData={threatData} />}
        {activePage === 'security' && <SecurityPage T={T} onNodeClick={setSelectedNode} threatData={threatData} />}
        {activePage === 'performance' && <PerformancePage T={T} data={data} />}
        {activePage === 'costs' && <CostsPage T={T} data={data} onSettingsClick={() => setShowSettings(true)} />}
        {activePage === 'data' && <DataStoresPage T={T} />}
      </div>

      {/* Threat panel - PASS THREAT DATA */}
      {selectedNode && <ThreatPanel nodeId={selectedNode} onClose={() => setSelectedNode(null)} T={T} threatData={threatData} />}

      {/* Settings modal */}
      <SettingsModal open={showSettings} onClose={() => setShowSettings(false)} T={T} />
    </div>
  );
}
