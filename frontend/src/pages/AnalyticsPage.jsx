/**
 * AnalyticsPage.jsx - BI Query Builder
 * 
 * Clean 3-panel layout: Catalog | Builder | Results
 * - Data Catalog: Browse tables and columns
 * - Query Builder: Visual builder or raw SQL
 * - Results: Data table and charts
 * 
 * Created: January 16, 2026
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useProject } from '../context/ProjectContext';
import api from '../services/api';
import { 
  Database, Table, Columns, Search, Play, Code, BarChart3, 
  ChevronRight, ChevronDown, Loader2, AlertCircle, Download,
  Plus, X, Filter, ArrowUpDown
} from 'lucide-react';

// =============================================================================
// STYLES
// =============================================================================
const styles = {
  container: {
    display: 'grid',
    gridTemplateColumns: '280px 1fr 1fr',
    gap: '16px',
    height: 'calc(100vh - 180px)',
    minHeight: '500px',
  },
  panel: {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  panelHeader: {
    padding: '16px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-tertiary)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexShrink: 0,
  },
  panelTitle: {
    fontSize: 'var(--text-sm)',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: 0,
  },
  panelBody: {
    flex: 1,
    overflow: 'auto',
    padding: '12px',
  },
  searchInput: {
    width: '100%',
    padding: '8px 12px 8px 32px',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    fontSize: 'var(--text-sm)',
    background: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
  },
  tableItem: {
    padding: '8px 12px',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '4px',
    transition: 'background 0.15s',
  },
  columnItem: {
    padding: '6px 12px 6px 32px',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    borderRadius: 'var(--radius-sm)',
  },
  badge: {
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 500,
    marginLeft: 'auto',
  },
  tabBar: {
    display: 'flex',
    gap: '4px',
    padding: '8px 12px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-tertiary)',
  },
  tab: (active) => ({
    padding: '6px 12px',
    border: 'none',
    background: active ? 'var(--bg-secondary)' : 'transparent',
    color: active ? 'var(--text-primary)' : 'var(--text-muted)',
    fontSize: '13px',
    fontWeight: 500,
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  }),
  sqlEditor: {
    width: '100%',
    height: '120px',
    padding: '12px',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    fontFamily: 'monospace',
    fontSize: '13px',
    resize: 'vertical',
    background: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
  },
  runButton: {
    padding: '10px 20px',
    background: 'var(--grass-green)',
    color: '#fff',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    fontWeight: 600,
    fontSize: 'var(--text-sm)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  dataTable: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  th: {
    padding: '10px 12px',
    textAlign: 'left',
    background: 'var(--bg-tertiary)',
    borderBottom: '2px solid var(--border)',
    fontWeight: 600,
    color: 'var(--text-primary)',
    position: 'sticky',
    top: 0,
  },
  td: {
    padding: '8px 12px',
    borderBottom: '1px solid var(--border)',
    color: 'var(--text-secondary)',
    maxWidth: '200px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '48px 24px',
    color: 'var(--text-muted)',
    textAlign: 'center',
  },
  chip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 10px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border)',
    borderRadius: '16px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
  },
};

// =============================================================================
// DATA CATALOG PANEL
// =============================================================================
function CatalogPanel({ tables, loading, selectedTable, onSelectTable, onSelectColumn }) {
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState({});

  const filteredTables = tables.filter(t => 
    t.name.toLowerCase().includes(search.toLowerCase()) ||
    t.columns?.some(c => c.toLowerCase().includes(search.toLowerCase()))
  );

  const toggleExpand = (tableName) => {
    setExpanded(prev => ({ ...prev, [tableName]: !prev[tableName] }));
  };

  return (
    <div style={styles.panel}>
      <div style={styles.panelHeader}>
        <Database size={16} style={{ color: 'var(--grass-green)' }} />
        <h3 style={styles.panelTitle}>Data Catalog</h3>
        <span style={{ ...styles.badge, background: 'var(--bg-tertiary)', color: 'var(--text-muted)' }}>
          {tables.length}
        </span>
      </div>
      
      <div style={{ padding: '12px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search tables & columns..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={styles.searchInput}
          />
        </div>
      </div>

      <div style={styles.panelBody}>
        {loading ? (
          <div style={styles.emptyState}>
            <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: '8px' }} />
            <span>Loading schema...</span>
          </div>
        ) : filteredTables.length === 0 ? (
          <div style={styles.emptyState}>
            <Database size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
            <span>No tables found</span>
          </div>
        ) : (
          filteredTables.map(table => (
            <div key={table.full_name}>
              <div
                style={{
                  ...styles.tableItem,
                  background: selectedTable === table.full_name ? 'rgba(131, 177, 109, 0.15)' : 'transparent',
                }}
                onClick={() => {
                  onSelectTable(table);
                  toggleExpand(table.full_name);
                }}
              >
                {expanded[table.full_name] ? 
                  <ChevronDown size={14} style={{ color: 'var(--text-muted)' }} /> : 
                  <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />
                }
                <Table size={14} style={{ color: 'var(--grass-green)' }} />
                <span style={{ fontSize: '13px', color: 'var(--text-primary)', flex: 1 }}>{table.name}</span>
                <span style={{ ...styles.badge, background: 'var(--bg-tertiary)', color: 'var(--text-muted)' }}>
                  {table.rows?.toLocaleString()}
                </span>
              </div>
              
              {expanded[table.full_name] && table.columns && (
                <div style={{ marginBottom: '8px' }}>
                  {table.columns.slice(0, 20).map(col => (
                    <div
                      key={col}
                      style={styles.columnItem}
                      onClick={() => onSelectColumn(table, col)}
                    >
                      <Columns size={12} style={{ color: 'var(--text-muted)' }} />
                      <span>{col}</span>
                    </div>
                  ))}
                  {table.columns.length > 20 && (
                    <div style={{ ...styles.columnItem, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      +{table.columns.length - 20} more columns
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// =============================================================================
// QUERY BUILDER PANEL
// =============================================================================
function BuilderPanel({ selectedTable, selectedColumns, sql, onSqlChange, onRun, running, onAddColumn, onRemoveColumn }) {
  const [mode, setMode] = useState('visual'); // 'visual' or 'sql'

  const generateSql = useCallback(() => {
    if (!selectedTable) return '';
    const cols = selectedColumns.length > 0 ? selectedColumns.join(', ') : '*';
    return `SELECT ${cols}\nFROM "${selectedTable.full_name}"\nLIMIT 100`;
  }, [selectedTable, selectedColumns]);

  // Auto-generate SQL when selections change in visual mode
  useEffect(() => {
    if (mode === 'visual' && selectedTable) {
      onSqlChange(generateSql());
    }
  }, [mode, selectedTable, selectedColumns, generateSql, onSqlChange]);

  return (
    <div style={styles.panel}>
      <div style={styles.panelHeader}>
        <Code size={16} style={{ color: '#8b5cf6' }} />
        <h3 style={styles.panelTitle}>Query Builder</h3>
      </div>

      <div style={styles.tabBar}>
        <button style={styles.tab(mode === 'visual')} onClick={() => setMode('visual')}>
          <Filter size={14} />
          Visual
        </button>
        <button style={styles.tab(mode === 'sql')} onClick={() => setMode('sql')}>
          <Code size={14} />
          SQL
        </button>
      </div>

      <div style={styles.panelBody}>
        {mode === 'visual' ? (
          <div>
            {/* Selected Table */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                TABLE
              </label>
              {selectedTable ? (
                <div style={styles.chip}>
                  <Table size={12} />
                  {selectedTable.name}
                </div>
              ) : (
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  Select a table from the catalog
                </div>
              )}
            </div>

            {/* Selected Columns */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                COLUMNS {selectedColumns.length > 0 && `(${selectedColumns.length})`}
              </label>
              {selectedColumns.length > 0 ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {selectedColumns.map(col => (
                    <div key={col} style={{ ...styles.chip, background: 'rgba(139, 92, 246, 0.1)', borderColor: 'rgba(139, 92, 246, 0.3)' }}>
                      {col}
                      <button
                        onClick={() => onRemoveColumn(col)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex' }}
                      >
                        <X size={12} style={{ color: 'var(--text-muted)' }} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  All columns (click columns in catalog to select specific ones)
                </div>
              )}
            </div>

            {/* Generated SQL Preview */}
            {selectedTable && (
              <div style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                  GENERATED SQL
                </label>
                <pre style={{
                  padding: '12px',
                  background: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  color: 'var(--text-secondary)',
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                  border: '1px solid var(--border)',
                }}>
                  {sql}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              SQL QUERY
            </label>
            <textarea
              style={styles.sqlEditor}
              value={sql}
              onChange={(e) => onSqlChange(e.target.value)}
              placeholder="SELECT * FROM table_name LIMIT 100"
              spellCheck={false}
            />
          </div>
        )}
      </div>

      <div style={{ padding: '12px', borderTop: '1px solid var(--border)', display: 'flex', gap: '8px' }}>
        <button
          style={{
            ...styles.runButton,
            opacity: (!sql || running) ? 0.6 : 1,
            cursor: (!sql || running) ? 'not-allowed' : 'pointer',
          }}
          onClick={onRun}
          disabled={!sql || running}
        >
          {running ? (
            <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
          ) : (
            <Play size={16} />
          )}
          {running ? 'Running...' : 'Run Query'}
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// RESULTS PANEL
// =============================================================================
function ResultsPanel({ results, error, executionTime }) {
  const [viewMode, setViewMode] = useState('table'); // 'table' or 'chart'

  const exportCsv = () => {
    if (!results?.data?.length) return;
    
    const headers = results.columns.join(',');
    const rows = results.data.map(row => 
      results.columns.map(col => {
        const val = row[col];
        if (val === null || val === undefined) return '';
        if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
          return `"${val.replace(/"/g, '""')}"`;
        }
        return val;
      }).join(',')
    ).join('\n');
    
    const csv = `${headers}\n${rows}`;
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'query_results.csv';
    a.click();
  };

  return (
    <div style={styles.panel}>
      <div style={styles.panelHeader}>
        <BarChart3 size={16} style={{ color: '#f59e0b' }} />
        <h3 style={styles.panelTitle}>Results</h3>
        {results && (
          <>
            <span style={{ ...styles.badge, background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
              {results.row_count?.toLocaleString()} rows
            </span>
            {executionTime && (
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                {executionTime.toFixed(2)}s
              </span>
            )}
          </>
        )}
      </div>

      {results?.data?.length > 0 && (
        <div style={styles.tabBar}>
          <button style={styles.tab(viewMode === 'table')} onClick={() => setViewMode('table')}>
            <Table size={14} />
            Table
          </button>
          <button style={styles.tab(viewMode === 'chart')} onClick={() => setViewMode('chart')}>
            <BarChart3 size={14} />
            Chart
          </button>
          <button
            onClick={exportCsv}
            style={{ ...styles.tab(false), marginLeft: 'auto' }}
          >
            <Download size={14} />
            Export CSV
          </button>
        </div>
      )}

      <div style={styles.panelBody}>
        {error ? (
          <div style={{ ...styles.emptyState, color: '#ef4444' }}>
            <AlertCircle size={32} style={{ marginBottom: '8px' }} />
            <span style={{ fontWeight: 600, marginBottom: '4px' }}>Query Error</span>
            <span style={{ fontSize: '13px' }}>{error}</span>
          </div>
        ) : !results ? (
          <div style={styles.emptyState}>
            <Play size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
            <span>Run a query to see results</span>
          </div>
        ) : results.data?.length === 0 ? (
          <div style={styles.emptyState}>
            <Table size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
            <span>No rows returned</span>
          </div>
        ) : viewMode === 'table' ? (
          <div style={{ overflow: 'auto', maxHeight: '100%' }}>
            <table style={styles.dataTable}>
              <thead>
                <tr>
                  {results.columns?.map(col => (
                    <th key={col} style={styles.th}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.data?.slice(0, 100).map((row, i) => (
                  <tr key={i}>
                    {results.columns?.map(col => (
                      <td key={col} style={styles.td} title={String(row[col] ?? '')}>
                        {row[col] === null ? <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>null</span> : String(row[col])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {results.data?.length > 100 && (
              <div style={{ padding: '12px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                Showing first 100 of {results.data.length} rows
              </div>
            )}
          </div>
        ) : (
          <div style={styles.emptyState}>
            <BarChart3 size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
            <span>Chart visualization coming soon</span>
            <span style={{ fontSize: '12px', marginTop: '4px' }}>Use Table view for now</span>
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================
export default function AnalyticsPage() {
  const { activeProject } = useProject();
  const projectCode = activeProject?.code || activeProject?.name;

  // State
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTable, setSelectedTable] = useState(null);
  const [selectedColumns, setSelectedColumns] = useState([]);
  const [sql, setSql] = useState('');
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [executionTime, setExecutionTime] = useState(null);

  // Load schema
  useEffect(() => {
    if (!projectCode) {
      setTables([]);
      setLoading(false);
      return;
    }

    const loadSchema = async () => {
      setLoading(true);
      try {
        const res = await api.get(`/bi/schema/${encodeURIComponent(projectCode)}`);
        setTables(res.data?.tables || []);
      } catch (err) {
        console.error('Failed to load schema:', err);
        setTables([]);
      } finally {
        setLoading(false);
      }
    };

    loadSchema();
  }, [projectCode]);

  // Handlers
  const handleSelectTable = (table) => {
    setSelectedTable(table);
    setSelectedColumns([]);
    setError(null);
  };

  const handleSelectColumn = (table, column) => {
    if (selectedTable?.full_name !== table.full_name) {
      setSelectedTable(table);
      setSelectedColumns([column]);
    } else {
      setSelectedColumns(prev => 
        prev.includes(column) 
          ? prev.filter(c => c !== column)
          : [...prev, column]
      );
    }
  };

  const handleRemoveColumn = (column) => {
    setSelectedColumns(prev => prev.filter(c => c !== column));
  };

  const handleRun = async () => {
    if (!sql || !projectCode) return;
    
    setRunning(true);
    setError(null);
    setResults(null);
    
    const startTime = Date.now();
    
    try {
      const res = await api.post('/bi/execute', {
        sql: sql,
        project: projectCode,
      });
      
      setExecutionTime((Date.now() - startTime) / 1000);
      
      if (res.data?.error) {
        setError(res.data.error);
      } else {
        setResults({
          columns: res.data?.columns || [],
          data: res.data?.data || [],
          row_count: res.data?.row_count || res.data?.data?.length || 0,
        });
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Query failed');
    } finally {
      setRunning(false);
    }
  };

  // No project selected
  if (!projectCode) {
    return (
      <div>
        <div style={{ marginBottom: '24px' }}>
          <h1 style={{ 
            margin: 0, 
            fontSize: '20px', 
            fontWeight: 600, 
            color: 'var(--text-primary)', 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px',
            fontFamily: "'Sora', var(--font-body)"
          }}>
            <div style={{ 
              width: '36px', 
              height: '36px', 
              borderRadius: '10px', 
              backgroundColor: '#f59e0b', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}>
              <BarChart3 size={20} color="#ffffff" />
            </div>
            Analytics
          </h1>
          <p style={{ margin: '6px 0 0 46px', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
            Query and visualize your project data
          </p>
        </div>

        <div style={{
          ...styles.panel,
          padding: '48px',
          alignItems: 'center',
          justifyContent: 'center',
          height: 'auto',
        }}>
          <Database size={48} style={{ color: 'var(--text-muted)', marginBottom: '16px', opacity: 0.5 }} />
          <h3 style={{ margin: '0 0 8px', color: 'var(--text-primary)' }}>No Project Selected</h3>
          <p style={{ margin: 0, color: 'var(--text-muted)', textAlign: 'center' }}>
            Select a project from the flow bar above to explore its data.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ 
          margin: 0, 
          fontSize: '20px', 
          fontWeight: 600, 
          color: 'var(--text-primary)', 
          display: 'flex', 
          alignItems: 'center', 
          gap: '10px',
          fontFamily: "'Sora', var(--font-body)"
        }}>
          <div style={{ 
            width: '36px', 
            height: '36px', 
            borderRadius: '10px', 
            backgroundColor: '#f59e0b', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center' 
          }}>
            <BarChart3 size={20} color="#ffffff" />
          </div>
          Analytics
        </h1>
        <p style={{ margin: '6px 0 0 46px', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
          Query and visualize data for <strong>{projectCode}</strong>
        </p>
      </div>

      {/* 3-Panel Layout */}
      <div style={styles.container}>
        <CatalogPanel
          tables={tables}
          loading={loading}
          selectedTable={selectedTable?.full_name}
          onSelectTable={handleSelectTable}
          onSelectColumn={handleSelectColumn}
        />
        
        <BuilderPanel
          selectedTable={selectedTable}
          selectedColumns={selectedColumns}
          sql={sql}
          onSqlChange={setSql}
          onRun={handleRun}
          running={running}
          onRemoveColumn={handleRemoveColumn}
        />
        
        <ResultsPanel
          results={results}
          error={error}
          executionTime={executionTime}
        />
      </div>

      {/* Spinner keyframes */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
