/**
 * DataModelPage - Simplified Relationship Review + ERD
 * 
 * All sections COLLAPSED by default
 * ERD only shows QUESTIONABLE matches (not everything)
 * 
 * Deploy to: frontend/src/pages/DataModelPage.jsx
 */

import React, { useState, useEffect, useRef } from 'react';
import { useProject } from '../context/ProjectContext';
import { 
  CheckCircle, AlertTriangle, RefreshCw, Zap, ChevronDown, ChevronRight,
  Database, Link2, Eye, EyeOff, X, Check, HelpCircle
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
  
  // ALL sections collapsed by default
  const [showERD, setShowERD] = useState(false);
  const [showHighConfidence, setShowHighConfidence] = useState(false);
  const [showNeedsReview, setShowNeedsReview] = useState(false);
  const [showSemanticTypes, setShowSemanticTypes] = useState(false);

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
  };

  const rejectRelationship = (rel) => {
    setRelationships(prev => prev.filter(r => r !== rel));
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
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Data Model</h1>
            <p className="text-sm text-gray-500 mt-1">
              {activeProject.name} • Auto-detect relationships between uploaded tables
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            {/* ERD Button - Only shows questionable matches */}
            {analyzed && needsReview.length > 0 && (
              <button
                onClick={() => setShowERD(!showERD)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  showERD 
                    ? 'bg-purple-600 text-white hover:bg-purple-700' 
                    : 'bg-purple-100 text-purple-700 hover:bg-purple-200 border border-purple-300'
                }`}
              >
                {showERD ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                {showERD ? 'Hide ERD' : '🔗 Visual ERD'}
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

      <div className="max-w-6xl mx-auto p-6">
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
          <div className="space-y-4">
            
            {/* Summary Stats Row */}
            <div className="grid grid-cols-5 gap-4">
              <StatCard label="Tables" value={stats?.tables_analyzed || 0} />
              <StatCard label="Columns" value={stats?.columns_analyzed || 0} />
              <StatCard label="Relationships" value={relationships.length} color="blue" />
              <StatCard label="Auto-matched" value={autoMatched.length} color="green" />
              <StatCard label="Needs Review" value={needsReview.length} color={needsReview.length > 0 ? 'amber' : 'green'} />
            </div>

            {/* ERD View - Only Questionable Matches */}
            {showERD && needsReview.length > 0 && (
              <div className="bg-white rounded-xl border overflow-hidden">
                <div className="px-6 py-4 border-b bg-amber-50 flex items-center justify-between">
                  <div>
                    <h2 className="font-semibold text-amber-800">Questionable Relationships</h2>
                    <p className="text-sm text-amber-600">Drag tables to rearrange • Only showing uncertain matches</p>
                  </div>
                  <div className="text-sm font-medium text-amber-700">
                    {needsReview.length} to review
                  </div>
                </div>
                <ERDCanvas relationships={needsReview} />
              </div>
            )}

            {/* High Confidence Matches - COLLAPSED */}
            <CollapsibleSection
              title="High Confidence Matches"
              count={autoMatched.length}
              icon={<CheckCircle className="w-5 h-5 text-green-500" />}
              badge="Auto-accepted"
              badgeColor="green"
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
                    {autoMatched.slice(0, 100).map((rel, i) => (
                      <RelationshipRow key={i} rel={rel} />
                    ))}
                    {autoMatched.length > 100 && (
                      <tr>
                        <td colSpan={4} className="px-4 py-2 text-center text-gray-400 text-sm">
                          +{autoMatched.length - 100} more matches
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CollapsibleSection>

            {/* Needs Review - COLLAPSED */}
            <CollapsibleSection
              title="Needs Review"
              count={needsReview.length}
              icon={<AlertTriangle className="w-5 h-5 text-amber-500" />}
              badge="Confirm or reject"
              badgeColor="amber"
              expanded={showNeedsReview}
              onToggle={() => setShowNeedsReview(!showNeedsReview)}
            >
              <div className="max-h-96 overflow-y-auto divide-y">
                {needsReview.slice(0, 50).map((rel, i) => (
                  <ReviewCard 
                    key={i} 
                    rel={rel}
                    onConfirm={() => confirmRelationship(rel, true)}
                    onReject={() => rejectRelationship(rel)}
                  />
                ))}
                {needsReview.length > 50 && (
                  <div className="px-4 py-3 text-center text-gray-400 text-sm bg-gray-50">
                    +{needsReview.length - 50} more items to review
                  </div>
                )}
              </div>
            </CollapsibleSection>

            {/* Semantic Types - COLLAPSED */}
            {semanticTypes.length > 0 && (
              <CollapsibleSection
                title="Semantic Types Detected"
                count={`${semanticTypes.length} columns`}
                icon={<Database className="w-5 h-5 text-purple-500" />}
                expanded={showSemanticTypes}
                onToggle={() => setShowSemanticTypes(!showSemanticTypes)}
              >
                <div className="p-4 max-h-64 overflow-y-auto">
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(groupByType(semanticTypes)).map(([type, items]) => (
                      <div key={type} className="px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm">
                        {type}: {items.length}
                      </div>
                    ))}
                  </div>
                </div>
              </CollapsibleSection>
            )}

            {/* Help Text */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <HelpCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-blue-800">How relationships improve chat queries:</h4>
                  <p className="text-sm text-blue-700 mt-1">
                    When you ask questions like "Show employees hired in 2024 with earnings over $100K", 
                    the system uses these relationships to JOIN data across your uploaded files automatically. 
                    Confirming matches ensures accurate cross-table queries.
                  </p>
                </div>
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}


// Stat Card Component
function StatCard({ label, value, color = 'gray' }) {
  const colors = {
    gray: 'text-gray-900',
    blue: 'text-blue-600',
    green: 'text-green-600',
    amber: 'text-amber-600',
  };
  
  return (
    <div className="bg-white rounded-xl border p-4 text-center">
      <div className={`text-2xl font-bold ${colors[color]}`}>{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
}


// Collapsible Section Component
function CollapsibleSection({ title, count, icon, badge, badgeColor, expanded, onToggle, children }) {
  const badgeColors = {
    green: 'text-green-600',
    amber: 'text-amber-600',
    blue: 'text-blue-600',
  };
  
  return (
    <div className="bg-white rounded-xl border overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />}
          {icon}
          <span className="font-medium text-gray-800">{title}</span>
          <span className="text-gray-400">({count})</span>
        </div>
        {badge && (
          <span className={`text-sm ${badgeColors[badgeColor] || 'text-gray-500'}`}>
            {badge}
          </span>
        )}
      </button>
      
      {expanded && (
        <div className="border-t">
          {children}
        </div>
      )}
    </div>
  );
}


// Relationship Row (for table view)
function RelationshipRow({ rel }) {
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-2">
        <div className="font-medium text-gray-900 text-xs">{getShortTableName(rel.source_table)}</div>
        <div className="text-blue-600 font-mono text-xs">{rel.source_column}</div>
      </td>
      <td className="px-4 py-2 text-gray-300">
        <Link2 className="w-4 h-4" />
      </td>
      <td className="px-4 py-2">
        <div className="font-medium text-gray-900 text-xs">{getShortTableName(rel.target_table)}</div>
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
  );
}


// Review Card with actions
function ReviewCard({ rel, onConfirm, onReject }) {
  return (
    <div className="px-4 py-3 flex items-center justify-between hover:bg-gray-50">
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-mono text-blue-600 truncate">{rel.source_column}</span>
            <span className="text-gray-400">in</span>
            <span className="text-gray-600 truncate">{getShortTableName(rel.source_table)}</span>
          </div>
        </div>
        
        <div className="text-amber-400 px-2">↔</div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-mono text-blue-600 truncate">{rel.target_column}</span>
            <span className="text-gray-400">in</span>
            <span className="text-gray-600 truncate">{getShortTableName(rel.target_table)}</span>
          </div>
        </div>
        
        <span className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${
          rel.confidence >= 0.7 ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'
        }`}>
          {Math.round(rel.confidence * 100)}%
        </span>
      </div>
      
      <div className="flex items-center gap-2 ml-4 flex-shrink-0">
        <button
          onClick={onConfirm}
          className="p-1.5 rounded bg-green-100 text-green-600 hover:bg-green-200"
          title="Yes, same data"
        >
          <Check className="w-4 h-4" />
        </button>
        <button
          onClick={onReject}
          className="p-1.5 rounded bg-red-100 text-red-600 hover:bg-red-200"
          title="No, different data"
        >
          <X className="w-4 h-4" />
        </button>
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


// Group semantic types by type
function groupByType(semanticTypes) {
  return semanticTypes.reduce((acc, item) => {
    const type = item.type || 'unknown';
    if (!acc[type]) acc[type] = [];
    acc[type].push(item);
    return acc;
  }, {});
}


// ERD Canvas - Shows only passed relationships (questionable ones)
function ERDCanvas({ relationships }) {
  const canvasRef = useRef(null);
  const [tables, setTables] = useState([]);
  const [positions, setPositions] = useState({});
  const [dragging, setDragging] = useState(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

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
    
    // Grid layout
    const cols = Math.ceil(Math.sqrt(tableList.length));
    const newPositions = {};
    tableList.forEach((t, i) => {
      newPositions[t.name] = {
        x: 50 + (i % cols) * 300,
        y: 50 + Math.floor(i / cols) * 200
      };
    });
    setPositions(newPositions);
  }, [relationships]);

  const handleMouseDown = (e, tableName) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    setDragging(tableName);
    setOffset({
      x: e.clientX - rect.left - positions[tableName].x,
      y: e.clientY - rect.top - positions[tableName].y
    });
  };

  const handleMouseMove = (e) => {
    if (!dragging || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    setPositions(prev => ({
      ...prev,
      [dragging]: {
        x: Math.max(0, e.clientX - rect.left - offset.x),
        y: Math.max(0, e.clientY - rect.top - offset.y)
      }
    }));
  };

  const handleMouseUp = () => setDragging(null);

  const getLineCoords = (rel) => {
    const source = positions[rel.source_table];
    const target = positions[rel.target_table];
    if (!source || !target) return null;
    
    return {
      x1: source.x + 260,
      y1: source.y + 60,
      x2: target.x,
      y2: target.y + 60
    };
  };

  if (tables.length === 0) {
    return (
      <div className="p-12 text-center text-gray-500">
        <Database className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>No questionable relationships to visualize.</p>
      </div>
    );
  }

  return (
    <div 
      ref={canvasRef}
      className="relative bg-slate-50 overflow-auto cursor-grab"
      style={{ height: '450px', minWidth: '100%' }}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Connection Lines */}
      <svg 
        className="absolute inset-0 pointer-events-none" 
        style={{ width: '2000px', height: '1000px' }}
      >
        {relationships.map((rel, i) => {
          const coords = getLineCoords(rel);
          if (!coords) return null;
          return (
            <g key={i}>
              <line
                x1={coords.x1}
                y1={coords.y1}
                x2={coords.x2}
                y2={coords.y2}
                stroke="#f59e0b"
                strokeWidth={2}
                strokeDasharray="6,4"
                opacity={0.7}
              />
              {/* Question mark at midpoint */}
              <text 
                x={(coords.x1 + coords.x2) / 2} 
                y={(coords.y1 + coords.y2) / 2 - 5}
                fill="#d97706"
                fontSize="16"
                fontWeight="bold"
                textAnchor="middle"
              >
                ?
              </text>
            </g>
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
            className="absolute bg-white border-2 border-amber-300 rounded-lg shadow-md cursor-move select-none"
            style={{ 
              left: pos.x, 
              top: pos.y, 
              width: 260,
              zIndex: dragging === table.name ? 10 : 1
            }}
            onMouseDown={(e) => handleMouseDown(e, table.name)}
          >
            <div className="px-3 py-2 bg-amber-500 text-white rounded-t-md text-sm font-medium truncate">
              {getShortTableName(table.name)}
            </div>
            <div className="p-2 text-xs space-y-1">
              {table.columns.map(col => (
                <div key={col} className="text-amber-700 font-mono bg-amber-50 px-2 py-1 rounded">
                  {col}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
