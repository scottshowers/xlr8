import { useState } from 'react'
import PersonaManagement from '../components/PersonaManagement'

/**
 * Admin Page - Main Dashboard
 * 
 * Central hub for system administration
 */
export default function AdminPage() {
  const [currentSection, setCurrentSection] = useState('dashboard')

  // Admin dashboard (no login required)
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
        {currentSection === 'security' && <SecuritySection />}
        {currentSection === 'settings' && <SettingsSection />}
      </div>
    </div>
  )
}

// Dashboard Section
function DashboardSection({ setCurrentSection }) {
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
          icon="💬"
          title="Total Chats"
          value="--"
          subtitle="Coming soon"
        />
        <StatCard
          icon="📁"
          title="Documents"
          value="--"
          subtitle="Coming soon"
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
            onClick={() => setCurrentSection('security')}
          >
            <div style={styles.actionIcon}>🔒</div>
            <div style={styles.actionContent}>
              <div style={styles.actionTitle}>Security Settings</div>
              <div style={styles.actionDescription}>Configure access and permissions</div>
            </div>
          </button>

          <button style={{...styles.actionButton, opacity: 0.5, cursor: 'not-allowed'}}>
            <div style={styles.actionIcon}>📊</div>
            <div style={styles.actionContent}>
              <div style={styles.actionTitle}>View Analytics</div>
              <div style={styles.actionDescription}>Coming soon</div>
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
  // Login Styles
  loginContainer: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    padding: '2rem'
  },
  loginBox: {
    background: 'white',
    borderRadius: '16px',
    padding: '3rem',
    maxWidth: '400px',
    width: '100%',
    boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
  },
  loginTitle: {
    margin: '0 0 0.5rem 0',
    fontSize: '2rem',
    textAlign: 'center',
    color: '#333'
  },
  loginSubtitle: {
    margin: '0 0 2rem 0',
    textAlign: 'center',
    color: '#666',
    fontSize: '0.95rem'
  },
  loginForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem'
  },
  loginInput: {
    padding: '0.75rem 1rem',
    fontSize: '1rem',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    outline: 'none',
    transition: 'border 0.2s'
  },
  loginError: {
    padding: '0.75rem',
    background: '#fee',
    border: '1px solid #fcc',
    borderRadius: '6px',
    color: '#c33',
    fontSize: '0.9rem',
    textAlign: 'center'
  },
  loginButton: {
    padding: '0.75rem 1.5rem',
    fontSize: '1rem',
    fontWeight: '600',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.2s'
  },
  loginHint: {
    marginTop: '1.5rem',
    fontSize: '0.85rem',
    color: '#999',
    textAlign: 'center'
  },

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
  logoutButton: {
    padding: '0.4rem 0.8rem',
    fontSize: '0.85rem',
    background: 'rgba(255,255,255,0.1)',
    color: 'white',
    border: '1px solid rgba(255,255,255,0.2)',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'background 0.2s'
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
