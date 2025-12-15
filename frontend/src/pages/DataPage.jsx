/**
 * DataPage.jsx - Streamlined Data Hub
 * 
 * 3 tabs: Upload | Vacuum | Jobs
 * Jobs tab has 3 columns: Processing, Structured, Documents
 */

import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { useUpload } from '../context/UploadContext';
import api from '../services/api';
import {
  Upload as UploadIcon, Sparkles, ClipboardList, RefreshCw,
  CheckCircle, XCircle, Clock, Loader2, Trash2, StopCircle,
  FileText, Table2, Calendar, Database
} from 'lucide-react';
import DataModelComponent from '../components/DataModelPage';

const COLORS = {
  grassGreen: '#83b16d',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

const TABS = [
  { id: 'upload', label: 'Upload', icon: UploadIcon },
  { id: 'vacuum', label: 'Vacuum', icon: Sparkles },
  { id: 'jobs', label: 'Jobs', icon: ClipboardList },
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
          Upload and process project data
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
          {activeTab === 'jobs' && <JobsTab />}
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
      <div style={{ textAlign: 'center', padding: '3rem', color: COLORS.textLight }}>
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
        <UploadIcon size={48} style={{ color: COLORS.grassGreen, marginBottom: '1rem' }} />
        <h3 style={{ margin: '0 0 0.5rem', color: COLORS.text }}>{dragOver ? 'Drop files here' : 'Click or drag files to upload'}</h3>
        <p style={{ color: COLORS.textLight, margin: 0, fontSize: '0.9rem' }}>PDF, Word, Excel, CSV, or Text files</p>
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
    <div style={{ textAlign: 'center', padding: '2rem' }}>
      <Sparkles size={48} style={{ color: COLORS.grassGreen, marginBottom: '1rem' }} />
      <h2 style={{ margin: '0 0 0.5rem', color: COLORS.text }}>Vacuum Extract</h2>
      <p style={{ color: COLORS.textLight, maxWidth: '500px', margin: '0 auto 1.5rem', lineHeight: 1.6 }}>
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

// ==================== JOBS TAB (3 Sections) ====================
function JobsTab() {
  const { projects } = useProject();
  const [jobs, setJobs] = useState([]);
  const [structuredData, setStructuredData] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);
  const [killing, setKilling] = useState(null);
  const [deleteStartDate, setDeleteStartDate] = useState('');
  const [deleteEndDate, setDeleteEndDate] = useState('');
  const [deletingRange, setDeletingRange] = useState(false);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [jobsRes, structRes, docsRes] = await Promise.all([
        api.get('/jobs').catch(() => ({ data: { jobs: [] } })),
        api.get('/status/structured').catch(() => ({ data: { files: [], total_rows: 0 } })),
        api.get('/status/documents').catch(() => ({ data: { documents: [] } })),
      ]);
      setJobs(jobsRes.data.jobs || []);
      setStructuredData(structRes.data);
      setDocuments(docsRes.data);
    } catch (err) { console.error('Failed to load:', err); }
    finally { setLoading(false); }
  };

  const killJob = async (jobId) => {
    if (!confirm('Kill this stuck job?')) return;
    setKilling(jobId);
    try { await api.post(`/jobs/${jobId}/fail`, null, { params: { error_message: 'Manually terminated' } }); loadData(); }
    catch (err) { alert('Error: ' + (err.response?.data?.detail || err.message)); }
    finally { setKilling(null); }
  };

  const deleteJob = async (jobId) => {
    if (!confirm('Delete this job?')) return;
    setDeleting(jobId);
    try { await api.delete(`/jobs/${jobId}`); loadData(); }
    catch (err) { alert('Error: ' + (err.response?.data?.detail || err.message)); }
    finally { setDeleting(null); }
  };

  const deleteJobsInRange = async () => {
    if (!deleteStartDate || !deleteEndDate) { alert('Select both dates'); return; }
    if (!confirm(`Delete all jobs between ${deleteStartDate} and ${deleteEndDate}?`)) return;
    setDeletingRange(true);
    try {
      await api.delete('/jobs/range', { params: { start_date: deleteStartDate, end_date: deleteEndDate } });
      setDeleteStartDate(''); setDeleteEndDate(''); loadData();
    } catch (err) { alert('Error: ' + (err.response?.data?.detail || err.message)); }
    finally { setDeletingRange(false); }
  };

  const deleteStructuredFile = async (project, filename) => {
    if (!confirm(`Delete ${filename}?`)) return;
    setDeleting(`struct:${project}:${filename}`);
    try { await api.delete(`/status/structured/${encodeURIComponent(project)}/${encodeURIComponent(filename)}`); loadData(); }
    catch (err) { alert('Error: ' + (err.response?.data?.detail || err.message)); }
    finally { setDeleting(null); }
  };

  const deleteDocument = async (filename) => {
    if (!confirm(`Delete ${filename}?`)) return;
    setDeleting(`doc:${filename}`);
    try { await api.delete(`/status/documents/${encodeURIComponent(filename)}`); loadData(); }
    catch (err) { alert('Error: ' + (err.response?.data?.detail || err.message)); }
    finally { setDeleting(null); }
  };

  const getProjectName = (pv) => {
    if (!pv) return 'Unknown';
    if (pv === 'GLOBAL') return 'GLOBAL';
    if (pv.length === 36 && pv.includes('-')) {
      const found = projects.find(p => p.id === pv);
      return found ? found.name : pv.slice(0, 8) + '...';
    }
    return pv;
  };

  const getStatusIcon = (status) => {
    if (status === 'completed') return <CheckCircle size={16} style={{ color: '#10b981' }} />;
    if (status === 'failed') return <XCircle size={16} style={{ color: '#ef4444' }} />;
    if (status === 'processing') return <Loader2 size={16} style={{ color: '#3b82f6', animation: 'spin 1s linear infinite' }} />;
    return <Clock size={16} style={{ color: '#f59e0b' }} />;
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

  const recentJobs = jobs.slice(0, 30);
  const activeJobs = jobs.filter(j => j.status === 'processing' || j.status === 'pending');
  const structuredFiles = structuredData?.files || [];
  const docs = documents?.documents || [];

  const sectionStyle = { background: '#f8fafc', border: '1px solid #e1e8ed', borderRadius: '12px', overflow: 'hidden' };
  const headerStyle = { padding: '0.75rem 1rem', borderBottom: '1px solid #e1e8ed', display: 'flex', alignItems: 'center', gap: '0.5rem' };
  const countBadge = { background: '#e1e8ed', padding: '0.1rem 0.5rem', borderRadius: '10px', fontSize: '0.75rem', color: COLORS.textLight };

  return (
    <div>
      {/* Summary Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          { label: 'Active Jobs', value: activeJobs.length, color: '#3b82f6' },
          { label: 'Structured Files', value: structuredFiles.length, color: '#f59e0b' },
          { label: 'Documents', value: docs.length, color: '#10b981' },
          { label: 'Total Rows', value: (structuredData?.total_rows || 0).toLocaleString(), color: COLORS.grassGreen },
        ].map((s, i) => (
          <div key={i} style={{ background: '#f8fafc', borderRadius: '8px', padding: '1rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: s.color, fontFamily: 'monospace' }}>{s.value}</div>
            <div style={{ fontSize: '0.75rem', color: COLORS.textLight, marginTop: '0.25rem' }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* 3-Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
        {/* JOBS SECTION */}
        <div style={sectionStyle}>
          <div style={headerStyle}>
            <ClipboardList size={18} style={{ color: '#3b82f6' }} />
            <span style={{ fontWeight: 600, color: COLORS.text }}>Jobs</span>
            <span style={countBadge}>{recentJobs.length}</span>
            <button onClick={loadData} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: COLORS.textLight }}>
              <RefreshCw size={14} />
            </button>
          </div>
          
          {/* Delete Range */}
          <div style={{ padding: '0.5rem 1rem', borderBottom: '1px solid #e1e8ed', background: 'white' }}>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <Calendar size={14} style={{ color: COLORS.textLight }} />
              <input type="date" value={deleteStartDate} onChange={(e) => setDeleteStartDate(e.target.value)}
                style={{ padding: '0.25rem 0.5rem', border: '1px solid #e1e8ed', borderRadius: '4px', fontSize: '0.7rem', flex: 1, minWidth: '90px' }} />
              <span style={{ color: COLORS.textLight, fontSize: '0.7rem' }}>to</span>
              <input type="date" value={deleteEndDate} onChange={(e) => setDeleteEndDate(e.target.value)}
                style={{ padding: '0.25rem 0.5rem', border: '1px solid #e1e8ed', borderRadius: '4px', fontSize: '0.7rem', flex: 1, minWidth: '90px' }} />
              <button onClick={deleteJobsInRange} disabled={deletingRange || !deleteStartDate || !deleteEndDate}
                style={{ padding: '0.25rem 0.5rem', background: deleteStartDate && deleteEndDate ? '#ef4444' : '#e1e8ed', color: deleteStartDate && deleteEndDate ? 'white' : COLORS.textLight, border: 'none', borderRadius: '4px', fontSize: '0.65rem', cursor: deleteStartDate && deleteEndDate ? 'pointer' : 'not-allowed' }}>
                {deletingRange ? '...' : 'Delete'}
              </button>
            </div>
          </div>

          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {recentJobs.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: COLORS.textLight, fontSize: '0.85rem' }}>No recent jobs</div>
            ) : (
              recentJobs.map((job) => (
                <div key={job.id} style={{ padding: '0.6rem 1rem', borderBottom: '1px solid #f0f0f0', background: 'white', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {getStatusIcon(job.status)}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{job.filename}</div>
                    <div style={{ fontSize: '0.65rem', color: COLORS.textLight }}>{getProjectName(job.project_id)}</div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.2rem' }}>
                    {job.status === 'processing' && (
                      <button onClick={() => killJob(job.id)} disabled={killing === job.id} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#f59e0b', padding: '0.2rem' }} title="Kill">
                        <StopCircle size={12} />
                      </button>
                    )}
                    <button onClick={() => deleteJob(job.id)} disabled={deleting === job.id} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', padding: '0.2rem' }} title="Delete">
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* STRUCTURED DATA SECTION */}
        <div style={sectionStyle}>
          <div style={headerStyle}>
            <Table2 size={18} style={{ color: '#f59e0b' }} />
            <span style={{ fontWeight: 600, color: COLORS.text }}>Structured Data</span>
            <span style={countBadge}>{structuredFiles.length}</span>
          </div>
          <div style={{ maxHeight: '450px', overflowY: 'auto' }}>
            {structuredFiles.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: COLORS.textLight, fontSize: '0.85rem' }}>No structured files</div>
            ) : (
              structuredFiles.map((file, i) => (
                <div key={i} style={{ padding: '0.6rem 1rem', borderBottom: '1px solid #f0f0f0', background: 'white', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Table2 size={14} style={{ color: '#f59e0b', flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.filename}</div>
                    <div style={{ fontSize: '0.65rem', color: COLORS.textLight }}>{getProjectName(file.project)} • {(file.total_rows || 0).toLocaleString()} rows</div>
                  </div>
                  <button onClick={() => deleteStructuredFile(file.project, file.filename)} disabled={deleting === `struct:${file.project}:${file.filename}`} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', padding: '0.2rem' }}>
                    <Trash2 size={12} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* DOCUMENTS SECTION */}
        <div style={sectionStyle}>
          <div style={headerStyle}>
            <FileText size={18} style={{ color: '#10b981' }} />
            <span style={{ fontWeight: 600, color: COLORS.text }}>Documents</span>
            <span style={countBadge}>{docs.length}</span>
          </div>
          <div style={{ maxHeight: '450px', overflowY: 'auto' }}>
            {docs.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: COLORS.textLight, fontSize: '0.85rem' }}>No documents</div>
            ) : (
              docs.slice(0, 50).map((doc, i) => (
                <div key={i} style={{ padding: '0.6rem 1rem', borderBottom: '1px solid #f0f0f0', background: 'white', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FileText size={14} style={{ color: '#10b981', flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.filename}</div>
                    <div style={{ fontSize: '0.65rem', color: COLORS.textLight }}>{getProjectName(doc.project)} • {doc.chunk_count || doc.chunks || 0} chunks</div>
                  </div>
                  <button onClick={() => deleteDocument(doc.filename)} disabled={deleting === `doc:${doc.filename}`} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', padding: '0.2rem' }}>
                    <Trash2 size={12} />
                  </button>
                </div>
              ))
            )}
            {docs.length > 50 && <div style={{ padding: '0.5rem', textAlign: 'center', color: COLORS.textLight, fontSize: '0.7rem' }}>+{docs.length - 50} more</div>}
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
