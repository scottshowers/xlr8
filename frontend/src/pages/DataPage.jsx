/**
 * DataPage.jsx - Restructured Data Hub
 * 
 * Tabs: Upload | Vacuum | Files | Data Model
 * 
 * Files tab shows:
 * - Structured Data (queryable tables)
 * - Documents (searchable PDFs/docs)
 * - Reference Data (standards, lookups)
 * - Processing History (collapsed, at bottom)
 * 
 * Features:
 * - Multi-select delete with checkboxes
 * - Metadata: uploaded by, date
 * - Bulk actions
 */

import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { useUpload } from '../context/UploadContext';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import {
  Upload as UploadIcon, Sparkles, Database, RefreshCw,
  CheckCircle, XCircle, Clock, Loader2, Trash2, StopCircle,
  FileText, Table2, ChevronDown, ChevronUp, User, Calendar,
  CheckSquare, Square, BookOpen, AlertCircle
} from 'lucide-react';
import DataModelComponent from '../components/DataModelPage';

const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

const TABS = [
  { id: 'upload', label: 'Upload', icon: UploadIcon },
  { id: 'vacuum', label: 'Vacuum', icon: Sparkles },
  { id: 'files', label: 'Files', icon: Database },
  { id: 'model', label: 'Data Model', icon: Database },
];

export default function DataPage() {
  const { activeProject, projectName } = useProject();
  const [activeTab, setActiveTab] = useState('upload');

  return (
    <div>
      <div data-tour="data-header" style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.75rem', fontWeight: 700, color: COLORS.text, margin: 0 }}>
          Data
        </h1>
        <p data-tour="data-project-context" style={{ color: COLORS.textLight, marginTop: '0.25rem' }}>
          Upload and manage project data
          {projectName && <span> • <strong>{projectName}</strong></span>}
        </p>
      </div>

      <div style={{ background: 'white', borderRadius: '16px', boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)', overflow: 'hidden' }}>
        <div style={{ display: 'flex', borderBottom: '1px solid #e1e8ed', background: '#fafbfc' }}>
          {TABS.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                data-tour={`data-tab-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '1rem 1.5rem',
                  border: 'none', background: isActive ? 'white' : 'transparent',
                  color: isActive ? COLORS.grassGreen : COLORS.textLight, fontWeight: 600,
                  fontSize: '0.9rem', cursor: 'pointer',
                  borderBottom: isActive ? `2px solid ${COLORS.grassGreen}` : '2px solid transparent',
                  marginBottom: '-1px',
                }}
              >
                <Icon size={18} />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div style={{ padding: '1.5rem' }}>
          {activeTab === 'upload' && <UploadTab project={activeProject} projectName={projectName} />}
          {activeTab === 'vacuum' && <VacuumTab />}
          {activeTab === 'files' && <FilesTab />}
          {activeTab === 'model' && <DataModelComponent embedded />}
        </div>
      </div>
    </div>
  );
}

// ==================== UPLOAD TAB ====================
function UploadTab({ project, projectName }) {
  const { addUpload } = useUpload();
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleFiles = (files) => {
    if (!project) { alert('Please select a project first'); return; }
    Array.from(files).forEach(file => addUpload(file, project, projectName));
  };

  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); };
  const handleFileSelect = (e) => { handleFiles(e.target.files); e.target.value = ''; };

  if (!project) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '3rem', color: COLORS.textLight }}>
        <UploadIcon size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
        <h3 style={{ margin: '0 0 0.5rem' }}>Select a Project</h3>
        <p>Choose a project from the top bar to upload data.</p>
      </div>
    );
  }

  return (
    <div>
      <input type="file" ref={fileInputRef} style={{ display: 'none' }} multiple accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md" onChange={handleFileSelect} />
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? COLORS.grassGreen : '#e1e8ed'}`, borderRadius: '12px',
          padding: '3rem', textAlign: 'center', cursor: 'pointer',
          background: dragOver ? '#f0fdf4' : '#fafbfc', transition: 'all 0.2s ease',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <UploadIcon size={48} style={{ color: COLORS.grassGreen, marginBottom: '1rem' }} />
          <h3 style={{ margin: '0 0 0.5rem', color: COLORS.text }}>{dragOver ? 'Drop files here' : 'Click or drag files to upload'}</h3>
          <p style={{ color: COLORS.textLight, margin: 0, fontSize: '0.9rem' }}>PDF, Word, Excel, CSV, or Text files</p>
        </div>
      </div>
      <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: '#f8fafc', borderRadius: '8px', fontSize: '0.85rem', color: COLORS.textLight }}>
        💡 <strong>Tip:</strong> Files upload in the background. You can navigate away and check progress in the top-right indicator.
      </div>
    </div>
  );
}

// ==================== VACUUM TAB ====================
function VacuumTab() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '2rem' }}>
      <Sparkles size={48} style={{ color: COLORS.grassGreen, marginBottom: '1rem' }} />
      <h2 style={{ margin: '0 0 0.5rem', color: COLORS.text }}>Vacuum Extract</h2>
      <p style={{ color: COLORS.textLight, maxWidth: '500px', margin: '0 auto 1.5rem', lineHeight: 1.6, textAlign: 'center' }}>
        Deep extraction for complex documents. Intelligent table detection, multi-sheet processing, and semantic column mapping.
      </p>
      <Link to="/vacuum" style={{
        display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.875rem 1.75rem',
        background: COLORS.grassGreen, border: 'none', borderRadius: '10px', color: 'white',
        fontSize: '1rem', fontWeight: 600, textDecoration: 'none', boxShadow: '0 2px 8px rgba(131, 177, 109, 0.3)',
      }}>
        <Sparkles size={18} />Open Vacuum
      </Link>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', maxWidth: '600px', margin: '2rem auto 0', textAlign: 'left' }}>
        {[
          { icon: '📊', text: 'Smart table detection from PDFs' },
          { icon: '🔍', text: 'Multi-sheet Excel processing' },
          { icon: '🏷️', text: 'Automatic column classification' },
          { icon: '✨', text: 'Data quality profiling' },
        ].map((f, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
            <span style={{ fontSize: '1.25rem' }}>{f.icon}</span>
            <span style={{ fontSize: '0.9rem', color: COLORS.text }}>{f.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==================== FILES TAB (Restructured) ====================
function FilesTab() {
  const { projects, activeProject } = useProject();
  const { user } = useAuth();
  const [structuredData, setStructuredData] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  
  // Multi-select state
  const [selectedStructured, setSelectedStructured] = useState(new Set());
  const [selectedDocs, setSelectedDocs] = useState(new Set());

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Slower refresh
    return () => clearInterval(interval);
  }, [activeProject?.id]);

  const loadData = async () => {
    try {
      const [structRes, docsRes, jobsRes] = await Promise.all([
        api.get('/status/structured').catch(() => ({ data: { files: [], total_rows: 0 } })),
        api.get('/status/documents').catch(() => ({ data: { documents: [] } })),
        api.get('/jobs').catch(() => ({ data: { jobs: [] } })),
      ]);
      setStructuredData(structRes.data);
      setDocuments(docsRes.data);
      setJobs(jobsRes.data.jobs || []);
    } catch (err) { 
      console.error('Failed to load:', err); 
    } finally { 
      setLoading(false); 
    }
  };

  // Filter by active project if selected
  const structuredFiles = (structuredData?.files || []).filter(f => 
    !activeProject || f.project === activeProject.id || f.project === activeProject.name
  );
  const docs = (documents?.documents || []).filter(d => 
    !activeProject || d.project === activeProject.id || d.project === activeProject.name
  );
  const recentJobs = jobs.filter(j => 
    !activeProject || j.project_id === activeProject.id
  ).slice(0, 20);

  const getProjectName = (pv) => {
    if (!pv) return 'Unknown';
    if (pv === 'GLOBAL') return 'GLOBAL';
    if (pv.length === 36 && pv.includes('-')) {
      const found = projects.find(p => p.id === pv);
      return found ? found.name : pv.slice(0, 8) + '...';
    }
    return pv;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch { return '—'; }
  };

  // Toggle selection
  const toggleStructured = (key) => {
    const newSet = new Set(selectedStructured);
    if (newSet.has(key)) newSet.delete(key);
    else newSet.add(key);
    setSelectedStructured(newSet);
  };

  const toggleDoc = (key) => {
    const newSet = new Set(selectedDocs);
    if (newSet.has(key)) newSet.delete(key);
    else newSet.add(key);
    setSelectedDocs(newSet);
  };

  const selectAllStructured = () => {
    if (selectedStructured.size === structuredFiles.length) {
      setSelectedStructured(new Set());
    } else {
      setSelectedStructured(new Set(structuredFiles.map(f => `${f.project}:${f.filename}`)));
    }
  };

  const selectAllDocs = () => {
    if (selectedDocs.size === docs.length) {
      setSelectedDocs(new Set());
    } else {
      setSelectedDocs(new Set(docs.map(d => d.filename)));
    }
  };

  // Bulk delete
  const deleteSelectedStructured = async () => {
    if (selectedStructured.size === 0) return;
    if (!confirm(`Delete ${selectedStructured.size} structured file(s)?`)) return;
    
    setDeleting(true);
    try {
      for (const key of selectedStructured) {
        const [project, filename] = key.split(':');
        await api.delete(`/status/structured/${encodeURIComponent(project)}/${encodeURIComponent(filename)}`);
      }
      setSelectedStructured(new Set());
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(false);
    }
  };

  const deleteSelectedDocs = async () => {
    if (selectedDocs.size === 0) return;
    if (!confirm(`Delete ${selectedDocs.size} document(s)?`)) return;
    
    setDeleting(true);
    try {
      for (const filename of selectedDocs) {
        await api.delete(`/status/documents/${encodeURIComponent(filename)}`);
      }
      setSelectedDocs(new Set());
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(false);
    }
  };

  const clearAllJobs = async () => {
    if (!confirm('Clear all processing history?')) return;
    setDeleting(true);
    try {
      await api.delete('/jobs/all');
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(false);
    }
  };

  const getStatusIcon = (status) => {
    if (status === 'completed') return <CheckCircle size={14} style={{ color: '#10b981' }} />;
    if (status === 'failed') return <XCircle size={14} style={{ color: '#ef4444' }} />;
    if (status === 'processing') return <Loader2 size={14} style={{ color: '#3b82f6', animation: 'spin 1s linear infinite' }} />;
    return <Clock size={14} style={{ color: '#f59e0b' }} />;
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: COLORS.textLight }}>
        <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
        <p>Loading...</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  const sectionStyle = { 
    background: 'white', 
    border: '1px solid #e1e8ed', 
    borderRadius: '12px', 
    overflow: 'hidden',
    marginBottom: '1.5rem',
  };
  
  const headerStyle = { 
    padding: '0.875rem 1rem', 
    borderBottom: '1px solid #e1e8ed', 
    display: 'flex', 
    alignItems: 'center', 
    gap: '0.75rem',
    background: '#fafbfc',
  };

  const rowStyle = {
    display: 'grid',
    gridTemplateColumns: '32px 1fr 120px 140px 40px',
    alignItems: 'center',
    padding: '0.75rem 1rem',
    borderBottom: '1px solid #f0f0f0',
    gap: '0.5rem',
  };

  const colHeaderStyle = {
    display: 'grid',
    gridTemplateColumns: '32px 1fr 120px 140px 40px',
    alignItems: 'center',
    padding: '0.5rem 1rem',
    background: '#f8fafc',
    borderBottom: '1px solid #e1e8ed',
    gap: '0.5rem',
    fontSize: '0.7rem',
    fontWeight: 600,
    color: COLORS.textLight,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  };

  return (
    <div>
      {/* Summary Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          { label: 'Structured Files', value: structuredFiles.length, color: '#f59e0b', icon: Table2 },
          { label: 'Documents', value: docs.length, color: '#10b981', icon: FileText },
          { label: 'Total Rows', value: (structuredData?.total_rows || 0).toLocaleString(), color: COLORS.grassGreen, icon: Database },
        ].map((s, i) => {
          const Icon = s.icon;
          return (
            <div key={i} style={{ background: '#f8fafc', borderRadius: '10px', padding: '1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: `${s.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon size={20} style={{ color: s.color }} />
              </div>
              <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: s.color, fontFamily: 'monospace' }}>{s.value}</div>
                <div style={{ fontSize: '0.75rem', color: COLORS.textLight }}>{s.label}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* STRUCTURED DATA SECTION */}
      <div style={sectionStyle}>
        <div style={headerStyle}>
          <Table2 size={20} style={{ color: '#f59e0b' }} />
          <span style={{ fontWeight: 600, color: COLORS.text, flex: 1 }}>Structured Data</span>
          <span style={{ background: '#fef3c7', color: '#92400e', padding: '0.2rem 0.6rem', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 600 }}>
            {structuredFiles.length}
          </span>
          {selectedStructured.size > 0 && (
            <button
              onClick={deleteSelectedStructured}
              disabled={deleting}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.35rem',
                padding: '0.4rem 0.75rem', background: '#fef2f2', border: '1px solid #fecaca',
                borderRadius: '6px', color: '#dc2626', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
              }}
            >
              <Trash2 size={14} />
              Delete ({selectedStructured.size})
            </button>
          )}
          <button onClick={loadData} style={{ background: 'none', border: 'none', cursor: 'pointer', color: COLORS.textLight, padding: '0.25rem' }}>
            <RefreshCw size={16} />
          </button>
        </div>

        {structuredFiles.length > 0 && (
          <div style={colHeaderStyle}>
            <button onClick={selectAllStructured} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
              {selectedStructured.size === structuredFiles.length ? <CheckSquare size={16} style={{ color: COLORS.grassGreen }} /> : <Square size={16} style={{ color: COLORS.textLight }} />}
            </button>
            <span>File Name</span>
            <span>Uploaded By</span>
            <span>Date</span>
            <span></span>
          </div>
        )}

        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {structuredFiles.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: COLORS.textLight }}>
              <Table2 size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
              <p style={{ margin: 0 }}>No structured data files</p>
            </div>
          ) : (
            structuredFiles.map((file, i) => {
              const key = `${file.project}:${file.filename}`;
              const isSelected = selectedStructured.has(key);
              return (
                <div key={i} style={{ ...rowStyle, background: isSelected ? '#f0fdf4' : 'white' }}>
                  <button onClick={() => toggleStructured(key)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                    {isSelected ? <CheckSquare size={16} style={{ color: COLORS.grassGreen }} /> : <Square size={16} style={{ color: COLORS.textLight }} />}
                  </button>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: COLORS.text }}>
                      {file.filename}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: COLORS.textLight }}>
                      {(file.total_rows || 0).toLocaleString()} rows • {getProjectName(file.project)}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: COLORS.textLight, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <User size={12} />
                    {file.uploaded_by || 'System'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: COLORS.textLight, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <Calendar size={12} />
                    {formatDate(file.uploaded_at || file.created_at)}
                  </div>
                  <div></div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* DOCUMENTS SECTION */}
      <div style={sectionStyle}>
        <div style={headerStyle}>
          <FileText size={20} style={{ color: '#10b981' }} />
          <span style={{ fontWeight: 600, color: COLORS.text, flex: 1 }}>Documents</span>
          <span style={{ background: '#d1fae5', color: '#065f46', padding: '0.2rem 0.6rem', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 600 }}>
            {docs.length}
          </span>
          {selectedDocs.size > 0 && (
            <button
              onClick={deleteSelectedDocs}
              disabled={deleting}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.35rem',
                padding: '0.4rem 0.75rem', background: '#fef2f2', border: '1px solid #fecaca',
                borderRadius: '6px', color: '#dc2626', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
              }}
            >
              <Trash2 size={14} />
              Delete ({selectedDocs.size})
            </button>
          )}
        </div>

        {docs.length > 0 && (
          <div style={colHeaderStyle}>
            <button onClick={selectAllDocs} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
              {selectedDocs.size === docs.length ? <CheckSquare size={16} style={{ color: COLORS.grassGreen }} /> : <Square size={16} style={{ color: COLORS.textLight }} />}
            </button>
            <span>Document Name</span>
            <span>Uploaded By</span>
            <span>Date</span>
            <span></span>
          </div>
        )}

        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {docs.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: COLORS.textLight }}>
              <FileText size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
              <p style={{ margin: 0 }}>No documents</p>
            </div>
          ) : (
            docs.map((doc, i) => {
              const isSelected = selectedDocs.has(doc.filename);
              return (
                <div key={i} style={{ ...rowStyle, background: isSelected ? '#f0fdf4' : 'white' }}>
                  <button onClick={() => toggleDoc(doc.filename)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                    {isSelected ? <CheckSquare size={16} style={{ color: COLORS.grassGreen }} /> : <Square size={16} style={{ color: COLORS.textLight }} />}
                  </button>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: COLORS.text }}>
                      {doc.filename}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: COLORS.textLight }}>
                      {doc.chunk_count || doc.chunks || 0} chunks • {getProjectName(doc.project)}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: COLORS.textLight, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <User size={12} />
                    {doc.uploaded_by || 'System'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: COLORS.textLight, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <Calendar size={12} />
                    {formatDate(doc.uploaded_at || doc.created_at)}
                  </div>
                  <div></div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* PROCESSING HISTORY (Collapsed) */}
      <div style={{ ...sectionStyle, marginBottom: 0 }}>
        <button
          onClick={() => setShowHistory(!showHistory)}
          style={{
            ...headerStyle,
            cursor: 'pointer',
            width: '100%',
            border: 'none',
            borderBottom: showHistory ? '1px solid #e1e8ed' : 'none',
          }}
        >
          <Clock size={20} style={{ color: '#3b82f6' }} />
          <span style={{ fontWeight: 600, color: COLORS.text, flex: 1, textAlign: 'left' }}>Processing History</span>
          <span style={{ background: '#dbeafe', color: '#1e40af', padding: '0.2rem 0.6rem', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 600 }}>
            {recentJobs.length}
          </span>
          {showHistory && recentJobs.length > 0 && (
            <button
              onClick={(e) => { e.stopPropagation(); clearAllJobs(); }}
              disabled={deleting}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.35rem',
                padding: '0.35rem 0.6rem', background: '#f5f5f5', border: '1px solid #e1e8ed',
                borderRadius: '6px', color: COLORS.textLight, fontSize: '0.75rem', cursor: 'pointer',
              }}
            >
              Clear All
            </button>
          )}
          {showHistory ? <ChevronUp size={18} style={{ color: COLORS.textLight }} /> : <ChevronDown size={18} style={{ color: COLORS.textLight }} />}
        </button>

        {showHistory && (
          <div style={{ maxHeight: '250px', overflowY: 'auto' }}>
            {recentJobs.length === 0 ? (
              <div style={{ padding: '1.5rem', textAlign: 'center', color: COLORS.textLight, fontSize: '0.85rem' }}>
                No processing history
              </div>
            ) : (
              recentJobs.map((job) => (
                <div key={job.id} style={{ padding: '0.6rem 1rem', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  {getStatusIcon(job.status)}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {job.filename}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: COLORS.textLight }}>
                      {job.status} • {formatDate(job.created_at)}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
