/**
 * StandardsPage - P4 Standards Layer Management
 * 
 * Tabs:
 * - Upload: Upload standards documents (PDF, DOCX)
 * - Rules: View extracted compliance rules
 * - Compliance: Run compliance checks against projects
 * - Findings: View compliance findings
 * 
 * Deploy to: frontend/src/pages/StandardsPage.jsx
 * 
 * Add route in App.jsx:
 *   import StandardsPage from './pages/StandardsPage';
 *   <Route path="/standards" element={<StandardsPage />} />
 * 
 * Add nav link in sidebar/navigation
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
      const response = await fetch(`${API_BASE}/api/standards/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
      setFile(null);
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
    { value: 'hr', label: 'HR / Employment' },
  ];

  return (
    <div>
      <div style={styles.sectionHeader}>
        <h3 style={styles.sectionTitle}>📄 Upload Standards Document</h3>
        <p style={styles.sectionSubtitle}>
          Upload compliance documents (PDF, DOCX). XLR8 will extract actionable rules for compliance checking.
        </p>
      </div>

      <form onSubmit={handleUpload} style={styles.uploadForm}>
        <div style={styles.formGroup}>
          <label style={styles.label}>Document File</label>
          <input
            type="file"
            accept=".pdf,.docx,.doc,.txt"
            onChange={(e) => setFile(e.target.files[0])}
            style={styles.fileInput}
          />
          {file && <span style={styles.fileName}>{file.name}</span>}
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Domain</label>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            style={styles.select}
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
            ...styles.button,
            opacity: (!file || uploading) ? 0.5 : 1,
          }}
        >
          {uploading ? '⏳ Processing...' : '🚀 Upload & Extract Rules'}
        </button>
      </form>

      {error && (
        <div style={styles.errorBox}>
          ❌ {error}
        </div>
      )}

      {result && (
        <div style={styles.successBox}>
          <h4 style={{ margin: '0 0 0.5rem 0' }}>✅ Document Processed</h4>
          <p style={{ margin: '0.25rem 0' }}><strong>Title:</strong> {result.title}</p>
          <p style={{ margin: '0.25rem 0' }}><strong>Domain:</strong> {result.domain}</p>
          <p style={{ margin: '0.25rem 0' }}><strong>Rules Extracted:</strong> {result.rules_extracted}</p>
          <p style={{ margin: '0.25rem 0' }}><strong>Pages:</strong> {result.page_count}</p>
          
          {result.rules && result.rules.length > 0 && (
            <div style={{ marginTop: '1rem' }}>
              <strong>Sample Rules:</strong>
              <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                {result.rules.slice(0, 3).map((rule, i) => (
                  <li key={i} style={{ marginBottom: '0.5rem' }}>
                    <strong>{rule.title}</strong>
                    <br />
                    <span style={{ color: '#5f6c7b', fontSize: '0.85rem' }}>{rule.description?.substring(0, 150)}...</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
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
  const [searchQuery, setSearchQuery] = useState('');

  const fetchRules = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/standards/rules?limit=100`);
      if (!response.ok) throw new Error('Failed to fetch rules');
      const data = await response.json();
      setRules(data.rules || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const filteredRules = rules.filter(rule => 
    !searchQuery || 
    rule.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    rule.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const severityColors = {
    critical: '#dc3545',
    high: '#fd7e14',
    medium: '#ffc107',
    low: '#28a745',
  };

  if (loading) return <div style={styles.loading}>Loading rules...</div>;
  if (error) return <div style={styles.errorBox}>❌ {error}</div>;

  return (
    <div>
      <div style={styles.sectionHeader}>
        <h3 style={styles.sectionTitle}>📋 Extracted Rules ({rules.length})</h3>
        <p style={styles.sectionSubtitle}>
          Compliance rules extracted from uploaded standards documents.
        </p>
      </div>

      <div style={styles.searchBar}>
        <input
          type="text"
          placeholder="Search rules..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={styles.searchInput}
        />
        <button onClick={fetchRules} style={styles.refreshButton}>🔄 Refresh</button>
      </div>

      {filteredRules.length === 0 ? (
        <div style={styles.emptyState}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>📭</div>
          <p>No rules found. Upload a standards document to extract rules.</p>
        </div>
      ) : (
        <div style={styles.rulesList}>
          {filteredRules.map((rule, index) => (
            <div key={rule.rule_id || index} style={styles.ruleCard}>
              <div style={styles.ruleHeader}>
                <span style={{ ...styles.severityBadge, background: severityColors[rule.severity] || '#6c757d' }}>
                  {rule.severity?.toUpperCase() || 'MEDIUM'}
                </span>
                <span style={styles.categoryBadge}>{rule.category || 'general'}</span>
              </div>
              <h4 style={styles.ruleTitle}>{rule.title}</h4>
              <p style={styles.ruleDescription}>{rule.description}</p>
              <div style={styles.ruleFooter}>
                <span>📄 {rule.source_document}</span>
                {rule.source_page && <span>Page {rule.source_page}</span>}
              </div>
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
  const [domain, setDomain] = useState('');
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch available projects
    fetch(`${API_BASE}/api/projects`)
      .then(res => res.json())
      .then(data => setProjects(data.projects || data || []))
      .catch(err => console.error('Failed to fetch projects:', err));
  }, []);

  const runComplianceCheck = async () => {
    if (!selectedProject) return;

    setRunning(true);
    setError(null);
    setResults(null);

    try {
      const url = new URL(`${API_BASE}/api/standards/compliance/check/${selectedProject}`);
      if (domain) url.searchParams.append('domain', domain);

      const response = await fetch(url, { method: 'POST' });
      if (!response.ok) throw new Error('Compliance check failed');
      
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
      <div style={styles.sectionHeader}>
        <h3 style={styles.sectionTitle}>🔍 Run Compliance Check</h3>
        <p style={styles.sectionSubtitle}>
          Check project data against extracted compliance rules.
        </p>
      </div>

      <div style={styles.complianceForm}>
        <div style={styles.formGroup}>
          <label style={styles.label}>Select Project</label>
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            style={styles.select}
          >
            <option value="">-- Select a project --</option>
            {projects.map(p => (
              <option key={p.id || p.project_id} value={p.id || p.project_id}>
                {p.name || p.project_name || p.id || p.project_id}
              </option>
            ))}
          </select>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Filter by Domain (optional)</label>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            style={styles.select}
          >
            <option value="">All domains</option>
            <option value="retirement">Retirement</option>
            <option value="tax">Tax</option>
            <option value="benefits">Benefits</option>
            <option value="payroll">Payroll</option>
          </select>
        </div>

        <button
          onClick={runComplianceCheck}
          disabled={!selectedProject || running}
          style={{
            ...styles.button,
            opacity: (!selectedProject || running) ? 0.5 : 1,
          }}
        >
          {running ? '⏳ Running Check...' : '▶️ Run Compliance Check'}
        </button>
      </div>

      {error && <div style={styles.errorBox}>❌ {error}</div>}

      {results && (
        <div style={styles.resultsBox}>
          <h4 style={{ margin: '0 0 1rem 0' }}>📊 Compliance Results</h4>
          <div style={styles.statsRow}>
            <div style={styles.statCard}>
              <div style={styles.statValue}>{results.rules_checked}</div>
              <div style={styles.statLabel}>Rules Checked</div>
            </div>
            <div style={{ ...styles.statCard, background: '#d4edda' }}>
              <div style={styles.statValue}>{results.compliant_count}</div>
              <div style={styles.statLabel}>Compliant</div>
            </div>
            <div style={{ ...styles.statCard, background: results.findings_count > 0 ? '#f8d7da' : '#d4edda' }}>
              <div style={styles.statValue}>{results.findings_count}</div>
              <div style={styles.statLabel}>Findings</div>
            </div>
          </div>

          {results.findings && results.findings.length > 0 && (
            <div style={{ marginTop: '1.5rem' }}>
              <h5>Findings:</h5>
              {results.findings.map((finding, i) => (
                <div key={i} style={styles.findingCard}>
                  <div style={styles.findingHeader}>
                    <span style={{ ...styles.severityBadge, background: finding.severity === 'critical' ? '#dc3545' : finding.severity === 'high' ? '#fd7e14' : '#ffc107' }}>
                      {finding.severity?.toUpperCase()}
                    </span>
                    <strong>{finding.title}</strong>
                  </div>
                  {finding.condition?.summary && (
                    <p style={{ margin: '0.5rem 0', color: '#5f6c7b' }}>
                      <strong>Condition:</strong> {finding.condition.summary}
                    </p>
                  )}
                  {finding.corrective_action?.immediate && (
                    <p style={{ margin: '0.5rem 0', color: '#28a745' }}>
                      <strong>Action:</strong> {finding.corrective_action.immediate}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {results.message && (
            <p style={{ color: '#5f6c7b', fontStyle: 'italic' }}>{results.message}</p>
          )}
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
      .catch(err => console.error('Failed to fetch documents:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={styles.loading}>Loading documents...</div>;

  return (
    <div>
      <div style={styles.sectionHeader}>
        <h3 style={styles.sectionTitle}>📚 Standards Documents ({documents.length})</h3>
        <p style={styles.sectionSubtitle}>
          Uploaded standards documents and their extracted rules.
        </p>
      </div>

      {documents.length === 0 ? (
        <div style={styles.emptyState}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>📭</div>
          <p>No documents uploaded yet. Go to the Upload tab to add standards.</p>
        </div>
      ) : (
        <div style={styles.documentList}>
          {documents.map((doc, index) => (
            <div key={doc.document_id || index} style={styles.documentCard}>
              <h4 style={{ margin: '0 0 0.5rem 0' }}>{doc.title || doc.filename}</h4>
              <p style={{ margin: '0.25rem 0', color: '#5f6c7b' }}>
                <strong>Domain:</strong> {doc.domain} | 
                <strong> Rules:</strong> {doc.rule_count || doc.rules?.length || 0} |
                <strong> Pages:</strong> {doc.page_count || '?'}
              </p>
              <p style={{ margin: '0.25rem 0', color: '#8a9bac', fontSize: '0.85rem' }}>
                Processed: {doc.processed_at ? new Date(doc.processed_at).toLocaleString() : 'Unknown'}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== MAIN COMPONENT ====================
export default function StandardsPage() {
  const [activeTab, setActiveTab] = useState('upload');
  const [refreshKey, setRefreshKey] = useState(0);

  const tabs = [
    { id: 'upload', label: 'Upload', icon: '📤' },
    { id: 'documents', label: 'Documents', icon: '📚' },
    { id: 'rules', label: 'Rules', icon: '📋' },
    { id: 'compliance', label: 'Compliance', icon: '🔍' },
  ];

  const handleUploadSuccess = () => {
    setRefreshKey(k => k + 1);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'upload': return <UploadTab onUploadSuccess={handleUploadSuccess} />;
      case 'documents': return <DocumentsTab key={refreshKey} />;
      case 'rules': return <RulesTab key={refreshKey} />;
      case 'compliance': return <ComplianceTab />;
      default: return null;
    }
  };

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.title}>📜 Standards & Compliance</h1>
        <p style={styles.subtitle}>Upload compliance documents, extract rules, and run compliance checks.</p>
      </div>

      <div style={styles.card}>
        <div style={styles.tabs}>
          {tabs.map(tab => (
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

// ==================== STYLES ====================
const styles = {
  header: { marginBottom: '1.5rem' },
  title: { fontFamily: "'Sora', sans-serif", fontSize: '1.75rem', fontWeight: '700', color: '#2a3441', margin: 0 },
  subtitle: { color: '#5f6c7b', marginTop: '0.25rem' },
  card: { background: 'white', borderRadius: '16px', boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)', overflow: 'hidden' },
  tabs: { display: 'flex', borderBottom: '1px solid #e1e8ed', background: '#fafbfc', overflowX: 'auto' },
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
  tabContent: { padding: '1.5rem' },
  
  // Section styles
  sectionHeader: { marginBottom: '1.5rem' },
  sectionTitle: { margin: '0 0 0.25rem 0', color: '#2a3441', fontSize: '1.25rem' },
  sectionSubtitle: { margin: 0, color: '#5f6c7b', fontSize: '0.9rem' },
  
  // Form styles
  uploadForm: { maxWidth: '500px' },
  complianceForm: { maxWidth: '500px' },
  formGroup: { marginBottom: '1rem' },
  label: { display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#2a3441' },
  fileInput: { display: 'block', width: '100%', padding: '0.5rem', border: '1px solid #e1e8ed', borderRadius: '8px' },
  fileName: { display: 'block', marginTop: '0.5rem', color: '#5f6c7b', fontSize: '0.85rem' },
  select: { width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px', fontSize: '1rem' },
  button: { padding: '0.75rem 1.5rem', background: '#83b16d', color: 'white', border: 'none', borderRadius: '8px', fontWeight: '600', fontSize: '1rem', cursor: 'pointer' },
  
  // Status boxes
  errorBox: { padding: '1rem', background: '#f8d7da', color: '#721c24', borderRadius: '8px', marginTop: '1rem' },
  successBox: { padding: '1rem', background: '#d4edda', color: '#155724', borderRadius: '8px', marginTop: '1rem' },
  resultsBox: { padding: '1.5rem', background: '#f8f9fa', borderRadius: '8px', marginTop: '1.5rem' },
  
  // Loading & empty
  loading: { color: '#5f6c7b', textAlign: 'center', padding: '3rem' },
  emptyState: { color: '#5f6c7b', textAlign: 'center', padding: '3rem' },
  
  // Search
  searchBar: { display: 'flex', gap: '1rem', marginBottom: '1.5rem' },
  searchInput: { flex: 1, padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px', fontSize: '1rem' },
  refreshButton: { padding: '0.75rem 1rem', background: '#f8f9fa', border: '1px solid #e1e8ed', borderRadius: '8px', cursor: 'pointer' },
  
  // Rules list
  rulesList: { display: 'flex', flexDirection: 'column', gap: '1rem' },
  ruleCard: { padding: '1rem', background: '#f8f9fa', borderRadius: '8px', border: '1px solid #e1e8ed' },
  ruleHeader: { display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' },
  ruleTitle: { margin: '0 0 0.5rem 0', color: '#2a3441' },
  ruleDescription: { margin: '0 0 0.75rem 0', color: '#5f6c7b', fontSize: '0.9rem' },
  ruleFooter: { display: 'flex', gap: '1rem', color: '#8a9bac', fontSize: '0.8rem' },
  severityBadge: { padding: '0.25rem 0.5rem', borderRadius: '4px', color: 'white', fontSize: '0.7rem', fontWeight: '700' },
  categoryBadge: { padding: '0.25rem 0.5rem', background: '#e1e8ed', borderRadius: '4px', color: '#5f6c7b', fontSize: '0.7rem' },
  
  // Stats
  statsRow: { display: 'flex', gap: '1rem', flexWrap: 'wrap' },
  statCard: { padding: '1rem', background: '#e9ecef', borderRadius: '8px', textAlign: 'center', minWidth: '120px' },
  statValue: { fontSize: '2rem', fontWeight: '700', color: '#2a3441' },
  statLabel: { fontSize: '0.85rem', color: '#5f6c7b' },
  
  // Findings
  findingCard: { padding: '1rem', background: 'white', borderRadius: '8px', border: '1px solid #e1e8ed', marginTop: '1rem' },
  findingHeader: { display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.5rem' },
  
  // Documents
  documentList: { display: 'flex', flexDirection: 'column', gap: '1rem' },
  documentCard: { padding: '1rem', background: '#f8f9fa', borderRadius: '8px', border: '1px solid #e1e8ed' },
};
