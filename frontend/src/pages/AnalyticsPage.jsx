/**
 * AnalyticsPage.jsx - Analytics Explorer
 * =======================================
 * 
 * Deploy to: frontend/src/pages/AnalyticsPage.jsx
 * 
 * REPLACES: BIBuilderPage.jsx and BIQueryBuilder.jsx
 * 
 * FEATURES:
 * - 2-way mode toggle: Visual Builder, SQL
 * - Drag-and-drop query building
 * - Smart chart visualization (table, bar, line, pie)
 * - Data catalog organized by domain
 * - Direct SQL paste support
 * 
 * ROUTES: Update App.jsx
 *   { path: '/analytics', element: <AnalyticsPage /> }
 * 
 * NAV: Update navigation
 *   { name: 'Analytics', path: '/analytics', icon: BarChart3 }
 * 
 * FIXED: Comprehensive null safety for API responses
 */

import React, { useState, useEffect, useRef, Component } from 'react'
import { useProject } from '../context/ProjectContext'
import api from '../services/api'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RechartsPie, Pie, Cell, AreaChart, Area
} from 'recharts'
import {
  Search, Database, ChevronRight, ChevronDown, GripVertical,
  DollarSign, Users, Clock, Shield, Table2, BarChart3, PieChart, LineChart,
  Layers, Eye, X, Play, Code, Copy, Check, Download, Hash,
  Calendar, FileText, MessageSquare, Sparkles, Send, Filter, Loader2,
  AlertCircle, RefreshCw, Settings, BookOpen, Target
} from 'lucide-react'

// =============================================================================
// ERROR BOUNDARY - Catches render crashes
// =============================================================================

class AnalyticsErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Analytics page error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-full flex items-center justify-center bg-gray-50">
          <div className="text-center p-8 max-w-md">
            <AlertCircle size={48} className="mx-auto text-red-400 mb-4" />
            <h2 className="text-xl font-semibold text-gray-700 mb-2">Something went wrong</h2>
            <p className="text-gray-500 mb-4 text-sm">{this.state.error?.message || 'An unexpected error occurred'}</p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null })
                window.location.reload()
              }}
              className="px-4 py-2 bg-[#83b16d] text-white rounded-lg hover:bg-[#729c5e] transition-colors"
            >
              <RefreshCw size={14} className="inline mr-2" />
              Reload Page
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

// =============================================================================
// CONSTANTS
// =============================================================================

// Mission Control Color Palette (consistent with other pages)
const COLORS = {
  primary: '#83b16d',
  primaryLight: 'rgba(131, 177, 109, 0.1)',
  accent: '#285390',
  accentLight: 'rgba(40, 83, 144, 0.1)',
  blue: '#285390',
  blueLight: 'rgba(40, 83, 144, 0.1)',
  amber: '#d97706',
  amberLight: 'rgba(217, 119, 6, 0.1)',
  red: '#993c44',
  redLight: 'rgba(153, 60, 68, 0.1)',
  teal: '#0891b2',
  tealLight: 'rgba(8, 145, 178, 0.1)',
  bg: '#f0f2f5',
  card: '#ffffff',
  cardBorder: '#e2e8f0',
  text: '#1a2332',
  textMuted: '#64748b',
}

const CHART_PALETTE = ['#83b16d', '#285390', '#d97706', '#0891b2', '#993c44', '#5f4282', '#7c9a5e', '#4a7a9a']
const AGGREGATIONS = ['SUM', 'AVG', 'COUNT', 'MIN', 'MAX', 'COUNT DISTINCT']

// Truth Type icons and labels (Five Truths - Part 14 Visual Standards)
const TRUTH_TYPE_CONFIG = {
  reality: { icon: Database, label: 'Reality', color: '#285390' },
  intent: { icon: Target, label: 'Intent', color: '#2766b1' },
  configuration: { icon: Settings, label: 'Configuration', color: '#7aa866' },
  reference: { icon: BookOpen, label: 'Reference', color: '#5f4282' },
  regulatory: { icon: AlertCircle, label: 'Regulatory', color: '#993c44' },
}

// Domain detection and icons (fallback for auto-detection)
const DOMAIN_CONFIG = {
  payroll: { icon: DollarSign, label: 'Payroll & Compensation', keywords: ['pay', 'wage', 'salary', 'earning', 'deduct', 'tax', 'gross', 'net'] },
  hr: { icon: Users, label: 'HR & People', keywords: ['emp', 'person', 'worker', 'staff', 'job', 'position', 'department', 'org'] },
  time: { icon: Clock, label: 'Time & Attendance', keywords: ['time', 'schedule', 'attendance', 'punch', 'clock', 'shift', 'hours'] },
  benefits: { icon: Shield, label: 'Benefits & Deductions', keywords: ['benefit', 'insurance', '401k', 'health', 'dental', 'vision', 'pto', 'leave'] },
  general: { icon: Database, label: 'Other', keywords: [] },
}


// =============================================================================
// MAIN COMPONENT
// =============================================================================

function AnalyticsPageInner() {
  const { projectName } = useProject()
  
  // Catalog state
  const [catalog, setCatalog] = useState(null)
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [catalogError, setCatalogError] = useState(null)
  const [catalogSearch, setCatalogSearch] = useState('')
  const [expandedTruthTypes, setExpandedTruthTypes] = useState({})
  const [expandedFiles, setExpandedFiles] = useState({})
  const [expandedDomains, setExpandedDomains] = useState({})
  const [selectedTable, setSelectedTable] = useState(null)
  
  // Mode: 'natural', 'builder', 'sql'
  const [mode, setMode] = useState('builder')
  
  // Builder state
  const [columns, setColumns] = useState([])
  const [groupBy, setGroupBy] = useState([])
  const [filters, setFilters] = useState([])
  const [orderBy, setOrderBy] = useState(null)
  const [xAxis, setXAxis] = useState(null)
  const [yAxis, setYAxis] = useState(null)
  
  // Natural language state
  const [nlQuery, setNlQuery] = useState('')
  const [nlMessages, setNlMessages] = useState([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  
  // SQL state
  const [sqlText, setSqlText] = useState('')
  
  // Shared state
  const [chartType, setChartType] = useState('bar')
  const [results, setResults] = useState(null)
  const [resultsLoading, setResultsLoading] = useState(false)
  const [resultsError, setResultsError] = useState(null)
  const [showSQL, setShowSQL] = useState(false)
  const [copied, setCopied] = useState(false)
  const [draggedColumn, setDraggedColumn] = useState(null)
  
  // ===========================================
  // LOAD CATALOG
  // ===========================================
  
  const loadingRef = useRef(false)
  
  useEffect(() => {
    if (projectName && !loadingRef.current) {
      loadCatalog()
    }
  }, [projectName])
  
  const loadCatalog = async () => {
    if (loadingRef.current) {
      console.log('[Analytics] Skipping duplicate load')
      return
    }
    loadingRef.current = true
    
    setCatalogLoading(true)
    setCatalogError(null)
    
    try {
      const response = await api.get(`/bi/schema/${projectName}`)
      const data = response?.data || {}
      const tables = Array.isArray(data.tables) ? data.tables : []
      
      console.log(`[Analytics] API returned ${tables.length} tables`)
      
      // Organize tables by truth_type -> domain
      const organized = organizeTables(tables)
      
      const totalOrganized = organized.reduce((sum, t) => sum + (t?.tableCount || 0), 0)
      console.log(`[Analytics] Organized into ${organized.length} truth types, ${totalOrganized} total tables`)
      
      setCatalog(organized)
      
      // Auto-expand first non-empty truth type
      if (Array.isArray(organized) && organized.length > 0) {
        const firstTruth = organized.find(t => {
          const domains = Array.isArray(t?.domains) ? t.domains : []
          return domains.some(d => {
            const tables = Array.isArray(d?.tables) ? d.tables : []
            return tables.length > 0
          })
        })
        if (firstTruth) {
          setExpandedTruthTypes({ [firstTruth.truthType]: true })
          const domains = Array.isArray(firstTruth.domains) ? firstTruth.domains : []
          const firstDomain = domains.find(d => {
            const tables = Array.isArray(d?.tables) ? d.tables : []
            return tables.length > 0
          })
          if (firstDomain) {
            setExpandedDomains({ [`${firstTruth.truthType}:${firstDomain.domain}`]: true })
          }
        }
      }
    } catch (err) {
      console.error('Failed to load catalog:', err)
      setCatalogError(err?.message || 'Failed to load data catalog')
    } finally {
      setCatalogLoading(false)
      loadingRef.current = false
    }
  }
  
  const organizeTables = (tables) => {
    // NULL SAFETY: Ensure tables is an array
    if (!Array.isArray(tables)) {
      return []
    }
    
    console.log(`[Analytics] Organizing ${tables.length} tables`)
    
    // Group by truth_type -> file -> domain -> tables
    const hierarchy = {}
    
    tables.forEach(table => {
      if (!table) return
      
      const truthType = table.truth_type || 'reality'
      const file = table.file || 'Unknown Source'
      const domain = table.domain || inferDomain(table.full_name || table.name || '')
      
      if (!hierarchy[truthType]) {
        hierarchy[truthType] = {}
      }
      if (!hierarchy[truthType][file]) {
        hierarchy[truthType][file] = {}
      }
      if (!hierarchy[truthType][file][domain]) {
        hierarchy[truthType][file][domain] = []
      }
      
      // Normalize columns to have type info
      const tableColumns = Array.isArray(table.columns) ? table.columns : []
      const normalizedColumns = tableColumns.map(col => {
        if (typeof col === 'string') {
          return { name: col, type: inferColumnType(col) }
        }
        if (col && typeof col === 'object') {
          return { ...col, type: col.type || inferColumnType(col.name || '') }
        }
        return { name: String(col || ''), type: 'string' }
      })
      
      hierarchy[truthType][file][domain].push({
        ...table,
        columns: normalizedColumns
      })
    })
    
    // Convert to array structure for rendering
    // Structure: truthTypes[] -> files[] -> domains[] -> tables[]
    const result = Object.entries(hierarchy).map(([truthType, files]) => {
      const config = TRUTH_TYPE_CONFIG[truthType] || TRUTH_TYPE_CONFIG.reality
      
      const fileList = Object.entries(files).map(([fileName, domains]) => {
        const domainList = Object.entries(domains).map(([domain, tables]) => {
          const domainConfig = DOMAIN_CONFIG[domain] || DOMAIN_CONFIG.general
          return {
            domain,
            label: domainConfig.label || domain,
            icon: domainConfig.icon,
            tables: tables.sort((a, b) => {
              const nameA = a?.display_name || a?.name || ''
              const nameB = b?.display_name || b?.name || ''
              return nameA.localeCompare(nameB)
            })
          }
        }).sort((a, b) => (b.tables?.length || 0) - (a.tables?.length || 0))
        
        const tableCount = domainList.reduce((sum, d) => sum + d.tables.length, 0)
        
        // Shorten filename for display
        const shortName = fileName.length > 40 
          ? fileName.substring(0, 37) + '...' 
          : fileName
        
        return {
          fileName,
          shortName,
          domains: domainList,
          tableCount
        }
      }).sort((a, b) => a.fileName.localeCompare(b.fileName))
      
      return {
        truthType,
        label: config.label,
        icon: config.icon,
        color: config.color,
        files: fileList,
        tableCount: fileList.reduce((sum, f) => sum + f.tableCount, 0)
      }
    })
    
    // Sort by table count descending
    const sorted = result.sort((a, b) => (b.tableCount || 0) - (a.tableCount || 0))
    
    // Log final structure
    sorted.forEach(tt => {
      console.log(`[Analytics] ${tt.truthType}: ${tt.tableCount} tables across ${tt.files.length} files`)
    })
    
    return sorted
  }
  
  const inferDomain = (tableName) => {
    const name = (tableName || '').toLowerCase()
    for (const [domain, config] of Object.entries(DOMAIN_CONFIG)) {
      if (config.keywords?.some(kw => name.includes(kw))) {
        return domain
      }
    }
    return 'general'
  }
  
  const inferColumnType = (colName) => {
    const name = (colName || '').toLowerCase()
    if (name.includes('date') || name.includes('time') || name.includes('_dt') || name.includes('_ts')) return 'date'
    if (name.includes('amount') || name.includes('rate') || name.includes('hours') || name.includes('salary') || 
        name.includes('wage') || name.includes('cost') || name.includes('price') || name.includes('qty') ||
        name.includes('count') || name.includes('total') || name.includes('sum') || name.includes('_num')) return 'number'
    if (name.includes('_id') || name.includes('code') || name.includes('key')) return 'string'
    return 'string'
  }
  
  // ===========================================
  // TABLE SELECTION
  // ===========================================
  
  const handleTableSelect = (table) => {
    setSelectedTable(table)
    // Reset query state
    setColumns([])
    setGroupBy([])
    setFilters([])
    setOrderBy(null)
    setXAxis(null)
    setYAxis(null)
    setResults(null)
    setResultsError(null)
    // Use full_name for SQL (actual DuckDB table name)
    const tableName = table?.full_name || table?.name || 'table'
    setSqlText(`SELECT *\nFROM "${tableName}"\nLIMIT 100`)
  }
  
  const toggleTruthType = (truthType) => {
    setExpandedTruthTypes(prev => ({ ...prev, [truthType]: !prev[truthType] }))
  }
  
  const toggleFile = (truthType, fileName) => {
    const key = `${truthType}:${fileName}`
    setExpandedFiles(prev => ({ ...prev, [key]: !prev[key] }))
  }
  
  const toggleDomain = (truthType, fileName, domain) => {
    const key = `${truthType}:${fileName}:${domain}`
    setExpandedDomains(prev => ({ ...prev, [key]: !prev[key] }))
  }
  
  // ===========================================
  // DRAG AND DROP
  // ===========================================
  
  const handleDragStart = (e, column) => {
    setDraggedColumn({ ...column, table: selectedTable?.full_name })
    e.dataTransfer.effectAllowed = 'copy'
  }
  
  const handleDragOver = (e) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'copy'
  }
  
  const handleDropOnColumns = (e) => {
    e.preventDefault()
    if (draggedColumn && !columns.find(c => c.name === draggedColumn.name)) {
      const newCol = { 
        ...draggedColumn, 
        aggregation: draggedColumn.type === 'number' ? 'SUM' : null 
      }
      setColumns([...columns, newCol])
      
      // Auto-set axes
      if (!xAxis && draggedColumn.type !== 'number') setXAxis(newCol)
      else if (!yAxis && draggedColumn.type === 'number') setYAxis(newCol)
    }
    setDraggedColumn(null)
  }
  
  const handleDropOnGroupBy = (e) => {
    e.preventDefault()
    if (draggedColumn && draggedColumn.type !== 'number' && !groupBy.find(c => c.name === draggedColumn.name)) {
      setGroupBy([...groupBy, draggedColumn])
      if (!xAxis) setXAxis(draggedColumn)
    }
    setDraggedColumn(null)
  }
  
  const handleDropOnXAxis = (e) => {
    e.preventDefault()
    if (draggedColumn) {
      setXAxis(draggedColumn)
      if (draggedColumn.type !== 'number' && !groupBy.find(c => c.name === draggedColumn.name)) {
        setGroupBy([...groupBy, draggedColumn])
      }
    }
    setDraggedColumn(null)
  }
  
  const handleDropOnYAxis = (e) => {
    e.preventDefault()
    if (draggedColumn && draggedColumn.type === 'number') {
      const newCol = { ...draggedColumn, aggregation: 'SUM' }
      setYAxis(newCol)
      if (!columns.find(c => c.name === draggedColumn.name)) {
        setColumns([...columns, newCol])
      }
    }
    setDraggedColumn(null)
  }
  
  const handleDropOnFilters = (e) => {
    e.preventDefault()
    if (draggedColumn && !filters.find(f => f.column?.name === draggedColumn.name)) {
      setFilters([...filters, { column: draggedColumn, operator: '=', value: '' }])
    }
    setDraggedColumn(null)
  }
  
  // ===========================================
  // QUERY MANAGEMENT
  // ===========================================
  
  const removeColumn = (index) => {
    const removed = columns[index]
    setColumns(columns.filter((_, i) => i !== index))
    if (xAxis?.name === removed?.name) setXAxis(null)
    if (yAxis?.name === removed?.name) setYAxis(null)
  }
  
  const removeGroupBy = (index) => {
    const removed = groupBy[index]
    setGroupBy(groupBy.filter((_, i) => i !== index))
    if (xAxis?.name === removed?.name) setXAxis(null)
  }
  
  const removeFilter = (index) => {
    setFilters(filters.filter((_, i) => i !== index))
  }
  
  const updateAggregation = (index, agg) => {
    const updated = [...columns]
    updated[index] = { ...updated[index], aggregation: agg }
    setColumns(updated)
    if (yAxis?.name === updated[index]?.name) {
      setYAxis(updated[index])
    }
  }
  
  const updateFilter = (index, field, value) => {
    const updated = [...filters]
    updated[index] = { ...updated[index], [field]: value }
    setFilters(updated)
  }
  
  // ===========================================
  // SQL GENERATION
  // ===========================================
  
  const generateSQL = () => {
    if (!selectedTable || !Array.isArray(columns) || columns.length === 0) return ''
    
    // Use full_name for DuckDB table name
    const tableName = selectedTable.full_name || selectedTable.name
    if (!tableName) {
      console.error('[Analytics] No table name available:', selectedTable)
      return ''
    }
    
    const selectCols = columns.map(c => {
      if (c?.aggregation) {
        const agg = c.aggregation === 'COUNT DISTINCT' ? 'COUNT(DISTINCT' : c.aggregation + '('
        const close = c.aggregation === 'COUNT DISTINCT' ? ')' : ')'
        const colName = c.name || 'column'
        return `${agg}"${colName}"${close} AS ${c.aggregation.replace(' ', '_').toLowerCase()}_${colName.toLowerCase().replace(/\s+/g, '_')}`
      }
      return `"${c?.name || 'column'}"`
    }).join(',\n       ')
    
    let sql = `SELECT ${selectCols}\nFROM "${tableName}"`
    
    // WHERE clause
    const activeFilters = (filters || []).filter(f => f?.value)
    if (activeFilters.length > 0) {
      const whereClauses = activeFilters.map(f => {
        const colType = f.column?.type
        const colName = f.column?.name || 'column'
        const val = colType === 'number' ? f.value : `'${f.value}'`
        if (f.operator === 'LIKE') return `"${colName}" LIKE '%${f.value}%'`
        if (f.operator === 'IN') return `"${colName}" IN (${f.value})`
        return `"${colName}" ${f.operator} ${val}`
      })
      sql += `\nWHERE ${whereClauses.join('\n  AND ')}`
    }
    
    // GROUP BY clause
    if (Array.isArray(groupBy) && groupBy.length > 0) {
      sql += `\nGROUP BY ${groupBy.map(c => `"${c?.name || 'column'}"`).join(', ')}`
    }
    
    // ORDER BY clause
    if (orderBy) {
      sql += `\nORDER BY "${orderBy.name || 'column'}" ${orderBy.direction || 'DESC'}`
    } else if (columns.find(c => c?.aggregation)) {
      // Default: order by first aggregated column
      const aggCol = columns.find(c => c?.aggregation)
      if (aggCol) {
        const alias = `${aggCol.aggregation.replace(' ', '_').toLowerCase()}_${(aggCol.name || 'column').toLowerCase().replace(/\s+/g, '_')}`
        sql += `\nORDER BY ${alias} DESC`
      }
    }
    
    sql += '\nLIMIT 100'
    
    return sql
  }
  
  // ===========================================
  // QUERY EXECUTION
  // ===========================================
  
  const runBuilderQuery = async () => {
    if (!Array.isArray(columns) || columns.length === 0) return
    
    setResultsLoading(true)
    setResultsError(null)
    setResults(null)
    
    try {
      const sql = generateSQL()
      if (!sql) {
        setResultsError('Could not generate SQL query')
        return
      }
      
      // Use /bi/execute for direct SQL execution
      const response = await api.post('/bi/execute', {
        project: projectName,
        sql: sql
      })
      
      // NULL SAFETY: Defensive access to response data
      const data = response?.data || {}
      const resultData = Array.isArray(data.data) ? data.data : []
      const resultColumns = Array.isArray(data.columns) ? data.columns : 
        (resultData.length > 0 ? Object.keys(resultData[0]) : [])
      
      setResults({
        data: resultData,
        columns: resultColumns,
        sql: sql,
        rowCount: data.row_count || resultData.length || 0
      })
    } catch (err) {
      console.error('Query error:', err)
      const errorMsg = err?.response?.data?.detail || 
                       err?.response?.data?.message ||
                       err?.message || 
                       'Query failed - check console for details'
      setResultsError(errorMsg)
      setResults(null)
    } finally {
      setResultsLoading(false)
    }
  }
  
  const runSQLQuery = async () => {
    if (!sqlText?.trim()) return
    
    setResultsLoading(true)
    setResultsError(null)
    setResults(null)
    
    try {
      // Use /bi/execute for direct SQL execution
      const response = await api.post('/bi/execute', {
        project: projectName,
        sql: sqlText.trim()
      })
      
      // NULL SAFETY: Defensive access to response data
      const data = response?.data || {}
      const resultData = Array.isArray(data.data) ? data.data : []
      const resultColumns = Array.isArray(data.columns) ? data.columns :
        (resultData.length > 0 ? Object.keys(resultData[0]) : [])
      
      setResults({
        data: resultData,
        columns: resultColumns,
        sql: sqlText,
        rowCount: data.row_count || resultData.length || 0
      })
    } catch (err) {
      console.error('Query error:', err)
      const errorMsg = err?.response?.data?.detail || 
                       err?.response?.data?.message ||
                       err?.message || 
                       'Query failed - check console for details'
      setResultsError(errorMsg)
      setResults(null)
    } finally {
      setResultsLoading(false)
    }
  }
  
  const runNLQuery = async () => {
    if (!nlQuery?.trim()) return
    
    setNlMessages(prev => [...prev, { role: 'user', content: nlQuery }])
    const query = nlQuery
    setNlQuery('')
    setIsAnalyzing(true)
    
    try {
      // /bi/query expects: query, project (and optional filters, session_id)
      const response = await api.post('/bi/query', {
        project: projectName,
        query: query
      })
      
      // NULL SAFETY: Defensive access to response data
      const data = response?.data || {}
      const resultData = Array.isArray(data.data) ? data.data : []
      const resultColumns = Array.isArray(data.columns) ? data.columns : []
      
      setNlMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer_text || 'Here are the results:',
        data: resultData,
        columns: resultColumns,
        sql: data.sql,
        chartType: data.chart?.recommended || 'table'
      }])
    } catch (err) {
      console.error('NL Query error:', err)
      setNlMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I couldn't process that query: ${err?.response?.data?.detail || err?.message || 'Unknown error'}`,
        isError: true
      }])
    } finally {
      setIsAnalyzing(false)
    }
  }
  
  const handleQuickQuery = (query) => {
    setNlQuery(query)
    setTimeout(runNLQuery, 50)
  }
  
  // ===========================================
  // UTILITIES
  // ===========================================
  
  const copySQL = () => {
    const sql = mode === 'sql' ? sqlText : generateSQL()
    navigator.clipboard.writeText(sql || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  
  const handleExport = async (format = 'csv') => {
    if (!results?.data?.length) return
    
    try {
      const response = await api.post('/bi/export', {
        project: projectName,
        sql: results.sql,
        format
      }, { responseType: 'blob' })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `export_${Date.now()}.${format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err) {
      console.error('Export error:', err)
    }
  }
  
  // Filter catalog by search
  // Structure: truthTypes[] -> files[] -> domains[] -> tables[]
  const filteredCatalog = Array.isArray(catalog) ? catalog.map(truthTypeGroup => {
    if (!truthTypeGroup) return null
    const files = Array.isArray(truthTypeGroup.files) ? truthTypeGroup.files : []
    
    const filteredFiles = files.map(fileGroup => {
      if (!fileGroup) return null
      const domains = Array.isArray(fileGroup.domains) ? fileGroup.domains : []
      
      const filteredDomains = domains.map(domainGroup => {
        if (!domainGroup) return null
        const tables = Array.isArray(domainGroup.tables) ? domainGroup.tables : []
        
        const filteredTables = tables.filter(t => {
          if (!t) return false
          const search = (catalogSearch || '').toLowerCase()
          if (!search) return true
          const name = (t.name || '').toLowerCase()
          const displayName = (t.display_name || '').toLowerCase()
          const cols = Array.isArray(t.columns) ? t.columns : []
          return name.includes(search) ||
            displayName.includes(search) ||
            cols.some(c => (c?.name || '').toLowerCase().includes(search))
        })
        
        return { ...domainGroup, tables: filteredTables }
      }).filter(d => d && d.tables.length > 0)
      
      const tableCount = filteredDomains.reduce((sum, d) => sum + d.tables.length, 0)
      return { ...fileGroup, domains: filteredDomains, tableCount }
    }).filter(f => f && f.domains.length > 0)
    
    const tableCount = filteredFiles.reduce((sum, f) => sum + f.tableCount, 0)
    return { ...truthTypeGroup, files: filteredFiles, tableCount }
  }).filter(t => t && t.files && t.files.length > 0) : []
  
  // ===========================================
  // RENDER: No Project
  // ===========================================
  
  if (!projectName) {
    return (
      <div style={{ padding: '1.5rem', background: '#f0f2f5', minHeight: 'calc(100vh - 60px)' }}>
        {/* Header - Standard Pattern */}
        <div style={{ marginBottom: '20px' }}>
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
              <BarChart3 size={20} color="#ffffff" />
            </div>
            Smart Analytics
          </h1>
          <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: '#64748b' }}>
            Build queries visually or write SQL directly
          </p>
        </div>
        
        {/* Empty State Card */}
        <div style={{ 
          background: 'white', 
          borderRadius: '12px', 
          border: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '400px'
        }}>
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <Database size={48} style={{ color: '#e2e8f0', marginBottom: '16px' }} />
            <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#64748b', margin: '0 0 8px' }}>Select a Project</h2>
            <p style={{ fontSize: '14px', color: '#94a3b8', margin: 0 }}>Choose a project from the header to analyze data</p>
          </div>
        </div>
      </div>
    )
  }
  
  // ===========================================
  // RENDER: Main Layout
  // ===========================================
  
  return (
    <div style={{ padding: '1.5rem', background: '#f0f2f5', minHeight: 'calc(100vh - 60px)' }}>
      {/* Header - Standard Pattern */}
      <div style={{ marginBottom: '20px' }}>
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
            <BarChart3 size={20} color="#ffffff" />
          </div>
          Smart Analytics
        </h1>
        <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: '#64748b' }}>
          Build queries visually or write SQL directly
        </p>
      </div>

      {/* Main Content */}
      <div className="flex bg-white text-sm overflow-hidden rounded-xl border border-gray-200" style={{ height: 'calc(100vh - 180px)' }}>
        {/* ================================================================
            LEFT PANEL: Data Catalog
            ================================================================ */}
        <div className="w-96 bg-white border-r flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-3 border-b bg-gray-50 flex-shrink-0">
          <h2 className="font-semibold text-gray-800 flex items-center gap-2 text-sm">
            <Layers size={14} className="text-[#83b16d]" />
            Data Catalog <span className="text-xs text-gray-400 ml-1">v5.0</span>
          </h2>
          {Array.isArray(catalog) && catalog.length > 0 && (
            <p className="text-xs text-gray-400 mt-0.5">
              {catalog.reduce((sum, t) => sum + (t?.tableCount || 0), 0)} tables
            </p>
          )}
        </div>
        
        {/* Search */}
        <div className="p-2 border-b flex-shrink-0">
          <div className="relative">
            <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search tables..."
              value={catalogSearch}
              onChange={(e) => setCatalogSearch(e.target.value)}
              className="w-full pl-7 pr-2 py-1.5 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-[#83b16d] focus:border-[#83b16d]"
            />
          </div>
        </div>
        
        {/* Catalog List - scrolls independently */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {console.log('[Analytics] Rendering catalog, filteredCatalog length:', filteredCatalog?.length)}
          {catalogLoading && (
            <div className="p-4 text-center text-gray-400">
              <Loader2 size={20} className="animate-spin mx-auto mb-2" />
              <span className="text-xs">Loading catalog...</span>
            </div>
          )}
          
          {catalogError && (
            <div className="p-4 text-center">
              <AlertCircle size={20} className="mx-auto mb-2 text-[#993c44]" />
              <p className="text-xs text-[#993c44] mb-2">{catalogError}</p>
              <button
                onClick={loadCatalog}
                className="text-xs text-[#83b16d] hover:underline flex items-center gap-1 mx-auto"
              >
                <RefreshCw size={10} /> Retry
              </button>
            </div>
          )}
          
          {Array.isArray(filteredCatalog) && filteredCatalog.map(truthTypeGroup => {
            if (!truthTypeGroup) return null
            const isTruthExpanded = expandedTruthTypes[truthTypeGroup.truthType]
            const files = Array.isArray(truthTypeGroup.files) ? truthTypeGroup.files : []
            
            return (
              <div key={truthTypeGroup.truthType} className="border-b border-gray-200">
                {/* Truth Type Header */}
                <button
                  onClick={() => toggleTruthType(truthTypeGroup.truthType)}
                  className="w-full px-3 py-2.5 flex items-center gap-2 hover:bg-gray-50 transition-colors"
                  style={{ borderLeft: `3px solid ${truthTypeGroup.color || '#83b16d'}` }}
                >
                  {truthTypeGroup.icon && React.createElement(truthTypeGroup.icon, { size: 16, color: truthTypeGroup.color || '#83b16d' })}
                  <div className="flex-1 text-left min-w-0">
                    <div className="text-sm font-semibold text-gray-800">{truthTypeGroup.label}</div>
                    <div className="text-xs text-gray-400">{truthTypeGroup.tableCount} tables • {files.length} files</div>
                  </div>
                  {isTruthExpanded ? (
                    <ChevronDown size={14} className="text-gray-400" />
                  ) : (
                    <ChevronRight size={14} className="text-gray-400" />
                  )}
                </button>
                
                {/* Files within Truth Type */}
                {isTruthExpanded && (
                  <div className="bg-gray-50/50">
                    {files.map(fileGroup => {
                      if (!fileGroup) return null
                      const fileKey = `${truthTypeGroup.truthType}:${fileGroup.fileName}`
                      const isFileExpanded = expandedFiles[fileKey]
                      const domains = Array.isArray(fileGroup.domains) ? fileGroup.domains : []
                      
                      return (
                        <div key={fileGroup.fileName} className="border-t border-gray-100">
                          {/* File Header */}
                          <button
                            onClick={() => toggleFile(truthTypeGroup.truthType, fileGroup.fileName)}
                            className="w-full px-3 py-2 pl-6 flex items-center gap-2 hover:bg-gray-100 transition-colors"
                          >
                            <div className="w-5 h-5 rounded flex items-center justify-center bg-white border border-gray-200">
                              <FileText size={10} className="text-gray-500" />
                            </div>
                            <div className="flex-1 text-left min-w-0">
                              <div className="text-xs font-medium text-gray-700 truncate" title={fileGroup.fileName}>
                                {fileGroup.shortName}
                              </div>
                              <div className="text-xs text-gray-400">{fileGroup.tableCount} tables</div>
                            </div>
                            {isFileExpanded ? (
                              <ChevronDown size={12} className="text-gray-400" />
                            ) : (
                              <ChevronRight size={12} className="text-gray-400" />
                            )}
                          </button>
                          
                          {/* Domains within File */}
                          {isFileExpanded && (
                            <div className="bg-white/50">
                              {domains.map(domainGroup => {
                                if (!domainGroup) return null
                                const Icon = domainGroup.icon || Database
                                const domainKey = `${truthTypeGroup.truthType}:${fileGroup.fileName}:${domainGroup.domain}`
                                const isDomainExpanded = expandedDomains[domainKey]
                                const tables = Array.isArray(domainGroup.tables) ? domainGroup.tables : []
                                
                                return (
                                  <div key={domainGroup.domain} className="border-t border-gray-50">
                                    {/* Domain Header */}
                                    <button
                                      onClick={() => toggleDomain(truthTypeGroup.truthType, fileGroup.fileName, domainGroup.domain)}
                                      className="w-full px-3 py-1.5 pl-10 flex items-center gap-2 hover:bg-gray-50 transition-colors"
                                    >
                                      <Icon size={10} className="text-gray-400" />
                                      <div className="flex-1 text-left min-w-0">
                                        <span className="text-xs text-gray-600">{domainGroup.label}</span>
                                        <span className="text-xs text-gray-400 ml-2">{tables.length}</span>
                                      </div>
                                      {isDomainExpanded ? (
                                        <ChevronDown size={10} className="text-gray-400" />
                                      ) : (
                                        <ChevronRight size={10} className="text-gray-400" />
                                      )}
                                    </button>
                                    
                                    {/* Tables within Domain */}
                                    {isDomainExpanded && (
                                      <div className="pb-1 bg-white">
                                        {tables.map(table => {
                                          if (!table) return null
                                          const tableKey = table.full_name || table.name
                                          return (
                                            <button
                                              key={tableKey}
                                              onClick={() => handleTableSelect(table)}
                                              className={`w-full px-3 py-1.5 pl-14 text-left text-xs hover:bg-gray-50 flex items-center gap-1.5 transition-colors ${
                                                selectedTable?.full_name === table.full_name 
                                                  ? 'bg-[rgba(131,177,109,0.1)] text-[#83b16d] font-medium' 
                                                  : 'text-gray-600'
                                              }`}
                                            >
                                              <Table2 size={10} className="text-gray-400 flex-shrink-0" />
                                              <span className="truncate flex-1">{table.display_name || table.name}</span>
                                              <span className="text-xs text-gray-400 flex-shrink-0">
                                                {table.rows ? (table.rows >= 1000 ? (table.rows / 1000).toFixed(0) + 'k' : table.rows) : ''}
                                              </span>
                                            </button>
                                          )
                                        })}
                                      </div>
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
        </div>
      
        {/* ================================================================
            CENTER PANEL: Main Canvas
            ================================================================ */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Toolbar with mode toggle */}
          <div className="bg-gray-50 border-b px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              {selectedTable ? (
                <>
                <Database size={14} className="text-[#83b16d]" />
                <span className="font-medium">{selectedTable.display_name || selectedTable.name || 'Table'}</span>
                <span className="text-gray-400">•</span>
                <span className="text-gray-400">{selectedTable.rows?.toLocaleString() || 0} rows</span>
                <span className="text-gray-400">•</span>
                <span className="text-gray-400">{Array.isArray(selectedTable.columns) ? selectedTable.columns.length : 0} columns</span>
              </>
            ) : (
              <span className="text-gray-400">Select a table from the catalog</span>
            )}
          </div>
          
          {/* 2-Way Mode Toggle */}
          <div className="flex bg-white rounded-lg p-0.5 border">
            <button
              onClick={() => setMode('builder')}
              title="Drag and drop columns to build queries visually"
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-all ${
                mode === 'builder' 
                  ? 'bg-[#83b16d] text-white' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <GripVertical size={12} />
              Visual Builder
            </button>
            <button
              onClick={() => setMode('sql')}
              title="Write or paste SQL directly for full control"
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-all ${
                mode === 'sql' 
                  ? 'bg-[#83b16d] text-white' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Code size={12} />
              SQL
            </button>
          </div>
        </div>
        
        {/* ============================================
            MODE: SQL
            ============================================ */}
        {mode === 'sql' && (
          <div className="flex-1 flex flex-col p-4 gap-4">
            {!selectedTable ? (
              <NoTableSelected />
            ) : (
              <>
                <div className="flex flex-col">
                  <textarea
                    value={sqlText}
                    onChange={(e) => setSqlText(e.target.value)}
                    onKeyDown={(e) => {
                      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                        e.preventDefault()
                        runSQLQuery()
                      }
                    }}
                    placeholder={`SELECT *\nFROM "${selectedTable?.full_name || 'table'}"\nLIMIT 100`}
                    className="w-full p-3 text-xs font-mono border rounded-lg focus:outline-none focus:ring-1 focus:ring-[#83b16d] focus:border-[#83b16d] bg-gray-50 resize-none min-h-[140px]"
                    spellCheck={false}
                  />
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-xs text-gray-400">⌘+Enter to run</span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setSqlText('')}
                        title="Clear the SQL editor"
                        className="px-3 py-1.5 rounded-lg text-xs text-gray-500 hover:bg-gray-100 transition-colors"
                      >
                        Clear
                      </button>
                      <button
                        onClick={runSQLQuery}
                        disabled={!sqlText?.trim() || resultsLoading}
                        title="Execute the SQL query against your project data"
                        className="px-4 py-1.5 rounded-lg bg-[#83b16d] text-white text-xs font-medium hover:bg-[#6b9b5a] disabled:opacity-50 flex items-center gap-1.5 transition-colors"
                      >
                        {resultsLoading ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                        Run Query
                      </button>
                    </div>
                  </div>
                </div>
                
                {resultsError && (
                  <div className="p-3 bg-[rgba(153,60,68,0.1)] border border-[#993c44]/20 rounded-lg text-[#993c44] text-xs">
                    <div className="flex items-center gap-2">
                      <AlertCircle size={14} />
                      <span>{resultsError}</span>
                    </div>
                  </div>
                )}
                
                {results && (
                  <ResultsPanel 
                    results={results} 
                    chartType={chartType} 
                    setChartType={setChartType}
                    onExport={handleExport}
                  />
                )}
              </>
            )}
          </div>
        )}
        
        {/* ============================================
            MODE: Visual Builder
            ============================================ */}
        {mode === 'builder' && (
          <div className="flex-1 flex overflow-hidden">
            {!selectedTable ? (
              <NoTableSelected />
            ) : (
              <>
                {/* Drop Zones Area */}
                <div className="flex-1 p-4 overflow-auto">
                  {/* Columns & Group By */}
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <DropZone
                      label="Columns"
                      hint="Drag columns to SELECT"
                      items={columns}
                      onDragOver={handleDragOver}
                      onDrop={handleDropOnColumns}
                      renderItem={(col, i) => (
                        <ColumnChip
                          key={i}
                          column={col}
                          showAggregation={col?.type === 'number'}
                          aggregation={col?.aggregation}
                          onAggregationChange={(agg) => updateAggregation(i, agg)}
                          onRemove={() => removeColumn(i)}
                        />
                      )}
                      isDragActive={!!draggedColumn}
                    />
                    
                    <DropZone
                      label="Group By"
                      hint="Text/date columns"
                      items={groupBy}
                      onDragOver={handleDragOver}
                      onDrop={handleDropOnGroupBy}
                      renderItem={(col, i) => (
                        <ColumnChip
                          key={i}
                          column={col}
                          onRemove={() => removeGroupBy(i)}
                        />
                      )}
                      isDragActive={!!draggedColumn && draggedColumn.type !== 'number'}
                    />
                  </div>
                  
                  {/* Filters */}
                  <DropZone
                    label="Filters"
                    hint="Add WHERE conditions"
                    items={filters}
                    onDragOver={handleDragOver}
                    onDrop={handleDropOnFilters}
                    renderItem={(filter, i) => (
                      <FilterRow
                        key={i}
                        filter={filter}
                        onChange={(field, value) => updateFilter(i, field, value)}
                        onRemove={() => removeFilter(i)}
                      />
                    )}
                    isDragActive={!!draggedColumn}
                    className="mb-3"
                  />
                  
                  {/* Chart Configuration */}
                  <div className="bg-white rounded-lg border p-3 mb-3">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-gray-700">Visualization</span>
                      <div className="flex gap-0.5 bg-gray-100 rounded p-0.5">
                        {[
                          { type: 'table', icon: Table2, label: 'Table' },
                          { type: 'bar', icon: BarChart3, label: 'Bar' },
                          { type: 'line', icon: LineChart, label: 'Line' },
                          { type: 'pie', icon: PieChart, label: 'Pie' },
                        ].map(({ type, icon: Icon, label }) => (
                          <button
                            key={type}
                            onClick={() => setChartType(type)}
                            className={`p-1.5 rounded transition-colors ${
                              chartType === type 
                                ? 'bg-white shadow-sm text-[#83b16d]' 
                                : 'text-gray-400 hover:text-gray-600'
                            }`}
                            title={label}
                          >
                            <Icon size={12} />
                          </button>
                        ))}
                      </div>
                    </div>
                    
                    {chartType !== 'table' && (
                      <div className="grid grid-cols-2 gap-3">
                        {/* X-Axis */}
                        <div
                          onDragOver={handleDragOver}
                          onDrop={handleDropOnXAxis}
                          className={`border-2 border-dashed rounded-lg p-2 text-center transition-colors ${
                            draggedColumn 
                              ? 'border-[#83b16d] bg-[rgba(131,177,109,0.1)]' 
                              : 'border-gray-200'
                          }`}
                        >
                          <div className="text-xs text-gray-500 mb-1">X-Axis (Category)</div>
                          {xAxis ? (
                            <div className="inline-flex items-center gap-1 px-2 py-1 bg-[#285390] text-white rounded text-xs">
                              {xAxis.name}
                              <button onClick={() => setXAxis(null)} className="hover:text-red-200">
                                <X size={10} />
                              </button>
                            </div>
                          ) : (
                            <div className="text-xs text-gray-400">Drop column</div>
                          )}
                        </div>
                        
                        {/* Y-Axis */}
                        <div
                          onDragOver={handleDragOver}
                          onDrop={handleDropOnYAxis}
                          className={`border-2 border-dashed rounded-lg p-2 text-center transition-colors ${
                            draggedColumn && draggedColumn.type === 'number' 
                              ? 'border-[#83b16d] bg-[rgba(131,177,109,0.1)]' 
                              : 'border-gray-200'
                          }`}
                        >
                          <div className="text-xs text-gray-500 mb-1">Y-Axis (Value)</div>
                          {yAxis ? (
                            <div className="inline-flex items-center gap-1 px-2 py-1 bg-[#83b16d] text-white rounded text-xs">
                              {yAxis.aggregation && (
                                <span className="opacity-75">{yAxis.aggregation}</span>
                              )}
                              {yAxis.name}
                              <button onClick={() => setYAxis(null)} className="hover:text-red-200">
                                <X size={10} />
                              </button>
                            </div>
                          ) : (
                            <div className="text-xs text-gray-400">Drop numeric</div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Run Button & SQL Preview */}
                  <div className="flex items-center gap-3 mb-3">
                    <button
                      onClick={runBuilderQuery}
                      disabled={!Array.isArray(columns) || columns.length === 0 || resultsLoading}
                      title="Execute the generated query against your project data"
                      className="px-4 py-2 rounded-lg bg-[#83b16d] text-white text-xs font-medium hover:bg-[#6b9b5a] disabled:opacity-50 flex items-center gap-1.5 transition-colors"
                    >
                      {resultsLoading ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                      Run Query
                    </button>
                    <button
                      onClick={() => setShowSQL(!showSQL)}
                      title={showSQL ? 'Hide the generated SQL' : 'Show the generated SQL query'}
                      className={`px-3 py-2 rounded-lg text-xs flex items-center gap-1.5 transition-colors ${
                        showSQL 
                          ? 'bg-gray-200 text-gray-700' 
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      <Code size={12} />
                      {showSQL ? 'Hide' : 'Show'} SQL
                    </button>
                    {showSQL && (
                      <button
                        onClick={copySQL}
                        className="p-2 rounded hover:bg-gray-100 text-gray-500 transition-colors"
                        title="Copy SQL"
                      >
                        {copied ? <Check size={12} className="text-green-500" /> : <Copy size={12} />}
                      </button>
                    )}
                  </div>
                  
                  {showSQL && (
                    <pre className="bg-gray-800 text-gray-100 p-3 rounded-lg text-xs font-mono mb-3 overflow-x-auto whitespace-pre-wrap">
                      {generateSQL() || '-- Drag columns to generate SQL'}
                    </pre>
                  )}
                  
                  {resultsError && (
                    <div className="p-3 bg-[rgba(153,60,68,0.1)] border border-[#993c44]/20 rounded-lg text-[#993c44] text-xs mb-3">
                      <div className="flex items-center gap-2">
                        <AlertCircle size={14} />
                        <span>{resultsError}</span>
                      </div>
                    </div>
                  )}
                  
                  {results && (
                    <ResultsPanel 
                      results={results} 
                      chartType={chartType} 
                      setChartType={setChartType}
                      onExport={handleExport}
                    />
                  )}
                </div>
                
                {/* Column List for Dragging */}
                <div className="w-52 bg-white border-l flex flex-col">
                  <div className="p-3 border-b bg-gray-50">
                    <div className="text-xs font-medium text-gray-700">Available Columns</div>
                    <div className="text-xs text-gray-400 mt-0.5">Drag to query builder</div>
                  </div>
                  <div className="flex-1 overflow-auto p-2">
                    {Array.isArray(selectedTable?.columns) && selectedTable.columns.map((col, i) => {
                      if (!col) return null
                      return (
                        <div
                          key={i}
                          draggable
                          onDragStart={(e) => handleDragStart(e, col)}
                          className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-50 cursor-grab active:cursor-grabbing group transition-colors"
                        >
                          <GripVertical size={10} className="text-gray-300 group-hover:text-gray-400" />
                          <TypeIcon type={col.type} />
                          <span className="text-xs text-gray-700 flex-1 truncate">{col.name}</span>
                          <span className="text-xs text-gray-400">{col.type}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
        </div>
      </div>
    </div>
  )
}


// =============================================================================
// SUB-COMPONENTS
// =============================================================================

function NoTableSelected() {
  return (
    <div className="flex-1 flex items-center justify-center text-gray-400">
      <div className="text-center">
        <Database size={32} className="mx-auto mb-2 opacity-50" />
        <p className="text-sm">Select a table from the catalog to start</p>
      </div>
    </div>
  )
}

function DropZone({ label, hint, items, onDragOver, onDrop, renderItem, isDragActive, className = '' }) {
  const safeItems = Array.isArray(items) ? items : []
  return (
    <div
      onDragOver={onDragOver}
      onDrop={onDrop}
      className={`bg-white rounded-lg border p-3 transition-all ${
        isDragActive ? 'border-[#83b16d] ring-2 ring-[#83b16d]/20' : ''
      } ${className}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-700">{label}</span>
        <span className="text-xs text-gray-400">{safeItems.length > 0 ? `${safeItems.length} selected` : hint}</span>
      </div>
      <div className={`min-h-[40px] border-2 border-dashed rounded-lg p-2 flex flex-wrap gap-1.5 transition-colors ${
        isDragActive ? 'border-[#83b16d] bg-[rgba(131,177,109,0.1)]' : 'border-gray-200'
      }`}>
        {safeItems.length === 0 ? (
          <span className="text-xs text-gray-400 m-auto">Drop here</span>
        ) : (
          safeItems.map((item, i) => renderItem(item, i))
        )}
      </div>
    </div>
  )
}

function ColumnChip({ column, showAggregation, aggregation, onAggregationChange, onRemove }) {
  const [showDropdown, setShowDropdown] = useState(false)
  
  if (!column) return null
  
  return (
    <div className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-xs relative">
      <TypeIcon type={column.type} size={10} />
      {showAggregation && aggregation && (
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="text-[#83b16d] font-medium hover:underline"
        >
          {aggregation}
        </button>
      )}
      <span className="text-gray-700">{column.name}</span>
      <button onClick={onRemove} className="text-gray-400 hover:text-red-500 ml-0.5">
        <X size={10} />
      </button>
      
      {showDropdown && (
        <div className="absolute top-full left-0 mt-1 bg-white border rounded-lg shadow-lg py-1 z-10 min-w-[100px]">
          {AGGREGATIONS.map(agg => (
            <button
              key={agg}
              onClick={() => { onAggregationChange(agg); setShowDropdown(false) }}
              className={`w-full px-3 py-1 text-left text-xs hover:bg-gray-50 transition-colors ${
                aggregation === agg ? 'text-[#83b16d] font-medium bg-[rgba(131,177,109,0.1)]' : 'text-gray-600'
              }`}
            >
              {agg}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function FilterRow({ filter, onChange, onRemove }) {
  if (!filter || !filter.column) return null
  
  const operators = filter.column.type === 'number'
    ? ['=', '!=', '>', '<', '>=', '<=']
    : ['=', '!=', 'LIKE', 'IN', 'IS NULL', 'IS NOT NULL']
  
  return (
    <div className="flex items-center gap-2 p-2 bg-gray-50 rounded w-full">
      <TypeIcon type={filter.column.type} size={10} />
      <span className="text-xs text-gray-700 min-w-[70px] truncate">{filter.column.name}</span>
      <select
        value={filter.operator || '='}
        onChange={(e) => onChange('operator', e.target.value)}
        className="px-2 py-1 text-xs border rounded bg-white focus:outline-none focus:ring-1 focus:ring-[#83b16d]"
      >
        {operators.map(op => <option key={op} value={op}>{op}</option>)}
      </select>
      {!['IS NULL', 'IS NOT NULL'].includes(filter.operator) && (
        <input
          type="text"
          value={filter.value || ''}
          onChange={(e) => onChange('value', e.target.value)}
          placeholder="value"
          className="flex-1 px-2 py-1 text-xs border rounded min-w-[80px] focus:outline-none focus:ring-1 focus:ring-[#83b16d]"
        />
      )}
      <button onClick={onRemove} className="text-gray-400 hover:text-red-500 transition-colors">
        <X size={12} />
      </button>
    </div>
  )
}

function TypeIcon({ type, size = 10 }) {
  if (type === 'number') return <Hash size={size} className="text-[#d97706]" />
  if (type === 'date' || type === 'time') return <Calendar size={size} className="text-[#285390]" />
  return <FileText size={size} className="text-gray-400" />
}

function ResultsPanel({ results, chartType, setChartType, onExport }) {
  // NULL SAFETY: Ensure results exists and has expected structure
  if (!results) return null
  
  const data = Array.isArray(results.data) ? results.data : []
  const columns = Array.isArray(results.columns) ? results.columns : []
  const xKey = columns[0]
  const yKey = columns[1]
  
  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <div className="px-3 py-2 border-b bg-gray-50 flex items-center justify-between">
        <span className="text-xs font-medium text-gray-700">
          Results ({results.rowCount || data.length || 0} rows)
        </span>
        <div className="flex items-center gap-2">
          <div className="flex gap-0.5 bg-gray-100 rounded p-0.5">
            {[
              { type: 'table', icon: Table2 },
              { type: 'bar', icon: BarChart3 },
              { type: 'line', icon: LineChart },
              { type: 'pie', icon: PieChart },
            ].map(({ type, icon: Icon }) => (
              <button
                key={type}
                onClick={() => setChartType(type)}
                className={`p-1.5 rounded transition-colors ${
                  chartType === type 
                    ? 'bg-white shadow-sm text-[#83b16d]' 
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                <Icon size={12} />
              </button>
            ))}
          </div>
          <button 
            onClick={() => onExport('csv')}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-500 transition-colors"
            title="Export CSV"
          >
            <Download size={12} />
          </button>
        </div>
      </div>
      
      <div className="p-3">
        {data.length === 0 ? (
          <div className="text-center py-8 text-gray-400 text-sm">No data returned</div>
        ) : (
          <>
            {chartType === 'table' && (
              <div className="overflow-auto max-h-64">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50">
                      {columns.map(col => (
                        <th key={col} className="px-3 py-2 text-left font-medium text-gray-600 border-b whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.slice(0, 100).map((row, i) => (
                      <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                        {columns.map(col => (
                          <td key={col} className="px-3 py-2 text-gray-700 whitespace-nowrap">
                            {formatCellValue(row?.[col])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            
            {chartType === 'bar' && xKey && yKey && (
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.slice(0, 20)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                    <XAxis dataKey={xKey} tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={formatAxisValue} />
                    <Tooltip formatter={formatTooltipValue} contentStyle={{ fontSize: 11 }} />
                    <Bar dataKey={yKey} fill="#83b16d" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            
            {chartType === 'line' && xKey && yKey && (
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.slice(0, 50)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                    <XAxis dataKey={xKey} tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={formatAxisValue} />
                    <Tooltip formatter={formatTooltipValue} contentStyle={{ fontSize: 11 }} />
                    <Area type="monotone" dataKey={yKey} stroke="#83b16d" fill="rgba(131,177,109,0.1)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
            
            {chartType === 'pie' && xKey && yKey && (
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPie>
                    <Pie
                      data={data.slice(0, 10)}
                      dataKey={yKey}
                      nameKey={xKey}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                      fontSize={10}
                    >
                      {data.slice(0, 10).map((_, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_PALETTE[index % CHART_PALETTE.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={formatTooltipValue} contentStyle={{ fontSize: 11 }} />
                  </RechartsPie>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}
      </div>
    </div>
    </div>
  )
}

// Value formatters
function formatCellValue(val) {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'number') return val.toLocaleString()
  return String(val)
}

function formatAxisValue(val) {
  if (typeof val !== 'number') return val
  if (val >= 1000000) return (val / 1000000).toFixed(1) + 'M'
  if (val >= 1000) return (val / 1000).toFixed(1) + 'K'
  return val
}

function formatTooltipValue(val) {
  if (typeof val === 'number') return val.toLocaleString()
  return val
}

// =============================================================================
// NATURAL LANGUAGE COMPONENTS
// =============================================================================

function NLEmptyState({ selectedTable, onQuickQuery }) {
  const queries = selectedTable ? [
    { icon: Eye, label: 'Preview data', query: `Show first 20 rows of ${selectedTable.name}` },
    { icon: BarChart3, label: 'Summarize', query: `Summarize ${selectedTable.name} by the most common groupings` },
    { icon: Filter, label: 'Find patterns', query: `What patterns or anomalies exist in ${selectedTable.name}?` },
  ] : [
    { icon: Users, label: 'Employee overview', query: 'How many employees are in the system?' },
    { icon: DollarSign, label: 'Payroll summary', query: 'Show total payroll by department' },
    { icon: Clock, label: 'Time analysis', query: 'What are the most common time entry patterns?' },
  ]
  
  return (
    <div className="max-w-md mx-auto pt-8">
      <div className="text-center mb-5">
        <div className="w-10 h-10 rounded-xl mx-auto mb-2 flex items-center justify-center bg-[rgba(131,177,109,0.1)]">
          <Sparkles size={18} className="text-[#83b16d]" />
        </div>
        <h2 className="text-base font-semibold text-gray-800 mb-1">
          {selectedTable ? `Explore ${selectedTable.name}` : 'Ask a question'}
        </h2>
        <p className="text-xs text-gray-500">Type naturally or try a suggestion</p>
      </div>
      
      <div className="grid grid-cols-1 gap-2">
        {queries.map((item, i) => (
          <button
            key={i}
            onClick={() => onQuickQuery(item.query)}
            className="p-3 bg-white border rounded-lg text-left hover:border-[#83b16d] hover:shadow-sm transition-all group flex items-center gap-3"
          >
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 group-hover:bg-[rgba(131,177,109,0.1)] transition-colors">
              <item.icon size={14} className="text-gray-400 group-hover:text-[#83b16d]" />
            </div>
            <div>
              <div className="text-sm font-medium text-gray-700 group-hover:text-[#83b16d]">{item.label}</div>
              <div className="text-xs text-gray-400 truncate">{item.query}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

function NLMessageBubble({ message }) {
  const [localChartType, setLocalChartType] = useState(message?.chartType || 'table')
  
  if (!message) return null
  
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-[#83b16d] text-white px-3 py-2 rounded-xl rounded-br-sm max-w-md text-sm">
          {message.content}
        </div>
      </div>
    )
  }
  
  const data = Array.isArray(message.data) ? message.data : []
  const columns = Array.isArray(message.columns) ? message.columns : []
  
  return (
    <div className="flex gap-2">
      <div className="w-6 h-6 rounded-full bg-[rgba(131,177,109,0.1)] flex items-center justify-center flex-shrink-0 mt-0.5">
        <Sparkles size={12} className="text-[#83b16d]" />
      </div>
      <div className="flex-1 space-y-2 min-w-0">
        <div className={`text-sm ${message.isError ? 'text-[#993c44]' : 'text-gray-700'}`}>
          {message.content}
        </div>
        
        {data.length > 0 && (
          <div className="bg-white border rounded-lg overflow-hidden">
            <div className="px-2 py-1.5 border-b bg-gray-50 flex items-center justify-between">
              <span className="text-xs text-gray-500">{data.length} rows</span>
              <div className="flex gap-0.5">
                {[
                  { type: 'table', icon: Table2 },
                  { type: 'bar', icon: BarChart3 },
                  { type: 'line', icon: LineChart },
                  { type: 'pie', icon: PieChart },
                ].map(({ type, icon: Icon }) => (
                  <button
                    key={type}
                    onClick={() => setLocalChartType(type)}
                    className={`p-1 rounded transition-colors ${
                      localChartType === type 
                        ? 'bg-[#83b16d] text-white' 
                        : 'text-gray-400 hover:text-gray-600'
                    }`}
                  >
                    <Icon size={12} />
                  </button>
                ))}
              </div>
            </div>
            
            <div className="p-2">
              {localChartType === 'table' && (
                <div className="overflow-auto max-h-48">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-gray-50">
                        {columns.map(col => (
                          <th key={col} className="px-2 py-1.5 text-left font-medium text-gray-600 border-b">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {data.slice(0, 20).map((row, i) => (
                        <tr key={i} className="border-b border-gray-50">
                          {columns.map(col => (
                            <td key={col} className="px-2 py-1.5 text-gray-700">{formatCellValue(row?.[col])}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              
              {localChartType === 'bar' && columns.length >= 2 && (
                <div className="h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.slice(0, 15)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                      <XAxis dataKey={columns[0]} tick={{ fontSize: 9 }} />
                      <YAxis tick={{ fontSize: 9 }} tickFormatter={formatAxisValue} />
                      <Tooltip formatter={formatTooltipValue} contentStyle={{ fontSize: 10 }} />
                      <Bar dataKey={columns[1]} fill="#83b16d" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
              
              {localChartType === 'line' && columns.length >= 2 && (
                <div className="h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.slice(0, 30)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                      <XAxis dataKey={columns[0]} tick={{ fontSize: 9 }} />
                      <YAxis tick={{ fontSize: 9 }} tickFormatter={formatAxisValue} />
                      <Tooltip formatter={formatTooltipValue} contentStyle={{ fontSize: 10 }} />
                      <Area type="monotone" dataKey={columns[1]} stroke="#83b16d" fill="rgba(131,177,109,0.1)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
              
              {localChartType === 'pie' && columns.length >= 2 && (
                <div className="h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <RechartsPie>
                      <Pie
                        data={data.slice(0, 8)}
                        dataKey={columns[1]}
                        nameKey={columns[0]}
                        cx="50%"
                        cy="50%"
                        outerRadius={60}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                        fontSize={9}
                      >
                        {data.slice(0, 8).map((_, index) => (
                          <Cell key={`cell-${index}`} fill={CHART_PALETTE[index % CHART_PALETTE.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={formatTooltipValue} contentStyle={{ fontSize: 10 }} />
                    </RechartsPie>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>
        )}
        
        {message.sql && (
          <details className="text-xs">
            <summary className="cursor-pointer text-gray-400 hover:text-gray-600">View SQL</summary>
            <pre className="mt-1 p-2 bg-gray-800 text-gray-100 rounded text-xs font-mono overflow-x-auto">{message.sql}</pre>
          </details>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// WRAPPED EXPORT - With error boundary
// =============================================================================

export default function AnalyticsPage() {
  return (
    <AnalyticsErrorBoundary>
      <AnalyticsPageInner />
    </AnalyticsErrorBoundary>
  )
}
