/**
 * AdminPage.jsx - System Administration
 * 
 * Updated: January 4, 2026 - Visual Standards Part 13
 * - Standard page header with icon
 * - Lucide icons instead of emojis
 * 
 * Tabs:
 * - System: Operations Center
 * - Personas: AI persona management
 * - Security: Security settings
 * - Users: User management
 * - Permissions: Role permission grid
 * - Integrations: UKG Connections
 * - Data Cleanup: Mass delete functionality
 * - Endpoints: API testing tool
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import PersonaManagement from '../components/PersonaManagement';
import SecurityTab from '../components/SecurityTab';
import RolePermissions from '../components/RolePermissions';
import UserManagement from '../components/UserManagement';
import SystemMonitor from '../components/SystemMonitor';
import { useAuth, Permissions } from '../context/AuthContext';
import { useProject } from '../context/ProjectContext';
import { PageHeader, EmptyState } from '../components/ui';
import { SimpleTooltip } from '../components/ui/Tooltip';
import { 
  Settings, BarChart3, Users, Shield, Lock, Plug, Trash2, Wrench,
  Building2, Clock, Rocket, HardDrive, Zap, ArrowLeft
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

// Tab icon mapping
const TAB_ICONS = {
  system: BarChart3,
  personas: Users,
  security: Lock,
  users: Users,
  permissions: Shield,
  integrations: Plug,
  cleanup: Trash2,
  endpoints: Wrench,
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

// ==================== DATA CLEANUP TAB ====================
function CleanupTab() {
  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: COLORS.text, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Trash2 size={18} color={COLORS.primary} />
          Data Cleanup
        </h3>
        <p style={{ margin: '0.25rem 0 0', color: COLORS.textMuted, fontSize: '0.9rem' }}>
          Delete tables, documents, and orphaned data. Use Force Wipe to reset all backend storage.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{
          background: '#fef2f2',
          border: '2px solid #fecaca',
          borderRadius: '12px',
          padding: '1.5rem',
        }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            borderRadius: '10px',
            background: 'rgba(220, 38, 38, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '0.5rem',
          }}>
            <HardDrive size={20} color="#dc2626" />
          </div>
          <div style={{ fontWeight: 700, color: COLORS.text, marginBottom: '0.25rem' }}>Selective Delete</div>
          <div style={{ fontSize: '0.85rem', color: COLORS.textMuted, marginBottom: '1rem' }}>
            Choose specific tables or documents to remove
          </div>
        </div>
        
        <div style={{
          background: '#fef2f2',
          border: '2px solid #fecaca',
          borderRadius: '12px',
          padding: '1.5rem',
        }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            borderRadius: '10px',
            background: 'rgba(220, 38, 38, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '0.5rem',
          }}>
            <Zap size={20} color="#dc2626" />
          </div>
          <div style={{ fontWeight: 700, color: COLORS.text, marginBottom: '0.25rem' }}>Force Full Wipe</div>
          <div style={{ fontSize: '0.85rem', color: COLORS.textMuted, marginBottom: '1rem' }}>
            Clear ALL data: DuckDB, ChromaDB, Supabase
          </div>
        </div>
      </div>

      <Link to="/admin/data-cleanup" style={{ textDecoration: 'none' }}>
        <button style={{
          padding: '0.75rem 1.5rem',
          background: '#dc2626',
          border: 'none',
          borderRadius: '8px',
          color: 'white',
          fontWeight: 600,
          fontSize: '0.9rem',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          <Trash2 size={16} />
          Open Data Cleanup Tool
        </button>
      </Link>
    </div>
  );
}

// ==================== ENDPOINTS TAB ====================
function EndpointsTab() {
  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: COLORS.text, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Wrench size={18} color={COLORS.primary} />
          API Endpoints
        </h3>
        <p style={{ margin: '0.25rem 0 0', color: COLORS.textMuted, fontSize: '0.9rem' }}>
          Test and explore API endpoints. View responses, debug issues, and verify functionality.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{
          background: '#f0fdf4',
          border: '2px solid #86efac',
          borderRadius: '12px',
          padding: '1rem',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '1.5rem', marginBottom: '0.25rem', fontWeight: 700, color: '#16a34a' }}>GET</div>
          <div style={{ fontSize: '0.8rem', color: COLORS.textMuted }}>Read data</div>
        </div>
        <div style={{
          background: '#eff6ff',
          border: '2px solid #93c5fd',
          borderRadius: '12px',
          padding: '1rem',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '1.5rem', marginBottom: '0.25rem', fontWeight: 700, color: '#2563eb' }}>POST</div>
          <div style={{ fontSize: '0.8rem', color: COLORS.textMuted }}>Create/Update</div>
        </div>
        <div style={{
          background: '#fef2f2',
          border: '2px solid #fecaca',
          borderRadius: '12px',
          padding: '1rem',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '1.5rem', marginBottom: '0.25rem', fontWeight: 700, color: '#dc2626' }}>DELETE</div>
          <div style={{ fontSize: '0.8rem', color: COLORS.textMuted }}>Remove data</div>
        </div>
      </div>

      <div style={{ background: '#f8fafc', borderRadius: '8px', padding: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ fontSize: '0.85rem', color: COLORS.textMuted, marginBottom: '0.5rem' }}>Quick Endpoints:</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {['/api/platform', '/api/platform/health', '/api/classification/tables', '/api/classification/chunks', '/api/metrics/summary'].map(ep => (
            <code key={ep} style={{
              padding: '0.25rem 0.5rem',
              background: '#e2e8f0',
              borderRadius: '4px',
              fontSize: '0.75rem',
              color: COLORS.text,
            }}>{ep}</code>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <Link to="/admin/endpoints" style={{ textDecoration: 'none' }}>
          <button style={{
            padding: '0.75rem 1.5rem',
            background: COLORS.primary,
            border: 'none',
            borderRadius: '8px',
            color: 'white',
            fontWeight: 600,
            fontSize: '0.9rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}>
            <Wrench size={16} />
            Open Endpoints Tool
          </button>
        </Link>
        
        <Link to="/admin/intelligence-test" style={{ textDecoration: 'none' }}>
          <button style={{
            padding: '0.75rem 1.5rem',
            background: '#6366f1',
            border: 'none',
            borderRadius: '8px',
            color: 'white',
            fontWeight: 600,
            fontSize: '0.9rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}>
            <Zap size={16} />
            Intelligence Test
          </button>
        </Link>
      </div>
    </div>
  );
}

// ==================== MAIN COMPONENT ====================
export default function AdminPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { hasPermission, isAdmin } = useAuth();
  
  // Get tab from URL or default to 'system'
  const activeTab = searchParams.get('tab') || 'system';
  
  const setActiveTab = (tabId) => {
    setSearchParams({ tab: tabId });
  };

  const ALL_TABS = [
    { id: 'system', label: 'System', icon: BarChart3, permission: Permissions.OPS_CENTER, tooltip: 'Platform health, database status, and system monitoring' },
    { id: 'personas', label: 'Personas', icon: Users, permission: null, tooltip: 'Create and manage AI personas for different consulting contexts' },
    { id: 'security', label: 'Security', icon: Lock, permission: Permissions.SECURITY_SETTINGS, tooltip: 'Security settings, MFA, and access controls' },
    { id: 'users', label: 'Users', icon: Users, permission: Permissions.USER_MANAGEMENT, tooltip: 'Manage user accounts, roles, and project assignments' },
    { id: 'permissions', label: 'Permissions', icon: Shield, permission: Permissions.ROLE_PERMISSIONS, tooltip: 'Configure role-based permissions and access levels' },
    { id: 'integrations', label: 'Integrations', icon: Plug, permission: Permissions.OPS_CENTER, tooltip: 'Connect to external systems like UKG APIs' },
    { id: 'cleanup', label: 'Data Cleanup', icon: Trash2, permission: Permissions.OPS_CENTER, tooltip: 'Mass delete files and cleanup orphaned data' },
    { id: 'endpoints', label: 'Endpoints', icon: Wrench, permission: Permissions.OPS_CENTER, tooltip: 'Test and debug API endpoints directly' },
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
      case 'cleanup':
        return <CleanupTab />;
      case 'endpoints':
        return <EndpointsTab />;
      default:
        return <SystemMonitor />;
    }
  };

  return (
    <div data-tour="admin-header">
      {/* Back to Admin Hub link */}
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
        Back to Admin Hub
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
