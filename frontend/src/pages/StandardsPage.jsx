/**
 * StandardsPage - Standards & Compliance
 * 
 * Upload compliance documents, extract rules, run compliance checks.
 * Project inherited from ContextBar (same pattern as PlaybooksPage).
 * 
 * Deploy to: frontend/src/pages/StandardsPage.jsx
 */

import React, { useState, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';
import { Tooltip } from '../components/ui';
import api from '../services/api';
import { 
  ScrollText, Upload, Library, ClipboardList, Search, FolderOpen,
  FileText, Trash2, CheckCircle, XCircle, Loader2, AlertTriangle, Play, Rocket, Folder
} from 'lucide-react';

// Brand Colors
const COLORS = {
  primary: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  white: '#f6f5fa',
  text: '#2a3441',
  textLight: '#5f6c7b',
  red: '#dc3545',
  redLight: '#f8d7da',
};

// Tab icon mapping
const TAB_ICONS = {
  upload: Upload,
  documents: Library,
  rules: ClipboardList,
  compliance: Search,
};

// =============================================================================
// SELECT PROJECT PROMPT (copied from PlaybooksPage)
// =============================================================================

function SelectProjectPrompt() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '50vh',
      textAlign: 'center',
      padding: '2rem',
    }}>
      <div style={{ 
        width: '64px', 
        height: '64px', 
        borderRadius: '16px',
        background: 'rgba(131, 177, 109, 0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: '1.5rem',
      }}>
        <FolderOpen size={28} color={COLORS.primary} />
      </div>
      <h2 style={{
        fontFamily: "'Sora', sans-serif",
        fontSize: '1.5rem',
        fontWeight: '700',
        color: COLORS.text,
        marginBottom: '0.75rem',
      }}>Select a Project First</h2>
      <p style={{
        color: COLORS.textLight,
        fontSize: '1rem',
        maxWidth: '400px',
        lineHeight: '1.6',
      }}>
        Choose a project from the selector above to run compliance checks.
      </p>
    </div>
  );
}

// =============================================================================
// UPLOAD TAB
// =============================================================================

function UploadTab({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [domain, setDomain] = useState('general');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('project', '__STANDARDS__');
    formData.append('standards_mode', 'true');
    formData.append('domain', domain);

    try {
      const response = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000
      });

      setResult(response.data);
      setFile(null);
      if (onUploadSuccess) onUploadSuccess();
    } catch (err) {
      console.error('Standards upload error:', err);
      setError(err.response?.data?.detail || err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const domains = [
    { value: 'general', label: 'General' },
    { value: 'retirement', label: 'Retirement / 401(k)' },
    { value: 'tax', label: 'Tax Compliance' },
    { value: 'benefits', label: 'Benefits' },
    { value: 'payroll', label: 'Payroll' },
  ];

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 0.25rem 0', color: '#2a3441', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FileText size={18} color={COLORS.primary} />
          Upload Standards Document
        </h3>
        <p style={{ margin: 0, color: '#5f6c7b', fontSize: '0.9rem' }}>
          Upload compliance documents (PDF, DOCX). XLR8 will extract actionable rules.
        </p>
      </div>

      <form onSubmit={handleUpload} style={{ maxWidth: '500px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Document File</label>
          <input
            type="file"
            accept=".pdf,.docx,.doc,.txt,.xlsx,.xls,.csv"
            onChange={(e) => setFile(e.target.files[0])}
            style={{ display: 'block', width: '100%', padding: '0.5rem', border: '1px solid #e1e8ed', borderRadius: '8px' }}
          />
          <span style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem', display: 'block' }}>
            Supported: PDF, Word, Excel, CSV, Text
          </span>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Domain</label>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px', fontSize: '1rem' }}
          >
            {domains.map(d => (
              <option key={d.value} value={d.value}>{d.label}</option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          disabled={!file || uploading}
          style={{
            padding: '0.75rem 1.5rem',
            background: COLORS.primary,
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontWeight: '600',
            fontSize: '1rem',
            cursor: 'pointer',
            opacity: (!file || uploading) ? 0.5 : 1,
          }}
        >
          {uploading ? (
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
              Processing...
            </span>
          ) : (
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Rocket size={16} />
              Upload & Extract Rules
            </span>
          )}
        </button>
      </form>

      {error && (
        <div style={{ padding: '1rem', background: '#f8d7da', color: '#721c24', borderRadius: '8px', marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <XCircle size={18} /> {error}
        </div>
      )}

      {result && (
        <div style={{ padding: '1rem', background: '#d4edda', color: '#155724', borderRadius: '8px', marginTop: '1rem' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle size={18} />
            Document Processed
          </h4>
          <p style={{ margin: '0.25rem 0' }}><strong>Title:</strong> {result.title}</p>
          <p style={{ margin: '0.25rem 0' }}><strong>Domain:</strong> {result.domain}</p>
          <p style={{ margin: '0.25rem 0' }}><strong>Rules Extracted:</strong> {result.rules_extracted}</p>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// RULES TAB
// =============================================================================

function RulesTab() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/standards/rules')
      .then(res => setRules(res.data.rules || []))
      .catch(() => setRules([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center', color: '#5f6c7b' }}>Loading...</div>;

  return (
    <div>
      <h3 style={{ margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <ClipboardList size={18} color={COLORS.primary} />
        Extracted Rules ({rules.length})
      </h3>
      {rules.length === 0 ? (
        <p style={{ color: '#5f6c7b' }}>No rules yet. Upload a standards document first.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {rules.map((rule, i) => (
            <div key={rule.rule_id || i} style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px', border: '1px solid #e1e8ed' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                <h4 style={{ margin: 0 }}>{rule.title}</h4>
                <span style={{
                  fontSize: '0.75rem',
                  padding: '0.2rem 0.5rem',
                  background: rule.severity === 'critical' ? '#f8d7da' :
                             rule.severity === 'high' ? '#fff3cd' :
                             rule.severity === 'medium' ? '#cce5ff' : '#d4edda',
                  color: rule.severity === 'critical' ? '#721c24' :
                         rule.severity === 'high' ? '#856404' :
                         rule.severity === 'medium' ? '#004085' : '#155724',
                  borderRadius: '4px',
                  fontWeight: '600',
                  textTransform: 'uppercase',
                }}>
                  {rule.severity || 'medium'}
                </span>
              </div>
              <p style={{ margin: '0 0 0.5rem 0', color: '#5f6c7b', fontSize: '0.9rem' }}>{rule.description}</p>
              <div style={{ fontSize: '0.8rem', color: '#5f6c7b', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><Folder size={14} /> {rule.category || 'general'}</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><FileText size={14} /> {rule.source_document}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// DOCUMENTS TAB - WITH DELETE FUNCTIONALITY
// =============================================================================

function DocumentsTab({ onDeleteSuccess }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);
  const [showClearAllModal, setShowClearAllModal] = useState(false);
  const [actionStatus, setActionStatus] = useState(null);

  const loadDocuments = async () => {
    setLoading(true);
    setActionStatus(null);
    try {
      // Try the new references endpoint first
      try {
        const res = await api.get('/status/references');
        setDocuments(res.data.files || []);
      } catch {
        // Fallback to standards/documents
        const res = await api.get('/standards/documents');
        setDocuments(res.data.documents || []);
      }
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleDelete = async (filename) => {
    if (!window.confirm(`Delete "${filename}"?\n\nThis will remove it from the registry, vector store, and rule registry.`)) {
      return;
    }
    
    setDeleting(filename);
    setActionStatus(null);
    try {
      await api.delete(`/status/references/${encodeURIComponent(filename)}?confirm=true`);
      setActionStatus({ type: 'success', message: `Deleted "${filename}"` });
      await loadDocuments();
      if (onDeleteSuccess) onDeleteSuccess();
    } catch (err) {
      setActionStatus({ type: 'error', message: err.response?.data?.detail || err.message || 'Delete failed' });
    } finally {
      setDeleting(null);
    }
  };

  const handleClearAll = async () => {
    setShowClearAllModal(false);
    setLoading(true);
    setActionStatus(null);
    try {
      const res = await api.delete('/status/references?confirm=true');
      setActionStatus({ type: 'success', message: `Cleared ${res.data.files_processed || 'all'} reference documents` });
      await loadDocuments();
      if (onDeleteSuccess) onDeleteSuccess();
    } catch (err) {
      setActionStatus({ type: 'error', message: err.response?.data?.detail || err.message || 'Clear failed' });
      setLoading(false);
    }
  };

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center', color: '#5f6c7b' }}>Loading...</div>;

  return (
    <div>
      {/* Header with actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Library size={18} color={COLORS.primary} />
          Documents ({documents.length})
        </h3>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {documents.length > 0 && (
            <button 
              onClick={() => setShowClearAllModal(true)} 
              style={{ 
                display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.75rem', 
                background: COLORS.redLight, border: `1px solid ${COLORS.red}40`, borderRadius: '6px', 
                color: COLORS.red, fontSize: '0.8rem', cursor: 'pointer', fontWeight: '500' 
              }}
            >
              <Trash2 size={14} /> Clear All
            </button>
          )}
          <button 
            onClick={loadDocuments} 
            style={{ 
              display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.75rem', 
              background: 'transparent', border: '1px solid #e1e8ed', borderRadius: '6px', 
              color: COLORS.textLight, fontSize: '0.8rem', cursor: 'pointer' 
            }}
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Status message */}
      {actionStatus && (
        <div style={{ 
          marginBottom: '1rem', padding: '0.75rem 1rem', 
          background: actionStatus.type === 'success' ? '#d4edda' : '#f8d7da', 
          border: `1px solid ${actionStatus.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`, 
          borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' 
        }}>
          <span style={{ color: actionStatus.type === 'success' ? '#155724' : '#721c24', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {actionStatus.type === 'success' ? <CheckCircle size={16} /> : <XCircle size={16} />} {actionStatus.message}
          </span>
          <button 
            onClick={() => setActionStatus(null)} 
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1rem', opacity: 0.6 }}
          >
            ✕
          </button>
        </div>
      )}

      {documents.length === 0 ? (
        <p style={{ color: '#5f6c7b' }}>No documents yet. Upload a standards document to get started.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {documents.map((doc, i) => (
            <div 
              key={doc.document_id || doc.id || doc.filename || i} 
              style={{ 
                padding: '1rem', background: '#f8f9fa', borderRadius: '8px', 
                border: '1px solid #e1e8ed', display: 'flex', alignItems: 'center', gap: '1rem' 
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <h4 style={{ margin: '0 0 0.25rem 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {doc.title || doc.filename}
                </h4>
                <p style={{ margin: '0', color: '#5f6c7b', fontSize: '0.85rem' }}>
                  {doc.domain || doc.truth_type || 'reference'} 
                  {doc.rule_count ? ` • ${doc.rule_count} rules` : ''}
                  {doc.chunk_count ? ` • ${doc.chunk_count} chunks` : ''}
                  {doc.file_size_bytes ? ` • ${formatFileSize(doc.file_size_bytes)}` : ''}
                </p>
              </div>
              <button
                onClick={() => handleDelete(doc.filename)}
                disabled={deleting === doc.filename}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  padding: '0.5rem 0.75rem', borderRadius: '6px',
                  background: deleting === doc.filename ? '#f8f9fa' : COLORS.redLight,
                  border: `1px solid ${COLORS.red}30`,
                  color: deleting === doc.filename ? COLORS.textLight : COLORS.red,
                  cursor: deleting === doc.filename ? 'wait' : 'pointer',
                  opacity: deleting === doc.filename ? 0.5 : 1,
                  fontSize: '0.8rem', fontWeight: '500',
                }}
                title="Delete document"
              >
                {deleting === doc.filename ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Trash2 size={14} />} Delete
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Clear All Confirmation Modal */}
      {showClearAllModal && (
        <div style={{ 
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', 
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 
        }}>
          <div style={{ 
            background: 'white', borderRadius: '12px', padding: '1.5rem', 
            maxWidth: '420px', margin: '1rem', boxShadow: '0 20px 40px rgba(0,0,0,0.3)'
          }}>
            <h3 style={{ margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertTriangle size={20} color={COLORS.red} />
              Clear All Documents?
            </h3>
            
            <p style={{ color: COLORS.textLight, fontSize: '0.9rem', margin: '0 0 1rem 0' }}>
              This will permanently delete all <strong>{documents.length}</strong> reference document(s) from:
            </p>
            
            <ul style={{ margin: '0 0 1rem 0', paddingLeft: '1.25rem', color: COLORS.textLight, fontSize: '0.85rem' }}>
              <li>Document Registry</li>
              <li>Vector Store (ChromaDB)</li>
              <li>Lineage Tracking</li>
              <li>Rule Registry</li>
            </ul>
            
            <p style={{ color: COLORS.red, fontWeight: '500', fontSize: '0.85rem', margin: '0 0 1.25rem 0' }}>
              This action cannot be undone.
            </p>
            
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button 
                onClick={() => setShowClearAllModal(false)}
                style={{ 
                  padding: '0.6rem 1rem', background: '#f8f9fa', 
                  border: '1px solid #e1e8ed', borderRadius: '8px', 
                  color: COLORS.text, fontWeight: '500', cursor: 'pointer', fontSize: '0.9rem' 
                }}
              >
                Cancel
              </button>
              <button 
                onClick={handleClearAll}
                style={{ 
                  padding: '0.6rem 1rem', background: COLORS.red, 
                  border: 'none', borderRadius: '8px', 
                  color: 'white', fontWeight: '600', cursor: 'pointer', fontSize: '0.9rem' 
                }}
              >
                Yes, Clear All
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper function
function formatFileSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// =============================================================================
// COMPLIANCE TAB - Uses activeProject from context
// =============================================================================

function ComplianceTab({ activeProject, projectName, customerName }) {
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const runCheck = async () => {
    if (!activeProject?.id) return;
    
    setRunning(true);
    setResults(null);
    setError(null);
    
    try {
      const res = await api.post(`/standards/compliance/check/${activeProject.id}`);
      setResults(res.data);
    } catch (e) {
      console.error('Compliance check error:', e);
      setError(e.response?.data?.detail || e.message || 'Compliance check failed');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <h3 style={{ margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Search size={18} color={COLORS.primary} />
        Run Compliance Check
      </h3>
      
      {/* Show current project context */}
      <div style={{ 
        padding: '1rem', 
        background: COLORS.iceFlow, 
        borderRadius: '8px', 
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem'
      }}>
        <ClipboardList size={28} color={COLORS.primary} />
        <div>
          <div style={{ fontWeight: '600', color: COLORS.text }}>{projectName}</div>
          <div style={{ fontSize: '0.85rem', color: COLORS.textLight }}>{customerName}</div>
        </div>
      </div>

      <button
        onClick={runCheck}
        disabled={running}
        style={{ 
          padding: '0.75rem 1.5rem', 
          background: COLORS.primary, 
          color: 'white', 
          border: 'none', 
          borderRadius: '8px', 
          fontWeight: '600', 
          cursor: 'pointer', 
          opacity: running ? 0.5 : 1,
          fontSize: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        {running ? (
          <>
            <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
            Running...
          </>
        ) : (
          <>
            <Play size={16} />
            Run Compliance Check
          </>
        )}
      </button>

      {error && (
        <div style={{ padding: '1rem', background: '#f8d7da', color: '#721c24', borderRadius: '8px', marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <XCircle size={18} /> {error}
        </div>
      )}

      {results && (
        <div style={{ marginTop: '1.5rem' }}>
          {/* Summary */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(3, 1fr)', 
            gap: '1rem',
            marginBottom: '1.5rem' 
          }}>
            <div style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: '700', color: COLORS.text }}>{results.rules_checked || 0}</div>
              <div style={{ fontSize: '0.85rem', color: COLORS.textLight }}>Rules Checked</div>
            </div>
            <div style={{ padding: '1rem', background: results.findings_count > 0 ? '#fff3cd' : '#d4edda', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: '700', color: results.findings_count > 0 ? '#856404' : '#155724' }}>
                {results.findings_count || 0}
              </div>
              <div style={{ fontSize: '0.85rem', color: COLORS.textLight }}>Findings</div>
            </div>
            <div style={{ padding: '1rem', background: '#d4edda', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: '700', color: '#155724' }}>{results.compliant_count || 0}</div>
              <div style={{ fontSize: '0.85rem', color: COLORS.textLight }}>Compliant</div>
            </div>
          </div>

          {/* Message */}
          {results.message && (
            <div style={{ padding: '1rem', background: '#cce5ff', color: '#004085', borderRadius: '8px', marginBottom: '1rem' }}>
              ℹ️ {results.message}
            </div>
          )}

          {/* Findings */}
          {results.findings && results.findings.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 1rem 0' }}>Findings</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {results.findings.map((finding, i) => (
                  <div key={i} style={{ 
                    padding: '1rem', 
                    background: '#f8f9fa', 
                    borderRadius: '8px', 
                    border: '1px solid #e1e8ed',
                    borderLeft: `4px solid ${
                      finding.severity === 'critical' ? '#dc3545' :
                      finding.severity === 'high' ? '#ffc107' :
                      finding.severity === 'medium' ? '#17a2b8' : '#28a745'
                    }`
                  }}>
                    <h5 style={{ margin: '0 0 0.5rem 0', color: COLORS.text }}>{finding.condition || finding.title}</h5>
                    {finding.criteria && <p style={{ margin: '0.25rem 0', fontSize: '0.9rem' }}><strong>Criteria:</strong> {finding.criteria}</p>}
                    {finding.cause && <p style={{ margin: '0.25rem 0', fontSize: '0.9rem' }}><strong>Cause:</strong> {finding.cause}</p>}
                    {finding.consequence && <p style={{ margin: '0.25rem 0', fontSize: '0.9rem' }}><strong>Consequence:</strong> {finding.consequence}</p>}
                    {finding.corrective_action && <p style={{ margin: '0.25rem 0', fontSize: '0.9rem' }}><strong>Action:</strong> {finding.corrective_action}</p>}
                    {finding.affected_count && (
                      <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: COLORS.textLight }}>
                        Affected: {finding.affected_count} records
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function StandardsPage() {
  const { activeProject, projectName, customerName, hasActiveProject, loading } = useProject();
  const [activeTab, setActiveTab] = useState('upload');
  const [key, setKey] = useState(0);

  const tabs = [
    { id: 'upload', label: 'Upload', icon: Upload, tooltip: { title: 'Upload Standards', detail: 'Upload compliance documents (PDF, DOCX). AI extracts rules automatically.', action: 'Supports SECURE 2.0, SOX, internal policies' } },
    { id: 'documents', label: 'Documents', icon: Library, tooltip: { title: 'Standards Library', detail: 'View all uploaded compliance documents and their metadata.', action: 'Delete or review document details' } },
    { id: 'rules', label: 'Rules', icon: ClipboardList, tooltip: { title: 'Extracted Rules', detail: 'AI-extracted compliance rules from your uploaded documents.', action: 'Rules are linked to playbooks for checking' } },
    { id: 'compliance', label: 'Compliance', icon: Search, tooltip: { title: 'Run Compliance Check', detail: 'Check project data against extracted rules.', action: 'Requires active project selection' } },
  ];

  // Refresh docs and rules tabs
  const handleRefresh = () => setKey(k => k + 1);

  // Show loading state
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
        <div className="spinner" />
      </div>
    );
  }

  // Compliance tab requires a project - other tabs don't
  const requiresProject = activeTab === 'compliance';

  return (
    <div>
      {/* Header - Standard Pattern */}
      <div style={{ marginBottom: '20px' }}>
        {hasActiveProject && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.85rem',
            color: COLORS.textLight,
            marginBottom: '0.5rem',
          }}>
            <span>{customerName}</span>
            <span>→</span>
            <span style={{ color: COLORS.primary, fontWeight: '600' }}>{projectName}</span>
          </div>
        )}
        <h1 style={{ 
          margin: 0, 
          fontSize: '20px', 
          fontWeight: 600, 
          color: '#2a3441', 
          display: 'flex', 
          alignItems: 'center', 
          gap: '10px',
          fontFamily: "'Sora', sans-serif"
        }}>
          <div style={{ 
            width: '36px', 
            height: '36px', 
            borderRadius: '10px', 
            backgroundColor: COLORS.primary, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center' 
          }}>
            <ScrollText size={20} color="#ffffff" />
          </div>
          Standards & Compliance
        </h1>
        <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: '#5f6c7b' }}>
          Upload compliance documents, extract rules, run checks
        </p>
      </div>

      <div style={{ background: 'white', borderRadius: '16px', boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)', overflow: 'hidden' }}>
        {/* Tab navigation */}
        <div style={{ display: 'flex', borderBottom: '1px solid #e1e8ed', background: '#fafbfc' }}>
          {tabs.map(tab => {
            const Icon = tab.icon;
            return (
              <Tooltip key={tab.id} title={tab.tooltip.title} detail={tab.tooltip.detail} action={tab.tooltip.action}>
                <button
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '1rem 1.5rem',
                    border: 'none', background: activeTab === tab.id ? 'white' : 'transparent',
                    color: activeTab === tab.id ? '#83b16d' : '#5f6c7b', fontWeight: '600', cursor: 'pointer',
                    borderBottom: activeTab === tab.id ? '2px solid #83b16d' : '2px solid transparent', marginBottom: '-1px',
                  }}
                >
                  <Icon size={16} />
                  {tab.label}
                </button>
              </Tooltip>
            );
          })}
        </div>

        {/* Tab content */}
        <div style={{ padding: '1.5rem' }}>
          {activeTab === 'upload' && <UploadTab onUploadSuccess={handleRefresh} />}
          {activeTab === 'documents' && <DocumentsTab key={key} onDeleteSuccess={handleRefresh} />}
          {activeTab === 'rules' && <RulesTab key={key} />}
          {activeTab === 'compliance' && (
            hasActiveProject ? (
              <ComplianceTab 
                activeProject={activeProject} 
                projectName={projectName} 
                customerName={customerName} 
              />
            ) : (
              <SelectProjectPrompt />
            )
          )}
        </div>
      </div>
    </div>
  );
}
