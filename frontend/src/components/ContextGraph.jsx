/**
 * ContextGraph.jsx - Hub/Spoke Relationship Visualization
 * ========================================================
 * 
 * Deploy to: frontend/src/components/ContextGraph.jsx
 * 
 * PURPOSE:
 * Shows the semantic hub/spoke relationships that power intelligent queries.
 * Each semantic type (company_code, job_code, etc.) has ONE hub (source of truth)
 * and multiple spokes (tables that reference the hub).
 * 
 * This is the intelligence layer that enables:
 * - Automatic join path discovery
 * - Gap detection ("13 configured, 6 have data")
 * - Query scoping
 */

import React, { useState, useEffect } from 'react';
import { 
  Network, Database, Link2, ChevronDown, ChevronRight, 
  CheckCircle2, AlertCircle, Loader2, RefreshCw, Info
} from 'lucide-react';
import api from '../services/api';

// ============================================================================
// BRAND COLORS (matches rest of platform)
// ============================================================================
const brandColors = {
  primary: '#83b16d',
  accent: '#285390',
  electricBlue: '#2766b1',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  silver: '#a2a1a0',
  white: '#f6f5fa',
  scarletSage: '#993c44',
  royalPurple: '#5f4282',
  background: '#f0f2f5',
  cardBg: '#ffffff',
  text: '#1a2332',
  textMuted: '#64748b',
  border: '#e2e8f0',
  warning: '#d97706',
  success: '#22c55e',
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function ContextGraph({ project }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedTypes, setExpandedTypes] = useState(new Set());
  
  const c = brandColors;

  // Debug
  console.log('[ContextGraph] Rendering with project:', project);

  useEffect(() => {
    if (project) {
      fetchContextGraph();
    } else {
      setLoading(false);
    }
  }, [project]);

  const fetchContextGraph = async () => {
    console.log('[ContextGraph] Fetching for project:', project);
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/data-model/context-graph/${project}`);
      console.log('[ContextGraph] Response:', res.data);
      setData(res.data);
      // Auto-expand first 3 semantic types
      const firstThree = (res.data?.summary?.semantic_types || []).slice(0, 3);
      setExpandedTypes(new Set(firstThree));
    } catch (err) {
      console.error('[ContextGraph] Error:', err);
      setError(err.message || 'Failed to load context graph');
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

  // Shorten table name for display
  const shortTableName = (fullName) => {
    if (!fullName) return '';
    const parts = fullName.split('_');
    // Take last 2-3 meaningful parts
    return parts.slice(-3).join('_');
  };

  // No project selected
  if (!project) {
    return (
      <div style={{ 
        padding: '3rem', 
        textAlign: 'center',
        color: c.textMuted 
      }}>
        <Network size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
        <h3 style={{ margin: '0 0 0.5rem', color: c.text, fontWeight: 600 }}>No Project Selected</h3>
        <p style={{ margin: 0, fontSize: '0.9rem' }}>
          Select a project to view its context graph.
        </p>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center', 
        justifyContent: 'center', 
        padding: '3rem',
        color: c.textMuted 
      }}>
        <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
        <p>Loading context graph...</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div style={{ 
        padding: '2rem', 
        background: `${c.scarletSage}15`, 
        border: `1px solid ${c.scarletSage}40`,
        borderRadius: 8,
        textAlign: 'center',
        color: c.scarletSage
      }}>
        <AlertCircle size={32} style={{ marginBottom: '1rem' }} />
        <p style={{ marginBottom: '1rem' }}>{error}</p>
        <button 
          onClick={fetchContextGraph}
          style={{
            padding: '0.5rem 1rem',
            background: c.accent,
            color: 'white',
            border: 'none',
            borderRadius: 6,
            cursor: 'pointer'
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  // Empty state
  if (!data || !data.hubs?.length) {
    return (
      <div style={{ 
        padding: '3rem', 
        textAlign: 'center',
        color: c.textMuted 
      }}>
        <Network size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
        <h3 style={{ margin: '0 0 0.5rem', color: c.text, fontWeight: 600 }}>No Context Graph Data</h3>
        <p style={{ margin: 0, fontSize: '0.9rem' }}>
          Upload data files to build semantic relationships.
        </p>
        <p style={{ margin: '0.5rem 0 0', fontSize: '0.8rem', color: c.textMuted }}>
          The context graph is computed automatically during upload.
        </p>
      </div>
    );
  }

  const grouped = getGroupedData();
  const summary = data.summary || {};
  const validFKCount = data.relationships?.filter(r => r.is_valid_fk).length || 0;
  const hasRealityData = summary.has_reality_data || false;
  const hubsAwaitingReality = summary.hubs_awaiting_reality || data.hubs?.length || 0;

  return (
    <div>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        marginBottom: '1.5rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ 
            padding: '0.6rem',
            background: `${c.royalPurple}20`,
            borderRadius: 8
          }}>
            <Network size={22} style={{ color: c.royalPurple }} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: c.text }}>
              Context Graph
            </h3>
            <p style={{ margin: 0, fontSize: '0.85rem', color: c.textMuted }}>
              {summary.hub_count || 0} hub{(summary.hub_count || 0) !== 1 ? 's' : ''} • {summary.spoke_count || 0} relationship{(summary.spoke_count || 0) !== 1 ? 's' : ''} • {(summary.semantic_types || []).length} semantic type{(summary.semantic_types || []).length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            onClick={expandAll}
            style={{
              padding: '0.4rem 0.75rem',
              fontSize: '0.75rem',
              background: 'transparent',
              border: `1px solid ${c.border}`,
              borderRadius: 4,
              cursor: 'pointer',
              color: c.textMuted
            }}
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            style={{
              padding: '0.4rem 0.75rem',
              fontSize: '0.75rem',
              background: 'transparent',
              border: `1px solid ${c.border}`,
              borderRadius: 4,
              cursor: 'pointer',
              color: c.textMuted
            }}
          >
            Collapse All
          </button>
          <button
            onClick={fetchContextGraph}
            title="Refresh"
            style={{
              padding: '0.4rem',
              background: 'transparent',
              border: `1px solid ${c.border}`,
              borderRadius: 4,
              cursor: 'pointer',
              color: c.textMuted
            }}
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Status Banner - No Reality Data */}
      {!hasRealityData && (
        <div style={{
          padding: '0.75rem 1rem',
          background: `${c.warning}15`,
          border: `1px solid ${c.warning}40`,
          borderRadius: 6,
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <AlertCircle size={18} style={{ color: c.warning }} />
          <div style={{ fontSize: '0.85rem' }}>
            <strong style={{ color: c.text }}>Configuration Only</strong>
            <span style={{ color: c.textMuted }}> — {hubsAwaitingReality} hub{hubsAwaitingReality !== 1 ? 's' : ''} ready. Upload employee/payroll data (Reality) to see coverage and gaps.</span>
          </div>
        </div>
      )}

      {/* Legend */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '1.5rem',
        padding: '0.75rem 1rem',
        background: c.background,
        borderRadius: 6,
        marginBottom: '1rem',
        fontSize: '0.8rem',
        color: c.textMuted
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: c.royalPurple }}></div>
          Hub (source of truth)
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: c.silver }}></div>
          Spoke (references hub)
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <CheckCircle2 size={14} style={{ color: c.success }} />
          Valid FK
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <AlertCircle size={14} style={{ color: c.warning }} />
          Partial match
        </span>
      </div>

      {/* Semantic Type Groups */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {Object.entries(grouped).map(([semanticType, { hub, spokes }]) => (
          <div 
            key={semanticType}
            style={{
              background: c.cardBg,
              border: `1px solid ${c.border}`,
              borderRadius: 8,
              overflow: 'hidden'
            }}
          >
            {/* Semantic Type Header */}
            <button
              onClick={() => toggleType(semanticType)}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                textAlign: 'left'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                {expandedTypes.has(semanticType) ? (
                  <ChevronDown size={16} style={{ color: c.textMuted }} />
                ) : (
                  <ChevronRight size={16} style={{ color: c.textMuted }} />
                )}
                <span style={{ 
                  fontFamily: 'monospace',
                  fontSize: '0.9rem',
                  fontWeight: 600,
                  color: c.royalPurple
                }}>
                  {semanticType}
                </span>
                <span style={{ 
                  fontSize: '0.75rem',
                  color: c.textMuted,
                  background: c.background,
                  padding: '0.15rem 0.5rem',
                  borderRadius: 4
                }}>
                  {spokes.length} relationship{spokes.length !== 1 ? 's' : ''}
                </span>
              </div>
              <div style={{ fontSize: '0.8rem', color: c.textMuted }}>
                Hub: {hub.cardinality?.toLocaleString()} unique values
              </div>
            </button>

            {/* Expanded Content */}
            {expandedTypes.has(semanticType) && (
              <div style={{ borderTop: `1px solid ${c.border}` }}>
                {/* Hub Info */}
                <div style={{ 
                  padding: '0.75rem 1rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  background: `${c.royalPurple}10`,
                  borderBottom: `1px solid ${c.border}`
                }}>
                  <Database size={16} style={{ color: c.royalPurple }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ 
                      fontSize: '0.85rem', 
                      fontWeight: 500, 
                      color: c.text,
                      fontFamily: 'monospace'
                    }}>
                      {shortTableName(hub.table)}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: c.textMuted }}>
                      Column: <span style={{ color: c.royalPurple }}>{hub.column}</span>
                    </div>
                  </div>
                  <span style={{
                    padding: '0.2rem 0.5rem',
                    background: `${c.royalPurple}20`,
                    color: c.royalPurple,
                    borderRadius: 4,
                    fontSize: '0.7rem',
                    fontWeight: 600
                  }}>
                    HUB
                  </span>
                </div>

                {/* Spokes */}
                {spokes.length > 0 ? (
                  <div>
                    {spokes.map((spoke, idx) => (
                      <div 
                        key={idx}
                        style={{
                          padding: '0.6rem 1rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.75rem',
                          borderBottom: idx < spokes.length - 1 ? `1px solid ${c.border}` : 'none',
                          background: 'transparent'
                        }}
                      >
                        <Link2 size={14} style={{ color: c.silver, marginLeft: '1.5rem' }} />
                        <div style={{ flex: 1 }}>
                          <div style={{ 
                            fontSize: '0.85rem', 
                            color: c.text,
                            fontFamily: 'monospace'
                          }}>
                            {shortTableName(spoke.spoke_table)}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: c.textMuted }}>
                            {spoke.spoke_column} → {spoke.hub_column}
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          {spoke.is_valid_fk ? (
                            <CheckCircle2 size={16} style={{ color: c.success }} title="Valid foreign key" />
                          ) : (
                            <AlertCircle size={16} style={{ color: c.warning }} title="Partial match" />
                          )}
                          <span style={{ 
                            fontSize: '0.75rem', 
                            color: c.textMuted,
                            minWidth: 45,
                            textAlign: 'right'
                          }}>
                            {spoke.coverage_pct ? `${Math.round(spoke.coverage_pct)}%` : '-'}
                          </span>
                          <span style={{ 
                            fontSize: '0.7rem', 
                            color: c.silver,
                            fontFamily: 'monospace'
                          }}>
                            {spoke.spoke_cardinality}/{spoke.hub_cardinality}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ 
                    padding: '1rem', 
                    textAlign: 'center', 
                    color: c.textMuted,
                    fontSize: '0.85rem',
                    background: `${c.warning}08`
                  }}>
                    <span style={{ color: c.warning }}>⏳</span> Awaiting Reality data — upload employee/payroll files to see coverage
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary Stats */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: hasRealityData ? 'repeat(3, 1fr)' : 'repeat(2, 1fr)',
        gap: '1rem',
        marginTop: '1.5rem',
        padding: '1rem 0',
        borderTop: `1px solid ${c.border}`
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: c.royalPurple }}>
            {summary.hub_count || 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: c.textMuted }}>
            {hasRealityData ? 'Hub Tables' : 'Hub Candidates'}
          </div>
        </div>
        {hasRealityData ? (
          <>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.75rem', fontWeight: 700, color: c.electricBlue }}>
                {summary.spoke_count || 0}
              </div>
              <div style={{ fontSize: '0.75rem', color: c.textMuted }}>Reality Connections</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.75rem', fontWeight: 700, color: c.success }}>
                {validFKCount}
              </div>
              <div style={{ fontSize: '0.75rem', color: c.textMuted }}>Valid FKs</div>
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: c.warning }}>
              {hubsAwaitingReality}
            </div>
            <div style={{ fontSize: '0.75rem', color: c.textMuted }}>Awaiting Reality</div>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div style={{
        marginTop: '1rem',
        padding: '0.75rem 1rem',
        background: `${c.accent}10`,
        borderRadius: 6,
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.75rem',
        fontSize: '0.8rem',
        color: c.textMuted
      }}>
        <Info size={16} style={{ color: c.accent, flexShrink: 0, marginTop: 2 }} />
        <div>
          <strong style={{ color: c.text }}>How it works:</strong> <strong>Configuration</strong> tables 
          (code lookups, mappings) become <strong>hubs</strong> — the source of truth for each semantic type. 
          When you upload <strong>Reality</strong> data (employee records, payroll), those tables become 
          <strong>spokes</strong> that reference the hubs. This enables gap detection: 
          "13 codes configured, 6 in use by employees."
        </div>
      </div>
    </div>
  );
}
