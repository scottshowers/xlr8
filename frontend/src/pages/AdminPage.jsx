/**
 * AdminPage - System Administration
 * 
 * Tabs:
 * - Projects: Create, edit, delete projects
 * - Personas: Manage AI personas
 * - Data Management: Structured data (DuckDB) + Documents (ChromaDB)
 * - Global Data: Shared reference data
 * - UKG Connections: API connections for PRO/WFM/READY
 * - Settings: System configuration
 */

import React, { useState, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';
import PersonaManagement from '../components/PersonaManagement';
import api from '../services/api';

// Tab definitions
const TABS = [
  { id: 'projects', label: 'Projects', icon: '🏢' },
  { id: 'personas', label: 'Personas', icon: '🎭' },
  { id: 'data', label: 'Data Management', icon: '📊' },
  { id: 'global', label: 'Global Data', icon: '🌐' },
  { id: 'connections', label: 'UKG Connections', icon: '🔌' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
];

// ==================== PROJECTS TAB ====================
function ProjectsTab() {
  const { projects, createProject, updateProject, deleteProject, selectProject } = useProject();
  const [showForm, setShowForm] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    customer: '',
    product: '',
    type: 'Implementation',
    notes: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingProject) {
        await updateProject(editingProject.id, formData);
      } else {
        await createProject(formData);
      }
      setShowForm(false);
      setEditingProject(null);
      setFormData({ name: '', customer: '', type: 'Implementation', notes: '' });
    } catch (err) {
      alert('Failed to save project: ' + err.message);
    }
  };

  const handleEdit = (project) => {
    setEditingProject(project);
    setFormData({
      name: project.name || '',
      customer: project.customer || '',
      type: project.type || 'Implementation',
      notes: project.notes || '',
    });
    setShowForm(true);
  };

  const handleDelete = async (project) => {
    if (window.confirm(`Delete project "${project.name}"? This cannot be undone.`)) {
      await deleteProject(project.id);
    }
  };

  const styles = {
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' },
    title: { fontSize: '1.1rem', fontWeight: '700', color: '#2a3441' },
    button: { padding: '0.6rem 1.2rem', background: '#83b16d', border: 'none', borderRadius: '8px', color: 'white', fontWeight: '600', cursor: 'pointer' },
    table: { width: '100%', borderCollapse: 'collapse' },
    th: { textAlign: 'left', padding: '0.75rem 1rem', background: '#f8fafc', fontWeight: '600', fontSize: '0.8rem', color: '#5f6c7b', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '1px solid #e1e8ed' },
    td: { padding: '0.75rem 1rem', borderBottom: '1px solid #e1e8ed' },
    actions: { display: 'flex', gap: '0.5rem' },
    actionBtn: (color) => ({ padding: '0.35rem 0.75rem', background: 'transparent', border: `1px solid ${color}`, borderRadius: '4px', color: color, fontSize: '0.8rem', cursor: 'pointer' }),
    form: { background: '#f8fafc', borderRadius: '12px', padding: '1.5rem', marginBottom: '1.5rem' },
    formGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' },
    formGroup: { marginBottom: '1rem' },
    label: { display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: '600', color: '#2a3441' },
    input: { width: '100%', padding: '0.65rem', border: '1px solid #e1e8ed', borderRadius: '6px', fontSize: '0.9rem' },
    formActions: { display: 'flex', gap: '0.75rem', marginTop: '1rem' },
    cancelBtn: { padding: '0.6rem 1.2rem', background: '#f0f4f7', border: 'none', borderRadius: '8px', color: '#5f6c7b', fontWeight: '600', cursor: 'pointer' },
  };

  return (
    <div>
      <div style={styles.header}>
        <h3 style={styles.title}>Manage Projects</h3>
        <button style={styles.button} onClick={() => setShowForm(true)}>➕ New Project</button>
      </div>

      {showForm && (
        <form style={styles.form} onSubmit={handleSubmit}>
          <div style={styles.formGrid}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Customer AR# *</label>
              <input style={styles.input} value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} placeholder="e.g., MEY1000" required />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>Company Name *</label>
              <input style={styles.input} value={formData.customer} onChange={(e) => setFormData({ ...formData, customer: e.target.value })} placeholder="e.g., Meyer Corporation" required />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>Product *</label>
              <select style={styles.input} value={formData.product || ''} onChange={(e) => setFormData({ ...formData, product: e.target.value })} required>
                <option value="">Select Product...</option>
                <option value="UKG Pro">UKG Pro</option>
                <option value="WFM Dimensions">WFM Dimensions</option>
                <option value="UKG Ready">UKG Ready</option>
              </select>
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>Type</label>
              <select style={styles.input} value={formData.type} onChange={(e) => setFormData({ ...formData, type: e.target.value })}>
                <option value="Implementation">Implementation</option>
                <option value="Support">Support</option>
                <option value="Analysis">Analysis</option>
              </select>
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>Notes</label>
              <input style={styles.input} value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} placeholder="Optional notes..." />
            </div>
          </div>
          <div style={styles.formActions}>
            <button type="submit" style={styles.button}>{editingProject ? 'Update Project' : 'Create Project'}</button>
            <button type="button" style={styles.cancelBtn} onClick={() => { setShowForm(false); setEditingProject(null); setFormData({ name: '', customer: '', product: '', type: 'Implementation', notes: '' }); }}>Cancel</button>
          </div>
        </form>
      )}

      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Customer AR#</th>
            <th style={styles.th}>Company Name</th>
            <th style={styles.th}>Product</th>
            <th style={styles.th}>Type</th>
            <th style={styles.th}>Status</th>
            <th style={styles.th}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {projects.map((project) => (
            <tr key={project.id}>
              <td style={styles.td}><strong>{project.name}</strong></td>
              <td style={styles.td}>{project.customer}</td>
              <td style={styles.td}>{project.product || '-'}</td>
              <td style={styles.td}>{project.type || 'Implementation'}</td>
              <td style={styles.td}>
                <span style={{ padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600', background: project.status === 'active' ? '#f0fdf4' : '#f8fafc', color: project.status === 'active' ? '#166534' : '#5f6c7b' }}>
                  {project.status || 'active'}
                </span>
              </td>
              <td style={styles.td}>
                <div style={styles.actions}>
                  <button style={styles.actionBtn('#83b16d')} onClick={() => selectProject(project)}>Select</button>
                  <button style={styles.actionBtn('#93abd9')} onClick={() => handleEdit(project)}>Edit</button>
                  <button style={styles.actionBtn('#e53e3e')} onClick={() => handleDelete(project)}>Delete</button>
                </div>
              </td>
            </tr>
          ))}
          {projects.length === 0 && (
            <tr>
              <td style={styles.td} colSpan={5}>
                <div style={{ textAlign: 'center', padding: '2rem', color: '#5f6c7b' }}>No projects yet. Create one to get started.</div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ==================== DATA MANAGEMENT TAB ====================
function DataManagementTab() {
  const [structuredData, setStructuredData] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);
  const [expandedFile, setExpandedFile] = useState(null);
  const [message, setMessage] = useState(null);
  const [mappingSummaries, setMappingSummaries] = useState({});
  const [semanticTypes, setSemanticTypes] = useState([]);
  const [expandedMappings, setExpandedMappings] = useState(null);
  const [pendingChanges, setPendingChanges] = useState({});  // { "table:column": newType }

  const fetchData = async () => {
    setLoading(true);
    try {
      const structuredRes = await api.get('/status/structured');
      setStructuredData(structuredRes.data);

      const docsRes = await api.get('/status/documents');
      setDocuments(docsRes.data);
      
      // Fetch semantic types for dropdowns
      try {
        const typesRes = await api.get('/status/semantic-types');
        setSemanticTypes(typesRes.data.types || []);
      } catch (e) { console.warn('Failed to fetch semantic types'); }
      
      // Fetch mapping summaries for each file
      if (structuredRes.data?.files) {
        const summaries = {};
        for (const file of structuredRes.data.files) {
          try {
            const sumRes = await api.get(`/status/mappings/${encodeURIComponent(file.project)}/${encodeURIComponent(file.filename)}/summary`);
            summaries[`${file.project}:${file.filename}`] = sumRes.data;
          } catch (e) {
            summaries[`${file.project}:${file.filename}`] = { status: 'none' };
          }
        }
        setMappingSummaries(summaries);
      }
    } catch (err) {
      console.error('Failed to fetch data:', err);
      // Set empty defaults so UI doesn't break
      setStructuredData({ available: false, files: [] });
      setDocuments({ documents: [], total: 0, total_chunks: 0 });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);
  
  // Poll for mapping job status
  useEffect(() => {
    const interval = setInterval(() => {
      // Check for any in-progress jobs
      const inProgress = Object.values(mappingSummaries).some(s => s.status === 'processing');
      if (inProgress) {
        fetchData();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [mappingSummaries]);

  const getMappingBadge = (file) => {
    const key = `${file.project}:${file.filename}`;
    const summary = mappingSummaries[key];
    if (!summary) return null;
    
    if (summary.status === 'processing') {
      return <span style={{ color: '#3b82f6', fontSize: '0.7rem', marginLeft: '8px' }}>🔄 Analyzing...</span>;
    }
    if (summary.needs_review_count > 0) {
      return <span style={{ color: '#f59e0b', fontSize: '0.7rem', marginLeft: '8px' }}>⚠️ {summary.needs_review_count} need review</span>;
    }
    if (summary.total_mappings > 0) {
      return <span style={{ color: '#22c55e', fontSize: '0.7rem', marginLeft: '8px' }}>✅ {summary.total_mappings} mapped</span>;
    }
    return null;
  };
  
  const getMappingPercentage = (file) => {
    const key = `${file.project}:${file.filename}`;
    const summary = mappingSummaries[key];
    
    // Calculate total columns across all sheets
    const totalColumns = file.sheets?.reduce((sum, sheet) => sum + (sheet.column_count || 0), 0) || 0;
    const mappedColumns = summary?.total_mappings || 0;
    
    if (totalColumns === 0) return null;
    if (summary?.status === 'processing') return { pct: null, status: 'processing' };
    
    const pct = Math.round((mappedColumns / totalColumns) * 100);
    return { pct, mappedColumns, totalColumns };
  };
  
  const updateMapping = async (project, tableName, columnName, newType) => {
    // Queue the change locally instead of immediate API call
    const key = `${project}:${tableName}:${columnName}`;
    setPendingChanges(prev => ({ ...prev, [key]: { project, tableName, columnName, newType } }));
  };
  
  const savePendingChanges = async () => {
    const changes = Object.values(pendingChanges);
    if (changes.length === 0) return;
    
    setDeleting('saving-mappings'); // Reuse deleting state for loading indicator
    let successCount = 0;
    
    for (const change of changes) {
      try {
        await api.put(
          `/status/mappings/${encodeURIComponent(change.project)}/${encodeURIComponent(change.tableName)}/${encodeURIComponent(change.columnName)}`,
          { semantic_type: change.newType }
        );
        successCount++;
      } catch (e) {
        console.error(`Failed to update ${change.columnName}:`, e);
      }
    }
    
    setPendingChanges({});
    setDeleting(null);
    showMessage(`Saved ${successCount} mapping${successCount !== 1 ? 's' : ''}`);
    fetchData();
  };
  
  const discardPendingChanges = () => {
    setPendingChanges({});
  };
  
  const getPendingValue = (project, tableName, columnName, currentValue) => {
    const key = `${project}:${tableName}:${columnName}`;
    return pendingChanges[key]?.newType || currentValue;
  };
  
  const hasPendingChange = (project, tableName, columnName) => {
    const key = `${project}:${tableName}:${columnName}`;
    return !!pendingChanges[key];
  };

  const showMessage = (text, type = 'success') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const deleteStructuredFile = async (project, filename) => {
    if (!confirm(`Delete all data for "${filename}"?`)) return;
    setDeleting(`structured:${project}:${filename}`);
    try {
      await api.delete(`/status/structured/${encodeURIComponent(project)}/${encodeURIComponent(filename)}`);
      showMessage(`Deleted "${filename}"`); 
      fetchData();
    } catch { showMessage('Failed to delete', 'error'); }
    finally { setDeleting(null); }
  };

  const deleteDocument = async (filename) => {
    if (!confirm(`Delete "${filename}" from vector store?`)) return;
    setDeleting(`doc:${filename}`);
    try {
      await api.delete(`/status/documents/${encodeURIComponent(filename)}`);
      showMessage(`Deleted "${filename}"`); 
      fetchData();
    } catch { showMessage('Failed to delete', 'error'); }
    finally { setDeleting(null); }
  };

  const resetStructuredData = async () => {
    if (!confirm('⚠️ DELETE ALL STRUCTURED DATA? This cannot be undone!')) return;
    setDeleting('reset-structured');
    try {
      await api.post('/status/structured/reset');
      showMessage('All structured data deleted'); 
      fetchData();
    } catch { showMessage('Failed to reset', 'error'); }
    finally { setDeleting(null); }
  };

  const resetChromaDB = async () => {
    if (!confirm('⚠️ DELETE ALL DOCUMENTS? This cannot be undone!')) return;
    setDeleting('reset-chromadb');
    try {
      await api.post('/status/chromadb/reset');
      showMessage('All documents deleted'); 
      fetchData();
    } catch { showMessage('Failed to reset', 'error'); }
    finally { setDeleting(null); }
  };

  const styles = {
    title: { fontSize: '1.1rem', fontWeight: '700', color: '#2a3441', marginBottom: '0.5rem' },
    subtitle: { color: '#5f6c7b', marginBottom: '1.5rem' },
    toast: { padding: '1rem', borderRadius: '8px', marginBottom: '1rem', border: '1px solid', fontWeight: '500' },
    card: { background: '#f8fafc', borderRadius: '12px', padding: '1.5rem', marginBottom: '1.5rem' },
    cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #e1e8ed' },
    cardTitle: { fontSize: '1rem', fontWeight: '600', color: '#2a3441' },
    cardStats: { fontSize: '0.85rem', color: '#5f6c7b' },
    table: { width: '100%', borderCollapse: 'collapse', background: 'white', borderRadius: '8px', overflow: 'hidden' },
    th: { textAlign: 'left', padding: '0.75rem 1rem', fontSize: '0.75rem', fontWeight: '600', color: '#5f6c7b', textTransform: 'uppercase', background: '#f1f5f9', borderBottom: '1px solid #e1e8ed' },
    td: { padding: '0.75rem 1rem', borderBottom: '1px solid #e1e8ed', fontSize: '0.9rem' },
    deleteBtn: { padding: '0.35rem 0.6rem', background: 'transparent', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '1rem' },
    dangerBtn: { padding: '0.5rem 1rem', fontSize: '0.85rem', background: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca', borderRadius: '6px', cursor: 'pointer' },
    emptyState: { textAlign: 'center', padding: '2rem', color: '#5f6c7b' },
    projectBadge: { display: 'inline-block', padding: '0.2rem 0.6rem', fontSize: '0.75rem', background: '#dbeafe', color: '#1e40af', borderRadius: '999px' },
    expandedTd: { padding: '1rem', background: '#f9fafb' },
    sheetRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.75rem', background: 'white', borderRadius: '6px', border: '1px solid #e5e7eb', marginBottom: '0.5rem', fontSize: '0.85rem' },
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '3rem', color: '#5f6c7b' }}>Loading data...</div>;
  }

  return (
    <div>
      <h3 style={styles.title}>Data Management</h3>
      <p style={styles.subtitle}>Manage structured data and documents</p>

      {message && (
        <div style={{ ...styles.toast, background: message.type === 'error' ? '#fee2e2' : '#dcfce7', color: message.type === 'error' ? '#b91c1c' : '#166534', borderColor: message.type === 'error' ? '#fca5a5' : '#86efac' }}>
          {message.text}
        </div>
      )}

      {/* Structured Data Section */}
      <div style={styles.card}>
        <div style={styles.cardHeader}>
          <h4 style={styles.cardTitle}>📊 Structured Data (DuckDB)</h4>
          <span style={styles.cardStats}>
            {structuredData?.available ? `${structuredData.total_files || 0} files • ${structuredData.total_tables || 0} tables • ${structuredData.total_rows?.toLocaleString() || 0} rows` : 'Not available'}
          </span>
        </div>

        {!structuredData?.files?.length ? (
          <div style={styles.emptyState}>
            <span style={{ fontSize: '2rem' }}>📁</span>
            <p>No Excel/CSV files uploaded yet</p>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>File</th>
                <th style={styles.th}>Project</th>
                <th style={{ ...styles.th, textAlign: 'center' }}>Sheets</th>
                <th style={{ ...styles.th, textAlign: 'center' }}>Rows</th>
                <th style={{ ...styles.th, textAlign: 'center' }}>Loaded</th>
                <th style={{ ...styles.th, textAlign: 'center' }}>🔒</th>
                <th style={{ ...styles.th, textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {structuredData.files.map((file) => (
                <React.Fragment key={`${file.project}::${file.filename}`}>
                  <tr style={{ cursor: 'pointer' }} onClick={() => setExpandedFile(expandedFile === file.filename ? null : file.filename)}>
                    <td style={styles.td}>
                      <span>{file.filename.endsWith('.csv') ? '📄' : '📊'} </span>
                      <strong>{file.filename}</strong>
                      {getMappingBadge(file)}
                      <span style={{ color: '#999', marginLeft: '8px', fontSize: '0.75rem' }}>{expandedFile === file.filename ? '▼' : '▶'}</span>
                    </td>
                    <td style={styles.td}><span style={styles.projectBadge}>{file.project}</span></td>
                    <td style={{ ...styles.td, textAlign: 'center' }}>{file.sheets?.length || 0}</td>
                    <td style={{ ...styles.td, textAlign: 'center' }}>{file.total_rows?.toLocaleString()}</td>
                    <td style={{ ...styles.td, textAlign: 'center', fontSize: '0.75rem', color: '#666' }}>
                      <div>{file.loaded_at ? new Date(file.loaded_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}</div>
                      {(() => {
                        const mapInfo = getMappingPercentage(file);
                        if (!mapInfo) return null;
                        if (mapInfo.status === 'processing') return <div style={{ color: '#3b82f6', fontSize: '0.65rem' }}>🔄 mapping...</div>;
                        const color = mapInfo.pct >= 80 ? '#22c55e' : mapInfo.pct >= 50 ? '#f59e0b' : '#ef4444';
                        return <div style={{ color, fontSize: '0.65rem', fontWeight: '600' }}>{mapInfo.pct}% mapped</div>;
                      })()}
                    </td>
                    <td style={{ ...styles.td, textAlign: 'center' }}>{file.has_encrypted ? '🔒' : '-'}</td>
                    <td style={{ ...styles.td, textAlign: 'center' }}>
                      <button onClick={(e) => { e.stopPropagation(); deleteStructuredFile(file.project, file.filename); }} disabled={deleting === `structured:${file.project}:${file.filename}`} style={styles.deleteBtn}>
                        {deleting === `structured:${file.project}:${file.filename}` ? '⏳' : '🗑️'}
                      </button>
                    </td>
                  </tr>
                  {expandedFile === file.filename && (
                    <tr>
                      <td colSpan={7} style={styles.expandedTd}>
                        <p style={{ fontSize: '0.7rem', fontWeight: '600', color: '#999', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>SHEETS / TABLES:</p>
                        {file.sheets?.map((sheet) => {
                          const key = `${file.project}:${file.filename}`;
                          const summary = mappingSummaries[key];
                          const sheetMappings = summary?.mappings?.filter(m => m.table_name === sheet.table_name) || [];
                          const needsReview = sheetMappings.filter(m => m.needs_review);
                          const isExpanded = expandedMappings === sheet.table_name;
                          
                          return (
                            <div key={sheet.table_name} style={{ marginBottom: '8px' }}>
                              <div style={styles.sheetRow}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <strong>{sheet.sheet_name}</strong>
                                  <span style={{ color: '#999', fontSize: '0.8rem' }}>({sheet.column_count} columns)</span>
                                  {sheetMappings.length > 0 && (
                                    <button 
                                      onClick={(e) => { e.stopPropagation(); setExpandedMappings(isExpanded ? null : sheet.table_name); }}
                                      style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.75rem', color: needsReview.length > 0 ? '#f59e0b' : '#3b82f6' }}
                                    >
                                      {needsReview.length > 0 ? `⚠️ ${needsReview.length} need review` : `🔗 ${sheetMappings.length} mappings`}
                                      <span style={{ marginLeft: '4px' }}>{isExpanded ? '▼' : '▶'}</span>
                                    </button>
                                  )}
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                  <span>{sheet.row_count?.toLocaleString()} rows</span>
                                  {sheet.encrypted_columns?.length > 0 && (
                                    <span style={{ color: '#22c55e', fontSize: '0.8rem' }}>🔒 {sheet.encrypted_columns.length} encrypted</span>
                                  )}
                                </div>
                              </div>
                              
                              {isExpanded && sheetMappings.length > 0 && (
                                <div style={{ marginLeft: '20px', marginTop: '8px', padding: '8px', background: '#f8fafc', borderRadius: '4px', fontSize: '0.8rem' }}>
                                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '4px 12px', alignItems: 'center' }}>
                                    <span style={{ fontWeight: '600', color: '#666', fontSize: '0.7rem' }}>COLUMN</span>
                                    <span style={{ fontWeight: '600', color: '#666', fontSize: '0.7rem' }}>MAPPED TO</span>
                                    <span style={{ fontWeight: '600', color: '#666', fontSize: '0.7rem' }}>CONF</span>
                                    {sheetMappings.map((mapping) => {
                                      const isPending = hasPendingChange(file.project, sheet.table_name, mapping.original_column);
                                      const displayValue = getPendingValue(file.project, sheet.table_name, mapping.original_column, mapping.semantic_type);
                                      
                                      return (
                                        <React.Fragment key={mapping.original_column}>
                                          <span style={{ color: mapping.needs_review ? '#f59e0b' : '#333' }}>
                                            {mapping.needs_review && '⚠️ '}{mapping.original_column}
                                          </span>
                                          <select
                                            value={displayValue}
                                            onChange={(e) => updateMapping(file.project, sheet.table_name, mapping.original_column, e.target.value)}
                                            style={{ 
                                              padding: '2px 4px', 
                                              fontSize: '0.75rem', 
                                              border: isPending ? '2px solid #3b82f6' : mapping.needs_review ? '1px solid #f59e0b' : '1px solid #ddd',
                                              borderRadius: '3px',
                                              background: isPending ? '#dbeafe' : mapping.is_override ? '#e0f2fe' : '#fff'
                                            }}
                                          >
                                            {semanticTypes.map(t => (
                                              <option key={t.id} value={t.id}>{t.label}</option>
                                            ))}
                                          </select>
                                          <span style={{ color: '#999', fontSize: '0.7rem' }}>
                                            {isPending ? '✏️' : mapping.is_override ? '✓' : `${Math.round(mapping.confidence * 100)}%`}
                                          </span>
                                        </React.Fragment>
                                      );
                                    })}
                                  </div>
                                  
                                  {/* Save/Discard buttons when there are pending changes */}
                                  {Object.keys(pendingChanges).length > 0 && (
                                    <div style={{ marginTop: '12px', paddingTop: '8px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                                      <button
                                        onClick={discardPendingChanges}
                                        style={{ padding: '4px 12px', fontSize: '0.75rem', background: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '4px', cursor: 'pointer' }}
                                      >
                                        Discard ({Object.keys(pendingChanges).length})
                                      </button>
                                      <button
                                        onClick={savePendingChanges}
                                        disabled={deleting === 'saving-mappings'}
                                        style={{ padding: '4px 12px', fontSize: '0.75rem', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: '600' }}
                                      >
                                        {deleting === 'saving-mappings' ? '⏳ Saving...' : `💾 Save Changes (${Object.keys(pendingChanges).length})`}
                                      </button>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}

        {structuredData?.files?.length > 0 && (
          <div style={{ marginTop: '1rem', textAlign: 'right' }}>
            <button onClick={resetStructuredData} disabled={deleting === 'reset-structured'} style={styles.dangerBtn}>
              {deleting === 'reset-structured' ? '⏳ Deleting...' : '⚠️ Reset All Structured Data'}
            </button>
          </div>
        )}
      </div>

      {/* Documents Section */}
      <div style={styles.card}>
        <div style={styles.cardHeader}>
          <h4 style={styles.cardTitle}>📄 Documents (ChromaDB)</h4>
          <span style={styles.cardStats}>{documents?.total || 0} files • {documents?.total_chunks?.toLocaleString() || 0} chunks</span>
        </div>

        {!documents?.documents?.length ? (
          <div style={styles.emptyState}>
            <span style={{ fontSize: '2rem' }}>📄</span>
            <p>No PDF/Word documents uploaded yet</p>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Document</th>
                <th style={styles.th}>Project</th>
                <th style={{ ...styles.th, textAlign: 'center' }}>Chunks</th>
                <th style={{ ...styles.th, textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.documents.map((doc) => (
                <tr key={doc.filename}>
                  <td style={styles.td}>
                    <span>{doc.filename?.endsWith('.pdf') ? '📕' : '📘'} </span>
                    <strong>{doc.filename}</strong>
                  </td>
                  <td style={styles.td}><span style={styles.projectBadge}>{doc.project || 'Unknown'}</span></td>
                  <td style={{ ...styles.td, textAlign: 'center' }}>{doc.chunks}</td>
                  <td style={{ ...styles.td, textAlign: 'center' }}>
                    <button onClick={() => deleteDocument(doc.filename)} disabled={deleting === `doc:${doc.filename}`} style={styles.deleteBtn}>
                      {deleting === `doc:${doc.filename}` ? '⏳' : '🗑️'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {documents?.documents?.length > 0 && (
          <div style={{ marginTop: '1rem', textAlign: 'right' }}>
            <button onClick={resetChromaDB} disabled={deleting === 'reset-chromadb'} style={styles.dangerBtn}>
              {deleting === 'reset-chromadb' ? '⏳ Deleting...' : '⚠️ Reset All Documents'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ==================== GLOBAL DATA TAB ====================
function GlobalDataTab() {
  const [globalData] = useState([
    { id: 1, name: 'UKG Pro Configuration Guide', type: 'Documentation', updated: '2024-01-15' },
    { id: 2, name: 'IRS Publication 15', type: 'Compliance', updated: '2024-01-01' },
    { id: 3, name: 'State Tax Tables 2024', type: 'Reference', updated: '2024-01-10' },
  ]);

  const styles = {
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' },
    title: { fontSize: '1.1rem', fontWeight: '700', color: '#2a3441' },
    description: { color: '#5f6c7b', fontSize: '0.9rem', marginBottom: '1.5rem' },
    button: { padding: '0.6rem 1.2rem', background: '#83b16d', border: 'none', borderRadius: '8px', color: 'white', fontWeight: '600', cursor: 'pointer' },
    card: { background: '#f8fafc', borderRadius: '8px', padding: '1rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  };

  return (
    <div>
      <div style={styles.header}>
        <h3 style={styles.title}>Global Reference Data</h3>
        <button style={styles.button}>➕ Add Data</button>
      </div>
      <p style={styles.description}>Shared knowledge base available across all projects. UKG documentation, IRS rules, compliance guides, and firm best practices.</p>

      {globalData.map((item) => (
        <div key={item.id} style={styles.card}>
          <div>
            <strong>{item.name}</strong>
            <div style={{ fontSize: '0.8rem', color: '#5f6c7b' }}>{item.type} • Updated {item.updated}</div>
          </div>
          <button style={{ ...styles.button, padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}>View</button>
        </div>
      ))}
    </div>
  );
}

// ==================== UKG CONNECTIONS TAB ====================
function ConnectionsTab() {
  const { activeProject } = useProject();
  const products = [
    { id: 'pro', name: 'UKG Pro', icon: '🏢', connected: false },
    { id: 'wfm', name: 'UKG WFM', icon: '⏰', connected: false },
    { id: 'ready', name: 'UKG Ready', icon: '🚀', connected: false },
  ];

  const styles = {
    title: { fontSize: '1.1rem', fontWeight: '700', color: '#2a3441', marginBottom: '0.5rem' },
    description: { color: '#5f6c7b', fontSize: '0.9rem' },
    products: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginTop: '1.5rem' },
    productCard: (connected) => ({ background: connected ? '#f0fdf4' : '#f8fafc', border: `2px solid ${connected ? '#86efac' : '#e1e8ed'}`, borderRadius: '12px', padding: '1.5rem', textAlign: 'center' }),
    productIcon: { fontSize: '2.5rem', marginBottom: '0.75rem' },
    productName: { fontWeight: '700', color: '#2a3441', marginBottom: '0.5rem' },
    productStatus: (connected) => ({ fontSize: '0.8rem', color: connected ? '#166534' : '#5f6c7b', marginBottom: '1rem' }),
    connectBtn: (connected) => ({ padding: '0.5rem 1rem', background: connected ? '#f0f4f7' : '#83b16d', border: connected ? '1px solid #e1e8ed' : 'none', borderRadius: '6px', color: connected ? '#5f6c7b' : 'white', fontWeight: '600', cursor: 'pointer' }),
    warning: { marginTop: '1.5rem', padding: '1rem', background: '#fef3c7', borderRadius: '8px', color: '#92400e', fontSize: '0.9rem' },
  };

  return (
    <div>
      <h3 style={styles.title}>UKG API Connections</h3>
      <p style={styles.description}>Connect to customer UKG instances to pull configuration and employee data directly.{!activeProject && ' Select a project first to configure connections.'}</p>

      <div style={styles.products}>
        {products.map((product) => (
          <div key={product.id} style={styles.productCard(product.connected)}>
            <div style={styles.productIcon}>{product.icon}</div>
            <div style={styles.productName}>{product.name}</div>
            <div style={styles.productStatus(product.connected)}>{product.connected ? '✓ Connected' : 'Not connected'}</div>
            <button style={styles.connectBtn(product.connected)} disabled={!activeProject}>{product.connected ? 'Configure' : 'Connect'}</button>
          </div>
        ))}
      </div>

      {!activeProject && (
        <div style={styles.warning}>⚠️ Select a project from the top bar to configure UKG connections.</div>
      )}
    </div>
  );
}

// ==================== SETTINGS TAB ====================
function SettingsTab() {
  return (
    <div style={{ color: '#5f6c7b', textAlign: 'center', padding: '3rem' }}>
      <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>⚙️</div>
      <h3>System Settings Coming Soon</h3>
      <p>User preferences, notification settings, and system configuration.</p>
    </div>
  );
}

// ==================== MAIN COMPONENT ====================
export default function AdminPage() {
  const [activeTab, setActiveTab] = useState('projects');

  const styles = {
    header: { marginBottom: '1.5rem' },
    title: { fontFamily: "'Sora', sans-serif", fontSize: '1.75rem', fontWeight: '700', color: '#2a3441', margin: 0 },
    subtitle: { color: '#5f6c7b', marginTop: '0.25rem' },
    card: { background: 'white', borderRadius: '16px', boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)', overflow: 'hidden' },
    tabs: { display: 'flex', borderBottom: '1px solid #e1e8ed', background: '#fafbfc', overflowX: 'auto' },
    tab: (active) => ({ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '1rem 1.5rem', border: 'none', background: active ? 'white' : 'transparent', color: active ? '#83b16d' : '#5f6c7b', fontWeight: '600', fontSize: '0.9rem', cursor: 'pointer', borderBottom: active ? '2px solid #83b16d' : '2px solid transparent', marginBottom: '-1px', transition: 'all 0.2s ease', whiteSpace: 'nowrap' }),
    tabContent: { padding: '1.5rem' },
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'projects': return <ProjectsTab />;
      case 'personas': return <PersonaManagement />;
      case 'data': return <DataManagementTab />;
      case 'global': return <GlobalDataTab />;
      case 'connections': return <ConnectionsTab />;
      case 'settings': return <SettingsTab />;
      default: return null;
    }
  };

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.title}>Administration</h1>
        <p style={styles.subtitle}>Manage projects, data, and system configuration.</p>
      </div>

      <div style={styles.card}>
        <div style={styles.tabs}>
          {TABS.map(tab => (
            <button key={tab.id} style={styles.tab(activeTab === tab.id)} onClick={() => setActiveTab(tab.id)}>
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
        <div style={styles.tabContent}>
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
}
