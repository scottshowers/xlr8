/**
 * AdminPage - System Administration
 * 
 * POLISHED: Consistent loading, error states, and navigation patterns
 * 
 * Tabs:
 * - System Monitor: System health and status
 * - Personas: AI persona management
 * - Security: Security settings and toggles
 * - Users: User management (admin only)
 * - Permissions: Role permission grid (admin only)
 * - Settings: System configuration
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PersonaManagement from '../components/PersonaManagement';
import SecurityTab from '../components/SecurityTab';
import RolePermissions from '../components/RolePermissions';
import UserManagement from '../components/UserManagement';
import { useAuth, Permissions } from '../context/AuthContext';
import { PageHeader, Card, EmptyState } from '../components/ui';

// Brand Colors
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

// ==================== MAIN COMPONENT ====================
export default function AdminPage() {
  const [activeTab, setActiveTab] = useState('settings');
  const navigate = useNavigate();
  const { hasPermission, isAdmin } = useAuth();

  // Tab definitions with permissions
  const ALL_TABS = [
    { id: 'system', label: 'System Monitor', icon: '📊', link: '/system', permission: Permissions.OPS_CENTER },
    { id: 'personas', label: 'Personas', icon: '🎭', permission: null },
    { id: 'security', label: 'Security', icon: '🔒', permission: Permissions.SECURITY_SETTINGS },
    { id: 'users', label: 'Users', icon: '👥', permission: Permissions.USER_MANAGEMENT },
    { id: 'permissions', label: 'Permissions', icon: '🛡️', permission: Permissions.ROLE_PERMISSIONS },
    { id: 'settings', label: 'Settings', icon: '⚙️', permission: null },
  ];

  // Filter tabs based on permissions
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
      padding: '1rem 1.5rem',
      border: 'none',
      background: active ? 'white' : 'transparent',
      color: active ? COLORS.grassGreen : COLORS.textLight,
      fontWeight: '600',
      fontSize: '0.9rem',
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
      case 'settings':
        return <SettingsTab />;
      default:
        return null;
    }
  };

  return (
    <div>
      <PageHeader
        title="Administration"
        subtitle="System monitoring and configuration."
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
              {tab.link && <span style={{ opacity: 0.5, marginLeft: '0.25rem' }}>↗</span>}
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
