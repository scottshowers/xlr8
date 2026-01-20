/**
 * DataExplorer.jsx - Data Explorer
 * =================================
 * 
 * Browse tables, fields, and context graph for the active project.
 * 
 * Tabs:
 * - Tables & Fields: Browse tables and columns, view fill rates
 * - Context Graph: Hub/spoke relationships for intelligent queries
 * 
 * Phase 4A UX Overhaul - January 2026
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Database, FileSpreadsheet, ChevronDown, ChevronRight,
  ArrowLeft, RefreshCw, Loader2, Network, Search, FolderOpen, Trash2
} from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import api from '../services/api';

// Import ContextGraph component
import ContextGraph from '../components/ContextGraph';

// =============================================================================
// TABLES & FIELDS TAB
// =============================================================================

function TablesFieldsTab({ tables, loading, customerId, onRefresh }) {
  const [expandedTables, setExpandedTables] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableDetails, setTableDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [deleting, setDeleting] = useState(null);

  // Group tables by source file
  const tablesByFile = tables.reduce((acc, table) => {
    const file = table.filename || 'Unknown';
    if (!acc[file]) acc[file] = [];
    acc[file].push(table);
    return acc;
  }, {});

  // Filter tables by search
  const filteredFiles = Object.entries(tablesByFile).filter(([filename, fileTables]) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return filename.toLowerCase().includes(term) || 
           fileTables.some(t => t.table_name?.toLowerCase().includes(term) || t.display_name?.toLowerCase().includes(term));
  });

  const toggleFile = (filename) => {
    setExpandedTables(prev => ({ ...prev, [filename]: !prev[filename] }));
  };

  const loadTableDetails = async (tableName) => {
    if (!tableName) return;
    setLoadingDetails(true);
    setSelectedTable(tableName);
    try {
      const res = await api.get(`/status/table-profile/${encodeURIComponent(tableName)}`);
      setTableDetails(res.data);
    } catch (err) {
      console.error('Failed to load table details:', err);
      setTableDetails(null);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleDeleteTable = async (e, tableName, displayName) => {
    e.stopPropagation(); // Don't trigger row selection
    
    if (!window.confirm(`Delete table "${displayName || tableName}"?\n\nThis will:\n• Remove the table from DuckDB\n• Clean up all metadata\n• Recalculate relationships\n\nThis cannot be undone.`)) {
      return;
    }
    
    setDeleting(tableName);
    try {
      await api.delete(`/status/structured/table/${encodeURIComponent(tableName)}`);
      
      // Clear selection if deleted table was selected
      if (selectedTable === tableName) {
        setSelectedTable(null);
        setTableDetails(null);
      }
      
      // Refresh the table list
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error('Failed to delete table:', err);
      alert('Failed to delete table: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(null);
    }
  };

  // Get fill rate color
  const getFillColor = (rate) => {
    if (rate >= 90) return 'var(--success)';
    if (rate >= 70) return 'var(--warning)';
    return 'var(--critical)';
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
        <Loader2 size={32} className="spin" style={{ marginBottom: '1rem' }} />
        <p style={{ fontSize: 'var(--text-sm)' }}>Loading tables...</p>
      </div>
    );
  }

  if (tables.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
        <FolderOpen size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
        <p style={{ fontSize: 'var(--text-sm)', marginBottom: '0.5rem' }}>No tables found</p>
        <p style={{ fontSize: 'var(--text-xs)' }}>Upload data files to see them here</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '350px 1fr', gap: 'var(--space-4)', minHeight: '500px' }}>
      {/* Left: Table List */}
      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
        {/* Search */}
        <div style={{ padding: 'var(--space-3)', borderBottom: '1px solid var(--border)' }}>
          <div style={{ 
            display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
            padding: 'var(--space-2) var(--space-3)',
            background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)'
          }}>
            <Search size={14} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search tables..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                border: 'none', background: 'transparent', outline: 'none',
                fontSize: 'var(--text-sm)', color: 'var(--text-primary)', width: '100%'
              }}
            />
          </div>
        </div>

        {/* Table List */}
        <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
          {filteredFiles.map(([filename, fileTables]) => (
            <div key={filename}>
              {/* File Header */}
              <button
                onClick={() => toggleFile(filename)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
                  width: '100%', padding: 'var(--space-3)',
                  background: 'var(--bg-tertiary)', border: 'none', borderBottom: '1px solid var(--border)',
                  cursor: 'pointer', textAlign: 'left'
                }}
              >
                {expandedTables[filename] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <FileSpreadsheet size={14} style={{ color: 'var(--grass-green)' }} />
                <span style={{ 
                  flex: 1, fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--text-primary)',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                }}>
                  {filename}
                </span>
                <span style={{ 
                  fontSize: 'var(--text-xs)', color: 'var(--text-muted)',
                  background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 'var(--radius-full)'
                }}>
                  {fileTables.length}
                </span>
              </button>

              {/* Tables in File */}
              {expandedTables[filename] && fileTables.map(table => (
                <div
                  key={table.table_name}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
                    padding: 'var(--space-2) var(--space-3) var(--space-2) var(--space-6)',
                    background: selectedTable === table.table_name ? 'var(--grass-green-alpha-10)' : 'transparent',
                    borderBottom: '1px solid var(--border-light)'
                  }}
                >
                  <button
                    onClick={() => loadTableDetails(table.table_name)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
                      flex: 1, minWidth: 0,
                      background: 'none', border: 'none',
                      cursor: 'pointer', textAlign: 'left', padding: 0
                    }}
                  >
                    <Database size={12} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ 
                        fontSize: 'var(--text-sm)', color: 'var(--text-primary)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                      }}>
                        {table.display_name || table.table_name}
                      </div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                        {table.row_count?.toLocaleString() || 0} rows • {table.column_count || table.columns?.length || 0} cols
                      </div>
                    </div>
                  </button>
                  <button
                    onClick={(e) => handleDeleteTable(e, table.table_name, table.display_name)}
                    disabled={deleting === table.table_name}
                    style={{
                      padding: 'var(--space-1)',
                      background: 'transparent',
                      border: 'none',
                      cursor: deleting === table.table_name ? 'wait' : 'pointer',
                      color: 'var(--text-muted)',
                      borderRadius: 'var(--radius-sm)',
                      opacity: deleting === table.table_name ? 0.5 : 1,
                      flexShrink: 0
                    }}
                    title="Delete table"
                  >
                    {deleting === table.table_name ? (
                      <Loader2 size={14} className="spin" />
                    ) : (
                      <Trash2 size={14} />
                    )}
                  </button>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Right: Table Details */}
      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
        {!selectedTable ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
            <Database size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
            <p style={{ fontSize: 'var(--text-sm)' }}>Select a table to view columns</p>
          </div>
        ) : loadingDetails ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
            <Loader2 size={32} className="spin" style={{ marginBottom: '1rem' }} />
            <p style={{ fontSize: 'var(--text-sm)' }}>Loading columns...</p>
          </div>
        ) : (
          <>
            {/* Table Header */}
            <div style={{ 
              padding: 'var(--space-4)', 
              background: 'var(--bg-tertiary)', 
              borderBottom: '1px solid var(--border)' 
            }}>
              <h3 style={{ margin: 0, fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)' }}>
                {selectedTable}
              </h3>
              {tableDetails && (
                <p style={{ margin: 'var(--space-1) 0 0', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                  {tableDetails.row_count?.toLocaleString() || 0} rows • {tableDetails.columns?.length || 0} columns
                </p>
              )}
            </div>

            {/* Columns List */}
            <div style={{ maxHeight: '450px', overflowY: 'auto' }}>
              {tableDetails?.columns?.length > 0 ? (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-tertiary)', position: 'sticky', top: 0 }}>
                      <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'left', fontWeight: 500, color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}>Column</th>
                      <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'left', fontWeight: 500, color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}>Type</th>
                      <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right', fontWeight: 500, color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}>Fill Rate</th>
                      <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right', fontWeight: 500, color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}>Distinct</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tableDetails.columns.map((col, idx) => {
                      const fillRate = col.fill_rate ?? col.fillRate ?? 100;
                      return (
                        <tr key={col.name || idx} style={{ borderBottom: '1px solid var(--border-light)' }}>
                          <td style={{ padding: 'var(--space-2) var(--space-3)', color: 'var(--text-primary)', fontWeight: 500 }}>
                            {col.name}
                          </td>
                          <td style={{ padding: 'var(--space-2) var(--space-3)', color: 'var(--text-muted)' }}>
                            {col.type || col.data_type || 'unknown'}
                          </td>
                          <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>
                            <span style={{ 
                              color: getFillColor(fillRate),
                              fontWeight: 500
                            }}>
                              {fillRate.toFixed(0)}%
                            </span>
                          </td>
                          <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right', color: 'var(--text-muted)' }}>
                            {col.distinct_count?.toLocaleString() || '-'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <p style={{ fontSize: 'var(--text-sm)' }}>No column information available</p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// CONTEXT GRAPH TAB
// =============================================================================

function ContextGraphTab({ customerId, customerName }) {
  // ContextGraph component handles its own data loading
  return (
    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-4)', minHeight: '500px' }}>
      <ContextGraph project={customerId || customerName} />
    </div>
  );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function DataExplorer() {
  const { activeProject, projects, selectProject } = useProject();
  const [activeTab, setActiveTab] = useState('tables');
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showProjectDropdown, setShowProjectDropdown] = useState(false);

  // Use customer ID (UUID) for all API operations
  const customerId = activeProject?.id;
  const customerName = activeProject?.name;

  // Load tables
  useEffect(() => {
    if (customerId) {
      loadTables();
    }
  }, [customerId]);

  const loadTables = async () => {
    if (!customerId) return;
    setLoading(true);
    try {
      // Use new canonical endpoint: /customers/{id}/tables
      const res = await api.get(`/customers/${customerId}/tables`);
      const tableList = res.data?.tables || [];
      
      // Tables already come in the right format from CustomerResolver
      const allTables = tableList.map(t => ({
        table_name: t.table_name,
        display_name: t.display_name || t.table_name,
        row_count: t.row_count || 0,
        column_count: t.columns?.length || 0,
        columns: t.columns || [],
        filename: t.filename,
        source: t.source
      }));
      
      setTables(allTables);
    } catch (err) {
      console.error('Failed to load tables:', err);
      setTables([]);
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'tables', label: 'Tables & Fields', icon: FileSpreadsheet },
    { id: 'context-graph', label: 'Context Graph', icon: Network }
  ];

  // No project selected
  if (!activeProject) {
    return (
      <div style={{ padding: '2rem' }}>
        <div style={{ marginBottom: '1rem' }}>
          <Link to="/data" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', textDecoration: 'none', fontSize: 'var(--text-sm)' }}>
            <ArrowLeft size={16} /> Back to Project Data
          </Link>
        </div>
        <div style={{ 
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', 
          padding: '4rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)'
        }}>
          <FolderOpen size={48} style={{ color: 'var(--text-muted)', opacity: 0.3, marginBottom: '1rem' }} />
          <p style={{ fontSize: 'var(--text-base)', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>No project selected</p>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Select a project from the Project Data page first</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Breadcrumb */}
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/data" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', textDecoration: 'none', fontSize: 'var(--text-sm)' }}>
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
              backgroundColor: 'var(--grass-green)', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}>
              <Database size={20} color="#ffffff" />
            </div>
            Data Explorer
          </h1>
          <p style={{ margin: '6px 0 0 46px', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
            View tables, columns, and relationships
          </p>
        </div>
        
        <button 
          onClick={loadTables}
          style={{
            display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
            padding: 'var(--space-2) var(--space-4)',
            background: 'var(--bg-secondary)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)', fontSize: 'var(--text-sm)',
            color: 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'var(--font-body)'
          }}
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Tabs */}
      <div style={{ 
        display: 'flex', gap: 'var(--space-1)', marginBottom: 'var(--space-6)',
        background: 'var(--bg-tertiary)', padding: 'var(--space-1)',
        borderRadius: 'var(--radius-lg)', width: 'fit-content'
      }}>
        {tabs.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
                padding: 'var(--space-2) var(--space-4)', border: 'none',
                background: isActive ? 'var(--bg-secondary)' : 'transparent',
                borderRadius: 'var(--radius-md)', fontSize: 'var(--text-sm)',
                fontWeight: 500, color: isActive ? 'var(--grass-green)' : 'var(--text-secondary)',
                cursor: 'pointer', transition: 'all 0.15s', fontFamily: 'var(--font-body)',
                boxShadow: isActive ? 'var(--shadow-sm)' : 'none'
              }}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {activeTab === 'tables' && (
        <TablesFieldsTab 
          tables={tables} 
          loading={loading} 
          customerId={customerId}
          onRefresh={loadTables}
        />
      )}
      
      {activeTab === 'context-graph' && (
        <ContextGraphTab 
          customerId={customerId}
          customerName={customerName}
        />
      )}
    </div>
  );
}
