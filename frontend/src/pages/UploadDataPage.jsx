/**
 * UploadDataPage.jsx - Mockup Screen 2
 * =====================================
 *
 * EXACT match to mockup "Upload Data" screen.
 * Simple, clean upload experience with:
 * - Drag-and-drop zone
 * - File progress tracking
 * - Start Analysis button
 *
 * Created: January 15, 2026 - Phase 4A UX Redesign
 */

import React, { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import StepIndicator from '../components/StepIndicator';

const API_BASE = import.meta.env.VITE_API_URL || '';

// File type colors
const FILE_COLORS = {
  xlsx: '#285390',
  xls: '#285390',
  csv: '#83b16d',
  pdf: '#5f4282',
};

export default function UploadDataPage() {
  const navigate = useNavigate();
  const { activeProject, customerName } = useProject();
  const { darkMode } = useTheme();
  const fileInputRef = useRef(null);

  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  // Colors based on theme
  const colors = {
    bg: darkMode ? '#1a1f2e' : '#f6f5fa',
    card: darkMode ? '#242b3d' : '#ffffff',
    border: darkMode ? '#2d3548' : '#e1e8ed',
    text: darkMode ? '#e8eaed' : '#2a3441',
    textMuted: darkMode ? '#8b95a5' : '#5f6c7b',
    primary: '#83b16d',
    primaryHover: '#6b9b5a',
    tertiary: darkMode ? '#1e2433' : '#f0f4f7',
  };

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
      type: getFileType(file.name),
      status: 'queued', // queued, uploading, uploaded, error
      progress: 0,
      rows: null,
    }));
    setFiles((prev) => [...prev, ...fileObjects]);
  };

  const getFileType = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    if (['xlsx', 'xls'].includes(ext)) return 'XLS';
    if (ext === 'csv') return 'CSV';
    if (ext === 'pdf') return 'PDF';
    return ext.toUpperCase();
  };

  const getFileColor = (type) => {
    const t = type.toLowerCase();
    return FILE_COLORS[t] || '#285390';
  };

  const simulateUpload = async (fileObj) => {
    return new Promise((resolve) => {
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
      }, 300);
    });
  };

  const uploadAllFiles = async () => {
    const queuedFiles = files.filter((f) => f.status === 'queued');
    for (const fileObj of queuedFiles) {
      await simulateUpload(fileObj);
    }
  };

  const handleStartAnalysis = async () => {
    if (files.length === 0) {
      setError('Please upload at least one file');
      return;
    }

    setError(null);
    setUploading(true);

    // Upload any queued files first
    await uploadAllFiles();

    // Navigate to processing page
    setTimeout(() => {
      navigate('/processing');
    }, 500);
  };

  const handleAddMoreFiles = () => {
    fileInputRef.current?.click();
  };

  const allUploaded = files.length > 0 && files.every((f) => f.status === 'uploaded');
  const hasQueuedFiles = files.some((f) => f.status === 'queued');

  return (
    <>
      <StepIndicator currentStep={2} />
      <div style={{ padding: 32, maxWidth: 1400, margin: '0 auto' }}>
        {/* Page Header */}
        <div className="xlr8-page-header">
          <h1>{customerName || activeProject?.customer || activeProject?.name || 'New Project'}</h1>
        <p className="subtitle">
          {activeProject?.system_type || 'UKG Pro'} · {activeProject?.engagement_type || 'Implementation'} · Go-Live: {activeProject?.target_go_live || 'TBD'}
        </p>
      </div>

      {/* Upload Card */}
      <div className="xlr8-card" style={{ maxWidth: 800 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          marginBottom: 24,
        }}>
          <div style={{
            width: 32,
            height: 32,
            background: 'rgba(131, 177, 109, 0.12)',
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
          }}>
            📤
          </div>
          <h2 style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: 16,
            fontWeight: 700,
            color: colors.text,
            margin: 0,
          }}>
            Upload Client Data
          </h2>
        </div>

        {/* Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${isDragging ? colors.primary : colors.border}`,
            borderRadius: 12,
            padding: 48,
            textAlign: 'center',
            background: isDragging ? 'rgba(131, 177, 109, 0.05)' : colors.tertiary,
            cursor: 'pointer',
            transition: 'all 0.3s',
          }}
        >
          <div style={{
            width: 64,
            height: 64,
            background: colors.primary,
            borderRadius: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
            color: 'white',
            fontSize: 24,
          }}>
            ↑
          </div>
          <h3 style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: 18,
            color: colors.text,
            marginBottom: 8,
          }}>
            Drop files here or click to browse
          </h3>
          <p style={{
            color: colors.textMuted,
            fontSize: 14,
            margin: 0,
          }}>
            Excel, CSV, PDF — we'll figure out what's what
          </p>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".xlsx,.xls,.csv,.pdf"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </div>

        {/* File Progress List */}
        {files.length > 0 && (
          <div style={{ marginTop: 24 }}>
            {files.map((fileObj) => (
              <div
                key={fileObj.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  padding: 16,
                  background: colors.tertiary,
                  borderRadius: 8,
                  marginBottom: 12,
                }}
              >
                {/* File Type Icon */}
                <div style={{
                  width: 40,
                  height: 40,
                  background: getFileColor(fileObj.type),
                  borderRadius: 8,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontSize: 12,
                  fontWeight: 700,
                }}>
                  {fileObj.type}
                </div>

                {/* File Info */}
                <div style={{ flex: 1 }}>
                  <div style={{
                    fontWeight: 600,
                    color: colors.text,
                    fontSize: 14,
                  }}>
                    {fileObj.name}
                  </div>
                  <div style={{
                    fontSize: 12,
                    color: colors.textMuted,
                  }}>
                    {fileObj.status === 'uploaded'
                      ? `${fileObj.rows?.toLocaleString() || 0} rows · Uploaded`
                      : fileObj.status === 'uploading'
                        ? `Uploading... ${Math.round(fileObj.progress)}%`
                        : 'Queued'}
                  </div>
                  {/* Progress Bar */}
                  <div style={{
                    height: 6,
                    background: colors.border,
                    borderRadius: 3,
                    marginTop: 8,
                    overflow: 'hidden',
                  }}>
                    <div style={{
                      height: '100%',
                      background: colors.primary,
                      borderRadius: 3,
                      width: `${fileObj.progress}%`,
                      transition: 'width 0.3s',
                    }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{
            padding: '12px 16px',
            background: 'rgba(153, 60, 68, 0.1)',
            border: '1px solid rgba(153, 60, 68, 0.3)',
            borderRadius: 8,
            color: '#993c44',
            fontSize: 14,
            marginTop: 20,
          }}>
            {error}
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
          <button
            onClick={handleStartAnalysis}
            className="xlr8-btn xlr8-btn-primary"
            disabled={files.length === 0 || uploading}
          >
            {uploading ? 'Uploading...' : 'Start Analysis →'}
          </button>
          <button
            onClick={handleAddMoreFiles}
            className="xlr8-btn xlr8-btn-secondary"
          >
            Add More Files
          </button>
        </div>
      </div>
    </div>
    </>
  );
}
