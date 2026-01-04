/**
 * DataCleanup.jsx
 * ================
 * 
 * UI for cleanup and data deletion operations
 * 
 * Deploy to: frontend/src/pages/DataCleanup.jsx
 * 
 * Add route in App.jsx:
 *   import DataCleanup from './pages/DataCleanup';
 *   <Route path="/admin/cleanup" element={<DataCleanup />} />
 * 
 * Add to navigation:
 *   { path: '/admin/cleanup', label: 'Data Cleanup', icon: '🗑️' }
 * 
 * Last Updated: December 27, 2025
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Trash2, RefreshCw, AlertTriangle, Check, X, Eye, Database, FileText, Loader2, Zap } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

export default function DataCleanup() {
  // State
  const [tables, setTables] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [orphanPreview, setOrphanPreview] = useState(null);
  const [loading, setLoading] = useState({ tables: false, documents: false, preview: false, action: false });
  const [actionResult, setActionResult] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [selectedTables, setSelectedTables] = useState(new Set());
  const [selectedDocs, setSelectedDocs] = useState(new Set());

  const isDark = document.documentElement.classList.contains('dark') || 
                 window.matchMedia('(prefers-color-scheme: dark)').matches;

  const c = {
    background: isDark ? '#0a0a0a' : '#f8f9fa',
    cardBg: isDark ? '#141414' : '#ffffff',
    border: isDark ? '#262626' : '#e5e7eb',
    text: isDark ? '#f5f5f5' : '#1f2937',
    textMuted: isDark ? '#a3a3a3' : '#6b7280',
    primary: '#6366f1',
    accent: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
  };

  // ==========================================================================
  // DATA LOADING
  // ==========================================================================

  const loadTables = async () => {
    setLoading(l => ({ ...l, tables: true }));
    try {
      // Use classification endpoint - provides all table details
      const res = await fetch(`${API_BASE}/api/classification/tables`);
      const data = await res.json();
      
      // Response is { success, tables: [...], total }
      const allTables = (data.tables || []).map(t => ({
        table_name: t.table_name,
        display_name: t.display_name || t.table_name,
        row_count: t.row_count || 0,
        column_count: t.column_count || t.columns?.length || 0,
        file_name: t.source_filename || t.file_name || t.source_file,
        sheet_name: t.sheet_name,
        project: t.project,
        created_at: t.created_at,
        uploaded_by: t.uploaded_by,
        domain: t.detected_domain || t.domain
      }));
      
      setTables(allTables);
    } catch (e) {
      console.error('Failed to load tables:', e);
      setTables([]);
    }
    setLoading(l => ({ ...l, tables: false }));
  };

  const loadDocuments = async () => {
    setLoading(l => ({ ...l, documents: true }));
    try {
      // Use classification endpoint - provides document chunk counts
      const res = await fetch(`${API_BASE}/api/classification/chunks`);
      const data = await res.json();
      // Response is { documents: [{ filename, chunk_count, ... }] }
      setDocuments(data.documents || data || []);
    } catch (e) {
      console.error('Failed to load documents:', e);
      setDocuments([]);
    }
    setLoading(l => ({ ...l, documents: false }));
  };

  const loadOrphanPreview = async () => {
    setLoading(l => ({ ...l, preview: true }));
    try {
      const res = await fetch(`${API_BASE}/api/deep-clean/preview`);
      const data = await res.json();
      setOrphanPreview(data);
    } catch (e) {
      console.error('Failed to load orphan preview:', e);
      setOrphanPreview({ error: e.message });
    }
    setLoading(l => ({ ...l, preview: false }));
  };

  useEffect(() => {
    loadTables();
    loadDocuments();
    loadOrphanPreview();
  }, []);

  // ==========================================================================
  // ACTIONS
  // ==========================================================================

  const showResult = (success, message) => {
    setActionResult({ success, message });
    setTimeout(() => setActionResult(null), 5000);
  };

  const deleteTable = async (tableName) => {
    setLoading(l => ({ ...l, action: true }));
    try {
      // cleanup.py uses /status/structured/table/{table_name}
      const res = await fetch(`${API_BASE}/api/status/structured/table/${encodeURIComponent(tableName)}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (data.success !== false) {
        showResult(true, `Deleted table: ${tableName}`);
        loadTables();
      } else {
        showResult(false, data.error || 'Delete failed');
      }
    } catch (e) {
      showResult(false, e.message);
    }
    setLoading(l => ({ ...l, action: false }));
    setConfirmDelete(null);
  };

  const deleteDocument = async (filename) => {
    setLoading(l => ({ ...l, action: true }));
    try {
      const res = await fetch(`${API_BASE}/api/status/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (data.success !== false) {
        showResult(true, `Deleted document: ${filename}`);
        loadDocuments();
      } else {
        showResult(false, data.error || 'Delete failed');
      }
    } catch (e) {
      showResult(false, e.message);
    }
    setLoading(l => ({ ...l, action: false }));
    setConfirmDelete(null);
  };

  const deleteSelectedTables = async () => {
    if (selectedTables.size === 0) return;
    setLoading(l => ({ ...l, action: true }));
    
    let successCount = 0;
    let failCount = 0;
    
    for (const tableName of selectedTables) {
      try {
        // cleanup.py uses /status/structured/table/{table_name}
        const res = await fetch(`${API_BASE}/api/status/structured/table/${encodeURIComponent(tableName)}`, {
          method: 'DELETE'
        });
        const data = await res.json();
        if (data.success !== false) successCount++;
        else failCount++;
      } catch (e) {
        failCount++;
      }
    }
    
    showResult(failCount === 0, `Deleted ${successCount} tables${failCount > 0 ? `, ${failCount} failed` : ''}`);
    setSelectedTables(new Set());
    loadTables();
    setLoading(l => ({ ...l, action: false }));
    setConfirmDelete(null);
  };

  const deleteSelectedDocs = async () => {
    if (selectedDocs.size === 0) return;
    setLoading(l => ({ ...l, action: true }));
    
    let successCount = 0;
    let failCount = 0;
    
    for (const filename of selectedDocs) {
      try {
        const res = await fetch(`${API_BASE}/api/status/documents/${encodeURIComponent(filename)}`, {
          method: 'DELETE'
        });
        const data = await res.json();
        if (data.success !== false) successCount++;
        else failCount++;
      } catch (e) {
        failCount++;
      }
    }
    
    showResult(failCount === 0, `Deleted ${successCount} documents${failCount > 0 ? `, ${failCount} failed` : ''}`);
    setSelectedDocs(new Set());
    loadDocuments();
    setLoading(l => ({ ...l, action: false }));
    setConfirmDelete(null);
  };

  const deepClean = async (force = false) => {
    setLoading(l => ({ ...l, action: true }));
    try {
      const url = force 
        ? `${API_BASE}/api/deep-clean?confirm=true&force=true`
        : `${API_BASE}/api/deep-clean?confirm=true`;
      const res = await fetch(url, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showResult(true, `Deep clean complete: ${data.total_cleaned} items cleaned`);
        loadTables();
        loadDocuments();
        loadOrphanPreview();
      } else {
        showResult(false, data.error || 'Deep clean failed');
      }
    } catch (e) {
      showResult(false, e.message);
    }
    setLoading(l => ({ ...l, action: false }));
    setConfirmDelete(null);
  };

  const refreshMetrics = async () => {
    setLoading(l => ({ ...l, action: true }));
    try {
      const res = await fetch(`${API_BASE}/api/status/refresh-metrics`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showResult(true, `Metrics refreshed: removed ${data.orphaned_removed?._schema_metadata || 0} orphans`);
        loadTables();
        loadOrphanPreview();
      } else {
        showResult(false, data.error || 'Refresh failed');
      }
    } catch (e) {
      showResult(false, e.message);
    }
    setLoading(l => ({ ...l, action: false }));
  };

  const clearAllJobs = async () => {
    setLoading(l => ({ ...l, action: true }));
    try {
      const res = await fetch(`${API_BASE}/api/jobs`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success !== false) {
        showResult(true, `Cleared ${data.deleted || 'all'} jobs`);
      } else {
        showResult(false, data.error || 'Clear failed');
      }
    } catch (e) {
      showResult(false, e.message);
    }
    setLoading(l => ({ ...l, action: false }));
    setConfirmDelete(null);
  };

  // ==========================================================================
  // RENDER
  // ==========================================================================

  const ConfirmModal = ({ title, message, onConfirm, onCancel, dangerous = true }) => (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: c.cardBg, borderRadius: 12, padding: '1.5rem', maxWidth: 400, width: '90%',
        border: `1px solid ${dangerous ? c.danger : c.border}`
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
          <AlertTriangle size={24} color={dangerous ? c.danger : c.warning} />
          <h3 style={{ margin: 0, color: c.text, fontSize: '1.1rem' }}>{title}</h3>
        </div>
        <p style={{ color: c.textMuted, fontSize: '0.9rem', marginBottom: '1.5rem' }}>{message}</p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{
              padding: '0.5rem 1rem', background: c.border, border: 'none', borderRadius: 6,
              color: c.text, cursor: 'pointer', fontSize: '0.85rem'
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading.action}
            style={{
              padding: '0.5rem 1rem', background: dangerous ? c.danger : c.primary, border: 'none',
              borderRadius: 6, color: '#fff', cursor: 'pointer', fontSize: '0.85rem',
              opacity: loading.action ? 0.7 : 1
            }}
          >
            {loading.action ? 'Processing...' : 'Confirm Delete'}
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div style={{ padding: '1.5rem', maxWidth: '1400px', margin: '0 auto', background: c.background, minHeight: '100vh' }}>
      {/* Breadcrumb */}
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/admin" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: c.textMuted, textDecoration: 'none', fontSize: '0.85rem' }}>
          <ArrowLeft size={16} /> Back to Admin
        </Link>
      </div>

      {/* Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, color: c.text, margin: 0, fontFamily: "'Sora', sans-serif" }}>
            🗑️ Data Cleanup
          </h1>
          <p style={{ fontSize: '0.85rem', color: c.textMuted, margin: '0.25rem 0 0' }}>
            Delete tables, documents, and clean orphaned data
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => { loadTables(); loadDocuments(); loadOrphanPreview(); }}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.5rem 1rem', background: c.cardBg, border: `1px solid ${c.border}`,
              borderRadius: 8, fontSize: '0.85rem', color: c.text, cursor: 'pointer'
            }}
          >
            <RefreshCw size={16} /> Refresh All
          </button>
        </div>
      </div>

      {/* Action Result Toast */}
      {actionResult && (
        <div style={{
          position: 'fixed', top: 20, right: 20, zIndex: 1000,
          background: actionResult.success ? c.accent : c.danger,
          color: '#fff', padding: '0.75rem 1.25rem', borderRadius: 8,
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
        }}>
          {actionResult.success ? <Check size={18} /> : <X size={18} />}
          {actionResult.message}
        </div>
      )}

      {/* Orphan Preview Card */}
      <div style={{ 
        background: c.cardBg, 
        border: `1px solid ${orphanPreview?.duckdb_orphan_tables > 0 || orphanPreview?.chromadb_orphan_chunks > 0 ? c.warning : c.border}`, 
        borderRadius: 10, 
        padding: '1.25rem', 
        marginBottom: '1.5rem' 
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Eye size={20} color={c.warning} />
            <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: c.text }}>Orphan Data Preview</h2>
          </div>
          <button
            onClick={loadOrphanPreview}
            disabled={loading.preview}
            style={{
              padding: '0.35rem 0.75rem', background: c.border, border: 'none',
              borderRadius: 6, fontSize: '0.75rem', color: c.textMuted, cursor: 'pointer'
            }}
          >
            {loading.preview ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : 'Refresh'}
          </button>
        </div>

        {orphanPreview ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.accent }}>{orphanPreview.registry_file_count || 0}</div>
              <div style={{ fontSize: '0.75rem', color: c.textMuted }}>Registry Files</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: orphanPreview.duckdb_orphan_tables > 0 ? c.warning : c.text }}>
                {orphanPreview.duckdb_orphan_tables || 0}
              </div>
              <div style={{ fontSize: '0.75rem', color: c.textMuted }}>Orphan Tables</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: orphanPreview.chromadb_orphan_chunks > 0 ? c.warning : c.text }}>
                {orphanPreview.chromadb_orphan_chunks || 0}
              </div>
              <div style={{ fontSize: '0.75rem', color: c.textMuted }}>Orphan Chunks</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <button
                onClick={() => setConfirmDelete({ type: 'deepClean' })}
                disabled={(orphanPreview.duckdb_orphan_tables || 0) === 0 && (orphanPreview.chromadb_orphan_chunks || 0) === 0}
                style={{
                  padding: '0.5rem 1rem', background: c.danger, border: 'none',
                  borderRadius: 6, color: '#fff', cursor: 'pointer', fontSize: '0.8rem',
                  opacity: ((orphanPreview.duckdb_orphan_tables || 0) === 0 && (orphanPreview.chromadb_orphan_chunks || 0) === 0) ? 0.5 : 1
                }}
              >
                <Zap size={14} style={{ marginRight: 4 }} />
                Deep Clean
              </button>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: c.textMuted, padding: '1rem' }}>
            {loading.preview ? 'Loading...' : 'Failed to load preview'}
          </div>
        )}

        {orphanPreview?.orphan_files?.length > 0 && (
          <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: `1px solid ${c.border}` }}>
            <div style={{ fontSize: '0.75rem', color: c.textMuted, marginBottom: '0.5rem' }}>Orphan files (first 20):</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
              {orphanPreview.orphan_files.map((f, i) => (
                <span key={i} style={{ 
                  background: `${c.warning}20`, color: c.warning, 
                  padding: '2px 8px', borderRadius: 4, fontSize: '0.7rem' 
                }}>
                  {f}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(3, 1fr)', 
        gap: '1rem', 
        marginBottom: '1.5rem' 
      }}>
        <button
          onClick={refreshMetrics}
          disabled={loading.action}
          style={{
            padding: '1rem', background: c.cardBg, border: `1px solid ${c.border}`,
            borderRadius: 10, cursor: 'pointer', textAlign: 'left'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <RefreshCw size={18} color={c.primary} />
            <span style={{ fontWeight: 600, color: c.text }}>Refresh Metrics</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: c.textMuted }}>
            Clean orphaned metadata entries that reference deleted tables
          </div>
        </button>

        <button
          onClick={() => setConfirmDelete({ type: 'clearJobs' })}
          disabled={loading.action}
          style={{
            padding: '1rem', background: c.cardBg, border: `1px solid ${c.border}`,
            borderRadius: 10, cursor: 'pointer', textAlign: 'left'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <Trash2 size={18} color={c.warning} />
            <span style={{ fontWeight: 600, color: c.text }}>Clear All Jobs</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: c.textMuted }}>
            Delete all processing job history from Supabase
          </div>
        </button>

        <button
          onClick={() => setConfirmDelete({ type: 'forceWipe' })}
          disabled={loading.action}
          style={{
            padding: '1rem', background: `${c.danger}10`, border: `1px solid ${c.danger}40`,
            borderRadius: 10, cursor: 'pointer', textAlign: 'left'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <AlertTriangle size={18} color={c.danger} />
            <span style={{ fontWeight: 600, color: c.danger }}>Force Full Wipe</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: c.textMuted }}>
            Delete ALL backend data (DuckDB + ChromaDB). Use with extreme caution!
          </div>
        </button>
      </div>

      {/* Two Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Tables Section */}
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
          <div style={{ 
            padding: '1rem 1.25rem', 
            background: c.background, 
            borderBottom: `1px solid ${c.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Database size={18} color={c.primary} />
              <span style={{ fontWeight: 600, color: c.text }}>DuckDB Tables ({tables.length})</span>
            </div>
            {selectedTables.size > 0 && (
              <button
                onClick={() => setConfirmDelete({ type: 'selectedTables' })}
                style={{
                  padding: '0.35rem 0.75rem', background: c.danger, border: 'none',
                  borderRadius: 6, color: '#fff', cursor: 'pointer', fontSize: '0.75rem'
                }}
              >
                Delete {selectedTables.size} Selected
              </button>
            )}
          </div>
          <div style={{ maxHeight: 400, overflowY: 'auto' }}>
            {loading.tables ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
                <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
              </div>
            ) : tables.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
                No tables found
              </div>
            ) : (
              tables.map((table, i) => {
                const tableName = table.table_name || table.name || table;
                const displayName = table.display_name || tableName;
                const isSelected = selectedTables.has(tableName);
                const uploadedAt = table.created_at ? new Date(table.created_at).toLocaleDateString() : null;
                const uploadedBy = table.uploaded_by;
                return (
                  <div
                    key={i}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '0.75rem',
                      padding: '0.75rem 1rem', borderBottom: `1px solid ${c.border}`,
                      background: isSelected ? `${c.primary}10` : 'transparent'
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        const newSet = new Set(selectedTables);
                        if (e.target.checked) newSet.add(tableName);
                        else newSet.delete(tableName);
                        setSelectedTables(newSet);
                      }}
                      style={{ cursor: 'pointer' }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 500, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {displayName}
                      </div>
                      {displayName !== tableName && (
                        <div style={{ fontSize: '0.7rem', color: c.textMuted, fontFamily: 'monospace' }}>
                          {tableName}
                        </div>
                      )}
                      <div style={{ fontSize: '0.7rem', color: c.textMuted }}>
                        {table.row_count?.toLocaleString() || '?'} rows • {table.column_count || table.columns?.length || '?'} cols
                        {uploadedAt && ` • ${uploadedAt}`}
                        {uploadedBy && ` • by ${uploadedBy}`}
                      </div>
                    </div>
                    <button
                      onClick={() => setConfirmDelete({ type: 'table', name: tableName })}
                      style={{
                        padding: '0.25rem 0.5rem', background: `${c.danger}15`, border: 'none',
                        borderRadius: 4, cursor: 'pointer', color: c.danger
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Documents Section */}
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
          <div style={{ 
            padding: '1rem 1.25rem', 
            background: c.background, 
            borderBottom: `1px solid ${c.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={18} color={c.accent} />
              <span style={{ fontWeight: 600, color: c.text }}>ChromaDB Documents ({documents.length})</span>
            </div>
            {selectedDocs.size > 0 && (
              <button
                onClick={() => setConfirmDelete({ type: 'selectedDocs' })}
                style={{
                  padding: '0.35rem 0.75rem', background: c.danger, border: 'none',
                  borderRadius: 6, color: '#fff', cursor: 'pointer', fontSize: '0.75rem'
                }}
              >
                Delete {selectedDocs.size} Selected
              </button>
            )}
          </div>
          <div style={{ maxHeight: 400, overflowY: 'auto' }}>
            {loading.documents ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
                <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
              </div>
            ) : documents.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
                No documents found
              </div>
            ) : (
              documents.map((doc, i) => {
                const filename = doc.document_name || doc.filename || doc.source || doc.name || 'unknown';
                const isSelected = selectedDocs.has(filename);
                return (
                  <div
                    key={i}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '0.75rem',
                      padding: '0.75rem 1rem', borderBottom: `1px solid ${c.border}`,
                      background: isSelected ? `${c.accent}10` : 'transparent'
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        const newSet = new Set(selectedDocs);
                        if (e.target.checked) newSet.add(filename);
                        else newSet.delete(filename);
                        setSelectedDocs(newSet);
                      }}
                      style={{ cursor: 'pointer' }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 500, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {filename}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: c.textMuted }}>
                        {doc.chunk_count || doc.chunks || '?'} chunks
                      </div>
                    </div>
                    <button
                      onClick={() => setConfirmDelete({ type: 'document', name: filename })}
                      style={{
                        padding: '0.25rem 0.5rem', background: `${c.danger}15`, border: 'none',
                        borderRadius: 4, cursor: 'pointer', color: c.danger
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Confirmation Modals */}
      {confirmDelete?.type === 'table' && (
        <ConfirmModal
          title="Delete Table"
          message={`Are you sure you want to delete "${confirmDelete.name}"? This will remove the table and its metadata from DuckDB.`}
          onConfirm={() => deleteTable(confirmDelete.name)}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {confirmDelete?.type === 'document' && (
        <ConfirmModal
          title="Delete Document"
          message={`Are you sure you want to delete "${confirmDelete.name}"? This will remove all chunks from ChromaDB.`}
          onConfirm={() => deleteDocument(confirmDelete.name)}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {confirmDelete?.type === 'selectedTables' && (
        <ConfirmModal
          title={`Delete ${selectedTables.size} Tables`}
          message={`Are you sure you want to delete ${selectedTables.size} selected tables? This cannot be undone.`}
          onConfirm={deleteSelectedTables}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {confirmDelete?.type === 'selectedDocs' && (
        <ConfirmModal
          title={`Delete ${selectedDocs.size} Documents`}
          message={`Are you sure you want to delete ${selectedDocs.size} selected documents? This cannot be undone.`}
          onConfirm={deleteSelectedDocs}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {confirmDelete?.type === 'deepClean' && (
        <ConfirmModal
          title="Deep Clean Orphans"
          message="This will delete all orphaned tables and chunks that are not registered in the document registry. Are you sure?"
          onConfirm={() => deepClean(false)}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {confirmDelete?.type === 'clearJobs' && (
        <ConfirmModal
          title="Clear All Jobs"
          message="This will delete all job history from Supabase. Are you sure?"
          onConfirm={clearAllJobs}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {confirmDelete?.type === 'forceWipe' && (
        <ConfirmModal
          title="⚠️ FORCE FULL WIPE"
          message="This will delete ALL data from DuckDB and ChromaDB, regardless of registry status. This is IRREVERSIBLE. Are you absolutely sure?"
          onConfirm={() => deepClean(true)}
          onCancel={() => setConfirmDelete(null)}
          dangerous={true}
        />
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
