/**
 * AdminPage.jsx - System Administration
 * 
 * Tabs:
 * - System Monitor: Link to Operations Center
 * - Personas: AI persona management
 * - Security: Security settings
 * - Users: User management
 * - Permissions: Role permission grid
 * - Global Data: Cross-project reference data (moved from Data)
 * - Integrations: UKG Connections (moved from Data)
 * - Settings: System configuration
 */

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import PersonaManagement from '../components/PersonaManagement';
import SecurityTab from '../components/SecurityTab';
import RolePermissions from '../components/RolePermissions';
import UserManagement from '../components/UserManagement';
import { useAuth, Permissions } from '../context/AuthContext';
import { useProject } from '../context/ProjectContext';
import { PageHeader, Card, EmptyState } from '../components/ui';
import api from '../services/api';

const COLORS = {
  grassGreen: '#83b16d',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

// ==================== SETTINGS TAB ====================
function SettingsTab() {
  return (
    <EmptyState
      icon="⚙️"
      title="System Settings Coming Soon"
      description="User preferences, notification settings, and system configuration."
    />
  );
}

// ==================== GLOBAL DATA TAB ====================
function GlobalDataTab() {
  const [globalData, setGlobalData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const fileInputRef = useRef(null);

  const fetchGlobalData = async () => {
    setLoading(true);
    try {
      const res = await api.get('/status/structured');
      const globalFiles = (res.data?.files || []).filter(f => 
        f.project === 'GLOBAL' || f.project === 'global' || f.project === 'Global/Universal'
      );
      setGlobalData(globalFiles);
    } catch (err) {
      console.error('Failed to fetch global data:', err);
      setGlobalData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchGlobalData(); }, []);

  const handleFileSelect = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    setUploading(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('project', 'GLOBAL');
        await api.post('/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      }
      fetchGlobalData();
    } catch (err) {
      console.error('Upload failed:', err);
      alert('Upload failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const deleteFile = async (project, filename) => {
    if (!confirm(`Delete ${filename}?`)) return;
    setDeleting(filename);
    try {
      await api.delete(`/status/structured/${encodeURIComponent(project)}/${encodeURIComponent(filename)}`);
      fetchGlobalData();
    } catch (err) {
      alert('Delete failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div>
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        accept=".doc,.docx,.xls,.xlsx,.csv,.pdf,.txt"
        multiple
        onChange={handleFileSelect}
      />
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: COLORS.text }}>
            🌐 Global Reference Data
          </h3>
          <p style={{ margin: '0.25rem 0 0', color: COLORS.textLight, fontSize: '0.9rem' }}>
            Shared knowledge base available across all projects
          </p>
        </div>
        <button 
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          style={{
            padding: '0.6rem 1.2rem',
            background: COLORS.grassGreen,
            border: 'none',
            borderRadius: '8px',
            color: 'white',
            fontWeight: 600,
            cursor: 'pointer',
            opacity: uploading ? 0.5 : 1,
          }}
        >
          {uploading ? '⏳ Uploading...' : '➕ Add Data'}
        </button>
      </div>

      <p style={{ color: COLORS.textLight, fontSize: '0.85rem', marginBottom: '1.5rem', padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
        Upload UKG documentation, compliance guides, industry best practices, and firm standards. 
        This data is available to the AI across all projects for context and reference.
      </p>

      {loading ? (
        <p style={{ color: COLORS.textLight }}>Loading...</p>
      ) : globalData.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: COLORS.textLight }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.3 }}>📚</div>
          <p>No global data uploaded yet.</p>
          <p style={{ fontSize: '0.85rem' }}>Upload reference documents to enhance AI capabilities.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {globalData.map((file) => (
            <div key={file.filename} style={{
              background: '#f8fafc',
              borderRadius: '8px',
              padding: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <div>
                <strong>{file.filename}</strong>
                <div style={{ fontSize: '0.8rem', color: COLORS.textLight }}>
                  {file.sheets?.length || 0} sheets • {file.total_rows?.toLocaleString() || 0} rows
                </div>
              </div>
              <button
                onClick={() => deleteFile(file.project, file.filename)}
                disabled={deleting === file.filename}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#ef4444',
                  fontSize: '1rem',
                }}
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ==================== INTEGRATIONS TAB (UKG Connections) ====================
function IntegrationsTab() {
  const { activeProject } = useProject();
  
  const products = [
    { id: 'pro', name: 'UKG Pro', icon: '🏢', description: 'Core HR, Payroll, Benefits', connected: false },
    { id: 'wfm', name: 'UKG WFM', icon: '⏰', description: 'Workforce Management, Scheduling', connected: false },
    { id: 'ready', name: 'UKG Ready', icon: '🚀', description: 'SMB HR & Payroll', connected: false },
  ];

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: COLORS.text }}>
          🔌 UKG API Connections
        </h3>
        <p style={{ margin: '0.25rem 0 0', color: COLORS.textLight, fontSize: '0.9rem' }}>
          Connect to customer UKG instances to pull configuration and data directly
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        {products.map((product) => (
          <div key={product.id} style={{
            background: product.connected ? '#f0fdf4' : '#f8fafc',
            border: `2px solid ${product.connected ? '#86efac' : '#e1e8ed'}`,
            borderRadius: '12px',
            padding: '1.5rem',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>{product.icon}</div>
            <div style={{ fontWeight: 700, color: COLORS.text, marginBottom: '0.25rem' }}>{product.name}</div>
            <div style={{ fontSize: '0.8rem', color: COLORS.textLight, marginBottom: '1rem' }}>{product.description}</div>
            <div style={{
              fontSize: '0.75rem',
              color: product.connected ? '#166534' : COLORS.textLight,
              marginBottom: '1rem',
            }}>
              {product.connected ? '✓ Connected' : 'Not connected'}
            </div>
            <button
              disabled={!activeProject}
              style={{
                padding: '0.5rem 1rem',
                background: product.connected ? '#f0f4f7' : COLORS.grassGreen,
                border: product.connected ? '1px solid #e1e8ed' : 'none',
                borderRadius: '6px',
                color: product.connected ? COLORS.textLight : 'white',
                fontWeight: 600,
                cursor: activeProject ? 'pointer' : 'not-allowed',
                opacity: activeProject ? 1 : 0.5,
              }}
            >
              {product.connected ? 'Configure' : 'Connect'}
            </button>
          </div>
        ))}
      </div>

      {!activeProject && (
        <div style={{
          padding: '1rem',
          background: '#fef3c7',
          borderRadius: '8px',
          color: '#92400e',
          fontSize: '0.9rem',
        }}>
          ⚠️ Select a project from the top bar to configure UKG connections.
        </div>
      )}

      <div style={{
        marginTop: '1.5rem',
        padding: '1rem',
        background: '#f8fafc',
        borderRadius: '8px',
      }}>
        <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: COLORS.text }}>Coming Soon</h4>
        <ul style={{ margin: 0, paddingLeft: '1.25rem', color: COLORS.textLight, fontSize: '0.85rem' }}>
          <li>Direct API integration with customer UKG tenants</li>
          <li>Automatic configuration extraction</li>
          <li>Real-time data synchronization</li>
          <li>Secure credential management</li>
        </ul>
      </div>
    </div>
  );
}

// ==================== MAIN COMPONENT ====================
export default function AdminPage() {
  const [activeTab, setActiveTab] = useState('settings');
  const navigate = useNavigate();
  const { hasPermission, isAdmin } = useAuth();

  const ALL_TABS = [
    { id: 'system', label: 'System Monitor', icon: '📊', link: '/system', permission: Permissions.OPS_CENTER },
    { id: 'personas', label: 'Personas', icon: '🎭', permission: null },
    { id: 'security', label: 'Security', icon: '🔒', permission: Permissions.SECURITY_SETTINGS },
    { id: 'users', label: 'Users', icon: '👥', permission: Permissions.USER_MANAGEMENT },
    { id: 'permissions', label: 'Permissions', icon: '🛡️', permission: Permissions.ROLE_PERMISSIONS },
    { id: 'global', label: 'Global Data', icon: '🌐', permission: Permissions.OPS_CENTER },
    { id: 'integrations', label: 'Integrations', icon: '🔌', permission: Permissions.OPS_CENTER },
    { id: 'settings', label: 'Settings', icon: '⚙️', permission: null },
  ];

  const visibleTabs = ALL_TABS.filter(tab => {
    if (!tab.permission) return true;
    if (isAdmin) return true;
    return hasPermission(tab.permission);
  });

  const handleTabClick = (tab) => {
    if (tab.link) {
      navigate(tab.link);
    } else {
      setActiveTab(tab.id);
    }
  };

  const styles = {
    card: {
      background: 'white',
      borderRadius: '16px',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      overflow: 'hidden',
    },
    tabs: {
      display: 'flex',
      borderBottom: '1px solid #e1e8ed',
      background: '#fafbfc',
      overflowX: 'auto',
    },
    tab: (active) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '1rem 1.25rem',
      border: 'none',
      background: active ? 'white' : 'transparent',
      color: active ? COLORS.grassGreen : COLORS.textLight,
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
      borderBottom: active ? `2px solid ${COLORS.grassGreen}` : '2px solid transparent',
      marginBottom: '-1px',
      transition: 'all 0.2s ease',
      whiteSpace: 'nowrap',
    }),
    tabContent: {
      padding: '1.5rem',
      minHeight: '400px',
    },
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'personas':
        return <PersonaManagement />;
      case 'security':
        return <SecurityTab />;
      case 'users':
        return <UserManagement />;
      case 'permissions':
        return <RolePermissions />;
      case 'global':
        return <GlobalDataTab />;
      case 'integrations':
        return <IntegrationsTab />;
      case 'settings':
        return <SettingsTab />;
      default:
        return <SettingsTab />;
    }
  };

  return (
    <div>
      <PageHeader
        title="Admin"
        subtitle="System administration and configuration"
      />

      <div style={styles.card}>
        <div style={styles.tabs}>
          {visibleTabs.map(tab => (
            <button
              key={tab.id}
              style={styles.tab(activeTab === tab.id && !tab.link)}
              onClick={() => handleTabClick(tab)}
            >
              <span>{tab.icon}</span>
              {tab.label}
              {tab.link && <span style={{ fontSize: '0.7rem', opacity: 0.6 }}>↗</span>}
            </button>
          ))}
        </div>

        <div style={styles.tabContent}>
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
}
