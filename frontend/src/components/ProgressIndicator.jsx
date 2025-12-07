/**
 * ProgressIndicator - Real-time chunk processing progress
 * 
 * Shows live updates as PDF chunks are processed in parallel.
 * Includes overall progress bar + chunk-by-chunk details.
 */

import React from 'react';
import { useProgressStream } from '../hooks/useProgressStream';

const styles = {
  container: {
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    padding: '1rem',
    marginBottom: '1rem',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.75rem',
  },
  title: {
    fontWeight: '600',
    color: '#334155',
    fontSize: '0.9rem',
  },
  status: {
    fontSize: '0.8rem',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
  },
  progressBar: {
    height: '8px',
    background: '#e2e8f0',
    borderRadius: '4px',
    overflow: 'hidden',
    marginBottom: '0.75rem',
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #3b82f6, #2563eb)',
    borderRadius: '4px',
    transition: 'width 0.3s ease',
  },
  stats: {
    display: 'flex',
    gap: '1.5rem',
    fontSize: '0.8rem',
    color: '#64748b',
  },
  stat: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.35rem',
  },
  statValue: {
    fontWeight: '600',
    color: '#334155',
  },
  currentStep: {
    fontSize: '0.8rem',
    color: '#64748b',
    marginTop: '0.5rem',
    fontStyle: 'italic',
  },
  chunkList: {
    marginTop: '0.75rem',
    maxHeight: '120px',
    overflowY: 'auto',
    fontSize: '0.75rem',
    fontFamily: 'monospace',
    background: '#1e293b',
    color: '#94a3b8',
    borderRadius: '4px',
    padding: '0.5rem',
  },
  chunkItem: {
    padding: '0.15rem 0',
  },
  chunkSuccess: {
    color: '#4ade80',
  },
  chunkFailed: {
    color: '#f87171',
  },
  chunkMethod: {
    color: '#fbbf24',
  },
};

const statusColors = {
  pending: { background: '#fef3c7', color: '#92400e' },
  processing: { background: '#dbeafe', color: '#1e40af' },
  completed: { background: '#d1fae5', color: '#065f46' },
  failed: { background: '#fee2e2', color: '#991b1b' },
  error: { background: '#fee2e2', color: '#991b1b' },
};

export function ProgressIndicator({ jobId, showChunkDetails = true }) {
  const {
    progress,
    chunks,
    chunkUpdates,
    isComplete,
    error,
    isProcessing,
    chunkPercent,
  } = useProgressStream(jobId);

  if (!jobId) return null;

  const statusStyle = statusColors[progress.status] || statusColors.pending;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.title}>
          {isProcessing ? '⚡ Processing PDF...' : isComplete ? '✓ Complete' : 'Starting...'}
        </span>
        <span style={{ ...styles.status, ...statusStyle }}>
          {progress.status}
        </span>
      </div>

      {/* Progress Bar */}
      <div style={styles.progressBar}>
        <div 
          style={{ 
            ...styles.progressFill, 
            width: `${progress.percent}%`,
            background: error ? '#ef4444' : undefined,
          }} 
        />
      </div>

      {/* Stats */}
      <div style={styles.stats}>
        <div style={styles.stat}>
          <span>Progress:</span>
          <span style={styles.statValue}>{progress.percent}%</span>
        </div>
        
        {chunks.total > 0 && (
          <>
            <div style={styles.stat}>
              <span>Chunks:</span>
              <span style={styles.statValue}>{chunks.done}/{chunks.total}</span>
            </div>
            <div style={styles.stat}>
              <span>Rows:</span>
              <span style={styles.statValue}>{chunks.rowsSoFar.toLocaleString()}</span>
            </div>
          </>
        )}
      </div>

      {/* Current Step */}
      {progress.currentStep && (
        <div style={styles.currentStep}>
          {progress.currentStep}
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ ...styles.currentStep, color: '#ef4444' }}>
          Error: {error}
        </div>
      )}

      {/* Chunk Details (optional) */}
      {showChunkDetails && chunkUpdates.length > 0 && (
        <div style={styles.chunkList}>
          {chunkUpdates.slice(-10).map((update, idx) => (
            <div key={idx} style={styles.chunkItem}>
              <span style={update.status === 'done' ? styles.chunkSuccess : {}}>
                Chunk {update.chunk_index + 1}/{update.total_chunks}:
              </span>
              {' '}
              <span style={styles.chunkMethod}>[{update.method}]</span>
              {' '}
              {update.rows_found} rows
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Compact version for inline use
 */
export function ProgressBar({ jobId }) {
  const { progress, chunks, isComplete, error } = useProgressStream(jobId);

  if (!jobId) return null;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem' }}>
      <div style={{ ...styles.progressBar, flex: 1, marginBottom: 0 }}>
        <div 
          style={{ 
            ...styles.progressFill, 
            width: `${progress.percent}%`,
            background: error ? '#ef4444' : isComplete ? '#22c55e' : undefined,
          }} 
        />
      </div>
      <span style={{ color: '#64748b', minWidth: '3rem' }}>
        {progress.percent}%
      </span>
      {chunks.total > 0 && (
        <span style={{ color: '#94a3b8' }}>
          ({chunks.done}/{chunks.total})
        </span>
      )}
    </div>
  );
}

export default ProgressIndicator;
