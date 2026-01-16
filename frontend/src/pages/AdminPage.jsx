/**
 * AdminPage.jsx - Settings Sub-Page
 * 
 * Updated: January 16, 2026 - Simplified tabs
 * 
 * Tabs (linked from AdminHub/Platform Settings):
 * - Users: User management
 * - Permissions: Role permission grid
 * - Security: Security settings
 * - Integrations: UKG Connections
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import SecurityTab from '../components/SecurityTab';
import RolePermissions from '../components/RolePermissions';
import UserManagement from '../components/UserManagement';
import { useAuth, Permissions } from '../context/AuthContext';
import { useProject } from '../context/ProjectContext';
import { PageHeader } from '../components/ui';
import { SimpleTooltip } from '../components/ui/Tooltip';
import { 
  Settings, Users, Shield, Lock, Plug,
  Building2, Clock, Rocket, ArrowLeft
} from 'lucide-react';

const COLORS = {
  primary: '#83b16d',
  text: '#1a2332',
  textMuted: '#64748b',
  bg: '#f0f2f5',
  card: '#ffffff',
  border: '#e2e8f0',
  white: '#ffffff',
};

// ==================== INTEGRATIONS TAB (UKG Connections) ====================
function IntegrationsTab() {
  const { activeProject } = useProject();
  
  const products = [
    { id: 'pro', name: 'UKG Pro', icon: Building2, description: 'Core HR, Payroll, Benefits', connected: false },
    { id: 'wfm', name: 'UKG WFM', icon: Clock, description: 'Workforce Management', connected: false },
    { id: 'ready', name: 'UKG Ready', icon: Rocket, description: 'SMB HR & Payroll', connected: false },
  ];

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: COLORS.text, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Plug size={18} color={COLORS.primary} />
          UKG API Connections
        </h3>
        <p style={{ margin: '0.25rem 0 0', color: COLORS.textMuted, fontSize: '0.9rem' }}>
          Connect to customer UKG instances to pull configuration and data directly
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        {products.map((product) => {
          const Icon = product.icon;
          return (
            <div key={product.id} style={{
              background: product.connected ? '#f0fdf4' : '#f8fafc',
              border: `2px solid ${product.connected ? '#86efac' : '#e1e8ed'}`,
              borderRadius: '12px', padding: '1.5rem', textAlign: 'center',
            }}>
              <div style={{ 
                width: '48px', 
                height: '48px', 
                borderRadius: '12px',
                background: product.connected ? 'rgba(22, 163, 74, 0.1)' : 'rgba(131, 177, 109, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 0.75rem',
              }}>
                <Icon size={24} color={product.connected ? '#16a34a' : COLORS.primary} />
              </div>
              <div style={{ fontWeight: 700, color: COLORS.text, marginBottom: '0.25rem' }}>{product.name}</div>
              <div style={{ fontSize: '0.8rem', color: COLORS.textMuted, marginBottom: '1rem' }}>{product.description}</div>
              <div style={{ fontSize: '0.75rem', color: product.connected ? '#166534' : COLORS.textMuted, marginBottom: '1rem' }}>
                {product.connected ? '✓ Connected' : 'Not connected'}
              </div>
              <button disabled={!activeProject} style={{
                padding: '0.5rem 1rem',
                background: product.connected ? '#f0f4f7' : COLORS.primary,
                border: product.connected ? '1px solid #e1e8ed' : 'none',
                borderRadius: '6px',
                color: product.connected ? COLORS.textMuted : 'white',
                fontWeight: 600,
                cursor: activeProject ? 'pointer' : 'not-allowed',
                opacity: activeProject ? 1 : 0.5,
              }}>
                {product.connected ? 'Configure' : 'Connect'}
              </button>
            </div>
          );
        })}
      </div>

      {!activeProject && (
        <div style={{ padding: '1rem', background: '#fef3c7', borderRadius: '8px', color: '#92400e', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Shield size={16} />
          Select a project from the top bar to configure UKG connections.
        </div>
      )}

      <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
        <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: COLORS.text }}>Coming Soon</h4>
        <ul style={{ margin: 0, paddingLeft: '1.25rem', color: COLORS.textMuted, fontSize: '0.85rem' }}>
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
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { hasPermission, isAdmin } = useAuth();
  
  // Get tab from URL or default to 'users'
  const activeTab = searchParams.get('tab') || 'users';
  
  const setActiveTab = (tabId) => {
    setSearchParams({ tab: tabId });
  };

  const ALL_TABS = [
    { id: 'users', label: 'Users', icon: Users, permission: Permissions.USER_MANAGEMENT, tooltip: 'Manage user accounts, roles, and project assignments' },
    { id: 'permissions', label: 'Permissions', icon: Shield, permission: Permissions.ROLE_PERMISSIONS, tooltip: 'Configure role-based permissions and access levels' },
    { id: 'security', label: 'Security', icon: Lock, permission: Permissions.SECURITY_SETTINGS, tooltip: 'Security settings, MFA, and access controls' },
    { id: 'integrations', label: 'Integrations', icon: Plug, permission: Permissions.OPS_CENTER, tooltip: 'Connect to external systems like UKG APIs' },
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
      color: active ? COLORS.primary : COLORS.textMuted, fontWeight: '600', fontSize: '0.85rem',
      cursor: 'pointer', borderBottom: active ? `2px solid ${COLORS.primary}` : '2px solid transparent',
      marginBottom: '-1px', whiteSpace: 'nowrap',
    }),
    tabContent: { padding: '1.5rem', minHeight: '400px' },
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'users':
        return <UserManagement />;
      case 'permissions':
        return <RolePermissions />;
      case 'security':
        return <SecurityTab />;
      case 'integrations':
        return <IntegrationsTab />;
      default:
        return <UserManagement />;
    }
  };

  return (
    <div data-tour="admin-header">
      {/* Back to Platform Settings link */}
      <button
        onClick={() => navigate('/admin')}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          color: COLORS.textMuted,
          background: 'none',
          border: 'none',
          fontSize: 13,
          marginBottom: 16,
          cursor: 'pointer',
          padding: 0,
        }}
      >
        <ArrowLeft size={16} />
        Back to Platform Settings
      </button>
      
      <PageHeader 
        icon={Settings}
        title="Admin Settings" 
        subtitle="System administration and configuration" 
      />

      <div style={styles.card}>
        <div style={styles.tabs}>
          {visibleTabs.map(tab => {
            const Icon = tab.icon;
            return (
              <SimpleTooltip key={tab.id} text={tab.tooltip}>
                <button
                  data-tour={`admin-tab-${tab.id}`}
                  style={styles.tab(activeTab === tab.id)}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <Icon size={16} />
                  {tab.label}
                </button>
              </SimpleTooltip>
            );
          })}
        </div>

        <div style={styles.tabContent}>
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
}
