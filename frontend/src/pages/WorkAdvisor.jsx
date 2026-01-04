import React, { useState, useRef, useEffect } from 'react'
import { 
  MessageSquare, 
  Send, 
  Lightbulb,
  ArrowRight,
  FileText,
  BarChart3,
  GitCompare,
  Upload,
  CheckSquare,
  Sparkles,
  RotateCcw,
  ChevronRight,
  Zap,
  Target,
  Compass,
  Bot
} from 'lucide-react'
import { Tooltip } from '../components/ui'

/**
 * WorkAdvisor - Conversational guide to help users find the right approach
 * 
 * POLISHED VERSION - Matches platform visual style with gradients, 
 * animations, and consistent brand colors
 */

// Mission Control Color Palette
const COLORS = {
  primary: '#83b16d',
  primaryDark: '#6b9b5a',
  accent: '#285390',
  accentLight: 'rgba(40, 83, 144, 0.1)',
  iceFlow: '#c9d3d4',
  text: '#1a2332',
  textMuted: '#64748b',
  bg: '#f0f2f5',
  card: '#ffffff',
  border: '#e2e8f0',
}

const ADVISOR_PERSONA = `You are a friendly, experienced implementation consultant helping a colleague figure out the best approach for their task. Ask thoughtful questions to understand what they need.

Guide them to: CHAT, VACUUM, BI_BUILDER, PLAYBOOK_EXISTING, PLAYBOOK_NEW, COMPARE, or GL_MAPPER.

Ask 2-3 questions before recommending. When ready, use exact phrases like:
- "I recommend using **Chat**" 
- "I recommend we **build a playbook**"
- "I recommend the **BI Builder**"
`

const INITIAL_MESSAGE = {
  role: 'assistant',
  content: `Hey! 👋 I'm here to help you figure out the best approach for what you're working on.

Tell me about what you're trying to accomplish - what's the problem you're solving or the deliverable you need?`,
  timestamp: new Date()
}

// Feature cards with brand-consistent styling
const FEATURES = {
  CHAT: {
    icon: MessageSquare,
    title: 'Chat',
    description: 'Upload files and explore with AI. Great for thinking through problems.',
    color: COLORS.accent,
    bgColor: 'rgba(147, 171, 217, 0.1)',
    route: '/workspace',
    available: true
  },
  VACUUM: {
    icon: Upload,
    title: 'Upload Data',
    description: 'Ingest and profile your files to use across the platform.',
    color: '#5a8a4a',
    bgColor: 'rgba(131, 177, 109, 0.1)',
    route: '/vacuum',
    available: true
  },
  BI_BUILDER: {
    icon: BarChart3,
    title: 'BI Builder',
    description: 'Ask questions in plain English. Build charts and dashboards.',
    color: '#9b7ed9',
    bgColor: 'rgba(155, 126, 217, 0.1)',
    route: '/analytics',
    available: true
  },
  PLAYBOOK_EXISTING: {
    icon: CheckSquare,
    title: 'Run Playbook',
    description: 'Execute a structured workflow with defined steps.',
    color: '#e8a838',
    bgColor: 'rgba(232, 168, 56, 0.1)',
    route: '/playbooks',
    available: true
  },
  PLAYBOOK_NEW: {
    icon: Sparkles,
    title: 'Build Playbook',
    description: "Create a reusable workflow. I'll help define it.",
    color: '#4ecdc4',
    bgColor: 'rgba(78, 205, 196, 0.1)',
    route: null,
    available: true
  },
  COMPARE: {
    icon: GitCompare,
    title: 'Compare',
    description: 'Compare datasets and find variances.',
    color: '#ff6b6b',
    bgColor: 'rgba(255, 107, 107, 0.1)',
    route: '/compare',
    available: false
  },
  GL_MAPPER: {
    icon: FileText,
    title: 'GL Mapper',
    description: 'Map legacy GL to new system rules.',
    color: '#45b7d1',
    bgColor: 'rgba(69, 183, 209, 0.1)',
    route: '/gl-mapper',
    available: false
  }
}

export default function WorkAdvisor() {
  const [messages, setMessages] = useState([INITIAL_MESSAGE])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [recommendation, setRecommendation] = useState(null)
  const [showPlaybookBuilder, setShowPlaybookBuilder] = useState(false)
  const [playbookDraft, setPlaybookDraft] = useState(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = { role: 'user', content: input.trim(), timestamp: new Date() }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const conversationHistory = [...messages, userMessage].map(m => ({
        role: m.role, content: m.content
      }))

      const response = await fetch('/api/advisor/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: conversationHistory, system_prompt: ADVISOR_PERSONA })
      })

      if (!response.ok) throw new Error('Advisor request failed')
      const data = await response.json()

      if (data.recommendation) {
        setRecommendation(data.recommendation)
        if (data.playbook_draft) setPlaybookDraft(data.playbook_draft)
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        recommendation: data.recommendation || null
      }])
    } catch (error) {
      console.error('Advisor error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Sorry, I hit a snag. What were you working on?",
        timestamp: new Date()
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleRestart = () => {
    setMessages([INITIAL_MESSAGE])
    setRecommendation(null)
    setPlaybookDraft(null)
    setShowPlaybookBuilder(false)
    setInput('')
  }

  const handleFeatureSelect = (featureKey) => {
    const feature = FEATURES[featureKey]
    if (!feature.available) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `**${feature.title}** is coming soon! For now, try **Chat** to work through it manually, or we can **build a playbook** for the workflow.`,
        timestamp: new Date()
      }])
      return
    }
    if (featureKey === 'PLAYBOOK_NEW') {
      setShowPlaybookBuilder(true)
      return
    }
    window.location.href = feature.route
  }

  const handleSkipAdvisor = () => {
    setMessages(prev => [...prev, {
      role: 'assistant', 
      content: `No problem! Here's what's available:`,
      timestamp: new Date(),
      showQuickAccess: true
    }])
  }

  const styles = {
    container: {
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'linear-gradient(135deg, #f8faf7 0%, #ffffff 50%, #f5f8fc 100%)',
    },
    header: {
      padding: '1.25rem 1.5rem',
      background: 'white',
      borderBottom: '1px solid #e8ecef',
      boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
    },
    headerInner: {
      maxWidth: '900px',
      margin: '0 auto',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    headerLeft: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
    },
    iconWrapper: {
      position: 'relative',
    },
    mainIcon: {
      width: '56px',
      height: '56px',
      borderRadius: '16px',
      background: `linear-gradient(135deg, #5a8a4a 0%, #4a7a3a 100%)`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: '0 4px 12px rgba(131, 177, 109, 0.3)',
    },
    sparkBadge: {
      position: 'absolute',
      bottom: '-4px',
      right: '-4px',
      width: '22px',
      height: '22px',
      borderRadius: '8px',
      background: 'linear-gradient(135deg, #ffd93d 0%, #ff9f43 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: '0 2px 6px rgba(255, 159, 67, 0.4)',
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.5rem',
      fontWeight: '700',
      color: COLORS.text,
      margin: 0,
    },
    subtitle: {
      fontSize: '0.875rem',
      color: COLORS.textMuted,
      margin: 0,
    },
    headerActions: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
    },
    skipButton: {
      padding: '0.5rem 1rem',
      fontSize: '0.875rem',
      fontWeight: '500',
      color: COLORS.textMuted,
      background: 'transparent',
      border: 'none',
      borderRadius: '10px',
      cursor: 'pointer',
      transition: 'all 0.2s',
    },
    resetButton: {
      padding: '0.625rem',
      background: '#f5f7f9',
      border: 'none',
      borderRadius: '10px',
      cursor: 'pointer',
      color: COLORS.textMuted,
      transition: 'all 0.2s',
    },
    messagesArea: {
      flex: 1,
      overflowY: 'auto',
      padding: '1.5rem',
    },
    messagesInner: {
      maxWidth: '900px',
      margin: '0 auto',
    },
    messageRow: (isUser) => ({
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: '1rem',
      animation: 'fadeSlideIn 0.3s ease-out',
    }),
    avatar: (isUser) => ({
      width: '40px',
      height: '40px',
      borderRadius: '12px',
      background: isUser 
        ? 'linear-gradient(135deg, #4a5568 0%, #2d3748 100%)'
        : `linear-gradient(135deg, #5a8a4a 0%, #4a7a3a 100%)`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      marginRight: isUser ? 0 : '0.75rem',
      marginLeft: isUser ? '0.75rem' : 0,
    }),
    messageBubble: (isUser) => ({
      maxWidth: '70%',
      padding: '1rem 1.25rem',
      borderRadius: '16px',
      borderBottomLeftRadius: isUser ? '16px' : '6px',
      borderBottomRightRadius: isUser ? '6px' : '16px',
      background: isUser 
        ? `linear-gradient(135deg, #5a8a4a 0%, #4a7a3a 100%)`
        : 'white',
      color: isUser ? 'white' : COLORS.text,
      boxShadow: isUser 
        ? '0 2px 12px rgba(131, 177, 109, 0.3)'
        : '0 2px 8px rgba(0,0,0,0.06)',
      border: isUser ? 'none' : '1px solid #e8ecef',
    }),
    messageText: {
      lineHeight: '1.6',
      whiteSpace: 'pre-wrap',
      margin: 0,
    },
    loadingBubble: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '1rem 1.5rem',
    },
    loadingDot: (delay) => ({
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      background: '#5a8a4a',
      animation: 'bounce 1s infinite',
      animationDelay: delay,
    }),
    inputArea: {
      padding: '1rem 1.5rem 1.25rem',
      background: 'white',
      borderTop: '1px solid #e8ecef',
    },
    inputInner: {
      maxWidth: '900px',
      margin: '0 auto',
    },
    inputWrapper: {
      position: 'relative',
      display: 'flex',
      alignItems: 'flex-end',
      gap: '0.75rem',
    },
    textarea: {
      flex: 1,
      padding: '1rem 3.5rem 1rem 1.25rem',
      fontSize: '0.9375rem',
      border: '2px solid #e8ecef',
      borderRadius: '16px',
      resize: 'none',
      outline: 'none',
      fontFamily: 'inherit',
      lineHeight: '1.5',
      transition: 'all 0.2s',
      background: '#f8faf9',
    },
    sendButton: {
      position: 'absolute',
      right: '0.75rem',
      bottom: '0.75rem',
      width: '40px',
      height: '40px',
      borderRadius: '12px',
      border: 'none',
      background: `linear-gradient(135deg, #5a8a4a 0%, #4a7a3a 100%)`,
      color: 'white',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'all 0.2s',
      boxShadow: '0 2px 8px rgba(131, 177, 109, 0.3)',
    },
    hint: {
      marginTop: '0.75rem',
      textAlign: 'center',
      fontSize: '0.75rem',
      color: '#9ca3af',
    },
    kbd: {
      display: 'inline-block',
      padding: '0.125rem 0.375rem',
      fontSize: '0.7rem',
      fontFamily: 'monospace',
      background: '#f0f2f4',
      borderRadius: '4px',
      color: '#6b7280',
    },
  }

  const renderMessage = (message, index) => {
    const isUser = message.role === 'user'
    
    return (
      <div key={index} style={styles.messageRow(isUser)}>
        {!isUser && (
          <div style={styles.avatar(false)}>
            <Bot size={20} color="white" />
          </div>
        )}
        
        <div style={styles.messageBubble(isUser)}>
          <p style={styles.messageText}>{message.content}</p>
          
          {message.recommendation && (
            <div style={{ marginTop: '1rem' }}>
              <RecommendationCard 
                featureKey={message.recommendation} 
                onSelect={handleFeatureSelect}
              />
            </div>
          )}

          {message.showQuickAccess && (
            <div style={{ 
              marginTop: '1rem', 
              display: 'grid', 
              gridTemplateColumns: 'repeat(2, 1fr)', 
              gap: '0.75rem' 
            }}>
              {Object.entries(FEATURES).map(([key, feature]) => (
                <QuickAccessCard 
                  key={key}
                  featureKey={key}
                  feature={feature}
                  onSelect={handleFeatureSelect}
                />
              ))}
            </div>
          )}
        </div>
        
        {isUser && (
          <div style={styles.avatar(true)}>
            <span style={{ color: 'white', fontWeight: '600', fontSize: '0.75rem' }}>You</span>
          </div>
        )}
      </div>
    )
  }

  if (showPlaybookBuilder) {
    return (
      <PlaybookBuilderFlow 
        draft={playbookDraft}
        conversationContext={messages}
        onBack={() => setShowPlaybookBuilder(false)}
        onComplete={(playbook) => console.log('Created:', playbook)}
      />
    )
  }

  return (
    <div style={styles.container}>
      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }
        textarea:focus {
          border-color: '#5a8a4a' !important;
          background: white !important;
          box-shadow: 0 0 0 3px rgba(131, 177, 109, 0.15) !important;
        }
        button:hover {
          transform: translateY(-1px);
        }
      `}</style>

      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerInner}>
          <div style={styles.headerLeft}>
            <div style={styles.iconWrapper}>
              <div style={styles.mainIcon}>
                <Lightbulb size={28} color="white" />
              </div>
              <div style={styles.sparkBadge}>
                <Zap size={12} color="white" />
              </div>
            </div>
            <div>
              <h1 style={styles.title}>Work Advisor</h1>
              <p style={styles.subtitle}>Let's find the right approach together</p>
            </div>
          </div>
          <div style={styles.headerActions}>
            <button 
              style={styles.skipButton}
              onClick={handleSkipAdvisor}
              onMouseEnter={(e) => e.target.style.background = '#f5f7f9'}
              onMouseLeave={(e) => e.target.style.background = 'transparent'}
            >
              I know what I want
            </button>
            <button 
              style={styles.resetButton}
              onClick={handleRestart}
              title="Start over"
              onMouseEnter={(e) => e.target.style.background = '#e8ecef'}
              onMouseLeave={(e) => e.target.style.background = '#f5f7f9'}
            >
              <RotateCcw size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={styles.messagesArea}>
        <div style={styles.messagesInner}>
          {messages.map((msg, i) => renderMessage(msg, i))}
          
          {isLoading && (
            <div style={styles.messageRow(false)}>
              <div style={styles.avatar(false)}>
                <Bot size={20} color="white" />
              </div>
              <div style={{ ...styles.messageBubble(false), ...styles.loadingBubble }}>
                <div style={styles.loadingDot('0ms')} />
                <div style={styles.loadingDot('150ms')} />
                <div style={styles.loadingDot('300ms')} />
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div style={styles.inputArea}>
        <div style={styles.inputInner}>
          <div style={styles.inputWrapper}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe what you're working on..."
              style={styles.textarea}
              rows={2}
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              style={{
                ...styles.sendButton,
                opacity: (!input.trim() || isLoading) ? 0.5 : 1,
                cursor: (!input.trim() || isLoading) ? 'not-allowed' : 'pointer',
              }}
            >
              <Send size={18} />
            </button>
          </div>
          <p style={styles.hint}>
            Press <span style={styles.kbd}>Enter</span> to send • <span style={styles.kbd}>Shift+Enter</span> for new line
          </p>
        </div>
      </div>
    </div>
  )
}

// Recommendation Card
function RecommendationCard({ featureKey, onSelect }) {
  const feature = FEATURES[featureKey]
  if (!feature) return null
  const Icon = feature.icon

  return (
    <button
      onClick={() => onSelect(featureKey)}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        padding: '1rem',
        background: feature.bgColor,
        border: `2px solid ${feature.color}20`,
        borderRadius: '14px',
        cursor: 'pointer',
        transition: 'all 0.2s',
        textAlign: 'left',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)'
        e.currentTarget.style.boxShadow = `0 4px 12px ${feature.color}30`
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      <div style={{
        width: '48px',
        height: '48px',
        borderRadius: '12px',
        background: feature.color,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        boxShadow: `0 3px 10px ${feature.color}40`,
      }}>
        <Icon size={24} color="white" />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ 
          fontWeight: '700', 
          color: COLORS.text,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          {feature.title}
          {!feature.available && (
            <span style={{
              fontSize: '0.65rem',
              padding: '0.2rem 0.5rem',
              background: '#e5e7eb',
              color: '#6b7280',
              borderRadius: '4px',
              fontWeight: '600',
            }}>SOON</span>
          )}
        </div>
        <div style={{ fontSize: '0.85rem', color: COLORS.textMuted, marginTop: '0.25rem' }}>
          {feature.description}
        </div>
      </div>
      <ChevronRight size={20} color={COLORS.textMuted} />
    </button>
  )
}

// Quick Access Card
function QuickAccessCard({ featureKey, feature, onSelect }) {
  const Icon = feature.icon

  return (
    <button
      onClick={() => onSelect(featureKey)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '0.75rem',
        background: feature.bgColor,
        border: `1px solid ${feature.color}20`,
        borderRadius: '10px',
        cursor: feature.available ? 'pointer' : 'default',
        transition: 'all 0.2s',
        opacity: feature.available ? 1 : 0.6,
      }}
      onMouseEnter={(e) => feature.available && (e.currentTarget.style.transform = 'translateY(-1px)')}
      onMouseLeave={(e) => feature.available && (e.currentTarget.style.transform = 'translateY(0)')}
    >
      <div style={{
        width: '32px',
        height: '32px',
        borderRadius: '8px',
        background: feature.color,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}>
        <Icon size={16} color="white" />
      </div>
      <span style={{ 
        fontSize: '0.8rem', 
        fontWeight: '600', 
        color: COLORS.text,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {feature.title}
      </span>
    </button>
  )
}

// Simplified Playbook Builder with AI-generated suggestions
function PlaybookBuilderFlow({ draft, conversationContext, onBack, onComplete }) {
  const [step, setStep] = useState(0)
  const [isGenerating, setIsGenerating] = useState(false)
  const [playbook, setPlaybook] = useState({
    name: draft?.name || '',
    description: draft?.description || '',
    inputs: draft?.inputs || [],
    steps: draft?.steps || [],
    outputs: draft?.outputs || []
  })

  // On mount, if we have conversation context, generate suggestions
  useEffect(() => {
    if (conversationContext && conversationContext.length > 1 && playbook.steps.length === 0) {
      generatePlaybookSuggestions()
    }
  }, [])

  const generatePlaybookSuggestions = async () => {
    setIsGenerating(true)
    
    // Extract user's description from conversation
    const userMessages = conversationContext
      .filter(m => m.role === 'user')
      .map(m => m.content)
      .join('\n')
    
    try {
      const response = await fetch('/api/advisor/generate-playbook', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: userMessages })
      })
      
      if (response.ok) {
        const data = await response.json()
        setPlaybook(prev => ({
          ...prev,
          name: data.name || prev.name,
          description: data.description || prev.description,
          inputs: data.inputs || prev.inputs,
          steps: data.steps || prev.steps,
          outputs: data.outputs || prev.outputs
        }))
      }
    } catch (error) {
      console.error('Failed to generate playbook suggestions:', error)
    } finally {
      setIsGenerating(false)
    }
  }

  const stepTitles = ['Review Plan', 'Refine Inputs', 'Refine Steps', 'Refine Outputs', 'Confirm']

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'linear-gradient(135deg, #f8faf7 0%, #ffffff 50%, #f5f8fc 100%)',
    }}>
      {/* Header */}
      <div style={{
        padding: '1.25rem 1.5rem',
        background: 'white',
        borderBottom: '1px solid #e8ecef',
      }}>
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
            <button
              onClick={onBack}
              style={{
                padding: '0.5rem',
                background: '#f5f7f9',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              <ArrowRight size={18} style={{ transform: 'rotate(180deg)', color: COLORS.textMuted }} />
            </button>
            <div>
              <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: '700', color: COLORS.text }}>
                {isGenerating ? ' Designing Your Playbook...' : 'Build Playbook'}
              </h1>
              <p style={{ margin: 0, fontSize: '0.875rem', color: COLORS.textMuted }}>
                {isGenerating 
                  ? 'AI is drafting steps based on your description'
                  : `Step ${step + 1} of ${stepTitles.length}: ${stepTitles[step]}`
                }
              </p>
            </div>
          </div>
          
          {/* Progress bar */}
          {!isGenerating && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {stepTitles.map((_, i) => (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    height: '4px',
                    borderRadius: '2px',
                    background: i <= step ?'#5a8a4a' : '#e5e7eb',
                    transition: 'background 0.3s',
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '1.5rem' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          {isGenerating ? (
            <GeneratingState />
          ) : (
            <>
              {step === 0 && <StepReviewPlan playbook={playbook} setPlaybook={setPlaybook} onRegenerate={generatePlaybookSuggestions} />}
              {step === 1 && <StepInputs playbook={playbook} setPlaybook={setPlaybook} />}
              {step === 2 && <StepWorkflow playbook={playbook} setPlaybook={setPlaybook} />}
              {step === 3 && <StepOutputs playbook={playbook} setPlaybook={setPlaybook} />}
              {step === 4 && <StepReview playbook={playbook} />}
            </>
          )}
        </div>
      </div>

      {/* Footer */}
      {!isGenerating && (
        <div style={{
          padding: '1rem 1.5rem',
          background: 'white',
          borderTop: '1px solid #e8ecef',
        }}>
          <div style={{ 
            maxWidth: '800px', 
            margin: '0 auto',
            display: 'flex',
            justifyContent: 'space-between',
          }}>
            <button
              onClick={() => setStep(Math.max(0, step - 1))}
              disabled={step === 0}
              style={{
                padding: '0.625rem 1.25rem',
                background: '#f5f7f9',
                border: 'none',
                borderRadius: '10px',
                fontWeight: '600',
                color: COLORS.textMuted,
                cursor: step === 0 ? 'not-allowed' : 'pointer',
                opacity: step === 0 ? 0.5 : 1,
              }}
            >
              Back
            </button>
            <button
              onClick={() => step < 4 ? setStep(step + 1) : onComplete(playbook)}
              style={{
                padding: '0.625rem 1.5rem',
                background: `linear-gradient(135deg, #5a8a4a 0%, #4a7a3a 100%)`,
                border: 'none',
                borderRadius: '10px',
                fontWeight: '600',
                color: 'white',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                boxShadow: '0 2px 8px rgba(131, 177, 109, 0.3)',
              }}
            >
              {step < 4 ? 'Continue' : 'Create Playbook'}
              {step < 4 ? <ArrowRight size={16} /> : <Sparkles size={16} />}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// Loading state while AI generates
function GeneratingState() {
  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      padding: '4rem 2rem',
      textAlign: 'center'
    }}>
      <div style={{
        width: '80px',
        height: '80px',
        borderRadius: '20px',
        background: `linear-gradient(135deg, #5a8a4a 0%, #4a7a3a 100%)`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: '1.5rem',
        boxShadow: '0 4px 20px rgba(131, 177, 109, 0.3)',
        animation: 'pulse 2s infinite',
      }}>
        <Sparkles size={36} color="white" />
      </div>
      <h2 style={{ margin: '0 0 0.5rem', color: COLORS.text }}>Designing Your Playbook</h2>
      <p style={{ color: COLORS.textMuted, maxWidth: '400px' }}>
        Based on your description, I'm drafting the inputs, workflow steps, and outputs. 
        You'll be able to review and refine everything.
      </p>
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.05); }
        }
      `}</style>
    </div>
  )
}

// Step 0: Review AI-generated plan
function StepReviewPlan({ playbook, setPlaybook, onRegenerate }) {
  return (
    <div>
      <div style={{ 
        background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1) 0%, rgba(147, 171, 217, 0.1) 100%)',
        border: '1px solid rgba(131, 177, 109, 0.2)',
        borderRadius: '14px',
        padding: '1.25rem',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '1rem'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          borderRadius: '10px',
          background: '#5a8a4a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0
        }}>
          <Sparkles size={20} color="white" />
        </div>
        <div>
          <div style={{ fontWeight: '600', color: COLORS.text, marginBottom: '0.25rem' }}>
            AI-Generated Draft
          </div>
          <div style={{ fontSize: '0.875rem', color: COLORS.textMuted }}>
            I've drafted a playbook based on your description. Review and edit anything that needs adjustment.
          </div>
        </div>
        <button
          onClick={onRegenerate}
          style={{
            padding: '0.5rem 1rem',
            background: 'white',
            border: '1px solid #e8ecef',
            borderRadius: '8px',
            fontSize: '0.8rem',
            fontWeight: '600',
            color: COLORS.textMuted,
            cursor: 'pointer',
            whiteSpace: 'nowrap'
          }}
        >
          ↻ Regenerate
        </button>
      </div>

      {/* Name & Description */}
      <div style={{ background: 'white', padding: '1.5rem', borderRadius: '14px', border: '1px solid #e8ecef', marginBottom: '1rem' }}>
        <label style={{ display: 'block', fontWeight: '600', marginBottom: '0.75rem', color: COLORS.text }}>
          Playbook Name
        </label>
        <input
          type="text"
          value={playbook.name}
          onChange={(e) => setPlaybook({ ...playbook, name: e.target.value })}
          placeholder="e.g., IRS Reconciliation Analysis"
          style={inputStyle}
        />
        <label style={{ display: 'block', fontWeight: '600', margin: '1rem 0 0.75rem', color: COLORS.text }}>
          Description
        </label>
        <textarea
          value={playbook.description}
          onChange={(e) => setPlaybook({ ...playbook, description: e.target.value })}
          placeholder="What this playbook accomplishes..."
          rows={3}
          style={{ ...inputStyle, resize: 'none' }}
        />
      </div>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
        <SummaryCard 
          icon={Upload} 
          label="Inputs" 
          count={playbook.inputs.length}
          items={playbook.inputs.map(i => i.name)}
          color="#4ecdc4"
        />
        <SummaryCard 
          icon={Compass} 
          label="Steps" 
          count={playbook.steps.length}
          items={playbook.steps.map(s => s.title)}
          color={'#5a8a4a'}
        />
        <SummaryCard 
          icon={FileText} 
          label="Outputs" 
          count={playbook.outputs.length}
          items={playbook.outputs.map(o => o.name)}
          color="#9b7ed9"
        />
      </div>
    </div>
  )
}

function SummaryCard({ icon: Icon, label, count, items, color }) {
  return (
    <div style={{
      background: 'white',
      borderRadius: '14px',
      border: '1px solid #e8ecef',
      padding: '1.25rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          background: `${color}15`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Icon size={18} color={color} />
        </div>
        <div>
          <div style={{ fontSize: '1.5rem', fontWeight: '700', color: COLORS.text }}>{count}</div>
          <div style={{ fontSize: '0.75rem', color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
        </div>
      </div>
      <div style={{ fontSize: '0.8rem', color: COLORS.textMuted }}>
        {items.length > 0 ? (
          <ul style={{ margin: 0, paddingLeft: '1rem' }}>
            {items.slice(0, 3).map((item, i) => (
              <li key={i} style={{ marginBottom: '0.25rem' }}>{item || 'Unnamed'}</li>
            ))}
            {items.length > 3 && <li style={{ fontStyle: 'italic' }}>+{items.length - 3} more</li>}
          </ul>
        ) : (
          <span style={{ fontStyle: 'italic' }}>None defined yet</span>
        )}
      </div>
    </div>
  )
}

// Step components (simplified)
const inputStyle = {
  width: '100%',
  padding: '0.875rem 1rem',
  border: '2px solid #e8ecef',
  borderRadius: '10px',
  fontSize: '0.9375rem',
  outline: 'none',
  transition: 'all 0.2s',
  background: '#f8faf9',
}

function StepName({ playbook, setPlaybook }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ background: 'white', padding: '1.5rem', borderRadius: '14px', border: '1px solid #e8ecef' }}>
        <label style={{ display: 'block', fontWeight: '600', marginBottom: '0.75rem', color: COLORS.text }}>
          Playbook Name
        </label>
        <input
          type="text"
          value={playbook.name}
          onChange={(e) => setPlaybook({ ...playbook, name: e.target.value })}
          placeholder="e.g., Parallel Testing Reconciliation"
          style={inputStyle}
        />
      </div>
      <div style={{ background: 'white', padding: '1.5rem', borderRadius: '14px', border: '1px solid #e8ecef' }}>
        <label style={{ display: 'block', fontWeight: '600', marginBottom: '0.75rem', color: COLORS.text }}>
          What problem does this solve?
        </label>
        <textarea
          value={playbook.description}
          onChange={(e) => setPlaybook({ ...playbook, description: e.target.value })}
          placeholder="Describe the use case..."
          rows={4}
          style={{ ...inputStyle, resize: 'none' }}
        />
      </div>
    </div>
  )
}

function StepInputs({ playbook, setPlaybook }) {
  const add = () => setPlaybook({ ...playbook, inputs: [...playbook.inputs, { name: '', description: '' }] })
  return (
    <div>
      <p style={{ color: COLORS.textMuted, marginBottom: '1rem' }}>What files or data does this playbook need?</p>
      {playbook.inputs.map((inp, i) => (
        <div key={i} style={{ background: 'white', padding: '1rem', borderRadius: '12px', border: '1px solid #e8ecef', marginBottom: '0.75rem' }}>
          <input
            type="text"
            value={inp.name}
            onChange={(e) => {
              const u = [...playbook.inputs]; u[i].name = e.target.value
              setPlaybook({ ...playbook, inputs: u })
            }}
            placeholder="Input name"
            style={{ ...inputStyle, marginBottom: '0.5rem' }}
          />
          <input
            type="text"
            value={inp.description}
            onChange={(e) => {
              const u = [...playbook.inputs]; u[i].description = e.target.value
              setPlaybook({ ...playbook, inputs: u })
            }}
            placeholder="Description"
            style={inputStyle}
          />
        </div>
      ))}
      <button onClick={add} style={{
        width: '100%', padding: '1rem', border: '2px dashed #d1d5db', borderRadius: '12px',
        background: 'transparent', color: COLORS.textMuted, fontWeight: '600', cursor: 'pointer'
      }}>+ Add Input</button>
    </div>
  )
}

function StepWorkflow({ playbook, setPlaybook }) {
  const add = () => setPlaybook({ ...playbook, steps: [...playbook.steps, { title: '', description: '' }] })
  return (
    <div>
      <p style={{ color: COLORS.textMuted, marginBottom: '1rem' }}>What are the workflow steps?</p>
      {playbook.steps.map((s, i) => (
        <div key={i} style={{ background: 'white', padding: '1rem', borderRadius: '12px', border: '1px solid #e8ecef', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <span style={{
              width: '28px', height: '28px', borderRadius: '8px',
              background: '#5a8a4a', color: 'white', fontWeight: '700',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.85rem'
            }}>{i + 1}</span>
            <input
              type="text"
              value={s.title}
              onChange={(e) => {
                const u = [...playbook.steps]; u[i].title = e.target.value
                setPlaybook({ ...playbook, steps: u })
              }}
              placeholder="Step title"
              style={{ ...inputStyle, flex: 1 }}
            />
          </div>
          <textarea
            value={s.description}
            onChange={(e) => {
              const u = [...playbook.steps]; u[i].description = e.target.value
              setPlaybook({ ...playbook, steps: u })
            }}
            placeholder="What happens?"
            rows={2}
            style={{ ...inputStyle, resize: 'none' }}
          />
        </div>
      ))}
      <button onClick={add} style={{
        width: '100%', padding: '1rem', border: '2px dashed #d1d5db', borderRadius: '12px',
        background: 'transparent', color: COLORS.textMuted, fontWeight: '600', cursor: 'pointer'
      }}>+ Add Step</button>
    </div>
  )
}

function StepOutputs({ playbook, setPlaybook }) {
  const add = () => setPlaybook({ ...playbook, outputs: [...playbook.outputs, { name: '', format: 'report' }] })
  return (
    <div>
      <p style={{ color: COLORS.textMuted, marginBottom: '1rem' }}>What deliverables come out?</p>
      {playbook.outputs.map((o, i) => (
        <div key={i} style={{ background: 'white', padding: '1rem', borderRadius: '12px', border: '1px solid #e8ecef', marginBottom: '0.75rem' }}>
          <input
            type="text"
            value={o.name}
            onChange={(e) => {
              const u = [...playbook.outputs]; u[i].name = e.target.value
              setPlaybook({ ...playbook, outputs: u })
            }}
            placeholder="Output name"
            style={{ ...inputStyle, marginBottom: '0.5rem' }}
          />
          <select
            value={o.format}
            onChange={(e) => {
              const u = [...playbook.outputs]; u[i].format = e.target.value
              setPlaybook({ ...playbook, outputs: u })
            }}
            style={inputStyle}
          >
            <option value="report">Report (PDF/Word)</option>
            <option value="spreadsheet">Spreadsheet (Excel)</option>
            <option value="data">Data File (CSV)</option>
            <option value="checklist">Checklist</option>
          </select>
        </div>
      ))}
      <button onClick={add} style={{
        width: '100%', padding: '1rem', border: '2px dashed #d1d5db', borderRadius: '12px',
        background: 'transparent', color: COLORS.textMuted, fontWeight: '600', cursor: 'pointer'
      }}>+ Add Output</button>
    </div>
  )
}

function StepReview({ playbook }) {
  return (
    <div style={{ background: 'white', padding: '1.5rem', borderRadius: '14px', border: '1px solid #e8ecef' }}>
      <h2 style={{ margin: '0 0 0.5rem', color: COLORS.text }}>{playbook.name || 'Untitled'}</h2>
      <p style={{ color: COLORS.textMuted, marginBottom: '1.5rem' }}>{playbook.description || 'No description'}</p>
      
      {playbook.inputs.length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: COLORS.text, fontSize: '0.9rem' }}>📥 Inputs</h4>
          <ul style={{ margin: 0, paddingLeft: '1.25rem', color: COLORS.textMuted }}>
            {playbook.inputs.map((i, idx) => <li key={idx}>{i.name || 'Unnamed'}</li>)}
          </ul>
        </div>
      )}
      
      {playbook.steps.length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: COLORS.text, fontSize: '0.9rem' }}> Steps</h4>
          <ol style={{ margin: 0, paddingLeft: '1.25rem', color: COLORS.textMuted }}>
            {playbook.steps.map((s, idx) => <li key={idx}>{s.title || 'Unnamed'}</li>)}
          </ol>
        </div>
      )}
      
      {playbook.outputs.length > 0 && (
        <div>
          <h4 style={{ margin: '0 0 0.5rem', color: COLORS.text, fontSize: '0.9rem' }}> Outputs</h4>
          <ul style={{ margin: 0, paddingLeft: '1.25rem', color: COLORS.textMuted }}>
            {playbook.outputs.map((o, idx) => <li key={idx}>{o.name || 'Unnamed'} ({o.format})</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
