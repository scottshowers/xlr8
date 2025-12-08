/**
 * XLR8 OPERATIONS CENTER - LIGHT MODE
 * 
 * Clean, professional light theme
 * Same structure as dark ops version
 */

import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

// =============================================================================
// THEME - Light Ops Center
// =============================================================================
const T = {
  // Backgrounds
  bg: '#f0f4f8',
  panel: '#ffffff',
  panelLight: '#f8fafc',
  panelBorder: '#e2e8f0',
  
  // Text
  text: '#1e293b',
  textDim: '#64748b',
  textBright: '#0f172a',
  
  // Accent colors - professional, not neon
  green: '#059669',
  greenDim: '#10b981',
  greenGlow: 'rgba(5, 150, 105, 0.08)',
  
  red: '#dc2626',
  redDim: '#ef4444',
  redGlow: 'rgba(220, 38, 38, 0.08)',
  
  yellow: '#d97706',
  yellowDim: '#f59e0b',
  yellowGlow: 'rgba(217, 119, 6, 0.08)',
  
  blue: '#2563eb',
  blueDim: '#3b82f6',
  blueGlow: 'rgba(37, 99, 235, 0.08)',
  
  cyan: '#0891b2',
  cyanDim: '#06b6d4',
  
  purple: '#7c3aed',
  orange: '#ea580c',
};

// Risk and security data
const THREATS = {
  api: { level: 2, label: 'API GATEWAY', issues: ['Rate limiting not enforced', 'Input validation needed'], action: 'Implement throttling' },
  duckdb: { level: 2, label: 'STRUCTURED DB', issues: ['PII exposure risk', 'Query logging disabled'], action: 'Enable data masking' },
  chromadb: { level: 1, label: 'VECTOR STORE', issues: ['Embeddings may contain PII'], action: 'Audit chunk content' },
  claude: { level: 2, label: 'CLOUD AI', issues: ['External data transmission', 'Prompt injection risk'], action: 'Sanitize prompts' },
  supabase: { level: 0, label: 'AUTH', issues: [], action: '' },
  runpod: { level: 0, label: 'LOCAL AI', issues: [], action: '' },
};

// =============================================================================
// UTILITY COMPONENTS
// =============================================================================

const AccentText = ({ children, color = T.green, size = '1rem', mono = false }) => (
  <span style={{
    color,
    fontSize: size,
    fontFamily: mono ? "'JetBrains Mono', 'Fira Code', monospace" : 'inherit',
    fontWeight: 600,
  }}>{children}</span>
);

const StatusDot = ({ status, size = 8 }) => {
  const color = status === 2 ? T.red : status === 1 ? T.yellow : T.green;
  return (
    <span style={{
      display: 'inline-block',
      width: size,
      height: size,
      borderRadius: '50%',
      background: color,
      boxShadow: `0 0 0 2px ${color}20`,
    }} />
  );
};

const Panel = ({ children, title, status, style = {} }) => (
  <div style={{
    background: T.panel,
    border: `1px solid ${T.panelBorder}`,
    borderRadius: 8,
    overflow: 'hidden',
    boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
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
        {status !== undefined && <StatusDot status={status} size={6} />}
      </div>
    )}
    <div style={{ padding: '0.875rem' }}>{children}</div>
  </div>
);

// =============================================================================
// EXECUTIVE METRICS
// =============================================================================

function MetricCard({ label, value, unit, sublabel, trend, status }) {
  return (
    <Panel status={status}>
      <div style={{ fontSize: '0.65rem', color: T.textDim, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.4rem', fontFamily: 'monospace' }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.3rem' }}>
        <AccentText size="1.75rem" color={status === 2 ? T.red : status === 1 ? T.yellow : T.green} mono>
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

function SpendBreakdown({ data }) {
  const items = [
    { label: 'SUBSCRIPTIONS', value: data.fixed || 0, color: T.purple },
    { label: 'CLAUDE API', value: data.claude || 0, color: T.cyan },
    { label: 'LOCAL LLM', value: data.runpod || 0, color: T.green },
    { label: 'TEXTRACT', value: data.textract || 0, color: T.orange },
  ];
  const max = Math.max(...items.map(i => i.value), 1);

  return (
    <Panel title="COST ALLOCATION">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
        {items.map(item => (
          <div key={item.label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
              <span style={{ fontSize: '0.65rem', color: T.textDim, fontFamily: 'monospace' }}>{item.label}</span>
              <AccentText size="0.75rem" color={item.color} mono>${item.value.toFixed(2)}</AccentText>
            </div>
            <div style={{ height: 4, background: T.panelBorder, borderRadius: 2 }}>
              <div style={{
                height: '100%',
                width: `${(item.value / max) * 100}%`,
                background: item.color,
                borderRadius: 2,
              }} />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

// =============================================================================
// SYSTEM TOPOLOGY
// =============================================================================

function SystemTopology({ status, flow, onNodeClick, selectedNode }) {
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

  const Node = ({ id, data }) => {
    const isSelected = selectedNode === id;
    const threat = data.threat;
    const threatLevel = threat?.level || 0;
    
    return (
      <g 
        transform={`translate(${data.x}, ${data.y})`} 
        style={{ cursor: 'pointer' }}
        onClick={() => onNodeClick(id)}
      >
        {/* Threat ring */}
        {threatLevel > 0 && (
          <circle
            r={28}
            fill="none"
            stroke={threatLevel === 2 ? T.red : T.yellow}
            strokeWidth={2}
            strokeDasharray="4,4"
            opacity={0.5}
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
          style={{ filter: isSelected ? `drop-shadow(0 2px 8px ${data.color}40)` : 'none' }}
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
        />
      </g>
    );
  };

  return (
    <Panel title="SYSTEM TOPOLOGY" style={{ gridColumn: 'span 2' }}>
      <svg width="100%" height="280" viewBox="0 0 780 280">
        {/* Zone backgrounds */}
        <rect x="550" y="40" width="220" height="80" rx={6} fill={T.cyan} opacity={0.06} stroke={T.cyan} strokeWidth={1} strokeOpacity={0.3} />
        <text x="560" y={55} fontSize={8} fill={T.cyanDim} style={{ fontFamily: 'monospace' }}>CLOUD ZONE</text>
        
        <rect x="550" y="140" width="220" height="100" rx={6} fill={T.green} opacity={0.06} stroke={T.green} strokeWidth={1} strokeOpacity={0.3} />
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
                style={{ transition: 'all 0.3s ease' }}
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
          <text x={139} y={3} fontSize={7} fill={T.textDim}>ACTION REQ</text>
          
          <g transform="translate(200, -3)">
            <circle r={5} fill="none" stroke={T.yellow} strokeWidth={1.5} strokeDasharray="2,2" />
          </g>
          <text x={210} y={3} fontSize={7} fill={T.textDim}>THREAT DETECTED</text>
        </g>
      </svg>
    </Panel>
  );
}

// =============================================================================
// THREAT PANEL
// =============================================================================

function ThreatPanel({ nodeId, onClose }) {
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
      boxShadow: '-4px 0 20px rgba(0,0,0,0.08)',
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
          CLOSE
        </button>
      </div>

      <div style={{ padding: '1rem', flex: 1, overflowY: 'auto' }}>
        {/* Risk level */}
        <div style={{
          padding: '0.75rem',
          background: threat.level === 2 ? T.redGlow : threat.level === 1 ? T.yellowGlow : T.greenGlow,
          borderRadius: 6,
          marginBottom: '1rem',
          border: `1px solid ${threat.level === 2 ? T.redDim : threat.level === 1 ? T.yellowDim : T.greenDim}20`,
        }}>
          <div style={{ fontSize: '0.6rem', color: T.textDim, marginBottom: '0.3rem', fontFamily: 'monospace' }}>RISK LEVEL</div>
          <AccentText 
            size="1.2rem" 
            color={threat.level === 2 ? T.red : threat.level === 1 ? T.yellow : T.green}
            mono
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
              background: T.greenGlow,
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

function ActivityLog({ entries }) {
  return (
    <Panel title="ACTIVITY LOG" style={{ flex: 1 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: 200, overflowY: 'auto' }}>
        {entries.length === 0 ? (
          <div style={{ color: T.textDim, fontSize: '0.7rem', fontFamily: 'monospace', textAlign: 'center', padding: '1rem' }}>
            AWAITING DATA...
          </div>
        ) : (
          entries.slice(0, 10).map((entry, i) => (
            <div key={i} style={{
              display: 'flex',
              gap: '0.5rem',
              padding: '0.4rem 0.5rem',
              background: i === 0 ? T.panelLight : 'transparent',
              borderRadius: 4,
            }}>
              <span style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', minWidth: 55 }}>
                {entry.time}
              </span>
              <StatusDot status={entry.status} size={6} />
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
// MAIN COMPONENT
// =============================================================================

export default function SystemMonitor() {
  const [data, setData] = useState({
    month: { total: 0, fixed: 0, api: 0, month_name: 'DEC' },
    usage: { total: 0, claude: 0, runpod: 0, textract: 0, calls: 0 },
    stats: { files: 0, rows: 0, chunks: 0 },
  });
  const [flow, setFlow] = useState({});
  const [selectedNode, setSelectedNode] = useState(null);
  const [activity, setActivity] = useState([]);
  const [time, setTime] = useState(new Date());

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

  // Simulate flow
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
    }}>
      {/* Header */}
      <div style={{
        padding: '0.75rem 1rem',
        borderBottom: `1px solid ${T.panelBorder}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: T.panel,
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
            background: threatCount > 0 ? T.yellowGlow : T.greenGlow,
            borderRadius: 6,
            border: `1px solid ${threatCount > 0 ? T.yellowDim : T.greenDim}30`,
          }}>
            <AccentText size="0.7rem" color={threatCount > 0 ? T.yellow : T.green} mono>
              {threatCount > 0 ? `${threatCount} ITEMS NEED REVIEW` : 'ALL SYSTEMS NOMINAL'}
            </AccentText>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
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
        <MetricCard label={`${data.month.month_name} SPEND`} value={`$${data.month.total.toFixed(0)}`} sublabel="Total" />
        <MetricCard label="API USAGE" value={`$${data.usage.total.toFixed(2)}`} sublabel={`${data.usage.calls} calls`} status={0} />
        <MetricCard label="DOCUMENTS" value={data.stats.files.toLocaleString()} sublabel="Processed" status={0} />
        <MetricCard label="LOCAL %" value="62%" sublabel="Cost savings" status={0} />
        <MetricCard label="UPTIME" value="99.9%" sublabel="30 days" status={0} />

        <SpendBreakdown data={{
          fixed: data.month.fixed,
          claude: data.usage.claude,
          runpod: data.usage.runpod,
          textract: data.usage.textract,
        }} />
        
        <SystemTopology 
          status={{}} 
          flow={flow} 
          onNodeClick={setSelectedNode}
          selectedNode={selectedNode}
        />

        <Panel title="STORAGE" style={{ gridColumn: 'span 2' }}>
          <div style={{ display: 'flex', gap: '1.5rem' }}>
            <div>
              <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '0.3rem' }}>STRUCTURED</div>
              <AccentText size="1.2rem" color={T.purple} mono>{data.stats.rows.toLocaleString()}</AccentText>
              <div style={{ fontSize: '0.6rem', color: T.textDim }}>rows</div>
            </div>
            <div>
              <div style={{ fontSize: '0.6rem', color: T.textDim, fontFamily: 'monospace', marginBottom: '0.3rem' }}>VECTOR</div>
              <AccentText size="1.2rem" color={T.cyan} mono>{(data.stats.chunks || 0).toLocaleString()}</AccentText>
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
                }} />
              </div>
            </div>
          </div>
        </Panel>

        <ActivityLog entries={activity} />
      </div>

      {selectedNode && (
        <ThreatPanel nodeId={selectedNode} onClose={() => setSelectedNode(null)} />
      )}
    </div>
  );
}
