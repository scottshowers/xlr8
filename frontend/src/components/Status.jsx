import { useState, useEffect } from 'react'
import { FileText, Loader2, CheckCircle, XCircle, Clock, Database } from 'lucide-react'
import api from '../services/api'

export default function Status() {
  const [chromaStats, setChromaStats] = useState(null)
  const [documents, setDocuments] = useState([])
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedProject, setSelectedProject] = useState('all')
  const [projects, setProjects] = useState([])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 3000)
    return () => clearInterval(interval)
  }, [selectedProject])

  const loadData = async () => {
    try {
      const [chromaRes, docsRes, jobsRes, projectsRes] = await Promise.all([
        api.get('/status/chromadb'),
        api.get('/status/documents', { params: selectedProject !== 'all' ? { project: selectedProject } : {} }),
        api.get('/jobs').catch(() => ({ data: { jobs: [] } })),
        api.get('/projects')
      ])
      
      setChromaStats(chromaRes.data)
      setDocuments(docsRes.data.documents || [])
      setJobs(jobsRes.data.jobs || [])
      setProjects(projectsRes.data.projects || [])
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

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'failed': return <XCircle className="w-5 h-5 text-red-500" />
      case 'processing': return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
      default: return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'failed': return 'bg-red-100 text-red-800'
      case 'processing': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
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
          <h2 className="text-2xl font-bold">System Status</h2>
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
            <option value="all">All Projects</option>
            <option value="__GLOBAL__">🌐 Global</option>
            {projects.map(p => (
              <option key={p.id} value={p.name}>{p.name}</option>
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
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Uploaded</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {documents.map((doc, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-gray-400" />
                        <span className="text-sm font-medium">{doc.filename}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-sm px-2 py-1 rounded ${
                        doc.project === '__GLOBAL__' 
                          ? 'bg-purple-100 text-purple-700' 
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {doc.project === '__GLOBAL__' ? '🌐 Global' : doc.project}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{doc.functional_area || '-'}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{doc.chunks}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {doc.upload_date ? new Date(doc.upload_date).toLocaleDateString() : '-'}
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
          <h2 className="text-2xl font-bold mb-4">Processing Jobs</h2>
          <div className="space-y-3">
            {jobs.map((job) => (
              <div key={job.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(job.status)}
                    <div>
                      <p className="font-medium">{job.filename}</p>
                      <p className="text-sm text-gray-500">{job.project}</p>
                    </div>
                  </div>
                  <span className={`text-xs px-3 py-1 rounded-full font-medium ${getStatusColor(job.status)}`}>
                    {job.status}
                  </span>
                </div>
                
                {job.progress !== undefined && job.status === 'processing' && (
                  <div className="mt-3">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">{job.current_step || 'Processing...'}</span>
                      <span className="text-gray-600">{job.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${job.progress}%` }}
                      />
                    </div>
                  </div>
                )}
                
                {job.error && (
                  <p className="mt-2 text-sm text-red-600">{job.error}</p>
                )}

                {job.result && (
                  <p className="mt-2 text-sm text-green-600">{job.result}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
