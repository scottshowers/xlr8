import { useState, useEffect } from 'react'
import { Upload as UploadIcon, FileText, CheckCircle, AlertCircle, Loader2, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

export default function Upload() {
  const navigate = useNavigate()
  const [files, setFiles] = useState([])
  const [selectedArea, setSelectedArea] = useState('')
  const [selectedProject, setSelectedProject] = useState('')
  const [projects, setProjects] = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [error, setError] = useState(null)

  const functionalAreas = [
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

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      const response = await api.get('/projects/list')
      setProjects(response.data || [])
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
      const file = files[0] // Upload first file
      
      const formData = new FormData()
      formData.append('file', file)
      formData.append('project', selectedProject)
      if (selectedArea) {
        formData.append('functional_area', selectedArea)
      }

      // Call async upload endpoint
      const response = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000 // 30 second timeout for initial upload (just file save)
      })

      const { job_id, message } = response.data

      // Show success and redirect to status page
      setUploadResult({
        success: true,
        message: message || 'File queued for processing!',
        job_id: job_id
      })

      // Clear form
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Upload Documents</h1>
        <p className="text-gray-400 mt-1">
          Upload files for analysis. Large files process in the background.
        </p>
      </div>

      {/* Upload Form */}
      <div className="bg-gray-800 rounded-lg p-6 space-y-6">
        
        {/* Project Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Project <span className="text-red-400">*</span>
          </label>
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-green-500 focus:border-transparent"
          >
            <option value="">Select a project...</option>
            {projects.map(project => (
              <option key={project.id} value={project.name}>
                {project.name}
              </option>
            ))}
          </select>
        </div>

        {/* Functional Area */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Functional Area
          </label>
          <select
            value={selectedArea}
            onChange={(e) => setSelectedArea(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-green-500 focus:border-transparent"
          >
            <option value="">Select area (optional)...</option>
            {functionalAreas.map(area => (
              <option key={area} value={area}>{area}</option>
            ))}
          </select>
        </div>

        {/* File Drop Zone */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            File <span className="text-red-400">*</span>
          </label>
          <div className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-green-500 transition-colors">
            <input
              type="file"
              onChange={handleFileChange}
              className="hidden"
              id="file-upload"
              accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <UploadIcon className="w-12 h-12 text-gray-500 mx-auto mb-4" />
              <p className="text-gray-300 mb-2">
                Click to select a file
              </p>
              <p className="text-gray-500 text-sm">
                PDF, Word, Excel, CSV, or Text files
              </p>
            </label>
          </div>
        </div>

        {/* Selected Files */}
        {files.length > 0 && (
          <div className="bg-gray-700/50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Selected File:</h3>
            <div className="space-y-2">
              {files.map((file, index) => (
                <div key={index} className="flex items-center gap-3 text-gray-300">
                  <FileText className="w-5 h-5 text-green-400" />
                  <span className="flex-1 truncate">{file.name}</span>
                  <span className="text-gray-500 text-sm">
                    {formatFileSize(file.size)}
                  </span>
                </div>
              ))}
            </div>
            {files.length > 1 && (
              <p className="text-yellow-400 text-sm mt-2">
                Note: Only the first file will be uploaded. Multiple file support coming soon!
              </p>
            )}
          </div>
        )}

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={uploading || files.length === 0 || !selectedProject}
          className={`w-full py-3 px-4 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors ${
            uploading || files.length === 0 || !selectedProject
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-700 text-white'
          }`}
        >
          {uploading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <UploadIcon className="w-5 h-5" />
              Upload File
            </>
          )}
        </button>

        {/* Info Box */}
        <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4">
          <p className="text-blue-300 text-sm">
            <strong>How it works:</strong> Files are queued for background processing. 
            Large files may take several minutes. Check the Status page to monitor progress.
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-300 font-medium">Upload Error</p>
              <p className="text-red-400 text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Success Message */}
        {uploadResult?.success && (
          <div className="bg-green-900/50 border border-green-700 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-green-300 font-medium">Upload Queued!</p>
                <p className="text-green-400 text-sm mt-1">{uploadResult.message}</p>
                <p className="text-green-400 text-sm mt-2">
                  Redirecting to Status page...
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate('/status')}
              className="mt-4 w-full bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              Go to Status Page
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Supported Formats */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Supported Formats</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { ext: 'PDF', desc: 'Documents' },
            { ext: 'DOCX', desc: 'Word files' },
            { ext: 'XLSX', desc: 'Excel files' },
            { ext: 'CSV', desc: 'Data files' },
            { ext: 'TXT', desc: 'Text files' },
            { ext: 'MD', desc: 'Markdown' },
          ].map(format => (
            <div key={format.ext} className="bg-gray-700/50 rounded-lg p-3 text-center">
              <p className="text-green-400 font-mono font-bold">.{format.ext}</p>
              <p className="text-gray-400 text-sm">{format.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
