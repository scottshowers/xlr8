/**
 * Context Graph Visualization
 * 
 * Displays the hub/spoke relationships that power intelligent queries.
 * Shows semantic types, their hub tables, and related spoke tables.
 */

import React, { useState, useEffect } from 'react';
import { 
  Network, Database, Link2, ChevronDown, ChevronRight, 
  CheckCircle2, AlertCircle, Loader2, RefreshCw 
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || '';

export default function ContextGraph({ project }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedTypes, setExpandedTypes] = useState(new Set());
  const [viewMode, setViewMode] = useState('grouped'); // 'grouped' or 'list'

  useEffect(() => {
    if (project) {
      fetchContextGraph();
    }
  }, [project]);

  const fetchContextGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/data-model/context-graph/${project}`);
      if (!res.ok) throw new Error('Failed to fetch context graph');
      const json = await res.json();
      setData(json);
      // Auto-expand first 3 semantic types
      const firstThree = (json.summary?.semantic_types || []).slice(0, 3);
      setExpandedTypes(new Set(firstThree));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleType = (type) => {
    const newExpanded = new Set(expandedTypes);
    if (newExpanded.has(type)) {
      newExpanded.delete(type);
    } else {
      newExpanded.add(type);
    }
    setExpandedTypes(newExpanded);
  };

  const expandAll = () => {
    setExpandedTypes(new Set(data?.summary?.semantic_types || []));
  };

  const collapseAll = () => {
    setExpandedTypes(new Set());
  };

  // Group relationships by semantic type
  const getGroupedData = () => {
    if (!data) return {};
    
    const grouped = {};
    const hubs = data.hubs || [];
    const relationships = data.relationships || [];
    
    // Initialize with hubs
    hubs.forEach(hub => {
      grouped[hub.semantic_type] = {
        hub: hub,
        spokes: []
      };
    });
    
    // Add relationships as spokes
    relationships.forEach(rel => {
      if (grouped[rel.semantic_type]) {
        grouped[rel.semantic_type].spokes.push(rel);
      }
    });
    
    return grouped;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 text-gray-400">
        <Loader2 className="w-6 h-6 animate-spin mr-2" />
        Loading context graph...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
        <AlertCircle className="w-5 h-5 inline mr-2" />
        {error}
      </div>
    );
  }

  if (!data || !data.hubs?.length) {
    return (
      <div className="p-6 bg-gray-800/50 rounded-lg border border-gray-700 text-center">
        <Network className="w-12 h-12 mx-auto mb-3 text-gray-500" />
        <p className="text-gray-400">No context graph data yet.</p>
        <p className="text-sm text-gray-500 mt-1">Upload data files to build relationships.</p>
      </div>
    );
  }

  const grouped = getGroupedData();
  const summary = data.summary || {};

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <Network className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Context Graph</h3>
            <p className="text-sm text-gray-400">
              {summary.hub_count} hubs • {summary.spoke_count} relationships • {summary.semantic_types?.length} types
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={expandAll}
            className="px-2 py-1 text-xs text-gray-400 hover:text-white transition"
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            className="px-2 py-1 text-xs text-gray-400 hover:text-white transition"
          >
            Collapse All
          </button>
          <button
            onClick={fetchContextGraph}
            className="p-1.5 text-gray-400 hover:text-white transition rounded hover:bg-gray-700"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-gray-400 px-2">
        <span className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-purple-500"></div>
          Hub (source of truth)
        </span>
        <span className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-gray-600"></div>
          Spoke (references hub)
        </span>
        <span className="flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-green-400" />
          Valid FK
        </span>
        <span className="flex items-center gap-1">
          <AlertCircle className="w-3 h-3 text-yellow-400" />
          Partial match
        </span>
      </div>

      {/* Grouped View */}
      <div className="space-y-2">
        {Object.entries(grouped).map(([semanticType, { hub, spokes }]) => (
          <div 
            key={semanticType}
            className="bg-gray-800/50 rounded-lg border border-gray-700 overflow-hidden"
          >
            {/* Semantic Type Header */}
            <button
              onClick={() => toggleType(semanticType)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-700/50 transition"
            >
              <div className="flex items-center gap-3">
                {expandedTypes.has(semanticType) ? (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
                <span className="font-mono text-sm text-purple-400 font-medium">
                  {semanticType}
                </span>
                <span className="text-xs text-gray-500">
                  {spokes.length} relationship{spokes.length !== 1 ? 's' : ''}
                </span>
              </div>
              <div className="text-xs text-gray-500">
                Hub: {hub.cardinality.toLocaleString()} unique values
              </div>
            </button>

            {/* Expanded Content */}
            {expandedTypes.has(semanticType) && (
              <div className="border-t border-gray-700 bg-gray-900/30">
                {/* Hub Info */}
                <div className="px-4 py-3 flex items-center gap-3 bg-purple-500/10 border-b border-gray-700">
                  <Database className="w-4 h-4 text-purple-400" />
                  <div className="flex-1">
                    <div className="text-sm text-white font-mono">
                      {hub.table.split('_').slice(-2).join('_')}
                    </div>
                    <div className="text-xs text-gray-400">
                      Column: <span className="text-purple-300">{hub.column}</span>
                    </div>
                  </div>
                  <div className="px-2 py-0.5 bg-purple-500/20 rounded text-xs text-purple-300">
                    HUB
                  </div>
                </div>

                {/* Spokes */}
                {spokes.length > 0 ? (
                  <div className="divide-y divide-gray-700/50">
                    {spokes.map((spoke, idx) => (
                      <div 
                        key={idx}
                        className="px-4 py-2 flex items-center gap-3 hover:bg-gray-800/50"
                      >
                        <Link2 className="w-4 h-4 text-gray-500 ml-4" />
                        <div className="flex-1">
                          <div className="text-sm text-gray-300 font-mono">
                            {spoke.spoke_table.split('_').slice(-2).join('_')}
                          </div>
                          <div className="text-xs text-gray-500">
                            {spoke.spoke_column} → {spoke.hub_column}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {spoke.is_valid_fk ? (
                            <CheckCircle2 className="w-4 h-4 text-green-400" title="Valid foreign key" />
                          ) : (
                            <AlertCircle className="w-4 h-4 text-yellow-400" title="Partial match" />
                          )}
                          <span className="text-xs text-gray-500">
                            {spoke.coverage_pct ? `${(spoke.coverage_pct * 100).toFixed(0)}%` : '-'}
                          </span>
                          <span className="text-xs text-gray-600">
                            {spoke.spoke_cardinality}/{spoke.hub_cardinality}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="px-4 py-3 text-sm text-gray-500 text-center">
                    No spoke relationships found
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-700">
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-400">{summary.hub_count}</div>
          <div className="text-xs text-gray-500">Hub Tables</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-400">{summary.spoke_count}</div>
          <div className="text-xs text-gray-500">Relationships</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-400">
            {data.relationships?.filter(r => r.is_valid_fk).length || 0}
          </div>
          <div className="text-xs text-gray-500">Valid FKs</div>
        </div>
      </div>
    </div>
  );
}
