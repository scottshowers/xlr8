/**
 * SystemMonitor - Real-time Data Flow, Cost Tracking & System Health Dashboard
 * Redesigned: December 2025
 * 
 * Features:
 * - Architecture diagram with encryption points and data flow branching
 * - Monthly/daily cost tracking with editable fixed costs
 * - Data storage breakdown (Chunks vs Structured)
 * - Session metrics (API calls, queries, LLM calls)
 * - Component health status
 */

import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';

const COLORS = {
  bg: '#f6f5fa',
  cardBg: '#ffffff',
  archBg: '#e8eef0',
  border: '#e1e8ed',
  text: '#2a3441',
  textMuted: '#5f6c7b',
  grassGreen: '#83b16d',
  green: '#22c55e',
  yellow: '#eab308',
  red: '#ef4444',
  blue: '#3b82f6',
  purple: '#8b5cf6',
  cyan: '#06b6d4',
  orange: '#f97316',
  pink: '#ec4899',
  indigo: '#4f46e5',
  amber: '#d97706',
  encryption: '#f59e0b',
};

// =============================================================================
// SMALL COMPONENTS
// =============================================================================

function StatusLight({ status, size = 12 }) {
  const color = status === 'healthy' ? COLORS.green : status === 'warning' ? COLORS.yellow : COLORS.red;
  return (
    <div style={{
      width: size,
      height: size,
      borderRadius: '50%',
      background: color,
      boxShadow: `0 0 8px ${color}`,
    }} />
  );
}

function MetricCard({ icon, label, value, subValue, color }) {
  return (
    <div style={{
      background: COLORS.cardBg,
      borderRadius: 12,
      padding: '0.875rem',
      border: `1px solid ${COLORS.border}`,
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      minWidth: 120,
      flex: '1 1 120px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '1rem' }}>{icon}</span>
        <span style={{ color: COLORS.textMuted, fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase' }}>{label}</span>
      </div>
      <div style={{ fontSize: '1.4rem', fontWeight: 700, color: color || COLORS.text }}>{value}</div>
      {subValue && <div style={{ fontSize: '0.65rem', color: COLORS.textMuted, marginTop: '0.2rem' }}>{subValue}</div>}
    </div>
  );
}

// =============================================================================
// COST SETTINGS MODAL
// =============================================================================

function CostSettingsModal({ isOpen, onClose, fixedItems, onSave }) {
  const [items, setItems] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (fixedItems) setItems([...fixedItems]);
  }, [fixedItems]);

  if (!isOpen) return null;

  const handleChange = (idx, field, value) => {
    const updated = [...items];
    updated[idx] = { ...updated[idx], [field]: field === 'quantity' ? parseInt(value) || 0 : parseFloat(value) || 0 };
    setItems(updated);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      for (const item of items) {
        await api.put(`/status/costs/fixed/${encodeURIComponent(item.name)}`, null, {
          params: { cost_per_unit: item.cost_per_unit, quantity: item.quantity }
        });
      }
      onSave();
      onClose();
    } catch (err) {
      console.error('Save failed:', err);
      alert('Failed to save costs');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000,
    }} onClick={onClose}>
      <div style={{
        background: COLORS.cardBg, borderRadius: 16, padding: '1.5rem', minWidth: 400,
        boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
      }} onClick={e => e.stopPropagation()}>
        <h3 style={{ margin: '0 0 1rem 0', color: COLORS.text }}>⚙️ Fixed Monthly Costs</h3>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {items.filter(i => i.category === 'subscription').map((item, idx) => (
            <div key={item.name} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span style={{ flex: 1, fontSize: '0.85rem', color: COLORS.text }}>{item.name}</span>
              <input
                type="number"
                value={item.cost_per_unit}
                onChange={e => handleChange(idx, 'cost_per_unit', e.target.value)}
                style={{ width: 80, padding: '0.4rem', borderRadius: 6, border: `1px solid ${COLORS.border}` }}
                step="0.01"
              />
              <span style={{ fontSize: '0.75rem', color: COLORS.textMuted }}>× </span>
              <input
                type="number"
                value={item.quantity}
                onChange={e => handleChange(idx, 'quantity', e.target.value)}
                style={{ width: 50, padding: '0.4rem', borderRadius: 6, border: `1px solid ${COLORS.border}` }}
              />
              <span style={{ fontSize: '0.75rem', color: COLORS.textMuted, width: 60 }}>
                = ${(item.cost_per_unit * item.quantity).toFixed(2)}
              </span>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem', justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{
            padding: '0.5rem 1rem', borderRadius: 8, border: `1px solid ${COLORS.border}`,
            background: 'white', cursor: 'pointer'
          }}>Cancel</button>
          <button onClick={handleSave} disabled={saving} style={{
            padding: '0.5rem 1rem', borderRadius: 8, border: 'none',
            background: COLORS.blue, color: 'white', cursor: 'pointer'
          }}>{saving ? 'Saving...' : 'Save Changes'}</button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// ARCHITECTURE DIAGRAM
// =============================================================================

function ArchitectureDiagram({ componentStatus, dataFlowActive }) {
  // Node component
  const Node = ({ x, y, icon, label, status, isActive, encrypted, size = 'normal' }) => {
    const statusColor = status === 'healthy' ? COLORS.green : status === 'warning' ? COLORS.yellow : COLORS.red;
    const w = size === 'small' ? 85 : 100;
    const h = size === 'small' ? 50 : 55;
    
    return (
      <g>
        <rect
          x={x - w/2} y={y - h/2} width={w} height={h} rx={10}
          fill={COLORS.cardBg}
          stroke={isActive ? COLORS.blue : '#94a3b8'}
          strokeWidth={isActive ? 2.5 : 1.5}
          style={{ filter: isActive ? 'drop-shadow(0 2px 8px rgba(59,130,246,0.3))' : 'drop-shadow(0 1px 2px rgba(0,0,0,0.08))' }}
        />
        <text x={x} y={y - 2} textAnchor="middle" fontSize={size === 'small' ? 16 : 20}>{icon}</text>
        <text x={x} y={y + 16} textAnchor="middle" fontSize={size === 'small' ? 8 : 9} fill={COLORS.textMuted} fontWeight="600">{label}</text>
        <circle cx={x + w/2 - 8} cy={y - h/2 + 8} r={4} fill={statusColor} />
        {encrypted && (
          <g>
            <circle cx={x - w/2 + 10} cy={y - h/2 + 10} r={7} fill="#fef3c7" stroke={COLORS.encryption} strokeWidth={1.5} />
            <text x={x - w/2 + 10} y={y - h/2 + 13} textAnchor="middle" fontSize="8">🔒</text>
          </g>
        )}
      </g>
    );
  };

  // Connection line with optional label
  const Connection = ({ x1, y1, x2, y2, active, color, label, encrypted }) => {
    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;
    
    return (
      <g>
        <line
          x1={x1} y1={y1} x2={x2} y2={y2}
          stroke={active ? (color || COLORS.blue) : COLORS.border}
          strokeWidth={active ? 2.5 : 1.5}
          strokeDasharray={active ? 'none' : '4,4'}
          style={{ transition: 'all 0.3s ease' }}
        />
        {label && (
          <text x={midX} y={midY - 5} textAnchor="middle" fontSize="7" fill={COLORS.textMuted}>{label}</text>
        )}
        {encrypted && (
          <text x={midX} y={midY + 8} textAnchor="middle" fontSize="7" fill={COLORS.encryption}>HTTPS</text>
        )}
      </g>
    );
  };

  // Section label
  const SectionLabel = ({ x, y, label, color }) => (
    <g>
      <rect x={x - 2} y={y - 10} width={label.length * 6 + 10} height={16} rx={4} fill={color} opacity={0.15} />
      <text x={x + 3} y={y} fontSize="9" fill={color} fontWeight="600">{label}</text>
    </g>
  );

  return (
    <svg width="100%" height="420" viewBox="0 0 700 420">
      {/* Background sections */}
      <rect x="430" y="140" width="260" height="110" rx={12} fill={COLORS.cyan} opacity={0.08} />
      <rect x="430" y="260" width="260" height="140" rx={12} fill={COLORS.orange} opacity={0.08} />
      
      {/* Section Labels */}
      <SectionLabel x={440} y={155} label="CLOUD API" color={COLORS.cyan} />
      <SectionLabel x={440} y={275} label="LOCAL LLM (RunPod)" color={COLORS.orange} />
      
      {/* Connections */}
      <Connection x1={100} y1={80} x2={200} y2={140} active={dataFlowActive.frontendToApi} label="REST" encrypted />
      <Connection x1={200} y1={200} x2={100} y2={260} active={dataFlowActive.apiToSupabase} label="Auth" encrypted />
      
      {/* API to Data Layer - SPLIT POINT */}
      <Connection x1={260} y1={160} x2={350} y2={90} active={dataFlowActive.apiToDuckdb} color={COLORS.purple} label="Structured" />
      <Connection x1={260} y1={180} x2={350} y2={180} active={dataFlowActive.apiToRag} color={COLORS.orange} label="Semantic" />
      
      {/* RAG to Storage */}
      <Connection x1={410} y1={180} x2={470} y2={90} active={dataFlowActive.ragToChroma} color={COLORS.green} label="Vector" />
      
      {/* RAG to LLMs - SPLIT POINT */}
      <Connection x1={410} y1={190} x2={470} y2={190} active={dataFlowActive.ragToClaude} color={COLORS.cyan} />
      <Connection x1={410} y1={200} x2={470} y2={310} active={dataFlowActive.ragToLocalLLM} color={COLORS.orange} />
      
      {/* Local LLM internal connections */}
      <line x1={530} y1={310} x2={530} y2={380} stroke={COLORS.orange} strokeWidth={1} opacity={0.3} />
      <line x1={610} y1={310} x2={610} y2={380} stroke={COLORS.orange} strokeWidth={1} opacity={0.3} />
      
      {/* Nodes - User Layer */}
      <Node x={70} y={80} icon="🖥️" label="FRONTEND" status={componentStatus.frontend} isActive={dataFlowActive.frontendToApi} />
      
      {/* Nodes - API Layer */}
      <Node x={230} y={170} icon="⚙️" label="API SERVER" status={componentStatus.api} isActive={true} encrypted />
      
      {/* Nodes - Auth */}
      <Node x={70} y={290} icon="🔐" label="SUPABASE" status={componentStatus.supabase} isActive={dataFlowActive.apiToSupabase} encrypted />
      
      {/* Nodes - Data Layer (SPLIT) */}
      <Node x={380} y={90} icon="🦆" label="DUCKDB" status={componentStatus.duckdb} isActive={dataFlowActive.apiToDuckdb} encrypted />
      <Node x={380} y={180} icon="🎯" label="RAG" status={componentStatus.rag} isActive={dataFlowActive.apiToRag} />
      <Node x={500} y={90} icon="🔍" label="CHROMADB" status={componentStatus.chromadb} isActive={dataFlowActive.ragToChroma} />
      
      {/* Nodes - Cloud LLM */}
      <Node x={530} y={190} icon="🤖" label="CLAUDE API" status={componentStatus.claude} isActive={dataFlowActive.ragToClaude} />
      
      {/* Nodes - Local LLMs */}
      <Node x={530} y={310} icon="🦙" label="LLAMA 3.1" status={componentStatus.llama} isActive={dataFlowActive.ragToLocalLLM} size="small" />
      <Node x={610} y={310} icon="🌬️" label="MISTRAL" status={componentStatus.mistral} isActive={dataFlowActive.ragToLocalLLM} size="small" />
      <Node x={530} y={370} icon="🔮" label="DEEPSEEK" status={componentStatus.deepseek} isActive={dataFlowActive.ragToLocalLLM} size="small" />
      <Node x={610} y={370} icon="❄️" label="QWEN" status={componentStatus.qwen || 'healthy'} isActive={false} size="small" />
      
      {/* Legend */}
      <g transform="translate(20, 390)">
        <circle cx={8} cy={4} r={6} fill="#fef3c7" stroke={COLORS.encryption} strokeWidth={1.5} />
        <text x={8} y={7} textAnchor="middle" fontSize="7">🔒</text>
        <text x={20} y={7} fontSize="8" fill={COLORS.textMuted}>Encryption at rest</text>
        
        <text x={120} y={7} fontSize="8" fill={COLORS.encryption}>HTTPS</text>
        <text x={150} y={7} fontSize="8" fill={COLORS.textMuted}>= Encrypted in transit</text>
        
        <rect x={260} y={-2} width={12} height={12} rx={3} fill={COLORS.purple} opacity={0.2} />
        <text x={278} y={7} fontSize="8" fill={COLORS.textMuted}>Structured data path</text>
        
        <rect x={370} y={-2} width={12} height={12} rx={3} fill={COLORS.orange} opacity={0.2} />
        <text x={388} y={7} fontSize="8" fill={COLORS.textMuted}>Semantic/LLM path</text>
      </g>
    </svg>
  );
}

// =============================================================================
// COST CARDS
// =============================================================================

function MonthCostCard({ monthCosts, loading, onSettingsClick }) {
  if (loading) {
    return (
      <div style={{ background: COLORS.cardBg, borderRadius: 12, padding: '1rem', border: `1px solid ${COLORS.border}`, minWidth: 200 }}>
        <div style={{ color: COLORS.textMuted, fontSize: '0.85rem' }}>Loading...</div>
      </div>
    );
  }

  return (
    <div style={{
      background: COLORS.cardBg, borderRadius: 12, padding: '1rem',
      border: `1px solid ${COLORS.border}`, boxShadow: '0 1px 3px rgba(0,0,0,0.05)', minWidth: 200,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ fontSize: '1rem' }}>💰</span>
          <span style={{ color: COLORS.textMuted, fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase' }}>
            {monthCosts.month_name || 'This Month'}
          </span>
        </div>
        <button onClick={onSettingsClick} style={{
          background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.9rem', padding: '0.2rem'
        }} title="Edit fixed costs">⚙️</button>
      </div>
      
      <div style={{ fontSize: '1.75rem', fontWeight: 700, color: COLORS.grassGreen, marginBottom: '0.5rem' }}>
        ${(monthCosts.total || 0).toFixed(2)}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.7rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: COLORS.textMuted }}>📋 Subscriptions</span>
          <span style={{ fontWeight: 600, color: COLORS.pink }}>${(monthCosts.fixed_costs || 0).toFixed(2)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: COLORS.textMuted }}>⚡ API Usage</span>
          <span style={{ fontWeight: 600, color: COLORS.cyan }}>${(monthCosts.api_usage || 0).toFixed(4)}</span>
        </div>
      </div>

      {monthCosts.fixed_items && monthCosts.fixed_items.length > 0 && (
        <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: `1px solid ${COLORS.border}` }}>
          {monthCosts.fixed_items.filter(i => i.category === 'subscription').map((item, idx) => (
            <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: COLORS.textMuted }}>
              <span>{item.name} {item.quantity > 1 ? `(×${item.quantity})` : ''}</span>
              <span>${(item.cost_per_unit * item.quantity).toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ApiUsageCard({ costs, loading }) {
  if (loading) return null;

  const services = [
    { key: 'claude', icon: '🤖', label: 'Claude', color: COLORS.cyan },
    { key: 'runpod', icon: '⚡', label: 'RunPod', color: COLORS.orange },
    { key: 'textract', icon: '📄', label: 'Textract', color: COLORS.purple },
  ];

  return (
    <div style={{
      background: COLORS.cardBg, borderRadius: 12, padding: '1rem',
      border: `1px solid ${COLORS.border}`, boxShadow: '0 1px 3px rgba(0,0,0,0.05)', minWidth: 180,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '1rem' }}>📊</span>
        <span style={{ color: COLORS.textMuted, fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase' }}>API Usage (30d)</span>
      </div>
      
      <div style={{ fontSize: '1.4rem', fontWeight: 700, color: COLORS.cyan, marginBottom: '0.5rem' }}>
        ${(costs.total_cost || 0).toFixed(4)}
        <span style={{ fontSize: '0.6rem', color: COLORS.textMuted, fontWeight: 400, marginLeft: '0.3rem' }}>
          {costs.record_count || 0} calls
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        {services.map(svc => (
          <div key={svc.key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem' }}>
            <span style={{ color: COLORS.textMuted }}>{svc.icon} {svc.label}</span>
            <span style={{ fontWeight: 600, color: svc.color }}>${(costs.by_service?.[svc.key] || 0).toFixed(4)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DailySpendCard({ dailyCosts, loading }) {
  if (loading || !dailyCosts || dailyCosts.length === 0) return null;

  const data = dailyCosts.slice(0, 7).reverse();
  const maxCost = Math.max(...data.map(d => d.total || 0), 0.001);

  return (
    <div style={{
      background: COLORS.cardBg, borderRadius: 12, padding: '1rem',
      border: `1px solid ${COLORS.border}`, boxShadow: '0 1px 3px rgba(0,0,0,0.05)', minWidth: 200,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '1rem' }}>📈</span>
        <span style={{ color: COLORS.textMuted, fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase' }}>Daily Spend</span>
      </div>

      <div style={{ display: 'flex', gap: '0.2rem', alignItems: 'flex-end', height: 45 }}>
        {data.map((day, idx) => {
          const height = Math.max((day.total / maxCost) * 100, 8);
          const dayName = new Date(day.date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short' });
          return (
            <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{ 
                width: '100%', height: `${height}%`, background: COLORS.cyan, borderRadius: 2, minHeight: 3,
              }} title={`${day.date}: $${day.total.toFixed(4)}`} />
              <span style={{ fontSize: '0.5rem', color: COLORS.textMuted, marginTop: 2 }}>{dayName.charAt(0)}</span>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: '0.4rem', fontSize: '0.6rem', color: COLORS.textMuted, textAlign: 'center' }}>
        Today: ${(dailyCosts[0]?.total || 0).toFixed(4)}
      </div>
    </div>
  );
}

function DataStorageCard({ chunks, structured, loading }) {
  if (loading) return null;

  const total = (chunks || 0) + (structured || 0);
  const chunkPercent = total > 0 ? Math.round((chunks / total) * 100) : 50;

  return (
    <div style={{
      background: COLORS.cardBg, borderRadius: 12, padding: '1rem',
      border: `1px solid ${COLORS.border}`, boxShadow: '0 1px 3px rgba(0,0,0,0.05)', minWidth: 160,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '1rem' }}>💾</span>
        <span style={{ color: COLORS.textMuted, fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase' }}>Data Storage</span>
      </div>

      <div style={{ display: 'flex', height: 6, borderRadius: 3, overflow: 'hidden', marginBottom: '0.5rem', background: COLORS.border }}>
        <div style={{ width: `${chunkPercent}%`, background: COLORS.green }} />
        <div style={{ width: `${100 - chunkPercent}%`, background: COLORS.purple }} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.7rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: COLORS.textMuted, display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: COLORS.green, display: 'inline-block' }} />
            ChromaDB
          </span>
          <span style={{ fontWeight: 600, color: COLORS.green }}>{(chunks || 0).toLocaleString()}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: COLORS.textMuted, display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: COLORS.purple, display: 'inline-block' }} />
            DuckDB
          </span>
          <span style={{ fontWeight: 600, color: COLORS.purple }}>{(structured || 0).toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// ACTIVITY PANEL
// =============================================================================

function ActivityPanel({ recentCosts, activity, showCosts, onToggle, loading }) {
  const serviceColors = { claude: COLORS.cyan, runpod: COLORS.orange, textract: COLORS.purple };

  return (
    <div style={{
      background: COLORS.cardBg, borderRadius: 12, padding: '1rem',
      border: `1px solid ${COLORS.border}`, boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      display: 'flex', flexDirection: 'column', height: '100%',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS.green }} />
          <span style={{ color: COLORS.text, fontSize: '0.85rem', fontWeight: 600 }}>
            {showCosts ? 'Cost Activity' : 'Live Activity'}
          </span>
        </div>
        <button onClick={onToggle} style={{
          background: 'none', border: 'none', color: COLORS.blue, fontSize: '0.65rem', cursor: 'pointer', textDecoration: 'underline'
        }}>{showCosts ? 'Show Live' : 'Show Costs'}</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {showCosts ? (
          loading ? <div style={{ color: COLORS.textMuted, fontSize: '0.8rem', padding: '1rem', textAlign: 'center' }}>Loading...</div> :
          recentCosts.length === 0 ? <div style={{ color: COLORS.textMuted, fontSize: '0.8rem', padding: '1rem', textAlign: 'center' }}>No API calls tracked yet</div> :
          recentCosts.slice(0, 12).map((item, idx) => (
            <div key={item.id || idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.35rem 0', borderBottom: `1px solid ${COLORS.border}` }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: serviceColors[item.service] || COLORS.blue, flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.7rem', color: COLORS.text, display: 'flex', justifyContent: 'space-between' }}>
                  <span>{item.service}/{item.operation}</span>
                  <span style={{ color: COLORS.grassGreen, fontWeight: 600 }}>${(item.estimated_cost || 0).toFixed(5)}</span>
                </div>
                <div style={{ fontSize: '0.55rem', color: COLORS.textMuted }}>
                  {item.tokens_in ? `${item.tokens_in}→${item.tokens_out} tok` : ''}
                  {item.duration_ms ? `${item.duration_ms}ms` : ''}
                  {item.pages ? `${item.pages}pg` : ''}
                  {' · '}{new Date(item.created_at).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        ) : (
          activity.length === 0 ? <div style={{ color: COLORS.textMuted, fontSize: '0.8rem', padding: '1rem', textAlign: 'center' }}>Waiting...</div> :
          activity.map(item => (
            <div key={item.id} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', padding: '0.35rem 0', borderBottom: `1px solid ${COLORS.border}` }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: item.color || COLORS.blue, marginTop: 3, flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.7rem', color: COLORS.text }}>{item.message}</div>
                <div style={{ fontSize: '0.55rem', color: COLORS.textMuted }}>{item.time}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function SystemMonitor() {
  // State
  const [metrics, setMetrics] = useState({ apiRequests: 0, dbQueries: 0, llmCalls: 0, ragQueries: 0, totalFiles: 0, totalRows: 0 });
  const [costs, setCosts] = useState({ total_cost: 0, by_service: {}, record_count: 0 });
  const [monthCosts, setMonthCosts] = useState({ api_usage: 0, fixed_costs: 0, total: 0, month_name: '', fixed_items: [] });
  const [dailyCosts, setDailyCosts] = useState([]);
  const [recentCosts, setRecentCosts] = useState([]);
  const [dataStats, setDataStats] = useState({ chunks: 0, structured: 0, loading: true });
  const [costsLoading, setCostsLoading] = useState(true);
  const [showCostDetails, setShowCostDetails] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const [componentStatus, setComponentStatus] = useState({
    frontend: 'healthy', api: 'healthy', supabase: 'healthy', duckdb: 'healthy',
    chromadb: 'healthy', rag: 'healthy', claude: 'healthy', llama: 'healthy',
    mistral: 'healthy', deepseek: 'healthy', qwen: 'healthy',
  });

  const [activity, setActivity] = useState([]);
  const [dataFlowActive, setDataFlowActive] = useState({
    frontendToApi: false, apiToSupabase: false, apiToDuckdb: false, apiToRag: false,
    ragToChroma: false, ragToClaude: false, ragToLocalLLM: false,
  });

  const requestCountRef = useRef(0);

  // Fetch costs
  useEffect(() => {
    const fetchCosts = async () => {
      try {
        setCostsLoading(true);
        const [summaryRes, recentRes, monthRes, dailyRes] = await Promise.all([
          api.get('/status/costs?days=30').catch(() => ({ data: {} })),
          api.get('/status/costs/recent?limit=20').catch(() => ({ data: { records: [] } })),
          api.get('/status/costs/month').catch(() => ({ data: {} })),
          api.get('/status/costs/daily?days=7').catch(() => ({ data: [] })),
        ]);
        setCosts(summaryRes.data || {});
        setRecentCosts(recentRes.data?.records || []);
        setMonthCosts(monthRes.data || {});
        setDailyCosts(Array.isArray(dailyRes.data) ? dailyRes.data : []);
      } catch (err) {
        console.error('Cost fetch error:', err);
      } finally {
        setCostsLoading(false);
      }
    };
    fetchCosts();
    const interval = setInterval(fetchCosts, 30000);
    return () => clearInterval(interval);
  }, []);

  // Fetch metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setDataFlowActive(prev => ({ ...prev, frontendToApi: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, frontendToApi: false })), 500);

        const [structuredRes, chromaRes] = await Promise.all([
          api.get('/status/structured').catch(() => ({ data: {} })),
          api.get('/status/chromadb').catch(() => ({ data: {} })),
        ]);

        requestCountRef.current += 2;
        setMetrics(prev => ({
          ...prev,
          apiRequests: requestCountRef.current,
          totalFiles: structuredRes.data?.total_files || 0,
          totalRows: structuredRes.data?.total_rows || 0,
          dbQueries: prev.dbQueries + 1,
        }));

        setDataStats({
          chunks: chromaRes.data?.total_chunks || chromaRes.data?.chunk_count || 0,
          structured: structuredRes.data?.total_rows || 0,
          loading: false,
        });

        setComponentStatus(prev => ({
          ...prev,
          duckdb: structuredRes.data?.available !== false ? 'healthy' : 'error',
          chromadb: chromaRes.data?.status === 'operational' ? 'healthy' : 'warning',
        }));

        setDataFlowActive(prev => ({ ...prev, apiToDuckdb: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, apiToDuckdb: false })), 300);
      } catch (err) {
        console.error('Metrics fetch error:', err);
      }
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  // Activity simulation
  useEffect(() => {
    const activities = [
      { type: 'query', message: 'DuckDB: Query executed', color: COLORS.purple },
      { type: 'upload', message: 'File ingested', color: COLORS.blue },
      { type: 'claude', message: 'Claude API response', color: COLORS.cyan },
      { type: 'llama', message: 'Llama 3.1 inference', color: COLORS.green },
      { type: 'rag', message: 'RAG context retrieved', color: COLORS.orange },
      { type: 'auth', message: 'Session validated', color: COLORS.pink },
    ];

    const addActivity = () => {
      const act = activities[Math.floor(Math.random() * activities.length)];
      setActivity(prev => [{ ...act, time: new Date().toLocaleTimeString(), id: Date.now() }, ...prev.slice(0, 9)]);

      if (act.type === 'claude') {
        setDataFlowActive(prev => ({ ...prev, ragToClaude: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, ragToClaude: false })), 800);
        setMetrics(prev => ({ ...prev, llmCalls: prev.llmCalls + 1 }));
      } else if (act.type === 'llama') {
        setDataFlowActive(prev => ({ ...prev, ragToLocalLLM: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, ragToLocalLLM: false })), 700);
        setMetrics(prev => ({ ...prev, llmCalls: prev.llmCalls + 1 }));
      } else if (act.type === 'rag') {
        setDataFlowActive(prev => ({ ...prev, apiToRag: true, ragToChroma: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, apiToRag: false, ragToChroma: false })), 600);
        setMetrics(prev => ({ ...prev, ragQueries: prev.ragQueries + 1 }));
      } else if (act.type === 'query') {
        setDataFlowActive(prev => ({ ...prev, apiToDuckdb: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, apiToDuckdb: false })), 500);
        setMetrics(prev => ({ ...prev, dbQueries: prev.dbQueries + 1 }));
      }
    };

    const interval = setInterval(addActivity, 3000);
    return () => clearInterval(interval);
  }, []);

  const allHealthy = Object.values(componentStatus).every(s => s === 'healthy');

  const refreshCosts = async () => {
    const monthRes = await api.get('/status/costs/month').catch(() => ({ data: {} }));
    setMonthCosts(monthRes.data || {});
  };

  return (
    <div style={{ background: COLORS.bg, minHeight: '100vh', padding: '0' }}>
      {/* Header */}
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <h1 style={{ fontFamily: 'Sora, sans-serif', fontSize: '1.4rem', fontWeight: 700, color: COLORS.text, margin: 0 }}>
            System Monitor
          </h1>
          <StatusLight status={allHealthy ? 'healthy' : 'warning'} size={10} />
        </div>
        <p style={{ color: COLORS.textMuted, fontSize: '0.8rem', margin: 0 }}>
          Real-time data flow, cost tracking & system health
        </p>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <MonthCostCard monthCosts={monthCosts} loading={costsLoading} onSettingsClick={() => setShowSettings(true)} />
        <ApiUsageCard costs={costs} loading={costsLoading} />
        <DailySpendCard dailyCosts={dailyCosts} loading={costsLoading} />
        <DataStorageCard chunks={dataStats.chunks} structured={dataStats.structured} loading={dataStats.loading} />
        <MetricCard icon="📡" label="API Calls" value={metrics.apiRequests} subValue="Session" color={COLORS.blue} />
        <MetricCard icon="🦆" label="DB Queries" value={metrics.dbQueries} subValue="DuckDB" color={COLORS.purple} />
        <MetricCard icon="🔍" label="RAG" value={metrics.ragQueries} subValue="Searches" color={COLORS.orange} />
        <MetricCard icon="🤖" label="LLM" value={metrics.llmCalls} subValue="Calls" color={COLORS.cyan} />
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: '1rem' }}>
        {/* Architecture Diagram */}
        <div style={{
          background: COLORS.archBg, borderRadius: 12, padding: '1rem',
          border: `1px solid ${COLORS.border}`, boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        }}>
          <h2 style={{ color: COLORS.text, fontSize: '1rem', fontWeight: 600, margin: '0 0 0.5rem 0' }}>
            Architecture & Data Flow
          </h2>
          <ArchitectureDiagram componentStatus={componentStatus} dataFlowActive={dataFlowActive} />
        </div>

        {/* Activity Panel */}
        <ActivityPanel
          recentCosts={recentCosts}
          activity={activity}
          showCosts={showCostDetails}
          onToggle={() => setShowCostDetails(!showCostDetails)}
          loading={costsLoading}
        />
      </div>

      {/* Status Bar */}
      <div style={{
        marginTop: '1rem', background: COLORS.cardBg, borderRadius: 10, padding: '0.6rem 1rem',
        border: `1px solid ${COLORS.border}`, display: 'flex', justifyContent: 'space-around',
        alignItems: 'center', flexWrap: 'wrap', gap: '0.4rem',
      }}>
        {Object.entries(componentStatus).slice(0, 8).map(([name, status]) => (
          <div key={name} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <StatusLight status={status} size={5} />
            <span style={{
              color: status === 'healthy' ? COLORS.green : status === 'warning' ? COLORS.yellow : COLORS.red,
              fontSize: '0.6rem', fontWeight: 600, textTransform: 'uppercase'
            }}>{name}</span>
          </div>
        ))}
      </div>

      {/* Cost Settings Modal */}
      <CostSettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        fixedItems={monthCosts.fixed_items}
        onSave={refreshCosts}
      />
    </div>
  );
}
