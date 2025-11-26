import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

export default function Upload({ projects = [], functionalAreas = [], onProjectCreated }) {
  const navigate = useNavigate()
  const [files, setFiles] = useState([])
  const [selectedArea, setSelectedArea] = useState('')
  const [selectedProject, setSelectedProject] = useState('')
  const [projectList, setProjectList] = useState(projects)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState([]) // Track each file's status
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

  useEffect(() => {
    if (projects.length > 0) {
      setProjectList(projects)
    } else {
      loadProjects()
    }
  }, [projects])

  const loadProjects = async () => {
    try {
      const response = await api.get('/projects/list')
      setProjectList(response.data || [])
    } catch (err) {
      console.error('Failed to load projects:', err)
    }
  }

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

    if (!selectedProject) {
      setError('Please select a project')
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
        formData.append('project', selectedProject)
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
      navigate('/status')
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
      marginBottom: '2rem'
    },
    title: {
      fontSize: '1.75rem',
      fontWeight: '700',
      color: '#2a3441',
      marginBottom: '0.5rem',
      fontFamily: "'Sora', sans-serif"
    },
    subtitle: {
      fontSize: '1rem',
      color: '#5f6c7b'
    },
    card: {
      background: 'white',
      borderRadius: '16px',
      padding: '2rem',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      marginBottom: '1.5rem'
    },
    label: {
      display: 'block',
      fontSize: '0.9rem',
      fontWeight: '600',
      color: '#2a3441',
      marginBottom: '0.5rem'
    },
    required: {
      color: '#e53e3e',
      marginLeft: '2px'
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
      gap: '0.75rem'
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

  const isDisabled = uploading || files.length === 0 || !selectedProject

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>Upload Documents</h1>
        <p style={styles.subtitle}>
          Upload multiple files for analysis. Files process in the background.
        </p>
      </div>

      {/* Upload Form Card */}
      <div style={styles.card}>
        {/* Project Selection */}
        <div>
          <label style={styles.label}>
            Project <span style={styles.required}>*</span>
          </label>
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            style={styles.select}
          >
            <option value="">Select a project...</option>
            {projectList.map(project => (
              <option key={project.id} value={project.name}>
                {project.name}
              </option>
            ))}
          </select>
        </div>

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
            Files <span style={styles.required}>*</span>
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
            <div style={styles.dropzoneIcon}>📄</div>
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
                <span style={styles.fileIcon}>📄</span>
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
                  {item.status === 'pending' && '⏳'}
                  {item.status === 'uploading' && '⬆️'}
                  {item.status === 'success' && '✅'}
                  {item.status === 'error' && '❌'}
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
            <>⏳ Uploading {uploadProgress.filter(p => p.status === 'success').length}/{uploadProgress.length}...</>
          ) : (
            <>📤 Upload {files.length > 1 ? `${files.length} Files` : 'File'}</>
          )}
        </button>

        {/* Info Box */}
        <div style={styles.infoBox}>
          <p style={styles.infoText}>
            <span style={styles.infoLabel}>How it works: </span>
            Files are uploaded sequentially and queued for background processing. 
            Check the Status page to monitor progress.
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div style={styles.errorBox}>
            <span style={styles.errorIcon}>⚠️</span>
            <span style={styles.errorText}>{error}</span>
          </div>
        )}
      </div>

      {/* Supported Formats Card */}
      <div style={styles.card}>
        <h2 style={{ ...styles.title, fontSize: '1.1rem', marginBottom: '1rem' }}>
          Supported Formats
        </h2>
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
    </div>
  )
}
