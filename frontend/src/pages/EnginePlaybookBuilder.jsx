/**
 * EnginePlaybookBuilder.jsx
 * =========================
 * 
 * New Playbook Builder using the 5 Universal Engines.
 * 
 * Features:
 * - Feature Library (pre-built engine configs)
 * - Drag to add features to playbook
 * - Configure each feature
 * - Run playbook via /api/engines/{project}/batch
 * - View results with findings
 * 
 * Route: /admin/playbook-builder (replaces old builder)
 * Created: January 17, 2026
 */

import React, { useState, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';
import { 
  Plus, Play, Save, Trash2, Settings, ChevronDown, ChevronRight,
  CheckCircle, XCircle, AlertTriangle, Loader2, GripVertical,
  Search, Filter, Database, GitCompare, Shield, Radar, Map,
  FileText, Copy, Download, ArrowLeft
} from 'lucide-react';
import { Link } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

// =============================================================================
// FEATURE LIBRARY - Pre-built engine configurations
// =============================================================================

const FEATURE_LIBRARY = [
  // =====================
  // GENERIC BUILDING BLOCKS
  // =====================
  {
    id: 'generic_compare',
    name: 'Compare Two Tables',
    description: 'Compare any two tables - select match keys and columns to compare',
    engine: 'compare',
    icon: GitCompare,
    category: 'Building Blocks',
    config: {
      source_a: '{{table_a}}',
      source_b: '{{table_b}}',
      match_keys: ['{{match_key}}'],
      compare_columns: ['{{column1}}', '{{column2}}']
    }
  },
  {
    id: 'generic_validate',
    name: 'Validate Data',
    description: 'Run validation rules against any table',
    engine: 'validate',
    icon: Shield,
    category: 'Building Blocks',
    config: {
      source_table: '{{table}}',
      rules: [
        { field: '{{field}}', type: '{{rule_type}}' }
      ],
      sample_limit: 20
    }
  },
  {
    id: 'generic_detect',
    name: 'Detect Patterns',
    description: 'Find duplicates, outliers, or anomalies in any table',
    engine: 'detect',
    icon: Radar,
    category: 'Building Blocks',
    config: {
      source_table: '{{table}}',
      patterns: [
        { type: '{{pattern_type}}', columns: ['{{column}}'] }
      ],
      sample_limit: 20
    }
  },
  {
    id: 'generic_aggregate',
    name: 'Aggregate Data',
    description: 'Count, sum, or average - grouped by any dimension',
    engine: 'aggregate',
    icon: Database,
    category: 'Building Blocks',
    config: {
      source_table: '{{table}}',
      measures: [{ function: '{{function}}', column: '{{measure_column}}' }],
      dimensions: ['{{group_by}}']
    }
  },
  {
    id: 'generic_map',
    name: 'Map Values',
    description: 'Transform or crosswalk values between systems',
    engine: 'map',
    icon: Map,
    category: 'Building Blocks',
    config: {
      mode: 'transform',
      source_table: '{{table}}',
      mappings: [{ column: '{{column}}', type: '{{mapping_type}}' }]
    }
  },

  // =====================
  // DETECT - Specific
  // =====================
  {
    id: 'detect_duplicate_ssn',
    name: 'Duplicate SSN Check',
    description: 'Find employees with duplicate Social Security Numbers',
    engine: 'detect',
    icon: Radar,
    category: 'Data Quality',
    config: {
      source_table: '{{census_table}}',
      patterns: [{ type: 'duplicate', columns: ['ssn'] }],
      sample_limit: 20
    }
  },
  {
    id: 'detect_duplicate_email',
    name: 'Duplicate Email Check',
    description: 'Find employees with duplicate email addresses',
    engine: 'detect',
    icon: Radar,
    category: 'Data Quality',
    config: {
      source_table: '{{census_table}}',
      patterns: [{ type: 'duplicate', columns: ['email'] }],
      sample_limit: 20
    }
  },
  {
    id: 'detect_duplicate_empid',
    name: 'Duplicate Employee ID',
    description: 'Find duplicate employee identifiers',
    engine: 'detect',
    icon: Radar,
    category: 'Data Quality',
    config: {
      source_table: '{{census_table}}',
      patterns: [{ type: 'duplicate', columns: ['employeeid'] }],
      sample_limit: 20
    }
  },
  {
    id: 'detect_salary_outliers',
    name: 'Salary Outliers',
    description: 'Find salaries that are statistical outliers (z-score > 3)',
    engine: 'detect',
    icon: Radar,
    category: 'Anomaly Detection',
    config: {
      source_table: '{{census_table}}',
      patterns: [{ type: 'outlier', column: 'salary', method: 'zscore', threshold: 3 }],
      sample_limit: 20
    }
  },
  
  // VALIDATE features
  {
    id: 'validate_required_fields',
    name: 'Required Fields Check',
    description: 'Verify critical fields are not null',
    engine: 'validate',
    icon: Shield,
    category: 'Data Quality',
    config: {
      source_table: '{{census_table}}',
      rules: [
        { field: 'employeeid', type: 'not_null' },
        { field: 'lastname', type: 'not_null' },
        { field: 'firstname', type: 'not_null' }
      ],
      sample_limit: 20
    }
  },
  {
    id: 'validate_email_format',
    name: 'Email Format Validation',
    description: 'Check email addresses match valid format',
    engine: 'validate',
    icon: Shield,
    category: 'Data Quality',
    config: {
      source_table: '{{census_table}}',
      rules: [{ field: 'email', type: 'format', pattern: 'email' }],
      sample_limit: 20
    }
  },
  {
    id: 'validate_ssn_format',
    name: 'SSN Format Validation',
    description: 'Check SSN matches XXX-XX-XXXX format',
    engine: 'validate',
    icon: Shield,
    category: 'Compliance',
    config: {
      source_table: '{{census_table}}',
      rules: [{ field: 'ssn', type: 'format', pattern: 'ssn' }],
      sample_limit: 20
    }
  },
  {
    id: 'validate_state_codes',
    name: 'Valid State Codes',
    description: 'Check state codes are valid US states',
    engine: 'validate',
    icon: Shield,
    category: 'Data Quality',
    config: {
      source_table: '{{census_table}}',
      rules: [{ 
        field: 'state', 
        type: 'allowed_values', 
        values: ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC']
      }],
      sample_limit: 20
    }
  },
  
  // COMPARE features
  {
    id: 'compare_census_payroll',
    name: 'Census vs Payroll Compare',
    description: 'Compare employee census against payroll records',
    engine: 'compare',
    icon: GitCompare,
    category: 'Reconciliation',
    config: {
      source_a: '{{census_table}}',
      source_b: '{{payroll_table}}',
      match_keys: ['employeeid']
    }
  },
  {
    id: 'compare_before_after',
    name: 'Before/After Compare',
    description: 'Compare two snapshots of the same data',
    engine: 'compare',
    icon: GitCompare,
    category: 'Reconciliation',
    config: {
      source_a: '{{before_table}}',
      source_b: '{{after_table}}',
      match_keys: ['employeeid']
    }
  },
  
  // AGGREGATE features
  {
    id: 'aggregate_headcount_state',
    name: 'Headcount by State',
    description: 'Count employees grouped by state',
    engine: 'aggregate',
    icon: Database,
    category: 'Analytics',
    config: {
      source_table: '{{census_table}}',
      measures: [{ function: 'COUNT' }],
      dimensions: ['state']
    }
  },
  {
    id: 'aggregate_headcount_dept',
    name: 'Headcount by Department',
    description: 'Count employees grouped by department',
    engine: 'aggregate',
    icon: Database,
    category: 'Analytics',
    config: {
      source_table: '{{census_table}}',
      measures: [{ function: 'COUNT' }],
      dimensions: ['department']
    }
  },
  {
    id: 'aggregate_salary_avg',
    name: 'Average Salary by Department',
    description: 'Calculate average salary per department',
    engine: 'aggregate',
    icon: Database,
    category: 'Analytics',
    config: {
      source_table: '{{census_table}}',
      measures: [{ function: 'AVG', column: 'salary' }],
      dimensions: ['department']
    }
  },
  
  // MAP features
  {
    id: 'map_state_names',
    name: 'Map State Codes to Names',
    description: 'Convert state abbreviations to full names',
    engine: 'map',
    icon: Map,
    category: 'Transformation',
    config: {
      mode: 'transform',
      source_table: '{{census_table}}',
      mappings: [{ column: 'state', type: 'state_names' }]
    }
  }
];

// Group features by category
const CATEGORIES = [...new Set(FEATURE_LIBRARY.map(f => f.category))];

// Engine colors
const ENGINE_COLORS = {
  detect: { bg: 'rgba(239, 68, 68, 0.1)', border: 'rgba(239, 68, 68, 0.3)', text: '#dc2626' },
  validate: { bg: 'rgba(245, 158, 11, 0.1)', border: 'rgba(245, 158, 11, 0.3)', text: '#d97706' },
  compare: { bg: 'rgba(59, 130, 246, 0.1)', border: 'rgba(59, 130, 246, 0.3)', text: '#2563eb' },
  aggregate: { bg: 'rgba(131, 177, 109, 0.1)', border: 'rgba(131, 177, 109, 0.3)', text: '#5a8a4a' },
  map: { bg: 'rgba(139, 92, 246, 0.1)', border: 'rgba(139, 92, 246, 0.3)', text: '#7c3aed' }
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function EnginePlaybookBuilder() {
  const { activeProject } = useProject();
  // Use TEA1000 for testing - has actual data
  const projectId = 'TEA1000';
  
  // Playbook state
  const [playbook, setPlaybook] = useState({
    name: 'New Playbook',
    description: '',
    features: []
  });
  
  // UI state
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [runStatus, setRunStatus] = useState({ running: false, results: null, error: null });
  const [tables, setTables] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [expandedResults, setExpandedResults] = useState({});
  
  // Load available tables on mount
  useEffect(() => {
    loadTables();
  }, [projectId]);
  
  const loadTables = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/engines/${projectId}/tables`);
      const data = await response.json();
      setTables(data.tables || []);
    } catch (err) {
      console.error('Failed to load tables:', err);
    }
  };
  
  // Add feature to playbook
  const addFeature = (libraryFeature) => {
    const newFeature = {
      ...libraryFeature,
      instanceId: `${libraryFeature.id}_${Date.now()}`,
      config: JSON.parse(JSON.stringify(libraryFeature.config)) // Deep clone
    };
    setPlaybook(prev => ({
      ...prev,
      features: [...prev.features, newFeature]
    }));
  };
  
  // Remove feature from playbook
  const removeFeature = (instanceId) => {
    setPlaybook(prev => ({
      ...prev,
      features: prev.features.filter(f => f.instanceId !== instanceId)
    }));
  };
  
  // Open config modal for feature
  const openConfig = (feature) => {
    setSelectedFeature(feature);
    setConfigModalOpen(true);
  };
  
  // Update feature config
  const updateFeatureConfig = (instanceId, newConfig) => {
    setPlaybook(prev => ({
      ...prev,
      features: prev.features.map(f => 
        f.instanceId === instanceId ? { ...f, config: newConfig } : f
      )
    }));
  };
  
  // Move feature up/down
  const moveFeature = (instanceId, direction) => {
    setPlaybook(prev => {
      const features = [...prev.features];
      const idx = features.findIndex(f => f.instanceId === instanceId);
      if (idx < 0) return prev;
      
      const newIdx = direction === 'up' ? idx - 1 : idx + 1;
      if (newIdx < 0 || newIdx >= features.length) return prev;
      
      [features[idx], features[newIdx]] = [features[newIdx], features[idx]];
      return { ...prev, features };
    });
  };
  
  // Resolve variables in config (replace {{table}} with actual table name)
  const resolveConfig = (config) => {
    const resolved = JSON.parse(JSON.stringify(config));
    const resolveValue = (val) => {
      if (typeof val === 'string' && val.startsWith('{{') && val.endsWith('}}')) {
        // For now, try to find a matching table or return the variable name
        const varName = val.slice(2, -2);
        const matchingTable = tables.find(t => 
          t.toLowerCase().includes(varName.replace('_table', '').toLowerCase())
        );
        return matchingTable || val;
      }
      return val;
    };
    
    const resolveObject = (obj) => {
      if (Array.isArray(obj)) {
        return obj.map(item => typeof item === 'object' ? resolveObject(item) : resolveValue(item));
      }
      if (typeof obj === 'object' && obj !== null) {
        const result = {};
        for (const [key, value] of Object.entries(obj)) {
          result[key] = typeof value === 'object' ? resolveObject(value) : resolveValue(value);
        }
        return result;
      }
      return obj;
    };
    
    return resolveObject(resolved);
  };
  
  // Run playbook
  const runPlaybook = async () => {
    if (playbook.features.length === 0) return;
    
    setRunStatus({ running: true, results: null, error: null });
    
    try {
      const operations = playbook.features.map((f, idx) => ({
        id: f.instanceId,
        engine: f.engine,
        config: resolveConfig(f.config)
      }));
      
      const response = await fetch(`${API_BASE}/api/engines/${projectId}/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operations })
      });
      
      const data = await response.json();
      setRunStatus({ running: false, results: data, error: null });
      
      // Auto-expand first result with findings
      if (data.results) {
        const firstWithFindings = data.results.find(r => r.findings?.length > 0);
        if (firstWithFindings) {
          setExpandedResults({ [firstWithFindings.id]: true });
        }
      }
    } catch (err) {
      setRunStatus({ running: false, results: null, error: err.message });
    }
  };
  
  // Filter library
  const filteredLibrary = FEATURE_LIBRARY.filter(f => {
    const matchesSearch = searchTerm === '' || 
      f.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || f.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });
  
  return (
    <div style={{ padding: 32, maxWidth: 1400, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Link to="/admin" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--grass-green)', textDecoration: 'none', marginBottom: 16, fontSize: 14 }}>
          <ArrowLeft size={16} /> Back to Admin
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600, color: 'var(--text-primary)' }}>
              Playbook Builder
            </h1>
            <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)', fontSize: 14 }}>
              Build analysis playbooks using the 5 universal engines • Project: <strong>{projectId}</strong>
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn" style={{ background: 'var(--bg-primary)' }}>
              <Save size={16} /> Save
            </button>
            <button 
              className="btn btn-primary" 
              onClick={runPlaybook}
              disabled={runStatus.running || playbook.features.length === 0}
            >
              {runStatus.running ? <Loader2 size={16} className="epb-spin" /> : <Play size={16} />}
              {runStatus.running ? 'Running...' : 'Run Playbook'}
            </button>
          </div>
        </div>
      </div>
      
      {/* Main Layout: Library | Playbook | Results */}
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 350px', gap: 24 }}>
        
        {/* Feature Library */}
        <div className="epb-panel">
          <div className="epb-panel-header">
            <FileText size={18} />
            <span>Feature Library</span>
          </div>
          
          {/* Search */}
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-color)' }}>
            <div className="epb-search">
              <Search size={14} />
              <input 
                type="text"
                placeholder="Search features..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          
          {/* Category filter */}
          <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--border-color)', display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            <button 
              className={`epb-cat-btn ${selectedCategory === 'All' ? 'active' : ''}`}
              onClick={() => setSelectedCategory('All')}
            >
              All
            </button>
            {CATEGORIES.map(cat => (
              <button 
                key={cat}
                className={`epb-cat-btn ${selectedCategory === cat ? 'active' : ''}`}
                onClick={() => setSelectedCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
          
          {/* Feature list */}
          <div className="epb-feature-list">
            {filteredLibrary.map(feature => {
              const Icon = feature.icon;
              const colors = ENGINE_COLORS[feature.engine];
              return (
                <div 
                  key={feature.id}
                  className="epb-library-item"
                  onClick={() => addFeature(feature)}
                >
                  <div className="epb-library-icon" style={{ background: colors.bg, color: colors.text }}>
                    <Icon size={16} />
                  </div>
                  <div className="epb-library-info">
                    <div className="epb-library-name">{feature.name}</div>
                    <div className="epb-library-desc">{feature.description}</div>
                  </div>
                  <Plus size={16} style={{ color: 'var(--grass-green)', flexShrink: 0 }} />
                </div>
              );
            })}
          </div>
        </div>
        
        {/* Playbook Editor */}
        <div className="epb-panel">
          <div className="epb-panel-header">
            <Settings size={18} />
            <span>Playbook</span>
            <span className="epb-badge">{playbook.features.length} features</span>
          </div>
          
          {/* Playbook name */}
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-color)' }}>
            <input
              type="text"
              value={playbook.name}
              onChange={(e) => setPlaybook(prev => ({ ...prev, name: e.target.value }))}
              className="epb-name-input"
              placeholder="Playbook name..."
            />
          </div>
          
          {/* Feature sequence */}
          <div className="epb-sequence">
            {playbook.features.length === 0 ? (
              <div className="epb-empty">
                <FileText size={32} style={{ opacity: 0.3 }} />
                <p>Click features in the library to add them here</p>
              </div>
            ) : (
              playbook.features.map((feature, idx) => {
                const colors = ENGINE_COLORS[feature.engine];
                const Icon = feature.icon;
                return (
                  <div key={feature.instanceId} className="epb-feature-card" style={{ borderLeftColor: colors.text }}>
                    <div className="epb-feature-header">
                      <div className="epb-feature-num">{idx + 1}</div>
                      <div className="epb-feature-icon" style={{ background: colors.bg, color: colors.text }}>
                        <Icon size={14} />
                      </div>
                      <div className="epb-feature-title">
                        <div className="epb-feature-name">{feature.name}</div>
                        <div className="epb-feature-engine">{feature.engine.toUpperCase()}</div>
                      </div>
                      <div className="epb-feature-actions">
                        <button onClick={() => openConfig(feature)} title="Configure">
                          <Settings size={14} />
                        </button>
                        <button onClick={() => moveFeature(feature.instanceId, 'up')} disabled={idx === 0} title="Move up">
                          ▲
                        </button>
                        <button onClick={() => moveFeature(feature.instanceId, 'down')} disabled={idx === playbook.features.length - 1} title="Move down">
                          ▼
                        </button>
                        <button onClick={() => removeFeature(feature.instanceId)} title="Remove" style={{ color: '#dc2626' }}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                    <div className="epb-feature-config">
                      <code>{JSON.stringify(feature.config, null, 0).slice(0, 100)}...</code>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
        
        {/* Results Panel */}
        <div className="epb-panel">
          <div className="epb-panel-header">
            <CheckCircle size={18} />
            <span>Results</span>
          </div>
          
          <div className="epb-results">
            {!runStatus.results && !runStatus.error && (
              <div className="epb-empty">
                <Play size={32} style={{ opacity: 0.3 }} />
                <p>Run the playbook to see results</p>
              </div>
            )}
            
            {runStatus.error && (
              <div className="epb-error">
                <XCircle size={16} />
                {runStatus.error}
              </div>
            )}
            
            {runStatus.results && (
              <>
                <div className="epb-results-summary">
                  <div className={`epb-results-status ${runStatus.results.success ? 'success' : 'warning'}`}>
                    {runStatus.results.success ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
                    {runStatus.results.summary}
                  </div>
                  {runStatus.results.total_findings > 0 && (
                    <div className="epb-findings-count">
                      {runStatus.results.total_findings} findings
                    </div>
                  )}
                </div>
                
                {/* Export Controls */}
                <ExportControls 
                  results={runStatus.results} 
                  projectId={projectId}
                  playbookName={playbook.name}
                />
                
                {runStatus.results.results?.map(result => {
                  const feature = playbook.features.find(f => f.instanceId === result.id);
                  const colors = ENGINE_COLORS[result.engine] || ENGINE_COLORS.aggregate;
                  const isExpanded = expandedResults[result.id];
                  
                  return (
                    <div key={result.id} className="epb-result-item">
                      <div 
                        className="epb-result-header"
                        onClick={() => setExpandedResults(prev => ({ ...prev, [result.id]: !prev[result.id] }))}
                      >
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        <span className="epb-result-status" style={{ 
                          color: result.success ? 'var(--grass-green)' : '#dc2626' 
                        }}>
                          {result.success ? <CheckCircle size={12} /> : <XCircle size={12} />}
                        </span>
                        <span className="epb-result-name">{feature?.name || result.engine}</span>
                        {result.findings?.length > 0 && (
                          <span className="epb-result-findings">{result.findings.length}</span>
                        )}
                      </div>
                      
                      {isExpanded && (
                        <div className="epb-result-details">
                          {result.summary && (
                            <div className="epb-result-summary">{result.summary}</div>
                          )}
                          
                          {result.findings?.length > 0 && (
                            <div className="epb-result-findings-list">
                              {result.findings.slice(0, 5).map((f, i) => (
                                <div key={i} className="epb-finding">
                                  <span className="epb-finding-type">{f.finding_type}</span>
                                  <span className="epb-finding-msg">{f.message}</span>
                                </div>
                              ))}
                              {result.findings.length > 5 && (
                                <div className="epb-finding-more">
                                  +{result.findings.length - 5} more findings
                                </div>
                              )}
                            </div>
                          )}
                          
                          {result.row_count !== undefined && (
                            <div className="epb-result-meta">
                              {result.row_count} rows returned
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </>
            )}
          </div>
        </div>
      </div>
      
      {/* Config Modal */}
      {configModalOpen && selectedFeature && (
        <ConfigModal
          feature={selectedFeature}
          tables={tables}
          onSave={(newConfig) => {
            updateFeatureConfig(selectedFeature.instanceId, newConfig);
            setConfigModalOpen(false);
          }}
          onClose={() => setConfigModalOpen(false)}
        />
      )}
      
      {/* Styles */}
      <style>{`
        .epb-spin { animation: epb-spin 1s linear infinite; }
        @keyframes epb-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        
        .epb-panel {
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          display: flex;
          flex-direction: column;
          max-height: calc(100vh - 180px);
        }
        
        .epb-panel-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 16px;
          border-bottom: 1px solid var(--border-color);
          font-weight: 600;
          color: var(--text-primary);
        }
        
        .epb-badge {
          margin-left: auto;
          background: var(--grass-green);
          color: white;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 11px;
          font-weight: 500;
        }
        
        .epb-search {
          display: flex;
          align-items: center;
          gap: 8px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 6px;
          padding: 8px 12px;
        }
        .epb-search input {
          border: none;
          background: none;
          outline: none;
          flex: 1;
          font-size: 13px;
          color: var(--text-primary);
        }
        
        .epb-cat-btn {
          padding: 4px 8px;
          border: 1px solid var(--border-color);
          border-radius: 4px;
          background: var(--bg-primary);
          font-size: 11px;
          cursor: pointer;
          color: var(--text-secondary);
        }
        .epb-cat-btn.active {
          background: var(--grass-green);
          border-color: var(--grass-green);
          color: white;
        }
        
        .epb-feature-list {
          flex: 1;
          overflow-y: auto;
          padding: 8px;
        }
        
        .epb-library-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px;
          border-radius: 6px;
          cursor: pointer;
          margin-bottom: 4px;
        }
        .epb-library-item:hover {
          background: var(--bg-primary);
        }
        
        .epb-library-icon {
          width: 32px;
          height: 32px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        
        .epb-library-info { flex: 1; min-width: 0; }
        .epb-library-name { font-size: 13px; font-weight: 500; color: var(--text-primary); }
        .epb-library-desc { font-size: 11px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        
        .epb-name-input {
          width: 100%;
          border: 1px solid var(--border-color);
          border-radius: 6px;
          padding: 8px 12px;
          font-size: 14px;
          font-weight: 500;
          color: var(--text-primary);
          background: var(--bg-primary);
        }
        
        .epb-sequence {
          flex: 1;
          overflow-y: auto;
          padding: 12px;
        }
        
        .epb-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 40px 20px;
          color: var(--text-secondary);
          text-align: center;
        }
        .epb-empty p { margin: 12px 0 0; font-size: 13px; }
        
        .epb-feature-card {
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-left: 3px solid;
          border-radius: 6px;
          margin-bottom: 8px;
          overflow: hidden;
        }
        
        .epb-feature-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
        }
        
        .epb-feature-num {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: var(--grass-green);
          color: white;
          font-size: 11px;
          font-weight: 600;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .epb-feature-icon {
          width: 24px;
          height: 24px;
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .epb-feature-title { flex: 1; }
        .epb-feature-name { font-size: 13px; font-weight: 500; color: var(--text-primary); }
        .epb-feature-engine { font-size: 10px; color: var(--text-secondary); text-transform: uppercase; }
        
        .epb-feature-actions {
          display: flex;
          gap: 4px;
        }
        .epb-feature-actions button {
          width: 24px;
          height: 24px;
          border: none;
          background: none;
          cursor: pointer;
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-secondary);
          font-size: 10px;
        }
        .epb-feature-actions button:hover { background: var(--bg-secondary); }
        .epb-feature-actions button:disabled { opacity: 0.3; cursor: not-allowed; }
        
        .epb-feature-config {
          padding: 8px 12px;
          background: rgba(0,0,0,0.02);
          border-top: 1px solid var(--border-color);
        }
        .epb-feature-config code {
          font-size: 10px;
          color: var(--text-secondary);
          word-break: break-all;
        }
        
        .epb-results {
          flex: 1;
          overflow-y: auto;
          padding: 12px;
        }
        
        .epb-error {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px;
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 6px;
          color: #dc2626;
          font-size: 13px;
        }
        
        .epb-results-summary {
          padding: 12px;
          background: var(--bg-primary);
          border-radius: 6px;
          margin-bottom: 12px;
        }
        
        .epb-results-status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 500;
          font-size: 14px;
        }
        .epb-results-status.success { color: var(--grass-green); }
        .epb-results-status.warning { color: #d97706; }
        
        .epb-findings-count {
          margin-top: 4px;
          font-size: 12px;
          color: var(--text-secondary);
        }
        
        .epb-result-item {
          border: 1px solid var(--border-color);
          border-radius: 6px;
          margin-bottom: 8px;
          overflow: hidden;
        }
        
        .epb-result-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          cursor: pointer;
          background: var(--bg-primary);
        }
        .epb-result-header:hover { background: var(--bg-secondary); }
        
        .epb-result-status { display: flex; align-items: center; }
        .epb-result-name { flex: 1; font-size: 13px; font-weight: 500; }
        .epb-result-findings {
          background: #dc2626;
          color: white;
          padding: 2px 6px;
          border-radius: 10px;
          font-size: 10px;
          font-weight: 600;
        }
        
        .epb-result-details {
          padding: 12px;
          border-top: 1px solid var(--border-color);
          font-size: 12px;
        }
        
        .epb-result-summary {
          color: var(--text-secondary);
          margin-bottom: 8px;
        }
        
        .epb-result-findings-list {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        
        .epb-finding {
          display: flex;
          gap: 8px;
          padding: 6px 8px;
          background: rgba(239, 68, 68, 0.05);
          border-radius: 4px;
        }
        .epb-finding-type { font-weight: 500; color: #dc2626; }
        .epb-finding-msg { color: var(--text-secondary); }
        .epb-finding-more { font-size: 11px; color: var(--text-secondary); font-style: italic; padding: 4px 8px; }
        
        .epb-result-meta {
          margin-top: 8px;
          color: var(--text-secondary);
          font-size: 11px;
        }
        
        /* Export styles */
        .epb-export {
          margin: 12px 0;
          padding: 12px;
          background: var(--bg-primary);
          border-radius: 6px;
        }
        
        .epb-export-row {
          display: flex;
          gap: 8px;
          align-items: center;
        }
        
        .epb-export-select {
          flex: 1;
          padding: 6px 10px;
          border: 1px solid var(--border-color);
          border-radius: 4px;
          font-size: 12px;
          background: var(--bg-secondary);
          color: var(--text-primary);
        }
        
        .epb-export-select:disabled {
          opacity: 0.5;
        }
        
        .epb-export-error {
          margin-top: 8px;
          padding: 8px;
          background: rgba(220, 38, 38, 0.1);
          border-radius: 4px;
          color: #dc2626;
          font-size: 12px;
        }
        
        /* Modal styles */
        .epb-modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        
        .epb-modal {
          background: var(--bg-secondary);
          border-radius: 12px;
          width: 600px;
          max-height: 80vh;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .epb-modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 20px;
          border-bottom: 1px solid var(--border-color);
        }
        
        .epb-modal-title { font-size: 16px; font-weight: 600; }
        
        .epb-modal-body {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
        }
        
        .epb-modal-footer {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          padding: 16px 20px;
          border-top: 1px solid var(--border-color);
        }
        
        .epb-form-group {
          margin-bottom: 16px;
        }
        .epb-form-group label {
          display: block;
          font-size: 12px;
          font-weight: 500;
          color: var(--text-secondary);
          margin-bottom: 4px;
        }
        .epb-form-group select,
        .epb-form-group textarea {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid var(--border-color);
          border-radius: 6px;
          font-size: 13px;
          background: var(--bg-primary);
          color: var(--text-primary);
        }
        .epb-form-group textarea {
          min-height: 200px;
          font-family: monospace;
        }
      `}</style>
    </div>
  );
}


// =============================================================================
// EXPORT CONTROLS
// =============================================================================

const EXPORT_TEMPLATES = [
  { id: 'executive_summary', name: 'Executive Summary', formats: ['pdf', 'docx', 'html'] },
  { id: 'findings_report', name: 'Detailed Findings Report', formats: ['docx', 'pdf', 'html'] },
  { id: 'data_quality_scorecard', name: 'Data Quality Scorecard', formats: ['xlsx', 'pdf', 'csv'] },
  { id: 'remediation_checklist', name: 'Remediation Checklist', formats: ['xlsx', 'docx', 'csv'] },
  { id: 'raw_data', name: 'Raw Data Export', formats: ['json', 'csv', 'xlsx'] }
];

function ExportControls({ results, projectId, playbookName }) {
  const [exporting, setExporting] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('');
  const [exportError, setExportError] = useState(null);
  
  const currentTemplate = EXPORT_TEMPLATES.find(t => t.id === selectedTemplate);
  
  const handleExport = async () => {
    if (!selectedTemplate || !selectedFormat) return;
    
    setExporting(true);
    setExportError(null);
    
    try {
      const response = await fetch(`${API_BASE}/api/engines/${projectId}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          playbook_results: results,
          template: selectedTemplate,
          format: selectedFormat,
          context: {
            project_name: projectId,
            playbook_name: playbookName
          }
        })
      });
      
      const data = await response.json();
      
      if (!data.success) {
        setExportError(data.error || 'Export failed');
        setExporting(false);
        return;
      }
      
      // Decode base64 and trigger download
      const binaryString = atob(data.content_base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      const blob = new Blob([bytes], { type: data.content_type });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = data.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      setExporting(false);
    } catch (err) {
      setExportError(err.message);
      setExporting(false);
    }
  };
  
  return (
    <div className="epb-export">
      <div className="epb-export-row">
        <select 
          value={selectedTemplate} 
          onChange={(e) => { 
            setSelectedTemplate(e.target.value); 
            setSelectedFormat(''); 
          }}
          className="epb-export-select"
        >
          <option value="">Select export template...</option>
          {EXPORT_TEMPLATES.map(t => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        
        <select 
          value={selectedFormat} 
          onChange={(e) => setSelectedFormat(e.target.value)}
          disabled={!currentTemplate}
          className="epb-export-select"
        >
          <option value="">Format...</option>
          {currentTemplate?.formats.map(f => (
            <option key={f} value={f}>{f.toUpperCase()}</option>
          ))}
        </select>
        
        <button 
          onClick={handleExport}
          disabled={!selectedTemplate || !selectedFormat || exporting}
          className="btn btn-primary"
          style={{ padding: '6px 12px' }}
        >
          {exporting ? <Loader2 size={14} className="epb-spin" /> : <Download size={14} />}
          {exporting ? 'Exporting...' : 'Export'}
        </button>
      </div>
      
      {exportError && (
        <div className="epb-export-error">{exportError}</div>
      )}
    </div>
  );
}


// =============================================================================
// CONFIG MODAL
// =============================================================================

function ConfigModal({ feature, tables, onSave, onClose }) {
  const [config, setConfig] = useState(JSON.stringify(feature.config, null, 2));
  const [error, setError] = useState(null);
  
  const handleSave = () => {
    try {
      const parsed = JSON.parse(config);
      onSave(parsed);
    } catch (e) {
      setError('Invalid JSON: ' + e.message);
    }
  };
  
  return (
    <div className="epb-modal-overlay" onClick={onClose}>
      <div className="epb-modal" onClick={e => e.stopPropagation()}>
        <div className="epb-modal-header">
          <div className="epb-modal-title">Configure: {feature.name}</div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18 }}>×</button>
        </div>
        
        <div className="epb-modal-body">
          <div className="epb-form-group">
            <label>Engine</label>
            <input type="text" value={feature.engine.toUpperCase()} disabled style={{ 
              width: '100%', padding: '8px 12px', border: '1px solid var(--border-color)', 
              borderRadius: 6, background: 'var(--bg-primary)', color: 'var(--text-secondary)'
            }} />
          </div>
          
          <div className="epb-form-group">
            <label>Available Tables</label>
            <select onChange={(e) => {
              if (e.target.value) {
                navigator.clipboard.writeText(e.target.value);
              }
            }}>
              <option value="">Click to copy table name...</option>
              {tables.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          
          <div className="epb-form-group">
            <label>Configuration (JSON)</label>
            <textarea 
              value={config}
              onChange={(e) => { setConfig(e.target.value); setError(null); }}
            />
            {error && <div style={{ color: '#dc2626', fontSize: 12, marginTop: 4 }}>{error}</div>}
          </div>
        </div>
        
        <div className="epb-modal-footer">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSave}>Save</button>
        </div>
      </div>
    </div>
  );
}
