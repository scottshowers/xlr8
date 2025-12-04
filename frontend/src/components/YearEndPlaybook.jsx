/**
 * YearEndPlaybook - Interactive Year-End Checklist
 * 
 * Guided journey through Year-End actions:
 * - Shows all steps/actions from parsed UKG doc
 * - Auto-scans for relevant documents per action
 * - Tracks status (not started, in progress, complete, n/a)
 * - Consultant can add notes, override status
 * - Export current state anytime
 * 
 * UPDATED: Non-blocking scan-all with live progress (no more 20-min freezes!)
 */

import React, { useState, useEffect, useRef, useCallback, Component } from 'react';
import api from '../services/api';

// Error Boundary to catch rendering errors and show them instead of blank screen
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo });
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ 
          padding: '2rem', 
          background: '#fef2f2', 
          border: '1px solid #fecaca',
          borderRadius: '8px',
          margin: '1rem'
        }}>
          <h3 style={{ color: '#dc2626', marginBottom: '1rem' }}>⚠️ Something went wrong</h3>
          <p style={{ color: '#991b1b', marginBottom: '0.5rem' }}>
            {this.state.error?.message || 'Unknown error'}
          </p>
          <details style={{ marginTop: '1rem', fontSize: '0.8rem', color: '#6b7280' }}>
            <summary style={{ cursor: 'pointer' }}>Technical details</summary>
            <pre style={{ 
              overflow: 'auto', 
              padding: '0.5rem', 
              background: '#f9fafb',
              borderRadius: '4px',
              marginTop: '0.5rem'
            }}>
              {this.state.errorInfo?.componentStack}
            </pre>
          </details>
          <button 
            onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

// Brand Colors
const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  clearwater: '#b2d6de',
  turkishSea: '#285390',
  electricBlue: '#2766b1',
  iceFlow: '#c9d3d4',
  white: '#f6f5fa',
  silver: '#a2a1a0',
  scarletSage: '#993c44',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

const STATUS_OPTIONS = [
  { value: 'not_started', label: 'Not Started', color: '#9ca3af', bg: '#f3f4f6' },
  { value: 'in_progress', label: 'In Progress', color: '#d97706', bg: '#fef3c7' },
  { value: 'complete', label: 'Complete', color: '#059669', bg: '#d1fae5' },
  { value: 'na', label: 'N/A', color: '#6b7280', bg: '#e5e7eb' },
  { value: 'blocked', label: 'Blocked', color: '#dc2626', bg: '#fee2e2' },
];

// Tooltip type configuration
const TOOLTIP_TYPES = {
  best_practice: { icon: '⭐', label: 'Best Practice', color: '#eab308', bg: '#fef9c3' },
  mandatory: { icon: '🚨', label: 'Mandatory', color: '#dc2626', bg: '#fee2e2' },
  hint: { icon: '💡', label: 'Helpful Hint', color: '#3b82f6', bg: '#dbeafe' },
};

// Action dependencies - which actions inherit from which
const ACTION_DEPENDENCIES = {
  "2B": ["2A"], "2C": ["2A"], "2E": ["2A"],
  "2H": ["2F", "2G"], "2J": ["2G"], "2K": ["2G"], "2L": ["2G", "2J"],
  "3B": ["3A"], "3C": ["3A"], "3D": ["3A"],
  "5B": ["5A"], "5E": ["5C", "5D"],
  "6B": ["6A"], "6C": ["6A"],
};

// Get parent actions for an action
const getParentActions = (actionId) => ACTION_DEPENDENCIES[actionId] || [];

// =============================================================================
// SCAN PROGRESS COMPONENT (Non-blocking with live updates)
// =============================================================================
const SCAN_STATUS_CONFIG = {
  pending: { color: '#6b7280', bg: '#f3f4f6', icon: '⏳', label: 'Waiting...' },
  running: { color: '#3b82f6', bg: '#dbeafe', icon: '🔄', label: 'Scanning...' },
  completed: { color: '#10b981', bg: '#d1fae5', icon: '✅', label: 'Complete' },
  failed: { color: '#ef4444', bg: '#fee2e2', icon: '❌', label: 'Failed' },
  timeout: { color: '#f59e0b', bg: '#fef3c7', icon: '⏰', label: 'Timed Out' },
  cancelled: { color: '#6b7280', bg: '#f3f4f6', icon: '🚫', label: 'Cancelled' },
};

function ScanAllProgress({ projectId, onComplete, onError, buttonText = "🔍 Analyze All", disabled = false }) {
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [isStarting, setIsStarting] = useState(false);
  const pollIntervalRef = useRef(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Start the scan
  const startScan = async () => {
    if (!projectId) {
      onError?.('No project selected');
      return;
    }

    // Confirm before starting
    if (!window.confirm('Analyze all documents for this playbook? This runs in the background - you can continue working.')) {
      return;
    }

    setIsStarting(true);
    setStatus(null);

    try {
      const response = await api.post(`/playbooks/year-end/scan-all/${projectId}`);
      const data = response.data;
      
      if (!data.job_id) {
        // No actions to scan or immediate response
        setStatus({
          status: 'completed',
          message: data.message || 'No actions to scan',
          progress_percent: 100,
        });
        onComplete?.([]);
        setIsStarting(false);
        return;
      }

      setJobId(data.job_id);

      // Start polling
      startPolling(data.job_id);

    } catch (error) {
      console.error('[SCAN] Start error:', error);
      onError?.(error.message);
      setStatus({
        status: 'failed',
        message: error.message || 'Failed to start scan',
        progress_percent: 0,
      });
    } finally {
      setIsStarting(false);
    }
  };

  // Poll for status
  const startPolling = useCallback((jid) => {
    // Clear any existing interval
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    const poll = async () => {
      try {
        const response = await api.get(`/playbooks/year-end/scan-all/status/${jid}`);
        const data = response.data;
        setStatus(data);

        // Check if done
        if (['completed', 'failed', 'timeout', 'cancelled'].includes(data.status)) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;

          if (data.status === 'completed') {
            onComplete?.(data.results || []);
          } else if (data.status === 'failed') {
            onError?.(data.message);
          }
        }
      } catch (error) {
        console.error('[SCAN] Poll error:', error);
        // Don't stop polling on transient errors
      }
    };

    // Poll immediately, then every 1.5 seconds
    poll();
    pollIntervalRef.current = setInterval(poll, 1500);
  }, [onComplete, onError]);

  // Cancel the scan
  const cancelScan = async () => {
    if (!jobId) return;

    try {
      await api.post(`/playbooks/year-end/scan-all/cancel/${jobId}`);
    } catch (error) {
      console.error('[SCAN] Cancel error:', error);
    }
  };

  // Reset to start a new scan
  const reset = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setJobId(null);
    setStatus(null);
  };

  // Render
  const isRunning = status?.status === 'running';
  const isDone = ['completed', 'failed', 'timeout', 'cancelled'].includes(status?.status);
  const config = SCAN_STATUS_CONFIG[status?.status] || SCAN_STATUS_CONFIG.pending;

  // Show button when no active job
  if (!jobId && !status) {
    return (
      <button 
        onClick={startScan}
        disabled={isStarting || !projectId || disabled}
        style={{
          padding: '0.5rem 1rem',
          background: (isStarting || !projectId || disabled) ? '#9ca3af' : '#3b82f6',
          border: 'none',
          borderRadius: '8px',
          color: 'white',
          fontWeight: '600',
          cursor: (isStarting || !projectId || disabled) ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
        title="Analyze all uploaded documents for the entire playbook"
      >
        {isStarting ? '⏳ Starting...' : buttonText}
      </button>
    );
  }

  // Show progress when running or done
  return (
    <div style={{ 
      padding: '0.75rem', 
      borderRadius: '8px', 
      backgroundColor: config.bg, 
      border: `2px solid ${config.color}`,
      minWidth: '280px'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '1.1rem' }}>{config.icon}</span>
        <span style={{ fontWeight: 600, color: config.color, fontSize: '0.9rem' }}>{config.label}</span>
        {isRunning && (
          <button 
            onClick={cancelScan} 
            style={{
              marginLeft: 'auto',
              padding: '0.2rem 0.5rem',
              backgroundColor: '#fee2e2',
              color: '#ef4444',
              border: '1px solid #ef4444',
              borderRadius: '4px',
              fontSize: '0.75rem',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
        )}
      </div>

      {/* Progress Bar */}
      <div style={{ height: '6px', backgroundColor: '#e5e7eb', borderRadius: '3px', overflow: 'hidden', marginBottom: '0.5rem' }}>
        <div 
          style={{
            height: '100%',
            width: `${status?.progress_percent || 0}%`,
            backgroundColor: config.color,
            transition: 'width 0.3s ease',
            borderRadius: '3px',
          }}
        />
      </div>

      {/* Status Text */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#374151', marginBottom: '0.25rem' }}>
        <span>{status?.message}</span>
        <span style={{ fontWeight: 600 }}>{status?.progress_percent || 0}%</span>
      </div>

      {/* Current Action */}
      {isRunning && status?.current_action && (
        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>
          Currently: <strong>{status.current_action}</strong>
        </div>
      )}

      {/* Stats */}
      {status?.total_actions > 0 && (
        <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem', color: '#6b7280', flexWrap: 'wrap' }}>
          <span>📋 {status.completed_actions || 0}/{status.total_actions}</span>
          {status.successful > 0 && <span style={{ color: '#10b981' }}>✓ {status.successful} found</span>}
          {status.failed > 0 && <span style={{ color: '#ef4444' }}>✗ {status.failed} errors</span>}
        </div>
      )}

      {/* Done Actions */}
      {isDone && (
        <div style={{ marginTop: '0.5rem', display: 'flex', justifyContent: 'center' }}>
          <button 
            onClick={reset} 
            style={{
              padding: '0.35rem 0.75rem',
              backgroundColor: 'white',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              fontSize: '0.8rem',
              cursor: 'pointer',
            }}
          >
            🔄 Scan Again
          </button>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// AI SUMMARY DASHBOARD COMPONENT
// =============================================================================
function AISummaryDashboard({ summary, expanded, onToggle }) {
  if (!summary) return null;
  
  const { overall_risk, summary_text, stats, issues, recommendations, conflicts, review_flags, high_risk_actions } = summary;
  
  const riskColors = {
    high: { text: '#dc2626' },
    medium: { text: '#d97706' },
    low: { text: '#059669' }
  };
  
  const riskTextColor = riskColors[overall_risk]?.text || '#059669';
  
  return (
    <div style={{
      background: '#e8ede8',
      border: '1px solid #c5d1c5',
      borderRadius: '12px',
      marginBottom: '1rem',
      overflow: 'hidden'
    }}>
      <div 
        onClick={onToggle}
        style={{
          padding: '1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.5rem' }}>
            {overall_risk === 'high' ? '🔴' : overall_risk === 'medium' ? '🟡' : '🟢'}
          </span>
          <div>
            <div style={{ fontWeight: '600', color: COLORS.text }}>
              Analysis Summary (AI Assisted)
            </div>
            <div style={{ fontSize: '0.85rem', color: COLORS.textLight }}>
              {summary_text || 'No issues detected'}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ fontSize: '1.2rem' }}>{expanded ? '▼' : '▶'}</span>
        </div>
      </div>
      
      {expanded && (
        <div style={{ padding: '0 1rem 1rem', borderTop: '1px solid #e1e8ed' }}>
          {/* High Risk Actions */}
          {Array.isArray(high_risk_actions) && high_risk_actions.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ fontWeight: '600', color: '#dc2626', marginBottom: '0.5rem' }}>
                🚨 High Risk Actions:
              </div>
              {high_risk_actions.map((action, i) => (
                <div key={i} style={{ 
                  background: 'white', 
                  padding: '0.5rem', 
                  borderRadius: '6px', 
                  marginBottom: '0.25rem',
                  fontSize: '0.85rem'
                }}>
                  <strong>{action.action_id}:</strong> {action.summary}
                </div>
              ))}
            </div>
          )}
          
          {/* Conflicts */}
          {Array.isArray(conflicts) && conflicts.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ fontWeight: '600', color: '#dc2626', marginBottom: '0.5rem' }}>
                ❗ Data Conflicts:
              </div>
              {conflicts.map((conflict, i) => (
                <div key={i} style={{ 
                  background: 'white', 
                  padding: '0.5rem', 
                  borderRadius: '6px', 
                  marginBottom: '0.25rem',
                  fontSize: '0.85rem'
                }}>
                  {conflict.message}
                </div>
              ))}
            </div>
          )}
          
          {/* Review Flags */}
          {Array.isArray(review_flags) && review_flags.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ fontWeight: '600', color: '#d97706', marginBottom: '0.5rem' }}>
                🔄 Actions Needing Review:
              </div>
              {review_flags.map((flag, i) => (
                <div key={i} style={{ 
                  background: 'white', 
                  padding: '0.5rem', 
                  borderRadius: '6px', 
                  marginBottom: '0.25rem',
                  fontSize: '0.85rem'
                }}>
                  <strong>{flag.action_id}:</strong> {flag.flag?.reason}
                </div>
              ))}
            </div>
          )}
          
          {/* Top Issues */}
          {Array.isArray(issues) && issues.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ fontWeight: '600', color: COLORS.text, marginBottom: '0.5rem' }}>
                ⚠️ Issues ({issues.length}):
              </div>
              <div style={{ maxHeight: '150px', overflow: 'auto' }}>
                {issues.slice(0, 10).map((issue, i) => (
                  <div key={i} style={{ 
                    background: 'white', 
                    padding: '0.5rem', 
                    borderRadius: '6px', 
                    marginBottom: '0.25rem',
                    fontSize: '0.8rem',
                    display: 'flex',
                    gap: '0.5rem'
                  }}>
                    <span style={{ 
                      background: issue.risk_level === 'high' ? '#fee2e2' : '#fef3c7',
                      padding: '0.1rem 0.4rem',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: '600'
                    }}>
                      {issue.action_id}
                    </span>
                    <span>{issue.issue}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Top Recommendations */}
          {Array.isArray(recommendations) && recommendations.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ fontWeight: '600', color: '#059669', marginBottom: '0.5rem' }}>
                ✅ Recommendations ({recommendations.length}):
              </div>
              <div style={{ maxHeight: '120px', overflow: 'auto' }}>
                {recommendations.slice(0, 8).map((rec, i) => (
                  <div key={i} style={{ 
                    background: 'white', 
                    padding: '0.5rem', 
                    borderRadius: '6px', 
                    marginBottom: '0.25rem',
                    fontSize: '0.8rem'
                  }}>
                    <span style={{ 
                      background: '#d1fae5',
                      padding: '0.1rem 0.4rem',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: '600',
                      marginRight: '0.5rem'
                    }}>
                      {rec.action_id}
                    </span>
                    {rec.recommendation}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// DOCUMENT CHECKLIST SIDEBAR COMPONENT
// =============================================================================
function DocumentChecklistSidebar({ checklist, collapsed, onToggle, onKeywordUpdate }) {
  const [editingDoc, setEditingDoc] = useState(null); // {step, keyword}
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);
  
  if (!checklist) return null;
  
  const { 
    has_step_documents = false, 
    uploaded_files = [], 
    step_checklists = [],
    stats = {} 
  } = checklist;
  
  // Truncate filename for display
  const truncateFilename = (filename, maxLen = 24) => {
    if (!filename || filename.length <= maxLen) return filename;
    const ext = filename.split('.').pop();
    const name = filename.slice(0, -(ext.length + 1));
    const truncated = name.slice(0, maxLen - ext.length - 4) + '...';
    return `${truncated}.${ext}`;
  };
  
  const handleEditClick = (step, keyword) => {
    setEditingDoc({ step, keyword });
    setEditValue(keyword);
  };
  
  const handleSaveKeyword = async () => {
    if (!editingDoc || !editValue.trim()) return;
    
    setSaving(true);
    try {
      const res = await api.put('/playbooks/year-end/step-documents/keyword', {
        step: String(editingDoc.step),
        old_keyword: editingDoc.keyword,
        new_keyword: editValue.trim()
      });
      
      if (res.data.success) {
        setEditingDoc(null);
        setEditValue('');
        if (onKeywordUpdate) onKeywordUpdate();
      } else {
        alert('Failed to update keyword');
      }
    } catch (err) {
      console.error('Update failed:', err);
      alert('Failed to update: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };
  
  const handleCancelEdit = () => {
    setEditingDoc(null);
    setEditValue('');
  };
  
  const styles = {
    sidebar: {
      position: 'fixed',
      right: 0,
      top: 0,
      bottom: 0,
      width: collapsed ? '40px' : '320px',
      background: 'white',
      borderLeft: '1px solid #e1e8ed',
      transition: 'width 0.3s ease',
      zIndex: 100,
      display: 'flex',
      flexDirection: 'column',
    },
    toggleBtn: {
      position: 'absolute',
      left: '-16px',
      top: '50%',
      transform: 'translateY(-50%)',
      width: '32px',
      height: '32px',
      background: 'white',
      border: '1px solid #e1e8ed',
      borderRadius: '50%',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: '-2px 0 4px rgba(0,0,0,0.1)',
    },
    header: {
      padding: '1rem',
      borderBottom: '1px solid #e1e8ed',
      background: '#f8fafc',
    },
    content: {
      flex: 1,
      overflow: 'auto',
      padding: collapsed ? '0' : '0.75rem',
    },
    stepSection: {
      marginBottom: '1rem',
      background: '#f8fafc',
      borderRadius: '8px',
      padding: '0.75rem',
      border: '1px solid #e1e8ed',
    },
    stepHeader: {
      fontSize: '0.8rem',
      fontWeight: '600',
      color: COLORS.text,
      marginBottom: '0.5rem',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    docItem: (isMatched) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.4rem',
      padding: '0.35rem 0.5rem',
      fontSize: '0.75rem',
      background: isMatched ? '#f0fdf4' : '#fef2f2',
      borderRadius: '4px',
      marginBottom: '0.25rem',
      border: `1px solid ${isMatched ? '#bbf7d0' : '#fecaca'}`,
    }),
    editableKeyword: {
      flex: 1,
      cursor: 'pointer',
      borderBottom: '1px dashed transparent',
    },
    editableKeywordHover: {
      borderBottom: '1px dashed #9ca3af',
    },
    editInput: {
      flex: 1,
      padding: '0.2rem 0.3rem',
      fontSize: '0.75rem',
      border: '1px solid #3b82f6',
      borderRadius: '3px',
      outline: 'none',
    },
    editBtn: {
      padding: '0.15rem 0.3rem',
      fontSize: '0.65rem',
      border: 'none',
      borderRadius: '3px',
      cursor: 'pointer',
    },
    badge: (color, bg) => ({
      fontSize: '0.65rem',
      padding: '0.1rem 0.3rem',
      borderRadius: '3px',
      background: bg,
      color: color,
      fontWeight: '500',
    }),
    emptyState: {
      textAlign: 'center',
      padding: '2rem 1rem',
      color: COLORS.textLight,
      fontSize: '0.85rem',
    }
  };
  
  // Render a document item (editable)
  const renderDocItem = (doc, isMatched, stepNumber) => {
    const isEditing = editingDoc?.step === stepNumber && editingDoc?.keyword === doc.keyword;
    
    return (
      <div 
        key={`${stepNumber}-${doc.keyword}`} 
        style={styles.docItem(isMatched)} 
        title={isMatched ? doc.matched_file : doc.description}
      >
        <span>{isMatched ? '✅' : '❌'}</span>
        
        {isEditing ? (
          <>
            <input
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              style={styles.editInput}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveKeyword();
                if (e.key === 'Escape') handleCancelEdit();
              }}
            />
            <button 
              onClick={handleSaveKeyword} 
              disabled={saving}
              style={{ ...styles.editBtn, background: '#10b981', color: 'white' }}
            >
              {saving ? '...' : '✓'}
            </button>
            <button 
              onClick={handleCancelEdit}
              style={{ ...styles.editBtn, background: '#e5e7eb', color: '#374151' }}
            >
              ✗
            </button>
          </>
        ) : (
          <>
            <span 
              style={styles.editableKeyword}
              onClick={() => handleEditClick(stepNumber, doc.keyword)}
              title="Click to edit keyword"
              onMouseOver={(e) => e.target.style.borderBottom = '1px dashed #9ca3af'}
              onMouseOut={(e) => e.target.style.borderBottom = '1px dashed transparent'}
            >
              {doc.keyword}
            </span>
            {doc.required && (
              <span style={styles.badge(isMatched ? '#059669' : '#dc2626', isMatched ? '#d1fae5' : '#fee2e2')}>
                REQ
              </span>
            )}
          </>
        )}
      </div>
    );
  };
  
  if (collapsed) {
    return (
      <div style={styles.sidebar}>
        <button style={styles.toggleBtn} onClick={onToggle}>◀</button>
        <div style={{ 
          writingMode: 'vertical-rl', 
          textOrientation: 'mixed',
          padding: '1rem 0.5rem',
          fontSize: '0.85rem',
          color: COLORS.textLight,
          fontWeight: '600'
        }}>
          📋 Docs ({stats.total_matched || 0}/{stats.total_matched + stats.total_missing || 0})
        </div>
      </div>
    );
  }
  
  // If no Step_Documents sheet, show simple file list
  if (!has_step_documents) {
    return (
      <div style={styles.sidebar}>
        <button style={styles.toggleBtn} onClick={onToggle}>▶</button>
        <div style={styles.header}>
          <div style={{ fontWeight: '600', color: COLORS.text }}>📁 Project Files</div>
          <div style={{ fontSize: '0.8rem', color: COLORS.textLight, marginTop: '0.25rem' }}>
            {uploaded_files.length} file{uploaded_files.length !== 1 ? 's' : ''} uploaded
          </div>
        </div>
        <div style={styles.content}>
          {uploaded_files.length > 0 ? (
            uploaded_files.map((file, i) => (
              <div key={i} style={styles.docItem(true)} title={file}>
                <span>📄</span>
                <span style={{ flex: 1 }}>{truncateFilename(file)}</span>
              </div>
            ))
          ) : (
            <div style={styles.emptyState}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📤</div>
              <div>No files uploaded yet</div>
            </div>
          )}
        </div>
      </div>
    );
  }
  
  // Step-based document checklist with editable keywords
  return (
    <div style={styles.sidebar}>
      <button style={styles.toggleBtn} onClick={onToggle}>▶</button>
      
      <div style={styles.header}>
        <div style={{ fontWeight: '600', color: COLORS.text }}>📋 Document Checklist</div>
        <div style={{ fontSize: '0.8rem', color: COLORS.textLight, marginTop: '0.25rem' }}>
          {stats.total_matched || 0} of {(stats.total_matched || 0) + (stats.total_missing || 0)} matched
        </div>
        {stats.required_missing > 0 && (
          <div style={{ fontSize: '0.75rem', color: '#dc2626', marginTop: '0.25rem' }}>
            ⚠️ {stats.required_missing} required missing
          </div>
        )}
        <div style={{ fontSize: '0.65rem', color: '#9ca3af', marginTop: '0.25rem', fontStyle: 'italic' }}>
          Click keyword to edit
        </div>
      </div>
      
      <div style={styles.content}>
        {step_checklists.map((step, i) => (
          <div key={i} style={styles.stepSection}>
            <div style={styles.stepHeader}>
              <span>Step {step.step_number}: {step.step_name?.slice(0, 20)}</span>
              <span style={styles.badge(
                step.stats.missing === 0 ? '#059669' : '#d97706',
                step.stats.missing === 0 ? '#d1fae5' : '#fef3c7'
              )}>
                {step.stats.matched}/{step.stats.total}
              </span>
            </div>
            
            {/* Matched docs */}
            {step.matched.map((doc) => renderDocItem(doc, true, step.step_number))}
            
            {/* Missing docs */}
            {step.missing.map((doc) => renderDocItem(doc, false, step.step_number))}
          </div>
        ))}
        
        {step_checklists.length === 0 && (
          <div style={styles.emptyState}>
            <div>No Step_Documents sheet found</div>
            <div style={{ fontSize: '0.75rem', marginTop: '0.5rem' }}>
              Add Step_Documents sheet to Year-End Excel
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


// =============================================================================
// TOOLTIP MODAL COMPONENT
// =============================================================================
function TooltipModal({ isOpen, onClose, onSave, actionId, existingTooltip }) {
  const [tooltipType, setTooltipType] = useState(existingTooltip?.tooltip_type || 'hint');
  const [title, setTitle] = useState(existingTooltip?.title || '');
  const [content, setContent] = useState(existingTooltip?.content || '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (existingTooltip) {
      setTooltipType(existingTooltip.tooltip_type || 'hint');
      setTitle(existingTooltip.title || '');
      setContent(existingTooltip.content || '');
    } else {
      setTooltipType('hint');
      setTitle('');
      setContent('');
    }
  }, [existingTooltip, isOpen]);

  if (!isOpen) return null;

  const handleSave = async () => {
    if (!content.trim()) {
      alert('Content is required');
      return;
    }
    setSaving(true);
    try {
      await onSave({
        playbook_id: 'year-end-2025',
        action_id: actionId,
        tooltip_type: tooltipType,
        title: title.trim() || null,
        content: content.trim(),
      });
      onClose();
    } catch (err) {
      alert('Failed to save note');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
    }}>
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '1.5rem',
        width: '90%',
        maxWidth: '500px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
      }}>
        <h3 style={{ margin: '0 0 1rem', color: COLORS.text }}>
          {existingTooltip ? 'Edit Note' : 'Add Note'} for {actionId}
        </h3>
        
        {/* Type Selection */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.85rem', fontWeight: '600', color: COLORS.textLight }}>Type</label>
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
            {Object.entries(TOOLTIP_TYPES).map(([key, config]) => (
              <button
                key={key}
                onClick={() => setTooltipType(key)}
                style={{
                  flex: 1,
                  padding: '0.5rem',
                  border: `2px solid ${tooltipType === key ? config.color : '#e1e8ed'}`,
                  borderRadius: '8px',
                  background: tooltipType === key ? config.bg : 'white',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                <span style={{ fontSize: '1.25rem' }}>{config.icon}</span>
                <span style={{ fontSize: '0.75rem', fontWeight: '600' }}>{config.label}</span>
              </button>
            ))}
          </div>
        </div>
        
        {/* Title */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.85rem', fontWeight: '600', color: COLORS.textLight }}>Title (optional)</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Brief title..."
            style={{
              width: '100%',
              padding: '0.5rem',
              border: '1px solid #e1e8ed',
              borderRadius: '6px',
              marginTop: '0.5rem',
              fontSize: '0.9rem',
            }}
          />
        </div>
        
        {/* Content */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.85rem', fontWeight: '600', color: COLORS.textLight }}>Content *</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Enter note content..."
            rows={4}
            style={{
              width: '100%',
              padding: '0.5rem',
              border: '1px solid #e1e8ed',
              borderRadius: '6px',
              marginTop: '0.5rem',
              fontSize: '0.9rem',
              resize: 'vertical',
              fontFamily: 'inherit',
            }}
          />
        </div>
        
        {/* Buttons */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem 1rem',
              border: '1px solid #e1e8ed',
              borderRadius: '6px',
              background: 'white',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              padding: '0.5rem 1rem',
              border: 'none',
              borderRadius: '6px',
              background: COLORS.grassGreen,
              color: 'white',
              fontWeight: '600',
              cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// TOOLTIP DISPLAY COMPONENT
// =============================================================================
function TooltipDisplay({ tooltips, onEdit, onDelete, isAdmin }) {
  const [activeTooltip, setActiveTooltip] = useState(null);
  
  if (!tooltips || tooltips.length === 0) return null;
  
  return (
    <>
      {/* Icons */}
      <div style={{ display: 'flex', gap: '0.3rem', marginLeft: '0.5rem' }}>
        {tooltips.map((tip, i) => {
          const config = TOOLTIP_TYPES[tip.tooltip_type] || TOOLTIP_TYPES.hint;
          const isActive = activeTooltip === i;
          return (
            <span
              key={tip.id || i}
              onClick={(e) => {
                e.stopPropagation();
                setActiveTooltip(isActive ? null : i);
              }}
              style={{
                cursor: 'pointer',
                fontSize: '1.1rem',
                transform: isActive ? 'scale(1.3)' : 'scale(1)',
                transition: 'transform 0.2s, filter 0.2s',
                filter: isActive ? `drop-shadow(0 0 4px ${config.color})` : 'none',
                animation: !isActive ? 'pulse 2s infinite' : 'none',
              }}
              title={config.label}
            >
              {config.icon}
            </span>
          );
        })}
      </div>

      {/* Popup */}
      {activeTooltip !== null && tooltips[activeTooltip] && (
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 1001,
            minWidth: '280px',
            maxWidth: '400px',
            padding: '1rem',
            borderRadius: '10px',
            boxShadow: '0 10px 40px rgba(0,0,0,0.25)',
            background: (() => {
              const tip = tooltips[activeTooltip];
              const config = TOOLTIP_TYPES[tip.tooltip_type] || TOOLTIP_TYPES.hint;
              return config.bg;
            })(),
            border: (() => {
              const tip = tooltips[activeTooltip];
              const config = TOOLTIP_TYPES[tip.tooltip_type] || TOOLTIP_TYPES.hint;
              return `2px solid ${config.color}`;
            })(),
          }}
        >
          {(() => {
            const tip = tooltips[activeTooltip];
            const config = TOOLTIP_TYPES[tip.tooltip_type] || TOOLTIP_TYPES.hint;
            return (
              <>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '0.5rem',
                  marginBottom: '0.75rem',
                  paddingBottom: '0.5rem',
                  borderBottom: `1px solid ${config.color}40`
                }}>
                  <span style={{ fontSize: '1.3rem' }}>{config.icon}</span>
                  <span style={{ 
                    color: config.color,
                    fontWeight: '700',
                    fontSize: '0.95rem'
                  }}>
                    {tip.title || config.label}
                  </span>
                </div>
                <div style={{ 
                  fontSize: '0.9rem', 
                  color: COLORS.text,
                  lineHeight: '1.5',
                  whiteSpace: 'pre-wrap'
                }}>
                  {tip.content}
                </div>
                
                {isAdmin && (
                  <div style={{ 
                    display: 'flex', 
                    gap: '0.5rem', 
                    marginTop: '1rem',
                    paddingTop: '0.75rem',
                    borderTop: '1px solid #e1e8ed'
                  }}>
                    <button
                      onClick={() => { onEdit(tip); setActiveTooltip(null); }}
                      style={{
                        fontSize: '0.8rem',
                        padding: '0.35rem 0.75rem',
                        border: '1px solid #e1e8ed',
                        borderRadius: '4px',
                        background: 'white',
                        cursor: 'pointer'
                      }}
                    >
                      ✏️ Edit
                    </button>
                    <button
                      onClick={() => { onDelete(tip.id); setActiveTooltip(null); }}
                      style={{
                        fontSize: '0.8rem',
                        padding: '0.35rem 0.75rem',
                        border: '1px solid #fee2e2',
                        borderRadius: '4px',
                        background: '#fee2e2',
                        color: '#dc2626',
                        cursor: 'pointer'
                      }}
                    >
                      🗑️ Delete
                    </button>
                  </div>
                )}

                {/* Close X */}
                <button
                  onClick={() => setActiveTooltip(null)}
                  style={{
                    position: 'absolute',
                    top: '0.5rem',
                    right: '0.75rem',
                    border: 'none',
                    background: 'none',
                    cursor: 'pointer',
                    fontSize: '1.2rem',
                    color: '#999',
                    padding: '0.25rem'
                  }}
                >
                  ×
                </button>
              </>
            );
          })()}
        </div>
      )}

      {/* CSS Animation for pulse */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </>
  );
}

// Action Card Component
function ActionCard({ action, stepNumber, progress, projectId, onUpdate, tooltips, isAdmin, onAddTooltip, onEditTooltip, onDeleteTooltip, uploadedFiles }) {
  const [expanded, setExpanded] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [notes, setNotes] = useState(progress?.notes || '');
  const [aiContext, setAiContext] = useState(progress?.ai_context || '');
  const [localStatus, setLocalStatus] = useState(progress?.status || 'not_started');
  const [localDocsFound, setLocalDocsFound] = useState(progress?.documents_found || []);
  const fileInputRef = React.useRef(null);
  
  // Pre-match uploaded files to this action's reports_needed (runs on every render)
  const reportsNeeded = Array.isArray(action?.reports_needed) 
    ? action.reports_needed 
    : (action?.reports_needed ? String(action.reports_needed).split(',').map(s => s.trim()) : []);
  
  // Match uploaded files against reports_needed using same fuzzy logic as sidebar
  const matchedFromUploads = React.useMemo(() => {
    if (!uploadedFiles?.length || !reportsNeeded.length) return [];
    
    const normalize = (s) => s.toLowerCase().replace(/_/g, ' ').replace(/-/g, ' ').replace(/\./g, ' ').replace(/'/g, '');
    
    const matched = [];
    for (const report of reportsNeeded) {
      const reportNorm = normalize(report);
      const reportWords = reportNorm.split(' ').filter(w => w.length > 2);
      
      for (const file of uploadedFiles) {
        const fileNorm = normalize(file);
        
        // Method 1: full keyword in filename
        if (fileNorm.includes(reportNorm)) {
          matched.push(file);
          break;
        }
        
        // Method 2: all words appear
        if (reportWords.every(w => fileNorm.includes(w))) {
          matched.push(file);
          break;
        }
        
        // Method 3: fuzzy word matching
        const fuzzyMatch = (keyword, text) => {
          if (text.includes(keyword)) return true;
          const textWords = text.split(' ');
          for (const tw of textWords) {
            if (tw.startsWith(keyword) || keyword.startsWith(tw)) return true;
            if (keyword.length >= 4 && tw.length >= 4 && keyword.slice(0,4) === tw.slice(0,4)) return true;
          }
          return false;
        };
        
        const fuzzyMatches = reportWords.filter(w => fuzzyMatch(w, fileNorm)).length;
        if (fuzzyMatches >= reportWords.length - 1 && fuzzyMatches > 0) {
          matched.push(file);
          break;
        }
      }
    }
    return matched;
  }, [uploadedFiles, reportsNeeded]);
  
  // Combine scan results + upload matches for display
  const allDocsFound = React.useMemo(() => {
    const combined = new Set([...localDocsFound, ...matchedFromUploads]);
    return Array.from(combined);
  }, [localDocsFound, matchedFromUploads]);
  
  // Sync local docs with progress prop - MUST be before any conditional returns
  React.useEffect(() => {
    setLocalDocsFound(progress?.documents_found || []);
  }, [progress?.documents_found]);
  
  // Safety check - if no action, don't render (AFTER all hooks)
  if (!action) {
    return null;
  }
  
  const findings = progress?.findings;
  const expectedCount = reportsNeeded.length || 1;
  
  const statusConfig = STATUS_OPTIONS.find(s => s.value === localStatus) || STATUS_OPTIONS[0];

  const handleScan = async (forceRefresh = true) => {
    setScanning(true);
    try {
      // Always force refresh for now - caching can be re-enabled once content retrieval is stable
      const res = await api.post(`/playbooks/year-end/scan/${projectId}/${action.action_id}?force_refresh=${forceRefresh}`);
      console.log('[SCAN] Response:', res.data);
      if (res.data) {
        if (res.data.cached) {
          console.log('[SCAN] ⚡ Using cached results');
        }
        const newDocs = res.data.documents?.map(d => d.filename) || [];
        console.log('[SCAN] Found docs:', newDocs);
        setLocalDocsFound(newDocs);
        setLocalStatus(res.data.suggested_status);
        onUpdate(action.action_id, {
          status: res.data.suggested_status,
          findings: res.data.findings,
          documents_found: newDocs
        });
      }
    } catch (err) {
      console.error('Scan failed:', err);
    } finally {
      setScanning(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    setUploading(true);
    setUploadStatus(null);
    
    try {
      const jobIds = [];
      
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('project', projectId);
        
        const res = await api.post('/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        if (res.data?.job_id) {
          jobIds.push(res.data.job_id);
        }
      }
      
      setUploading(false);
      setUploadStatus('processing');
      
      const pollJobs = async () => {
        let allComplete = false;
        let attempts = 0;
        const maxAttempts = 60;
        
        while (!allComplete && attempts < maxAttempts) {
          await new Promise(r => setTimeout(r, 2000));
          attempts++;
          
          try {
            const jobsRes = await api.get('/jobs');
            const jobs = jobsRes.data?.jobs || [];
            
            const ourJobs = jobs.filter(j => jobIds.includes(j.id));
            allComplete = ourJobs.length > 0 && ourJobs.every(j => 
              j.status === 'completed' || j.status === 'failed'
            );
            
            const failed = ourJobs.filter(j => j.status === 'failed');
            if (failed.length > 0) {
              setUploadStatus('error');
              setTimeout(() => setUploadStatus(null), 3000);
              return;
            }
          } catch (err) {
            console.error('Polling failed:', err);
          }
        }
        
        if (allComplete) {
          setUploadStatus('scanning');
          await handleScan();
          setUploadStatus('complete');
          setTimeout(() => setUploadStatus(null), 2000);
        }
      };
      
      pollJobs();
      
    } catch (err) {
      console.error('Upload failed:', err);
      setUploading(false);
      setUploadStatus('error');
      setTimeout(() => setUploadStatus(null), 3000);
    }
    
    // Reset input
    e.target.value = '';
  };

  const handleStatusChange = async (newStatus) => {
    setLocalStatus(newStatus);
    try {
      await api.put(`/playbooks/year-end/progress/${projectId}/${action.action_id}`, {
        status: newStatus
      });
      onUpdate(action.action_id, { status: newStatus });
    } catch (err) {
      console.error('Status update failed:', err);
    }
  };

  const handleNotesChange = async () => {
    try {
      await api.put(`/playbooks/year-end/progress/${projectId}/${action.action_id}`, {
        notes
      });
      onUpdate(action.action_id, { notes });
    } catch (err) {
      console.error('Notes update failed:', err);
    }
  };

  const handleAiContextChange = async () => {
    try {
      await api.put(`/playbooks/year-end/progress/${projectId}/${action.action_id}`, {
        ai_context: aiContext
      });
      onUpdate(action.action_id, { ai_context: aiContext });
    } catch (err) {
      console.error('AI Context update failed:', err);
    }
  };

  // Helper functions for upload button styling
  const getUploadButtonStyle = () => {
    const baseStyle = {
      padding: '0.5rem 1rem',
      border: 'none',
      borderRadius: '6px',
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      transition: 'background 0.2s, color 0.2s',
    };
    
    if (uploading || uploadStatus === 'processing' || uploadStatus === 'scanning') {
      return { ...baseStyle, background: '#fef3c7', color: '#92400e', cursor: 'not-allowed' };
    }
    if (uploadStatus === 'complete') {
      return { ...baseStyle, background: '#d1fae5', color: '#065f46' };
    }
    if (uploadStatus === 'error') {
      return { ...baseStyle, background: '#fee2e2', color: '#991b1b' };
    }
    return { ...baseStyle, background: COLORS.clearwater, color: COLORS.text };
  };

  const getUploadButtonContent = () => {
    if (uploading) return '⏳ Uploading...';
    if (uploadStatus === 'processing') return '⏳ Processing...';
    if (uploadStatus === 'scanning') return '🔍 Scanning...';
    if (uploadStatus === 'complete') return '✅ Complete!';
    if (uploadStatus === 'error') return '❌ Error';
    return '📤 Upload';
  };

  const styles = {
    card: {
      background: 'white',
      borderRadius: '10px',
      border: '1px solid #e1e8ed',
      marginBottom: '0.75rem',
      overflow: 'hidden',
    },
    header: {
      padding: '0.75rem 1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      cursor: 'pointer',
      borderLeft: `4px solid ${statusConfig.color}`,
    },
    actionId: {
      fontWeight: '700',
      fontSize: '0.9rem',
      color: COLORS.turkishSea,
      minWidth: '36px',
    },
    content: {
      flex: 1,
    },
    description: {
      fontWeight: '500',
      color: COLORS.text,
      fontSize: '0.9rem',
    },
    meta: {
      display: 'flex',
      gap: '0.75rem',
      marginTop: '0.25rem',
      flexWrap: 'wrap',
    },
    dueDate: {
      fontSize: '0.75rem',
      color: COLORS.textLight,
    },
    actionType: {
      fontSize: '0.7rem',
      padding: '0.15rem 0.4rem',
      background: '#e0f2fe',
      color: '#0369a1',
      borderRadius: '4px',
      textTransform: 'uppercase',
    },
    statusBadge: {
      fontSize: '0.75rem',
      padding: '0.3rem 0.6rem',
      background: statusConfig.bg,
      color: statusConfig.color,
      borderRadius: '4px',
      fontWeight: '600',
    },
    expandIcon: {
      fontSize: '0.9rem',
      color: COLORS.textLight,
    },
    expandedContent: {
      padding: '1rem',
      borderTop: '1px solid #e1e8ed',
      background: '#fafbfc',
    },
    section: {
      marginBottom: '0.75rem',
    },
    sectionTitle: {
      fontSize: '0.8rem',
      fontWeight: '600',
      color: COLORS.textLight,
      marginBottom: '0.4rem',
      textTransform: 'uppercase',
    },
    docsFound: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '0.5rem',
    },
    docBadge: {
      fontSize: '0.75rem',
      padding: '0.25rem 0.5rem',
      background: '#dbeafe',
      color: '#1e40af',
      borderRadius: '4px',
    },
    statusSelect: {
      display: 'flex',
      gap: '0.5rem',
      flexWrap: 'wrap',
    },
    statusBtn: (isActive, config) => ({
      padding: '0.4rem 0.75rem',
      fontSize: '0.8rem',
      fontWeight: '600',
      border: `2px solid ${isActive ? config.color : '#e1e8ed'}`,
      background: isActive ? config.bg : 'white',
      color: isActive ? config.color : COLORS.textLight,
      borderRadius: '6px',
      cursor: 'pointer',
    }),
    notesArea: {
      width: '100%',
      padding: '0.5rem',
      border: '1px solid #e1e8ed',
      borderRadius: '6px',
      fontSize: '0.85rem',
      minHeight: '60px',
      resize: 'vertical',
      fontFamily: 'inherit',
    },
    buttonRow: {
      display: 'flex',
      gap: '0.75rem',
      flexWrap: 'wrap',
    },
    scanBtn: {
      padding: '0.5rem 1rem',
      background: COLORS.grassGreen,
      color: 'white',
      border: 'none',
      borderRadius: '6px',
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    reportsNeeded: {
      fontSize: '0.8rem',
      color: COLORS.textLight,
      fontStyle: 'italic',
    },
    hiddenInput: {
      display: 'none',
    },
  };

  return (
    <div style={styles.card}>
      <div style={styles.header} onClick={() => setExpanded(!expanded)}>
        <span style={styles.actionId}>{action.action_id || '?'}</span>
        
        {/* Tooltip icons */}
        <TooltipDisplay 
          tooltips={tooltips} 
          onEdit={onEditTooltip}
          onDelete={onDeleteTooltip}
          isAdmin={isAdmin}
        />
        
        {/* Admin add button */}
        {isAdmin && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAddTooltip(action.action_id);
            }}
            style={{
              marginLeft: '0.3rem',
              padding: '0 0.4rem',
              border: '1px dashed #ccc',
              borderRadius: '4px',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: '0.9rem',
              color: '#999',
              lineHeight: '1.2'
            }}
            title="Add note"
          >
            +
          </button>
        )}
        
        <div style={styles.content}>
          <div style={styles.description}>{action.description || 'No description'}</div>
          <div style={styles.meta}>
            {action.due_date && (
              <span style={styles.dueDate}>📅 Due: {action.due_date}</span>
            )}
            <span style={styles.actionType}>{action.action_type || 'unknown'}</span>
            {allDocsFound.length > 0 && (
              <span style={{ fontSize: '0.75rem', color: COLORS.grassGreen }}>
                ✓ {allDocsFound.length} doc{allDocsFound.length > 1 ? 's' : ''} found
              </span>
            )}
          </div>
        </div>
        <span style={styles.statusBadge}>{statusConfig.label}</span>
        <span style={styles.expandIcon}>{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && (
        <div style={styles.expandedContent}>
          {reportsNeeded.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Reports Needed</div>
              <div style={styles.reportsNeeded}>
                {reportsNeeded.join(', ')}
              </div>
            </div>
          )}

          {/* Show dependency info if this action inherits from others */}
          {(() => {
            const parents = getParentActions(action.action_id);
            if (parents.length > 0 && reportsNeeded.length === 0) {
              return (
                <div style={{
                  background: '#eff6ff',
                  border: '1px solid #bfdbfe',
                  padding: '0.6rem 0.75rem',
                  borderRadius: '6px',
                  marginBottom: '0.75rem',
                  fontSize: '0.8rem',
                  color: '#1e40af',
                }}>
                  <span style={{ marginRight: '0.5rem' }}>💡</span>
                  <strong>No upload needed</strong> - This action uses data from action{parents.length > 1 ? 's' : ''} {parents.join(', ')}. 
                  Click "Scan Documents" to analyze.
                </div>
              );
            }
            return null;
          })()}

          <div style={styles.section}>
            <div style={styles.buttonRow}>
              <input
                type="file"
                ref={fileInputRef}
                style={styles.hiddenInput}
                onChange={handleFileChange}
                multiple
                accept=".pdf,.xlsx,.xls,.csv,.docx,.doc,.txt"
              />
              <button 
                style={getUploadButtonStyle()} 
                onClick={(e) => { e.stopPropagation(); handleUploadClick(); }}
                disabled={uploading || scanning || uploadStatus === 'processing' || uploadStatus === 'scanning'}
              >
                {getUploadButtonContent()}
              </button>
              <button 
                style={styles.scanBtn} 
                onClick={(e) => { e.stopPropagation(); handleScan(); }}
                disabled={scanning || uploading}
              >
                {scanning ? '⏳ Scanning...' : '🔍 Scan Documents'}
              </button>
            </div>
          </div>

          {/* Show matched and missing reports */}
          {action.reports_needed && (Array.isArray(action.reports_needed) ? action.reports_needed.length > 0 : String(action.reports_needed).trim().length > 0) && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Document Status</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                {(action.reports_needed 
                  ? (Array.isArray(action.reports_needed) 
                      ? action.reports_needed 
                      : String(action.reports_needed).split(','))
                  : []
                ).map((report, i) => {
                  const reportTrimmed = String(report).trim();
                  // Normalize: lowercase, replace separators
                  const normalize = (s) => s.toLowerCase().replace(/_/g, ' ').replace(/-/g, ' ').replace(/\./g, ' ');
                  const reportNorm = normalize(reportTrimmed);
                  const reportWords = reportNorm.split(' ').filter(w => w.length > 2); // Skip tiny words
                  
                  // Check if this report was found - with fuzzy matching
                  const matchDoc = (doc) => {
                    const docNorm = normalize(doc);
                    
                    // Method 1: full keyword in filename
                    if (docNorm.includes(reportNorm)) return true;
                    
                    // Method 2: all words appear (exact)
                    if (reportWords.every(w => docNorm.includes(w))) return true;
                    
                    // Method 3: fuzzy word matching (partial/prefix)
                    // "workers" matches "worker", "comp" matches "compensation"
                    const fuzzyMatch = (keyword, text) => {
                      if (text.includes(keyword)) return true;
                      // Check if keyword is prefix of any word in text
                      const textWords = text.split(' ');
                      for (const tw of textWords) {
                        if (tw.startsWith(keyword) || keyword.startsWith(tw)) return true;
                        // Also check if first 4 chars match (worker/workers, comp/compensation)
                        if (keyword.length >= 4 && tw.length >= 4 && keyword.slice(0,4) === tw.slice(0,4)) return true;
                      }
                      return false;
                    };
                    
                    // Check if most keyword words fuzzy-match
                    const fuzzyMatches = reportWords.filter(w => fuzzyMatch(w, docNorm)).length;
                    if (fuzzyMatches >= reportWords.length - 1 && fuzzyMatches > 0) return true;
                    
                    return false;
                  };
                  
                  const found = allDocsFound.some(matchDoc);
                  const matchedDoc = found ? allDocsFound.find(matchDoc) : null;
                  
                  return (
                    <div key={i} style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.35rem 0.5rem',
                      background: found ? '#f0fdf4' : '#fef2f2',
                      border: `1px solid ${found ? '#bbf7d0' : '#fecaca'}`,
                      borderRadius: '4px',
                      fontSize: '0.8rem'
                    }}>
                      <span>{found ? '✅' : '❌'}</span>
                      <span style={{ fontWeight: '500' }}>{reportTrimmed}</span>
                      {matchedDoc && (
                        <span style={{ color: '#6b7280', fontSize: '0.75rem', marginLeft: 'auto' }}>
                          → {matchedDoc.length > 30 ? matchedDoc.slice(0, 30) + '...' : matchedDoc}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Show inherited indicator if applicable */}
          {progress?.inherited_from && (Array.isArray(progress.inherited_from) ? progress.inherited_from.length > 0 : progress.inherited_from) && (
            <div style={{ 
              background: '#e0f2fe', 
              padding: '0.5rem 0.75rem', 
              borderRadius: '6px', 
              marginBottom: '0.75rem',
              fontSize: '0.8rem',
              color: '#0369a1',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <span>🔗</span>
              <span>Using data from action{Array.isArray(progress.inherited_from) && progress.inherited_from.length > 1 ? 's' : ''}: <strong>{Array.isArray(progress.inherited_from) ? progress.inherited_from.join(', ') : progress.inherited_from}</strong></span>
            </div>
          )}
          
          {/* Show review flag warning if action was impacted by new data */}
          {progress?.review_flag && (
            <div style={{ 
              background: '#fef3c7', 
              padding: '0.75rem', 
              borderRadius: '6px', 
              marginBottom: '0.75rem',
              fontSize: '0.85rem',
              color: '#92400e',
              border: '1px solid #fcd34d'
            }}>
              <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                🔄 Review Recommended
              </div>
              <div>{progress.review_flag.reason}</div>
              <div style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: '#b45309' }}>
                Triggered by update to action {progress.review_flag.triggered_by}
              </div>
            </div>
          )}
          
          {/* Show guidance for dependent actions */}
          {findings?.is_dependent && findings?.guidance && (
            <div style={{ 
              background: '#f0fdf4', 
              padding: '0.75rem', 
              borderRadius: '6px', 
              marginBottom: '0.75rem',
              fontSize: '0.85rem',
              color: '#166534',
              border: '1px solid #86efac'
            }}>
              <div style={{ fontWeight: '600', marginBottom: '0.5rem' }}>
                📋 Guidance for this action:
              </div>
              <div style={{ whiteSpace: 'pre-wrap' }}>{findings.guidance}</div>
            </div>
          )}

          {/* Show findings summary */}
          {findings?.summary && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Analysis Summary</div>
              <div style={{ 
                fontSize: '0.85rem', 
                color: COLORS.text, 
                background: '#f8fafc', 
                padding: '0.5rem', 
                borderRadius: '6px',
                whiteSpace: 'pre-wrap',
                lineHeight: '1.5'
              }}>
                {findings.summary}
              </div>
            </div>
          )}

          {/* Show issues/concerns */}
          {findings?.issues && Array.isArray(findings.issues) && findings.issues.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>⚠️ Issues Identified</div>
              <div style={{ 
                background: '#fef2f2', 
                border: '1px solid #fecaca',
                borderRadius: '6px',
                padding: '0.5rem'
              }}>
                {findings.issues.map((issue, i) => (
                  <div key={i} style={{
                    fontSize: '0.85rem',
                    color: '#991b1b',
                    padding: '0.35rem 0',
                    borderBottom: i < findings.issues.length - 1 ? '1px solid #fecaca' : 'none',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.5rem'
                  }}>
                    <span style={{ color: '#dc2626' }}>•</span>
                    <span>{issue}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Show action-specific guidance */}
          {findings?.guidance && Array.isArray(findings.guidance) && findings.guidance.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>📋 Guidance for This Action</div>
              <div style={{ 
                background: '#f0fdf4', 
                border: '1px solid #86efac',
                borderRadius: '6px',
                padding: '0.5rem'
              }}>
                {findings.guidance.map((step, i) => (
                  <div key={i} style={{
                    fontSize: '0.85rem',
                    color: '#166534',
                    padding: '0.35rem 0',
                    borderBottom: i < findings.guidance.length - 1 ? '1px solid #bbf7d0' : 'none',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.5rem'
                  }}>
                    <span style={{ 
                      background: '#16a34a', 
                      color: 'white', 
                      borderRadius: '50%', 
                      width: '18px', 
                      height: '18px', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      fontSize: '0.7rem',
                      flexShrink: 0
                    }}>{i + 1}</span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Show guidance as text if it's a string */}
          {findings?.guidance && typeof findings.guidance === 'string' && findings.guidance.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>📋 Guidance for This Action</div>
              <div style={{ 
                background: '#f0fdf4', 
                border: '1px solid #86efac',
                borderRadius: '6px',
                padding: '0.75rem',
                fontSize: '0.85rem',
                color: '#166534',
                whiteSpace: 'pre-wrap'
              }}>
                {findings.guidance}
              </div>
            </div>
          )}

          {/* Show recommendations */}
          {findings?.recommendations && Array.isArray(findings.recommendations) && findings.recommendations.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>💡 Recommendations</div>
              <div style={{ 
                background: '#eff6ff', 
                border: '1px solid #bfdbfe',
                borderRadius: '6px',
                padding: '0.5rem'
              }}>
                {findings.recommendations.map((rec, i) => (
                  <div key={i} style={{
                    fontSize: '0.85rem',
                    color: '#1e40af',
                    padding: '0.35rem 0',
                    borderBottom: i < findings.recommendations.length - 1 ? '1px solid #bfdbfe' : 'none',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.5rem'
                  }}>
                    <span style={{ color: '#3b82f6' }}>→</span>
                    <span>{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={styles.section}>
            <div style={styles.sectionTitle}>Status</div>
            <div style={styles.statusSelect}>
              {STATUS_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  style={styles.statusBtn(localStatus === opt.value, opt)}
                  onClick={(e) => { e.stopPropagation(); handleStatusChange(opt.value); }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Two text boxes side by side */}
          <div style={{ display: 'flex', gap: '1rem' }}>
            <div style={{ ...styles.section, flex: 1 }}>
              <div style={styles.sectionTitle}>📝 Consultant Notes</div>
              <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '0.25rem' }}>
                For team handoffs & documentation (not sent to AI)
              </div>
              <textarea
                style={styles.notesArea}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                onBlur={handleNotesChange}
                placeholder="Add consultant notes, reminders, handoff info..."
                onClick={(e) => e.stopPropagation()}
              />
            </div>
            
            <div style={{ ...styles.section, flex: 1 }}>
              <div style={styles.sectionTitle}>🤖 AI Context</div>
              <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '0.25rem' }}>
                Tell AI to adjust analysis (sent on re-scan)
              </div>
              <textarea
                style={{ ...styles.notesArea, borderColor: '#bfdbfe', background: '#f0f9ff' }}
                value={aiContext}
                onChange={(e) => setAiContext(e.target.value)}
                onBlur={handleAiContextChange}
                placeholder="e.g., 'PA rate confirmed via email 12/3', 'N/A - no employees in WA', 'Client aware, fixing in Jan'"
                onClick={(e) => e.stopPropagation()}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Step Accordion Component
function StepAccordion({ step, progress, projectId, onUpdate, tooltipsByAction, isAdmin, onAddTooltip, onEditTooltip, onDeleteTooltip, uploadedFiles }) {
  const [expanded, setExpanded] = useState(false); // Default collapsed
  
  // Safety check
  if (!step) {
    return null;
  }
  
  const actions = step.actions || [];
  const completedCount = actions.filter(a => {
    const status = progress[a?.action_id]?.status;
    return status === 'complete' || status === 'na';
  }).length;
  const totalCount = actions.length;
  const allComplete = totalCount > 0 && completedCount === totalCount;
  
  const isBefore = step.phase === 'before_final_payroll';
  
  const styles = {
    container: {
      background: 'white',
      borderRadius: '12px',
      marginBottom: '1rem',
      border: '1px solid #e1e8ed',
      overflow: 'hidden',
    },
    header: {
      padding: '1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
      cursor: 'pointer',
      background: allComplete ? '#f0fdf4' : 'white',
    },
    stepNumber: {
      fontFamily: "'Sora', sans-serif",
      fontWeight: '700',
      fontSize: '1rem',
      color: 'white',
      background: allComplete ? '#059669' : COLORS.grassGreen,
      width: '36px',
      height: '36px',
      borderRadius: '8px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    },
    stepName: {
      flex: 1,
      fontFamily: "'Sora', sans-serif",
      fontWeight: '600',
      fontSize: '1rem',
      color: COLORS.text,
    },
    progressText: {
      fontSize: '0.85rem',
      color: COLORS.textLight,
    },
    phaseBadge: {
      fontSize: '0.7rem',
      padding: '0.2rem 0.5rem',
      borderRadius: '4px',
      fontWeight: '600',
      textTransform: 'uppercase',
      background: isBefore ? '#dbeafe' : '#fae8ff',
      color: isBefore ? '#1e40af' : '#86198f',
    },
    expandIcon: {
      fontSize: '1.25rem',
      color: COLORS.textLight,
    },
    actionsContainer: {
      marginTop: '0.75rem',
      paddingLeft: '1rem',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.header} onClick={() => setExpanded(!expanded)}>
        <div style={styles.stepNumber}>{step.step_number || '?'}</div>
        <div style={styles.stepName}>{step.step_name || 'Unknown Step'}</div>
        <span style={styles.phaseBadge}>
          {isBefore ? 'Before Final' : 'After Final'}
        </span>
        <span style={styles.progressText}>
          {completedCount}/{totalCount} {allComplete && '✓'}
        </span>
        <span style={styles.expandIcon}>{expanded ? '▼' : '▶'}</span>
      </div>
      
      {expanded && (
        <div style={styles.actionsContainer}>
          {actions.map(action => action ? (
            <ErrorBoundary key={`eb-${action.action_id}`}>
              <ActionCard
                key={action.action_id}
                action={action}
                stepNumber={step.step_number}
                progress={progress[action.action_id] || {}}
                projectId={projectId}
                onUpdate={onUpdate}
                tooltips={tooltipsByAction[action.action_id] || []}
                isAdmin={isAdmin}
                onAddTooltip={onAddTooltip}
                onEditTooltip={onEditTooltip}
                onDeleteTooltip={onDeleteTooltip}
                uploadedFiles={uploadedFiles || []}
              />
            </ErrorBoundary>
          ) : null)}
        </div>
      )}
    </div>
  );
}

// Main Component
export default function YearEndPlaybook({ project, projectName, customerName, onClose }) {
  const [structure, setStructure] = useState(null);
  const [progress, setProgress] = useState({});
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [scanProgress, setScanProgress] = useState(null); // {completed, total, current_action}
  const [activePhase, setActivePhase] = useState('all');
  const [viewMode, setViewMode] = useState('ukg'); // 'ukg' or 'fasttrack'
  const [expandedAction, setExpandedAction] = useState(null); // For Fast Track expand/collapse
  
  // NEW: Document checklist and AI summary state
  const [docChecklist, setDocChecklist] = useState(null);
  const [aiSummary, setAiSummary] = useState(null);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [actionsReadyToScan, setActionsReadyToScan] = useState([]);
  const [scanningAll, setScanningAll] = useState(false);
  
  // TOOLTIPS: State for consultant-driven notes
  const [tooltipsByAction, setTooltipsByAction] = useState({});
  const [tooltipModalOpen, setTooltipModalOpen] = useState(false);
  const [tooltipModalActionId, setTooltipModalActionId] = useState(null);
  const [editingTooltip, setEditingTooltip] = useState(null);
  
  // TODO: Replace with actual auth check
  const isAdmin = true;

  // SAFETY: Only load if project exists
  useEffect(() => {
    if (project?.id) {
      loadPlaybook();
      loadDocChecklist();
      loadAiSummary();
      loadTooltips();
    }
  }, [project]);
  
  // Poll for processing jobs updates
  useEffect(() => {
    if (!project?.id) return;
    
    const interval = setInterval(() => {
      // Only poll if there are processing jobs
      if (docChecklist?.processing_jobs?.length > 0) {
        loadDocChecklist();
      }
    }, 3000); // Poll every 3 seconds
    
    return () => clearInterval(interval);
  }, [project?.id, docChecklist?.processing_jobs?.length]);

  const loadPlaybook = async () => {
    setLoading(true);
    try {
      const [structRes, progressRes] = await Promise.all([
        api.get('/playbooks/year-end/structure'),
        api.get(`/playbooks/year-end/progress/${project.id}`)
      ]);
      
      setStructure(structRes.data);
      setProgress(progressRes.data?.progress || {});
    } catch (err) {
      console.error('Failed to load playbook:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const loadDocChecklist = async () => {
    try {
      const res = await api.get(`/playbooks/year-end/document-checklist/${project.id}`);
      const data = res.data;
      
      // New step-based format
      setDocChecklist({
        has_step_documents: data.has_step_documents || false,
        uploaded_files: data.uploaded_files || [],
        step_checklists: data.step_checklists || [],
        stats: data.stats || {}
      });
    } catch (err) {
      console.error('Failed to load document checklist:', err);
    }
  };
  
  const loadAiSummary = async () => {
    try {
      const res = await api.get(`/playbooks/year-end/summary/${project.id}`);
      setAiSummary(res.data);
    } catch (err) {
      console.error('Failed to load AI summary:', err);
    }
  };
  
  // Calculate which actions have documents but haven't been scanned yet
  const calculateActionsReadyToScan = React.useCallback(() => {
    if (!structure?.steps || !docChecklist?.uploaded_files) return [];
    
    const uploadedFiles = docChecklist.uploaded_files || [];
    const normalize = (s) => s.toLowerCase().replace(/_/g, ' ').replace(/-/g, ' ').replace(/\./g, ' ').replace(/'/g, '');
    
    const ready = [];
    
    for (const step of structure.steps) {
      for (const action of (step.actions || [])) {
        if (!action?.reports_needed?.length) continue;
        
        const reportsNeeded = Array.isArray(action.reports_needed) 
          ? action.reports_needed 
          : String(action.reports_needed).split(',').map(s => s.trim());
        
        // Check if any uploaded file matches this action's reports
        let hasMatchingFile = false;
        for (const report of reportsNeeded) {
          const reportNorm = normalize(report);
          const reportWords = reportNorm.split(' ').filter(w => w.length > 2);
          
          for (const file of uploadedFiles) {
            const fileNorm = normalize(file);
            // Simple match: all report words in filename
            if (reportWords.every(w => fileNorm.includes(w))) {
              hasMatchingFile = true;
              break;
            }
          }
          if (hasMatchingFile) break;
        }
        
        // Check if this action has been scanned
        const actionProgress = progress[action.action_id] || {};
        const hasFindings = actionProgress.findings && Object.keys(actionProgress.findings).length > 0;
        
        // Ready to scan if: has matching file AND (no findings OR status is not_started)
        if (hasMatchingFile && (!hasFindings || actionProgress.status === 'not_started')) {
          ready.push({
            action_id: action.action_id,
            description: action.description,
            step_number: step.step_number
          });
        }
      }
    }
    
    return ready;
  }, [structure, docChecklist, progress]);
  
  // Update actions ready to scan when dependencies change
  React.useEffect(() => {
    const ready = calculateActionsReadyToScan();
    setActionsReadyToScan(ready);
  }, [calculateActionsReadyToScan]);
  
  // Scan all affected actions
  const handleScanAllAffected = async () => {
    if (actionsReadyToScan.length === 0) return;
    
    setScanningAll(true);
    
    try {
      for (const action of actionsReadyToScan) {
        try {
          const res = await api.post(`/playbooks/year-end/scan/${project.id}/${action.action_id}?force_refresh=true`);
          if (res.data) {
            const newDocs = res.data.documents?.map(d => d.filename) || [];
            handleUpdate(action.action_id, {
              status: res.data.suggested_status,
              findings: res.data.findings,
              documents_found: newDocs
            });
          }
        } catch (err) {
          console.error(`Scan failed for ${action.action_id}:`, err);
        }
      }
      
      // Refresh AI summary after all scans
      loadAiSummary();
      
      // Clear the ready list
      setActionsReadyToScan([]);
    } finally {
      setScanningAll(false);
    }
  };
  
  // TOOLTIP FUNCTIONS
  const loadTooltips = async () => {
    try {
      const res = await api.get('/playbooks/tooltips/bulk/year-end-2025');
      setTooltipsByAction(res.data?.tooltips_by_action || {});
    } catch (err) {
      console.error('Failed to load tooltips:', err);
    }
  };
  
  const handleAddTooltip = (actionId) => {
    setTooltipModalActionId(actionId);
    setEditingTooltip(null);
    setTooltipModalOpen(true);
  };
  
  const handleEditTooltip = (tooltip) => {
    setTooltipModalActionId(tooltip.action_id);
    setEditingTooltip(tooltip);
    setTooltipModalOpen(true);
  };
  
  const handleSaveTooltip = async (data) => {
    try {
      if (editingTooltip) {
        await api.put(`/playbooks/tooltips/${editingTooltip.id}`, data);
      } else {
        await api.post('/playbooks/tooltips', data);
      }
      await loadTooltips();
    } catch (err) {
      console.error('Failed to save tooltip:', err);
      throw err;
    }
  };
  
  const handleDeleteTooltip = async (tooltipId) => {
    if (!window.confirm('Delete this note?')) return;
    try {
      await api.delete(`/playbooks/tooltips/${tooltipId}`);
      await loadTooltips();
    } catch (err) {
      console.error('Failed to delete tooltip:', err);
    }
  };
  
  // Refresh all data
  const refreshAll = async () => {
    await Promise.all([loadPlaybook(), loadDocChecklist(), loadAiSummary()]);
  };

  const handleUpdate = (actionId, updates) => {
    setProgress(prev => ({
      ...prev,
      [actionId]: { ...prev[actionId], ...updates }
    }));
  };

  // Fast Track: Get combined status from referenced UKG actions
  const getFastTrackProgress = (ftItem) => {
    if (!ftItem?.ukg_action_ref || !Array.isArray(ftItem.ukg_action_ref) || ftItem.ukg_action_ref.length === 0) {
      return { status: 'not_started', findings: null };
    }
    
    const refStatuses = ftItem.ukg_action_ref.map(actionId => {
      const p = progress[actionId] || {};
      return p.status || 'not_started';
    });
    
    // All complete = complete, any blocked = blocked, any in_progress = in_progress, else not_started
    if (refStatuses.every(s => s === 'complete' || s === 'na')) return { status: 'complete' };
    if (refStatuses.some(s => s === 'blocked')) return { status: 'blocked' };
    if (refStatuses.some(s => s === 'in_progress' || s === 'complete')) return { status: 'in_progress' };
    return { status: 'not_started' };
  };
  
  // Fast Track: Update status (syncs to all referenced UKG actions)
  const handleFastTrackUpdate = async (ftItem, newStatus) => {
    if (!ftItem?.ukg_action_ref || !Array.isArray(ftItem.ukg_action_ref) || ftItem.ukg_action_ref.length === 0) return;
    
    for (const actionId of ftItem.ukg_action_ref) {
      try {
        await api.put(`/playbooks/year-end/progress/${project.id}/${actionId}`, {
          status: newStatus
        });
        handleUpdate(actionId, { status: newStatus });
      } catch (err) {
        console.error(`Failed to update ${actionId}:`, err);
      }
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset all progress for this playbook? This cannot be undone.')) {
      return;
    }
    
    try {
      await api.delete(`/playbooks/year-end/progress/${project.id}`);
      setProgress({});
      alert('Progress reset. Refreshing...');
      window.location.reload();
    } catch (err) {
      console.error('Reset failed:', err);
      alert('Failed to reset progress');
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await api.get(
        `/playbooks/year-end/export/${project.id}?customer_name=${encodeURIComponent(customerName || 'Customer')}`,
        { responseType: 'blob' }
      );
      
      const blob = new Blob([res.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${(customerName || 'Customer').replace(/[^a-zA-Z0-9]/g, '_')}_Year_End_Progress.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  // NEW: Callback for when non-blocking scan completes
  const handleScanComplete = async (results) => {
    console.log('[SCAN-ALL] Complete:', results);
    
    // Reload all data to show updated findings
    await refreshAll();
    
    const successful = results?.filter(r => r.found)?.length || 0;
    const total = results?.length || 0;
    
    alert(`Analysis complete: Found data for ${successful} of ${total} actions!`);
  };

  const handleScanError = (error) => {
    console.error('[SCAN-ALL] Error:', error);
    alert('Analysis encountered an error. Some actions may need manual review.');
  };
  
  const handleRefreshStructure = async () => {
    if (!window.confirm('Refresh playbook structure from Global Library and re-analyze all documents? This may take 1-2 minutes.')) {
      return;
    }
    
    setAnalyzing(true);
    
    try {
      // Step 1: Refresh structure
      const structRes = await api.post('/playbooks/year-end/refresh-structure');
      
      if (!structRes.data.success) {
        alert('Failed to refresh structure');
        setAnalyzing(false);
        return;
      }
      
      const actionCount = structRes.data.total_actions || 0;
      const sourceFile = structRes.data.source_file || 'source file';
      
      // Reload structure
      await loadPlaybook();
      
      // Step 2: Start scan-all job (runs in background)
      const scanRes = await api.post(`/playbooks/year-end/scan-all/${project.id}`);
      const results = scanRes.data;
      
      // Check if it's a background job
      if (results.job_id) {
        // Poll for completion
        const jobId = results.job_id;
        let done = false;
        let finalStatus = null;
        
        setScanProgress({ completed: 0, total: results.total_actions || 60, current_action: 'Starting...' });
        
        while (!done) {
          await new Promise(resolve => setTimeout(resolve, 1500)); // Wait 1.5s
          
          try {
            const statusRes = await api.get(`/playbooks/year-end/scan-all/status/${jobId}`);
            finalStatus = statusRes.data;
            
            // Update progress display
            setScanProgress({
              completed: finalStatus.completed || 0,
              total: finalStatus.total || 60,
              current_action: finalStatus.current_action || 'Analyzing...'
            });
            
            if (finalStatus.status === 'completed' || finalStatus.status === 'failed' || finalStatus.status === 'cancelled') {
              done = true;
            }
          } catch (pollErr) {
            console.error('Poll error:', pollErr);
            done = true;
          }
        }
        
        setScanProgress(null);
        
        // Reload all data
        await refreshAll();
        
        if (finalStatus) {
          const successful = finalStatus.successful || finalStatus.completed || 0;
          const failed = finalStatus.failed || 0;
          alert(`Structure refreshed (${actionCount} actions from ${sourceFile}) and analyzed: ${successful} successful, ${failed} failed.`);
        } else {
          alert(`Structure refreshed (${actionCount} actions from ${sourceFile}). Analysis completed.`);
        }
      } else {
        // Immediate result (legacy)
        await refreshAll();
        const successful = results.successful || 0;
        const failed = results.failed || 0;
        alert(`Structure refreshed (${actionCount} actions from ${sourceFile}) and re-analyzed: ${successful} successful, ${failed} failed.`);
      }
      
    } catch (err) {
      console.error('Refresh and analyze failed:', err);
      alert('Failed to refresh structure. Check that Year-End Checklist is in Global Library.');
    } finally {
      setAnalyzing(false);
      setScanProgress(null);
    }
  };

  // Calculate progress stats
  const totalActions = structure?.total_actions || 0;
  const completedActions = Object.values(progress).filter(p => 
    p.status === 'complete' || p.status === 'na'
  ).length;
  const progressPercent = totalActions > 0 ? Math.round((completedActions / totalActions) * 100) : 0;

  // Filter steps by phase
  const filteredSteps = structure?.steps?.filter(step => {
    if (activePhase === 'all') return true;
    return step.phase === activePhase;
  }) || [];

  const styles = {
    container: {
      maxWidth: '1000px',
      margin: '0 auto',
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      marginBottom: '1.5rem',
      flexWrap: 'wrap',
      gap: '1rem',
    },
    titleSection: {},
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.75rem',
      fontWeight: '700',
      color: COLORS.text,
      margin: 0,
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    subtitle: {
      color: COLORS.textLight,
      marginTop: '0.25rem',
    },
    headerActions: {
      display: 'flex',
      gap: '0.75rem',
      flexWrap: 'wrap',
      alignItems: 'flex-start',
    },
    backBtn: {
      padding: '0.5rem 1rem',
      background: 'white',
      border: '1px solid #e1e8ed',
      borderRadius: '8px',
      color: COLORS.textLight,
      fontWeight: '600',
      cursor: 'pointer',
    },
    resetBtn: {
      padding: '0.5rem 1rem',
      background: '#fee2e2',
      border: '1px solid #fecaca',
      borderRadius: '8px',
      color: '#dc2626',
      fontWeight: '600',
      cursor: 'pointer',
    },
    exportBtn: {
      padding: '0.5rem 1rem',
      background: COLORS.grassGreen,
      border: 'none',
      borderRadius: '8px',
      color: 'white',
      fontWeight: '600',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    refreshStructureBtn: {
      padding: '0.5rem 1rem',
      background: analyzing ? '#9ca3af' : '#8b5cf6',
      border: 'none',
      borderRadius: '8px',
      color: 'white',
      fontWeight: '600',
      cursor: analyzing ? 'not-allowed' : 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    progressCard: {
      background: 'white',
      borderRadius: '12px',
      padding: '1.25rem',
      marginBottom: '1.5rem',
      border: '1px solid #e1e8ed',
    },
    progressBar: {
      height: '12px',
      background: '#e1e8ed',
      borderRadius: '6px',
      overflow: 'hidden',
      marginBottom: '0.75rem',
    },
    progressFill: {
      height: '100%',
      background: `linear-gradient(90deg, ${COLORS.grassGreen}, #6aa84f)`,
      borderRadius: '6px',
      transition: 'width 0.3s ease',
      width: `${progressPercent}%`,
    },
    progressStats: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    progressText: {
      fontWeight: '600',
      color: COLORS.text,
    },
    progressPercent: {
      fontSize: '1.5rem',
      fontWeight: '700',
      color: COLORS.grassGreen,
    },
    phaseFilter: {
      display: 'flex',
      gap: '0.5rem',
      marginBottom: '1.5rem',
    },
    phaseBtn: (isActive) => ({
      padding: '0.5rem 1rem',
      background: isActive ? COLORS.grassGreen : 'white',
      border: `1px solid ${isActive ? COLORS.grassGreen : '#e1e8ed'}`,
      borderRadius: '20px',
      color: isActive ? 'white' : COLORS.textLight,
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
    }),
    loadingState: {
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '300px',
      color: COLORS.textLight,
      gap: '1rem',
    },
  };

  // SAFETY CHECK: If no project, show error
  if (!project?.id) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingState}>
          <span>Error: No project selected. Please go back and select a project.</span>
          <button style={styles.backBtn} onClick={onClose}>← Back</button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingState}>
          <span>Loading Year-End Checklist...</span>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
    <div style={{ display: 'flex' }}>
      {/* Main Content */}
      <div style={{ ...styles.container, marginRight: sidebarCollapsed ? '40px' : '320px', transition: 'margin-right 0.3s ease' }}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.titleSection}>
            <h1 style={styles.title}>📅 Year-End Checklist</h1>
            <p style={styles.subtitle}>
              {customerName || 'Customer'} → {projectName || 'Project'}
            </p>
          </div>
          <div style={styles.headerActions}>
            <button style={styles.backBtn} onClick={onClose}>
              ← Back
            </button>
            <button 
              style={styles.refreshStructureBtn} 
              onClick={handleRefreshStructure}
              disabled={analyzing}
              title="Refresh playbook structure from Global Library and re-analyze all documents"
            >
              {analyzing 
                ? (scanProgress 
                    ? `⏳ Analyzing ${scanProgress.completed}/${scanProgress.total} (${scanProgress.current_action || '...'})` 
                    : '⏳ Refreshing...')
                : '🔄 Refresh & Analyze'}
            </button>
            
            {/* NEW: Non-blocking scan progress component */}
            <ScanAllProgress
              projectId={project.id}
              onComplete={handleScanComplete}
              onError={handleScanError}
              buttonText="🔍 Analyze All"
              disabled={analyzing}
            />
            
            <button 
              style={styles.resetBtn} 
              onClick={handleReset}
              title="Reset all progress for this project"
            >
              🗑️ Reset
            </button>
            <button style={styles.exportBtn} onClick={handleExport} disabled={exporting}>
              {exporting ? '⏳ Exporting...' : '📥 Export Progress'}
            </button>
          </div>
        </div>
        
        {/* AI Summary Dashboard */}
        <AISummaryDashboard 
          summary={aiSummary} 
          expanded={summaryExpanded} 
          onToggle={() => setSummaryExpanded(!summaryExpanded)} 
        />

        {/* Progress Card */}
        <div style={styles.progressCard}>
          <div style={styles.progressBar}>
            <div style={styles.progressFill} />
          </div>
          <div style={styles.progressStats}>
            <span style={styles.progressText}>
              {completedActions} of {totalActions} actions complete
            </span>
            <span style={styles.progressPercent}>{progressPercent}%</span>
          </div>
        </div>

        {/* View Mode Toggle */}
        <div style={{ 
          display: 'flex', 
          gap: '0.5rem', 
          marginBottom: '1rem',
          padding: '0.25rem',
          background: '#f1f5f9',
          borderRadius: '8px',
          width: 'fit-content'
        }}>
          <button
            onClick={() => setViewMode('ukg')}
            style={{
              padding: '0.5rem 1rem',
              border: 'none',
              borderRadius: '6px',
              fontWeight: '600',
              cursor: 'pointer',
              background: viewMode === 'ukg' ? 'white' : 'transparent',
              color: viewMode === 'ukg' ? '#1e40af' : '#64748b',
              boxShadow: viewMode === 'ukg' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              transition: 'all 0.2s'
            }}
          >
            📋 UKG Full Checklist
          </button>
          <button
            onClick={() => setViewMode('fasttrack')}
            style={{
              padding: '0.5rem 1rem',
              border: 'none',
              borderRadius: '6px',
              fontWeight: '600',
              cursor: 'pointer',
              background: viewMode === 'fasttrack' ? 'white' : 'transparent',
              color: viewMode === 'fasttrack' ? '#059669' : '#64748b',
              boxShadow: viewMode === 'fasttrack' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              transition: 'all 0.2s'
            }}
          >
            ⚡ Fast Track
          </button>
        </div>

        {/* Phase Filter - only show for UKG view */}
        {viewMode === 'ukg' && (
        <div style={styles.phaseFilter}>
          <button 
            style={styles.phaseBtn(activePhase === 'all')} 
            onClick={() => setActivePhase('all')}
          >
            All Steps
          </button>
          <button 
            style={styles.phaseBtn(activePhase === 'before_final_payroll')} 
            onClick={() => setActivePhase('before_final_payroll')}
          >
            Before Final Payroll
          </button>
          <button 
            style={styles.phaseBtn(activePhase === 'after_final_payroll')} 
            onClick={() => setActivePhase('after_final_payroll')}
          >
            After Final Payroll
          </button>
        </div>
        )}

        {/* Smart Queue - Actions Ready to Analyze */}
        {actionsReadyToScan.length > 0 && (
          <div style={{
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            borderRadius: '8px',
            padding: '0.75rem 1rem',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.25rem' }}>📋</span>
              <div>
                <div style={{ fontWeight: '600', color: '#1e40af' }}>
                  {actionsReadyToScan.length} action{actionsReadyToScan.length > 1 ? 's' : ''} ready to analyze
                </div>
                <div style={{ fontSize: '0.8rem', color: '#3b82f6' }}>
                  Documents uploaded - click to run AI analysis
                </div>
              </div>
            </div>
            <button
              onClick={handleScanAllAffected}
              disabled={scanningAll}
              style={{
                background: scanningAll ? '#94a3b8' : '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                padding: '0.5rem 1rem',
                fontWeight: '600',
                cursor: scanningAll ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              {scanningAll ? (
                <>
                  <span style={{ animation: 'spin 1s linear infinite' }}>⏳</span>
                  Analyzing...
                </>
              ) : (
                <>
                  🔍 Analyze All
                </>
              )}
            </button>
          </div>
        )}

        {/* UKG Full Checklist View */}
        {viewMode === 'ukg' && filteredSteps.map(step => (
          <StepAccordion
            key={step.step_number || Math.random()}
            step={step}
            progress={progress}
            projectId={project.id}
            onUpdate={handleUpdate}
            tooltipsByAction={tooltipsByAction}
            isAdmin={isAdmin}
            onAddTooltip={handleAddTooltip}
            onEditTooltip={handleEditTooltip}
            onDeleteTooltip={handleDeleteTooltip}
            uploadedFiles={docChecklist?.uploaded_files || []}
          />
        ))}

        {/* Fast Track View */}
        {viewMode === 'fasttrack' && (
          <div style={{ background: 'white', borderRadius: '12px', padding: '1rem', border: '1px solid #e1e8ed' }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem', 
              marginBottom: '1rem',
              paddingBottom: '0.75rem',
              borderBottom: '1px solid #e1e8ed'
            }}>
              <span style={{ fontSize: '1.5rem' }}>⚡</span>
              <div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#059669' }}>Fast Track Checklist</div>
                <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>HCMPACT's curated essential actions • Status syncs with UKG actions</div>
              </div>
            </div>
            
            {(structure?.fast_track || []).map((ftItem, index) => {
              const ftProgress = getFastTrackProgress(ftItem);
              // Get the primary linked UKG action for details
              const primaryActionId = ftItem.ukg_action_ref?.[0];
              const primaryActionProgress = primaryActionId ? (progress[primaryActionId] || {}) : {};
              
              const statusColors = {
                complete: { bg: '#f0fdf4', border: '#bbf7d0', text: '#166534', badge: '#22c55e' },
                in_progress: { bg: '#eff6ff', border: '#bfdbfe', text: '#1e40af', badge: '#3b82f6' },
                blocked: { bg: '#fef2f2', border: '#fecaca', text: '#991b1b', badge: '#ef4444' },
                na: { bg: '#f5f5f4', border: '#d6d3d1', text: '#57534e', badge: '#78716c' },
                not_started: { bg: '#f9fafb', border: '#e5e7eb', text: '#374151', badge: '#9ca3af' }
              };
              const colors = statusColors[ftProgress.status] || statusColors.not_started;
              
              // Track expanded state for this FT item
              const isExpanded = expandedAction === `ft_${ftItem.ft_id}`;
              
              // Get documents found for linked actions
              const linkedDocsFound = (Array.isArray(ftItem.ukg_action_ref) ? ftItem.ukg_action_ref : []).flatMap(actionId => 
                progress[actionId]?.documents_found || []
              );
              
              return (
                <div 
                  key={ftItem.ft_id}
                  style={{
                    background: colors.bg,
                    border: `1px solid ${colors.border}`,
                    borderRadius: '8px',
                    marginBottom: '0.75rem',
                    overflow: 'hidden'
                  }}
                >
                  {/* Header Row - Clickable */}
                  <div 
                    onClick={() => setExpandedAction(isExpanded ? null : `ft_${ftItem.ft_id}`)}
                    style={{ 
                      display: 'flex', 
                      alignItems: 'flex-start', 
                      justifyContent: 'space-between',
                      padding: '1rem',
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                        <span style={{ 
                          background: colors.badge, 
                          color: 'white', 
                          borderRadius: '50%',
                          width: '24px',
                          height: '24px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '0.8rem',
                          fontWeight: '700'
                        }}>
                          {ftItem.sequence}
                        </span>
                        <span style={{ fontWeight: '600', color: colors.text }}>{ftItem.description}</span>
                      </div>
                      
                      <div style={{ marginLeft: '32px', display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
                        {Array.isArray(ftItem.ukg_action_ref) && ftItem.ukg_action_ref.length > 0 && (
                          <span style={{ fontSize: '0.75rem', color: '#6b7280', background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>
                            🔗 UKG: {ftItem.ukg_action_ref.join(', ')}
                          </span>
                        )}
                        
                        {Array.isArray(ftItem.reports_needed) && ftItem.reports_needed.length > 0 && (
                          <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                            📄 {ftItem.reports_needed.length} report{ftItem.reports_needed.length > 1 ? 's' : ''}
                          </span>
                        )}
                        
                        {linkedDocsFound.length > 0 && (
                          <span style={{ fontSize: '0.75rem', color: '#22c55e' }}>
                            ✓ {linkedDocsFound.length} doc{linkedDocsFound.length > 1 ? 's' : ''} found
                          </span>
                        )}
                        
                        {ftItem.notes && (
                          <span style={{ fontSize: '0.75rem', color: '#f59e0b' }}>
                            📝 Has notes
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }} onClick={e => e.stopPropagation()}>
                      {/* SQL Copy Button with Tooltip */}
                      {ftItem.sql_script && (
                        <div style={{ position: 'relative' }} className="sql-tooltip-container">
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(ftItem.sql_script);
                              alert('SQL copied to clipboard!');
                            }}
                            style={{
                              background: '#dbeafe',
                              border: '1px solid #93c5fd',
                              borderRadius: '4px',
                              padding: '0.25rem 0.5rem',
                              fontSize: '0.75rem',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem',
                              color: '#1e40af'
                            }}
                            title={ftItem.sql_script}
                          >
                            📋 SQL
                          </button>
                        </div>
                      )}
                      
                      {/* Status Dropdown */}
                      <select
                        value={ftProgress.status}
                        onChange={(e) => handleFastTrackUpdate(ftItem, e.target.value)}
                        style={{
                          background: colors.badge,
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '0.25rem 0.5rem',
                          fontSize: '0.7rem',
                          fontWeight: '600',
                          cursor: 'pointer'
                        }}
                      >
                        <option value="not_started">Not Started</option>
                        <option value="in_progress">In Progress</option>
                        <option value="complete">Complete</option>
                        <option value="blocked">Blocked</option>
                        <option value="na">N/A</option>
                      </select>
                      
                      {/* Expand Arrow */}
                      <span style={{ color: '#9ca3af', fontSize: '0.9rem', marginLeft: '0.25rem' }}>
                        {isExpanded ? '▼' : '▶'}
                      </span>
                    </div>
                  </div>
                  
                  {/* Expanded Details */}
                  {isExpanded && (
                    <div style={{ 
                      borderTop: `1px solid ${colors.border}`,
                      padding: '1rem',
                      background: 'rgba(255,255,255,0.5)'
                    }}>
                      {/* FT Notes from Workbook */}
                      {ftItem.notes && (
                        <div style={{ marginBottom: '1rem' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#6b7280', marginBottom: '0.25rem' }}>
                            📋 FAST TRACK NOTES (from workbook)
                          </div>
                          <div style={{ 
                            background: '#fffbeb', 
                            border: '1px solid #fcd34d',
                            borderRadius: '6px',
                            padding: '0.75rem',
                            fontSize: '0.85rem',
                            color: '#92400e'
                          }}>
                            {ftItem.notes}
                          </div>
                        </div>
                      )}
                      
                      {/* SQL Script Display */}
                      {ftItem.sql_script && (
                        <div style={{ marginBottom: '1rem' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#6b7280', marginBottom: '0.25rem' }}>
                            💾 SQL SCRIPT
                          </div>
                          <pre style={{ 
                            background: '#1e293b', 
                            color: '#e2e8f0',
                            borderRadius: '6px',
                            padding: '0.75rem',
                            fontSize: '0.75rem',
                            overflow: 'auto',
                            maxHeight: '150px',
                            margin: 0
                          }}>
                            {ftItem.sql_script}
                          </pre>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(ftItem.sql_script);
                              alert('SQL copied!');
                            }}
                            style={{
                              marginTop: '0.5rem',
                              background: '#3b82f6',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              padding: '0.25rem 0.75rem',
                              fontSize: '0.75rem',
                              cursor: 'pointer'
                            }}
                          >
                            📋 Copy SQL
                          </button>
                        </div>
                      )}
                      
                      {/* Reports Needed */}
                      {Array.isArray(ftItem.reports_needed) && ftItem.reports_needed.length > 0 && (
                        <div style={{ marginBottom: '1rem' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#6b7280', marginBottom: '0.25rem' }}>
                            📄 REPORTS NEEDED
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                            {ftItem.reports_needed.map((report, i) => {
                              const isFound = linkedDocsFound.some(d => 
                                d.toLowerCase().includes(report.toLowerCase().split(' ')[0])
                              );
                              return (
                                <span 
                                  key={i}
                                  style={{
                                    background: isFound ? '#dcfce7' : '#f1f5f9',
                                    color: isFound ? '#166534' : '#64748b',
                                    padding: '0.25rem 0.5rem',
                                    borderRadius: '4px',
                                    fontSize: '0.75rem',
                                    border: `1px solid ${isFound ? '#bbf7d0' : '#e2e8f0'}`
                                  }}
                                >
                                  {isFound ? '✓' : '○'} {report}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      )}
                      
                      {/* Linked UKG Actions Details */}
                      {Array.isArray(ftItem.ukg_action_ref) && ftItem.ukg_action_ref.length > 0 && (
                        <div style={{ marginBottom: '1rem' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#6b7280', marginBottom: '0.5rem' }}>
                            🔗 LINKED UKG ACTIONS
                          </div>
                          {ftItem.ukg_action_ref.map(actionId => {
                            const actionProg = progress[actionId] || {};
                            const actionStatus = actionProg.status || 'not_started';
                            const actionColors = statusColors[actionStatus] || statusColors.not_started;
                            
                            // Find the action details from structure
                            let actionDesc = '';
                            for (const step of (structure?.steps || [])) {
                              const found = step.actions?.find(a => a.action_id === actionId);
                              if (found) {
                                actionDesc = found.description?.substring(0, 100) + '...';
                                break;
                              }
                            }
                            
                            return (
                              <div 
                                key={actionId}
                                style={{
                                  background: actionColors.bg,
                                  border: `1px solid ${actionColors.border}`,
                                  borderRadius: '6px',
                                  padding: '0.75rem',
                                  marginBottom: '0.5rem'
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <div>
                                    <span style={{ fontWeight: '600', color: actionColors.text }}>{actionId}</span>
                                    <span style={{ 
                                      marginLeft: '0.5rem',
                                      background: actionColors.badge,
                                      color: 'white',
                                      padding: '2px 6px',
                                      borderRadius: '4px',
                                      fontSize: '0.65rem',
                                      textTransform: 'uppercase'
                                    }}>
                                      {actionStatus.replace('_', ' ')}
                                    </span>
                                  </div>
                                  <button
                                    onClick={() => {
                                      setExpandedAction(actionId);
                                      setViewMode('ukg');
                                    }}
                                    style={{
                                      background: 'transparent',
                                      border: '1px solid #cbd5e1',
                                      borderRadius: '4px',
                                      padding: '0.25rem 0.5rem',
                                      fontSize: '0.7rem',
                                      cursor: 'pointer',
                                      color: '#64748b'
                                    }}
                                  >
                                    View in UKG →
                                  </button>
                                </div>
                                {actionDesc && (
                                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                                    {actionDesc}
                                  </div>
                                )}
                                {actionProg.documents_found?.length > 0 && (
                                  <div style={{ fontSize: '0.7rem', color: '#22c55e', marginTop: '0.25rem' }}>
                                    ✓ {actionProg.documents_found.length} document{actionProg.documents_found.length > 1 ? 's' : ''} found
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                      
                      {/* Notes Section - Same as UKG Actions */}
                      <div style={{ marginBottom: '1rem' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#6b7280', marginBottom: '0.5rem' }}>
                          ✏️ CONSULTANT NOTES & AI CONTEXT
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                          {/* Consultant Notes - syncs to primary linked action */}
                          <div>
                            <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '0.25rem' }}>
                              📝 Notes (for handoffs)
                            </div>
                            <textarea
                              value={primaryActionProgress.notes || ''}
                              onChange={async (e) => {
                                if (!primaryActionId) return;
                                const newNotes = e.target.value;
                                handleUpdate(primaryActionId, { notes: newNotes });
                                try {
                                  await api.put(`/playbooks/year-end/progress/${project.id}/${primaryActionId}`, {
                                    notes: newNotes
                                  });
                                } catch (err) {
                                  console.error('Failed to save notes:', err);
                                }
                              }}
                              placeholder="Add notes for team handoffs..."
                              style={{
                                width: '100%',
                                minHeight: '80px',
                                padding: '0.5rem',
                                borderRadius: '6px',
                                border: '1px solid #d1d5db',
                                fontSize: '0.8rem',
                                resize: 'vertical'
                              }}
                            />
                          </div>
                          
                          {/* AI Context - syncs to primary linked action */}
                          <div>
                            <div style={{ fontSize: '0.7rem', color: '#3b82f6', marginBottom: '0.25rem' }}>
                              🤖 AI Context (sent on re-scan)
                            </div>
                            <textarea
                              value={primaryActionProgress.ai_context || ''}
                              onChange={async (e) => {
                                if (!primaryActionId) return;
                                const newContext = e.target.value;
                                handleUpdate(primaryActionId, { ai_context: newContext });
                                try {
                                  await api.put(`/playbooks/year-end/progress/${project.id}/${primaryActionId}`, {
                                    ai_context: newContext
                                  });
                                } catch (err) {
                                  console.error('Failed to save AI context:', err);
                                }
                              }}
                              placeholder="Tell AI to adjust analysis..."
                              style={{
                                width: '100%',
                                minHeight: '80px',
                                padding: '0.5rem',
                                borderRadius: '6px',
                                border: '1px solid #bfdbfe',
                                background: '#f0f9ff',
                                fontSize: '0.8rem',
                                resize: 'vertical'
                              }}
                            />
                          </div>
                        </div>
                      </div>
                      
                      {/* Scan Button */}
                      {primaryActionId && (
                        <button
                          onClick={async () => {
                            try {
                              const res = await api.post(`/playbooks/year-end/scan/${project.id}/${primaryActionId}?force_refresh=true`);
                              handleUpdate(primaryActionId, {
                                status: res.data.suggested_status,
                                findings: res.data.findings,
                                documents_found: res.data.documents?.map(d => d.filename) || []
                              });
                              loadAiSummary();
                            } catch (err) {
                              console.error('Scan failed:', err);
                            }
                          }}
                          style={{
                            background: '#8b5cf6',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            padding: '0.5rem 1rem',
                            fontSize: '0.8rem',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                          }}
                        >
                          🔍 Scan Documents for {primaryActionId}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
            
            {(!structure?.fast_track || structure.fast_track.length === 0) && (
              <div style={{ 
                textAlign: 'center', 
                padding: '2rem', 
                color: '#6b7280',
                fontStyle: 'italic'
              }}>
                No Fast Track items defined. Add fast_track_seq column to your workbook.
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Document Checklist Sidebar */}
      <DocumentChecklistSidebar 
        checklist={docChecklist} 
        collapsed={sidebarCollapsed} 
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        onKeywordUpdate={loadDocChecklist}
      />
      
      {/* Tooltip Add/Edit Modal */}
      <TooltipModal
        isOpen={tooltipModalOpen}
        onClose={() => {
          setTooltipModalOpen(false);
          setEditingTooltip(null);
        }}
        onSave={handleSaveTooltip}
        actionId={tooltipModalActionId}
        existingTooltip={editingTooltip}
      />
    </div>
    </ErrorBoundary>
  );
}
