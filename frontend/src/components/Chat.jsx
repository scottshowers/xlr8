import { useState } from 'react'
import api from '../services/api'

export default function Chat({ projects, functionalAreas }) {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedProject, setSelectedProject] = useState('')
  const [selectedArea, setSelectedArea] = useState('')

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!message.trim()) return

    const userMessage = { role: 'user', content: message }
    setMessages(prev => [...prev, userMessage])
    setMessage('')
    setLoading(true)

    try {
      const res = await api.post('/chat', {
        message,
        project: selectedProject || null,
        functional_area: selectedArea || null
      })

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.data.response,
        routing: res.data.routing_decision,
        sources: res.data.sources_count
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'error',
        content: 'Error: ' + (err.response?.data?.detail || err.message)
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-4">Chat</h2>

        <div className="flex gap-4 mb-4">
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="border rounded px-3 py-2 flex-1"
          >
            <option value="">All Projects</option>
            {projects.map(p => (
              <option key={p.id} value={p.name}>{p.name}</option>
            ))}
          </select>

          <select
            value={selectedArea}
            onChange={(e) => setSelectedArea(e.target.value)}
            className="border rounded px-3 py-2 flex-1"
          >
            <option value="">All Areas</option>
            {functionalAreas.map(area => (
              <option key={area} value={area}>{area}</option>
            ))}
          </select>
        </div>

        <div className="border rounded p-4 h-96 overflow-y-auto mb-4 bg-gray-50">
          {messages.length === 0 && (
            <p className="text-gray-400 text-center">No messages yet</p>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`mb-4 ${msg.role === 'user' ? 'text-right' : ''}`}>
              <div className={`inline-block p-3 rounded-lg max-w-lg ${
                msg.role === 'user' ? 'bg-blue-500 text-white' :
                msg.role === 'error' ? 'bg-red-100 text-red-800' :
                'bg-white border'
              }`}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.routing && (
                  <p className="text-xs mt-2 opacity-75">
                    {msg.routing} • {msg.sources} sources
                  </p>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="text-center">
              <div className="inline-block animate-pulse bg-gray-300 rounded p-3">
                Thinking...
              </div>
            </div>
          )}
        </div>

        <form onSubmit={sendMessage} className="flex gap-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1 border rounded px-4 py-2"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !message.trim()}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
