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
  ChevronRight
} from 'lucide-react'

/**
 * WorkAdvisor - A conversational guide that helps users figure out 
 * the best approach for their task.
 * 
 * Philosophy: Most people don't know what they want, they know what 
 * they don't want. So we ask questions, listen, and guide them to
 * the right tool or help them build a playbook.
 */

const ADVISOR_PERSONA = `You are a friendly, experienced implementation consultant helping a colleague figure out the best approach for their task. You're not pushy - you ask thoughtful questions to understand what they're really trying to accomplish.

Your goal is to guide them to one of these outcomes:
1. CHAT - They just need to explore/analyze something with AI assistance (no structured workflow)
2. VACUUM - They need to upload and profile data first
3. BI_BUILDER - They want to build reports, dashboards, or analyze trends
4. PLAYBOOK_EXISTING - Their need matches an existing playbook (Year-End Readiness, etc.)
5. PLAYBOOK_NEW - They need a structured, repeatable workflow that doesn't exist yet
6. COMPARE - They need to compare two datasets and reconcile differences (FUTURE FEATURE)
7. GL_MAPPER - They need to map legacy GL to new system rules (FUTURE FEATURE)

Ask 3-5 questions before making a recommendation. Questions to consider:
- What's the end goal? What deliverable do they need?
- Is this a one-time thing or will they do it repeatedly?
- Do they have files to upload? What kind?
- Do they need structured steps or just guidance?
- Are they comparing things, building something, or analyzing?
- Is there a customer deadline or deliverable involved?

Be conversational, not robotic. Use their language back to them. If they're vague, dig deeper. If they're clear, move faster.

When ready to recommend, be clear about WHY you're recommending that path.`

const INITIAL_MESSAGE = {
  role: 'assistant',
  content: `Hey! 👋 I'm here to help you figure out the best approach for what you're working on.

Tell me a bit about what you're trying to accomplish. Don't worry about using the "right" words - just describe the situation or problem you're dealing with.`,
  timestamp: new Date()
}

// Feature cards for recommendations
const FEATURES = {
  CHAT: {
    icon: MessageSquare,
    title: 'Use Chat',
    description: 'Upload files and have a conversation. Great for exploration, analysis, and getting AI help thinking through problems.',
    color: 'blue',
    route: '/chat',
    available: true
  },
  VACUUM: {
    icon: Upload,
    title: 'Upload Data (Vacuum)',
    description: 'Ingest and profile your data files. This gets them into the system so you can analyze, query, and use them in playbooks.',
    color: 'green',
    route: '/data/vacuum',
    available: true
  },
  BI_BUILDER: {
    icon: BarChart3,
    title: 'BI Builder',
    description: 'Ask questions about your data in plain English. Build charts, reports, and dashboards.',
    color: 'purple',
    route: '/bi-builder',
    available: true
  },
  PLAYBOOK_EXISTING: {
    icon: CheckSquare,
    title: 'Run a Playbook',
    description: 'Follow a structured workflow with defined steps, checks, and deliverables.',
    color: 'amber',
    route: '/playbooks',
    available: true
  },
  PLAYBOOK_NEW: {
    icon: Sparkles,
    title: 'Build a New Playbook',
    description: "Let's create a reusable workflow for this. I'll help you define the steps, inputs, and outputs.",
    color: 'emerald',
    route: null, // Handled specially
    available: true
  },
  COMPARE: {
    icon: GitCompare,
    title: 'Compare & Reconcile',
    description: 'Compare two datasets, find variances, and categorize differences. Perfect for parallel testing and go-live validation.',
    color: 'orange',
    route: '/compare',
    available: false // Not built yet
  },
  GL_MAPPER: {
    icon: FileText,
    title: 'GL Configuration',
    description: 'Map legacy GL structure to new system rules. Upload your files and let AI figure out the mapping.',
    color: 'cyan',
    route: '/gl-mapper',
    available: false // Not built yet
  }
}

const colorClasses = {
  blue: 'bg-blue-50 border-blue-200 text-blue-700',
  green: 'bg-green-50 border-green-200 text-green-700',
  purple: 'bg-purple-50 border-purple-200 text-purple-700',
  amber: 'bg-amber-50 border-amber-200 text-amber-700',
  emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  orange: 'bg-orange-50 border-orange-200 text-orange-700',
  cyan: 'bg-cyan-50 border-cyan-200 text-cyan-700'
}

const iconColorClasses = {
  blue: 'text-blue-500',
  green: 'text-green-500',
  purple: 'text-purple-500',
  amber: 'text-amber-500',
  emerald: 'text-emerald-500',
  orange: 'text-orange-500',
  cyan: 'text-cyan-500'
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

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input on load
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      // Build conversation history for AI
      const conversationHistory = [...messages, userMessage].map(m => ({
        role: m.role,
        content: m.content
      }))

      const response = await fetch('/api/advisor/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: conversationHistory,
          system_prompt: ADVISOR_PERSONA
        })
      })

      if (!response.ok) throw new Error('Advisor request failed')

      const data = await response.json()

      // Check if AI made a recommendation
      if (data.recommendation) {
        setRecommendation(data.recommendation)
        if (data.playbook_draft) {
          setPlaybookDraft(data.playbook_draft)
        }
      }

      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        recommendation: data.recommendation || null
      }

      setMessages(prev => [...prev, assistantMessage])

    } catch (error) {
      console.error('Advisor error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Sorry, I hit a snag. Let me try again - what were you working on?",
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
      // Show "coming soon" message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `The ${feature.title} feature is on our roadmap but not built yet. For now, you could use **Chat** to upload your files and work through this manually, or we could **build a playbook** to structure the workflow. What sounds better?`,
        timestamp: new Date()
      }])
      return
    }

    if (featureKey === 'PLAYBOOK_NEW') {
      setShowPlaybookBuilder(true)
      return
    }

    // Navigate to feature
    window.location.href = feature.route
  }

  const handleSkipAdvisor = () => {
    // Show quick access menu
    setMessages(prev => [...prev, {
      role: 'assistant', 
      content: `No problem! Here's what's available:`,
      timestamp: new Date(),
      showQuickAccess: true
    }])
  }

  // Render a single message
  const renderMessage = (message, index) => {
    const isUser = message.role === 'user'
    
    return (
      <div 
        key={index}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
      >
        <div 
          className={`max-w-[80%] rounded-2xl px-4 py-3 ${
            isUser 
              ? 'bg-[#008751] text-white rounded-br-md' 
              : 'bg-gray-100 text-gray-800 rounded-bl-md'
          }`}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
          
          {/* Show recommendation cards if present */}
          {message.recommendation && (
            <div className="mt-4 space-y-2">
              {Array.isArray(message.recommendation) 
                ? message.recommendation.map(rec => (
                    <RecommendationCard 
                      key={rec} 
                      featureKey={rec} 
                      onSelect={handleFeatureSelect}
                    />
                  ))
                : (
                    <RecommendationCard 
                      featureKey={message.recommendation} 
                      onSelect={handleFeatureSelect}
                    />
                  )
              }
            </div>
          )}

          {/* Quick access grid */}
          {message.showQuickAccess && (
            <div className="mt-4 grid grid-cols-2 gap-2">
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
      </div>
    )
  }

  // Playbook Builder Flow
  if (showPlaybookBuilder) {
    return (
      <PlaybookBuilderFlow 
        draft={playbookDraft}
        conversationContext={messages}
        onBack={() => setShowPlaybookBuilder(false)}
        onComplete={(playbook) => {
          console.log('Playbook created:', playbook)
          // TODO: Save playbook and navigate
        }}
      />
    )
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex-none px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#008751]/10 rounded-xl">
              <Lightbulb className="w-6 h-6 text-[#008751]" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Work Advisor</h1>
              <p className="text-sm text-gray-500">Let's figure out the best approach together</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleSkipAdvisor}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              I know what I want
            </button>
            <button
              onClick={handleRestart}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title="Start over"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.map((message, index) => renderMessage(message, index))}
        
        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex items-center gap-2 text-gray-500">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex-none px-6 py-4 border-t border-gray-200">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe what you're working on..."
              className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-[#008751]/20 focus:border-[#008751] transition-all"
              rows={2}
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="absolute right-2 bottom-2 p-2 bg-[#008751] text-white rounded-lg hover:bg-[#007244] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
        <p className="mt-2 text-xs text-gray-400 text-center">
          Press Enter to send • Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}

// Recommendation card component
function RecommendationCard({ featureKey, onSelect }) {
  const feature = FEATURES[featureKey]
  if (!feature) return null

  const Icon = feature.icon
  
  return (
    <button
      onClick={() => onSelect(featureKey)}
      className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition-all hover:scale-[1.02] ${colorClasses[feature.color]} ${!feature.available ? 'opacity-60' : ''}`}
    >
      <Icon className={`w-5 h-5 ${iconColorClasses[feature.color]}`} />
      <div className="flex-1 text-left">
        <div className="font-medium flex items-center gap-2">
          {feature.title}
          {!feature.available && (
            <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">Coming Soon</span>
          )}
        </div>
        <div className="text-sm opacity-80">{feature.description}</div>
      </div>
      <ChevronRight className="w-5 h-5 opacity-50" />
    </button>
  )
}

// Quick access card (smaller, for grid)
function QuickAccessCard({ featureKey, feature, onSelect }) {
  const Icon = feature.icon
  
  return (
    <button
      onClick={() => onSelect(featureKey)}
      className={`flex items-center gap-2 p-2 rounded-lg border transition-all hover:scale-[1.02] ${colorClasses[feature.color]} ${!feature.available ? 'opacity-60' : ''}`}
    >
      <Icon className={`w-4 h-4 ${iconColorClasses[feature.color]}`} />
      <span className="text-sm font-medium truncate">{feature.title}</span>
    </button>
  )
}

// Playbook Builder Flow (simplified for now)
function PlaybookBuilderFlow({ draft, conversationContext, onBack, onComplete }) {
  const [step, setStep] = useState(0)
  const [playbook, setPlaybook] = useState({
    name: draft?.name || '',
    description: draft?.description || '',
    inputs: draft?.inputs || [],
    steps: draft?.steps || [],
    outputs: draft?.outputs || []
  })

  const steps = [
    { title: 'Name & Purpose', component: StepNamePurpose },
    { title: 'Inputs', component: StepInputs },
    { title: 'Workflow Steps', component: StepWorkflow },
    { title: 'Outputs', component: StepOutputs },
    { title: 'Review', component: StepReview }
  ]

  const CurrentStepComponent = steps[step].component

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex-none px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowRight className="w-5 h-5 rotate-180 text-gray-600" />
            </button>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Build Playbook</h1>
              <p className="text-sm text-gray-500">Step {step + 1} of {steps.length}: {steps[step].title}</p>
            </div>
          </div>
        </div>
        
        {/* Progress bar */}
        <div className="mt-4 flex gap-1">
          {steps.map((s, i) => (
            <div 
              key={i}
              className={`flex-1 h-1 rounded-full transition-colors ${i <= step ? 'bg-[#008751]' : 'bg-gray-200'}`}
            />
          ))}
        </div>
      </div>

      {/* Step content */}
      <div className="flex-1 overflow-y-auto p-6">
        <CurrentStepComponent 
          playbook={playbook}
          setPlaybook={setPlaybook}
          conversationContext={conversationContext}
        />
      </div>

      {/* Navigation */}
      <div className="flex-none px-6 py-4 border-t border-gray-200">
        <div className="flex justify-between">
          <button
            onClick={() => setStep(Math.max(0, step - 1))}
            disabled={step === 0}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Back
          </button>
          {step < steps.length - 1 ? (
            <button
              onClick={() => setStep(step + 1)}
              className="px-6 py-2 bg-[#008751] text-white rounded-lg hover:bg-[#007244] transition-colors flex items-center gap-2"
            >
              Continue
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => onComplete(playbook)}
              className="px-6 py-2 bg-[#008751] text-white rounded-lg hover:bg-[#007244] transition-colors flex items-center gap-2"
            >
              Create Playbook
              <Sparkles className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// Step components (simplified placeholders - we'll flesh these out)
function StepNamePurpose({ playbook, setPlaybook }) {
  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Playbook Name
        </label>
        <input
          type="text"
          value={playbook.name}
          onChange={(e) => setPlaybook({ ...playbook, name: e.target.value })}
          placeholder="e.g., Parallel Testing Reconciliation"
          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#008751]/20 focus:border-[#008751]"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          What problem does this solve?
        </label>
        <textarea
          value={playbook.description}
          onChange={(e) => setPlaybook({ ...playbook, description: e.target.value })}
          placeholder="Describe the use case and what success looks like..."
          rows={4}
          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#008751]/20 focus:border-[#008751] resize-none"
        />
      </div>
    </div>
  )
}

function StepInputs({ playbook, setPlaybook }) {
  const addInput = () => {
    setPlaybook({
      ...playbook,
      inputs: [...playbook.inputs, { name: '', type: 'file', description: '' }]
    })
  }

  return (
    <div className="max-w-2xl space-y-6">
      <p className="text-gray-600">What files or data does this playbook need to get started?</p>
      
      {playbook.inputs.map((input, i) => (
        <div key={i} className="p-4 border border-gray-200 rounded-xl space-y-3">
          <input
            type="text"
            value={input.name}
            onChange={(e) => {
              const updated = [...playbook.inputs]
              updated[i].name = e.target.value
              setPlaybook({ ...playbook, inputs: updated })
            }}
            placeholder="Input name (e.g., Historical Pay Register)"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#008751]/20 focus:border-[#008751]"
          />
          <input
            type="text"
            value={input.description}
            onChange={(e) => {
              const updated = [...playbook.inputs]
              updated[i].description = e.target.value
              setPlaybook({ ...playbook, inputs: updated })
            }}
            placeholder="Description (e.g., Last 3 months of pay data from legacy system)"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#008751]/20 focus:border-[#008751]"
          />
        </div>
      ))}
      
      <button
        onClick={addInput}
        className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-[#008751] hover:text-[#008751] transition-colors"
      >
        + Add Input
      </button>
    </div>
  )
}

function StepWorkflow({ playbook, setPlaybook }) {
  const addStep = () => {
    setPlaybook({
      ...playbook,
      steps: [...playbook.steps, { title: '', description: '', ai_assisted: true }]
    })
  }

  return (
    <div className="max-w-2xl space-y-6">
      <p className="text-gray-600">What are the steps in this workflow?</p>
      
      {playbook.steps.map((step, i) => (
        <div key={i} className="p-4 border border-gray-200 rounded-xl space-y-3">
          <div className="flex items-center gap-3">
            <span className="w-8 h-8 flex items-center justify-center bg-[#008751]/10 text-[#008751] font-semibold rounded-full">
              {i + 1}
            </span>
            <input
              type="text"
              value={step.title}
              onChange={(e) => {
                const updated = [...playbook.steps]
                updated[i].title = e.target.value
                setPlaybook({ ...playbook, steps: updated })
              }}
              placeholder="Step title"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#008751]/20 focus:border-[#008751]"
            />
          </div>
          <textarea
            value={step.description}
            onChange={(e) => {
              const updated = [...playbook.steps]
              updated[i].description = e.target.value
              setPlaybook({ ...playbook, steps: updated })
            }}
            placeholder="What happens in this step?"
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#008751]/20 focus:border-[#008751] resize-none"
          />
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={step.ai_assisted}
              onChange={(e) => {
                const updated = [...playbook.steps]
                updated[i].ai_assisted = e.target.checked
                setPlaybook({ ...playbook, steps: updated })
              }}
              className="rounded border-gray-300 text-[#008751] focus:ring-[#008751]"
            />
            AI assists with this step
          </label>
        </div>
      ))}
      
      <button
        onClick={addStep}
        className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-[#008751] hover:text-[#008751] transition-colors"
      >
        + Add Step
      </button>
    </div>
  )
}

function StepOutputs({ playbook, setPlaybook }) {
  const addOutput = () => {
    setPlaybook({
      ...playbook,
      outputs: [...playbook.outputs, { name: '', format: 'report', description: '' }]
    })
  }

  return (
    <div className="max-w-2xl space-y-6">
      <p className="text-gray-600">What deliverables come out of this playbook?</p>
      
      {playbook.outputs.map((output, i) => (
        <div key={i} className="p-4 border border-gray-200 rounded-xl space-y-3">
          <input
            type="text"
            value={output.name}
            onChange={(e) => {
              const updated = [...playbook.outputs]
              updated[i].name = e.target.value
              setPlaybook({ ...playbook, outputs: updated })
            }}
            placeholder="Output name (e.g., Variance Report)"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#008751]/20 focus:border-[#008751]"
          />
          <select
            value={output.format}
            onChange={(e) => {
              const updated = [...playbook.outputs]
              updated[i].format = e.target.value
              setPlaybook({ ...playbook, outputs: updated })
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#008751]/20 focus:border-[#008751]"
          >
            <option value="report">Report (PDF/Word)</option>
            <option value="spreadsheet">Spreadsheet (Excel)</option>
            <option value="data">Data File (CSV)</option>
            <option value="checklist">Checklist</option>
            <option value="config">Configuration File</option>
          </select>
        </div>
      ))}
      
      <button
        onClick={addOutput}
        className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-[#008751] hover:text-[#008751] transition-colors"
      >
        + Add Output
      </button>
    </div>
  )
}

function StepReview({ playbook }) {
  return (
    <div className="max-w-2xl space-y-6">
      <div className="p-6 bg-gray-50 rounded-xl space-y-4">
        <h3 className="text-xl font-semibold text-gray-900">{playbook.name || 'Untitled Playbook'}</h3>
        <p className="text-gray-600">{playbook.description || 'No description'}</p>
        
        {playbook.inputs.length > 0 && (
          <div>
            <h4 className="font-medium text-gray-700 mb-2">Inputs</h4>
            <ul className="list-disc list-inside text-gray-600">
              {playbook.inputs.map((input, i) => (
                <li key={i}>{input.name || 'Unnamed input'}</li>
              ))}
            </ul>
          </div>
        )}
        
        {playbook.steps.length > 0 && (
          <div>
            <h4 className="font-medium text-gray-700 mb-2">Steps</h4>
            <ol className="list-decimal list-inside text-gray-600">
              {playbook.steps.map((step, i) => (
                <li key={i}>{step.title || 'Unnamed step'}</li>
              ))}
            </ol>
          </div>
        )}
        
        {playbook.outputs.length > 0 && (
          <div>
            <h4 className="font-medium text-gray-700 mb-2">Outputs</h4>
            <ul className="list-disc list-inside text-gray-600">
              {playbook.outputs.map((output, i) => (
                <li key={i}>{output.name || 'Unnamed output'} ({output.format})</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
