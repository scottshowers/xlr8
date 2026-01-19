/**
 * DataCleanup.jsx - Project Data Cleanup
 * 
 * Simple, focused UI for cleaning up project data.
 * Performs complete cascade delete across all storage systems.
 * 
 * Phase 4A UX Cleanup - January 2026
 */

import React, { useState, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';
import api from '../services/api';
import { 
  Trash2, AlertTriangle, Check, Loader2, Database, 
  FileText, FolderOpen, RefreshCw, ChevronDown
} from 'lucide-react';

export default function DataCleanup() {
  const { projects, activeProject, selectProject, refreshProjects } = useProject();
  const [selectedProject, setSelectedProject] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [projectStats, setProjectStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);

  // Load stats when project selected
  useEffect(() => {
    if (selectedProject) {
      loadProjectStats(selectedProject.id);  // Use customer ID for API
    } else {
      setProjectStats(null);
    }
  }, [selectedProject]);

  const loadProjectStats = async (customerId) => {
    setLoadingStats(true);
    try {
      // Get table count
      const filesRes = await api.get(`/files?project=${encodeURIComponent(customerId)}`);
      const files = filesRes.data?.files || [];
      
      let tableCount = 0;
      let rowCount = 0;
      files.forEach(f => {
        if (f.sheets) {
          tableCount += f.sheets.length;
          f.sheets.forEach(s => { rowCount += s.row_count || 0; });
        }
      });

      // Try to get document count
      let docCount = 0;
      try {
        const docsRes = await api.get(`/platform?include=documents&project=${encodeURIComponent(customerId)}`);
        docCount = docsRes.data?.documents?.length || 0;
      } catch (e) {
        // Documents endpoint may not exist
      }

      setProjectStats({
        files: files.length,
        tables: tableCount,
        rows: rowCount,
        documents: docCount
      });
    } catch (err) {
      console.error('Failed to load project stats:', err);
      setProjectStats({ files: 0, tables: 0, rows: 0, documents: 0 });
    } finally {
      setLoadingStats(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedProject) return;
    
    // Use name for user confirmation (human-readable)
    const customerName = selectedProject.name;
    if (confirmText !== customerName) {
      setError(`Type "${customerName}" to confirm deletion`);
      return;
    }

    setDeleting(true);
    setError(null);
    setResult(null);

    try {
      // Use ID for API call
      const res = await api.delete(`/status/project/${encodeURIComponent(selectedProject.id)}/all`);
      setResult(res.data);
      setConfirmText('');
      setSelectedProject(null);
      
      // Refresh projects list
      if (refreshProjects) refreshProjects();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Delete failed');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
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
            backgroundColor: '#ef4444', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center' 
          }}>
            <Trash2 size={20} color="#ffffff" />
          </div>
          Data Cleanup
        </h1>
        <p style={{ margin: '6px 0 0 46px', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
          Delete all data for a project (DuckDB tables, documents, metadata)
        </p>
      </div>

      {/* Main Content */}
      <div style={{ maxWidth: '600px' }}>
        {/* Success Message */}
        {result && (
          <div style={{
            padding: 'var(--space-4)',
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: 'var(--radius-lg)',
            marginBottom: 'var(--space-6)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
              <Check size={20} style={{ color: '#10b981' }} />
              <span style={{ fontWeight: 600, color: '#10b981' }}>Project data deleted successfully</span>
            </div>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
              Deleted: {result.deleted?.tables || 0} tables, {result.deleted?.documents || 0} documents, 
              {result.deleted?.files || 0} file records, {result.deleted?.jobs || 0} jobs
            </div>
          </div>
        )}

        {/* Project Selector */}
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-6)'
        }}>
          <h3 style={{ 
            margin: '0 0 var(--space-4)', 
            fontSize: 'var(--text-base)', 
            fontWeight: 600,
            color: 'var(--text-primary)'
          }}>
            Select Project to Delete
          </h3>

          {/* Dropdown */}
          <div style={{ position: 'relative', marginBottom: 'var(--space-4)' }}>
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%',
                padding: 'var(--space-3)',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                fontSize: 'var(--text-sm)',
                color: selectedProject ? 'var(--text-primary)' : 'var(--text-muted)',
                fontFamily: 'var(--font-body)'
              }}
            >
              <span>
                {selectedProject 
                  ? `${selectedProject.customer || selectedProject.name} (${selectedProject.code || selectedProject.name})`
                  : 'Select a project...'
                }
              </span>
              <ChevronDown size={16} style={{ color: 'var(--text-muted)' }} />
            </button>

            {showDropdown && (
              <div style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                marginTop: '4px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-lg)',
                zIndex: 100,
                maxHeight: '250px',
                overflowY: 'auto'
              }}>
                {projects.length === 0 ? (
                  <div style={{ padding: 'var(--space-3)', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
                    No projects found
                  </div>
                ) : (
                  projects.map(proj => (
                    <button
                      key={proj.id}
                      onClick={() => { setSelectedProject(proj); setShowDropdown(false); setResult(null); }}
                      style={{
                        display: 'block',
                        width: '100%',
                        padding: 'var(--space-3)',
                        border: 'none',
                        background: selectedProject?.id === proj.id ? 'var(--grass-green-alpha-10)' : 'transparent',
                        cursor: 'pointer',
                        textAlign: 'left',
                        borderBottom: '1px solid var(--border-light)',
                        fontSize: 'var(--text-sm)',
                        color: 'var(--text-primary)',
                        fontFamily: 'var(--font-body)'
                      }}
                    >
                      <div style={{ fontWeight: 500 }}>{proj.customer || proj.name}</div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                        {proj.code || proj.name}
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Project Stats */}
          {selectedProject && (
            <div style={{
              padding: 'var(--space-4)',
              background: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-4)'
            }}>
              {loadingStats ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--text-muted)' }}>
                  <Loader2 size={16} className="spin" />
                  <span style={{ fontSize: 'var(--text-sm)' }}>Loading project data...</span>
                </div>
              ) : projectStats ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-3)' }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 'var(--text-xl)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {projectStats.files}
                    </div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Files</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 'var(--text-xl)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {projectStats.tables}
                    </div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Tables</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 'var(--text-xl)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {projectStats.rows.toLocaleString()}
                    </div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Rows</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 'var(--text-xl)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {projectStats.documents}
                    </div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Docs</div>
                  </div>
                </div>
              ) : null}
            </div>
          )}

          {/* Warning */}
          {selectedProject && (
            <div style={{
              display: 'flex',
              gap: 'var(--space-3)',
              padding: 'var(--space-4)',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-4)'
            }}>
              <AlertTriangle size={20} style={{ color: '#ef4444', flexShrink: 0, marginTop: '2px' }} />
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
                <strong>This will permanently delete:</strong>
                <ul style={{ margin: 'var(--space-2) 0 0', paddingLeft: 'var(--space-4)' }}>
                  <li>All DuckDB tables for this project</li>
                  <li>All uploaded documents and chunks</li>
                  <li>Column profiles, classifications, and metadata</li>
                  <li>Context graph relationships</li>
                  <li>Processing jobs and history</li>
                </ul>
              </div>
            </div>
          )}

          {/* Confirmation Input */}
          {selectedProject && (
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <label style={{ 
                display: 'block', 
                fontSize: 'var(--text-sm)', 
                fontWeight: 500,
                color: 'var(--text-secondary)',
                marginBottom: 'var(--space-2)'
              }}>
                Type <strong style={{ color: '#ef4444' }}>{selectedProject.name}</strong> to confirm
              </label>
              <input
                type="text"
                value={confirmText}
                onChange={(e) => { setConfirmText(e.target.value); setError(null); }}
                placeholder="Type customer name to confirm"
                style={{
                  width: '100%',
                  padding: 'var(--space-3)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 'var(--text-sm)',
                  fontFamily: 'var(--font-body)',
                  background: 'var(--bg-tertiary)',
                  color: 'var(--text-primary)'
                }}
              />
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{
              padding: 'var(--space-3)',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-4)',
              fontSize: 'var(--text-sm)',
              color: '#ef4444'
            }}>
              {error}
            </div>
          )}

          {/* Delete Button */}
          {selectedProject && (
            <button
              onClick={handleDelete}
              disabled={deleting || confirmText !== selectedProject.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-2)',
                width: '100%',
                padding: 'var(--space-3)',
                background: (deleting || confirmText !== selectedProject.name) 
                  ? 'var(--text-muted)' 
                  : '#ef4444',
                color: '#ffffff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--text-sm)',
                fontWeight: 600,
                cursor: (deleting || confirmText !== selectedProject.name) 
                  ? 'not-allowed' 
                  : 'pointer',
                fontFamily: 'var(--font-body)'
              }}
            >
              {deleting ? (
                <>
                  <Loader2 size={16} className="spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 size={16} />
                  Delete All Project Data
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
