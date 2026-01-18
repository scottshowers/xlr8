/**
 * PlaybookViewer.jsx
 * ==================
 * 
 * Universal playbook viewer using the Playbook Framework.
 * Supports all playbook types: vendor, xlr8, generated, discovery, comparison.
 * 
 * Clean rebuild - framework-native, no legacy baggage.
 * 
 * Created: January 18, 2026
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Play, CheckCircle, XCircle, AlertTriangle, Clock, 
  ChevronRight, ChevronDown, Loader2, RefreshCw,
  FileText, Eye, EyeOff, Check, X
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

// =============================================================================
// CONSTANTS
// =============================================================================

const STATUS_CONFIG = {
  not_started: { label: 'Not Started', color: '#6b7280', bg: '#f3f4f6', icon: Clock },
  blocked: { label: 'Blocked', color: '#dc2626', bg: '#fee2e2', icon: XCircle },
  in_progress: { label: 'In Progress', color: '#d97706', bg: '#fef3c7', icon: RefreshCw },
  complete: { label: 'Complete', color: '#059669', bg: '#d1fae5', icon: CheckCircle },
  skipped: { label: 'Skipped', color: '#6b7280', bg: '#e5e7eb', icon: X },
};

const SEVERITY_CONFIG = {
  critical: { label: 'Critical', color: '#dc2626', bg: '#fee2e2' },
  high: { label: 'High', color: '#ea580c', bg: '#ffedd5' },
  medium: { label: 'Medium', color: '#d97706', bg: '#fef3c7' },
  low: { label: 'Low', color: '#0891b2', bg: '#cffafe' },
  info: { label: 'Info', color: '#6b7280', bg: '#f3f4f6' },
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function PlaybookViewer({ playbookId = 'year-end', projectId, onClose }) {
  // Core state
  const [definition, setDefinition] = useState(null);
  const [instance, setInstance] = useState(null);
  const [progress, setProgress] = useState(null);
  const [stepDetails, setStepDetails] = useState({});
  
  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedStep, setSelectedStep] = useState(null);
  const [executing, setExecuting] = useState(null);
  const [executingAll, setExecutingAll] = useState(false);

  // =============================================================================
  // DATA LOADING
  // =============================================================================

  const loadDefinition = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/playbooks/${playbookId}/definition`);
      const data = await res.json();
      if (data.success) {
        setDefinition(data.playbook);
        if (data.playbook.steps?.length > 0) {
          setSelectedStep(data.playbook.steps[0].id);
        }
      } else {
        setError(data.error || 'Failed to load playbook');
      }
    } catch (err) {
      setError(`Failed to load playbook: ${err.message}`);
    }
  }, [playbookId]);

  const loadInstance = useCallback(async () => {
    if (!projectId) return;
    try {
      const res = await fetch(`${API_BASE}/api/playbooks/${playbookId}/instance/${projectId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ create_if_missing: true })
      });
      const data = await res.json();
      if (data.success) {
        setInstance(data);
        loadProgress(data.instance_id);
      }
    } catch (err) {
      console.error('Failed to load instance:', err);
    }
  }, [playbookId, projectId]);

  const loadProgress = useCallback(async (instanceId) => {
    if (!instanceId) return;
    try {
      const res = await fetch(`${API_BASE}/api/playbooks/instance/${instanceId}/progress`);
      const data = await res.json();
      if (data.success) {
        setProgress(data);
      }
    } catch (err) {
      console.error('Failed to load progress:', err);
    }
  }, []);

  const loadStepDetails = useCallback(async (stepId) => {
    if (!instance?.instance_id) return;
    try {
      const res = await fetch(
        `${API_BASE}/api/playbooks/instance/${instance.instance_id}/step/${stepId}`
      );
      const data = await res.json();
      if (data.success) {
        setStepDetails(prev => ({ ...prev, [stepId]: data.step }));
      }
    } catch (err) {
      console.error('Failed to load step details:', err);
    }
  }, [instance?.instance_id]);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await loadDefinition();
      await loadInstance();
      setLoading(false);
    };
    init();
  }, [loadDefinition, loadInstance]);

  // Load step details when selected
  useEffect(() => {
    if (selectedStep && instance?.instance_id) {
      loadStepDetails(selectedStep);
    }
  }, [selectedStep, instance?.instance_id, loadStepDetails]);

  // =============================================================================
  // ACTIONS
  // =============================================================================

  const executeStep = async (stepId) => {
    if (!instance?.instance_id) return;
    
    setExecuting(stepId);
    try {
      const res = await fetch(
        `${API_BASE}/api/playbooks/instance/${instance.instance_id}/step/${stepId}/execute`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ force_refresh: true })
        }
      );
      await res.json();
      await loadProgress(instance.instance_id);
      await loadStepDetails(stepId);
    } catch (err) {
      console.error('Execute step failed:', err);
    } finally {
      setExecuting(null);
    }
  };

  const executeAllSteps = async () => {
    if (!instance?.instance_id) return;
    
    setExecutingAll(true);
    try {
      await fetch(
        `${API_BASE}/api/playbooks/instance/${instance.instance_id}/execute-all`,
        { method: 'POST' }
      );
      await loadProgress(instance.instance_id);
      if (selectedStep) {
        await loadStepDetails(selectedStep);
      }
    } catch (err) {
      console.error('Execute all failed:', err);
    } finally {
      setExecutingAll(false);
    }
  };

  const updateStepStatus = async (stepId, status) => {
    if (!instance?.instance_id) return;
    
    try {
      await fetch(
        `${API_BASE}/api/playbooks/instance/${instance.instance_id}/step/${stepId}/status`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status })
        }
      );
      await loadProgress(instance.instance_id);
      await loadStepDetails(stepId);
    } catch (err) {
      console.error('Update status failed:', err);
    }
  };

  const updateFinding = async (findingId, status) => {
    if (!instance?.instance_id) return;
    
    try {
      await fetch(
        `${API_BASE}/api/playbooks/instance/${instance.instance_id}/finding/${findingId}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status })
        }
      );
      if (selectedStep) {
        await loadStepDetails(selectedStep);
        await loadProgress(instance.instance_id);
      }
    } catch (err) {
      console.error('Update finding failed:', err);
    }
  };

  // =============================================================================
  // HELPERS
  // =============================================================================

  const getStepStatus = (stepId) => {
    const details = stepDetails[stepId];
    return details?.status || 'not_started';
  };

  const getStepFindings = (stepId) => {
    const details = stepDetails[stepId];
    return {
      total: details?.findings_total || 0,
      active: details?.findings_active || 0,
    };
  };

  // =============================================================================
  // RENDER
  // =============================================================================

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.centered}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', color: '#3b82f6' }} />
          <p style={{ marginTop: '1rem', color: '#6b7280' }}>Loading playbook...</p>
        </div>
        <style>{spinKeyframes}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.centered}>
          <AlertTriangle size={32} color="#dc2626" />
          <p style={{ marginTop: '1rem', color: '#dc2626' }}>{error}</p>
          <button onClick={() => window.location.reload()} style={styles.button}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!definition) {
    return (
      <div style={styles.container}>
        <div style={styles.centered}>
          <p style={{ color: '#6b7280' }}>Playbook not found</p>
        </div>
      </div>
    );
  }

  const selectedStepDef = definition.steps?.find(s => s.id === selectedStep);
  const selectedStepData = stepDetails[selectedStep];

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>{definition.name}</h1>
          <p style={styles.subtitle}>
            {definition.total_steps} steps • {definition.type} playbook
          </p>
        </div>
        <div style={styles.headerActions}>
          <button
            onClick={executeAllSteps}
            disabled={executingAll}
            style={{ ...styles.button, ...styles.primaryButton }}
          >
            {executingAll ? (
              <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Running...</>
            ) : (
              <><Play size={16} /> Run All Steps</>
            )}
          </button>
          {onClose && (
            <button onClick={onClose} style={styles.button}>Close</button>
          )}
        </div>
      </div>

      {/* Progress Summary */}
      {progress && (
        <div style={styles.progressBar}>
          <div style={styles.progressStats}>
            <span><CheckCircle size={14} color="#059669" /> {progress.completed_steps || 0} complete</span>
            <span><AlertTriangle size={14} color="#d97706" /> {progress.active_findings || 0} findings</span>
            <span>{Math.round(progress.completion_pct || 0)}% done</span>
          </div>
          <div style={styles.progressTrack}>
            <div style={{ ...styles.progressFill, width: `${progress.completion_pct || 0}%` }} />
          </div>
        </div>
      )}

      {/* Main 2-panel layout */}
      <div style={styles.main}>
        {/* Step List */}
        <div style={styles.stepList}>
          <div style={styles.panelHeader}>Steps</div>
          {definition.steps?.map((step) => {
            const status = getStepStatus(step.id);
            const config = STATUS_CONFIG[status] || STATUS_CONFIG.not_started;
            const findings = getStepFindings(step.id);
            const isSelected = selectedStep === step.id;
            const Icon = config.icon;

            return (
              <div
                key={step.id}
                onClick={() => setSelectedStep(step.id)}
                style={{
                  ...styles.stepItem,
                  background: isSelected ? '#eff6ff' : 'white',
                  borderLeftColor: isSelected ? '#3b82f6' : 'transparent',
                }}
              >
                <div style={styles.stepItemRow}>
                  <Icon size={16} color={config.color} />
                  <span style={styles.stepId}>{step.id}</span>
                  {findings.active > 0 && (
                    <span style={styles.badge}>{findings.active}</span>
                  )}
                </div>
                <div style={styles.stepDesc}>
                  {step.description?.slice(0, 80) || step.name}
                  {(step.description?.length || 0) > 80 && '...'}
                </div>
              </div>
            );
          })}
        </div>

        {/* Step Detail */}
        <div style={styles.detail}>
          {selectedStepDef ? (
            <>
              {/* Detail Header */}
              <div style={styles.detailHeader}>
                <span style={styles.detailTitle}>Step {selectedStepDef.id}</span>
                <button
                  onClick={() => executeStep(selectedStepDef.id)}
                  disabled={executing === selectedStepDef.id}
                  style={{ ...styles.smallButton, ...styles.primaryButton }}
                >
                  {executing === selectedStepDef.id ? (
                    <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                  ) : (
                    <Play size={14} />
                  )}
                  Analyze
                </button>
              </div>

              {/* Description */}
              <div style={styles.section}>
                <div style={styles.sectionLabel}>Description</div>
                <p style={styles.descText}>{selectedStepDef.description || 'No description'}</p>
              </div>

              {/* Status Selector */}
              <div style={styles.section}>
                <div style={styles.sectionLabel}>Status</div>
                <div style={styles.statusRow}>
                  {Object.entries(STATUS_CONFIG).map(([key, cfg]) => {
                    const current = getStepStatus(selectedStepDef.id);
                    const active = current === key;
                    return (
                      <button
                        key={key}
                        onClick={() => updateStepStatus(selectedStepDef.id, key)}
                        style={{
                          ...styles.statusBtn,
                          background: active ? cfg.bg : '#f9fafb',
                          borderColor: active ? cfg.color : '#e5e7eb',
                          color: active ? cfg.color : '#6b7280',
                        }}
                      >
                        {cfg.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Required Data */}
              {selectedStepDef.required_data?.length > 0 && (
                <div style={styles.section}>
                  <div style={styles.sectionLabel}>Required Data</div>
                  {selectedStepDef.required_data.map((req, i) => (
                    <div key={i} style={styles.reqItem}>
                      <FileText size={14} /> {req}
                    </div>
                  ))}
                </div>
              )}

              {/* Findings */}
              <div style={styles.section}>
                <div style={styles.sectionLabel}>
                  Findings
                  {selectedStepData?.findings_total > 0 && (
                    <span style={styles.findingMeta}>
                      {selectedStepData.findings_active} active / {selectedStepData.findings_total} total
                    </span>
                  )}
                </div>
                
                {!selectedStepData?.findings_total ? (
                  <p style={styles.noFindings}>
                    No findings. Click "Analyze" to check for issues.
                  </p>
                ) : (
                  <div>
                    {/* Placeholder - findings would come from step details */}
                    <p style={styles.noFindings}>
                      {selectedStepData.findings_active} active findings.
                      (Finding details rendering TBD)
                    </p>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div style={styles.centered}>
              <p style={{ color: '#6b7280' }}>Select a step to view details</p>
            </div>
          )}
        </div>
      </div>

      <style>{spinKeyframes}</style>
    </div>
  );
}

// =============================================================================
// STYLES
// =============================================================================

const spinKeyframes = `
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#f9fafb',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  centered: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '1rem 1.5rem',
    background: 'white',
    borderBottom: '1px solid #e5e7eb',
  },
  title: {
    margin: 0,
    fontSize: '1.5rem',
    fontWeight: 600,
    color: '#111827',
  },
  subtitle: {
    margin: '0.25rem 0 0',
    fontSize: '0.875rem',
    color: '#6b7280',
  },
  headerActions: {
    display: 'flex',
    gap: '0.5rem',
  },
  button: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.5rem 1rem',
    fontSize: '0.875rem',
    fontWeight: 500,
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    background: 'white',
    color: '#374151',
    cursor: 'pointer',
  },
  primaryButton: {
    background: '#3b82f6',
    borderColor: '#3b82f6',
    color: 'white',
  },
  smallButton: {
    padding: '0.375rem 0.75rem',
    fontSize: '0.8rem',
  },
  progressBar: {
    padding: '0.75rem 1.5rem',
    background: 'white',
    borderBottom: '1px solid #e5e7eb',
  },
  progressStats: {
    display: 'flex',
    gap: '1.5rem',
    fontSize: '0.8rem',
    marginBottom: '0.5rem',
    color: '#374151',
  },
  progressTrack: {
    height: '6px',
    background: '#e5e7eb',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    background: '#3b82f6',
    transition: 'width 0.3s ease',
  },
  main: {
    display: 'grid',
    gridTemplateColumns: '320px 1fr',
    flex: 1,
    overflow: 'hidden',
  },
  stepList: {
    background: 'white',
    borderRight: '1px solid #e5e7eb',
    overflowY: 'auto',
  },
  panelHeader: {
    padding: '0.75rem 1rem',
    fontSize: '0.875rem',
    fontWeight: 600,
    color: '#374151',
    background: '#f9fafb',
    borderBottom: '1px solid #e5e7eb',
    position: 'sticky',
    top: 0,
  },
  stepItem: {
    padding: '0.75rem 1rem',
    borderBottom: '1px solid #f3f4f6',
    borderLeft: '3px solid transparent',
    cursor: 'pointer',
    transition: 'background 0.1s',
  },
  stepItemRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '0.25rem',
  },
  stepId: {
    fontWeight: 600,
    fontSize: '0.875rem',
    color: '#111827',
  },
  badge: {
    marginLeft: 'auto',
    padding: '0.125rem 0.5rem',
    fontSize: '0.7rem',
    fontWeight: 600,
    background: '#fee2e2',
    color: '#dc2626',
    borderRadius: '10px',
  },
  stepDesc: {
    fontSize: '0.8rem',
    color: '#6b7280',
    lineHeight: 1.4,
  },
  detail: {
    padding: '1.5rem',
    overflowY: 'auto',
  },
  detailHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1.5rem',
    paddingBottom: '1rem',
    borderBottom: '1px solid #e5e7eb',
  },
  detailTitle: {
    fontSize: '1.25rem',
    fontWeight: 600,
    color: '#111827',
  },
  section: {
    marginBottom: '1.5rem',
  },
  sectionLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.75rem',
    fontWeight: 600,
    color: '#6b7280',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '0.5rem',
  },
  descText: {
    margin: 0,
    fontSize: '0.9rem',
    lineHeight: 1.6,
    color: '#374151',
  },
  statusRow: {
    display: 'flex',
    gap: '0.5rem',
    flexWrap: 'wrap',
  },
  statusBtn: {
    padding: '0.375rem 0.75rem',
    fontSize: '0.8rem',
    fontWeight: 500,
    border: '1px solid',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  reqItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.5rem 0.75rem',
    fontSize: '0.85rem',
    color: '#374151',
    background: '#f9fafb',
    borderRadius: '4px',
    marginBottom: '0.25rem',
  },
  noFindings: {
    margin: 0,
    padding: '1rem',
    fontSize: '0.875rem',
    color: '#6b7280',
    background: '#f9fafb',
    borderRadius: '6px',
    textAlign: 'center',
  },
  findingMeta: {
    marginLeft: 'auto',
    fontSize: '0.7rem',
    fontWeight: 400,
    color: '#9ca3af',
    textTransform: 'none',
    letterSpacing: 'normal',
  },
};
