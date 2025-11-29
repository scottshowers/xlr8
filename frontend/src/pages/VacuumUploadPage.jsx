import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

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
  const navigate = useNavigate()

  const handleNavClick = (section) => {
    if (section === 'explore') {
      navigate('/vacuum/explore')
    } else {
      setCurrentSection(section)
    }
  }

  return (
    <div style={styles.container}>
      {/* Sidebar Navigation */}
      <div style={styles.sidebar}>
        <div style={styles.sidebarHeader}>
          <h2 style={styles.sidebarTitle}>🧹 Vacuum Extract</h2>
        </div>

        <nav style={styles.nav}>
          <button
            onClick={() => handleNavClick('upload')}
            style={{
              ...styles.navItem,
              ...(currentSection === 'upload' ? styles.navItemActive : {})
            }}
          >
            📤 Upload & Extract
          </button>

          <button
            onClick={() => handleNavClick('explore')}
            style={styles.navItem}
          >
            🔍 Explore Data
            <span style={styles.navBadge}>NEW</span>
          </button>

          <button
            onClick={() => handleNavClick('map')}
            style={{
              ...styles.navItem,
              ...(currentSection === 'map' ? styles.navItemActive : {})
            }}
          >
            🗺️ Map Columns
          </button>

          <button
            onClick={() => handleNavClick('learn')}
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
        {currentSection === 'upload' && <UploadSection onExplore={() => handleNavClick('explore')} />}
        {currentSection === 'map' && <MapSection />}
        {currentSection === 'learn' && <LearnSection />}
      </div>
    </div>
  )
}


// ============================================================================
// UPLOAD SECTION
// ============================================================================
function UploadSection({ onExplore }) {
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [project, setProject] = useState('')
  const [status, setStatus] = useState(null)
  const fileInputRef = useRef(null)

  const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app'

  useEffect(() => {
    checkStatus()
  }, [])

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/status`)
      const data = await res.json()
      setStatus(data)
    } catch (err) {
      setStatus({ available: false, error: err.message })
    }
  }

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

      {status && !status.available && (
        <div style={styles.errorBox}>
          ❌ Vacuum extractor not available
        </div>
      )}

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
            <p style={styles.dropText}>Drop PDF, Excel, or CSV here</p>
            <p style={styles.dropSubtext}>or click to browse</p>
          </>
        )}
      </div>

      {error && (
        <div style={styles.errorBox}>❌ {error}</div>
      )}

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
            {result.detected_report_type && (
              <div style={styles.statItem}>
                <span style={{...styles.statValue, fontSize: '1.2rem'}}>
                  {result.detected_report_type.replace('_', ' ')}
                </span>
                <span style={styles.statLabel}>Detected Type</span>
              </div>
            )}
          </div>

          {result.extracts?.length > 0 && (
            <div style={styles.extractsList}>
              <h4 style={styles.extractsTitle}>Extracted Tables:</h4>
              {result.extracts.map((ext, idx) => (
                <div key={idx} style={styles.extractItem}>
                  <div style={styles.extractHeader}>
                    <span style={styles.extractName}>
                      {ext.detected_section ? (
                        <span style={{
                          ...styles.sectionBadge,
                          background: getSectionColor(ext.detected_section)
                        }}>
                          {getSectionIcon(ext.detected_section)} {formatSectionName(ext.detected_section)}
                        </span>
                      ) : (
                        ext.sheet_name || `Table ${ext.table_index + 1}`
                      )}
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
                        width: `${(ext.section_confidence || ext.confidence || 0) * 100}%`,
                        background: (ext.section_confidence || ext.confidence) > 0.7 ? '#22c55e' 
                          : (ext.section_confidence || ext.confidence) > 0.4 ? '#f59e0b' : '#ef4444'
                      }}
                    />
                  </div>
                  <span style={styles.confidenceLabel}>
                    {Math.round((ext.section_confidence || ext.confidence || 0) * 100)}% detection confidence
                  </span>
                </div>
              ))}
            </div>
          )}

          <button style={styles.exploreButton} onClick={onExplore}>
            🔍 Go to Explore Data →
          </button>
        </div>
      )}

      <div style={styles.infoBox}>
        <strong>🧹 How Vacuum Extract Works:</strong>
        <ol style={styles.infoList}>
          <li><strong>Upload</strong> - Drop any PDF, Excel, or CSV file</li>
          <li><strong>Extract</strong> - We find ALL tables with intelligent section detection</li>
          <li><strong>Explore</strong> - Review detected sections (Earnings, Taxes, Deductions)</li>
          <li><strong>Confirm/Correct</strong> - Teach the system when it's wrong</li>
          <li><strong>Learn</strong> - System remembers for next time</li>
        </ol>
        <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#666' }}>
          💡 Supported formats: PDF (native tables), Excel (.xlsx, .xls), CSV
        </p>
      </div>
    </div>
  )
}

function getSectionColor(section) {
  const colors = {
    employee_info: '#3b82f6',
    earnings: '#22c55e',
    taxes: '#ef4444',
    deductions: '#f59e0b',
    pay_info: '#8b5cf6',
    unknown: '#6b7280'
  }
  return colors[section] || colors.unknown
}

function getSectionIcon(section) {
  const icons = {
    employee_info: '👤',
    earnings: '💰',
    taxes: '🏛️',
    deductions: '📋',
    pay_info: '💵',
    unknown: '❓'
  }
  return icons[section] || icons.unknown
}

function formatSectionName(section) {
  const names = {
    employee_info: 'Employee Info',
    earnings: 'Earnings',
    taxes: 'Taxes',
    deductions: 'Deductions',
    pay_info: 'Pay Info',
    unknown: 'Unknown'
  }
  return names[section] || section
}


// ============================================================================
// MAP SECTION
// ============================================================================
function MapSection() {
  const navigate = useNavigate()
  
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
        <p style={{ ...styles.cardText, marginTop: '1rem' }}>
          For now, use <strong>Explore Data</strong> to review and confirm detections.
        </p>
        <button style={styles.exploreButton} onClick={() => navigate('/vacuum/explore')}>
          🔍 Go to Explore Data →
        </button>
      </div>
    </div>
  )
}


// ============================================================================
// LEARN SECTION
// ============================================================================
function LearnSection() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  
  const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app'

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/learning-stats`)
      const data = await res.json()
      if (data.success) {
        setStats(data.stats)
      }
    } catch (err) {
      console.error('Failed to fetch learning stats:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.section}>
      <h1 style={styles.sectionTitle}>🧠 Learned Mappings</h1>
      <p style={styles.sectionSubtitle}>
        View what the system has learned from your confirmations
      </p>

      {loading ? (
        <div style={styles.loadingBox}>
          <div style={styles.spinner}></div>
          Loading...
        </div>
      ) : stats ? (
        <div style={styles.statsGrid}>
          <div style={styles.statCard}>
            <div style={styles.statCardValue}>{stats.section_patterns || 0}</div>
            <div style={styles.statCardLabel}>Section Patterns</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.statCardValue}>{stats.column_patterns || 0}</div>
            <div style={styles.statCardLabel}>Column Patterns</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.statCardValue}>{stats.vendor_signatures || 0}</div>
            <div style={styles.statCardLabel}>Vendor Signatures</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.statCardValue}>{stats.confirmed_mappings || 0}</div>
            <div style={styles.statCardLabel}>Confirmed Mappings</div>
          </div>
        </div>
      ) : (
        <div style={styles.card}>
          <p style={styles.cardText}>
            No learning data yet. Upload files and confirm detections to start teaching the system.
          </p>
        </div>
      )}

      {stats?.top_mappings?.length > 0 && (
        <div style={{ ...styles.card, marginTop: '1.5rem' }}>
          <h3 style={styles.cardTitle}>Top Confirmed Mappings</h3>
          <table style={styles.mappingsTable}>
            <thead>
              <tr>
                <th style={styles.mappingsTh}>Source Header</th>
                <th style={styles.mappingsTh}>Maps To</th>
                <th style={styles.mappingsTh}>Times Used</th>
              </tr>
            </thead>
            <tbody>
              {stats.top_mappings.map((m, i) => (
                <tr key={i}>
                  <td style={styles.mappingsTd}>{m.source_header}</td>
                  <td style={styles.mappingsTd}>
                    <span style={styles.mappingType}>{m.target_column_type}</span>
                  </td>
                  <td style={styles.mappingsTd}>{m.times_used}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}


// ============================================================================
// STYLES
// ============================================================================
const styles = {
  container: {
    display: 'flex',
    minHeight: '100%',
    background: '#f5f7fa'
  },
  sidebar: {
    width: '260px',
    background: 'linear-gradient(180deg, #e8f0e8 0%, #d4e4d4 100%)',
    borderRight: '1px solid #c5d5c5',
    flexShrink: 0
  },
  sidebarHeader: {
    padding: '1.5rem',
    borderBottom: '1px solid #c5d5c5'
  },
  sidebarTitle: {
    margin: 0,
    fontSize: '1.25rem',
    color: '#2d4a2d'
  },
  nav: {
    padding: '1rem'
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    width: '100%',
    padding: '0.75rem 1rem',
    border: 'none',
    background: 'transparent',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '0.95rem',
    color: '#2d4a2d',
    textAlign: 'left',
    transition: 'all 0.15s',
    marginBottom: '0.25rem'
  },
  navItemActive: {
    background: 'rgba(45, 74, 45, 0.15)',
    fontWeight: '600'
  },
  navBadge: {
    marginLeft: 'auto',
    padding: '2px 6px',
    background: '#22c55e',
    color: 'white',
    borderRadius: '4px',
    fontSize: '0.65rem',
    fontWeight: '600'
  },
  navDivider: {
    height: '1px',
    background: '#c5d5c5',
    margin: '1rem 0'
  },
  navPlaceholder: {
    padding: '0.75rem 1rem',
    fontSize: '0.8rem',
    color: '#5a7a5a',
    fontStyle: 'italic'
  },
  mainContent: {
    flex: 1,
    padding: '2rem',
    overflowY: 'auto'
  },
  section: {
    maxWidth: '1200px'
  },
  sectionTitle: {
    margin: '0 0 0.5rem 0',
    fontSize: '1.75rem',
    color: '#2a3441'
  },
  sectionSubtitle: {
    margin: '0 0 2rem 0',
    color: '#666',
    fontSize: '1rem'
  },
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
    padding: '0.75rem',
    border: '1px solid #ddd',
    borderRadius: '8px',
    fontSize: '1rem'
  },
  dropZone: {
    border: '2px dashed #ccc',
    borderRadius: '12px',
    padding: '3rem',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    background: '#fafafa',
    marginBottom: '1.5rem'
  },
  dropZoneActive: {
    borderColor: '#3b82f6',
    background: '#eff6ff'
  },
  dropZoneUploading: {
    borderColor: '#3b82f6',
    background: '#f0f9ff',
    cursor: 'wait'
  },
  dropIcon: {
    fontSize: '3rem',
    display: 'block',
    marginBottom: '1rem'
  },
  dropText: {
    fontSize: '1.1rem',
    color: '#333',
    margin: '0 0 0.5rem 0'
  },
  dropSubtext: {
    fontSize: '0.9rem',
    color: '#999',
    margin: 0
  },
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
    marginBottom: '1.5rem',
    flexWrap: 'wrap'
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
    alignItems: 'center',
    marginBottom: '0.5rem',
    flexWrap: 'wrap',
    gap: '0.5rem'
  },
  extractName: {
    fontWeight: '600',
    color: '#333'
  },
  sectionBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 10px',
    borderRadius: '6px',
    color: 'white',
    fontSize: '0.85rem',
    fontWeight: '500'
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
  exploreButton: {
    marginTop: '1rem',
    padding: '0.75rem 1.5rem',
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '1rem',
    fontWeight: '500',
    cursor: 'pointer'
  },
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
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1rem',
    marginBottom: '1.5rem'
  },
  statCard: {
    background: 'white',
    borderRadius: '12px',
    padding: '1.5rem',
    textAlign: 'center',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
  },
  statCardValue: {
    fontSize: '2.5rem',
    fontWeight: '700',
    color: '#3b82f6'
  },
  statCardLabel: {
    fontSize: '0.9rem',
    color: '#666',
    marginTop: '0.5rem'
  },
  mappingsTable: {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '1rem'
  },
  mappingsTh: {
    textAlign: 'left',
    padding: '0.75rem',
    borderBottom: '2px solid #e5e7eb',
    color: '#666',
    fontSize: '0.85rem'
  },
  mappingsTd: {
    padding: '0.75rem',
    borderBottom: '1px solid #f0f0f0'
  },
  mappingType: {
    display: 'inline-block',
    padding: '2px 8px',
    background: '#dbeafe',
    color: '#1e40af',
    borderRadius: '4px',
    fontSize: '0.8rem'
  },
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
