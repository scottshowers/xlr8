/**
 * WorkspacePage - The Main Work Hub
 * 
 * This is where the work happens:
 * - Chat with AI
 * - View analysis results
 * - Generate deliverables
 * 
 * Requires active project context.
 */

import React from 'react';
import { useProject } from '../context/ProjectContext';
import Chat from '../components/Chat';

// No-project placeholder
function SelectProjectPrompt() {
  const styles = {
    container: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '60vh',
      textAlign: 'center',
      padding: '2rem',
    },
    icon: {
      fontSize: '4rem',
      marginBottom: '1.5rem',
      opacity: 0.6,
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.5rem',
      fontWeight: '700',
      color: '#2a3441',
      marginBottom: '0.75rem',
    },
    subtitle: {
      color: '#5f6c7b',
      fontSize: '1rem',
      maxWidth: '400px',
      lineHeight: '1.6',
    },
    arrow: {
      marginTop: '2rem',
      color: '#83b16d',
      fontSize: '1.5rem',
      animation: 'bounce 2s infinite',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.icon}>🎯</div>
      <h2 style={styles.title}>Select a Project to Begin</h2>
      <p style={styles.subtitle}>
        Choose a project from the selector above to start analyzing data, 
        chatting with the AI, and generating deliverables.
      </p>
      <div style={styles.arrow}>↑</div>
      <style>{`
        @keyframes bounce {
          0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-10px); }
          60% { transform: translateY(-5px); }
        }
      `}</style>
    </div>
  );
}

export default function WorkspacePage() {
  const { activeProject, projectName, customerName, hasActiveProject, loading } = useProject();

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
        <div className="spinner" />
      </div>
    );
  }

  if (!hasActiveProject) {
    return <SelectProjectPrompt />;
  }

  const styles = {
    header: {
      marginBottom: '1.5rem',
    },
    breadcrumb: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '0.85rem',
      color: '#5f6c7b',
      marginBottom: '0.5rem',
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.75rem',
      fontWeight: '700',
      color: '#2a3441',
      margin: 0,
    },
    subtitle: {
      color: '#5f6c7b',
      marginTop: '0.25rem',
    },
  };

  return (
    <div>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.breadcrumb}>
          <span>{customerName}</span>
          <span>→</span>
          <span style={{ color: '#83b16d', fontWeight: '600' }}>{projectName}</span>
        </div>
        <h1 style={styles.title}>Workspace</h1>
        <p style={styles.subtitle}>
          Chat with the AI, analyze your data, and generate deliverables.
        </p>
      </div>

      {/* Chat Component - Pass project context */}
      <Chat 
        projects={[activeProject]} 
        selectedProject={projectName}
        hideProjectSelector={true}
      />
    </div>
  );
}
