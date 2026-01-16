/**
 * Chat.jsx - Intelligent Chat Interface
 * 
 * Modern, polished AI assistant interface.
 * Uses CSS classes from index.css for consistent styling.
 * 
 * Features:
 * - INTELLIGENT MODE: Five Truths synthesis, smart clarification, proactive insights
 * - Scope selector: project, global, all
 * - Thumbs up/down feedback
 * - Export to Excel
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import { useState, useEffect, useRef } from 'react'
import api from '../services/api'
import { useProject } from '../context/ProjectContext'
import { 
  Brain, Database, FileText, BookOpen, AlertTriangle, 
  ChevronDown, ChevronRight, Lightbulb, Download,
  ThumbsUp, ThumbsDown, Copy, RefreshCw, Send, Trash2,
  Check, Zap, AlertCircle
} from 'lucide-react'
import { Tooltip } from './ui'

export default function Chat({ functionalAreas = [] }) {
  const { activeProject, projectName } = useProject()
  
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [expandedSources, setExpandedSources] = useState({})
  const messagesEndRef = useRef(null)
  const messagesAreaRef = useRef(null)
  
  // Scope state
  const [scope, setScope] = useState('project')
  
  // Intelligent mode state
  const [sessionId, setSessionId] = useState(null)
  const [pendingClarification, setPendingClarification] = useState(null)
  const [learningStats, setLearningStats] = useState(null)

  const scopeLabels = {
    project: 'Project',
    global: 'Global',
    all: 'All'
  }

  useEffect(() => {
    loadLearningStats()
    setSessionId(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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
            ? 'Preferences cleared. I\'ll ask clarifying questions again.'
            : 'Session filters reset. Ask your question again.',
          timestamp: new Date().toISOString()
        }])
      }
      
      return response.data
    } catch (err) {
      console.error('Failed to reset preferences:', err)
      return { success: false, message: err.message }
    }
  }

  const clearChat = () => {
    setMessages([])
    setPendingClarification(null)
  }

  const handleFeedback = async (index, feedbackType) => {
    const message = messages[index]
    if (!message?.job_id) return
    
    try {
      await api.post('/chat/unified/feedback', {
        job_id: message.job_id,
        feedback: feedbackType,
        message: messages[index - 1]?.content || '',
        response: message.content
      })
      
      setMessages(prev => prev.map((m, i) => 
        i === index ? { ...m, feedbackGiven: feedbackType } : m
      ))
    } catch (err) {
      console.error('Failed to submit feedback:', err)
    }
  }

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  // Send message handler
  const sendMessage = async (clarifications = null) => {
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
        persona: 'bessie',
        scope: scope,
        session_id: sessionId,
        clarifications: clarifications,
        include_citations: true,
        include_quality_alerts: true,
        include_follow_ups: true
      })

      const data = response.data

      // Handle file export
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
        setMessages(prev => {
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
            citations: data.citations || [],
            quality_alerts: data.quality_alerts || [],
            follow_ups: data.follow_ups || [],
            auto_applied_note: data.auto_applied_note,
            can_reset_preferences: data.can_reset_preferences,
            used_learning: data.used_learning,
            export: data.export,
            job_id: data.job_id,
            timestamp: new Date().toISOString()
          }]
        })
      }
    } catch (err) {
      console.error('Chat error:', err)
      setMessages(prev => [...prev, {
        role: 'assistant',
        type: 'error',
        content: err.response?.data?.detail || err.message || 'Failed to get response',
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

  const canSend = input.trim() && !loading && (scope !== 'project' || activeProject)

  return (
    <div className="chat">
      {/* Toolbar */}
      <div className="chat__toolbar">
        <div className="chat__toolbar-left">
          <Tooltip 
            title="Intelligent Mode" 
            detail="AI synthesizes answers from your structured data, documents, and reference library."
            action="Uses all available sources"
          >
            <div className="chat__mode-badge">
              <Brain size={16} />
              Intelligent
            </div>
          </Tooltip>
        </div>

        <div className="chat__toolbar-right">
          <Tooltip 
            title="Query Scope" 
            detail="Project: Current project data only. Global: Reference library only. All: Both sources combined."
            action="Select data sources to search"
          >
            <select
              className="chat__scope-select"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
            >
              {Object.entries(scopeLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </Tooltip>

          <Tooltip title="Clear Chat" detail="Remove all messages from this conversation.">
            <button className="chat__icon-btn" onClick={clearChat}>
              <Trash2 size={18} />
            </button>
          </Tooltip>
        </div>
      </div>

      {/* Intel Banner */}
      <div className="chat__intel-banner">
        <div className="chat__intel-banner-text">
          <Zap size={16} />
          <span><strong>Intelligent Mode:</strong> Synthesizes data + documents + reference library</span>
        </div>
        {learningStats?.available && (
          <div className="chat__intel-stats">
            <span title="Learned query patterns">{learningStats.learned_queries || 0} patterns</span>
            <span title="Feedback records">{learningStats.feedback_records || 0} feedback</span>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="chat__messages" ref={messagesAreaRef}>
        {messages.length === 0 ? (
          <div className="chat__empty-state">
            <div className="chat__empty-icon">
              <Brain />
            </div>
            <h3>Intelligent Analysis Ready</h3>
            <p>Ask questions and I'll synthesize answers from your data, documents, and reference library.</p>
            <div className="chat__empty-sources">
              <Tooltip title="Structured Data" detail="SQL queries against your uploaded tables - employee records, payroll data, configurations.">
                <div style={{ color: 'var(--electric-blue)' }}>
                  <Database size={14} /> Data
                </div>
              </Tooltip>
              <Tooltip title="Documents" detail="Semantic search across uploaded PDFs, Word docs, and text files.">
                <div style={{ color: 'var(--grass-green)' }}>
                  <FileText size={14} /> Docs
                </div>
              </Tooltip>
              <Tooltip title="Reference Library" detail="Global knowledge base - vendor documentation, regulatory guides, best practices.">
                <div style={{ color: 'var(--amber)' }}>
                  <BookOpen size={14} /> Reference
                </div>
              </Tooltip>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <MessageRenderer
              key={index}
              message={message}
              index={index}
              expandedSources={expandedSources}
              setExpandedSources={setExpandedSources}
              onFeedback={handleFeedback}
              onClarificationSubmit={(answers) => sendMessage(answers)}
              onResetPreferences={resetPreferences}
              onCopy={copyToClipboard}
            />
          ))
        )}
        
        {loading && (
          <div className="chat__loading">
            <RefreshCw size={16} />
            Analyzing sources...
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat__input-area">
        <div className="chat__input-row">
          <textarea
            className="chat__textarea"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              scope === 'project' && !activeProject 
                ? "Select a project first..." 
                : "Ask anything - I'll synthesize from all sources..."
            }
            rows={1}
          />
          <button
            className="chat__send-btn"
            onClick={() => sendMessage()}
            disabled={!canSend}
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  )
}


// ============================================================
// MESSAGE RENDERER - Routes to appropriate component
// ============================================================

function MessageRenderer({ message, index, expandedSources, setExpandedSources, onFeedback, onClarificationSubmit, onResetPreferences, onCopy }) {
  if (message.type === 'system') {
    return (
      <div className="chat-msg chat-msg--system">
        <div className="chat-msg__bubble">{message.content}</div>
      </div>
    )
  }
  
  if (message.type === 'clarification') {
    return (
      <ClarificationCard 
        questions={message.questions} 
        originalQuestion={message.originalQuestion} 
        onSubmit={onClarificationSubmit} 
      />
    )
  }
  
  if (message.type === 'intelligent') {
    return (
      <IntelligentResponse 
        message={message} 
        index={index} 
        expandedSources={expandedSources}
        setExpandedSources={setExpandedSources}
        onFeedback={onFeedback} 
        onResetPreferences={onResetPreferences}
        onCopy={onCopy}
      />
    )
  }

  if (message.type === 'error') {
    return (
      <div className="chat-msg chat-msg--assistant">
        <div className="chat-msg__avatar"><AlertCircle size={18} /></div>
        <div className="chat-msg__bubble" style={{ background: 'var(--scarlet-light)', borderColor: 'var(--scarlet)', color: 'var(--scarlet)' }}>
          {message.content}
        </div>
      </div>
    )
  }
  
  // Standard user/assistant message
  const isUser = message.role === 'user'
  
  return (
    <div className={`chat-msg ${isUser ? 'chat-msg--user' : 'chat-msg--assistant'}`}>
      <div className="chat-msg__avatar">
        {isUser ? 'U' : 'AI'}
      </div>
      <div className="chat-msg__bubble">
        {message.content}
      </div>
    </div>
  )
}


// ============================================================
// INTELLIGENT RESPONSE CARD
// ============================================================

function IntelligentResponse({ message, index, expandedSources, setExpandedSources, onFeedback, onResetPreferences, onCopy }) {
  const [showSources, setShowSources] = useState(false)
  const [expandedSection, setExpandedSection] = useState(null)
  const [resetting, setResetting] = useState(false)
  const [copied, setCopied] = useState(false)
  
  const hasReality = message.from_reality?.length > 0
  const hasIntent = message.from_intent?.length > 0
  const hasBestPractice = message.from_best_practice?.length > 0
  const hasConflicts = message.conflicts?.length > 0
  const hasInsights = message.insights?.length > 0
  const hasSources = hasReality || hasIntent || hasBestPractice
  
  const handleReset = async (resetType) => {
    setResetting(true)
    try {
      await onResetPreferences(resetType)
    } finally {
      setResetting(false)
    }
  }

  const handleCopy = async () => {
    await onCopy(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const confidenceLevel = message.confidence >= 0.8 ? 'high' : message.confidence >= 0.6 ? 'medium' : 'low'
  
  return (
    <div className="chat-intel">
      {/* Auto-Applied Banner */}
      {message.auto_applied_note && message.can_reset_preferences && (
        <div className="chat-intel__auto-banner">
          <span>{message.auto_applied_note}</span>
          <div className="chat-intel__auto-actions">
            <button onClick={() => handleReset('session')} disabled={resetting}>
              {resetting ? '...' : 'Reset'}
            </button>
            <button onClick={() => handleReset('learned')} disabled={resetting} style={{ color: 'var(--scarlet)' }}>
              {resetting ? '...' : 'Forget'}
            </button>
          </div>
        </div>
      )}
      
      {/* Header */}
      <div className="chat-intel__header">
        <div className="chat-intel__header-left">
          <Brain size={18} className="chat-intel__header-icon" />
          <span className="chat-intel__header-title">Intelligent Analysis</span>
          {message.used_learning && (
            <span className="chat-intel__learned-badge">Learned</span>
          )}
        </div>
        <div className={`chat-intel__confidence chat-intel__confidence--${confidenceLevel}`}>
          {Math.round((message.confidence || 0) * 100)}% confidence
        </div>
      </div>
      
      {/* Main Answer */}
      <div className="chat-intel__content">
        <div className="chat-intel__answer">
          <FormattedContent content={message.content} />
        </div>
        
        {/* Export Button */}
        {message.export && (
          <div className="chat-intel__export">
            <button
              className="chat-intel__export-btn"
              onClick={() => {
                const { filename, data, mime_type } = message.export
                const link = document.createElement('a')
                link.href = `data:${mime_type};base64,${data}`
                link.download = filename
                document.body.appendChild(link)
                link.click()
                document.body.removeChild(link)
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
        <div className="chat-intel__insights">
          <div className="chat-intel__insights-header">
            <Lightbulb size={16} />
            <span className="chat-intel__insights-title">Proactive Insights</span>
          </div>
          {message.insights.map((insight, i) => (
            <div key={i} className="chat-intel__insight">
              <span className={`chat-intel__insight-dot chat-intel__insight-dot--${insight.severity === 'high' ? 'high' : 'medium'}`}>
                {insight.severity === 'high' ? '●' : '○'}
              </span>
              <span>
                <strong>{insight.title}:</strong> {insight.description}
              </span>
            </div>
          ))}
        </div>
      )}
      
      {/* Conflicts */}
      {hasConflicts && (
        <div className="chat-intel__conflicts">
          <div className="chat-intel__conflicts-header">
            <AlertTriangle size={16} />
            <span className="chat-intel__conflicts-title">Conflicts Detected</span>
          </div>
          {message.conflicts.map((conflict, i) => (
            <div key={i} className="chat-intel__conflict">
              <div>{conflict.description}</div>
              <div className="chat-intel__conflict-rec">
                Recommendation: {conflict.recommendation}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Sources Toggle */}
      {hasSources && (
        <div className="chat-intel__sources">
          <button 
            className="chat-intel__sources-toggle"
            onClick={() => setShowSources(!showSources)}
          >
            <div className="chat-intel__sources-toggle-left">
              {showSources ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <span>View Sources</span>
            </div>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              {(message.from_reality?.length || 0) + (message.from_intent?.length || 0) + (message.from_best_practice?.length || 0)} sources
            </span>
          </button>
          
          {showSources && (
            <div className="chat-intel__sources-content">
              {hasReality && (
                <SourceSection
                  title="From Your Data"
                  icon={<Database size={14} style={{ color: 'var(--electric-blue)' }} />}
                  variant="reality"
                  items={message.from_reality}
                  expanded={expandedSection === 'reality'}
                  onToggle={() => setExpandedSection(expandedSection === 'reality' ? null : 'reality')}
                />
              )}
              {hasIntent && (
                <SourceSection
                  title="From Documents"
                  icon={<FileText size={14} style={{ color: 'var(--grass-green)' }} />}
                  variant="intent"
                  items={message.from_intent}
                  expanded={expandedSection === 'intent'}
                  onToggle={() => setExpandedSection(expandedSection === 'intent' ? null : 'intent')}
                />
              )}
              {hasBestPractice && (
                <SourceSection
                  title="From Reference Library"
                  icon={<BookOpen size={14} style={{ color: 'var(--amber)' }} />}
                  variant="reference"
                  items={message.from_best_practice}
                  expanded={expandedSection === 'reference'}
                  onToggle={() => setExpandedSection(expandedSection === 'reference' ? null : 'reference')}
                />
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Feedback */}
      <div className="chat-intel__feedback">
        <button
          className={`chat-intel__feedback-btn ${message.feedbackGiven === 'positive' ? 'chat-intel__feedback-btn--active-positive' : ''}`}
          onClick={() => onFeedback(index, 'positive')}
        >
          <ThumbsUp size={14} />
        </button>
        <button
          className={`chat-intel__feedback-btn ${message.feedbackGiven === 'negative' ? 'chat-intel__feedback-btn--active-negative' : ''}`}
          onClick={() => onFeedback(index, 'negative')}
        >
          <ThumbsDown size={14} />
        </button>
        <button className="chat-intel__copy-btn" onClick={handleCopy}>
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
    </div>
  )
}


// ============================================================
// SOURCE SECTION
// ============================================================

function SourceSection({ title, icon, variant, items, expanded, onToggle }) {
  return (
    <div className={`chat-intel__source-section chat-intel__source-section--${variant}`}>
      <button className="chat-intel__source-header" onClick={onToggle}>
        <div className="chat-intel__source-header-left">
          {icon}
          <span className="chat-intel__source-title">{title}</span>
          <span className="chat-intel__source-count">({items.length})</span>
        </div>
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>
      
      {expanded && (
        <div className="chat-intel__source-items">
          {items.slice(0, 5).map((item, i) => (
            <div key={i} className="chat-intel__source-item">
              <div className="chat-intel__source-item-name">
                {item.source_name || item.table_name || 'Source'}
              </div>
              <div className="chat-intel__source-item-content">
                {typeof item.content === 'string' 
                  ? item.content.slice(0, 200) 
                  : JSON.stringify(item.content || item.data || '').slice(0, 200)
                }...
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


// ============================================================
// CLARIFICATION CARD
// ============================================================

function ClarificationCard({ questions, originalQuestion, onSubmit }) {
  const [answers, setAnswers] = useState({})
  
  useEffect(() => {
    const defaults = {}
    questions?.forEach(q => {
      const defaultOpt = q.options?.find(o => o.default)
      if (defaultOpt) {
        defaults[q.id] = q.type === 'checkbox' ? [defaultOpt.id] : defaultOpt.id
      }
    })
    setAnswers(defaults)
  }, [questions])

  const handleOptionClick = (questionId, optionId, type) => {
    if (type === 'checkbox') {
      setAnswers(prev => ({
        ...prev,
        [questionId]: prev[questionId]?.includes(optionId)
          ? prev[questionId].filter(v => v !== optionId)
          : [...(prev[questionId] || []), optionId]
      }))
    } else {
      setAnswers(prev => ({ ...prev, [questionId]: optionId }))
    }
  }

  const isSelected = (questionId, optionId, type) => {
    if (type === 'checkbox') {
      return answers[questionId]?.includes(optionId)
    }
    return answers[questionId] === optionId
  }
  
  return (
    <div className="chat-clarify">
      <div className="chat-clarify__header">
        <div className="chat-clarify__avatar">
          <Brain size={22} />
        </div>
        <div>
          <h4 className="chat-clarify__title">Quick clarification needed</h4>
          <p className="chat-clarify__subtitle">Help me give you a more precise answer</p>
        </div>
      </div>
      
      <div className="chat-clarify__questions">
        {questions?.map((q) => (
          <div key={q.id} className="chat-clarify__question">
            <label className="chat-clarify__question-label">{q.question}</label>
            <div className="chat-clarify__options">
              {q.options?.map((opt) => (
                <button
                  key={opt.id}
                  className={`chat-clarify__option ${isSelected(q.id, opt.id, q.type) ? 'chat-clarify__option--selected' : ''}`}
                  onClick={() => handleOptionClick(q.id, opt.id, q.type)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
      
      <button 
        className="chat-clarify__submit"
        onClick={() => onSubmit(answers)}
        disabled={Object.keys(answers).length === 0}
      >
        Get Answer
      </button>
    </div>
  )
}


// ============================================================
// FORMATTED CONTENT - Simple markdown-like rendering
// ============================================================

function FormattedContent({ content }) {
  if (!content) return null
  
  // Split into paragraphs and render
  const paragraphs = content.split('\n\n').filter(p => p.trim())
  
  return (
    <>
      {paragraphs.map((para, i) => {
        // Check for bullet lists
        if (para.includes('\n- ') || para.startsWith('- ')) {
          const items = para.split('\n').filter(line => line.trim())
          return (
            <ul key={i}>
              {items.map((item, j) => (
                <li key={j}>{item.replace(/^-\s*/, '')}</li>
              ))}
            </ul>
          )
        }
        
        // Check for numbered lists
        if (/^\d+\.\s/.test(para)) {
          const items = para.split('\n').filter(line => line.trim())
          return (
            <ol key={i}>
              {items.map((item, j) => (
                <li key={j}>{item.replace(/^\d+\.\s*/, '')}</li>
              ))}
            </ol>
          )
        }
        
        // Regular paragraph - handle inline formatting
        let text = para
        // Bold: **text** or __text__
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        text = text.replace(/__(.*?)__/g, '<strong>$1</strong>')
        // Code: `code`
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>')
        
        return (
          <p key={i} dangerouslySetInnerHTML={{ __html: text }} />
        )
      })}
    </>
  )
}
