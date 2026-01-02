/**
 * DataExplorer.jsx - COMPLETE FIX
 * ================================
 * 
 * Fixed: Relationship editor dropdowns now properly fetch and display columns.
 * 
 * The core issue was that `tables` array was loaded with `columns: []` and
 * never populated. Now:
 * 1. Added `tableSchemas` state to cache column data
 * 2. RelationshipEditor fetches columns on-demand when expanding/editing
 * 3. Dropdowns populate from cached schema data
 * 
 * Updated: December 29, 2025
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  Database, FileSpreadsheet, FileText, Link2, Heart, ChevronDown, ChevronRight, ChevronUp,
  ArrowLeft, RefreshCw, CheckCircle, AlertTriangle, XCircle, Key, Loader2,
  Shield, Play, Folder, BookOpen, Code, Trash2, Edit3, Sparkles, Eye, Edit2
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useProject } from '../context/ProjectContext';
import api from '../services/api';

// NEW: Import ClassificationPanel
import ClassificationPanel, { ChunkPanel } from '../components/ClassificationPanel';

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

// ============================================================================
// TOOLTIP COMPONENT (from Mission Control)
// ============================================================================
function Tooltip({ children, title, detail, action }) {
  const [show, setShow] = useState(false);
  
  return (
    <div 
      style={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={() => setShow(true)} 
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <div style={{
          position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
          marginBottom: '8px', padding: '12px 16px', backgroundColor: brandColors.text, color: brandColors.white,
          borderRadius: '8px', fontSize: '12px', width: '260px', zIndex: 1000,
          boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
        }}>
          <div style={{ fontWeight: 600, marginBottom: '4px' }}>{title}</div>
          <div style={{ opacity: 0.85, lineHeight: 1.4 }}>{detail}</div>
          {action && (
            <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.2)', color: brandColors.skyBlue, fontWeight: 500 }}>
              💡 {action}
            </div>
          )}
          <div style={{ position: 'absolute', bottom: '-6px', left: '50%', transform: 'translateX(-50%)',
            width: 0, height: 0, borderLeft: '6px solid transparent', borderRight: '6px solid transparent', 
            borderTop: `6px solid ${brandColors.text}` }} />
        </div>
      )}
    </div>
  );
}

// ============================================================================
// STATUS CONFIG for relationship verification
// ============================================================================
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
    label: 'UNTESTED',
    icon: Eye,
    description: 'Click to test and verify'
  }
};

// ============================================================================
// DATA MODEL PANEL - Replaces RelationshipEditor with verification UI
// ============================================================================
function DataModelPanel({ relationships, tables, c, projectName, onConfirm, onReload }) {
  const [selectedRel, setSelectedRel] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);
  const [filter, setFilter] = useState('all');
  const [analyzing, setAnalyzing] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState({});

  // Toggle group expansion
  const toggleGroup = (groupKey) => {
    setExpandedGroups(prev => ({ ...prev, [groupKey]: !prev[groupKey] }));
  };

  // Test a relationship
  const testRelationship = async (rel) => {
    setTesting(true);
    setTestResult(null);
    
    try {
      const sourceTable = rel.source_table || rel.from_table;
      const targetTable = rel.target_table || rel.to_table;
      
      const response = await api.post('/data-model/test-relationship', {
        table_a: sourceTable,
        table_b: targetTable,
        project: projectName,
        sample_limit: 10
      });
      
      setTestResult(response.data);
    } catch (err) {
      console.error('Failed to test relationship:', err);
      setTestResult({ error: err.message });
    } finally {
      setTesting(false);
    }
  };

  // Analyze project to detect relationships
  const analyzeProject = async () => {
    if (!projectName) return;
    setAnalyzing(true);
    try {
      await api.post(`/data-model/analyze/${encodeURIComponent(projectName)}`);
      if (onReload) onReload();
    } catch (err) {
      console.error('Failed to analyze:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  // Select and test relationship
  const handleSelect = (rel) => {
    setSelectedRel(rel);
    testRelationship(rel);
  };

  // Get display name for table - extracts the friendly part from full table name
  const getDisplayName = (tableName) => {
    if (!tableName) return '?';
    
    // Check if we have this table in our tables array with a display_name
    const tableInfo = tables?.find(t => t.table_name === tableName);
    if (tableInfo?.display_name) {
      return tableInfo.display_name;
    }
    
    // Extract from table name: project_filename_sheetname
    // Pattern: tea1000_team_configuration_validation_for_brande_company_information_component_company_information_r
    // We want the last meaningful segment(s)
    const parts = tableName.split('_');
    
    // Skip project prefix (first part that looks like a project code)
    let startIdx = 0;
    if (parts[0]?.match(/^[a-z]+\d+$/i)) {
      startIdx = 1;
    }
    
    // Try to find where the actual sheet name starts
    // Usually after repeated words like "for_brande" or "validation"
    const remaining = parts.slice(startIdx);
    
    // Take last 3-4 meaningful words, capitalize them
    const meaningful = remaining.slice(-4).filter(p => p.length > 1);
    if (meaningful.length > 0) {
      return meaningful.map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    }
    
    return tableName.split('__').pop() || tableName;
  };

  // Get truncated full table name for display
  const getTruncatedName = (tableName, maxLen = 50) => {
    if (!tableName) return '';
    if (tableName.length <= maxLen) return tableName;
    return tableName.substring(0, maxLen - 3) + '...';
  };

  // Filter relationships
  const filteredRels = filter === 'all' 
    ? relationships 
    : relationships.filter(r => (r.verification_status || 'unknown') === filter);

  // Current status
  const currentStatus = testResult?.verification?.status || selectedRel?.verification_status || 'unknown';
  const currentConfig = statusConfig[currentStatus] || statusConfig.unknown;
  const StatusIcon = currentConfig.icon;

  return (
    <div style={{ display: 'flex', gap: '1rem', minHeight: '500px' }}>
      {/* Left Panel - List */}
      <div style={{ 
        width: '320px', 
        flexShrink: 0,
        border: `1px solid ${c.border}`, 
        borderRadius: 8, 
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header with Analyze button */}
        <div style={{ 
          padding: '12px 16px', 
          borderBottom: `1px solid ${c.border}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: c.background
        }}>
          <span style={{ fontWeight: 600, fontSize: '0.9rem', color: c.text }}>
            Relationships ({relationships?.length || 0})
          </span>
          <Tooltip title="Analyze Tables" detail="Auto-detect relationships between all tables in this project" action="Creates new relationship entries">
            <button
              onClick={analyzeProject}
              disabled={analyzing}
              style={{
                padding: '6px 12px',
                background: c.primary,
                color: 'white',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              {analyzing ? <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> : <Sparkles size={12} />}
              {analyzing ? 'Analyzing...' : 'Analyze'}
            </button>
          </Tooltip>
        </div>

        {/* Filter Tabs */}
        <div style={{ padding: '8px 12px', borderBottom: `1px solid ${c.border}`, display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
          {['all', 'good', 'partial', 'weak', 'unknown'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '3px 8px',
                fontSize: '0.7rem',
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

        {/* List - Grouped by Source File (Analytics-style) */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {filteredRels.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
              <Link2 size={32} style={{ opacity: 0.3, marginBottom: '8px' }} />
              <div style={{ fontSize: '0.85rem' }}>No relationships found</div>
              <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>Click "Analyze" to detect</div>
            </div>
          ) : (
            // Group relationships by source FILE (like Analytics)
            (() => {
              // Build lookup: table_name -> file info
              const tableToFile = {};
              (tables || []).forEach(t => {
                if (t.table_name) {
                  tableToFile[t.table_name] = {
                    filename: t.filename || 'Unknown Source',
                    display_name: t.display_name || t.table_name
                  };
                }
              });
              
              // Group by source file
              const fileGroups = {};
              filteredRels.forEach(rel => {
                const sourceTable = rel.source_table || rel.from_table || '?';
                const fileInfo = tableToFile[sourceTable] || { filename: 'Unknown Source' };
                const fileName = fileInfo.filename;
                
                if (!fileGroups[fileName]) {
                  fileGroups[fileName] = { 
                    fileName, 
                    shortName: fileName.length > 35 ? fileName.substring(0, 32) + '...' : fileName,
                    rels: [] 
                  };
                }
                fileGroups[fileName].rels.push(rel);
              });
              
              return Object.values(fileGroups).map(group => {
                const isExpanded = expandedGroups[group.fileName] === true; // Default collapsed
                
                return (
                  <div key={group.fileName} style={{ borderBottom: `1px solid ${c.border}` }}>
                    {/* File Header - Analytics style */}
                    <button
                      onClick={() => toggleGroup(group.fileName)}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        background: 'transparent',
                        border: 'none',
                        borderLeft: `3px solid ${c.primary}`,
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'background 0.15s',
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = c.background}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <div style={{ 
                        width: 24, height: 24, borderRadius: 4, 
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: 'white', border: `1px solid ${c.border}`
                      }}>
                        <FileText size={12} style={{ color: c.textMuted }} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={group.fileName}>
                          {group.shortName}
                        </div>
                        <div style={{ fontSize: '0.65rem', color: c.textMuted }}>{group.rels.length} relationship{group.rels.length !== 1 ? 's' : ''}</div>
                      </div>
                      {isExpanded ? (
                        <ChevronDown size={14} style={{ color: c.textMuted }} />
                      ) : (
                        <ChevronRight size={14} style={{ color: c.textMuted }} />
                      )}
                    </button>
                    
                    {/* Relationships within File */}
                    {isExpanded && (
                      <div style={{ background: `${c.background}50` }}>
                        {group.rels.map((rel, idx) => {
                          const sourceTable = rel.source_table || rel.from_table || '?';
                          const targetTable = rel.target_table || rel.to_table || '?';
                          const sourceCol = rel.source_column || rel.from_column || '?';
                          const targetCol = rel.target_column || rel.to_column || '?';
                          const status = rel.verification_status || 'unknown';
                          const cfg = statusConfig[status] || statusConfig.unknown;
                          const isSelected = selectedRel && (
                            (selectedRel.source_table === sourceTable && selectedRel.target_table === targetTable) ||
                            (selectedRel.from_table === sourceTable && selectedRel.to_table === targetTable)
                          );

                          return (
                            <button
                              key={rel.id || idx}
                              onClick={() => handleSelect(rel)}
                              style={{
                                width: '100%',
                                padding: '8px 12px 8px 44px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                background: isSelected ? `${c.accent}15` : 'transparent',
                                border: 'none',
                                borderTop: `1px solid ${c.border}`,
                                borderLeft: isSelected ? `3px solid ${c.accent}` : '3px solid transparent',
                                cursor: 'pointer',
                                textAlign: 'left',
                                transition: 'background 0.15s',
                              }}
                              onMouseEnter={(e) => !isSelected && (e.currentTarget.style.background = c.background)}
                              onMouseLeave={(e) => !isSelected && (e.currentTarget.style.background = 'transparent')}
                            >
                              <Database size={10} style={{ color: c.textMuted, flexShrink: 0 }} />
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 500, color: isSelected ? c.accent : c.text }}>
                                  {getDisplayName(sourceTable)} → {getDisplayName(targetTable)}
                                </div>
                                <div style={{ fontSize: '0.6rem', color: c.textMuted }}>
                                  {sourceCol} = {targetCol}
                                </div>
                              </div>
                              <span style={{ 
                                fontSize: '0.55rem', 
                                padding: '2px 5px', 
                                borderRadius: '3px',
                                backgroundColor: cfg.bgColor,
                                color: cfg.color,
                                fontWeight: 600,
                                flexShrink: 0,
                              }}>
                                {rel.match_rate != null ? `${rel.match_rate}%` : cfg.label}
                              </span>
                              {rel.confirmed && (
                                <CheckCircle size={10} style={{ color: c.success, flexShrink: 0 }} />
                              )}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              });
            })()
          )}
        </div>
      </div>

      {/* Right Panel - Detail */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {!selectedRel ? (
          <div style={{ 
            height: '100%', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            border: `1px solid ${c.border}`,
            borderRadius: 8,
            color: c.textMuted,
          }}>
            <div style={{ textAlign: 'center' }}>
              <Link2 size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
              <div style={{ fontSize: '1rem', fontWeight: 500 }}>Select a relationship</div>
              <div style={{ fontSize: '0.85rem', marginTop: '4px' }}>
                Click one on the left to test and verify
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Status Banner */}
            <div style={{
              backgroundColor: currentConfig.bgColor,
              borderLeft: `4px solid ${currentConfig.color}`,
              borderRadius: '8px',
              padding: '14px 18px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '8px',
                    fontSize: '1rem', 
                    fontWeight: 600, 
                    color: currentConfig.color,
                    marginBottom: '6px',
                  }}>
                    <StatusIcon size={18} />
                    {currentConfig.label}
                    {testResult?.statistics?.match_rate_percent != null && (
                      <span> — {testResult.statistics.match_rate_percent}% Match</span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.9rem', color: c.text, marginBottom: '2px' }}>
                    <span style={{ color: c.electricBlue, fontWeight: 600 }}>{getDisplayName(selectedRel.source_table || selectedRel.from_table)}</span>
                    <span style={{ margin: '0 8px', color: c.textMuted }}>→</span>
                    <span style={{ color: c.electricBlue, fontWeight: 600 }}>{getDisplayName(selectedRel.target_table || selectedRel.to_table)}</span>
                  </div>
                  <div style={{ fontSize: '0.6rem', color: c.silver, fontFamily: 'monospace', marginBottom: '4px' }} title={`${selectedRel.source_table || selectedRel.from_table} → ${selectedRel.target_table || selectedRel.to_table}`}>
                    {getTruncatedName(selectedRel.source_table || selectedRel.from_table, 45)} → {getTruncatedName(selectedRel.target_table || selectedRel.to_table, 45)}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: c.textMuted, marginTop: '4px' }}>
                    Join: {testResult?.join_column_a || selectedRel.source_column || selectedRel.from_column} = {testResult?.join_column_b || selectedRel.target_column || selectedRel.to_column}
                  </div>
                  {testResult?.verification?.message && (
                    <div style={{ fontSize: '0.75rem', color: c.textMuted, marginTop: '6px', fontStyle: 'italic' }}>
                      {testResult.verification.message}
                    </div>
                  )}
                </div>
                
                <div style={{ display: 'flex', gap: '6px' }}>
                  <Tooltip title="Confirm" detail="Mark as verified and correct" action="Used for JOIN queries">
                    <button
                      onClick={() => onConfirm && onConfirm(selectedRel, true)}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: c.primary,
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        color: 'white',
                        fontWeight: 500,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <CheckCircle size={12} /> Confirm
                    </button>
                  </Tooltip>
                  
                  <Tooltip title="Reject" detail="Mark as incorrect" action="Excluded from JOINs">
                    <button
                      onClick={() => onConfirm && onConfirm(selectedRel, false)}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: c.scarletSage,
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        color: 'white',
                        fontWeight: 500,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <XCircle size={12} /> Reject
                    </button>
                  </Tooltip>
                  
                  <Tooltip title="Re-test" detail="Refresh verification">
                    <button
                      onClick={() => testRelationship(selectedRel)}
                      disabled={testing}
                      style={{
                        padding: '6px 10px',
                        backgroundColor: c.background,
                        border: `1px solid ${c.border}`,
                        borderRadius: '4px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                      }}
                    >
                      {testing ? <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> : <RefreshCw size={12} />}
                    </button>
                  </Tooltip>
                </div>
              </div>
            </div>

            {/* Stats Row */}
            {testResult?.statistics && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                <Tooltip title="Matching Keys" detail="Distinct key values found in both tables" action="Higher = stronger relationship">
                  <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 8, padding: '12px', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: c.primary }}>{testResult.statistics.matching_keys || 0}</div>
                    <div style={{ fontSize: '0.65rem', color: c.textMuted }}>Matching</div>
                  </div>
                </Tooltip>
                <Tooltip title="Only in Source" detail="Keys in source with no match in target" action="May indicate unused codes">
                  <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 8, padding: '12px', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: testResult.statistics.orphans_in_a > 0 ? c.warning : c.textMuted }}>{testResult.statistics.orphans_in_a || 0}</div>
                    <div style={{ fontSize: '0.65rem', color: c.textMuted }}>Source Only</div>
                  </div>
                </Tooltip>
                <Tooltip title="Only in Target" detail="Keys in target with no match in source" action="May indicate data issues">
                  <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 8, padding: '12px', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: testResult.statistics.orphans_in_b > 0 ? c.warning : c.textMuted }}>{testResult.statistics.orphans_in_b || 0}</div>
                    <div style={{ fontSize: '0.65rem', color: c.textMuted }}>Target Only</div>
                  </div>
                </Tooltip>
                <Tooltip title="Match Rate" detail="Percentage of source keys found in target">
                  <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 8, padding: '12px', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: c.accent }}>{testResult.statistics.match_rate_percent || 0}%</div>
                    <div style={{ fontSize: '0.65rem', color: c.textMuted }}>Match Rate</div>
                  </div>
                </Tooltip>
              </div>
            )}

            {/* Sample Data Tables */}
            {testing ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: c.textMuted, border: `1px solid ${c.border}`, borderRadius: 8 }}>
                <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: '8px' }} />
                <div>Testing relationship...</div>
              </div>
            ) : testResult && !testResult.error ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                {/* Source Table */}
                <div style={{ border: `1px solid ${c.border}`, borderRadius: 8, overflow: 'hidden' }}>
                  <div style={{ padding: '10px 14px', background: c.background, borderBottom: `1px solid ${c.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: c.text }}>{getDisplayName(selectedRel.source_table || selectedRel.from_table)}</div>
                      <div style={{ fontSize: '0.55rem', color: c.silver, fontFamily: 'monospace', marginTop: '2px' }} title={selectedRel.source_table || selectedRel.from_table}>{getTruncatedName(selectedRel.source_table || selectedRel.from_table, 35)}</div>
                      <div style={{ fontSize: '0.7rem', color: c.textMuted, marginTop: '2px' }}>{testResult.statistics?.table_a_rows?.toLocaleString() || 0} rows</div>
                    </div>
                    <span style={{ fontSize: '0.65rem', padding: '3px 6px', background: `${c.electricBlue}15`, color: c.electricBlue, borderRadius: 4 }}>
                      🔗 {testResult.join_column_a}
                    </span>
                  </div>
                  <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                    <table style={{ width: '100%', fontSize: '0.7rem', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ background: c.background }}>
                          {testResult.table_a_columns?.slice(0, 4).map((col, i) => (
                            <th key={i} style={{ textAlign: 'left', padding: '6px 10px', fontWeight: 500, color: col === testResult.join_column_a ? c.electricBlue : c.textMuted, borderBottom: `1px solid ${c.border}` }}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {testResult.table_a_sample?.slice(0, 6).map((row, i) => {
                          const keyVal = row[testResult.join_column_a];
                          const isOrphan = testResult.statistics?.orphan_samples_from_a?.includes(keyVal);
                          return (
                            <tr key={i} style={{ background: isOrphan ? `${c.warning}10` : 'transparent' }}>
                              {testResult.table_a_columns?.slice(0, 4).map((col, j) => (
                                <td key={j} style={{ padding: '6px 10px', borderBottom: `1px solid ${c.border}`, color: col === testResult.join_column_a ? (isOrphan ? c.warning : c.electricBlue) : c.text }}>
                                  {row[col] ?? '—'}{isOrphan && col === testResult.join_column_a && ' ⚠️'}
                                </td>
                              ))}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Target Table */}
                <div style={{ border: `1px solid ${c.border}`, borderRadius: 8, overflow: 'hidden' }}>
                  <div style={{ padding: '10px 14px', background: c.background, borderBottom: `1px solid ${c.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: c.text }}>{getDisplayName(selectedRel.target_table || selectedRel.to_table)}</div>
                      <div style={{ fontSize: '0.55rem', color: c.silver, fontFamily: 'monospace', marginTop: '2px' }} title={selectedRel.target_table || selectedRel.to_table}>{getTruncatedName(selectedRel.target_table || selectedRel.to_table, 35)}</div>
                      <div style={{ fontSize: '0.7rem', color: c.textMuted, marginTop: '2px' }}>{testResult.statistics?.table_b_rows?.toLocaleString() || 0} rows</div>
                    </div>
                    <span style={{ fontSize: '0.65rem', padding: '3px 6px', background: `${c.electricBlue}15`, color: c.electricBlue, borderRadius: 4 }}>
                      🔗 {testResult.join_column_b}
                    </span>
                  </div>
                  <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                    <table style={{ width: '100%', fontSize: '0.7rem', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ background: c.background }}>
                          {testResult.table_b_columns?.slice(0, 4).map((col, i) => (
                            <th key={i} style={{ textAlign: 'left', padding: '6px 10px', fontWeight: 500, color: col === testResult.join_column_b ? c.electricBlue : c.textMuted, borderBottom: `1px solid ${c.border}` }}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {testResult.table_b_sample?.slice(0, 6).map((row, i) => (
                          <tr key={i}>
                            {testResult.table_b_columns?.slice(0, 4).map((col, j) => (
                              <td key={j} style={{ padding: '6px 10px', borderBottom: `1px solid ${c.border}`, color: col === testResult.join_column_b ? c.electricBlue : c.text }}>
                                {row[col] ?? '—'}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : testResult?.error ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: c.scarletSage, border: `1px solid ${c.border}`, borderRadius: 8 }}>
                <XCircle size={24} style={{ marginBottom: '8px' }} />
                <div>Error: {testResult.error}</div>
              </div>
            ) : null}

            {/* Orphan Values */}
            {testResult?.statistics?.orphan_samples_from_a?.length > 0 && (
              <div style={{ border: `1px solid ${c.border}`, borderRadius: 8, padding: '12px 16px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: c.warning, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertTriangle size={14} />
                  Orphan Values ({testResult.statistics.orphans_in_a} not in target)
                </div>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {testResult.statistics.orphan_samples_from_a.map((val, i) => (
                    <span key={i} style={{ padding: '3px 10px', background: `${c.warning}15`, color: c.warning, borderRadius: 4, fontSize: '0.75rem', fontFamily: 'monospace' }}>{val}</span>
                  ))}
                </div>
                <div style={{ fontSize: '0.7rem', color: c.textMuted, marginTop: '8px' }}>
                  These values exist in the source but have no match in target.
                </div>
              </div>
            )}
          </div>
        )}
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

// Keep old RelationshipEditor for backward compatibility (not used)
function RelationshipEditor({ relationships, tables, tableSchemas, c, onConfirm, onDelete, onUpdate, onFetchColumns }) {
  const [expandedConnections, setExpandedConnections] = useState({});
  const [editingRel, setEditingRel] = useState(null);
  const [editFromCol, setEditFromCol] = useState('');
  const [editToCol, setEditToCol] = useState('');
  const [loadingSchemas, setLoadingSchemas] = useState({});
  
  // Group relationships by connection (from_table → to_table)
  const grouped = relationships.reduce((acc, rel) => {
    const fromTable = rel.from_table || rel.source_table || '?';
    const toTable = rel.to_table || rel.target_table || '?';
    const key = `${fromTable}→${toTable}`;
    if (!acc[key]) acc[key] = { fromTable, toTable, rels: [] };
    acc[key].rels.push(rel);
    return acc;
  }, {});
  
  const toggleConnection = async (key, fromTable, toTable) => {
    const willExpand = !expandedConnections[key];
    setExpandedConnections(prev => ({ ...prev, [key]: willExpand }));
    
    // Fetch columns for both tables when expanding
    if (willExpand) {
      const tablesToFetch = [];
      if (!tableSchemas[fromTable]) tablesToFetch.push(fromTable);
      if (!tableSchemas[toTable]) tablesToFetch.push(toTable);
      
      if (tablesToFetch.length > 0) {
        setLoadingSchemas(prev => ({ ...prev, [key]: true }));
        await Promise.all(tablesToFetch.map(t => onFetchColumns(t)));
        setLoadingSchemas(prev => ({ ...prev, [key]: false }));
      }
    }
  };
  
  const startEdit = async (rel, fromTable, toTable) => {
    // Ensure we have columns for both tables before editing
    const tablesToFetch = [];
    if (!tableSchemas[fromTable]) tablesToFetch.push(fromTable);
    if (!tableSchemas[toTable]) tablesToFetch.push(toTable);
    
    if (tablesToFetch.length > 0) {
      await Promise.all(tablesToFetch.map(t => onFetchColumns(t)));
    }
    
    setEditingRel(rel.id);
    setEditFromCol(rel.from_column || rel.source_column || '');
    setEditToCol(rel.to_column || rel.target_column || '');
  };
  
  const cancelEdit = () => {
    setEditingRel(null);
    setEditFromCol('');
    setEditToCol('');
  };
  
  const saveEdit = (rel) => {
    onUpdate(rel, { 
      source_column: editFromCol, 
      target_column: editToCol 
    });
    setEditingRel(null);
  };
  
  // Get columns from tableSchemas (the cached column data)
  const getColumns = (tableName) => {
    const schema = tableSchemas[tableName];
    if (!schema?.columns) return [];
    return schema.columns.map(col => typeof col === 'string' ? col : col.name);
  };
  
  const getDisplayName = (tableName) => {
    const table = tables.find(t => t.table_name === tableName);
    return table?.display_name || tableName;
  };
  
  if (Object.keys(grouped).length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem', color: c.textMuted }}>
        <Link2 size={48} style={{ color: c.skyBlue, marginBottom: '1rem' }} />
        <p style={{ margin: '0 0 0.5rem', fontWeight: 500, color: c.text }}>No relationships detected yet</p>
        <p style={{ fontSize: '0.85rem', margin: 0 }}>Upload related files to see FK/PK relationships.</p>
      </div>
    );
  }
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {Object.entries(grouped).map(([key, { fromTable, toTable, rels }]) => {
        const isExpanded = expandedConnections[key];
        const fromDisplay = getDisplayName(fromTable);
        const toDisplay = getDisplayName(toTable);
        const confirmedCount = rels.filter(r => r.confirmed).length;
        const isLoadingSchema = loadingSchemas[key];
        
        return (
          <div key={key} style={{ border: `1px solid ${c.border}`, borderRadius: 8, overflow: 'hidden' }}>
            {/* Connection Header - Click to expand */}
            <div
              onClick={() => toggleConnection(key, fromTable, toTable)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.75rem 1rem',
                background: c.background,
                cursor: 'pointer',
                userSelect: 'none'
              }}
            >
              {isLoadingSchema ? (
                <Loader2 size={16} style={{ color: c.textMuted, animation: 'spin 1s linear infinite' }} />
              ) : isExpanded ? (
                <ChevronDown size={16} color={c.textMuted} />
              ) : (
                <ChevronRight size={16} color={c.textMuted} />
              )}
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontWeight: 600, color: c.primary, fontSize: '0.9rem' }}>{fromDisplay}</span>
                <span style={{ color: c.textMuted }}>→</span>
                <span style={{ fontWeight: 600, color: c.accent, fontSize: '0.9rem' }}>{toDisplay}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', color: c.textMuted }}>{rels.length} field{rels.length !== 1 ? 's' : ''}</span>
                {confirmedCount > 0 && (
                  <span style={{ fontSize: '0.7rem', padding: '0.15rem 0.4rem', background: `${c.success}15`, color: c.success, borderRadius: 4 }}>
                    {confirmedCount} confirmed
                  </span>
                )}
              </div>
            </div>
            
            {/* Expanded: Show field mappings */}
            {isExpanded && (
              <div style={{ borderTop: `1px solid ${c.border}` }}>
                {rels.map((rel, idx) => {
                  const fromCol = rel.from_column || rel.source_column || '?';
                  const toCol = rel.to_column || rel.target_column || '?';
                  const isEditing = editingRel === rel.id;
                  const fromCols = getColumns(fromTable);
                  const toCols = getColumns(toTable);
                  
                  return (
                    <div key={rel.id || idx} style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      padding: '0.6rem 1rem 0.6rem 2.5rem',
                      borderBottom: idx < rels.length - 1 ? `1px solid ${c.border}` : 'none',
                      background: rel.needs_review ? `${c.warning}05` : 'transparent'
                    }}>
                      {isEditing ? (
                        <>
                          {/* Editing mode with dropdowns */}
                          <select
                            value={editFromCol}
                            onChange={(e) => setEditFromCol(e.target.value)}
                            style={{
                              padding: '0.35rem 0.5rem',
                              fontSize: '0.8rem',
                              border: `1px solid ${c.border}`,
                              borderRadius: 4,
                              background: c.cardBg,
                              color: c.text,
                              minWidth: 140
                            }}
                          >
                            <option value="">-- Select column --</option>
                            {fromCols.length === 0 ? (
                              <option disabled>Loading columns...</option>
                            ) : (
                              fromCols.map(col => (
                                <option key={col} value={col}>{col}</option>
                              ))
                            )}
                          </select>
                          <span style={{ color: c.textMuted }}>→</span>
                          <select
                            value={editToCol}
                            onChange={(e) => setEditToCol(e.target.value)}
                            style={{
                              padding: '0.35rem 0.5rem',
                              fontSize: '0.8rem',
                              border: `1px solid ${c.border}`,
                              borderRadius: 4,
                              background: c.cardBg,
                              color: c.text,
                              minWidth: 140
                            }}
                          >
                            <option value="">-- Select column --</option>
                            {toCols.length === 0 ? (
                              <option disabled>Loading columns...</option>
                            ) : (
                              toCols.map(col => (
                                <option key={col} value={col}>{col}</option>
                              ))
                            )}
                          </select>
                          <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.25rem' }}>
                            <button 
                              onClick={() => saveEdit(rel)} 
                              disabled={!editFromCol || !editToCol}
                              style={{ 
                                padding: '0.25rem 0.5rem', 
                                background: (!editFromCol || !editToCol) ? c.border : `${c.success}15`, 
                                border: `1px solid ${(!editFromCol || !editToCol) ? c.border : c.success}40`, 
                                borderRadius: 4, 
                                fontSize: '0.7rem', 
                                color: (!editFromCol || !editToCol) ? c.textMuted : c.success, 
                                cursor: (!editFromCol || !editToCol) ? 'not-allowed' : 'pointer' 
                              }}
                            >
                              Save
                            </button>
                            <button onClick={cancelEdit} style={{ padding: '0.25rem 0.5rem', background: c.background, border: `1px solid ${c.border}`, borderRadius: 4, fontSize: '0.7rem', color: c.textMuted, cursor: 'pointer' }}>Cancel</button>
                          </div>
                        </>
                      ) : (
                        <>
                          {/* Display mode */}
                          <code style={{ fontSize: '0.8rem', color: c.text, background: `${c.primary}10`, padding: '0.2rem 0.4rem', borderRadius: 3 }}>{fromCol}</code>
                          <span style={{ color: c.textMuted, fontSize: '0.85rem' }}>→</span>
                          <code style={{ fontSize: '0.8rem', color: c.text, background: `${c.accent}10`, padding: '0.2rem 0.4rem', borderRadius: 3 }}>{toCol}</code>
                          
                          {rel.confirmed && (
                            <CheckCircle size={14} color={c.success} style={{ marginLeft: '0.25rem' }} />
                          )}
                          
                          <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.25rem' }}>
                            <button
                              onClick={() => startEdit(rel, fromTable, toTable)}
                              style={{ padding: '0.25rem 0.4rem', background: 'transparent', border: `1px solid ${c.border}`, borderRadius: 4, cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                              title="Edit mapping"
                            >
                              <Edit2 size={12} color={c.textMuted} />
                            </button>
                            {!rel.confirmed && (
                              <button
                                onClick={() => onConfirm(rel)}
                                style={{ padding: '0.25rem 0.4rem', background: `${c.success}15`, border: `1px solid ${c.success}40`, borderRadius: 4, cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                                title="Confirm"
                              >
                                <CheckCircle size={12} color={c.success} />
                              </button>
                            )}
                            <button
                              onClick={() => onDelete(rel)}
                              style={{ padding: '0.25rem 0.4rem', background: `${c.scarletSage}15`, border: `1px solid ${c.scarletSage}40`, borderRadius: 4, cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                              title="Delete"
                            >
                              <Trash2 size={12} color={c.scarletSage} />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
      
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ============================================================================
// MAIN PAGE
// ============================================================================
export default function DataExplorer() {
  const { colors } = useTheme();
  const { activeProject } = useProject();
  
  const [activeTab, setActiveTab] = useState('tables');
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableDetails, setTableDetails] = useState(null);
  const [relationships, setRelationships] = useState([]);
  const [healthIssues, setHealthIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [expandedFiles, setExpandedFiles] = useState({}); // For grouping tables by file
  
  // NEW: Cache for table schemas (columns) - used by RelationshipEditor
  const [tableSchemas, setTableSchemas] = useState({});
  
  // Compliance state
  const [complianceRunning, setComplianceRunning] = useState(false);
  const [complianceResults, setComplianceResults] = useState(null);
  const [complianceError, setComplianceError] = useState(null);
  
  // Rules state
  const [rules, setRules] = useState([]);
  const [loadingRules, setLoadingRules] = useState(false);
  const [testingRule, setTestingRule] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [generatingSQL, setGeneratingSQL] = useState(null);
  
  const c = { ...colors, ...brandColors };
  
  const projectName = activeProject?.name || activeProject?.id || 'default';

  // NEW: Fetch columns for a specific table and cache them
  const fetchTableColumns = useCallback(async (tableName) => {
    // Skip if already cached
    if (tableSchemas[tableName]) return tableSchemas[tableName];
    
    try {
      const res = await api.get(`/status/table-profile/${encodeURIComponent(tableName)}`);
      const schema = {
        table_name: tableName,
        columns: res.data?.columns || [],
        row_count: res.data?.row_count || 0
      };
      
      setTableSchemas(prev => ({ ...prev, [tableName]: schema }));
      return schema;
    } catch (err) {
      console.error(`Failed to fetch columns for ${tableName}:`, err);
      // Return empty schema on error
      const emptySchema = { table_name: tableName, columns: [], row_count: 0 };
      setTableSchemas(prev => ({ ...prev, [tableName]: emptySchema }));
      return emptySchema;
    }
  }, [tableSchemas]);

  // Load tables
  useEffect(() => {
    loadTables();
  }, [activeProject?.id]);

  const loadTables = async () => {
    setLoading(true);
    try {
      // SINGLE API CALL - /api/platform returns everything we need
      const res = await api.get(`/platform?include=files,relationships&project=${encodeURIComponent(projectName)}`);
      const platform = res.data;
      
      // Get files and build tables from platform.files
      const files = platform?.files || [];
      const allTables = [];
      files.forEach(file => {
        if (file.sheets && file.sheets.length > 0) {
          // Use sheets with actual DuckDB table names
          file.sheets.forEach(sheet => {
            allTables.push({
              table_name: sheet.table_name,  // Actual DuckDB table name
              display_name: sheet.display_name || sheet.table_name,
              row_count: sheet.row_count || 0,
              column_count: sheet.column_count || 0,
              columns: sheet.columns || [],  // May be populated
              filename: file.filename,
              project: file.project,
              truth_type: file.truth_type
            });
          });
        } else {
          // Fallback for files without sheets
          allTables.push({
            table_name: file.filename?.replace(/\.[^.]+$/, '') || file.filename,
            display_name: file.filename?.replace(/\.[^.]+$/, '') || file.filename,
            filename: file.filename,
            row_count: file.rows || file.row_count || 0,
            column_count: 0,
            columns: file.columns || [],
            project: file.project,
            truth_type: file.truth_type || file.type
          });
        }
      });
      
      setTables(allTables);
      
      // Select first table by default
      if (allTables.length > 0 && !selectedTable) {
        setSelectedTable(allTables[0].table_name);
      }
      
      // Health issues from platform (if available)
      setHealthIssues([]);  // Platform doesn't include detailed issues yet
      
      // Relationships from platform.relationships
      setRelationships(platform?.relationships || []);
      
      // Load rules from standards_rules
      try {
        const rulesRes = await api.get('/standards/rules');
        setRules(rulesRes.data?.rules || []);
      } catch (rulesErr) {
        console.log('Rules not loaded:', rulesErr);
        setRules([]);
      }
      
    } catch (err) {
      console.error('Failed to load tables:', err);
      // Fallback to old endpoints if /platform not available
      try {
        const res = await api.get('/platform?include=files,relationships');
        const files = res.data?.files || [];
        const allTables = [];
        files.forEach(file => {
          if (file.sheets && file.sheets.length > 0) {
            file.sheets.forEach(sheet => {
              allTables.push({
                table_name: sheet.table_name,
                display_name: sheet.display_name || sheet.table_name,
                row_count: sheet.row_count || 0,
                column_count: sheet.column_count || 0,
                columns: [],
                filename: file.filename,
                project: file.project,
                truth_type: file.truth_type
              });
            });
          } else {
            allTables.push({
              table_name: file.filename.replace(/\.[^.]+$/, ''),
              display_name: file.filename.replace(/\.[^.]+$/, ''),
              filename: file.filename,
              row_count: file.row_count || 0,
              column_count: 0,
              columns: file.columns || [],
              project: file.project,
              truth_type: file.truth_type
            });
          }
        });
        setTables(allTables);
        if (allTables.length > 0 && !selectedTable) {
          setSelectedTable(allTables[0].table_name);
        }
        
        // Load rules in fallback too
        try {
          const rulesRes = await api.get('/standards/rules');
          setRules(rulesRes.data?.rules || []);
        } catch (rulesErr) {
          console.log('Rules not loaded:', rulesErr);
        }
      } catch (e2) {
        console.error('Fallback also failed:', e2);
      }
    } finally {
      setLoading(false);
    }
  };

  // Load table details when selected
  useEffect(() => {
    if (selectedTable) {
      loadTableDetails(selectedTable);
    }
  }, [selectedTable]);

  const loadTableDetails = async (tableName) => {
    setLoadingDetails(true);
    
    // Get the table from our list - this is the source of truth for row count
    const tableFromList = tables.find(t => t.table_name === tableName);
    const knownRowCount = tableFromList?.row_count || 0;
    
    try {
      const res = await api.get(`/status/table-profile/${encodeURIComponent(tableName)}`);
      const details = {
        ...res.data,
        row_count: knownRowCount // Always use the count from table list
      };
      setTableDetails(details);
      
      // Also cache this in tableSchemas for RelationshipEditor
      setTableSchemas(prev => ({
        ...prev,
        [tableName]: {
          table_name: tableName,
          columns: res.data?.columns || [],
          row_count: knownRowCount
        }
      }));
    } catch (err) {
      // Build details from tables list
      setTableDetails({
        table_name: tableName,
        columns: tableFromList?.columns?.map(col => ({
          name: typeof col === 'string' ? col : col.name,
          type: typeof col === 'string' ? 'VARCHAR' : col.type,
          fill_rate: typeof col === 'string' ? 100 : col.fill_rate || 100
        })) || [],
        row_count: knownRowCount
      });
    } finally {
      setLoadingDetails(false);
    }
  };

  // Relationship handlers
  const confirmRelationship = async (rel) => {
    const sourceTable = rel.source_table || rel.from_table;
    const sourceCol = rel.source_column || rel.from_column;
    const targetTable = rel.target_table || rel.to_table;
    const targetCol = rel.target_column || rel.to_column;
    
    try {
      await api.post(`/data-model/relationships/${encodeURIComponent(projectName)}/confirm`, {
        source_table: sourceTable,
        source_column: sourceCol,
        target_table: targetTable,
        target_column: targetCol,
        confirmed: true
      });
      // Reload relationships
      const relRes = await api.get(`/data-model/relationships/${encodeURIComponent(projectName)}`);
      setRelationships(relRes.data?.relationships || []);
    } catch (e) {
      console.error('Failed to confirm relationship:', e);
      alert('Failed to confirm relationship');
    }
  };

  const deleteRelationship = async (rel) => {
    const sourceTable = rel.source_table || rel.from_table;
    const sourceCol = rel.source_column || rel.from_column;
    const targetTable = rel.target_table || rel.to_table;
    const targetCol = rel.target_column || rel.to_column;
    
    if (!confirm(`Delete relationship ${sourceTable}.${sourceCol} → ${targetTable}.${targetCol}?`)) return;
    
    try {
      await api.delete(`/data-model/relationships/${encodeURIComponent(projectName)}`, {
        params: {
          source_table: sourceTable,
          source_column: sourceCol,
          target_table: targetTable,
          target_column: targetCol
        }
      });
      // Reload relationships
      const relRes = await api.get(`/data-model/relationships/${encodeURIComponent(projectName)}`);
      setRelationships(relRes.data?.relationships || []);
    } catch (e) {
      console.error('Failed to delete relationship:', e);
      alert('Failed to delete relationship');
    }
  };

  const updateRelationship = async (rel, updates) => {
    try {
      await api.patch(`/data-model/relationships/${rel.id}`, updates);
      // Refresh relationships
      const resp = await api.get(`/data-model/relationships/${encodeURIComponent(projectName)}`);
      if (resp.data?.relationships) setRelationships(resp.data.relationships);
    } catch (err) {
      console.error('Failed to update relationship:', err);
      alert('Failed to update relationship');
    }
  };

  const getTableHealth = (tableName) => {
    const tableIssues = healthIssues.filter(i => i.table === tableName);
    if (tableIssues.some(i => i.severity === 'error')) return 'error';
    if (tableIssues.some(i => i.severity === 'warning')) return 'warning';
    return 'good';
  };

  const getFillRateColor = (rate) => {
    if (rate >= 90) return c.accent;
    if (rate >= 50) return c.warning;
    return c.scarletSage;
  };

  // UPDATED: Added classification tab with tooltips
  const tabs = [
    { id: 'tables', label: '📊 Tables & Fields', icon: FileSpreadsheet, tooltip: 'Browse all tables and their columns. View fill rates and data types.' },
    { id: 'classification', label: '🔍 Classification', icon: Eye, tooltip: 'See how columns are classified (PII, categorical, numeric) and their data quality.' },
    { id: 'relationships', label: '🔗 Data Model', icon: Link2, tooltip: 'View, verify, and test relationships. Confirm join columns between tables.' },
    { id: 'health', label: '❤️ Data Health', icon: Heart, tooltip: 'Data integrity checks: missing values, format issues, and quality scores.' },
    { id: 'compliance', label: '✅ Compliance', icon: Shield, tooltip: 'Run compliance checks against loaded rules. View gaps and recommendations.' },
    { id: 'rules', label: '📜 Rules', icon: BookOpen, tooltip: 'Extracted validation rules from regulatory documents. Used in compliance checks.' },
  ];

  const totalTables = tables.length;
  const totalColumns = tables.reduce((sum, t) => sum + (t.column_count || t.columns?.length || 0), 0);
  const totalIssues = healthIssues?.length || 0;

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', color: c.textMuted }}>
        <Loader2 size={40} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
        <p>Loading data explorer...</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div style={{ padding: '1.5rem', maxWidth: '1400px', margin: '0 auto', background: c.background, minHeight: '100vh' }}>
      {/* Breadcrumb */}
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/data" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: c.textMuted, textDecoration: 'none', fontSize: '0.85rem' }}>
          <ArrowLeft size={16} /> Back to Data Management
        </Link>
      </div>
      
      {/* Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, color: c.text, margin: 0, fontFamily: "'Sora', sans-serif" }}>
            Data Explorer
          </h1>
          <p style={{ fontSize: '0.85rem', color: c.textMuted, margin: '0.25rem 0 0' }}>
            View tables, columns, relationships, and data health
          </p>
        </div>
        <button 
          onClick={loadTables}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.5rem 1rem', background: c.cardBg, border: `1px solid ${c.border}`,
            borderRadius: 8, fontSize: '0.85rem', color: c.text, cursor: 'pointer'
          }}
        >
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '1.5rem', background: c.border, padding: 4, borderRadius: 10, width: 'fit-content' }}>
        {tabs.map(tab => (
          <Tooltip key={tab.id} title={tab.label.replace(/^[^\s]+\s/, '')} detail={tab.tooltip} action="Click to view">
            <button
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '0.6rem 1.25rem', border: 'none',
                background: activeTab === tab.id ? c.cardBg : 'transparent',
                fontWeight: 500, fontSize: '0.85rem',
                color: activeTab === tab.id ? c.primary : c.textMuted,
                cursor: 'pointer', borderRadius: 8, transition: 'all 0.2s',
                boxShadow: activeTab === tab.id ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
              }}
            >
              {tab.label}
            </button>
          </Tooltip>
        ))}
      </div>

      {/* Stats Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        <Tooltip title="Tables" detail="Total structured tables loaded into the system." action="Click a table to view columns">
          <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1rem 1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', cursor: 'help' }}>
            <span style={{ fontSize: '1.5rem' }}>🗄️</span>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.text }}>{totalTables}</div>
              <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Tables</div>
            </div>
          </div>
        </Tooltip>
        
        <Tooltip title="Columns" detail="Total columns across all tables." action="Check fill rates in table detail">
          <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1rem 1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', cursor: 'help' }}>
            <span style={{ fontSize: '1.5rem' }}>📋</span>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.text }}>{totalColumns}</div>
              <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Columns</div>
            </div>
          </div>
        </Tooltip>
        
        <Tooltip title="Relationships" detail="Detected joins between tables based on matching columns." action="Used for smart SQL generation">
          <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1rem 1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', cursor: 'help' }}>
            <span style={{ fontSize: '1.5rem' }}>🔗</span>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.text }}>{relationships?.length || 0}</div>
              <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Relationships</div>
            </div>
          </div>
        </Tooltip>
        
        <Tooltip title="Data Health" detail="Number of data quality issues detected." action="Check the Health tab for details">
          <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1rem 1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', cursor: 'help' }}>
            <span style={{ fontSize: '1.5rem' }}>{totalIssues === 0 ? '✅' : '⚠️'}</span>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: totalIssues === 0 ? c.success : c.warning }}>{totalIssues}</div>
              <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Issues</div>
            </div>
          </div>
        </Tooltip>
      </div>

      {/* Tables Tab */}
      {activeTab === 'tables' && (
        <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '1rem' }}>
          {/* Table List - Grouped by File */}
          <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, maxHeight: '70vh', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '1rem', borderBottom: `1px solid ${c.border}` }}>
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: c.text }}>
                <Database size={16} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                Tables ({tables.length})
              </h3>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {(() => {
                // Group tables by filename
                const fileGroups = {};
                tables.forEach(table => {
                  const fileName = table.filename || 'Unknown Source';
                  if (!fileGroups[fileName]) {
                    fileGroups[fileName] = {
                      fileName,
                      shortName: fileName.length > 32 ? fileName.substring(0, 29) + '...' : fileName,
                      tables: []
                    };
                  }
                  fileGroups[fileName].tables.push(table);
                });
                
                return Object.values(fileGroups).map(group => {
                  const isExpanded = expandedFiles[group.fileName] === true; // Default collapsed
                  
                  return (
                    <div key={group.fileName} style={{ borderBottom: `1px solid ${c.border}` }}>
                      {/* File Header */}
                      <button
                        onClick={() => setExpandedFiles(prev => ({ ...prev, [group.fileName]: !isExpanded }))}
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          background: 'transparent',
                          border: 'none',
                          borderLeft: `3px solid ${c.primary}`,
                          cursor: 'pointer',
                          textAlign: 'left',
                          transition: 'background 0.15s',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = c.background}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        <div style={{ 
                          width: 24, height: 24, borderRadius: 4, 
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          background: 'white', border: `1px solid ${c.border}`
                        }}>
                          <FileText size={12} style={{ color: c.textMuted }} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={group.fileName}>
                            {group.shortName}
                          </div>
                          <div style={{ fontSize: '0.65rem', color: c.textMuted }}>{group.tables.length} table{group.tables.length !== 1 ? 's' : ''}</div>
                        </div>
                        {isExpanded ? (
                          <ChevronDown size={14} style={{ color: c.textMuted }} />
                        ) : (
                          <ChevronRight size={14} style={{ color: c.textMuted }} />
                        )}
                      </button>
                      
                      {/* Tables within File */}
                      {isExpanded && (
                        <div style={{ background: `${c.background}50` }}>
                          {group.tables.map(table => {
                            const health = getTableHealth(table.table_name);
                            const healthColor = health === 'good' ? c.success : health === 'warning' ? c.warning : c.scarletSage;
                            const isSelected = selectedTable === table.table_name;
                            
                            return (
                              <button
                                key={table.table_name}
                                onClick={() => setSelectedTable(table.table_name)}
                                style={{
                                  width: '100%',
                                  padding: '8px 12px 8px 44px',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '8px',
                                  background: isSelected ? `${c.accent}15` : 'transparent',
                                  border: 'none',
                                  borderTop: `1px solid ${c.border}`,
                                  borderLeft: isSelected ? `3px solid ${c.accent}` : '3px solid transparent',
                                  cursor: 'pointer',
                                  textAlign: 'left',
                                  transition: 'background 0.15s',
                                }}
                                onMouseEnter={(e) => !isSelected && (e.currentTarget.style.background = c.background)}
                                onMouseLeave={(e) => !isSelected && (e.currentTarget.style.background = 'transparent')}
                              >
                                <FileSpreadsheet size={12} style={{ color: c.primary, flexShrink: 0 }} />
                                <div style={{ flex: 1, minWidth: 0 }}>
                                  <div style={{ 
                                    fontSize: '0.8rem', 
                                    fontWeight: isSelected ? 600 : 500, 
                                    color: isSelected ? c.accent : c.text,
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap'
                                  }}>
                                    {table.display_name || table.table_name}
                                  </div>
                                  <div style={{ fontSize: '0.65rem', color: c.textMuted }}>
                                    {table.row_count?.toLocaleString() || 0} rows
                                  </div>
                                </div>
                                <div style={{ width: 6, height: 6, borderRadius: '50%', background: healthColor, flexShrink: 0 }} title={`Health: ${health}`} />
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                });
              })()}
            </div>
          </div>

          {/* Table Detail */}
          <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1.25rem' }}>
            {loadingDetails ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px', color: c.textMuted }}>
                <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', marginRight: '0.5rem' }} />
                Loading...
              </div>
            ) : tableDetails ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: c.text }}>
                      {tableDetails.display_name || tableDetails.table_name}
                    </h3>
                    <div style={{ fontSize: '0.8rem', color: c.textMuted, marginTop: '0.25rem' }}>
                      {tableDetails.row_count?.toLocaleString() || 0} rows • {tableDetails.columns?.length || 0} columns
                    </div>
                  </div>
                  <button
                    onClick={() => setActiveTab('classification')}
                    style={{
                      padding: '0.25rem 0.6rem',
                      background: `${c.royalPurple}15`,
                      border: `1px solid ${c.royalPurple}40`,
                      borderRadius: 6,
                      fontSize: '0.75rem',
                      color: c.royalPurple,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.35rem'
                    }}
                  >
                    <Eye size={14} /> Classification
                  </button>
                </div>
                
                {/* Columns Grid */}
                <div style={{ maxHeight: '55vh', overflowY: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead>
                      <tr style={{ borderBottom: `2px solid ${c.border}` }}>
                        <th style={{ textAlign: 'left', padding: '0.5rem 0.75rem', fontWeight: 600, color: c.text }}>Column</th>
                        <th style={{ textAlign: 'left', padding: '0.5rem 0.75rem', fontWeight: 600, color: c.text }}>Type</th>
                        <th style={{ textAlign: 'right', padding: '0.5rem 0.75rem', fontWeight: 600, color: c.text }}>Fill Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(tableDetails.columns || []).map((col, idx) => {
                        const colName = typeof col === 'string' ? col : col.name;
                        const colType = typeof col === 'string' ? 'VARCHAR' : col.type || 'VARCHAR';
                        const fillRate = typeof col === 'string' ? 100 : col.fill_rate || 100;
                        
                        return (
                          <tr key={idx} style={{ borderBottom: `1px solid ${c.border}` }}>
                            <td style={{ padding: '0.5rem 0.75rem', color: c.text }}>
                              <code style={{ fontSize: '0.8rem', background: c.background, padding: '0.15rem 0.35rem', borderRadius: 3 }}>
                                {colName}
                              </code>
                            </td>
                            <td style={{ padding: '0.5rem 0.75rem', color: c.textMuted, fontSize: '0.8rem' }}>{colType}</td>
                            <td style={{ padding: '0.5rem 0.75rem', textAlign: 'right' }}>
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem' }}>
                                <div style={{ width: '60px', height: '6px', background: c.background, borderRadius: 3, overflow: 'hidden' }}>
                                  <div style={{ width: `${fillRate}%`, height: '100%', background: getFillRateColor(fillRate), borderRadius: 3 }} />
                                </div>
                                <span style={{ fontSize: '0.75rem', color: getFillRateColor(fillRate), fontWeight: 500, minWidth: '35px' }}>
                                  {fillRate}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '200px', color: c.textMuted }}>
                <FileSpreadsheet size={40} style={{ marginBottom: '0.75rem', opacity: 0.5 }} />
                <p>Select a table to view columns</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Classification Tab */}
      {activeTab === 'classification' && (
        <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '1rem' }}>
          {/* Table List - Grouped by File */}
          <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, maxHeight: '70vh', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '1rem', borderBottom: `1px solid ${c.border}` }}>
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: c.text }}>
                <Eye size={16} style={{ marginRight: 6, verticalAlign: 'middle', color: c.royalPurple }} />
                Tables ({tables.length})
              </h3>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {(() => {
                // Group tables by filename
                const fileGroups = {};
                tables.forEach(table => {
                  const fileName = table.filename || 'Unknown Source';
                  if (!fileGroups[fileName]) {
                    fileGroups[fileName] = {
                      fileName,
                      shortName: fileName.length > 32 ? fileName.substring(0, 29) + '...' : fileName,
                      tables: []
                    };
                  }
                  fileGroups[fileName].tables.push(table);
                });
                
                return Object.values(fileGroups).map(group => {
                  const isExpanded = expandedFiles[`class_${group.fileName}`] === true; // Default collapsed
                  
                  return (
                    <div key={group.fileName} style={{ borderBottom: `1px solid ${c.border}` }}>
                      {/* File Header */}
                      <button
                        onClick={() => setExpandedFiles(prev => ({ ...prev, [`class_${group.fileName}`]: !isExpanded }))}
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          background: 'transparent',
                          border: 'none',
                          borderLeft: `3px solid ${c.royalPurple}`,
                          cursor: 'pointer',
                          textAlign: 'left',
                          transition: 'background 0.15s',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = c.background}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        <div style={{ 
                          width: 24, height: 24, borderRadius: 4, 
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          background: 'white', border: `1px solid ${c.border}`
                        }}>
                          <FileText size={12} style={{ color: c.textMuted }} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={group.fileName}>
                            {group.shortName}
                          </div>
                          <div style={{ fontSize: '0.65rem', color: c.textMuted }}>{group.tables.length} table{group.tables.length !== 1 ? 's' : ''}</div>
                        </div>
                        {isExpanded ? (
                          <ChevronDown size={14} style={{ color: c.textMuted }} />
                        ) : (
                          <ChevronRight size={14} style={{ color: c.textMuted }} />
                        )}
                      </button>
                      
                      {/* Tables within File */}
                      {isExpanded && (
                        <div style={{ background: `${c.background}50` }}>
                          {group.tables.map(table => {
                            const isSelected = selectedTable === table.table_name;
                            
                            return (
                              <button
                                key={table.table_name}
                                onClick={() => setSelectedTable(table.table_name)}
                                style={{
                                  width: '100%',
                                  padding: '8px 12px 8px 44px',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '8px',
                                  background: isSelected ? `${c.royalPurple}15` : 'transparent',
                                  border: 'none',
                                  borderTop: `1px solid ${c.border}`,
                                  borderLeft: isSelected ? `3px solid ${c.royalPurple}` : '3px solid transparent',
                                  cursor: 'pointer',
                                  textAlign: 'left',
                                  transition: 'background 0.15s',
                                }}
                                onMouseEnter={(e) => !isSelected && (e.currentTarget.style.background = c.background)}
                                onMouseLeave={(e) => !isSelected && (e.currentTarget.style.background = 'transparent')}
                              >
                                <Eye size={12} style={{ color: c.royalPurple, flexShrink: 0 }} />
                                <span style={{ 
                                  fontSize: '0.8rem', 
                                  fontWeight: isSelected ? 600 : 500, 
                                  color: isSelected ? c.royalPurple : c.text,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                  flex: 1
                                }}>
                                  {table.display_name || table.table_name}
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                });
              })()}
            </div>
          </div>

          {/* Classification Panel */}
          {selectedTable ? (
            <ClassificationPanel tableName={selectedTable} />
          ) : (
            <div style={{ 
              background: c.cardBg, 
              border: `1px solid ${c.border}`, 
              borderRadius: 10,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: c.textMuted,
              padding: '3rem'
            }}>
              Select a table to view its classification
            </div>
          )}
        </div>
      )}

      {/* Relationships Tab - Data Model */}
      {activeTab === 'relationships' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <Tooltip title="Data Model" detail="View, verify, and manage table relationships. Test join columns and verify match rates." action="Confirm relationships for accurate JOIN queries">
              <h3 style={{ margin: 0, color: c.text, fontSize: '1.1rem', cursor: 'help' }}>
                <Link2 size={18} style={{ marginRight: 8, verticalAlign: 'middle', color: c.accent }} />
                Data Model
              </h3>
            </Tooltip>
          </div>
          
          <DataModelPanel 
            relationships={relationships}
            tables={tables}
            projectName={projectName}
            c={c}
            onConfirm={confirmRelationship}
            onReload={loadTables}
          />
        </div>
      )}

      {/* Data Health Tab */}
      {activeTab === 'health' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem', color: c.text, fontSize: '1.1rem' }}>
            <Heart size={18} style={{ marginRight: 8, verticalAlign: 'middle', color: c.scarletSage }} />
            Data Health
          </h3>
          {(!healthIssues || healthIssues.length === 0) ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
              <CheckCircle size={48} style={{ color: c.success, marginBottom: '1rem' }} />
              <p style={{ fontWeight: 600, margin: '0 0 0.5rem', color: c.success }}>All data looks healthy!</p>
              <p style={{ fontSize: '0.85rem', color: c.textMuted, margin: '0 0 1rem' }}>
                No integrity issues detected across {tables?.length || 0} table(s).
              </p>
              <div style={{ 
                textAlign: 'left', 
                background: c.background, 
                borderRadius: 8, 
                padding: '1rem',
                fontSize: '0.8rem',
                color: c.textMuted,
                width: '100%',
                maxWidth: '400px'
              }}>
                <strong style={{ color: c.text }}>Checks performed:</strong>
                <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem' }}>
                  <li>Registry entries exist for all DuckDB tables</li>
                  <li>Row counts match between registry and actual data</li>
                  <li>No orphaned embeddings in ChromaDB</li>
                  <li>File metadata is complete</li>
                </ul>
              </div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              {healthIssues.map((issue, i) => (
                <div key={i} style={{ 
                  padding: '0.75rem 1rem',
                  background: issue.severity === 'error' ? `${c.scarletSage}10` : `${c.warning}10`,
                  borderRadius: 8,
                  border: `1px solid ${issue.severity === 'error' ? c.scarletSage : c.warning}40`
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    {issue.severity === 'error' ? 
                      <XCircle size={16} style={{ color: c.scarletSage }} /> : 
                      <AlertTriangle size={16} style={{ color: c.warning }} />
                    }
                    <span style={{ fontWeight: 600, color: c.text }}>{issue.type || 'Issue'}</span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: c.textMuted }}>{issue.message}</div>
                  {issue.table && <code style={{ fontSize: '0.75rem', color: c.primary }}>{issue.table}</code>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Compliance Tab */}
      {activeTab === 'compliance' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: c.text, fontSize: '1.1rem' }}>
              <Shield size={18} style={{ marginRight: 8, verticalAlign: 'middle', color: c.success }} />
              Compliance Check
            </h3>
            <button
              onClick={async () => {
                setComplianceRunning(true);
                setComplianceError(null);
                try {
                  const res = await api.post(`/standards/compliance/check/${activeProject?.id || 'default'}`);
                  setComplianceResults(res.data);
                } catch (e) {
                  setComplianceError(e.message || 'Compliance check failed');
                } finally {
                  setComplianceRunning(false);
                }
              }}
              disabled={complianceRunning || !rules || rules.length === 0}
              title={(!rules || rules.length === 0) ? 'Upload regulatory documents first to extract rules' : 'Run compliance check against your data'}
              style={{
                padding: '0.5rem 1rem',
                background: (!rules || rules.length === 0) ? c.border : c.primary,
                color: (!rules || rules.length === 0) ? c.textMuted : '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: (complianceRunning || !rules || rules.length === 0) ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                opacity: (!rules || rules.length === 0) ? 0.6 : 1
              }}
            >
              {complianceRunning ? <Loader2 size={16} className="spin" /> : <Play size={16} />}
              Run Check
            </button>
          </div>
          
          {complianceError && (
            <div style={{ padding: '1rem', background: `${c.scarletSage}10`, borderRadius: 8, color: c.scarletSage, marginBottom: '1rem' }}>
              {complianceError}
            </div>
          )}
          
          {complianceResults ? (
            <div style={{ display: 'grid', gap: '1rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                <div style={{ padding: '1rem', background: `${c.success}10`, borderRadius: 8, textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.success }}>{complianceResults.passed || 0}</div>
                  <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Passed</div>
                </div>
                <div style={{ padding: '1rem', background: `${c.warning}10`, borderRadius: 8, textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.warning }}>{complianceResults.warnings || 0}</div>
                  <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Warnings</div>
                </div>
                <div style={{ padding: '1rem', background: `${c.scarletSage}10`, borderRadius: 8, textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.scarletSage }}>{complianceResults.failed || 0}</div>
                  <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Failed</div>
                </div>
              </div>
              {complianceResults.details?.map((d, i) => (
                <div key={i} style={{ padding: '0.75rem', background: c.background, borderRadius: 6, fontSize: '0.85rem' }}>
                  {d.rule}: <span style={{ color: d.passed ? c.success : c.scarletSage }}>{d.passed ? 'PASS' : 'FAIL'}</span>
                </div>
              ))}
            </div>
          ) : (rules && rules.length > 0) ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem' }}>
              <Shield size={48} style={{ color: c.primary, marginBottom: '1rem' }} />
              <p style={{ margin: '0 0 0.5rem', fontWeight: 500, color: c.text }}>Ready to check compliance</p>
              <p style={{ fontSize: '0.85rem', color: c.textMuted, margin: 0 }}>Click "Run Check" to validate data against {rules.length} loaded rules.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem' }}>
              <Shield size={48} style={{ color: c.iceFlow, marginBottom: '1rem' }} />
              <p style={{ margin: '0 0 0.5rem', fontWeight: 500, color: c.text }}>No rules loaded yet</p>
              <p style={{ fontSize: '0.85rem', color: c.textMuted, margin: 0 }}>Upload standards documents in the Standards page to extract validation rules.</p>
            </div>
          )}
        </div>
      )}

      {/* Rules Tab */}
      {activeTab === 'rules' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: c.text, fontSize: '1.1rem' }}>
              <BookOpen size={18} style={{ marginRight: 8, verticalAlign: 'middle', color: c.royalPurple }} />
              Extracted Rules ({rules?.length || 0})
            </h3>
            {rules?.length > 0 && (
              <button
                onClick={async () => {
                  setLoadingRules(true);
                  try {
                    const res = await api.get('/standards/rules');
                    setRules(res.data?.rules || []);
                  } catch (e) {
                    console.error('Failed to load rules:', e);
                  } finally {
                    setLoadingRules(false);
                  }
                }}
                disabled={loadingRules}
                style={{
                  padding: '0.5rem 1rem',
                  background: c.background,
                  color: c.text,
                  border: `1px solid ${c.border}`,
                  borderRadius: 6,
                  cursor: loadingRules ? 'wait' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                {loadingRules ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />}
                Refresh
              </button>
            )}
          </div>
          
          {(!rules || rules.length === 0) ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem', color: c.textMuted }}>
              <BookOpen size={48} style={{ color: c.royalPurple, opacity: 0.5, marginBottom: '1rem' }} />
              <p style={{ fontWeight: 600, margin: '0 0 0.5rem', color: c.text }}>No rules extracted yet</p>
              <p style={{ fontSize: '0.85rem', margin: 0, textAlign: 'center' }}>
                Upload regulatory or standards documents in the Data page.<br />
                Rules will be automatically extracted for compliance checks.
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              {(rules || []).map((rule, i) => (
                <div key={i} style={{ 
                  padding: '0.75rem 1rem',
                  background: c.background,
                  borderRadius: 8,
                  border: `1px solid ${c.border}`
                }}>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', color: c.text, marginBottom: '0.25rem' }}>
                    {rule.name || `Rule ${i + 1}`}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: c.textMuted }}>{rule.description || rule.condition}</div>
                  {rule.source && (
                    <div style={{ fontSize: '0.75rem', color: c.primary, marginTop: '0.5rem' }}>
                      Source: {rule.source}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spin { animation: spin 1s linear infinite; }
      `}</style>
    </div>
  );
}
