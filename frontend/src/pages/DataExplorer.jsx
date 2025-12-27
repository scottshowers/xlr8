/**
 * DataExplorer.jsx - INTEGRATION UPDATE
 * ======================================
 * 
 * This file contains the changes needed to integrate ClassificationPanel
 * into the existing DataExplorer.jsx
 * 
 * CHANGES REQUIRED:
 * 
 * 1. Add import at top:
 *    import ClassificationPanel, { ChunkPanel } from '../components/ClassificationPanel';
 * 
 * 2. Add state for showing classification panel (around line 98):
 *    const [showClassification, setShowClassification] = useState(false);
 * 
 * 3. Add new tab to tabs array (around line 407):
 *    { id: 'classification', label: '🔍 Classification', icon: Eye },
 * 
 * 4. Add tab content after the tables tab (around line 656):
 *    {activeTab === 'classification' && selectedTable && (
 *      <ClassificationPanel tableName={selectedTable} />
 *    )}
 * 
 * 5. Add "View Classification" button in table detail header (around line 577):
 *    <button
 *      onClick={() => setActiveTab('classification')}
 *      style={{
 *        padding: '0.25rem 0.6rem',
 *        background: `${c.royalPurple}15`,
 *        border: `1px solid ${c.royalPurple}40`,
 *        borderRadius: 6,
 *        fontSize: '0.75rem',
 *        color: c.royalPurple,
 *        cursor: 'pointer',
 *        display: 'flex',
 *        alignItems: 'center',
 *        gap: '0.35rem'
 *      }}
 *    >
 *      <Eye size={14} /> Classification
 *    </button>
 * 
 * Below is the complete updated file with all changes integrated:
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Database, FileSpreadsheet, Link2, Heart, ChevronDown, ChevronRight,
  ArrowLeft, RefreshCw, CheckCircle, AlertTriangle, XCircle, Key, Loader2,
  Shield, Play, Folder, BookOpen, Code, Trash2, Edit3, Sparkles, Eye
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

  // Load tables
  useEffect(() => {
    loadTables();
  }, [activeProject?.id]);

  const loadTables = async () => {
    setLoading(true);
    try {
      const res = await api.get('/status/structured');
      const files = res.data?.files || [];
      
      // Flatten sheets from all files into tables
      const allTables = [];
      files.forEach(file => {
        if (file.sheets) {
          file.sheets.forEach(sheet => {
            allTables.push({
              ...sheet,
              filename: file.filename,
              project: file.project,
              truth_type: file.truth_type
            });
          });
        } else {
          allTables.push({
            table_name: file.filename.replace(/\.[^.]+$/, ''),
            filename: file.filename,
            row_count: file.row_count || 0,
            columns: file.columns || [],
            project: file.project,
            truth_type: file.truth_type
          });
        }
      });
      
      setTables(allTables);
      
      // Select first table by default
      if (allTables.length > 0 && !selectedTable) {
        setSelectedTable(allTables[0].table_name);
      }
      
      // Load health issues
      try {
        const healthRes = await api.get('/status/data-integrity');
        setHealthIssues(healthRes.data?.issues || []);
      } catch (e) {
        console.log('No health data available');
      }
      
      // Load relationships (if endpoint exists)
      try {
        const relRes = await api.get('/status/relationships');
        setRelationships(relRes.data?.relationships || []);
      } catch (e) {
        // Generate mock relationships from common columns
        const mockRels = generateMockRelationships(allTables);
        setRelationships(mockRels);
      }
      
    } catch (err) {
      console.error('Failed to load tables:', err);
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
      // Use API for column details, but always use list row count (more reliable)
      setTableDetails({
        ...res.data,
        row_count: knownRowCount // Always use the count from table list
      });
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

  // Generate mock relationships from common columns
  const generateMockRelationships = (allTables) => {
    const rels = [];
    const idColumns = ['employee_id', 'emp_id', 'company_code', 'location_code', 'department_code', 'job_code'];
    
    for (const table of allTables) {
      if (!table.columns) continue;
      
      for (const col of table.columns) {
        const colName = typeof col === 'string' ? col : col.name;
        if (!colName) continue;
        
        const colLower = colName.toLowerCase();
        
        // Check for ID-like columns
        for (const idCol of idColumns) {
          if (colLower.includes(idCol) || colLower === idCol) {
            // Look for potential parent table
            for (const otherTable of allTables) {
              if (otherTable.table_name === table.table_name) continue;
              
              const otherCols = otherTable.columns?.map(c => (typeof c === 'string' ? c : c.name).toLowerCase()) || [];
              if (otherCols.includes(colLower) || otherCols.includes('id')) {
                rels.push({
                  from_table: table.table_name,
                  to_table: otherTable.table_name,
                  column: colName,
                  type: 'N:1'
                });
                break;
              }
            }
            break;
          }
        }
      }
    }
    
    return rels;
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

  // UPDATED: Added classification tab
  const tabs = [
    { id: 'tables', label: '📊 Tables & Fields', icon: FileSpreadsheet },
    { id: 'classification', label: '🔍 Classification', icon: Eye },  // NEW
    { id: 'relationships', label: '🔗 Relationships', icon: Link2 },
    { id: 'health', label: '❤️ Data Health', icon: Heart },
    { id: 'compliance', label: '✅ Compliance', icon: Shield },
    { id: 'rules', label: '📜 Rules', icon: BookOpen },
  ];

  const totalTables = tables.length;
  const totalColumns = tables.reduce((sum, t) => sum + (t.columns?.length || 0), 0);
  const totalIssues = healthIssues.length;

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
          <button
            key={tab.id}
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
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.text }}>{relationships.length}</div>
              <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Relationships</div>
            </div>
          </div>
        </Tooltip>
        
        <Tooltip title="Health Issues" detail="Data quality issues that may affect analysis." action="Review and fix for better results">
          <div style={{ 
            background: totalIssues > 0 ? `${c.warning}10` : c.cardBg, 
            border: `1px solid ${totalIssues > 0 ? c.warning : c.border}`, 
            borderRadius: 10, padding: '1rem 1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', cursor: 'help' 
          }}>
            <span style={{ fontSize: '1.5rem' }}>{totalIssues > 0 ? '⚠️' : '✅'}</span>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: totalIssues > 0 ? c.warning : c.text }}>{totalIssues}</div>
              <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Issues</div>
            </div>
          </div>
        </Tooltip>
      </div>

      {/* Tab Content */}
      {activeTab === 'tables' && (
        <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '1.5rem' }}>
          {/* Table List */}
          <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
            <div style={{ padding: '0.875rem 1rem', background: c.background, borderBottom: `1px solid ${c.border}`, fontWeight: 600, fontSize: '0.9rem', color: c.text }}>
              Tables ({tables.length})
            </div>
            <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
              {tables.map((table, i) => {
                const health = getTableHealth(table.table_name);
                const displayName = table.display_name || table.table_name;
                const uploadedAt = table.created_at ? new Date(table.created_at).toLocaleDateString() : null;
                const uploadedBy = table.uploaded_by;
                return (
                  <div
                    key={i}
                    onClick={() => setSelectedTable(table.table_name)}
                    title={table.table_name}
                    style={{
                      padding: '0.75rem 1rem', borderBottom: `1px solid ${c.border}`, cursor: 'pointer',
                      background: selectedTable === table.table_name ? `${c.primary}15` : 'transparent',
                      borderLeft: selectedTable === table.table_name ? `3px solid ${c.primary}` : '3px solid transparent',
                      transition: 'all 0.15s'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 500, fontSize: '0.85rem', color: c.text }}>
                      <span style={{ 
                        width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                        background: health === 'good' ? c.accent : health === 'warning' ? c.warning : c.scarletSage
                      }} />
                      <span style={{ 
                        overflow: 'hidden', 
                        textOverflow: 'ellipsis', 
                        whiteSpace: 'nowrap',
                        maxWidth: '200px'
                      }}>
                        {displayName}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: c.textMuted, marginTop: '0.25rem' }}>
                      {(table.row_count || 0).toLocaleString()} rows • {table.column_count || table.columns?.length || 0} columns
                      {uploadedAt && ` • ${uploadedAt}`}
                      {uploadedBy && ` • by ${uploadedBy}`}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Table Detail */}
          <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
            {loadingDetails ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: c.textMuted }}>
                <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
              </div>
            ) : tableDetails ? (
              <>
                <div style={{ padding: '1rem 1.25rem', background: c.background, borderBottom: `1px solid ${c.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontWeight: 600, fontSize: '1.1rem', color: c.text }}>
                      🗄️ {tableDetails.display_name || tableDetails.table_name}
                    </div>
                    {tableDetails.display_name && tableDetails.display_name !== tableDetails.table_name && (
                      <div style={{ fontSize: '0.7rem', color: c.textMuted, fontFamily: 'monospace' }}>
                        {tableDetails.table_name}
                      </div>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {/* NEW: View Classification button */}
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
                    <span style={{ background: `${c.accent}15`, color: c.accent, padding: '0.25rem 0.6rem', borderRadius: 6, fontSize: '0.75rem', fontWeight: 500 }}>
                      {(tableDetails.row_count || 0).toLocaleString()} rows
                    </span>
                  </div>
                </div>
                
                <div style={{ padding: '1.25rem' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem', background: c.background, fontSize: '0.7rem', fontWeight: 600, color: c.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: `1px solid ${c.border}` }}>Column</th>
                        <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem', background: c.background, fontSize: '0.7rem', fontWeight: 600, color: c.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: `1px solid ${c.border}` }}>Type</th>
                        <th style={{ textAlign: 'left', padding: '0.6rem 0.75rem', background: c.background, fontSize: '0.7rem', fontWeight: 600, color: c.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: `1px solid ${c.border}` }}>Fill Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tableDetails.columns?.map((col, i) => {
                        const colName = typeof col === 'string' ? col : col.name;
                        const colType = typeof col === 'string' ? 'VARCHAR' : (col.type || 'VARCHAR');
                        const fillRate = typeof col === 'string' ? 100 : (col.fill_rate ?? 100);
                        const isKey = colName.toLowerCase().includes('_id') || colName.toLowerCase() === 'id';
                        
                        return (
                          <tr key={i}>
                            <td style={{ padding: '0.6rem 0.75rem', borderBottom: `1px solid ${c.border}`, fontSize: '0.85rem' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 500, color: c.text }}>
                                {isKey && <Key size={12} style={{ color: c.warning }} />}
                                {colName}
                              </div>
                            </td>
                            <td style={{ padding: '0.6rem 0.75rem', borderBottom: `1px solid ${c.border}` }}>
                              <span style={{ fontSize: '0.75rem', color: c.textMuted, fontFamily: 'monospace' }}>{colType}</span>
                            </td>
                            <td style={{ padding: '0.6rem 0.75rem', borderBottom: `1px solid ${c.border}` }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <div style={{ width: 60, height: 6, background: c.border, borderRadius: 3, overflow: 'hidden' }}>
                                  <div style={{ height: '100%', width: `${fillRate}%`, background: getFillRateColor(fillRate), borderRadius: 3 }} />
                                </div>
                                <span style={{ fontSize: '0.8rem', color: getFillRateColor(fillRate) }}>{fillRate}%</span>
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
              <div style={{ padding: '3rem', textAlign: 'center', color: c.textMuted }}>
                Select a table to view details
              </div>
            )}
          </div>
        </div>
      )}

      {/* NEW: Classification Tab */}
      {activeTab === 'classification' && (
        <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '1.5rem' }}>
          {/* Table List */}
          <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
            <div style={{ padding: '0.875rem 1rem', background: c.background, borderBottom: `1px solid ${c.border}`, fontWeight: 600, fontSize: '0.9rem', color: c.text }}>
              Select Table
            </div>
            <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
              {tables.map((table, i) => {
                const displayName = table.display_name || table.table_name;
                const uploadedAt = table.created_at ? new Date(table.created_at).toLocaleDateString() : null;
                const uploadedBy = table.uploaded_by;
                return (
                  <div
                    key={i}
                    onClick={() => setSelectedTable(table.table_name)}
                    title={table.table_name}
                    style={{
                      padding: '0.75rem 1rem', borderBottom: `1px solid ${c.border}`, cursor: 'pointer',
                      background: selectedTable === table.table_name ? `${c.royalPurple}15` : 'transparent',
                      borderLeft: selectedTable === table.table_name ? `3px solid ${c.royalPurple}` : '3px solid transparent',
                    }}
                  >
                    <div style={{ fontWeight: 500, fontSize: '0.85rem', color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {displayName}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: c.textMuted, marginTop: '0.15rem' }}>
                      {(table.row_count || 0).toLocaleString()} rows
                      {uploadedAt && ` • ${uploadedAt}`}
                      {uploadedBy && ` • by ${uploadedBy}`}
                    </div>
                  </div>
                );
              })}
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

      {/* Relationships Tab */}
      {activeTab === 'relationships' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: c.text, fontSize: '1.1rem' }}>
              <Link2 size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              Detected Relationships ({relationships.length})
            </h3>
            <button
              onClick={() => alert('Relationship editor coming soon - will allow adding/editing/removing relationships')}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.35rem',
                padding: '0.4rem 0.75rem', background: `${c.primary}15`,
                border: `1px solid ${c.primary}40`, borderRadius: 6,
                fontSize: '0.75rem', color: c.primary, cursor: 'pointer',
              }}
            >
              <Edit3 size={12} /> Edit Mappings
            </button>
          </div>
          
          {relationships.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: c.textMuted }}>
              <Link2 size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
              <p>No relationships detected yet.</p>
              <p style={{ fontSize: '0.85rem' }}>Upload related files to see FK/PK relationships.</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              {relationships.map((rel, i) => {
                // NORMALIZE: Handle all field name formats
                // Backend may return: source_table/target_table OR from_table/to_table
                // Column may be: source_column/target_column OR from_column/to_column OR just 'column'
                const fromTable = rel.from_table || rel.source_table || '?';
                const toTable = rel.to_table || rel.target_table || '?';
                const fromCol = rel.from_column || rel.source_column || rel.column || '?';
                const toCol = rel.to_column || rel.target_column || rel.column || '?';
                const confidence = rel.confidence || rel.type || 'detected';
                const needsReview = rel.needs_review || confidence === 'low';
                
                return (
                  <div key={i} style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '0.75rem',
                    padding: '0.75rem 1rem',
                    background: needsReview ? `${c.warning}08` : c.background,
                    borderRadius: 8,
                    border: `1px solid ${needsReview ? c.warning + '40' : c.border}`
                  }}>
                    {/* From side */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.7rem', color: c.textMuted, marginBottom: '0.15rem' }}>From</div>
                      <code style={{ 
                        fontSize: '0.8rem', color: c.primary,
                        display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                      }}>
                        {fromTable}
                      </code>
                      <code style={{ fontSize: '0.75rem', color: c.textMuted }}>
                        .{fromCol}
                      </code>
                    </div>
                    
                    {/* Arrow */}
                    <div style={{ color: c.textMuted, fontSize: '1.2rem' }}>→</div>
                    
                    {/* To side */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.7rem', color: c.textMuted, marginBottom: '0.15rem' }}>To</div>
                      <code style={{ 
                        fontSize: '0.8rem', color: c.accent,
                        display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                      }}>
                        {toTable}
                      </code>
                      <code style={{ fontSize: '0.75rem', color: c.textMuted }}>
                        .{toCol}
                      </code>
                    </div>
                    
                    {/* Confidence badge */}
                    <div style={{ 
                      fontSize: '0.7rem', 
                      padding: '0.25rem 0.5rem', 
                      background: needsReview ? `${c.warning}15` : `${c.success}15`, 
                      color: needsReview ? c.warning : c.success, 
                      borderRadius: 4,
                      whiteSpace: 'nowrap',
                    }}>
                      {needsReview && '⚠ '}{confidence}
                    </div>
                    
                    {/* Action buttons */}
                    <div style={{ display: 'flex', gap: '0.25rem' }}>
                      <button
                        onClick={() => alert(`Confirm relationship: ${fromTable}.${fromCol} → ${toTable}.${toCol}`)}
                        title="Confirm this relationship"
                        style={{
                          padding: '0.25rem 0.4rem', background: `${c.success}15`,
                          border: `1px solid ${c.success}30`, borderRadius: 4,
                          cursor: 'pointer', color: c.success, fontSize: '0.7rem',
                        }}
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => alert(`Remove relationship: ${fromTable}.${fromCol} → ${toTable}.${toCol}`)}
                        title="Remove this relationship"
                        style={{
                          padding: '0.25rem 0.4rem', background: `${c.scarletSage}15`,
                          border: `1px solid ${c.scarletSage}30`, borderRadius: 4,
                          cursor: 'pointer', color: c.scarletSage, fontSize: '0.7rem',
                        }}
                      >
                        ✗
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          
          {/* Legend */}
          <div style={{ 
            marginTop: '1rem', paddingTop: '1rem', borderTop: `1px solid ${c.border}`,
            display: 'flex', gap: '1.5rem', fontSize: '0.75rem', color: c.textMuted
          }}>
            <span>🔗 Detected via column name matching</span>
            <span>⚠ Low confidence = needs manual review</span>
          </div>
        </div>
      )}

      {/* Data Health Tab */}
      {activeTab === 'health' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: c.text, fontSize: '1.1rem' }}>
              <Heart size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              Data Health
            </h3>
            <button
              onClick={loadData}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.35rem',
                padding: '0.4rem 0.75rem', background: c.background,
                border: `1px solid ${c.border}`, borderRadius: 6,
                fontSize: '0.75rem', color: c.textMuted, cursor: 'pointer',
              }}
            >
              <RefreshCw size={12} /> Re-check
            </button>
          </div>
          
          {/* Health checks performed - always show */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: c.text, marginBottom: '0.75rem' }}>
              Checks Performed
            </div>
            <div style={{ display: 'grid', gap: '0.5rem' }}>
              {[
                { 
                  name: 'Orphaned Tables', 
                  desc: 'DuckDB tables without registry entry',
                  passed: healthIssues.filter(i => i.type === 'orphaned_table').length === 0,
                  count: healthIssues.filter(i => i.type === 'orphaned_table').length,
                },
                { 
                  name: 'Registry Sync', 
                  desc: 'Document registry matches stored data',
                  passed: healthIssues.filter(i => i.type === 'registry_mismatch').length === 0,
                  count: healthIssues.filter(i => i.type === 'registry_mismatch').length,
                },
                { 
                  name: 'ChromaDB Orphans', 
                  desc: 'Embedded chunks with valid sources',
                  passed: healthIssues.filter(i => i.type === 'orphaned_chunk').length === 0,
                  count: healthIssues.filter(i => i.type === 'orphaned_chunk').length,
                },
                { 
                  name: 'Row Count Integrity', 
                  desc: 'Stored row counts match actual data',
                  passed: healthIssues.filter(i => i.type === 'count_mismatch').length === 0,
                  count: healthIssues.filter(i => i.type === 'count_mismatch').length,
                },
              ].map((check, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: '0.75rem',
                  padding: '0.6rem 0.75rem', background: c.background,
                  borderRadius: 6, border: `1px solid ${c.border}`,
                }}>
                  {check.passed ? (
                    <CheckCircle size={16} style={{ color: c.success, flexShrink: 0 }} />
                  ) : (
                    <XCircle size={16} style={{ color: c.scarletSage, flexShrink: 0 }} />
                  )}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 500, color: c.text }}>
                      {check.name}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: c.textMuted }}>
                      {check.desc}
                    </div>
                  </div>
                  <div style={{
                    fontSize: '0.7rem', padding: '0.2rem 0.5rem',
                    background: check.passed ? `${c.success}15` : `${c.scarletSage}15`,
                    color: check.passed ? c.success : c.scarletSage,
                    borderRadius: 4,
                  }}>
                    {check.passed ? 'PASS' : `${check.count} issue${check.count !== 1 ? 's' : ''}`}
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Issues section */}
          {healthIssues.length === 0 ? (
            <div style={{ 
              textAlign: 'center', padding: '2rem', 
              background: `${c.success}08`, borderRadius: 8,
              border: `1px solid ${c.success}30`
            }}>
              <CheckCircle size={36} style={{ color: c.success, marginBottom: '0.75rem' }} />
              <p style={{ fontWeight: 600, color: c.success, margin: '0 0 0.25rem' }}>
                All checks passed!
              </p>
              <p style={{ fontSize: '0.85rem', color: c.textMuted, margin: 0 }}>
                No data integrity issues detected across {tables.length} table(s).
              </p>
            </div>
          ) : (
            <div>
              <div style={{ 
                fontSize: '0.8rem', fontWeight: 600, color: c.scarletSage, marginBottom: '0.75rem',
                display: 'flex', alignItems: 'center', gap: '0.5rem'
              }}>
                <AlertTriangle size={14} />
                {healthIssues.length} Issue{healthIssues.length !== 1 ? 's' : ''} Found
              </div>
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
                    {issue.table && (
                      <code style={{ 
                        fontSize: '0.75rem', color: c.primary, marginTop: '0.25rem', display: 'block' 
                      }}>
                        {issue.table}
                      </code>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Health criteria legend */}
          <div style={{ 
            marginTop: '1.5rem', paddingTop: '1rem', borderTop: `1px solid ${c.border}`,
            fontSize: '0.75rem', color: c.textMuted
          }}>
            <strong>How health is determined:</strong> XLR8 checks that all stored tables are registered, 
            row counts match between registry and actual data, and no orphaned embeddings exist in ChromaDB.
            Run playbooks to check business rule compliance.
          </div>
        </div>
      )}

      {/* Compliance Tab */}
      {activeTab === 'compliance' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: c.text, fontSize: '1.1rem' }}>
              <Shield size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} />
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
              disabled={complianceRunning}
              style={{
                padding: '0.5rem 1rem',
                background: c.primary,
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: complianceRunning ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
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
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem', color: c.textMuted }}>
              <Shield size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
              <p>Click "Run Check" to validate data against standards.</p>
            </div>
          )}
        </div>
      )}

      {/* Rules Tab */}
      {activeTab === 'rules' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: c.text, fontSize: '1.1rem' }}>
              <BookOpen size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              Extracted Rules ({rules.length})
            </h3>
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
              Load Rules
            </button>
          </div>
          
          {rules.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: c.textMuted }}>
              <BookOpen size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
              <p>No rules extracted yet.</p>
              <p style={{ fontSize: '0.85rem' }}>Upload standards documents to extract validation rules.</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              {rules.map((rule, i) => (
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
