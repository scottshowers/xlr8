/**
 * WorkspacePage - The Main Work Hub
 * Chat + Personas tabs
 */

import React, { useState } from 'react';
import { useProject } from '../context/ProjectContext';
import Chat from '../components/Chat';
import PersonaManagement from '../components/PersonaManagement';

const TABS = [
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'personas', label: 'Personas', icon: '🎭' },
];

// No-project placeholder
function SelectProjectPrompt() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '50vh',
      textAlign: 'center',
      padding: '2rem',
    }}>
      <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.6 }}>🎯</div>
      <h2 style={{
        fontFamily: "'Sora', sans-serif",
        fontSize: '1.25rem',
        fontWeight: '700',
        color: '#2a3441',
        marginBottom: '0.5rem',
      }}>Select a Project to Begin</h2>
      <p style={{
        color: '#5f6c7b',
        fontSize: '0.9rem',
        maxWidth: '350px',
        lineHeight: '1.5',
      }}>
        Choose a project from the selector above to start.
      </p>
    </div>
  );
}

export default function WorkspacePage() {
  const { activeProject, projectName, customerName, hasActiveProject, loading } = useProject();
  const [activeTab, setActiveTab] = useState('chat');

  const styles = {
    tabs: {
      display: 'flex',
      borderBottom: '1px solid #e1e8ed',
      background: '#fafbfc',
      borderRadius: '16px 16px 0 0',
      marginBottom: '0',
    },
    tab: (active) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '1rem 1.5rem',
      border: 'none',
      background: active ? 'white' : 'transparent',
      color: active ? '#83b16d' : '#5f6c7b',
      fontWeight: '600',
      fontSize: '0.9rem',
      cursor: 'pointer',
      borderBottom: active ? '2px solid #83b16d' : '2px solid transparent',
      marginBottom: '-1px',
      transition: 'all 0.2s ease',
    }),
    tabContent: {
      background: 'white',
      borderRadius: '0 0 16px 16px',
      padding: '1.5rem',
      minHeight: '400px',
    },
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
        <div className="spinner" />
      </div>
    );
  }

  if (!hasActiveProject) {
    return <SelectProjectPrompt />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 140px)' }}>
      {/* Compact Header */}
      <div style={{ marginBottom: '0.75rem', flexShrink: 0 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.8rem',
          color: '#5f6c7b',
          marginBottom: '0.25rem',
        }}>
          <span>{customerName}</span>
          <span>→</span>
          <span style={{ color: '#83b16d', fontWeight: '600' }}>{projectName}</span>
        </div>
        <h1 style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: '1.25rem',
          fontWeight: '700',
          color: '#2a3441',
          margin: 0,
        }}>Workspace</h1>
      </div>

      {/* Tabs */}
      <div style={styles.tabs}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            style={styles.tab(activeTab === tab.id)}
            onClick={() => setActiveTab(tab.id)}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'chat' ? (
        <div style={{ flex: 1, minHeight: 0 }}>
          <Chat 
            projects={[activeProject]} 
            selectedProject={projectName}
            hideProjectSelector={true}
          />
        </div>
      ) : (
        <div style={styles.tabContent}>
          <PersonaManagement />
        </div>
      )}
    </div>
  );
}
