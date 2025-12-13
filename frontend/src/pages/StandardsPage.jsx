/**
 * StandardsPage - P4 Standards Layer
 * 
 * Deploy to: frontend/src/pages/StandardsPage.jsx
 */

import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'https://xlr8-backend-production.up.railway.app';

// ==================== UPLOAD TAB ====================
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
    formData.append('domain', domain);

    try {
      const response = await fetch(`${API_BASE}/api/upload-standards`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Upload failed: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      setResult(data);
      setFile(null);
      document.querySelector('input[type="file"]').value = '';
      if (onUploadSuccess) onUploadSuccess();
    } catch (err) {
      setError(err.message);
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
        <h3 style={{ margin: '0 0 0.25rem 0', color: '#2a3441' }}>📄 Upload Standards Document</h3>
        <p style={{ margin: 0, color: '#5f6c7b', fontSize: '0.9rem' }}>
          Upload compliance documents (PDF, DOCX). XLR8 will extract actionable rules.
        </p>
      </div>

      <form onSubmit={handleUpload} style={{ maxWidth: '500px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Document File</label>
          <input
            type="file"
            accept=".pdf,.docx,.doc,.txt"
            onChange={(e) => setFile(e.target.files[0])}
            style={{ display: 'block', width: '100%', padding: '0.5rem', border: '1px solid #e1e8ed', borderRadius: '8px' }}
          />
          {file && <span style={{ display: 'block', marginTop: '0.5rem', color: '#5f6c7b', fontSize: '0.85rem' }}>{file.name}</span>}
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
            background: '#83b16d',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontWeight: '600',
            fontSize: '1rem',
            cursor: 'pointer',
            opacity: (!file || uploading) ? 0.5 : 1,
          }}
        >
          {uploading ? '⏳ Processing...' : '🚀 Upload & Extract Rules'}
        </button>
      </form>

      {error && (
        <div style={{ padding: '1rem', background: '#f8d7da', color: '#721c24', borderRadius: '8px', marginTop: '1rem' }}>
          ❌ {error}
        </div>
      )}

      {result && (
        <div style={{ padding: '1rem', background: '#d4edda', color: '#155724', borderRadius: '8px', marginTop: '1rem' }}>
          <h4 style={{ margin: '0 0 0.5rem 0' }}>✅ Document Processed</h4>
          <p style={{ margin: '0.25rem 0' }}><strong>Title:</strong> {result.title}</p>
          <p style={{ margin: '0.25rem 0' }}><strong>Domain:</strong> {result.domain}</p>
          <p style={{ margin: '0.25rem 0' }}><strong>Rules Extracted:</strong> {result.rules_extracted}</p>
        </div>
      )}
    </div>
  );
}

// ==================== RULES TAB ====================
function RulesTab() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/standards/rules`)
      .then(res => res.json())
      .then(data => setRules(data.rules || []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center', color: '#5f6c7b' }}>Loading rules...</div>;
  if (error) return <div style={{ padding: '1rem', background: '#f8d7da', color: '#721c24', borderRadius: '8px' }}>❌ {error}</div>;

  return (
    <div>
      <h3 style={{ margin: '0 0 1rem 0' }}>📋 Extracted Rules ({rules.length})</h3>
      {rules.length === 0 ? (
        <p style={{ color: '#5f6c7b' }}>No rules yet. Upload a standards document first.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {rules.map((rule, i) => (
            <div key={rule.rule_id || i} style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px', border: '1px solid #e1e8ed' }}>
              <h4 style={{ margin: '0 0 0.5rem 0' }}>{rule.title}</h4>
              <p style={{ margin: '0', color: '#5f6c7b', fontSize: '0.9rem' }}>{rule.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== DOCUMENTS TAB ====================
function DocumentsTab() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/standards/documents`)
      .then(res => res.json())
      .then(data => setDocuments(data.documents || []))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center', color: '#5f6c7b' }}>Loading...</div>;

  return (
    <div>
      <h3 style={{ margin: '0 0 1rem 0' }}>📚 Standards Documents ({documents.length})</h3>
      {documents.length === 0 ? (
        <p style={{ color: '#5f6c7b' }}>No documents uploaded yet.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {documents.map((doc, i) => (
            <div key={doc.document_id || i} style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px', border: '1px solid #e1e8ed' }}>
              <h4 style={{ margin: '0 0 0.5rem 0' }}>{doc.title || doc.filename}</h4>
              <p style={{ margin: '0', color: '#5f6c7b', fontSize: '0.9rem' }}>
                Domain: {doc.domain} | Rules: {doc.rule_count || 0}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== COMPLIANCE TAB ====================
function ComplianceTab() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/projects`)
      .then(res => res.json())
      .then(data => setProjects(data.projects || data || []))
      .catch(err => console.error(err));
  }, []);

  const runCheck = async () => {
    if (!selectedProject) return;
    setRunning(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch(`${API_BASE}/api/standards/compliance/check/${selectedProject}`, { method: 'POST' });
      if (!response.ok) throw new Error('Check failed');
      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <h3 style={{ margin: '0 0 1rem 0' }}>🔍 Run Compliance Check</h3>
      
      <div style={{ maxWidth: '500px' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Select Project</label>
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px' }}
          >
            <option value="">-- Select --</option>
            {projects.map(p => (
              <option key={p.id || p.project_id} value={p.id || p.project_id}>
                {p.name || p.project_name || p.id}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={runCheck}
          disabled={!selectedProject || running}
          style={{
            padding: '0.75rem 1.5rem',
            background: '#83b16d',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontWeight: '600',
            cursor: 'pointer',
            opacity: (!selectedProject || running) ? 0.5 : 1,
          }}
        >
          {running ? '⏳ Running...' : '▶️ Run Check'}
        </button>
      </div>

      {error && <div style={{ padding: '1rem', background: '#f8d7da', color: '#721c24', borderRadius: '8px', marginTop: '1rem' }}>❌ {error}</div>}

      {results && (
        <div style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px', marginTop: '1rem' }}>
          <p><strong>Rules Checked:</strong> {results.rules_checked}</p>
          <p><strong>Findings:</strong> {results.findings_count}</p>
          {results.message && <p style={{ color: '#5f6c7b' }}>{results.message}</p>}
        </div>
      )}
    </div>
  );
}

// ==================== MAIN ====================
export default function StandardsPage() {
  const [activeTab, setActiveTab] = useState('upload');
  const [refreshKey, setRefreshKey] = useState(0);

  const tabs = [
    { id: 'upload', label: 'Upload', icon: '📤' },
    { id: 'documents', label: 'Documents', icon: '📚' },
    { id: 'rules', label: 'Rules', icon: '📋' },
    { id: 'compliance', label: 'Compliance', icon: '🔍' },
  ];

  const renderTab = () => {
    switch (activeTab) {
      case 'upload': return <UploadTab onUploadSuccess={() => setRefreshKey(k => k + 1)} />;
      case 'documents': return <DocumentsTab key={refreshKey} />;
      case 'rules': return <RulesTab key={refreshKey} />;
      case 'compliance': return <ComplianceTab />;
      default: return null;
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.75rem', fontWeight: '700', color: '#2a3441', margin: 0 }}>
          📜 Standards & Compliance
        </h1>
        <p style={{ color: '#5f6c7b', marginTop: '0.25rem' }}>
          Upload compliance documents, extract rules, run checks.
        </p>
      </div>

      <div style={{ background: 'white', borderRadius: '16px', boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)', overflow: 'hidden' }}>
        <div style={{ display: 'flex', borderBottom: '1px solid #e1e8ed', background: '#fafbfc' }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '1rem 1.5rem',
                border: 'none',
                background: activeTab === tab.id ? 'white' : 'transparent',
                color: activeTab === tab.id ? '#83b16d' : '#5f6c7b',
                fontWeight: '600',
                fontSize: '0.9rem',
                cursor: 'pointer',
                borderBottom: activeTab === tab.id ? '2px solid #83b16d' : '2px solid transparent',
                marginBottom: '-1px',
              }}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
        <div style={{ padding: '1.5rem' }}>
          {renderTab()}
        </div>
      </div>
    </div>
  );
}
