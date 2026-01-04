/**
 * DataModelPage.jsx - Relationship Verification & Management
 * ===========================================================
 * 
 * View, verify, and manage table relationships.
 * 
 * Features:
 * - Left panel: Filterable relationship list
 * - Right panel: Two-table detail view with verification status
 * - Sample data display with join column highlighting
 * - Orphan value detection
 * - Confirm/Reject/Edit actions
 * 
 * Connected to:
 * - GET /api/data-model/projects - List projects with data
 * - GET /api/data-model/relationships/{project} - Get relationships
 * - POST /api/data-model/analyze/{project} - Detect relationships
 * - POST /api/data-model/test-relationship - Verify a relationship
 * - POST /api/data-model/relationships/{project}/confirm - Confirm/reject
 * 
 * Deploy to: frontend/src/pages/DataModelPage.jsx
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, RefreshCw, CheckCircle, AlertTriangle, XCircle, 
  Loader2, ChevronDown, ChevronRight, Database, Link2, 
  GitBranch, Eye, Edit2, Trash2, Search, Filter, Sparkles
} from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import { Tooltip } from '../components/ui';
import api from '../services/api';

// ============================================================================
// BRAND COLORS (from Mission Control)
// ============================================================================
const brandColors = {
  primary: '#83b16d',
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
  success: '#285390',
};

// Status configuration
const statusConfig = {
  good: { 
    color: brandColors.primary, 
    bgColor: 'rgba(131, 177, 109, 0.15)', 
    label: 'GOOD',
    icon: CheckCircle,
    description: 'Strong relationship with high match rate'
  },
  partial: { 
    color: brandColors.warning, 
    bgColor: 'rgba(217, 119, 6, 0.15)', 
    label: 'PARTIAL',
    icon: AlertTriangle,
    description: 'Relationship exists but has orphan records'
  },
  weak: { 
    color: brandColors.scarletSage, 
    bgColor: 'rgba(153, 60, 68, 0.15)', 
    label: 'WEAK',
    icon: AlertTriangle,
    description: 'Low match rate - review if tables should be joined'
  },
  none: { 
    color: '#ef4444', 
    bgColor: 'rgba(239, 68, 68, 0.15)', 
    label: 'NO MATCH',
    icon: XCircle,
    description: 'No matching keys found between tables'
  },
  unknown: { 
    color: brandColors.textMuted, 
    bgColor: 'rgba(100, 116, 139, 0.15)', 
    label: 'UNKNOWN',
    icon: Search,
    description: 'Not yet tested'
  }
};

const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

// ============================================================================
// RELATIONSHIP LIST ITEM
// ============================================================================
function RelationshipListItem({ rel, selected, onClick }) {
  const status = rel.verification_status || 'unknown';
  const cfg = statusConfig[status] || statusConfig.unknown;
  const Icon = cfg.icon;
  
  return (
    <div
      onClick={onClick}
      style={{
        padding: '12px 16px',
        borderBottom: `1px solid ${brandColors.border}`,
        cursor: 'pointer',
        backgroundColor: selected ? brandColors.background : 'transparent',
        borderLeft: selected ? `3px solid ${brandColors.accent}` : '3px solid transparent',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={(e) => !selected && (e.currentTarget.style.backgroundColor = brandColors.background)}
      onMouseLeave={(e) => !selected && (e.currentTarget.style.backgroundColor = 'transparent')}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span style={{ 
          fontSize: '11px', 
          padding: '2px 8px', 
          borderRadius: '4px',
          backgroundColor: cfg.bgColor,
          color: cfg.color,
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '4px'
        }}>
          <Icon size={12} />
          {rel.match_rate != null ? `${rel.match_rate}%` : cfg.label}
        </span>
        <span style={{ fontSize: '11px', color: cfg.color, fontWeight: 500 }}>{cfg.label}</span>
      </div>
      <div style={{ fontSize: '13px', fontWeight: 500, color: brandColors.text, marginBottom: '2px' }}>
        {rel.source_table?.split('__').pop() || rel.source_table}
      </div>
      <div style={{ fontSize: '11px', color: brandColors.textMuted }}>
        ↓ {rel.source_column} → {rel.target_column}
      </div>
      <div style={{ fontSize: '13px', color: brandColors.textMuted }}>
        {rel.target_table?.split('__').pop() || rel.target_table}
      </div>
    </div>
  );
}

// ============================================================================
// STAT CARD
// ============================================================================
function StatCard({ label, value, color, tooltip }) {
  const content = (
    <div style={{
      backgroundColor: brandColors.cardBg,
      borderRadius: '8px',
      padding: '16px',
      textAlign: 'center',
      border: `1px solid ${brandColors.border}`,
    }}>
      <div style={{ fontSize: '24px', fontWeight: 700, color: color || brandColors.text }}>{value}</div>
      <div style={{ fontSize: '11px', color: brandColors.textMuted, marginTop: '4px' }}>{label}</div>
    </div>
  );
  
  if (tooltip) {
    return (
      <Tooltip title={tooltip.title} detail={tooltip.detail} action={tooltip.action}>
        {content}
      </Tooltip>
    );
  }
  return content;
}

// ============================================================================
// SAMPLE DATA TABLE
// ============================================================================
function SampleDataTable({ title, rows, columns, joinColumn, rowCount, orphanValues = [] }) {
  const c = brandColors;
  const displayCols = columns?.slice(0, 6) || [];
  
  return (
    <div style={{
      backgroundColor: c.cardBg,
      borderRadius: '8px',
      overflow: 'hidden',
      border: `1px solid ${c.border}`,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: `1px solid ${c.border}`,
        backgroundColor: c.background,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: c.text }}>{title}</div>
          <div style={{ fontSize: '11px', color: c.textMuted }}>{rowCount?.toLocaleString() || 0} rows</div>
        </div>
        {joinColumn && (
          <Tooltip title="Join Column" detail={`This column is used to match records between tables.`}>
            <span style={{
              fontSize: '11px',
              padding: '4px 8px',
              backgroundColor: 'rgba(39, 102, 177, 0.15)',
              color: c.electricBlue,
              borderRadius: '4px',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}>
              <Link2 size={12} /> {joinColumn}
            </span>
          </Tooltip>
        )}
      </div>
      
      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: c.background }}>
              {displayCols.map((col, i) => (
                <th key={i} style={{
                  textAlign: 'left',
                  padding: '8px 12px',
                  fontWeight: 500,
                  color: col.toLowerCase() === joinColumn?.toLowerCase() ? c.electricBlue : c.textMuted,
                  borderBottom: `1px solid ${c.border}`,
                }}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows?.slice(0, 8).map((row, i) => {
              const keyValue = row[joinColumn];
              const isOrphan = orphanValues.includes(keyValue);
              return (
                <tr key={i} style={{ backgroundColor: isOrphan ? 'rgba(249, 115, 22, 0.1)' : 'transparent' }}>
                  {displayCols.map((col, j) => (
                    <td key={j} style={{
                      padding: '8px 12px',
                      borderBottom: `1px solid ${c.border}`,
                      color: col.toLowerCase() === joinColumn?.toLowerCase() 
                        ? (isOrphan ? c.warning : c.electricBlue) 
                        : c.text,
                      fontWeight: col.toLowerCase() === joinColumn?.toLowerCase() ? 500 : 400,
                    }}>
                      {row[col] ?? '—'}
                      {isOrphan && col.toLowerCase() === joinColumn?.toLowerCase() && ' '}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      
      {(!rows || rows.length === 0) && (
        <div style={{ padding: '24px', textAlign: 'center', color: c.textMuted }}>
          No sample data available
        </div>
      )}
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function DataModelPage() {
  const c = brandColors;
  const { selectedProject } = useProject();
  
  // State
  const [relationships, setRelationships] = useState([]);
  const [selectedRel, setSelectedRel] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [filter, setFilter] = useState('all');
  const [error, setError] = useState(null);
  
  // Load relationships
  const loadRelationships = useCallback(async () => {
    if (!selectedProject) {
      setRelationships([]);
      setLoading(false);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/api/data-model/relationships/${encodeURIComponent(selectedProject)}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setRelationships(data.relationships || []);
    } catch (err) {
      console.error('Failed to load relationships:', err);
      setError('Failed to load relationships');
      setRelationships([]);
    } finally {
      setLoading(false);
    }
  }, [selectedProject]);
  
  useEffect(() => {
    loadRelationships();
  }, [loadRelationships]);
  
  // Test a relationship
  const testRelationship = async (rel) => {
    setTesting(true);
    setTestResult(null);
    
    try {
      const response = await fetch(`${API_BASE}/api/data-model/test-relationship`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_a: rel.source_table,
          table_b: rel.target_table,
          project: selectedProject,
          sample_limit: 10
        })
      });
      
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setTestResult(data);
      
      // Update the relationship with verification status
      setRelationships(prev => prev.map(r => 
        r.id === rel.id 
          ? { ...r, verification_status: data.verification?.status, match_rate: data.statistics?.match_rate_percent }
          : r
      ));
      
    } catch (err) {
      console.error('Failed to test relationship:', err);
      setTestResult({ error: err.message });
    } finally {
      setTesting(false);
    }
  };
  
  // Analyze project
  const analyzeProject = async () => {
    if (!selectedProject) return;
    
    setAnalyzing(true);
    try {
      const response = await fetch(`${API_BASE}/api/data-model/analyze/${encodeURIComponent(selectedProject)}`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await loadRelationships();
    } catch (err) {
      console.error('Failed to analyze:', err);
      setError('Failed to analyze project');
    } finally {
      setAnalyzing(false);
    }
  };
  
  // Confirm/Reject relationship
  const updateRelationship = async (rel, action) => {
    try {
      const response = await fetch(`${API_BASE}/api/data-model/relationships/${encodeURIComponent(selectedProject)}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_table: rel.source_table,
          source_column: rel.source_column,
          target_table: rel.target_table,
          target_column: rel.target_column,
          confirmed: action === 'confirm'
        })
      });
      
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await loadRelationships();
    } catch (err) {
      console.error('Failed to update relationship:', err);
    }
  };
  
  // Select relationship and test it
  const handleSelectRelationship = (rel) => {
    setSelectedRel(rel);
    testRelationship(rel);
  };
  
  // Filter relationships
  const filteredRels = filter === 'all' 
    ? relationships 
    : relationships.filter(r => (r.verification_status || 'unknown') === filter);
  
  // Get current status config
  const currentStatus = testResult?.verification?.status || selectedRel?.verification_status || 'unknown';
  const currentConfig = statusConfig[currentStatus] || statusConfig.unknown;
  const StatusIcon = currentConfig.icon;
  
  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: c.background, 
      display: 'flex', 
      flexDirection: 'column' 
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px',
        backgroundColor: c.cardBg,
        borderBottom: `1px solid ${c.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Link 
            to="/data" 
            style={{ 
              display: 'inline-flex', 
              alignItems: 'center', 
              gap: '6px', 
              color: c.textMuted, 
              textDecoration: 'none', 
              fontSize: '13px' 
            }}
          >
            <ArrowLeft size={16} /> Back to Data
          </Link>
          
          <div style={{ width: '1px', height: '24px', backgroundColor: c.border }} />
          
          <div>
            <h1 style={{ 
              margin: 0, 
              fontSize: '20px', 
              fontWeight: 600, 
              color: c.text, 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px',
              fontFamily: "'Sora', sans-serif"
            }}>
              <div style={{ 
                width: '36px', 
                height: '36px', 
                borderRadius: '10px', 
                backgroundColor: c.primary, 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center' 
              }}>
                <GitBranch size={20} color="#ffffff" />
              </div>
              Data Model
            </h1>
            <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: c.textMuted }}>
              {selectedProject || 'No project selected'} • {relationships.length} relationships
            </p>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '8px' }}>
          <Tooltip title="Refresh" detail="Reload relationships from database">
            <button
              onClick={loadRelationships}
              disabled={loading}
              style={{
                padding: '8px 12px',
                backgroundColor: c.background,
                border: `1px solid ${c.border}`,
                borderRadius: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '13px',
                color: c.text,
              }}
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
          </Tooltip>
          
          <Tooltip title="Analyze Project" detail="Auto-detect relationships between all tables in this project" action="Creates new relationship entries">
            <button
              onClick={analyzeProject}
              disabled={analyzing || !selectedProject}
              style={{
                padding: '8px 16px',
                backgroundColor: c.primary,
                border: 'none',
                borderRadius: '6px',
                cursor: selectedProject ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '13px',
                color: 'white',
                fontWeight: 500,
                opacity: selectedProject ? 1 : 0.5,
              }}
            >
              {analyzing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              {analyzing ? 'Analyzing...' : 'Analyze'}
            </button>
          </Tooltip>
        </div>
      </div>
      
      {/* Main Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left Panel - Relationship List */}
        <div style={{
          width: '320px',
          backgroundColor: c.cardBg,
          borderRight: `1px solid ${c.border}`,
          display: 'flex',
          flexDirection: 'column',
        }}>
          {/* Filter Tabs */}
          <div style={{ padding: '12px 16px', borderBottom: `1px solid ${c.border}` }}>
            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
              {['all', 'good', 'partial', 'weak', 'none', 'unknown'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  style={{
                    padding: '4px 10px',
                    fontSize: '11px',
                    fontWeight: 500,
                    backgroundColor: filter === f ? c.accent : c.background,
                    color: filter === f ? 'white' : c.textMuted,
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>
          
          {/* List */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {loading ? (
              <div style={{ padding: '24px', textAlign: 'center', color: c.textMuted }}>
                <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 8px' }} />
                Loading relationships...
              </div>
            ) : filteredRels.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: c.textMuted }}>
                <Database size={32} style={{ opacity: 0.3, marginBottom: '8px' }} />
                <div>No relationships found</div>
                <div style={{ fontSize: '12px', marginTop: '4px' }}>
                  Click "Analyze" to detect relationships
                </div>
              </div>
            ) : (
              filteredRels.map(rel => (
                <RelationshipListItem
                  key={rel.id || `${rel.source_table}-${rel.target_table}`}
                  rel={rel}
                  selected={selectedRel?.id === rel.id || (selectedRel?.source_table === rel.source_table && selectedRel?.target_table === rel.target_table)}
                  onClick={() => handleSelectRelationship(rel)}
                />
              ))
            )}
          </div>
          
          {/* Summary Footer */}
          <div style={{
            padding: '12px 16px',
            borderTop: `1px solid ${c.border}`,
            fontSize: '11px',
            color: c.textMuted,
          }}>
            {relationships.length} relationships • 
            {relationships.filter(r => r.verification_status === 'good' || r.status === 'confirmed').length} confirmed
          </div>
        </div>
        
        {/* Right Panel - Detail View */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          {!selectedRel ? (
            <div style={{ 
              height: '100%', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              color: c.textMuted,
            }}>
              <div style={{ textAlign: 'center' }}>
                <Link2 size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
                <div style={{ fontSize: '16px', fontWeight: 500 }}>Select a relationship</div>
                <div style={{ fontSize: '13px', marginTop: '4px' }}>
                  Click a relationship on the left to view details and verify
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Status Banner */}
              <div style={{
                backgroundColor: currentConfig.bgColor,
                borderLeft: `4px solid ${currentConfig.color}`,
                borderRadius: '8px',
                padding: '16px 20px',
                marginBottom: '24px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '8px',
                      fontSize: '16px', 
                      fontWeight: 600, 
                      color: currentConfig.color,
                      marginBottom: '8px',
                    }}>
                      <StatusIcon size={20} />
                      {currentConfig.label}
                      {testResult?.statistics?.match_rate_percent != null && (
                        <span> — {testResult.statistics.match_rate_percent}% Match Rate</span>
                      )}
                    </div>
                    <div style={{ fontSize: '14px', color: c.text, marginBottom: '4px' }}>
                      <span style={{ color: c.electricBlue, fontWeight: 500 }}>{selectedRel.source_table?.split('__').pop()}</span>
                      <span style={{ margin: '0 8px', color: c.textMuted }}>→</span>
                      <span style={{ color: c.electricBlue, fontWeight: 500 }}>{selectedRel.target_table?.split('__').pop()}</span>
                    </div>
                    <div style={{ fontSize: '12px', color: c.textMuted }}>
                      Join: {testResult?.join_column_a || selectedRel.source_column} = {testResult?.join_column_b || selectedRel.target_column}
                      {selectedRel.confidence && ` • Confidence: ${(selectedRel.confidence * 100).toFixed(0)}%`}
                    </div>
                    {testResult?.verification?.message && (
                      <div style={{ fontSize: '12px', color: c.textMuted, marginTop: '8px', fontStyle: 'italic' }}>
                        {testResult.verification.message}
                      </div>
                    )}
                  </div>
                  
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <Tooltip title="Confirm Relationship" detail="Mark this relationship as verified and correct" action="Will be used for JOIN queries">
                      <button
                        onClick={() => updateRelationship(selectedRel, 'confirm')}
                        style={{
                          padding: '8px 16px',
                          backgroundColor: c.primary,
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '13px',
                          color: 'white',
                          fontWeight: 500,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <CheckCircle size={14} /> Confirm
                      </button>
                    </Tooltip>
                    
                    <Tooltip title="Reject Relationship" detail="Mark this relationship as incorrect" action="Will be excluded from JOIN queries">
                      <button
                        onClick={() => updateRelationship(selectedRel, 'reject')}
                        style={{
                          padding: '8px 16px',
                          backgroundColor: c.scarletSage,
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '13px',
                          color: 'white',
                          fontWeight: 500,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <XCircle size={14} /> Reject
                      </button>
                    </Tooltip>
                    
                    <Tooltip title="Re-test" detail="Run verification again to refresh statistics">
                      <button
                        onClick={() => testRelationship(selectedRel)}
                        disabled={testing}
                        style={{
                          padding: '8px 12px',
                          backgroundColor: c.background,
                          border: `1px solid ${c.border}`,
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '13px',
                          color: c.text,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        {testing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                      </button>
                    </Tooltip>
                  </div>
                </div>
              </div>
              
              {/* Stats Row */}
              {testResult?.statistics && (
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(4, 1fr)', 
                  gap: '16px',
                  marginBottom: '24px',
                }}>
                  <StatCard 
                    label="Matching Keys" 
                    value={testResult.statistics.matching_keys || 0}
                    color={c.primary}
                    tooltip={{
                      title: "Matching Keys",
                      detail: "Number of distinct key values that exist in both tables",
                      action: "Higher = stronger relationship"
                    }}
                  />
                  <StatCard 
                    label="Only in Source" 
                    value={testResult.statistics.orphans_in_a || 0}
                    color={testResult.statistics.orphans_in_a > 0 ? c.warning : c.textMuted}
                    tooltip={{
                      title: "Orphan Values in Source",
                      detail: "Key values in the source table that have no match in the target table",
                      action: "May indicate missing configuration or unused codes"
                    }}
                  />
                  <StatCard 
                    label="Only in Target" 
                    value={testResult.statistics.orphans_in_b || 0}
                    color={testResult.statistics.orphans_in_b > 0 ? c.warning : c.textMuted}
                    tooltip={{
                      title: "Orphan Values in Target",
                      detail: "Key values in the target table that have no match in the source table",
                      action: "May indicate data issues or new values"
                    }}
                  />
                  <StatCard 
                    label="Total Rows" 
                    value={((testResult.statistics.table_a_rows || 0) + (testResult.statistics.table_b_rows || 0)).toLocaleString()}
                    color={c.accent}
                    tooltip={{
                      title: "Total Row Count",
                      detail: "Combined rows across both tables",
                    }}
                  />
                </div>
              )}
              
              {/* Sample Data Tables */}
              {testing ? (
                <div style={{ padding: '48px', textAlign: 'center', color: c.textMuted }}>
                  <Loader2 size={32} className="animate-spin" style={{ margin: '0 auto 16px' }} />
                  Testing relationship...
                </div>
              ) : testResult ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                  <SampleDataTable
                    title={selectedRel.source_table?.split('__').pop() || 'Source Table'}
                    rows={testResult.table_a_sample}
                    columns={testResult.table_a_columns}
                    joinColumn={testResult.join_column_a}
                    rowCount={testResult.statistics?.table_a_rows}
                    orphanValues={testResult.statistics?.orphan_samples_from_a || []}
                  />
                  <SampleDataTable
                    title={selectedRel.target_table?.split('__').pop() || 'Target Table'}
                    rows={testResult.table_b_sample}
                    columns={testResult.table_b_columns}
                    joinColumn={testResult.join_column_b}
                    rowCount={testResult.statistics?.table_b_rows}
                  />
                </div>
              ) : null}
              
              {/* Orphan Values Detail */}
              {testResult?.statistics?.orphan_samples_from_a?.length > 0 && (
                <div style={{
                  backgroundColor: c.cardBg,
                  borderRadius: '8px',
                  padding: '16px',
                  border: `1px solid ${c.border}`,
                  marginBottom: '24px',
                }}>
                  <div style={{ 
                    fontSize: '14px', 
                    fontWeight: 600, 
                    color: c.warning, 
                    marginBottom: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}>
                    <AlertTriangle size={16} />
                    Orphan Values ({testResult.statistics.orphans_in_a} codes in source not found in target)
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {testResult.statistics.orphan_samples_from_a.map((val, i) => (
                      <span key={i} style={{
                        padding: '4px 12px',
                        backgroundColor: 'rgba(249, 115, 22, 0.15)',
                        color: c.warning,
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontFamily: 'monospace',
                      }}>
                        {val}
                      </span>
                    ))}
                  </div>
                  <div style={{ fontSize: '11px', color: c.textMuted, marginTop: '12px' }}>
                    These values exist in the configuration but have no matching transactions. 
                    They may be unused codes or indicate a mapping issue.
                  </div>
                </div>
              )}
              
              {/* Join SQL Preview */}
              {testResult?.join_sql && (
                <div style={{
                  backgroundColor: c.cardBg,
                  borderRadius: '8px',
                  border: `1px solid ${c.border}`,
                  overflow: 'hidden',
                }}>
                  <div style={{
                    padding: '12px 16px',
                    backgroundColor: c.background,
                    borderBottom: `1px solid ${c.border}`,
                    fontSize: '12px',
                    fontWeight: 600,
                    color: c.textMuted,
                  }}>
                    Generated JOIN SQL
                  </div>
                  <pre style={{
                    margin: 0,
                    padding: '16px',
                    fontSize: '11px',
                    fontFamily: 'monospace',
                    color: c.text,
                    whiteSpace: 'pre-wrap',
                    backgroundColor: 'rgba(0,0,0,0.02)',
                  }}>
                    {testResult.join_sql}
                  </pre>
                </div>
              )}
            </>
          )}
        </div>
      </div>
      
      {/* CSS for animations */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
}
