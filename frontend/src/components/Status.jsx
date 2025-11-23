import { useState, useEffect } from 'react'
import api from '../services/api'

export default function Status() {
  const [chromaStats, setChromaStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadChromaStats()
    const interval = setInterval(loadChromaStats, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadChromaStats = async () => {
    try {
      const res = await api.get('/status/chromadb')
      setChromaStats(res.data)
      setError(null)
    } catch (err) {
      console.error('Error loading ChromaDB stats:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const resetChromaDB = async () => {
    if (!confirm('Are you sure? This will delete all embeddings!')) return
    
    try {
      await api.post('/status/chromadb/reset')
      alert('ChromaDB reset successfully')
      loadChromaStats()
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
        <h2 className="text-2xl font-bold mb-6">System Status</h2>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded p-4 mb-4">
            <p className="text-red-800">Error: {error}</p>
          </div>
        )}

        {chromaStats && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 p-6 rounded">
              <p className="text-sm text-gray-600 mb-2">Total Chunks</p>
              <p className="text-3xl font-bold text-blue-600">
                {chromaStats.total_chunks || 0}
              </p>
            </div>
            <div className="bg-gray-50 p-6 rounded">
              <p className="text-sm text-gray-600 mb-2">Actions</p>
              <button
                onClick={resetChromaDB}
                className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700"
              >
                Reset ChromaDB
              </button>
            </div>
          </div>
        )}

        {chromaStats?.error && (
          <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded p-4">
            <p className="text-yellow-800 text-sm">{chromaStats.error}</p>
          </div>
        )}
      </div>
    </div>
  )
}
