/**
 * DataExplorer.jsx - Tables, Fields, Relationships, Health, Compliance
 * =====================================================================
 * 
 * Deploy to: frontend/src/pages/DataExplorer.jsx
 * 
 * Features:
 * - View all tables and columns
 * - See data types and fill rates
 * - View detected relationships
 * - Data health issues with actions
 * - Compliance check against extracted rules
 * - Mission Control color scheme
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Database, FileSpreadsheet, Link2, Heart, ChevronDown, ChevronRight,
  ArrowLeft, RefreshCw, CheckCircle, AlertTriangle, XCircle, Key, Loader2,
  Shield, Play, Folder, BookOpen, Code, Trash2, Edit3, Sparkles
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useProject } from '../context/ProjectContext';
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

  // Run compliance check against extracted rules
  const runComplianceCheck = async () => {
    if (!activeProject?.id) {
      setComplianceError('Please select a project first');
      return;
    }
    
    setComplianceRunning(true);
    setComplianceError(null);
    setComplianceResults(null);
    
    try {
      const response = await api.post('/status/standards/check', { project_id: activeProject.id }, { timeout: 180000 });
      setComplianceResults(response.data);
    } catch (err) {
      setComplianceError(err.response?.data?.detail || err.message || 'Compliance check failed');
    } finally {
      setComplianceRunning(false);
    }
  };

  // Load extracted rules
  const loadRules = async () => {
    setLoadingRules(true);
    try {
      const response = await api.get('/status/rules');
      setRules(response.data?.rules || []);
    } catch (err) {
      console.log('Could not load rules:', err);
      // Try fallback to references endpoint
      try {
        const refRes = await api.get('/status/references');
        setRules(refRes.data?.rules || []);
      } catch (e) {
        setRules([]);
      }
    } finally {
      setLoadingRules(false);
    }
  };

  // Load rules when switching to rules tab
  useEffect(() => {
    if (activeTab === 'rules') {
      loadRules();
    }
  }, [activeTab]);

  // Extract table names from SQL query
  const extractTablesFromSQL = (sql) => {
    if (!sql) return [];
    const upperSQL = sql.toUpperCase();
    const tables = new Set();
    
    // Match FROM table_name and JOIN table_name patterns
    const fromMatch = upperSQL.match(/FROM\s+([a-zA-Z0-9_]+)/gi);
    const joinMatch = upperSQL.match(/JOIN\s+([a-zA-Z0-9_]+)/gi);
    
    if (fromMatch) {
      fromMatch.forEach(m => {
        const tableName = m.replace(/FROM\s+/i, '').toLowerCase();
        if (!['select', 'where', 'and', 'or'].includes(tableName)) {
          tables.add(tableName);
        }
      });
    }
    if (joinMatch) {
      joinMatch.forEach(m => {
        const tableName = m.replace(/JOIN\s+/i, '').toLowerCase();
        tables.add(tableName);
      });
    }
    
    return Array.from(tables);
  };

  // Check if tables exist in user's data
  const getTableStatus = (sqlTables) => {
    const userTables = tables.map(t => t.table_name?.toLowerCase() || t.name?.toLowerCase());
    return sqlTables.map(t => ({
      name: t,
      exists: userTables.includes(t.toLowerCase())
    }));
  };

  // Test SQL query against DuckDB
  const testRuleSQL = async (ruleId, sql) => {
    setTestingRule(ruleId);
    try {
      const response = await api.post('/status/test-sql', { sql }, { timeout: 30000 });
      setTestResults(prev => ({
        ...prev,
        [ruleId]: {
          success: true,
          rowCount: response.data?.row_count || 0,
          columns: response.data?.columns || [],
          sample: response.data?.sample || [],
          error: null
        }
      }));
    } catch (err) {
      setTestResults(prev => ({
        ...prev,
        [ruleId]: {
          success: false,
          rowCount: 0,
          columns: [],
          sample: [],
          error: err.response?.data?.detail || err.message
        }
      }));
    } finally {
      setTestingRule(null);
    }
  };

  // Generate SQL pattern for a rule using LLM
  const generateSQL = async (ruleId) => {
    setGeneratingSQL(ruleId);
    try {
      const response = await api.post(`/status/rules/${ruleId}/generate-sql`, {}, { timeout: 60000 });
      if (response.data?.success && response.data?.sql) {
        // Update the rule in local state with the new SQL
        setRules(prev => prev.map(r => 
          r.rule_id === ruleId 
            ? { ...r, suggested_sql_pattern: response.data.sql }
            : r
        ));
      } else {
        alert('Could not generate SQL: ' + (response.data?.error || 'Unknown error'));
      }
    } catch (err) {
      alert('Failed to generate SQL: ' + (err.response?.data?.detail || err.message));
    } finally {
      setGeneratingSQL(null);
    }
  };

  // Generate mock relationships based on common column patterns
  const generateMockRelationships = (tables) => {
    const rels = [];
    const keyColumns = ['employee_id', 'emp_id', 'company_code', 'co_code', 'dept_id', 'location_id'];
    
    tables.forEach(table => {
      const cols = table.columns?.map(c => typeof c === 'string' ? c : c.name) || [];
      cols.forEach(col => {
        const colLower = col.toLowerCase();
        if (keyColumns.some(k => colLower.includes(k))) {
          // Find other tables with same column
          tables.forEach(otherTable => {
            if (otherTable.table_name !== table.table_name) {
              const otherCols = otherTable.columns?.map(c => typeof c === 'string' ? c : c.name) || [];
              if (otherCols.some(oc => oc.toLowerCase() === colLower)) {
                // Avoid duplicates
                if (!rels.some(r => 
                  (r.from_table === table.table_name && r.to_table === otherTable.table_name && r.column === col) ||
                  (r.from_table === otherTable.table_name && r.to_table === table.table_name && r.column === col)
                )) {
                  rels.push({
                    from_table: table.table_name,
                    to_table: otherTable.table_name,
                    column: col,
                    type: colLower.includes('employee') ? '1:1' : 'N:1'
                  });
                }
              }
            }
          });
        }
      });
    });
    
    return rels;
  };

  const getTableHealth = (tableName) => {
    const issues = healthIssues.filter(i => i.table === tableName);
    if (issues.some(i => i.severity === 'error')) return 'error';
    if (issues.some(i => i.severity === 'warning')) return 'warning';
    return 'good';
  };

  const getFillRateColor = (rate) => {
    if (rate >= 90) return c.accent;
    if (rate >= 50) return c.warning;
    return c.scarletSage;
  };

  const tabs = [
    { id: 'tables', label: '📊 Tables & Fields', icon: FileSpreadsheet },
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
                return (
                  <div
                    key={i}
                    onClick={() => setSelectedTable(table.table_name)}
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
                      {table.table_name}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: c.textMuted, marginTop: '0.25rem' }}>
                      {(table.row_count || 0).toLocaleString()} rows • {table.columns?.length || 0} columns
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
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontWeight: 600, fontSize: '1.1rem', color: c.text }}>
                    🗄️ {tableDetails.table_name}
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
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
                  
                  {/* Table Relationships */}
                  {(() => {
                    const tableRels = relationships.filter(r => r.from_table === selectedTable || r.to_table === selectedTable);
                    if (tableRels.length === 0) return null;
                    
                    return (
                      <div style={{ marginTop: '1.5rem' }}>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem', color: c.text, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          🔗 Relationships
                        </div>
                        {tableRels.map((rel, i) => (
                          <div key={i} style={{ background: c.background, border: `1px solid ${c.border}`, borderRadius: 8, padding: '0.75rem 1rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <span style={{ fontWeight: 500, fontSize: '0.85rem', color: c.text }}>{rel.from_table}</span>
                            <span style={{ fontSize: '0.8rem', color: c.textMuted, fontFamily: 'monospace' }}>{rel.column}</span>
                            <span style={{ color: c.primary, fontSize: '1.1rem' }}>→</span>
                            <span style={{ fontWeight: 500, fontSize: '0.85rem', color: c.text }}>{rel.to_table}</span>
                            <span style={{ fontSize: '0.7rem', color: c.textMuted, padding: '0.15rem 0.4rem', background: c.cardBg, borderRadius: 4 }}>{rel.type}</span>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
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

      {activeTab === 'relationships' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
          <div style={{ padding: '1rem 1.25rem', background: c.background, borderBottom: `1px solid ${c.border}`, fontWeight: 600, color: c.text }}>
            All Relationships ({relationships.length})
          </div>
          <div style={{ padding: '1rem' }}>
            {relationships.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
                No relationships detected yet
              </div>
            ) : (
              relationships.map((rel, i) => (
                <div key={i} style={{ background: c.background, border: `1px solid ${c.border}`, borderRadius: 8, padding: '0.875rem 1rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <span style={{ fontWeight: 500, fontSize: '0.9rem', color: c.text }}>{rel.from_table}</span>
                  <span style={{ fontSize: '0.8rem', color: c.textMuted, fontFamily: 'monospace', background: c.cardBg, padding: '0.2rem 0.5rem', borderRadius: 4 }}>{rel.column}</span>
                  <span style={{ color: c.primary, fontSize: '1.25rem' }}>→</span>
                  <span style={{ fontWeight: 500, fontSize: '0.9rem', color: c.text }}>{rel.to_table}</span>
                  <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: c.textMuted, padding: '0.2rem 0.5rem', background: c.cardBg, borderRadius: 4 }}>{rel.type}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {activeTab === 'health' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
          <div style={{ padding: '1rem 1.25rem', background: c.background, borderBottom: `1px solid ${c.border}`, fontWeight: 600, color: c.text }}>
            Data Health Issues ({healthIssues.length})
          </div>
          <div style={{ padding: '1rem' }}>
            {healthIssues.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center' }}>
                <CheckCircle size={40} style={{ color: c.accent, marginBottom: '0.75rem' }} />
                <p style={{ color: c.text, fontWeight: 500, margin: '0 0 0.25rem' }}>All systems healthy</p>
                <p style={{ color: c.textMuted, fontSize: '0.85rem', margin: 0 }}>No data quality issues detected</p>
              </div>
            ) : (
              healthIssues.map((issue, i) => (
                <div key={i} style={{ 
                  background: issue.severity === 'error' ? `${c.scarletSage}10` : `${c.warning}10`, 
                  border: `1px solid ${issue.severity === 'error' ? c.scarletSage : c.warning}30`, 
                  borderRadius: 8, padding: '0.875rem 1rem', marginBottom: '0.5rem',
                  display: 'flex', alignItems: 'flex-start', gap: '0.75rem'
                }}>
                  {issue.severity === 'error' 
                    ? <XCircle size={18} style={{ color: c.scarletSage, flexShrink: 0, marginTop: 2 }} />
                    : <AlertTriangle size={18} style={{ color: c.warning, flexShrink: 0, marginTop: 2 }} />
                  }
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500, fontSize: '0.9rem', color: c.text }}>{issue.title}</div>
                    <div style={{ fontSize: '0.8rem', color: c.textMuted, marginTop: '0.25rem' }}>{issue.description}</div>
                    {issue.table && (
                      <div style={{ fontSize: '0.75rem', color: c.textMuted, marginTop: '0.35rem' }}>
                        Table: <span style={{ fontFamily: 'monospace' }}>{issue.table}</span>
                      </div>
                    )}
                    {issue.action && (
                      <div style={{ fontSize: '0.8rem', color: c.primary, marginTop: '0.5rem', cursor: 'pointer' }}>
                        → {issue.action}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {activeTab === 'compliance' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
          <div style={{ padding: '1rem 1.25rem', background: c.background, borderBottom: `1px solid ${c.border}`, fontWeight: 600, color: c.text, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Shield size={18} style={{ color: c.primary }} />
            Compliance Check
          </div>
          <div style={{ padding: '1.25rem' }}>
            {/* Project Context */}
            {activeProject ? (
              <div style={{ padding: '1rem', background: `${c.primary}10`, border: `1px solid ${c.primary}40`, borderLeft: `4px solid ${c.primary}`, borderRadius: 8, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <Folder size={24} style={{ color: c.primary }} />
                <div>
                  <div style={{ fontWeight: 600, color: c.primary }}>{activeProject.name}</div>
                  <div style={{ fontSize: '0.85rem', color: c.textMuted }}>Run compliance check against extracted rules</div>
                </div>
              </div>
            ) : (
              <div style={{ padding: '1rem', background: `${c.warning}10`, border: `1px solid ${c.warning}40`, borderRadius: 8, marginBottom: '1.5rem', color: c.warning }}>
                ⚠️ Select a project to run compliance checks
              </div>
            )}
            
            {/* Run Button */}
            <Tooltip title="Run Compliance Check" detail="Compares your data against extracted rules from uploaded regulatory and compliance documents." action="Results show rule violations with corrective actions">
              <button 
                onClick={runComplianceCheck} 
                disabled={complianceRunning || !activeProject}
                style={{ 
                  padding: '0.75rem 1.5rem', background: c.primary, color: 'white', 
                  border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer', 
                  opacity: (complianceRunning || !activeProject) ? 0.5 : 1, 
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  transition: 'all 0.2s'
                }}
              >
                {complianceRunning ? (
                  <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Running...</>
                ) : (
                  <><Play size={16} /> Run Compliance Check</>
                )}
              </button>
            </Tooltip>

            {/* Error */}
            {complianceError && (
              <div style={{ padding: '1rem', background: `${c.scarletSage}10`, border: `1px solid ${c.scarletSage}40`, borderRadius: 8, marginTop: '1rem', color: c.scarletSage, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <XCircle size={18} /> {complianceError}
              </div>
            )}

            {/* Results */}
            {complianceResults && (
              <div style={{ marginTop: '1.5rem' }}>
                {/* Stats Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                  <Tooltip title="Rules Checked" detail="Total rules extracted from your uploaded compliance documents." action="Upload more docs to add rules">
                    <div style={{ padding: '1rem', background: c.background, border: `1px solid ${c.border}`, borderRadius: 8, textAlign: 'center', cursor: 'help' }}>
                      <div style={{ fontSize: '2rem', fontWeight: 700, color: c.primary, fontFamily: 'monospace' }}>{complianceResults.rules_checked || 0}</div>
                      <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Rules Checked</div>
                    </div>
                  </Tooltip>
                  <Tooltip title="Findings" detail="Rules that found violations in your data." action="Review each finding below">
                    <div style={{ padding: '1rem', background: c.background, border: `1px solid ${c.border}`, borderRadius: 8, textAlign: 'center', cursor: 'help' }}>
                      <div style={{ fontSize: '2rem', fontWeight: 700, color: (complianceResults.findings_count || 0) > 0 ? c.warning : c.accent, fontFamily: 'monospace' }}>{complianceResults.findings_count || 0}</div>
                      <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Findings</div>
                    </div>
                  </Tooltip>
                  <Tooltip title="Compliant" detail="Rules that passed with no violations." action="Great job!">
                    <div style={{ padding: '1rem', background: c.background, border: `1px solid ${c.border}`, borderRadius: 8, textAlign: 'center', cursor: 'help' }}>
                      <div style={{ fontSize: '2rem', fontWeight: 700, color: c.accent, fontFamily: 'monospace' }}>{complianceResults.compliant_count || 0}</div>
                      <div style={{ fontSize: '0.8rem', color: c.textMuted }}>Compliant</div>
                    </div>
                  </Tooltip>
                </div>

                {/* Findings List */}
                {complianceResults.findings && complianceResults.findings.length > 0 && (
                  <div>
                    <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.9rem', fontWeight: 600, color: c.text, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <AlertTriangle size={16} style={{ color: c.warning }} />
                      Findings ({complianceResults.findings.length})
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {complianceResults.findings.map((finding, i) => {
                        const severityColor = finding.severity === 'critical' ? c.scarletSage : finding.severity === 'high' ? c.warning : c.electricBlue;
                        return (
                          <div key={i} style={{ 
                            background: c.background, 
                            border: `1px solid ${c.border}`, 
                            borderLeft: `4px solid ${severityColor}`, 
                            borderRadius: 8, 
                            padding: '1rem' 
                          }}>
                            <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: c.text, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <span>{finding.condition || finding.title}</span>
                              <span style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem', background: `${severityColor}20`, color: severityColor, borderRadius: 4, textTransform: 'uppercase' }}>
                                {finding.severity || 'medium'}
                              </span>
                            </div>
                            {finding.criteria && (
                              <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: c.text }}>
                                <strong>Criteria:</strong> {finding.criteria}
                              </p>
                            )}
                            {finding.cause && (
                              <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: c.text }}>
                                <strong>Cause:</strong> {finding.cause}
                              </p>
                            )}
                            {finding.corrective_action && (
                              <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: c.primary }}>
                                <strong>Action:</strong> {finding.corrective_action}
                              </p>
                            )}
                            {finding.affected_count && (
                              <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: c.textMuted, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <Database size={14} />
                                Affected: {finding.affected_count.toLocaleString()} records
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* All Clear Message */}
                {(!complianceResults.findings || complianceResults.findings.length === 0) && (
                  <div style={{ padding: '2rem', textAlign: 'center' }}>
                    <CheckCircle size={48} style={{ color: c.accent, marginBottom: '0.75rem' }} />
                    <p style={{ color: c.text, fontWeight: 600, margin: '0 0 0.25rem', fontSize: '1.1rem' }}>All Clear!</p>
                    <p style={{ color: c.textMuted, fontSize: '0.9rem', margin: 0 }}>No compliance issues found in your data</p>
                  </div>
                )}
              </div>
            )}

            {/* Empty State */}
            {!complianceResults && !complianceRunning && !complianceError && (
              <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted, marginTop: '1rem' }}>
                <Shield size={40} style={{ opacity: 0.3, marginBottom: '0.75rem' }} />
                <p style={{ margin: '0 0 0.5rem', fontWeight: 500, color: c.text }}>Ready to check compliance</p>
                <p style={{ margin: 0, fontSize: '0.85rem' }}>
                  Upload regulatory documents to the Reference Library, then run a check to find violations in your data.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Rules Tab */}
      {activeTab === 'rules' && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
          <div style={{ padding: '1rem 1.25rem', background: c.background, borderBottom: `1px solid ${c.border}`, fontWeight: 600, color: c.text, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <BookOpen size={18} style={{ color: c.royalPurple }} />
              Extracted Rules ({rules.length})
            </div>
            <button 
              onClick={loadRules}
              disabled={loadingRules}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.35rem',
                padding: '0.4rem 0.75rem', background: 'transparent', border: `1px solid ${c.border}`,
                borderRadius: 6, fontSize: '0.8rem', color: c.textMuted, cursor: 'pointer'
              }}
            >
              <RefreshCw size={14} style={{ animation: loadingRules ? 'spin 1s linear infinite' : 'none' }} /> Refresh
            </button>
          </div>
          <div style={{ padding: '1rem' }}>
            {loadingRules ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
                <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: '0.5rem' }} />
                <p>Loading rules...</p>
              </div>
            ) : rules.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center' }}>
                <BookOpen size={48} style={{ color: c.textMuted, opacity: 0.3, marginBottom: '0.75rem' }} />
                <p style={{ color: c.text, fontWeight: 500, margin: '0 0 0.5rem' }}>No rules extracted yet</p>
                <p style={{ color: c.textMuted, fontSize: '0.85rem', margin: 0 }}>
                  Upload regulatory documents (IRS Pub 15, SECURE 2.0, etc.) to the Reference Library to extract compliance rules.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {rules.map((rule, i) => {
                  const severityColor = rule.severity === 'critical' ? c.scarletSage : rule.severity === 'high' ? c.warning : c.electricBlue;
                  return (
                    <div key={i} style={{ 
                      background: c.background, 
                      border: `1px solid ${c.border}`, 
                      borderLeft: `4px solid ${severityColor}`, 
                      borderRadius: 8, 
                      padding: '1rem',
                      overflow: 'hidden'
                    }}>
                      {/* Rule Header */}
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600, color: c.text, marginBottom: '0.25rem' }}>
                            {rule.title || rule.rule_id || `Rule ${i + 1}`}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: c.textMuted }}>
                            Source: {rule.source_document || 'Unknown'}
                            {rule.source_section && ` • ${rule.source_section}`}
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ 
                            fontSize: '0.7rem', padding: '0.2rem 0.5rem', 
                            background: `${severityColor}20`, color: severityColor, 
                            borderRadius: 4, textTransform: 'uppercase', fontWeight: 600 
                          }}>
                            {rule.severity || 'medium'}
                          </span>
                        </div>
                      </div>
                      
                      {/* Rule Description */}
                      {rule.description && (
                        <p style={{ fontSize: '0.85rem', color: c.text, margin: '0.5rem 0', lineHeight: 1.5 }}>
                          {rule.description}
                        </p>
                      )}
                      
                      {/* Rule Details */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginTop: '0.75rem' }}>
                        {rule.applies_to && Object.keys(rule.applies_to).length > 0 && (
                          <div style={{ background: c.cardBg, padding: '0.5rem 0.75rem', borderRadius: 6, border: `1px solid ${c.border}` }}>
                            <div style={{ fontSize: '0.7rem', color: c.textMuted, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Applies To</div>
                            <div style={{ fontSize: '0.8rem', color: c.text, fontFamily: 'monospace' }}>
                              {JSON.stringify(rule.applies_to)}
                            </div>
                          </div>
                        )}
                        {rule.requirement && Object.keys(rule.requirement).length > 0 && (
                          <div style={{ background: c.cardBg, padding: '0.5rem 0.75rem', borderRadius: 6, border: `1px solid ${c.border}` }}>
                            <div style={{ fontSize: '0.7rem', color: c.textMuted, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Requirement</div>
                            <div style={{ fontSize: '0.8rem', color: c.text, fontFamily: 'monospace' }}>
                              {JSON.stringify(rule.requirement)}
                            </div>
                          </div>
                        )}
                      </div>
                      
                      {/* SQL Query Pattern - or Generate Button */}
                      {rule.suggested_sql_pattern ? (
                        <div style={{ marginTop: '0.75rem' }}>
                          <div style={{ 
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            marginBottom: '0.35rem' 
                          }}>
                            <div style={{ 
                              display: 'flex', alignItems: 'center', gap: '0.5rem', 
                              fontSize: '0.7rem', color: c.textMuted, textTransform: 'uppercase'
                            }}>
                              <Code size={12} /> SQL Query Pattern
                            </div>
                            <button
                              onClick={() => testRuleSQL(rule.rule_id, rule.suggested_sql_pattern)}
                              disabled={testingRule === rule.rule_id}
                              style={{
                                display: 'flex', alignItems: 'center', gap: '0.35rem',
                                padding: '0.3rem 0.6rem', 
                                background: c.accent, 
                                border: 'none',
                                borderRadius: 4, 
                                fontSize: '0.75rem', 
                                color: 'white', 
                                cursor: testingRule === rule.rule_id ? 'wait' : 'pointer',
                                opacity: testingRule === rule.rule_id ? 0.7 : 1
                              }}
                            >
                              {testingRule === rule.rule_id ? (
                                <><Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> Testing...</>
                              ) : (
                                <><Play size={12} /> Test Query</>
                              )}
                            </button>
                          </div>
                          
                          {/* Table Validation */}
                          {(() => {
                            const sqlTables = extractTablesFromSQL(rule.suggested_sql_pattern);
                            const tableStatus = getTableStatus(sqlTables);
                            if (sqlTables.length > 0) {
                              return (
                                <div style={{ 
                                  display: 'flex', gap: '0.5rem', flexWrap: 'wrap', 
                                  marginBottom: '0.5rem', fontSize: '0.75rem' 
                                }}>
                                  <span style={{ color: c.textMuted }}>Tables:</span>
                                  {tableStatus.map((t, idx) => (
                                    <span key={idx} style={{ 
                                      display: 'flex', alignItems: 'center', gap: '0.25rem',
                                      padding: '0.15rem 0.4rem',
                                      background: t.exists ? `${c.primary}20` : `${c.scarletSage}20`,
                                      color: t.exists ? c.primary : c.scarletSage,
                                      borderRadius: 4,
                                      fontFamily: 'monospace'
                                    }}>
                                      {t.exists ? <CheckCircle size={10} /> : <XCircle size={10} />}
                                      {t.name}
                                    </span>
                                  ))}
                                </div>
                              );
                            }
                            return null;
                          })()}
                          
                          <div style={{ 
                            background: '#1e1e1e', 
                            color: '#d4d4d4', 
                            padding: '0.75rem', 
                            borderRadius: 6, 
                            fontSize: '0.8rem', 
                            fontFamily: 'monospace',
                            whiteSpace: 'pre-wrap',
                            overflowX: 'auto'
                          }}>
                            {rule.suggested_sql_pattern}
                          </div>
                          
                          {/* Test Results */}
                          {testResults[rule.rule_id] && (
                            <div style={{ 
                              marginTop: '0.5rem', 
                              padding: '0.75rem', 
                              background: testResults[rule.rule_id].success ? `${c.primary}10` : `${c.scarletSage}10`,
                              border: `1px solid ${testResults[rule.rule_id].success ? c.primary : c.scarletSage}`,
                              borderRadius: 6 
                            }}>
                              {testResults[rule.rule_id].success ? (
                                <>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                    <CheckCircle size={16} style={{ color: c.primary }} />
                                    <span style={{ fontWeight: 600, color: c.text }}>
                                      Query returned {testResults[rule.rule_id].rowCount} row(s)
                                    </span>
                                    {testResults[rule.rule_id].rowCount > 0 && (
                                      <span style={{ 
                                        fontSize: '0.7rem', padding: '0.15rem 0.4rem', 
                                        background: c.scarletSage, color: 'white', 
                                        borderRadius: 4 
                                      }}>
                                        POTENTIAL VIOLATION
                                      </span>
                                    )}
                                  </div>
                                  {testResults[rule.rule_id].columns?.length > 0 && (
                                    <div style={{ fontSize: '0.75rem', color: c.textMuted, marginBottom: '0.35rem' }}>
                                      Columns: {testResults[rule.rule_id].columns.join(', ')}
                                    </div>
                                  )}
                                  {testResults[rule.rule_id].sample?.length > 0 && (
                                    <div style={{ 
                                      background: c.cardBg, padding: '0.5rem', borderRadius: 4, 
                                      fontSize: '0.75rem', fontFamily: 'monospace', 
                                      maxHeight: '150px', overflowY: 'auto' 
                                    }}>
                                      <div style={{ fontWeight: 600, marginBottom: '0.25rem', color: c.textMuted }}>Sample Data (first 5 rows):</div>
                                      {testResults[rule.rule_id].sample.map((row, idx) => (
                                        <div key={idx} style={{ color: c.text, borderBottom: `1px solid ${c.border}`, padding: '0.25rem 0' }}>
                                          {JSON.stringify(row)}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </>
                              ) : (
                                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
                                  <XCircle size={16} style={{ color: c.scarletSage, flexShrink: 0, marginTop: '0.1rem' }} />
                                  <div>
                                    <span style={{ fontWeight: 600, color: c.scarletSage }}>Query failed</span>
                                    <div style={{ fontSize: '0.8rem', color: c.text, marginTop: '0.25rem', fontFamily: 'monospace' }}>
                                      {testResults[rule.rule_id].error}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div style={{ marginTop: '0.75rem' }}>
                          <button
                            onClick={() => generateSQL(rule.rule_id)}
                            disabled={generatingSQL === rule.rule_id}
                            style={{
                              display: 'flex', alignItems: 'center', gap: '0.5rem',
                              padding: '0.5rem 1rem',
                              background: `${c.royalPurple}15`,
                              border: `1px dashed ${c.royalPurple}`,
                              borderRadius: 6,
                              fontSize: '0.8rem',
                              color: c.royalPurple,
                              cursor: generatingSQL === rule.rule_id ? 'wait' : 'pointer',
                              width: '100%',
                              justifyContent: 'center'
                            }}
                          >
                            {generatingSQL === rule.rule_id ? (
                              <><Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Generating SQL...</>
                            ) : (
                              <><Sparkles size={14} /> Generate SQL Query</>
                            )}
                          </button>
                          <div style={{ fontSize: '0.7rem', color: c.textMuted, textAlign: 'center', marginTop: '0.35rem' }}>
                            Uses AI to create a compliance check query based on your data
                          </div>
                        </div>
                      )}
                      
                      {/* Source Text */}
                      {rule.source_text && (
                        <div style={{ marginTop: '0.75rem', padding: '0.5rem 0.75rem', background: `${c.skyBlue}10`, borderRadius: 6, borderLeft: `3px solid ${c.skyBlue}` }}>
                          <div style={{ fontSize: '0.7rem', color: c.textMuted, marginBottom: '0.25rem' }}>Original Text</div>
                          <div style={{ fontSize: '0.8rem', color: c.text, fontStyle: 'italic', lineHeight: 1.4 }}>
                            "{rule.source_text.slice(0, 300)}{rule.source_text.length > 300 ? '...' : ''}"
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
      
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
