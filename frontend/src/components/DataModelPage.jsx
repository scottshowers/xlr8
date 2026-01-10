/**
 * DataModelPage - Data Integrity
 * 
 * Shows table health, flags bad columns, header issues.
 * Relationship analysis has moved to Context Graph in Data Explorer.
 * 
 * Updated: January 10, 2026
 */

import React, { useState, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';
import { 
  RefreshCw, ChevronDown, ChevronRight, Database, Link2,
  AlertCircle, Table2, FileWarning, CheckCircle2, Loader2
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

  // Load data integrity on mount
  useEffect(() => {
    if (activeProject?.name) {
      loadDataIntegrity();
    }
  }, [activeProject?.name]);

  // ==================== DATA INTEGRITY ====================
  const loadDataIntegrity = async () => {
    setIntegrityLoading(true);
    try {
      // Use platform endpoint instead of status/data-integrity
      const res = await fetch(`${API_BASE}/api/platform?project=${encodeURIComponent(activeProject?.id || '')}`);
      if (res.ok) {
        const data = await res.json();
        // Map platform response to expected integrity format
        setIntegrityData({
          duckdb: { connected: data.health?.services?.duckdb?.status === 'healthy', latency_ms: data.health?.services?.duckdb?.latency_ms },
          chromadb: { connected: data.health?.services?.chromadb?.status === 'healthy', latency_ms: data.health?.services?.chromadb?.latency_ms },
          supabase: { connected: data.health?.services?.supabase?.status === 'healthy', latency_ms: data.health?.services?.supabase?.latency_ms },
          ollama: { connected: data.health?.services?.ollama?.status === 'healthy', latency_ms: data.health?.services?.ollama?.latency_ms },
          tables: data.stats?.tables || 0,
          rows: data.stats?.rows || 0,
          chunks: data.stats?.chunks || 0
        });
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
      // Use classification endpoint instead of status/table-profile
      const res = await fetch(`${API_BASE}/api/classification/table/${encodeURIComponent(tableName)}`);
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
          <p className="text-sm text-gray-500">{activeProject.name} • Data Integrity</p>
        </div>
        <button
          onClick={() => loadDataIntegrity()}
          disabled={integrityLoading}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 disabled:opacity-50"
        >
          {integrityLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Refresh
        </button>
      </div>

      {/* ==================== DATA INTEGRITY SECTION ==================== */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Database className="w-5 h-5 text-blue-500" />
            <div>
              <h2 className="font-semibold text-gray-800">Data Integrity</h2>
              <p className="text-xs text-gray-500">Verify tables loaded correctly</p>
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

      {/* ==================== CONTEXT GRAPH NOTICE ==================== */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link2 className="w-5 h-5 text-purple-500" />
            <div>
              <h2 className="font-semibold text-gray-800">Table Relationships</h2>
              <p className="text-xs text-gray-500">Hub/spoke relationships for intelligent queries</p>
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
            <Database className="w-5 h-5 text-blue-500 mt-0.5" />
            <div>
              <div className="font-medium text-blue-700">View in Data Explorer</div>
              <div className="text-sm text-blue-600 mt-1">
                Table relationships are now shown in the <strong>Context Graph</strong> tab in Data Explorer.
                The Context Graph shows hub/spoke relationships that power intelligent JOINs and queries.
              </div>
              <a 
                href="/data-explorer" 
                className="inline-block mt-3 px-4 py-2 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600"
              >
                Open Data Explorer →
              </a>
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
