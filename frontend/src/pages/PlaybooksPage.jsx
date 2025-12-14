/**
 * PlaybooksPage - Analysis Playbooks
 * 
 * POLISHED: Consistent loading, error states, and navigation patterns
 * 
 * - Run pre-built analysis playbooks against project data
 * - Create new playbooks via Playbook Builder
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useProject } from '../context/ProjectContext';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import YearEndPlaybook from '../components/YearEndPlaybook';
import { LoadingSpinner, ErrorState, EmptyState, PageHeader, Card } from '../components/ui';
import api from '../services/api';

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
    hasRunner: true,
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
function PlaybookCard({ playbook, onRun, hasProgress, isAssigned }) {
  const styles = {
    card: {
      background: 'white',
      borderRadius: '12px',
      padding: '1.5rem',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      border: playbook.hasRunner ? `2px solid ${COLORS.grassGreen}` : '1px solid #e1e8ed',
      transition: 'all 0.2s ease',
      cursor: 'pointer',
      position: 'relative',
    },
    badge: {
      position: 'absolute',
      top: '0.75rem',
      right: '0.75rem',
      background: hasProgress ? '#FFEB9C' : '#C6EFCE',
      color: hasProgress ? '#9C6500' : '#006600',
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
      cursor: playbook.hasRunner ? 'pointer' : 'default',
      opacity: playbook.hasRunner ? 1 : 0.7,
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
      {playbook.hasRunner && isAssigned && (
        <span style={styles.badge}>
          {hasProgress ? 'IN PROGRESS' : 'LIVE'}
        </span>
      )}
      
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
          disabled={!playbook.hasRunner}
        >
          {playbook.hasRunner ? (hasProgress ? 'Continue →' : 'Kickoff →') : 'Coming Soon'}
        </button>
      </div>
    </div>
  );
}

export default function PlaybooksPage() {
  const { activeProject, projectName, customerName, hasActiveProject, loading: projectLoading } = useProject();
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [activePlaybook, setActivePlaybook] = useState(null);
  const [playbookProgress, setPlaybookProgress] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPlaybookProgress = useCallback(async () => {
    if (!activeProject?.id) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const res = await api.get(`/playbooks/year-end/progress/${activeProject.id}`);
      const progress = res.data?.progress || {};
      const hasStarted = Object.keys(progress).length > 0;
      setPlaybookProgress(prev => ({ ...prev, 'year-end-checklist': hasStarted }));
    } catch (err) {
      // Don't show error for 404 (no progress yet)
      if (err.response?.status !== 404) {
        console.error('Failed to fetch playbook progress:', err);
      }
      setPlaybookProgress(prev => ({ ...prev, 'year-end-checklist': false }));
    } finally {
      setLoading(false);
    }
  }, [activeProject?.id]);

  useEffect(() => {
    fetchPlaybookProgress();
  }, [fetchPlaybookProgress]);

  // Loading state
  if (projectLoading || loading) {
    return <LoadingSpinner fullPage message="Loading playbooks..." />;
  }

  // No project selected
  if (!hasActiveProject) {
    return (
      <EmptyState
        fullPage
        icon="📋"
        title="Select a Project First"
        description="Choose a project from the selector above to run playbooks."
        action={{ label: 'Go to Projects', to: '/projects' }}
      />
    );
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

  // Get assigned playbooks for this project
  const assignedPlaybookIds = activeProject?.playbooks || [];
  const availablePlaybooks = PLAYBOOKS.filter(p => assignedPlaybookIds.includes(p.id));

  // No playbooks assigned
  if (availablePlaybooks.length === 0) {
    return (
      <>
        <PageHeader
          title="Playbooks"
          subtitle="Run pre-built analysis templates to generate deliverables."
          breadcrumbs={[
            { label: customerName },
            { label: projectName },
          ]}
        />
        <EmptyState
          fullPage
          icon="📭"
          title="No Playbooks Assigned"
          description={
            isAdmin 
              ? "This project doesn't have any playbooks assigned yet. Go to Projects to assign playbooks."
              : "No playbooks have been assigned to this project. Contact your administrator to enable playbooks."
          }
          action={isAdmin ? { label: 'Manage Projects', to: '/projects' } : null}
        />
      </>
    );
  }

  const categories = ['all', ...new Set(availablePlaybooks.map(p => p.category))];
  const filteredPlaybooks = selectedCategory === 'all' 
    ? availablePlaybooks 
    : availablePlaybooks.filter(p => p.category === selectedCategory);

  const handleRunPlaybook = (playbook) => {
    if (playbook.hasRunner) {
      setActivePlaybook(playbook);
    } else {
      navigate('/workspace', { state: { playbook } });
    }
  };

  const styles = {
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
      transition: 'all 0.2s ease',
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
      <PageHeader
        title="Playbooks"
        subtitle="Run pre-built analysis templates to generate deliverables."
        breadcrumbs={[
          { label: customerName },
          { label: projectName },
        ]}
        action={isAdmin ? {
          label: 'Create Playbook',
          icon: '➕',
          to: '/playbook-builder',
        } : null}
      />

      {/* Error state (inline) */}
      {error && (
        <ErrorState
          compact
          title="Failed to load progress"
          message={error}
          onRetry={fetchPlaybookProgress}
        />
      )}

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
            hasProgress={playbookProgress[playbook.id] || false}
            isAssigned={true}
          />
        ))}
      </div>
    </div>
  );
}
