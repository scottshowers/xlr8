import { useState, useEffect, useRef } from 'react'

/**
 * Vacuum Upload Page
 * 
 * Extract EVERYTHING from complex files (PDFs, Excel)
 * Parse now, understand later, learn forever.
 * 
 * Separate from normal uploads - for complex payroll vendor files
 */
export default function VacuumUploadPage() {
  const [currentSection, setCurrentSection] = useState('upload')

  return (
    <div style={styles.container}>
      {/* Sidebar Navigation */}
      <div style={styles.sidebar}>
        <div style={styles.sidebarHeader}>
          <h2 style={styles.sidebarTitle}>🧹 Vacuum Extract</h2>
        </div>

        <nav style={styles.nav}>
          <button
            onClick={() => setCurrentSection('upload')}
            style={{
              ...styles.navItem,
              ...(currentSection === 'upload' ? styles.navItemActive : {})
            }}
          >
            📤 Upload & Extract
          </button>

          <button
            onClick={() => setCurrentSection('explore')}
            style={{
              ...styles.navItem,
              ...(currentSection === 'explore' ? styles.navItemActive : {})
            }}
          >
            🔍 Explore Data
          </button>

          <button
            onClick={() => setCurrentSection('map')}
            style={{
              ...styles.navItem,
              ...(currentSection === 'map' ? styles.navItemActive : {})
            }}
          >
            🗺️ Map Columns
          </button>

          <button
            onClick={() => setCurrentSection('learn')}
            style={{
              ...styles.navItem,
              ...(currentSection === 'learn' ? styles.navItemActive : {})
            }}
          >
            🧠 Learned Mappings
          </button>

          <div style={styles.navDivider} />
          
          <div style={styles.navPlaceholder}>
            💡 Extract → Explore → Map → Done
          </div>
        </nav>
      </div>

      {/* Main Content Area */}
      <div style={styles.mainContent}>
        {currentSection === 'upload' && <UploadSection />}
        {currentSection === 'explore' && <ExploreSection />}
        {currentSection === 'map' && <MapSection />}
        {currentSection === 'learn' && <LearnSection />}
      </div>
    </div>
  )
}


// ============================================================================
// UPLOAD SECTION
// ============================================================================
function UploadSection() {
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [project, setProject] = useState('')
  const fileInputRef = useRef(null)

  const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app'

  const handleDrop = async (e) => {
    e.preventDefault()
    setDragOver(false)
    
    const files = e.dataTransfer?.files
    if (files?.length) {
      await uploadFile(files[0])
    }
  }

  const handleFileSelect = async (e) => {
    const files = e.target.files
    if (files?.length) {
      await uploadFile(files[0])
    }
  }

  const uploadFile = async (file) => {
    setUploading(true)
    setResult(null)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)
    if (project) {
      formData.append('project', project)
    }

    try {
      const res = await fetch(`${API_BASE}/api/vacuum/upload`, {
        method: 'POST',
        body: formData
      })

      const data = await res.json()

      if (res.ok) {
        setResult(data)
      } else {
        setError(data.detail || 'Upload failed')
      }
    } catch (err) {
      setError('Upload failed: ' + err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={styles.section}>
      <h1 style={styles.sectionTitle}>📤 Vacuum Upload</h1>
      <p style={styles.sectionSubtitle}>
        Extract ALL data from complex files. Parse now, understand later.
      </p>

      {/* Project Input */}
      <div style={styles.formGroup}>
        <label style={styles.label}>Project (optional)</label>
        <input
          type="text"
          value={project}
          onChange={(e) => setProject(e.target.value)}
          placeholder="e.g., ADP Migration, Paychex Conversion"
          style={styles.input}
        />
      </div>

      {/* Drop Zone */}
      <div
        style={{
          ...styles.dropZone,
          ...(dragOver ? styles.dropZoneActive : {}),
          ...(uploading ? styles.dropZoneUploading : {})
        }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.xlsx,.xls,.csv"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        
        {uploading ? (
          <>
            <div style={styles.spinner}></div>
            <p style={styles.dropText}>Extracting all data...</p>
          </>
        ) : (
          <>
            <span style={styles.dropIcon}>🧹</span>
            <p style={styles.dropText}>
              Drop PDF, Excel, or CSV here
            </p>
            <p style={styles.dropSubtext}>
              or click to browse
            </p>
          </>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div style={styles.errorBox}>
          ❌ {error}
        </div>
      )}

      {/* Success Result */}
      {result && (
        <div style={styles.resultBox}>
          <h3 style={styles.resultTitle}>✅ Extraction Complete!</h3>
          
          <div style={styles.resultStats}>
            <div style={styles.statItem}>
              <span style={styles.statValue}>{result.tables_found}</span>
              <span style={styles.statLabel}>Tables Found</span>
            </div>
            <div style={styles.statItem}>
              <span style={styles.statValue}>{result.total_rows?.toLocaleString()}</span>
              <span style={styles.statLabel}>Total Rows</span>
            </div>
          </div>

          {result.extracts?.length > 0 && (
            <div style={styles.extractsList}>
              <h4 style={styles.extractsTitle}>Extracted Tables:</h4>
              {result.extracts.map((ext, idx) => (
                <div key={idx} style={styles.extractItem}>
                  <div style={styles.extractHeader}>
                    <span style={styles.extractName}>
                      {ext.sheet_name || `Table ${ext.table_index + 1}`}
                    </span>
                    <span style={styles.extractMeta}>
                      Page {ext.page + 1} • {ext.row_count} rows • {ext.column_count} cols
                    </span>
                  </div>
                  <div style={styles.extractColumns}>
                    {ext.headers?.slice(0, 6).map((h, i) => (
                      <span key={i} style={styles.columnTag}>{h}</span>
                    ))}
                    {ext.headers?.length > 6 && (
                      <span style={styles.columnMore}>+{ext.headers.length - 6} more</span>
                    )}
                  </div>
                  <div style={styles.confidenceBar}>
                    <div 
                      style={{
                        ...styles.confidenceFill,
                        width: `${(ext.confidence || 0) * 100}%`,
                        background: ext.confidence > 0.7 ? '#22c55e' : ext.confidence > 0.4 ? '#f59e0b' : '#ef4444'
                      }}
                    />
                  </div>
                  <span style={styles.confidenceLabel}>
                    {Math.round((ext.confidence || 0) * 100)}% header confidence
                  </span>
                </div>
              ))}
            </div>
          )}

          <p style={styles.nextStep}>
            👉 Go to <strong>Explore Data</strong> to view and map columns
          </p>
        </div>
      )}

      {/* Info Box */}
      <div style={styles.infoBox}>
        <strong>🧹 How Vacuum Extract Works:</strong>
        <ol style={styles.infoList}>
          <li><strong>Upload</strong> - Drop any PDF, Excel, or CSV file</li>
          <li><strong>Extract</strong> - We find ALL tables, no interpretation</li>
          <li><strong>Explore</strong> - Browse what we found, preview data</li>
          <li><strong>Map</strong> - You tell us what each column means</li>
          <li><strong>Learn</strong> - We remember for next time</li>
        </ol>
        <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#666' }}>
          💡 Supported formats: PDF (native tables), Excel (.xlsx, .xls), CSV
        </p>
      </div>
    </div>
  )
}


// ============================================================================
// EXPLORE SECTION
// ============================================================================
function ExploreSection() {
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedFile, setSelectedFile] = useState(null)
  const [extracts, setExtracts] = useState([])
  const [selectedExtract, setSelectedExtract] = useState(null)
  const [extractDetail, setExtractDetail] = useState(null)

  const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app'

  useEffect(() => {
    fetchFiles()
  }, [])

  const fetchFiles = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/files`)
      const data = await res.json()
      setFiles(data.files || [])
    } catch (err) {
      console.error('Failed to fetch files:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchExtracts = async (sourceFile) => {
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/extracts?source_file=${encodeURIComponent(sourceFile)}`)
      const data = await res.json()
      setExtracts(data.extracts || [])
    } catch (err) {
      console.error('Failed to fetch extracts:', err)
    }
  }

  const fetchExtractDetail = async (extractId) => {
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/extract/${extractId}`)
      const data = await res.json()
      setExtractDetail(data)
    } catch (err) {
      console.error('Failed to fetch extract detail:', err)
    }
  }

  const handleFileSelect = (file) => {
    setSelectedFile(file)
    setSelectedExtract(null)
    setExtractDetail(null)
    fetchExtracts(file.source_file)
  }

  const handleExtractSelect = (extract) => {
    setSelectedExtract(extract)
    fetchExtractDetail(extract.id)
  }

  const handleDelete = async (sourceFile) => {
    if (!confirm(`Delete all extracts for "${sourceFile}"?`)) return
    
    try {
      await fetch(`${API_BASE}/api/vacuum/file/${encodeURIComponent(sourceFile)}`, {
        method: 'DELETE'
      })
      fetchFiles()
      setSelectedFile(null)
      setExtracts([])
    } catch (err) {
      alert('Delete failed')
    }
  }

  return (
    <div style={styles.section}>
      <h1 style={styles.sectionTitle}>🔍 Explore Extracted Data</h1>
      <p style={styles.sectionSubtitle}>
        Browse files and tables extracted by vacuum upload
      </p>

      {loading ? (
        <div style={styles.loadingBox}>
          <div style={styles.spinner}></div>
          <p>Loading...</p>
        </div>
      ) : files.length === 0 ? (
        <div style={styles.emptyState}>
          <span style={{ fontSize: '4rem' }}>🧹</span>
          <p>No files extracted yet</p>
          <p style={{ fontSize: '0.9rem', color: '#999' }}>
            Go to Upload & Extract to add files
          </p>
        </div>
      ) : (
        <div style={styles.exploreGrid}>
          {/* Files List */}
          <div style={styles.filesList}>
            <h3 style={styles.panelTitle}>Files ({files.length})</h3>
            {files.map((file, idx) => (
              <div
                key={idx}
                style={{
                  ...styles.fileItem,
                  ...(selectedFile?.source_file === file.source_file ? styles.fileItemActive : {})
                }}
                onClick={() => handleFileSelect(file)}
              >
                <div style={styles.fileIcon}>
                  {file.file_type === 'pdf' ? '📄' : '📊'}
                </div>
                <div style={styles.fileInfo}>
                  <div style={styles.fileName}>{file.source_file}</div>
                  <div style={styles.fileMeta}>
                    {file.table_count} tables • {file.total_rows?.toLocaleString()} rows
                  </div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(file.source_file) }}
                  style={styles.deleteBtn}
                  title="Delete"
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>

          {/* Extracts List */}
          <div style={styles.extractsPanel}>
            <h3 style={styles.panelTitle}>
              {selectedFile ? `Tables in ${selectedFile.source_file}` : 'Select a file'}
            </h3>
            {extracts.length === 0 ? (
              <p style={styles.placeholder}>Select a file to see tables</p>
            ) : (
              extracts.map((ext, idx) => (
                <div
                  key={idx}
                  style={{
                    ...styles.extractCard,
                    ...(selectedExtract?.id === ext.id ? styles.extractCardActive : {})
                  }}
                  onClick={() => handleExtractSelect(ext)}
                >
                  <div style={styles.extractCardHeader}>
                    <strong>Table {ext.table_index + 1}</strong>
                    <span>Page {ext.page_num + 1}</span>
                  </div>
                  <div style={styles.extractCardMeta}>
                    {ext.row_count} rows • {ext.column_count} columns
                  </div>
                  <div style={styles.extractCardHeaders}>
                    {ext.raw_headers?.slice(0, 4).join(', ')}
                    {ext.raw_headers?.length > 4 && '...'}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Data Preview */}
          <div style={styles.previewPanel}>
            <h3 style={styles.panelTitle}>
              {extractDetail ? 'Data Preview' : 'Select a table'}
            </h3>
            {!extractDetail ? (
              <p style={styles.placeholder}>Select a table to preview data</p>
            ) : (
              <div style={styles.previewContent}>
                <div style={styles.previewMeta}>
                  <span>Showing {extractDetail.preview?.length || 0} of {extractDetail.row_count} rows</span>
                  <span style={{
                    color: extractDetail.confidence > 0.7 ? '#22c55e' : '#f59e0b'
                  }}>
                    {Math.round((extractDetail.confidence || 0) * 100)}% confidence
                  </span>
                </div>
                <div style={styles.tableWrapper}>
                  <table style={styles.dataTable}>
                    <thead>
                      <tr>
                        {extractDetail.raw_headers?.map((h, i) => (
                          <th key={i} style={styles.dataTableTh}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {extractDetail.preview?.map((row, rowIdx) => (
                        <tr key={rowIdx}>
                          {row.map((cell, cellIdx) => (
                            <td key={cellIdx} style={styles.dataTableTd}>{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}


// ============================================================================
// MAP SECTION (Placeholder - full implementation would be larger)
// ============================================================================
function MapSection() {
  return (
    <div style={styles.section}>
      <h1 style={styles.sectionTitle}>🗺️ Map Columns</h1>
      <p style={styles.sectionSubtitle}>
        Define what each column means and create structured tables
      </p>

      <div style={styles.card}>
        <h3 style={styles.cardTitle}>🚧 Coming Soon</h3>
        <p style={styles.cardText}>
          The column mapping interface will allow you to:
        </p>
        <ul style={styles.featureList}>
          <li>Select an extracted table</li>
          <li>Map each column to a standard field (employee_id, hire_date, etc.)</li>
          <li>Get AI suggestions based on column names</li>
          <li>Create a clean, structured table in DuckDB</li>
          <li>Apply same mapping to similar files automatically</li>
        </ul>
        <p style={{ marginTop: '1rem', color: '#666' }}>
          For now, use the Explore section to preview your data.
        </p>
      </div>
    </div>
  )
}


// ============================================================================
// LEARN SECTION (Placeholder)
// ============================================================================
function LearnSection() {
  return (
    <div style={styles.section}>
      <h1 style={styles.sectionTitle}>🧠 Learned Mappings</h1>
      <p style={styles.sectionSubtitle}>
        View and manage column mappings the system has learned
      </p>

      <div style={styles.card}>
        <h3 style={styles.cardTitle}>🚧 Coming Soon</h3>
        <p style={styles.cardText}>
          The learning system will:
        </p>
        <ul style={styles.featureList}>
          <li>Remember your column mappings</li>
          <li>Recognize vendor-specific formats (ADP, Paychex, etc.)</li>
          <li>Auto-suggest mappings for new files</li>
          <li>Improve accuracy over time</li>
          <li>Export/import mapping templates</li>
        </ul>
      </div>
    </div>
  )
}


// ============================================================================
// STYLES
// ============================================================================
const styles = {
  // Layout
  container: {
    display: 'flex',
    minHeight: '100vh',
    background: '#f5f7fa'
  },
  sidebar: {
    width: '280px',
    background: '#c9d3d4',
    color: '#2a3441',
    display: 'flex',
    flexDirection: 'column'
  },
  sidebarHeader: {
    padding: '1.5rem',
    borderBottom: '1px solid rgba(42, 52, 65, 0.15)'
  },
  sidebarTitle: {
    margin: 0,
    fontSize: '1.5rem',
    fontWeight: '600'
  },
  nav: {
    padding: '1rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem'
  },
  navItem: {
    padding: '0.75rem 1rem',
    fontSize: '0.95rem',
    background: 'transparent',
    color: 'rgba(42, 52, 65, 0.7)',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'all 0.2s'
  },
  navItemActive: {
    background: 'rgba(131, 177, 109, 0.3)',
    color: '#2a3441',
    fontWeight: '600'
  },
  navDivider: {
    height: '1px',
    background: 'rgba(42, 52, 65, 0.15)',
    margin: '1rem 0'
  },
  navPlaceholder: {
    padding: '0.75rem 1rem',
    fontSize: '0.85rem',
    color: 'rgba(42, 52, 65, 0.5)',
    fontStyle: 'italic'
  },
  mainContent: {
    flex: 1,
    overflow: 'auto'
  },
  section: {
    padding: '2rem',
    maxWidth: '1400px',
    margin: '0 auto'
  },
  sectionTitle: {
    margin: '0 0 0.5rem 0',
    fontSize: '2rem',
    color: '#2a3441'
  },
  sectionSubtitle: {
    margin: '0 0 2rem 0',
    fontSize: '1rem',
    color: '#666'
  },

  // Form
  formGroup: {
    marginBottom: '1.5rem'
  },
  label: {
    display: 'block',
    marginBottom: '0.5rem',
    fontWeight: '500',
    color: '#333'
  },
  input: {
    width: '100%',
    maxWidth: '400px',
    padding: '0.75rem 1rem',
    fontSize: '1rem',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    outline: 'none'
  },

  // Drop Zone
  dropZone: {
    border: '3px dashed #ccc',
    borderRadius: '16px',
    padding: '3rem',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    background: '#fafafa',
    marginBottom: '2rem'
  },
  dropZoneActive: {
    borderColor: '#3b82f6',
    background: '#eff6ff'
  },
  dropZoneUploading: {
    borderColor: '#22c55e',
    background: '#f0fdf4',
    cursor: 'wait'
  },
  dropIcon: {
    fontSize: '4rem',
    display: 'block',
    marginBottom: '1rem'
  },
  dropText: {
    fontSize: '1.25rem',
    color: '#333',
    margin: '0 0 0.5rem 0'
  },
  dropSubtext: {
    fontSize: '0.9rem',
    color: '#999',
    margin: 0
  },

  // Results
  errorBox: {
    padding: '1rem',
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    color: '#b91c1c',
    marginBottom: '1rem'
  },
  resultBox: {
    padding: '1.5rem',
    background: 'white',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    marginBottom: '2rem'
  },
  resultTitle: {
    margin: '0 0 1rem 0',
    color: '#166534'
  },
  resultStats: {
    display: 'flex',
    gap: '2rem',
    marginBottom: '1.5rem'
  },
  statItem: {
    display: 'flex',
    flexDirection: 'column'
  },
  statValue: {
    fontSize: '2rem',
    fontWeight: '700',
    color: '#2a3441'
  },
  statLabel: {
    fontSize: '0.85rem',
    color: '#666'
  },
  extractsList: {
    borderTop: '1px solid #eee',
    paddingTop: '1rem'
  },
  extractsTitle: {
    margin: '0 0 1rem 0',
    fontSize: '1rem',
    color: '#333'
  },
  extractItem: {
    padding: '1rem',
    background: '#f9fafb',
    borderRadius: '8px',
    marginBottom: '0.75rem'
  },
  extractHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '0.5rem'
  },
  extractName: {
    fontWeight: '600',
    color: '#333'
  },
  extractMeta: {
    fontSize: '0.85rem',
    color: '#666'
  },
  extractColumns: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.5rem',
    marginBottom: '0.5rem'
  },
  columnTag: {
    padding: '0.25rem 0.5rem',
    background: '#dbeafe',
    color: '#1e40af',
    borderRadius: '4px',
    fontSize: '0.75rem'
  },
  columnMore: {
    padding: '0.25rem 0.5rem',
    color: '#999',
    fontSize: '0.75rem'
  },
  confidenceBar: {
    height: '4px',
    background: '#e5e7eb',
    borderRadius: '2px',
    overflow: 'hidden',
    marginBottom: '0.25rem'
  },
  confidenceFill: {
    height: '100%',
    transition: 'width 0.3s'
  },
  confidenceLabel: {
    fontSize: '0.75rem',
    color: '#999'
  },
  nextStep: {
    marginTop: '1rem',
    padding: '1rem',
    background: '#eff6ff',
    borderRadius: '8px',
    color: '#1e40af'
  },

  // Info Box
  infoBox: {
    padding: '1.5rem',
    background: '#f0f9ff',
    borderRadius: '8px',
    border: '1px solid #bae6fd',
    color: '#0c4a6e'
  },
  infoList: {
    margin: '0.75rem 0 0 1.25rem',
    padding: 0,
    lineHeight: 1.8
  },

  // Explore Grid
  exploreGrid: {
    display: 'grid',
    gridTemplateColumns: '280px 300px 1fr',
    gap: '1.5rem',
    minHeight: '600px'
  },
  filesList: {
    background: 'white',
    borderRadius: '12px',
    padding: '1rem',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
  },
  extractsPanel: {
    background: 'white',
    borderRadius: '12px',
    padding: '1rem',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
  },
  previewPanel: {
    background: 'white',
    borderRadius: '12px',
    padding: '1rem',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    overflow: 'hidden'
  },
  panelTitle: {
    margin: '0 0 1rem 0',
    fontSize: '1rem',
    color: '#333',
    paddingBottom: '0.75rem',
    borderBottom: '1px solid #eee'
  },
  fileItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.75rem',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background 0.15s',
    marginBottom: '0.5rem'
  },
  fileItemActive: {
    background: 'rgba(59, 130, 246, 0.1)'
  },
  fileIcon: {
    fontSize: '1.5rem'
  },
  fileInfo: {
    flex: 1,
    minWidth: 0
  },
  fileName: {
    fontWeight: '500',
    fontSize: '0.9rem',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
  },
  fileMeta: {
    fontSize: '0.75rem',
    color: '#999'
  },
  deleteBtn: {
    padding: '0.4rem',
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    opacity: 0.5,
    transition: 'opacity 0.15s'
  },
  extractCard: {
    padding: '0.75rem',
    background: '#f9fafb',
    borderRadius: '8px',
    marginBottom: '0.5rem',
    cursor: 'pointer',
    border: '2px solid transparent',
    transition: 'all 0.15s'
  },
  extractCardActive: {
    borderColor: '#3b82f6',
    background: '#eff6ff'
  },
  extractCardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.9rem',
    marginBottom: '0.25rem'
  },
  extractCardMeta: {
    fontSize: '0.75rem',
    color: '#999',
    marginBottom: '0.25rem'
  },
  extractCardHeaders: {
    fontSize: '0.75rem',
    color: '#666',
    fontStyle: 'italic'
  },
  placeholder: {
    color: '#999',
    textAlign: 'center',
    padding: '2rem'
  },
  previewContent: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column'
  },
  previewMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.85rem',
    color: '#666',
    marginBottom: '0.75rem'
  },
  tableWrapper: {
    flex: 1,
    overflow: 'auto'
  },
  dataTable: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.8rem'
  },
  dataTableTh: {
    padding: '0.5rem',
    background: '#f3f4f6',
    borderBottom: '2px solid #e5e7eb',
    textAlign: 'left',
    fontWeight: '600',
    whiteSpace: 'nowrap'
  },
  dataTableTd: {
    padding: '0.5rem',
    borderBottom: '1px solid #f0f0f0',
    maxWidth: '200px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },

  // Common
  loadingBox: {
    textAlign: 'center',
    padding: '3rem',
    color: '#666'
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '3px solid #e5e7eb',
    borderTop: '3px solid #3b82f6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 1rem'
  },
  emptyState: {
    textAlign: 'center',
    padding: '4rem 2rem',
    color: '#666'
  },
  card: {
    background: 'white',
    borderRadius: '12px',
    padding: '2rem',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
  },
  cardTitle: {
    margin: '0 0 1rem 0',
    fontSize: '1.25rem',
    color: '#2a3441'
  },
  cardText: {
    margin: '0 0 1rem 0',
    color: '#666',
    lineHeight: 1.6
  },
  featureList: {
    margin: 0,
    paddingLeft: '1.5rem',
    color: '#666',
    lineHeight: 2
  }
}
