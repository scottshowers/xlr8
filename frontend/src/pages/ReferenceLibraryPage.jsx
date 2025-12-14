/**
 * ReferenceLibraryPage.jsx - Reference Library (formerly Standards)
 * 
 * COMMAND CENTER AESTHETIC
 * Upload compliance documents, best practices, extract rules, run checks.
 * 
 * Renamed from StandardsPage to better reflect its purpose as a
 * cross-project reference library for consultants.
 */

import React, { useState, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';
import api from '../services/api';
import {
  Sun, Moon, Upload, FileText, ListChecks, Search as SearchIcon,
  RefreshCw, Trash2, ChevronDown, ChevronRight, AlertTriangle,
  CheckCircle, XCircle, BookOpen, Folder, Filter
} from 'lucide-react';

// Brand colors
const BRAND = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
};

// Theme definitions - matches Dashboard
const themes = {
  light: {
    bg: '#f6f5fa',
    bgCard: '#ffffff',
    border: '#e2e8f0',
    text: '#2a3441',
    textDim: '#5f6c7b',
    accent: BRAND.grassGreen,
  },
  dark: {
    bg: '#1a2332',
    bgCard: '#232f42',
    border: '#334766',
    text: '#e5e7eb',
    textDim: '#9ca3af',
    accent: BRAND.grassGreen,
  },
};

const STATUS = {
  green: '#10b981',
  amber: '#f59e0b',
  red: '#ef4444',
  blue: '#3b82f6',
};

export default function ReferenceLibraryPage() {
  const { activeProject, projectName, customerName, hasActiveProject, loading: projectLoading } = useProject();
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('xlr8-theme');
    return saved ? saved === 'dark' : true;
  });
  const [activeTab, setActiveTab] = useState('documents');
  const [time, setTime] = useState(new Date());

  const T = darkMode ? themes.dark : themes.light;

  useEffect(() => {
    localStorage.setItem('xlr8-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const tabs = [
    { id: 'documents', label: 'Documents', icon: BookOpen },
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'rules', label: 'Rules', icon: ListChecks },
    { id: 'compliance', label: 'Compliance Check', icon: SearchIcon },
  ];

  return (
    <div style={{
      padding: '1.5rem',
      background: T.bg,
      minHeight: '100vh',
      color: T.text,
      fontFamily: "'Inter', system-ui, sans-serif",
      transition: 'background 0.3s ease, color 0.3s ease',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem',
      }}>
        <div>
          <h1 style={{
            fontSize: '1.5rem',
            fontWeight: 700,
            margin: 0,
            letterSpacing: '0.05em',
            fontFamily: "'Sora', sans-serif",
          }}>
            REFERENCE LIBRARY
          </h1>
          <p style={{ color: T.textDim, margin: '0.25rem 0 0 0', fontSize: '0.85rem' }}>
            Compliance Standards, Best Practices & Rules
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={() => setDarkMode(!darkMode)}
            style={{
              background: T.bgCard,
              border: `1px solid ${T.border}`,
              borderRadius: '8px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              color: T.text,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
            }}
          >
            {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            {darkMode ? 'Light' : 'Dark'}
          </button>

          <div style={{
            fontFamily: 'monospace',
            fontSize: '1.5rem',
            color: T.accent,
            textShadow: darkMode ? `0 0 20px ${T.accent}40` : 'none',
          }}>
            {time.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: '0.5rem',
        marginBottom: '1.5rem',
        borderBottom: `1px solid ${T.border}`,
        paddingBottom: '0.5rem',
      }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              background: activeTab === tab.id ? T.accent : 'transparent',
              border: 'none',
              borderRadius: '6px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              color: activeTab === tab.id ? 'white' : T.textDim,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
              fontWeight: activeTab === tab.id ? 600 : 400,
              transition: 'all 0.2s ease',
            }}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{
        background: T.bgCard,
        border: `1px solid ${T.border}`,
        borderRadius: '12px',
        overflow: 'hidden',
      }}>
        <div style={{ padding: '1.5rem' }}>
          {activeTab === 'documents' && <DocumentsTab T={T} darkMode={darkMode} />}
          {activeTab === 'upload' && <UploadTab T={T} darkMode={darkMode} />}
          {activeTab === 'rules' && <RulesTab T={T} darkMode={darkMode} />}
          {activeTab === 'compliance' && (
            hasActiveProject ? (
              <ComplianceTab T={T} darkMode={darkMode} activeProject={activeProject} projectName={projectName} customerName={customerName} />
            ) : (
              <SelectProjectPrompt T={T} />
            )
          )}
        </div>
      </div>
    </div>
  );
}

// Select Project Prompt
function SelectProjectPrompt({ T }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '4rem',
      textAlign: 'center',
    }}>
      <Folder size={64} style={{ opacity: 0.3, color: T.textDim, marginBottom: '1.5rem' }} />
      <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>Select a Project First</h2>
      <p style={{ color: T.textDim, maxWidth: '400px' }}>
        Choose a project from the selector above to run compliance checks against your data.
      </p>
    </div>
  );
}

// Documents Tab
function DocumentsTab({ T, darkMode }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const res = await api.get('/standards/documents');
      setDocuments(res.data.documents || []);
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: T.textDim }}>
        <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
        <p>Loading documents...</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: T.textDim }}>
        <FileText size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
        <p>No documents uploaded yet.</p>
        <p style={{ fontSize: '0.85rem' }}>Upload compliance standards to get started.</p>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>
          📚 Reference Documents ({documents.length})
        </h3>
        <button
          onClick={loadDocuments}
          style={{
            background: T.bg,
            border: `1px solid ${T.border}`,
            borderRadius: '6px',
            padding: '0.5rem 0.75rem',
            cursor: 'pointer',
            color: T.text,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.8rem',
          }}
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {documents.map((doc, i) => (
          <div
            key={doc.id || i}
            style={{
              background: T.bg,
              border: `1px solid ${T.border}`,
              borderRadius: '8px',
              padding: '1rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <FileText size={24} style={{ color: T.accent }} />
              <div>
                <div style={{ fontWeight: 600 }}>{doc.title || doc.filename}</div>
                <div style={{ fontSize: '0.8rem', color: T.textDim }}>
                  {doc.domain} • {doc.rules_count || 0} rules • Uploaded {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'N/A'}
                </div>
              </div>
            </div>
            <div style={{
              padding: '0.25rem 0.75rem',
              background: darkMode ? `${T.accent}20` : '#f0fdf4',
              color: T.accent,
              fontSize: '0.75rem',
              fontWeight: 600,
              borderRadius: '20px',
            }}>
              {doc.domain || 'General'}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Upload Tab
function UploadTab({ T, darkMode }) {
  const [file, setFile] = useState(null);
  const [domain, setDomain] = useState('general');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const domains = [
    { value: 'general', label: 'General' },
    { value: 'retirement', label: 'Retirement / 401(k)' },
    { value: 'tax', label: 'Tax Compliance' },
    { value: 'benefits', label: 'Benefits' },
    { value: 'payroll', label: 'Payroll' },
    { value: 'security', label: 'Security / SOC' },
    { value: 'hr', label: 'HR Policies' },
  ];

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
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '0.75rem',
    background: T.bg,
    border: `1px solid ${T.border}`,
    borderRadius: '8px',
    color: T.text,
    fontSize: '0.9rem',
  };

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1rem', fontWeight: 600 }}>
          📤 Upload Reference Document
        </h3>
        <p style={{ margin: 0, color: T.textDim, fontSize: '0.85rem' }}>
          Upload compliance documents (PDF, DOCX). XLR8 will extract actionable rules.
        </p>
      </div>

      <form onSubmit={handleUpload} style={{ maxWidth: '500px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.85rem' }}>
            Document File
          </label>
          <input
            type="file"
            accept=".pdf,.docx,.doc,.txt"
            onChange={(e) => setFile(e.target.files[0])}
            style={inputStyle}
          />
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.85rem' }}>
            Domain Category
          </label>
          <select value={domain} onChange={(e) => setDomain(e.target.value)} style={inputStyle}>
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
            background: T.accent,
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontWeight: 600,
            cursor: 'pointer',
            opacity: (!file || uploading) ? 0.5 : 1,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          {uploading ? (
            <>
              <RefreshCw size={16} style={{ animation: 'spin 1s linear infinite' }} />
              Processing...
            </>
          ) : (
            <>
              <Upload size={16} />
              Upload & Extract Rules
            </>
          )}
        </button>
      </form>

      {error && (
        <div style={{
          padding: '1rem',
          background: darkMode ? `${STATUS.red}20` : '#fef2f2',
          border: `1px solid ${STATUS.red}40`,
          borderRadius: '8px',
          marginTop: '1rem',
          color: STATUS.red,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          <XCircle size={18} />
          {error}
        </div>
      )}

      {result && (
        <div style={{
          padding: '1rem',
          background: darkMode ? `${STATUS.green}20` : '#f0fdf4',
          border: `1px solid ${STATUS.green}40`,
          borderRadius: '8px',
          marginTop: '1rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: STATUS.green, fontWeight: 600 }}>
            <CheckCircle size={18} />
            Document Processed
          </div>
          <div style={{ fontSize: '0.85rem', color: T.text }}>
            <p style={{ margin: '0.25rem 0' }}><strong>Title:</strong> {result.title}</p>
            <p style={{ margin: '0.25rem 0' }}><strong>Domain:</strong> {result.domain}</p>
            <p style={{ margin: '0.25rem 0' }}><strong>Rules Extracted:</strong> {result.rules_extracted}</p>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// Rules Tab
function RulesTab({ T, darkMode }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    api.get('/standards/rules')
      .then(res => setRules(res.data.rules || []))
      .catch(() => setRules([]))
      .finally(() => setLoading(false));
  }, []);

  const toggleExpand = (id) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const getSeverityColor = (severity) => {
    if (severity === 'critical') return STATUS.red;
    if (severity === 'high') return STATUS.amber;
    if (severity === 'medium') return STATUS.blue;
    return STATUS.green;
  };

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: T.textDim }}>
        <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite' }} />
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div>
      <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: 600 }}>
        📋 Extracted Rules ({rules.length})
      </h3>

      {rules.length === 0 ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: T.textDim }}>
          <ListChecks size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
          <p>No rules yet. Upload a standards document first.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {rules.map((rule, i) => (
            <div
              key={rule.rule_id || i}
              style={{
                background: T.bg,
                border: `1px solid ${T.border}`,
                borderLeft: `4px solid ${getSeverityColor(rule.severity)}`,
                borderRadius: '8px',
                overflow: 'hidden',
              }}
            >
              <div
                onClick={() => toggleExpand(rule.rule_id || i)}
                style={{
                  padding: '1rem',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{rule.title}</div>
                  <div style={{ fontSize: '0.8rem', color: T.textDim }}>
                    {rule.domain} • {rule.severity}
                  </div>
                </div>
                {expanded[rule.rule_id || i] ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
              </div>
              {expanded[rule.rule_id || i] && (
                <div style={{ padding: '0 1rem 1rem', borderTop: `1px solid ${T.border}` }}>
                  <p style={{ margin: '1rem 0 0.5rem', fontSize: '0.85rem' }}>{rule.description}</p>
                  {rule.citation && (
                    <p style={{ margin: '0.25rem 0', fontSize: '0.8rem', color: T.textDim }}>
                      <strong>Citation:</strong> {rule.citation}
                    </p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Compliance Check Tab
function ComplianceTab({ T, darkMode, activeProject, projectName, customerName }) {
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

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
      <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: 600 }}>
        🔍 Run Compliance Check
      </h3>

      {/* Project Context */}
      <div style={{
        padding: '1rem',
        background: T.bg,
        border: `1px solid ${T.border}`,
        borderRadius: '8px',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
      }}>
        <Folder size={24} style={{ color: T.accent }} />
        <div>
          <div style={{ fontWeight: 600 }}>{projectName}</div>
          <div style={{ fontSize: '0.85rem', color: T.textDim }}>{customerName}</div>
        </div>
      </div>

      <button
        onClick={runCheck}
        disabled={running}
        style={{
          padding: '0.75rem 1.5rem',
          background: T.accent,
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          fontWeight: 600,
          cursor: 'pointer',
          opacity: running ? 0.5 : 1,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        {running ? (
          <>
            <RefreshCw size={16} style={{ animation: 'spin 1s linear infinite' }} />
            Running...
          </>
        ) : (
          <>
            <SearchIcon size={16} />
            Run Compliance Check
          </>
        )}
      </button>

      {error && (
        <div style={{
          padding: '1rem',
          background: darkMode ? `${STATUS.red}20` : '#fef2f2',
          border: `1px solid ${STATUS.red}40`,
          borderRadius: '8px',
          marginTop: '1rem',
          color: STATUS.red,
        }}>
          ❌ {error}
        </div>
      )}

      {results && (
        <div style={{ marginTop: '1.5rem' }}>
          {/* Summary Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
            {[
              { label: 'Rules Checked', value: results.rules_checked || 0, color: T.accent },
              { label: 'Findings', value: results.findings_count || 0, color: results.findings_count > 0 ? STATUS.amber : STATUS.green },
              { label: 'Compliant', value: results.compliant_count || 0, color: STATUS.green },
            ].map((stat, i) => (
              <div key={i} style={{
                padding: '1rem',
                background: T.bg,
                border: `1px solid ${T.border}`,
                borderRadius: '8px',
                textAlign: 'center',
              }}>
                <div style={{
                  fontSize: '2rem',
                  fontWeight: 700,
                  color: stat.color,
                  textShadow: darkMode ? `0 0 15px ${stat.color}40` : 'none',
                  fontFamily: 'monospace',
                }}>
                  {stat.value}
                </div>
                <div style={{ fontSize: '0.8rem', color: T.textDim }}>{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Findings */}
          {results.findings && results.findings.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.9rem', fontWeight: 600 }}>Findings</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {results.findings.map((finding, i) => (
                  <div key={i} style={{
                    background: T.bg,
                    border: `1px solid ${T.border}`,
                    borderLeft: `4px solid ${
                      finding.severity === 'critical' ? STATUS.red :
                      finding.severity === 'high' ? STATUS.amber : STATUS.blue
                    }`,
                    borderRadius: '8px',
                    padding: '1rem',
                  }}>
                    <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>{finding.condition || finding.title}</div>
                    {finding.criteria && <p style={{ margin: '0.25rem 0', fontSize: '0.85rem' }}><strong>Criteria:</strong> {finding.criteria}</p>}
                    {finding.cause && <p style={{ margin: '0.25rem 0', fontSize: '0.85rem' }}><strong>Cause:</strong> {finding.cause}</p>}
                    {finding.corrective_action && <p style={{ margin: '0.25rem 0', fontSize: '0.85rem' }}><strong>Action:</strong> {finding.corrective_action}</p>}
                    {finding.affected_count && (
                      <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: T.textDim }}>
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

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
