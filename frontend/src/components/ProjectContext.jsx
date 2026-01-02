/**
 * ProjectContext.jsx - System & Domain Detection Display
 * ======================================================
 * 
 * Deploy to: frontend/src/components/ProjectContext.jsx
 * 
 * PURPOSE:
 * Shows what systems and domains were detected for a project.
 * Allows users to confirm or override the auto-detection.
 * 
 * A project can have MULTIPLE systems, domains, and functional areas.
 * Example: UKG Pro + UKG Dimensions + SAP for Finance
 * 
 * FEATURES:
 * - Display detected systems with confidence scores
 * - Display detected domains and functional areas
 * - Allow user to confirm or modify selections
 * - Select engagement type
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Server, Briefcase, Layers, Check, Edit3, X, ChevronDown, ChevronRight,
  Loader2, RefreshCw, AlertCircle, Building, Settings, CheckCircle2,
  Plus, Minus
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
  white: '#f6f5fa',
  background: '#f0f2f5',
  cardBg: '#ffffff',
  text: '#1a2332',
  textMuted: '#64748b',
  border: '#e2e8f0',
  warning: '#d97706',
  success: '#22c55e',
  error: '#ef4444',
};

// Domain colors for visual distinction
const domainColors = {
  hcm: '#3B82F6',
  finance: '#10B981',
  compliance: '#8B5CF6',
  crm: '#F59E0B',
  procurement: '#EC4899',
  itsm: '#6366F1',
};

// ============================================================================
// CONFIDENCE BADGE
// ============================================================================
function ConfidenceBadge({ confidence }) {
  const pct = Math.round((confidence || 0) * 100);
  const color = pct >= 80 ? brandColors.success : pct >= 50 ? brandColors.warning : brandColors.error;
  
  return (
    <span 
      style={{
        fontSize: '11px',
        color: color,
        background: `${color}15`,
        padding: '2px 6px',
        borderRadius: '4px',
        marginLeft: '8px'
      }}
    >
      {pct}%
    </span>
  );
}

// ============================================================================
// SYSTEM CHIP
// ============================================================================
function SystemChip({ system, onRemove, editable }) {
  const c = brandColors;
  
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      background: `${c.electricBlue}10`,
      border: `1px solid ${c.electricBlue}30`,
      borderRadius: '16px',
      padding: '4px 12px',
      fontSize: '13px',
      color: c.electricBlue
    }}>
      <Server size={14} />
      <span>{system.name || system.code}</span>
      {system.confidence && <ConfidenceBadge confidence={system.confidence} />}
      {editable && onRemove && (
        <button 
          onClick={() => onRemove(system.code)}
          style={{ 
            background: 'none', 
            border: 'none', 
            cursor: 'pointer', 
            padding: '2px',
            display: 'flex',
            color: c.textMuted
          }}
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

// ============================================================================
// DOMAIN CHIP
// ============================================================================
function DomainChip({ domain, onRemove, editable }) {
  const color = domainColors[domain.code] || brandColors.accent;
  
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      background: `${color}15`,
      border: `1px solid ${color}30`,
      borderRadius: '16px',
      padding: '4px 12px',
      fontSize: '13px',
      color: color
    }}>
      <Briefcase size={14} />
      <span>{domain.name || domain.code}</span>
      {domain.confidence && <ConfidenceBadge confidence={domain.confidence} />}
      {editable && onRemove && (
        <button 
          onClick={() => onRemove(domain.code)}
          style={{ 
            background: 'none', 
            border: 'none', 
            cursor: 'pointer', 
            padding: '2px',
            display: 'flex',
            color: brandColors.textMuted
          }}
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

// ============================================================================
// FUNCTIONAL AREA CHIP
// ============================================================================
function FunctionalAreaChip({ area, onRemove, editable }) {
  const color = domainColors[area.domain_code || area.domain] || brandColors.accent;
  
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      background: `${color}10`,
      border: `1px solid ${color}20`,
      borderRadius: '12px',
      padding: '2px 10px',
      fontSize: '12px',
      color: brandColors.text
    }}>
      <Layers size={12} style={{ color }} />
      <span>{area.name || area.area || area.code}</span>
      {editable && onRemove && (
        <button 
          onClick={() => onRemove(area)}
          style={{ 
            background: 'none', 
            border: 'none', 
            cursor: 'pointer', 
            padding: '2px',
            display: 'flex',
            color: brandColors.textMuted
          }}
        >
          <X size={12} />
        </button>
      )}
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function ProjectContext({ projectId, projectName, compact = false }) {
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState(!compact);
  
  // Reference data for editing
  const [allSystems, setAllSystems] = useState([]);
  const [allDomains, setAllDomains] = useState([]);
  const [allFunctionalAreas, setAllFunctionalAreas] = useState([]);
  const [engagementTypes, setEngagementTypes] = useState([]);
  
  // Edit state
  const [editSystems, setEditSystems] = useState([]);
  const [editDomains, setEditDomains] = useState([]);
  const [editFunctionalAreas, setEditFunctionalAreas] = useState([]);
  const [editEngagementType, setEditEngagementType] = useState('');
  
  const c = brandColors;
  const project = projectName || projectId;
  
  // Load context
  const loadContext = useCallback(async () => {
    if (!project) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const res = await api.get(`/reference/projects/${encodeURIComponent(project)}/context`);
      setContext(res.data);
      
      // Initialize edit state
      setEditSystems(res.data?.systems || []);
      setEditDomains(res.data?.domains || []);
      setEditFunctionalAreas(res.data?.functional_areas || []);
      setEditEngagementType(res.data?.engagement_type || '');
    } catch (err) {
      if (err.response?.status !== 404) {
        setError(err.message || 'Failed to load context');
      }
    } finally {
      setLoading(false);
    }
  }, [project]);
  
  // Load reference data for editing
  const loadReferenceData = useCallback(async () => {
    try {
      const [systemsRes, domainsRes, areasRes, typesRes] = await Promise.all([
        api.get('/reference/systems'),
        api.get('/reference/domains'),
        api.get('/reference/functional-areas'),
        api.get('/reference/engagement-types')
      ]);
      
      setAllSystems(systemsRes.data || []);
      setAllDomains(domainsRes.data || []);
      setAllFunctionalAreas(areasRes.data || []);
      setEngagementTypes(typesRes.data || []);
    } catch (err) {
      console.error('Failed to load reference data:', err);
    }
  }, []);
  
  useEffect(() => {
    loadContext();
  }, [loadContext]);
  
  useEffect(() => {
    if (editing) {
      loadReferenceData();
    }
  }, [editing, loadReferenceData]);
  
  // Run detection
  const runDetection = async () => {
    if (!project) return;
    
    setLoading(true);
    try {
      await api.post(`/reference/projects/${encodeURIComponent(project)}/detect`);
      await loadContext();
    } catch (err) {
      setError(err.message || 'Detection failed');
    } finally {
      setLoading(false);
    }
  };
  
  // Save changes
  const saveChanges = async () => {
    if (!project) return;
    
    setSaving(true);
    try {
      await api.post(`/reference/projects/${encodeURIComponent(project)}/context/confirm`, {
        system_codes: editSystems,
        domain_codes: editDomains,
        functional_areas: editFunctionalAreas,
        engagement_type: editEngagementType || null
      });
      
      await loadContext();
      setEditing(false);
    } catch (err) {
      setError(err.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };
  
  // Cancel editing
  const cancelEdit = () => {
    setEditSystems(context?.systems || []);
    setEditDomains(context?.domains || []);
    setEditFunctionalAreas(context?.functional_areas || []);
    setEditEngagementType(context?.engagement_type || '');
    setEditing(false);
  };
  
  // Get detected context details
  const detectedContext = context?.detected_context || {};
  const systems = detectedContext.systems || [];
  const domains = detectedContext.domains || [];
  const functionalAreas = detectedContext.functional_areas || [];
  const isConfirmed = context?.context_confirmed;
  
  // Compact view
  if (compact && !expanded) {
    return (
      <div 
        onClick={() => setExpanded(true)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 12px',
          background: c.cardBg,
          border: `1px solid ${c.border}`,
          borderRadius: '8px',
          cursor: 'pointer',
          fontSize: '13px'
        }}
      >
        <Server size={16} style={{ color: c.electricBlue }} />
        {systems.length > 0 ? (
          <span>{systems.map(s => s.name || s.code).join(', ')}</span>
        ) : (
          <span style={{ color: c.textMuted }}>No system detected</span>
        )}
        <ChevronRight size={16} style={{ color: c.textMuted, marginLeft: 'auto' }} />
      </div>
    );
  }
  
  return (
    <div style={{
      background: c.cardBg,
      border: `1px solid ${c.border}`,
      borderRadius: '12px',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: `1px solid ${c.border}`,
        background: c.background
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Building size={18} style={{ color: c.accent }} />
          <span style={{ fontWeight: 600, color: c.text }}>Project Context</span>
          {isConfirmed && (
            <CheckCircle2 size={16} style={{ color: c.success }} title="Confirmed" />
          )}
        </div>
        
        <div style={{ display: 'flex', gap: '8px' }}>
          {!editing && (
            <>
              <button
                onClick={runDetection}
                disabled={loading}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '6px 12px',
                  background: 'transparent',
                  border: `1px solid ${c.border}`,
                  borderRadius: '6px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontSize: '12px',
                  color: c.textMuted
                }}
              >
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                Re-detect
              </button>
              <button
                onClick={() => setEditing(true)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '6px 12px',
                  background: c.accent,
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  color: 'white'
                }}
              >
                <Edit3 size={14} />
                Edit
              </button>
            </>
          )}
          
          {editing && (
            <>
              <button
                onClick={cancelEdit}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '6px 12px',
                  background: 'transparent',
                  border: `1px solid ${c.border}`,
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  color: c.textMuted
                }}
              >
                <X size={14} />
                Cancel
              </button>
              <button
                onClick={saveChanges}
                disabled={saving}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '6px 12px',
                  background: c.success,
                  border: 'none',
                  borderRadius: '6px',
                  cursor: saving ? 'not-allowed' : 'pointer',
                  fontSize: '12px',
                  color: 'white'
                }}
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                {isConfirmed ? 'Update' : 'Confirm'}
              </button>
            </>
          )}
          
          {compact && (
            <button
              onClick={() => setExpanded(false)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '4px',
                color: c.textMuted
              }}
            >
              <ChevronDown size={16} />
            </button>
          )}
        </div>
      </div>
      
      {/* Loading */}
      {loading && (
        <div style={{ padding: '32px', textAlign: 'center' }}>
          <Loader2 size={24} className="animate-spin" style={{ color: c.accent }} />
        </div>
      )}
      
      {/* Error */}
      {error && (
        <div style={{ 
          padding: '16px', 
          background: `${c.error}10`, 
          color: c.error,
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <AlertCircle size={16} />
          {error}
        </div>
      )}
      
      {/* Content */}
      {!loading && !error && (
        <div style={{ padding: '16px' }}>
          {/* Systems */}
          <div style={{ marginBottom: '16px' }}>
            <div style={{ 
              fontSize: '12px', 
              fontWeight: 600, 
              color: c.textMuted, 
              marginBottom: '8px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Systems
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {editing ? (
                <>
                  {editSystems.map((code, i) => {
                    const sys = allSystems.find(s => s.code === code) || { code, name: code };
                    return (
                      <SystemChip 
                        key={i} 
                        system={sys} 
                        editable 
                        onRemove={(c) => setEditSystems(prev => prev.filter(x => x !== c))}
                      />
                    );
                  })}
                  <select
                    value=""
                    onChange={(e) => {
                      if (e.target.value && !editSystems.includes(e.target.value)) {
                        setEditSystems([...editSystems, e.target.value]);
                      }
                    }}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '16px',
                      border: `1px dashed ${c.border}`,
                      background: 'transparent',
                      fontSize: '13px',
                      color: c.textMuted,
                      cursor: 'pointer'
                    }}
                  >
                    <option value="">+ Add system...</option>
                    {allSystems.filter(s => !editSystems.includes(s.code)).map(s => (
                      <option key={s.code} value={s.code}>{s.name} ({s.vendor})</option>
                    ))}
                  </select>
                </>
              ) : (
                systems.length > 0 ? (
                  systems.map((sys, i) => <SystemChip key={i} system={sys} />)
                ) : (
                  <span style={{ color: c.textMuted, fontSize: '13px' }}>No systems detected</span>
                )
              )}
            </div>
          </div>
          
          {/* Domains */}
          <div style={{ marginBottom: '16px' }}>
            <div style={{ 
              fontSize: '12px', 
              fontWeight: 600, 
              color: c.textMuted, 
              marginBottom: '8px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Domains
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {editing ? (
                <>
                  {editDomains.map((code, i) => {
                    const dom = allDomains.find(d => d.code === code) || { code, name: code };
                    return (
                      <DomainChip 
                        key={i} 
                        domain={dom} 
                        editable 
                        onRemove={(c) => setEditDomains(prev => prev.filter(x => x !== c))}
                      />
                    );
                  })}
                  <select
                    value=""
                    onChange={(e) => {
                      if (e.target.value && !editDomains.includes(e.target.value)) {
                        setEditDomains([...editDomains, e.target.value]);
                      }
                    }}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '16px',
                      border: `1px dashed ${c.border}`,
                      background: 'transparent',
                      fontSize: '13px',
                      color: c.textMuted,
                      cursor: 'pointer'
                    }}
                  >
                    <option value="">+ Add domain...</option>
                    {allDomains.filter(d => !editDomains.includes(d.code)).map(d => (
                      <option key={d.code} value={d.code}>{d.name}</option>
                    ))}
                  </select>
                </>
              ) : (
                domains.length > 0 ? (
                  domains.map((dom, i) => <DomainChip key={i} domain={dom} />)
                ) : (
                  <span style={{ color: c.textMuted, fontSize: '13px' }}>No domains detected</span>
                )
              )}
            </div>
          </div>
          
          {/* Functional Areas */}
          {(functionalAreas.length > 0 || editing) && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ 
                fontSize: '12px', 
                fontWeight: 600, 
                color: c.textMuted, 
                marginBottom: '8px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Functional Areas
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {editing ? (
                  <>
                    {editFunctionalAreas.map((fa, i) => (
                      <FunctionalAreaChip 
                        key={i} 
                        area={fa} 
                        editable 
                        onRemove={() => setEditFunctionalAreas(prev => prev.filter((_, j) => j !== i))}
                      />
                    ))}
                    <select
                      value=""
                      onChange={(e) => {
                        const fa = allFunctionalAreas.find(f => f.code === e.target.value);
                        if (fa) {
                          setEditFunctionalAreas([...editFunctionalAreas, { 
                            domain: fa.domain_code, 
                            area: fa.code,
                            name: fa.name
                          }]);
                        }
                      }}
                      style={{
                        padding: '2px 8px',
                        borderRadius: '12px',
                        border: `1px dashed ${c.border}`,
                        background: 'transparent',
                        fontSize: '12px',
                        color: c.textMuted,
                        cursor: 'pointer'
                      }}
                    >
                      <option value="">+ Add area...</option>
                      {allFunctionalAreas.map(fa => (
                        <option key={fa.code} value={fa.code}>
                          {fa.domain_name} › {fa.name}
                        </option>
                      ))}
                    </select>
                  </>
                ) : (
                  functionalAreas.map((fa, i) => <FunctionalAreaChip key={i} area={fa} />)
                )}
              </div>
            </div>
          )}
          
          {/* Engagement Type */}
          <div>
            <div style={{ 
              fontSize: '12px', 
              fontWeight: 600, 
              color: c.textMuted, 
              marginBottom: '8px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Engagement Type
            </div>
            {editing ? (
              <select
                value={editEngagementType}
                onChange={(e) => setEditEngagementType(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: `1px solid ${c.border}`,
                  background: 'white',
                  fontSize: '13px',
                  color: c.text,
                  width: '100%',
                  maxWidth: '300px'
                }}
              >
                <option value="">Select engagement type...</option>
                {engagementTypes.map(t => (
                  <option key={t.code} value={t.code}>{t.name}</option>
                ))}
              </select>
            ) : (
              <span style={{ 
                fontSize: '13px', 
                color: context?.engagement_type ? c.text : c.textMuted 
              }}>
                {engagementTypes.find(t => t.code === context?.engagement_type)?.name || 
                 context?.engagement_type || 
                 'Not specified'}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// COMPACT INLINE VERSION
// ============================================================================
export function ProjectContextBadge({ projectId, projectName }) {
  const [context, setContext] = useState(null);
  const project = projectName || projectId;
  
  useEffect(() => {
    if (!project) return;
    
    api.get(`/reference/projects/${encodeURIComponent(project)}/context`)
      .then(res => setContext(res.data))
      .catch(() => {});
  }, [project]);
  
  if (!context?.detected_context?.systems?.length) {
    return null;
  }
  
  const sys = context.detected_context.systems[0];
  
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      fontSize: '11px',
      color: brandColors.electricBlue,
      background: `${brandColors.electricBlue}10`,
      padding: '2px 8px',
      borderRadius: '10px'
    }}>
      <Server size={12} />
      {sys.name || sys.code}
    </span>
  );
}
