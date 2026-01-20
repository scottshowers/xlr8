import { useState, useEffect } from 'react'
import { FileText, Loader2, CheckCircle, XCircle, Clock, Database, Trash2, StopCircle, Calendar, HardDrive } from 'lucide-react'
import api from '../services/api'

export default function Status() {
  const [chromaStats, setChromaStats] = useState(null)
  const [documents, setDocuments] = useState([])
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedProject, setSelectedProject] = useState('all')
  const [projects, setProjects] = useState([])
  const [deleting, setDeleting] = useState(null)
  const [killingJob, setKillingJob] = useState(null)
  const [deletingJob, setDeletingJob] = useState(null)
  const [clearingOldJobs, setClearingOldJobs] = useState(false)
  const [deleteStartDate, setDeleteStartDate] = useState('')
  const [deleteEndDate, setDeleteEndDate] = useState('')

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 3000)
    return () => clearInterval(interval)
  }, [selectedProject])

  const loadData = async () => {
    try {
      const chromaRes = await api.get('/status/chromadb').catch(() => ({ data: { total_chunks: 0 } }))
      const docsRes = await api.get('/status/documents', { 
        params: selectedProject !== 'all' ? { customer_id: selectedProject } : {} 
      }).catch(() => ({ data: { documents: [] } }))
      const jobsRes = await api.get('/jobs').catch(() => ({ data: { jobs: [] } }))
      const projectsRes = await api.get('/customers/list').catch(() => ({ data: [] }))
      
      setChromaStats(chromaRes.data)
      setDocuments(docsRes.data.documents || [])
      setJobs(jobsRes.data.jobs || [])
      setProjects(Array.isArray(projectsRes.data) ? projectsRes.data : projectsRes.data.projects || [])
    } catch (err) {
      console.error('Error loading data:', err)
    } finally {
      setLoading(false)
    }
  }

  const resetChromaDB = async () => {
    if (!confirm('Are you sure? This will delete all embeddings!')) return
    
    try {
      await api.post('/status/chromadb/reset')
      alert('ChromaDB reset successfully')
      loadData()
    } catch (err) {
      alert('Error resetting ChromaDB: ' + err.message)
    }
  }

  const killJob = async (jobId) => {
    if (!confirm('Kill this stuck job? It will be marked as failed.')) return
    
    setKillingJob(jobId)
    
    try {
      await api.post(`/jobs/${jobId}/fail`, null, {
        params: { error_message: 'Job manually terminated - stuck/hung' }
      })
      
      alert('Job terminated successfully')
      await loadData()
    } catch (err) {
      console.error('Kill job error:', err)
      alert('Error killing job: ' + (err.response?.data?.detail || err.message))
    } finally {
      setKillingJob(null)
    }
  }

  const deleteJob = async (jobId) => {
    if (!confirm('Delete this job from history? This cannot be undone.')) return
    
    setDeletingJob(jobId)
    
    try {
      await api.delete(`/jobs/${jobId}`)
      
      alert('Job deleted successfully')
      await loadData()
    } catch (err) {
      console.error('Delete job error:', err)
      alert('Error deleting job: ' + (err.response?.data?.detail || err.message))
    } finally {
      setDeletingJob(null)
    }
  }

  const deleteOldJobs = async () => {
    if (!deleteStartDate || !deleteEndDate) {
      alert('Please select both start and end dates')
      return
    }
    
    if (!confirm(`Delete all jobs from ${deleteStartDate} to ${deleteEndDate}?`)) return
    
    setClearingOldJobs(true)
    
    try {
      const res = await api.delete(`/jobs/old?start_date=${deleteStartDate}T00:00:00Z&end_date=${deleteEndDate}T23:59:59Z`)
      alert(`Deleted ${res.data.deleted_count || 0} jobs`)
      setDeleteStartDate('')
      setDeleteEndDate('')
      await loadData()
    } catch (err) {
      console.error('Delete old jobs error:', err)
      alert('Error clearing jobs: ' + (err.response?.data?.detail || err.message))
    } finally {
      setClearingOldJobs(false)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'failed': return <XCircle className="w-5 h-5 text-red-500" />
      case 'processing': return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
      case 'queued': 
      case 'pending': return <Clock className="w-5 h-5 text-yellow-500" />
      default: return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'failed': return 'bg-red-100 text-red-800'
      case 'processing': return 'bg-blue-100 text-blue-800'
      case 'queued':
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const deleteDocument = async (filename, project) => {
    if (!confirm(`Delete "${filename}"? This cannot be undone.`)) return
    
    setDeleting(filename)
    
    try {
      await api.delete(`/status/documents/${encodeURIComponent(filename)}`, {
        params: { project }
      })
      
      await loadData()
      alert(`"${filename}" deleted successfully`)
    } catch (err) {
      console.error('Delete error:', err)
      alert('Error deleting document: ' + (err.response?.data?.detail || err.message))
    } finally {
      setDeleting(null)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return '-'
    }
  }

  const formatFileSize = (bytes) => {
    if (!bytes) return '-'
    const mb = bytes / (1024 * 1024)
    if (mb < 1) {
      return `${(bytes / 1024).toFixed(1)} KB`
    }
    return `${mb.toFixed(2)} MB`
  }

  // Helper to get project name from ID or name
  const getProjectDisplay = (projectValue) => {
    if (!projectValue) return '-'
    if (projectValue === '__GLOBAL__' || projectValue === 'GLOBAL' || projectValue === 'global' || projectValue === 'Global/Universal') {
      return 'Global'
    }
    // Check if it's a UUID (has dashes and is 36 chars)
    if (projectValue.length === 36 && projectValue.includes('-')) {
      const found = projects.find(p => p.id === projectValue)
      return found ? found.name : projectValue.slice(0, 8) + '...'
    }
    return projectValue
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* System Stats */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-6 h-6 text-blue-600" />
          <h2 className="text-2xl font-bold">File Status</h2>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">Total Chunks</p>
            <p className="text-3xl font-bold text-blue-600">{chromaStats?.total_chunks || 0}</p>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">Documents</p>
            <p className="text-3xl font-bold text-green-600">{documents.length}</p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg flex items-center justify-center">
            <button
              onClick={resetChromaDB}
              className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700 text-sm font-medium"
            >
              Reset Database
            </button>
          </div>
        </div>
      </div>

      {/* Documents List */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FileText className="w-6 h-6 text-blue-600" />
            <h2 className="text-2xl font-bold">Documents</h2>
          </div>
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="all">All Customers</option>
            <option value="__GLOBAL__">Global</option>
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        {documents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p>No documents uploaded yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">File</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Project</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Area</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Chunks</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      Uploaded
                    </div>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {documents.map((doc, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-gray-400" />
                        <div>
                          <span className="text-sm font-medium">{doc.filename}</span>
                          {doc.file_type && (
                            <span className="ml-2 text-xs text-gray-500 uppercase">
                              .{doc.file_type}
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-sm px-2 py-1 rounded ${
                        doc.project === '__GLOBAL__' || doc.project === 'GLOBAL' || doc.project === 'Global/Universal'
                          ? 'bg-purple-100 text-purple-700' 
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {getProjectDisplay(doc.project)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{doc.functional_area || '-'}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 text-sm text-gray-600">
                        <Database className="w-3 h-3" />
                        {doc.chunks}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {formatDate(doc.upload_date)}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => deleteDocument(doc.filename, doc.project)}
                        disabled={deleting === doc.filename}
                        className="text-red-600 hover:text-red-800 p-1 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Delete document"
                      >
                        {deleting === doc.filename ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Job Monitor */}
      {jobs.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold">Processing Jobs</h2>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Delete range:</span>
              <input
                type="date"
                value={deleteStartDate}
                onChange={(e) => setDeleteStartDate(e.target.value)}
                className="px-2 py-1 text-sm border rounded"
                title="Start date"
              />
              <span className="text-gray-400">to</span>
              <input
                type="date"
                value={deleteEndDate}
                onChange={(e) => setDeleteEndDate(e.target.value)}
                className="px-2 py-1 text-sm border rounded"
                title="End date"
              />
              <button
                onClick={deleteOldJobs}
                disabled={clearingOldJobs || !deleteStartDate || !deleteEndDate}
                className="flex items-center gap-1 px-3 py-1 bg-red-100 text-red-700 text-sm rounded hover:bg-red-200 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Delete jobs in date range"
              >
                {clearingOldJobs ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    <span>Delete Range</span>
                  </>
                )}
              </button>
            </div>
          </div>
          <div className="space-y-3">
            {jobs.map((job) => (
              <div key={job.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3 flex-1">
                    {getStatusIcon(job.status)}
                    <div className="flex-1">
                      <p className="font-medium">{job.input_data?.filename || 'Processing...'}</p>
                      <div className="flex items-center gap-3 mt-1">
                        <p className="text-sm text-gray-500">{getProjectDisplay(job.project_id)}</p>
                        {job.created_at && (
                          <p className="text-xs text-gray-400 flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(job.created_at)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-3 py-1 rounded-full font-medium ${getStatusColor(job.status)}`}>
                      {job.status}
                    </span>
                    {/* Kill button for processing jobs */}
                    {job.status === 'processing' && (
                      <button
                        onClick={() => killJob(job.id)}
                        disabled={killingJob === job.id}
                        className="flex items-center gap-1 px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Kill stuck job"
                      >
                        {killingJob === job.id ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin" />
                            <span>Killing...</span>
                          </>
                        ) : (
                          <>
                            <StopCircle className="w-3 h-3" />
                            <span>Kill Job</span>
                          </>
                        )}
                      </button>
                    )}
                    {/* Delete button for completed/failed/queued/pending jobs */}
                    {(job.status === 'completed' || job.status === 'failed' || job.status === 'queued' || job.status === 'pending') && (
                      <button
                        onClick={() => deleteJob(job.id)}
                        disabled={deletingJob === job.id}
                        className="flex items-center gap-1 px-3 py-1 bg-gray-600 text-white text-xs rounded hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Delete job from history"
                      >
                        {deletingJob === job.id ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin" />
                            <span>Deleting...</span>
                          </>
                        ) : (
                          <>
                            <Trash2 className="w-3 h-3" />
                            <span>Delete</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
                
                {job.progress && job.status === 'processing' && (
                  <div className="mt-3">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">{job.progress.step || 'Processing...'}</span>
                      <span className="text-gray-600">{job.progress.percent || 0}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${job.progress.percent || 0}%` }}
                      />
                    </div>
                  </div>
                )}
                
                {job.error_message && (
                  <p className="mt-2 text-sm text-red-600">{job.error_message}</p>
                )}

                {job.result_data && (
                  <p className="mt-2 text-sm text-green-600">
                    {typeof job.result_data === 'string' ? job.result_data : 'Completed'}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
