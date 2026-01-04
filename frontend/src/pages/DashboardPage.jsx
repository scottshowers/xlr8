/**
 * DashboardPage.jsx - Mission Control v2
 * =======================================
 * 
 * Real platform intelligence with:
 * - Pipeline health (actual tests, not pings)
 * - Data by Five Truths
 * - Lineage tracking (file → tables)
 * - Relationship coverage
 * - Attention items
 * - Historical activity graphs
 * 
 * Uses: /api/dashboard (single consolidated endpoint)
 * 
 * Updated: January 4, 2026
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle, CheckCircle, TrendingUp, TrendingDown,
  Clock, Zap, Database, Upload, FileText, Link2,
  Target, RefreshCw, Activity, Layers, GitBranch,
  Server, Bell, XCircle, AlertCircle, ChevronRight,
  BarChart3, PieChart, ArrowRight, Eye
} from 'lucide-react';
import { Tooltip } from '../components/ui';

// ============================================================================
// BRAND COLORS (Green primary, Blue accent)
// ============================================================================
const colors = {
  primary: '#7aa866',
  primaryBright: '#83b16d',
  accent: '#285390',
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
  error: '#dc2626',
  success: '#16a34a',
};

// Truth type colors (Five Truths - Part 14 Visual Standards)
const truthColors = {
  reality: '#285390',
  configuration: '#7aa866',
  reference: '#5f4282',
  regulatory: '#993c44',
  intent: '#2766b1',
  unclassified: '#a2a1a0',
};

const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================
function formatNumber(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return n?.toLocaleString() || '0';
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

// ============================================================================
// PIPELINE STATUS
// ============================================================================
function PipelineStatus({ data }) {
  const stages = data?.stages || {};
  const allHealthy = data?.healthy;
  
  const stageConfig = [
    { key: 'upload', label: 'Upload', icon: Upload, 
      tooltip: { title: 'Upload Pipeline', detail: 'Tests file ingestion and DuckDB table creation. Validates that uploaded files can be processed into queryable tables.', action: 'Green = files processing correctly' }},
    { key: 'process', label: 'Process', icon: Database, 
      tooltip: { title: 'Process Pipeline', detail: 'Tests schema metadata extraction and column profiling. Ensures table structures are being analyzed for intelligent queries.', action: 'Green = metadata being captured' }},
    { key: 'query', label: 'Query', icon: Zap, 
      tooltip: { title: 'Query Pipeline', detail: 'Tests intelligence engine query capability. Validates that natural language questions can be translated to SQL.', action: 'Green = queries executing correctly' }},
    { key: 'semantic', label: 'Semantic', icon: Layers, 
      tooltip: { title: 'Semantic Pipeline', detail: 'Tests ChromaDB vector search and embeddings. Ensures reference docs and regulatory content is searchable.', action: 'Green = semantic search operational' }},
  ];
  
  return (
    <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '20px', border: `1px solid ${colors.border}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <Tooltip 
          title="Pipeline Status" 
          detail="Real-time health checks for each pipeline stage. Tests actual operations, not just connectivity pings."
          action="Hover each stage for details"
        >
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'help' }}>
            <Activity size={16} color={colors.primary} />
            Pipeline Status
          </h3>
        </Tooltip>
        <div style={{ 
          fontSize: '11px', 
          padding: '4px 10px', 
          borderRadius: '12px',
          backgroundColor: allHealthy ? `${colors.success}15` : `${colors.error}15`,
          color: allHealthy ? colors.success : colors.error,
          fontWeight: 500
        }}>
          {allHealthy ? 'All Systems Healthy' : 'Issues Detected'}
        </div>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr auto 1fr auto 1fr', alignItems: 'center', gap: '12px' }}>
        {stageConfig.map((stage, i) => {
          const stageData = stages[stage.key] || {};
          const Icon = stage.icon;
          const healthy = stageData.healthy !== false;
          
          return (
            <React.Fragment key={stage.key}>
              <Tooltip 
                title={stage.tooltip.title} 
                detail={stage.tooltip.detail} 
                action={stage.tooltip.action}
                position="bottom"
              >
                <div 
                  style={{
                    padding: '16px 12px',
                    borderRadius: '8px',
                    backgroundColor: healthy ? `${colors.success}08` : `${colors.error}08`,
                    border: `1px solid ${healthy ? colors.success : colors.error}30`,
                    textAlign: 'center',
                    cursor: 'help'
                  }}
                >
                  <Icon size={20} color={healthy ? colors.success : colors.error} style={{ marginBottom: '8px' }} />
                  <div style={{ fontSize: '13px', fontWeight: 500, color: colors.text }}>{stage.label}</div>
                  <div style={{ fontSize: '11px', color: colors.textMuted, marginTop: '4px' }}>
                    {stageData.latency_ms ? `${stageData.latency_ms}ms` : '—'}
                  </div>
                </div>
              </Tooltip>
              {i < stageConfig.length - 1 && (
                <ArrowRight size={16} color={colors.silver} />
              )}
            </React.Fragment>
          );
        })}
      </div>
      
      {data?.last_test && (
        <div style={{ marginTop: '12px', fontSize: '11px', color: colors.textMuted, textAlign: 'right' }}>
          Last test: {formatTimeAgo(data.last_test)} • Total: {data.total_latency_ms}ms
        </div>
      )}
    </div>
  );
}

// ============================================================================
// DATA BY TRUTH TYPE
// ============================================================================
function DataByTruthType({ data }) {
  const byType = data?.by_truth_type || {};
  
  const truthTypes = [
    { key: 'reality', label: 'Reality', icon: Database, desc: 'Transactional data',
      tooltip: { title: 'Reality Truth', detail: 'Customer transactional data - employee records, payroll, time tracking. Stored in DuckDB for fast SQL queries.', action: 'Upload CSV/Excel files to populate' }},
    { key: 'configuration', label: 'Configuration', icon: Server, desc: 'System setup',
      tooltip: { title: 'Configuration Truth', detail: 'Customer system settings - pay codes, earning codes, tax setups. Used to validate data against intended config.', action: 'Upload config exports from HCM systems' }},
    { key: 'reference', label: 'Reference', icon: FileText, desc: 'Product docs',
      tooltip: { title: 'Reference Truth', detail: 'Product documentation and best practices. Enables AI to provide context-aware recommendations.', action: 'Stored in ChromaDB for semantic search' }},
    { key: 'regulatory', label: 'Regulatory', icon: AlertCircle, desc: 'Compliance rules',
      tooltip: { title: 'Regulatory Truth', detail: 'Tax rules, labor laws, compliance requirements. Powers automated compliance checking.', action: 'Regulations by jurisdiction' }},
    { key: 'intent', label: 'Intent', icon: Target, desc: 'Customer goals',
      tooltip: { title: 'Intent Truth', detail: 'Customer requirements, SOWs, project goals. Helps identify gaps between what customer wants and what they have.', action: 'Upload requirements documents' }},
  ];
  
  return (
    <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '20px', border: `1px solid ${colors.border}` }}>
      <Tooltip 
        title="Five Truths Architecture" 
        detail="XLR8's data model separates information into five truth types, each serving a distinct analytical purpose."
        action="Hover each type for details"
      >
        <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'help' }}>
          <PieChart size={16} color={colors.primary} />
          Data by Truth Type
        </h3>
      </Tooltip>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {truthTypes.map(truth => {
          const typeData = byType[truth.key] || {};
          const files = typeData.files || 0;
          const tables = typeData.tables || 0;
          const rows = typeData.rows || 0;
          const chunks = typeData.chunks || 0;
          const Icon = truth.icon;
          
          return (
            <Tooltip 
              key={truth.key}
              title={truth.tooltip.title} 
              detail={truth.tooltip.detail} 
              action={truth.tooltip.action}
              position="right"
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                padding: '10px 12px',
                borderRadius: '8px',
                backgroundColor: `${truthColors[truth.key]}08`,
                border: `1px solid ${truthColors[truth.key]}20`,
                cursor: 'help'
              }}>
                <div style={{
                  width: '32px', height: '32px', borderRadius: '8px',
                  backgroundColor: truthColors[truth.key],
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginRight: '12px'
                }}>
                  <Icon size={16} color={colors.white} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '13px', fontWeight: 500, color: colors.text }}>{truth.label}</div>
                  <div style={{ fontSize: '11px', color: colors.textMuted }}>{truth.desc}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: colors.text }}>
                    {files} files
                  </div>
                  <div style={{ fontSize: '11px', color: colors.textMuted }}>
                    {tables > 0 ? `${tables} tables • ${formatNumber(rows)} rows` : 
                     chunks > 0 ? `${formatNumber(chunks)} chunks` : '—'}
                  </div>
                </div>
              </div>
            </Tooltip>
          );
        })}
      </div>
      
      <div style={{ marginTop: '12px', padding: '10px', backgroundColor: colors.background, borderRadius: '8px', display: 'flex', justifyContent: 'space-around' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '18px', fontWeight: 600, color: colors.accent }}>{data?.total_files || 0}</div>
          <div style={{ fontSize: '11px', color: colors.textMuted }}>Files</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '18px', fontWeight: 600, color: colors.accent }}>{data?.total_tables || 0}</div>
          <div style={{ fontSize: '11px', color: colors.textMuted }}>Tables</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '18px', fontWeight: 600, color: colors.accent }}>{formatNumber(data?.total_rows || 0)}</div>
          <div style={{ fontSize: '11px', color: colors.textMuted }}>Rows</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '18px', fontWeight: 600, color: colors.accent }}>{formatNumber(data?.total_chunks || 0)}</div>
          <div style={{ fontSize: '11px', color: colors.textMuted }}>Chunks</div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// LINEAGE TRACKING
// ============================================================================
function LineageTracking({ data }) {
  return (
    <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '20px', border: `1px solid ${colors.border}` }}>
      <Tooltip 
        title="Data Lineage" 
        detail="Tracks data provenance: which files produced which tables. Essential for audit trails, debugging, and demonstrating data governance to buyers."
        action="Click files to see full lineage chain"
      >
        <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'help' }}>
          <GitBranch size={16} color={colors.primary} />
          Data Lineage
        </h3>
      </Tooltip>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '16px' }}>
        <Tooltip title="Files Tracked" detail="Number of uploaded files with lineage recorded. Each file's journey through the pipeline is tracked." position="bottom">
          <div style={{ padding: '12px', backgroundColor: colors.background, borderRadius: '8px', textAlign: 'center', cursor: 'help' }}>
            <div style={{ fontSize: '20px', fontWeight: 600, color: colors.accent }}>{data?.files_tracked || 0}</div>
            <div style={{ fontSize: '11px', color: colors.textMuted }}>Files Tracked</div>
          </div>
        </Tooltip>
        <Tooltip title="Tables Created" detail="Number of DuckDB tables generated from uploaded files. One file can create multiple tables (multi-sheet Excel, etc)." position="bottom">
          <div style={{ padding: '12px', backgroundColor: colors.background, borderRadius: '8px', textAlign: 'center', cursor: 'help' }}>
            <div style={{ fontSize: '20px', fontWeight: 600, color: colors.accent }}>{data?.tables_created || 0}</div>
            <div style={{ fontSize: '11px', color: colors.textMuted }}>Tables Created</div>
          </div>
        </Tooltip>
        <Tooltip title="Lineage Edges" detail="Total connections in the lineage graph. Edges connect files → tables → analyses → outputs." position="bottom">
          <div style={{ padding: '12px', backgroundColor: colors.background, borderRadius: '8px', textAlign: 'center', cursor: 'help' }}>
            <div style={{ fontSize: '20px', fontWeight: 600, color: colors.accent }}>{data?.total_edges || 0}</div>
            <div style={{ fontSize: '11px', color: colors.textMuted }}>Lineage Edges</div>
          </div>
        </Tooltip>
      </div>
      
      <div style={{ fontSize: '12px', fontWeight: 500, color: colors.text, marginBottom: '8px' }}>Recent Provenance</div>
      
      {(data?.recent || []).length === 0 ? (
        <div style={{ padding: '20px', textAlign: 'center', color: colors.textMuted, fontSize: '12px' }}>
          No lineage data yet. Upload files to see provenance tracking.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {(data?.recent || []).slice(0, 5).map((item, i) => (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'center',
              padding: '8px 10px',
              backgroundColor: colors.background,
              borderRadius: '6px',
              fontSize: '12px'
            }}>
              <FileText size={14} color={colors.primary} style={{ marginRight: '8px' }} />
              <span style={{ fontWeight: 500, color: colors.text }}>{item.file}</span>
              <ArrowRight size={12} color={colors.silver} style={{ margin: '0 8px' }} />
              <span style={{ color: colors.textMuted }}>
                {item.tables?.length || 0} tables • {formatNumber(item.rows)} rows
              </span>
              <span style={{ marginLeft: 'auto', color: colors.textMuted, fontSize: '11px' }}>
                {formatTimeAgo(item.timestamp)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// RELATIONSHIP COVERAGE
// ============================================================================
function RelationshipCoverage({ data }) {
  const coverage = data?.coverage_percent || 0;
  
  return (
    <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '20px', border: `1px solid ${colors.border}` }}>
      <Tooltip 
        title="Table Relationships" 
        detail="Shows how well tables are connected via detected foreign keys and column matches. Higher coverage enables better cross-table queries."
        action="80%+ = optimal for intelligent joins"
      >
        <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'help' }}>
          <Link2 size={16} color={colors.primary} />
          Table Relationships
        </h3>
      </Tooltip>
      
      {/* Coverage Bar */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
          <span style={{ fontSize: '12px', color: colors.textMuted }}>Coverage</span>
          <span style={{ fontSize: '12px', fontWeight: 500, color: coverage >= 80 ? colors.success : coverage >= 50 ? colors.warning : colors.error }}>
            {coverage}%
          </span>
        </div>
        <div style={{ height: '8px', backgroundColor: colors.background, borderRadius: '4px', overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${coverage}%`,
            backgroundColor: coverage >= 80 ? colors.success : coverage >= 50 ? colors.warning : colors.error,
            borderRadius: '4px',
            transition: 'width 0.3s ease'
          }} />
        </div>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        <Tooltip title="Connected Tables" detail="Tables that have at least one detected relationship to another table. These can be joined intelligently in queries." position="bottom">
          <div style={{ padding: '12px', backgroundColor: colors.background, borderRadius: '8px', cursor: 'help' }}>
            <div style={{ fontSize: '18px', fontWeight: 600, color: colors.success }}>{data?.tables_with_relationships || 0}</div>
            <div style={{ fontSize: '11px', color: colors.textMuted }}>Connected Tables</div>
          </div>
        </Tooltip>
        <Tooltip title="Orphaned Tables" detail="Tables with no detected relationships. These can still be queried individually but won't be joined automatically." position="bottom">
          <div style={{ padding: '12px', backgroundColor: colors.background, borderRadius: '8px', cursor: 'help' }}>
            <div style={{ fontSize: '18px', fontWeight: 600, color: data?.tables_orphaned > 0 ? colors.warning : colors.success }}>
              {data?.tables_orphaned || 0}
            </div>
            <div style={{ fontSize: '11px', color: colors.textMuted }}>Orphaned Tables</div>
          </div>
        </Tooltip>
      </div>
      
      <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '12px', color: colors.textMuted }}>
          {data?.total_relationships || 0} relationships detected
        </span>
        {data?.tables_orphaned > 0 && (
          <span style={{ fontSize: '11px', color: colors.warning }}>
            ⚠ {data.tables_orphaned} tables need relationships
          </span>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// ATTENTION ITEMS
// ============================================================================
function AttentionItems({ items }) {
  const severityStyles = {
    error: { bg: `${colors.error}10`, border: colors.error, icon: XCircle },
    warning: { bg: `${colors.warning}10`, border: colors.warning, icon: AlertTriangle },
    info: { bg: `${colors.accent}10`, border: colors.accent, icon: Bell },
  };
  
  if (!items || items.length === 0) {
    return (
      <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '20px', border: `1px solid ${colors.border}` }}>
        <Tooltip 
          title="Attention Required" 
          detail="Monitors for issues that need action: failed uploads, stuck processing jobs, tables missing column profiles, unclassified data."
          action="Green = no issues detected"
        >
          <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'help' }}>
            <Bell size={16} color={colors.primary} />
            Attention Required
          </h3>
        </Tooltip>
        <div style={{ 
          padding: '24px', 
          textAlign: 'center', 
          backgroundColor: `${colors.success}08`, 
          borderRadius: '8px',
          border: `1px solid ${colors.success}30`
        }}>
          <CheckCircle size={24} color={colors.success} style={{ marginBottom: '8px' }} />
          <div style={{ fontSize: '13px', fontWeight: 500, color: colors.success }}>All Clear</div>
          <div style={{ fontSize: '11px', color: colors.textMuted, marginTop: '4px' }}>No issues require attention</div>
        </div>
      </div>
    );
  }
  
  return (
    <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '20px', border: `1px solid ${colors.border}` }}>
      <Tooltip 
        title="Attention Required" 
        detail="Issues that need your action: failed uploads, stuck processing jobs, tables missing column profiles, unclassified data."
        action="Click items to resolve"
      >
        <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'help' }}>
          <Bell size={16} color={colors.primary} />
          Attention Required
          <span style={{ 
            marginLeft: 'auto', 
            fontSize: '11px', 
            padding: '2px 8px', 
            borderRadius: '10px',
            backgroundColor: colors.warning,
            color: colors.white
          }}>
            {items.length}
          </span>
        </h3>
      </Tooltip>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {items.map((item, i) => {
          const style = severityStyles[item.severity] || severityStyles.info;
          const Icon = style.icon;
          
          return (
            <div key={i} style={{
              padding: '10px 12px',
              backgroundColor: style.bg,
              borderLeft: `3px solid ${style.border}`,
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px'
            }}>
              <Icon size={16} color={style.border} style={{ marginTop: '2px' }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '12px', fontWeight: 500, color: colors.text }}>{item.message}</div>
                {item.detail && (
                  <div style={{ fontSize: '11px', color: colors.textMuted, marginTop: '2px' }}>{item.detail}</div>
                )}
              </div>
              {item.time && (
                <span style={{ fontSize: '10px', color: colors.textMuted }}>{formatTimeAgo(item.time)}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// ACTIVITY CHART (Simple Sparkline)
// ============================================================================
function ActivityChart({ data }) {
  const uploads = data?.uploads_by_day || [];
  const queries = data?.queries_by_day || [];
  
  // Get max value for scaling
  const allValues = [
    ...uploads.map(d => d.total || 0),
    ...queries.map(d => d.count || 0)
  ];
  const maxVal = Math.max(...allValues, 1);
  
  // Recent 14 days
  const recentUploads = uploads.slice(-14);
  const recentQueries = queries.slice(-14);
  
  const totalUploads = uploads.reduce((sum, d) => sum + (d.total || 0), 0);
  const totalQueries = queries.reduce((sum, d) => sum + (d.count || 0), 0);
  
  return (
    <div style={{ backgroundColor: colors.cardBg, borderRadius: '12px', padding: '20px', border: `1px solid ${colors.border}` }}>
      <Tooltip 
        title="Activity History" 
        detail="Historical view of platform usage over the past 30 days. Uploads track file processing jobs, Queries track intelligence engine usage."
        action="Hover bars for daily counts"
      >
        <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'help' }}>
          <BarChart3 size={16} color={colors.primary} />
          Activity History
          <span style={{ marginLeft: 'auto', fontSize: '11px', color: colors.textMuted }}>Last 30 days</span>
        </h3>
      </Tooltip>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Uploads */}
        <div>
          <Tooltip title="Uploads" detail="File processing jobs completed. Orange bars indicate days with failed uploads." position="bottom">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', cursor: 'help' }}>
              <span style={{ fontSize: '12px', color: colors.textMuted }}>Uploads</span>
              <span style={{ fontSize: '14px', fontWeight: 600, color: colors.accent }}>{totalUploads}</span>
            </div>
          </Tooltip>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height: '40px' }}>
            {recentUploads.length > 0 ? recentUploads.map((d, i) => (
              <div
                key={i}
                style={{
                  flex: 1,
                  height: `${Math.max(4, (d.total / maxVal) * 40)}px`,
                  backgroundColor: d.failed > 0 ? colors.warning : colors.accent,
                  borderRadius: '2px',
                  opacity: 0.8
                }}
                title={`${d.date}: ${d.total} uploads (${d.failed || 0} failed)`}
              />
            )) : (
              <div style={{ width: '100%', textAlign: 'center', color: colors.textMuted, fontSize: '11px', paddingTop: '10px' }}>
                No upload data
              </div>
            )}
          </div>
        </div>
        
        {/* Queries */}
        <div>
          <Tooltip title="Queries" detail="Intelligence engine queries from chat. Each bar represents questions asked that day." position="bottom">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', cursor: 'help' }}>
              <span style={{ fontSize: '12px', color: colors.textMuted }}>Queries</span>
              <span style={{ fontSize: '14px', fontWeight: 600, color: colors.primary }}>{totalQueries}</span>
            </div>
          </Tooltip>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height: '40px' }}>
            {recentQueries.length > 0 ? recentQueries.map((d, i) => (
              <div
                key={i}
                style={{
                  flex: 1,
                  height: `${Math.max(4, (d.count / maxVal) * 40)}px`,
                  backgroundColor: colors.primary,
                  borderRadius: '2px',
                  opacity: 0.8
                }}
                title={`${d.date}: ${d.count} queries`}
              />
            )) : (
              <div style={{ width: '100%', textAlign: 'center', color: colors.textMuted, fontSize: '11px', paddingTop: '10px' }}>
                No query data
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN DASHBOARD
// ============================================================================
export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  
  const fetchData = useCallback(async (force = false) => {
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/dashboard${force ? '?force=true' : ''}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setLastRefresh(new Date());
    } catch (err) {
      console.error('Dashboard fetch failed:', err);
      setError(err.message);
    }
    
    setLoading(false);
  }, []);
  
  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(), 30000);
    return () => clearInterval(interval);
  }, [fetchData]);
  
  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <h1 style={{ 
            margin: 0, 
            fontSize: '20px', 
            fontWeight: 600, 
            color: colors.text, 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px',
            fontFamily: "'Sora', sans-serif"
          }}>
            <div style={{ 
              width: '36px', 
              height: '36px', 
              borderRadius: '10px', 
              backgroundColor: colors.primary, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}>
              <Target size={20} color={colors.white} />
            </div>
            Mission Control
          </h1>
          <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: colors.textMuted }}>
            Real-time platform intelligence • Updated {lastRefresh.toLocaleTimeString()}
            {data?._cached && <span style={{ marginLeft: '8px', color: colors.warning }}>(cached)</span>}
          </p>
        </div>
        <button 
          onClick={() => fetchData(true)} 
          disabled={loading}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            padding: '10px 16px', 
            backgroundColor: colors.primary, 
            color: colors.white, 
            border: 'none', 
            borderRadius: '8px', 
            fontSize: '13px', 
            fontWeight: 500, 
            cursor: loading ? 'wait' : 'pointer',
            opacity: loading ? 0.7 : 1
          }}
        >
          <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>
      
      {error && (
        <div style={{ 
          padding: '12px 16px', 
          backgroundColor: `${colors.error}10`, 
          border: `1px solid ${colors.error}30`,
          borderRadius: '8px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <XCircle size={16} color={colors.error} />
          <span style={{ fontSize: '13px', color: colors.error }}>Failed to load dashboard: {error}</span>
        </div>
      )}
      
      {/* Pipeline Status - Full Width */}
      <div style={{ marginBottom: '16px' }}>
        <PipelineStatus data={data?.pipeline_status} />
      </div>
      
      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
        <DataByTruthType data={data?.data_summary} />
        <AttentionItems items={data?.attention} />
      </div>
      
      {/* Lineage & Relationships */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px', marginBottom: '16px' }}>
        <LineageTracking data={data?.lineage} />
        <RelationshipCoverage data={data?.relationships} />
      </div>
      
      {/* Activity Chart */}
      <ActivityChart data={data?.activity} />
      
      {/* Response Time Footer */}
      {data?._meta?.response_time_ms && (
        <div style={{ 
          marginTop: '16px', 
          textAlign: 'right', 
          fontSize: '11px', 
          color: colors.textMuted 
        }}>
          Dashboard loaded in {data._meta.response_time_ms}ms
        </div>
      )}
      
      <style>{`
        @keyframes spin { 
          from { transform: rotate(0deg); } 
          to { transform: rotate(360deg); } 
        }
        .spin { animation: spin 1s linear infinite; }
      `}</style>
    </div>
  );
}
