/**
 * UploadContext.jsx - Background Upload Manager
 * 
 * Allows uploads to continue when navigating away.
 * Shows status indicator in header.
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import api from '../services/api';

const UploadContext = createContext(null);

export function useUpload() {
  const context = useContext(UploadContext);
  if (!context) {
    throw new Error('useUpload must be used within UploadProvider');
  }
  return context;
}

export function UploadProvider({ children }) {
  const [uploads, setUploads] = useState([]);

  const addUpload = useCallback((file, projectId, projectName, options = {}) => {
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    const uploadEntry = {
      id,
      filename: file.name,
      projectId,
      projectName,
      progress: 0,
      status: 'uploading',
      error: null,
      startedAt: new Date(),
    };

    setUploads(prev => [...prev, uploadEntry]);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('project', projectId);
    
    if (options.standards_mode) {
      formData.append('standards_mode', 'true');
      formData.append('domain', options.domain || 'general');
    }

    api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
      onUploadProgress: (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploads(prev => prev.map(u => 
          u.id === id ? { ...u, progress, status: progress < 100 ? 'uploading' : 'processing' } : u
        ));
      },
    })
    .then((response) => {
      setUploads(prev => prev.map(u => 
        u.id === id ? { ...u, status: 'completed', progress: 100, result: response.data } : u
      ));
      setTimeout(() => {
        setUploads(prev => prev.filter(u => u.id !== id));
      }, 10000);
    })
    .catch((error) => {
      setUploads(prev => prev.map(u => 
        u.id === id ? { 
          ...u, 
          status: 'failed', 
          error: error.response?.data?.detail || error.message || 'Upload failed' 
        } : u
      ));
    });

    return id;
  }, []);

  const removeUpload = useCallback((id) => {
    setUploads(prev => prev.filter(u => u.id !== id));
  }, []);

  const clearCompleted = useCallback(() => {
    setUploads(prev => prev.filter(u => u.status !== 'completed'));
  }, []);

  const activeCount = uploads.filter(u => u.status === 'uploading' || u.status === 'processing').length;
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
    if (status === 'completed') return '#10b981';
    if (status === 'failed') return '#ef4444';
    if (status === 'processing') return '#3b82f6';
    return '#f59e0b';
  };

  const getStatusIcon = (status) => {
    if (status === 'completed') return '✓';
    if (status === 'failed') return '✗';
    if (status === 'processing') return '⚙';
    return '↑';
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
            {activeCount} uploading
          </>
        ) : failedCount > 0 ? (
          <><span>⚠</span>{failedCount} failed</>
        ) : (
          <><span>✓</span>Done</>
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
          width: '320px',
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
              <button onClick={clearCompleted} style={{ background: 'none', border: 'none', color: '#5f6c7b', fontSize: '0.75rem', cursor: 'pointer' }}>
                Clear completed
              </button>
            )}
          </div>

          {uploads.map(upload => (
            <div key={upload.id} style={{ padding: '0.75rem 1rem', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ color: getStatusColor(upload.status), fontSize: '1rem' }}>{getStatusIcon(upload.status)}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500, fontSize: '0.85rem', color: '#2a3441', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {upload.filename}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#5f6c7b' }}>{upload.projectName || 'Unknown'}</div>
                {upload.status === 'uploading' && (
                  <div style={{ marginTop: '0.25rem', height: '3px', background: '#e2e8f0', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{ width: `${upload.progress}%`, height: '100%', background: '#f59e0b', transition: 'width 0.3s ease' }} />
                  </div>
                )}
                {upload.status === 'processing' && <div style={{ fontSize: '0.7rem', color: '#3b82f6', marginTop: '0.25rem' }}>Processing...</div>}
                {upload.error && <div style={{ fontSize: '0.7rem', color: '#ef4444', marginTop: '0.25rem' }}>{upload.error}</div>}
              </div>
              {(upload.status === 'completed' || upload.status === 'failed') && (
                <button onClick={() => removeUpload(upload.id)} style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', padding: '0.25rem' }}>✕</button>
              )}
            </div>
          ))}
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default UploadProvider;
