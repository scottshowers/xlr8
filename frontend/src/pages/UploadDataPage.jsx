/**
 * UploadDataPage.jsx - Step 2: Upload Data
 * 
 * Second step in the 8-step consultant workflow.
 * Drag-and-drop file upload with progress tracking.
 * 
 * Flow: Create Project → [UPLOAD DATA] → Select Playbooks → Analysis → ...
 * 
 * Updated: January 15, 2026 - Phase 4A UX Overhaul (proper rebuild)
 */

import React, { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import MainLayout from '../components/MainLayout';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { useProject } from '../context/ProjectContext';
import './UploadDataPage.css';

const API_BASE = import.meta.env.VITE_API_URL || '';

// File type configuration
const FILE_TYPES = {
  xlsx: { label: 'XLS', color: 'info', icon: '📊' },
  xls: { label: 'XLS', color: 'info', icon: '📊' },
  csv: { label: 'CSV', color: 'success', icon: '📄' },
  pdf: { label: 'PDF', color: 'warning', icon: '📑' },
  default: { label: 'FILE', color: 'neutral', icon: '📁' },
};

const UploadDataPage = () => {
  const navigate = useNavigate();
  const { activeProject, customerName } = useProject();
  const fileInputRef = useRef(null);

  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  // Get file type config
  const getFileTypeConfig = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    return FILE_TYPES[ext] || FILE_TYPES.default;
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
    const droppedFiles = Array.from(e.dataTransfer.files);
    addFiles(droppedFiles);
  }, []);

  // File selection
  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    addFiles(selectedFiles);
  };

  const addFiles = (newFiles) => {
    const fileObjects = newFiles.map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      name: file.name,
      size: file.size,
      typeConfig: getFileTypeConfig(file.name),
      status: 'queued', // queued, uploading, uploaded, error
      progress: 0,
      rows: null,
      error: null,
    }));
    setFiles((prev) => [...prev, ...fileObjects]);
    setError(null);
  };

  const removeFile = (id) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  // Upload simulation (replace with real API call)
  const uploadFile = async (fileObj) => {
    return new Promise((resolve, reject) => {
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 30 + 10;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          // Simulate row count
          const rows = Math.floor(Math.random() * 50000) + 1000;
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileObj.id
                ? { ...f, status: 'uploaded', progress: 100, rows }
                : f
            )
          );
          resolve();
        } else {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileObj.id
                ? { ...f, status: 'uploading', progress: Math.min(progress, 99) }
                : f
            )
          );
        }
      }, 200);
    });
  };

  const uploadAllFiles = async () => {
    const queuedFiles = files.filter((f) => f.status === 'queued');
    for (const fileObj of queuedFiles) {
      try {
        await uploadFile(fileObj);
      } catch (err) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileObj.id
              ? { ...f, status: 'error', error: err.message }
              : f
          )
        );
      }
    }
  };

  // Start analysis
  const handleStartAnalysis = async () => {
    if (files.length === 0) {
      setError('Please upload at least one file');
      return;
    }

    setError(null);
    setUploading(true);

    // Upload any queued files first
    await uploadAllFiles();

    // Navigate to playbook selection (Step 3)
    setTimeout(() => {
      navigate('/playbooks/select');
    }, 500);
  };

  // Stats
  const totalFiles = files.length;
  const uploadedFiles = files.filter((f) => f.status === 'uploaded').length;
  const totalRows = files.reduce((sum, f) => sum + (f.rows || 0), 0);
  const allUploaded = totalFiles > 0 && uploadedFiles === totalFiles;

  // Format file size
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <MainLayout showFlowBar={true} currentStep={2}>
      <div className="upload-data">
        <PageHeader
          title={customerName || activeProject?.customer || 'Upload Data'}
          subtitle={`Step 2 of 8 • ${activeProject?.system_type || 'UKG Pro'} · ${activeProject?.engagement_type || 'Implementation'}`}
        />

        <div className="upload-data__content">
          {/* Main Upload Card */}
          <Card className="upload-data__main-card">
            <CardHeader>
              <CardTitle icon="📤">Upload Client Data</CardTitle>
              {totalFiles > 0 && (
                <Badge variant="info">
                  {uploadedFiles}/{totalFiles} files
                </Badge>
              )}
            </CardHeader>

            {/* Drop Zone */}
            <div
              className={`upload-data__dropzone ${isDragging ? 'upload-data__dropzone--active' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="dropzone-icon">↑</div>
              <h3 className="dropzone-title">Drop files here or click to browse</h3>
              <p className="dropzone-hint">Excel, CSV, PDF — we'll figure out what's what</p>
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
              <div className="upload-data__files">
                {files.map((fileObj) => (
                  <div key={fileObj.id} className={`file-row file-row--${fileObj.status}`}>
                    {/* File Type Badge */}
                    <div className={`file-type-badge file-type-badge--${fileObj.typeConfig.color}`}>
                      {fileObj.typeConfig.label}
                    </div>

                    {/* File Info */}
                    <div className="file-info">
                      <div className="file-name">{fileObj.name}</div>
                      <div className="file-meta">
                        {fileObj.status === 'uploaded' && fileObj.rows && (
                          <span>{fileObj.rows.toLocaleString()} rows</span>
                        )}
                        {fileObj.status === 'uploading' && (
                          <span>Uploading... {Math.round(fileObj.progress)}%</span>
                        )}
                        {fileObj.status === 'queued' && (
                          <span>Queued • {formatSize(fileObj.size)}</span>
                        )}
                        {fileObj.status === 'error' && (
                          <span className="file-error">{fileObj.error || 'Upload failed'}</span>
                        )}
                      </div>
                      {/* Progress Bar */}
                      <div className="file-progress">
                        <div 
                          className="file-progress-bar" 
                          style={{ width: `${fileObj.progress}%` }} 
                        />
                      </div>
                    </div>

                    {/* Status / Actions */}
                    <div className="file-actions">
                      {fileObj.status === 'uploaded' && (
                        <span className="file-status file-status--success">✓</span>
                      )}
                      {fileObj.status === 'error' && (
                        <span className="file-status file-status--error">✗</span>
                      )}
                      {(fileObj.status === 'queued' || fileObj.status === 'error') && (
                        <button 
                          className="file-remove"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeFile(fileObj.id);
                          }}
                        >
                          ×
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="upload-data__error">
                <span className="error-icon">⚠️</span>
                {error}
              </div>
            )}

            {/* Actions */}
            <div className="upload-data__actions">
              <Button
                variant="primary"
                onClick={handleStartAnalysis}
                disabled={files.length === 0 || uploading}
              >
                {uploading ? 'Uploading...' : allUploaded ? 'Continue to Playbooks →' : 'Upload & Continue →'}
              </Button>
              <Button
                variant="secondary"
                onClick={() => fileInputRef.current?.click()}
              >
                Add More Files
              </Button>
            </div>
          </Card>

          {/* Sidebar */}
          <div className="upload-data__sidebar">
            {/* Stats Card */}
            {files.length > 0 && (
              <Card className="upload-data__stats-card">
                <CardHeader>
                  <CardTitle icon="📊">Upload Summary</CardTitle>
                </CardHeader>
                <div className="stats-grid">
                  <div className="stat-item">
                    <div className="stat-value">{totalFiles}</div>
                    <div className="stat-label">Files</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value">{uploadedFiles}</div>
                    <div className="stat-label">Uploaded</div>
                  </div>
                  <div className="stat-item stat-item--wide">
                    <div className="stat-value">{totalRows.toLocaleString()}</div>
                    <div className="stat-label">Total Rows</div>
                  </div>
                </div>
              </Card>
            )}

            {/* Help Card */}
            <Card className="upload-data__help-card">
              <CardHeader>
                <CardTitle icon="💡">Supported Formats</CardTitle>
              </CardHeader>
              <ul className="format-list">
                <li>
                  <Badge variant="info" size="sm">XLS</Badge>
                  <span>Excel spreadsheets (.xlsx, .xls)</span>
                </li>
                <li>
                  <Badge variant="success" size="sm">CSV</Badge>
                  <span>Comma-separated values</span>
                </li>
                <li>
                  <Badge variant="warning" size="sm">PDF</Badge>
                  <span>Configuration exports, reports</span>
                </li>
              </ul>
              <p className="help-note">
                No special formatting required. Just export from your system and drop here.
              </p>
            </Card>

            {/* Next Step Preview */}
            <Card className="upload-data__next-card">
              <div className="next-step-preview">
                <div className="next-step-label">Next Step</div>
                <div className="next-step-title">📋 Select Playbooks</div>
                <div className="next-step-description">
                  Choose which analysis playbooks to run against your data.
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default UploadDataPage;
