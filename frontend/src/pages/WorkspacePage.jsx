/**
 * AI Assist - Chat Interface with Bessie
 * Streamlined chat page, no tabs
 */

import React from 'react';
import { useProject } from '../context/ProjectContext';
import Chat from '../components/Chat';

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
      <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.6 }}>🐄</div>
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
        Choose a project from the selector above to chat with Bessie.
      </p>
    </div>
  );
}

export default function WorkspacePage() {
  const { activeProject, projectName, customerName, hasActiveProject, loading } = useProject();

  const styles = {
    header: { marginBottom: '1rem' },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.75rem',
      fontWeight: '700',
      color: '#2a3441',
      margin: 0,
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    subtitle: { color: '#5f6c7b', marginTop: '0.25rem' },
    container: {
      background: 'white',
      borderRadius: '16px',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      overflow: 'hidden',
      minHeight: '60vh',
    },
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '3rem', color: '#5f6c7b' }}>Loading...</div>;
  }

  if (!hasActiveProject) {
    return (
      <div>
        <div style={styles.header}>
          <h1 style={styles.title}>
            <span>🐄</span>
            AI Assist
          </h1>
          <p style={styles.subtitle}>Chat with Bessie about your implementation.</p>
        </div>
        <div style={styles.container}>
          <SelectProjectPrompt />
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.title}>
          <span>🐄</span>
          AI Assist
        </h1>
        <p style={styles.subtitle}>
          {customerName ? `${customerName} • ` : ''}{projectName || 'Project'}
        </p>
      </div>
      <div style={styles.container}>
        <Chat />
      </div>
    </div>
  );
}
