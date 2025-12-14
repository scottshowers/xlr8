/**
 * AdminPage.jsx - System Administration
 * 
 * Tabs:
 * - System: Operations Center (moved from main nav)
 * - Personas: AI persona management
 * - Security: Security settings
 * - Users: User management
 * - Permissions: Role permission grid
 * - Integrations: UKG Connections
 * 
 * REMOVED: Global Data (use Reference Library), Settings (was empty)
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PersonaManagement from '../components/PersonaManagement';
import SecurityTab from '../components/SecurityTab';
import RolePermissions from '../components/RolePermissions';
import UserManagement from '../components/UserManagement';
import SystemMonitor from '../components/SystemMonitor';
import { useAuth, Permissions } from '../context/AuthContext';
import { useProject } from '../context/ProjectContext';
import { PageHeader, EmptyState } from '../components/ui';

const COLORS = {
  grassGreen: '#83b16d',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

// ==================== INTEGRATIONS TAB (UKG Connections) ====================
function IntegrationsTab() {
  const { activeProject } = useProject();
  
  const products = [
    { id: 'pro', name: 'UKG Pro', icon: '🏢', description: 'Core HR, Payroll, Benefits', connected: false },
    { id: 'wfm', name: 'UKG WFM', icon: '⏰', description: 'Workforce Management', connected: false },
    { id: 'ready', name: 'UKG Ready', icon: '🚀', description: 'SMB HR & Payroll', connected: false },
  ];

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: COLORS.text }}>🔌 UKG API Connections</h3>
        <p style={{ margin: '0.25rem 0 0', color: COLORS.textLight, fontSize: '0.9rem' }}>
          Connect to customer UKG instances to pull configuration and data directly
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        {products.map((product) => (
          <div key={product.id} style={{
            background: product.connected ? '#f0fdf4' : '#f8fafc',
            border: `2px solid ${product.connected ? '#86efac' : '#e1e8ed'}`,
            borderRadius: '12px', padding: '1.5rem', textAlign: 'center',
          }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>{product.icon}</div>
            <div style={{ fontWeight: 700, color: COLORS.text, marginBottom: '0.25rem' }}>{product.name}</div>
            <div style={{ fontSize: '0.8rem', color: COLORS.textLight, marginBottom: '1rem' }}>{product.description}</div>
            <div style={{ fontSize: '0.75rem', color: product.connected ? '#166534' : COLORS.textLight, marginBottom: '1rem' }}>
              {product.connected ? '✓ Connected' : 'Not connected'}
            </div>
            <button disabled={!activeProject} style={{
              padding: '0.5rem 1rem',
              background: product.connected ? '#f0f4f7' : COLORS.grassGreen,
              border: product.connected ? '1px solid #e1e8ed' : 'none',
              borderRadius: '6px',
              color: product.connected ? COLORS.textLight : 'white',
              fontWeight: 600,
              cursor: activeProject ? 'pointer' : 'not-allowed',
              opacity: activeProject ? 1 : 0.5,
            }}>
              {product.connected ? 'Configure' : 'Connect'}
            </button>
          </div>
        ))}
      </div>

      {!activeProject && (
        <div style={{ padding: '1rem', background: '#fef3c7', borderRadius: '8px', color: '#92400e', fontSize: '0.9rem' }}>
          ⚠️ Select a project from the top bar to configure UKG connections.
        </div>
      )}

      <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
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
  const [activeTab, setActiveTab] = useState('system');
  const { hasPermission, isAdmin } = useAuth();

  const ALL_TABS = [
    { id: 'system', label: 'System', icon: '📊', permission: Permissions.OPS_CENTER },
    { id: 'personas', label: 'Personas', icon: '🎭', permission: null },
    { id: 'security', label: 'Security', icon: '🔒', permission: Permissions.SECURITY_SETTINGS },
    { id: 'users', label: 'Users', icon: '👥', permission: Permissions.USER_MANAGEMENT },
    { id: 'permissions', label: 'Permissions', icon: '🛡️', permission: Permissions.ROLE_PERMISSIONS },
    { id: 'integrations', label: 'Integrations', icon: '🔌', permission: Permissions.OPS_CENTER },
  ];

  const visibleTabs = ALL_TABS.filter(tab => {
    if (!tab.permission) return true;
    if (isAdmin) return true;
    return hasPermission(tab.permission);
  });

  const styles = {
    card: { background: 'white', borderRadius: '16px', boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)', overflow: 'hidden' },
    tabs: { display: 'flex', borderBottom: '1px solid #e1e8ed', background: '#fafbfc', overflowX: 'auto' },
    tab: (active) => ({
      display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '1rem 1.25rem',
      border: 'none', background: active ? 'white' : 'transparent',
      color: active ? COLORS.grassGreen : COLORS.textLight, fontWeight: '600', fontSize: '0.85rem',
      cursor: 'pointer', borderBottom: active ? `2px solid ${COLORS.grassGreen}` : '2px solid transparent',
      marginBottom: '-1px', whiteSpace: 'nowrap',
    }),
    tabContent: { padding: '1.5rem', minHeight: '400px' },
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'system':
        return <SystemMonitor />;
      case 'personas':
        return <PersonaManagement />;
      case 'security':
        return <SecurityTab />;
      case 'users':
        return <UserManagement />;
      case 'permissions':
        return <RolePermissions />;
      case 'integrations':
        return <IntegrationsTab />;
      default:
        return <SystemMonitor />;
    }
  };

  return (
    <div data-tour="admin-header">
      <PageHeader title="Admin" subtitle="System administration and configuration" />

      <div style={styles.card}>
        <div style={styles.tabs}>
          {visibleTabs.map(tab => (
            <button
              key={tab.id}
              data-tour={`admin-tab-${tab.id}`}
              style={styles.tab(activeTab === tab.id)}
              onClick={() => setActiveTab(tab.id)}
            >
              <span>{tab.icon}</span>
              {tab.label}
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
