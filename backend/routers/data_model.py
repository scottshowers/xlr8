/**
 * DataModelPage - Simplified Relationship Review + ERD
 * 
 * Primary View: Clean summary + just the items needing review
 * Advanced View: Full ERD for power users / sales demos
 * 
 * Deploy to: frontend/src/pages/DataModelPage.jsx
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useProject } from '../context/ProjectContext';
import { 
  CheckCircle, AlertTriangle, RefreshCw, Zap, ChevronDown, ChevronRight,
  Database, Link2, Eye, EyeOff, X, Check
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function DataModelPage() {
  const { activeProject } = useProject();
  const [loading, setLoading] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);
  const [relationships, setRelationships] = useState([]);
  const [semanticTypes, setSemanticTypes] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [showERD, setShowERD] = useState(false);
  const [showAutoMatched, setShowAutoMatched] = useState(false);

  // Separate relationships
  const needsReview = relationships.filter(r => r.needs_review && !r.confirmed);
  const autoMatched = relationships.filter(r => !r.needs_review || r.confirmed);

  const analyzeProject = async () => {
    if (!activeProject?.name) return;
    
    setLoading(true);
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
      setAnalyzed(true);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const confirmRelationship = (rel, confirmed) => {
    setRelationships(prev => prev.map(r => 
      r === rel ? { ...r, confirmed, needs_review: false } : r
    ));
    // TODO: POST to backend to persist
  };

  const rejectRelationship = (rel) => {
    setRelationships(prev => prev.filter(r => r !== rel));
    // TODO: DELETE to backend
  };

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
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Data Model</h1>
            <p className="text-sm text-gray-500 mt-1">
              {activeProject.name} • Auto-detect relationships between tables
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            {analyzed && (
              <button
                onClick={() => setShowERD(!showERD)}
                className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg text-sm"
              >
                {showERD ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                {showERD ? 'Hide' : 'Show'} ERD
              </button>
            )}
            <button
              onClick={analyzeProject}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
            >
              {loading ? (
                <><RefreshCw className="w-4 h-4 animate-spin" /> Analyzing...</>
              ) : (
                <><Zap className="w-4 h-4" /> {analyzed ? 'Re-analyze' : 'Analyze'}</>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto p-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Not analyzed yet */}
        {!analyzed && !loading && (
          <div className="bg-white rounded-xl border p-12 text-center">
            <Database className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <h2 className="text-xl font-semibold text-gray-700 mb-2">Ready to Analyze</h2>
            <p className="text-gray-500 mb-6 max-w-md mx-auto">
              Click "Analyze" to automatically detect relationships between your uploaded data files.
            </p>
          </div>
        )}

        {/* Results */}
        {analyzed && (
          <div className="space-y-6">
            
            {/* Summary Cards */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-xl border p-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-gray-900">{autoMatched.length}</div>
                    <div className="text-sm text-gray-500">Auto-matched</div>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-xl border p-6">
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                    needsReview.length > 0 ? 'bg-amber-100' : 'bg-green-100'
                  }`}>
                    {needsReview.length > 0 ? (
                      <AlertTriangle className="w-6 h-6 text-amber-600" />
                    ) : (
                      <CheckCircle className="w-6 h-6 text-green-600" />
                    )}
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-gray-900">{needsReview.length}</div>
                    <div className="text-sm text-gray-500">
                      {needsReview.length > 0 ? 'Need review' : 'All confirmed!'}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Needs Review Section */}
            {needsReview.length > 0 && (
              <div className="bg-white rounded-xl border overflow-hidden">
                <div className="px-6 py-4 border-b bg-amber-50">
                  <h2 className="font-semibold text-amber-800">
                    Please confirm these relationships
                  </h2>
                  <p className="text-sm text-amber-600 mt-1">
                    We're not sure if these columns refer to the same data
                  </p>
                </div>
                
                <div className="divide-y">
                  {needsReview.map((rel, i) => (
                    <ReviewCard 
                      key={i} 
                      rel={rel}
                      onConfirm={() => confirmRelationship(rel, true)}
                      onReject={() => rejectRelationship(rel)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* All done message */}
            {needsReview.length === 0 && (
              <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
                <CheckCircle className="w-10 h-10 text-green-500 mx-auto mb-3" />
                <h3 className="font-semibold text-green-800">All relationships confirmed!</h3>
                <p className="text-sm text-green-600 mt-1">
                  Your data model is ready. Chat queries will use these connections automatically.
                </p>
              </div>
            )}

            {/* Collapsed Auto-matched Section */}
            <div className="bg-white rounded-xl border overflow-hidden">
              <button
                onClick={() => setShowAutoMatched(!showAutoMatched)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {showAutoMatched ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                  <span className="font-medium">View {autoMatched.length} auto-detected relationships</span>
                </div>
                <span className="text-sm text-gray-400">Click to {showAutoMatched ? 'hide' : 'expand'}</span>
              </button>
              
              {showAutoMatched && (
                <div className="border-t max-h-96 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="text-left px-4 py-2 font-medium text-gray-600">Source</th>
                        <th className="px-4 py-2"></th>
                        <th className="text-left px-4 py-2 font-medium text-gray-600">Target</th>
                        <th className="text-right px-4 py-2 font-medium text-gray-600">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {autoMatched.map((rel, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-4 py-2">
                            <div className="font-medium text-gray-900">{getShortTableName(rel.source_table)}</div>
                            <div className="text-blue-600 font-mono text-xs">{rel.source_column}</div>
                          </td>
                          <td className="px-4 py-2 text-gray-300">
                            <Link2 className="w-4 h-4" />
                          </td>
                          <td className="px-4 py-2">
                            <div className="font-medium text-gray-900">{getShortTableName(rel.target_table)}</div>
                            <div className="text-blue-600 font-mono text-xs">{rel.target_column}</div>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                              rel.confidence >= 0.9 ? 'bg-green-100 text-green-700' :
                              rel.confidence >= 0.7 ? 'bg-blue-100 text-blue-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {Math.round(rel.confidence * 100)}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* ERD View (Advanced) */}
            {showERD && (
              <div className="bg-white rounded-xl border overflow-hidden">
                <div className="px-6 py-4 border-b bg-gray-50 flex items-center justify-between">
                  <div>
                    <h2 className="font-semibold">Entity Relationship Diagram</h2>
                    <p className="text-sm text-gray-500">Drag tables to rearrange • Scroll to zoom</p>
                  </div>
                </div>
                <ERDCanvas 
                  relationships={relationships}
                  stats={stats}
                />
              </div>
            )}

          </div>
        )}
      </div>
    </div>
  );
}


// Helper to shorten table names
function getShortTableName(fullName) {
  if (!fullName) return '';
  const parts = fullName.split('__');
  return parts.length > 2 ? parts[parts.length - 1] : parts[parts.length - 1] || fullName;
}


// Review Card with mini ERD
function ReviewCard({ rel, onConfirm, onReject }) {
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-gray-500">
          Is <span className="font-mono font-semibold text-gray-800">{rel.source_column}</span> the same as <span className="font-mono font-semibold text-gray-800">{rel.target_column}</span>?
        </div>
        <div className="text-xs text-gray-400">
          {Math.round(rel.confidence * 100)}% match
        </div>
      </div>
      
      {/* Mini ERD */}
      <div className="flex items-center justify-center gap-4 mb-6">
        <div className="bg-gray-50 border rounded-lg p-3 min-w-[160px]">
          <div className="text-xs text-gray-400 mb-1">Table</div>
          <div className="font-medium text-sm truncate" title={rel.source_table}>
            {getShortTableName(rel.source_table)}
          </div>
          <div className="mt-2 text-xs text-gray-400">Column</div>
          <div className="font-mono text-blue-600 text-sm">{rel.source_column}</div>
        </div>
        
        <div className="flex flex-col items-center">
          <div className="text-amber-500 text-lg">?</div>
          <div className="w-16 border-t-2 border-dashed border-amber-300"></div>
        </div>
        
        <div className="bg-gray-50 border rounded-lg p-3 min-w-[160px]">
          <div className="text-xs text-gray-400 mb-1">Table</div>
          <div className="font-medium text-sm truncate" title={rel.target_table}>
            {getShortTableName(rel.target_table)}
          </div>
          <div className="mt-2 text-xs text-gray-400">Column</div>
          <div className="font-mono text-blue-600 text-sm">{rel.target_column}</div>
        </div>
      </div>
      
      {/* Actions */}
      <div className="flex gap-3 justify-center">
        <button
          onClick={onConfirm}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
        >
          <Check className="w-4 h-4" /> Yes, same data
        </button>
        <button
          onClick={onReject}
          className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium"
        >
          <X className="w-4 h-4" /> No, different
        </button>
      </div>
    </div>
  );
}


// Full ERD Canvas (for power users / demos)
function ERDCanvas({ relationships, stats }) {
  const canvasRef = useRef(null);
  const [tables, setTables] = useState([]);
  const [positions, setPositions] = useState({});
  const [dragging, setDragging] = useState(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  // Extract unique tables from relationships
  useEffect(() => {
    const tableSet = new Set();
    const tableColumns = {};
    
    relationships.forEach(rel => {
      tableSet.add(rel.source_table);
      tableSet.add(rel.target_table);
      
      if (!tableColumns[rel.source_table]) tableColumns[rel.source_table] = new Set();
      if (!tableColumns[rel.target_table]) tableColumns[rel.target_table] = new Set();
      
      tableColumns[rel.source_table].add(rel.source_column);
      tableColumns[rel.target_table].add(rel.target_column);
    });
    
    const tableList = Array.from(tableSet).map(name => ({
      name,
      columns: Array.from(tableColumns[name] || [])
    }));
    
    setTables(tableList);
    
    // Initialize positions in grid
    const cols = Math.ceil(Math.sqrt(tableList.length));
    const newPositions = {};
    tableList.forEach((t, i) => {
      newPositions[t.name] = {
        x: 50 + (i % cols) * 280,
        y: 50 + Math.floor(i / cols) * 180
      };
    });
    setPositions(newPositions);
  }, [relationships]);

  const handleMouseDown = (e, tableName) => {
    const rect = canvasRef.current.getBoundingClientRect();
    setDragging(tableName);
    setOffset({
      x: e.clientX - rect.left - positions[tableName].x,
      y: e.clientY - rect.top - positions[tableName].y
    });
  };

  const handleMouseMove = (e) => {
    if (!dragging) return;
    const rect = canvasRef.current.getBoundingClientRect();
    setPositions(prev => ({
      ...prev,
      [dragging]: {
        x: e.clientX - rect.left - offset.x,
        y: e.clientY - rect.top - offset.y
      }
    }));
  };

  const handleMouseUp = () => setDragging(null);

  // Get line coordinates
  const getLineCoords = (rel) => {
    const source = positions[rel.source_table];
    const target = positions[rel.target_table];
    if (!source || !target) return null;
    
    return {
      x1: source.x + 240,
      y1: source.y + 50,
      x2: target.x,
      y2: target.y + 50
    };
  };

  return (
    <div 
      ref={canvasRef}
      className="relative bg-gray-50 overflow-auto"
      style={{ height: '500px', minWidth: '100%' }}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* SVG Lines */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ minWidth: '1500px', minHeight: '800px' }}>
        {relationships.map((rel, i) => {
          const coords = getLineCoords(rel);
          if (!coords) return null;
          return (
            <line
              key={i}
              x1={coords.x1}
              y1={coords.y1}
              x2={coords.x2}
              y2={coords.y2}
              stroke={rel.needs_review ? '#f59e0b' : '#3b82f6'}
              strokeWidth={rel.needs_review ? 2 : 1.5}
              strokeDasharray={rel.needs_review ? '5,5' : 'none'}
              opacity={0.6}
            />
          );
        })}
      </svg>

      {/* Table Boxes */}
      {tables.map(table => {
        const pos = positions[table.name];
        if (!pos) return null;
        
        return (
          <div
            key={table.name}
            className="absolute bg-white border rounded-lg shadow-sm cursor-move select-none"
            style={{ 
              left: pos.x, 
              top: pos.y, 
              width: 240,
              zIndex: dragging === table.name ? 10 : 1
            }}
            onMouseDown={(e) => handleMouseDown(e, table.name)}
          >
            <div className="px-3 py-2 bg-slate-800 text-white rounded-t-lg text-sm font-medium truncate">
              {getShortTableName(table.name)}
            </div>
            <div className="p-2 text-xs space-y-1 max-h-32 overflow-y-auto">
              {table.columns.slice(0, 8).map(col => (
                <div key={col} className="text-gray-600 truncate font-mono">
                  {col}
                </div>
              ))}
              {table.columns.length > 8 && (
                <div className="text-gray-400 italic">+{table.columns.length - 8} more</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
