import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

/**
 * Vacuum Column Mapping
 * 
 * Visual mapping interface for pay register data.
 * Shows document preview on left, mapping interface on right.
 * 
 * Pay registers always have 5 sections:
 * - Employee Info (+ injected header metadata)
 * - Earnings
 * - Taxes  
 * - Deductions
 * - Pay Info
 */

const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app'

// Section definitions with colors and icons
const SECTIONS = {
  employee_info: { label: 'Employee Info', icon: '👤', color: '#3b82f6', bgColor: '#eff6ff' },
  earnings: { label: 'Earnings', icon: '💰', color: '#22c55e', bgColor: '#f0fdf4' },
  taxes: { label: 'Taxes', icon: '🏛️', color: '#ef4444', bgColor: '#fef2f2' },
  deductions: { label: 'Deductions', icon: '📋', color: '#f59e0b', bgColor: '#fffbeb' },
  pay_info: { label: 'Pay Info', icon: '💵', color: '#8b5cf6', bgColor: '#f5f3ff' }
}

// Target fields by section
const TARGET_FIELDS = {
  employee_info: [
    { value: 'employee_id', label: 'Employee ID' },
    { value: 'employee_name', label: 'Employee Name' },
    { value: 'first_name', label: 'First Name' },
    { value: 'last_name', label: 'Last Name' },
    { value: 'ssn', label: 'SSN' },
    { value: 'department', label: 'Department' },
    { value: 'location', label: 'Location' },
    { value: 'job_title', label: 'Job Title' },
    { value: 'hire_date', label: 'Hire Date' },
    { value: 'term_date', label: 'Term Date' },
    { value: 'pay_rate', label: 'Pay Rate' },
    { value: 'skip', label: '⏭️ Skip' },
  ],
  earnings: [
    { value: 'earning_code', label: 'Earning Code' },
    { value: 'earning_description', label: 'Description' },
    { value: 'hours_current', label: 'Current Hours' },
    { value: 'hours_ytd', label: 'YTD Hours' },
    { value: 'rate', label: 'Rate' },
    { value: 'amount_current', label: 'Current Amount' },
    { value: 'amount_ytd', label: 'YTD Amount' },
    { value: 'skip', label: '⏭️ Skip' },
  ],
  taxes: [
    { value: 'tax_code', label: 'Tax Code' },
    { value: 'tax_description', label: 'Description' },
    { value: 'taxable_wages', label: 'Taxable Wages' },
    { value: 'tax_amount_current', label: 'Current Amount' },
    { value: 'tax_amount_ytd', label: 'YTD Amount' },
    { value: 'tax_er_current', label: 'Employer Current' },
    { value: 'tax_er_ytd', label: 'Employer YTD' },
    { value: 'skip', label: '⏭️ Skip' },
  ],
  deductions: [
    { value: 'deduction_code', label: 'Deduction Code' },
    { value: 'deduction_description', label: 'Description' },
    { value: 'deduction_ee_current', label: 'Employee Current' },
    { value: 'deduction_ee_ytd', label: 'Employee YTD' },
    { value: 'deduction_er_current', label: 'Employer Current' },
    { value: 'deduction_er_ytd', label: 'Employer YTD' },
    { value: 'skip', label: '⏭️ Skip' },
  ],
  pay_info: [
    { value: 'gross_pay', label: 'Gross Pay' },
    { value: 'net_pay', label: 'Net Pay' },
    { value: 'total_taxes', label: 'Total Taxes' },
    { value: 'total_deductions', label: 'Total Deductions' },
    { value: 'check_number', label: 'Check Number' },
    { value: 'direct_deposit', label: 'Direct Deposit' },
    { value: 'skip', label: '⏭️ Skip' },
  ]
}

export default function VacuumColumnMapping() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const fileParam = searchParams.get('file')

  // State
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [extracts, setExtracts] = useState([])
  const [headerMetadata, setHeaderMetadata] = useState({
    company: '',
    pay_period_start: '',
    pay_period_end: '',
    check_date: ''
  })
  const [activeSection, setActiveSection] = useState('earnings')
  const [sectionMappings, setSectionMappings] = useState({})
  const [sectionStatus, setSectionStatus] = useState({
    employee_info: 'pending',
    earnings: 'pending',
    taxes: 'pending',
    deductions: 'pending',
    pay_info: 'pending'
  })
  const [showPreview, setShowPreview] = useState(true)
  const [saving, setSaving] = useState(false)

  // Load files on mount
  useEffect(() => {
    loadFiles()
  }, [])

  // Load file from URL param
  useEffect(() => {
    if (fileParam && files.length > 0) {
      const file = files.find(f => f.source_file === fileParam)
      if (file) {
        selectFile(file)
      }
    }
  }, [fileParam, files])

  const loadFiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/files`)
      const data = await res.json()
      setFiles(data.files || [])
      setLoading(false)
    } catch (err) {
      setError('Failed to load files')
      setLoading(false)
    }
  }

  const selectFile = async (file) => {
    setSelectedFile(file)
    setLoading(true)
    
    try {
      // Load extracts for this file
      const res = await fetch(`${API_BASE}/api/vacuum/extracts?source_file=${encodeURIComponent(file.source_file)}`)
      const data = await res.json()
      setExtracts(data.extracts || [])
      
      // Try to extract header metadata
      await extractHeaderMetadata(file.source_file)
      
      // Initialize mappings for each section
      initializeMappings(data.extracts || [])
      
      // Set first section with data as active
      const sectionsWithData = (data.extracts || []).map(e => e.detected_section).filter(Boolean)
      if (sectionsWithData.length > 0) {
        setActiveSection(sectionsWithData[0])
      }
      
      setLoading(false)
    } catch (err) {
      setError('Failed to load file data')
      setLoading(false)
    }
  }

  const extractHeaderMetadata = async (sourceFile) => {
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/header-metadata?source_file=${encodeURIComponent(sourceFile)}`)
      if (res.ok) {
        const data = await res.json()
        setHeaderMetadata(data.metadata || {
          company: '',
          pay_period_start: '',
          pay_period_end: '',
          check_date: ''
        })
      }
    } catch (err) {
      console.log('Header metadata not available')
    }
  }

  const initializeMappings = (extractsList) => {
    const mappings = {}
    
    extractsList.forEach(extract => {
      const section = extract.detected_section || 'unknown'
      if (!mappings[section]) {
        mappings[section] = {
          extract_id: extract.id,
          columns: {}
        }
      }
      
      // Initialize column mappings with AI suggestions
      const headers = extract.headers || []
      const classifications = extract.column_classifications || {}
      
      headers.forEach((header, idx) => {
        const suggestion = classifications[header] || classifications[idx] || null
        mappings[section].columns[header] = {
          index: idx,
          suggested: suggestion?.type || 'skip',
          confirmed: suggestion?.type || 'skip',
          confidence: suggestion?.confidence || 0
        }
      })
    })
    
    setSectionMappings(mappings)
  }

  const getExtractForSection = (section) => {
    return extracts.find(e => e.detected_section === section)
  }

  const updateColumnMapping = (section, header, targetField) => {
    setSectionMappings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        columns: {
          ...prev[section]?.columns,
          [header]: {
            ...prev[section]?.columns?.[header],
            confirmed: targetField
          }
        }
      }
    }))
  }

  const confirmSection = (section) => {
    setSectionStatus(prev => ({
      ...prev,
      [section]: 'done'
    }))
    
    // Move to next pending section
    const sectionOrder = ['employee_info', 'earnings', 'taxes', 'deductions', 'pay_info']
    const currentIdx = sectionOrder.indexOf(section)
    for (let i = currentIdx + 1; i < sectionOrder.length; i++) {
      if (sectionStatus[sectionOrder[i]] !== 'done' && getExtractForSection(sectionOrder[i])) {
        setActiveSection(sectionOrder[i])
        return
      }
    }
  }

  const confirmAllHighConfidence = () => {
    const section = activeSection
    const mapping = sectionMappings[section]
    if (!mapping) return
    
    // All high confidence mappings are already set as confirmed
    // Just mark section as done
    confirmSection(section)
  }

  const saveAllMappings = async () => {
    setSaving(true)
    
    try {
      const payload = {
        source_file: selectedFile.source_file,
        header_metadata: headerMetadata,
        section_mappings: sectionMappings,
        remember_for_vendor: true
      }
      
      const res = await fetch(`${API_BASE}/api/vacuum/apply-mappings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      
      if (res.ok) {
        alert('Mappings saved successfully!')
        navigate('/vacuum/explore')
      } else {
        const data = await res.json()
        setError(data.detail || 'Failed to save mappings')
      }
    } catch (err) {
      setError('Failed to save mappings: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  const getConfidenceLevel = (confidence) => {
    if (confidence >= 0.85) return 'high'
    if (confidence >= 0.70) return 'medium'
    return 'low'
  }

  const highConfidenceCount = () => {
    const mapping = sectionMappings[activeSection]
    if (!mapping) return 0
    return Object.values(mapping.columns).filter(c => c.confidence >= 0.85).length
  }

  const completedSections = Object.values(sectionStatus).filter(s => s === 'done').length

  // Loading state
  if (loading && !selectedFile) {
    return (
      <div style={styles.loadingContainer}>
        <div style={styles.spinner}></div>
        <p>Loading...</p>
      </div>
    )
  }

  // File selection if no file selected
  if (!selectedFile) {
    return (
      <div style={styles.fileSelectContainer}>
        <h1 style={styles.pageTitle}>🗺️ Map Columns</h1>
        <p style={styles.pageSubtitle}>Select a file to map its columns to the standard schema</p>
        
        {files.length === 0 ? (
          <div style={styles.emptyState}>
            <p>No files available. Upload files first in the Vacuum Extract section.</p>
            <button style={styles.btnPrimary} onClick={() => navigate('/vacuum')}>
              Go to Upload
            </button>
          </div>
        ) : (
          <div style={styles.fileGrid}>
            {files.map((file, idx) => (
              <div 
                key={idx} 
                style={styles.fileCard}
                onClick={() => selectFile(file)}
              >
                <div style={styles.fileIcon}>📄</div>
                <div style={styles.fileDetails}>
                  <div style={styles.fileName}>{file.source_file}</div>
                  <div style={styles.fileMeta}>
                    {file.table_count} tables • {file.total_rows} rows
                  </div>
                  {file.sections_found && (
                    <div style={styles.fileSections}>
                      {file.sections_found.split(',').map((s, i) => (
                        <span key={i} style={{
                          ...styles.sectionTag,
                          background: SECTIONS[s.trim()]?.bgColor || '#f3f4f6',
                          color: SECTIONS[s.trim()]?.color || '#666'
                        }}>
                          {SECTIONS[s.trim()]?.icon} {SECTIONS[s.trim()]?.label || s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  const currentExtract = getExtractForSection(activeSection)
  const currentMapping = sectionMappings[activeSection]
  const sectionConfig = SECTIONS[activeSection]

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>🗺️ Map Columns</h1>
          <div style={styles.fileInfo}>
            <span style={styles.fileNameHeader}>{selectedFile.source_file}</span>
          </div>
        </div>
        <div style={styles.headerActions}>
          <button style={styles.btnSecondary} onClick={() => setSelectedFile(null)}>
            ← Change File
          </button>
          <button 
            style={styles.btnSuccess} 
            onClick={confirmAllHighConfidence}
            disabled={!currentExtract}
          >
            ✓ Confirm High ({highConfidenceCount()})
          </button>
          <button 
            style={styles.btnPrimary} 
            onClick={saveAllMappings}
            disabled={saving || completedSections < 1}
          >
            {saving ? 'Saving...' : '💾 Save All Mappings'}
          </button>
        </div>
      </div>

      {/* Main Split View */}
      <div style={styles.mainSplit}>
        {/* Left Panel - Document Preview */}
        <div style={styles.docPanel}>
          <div style={styles.docHeader}>
            <span style={styles.docTitle}>📄 Document Sections</span>
          </div>
          
          {/* Header Metadata */}
          <div style={styles.metadataSection}>
            <h4 style={styles.metadataTitle}>📋 Header Information</h4>
            <div style={styles.metadataGrid}>
              <div style={styles.metadataField}>
                <label>Company</label>
                <input 
                  type="text" 
                  value={headerMetadata.company}
                  onChange={(e) => setHeaderMetadata(prev => ({ ...prev, company: e.target.value }))}
                  placeholder="Extracted or enter..."
                  style={styles.metadataInput}
                />
              </div>
              <div style={styles.metadataField}>
                <label>Pay Period Start</label>
                <input 
                  type="text" 
                  value={headerMetadata.pay_period_start}
                  onChange={(e) => setHeaderMetadata(prev => ({ ...prev, pay_period_start: e.target.value }))}
                  placeholder="MM/DD/YYYY"
                  style={styles.metadataInput}
                />
              </div>
              <div style={styles.metadataField}>
                <label>Pay Period End</label>
                <input 
                  type="text" 
                  value={headerMetadata.pay_period_end}
                  onChange={(e) => setHeaderMetadata(prev => ({ ...prev, pay_period_end: e.target.value }))}
                  placeholder="MM/DD/YYYY"
                  style={styles.metadataInput}
                />
              </div>
              <div style={styles.metadataField}>
                <label>Check Date</label>
                <input 
                  type="text" 
                  value={headerMetadata.check_date}
                  onChange={(e) => setHeaderMetadata(prev => ({ ...prev, check_date: e.target.value }))}
                  placeholder="MM/DD/YYYY"
                  style={styles.metadataInput}
                />
              </div>
            </div>
          </div>

          {/* Section List */}
          <div style={styles.sectionList}>
            {Object.entries(SECTIONS).map(([key, config]) => {
              const extract = getExtractForSection(key)
              const status = sectionStatus[key]
              const isActive = activeSection === key
              
              return (
                <div
                  key={key}
                  style={{
                    ...styles.sectionCard,
                    ...(isActive ? { 
                      borderColor: config.color,
                      background: config.bgColor 
                    } : {}),
                    ...(status === 'done' ? styles.sectionCardDone : {}),
                    ...(!extract ? styles.sectionCardEmpty : {})
                  }}
                  onClick={() => extract && setActiveSection(key)}
                >
                  <div style={styles.sectionCardHeader}>
                    <span style={styles.sectionIcon}>{config.icon}</span>
                    <span style={styles.sectionLabel}>{config.label}</span>
                    {status === 'done' && <span style={styles.checkMark}>✓</span>}
                  </div>
                  {extract ? (
                    <div style={styles.sectionCardMeta}>
                      {extract.row_count} rows • {extract.headers?.length || 0} columns
                    </div>
                  ) : (
                    <div style={styles.sectionCardMeta}>No data detected</div>
                  )}
                  {extract && (
                    <div style={styles.sectionCardHeaders}>
                      {extract.headers?.slice(0, 4).join(', ')}
                      {extract.headers?.length > 4 && ` +${extract.headers.length - 4} more`}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Right Panel - Mapping Interface */}
        <div style={styles.mappingPanel}>
          <div style={styles.mappingHeader}>
            <div style={styles.mappingTitleRow}>
              <span style={styles.mappingTitle}>
                {sectionConfig?.icon} {sectionConfig?.label} Columns
              </span>
              <span style={{
                ...styles.sectionBadge,
                background: sectionConfig?.bgColor,
                color: sectionConfig?.color
              }}>
                {currentExtract?.row_count || 0} rows
              </span>
            </div>
          </div>

          {!currentExtract ? (
            <div style={styles.noDataMessage}>
              <p>No data detected for {sectionConfig?.label}.</p>
              <p>Select a different section or re-upload the file.</p>
            </div>
          ) : (
            <>
              <div style={styles.mappingContent}>
                {currentExtract.headers?.map((header, idx) => {
                  const columnMapping = currentMapping?.columns?.[header] || {}
                  const confidence = columnMapping.confidence || 0
                  const level = getConfidenceLevel(confidence)
                  
                  return (
                    <div 
                      key={idx} 
                      style={{
                        ...styles.mappingCard,
                        borderLeftColor: level === 'high' ? '#22c55e' : level === 'medium' ? '#f59e0b' : '#9ca3af'
                      }}
                    >
                      <div style={styles.sourceCol}>
                        <div style={styles.sourceName}>{header}</div>
                        <div style={styles.sourceSamples}>
                          {currentExtract.sample_data?.slice(0, 3).map((row, rowIdx) => (
                            <span key={rowIdx} style={styles.sample}>
                              {row[idx] || '-'}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div style={styles.arrowCol}>→</div>
                      <div style={styles.targetCol}>
                        <select
                          value={columnMapping.confirmed || 'skip'}
                          onChange={(e) => updateColumnMapping(activeSection, header, e.target.value)}
                          style={{
                            ...styles.targetSelect,
                            borderColor: level === 'high' ? '#22c55e' : level === 'medium' ? '#f59e0b' : '#e5e7eb'
                          }}
                        >
                          {TARGET_FIELDS[activeSection]?.map(field => (
                            <option key={field.value} value={field.value}>
                              {field.label}
                            </option>
                          ))}
                        </select>
                        <div 
                          style={{
                            ...styles.confidenceDot,
                            background: level === 'high' ? '#22c55e' : level === 'medium' ? '#f59e0b' : '#9ca3af'
                          }} 
                          title={`${Math.round(confidence * 100)}% confidence`}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Section Actions */}
              <div style={styles.sectionActions}>
                <button 
                  style={styles.btnSuccess}
                  onClick={() => confirmSection(activeSection)}
                >
                  ✓ Confirm {sectionConfig?.label} Mapping
                </button>
              </div>

              {/* Collapsible Preview */}
              <div 
                style={styles.previewToggle}
                onClick={() => setShowPreview(!showPreview)}
              >
                <span>{showPreview ? '▼' : '▶'}</span> Live Preview
              </div>
              
              {showPreview && currentExtract.sample_data && (
                <div style={styles.previewPanel}>
                  <table style={styles.previewTable}>
                    <thead>
                      <tr>
                        {currentExtract.headers?.map((header, idx) => {
                          const mapping = currentMapping?.columns?.[header]
                          const targetField = TARGET_FIELDS[activeSection]?.find(
                            f => f.value === (mapping?.confirmed || 'skip')
                          )
                          if (mapping?.confirmed === 'skip') return null
                          return (
                            <th key={idx} style={styles.previewTh}>
                              {targetField?.label || header}
                            </th>
                          )
                        })}
                      </tr>
                    </thead>
                    <tbody>
                      {currentExtract.sample_data?.slice(0, 5).map((row, rowIdx) => (
                        <tr key={rowIdx}>
                          {row.map((cell, cellIdx) => {
                            const header = currentExtract.headers?.[cellIdx]
                            const mapping = currentMapping?.columns?.[header]
                            if (mapping?.confirmed === 'skip') return null
                            return <td key={cellIdx} style={styles.previewTd}>{cell}</td>
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        <div style={styles.footerLeft}>
          <span style={styles.progressLabel}>Progress:</span>
          <div style={styles.sectionDots}>
            {Object.entries(SECTIONS).map(([key, config]) => (
              <div
                key={key}
                style={{
                  ...styles.sectionDot,
                  background: sectionStatus[key] === 'done' ? config.color : 
                    activeSection === key ? 'white' : '#e5e7eb',
                  borderColor: activeSection === key ? config.color : 
                    sectionStatus[key] === 'done' ? config.color : '#e5e7eb',
                  boxShadow: activeSection === key ? `0 0 0 2px ${config.color}40` : 'none'
                }}
                title={config.label}
                onClick={() => getExtractForSection(key) && setActiveSection(key)}
              />
            ))}
          </div>
          <span style={styles.progressText}>{completedSections} of 5 sections mapped</span>
        </div>
        <div style={styles.footerRight}>
          <label style={styles.rememberCheck}>
            <input type="checkbox" defaultChecked />
            Remember mapping for similar files
          </label>
        </div>
      </div>

      {/* Error Toast */}
      {error && (
        <div style={styles.errorToast}>
          {error}
          <button onClick={() => setError(null)} style={styles.errorClose}>×</button>
        </div>
      )}
    </div>
  )
}


// Styles
const styles = {
  container: {
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    background: '#f5f7fa'
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    color: '#666'
  },
  spinner: {
    width: 40,
    height: 40,
    border: '3px solid #e5e7eb',
    borderTop: '3px solid #3b82f6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginBottom: '1rem'
  },
  
  // File selection
  fileSelectContainer: {
    padding: '2rem',
    maxWidth: 1000,
    margin: '0 auto'
  },
  pageTitle: {
    fontSize: '1.75rem',
    color: '#1f2937',
    marginBottom: '0.5rem'
  },
  pageSubtitle: {
    color: '#6b7280',
    marginBottom: '2rem'
  },
  fileGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '1rem'
  },
  fileCard: {
    background: 'white',
    borderRadius: 12,
    padding: '1.25rem',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    cursor: 'pointer',
    display: 'flex',
    gap: '1rem',
    transition: 'all 0.15s',
    border: '2px solid transparent'
  },
  fileIcon: {
    fontSize: '2rem'
  },
  fileDetails: {
    flex: 1
  },
  fileName: {
    fontWeight: 600,
    color: '#1f2937',
    marginBottom: '0.25rem'
  },
  fileMeta: {
    fontSize: '0.85rem',
    color: '#6b7280',
    marginBottom: '0.5rem'
  },
  fileSections: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.5rem'
  },
  sectionTag: {
    fontSize: '0.7rem',
    padding: '2px 8px',
    borderRadius: 4,
    fontWeight: 500
  },
  emptyState: {
    textAlign: 'center',
    padding: '3rem',
    color: '#666'
  },
  
  // Header
  header: {
    background: 'white',
    padding: '1rem 1.5rem',
    borderBottom: '1px solid #e5e7eb',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '1rem',
    flexShrink: 0
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '1.5rem'
  },
  title: {
    fontSize: '1.25rem',
    color: '#1f2937',
    margin: 0
  },
  fileInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem'
  },
  fileNameHeader: {
    color: '#6b7280',
    fontSize: '0.9rem'
  },
  headerActions: {
    display: 'flex',
    gap: '0.5rem'
  },
  btnPrimary: {
    padding: '0.5rem 1rem',
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: 6,
    fontSize: '0.85rem',
    fontWeight: 500,
    cursor: 'pointer'
  },
  btnSuccess: {
    padding: '0.5rem 1rem',
    background: '#22c55e',
    color: 'white',
    border: 'none',
    borderRadius: 6,
    fontSize: '0.85rem',
    fontWeight: 500,
    cursor: 'pointer'
  },
  btnSecondary: {
    padding: '0.5rem 1rem',
    background: '#f3f4f6',
    color: '#374151',
    border: '1px solid #e5e7eb',
    borderRadius: 6,
    fontSize: '0.85rem',
    cursor: 'pointer'
  },
  
  // Main split
  mainSplit: {
    flex: 1,
    display: 'flex',
    overflow: 'hidden'
  },
  
  // Doc panel (left)
  docPanel: {
    width: '320px',
    background: 'white',
    borderRight: '1px solid #e5e7eb',
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0
  },
  docHeader: {
    padding: '0.75rem 1rem',
    borderBottom: '1px solid #e5e7eb'
  },
  docTitle: {
    fontWeight: 600,
    fontSize: '0.9rem',
    color: '#374151'
  },
  
  // Metadata section
  metadataSection: {
    padding: '1rem',
    borderBottom: '1px solid #e5e7eb',
    background: '#f9fafb'
  },
  metadataTitle: {
    fontSize: '0.8rem',
    fontWeight: 600,
    color: '#374151',
    marginBottom: '0.75rem'
  },
  metadataGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '0.75rem'
  },
  metadataField: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem'
  },
  metadataInput: {
    padding: '0.4rem 0.5rem',
    border: '1px solid #e5e7eb',
    borderRadius: 4,
    fontSize: '0.8rem'
  },
  
  // Section list
  sectionList: {
    flex: 1,
    overflow: 'auto',
    padding: '0.75rem'
  },
  sectionCard: {
    padding: '0.75rem',
    borderRadius: 8,
    marginBottom: '0.5rem',
    border: '2px solid #e5e7eb',
    cursor: 'pointer',
    transition: 'all 0.15s'
  },
  sectionCardDone: {
    background: '#f0fdf4',
    borderColor: '#86efac'
  },
  sectionCardEmpty: {
    opacity: 0.5,
    cursor: 'default'
  },
  sectionCardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '0.25rem'
  },
  sectionIcon: {
    fontSize: '1rem'
  },
  sectionLabel: {
    fontWeight: 600,
    fontSize: '0.9rem',
    color: '#1f2937',
    flex: 1
  },
  checkMark: {
    color: '#22c55e',
    fontWeight: 'bold'
  },
  sectionCardMeta: {
    fontSize: '0.75rem',
    color: '#6b7280',
    marginBottom: '0.25rem'
  },
  sectionCardHeaders: {
    fontSize: '0.7rem',
    color: '#9ca3af',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },
  
  // Mapping panel (right)
  mappingPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden'
  },
  mappingHeader: {
    padding: '0.75rem 1rem',
    background: 'white',
    borderBottom: '1px solid #e5e7eb'
  },
  mappingTitleRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between'
  },
  mappingTitle: {
    fontWeight: 600,
    fontSize: '1rem',
    color: '#1f2937'
  },
  sectionBadge: {
    padding: '4px 10px',
    borderRadius: 6,
    fontSize: '0.75rem',
    fontWeight: 500
  },
  noDataMessage: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#6b7280',
    padding: '2rem'
  },
  
  // Mapping content
  mappingContent: {
    flex: 1,
    overflow: 'auto',
    padding: '1rem',
    background: '#f9fafb'
  },
  mappingCard: {
    background: 'white',
    borderRadius: 8,
    padding: '0.875rem',
    marginBottom: '0.75rem',
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
    borderLeft: '3px solid #ccc',
    display: 'grid',
    gridTemplateColumns: '1fr auto 1fr',
    alignItems: 'center',
    gap: '1rem'
  },
  sourceCol: {},
  sourceName: {
    fontWeight: 600,
    fontSize: '0.9rem',
    color: '#1f2937',
    marginBottom: '0.25rem'
  },
  sourceSamples: {
    display: 'flex',
    gap: '0.5rem',
    flexWrap: 'wrap'
  },
  sample: {
    fontSize: '0.7rem',
    background: '#f3f4f6',
    padding: '2px 6px',
    borderRadius: 3,
    fontFamily: 'monospace',
    color: '#4b5563'
  },
  arrowCol: {
    color: '#9ca3af',
    fontSize: '1.25rem'
  },
  targetCol: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem'
  },
  targetSelect: {
    flex: 1,
    padding: '0.5rem',
    fontSize: '0.85rem',
    border: '2px solid #e5e7eb',
    borderRadius: 6,
    background: 'white'
  },
  confidenceDot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    flexShrink: 0
  },
  
  // Section actions
  sectionActions: {
    padding: '0.75rem 1rem',
    background: 'white',
    borderTop: '1px solid #e5e7eb',
    display: 'flex',
    justifyContent: 'flex-end'
  },
  
  // Preview
  previewToggle: {
    padding: '0.5rem 1rem',
    background: '#e5e7eb',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.8rem',
    color: '#6b7280'
  },
  previewPanel: {
    maxHeight: 200,
    overflow: 'auto',
    background: 'white'
  },
  previewTable: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.8rem'
  },
  previewTh: {
    background: '#f9fafb',
    padding: '0.5rem 0.75rem',
    textAlign: 'left',
    fontWeight: 600,
    color: '#374151',
    borderBottom: '2px solid #e5e7eb',
    position: 'sticky',
    top: 0
  },
  previewTd: {
    padding: '0.5rem 0.75rem',
    borderBottom: '1px solid #f3f4f6',
    color: '#4b5563'
  },
  
  // Footer
  footer: {
    background: 'white',
    padding: '0.75rem 1.5rem',
    borderTop: '1px solid #e5e7eb',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexShrink: 0
  },
  footerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem'
  },
  progressLabel: {
    fontSize: '0.85rem',
    color: '#6b7280'
  },
  sectionDots: {
    display: 'flex',
    gap: '0.5rem'
  },
  sectionDot: {
    width: 14,
    height: 14,
    borderRadius: '50%',
    border: '2px solid #e5e7eb',
    cursor: 'pointer',
    transition: 'all 0.15s'
  },
  progressText: {
    fontSize: '0.8rem',
    color: '#9ca3af'
  },
  footerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem'
  },
  rememberCheck: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.85rem',
    color: '#6b7280',
    cursor: 'pointer'
  },
  
  // Error toast
  errorToast: {
    position: 'fixed',
    bottom: 20,
    right: 20,
    background: '#ef4444',
    color: 'white',
    padding: '1rem 1.5rem',
    borderRadius: 8,
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
    display: 'flex',
    alignItems: 'center',
    gap: '1rem'
  },
  errorClose: {
    background: 'none',
    border: 'none',
    color: 'white',
    fontSize: '1.25rem',
    cursor: 'pointer'
  }
}
