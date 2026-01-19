/**
 * IntelligenceTestPage.jsx
 * ========================
 * 
 * Interactive test page for the Intelligence Pipeline
 * - Diagnose project data availability
 * - Run Analyze (populates _intelligence_lookups)
 * - Run Recalc (builds term index)
 * - Test 5 engines
 * - Test query resolution with sample questions
 * 
 * Route: /admin/intelligence-test
 * Updated: January 17, 2026 - Matching platform UX
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { 
  ArrowLeft, Play, RefreshCw, Search, CheckCircle, XCircle, 
  Loader2, Brain, Database, Zap, ChevronDown, ChevronRight,
  Copy, Check, AlertTriangle
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

// Sample test questions
const SAMPLE_QUESTIONS = [
  { query: 'employees in Texas', description: 'Term index fast path (state lookup)' },
  { query: 'employees with 401k', description: 'MetadataReasoner fallback (deduction search)' },
  { query: 'employees in Texas with 401k', description: 'Cross-domain JOIN test' },
  { query: 'active employees', description: 'Status code mapping' },
  { query: 'hourly employees in California', description: 'Multi-filter test' },
];

export default function IntelligenceTestPage() {
  const { activeProject } = useProject();
  // Always use TEA1000 for testing - this is a test page
  const projectId = 'TEA1000';
  
  // State for each operation
  const [analyzeStatus, setAnalyzeStatus] = useState({ loading: false, result: null, error: null });
  const [recalcStatus, setRecalcStatus] = useState({ loading: false, result: null, error: null });
  const [queryResults, setQueryResults] = useState({});
  const [customQuery, setCustomQuery] = useState('');
  const [expandedResults, setExpandedResults] = useState({});
  const [copiedText, setCopiedText] = useState(null);
  
  // Engine test state
  const [enginesStatus, setEnginesStatus] = useState({ loading: false, result: null, error: null });
  const [selectedEngine, setSelectedEngine] = useState('aggregate');
  const [engineConfig, setEngineConfig] = useState('');
  const [engineTestResult, setEngineTestResult] = useState({ loading: false, result: null, error: null });
  const [diagnoseStatus, setDiagnoseStatus] = useState({ loading: false, result: null, error: null });

  // Helper to copy text
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedText(text);
    setTimeout(() => setCopiedText(null), 2000);
  };

  // Run Analyze
  const runAnalyze = async () => {
    setAnalyzeStatus({ loading: true, result: null, error: null });
    try {
      const response = await fetch(`${API_BASE}/api/intelligence/${projectId}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await response.json();
      setAnalyzeStatus({ loading: false, result: data, error: null });
    } catch (err) {
      setAnalyzeStatus({ loading: false, result: null, error: err.message });
    }
  };

  // Run Recalc
  const runRecalc = async () => {
    setRecalcStatus({ loading: true, result: null, error: null });
    try {
      const response = await fetch(`${API_BASE}/api/customers/${projectId}/recalc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ what: ['terms', 'entities', 'joins'] })
      });
      const data = await response.json();
      setRecalcStatus({ loading: false, result: data, error: null });
    } catch (err) {
      setRecalcStatus({ loading: false, result: null, error: err.message });
    }
  };

  // Run quick engine tests
  const runEnginesQuickTest = async () => {
    setEnginesStatus({ loading: true, result: null, error: null });
    try {
      const response = await fetch(`${API_BASE}/api/intelligence/${projectId}/test-engines-quick`);
      const data = await response.json();
      setEnginesStatus({ loading: false, result: data, error: null });
    } catch (err) {
      setEnginesStatus({ loading: false, result: null, error: err.message });
    }
  };

  // Diagnose project data
  const runDiagnose = async () => {
    setDiagnoseStatus({ loading: true, result: null, error: null });
    try {
      const response = await fetch(`${API_BASE}/api/intelligence/${projectId}/diagnose`);
      const data = await response.json();
      setDiagnoseStatus({ loading: false, result: data, error: null });
    } catch (err) {
      setDiagnoseStatus({ loading: false, result: null, error: err.message });
    }
  };

  // Test single engine with config
  const runEngineTest = async () => {
    setEngineTestResult({ loading: true, result: null, error: null });
    try {
      let config;
      try {
        config = JSON.parse(engineConfig);
      } catch (e) {
        setEngineTestResult({ loading: false, result: null, error: 'Invalid JSON config' });
        return;
      }
      
      const response = await fetch(`${API_BASE}/api/intelligence/${projectId}/test-engine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ engine: selectedEngine, config })
      });
      const data = await response.json();
      setEngineTestResult({ loading: false, result: data, error: null });
    } catch (err) {
      setEngineTestResult({ loading: false, result: null, error: err.message });
    }
  };

  // Sample configs for each engine
  const ENGINE_SAMPLE_CONFIGS = {
    aggregate: {
      source_table: "YOUR_TABLE_NAME",
      measures: [{ function: "COUNT" }],
      dimensions: ["stateprovince"]
    },
    compare: {
      source_a: "TABLE_A",
      source_b: "TABLE_B"
    },
    validate: {
      source_table: "YOUR_TABLE_NAME",
      rules: [
        { field: "email", type: "format", pattern: "email" },
        { field: "employeeid", type: "not_null" }
      ]
    },
    detect: {
      source_table: "YOUR_TABLE_NAME",
      patterns: [
        { type: "duplicate", columns: ["email"] },
        { type: "duplicate", columns: ["employeeid"] }
      ]
    },
    map: {
      mode: "lookup",
      value: "TX",
      type: "state_names"
    }
  };

  // Load sample config when engine changes
  const handleEngineChange = (engine) => {
    setSelectedEngine(engine);
    setEngineConfig(JSON.stringify(ENGINE_SAMPLE_CONFIGS[engine], null, 2));
  };

  // Test a query
  const testQuery = async (question) => {
    setQueryResults(prev => ({
      ...prev,
      [question]: { loading: true, result: null, error: null }
    }));
    try {
      const response = await fetch(
        `${API_BASE}/api/customers/${projectId}/resolve-terms?question=${encodeURIComponent(question)}`,
        { method: 'POST' }
      );
      const data = await response.json();
      setQueryResults(prev => ({
        ...prev,
        [question]: { loading: false, result: data, error: null }
      }));
      setExpandedResults(prev => ({ ...prev, [question]: true }));
    } catch (err) {
      setQueryResults(prev => ({
        ...prev,
        [question]: { loading: false, result: null, error: err.message }
      }));
    }
  };

  // Run all sample queries
  const runAllQueries = async () => {
    for (const sample of SAMPLE_QUESTIONS) {
      await testQuery(sample.query);
    }
  };

  // Toggle result expansion
  const toggleExpanded = (question) => {
    setExpandedResults(prev => ({ ...prev, [question]: !prev[question] }));
  };

  // Render status badge
  const StatusBadge = ({ status }) => {
    if (status.loading) {
      return (
        <span className="itp-status itp-status--loading">
          <Loader2 size={14} className="itp-spin" />
          Running...
        </span>
      );
    }
    if (status.error) {
      return (
        <span className="itp-status itp-status--error">
          <XCircle size={14} /> Error
        </span>
      );
    }
    if (status.result) {
      return (
        <span className="itp-status itp-status--success">
          <CheckCircle size={14} /> Complete
        </span>
      );
    }
    return <span className="itp-status">Not run</span>;
  };

  return (
    <div style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: 24 }}>
        <Link to="/admin" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--grass-green)', textDecoration: 'none', marginBottom: 16, fontSize: 14 }}>
          <ArrowLeft size={16} /> Back to Admin
        </Link>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 12 }}>
          <Brain size={28} style={{ color: 'var(--grass-green)' }} />
          Intelligence Pipeline Test
        </h1>
        <p style={{ margin: '8px 0 0', color: 'var(--text-secondary)' }}>
          Test MetadataReasoner and term resolution for project: <strong style={{ color: 'var(--grass-green)' }}>{projectId}</strong>
          {activeProject?.id && activeProject.id !== projectId && (
            <span style={{ marginLeft: 8, fontSize: 12 }}>
              (UUID: <code style={{ background: 'var(--bg-primary)', padding: '2px 6px', borderRadius: 3 }}>{activeProject.id}</code>)
            </span>
          )}
        </p>
      </div>

      {/* Warning if no project */}
      {!activeProject && (
        <div className="itp-alert itp-alert--warning" style={{ marginBottom: 24 }}>
          <AlertTriangle size={20} />
          <span>No project selected. Using default: <strong>TEA1000</strong>. Select a project from Projects page for different data.</span>
        </div>
      )}

      {/* Step 0: Diagnose Project */}
      <div className="itp-card" style={{ marginBottom: 16 }}>
        <div className="itp-card-header">
          <div className="itp-step">0</div>
          <div className="itp-step-info">
            <div className="itp-step-title">Diagnose Project</div>
            <div className="itp-step-desc">Check what data exists for this project identifier</div>
          </div>
          <StatusBadge status={diagnoseStatus} />
        </div>
        <button onClick={runDiagnose} disabled={diagnoseStatus.loading} className="btn btn-primary">
          {diagnoseStatus.loading ? <Loader2 size={16} className="itp-spin" /> : <Search size={16} />}
          {diagnoseStatus.loading ? 'Checking...' : 'Diagnose'}
        </button>
        {diagnoseStatus.error && <div className="itp-alert itp-alert--error" style={{ marginTop: 12 }}>{diagnoseStatus.error}</div>}
        {diagnoseStatus.result && (
          <div className="itp-result" style={{ marginTop: 12 }}>
            <div className="itp-result-item"><strong>Input project:</strong> <code>{diagnoseStatus.result.input_project}</code></div>
            
            {/* CRITICAL: Schema Metadata - This is where uploaded files live */}
            <div className="itp-result-item" style={{ background: '#f0f9ff', padding: 12, borderRadius: 8, marginTop: 8 }}>
              <strong style={{ color: '#0369a1' }}>📁 _schema_metadata (Uploaded Files):</strong>
              <div style={{ marginTop: 8 }}>
                <div><strong>Has project_id column:</strong> {diagnoseStatus.result.schema_metadata?.has_project_id_column ? '✅ Yes' : '❌ No'}</div>
                <div><strong>Files matching "{diagnoseStatus.result.input_project}":</strong> {diagnoseStatus.result.schema_metadata?.match_count || 0}</div>
                {diagnoseStatus.result.schema_metadata?.matching_files?.length > 0 && (
                  <div className="itp-result-detail" style={{ marginTop: 4 }}>
                    {diagnoseStatus.result.schema_metadata.matching_files.slice(0, 5).map((f, i) => (
                      <div key={i}>• {f.file_name} (project={f.project}, project_id={f.project_id || 'null'}, rows={f.row_count})</div>
                    ))}
                  </div>
                )}
                <div style={{ marginTop: 8, borderTop: '1px solid #e0e0e0', paddingTop: 8 }}>
                  <strong>ALL projects in DuckDB:</strong>
                  {diagnoseStatus.result.schema_metadata?.all_stored_projects?.length > 0 ? (
                    <div className="itp-result-detail">
                      {diagnoseStatus.result.schema_metadata.all_stored_projects.map((p, i) => (
                        <div key={i}>• project="{p.project}", project_id="{p.project_id || 'null'}" ({p.file_count} files)</div>
                      ))}
                    </div>
                  ) : (
                    <div className="itp-result-detail">No files in _schema_metadata</div>
                  )}
                </div>
              </div>
            </div>
            
            <div className="itp-result-item">
              <strong>Tables found:</strong> {diagnoseStatus.result.tables?.count || 0}
              {diagnoseStatus.result.tables?.names?.length > 0 && (
                <div className="itp-result-detail">{diagnoseStatus.result.tables.names.slice(0, 5).join(', ')}{diagnoseStatus.result.tables.names.length > 5 && '...'}</div>
              )}
            </div>
            <div className="itp-result-item">
              <strong>Classifications:</strong> {diagnoseStatus.result.classifications?.found?.length > 0 
                ? diagnoseStatus.result.classifications.found.map(c => `${c.project_name}: ${c.count}`).join(', ')
                : 'None found'}
              {diagnoseStatus.result.classifications?.all_project_names && (
                <div className="itp-result-detail">All project_names in DB: {diagnoseStatus.result.classifications.all_project_names.join(', ') || 'none'}</div>
              )}
            </div>
            <div className="itp-result-item">
              <strong>Term Index:</strong> {diagnoseStatus.result.term_index?.found?.length > 0 
                ? diagnoseStatus.result.term_index.found.map(t => `${t.project}: ${t.count}`).join(', ')
                : 'None found'}
              {diagnoseStatus.result.term_index?.all_projects && (
                <div className="itp-result-detail">All projects in term_index: {diagnoseStatus.result.term_index.all_projects.join(', ') || 'none'}</div>
              )}
            </div>
            <div className="itp-result-item">
              <strong>Column Profiles:</strong> {diagnoseStatus.result.column_profiles?.found?.length > 0 
                ? diagnoseStatus.result.column_profiles.found.map(p => `${p.project}: ${p.count}`).join(', ')
                : 'None found'}
              {diagnoseStatus.result.column_profiles?.all_projects && (
                <div className="itp-result-detail">All projects in profiles: {diagnoseStatus.result.column_profiles.all_projects.join(', ') || 'none'}</div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Step 1: Analyze */}
      <div className="itp-card" style={{ marginBottom: 16 }}>
        <div className="itp-card-header">
          <div className="itp-step">1</div>
          <div className="itp-step-info">
            <div className="itp-step-title">Run Analyze</div>
            <div className="itp-step-desc">Populates _intelligence_lookups, _table_classifications</div>
          </div>
          <StatusBadge status={analyzeStatus} />
        </div>
        <button onClick={runAnalyze} disabled={analyzeStatus.loading} className="btn btn-primary">
          {analyzeStatus.loading ? <Loader2 size={16} className="itp-spin" /> : <Database size={16} />}
          {analyzeStatus.loading ? 'Analyzing...' : 'Run Analyze'}
        </button>
        {analyzeStatus.error && <div className="itp-alert itp-alert--error" style={{ marginTop: 12 }}>{analyzeStatus.error}</div>}
        {analyzeStatus.result && (
          <div className="itp-result itp-result--code" style={{ marginTop: 12 }}>
            <pre>{JSON.stringify(analyzeStatus.result, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Step 2: Recalc */}
      <div className="itp-card" style={{ marginBottom: 16 }}>
        <div className="itp-card-header">
          <div className="itp-step">2</div>
          <div className="itp-step-info">
            <div className="itp-step-title">Run Recalc</div>
            <div className="itp-step-desc">Builds _term_index, _entity_tables, join_priority</div>
          </div>
          <StatusBadge status={recalcStatus} />
        </div>
        <button onClick={runRecalc} disabled={recalcStatus.loading} className="btn btn-primary">
          {recalcStatus.loading ? <Loader2 size={16} className="itp-spin" /> : <RefreshCw size={16} />}
          {recalcStatus.loading ? 'Recalculating...' : 'Run Recalc'}
        </button>
        {recalcStatus.error && <div className="itp-alert itp-alert--error" style={{ marginTop: 12 }}>{recalcStatus.error}</div>}
        {recalcStatus.result && (
          <div className="itp-result itp-result--code" style={{ marginTop: 12 }}>
            <pre>{JSON.stringify(recalcStatus.result, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Step 3: Test 5 Engines */}
      <div className="itp-card" style={{ marginBottom: 16 }}>
        <div className="itp-card-header">
          <div className="itp-step">3</div>
          <div className="itp-step-info">
            <div className="itp-step-title">Test 5 Engines</div>
            <div className="itp-step-desc">Aggregate, Compare, Validate, Detect, Map</div>
          </div>
          <StatusBadge status={enginesStatus} />
        </div>
        
        <button onClick={runEnginesQuickTest} disabled={enginesStatus.loading} className="btn btn-primary" style={{ marginBottom: 16 }}>
          {enginesStatus.loading ? <Loader2 size={16} className="itp-spin" /> : <Zap size={16} />}
          {enginesStatus.loading ? 'Testing...' : 'Quick Test All Engines'}
        </button>
        
        {/* Quick Test Results */}
        {enginesStatus.result && (
          <div style={{ marginBottom: 16 }}>
            {enginesStatus.result.error && (
              <div className="itp-alert itp-alert--error" style={{ marginBottom: 12 }}>
                <strong>Error:</strong> {enginesStatus.result.error}
                {enginesStatus.result.traceback && (
                  <pre style={{ marginTop: 8, fontSize: 11, whiteSpace: 'pre-wrap', opacity: 0.8 }}>{enginesStatus.result.traceback}</pre>
                )}
              </div>
            )}
            
            <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>
              {enginesStatus.result.summary || 'No summary available'}
            </div>
            
            {enginesStatus.result.test_table && (
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
                Test table: <code>{enginesStatus.result.test_table}</code>
              </div>
            )}
            
            {enginesStatus.result.results && Object.keys(enginesStatus.result.results).length > 0 ? (
              <div className="itp-engines">
                {Object.entries(enginesStatus.result.results).map(([engine, result]) => (
                  <div key={engine} className={`itp-engine itp-engine--${result.status}`}>
                    <div className="itp-engine-name">
                      {result.status === 'pass' && <CheckCircle size={12} />}
                      {result.status === 'error' && <XCircle size={12} />}
                      {result.status === 'skip' && <AlertTriangle size={12} />}
                      {engine}
                    </div>
                    <div className="itp-engine-msg">{result.message}</div>
                  </div>
                ))}
              </div>
            ) : !enginesStatus.result.error && (
              <div className="itp-alert itp-alert--warning">
                No engine results returned. Make sure the <code>backend/engines/</code> folder is deployed.
              </div>
            )}
          </div>
        )}
        
        {enginesStatus.error && (
          <div className="itp-alert itp-alert--error" style={{ marginBottom: 16 }}>{enginesStatus.error}</div>
        )}
        
        {/* Individual Engine Test */}
        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)' }}>Test Individual Engine</div>
          
          <div className="itp-engine-btns">
            {['aggregate', 'compare', 'validate', 'detect', 'map'].map(eng => (
              <button
                key={eng}
                onClick={() => handleEngineChange(eng)}
                className={`itp-engine-btn ${selectedEngine === eng ? 'itp-engine-btn--active' : ''}`}
              >
                {eng}
              </button>
            ))}
          </div>
          
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Config (JSON)</label>
            <textarea
              value={engineConfig}
              onChange={(e) => setEngineConfig(e.target.value)}
              placeholder="Enter engine config as JSON..."
              className="itp-textarea"
            />
          </div>
          
          <button onClick={runEngineTest} disabled={engineTestResult.loading || !engineConfig} className="btn btn-primary">
            {engineTestResult.loading ? <Loader2 size={14} className="itp-spin" /> : <Play size={14} />}
            Run {selectedEngine.charAt(0).toUpperCase() + selectedEngine.slice(1)} Engine
          </button>
          
          {engineTestResult.error && (
            <div className="itp-alert itp-alert--error" style={{ marginTop: 12 }}>{engineTestResult.error}</div>
          )}
          
          {engineTestResult.result && (
            <div className="itp-result" style={{ marginTop: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingBottom: 8, borderBottom: '1px solid var(--border-color)', marginBottom: 8 }}>
                {engineTestResult.result.result?.status === 'success' ? (
                  <CheckCircle size={16} style={{ color: 'var(--grass-green)' }} />
                ) : (
                  <AlertTriangle size={16} style={{ color: 'var(--warning)' }} />
                )}
                <span style={{ fontWeight: 600 }}>{engineTestResult.result.result?.status?.toUpperCase()}</span>
                <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-secondary)' }}>
                  {engineTestResult.result.result?.row_count} rows
                </span>
              </div>
              
              {engineTestResult.result.result?.summary && (
                <div className="itp-result-item">{engineTestResult.result.result.summary}</div>
              )}
              
              {engineTestResult.result.result?.sql && (
                <div className="itp-result-item">
                  <div className="itp-result-label">SQL</div>
                  <pre className="itp-code">{engineTestResult.result.result.sql}</pre>
                </div>
              )}
              
              {engineTestResult.result.result?.findings?.length > 0 && (
                <div className="itp-result-item">
                  <div className="itp-result-label">FINDINGS ({engineTestResult.result.result.findings.length})</div>
                  {engineTestResult.result.result.findings.map((f, i) => (
                    <div key={i} className={`itp-finding itp-finding--${f.severity}`}>
                      <div style={{ fontWeight: 600, fontSize: 12 }}>{f.finding_type}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{f.message}</div>
                    </div>
                  ))}
                </div>
              )}
              
              {engineTestResult.result.result?.data?.length > 0 && (
                <div className="itp-result-item">
                  <div className="itp-result-label">DATA (first {Math.min(5, engineTestResult.result.result.data.length)} rows)</div>
                  <pre className="itp-code">{JSON.stringify(engineTestResult.result.result.data.slice(0, 5), null, 2)}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Step 4: Test Queries */}
      <div className="itp-card">
        <div className="itp-card-header">
          <div className="itp-step">4</div>
          <div className="itp-step-info">
            <div className="itp-step-title">Test Query Resolution</div>
            <div className="itp-step-desc">Test term_index + MetadataReasoner + SQLAssembler</div>
          </div>
          <button onClick={runAllQueries} className="btn btn-primary" style={{ padding: '6px 12px', fontSize: 13 }}>
            <Zap size={14} /> Run All Tests
          </button>
        </div>

        {/* Custom query input */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <input
            type="text"
            value={customQuery}
            onChange={(e) => setCustomQuery(e.target.value)}
            placeholder="Enter custom query to test..."
            className="itp-input"
            onKeyDown={(e) => e.key === 'Enter' && customQuery && testQuery(customQuery)}
          />
          <button onClick={() => customQuery && testQuery(customQuery)} disabled={!customQuery} className="btn btn-primary">
            <Search size={14} /> Test
          </button>
        </div>

        {/* Sample queries */}
        <div className="itp-queries">
          {SAMPLE_QUESTIONS.map((sample, idx) => {
            const status = queryResults[sample.query] || {};
            return (
              <div key={idx} className="itp-query">
                <div 
                  className="itp-query-header"
                  onClick={() => status.result && toggleExpanded(sample.query)}
                  style={{ cursor: status.result ? 'pointer' : 'default' }}
                >
                  {status.result ? (
                    expandedResults[sample.query] ? <ChevronDown size={16} /> : <ChevronRight size={16} />
                  ) : (
                    <div style={{ width: 16 }} />
                  )}
                  <div style={{ flex: 1 }}>
                    <code style={{ fontSize: 14, color: 'var(--grass-green)' }}>{sample.query}</code>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{sample.description}</div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); testQuery(sample.query); }}
                    disabled={status.loading}
                    className="btn"
                    style={{ padding: '4px 8px' }}
                  >
                    {status.loading ? <Loader2 size={12} className="itp-spin" /> : <Play size={12} />}
                  </button>
                  <StatusBadge status={status} />
                </div>
                
                {expandedResults[sample.query] && status.result && (
                  <div style={{ padding: '0 12px 12px 40px' }}>
                    {status.result.term_matches && (
                      <div className="itp-result-item">
                        <div className="itp-result-label">TERM MATCHES ({status.result.term_matches.length})</div>
                        {status.result.term_matches.map((match, i) => (
                          <div key={i} className="itp-match">
                            <span style={{ color: 'var(--grass-green)', fontWeight: 600 }}>{match.term}</span>
                            <span style={{ color: 'var(--text-secondary)' }}>→</span>
                            <span style={{ color: 'var(--warning)' }}>{match.table}</span>
                            <span style={{ color: 'var(--text-secondary)' }}>.</span>
                            <span style={{ color: 'var(--accent)' }}>{match.column}</span>
                            <span style={{ color: 'var(--text-secondary)' }}>{match.operator}</span>
                            <span>'{match.match_value}'</span>
                            <span className={`itp-match-src itp-match-src--${match.source || 'term_index'}`}>
                              {match.source || 'term_index'}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {status.result.assembly?.sql && (
                      <div className="itp-result-item">
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                          <div className="itp-result-label">GENERATED SQL</div>
                          <button onClick={() => copyToClipboard(status.result.assembly.sql)} className="btn" style={{ padding: '2px 8px', fontSize: 11 }}>
                            {copiedText === status.result.assembly.sql ? <Check size={10} /> : <Copy size={10} />}
                            {copiedText === status.result.assembly.sql ? 'Copied!' : 'Copy'}
                          </button>
                        </div>
                        <pre className="itp-code">{status.result.assembly.sql}</pre>
                      </div>
                    )}

                    {status.result.execution && (
                      <div className="itp-result-item">
                        <div className="itp-result-label">EXECUTION ({status.result.execution.row_count} rows)</div>
                        <pre className="itp-code" style={{ maxHeight: 150 }}>
                          {JSON.stringify(status.result.execution.sample_rows || status.result.execution, null, 2)}
                        </pre>
                      </div>
                    )}

                    {status.result.error && (
                      <div className="itp-alert itp-alert--error">{status.result.error}</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Scoped styles */}
      <style>{`
        .itp-spin { animation: itp-spin 1s linear infinite; }
        @keyframes itp-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        
        .itp-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; }
        .itp-card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
        
        .itp-step { width: 32px; height: 32px; border-radius: 50%; background: var(--grass-green); color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px; flex-shrink: 0; }
        .itp-step-info { flex: 1; }
        .itp-step-title { font-weight: 600; font-size: 16px; color: var(--text-primary); }
        .itp-step-desc { font-size: 13px; color: var(--text-secondary); }
        
        .itp-status { display: flex; align-items: center; gap: 4px; font-size: 13px; color: var(--text-secondary); }
        .itp-status--loading { color: var(--warning); }
        .itp-status--error { color: var(--error); }
        .itp-status--success { color: var(--grass-green); }
        
        .itp-alert { display: flex; align-items: flex-start; gap: 8px; padding: 12px; border-radius: 6px; font-size: 13px; }
        .itp-alert--warning { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); color: #b45309; }
        .itp-alert--error { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #dc2626; }
        
        .itp-result { background: var(--bg-primary); border-radius: 6px; padding: 12px; }
        .itp-result--code pre { margin: 0; font-size: 12px; white-space: pre-wrap; max-height: 150px; overflow: auto; }
        .itp-result-item { margin-bottom: 8px; font-size: 13px; }
        .itp-result-item:last-child { margin-bottom: 0; }
        .itp-result-detail { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }
        .itp-result-label { font-size: 11px; color: var(--text-secondary); font-weight: 600; margin-bottom: 4px; text-transform: uppercase; }
        
        .itp-code { margin: 0; padding: 8px; background: rgba(0,0,0,0.03); border-radius: 4px; font-size: 12px; overflow: auto; white-space: pre-wrap; }
        
        .itp-engines { display: flex; flex-wrap: wrap; gap: 8px; }
        .itp-engine { padding: 8px 12px; border-radius: 6px; font-size: 13px; }
        .itp-engine--pass { background: rgba(131, 177, 109, 0.15); border: 1px solid rgba(131, 177, 109, 0.3); }
        .itp-engine--error { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); }
        .itp-engine--skip { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); }
        .itp-engine-name { font-weight: 600; text-transform: uppercase; display: flex; align-items: center; gap: 4px; margin-bottom: 2px; }
        .itp-engine--pass .itp-engine-name { color: var(--grass-green); }
        .itp-engine--error .itp-engine-name { color: #dc2626; }
        .itp-engine--skip .itp-engine-name { color: #b45309; }
        .itp-engine-msg { font-size: 11px; color: var(--text-secondary); }
        
        .itp-engine-btns { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
        .itp-engine-btn { padding: 6px 12px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 4px; font-size: 12px; font-weight: 500; text-transform: uppercase; cursor: pointer; color: var(--text-secondary); }
        .itp-engine-btn--active { background: var(--grass-green); border-color: var(--grass-green); color: white; }
        
        .itp-textarea { width: 100%; min-height: 120px; padding: 12px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; font-size: 13px; font-family: monospace; resize: vertical; color: var(--text-primary); }
        
        .itp-input { flex: 1; padding: 10px 12px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; font-size: 14px; color: var(--text-primary); }
        .itp-input:focus { outline: none; border-color: var(--grass-green); }
        
        .itp-queries { display: flex; flex-direction: column; gap: 8px; }
        .itp-query { background: var(--bg-primary); border-radius: 6px; overflow: hidden; }
        .itp-query-header { display: flex; align-items: center; gap: 12px; padding: 12px; }
        
        .itp-match { display: flex; align-items: center; gap: 6px; padding: 6px 8px; background: var(--bg-secondary); border-radius: 4px; margin-bottom: 4px; font-size: 12px; flex-wrap: wrap; }
        .itp-match-src { margin-left: auto; padding: 1px 6px; border-radius: 3px; font-size: 10px; }
        .itp-match-src--term_index { background: rgba(131, 177, 109, 0.2); color: var(--grass-green); }
        .itp-match-src--reasoned { background: rgba(245, 158, 11, 0.2); color: #b45309; }
        
        .itp-finding { padding: 8px; border-radius: 4px; margin-bottom: 4px; }
        .itp-finding--error { background: rgba(239, 68, 68, 0.1); }
        .itp-finding--warning { background: rgba(245, 158, 11, 0.1); }
      `}</style>
    </div>
  );
}
