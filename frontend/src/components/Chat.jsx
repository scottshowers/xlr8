/**
 * Chat.jsx - Intelligent Chat Interface
 * 
 * v14: Full theme conversion - inline styles, consistent sizing
 * 
 * Features:
 * - INTELLIGENT MODE: Three Truths synthesis, smart clarification, proactive insights
 * - Standard Mode: Original chat functionality
 * - Scope selector: project, global, all
 * - Thumbs up/down feedback
 * - Personas, Excel export, PII indicators
 */

import { useState, useEffect, useRef } from 'react'
import api from '../services/api'
import { useProject } from '../context/ProjectContext'
import { useTheme } from '../context/ThemeContext'
import PersonaSwitcher from '../components/PersonaSwitcher'
import PersonaCreator from '../components/PersonaCreator'
import { 
  Zap, Brain, Database, FileText, BookOpen, AlertTriangle, 
  CheckCircle, ChevronDown, ChevronRight, Lightbulb, Download,
  ThumbsUp, ThumbsDown, Copy, RefreshCw, Send, Trash2, Eye, EyeOff
} from 'lucide-react'

// Theme-aware colors - Mission Control palette
const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f0f2f5',
  card: dark ? '#242b3d' : '#ffffff',
  cardBorder: dark ? '#2d3548' : '#e2e8f0',
  text: dark ? '#e8eaed' : '#1a2332',
  textMuted: dark ? '#8b95a5' : '#64748b',
  textLight: dark ? '#5f6a7d' : '#94a3b8',
  primary: '#83b16d',
  primaryDark: '#6b9b5a',
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.1)',
  primaryBorder: 'rgba(131, 177, 109, 0.3)',
  accent: '#285390',
  accentLight: dark ? 'rgba(40, 83, 144, 0.15)' : 'rgba(40, 83, 144, 0.1)',
  warning: '#d97706',
  warningLight: dark ? 'rgba(217, 119, 6, 0.15)' : 'rgba(217, 119, 6, 0.1)',
  red: '#993c44',
  redLight: dark ? 'rgba(153, 60, 68, 0.15)' : 'rgba(153, 60, 68, 0.1)',
  success: '#10b981',
  successLight: dark ? 'rgba(16, 185, 129, 0.15)' : '#ecfdf5',
  divider: dark ? '#2d3548' : '#e2e8f0',
  inputBg: dark ? '#1a1f2e' : '#f8fafc',
  messageBg: dark ? '#2d3548' : '#f1f5f9',
  // Aliases for backward compatibility
  blue: '#285390',
  blueLight: dark ? 'rgba(40, 83, 144, 0.15)' : 'rgba(40, 83, 144, 0.1)',
  amber: '#d97706',
  amberLight: dark ? 'rgba(217, 119, 6, 0.15)' : 'rgba(217, 119, 6, 0.1)',
})

export default function Chat({ functionalAreas = [] }) {
  const { activeProject, projectName } = useProject()
  const { darkMode } = useTheme()
  const colors = getColors(darkMode)
  
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedSources, setExpandedSources] = useState({})
  const [modelInfo, setModelInfo] = useState(null)
  const messagesEndRef = useRef(null)
  const messagesAreaRef = useRef(null)
  
  // Scope state
  const [scope, setScope] = useState('project')
  
  // INTELLIGENT MODE
  const [intelligentMode, setIntelligentMode] = useState(true)
  const [sessionId, setSessionId] = useState(null)
  const [pendingClarification, setPendingClarification] = useState(null)
  const [learningStats, setLearningStats] = useState(null)
  
  // Experimental: Use new modular engine
  const [useEngineV2, setUseEngineV2] = useState(false)
  
  // Persona state
  const [debugInfo, setDebugInfo] = useState(null)
  
  // Persona state
  const [currentPersona, setCurrentPersona] = useState({
    id: 'bessie',
    name: 'Bessie',
    icon: '🐮',
    description: 'Your friendly payroll expert'
  })
  const [showPersonaCreator, setShowPersonaCreator] = useState(false)

  const scopeLabels = {
    project: '📁 Project',
    global: '🌐 Global',
    all: '📊 All'
  }

  useEffect(() => {
    loadModelInfo()
    loadLearningStats()
    setSessionId(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    window.openPersonaCreator = () => setShowPersonaCreator(true)
    return () => { delete window.openPersonaCreator }
  }, [])

  const scrollToBottom = () => {
    if (messagesAreaRef.current) {
      messagesAreaRef.current.scrollTop = messagesAreaRef.current.scrollHeight
    }
  }

  const loadLearningStats = async () => {
    try {
      const response = await api.get('/chat/intelligent/learning/stats')
      setLearningStats(response.data)
    } catch (err) {
      console.log('Learning stats not available')
    }
  }

  const resetPreferences = async (resetType = 'session') => {
    try {
      const response = await api.post('/chat/unified/reset-preferences', {
        session_id: sessionId,
        project: projectName || null,
        reset_type: resetType
      })
      
      if (response.data.success) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          type: 'system',
          content: resetType === 'learned' 
            ? '🔄 Preferences cleared. I\'ll ask clarifying questions again.'
            : '🔄 Session filters reset. Ask your question again.',
          timestamp: new Date().toISOString()
        }])
      }
      
      return response.data
    } catch (err) {
      console.error('Failed to reset preferences:', err)
      return { success: false, message: err.message }
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
    setExpandedSources(prev => ({ ...prev, [messageIndex]: !prev[messageIndex] }))
  }

  const submitFeedback = async (jobId, feedbackType, messageContent, responseContent) => {
    try {
      await api.post('/chat/unified/feedback', {
        job_id: jobId,
        feedback: feedbackType,
        message: messageContent,
        response: responseContent
      })
    } catch (err) {
      console.error('Failed to submit feedback:', err)
    }
  }

  // INTELLIGENT MESSAGE HANDLER
  const sendIntelligentMessage = async (clarifications = null) => {
    const messageText = clarifications ? pendingClarification?.originalQuestion : input.trim()
    if (!messageText) return

    if (!clarifications) {
      const userMessage = {
        role: 'user',
        content: messageText,
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, userMessage])
      setInput('')
    }
    
    setLoading(true)
    setPendingClarification(null)

    try {
      const response = await api.post('/chat/unified', {
        message: messageText,
        project: projectName || null,
        persona: currentPersona?.id || 'bessie',
        scope: scope,
        session_id: sessionId,
        clarifications: clarifications,
        include_citations: true,
        include_quality_alerts: true,
        include_follow_ups: true,
        use_engine_v2: useEngineV2
      })

      const data = response.data
      
      // DEBUG - shows on screen
      const debugData = {
        needs_clarification: data.needs_clarification,
        has_answer: !!data.answer,
        answer_length: data.answer?.length,
        answer_preview: data.answer?.substring(0, 200),
        from_reality: data.from_reality?.length || 0,
        from_intent: data.from_intent?.length || 0,
        timestamp: new Date().toISOString()
      }
      console.log('[CHAT DEBUG] Response:', debugData)
      setDebugInfo(debugData)

      if (data.export) {
        const { filename, data: base64Data, mime_type } = data.export
        const link = document.createElement('a')
        link.href = `data:${mime_type};base64,${base64Data}`
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }

      if (data.needs_clarification) {
        setPendingClarification({
          originalQuestion: messageText,
          questions: data.clarification_questions,
          sessionId: data.session_id
        })
        
        setMessages(prev => [...prev, {
          role: 'assistant',
          type: 'clarification',
          questions: data.clarification_questions,
          originalQuestion: messageText,
          timestamp: new Date().toISOString()
        }])
      } else {
        // Remove any pending clarification messages when we get an answer
        console.log('[CHAT DEBUG] Adding intelligent response, removing clarification')
        setMessages(prev => {
          // Filter out clarification messages for this question
          const filtered = prev.filter(m => m.type !== 'clarification')
          return [...filtered, {
            role: 'assistant',
            type: 'intelligent',
            content: data.answer,
            confidence: data.confidence,
            from_reality: data.from_reality || [],
            from_intent: data.from_intent || [],
            from_best_practice: data.from_best_practice || [],
            conflicts: data.conflicts || [],
            insights: data.insights || [],
            reasoning: data.reasoning || [],
            structured_output: data.structured_output,
            auto_applied_note: data.auto_applied_note || null,
            auto_applied_facts: data.auto_applied_facts || null,
            can_reset_preferences: data.can_reset_preferences || false,
            quality_alerts: data.quality_alerts || null,
            follow_up_suggestions: data.follow_up_suggestions || [],
            citations: data.citations || null,
            export: data.export || null,
            timestamp: new Date().toISOString()
          }]
        })
      }

      if (data.session_id) {
        setSessionId(data.session_id)
      }

    } catch (err) {
      console.error('Intelligent chat error:', err)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '❌ ' + (err.response?.data?.detail || err.message || 'Failed to get intelligent response'),
        error: true,
        timestamp: new Date().toISOString()
      }])
    } finally {
      setLoading(false)
    }
  }

  const sendMessage = () => {
    // Always use intelligent mode - standard mode endpoints don't exist
    sendIntelligentMessage()
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
    setPendingClarification(null)
  }

  const handleFeedback = (messageIndex, feedbackType) => {
    setMessages(prev => prev.map((msg, idx) => 
      idx === messageIndex ? { ...msg, feedbackGiven: feedbackType } : msg
    ))
    
    const message = messages[messageIndex]
    if (message?.type === 'intelligent' && sessionId) {
      api.post('/chat/intelligent/feedback', {
        session_id: sessionId,
        message_index: messageIndex,
        feedback: feedbackType,
        question: messages[messageIndex - 1]?.content || ''
      }).catch(console.error)
    } else if (message?.job_id) {
      submitFeedback(message.job_id, feedbackType, message.userQuery, message.content)
    }
  }

  const isDisabled = loading || (!input.trim()) || (scope === 'project' && !activeProject)

  return (
    <div style={{
      height: '75vh',
      minHeight: 500,
      display: 'flex',
      flexDirection: 'column',
      background: colors.card,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.75rem 1rem',
        background: colors.card,
        borderBottom: `1px solid ${colors.divider}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <PersonaSwitcher 
            currentPersona={currentPersona}
            onPersonaChange={setCurrentPersona}
            onCreateNew={() => setShowPersonaCreator(true)}
          />
          
          {/* Always using Intelligent Mode - indicator badge */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.375rem 0.75rem',
              borderRadius: 8,
              fontSize: '0.85rem',
              fontWeight: 500,
              background: colors.primary,
              color: 'white',
            }}
          >
            <Brain size={16} />
            Intelligent
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {/* Engine V2 Toggle (experimental) */}
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
              padding: '0.375rem 0.5rem',
              fontSize: '0.75rem',
              borderRadius: 6,
              cursor: 'pointer',
              background: useEngineV2 ? colors.successLight : colors.inputBg,
              border: `1px solid ${useEngineV2 ? colors.success : colors.divider}`,
              color: useEngineV2 ? colors.success : colors.textMuted,
            }}
            title="Experimental: Use new modular intelligence engine"
          >
            <input
              type="checkbox"
              checked={useEngineV2}
              onChange={(e) => setUseEngineV2(e.target.checked)}
              style={{ margin: 0, cursor: 'pointer' }}
            />
            V2
          </label>
          
          {/* Scope Selector */}
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            style={{
              padding: '0.375rem 0.75rem',
              fontSize: '0.85rem',
              border: `1px solid ${colors.divider}`,
              borderRadius: 8,
              background: colors.card,
              color: colors.text,
            }}
          >
            {Object.entries(scopeLabels).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>

          <button
            onClick={clearChat}
            style={{
              padding: '0.5rem',
              background: 'transparent',
              border: 'none',
              borderRadius: 8,
              cursor: 'pointer',
              color: colors.textMuted,
            }}
            title="Clear chat"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>

      {/* Intelligent Mode Banner */}
      {intelligentMode && (
        <div style={{
          padding: '0.5rem 1rem',
          background: colors.primaryLight,
          borderBottom: `1px solid ${colors.divider}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.85rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Zap size={16} style={{ color: colors.primary }} />
            <span style={{ color: colors.primary }}>
              <strong>Intelligent Mode:</strong> Synthesizes data + documents + reference library
            </span>
          </div>
          {learningStats?.available && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.75rem', color: colors.primary }}>
              <span title="Learned query patterns">🧠 {learningStats.learned_queries || 0} patterns</span>
              <span title="Feedback records">👍 {learningStats.feedback_records || 0} feedback</span>
            </div>
          )}
        </div>
      )}

      {/* DEBUG PANEL - Remove after fixing */}
      {debugInfo && (
        <div style={{
          padding: '0.5rem 1rem',
          background: '#ffe4e4',
          borderBottom: '2px solid #ff6b6b',
          fontSize: '0.75rem',
          fontFamily: 'monospace',
        }}>
          <strong>🔧 DEBUG:</strong> needs_clarification={String(debugInfo.needs_clarification)} | 
          has_answer={String(debugInfo.has_answer)} | 
          len={debugInfo.answer_length} | 
          reality={debugInfo.from_reality} | 
          intent={debugInfo.from_intent} |
          preview: "{debugInfo.answer_preview?.substring(0, 60)}..."
          <button 
            onClick={() => setDebugInfo(null)} 
            style={{ marginLeft: '1rem', cursor: 'pointer' }}
          >
            ✕ Close
          </button>
        </div>
      )}

      {/* Messages Area */}
      <div 
        ref={messagesAreaRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1rem',
          background: colors.messageBg,
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        {messages.length === 0 ? (
          <div style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: colors.textMuted,
          }}>
            <div style={{ fontSize: '3.5rem', marginBottom: '1rem', opacity: 0.5 }}>
              {intelligentMode ? '🧠' : '💬'}
            </div>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: colors.text, marginBottom: '0.5rem' }}>
              {intelligentMode ? 'Intelligent Analysis Ready' : 'Start a Conversation'}
            </h3>
            <p style={{ fontSize: '0.85rem', textAlign: 'center', maxWidth: 400 }}>
              {intelligentMode 
                ? 'Ask questions and I\'ll synthesize answers from your data, documents, and reference library.'
                : 'Ask questions about your uploaded data and documents.'
              }
            </p>
            {intelligentMode && (
              <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem', fontSize: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: colors.blue }}>
                  <Database size={14} /> Data
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: colors.primary }}>
                  <FileText size={14} /> Docs
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: colors.amber }}>
                  <BookOpen size={14} /> Reference
                </div>
              </div>
            )}
          </div>
        ) : (
          messages.map((message, index) => (
            <MessageBubble
              key={index}
              message={message}
              index={index}
              persona={currentPersona}
              expandedSources={expandedSources}
              toggleSources={toggleSources}
              onFeedback={handleFeedback}
              onClarificationSubmit={(answers) => sendIntelligentMessage(answers)}
              onResetPreferences={resetPreferences}
              colors={colors}
            />
          ))
        )}
        
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: colors.textMuted, fontSize: '0.85rem' }}>
            <RefreshCw size={16} style={{ animation: 'spin 1s linear infinite' }} />
            {intelligentMode ? 'Analyzing sources...' : 'Processing...'}
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={{
        padding: '1rem',
        background: colors.card,
        borderTop: `1px solid ${colors.divider}`,
      }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              scope === 'project' && !activeProject 
                ? "Select a project first..." 
                : intelligentMode
                  ? "Ask anything - I'll synthesize from all sources..."
                  : "Type your question..."
            }
            style={{
              flex: 1,
              padding: '0.75rem 1rem',
              border: `1px solid ${colors.divider}`,
              borderRadius: 12,
              resize: 'none',
              fontSize: '0.85rem',
              background: colors.card,
              color: colors.text,
              outline: 'none',
            }}
            rows={2}
            disabled={scope === 'project' && !activeProject}
          />
          <button
            onClick={sendMessage}
            disabled={isDisabled}
            style={{
              padding: '0.75rem 1.25rem',
              borderRadius: 12,
              fontWeight: 500,
              fontSize: '0.85rem',
              border: 'none',
              cursor: isDisabled ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              transition: 'all 0.15s ease',
              ...(isDisabled ? {
                background: colors.inputBg,
                color: colors.textLight,
              } : {
                background: colors.primary,
                color: 'white',
              })
            }}
          >
            <Send size={18} />
            {intelligentMode ? 'Analyze' : 'Send'}
          </button>
        </div>
      </div>

      {/* Persona Creator Modal */}
      {showPersonaCreator && (
        <PersonaCreator
          onClose={() => setShowPersonaCreator(false)}
          onSave={(newPersona) => {
            setCurrentPersona(newPersona)
            setShowPersonaCreator(false)
          }}
        />
      )}
      
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}


// MESSAGE BUBBLE COMPONENT
function MessageBubble({ message, index, persona, expandedSources, toggleSources, onFeedback, onClarificationSubmit, onResetPreferences, colors }) {
  const isUser = message.role === 'user'
  
  // System message
  if (message.type === 'system') {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', margin: '0.5rem 0' }}>
        <div style={{
          padding: '0.5rem 1rem',
          background: colors.inputBg,
          color: colors.textMuted,
          fontSize: '0.85rem',
          borderRadius: 20,
        }}>
          {message.content}
        </div>
      </div>
    )
  }
  
  // Clarification message
  if (message.type === 'clarification') {
    return <ClarificationCard questions={message.questions} originalQuestion={message.originalQuestion} onSubmit={onClarificationSubmit} colors={colors} />
  }
  
  // Intelligent response
  if (message.type === 'intelligent') {
    return <IntelligentResponse message={message} index={index} onFeedback={onFeedback} onResetPreferences={onResetPreferences} colors={colors} />
  }
  
  // Standard message
  return (
    <div style={{ display: 'flex', gap: '0.75rem', flexDirection: isUser ? 'row-reverse' : 'row' }}>
      {/* Avatar */}
      <div style={{
        width: 36,
        height: 36,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        fontSize: '1rem',
        ...(isUser ? {
          background: `linear-gradient(135deg, ${colors.primary}, ${colors.primaryDark})`,
          color: 'white'
        } : {
          background: colors.primaryLight,
          color: colors.primary
        })
      }}>
        {isUser ? '👤' : persona?.icon || '🐮'}
      </div>
      
      {/* Bubble */}
      <div style={{
        maxWidth: '75%',
        borderRadius: 12,
        padding: '0.75rem 1rem',
        ...(isUser ? {
          background: `linear-gradient(135deg, ${colors.primary}, ${colors.primaryDark})`,
          color: 'white',
          borderBottomRightRadius: 4,
        } : message.error ? {
          background: colors.redLight,
          border: `1px solid ${colors.red}40`,
          color: colors.red,
          borderBottomLeftRadius: 4,
        } : {
          background: colors.card,
          border: `1px solid ${colors.divider}`,
          borderBottomLeftRadius: 4,
        })
      }}>
        <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', lineHeight: 1.6, color: isUser ? 'white' : colors.text }}>
          {message.content}
        </div>
        
        {/* Sources */}
        {message.sources?.length > 0 && (
          <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: `1px solid ${colors.divider}` }}>
            <button 
              onClick={() => toggleSources(index)}
              style={{
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                color: colors.primary,
                background: 'none',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              {expandedSources[index] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              {message.sources.length} sources
            </button>
            {expandedSources[index] && (
              <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                {message.sources.slice(0, 5).map((src, i) => (
                  <div key={i} style={{ fontSize: '0.75rem', color: colors.textMuted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    📄 {src.filename || src.source || 'Unknown'}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* Feedback */}
        {!isUser && !message.error && !message.isStatus && message.type === 'standard' && (
          <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: `1px solid ${colors.divider}`, display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => onFeedback(index, 'positive')}
              style={{
                padding: '0.25rem',
                borderRadius: 4,
                background: message.feedbackGiven === 'positive' ? colors.primaryLight : 'transparent',
                color: message.feedbackGiven === 'positive' ? colors.primary : colors.textLight,
                border: 'none',
                cursor: 'pointer',
              }}
            >
              <ThumbsUp size={14} />
            </button>
            <button
              onClick={() => onFeedback(index, 'negative')}
              style={{
                padding: '0.25rem',
                borderRadius: 4,
                background: message.feedbackGiven === 'negative' ? colors.redLight : 'transparent',
                color: message.feedbackGiven === 'negative' ? colors.red : colors.textLight,
                border: 'none',
                cursor: 'pointer',
              }}
            >
              <ThumbsDown size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}


// CLARIFICATION CARD
function ClarificationCard({ questions, originalQuestion, onSubmit, colors }) {
  const [answers, setAnswers] = useState({})
  
  const handleChange = (questionId, value, type) => {
    if (type === 'checkbox') {
      setAnswers(prev => ({
        ...prev,
        [questionId]: prev[questionId]?.includes(value)
          ? prev[questionId].filter(v => v !== value)
          : [...(prev[questionId] || []), value]
      }))
    } else {
      setAnswers(prev => ({ ...prev, [questionId]: value }))
    }
  }
  
  useEffect(() => {
    const defaults = {}
    questions?.forEach(q => {
      const defaultOpt = q.options?.find(o => o.default)
      if (defaultOpt) {
        if (q.type === 'checkbox') {
          defaults[q.id] = [defaultOpt.id]
        } else {
          defaults[q.id] = defaultOpt.id
        }
      }
    })
    setAnswers(defaults)
  }, [questions])
  
  return (
    <div style={{
      borderRadius: 12,
      padding: '1.25rem',
      maxWidth: 480,
      background: colors.primaryLight,
      border: `1px solid ${colors.primaryBorder}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
        <div style={{
          width: 40,
          height: 40,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: colors.card,
        }}>
          <Brain size={20} style={{ color: colors.primary }} />
        </div>
        <div>
          <h3 style={{ fontWeight: 600, color: colors.primary, margin: 0, fontSize: '0.9rem' }}>Let me clarify</h3>
          <p style={{ fontSize: '0.85rem', color: colors.primary, margin: 0, opacity: 0.8 }}>Quick questions for a better answer</p>
        </div>
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {questions?.map((q) => (
          <div key={q.id} style={{
            background: colors.card,
            borderRadius: 8,
            padding: '1rem',
            border: `1px solid ${colors.primaryBorder}`,
          }}>
            <div style={{ fontWeight: 500, color: colors.text, marginBottom: '0.75rem', fontSize: '0.85rem' }}>{q.question}</div>
            
            {q.type === 'radio' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {q.options?.map((opt) => (
                  <label key={opt.id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name={q.id}
                      checked={answers[q.id] === opt.id}
                      onChange={() => handleChange(q.id, opt.id, 'radio')}
                      style={{ accentColor: colors.primary }}
                    />
                    <span style={{ fontSize: '0.85rem', color: colors.text }}>{opt.label}</span>
                  </label>
                ))}
              </div>
            )}
            
            {q.type === 'checkbox' && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                {q.options?.map((opt) => (
                  <label key={opt.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={answers[q.id]?.includes(opt.id)}
                      onChange={() => handleChange(q.id, opt.id, 'checkbox')}
                      style={{ accentColor: colors.primary }}
                    />
                    <span style={{ fontSize: '0.85rem', color: colors.text }}>{opt.label}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div style={{ marginTop: '1.25rem', display: 'flex', gap: '0.75rem' }}>
        <button
          onClick={() => onSubmit(answers)}
          style={{
            padding: '0.5rem 1.25rem',
            background: colors.primary,
            color: 'white',
            border: 'none',
            borderRadius: 8,
            fontWeight: 500,
            fontSize: '0.85rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <Zap size={16} /> Get Answer
        </button>
        <button
          onClick={() => onSubmit(null)}
          style={{
            padding: '0.5rem 1rem',
            background: 'transparent',
            color: colors.textMuted,
            border: 'none',
            borderRadius: 8,
            fontSize: '0.85rem',
            cursor: 'pointer',
          }}
        >
          Skip
        </button>
      </div>
    </div>
  )
}


// INTELLIGENT RESPONSE COMPONENT
function IntelligentResponse({ message, index, onFeedback, onResetPreferences, colors }) {
  const [showSources, setShowSources] = useState(false)
  const [expandedSection, setExpandedSection] = useState(null)
  const [resetting, setResetting] = useState(false)
  
  const hasReality = message.from_reality?.length > 0
  const hasIntent = message.from_intent?.length > 0
  const hasBestPractice = message.from_best_practice?.length > 0
  const hasConflicts = message.conflicts?.length > 0
  const hasInsights = message.insights?.length > 0
  
  const handleReset = async (resetType) => {
    setResetting(true)
    try {
      await onResetPreferences(resetType)
    } finally {
      setResetting(false)
    }
  }
  
  return (
    <div style={{
      background: colors.card,
      borderRadius: 12,
      border: `1px solid ${colors.divider}`,
      overflow: 'hidden',
      maxWidth: 640,
    }}>
      {/* Auto-Applied Banner */}
      {message.auto_applied_note && message.can_reset_preferences && (
        <div style={{
          padding: '0.5rem 1rem',
          background: colors.amberLight,
          borderBottom: `1px solid ${colors.amber}40`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <span style={{ fontSize: '0.85rem', color: colors.amber }}>{message.auto_applied_note}</span>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => handleReset('session')}
              disabled={resetting}
              style={{ fontSize: '0.75rem', color: colors.amber, background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
            >
              {resetting ? '...' : 'Reset'}
            </button>
            <button
              onClick={() => handleReset('learned')}
              disabled={resetting}
              style={{ fontSize: '0.75rem', color: colors.red, background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
            >
              {resetting ? '...' : 'Forget'}
            </button>
          </div>
        </div>
      )}
      
      {/* Confidence Header */}
      <div style={{
        padding: '0.5rem 1rem',
        background: colors.primaryLight,
        borderBottom: `1px solid ${colors.divider}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Brain size={16} style={{ color: colors.primary }} />
          <span style={{ fontSize: '0.85rem', fontWeight: 500, color: colors.primary }}>Intelligent Analysis</span>
          {message.used_learning && (
            <span style={{
              padding: '0.125rem 0.5rem',
              background: colors.primaryLight,
              color: colors.primary,
              fontSize: '0.75rem',
              borderRadius: 12,
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}>
              🧠 Learned
            </span>
          )}
        </div>
        <div style={{
          padding: '0.125rem 0.5rem',
          borderRadius: 4,
          fontSize: '0.75rem',
          fontWeight: 500,
          background: message.confidence >= 0.8 ? colors.primaryLight : message.confidence >= 0.6 ? colors.blueLight : colors.amberLight,
          color: message.confidence >= 0.8 ? colors.primary : message.confidence >= 0.6 ? colors.blue : colors.amber,
        }}>
          {Math.round((message.confidence || 0) * 100)}% confidence
        </div>
      </div>
      
      {/* Main Answer */}
      <div style={{ padding: '1rem' }}>
        <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', lineHeight: 1.6, color: colors.text }}>
          {message.content}
        </div>
        
        {/* Export Button */}
        {message.export && (
          <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: `1px solid ${colors.divider}` }}>
            <button
              onClick={() => {
                const { filename, data, mime_type } = message.export
                const link = document.createElement('a')
                link.href = `data:${mime_type};base64,${data}`
                link.download = filename
                document.body.appendChild(link)
                link.click()
                document.body.removeChild(link)
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 0.75rem',
                borderRadius: 8,
                fontSize: '0.85rem',
                fontWeight: 500,
                background: colors.primaryLight,
                color: colors.primary,
                border: `1px solid ${colors.primary}40`,
                cursor: 'pointer',
              }}
            >
              <Download size={16} />
              Download {message.export.filename}
            </button>
          </div>
        )}
      </div>
      
      {/* Insights */}
      {hasInsights && (
        <div style={{
          margin: '0 1rem 1rem',
          background: colors.amberLight,
          border: `1px solid ${colors.amber}40`,
          borderRadius: 8,
          padding: '0.75rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <Lightbulb size={16} style={{ color: colors.amber }} />
            <span style={{ fontWeight: 500, color: colors.amber, fontSize: '0.85rem' }}>Proactive Insights</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            {message.insights.map((insight, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.85rem' }}>
                <span style={{ flexShrink: 0, color: insight.severity === 'high' ? colors.red : colors.amber }}>
                  {insight.severity === 'high' ? '🔴' : '🟡'}
                </span>
                <span style={{ color: colors.text }}>
                  <strong>{insight.title}:</strong> {insight.description}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Conflicts */}
      {hasConflicts && (
        <div style={{
          margin: '0 1rem 1rem',
          background: colors.redLight,
          border: `1px solid ${colors.red}40`,
          borderRadius: 8,
          padding: '0.75rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <AlertTriangle size={16} style={{ color: colors.red }} />
            <span style={{ fontWeight: 500, color: colors.red, fontSize: '0.85rem' }}>Conflicts Detected</span>
          </div>
          {message.conflicts.map((conflict, i) => (
            <div key={i} style={{ fontSize: '0.85rem', color: colors.text, marginBottom: '0.5rem' }}>
              <div>{conflict.description}</div>
              <div style={{ color: colors.red, fontSize: '0.75rem', marginTop: '0.25rem' }}>
                💡 Recommendation: {conflict.recommendation}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Sources Toggle */}
      {(hasReality || hasIntent || hasBestPractice) && (
        <div style={{ borderTop: `1px solid ${colors.divider}` }}>
          <button
            onClick={() => setShowSources(!showSources)}
            style={{
              width: '100%',
              padding: '0.5rem 1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            <span style={{ color: colors.textMuted }}>Sources of Truth</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {hasReality && <span style={{ color: colors.blue, fontSize: '0.75rem' }}>📊 Data</span>}
              {hasIntent && <span style={{ color: colors.primary, fontSize: '0.75rem' }}>📄 Docs</span>}
              {hasBestPractice && <span style={{ color: colors.amber, fontSize: '0.75rem' }}>📘 Reference</span>}
              {showSources ? <ChevronDown size={16} style={{ color: colors.textMuted }} /> : <ChevronRight size={16} style={{ color: colors.textMuted }} />}
            </div>
          </button>
          
          {showSources && (
            <div style={{ padding: '0 1rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {hasReality && (
                <SourceSection
                  title="Customer Data"
                  icon={<Database size={14} style={{ color: colors.blue }} />}
                  colorScheme="blue"
                  items={message.from_reality}
                  expanded={expandedSection === 'reality'}
                  onToggle={() => setExpandedSection(expandedSection === 'reality' ? null : 'reality')}
                  colors={colors}
                />
              )}
              
              {hasIntent && (
                <SourceSection
                  title="Customer Documents"
                  icon={<FileText size={14} style={{ color: colors.primary }} />}
                  colorScheme="green"
                  items={message.from_intent}
                  expanded={expandedSection === 'intent'}
                  onToggle={() => setExpandedSection(expandedSection === 'intent' ? null : 'intent')}
                  colors={colors}
                />
              )}
              
              {hasBestPractice && (
                <SourceSection
                  title="Reference Library"
                  icon={<BookOpen size={14} style={{ color: colors.amber }} />}
                  colorScheme="amber"
                  items={message.from_best_practice}
                  expanded={expandedSection === 'best_practice'}
                  onToggle={() => setExpandedSection(expandedSection === 'best_practice' ? null : 'best_practice')}
                  colors={colors}
                />
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Feedback */}
      <div style={{
        padding: '0.5rem 1rem',
        borderTop: `1px solid ${colors.divider}`,
        background: colors.inputBg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{ fontSize: '0.75rem', color: colors.textMuted }}>Was this helpful?</span>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => onFeedback(index, 'positive')}
            style={{
              padding: '0.375rem',
              borderRadius: 8,
              background: message.feedbackGiven === 'positive' ? colors.primaryLight : 'transparent',
              color: message.feedbackGiven === 'positive' ? colors.primary : colors.textLight,
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <ThumbsUp size={16} />
          </button>
          <button
            onClick={() => onFeedback(index, 'negative')}
            style={{
              padding: '0.375rem',
              borderRadius: 8,
              background: message.feedbackGiven === 'negative' ? colors.redLight : 'transparent',
              color: message.feedbackGiven === 'negative' ? colors.red : colors.textLight,
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <ThumbsDown size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}


// SOURCE SECTION COMPONENT
function SourceSection({ title, icon, colorScheme, items, expanded, onToggle, colors }) {
  const schemeColors = {
    blue: { bg: colors.blueLight, border: `${colors.blue}40` },
    green: { bg: colors.primaryLight, border: colors.primaryBorder },
    amber: { bg: colors.amberLight, border: `${colors.amber}40` },
  }
  
  const scheme = schemeColors[colorScheme] || schemeColors.green
  
  return (
    <div style={{
      borderRadius: 8,
      border: `1px solid ${scheme.border}`,
      background: scheme.bg,
      overflow: 'hidden',
    }}>
      <button
        onClick={onToggle}
        style={{
          width: '100%',
          padding: '0.5rem 0.75rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {icon}
          <span style={{ fontSize: '0.85rem', fontWeight: 500, color: colors.text }}>{title}</span>
          <span style={{ fontSize: '0.75rem', color: colors.textLight }}>({items.length})</span>
        </div>
        {expanded ? <ChevronDown size={14} style={{ color: colors.textMuted }} /> : <ChevronRight size={14} style={{ color: colors.textMuted }} />}
      </button>
      
      {expanded && (
        <div style={{ padding: '0 0.75rem 0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {items.slice(0, 3).map((item, i) => (
            <div key={i} style={{
              background: colors.card,
              borderRadius: 6,
              padding: '0.5rem',
              fontSize: '0.75rem',
            }}>
              <div style={{ fontWeight: 500, color: colors.text }}>{item.source_name}</div>
              <div style={{
                color: colors.textMuted,
                marginTop: '0.25rem',
                overflow: 'hidden',
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
              }}>
                {typeof item.content === 'string' 
                  ? item.content.slice(0, 200) 
                  : JSON.stringify(item.content).slice(0, 200)
                }...
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
