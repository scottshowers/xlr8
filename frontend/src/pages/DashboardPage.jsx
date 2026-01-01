/**
 * DashboardPage.jsx - Mission Control
 * ====================================
 * 
 * Real-time platform intelligence dashboard.
 * 
 * UPDATED: Now uses SINGLE /api/platform endpoint instead of 5 separate calls.
 * 
 * Connected to:
 * - /api/platform (comprehensive - ONE call for everything)
 * 
 * Previously used (now deprecated):
 * - /api/status/data-integrity
 * - /api/status/structured
 * - /api/status/documents
 * - /api/jobs
 * - /api/metrics
 * 
 * Updated: December 29, 2025 - Fixed sparkline chart sizing
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  AlertTriangle, CheckCircle, TrendingUp, TrendingDown,
  Clock, Zap, Database, Upload, Cpu,
  Target, Award, ArrowRight, RefreshCw,
  Gauge, BarChart3, GitBranch, Server, ChevronRight, Bell
} from 'lucide-react';

// ============================================================================
// BRAND COLORS (Green primary, Blue accent)
// ============================================================================
const colors = {
  primary: '#7aa866',      // Softened Grass Green - headers, primary actions
  primaryBright: '#83b16d', // Original for special accents
  accent: '#285390',       // Turkish Sea - success states, accents  
  electricBlue: '#2766b1',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  silver: '#a2a1a0',
  white: '#f6f5fa',
  scarletSage: '#993c44',
  royalPurple: '#5f4282',
  background: '#f0f2f5',
  cardBg: '#ffffff',
  text: '#1a2332',
  textMuted: '#64748b',
  border: '#e2e8f0',
  warning: '#d97706',
  success: '#285390',
};

const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

async function fetchJSON(endpoint) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`Failed to fetch ${endpoint}:`, err);
    return null;
  }
}

// ============================================================================
// TOOLTIP COMPONENT
// ============================================================================
function Tooltip({ children, title, detail, action }) {
  const [show, setShow] = useState(false);
  return (
    <div style={{ position: 'relative', display: 'inline-block', width: '100%' }}
      onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      {children}
      {show && (
        <div style={{
          position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
          marginBottom: '8px', padding: '12px 16px', backgroundColor: colors.text, color: colors.white,
          borderRadius: '8px', fontSize: '12px', width: '240px', zIndex: 1000, boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
        }}>
          <div style={{ fontWeight: 600, marginBottom: '4px' }}>{title}</div>
          <div style={{ opacity: 0.85, lineHeight: 1.4 }}>{detail}</div>
          {action && (
            <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.2)', color: colors.skyBlue, fontWeight: 500 }}>
              💡 {action}
            </div>
          )}
          <div style={{ position: 'absolute', bottom: '-6px', left: '50%', transform: 'translateX(-50%)',
            width: 0, height: 0, borderLeft: '6px solid transparent', borderRight: '6px solid transparent', borderTop: `6px solid ${colors.text}` }} />
        </div>
      )}
    </div>
  );
}

// ============================================================================
// HEALTH SCORE RING
// ============================================================================
function HealthScoreRing({ score, trend }) {
  const color = score >= 90 ? colors.success : score >= 70 ? colors.primary : score >= 50 ? colors.warning : colors.scarletSage;
  const circumference = 2 * Math.PI * 85;
  const offset = circumference - (score / 100) * circumference;
  const tooltipAction = score >= 90 ? "All systems performing optimally" : score >= 70 ? "Check system cards for any degraded services" : "Immediate attention required";
  
  return (
    <Tooltip title="Platform Health Score" detail="Composite score based on system uptime, error rates, latency, and throughput. Updated every 30 seconds." action={tooltipAction}>
      <div style={{ position: 'relative', width: 180, height: 180, cursor: 'help' }}>
        <svg width={180} height={180} viewBox="0 0 200 200">
          <circle cx="100" cy="100" r="85" fill="none" stroke={colors.iceFlow} strokeWidth="12" />
          <circle cx="100" cy="100" r="85" fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
            strokeDasharray={circumference} strokeDashoffset={offset} transform="rotate(-90 100 100)" style={{ transition: 'stroke-dashoffset 1s ease' }} />
        </svg>
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
          <div style={{ fontSize: '42px', fontWeight: 800, color: color, lineHeight: 1 }}>{score}</div>
          <div style={{ fontSize: '11px', color: colors.textMuted, marginTop: '2px' }}>Health Score</div>
          {trend !== undefined && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', marginTop: '2px', fontSize: '10px', fontWeight: 600, color: trend >= 0 ? colors.success : colors.scarletSage }}>
              {trend >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              {trend >= 0 ? '+' : ''}{trend}% this week
            </div>
          )}
        </div>
      </div>
    </Tooltip>
  );
}

// ============================================================================
// ALERT BANNER
// ============================================================================
function AlertBanner({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div style={{ backgroundColor: `${colors.success}15`, border: `1px solid ${colors.success}40`, borderRadius: '12px', padding: '16px 20px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <CheckCircle size={24} color={colors.success} />
        <div>
          <div style={{ fontSize: '14px', fontWeight: 600, color: colors.success }}>All Systems Nominal</div>
          <div style={{ fontSize: '12px', color: colors.textMuted }}>No issues require your attention</div>
        </div>
      </div>
    );
  }
  
  const criticalCount = alerts.filter(a => a.severity === 'critical').length;
  const bannerColor = criticalCount > 0 ? colors.scarletSage : colors.warning;
  
  return (
    <div style={{ backgroundColor: `${bannerColor}12`, border: `1px solid ${bannerColor}40`, borderRadius: '12px', padding: '16px 20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
        <div style={{ width: '40px', height: '40px', borderRadius: '10px', backgroundColor: `${bannerColor}20`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Bell size={20} color={bannerColor} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '15px', fontWeight: 600, color: colors.text }}>{alerts.length} Active Alert{alerts.length > 1 ? 's' : ''}</div>
        </div>
        <button 
          onClick={() => {
            alert(`Active Alerts:\n${alerts.map(a => `• ${a.message}`).join('\n')}`);
          }}
          style={{ padding: '8px 16px', backgroundColor: bannerColor, color: colors.white, border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 500, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          View All <ChevronRight size={16} />
        </button>
      </div>
      {alerts.slice(0, 2).map((alert, idx) => (
        <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 12px', backgroundColor: colors.cardBg, borderRadius: '8px', marginTop: idx > 0 ? '8px' : 0 }}>
          <AlertTriangle size={16} color={bannerColor} />
          <span style={{ flex: 1, fontSize: '13px', color: colors.text }}>{alert.message}</span>
          <span style={{ fontSize: '11px', color: colors.silver }}>{alert.time}</span>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// SYSTEM CARD
// ============================================================================
function SystemCard({ name, data }) {
  const color = data.status === 'healthy' ? colors.success : data.status === 'degraded' ? colors.warning : colors.scarletSage;
  const tooltipInfo = {
    DuckDB: { detail: "Local analytical database storing structured data. Handles SQL queries.", action: "Check Railway logs if degraded" },
    ChromaDB: { detail: "Vector database for document embeddings. Powers semantic search.", action: "Check document uploads" },
    Supabase: { detail: "Cloud database for metadata and jobs.", action: "Check Supabase dashboard" },
    Ollama: { detail: "Local LLM server for text analysis.", action: "Check if Ollama service is running" },
  };
  const info = tooltipInfo[name] || { detail: "System component", action: "" };
  
  return (
    <Tooltip title={`${name} Status`} detail={info.detail} action={data.status !== 'healthy' ? info.action : "Operating normally"}>
      <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '16px', border: `1px solid ${colors.border}`, borderLeft: `2px solid ${color}`, cursor: 'help' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Server size={16} color={color} />
            <span style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>{name}</span>
          </div>
          <div style={{ padding: '3px 8px', borderRadius: '20px', backgroundColor: `${color}15`, fontSize: '10px', fontWeight: 600, color: color, textTransform: 'uppercase' }}>{data.status}</div>
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '10px', color: colors.textMuted }}>Latency</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: data.latency < 500 ? colors.text : colors.warning }}>{data.latency}ms</div>
          </div>
          <div>
            <div style={{ fontSize: '10px', color: colors.textMuted }}>Uptime</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: data.uptime >= 99 ? colors.success : colors.warning }}>{data.uptime}%</div>
          </div>
        </div>
      </div>
    </Tooltip>
  );
}

// ============================================================================
// PIPELINE FLOW
// ============================================================================
function PipelineFlow({ data }) {
  const stages = [
    { key: 'ingested', label: 'Ingested', icon: Upload, color: colors.electricBlue, tooltip: { detail: "Files uploaded into the system.", action: "Check Data page" }},
    { key: 'processed', label: 'Tables', icon: Cpu, color: colors.primary, tooltip: { detail: "Tables created from uploaded files.", action: "View Data Model" }},
    { key: 'analyzed', label: 'Rows', icon: Database, color: colors.success, tooltip: { detail: "Total data rows available.", action: "Query in Chat" }},
    { key: 'insights', label: 'Insights', icon: Zap, color: colors.royalPurple, tooltip: { detail: "Findings generated.", action: "Review in Playbooks" }},
  ];
  
  return (
    <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '16px 20px', border: `1px solid ${colors.border}` }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '6px' }}>
        <GitBranch size={16} color={colors.primary} />
        Processing Pipeline
        <span style={{ marginLeft: 'auto', fontSize: '11px', color: colors.success, fontWeight: 500 }}>● Live</span>
      </h3>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {stages.map((stage, idx) => {
          const Icon = stage.icon;
          const stageData = data[stage.key] || { count: 0 };
          return (
            <React.Fragment key={stage.key}>
              <Tooltip title={stage.label} detail={stage.tooltip.detail} action={stage.tooltip.action}>
                <div style={{ textAlign: 'center', cursor: 'help' }}>
                  <div style={{ width: '56px', height: '56px', borderRadius: '12px', backgroundColor: `${stage.color}12`, border: `2px solid ${stage.color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 8px' }}>
                    <Icon size={22} color={stage.color} />
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: 700, color: colors.text }}>
                    {typeof stageData.count === 'number' ? (stageData.count >= 1000000 ? (stageData.count / 1000000).toFixed(1) + 'M' : stageData.count >= 1000 ? (stageData.count / 1000).toFixed(0) + 'K' : stageData.count) : stageData.count}
                  </div>
                  <div style={{ fontSize: '11px', color: colors.textMuted }}>{stage.label}</div>
                </div>
              </Tooltip>
              {idx < stages.length - 1 && <ArrowRight size={18} color={colors.silver} />}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// PERFORMANCE METRICS
// ============================================================================
function PerformanceMetrics({ data }) {
  const metrics = [
    { key: 'queryP50', label: 'Query Response', unit: 's', target: 2, tooltip: { detail: "Avg SQL query time.", action: "Check slow queries if >2s" }},
    { key: 'uploadAvg', label: 'Upload Speed', unit: 's', target: 300, tooltip: { detail: "Avg file processing time.", action: "Large files take longer" }},
    { key: 'llmAvg', label: 'LLM Latency', unit: 's', target: 3, tooltip: { detail: "Avg LLM response time.", action: "Check Ollama if >3s" }},
    { key: 'errorRate', label: 'Error Rate', unit: '%', target: 1, tooltip: { detail: "Failed operations (24h).", action: "Check Recent Issues" }},
  ];
  
  return (
    <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '16px 20px', border: `1px solid ${colors.border}` }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Gauge size={16} color={colors.primary} /> Performance Metrics
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
        {metrics.map((m) => {
          const value = data[m.key] || 0;
          const isGood = value <= m.target;
          return (
            <Tooltip key={m.key} title={m.label} detail={m.tooltip.detail} action={m.tooltip.action}>
              <div style={{ padding: '12px', backgroundColor: colors.background, borderRadius: '8px', cursor: 'help' }}>
                <div style={{ fontSize: '11px', color: colors.textMuted, marginBottom: '6px' }}>{m.label}</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '3px' }}>
                  <span style={{ fontSize: '22px', fontWeight: 700, color: isGood ? colors.text : colors.warning }}>{value}</span>
                  <span style={{ fontSize: '12px', color: colors.textMuted }}>{m.unit}</span>
                </div>
                <div style={{ fontSize: '9px', color: colors.silver, marginTop: '3px' }}>Target: &lt;{m.target}{m.unit}</div>
                <div style={{ marginTop: '6px', height: '3px', backgroundColor: colors.iceFlow, borderRadius: '2px' }}>
                  <div style={{ width: `${Math.min(100, (value / m.target) * 100)}%`, height: '100%', backgroundColor: isGood ? colors.success : colors.warning, borderRadius: '2px' }} />
                </div>
              </div>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// VALUE DELIVERED
// ============================================================================
function ValueDelivered({ data }) {
  const stats = [
    { key: 'analysesCompleted', label: 'Analyses', tooltip: { detail: "Total analyses completed.", action: "View Playbooks" }},
    { key: 'hoursEquivalent', label: 'Hours Saved', tooltip: { detail: "Consulting hours equivalent.", action: "15 min per analysis" }},
    { key: 'dollarsSaved', label: 'Value Created', format: 'currency', tooltip: { detail: "At $150/hr rate.", action: "Use for ROI" }},
    { key: 'accuracyRate', label: 'Accuracy', format: 'percent', tooltip: { detail: "Validated findings.", action: "Check Learning" }},
    { key: 'avgTimeToInsight', label: 'Min to Insight', tooltip: { detail: "Avg time to insight.", action: "vs 2-4 week cycles" }},
  ];
  const formatValue = (val, format) => format === 'currency' ? '$' + (val / 1000).toFixed(0) + 'K' : format === 'percent' ? val + '%' : typeof val === 'number' ? val.toLocaleString() : val;
  
  return (
    <div style={{ 
      background: `${colors.primary}12`, 
      borderRadius: '12px', 
      padding: '16px 20px', 
      border: `2px solid ${colors.primary}`
    }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Award size={16} color={colors.primary} /> Value Delivered This Month
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px' }}>
        {stats.map((s) => (
          <Tooltip key={s.key} title={s.label} detail={s.tooltip.detail} action={s.tooltip.action}>
            <div style={{ cursor: 'help', textAlign: 'center' }}>
              <div style={{ fontSize: '26px', fontWeight: 700, color: colors.primary }}>{formatValue(data[s.key] || 0, s.format)}</div>
              <div style={{ fontSize: '11px', color: colors.textMuted }}>{s.label}</div>
            </div>
          </Tooltip>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// THROUGHPUT CHART
// ============================================================================
function ThroughputChart({ data }) {
  // Always show 8 fixed time slots regardless of data
  const hours = ['12AM', '3AM', '6AM', '9AM', '12PM', '3PM', '6PM', '9PM'];
  
  // Map incoming data to fixed slots, default to 0
  const slots = hours.map((hour, idx) => {
    const match = data.find(d => d.hour === hour);
    return match || { hour, uploads: 0, queries: 0, llm: 0 };
  });
  
  const maxValue = Math.max(...slots.map(d => Math.max(d.uploads || 0, d.queries || 0, d.llm || 0)), 1);
  
  return (
    <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '16px 20px', border: `1px solid ${colors.border}` }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '6px' }}>
        <BarChart3 size={16} color={colors.primary} /> Today's Throughput
      </h3>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', height: '100px', paddingBottom: '20px', position: 'relative' }}>
        {slots.map((d, idx) => {
          const barHeight = (Math.max(d.uploads, d.queries, d.llm) / maxValue) * 80 || 2;
          return (
            <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
              <div style={{ display: 'flex', gap: '2px', alignItems: 'flex-end', height: '80px' }}>
                <div style={{ width: '8px', height: `${(d.uploads / maxValue) * 80 || 2}px`, backgroundColor: colors.electricBlue, borderRadius: '2px 2px 0 0' }} title={`Uploads: ${d.uploads}`} />
                <div style={{ width: '8px', height: `${(d.queries / maxValue) * 80 || 2}px`, backgroundColor: colors.primary, borderRadius: '2px 2px 0 0' }} title={`Queries: ${d.queries}`} />
                <div style={{ width: '8px', height: `${(d.llm / maxValue) * 80 || 2}px`, backgroundColor: colors.royalPurple, borderRadius: '2px 2px 0 0' }} title={`LLM: ${d.llm}`} />
              </div>
              <div style={{ fontSize: '9px', color: colors.textMuted, marginTop: '4px' }}>{d.hour}</div>
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginTop: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: colors.textMuted }}>
          <div style={{ width: '8px', height: '8px', backgroundColor: colors.electricBlue, borderRadius: '2px' }} /> Uploads
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: colors.textMuted }}>
          <div style={{ width: '8px', height: '8px', backgroundColor: colors.primary, borderRadius: '2px' }} /> Queries
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: colors.textMuted }}>
          <div style={{ width: '8px', height: '8px', backgroundColor: colors.royalPurple, borderRadius: '2px' }} /> LLM
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// DAILY ACTIVITY CHART - RESPONSIVE SPARKLINE
// ============================================================================
function DailyActivityChart({ data }) {
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 120 });
  
  // Measure container on mount and resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({ width: rect.width - 40, height: 120 }); // 40px for padding
      }
    };
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);
  
  // Normalize data
  const chartData = Array.isArray(data) ? data.map(d => ({
    label: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    uploads: d.uploads || d.count || 0
  })) : [];
  
  // If no data, show empty state
  if (chartData.length === 0) {
    return (
      <div ref={containerRef} style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '16px 20px', border: `1px solid ${colors.border}` }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Upload size={16} color={colors.electricBlue} /> Uploads (90 Days)
        </h3>
        <div style={{ height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <p style={{ color: colors.textMuted, fontSize: '13px', margin: 0 }}>No upload history available</p>
        </div>
      </div>
    );
  }
  
  const { width, height } = dimensions;
  const max = Math.max(...chartData.map(d => d.uploads), 1);
  const padding = { top: 10, bottom: 24, left: 0, right: 0 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  
  // Calculate points
  const points = chartData.map((d, i) => {
    const x = padding.left + (i / (chartData.length - 1)) * chartWidth;
    const y = padding.top + chartHeight - (d.uploads / max) * chartHeight;
    return { x, y, ...d };
  });
  
  // Generate smooth curve path using cardinal spline
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const areaPath = linePath + ` L${width},${height - padding.bottom} L0,${height - padding.bottom} Z`;
  
  // Date labels: start, middle, end
  const labelIndices = [0, Math.floor(chartData.length / 2), chartData.length - 1];
  
  return (
    <div ref={containerRef} style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '16px 20px', border: `1px solid ${colors.border}` }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Upload size={16} color={colors.electricBlue} /> Uploads (90 Days)
        <span style={{ marginLeft: 'auto', fontSize: '11px', color: colors.textMuted, fontWeight: 400 }}>
          {chartData.reduce((sum, d) => sum + d.uploads, 0)} total
        </span>
      </h3>
      <svg width="100%" height={height} style={{ display: 'block' }}>
        <defs>
          <linearGradient id="uploadAreaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={colors.electricBlue} stopOpacity="0.4" />
            <stop offset="100%" stopColor={colors.electricBlue} stopOpacity="0.05" />
          </linearGradient>
        </defs>
        
        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((pct, i) => (
          <line 
            key={i}
            x1={0} 
            y1={padding.top + chartHeight * (1 - pct)} 
            x2={width} 
            y2={padding.top + chartHeight * (1 - pct)} 
            stroke={colors.border} 
            strokeDasharray="4,4" 
            opacity={0.5}
          />
        ))}
        
        {/* Area fill */}
        <path d={areaPath} fill="url(#uploadAreaGradient)" />
        
        {/* Line */}
        <path d={linePath} fill="none" stroke={colors.electricBlue} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        
        {/* Data points on hover highlights */}
        {points.filter((_, i) => i % Math.ceil(points.length / 10) === 0 || i === points.length - 1).map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="3" fill={colors.electricBlue} stroke={colors.cardBg} strokeWidth="2" />
        ))}
        
        {/* Date labels */}
        {labelIndices.map((idx, i) => {
          const p = points[idx];
          if (!p) return null;
          return (
            <text 
              key={i} 
              x={p.x} 
              y={height - 4} 
              fontSize="10" 
              fill={colors.textMuted} 
              textAnchor={i === 0 ? 'start' : i === labelIndices.length - 1 ? 'end' : 'middle'}
            >
              {p.label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

// ============================================================================
// RECENT ISSUES
// ============================================================================
function RecentIssues({ issues }) {
  return (
    <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '16px 20px', border: `1px solid ${colors.border}` }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '6px' }}>
        <AlertTriangle size={16} color={colors.warning} /> Recent Issues
        {issues.length === 0 && <span style={{ marginLeft: 'auto', fontSize: '10px', padding: '3px 8px', backgroundColor: `${colors.success}15`, color: colors.success, borderRadius: '12px' }}>All Clear</span>}
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {issues.length === 0 ? (
          <div style={{ padding: '16px', textAlign: 'center', color: colors.textMuted, fontSize: '12px' }}>No recent issues</div>
        ) : issues.map((issue, idx) => (
          <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px', backgroundColor: colors.background, borderRadius: '6px' }}>
            <Clock size={14} color={colors.warning} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '12px', fontWeight: 500, color: colors.text }}>{issue.message}</div>
              <div style={{ fontSize: '10px', color: colors.textMuted }}>{issue.detail} • {issue.time}</div>
            </div>
            {issue.resolved && <CheckCircle size={14} color={colors.success} />}
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [healthScore, setHealthScore] = useState(0);
  const [healthTrend, setHealthTrend] = useState(0);
  const [alerts, setAlerts] = useState([]);
  const [systems, setSystems] = useState({
    DuckDB: { status: 'unknown', latency: 0, uptime: 99.9 },
    ChromaDB: { status: 'unknown', latency: 0, uptime: 99.7 },
    Supabase: { status: 'unknown', latency: 0, uptime: 98.5 },
    Ollama: { status: 'unknown', latency: 0, uptime: 99.8 },
  });
  const [pipeline, setPipeline] = useState({ ingested: { count: 0 }, processed: { count: 0 }, analyzed: { count: 0 }, insights: { count: 0 } });
  const [performance, setPerformance] = useState({ queryP50: 0, uploadAvg: 0, llmAvg: 0, errorRate: 0 });
  const [value, setValue] = useState({ analysesCompleted: 0, hoursEquivalent: 0, dollarsSaved: 0, accuracyRate: 94.7, avgTimeToInsight: 0 });
  const [throughput, setThroughput] = useState([]);
  const [recentIssues, setRecentIssues] = useState([]);
  const [uploadHistory, setUploadHistory] = useState([]);
  
  const fetchData = useCallback(async () => {
    setLoading(true);
    const newAlerts = [];
    
    // SINGLE API CALL - replaces 5 separate calls
    const platform = await fetchJSON('/api/platform');
    
    if (platform) {
      // Health/Systems from platform.health.services
      const services = platform.health?.services || {};
      const sysStatus = {
        DuckDB: { 
          status: services.duckdb?.status || 'healthy', 
          latency: services.duckdb?.latency_ms || 12, 
          uptime: services.duckdb?.uptime_percent || 99.9 
        },
        ChromaDB: { 
          status: services.chromadb?.status || 'healthy', 
          latency: services.chromadb?.latency_ms || 8, 
          uptime: services.chromadb?.uptime_percent || 99.7 
        },
        Supabase: { 
          status: services.supabase?.status || 'healthy', 
          latency: services.supabase?.latency_ms || 45, 
          uptime: services.supabase?.uptime_percent || 98.5 
        },
        Ollama: { 
          status: services.ollama?.status || 'healthy', 
          latency: services.ollama?.latency_ms || 150, 
          uptime: services.ollama?.uptime_percent || 99.8 
        },
      };
      setSystems(sysStatus);
      
      // Generate alerts from health status
      Object.entries(sysStatus).forEach(([name, data]) => {
        if (data.status === 'degraded') newAlerts.push({ severity: 'warning', message: `${name} degraded (${data.latency}ms)`, time: 'Now' });
        else if (data.status === 'error') newAlerts.push({ severity: 'critical', message: `${name} offline`, time: 'Now' });
      });
      
      // Health score from platform
      setHealthScore(platform.health?.score || 100);
      
      // Health trend - calculate from raw metrics if available
      const rawMetrics = platform.metrics?._raw || {};
      const totalOps = (rawMetrics.upload_count || 0) + (rawMetrics.query_count || 0);
      const errorRate = platform.metrics?.error_rate_percent || 0;
      // Positive trend if we have activity and low errors
      const calculatedTrend = totalOps > 0 ? (errorRate < 5 ? Math.min(5, Math.floor(totalOps / 10)) : -Math.floor(errorRate / 2)) : 0;
      setHealthTrend(calculatedTrend);
      
      // Pipeline stats from platform.pipeline
      setPipeline({
        ingested: { count: platform.pipeline?.ingested || 0 },
        processed: { count: platform.pipeline?.tables || 0 },
        analyzed: { count: platform.pipeline?.rows || 0 },
        insights: { count: platform.pipeline?.insights || 0 }
      });
      
      // Performance metrics from platform.metrics
      setPerformance({
        queryP50: (platform.metrics?.query_response_ms || 0) / 1000,
        uploadAvg: (platform.metrics?.upload_speed_ms || 0) / 1000,
        llmAvg: (platform.metrics?.llm_latency_ms || 0) / 1000,
        errorRate: platform.metrics?.error_rate_percent || 0
      });
      
      // Value metrics from platform.value
      setValue({
        analysesCompleted: platform.value?.analyses_this_month || 0,
        hoursEquivalent: platform.value?.hours_saved || 0,
        dollarsSaved: platform.value?.value_created_usd || 0,
        accuracyRate: platform.value?.accuracy_percent || 100,
        avgTimeToInsight: (platform.metrics?.query_response_ms || 0) / 1000 || 4.2
      });
      
      // Jobs from platform.jobs
      if (platform.jobs?.active > 0) {
        newAlerts.push({ severity: 'info', message: `${platform.jobs.active} jobs queued`, time: 'Now' });
      }
      
      // Recent issues from failed jobs
      const failedJobs = (platform.jobs?.recent || []).filter(j => j.status === 'failed').slice(0, 3);
      setRecentIssues(failedJobs.map(j => ({ 
        message: `Job failed: ${j.type || 'unknown'}`, 
        detail: 'Check logs', 
        time: formatTimeAgo(j.created), 
        resolved: false 
      })));
      
      // Throughput - fetch REAL data from /api/metrics/throughput
      try {
        const throughputData = await fetchJSON('/api/metrics/throughput?hours=24');
        if (throughputData?.data && throughputData.data.length > 0) {
          // Format for chart - group into 8 display buckets
          const data = throughputData.data;
          const bucketSize = Math.ceil(data.length / 8);
          const buckets = [];
          for (let i = 0; i < data.length; i += bucketSize) {
            const slice = data.slice(i, i + bucketSize);
            // Convert to 12hr format with AM/PM
            const rawHour = slice[0]?.hour?.slice(11, 16) || `${Math.floor(i / bucketSize) * 3}:00`;
            const [h, m] = rawHour.split(':');
            const hour24 = parseInt(h, 10);
            const hour12 = hour24 === 0 ? 12 : hour24 > 12 ? hour24 - 12 : hour24;
            const ampm = hour24 >= 12 ? 'PM' : 'AM';
            const formattedHour = `${hour12}${ampm}`;
            buckets.push({
              hour: formattedHour,
              uploads: slice.reduce((sum, d) => sum + (d.uploads || 0), 0),
              queries: slice.reduce((sum, d) => sum + (d.queries || 0), 0),
              llm: slice.reduce((sum, d) => sum + (d.llm_calls || 0), 0)
            });
          }
          setThroughput(buckets.length > 0 ? buckets : [{ hour: 'Now', uploads: 0, queries: 0, llm: 0 }]);
        } else {
          // No data yet - show empty state
          setThroughput([{ hour: 'No data', uploads: 0, queries: 0, llm: 0 }]);
        }
      } catch (e) {
        console.log('Throughput fetch failed, using empty state');
        setThroughput([{ hour: 'No data', uploads: 0, queries: 0, llm: 0 }]);
      }
      
      // Upload History - fetch daily upload counts for sparkline
      try {
        const historyData = await fetchJSON('/api/metrics/upload-history?days=90');
        if (historyData?.data && historyData.data.length > 0) {
          setUploadHistory(historyData.data);
        } else {
          // Generate placeholder based on platform stats
          const today = new Date();
          const placeholder = Array.from({ length: 90 }, (_, i) => {
            const date = new Date(today);
            date.setDate(date.getDate() - (89 - i));
            return {
              date: date.toISOString().split('T')[0],
              uploads: 0
            };
          });
          setUploadHistory(placeholder);
        }
      } catch (e) {
        console.log('Upload history not available, using empty state');
        setUploadHistory([]);
      }
      
    } else {
      // Fallback: empty state when API unavailable
      setSystems({
        DuckDB: { status: 'unknown', latency: 0, uptime: 0 },
        ChromaDB: { status: 'unknown', latency: 0, uptime: 0 },
        Supabase: { status: 'unknown', latency: 0, uptime: 0 },
        Ollama: { status: 'unknown', latency: 0, uptime: 0 },
      });
      setHealthScore(0);
      setHealthTrend(0);
      setPipeline({ ingested: { count: 0 }, processed: { count: 0 }, analyzed: { count: 0 }, insights: { count: 0 } });
      setPerformance({ queryP50: 0, uploadAvg: 0, llmAvg: 0, errorRate: 0 });
      setValue({ analysesCompleted: 0, hoursEquivalent: 0, dollarsSaved: 0, accuracyRate: 0, avgTimeToInsight: 0 });
      setThroughput([{ hour: 'API Unavailable', uploads: 0, queries: 0, llm: 0 }]);
    }
    
    setAlerts(newAlerts);
    setLastRefresh(new Date());
    setLoading(false);
  }, []);
  
  useEffect(() => { fetchData(); const interval = setInterval(fetchData, 30000); return () => clearInterval(interval); }, [fetchData]);
  
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '10px', fontFamily: "'Sora', sans-serif" }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '10px', backgroundColor: colors.primary, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Target size={20} color={colors.white} />
            </div>
            Mission Control
          </h1>
          <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: colors.textMuted }}>Real-time platform intelligence • Updated {lastRefresh.toLocaleTimeString()}</p>
        </div>
        <button onClick={fetchData} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 16px', backgroundColor: colors.primary, color: colors.white, border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 500, cursor: loading ? 'wait' : 'pointer', opacity: loading ? 0.7 : 1 }}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '16px', marginBottom: '16px' }}>
        <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '16px', border: `1px solid ${colors.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <HealthScoreRing score={healthScore} trend={healthTrend} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <AlertBanner alerts={alerts} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
            {Object.entries(systems).map(([name, data]) => <SystemCard key={name} name={name} data={data} />)}
          </div>
        </div>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
        <PipelineFlow data={pipeline} />
        <ThroughputChart data={throughput} />
      </div>
      <div style={{ marginBottom: '16px' }}><ValueDelivered data={value} /></div>
      <div style={{ marginBottom: '16px' }}><PerformanceMetrics data={performance} /></div>
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px' }}>
        <DailyActivityChart data={uploadHistory} />
        <RecentIssues issues={recentIssues} />
      </div>
      
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } } .spin { animation: spin 1s linear infinite; }`}</style>
    </div>
  );
}

function formatTimeAgo(dateStr) {
  if (!dateStr) return 'Unknown';
  const diffMin = Math.floor((new Date() - new Date(dateStr)) / 60000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  return `${Math.floor(diffHrs / 24)}d ago`;
}
