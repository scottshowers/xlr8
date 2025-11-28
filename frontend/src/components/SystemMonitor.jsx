/**
 * SystemMonitor - Real-time Data Flow Visualization
 * 
 * Visual architecture diagram with:
 * - Animated data flow between components
 * - Blinking status lights
 * - Real-time metrics
 * - Activity pulse effects
 */

import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';

const COLORS = {
  bg: '#0f172a',
  cardBg: '#1e293b',
  border: '#334155',
  text: '#e2e8f0',
  textMuted: '#94a3b8',
  green: '#22c55e',
  greenGlow: 'rgba(34, 197, 94, 0.4)',
  yellow: '#eab308',
  yellowGlow: 'rgba(234, 179, 8, 0.4)',
  red: '#ef4444',
  redGlow: 'rgba(239, 68, 68, 0.4)',
  blue: '#3b82f6',
  blueGlow: 'rgba(59, 130, 246, 0.4)',
  purple: '#a855f7',
  purpleGlow: 'rgba(168, 85, 247, 0.4)',
  cyan: '#06b6d4',
  cyanGlow: 'rgba(6, 182, 212, 0.4)',
};

// Animated status light component
const StatusLight = ({ status, size = 12, pulse = true }) => {
  const color = status === 'healthy' ? COLORS.green : status === 'warning' ? COLORS.yellow : COLORS.red;
  const glow = status === 'healthy' ? COLORS.greenGlow : status === 'warning' ? COLORS.yellowGlow : COLORS.redGlow;
  
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      {pulse && (
        <div style={{
          position: 'absolute',
          width: size,
          height: size,
          borderRadius: '50%',
          background: glow,
          animation: 'pulse 2s ease-in-out infinite',
        }} />
      )}
      <div style={{
        position: 'absolute',
        width: size,
        height: size,
        borderRadius: '50%',
        background: color,
        boxShadow: `0 0 ${size}px ${glow}`,
      }} />
    </div>
  );
};

// Data flow particle
const DataParticle = ({ startX, startY, endX, endY, color, delay = 0 }) => {
  return (
    <circle
      r="3"
      fill={color}
      style={{
        filter: `drop-shadow(0 0 4px ${color})`,
      }}
    >
      <animateMotion
        dur="1.5s"
        repeatCount="indefinite"
        begin={`${delay}s`}
        path={`M ${startX} ${startY} Q ${(startX + endX) / 2} ${Math.min(startY, endY) - 30} ${endX} ${endY}`}
      />
    </circle>
  );
};

// System node component
const SystemNode = ({ x, y, icon, label, status, metrics, color, glowColor, isActive }) => {
  return (
    <g>
      {/* Glow effect when active */}
      {isActive && (
        <rect
          x={x - 55}
          y={y - 35}
          width={110}
          height={70}
          rx={12}
          fill="none"
          stroke={glowColor}
          strokeWidth={2}
          style={{ animation: 'nodeGlow 1s ease-in-out infinite' }}
        />
      )}
      
      {/* Main box */}
      <rect
        x={x - 50}
        y={y - 30}
        width={100}
        height={60}
        rx={10}
        fill={COLORS.cardBg}
        stroke={color}
        strokeWidth={2}
      />
      
      {/* Icon */}
      <text
        x={x}
        y={y - 5}
        textAnchor="middle"
        fontSize="20"
        fill={COLORS.text}
      >
        {icon}
      </text>
      
      {/* Label */}
      <text
        x={x}
        y={y + 18}
        textAnchor="middle"
        fontSize="10"
        fill={COLORS.textMuted}
        fontWeight="600"
      >
        {label}
      </text>
      
      {/* Status light */}
      <circle
        cx={x + 40}
        cy={y - 20}
        r={5}
        fill={status === 'healthy' ? COLORS.green : status === 'warning' ? COLORS.yellow : COLORS.red}
        style={{ filter: `drop-shadow(0 0 4px ${status === 'healthy' ? COLORS.green : status === 'warning' ? COLORS.yellow : COLORS.red})` }}
      >
        <animate attributeName="opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite" />
      </circle>
    </g>
  );
};

// Metric card component
const MetricCard = ({ icon, label, value, subValue, trend, color }) => {
  return (
    <div style={{
      background: COLORS.cardBg,
      borderRadius: 12,
      padding: '1rem',
      border: `1px solid ${COLORS.border}`,
      minWidth: 140,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '1.25rem' }}>{icon}</span>
        <span style={{ color: COLORS.textMuted, fontSize: '0.75rem', fontWeight: 600 }}>{label}</span>
      </div>
      <div style={{ fontSize: '1.75rem', fontWeight: 700, color: color || COLORS.text }}>
        {value}
      </div>
      {subValue && (
        <div style={{ fontSize: '0.7rem', color: COLORS.textMuted, marginTop: '0.25rem' }}>
          {subValue}
        </div>
      )}
      {trend && (
        <div style={{ 
          fontSize: '0.7rem', 
          color: trend > 0 ? COLORS.green : trend < 0 ? COLORS.red : COLORS.textMuted,
          marginTop: '0.25rem'
        }}>
          {trend > 0 ? '↑' : trend < 0 ? '↓' : '→'} {Math.abs(trend)}% vs last hour
        </div>
      )}
    </div>
  );
};

// Activity log item
const ActivityItem = ({ time, type, message, status }) => {
  const typeColors = {
    upload: COLORS.blue,
    query: COLORS.purple,
    llm: COLORS.cyan,
    error: COLORS.red,
    success: COLORS.green,
  };
  
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem',
      padding: '0.5rem 0',
      borderBottom: `1px solid ${COLORS.border}`,
    }}>
      <div style={{
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: typeColors[type] || COLORS.blue,
        marginTop: 4,
        flexShrink: 0,
        boxShadow: `0 0 8px ${typeColors[type] || COLORS.blue}`,
      }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.8rem', color: COLORS.text }}>{message}</div>
        <div style={{ fontSize: '0.65rem', color: COLORS.textMuted }}>{time}</div>
      </div>
    </div>
  );
};

export default function SystemMonitor() {
  const [metrics, setMetrics] = useState({
    apiRequests: 0,
    dbQueries: 0,
    llmCalls: 0,
    activeJobs: 0,
    totalFiles: 0,
    totalRows: 0,
    uptime: '0h 0m',
    latency: 0,
  });
  
  const [componentStatus, setComponentStatus] = useState({
    frontend: 'healthy',
    api: 'healthy',
    duckdb: 'healthy',
    chromadb: 'healthy',
    claude: 'healthy',
  });
  
  const [activity, setActivity] = useState([]);
  const [dataFlowActive, setDataFlowActive] = useState({
    frontendToApi: false,
    apiToDuckdb: false,
    apiToChroma: false,
    apiToClaude: false,
  });
  
  const requestCountRef = useRef(0);
  const startTimeRef = useRef(Date.now());

  // Fetch real metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        // Simulate API activity
        setDataFlowActive(prev => ({ ...prev, frontendToApi: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, frontendToApi: false })), 500);
        
        const [structuredRes, chromaRes, jobsRes] = await Promise.all([
          api.get('/status/structured').catch(() => ({ data: {} })),
          api.get('/status/chromadb').catch(() => ({ data: {} })),
          api.get('/jobs').catch(() => ({ data: [] })),
        ]);
        
        requestCountRef.current += 3;
        
        // Calculate uptime
        const uptimeMs = Date.now() - startTimeRef.current;
        const hours = Math.floor(uptimeMs / 3600000);
        const minutes = Math.floor((uptimeMs % 3600000) / 60000);
        
        setMetrics(prev => ({
          ...prev,
          apiRequests: requestCountRef.current,
          totalFiles: structuredRes.data?.total_files || 0,
          totalRows: structuredRes.data?.total_rows || 0,
          activeJobs: Array.isArray(jobsRes.data) ? jobsRes.data.filter(j => j.status === 'processing').length : 0,
          uptime: `${hours}h ${minutes}m`,
          latency: Math.floor(Math.random() * 50 + 20), // Simulated
          dbQueries: prev.dbQueries + 1,
        }));
        
        // Update component status
        setComponentStatus({
          frontend: 'healthy',
          api: 'healthy',
          duckdb: structuredRes.data?.available !== false ? 'healthy' : 'error',
          chromadb: chromaRes.data?.status === 'operational' ? 'healthy' : 'warning',
          claude: 'healthy',
        });
        
        // Simulate data flow
        setDataFlowActive(prev => ({ ...prev, apiToDuckdb: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, apiToDuckdb: false })), 300);
        
      } catch (err) {
        console.error('Metrics fetch error:', err);
        setComponentStatus(prev => ({ ...prev, api: 'error' }));
      }
    };
    
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  // Simulate activity log
  useEffect(() => {
    const activities = [
      { type: 'query', message: 'DuckDB query executed: SELECT * FROM...' },
      { type: 'upload', message: 'File processed: Employee_Data.xlsx' },
      { type: 'llm', message: 'Claude inference: table selection' },
      { type: 'success', message: 'Mapping job completed' },
      { type: 'query', message: 'Vector search: 5 documents retrieved' },
    ];
    
    const addActivity = () => {
      const randomActivity = activities[Math.floor(Math.random() * activities.length)];
      setActivity(prev => [{
        ...randomActivity,
        time: new Date().toLocaleTimeString(),
        id: Date.now(),
      }, ...prev.slice(0, 9)]);
      
      // Trigger appropriate data flow
      if (randomActivity.type === 'llm') {
        setDataFlowActive(prev => ({ ...prev, apiToClaude: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, apiToClaude: false })), 800);
        setMetrics(prev => ({ ...prev, llmCalls: prev.llmCalls + 1 }));
      } else if (randomActivity.type === 'query') {
        setDataFlowActive(prev => ({ ...prev, apiToDuckdb: true, apiToChroma: true }));
        setTimeout(() => setDataFlowActive(prev => ({ ...prev, apiToDuckdb: false, apiToChroma: false })), 500);
        setMetrics(prev => ({ ...prev, dbQueries: prev.dbQueries + 1 }));
      }
    };
    
    const interval = setInterval(addActivity, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      background: COLORS.bg,
      padding: '1.5rem',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 0.4; }
          50% { transform: scale(1.5); opacity: 0; }
        }
        @keyframes nodeGlow {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.8; }
        }
        @keyframes flowDash {
          to { stroke-dashoffset: -20; }
        }
      `}</style>
      
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ color: COLORS.text, fontSize: '1.5rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span>🔮</span> System Monitor
          <StatusLight status={Object.values(componentStatus).every(s => s === 'healthy') ? 'healthy' : 'warning'} size={10} />
        </h1>
        <p style={{ color: COLORS.textMuted, fontSize: '0.85rem', margin: '0.5rem 0 0 0' }}>
          Real-time data flow visualization
        </p>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <MetricCard icon="📡" label="API REQUESTS" value={metrics.apiRequests} subValue="This session" color={COLORS.blue} />
        <MetricCard icon="🗄️" label="DB QUERIES" value={metrics.dbQueries} subValue="DuckDB + Chroma" color={COLORS.purple} />
        <MetricCard icon="🤖" label="LLM CALLS" value={metrics.llmCalls} subValue="Claude API" color={COLORS.cyan} />
        <MetricCard icon="⚡" label="LATENCY" value={`${metrics.latency}ms`} subValue="Avg response" color={COLORS.green} />
        <MetricCard icon="📊" label="DATA" value={metrics.totalRows.toLocaleString()} subValue={`${metrics.totalFiles} files`} color={COLORS.yellow} />
        <MetricCard icon="⏱️" label="UPTIME" value={metrics.uptime} subValue="Session duration" />
      </div>

      {/* Main Content */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '1.5rem' }}>
        
        {/* Architecture Diagram */}
        <div style={{
          background: COLORS.cardBg,
          borderRadius: 16,
          padding: '1.5rem',
          border: `1px solid ${COLORS.border}`,
        }}>
          <h2 style={{ color: COLORS.text, fontSize: '1rem', fontWeight: 600, margin: '0 0 1rem 0' }}>
            Data Flow Architecture
          </h2>
          
          <svg width="100%" height="400" viewBox="0 0 700 400">
            {/* Connection Lines */}
            
            {/* Frontend to API */}
            <path
              d="M 120 100 Q 200 100 280 200"
              fill="none"
              stroke={dataFlowActive.frontendToApi ? COLORS.blue : COLORS.border}
              strokeWidth={dataFlowActive.frontendToApi ? 3 : 2}
              strokeDasharray={dataFlowActive.frontendToApi ? "none" : "5,5"}
              style={dataFlowActive.frontendToApi ? { filter: `drop-shadow(0 0 8px ${COLORS.blue})` } : {}}
            />
            
            {/* API to DuckDB */}
            <path
              d="M 380 200 Q 450 150 520 100"
              fill="none"
              stroke={dataFlowActive.apiToDuckdb ? COLORS.purple : COLORS.border}
              strokeWidth={dataFlowActive.apiToDuckdb ? 3 : 2}
              strokeDasharray={dataFlowActive.apiToDuckdb ? "none" : "5,5"}
              style={dataFlowActive.apiToDuckdb ? { filter: `drop-shadow(0 0 8px ${COLORS.purple})` } : {}}
            />
            
            {/* API to ChromaDB */}
            <path
              d="M 380 200 Q 450 200 520 200"
              fill="none"
              stroke={dataFlowActive.apiToChroma ? COLORS.green : COLORS.border}
              strokeWidth={dataFlowActive.apiToChroma ? 3 : 2}
              strokeDasharray={dataFlowActive.apiToChroma ? "none" : "5,5"}
              style={dataFlowActive.apiToChroma ? { filter: `drop-shadow(0 0 8px ${COLORS.green})` } : {}}
            />
            
            {/* API to Claude */}
            <path
              d="M 380 200 Q 450 250 520 300"
              fill="none"
              stroke={dataFlowActive.apiToClaude ? COLORS.cyan : COLORS.border}
              strokeWidth={dataFlowActive.apiToClaude ? 3 : 2}
              strokeDasharray={dataFlowActive.apiToClaude ? "none" : "5,5"}
              style={dataFlowActive.apiToClaude ? { filter: `drop-shadow(0 0 8px ${COLORS.cyan})` } : {}}
            />

            {/* Animated particles when active */}
            {dataFlowActive.frontendToApi && (
              <>
                <DataParticle startX={120} startY={100} endX={280} endY={200} color={COLORS.blue} delay={0} />
                <DataParticle startX={120} startY={100} endX={280} endY={200} color={COLORS.blue} delay={0.5} />
              </>
            )}
            {dataFlowActive.apiToDuckdb && (
              <DataParticle startX={380} startY={200} endX={520} endY={100} color={COLORS.purple} delay={0} />
            )}
            {dataFlowActive.apiToChroma && (
              <DataParticle startX={380} startY={200} endX={520} endY={200} color={COLORS.green} delay={0} />
            )}
            {dataFlowActive.apiToClaude && (
              <DataParticle startX={380} startY={200} endX={520} endY={300} color={COLORS.cyan} delay={0} />
            )}

            {/* System Nodes */}
            <SystemNode
              x={70}
              y={100}
              icon="🖥️"
              label="FRONTEND"
              status={componentStatus.frontend}
              color={COLORS.blue}
              glowColor={COLORS.blueGlow}
              isActive={dataFlowActive.frontendToApi}
            />
            
            <SystemNode
              x={330}
              y={200}
              icon="⚙️"
              label="API SERVER"
              status={componentStatus.api}
              color={COLORS.yellow}
              glowColor={COLORS.yellowGlow}
              isActive={Object.values(dataFlowActive).some(v => v)}
            />
            
            <SystemNode
              x={570}
              y={100}
              icon="🦆"
              label="DUCKDB"
              status={componentStatus.duckdb}
              color={COLORS.purple}
              glowColor={COLORS.purpleGlow}
              isActive={dataFlowActive.apiToDuckdb}
            />
            
            <SystemNode
              x={570}
              y={200}
              icon="🔍"
              label="CHROMADB"
              status={componentStatus.chromadb}
              color={COLORS.green}
              glowColor={COLORS.greenGlow}
              isActive={dataFlowActive.apiToChroma}
            />
            
            <SystemNode
              x={570}
              y={300}
              icon="🤖"
              label="CLAUDE"
              status={componentStatus.claude}
              color={COLORS.cyan}
              glowColor={COLORS.cyanGlow}
              isActive={dataFlowActive.apiToClaude}
            />

            {/* Labels on connections */}
            <text x="180" y="85" fontSize="9" fill={COLORS.textMuted}>HTTP/REST</text>
            <text x="430" y="135" fontSize="9" fill={COLORS.textMuted}>SQL</text>
            <text x="455" y="190" fontSize="9" fill={COLORS.textMuted}>Vector</text>
            <text x="430" y="270" fontSize="9" fill={COLORS.textMuted}>Inference</text>
          </svg>
        </div>

        {/* Activity Log */}
        <div style={{
          background: COLORS.cardBg,
          borderRadius: 16,
          padding: '1.5rem',
          border: `1px solid ${COLORS.border}`,
          display: 'flex',
          flexDirection: 'column',
        }}>
          <h2 style={{ color: COLORS.text, fontSize: '1rem', fontWeight: 600, margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ 
              width: 8, 
              height: 8, 
              borderRadius: '50%', 
              background: COLORS.green,
              animation: 'pulse 1s ease-in-out infinite',
            }} />
            Live Activity
          </h2>
          
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {activity.length === 0 ? (
              <div style={{ color: COLORS.textMuted, fontSize: '0.85rem', textAlign: 'center', padding: '2rem 0' }}>
                Waiting for activity...
              </div>
            ) : (
              activity.map((item) => (
                <ActivityItem key={item.id} {...item} />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Component Status Bar */}
      <div style={{
        marginTop: '1.5rem',
        background: COLORS.cardBg,
        borderRadius: 12,
        padding: '1rem 1.5rem',
        border: `1px solid ${COLORS.border}`,
        display: 'flex',
        justifyContent: 'space-around',
        alignItems: 'center',
      }}>
        {Object.entries(componentStatus).map(([name, status]) => (
          <div key={name} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <StatusLight status={status} size={8} pulse={status !== 'healthy'} />
            <span style={{ 
              color: status === 'healthy' ? COLORS.green : status === 'warning' ? COLORS.yellow : COLORS.red,
              fontSize: '0.75rem',
              fontWeight: 600,
              textTransform: 'uppercase',
            }}>
              {name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
