/**
 * DashboardPage.jsx - Platform Intelligence Dashboard
 * 
 * Shows the sophistication of XLR8's intelligence systems:
 * - Three Truths Architecture health
 * - Classification Engine metrics
 * - Intelligence Pipeline status
 * - Data Quality Engine results
 * - Learning Engine progress
 * - Processing Performance
 * 
 * Every metric has hover explanations showing WHY it matters.
 * Click any metric to drill down into detailed views.
 */

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';
import { 
  Database, FileText, Brain, Zap, Shield, Clock,
  TrendingUp, CheckCircle, AlertTriangle, ArrowRight,
  Layers, GitBranch, Search, BarChart3, RefreshCw,
  Info, ChevronRight, Activity, Target, Sparkles,
  Server, HardDrive, FileCheck, Link2, BookOpen
} from 'lucide-react';

// Theme colors - professional, refined
const getColors = (dark) => ({
  bg: dark ? '#0f1219' : '#f8f9fc',
  card: dark ? '#1a1f2e' : '#ffffff',
  cardBorder: dark ? '#2a3142' : '#e5e8ef',
  cardHover: dark ? '#1e2433' : '#f8f9fc',
  text: dark ? '#e8eaed' : '#1a202c',
  textMuted: dark ? '#8b95a5' : '#64748b',
  textLight: dark ? '#5f6a7d' : '#94a3b8',
  primary: '#4a7c59',      // XLR8 green
  primaryLight: dark ? 'rgba(74, 124, 89, 0.15)' : 'rgba(74, 124, 89, 0.08)',
  primaryDark: '#3d6649',
  accent: '#6366f1',       // Indigo for emphasis
  accentLight: dark ? 'rgba(99, 102, 241, 0.15)' : 'rgba(99, 102, 241, 0.08)',
  success: '#10b981',
  successLight: dark ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.08)',
  warning: '#f59e0b',
  warningLight: dark ? 'rgba(245, 158, 11, 0.15)' : 'rgba(245, 158, 11, 0.08)',
  error: '#ef4444',
  errorLight: dark ? 'rgba(239, 68, 68, 0.15)' : 'rgba(239, 68, 68, 0.08)',
  divider: dark ? '#2a3142' : '#e5e8ef',
});

// Tooltip Component with explanation
function Tooltip({ children, tooltip, colors, dark }) {
  const [show, setShow] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const triggerRef = useRef(null);
  
  const handleMouseEnter = () => {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) {
      setPosition({
        x: rect.left + rect.width / 2,
        y: rect.top - 10
      });
    }
    setShow(true);
  };
  
  return (
    <div 
      ref={triggerRef}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setShow(false)}
      style={{ position: 'relative', display: 'inline-flex', width: '100%' }}
    >
      {children}
      {show && tooltip && (
        <div style={{
          position: 'fixed',
          left: position.x,
          top: position.y,
          transform: 'translate(-50%, -100%)',
          zIndex: 1000,
          background: dark ? '#1a1f2e' : '#ffffff',
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: 12,
          padding: '1rem 1.25rem',
          maxWidth: 320,
          boxShadow: '0 20px 40px rgba(0,0,0,0.15), 0 8px 16px rgba(0,0,0,0.1)',
          pointerEvents: 'none',
        }}>
          <div style={{ 
            fontSize: '0.75rem', 
            fontWeight: 700, 
            color: colors.primary,
            marginBottom: '0.5rem',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}>
            {tooltip.title}
          </div>
          <div style={{ 
            fontSize: '0.85rem', 
            color: colors.text,
            lineHeight: 1.5,
            marginBottom: tooltip.insight ? '0.75rem' : 0
          }}>
            {tooltip.description}
          </div>
          {tooltip.insight && (
            <div style={{
              fontSize: '0.8rem',
              color: colors.textMuted,
              padding: '0.5rem 0.75rem',
              background: colors.primaryLight,
              borderRadius: 6,
              borderLeft: `3px solid ${colors.primary}`,
            }}>
              💡 {tooltip.insight}
            </div>
          )}
          {/* Arrow */}
          <div style={{
            position: 'absolute',
            bottom: -6,
            left: '50%',
            transform: 'translateX(-50%) rotate(45deg)',
            width: 12,
            height: 12,
            background: dark ? '#1a1f2e' : '#ffffff',
            borderRight: `1px solid ${colors.cardBorder}`,
            borderBottom: `1px solid ${colors.cardBorder}`,
          }} />
        </div>
      )}
    </div>
  );
}

// Large Metric Card (for hero stats)
function HeroMetric({ value, label, icon: Icon, tooltip, colors, dark, onClick, status = 'normal' }) {
  const [hovered, setHovered] = useState(false);
  
  const statusColor = status === 'success' ? colors.success 
    : status === 'warning' ? colors.warning 
    : status === 'error' ? colors.error 
    : colors.primary;
  
  const content = (
    <div 
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: colors.card,
        border: `1px solid ${hovered ? statusColor : colors.cardBorder}`,
        borderRadius: 16,
        padding: '1.5rem',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s ease',
        transform: hovered ? 'translateY(-2px)' : 'translateY(0)',
        boxShadow: hovered 
          ? `0 12px 24px rgba(0,0,0,0.1), 0 0 0 1px ${statusColor}20`
          : '0 2px 8px rgba(0,0,0,0.04)',
        position: 'relative',
        overflow: 'hidden',
        width: '100%',
      }}
    >
      {/* Subtle gradient overlay */}
      <div style={{
        position: 'absolute',
        top: 0,
        right: 0,
        width: 120,
        height: 120,
        background: `radial-gradient(circle at top right, ${statusColor}08, transparent)`,
        pointerEvents: 'none',
      }} />
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div style={{
          width: 44,
          height: 44,
          borderRadius: 12,
          background: `${statusColor}15`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Icon size={22} style={{ color: statusColor }} />
        </div>
        {tooltip && (
          <Info size={16} style={{ color: colors.textLight, opacity: 0.6 }} />
        )}
      </div>
      
      <div style={{ 
        fontSize: '2.5rem', 
        fontWeight: 800, 
        color: colors.text, 
        lineHeight: 1,
        fontFamily: "'Sora', sans-serif",
        marginBottom: '0.5rem'
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
  );
  
  if (tooltip) {
    return <Tooltip tooltip={tooltip} colors={colors} dark={dark}>{content}</Tooltip>;
  }
  return content;
}

// Section Card with metrics
function SectionCard({ title, icon: Icon, metrics, colors, dark, onSectionClick }) {
  const [hovered, setHovered] = useState(false);
  
  return (
    <div 
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: colors.card,
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: 16,
        overflow: 'hidden',
        transition: 'all 0.2s ease',
        boxShadow: hovered ? '0 8px 24px rgba(0,0,0,0.08)' : '0 2px 8px rgba(0,0,0,0.04)',
      }}
    >
      {/* Header */}
      <div 
        onClick={onSectionClick}
        style={{
          padding: '1rem 1.25rem',
          borderBottom: `1px solid ${colors.divider}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: onSectionClick ? 'pointer' : 'default',
          background: hovered ? colors.cardHover : 'transparent',
          transition: 'background 0.15s ease',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: colors.primaryLight,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Icon size={16} style={{ color: colors.primary }} />
          </div>
          <span style={{ 
            fontSize: '0.9rem', 
            fontWeight: 700, 
            color: colors.text,
            letterSpacing: '-0.01em'
          }}>
            {title}
          </span>
        </div>
        {onSectionClick && (
          <ArrowRight size={16} style={{ color: colors.textLight }} />
        )}
      </div>
      
      {/* Metrics */}
      <div style={{ padding: '0.5rem 0' }}>
        {metrics.map((metric, i) => (
          <MetricRow key={i} {...metric} colors={colors} dark={dark} />
        ))}
      </div>
    </div>
  );
}

// Individual metric row within a section
function MetricRow({ label, value, tooltip, status, onClick, colors, dark }) {
  const [hovered, setHovered] = useState(false);
  
  const statusIcon = status === 'success' ? <CheckCircle size={14} style={{ color: colors.success }} />
    : status === 'warning' ? <AlertTriangle size={14} style={{ color: colors.warning }} />
    : status === 'error' ? <AlertTriangle size={14} style={{ color: colors.error }} />
    : null;
  
  const content = (
    <div 
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.75rem 1.25rem',
        cursor: onClick ? 'pointer' : 'default',
        background: hovered ? colors.cardHover : 'transparent',
        transition: 'background 0.15s ease',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        {statusIcon}
        <span style={{ fontSize: '0.85rem', color: colors.textMuted }}>{label}</span>
        {tooltip && (
          <Info size={12} style={{ color: colors.textLight, opacity: 0.4 }} />
        )}
      </div>
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '0.5rem',
        fontSize: '0.9rem',
        fontWeight: 700,
        color: colors.text,
      }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
        {onClick && <ChevronRight size={14} style={{ color: colors.textLight, opacity: 0.5 }} />}
      </div>
    </div>
  );
  
  if (tooltip) {
    return <Tooltip tooltip={tooltip} colors={colors} dark={dark}>{content}</Tooltip>;
  }
  return content;
}

// Progress bar component
function ProgressBar({ value, max, label, color, colors }) {
  const percentage = Math.min((value / max) * 100, 100);
  
  return (
    <div style={{ marginBottom: '0.75rem' }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        marginBottom: '0.35rem',
        fontSize: '0.8rem',
      }}>
        <span style={{ color: colors.textMuted }}>{label}</span>
        <span style={{ fontWeight: 600, color: colors.text }}>{value}%</span>
      </div>
      <div style={{
        height: 6,
        background: colors.divider,
        borderRadius: 3,
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${percentage}%`,
          background: color || colors.primary,
          borderRadius: 3,
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  );
}

// Activity Item
function ActivityItem({ item, colors }) {
  const getIcon = () => {
    switch (item.type) {
      case 'classification': return <FileCheck size={14} style={{ color: colors.primary }} />;
      case 'relationship': return <Link2 size={14} style={{ color: colors.accent }} />;
      case 'pattern': return <Sparkles size={14} style={{ color: colors.warning }} />;
      case 'finding': return <AlertTriangle size={14} style={{ color: colors.error }} />;
      default: return <Activity size={14} style={{ color: colors.textMuted }} />;
    }
  };
  
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem',
      padding: '0.75rem 0',
      borderBottom: `1px solid ${colors.divider}`,
    }}>
      <div style={{
        width: 28,
        height: 28,
        borderRadius: 8,
        background: colors.cardHover,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}>
        {getIcon()}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ 
          fontSize: '0.85rem', 
          color: colors.text,
          lineHeight: 1.4,
        }}>
          {item.message}
        </div>
        <div style={{ fontSize: '0.75rem', color: colors.textLight, marginTop: '0.25rem' }}>
          {item.time}
        </div>
      </div>
    </div>
  );
}


export default function DashboardPage() {
  const navigate = useNavigate();
  const { projects: realProjects } = useProject();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  
  // Platform Intelligence Metrics
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
    expertContextsUsed: 0,
    avgParseTime: 0,
    successRate: 0,
    recentActivity: [],
  });

  useEffect(() => {
    loadDashboardData();
  }, [realProjects]);

  const loadDashboardData = async () => {
    if (!refreshing) setLoading(true);
    try {
      const [
        structuredRes,
        docsRes,
        registryRes,
        integrityRes,
        learningRes,
        jobsRes,
      ] = await Promise.all([
        api.get('/status/structured').catch(() => ({ data: {} })),
        api.get('/status/documents').catch(() => ({ data: {} })),
        api.get('/status/registry').catch(() => ({ data: {} })),
        api.get('/status/data-integrity').catch(() => ({ data: {} })),
        api.get('/chat/intelligent/learning/stats').catch(() => ({ data: {} })),
        api.get('/jobs').catch(() => ({ data: { jobs: [] } })),
      ]);
      
      const structured = structuredRes.data || {};
      const docs = docsRes.data || {};
      const registry = registryRes.data || {};
      const integrity = integrityRes.data || {};
      const learning = learningRes.data || {};
      const jobs = jobsRes.data?.jobs || [];
      
      const structuredFiles = structured.files || [];
      const documents = docs.documents || [];
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
      const unclassified = registryDocs.filter(d => !d.classification_method).length;
      
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
      const lookupsDetected = structured.lookup_tables_count || 0;
      const findingsGenerated = integrity.total_findings || 0;
      const relationships = structured.relationships_count || 0;
      
      // Learning metrics
      const patterns = learning.patterns_count || learning.cached_queries || 0;
      const feedback = learning.feedback_count || 0;
      
      // Processing performance
      const recentJobs = jobs.slice(0, 20);
      const avgParseTime = recentJobs.length > 0
        ? (recentJobs.reduce((sum, j) => sum + (j.processing_time_ms || 0), 0) / recentJobs.length / 1000).toFixed(1)
        : 0;
      
      // Build recent activity
      const recentActivity = [];
      
      registryDocs.slice(0, 3).forEach(doc => {
        recentActivity.push({
          type: 'classification',
          message: `Classified "${doc.filename}" as ${doc.truth_type || 'unknown'}`,
          time: formatTimeAgo(doc.created_at || doc.uploaded_at),
        });
      });
      
      if (findingsGenerated > 0) {
        recentActivity.push({
          type: 'finding',
          message: `Generated ${findingsGenerated} data quality findings`,
          time: 'Recently',
        });
      }
      
      if (patterns > 0) {
        recentActivity.push({
          type: 'pattern',
          message: `${patterns} SQL patterns learned and cached`,
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
        expertContextsUsed: learning.expert_contexts_used || 0,
        avgParseTime: parseFloat(avgParseTime),
        successRate: Math.round(jobSuccessRate * 100),
        recentActivity: recentActivity.slice(0, 5),
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

  const healthStatus = metrics.platformHealth >= 90 ? 'success' 
    : metrics.platformHealth >= 70 ? 'warning' 
    : 'error';

  return (
    <div style={{ 
      padding: '2rem', 
      background: colors.bg, 
      minHeight: 'calc(100vh - 60px)',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-start', 
        marginBottom: '2rem' 
      }}>
        <div>
          <h1 style={{ 
            fontSize: '1.75rem', 
            fontWeight: 800, 
            margin: 0, 
            color: colors.text,
            fontFamily: "'Sora', sans-serif",
            letterSpacing: '-0.02em',
          }}>
            Platform Intelligence
          </h1>
          <p style={{ 
            color: colors.textMuted, 
            margin: '0.5rem 0 0 0', 
            fontSize: '0.9rem' 
          }}>
            Real-time view of XLR8's intelligent systems
          </p>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
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
              color: colors.text,
              fontSize: '0.85rem',
              fontWeight: 500,
            }}
          >
            <RefreshCw size={16} style={{ 
              animation: refreshing ? 'spin 1s linear infinite' : 'none' 
            }} />
            Refresh
          </button>
          <span style={{ fontSize: '0.8rem', color: colors.textLight }}>
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Hero Metrics */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(4, 1fr)', 
        gap: '1.25rem', 
        marginBottom: '2rem' 
      }}>
        <HeroMetric
          value={`${metrics.platformHealth}%`}
          label="Platform Health"
          icon={Shield}
          status={healthStatus}
          colors={colors}
          dark={darkMode}
          tooltip={{
            title: "What this measures",
            description: "Combined score of document processing success, classification accuracy, and data quality across all projects.",
            insight: metrics.platformHealth < 90 
              ? "Below 90% indicates issues that need attention."
              : "Excellent! All systems operating normally."
          }}
          onClick={() => navigate('/data')}
        />
        
        <HeroMetric
          value={metrics.documentsClassified}
          label="Documents Classified"
          icon={FileText}
          colors={colors}
          dark={darkMode}
          tooltip={{
            title: "What this measures",
            description: "Total documents automatically routed to Reality (structured data), Intent (customer documents), or Reference (standards/checklists).",
            insight: "Higher count = more intelligence available for queries and analysis."
          }}
          onClick={() => navigate('/data')}
        />
        
        <HeroMetric
          value={metrics.patternsLearned}
          label="Patterns Learned"
          icon={Sparkles}
          colors={colors}
          dark={darkMode}
          tooltip={{
            title: "What this measures",
            description: "SQL query patterns cached for instant reuse. When users ask similar questions, cached patterns provide faster, more accurate responses.",
            insight: "Each pattern saves 2-3 seconds on repeat questions."
          }}
          onClick={() => navigate('/workspace')}
        />
        
        <HeroMetric
          value={metrics.relationshipsDetected}
          label="Relationships Detected"
          icon={GitBranch}
          colors={colors}
          dark={darkMode}
          tooltip={{
            title: "What this measures",
            description: "Foreign key connections discovered between tables. Enables cross-table queries like 'employees by department' without manual mapping.",
            insight: "More relationships = smarter automatic JOINs in queries."
          }}
          onClick={() => navigate('/data?tab=relationships')}
        />
      </div>

      {/* Main Grid */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr 1fr 380px', 
        gap: '1.25rem' 
      }}>
        {/* Three Truths Architecture */}
        <SectionCard
          title="Three Truths Architecture"
          icon={Layers}
          colors={colors}
          dark={darkMode}
          onSectionClick={() => navigate('/data')}
          metrics={[
            {
              label: 'Reality (Structured Data)',
              value: metrics.realityCount,
              status: metrics.realityCount > 0 ? 'success' : null,
              tooltip: {
                title: "Reality Layer",
                description: "Excel files, CSVs, and databases stored in DuckDB. This is your queryable source of truth for employee data, configurations, and transactions.",
                insight: "Queries like 'how many employees' pull from Reality."
              },
              onClick: () => navigate('/data?filter=reality'),
            },
            {
              label: 'Intent (Customer Documents)',
              value: metrics.intentCount,
              status: metrics.intentCount > 0 ? 'success' : null,
              tooltip: {
                title: "Intent Layer",
                description: "Requirements, SOWs, and customer-provided documents stored in ChromaDB. Captures what the customer wants to achieve.",
                insight: "Used to validate if Reality matches what customer requested."
              },
              onClick: () => navigate('/data?filter=intent'),
            },
            {
              label: 'Reference (Standards)',
              value: metrics.referenceCount,
              status: metrics.referenceCount > 0 ? 'success' : null,
              tooltip: {
                title: "Reference Layer",
                description: "Best practice guides, checklists, and compliance standards. The 'gold standard' for how things should be configured.",
                insight: "Enables validation like 'is this SUI rate correct?'"
              },
              onClick: () => navigate('/data?filter=reference'),
            },
          ]}
        />

        {/* Classification Engine */}
        <SectionCard
          title="Classification Engine"
          icon={Brain}
          colors={colors}
          dark={darkMode}
          onSectionClick={() => navigate('/data')}
          metrics={[
            {
              label: 'Content-Based (AI)',
              value: `${metrics.contentBased} files`,
              tooltip: {
                title: "Content Analysis",
                description: "Documents classified by analyzing their actual content - headers, structure, and text patterns - using AI.",
                insight: "Most accurate method. Used for ambiguous file types."
              },
            },
            {
              label: 'Extension-Based',
              value: `${metrics.extensionBased} files`,
              tooltip: {
                title: "Extension Detection",
                description: "Quick classification based on file extension (.xlsx → Reality, .pdf → Intent). Fast but less nuanced.",
                insight: "Used as first-pass before content analysis."
              },
            },
            {
              label: 'User Override',
              value: `${metrics.userOverride} files`,
              tooltip: {
                title: "Manual Classification",
                description: "Documents where a user explicitly set the truth type, overriding automatic classification.",
                insight: "User corrections help train future classifications."
              },
            },
            {
              label: 'Unclassified',
              value: `${metrics.unclassified} files`,
              status: metrics.unclassified > 0 ? 'warning' : 'success',
              tooltip: {
                title: "Pending Classification",
                description: "Documents that haven't been classified yet or couldn't be automatically determined.",
                insight: metrics.unclassified > 0 
                  ? "Review these files to ensure proper routing."
                  : "All documents successfully classified!"
              },
              onClick: metrics.unclassified > 0 ? () => navigate('/data?filter=unclassified') : null,
            },
          ]}
        />

        {/* Recent Intelligence Activity */}
        <div style={{
          background: colors.card,
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: 16,
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '1rem 1.25rem',
            borderBottom: `1px solid ${colors.divider}`,
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
          }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: colors.accentLight,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Activity size={16} style={{ color: colors.accent }} />
            </div>
            <span style={{ 
              fontSize: '0.9rem', 
              fontWeight: 700, 
              color: colors.text 
            }}>
              Recent Intelligence Activity
            </span>
          </div>
          
          <div style={{ padding: '0.5rem 1.25rem' }}>
            {metrics.recentActivity.length === 0 ? (
              <div style={{ 
                padding: '2rem 0', 
                textAlign: 'center', 
                color: colors.textMuted,
                fontSize: '0.85rem' 
              }}>
                No recent activity
              </div>
            ) : (
              metrics.recentActivity.map((item, i) => (
                <ActivityItem key={i} item={item} colors={colors} />
              ))
            )}
          </div>
        </div>

        {/* Data Quality Engine */}
        <SectionCard
          title="Data Quality Engine"
          icon={Target}
          colors={colors}
          dark={darkMode}
          onSectionClick={() => navigate('/data?tab=health')}
          metrics={[
            {
              label: 'Average Health Score',
              value: `${metrics.avgHealthScore}%`,
              status: metrics.avgHealthScore >= 90 ? 'success' : metrics.avgHealthScore >= 70 ? 'warning' : 'error',
              tooltip: {
                title: "Data Health",
                description: "Weighted score based on fill rates, data type consistency, and absence of parsing artifacts across all uploaded files.",
                insight: metrics.avgHealthScore < 90 
                  ? "Click to see which files need attention."
                  : "Excellent data quality across all files!"
              },
              onClick: () => navigate('/data?tab=health'),
            },
            {
              label: 'Issues Detected',
              value: metrics.issuesFound,
              status: metrics.issuesFound > 0 ? 'warning' : 'success',
              tooltip: {
                title: "Quality Issues",
                description: "Problems like missing required fields, invalid formats, or suspicious patterns that may need review.",
                insight: "Issues are auto-prioritized by severity."
              },
              onClick: () => navigate('/data?tab=health&filter=issues'),
            },
            {
              label: 'Auto-Cleaned',
              value: metrics.autoCleaned,
              tooltip: {
                title: "Automatic Cleanup",
                description: "Junk columns, parsing artifacts, and empty fields automatically removed during upload.",
                insight: "Saves manual cleanup time while preserving real data."
              },
            },
            {
              label: 'Insights (Optional Fields)',
              value: metrics.insightsCount,
              tooltip: {
                title: "Optional Field Insights",
                description: "Fields like UDFs or custom attributes that are empty but don't affect data quality. Informational, not issues.",
                insight: "These may indicate unused configuration options."
              },
            },
          ]}
        />

        {/* Intelligence Pipeline */}
        <SectionCard
          title="Intelligence Pipeline"
          icon={Zap}
          colors={colors}
          dark={darkMode}
          onSectionClick={() => navigate('/data?tab=intelligence')}
          metrics={[
            {
              label: 'Lookup Tables Detected',
              value: metrics.lookupsDetected,
              tooltip: {
                title: "Lookup Detection",
                description: "Reference tables automatically identified (pay groups, job codes, locations, etc.) and indexed for validation.",
                insight: "Lookups enable dropdown suggestions and value validation."
              },
            },
            {
              label: 'Findings Generated',
              value: metrics.findingsGenerated,
              tooltip: {
                title: "Auto-Generated Findings",
                description: "Data quality observations, missing values, and potential issues discovered during analysis.",
                insight: "Findings become actionable tasks when assigned to playbooks."
              },
              onClick: () => navigate('/playbooks'),
            },
            {
              label: 'Tasks Created',
              value: metrics.tasksCreated,
              tooltip: {
                title: "Actionable Tasks",
                description: "Findings converted into trackable tasks with owners and due dates.",
                insight: "Connect playbooks to convert findings into tasks."
              },
              onClick: () => navigate('/playbooks'),
            },
          ]}
        />

        {/* Learning & Performance */}
        <div style={{
          background: colors.card,
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: 16,
          padding: '1.25rem',
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.75rem',
            marginBottom: '1rem'
          }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: colors.successLight,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <TrendingUp size={16} style={{ color: colors.success }} />
            </div>
            <span style={{ 
              fontSize: '0.9rem', 
              fontWeight: 700, 
              color: colors.text 
            }}>
              Learning & Performance
            </span>
          </div>
          
          <div style={{ marginBottom: '1.25rem' }}>
            <Tooltip tooltip={{
              title: "SQL Cache Performance",
              description: "Percentage of queries served from cached patterns vs. generated fresh. Higher = faster responses.",
              insight: "Cache builds automatically as users ask questions."
            }} colors={colors} dark={darkMode}>
              <div>
                <ProgressBar 
                  value={metrics.sqlCacheHits} 
                  max={100} 
                  label="SQL Cache Hit Rate"
                  color={colors.success}
                  colors={colors}
                />
              </div>
            </Tooltip>
            
            <Tooltip tooltip={{
              title: "Processing Success",
              description: "Percentage of file uploads that complete successfully without errors.",
              insight: metrics.successRate < 95 ? "Check failed jobs for details." : "Excellent reliability!"
            }} colors={colors} dark={darkMode}>
              <div>
                <ProgressBar 
                  value={metrics.successRate} 
                  max={100} 
                  label="Processing Success Rate"
                  color={metrics.successRate >= 95 ? colors.success : colors.warning}
                  colors={colors}
                />
              </div>
            </Tooltip>
          </div>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr', 
            gap: '1rem',
            padding: '1rem',
            background: colors.cardHover,
            borderRadius: 10,
          }}>
            <Tooltip tooltip={{
              title: "User Feedback",
              description: "Thumbs up/down feedback received on AI responses. Used to improve response quality.",
              insight: "More feedback = smarter responses over time."
            }} colors={colors} dark={darkMode}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: colors.text }}>
                  {metrics.feedbackReceived}
                </div>
                <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>
                  Feedback Received
                </div>
              </div>
            </Tooltip>
            
            <Tooltip tooltip={{
              title: "Avg Processing Time",
              description: "Average time to parse, analyze, and store uploaded files.",
              insight: metrics.avgParseTime > 5 ? "Large files may take longer." : "Fast processing!"
            }} colors={colors} dark={darkMode}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: colors.text }}>
                  {metrics.avgParseTime}s
                </div>
                <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>
                  Avg Parse Time
                </div>
              </div>
            </Tooltip>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
