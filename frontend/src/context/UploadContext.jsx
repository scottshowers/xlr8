/**
 * UploadContext.jsx - Background Upload Manager with Job Polling
 * ==============================================================
 * 
 * v2.0 - December 2025
 * 
 * FIXES:
 * - Polls job status for async processing (register extractor, smart_pdf)
 * - Shows real-time processing stages
 * - Files remain visible until processing completes
 * - Displays actual metrics when done (rows, tables, chunks)
 * 
 * CANONICAL JOB STATUS FORMAT:
 * - job_id: string
 * - status: 'uploading' | 'processing' | 'completed' | 'failed'
 * - progress: 0-100
 * - message: current stage description
 * - result: final result object when completed
 * 
 * Five Truths Support:
 * - reality → DuckDB
 * - intent → ChromaDB (project-scoped)
 * - configuration → DuckDB + ChromaDB
 * - reference/regulatory/compliance → ChromaDB (global)
 */

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import api from '../services/api';

const UploadContext = createContext(null);

export function useUpload() {
  const context = useContext(UploadContext);
  if (!context) {
    throw new Error('useUpload must be used within UploadProvider');
  }
  return context;
}

// Processing stage messages for display
const STAGE_MESSAGES = {
  uploading: 'Uploading file...',
  queued: 'Queued for processing...',
  extracting: 'Extracting content...',
  analyzing: 'Analyzing structure...',
  storing: 'Storing to database...',
  profiling: 'Profiling columns...',
  indexing: 'Building search index...',
  completed: 'Complete',
  failed: 'Failed',
};

export function UploadProvider({ children }) {
  const [uploads, setUploads] = useState([]);
  const pollIntervals = useRef({});

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      Object.values(pollIntervals.current).forEach(clearInterval);
    };
  }, []);

  // Poll job status for async jobs
  const pollJobStatus = useCallback((uploadId, jobId) => {
    // Clear any existing poll for this upload
    if (pollIntervals.current[uploadId]) {
      clearInterval(pollIntervals.current[uploadId]);
    }

    const poll = async () => {
      try {
        const res = await api.get(`/jobs/${jobId}`);
        const job = res.data;

        setUploads(prev => prev.map(u => {
          if (u.id !== uploadId) return u;

          // Map actual API response to our format
          // API returns: { status, progress: {step, percent}, result_data, error_message }
          let displayStatus = job.status || 'processing';
          let displayProgress = job.progress?.percent || u.progress || 50;
          let displayMessage = job.progress?.step || STAGE_MESSAGES[displayStatus] || 'Processing...';

          // Handle completion
          if (job.status === 'completed') {
            displayStatus = 'completed';
            const result = job.result_data || {};
            const rowCount = result.total_rows || result.row_count || result.employees_found || 0;
            const chunks = result.chunks_created || 0;
            if (rowCount > 0) {
              displayMessage = `Done: ${rowCount.toLocaleString()} rows`;
            } else if (chunks > 0) {
              displayMessage = `Done: ${chunks} chunks`;
            } else {
              displayMessage = 'Complete';
            }
          } else if (job.status === 'failed' || job.status === 'error') {
            displayStatus = 'failed';
            displayMessage = job.error_message || job.error || 'Processing failed';
          }

          return {
            ...u,
            status: displayStatus,
            progress: displayProgress,
            message: displayMessage,
            result: job.result_data,
          };
        }));

        // Stop polling if done
        if (job.status === 'completed' || job.status === 'failed' || job.status === 'error') {
          clearInterval(pollIntervals.current[uploadId]);
          delete pollIntervals.current[uploadId];

          // Auto-remove completed uploads after delay
          if (job.status === 'completed') {
            setTimeout(() => {
              setUploads(prev => prev.filter(u => u.id !== uploadId));
            }, 15000);
          }
        }
      } catch (err) {
        // Job endpoint might not exist for non-async uploads - that's okay
        console.debug('Job poll error (may be normal):', err.message);
      }
    };

    // Poll immediately, then every 2 seconds
    poll();
    pollIntervals.current[uploadId] = setInterval(poll, 2000);
  }, []);

  const addUpload = useCallback((file, project, projectName, options = {}) => {
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    const projName = projectName || project?.name || 'Unknown';
    const projId = project?.id || null;
    
    const uploadEntry = {
      id,
      filename: file.name,
      projectId: projId,
      projectName: projName,
      progress: 0,
      status: 'uploading',
      message: STAGE_MESSAGES.uploading,
      error: null,
      startedAt: new Date(),
      result: null,
    };

    setUploads(prev => [...prev, uploadEntry]);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('project', projName);
    if (projId) {
      formData.append('project_id', projId);
    }
    
    if (options.standards_mode) {
      formData.append('standards_mode', 'true');
      formData.append('domain', options.domain || 'general');
    }
    
    if (options.truth_type) {
      formData.append('truth_type', options.truth_type);
    }

    api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
      onUploadProgress: (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploads(prev => prev.map(u => 
          u.id === id ? { 
            ...u, 
            progress: Math.min(progress, 50), // Cap at 50% for upload phase
            status: progress < 100 ? 'uploading' : 'processing',
            message: progress < 100 ? STAGE_MESSAGES.uploading : STAGE_MESSAGES.queued,
          } : u
        ));
      },
    })
    .then((response) => {
      const data = response.data;
      
      // Check if this is an async job that needs polling
      if (data.job_id) {
        setUploads(prev => prev.map(u => 
          u.id === id ? { 
            ...u, 
            status: 'processing', 
            progress: 50,
            message: data.message || STAGE_MESSAGES.extracting,
            jobId: data.job_id,
          } : u
        ));
        // Start polling for job status
        pollJobStatus(id, data.job_id);
      } else {
        // Synchronous completion
        const rowCount = data.row_count || data.total_rows || data.rows || 0;
        const tableCount = data.tables_created?.length || data.table_count || 1;
        
        setUploads(prev => prev.map(u => 
          u.id === id ? { 
            ...u, 
            status: 'completed', 
            progress: 100,
            message: `Done: ${rowCount.toLocaleString()} rows in ${tableCount} table(s)`,
            result: data,
          } : u
        ));
        
        // Auto-remove after delay
        setTimeout(() => {
          setUploads(prev => prev.filter(u => u.id !== id));
        }, 10000);
      }
    })
    .catch((error) => {
      setUploads(prev => prev.map(u => 
        u.id === id ? { 
          ...u, 
          status: 'failed',
          message: error.response?.data?.detail || error.message || 'Upload failed',
          error: error.response?.data?.detail || error.message || 'Upload failed',
        } : u
      ));
    });

    return id;
  }, [pollJobStatus]);

  const removeUpload = useCallback((id) => {
    // Stop any polling for this upload
    if (pollIntervals.current[id]) {
      clearInterval(pollIntervals.current[id]);
      delete pollIntervals.current[id];
    }
    setUploads(prev => prev.filter(u => u.id !== id));
  }, []);

  const clearCompleted = useCallback(() => {
    setUploads(prev => prev.filter(u => u.status !== 'completed'));
  }, []);

  const clearAll = useCallback(() => {
    // Stop ALL polling
    Object.keys(pollIntervals.current).forEach(id => {
      clearInterval(pollIntervals.current[id]);
      delete pollIntervals.current[id];
    });
    setUploads([]);
  }, []);

  const activeCount = uploads.filter(u => 
    u.status === 'uploading' || u.status === 'processing'
  ).length;
  const hasActive = activeCount > 0;
  const failedCount = uploads.filter(u => u.status === 'failed').length;

  return (
    <UploadContext.Provider value={{
      uploads,
      addUpload,
      removeUpload,
      clearCompleted,
      activeCount,
      hasActive,
      failedCount,
    }}>
      {children}
    </UploadContext.Provider>
  );
}

/**
 * UploadStatusIndicator - Shows in header when uploads are active
 */
export function UploadStatusIndicator() {
  const { uploads, hasActive, activeCount, failedCount, removeUpload, clearCompleted } = useUpload();
  const [expanded, setExpanded] = useState(false);

  if (uploads.length === 0) return null;

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'failed': return '#ef4444';
      case 'processing': return '#3b82f6';
      default: return '#f59e0b';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return '✓';
      case 'failed': return '✗';
      case 'processing': return '⚙';
      default: return '↑';
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 0.75rem',
          background: hasActive ? '#f59e0b20' : (failedCount > 0 ? '#ef444420' : '#10b98120'),
          border: `1px solid ${hasActive ? '#f59e0b40' : (failedCount > 0 ? '#ef444440' : '#10b98140')}`,
          borderRadius: '8px',
          cursor: 'pointer',
          color: hasActive ? '#f59e0b' : (failedCount > 0 ? '#ef4444' : '#10b981'),
          fontSize: '0.85rem',
          fontWeight: 600,
        }}
      >
        {hasActive ? (
          <>
            <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>↻</span>
            {activeCount} processing
          </>
        ) : failedCount > 0 ? (
          <><span>⚠</span> {failedCount} failed</>
        ) : (
          <><span>✓</span> Done</>
        )}
      </button>

      {expanded && (
        <div style={{
          position: 'absolute',
          top: '100%',
          right: 0,
          marginTop: '0.5rem',
          background: 'white',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          width: '360px',
          maxHeight: '400px',
          overflow: 'auto',
          zIndex: 1000,
        }}>
          <div style={{ 
            padding: '0.75rem 1rem', 
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span style={{ fontWeight: 600, color: '#2a3441' }}>Uploads</span>
            {uploads.some(u => u.status === 'completed') && (
              <button 
                onClick={clearCompleted} 
                style={{ 
                  background: 'none', 
                  border: 'none', 
                  color: '#5f6c7b', 
                  fontSize: '0.75rem', 
                  cursor: 'pointer' 
                }}
              >
                Clear completed
              </button>
            )}
          </div>

          {uploads.map(upload => (
            <div 
              key={upload.id} 
              style={{ 
                padding: '0.75rem 1rem', 
                borderBottom: '1px solid #f0f0f0', 
                display: 'flex', 
                alignItems: 'flex-start', 
                gap: '0.75rem' 
              }}
            >
              <span style={{ 
                color: getStatusColor(upload.status), 
                fontSize: '1rem',
                marginTop: '2px',
              }}>
                {getStatusIcon(upload.status)}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ 
                  fontWeight: 500, 
                  fontSize: '0.85rem', 
                  color: '#2a3441', 
                  overflow: 'hidden', 
                  textOverflow: 'ellipsis', 
                  whiteSpace: 'nowrap' 
                }}>
                  {upload.filename}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#5f6c7b' }}>
                  {upload.projectName}
                </div>
                
                {/* Progress bar for active uploads */}
                {(upload.status === 'uploading' || upload.status === 'processing') && (
                  <div style={{ marginTop: '0.35rem' }}>
                    <div style={{ 
                      height: '4px', 
                      background: '#e2e8f0', 
                      borderRadius: '2px', 
                      overflow: 'hidden' 
                    }}>
                      <div style={{ 
                        width: `${upload.progress}%`, 
                        height: '100%', 
                        background: upload.status === 'processing' ? '#3b82f6' : '#f59e0b', 
                        transition: 'width 0.3s ease' 
                      }} />
                    </div>
                    <div style={{ 
                      fontSize: '0.7rem', 
                      color: upload.status === 'processing' ? '#3b82f6' : '#f59e0b', 
                      marginTop: '0.25rem' 
                    }}>
                      {upload.message || 'Processing...'}
                    </div>
                  </div>
                )}
                
                {/* Success message */}
                {upload.status === 'completed' && (
                  <div style={{ 
                    fontSize: '0.7rem', 
                    color: '#10b981', 
                    marginTop: '0.25rem' 
                  }}>
                    {upload.message}
                  </div>
                )}
                
                {/* Error message */}
                {upload.status === 'failed' && (
                  <div style={{ 
                    fontSize: '0.7rem', 
                    color: '#ef4444', 
                    marginTop: '0.25rem' 
                  }}>
                    {upload.error || upload.message}
                  </div>
                )}
              </div>
              
              {(upload.status === 'completed' || upload.status === 'failed') && (
                <button 
                  onClick={() => removeUpload(upload.id)} 
                  style={{ 
                    background: 'none', 
                    border: 'none', 
                    color: '#9ca3af', 
                    cursor: 'pointer', 
                    padding: '0.25rem',
                    fontSize: '1rem',
                  }}
                >
                  ✕
                </button>
              )}
            </div>
          ))}
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

export default UploadProvider;
