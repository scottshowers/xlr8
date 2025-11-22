import { useState, useEffect, useRef } from 'react'
import api from '../services/api'

export default function Status() {
  const [jobs, setJobs] = useState([])
  const [chromaStats, setChromaStats] = useState(null)
  const [wsStatus, setWsStatus] = useState('connecting')
  const [loading, setLoading] = useState(true)
  const wsRef = useRef(null)

  useEffect(() => {
    loadInitialData()
    connectWebSocket()
    const interval = setInterval(loadJobs, 10000)
    
    return () => {
      clearInterval(interval)
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const loadInitialData = async () => {
    try {
      const [jobsRes, chromaRes] = await Promise.all([
        api.get('/status/jobs'),
        api.get('/status/chromadb')
      ])
      setJobs(jobsRes.data.jobs || [])
      setChromaStats(chromaRes.data)
    } catch (err) {
      console.error('Error loading data:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadJobs = async () => {
    try {
      const res = await api.get('/status/jobs')
      setJobs(res.data.jobs || [])
    } catch (err) {
      console.error('Error loading jobs:', err)
    }
  }

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/jobs`)
    
    ws.onopen = () => {
      setWsStatus('connected')
      console.log('WebSocket connected')
    }
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data)
      setJobs(prev => prev.map(job => 
        job.job_id === update.job_id 
          ? { ...job, ...update }
          : job
      ))
    }
    
    ws.onerror = () => {
      setWsStatus('error')
    }
    
    ws.onclose = () => {
      setWsStatus('disconnected')
      setTimeout(connectWebSocket, 5000)
    }
    
    wsRef.current = ws
  }

  const resetChromaDB = async () => {
    if (!confirm('Are you sure? This will delete all embeddings!')) return
    
    try {
      await api.post('/status/chromadb/reset')
      alert('ChromaDB reset successfully')
      loadInitialData()
    } catch (err) {
      alert('Error resetting ChromaDB: ' + err.message)
    }
  }

  if (loading) {
    return <div className="text-center py-8">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">System Status</h2>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              wsStatus === 'connected' ? 'bg-green-500' :
              wsStatus === 'connecting' ? 'bg-yellow-500' :
              'bg-red-500'
            }`}></div>
            <span className="text-sm text-gray-600">WebSocket: {wsStatus}</span>
          </div>
        </div>

        {chromaStats && (
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded">
              <p className="text-sm text-gray-600">Total Chunks</p>
              <p className="text-2xl font-bold">{chromaStats.total_chunks || 0}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded">
              <p className="text-sm text-gray-600">Collections</p>
              <p className="text-2xl font-bold">{chromaStats.collections?.length || 0}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded">
              <button
                onClick={resetChromaDB}
                className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700 text-sm"
              >
                Reset ChromaDB
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold mb-4">Recent Jobs</h3>
        
        {jobs.length === 0 ? (
          <p className="text-gray-400 text-center py-4">No jobs yet</p>
        ) : (
          <div className="space-y-2">
            {jobs.map(job => (
              <div key={job.job_id} className="border rounded p-4">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="font-medium">{job.filename}</p>
                    <p className="text-sm text-gray-600">{job.project}</p>
                    {job.functional_area && (
                      <p className="text-xs text-gray-500">{job.functional_area}</p>
                    )}
                  </div>
                  <span className={`px-3 py-1 rounded text-sm ${
                    job.status === 'completed' ? 'bg-green-100 text-green-800' :
                    job.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                    job.status === 'failed' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {job.status}
                  </span>
                </div>
                
                {job.status === 'processing' && job.progress !== undefined && (
                  <div className="mt-2">
                    <div className="bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all"
                        style={{ width: `${job.progress}%` }}
                      ></div>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">{job.progress}%</p>
                  </div>
                )}
                
                {job.chunks_processed && (
                  <p className="text-sm text-gray-600 mt-2">
                    Chunks processed: {job.chunks_processed}
                  </p>
                )}
                
                {job.error && (
                  <p className="text-sm text-red-600 mt-2">{job.error}</p>
                )}
                
                <p className="text-xs text-gray-400 mt-2">
                  {new Date(job.created_at).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
