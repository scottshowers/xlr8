/**
 * DataHealthPage - Data Integrity + Relationship Review
 * Clean professional design with theme support
 * 
 * FIXED: Uses api service instead of raw fetch
 * FIXED: Proper error handling to prevent auth cascades
 */

import React, { useState, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';
import { 
  CheckCircle, AlertTriangle, RefreshCw, Zap, ChevronDown, ChevronRight,
  Database, Link2, X, Check, HelpCircle, Table2, Loader2
} from 'lucide-react';

const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f5f7fa',
  card: dark ? '#242b3d' : '#ffffff',
  cardBorder: dark ? '#2d3548' : '#e8ecf1',
  text: dark ? '#e8eaed' : '#2a3441',
  textMuted: dark ? '#8b95a5' : '#6b7280',
  textLight: dark ? '#5f6a7d' : '#9ca3af',
  primary: '#6b9b5a',  // Muted green
  primaryLight: dark ? 'rgba(107, 155, 90, 0.15)' : 'rgba(107, 155, 90, 0.1)',
  blue: '#285390',     // Slate blue
  blueLight: dark ? 'rgba(74, 107, 138, 0.15)' : 'rgba(74, 107, 138, 0.1)',
  amber: '#d97706',    // Muted rust
  amberLight: dark ? 'rgba(138, 107, 74, 0.15)' : 'rgba(138, 107, 74, 0.1)',
  red: '#993c44',      // Muted burgundy
  redLight: dark ? 'rgba(138, 74, 74, 0.15)' : 'rgba(138, 74, 74, 0.1)',
  green: '#5a8a5a',    // Muted forest green
  greenLight: dark ? 'rgba(90, 138, 90, 0.15)' : 'rgba(90, 138, 90, 0.1)',
  divider: dark ? '#2d3548' : '#e8ecf1',
  inputBg: dark ? '#1a1f2e' : '#f8fafc',
});

export default function DataHealthPage({ embedded = false }) {
  const { activeProject } = useProject();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  
  const [integrityLoading, setIntegrityLoading] = useState(false);
  const [integrityData, setIntegrityData] = useState(null);
  const [integrityError, setIntegrityError] = useState(null);
  const [expandedTables, setExpandedTables] = useState(new Set());
  const [tableProfiles, setTableProfiles] = useState({});
  const [loadingProfiles, setLoadingProfiles] = useState(new Set());
  
  const [relLoading, setRelLoading] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);
  const [relationships, setRelationships] = useState([]);
  const [stats, setStats] = useState(null);
  
  const [showHighConfidence, setShowHighConfidence] = useState(false);
  const [showNeedsReview, setShowNeedsReview] = useState(false);

  const needsReview = relationships.filter(r => r.needs_review && !r.confirmed);
  const autoMatched = relationships.filter(r => !r.needs_review || r.confirmed);

  useEffect(() => { 
    if (activeProject?.name) { 
      loadDataIntegrity(); 
      loadExistingRelationships(); 
    } 
  }, [activeProject?.id]);

  const loadDataIntegrity = async () => {
    setIntegrityLoading(true);
    setIntegrityError(null);
    try {
      const res = await api.get('/status/data-integrity', {
        params: { customer_id: activeProject?.id || '' },
        timeout: 15000 // 15 second timeout
      });
      setIntegrityData(res.data);
    } catch (err) {
      console.error('Failed to load integrity:', err);
      // Don't let errors cascade - just show error state
      setIntegrityError(err.message || 'Failed to load data integrity');
      setIntegrityData(null);
    } finally {
      setIntegrityLoading(false);
    }
  };

  const loadTableProfile = async (tableName) => {
    if (tableProfiles[tableName] || loadingProfiles.has(tableName)) return;
    setLoadingProfiles(prev => new Set([...prev, tableName]));
    try {
      const res = await api.get(`/status/table-profile/${encodeURIComponent(tableName)}`, {
        timeout: 10000
      });
      setTableProfiles(prev => ({ ...prev, [tableName]: res.data }));
    } catch (err) {
      console.error('Failed to load profile:', err);
      setTableProfiles(prev => ({ ...prev, [tableName]: { error: err.message } }));
    } finally {
      setLoadingProfiles(prev => { 
        const n = new Set(prev); 
        n.delete(tableName); 
        return n; 
      });
    }
  };

  const toggleTableExpand = (tableName) => {
    const s = new Set(expandedTables);
    if (s.has(tableName)) {
      s.delete(tableName);
    } else {
      s.add(tableName);
      loadTableProfile(tableName);
    }
    setExpandedTables(s);
  };

  const loadExistingRelationships = async () => {
    if (!activeProject?.name) return;
    setRelLoading(true);
    try {
      const res = await api.get(`/data-model/relationships/${encodeURIComponent(activeProject.id)}`, {
        timeout: 15000
      });
      if (res.data?.relationships?.length > 0) {
        setRelationships(res.data.relationships);
        setStats(res.data.stats || null);
        setAnalyzed(true);
      } else {
        setStats(res.data?.stats || null);
      }
    } catch (err) {
      // 404 is expected if no relationships analyzed yet
      if (err.response?.status !== 404) {
        console.warn('Relationships load error:', err.message);
      }
    } finally {
      setRelLoading(false);
    }
  };

  const analyzeProject = async () => {
    if (!activeProject?.name) return;
    setRelLoading(true);
    try {
      const res = await api.post(`/data-model/analyze/${encodeURIComponent(activeProject.id)}`, null, {
        timeout: 60000 // Analysis can take a while
      });
      setRelationships(res.data?.relationships || []);
      setStats(res.data?.stats || null);
      setAnalyzed(true);
    } catch (err) {
      console.error('Analysis failed:', err.message);
    } finally {
      setRelLoading(false);
    }
  };

  const confirmRelationship = async (rel, confirmed) => {
    try {
      await api.post(
        `/data-model/relationships/${encodeURIComponent(activeProject.id)}/confirm`,
        {
          source_table: rel.source_table,
          source_column: rel.source_column,
          target_table: rel.target_table,
          target_column: rel.target_column,
          confirmed: confirmed,
          semantic_type: rel.semantic_type
        },
        { timeout: 10000 }
      );
      
      setRelationships(prev => 
        prev.map(r => {
          if (r.source_table === rel.source_table && r.source_column === rel.source_column && 
              r.target_table === rel.target_table && r.target_column === rel.target_column) {
            return confirmed ? { ...r, confirmed: true, needs_review: false } : null;
          }
          return r;
        }).filter(Boolean)
      );
    } catch (err) {
      console.error('Failed to confirm:', err);
    }
  };

  if (!activeProject) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: colors.textMuted }}>
        <Database size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
        <p>Select a project to view data health</p>
      </div>
    );
  }

  const hasIntegrityIssues = integrityData && (integrityData.status === 'unhealthy' || integrityData.status === 'degraded');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* DATA INTEGRITY SECTION */}
      <div style={{ background: colors.card, border: '1px solid ' + colors.cardBorder, borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid ' + colors.divider, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Table2 size={20} style={{ color: colors.primary }} />
            <div>
              <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: colors.text }}>Data Integrity</h2>
              <p style={{ margin: 0, fontSize: '0.75rem', color: colors.textMuted }}>Table health and column quality</p>
            </div>
          </div>
          <button onClick={loadDataIntegrity} disabled={integrityLoading} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.75rem', background: 'transparent', border: '1px solid ' + colors.divider, borderRadius: 6, color: colors.textMuted, fontSize: '0.8rem', cursor: 'pointer' }}>
            <RefreshCw size={14} style={{ animation: integrityLoading ? 'spin 1s linear infinite' : 'none' }} /> Refresh
          </button>
        </div>

        <div style={{ padding: '1.25rem' }}>
          {/* Error State */}
          {integrityError && (
            <div style={{ padding: '1rem', background: colors.redLight, border: '1px solid ' + colors.red + '40', borderRadius: 8, marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: colors.red }}>
                <AlertTriangle size={16} />
                <span style={{ fontWeight: 600 }}>Error loading data</span>
              </div>
              <p style={{ margin: '0.5rem 0 0', fontSize: '0.85rem', color: colors.textMuted }}>{integrityError}</p>
            </div>
          )}

          {integrityLoading && !integrityData ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: colors.textMuted }}>
              <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: '0.5rem' }} />
              <p style={{ margin: 0 }}>Loading...</p>
            </div>
          ) : !integrityData || !integrityData.tables || integrityData.tables.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: colors.textMuted }}>
              <Database size={40} style={{ opacity: 0.3, marginBottom: '0.75rem' }} />
              <p style={{ margin: 0 }}>No structured data found.</p>
            </div>
          ) : (
            <>
              {/* Summary Stats */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.25rem' }}>
                <StatCard label="Tables" value={integrityData.tables.length} color={colors.blue} colors={colors} />
                <StatCard label="Total Rows" value={(integrityData.total_rows || 0).toLocaleString()} color={colors.primary} colors={colors} />
                <StatCard label="Health Score" value={(integrityData.health_score || 0) + '%'} color={integrityData.health_score >= 80 ? colors.green : integrityData.health_score >= 50 ? colors.amber : colors.red} colors={colors} />
                <StatCard label="Issues" value={integrityData.issues_count || 0} color={integrityData.issues_count > 0 ? colors.amber : colors.green} colors={colors} />
              </div>

              {/* Warning Banner */}
              {hasIntegrityIssues && (
                <div style={{ marginBottom: '1rem', padding: '1rem', background: colors.amberLight, border: '1px solid ' + colors.amber + '40', borderRadius: 8, display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                  <AlertTriangle size={18} style={{ color: colors.amber, marginTop: '0.125rem' }} />
                  <div>
                    <div style={{ fontWeight: 600, color: colors.amber, marginBottom: '0.25rem' }}>Data quality issues detected</div>
                    <div style={{ fontSize: '0.85rem', color: colors.textMuted }}>Some tables have header detection or sparse column issues.</div>
                  </div>
                </div>
              )}

              {/* Tables List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {integrityData.tables.map((table, i) => {
                  const isExpanded = expandedTables.has(table.table_name);
                  const profile = tableProfiles[table.table_name];
                  const isLoadingProfile = loadingProfiles.has(table.table_name);
                  const statusColor = table.status === 'healthy' ? colors.green : table.status === 'warning' ? colors.amber : colors.red;
                  
                  return (
                    <div key={i} style={{ border: '1px solid ' + colors.divider, borderRadius: 8, overflow: 'hidden' }}>
                      <div onClick={() => toggleTableExpand(table.table_name)} style={{ padding: '0.875rem 1rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.75rem', background: colors.inputBg }}>
                        {isExpanded ? <ChevronDown size={16} style={{ color: colors.textMuted }} /> : <ChevronRight size={16} style={{ color: colors.textMuted }} />}
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: statusColor }} />
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600, fontSize: '0.9rem', color: colors.text }}>{table.table_name}</div>
                          <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>{(table.row_count || 0).toLocaleString()} rows • {table.column_count || 0} columns</div>
                        </div>
                        {table.issues && table.issues.length > 0 && (
                          <span style={{ padding: '0.2rem 0.5rem', background: colors.amberLight, color: colors.amber, borderRadius: 4, fontSize: '0.7rem', fontWeight: 600 }}>
                            {table.issues.length} issue{table.issues.length > 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                      
                      {isExpanded && (
                        <div style={{ padding: '1rem', borderTop: '1px solid ' + colors.divider }}>
                          {isLoadingProfile ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: colors.textMuted }}>
                              <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Loading...
                            </div>
                          ) : profile && profile.columns ? (
                            <div>
                              {table.issues && table.issues.length > 0 && (
                                <div style={{ marginBottom: '1rem' }}>
                                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: colors.text, marginBottom: '0.5rem' }}>Issues:</div>
                                  {table.issues.map((issue, j) => (
                                    <div key={j} style={{ fontSize: '0.8rem', color: colors.amber, marginBottom: '0.25rem' }}>• {issue.message || issue.type || String(issue)}</div>
                                  ))}
                                </div>
                              )}
                              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: colors.text, marginBottom: '0.5rem' }}>Columns:</div>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                                {profile.columns?.map((col, ci) => {
                                  const fillRate = col.fill_rate != null ? col.fill_rate : 100;
                                  return (
                                    <span key={ci} style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem', background: fillRate < 50 ? colors.amberLight : colors.inputBg, border: '1px solid ' + (fillRate < 50 ? colors.amber : colors.divider), borderRadius: 4, color: fillRate < 50 ? colors.amber : colors.textMuted }}>
                                      {col.name || 'Unknown'}: {fillRate}%
                                    </span>
                                  );
                                })}
                              </div>
                            </div>
                          ) : profile?.error ? (
                            <div style={{ color: colors.red, fontSize: '0.85rem' }}>Error: {profile.error}</div>
                          ) : (
                            <div style={{ color: colors.textMuted, fontSize: '0.85rem' }}>No profile data</div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* RELATIONSHIPS SECTION */}
      <div style={{ background: colors.card, border: '1px solid ' + colors.cardBorder, borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid ' + colors.divider, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Link2 size={20} style={{ color: colors.blue }} />
            <div>
              <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: colors.text }}>Table Relationships</h2>
              <p style={{ margin: 0, fontSize: '0.75rem', color: colors.textMuted }}>Auto-detected JOIN keys</p>
            </div>
          </div>
          <div style={{ fontSize: '0.85rem', color: colors.textMuted }}>{relationships.length} found</div>
        </div>

        <div style={{ padding: '1.25rem' }}>
          {hasIntegrityIssues && (
            <div style={{ marginBottom: '1rem', padding: '1rem', background: colors.amberLight, border: '1px solid ' + colors.amber + '40', borderRadius: 8, display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <AlertTriangle size={18} style={{ color: colors.amber, marginTop: '0.125rem' }} />
              <div>
                <div style={{ fontWeight: 600, color: colors.amber, marginBottom: '0.25rem' }}>Relationships may be unreliable</div>
                <div style={{ fontSize: '0.85rem', color: colors.textMuted }}>Fix data integrity issues first.</div>
              </div>
            </div>
          )}

          {!analyzed ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>
              <Link2 size={40} style={{ color: colors.textMuted, opacity: 0.3, marginBottom: '1rem' }} />
              <p style={{ color: colors.textMuted, marginBottom: '1rem' }}>No relationships analyzed yet</p>
              <button onClick={analyzeProject} disabled={relLoading} style={{ padding: '0.6rem 1.25rem', background: colors.primary, color: 'white', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                {relLoading ? (
                  <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Analyzing...</>
                ) : (
                  <><Zap size={16} /> Analyze Relationships</>
                )}
              </button>
            </div>
          ) : (
            <>
              {/* Stats Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.25rem' }}>
                <StatCard label="Tables" value={stats?.tables_analyzed || 0} color={colors.textMuted} colors={colors} />
                <StatCard label="Relationships" value={relationships.length} color={colors.blue} colors={colors} />
                <StatCard label="Auto-matched" value={autoMatched.length} color={colors.green} colors={colors} />
                <StatCard label="Needs Review" value={needsReview.length} color={needsReview.length > 0 ? colors.amber : colors.green} colors={colors} />
              </div>

              {/* High Confidence Section */}
              <CollapsibleSection 
                title="High Confidence Matches" 
                count={autoMatched.length} 
                icon={<CheckCircle size={18} style={{ color: colors.green }} />} 
                expanded={showHighConfidence} 
                onToggle={() => setShowHighConfidence(!showHighConfidence)} 
                colors={colors}
              >
                <RelationshipTable relationships={autoMatched} colors={colors} showActions={false} />
              </CollapsibleSection>

              {/* Needs Review Section */}
              {needsReview.length > 0 && (
                <CollapsibleSection 
                  title="Needs Review" 
                  count={needsReview.length} 
                  icon={<AlertTriangle size={18} style={{ color: colors.amber }} />} 
                  expanded={showNeedsReview} 
                  onToggle={() => setShowNeedsReview(!showNeedsReview)} 
                  colors={colors}
                >
                  <RelationshipTable relationships={needsReview} colors={colors} showActions={true} onConfirm={confirmRelationship} />
                </CollapsibleSection>
              )}

              {/* Help Info */}
              <div style={{ marginTop: '1rem', padding: '1rem', background: colors.blueLight, border: '1px solid ' + colors.blue + '40', borderRadius: 8, display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                <HelpCircle size={18} style={{ color: colors.blue, marginTop: '0.125rem' }} />
                <div>
                  <div style={{ fontWeight: 600, color: colors.blue, marginBottom: '0.25rem' }}>How relationships improve queries</div>
                  <div style={{ fontSize: '0.85rem', color: colors.textMuted }}>The system uses these to JOIN data across files automatically.</div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function StatCard({ label, value, color, colors }) {
  return (
    <div style={{ padding: '1rem', background: colors.inputBg, border: '1px solid ' + colors.divider, borderRadius: 8, textAlign: 'center' }}>
      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: color, fontFamily: 'monospace' }}>{value}</div>
      <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>{label}</div>
    </div>
  );
}

function CollapsibleSection({ title, count, icon, expanded, onToggle, children, colors }) {
  return (
    <div style={{ border: '1px solid ' + colors.divider, borderRadius: 8, overflow: 'hidden', marginBottom: '1rem' }}>
      <button onClick={onToggle} style={{ width: '100%', padding: '0.875rem 1rem', background: colors.inputBg, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {expanded ? <ChevronDown size={16} style={{ color: colors.textMuted }} /> : <ChevronRight size={16} style={{ color: colors.textMuted }} />}
          {icon}
          <span style={{ fontWeight: 600, color: colors.text }}>{title}</span>
          <span style={{ fontSize: '0.85rem', color: colors.textMuted }}>({count})</span>
        </div>
      </button>
      {expanded && <div style={{ borderTop: '1px solid ' + colors.divider }}>{children}</div>}
    </div>
  );
}

function RelationshipTable({ relationships, colors, showActions, onConfirm }) {
  return (
    <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
        <thead>
          <tr style={{ background: colors.inputBg }}>
            <th style={{ textAlign: 'left', padding: '0.75rem', fontWeight: 600, color: colors.textMuted }}>Source</th>
            <th style={{ padding: '0.75rem', width: 40 }}></th>
            <th style={{ textAlign: 'left', padding: '0.75rem', fontWeight: 600, color: colors.textMuted }}>Target</th>
            <th style={{ textAlign: 'right', padding: '0.75rem', fontWeight: 600, color: colors.textMuted }}>
              {showActions ? 'Actions' : 'Confidence'}
            </th>
          </tr>
        </thead>
        <tbody>
          {relationships.map((rel, i) => (
            <tr key={i} style={{ borderBottom: '1px solid ' + colors.divider }}>
              <td style={{ padding: '0.75rem' }}>
                <span style={{ color: colors.textMuted }}>{rel.source_table}.</span>
                <span style={{ fontWeight: 500, color: colors.text }}>{rel.source_column}</span>
              </td>
              <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                <Link2 size={14} style={{ color: showActions ? colors.amber : colors.textLight }} />
              </td>
              <td style={{ padding: '0.75rem' }}>
                <span style={{ color: colors.textMuted }}>{rel.target_table}.</span>
                <span style={{ fontWeight: 500, color: colors.text }}>{rel.target_column}</span>
              </td>
              <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                {showActions ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem' }}>
                    <button onClick={() => onConfirm(rel, true)} style={{ padding: '0.35rem', borderRadius: 4, background: colors.greenLight, border: 'none', cursor: 'pointer', color: colors.green }} title="Confirm">
                      <Check size={14} />
                    </button>
                    <button onClick={() => onConfirm(rel, false)} style={{ padding: '0.35rem', borderRadius: 4, background: colors.redLight, border: 'none', cursor: 'pointer', color: colors.red }} title="Reject">
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <span style={{ padding: '0.2rem 0.5rem', borderRadius: 4, fontSize: '0.75rem', fontWeight: 600, background: rel.confidence >= 0.95 ? colors.greenLight : rel.confidence >= 0.85 ? colors.blueLight : colors.inputBg, color: rel.confidence >= 0.95 ? colors.green : rel.confidence >= 0.85 ? colors.blue : colors.textMuted }}>
                    {Math.round(rel.confidence * 100)}%
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
