import { useState, useEffect } from 'react'
import api from '../services/api'

export default function Status() {
  const [chromaStats, setChromaStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
    const interval = setInterval(loadStats, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadStats = async () => {
    try {
      const res = await api.get('/status/chromadb')
      setChromaStats(res.data)
    } catch (err) {
      console.error('Error loading stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const resetChromaDB = async () => {
    if (!confirm('Are you sure? This will delete all embeddings!')) return
    
    try {
      await api.post('/status/chromadb/reset')
      alert('ChromaDB reset successfully')
      loadStats()
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
        <h2 className="text-2xl font-bold mb-4">System Status</h2>

        {chromaStats && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 p-4 rounded">
              <p className="text-sm text-gray-600">Total Chunks</p>
              <p className="text-2xl font-bold">{chromaStats.total_chunks || 0}</p>
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
    </div>
  )
}
