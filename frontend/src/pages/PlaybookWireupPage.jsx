/**
 * PlaybookWireupPage.jsx - Build Playbook from Findings
 * ======================================================
 * 
 * Phase 4A.6: Playbook Wire-up
 * 
 * Select findings → Generate action items → Save playbook
 * Matches mockup Screen 6 design.
 * 
 * Created: January 15, 2026
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  ClipboardList, AlertTriangle, AlertCircle, Info, Check, 
  Loader2, User, Calendar, Clock, Save, FileText, Share2,
  ChevronRight, Sparkles, ArrowRight
} from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import { PageHeader } from '../components/ui';
import api from '../services/api';

// =============================================================================
// COLORS
// =============================================================================

const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f8fafc',
  card: dark ? '#242b3d' : '#ffffff',
  border: dark ? '#2d3548' : '#e2e8f0',
  text: dark ? '#e8eaed' : '#1a2332',
  textMuted: dark ? '#8b95a5' : '#64748b',
  textLight: dark ? '#6b7280' : '#9ca3af',
  primary: '#83b16d',
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.1)',
  accent: '#285390',
  critical: '#dc2626',
  criticalBg: dark ? 'rgba(220, 38, 38, 0.15)' : '#fef2f2',
  warning: '#d97706',
  warningBg: dark ? 'rgba(217, 119, 6, 0.15)' : '#fffbeb',
  info: '#0ea5e9',
  infoBg: dark ? 'rgba(14, 165, 233, 0.15)' : '#f0f9ff',
  inputBg: dark ? '#1e2433' : '#f8fafc',
  hoverBg: dark ? '#2d3548' : '#f1f5f9',
});

// =============================================================================
// FINDING CHECKBOX COMPONENT
// =============================================================================

function FindingCheckbox({ finding, selected, onToggle, colors }) {
  const severityConfig = {
    critical: { color: colors.critical, label: 'Critical' },
    warning: { color: colors.warning, label: 'Warning' },
    info: { color: colors.info, label: 'Info' },
  };
  
  const config = severityConfig[finding.severity] || severityConfig.info;
  
  return (
    <label
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.75rem',
        padding: '0.875rem 1rem',
        borderRadius: 8,
        border: `1px solid ${selected ? colors.primary : colors.border}`,
        background: selected ? colors.primaryLight : colors.card,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        marginBottom: '0.5rem',
      }}
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={() => onToggle(finding.id)}
        style={{
          width: 18,
          height: 18,
          marginTop: 2,
          accentColor: colors.primary,
          cursor: 'pointer',
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ 
          fontSize: '0.9rem', 
          fontWeight: 500, 
          color: colors.text,
          marginBottom: '0.25rem'
        }}>
          {finding.title}
        </div>
        <div style={{ 
          fontSize: '0.75rem', 
          color: colors.textMuted,
          display: 'flex',
          gap: '0.5rem',
          alignItems: 'center',
        }}>
          <span style={{ color: config.color, fontWeight: 600 }}>
            {config.label}
          </span>
          <span>·</span>
          <span>{finding.affected_count?.toLocaleString() || 0} records</span>
        </div>
      </div>
    </label>
  );
}

// =============================================================================
// ACTION ITEM COMPONENT
// =============================================================================

function ActionItem({ action, index, colors, onAssigneeChange, onDueDateChange }) {
  const [editingAssignee, setEditingAssignee] = useState(false);
  const [editingDue, setEditingDue] = useState(false);
  
  const formatHours = (hours) => {
    if (hours < 1) return `${Math.round(hours * 60)} min`;
    if (hours === 1) return '1 hour';
    return `${hours} hours`;
  };
  
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };
  
  return (
    <div style={{
      display: 'flex',
      gap: '1rem',
      padding: '1.25rem',
      background: colors.card,
      border: `1px solid ${colors.border}`,
      borderRadius: 10,
      marginBottom: '0.75rem',
    }}>
      {/* Sequence number */}
      <div style={{
        width: 32,
        height: 32,
        borderRadius: 8,
        background: colors.primaryLight,
        color: colors.primary,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        fontSize: '0.9rem',
        flexShrink: 0,
      }}>
        {index + 1}
      </div>
      
      {/* Content */}
      <div style={{ flex: 1 }}>
        <div style={{ 
          fontSize: '0.95rem', 
          fontWeight: 600, 
          color: colors.text,
          marginBottom: '0.5rem'
        }}>
          {action.title}
        </div>
        <div style={{ 
          fontSize: '0.85rem', 
          color: colors.textMuted,
          marginBottom: '0.75rem',
          lineHeight: 1.5,
        }}>
          {action.description}
        </div>
        
        {/* Meta row */}
        <div style={{
          display: 'flex',
          gap: '1.25rem',
          fontSize: '0.8rem',
          color: colors.textMuted,
          flexWrap: 'wrap',
        }}>
          {/* Assignee */}
          <div 
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.35rem',
              cursor: 'pointer',
            }}
            onClick={() => setEditingAssignee(true)}
          >
            <User size={14} />
            {editingAssignee ? (
              <input
                autoFocus
                defaultValue={action.assignee_name}
                style={{
                  border: `1px solid ${colors.border}`,
                  borderRadius: 4,
                  padding: '2px 6px',
                  fontSize: '0.8rem',
                  width: 100,
                  background: colors.inputBg,
                  color: colors.text,
                }}
                onBlur={(e) => {
                  onAssigneeChange(action.id, e.target.value);
                  setEditingAssignee(false);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    onAssigneeChange(action.id, e.target.value);
                    setEditingAssignee(false);
                  }
                }}
              />
            ) : (
              <span>{action.assignee_name}</span>
            )}
          </div>
          
          {/* Due date */}
          <div 
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.35rem',
              cursor: 'pointer',
            }}
          >
            <Calendar size={14} />
            {editingDue ? (
              <input
                type="date"
                autoFocus
                defaultValue={action.due_date}
                style={{
                  border: `1px solid ${colors.border}`,
                  borderRadius: 4,
                  padding: '2px 6px',
                  fontSize: '0.8rem',
                  background: colors.inputBg,
                  color: colors.text,
                }}
                onBlur={(e) => {
                  onDueDateChange(action.id, e.target.value);
                  setEditingDue(false);
                }}
              />
            ) : (
              <span onClick={() => setEditingDue(true)}>
                Due: {formatDate(action.due_date)}
              </span>
            )}
          </div>
          
          {/* Effort */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Clock size={14} />
            <span>Est: {formatHours(action.effort_hours)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN PAGE COMPONENT
// =============================================================================

export default function PlaybookWireupPage() {
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  const navigate = useNavigate();
  const location = useLocation();
  const { activeProject, customerName, projectName } = useProject();
  
  // State
  const [findings, setFindings] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [playbook, setPlaybook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  
  // Pre-selected findings from navigation
  const preSelectedIds = location.state?.selectedFindingIds || [];
  
  // Load findings
  useEffect(() => {
    if (activeProject?.name) {
      loadFindings();
    }
  }, [activeProject?.name]);
  
  const loadFindings = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get(`/findings/${activeProject.id}/findings`);
      setFindings(response.data.findings || []);
      
      // Pre-select if passed from FindingsDashboard
      if (preSelectedIds.length > 0) {
        setSelectedIds(new Set(preSelectedIds));
      }
    } catch (err) {
      console.error('Error loading findings:', err);
      setError('Failed to load findings');
    } finally {
      setLoading(false);
    }
  };
  
  // Toggle finding selection
  const toggleFinding = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
    // Clear existing playbook when selection changes
    setPlaybook(null);
  };
  
  // Generate playbook from selected findings
  const generatePlaybook = async () => {
    if (selectedIds.size === 0) return;
    
    setGenerating(true);
    setError(null);
    
    try {
      const selectedFindings = findings.filter(f => selectedIds.has(f.id));
      
      const response = await api.post('/remediation/generate', {
        project_id: activeProject.id,
        project_name: activeProject.name,
        customer_name: customerName || activeProject.customer || activeProject.name,
        findings: selectedFindings,
        default_assignee: 'Project Lead',
      });
      
      setPlaybook(response.data);
    } catch (err) {
      console.error('Error generating playbook:', err);
      setError('Failed to generate playbook');
    } finally {
      setGenerating(false);
    }
  };
  
  // Save playbook
  const savePlaybook = async () => {
    if (!playbook) return;
    
    setSaving(true);
    try {
      // Playbook is already saved on generation, just navigate to progress tracker
      navigate(`/progress/${playbook.id}`);
    } catch (err) {
      console.error('Error saving playbook:', err);
      setError('Failed to save playbook');
    } finally {
      setSaving(false);
    }
  };
  
  // Update action assignee
  const updateAssignee = (actionId, newAssignee) => {
    if (!playbook) return;
    setPlaybook(prev => ({
      ...prev,
      actions: prev.actions.map(a => 
        a.id === actionId ? { ...a, assignee_name: newAssignee } : a
      )
    }));
  };
  
  // Update action due date
  const updateDueDate = (actionId, newDate) => {
    if (!playbook) return;
    setPlaybook(prev => ({
      ...prev,
      actions: prev.actions.map(a => 
        a.id === actionId ? { ...a, due_date: newDate } : a
      )
    }));
  };
  
  // Calculate totals
  const totals = useMemo(() => {
    if (!playbook) return { actions: 0, hours: 0 };
    return {
      actions: playbook.actions.length,
      hours: playbook.total_effort_hours,
    };
  }, [playbook]);
  
  // No project selected
  if (!activeProject) {
    return (
      <div>
        <PageHeader
          icon={ClipboardList}
          title="Build Playbook"
          subtitle="Select findings to create an action plan"
        />
        <div style={{
          textAlign: 'center',
          padding: '4rem 2rem',
          color: colors.textMuted,
        }}>
          <ClipboardList size={48} color={colors.textMuted} style={{ marginBottom: '1rem', opacity: 0.5 }} />
          <h3 style={{ color: colors.text, marginBottom: '0.5rem' }}>Select a Project</h3>
          <p>Choose a project from the selector above to build a playbook.</p>
        </div>
      </div>
    );
  }
  
  return (
    <div>
      <PageHeader
        icon={ClipboardList}
        title="Build Playbook"
        subtitle="Select findings to create an action plan"
        breadcrumbs={[
          { label: customerName || activeProject.name },
          { label: 'Build Playbook' },
        ]}
      />
      
      {/* Error */}
      {error && (
        <div style={{
          padding: '1rem 1.5rem',
          background: colors.criticalBg,
          border: `1px solid ${colors.critical}30`,
          borderRadius: 8,
          color: colors.critical,
          marginBottom: '1.5rem',
        }}>
          {error}
        </div>
      )}
      
      {/* Loading */}
      {loading ? (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '4rem',
          gap: '0.75rem',
          color: colors.textMuted,
        }}>
          <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
          <span>Loading findings...</span>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: '320px 1fr',
          gap: '1.5rem',
          minHeight: 500,
        }}>
          {/* Left Sidebar - Finding Selection */}
          <div style={{
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 12,
            padding: '1.25rem',
            height: 'fit-content',
            maxHeight: 'calc(100vh - 200px)',
            overflow: 'auto',
          }}>
            <h3 style={{ 
              fontFamily: "'Sora', sans-serif",
              fontSize: '0.9rem',
              fontWeight: 600,
              color: colors.text,
              marginBottom: '1rem',
            }}>
              Select Findings
            </h3>
            
            {findings.length === 0 ? (
              <p style={{ 
                fontSize: '0.85rem', 
                color: colors.textMuted,
                textAlign: 'center',
                padding: '2rem 0',
              }}>
                No findings available. Upload data to generate findings.
              </p>
            ) : (
              <>
                {findings.map(finding => (
                  <FindingCheckbox
                    key={finding.id}
                    finding={finding}
                    selected={selectedIds.has(finding.id)}
                    onToggle={toggleFinding}
                    colors={colors}
                  />
                ))}
                
                {/* Selection summary + Generate button */}
                <div style={{
                  marginTop: '1rem',
                  paddingTop: '1rem',
                  borderTop: `1px solid ${colors.border}`,
                }}>
                  <div style={{ 
                    fontSize: '0.8rem', 
                    color: colors.textMuted,
                    marginBottom: '0.75rem',
                  }}>
                    {selectedIds.size} finding{selectedIds.size !== 1 ? 's' : ''} selected
                  </div>
                  <button
                    onClick={generatePlaybook}
                    disabled={selectedIds.size === 0 || generating}
                    style={{
                      width: '100%',
                      padding: '0.75rem 1rem',
                      background: selectedIds.size === 0 ? colors.border : colors.primary,
                      border: 'none',
                      borderRadius: 8,
                      color: selectedIds.size === 0 ? colors.textMuted : '#fff',
                      fontWeight: 600,
                      fontSize: '0.9rem',
                      cursor: selectedIds.size === 0 ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem',
                    }}
                  >
                    {generating ? (
                      <>
                        <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles size={16} />
                        Generate Playbook
                      </>
                    )}
                  </button>
                </div>
              </>
            )}
          </div>
          
          {/* Right Panel - Playbook Actions */}
          <div style={{
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 12,
            padding: '1.5rem',
          }}>
            {!playbook ? (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                minHeight: 400,
                color: colors.textMuted,
                textAlign: 'center',
              }}>
                <ClipboardList size={48} color={colors.textMuted} style={{ marginBottom: '1rem', opacity: 0.3 }} />
                <h3 style={{ color: colors.text, marginBottom: '0.5rem', fontWeight: 600 }}>
                  Select findings to build your playbook
                </h3>
                <p style={{ fontSize: '0.9rem', maxWidth: 350 }}>
                  Choose one or more findings from the left panel, then click "Generate Playbook" to create your action items.
                </p>
              </div>
            ) : (
              <>
                {/* Playbook header */}
                <div style={{ marginBottom: '1.5rem' }}>
                  <h3 style={{ 
                    fontFamily: "'Sora', sans-serif",
                    fontSize: '1.1rem',
                    fontWeight: 600,
                    color: colors.text,
                    marginBottom: '0.35rem',
                  }}>
                    {playbook.name}
                  </h3>
                  <p style={{ 
                    fontSize: '0.85rem', 
                    color: colors.textMuted,
                  }}>
                    {selectedIds.size} finding{selectedIds.size !== 1 ? 's' : ''} · {totals.actions} action items · Est. {totals.hours} hours
                  </p>
                </div>
                
                {/* Action items */}
                <div style={{ marginBottom: '1.5rem' }}>
                  {playbook.actions.map((action, index) => (
                    <ActionItem
                      key={action.id}
                      action={action}
                      index={index}
                      colors={colors}
                      onAssigneeChange={updateAssignee}
                      onDueDateChange={updateDueDate}
                    />
                  ))}
                </div>
                
                {/* Action buttons */}
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <button
                    onClick={savePlaybook}
                    disabled={saving}
                    style={{
                      padding: '0.75rem 1.25rem',
                      background: colors.primary,
                      border: 'none',
                      borderRadius: 8,
                      color: '#fff',
                      fontWeight: 600,
                      fontSize: '0.9rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                    }}
                  >
                    {saving ? (
                      <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                    ) : (
                      <Save size={16} />
                    )}
                    Save & Track Progress
                  </button>
                  
                  <button
                    style={{
                      padding: '0.75rem 1.25rem',
                      background: colors.inputBg,
                      border: `1px solid ${colors.border}`,
                      borderRadius: 8,
                      color: colors.text,
                      fontWeight: 500,
                      fontSize: '0.9rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                    }}
                  >
                    <FileText size={16} />
                    Export to PDF
                  </button>
                  
                  <button
                    style={{
                      padding: '0.75rem 1.25rem',
                      background: colors.inputBg,
                      border: `1px solid ${colors.border}`,
                      borderRadius: 8,
                      color: colors.text,
                      fontWeight: 500,
                      fontSize: '0.9rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                    }}
                  >
                    <Share2 size={16} />
                    Share with Client
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
      
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
