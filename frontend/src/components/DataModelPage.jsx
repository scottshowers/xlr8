/**
 * DataModelPage - Simplified Relationship Review
 * 
 * Features:
 * - One-click "Analyze" to detect relationships
 * - List-based review (not overwhelming ERD)
 * - High confidence auto-accepted
 * - Uncertain matches shown for review
 * - Semantic type badges
 * - Unmatched key columns highlighted
 * 
 * Deploy to: frontend/src/pages/DataModelPage.jsx
 */

import React, { useState, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';
import { 
  Search, CheckCircle, XCircle, AlertTriangle, 
  Link2, Unlink, RefreshCw, ChevronDown, ChevronRight,
  Database, Columns, Zap, HelpCircle
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Semantic type colors
const TYPE_COLORS = {
  employee_id: { bg: '#dbeafe', text: '#1e40af', label: 'Employee ID' },
  company_code: { bg: '#fce7f3', text: '#9d174d', label: 'Company' },
  department: { bg: '#d1fae5', text: '#065f46', label: 'Department' },
  job_code: { bg: '#fef3c7', text: '#92400e', label: 'Job Code' },
  location: { bg: '#e0e7ff', text: '#3730a3', label: 'Location' },
  date: { bg: '#f3e8ff', text: '#6b21a8', label: 'Date' },
  amount: { bg: '#dcfce7', text: '#166534', label: 'Amount' },
  rate: { bg: '#ffedd5', text: '#9a3412', label: 'Rate' },
  hours: { bg: '#cffafe', text: '#0e7490', label: 'Hours' },
  status: { bg: '#fef9c3', text: '#854d0e', label: 'Status' },
  earning_code: { bg: '#dcfce7', text: '#166534', label: 'Earning' },
  deduction_code: { bg: '#fee2e2', text: '#991b1b', label: 'Deduction' },
  tax_code: { bg: '#fed7aa', text: '#9a3412', label: 'Tax' },
  unknown: { bg: '#f1f5f9', text: '#475569', label: 'Unknown' }
};

export default function DataModelPage() {
  const { activeProject } = useProject();
  const [loading, setLoading] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);
  const [relationships, setRelationships] = useState([]);
  const [semanticTypes, setSemanticTypes] = useState([]);
  const [unmatchedColumns, setUnmatchedColumns] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [expandedSections, setExpandedSections] = useState({
    highConfidence: true,
    needsReview: true,
    semantic: false,
    unmatched: false
  });
  const [filter, setFilter] = useState('all'); // all, confirmed, review

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const analyzeProject = async () => {
    if (!activeProject?.name) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/data-model/analyze/${encodeURIComponent(activeProject.name)}`, {
        method: 'POST'
      });
      
      if (!res.ok) {
        throw new Error(`Analysis failed: ${res.status}`);
      }
      
      const data = await res.json();
      setRelationships(data.relationships || []);
      setSemanticTypes(data.semantic_types || []);
      setUnmatchedColumns(data.unmatched_columns || []);
      setStats(data.stats || null);
      setAnalyzed(true);
      
    } catch (err) {
      console.error('Analysis failed:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const confirmRelationship = async (rel, confirmed) => {
    try {
      await fetch(`${API_BASE}/api/data-model/relationships/${encodeURIComponent(activeProject.name)}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_table: rel.source_table,
          source_column: rel.source_column,
          target_table: rel.target_table,
          target_column: rel.target_column,
          confirmed
        })
      });
      
      // Update local state
      setRelationships(prev => prev.map(r => 
        r === rel ? { ...r, confirmed, needs_review: false } : r
      ));
    } catch (err) {
      console.error('Failed to confirm:', err);
    }
  };

  const removeRelationship = async (rel) => {
    setRelationships(prev => prev.filter(r => r !== rel));
  };

  // Group relationships
  const highConfidence = relationships.filter(r => r.confidence >= 0.85 && !r.needs_review);
  const needsReview = relationships.filter(r => r.needs_review);
  const confirmed = relationships.filter(r => r.confirmed);

  // Group semantic types by type
  const semanticByType = semanticTypes.reduce((acc, st) => {
    if (!acc[st.type]) acc[st.type] = [];
    acc[st.type].push(st);
    return acc;
  }, {});

  if (!activeProject) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <Database className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>Select a project from the header to analyze data relationships.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Data Model</h1>
            <p className="text-sm text-gray-500 mt-1">
              {activeProject.name} • Auto-detect relationships between uploaded tables
            </p>
          </div>
          
          <button
            onClick={analyzeProject}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {loading ? (
              <><RefreshCw className="w-4 h-4 animate-spin" /> Analyzing...</>
            ) : (
              <><Zap className="w-4 h-4" /> {analyzed ? 'Re-analyze' : 'Analyze Tables'}</>
            )}
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-6">
        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Stats Summary */}
        {stats && (
          <div className="mb-6 grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-white rounded-lg p-4 border">
              <div className="text-2xl font-bold text-gray-900">{stats.tables_analyzed}</div>
              <div className="text-sm text-gray-500">Tables</div>
            </div>
            <div className="bg-white rounded-lg p-4 border">
              <div className="text-2xl font-bold text-gray-900">{stats.columns_analyzed}</div>
              <div className="text-sm text-gray-500">Columns</div>
            </div>
            <div className="bg-white rounded-lg p-4 border">
              <div className="text-2xl font-bold text-blue-600">{stats.relationships_found}</div>
              <div className="text-sm text-gray-500">Relationships</div>
            </div>
            <div className="bg-white rounded-lg p-4 border">
              <div className="text-2xl font-bold text-green-600">{stats.high_confidence}</div>
              <div className="text-sm text-gray-500">Auto-matched</div>
            </div>
            <div className="bg-white rounded-lg p-4 border">
              <div className="text-2xl font-bold text-amber-600">{stats.needs_review}</div>
              <div className="text-sm text-gray-500">Needs Review</div>
            </div>
          </div>
        )}

        {/* Not analyzed yet */}
        {!analyzed && !loading && (
          <div className="bg-white rounded-lg border p-12 text-center">
            <Database className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <h2 className="text-xl font-semibold text-gray-700 mb-2">Ready to Analyze</h2>
            <p className="text-gray-500 mb-6 max-w-md mx-auto">
              Click "Analyze Tables" to automatically detect relationships between your uploaded data files.
              The system will identify matching columns and suggest JOINs.
            </p>
            <div className="flex items-center justify-center gap-6 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <CheckCircle className="w-4 h-4 text-green-500" /> Rule-based matching
              </span>
              <span className="flex items-center gap-1">
                <Zap className="w-4 h-4 text-blue-500" /> AI-assisted analysis
              </span>
              <span className="flex items-center gap-1">
                <Link2 className="w-4 h-4 text-purple-500" /> Semantic detection
              </span>
            </div>
          </div>
        )}

        {/* Results */}
        {analyzed && (
          <div className="space-y-6">
            
            {/* High Confidence Matches */}
            <div className="bg-white rounded-lg border">
              <button
                onClick={() => toggleSection('highConfidence')}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50"
              >
                <div className="flex items-center gap-2">
                  {expandedSections.highConfidence ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                  <CheckCircle className="w-5 h-5 text-green-500" />
                  <span className="font-semibold">High Confidence Matches</span>
                  <span className="text-sm text-gray-500">({highConfidence.length})</span>
                </div>
                <span className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded">Auto-accepted</span>
              </button>
              
              {expandedSections.highConfidence && highConfidence.length > 0 && (
                <div className="border-t divide-y">
                  {highConfidence.map((rel, i) => (
                    <RelationshipRow key={i} rel={rel} onRemove={() => removeRelationship(rel)} />
                  ))}
                </div>
              )}
              
              {expandedSections.highConfidence && highConfidence.length === 0 && (
                <div className="px-4 py-8 text-center text-gray-400 border-t">
                  No high-confidence matches found
                </div>
              )}
            </div>

            {/* Needs Review */}
            <div className="bg-white rounded-lg border">
              <button
                onClick={() => toggleSection('needsReview')}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50"
              >
                <div className="flex items-center gap-2">
                  {expandedSections.needsReview ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  <span className="font-semibold">Needs Review</span>
                  <span className="text-sm text-gray-500">({needsReview.length})</span>
                </div>
                <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">Confirm or reject</span>
              </button>
              
              {expandedSections.needsReview && needsReview.length > 0 && (
                <div className="border-t divide-y">
                  {needsReview.map((rel, i) => (
                    <RelationshipRow 
                      key={i} 
                      rel={rel} 
                      showActions
                      onConfirm={() => confirmRelationship(rel, true)}
                      onReject={() => confirmRelationship(rel, false)}
                      onRemove={() => removeRelationship(rel)}
                    />
                  ))}
                </div>
              )}
              
              {expandedSections.needsReview && needsReview.length === 0 && (
                <div className="px-4 py-8 text-center text-gray-400 border-t">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-400" />
                  All matches reviewed!
                </div>
              )}
            </div>

            {/* Semantic Types Detected */}
            <div className="bg-white rounded-lg border">
              <button
                onClick={() => toggleSection('semantic')}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50"
              >
                <div className="flex items-center gap-2">
                  {expandedSections.semantic ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                  <Columns className="w-5 h-5 text-purple-500" />
                  <span className="font-semibold">Semantic Types Detected</span>
                  <span className="text-sm text-gray-500">({semanticTypes.length} columns)</span>
                </div>
              </button>
              
              {expandedSections.semantic && Object.keys(semanticByType).length > 0 && (
                <div className="border-t p-4">
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Object.entries(semanticByType).map(([type, cols]) => {
                      const typeInfo = TYPE_COLORS[type] || TYPE_COLORS.unknown;
                      return (
                        <div key={type} className="border rounded-lg p-3">
                          <div 
                            className="inline-block px-2 py-1 rounded text-xs font-medium mb-2"
                            style={{ background: typeInfo.bg, color: typeInfo.text }}
                          >
                            {typeInfo.label} ({cols.length})
                          </div>
                          <div className="space-y-1">
                            {cols.slice(0, 5).map((col, i) => (
                              <div key={i} className="text-sm text-gray-600 truncate" title={`${col.table}.${col.column}`}>
                                <span className="text-gray-400">{col.table}.</span>
                                <span className="font-medium">{col.column}</span>
                              </div>
                            ))}
                            {cols.length > 5 && (
                              <div className="text-xs text-gray-400">+{cols.length - 5} more</div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Unmatched Key Columns */}
            {unmatchedColumns.length > 0 && (
              <div className="bg-white rounded-lg border">
                <button
                  onClick={() => toggleSection('unmatched')}
                  className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50"
                >
                  <div className="flex items-center gap-2">
                    {expandedSections.unmatched ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                    <Unlink className="w-5 h-5 text-red-500" />
                    <span className="font-semibold">Unmatched Key Columns</span>
                    <span className="text-sm text-gray-500">({unmatchedColumns.length})</span>
                  </div>
                  <span className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">May need manual mapping</span>
                </button>
                
                {expandedSections.unmatched && (
                  <div className="border-t p-4">
                    <p className="text-sm text-gray-500 mb-3">
                      These columns look like keys but couldn't be automatically matched to other tables.
                    </p>
                    <div className="space-y-2">
                      {unmatchedColumns.map((col, i) => {
                        const typeInfo = TYPE_COLORS[col.semantic_type] || TYPE_COLORS.unknown;
                        return (
                          <div key={i} className="flex items-center gap-3 p-2 bg-gray-50 rounded">
                            <span 
                              className="px-2 py-1 rounded text-xs font-medium"
                              style={{ background: typeInfo.bg, color: typeInfo.text }}
                            >
                              {typeInfo.label}
                            </span>
                            <span className="text-sm">
                              <span className="text-gray-400">{col.table}.</span>
                              <span className="font-medium text-gray-700">{col.column}</span>
                            </span>
                            <span className="text-xs text-gray-400 ml-auto">
                              {Math.round(col.confidence * 100)}% match
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

          </div>
        )}

        {/* Help Text */}
        <div className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-100">
          <div className="flex gap-3">
            <HelpCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <strong>How relationships improve chat queries:</strong>
              <p className="mt-1 text-blue-700">
                When you ask questions like "Show employees hired in 2024 with earnings over $100K", 
                the system uses these relationships to JOIN data across your uploaded files automatically.
                Confirming matches ensures accurate cross-table queries.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


// Relationship row component
function RelationshipRow({ rel, showActions, onConfirm, onReject, onRemove }) {
  const confidenceColor = rel.confidence >= 0.85 
    ? 'text-green-600 bg-green-50' 
    : rel.confidence >= 0.7 
      ? 'text-amber-600 bg-amber-50'
      : 'text-red-600 bg-red-50';
  
  const methodLabel = {
    exact: 'Exact match',
    fuzzy: 'Fuzzy match',
    llm: 'AI suggested',
    semantic: 'Same type',
    manual: 'Manual'
  }[rel.method] || rel.method;

  return (
    <div className="px-4 py-3 flex items-center gap-4 hover:bg-gray-50">
      {/* Source */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-900 truncate" title={rel.source_table}>
          {rel.source_table}
        </div>
        <div className="text-sm text-blue-600 font-mono truncate" title={rel.source_column}>
          {rel.source_column}
        </div>
      </div>
      
      {/* Arrow */}
      <div className="flex-shrink-0 text-gray-300">
        <Link2 className="w-5 h-5" />
      </div>
      
      {/* Target */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-900 truncate" title={rel.target_table}>
          {rel.target_table}
        </div>
        <div className="text-sm text-blue-600 font-mono truncate" title={rel.target_column}>
          {rel.target_column}
        </div>
      </div>
      
      {/* Confidence & Method */}
      <div className="flex-shrink-0 text-right">
        <div className={`text-sm font-medium px-2 py-0.5 rounded ${confidenceColor}`}>
          {Math.round(rel.confidence * 100)}%
        </div>
        <div className="text-xs text-gray-400 mt-1">{methodLabel}</div>
      </div>
      
      {/* Actions */}
      {showActions ? (
        <div className="flex-shrink-0 flex gap-2">
          <button
            onClick={onConfirm}
            className="p-1.5 text-green-600 hover:bg-green-50 rounded"
            title="Confirm match"
          >
            <CheckCircle className="w-5 h-5" />
          </button>
          <button
            onClick={onReject}
            className="p-1.5 text-red-600 hover:bg-red-50 rounded"
            title="Reject match"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>
      ) : (
        <div className="flex-shrink-0">
          <button
            onClick={onRemove}
            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
            title="Remove"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>
      )}
      
      {/* Confirmed badge */}
      {rel.confirmed && (
        <div className="flex-shrink-0">
          <span className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded">✓ Confirmed</span>
        </div>
      )}
    </div>
  );
}
