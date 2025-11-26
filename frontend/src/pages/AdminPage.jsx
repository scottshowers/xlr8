import { useState, useEffect } from 'react'
import PersonaManagement from '../components/PersonaManagement'

/**
 * Admin Page - Main Dashboard
 * 
 * Central hub for system administration
 * Includes: Dashboard, Personas, Data Management, Security, Settings
 */
export default function AdminPage() {
  const [currentSection, setCurrentSection] = useState('dashboard')

  return (
    <div style={styles.container}>
      {/* Sidebar Navigation */}
      <div style={styles.sidebar}>
        <div style={styles.sidebarHeader}>
          <h2 style={styles.sidebarTitle}>⚙️ Admin</h2>
        </div>

        <nav style={styles.nav}>
          <button
            onClick={() => setCurrentSection('dashboard')}
            style={{
              ...styles.navItem,
              ...(currentSection === 'dashboard' ? styles.navItemActive : {})
            }}
          >
            📊 Dashboard
          </button>

          <button
            onClick={() => setCurrentSection('personas')}
            style={{
              ...styles.navItem,
              ...(currentSection === 'personas' ? styles.navItemActive : {})
            }}
          >
            🎭 Persona Management
          </button>

          <button
            onClick={() => setCurrentSection('data')}
            style={{
              ...styles.navItem,
              ...(currentSection === 'data' ? styles.navItemActive : {})
            }}
          >
            📊 Data Management
          </button>

          <button
            onClick={() => setCurrentSection('security')}
            style={{
              ...styles.navItem,
              ...(currentSection === 'security' ? styles.navItemActive : {})
            }}
          >
            🔒 Security
          </button>

          <button
            onClick={() => setCurrentSection('settings')}
            style={{
              ...styles.navItem,
              ...(currentSection === 'settings' ? styles.navItemActive : {})
            }}
          >
            ⚙️ Settings
          </button>

          {/* Placeholder for future features */}
          <div style={styles.navDivider} />
          
          <div style={styles.navPlaceholder}>
            🚀 More features coming...
          </div>
        </nav>
      </div>

      {/* Main Content Area */}
      <div style={styles.mainContent}>
        {currentSection === 'dashboard' && <DashboardSection setCurrentSection={setCurrentSection} />}
        {currentSection === 'personas' && <PersonaManagement />}
        {currentSection === 'data' && <DataManagementSection />}
        {currentSection === 'security' && <SecuritySection />}
        {currentSection === 'settings' && <SettingsSection />}
      </div>
    </div>
  )
}

// ============================================================================
// DATA MANAGEMENT SECTION - Structured Data (DuckDB) + Documents (ChromaDB)
// ============================================================================
function DataManagementSection() {
  const [structuredData, setStructuredData] = useState(null)
  const [documents, setDocuments] = useState(null)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(null)
  const [expandedFile, setExpandedFile] = useState(null)
  const [message, setMessage] = useState(null)

  const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app'

  const fetchData = async () => {
    setLoading(true)
    try {
      // Fetch structured data (Excel/CSV in DuckDB)
      const structuredRes = await fetch(`${API_BASE}/api/status/structured`)
      const structuredJson = await structuredRes.json()
      setStructuredData(structuredJson)

      // Fetch documents (PDFs/Word in ChromaDB)
      const docsRes = await fetch(`${API_BASE}/api/status/documents`)
      const docsJson = await docsRes.json()
      setDocuments(docsJson)
    } catch (err) {
      console.error('Failed to fetch data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const showMessage = (text, type = 'success') => {
    setMessage({ text, type })
    setTimeout(() => setMessage(null), 4000)
  }

  // Delete structured file (Excel/CSV from DuckDB)
  const deleteStructuredFile = async (project, filename) => {
    if (!confirm(`Delete all data for "${filename}"?\n\nThis will remove all tables and data. You can re-upload to restore.`)) {
      return
    }

    setDeleting(`structured:${project}:${filename}`)
    try {
      const res = await fetch(
        `${API_BASE}/api/status/structured/${encodeURIComponent(project)}/${encodeURIComponent(filename)}`,
        { method: 'DELETE' }
      )
      
      if (res.ok) {
        showMessage(`Deleted "${filename}" successfully`)
        fetchData()
      } else {
        const err = await res.json()
        showMessage(`Failed: ${err.detail || 'Unknown error'}`, 'error')
      }
    } catch (err) {
      showMessage('Failed to delete file', 'error')
    } finally {
      setDeleting(null)
    }
  }

  // Delete document (PDF/Word from ChromaDB)
  const deleteDocument = async (filename) => {
    if (!confirm(`Delete "${filename}" from vector store?\n\nThis removes all chunks. You can re-upload to restore.`)) {
      return
    }

    setDeleting(`doc:${filename}`)
    try {
      const res = await fetch(
        `${API_BASE}/api/status/documents/${encodeURIComponent(filename)}`,
        { method: 'DELETE' }
      )
      
      if (res.ok) {
        showMessage(`Deleted "${filename}" successfully`)
        fetchData()
      } else {
        const err = await res.json()
        showMessage(`Failed: ${err.detail || 'Unknown error'}`, 'error')
      }
    } catch (err) {
      showMessage('Failed to delete document', 'error')
    } finally {
      setDeleting(null)
    }
  }

  // Reset all structured data
  const resetStructuredData = async () => {
    if (!confirm('⚠️ DELETE ALL STRUCTURED DATA?\n\nThis will remove ALL Excel/CSV data from DuckDB.\nThis cannot be undone!')) {
      return
    }
    if (!confirm('Are you REALLY sure? Type "yes" mentally and click OK.')) {
      return
    }

    setDeleting('reset-structured')
    try {
      const res = await fetch(`${API_BASE}/api/status/structured/reset`, { method: 'POST' })
      if (res.ok) {
        showMessage('All structured data deleted')
        fetchData()
      } else {
        showMessage('Failed to reset', 'error')
      }
    } catch (err) {
      showMessage('Failed to reset', 'error')
    } finally {
      setDeleting(null)
    }
  }

  // Reset ChromaDB
  const resetChromaDB = async () => {
    if (!confirm('⚠️ DELETE ALL DOCUMENTS?\n\nThis will remove ALL PDFs/Word docs from ChromaDB.\nThis cannot be undone!')) {
      return
    }
    if (!confirm('Are you REALLY sure?')) {
      return
    }

    setDeleting('reset-chromadb')
    try {
      const res = await fetch(`${API_BASE}/api/status/chromadb/reset`, { method: 'POST' })
      if (res.ok) {
        showMessage('All documents deleted')
        fetchData()
      } else {
        showMessage('Failed to reset', 'error')
      }
    } catch (err) {
      showMessage('Failed to reset', 'error')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div style={styles.section}>
      <h1 style={styles.sectionTitle}>📊 Data Management</h1>
      <p style={styles.sectionSubtitle}>Manage uploaded files and data stores</p>

      {/* Message Toast */}
      {message && (
        <div style={{
          ...styles.toast,
          background: message.type === 'error' ? '#fee2e2' : '#dcfce7',
          color: message.type === 'error' ? '#b91c1c' : '#166534',
          borderColor: message.type === 'error' ? '#fca5a5' : '#86efac'
        }}>
          {message.text}
        </div>
      )}

      {loading ? (
        <div style={styles.loadingBox}>
          <div style={styles.spinner}></div>
          <p>Loading data...</p>
        </div>
      ) : (
        <>
          {/* ============================================================ */}
          {/* STRUCTURED DATA SECTION (Excel/CSV → DuckDB) */}
          {/* ============================================================ */}
          <div style={styles.card}>
            <div style={styles.cardHeader}>
              <h3 style={styles.cardTitle}>📊 Structured Data (SQL Queries)</h3>
              <div style={styles.cardStats}>
                {structuredData?.available ? (
                  <span>{structuredData.total_files} files • {structuredData.total_tables} tables • {structuredData.total_rows?.toLocaleString()} rows</span>
                ) : (
                  <span style={{color: '#ef4444'}}>Not available</span>
                )}
              </div>
            </div>

            {!structuredData?.available ? (
              <p style={styles.notAvailable}>
                Structured data queries not available. Ensure duckdb and cryptography packages are installed.
              </p>
            ) : structuredData.files?.length === 0 ? (
              <div style={styles.emptyState}>
                <span style={{fontSize: '3rem'}}>📁</span>
                <p>No Excel/CSV files uploaded yet</p>
                <p style={{fontSize: '0.85rem', color: '#999'}}>Upload Excel or CSV files to enable SQL queries</p>
              </div>
            ) : (
              <div style={styles.tableWrapper}>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>File</th>
                      <th style={styles.th}>Project</th>
                      <th style={{...styles.th, textAlign: 'center'}}>Sheets</th>
                      <th style={{...styles.th, textAlign: 'center'}}>Rows</th>
                      <th style={{...styles.th, textAlign: 'center'}}>🔒</th>
                      <th style={{...styles.th, textAlign: 'center'}}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {structuredData.files.map((file) => (
                      <>
                        <tr 
                          key={`${file.project}::${file.filename}`}
                          style={styles.tr}
                          onClick={() => setExpandedFile(expandedFile === file.filename ? null : file.filename)}
                        >
                          <td style={styles.td}>
                            <div style={{display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer'}}>
                              <span>{file.filename.endsWith('.csv') ? '📄' : '📊'}</span>
                              <span style={{fontWeight: 500}}>{file.filename}</span>
                              <span style={{color: '#999', fontSize: '0.75rem'}}>
                                {expandedFile === file.filename ? '▼' : '▶'}
                              </span>
                            </div>
                          </td>
                          <td style={styles.td}>
                            <span style={styles.projectBadge}>{file.project}</span>
                          </td>
                          <td style={{...styles.td, textAlign: 'center'}}>{file.sheets?.length || 0}</td>
                          <td style={{...styles.td, textAlign: 'center'}}>{file.total_rows?.toLocaleString()}</td>
                          <td style={{...styles.td, textAlign: 'center'}}>
                            {file.has_encrypted ? <span title="Contains encrypted PII">🔒</span> : '-'}
                          </td>
                          <td style={{...styles.td, textAlign: 'center'}}>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                deleteStructuredFile(file.project, file.filename)
                              }}
                              disabled={deleting === `structured:${file.project}:${file.filename}`}
                              style={styles.deleteBtn}
                              title="Delete file data"
                            >
                              {deleting === `structured:${file.project}:${file.filename}` ? '⏳' : '🗑️'}
                            </button>
                          </td>
                        </tr>
                        
                        {/* Expanded row showing sheets */}
                        {expandedFile === file.filename && (
                          <tr key={`${file.filename}-expanded`}>
                            <td colSpan={6} style={styles.expandedTd}>
                              <div style={styles.sheetsContainer}>
                                <p style={styles.sheetsLabel}>SHEETS / TABLES:</p>
                                {file.sheets?.map((sheet) => (
                                  <div key={sheet.table_name} style={styles.sheetRow}>
                                    <div>
                                      <strong>{sheet.sheet_name}</strong>
                                      <span style={{color: '#999', marginLeft: '8px', fontSize: '0.8rem'}}>
                                        ({sheet.column_count} columns)
                                      </span>
                                    </div>
                                    <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
                                      <span>{sheet.row_count?.toLocaleString()} rows</span>
                                      {sheet.encrypted_columns?.length > 0 && (
                                        <span style={{color: '#22c55e', fontSize: '0.8rem'}}>
                                          🔒 {sheet.encrypted_columns.length} encrypted
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {structuredData?.available && structuredData.files?.length > 0 && (
              <div style={styles.dangerZone}>
                <button
                  onClick={resetStructuredData}
                  disabled={deleting === 'reset-structured'}
                  style={styles.dangerBtn}
                >
                  {deleting === 'reset-structured' ? '⏳ Deleting...' : '⚠️ Reset All Structured Data'}
                </button>
              </div>
            )}
          </div>

          {/* ============================================================ */}
          {/* DOCUMENTS SECTION (PDF/Word → ChromaDB) */}
          {/* ============================================================ */}
          <div style={{...styles.card, marginTop: '2rem'}}>
            <div style={styles.cardHeader}>
              <h3 style={styles.cardTitle}>📄 Documents (RAG/Vector Store)</h3>
              <div style={styles.cardStats}>
                <span>{documents?.total || 0} files • {documents?.total_chunks?.toLocaleString() || 0} chunks</span>
              </div>
            </div>

            {!documents?.documents?.length ? (
              <div style={styles.emptyState}>
                <span style={{fontSize: '3rem'}}>📄</span>
                <p>No documents in vector store</p>
                <p style={{fontSize: '0.85rem', color: '#999'}}>Upload PDFs or Word docs for RAG queries</p>
              </div>
            ) : (
              <div style={styles.tableWrapper}>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>File</th>
                      <th style={styles.th}>Project</th>
                      <th style={styles.th}>Area</th>
                      <th style={{...styles.th, textAlign: 'center'}}>Chunks</th>
                      <th style={{...styles.th, textAlign: 'center'}}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.documents.map((doc) => (
                      <tr key={doc.filename} style={styles.tr}>
                        <td style={styles.td}>
                          <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                            <span>📄</span>
                            <span style={{fontWeight: 500}}>{doc.filename}</span>
                          </div>
                        </td>
                        <td style={styles.td}>
                          <span style={styles.projectBadge}>{doc.project}</span>
                        </td>
                        <td style={styles.td}>{doc.functional_area || '-'}</td>
                        <td style={{...styles.td, textAlign: 'center'}}>{doc.chunks}</td>
                        <td style={{...styles.td, textAlign: 'center'}}>
                          <button
                            onClick={() => deleteDocument(doc.filename)}
                            disabled={deleting === `doc:${doc.filename}`}
                            style={styles.deleteBtn}
                            title="Delete document"
                          >
                            {deleting === `doc:${doc.filename}` ? '⏳' : '🗑️'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {documents?.documents?.length > 0 && (
              <div style={styles.dangerZone}>
                <button
                  onClick={resetChromaDB}
                  disabled={deleting === 'reset-chromadb'}
                  style={styles.dangerBtn}
                >
                  {deleting === 'reset-chromadb' ? '⏳ Deleting...' : '⚠️ Reset All Documents'}
                </button>
              </div>
            )}
          </div>

          {/* Info Box */}
          <div style={styles.infoBox}>
            <strong>💡 How it works:</strong>
            <ul style={{margin: '0.5rem 0 0 1.5rem', padding: 0}}>
              <li><strong>Structured Data (Excel/CSV)</strong> → Stored in DuckDB for fast SQL queries like "How many employees have REG earning?"</li>
              <li><strong>Documents (PDF/Word)</strong> → Stored in ChromaDB for semantic search and RAG queries</li>
            </ul>
          </div>
        </>
      )}
    </div>
  )
}

// Dashboard Section
function DashboardSection({ setCurrentSection }) {
  const [stats, setStats] = useState({
    structured: { files: '--', rows: '--' },
    documents: { files: '--', chunks: '--' }
  })

  const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app'

  useEffect(() => {
    // Fetch quick stats
    Promise.all([
      fetch(`${API_BASE}/api/status/structured`).then(r => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/status/documents`).then(r => r.json()).catch(() => null)
    ]).then(([structured, docs]) => {
      setStats({
        structured: {
          files: structured?.total_files || 0,
          rows: structured?.total_rows?.toLocaleString() || 0
        },
        documents: {
          files: docs?.total || 0,
          chunks: docs?.total_chunks?.toLocaleString() || 0
        }
      })
    })
  }, [])

  return (
    <div style={styles.section}>
      <h1 style={styles.sectionTitle}>📊 Admin Dashboard</h1>
      <p style={styles.sectionSubtitle}>System overview and quick stats</p>

      <div style={styles.statsGrid}>
        <StatCard
          icon="🎭"
          title="Active Personas"
          value="5"
          subtitle="Built-in personas"
        />
        <StatCard
          icon="📊"
          title="Structured Data"
          value={stats.structured.files}
          subtitle={`${stats.structured.rows} total rows`}
        />
        <StatCard
          icon="📄"
          title="Documents"
          value={stats.documents.files}
          subtitle={`${stats.documents.chunks} chunks`}
        />
        <StatCard
          icon="👥"
          title="Users"
          value="--"
          subtitle="Coming soon"
        />
      </div>

      <div style={styles.quickActions}>
        <h3 style={styles.quickActionsTitle}>Quick Actions</h3>
        <div style={styles.actionGrid}>
          <button
            style={styles.actionButton}
            onClick={() => setCurrentSection('personas')}
          >
            <div style={styles.actionIcon}>🎭</div>
            <div style={styles.actionContent}>
              <div style={styles.actionTitle}>Manage Personas</div>
              <div style={styles.actionDescription}>Create, edit, or delete personas</div>
            </div>
          </button>

          <button
            style={styles.actionButton}
            onClick={() => setCurrentSection('data')}
          >
            <div style={styles.actionIcon}>📊</div>
            <div style={styles.actionContent}>
              <div style={styles.actionTitle}>Data Management</div>
              <div style={styles.actionDescription}>Manage uploaded files and data</div>
            </div>
          </button>

          <button
            style={styles.actionButton}
            onClick={() => setCurrentSection('security')}
          >
            <div style={styles.actionIcon}>🔒</div>
            <div style={styles.actionContent}>
              <div style={styles.actionTitle}>Security Settings</div>
              <div style={styles.actionDescription}>Configure access and permissions</div>
            </div>
          </button>
        </div>
      </div>
    </div>
  )
}

// Security Section (Placeholder)
function SecuritySection() {
  return (
    <div style={styles.section}>
      <h1 style={styles.sectionTitle}>🔒 Security Settings</h1>
      <p style={styles.sectionSubtitle}>Manage access controls and authentication</p>

      <div style={styles.card}>
        <h3 style={styles.cardTitle}>🚧 Coming Soon</h3>
        <p style={styles.cardText}>
          This section will include:
        </p>
        <ul style={styles.featureList}>
          <li>Role-based access control (RBAC)</li>
          <li>User management</li>
          <li>Password policies</li>
          <li>Session management</li>
          <li>Audit logs</li>
          <li>API key management</li>
        </ul>
      </div>
    </div>
  )
}

// Settings Section (Placeholder)
function SettingsSection() {
  return (
    <div style={styles.section}>
      <h1 style={styles.sectionTitle}>⚙️ System Settings</h1>
      <p style={styles.sectionSubtitle}>Configure system behavior and preferences</p>

      <div style={styles.card}>
        <h3 style={styles.cardTitle}>🚧 Coming Soon</h3>
        <p style={styles.cardText}>
          This section will include:
        </p>
        <ul style={styles.featureList}>
          <li>Default persona settings</li>
          <li>Chat history retention</li>
          <li>Document upload limits</li>
          <li>LLM configuration</li>
          <li>Notification settings</li>
          <li>System maintenance</li>
        </ul>
      </div>
    </div>
  )
}

// Stat Card Component
function StatCard({ icon, title, value, subtitle }) {
  return (
    <div style={styles.statCard}>
      <div style={styles.statIcon}>{icon}</div>
      <div style={styles.statContent}>
        <div style={styles.statValue}>{value}</div>
        <div style={styles.statTitle}>{title}</div>
        <div style={styles.statSubtitle}>{subtitle}</div>
      </div>
    </div>
  )
}

const styles = {
  // Main Layout
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
    borderBottom: '1px solid rgba(42, 52, 65, 0.15)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
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
    color: 'rgba(42, 52, 65, 0.4)',
    fontStyle: 'italic'
  },

  // Main Content
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

  // Stats Grid
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
    gap: '1.5rem',
    marginBottom: '3rem'
  },
  statCard: {
    background: 'white',
    borderRadius: '12px',
    padding: '1.5rem',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    display: 'flex',
    alignItems: 'center',
    gap: '1rem'
  },
  statIcon: {
    fontSize: '3rem',
    lineHeight: 1
  },
  statContent: {
    flex: 1
  },
  statValue: {
    fontSize: '2rem',
    fontWeight: '700',
    color: '#2a3441',
    marginBottom: '0.25rem'
  },
  statTitle: {
    fontSize: '0.9rem',
    color: '#666',
    marginBottom: '0.25rem'
  },
  statSubtitle: {
    fontSize: '0.8rem',
    color: '#999'
  },

  // Quick Actions
  quickActions: {
    background: 'white',
    borderRadius: '12px',
    padding: '2rem',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
  },
  quickActionsTitle: {
    margin: '0 0 1.5rem 0',
    fontSize: '1.25rem',
    color: '#2a3441'
  },
  actionGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
    gap: '1rem'
  },
  actionButton: {
    background: '#f8f9fa',
    border: '2px solid #e0e0e0',
    borderRadius: '12px',
    padding: '1.5rem',
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    textAlign: 'left'
  },
  actionIcon: {
    fontSize: '2.5rem',
    lineHeight: 1
  },
  actionContent: {
    flex: 1
  },
  actionTitle: {
    fontSize: '1rem',
    fontWeight: '600',
    color: '#2a3441',
    marginBottom: '0.25rem'
  },
  actionDescription: {
    fontSize: '0.85rem',
    color: '#666'
  },

  // Card Styles
  card: {
    background: 'white',
    borderRadius: '12px',
    padding: '1.5rem',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
    paddingBottom: '1rem',
    borderBottom: '1px solid #eee'
  },
  cardTitle: {
    margin: 0,
    fontSize: '1.25rem',
    color: '#2a3441'
  },
  cardStats: {
    fontSize: '0.9rem',
    color: '#666'
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
  },

  // Table Styles
  tableWrapper: {
    overflowX: 'auto'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse'
  },
  th: {
    textAlign: 'left',
    padding: '0.75rem 1rem',
    fontSize: '0.75rem',
    fontWeight: '600',
    color: '#666',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    borderBottom: '2px solid #eee'
  },
  tr: {
    borderBottom: '1px solid #f0f0f0',
    transition: 'background 0.15s'
  },
  td: {
    padding: '0.75rem 1rem',
    fontSize: '0.9rem',
    color: '#333'
  },
  expandedTd: {
    padding: '1rem',
    background: '#f9fafb'
  },
  projectBadge: {
    display: 'inline-block',
    padding: '0.25rem 0.75rem',
    fontSize: '0.75rem',
    fontWeight: '500',
    background: '#dbeafe',
    color: '#1e40af',
    borderRadius: '999px'
  },
  deleteBtn: {
    padding: '0.4rem 0.6rem',
    background: 'transparent',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '1rem',
    transition: 'background 0.15s'
  },

  // Sheets expanded view
  sheetsContainer: {
    marginLeft: '1.5rem'
  },
  sheetsLabel: {
    fontSize: '0.7rem',
    fontWeight: '600',
    color: '#999',
    marginBottom: '0.5rem',
    letterSpacing: '0.05em'
  },
  sheetRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.5rem 0.75rem',
    background: 'white',
    borderRadius: '6px',
    border: '1px solid #e5e7eb',
    marginBottom: '0.5rem',
    fontSize: '0.85rem'
  },

  // States
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
    padding: '2rem',
    color: '#666'
  },
  notAvailable: {
    color: '#ef4444',
    padding: '1rem',
    background: '#fef2f2',
    borderRadius: '8px'
  },

  // Danger zone
  dangerZone: {
    marginTop: '1rem',
    paddingTop: '1rem',
    borderTop: '1px solid #fee2e2',
    textAlign: 'right'
  },
  dangerBtn: {
    padding: '0.5rem 1rem',
    fontSize: '0.85rem',
    background: '#fef2f2',
    color: '#b91c1c',
    border: '1px solid #fecaca',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'background 0.15s'
  },

  // Toast message
  toast: {
    padding: '1rem',
    borderRadius: '8px',
    marginBottom: '1rem',
    border: '1px solid',
    fontWeight: '500'
  },

  // Info box
  infoBox: {
    marginTop: '2rem',
    padding: '1rem',
    background: '#f0f9ff',
    borderRadius: '8px',
    border: '1px solid #bae6fd',
    fontSize: '0.9rem',
    color: '#0c4a6e'
  }
}
