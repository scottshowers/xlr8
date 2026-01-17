/**
 * IntelligenceTestPage.jsx
 * ========================
 * 
 * Interactive test page for the Intelligence Pipeline
 * - Run Analyze (populates _intelligence_lookups)
 * - Run Recalc (builds term index)
 * - Test query resolution with sample questions
 * 
 * Route: /admin/intelligence-test
 * Created: January 11, 2026
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

// Color scheme matching your app
const colors = {
  background: 'transparent',
  cardBg: 'rgba(255, 255, 255, 0.02)',
  border: 'rgba(255, 255, 255, 0.1)',
  text: '#e4e4e7',
  textMuted: '#71717a',
  primary: '#6366f1',
  accent: '#22c55e',
  warning: '#f59e0b',
  danger: '#ef4444',
};

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
  const projectId = activeProject?.name || 'TEA1000';
  
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
      const response = await fetch(`${API_BASE}/api/projects/${projectId}/recalc`, {
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

  // Test a query
  const testQuery = async (question) => {
    setQueryResults(prev => ({
      ...prev,
      [question]: { loading: true, result: null, error: null }
    }));
    try {
      const response = await fetch(
        `${API_BASE}/api/projects/${projectId}/resolve-terms?question=${encodeURIComponent(question)}`,
        { method: 'POST' }
      );
      const data = await response.json();
      setQueryResults(prev => ({
        ...prev,
        [question]: { loading: false, result: data, error: null }
      }));
      // Auto-expand results
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

  // Toggle result expansion
  const toggleExpanded = (question) => {
    setExpandedResults(prev => ({ ...prev, [question]: !prev[question] }));
  };

  // Render status badge
  const StatusBadge = ({ status }) => {
    if (status.loading) {
      return (
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: colors.warning }}>
          <Loader2 size={14} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
          Running...
        </span>
      );
    }
    if (status.error) {
      return (
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: colors.danger }}>
          <XCircle size={14} /> Error
        </span>
      );
    }
    if (status.result) {
      return (
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: colors.accent }}>
          <CheckCircle size={14} /> Complete
        </span>
      );
    }
    return <span style={{ color: colors.textMuted }}>Not run</span>;
  };

  return (
    <div style={{ minHeight: '100vh', background: colors.background, padding: '1.5rem', color: colors.text }}>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <Link to="/admin" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: colors.primary, textDecoration: 'none', marginBottom: '1rem' }}>
          <ArrowLeft size={16} /> Back to Admin
        </Link>
        <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Brain size={28} color={colors.primary} />
          Intelligence Pipeline Test
        </h1>
        <p style={{ margin: '0.5rem 0 0', color: colors.textMuted }}>
          Test MetadataReasoner and term resolution for project: <strong style={{ color: colors.primary }}>{projectId}</strong>
          {activeProject?.id && activeProject.id !== projectId && (
            <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem' }}>
              (UUID: <code style={{ color: colors.warning }}>{activeProject.id}</code>)
            </span>
          )}
        </p>
      </div>

      {/* Warning if no project */}
      {!activeProject && (
        <div style={{ 
          padding: '1rem', 
          background: `${colors.warning}15`, 
          border: `1px solid ${colors.warning}40`,
          borderRadius: 8, 
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <AlertTriangle size={20} color={colors.warning} />
          <span>No project selected. Using default: <strong>TEA1000</strong>. Select a project from Projects page for different data.</span>
        </div>
      )}

      {/* Step 0: Diagnose Project */}
      <div style={{ background: colors.cardBg, border: `1px solid ${colors.border}`, borderRadius: 10, padding: '1.25rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: colors.warning, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, color: '#000' }}>0</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '1rem' }}>Diagnose Project</div>
              <div style={{ fontSize: '0.8rem', color: colors.textMuted }}>Check what data exists for this project identifier</div>
            </div>
          </div>
          <StatusBadge status={diagnoseStatus} />
        </div>
        <button
          onClick={runDiagnose}
          disabled={diagnoseStatus.loading}
          style={{
            padding: '0.6rem 1.25rem',
            background: diagnoseStatus.loading ? colors.border : colors.warning,
            color: '#000',
            border: 'none',
            borderRadius: 6,
            cursor: diagnoseStatus.loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.9rem',
            fontWeight: 600
          }}
        >
          {diagnoseStatus.loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Search size={16} />}
          {diagnoseStatus.loading ? 'Checking...' : 'Diagnose'}
        </button>
        {diagnoseStatus.error && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: `${colors.danger}15`, borderRadius: 6, fontSize: '0.85rem', color: colors.danger }}>
            {diagnoseStatus.error}
          </div>
        )}
        {diagnoseStatus.result && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'rgba(0,0,0,0.2)', borderRadius: 6 }}>
            <div style={{ fontSize: '0.8rem', marginBottom: '0.5rem' }}>
              <strong>Input project:</strong> <code>{diagnoseStatus.result.input_project}</code>
            </div>
            
            {/* Tables */}
            <div style={{ fontSize: '0.8rem', marginBottom: '0.5rem', padding: '0.5rem', background: 'rgba(255,255,255,0.05)', borderRadius: 4 }}>
              <strong>Tables found:</strong> {diagnoseStatus.result.tables?.count || 0}
              {diagnoseStatus.result.tables?.names?.length > 0 && (
                <div style={{ fontSize: '0.7rem', color: colors.textMuted, marginTop: '0.25rem' }}>
                  {diagnoseStatus.result.tables.names.slice(0, 5).join(', ')}
                  {diagnoseStatus.result.tables.names.length > 5 && '...'}
                </div>
              )}
            </div>
            
            {/* Classifications */}
            <div style={{ fontSize: '0.8rem', marginBottom: '0.5rem', padding: '0.5rem', background: 'rgba(255,255,255,0.05)', borderRadius: 4 }}>
              <strong>Classifications:</strong> {diagnoseStatus.result.classifications?.found?.length > 0 
                ? diagnoseStatus.result.classifications.found.map(c => `${c.project_name}: ${c.count}`).join(', ')
                : 'None found'}
              {diagnoseStatus.result.classifications?.all_project_names && (
                <div style={{ fontSize: '0.7rem', color: colors.textMuted, marginTop: '0.25rem' }}>
                  All project_names in DB: {diagnoseStatus.result.classifications.all_project_names.join(', ') || 'none'}
                </div>
              )}
            </div>
            
            {/* Term Index */}
            <div style={{ fontSize: '0.8rem', marginBottom: '0.5rem', padding: '0.5rem', background: 'rgba(255,255,255,0.05)', borderRadius: 4 }}>
              <strong>Term Index:</strong> {diagnoseStatus.result.term_index?.found?.length > 0 
                ? diagnoseStatus.result.term_index.found.map(t => `${t.project}: ${t.count}`).join(', ')
                : 'None found'}
              {diagnoseStatus.result.term_index?.all_projects && (
                <div style={{ fontSize: '0.7rem', color: colors.textMuted, marginTop: '0.25rem' }}>
                  All projects in term_index: {diagnoseStatus.result.term_index.all_projects.join(', ') || 'none'}
                </div>
              )}
            </div>
            
            {/* Column Profiles */}
            <div style={{ fontSize: '0.8rem', padding: '0.5rem', background: 'rgba(255,255,255,0.05)', borderRadius: 4 }}>
              <strong>Column Profiles:</strong> {diagnoseStatus.result.column_profiles?.found?.length > 0 
                ? diagnoseStatus.result.column_profiles.found.map(p => `${p.project}: ${p.count}`).join(', ')
                : 'None found'}
              {diagnoseStatus.result.column_profiles?.all_projects && (
                <div style={{ fontSize: '0.7rem', color: colors.textMuted, marginTop: '0.25rem' }}>
                  All projects in profiles: {diagnoseStatus.result.column_profiles.all_projects.join(', ') || 'none'}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Step 1: Analyze */}
      <div style={{ background: colors.cardBg, border: `1px solid ${colors.border}`, borderRadius: 10, padding: '1.25rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: colors.primary, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600 }}>1</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '1rem' }}>Run Analyze</div>
              <div style={{ fontSize: '0.8rem', color: colors.textMuted }}>Populates _intelligence_lookups, _table_classifications</div>
            </div>
          </div>
          <StatusBadge status={analyzeStatus} />
        </div>
        <button
          onClick={runAnalyze}
          disabled={analyzeStatus.loading}
          style={{
            padding: '0.6rem 1.25rem',
            background: analyzeStatus.loading ? colors.border : colors.primary,
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: analyzeStatus.loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.9rem',
            fontWeight: 500
          }}
        >
          {analyzeStatus.loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Database size={16} />}
          {analyzeStatus.loading ? 'Analyzing...' : 'Run Analyze'}
        </button>
        {analyzeStatus.error && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: `${colors.danger}15`, borderRadius: 6, fontSize: '0.85rem', color: colors.danger }}>
            {analyzeStatus.error}
          </div>
        )}
        {analyzeStatus.result && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: colors.background, borderRadius: 6, fontSize: '0.8rem', fontFamily: 'monospace', maxHeight: 150, overflow: 'auto' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(analyzeStatus.result, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Step 2: Recalc */}
      <div style={{ background: colors.cardBg, border: `1px solid ${colors.border}`, borderRadius: 10, padding: '1.25rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: colors.primary, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600 }}>2</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '1rem' }}>Run Recalc</div>
              <div style={{ fontSize: '0.8rem', color: colors.textMuted }}>Builds _term_index, _entity_tables, join_priority</div>
            </div>
          </div>
          <StatusBadge status={recalcStatus} />
        </div>
        <button
          onClick={runRecalc}
          disabled={recalcStatus.loading}
          style={{
            padding: '0.6rem 1.25rem',
            background: recalcStatus.loading ? colors.border : colors.primary,
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: recalcStatus.loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.9rem',
            fontWeight: 500
          }}
        >
          {recalcStatus.loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <RefreshCw size={16} />}
          {recalcStatus.loading ? 'Recalculating...' : 'Run Recalc'}
        </button>
        {recalcStatus.error && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: `${colors.danger}15`, borderRadius: 6, fontSize: '0.85rem', color: colors.danger }}>
            {recalcStatus.error}
          </div>
        )}
        {recalcStatus.result && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: colors.background, borderRadius: 6, fontSize: '0.8rem', fontFamily: 'monospace', maxHeight: 150, overflow: 'auto' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(recalcStatus.result, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Step 3: Test 5 Engines */}
      <div style={{ background: colors.cardBg, border: `1px solid ${colors.border}`, borderRadius: 10, padding: '1.25rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: colors.accent, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, color: '#000' }}>3</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '1rem' }}>Test 5 Engines</div>
              <div style={{ fontSize: '0.8rem', color: colors.textMuted }}>Aggregate, Compare, Validate, Detect, Map</div>
            </div>
          </div>
          <StatusBadge status={enginesStatus} />
        </div>
        
        {/* Quick Test Button */}
        <button
          onClick={runEnginesQuickTest}
          disabled={enginesStatus.loading}
          style={{
            padding: '0.6rem 1.25rem',
            background: enginesStatus.loading ? colors.border : colors.accent,
            color: '#000',
            border: 'none',
            borderRadius: 6,
            cursor: enginesStatus.loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.9rem',
            fontWeight: 600,
            marginBottom: '1rem'
          }}
        >
          {enginesStatus.loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Zap size={16} />}
          {enginesStatus.loading ? 'Testing...' : 'Quick Test All Engines'}
        </button>
        
        {/* Quick Test Results */}
        {enginesStatus.result && (
          <div style={{ marginBottom: '1rem' }}>
            {/* Show error if present */}
            {enginesStatus.result.error && (
              <div style={{ 
                padding: '0.75rem', 
                background: `${colors.danger}15`, 
                border: `1px solid ${colors.danger}40`,
                borderRadius: 6, 
                marginBottom: '0.75rem',
                fontSize: '0.85rem', 
                color: colors.danger 
              }}>
                <strong>Error:</strong> {enginesStatus.result.error}
                {enginesStatus.result.traceback && (
                  <pre style={{ marginTop: '0.5rem', fontSize: '0.7rem', whiteSpace: 'pre-wrap', opacity: 0.8 }}>
                    {enginesStatus.result.traceback}
                  </pre>
                )}
              </div>
            )}
            
            {/* Summary */}
            <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem', color: colors.text }}>
              {enginesStatus.result.summary || 'No summary available'}
            </div>
            
            {/* Test table info */}
            {enginesStatus.result.test_table && (
              <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.5rem' }}>
                Test table: <code>{enginesStatus.result.test_table}</code>
              </div>
            )}
            
            {/* Results grid */}
            {enginesStatus.result.results && Object.keys(enginesStatus.result.results).length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {Object.entries(enginesStatus.result.results).map(([engine, result]) => (
                <div 
                  key={engine}
                  style={{
                    padding: '0.5rem 0.75rem',
                    borderRadius: 6,
                    background: result.status === 'pass' ? `${colors.accent}20` : 
                               result.status === 'error' ? `${colors.danger}20` : 
                               `${colors.warning}20`,
                    border: `1px solid ${result.status === 'pass' ? colors.accent : 
                                        result.status === 'error' ? colors.danger : colors.warning}40`,
                    fontSize: '0.8rem'
                  }}
                >
                  <div style={{ fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                    {result.status === 'pass' && <CheckCircle size={12} style={{ marginRight: 4, color: colors.accent }} />}
                    {result.status === 'error' && <XCircle size={12} style={{ marginRight: 4, color: colors.danger }} />}
                    {result.status === 'skip' && <AlertTriangle size={12} style={{ marginRight: 4, color: colors.warning }} />}
                    {engine}
                  </div>
                  <div style={{ color: colors.textMuted, fontSize: '0.75rem' }}>{result.message}</div>
                </div>
              ))}
              </div>
            ) : (
              <div style={{ 
                padding: '0.75rem', 
                background: `${colors.warning}15`, 
                borderRadius: 6, 
                fontSize: '0.85rem', 
                color: colors.warning 
              }}>
                No engine results returned. Make sure the <code>backend/engines/</code> folder is deployed.
              </div>
            )}
          </div>
        )}
        
        {enginesStatus.error && (
          <div style={{ marginBottom: '1rem', padding: '0.75rem', background: `${colors.danger}15`, borderRadius: 6, fontSize: '0.85rem', color: colors.danger }}>
            {enginesStatus.error}
          </div>
        )}
        
        {/* Individual Engine Test */}
        <div style={{ borderTop: `1px solid ${colors.border}`, paddingTop: '1rem' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem' }}>Test Individual Engine</div>
          
          {/* Engine Selector */}
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
            {['aggregate', 'compare', 'validate', 'detect', 'map'].map(eng => (
              <button
                key={eng}
                onClick={() => handleEngineChange(eng)}
                style={{
                  padding: '0.4rem 0.75rem',
                  background: selectedEngine === eng ? colors.primary : colors.border,
                  color: selectedEngine === eng ? '#fff' : colors.textMuted,
                  border: 'none',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  fontWeight: 500,
                  textTransform: 'uppercase'
                }}
              >
                {eng}
              </button>
            ))}
          </div>
          
          {/* Config Editor */}
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ fontSize: '0.75rem', color: colors.textMuted, display: 'block', marginBottom: '0.35rem' }}>
              Config (JSON)
            </label>
            <textarea
              value={engineConfig}
              onChange={(e) => setEngineConfig(e.target.value)}
              placeholder="Enter engine config as JSON..."
              style={{
                width: '100%',
                minHeight: 120,
                padding: '0.75rem',
                background: colors.background,
                border: `1px solid ${colors.border}`,
                borderRadius: 6,
                color: colors.text,
                fontSize: '0.8rem',
                fontFamily: 'monospace',
                resize: 'vertical'
              }}
            />
          </div>
          
          {/* Run Button */}
          <button
            onClick={runEngineTest}
            disabled={engineTestResult.loading || !engineConfig}
            style={{
              padding: '0.5rem 1rem',
              background: engineTestResult.loading ? colors.border : colors.primary,
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: engineTestResult.loading || !engineConfig ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
              fontWeight: 500
            }}
          >
            {engineTestResult.loading ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Play size={14} />}
            Run {selectedEngine.charAt(0).toUpperCase() + selectedEngine.slice(1)} Engine
          </button>
          
          {/* Engine Test Result */}
          {engineTestResult.error && (
            <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: `${colors.danger}15`, borderRadius: 6, fontSize: '0.85rem', color: colors.danger }}>
              {engineTestResult.error}
            </div>
          )}
          
          {engineTestResult.result && (
            <div style={{ marginTop: '0.75rem', background: colors.background, borderRadius: 6, overflow: 'hidden' }}>
              {/* Status Header */}
              <div style={{ 
                padding: '0.75rem', 
                borderBottom: `1px solid ${colors.border}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {engineTestResult.result.result?.status === 'success' ? (
                    <CheckCircle size={16} color={colors.accent} />
                  ) : (
                    <AlertTriangle size={16} color={colors.warning} />
                  )}
                  <span style={{ fontWeight: 600 }}>
                    {engineTestResult.result.result?.status?.toUpperCase()}
                  </span>
                </div>
                <span style={{ fontSize: '0.8rem', color: colors.textMuted }}>
                  {engineTestResult.result.result?.row_count} rows
                </span>
              </div>
              
              {/* Summary */}
              {engineTestResult.result.result?.summary && (
                <div style={{ padding: '0.5rem 0.75rem', borderBottom: `1px solid ${colors.border}`, fontSize: '0.85rem' }}>
                  {engineTestResult.result.result.summary}
                </div>
              )}
              
              {/* SQL */}
              {engineTestResult.result.result?.sql && (
                <div style={{ padding: '0.75rem', borderBottom: `1px solid ${colors.border}` }}>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.35rem', fontWeight: 600 }}>SQL</div>
                  <pre style={{ 
                    margin: 0, 
                    padding: '0.5rem', 
                    background: '#1a1a2e', 
                    borderRadius: 4, 
                    fontSize: '0.75rem', 
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                    maxHeight: 100
                  }}>
                    {engineTestResult.result.result.sql}
                  </pre>
                </div>
              )}
              
              {/* Findings */}
              {engineTestResult.result.result?.findings?.length > 0 && (
                <div style={{ padding: '0.75rem', borderBottom: `1px solid ${colors.border}` }}>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.35rem', fontWeight: 600 }}>
                    FINDINGS ({engineTestResult.result.result.findings.length})
                  </div>
                  {engineTestResult.result.result.findings.map((f, i) => (
                    <div key={i} style={{ 
                      padding: '0.5rem', 
                      background: f.severity === 'error' ? `${colors.danger}15` : `${colors.warning}15`,
                      borderRadius: 4,
                      marginBottom: '0.25rem',
                      fontSize: '0.8rem'
                    }}>
                      <div style={{ fontWeight: 600 }}>{f.finding_type}</div>
                      <div style={{ color: colors.textMuted }}>{f.message}</div>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Data Preview */}
              {engineTestResult.result.result?.data?.length > 0 && (
                <div style={{ padding: '0.75rem' }}>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.35rem', fontWeight: 600 }}>
                    DATA (first {Math.min(5, engineTestResult.result.result.data.length)} rows)
                  </div>
                  <pre style={{ 
                    margin: 0, 
                    padding: '0.5rem', 
                    background: '#1a1a2e', 
                    borderRadius: 4, 
                    fontSize: '0.7rem', 
                    overflow: 'auto',
                    maxHeight: 150
                  }}>
                    {JSON.stringify(engineTestResult.result.result.data.slice(0, 5), null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Step 4: Test Queries */}
      <div style={{ background: colors.cardBg, border: `1px solid ${colors.border}`, borderRadius: 10, padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: colors.primary, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600 }}>4</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '1rem' }}>Test Query Resolution</div>
              <div style={{ fontSize: '0.8rem', color: colors.textMuted }}>Test term_index + MetadataReasoner + SQLAssembler</div>
            </div>
          </div>
          <button
            onClick={runAllQueries}
            style={{
              padding: '0.5rem 1rem',
              background: colors.accent,
              color: '#000',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
              fontWeight: 600
            }}
          >
            <Zap size={14} /> Run All Tests
          </button>
        </div>

        {/* Custom query input */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <input
            type="text"
            value={customQuery}
            onChange={(e) => setCustomQuery(e.target.value)}
            placeholder="Enter custom query..."
            style={{
              flex: 1,
              padding: '0.6rem 1rem',
              background: colors.background,
              border: `1px solid ${colors.border}`,
              borderRadius: 6,
              color: colors.text,
              fontSize: '0.9rem'
            }}
            onKeyDown={(e) => e.key === 'Enter' && customQuery && testQuery(customQuery)}
          />
          <button
            onClick={() => customQuery && testQuery(customQuery)}
            disabled={!customQuery}
            style={{
              padding: '0.6rem 1rem',
              background: customQuery ? colors.primary : colors.border,
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: customQuery ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <Search size={16} /> Test
          </button>
        </div>

        {/* Sample queries */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {SAMPLE_QUESTIONS.map((sample, idx) => {
            const status = queryResults[sample.query] || {};
            const isExpanded = expandedResults[sample.query];
            
            return (
              <div key={idx} style={{ background: colors.background, borderRadius: 8, overflow: 'hidden' }}>
                {/* Query row */}
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '0.75rem', 
                  padding: '0.75rem 1rem',
                  cursor: status.result ? 'pointer' : 'default'
                }}
                onClick={() => status.result && toggleExpanded(sample.query)}
                >
                  {status.result ? (
                    isExpanded ? <ChevronDown size={16} color={colors.textMuted} /> : <ChevronRight size={16} color={colors.textMuted} />
                  ) : (
                    <div style={{ width: 16 }} />
                  )}
                  <div style={{ flex: 1 }}>
                    <code style={{ fontSize: '0.85rem', color: colors.text }}>{sample.query}</code>
                    <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>{sample.description}</div>
                  </div>
                  <StatusBadge status={status} />
                  <button
                    onClick={(e) => { e.stopPropagation(); testQuery(sample.query); }}
                    disabled={status.loading}
                    style={{
                      padding: '0.4rem 0.75rem',
                      background: status.loading ? colors.border : colors.primary,
                      color: '#fff',
                      border: 'none',
                      borderRadius: 4,
                      cursor: status.loading ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      fontSize: '0.8rem'
                    }}
                  >
                    {status.loading ? <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> : <Play size={12} />}
                    Run
                  </button>
                </div>

                {/* Expanded results */}
                {isExpanded && status.result && (
                  <div style={{ padding: '0 1rem 1rem 2.75rem' }}>
                    {/* Term matches */}
                    {status.result.term_matches && (
                      <div style={{ marginBottom: '0.75rem' }}>
                        <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.35rem', fontWeight: 600 }}>
                          TERM MATCHES ({status.result.term_matches.length})
                        </div>
                        {status.result.term_matches.map((match, i) => (
                          <div key={i} style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: '0.5rem', 
                            padding: '0.35rem 0.5rem',
                            background: colors.cardBg,
                            borderRadius: 4,
                            marginBottom: '0.25rem',
                            fontSize: '0.8rem'
                          }}>
                            <span style={{ color: colors.accent, fontWeight: 600 }}>{match.term}</span>
                            <span style={{ color: colors.textMuted }}>→</span>
                            <span style={{ color: colors.warning }}>{match.table}</span>
                            <span style={{ color: colors.textMuted }}>.</span>
                            <span style={{ color: colors.primary }}>{match.column}</span>
                            <span style={{ color: colors.textMuted }}>{match.operator}</span>
                            <span style={{ color: colors.text }}>'{match.match_value}'</span>
                            <span style={{ 
                              marginLeft: 'auto', 
                              padding: '1px 6px', 
                              background: match.source === 'reasoned' ? `${colors.warning}20` : `${colors.accent}20`,
                              color: match.source === 'reasoned' ? colors.warning : colors.accent,
                              borderRadius: 3,
                              fontSize: '0.7rem'
                            }}>
                              {match.source || 'term_index'}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* SQL */}
                    {status.result.assembly?.sql && (
                      <div style={{ marginBottom: '0.75rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                          <div style={{ fontSize: '0.75rem', color: colors.textMuted, fontWeight: 600 }}>GENERATED SQL</div>
                          <button
                            onClick={() => copyToClipboard(status.result.assembly.sql)}
                            style={{
                              padding: '2px 6px',
                              background: colors.border,
                              border: 'none',
                              borderRadius: 3,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem',
                              fontSize: '0.7rem',
                              color: copiedText === status.result.assembly.sql ? colors.accent : colors.textMuted
                            }}
                          >
                            {copiedText === status.result.assembly.sql ? <Check size={10} /> : <Copy size={10} />}
                            {copiedText === status.result.assembly.sql ? 'Copied!' : 'Copy'}
                          </button>
                        </div>
                        <pre style={{ 
                          margin: 0, 
                          padding: '0.5rem', 
                          background: '#1a1a2e', 
                          borderRadius: 4, 
                          fontSize: '0.75rem', 
                          overflow: 'auto',
                          whiteSpace: 'pre-wrap',
                          color: colors.text,
                          fontFamily: 'monospace'
                        }}>
                          {status.result.assembly.sql}
                        </pre>
                      </div>
                    )}

                    {/* Execution results */}
                    {status.result.execution && (
                      <div>
                        <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.35rem', fontWeight: 600 }}>
                          EXECUTION ({status.result.execution.row_count} rows)
                        </div>
                        <pre style={{ 
                          margin: 0, 
                          padding: '0.5rem', 
                          background: '#1a1a2e', 
                          borderRadius: 4, 
                          fontSize: '0.7rem', 
                          maxHeight: 150,
                          overflow: 'auto',
                          whiteSpace: 'pre-wrap',
                          color: colors.text,
                          fontFamily: 'monospace'
                        }}>
                          {JSON.stringify(status.result.execution.sample_rows || status.result.execution, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Error */}
                    {status.result.error && (
                      <div style={{ padding: '0.5rem', background: `${colors.danger}15`, borderRadius: 4, fontSize: '0.8rem', color: colors.danger }}>
                        {status.result.error}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {/* Show custom query results */}
          {customQuery && queryResults[customQuery] && (
            <div style={{ background: colors.background, borderRadius: 8, overflow: 'hidden', border: `1px solid ${colors.primary}` }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '0.75rem', 
                padding: '0.75rem 1rem',
                cursor: queryResults[customQuery].result ? 'pointer' : 'default'
              }}
              onClick={() => queryResults[customQuery].result && toggleExpanded(customQuery)}
              >
                {queryResults[customQuery].result ? (
                  expandedResults[customQuery] ? <ChevronDown size={16} color={colors.textMuted} /> : <ChevronRight size={16} color={colors.textMuted} />
                ) : (
                  <div style={{ width: 16 }} />
                )}
                <div style={{ flex: 1 }}>
                  <code style={{ fontSize: '0.85rem', color: colors.primary }}>{customQuery}</code>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Custom query</div>
                </div>
                <StatusBadge status={queryResults[customQuery]} />
              </div>
              
              {/* Custom query expanded results - same structure as samples */}
              {expandedResults[customQuery] && queryResults[customQuery].result && (
                <div style={{ padding: '0 1rem 1rem 2.75rem' }}>
                  {queryResults[customQuery].result.term_matches && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.35rem', fontWeight: 600 }}>
                        TERM MATCHES ({queryResults[customQuery].result.term_matches.length})
                      </div>
                      {queryResults[customQuery].result.term_matches.map((match, i) => (
                        <div key={i} style={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: '0.5rem', 
                          padding: '0.35rem 0.5rem',
                          background: colors.cardBg,
                          borderRadius: 4,
                          marginBottom: '0.25rem',
                          fontSize: '0.8rem'
                        }}>
                          <span style={{ color: colors.accent, fontWeight: 600 }}>{match.term}</span>
                          <span style={{ color: colors.textMuted }}>→</span>
                          <span style={{ color: colors.warning }}>{match.table}</span>
                          <span style={{ color: colors.textMuted }}>.</span>
                          <span style={{ color: colors.primary }}>{match.column}</span>
                          <span style={{ color: colors.textMuted }}>{match.operator}</span>
                          <span style={{ color: colors.text }}>'{match.match_value}'</span>
                          <span style={{ 
                            marginLeft: 'auto', 
                            padding: '1px 6px', 
                            background: match.source === 'reasoned' ? `${colors.warning}20` : `${colors.accent}20`,
                            color: match.source === 'reasoned' ? colors.warning : colors.accent,
                            borderRadius: 3,
                            fontSize: '0.7rem'
                          }}>
                            {match.source || 'term_index'}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                  {queryResults[customQuery].result.assembly?.sql && (
                    <div>
                      <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.35rem', fontWeight: 600 }}>GENERATED SQL</div>
                      <pre style={{ 
                        margin: 0, 
                        padding: '0.5rem', 
                        background: '#1a1a2e', 
                        borderRadius: 4, 
                        fontSize: '0.75rem', 
                        overflow: 'auto',
                        whiteSpace: 'pre-wrap',
                        color: colors.text,
                        fontFamily: 'monospace'
                      }}>
                        {queryResults[customQuery].result.assembly.sql}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* CSS for spinner animation */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
