import { useState } from 'react'
import api from '../services/api'

export default function Upload({ projects, functionalAreas }) {
  const [file, setFile] = useState(null)
  const [selectedProject, setSelectedProject] = useState('')
  const [selectedArea, setSelectedArea] = useState('')
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file || !selectedProject) return

    setUploading(true)
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('project', selectedProject)
    if (selectedArea) {
      formData.append('functional_area', selectedArea)
    }

    try {
      const res = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000
      })

      setResult({
        success: true,
        message: `Upload queued! Job ID: ${res.data.job_id}`,
        jobId: res.data.job_id
      })
      setFile(null)
    } catch (err) {
      setResult({
        success: false,
        message: 'Upload failed: ' + (err.response?.data?.detail || err.message)
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-4">Upload Document</h2>

        <form onSubmit={handleUpload} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Project *</label>
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="w-full border rounded px-3 py-2"
              required
            >
              <option value="">Select project</option>
              {projects.map(p => (
                <option key={p.id} value={p.name}>{p.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Functional Area</label>
            <select
              value={selectedArea}
              onChange={(e) => setSelectedArea(e.target.value)}
              className="w-full border rounded px-3 py-2"
            >
              <option value="">Select area (optional)</option>
              {functionalAreas.map(area => (
                <option key={area} value={area}>{area}</option>
              ))}
            </select>
          </div>

          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center ${
              dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {file ? (
              <div>
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  className="mt-2 text-red-600 text-sm hover:underline"
                >
                  Remove
                </button>
              </div>
            ) : (
              <div>
                <p className="text-gray-600">Drag & drop file here, or</p>
                <label className="mt-2 inline-block cursor-pointer text-blue-600 hover:underline">
                  browse files
                  <input
                    type="file"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files[0])}
                    accept=".xlsx,.xls,.pdf,.docx,.txt"
                  />
                </label>
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={!file || !selectedProject || uploading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </form>

        {result && (
          <div className={`mt-4 p-4 rounded-lg ${
            result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            <p>{result.message}</p>
            {result.jobId && (
              <p className="text-sm mt-2">Check Status page to monitor progress</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
