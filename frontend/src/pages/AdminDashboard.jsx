/**
 * AdminDashboard.jsx - Learning System Administration
 * 
 * View and manage:
 * - Learned query patterns
 * - User preferences
 * - Clarification patterns
 * - Feedback history
 * - Global column mappings
 * - System statistics
 * 
 * Deploy to: frontend/src/pages/AdminDashboard.jsx
 */

import { useState, useEffect } from 'react'
import api from '../services/api'
import {
  Brain, Database, Users, MessageSquare, ThumbsUp, ThumbsDown,
  Trash2, RefreshCw, Download, Search, ChevronDown, ChevronRight,
  BarChart3, TrendingUp, Zap, Settings, Shield, Eye, EyeOff,
  CheckCircle, XCircle, AlertTriangle, Filter, Calendar
} from 'lucide-react'

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
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
    <div style={{ padding: '1.5rem', background: '#f0f2f5', minHeight: 'calc(100vh - 60px)' }}>
      {/* Header - Standard Pattern */}
      <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ 
            margin: 0, 
            fontSize: '20px', 
            fontWeight: 600, 
            color: '#1a2332', 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px',
            fontFamily: "'Sora', sans-serif"
          }}>
            <div style={{ 
              width: '36px', 
              height: '36px', 
              borderRadius: '10px', 
              backgroundColor: '#83b16d', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}>
              <Brain size={20} color="#ffffff" />
            </div>
            Learning Admin
          </h1>
          <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: '#64748b' }}>
            Manage AI learning patterns and preferences
          </p>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={loadDashboardData}
            disabled={loading}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.5rem 1rem', background: 'white', border: '1px solid #e2e8f0',
              borderRadius: 8, cursor: loading ? 'wait' : 'pointer', color: '#64748b',
              fontSize: '0.85rem'
            }}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={() => exportData('all')}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.5rem 1rem', background: '#83b16d', border: 'none',
              borderRadius: 8, cursor: 'pointer', color: 'white',
              fontSize: '0.85rem', fontWeight: 500
            }}
          >
            <Download size={16} />
            Export All
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ 
        display: 'flex', gap: '4px', marginBottom: '1.5rem', 
        background: 'white', borderRadius: 10, padding: '4px', 
        border: '1px solid #e2e8f0', overflowX: 'auto'
      }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.5rem 1rem', borderRadius: 8, border: 'none',
              fontSize: '0.85rem', fontWeight: 500, whiteSpace: 'nowrap',
              cursor: 'pointer', transition: 'all 0.15s',
              background: activeTab === tab.id ? '#83b16d' : 'transparent',
              color: activeTab === tab.id ? 'white' : '#64748b'
            }}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ background: 'white', borderRadius: 10, border: '1px solid #e2e8f0', padding: '1.5rem' }}>
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '5rem' }}>
            <RefreshCw className="animate-spin" size={32} style={{ color: '#83b16d' }} />
          </div>
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
      color: 'green',
      description: 'Query patterns that can be reused'
    },
    { 
      label: 'Feedback Records', 
      value: stats?.feedback_records || 0, 
      icon: MessageSquare, 
      color: 'blue',
      description: 'User ratings collected'
    },
    { 
      label: 'User Preferences', 
      value: stats?.user_preferences || 0, 
      icon: Users, 
      color: 'teal',
      description: 'Learned user choices'
    },
    { 
      label: 'Clarification Patterns', 
      value: stats?.clarification_patterns || 0, 
      icon: Zap, 
      color: 'amber',
      description: 'Auto-answer patterns'
    },
  ]

  const colors = {
    green: 'bg-[rgba(90,138,90,0.15)] text-[#5a8a5a]',
    blue: 'bg-[rgba(74,107,138,0.15)] text-[#285390]',
    teal: 'bg-[rgba(74,122,122,0.15)] text-[#4a7a7a]',
    amber: 'bg-[rgba(138,107,74,0.15)] text-[#d97706]',
  }

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
              <div className={`p-3 rounded-lg ${colors[stat.color]}`}>
                <stat.icon size={24} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Feedback Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 border shadow-sm">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="text-[#5a8a5a]" size={20} />
            Feedback Summary
          </h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Satisfaction Rate</span>
              <span className={`text-2xl font-bold ${
                feedbackRate >= 80 ? 'text-[#5a8a5a]' : 
                feedbackRate >= 60 ? 'text-[#d97706]' : 'text-[#993c44]'
              }`}>
                {feedbackRate}%
              </span>
            </div>
            
            <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
              <div 
                className="h-full bg-[#5a8a5a] rounded-full"
                style={{ width: `${feedbackRate}%` }}
              />
            </div>
            
            <div className="flex justify-between text-sm">
              <span className="flex items-center gap-1 text-[#5a8a5a]">
                <ThumbsUp size={14} /> {positiveCount} positive
              </span>
              <span className="flex items-center gap-1 text-[#993c44]">
                <ThumbsDown size={14} /> {negativeCount} negative
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 border shadow-sm">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Brain className="text-[#5a8a5a]" size={20} />
            Learning Progress
          </h3>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Queries that skip clarification</span>
              <span className="font-medium text-[#5a8a5a]">
                {preferences.filter(p => p.confidence >= 0.7).length} ready
              </span>
            </div>
            
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">High-confidence patterns</span>
              <span className="font-medium text-[#5a8a5a]">
                {learnedQueries.filter(q => q.avg_feedback >= 0.5).length} patterns
              </span>
            </div>
            
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Patterns needing more data</span>
              <span className="font-medium text-[#d97706]">
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
                <div className="p-2 bg-[rgba(90,138,90,0.1)] rounded-lg">
                  <Brain className="text-[#5a8a5a]" size={16} />
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
                  <span className="text-[#5a8a5a]"><ThumbsUp size={14} /></span>
                ) : (
                  <span className="text-[#993c44]"><ThumbsDown size={14} /></span>
                )}
                <span className="text-xs text-gray-400">
                  {new Date(query.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
          
          {learnedQueries.length === 0 && (
            <p className="text-center text-gray-500 py-8">
              No learned patterns yet. Start using Intelligent Chat!
            </p>
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
  const [expandedId, setExpandedId] = useState(null)
  
  const filtered = queries.filter(q => 
    q.question_pattern?.toLowerCase().includes(search.toLowerCase()) ||
    q.semantic_domain?.toLowerCase().includes(search.toLowerCase())
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
            placeholder="Search patterns..."
            className="w-full pl-10 pr-4 py-2 border rounded-lg"
          />
        </div>
        <button
          onClick={onExport}
          className="flex items-center gap-2 px-4 py-2 text-[#5a8a5a] hover:bg-[rgba(90,138,90,0.1)] rounded-lg"
        >
          <Download size={18} />
          Export
        </button>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Pattern</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Domain</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">Uses</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">Feedback</th>
              <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((query) => (
              <tr key={query.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <button
                    onClick={() => setExpandedId(expandedId === query.id ? null : query.id)}
                    className="flex items-center gap-2 text-left"
                  >
                    {expandedId === query.id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    <span className="text-sm font-medium text-gray-900 truncate max-w-xs">
                      {query.question_pattern}
                    </span>
                  </button>
                  {expandedId === query.id && query.successful_sql && (
                    <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-x-auto">
                      {query.successful_sql}
                    </pre>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className="px-2 py-1 bg-[rgba(90,138,90,0.15)] text-[#4a6a4a] text-xs rounded-full">
                    {query.semantic_domain || 'general'}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="text-sm font-medium">{query.use_count}</span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`text-sm font-medium ${
                    query.avg_feedback >= 0.5 ? 'text-[#5a8a5a]' :
                    query.avg_feedback >= 0 ? 'text-gray-600' : 'text-[#993c44]'
                  }`}>
                    {query.avg_feedback >= 0 ? '+' : ''}{query.avg_feedback?.toFixed(1) || '0'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => onDelete(query.id)}
                    className="p-1 text-[#993c44] hover:bg-[rgba(138,74,74,0.1)] rounded"
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
          <div className="text-center py-12 text-gray-500">
            {search ? 'No patterns match your search' : 'No learned patterns yet'}
          </div>
        )}
      </div>
    </div>
  )
}


// =============================================================================
// FEEDBACK TAB
// =============================================================================

function FeedbackTab({ feedback, onDelete }) {
  const [filter, setFilter] = useState('all')
  
  const filtered = feedback.filter(f => 
    filter === 'all' || f.feedback === filter
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        {['all', 'positive', 'negative'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === f
                ? f === 'positive' ? 'bg-[rgba(90,138,90,0.15)] text-[#4a6a4a]' :
                  f === 'negative' ? 'bg-[rgba(138,74,74,0.15)] text-[#6a3a3a]' :
                  'bg-[rgba(90,138,90,0.15)] text-[#4a6a4a]'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f === 'all' ? 'All' : f === 'positive' ? '👍 Positive' : '👎 Negative'}
            <span className="ml-2 text-xs">
              ({f === 'all' ? feedback.length : feedback.filter(x => x.feedback === f).length})
            </span>
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="divide-y">
          {filtered.map((item) => (
            <div key={item.id} className="p-4 hover:bg-gray-50">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${
                    item.feedback === 'positive' ? 'bg-[rgba(90,138,90,0.15)]' : 'bg-[rgba(138,74,74,0.15)]'
                  }`}>
                    {item.feedback === 'positive' 
                      ? <ThumbsUp className="text-[#5a8a5a]" size={16} />
                      : <ThumbsDown className="text-[#993c44]" size={16} />
                    }
                  </div>
                  <div>
                    <p className="text-sm text-gray-900">{item.question}</p>
                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                      <span>{item.project || 'No project'}</span>
                      <span>•</span>
                      <span>{new Date(item.created_at).toLocaleString()}</span>
                      {item.was_intelligent_mode && (
                        <>
                          <span>•</span>
                          <span className="text-[#5a8a5a] flex items-center gap-1"><Brain size={12} /> Intelligent</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => onDelete(item.id)}
                  className="p-1 text-gray-400 hover:text-[#993c44] hover:bg-[rgba(138,74,74,0.1)] rounded"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
        
        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No feedback records yet
          </div>
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
                    <span className="px-2 py-1 bg-[rgba(74,107,138,0.15)] text-[#3a5a7a] text-sm rounded">
                      {pref.preference_value}
                    </span>
                    <span className={`text-xs ${
                      pref.confidence >= 0.8 ? 'text-[#5a8a5a]' : 
                      pref.confidence >= 0.5 ? 'text-[#d97706]' : 'text-gray-500'
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
                  className="p-1 text-gray-400 hover:text-[#993c44] hover:bg-[rgba(138,74,74,0.1)] rounded"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}
      
      {Object.keys(grouped).length === 0 && (
        <div className="bg-white rounded-xl border shadow-sm p-12 text-center text-gray-500">
          No user preferences learned yet
        </div>
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
                        className="h-full bg-[#5a8a5a] rounded-full"
                        style={{ width: `${opt.choice_rate * 100}%` }}
                      />
                    </div>
                  </div>
                  <button
                    onClick={() => onDelete(opt.id)}
                    className="p-1 text-gray-400 hover:text-[#993c44]"
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
        <div className="bg-white rounded-xl border shadow-sm p-12 text-center text-gray-500">
          No clarification patterns yet. Answer some clarification questions!
        </div>
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
                  <span className="px-2 py-1 bg-[rgba(90,138,90,0.15)] text-[#4a6a4a] text-xs rounded-full">
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
                    className="p-1 text-[#993c44] hover:bg-[rgba(138,74,74,0.1)] rounded"
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
          <div className="text-center py-12 text-gray-500">
            {search ? 'No mappings match your search' : 'No global mappings yet'}
          </div>
        )}
      </div>
    </div>
  )
}
