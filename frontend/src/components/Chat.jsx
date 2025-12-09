/**
 * Chat.jsx - Enhanced with Scope Selection & Feedback
 * 
 * UPDATED: Now uses ProjectContext for project selection.
 * No internal project selector - uses header context bar.
 * 
 * FEATURES:
 * - Scope selector: project, global, all
 * - Thumbs up/down feedback buttons
 * - Routing indicator showing what was searched
 * - Learning integration
 * - Personas
 * - Excel export
 * - PII indicators
 * - Source citations
 */

import { useState, useEffect, useRef } from 'react'
import api from '../services/api'
import { useProject } from '../context/ProjectContext'
import PersonaSwitcher from './PersonaSwitcher'
import PersonaCreator from './PersonaCreator'

export default function Chat({ 
  functionalAreas = [],
}) {
  // Use project from context
  const { activeProject, projectName } = useProject()
  
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedSources, setExpandedSources] = useState({})
  const [modelInfo, setModelInfo] = useState(null)
  const messagesEndRef = useRef(null)
  const messagesAreaRef = useRef(null)
  
  // Scope state - project, global, all
  const [scope, setScope] = useState('project')
  
  // Persona state
  const [currentPersona, setCurrentPersona] = useState({
    id: 'bessie',
    name: 'Bessie',
    icon: '🐮',
    description: 'Your friendly payroll expert'
  })
  const [showPersonaCreator, setShowPersonaCreator] = useState(false)

  // Scope labels
  const scopeLabels = {
    project: '📁 This Project',
    global: '🌐 Global',
    all: '📊 All Data'
  }

  useEffect(() => {
    loadModelInfo()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Set up global function for opening persona creator
  useEffect(() => {
    window.openPersonaCreator = () => setShowPersonaCreator(true)
    return () => {
      delete window.openPersonaCreator
    }
  }, [])

  const scrollToBottom = () => {
    if (messagesAreaRef.current) {
      messagesAreaRef.current.scrollTop = messagesAreaRef.current.scrollHeight
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

  // Submit feedback
  const submitFeedback = async (jobId, feedbackType, messageContent, responseContent) => {
    try {
      await api.post('/chat/feedback', {
        job_id: jobId,
        feedback: feedbackType,
        message: messageContent,
        response: responseContent
      })
      console.log(`✅ Feedback submitted: ${feedbackType}`)
    } catch (err) {
      console.error('Failed to submit feedback:', err)
    }
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

    // Add placeholder message for status updates
    const tempId = `temp-${Date.now()}`
    const statusMessage = {
      role: 'assistant',
      content: '🔵 Starting...',
      isStatus: true,
      progress: 0,
      timestamp: new Date().toISOString(),
      tempId
    }
    setMessages(prev => [...prev, statusMessage])

    try {
      // Start the chat job - use project from context
      const startResponse = await api.post('/chat/start', {
        message: userMessage.content,
        project: projectName || null,
        max_results: 50,
        persona: currentPersona?.id || 'bessie',
        scope: scope
      })

      const { job_id } = startResponse.data

      // Poll for status updates
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await api.get(`/chat/status/${job_id}`)
          const jobStatus = statusResponse.data

          // Update status message
          setMessages(prev => prev.map(msg =>
            msg.tempId === tempId
              ? {
                  ...msg,
                  content: jobStatus.current_step,
                  progress: jobStatus.progress
                }
              : msg
          ))

          // Check if complete
          if (jobStatus.status === 'complete') {
            clearInterval(pollInterval)

            // Replace status message with final response
            const finalMessage = {
              role: 'assistant',
              content: jobStatus.response,
              sources: jobStatus.sources || [],
              chunks_found: jobStatus.chunks_found || 0,
              models_used: jobStatus.models_used || [],
              query_type: jobStatus.query_type || 'unknown',
              sanitized: jobStatus.sanitized || false,
              routing_info: jobStatus.routing_info || null,
              scope: jobStatus.scope || scope,
              pii_redacted: jobStatus.pii_redacted || false,
              job_id: job_id,
              userQuery: userMessage.content,
              timestamp: new Date().toISOString(),
              feedbackGiven: null
            }

            setMessages(prev => prev.map(msg =>
              msg.tempId === tempId ? finalMessage : msg
            ))
            setLoading(false)
          }

          // Check if failed
          if (jobStatus.status === 'failed') {
            clearInterval(pollInterval)
            setMessages(prev => prev.map(msg =>
              msg.tempId === tempId
                ? { ...msg, content: '❌ ' + (jobStatus.error || 'Request failed'), error: true }
                : msg
            ))
            setLoading(false)
          }
        } catch (pollErr) {
          console.error('Poll error:', pollErr)
        }
      }, 500)

      // Timeout after 2 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        if (loading) {
          setMessages(prev => prev.map(msg =>
            msg.tempId === tempId
              ? { ...msg, content: '⚠️ Request timed out', error: true }
              : msg
          ))
          setLoading(false)
        }
      }, 120000)

    } catch (err) {
      console.error('Chat error:', err)
      setMessages(prev => prev.map(msg =>
        msg.tempId === tempId
          ? { ...msg, content: '❌ ' + (err.response?.data?.detail || err.message || 'Failed to send'), error: true }
          : msg
      ))
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
    setError(null)
  }

  // Handle feedback click
  const handleFeedback = (messageIndex, feedbackType) => {
    const message = messages[messageIndex]
    if (message && message.job_id) {
      submitFeedback(message.job_id, feedbackType, message.userQuery, message.content)
      
      // Update message to show feedback was given
      setMessages(prev => prev.map((msg, idx) => 
        idx === messageIndex ? { ...msg, feedbackGiven: feedbackType } : msg
      ))
    }
  }

  // Check if send should be disabled
  const isDisabled = loading || (!input.trim()) || (scope === 'project' && !activeProject)

  const styles = {
    container: {
      height: '70vh',
      minHeight: '500px',
      display: 'flex',
      flexDirection: 'column',
      background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.02) 0%, rgba(147, 171, 217, 0.02) 100%)',
      borderRadius: '16px',
      boxShadow: '0 4px 24px rgba(42, 52, 65, 0.08)',
      overflow: 'hidden'
    },
    header: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '1rem 1.5rem',
      background: 'white',
      borderRadius: '16px 16px 0 0',
      borderBottom: '1px solid #e1e8ed',
      flexWrap: 'wrap',
      gap: '0.75rem'
    },
    headerControls: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      flexWrap: 'wrap'
    },
    scopeSelect: {
      padding: '0.5rem 0.75rem',
      fontSize: '0.8rem',
      border: '1px solid #e1e8ed',
      borderRadius: '8px',
      background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.1))',
      cursor: 'pointer',
      outline: 'none',
      color: '#2a3441',
      fontWeight: '500'
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
    routingBadge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.25rem',
      padding: '0.25rem 0.5rem',
      background: 'rgba(59, 130, 246, 0.1)',
      color: '#3b82f6',
      fontSize: '0.7rem',
      borderRadius: '4px',
      marginTop: '0.5rem'
    },
    sourcesSection: {
      marginTop: '1rem',
      paddingTop: '0.75rem',
      borderTop: '1px solid #e1e8ed'
    },
    sourcesHeader: {
      fontSize: '0.8rem',
      color: '#5f6c7b',
      marginBottom: '0.5rem',
      fontWeight: '600'
    },
    sourcesList: {
      display: 'flex',
      flexDirection: 'column',
      gap: '0.5rem'
    },
    sourceItem: {
      padding: '0.5rem',
      background: '#f8fafc',
      borderRadius: '6px'
    },
    sourceHeader: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '0.25rem'
    },
    sourceFilename: {
      fontWeight: '600',
      fontSize: '0.8rem',
      color: '#2a3441'
    },
    sourceRelevance: {
      fontSize: '0.7rem'
    },
    sourceMetadata: {
      display: 'flex',
      gap: '0.5rem',
      flexWrap: 'wrap'
    },
    metadataTag: {
      fontSize: '0.7rem',
      color: '#5f6c7b',
      padding: '0.125rem 0.375rem',
      background: 'white',
      borderRadius: '4px'
    },
    feedbackButtons: {
      display: 'flex',
      gap: '0.5rem',
      marginTop: '0.75rem'
    },
    feedbackBtn: (isActive, type) => ({
      padding: '0.25rem 0.5rem',
      fontSize: '0.75rem',
      border: '1px solid #e1e8ed',
      borderRadius: '4px',
      background: isActive ? (type === 'positive' ? '#dcfce7' : '#fee2e2') : 'white',
      cursor: isActive ? 'default' : 'pointer',
      opacity: isActive ? 1 : 0.7
    }),
    inputArea: {
      padding: '1rem 1.5rem',
      background: 'white',
      borderTop: '1px solid #e1e8ed'
    },
    inputRow: {
      display: 'flex',
      gap: '0.75rem',
      alignItems: 'flex-end'
    },
    textarea: {
      flex: 1,
      padding: '0.75rem 1rem',
      fontSize: '0.95rem',
      border: '1px solid #e1e8ed',
      borderRadius: '10px',
      resize: 'none',
      outline: 'none',
      fontFamily: 'inherit',
      lineHeight: 1.5
    },
    sendButton: {
      padding: '0.75rem 1.25rem',
      fontSize: '1.25rem',
      background: 'linear-gradient(135deg, #83b16d 0%, #6b9956 100%)',
      color: 'white',
      border: 'none',
      borderRadius: '10px',
      cursor: 'pointer',
      transition: 'all 0.2s ease'
    },
    sendButtonDisabled: {
      opacity: 0.5,
      cursor: 'not-allowed'
    },
    inputHint: {
      fontSize: '0.75rem',
      color: '#9ca3af',
      marginTop: '0.5rem'
    },
    errorBanner: {
      display: 'flex',
      alignItems: 'center',
      padding: '0.75rem 1.5rem',
      background: '#fef2f2',
      color: '#dc2626',
      fontSize: '0.9rem'
    },
    loadingBubble: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '1rem',
      background: '#f0f4f7',
      borderRadius: '12px',
      color: '#5f6c7b'
    }
  }

  return (
    <div style={styles.container}>
      {/* Header - Persona + Scope + Controls */}
      <div style={styles.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {/* Persona Switcher */}
          <PersonaSwitcher 
            currentPersona={currentPersona?.id || 'bessie'}
            onPersonaChange={(persona) => setCurrentPersona(persona)}
          />
        </div>
        
        <div style={styles.headerControls}>
          {/* Scope Selector */}
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            style={styles.scopeSelect}
            title="Search scope"
          >
            <option value="project">📁 This Project</option>
            <option value="global">🌐 Global Knowledge</option>
            <option value="all">📊 All Projects</option>
          </select>

          {/* Model/Feature indicators */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem',
            padding: '0.25rem 0.75rem',
            background: 'rgba(131, 177, 109, 0.1)',
            borderRadius: '6px',
            fontSize: '0.65rem',
            color: '#5f6c7b'
          }}>
            <span title="Local LLM tried first">🏠 Local→</span>
            <span title="Claude fallback">🧠 Claude</span>
            <span style={{ color: '#d1d5db' }}>|</span>
            <span title="PII is redacted before sending to Claude">🔒 PII Safe</span>
          </div>

          <button onClick={clearChat} style={styles.clearButton}>
            🔄 Clear
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div ref={messagesAreaRef} style={styles.messagesArea}>
        {messages.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>💬</div>
            <p style={styles.emptyTitle}>Start a conversation</p>
            <p style={styles.emptyText}>
              {scope === 'project' && !activeProject
                ? 'Select a project from the header to search project data'
                : scope === 'project' && activeProject
                  ? `Ready to search ${activeProject.name}`
                  : scope === 'global'
                    ? 'Searching global knowledge base'
                    : 'Searching across all projects'}
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
                {message.role === 'user' ? '👤' : (currentPersona?.icon || '🐮')}
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
                  <div style={styles.messageContent}>
                    {message.content}
                    
                    {/* Progress bar for status messages */}
                    {message.isStatus && message.progress !== undefined && (
                      <div style={{
                        marginTop: '0.5rem',
                        width: '100%',
                        height: '4px',
                        background: 'rgba(131, 177, 109, 0.2)',
                        borderRadius: '2px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${message.progress}%`,
                          height: '100%',
                          background: 'linear-gradient(90deg, #83b16d, #6a9456)',
                          transition: 'width 0.3s ease'
                        }} />
                      </div>
                    )}
                  </div>
                  
                  {/* Routing indicator */}
                  {message.role === 'assistant' && message.routing_info && !message.isStatus && (
                    <div style={styles.routingBadge}>
                      🔍 {message.routing_info.route || 'hybrid'}
                      {message.routing_info.reasoning && message.routing_info.reasoning.length > 0 && (
                        <span style={{ marginLeft: '0.25rem', opacity: 0.7 }}>
                          ({message.routing_info.reasoning.slice(0, 2).join(', ')})
                        </span>
                      )}
                    </div>
                  )}
                  
                  {/* Sources Section */}
                  {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                    <div style={styles.sourcesSection}>
                      <div style={styles.sourcesHeader}>
                        📄 Sources Referenced
                      </div>
                      
                      <div style={styles.sourcesList}>
                        {(() => {
                          const grouped = message.sources.reduce((acc, source) => {
                            const key = source.filename || 'Unknown';
                            if (!acc[key]) {
                              acc[key] = {
                                filename: key,
                                functional_area: source.functional_area,
                                chunks: [],
                                maxRelevance: 0,
                                sheets: new Set(),
                                type: source.type
                              };
                            }
                            acc[key].chunks.push(source);
                            acc[key].maxRelevance = Math.max(acc[key].maxRelevance, source.relevance || 0);
                            if (source.sheet) acc[key].sheets.add(source.sheet);
                            return acc;
                          }, {});
                          
                          return Object.values(grouped).map((doc, idx) => (
                            <div key={idx} style={styles.sourceItem}>
                              <div style={styles.sourceHeader}>
                                <span style={styles.sourceFilename}>
                                  {doc.type === 'structured' ? '📊 ' : '📄 '}
                                  {doc.filename}
                                </span>
                                <span style={{
                                  ...styles.sourceRelevance,
                                  background: doc.maxRelevance > 80 ? 'rgba(22, 163, 74, 0.1)' : 
                                             doc.maxRelevance > 60 ? 'rgba(131, 177, 109, 0.1)' : 
                                             doc.maxRelevance > 40 ? 'rgba(234, 179, 8, 0.1)' : 'rgba(220, 38, 38, 0.1)',
                                  color: doc.maxRelevance > 80 ? '#16a34a' : 
                                         doc.maxRelevance > 60 ? '#16a34a' : 
                                         doc.maxRelevance > 40 ? '#ca8a04' : '#dc2626',
                                  padding: '0.125rem 0.5rem',
                                  borderRadius: '4px',
                                  fontWeight: '600'
                                }}>
                                  {Math.round(doc.maxRelevance)}% match
                                </span>
                              </div>
                              <div style={styles.sourceMetadata}>
                                <span style={styles.metadataTag}>
                                  {doc.type === 'structured' ? `📊 ${doc.chunks[0]?.rows || '?'} rows` : `📄 ${doc.chunks.length} section${doc.chunks.length > 1 ? 's' : ''}`}
                                </span>
                                {doc.functional_area && <span style={styles.metadataTag}>📁 {doc.functional_area}</span>}
                                {doc.sheets.size > 0 && <span style={styles.metadataTag}>📋 {doc.sheets.size} sheet{doc.sheets.size > 1 ? 's' : ''}</span>}
                              </div>
                            </div>
                          ));
                        })()}
                      </div>
                    </div>
                  )}
                  
                  {/* Download Button - for structured data */}
                  {message.role === 'assistant' && message.sources && message.sources.some(s => s.type === 'structured') && !message.isStatus && (
                    <button
                      onClick={async () => {
                        try {
                          const userQuery = messages[index - 1]?.content || 'data export';
                          
                          const response = await api.post('/chat/export-excel', {
                            query: userQuery,
                            project: projectName
                          }, {
                            responseType: 'blob'
                          });
                          
                          const blob = new Blob([response.data], { 
                            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
                          });
                          const url = window.URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `export_${new Date().toISOString().slice(0,10)}.xlsx`;
                          document.body.appendChild(a);
                          a.click();
                          window.URL.revokeObjectURL(url);
                          a.remove();
                        } catch (err) {
                          console.error('Export error:', err);
                          alert('Export failed. Please try again.');
                        }
                      }}
                      style={{
                        marginTop: '0.75rem',
                        padding: '0.5rem 1rem',
                        background: 'linear-gradient(135deg, #16a34a 0%, #22c55e 100%)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '0.8rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                      }}
                    >
                      📥 Download as Excel
                    </button>
                  )}

                  {/* Feedback Buttons */}
                  {message.role === 'assistant' && !message.isStatus && message.job_id && (
                    <div style={styles.feedbackButtons}>
                      <button
                        onClick={() => !message.feedbackGiven && handleFeedback(index, 'positive')}
                        style={styles.feedbackBtn(message.feedbackGiven === 'positive', 'positive')}
                        disabled={message.feedbackGiven}
                      >
                        👍 {message.feedbackGiven === 'positive' ? 'Thanks!' : 'Helpful'}
                      </button>
                      <button
                        onClick={() => !message.feedbackGiven && handleFeedback(index, 'negative')}
                        style={styles.feedbackBtn(message.feedbackGiven === 'negative', 'negative')}
                        disabled={message.feedbackGiven}
                      >
                        👎 {message.feedbackGiven === 'negative' ? 'Noted' : 'Not helpful'}
                      </button>
                    </div>
                  )}
                </div>
                
                <div style={styles.messageTime}>
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}
        
        {loading && messages[messages.length - 1]?.role !== 'assistant' && (
          <div style={styles.messageRow}>
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
            placeholder={
              scope === 'project' && !activeProject
                ? "Select a project to search..."
                : scope === 'global' 
                  ? "Ask about global knowledge..." 
                  : activeProject 
                    ? `Ask about ${activeProject.name}...` 
                    : "Ask a question..."
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
          Press Enter to send • Shift+Enter for new line • Scope: {scopeLabels[scope]}
        </p>
      </div>

      {/* Persona Creator Modal */}
      <PersonaCreator
        isOpen={showPersonaCreator}
        onClose={() => setShowPersonaCreator(false)}
        onPersonaCreated={(persona) => {
          setCurrentPersona({
            id: persona.name.toLowerCase().replace(/\s+/g, '_'),
            name: persona.name,
            icon: persona.icon || '🤖',
            description: persona.description
          })
          console.log(`✅ Created and switched to: ${persona.name}`)
        }}
      />
    </div>
  )
}
