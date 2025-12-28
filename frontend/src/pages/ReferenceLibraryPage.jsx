/**
 * ReferenceLibraryPage.jsx - Reference Library
 * 
 * Clean professional design with:
 * - Light/dark mode support via ThemeContext
 * - Consistent styling with Command Center
 * - Delete functionality for reference documents
 */

import React, { useState, useEffect, useRef } from 'react';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import { getCustomerColorPalette } from '../utils/customerColors';
import { Tooltip } from '../components/ui';
import api from '../services/api';
import {
  Upload, FileText, ListChecks, Search as SearchIcon,
  RefreshCw, Trash2, ChevronDown, ChevronRight, AlertTriangle,
  CheckCircle, XCircle, BookOpen, Folder, Filter
} from 'lucide-react';

// Theme-aware colors - Mission Control palette
const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f0f2f5',
  card: dark ? '#242b3d' : '#ffffff',
  cardBorder: dark ? '#2d3548' : '#e2e8f0',
  text: dark ? '#e8eaed' : '#1a2332',
  textMuted: dark ? '#8b95a5' : '#64748b',
  textLight: dark ? '#5f6a7d' : '#94a3b8',
  primary: '#83b16d',
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.1)',
  accent: '#285390',
  accentLight: dark ? 'rgba(40, 83, 144, 0.15)' : 'rgba(40, 83, 144, 0.1)',
  blue: '#285390',
  blueLight: dark ? 'rgba(40, 83, 144, 0.15)' : 'rgba(40, 83, 144, 0.1)',
  warning: '#d97706',
  amber: '#d97706',
  amberLight: dark ? 'rgba(217, 119, 6, 0.15)' : 'rgba(217, 119, 6, 0.1)',
  red: '#993c44',
  redLight: dark ? 'rgba(153, 60, 68, 0.15)' : 'rgba(153, 60, 68, 0.1)',
  green: '#83b16d',
  greenLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.1)',
  divider: dark ? '#2d3548' : '#e2e8f0',
  inputBg: dark ? '#1a1f2e' : '#f8fafc',
  tabBg: dark ? '#1e2433' : '#fafbfc',
});

export default function ReferenceLibraryPage() {
  const { activeProject, projectName, customerName, hasActiveProject } = useProject();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  const [activeTab, setActiveTab] = useState('documents');

  const tabs = [
    { id: 'documents', label: 'Documents', icon: BookOpen, tooltip: { title: 'Reference Documents', detail: 'Browse uploaded reference documents organized by category.', action: 'Click to expand and view details' } },
    { id: 'upload', label: 'Upload', icon: Upload, tooltip: { title: 'Upload References', detail: 'Add new reference documents for best practices and compliance.', action: 'Supports PDF and DOCX' } },
    { id: 'rules', label: 'Rules', icon: ListChecks, tooltip: { title: 'Extracted Rules', detail: 'AI-extracted rules from your reference documents.', action: 'Rules power compliance checks' } },
    { id: 'compliance', label: 'Compliance Check', icon: SearchIcon, tooltip: { title: 'Run Compliance Check', detail: 'Check project data against reference rules.', action: 'Select a project first' } },
  ];

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.5rem', fontWeight: 700, color: colors.text, margin: 0 }}>
          Reference Library
        </h1>
        <p style={{ color: colors.textMuted, marginTop: '0.25rem', fontSize: '0.875rem' }}>
          Compliance Standards, Best Practices & Rules
        </p>
      </div>

      {/* Main Card */}
      <div style={{ background: colors.card, border: `1px solid ${colors.cardBorder}`, borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: `1px solid ${colors.divider}`, background: colors.tabBg }}>
          {tabs.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <Tooltip key={tab.id} title={tab.tooltip.title} detail={tab.tooltip.detail} action={tab.tooltip.action}>
                <button
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '1rem 1.25rem',
                    border: 'none', background: isActive ? colors.card : 'transparent',
                    color: isActive ? colors.primary : colors.textMuted, fontWeight: 600, fontSize: '0.85rem',
                    cursor: 'pointer', borderBottom: isActive ? `2px solid ${colors.primary}` : '2px solid transparent',
                    marginBottom: '-1px', transition: 'all 0.15s ease',
                  }}
                >
                  <Icon size={18} />
                  {tab.label}
                </button>
              </Tooltip>
            );
          })}
        </div>

        {/* Tab Content */}
        <div style={{ padding: '1.5rem' }}>
          {activeTab === 'documents' && <DocumentsTab colors={colors} darkMode={darkMode} />}
          {activeTab === 'upload' && <UploadTab colors={colors} darkMode={darkMode} />}
          {activeTab === 'rules' && <RulesTab colors={colors} darkMode={darkMode} />}
          {activeTab === 'compliance' && (
            hasActiveProject ? (
              <ComplianceTab colors={colors} darkMode={darkMode} activeProject={activeProject} projectName={projectName} customerName={customerName} />
            ) : (
              <SelectProjectPrompt colors={colors} />
            )
          )}
        </div>
      </div>
    </div>
  );
}

function SelectProjectPrompt({ colors }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4rem', textAlign: 'center' }}>
      <div style={{ width: 64, height: 64, borderRadius: 16, background: colors.primaryLight, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.25rem' }}>
        <Folder size={28} style={{ color: colors.primary }} />
      </div>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem', color: colors.text }}>Select a Project First</h2>
      <p style={{ color: colors.textMuted, maxWidth: '400px', margin: 0 }}>
        Choose a project from the selector above to run compliance checks against your data.
      </p>
    </div>
  );
}

function DocumentsTab({ colors, darkMode }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);
  const [showClearAllModal, setShowClearAllModal] = useState(false);
  const [actionStatus, setActionStatus] = useState(null);

  useEffect(() => { loadDocuments(); }, []);

  const loadDocuments = async () => {
    setLoading(true);
    setActionStatus(null);
    try {
      // Try the new references endpoint first, fallback to standards/documents
      try {
        const res = await api.get('/status/references');
        setDocuments(res.data.files || []);
      } catch {
        const res = await api.get('/standards/documents');
        setDocuments(res.data.documents || []);
      }
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

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
    } catch (err) {
      setActionStatus({ type: 'error', message: err.response?.data?.detail || err.message || 'Clear failed' });
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: colors.textMuted }}>
        <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
        <p>Loading documents...</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div>
      {/* Header with actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <BookOpen size={18} style={{ color: colors.primary }} />
          Reference Documents ({documents.length})
        </h3>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {documents.length > 0 && (
            <button 
              onClick={() => setShowClearAllModal(true)} 
              style={{ 
                display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.75rem', 
                background: colors.redLight, border: `1px solid ${colors.red}40`, borderRadius: 6, 
                color: colors.red, fontSize: '0.8rem', cursor: 'pointer', fontWeight: 500 
              }}
            >
              <Trash2 size={14} /> Clear All
            </button>
          )}
          <button 
            onClick={loadDocuments} 
            style={{ 
              display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.75rem', 
              background: 'transparent', border: `1px solid ${colors.divider}`, borderRadius: 6, 
              color: colors.textMuted, fontSize: '0.8rem', cursor: 'pointer' 
            }}
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Status message */}
      {actionStatus && (
        <div style={{ 
          marginBottom: '1rem', padding: '0.75rem 1rem', 
          background: actionStatus.type === 'success' ? colors.greenLight : colors.redLight, 
          border: `1px solid ${actionStatus.type === 'success' ? colors.green : colors.red}40`, 
          borderRadius: 8, display: 'flex', alignItems: 'center', gap: '0.5rem' 
        }}>
          {actionStatus.type === 'success' ? 
            <CheckCircle size={16} style={{ color: colors.green }} /> : 
            <XCircle size={16} style={{ color: colors.red }} />
          }
          <span style={{ color: actionStatus.type === 'success' ? colors.green : colors.red, fontSize: '0.85rem' }}>
            {actionStatus.message}
          </span>
          <button 
            onClick={() => setActionStatus(null)} 
            style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', padding: '0.25rem' }}
          >
            <XCircle size={14} style={{ color: colors.textMuted }} />
          </button>
        </div>
      )}

      {documents.length === 0 ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: colors.textMuted }}>
          <BookOpen size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
          <p style={{ margin: 0 }}>No documents in the reference library yet.</p>
          <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.85rem' }}>Upload compliance documents to get started.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {documents.map((doc, i) => (
            <div 
              key={doc.id || doc.filename || i} 
              style={{ 
                display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', 
                background: colors.inputBg, border: `1px solid ${colors.divider}`, borderRadius: 8 
              }}
            >
              <FileText size={18} style={{ color: colors.blue, flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.9rem', fontWeight: 500, color: colors.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {doc.filename}
                </div>
                <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>
                  {doc.rules_count || doc.chunk_count || 0} {doc.rules_count ? 'rules' : 'chunks'} • {doc.domain || doc.truth_type || 'reference'}
                  {doc.file_size_bytes && ` • ${formatFileSize(doc.file_size_bytes)}`}
                </div>
              </div>
              <span style={{ 
                padding: '0.2rem 0.5rem', 
                background: colors.greenLight, 
                color: colors.green, 
                borderRadius: 4, 
                fontSize: '0.7rem', 
                fontWeight: 600,
                flexShrink: 0 
              }}>
                {doc.status || doc.parse_status || 'Active'}
              </span>
              <button
                onClick={() => handleDelete(doc.filename)}
                disabled={deleting === doc.filename}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  width: 32, height: 32, borderRadius: 6,
                  background: deleting === doc.filename ? colors.inputBg : colors.redLight,
                  border: `1px solid ${colors.red}30`,
                  color: deleting === doc.filename ? colors.textMuted : colors.red,
                  cursor: deleting === doc.filename ? 'wait' : 'pointer',
                  opacity: deleting === doc.filename ? 0.5 : 1,
                  flexShrink: 0
                }}
                title="Delete document"
              >
                {deleting === doc.filename ? 
                  <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} /> : 
                  <Trash2 size={14} />
                }
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
            background: colors.card, borderRadius: 12, padding: '1.5rem', 
            maxWidth: 420, margin: '1rem', boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
            border: `1px solid ${colors.cardBorder}`
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{ 
                width: 40, height: 40, borderRadius: 10, background: colors.redLight, 
                display: 'flex', alignItems: 'center', justifyContent: 'center' 
              }}>
                <AlertTriangle size={20} style={{ color: colors.red }} />
              </div>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: colors.text }}>
                Clear All References?
              </h3>
            </div>
            
            <p style={{ color: colors.textMuted, fontSize: '0.9rem', margin: '0 0 1rem 0' }}>
              This will permanently delete all <strong>{documents.length}</strong> reference document(s) from:
            </p>
            
            <ul style={{ margin: '0 0 1rem 0', paddingLeft: '1.25rem', color: colors.textMuted, fontSize: '0.85rem' }}>
              <li>Document Registry</li>
              <li>Vector Store (ChromaDB)</li>
              <li>Lineage Tracking</li>
              <li>Rule Registry</li>
            </ul>
            
            <p style={{ color: colors.red, fontWeight: 500, fontSize: '0.85rem', margin: '0 0 1.25rem 0' }}>
              This action cannot be undone.
            </p>
            
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button 
                onClick={() => setShowClearAllModal(false)}
                style={{ 
                  padding: '0.6rem 1rem', background: colors.inputBg, 
                  border: `1px solid ${colors.divider}`, borderRadius: 8, 
                  color: colors.text, fontWeight: 500, cursor: 'pointer', fontSize: '0.9rem' 
                }}
              >
                Cancel
              </button>
              <button 
                onClick={handleClearAll}
                style={{ 
                  padding: '0.6rem 1rem', background: colors.red, 
                  border: 'none', borderRadius: 8, 
                  color: 'white', fontWeight: 600, cursor: 'pointer', fontSize: '0.9rem' 
                }}
              >
                Yes, Clear All
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
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

function UploadTab({ colors, darkMode }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const fileInputRef = useRef(null);

  const handleUpload = async (files) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadStatus(null);
    
    try {
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append('file', file);
        await api.post('/standards/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 300000 });
      }
      setUploadStatus({ type: 'success', message: `Successfully uploaded ${files.length} file(s)` });
    } catch (err) {
      setUploadStatus({ type: 'error', message: err.response?.data?.detail || err.message });
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); handleUpload(e.dataTransfer.files); };
  const handleFileSelect = (e) => { handleUpload(e.target.files); e.target.value = ''; };

  return (
    <div>
      <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Upload size={18} style={{ color: colors.primary }} />
        Upload Standards Documents
      </h3>
      
      <input type="file" ref={fileInputRef} style={{ display: 'none' }} multiple accept=".pdf,.docx,.doc,.txt,.md" onChange={handleFileSelect} />
      <div onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop} onClick={() => !uploading && fileInputRef.current?.click()} style={{ border: `2px dashed ${dragOver ? colors.primary : colors.divider}`, borderRadius: 12, padding: '3rem', textAlign: 'center', cursor: uploading ? 'wait' : 'pointer', background: dragOver ? colors.primaryLight : colors.inputBg, transition: 'all 0.2s ease', opacity: uploading ? 0.6 : 1 }}>
        {uploading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <RefreshCw size={48} style={{ color: colors.primary, marginBottom: '1rem', animation: 'spin 1s linear infinite' }} />
            <h3 style={{ margin: '0 0 0.5rem', color: colors.text }}>Processing...</h3>
            <p style={{ color: colors.textMuted, margin: 0, fontSize: '0.9rem' }}>Extracting rules from documents</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Upload size={48} style={{ color: colors.primary, marginBottom: '1rem' }} />
            <h3 style={{ margin: '0 0 0.5rem', color: colors.text }}>{dragOver ? 'Drop files here' : 'Click or drag files to upload'}</h3>
            <p style={{ color: colors.textMuted, margin: 0, fontSize: '0.9rem' }}>PDF, Word, or Text files containing compliance rules</p>
          </div>
        )}
      </div>

      {uploadStatus && (
        <div style={{ marginTop: '1rem', padding: '1rem', background: uploadStatus.type === 'success' ? colors.greenLight : colors.redLight, border: `1px solid ${uploadStatus.type === 'success' ? colors.green : colors.red}40`, borderRadius: 8, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {uploadStatus.type === 'success' ? <CheckCircle size={18} style={{ color: colors.green }} /> : <XCircle size={18} style={{ color: colors.red }} />}
          <span style={{ color: uploadStatus.type === 'success' ? colors.green : colors.red, fontSize: '0.9rem' }}>{uploadStatus.message}</span>
        </div>
      )}

      <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: colors.inputBg, borderRadius: 8, fontSize: '0.85rem', color: colors.textMuted, border: `1px solid ${colors.divider}` }}>
        💡 <strong>Tip:</strong> Upload compliance documents like Year-End Checklists, SECURE 2.0 guides, or internal policies. XLR8 will automatically extract actionable rules.
      </div>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function RulesTab({ colors, darkMode }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState({});
  const [clearing, setClearing] = useState(false);
  const [status, setStatus] = useState(null);

  const loadRules = () => {
    setLoading(true);
    api.get('/standards/rules').then(res => setRules(res.data.rules || [])).catch(() => setRules([])).finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRules();
  }, []);

  const handleClearRules = async () => {
    if (!window.confirm(`Clear all ${rules.length} rules?\n\nThis will delete from:\n- standards_documents table\n- standards_rules table\n- In-memory registry`)) {
      return;
    }
    
    setClearing(true);
    setStatus(null);
    try {
      const res = await api.delete('/status/references?confirm=true');
      setStatus({ type: 'success', message: `Cleared ${res.data.deleted?.standards_rules || 0} rules` });
      loadRules();
    } catch (err) {
      setStatus({ type: 'error', message: err.response?.data?.detail || err.message || 'Clear failed' });
    } finally {
      setClearing(false);
    }
  };

  const toggleExpand = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }));

  const getSeverityColor = (severity) => {
    if (severity === 'critical') return colors.red;
    if (severity === 'high') return colors.amber;
    if (severity === 'medium') return colors.blue;
    return colors.green;
  };

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: colors.textMuted }}>
        <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite' }} />
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div>
      {/* Header with actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <ListChecks size={18} style={{ color: colors.primary }} />
          Extracted Rules ({rules.length})
        </h3>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {rules.length > 0 && (
            <button 
              onClick={handleClearRules}
              disabled={clearing}
              style={{ 
                display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.75rem', 
                background: colors.redLight, border: `1px solid ${colors.red}40`, borderRadius: 6, 
                color: colors.red, fontSize: '0.8rem', cursor: clearing ? 'wait' : 'pointer', 
                fontWeight: 500, opacity: clearing ? 0.5 : 1
              }}
            >
              {clearing ? <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Trash2 size={14} />}
              {clearing ? 'Clearing...' : 'Clear All Rules'}
            </button>
          )}
          <button 
            onClick={loadRules}
            style={{ 
              display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.75rem', 
              background: 'transparent', border: `1px solid ${colors.divider}`, borderRadius: 6, 
              color: colors.textMuted, fontSize: '0.8rem', cursor: 'pointer' 
            }}
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Status message */}
      {status && (
        <div style={{ 
          marginBottom: '1rem', padding: '0.75rem 1rem', 
          background: status.type === 'success' ? colors.greenLight : colors.redLight, 
          border: `1px solid ${status.type === 'success' ? colors.green : colors.red}40`, 
          borderRadius: 8, display: 'flex', alignItems: 'center', gap: '0.5rem' 
        }}>
          {status.type === 'success' ? 
            <CheckCircle size={16} style={{ color: colors.green }} /> : 
            <XCircle size={16} style={{ color: colors.red }} />
          }
          <span style={{ color: status.type === 'success' ? colors.green : colors.red, fontSize: '0.85rem' }}>
            {status.message}
          </span>
          <button 
            onClick={() => setStatus(null)} 
            style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', padding: '0.25rem' }}
          >
            <XCircle size={14} style={{ color: colors.textMuted }} />
          </button>
        </div>
      )}

      {rules.length === 0 ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: colors.textMuted }}>
          <ListChecks size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
          <p style={{ margin: 0 }}>No rules yet. Upload a standards document first.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {rules.map((rule, i) => (
            <div key={rule.rule_id || i} style={{ background: colors.inputBg, border: `1px solid ${colors.divider}`, borderLeft: `4px solid ${getSeverityColor(rule.severity)}`, borderRadius: 8, overflow: 'hidden' }}>
              <div onClick={() => toggleExpand(rule.rule_id || i)} style={{ padding: '1rem', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, marginBottom: '0.25rem', color: colors.text }}>{rule.title}</div>
                  <div style={{ fontSize: '0.8rem', color: colors.textMuted }}>{rule.domain} • {rule.severity}</div>
                </div>
                {expanded[rule.rule_id || i] ? <ChevronDown size={20} style={{ color: colors.textMuted }} /> : <ChevronRight size={20} style={{ color: colors.textMuted }} />}
              </div>
              {expanded[rule.rule_id || i] && (
                <div style={{ padding: '0 1rem 1rem', borderTop: `1px solid ${colors.divider}` }}>
                  <p style={{ margin: '1rem 0 0.5rem', fontSize: '0.85rem', color: colors.text }}>{rule.description}</p>
                  {rule.citation && <p style={{ margin: '0.25rem 0', fontSize: '0.8rem', color: colors.textMuted }}><strong>Citation:</strong> {rule.citation}</p>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function ComplianceTab({ colors, darkMode, activeProject, projectName, customerName }) {
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const customerColors = getCustomerColorPalette(customerName || projectName);

  const runCheck = async () => {
    setRunning(true);
    setError(null);
    setResults(null);
    try {
      const response = await api.post('/standards/check', { project_id: activeProject }, { timeout: 180000 });
      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Compliance check failed');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <SearchIcon size={18} style={{ color: colors.primary }} />
        Run Compliance Check
      </h3>

      {/* Project Context */}
      <div style={{ padding: '1rem', background: customerColors.bg, border: `1px solid ${customerColors.primary}40`, borderLeft: `4px solid ${customerColors.primary}`, borderRadius: 8, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <Folder size={24} style={{ color: customerColors.primary }} />
        <div>
          <div style={{ fontWeight: 600, color: customerColors.primary }}>{projectName}</div>
          <div style={{ fontSize: '0.85rem', color: colors.textMuted }}>{customerName}</div>
        </div>
      </div>

      <button onClick={runCheck} disabled={running} style={{ padding: '0.75rem 1.5rem', background: colors.primary, color: 'white', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer', opacity: running ? 0.5 : 1, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        {running ? (<><RefreshCw size={16} style={{ animation: 'spin 1s linear infinite' }} />Running...</>) : (<><SearchIcon size={16} />Run Compliance Check</>)}
      </button>

      {error && (
        <div style={{ padding: '1rem', background: colors.redLight, border: `1px solid ${colors.red}40`, borderRadius: 8, marginTop: '1rem', color: colors.red, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <XCircle size={18} /> {error}
        </div>
      )}

      {results && (
        <div style={{ marginTop: '1.5rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
            {[
              { label: 'Rules Checked', value: results.rules_checked || 0, color: colors.primary },
              { label: 'Findings', value: results.findings_count || 0, color: results.findings_count > 0 ? colors.amber : colors.green },
              { label: 'Compliant', value: results.compliant_count || 0, color: colors.green },
            ].map((stat, i) => (
              <div key={i} style={{ padding: '1rem', background: colors.inputBg, border: `1px solid ${colors.divider}`, borderRadius: 8, textAlign: 'center' }}>
                <div style={{ fontSize: '2rem', fontWeight: 700, color: stat.color, fontFamily: 'monospace' }}>{stat.value}</div>
                <div style={{ fontSize: '0.8rem', color: colors.textMuted }}>{stat.label}</div>
              </div>
            ))}
          </div>

          {results.findings && results.findings.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.9rem', fontWeight: 600, color: colors.text }}>Findings</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {results.findings.map((finding, i) => (
                  <div key={i} style={{ background: colors.inputBg, border: `1px solid ${colors.divider}`, borderLeft: `4px solid ${finding.severity === 'critical' ? colors.red : finding.severity === 'high' ? colors.amber : colors.blue}`, borderRadius: 8, padding: '1rem' }}>
                    <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: colors.text }}>{finding.condition || finding.title}</div>
                    {finding.criteria && <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: colors.text }}><strong>Criteria:</strong> {finding.criteria}</p>}
                    {finding.cause && <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: colors.text }}><strong>Cause:</strong> {finding.cause}</p>}
                    {finding.corrective_action && <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: colors.text }}><strong>Action:</strong> {finding.corrective_action}</p>}
                    {finding.affected_count && <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: colors.textMuted }}>Affected: {finding.affected_count} records</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
