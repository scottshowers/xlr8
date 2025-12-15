/**
 * BIBuilderPage.jsx - Analytics Dashboard
 * ========================================
 * 
 * Deploy to: frontend/src/pages/BIBuilderPage.jsx
 * 
 * FEATURES:
 * - Natural language BI queries
 * - Smart chart generation
 * - Transform & Export
 * - Saved queries library
 * - Dashboard composition (future)
 * 
 * Add to navigation:
 * { name: 'Analytics', path: '/analytics', icon: BarChart3 }
 */

import { useState, useEffect } from 'react'
import { useProject } from '../context/ProjectContext'
import api from '../services/api'
import { COLORS } from '../components/ui'
import BIQueryBuilder from '../components/BIQueryBuilder'
import {
  BarChart3, Clock, Star, Trash2, Play, Plus, 
  ChevronRight, Database, FileSpreadsheet, TrendingUp,
  Lightbulb, Bookmark, Layout
} from 'lucide-react'

// Brand colors
const BRAND = COLORS?.grassGreen || '#83b16d'
const BRAND_LIGHT = '#f0fdf4'
const BRAND_BORDER = '#bbf7d0'


export default function BIBuilderPage() {
  const { activeProject, projectName } = useProject()
  
  // State
  const [savedQueries, setSavedQueries] = useState([])
  const [recentQueries, setRecentQueries] = useState([])
  const [schema, setSchema] = useState(null)
  const [view, setView] = useState('builder') // 'builder', 'saved', 'dashboard'
  const [selectedQuery, setSelectedQuery] = useState(null)
  
  // Load data on mount
  useEffect(() => {
    if (projectName) {
      loadSavedQueries()
      loadSchema()
      loadRecentQueries()
    }
  }, [projectName])
  
  const loadSavedQueries = async () => {
    try {
      const response = await api.get(`/bi/saved/${projectName}`)
      setSavedQueries(response.data.queries || [])
    } catch (err) {
      console.error('Failed to load saved queries:', err)
    }
  }
  
  const loadSchema = async () => {
    try {
      const response = await api.get(`/bi/schema/${projectName}`)
      setSchema(response.data)
    } catch (err) {
      console.error('Failed to load schema:', err)
    }
  }
  
  const loadRecentQueries = () => {
    // Load from localStorage
    try {
      const stored = localStorage.getItem(`bi_recent_${projectName}`)
      if (stored) {
        setRecentQueries(JSON.parse(stored))
      }
    } catch (err) {
      console.error('Failed to load recent queries:', err)
    }
  }
  
  const saveRecentQuery = (query) => {
    const updated = [query, ...recentQueries.filter(q => q !== query)].slice(0, 10)
    setRecentQueries(updated)
    localStorage.setItem(`bi_recent_${projectName}`, JSON.stringify(updated))
  }
  
  const handleQueryComplete = (result) => {
    if (result.query) {
      saveRecentQuery(result.query)
    }
  }
  
  const deleteSavedQuery = async (queryId) => {
    try {
      await api.delete(`/bi/saved/${queryId}`)
      setSavedQueries(prev => prev.filter(q => q.id !== queryId))
    } catch (err) {
      console.error('Failed to delete query:', err)
    }
  }
  
  const runSavedQuery = (query) => {
    setSelectedQuery(query.query)
    setView('builder')
  }
  
  // No project selected
  if (!projectName) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8">
          <Database size={48} className="mx-auto text-gray-300 mb-4" />
          <h2 className="text-xl font-semibold text-gray-600 mb-2">Select a Project</h2>
          <p className="text-gray-500">Choose a project from the header to start analyzing data</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div 
              className="w-10 h-10 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: BRAND_LIGHT }}
            >
              <BarChart3 size={20} style={{ color: BRAND }} />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Analytics</h1>
              <p className="text-sm text-gray-500">
                Ask questions in plain English • {schema?.tables?.length || 0} tables available
              </p>
            </div>
          </div>
          
          {/* View tabs */}
          <div className="flex bg-gray-100 rounded-lg p-1">
            {[
              { id: 'builder', label: 'Query Builder', icon: Play },
              { id: 'saved', label: 'Saved', icon: Bookmark },
              // { id: 'dashboard', label: 'Dashboard', icon: Layout },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setView(id)}
                className={`px-4 py-2 rounded-md text-sm font-medium flex items-center gap-2 transition-all ${
                  view === id 
                    ? 'bg-white shadow-sm text-gray-900' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon size={16} />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {view === 'builder' && (
          <div className="max-w-6xl mx-auto space-y-6">
            {/* Quick Stats */}
            {schema && (
              <div className="grid grid-cols-4 gap-4">
                <StatCard 
                  icon={Database}
                  label="Tables"
                  value={schema.tables?.length || 0}
                />
                <StatCard 
                  icon={FileSpreadsheet}
                  label="Total Rows"
                  value={schema.tables?.reduce((sum, t) => sum + (t.rows || 0), 0)?.toLocaleString()}
                />
                <StatCard 
                  icon={Star}
                  label="Saved Queries"
                  value={savedQueries.length}
                />
                <StatCard 
                  icon={Clock}
                  label="Recent"
                  value={recentQueries.length}
                />
              </div>
            )}
            
            {/* Query Builder */}
            <BIQueryBuilder
              project={projectName}
              onQueryComplete={handleQueryComplete}
              showExport={true}
              showSave={true}
              initialQuery={selectedQuery || ''}
            />
            
            {/* Recent Queries */}
            {recentQueries.length > 0 && (
              <div className="bg-white rounded-xl border p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Clock size={16} className="text-gray-400" />
                  <span className="text-sm font-medium text-gray-600">Recent Queries</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {recentQueries.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => setSelectedQuery(q)}
                      className="px-3 py-1.5 rounded-full text-sm bg-gray-100 hover:bg-gray-200 transition-all truncate max-w-xs"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {/* Available Tables */}
            {schema?.tables && (
              <div className="bg-white rounded-xl border p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Database size={16} className="text-gray-400" />
                  <span className="text-sm font-medium text-gray-600">Available Data</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {schema.tables.map((table, i) => (
                    <div 
                      key={i}
                      className="p-3 rounded-lg border border-gray-100 hover:border-gray-200 transition-all"
                    >
                      <div className="font-medium text-sm text-gray-800 truncate">
                        {table.name}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {table.rows?.toLocaleString()} rows • {table.columns?.length} cols
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {view === 'saved' && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-xl border">
              <div className="p-4 border-b flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bookmark size={18} className="text-gray-400" />
                  <span className="font-medium">Saved Queries</span>
                  <span className="text-sm text-gray-500">({savedQueries.length})</span>
                </div>
              </div>
              
              {savedQueries.length === 0 ? (
                <div className="p-12 text-center">
                  <Star size={48} className="mx-auto text-gray-200 mb-4" />
                  <h3 className="text-lg font-medium text-gray-600 mb-2">No saved queries yet</h3>
                  <p className="text-gray-500 text-sm mb-4">
                    Run a query and click Save to add it here
                  </p>
                  <button
                    onClick={() => setView('builder')}
                    className="px-4 py-2 rounded-lg text-white"
                    style={{ backgroundColor: BRAND }}
                  >
                    Create Query
                  </button>
                </div>
              ) : (
                <div className="divide-y">
                  {savedQueries.map((query) => (
                    <div 
                      key={query.id}
                      className="p-4 hover:bg-gray-50 transition-all flex items-center justify-between"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-800">{query.name}</div>
                        <div className="text-sm text-gray-500 truncate">{query.query}</div>
                        {query.chart_type && (
                          <span className="inline-block mt-1 text-xs px-2 py-0.5 rounded bg-gray-100">
                            {query.chart_type}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <button
                          onClick={() => runSavedQuery(query)}
                          className="p-2 rounded-lg hover:bg-gray-100 transition-all"
                          title="Run query"
                        >
                          <Play size={16} style={{ color: BRAND }} />
                        </button>
                        <button
                          onClick={() => deleteSavedQuery(query.id)}
                          className="p-2 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-all"
                          title="Delete"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
        
        {view === 'dashboard' && (
          <div className="max-w-6xl mx-auto">
            <div className="bg-white rounded-xl border p-12 text-center">
              <Layout size={48} className="mx-auto text-gray-200 mb-4" />
              <h3 className="text-lg font-medium text-gray-600 mb-2">Dashboard Builder</h3>
              <p className="text-gray-500 text-sm">
                Coming soon - Compose multiple queries into a dashboard
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


// =============================================================================
// STAT CARD
// =============================================================================

function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="bg-white rounded-xl border p-4">
      <div className="flex items-center gap-3">
        <div 
          className="w-10 h-10 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: BRAND_LIGHT }}
        >
          <Icon size={18} style={{ color: BRAND }} />
        </div>
        <div>
          <div className="text-2xl font-semibold text-gray-900">{value}</div>
          <div className="text-sm text-gray-500">{label}</div>
        </div>
      </div>
    </div>
  )
}
