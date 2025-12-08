/**
 * XLR8 OPERATIONS CENTER
 * 
 * Combined Light/Dark Theme with Toggle
 * Zoomable System Topology
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';

// =============================================================================
// THEMES
// =============================================================================
const THEMES = {
  dark: {
    name: 'dark',
    bg: '#1a1f2e',           // Softer dark (not black)
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

// Security/Threat Data
const THREATS = {
  api: { level: 2, label: 'API GATEWAY', issues: ['Rate limiting not enforced', 'Input validation needed'], action: 'Implement throttling' },
  duckdb: { level: 2, label: 'STRUCTURED DB', issues: ['PII exposure risk', 'Query logging disabled'], action: 'Enable data masking' },
  chromadb: { level: 1, label: 'VECTOR STORE', issues: ['Embeddings may contain PII'], action: 'Audit chunk content' },
  claude: { level: 2, label: 'CLOUD AI', issues: ['External data transmission', 'Prompt injection risk'], action: 'Sanitize prompts' },
  supabase: { level: 0, label: 'AUTH', issues: [], action: '' },
  runpod: { level: 0, label: 'LOCAL AI', issues: [], action: '' },
};

// =============================================================================
// CONTEXT
// =============================================================================
const ThemeContext = React.createContext();

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

const Panel = ({ children, title, status, style = {}, T }) => (
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
        {status !== undefined && <StatusDot status={status} size={6} T={T} />}
      </div>
    )}
    <div style={{ padding: '0.875rem' }}>{children}</div>
  </div>
);

// =============================================================================
// METRIC CARDS
// =============================================================================

function MetricCard({ label, value, unit, sublabel, trend, status, T }) {
  return (
    <Panel status={status} T={T}>
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

function SystemTopology({ status, flow, onNodeClick, selectedNode, T }) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [startPan, setStartPan] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  const nodes = {
    user: { x: 60, y: 140, icon: '◉', label: 'USER', color: T.blue },
    api: { x: 180, y: 140, icon: '⬡', label: 'API', color: T.blue, encrypted: true, threat: THREATS.api },
    supabase: { x: 180, y: 240, icon: '◈', label: 'AUTH', color: T.purple, encrypted: true, threat: THREATS.supabase },
    duckdb: { x: 340, y: 70, icon: '▣', label: 'STRUCT', color: T.purple, encrypted: true, threat: THREATS.duckdb },
    rag: { x: 340, y: 140, icon: '◎', label: 'RAG', color: T.orange },
    chromadb: { x: 340, y: 210, icon: '◇', label: 'VECTOR', color: T.cyan, threat: THREATS.chromadb },
    router: { x: 480, y: 140, icon: '⬢', label: 'ROUTER', color: T.yellow },
    claude: { x: 620, y: 80, icon: '●', label: 'CLAUDE', color: T.cyan, threat: THREATS.claude },
    llama: { x: 580, y: 200, icon: '○', label: 'LLAMA', color: T.green, threat: THREATS.runpod },
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

  // Zoom handlers
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

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

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
        {/* Threat ring */}
        {threatLevel > 0 && (
          <circle
            r={28}
            fill="none"
            stroke={threatLevel === 2 ? T.red : T.yellow}
            strokeWidth={2}
            strokeDasharray="4,4"
            opacity={0.6}
          >
            <animateTransform
              attributeName="transform"
              type="rotate"
              from="0"
              to="360"
              dur="10s"
              repeatCount="indefinite"
            />
          </circle>
        )}
        
        {/* Main node */}
        <circle
          r={isSelected ? 24 : 20}
          fill={T.panel}
          stroke={isSelected ? T.textBright : data.color}
          strokeWidth={isSelected ? 2.5 : 2}
          style={{ 
            filter: T.name === 'dark' && isSelected ? `drop-shadow(0 0 12px ${data.color})` : 
                   isSelected ? `drop-shadow(0 2px 8px ${T.shadow})` : 'none',
            transition: 'all 0.2s ease',
          }}
        />
        
        {/* Icon */}
        <text y={4} textAnchor="middle" fontSize={14} fill={data.color} style={{ fontFamily: 'monospace' }}>
          {data.icon}
        </text>
        
        {/* Label */}
        <text y={38} textAnchor="middle" fontSize={8} fill={T.textDim} style={{ fontFamily: 'monospace', letterSpacing: '0.05em' }}>
          {data.label}
        </text>
        
        {/* Encrypted badge */}
        {data.encrypted && (
          <g transform="translate(14, -14)">
            <circle r={7} fill={T.panel} stroke={T.yellow} strokeWidth={1.5} />
            <text y={3} textAnchor="middle" fontSize={7} fill={T.yellow}>🔒</text>
          </g>
        )}
        
        {/* Status indicator */}
        <circle
          cx={-14}
          cy={-14}
          r={4}
          fill={threatLevel === 2 ? T.red : threatLevel === 1 ? T.yellow : T.green}
          style={{ filter: T.name === 'dark' ? `drop-shadow(0 0 4px ${threatLevel === 2 ? T.red : threatLevel === 1 ? T.yellow : T.green})` : 'none' }}
        />
      </g>
    );
  };

  return (
    <Panel title="SYSTEM TOPOLOGY" style={{ gridColumn: 'span 2', position: 'relative' }} T={T}>
      {/* Zoom controls */}
      <div style={{
        position: 'absolute',
        top: 48,
        right: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        zIndex: 5,
      }}>
        <button
          onClick={() => setZoom(z => Math.min(z + 0.2, 3))}
          style={{
            width: 28,
            height: 28,
            borderRadius: 4,
            border: `1px solid ${T.panelBorder}`,
            background: T.panelLight,
            color: T.text,
            cursor: 'pointer',
            fontSize: '1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >+</button>
        <button
          onClick={() => setZoom(z => Math.max(z - 0.2, 0.5))}
          style={{
            width: 28,
            height: 28,
            borderRadius: 4,
            border: `1px solid ${T.panelBorder}`,
            background: T.panelLight,
            color: T.text,
            cursor: 'pointer',
            fontSize: '1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >−</button>
        <button
          onClick={resetView}
          style={{
            width: 28,
            height: 28,
            borderRadius: 4,
            border: `1px solid ${T.panelBorder}`,
            background: T.panelLight,
            color: T.textDim,
            cursor: 'pointer',
            fontSize: '0.6rem',
            fontFamily: 'monospace',
          }}
        >⟲</button>
      </div>

      {/* Zoom level indicator */}
      <div style={{
        position: 'absolute',
        bottom: 12,
        right: 12,
        fontSize: '0.6rem',
        color: T.textDim,
        fontFamily: 'monospace',
        background: T.panelLight,
        padding: '2px 6px',
        borderRadius: 3,
        border: `1px solid ${T.panelBorder}`,
      }}>
        {Math.round(zoom * 100)}%
      </div>

      <div
        ref={containerRef}
        style={{ overflow: 'hidden', cursor: isPanning ? 'grabbing' : 'grab' }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <svg 
          width="100%" 
          height="280" 
          viewBox="0 0 780 280"
          style={{
            transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
            transformOrigin: 'center center',
            transition: isPanning ? 'none' : 'transform 0.1s ease-out',
          }}
        >
          {/* Zone backgrounds */}
          <rect x="550" y="40" width="220" height="80" rx={6} fill={T.cyan} opacity={0.08} stroke={T.cyan} strokeWidth={1} strokeOpacity={0.3} />
          <text x="560" y={55} fontSize={8} fill={T.cyanDim} style={{ fontFamily: 'monospace' }}>CLOUD ZONE</text>
          
          <rect x="550" y="140" width="220" height="100" rx={6} fill={T.green} opacity={0.08} stroke={T.green} strokeWidth={1} strokeOpacity={0.3} />
          <text x="560" y={155} fontSize={8} fill={T.greenDim} style={{ fontFamily: 'monospace' }}>LOCAL ZONE</text>

          {/* Connections */}
          {connections.map((conn, i) => {
            const from = nodes[conn.from];
            const to = nodes[conn.to];
            const mx = (from.x + to.x) / 2;
            const my = (from.y + to.y) / 2;
            
            return (
              <g key={i}>
                <line
                  x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                  stroke={conn.active ? conn.color : T.panelBorder}
                  strokeWidth={conn.active ? 2.5 : 1.5}
                  opacity={conn.active ? 1 : 0.4}
                  style={{ 
                    filter: conn.active && T.name === 'dark' ? `drop-shadow(0 0 4px ${conn.color})` : 'none',
                    transition: 'all 0.3s ease',
                  }}
                />
                {conn.label && (
                  <text x={mx} y={my - 6} textAnchor="middle" fontSize={6} fill={T.textDim} style={{ fontFamily: 'monospace' }}>
                    {conn.label}
                  </text>
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {Object.entries(nodes).map(([id, data]) => (
            <Node key={id} id={id} data={data} />
          ))}

          {/* Legend */}
          <g transform="translate(20, 260)">
            <circle cx={5} cy={0} r={4} fill={T.green} />
            <text x={14} y={3} fontSize={7} fill={T.textDim}>SECURE</text>
            
            <circle cx={70} cy={0} r={4} fill={T.yellow} />
            <text x={79} y={3} fontSize={7} fill={T.textDim}>REVIEW</text>
            
            <circle cx={130} cy={0} r={4} fill={T.red} />
            <text x={139} y={3} fontSize={7} fill={T.textDim}>ACTION</text>
            
            <g transform="translate(190, -3)">
              <circle r={5} fill="none" stroke={T.yellow} strokeWidth={1.5} strokeDasharray="2,2" />
            </g>
            <text x={200} y={3} fontSize={7} fill={T.textDim}>THREAT</text>
            
            <text x={260} y={3} fontSize={7} fill={T.textDim}>SCROLL TO ZOOM • DRAG TO PAN</text>
          </g>
        </svg>
      </div>
    </Panel>
  );
}

// =============================================================================
// THREAT PANEL
// =============================================================================

function ThreatPanel({ nodeId, onClose, T }) {
  const threat = THREATS[nodeId];
  if (!threat) return null;

  return (
    <div style={{
      position: 'absolute',
      right: 0,
      top: 0,
      bottom: 0,
      width: 320,
      background: T.panel,
      borderLeft: `1px solid ${T.panelBorder}`,
      display: 'flex',
      flexDirection: 'column',
      zIndex: 10,
      boxShadow: `-4px 0 20px ${T.shadow}`,
    }}>
      <div style={{
        padding: '1rem',
        borderBottom: `1px solid ${T.panelBorder}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: T.panelLight,
      }}>
        <div>
          <div style={{ fontSize: '0.7rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '0.2rem' }}>
            THREAT ASSESSMENT
          </div>
          <div style={{ fontSize: '1rem', color: T.text, fontWeight: 600 }}>{threat.label}</div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: T.panelLight,
            border: `1px solid ${T.panelBorder}`,
            borderRadius: 4,
            color: T.textDim,
            padding: '0.25rem 0.5rem',
            cursor: 'pointer',
            fontFamily: 'monospace',
            fontSize: '0.7rem',
          }}
        >
          ✕
        </button>
      </div>

      <div style={{ padding: '1rem', flex: 1, overflowY: 'auto' }}>
        {/* Risk level */}
        <div style={{
          padding: '0.75rem',
          background: threat.level === 2 ? T.redBg : threat.level === 1 ? T.yellowBg : T.greenBg,
          borderRadius: 6,
          marginBottom: '1rem',
          border: `1px solid ${threat.level === 2 ? T.redDim : threat.level === 1 ? T.yellowDim : T.greenDim}30`,
        }}>
          <div style={{ fontSize: '0.6rem', color: T.textDim, marginBottom: '0.3rem', fontFamily: 'monospace' }}>RISK LEVEL</div>
          <AccentText 
            size="1.2rem" 
            color={threat.level === 2 ? T.red : threat.level === 1 ? T.yellow : T.green}
            mono
            glow={T.name === 'dark'}
            T={T}
          >
            {threat.level === 2 ? 'HIGH' : threat.level === 1 ? 'MEDIUM' : 'LOW'}
          </AccentText>
        </div>

        {/* Issues */}
        {threat.issues.length > 0 && (
          <>
            <div style={{ fontSize: '0.6rem', color: T.textDim, marginBottom: '0.5rem', fontFamily: 'monospace' }}>
              IDENTIFIED ISSUES
            </div>
            {threat.issues.map((issue, i) => (
              <div key={i} style={{
                padding: '0.6rem',
                background: T.panelLight,
                borderRadius: 6,
                marginBottom: '0.5rem',
                borderLeft: `3px solid ${T.yellow}`,
              }}>
                <div style={{ fontSize: '0.75rem', color: T.text }}>{issue}</div>
              </div>
            ))}
          </>
        )}

        {/* Recommended action */}
        {threat.action && (
          <div style={{ marginTop: '1rem' }}>
            <div style={{ fontSize: '0.6rem', color: T.textDim, marginBottom: '0.5rem', fontFamily: 'monospace' }}>
              RECOMMENDED ACTION
            </div>
            <div style={{
              padding: '0.75rem',
              background: T.greenBg,
              borderRadius: 6,
              borderLeft: `3px solid ${T.green}`,
            }}>
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

function ActivityLog({ entries, T }) {
  return (
    <Panel title="ACTIVITY LOG" style={{ flex: 1 }} T={T}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: 200, overflowY: 'auto' }}>
        {entries.length === 0 ? (
          <div style={{ color: T.textDim, fontSize: '0.7rem', fontFamily: 'monospace', textAlign: 'center', padding: '1rem' }}>
            AWAITING DATA...
          </div>
        ) : (
          entries.slice(0, 10).map((entry, i) => (
            <div key={entry.id || i} style={{
              display: 'flex',
              gap: '0.5rem',
              padding: '0.4rem 0.5rem',
              background: i === 0 ? T.panelLight : 'transparent',
              borderRadius: 4,
            }}>
              <span style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', minWidth: 55 }}>
                {entry.time}
              </span>
              <StatusDot status={entry.status} size={6} T={T} />
              <span style={{ fontSize: '0.7rem', color: T.text, fontFamily: 'monospace' }}>
                {entry.message}
              </span>
              {entry.cost && (
                <span style={{ fontSize: '0.65rem', color: T.green, fontFamily: 'monospace', marginLeft: 'auto', fontWeight: 600 }}>
                  ${entry.cost.toFixed(4)}
                </span>
              )}
            </div>
          ))
        )}
      </div>
    </Panel>
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
        position: 'relative',
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
// MAIN COMPONENT
// =============================================================================

export default function SystemMonitor() {
  const [themeName, setThemeName] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('xlr8-theme') || 'dark';
    }
    return 'dark';
  });
  const T = THEMES[themeName];

  const [data, setData] = useState({
    month: { total: 0, fixed: 0, api: 0, month_name: 'DEC' },
    usage: { total: 0, claude: 0, runpod: 0, textract: 0, calls: 0 },
    stats: { files: 0, rows: 0, chunks: 0 },
  });
  const [flow, setFlow] = useState({});
  const [selectedNode, setSelectedNode] = useState(null);
  const [activity, setActivity] = useState([]);
  const [time, setTime] = useState(new Date());

  const toggleTheme = () => {
    const newTheme = themeName === 'dark' ? 'light' : 'dark';
    setThemeName(newTheme);
    localStorage.setItem('xlr8-theme', newTheme);
  };

  // Clock
  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [monthRes, usageRes, structRes] = await Promise.all([
          api.get('/status/costs/month').catch(() => ({ data: {} })),
          api.get('/status/costs?days=30').catch(() => ({ data: {} })),
          api.get('/status/structured').catch(() => ({ data: {} })),
        ]);

        setData({
          month: {
            total: monthRes.data?.total || 0,
            fixed: monthRes.data?.fixed_costs || 0,
            api: monthRes.data?.api_usage || 0,
            month_name: monthRes.data?.month_name?.toUpperCase()?.slice(0, 3) || 'DEC',
          },
          usage: {
            total: usageRes.data?.total_cost || 0,
            claude: usageRes.data?.by_service?.claude || 0,
            runpod: usageRes.data?.by_service?.runpod || 0,
            textract: usageRes.data?.by_service?.textract || 0,
            calls: usageRes.data?.record_count || 0,
          },
          stats: {
            files: structRes.data?.total_files || 0,
            rows: structRes.data?.total_rows || 0,
          },
        });
      } catch (err) {
        console.error('Fetch error:', err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Animate flow
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

  // Simulate activity
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
      setActivity(prev => [{
        ...msg,
        time: new Date().toLocaleTimeString('en-US', { hour12: false }),
        id: Date.now(),
      }, ...prev].slice(0, 20));
    };

    const interval = setInterval(addEntry, 3000);
    return () => clearInterval(interval);
  }, []);

  const threatCount = Object.values(THREATS).filter(t => t.level > 0).length;

  return (
    <div style={{
      background: T.bg,
      minHeight: '100vh',
      color: T.text,
      fontFamily: "'Inter', -apple-system, sans-serif",
      position: 'relative',
      transition: 'background 0.3s ease, color 0.3s ease',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.75rem 1rem',
        borderBottom: `1px solid ${T.panelBorder}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: T.panel,
        transition: 'background 0.3s ease',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', letterSpacing: '0.15em' }}>
              XLR8 PLATFORM
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: T.textBright }}>
              OPERATIONS CENTER
            </div>
          </div>
          
          <div style={{ 
            padding: '0.4rem 0.75rem', 
            background: threatCount > 0 ? T.yellowBg : T.greenBg,
            borderRadius: 6,
            border: `1px solid ${threatCount > 0 ? T.yellowDim : T.greenDim}30`,
          }}>
            <AccentText size="0.7rem" color={threatCount > 0 ? T.yellow : T.green} mono glow={T.name === 'dark'} T={T}>
              {threatCount > 0 ? `${threatCount} ITEMS NEED REVIEW` : 'ALL SYSTEMS NOMINAL'}
            </AccentText>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <ThemeToggle theme={T} onToggle={toggleTheme} />
          
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '1.2rem', fontFamily: 'monospace', color: T.green, fontWeight: 600 }}>
              {time.toLocaleTimeString('en-US', { hour12: false })}
            </div>
            <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace' }}>
              {time.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase()}
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div style={{ 
        padding: '1rem', 
        display: 'grid', 
        gridTemplateColumns: 'repeat(5, 1fr)', 
        gap: '0.75rem',
        paddingRight: selectedNode ? '340px' : '1rem',
        transition: 'padding-right 0.3s ease',
      }}>
        <MetricCard label={`${data.month.month_name} SPEND`} value={`$${data.month.total.toFixed(0)}`} sublabel="Total" T={T} />
        <MetricCard label="API USAGE" value={`$${data.usage.total.toFixed(2)}`} sublabel={`${data.usage.calls} calls`} status={0} T={T} />
        <MetricCard label="DOCUMENTS" value={data.stats.files.toLocaleString()} sublabel="Processed" status={0} T={T} />
        <MetricCard label="LOCAL %" value="62%" sublabel="Cost savings" status={0} T={T} />
        <MetricCard label="UPTIME" value="99.9%" sublabel="30 days" status={0} T={T} />

        <SpendBreakdown data={{
          fixed: data.month.fixed,
          claude: data.usage.claude,
          runpod: data.usage.runpod,
          textract: data.usage.textract,
        }} T={T} />
        
        <SystemTopology 
          status={{}} 
          flow={flow} 
          onNodeClick={setSelectedNode}
          selectedNode={selectedNode}
          T={T}
        />

        <Panel title="STORAGE" style={{ gridColumn: 'span 2' }} T={T}>
          <div style={{ display: 'flex', gap: '1.5rem' }}>
            <div>
              <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '0.3rem' }}>STRUCTURED</div>
              <AccentText size="1.2rem" color={T.purple} mono glow={T.name === 'dark'} T={T}>{data.stats.rows.toLocaleString()}</AccentText>
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
                <div style={{ 
                  height: '100%', 
                  width: '60%', 
                  background: `linear-gradient(90deg, ${T.purple}, ${T.cyan})`,
                  borderRadius: 3,
                  boxShadow: T.name === 'dark' ? `0 0 8px ${T.purple}60` : 'none',
                }} />
              </div>
            </div>
          </div>
        </Panel>

        <ActivityLog entries={activity} T={T} />
      </div>

      {selectedNode && (
        <ThreatPanel nodeId={selectedNode} onClose={() => setSelectedNode(null)} T={T} />
      )}
    </div>
  );
}
