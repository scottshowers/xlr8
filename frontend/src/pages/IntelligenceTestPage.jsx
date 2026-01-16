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
 * Updated: January 16, 2026 - Light theme UX
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  const navigate = useNavigate();
  const projectId = activeProject?.name || 'TEA1000';
  
  // State for each operation
  const [analyzeStatus, setAnalyzeStatus] = useState({ loading: false, result: null, error: null });
  const [recalcStatus, setRecalcStatus] = useState({ loading: false, result: null, error: null });
  const [queryResults, setQueryResults] = useState({});
  const [customQuery, setCustomQuery] = useState('');
  const [expandedResults, setExpandedResults] = useState({});
  const [copiedText, setCopiedText] = useState(null);

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

  // Toggle result expansion
  const toggleExpanded = (question) => {
    setExpandedResults(prev => ({ ...prev, [question]: !prev[question] }));
  };

  // Render status badge
  const StatusBadge = ({ status }) => {
    if (status.loading) {
      return (
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#f59e0b' }}>
          <Loader2 size={14} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
          Running...
        </span>
      );
    }
    if (status.error) {
      return (
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#ef4444' }}>
          <XCircle size={14} /> Error
        </span>
      );
    }
    if (status.result) {
      return (
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#10b981' }}>
          <CheckCircle size={14} /> Complete
        </span>
      );
    }
    return <span style={{ color: 'var(--text-muted)' }}>Not run</span>;
  };

  return (
    <div>
      {/* Back link */}
      <button
        onClick={() => navigate('/admin')}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          color: 'var(--text-muted)',
          background: 'none',
          border: 'none',
          fontSize: 13,
          marginBottom: 16,
          cursor: 'pointer',
          padding: 0,
        }}
      >
        <ArrowLeft size={16} />
        Back to Platform Settings
      </button>

      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ 
          margin: 0, 
          fontSize: '20px', 
          fontWeight: 600, 
          color: 'var(--text-primary)', 
          display: 'flex', 
          alignItems: 'center', 
          gap: '10px',
          fontFamily: "'Sora', var(--font-body)"
        }}>
          <div style={{ 
            width: '36px', 
            height: '36px', 
            borderRadius: '10px', 
            backgroundColor: 'var(--grass-green)', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center' 
          }}>
            <Brain size={20} color="#ffffff" />
          </div>
          Intelligence Pipeline Test
        </h1>
        <p style={{ margin: '6px 0 0 46px', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
          Test MetadataReasoner and term resolution for project: <strong style={{ color: 'var(--grass-green)' }}>{projectId}</strong>
        </p>
      </div>

      {/* Warning if no project */}
      {!activeProject && (
        <div style={{ 
          padding: '12px 16px', 
          background: 'rgba(245, 158, 11, 0.1)', 
          border: '1px solid rgba(245, 158, 11, 0.3)',
          borderRadius: 'var(--radius-lg)', 
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          fontSize: 'var(--text-sm)'
        }}>
          <AlertTriangle size={20} color="#f59e0b" />
          <span style={{ color: 'var(--text-secondary)' }}>
            No project selected. Using default: <strong>TEA1000</strong>. Select a project from the flow bar for different data.
          </span>
        </div>
      )}

      {/* Step 1: Analyze */}
      <div style={{ 
        background: 'var(--bg-secondary)', 
        border: '1px solid var(--border)', 
        borderRadius: 'var(--radius-lg)', 
        padding: '20px', 
        marginBottom: '16px' 
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ 
              width: 32, height: 32, borderRadius: '50%', 
              background: 'var(--grass-green)', color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', 
              fontWeight: 600, fontSize: '14px' 
            }}>1</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 'var(--text-base)', color: 'var(--text-primary)' }}>Run Analyze</div>
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Populates _intelligence_lookups, _table_classifications</div>
            </div>
          </div>
          <StatusBadge status={analyzeStatus} />
        </div>
        <button
          onClick={runAnalyze}
          disabled={analyzeStatus.loading}
          style={{
            padding: '10px 20px',
            background: analyzeStatus.loading ? 'var(--border)' : 'var(--grass-green)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            cursor: analyzeStatus.loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: 'var(--text-sm)',
            fontWeight: 600
          }}
        >
          {analyzeStatus.loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Database size={16} />}
          {analyzeStatus.loading ? 'Analyzing...' : 'Run Analyze'}
        </button>
        {analyzeStatus.error && (
          <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 'var(--radius-md)', fontSize: 'var(--text-sm)', color: '#ef4444' }}>
            {analyzeStatus.error}
          </div>
        )}
        {analyzeStatus.result && (
          <div style={{ marginTop: '12px', padding: '12px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', fontSize: '12px', fontFamily: 'monospace', maxHeight: 150, overflow: 'auto' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>{JSON.stringify(analyzeStatus.result, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Step 2: Recalc */}
      <div style={{ 
        background: 'var(--bg-secondary)', 
        border: '1px solid var(--border)', 
        borderRadius: 'var(--radius-lg)', 
        padding: '20px', 
        marginBottom: '16px' 
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ 
              width: 32, height: 32, borderRadius: '50%', 
              background: 'var(--grass-green)', color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', 
              fontWeight: 600, fontSize: '14px' 
            }}>2</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 'var(--text-base)', color: 'var(--text-primary)' }}>Run Recalc</div>
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Builds _term_index, _entity_tables, join_priority</div>
            </div>
          </div>
          <StatusBadge status={recalcStatus} />
        </div>
        <button
          onClick={runRecalc}
          disabled={recalcStatus.loading}
          style={{
            padding: '10px 20px',
            background: recalcStatus.loading ? 'var(--border)' : 'var(--grass-green)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            cursor: recalcStatus.loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: 'var(--text-sm)',
            fontWeight: 600
          }}
        >
          {recalcStatus.loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <RefreshCw size={16} />}
          {recalcStatus.loading ? 'Recalculating...' : 'Run Recalc'}
        </button>
        {recalcStatus.error && (
          <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 'var(--radius-md)', fontSize: 'var(--text-sm)', color: '#ef4444' }}>
            {recalcStatus.error}
          </div>
        )}
        {recalcStatus.result && (
          <div style={{ marginTop: '12px', padding: '12px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', fontSize: '12px', fontFamily: 'monospace', maxHeight: 150, overflow: 'auto' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>{JSON.stringify(recalcStatus.result, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Step 3: Query Tests */}
      <div style={{ 
        background: 'var(--bg-secondary)', 
        border: '1px solid var(--border)', 
        borderRadius: 'var(--radius-lg)', 
        padding: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ 
              width: 32, height: 32, borderRadius: '50%', 
              background: 'var(--grass-green)', color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', 
              fontWeight: 600, fontSize: '14px' 
            }}>3</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 'var(--text-base)', color: 'var(--text-primary)' }}>Test Queries</div>
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Test term resolution and SQL assembly</div>
            </div>
          </div>
          <button
            onClick={runAllQueries}
            style={{
              padding: '8px 16px',
              background: 'var(--grass-green)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: 'var(--text-sm)',
              fontWeight: 600
            }}
          >
            <Play size={14} />
            Run All Tests
          </button>
        </div>

        {/* Custom Query Input */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              value={customQuery}
              onChange={(e) => setCustomQuery(e.target.value)}
              placeholder="Enter custom query..."
              onKeyPress={(e) => e.key === 'Enter' && customQuery && testQuery(customQuery)}
              style={{
                width: '100%',
                padding: '10px 12px 10px 36px',
                background: 'var(--bg-primary)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--text-sm)',
                color: 'var(--text-primary)',
                outline: 'none'
              }}
            />
          </div>
          <button
            onClick={() => customQuery && testQuery(customQuery)}
            disabled={!customQuery}
            style={{
              padding: '10px 20px',
              background: customQuery ? 'var(--grass-green)' : 'var(--border)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              cursor: customQuery ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: 'var(--text-sm)',
              fontWeight: 600
            }}
          >
            <Zap size={14} />
            Test
          </button>
        </div>

        {/* Sample Queries */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {SAMPLE_QUESTIONS.map((sample, idx) => {
            const status = queryResults[sample.query] || {};
            return (
              <div key={idx} style={{ 
                background: 'var(--bg-primary)', 
                borderRadius: 'var(--radius-md)', 
                overflow: 'hidden', 
                border: '1px solid var(--border)' 
              }}>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '12px', 
                  padding: '12px 16px',
                  cursor: status.result ? 'pointer' : 'default'
                }}
                onClick={() => status.result && toggleExpanded(sample.query)}
                >
                  {status.result ? (
                    expandedResults[sample.query] ? <ChevronDown size={16} style={{ color: 'var(--text-muted)' }} /> : <ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />
                  ) : (
                    <div style={{ width: 16 }} />
                  )}
                  <div style={{ flex: 1 }}>
                    <code style={{ fontSize: 'var(--text-sm)', color: 'var(--grass-green)', fontFamily: 'monospace' }}>{sample.query}</code>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{sample.description}</div>
                  </div>
                  <StatusBadge status={status} />
                  {!status.loading && !status.result && (
                    <button
                      onClick={(e) => { e.stopPropagation(); testQuery(sample.query); }}
                      style={{
                        padding: '6px 12px',
                        background: 'var(--border)',
                        border: 'none',
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer',
                        fontSize: '12px',
                        color: 'var(--text-secondary)',
                        fontWeight: 500
                      }}
                    >
                      Run
                    </button>
                  )}
                </div>

                {/* Expanded Results */}
                {expandedResults[sample.query] && status.result && (
                  <div style={{ padding: '0 16px 16px 44px', borderTop: '1px solid var(--border)', marginTop: '4px', paddingTop: '12px' }}>
                    {/* Term Matches */}
                    {status.result.term_matches && (
                      <div style={{ marginBottom: '12px' }}>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase' }}>
                          TERM MATCHES ({status.result.term_matches.length})
                        </div>
                        {status.result.term_matches.map((match, i) => (
                          <div key={i} style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: '8px', 
                            padding: '6px 10px',
                            background: 'var(--bg-tertiary)',
                            borderRadius: 'var(--radius-sm)',
                            marginBottom: '4px',
                            fontSize: '13px'
                          }}>
                            <span style={{ color: '#10b981', fontWeight: 600 }}>{match.term}</span>
                            <span style={{ color: 'var(--text-muted)' }}>→</span>
                            <span style={{ color: '#f59e0b' }}>{match.table}</span>
                            <span style={{ color: 'var(--text-muted)' }}>.</span>
                            <span style={{ color: 'var(--grass-green)' }}>{match.column}</span>
                            <span style={{ color: 'var(--text-muted)' }}>{match.operator}</span>
                            <span style={{ color: 'var(--text-primary)' }}>'{match.match_value}'</span>
                            <span style={{ 
                              marginLeft: 'auto', 
                              padding: '2px 8px', 
                              background: match.source === 'reasoned' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                              color: match.source === 'reasoned' ? '#f59e0b' : '#10b981',
                              borderRadius: 4,
                              fontSize: '11px',
                              fontWeight: 500
                            }}>
                              {match.source || 'term_index'}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* SQL */}
                    {status.result.assembly?.sql && (
                      <div style={{ marginBottom: '12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>GENERATED SQL</div>
                          <button
                            onClick={() => copyToClipboard(status.result.assembly.sql)}
                            style={{
                              padding: '4px 8px',
                              background: 'var(--border)',
                              border: 'none',
                              borderRadius: 'var(--radius-sm)',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontSize: '11px',
                              color: copiedText === status.result.assembly.sql ? '#10b981' : 'var(--text-muted)'
                            }}
                          >
                            {copiedText === status.result.assembly.sql ? <Check size={12} /> : <Copy size={12} />}
                            {copiedText === status.result.assembly.sql ? 'Copied!' : 'Copy'}
                          </button>
                        </div>
                        <pre style={{ 
                          margin: 0, 
                          padding: '12px', 
                          background: 'var(--bg-tertiary)', 
                          borderRadius: 'var(--radius-md)', 
                          fontSize: '12px', 
                          overflow: 'auto',
                          whiteSpace: 'pre-wrap',
                          color: 'var(--text-secondary)',
                          fontFamily: 'monospace',
                          border: '1px solid var(--border)'
                        }}>
                          {status.result.assembly.sql}
                        </pre>
                      </div>
                    )}

                    {/* Execution results */}
                    {status.result.execution && (
                      <div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase' }}>
                          EXECUTION ({status.result.execution.row_count} rows)
                        </div>
                        <pre style={{ 
                          margin: 0, 
                          padding: '12px', 
                          background: 'var(--bg-tertiary)', 
                          borderRadius: 'var(--radius-md)', 
                          fontSize: '11px', 
                          maxHeight: 150,
                          overflow: 'auto',
                          whiteSpace: 'pre-wrap',
                          color: 'var(--text-secondary)',
                          fontFamily: 'monospace',
                          border: '1px solid var(--border)'
                        }}>
                          {JSON.stringify(status.result.execution.sample_rows || status.result.execution, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Error */}
                    {status.result.error && (
                      <div style={{ padding: '10px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 'var(--radius-md)', fontSize: 'var(--text-sm)', color: '#ef4444' }}>
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
            <div style={{ 
              background: 'var(--bg-primary)', 
              borderRadius: 'var(--radius-md)', 
              overflow: 'hidden', 
              border: '2px solid var(--grass-green)' 
            }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '12px', 
                padding: '12px 16px',
                cursor: queryResults[customQuery].result ? 'pointer' : 'default'
              }}
              onClick={() => queryResults[customQuery].result && toggleExpanded(customQuery)}
              >
                {queryResults[customQuery].result ? (
                  expandedResults[customQuery] ? <ChevronDown size={16} style={{ color: 'var(--text-muted)' }} /> : <ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />
                ) : (
                  <div style={{ width: 16 }} />
                )}
                <div style={{ flex: 1 }}>
                  <code style={{ fontSize: 'var(--text-sm)', color: 'var(--grass-green)', fontFamily: 'monospace' }}>{customQuery}</code>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Custom query</div>
                </div>
                <StatusBadge status={queryResults[customQuery]} />
              </div>
              
              {/* Custom query expanded results */}
              {expandedResults[customQuery] && queryResults[customQuery].result && (
                <div style={{ padding: '0 16px 16px 44px', borderTop: '1px solid var(--border)', marginTop: '4px', paddingTop: '12px' }}>
                  {queryResults[customQuery].result.term_matches && (
                    <div style={{ marginBottom: '12px' }}>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase' }}>
                        TERM MATCHES ({queryResults[customQuery].result.term_matches.length})
                      </div>
                      {queryResults[customQuery].result.term_matches.map((match, i) => (
                        <div key={i} style={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: '8px', 
                          padding: '6px 10px',
                          background: 'var(--bg-tertiary)',
                          borderRadius: 'var(--radius-sm)',
                          marginBottom: '4px',
                          fontSize: '13px'
                        }}>
                          <span style={{ color: '#10b981', fontWeight: 600 }}>{match.term}</span>
                          <span style={{ color: 'var(--text-muted)' }}>→</span>
                          <span style={{ color: '#f59e0b' }}>{match.table}</span>
                          <span style={{ color: 'var(--text-muted)' }}>.</span>
                          <span style={{ color: 'var(--grass-green)' }}>{match.column}</span>
                          <span style={{ color: 'var(--text-muted)' }}>{match.operator}</span>
                          <span style={{ color: 'var(--text-primary)' }}>'{match.match_value}'</span>
                          <span style={{ 
                            marginLeft: 'auto', 
                            padding: '2px 8px', 
                            background: match.source === 'reasoned' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                            color: match.source === 'reasoned' ? '#f59e0b' : '#10b981',
                            borderRadius: 4,
                            fontSize: '11px',
                            fontWeight: 500
                          }}>
                            {match.source || 'term_index'}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                  {queryResults[customQuery].result.assembly?.sql && (
                    <div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase' }}>GENERATED SQL</div>
                      <pre style={{ 
                        margin: 0, 
                        padding: '12px', 
                        background: 'var(--bg-tertiary)', 
                        borderRadius: 'var(--radius-md)', 
                        fontSize: '12px', 
                        overflow: 'auto',
                        whiteSpace: 'pre-wrap',
                        color: 'var(--text-secondary)',
                        fontFamily: 'monospace',
                        border: '1px solid var(--border)'
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
