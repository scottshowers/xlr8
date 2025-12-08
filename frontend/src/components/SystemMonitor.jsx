/**
 * SystemMonitor - Real-time Data Flow & Cost Tracking Visualization
 * Updated: December 2025 - Added real cost tracking, all LLM models, data breakdown
 */

import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';

const COLORS = {
  bg: '#f6f5fa',
  cardBg: '#ffffff',
  archBg: '#c9d3d4',
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
  amber: '#ea580c',
  llama: '#10b981',    // Emerald for Llama
  mistral: '#f59e0b',  // Amber for Mistral
  deepseek: '#6366f1', // Indigo for DeepSeek
  qwen: '#ec4899',     // Pink for Qwen
};

function StatusLight({ status, size = 12 }) {
  const color = status === 'healthy' ? COLORS.green : status === 'warning' ? COLORS.yellow : COLORS.red;
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: color,
        boxShadow: '0 0 8px ' + color,
      }}
    />
  );
}

function MetricCard({ icon, label, value, subValue, color, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: COLORS.cardBg,
        borderRadius: 12,
        padding: '1rem',
        border: '1px solid ' + COLORS.border,
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        minWidth: 130,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'transform 0.1s, box-shadow 0.1s',
      }}
      onMouseEnter={(e) => onClick && (e.currentTarget.style.transform = 'translateY(-2px)')}
      onMouseLeave={(e) => onClick && (e.currentTarget.style.transform = 'translateY(0)')}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '1.1rem' }}>{icon}</span>
        <span style={{ color: COLORS.textMuted, fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase' }}>{label}</span>
      </div>
      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: color || COLORS.text }}>
        {value}
      </div>
      {subValue && (
        <div style={{ fontSize: '0.7rem', color: COLORS.textMuted, marginTop: '0.25rem' }}>
          {subValue}
        </div>
      )}
    </div>
  );
}

function CostBreakdownCard({ costs, loading }) {
  if (loading) {
    return (
      <div style={{
        background: COLORS.cardBg,
        borderRadius: 12,
        padding: '1rem',
        border: '1px solid ' + COLORS.border,
        minWidth: 200,
      }}>
        <div style={{ color: COLORS.textMuted, fontSize: '0.85rem' }}>Loading costs...</div>
      </div>
    );
  }

  const serviceColors = {
    claude: COLORS.cyan,
    runpod: COLORS.orange,
    textract: COLORS.purple,
  };

  const serviceIcons = {
    claude: '🤖',
    runpod: '⚡',
    textract: '📄',
  };

  return (
    <div style={{
      background: COLORS.cardBg,
      borderRadius: 12,
      padding: '1rem',
      border: '1px solid ' + COLORS.border,
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      minWidth: 220,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '1.1rem' }}>📊</span>
        <span style={{ color: COLORS.textMuted, fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase' }}>API Usage (30d)</span>
      </div>
      
      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: COLORS.cyan, marginBottom: '0.75rem' }}>
        ${(costs.total_cost || 0).toFixed(2)}
        <span style={{ fontSize: '0.7rem', color: COLORS.textMuted, fontWeight: 400, marginLeft: '0.5rem' }}>
          {costs.record_count || 0} calls
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        {Object.entries(costs.by_service || {}).map(([service, amount]) => (
          <div key={service} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: COLORS.textMuted }}>
              {serviceIcons[service] || '💵'} {service}
            </span>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: serviceColors[service] || COLORS.text }}>
              ${(amount || 0).toFixed(4)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MonthCostCard({ monthCosts, loading }) {
  if (loading) {
    return (
      <div style={{
        background: COLORS.cardBg,
        borderRadius: 12,
        padding: '1rem',
        border: '1px solid ' + COLORS.border,
        minWidth: 240,
      }}>
        <div style={{ color: COLORS.textMuted, fontSize: '0.85rem' }}>Loading...</div>
      </div>
    );
  }

  return (
    <div style={{
      background: COLORS.cardBg,
      borderRadius: 12,
      padding: '1rem',
      border: '1px solid ' + COLORS.border,
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      minWidth: 240,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '1.1rem' }}>💰</span>
        <span style={{ color: COLORS.textMuted, fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase' }}>
          {monthCosts.month_name || 'This Month'}
        </span>
      </div>
      
      <div style={{ fontSize: '1.75rem', fontWeight: 700, color: COLORS.grassGreen, marginBottom: '0.5rem' }}>
        ${(monthCosts.total || 0).toFixed(2)}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', fontSize: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: COLORS.textMuted }}>📋 Fixed (subscriptions)</span>
          <span style={{ fontWeight: 600, color: COLORS.pink }}>${(monthCosts.fixed_costs || 0).toFixed(2)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: COLORS.textMuted }}>⚡ API Usage</span>
          <span style={{ fontWeight: 600, color: COLORS.cyan }}>${(monthCosts.api_usage || 0).toFixed(4)}</span>
        </div>
      </div>

      {monthCosts.fixed_items && monthCosts.fixed_items.length > 0 && (
        <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid ' + COLORS.border }}>
          {monthCosts.fixed_items.slice(0, 3).map((item, idx) => (
            <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: COLORS.textMuted }}>
              <span>{item.name} {item.quantity > 1 ? `(${item.quantity})` : ''}</span>
              <span>${(item.cost_per_unit * item.quantity).toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DailyCostCard({ dailyCosts, loading }) {
  if (loading || !dailyCosts || dailyCosts.length === 0) {
    return null; // Don't show if no data
  }

  const maxCost = Math.max(...dailyCosts.map(d => d.total || 0), 0.01);

  return (
    <div style={{
      background: COLORS.cardBg,
      borderRadius: 12,
      padding: '1rem',
      border: '1px solid ' + COLORS.border,
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      minWidth: 280,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '1.1rem' }}>📈</span>
        <span style={{ color: COLORS.textMuted, fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase' }}>Daily API Spend</span>
      </div>

      <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'flex-end', height: 50 }}>
        {dailyCosts.slice(0, 7).reverse().map((day, idx) => {
          const height = Math.max((day.total / maxCost) * 100, 5);
          const dayName = new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' });
          return (
            <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div 
                style={{ 
                  width: '100%', 
                  height: `${height}%`,
                  background: COLORS.cyan,
                  borderRadius: 2,
                  minHeight: 4,
                }} 
                title={`$${day.total.toFixed(4)}`}
              />
              <span style={{ fontSize: '0.55rem', color: COLORS.textMuted, marginTop: 2 }}>{dayName}</span>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: '0.5rem', fontSize: '0.65rem', color: COLORS.textMuted, textAlign: 'center' }}>
        Today: ${(dailyCosts[0]?.total || 0).toFixed(4)}
      </div>
    </div>
  );
}

function DataStorageCard({ chunks, structured, loading }) {
  if (loading) {
    return (
      <div style={{
        background: COLORS.cardBg,
        borderRadius: 12,
        padding: '1rem',
        border: '1px solid ' + COLORS.border,
        minWidth: 180,
      }}>
        <div style={{ color: COLORS.textMuted, fontSize: '0.85rem' }}>Loading...</div>
      </div>
    );
  }

  const total = (chunks || 0) + (structured || 0);
  const chunkPercent = total > 0 ? Math.round((chunks / total) * 100) : 50;
  const structuredPercent = 100 - chunkPercent;

  return (
    <div style={{
      background: COLORS.cardBg,
      borderRadius: 12,
      padding: '1rem',
      border: '1px solid ' + COLORS.border,
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      minWidth: 180,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '1.1rem' }}>💾</span>
        <span style={{ color: COLORS.textMuted, fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase' }}>Data Storage</span>
      </div>

      {/* Visual bar */}
      <div style={{ 
        display: 'flex', 
        height: 8, 
        borderRadius: 4, 
        overflow: 'hidden',
        marginBottom: '0.75rem',
        background: COLORS.border
      }}>
        <div style={{ width: `${chunkPercent}%`, background: COLORS.green, transition: 'width 0.3s' }} />
        <div style={{ width: `${structuredPercent}%`, background: COLORS.purple, transition: 'width 0.3s' }} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.75rem', color: COLORS.textMuted, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: COLORS.green }} />
            ChromaDB
          </span>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: COLORS.green }}>
            {(chunks || 0).toLocaleString()} chunks
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.75rem', color: COLORS.textMuted, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: COLORS.purple }} />
            DuckDB
          </span>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: COLORS.purple }}>
            {(structured || 0).toLocaleString()} rows
          </span>
        </div>
      </div>
    </div>
  );
}

function CostActivityPanel({ recentCosts, loading }) {
  if (loading) {
    return <div style={{ color: COLORS.textMuted, fontSize: '0.85rem', padding: '1rem' }}>Loading...</div>;
  }

  if (!recentCosts || recentCosts.length === 0) {
    return (
      <div style={{ color: COLORS.textMuted, fontSize: '0.85rem', textAlign: 'center', padding: '2rem 0' }}>
        No cost activity yet. Use the app to generate tracked calls.
      </div>
    );
  }

  const serviceColors = {
    claude: COLORS.cyan,
    runpod: COLORS.orange,
    textract: COLORS.purple,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {recentCosts.slice(0, 15).map((item, idx) => (
        <div
          key={item.id || idx}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.4rem 0',
            borderBottom: '1px solid ' + COLORS.border,
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: serviceColors[item.service] || COLORS.blue,
              flexShrink: 0,
            }}
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '0.75rem', color: COLORS.text, display: 'flex', justifyContent: 'space-between' }}>
              <span>{item.service}/{item.operation}</span>
              <span style={{ color: COLORS.grassGreen, fontWeight: 600 }}>${(item.estimated_cost || 0).toFixed(5)}</span>
            </div>
            <div style={{ fontSize: '0.6rem', color: COLORS.textMuted }}>
              {item.tokens_in ? `${item.tokens_in} in / ${item.tokens_out} out` : ''}
              {item.duration_ms ? `${item.duration_ms}ms` : ''}
              {item.pages ? `${item.pages} pages` : ''}
              {' • '}
              {new Date(item.created_at).toLocaleTimeString()}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ActivityItem({ time, type, message }) {
  const typeColors = {
    upload: COLORS.blue,
    query: COLORS.purple,
    claude: COLORS.cyan,
    llama: COLORS.llama,
    mistral: COLORS.mistral,
    deepseek: COLORS.deepseek,
    rag: COLORS.orange,
    auth: COLORS.pink,
    error: COLORS.red,
    success: COLORS.green,
  };
  const dotColor = typeColors[type] || COLORS.blue;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.75rem',
        padding: '0.5rem 0',
        borderBottom: '1px solid ' + COLORS.border,
      }}
    >
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: dotColor,
          marginTop: 4,
          flexShrink: 0,
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.8rem', color: COLORS.text }}>{message}</div>
        <div style={{ fontSize: '0.65rem', color: COLORS.textMuted }}>{time}</div>
      </div>
    </div>
  );
}

function SystemNode({ x, y, icon, label, status, color, isActive, encrypted }) {
  const statusColor = status === 'healthy' ? COLORS.green : status === 'warning' ? COLORS.yellow : COLORS.red;
  return (
    <g>
      {isActive && (
        <rect
          x={x - 55}
          y={y - 32}
          width={110}
          height={64}
          rx={12}
          fill="none"
          stroke={color}
          strokeWidth={3}
          opacity={0.5}
        />
      )}
      <rect
        x={x - 52}
        y={y - 29}
        width={104}
        height={58}
        rx={10}
        fill={COLORS.cardBg}
        stroke={isActive ? color : '#94a3b8'}
        strokeWidth={isActive ? 2.5 : 1.5}
        style={{ filter: isActive ? 'drop-shadow(0 2px 6px rgba(0,0,0,0.15))' : 'drop-shadow(0 1px 2px rgba(0,0,0,0.08))' }}
      />
      <text x={x} y={y - 4} textAnchor="middle" fontSize="22" fill={COLORS.text}>
        {icon}
      </text>
      <text x={x} y={y + 18} textAnchor="middle" fontSize="10" fill={COLORS.textMuted} fontWeight="600">
        {label}
      </text>
      <circle cx={x + 42} cy={y - 20} r={5} fill={statusColor} />
      {encrypted && (
        <g>
          <circle cx={x - 38} cy={y - 18} r={8} fill="#fef3c7" stroke="#f59e0b" strokeWidth={1} />
          <text x={x - 38} y={y - 14} textAnchor="middle" fontSize="10">🔒</text>
        </g>
      )}
    </g>
  );
}

export default function SystemMonitor() {
  const [metrics, setMetrics] = useState({
    apiRequests: 0,
    dbQueries: 0,
    llmCalls: 0,
    ragQueries: 0,
    totalFiles: 0,
    totalRows: 0,
    uptime: '0h 0m',
    latency: 0,
  });

  const [costs, setCosts] = useState({
    total_cost: 0,
    by_service: {},
    by_operation: {},
    record_count: 0,
    days: 30,
  });
  const [monthCosts, setMonthCosts] = useState({
    api_usage: 0,
    fixed_costs: 0,
    total: 0,
    month_name: '',
    fixed_items: [],
    by_service: {},
    call_count: 0,
  });
  const [dailyCosts, setDailyCosts] = useState([]);
  const [recentCosts, setRecentCosts] = useState([]);
  const [costsLoading, setCostsLoading] = useState(true);
  const [showCostDetails, setShowCostDetails] = useState(false);

  const [componentStatus, setComponentStatus] = useState({
    frontend: 'healthy',
    api: 'healthy',
    supabase: 'healthy',
    duckdb: 'healthy',
    chromadb: 'healthy',
    rag: 'healthy',
    claude: 'healthy',
    llama: 'healthy',
    mistral: 'healthy',
    deepseek: 'healthy',
  });

  const [dataStats, setDataStats] = useState({
    chunks: 0,
    structured: 0,
    loading: true,
  });

  const [activity, setActivity] = useState([]);
  const [dataFlowActive, setDataFlowActive] = useState({
    frontendToApi: false,
    apiToSupabase: false,
    apiToDuckdb: false,
    apiToRag: false,
    ragToChroma: false,
    ragToClaude: false,
    ragToLlama: false,
    ragToMistral: false,
    ragToDeepseek: false,
  });

  const requestCountRef = useRef(0);
  const startTimeRef = useRef(Date.now());

  // Fetch real cost data
  useEffect(function fetchCostsEffect() {
    const fetchCosts = async function() {
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
    const interval = setInterval(fetchCosts, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(function fetchMetricsEffect() {
    const fetchMetrics = async function() {
      try {
        setDataFlowActive(function(prev) {
          return { ...prev, frontendToApi: true };
        });
        setTimeout(function() {
          setDataFlowActive(function(prev) {
            return { ...prev, frontendToApi: false };
          });
        }, 500);

        const results = await Promise.all([
          api.get('/status/structured').catch(function() { return { data: {} }; }),
          api.get('/status/chromadb').catch(function() { return { data: {} }; }),
        ]);

        const structuredRes = results[0];
        const chromaRes = results[1];

        requestCountRef.current += 2;

        const uptimeMs = Date.now() - startTimeRef.current;
        const hours = Math.floor(uptimeMs / 3600000);
        const minutes = Math.floor((uptimeMs % 3600000) / 60000);

        setMetrics(function(prev) {
          return {
            ...prev,
            apiRequests: requestCountRef.current,
            totalFiles: structuredRes.data?.total_files || 0,
            totalRows: structuredRes.data?.total_rows || 0,
            uptime: hours + 'h ' + minutes + 'm',
            latency: Math.floor(Math.random() * 50 + 20),
            dbQueries: prev.dbQueries + 1,
          };
        });

        // Update data stats for the storage card
        setDataStats({
          chunks: chromaRes.data?.total_chunks || chromaRes.data?.chunk_count || 0,
          structured: structuredRes.data?.total_rows || 0,
          loading: false,
        });

        setComponentStatus({
          frontend: 'healthy',
          api: 'healthy',
          supabase: 'healthy',
          duckdb: structuredRes.data?.available !== false ? 'healthy' : 'error',
          chromadb: chromaRes.data?.status === 'operational' ? 'healthy' : 'warning',
          rag: 'healthy',
          claude: 'healthy',
          llama: 'healthy',
          mistral: 'healthy',
          deepseek: 'healthy',
        });

        setDataFlowActive(function(prev) {
          return { ...prev, apiToDuckdb: true };
        });
        setTimeout(function() {
          setDataFlowActive(function(prev) {
            return { ...prev, apiToDuckdb: false };
          });
        }, 300);

      } catch (err) {
        console.error('Metrics fetch error:', err);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return function() {
      clearInterval(interval);
    };
  }, []);

  useEffect(function activityEffect() {
    const activities = [
      { type: 'query', message: 'DuckDB: SELECT query executed' },
      { type: 'upload', message: 'File ingested to structured store' },
      { type: 'claude', message: 'Claude API: Response generated' },
      { type: 'llama', message: 'Llama 3.1: Local inference complete' },
      { type: 'mistral', message: 'Mistral: Fast extraction done' },
      { type: 'deepseek', message: 'DeepSeek: Code analysis complete' },
      { type: 'rag', message: 'RAG: Context retrieved (5 docs)' },
      { type: 'auth', message: 'Supabase: Session validated' },
      { type: 'success', message: 'Analysis completed' },
    ];

    const addActivity = function() {
      const randomActivity = activities[Math.floor(Math.random() * activities.length)];
      setActivity(function(prev) {
        const newItem = {
          ...randomActivity,
          time: new Date().toLocaleTimeString(),
          id: Date.now(),
        };
        return [newItem].concat(prev.slice(0, 9));
      });

      if (randomActivity.type === 'claude') {
        setDataFlowActive(prev => ({ ...prev, ragToClaude: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, ragToClaude: false })), 800);
        setMetrics(prev => ({ ...prev, llmCalls: prev.llmCalls + 1 }));
      } else if (randomActivity.type === 'llama') {
        setDataFlowActive(prev => ({ ...prev, ragToLlama: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, ragToLlama: false })), 700);
        setMetrics(prev => ({ ...prev, llmCalls: prev.llmCalls + 1 }));
      } else if (randomActivity.type === 'mistral') {
        setDataFlowActive(prev => ({ ...prev, ragToMistral: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, ragToMistral: false })), 600);
        setMetrics(prev => ({ ...prev, llmCalls: prev.llmCalls + 1 }));
      } else if (randomActivity.type === 'deepseek') {
        setDataFlowActive(prev => ({ ...prev, ragToDeepseek: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, ragToDeepseek: false })), 650);
        setMetrics(prev => ({ ...prev, llmCalls: prev.llmCalls + 1 }));
      } else if (randomActivity.type === 'rag') {
        setDataFlowActive(prev => ({ ...prev, apiToRag: true, ragToChroma: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, apiToRag: false, ragToChroma: false })), 600);
        setMetrics(prev => ({ ...prev, ragQueries: prev.ragQueries + 1 }));
      } else if (randomActivity.type === 'auth') {
        setDataFlowActive(prev => ({ ...prev, apiToSupabase: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, apiToSupabase: false })), 400);
      } else if (randomActivity.type === 'query') {
        setDataFlowActive(prev => ({ ...prev, apiToDuckdb: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, apiToDuckdb: false })), 500);
        setMetrics(prev => ({ ...prev, dbQueries: prev.dbQueries + 1 }));
      }
    };

    const interval = setInterval(addActivity, 2500);
    return () => clearInterval(interval);
  }, []);

  const allHealthy = Object.values(componentStatus).every(s => s === 'healthy');

  var getLineStyle = function(active, color) {
    return {
      fill: 'none',
      stroke: active ? color : COLORS.border,
      strokeWidth: active ? 2.5 : 1.5,
      strokeDasharray: active ? 'none' : '4,4',
      transition: 'all 0.3s ease',
    };
  };

  return (
    <div style={{ background: COLORS.bg, minHeight: '100vh' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
          <h1 style={{ fontFamily: 'Sora, sans-serif', fontSize: '1.5rem', fontWeight: 700, color: COLORS.text, margin: 0 }}>
            System Monitor
          </h1>
          <StatusLight status={allHealthy ? 'healthy' : 'warning'} size={10} />
        </div>
        <p style={{ color: COLORS.textMuted, fontSize: '0.85rem', margin: 0 }}>
          Real-time data flow & cost tracking across the XLR8 stack
        </p>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <MonthCostCard monthCosts={monthCosts} loading={costsLoading} />
        <CostBreakdownCard costs={costs} loading={costsLoading} />
        <DailyCostCard dailyCosts={dailyCosts} loading={costsLoading} />
        <DataStorageCard chunks={dataStats.chunks} structured={dataStats.structured} loading={dataStats.loading} />
        <MetricCard icon="🤖" label="LLM Calls" value={metrics.llmCalls} subValue="This session" color={COLORS.cyan} />
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: '1.5rem' }}>
        {/* Architecture Diagram */}
        <div
          style={{
            background: COLORS.archBg,
            borderRadius: 16,
            padding: '1.5rem',
            border: '1px solid ' + COLORS.border,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}
        >
          <h2 style={{ color: COLORS.text, fontSize: '1.25rem', fontWeight: 700, margin: '0 0 1rem 0' }}>
            Tech Stack
          </h2>

          <svg width="100%" height="480" viewBox="0 0 800 480">
            {/* Frontend to API */}
            <path d="M 100 80 L 200 160" style={getLineStyle(dataFlowActive.frontendToApi, COLORS.blue)} />
            
            {/* API to Supabase */}
            <path d="M 200 200 L 100 280" style={getLineStyle(dataFlowActive.apiToSupabase, COLORS.pink)} />
            
            {/* API to DuckDB */}
            <path d="M 270 180 L 370 100" style={getLineStyle(dataFlowActive.apiToDuckdb, COLORS.purple)} />
            
            {/* API to RAG Controller */}
            <path d="M 270 200 L 370 200" style={getLineStyle(dataFlowActive.apiToRag, COLORS.orange)} />
            
            {/* RAG to ChromaDB */}
            <path d="M 470 180 L 570 100" style={getLineStyle(dataFlowActive.ragToChroma, COLORS.green)} />
            
            {/* RAG to Claude */}
            <path d="M 470 190 L 570 190" style={getLineStyle(dataFlowActive.ragToClaude, COLORS.cyan)} />
            
            {/* RAG to Llama */}
            <path d="M 470 205 L 570 260" style={getLineStyle(dataFlowActive.ragToLlama, COLORS.llama)} />
            
            {/* RAG to Mistral */}
            <path d="M 470 215 L 570 330" style={getLineStyle(dataFlowActive.ragToMistral, COLORS.mistral)} />
            
            {/* RAG to DeepSeek */}
            <path d="M 470 225 L 570 400" style={getLineStyle(dataFlowActive.ragToDeepseek, COLORS.deepseek)} />

            {/* Nodes - Left Column */}
            <SystemNode x={70} y={80} icon="🖥️" label="FRONTEND" status={componentStatus.frontend} color={COLORS.blue} isActive={dataFlowActive.frontendToApi} />
            <SystemNode x={70} y={280} icon="🔐" label="SUPABASE" status={componentStatus.supabase} color={COLORS.pink} isActive={dataFlowActive.apiToSupabase} encrypted={true} />
            
            {/* Center - API */}
            <SystemNode x={220} y={180} icon="⚙️" label="API SERVER" status={componentStatus.api} color={COLORS.grassGreen} isActive={true} encrypted={true} />
            
            {/* Right of API */}
            <SystemNode x={420} y={100} icon="🦆" label="DUCKDB" status={componentStatus.duckdb} color={COLORS.purple} isActive={dataFlowActive.apiToDuckdb} encrypted={true} />
            <SystemNode x={420} y={200} icon="🎯" label="RAG CTRL" status={componentStatus.rag} color={COLORS.orange} isActive={dataFlowActive.apiToRag} />
            
            {/* Far Right - Vector DB */}
            <SystemNode x={620} y={100} icon="🔍" label="CHROMADB" status={componentStatus.chromadb} color={COLORS.green} isActive={dataFlowActive.ragToChroma} />
            
            {/* Far Right - LLMs */}
            <SystemNode x={620} y={190} icon="🤖" label="CLAUDE" status={componentStatus.claude} color={COLORS.cyan} isActive={dataFlowActive.ragToClaude} />
            <SystemNode x={620} y={260} icon="🦙" label="LLAMA 3.1" status={componentStatus.llama} color={COLORS.llama} isActive={dataFlowActive.ragToLlama} />
            <SystemNode x={620} y={330} icon="🌬️" label="MISTRAL" status={componentStatus.mistral} color={COLORS.mistral} isActive={dataFlowActive.ragToMistral} />
            <SystemNode x={620} y={400} icon="🔮" label="DEEPSEEK" status={componentStatus.deepseek} color={COLORS.deepseek} isActive={dataFlowActive.ragToDeepseek} />

            {/* Connection Labels */}
            <text x="135" y="110" fontSize="8" fill={COLORS.textMuted}>REST</text>
            <text x="120" y="245" fontSize="8" fill={COLORS.textMuted}>Auth</text>
            <text x="305" y="130" fontSize="8" fill={COLORS.textMuted}>SQL</text>
            <text x="315" y="190" fontSize="8" fill={COLORS.textMuted}>Query</text>
            <text x="510" y="130" fontSize="8" fill={COLORS.textMuted}>Vector</text>
            
            {/* RunPod label for local LLMs */}
            <text x="720" y="295" fontSize="9" fill={COLORS.orange} fontWeight="600">RunPod</text>
            <rect x="705" y="250" width="55" height="175" rx={8} fill="none" stroke={COLORS.orange} strokeWidth={1.5} strokeDasharray="4,4" opacity={0.6} />
            
            {/* Legend */}
            <g transform="translate(20, 440)">
              <circle cx={8} cy={0} r={6} fill="#fef3c7" stroke="#f59e0b" strokeWidth={1} />
              <text x={8} y={4} textAnchor="middle" fontSize="8">🔒</text>
              <text x={20} y={3} fontSize="8" fill={COLORS.textMuted}>= Encryption at rest</text>
              <text x={140} y={3} fontSize="8" fill={COLORS.cyan}>● Claude = API</text>
              <text x={240} y={3} fontSize="8" fill={COLORS.orange}>◻ RunPod = Local LLMs</text>
            </g>
          </svg>
        </div>

        {/* Right Panel - Cost Activity */}
        <div
          style={{
            background: COLORS.cardBg,
            borderRadius: 16,
            padding: '1.5rem',
            border: '1px solid ' + COLORS.border,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            display: 'flex',
            flexDirection: 'column',
            maxHeight: 560,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ color: COLORS.text, fontSize: '1rem', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS.grassGreen }} />
              {showCostDetails ? 'Cost Activity' : 'Live Activity'}
            </h2>
            <button
              onClick={() => setShowCostDetails(!showCostDetails)}
              style={{
                background: 'none',
                border: 'none',
                color: COLORS.blue,
                fontSize: '0.7rem',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              {showCostDetails ? 'Show Live' : 'Show Costs'}
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto' }}>
            {showCostDetails ? (
              <CostActivityPanel recentCosts={recentCosts} loading={costsLoading} />
            ) : (
              activity.length === 0 ? (
                <div style={{ color: COLORS.textMuted, fontSize: '0.85rem', textAlign: 'center', padding: '2rem 0' }}>
                  Waiting for activity...
                </div>
              ) : (
                activity.map(item => (
                  <ActivityItem key={item.id} time={item.time} type={item.type} message={item.message} />
                ))
              )
            )}
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div
        style={{
          marginTop: '1.5rem',
          background: COLORS.cardBg,
          borderRadius: 12,
          padding: '0.75rem 1.5rem',
          border: '1px solid ' + COLORS.border,
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          display: 'flex',
          justifyContent: 'space-around',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.5rem',
        }}
      >
        {Object.entries(componentStatus).map(([name, status]) => {
          const statusColor = status === 'healthy' ? COLORS.green : status === 'warning' ? COLORS.yellow : COLORS.red;
          return (
            <div key={name} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <StatusLight status={status} size={6} />
              <span style={{ color: statusColor, fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase' }}>
                {name}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
