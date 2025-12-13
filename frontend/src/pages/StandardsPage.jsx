/**
 * StandardsPage - Uses same api service as working Upload component
 * 
 * Deploy to: frontend/src/pages/StandardsPage.jsx
 */

import React, { useState, useEffect } from 'react';
import api from '../services/api';

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

function DocumentsTab() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/standards/documents')
      .then(res => setDocuments(res.data.documents || []))
      .catch(() => setDocuments([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center', color: '#5f6c7b' }}>Loading...</div>;

  return (
    <div>
      <h3 style={{ margin: '0 0 1rem 0' }}>📚 Documents ({documents.length})</h3>
      {documents.length === 0 ? (
        <p style={{ color: '#5f6c7b' }}>No documents yet.</p>
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

function ComplianceTab() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);

  useEffect(() => {
    api.get('/projects')
      .then(res => setProjects(res.data.projects || res.data || []))
      .catch(() => {});
  }, []);

  const runCheck = async () => {
    if (!selectedProject) return;
    setRunning(true);
    setResults(null);
    try {
      const res = await api.post(`/standards/compliance/check/${selectedProject}`);
      setResults(res.data);
    } catch (e) {
      setResults({ error: e.message });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <h3 style={{ margin: '0 0 1rem 0' }}>🔍 Run Compliance Check</h3>
      <div style={{ maxWidth: '400px', marginBottom: '1rem' }}>
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px', marginBottom: '1rem' }}
        >
          <option value="">Select Project</option>
          {projects.map(p => (
            <option key={p.id || p.project_id} value={p.id || p.project_id}>{p.name || p.id}</option>
          ))}
        </select>
        <button
          onClick={runCheck}
          disabled={!selectedProject || running}
          style={{ padding: '0.75rem 1.5rem', background: '#83b16d', color: 'white', border: 'none', borderRadius: '8px', fontWeight: '600', cursor: 'pointer', opacity: (!selectedProject || running) ? 0.5 : 1 }}
        >
          {running ? '⏳ Running...' : '▶️ Run Check'}
        </button>
      </div>
      {results && (
        <div style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
          <p><strong>Rules Checked:</strong> {results.rules_checked}</p>
          <p><strong>Findings:</strong> {results.findings_count}</p>
          {results.message && <p>{results.message}</p>}
        </div>
      )}
    </div>
  );
}

export default function StandardsPage() {
  const [activeTab, setActiveTab] = useState('upload');
  const [key, setKey] = useState(0);

  const tabs = [
    { id: 'upload', label: 'Upload', icon: '📤' },
    { id: 'documents', label: 'Documents', icon: '📚' },
    { id: 'rules', label: 'Rules', icon: '📋' },
    { id: 'compliance', label: 'Compliance', icon: '🔍' },
  ];

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.75rem', fontWeight: '700', color: '#2a3441', margin: 0 }}>
          📜 Standards & Compliance
        </h1>
        <p style={{ color: '#5f6c7b', marginTop: '0.25rem' }}>Upload compliance documents, extract rules, run checks.</p>
      </div>

      <div style={{ background: 'white', borderRadius: '16px', boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)', overflow: 'hidden' }}>
        <div style={{ display: 'flex', borderBottom: '1px solid #e1e8ed', background: '#fafbfc' }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '1rem 1.5rem',
                border: 'none', background: activeTab === tab.id ? 'white' : 'transparent',
                color: activeTab === tab.id ? '#83b16d' : '#5f6c7b', fontWeight: '600', cursor: 'pointer',
                borderBottom: activeTab === tab.id ? '2px solid #83b16d' : '2px solid transparent', marginBottom: '-1px',
              }}
            >
              <span>{tab.icon}</span>{tab.label}
            </button>
          ))}
        </div>
        <div style={{ padding: '1.5rem' }}>
          {activeTab === 'upload' && <UploadTab onUploadSuccess={() => setKey(k => k + 1)} />}
          {activeTab === 'documents' && <DocumentsTab key={key} />}
          {activeTab === 'rules' && <RulesTab key={key} />}
          {activeTab === 'compliance' && <ComplianceTab />}
        </div>
      </div>
    </div>
  );
}
