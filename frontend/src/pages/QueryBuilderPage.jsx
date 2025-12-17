/**
 * QueryBuilderPage.jsx - Smart Analytics
 * =======================================
 * 
 * Visual query builder with:
 * - Smart table display names
 * - Auto-joins
 * - Charts/Visualizations
 * 
 * Deploy to: frontend/src/pages/QueryBuilderPage.jsx
 */

import { useState, useEffect } from 'react'
import { useProject } from '../context/ProjectContext'
import { useTheme } from '../context/ThemeContext'
import api from '../services/api'
import { 
  Database, Table2, Play, Download, 
  Plus, X, Check, AlertCircle, Sparkles,
  RefreshCw, Code2, Copy, CheckCheck, Link2,
  Loader2, Activity, BarChart3, PieChart, TrendingUp
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart as RePieChart, Pie, Cell, LineChart, Line } from 'recharts'

// =============================================================================
// CONSTANTS
// =============================================================================

const COLORS = {
  grassGreen: '#83b16d',
  grassGreenLight: '#f0f7ed',
  text: '#2a3441',
  textLight: '#5f6c7b',
  border: '#e1e8ed',
}

const CHART_COLORS = ['#83b16d', '#93abd9', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#14b8a6']

// =============================================================================
// SMART TABLE NAME PARSER
// =============================================================================

function parseTableDisplayName(fullName, shortName, file, sheet) {
  // Priority: sheet name > file name > short name
  if (sheet && sheet !== 'Sheet1' && sheet !== 'Sheet 1') {
    // Clean up sheet name
    return cleanName(sheet)
  }
  if (file) {
    // Extract filename without extension
    const fileName = file.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ')
    return cleanName(fileName)
  }
  if (shortName) {
    return cleanName(shortName)
  }
  // Fallback: parse full name
  const parts = fullName.split('__')
  return cleanName(parts[parts.length - 1])
}

function cleanName(name) {
  if (!name) return 'Unknown'
  return name
    .replace(/[-_]/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2') // camelCase to spaces
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
    .trim()
    .substring(0, 30) // Max 30 chars
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function QueryBuilderPage() {
  const { projectName } = useProject()
  const { darkMode, T } = useTheme()
  
  // Schema state
  const [tables, setTables] = useState([])
  const [relationships, setRelationships] = useState([])
  const [isLoadingSchema, setIsLoadingSchema] = useState(true)
  
  // Query builder state
  const [selectedTables, setSelectedTables] = useState([])
  const [selectedColumns, setSelectedColumns] = useState([])
  const [filters, setFilters] = useState([])
  const [orderBy, setOrderBy] = useState({ column: '', direction: 'DESC' })
  const [limit, setLimit] = useState(100)
  
  // Results state
  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [showSQL, setShowSQL] = useState(false)
  const [copied, setCopied] = useState(false)
  
  // Chart state
  const [showChart, setShowChart] = useState(false)
  const [chartType, setChartType] = useState('bar')
  const [chartConfig, setChartConfig] = useState({ xAxis: '', yAxis: '' })

  // ===========================================
  // LOAD SCHEMA
  // ===========================================
  
  useEffect(() => {
    if (projectName) {
      loadSchema()
    }
  }, [projectName])
  
  const loadSchema = async () => {
    setIsLoadingSchema(true)
    try {
      const response = await api.get(`/bi/schema/${projectName}`)
      const schema = response.data
      
      const tableList = (schema.tables || []).map(t => ({
        name: t.full_name || t.name, // Use full_name for SQL!
        shortName: t.name,
        displayName: parseTableDisplayName(t.full_name || t.name, t.name, t.file, t.sheet),
        rows: t.row_count || t.rows || 0,
        columns: t.columns || [],
        file: t.file,
        sheet: t.sheet,
        keyColumns: (t.columns || []).filter(c => 
          c.toLowerCase().endsWith('_id') || 
          c.toLowerCase().endsWith('_code') ||
          c.toLowerCase() === 'id'
        )
      }))
      
      setTables(tableList)
      setRelationships(detectRelationships(tableList))
    } catch (err) {
      console.error('Failed to load schema:', err)
      setTables([])
    } finally {
      setIsLoadingSchema(false)
    }
  }
  
  const detectRelationships = (tableList) => {
    const rels = []
    tableList.forEach((t1, i) => {
      tableList.forEach((t2, j) => {
        if (i >= j) return
        t1.keyColumns.forEach(k1 => {
          t2.keyColumns.forEach(k2 => {
            if (k1 === k2 || 
                (k1.replace('_id', '_code') === k2) ||
                (k1.replace('_code', '_id') === k2)) {
              rels.push({
                from: { table: t1.name, column: k1 },
                to: { table: t2.name, column: k2 }
              })
            }
          })
        })
      })
    })
    return rels
  }

  // ===========================================
  // TABLE & COLUMN SELECTION
  // ===========================================
  
  const selectTable = (table) => {
    if (selectedTables.find(t => t.name === table.name)) {
      setSelectedTables(prev => prev.filter(t => t.name !== table.name))
      setSelectedColumns(prev => prev.filter(c => c.table !== table.name))
    } else {
      setSelectedTables(prev => [...prev, { ...table }])
    }
  }
  
  const getRelatedTables = (tableName) => {
    const related = []
    relationships.forEach(rel => {
      if (rel.from.table === tableName) {
        const t = tables.find(t => t.name === rel.to.table)
        if (t && !selectedTables.find(st => st.name === t.name)) {
          related.push({ table: t, joinOn: { from: rel.from.column, to: rel.to.column } })
        }
      } else if (rel.to.table === tableName) {
        const t = tables.find(t => t.name === rel.from.table)
        if (t && !selectedTables.find(st => st.name === t.name)) {
          related.push({ table: t, joinOn: { from: rel.to.column, to: rel.from.column } })
        }
      }
    })
    return related
  }
  
  const toggleColumn = (tableName, columnName) => {
    const exists = selectedColumns.find(c => c.table === tableName && c.column === columnName)
    if (exists) {
      setSelectedColumns(prev => prev.filter(c => !(c.table === tableName && c.column === columnName)))
    } else {
      setSelectedColumns(prev => [...prev, { table: tableName, column: columnName }])
    }
  }
  
  const selectAllColumns = (tableName) => {
    const table = tables.find(t => t.name === tableName)
    if (!table) return
    const newCols = table.columns
      .filter(col => !selectedColumns.find(c => c.table === tableName && c.column === col))
      .map(col => ({ table: tableName, column: col }))
    setSelectedColumns(prev => [...prev, ...newCols])
  }
  
  const clearTableColumns = (tableName) => {
    setSelectedColumns(prev => prev.filter(c => c.table !== tableName))
  }

  // ===========================================
  // FILTERS
  // ===========================================
  
  const addFilter = () => {
    const firstTable = selectedTables[0]
    const firstColumn = firstTable?.columns?.[0] || ''
    setFilters(prev => [...prev, {
      id: Date.now(),
      table: firstTable?.name || '',
      column: firstColumn,
      operator: '=',
      value: ''
    }])
  }
  
  const updateFilter = (id, field, value) => {
    setFilters(prev => prev.map(f => f.id === id ? { ...f, [field]: value } : f))
  }
  
  const removeFilter = (id) => {
    setFilters(prev => prev.filter(f => f.id !== id))
  }
  
  const getAllColumns = () => {
    const cols = []
    selectedTables.forEach(table => {
      table.columns.forEach(col => {
        cols.push({ 
          table: table.name, 
          column: col, 
          display: selectedTables.length > 1 ? `${table.displayName}.${col}` : col 
        })
      })
    })
    return cols
  }

  // ===========================================
  // SQL GENERATION - Use full table names!
  // ===========================================
  
  const generateSQL = () => {
    if (selectedTables.length === 0) return '-- Select a table to begin'
    
    const primaryTable = selectedTables[0]
    
    // Quote table name if it contains special chars
    const quoteName = (name) => name.includes('__') || name.includes('-') ? `"${name}"` : name
    
    const cols = selectedColumns.length > 0
      ? selectedColumns.map(c => {
          const colName = selectedTables.length > 1 ? `${quoteName(c.table)}.${c.column}` : c.column
          return colName
        }).join(', ')
      : '*'
    
    let sql = `SELECT ${cols}\nFROM ${quoteName(primaryTable.name)}`
    
    if (selectedTables.length > 1) {
      selectedTables.slice(1).forEach(table => {
        const rel = relationships.find(r => 
          (r.from.table === primaryTable.name && r.to.table === table.name) ||
          (r.to.table === primaryTable.name && r.from.table === table.name)
        )
        if (rel) {
          const isFromPrimary = rel.from.table === primaryTable.name
          const joinCol1 = isFromPrimary ? rel.from.column : rel.to.column
          const joinCol2 = isFromPrimary ? rel.to.column : rel.from.column
          sql += `\nLEFT JOIN ${quoteName(table.name)} ON ${quoteName(primaryTable.name)}.${joinCol1} = ${quoteName(table.name)}.${joinCol2}`
        }
      })
    }
    
    const validFilters = filters.filter(f => f.column && f.operator && (f.operator.includes('NULL') || f.value))
    if (validFilters.length > 0) {
      const whereClauses = validFilters.map(f => {
        const colRef = selectedTables.length > 1 ? `${quoteName(f.table)}.${f.column}` : f.column
        if (f.operator === 'IS NULL' || f.operator === 'IS NOT NULL') return `${colRef} ${f.operator}`
        if (f.operator === 'LIKE') return `${colRef} ILIKE '%${f.value}%'`
        const quote = isNaN(f.value) ? "'" : ''
        return `${colRef} ${f.operator} ${quote}${f.value}${quote}`
      })
      sql += `\nWHERE ${whereClauses.join(' AND ')}`
    }
    
    if (orderBy.column) {
      sql += `\nORDER BY ${orderBy.column} ${orderBy.direction}`
    }
    
    sql += `\nLIMIT ${limit}`
    
    return sql
  }
  
  const copySQL = () => {
    navigator.clipboard.writeText(generateSQL())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // ===========================================
  // RUN QUERY
  // ===========================================
  
  const runQuery = async () => {
    if (selectedTables.length === 0) {
      setError('Please select at least one table')
      return
    }
    
    setIsLoading(true)
    setError(null)
    setShowChart(false)
    
    try {
      const sql = generateSQL()
      console.log('[Smart Analytics] Running SQL:', sql)
      
      const response = await api.post('/bi/execute', { sql, project: projectName })
      
      const data = response.data.data || []
      const columns = response.data.columns || (data.length > 0 ? Object.keys(data[0]) : [])
      
      setResults({
        columns,
        data,
        rowCount: response.data.row_count || data.length,
        executionTime: response.data.execution_time || 0
      })
      
      // Auto-detect chart config
      autoDetectChartConfig(columns, data)
      
    } catch (err) {
      console.error('Query failed:', err)
      setError(err.response?.data?.detail || err.message || 'Query failed')
    } finally {
      setIsLoading(false)
    }
  }
  
  // ===========================================
  // CHART AUTO-CONFIG
  // ===========================================
  
  const autoDetectChartConfig = (columns, data) => {
    if (!data || data.length === 0) return
    
    // Find first string column (for X axis) and first numeric column (for Y axis)
    let xCol = ''
    let yCol = ''
    
    const sample = data[0]
    for (const col of columns) {
      const val = sample[col]
      if (!xCol && typeof val === 'string') xCol = col
      if (!yCol && typeof val === 'number') yCol = col
    }
    
    // Fallback
    if (!xCol && columns.length > 0) xCol = columns[0]
    if (!yCol && columns.length > 1) yCol = columns[1]
    
    setChartConfig({ xAxis: xCol, yAxis: yCol })
  }
  
  const getChartData = () => {
    if (!results?.data || !chartConfig.xAxis || !chartConfig.yAxis) return []
    
    // Aggregate if needed (group by xAxis, sum yAxis)
    const grouped = {}
    results.data.forEach(row => {
      const key = String(row[chartConfig.xAxis] || 'Unknown')
      const val = Number(row[chartConfig.yAxis]) || 0
      grouped[key] = (grouped[key] || 0) + val
    })
    
    return Object.entries(grouped)
      .map(([name, value]) => ({ name, value }))
      .slice(0, 20) // Max 20 items for chart
  }

  const resetAll = () => {
    setSelectedTables([])
    setSelectedColumns([])
    setFilters([])
    setOrderBy({ column: '', direction: 'DESC' })
    setResults(null)
    setError(null)
    setShowChart(false)
  }

  // ===========================================
  // STYLES
  // ===========================================
  
  const styles = {
    container: { minHeight: '100%' },
    header: { marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' },
    title: { fontFamily: "'Sora', sans-serif", fontSize: '1.75rem', fontWeight: 700, color: T.text, margin: 0 },
    subtitle: { color: T.textDim, marginTop: '0.25rem' },
    headerActions: { display: 'flex', gap: '0.5rem' },
    btn: { display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', border: `1px solid ${T.border}`, borderRadius: '8px', background: T.bgCard, color: T.textDim, fontSize: '0.875rem', fontWeight: 500, cursor: 'pointer' },
    btnActive: { background: COLORS.grassGreenLight, borderColor: COLORS.grassGreen, color: COLORS.grassGreen },
    mainCard: { background: T.bgCard, borderRadius: '16px', boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)', overflow: 'hidden' },
    grid: { display: 'grid', gridTemplateColumns: '340px 1fr', minHeight: '600px' },
    leftPanel: { borderRight: `1px solid ${T.border}`, padding: '1rem', overflowY: 'auto', maxHeight: '75vh' },
    rightPanel: { display: 'flex', flexDirection: 'column', overflow: 'hidden' },
    section: { marginBottom: '1.25rem' },
    sectionHeader: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' },
    stepNumber: { width: '24px', height: '24px', borderRadius: '6px', background: COLORS.grassGreen, color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 600 },
    sectionTitle: { fontWeight: 600, color: T.text, fontSize: '0.875rem' },
    tableCard: { padding: '0.75rem', border: `2px solid ${T.border}`, borderRadius: '10px', cursor: 'pointer', marginBottom: '0.5rem', transition: 'all 0.15s ease' },
    tableCardSelected: { borderColor: COLORS.grassGreen, background: darkMode ? 'rgba(131, 177, 109, 0.1)' : COLORS.grassGreenLight },
    tableName: { fontWeight: 600, color: T.text, fontSize: '0.85rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
    tableMeta: { fontSize: '0.7rem', color: T.textDim, marginTop: '0.25rem' },
    columnGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.25rem', maxHeight: '140px', overflowY: 'auto', padding: '0.5rem', background: T.panelLight, borderRadius: '8px' },
    columnBtn: { display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.4rem', border: 'none', borderRadius: '4px', background: 'transparent', color: T.textDim, fontSize: '0.7rem', cursor: 'pointer', textAlign: 'left', overflow: 'hidden' },
    columnBtnSelected: { background: darkMode ? 'rgba(131, 177, 109, 0.15)' : COLORS.grassGreenLight, color: COLORS.grassGreen, fontWeight: 500 },
    checkbox: (checked) => ({ width: '12px', height: '12px', borderRadius: '3px', border: `2px solid ${checked ? COLORS.grassGreen : T.border}`, background: checked ? COLORS.grassGreen : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }),
    filterRow: { display: 'flex', gap: '0.4rem', alignItems: 'center', marginBottom: '0.4rem', padding: '0.5rem', background: T.panelLight, borderRadius: '6px', flexWrap: 'wrap' },
    select: { flex: 1, minWidth: '80px', padding: '0.4rem', border: `1px solid ${T.border}`, borderRadius: '4px', background: T.bgCard, color: T.text, fontSize: '0.75rem' },
    input: { flex: 1, minWidth: '60px', padding: '0.4rem', border: `1px solid ${T.border}`, borderRadius: '4px', background: T.bgCard, color: T.text, fontSize: '0.75rem' },
    runBtn: { width: '100%', padding: '0.875rem', border: 'none', borderRadius: '10px', background: COLORS.grassGreen, color: 'white', fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' },
    sqlPreview: { background: '#1e293b', color: '#4ade80', padding: '1rem', fontFamily: 'monospace', fontSize: '0.8rem', whiteSpace: 'pre-wrap', borderBottom: `1px solid ${T.border}`, maxHeight: '150px', overflowY: 'auto' },
    resultsHeader: { padding: '1rem', borderBottom: `1px solid ${T.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' },
    table: { width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' },
    th: { textAlign: 'left', padding: '0.6rem 0.75rem', background: T.panelLight, borderBottom: `1px solid ${T.border}`, fontWeight: 600, color: T.text, fontSize: '0.75rem' },
    td: { padding: '0.6rem 0.75rem', borderBottom: `1px solid ${T.border}`, color: T.textDim, fontSize: '0.75rem' },
    emptyState: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem 2rem', textAlign: 'center' },
    chartContainer: { height: '300px', padding: '1rem' },
  }

  // ===========================================
  // RENDER: NO PROJECT
  // ===========================================
  
  if (!projectName) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyState}>
          <Database size={48} color={T.textDim} style={{ marginBottom: '1rem' }} />
          <h2 style={{ color: T.text, marginBottom: '0.5rem' }}>Select a Project</h2>
          <p style={{ color: T.textDim }}>Choose a project from the header to start querying</p>
        </div>
      </div>
    )
  }

  // ===========================================
  // RENDER
  // ===========================================
  
  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Smart Analytics</h1>
          <p style={styles.subtitle}>
            Build queries visually • <strong>{projectName}</strong>
            {!isLoadingSchema && ` • ${tables.length} tables`}
          </p>
        </div>
        
        <div style={styles.headerActions}>
          <button style={styles.btn} onClick={resetAll}>
            <RefreshCw size={16} /> Reset
          </button>
          <button 
            style={{ ...styles.btn, ...(showSQL ? styles.btnActive : {}) }} 
            onClick={() => setShowSQL(!showSQL)}
          >
            <Code2 size={16} /> SQL
          </button>
        </div>
      </div>
      
      {/* Main Card */}
      <div style={styles.mainCard}>
        <div style={styles.grid}>
          {/* Left Panel - Builder */}
          <div style={styles.leftPanel}>
            
            {/* Step 1: Tables */}
            <div style={styles.section}>
              <div style={styles.sectionHeader}>
                <div style={styles.stepNumber}>1</div>
                <span style={styles.sectionTitle}>Select Tables</span>
              </div>
              
              {isLoadingSchema ? (
                <div style={{ textAlign: 'center', padding: '1.5rem', color: T.textDim }}>
                  <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
                  <p style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>Loading...</p>
                </div>
              ) : tables.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '1.5rem', color: T.textDim, fontSize: '0.85rem' }}>
                  No tables found. Upload data first.
                </div>
              ) : (
                tables.map(table => {
                  const isSelected = selectedTables.find(t => t.name === table.name)
                  const related = isSelected ? getRelatedTables(table.name) : []
                  
                  return (
                    <div key={table.name}>
                      <div 
                        style={{ ...styles.tableCard, ...(isSelected ? styles.tableCardSelected : {}) }}
                        onClick={() => selectTable(table)}
                        title={table.name}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={styles.tableName}>{table.displayName}</div>
                            <div style={styles.tableMeta}>
                              {table.rows.toLocaleString()} rows • {table.columns.length} cols
                            </div>
                          </div>
                          {isSelected && <Check size={16} color={COLORS.grassGreen} />}
                        </div>
                      </div>
                      
                      {/* Related tables */}
                      {related.length > 0 && (
                        <div style={{ marginLeft: '0.75rem', marginBottom: '0.5rem' }}>
                          <div style={{ fontSize: '0.65rem', color: T.textDim, marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            <Link2 size={10} /> Auto-join:
                          </div>
                          {related.slice(0, 3).map(r => (
                            <button
                              key={r.table.name}
                              onClick={() => selectTable(r.table)}
                              style={{ 
                                display: 'flex', alignItems: 'center', gap: '0.4rem',
                                padding: '0.4rem 0.6rem', marginBottom: '0.25rem',
                                border: `1px dashed ${T.border}`, borderRadius: '6px',
                                background: 'transparent', color: T.textDim,
                                fontSize: '0.7rem', cursor: 'pointer', width: '100%',
                              }}
                            >
                              <Plus size={12} color={COLORS.grassGreen} />
                              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.table.displayName}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
            
            {/* Step 2: Columns */}
            {selectedTables.length > 0 && (
              <div style={styles.section}>
                <div style={styles.sectionHeader}>
                  <div style={styles.stepNumber}>2</div>
                  <span style={styles.sectionTitle}>
                    Columns {selectedColumns.length > 0 && `(${selectedColumns.length})`}
                  </span>
                </div>
                
                {selectedTables.map(table => (
                  <div key={table.name} style={{ marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 500, color: T.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{table.displayName}</span>
                      <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
                        <button onClick={() => selectAllColumns(table.name)} style={{ fontSize: '0.65rem', color: COLORS.grassGreen, background: 'none', border: 'none', cursor: 'pointer' }}>All</button>
                        <button onClick={() => clearTableColumns(table.name)} style={{ fontSize: '0.65rem', color: T.textDim, background: 'none', border: 'none', cursor: 'pointer' }}>Clear</button>
                      </div>
                    </div>
                    <div style={styles.columnGrid}>
                      {table.columns.map(col => {
                        const isSelected = selectedColumns.find(c => c.table === table.name && c.column === col)
                        return (
                          <button
                            key={col}
                            onClick={() => toggleColumn(table.name, col)}
                            style={{ ...styles.columnBtn, ...(isSelected ? styles.columnBtnSelected : {}) }}
                            title={col}
                          >
                            <div style={styles.checkbox(isSelected)}>
                              {isSelected && <Check size={8} color="white" />}
                            </div>
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{col}</span>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {/* Step 3: Filters */}
            {selectedTables.length > 0 && (
              <div style={styles.section}>
                <div style={{ ...styles.sectionHeader, justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={styles.stepNumber}>3</div>
                    <span style={styles.sectionTitle}>Filters</span>
                  </div>
                  <button onClick={addFilter} style={{ ...styles.btn, padding: '0.2rem 0.5rem', fontSize: '0.7rem' }}>
                    <Plus size={12} /> Add
                  </button>
                </div>
                
                {filters.length === 0 ? (
                  <div style={{ padding: '0.75rem', textAlign: 'center', color: T.textDim, fontSize: '0.75rem', background: T.panelLight, borderRadius: '6px' }}>
                    No filters
                  </div>
                ) : (
                  filters.map(filter => (
                    <div key={filter.id} style={styles.filterRow}>
                      <select
                        style={styles.select}
                        value={`${filter.table}|||${filter.column}`}
                        onChange={(e) => {
                          const [table, column] = e.target.value.split('|||')
                          updateFilter(filter.id, 'table', table)
                          updateFilter(filter.id, 'column', column)
                        }}
                      >
                        {getAllColumns().map(c => (
                          <option key={`${c.table}|||${c.column}`} value={`${c.table}|||${c.column}`}>{c.column}</option>
                        ))}
                      </select>
                      <select
                        style={{ ...styles.select, width: '70px', flex: 'none' }}
                        value={filter.operator}
                        onChange={(e) => updateFilter(filter.id, 'operator', e.target.value)}
                      >
                        <option value="=">=</option>
                        <option value="!=">≠</option>
                        <option value=">">{">"}</option>
                        <option value="<">{"<"}</option>
                        <option value="LIKE">~</option>
                        <option value="IS NULL">∅</option>
                        <option value="IS NOT NULL">≠∅</option>
                      </select>
                      {!['IS NULL', 'IS NOT NULL'].includes(filter.operator) && (
                        <input
                          style={styles.input}
                          value={filter.value}
                          onChange={(e) => updateFilter(filter.id, 'value', e.target.value)}
                          placeholder="value"
                        />
                      )}
                      <button onClick={() => removeFilter(filter.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.textDim, padding: '0.2rem' }}>
                        <X size={14} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
            
            {/* Step 4: Sort & Limit */}
            {selectedTables.length > 0 && (
              <div style={styles.section}>
                <div style={styles.sectionHeader}>
                  <div style={styles.stepNumber}>4</div>
                  <span style={styles.sectionTitle}>Sort & Limit</span>
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', marginBottom: '0.5rem' }}>
                  <select style={styles.select} value={orderBy.column} onChange={(e) => setOrderBy(p => ({ ...p, column: e.target.value }))}>
                    <option value="">Sort by...</option>
                    {getAllColumns().map(c => <option key={c.column} value={c.column}>{c.column}</option>)}
                  </select>
                  <select style={styles.select} value={orderBy.direction} onChange={(e) => setOrderBy(p => ({ ...p, direction: e.target.value }))}>
                    <option value="ASC">↑ Asc</option>
                    <option value="DESC">↓ Desc</option>
                  </select>
                </div>
                
                <div style={{ display: 'flex', gap: '0.4rem' }}>
                  {[50, 100, 500, 1000].map(n => (
                    <button
                      key={n}
                      onClick={() => setLimit(n)}
                      style={{
                        flex: 1, padding: '0.4rem', border: 'none', borderRadius: '4px',
                        background: limit === n ? COLORS.grassGreen : T.panelLight,
                        color: limit === n ? 'white' : T.textDim,
                        fontWeight: 500, cursor: 'pointer', fontSize: '0.75rem',
                      }}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {/* Run Button */}
            {selectedTables.length > 0 && (
              <button style={styles.runBtn} onClick={runQuery} disabled={isLoading}>
                {isLoading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <Play size={18} />}
                {isLoading ? 'Running...' : 'Run Query'}
              </button>
            )}
          </div>
          
          {/* Right Panel - Results */}
          <div style={styles.rightPanel}>
            {/* SQL Preview */}
            {showSQL && (
              <div style={styles.sqlPreview}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ color: '#94a3b8', fontSize: '0.7rem' }}>Generated SQL</span>
                  <button onClick={copySQL} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    {copied ? <CheckCheck size={12} /> : <Copy size={12} />}
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                {generateSQL()}
              </div>
            )}
            
            {/* Error */}
            {error && (
              <div style={{ margin: '1rem', padding: '0.75rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertCircle size={18} color="#ef4444" />
                <span style={{ color: '#dc2626', fontSize: '0.85rem' }}>{error}</span>
              </div>
            )}
            
            {/* Results */}
            {results ? (
              <>
                <div style={styles.resultsHeader}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Activity size={18} color={COLORS.grassGreen} />
                    <div>
                      <div style={{ fontWeight: 600, color: T.text, fontSize: '0.9rem' }}>Results</div>
                      <div style={{ fontSize: '0.75rem', color: T.textDim }}>
                        {results.rowCount} rows • {results.executionTime}ms
                      </div>
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', gap: '0.4rem' }}>
                    <button 
                      style={{ ...styles.btn, padding: '0.4rem 0.75rem', fontSize: '0.75rem', ...(showChart ? styles.btnActive : {}) }}
                      onClick={() => setShowChart(!showChart)}
                    >
                      <BarChart3 size={14} /> Chart
                    </button>
                    <button style={{ ...styles.btn, padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}>
                      <Download size={14} /> Export
                    </button>
                  </div>
                </div>
                
                {/* Chart */}
                {showChart && results.data.length > 0 && (
                  <div style={{ borderBottom: `1px solid ${T.border}`, padding: '1rem' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                      <select 
                        style={{ ...styles.select, width: 'auto' }}
                        value={chartType}
                        onChange={(e) => setChartType(e.target.value)}
                      >
                        <option value="bar">Bar</option>
                        <option value="pie">Pie</option>
                        <option value="line">Line</option>
                      </select>
                      <span style={{ fontSize: '0.7rem', color: T.textDim }}>X:</span>
                      <select 
                        style={{ ...styles.select, width: 'auto' }}
                        value={chartConfig.xAxis}
                        onChange={(e) => setChartConfig(p => ({ ...p, xAxis: e.target.value }))}
                      >
                        {results.columns.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                      <span style={{ fontSize: '0.7rem', color: T.textDim }}>Y:</span>
                      <select 
                        style={{ ...styles.select, width: 'auto' }}
                        value={chartConfig.yAxis}
                        onChange={(e) => setChartConfig(p => ({ ...p, yAxis: e.target.value }))}
                      >
                        {results.columns.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                    
                    <div style={{ height: '250px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        {chartType === 'bar' ? (
                          <BarChart data={getChartData()}>
                            <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                            <XAxis dataKey="name" tick={{ fontSize: 10, fill: T.textDim }} />
                            <YAxis tick={{ fontSize: 10, fill: T.textDim }} />
                            <Tooltip />
                            <Bar dataKey="value" fill={COLORS.grassGreen} radius={[4, 4, 0, 0]} />
                          </BarChart>
                        ) : chartType === 'pie' ? (
                          <RePieChart>
                            <Pie
                              data={getChartData()}
                              dataKey="value"
                              nameKey="name"
                              cx="50%"
                              cy="50%"
                              outerRadius={80}
                              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                              labelLine={false}
                            >
                              {getChartData().map((_, i) => (
                                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip />
                          </RePieChart>
                        ) : (
                          <LineChart data={getChartData()}>
                            <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                            <XAxis dataKey="name" tick={{ fontSize: 10, fill: T.textDim }} />
                            <YAxis tick={{ fontSize: 10, fill: T.textDim }} />
                            <Tooltip />
                            <Line type="monotone" dataKey="value" stroke={COLORS.grassGreen} strokeWidth={2} dot={{ fill: COLORS.grassGreen }} />
                          </LineChart>
                        )}
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
                
                <div style={{ flex: 1, overflow: 'auto', padding: '0.75rem' }}>
                  <table style={styles.table}>
                    <thead>
                      <tr>
                        {results.columns.map(col => <th key={col} style={styles.th}>{col}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {results.data.slice(0, 100).map((row, i) => (
                        <tr key={i}>
                          {results.columns.map(col => (
                            <td key={col} style={styles.td}>
                              {typeof row[col] === 'number' && (col.toLowerCase().includes('salary') || col.toLowerCase().includes('amount') || col.toLowerCase().includes('pay'))
                                ? `$${row[col].toLocaleString()}`
                                : row[col] ?? '-'
                              }
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {results.data.length > 100 && (
                    <div style={{ textAlign: 'center', padding: '1rem', color: T.textDim, fontSize: '0.8rem' }}>
                      Showing 100 of {results.data.length} rows
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div style={styles.emptyState}>
                <Sparkles size={40} color={T.textDim} style={{ marginBottom: '1rem' }} />
                <h3 style={{ color: T.text, marginBottom: '0.5rem', fontSize: '1.1rem' }}>Build Your Query</h3>
                <p style={{ color: T.textDim, maxWidth: '280px', fontSize: '0.85rem' }}>
                  Select tables, choose columns, add filters, and click Run Query.
                  <br /><br />
                  <span style={{ color: COLORS.grassGreen }}>Smart joins are automatic!</span>
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
      
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
