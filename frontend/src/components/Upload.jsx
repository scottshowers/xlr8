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
  const [uploadResult, setUploadResult] = useState(null)
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
    setFiles(selectedFiles)
    setError(null)
    setUploadResult(null)
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select a file to upload')
      return
    }

    if (!selectedProject) {
      setError('Please select a project')
      return
    }

    setUploading(true)
    setError(null)
    setUploadResult(null)

    try {
      const file = files[0]
      
      const formData = new FormData()
      formData.append('file', file)
      formData.append('project', selectedProject)
      if (selectedArea) {
        formData.append('functional_area', selectedArea)
      }

      const response = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000
      })

      const { job_id, message } = response.data

      setUploadResult({
        success: true,
        message: message || 'File queued for processing!',
        job_id: job_id
      })

      setFiles([])
      setSelectedArea('')
      
      // Redirect to status page after 2 seconds
      setTimeout(() => {
        navigate('/status')
      }, 2000)

    } catch (err) {
      console.error('Upload error:', err)
      setError(err.response?.data?.detail || err.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  }

  // Styles matching your app's design
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
      marginBottom: '0.5rem'
    },
    dropzoneSubtext: {
      fontSize: '0.875rem',
      color: '#5f6c7b'
    },
    filePreview: {
      background: '#f0fdf4',
      border: '1px solid #86efac',
      borderRadius: '8px',
      padding: '1rem',
      marginBottom: '1.5rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem'
    },
    fileIcon: {
      fontSize: '1.5rem'
    },
    fileName: {
      flex: 1,
      color: '#2a3441',
      fontWeight: '500'
    },
    fileSize: {
      color: '#5f6c7b',
      fontSize: '0.875rem'
    },
    button: {
      width: '100%',
      padding: '1rem',
      fontSize: '1rem',
      fontWeight: '600',
      color: 'white',
      background: 'linear-gradient(135deg, #83b16d, #6b9956)',
      border: 'none',
      borderRadius: '10px',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.5rem',
      transition: 'all 0.2s ease',
      boxShadow: '0 2px 8px rgba(131, 177, 109, 0.3)'
    },
    buttonDisabled: {
      background: '#d1d9e0',
      cursor: 'not-allowed',
      boxShadow: 'none'
    },
    infoBox: {
      background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.08))',
      border: '1px solid rgba(131, 177, 109, 0.3)',
      borderRadius: '10px',
      padding: '1rem 1.25rem',
      marginTop: '1.5rem'
    },
    infoText: {
      fontSize: '0.9rem',
      color: '#2a3441',
      lineHeight: '1.5'
    },
    infoLabel: {
      fontWeight: '600',
      color: '#83b16d'
    },
    errorBox: {
      background: '#fef2f2',
      border: '1px solid #fecaca',
      borderRadius: '10px',
      padding: '1rem 1.25rem',
      marginTop: '1rem',
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem'
    },
    errorIcon: {
      color: '#dc2626',
      fontSize: '1.25rem'
    },
    errorText: {
      color: '#dc2626',
      fontSize: '0.9rem'
    },
    successBox: {
      background: '#f0fdf4',
      border: '1px solid #86efac',
      borderRadius: '10px',
      padding: '1.25rem',
      marginTop: '1rem'
    },
    successTitle: {
      color: '#166534',
      fontWeight: '600',
      fontSize: '1rem',
      marginBottom: '0.5rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem'
    },
    successText: {
      color: '#15803d',
      fontSize: '0.9rem'
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
    }
  }

  const isDisabled = uploading || files.length === 0 || !selectedProject

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>Upload Documents</h1>
        <p style={styles.subtitle}>
          Upload files for analysis. Large files process in the background.
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
            <option value="Global/Universal" style={{ fontWeight: '600', backgroundColor: '#f0f7ed' }}>
              🌐 Global/Universal (All Projects)
            </option>
            <option disabled>──────────────</option>
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
            File <span style={styles.required}>*</span>
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
            />
            <div style={styles.dropzoneIcon}>📄</div>
            <p style={styles.dropzoneText}>
              Click to select a file
            </p>
            <p style={styles.dropzoneSubtext}>
              PDF, Word, Excel, CSV, or Text files
            </p>
          </div>
        </div>

        {/* Selected Files */}
        {files.length > 0 && (
          <div style={styles.filePreview}>
            <span style={styles.fileIcon}>✅</span>
            <span style={styles.fileName}>{files[0].name}</span>
            <span style={styles.fileSize}>{formatFileSize(files[0].size)}</span>
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
            <>⏳ Uploading...</>
          ) : (
            <>📤 Upload File</>
          )}
        </button>

        {/* Info Box */}
        <div style={styles.infoBox}>
          <p style={styles.infoText}>
            <span style={styles.infoLabel}>How it works: </span>
            Files are queued for background processing. Large files may take several minutes. 
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

        {/* Success Message */}
        {uploadResult?.success && (
          <div style={styles.successBox}>
            <div style={styles.successTitle}>
              ✅ Upload Queued!
            </div>
            <p style={styles.successText}>
              {uploadResult.message}
            </p>
            <p style={{ ...styles.successText, marginTop: '0.5rem' }}>
              Redirecting to Status page...
            </p>
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
