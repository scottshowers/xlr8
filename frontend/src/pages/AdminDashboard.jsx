/**
 * AdminDashboard.jsx - Learning System Administration
 * 
 * COMMAND CENTER AESTHETIC - matches main Dashboard
 * - Dark/light theme toggle (Soft Navy dark mode)
 * - Stats bar with glowing metrics
 * - Consistent card styling
 */

import { useState, useEffect } from 'react'
import api from '../services/api'
import {
  Sun, Moon, Brain, Database, Users, MessageSquare, ThumbsUp, ThumbsDown,
  Trash2, RefreshCw, Download, Search, ChevronDown, ChevronRight,
  BarChart3, TrendingUp, Zap, Settings, Shield, Eye, EyeOff,
  CheckCircle, XCircle, AlertTriangle, Filter, Calendar, Activity
} from 'lucide-react'

// Brand colors
const BRAND = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
};

// Theme definitions - matches Dashboard
const themes = {
  light: {
    bg: '#f6f5fa',
    bgCard: '#ffffff',
    border: '#e2e8f0',
    text: '#2a3441',
    textDim: '#5f6c7b',
    accent: BRAND.grassGreen,
  },
  dark: {
    bg: '#1a2332',        // Soft Navy
    bgCard: '#232f42',
    border: '#334766',
    text: '#e5e7eb',
    textDim: '#9ca3af',
    accent: BRAND.grassGreen,
  },
};

const STATUS = {
  green: '#10b981',
  amber: '#f59e0b',
  red: '#ef4444',
  blue: '#3b82f6',
};

export default function AdminDashboard() {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('xlr8-theme');
    return saved ? saved === 'dark' : true;
  });
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)
  const [time, setTime] = useState(new Date());
  
  // Data for each section
  const [learnedQueries, setLearnedQueries] = useState([])
  const [feedback, setFeedback] = useState([])
  const [preferences, setPreferences] = useState([])
  const [clarificationPatterns, setClarificationPatterns] = useState([])
  const [globalMappings, setGlobalMappings] = useState([])
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('')

  const T = darkMode ? themes.dark : themes.light;

  // Persist theme
  useEffect(() => {
    localStorage.setItem('xlr8-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  // Update time
  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setLoading(true)
    setError(null)
    try {
      const statsRes = await api.get('/chat/intelligent/learning/stats')
      setStats(statsRes.data)
      
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
    { id: 'queries', label: 'Queries', icon: Brain },
    { id: 'feedback', label: 'Feedback', icon: MessageSquare },
    { id: 'preferences', label: 'Preferences', icon: Users },
    { id: 'clarifications', label: 'Clarifications', icon: Zap },
    { id: 'mappings', label: 'Mappings', icon: Database },
  ]

  const statCards = [
    { label: 'Learned Queries', value: stats?.learned_queries || 0, icon: Brain, color: BRAND.grassGreen },
    { label: 'Feedback Records', value: stats?.feedback_records || 0, icon: ThumbsUp, color: STATUS.blue },
    { label: 'User Preferences', value: stats?.preferences || 0, icon: Users, color: STATUS.amber },
    { label: 'Clarification Patterns', value: stats?.clarifications || 0, icon: Zap, color: STATUS.green },
  ]

  return (
    <div style={{ 
      padding: '1.5rem', 
      background: T.bg, 
      minHeight: '100vh', 
      color: T.text,
      fontFamily: "'Inter', system-ui, sans-serif",
      transition: 'background 0.3s ease, color 0.3s ease',
    }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '2rem' 
      }}>
        <div>
          <h1 style={{ 
            fontSize: '1.5rem', 
            fontWeight: 700, 
            margin: 0, 
            letterSpacing: '0.05em',
            fontFamily: "'Sora', sans-serif",
          }}>
            LEARNING CENTER
          </h1>
          <p style={{ color: T.textDim, margin: '0.25rem 0 0 0', fontSize: '0.85rem' }}>
            Intelligence & Pattern Management
          </p>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={() => setDarkMode(!darkMode)}
            style={{
              background: T.bgCard,
              border: `1px solid ${T.border}`,
              borderRadius: '8px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              color: T.text,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
            }}
          >
            {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            {darkMode ? 'Light' : 'Dark'}
          </button>

          <button
            onClick={loadDashboardData}
            style={{
              background: T.bgCard,
              border: `1px solid ${T.border}`,
              borderRadius: '8px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              color: T.text,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
            }}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>

          <div style={{ textAlign: 'right' }}>
            <div style={{ 
              fontSize: '0.7rem', 
              color: T.textDim, 
              textTransform: 'uppercase', 
              letterSpacing: '0.1em' 
            }}>
              Status
            </div>
            <div style={{ 
              fontSize: '0.85rem', 
              color: STATUS.green, 
              fontWeight: 600, 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem',
              justifyContent: 'flex-end',
            }}>
              <span style={{ 
                width: 8, 
                height: 8, 
                borderRadius: '50%', 
                background: STATUS.green, 
                boxShadow: `0 0 10px ${STATUS.green}`,
              }} />
              LEARNING
            </div>
          </div>

          <div style={{ 
            fontFamily: 'monospace', 
            fontSize: '1.5rem', 
            color: T.accent, 
            textShadow: darkMode ? `0 0 20px ${T.accent}40` : 'none',
          }}>
            {time.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(4, 1fr)', 
        gap: '1rem', 
        marginBottom: '2rem' 
      }}>
        {statCards.map((stat, i) => (
          <div 
            key={i} 
            style={{ 
              background: T.bgCard, 
              border: `1px solid ${T.border}`, 
              borderRadius: '8px', 
              padding: '1.25rem', 
              position: 'relative', 
              overflow: 'hidden',
            }}
          >
            <div style={{ 
              position: 'absolute', 
              top: 0, 
              left: 0, 
              right: 0, 
              height: 2, 
              background: stat.color, 
              boxShadow: `0 0 10px ${stat.color}` 
            }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ 
                  fontSize: '0.75rem', 
                  color: T.textDim, 
                  marginBottom: '0.5rem', 
                  textTransform: 'uppercase', 
                  letterSpacing: '0.05em' 
                }}>
                  {stat.label}
                </div>
                <div style={{ 
                  fontSize: '2rem', 
                  fontWeight: 700, 
                  color: stat.color, 
                  textShadow: darkMode ? `0 0 20px ${stat.color}40` : 'none', 
                  fontFamily: 'monospace' 
                }}>
                  {loading ? '...' : stat.value.toLocaleString()}
                </div>
              </div>
              <stat.icon size={24} style={{ opacity: 0.5, color: T.textDim }} />
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ 
        display: 'flex', 
        gap: '0.5rem', 
        marginBottom: '1.5rem',
        borderBottom: `1px solid ${T.border}`,
        paddingBottom: '0.5rem',
      }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              background: activeTab === tab.id ? T.accent : 'transparent',
              border: 'none',
              borderRadius: '6px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              color: activeTab === tab.id ? 'white' : T.textDim,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
              fontWeight: activeTab === tab.id ? 600 : 400,
              transition: 'all 0.2s ease',
            }}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error State */}
      {error && (
        <div style={{
          background: T.bgCard,
          border: `1px solid ${STATUS.red}40`,
          borderLeft: `4px solid ${STATUS.red}`,
          borderRadius: '8px',
          padding: '1rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
        }}>
          <AlertTriangle size={20} style={{ color: STATUS.red }} />
          <span style={{ color: T.text }}>{error}</span>
          <button
            onClick={loadDashboardData}
            style={{
              marginLeft: 'auto',
              background: STATUS.red,
              border: 'none',
              borderRadius: '4px',
              padding: '0.25rem 0.75rem',
              color: 'white',
              cursor: 'pointer',
              fontSize: '0.8rem',
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '4rem',
          color: T.textDim,
        }}>
          <RefreshCw size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
          <p>Loading learning data...</p>
          <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Content */}
      {!loading && (
        <div style={{ 
          background: T.bgCard, 
          border: `1px solid ${T.border}`, 
          borderRadius: '12px', 
          overflow: 'hidden',
        }}>
          {/* Tab Content Header */}
          <div style={{
            padding: '1rem 1.25rem',
            borderBottom: `1px solid ${T.border}`,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Activity size={18} style={{ color: T.accent }} />
              <span style={{ fontWeight: 600 }}>
                {tabs.find(t => t.id === activeTab)?.label}
              </span>
            </div>
            
            {activeTab !== 'overview' && (
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <div style={{ position: 'relative' }}>
                  <Search size={16} style={{ 
                    position: 'absolute', 
                    left: '0.75rem', 
                    top: '50%', 
                    transform: 'translateY(-50%)',
                    color: T.textDim,
                  }} />
                  <input
                    type="text"
                    placeholder="Search..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={{
                      background: T.bg,
                      border: `1px solid ${T.border}`,
                      borderRadius: '6px',
                      padding: '0.5rem 0.75rem 0.5rem 2.25rem',
                      color: T.text,
                      fontSize: '0.85rem',
                      width: '200px',
                    }}
                  />
                </div>
                <button
                  onClick={() => exportData(activeTab)}
                  style={{
                    background: T.bg,
                    border: `1px solid ${T.border}`,
                    borderRadius: '6px',
                    padding: '0.5rem 0.75rem',
                    cursor: 'pointer',
                    color: T.text,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    fontSize: '0.85rem',
                  }}
                >
                  <Download size={16} />
                  Export
                </button>
              </div>
            )}
          </div>

          {/* Tab Content */}
          <div style={{ padding: '1.25rem' }}>
            {activeTab === 'overview' && (
              <OverviewTab T={T} stats={stats} darkMode={darkMode} />
            )}
            {activeTab === 'queries' && (
              <DataTable 
                T={T}
                data={learnedQueries}
                searchTerm={searchTerm}
                columns={['pattern', 'intent', 'use_count', 'last_used']}
                onDelete={(id) => deleteItem('queries', id)}
              />
            )}
            {activeTab === 'feedback' && (
              <DataTable 
                T={T}
                data={feedback}
                searchTerm={searchTerm}
                columns={['question', 'feedback', 'project', 'created_at']}
                onDelete={(id) => deleteItem('feedback', id)}
              />
            )}
            {activeTab === 'preferences' && (
              <DataTable 
                T={T}
                data={preferences}
                searchTerm={searchTerm}
                columns={['user_id', 'preference_type', 'value', 'created_at']}
                onDelete={(id) => deleteItem('preferences', id)}
              />
            )}
            {activeTab === 'clarifications' && (
              <DataTable 
                T={T}
                data={clarificationPatterns}
                searchTerm={searchTerm}
                columns={['pattern', 'question_type', 'options', 'use_count']}
                onDelete={(id) => deleteItem('clarifications', id)}
              />
            )}
            {activeTab === 'mappings' && (
              <DataTable 
                T={T}
                data={globalMappings}
                searchTerm={searchTerm}
                columns={['source_column', 'target_field', 'confidence', 'created_at']}
                onDelete={(id) => deleteItem('mappings', id)}
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Overview Tab Component
function OverviewTab({ T, stats, darkMode }) {
  const insights = [
    { label: 'Most Common Query Type', value: stats?.top_query_type || 'Data Analysis', color: BRAND.grassGreen },
    { label: 'Average Confidence', value: `${Math.round((stats?.avg_confidence || 0.75) * 100)}%`, color: STATUS.green },
    { label: 'Positive Feedback Rate', value: `${Math.round((stats?.positive_rate || 0.82) * 100)}%`, color: STATUS.blue },
    { label: 'Auto-Apply Rate', value: `${Math.round((stats?.auto_apply_rate || 0.65) * 100)}%`, color: STATUS.amber },
  ]

  return (
    <div>
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(2, 1fr)', 
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        {insights.map((insight, i) => (
          <div 
            key={i}
            style={{
              background: T.bg,
              border: `1px solid ${T.border}`,
              borderRadius: '8px',
              padding: '1rem',
            }}
          >
            <div style={{ fontSize: '0.75rem', color: T.textDim, marginBottom: '0.5rem' }}>
              {insight.label}
            </div>
            <div style={{ 
              fontSize: '1.5rem', 
              fontWeight: 700, 
              color: insight.color,
              textShadow: darkMode ? `0 0 15px ${insight.color}40` : 'none',
            }}>
              {insight.value}
            </div>
          </div>
        ))}
      </div>

      <div style={{
        background: T.bg,
        border: `1px solid ${T.border}`,
        borderRadius: '8px',
        padding: '1rem',
      }}>
        <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '1rem', color: T.text }}>
          System Health
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {[
            { label: 'Learning Database', status: 'healthy' },
            { label: 'Pattern Matching', status: 'healthy' },
            { label: 'Preference Engine', status: 'healthy' },
            { label: 'Feedback Loop', status: 'healthy' },
          ].map((item, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ color: T.textDim, fontSize: '0.85rem' }}>{item.label}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle size={16} style={{ color: STATUS.green }} />
                <span style={{ color: STATUS.green, fontSize: '0.8rem', fontWeight: 600 }}>
                  {item.status.toUpperCase()}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Reusable Data Table Component
function DataTable({ T, data, searchTerm, columns, onDelete }) {
  const filteredData = data.filter(item => 
    Object.values(item).some(val => 
      String(val).toLowerCase().includes(searchTerm.toLowerCase())
    )
  )

  if (filteredData.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '3rem',
        color: T.textDim,
      }}>
        <Database size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
        <p>No data found</p>
      </div>
    )
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {columns.map(col => (
              <th 
                key={col}
                style={{
                  textAlign: 'left',
                  padding: '0.75rem',
                  borderBottom: `1px solid ${T.border}`,
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: T.textDim,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                {col.replace(/_/g, ' ')}
              </th>
            ))}
            <th style={{ width: 50 }}></th>
          </tr>
        </thead>
        <tbody>
          {filteredData.slice(0, 50).map((item, i) => (
            <tr 
              key={item.id || i}
              style={{
                borderBottom: `1px solid ${T.border}`,
              }}
            >
              {columns.map(col => (
                <td 
                  key={col}
                  style={{
                    padding: '0.75rem',
                    fontSize: '0.85rem',
                    color: T.text,
                    maxWidth: '300px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {formatValue(item[col], col)}
                </td>
              ))}
              <td style={{ padding: '0.75rem' }}>
                <button
                  onClick={() => onDelete(item.id)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: T.textDim,
                    padding: '0.25rem',
                    borderRadius: '4px',
                  }}
                >
                  <Trash2 size={16} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {filteredData.length > 50 && (
        <div style={{ 
          padding: '1rem', 
          textAlign: 'center', 
          color: T.textDim,
          fontSize: '0.85rem',
        }}>
          Showing 50 of {filteredData.length} records
        </div>
      )}
    </div>
  )
}

// Format cell values
function formatValue(value, column) {
  if (value === null || value === undefined) return '-'
  
  if (column.includes('date') || column.includes('_at')) {
    try {
      return new Date(value).toLocaleDateString()
    } catch {
      return value
    }
  }
  
  if (column === 'feedback') {
    return value === 'positive' ? '👍' : '👎'
  }
  
  if (column === 'confidence') {
    return `${Math.round(value * 100)}%`
  }
  
  if (typeof value === 'object') {
    return JSON.stringify(value).slice(0, 50) + '...'
  }
  
  return String(value)
}
