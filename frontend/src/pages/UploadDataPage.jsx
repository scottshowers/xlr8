/**
 * UploadDataPage.jsx - Step 2: Upload Data
 * 
 * Drag-and-drop file upload with progress tracking.
 * Uses design system classes - NO emojis.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileSpreadsheet, FileText, File, X, Check, AlertCircle, ChevronRight } from 'lucide-react';
import { useProject } from '../context/ProjectContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

const UploadDataPage = () => {
  const navigate = useNavigate();
  const { activeProject, customerName } = useProject();
  const fileInputRef = useRef(null);

  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  // Get file type config
  const getFileType = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    if (['xlsx', 'xls'].includes(ext)) return { label: 'XLS', variant: 'info', Icon: FileSpreadsheet };
    if (ext === 'csv') return { label: 'CSV', variant: 'success', Icon: FileText };
    if (ext === 'pdf') return { label: 'PDF', variant: 'warning', Icon: FileText };
    return { label: 'FILE', variant: 'info', Icon: File };
  };

  // Drag handlers
  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    addFiles(Array.from(e.dataTransfer.files));
  }, []);

  const handleFileSelect = (e) => {
    addFiles(Array.from(e.target.files));
  };

  const addFiles = (newFiles) => {
    const fileObjects = newFiles.map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      name: file.name,
      size: file.size,
      type: getFileType(file.name),
      status: 'queued',
      progress: 0,
      rows: null,
    }));
    setFiles((prev) => [...prev, ...fileObjects]);
    setError(null);
  };

  const removeFile = (id) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  // Upload simulation
  const uploadFile = async (fileObj) => {
    return new Promise((resolve) => {
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 30 + 10;
        if (progress >= 100) {
          clearInterval(interval);
          const rows = Math.floor(Math.random() * 50000) + 1000;
          setFiles((prev) =>
            prev.map((f) => f.id === fileObj.id ? { ...f, status: 'uploaded', progress: 100, rows } : f)
          );
          resolve();
        } else {
          setFiles((prev) =>
            prev.map((f) => f.id === fileObj.id ? { ...f, status: 'uploading', progress: Math.min(progress, 99) } : f)
          );
        }
      }, 200);
    });
  };

  const uploadAllFiles = async () => {
    for (const fileObj of files.filter((f) => f.status === 'queued')) {
      await uploadFile(fileObj);
    }
  };

  const handleContinue = async () => {
    if (files.length === 0) {
      setError('Please upload at least one file');
      return;
    }
    setUploading(true);
    await uploadAllFiles();
    setTimeout(() => navigate('/playbooks/select'), 500);
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const totalFiles = files.length;
  const uploadedFiles = files.filter((f) => f.status === 'uploaded').length;
  const totalRows = files.reduce((sum, f) => sum + (f.rows || 0), 0);
  const allUploaded = totalFiles > 0 && uploadedFiles === totalFiles;

  return (
    <div className="upload-page">
      <div className="page-header">
        <h1 className="page-title">Upload Data</h1>
        <p className="page-subtitle">
          {customerName || activeProject?.customer || 'Project'} - {activeProject?.system_type || 'UKG Pro'}
        </p>
      </div>

      <div className="hub-grid">
        {/* Main Upload Area */}
        <div className="hub-main">
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Upload Client Data</h3>
              {totalFiles > 0 && (
                <span className="badge badge--info">{uploadedFiles}/{totalFiles} files</span>
              )}
            </div>
            <div className="card-body">
              {/* Drop Zone */}
              <div
                className={`dropzone ${isDragging ? 'dropzone--active' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={32} style={{ color: 'var(--grass-green)', marginBottom: 'var(--space-3)' }} />
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 'var(--weight-semibold)', marginBottom: 'var(--space-1)' }}>
                  Drop files here or click to browse
                </div>
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
                  Excel, CSV, PDF - we'll figure out what's what
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".xlsx,.xls,.csv,.pdf"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />
              </div>

              {/* File List */}
              {files.length > 0 && (
                <div className="file-list mt-4">
                  {files.map((fileObj) => {
                    const { Icon } = fileObj.type;
                    return (
                      <div key={fileObj.id} className="file-item">
                        <div className="flex items-center gap-3" style={{ flex: 1 }}>
                          <span className={`badge badge--${fileObj.type.variant}`}>{fileObj.type.label}</span>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 'var(--weight-medium)' }}>{fileObj.name}</div>
                            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
                              {fileObj.status === 'uploaded' && `${fileObj.rows?.toLocaleString()} rows`}
                              {fileObj.status === 'uploading' && `Uploading... ${Math.round(fileObj.progress)}%`}
                              {fileObj.status === 'queued' && `${formatSize(fileObj.size)}`}
                            </div>
                            {fileObj.status === 'uploading' && (
                              <div className="progress-bar mt-2" style={{ height: '4px' }}>
                                <div className="progress-bar__fill" style={{ width: `${fileObj.progress}%` }} />
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {fileObj.status === 'uploaded' && <Check size={18} style={{ color: 'var(--success)' }} />}
                          {fileObj.status === 'queued' && (
                            <button className="btn-icon" onClick={() => removeFile(fileObj.id)}>
                              <X size={16} />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="alert alert--error mt-4">
                  <AlertCircle size={16} />
                  {error}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-4 mt-6">
                <button
                  className="btn btn-primary btn-lg"
                  onClick={handleContinue}
                  disabled={files.length === 0 || uploading}
                >
                  {uploading ? 'Uploading...' : allUploaded ? 'Continue to Playbooks' : 'Upload & Continue'}
                  <ChevronRight size={18} />
                </button>
                <button className="btn btn-secondary" onClick={() => fileInputRef.current?.click()}>
                  Add More Files
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="hub-sidebar">
          {/* Stats */}
          {files.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Upload Summary</h3>
              </div>
              <div className="card-body">
                <div className="flex gap-6">
                  <div className="finding-stat">
                    <div className="finding-stat__value">{totalFiles}</div>
                    <div className="finding-stat__label">Files</div>
                  </div>
                  <div className="finding-stat">
                    <div className="finding-stat__value finding-stat__value--info">{uploadedFiles}</div>
                    <div className="finding-stat__label">Uploaded</div>
                  </div>
                  <div className="finding-stat">
                    <div className="finding-stat__value">{totalRows.toLocaleString()}</div>
                    <div className="finding-stat__label">Rows</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Supported Formats */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Supported Formats</h3>
            </div>
            <div className="card-body">
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <span className="badge badge--info">XLS</span>
                  <span style={{ fontSize: 'var(--text-sm)' }}>Excel spreadsheets</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="badge badge--success">CSV</span>
                  <span style={{ fontSize: 'var(--text-sm)' }}>Comma-separated values</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="badge badge--warning">PDF</span>
                  <span style={{ fontSize: 'var(--text-sm)' }}>Configuration exports</span>
                </div>
              </div>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginTop: 'var(--space-4)' }}>
                No special formatting required. Just export and drop.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadDataPage;
