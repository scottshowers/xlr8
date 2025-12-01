/**
 * PlaybooksPage - Analysis Playbooks
 * 
 * This is where:
 * - Run pre-built analysis playbooks against project data
 * - Create new playbooks from successful ad-hoc analysis
 * 
 * Playbooks are "recipes" that combine:
 * - Questions to answer
 * - Data sources to use
 * - Output structure (workbook format)
 */

import React, { useState } from 'react';
import { useProject } from '../context/ProjectContext';
import { useNavigate } from 'react-router-dom';
import YearEndPlaybook from '../components/YearEndPlaybook';

// Brand Colors
const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  white: '#f6f5fa',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

// Playbook Definitions
const PLAYBOOKS = [
  {
    id: 'year-end-checklist',
    name: 'Year-End Checklist',
    description: 'Comprehensive year-end processing workbook. Analyzes tax setup, earnings/deductions, outstanding items, and generates action-centric checklist with findings and required actions.',
    category: 'Year-End',
    icon: '📅',
    modules: ['Payroll', 'Tax', 'Benefits'],
    outputs: ['Action Checklist', 'Tax Verification', 'Earnings Analysis', 'Deductions Review', 'Outstanding Items', 'Arrears Summary'],
    estimatedTime: '5-15 minutes',
    dataRequired: ['Company Tax Verification', 'Earnings Codes', 'Deduction Codes', 'Workers Comp Rates'],
    hasRunner: true, // Has dedicated runner component
  },
  {
    id: 'secure-2.0',
    name: 'SECURE 2.0 Compliance',
    description: 'Analyze retirement plan configurations against SECURE 2.0 requirements. Identifies gaps, generates compliance checklist, and provides configuration recommendations.',
    category: 'Compliance',
    icon: '🏛️',
    modules: ['Payroll', 'Benefits'],
    outputs: ['Executive Summary', 'Gap Analysis', 'Configuration Guide', 'Action Items'],
    estimatedTime: '5-10 minutes',
    dataRequired: ['Employee Census', 'Benefit Plans', 'Deduction Codes'],
    hasRunner: false,
  },
  {
    id: 'one-big-bill',
    name: 'One Big Beautiful Bill',
    description: 'Comprehensive analysis of tax and regulatory changes impact on your configuration. Generates complete documentation package for customer review.',
    category: 'Regulatory',
    icon: '📜',
    modules: ['Payroll', 'Tax'],
    outputs: ['Executive Summary', 'Detailed Next Steps', 'Configuration Guide', 'High Priority Items', 'Import Templates'],
    estimatedTime: '10-15 minutes',
    dataRequired: ['Tax Groups', 'Earning Codes', 'Employee Data'],
    hasRunner: false,
  },
  {
    id: 'payroll-audit',
    name: 'Payroll Configuration Audit',
    description: 'Deep dive into payroll setup. Identifies inconsistencies, missing configurations, and optimization opportunities.',
    category: 'Audit',
    icon: '🔍',
    modules: ['Payroll'],
    outputs: ['Audit Report', 'Issue List', 'Recommendations', 'Best Practices'],
    estimatedTime: '8-12 minutes',
    dataRequired: ['Earning Codes', 'Deduction Codes', 'Pay Groups', 'Tax Setup'],
    hasRunner: false,
  },
  {
    id: 'data-validation',
    name: 'Pre-Load Data Validation',
    description: 'Validate employee conversion data before loading. Checks required fields, formats, cross-references, and business rules.',
    category: 'Implementation',
    icon: '✅',
    modules: ['All'],
    outputs: ['Validation Report', 'Error List', 'Warning List', 'Ready-to-Load Files'],
    estimatedTime: '3-5 minutes',
    dataRequired: ['Employee Load Template'],
    hasRunner: false,
  },
];

// Playbook Card Component
function PlaybookCard({ playbook, onRun, isActive }) {
  const styles = {
    card: {
      background: 'white',
      borderRadius: '12px',
      padding: '1.5rem',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      border: isActive ? `2px solid ${COLORS.grassGreen}` : '1px solid #e1e8ed',
      transition: 'all 0.2s ease',
      cursor: 'pointer',
      position: 'relative',
    },
    activeBadge: {
      position: 'absolute',
      top: '0.75rem',
      right: '0.75rem',
      background: COLORS.grassGreen,
      color: 'white',
      fontSize: '0.7rem',
      fontWeight: '700',
      padding: '0.2rem 0.5rem',
      borderRadius: '4px',
    },
    header: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '1rem',
      marginBottom: '1rem',
    },
    icon: {
      fontSize: '2rem',
      width: '48px',
      height: '48px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: COLORS.iceFlow,
      borderRadius: '10px',
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.1rem',
      fontWeight: '700',
      color: COLORS.text,
      marginBottom: '0.25rem',
    },
    category: {
      fontSize: '0.75rem',
      color: COLORS.grassGreen,
      fontWeight: '600',
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
    },
    description: {
      color: COLORS.textLight,
      fontSize: '0.9rem',
      lineHeight: '1.5',
      marginBottom: '1rem',
    },
    meta: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '0.5rem',
      marginBottom: '1rem',
    },
    tag: {
      fontSize: '0.75rem',
      padding: '0.25rem 0.5rem',
      background: '#f0f4f7',
      borderRadius: '4px',
      color: COLORS.textLight,
    },
    footer: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      paddingTop: '1rem',
      borderTop: '1px solid #e1e8ed',
    },
    time: {
      fontSize: '0.8rem',
      color: COLORS.textLight,
    },
    button: {
      padding: '0.5rem 1rem',
      background: playbook.hasRunner ? COLORS.grassGreen : COLORS.textLight,
      border: 'none',
      borderRadius: '6px',
      color: 'white',
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
    },
  };

  return (
    <div 
      style={styles.card}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 4px 12px rgba(42, 52, 65, 0.12)';
        e.currentTarget.style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = '0 1px 3px rgba(42, 52, 65, 0.08)';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      {playbook.hasRunner && <span style={styles.activeBadge}>LIVE</span>}
      
      <div style={styles.header}>
        <div style={styles.icon}>{playbook.icon}</div>
        <div>
          <h3 style={styles.title}>{playbook.name}</h3>
          <span style={styles.category}>{playbook.category}</span>
        </div>
      </div>

      <p style={styles.description}>{playbook.description}</p>

      <div style={styles.meta}>
        {playbook.modules.map(m => (
          <span key={m} style={styles.tag}>{m}</span>
        ))}
      </div>

      <div style={styles.footer}>
        <span style={styles.time}>⏱️ {playbook.estimatedTime}</span>
        <button 
          style={styles.button} 
          onClick={() => onRun(playbook)}
        >
          {playbook.hasRunner ? 'Run Playbook →' : 'Coming Soon'}
        </button>
      </div>
    </div>
  );
}

// Create Playbook Modal (simplified for now)
function CreatePlaybookPrompt({ onClose }) {
  const styles = {
    overlay: {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(42, 52, 65, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
    },
    modal: {
      background: 'white',
      borderRadius: '16px',
      padding: '2rem',
      maxWidth: '500px',
      width: '90%',
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.25rem',
      fontWeight: '700',
      marginBottom: '1rem',
    },
    text: {
      color: COLORS.textLight,
      lineHeight: '1.6',
      marginBottom: '1.5rem',
    },
    button: {
      padding: '0.75rem 1.5rem',
      background: COLORS.textLight,
      border: 'none',
      borderRadius: '8px',
      color: 'white',
      fontWeight: '600',
      cursor: 'pointer',
    },
  };

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h2 style={styles.title}>🚧 Coming Soon</h2>
        <p style={styles.text}>
          The ability to create custom playbooks from successful ad-hoc analyses is coming soon.
          <br /><br />
          For now, use the <strong>Workspace</strong> for ad-hoc analysis, and these Playbooks for structured deliverables.
        </p>
        <button style={styles.button} onClick={onClose}>Got it</button>
      </div>
    </div>
  );
}

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
      <div style={{ fontSize: '4rem', marginBottom: '1.5rem', opacity: 0.6 }}>📋</div>
      <h2 style={{
        fontFamily: "'Sora', sans-serif",
        fontSize: '1.5rem',
        fontWeight: '700',
        color: COLORS.text,
        marginBottom: '0.75rem',
      }}>Select a Project First</h2>
      <p style={{
        color: COLORS.textLight,
        fontSize: '1rem',
        maxWidth: '400px',
        lineHeight: '1.6',
      }}>
        Choose a project from the selector above to run playbooks.
      </p>
    </div>
  );
}

export default function PlaybooksPage() {
  const { activeProject, projectName, customerName, hasActiveProject, loading } = useProject();
  const navigate = useNavigate();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [activePlaybook, setActivePlaybook] = useState(null);

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

  // If a playbook runner is active, show it
  if (activePlaybook) {
    if (activePlaybook.id === 'year-end-checklist') {
      return (
        <YearEndPlaybook 
          project={activeProject}
          projectName={projectName}
          customerName={customerName}
          onClose={() => setActivePlaybook(null)}
        />
      );
    }
  }

  const categories = ['all', ...new Set(PLAYBOOKS.map(p => p.category))];
  const filteredPlaybooks = selectedCategory === 'all' 
    ? PLAYBOOKS 
    : PLAYBOOKS.filter(p => p.category === selectedCategory);

  const handleRunPlaybook = (playbook) => {
    if (playbook.hasRunner) {
      // Open dedicated runner
      setActivePlaybook(playbook);
    } else {
      // Coming soon - navigate to workspace with context (placeholder)
      navigate('/workspace', { state: { playbook } });
    }
  };

  const styles = {
    header: {
      marginBottom: '1.5rem',
    },
    breadcrumb: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '0.85rem',
      color: COLORS.textLight,
      marginBottom: '0.5rem',
    },
    titleRow: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.75rem',
      fontWeight: '700',
      color: COLORS.text,
      margin: 0,
    },
    subtitle: {
      color: COLORS.textLight,
      marginTop: '0.25rem',
    },
    createButton: {
      padding: '0.75rem 1.25rem',
      background: 'white',
      border: `2px solid ${COLORS.grassGreen}`,
      borderRadius: '8px',
      color: COLORS.grassGreen,
      fontWeight: '600',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    filters: {
      display: 'flex',
      gap: '0.5rem',
      marginBottom: '1.5rem',
      flexWrap: 'wrap',
    },
    filterButton: (active) => ({
      padding: '0.5rem 1rem',
      background: active ? COLORS.grassGreen : '#f0f4f7',
      border: 'none',
      borderRadius: '20px',
      color: active ? 'white' : COLORS.textLight,
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
    }),
    grid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
      gap: '1.5rem',
    },
  };

  return (
    <div>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.breadcrumb}>
          <span>{customerName}</span>
          <span>→</span>
          <span style={{ color: COLORS.grassGreen, fontWeight: '600' }}>{projectName}</span>
        </div>
        <div style={styles.titleRow}>
          <div>
            <h1 style={styles.title}>Playbooks</h1>
            <p style={styles.subtitle}>
              Run pre-built analysis templates to generate deliverables.
            </p>
          </div>
          <button style={styles.createButton} onClick={() => setShowCreateModal(true)}>
            ➕ Create Playbook
          </button>
        </div>
      </div>

      {/* Category Filters */}
      <div style={styles.filters}>
        {categories.map(cat => (
          <button
            key={cat}
            style={styles.filterButton(selectedCategory === cat)}
            onClick={() => setSelectedCategory(cat)}
          >
            {cat === 'all' ? 'All Playbooks' : cat}
          </button>
        ))}
      </div>

      {/* Playbooks Grid */}
      <div style={styles.grid}>
        {filteredPlaybooks.map(playbook => (
          <PlaybookCard 
            key={playbook.id} 
            playbook={playbook} 
            onRun={handleRunPlaybook}
            isActive={playbook.hasRunner}
          />
        ))}
      </div>

      {/* Create Modal */}
      {showCreateModal && <CreatePlaybookPrompt onClose={() => setShowCreateModal(false)} />}
    </div>
  );
}
