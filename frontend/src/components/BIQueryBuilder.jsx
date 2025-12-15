/**
 * BIQueryBuilder.jsx - Reusable BI Query Component
 * =================================================
 * 
 * Deploy to: frontend/src/components/BIQueryBuilder.jsx
 * 
 * FEATURES:
 * - Natural language query input
 * - Smart suggestions from intelligence
 * - Dynamic chart rendering
 * - Transform & Export panel
 * - Reusable in pages and playbooks
 * 
 * PROPS:
 * - project: string (required) - Project name/ID
 * - onQueryComplete: function - Callback when query completes
 * - showExport: boolean - Show export options
 * - showSave: boolean - Show save query option
 * - embedded: boolean - Compact mode for embedding
 * - initialQuery: string - Pre-fill query
 */

import { useState, useEffect, useRef } from 'react'
import api from '../services/api'
import { COLORS } from '../components/ui'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, AreaChart, Area,
  ScatterChart, Scatter
} from 'recharts'
import {
  Sparkles, Send, Download, Save, Table2, BarChart3, PieChart as PieIcon,
  LineChart as LineIcon, TrendingUp, RefreshCw, ChevronDown, ChevronRight,
  Plus, X, GripVertical, Eye, EyeOff, ArrowRight, FileSpreadsheet,
  Lightbulb, Clock, Star, Filter, Columns, Wand2, Check, AlertCircle,
  Database, Play, Loader2, Settings, Layout, MoreHorizontal, Copy,
  Maximize2, Minimize2, ZoomIn, ZoomOut
} from 'lucide-react'

// Brand colors (matching Chat.jsx)
const BRAND = COLORS?.grassGreen || '#83b16d'
const BRAND_LIGHT = '#f0fdf4'
const BRAND_BORDER = '#bbf7d0'

// Chart colors
const CHART_COLORS = ['#83b16d', '#3B82F6', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#F97316', '#6366F1']


// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function BIQueryBuilder({
  project,
  onQueryComplete,
  showExport = true,
  showSave = true,
  embedded = false,
  initialQuery = ''
}) {
  // Query state
  const [query, setQuery] = useState(initialQuery)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // Results state
  const [results, setResults] = useState(null)
  const [chartType, setChartType] = useState('table')
  
  // Suggestions
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(true)
  
  // Transform panel
  const [showTransforms, setShowTransforms] = useState(false)
  const [transforms, setTransforms] = useState([])
  const [availableTransforms, setAvailableTransforms] = useState([])
  
  // Clarification
  const [pendingClarification, setPendingClarification] = useState(null)
  
  // Fullscreen chart view
  const [isFullscreen, setIsFullscreen] = useState(false)
  
  // Refs
  const inputRef = useRef(null)
  
  // Sync initialQuery prop to query state
  useEffect(() => {
    if (initialQuery && initialQuery !== query) {
      setQuery(initialQuery)
    }
  }, [initialQuery])
  
  // Load suggestions on mount
  useEffect(() => {
    if (project) {
      loadSuggestions()
    }
  }, [project])
  
  // ===========================================
  // API CALLS
  // ===========================================
  
  const loadSuggestions = async () => {
    try {
      const response = await api.get(`/bi/suggestions/${project}`)
      setSuggestions(response.data.suggestions || [])
    } catch (err) {
      console.error('Failed to load suggestions:', err)
    }
  }
  
  const executeQuery = async (filters = null) => {
    if (!query.trim()) return
    
    setIsLoading(true)
    setError(null)
    setPendingClarification(null)
    
    try {
      const response = await api.post('/bi/query', {
        query: query.trim(),
        project,
        filters
      })
      
      const data = response.data
      
      // Check if clarification needed
      if (data.needs_clarification) {
        setPendingClarification(data.clarification)
        setIsLoading(false)
        return
      }
      
      // Set results
      setResults(data)
      setChartType(data.chart?.recommended || 'table')
      setAvailableTransforms(data.available_transforms || [])
      setShowSuggestions(false)
      
      // Callback
      if (onQueryComplete) {
        onQueryComplete(data)
      }
      
    } catch (err) {
      console.error('Query error:', err)
      setError(err.response?.data?.detail || err.message || 'Query failed')
    } finally {
      setIsLoading(false)
    }
  }
  
  const handleClarificationSubmit = (answers) => {
    setPendingClarification(null)
    executeQuery(answers)
  }
  
  const handleExport = async (format = 'xlsx') => {
    try {
      const response = await api.post('/bi/export', {
        query,
        project,
        sql: results?.sql,
        transforms,
        format,
        include_metadata: true
      }, { responseType: 'blob' })
      
      // Download file
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `xlr8_export.${format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      
    } catch (err) {
      console.error('Export error:', err)
      setError('Export failed')
    }
  }
  
  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion.text)
    setShowSuggestions(false)
    setTimeout(() => executeQuery(), 100)
  }
  
  const addTransform = (transform) => {
    setTransforms(prev => [...prev, transform])
  }
  
  const removeTransform = (index) => {
    setTransforms(prev => prev.filter((_, i) => i !== index))
  }
  
  // ===========================================
  // RENDER CHART
  // ===========================================
  
  const renderChart = () => {
    if (!results?.data || results.data.length === 0) {
      return (
        <div className="flex items-center justify-center h-64 text-gray-400">
          No data to display
        </div>
      )
    }
    
    const data = results.data
    const config = results.chart?.config || {}
    const xKey = config.xAxis || results.columns?.[0]
    const yKey = config.yAxis || results.columns?.[1]
    
    // Metric display (single value)
    if (chartType === 'metric' && data.length === 1) {
      const value = Object.values(data[0])[0]
      return (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="text-5xl font-bold" style={{ color: BRAND }}>
              {typeof value === 'number' ? value.toLocaleString() : value}
            </div>
            <div className="text-gray-500 mt-2">{results.columns?.[0]}</div>
          </div>
        </div>
      )
    }
    
    // Table view
    if (chartType === 'table') {
      return (
        <div className="overflow-auto max-h-96">
          <table className="w-full text-sm">
            <thead className="sticky top-0">
              <tr style={{ backgroundColor: BRAND }}>
                {results.columns?.map(col => (
                  <th key={col} className="px-3 py-2 text-left text-white font-medium">
                    {col.replace(/_/g, ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.slice(0, 100).map((row, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                  {results.columns?.map(col => (
                    <td key={col} className="px-3 py-2 border-b border-gray-100">
                      {formatValue(row[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {data.length > 100 && (
            <div className="text-center py-2 text-sm text-gray-500">
              Showing 100 of {data.length.toLocaleString()} rows
            </div>
          )}
        </div>
      )
    }
    
    // Bar chart
    if (chartType === 'bar') {
      return (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
            <XAxis 
              dataKey={xKey} 
              tick={{ fill: '#6b7280', fontSize: 11 }}
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} tickFormatter={formatNumber} />
            <Tooltip 
              contentStyle={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '8px' }}
              formatter={(value) => formatNumber(value)}
            />
            <Bar dataKey={yKey} fill={BRAND} radius={[4, 4, 0, 0]} maxBarSize={50} />
          </BarChart>
        </ResponsiveContainer>
      )
    }
    
    // Pie chart
    if (chartType === 'pie') {
      return (
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={100}
              paddingAngle={2}
              dataKey={yKey}
              nameKey={xKey}
              label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
            >
              {data.map((_, index) => (
                <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => formatNumber(value)} />
          </PieChart>
        </ResponsiveContainer>
      )
    }
    
    // Line/Area chart
    if (chartType === 'line' || chartType === 'area') {
      const ChartComponent = chartType === 'area' ? AreaChart : LineChart
      const DataComponent = chartType === 'area' ? Area : Line
      
      return (
        <ResponsiveContainer width="100%" height={300}>
          <ChartComponent data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey={xKey} tick={{ fill: '#6b7280', fontSize: 11 }} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} tickFormatter={formatNumber} />
            <Tooltip formatter={(value) => formatNumber(value)} />
            <DataComponent 
              type="monotone" 
              dataKey={yKey} 
              stroke={BRAND} 
              fill={chartType === 'area' ? BRAND : 'none'}
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </ChartComponent>
        </ResponsiveContainer>
      )
    }
    
    // Default: table fallback
    return (
      <div className="overflow-auto max-h-96">
        <table className="w-full text-sm">
          <thead className="sticky top-0">
            <tr style={{ backgroundColor: BRAND }}>
              {results.columns?.map(col => (
                <th key={col} className="px-3 py-2 text-left text-white font-medium">
                  {col.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 100).map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                {results.columns?.map(col => (
                  <td key={col} className="px-3 py-2 border-b border-gray-100">
                    {formatValue(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }
  
  // ===========================================
  // RENDER CHART FULLSCREEN (larger version)
  // ===========================================
  
  const renderChartFullscreen = () => {
    if (!results?.data || results.data.length === 0) return null
    
    const data = results.data
    const config = results.chart?.config || {}
    const xKey = config.xAxis || results.columns?.[0]
    const yKey = config.yAxis || results.columns?.[1]
    
    // Bar chart - fullscreen
    if (chartType === 'bar') {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 100 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
            <XAxis 
              dataKey={xKey} 
              tick={{ fill: '#6b7280', fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={100}
            />
            <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} tickFormatter={formatNumber} />
            <Tooltip 
              contentStyle={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '8px' }}
              formatter={(value) => formatNumber(value)}
            />
            <Bar dataKey={yKey} fill={BRAND} radius={[4, 4, 0, 0]} maxBarSize={80} />
          </BarChart>
        </ResponsiveContainer>
      )
    }
    
    // Pie chart - fullscreen
    if (chartType === 'pie') {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={80}
              outerRadius={180}
              paddingAngle={2}
              dataKey={yKey}
              nameKey={xKey}
              label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
            >
              {data.map((_, index) => (
                <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => formatNumber(value)} />
          </PieChart>
        </ResponsiveContainer>
      )
    }
    
    // Line chart - fullscreen
    if (chartType === 'line' || chartType === 'area') {
      const ChartComponent = chartType === 'area' ? AreaChart : LineChart
      const DataComponent = chartType === 'area' ? Area : Line
      
      return (
        <ResponsiveContainer width="100%" height="100%">
          <ChartComponent data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey={xKey} tick={{ fill: '#6b7280', fontSize: 12 }} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} tickFormatter={formatNumber} />
            <Tooltip formatter={(value) => formatNumber(value)} />
            <DataComponent 
              type="monotone" 
              dataKey={yKey} 
              stroke={BRAND} 
              fill={chartType === 'area' ? BRAND : 'none'}
              fillOpacity={0.2}
              strokeWidth={3}
            />
          </ChartComponent>
        </ResponsiveContainer>
      )
    }
    
    return null
  }
  
  // ===========================================
  // HELPERS
  // ===========================================
  
  const formatValue = (val) => {
    if (val === null || val === undefined) return '-'
    if (typeof val === 'number') return val.toLocaleString()
    return String(val)
  }
  
  const formatNumber = (val) => {
    if (typeof val !== 'number') return val
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`
    if (val >= 1000) return `${(val / 1000).toFixed(1)}K`
    return val.toLocaleString()
  }
  
  // ===========================================
  // RENDER
  // ===========================================
  
  const containerClass = embedded 
    ? 'bg-white rounded-lg border' 
    : 'bg-white rounded-xl shadow-sm border'
  
  return (
    <div className={containerClass}>
      {/* Query Input */}
      <div className="p-4 border-b">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !isLoading && executeQuery()}
              onFocus={() => !results && setShowSuggestions(true)}
              placeholder="Ask a question... e.g., 'How many employees in Texas?'"
              className="w-full px-4 py-3 pr-12 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 transition-all"
              style={{ 
                focusRing: BRAND,
                '--tw-ring-color': BRAND 
              }}
              disabled={isLoading}
            />
            <Sparkles 
              size={18} 
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400"
            />
          </div>
          
          <button
            onClick={() => executeQuery()}
            disabled={isLoading || !query.trim()}
            className="px-5 py-3 rounded-lg font-medium flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: BRAND,
              color: 'white',
              boxShadow: '0 2px 8px rgba(131, 177, 109, 0.3)'
            }}
          >
            {isLoading ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Play size={18} />
            )}
            {isLoading ? 'Running...' : 'Run'}
          </button>
        </div>
        
        {/* Error */}
        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
            <AlertCircle size={16} />
            {error}
          </div>
        )}
      </div>
      
      {/* Suggestions */}
      {showSuggestions && suggestions.length > 0 && !results && (
        <div className="p-4 border-b bg-gray-50">
          <div className="flex items-center gap-2 text-sm text-gray-500 mb-3">
            <Lightbulb size={14} />
            Suggested queries
          </div>
          <div className="flex flex-wrap gap-2">
            {suggestions.slice(0, 6).map((s, i) => (
              <button
                key={i}
                onClick={() => handleSuggestionClick(s)}
                className="px-3 py-1.5 rounded-full text-sm border transition-all hover:border-gray-400"
                style={{
                  backgroundColor: s.type === 'finding' ? '#FEF3C7' : 'white',
                  borderColor: s.type === 'finding' ? '#F59E0B' : '#e5e7eb'
                }}
              >
                {s.text}
                {s.badge && (
                  <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">
                    {s.badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Clarification Card */}
      {pendingClarification && (
        <ClarificationCard
          clarification={pendingClarification}
          onSubmit={handleClarificationSubmit}
          onCancel={() => setPendingClarification(null)}
        />
      )}
      
      {/* Results */}
      {results && !pendingClarification && (
        <>
          {/* Toolbar */}
          <div className="p-3 border-b flex items-center justify-between bg-gray-50">
            <div className="flex items-center gap-2">
              {/* Chart type selector */}
              <div className="flex bg-white rounded-lg border p-1">
                {[
                  { type: 'table', icon: Table2, label: 'Table' },
                  { type: 'bar', icon: BarChart3, label: 'Bar' },
                  { type: 'pie', icon: PieIcon, label: 'Pie' },
                  { type: 'line', icon: LineIcon, label: 'Line' },
                ].map(({ type, icon: Icon, label }) => (
                  <button
                    key={type}
                    onClick={() => setChartType(type)}
                    className={`p-2 rounded transition-all ${
                      chartType === type 
                        ? 'text-white' 
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                    style={chartType === type ? { backgroundColor: BRAND } : {}}
                    title={label}
                  >
                    <Icon size={16} />
                  </button>
                ))}
              </div>
              
              {/* Row count */}
              <span className="text-sm text-gray-500 ml-2">
                {results.total_rows?.toLocaleString()} rows
                {results.truncated && ' (truncated)'}
              </span>
              
              {/* Fullscreen toggle for charts */}
              {chartType !== 'table' && (
                <button
                  onClick={() => setIsFullscreen(!isFullscreen)}
                  className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700"
                  title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
                >
                  {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </button>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              {/* Transform toggle */}
              <button
                onClick={() => setShowTransforms(!showTransforms)}
                className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5 transition-all ${
                  showTransforms ? 'bg-gray-200' : 'hover:bg-gray-100'
                }`}
              >
                <Wand2 size={14} />
                Transform
              </button>
              
              {/* Export */}
              {showExport && (
                <button
                  onClick={() => handleExport('xlsx')}
                  className="px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5 hover:bg-gray-100"
                >
                  <Download size={14} />
                  Export
                </button>
              )}
              
              {/* Save */}
              {showSave && (
                <button
                  className="px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5 hover:bg-gray-100"
                >
                  <Save size={14} />
                  Save
                </button>
              )}
            </div>
          </div>
          
          {/* Transform Panel */}
          {showTransforms && (
            <TransformPanel
              availableTransforms={availableTransforms}
              activeTransforms={transforms}
              onAdd={addTransform}
              onRemove={removeTransform}
              columns={results.columns}
            />
          )}
          
          {/* Chart/Table */}
          <div className="p-4">
            {renderChart()}
          </div>
          
          {/* Fullscreen Modal */}
          {isFullscreen && chartType !== 'table' && (
            <div 
              className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-8"
              onClick={() => setIsFullscreen(false)}
            >
              <div 
                className="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-auto"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Fullscreen Header */}
                <div className="p-4 border-b flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-gray-800">
                      {query}
                    </span>
                    <span className="text-sm text-gray-500">
                      {results.total_rows?.toLocaleString()} rows
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* Chart type selector in fullscreen */}
                    <div className="flex bg-gray-100 rounded-lg p-1">
                      {[
                        { type: 'bar', icon: BarChart3, label: 'Bar' },
                        { type: 'pie', icon: PieIcon, label: 'Pie' },
                        { type: 'line', icon: LineIcon, label: 'Line' },
                      ].map(({ type, icon: Icon, label }) => (
                        <button
                          key={type}
                          onClick={() => setChartType(type)}
                          className={`p-2 rounded transition-all ${
                            chartType === type 
                              ? 'text-white' 
                              : 'text-gray-500 hover:text-gray-700'
                          }`}
                          style={chartType === type ? { backgroundColor: BRAND } : {}}
                          title={label}
                        >
                          <Icon size={16} />
                        </button>
                      ))}
                    </div>
                    <button
                      onClick={() => setIsFullscreen(false)}
                      className="p-2 rounded-lg hover:bg-gray-100 text-gray-500"
                      title="Close"
                    >
                      <X size={20} />
                    </button>
                  </div>
                </div>
                
                {/* Fullscreen Chart - Larger */}
                <div className="p-8" style={{ height: '70vh' }}>
                  {renderChartFullscreen()}
                </div>
              </div>
            </div>
          )}
          
          {/* SQL Preview */}
          {results.sql && (
            <div className="px-4 pb-4">
              <details className="text-sm">
                <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
                  View SQL
                </summary>
                <pre className="mt-2 p-3 bg-gray-50 rounded-lg overflow-x-auto text-xs">
                  {results.sql}
                </pre>
              </details>
            </div>
          )}
          
          {/* Answer text */}
          {results.answer_text && (
            <div className="px-4 pb-4 text-sm text-gray-600">
              {results.answer_text}
            </div>
          )}
        </>
      )}
    </div>
  )
}


// =============================================================================
// CLARIFICATION CARD
// =============================================================================

function ClarificationCard({ clarification, onSubmit, onCancel }) {
  const [answers, setAnswers] = useState({})
  const questions = clarification?.questions || []
  
  useEffect(() => {
    // Set defaults
    const defaults = {}
    questions.forEach(q => {
      const defaultOpt = q.options?.find(o => o.default)
      if (defaultOpt) {
        defaults[q.id] = defaultOpt.id
      }
    })
    setAnswers(defaults)
  }, [questions])
  
  const handleChange = (questionId, value) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }))
  }
  
  return (
    <div className="p-4 border-b" style={{ backgroundColor: BRAND_LIGHT }}>
      <div className="flex items-center gap-3 mb-4">
        <div 
          className="w-10 h-10 rounded-full flex items-center justify-center"
          style={{ backgroundColor: 'white' }}
        >
          <Sparkles size={20} style={{ color: BRAND }} />
        </div>
        <div>
          <h3 className="font-semibold" style={{ color: '#166534' }}>Quick clarification</h3>
          <p className="text-sm" style={{ color: BRAND }}>Help me give you a better answer</p>
        </div>
      </div>
      
      <div className="space-y-4">
        {questions.map((q) => (
          <div key={q.id} className="bg-white rounded-lg p-4 border" style={{ borderColor: BRAND_BORDER }}>
            <div className="font-medium text-gray-800 mb-3">{q.question}</div>
            
            <div className="space-y-2">
              {q.options?.map((opt) => (
                <label 
                  key={opt.id}
                  className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all ${
                    answers[q.id] === opt.id 
                      ? 'border-2' 
                      : 'border border-gray-200 hover:border-gray-300'
                  }`}
                  style={answers[q.id] === opt.id ? { 
                    borderColor: BRAND, 
                    backgroundColor: BRAND_LIGHT 
                  } : {}}
                >
                  <input
                    type="radio"
                    name={q.id}
                    value={opt.id}
                    checked={answers[q.id] === opt.id}
                    onChange={() => handleChange(q.id, opt.id)}
                    className="sr-only"
                  />
                  <div 
                    className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                      answers[q.id] === opt.id ? '' : 'border-gray-300'
                    }`}
                    style={answers[q.id] === opt.id ? { borderColor: BRAND } : {}}
                  >
                    {answers[q.id] === opt.id && (
                      <div 
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: BRAND }}
                      />
                    )}
                  </div>
                  <span className="text-sm">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
      
      <div className="flex gap-3 mt-4">
        <button
          onClick={() => onSubmit(answers)}
          className="px-4 py-2 rounded-lg text-white font-medium"
          style={{ backgroundColor: BRAND }}
        >
          Continue
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-100"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}


// =============================================================================
// TRANSFORM PANEL
// =============================================================================

function TransformPanel({ availableTransforms, activeTransforms, onAdd, onRemove, columns }) {
  const [selectedColumn, setSelectedColumn] = useState('')
  
  // Group transforms by column
  const transformsByColumn = {}
  availableTransforms.forEach(t => {
    if (!transformsByColumn[t.column]) {
      transformsByColumn[t.column] = []
    }
    transformsByColumn[t.column].push(t)
  })
  
  return (
    <div className="p-4 border-b bg-gray-50">
      <div className="flex items-center gap-2 mb-3">
        <Wand2 size={16} className="text-gray-500" />
        <span className="text-sm font-medium">Transform Data</span>
      </div>
      
      {/* Active transforms */}
      {activeTransforms.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {activeTransforms.map((t, i) => (
            <div 
              key={i}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm"
              style={{ backgroundColor: BRAND_LIGHT, border: `1px solid ${BRAND_BORDER}` }}
            >
              <span>{t.icon || '✨'}</span>
              <span>{t.label}</span>
              <span className="text-gray-500">on {t.column}</span>
              <button
                onClick={() => onRemove(i)}
                className="text-gray-400 hover:text-red-500"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
      
      {/* Available transforms by column */}
      <div className="space-y-2">
        {Object.entries(transformsByColumn).slice(0, 5).map(([col, transforms]) => (
          <div key={col} className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-500 w-24 truncate">{col}:</span>
            {transforms.map((t, i) => (
              <button
                key={i}
                onClick={() => onAdd(t)}
                className="px-2 py-1 rounded text-xs bg-white border hover:border-gray-400 transition-all flex items-center gap-1"
              >
                <span>{t.icon}</span>
                {t.label}
              </button>
            ))}
          </div>
        ))}
      </div>
      
      {Object.keys(transformsByColumn).length === 0 && (
        <div className="text-sm text-gray-500">
          No transforms available for this data
        </div>
      )}
    </div>
  )
}
