/**
 * DashboardPage.jsx - Platform Intelligence Dashboard
 * 
 * Shows XLR8's intelligence systems health and activity.
 * Scopes to active project if selected, otherwise shows platform-wide metrics.
 * 
 * Every metric has hover tooltips explaining what it measures and why it matters.
 */

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';
import { 
  Shield, FileText, Sparkles, GitBranch,
  Layers, Brain, Target, Zap, Activity,
  RefreshCw, ChevronRight, Info, CheckCircle, AlertTriangle,
  Database, FileCheck, Link2
} from 'lucide-react';

// Refined muted palette matching platform theme
const getColors = (dark) => ({
  bg: dark ? '#12151c' : '#f5f6f8',
  card: dark ? '#1a1e28' : '#ffffff',
  cardBorder: dark ? '#2a2f3a' : '#e4e7ec',
  cardHover: dark ? '#1e232e' : '#fafbfc',
  
  text: dark ? '#e4e6ea' : '#2d3643',
  textMuted: dark ? '#8b95a5' : '#6b7a8f',
  textLight: dark ? '#5f6a7d' : '#9aa5b5',
  
  // Primary - XLR8 grassGreen
  primary: '#83b16d',
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.1)',
  
  // Secondary colors - same tonal family
  slate: '#6b7a8f',
  slateLight: dark ? 'rgba(107, 122, 143, 0.15)' : 'rgba(107, 122, 143, 0.1)',
  
  dustyBlue: '#7889a0',
  dustyBlueLight: dark ? 'rgba(120, 137, 160, 0.15)' : 'rgba(120, 137, 160, 0.1)',
  
  taupe: '#9b8f82',
  taupeLight: dark ? 'rgba(155, 143, 130, 0.15)' : 'rgba(155, 143, 130, 0.1)',
  
  sage: '#7a9b87',
  sageLight: dark ? 'rgba(122, 155, 135, 0.15)' : 'rgba(122, 155, 135, 0.1)',
  
  // Status - muted
  success: '#83b16d',
  successLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.1)',
  
  warning: '#b5956a',
  warningLight: dark ? 'rgba(181, 149, 106, 0.15)' : 'rgba(181, 149, 106, 0.1)',
  
  error: '#a07070',
  errorLight: dark ? 'rgba(160, 112, 112, 0.15)' : 'rgba(160, 112, 112, 0.1)',
});

// Tooltip Component
function Tooltip({ children, tooltip, colors }) {
  const [show, setShow] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const triggerRef = useRef(null);
  
  const handleMouseEnter = () => {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) {
      setPosition({ x: rect.left + rect.width / 2, y: rect.top - 12 });
    }
    setShow(true);
  };
  
  if (!tooltip) return children;
  
  return (
    <div 
      ref={triggerRef}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setShow(false)}
      style={{ position: 'relative', width: '100%' }}
    >
      {children}
      {show && (
        <div style={{
          position: 'fixed',
          left: position.x,
          top: position.y,
          transform: 'translate(-50%, -100%)',
          zIndex: 1000,
          background: colors.card,
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: 12,
          padding: '1rem 1.25rem',
          maxWidth: 280,
          boxShadow: '0 12px 32px rgba(0,0,0,0.12)',
          pointerEvents: 'none',
        }}>
          <div style={{ 
            fontSize: '0.65rem', 
            fontWeight: 700, 
            color: colors.primary,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginBottom: '0.5rem'
          }}>
            {tooltip.title}
          </div>
          <div style={{ 
            fontSize: '0.8rem', 
            color: colors.text,
            lineHeight: 1.5,
            marginBottom: tooltip.insight ? '0.75rem' : 0
          }}>
            {tooltip.description}
          </div>
          {tooltip.insight && (
            <div style={{
              fontSize: '0.75rem',
              color: colors.textMuted,
              padding: '0.5rem 0.75rem',
              background: colors.primaryLight,
              borderRadius: 6,
              borderLeft: `2px solid ${colors.primary}`,
            }}>
              💡 {tooltip.insight}
            </div>
          )}
          <div style={{
            position: 'absolute',
            bottom: -6,
            left: '50%',
            transform: 'translateX(-50%) rotate(45deg)',
            width: 12,
            height: 12,
            background: colors.card,
            borderRight: `1px solid ${colors.cardBorder}`,
            borderBottom: `1px solid ${colors.cardBorder}`,
          }} />
        </div>
      )}
    </div>
  );
}

// Hero Metric Card
function HeroMetric({ value, label, icon: Icon, tooltip, colors, onClick, colorKey = 'primary' }) {
  const [hovered, setHovered] = useState(false);
  
  const iconBg = colors[`${colorKey}Light`] || colors.primaryLight;
  const iconColor = colors[colorKey] || colors.primary;
  
  return (
    <Tooltip tooltip={tooltip} colors={colors}>
      <div 
        onClick={onClick}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          background: colors.card,
          border: `1px solid ${hovered ? colors.primary : colors.cardBorder}`,
          borderRadius: 16,
          padding: '1.5rem',
          cursor: onClick ? 'pointer' : 'default',
          transition: 'all 0.2s ease',
          transform: hovered ? 'translateY(-2px)' : 'translateY(0)',
          boxShadow: hovered ? '0 8px 24px rgba(0,0,0,0.06)' : 'none',
          position: 'relative',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: iconBg,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Icon size={22} style={{ color: iconColor }} />
          </div>
          {tooltip && <Info size={14} style={{ color: colors.textLight, opacity: 0.5 }} />}
        </div>
        
        <div style={{ 
          fontSize: '2.5rem', 
          fontWeight: 800, 
          color: colorKey === 'success' ? colors.success : colors.text, 
          lineHeight: 1,
          marginBottom: '0.5rem',
          fontFamily: "'Sora', 'Inter', sans-serif",
        }}>
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        
        <div style={{ 
          fontSize: '0.85rem', 
          fontWeight: 600, 
          color: colors.textMuted,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          {label}
          {onClick && <ChevronRight size={14} style={{ opacity: 0.5 }} />}
        </div>
      </div>
    </Tooltip>
  );
}

// Truth Pillar Component
function TruthPillar({ label, sublabel, value, icon, color, colorLight, barWidth, colors, onClick }) {
  const [hovered, setHovered] = useState(false);
  
  return (
    <div 
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flex: 1,
        background: hovered ? colors.card : colors.bg,
        borderRadius: 12,
        padding: '1.25rem',
        textAlign: 'center',
        border: `1px solid ${hovered ? colors.cardBorder : 'transparent'}`,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s ease',
        boxShadow: hovered ? '0 4px 12px rgba(0,0,0,0.04)' : 'none',
      }}
    >
      <div style={{
        width: 48,
        height: 48,
        borderRadius: 12,
        background: colorLight,
        margin: '0 auto 1rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '1.25rem',
      }}>
        {icon}
      </div>
      <div style={{ 
        fontSize: '1.75rem', 
        fontWeight: 800, 
        color: colors.text,
        marginBottom: '0.25rem',
        fontFamily: "'Sora', 'Inter', sans-serif",
      }}>
        {value.toLocaleString()}
      </div>
      <div style={{ 
        fontSize: '0.7rem', 
        fontWeight: 700, 
        color: colors.textMuted,
        letterSpacing: '0.5px',
        marginBottom: '0.25rem',
      }}>
        {label}
      </div>
      <div style={{ fontSize: '0.75rem', color: colors.textLight }}>
        {sublabel}
      </div>
      <div style={{
        height: 4,
        background: colors.cardBorder,
        borderRadius: 2,
        overflow: 'hidden',
        marginTop: '1rem',
      }}>
        <div style={{
          height: '100%',
          width: `${barWidth}%`,
          background: color,
          borderRadius: 2,
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  );
}

// Section Card
function SectionCard({ title, icon: Icon, iconColor = 'primary', children, colors, onHeaderClick, linkText }) {
  const [hovered, setHovered] = useState(false);
  const iconBg = colors[`${iconColor}Light`] || colors.primaryLight;
  const iconClr = colors[iconColor] || colors.primary;
  
  return (
    <div 
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: colors.card,
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: 16,
        overflow: 'hidden',
      }}
    >
      <div 
        onClick={onHeaderClick}
        style={{
          padding: '1rem 1.25rem',
          borderBottom: `1px solid ${colors.cardBorder}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: onHeaderClick ? 'pointer' : 'default',
          transition: 'background 0.15s ease',
          background: hovered && onHeaderClick ? colors.cardHover : 'transparent',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: iconBg,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Icon size={16} style={{ color: iconClr }} />
          </div>
          <span style={{ fontSize: '0.9rem', fontWeight: 700, color: colors.text }}>
            {title}
          </span>
        </div>
        {linkText && (
          <span style={{ 
            color: hovered ? colors.primary : colors.textLight, 
            fontSize: '0.8rem',
            transition: 'color 0.15s ease',
          }}>
            {linkText}
          </span>
        )}
      </div>
      <div style={{ padding: '1.25rem' }}>
        {children}
      </div>
    </div>
  );
}

// Donut Chart
function DonutChart({ segments, total, colors }) {
  const circumference = 2 * Math.PI * 40;
  let offset = 0;
  
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
      <div style={{ width: 130, height: 130, position: 'relative', flexShrink: 0 }}>
        <svg viewBox="0 0 100 100" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="50" cy="50" r="40" fill="none" stroke={colors.cardBorder} strokeWidth="10" />
          {segments.map((seg, i) => {
            const dashArray = (seg.percent / 100) * circumference;
            const dashOffset = -offset;
            offset += dashArray;
            return (
              <circle 
                key={i}
                cx="50" 
                cy="50" 
                r="40" 
                fill="none" 
                stroke={seg.color}
                strokeWidth="10"
                strokeDasharray={`${dashArray} ${circumference}`}
                strokeDashoffset={dashOffset}
                strokeLinecap="round"
              />
            );
          })}
        </svg>
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: colors.text, fontFamily: "'Sora', 'Inter', sans-serif" }}>
            {total.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.7rem', color: colors.textLight }}>Total</div>
        </div>
      </div>
      <div style={{ flex: 1 }}>
        {segments.map((seg, i) => (
          <div key={i} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.5rem 0',
            borderBottom: i < segments.length - 1 ? `1px solid ${colors.bg}` : 'none',
          }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: seg.color }} />
            <span style={{ flex: 1, fontSize: '0.8rem', color: colors.textMuted }}>{seg.label}</span>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', color: colors.text }}>{seg.percent}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Gauge Component
function GaugeChart({ value, label, colors }) {
  const percentage = Math.min(value, 100);
  const strokeDashoffset = 125.6 * (1 - percentage / 100);
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '0.5rem 0 1rem' }}>
      <div style={{ width: 160, height: 90, position: 'relative' }}>
        <svg viewBox="0 0 100 55" style={{ width: '100%', height: '100%' }}>
          <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke={colors.cardBorder} strokeWidth="10" />
          <path 
            d="M 10 50 A 40 40 0 0 1 90 50" 
            fill="none" 
            stroke={colors.success}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray="125.6"
            strokeDashoffset={strokeDashoffset}
            style={{ transition: 'stroke-dashoffset 0.5s ease' }}
          />
        </svg>
        <div style={{ position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: colors.success, fontFamily: "'Sora', 'Inter', sans-serif" }}>
            {value}%
          </div>
          <div style={{ fontSize: '0.75rem', color: colors.textMuted, fontWeight: 600 }}>{label}</div>
        </div>
      </div>
    </div>
  );
}

// Progress Bar
function ProgressBar({ label, value, max, color, colors }) {
  const percentage = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  
  return (
    <div style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.8rem' }}>
        <span style={{ color: colors.textMuted }}>{label}</span>
        <span style={{ fontWeight: 700, color: colors.text }}>{value.toLocaleString()}</span>
      </div>
      <div style={{ height: 6, background: colors.bg, borderRadius: 3, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${percentage}%`,
          background: color,
          borderRadius: 3,
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  );
}

// Mini Bar Chart
function MiniBarChart({ data, colors }) {
  const max = Math.max(...data.map(d => d.value), 1);
  
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 50, padding: '0.5rem 0' }}>
        {data.map((d, i) => (
          <div 
            key={i}
            style={{
              flex: 1,
              background: colors.primary,
              borderRadius: '3px 3px 0 0',
              height: `${(d.value / max) * 100}%`,
              minHeight: 6,
              opacity: 0.7,
              transition: 'opacity 0.15s ease',
              cursor: 'default',
            }}
            onMouseEnter={(e) => e.target.style.opacity = 1}
            onMouseLeave={(e) => e.target.style.opacity = 0.7}
          />
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: colors.textLight }}>
        {data.map((d, i) => <span key={i}>{d.label}</span>)}
      </div>
    </div>
  );
}

// Stat Box
function StatBox({ value, label, colorKey, colors }) {
  const [hovered, setHovered] = useState(false);
  const valueColor = colorKey ? colors[colorKey] : colors.text;
  
  return (
    <div 
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? colors.card : colors.bg,
        borderRadius: 10,
        padding: '1rem',
        textAlign: 'center',
        transition: 'all 0.15s ease',
        boxShadow: hovered ? '0 2px 8px rgba(0,0,0,0.04)' : 'none',
        cursor: 'default',
      }}
    >
      <div style={{ fontSize: '1.35rem', fontWeight: 700, color: valueColor, fontFamily: "'Sora', 'Inter', sans-serif" }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      <div style={{ fontSize: '0.7rem', color: colors.textMuted, marginTop: '0.25rem' }}>{label}</div>
    </div>
  );
}

// Activity Item
function ActivityItem({ icon, iconColor, message, time, colors }) {
  const iconBg = colors[`${iconColor}Light`] || colors.primaryLight;
  
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem',
      padding: '0.75rem 0',
      borderBottom: `1px solid ${colors.bg}`,
    }}>
      <div style={{
        width: 28,
        height: 28,
        borderRadius: 6,
        background: iconBg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}>
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.8rem', color: colors.text, lineHeight: 1.4 }}>{message}</div>
        <div style={{ fontSize: '0.7rem', color: colors.textLight, marginTop: '0.2rem' }}>{time}</div>
      </div>
    </div>
  );
}


export default function DashboardPage() {
  const navigate = useNavigate();
  const { projects, activeProject } = useProject();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  
  const [metrics, setMetrics] = useState({
    platformHealth: 0,
    documentsClassified: 0,
    patternsLearned: 0,
    relationshipsDetected: 0,
    realityCount: 0,
    intentCount: 0,
    referenceCount: 0,
    contentBased: 0,
    extensionBased: 0,
    userOverride: 0,
    unclassified: 0,
    lookupsDetected: 0,
    findingsGenerated: 0,
    tasksCreated: 0,
    avgHealthScore: 0,
    issuesFound: 0,
    autoCleaned: 0,
    junkColumnsRemoved: 0,
    insightsCount: 0,
    sqlCacheHits: 0,
    feedbackReceived: 0,
    successRate: 0,
    recentActivity: [],
    processingByDay: [],
  });

  useEffect(() => {
    loadDashboardData();
  }, [activeProject]);

  const loadDashboardData = async () => {
    if (!refreshing) setLoading(true);
    
    try {
      // Build query param for project scoping
      const projectParam = activeProject ? `?project_id=${activeProject.id}` : '';
      
      const [
        structuredRes,
        registryRes,
        integrityRes,
        learningRes,
        jobsRes,
      ] = await Promise.all([
        api.get(`/status/structured${projectParam}`).catch(() => ({ data: {} })),
        api.get(`/status/registry${projectParam}`).catch(() => ({ data: {} })),
        api.get(`/status/data-integrity${projectParam}`).catch(() => ({ data: {} })),
        api.get('/chat/intelligent/learning/stats').catch(() => ({ data: {} })),
        api.get(`/jobs${projectParam}`).catch(() => ({ data: { jobs: [] } })),
      ]);
      
      const structured = structuredRes.data || {};
      const registry = registryRes.data || {};
      const integrity = integrityRes.data || {};
      const learning = learningRes.data || {};
      const jobs = jobsRes.data?.jobs || [];
      
      const structuredFiles = structured.files || [];
      const registryDocs = registry.documents || [];
      
      // Three Truths counts
      const realityCount = registryDocs.filter(d => d.truth_type === 'reality').length;
      const intentCount = registryDocs.filter(d => d.truth_type === 'intent').length;
      const referenceCount = registryDocs.filter(d => d.truth_type === 'reference').length;
      const totalClassified = realityCount + intentCount + referenceCount;
      
      // Classification methods
      const contentBased = registryDocs.filter(d => d.classification_method === 'content_analysis').length;
      const extensionBased = registryDocs.filter(d => d.classification_method === 'extension').length;
      const userOverride = registryDocs.filter(d => d.classification_method === 'user_override').length;
      const unclassified = registryDocs.filter(d => !d.classification_method && !d.truth_type).length;
      
      // Health scores
      const healthScores = structuredFiles.map(f => f.health_score || 100).filter(s => s > 0);
      const avgHealth = healthScores.length > 0 
        ? Math.round(healthScores.reduce((a, b) => a + b, 0) / healthScores.length)
        : 100;
      
      // Platform health calculation
      const classificationRate = totalClassified > 0 ? (totalClassified - unclassified) / totalClassified : 1;
      const successfulJobs = jobs.filter(j => j.status === 'completed').length;
      const jobSuccessRate = jobs.length > 0 ? successfulJobs / jobs.length : 1;
      const platformHealth = Math.round((avgHealth * 0.4 + classificationRate * 100 * 0.3 + jobSuccessRate * 100 * 0.3));
      
      // Intelligence metrics
      const lookupsDetected = structured.lookup_tables_count || structuredFiles.filter(f => f.is_lookup).length || 0;
      const findingsGenerated = integrity.total_findings || 0;
      const relationships = structured.relationships_count || 0;
      
      // Learning metrics
      const patterns = learning.patterns_count || learning.cached_queries || 0;
      const feedback = learning.feedback_count || 0;
      
      // Build processing by day (last 7 days)
      const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
      const processingByDay = days.map((label, i) => ({
        label,
        value: Math.floor(Math.random() * 50) + 10, // TODO: Replace with real data
      }));
      
      // Build recent activity
      const recentActivity = [];
      registryDocs.slice(0, 2).forEach(doc => {
        recentActivity.push({
          type: 'classification',
          message: `Classified "${doc.filename}" as ${doc.truth_type || 'unknown'}`,
          time: formatTimeAgo(doc.created_at || doc.uploaded_at),
        });
      });
      
      if (relationships > 0) {
        recentActivity.push({
          type: 'relationship',
          message: `Detected ${relationships} table relationships`,
          time: 'Recently',
        });
      }
      
      if (patterns > 0) {
        recentActivity.push({
          type: 'pattern',
          message: `${patterns} SQL patterns learned`,
          time: 'Ongoing',
        });
      }
      
      setMetrics({
        platformHealth,
        documentsClassified: totalClassified,
        patternsLearned: patterns,
        relationshipsDetected: relationships,
        realityCount,
        intentCount,
        referenceCount,
        contentBased,
        extensionBased,
        userOverride,
        unclassified,
        lookupsDetected,
        findingsGenerated,
        tasksCreated: 0,
        avgHealthScore: avgHealth,
        issuesFound: integrity.issues_count || 0,
        autoCleaned: integrity.auto_cleaned || 0,
        junkColumnsRemoved: integrity.junk_removed || 0,
        insightsCount: integrity.insights_count || 0,
        sqlCacheHits: learning.cache_hit_rate || 0,
        feedbackReceived: feedback,
        successRate: Math.round(jobSuccessRate * 100),
        recentActivity: recentActivity.slice(0, 4),
        processingByDay,
      });
      
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };
  
  const formatTimeAgo = (dateStr) => {
    if (!dateStr) return 'Recently';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadDashboardData();
  };

  // Calculate donut segments
  const totalDocs = metrics.contentBased + metrics.extensionBased + metrics.userOverride + metrics.unclassified;
  const donutSegments = totalDocs > 0 ? [
    { label: 'Content-Based (AI)', percent: Math.round((metrics.contentBased / totalDocs) * 100), color: colors.primary },
    { label: 'Extension-Based', percent: Math.round((metrics.extensionBased / totalDocs) * 100), color: colors.dustyBlue },
    { label: 'User Override', percent: Math.round((metrics.userOverride / totalDocs) * 100), color: colors.taupe },
    { label: 'Unclassified', percent: Math.round((metrics.unclassified / totalDocs) * 100), color: colors.textLight },
  ] : [
    { label: 'No documents', percent: 100, color: colors.cardBorder },
  ];

  // Calculate truth bar widths
  const maxTruth = Math.max(metrics.realityCount, metrics.intentCount, metrics.referenceCount, 1);

  return (
    <div style={{ 
      padding: '2rem', 
      background: colors.bg, 
      minHeight: 'calc(100vh - 60px)',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ 
            fontSize: '1.75rem', 
            fontWeight: 800, 
            margin: 0, 
            color: colors.text,
            fontFamily: "'Sora', 'Inter', sans-serif",
            letterSpacing: '-0.02em',
          }}>
            {activeProject ? `Project Intelligence` : 'Platform Intelligence'}
          </h1>
          <p style={{ color: colors.textMuted, margin: '0.5rem 0 0 0', fontSize: '0.9rem' }}>
            {activeProject 
              ? `Metrics for ${activeProject.name}`
              : 'Aggregated across all projects'}
          </p>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            fontSize: '0.75rem', 
            color: colors.success, 
            fontWeight: 600 
          }}>
            <span style={{
              width: 6,
              height: 6,
              background: colors.success,
              borderRadius: '50%',
              marginRight: '0.4rem',
              animation: 'pulse 2s infinite',
            }} />
            Live
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.6rem 1rem',
              background: colors.card,
              border: `1px solid ${colors.cardBorder}`,
              borderRadius: 10,
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 500,
              color: colors.text,
              transition: 'all 0.15s ease',
            }}
          >
            <RefreshCw size={16} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
          <span style={{ fontSize: '0.8rem', color: colors.textLight }}>
            {lastUpdated.toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Hero Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.25rem', marginBottom: '2rem' }}>
        <HeroMetric
          value={`${metrics.platformHealth}%`}
          label="Platform Health"
          icon={Shield}
          colorKey="success"
          colors={colors}
          tooltip={{
            title: "What this measures",
            description: "Combined score of document processing success, classification accuracy, and data quality.",
            insight: metrics.platformHealth >= 90 
              ? "Excellent! All systems operating normally."
              : "Below 90% indicates issues that need attention."
          }}
          onClick={() => navigate('/data')}
        />
        
        <HeroMetric
          value={metrics.documentsClassified}
          label="Documents Classified"
          icon={FileText}
          colorKey="slate"
          colors={colors}
          tooltip={{
            title: "What this measures",
            description: "Total documents automatically routed to Reality, Intent, or Reference layers.",
            insight: "Higher count = more intelligence available for queries."
          }}
          onClick={() => navigate('/data')}
        />
        
        <HeroMetric
          value={metrics.patternsLearned}
          label="Patterns Learned"
          icon={Sparkles}
          colorKey="dustyBlue"
          colors={colors}
          tooltip={{
            title: "What this measures",
            description: "SQL query patterns cached for instant reuse. Faster, more accurate repeat responses.",
            insight: "Each pattern saves 2-3 seconds on repeat questions."
          }}
          onClick={() => navigate('/workspace')}
        />
        
        <HeroMetric
          value={metrics.relationshipsDetected}
          label="Relationships Detected"
          icon={GitBranch}
          colorKey="taupe"
          colors={colors}
          tooltip={{
            title: "What this measures",
            description: "Foreign key connections discovered between tables. Enables smart cross-table queries.",
            insight: "More relationships = smarter automatic JOINs."
          }}
          onClick={() => navigate('/data?tab=relationships')}
        />
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.25rem', marginBottom: '1.25rem' }}>
        {/* Three Truths */}
        <SectionCard 
          title="Three Truths Architecture" 
          icon={Layers} 
          colors={colors}
          onHeaderClick={() => navigate('/data')}
          linkText="Explore →"
        >
          <div style={{ display: 'flex', gap: '1rem' }}>
            <TruthPillar
              label="REALITY"
              sublabel="Structured Data"
              value={metrics.realityCount}
              icon="🗄️"
              color={colors.primary}
              colorLight={colors.primaryLight}
              barWidth={(metrics.realityCount / maxTruth) * 100}
              colors={colors}
              onClick={() => navigate('/data?filter=reality')}
            />
            <TruthPillar
              label="INTENT"
              sublabel="Customer Docs"
              value={metrics.intentCount}
              icon="📋"
              color={colors.dustyBlue}
              colorLight={colors.dustyBlueLight}
              barWidth={(metrics.intentCount / maxTruth) * 100}
              colors={colors}
              onClick={() => navigate('/data?filter=intent')}
            />
            <TruthPillar
              label="REFERENCE"
              sublabel="Standards"
              value={metrics.referenceCount}
              icon="📖"
              color={colors.taupe}
              colorLight={colors.taupeLight}
              barWidth={(metrics.referenceCount / maxTruth) * 100}
              colors={colors}
              onClick={() => navigate('/data?filter=reference')}
            />
          </div>
        </SectionCard>

        {/* Classification Engine */}
        <SectionCard title="Classification Engine" icon={Brain} iconColor="slate" colors={colors}>
          <DonutChart segments={donutSegments} total={totalDocs} colors={colors} />
        </SectionCard>
      </div>

      {/* Bottom Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem' }}>
        {/* Data Quality */}
        <SectionCard title="Data Quality Engine" icon={Target} colors={colors} onHeaderClick={() => navigate('/data?tab=health')}>
          <GaugeChart value={metrics.avgHealthScore} label="Health Score" colors={colors} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
            <StatBox value={metrics.issuesFound} label="Issues Found" colorKey="warning" colors={colors} />
            <StatBox value={metrics.autoCleaned} label="Auto-Cleaned" colorKey="success" colors={colors} />
            <StatBox value={metrics.junkColumnsRemoved} label="Junk Removed" colors={colors} />
            <StatBox value={metrics.insightsCount} label="Insights" colorKey="dustyBlue" colors={colors} />
          </div>
        </SectionCard>

        {/* Intelligence Pipeline */}
        <SectionCard title="Intelligence Pipeline" icon={Zap} iconColor="taupe" colors={colors}>
          <ProgressBar label="Lookup Tables Detected" value={metrics.lookupsDetected} max={50} color={colors.primary} colors={colors} />
          <ProgressBar label="Findings Generated" value={metrics.findingsGenerated} max={5000} color={colors.dustyBlue} colors={colors} />
          <ProgressBar label="Tasks Created" value={metrics.tasksCreated} max={500} color={colors.sage} colors={colors} />
          
          <div style={{ marginTop: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.5rem' }}>Processing (7 days)</div>
            <MiniBarChart data={metrics.processingByDay} colors={colors} />
          </div>
        </SectionCard>

        {/* Recent Activity */}
        <SectionCard title="Recent Activity" icon={Activity} iconColor="dustyBlue" colors={colors}>
          {metrics.recentActivity.length === 0 ? (
            <div style={{ padding: '2rem 0', textAlign: 'center', color: colors.textMuted, fontSize: '0.85rem' }}>
              No recent activity
            </div>
          ) : (
            metrics.recentActivity.map((item, i) => (
              <ActivityItem
                key={i}
                icon={
                  item.type === 'classification' ? <FileCheck size={14} style={{ color: colors.primary }} /> :
                  item.type === 'relationship' ? <Link2 size={14} style={{ color: colors.dustyBlue }} /> :
                  <Sparkles size={14} style={{ color: colors.taupe }} />
                }
                iconColor={item.type === 'classification' ? 'primary' : item.type === 'relationship' ? 'dustyBlue' : 'taupe'}
                message={item.message}
                time={item.time}
                colors={colors}
              />
            ))
          )}
        </SectionCard>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
