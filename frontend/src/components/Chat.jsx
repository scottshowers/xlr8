import { useState, useEffect, useRef } from 'react'
import api from '../services/api'

export default function Chat({ projects = [], functionalAreas = [] }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedProject, setSelectedProject] = useState('')
  const [projectList, setProjectList] = useState(projects)
  const [error, setError] = useState(null)
  const [expandedSources, setExpandedSources] = useState({})
  const [modelInfo, setModelInfo] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (projects.length > 0) {
      setProjectList(projects)
    } else {
      loadProjects()
    }
    loadModelInfo()
  }, [projects])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadProjects = async () => {
    try {
      const response = await api.get('/projects/list')
      setProjectList(response.data || [])
    } catch (err) {
      console.error('Failed to load projects:', err)
    }
  }

  const loadModelInfo = async () => {
    try {
      const response = await api.get('/chat/models')
      setModelInfo(response.data)
    } catch (err) {
      console.error('Failed to load model info:', err)
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
        max_results: 10,
        use_claude: true
      })

      const { response: llmResponse, sources, chunks_found, models_used, sanitized } = response.data

      const assistantMessage = {
        role: 'assistant',
        content: llmResponse,
        sources: sources || [],
        chunks_found: chunks_found || 0,
        models_used: models_used || [],
        sanitized: sanitized || false,
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, assistantMessage])

    } catch (err) {
      console.error('Chat error:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to get response')
      
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

  const getModelBadge = (model) => {
    if (model.includes('mistral')) return { icon: '🔵', label: 'Mistral', color: '#3b82f6' }
    if (model.includes('deepseek')) return { icon: '🟣', label: 'DeepSeek', color: '#8b5cf6' }
    if (model.includes('claude')) return { icon: '🟠', label: 'Claude', color: '#f97316' }
    return { icon: '⚪', label: model, color: '#6b7280' }
  }

  // Styles matching your app's design
  const styles = {
    container: {
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 180px)',
      maxWidth: '1000px',
      margin: '0 auto'
    },
    header: {
      background: 'white',
      borderRadius: '16px 16px 0 0',
      padding: '1.25rem 1.5rem',
      borderBottom: '1px solid #e1e8ed',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)'
    },
    headerTitle: {
      fontSize: '1.25rem',
      fontWeight: '700',
      color: '#2a3441',
      fontFamily: "'Sora', sans-serif"
    },
    headerSubtitle: {
      fontSize: '0.875rem',
      color: '#5f6c7b',
      marginTop: '0.25rem'
    },
    headerControls: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem'
    },
    select: {
      padding: '0.5rem 1rem',
      fontSize: '0.9rem',
      border: '1px solid #e1e8ed',
      borderRadius: '8px',
      background: 'white',
      color: '#2a3441',
      outline: 'none',
      cursor: 'pointer'
    },
    clearButton: {
      padding: '0.5rem 1rem',
      fontSize: '0.875rem',
      fontWeight: '500',
      color: '#5f6c7b',
      background: '#f6f5fa',
      border: '1px solid #e1e8ed',
      borderRadius: '8px',
      cursor: 'pointer',
      transition: 'all 0.2s ease'
    },
    messagesArea: {
      flex: 1,
      overflowY: 'auto',
      background: '#fafbfc',
      padding: '1.5rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '1rem'
    },
    emptyState: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      color: '#5f6c7b',
      textAlign: 'center'
    },
    emptyIcon: {
      fontSize: '4rem',
      marginBottom: '1rem',
      opacity: 0.5
    },
    emptyTitle: {
      fontSize: '1.1rem',
      fontWeight: '600',
      color: '#2a3441',
      marginBottom: '0.5rem'
    },
    emptyText: {
      fontSize: '0.9rem',
      maxWidth: '300px'
    },
    messageRow: {
      display: 'flex',
      gap: '0.75rem'
    },
    messageRowUser: {
      flexDirection: 'row-reverse'
    },
    avatar: {
      width: '36px',
      height: '36px',
      borderRadius: '50%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '1rem',
      flexShrink: 0
    },
    avatarUser: {
      background: 'linear-gradient(135deg, #83b16d, #6b9956)',
      color: 'white'
    },
    avatarAssistant: {
      background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.2), rgba(147, 171, 217, 0.2))',
      color: '#83b16d'
    },
    messageBubble: {
      maxWidth: '75%',
      borderRadius: '12px',
      padding: '1rem 1.25rem'
    },
    messageBubbleUser: {
      background: 'linear-gradient(135deg, #83b16d, #6b9956)',
      color: 'white',
      borderBottomRightRadius: '4px'
    },
    messageBubbleAssistant: {
      background: 'white',
      color: '#2a3441',
      borderBottomLeftRadius: '4px',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)'
    },
    messageBubbleError: {
      background: '#fef2f2',
      border: '1px solid #fecaca',
      color: '#dc2626'
    },
    messageContent: {
      whiteSpace: 'pre-wrap',
      lineHeight: 1.5,
      fontSize: '0.95rem'
    },
    messageTime: {
      fontSize: '0.75rem',
      marginTop: '0.5rem',
      opacity: 0.7
    },
    sourcesSection: {
      marginTop: '1rem',
      paddingTop: '1rem',
      borderTop: '1px solid #e1e8ed'
    },
    sourcesHeader: {
      fontSize: '0.9rem',
      fontWeight: '600',
      color: '#2a3441',
      marginBottom: '0.75rem'
    },
    sourcesToggle: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '0.85rem',
      color: '#5f6c7b',
      cursor: 'pointer',
      background: 'none',
      border: 'none',
      padding: 0
    },
    sourcesList: {
      display: 'flex',
      flexDirection: 'column',
      gap: '0.5rem',
      maxHeight: '300px',
      overflowY: 'auto'
    },
    sourceItem: {
      background: '#f6f5fa',
      borderRadius: '8px',
      padding: '0.75rem',
      fontSize: '0.8rem',
      border: '1px solid #e1e8ed'
    },
    sourceHeader: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '0.5rem'
    },
    sourceFilename: {
      color: '#83b16d',
      fontWeight: '600',
      fontSize: '0.85rem'
    },
    sourceRelevance: {
      fontSize: '0.75rem'
    },
    sourceMetadata: {
      display: 'flex',
      gap: '0.75rem',
      marginBottom: '0.5rem',
      flexWrap: 'wrap'
    },
    metadataTag: {
      fontSize: '0.7rem',
      color: '#5f6c7b',
      background: 'rgba(131, 177, 109, 0.1)',
      padding: '0.125rem 0.5rem',
      borderRadius: '4px'
    },
    sourcePreview: {
      color: '#5f6c7b',
      fontSize: '0.75rem',
      marginTop: '0.25rem',
      lineHeight: 1.4,
      overflow: 'hidden',
      display: '-webkit-box',
      WebkitLineClamp: 2,
      WebkitBoxOrient: 'vertical'
    },
    loadingBubble: {
      background: 'white',
      borderRadius: '12px',
      padding: '1rem 1.25rem',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      color: '#5f6c7b'
    },
    inputArea: {
      background: 'white',
      borderRadius: '0 0 16px 16px',
      padding: '1rem 1.5rem',
      borderTop: '1px solid #e1e8ed',
      boxShadow: '0 -1px 3px rgba(42, 52, 65, 0.04)'
    },
    inputRow: {
      display: 'flex',
      gap: '0.75rem'
    },
    textarea: {
      flex: 1,
      padding: '0.75rem 1rem',
      fontSize: '1rem',
      border: '1px solid #e1e8ed',
      borderRadius: '10px',
      resize: 'none',
      outline: 'none',
      fontFamily: 'inherit',
      lineHeight: 1.4
    },
    sendButton: {
      padding: '0.75rem 1.5rem',
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
      transition: 'all 0.2s ease',
      boxShadow: '0 2px 8px rgba(131, 177, 109, 0.3)'
    },
    sendButtonDisabled: {
      background: '#d1d9e0',
      cursor: 'not-allowed',
      boxShadow: 'none'
    },
    inputHint: {
      fontSize: '0.75rem',
      color: '#5f6c7b',
      marginTop: '0.5rem'
    },
    errorBanner: {
      background: '#fef2f2',
      border: '1px solid #fecaca',
      padding: '0.75rem 1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '0.875rem',
      color: '#dc2626'
    }
  }

  const isDisabled = loading || !input.trim()

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.headerTitle}>Chat with Documents</h1>
          <p style={styles.headerSubtitle}>Ask questions about your uploaded files</p>
        </div>
        
        <div style={styles.headerControls}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem',
            padding: '0.25rem 0.75rem',
            background: 'rgba(131, 177, 109, 0.1)',
            borderRadius: '6px',
            fontSize: '0.75rem',
            color: '#5f6c7b'
          }}>
            <span title="Local AI (can see data)">🔵 Local</span>
            <span>→</span>
            <span title="PII Sanitized">🔒</span>
            <span>→</span>
            <span title="Claude (synthesis only)">🟠 Claude</span>
          </div>

          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            style={styles.select}
          >
            <option value="">All Projects</option>
            {projectList.map(project => (
              <option key={project.id} value={project.name}>
                {project.name}
              </option>
            ))}
          </select>

          <button onClick={clearChat} style={styles.clearButton}>
            🔄 Clear
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div style={styles.messagesArea}>
        {messages.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>💬</div>
            <p style={styles.emptyTitle}>Start a conversation</p>
            <p style={styles.emptyText}>
              Ask questions about your uploaded documents.
              {selectedProject ? ` Searching in: ${selectedProject}` : ' Select a project to filter results.'}
            </p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              style={{
                ...styles.messageRow,
                ...(message.role === 'user' ? styles.messageRowUser : {})
              }}
            >
              <div style={{
                ...styles.avatar,
                ...(message.role === 'user' ? styles.avatarUser : styles.avatarAssistant)
              }}>
                {message.role === 'user' ? '👤' : '🤖'}
              </div>
              
              <div>
                <div style={{
                  ...styles.messageBubble,
                  ...(message.role === 'user' 
                    ? styles.messageBubbleUser 
                    : message.error 
                      ? styles.messageBubbleError 
                      : styles.messageBubbleAssistant)
                }}>
                  <div style={styles.messageContent}>{message.content}</div>
                  
                  {/* Sources Section - ALWAYS VISIBLE */}
                  {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                    <div style={styles.sourcesSection}>
                      <div style={styles.sourcesHeader}>
                        📄 {message.chunks_found} Sources Referenced
                      </div>
                      
                      <div style={styles.sourcesList}>
                        {message.sources.map((source, sIdx) => (
                          <div key={sIdx} style={styles.sourceItem}>
                            <div style={styles.sourceHeader}>
                              <span style={styles.sourceFilename}>{source.filename}</span>
                              <span style={{
                                ...styles.sourceRelevance,
                                background: source.relevance > 80 ? 'rgba(22, 163, 74, 0.1)' : 
                                           source.relevance > 60 ? 'rgba(131, 177, 109, 0.1)' : 
                                           source.relevance > 40 ? 'rgba(234, 179, 8, 0.1)' : 'rgba(220, 38, 38, 0.1)',
                                color: source.relevance > 80 ? '#16a34a' : 
                                       source.relevance > 60 ? '#16a34a' : 
                                       source.relevance > 40 ? '#ca8a04' : '#dc2626',
                                padding: '0.125rem 0.5rem',
                                borderRadius: '4px',
                                fontWeight: '600'
                              }}>
                                {source.relevance}%
                              </span>
                            </div>
                            <div style={styles.sourceMetadata}>
                              {source.sheet && <span style={styles.metadataTag}>📋 {source.sheet}</span>}
                              {source.functional_area && <span style={styles.metadataTag}>📁 {source.functional_area}</span>}
                            </div>
                            <p style={styles.sourcePreview}>{source.preview}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                
                <div style={{
                  ...styles.messageTime,
                  textAlign: message.role === 'user' ? 'right' : 'left'
                }}>
                  {formatTimestamp(message.timestamp)}
                  {message.models_used && message.models_used.length > 0 && (
                    <span style={{ marginLeft: '0.5rem' }}>
                      {message.models_used.map((model, idx) => {
                        const badge = getModelBadge(model)
                        return (
                          <span key={idx} style={{ marginLeft: '0.25rem' }} title={model}>
                            {badge.icon}
                          </span>
                        )
                      })}
                      {message.sanitized && (
                        <span style={{ marginLeft: '0.25rem' }} title="PII Sanitized">
                          🔒
                        </span>
                      )}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        
        {/* Loading Indicator */}
        {loading && (
          <div style={styles.messageRow}>
            <div style={{ ...styles.avatar, ...styles.avatarAssistant }}>🤖</div>
            <div style={styles.loadingBubble}>
              ⏳ Searching documents and generating response...
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Error Banner */}
      {error && (
        <div style={styles.errorBanner}>
          ⚠️ {error}
          <button 
            onClick={() => setError(null)}
            style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Input Area */}
      <div style={styles.inputArea}>
        <div style={styles.inputRow}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={selectedProject 
              ? `Ask about ${selectedProject} documents...` 
              : "Ask a question about your documents..."
            }
            style={styles.textarea}
            rows={2}
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={isDisabled}
            style={{
              ...styles.sendButton,
              ...(isDisabled ? styles.sendButtonDisabled : {})
            }}
          >
            {loading ? '⏳' : '📤'}
          </button>
        </div>
        <p style={styles.inputHint}>
          Press Enter to send • Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
