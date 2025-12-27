/**
 * ClassificationPanel.jsx - FIVE TRUTHS Classification Transparency
 * ==================================================================
 * 
 * Deploy to: frontend/src/components/ClassificationPanel.jsx
 * 
 * PURPOSE:
 * Shows users exactly what the system captured and WHY.
 * Without this transparency, there is no trust in the platform.
 * 
 * FEATURES:
 * - Column classifications with captured values
 * - WHY each classification was assigned
 * - Detected relationships
 * - Domain detection with confidence
 * - Query routing keywords
 * - Edit capability for corrections
 */

import React, { useState, useEffect } from 'react';
import { 
  Database, Eye, EyeOff, Edit3, Check, X, ChevronDown, ChevronRight,
  Link2, Tag, Hash, Type, Calendar, ToggleLeft, Key, AlertCircle,
  Loader2, RefreshCw, Search, Sparkles
} from 'lucide-react';
import api from '../services/api';

// ============================================================================
// BRAND COLORS
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
  success: '#285390',
};

// ============================================================================
// TYPE ICONS
// ============================================================================
const typeIcons = {
  categorical: { icon: Tag, color: brandColors.primary },
  numeric: { icon: Hash, color: brandColors.electricBlue },
  text: { icon: Type, color: brandColors.textMuted },
  date: { icon: Calendar, color: brandColors.royalPurple },
  boolean: { icon: ToggleLeft, color: brandColors.warning },
};

const filterCategoryColors = {
  status: '#22c55e',
  company: '#3b82f6',
  organization: '#8b5cf6',
  location: '#f59e0b',
  pay_type: '#ec4899',
  employee_type: '#06b6d4',
  job: '#6366f1',
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function ClassificationPanel({ tableName, onClose }) {
  const [classification, setClassification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedColumns, setExpandedColumns] = useState({});
  const [editingColumn, setEditingColumn] = useState(null);
  const [showRelationships, setShowRelationships] = useState(true);
  const [showRouting, setShowRouting] = useState(true);
  
  const c = brandColors;
  
  useEffect(() => {
    if (tableName) {
      loadClassification();
    }
  }, [tableName]);
  
  const loadClassification = async () => {
    setLoading(true);
    setError(null);
    try {
      // Try classification endpoint first
      const res = await api.get(`/classification/table/${encodeURIComponent(tableName)}`);
      let classData = res.data?.classification;
      
      // If columns are empty, fall back to table-profile endpoint which has the data
      if (!classData?.columns || classData.columns.length === 0) {
        try {
          const profileRes = await api.get(`/status/table-profile/${encodeURIComponent(tableName)}`);
          const profile = profileRes.data;
          
          // Build columns from profile data
          const columns = (profile.columns || []).map(col => ({
            column_name: col.name,
            data_type: col.type || 'VARCHAR',
            inferred_type: inferType(col),
            total_count: profile.total_rows || profile.row_count || 0,
            null_count: col.null_count || 0,
            fill_rate: col.fill_rate || 100,
            distinct_count: col.distinct_values || 0,
            is_categorical: (col.distinct_values || 0) < 50 && (col.distinct_values || 0) > 0,
            is_likely_key: col.name?.toLowerCase().includes('_id') || col.name?.toLowerCase().includes('_code'),
            distinct_values: [],
            value_distribution: {},
            sample_values: col.top_values || [],
            filter_category: null,
            filter_priority: 0,
            classification_reason: 'Inferred from profile data',
          }));
          
          classData = {
            ...classData,
            columns,
            column_count: columns.length,
            row_count: profile.total_rows || profile.row_count || classData?.row_count || 0,
          };
        } catch (profileErr) {
          console.warn('Profile fallback failed:', profileErr);
        }
      }
      
      setClassification(classData);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };
  
  // Helper to infer column type
  const inferType = (col) => {
    const name = (col.name || '').toLowerCase();
    if (name.includes('date') || name.includes('_at') || name.includes('time')) return 'date';
    if (name.includes('amount') || name.includes('rate') || name.includes('total') || name.includes('count')) return 'numeric';
    if (name.includes('is_') || name.includes('has_') || name.includes('flag')) return 'boolean';
    if ((col.distinct_values || 0) < 20) return 'categorical';
    return 'text';
  };
  
  const toggleColumn = (colName) => {
    setExpandedColumns(prev => ({
      ...prev,
      [colName]: !prev[colName]
    }));
  };
  
  const handleReclassify = async (columnName, newCategory) => {
    try {
      await api.post('/classification/reclassify/column', null, {
        params: {
          table_name: tableName,
          column_name: columnName,
          new_filter_category: newCategory
        }
      });
      setEditingColumn(null);
      loadClassification();
    } catch (err) {
      alert('Failed to update: ' + (err.response?.data?.detail || err.message));
    }
  };
  
  if (loading) {
    return (
      <div style={{ 
        padding: '2rem', 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center',
        justifyContent: 'center',
        color: c.textMuted 
      }}>
        <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
        <p>Loading classification...</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }
  
  if (error) {
    return (
      <div style={{ 
        padding: '2rem', 
        textAlign: 'center',
        color: c.scarletSage 
      }}>
        <AlertCircle size={32} style={{ marginBottom: '1rem' }} />
        <p>{error}</p>
        <button 
          onClick={loadClassification}
          style={{
            marginTop: '1rem',
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
  
  if (!classification) {
    return null;
  }
  
  const { columns, relationships, detected_domain, domain_confidence, domain_reason, routing_keywords, routing_boost_reasons } = classification;
  
  return (
    <div style={{ 
      background: c.cardBg, 
      border: `1px solid ${c.border}`, 
      borderRadius: 12,
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        padding: '1rem',
        background: c.background,
        borderBottom: `1px solid ${c.border}`
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Database size={20} style={{ color: c.accent }} />
          <div>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: c.text }}>
              Classification Report
            </h3>
            <p style={{ margin: 0, fontSize: '0.8rem', color: c.textMuted }}>
              {classification.display_name || classification.table_name}
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            onClick={loadClassification}
            style={{
              padding: '0.4rem',
              background: 'transparent',
              border: `1px solid ${c.border}`,
              borderRadius: 6,
              cursor: 'pointer',
              color: c.textMuted
            }}
          >
            <RefreshCw size={16} />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                padding: '0.4rem',
                background: 'transparent',
                border: `1px solid ${c.border}`,
                borderRadius: 6,
                cursor: 'pointer',
                color: c.textMuted
              }}
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>
      
      {/* Domain Detection */}
      {detected_domain && (
        <div style={{ 
          padding: '0.75rem 1rem',
          background: `${c.primary}10`,
          borderBottom: `1px solid ${c.border}`,
          display: 'flex',
          alignItems: 'center',
          gap: '1rem'
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem',
            padding: '0.35rem 0.75rem',
            background: c.primary,
            color: 'white',
            borderRadius: 20,
            fontSize: '0.8rem',
            fontWeight: 600
          }}>
            <Sparkles size={14} />
            {detected_domain.toUpperCase()}
          </div>
          <span style={{ fontSize: '0.85rem', color: c.text }}>
            {Math.round(domain_confidence * 100)}% confidence
          </span>
          <span style={{ fontSize: '0.8rem', color: c.textMuted, flex: 1 }}>
            {domain_reason}
          </span>
        </div>
      )}
      
      {/* Summary Stats */}
      <div style={{ 
        display: 'flex', 
        gap: '1.5rem', 
        padding: '0.75rem 1rem',
        borderBottom: `1px solid ${c.border}`,
        fontSize: '0.85rem'
      }}>
        <span><strong>{classification.row_count?.toLocaleString()}</strong> rows</span>
        <span><strong>{columns?.length || 0}</strong> columns</span>
        <span><strong>{columns?.filter(c => c.is_categorical).length || 0}</strong> categorical</span>
        <span><strong>{relationships?.length || 0}</strong> relationships</span>
      </div>
      
      {/* Columns Section */}
      <div style={{ padding: '1rem' }}>
        <h4 style={{ 
          margin: '0 0 0.75rem', 
          fontSize: '0.85rem', 
          fontWeight: 600, 
          color: c.text,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <Tag size={16} style={{ color: c.primary }} />
          Column Classifications
        </h4>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {columns?.map(col => {
            const TypeIcon = typeIcons[col.inferred_type]?.icon || Type;
            const typeColor = typeIcons[col.inferred_type]?.color || c.textMuted;
            const isExpanded = expandedColumns[col.column_name];
            const isEditing = editingColumn === col.column_name;
            
            return (
              <div 
                key={col.column_name}
                style={{ 
                  border: `1px solid ${c.border}`,
                  borderRadius: 8,
                  overflow: 'hidden',
                  background: isExpanded ? `${c.background}` : 'white'
                }}
              >
                {/* Column Header */}
                <div 
                  onClick={() => toggleColumn(col.column_name)}
                  style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '0.75rem',
                    padding: '0.65rem 0.75rem',
                    cursor: 'pointer'
                  }}
                >
                  {isExpanded ? (
                    <ChevronDown size={16} style={{ color: c.textMuted }} />
                  ) : (
                    <ChevronRight size={16} style={{ color: c.textMuted }} />
                  )}
                  
                  <TypeIcon size={16} style={{ color: typeColor }} />
                  
                  <span style={{ 
                    fontFamily: 'monospace', 
                    fontSize: '0.85rem', 
                    fontWeight: 500,
                    color: c.text 
                  }}>
                    {col.column_name}
                  </span>
                  
                  {col.is_likely_key && (
                    <Key size={14} style={{ color: c.warning }} title="Likely Key Column" />
                  )}
                  
                  {col.filter_category && (
                    <span style={{
                      padding: '0.15rem 0.5rem',
                      background: filterCategoryColors[col.filter_category] || c.silver,
                      color: 'white',
                      borderRadius: 10,
                      fontSize: '0.7rem',
                      fontWeight: 600
                    }}>
                      {col.filter_category}
                    </span>
                  )}
                  
                  <div style={{ flex: 1 }} />
                  
                  {/* Fill Rate Bar */}
                  <div style={{ 
                    width: 60, 
                    height: 6, 
                    background: c.border, 
                    borderRadius: 3,
                    overflow: 'hidden'
                  }}>
                    <div style={{ 
                      width: `${col.fill_rate}%`, 
                      height: '100%', 
                      background: col.fill_rate > 80 ? c.primary : col.fill_rate > 50 ? c.warning : c.scarletSage,
                      borderRadius: 3
                    }} />
                  </div>
                  <span style={{ fontSize: '0.75rem', color: c.textMuted, minWidth: 40 }}>
                    {col.fill_rate}%
                  </span>
                  
                  <span style={{ 
                    fontSize: '0.75rem', 
                    color: c.textMuted,
                    minWidth: 50
                  }}>
                    {col.distinct_count} vals
                  </span>
                </div>
                
                {/* Expanded Details */}
                {isExpanded && (
                  <div style={{ 
                    padding: '0.75rem', 
                    borderTop: `1px solid ${c.border}`,
                    background: c.cardBg
                  }}>
                    {/* Classification Reason */}
                    <div style={{ 
                      padding: '0.5rem 0.75rem',
                      background: `${c.skyBlue}15`,
                      borderRadius: 6,
                      marginBottom: '0.75rem',
                      fontSize: '0.8rem',
                      color: c.text
                    }}>
                      <strong>Why this classification: </strong>
                      {col.classification_reason || 'No specific classification applied'}
                    </div>
                    
                    {/* Values */}
                    {col.is_categorical && col.distinct_values?.length > 0 && (
                      <div style={{ marginBottom: '0.75rem' }}>
                        <div style={{ 
                          fontSize: '0.75rem', 
                          fontWeight: 600, 
                          color: c.textMuted, 
                          marginBottom: '0.35rem',
                          textTransform: 'uppercase'
                        }}>
                          Captured Values ({col.distinct_count})
                        </div>
                        <div style={{ 
                          display: 'flex', 
                          flexWrap: 'wrap', 
                          gap: '0.35rem'
                        }}>
                          {col.distinct_values.slice(0, 20).map((val, i) => (
                            <span 
                              key={i}
                              style={{
                                padding: '0.2rem 0.5rem',
                                background: c.background,
                                border: `1px solid ${c.border}`,
                                borderRadius: 4,
                                fontSize: '0.75rem',
                                fontFamily: 'monospace',
                                color: c.text
                              }}
                            >
                              {String(val).slice(0, 30)}
                            </span>
                          ))}
                          {col.distinct_values.length > 20 && (
                            <span style={{ 
                              fontSize: '0.75rem', 
                              color: c.textMuted,
                              padding: '0.2rem 0.5rem'
                            }}>
                              +{col.distinct_values.length - 20} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Value Distribution */}
                    {col.value_distribution && Object.keys(col.value_distribution).length > 0 && (
                      <div style={{ marginBottom: '0.75rem' }}>
                        <div style={{ 
                          fontSize: '0.75rem', 
                          fontWeight: 600, 
                          color: c.textMuted, 
                          marginBottom: '0.35rem',
                          textTransform: 'uppercase'
                        }}>
                          Value Distribution (Top 10)
                        </div>
                        <div style={{ fontSize: '0.8rem' }}>
                          {Object.entries(col.value_distribution)
                            .sort(([,a], [,b]) => b - a)
                            .slice(0, 10)
                            .map(([val, count], i) => (
                              <div 
                                key={i}
                                style={{ 
                                  display: 'flex', 
                                  justifyContent: 'space-between',
                                  padding: '0.2rem 0',
                                  borderBottom: i < 9 ? `1px solid ${c.border}` : 'none'
                                }}
                              >
                                <span style={{ fontFamily: 'monospace', color: c.text }}>
                                  {String(val).slice(0, 40)}
                                </span>
                                <span style={{ color: c.textMuted }}>
                                  {count.toLocaleString()}
                                </span>
                              </div>
                            ))
                          }
                        </div>
                      </div>
                    )}
                    
                    {/* Numeric Stats */}
                    {col.inferred_type === 'numeric' && (col.min_value !== null || col.max_value !== null) && (
                      <div style={{ 
                        display: 'flex', 
                        gap: '1rem', 
                        fontSize: '0.8rem',
                        marginBottom: '0.75rem'
                      }}>
                        {col.min_value !== null && <span><strong>Min:</strong> {col.min_value}</span>}
                        {col.max_value !== null && <span><strong>Max:</strong> {col.max_value}</span>}
                        {col.mean_value !== null && <span><strong>Mean:</strong> {col.mean_value.toFixed(2)}</span>}
                      </div>
                    )}
                    
                    {/* Date Stats */}
                    {col.inferred_type === 'date' && (col.min_date || col.max_date) && (
                      <div style={{ 
                        display: 'flex', 
                        gap: '1rem', 
                        fontSize: '0.8rem',
                        marginBottom: '0.75rem'
                      }}>
                        {col.min_date && <span><strong>Earliest:</strong> {col.min_date}</span>}
                        {col.max_date && <span><strong>Latest:</strong> {col.max_date}</span>}
                      </div>
                    )}
                    
                    {/* Edit Classification */}
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '0.5rem',
                      marginTop: '0.5rem',
                      paddingTop: '0.5rem',
                      borderTop: `1px dashed ${c.border}`
                    }}>
                      {isEditing ? (
                        <>
                          <select
                            defaultValue={col.filter_category || ''}
                            onChange={(e) => handleReclassify(col.column_name, e.target.value)}
                            style={{
                              padding: '0.35rem 0.5rem',
                              border: `1px solid ${c.border}`,
                              borderRadius: 4,
                              fontSize: '0.8rem'
                            }}
                          >
                            <option value="">No category</option>
                            <option value="status">Status</option>
                            <option value="company">Company</option>
                            <option value="organization">Organization</option>
                            <option value="location">Location</option>
                            <option value="pay_type">Pay Type</option>
                            <option value="employee_type">Employee Type</option>
                            <option value="job">Job</option>
                          </select>
                          <button
                            onClick={() => setEditingColumn(null)}
                            style={{
                              padding: '0.35rem',
                              background: 'transparent',
                              border: 'none',
                              cursor: 'pointer',
                              color: c.textMuted
                            }}
                          >
                            <X size={14} />
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => setEditingColumn(col.column_name)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            padding: '0.35rem 0.75rem',
                            background: 'transparent',
                            border: `1px solid ${c.border}`,
                            borderRadius: 4,
                            fontSize: '0.75rem',
                            color: c.textMuted,
                            cursor: 'pointer'
                          }}
                        >
                          <Edit3 size={12} />
                          Change Category
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
      
      {/* Relationships Section */}
      {relationships?.length > 0 && (
        <div style={{ padding: '0 1rem 1rem' }}>
          <button
            onClick={() => setShowRelationships(!showRelationships)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              width: '100%',
              padding: '0.65rem 0',
              background: 'transparent',
              border: 'none',
              borderTop: `1px solid ${c.border}`,
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 600,
              color: c.text
            }}
          >
            {showRelationships ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            <Link2 size={16} style={{ color: c.electricBlue }} />
            Relationships ({relationships.length})
          </button>
          
          {showRelationships && (
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              gap: '0.5rem',
              paddingTop: '0.5rem'
            }}>
              {relationships.map((rel, i) => (
                <div 
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.5rem 0.75rem',
                    background: c.background,
                    borderRadius: 6,
                    fontSize: '0.8rem'
                  }}
                >
                  <span style={{ fontFamily: 'monospace', color: c.accent }}>
                    {rel.from_column}
                  </span>
                  <span style={{ color: c.textMuted }}>→</span>
                  <span style={{ fontFamily: 'monospace', color: c.primary }}>
                    {rel.to_table}.{rel.to_column}
                  </span>
                  <span style={{
                    padding: '0.1rem 0.4rem',
                    background: c.electricBlue,
                    color: 'white',
                    borderRadius: 4,
                    fontSize: '0.7rem'
                  }}>
                    {rel.relationship_type}
                  </span>
                  <span style={{ color: c.textMuted, fontSize: '0.75rem' }}>
                    {Math.round(rel.match_percentage)}% match
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* Routing Keywords Section */}
      {routing_keywords?.length > 0 && (
        <div style={{ padding: '0 1rem 1rem' }}>
          <button
            onClick={() => setShowRouting(!showRouting)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              width: '100%',
              padding: '0.65rem 0',
              background: 'transparent',
              border: 'none',
              borderTop: `1px solid ${c.border}`,
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 600,
              color: c.text
            }}
          >
            {showRouting ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            <Search size={16} style={{ color: c.royalPurple }} />
            Query Routing
          </button>
          
          {showRouting && (
            <div style={{ paddingTop: '0.5rem' }}>
              {routing_boost_reasons?.length > 0 && (
                <div style={{ 
                  padding: '0.5rem 0.75rem',
                  background: `${c.royalPurple}10`,
                  borderRadius: 6,
                  marginBottom: '0.5rem',
                  fontSize: '0.8rem',
                  color: c.text
                }}>
                  <strong>Routing Boosts:</strong>
                  <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem' }}>
                    {routing_boost_reasons.map((reason, i) => (
                      <li key={i}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div style={{ 
                fontSize: '0.75rem', 
                fontWeight: 600, 
                color: c.textMuted, 
                marginBottom: '0.35rem',
                textTransform: 'uppercase'
              }}>
                Keywords that route here
              </div>
              <div style={{ 
                display: 'flex', 
                flexWrap: 'wrap', 
                gap: '0.25rem'
              }}>
                {routing_keywords.slice(0, 30).map((kw, i) => (
                  <span 
                    key={i}
                    style={{
                      padding: '0.15rem 0.4rem',
                      background: `${c.royalPurple}15`,
                      color: c.royalPurple,
                      borderRadius: 4,
                      fontSize: '0.7rem',
                      fontFamily: 'monospace'
                    }}
                  >
                    {kw}
                  </span>
                ))}
                {routing_keywords.length > 30 && (
                  <span style={{ fontSize: '0.7rem', color: c.textMuted }}>
                    +{routing_keywords.length - 30} more
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


// ============================================================================
// CHUNK PANEL COMPONENT
// ============================================================================
export function ChunkPanel({ documentName, projectId, onClose }) {
  const [chunks, setChunks] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedChunk, setExpandedChunk] = useState(null);
  
  const c = brandColors;
  
  useEffect(() => {
    if (documentName) {
      loadChunks();
    }
  }, [documentName, projectId]);
  
  const loadChunks = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);
      
      const res = await api.get(`/classification/chunks/${encodeURIComponent(documentName)}?${params}`);
      setChunks(res.data?.document);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
        <Loader2 size={32} style={{ animation: 'spin 1s linear infinite' }} />
        <p>Loading chunks...</p>
      </div>
    );
  }
  
  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: c.scarletSage }}>
        <AlertCircle size={32} />
        <p>{error}</p>
      </div>
    );
  }
  
  if (!chunks) return null;
  
  return (
    <div style={{ 
      background: c.cardBg, 
      border: `1px solid ${c.border}`, 
      borderRadius: 12,
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        padding: '1rem',
        background: c.background,
        borderBottom: `1px solid ${c.border}`
      }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: c.text }}>
            Chunk Details
          </h3>
          <p style={{ margin: 0, fontSize: '0.8rem', color: c.textMuted }}>
            {documentName} • {chunks.total_chunks} chunks
          </p>
        </div>
        {onClose && (
          <button onClick={onClose} style={{ 
            padding: '0.4rem', 
            background: 'transparent', 
            border: `1px solid ${c.border}`,
            borderRadius: 6,
            cursor: 'pointer'
          }}>
            <X size={16} />
          </button>
        )}
      </div>
      
      {/* Chunk List */}
      <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
        {chunks.chunks?.map((chunk, i) => (
          <div 
            key={chunk.chunk_id}
            style={{
              borderBottom: `1px solid ${c.border}`,
              padding: '0.75rem 1rem'
            }}
          >
            <div 
              onClick={() => setExpandedChunk(expandedChunk === i ? null : i)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                cursor: 'pointer'
              }}
            >
              {expandedChunk === i ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <span style={{ fontWeight: 500, color: c.text }}>
                Chunk {chunk.chunk_index + 1}
              </span>
              {chunk.truth_type && (
                <span style={{
                  padding: '0.1rem 0.4rem',
                  background: `${c.accent}20`,
                  color: c.accent,
                  borderRadius: 4,
                  fontSize: '0.7rem'
                }}>
                  {chunk.truth_type}
                </span>
              )}
              {chunk.structure && (
                <span style={{
                  padding: '0.1rem 0.4rem',
                  background: `${c.primary}20`,
                  color: c.primary,
                  borderRadius: 4,
                  fontSize: '0.7rem'
                }}>
                  {chunk.structure}
                </span>
              )}
              <span style={{ flex: 1 }} />
              <span style={{ fontSize: '0.75rem', color: c.textMuted }}>
                {chunk.full_length} chars
              </span>
            </div>
            
            {expandedChunk === i && (
              <div style={{ 
                marginTop: '0.5rem',
                padding: '0.75rem',
                background: c.background,
                borderRadius: 6,
                fontSize: '0.8rem'
              }}>
                {/* Metadata */}
                <div style={{ 
                  display: 'flex', 
                  flexWrap: 'wrap', 
                  gap: '0.5rem',
                  marginBottom: '0.5rem'
                }}>
                  {chunk.strategy && <span style={{ color: c.textMuted }}>Strategy: {chunk.strategy}</span>}
                  {chunk.parent_section && <span style={{ color: c.textMuted }}>Section: {chunk.parent_section}</span>}
                  {chunk.position && <span style={{ color: c.textMuted }}>Position: {chunk.position}</span>}
                </div>
                
                {/* Preview */}
                <div style={{
                  padding: '0.5rem',
                  background: c.cardBg,
                  border: `1px solid ${c.border}`,
                  borderRadius: 4,
                  fontFamily: 'monospace',
                  whiteSpace: 'pre-wrap',
                  maxHeight: '200px',
                  overflowY: 'auto'
                }}>
                  {chunk.chunk_text}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
