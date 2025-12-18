/**
 * DataModelPage - Data Integrity + Relationship Review
 * 
 * TWO SECTIONS:
 * 1. DATA INTEGRITY (top) - Shows table health, flags bad columns, header issues
 * 2. RELATIONSHIPS (bottom) - Only meaningful after data is clean
 * 
 * Deploy to: frontend/src/components/DataModelPage.jsx
 */

import React, { useState, useEffect, useRef } from 'react';
import { useProject } from '../context/ProjectContext';
import { 
  CheckCircle, AlertTriangle, RefreshCw, Zap, ChevronDown, ChevronRight,
  Database, Link2, Eye, EyeOff, X, Check, HelpCircle, AlertCircle,
  Table2, Columns, FileWarning, CheckCircle2, XCircle, Loader2
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function DataModelPage({ embedded = false }) {
  const { activeProject } = useProject();
  
  // Data Integrity state
  const [integrityLoading, setIntegrityLoading] = useState(false);
  const [integrityData, setIntegrityData] = useState(null);
  const [expandedTables, setExpandedTables] = useState(new Set());
  const [tableProfiles, setTableProfiles] = useState({});
  const [loadingProfiles, setLoadingProfiles] = useState(new Set());
  
  // Relationships state
  const [relLoading, setRelLoading] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);
  const [relationships, setRelationships] = useState([]);
  const [semanticTypes, setSemanticTypes] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [warnings, setWarnings] = useState([]);
  
  // UI state
  const [showHighConfidence, setShowHighConfidence] = useState(false);
  const [showNeedsReview, setShowNeedsReview] = useState(false);

  // Separate relationships
  const needsReview = relationships.filter(r => r.needs_review && !r.confirmed);
  const autoMatched = relationships.filter(r => !r.needs_review || r.confirmed);

  // Load both integrity and relationships on mount
  useEffect(() => {
    if (activeProject?.name) {
      loadDataIntegrity();
      loadExistingRelationships();
    }
  }, [activeProject?.name]);

  // ==================== DATA INTEGRITY ====================
  const loadDataIntegrity = async () => {
    setIntegrityLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/status/data-integrity?project=${encodeURIComponent(activeProject?.id || '')}`);
      if (res.ok) {
        const data = await res.json();
        setIntegrityData(data);
      }
    } catch (err) {
      console.error('Failed to load integrity:', err);
    } finally {
      setIntegrityLoading(false);
    }
  };

  const loadTableProfile = async (tableName) => {
    if (tableProfiles[tableName] || loadingProfiles.has(tableName)) return;
    
    setLoadingProfiles(prev => new Set([...prev, tableName]));
    try {
      const res = await fetch(`${API_BASE}/api/status/table-profile/${encodeURIComponent(tableName)}`);
      if (res.ok) {
        const data = await res.json();
        setTableProfiles(prev => ({ ...prev, [tableName]: data }));
      }
    } catch (err) {
      console.error(`Failed to load profile for ${tableName}:`, err);
    } finally {
      setLoadingProfiles(prev => {
        const next = new Set(prev);
        next.delete(tableName);
        return next;
      });
    }
  };

  const toggleTableExpand = (tableName) => {
    const newSet = new Set(expandedTables);
    if (newSet.has(tableName)) {
      newSet.delete(tableName);
    } else {
      newSet.add(tableName);
      loadTableProfile(tableName);
    }
    setExpandedTables(newSet);
  };

  // ==================== RELATIONSHIPS ====================
  const loadExistingRelationships = async () => {
    if (!activeProject?.name) return;
    
    setRelLoading(true);
    setError(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/data-model/relationships/${encodeURIComponent(activeProject.name)}`);
      
      if (!res.ok) throw new Error(`Failed to load: ${res.status}`);
      
      const data = await res.json();
      
      if (data.relationships && data.relationships.length > 0) {
        setRelationships(data.relationships);
        setSemanticTypes(data.semantic_types || []);
        setStats(data.stats || null);
        setWarnings(data.warnings || []);
        setAnalyzed(true);
      } else {
        setStats(data.stats || null);
        setWarnings(data.warnings || []);
      }
      
    } catch (err) {
      console.warn('No existing relationships:', err.message);
    } finally {
      setRelLoading(false);
    }
  };

  const analyzeProject = async () => {
    if (!activeProject?.name) return;
    
    setRelLoading(true);
    setError(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/data-model/analyze/${encodeURIComponent(activeProject.name)}`, {
        method: 'POST'
      });
      
      if (!res.ok) throw new Error(`Analysis failed: ${res.status}`);
      
      const data = await res.json();
      setRelationships(data.relationships || []);
      setSemanticTypes(data.semantic_types || []);
      setStats(data.stats || null);
      setWarnings(data.warnings || []);
      setAnalyzed(true);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setRelLoading(false);
    }
  };

  const confirmRelationship = async (rel, confirmed) => {
    try {
      const res = await fetch(`${API_BASE}/api/data-model/relationships/${encodeURIComponent(activeProject.name)}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_table: rel.source_table,
          source_column: rel.source_column,
          target_table: rel.target_table,
          target_column: rel.target_column,
          confirmed,
          semantic_type: rel.semantic_type
        })
      });
      
      if (res.ok) {
        setRelationships(prev => prev.map(r => {
          if (r.source_table === rel.source_table && r.source_column === rel.source_column &&
              r.target_table === rel.target_table && r.target_column === rel.target_column) {
            return confirmed 
              ? { ...r, confirmed: true, needs_review: false }
              : null;
          }
          return r;
        }).filter(Boolean));
      }
    } catch (err) {
      console.error('Failed to confirm:', err);
    }
  };

  // ==================== RENDER ====================
  if (!activeProject) {
    return (
      <div className="p-8 text-center text-gray-500">
        <Database className="w-12 h-12 mx-auto mb-4 opacity-30" />
        <p>Select a project to view data model</p>
      </div>
    );
  }

  const hasIntegrityIssues = integrityData?.tables_with_issues > 0;

  return (
    <div className={`space-y-6 ${embedded ? '' : 'p-6'}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-800">Data Model</h1>
          <p className="text-sm text-gray-500">{activeProject.name} • Data integrity + relationships</p>
        </div>
        <button
          onClick={() => { loadDataIntegrity(); analyzeProject(); }}
          disabled={relLoading || integrityLoading}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 disabled:opacity-50"
        >
          {(relLoading || integrityLoading) ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Zap className="w-4 h-4" />
          )}
          Re-analyze
        </button>
      </div>

      {/* ==================== DATA INTEGRITY SECTION ==================== */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Database className="w-5 h-5 text-blue-500" />
            <div>
              <h2 className="font-semibold text-gray-800">Data Integrity</h2>
              <p className="text-xs text-gray-500">Verify tables loaded correctly before analyzing relationships</p>
            </div>
          </div>
          {integrityData && (
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              integrityData.status === 'healthy' ? 'bg-green-100 text-green-700' :
              integrityData.status === 'warning' ? 'bg-amber-100 text-amber-700' :
              'bg-red-100 text-red-700'
            }`}>
              {integrityData.status === 'healthy' ? '✓ Healthy' :
               integrityData.status === 'warning' ? '⚠ Issues Found' :
               '✗ Critical Issues'}
            </div>
          )}
        </div>

        <div className="p-6">
          {integrityLoading ? (
            <div className="flex items-center justify-center py-8 text-gray-400">
              <Loader2 className="w-6 h-6 animate-spin mr-2" />
              Checking data integrity...
            </div>
          ) : !integrityData ? (
            <div className="text-center py-8 text-gray-400">
              <FileWarning className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p>Click Re-analyze to check data integrity</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-gray-800">{integrityData.tables_checked}</div>
                  <div className="text-sm text-gray-500">Tables Checked</div>
                </div>
                <div className={`rounded-lg p-4 text-center ${
                  integrityData.tables_with_issues === 0 ? 'bg-green-50' : 'bg-red-50'
                }`}>
                  <div className={`text-2xl font-bold ${
                    integrityData.tables_with_issues === 0 ? 'text-green-600' : 'text-red-600'
                  }`}>{integrityData.tables_with_issues}</div>
                  <div className={`text-sm ${
                    integrityData.tables_with_issues === 0 ? 'text-green-600' : 'text-red-600'
                  }`}>Tables with Issues</div>
                </div>
                <div className="bg-blue-50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-blue-600">{stats?.columns_analyzed || 0}</div>
                  <div className="text-sm text-blue-600">Total Columns</div>
                </div>
              </div>

              {/* Issues List */}
              {hasIntegrityIssues && (
                <div className="border border-red-200 rounded-lg overflow-hidden">
                  <div className="bg-red-50 px-4 py-3 border-b border-red-200">
                    <div className="flex items-center gap-2 text-red-700 font-medium">
                      <AlertCircle className="w-4 h-4" />
                      Tables with Problems
                    </div>
                    <p className="text-xs text-red-600 mt-1">
                      These tables may have header detection failures. Re-upload after deploying fixes.
                    </p>
                  </div>
                  <div className="divide-y divide-red-100 max-h-80 overflow-y-auto">
                    {integrityData.issues?.map((issue, i) => (
                      <div key={i} className="bg-white">
                        <button
                          onClick={() => toggleTableExpand(issue.table)}
                          className="w-full px-4 py-3 flex items-center justify-between hover:bg-red-50 text-left"
                        >
                          <div className="flex items-center gap-3">
                            {expandedTables.has(issue.table) ? 
                              <ChevronDown className="w-4 h-4 text-gray-400" /> : 
                              <ChevronRight className="w-4 h-4 text-gray-400" />
                            }
                            <Table2 className="w-4 h-4 text-red-400" />
                            <span className="font-medium text-gray-700 text-sm">{issue.table}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-500">{issue.column_count} cols</span>
                            {issue.issues?.map((iss, j) => (
                              <span key={j} className={`text-xs px-2 py-0.5 rounded ${
                                iss.severity === 'high' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                              }`}>
                                {iss.type.replace(/_/g, ' ')}
                              </span>
                            ))}
                          </div>
                        </button>
                        
                        {expandedTables.has(issue.table) && (
                          <div className="px-4 py-3 bg-gray-50 border-t">
                            {issue.issues?.map((iss, j) => (
                              <div key={j} className="text-sm text-gray-600 mb-2">
                                <span className="font-medium">{iss.type}:</span> {iss.details}
                              </div>
                            ))}
                            
                            {tableProfiles[issue.table] ? (
                              <div className="mt-3 grid grid-cols-4 gap-2">
                                {tableProfiles[issue.table].columns?.slice(0, 20).map((col, ci) => (
                                  <div key={ci} className={`text-xs px-2 py-1 rounded border ${
                                    col.name.toLowerCase().includes('nan') || 
                                    col.name.toLowerCase().includes('unnamed') ||
                                    /^col_\d+$/.test(col.name)
                                      ? 'bg-red-50 border-red-200 text-red-700'
                                      : 'bg-white border-gray-200 text-gray-600'
                                  }`}>
                                    <div className="font-medium truncate" title={col.name}>{col.name}</div>
                                    <div className="text-gray-400">
                                      {col.distinct_values?.toLocaleString() || '?'} vals • {col.fill_rate ?? '?'}%
                                    </div>
                                  </div>
                                ))}
                                {tableProfiles[issue.table].columns?.length > 20 && (
                                  <div className="text-xs text-gray-400 flex items-center">
                                    +{tableProfiles[issue.table].columns.length - 20} more
                                  </div>
                                )}
                              </div>
                            ) : loadingProfiles.has(issue.table) ? (
                              <div className="text-xs text-gray-400 flex items-center gap-2">
                                <Loader2 className="w-3 h-3 animate-spin" /> Loading columns...
                              </div>
                            ) : null}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!hasIntegrityIssues && integrityData.tables_checked > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
                  <CheckCircle2 className="w-6 h-6 text-green-500" />
                  <div>
                    <div className="font-medium text-green-700">All tables look healthy</div>
                    <div className="text-sm text-green-600">Column names are valid and data appears properly loaded</div>
                  </div>
                </div>
              )}

              {integrityData.recommendation && hasIntegrityIssues && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-700">
                  <strong>Recommendation:</strong> {integrityData.recommendation}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ==================== RELATIONSHIPS SECTION ==================== */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link2 className="w-5 h-5 text-purple-500" />
            <div>
              <h2 className="font-semibold text-gray-800">Table Relationships</h2>
              <p className="text-xs text-gray-500">Auto-detected JOIN keys between tables</p>
            </div>
          </div>
          <div className="text-sm text-gray-500">
            {relationships.length} found
          </div>
        </div>

        <div className="p-6">
          {hasIntegrityIssues && (
            <div className="mb-4 bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
              <div>
                <div className="font-medium text-amber-700">Relationships may be unreliable</div>
                <div className="text-sm text-amber-600">
                  Data integrity issues detected. Fix header detection and re-upload files before trusting these relationships.
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-gray-800">{stats?.tables_analyzed || 0}</div>
              <div className="text-sm text-gray-500">Tables</div>
            </div>
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-600">{relationships.length}</div>
              <div className="text-sm text-blue-600">Relationships</div>
            </div>
            <div className="bg-green-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-600">{autoMatched.length}</div>
              <div className="text-sm text-green-600">Auto-matched</div>
            </div>
            <div className={`rounded-lg p-4 text-center ${needsReview.length > 0 ? 'bg-amber-50' : 'bg-green-50'}`}>
              <div className={`text-2xl font-bold ${needsReview.length > 0 ? 'text-amber-600' : 'text-green-600'}`}>
                {needsReview.length}
              </div>
              <div className={`text-sm ${needsReview.length > 0 ? 'text-amber-600' : 'text-green-600'}`}>
                Needs Review
              </div>
            </div>
          </div>

          <CollapsibleSection
            title="High Confidence Matches"
            count={autoMatched.length}
            icon={<CheckCircle className="w-5 h-5 text-green-500" />}
            expanded={showHighConfidence}
            onToggle={() => setShowHighConfidence(!showHighConfidence)}
          >
            <div className="max-h-80 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">Source</th>
                    <th className="px-4 py-2 w-10"></th>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">Target</th>
                    <th className="text-right px-4 py-2 font-medium text-gray-600">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {autoMatched.slice(0, 50).map((rel, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2">
                        <span className="text-gray-500">{rel.source_table}.</span>
                        <span className="font-medium">{rel.source_column}</span>
                      </td>
                      <td className="px-4 py-2 text-center">
                        <Link2 className="w-4 h-4 text-gray-300" />
                      </td>
                      <td className="px-4 py-2">
                        <span className="text-gray-500">{rel.target_table}.</span>
                        <span className="font-medium">{rel.target_column}</span>
                      </td>
                      <td className="px-4 py-2 text-right">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          rel.confidence >= 0.95 ? 'bg-green-100 text-green-700' :
                          rel.confidence >= 0.85 ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {Math.round(rel.confidence * 100)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                  {autoMatched.length > 50 && (
                    <tr>
                      <td colSpan={4} className="px-4 py-2 text-center text-gray-400 text-sm">
                        +{autoMatched.length - 50} more matches
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CollapsibleSection>

          {needsReview.length > 0 && (
            <CollapsibleSection
              title="Needs Review"
              count={needsReview.length}
              icon={<AlertTriangle className="w-5 h-5 text-amber-500" />}
              expanded={showNeedsReview}
              onToggle={() => setShowNeedsReview(!showNeedsReview)}
            >
              <div className="max-h-80 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="text-left px-4 py-2 font-medium text-gray-600">Source</th>
                      <th className="px-4 py-2 w-10"></th>
                      <th className="text-left px-4 py-2 font-medium text-gray-600">Target</th>
                      <th className="text-right px-4 py-2 font-medium text-gray-600">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {needsReview.map((rel, i) => (
                      <tr key={i} className="hover:bg-amber-50">
                        <td className="px-4 py-2">
                          <span className="text-gray-500">{rel.source_table}.</span>
                          <span className="font-medium">{rel.source_column}</span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <Link2 className="w-4 h-4 text-amber-300" />
                        </td>
                        <td className="px-4 py-2">
                          <span className="text-gray-500">{rel.target_table}.</span>
                          <span className="font-medium">{rel.target_column}</span>
                        </td>
                        <td className="px-4 py-2 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => confirmRelationship(rel, true)}
                              className="p-1 rounded hover:bg-green-100 text-green-600"
                              title="Confirm"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => confirmRelationship(rel, false)}
                              className="p-1 rounded hover:bg-red-100 text-red-600"
                              title="Reject"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CollapsibleSection>
          )}

          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-700">
            <div className="flex items-start gap-2">
              <HelpCircle className="w-4 h-4 mt-0.5" />
              <div>
                <strong>How relationships improve chat queries:</strong>
                <p className="mt-1">
                  When you ask questions like "Show employees hired in 2024 with earnings over $100K", 
                  the system uses these relationships to JOIN data across your uploaded files automatically.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


// ==================== HELPER COMPONENTS ====================

function CollapsibleSection({ title, count, icon, expanded, onToggle, children }) {
  return (
    <div className="border rounded-lg overflow-hidden mb-4">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 bg-gray-50 flex items-center justify-between hover:bg-gray-100"
      >
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          {icon}
          <span className="font-medium text-gray-700">{title}</span>
          <span className="text-sm text-gray-500">({count})</span>
        </div>
      </button>
      {expanded && (
        <div className="border-t">
          {children}
        </div>
      )}
    </div>
  );
}
