/**
 * AdminDashboard.jsx - Learning System Administration
 * 
 * POLISHED: All purple → grassGreen for consistency
 * 
 * View and manage:
 * - Learned query patterns
 * - User preferences
 * - Clarification patterns
 * - Feedback history
 * - Global column mappings
 * - System statistics
 */

import { useState, useEffect } from 'react'
import api from '../services/api'
import { LoadingSpinner, ErrorState, EmptyState, PageHeader, COLORS } from '../components/ui'
import {
  Brain, Database, Users, MessageSquare, ThumbsUp, ThumbsDown,
  Trash2, RefreshCw, Download, Search, ChevronDown, ChevronRight,
  BarChart3, TrendingUp, Zap, Settings, Shield, Eye, EyeOff,
  CheckCircle, XCircle, AlertTriangle, Filter, Calendar
} from 'lucide-react'

// Brand color for consistent styling
const BRAND = COLORS.grassGreen;
const BRAND_LIGHT = '#f0fdf4';
const BRAND_BORDER = '#bbf7d0';

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)
  
  // Data for each section
  const [learnedQueries, setLearnedQueries] = useState([])
  const [feedback, setFeedback] = useState([])
  const [preferences, setPreferences] = useState([])
  const [clarificationPatterns, setClarificationPatterns] = useState([])
  const [globalMappings, setGlobalMappings] = useState([])
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('')
  const [dateFilter, setDateFilter] = useState('all')

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setLoading(true)
    setError(null)
    try {
      // Load learning stats
      const statsRes = await api.get('/chat/intelligent/learning/stats')
      setStats(statsRes.data)
      
      // Load all data in parallel
      const [queriesRes, feedbackRes, prefsRes, clarifyRes, mappingsRes] = await Promise.all([
        api.get('/admin/learning/queries').catch(() => ({ data: [] })),
        api.get('/admin/learning/feedback').catch(() => ({ data: [] })),
        api.get('/admin/learning/preferences').catch(() => ({ data: [] })),
        api.get('/admin/learning/clarifications').catch(() => ({ data: [] })),
        api.get('/admin/learning/mappings').catch(() => ({ data: [] })),
      ])
      
      setLearnedQueries(queriesRes.data || [])
      setFeedback(feedbackRes.data || [])
      setPreferences(prefsRes.data || [])
      setClarificationPatterns(clarifyRes.data || [])
      setGlobalMappings(mappingsRes.data || [])
      
    } catch (err) {
      console.error('Failed to load dashboard data:', err)
      setError('Failed to load learning data. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const deleteItem = async (table, id) => {
    if (!confirm('Are you sure you want to delete this item?')) return
    
    try {
      await api.delete(`/admin/learning/${table}/${id}`)
      loadDashboardData()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const exportData = async (type) => {
    try {
      const res = await api.get(`/admin/learning/export/${type}`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${type}_export_${new Date().toISOString().split('T')[0]}.json`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err) {
      console.error('Export failed:', err)
    }
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'queries', label: 'Learned Queries', icon: Brain },
    { id: 'feedback', label: 'Feedback', icon: MessageSquare },
    { id: 'preferences', label: 'User Preferences', icon: Users },
    { id: 'clarifications', label: 'Clarification Patterns', icon: Zap },
    { id: 'mappings', label: 'Column Mappings', icon: Database },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg" style={{ background: BRAND_LIGHT }}>
                <Shield style={{ color: BRAND }} size={24} />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Learning Admin</h1>
                <p className="text-sm text-gray-500">Manage AI learning patterns and preferences</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <button
                onClick={loadDashboardData}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
                title="Refresh"
              >
                <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
              </button>
              <button
                onClick={() => exportData('all')}
                className="flex items-center gap-2 px-4 py-2 text-white rounded-lg hover:opacity-90"
                style={{ background: BRAND }}
              >
                <Download size={18} />
                Export All
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-white rounded-lg p-1 shadow-sm border overflow-x-auto">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all"
              style={activeTab === tab.id ? {
                background: BRAND,
                color: 'white'
              } : {
                color: '#6b7280'
              }}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {loading ? (
          <LoadingSpinner fullPage message="Loading learning data..." />
        ) : error ? (
          <ErrorState
            fullPage
            title="Failed to Load Data"
            message={error}
            onRetry={loadDashboardData}
          />
        ) : (
          <>
            {activeTab === 'overview' && (
              <OverviewTab 
                stats={stats} 
                learnedQueries={learnedQueries}
                feedback={feedback}
                preferences={preferences}
              />
            )}
            {activeTab === 'queries' && (
              <QueriesTab 
                queries={learnedQueries} 
                onDelete={(id) => deleteItem('queries', id)}
                onExport={() => exportData('queries')}
              />
            )}
            {activeTab === 'feedback' && (
              <FeedbackTab 
                feedback={feedback}
                onDelete={(id) => deleteItem('feedback', id)}
              />
            )}
            {activeTab === 'preferences' && (
              <PreferencesTab 
                preferences={preferences}
                onDelete={(id) => deleteItem('preferences', id)}
              />
            )}
            {activeTab === 'clarifications' && (
              <ClarificationsTab 
                patterns={clarificationPatterns}
                onDelete={(id) => deleteItem('clarifications', id)}
              />
            )}
            {activeTab === 'mappings' && (
              <MappingsTab 
                mappings={globalMappings}
                onDelete={(id) => deleteItem('mappings', id)}
                onRefresh={loadDashboardData}
              />
            )}
          </>
        )}
      </div>
    </div>
  )
}


// =============================================================================
// OVERVIEW TAB
// =============================================================================

function OverviewTab({ stats, learnedQueries, feedback, preferences }) {
  const positiveCount = feedback.filter(f => f.feedback === 'positive').length
  const negativeCount = feedback.filter(f => f.feedback === 'negative').length
  const feedbackRate = feedback.length > 0 
    ? ((positiveCount / feedback.length) * 100).toFixed(0) 
    : 0

  const statCards = [
    { 
      label: 'Learned Patterns', 
      value: stats?.learned_queries || 0, 
      icon: Brain, 
      color: BRAND,
      bgColor: BRAND_LIGHT,
      description: 'Query patterns that can be reused'
    },
    { 
      label: 'Feedback Records', 
      value: stats?.feedback_records || 0, 
      icon: MessageSquare, 
      color: '#3b82f6',
      bgColor: '#eff6ff',
      description: 'User ratings collected'
    },
    { 
      label: 'User Preferences', 
      value: stats?.user_preferences || 0, 
      icon: Users, 
      color: '#10b981',
      bgColor: '#ecfdf5',
      description: 'Learned user choices'
    },
    { 
      label: 'Clarification Patterns', 
      value: stats?.clarification_patterns || 0, 
      icon: Zap, 
      color: '#f59e0b',
      bgColor: '#fffbeb',
      description: 'Auto-answer patterns'
    },
  ]

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat, i) => (
          <div key={i} className="bg-white rounded-xl p-5 border shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-500">{stat.label}</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
                <p className="text-xs text-gray-400 mt-1">{stat.description}</p>
              </div>
              <div className="p-3 rounded-lg" style={{ background: stat.bgColor }}>
                <stat.icon size={24} style={{ color: stat.color }} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Feedback Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 border shadow-sm">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="text-green-500" size={20} />
            Feedback Summary
          </h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Satisfaction Rate</span>
              <span className={`text-2xl font-bold ${
                feedbackRate >= 80 ? 'text-green-600' : 
                feedbackRate >= 60 ? 'text-amber-600' : 'text-red-600'
              }`}>
                {feedbackRate}%
              </span>
            </div>
            
            <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
              <div 
                className="h-full rounded-full"
                style={{ width: `${feedbackRate}%`, background: BRAND }}
              />
            </div>
            
            <div className="flex justify-between text-sm">
              <span className="flex items-center gap-1 text-green-600">
                <ThumbsUp size={14} /> {positiveCount} positive
              </span>
              <span className="flex items-center gap-1 text-red-600">
                <ThumbsDown size={14} /> {negativeCount} negative
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 border shadow-sm">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Brain size={20} style={{ color: BRAND }} />
            Learning Progress
          </h3>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Queries that skip clarification</span>
              <span className="font-medium" style={{ color: BRAND }}>
                {preferences.filter(p => p.confidence >= 0.7).length} ready
              </span>
            </div>
            
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">High-confidence patterns</span>
              <span className="font-medium text-green-600">
                {learnedQueries.filter(q => q.avg_feedback >= 0.5).length} patterns
              </span>
            </div>
            
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Patterns needing more data</span>
              <span className="font-medium text-amber-600">
                {learnedQueries.filter(q => q.use_count < 3).length} patterns
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl p-6 border shadow-sm">
        <h3 className="font-semibold text-gray-900 mb-4">Recent Learning Activity</h3>
        
        <div className="space-y-3">
          {learnedQueries.slice(0, 5).map((query, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ background: BRAND_LIGHT }}>
                  <Brain size={16} style={{ color: BRAND }} />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900 truncate max-w-md">
                    {query.question_pattern}
                  </p>
                  <p className="text-xs text-gray-500">
                    {query.semantic_domain} • Used {query.use_count}x
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {query.avg_feedback >= 0 ? (
                  <span className="text-green-500"><ThumbsUp size={14} /></span>
                ) : (
                  <span className="text-red-500"><ThumbsDown size={14} /></span>
                )}
                <span className="text-xs text-gray-400">
                  {new Date(query.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
          
          {learnedQueries.length === 0 && (
            <EmptyState
              icon="🧠"
              title="No learned patterns yet"
              description="Start using Intelligent Chat to begin learning!"
            />
          )}
        </div>
      </div>
    </div>
  )
}


// =============================================================================
// QUERIES TAB
// =============================================================================

function QueriesTab({ queries, onDelete, onExport }) {
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState({})
  
  const filtered = queries.filter(q =>
    q.question_pattern?.toLowerCase().includes(search.toLowerCase()) ||
    q.semantic_domain?.toLowerCase().includes(search.toLowerCase())
  )

  const grouped = filtered.reduce((acc, q) => {
    const domain = q.semantic_domain || 'other'
    if (!acc[domain]) acc[domain] = []
    acc[domain].push(q)
    return acc
  }, {})

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search patterns..."
            className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2"
            style={{ '--tw-ring-color': BRAND }}
          />
        </div>
        <button
          onClick={onExport}
          className="flex items-center gap-2 px-4 py-2 text-white rounded-lg"
          style={{ background: BRAND }}
        >
          <Download size={18} />
          Export
        </button>
      </div>

      {Object.entries(grouped).map(([domain, domainQueries]) => (
        <div key={domain} className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <button
            onClick={() => setExpanded(e => ({ ...e, [domain]: !e[domain] }))}
            className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100"
          >
            <div className="flex items-center gap-2">
              <Brain size={18} style={{ color: BRAND }} />
              <span className="font-medium text-gray-900">{domain}</span>
              <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
                {domainQueries.length}
              </span>
            </div>
            {expanded[domain] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          </button>
          
          {expanded[domain] && (
            <div className="divide-y">
              {domainQueries.map((query) => (
                <div key={query.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{query.question_pattern}</p>
                      <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
                        <span>Used {query.use_count}x</span>
                        <span>Avg feedback: {(query.avg_feedback || 0).toFixed(2)}</span>
                        <span>{new Date(query.created_at).toLocaleDateString()}</span>
                      </div>
                      {query.sql_pattern && (
                        <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-x-auto">
                          {query.sql_pattern}
                        </pre>
                      )}
                    </div>
                    <button
                      onClick={() => onDelete(query.id)}
                      className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
      
      {Object.keys(grouped).length === 0 && (
        <EmptyState
          icon="🧠"
          title="No learned queries"
          description="Query patterns will appear here as the system learns."
        />
      )}
    </div>
  )
}


// =============================================================================
// FEEDBACK TAB
// =============================================================================

function FeedbackTab({ feedback, onDelete }) {
  const [filter, setFilter] = useState('all')
  
  const filtered = feedback.filter(f => {
    if (filter === 'positive') return f.feedback === 'positive'
    if (filter === 'negative') return f.feedback === 'negative'
    return true
  })

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {['all', 'positive', 'negative'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
            style={filter === f ? {
              background: BRAND,
              color: 'white'
            } : {
              background: '#f3f4f6',
              color: '#6b7280'
            }}
          >
            {f === 'all' ? 'All' : f === 'positive' ? '👍 Positive' : '👎 Negative'}
          </button>
        ))}
        <span className="ml-auto text-sm text-gray-500 self-center">
          {filtered.length} records
        </span>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Query</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">Rating</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Comment</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((fb) => (
              <tr key={fb.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 max-w-md">
                  <p className="text-sm text-gray-900 truncate">{fb.question}</p>
                </td>
                <td className="px-4 py-3 text-center">
                  {fb.feedback === 'positive' ? (
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium" style={{ background: BRAND_LIGHT, color: BRAND }}>
                      <ThumbsUp size={12} /> Good
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                      <ThumbsDown size={12} /> Bad
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <p className="text-sm text-gray-600 truncate max-w-xs">
                    {fb.feedback_text || '-'}
                  </p>
                </td>
                <td className="px-4 py-3 text-center text-xs text-gray-500">
                  {new Date(fb.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => onDelete(fb.id)}
                    className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {filtered.length === 0 && (
          <EmptyState
            icon="💬"
            title="No feedback records"
            description={filter !== 'all' ? 'Try changing the filter' : 'Feedback will appear as users rate responses'}
          />
        )}
      </div>
    </div>
  )
}


// =============================================================================
// PREFERENCES TAB
// =============================================================================

function PreferencesTab({ preferences, onDelete }) {
  const grouped = preferences.reduce((acc, pref) => {
    const key = pref.preference_key || 'other'
    if (!acc[key]) acc[key] = []
    acc[key].push(pref)
    return acc
  }, {})

  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([key, prefs]) => (
        <div key={key} className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b">
            <h3 className="font-medium text-gray-900">{key}</h3>
            <p className="text-xs text-gray-500">{prefs.length} preference(s)</p>
          </div>
          
          <div className="divide-y">
            {prefs.map((pref) => (
              <div key={pref.id} className="p-4 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-1 text-sm rounded" style={{ background: BRAND_LIGHT, color: BRAND }}>
                      {pref.preference_value}
                    </span>
                    <span className={`text-xs ${
                      pref.confidence >= 0.8 ? 'text-green-600' : 
                      pref.confidence >= 0.5 ? 'text-amber-600' : 'text-gray-500'
                    }`}>
                      {(pref.confidence * 100).toFixed(0)}% confident
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {pref.semantic_domain && <span>{pref.semantic_domain} • </span>}
                    Used {pref.use_count}x • Learned from {pref.learned_from}
                  </div>
                </div>
                <button
                  onClick={() => onDelete(pref.id)}
                  className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}
      
      {Object.keys(grouped).length === 0 && (
        <EmptyState
          icon="👤"
          title="No user preferences learned yet"
          description="Preferences are learned as users make choices in conversations."
        />
      )}
    </div>
  )
}


// =============================================================================
// CLARIFICATIONS TAB
// =============================================================================

function ClarificationsTab({ patterns, onDelete }) {
  const grouped = patterns.reduce((acc, p) => {
    const key = p.question_id || 'other'
    if (!acc[key]) acc[key] = []
    acc[key].push(p)
    return acc
  }, {})

  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([questionId, options]) => {
        const total = options.reduce((sum, o) => sum + o.choice_count, 0)
        
        return (
          <div key={questionId} className="bg-white rounded-xl border shadow-sm overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b">
              <h3 className="font-medium text-gray-900">{questionId}</h3>
              <p className="text-xs text-gray-500">{total} total responses</p>
            </div>
            
            <div className="p-4 space-y-2">
              {options.sort((a, b) => b.choice_rate - a.choice_rate).map((opt) => (
                <div key={opt.id} className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{opt.chosen_option}</span>
                      <span className="text-xs text-gray-500">
                        {(opt.choice_rate * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div 
                        className="h-full rounded-full"
                        style={{ width: `${opt.choice_rate * 100}%`, background: BRAND }}
                      />
                    </div>
                  </div>
                  <button
                    onClick={() => onDelete(opt.id)}
                    className="p-1 text-gray-400 hover:text-red-500"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )
      })}
      
      {Object.keys(grouped).length === 0 && (
        <EmptyState
          icon="❓"
          title="No clarification patterns yet"
          description="Answer some clarification questions to start learning!"
        />
      )}
    </div>
  )
}


// =============================================================================
// MAPPINGS TAB (Global Column Mappings from Data Model)
// =============================================================================

function MappingsTab({ mappings, onDelete, onRefresh }) {
  const [search, setSearch] = useState('')
  
  const filtered = mappings.filter(m =>
    m.column_pattern_1?.toLowerCase().includes(search.toLowerCase()) ||
    m.column_pattern_2?.toLowerCase().includes(search.toLowerCase()) ||
    m.semantic_type?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search mappings..."
            className="w-full pl-10 pr-4 py-2 border rounded-lg"
          />
        </div>
        <span className="text-sm text-gray-500">
          {mappings.length} global mappings
        </span>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Column 1</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">↔</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Column 2</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">Confirmed</th>
              <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((mapping) => (
              <tr key={mapping.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <code className="text-sm bg-gray-100 px-2 py-0.5 rounded">
                    {mapping.column_pattern_1}
                  </code>
                </td>
                <td className="px-4 py-3 text-center text-gray-400">↔</td>
                <td className="px-4 py-3">
                  <code className="text-sm bg-gray-100 px-2 py-0.5 rounded">
                    {mapping.column_pattern_2}
                  </code>
                </td>
                <td className="px-4 py-3">
                  <span className="px-2 py-1 text-xs rounded-full" style={{ background: BRAND_LIGHT, color: BRAND }}>
                    {mapping.semantic_type || 'unknown'}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="text-sm font-medium text-gray-900">
                    {mapping.confirmed_count || 1}x
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => onDelete(mapping.id)}
                    className="p-1 text-red-500 hover:bg-red-50 rounded"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {filtered.length === 0 && (
          <EmptyState
            icon="🔗"
            title={search ? 'No mappings match your search' : 'No global mappings yet'}
            description="Column mappings are learned from the Data Model page."
          />
        )}
      </div>
    </div>
  )
}
