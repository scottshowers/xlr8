/**
 * ScanAllProgress Component - Non-blocking scan with live progress
 * ================================================================
 * 
 * Drop-in replacement for the old blocking "Analyze All" button.
 * Shows real-time progress, never freezes the UI.
 * 
 * Usage:
 *   <ScanAllProgress 
 *     projectId={currentProject.id}
 *     onComplete={(results) => handleScanComplete(results)}
 *     onError={(error) => console.error(error)}
 *   />
 * 
 * Author: XLR8 Team
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = '/api';

// Status colors and icons
const STATUS_CONFIG = {
  pending: { color: '#6b7280', bg: '#f3f4f6', icon: '⏳', label: 'Waiting...' },
  running: { color: '#3b82f6', bg: '#dbeafe', icon: '🔄', label: 'Scanning...' },
  completed: { color: '#10b981', bg: '#d1fae5', icon: '✅', label: 'Complete' },
  failed: { color: '#ef4444', bg: '#fee2e2', icon: '❌', label: 'Failed' },
  timeout: { color: '#f59e0b', bg: '#fef3c7', icon: '⏰', label: 'Timed Out' },
  cancelled: { color: '#6b7280', bg: '#f3f4f6', icon: '🚫', label: 'Cancelled' },
};

export default function ScanAllProgress({ 
  projectId, 
  onComplete, 
  onError,
  onStart,
  buttonText = "🔍 Analyze All Documents",
  autoStart = false 
}) {
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

  // Auto-start if requested
  useEffect(() => {
    if (autoStart && projectId && !jobId) {
      startScan();
    }
  }, [autoStart, projectId]);

  // Start the scan
  const startScan = async () => {
    if (!projectId) {
      onError?.('No project selected');
      return;
    }

    setIsStarting(true);
    setStatus(null);

    try {
      const response = await fetch(`${API_BASE}/playbooks/year-end/scan-all/${projectId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error(`Failed to start scan: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (!data.job_id) {
        // No actions to scan
        setStatus({
          status: 'completed',
          message: data.message || 'No actions to scan',
          progress_percent: 100,
        });
        onComplete?.([]);
        return;
      }

      setJobId(data.job_id);
      onStart?.(data);

      // Start polling
      startPolling(data.job_id);

    } catch (error) {
      console.error('[SCAN] Start error:', error);
      onError?.(error.message);
      setStatus({
        status: 'failed',
        message: error.message,
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
        const response = await fetch(`${API_BASE}/playbooks/year-end/scan-all/status/${jid}`);
        
        if (!response.ok) {
          throw new Error('Failed to get status');
        }

        const data = await response.json();
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
      await fetch(`${API_BASE}/playbooks/year-end/scan-all/cancel/${jobId}`, {
        method: 'POST',
      });
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
  const config = STATUS_CONFIG[status?.status] || STATUS_CONFIG.pending;

  return (
    <div style={styles.container}>
      {/* Start Button - show when no active job */}
      {!jobId && !status && (
        <button 
          onClick={startScan}
          disabled={isStarting || !projectId}
          style={{
            ...styles.button,
            opacity: (isStarting || !projectId) ? 0.6 : 1,
            cursor: (isStarting || !projectId) ? 'not-allowed' : 'pointer',
          }}
        >
          {isStarting ? '⏳ Starting...' : buttonText}
        </button>
      )}

      {/* Progress Display */}
      {status && (
        <div style={{ ...styles.progressContainer, backgroundColor: config.bg, borderColor: config.color }}>
          {/* Header */}
          <div style={styles.header}>
            <span style={{ fontSize: '1.25rem' }}>{config.icon}</span>
            <span style={{ fontWeight: 600, color: config.color }}>{config.label}</span>
            {isRunning && (
              <button onClick={cancelScan} style={styles.cancelButton}>
                Cancel
              </button>
            )}
          </div>

          {/* Progress Bar */}
          <div style={styles.progressBarContainer}>
            <div 
              style={{
                ...styles.progressBar,
                width: `${status.progress_percent || 0}%`,
                backgroundColor: config.color,
              }}
            />
          </div>

          {/* Status Text */}
          <div style={styles.statusText}>
            <span>{status.message}</span>
            <span style={{ fontWeight: 600 }}>{status.progress_percent || 0}%</span>
          </div>

          {/* Current Action */}
          {isRunning && status.current_action && (
            <div style={styles.currentAction}>
              Currently scanning: <strong>{status.current_action}</strong>
            </div>
          )}

          {/* Stats */}
          {status.total_actions > 0 && (
            <div style={styles.stats}>
              <span>📋 {status.completed_actions || 0}/{status.total_actions} actions</span>
              {status.successful > 0 && <span style={{ color: '#10b981' }}>✓ {status.successful} found</span>}
              {status.failed > 0 && <span style={{ color: '#ef4444' }}>✗ {status.failed} failed</span>}
            </div>
          )}

          {/* Errors */}
          {status.errors?.length > 0 && (
            <div style={styles.errors}>
              {status.errors.slice(0, 3).map((err, i) => (
                <div key={i} style={styles.errorItem}>
                  ⚠️ {err.action_id}: {err.error?.slice(0, 50)}...
                </div>
              ))}
              {status.errors.length > 3 && (
                <div style={styles.errorItem}>...and {status.errors.length - 3} more</div>
              )}
            </div>
          )}

          {/* Done Actions */}
          {isDone && (
            <div style={styles.doneActions}>
              <button onClick={reset} style={styles.resetButton}>
                🔄 Scan Again
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Styles
const styles = {
  container: {
    width: '100%',
  },
  button: {
    width: '100%',
    padding: '12px 24px',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '1rem',
    fontWeight: 600,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    transition: 'all 0.2s',
  },
  progressContainer: {
    padding: '16px',
    borderRadius: '8px',
    border: '2px solid',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '12px',
  },
  cancelButton: {
    marginLeft: 'auto',
    padding: '4px 12px',
    backgroundColor: '#fee2e2',
    color: '#ef4444',
    border: '1px solid #ef4444',
    borderRadius: '4px',
    fontSize: '0.875rem',
    cursor: 'pointer',
  },
  progressBarContainer: {
    height: '8px',
    backgroundColor: '#e5e7eb',
    borderRadius: '4px',
    overflow: 'hidden',
    marginBottom: '8px',
  },
  progressBar: {
    height: '100%',
    transition: 'width 0.3s ease',
    borderRadius: '4px',
  },
  statusText: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.875rem',
    color: '#374151',
    marginBottom: '8px',
  },
  currentAction: {
    fontSize: '0.875rem',
    color: '#6b7280',
    padding: '8px',
    backgroundColor: 'rgba(255,255,255,0.5)',
    borderRadius: '4px',
    marginBottom: '8px',
  },
  stats: {
    display: 'flex',
    gap: '16px',
    fontSize: '0.875rem',
    color: '#6b7280',
    flexWrap: 'wrap',
  },
  errors: {
    marginTop: '12px',
    padding: '8px',
    backgroundColor: '#fef2f2',
    borderRadius: '4px',
    fontSize: '0.75rem',
  },
  errorItem: {
    color: '#b91c1c',
    marginBottom: '4px',
  },
  doneActions: {
    marginTop: '12px',
    display: 'flex',
    justifyContent: 'center',
  },
  resetButton: {
    padding: '8px 16px',
    backgroundColor: 'white',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '0.875rem',
    cursor: 'pointer',
  },
};


/**
 * INTEGRATION EXAMPLE
 * ===================
 * 
 * In your YearEndPlaybook.jsx, replace the old "Analyze All" button:
 * 
 * OLD (blocking):
 * ```jsx
 * <button onClick={handleAnalyzeAll}>Analyze All</button>
 * 
 * const handleAnalyzeAll = async () => {
 *   setLoading(true);
 *   const result = await fetch(`/api/playbooks/year-end/scan-all/${projectId}`, {
 *     method: 'POST'
 *   });
 *   // This would freeze for 20 minutes!
 *   setLoading(false);
 * };
 * ```
 * 
 * NEW (non-blocking):
 * ```jsx
 * import ScanAllProgress from './ScanAllProgress';
 * 
 * <ScanAllProgress
 *   projectId={currentProject?.id}
 *   onComplete={(results) => {
 *     console.log('Scan complete!', results);
 *     // Refresh the playbook data
 *     fetchProgress();
 *   }}
 *   onError={(error) => {
 *     console.error('Scan failed:', error);
 *   }}
 * />
 * ```
 * 
 * That's it! The component handles everything:
 * - Starting the scan
 * - Polling for progress
 * - Showing progress bar
 * - Showing current action
 * - Cancel button
 * - Error handling
 * - Reset for new scan
 */
