/**
 * AdminPage - System Administration
 * 
 * Tabs:
 * - System Monitor: System health and status
 * - Personas: AI persona management
 * - Security: Security settings and toggles
 * - Settings: System configuration
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PersonaManagement from '../components/PersonaManagement';
import SecurityTab from '../components/SecurityTab';

// Tab definitions
const TABS = [
  { id: 'system', label: 'System Monitor', icon: '📊', link: '/system' },
  { id: 'personas', label: 'Personas', icon: '🎭' },
  { id: 'security', label: 'Security', icon: '🔒' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
];

// ==================== SETTINGS TAB ====================
function SettingsTab() {
  return (
    <div style={{ color: '#5f6c7b', textAlign: 'center', padding: '3rem' }}>
      <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>⚙️</div>
      <h3>System Settings Coming Soon</h3>
      <p>User preferences, notification settings, and system configuration.</p>
    </div>
  );
}

// ==================== MAIN COMPONENT ====================
export default function AdminPage() {
  const [activeTab, setActiveTab] = useState('settings');
  const navigate = useNavigate();

  const handleTabClick = (tab) => {
    if (tab.link) {
      navigate(tab.link);
    } else {
      setActiveTab(tab.id);
    }
  };

  const styles = {
    header: { marginBottom: '1.5rem' },
    title: { fontFamily: "'Sora', sans-serif", fontSize: '1.75rem', fontWeight: '700', color: '#2a3441', margin: 0 },
    subtitle: { color: '#5f6c7b', marginTop: '0.25rem' },
    card: { background: 'white', borderRadius: '16px', boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)', overflow: 'hidden' },
    tabs: { display: 'flex', borderBottom: '1px solid #e1e8ed', background: '#fafbfc', overflowX: 'auto' },
    tab: (active) => ({ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '1rem 1.5rem', border: 'none', background: active ? 'white' : 'transparent', color: active ? '#83b16d' : '#5f6c7b', fontWeight: '600', fontSize: '0.9rem', cursor: 'pointer', borderBottom: active ? '2px solid #83b16d' : '2px solid transparent', marginBottom: '-1px', transition: 'all 0.2s ease', whiteSpace: 'nowrap' }),
    tabContent: { padding: '1.5rem' },
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'personas': return <PersonaManagement />;
      case 'security': return <SecurityTab />;
      case 'settings': return <SettingsTab />;
      default: return null;
    }
  };

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.title}>Administration</h1>
        <p style={styles.subtitle}>System monitoring and configuration.</p>
      </div>

      <div style={styles.card}>
        <div style={styles.tabs}>
          {TABS.map(tab => (
            <button key={tab.id} style={styles.tab(activeTab === tab.id)} onClick={() => handleTabClick(tab)}>
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
