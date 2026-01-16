/**
 * DataExplorer.jsx - Data Explorer
 * =================================
 * 
 * Browse tables, fields, context graph, classification, compliance, and rules.
 * 
 * Tabs:
 * - Tables & Fields: Browse tables and columns, view fill rates
 * - Context Graph: Hub/spoke relationships for intelligent queries
 * - Classification: Column classifications (PII, categorical, numeric)
 * - Compliance: Run compliance checks against loaded rules
 * - Rules: Extracted validation rules from regulatory documents
 * 
 * Updated: January 10, 2026
 * Cleanup: Removed legacy DataModelPanel and RelationshipEditor (replaced by Context Graph)
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Database, FileSpreadsheet, FileText, ChevronDown, ChevronRight, ChevronUp,
  ArrowLeft, RefreshCw, CheckCircle, AlertTriangle, XCircle, Key, Loader2,
  Shield, Play, Folder, BookOpen, Code, Trash2, Edit3, Sparkles, Eye, Edit2,
  Search, ClipboardList, BarChart3, Tags, Network
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useProject } from '../context/ProjectContext';
import { Tooltip } from '../components/ui';
import api from '../services/api';

// NEW: Import ClassificationPanel
import ClassificationPanel, { ChunkPanel } from '../components/ClassificationPanel';

// NEW: Import ContextGraph
import ContextGraph from '../components/ContextGraph';

// Import column splitter for Data view
import ClickToSplit from '../components/ClickToSplit';

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
// MAIN PAGE
// ============================================================================
export default function DataExplorer() {
  const { colors } = useTheme();
  const { activeProject } = useProject();
  
  const [activeTab, setActiveTab] = useState('tables');
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableDetails, setTableDetails] = useState(null);
  const [sampleData, setSampleData] = useState(null);
  const [detailView, setDetailView] = useState('schema'); // 'schema' | 'data'
  const [splitColumn, setSplitColumn] = useState(null); // { columnName, sampleValues } when splitting
  const [relationships, setRelationships] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [expandedFiles, setExpandedFiles] = useState({}); // For grouping tables by file
  
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
    setSampleData(null);
    
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
      // Fetch sample data from table-preview endpoint
      try {
        const previewRes = await api.get(`/data-model/table-preview/${encodeURIComponent(projectName)}/${encodeURIComponent(tableName)}`);
        if (previewRes.data?.sample_data) {
          setSampleData(previewRes.data.sample_data);
        }
      } catch (previewErr) {
        console.warn('Could not load sample data:', previewErr);
      }
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

  const getTableHealth = (tableName) => {
    // Health tracking removed - always return good
    return 'good';
  };

  const getFillRateColor = (rate) => {
    if (rate >= 90) return c.accent;
    if (rate >= 50) return c.warning;
    return c.scarletSage;
  };

  // UPDATED: Added classification tab with tooltips
  const tabs = [
    { id: 'tables', label: 'Tables & Fields', icon: FileSpreadsheet, tooltip: 'Browse all tables and their columns. View fill rates and data types.' },
    { id: 'context-graph', label: 'Context Graph', icon: Network, tooltip: 'View hub/spoke relationships that power intelligent joins and queries.' },
    { id: 'classification', label: 'Classification', icon: Eye, tooltip: 'See how columns are classified (PII, categorical, numeric) and their data quality.' },
    { id: 'compliance', label: 'Compliance', icon: Shield, tooltip: 'Run compliance checks against loaded rules. View gaps and recommendations.' },
    { id: 'rules', label: 'Rules', icon: BookOpen, tooltip: 'Extracted validation rules from regulatory documents. Used in compliance checks.' },
  ];

  const totalTables = tables.length;
  const totalColumns = tables.reduce((sum, t) => sum + (t.column_count || t.columns?.length || 0), 0);

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
    <div>
      {/* Breadcrumb */}
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/data" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: c.textMuted, textDecoration: 'none', fontSize: '0.85rem' }}>
          <ArrowLeft size={16} /> Back to Project Data
        </Link>
      </div>
      
      {/* Header */}
      <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
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
              <Database size={20} color="#ffffff" />
            </div>
            Data Explorer
          </h1>
          <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: c.textMuted }}>
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
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
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
            <ClipboardList size={28} color={c.primary} />
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.text }}>{totalColumns}</div>
              <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Columns</div>
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
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {/* Schema/Data Toggle */}
                    <div style={{ display: 'flex', background: c.background, borderRadius: 6, padding: 2 }}>
                      <button
                        onClick={() => setDetailView('schema')}
                        style={{
                          padding: '0.25rem 0.6rem',
                          background: detailView === 'schema' ? c.cardBg : 'transparent',
                          border: 'none',
                          borderRadius: 4,
                          fontSize: '0.75rem',
                          fontWeight: detailView === 'schema' ? 600 : 400,
                          color: detailView === 'schema' ? c.accent : c.textMuted,
                          cursor: 'pointer',
                          boxShadow: detailView === 'schema' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none'
                        }}
                      >
                        Schema
                      </button>
                      <button
                        onClick={() => setDetailView('data')}
                        style={{
                          padding: '0.25rem 0.6rem',
                          background: detailView === 'data' ? c.cardBg : 'transparent',
                          border: 'none',
                          borderRadius: 4,
                          fontSize: '0.75rem',
                          fontWeight: detailView === 'data' ? 600 : 400,
                          color: detailView === 'data' ? c.accent : c.textMuted,
                          cursor: 'pointer',
                          boxShadow: detailView === 'data' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none'
                        }}
                      >
                        Data
                      </button>
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
                </div>
                
                {/* Schema View */}
                {detailView === 'schema' && (
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
                )}

                {/* Data View - Sample Rows */}
                {detailView === 'data' && (
                  <div style={{ maxHeight: '55vh', overflowY: 'auto' }}>
                    {sampleData && sampleData.length > 0 ? (
                      <>
                        <div style={{ fontSize: '0.75rem', color: c.textMuted, marginBottom: '0.5rem' }}>
                          Showing {sampleData.length} sample rows • Click column header to split
                        </div>
                        <div style={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', minWidth: 'max-content' }}>
                            <thead>
                              <tr style={{ borderBottom: `2px solid ${c.border}` }}>
                                {Object.keys(sampleData[0] || {}).map((col, idx) => (
                                  <th 
                                    key={idx} 
                                    onClick={() => setSplitColumn({
                                      columnName: col,
                                      sampleValues: sampleData.map(row => row[col]).filter(v => v)
                                    })}
                                    style={{ 
                                      textAlign: 'left', 
                                      padding: '0.5rem 0.75rem', 
                                      fontWeight: 600, 
                                      color: c.text,
                                      whiteSpace: 'nowrap',
                                      background: c.background,
                                      cursor: 'pointer',
                                      transition: 'background 0.15s'
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.background = '#e2e8f0'}
                                    onMouseLeave={(e) => e.currentTarget.style.background = c.background}
                                    title={`Click to split "${col}"`}
                                  >
                                    {col}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {sampleData.map((row, ridx) => (
                                <tr key={ridx} style={{ borderBottom: `1px solid ${c.border}` }}>
                                  {Object.values(row).map((val, cidx) => (
                                    <td key={cidx} style={{ 
                                      padding: '0.5rem 0.75rem', 
                                      color: c.text,
                                      maxWidth: '200px',
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      whiteSpace: 'nowrap'
                                    }} title={String(val || '')}>
                                      {val === null || val === undefined ? (
                                        <span style={{ color: c.textMuted, fontStyle: 'italic' }}>null</span>
                                      ) : String(val).length > 50 ? (
                                        String(val).substring(0, 47) + '...'
                                      ) : (
                                        String(val)
                                      )}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '200px', color: c.textMuted }}>
                        <Database size={40} style={{ marginBottom: '0.75rem', opacity: 0.5 }} />
                        <p>No sample data available</p>
                      </div>
                    )}
                  </div>
                )}
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

      {/* Context Graph Tab */}
      {activeTab === 'context-graph' && (
        <div style={{ 
          background: c.cardBg, 
          border: `1px solid ${c.border}`, 
          borderRadius: 10, 
          padding: '1.5rem',
          maxWidth: '1200px'
        }}>
          <ContextGraph project={activeProject?.name || activeProject} />
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
              <div style={{ textAlign: 'center' }}>
                <Tags size={48} style={{ opacity: 0.3, marginBottom: '16px', display: 'block', margin: '0 auto 16px' }} />
                <div style={{ fontSize: '1rem', fontWeight: 500 }}>Select a table</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px' }}>
                  Click one on the left to view its classification
                </div>
              </div>
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
                  const res = await api.post(`/standards/compliance/check/${encodeURIComponent(projectName)}`);
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
              {/* Summary Stats - 4 columns: passed, failed, skipped, errors */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
                <div style={{ padding: '1rem', background: `${c.success}10`, borderRadius: 8, textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.success }}>{complianceResults.passed || 0}</div>
                  <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Passed</div>
                </div>
                <div style={{ padding: '1rem', background: `${c.scarletSage}10`, borderRadius: 8, textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.scarletSage }}>{complianceResults.failed || 0}</div>
                  <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Failed</div>
                </div>
                <div style={{ padding: '1rem', background: `${c.warning}10`, borderRadius: 8, textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.warning }}>{complianceResults.skipped || 0}</div>
                  <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Skipped</div>
                </div>
                <div style={{ padding: '1rem', background: `${c.iceFlow}20`, borderRadius: 8, textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.textMuted }}>{complianceResults.errors || 0}</div>
                  <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Errors</div>
                </div>
              </div>
              
              {/* Per-rule check results */}
              <div style={{ maxHeight: '50vh', overflowY: 'auto' }}>
                <h4 style={{ margin: '0.5rem 0', color: c.text, fontSize: '0.9rem' }}>Check Results ({complianceResults.check_results?.length || 0} rules)</h4>
                {(complianceResults.check_results || []).map((r, i) => {
                  const statusColor = r.status === 'passed' ? c.success : 
                                      r.status === 'failed' ? c.scarletSage : 
                                      r.status === 'skipped' ? c.warning : c.textMuted;
                  const statusIcon = r.status === 'passed' ? '✓' : 
                                     r.status === 'failed' ? '✗' : 
                                     r.status === 'skipped' ? '⊘' : '⚠';
                  return (
                    <div key={i} style={{ 
                      padding: '0.75rem', 
                      background: c.background, 
                      borderRadius: 6, 
                      marginBottom: '0.5rem',
                      borderLeft: `3px solid ${statusColor}`
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600, fontSize: '0.85rem', color: c.text }}>
                            {r.rule_title || r.rule_id}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: c.textMuted, marginTop: '2px' }}>
                            {r.message}
                          </div>
                        </div>
                        <span style={{ 
                          fontSize: '0.75rem', 
                          padding: '2px 8px', 
                          borderRadius: 4, 
                          background: `${statusColor}20`,
                          color: statusColor,
                          fontWeight: 600
                        }}>
                          {statusIcon} {r.status?.toUpperCase()}
                        </span>
                      </div>
                      {r.sql_generated && (
                        <details style={{ marginTop: '0.5rem' }}>
                          <summary style={{ fontSize: '0.75rem', color: c.accent, cursor: 'pointer' }}>View SQL</summary>
                          <pre style={{ 
                            fontSize: '0.7rem', 
                            background: c.cardBg, 
                            padding: '0.5rem', 
                            borderRadius: 4, 
                            overflow: 'auto',
                            margin: '0.25rem 0 0 0',
                            maxHeight: '150px'
                          }}>{r.sql_generated}</pre>
                        </details>
                      )}
                      {r.sql_error && (
                        <div style={{ fontSize: '0.75rem', color: c.scarletSage, marginTop: '0.25rem' }}>
                          SQL Error: {r.sql_error}
                        </div>
                      )}
                      {r.result_count > 0 && (
                        <div style={{ fontSize: '0.75rem', color: c.scarletSage, marginTop: '0.25rem' }}>
                          Found {r.result_count} violation{r.result_count !== 1 ? 's' : ''}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
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

      {/* Column Split Modal */}
      {splitColumn && (
        <ClickToSplit
          tableName={selectedTable}
          columnName={splitColumn.columnName}
          sampleValues={splitColumn.sampleValues}
          projectName={projectName}
          onComplete={(result) => {
            setSplitColumn(null);
            // Refresh the table data
            if (selectedTable) {
              loadTableDetails(selectedTable);
            }
          }}
          onCancel={() => setSplitColumn(null)}
        />
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spin { animation: spin 1s linear infinite; }
      `}</style>
    </div>
  );
}
