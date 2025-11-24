import { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, FileText, Loader2, AlertCircle, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import api from '../services/api'

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedProject, setSelectedProject] = useState('')
  const [projects, setProjects] = useState([])
  const [error, setError] = useState(null)
  const [expandedSources, setExpandedSources] = useState({})
  const messagesEndRef = useRef(null)

  useEffect(() => {
    loadProjects()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadProjects = async () => {
    try {
      const response = await api.get('/projects/list')
      setProjects(response.data || [])
    } catch (err) {
      console.error('Failed to load projects:', err)
    }
  }

  const toggleSources = (messageIndex) => {
    setExpandedSources(prev => ({
      ...prev,
      [messageIndex]: !prev[messageIndex]
    }))
  }

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const response = await api.post('/chat', {
        message: userMessage.content,
        project: selectedProject || null,
        max_results: 10
      })

      const { response: llmResponse, sources, chunks_found, model_used } = response.data

      const assistantMessage = {
        role: 'assistant',
        content: llmResponse,
        sources: sources || [],
        chunks_found: chunks_found || 0,
        model_used: model_used || 'unknown',
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, assistantMessage])

    } catch (err) {
      console.error('Chat error:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to get response')
      
      // Add error message to chat
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.response?.data?.detail || err.message}`,
        error: true,
        timestamp: new Date().toISOString()
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
    setExpandedSources({})
    setError(null)
  }

  const formatTimestamp = (ts) => {
    return new Date(ts).toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {/* Header */}
      <div className="bg-gray-800 rounded-t-lg p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Chat with Documents</h1>
            <p className="text-gray-400 text-sm">Ask questions about your uploaded files</p>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Project Filter */}
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:ring-2 focus:ring-green-500"
            >
              <option value="">All Projects</option>
              {projects.map(project => (
                <option key={project.id} value={project.name}>
                  {project.name}
                </option>
              ))}
            </select>

            {/* Clear Chat */}
            <button
              onClick={clearChat}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
              title="Clear chat"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto bg-gray-900 p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <Bot className="w-16 h-16 mb-4 opacity-50" />
            <p className="text-lg mb-2">Start a conversation</p>
            <p className="text-sm text-center max-w-md">
              Ask questions about your uploaded documents. 
              {selectedProject ? ` Searching in: ${selectedProject}` : ' Select a project to filter results.'}
            </p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-5 h-5 text-white" />
                </div>
              )}
              
              <div className={`max-w-[80%] ${message.role === 'user' ? 'order-first' : ''}`}>
                <div
                  className={`rounded-lg p-4 ${
                    message.role === 'user'
                      ? 'bg-green-600 text-white'
                      : message.error
                        ? 'bg-red-900/50 border border-red-700 text-red-200'
                        : 'bg-gray-800 text-gray-100'
                  }`}
                >
                  {/* Message Content */}
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  
                  {/* Sources Section (for assistant messages) */}
                  {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-gray-700">
                      <button
                        onClick={() => toggleSources(index)}
                        className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
                      >
                        <FileText className="w-4 h-4" />
                        <span>{message.chunks_found} sources found</span>
                        {expandedSources[index] ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                      
                      {expandedSources[index] && (
                        <div className="mt-3 space-y-2">
                          {message.sources.slice(0, 5).map((source, sIdx) => (
                            <div
                              key={sIdx}
                              className="bg-gray-700/50 rounded-lg p-3 text-sm"
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-green-400 font-medium">
                                  {source.filename}
                                </span>
                                <span className="text-gray-500 text-xs">
                                  {source.relevance}% match
                                </span>
                              </div>
                              {source.sheet && (
                                <span className="text-gray-400 text-xs">
                                  Sheet: {source.sheet}
                                </span>
                              )}
                              {source.functional_area && (
                                <span className="text-gray-400 text-xs ml-2">
                                  Area: {source.functional_area}
                                </span>
                              )}
                              <p className="text-gray-300 text-xs mt-2 line-clamp-2">
                                {source.preview}
                              </p>
                            </div>
                          ))}
                          {message.sources.length > 5 && (
                            <p className="text-gray-500 text-xs text-center">
                              + {message.sources.length - 5} more sources
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                
                {/* Timestamp & Model */}
                <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                  <span>{formatTimestamp(message.timestamp)}</span>
                  {message.model_used && message.model_used !== 'none' && (
                    <span className="text-gray-600">• {message.model_used}</span>
                  )}
                </div>
              </div>

              {message.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center flex-shrink-0">
                  <User className="w-5 h-5 text-white" />
                </div>
              )}
            </div>
          ))
        )}
        
        {/* Loading Indicator */}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center gap-2 text-gray-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Searching documents and generating response...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-900/50 border-t border-red-700 p-3 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <span className="text-red-300 text-sm">{error}</span>
          <button 
            onClick={() => setError(null)}
            className="ml-auto text-red-400 hover:text-red-300"
          >
            ×
          </button>
        </div>
      )}

      {/* Input Area */}
      <div className="bg-gray-800 rounded-b-lg p-4 border-t border-gray-700">
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={selectedProject 
              ? `Ask about ${selectedProject} documents...` 
              : "Ask a question about your documents..."
            }
            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-400 resize-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
            rows={2}
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className={`px-4 rounded-lg transition-colors flex items-center justify-center ${
              loading || !input.trim()
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                : 'bg-green-600 hover:bg-green-700 text-white'
            }`}
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        <p className="text-gray-500 text-xs mt-2">
          Press Enter to send • Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
