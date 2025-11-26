/**
 * DataPage - Data Management Hub
 * 
 * Tabs:
 * - Upload Files: Standard document upload
 * - Vacuum Extract: Link to full Vacuum page (complex extraction tool)
 * - Processing Status: View file processing jobs
 * - Browse Data: View uploaded data (placeholder)
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import Upload from '../components/Upload';
import Status from '../components/Status';

// Tab definitions
const TABS = [
  { id: 'upload', label: 'Upload Files', icon: '📤' },
  { id: 'vacuum', label: 'Vacuum Extract', icon: '🧹' },
  { id: 'status', label: 'Processing Status', icon: '📊' },
  { id: 'browse', label: 'Browse Data', icon: '🗂️' },
];

export default function DataPage() {
  const { activeProject } = useProject();
  const [activeTab, setActiveTab] = useState('upload');

  const styles = {
    header: {
      marginBottom: '1.5rem',
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
      padding: '1.5rem',
    },
    noProject: {
      textAlign: 'center',
      padding: '3rem',
      color: '#5f6c7b',
    },
    noProjectIcon: {
      fontSize: '3rem',
      marginBottom: '1rem',
      opacity: 0.5,
    },
  };

  // Render tab content
  const renderTabContent = () => {
    if (!activeProject && activeTab !== 'browse') {
      return (
        <div style={styles.noProject}>
          <div style={styles.noProjectIcon}>📁</div>
          <h3>Select a Project</h3>
          <p>Choose a project from the top bar to manage data.</p>
        </div>
      );
    }

    switch (activeTab) {
      case 'upload':
        return <UploadTab project={activeProject} />;
      case 'vacuum':
        return <VacuumTab />;
      case 'status':
        return <StatusTab project={activeProject} />;
      case 'browse':
        return <BrowseTab />;
      default:
        return null;
    }
  };

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.title}>Data Management</h1>
        <p style={styles.subtitle}>
          Upload, extract, and manage project data.
          {activeProject && <span> • <strong>{activeProject.name}</strong></span>}
        </p>
      </div>

      <div style={styles.card}>
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

        <div style={styles.tabContent}>
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
}

// ==================== UPLOAD TAB ====================
function UploadTab({ project }) {
  return (
    <div>
      <Upload selectedProject={project} />
    </div>
  );
}

// ==================== VACUUM TAB ====================
function VacuumTab() {
  const styles = {
    container: {
      textAlign: 'center',
      padding: '2rem',
    },
    icon: {
      fontSize: '4rem',
      marginBottom: '1rem',
    },
    title: {
      fontSize: '1.5rem',
      fontWeight: '700',
      color: '#2a3441',
      marginBottom: '0.5rem',
    },
    description: {
      color: '#5f6c7b',
      marginBottom: '1.5rem',
      maxWidth: '500px',
      margin: '0 auto 1.5rem',
      lineHeight: 1.6,
    },
    button: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.875rem 1.75rem',
      background: '#83b16d',
      border: 'none',
      borderRadius: '10px',
      color: 'white',
      fontSize: '1rem',
      fontWeight: '600',
      textDecoration: 'none',
      cursor: 'pointer',
      boxShadow: '0 2px 8px rgba(131, 177, 109, 0.3)',
      transition: 'transform 0.2s ease',
    },
    featureGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: '1rem',
      maxWidth: '600px',
      margin: '2rem auto 0',
      textAlign: 'left',
    },
    feature: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem',
      padding: '1rem',
      background: '#f8fafc',
      borderRadius: '8px',
    },
    featureIcon: {
      fontSize: '1.25rem',
    },
    featureText: {
      fontSize: '0.9rem',
      color: '#2a3441',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.icon}>🧹</div>
      <h2 style={styles.title}>Vacuum Extract</h2>
      <p style={styles.description}>
        Extract ALL data from complex files like PDF reports, payroll exports, and vendor files. 
        Parse now, understand later, learn forever.
      </p>
      
      <Link to="/vacuum" style={styles.button}>
        🚀 Open Vacuum Extractor
      </Link>

      <div style={styles.featureGrid}>
        <div style={styles.feature}>
          <span style={styles.featureIcon}>📤</span>
          <span style={styles.featureText}>Upload PDF, Excel, or CSV files</span>
        </div>
        <div style={styles.feature}>
          <span style={styles.featureIcon}>🔍</span>
          <span style={styles.featureText}>Explore extracted tables</span>
        </div>
        <div style={styles.feature}>
          <span style={styles.featureIcon}>🗺️</span>
          <span style={styles.featureText}>Map columns to standard fields</span>
        </div>
        <div style={styles.feature}>
          <span style={styles.featureIcon}>🧠</span>
          <span style={styles.featureText}>System learns your mappings</span>
        </div>
      </div>
    </div>
  );
}

// ==================== STATUS TAB ====================
function StatusTab({ project }) {
  return (
    <div>
      <Status selectedProject={project} />
    </div>
  );
}

// ==================== BROWSE TAB ====================
function BrowseTab() {
  const styles = {
    container: {
      textAlign: 'center',
      padding: '3rem',
      color: '#5f6c7b',
    },
    icon: {
      fontSize: '3rem',
      marginBottom: '1rem',
      opacity: 0.5,
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.icon}>🗂️</div>
      <h3>Browse Data</h3>
      <p>View and search uploaded data across all sources.</p>
      <p style={{ fontSize: '0.9rem', marginTop: '1rem', opacity: 0.7 }}>
        Coming soon - use Admin → Data Management for now.
      </p>
    </div>
  );
}
