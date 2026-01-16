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

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useProject } from '../context/ProjectContext';
import api from '../services/api';
import { 
  Database, Table, Columns, Search, Play, Code, BarChart3, 
  ChevronRight, ChevronDown, Loader2, AlertCircle, Download,
  Plus, X, Filter, ArrowUpDown, PieChart, TrendingUp, Hash
} from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, PieChart as RechartsPie, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

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
function BuilderPanel({ selectedTable, selectedColumns, filters, groupBy, aggregations, sql, onSqlChange, onRun, running, onRemoveColumn, onFiltersChange, onGroupByChange, onAggregationsChange }) {
  const [mode, setMode] = useState('visual'); // 'visual' or 'sql'

  const generateSql = useCallback(() => {
    if (!selectedTable) return '';
    
    // Build SELECT clause
    let selectParts = [];
    
    if (groupBy.length > 0) {
      // When grouping, include group by columns and aggregations
      selectParts = [...groupBy.map(col => `"${col}"`)];
      aggregations.forEach(agg => {
        if (agg.column && agg.function) {
          const fn = agg.function.toUpperCase();
          if (fn === 'COUNT') {
            selectParts.push(`COUNT(*) as count`);
          } else {
            selectParts.push(`${fn}("${agg.column}") as ${fn.toLowerCase()}_${agg.column}`);
          }
        }
      });
    } else if (selectedColumns.length > 0) {
      selectParts = selectedColumns.map(col => `"${col}"`);
    } else {
      selectParts = ['*'];
    }
    
    let query = `SELECT ${selectParts.join(', ')}\nFROM "${selectedTable.full_name}"`;
    
    // Add WHERE clauses from filters
    const activeFilters = filters.filter(f => f.column && (f.value || ['null', 'notnull'].includes(f.operator)));
    if (activeFilters.length > 0) {
      const whereClauses = activeFilters.map(f => {
        const val = isNaN(f.value) ? `'${f.value.replace(/'/g, "''")}'` : f.value;
        switch (f.operator) {
          case '=': return `"${f.column}" = ${val}`;
          case '!=': return `"${f.column}" != ${val}`;
          case '>': return `"${f.column}" > ${val}`;
          case '<': return `"${f.column}" < ${val}`;
          case '>=': return `"${f.column}" >= ${val}`;
          case '<=': return `"${f.column}" <= ${val}`;
          // Use ILIKE for case-insensitive matching (DuckDB supports this)
          case 'contains': return `"${f.column}" ILIKE '%${f.value.replace(/'/g, "''")}%'`;
          case 'starts': return `"${f.column}" ILIKE '${f.value.replace(/'/g, "''")}%'`;
          case 'ends': return `"${f.column}" ILIKE '%${f.value.replace(/'/g, "''")}'`;
          case 'null': return `"${f.column}" IS NULL`;
          case 'notnull': return `"${f.column}" IS NOT NULL`;
          default: return `"${f.column}" = ${val}`;
        }
      });
      query += `\nWHERE ${whereClauses.join('\n  AND ')}`;
    }
    
    // Add GROUP BY
    if (groupBy.length > 0) {
      query += `\nGROUP BY ${groupBy.map(col => `"${col}"`).join(', ')}`;
    }
    
    query += '\nLIMIT 100';
    return query;
  }, [selectedTable, selectedColumns, filters, groupBy, aggregations]);

  // Auto-generate SQL when selections change in visual mode
  useEffect(() => {
    if (mode === 'visual' && selectedTable) {
      onSqlChange(generateSql());
    }
  }, [mode, selectedTable, selectedColumns, filters, groupBy, aggregations, generateSql, onSqlChange]);

  const addFilter = () => {
    onFiltersChange([...filters, { column: '', operator: '=', value: '' }]);
  };

  const updateFilter = (index, field, value) => {
    const newFilters = [...filters];
    newFilters[index] = { ...newFilters[index], [field]: value };
    onFiltersChange(newFilters);
  };

  const removeFilter = (index) => {
    onFiltersChange(filters.filter((_, i) => i !== index));
  };

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

            {/* Filters */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                FILTERS {filters.length > 0 && `(${filters.length})`}
              </label>
              
              {filters.map((filter, idx) => (
                <div key={idx} style={{ 
                  display: 'flex', 
                  gap: '6px', 
                  marginBottom: '8px',
                  alignItems: 'center',
                }}>
                  {/* Column select */}
                  <select
                    value={filter.column}
                    onChange={(e) => updateFilter(idx, 'column', e.target.value)}
                    style={{
                      flex: 1,
                      padding: '6px 8px',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-primary)',
                      fontSize: '12px',
                      color: 'var(--text-primary)',
                    }}
                  >
                    <option value="">Column...</option>
                    {selectedTable?.columns?.map(col => (
                      <option key={col} value={col}>{col}</option>
                    ))}
                  </select>
                  
                  {/* Operator select */}
                  <select
                    value={filter.operator}
                    onChange={(e) => updateFilter(idx, 'operator', e.target.value)}
                    style={{
                      width: '90px',
                      padding: '6px 8px',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-primary)',
                      fontSize: '12px',
                      color: 'var(--text-primary)',
                    }}
                  >
                    <option value="=">=</option>
                    <option value="!=">≠</option>
                    <option value=">">&gt;</option>
                    <option value="<">&lt;</option>
                    <option value=">=">&ge;</option>
                    <option value="<=">&le;</option>
                    <option value="contains">contains</option>
                    <option value="starts">starts with</option>
                    <option value="ends">ends with</option>
                    <option value="null">is null</option>
                    <option value="notnull">not null</option>
                  </select>
                  
                  {/* Value input */}
                  {!['null', 'notnull'].includes(filter.operator) && (
                    <input
                      type="text"
                      value={filter.value}
                      onChange={(e) => updateFilter(idx, 'value', e.target.value)}
                      placeholder="Value..."
                      style={{
                        flex: 1,
                        padding: '6px 8px',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--bg-primary)',
                        fontSize: '12px',
                        color: 'var(--text-primary)',
                      }}
                    />
                  )}
                  
                  {/* Remove button */}
                  <button
                    onClick={() => removeFilter(idx)}
                    style={{
                      padding: '6px',
                      border: 'none',
                      background: 'none',
                      cursor: 'pointer',
                      color: 'var(--text-muted)',
                      display: 'flex',
                    }}
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
              
              {selectedTable && (
                <button
                  onClick={addFilter}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '6px 10px',
                    border: '1px dashed var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    background: 'transparent',
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                  }}
                >
                  <Plus size={12} />
                  Add Filter
                </button>
              )}
            </div>

            {/* GROUP BY */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                GROUP BY {groupBy.length > 0 && `(${groupBy.length})`}
              </label>
              
              {groupBy.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
                  {groupBy.map(col => (
                    <div key={col} style={{ ...styles.chip, background: 'rgba(245, 158, 11, 0.1)', borderColor: 'rgba(245, 158, 11, 0.3)' }}>
                      {col}
                      <button
                        onClick={() => onGroupByChange(groupBy.filter(c => c !== col))}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex' }}
                      >
                        <X size={12} style={{ color: 'var(--text-muted)' }} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              {selectedTable && (
                <select
                  value=""
                  onChange={(e) => {
                    if (e.target.value && !groupBy.includes(e.target.value)) {
                      onGroupByChange([...groupBy, e.target.value]);
                    }
                  }}
                  style={{
                    padding: '6px 8px',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg-primary)',
                    fontSize: '12px',
                    color: 'var(--text-primary)',
                  }}
                >
                  <option value="">+ Add group by column...</option>
                  {selectedTable.columns?.filter(c => !groupBy.includes(c)).map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              )}
            </div>

            {/* AGGREGATIONS (only show when GROUP BY is active) */}
            {groupBy.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                  AGGREGATIONS {aggregations.length > 0 && `(${aggregations.length})`}
                </label>
                
                {aggregations.map((agg, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: '6px', marginBottom: '8px', alignItems: 'center' }}>
                    <select
                      value={agg.function}
                      onChange={(e) => {
                        const newAggs = [...aggregations];
                        newAggs[idx] = { ...newAggs[idx], function: e.target.value };
                        onAggregationsChange(newAggs);
                      }}
                      style={{
                        width: '100px',
                        padding: '6px 8px',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--bg-primary)',
                        fontSize: '12px',
                        color: 'var(--text-primary)',
                      }}
                    >
                      <option value="count">COUNT</option>
                      <option value="sum">SUM</option>
                      <option value="avg">AVG</option>
                      <option value="min">MIN</option>
                      <option value="max">MAX</option>
                    </select>
                    
                    {agg.function !== 'count' && (
                      <select
                        value={agg.column}
                        onChange={(e) => {
                          const newAggs = [...aggregations];
                          newAggs[idx] = { ...newAggs[idx], column: e.target.value };
                          onAggregationsChange(newAggs);
                        }}
                        style={{
                          flex: 1,
                          padding: '6px 8px',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--radius-sm)',
                          background: 'var(--bg-primary)',
                          fontSize: '12px',
                          color: 'var(--text-primary)',
                        }}
                      >
                        <option value="">Select column...</option>
                        {selectedTable?.columns?.map(col => (
                          <option key={col} value={col}>{col}</option>
                        ))}
                      </select>
                    )}
                    
                    <button
                      onClick={() => onAggregationsChange(aggregations.filter((_, i) => i !== idx))}
                      style={{
                        padding: '6px',
                        border: 'none',
                        background: 'none',
                        cursor: 'pointer',
                        color: 'var(--text-muted)',
                        display: 'flex',
                      }}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
                
                <button
                  onClick={() => onAggregationsChange([...aggregations, { function: 'count', column: '' }])}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '6px 10px',
                    border: '1px dashed var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    background: 'transparent',
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                  }}
                >
                  <Plus size={12} />
                  Add Aggregation
                </button>
              </div>
            )}

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
// CHART COLORS
// =============================================================================
const CHART_COLORS = ['#83b16d', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#10b981', '#6366f1'];

// =============================================================================
// RESULTS PANEL
// =============================================================================
function ResultsPanel({ results, error, executionTime }) {
  const [viewMode, setViewMode] = useState('table'); // 'table' or 'chart'
  const [chartType, setChartType] = useState('bar'); // 'bar', 'line', 'pie'
  const [xAxis, setXAxis] = useState('');
  const [yAxis, setYAxis] = useState('');

  // Detect column types and auto-select axes
  const columnInfo = useMemo(() => {
    if (!results?.data?.length || !results?.columns?.length) return { numeric: [], categorical: [] };
    
    const numeric = [];
    const categorical = [];
    
    results.columns.forEach(col => {
      const sample = results.data.slice(0, 10).map(row => row[col]).filter(v => v != null);
      const isNumeric = sample.length > 0 && sample.every(v => !isNaN(Number(v)));
      if (isNumeric) {
        numeric.push(col);
      } else {
        categorical.push(col);
      }
    });
    
    return { numeric, categorical };
  }, [results]);

  // Auto-set axes when results change
  useEffect(() => {
    if (results?.columns?.length) {
      // Pick first categorical for X, first numeric for Y
      const newX = columnInfo.categorical[0] || results.columns[0];
      const newY = columnInfo.numeric[0] || results.columns[1] || results.columns[0];
      setXAxis(newX);
      setYAxis(newY);
    }
  }, [results, columnInfo]);

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!results?.data?.length || !xAxis || !yAxis) return [];
    
    // For pie charts, aggregate by xAxis
    if (chartType === 'pie') {
      const aggregated = {};
      results.data.forEach(row => {
        const key = String(row[xAxis] ?? 'Unknown');
        const val = Number(row[yAxis]) || 0;
        aggregated[key] = (aggregated[key] || 0) + val;
      });
      return Object.entries(aggregated)
        .map(([name, value]) => ({ name, value }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 10); // Top 10 for pie
    }
    
    // For bar/line, use raw data (limit to 50 points)
    return results.data.slice(0, 50).map(row => ({
      name: String(row[xAxis] ?? ''),
      value: Number(row[yAxis]) || 0,
      ...row, // Include all fields for tooltip
    }));
  }, [results, xAxis, yAxis, chartType]);

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

  const renderChart = () => {
    if (!chartData.length) {
      return (
        <div style={styles.emptyState}>
          <BarChart3 size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
          <span>Select X and Y axes to visualize</span>
        </div>
      );
    }

    const commonProps = {
      data: chartData,
      margin: { top: 20, right: 30, left: 20, bottom: 60 },
    };

    switch (chartType) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={350}>
            <LineChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis 
                dataKey="name" 
                tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <Tooltip 
                contentStyle={{ 
                  background: 'var(--bg-secondary)', 
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#83b16d" 
                strokeWidth={2}
                dot={{ fill: '#83b16d', strokeWidth: 0, r: 4 }}
                activeDot={{ r: 6, fill: '#83b16d' }}
              />
            </LineChart>
          </ResponsiveContainer>
        );
      
      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={350}>
            <RechartsPie>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={120}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                labelLine={{ stroke: 'var(--text-muted)' }}
              >
                {chartData.map((entry, index) => (
                  <Cell key={entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  background: 'var(--bg-secondary)', 
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
            </RechartsPie>
          </ResponsiveContainer>
        );
      
      default: // bar
        return (
          <ResponsiveContainer width="100%" height={350}>
            <BarChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis 
                dataKey="name" 
                tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <Tooltip 
                contentStyle={{ 
                  background: 'var(--bg-secondary)', 
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="value" fill="#83b16d" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        );
    }
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
          <div>
            {/* Chart Controls */}
            <div style={{ 
              display: 'flex', 
              gap: '16px', 
              marginBottom: '16px', 
              padding: '12px',
              background: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-md)',
              alignItems: 'flex-end',
              flexWrap: 'wrap',
            }}>
              {/* Chart Type */}
              <div>
                <label style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  CHART TYPE
                </label>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button
                    onClick={() => setChartType('bar')}
                    style={{
                      ...styles.tab(chartType === 'bar'),
                      padding: '6px 10px',
                    }}
                  >
                    <BarChart3 size={14} />
                  </button>
                  <button
                    onClick={() => setChartType('line')}
                    style={{
                      ...styles.tab(chartType === 'line'),
                      padding: '6px 10px',
                    }}
                  >
                    <TrendingUp size={14} />
                  </button>
                  <button
                    onClick={() => setChartType('pie')}
                    style={{
                      ...styles.tab(chartType === 'pie'),
                      padding: '6px 10px',
                    }}
                  >
                    <PieChart size={14} />
                  </button>
                </div>
              </div>
              
              {/* X Axis */}
              <div style={{ flex: 1, minWidth: '120px' }}>
                <label style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  X AXIS (Category)
                </label>
                <select
                  value={xAxis}
                  onChange={(e) => setXAxis(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '6px 8px',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-primary)',
                    fontSize: '13px',
                    color: 'var(--text-primary)',
                  }}
                >
                  {results.columns?.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>
              
              {/* Y Axis */}
              <div style={{ flex: 1, minWidth: '120px' }}>
                <label style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Y AXIS (Value)
                </label>
                <select
                  value={yAxis}
                  onChange={(e) => setYAxis(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '6px 8px',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-primary)',
                    fontSize: '13px',
                    color: 'var(--text-primary)',
                  }}
                >
                  {results.columns?.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>
            </div>
            
            {/* Chart */}
            {renderChart()}
            
            {chartData.length >= 50 && (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px', marginTop: '8px' }}>
                Showing first 50 data points
              </div>
            )}
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
  const [filters, setFilters] = useState([]);
  const [groupBy, setGroupBy] = useState([]);
  const [aggregations, setAggregations] = useState([]);
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
    setFilters([]);
    setGroupBy([]);
    setAggregations([]);
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
          filters={filters}
          groupBy={groupBy}
          aggregations={aggregations}
          sql={sql}
          onSqlChange={setSql}
          onRun={handleRun}
          running={running}
          onRemoveColumn={handleRemoveColumn}
          onFiltersChange={setFilters}
          onGroupByChange={setGroupBy}
          onAggregationsChange={setAggregations}
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
