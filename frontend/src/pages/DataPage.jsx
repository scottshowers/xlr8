/**
 * DataPage - Data Management Hub
 * 
 * Tabs:
 * - Upload Files: Standard document upload
 * - Vacuum Extract: Link to full Vacuum page
 * - Processing Status: View file processing jobs
 * - Data Management: Structured data (DuckDB) + Documents (ChromaDB)
 * - Global Data: Shared reference data
 * - UKG Connections: API connections for PRO/WFM/READY
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import Upload from '../components/Upload';
import Status from '../components/Status';
import api from '../services/api';

// Tab definitions
const TABS = [
  { id: 'upload', label: 'Upload Files', icon: '📤' },
  { id: 'vacuum', label: 'Vacuum Extract', icon: '🧹' },
  { id: 'status', label: 'Processing Status', icon: '📊' },
  { id: 'management', label: 'Data Management', icon: '🗃️' },
  { id: 'global', label: 'Global Data', icon: '🌐' },
  { id: 'connections', label: 'UKG Connections', icon: '🔌' },
];

export default function DataPage() {
  const { activeProject } = useProject();
  const [activeTab, setActiveTab] = useState('upload');

  const styles = {
    header: {
      marginBottom: '1.5rem',
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.75rem',
      fontWeight: '700',
      color: '#2a3441',
      margin: 0,
    },
    subtitle: {
      color: '#5f6c7b',
      marginTop: '0.25rem',
    },
    card: {
      background: 'white',
      borderRadius: '16px',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      overflow: 'hidden',
    },
    tabs: {
      display: 'flex',
      borderBottom: '1px solid #e1e8ed',
      background: '#fafbfc',
      overflowX: 'auto',
    },
    tab: (active) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '1rem 1.5rem',
      border: 'none',
      background: active ? 'white' : 'transparent',
      color: active ? '#83b16d' : '#5f6c7b',
      fontWeight: '600',
      fontSize: '0.9rem',
      cursor: 'pointer',
      borderBottom: active ? '2px solid #83b16d' : '2px solid transparent',
      marginBottom: '-1px',
      transition: 'all 0.2s ease',
      whiteSpace: 'nowrap',
    }),
    tabContent: {
      padding: '1.5rem',
    },
    noProject: {
      textAlign: 'center',
      padding: '3rem',
      color: '#5f6c7b',
    },
    noProjectIcon: {
      fontSize: '3rem',
      marginBottom: '1rem',
      opacity: 0.5,
    },
  };

  // Render tab content
  const renderTabContent = () => {
    if (!activeProject && !['global', 'management'].includes(activeTab)) {
      return (
        <div style={styles.noProject}>
          <div style={styles.noProjectIcon}>📁</div>
          <h3>Select a Project</h3>
          <p>Choose a project from the top bar to manage data.</p>
        </div>
      );
    }

    switch (activeTab) {
      case 'upload':
        return <UploadTab project={activeProject} />;
      case 'vacuum':
        return <VacuumTab />;
      case 'status':
        return <StatusTab project={activeProject} />;
      case 'management':
        return <DataManagementTab />;
      case 'global':
        return <GlobalDataTab />;
      case 'connections':
        return <ConnectionsTab />;
      default:
        return null;
    }
  };

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.title}>Data Management</h1>
        <p style={styles.subtitle}>
          Upload, extract, and manage project data.
          {activeProject && <span> • <strong>{activeProject.name}</strong></span>}
        </p>
      </div>

      <div style={styles.card}>
        <div style={styles.tabs}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              style={styles.tab(activeTab === tab.id)}
              onClick={() => setActiveTab(tab.id)}
            >
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

// ==================== UPLOAD TAB ====================
function UploadTab({ project }) {
  return (
    <div>
      <Upload selectedProject={project} />
    </div>
  );
}

// ==================== VACUUM TAB ====================
function VacuumTab() {
  const styles = {
    container: {
      textAlign: 'center',
      padding: '2rem',
    },
    icon: {
      fontSize: '4rem',
      marginBottom: '1rem',
    },
    title: {
      fontSize: '1.5rem',
      fontWeight: '700',
      color: '#2a3441',
      marginBottom: '0.5rem',
    },
    description: {
      color: '#5f6c7b',
      marginBottom: '1.5rem',
      maxWidth: '500px',
      margin: '0 auto 1.5rem',
      lineHeight: 1.6,
    },
    button: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.875rem 1.75rem',
      background: '#83b16d',
      border: 'none',
      borderRadius: '10px',
      color: 'white',
      fontSize: '1rem',
      fontWeight: '600',
      textDecoration: 'none',
      cursor: 'pointer',
      boxShadow: '0 2px 8px rgba(131, 177, 109, 0.3)',
      transition: 'transform 0.2s ease',
    },
    featureGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: '1rem',
      maxWidth: '600px',
      margin: '2rem auto 0',
      textAlign: 'left',
    },
    feature: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem',
      padding: '1rem',
      background: '#f8fafc',
      borderRadius: '8px',
    },
    featureIcon: {
      fontSize: '1.25rem',
    },
    featureText: {
      fontSize: '0.9rem',
      color: '#2a3441',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.icon}>🧹</div>
      <h2 style={styles.title}>Vacuum Extract</h2>
      <p style={styles.description}>
        Extract data directly from UKG Pro using credentials. Pulls tax documents, 
        pay statements, and other employee data automatically.
      </p>
      <Link to="/vacuum" style={styles.button}>
        🧹 Open Vacuum Extractor
      </Link>
      <div style={styles.featureGrid}>
        <div style={styles.feature}>
          <span style={styles.featureIcon}>📋</span>
          <span style={styles.featureText}>Tax documents (W-2, 1095-C)</span>
        </div>
        <div style={styles.feature}>
          <span style={styles.featureIcon}>💰</span>
          <span style={styles.featureText}>Pay statements</span>
        </div>
        <div style={styles.feature}>
          <span style={styles.featureIcon}>👤</span>
          <span style={styles.featureText}>Employee profiles</span>
        </div>
        <div style={styles.feature}>
          <span style={styles.featureIcon}>🔐</span>
          <span style={styles.featureText}>Secure credential handling</span>
        </div>
      </div>
    </div>
  );
}

// ==================== STATUS TAB ====================
function StatusTab({ project }) {
  return <Status />;
}

// ==================== DATA MANAGEMENT TAB ====================
function DataManagementTab() {
  const { projects } = useProject();
  const [structuredData, setStructuredData] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);
  const [expandedFile, setExpandedFile] = useState(null);
  const [message, setMessage] = useState(null);
  const [mappingSummaries, setMappingSummaries] = useState({});
  const [semanticTypes, setSemanticTypes] = useState([]);
  const [expandedMappings, setExpandedMappings] = useState(null);
  const [pendingChanges, setPendingChanges] = useState({});
  
  // Bulk selection state
  const [selectedDocs, setSelectedDocs] = useState(new Set());
  const [selectedStructured, setSelectedStructured] = useState(new Set());
  
  // ChromaDB audit/cleanup state
  const [chromaAudit, setChromaAudit] = useState(null);
  const [chromaAuditing, setChromaAuditing] = useState(false);
  const [chromaPurging, setChromaPurging] = useState(false);

  // Helper to get project name from ID or name
  const getProjectDisplay = (projectValue) => {
    if (!projectValue) return 'Unknown';
    if (projectValue === 'GLOBAL' || projectValue === 'global' || projectValue === 'Global/Universal') return 'GLOBAL';
    // Check if it's a UUID (has dashes and is 36 chars)
    if (projectValue.length === 36 && projectValue.includes('-')) {
      const found = projects.find(p => p.id === projectValue);
      return found ? found.name : projectValue.slice(0, 8) + '...';
    }
    return projectValue;
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const structuredRes = await api.get('/status/structured');
      setStructuredData(structuredRes.data);

      const docsRes = await api.get('/status/documents');
      setDocuments(docsRes.data);
      
      try {
        const typesRes = await api.get('/status/semantic-types');
        setSemanticTypes(typesRes.data.types || []);
      } catch (e) { console.warn('Failed to fetch semantic types'); }
      
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
      setStructuredData({ available: false, files: [] });
      setDocuments({ documents: [], total: 0, total_chunks: 0 });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);
  
  useEffect(() => {
    const interval = setInterval(() => {
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
    
    if (!summary) return null;
    if (summary.status === 'processing') return { status: 'processing' };
    
    const needsReview = summary.needs_review_count || 0;
    const totalMappings = summary.total_mappings || 0;
    
    if (totalMappings === 0 && summary.status !== 'complete') return null;
    
    if (needsReview > 0) {
      return { status: 'review', count: needsReview };
    }
    
    return { status: 'ready', count: totalMappings };
  };
  
  const updateMapping = async (project, tableName, columnName, newType) => {
    const key = `${project}:${tableName}:${columnName}`;
    setPendingChanges(prev => ({ ...prev, [key]: { project, tableName, columnName, newType } }));
  };
  
  const savePendingChanges = async () => {
    const changes = Object.values(pendingChanges);
    if (changes.length === 0) return;
    
    setDeleting('saving-mappings');
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

  // Bulk delete documents
  const deleteSelectedDocs = async () => {
    if (selectedDocs.size === 0) return;
    if (!confirm(`Delete ${selectedDocs.size} selected document(s)? This cannot be undone.`)) return;
    
    setDeleting('bulk-docs');
    let successCount = 0;
    
    for (const filename of selectedDocs) {
      try {
        await api.delete(`/status/documents/${encodeURIComponent(filename)}`);
        successCount++;
      } catch (e) {
        console.error(`Failed to delete ${filename}:`, e);
      }
    }
    
    setSelectedDocs(new Set());
    setDeleting(null);
    showMessage(`Deleted ${successCount} document(s)`);
    fetchData();
  };
  
  // Bulk delete structured files
  const deleteSelectedStructured = async () => {
    if (selectedStructured.size === 0) return;
    if (!confirm(`Delete ${selectedStructured.size} selected file(s)? This cannot be undone.`)) return;
    
    setDeleting('bulk-structured');
    let successCount = 0;
    
    for (const key of selectedStructured) {
      const [project, filename] = key.split('::');
      try {
        await api.delete(`/status/structured/${encodeURIComponent(project)}/${encodeURIComponent(filename)}`);
        successCount++;
      } catch (e) {
        console.error(`Failed to delete ${filename}:`, e);
      }
    }
    
    setSelectedStructured(new Set());
    setDeleting(null);
    showMessage(`Deleted ${successCount} file(s)`);
    fetchData();
  };
  
  // Toggle document selection
  const toggleDocSelection = (filename) => {
    setSelectedDocs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(filename)) {
        newSet.delete(filename);
      } else {
        newSet.add(filename);
      }
      return newSet;
    });
  };
  
  // Toggle structured file selection
  const toggleStructuredSelection = (project, filename) => {
    const key = `${project}::${filename}`;
    setSelectedStructured(prev => {
      const newSet = new Set(prev);
      if (newSet.has(key)) {
        newSet.delete(key);
      } else {
        newSet.add(key);
      }
      return newSet;
    });
  };
  
  // Select all documents
  const selectAllDocs = () => {
    if (selectedDocs.size === documents?.documents?.length) {
      setSelectedDocs(new Set());
    } else {
      setSelectedDocs(new Set(documents?.documents?.map(d => d.filename) || []));
    }
  };
  
  // Select all structured files
  const selectAllStructured = () => {
    if (selectedStructured.size === structuredData?.files?.length) {
      setSelectedStructured(new Set());
    } else {
      setSelectedStructured(new Set(structuredData?.files?.map(f => `${f.project}::${f.filename}`) || []));
    }
  };

  // ChromaDB Audit - check for orphaned documents
  const auditChromaDB = async () => {
    setChromaAuditing(true);
    try {
      const res = await api.get('/status/chromadb/audit');
      setChromaAudit(res.data);
      if (res.data.orphaned_files === 0) {
        setMessage({ type: 'success', text: `✓ ChromaDB clean: ${res.data.registered_files} files, no orphans` });
      } else {
        setMessage({ type: 'warning', text: `Found ${res.data.orphaned_files} orphaned files in ChromaDB` });
      }
    } catch (err) {
      console.error('Audit failed:', err);
      setMessage({ type: 'error', text: 'Audit failed: ' + err.message });
    } finally {
      setChromaAuditing(false);
    }
  };

  // Purge orphaned ChromaDB documents
  const purgeChromaOrphans = async () => {
    if (!confirm(`Delete ${chromaAudit?.orphaned_files} orphaned documents from ChromaDB? This cannot be undone.`)) return;
    
    setChromaPurging(true);
    try {
      const res = await api.delete('/status/chromadb/purge-orphans');
      setMessage({ type: 'success', text: res.data.message });
      setChromaAudit(null);
      // Refresh document list
      const docsRes = await api.get('/status/documents');
      setDocuments(docsRes.data);
    } catch (err) {
      console.error('Purge failed:', err);
      setMessage({ type: 'error', text: 'Purge failed: ' + err.message });
    } finally {
      setChromaPurging(false);
    }
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
  
  // Format date helper
  const formatDate = (dateString) => {
    if (!dateString) return '-';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '-';
    }
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
    bulkBtn: { padding: '0.5rem 1rem', fontSize: '0.85rem', background: '#fee2e2', color: '#b91c1c', border: '1px solid #fecaca', borderRadius: '6px', cursor: 'pointer', fontWeight: '600' },
    emptyState: { textAlign: 'center', padding: '2rem', color: '#5f6c7b' },
    projectBadge: { display: 'inline-block', padding: '0.2rem 0.6rem', fontSize: '0.75rem', background: '#dbeafe', color: '#1e40af', borderRadius: '999px' },
    expandedTd: { padding: '1rem', background: '#f9fafb' },
    sheetRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.75rem', background: 'white', borderRadius: '6px', border: '1px solid #e5e7eb', marginBottom: '0.5rem', fontSize: '0.85rem' },
    checkbox: { width: '16px', height: '16px', cursor: 'pointer', accentColor: '#3b82f6' },
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
          <>
            {/* Bulk actions for structured */}
            {selectedStructured.size > 0 && (
              <div style={{ marginBottom: '1rem', padding: '0.75rem', background: '#fee2e2', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ color: '#b91c1c', fontWeight: '600' }}>{selectedStructured.size} file(s) selected</span>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button onClick={() => setSelectedStructured(new Set())} style={{ padding: '0.4rem 0.8rem', background: '#fff', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}>Clear</button>
                  <button onClick={deleteSelectedStructured} disabled={deleting === 'bulk-structured'} style={styles.bulkBtn}>
                    {deleting === 'bulk-structured' ? '⏳ Deleting...' : `🗑️ Delete ${selectedStructured.size} File(s)`}
                  </button>
                </div>
              </div>
            )}
            
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={{ ...styles.th, width: '40px', textAlign: 'center' }}>
                    <input 
                      type="checkbox" 
                      style={styles.checkbox}
                      checked={selectedStructured.size === structuredData.files.length && structuredData.files.length > 0}
                      onChange={selectAllStructured}
                    />
                  </th>
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
                    <tr style={{ cursor: 'pointer' }}>
                      <td style={{ ...styles.td, textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                        <input 
                          type="checkbox" 
                          style={styles.checkbox}
                          checked={selectedStructured.has(`${file.project}::${file.filename}`)}
                          onChange={() => toggleStructuredSelection(file.project, file.filename)}
                        />
                      </td>
                      <td style={styles.td} onClick={() => setExpandedFile(expandedFile === file.filename ? null : file.filename)}>
                        <span>{file.source_type === 'pdf' ? '📕' : file.filename.endsWith('.csv') ? '📄' : '📊'} </span>
                        <strong>{file.filename}</strong>
                        {file.source_type === 'pdf' && <span style={{ marginLeft: '8px', fontSize: '0.7rem', background: '#fef3c7', color: '#92400e', padding: '2px 6px', borderRadius: '4px' }}>PDF</span>}
                        {getMappingBadge(file)}
                        <span style={{ color: '#999', marginLeft: '8px', fontSize: '0.75rem' }}>{expandedFile === file.filename ? '▼' : '▶'}</span>
                      </td>
                      <td style={styles.td}><span style={styles.projectBadge}>{getProjectDisplay(file.project)}</span></td>
                      <td style={{ ...styles.td, textAlign: 'center' }}>{file.sheets?.length || 0}</td>
                      <td style={{ ...styles.td, textAlign: 'center' }}>{file.total_rows?.toLocaleString()}</td>
                      <td style={{ ...styles.td, textAlign: 'center', fontSize: '0.75rem', color: '#666' }}>
                        <div>{file.loaded_at ? new Date(file.loaded_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}</div>
                        {(() => {
                          const mapInfo = getMappingPercentage(file);
                          if (!mapInfo) return null;
                          if (mapInfo.status === 'processing') return <div style={{ color: '#3b82f6', fontSize: '0.65rem' }}>🔄 Analyzing...</div>;
                          if (mapInfo.status === 'review') return <div style={{ color: '#f59e0b', fontSize: '0.65rem', fontWeight: '600' }}>⚠️ {mapInfo.count} to review</div>;
                          if (mapInfo.status === 'ready') return <div style={{ color: '#22c55e', fontSize: '0.65rem', fontWeight: '600' }}>✅ Ready</div>;
                          return null;
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
                        <td colSpan={8} style={styles.expandedTd}>
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
                                            <div style={{ position: 'relative' }}>
                                              <input
                                                type="text"
                                                list={`semantic-types-${mapping.original_column}`}
                                                value={semanticTypes.find(t => t.id === displayValue)?.label || displayValue}
                                                onChange={(e) => {
                                                  const matchedType = semanticTypes.find(t => t.label.toLowerCase() === e.target.value.toLowerCase());
                                                  const newValue = matchedType ? matchedType.id : e.target.value;
                                                  updateMapping(file.project, sheet.table_name, mapping.original_column, newValue);
                                                }}
                                                onBlur={(e) => {
                                                  const matchedType = semanticTypes.find(t => t.label.toLowerCase() === e.target.value.toLowerCase());
                                                  if (matchedType) {
                                                    updateMapping(file.project, sheet.table_name, mapping.original_column, matchedType.id);
                                                  }
                                                }}
                                                placeholder="Select or type..."
                                                style={{ 
                                                  padding: '2px 4px', 
                                                  fontSize: '0.75rem', 
                                                  width: '140px',
                                                  border: isPending ? '2px solid #3b82f6' : mapping.needs_review ? '1px solid #f59e0b' : '1px solid #ddd',
                                                  borderRadius: '3px',
                                                  background: isPending ? '#dbeafe' : mapping.is_override ? '#e0f2fe' : '#fff'
                                                }}
                                              />
                                              <datalist id={`semantic-types-${mapping.original_column}`}>
                                                {semanticTypes.map(t => (
                                                  <option key={t.id} value={t.label} />
                                                ))}
                                              </datalist>
                                            </div>
                                            <span style={{ color: '#999', fontSize: '0.7rem' }}>
                                              {isPending ? '✏️' : mapping.is_override ? '✓' : `${Math.round(mapping.confidence * 100)}%`}
                                            </span>
                                          </React.Fragment>
                                        );
                                      })}
                                    </div>
                                    
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
          </>
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <h4 style={styles.cardTitle}>📄 Documents (ChromaDB)</h4>
            <span style={styles.cardStats}>{documents?.total || 0} files • {documents?.total_chunks?.toLocaleString() || 0} chunks</span>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button 
              onClick={auditChromaDB} 
              disabled={chromaAuditing}
              style={{ 
                padding: '0.4rem 0.8rem', 
                background: '#f3f4f6', 
                border: '1px solid #d1d5db', 
                borderRadius: '6px', 
                fontSize: '0.8rem',
                cursor: chromaAuditing ? 'not-allowed' : 'pointer',
                color: '#374151'
              }}
            >
              {chromaAuditing ? '⏳ Auditing...' : '🔍 Audit'}
            </button>
            {chromaAudit?.orphaned_files > 0 && (
              <button 
                onClick={purgeChromaOrphans} 
                disabled={chromaPurging}
                style={{ 
                  padding: '0.4rem 0.8rem', 
                  background: '#fef3c7', 
                  border: '1px solid #f59e0b', 
                  borderRadius: '6px', 
                  fontSize: '0.8rem',
                  cursor: chromaPurging ? 'not-allowed' : 'pointer',
                  color: '#92400e'
                }}
              >
                {chromaPurging ? '⏳ Purging...' : `🧹 Purge ${chromaAudit.orphaned_files} Orphans`}
              </button>
            )}
          </div>
        </div>
        
        {/* Audit Results Banner */}
        {chromaAudit && (
          <div style={{ 
            marginBottom: '1rem', 
            padding: '0.75rem', 
            background: chromaAudit.registry_error ? '#fef2f2' : (chromaAudit.orphaned_files > 0 ? '#fef3c7' : '#d1fae5'), 
            borderRadius: '8px',
            fontSize: '0.85rem'
          }}>
            {chromaAudit.registry_error ? (
              <>
                <strong style={{ color: '#b91c1c' }}>⚠️ Registry Not Setup:</strong>{' '}
                <span style={{ color: '#7f1d1d' }}>{chromaAudit.registry_error}</span>
                <div style={{ marginTop: '0.5rem' }}>
                  <a 
                    href="/api/status/document-registry/setup-sql" 
                    target="_blank" 
                    style={{ color: '#2563eb', textDecoration: 'underline' }}
                  >
                    Get SQL to create table →
                  </a>
                </div>
              </>
            ) : (
              <>
                <strong>Audit Results:</strong> {chromaAudit.registered_files} registered, {chromaAudit.orphaned_files} orphaned
                {chromaAudit.orphaned_files > 0 && (
                  <span style={{ marginLeft: '0.5rem', color: '#92400e' }}>
                    (Orphans: {chromaAudit.orphans?.slice(0, 3).map(o => o.filename).join(', ')}{chromaAudit.orphans?.length > 3 ? '...' : ''})
                  </span>
                )}
              </>
            )}
          </div>
        )}

        {!documents?.documents?.length ? (
          <div style={styles.emptyState}>
            <span style={{ fontSize: '2rem' }}>📄</span>
            <p>No PDF/Word documents uploaded yet</p>
          </div>
        ) : (
          <>
            {/* Bulk actions for documents */}
            {selectedDocs.size > 0 && (
              <div style={{ marginBottom: '1rem', padding: '0.75rem', background: '#fee2e2', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ color: '#b91c1c', fontWeight: '600' }}>{selectedDocs.size} document(s) selected</span>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button onClick={() => setSelectedDocs(new Set())} style={{ padding: '0.4rem 0.8rem', background: '#fff', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}>Clear</button>
                  <button onClick={deleteSelectedDocs} disabled={deleting === 'bulk-docs'} style={styles.bulkBtn}>
                    {deleting === 'bulk-docs' ? '⏳ Deleting...' : `🗑️ Delete ${selectedDocs.size} Doc(s)`}
                  </button>
                </div>
              </div>
            )}
            
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={{ ...styles.th, width: '40px', textAlign: 'center' }}>
                    <input 
                      type="checkbox" 
                      style={styles.checkbox}
                      checked={selectedDocs.size === documents.documents.length && documents.documents.length > 0}
                      onChange={selectAllDocs}
                    />
                  </th>
                  <th style={styles.th}>Document</th>
                  <th style={styles.th}>Project</th>
                  <th style={{ ...styles.th, textAlign: 'center' }}>Chunks</th>
                  <th style={{ ...styles.th, textAlign: 'center' }}>Uploaded</th>
                  <th style={{ ...styles.th, textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.documents.map((doc) => (
                  <tr key={doc.filename || doc.id}>
                    <td style={{ ...styles.td, textAlign: 'center' }}>
                      <input 
                        type="checkbox" 
                        style={styles.checkbox}
                        checked={selectedDocs.has(doc.filename)}
                        onChange={() => toggleDocSelection(doc.filename)}
                      />
                    </td>
                    <td style={styles.td}>
                      <span>{doc.filename?.endsWith('.pdf') ? '📕' : '📘'} </span>
                      <strong>{doc.filename}</strong>
                    </td>
                    <td style={styles.td}><span style={styles.projectBadge}>{getProjectDisplay(doc.project)}</span></td>
                    <td style={{ ...styles.td, textAlign: 'center' }}>{doc.chunks}</td>
                    <td style={{ ...styles.td, textAlign: 'center', fontSize: '0.8rem', color: '#666' }}>
                      {formatDate(doc.upload_date)}
                    </td>
                    <td style={{ ...styles.td, textAlign: 'center' }}>
                      <button onClick={() => deleteDocument(doc.filename)} disabled={deleting === `doc:${doc.filename}`} style={styles.deleteBtn}>
                        {deleting === `doc:${doc.filename}` ? '⏳' : '🗑️'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
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
  const [globalData, setGlobalData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = React.useRef(null);

  const fetchGlobalData = async () => {
    setLoading(true);
    try {
      const res = await api.get('/status/structured');
      const globalFiles = (res.data?.files || []).filter(f => f.project === 'GLOBAL');
      setGlobalData(globalFiles);
    } catch (err) {
      console.error('Failed to fetch global data:', err);
      setGlobalData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchGlobalData(); }, []);

  const handleFileSelect = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    setUploading(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('project', 'GLOBAL');
        await api.post('/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      }
      fetchGlobalData();
    } catch (err) {
      console.error('Upload failed:', err);
      alert('Upload failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const styles = {
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' },
    title: { fontSize: '1.1rem', fontWeight: '700', color: '#2a3441' },
    description: { color: '#5f6c7b', fontSize: '0.9rem', marginBottom: '1.5rem' },
    button: { padding: '0.6rem 1.2rem', background: '#83b16d', border: 'none', borderRadius: '8px', color: 'white', fontWeight: '600', cursor: 'pointer' },
    card: { background: '#f8fafc', borderRadius: '8px', padding: '1rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  };

  return (
    <div>
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        accept=".doc,.docx,.xls,.xlsx,.csv,.pdf,.txt"
        onChange={handleFileSelect}
      />
      <div style={styles.header}>
        <h3 style={styles.title}>Global Reference Data</h3>
        <button 
          style={styles.button} 
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? '⏳ Uploading...' : '➕ Add Data'}
        </button>
      </div>
      <p style={styles.description}>Shared knowledge base available across all projects. UKG documentation, compliance guides, and firm best practices.</p>

      {loading ? (
        <p style={{ color: '#666' }}>Loading...</p>
      ) : globalData.length === 0 ? (
        <p style={{ color: '#666', fontStyle: 'italic' }}>No global data uploaded yet.</p>
      ) : (
        globalData.map((file) => (
          <div key={file.filename} style={styles.card}>
            <div>
              <strong>{file.filename}</strong>
              <div style={{ fontSize: '0.8rem', color: '#5f6c7b' }}>
                {file.sheets?.length || 0} sheets • {file.total_rows?.toLocaleString() || 0} rows
              </div>
            </div>
          </div>
        ))
      )}
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
