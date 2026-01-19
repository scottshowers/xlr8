/**
 * Upload Component - Document Upload
 * 
 * Uses ProjectContext for project selection (no local selector).
 * Parent page handles "no project" state.
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProject } from '../context/ProjectContext'
import api from '../services/api'

export default function Upload({ functionalAreas = [] }) {
  const navigate = useNavigate()
  const { activeProject } = useProject()
  
  const [files, setFiles] = useState([])
  const [selectedArea, setSelectedArea] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState([])
  const [error, setError] = useState(null)

  const defaultAreas = [
    'Payroll',
    'Time & Attendance', 
    'Benefits',
    'HR Core',
    'Recruiting',
    'Onboarding',
    'Performance',
    'Learning',
    'Compensation',
    'Other'
  ]

  const areas = functionalAreas.length > 0 ? functionalAreas : defaultAreas

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files)
    setFiles(prev => [...prev, ...selectedFiles])
    setError(null)
    setUploadProgress([])
  }

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one file to upload')
      return
    }

    if (!activeProject) {
      setError('Please select a project from the header')
      return
    }

    setUploading(true)
    setError(null)
    
    // Initialize progress for all files
    setUploadProgress(files.map(f => ({ 
      name: f.name, 
      status: 'pending', 
      message: 'Waiting...' 
    })))

    // Upload files sequentially
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      
      // Update status to uploading
      setUploadProgress(prev => prev.map((p, idx) => 
        idx === i ? { ...p, status: 'uploading', message: 'Uploading...' } : p
      ))

      try {
        const formData = new FormData()
        formData.append('file', file)
        // CRITICAL: Use customer ID (UUID) - this is the ONLY identifier for all operations
        formData.append('project', activeProject.id)
        if (selectedArea) {
          formData.append('functional_area', selectedArea)
        }

        const response = await api.post('/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000
        })

        const { job_id, message } = response.data

        // Update status to success
        setUploadProgress(prev => prev.map((p, idx) => 
          idx === i ? { 
            ...p, 
            status: 'success', 
            message: message || 'Queued for processing',
            job_id 
          } : p
        ))

      } catch (err) {
        console.error(`Upload error for ${file.name}:`, err)
        
        // Update status to error
        setUploadProgress(prev => prev.map((p, idx) => 
          idx === i ? { 
            ...p, 
            status: 'error', 
            message: err.response?.data?.detail || err.message || 'Upload failed'
          } : p
        ))
      }
    }

    setUploading(false)
    setFiles([])
    
    // Redirect to status page after brief delay
    setTimeout(() => {
      navigate('/data?tab=status')
    }, 2000)
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  }

  const styles = {
    container: {
      maxWidth: '800px',
      margin: '0 auto'
    },
    header: {
      marginBottom: '1.5rem'
    },
    title: {
      fontSize: '1.25rem',
      fontWeight: '700',
      color: '#2a3441',
      marginBottom: '0.25rem',
      fontFamily: "'Sora', sans-serif"
    },
    subtitle: {
      fontSize: '0.9rem',
      color: '#5f6c7b'
    },
    projectBadge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.5rem 1rem',
      background: '#f0fdf4',
      border: '1px solid #bbf7d0',
      borderRadius: '8px',
      marginBottom: '1rem',
    },
    projectName: {
      fontWeight: '600',
      color: '#166534',
    },
    label: {
      display: 'block',
      fontSize: '0.9rem',
      fontWeight: '600',
      color: '#2a3441',
      marginBottom: '0.5rem'
    },
    select: {
      width: '100%',
      padding: '0.75rem 1rem',
      fontSize: '1rem',
      border: '1px solid #e1e8ed',
      borderRadius: '8px',
      background: 'white',
      color: '#2a3441',
      outline: 'none',
      cursor: 'pointer',
      marginBottom: '1.5rem'
    },
    dropzone: {
      border: '2px dashed #d1d9e0',
      borderRadius: '12px',
      padding: '3rem 2rem',
      textAlign: 'center',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      background: '#fafbfc',
      marginBottom: '1.5rem'
    },
    dropzoneIcon: {
      fontSize: '3rem',
      marginBottom: '1rem'
    },
    dropzoneText: {
      fontSize: '1rem',
      color: '#2a3441',
      fontWeight: '500',
      marginBottom: '0.5rem'
    },
    dropzoneSubtext: {
      fontSize: '0.875rem',
      color: '#5f6c7b'
    },
    fileList: {
      marginBottom: '1.5rem'
    },
    fileItem: {
      display: 'flex',
      alignItems: 'center',
      padding: '0.75rem 1rem',
      background: '#f8fafc',
      borderRadius: '8px',
      marginBottom: '0.5rem',
      gap: '0.75rem'
    },
    fileIcon: {
      fontSize: '1.25rem'
    },
    fileName: {
      flex: 1,
      fontWeight: '500',
      color: '#2a3441',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    },
    fileSize: {
      color: '#5f6c7b',
      fontSize: '0.875rem'
    },
    removeBtn: {
      background: 'none',
      border: 'none',
      color: '#e53e3e',
      cursor: 'pointer',
      fontSize: '1.25rem',
      padding: '0.25rem',
      lineHeight: 1
    },
    button: {
      width: '100%',
      padding: '1rem',
      fontSize: '1rem',
      fontWeight: '600',
      color: 'white',
      background: 'linear-gradient(135deg, #83b16d 0%, #93abd9 100%)',
      border: 'none',
      borderRadius: '8px',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      marginBottom: '1rem'
    },
    buttonDisabled: {
      opacity: 0.5,
      cursor: 'not-allowed'
    },
    infoBox: {
      background: '#f0f7ed',
      borderRadius: '8px',
      padding: '1rem',
      marginBottom: '1rem'
    },
    infoText: {
      fontSize: '0.875rem',
      color: '#2a3441',
      lineHeight: '1.5',
      margin: 0
    },
    infoLabel: {
      fontWeight: '600'
    },
    errorBox: {
      background: '#fef2f2',
      borderRadius: '8px',
      padding: '1rem',
      marginBottom: '1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem'
    },
    errorIcon: {
      fontSize: '1.25rem'
    },
    errorText: {
      color: '#dc2626',
      fontSize: '0.9rem'
    },
    progressList: {
      marginBottom: '1rem'
    },
    progressItem: {
      display: 'flex',
      alignItems: 'center',
      padding: '0.75rem 1rem',
      borderRadius: '8px',
      marginBottom: '0.5rem',
      gap: '0.75rem'
    },
    progressPending: {
      background: '#f8fafc'
    },
    progressUploading: {
      background: '#eff6ff'
    },
    progressSuccess: {
      background: '#f0fdf4'
    },
    progressError: {
      background: '#fef2f2'
    },
    progressMessage: {
      fontSize: '0.875rem',
      color: '#5f6c7b'
    },
    formatsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))',
      gap: '0.75rem',
      marginTop: '1rem'
    },
    formatBadge: {
      background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.08))',
      borderRadius: '8px',
      padding: '0.75rem',
      textAlign: 'center'
    },
    formatExt: {
      color: '#83b16d',
      fontWeight: '700',
      fontFamily: 'monospace',
      fontSize: '0.9rem'
    },
    formatDesc: {
      color: '#5f6c7b',
      fontSize: '0.75rem',
      marginTop: '0.25rem'
    },
    fileCount: {
      background: 'linear-gradient(135deg, #83b16d 0%, #93abd9 100%)',
      color: 'white',
      borderRadius: '12px',
      padding: '0.25rem 0.75rem',
      fontSize: '0.8rem',
      fontWeight: '600'
    }
  }

  const isDisabled = uploading || files.length === 0 || !activeProject

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>Upload Documents</h2>
        <p style={styles.subtitle}>
          Files will be uploaded to the selected project and processed in the background.
        </p>
      </div>

      {/* Current Project Indicator */}
      {activeProject && (
        <div style={styles.projectBadge}>
          <span></span>
          <span style={styles.projectName}>{activeProject.name}</span>
          <span style={{ color: '#5f6c7b', fontSize: '0.85rem' }}>
            {activeProject.customer}
          </span>
        </div>
      )}

      {/* Functional Area */}
      <div>
        <label style={styles.label}>
          Functional Area
        </label>
        <select
          value={selectedArea}
          onChange={(e) => setSelectedArea(e.target.value)}
          style={styles.select}
        >
          <option value="">Select area (optional)...</option>
          {areas.map(area => (
            <option key={area} value={area}>{area}</option>
          ))}
        </select>
      </div>

      {/* File Drop Zone */}
      <div>
        <label style={styles.label}>
          Files
          {files.length > 0 && (
            <span style={{ ...styles.fileCount, marginLeft: '0.75rem' }}>
              {files.length} selected
            </span>
          )}
        </label>
        <div 
          style={styles.dropzone}
          onClick={() => document.getElementById('file-upload').click()}
        >
          <input
            type="file"
            onChange={handleFileChange}
            style={{ display: 'none' }}
            id="file-upload"
            accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md"
            multiple
          />
          <div style={styles.dropzoneIcon}>File</div>
          <p style={styles.dropzoneText}>
            Click to select files
          </p>
          <p style={styles.dropzoneSubtext}>
            Select multiple files at once • PDF, Word, Excel, CSV, or Text
          </p>
        </div>
      </div>

      {/* Selected Files List */}
      {files.length > 0 && !uploading && (
        <div style={styles.fileList}>
          {files.map((file, index) => (
            <div key={index} style={styles.fileItem}>
              <span style={styles.fileIcon}>File</span>
              <span style={styles.fileName}>{file.name}</span>
              <span style={styles.fileSize}>{formatFileSize(file.size)}</span>
              <button 
                style={styles.removeBtn}
                onClick={() => removeFile(index)}
                title="Remove file"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Upload Progress */}
      {uploadProgress.length > 0 && (
        <div style={styles.progressList}>
          {uploadProgress.map((item, index) => (
            <div 
              key={index} 
              style={{
                ...styles.progressItem,
                ...(item.status === 'pending' ? styles.progressPending : {}),
                ...(item.status === 'uploading' ? styles.progressUploading : {}),
                ...(item.status === 'success' ? styles.progressSuccess : {}),
                ...(item.status === 'error' ? styles.progressError : {})
              }}
            >
              <span style={styles.fileIcon}>
                {item.status === 'pending' && ''}
                {item.status === 'uploading' && '⬆️'}
                {item.status === 'success' && ''}
                {item.status === 'error' && ''}
              </span>
              <span style={styles.fileName}>{item.name}</span>
              <span style={styles.progressMessage}>{item.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={isDisabled}
        style={{
          ...styles.button,
          ...(isDisabled ? styles.buttonDisabled : {})
        }}
      >
        {uploading ? (
          <>Uploading {uploadProgress.filter(p => p.status === 'success').length}/{uploadProgress.length}...</>
        ) : (
          <>Upload {files.length > 1 ? `${files.length} Files` : 'File'}</>
        )}
      </button>

      {/* Info Box */}
      <div style={styles.infoBox}>
        <p style={styles.infoText}>
          <span style={styles.infoLabel}>How it works: </span>
          Files are uploaded sequentially and queued for background processing. 
          Check the Processing Status tab to monitor progress.
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div style={styles.errorBox}>
          <span style={styles.errorIcon}>!</span>
          <span style={styles.errorText}>{error}</span>
        </div>
      )}

      {/* Supported Formats */}
      <div style={styles.formatsGrid}>
        {[
          { ext: '.PDF', desc: 'Documents' },
          { ext: '.DOCX', desc: 'Word files' },
          { ext: '.XLSX', desc: 'Excel files' },
          { ext: '.CSV', desc: 'Data files' },
          { ext: '.TXT', desc: 'Text files' },
          { ext: '.MD', desc: 'Markdown' },
        ].map(format => (
          <div key={format.ext} style={styles.formatBadge}>
            <div style={styles.formatExt}>{format.ext}</div>
            <div style={styles.formatDesc}>{format.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
