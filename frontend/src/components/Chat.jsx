/**
 * Chat.jsx - REVOLUTIONARY INTELLIGENT CHAT
 * 
 * Features:
 * - INTELLIGENT MODE: Three Truths synthesis, smart clarification, proactive insights
 * - Standard Mode: Original chat functionality
 * - Scope selector: project, global, all
 * - Thumbs up/down feedback
 * - Personas, Excel export, PII indicators
 * 
 * Deploy to: frontend/src/pages/Chat.jsx
 */

import { useState, useEffect, useRef } from 'react'
import api from '../services/api'
import { useProject } from '../context/ProjectContext'
import PersonaSwitcher from '../components/PersonaSwitcher'
import PersonaCreator from '../components/PersonaCreator'
import { 
  Zap, Brain, Database, FileText, BookOpen, AlertTriangle, 
  CheckCircle, ChevronDown, ChevronRight, Lightbulb, Download,
  ThumbsUp, ThumbsDown, Copy, RefreshCw, Send, Trash2, Eye, EyeOff
} from 'lucide-react'

export default function Chat({ functionalAreas = [] }) {
  const { activeProject, projectName } = useProject()
  
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
  const [intelligentMode, setIntelligentMode] = useState(true)  // ON by default!
  const [sessionId, setSessionId] = useState(null)
  const [pendingClarification, setPendingClarification] = useState(null)
  const [learningStats, setLearningStats] = useState(null)
  
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
    // Generate session ID for intelligent mode
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

  // Reset preferences (clear learned filters)
  const resetPreferences = async (resetType = 'session') => {
    try {
      const response = await api.post('/chat/intelligent/reset-preferences', {
        session_id: sessionId,
        project: projectName || null,
        reset_type: resetType
      })
      
      if (response.data.success) {
        // Add a system message indicating reset
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
      await api.post('/chat/feedback', {
        job_id: jobId,
        feedback: feedbackType,
        message: messageContent,
        response: responseContent
      })
    } catch (err) {
      console.error('Failed to submit feedback:', err)
    }
  }

  // ============================================================
  // INTELLIGENT MESSAGE HANDLER
  // ============================================================
  
  const sendIntelligentMessage = async (clarifications = null) => {
    const messageText = clarifications ? pendingClarification?.originalQuestion : input.trim()
    if (!messageText) return

    if (!clarifications) {
      // Add user message
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
      const response = await api.post('/chat/intelligent', {
        message: messageText,
        project: projectName || null,
        persona: currentPersona?.id || 'bessie',
        scope: scope,
        session_id: sessionId,
        clarifications: clarifications
      })

      const data = response.data

      // Check if clarification needed
      if (data.needs_clarification) {
        setPendingClarification({
          originalQuestion: messageText,
          questions: data.clarification_questions,
          sessionId: data.session_id
        })
        
        // Add clarification message
        setMessages(prev => [...prev, {
          role: 'assistant',
          type: 'clarification',
          questions: data.clarification_questions,
          originalQuestion: messageText,
          timestamp: new Date().toISOString()
        }])
      } else {
        // Add intelligent response
        setMessages(prev => [...prev, {
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
          timestamp: new Date().toISOString()
        }])
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

  // ============================================================
  // STANDARD MESSAGE HANDLER (original)
  // ============================================================
  
  const sendStandardMessage = async () => {
    if (!input.trim()) return

    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    const tempId = `temp-${Date.now()}`
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: '🔵 Starting...',
      isStatus: true,
      tempId,
      timestamp: new Date().toISOString()
    }])

    try {
      const startResponse = await api.post('/chat/start', {
        message: userMessage.content,
        project: projectName || null,
        max_results: 50,
        persona: currentPersona?.id || 'bessie',
        scope: scope
      })

      const { job_id } = startResponse.data

      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await api.get(`/chat/status/${job_id}`)
          const jobStatus = statusResponse.data

          setMessages(prev => prev.map(msg =>
            msg.tempId === tempId
              ? { ...msg, content: jobStatus.current_step, progress: jobStatus.progress }
              : msg
          ))

          if (jobStatus.status === 'complete') {
            clearInterval(pollInterval)
            setMessages(prev => prev.map(msg =>
              msg.tempId === tempId ? {
                role: 'assistant',
                type: 'standard',
                content: jobStatus.response,
                sources: jobStatus.sources || [],
                chunks_found: jobStatus.chunks_found || 0,
                routing_info: jobStatus.routing_info,
                job_id: job_id,
                userQuery: userMessage.content,
                timestamp: new Date().toISOString()
              } : msg
            ))
            setLoading(false)
          }

          if (jobStatus.status === 'failed') {
            clearInterval(pollInterval)
            setMessages(prev => prev.map(msg =>
              msg.tempId === tempId
                ? { ...msg, content: '❌ ' + (jobStatus.error || 'Failed'), error: true }
                : msg
            ))
            setLoading(false)
          }
        } catch (pollErr) {
          console.error('Poll error:', pollErr)
        }
      }, 500)

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
          ? { ...msg, content: '❌ ' + (err.response?.data?.detail || err.message), error: true }
          : msg
      ))
      setLoading(false)
    }
  }

  // Main send handler
  const sendMessage = () => {
    if (intelligentMode) {
      sendIntelligentMessage()
    } else {
      sendStandardMessage()
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
    setPendingClarification(null)
    setSessionId(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  }

  const handleFeedback = async (messageIndex, feedbackType) => {
    const message = messages[messageIndex]
    
    // Update UI immediately
    setMessages(prev => prev.map((msg, idx) => 
      idx === messageIndex ? { ...msg, feedbackGiven: feedbackType } : msg
    ))
    
    // Send feedback to appropriate endpoint
    if (message?.type === 'intelligent') {
      // Use learning feedback endpoint
      try {
        await api.post('/chat/intelligent/feedback', {
          question: message.question || messages[messageIndex - 1]?.content || '',
          feedback: feedbackType,
          project: projectName,
          intent: message.structured_output?.detected_mode
        })
        console.log(`✅ Learning feedback recorded: ${feedbackType}`)
      } catch (err) {
        console.error('Failed to submit learning feedback:', err)
      }
    } else if (message?.job_id) {
      // Use standard feedback endpoint
      submitFeedback(message.job_id, feedbackType, message.userQuery, message.content)
    }
  }

  const isDisabled = loading || (!input.trim()) || (scope === 'project' && !activeProject)

  return (
    <div className="h-[75vh] min-h-[500px] flex flex-col bg-white rounded-xl shadow-lg overflow-hidden border">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-slate-50 to-white border-b flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <PersonaSwitcher 
            currentPersona={currentPersona}
            onPersonaChange={setCurrentPersona}
            onCreateNew={() => setShowPersonaCreator(true)}
          />
          
          {/* Intelligent Mode Toggle */}
          <button
            onClick={() => setIntelligentMode(!intelligentMode)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              intelligentMode 
                ? 'bg-purple-600 text-white shadow-md' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <Brain size={16} />
            {intelligentMode ? '🧠 Intelligent' : 'Standard'}
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* Scope Selector */}
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            className="px-3 py-1.5 text-sm border rounded-lg bg-white"
          >
            {Object.entries(scopeLabels).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>

          <button
            onClick={clearChat}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
            title="Clear chat"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>

      {/* Intelligent Mode Banner */}
      {intelligentMode && (
        <div className="px-4 py-2 bg-purple-50 border-b border-purple-100 flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <Zap className="text-purple-600" size={16} />
            <span className="text-purple-700">
              <strong>Intelligent Mode:</strong> Synthesizes data + documents + best practices
            </span>
          </div>
          {learningStats?.available && (
            <div className="flex items-center gap-3 text-xs text-purple-600">
              <span title="Learned query patterns">
                🧠 {learningStats.learned_queries || 0} patterns
              </span>
              <span title="Feedback records">
                👍 {learningStats.feedback_records || 0} feedback
              </span>
            </div>
          )}
        </div>
      )}

      {/* Messages Area */}
      <div 
        ref={messagesAreaRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-500">
            <div className="text-6xl mb-4 opacity-50">
              {intelligentMode ? '🧠' : '💬'}
            </div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">
              {intelligentMode ? 'Intelligent Analysis Ready' : 'Start a Conversation'}
            </h3>
            <p className="text-sm text-center max-w-md">
              {intelligentMode 
                ? 'Ask questions and I\'ll synthesize answers from your data, documents, and UKG best practices.'
                : 'Ask questions about your uploaded data and documents.'
              }
            </p>
            {intelligentMode && (
              <div className="mt-4 flex gap-4 text-xs">
                <div className="flex items-center gap-1 text-blue-600">
                  <Database size={14} /> Data
                </div>
                <div className="flex items-center gap-1 text-purple-600">
                  <FileText size={14} /> Docs
                </div>
                <div className="flex items-center gap-1 text-green-600">
                  <BookOpen size={14} /> Best Practice
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
            />
          ))
        )}
        
        {loading && (
          <div className="flex items-center gap-2 text-gray-500 text-sm">
            <RefreshCw className="animate-spin" size={16} />
            {intelligentMode ? 'Analyzing sources...' : 'Processing...'}
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white border-t">
        <div className="flex gap-2">
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
            className="flex-1 px-4 py-3 border rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            rows={2}
            disabled={scope === 'project' && !activeProject}
          />
          <button
            onClick={sendMessage}
            disabled={isDisabled}
            className={`px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 ${
              isDisabled
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : intelligentMode
                  ? 'bg-purple-600 text-white hover:bg-purple-700 shadow-md'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
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
    </div>
  )
}


// ============================================================
// MESSAGE BUBBLE COMPONENT
// ============================================================

function MessageBubble({ message, index, persona, expandedSources, toggleSources, onFeedback, onClarificationSubmit, onResetPreferences }) {
  const isUser = message.role === 'user'
  
  // System message (like reset confirmation)
  if (message.type === 'system') {
    return (
      <div className="flex justify-center my-2">
        <div className="px-4 py-2 bg-gray-100 text-gray-600 text-sm rounded-full">
          {message.content}
        </div>
      </div>
    )
  }
  
  // Clarification message
  if (message.type === 'clarification') {
    return (
      <ClarificationCard 
        questions={message.questions}
        originalQuestion={message.originalQuestion}
        onSubmit={onClarificationSubmit}
      />
    )
  }
  
  // Intelligent response
  if (message.type === 'intelligent') {
    return (
      <IntelligentResponse 
        message={message}
        index={index}
        onFeedback={onFeedback}
        onResetPreferences={onResetPreferences}
      />
    )
  }
  
  // Standard message (user or assistant)
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser 
          ? 'bg-gradient-to-br from-green-500 to-green-600 text-white' 
          : 'bg-gradient-to-br from-purple-100 to-blue-100 text-purple-600'
      }`}>
        {isUser ? '👤' : persona?.icon || '🐮'}
      </div>
      
      {/* Bubble */}
      <div className={`max-w-[75%] rounded-xl px-4 py-3 ${
        isUser 
          ? 'bg-gradient-to-br from-green-500 to-green-600 text-white rounded-br-sm'
          : message.error
            ? 'bg-red-50 border border-red-200 text-red-700 rounded-bl-sm'
            : 'bg-white shadow-sm border rounded-bl-sm'
      }`}>
        <div className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
        </div>
        
        {/* Sources for standard responses */}
        {message.sources?.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <button 
              onClick={() => toggleSources(index)}
              className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              {expandedSources[index] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              {message.sources.length} sources
            </button>
            {expandedSources[index] && (
              <div className="mt-2 space-y-1">
                {message.sources.slice(0, 5).map((src, i) => (
                  <div key={i} className="text-xs text-gray-500 truncate">
                    📄 {src.filename || src.source || 'Unknown'}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* Feedback buttons */}
        {!isUser && !message.error && !message.isStatus && message.type === 'standard' && (
          <div className="mt-2 pt-2 border-t border-gray-100 flex gap-2">
            <button
              onClick={() => onFeedback(index, 'positive')}
              className={`p-1 rounded ${message.feedbackGiven === 'positive' ? 'text-green-600 bg-green-50' : 'text-gray-400 hover:text-green-600'}`}
            >
              <ThumbsUp size={14} />
            </button>
            <button
              onClick={() => onFeedback(index, 'negative')}
              className={`p-1 rounded ${message.feedbackGiven === 'negative' ? 'text-red-600 bg-red-50' : 'text-gray-400 hover:text-red-600'}`}
            >
              <ThumbsDown size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}


// ============================================================
// CLARIFICATION CARD
// ============================================================

function ClarificationCard({ questions, originalQuestion, onSubmit }) {
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
  
  // Set defaults
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
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 max-w-lg">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
          <Brain className="text-blue-600" size={20} />
        </div>
        <div>
          <h3 className="font-semibold text-blue-900">Let me clarify</h3>
          <p className="text-sm text-blue-700">Quick questions for a better answer</p>
        </div>
      </div>
      
      <div className="space-y-4">
        {questions?.map((q) => (
          <div key={q.id} className="bg-white rounded-lg p-4 border border-blue-100">
            <div className="font-medium text-gray-800 mb-3">{q.question}</div>
            
            {q.type === 'radio' && (
              <div className="space-y-2">
                {q.options?.map((opt) => (
                  <label key={opt.id} className="flex items-center gap-3 cursor-pointer group">
                    <input
                      type="radio"
                      name={q.id}
                      checked={answers[q.id] === opt.id}
                      onChange={() => handleChange(q.id, opt.id, 'radio')}
                      className="text-blue-600"
                    />
                    <span className="text-sm text-gray-700 group-hover:text-gray-900">
                      {opt.label}
                    </span>
                  </label>
                ))}
              </div>
            )}
            
            {q.type === 'checkbox' && (
              <div className="flex flex-wrap gap-3">
                {q.options?.map((opt) => (
                  <label key={opt.id} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={answers[q.id]?.includes(opt.id)}
                      onChange={() => handleChange(q.id, opt.id, 'checkbox')}
                      className="text-blue-600 rounded"
                    />
                    <span className="text-sm text-gray-700">{opt.label}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div className="mt-5 flex gap-3">
        <button
          onClick={() => onSubmit(answers)}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium flex items-center gap-2"
        >
          <Zap size={16} /> Get Answer
        </button>
        <button
          onClick={() => onSubmit(null)}
          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg text-sm"
        >
          Skip
        </button>
      </div>
    </div>
  )
}


// ============================================================
// INTELLIGENT RESPONSE COMPONENT
// ============================================================

function IntelligentResponse({ message, index, onFeedback, onResetPreferences }) {
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
    <div className="bg-white rounded-xl border shadow-sm overflow-hidden max-w-2xl">
      {/* Auto-Applied Preferences Banner */}
      {message.auto_applied_note && message.can_reset_preferences && (
        <div className="px-4 py-2 bg-amber-50 border-b border-amber-100 flex items-center justify-between">
          <span className="text-sm text-amber-800">{message.auto_applied_note}</span>
          <div className="flex gap-2">
            <button
              onClick={() => handleReset('session')}
              disabled={resetting}
              className="text-xs text-amber-600 hover:text-amber-800 hover:underline disabled:opacity-50"
              title="Ask clarification again for this session"
            >
              {resetting ? '...' : 'Reset'}
            </button>
            <button
              onClick={() => handleReset('learned')}
              disabled={resetting}
              className="text-xs text-red-600 hover:text-red-800 hover:underline disabled:opacity-50"
              title="Forget this preference permanently"
            >
              {resetting ? '...' : 'Forget'}
            </button>
          </div>
        </div>
      )}
      
      {/* Confidence Header */}
      <div className="px-4 py-2 bg-gradient-to-r from-purple-50 to-blue-50 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="text-purple-600" size={16} />
          <span className="text-sm font-medium text-purple-800">Intelligent Analysis</span>
          {message.used_learning && (
            <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full flex items-center gap-1">
              🧠 Learned
            </span>
          )}
        </div>
        <div className={`px-2 py-0.5 rounded text-xs font-medium ${
          message.confidence >= 0.8 ? 'bg-green-100 text-green-700' :
          message.confidence >= 0.6 ? 'bg-blue-100 text-blue-700' :
          'bg-amber-100 text-amber-700'
        }`}>
          {Math.round((message.confidence || 0) * 100)}% confidence
        </div>
      </div>
      
      {/* Main Answer */}
      <div className="p-4">
        <div className="prose prose-sm max-w-none whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
      
      {/* Proactive Insights */}
      {hasInsights && (
        <div className="mx-4 mb-4 bg-amber-50 border border-amber-200 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb className="text-amber-600" size={16} />
            <span className="font-medium text-amber-800 text-sm">Proactive Insights</span>
          </div>
          <div className="space-y-1">
            {message.insights.map((insight, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className={`flex-shrink-0 ${
                  insight.severity === 'high' ? 'text-red-500' : 'text-amber-500'
                }`}>
                  {insight.severity === 'high' ? '🔴' : '🟡'}
                </span>
                <span className="text-amber-900">
                  <strong>{insight.title}:</strong> {insight.description}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Conflicts */}
      {hasConflicts && (
        <div className="mx-4 mb-4 bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="text-red-600" size={16} />
            <span className="font-medium text-red-800 text-sm">Conflicts Detected</span>
          </div>
          {message.conflicts.map((conflict, i) => (
            <div key={i} className="text-sm text-red-900 mb-2">
              <div>{conflict.description}</div>
              <div className="text-red-700 text-xs mt-1">
                💡 Recommendation: {conflict.recommendation}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Sources Toggle */}
      {(hasReality || hasIntent || hasBestPractice) && (
        <div className="border-t">
          <button
            onClick={() => setShowSources(!showSources)}
            className="w-full px-4 py-2 flex items-center justify-between hover:bg-gray-50 text-sm"
          >
            <span className="text-gray-600">Sources of Truth</span>
            <div className="flex items-center gap-3">
              {hasReality && <span className="text-blue-600 text-xs">📊 Data</span>}
              {hasIntent && <span className="text-purple-600 text-xs">📄 Docs</span>}
              {hasBestPractice && <span className="text-green-600 text-xs">📘 UKG</span>}
              {showSources ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
          </button>
          
          {showSources && (
            <div className="px-4 pb-4 space-y-2">
              {/* Reality */}
              {hasReality && (
                <SourceSection
                  title="Customer Data"
                  icon={<Database className="text-blue-500" size={14} />}
                  color="blue"
                  items={message.from_reality}
                  expanded={expandedSection === 'reality'}
                  onToggle={() => setExpandedSection(expandedSection === 'reality' ? null : 'reality')}
                />
              )}
              
              {/* Intent */}
              {hasIntent && (
                <SourceSection
                  title="Customer Documents"
                  icon={<FileText className="text-purple-500" size={14} />}
                  color="purple"
                  items={message.from_intent}
                  expanded={expandedSection === 'intent'}
                  onToggle={() => setExpandedSection(expandedSection === 'intent' ? null : 'intent')}
                />
              )}
              
              {/* Best Practice */}
              {hasBestPractice && (
                <SourceSection
                  title="UKG Best Practice"
                  icon={<BookOpen className="text-green-500" size={14} />}
                  color="green"
                  items={message.from_best_practice}
                  expanded={expandedSection === 'best_practice'}
                  onToggle={() => setExpandedSection(expandedSection === 'best_practice' ? null : 'best_practice')}
                />
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Feedback Buttons */}
      <div className="px-4 py-2 border-t bg-gray-50 flex items-center justify-between">
        <span className="text-xs text-gray-500">Was this helpful?</span>
        <div className="flex gap-2">
          <button
            onClick={() => onFeedback(index, 'positive')}
            className={`p-1.5 rounded-lg transition-all ${
              message.feedbackGiven === 'positive' 
                ? 'bg-green-100 text-green-600' 
                : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
            }`}
            title="This was helpful"
          >
            <ThumbsUp size={16} />
          </button>
          <button
            onClick={() => onFeedback(index, 'negative')}
            className={`p-1.5 rounded-lg transition-all ${
              message.feedbackGiven === 'negative' 
                ? 'bg-red-100 text-red-600' 
                : 'text-gray-400 hover:text-red-600 hover:bg-red-50'
            }`}
            title="This needs improvement"
          >
            <ThumbsDown size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}


// Source Section Component
function SourceSection({ title, icon, color, items, expanded, onToggle }) {
  const colors = {
    blue: 'bg-blue-50 border-blue-100 hover:bg-blue-100',
    purple: 'bg-purple-50 border-purple-100 hover:bg-purple-100',
    green: 'bg-green-50 border-green-100 hover:bg-green-100',
  }
  
  return (
    <div className={`rounded-lg border ${colors[color]}`}>
      <button
        onClick={onToggle}
        className="w-full px-3 py-2 flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-medium">{title}</span>
          <span className="text-xs text-gray-400">({items.length})</span>
        </div>
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>
      
      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          {items.slice(0, 3).map((item, i) => (
            <div key={i} className="bg-white rounded p-2 text-xs">
              <div className="font-medium text-gray-700">{item.source_name}</div>
              <div className="text-gray-500 mt-1 line-clamp-3">
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
