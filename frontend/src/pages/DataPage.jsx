/**
 * DataPage.jsx - Streamlined Data Hub
 * 
 * SIMPLIFIED: 3 tabs focused on getting data IN
 * - Upload: Standard document upload
 * - Vacuum: Deep extraction tool
 * - Jobs: Processing status + file listing (combined)
 * 
 * Removed: Global Data, UKG Connections (moved to Admin)
 * Data browsing/management moved to Operations Center → Data Stores
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import Upload from '../components/Upload';
import api from '../services/api';
import {
  Upload as UploadIcon, Sparkles, ClipboardList, RefreshCw,
  CheckCircle, XCircle, Clock, Loader2, Trash2, StopCircle,
  FileText, Table2, ChevronDown, ChevronRight
} from 'lucide-react';

const COLORS = {
  grassGreen: '#83b16d',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

const TABS = [
  { id: 'upload', label: 'Upload', icon: UploadIcon },
  { id: 'vacuum', label: 'Vacuum', icon: Sparkles },
  { id: 'jobs', label: 'Jobs', icon: ClipboardList },
];

export default function DataPage() {
  const { activeProject, projectName } = useProject();
  const [activeTab, setActiveTab] = useState('upload');

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: '1.75rem',
          fontWeight: 700,
          color: COLORS.text,
          margin: 0,
        }}>
          Data
        </h1>
        <p style={{ color: COLORS.textLight, marginTop: '0.25rem' }}>
          Upload and process project data
          {projectName && <span> • <strong>{projectName}</strong></span>}
        </p>
      </div>

      {/* Card */}
      <div style={{
        background: 'white',
        borderRadius: '16px',
        boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
        overflow: 'hidden',
      }}>
        {/* Tabs */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid #e1e8ed',
          background: '#fafbfc',
        }}>
          {TABS.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '1rem 1.5rem',
                  border: 'none',
                  background: isActive ? 'white' : 'transparent',
                  color: isActive ? COLORS.grassGreen : COLORS.textLight,
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
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

        {/* Content */}
        <div style={{ padding: '1.5rem' }}>
          {activeTab === 'upload' && <UploadTab project={activeProject} />}
          {activeTab === 'vacuum' && <VacuumTab />}
          {activeTab === 'jobs' && <JobsTab />}
        </div>
      </div>
    </div>
  );
}

// ==================== UPLOAD TAB ====================
function UploadTab({ project }) {
  if (!project) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: COLORS.textLight }}>
        <UploadIcon size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
        <h3 style={{ margin: '0 0 0.5rem' }}>Select a Project</h3>
        <p>Choose a project from the top bar to upload data.</p>
      </div>
    );
  }
  return <Upload selectedProject={project} />;
}

// ==================== VACUUM TAB ====================
function VacuumTab() {
  return (
    <div style={{ textAlign: 'center', padding: '2rem' }}>
      <Sparkles size={48} style={{ color: COLORS.grassGreen, marginBottom: '1rem' }} />
      <h2 style={{ margin: '0 0 0.5rem', color: COLORS.text }}>Vacuum Extract</h2>
      <p style={{ color: COLORS.textLight, maxWidth: '500px', margin: '0 auto 1.5rem', lineHeight: 1.6 }}>
        Deep extraction tool for complex documents. Intelligent table detection, 
        multi-sheet processing, and semantic column mapping.
      </p>
      
      <Link
        to="/vacuum"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.875rem 1.75rem',
          background: COLORS.grassGreen,
          border: 'none',
          borderRadius: '10px',
          color: 'white',
          fontSize: '1rem',
          fontWeight: 600,
          textDecoration: 'none',
          boxShadow: '0 2px 8px rgba(131, 177, 109, 0.3)',
        }}
      >
        <Sparkles size={18} />
        Open Vacuum
      </Link>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '1rem',
        maxWidth: '600px',
        margin: '2rem auto 0',
        textAlign: 'left',
      }}>
        {[
          { icon: '📊', text: 'Smart table detection from PDFs' },
          { icon: '🔍', text: 'Multi-sheet Excel processing' },
          { icon: '🏷️', text: 'Automatic column classification' },
          { icon: '✨', text: 'Data quality profiling' },
        ].map((feature, i) => (
          <div key={i} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '1rem',
            background: '#f8fafc',
            borderRadius: '8px',
          }}>
            <span style={{ fontSize: '1.25rem' }}>{feature.icon}</span>
            <span style={{ fontSize: '0.9rem', color: COLORS.text }}>{feature.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==================== JOBS TAB (Combined Processing + Files) ====================
function JobsTab() {
  const { projects } = useProject();
  const [jobs, setJobs] = useState([]);
  const [structuredData, setStructuredData] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);
  const [killing, setKilling] = useState(null);
  const [expandedSection, setExpandedSection] = useState('jobs');

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
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  const killJob = async (jobId) => {
    if (!confirm('Kill this stuck job?')) return;
    setKilling(jobId);
    try {
      await api.post(`/jobs/${jobId}/fail`, null, { params: { error_message: 'Manually terminated' } });
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setKilling(null);
    }
  };

  const deleteJob = async (jobId) => {
    if (!confirm('Delete this job from history?')) return;
    setDeleting(jobId);
    try {
      await api.delete(`/jobs/${jobId}`);
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(null);
    }
  };

  const deleteStructuredFile = async (project, filename) => {
    if (!confirm(`Delete ${filename}?`)) return;
    setDeleting(`struct:${project}:${filename}`);
    try {
      await api.delete(`/status/structured/${encodeURIComponent(project)}/${encodeURIComponent(filename)}`);
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(null);
    }
  };

  const deleteDocument = async (filename) => {
    if (!confirm(`Delete ${filename} and all its chunks?`)) return;
    setDeleting(`doc:${filename}`);
    try {
      await api.delete(`/status/documents/${encodeURIComponent(filename)}`);
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(null);
    }
  };

  const getProjectName = (projectValue) => {
    if (!projectValue) return 'Unknown';
    if (projectValue === 'GLOBAL') return 'GLOBAL';
    if (projectValue.length === 36 && projectValue.includes('-')) {
      const found = projects.find(p => p.id === projectValue);
      return found ? found.name : projectValue.slice(0, 8) + '...';
    }
    return projectValue;
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

  const recentJobs = jobs.slice(0, 20);
  const activeJobs = jobs.filter(j => j.status === 'processing' || j.status === 'pending');
  const structuredFiles = structuredData?.files || [];
  const docs = documents?.documents || [];

  return (
    <div>
      {/* Summary Stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        {[
          { label: 'Active Jobs', value: activeJobs.length, color: '#3b82f6' },
          { label: 'Structured Files', value: structuredFiles.length, color: '#f59e0b' },
          { label: 'Documents', value: docs.length, color: '#10b981' },
          { label: 'Total Rows', value: (structuredData?.total_rows || 0).toLocaleString(), color: COLORS.grassGreen },
        ].map((stat, i) => (
          <div key={i} style={{
            background: '#f8fafc',
            borderRadius: '8px',
            padding: '1rem',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: stat.color, fontFamily: 'monospace' }}>
              {stat.value}
            </div>
            <div style={{ fontSize: '0.75rem', color: COLORS.textLight, marginTop: '0.25rem' }}>
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* Collapsible Sections */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Processing Jobs Section */}
        <Section
          title="Processing Jobs"
          icon={<ClipboardList size={18} />}
          count={recentJobs.length}
          expanded={expandedSection === 'jobs'}
          onToggle={() => setExpandedSection(expandedSection === 'jobs' ? null : 'jobs')}
        >
          {recentJobs.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: COLORS.textLight }}>
              No recent jobs
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e1e8ed' }}>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Status</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>File</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Project</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Started</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {recentJobs.map((job) => (
                  <tr key={job.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '0.75rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {getStatusIcon(job.status)}
                        <span style={{ textTransform: 'capitalize' }}>{job.status}</span>
                      </div>
                    </td>
                    <td style={{ padding: '0.75rem', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {job.filename}
                    </td>
                    <td style={{ padding: '0.75rem' }}>{getProjectName(job.project_id)}</td>
                    <td style={{ padding: '0.75rem', color: COLORS.textLight, fontSize: '0.8rem' }}>
                      {job.created_at ? new Date(job.created_at).toLocaleString() : '-'}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                        {job.status === 'processing' && (
                          <button
                            onClick={() => killJob(job.id)}
                            disabled={killing === job.id}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#f59e0b' }}
                            title="Kill Job"
                          >
                            <StopCircle size={16} />
                          </button>
                        )}
                        <button
                          onClick={() => deleteJob(job.id)}
                          disabled={deleting === job.id}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444' }}
                          title="Delete"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>

        {/* Structured Files Section */}
        <Section
          title="Structured Data"
          icon={<Table2 size={18} />}
          count={structuredFiles.length}
          expanded={expandedSection === 'structured'}
          onToggle={() => setExpandedSection(expandedSection === 'structured' ? null : 'structured')}
        >
          {structuredFiles.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: COLORS.textLight }}>
              No structured data files
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e1e8ed' }}>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>File</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Project</th>
                  <th style={{ textAlign: 'right', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Rows</th>
                  <th style={{ textAlign: 'right', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Sheets</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Delete</th>
                </tr>
              </thead>
              <tbody>
                {structuredFiles.map((file, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '0.75rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Table2 size={16} style={{ color: '#f59e0b' }} />
                        {file.filename}
                      </div>
                    </td>
                    <td style={{ padding: '0.75rem' }}>{getProjectName(file.project)}</td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace' }}>
                      {(file.total_rows || 0).toLocaleString()}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>{file.sheets?.length || 0}</td>
                    <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                      <button
                        onClick={() => deleteStructuredFile(file.project, file.filename)}
                        disabled={deleting === `struct:${file.project}:${file.filename}`}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444' }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>

        {/* Documents Section */}
        <Section
          title="Documents"
          icon={<FileText size={18} />}
          count={docs.length}
          expanded={expandedSection === 'docs'}
          onToggle={() => setExpandedSection(expandedSection === 'docs' ? null : 'docs')}
        >
          {docs.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: COLORS.textLight }}>
              No documents uploaded
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e1e8ed' }}>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Document</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Project</th>
                  <th style={{ textAlign: 'right', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Chunks</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem', color: COLORS.textLight, fontWeight: 600 }}>Delete</th>
                </tr>
              </thead>
              <tbody>
                {docs.slice(0, 50).map((doc, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '0.75rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <FileText size={16} style={{ color: '#10b981' }} />
                        {doc.filename}
                      </div>
                    </td>
                    <td style={{ padding: '0.75rem' }}>{getProjectName(doc.project)}</td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace' }}>
                      {doc.chunk_count || doc.chunks || 0}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                      <button
                        onClick={() => deleteDocument(doc.filename)}
                        disabled={deleting === `doc:${doc.filename}`}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444' }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {docs.length > 50 && (
            <div style={{ padding: '0.75rem', textAlign: 'center', color: COLORS.textLight, fontSize: '0.8rem' }}>
              Showing 50 of {docs.length} documents
            </div>
          )}
        </Section>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// Collapsible Section Component
function Section({ title, icon, count, expanded, onToggle, children }) {
  return (
    <div style={{
      border: '1px solid #e1e8ed',
      borderRadius: '8px',
      overflow: 'hidden',
    }}>
      <button
        onClick={onToggle}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '1rem',
          background: expanded ? '#f8fafc' : 'white',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {icon}
          <span style={{ fontWeight: 600, color: COLORS.text }}>{title}</span>
          <span style={{
            background: '#e1e8ed',
            padding: '0.2rem 0.6rem',
            borderRadius: '12px',
            fontSize: '0.75rem',
            color: COLORS.textLight,
          }}>
            {count}
          </span>
        </div>
        {expanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
      </button>
      {expanded && (
        <div style={{ borderTop: '1px solid #e1e8ed' }}>
          {children}
        </div>
      )}
    </div>
  );
}
