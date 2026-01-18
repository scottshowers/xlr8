/**
 * PlaybookRunner - Universal Playbook Execution Flow
 * 
 * Three-phase flow for ANY playbook:
 * 1. Data Sources Review - Confirm/fix data mappings before analysis
 * 2. Step Execution - Work through steps, run analysis, see findings
 * 3. Findings Review - Aggregate view, acknowledge/suppress, export
 * 
 * This replaces playbook-specific runners (like YearEndPlaybook) with
 * a universal component that works with any playbook definition.
 * 
 * Created: January 18, 2026
 */

import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import DataSourcesReview from './DataSourcesReview';
import PlaybookSteps from './PlaybookSteps';
import PlaybookFindings from './PlaybookFindings';
import { 
  ArrowLeft, Database, ListChecks, FileSearch, 
  CheckCircle, Loader2, AlertTriangle 
} from 'lucide-react';

// Mission Control Colors
const COLORS = {
  primary: '#83b16d',
  turkishSea: '#285390',
  text: '#1a2332',
  textMuted: '#64748b',
  border: '#e2e8f0',
  bg: '#f8fafc',
  white: '#ffffff',
  green: '#059669',
  greenBg: '#d1fae5',
  yellow: '#d97706',
  yellowBg: '#fef3c7',
  red: '#dc2626',
  redBg: '#fee2e2',
};

// Map frontend playbook IDs to backend IDs
const PLAYBOOK_ID_MAP = {
  'year-end-checklist': 'year-end',
  // Add other mappings as needed
};

const getBackendId = (frontendId) => PLAYBOOK_ID_MAP[frontendId] || frontendId;

// Phase definitions
const PHASES = {
  LOADING: 'loading',
  DATA_SOURCES: 'data-sources',
  EXECUTION: 'execution',
  FINDINGS: 'findings',
  ERROR: 'error'
};

const PHASE_CONFIG = {
  [PHASES.DATA_SOURCES]: {
    label: 'Data Sources',
    icon: Database,
    description: 'Review and confirm data mappings'
  },
  [PHASES.EXECUTION]: {
    label: 'Execute Steps',
    icon: ListChecks,
    description: 'Run analysis step by step'
  },
  [PHASES.FINDINGS]: {
    label: 'Review Findings',
    icon: FileSearch,
    description: 'Review and act on findings'
  }
};

export default function PlaybookRunner({ 
  playbook,        // Playbook metadata (id, name, etc.)
  project,         // Active project
  projectName,
  customerName,
  onClose          // Callback to exit runner
}) {
  // Core state
  const [phase, setPhase] = useState(PHASES.LOADING);
  const [error, setError] = useState(null);
  
  // Framework state
  const [instanceId, setInstanceId] = useState(null);
  const [definition, setDefinition] = useState(null);
  const [progress, setProgress] = useState({});
  
  // Data sources state
  const [resolutions, setResolutions] = useState({});
  const [hasUnresolved, setHasUnresolved] = useState(false);
  
  // Findings state
  const [allFindings, setAllFindings] = useState([]);

  // =========================================================================
  // INITIALIZATION
  // =========================================================================
  
  useEffect(() => {
    if (project?.id && playbook?.id) {
      initializePlaybook();
    }
  }, [project?.id, playbook?.id]);

  const initializePlaybook = async () => {
    setPhase(PHASES.LOADING);
    setError(null);
    
    const backendId = getBackendId(playbook?.id);
    
    try {
      // 1. Get or create framework instance
      const instanceRes = await api.post(`/playbooks/${backendId}/instance/${project.id}`, {
        create_if_missing: true
      });
      
      if (!instanceRes.data?.instance_id) {
        throw new Error('Failed to create playbook instance');
      }
      
      setInstanceId(instanceRes.data.instance_id);
      console.log('[RUNNER] Instance:', instanceRes.data.instance_id);
      
      // 2. Load playbook definition (steps, analysis configs)
      const defRes = await api.get(`/playbooks/${backendId}/definition`);
      
      if (!defRes.data?.playbook) {
        throw new Error('Failed to load playbook definition');
      }
      
      setDefinition(defRes.data.playbook);
      console.log('[RUNNER] Definition loaded:', defRes.data.playbook.name);
      
      // 3. Load current progress
      const progressRes = await api.get(`/playbooks/instance/${instanceRes.data.instance_id}/progress`);
      setProgress(progressRes.data?.progress || {});
      
      // 4. Load all resolutions to check status
      await loadAllResolutions(instanceRes.data.instance_id, defRes.data.playbook.steps);
      
      // 5. Move to data sources phase
      setPhase(PHASES.DATA_SOURCES);
      
    } catch (err) {
      console.error('[RUNNER] Initialization failed:', err);
      setError(err.message || 'Failed to initialize playbook');
      setPhase(PHASES.ERROR);
    }
  };

  const loadAllResolutions = async (instId, steps) => {
    const allResolutions = {};
    let anyUnresolved = false;
    
    for (const step of steps) {
      try {
        const res = await api.get(`/playbooks/instance/${instId}/step/${step.id}/resolve`);
        allResolutions[step.id] = res.data.resolutions || {};
        if (res.data.has_unresolved) {
          anyUnresolved = true;
        }
      } catch (err) {
        console.warn(`[RUNNER] Could not load resolutions for step ${step.id}:`, err);
      }
    }
    
    setResolutions(allResolutions);
    setHasUnresolved(anyUnresolved);
  };

  // =========================================================================
  // PHASE HANDLERS
  // =========================================================================
  
  const handleDataSourcesConfirmed = () => {
    setPhase(PHASES.EXECUTION);
  };

  const handleStepComplete = (stepId, findings) => {
    // Update progress
    setProgress(prev => ({
      ...prev,
      [stepId]: { ...prev[stepId], status: 'complete' }
    }));
    
    // Collect findings
    if (findings?.length > 0) {
      setAllFindings(prev => [...prev, ...findings.map(f => ({ ...f, stepId }))]);
    }
  };

  const handleAllStepsComplete = () => {
    setPhase(PHASES.FINDINGS);
  };

  const handleBackToSteps = () => {
    setPhase(PHASES.EXECUTION);
  };

  // =========================================================================
  // RENDER
  // =========================================================================
  
  const styles = {
    container: {
      minHeight: '100vh',
      background: COLORS.bg,
    },
    header: {
      background: COLORS.white,
      borderBottom: `1px solid ${COLORS.border}`,
      padding: '1rem 1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    },
    headerLeft: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
    },
    backBtn: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.5rem 0.75rem',
      background: 'transparent',
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      cursor: 'pointer',
      fontSize: '0.85rem',
      color: COLORS.textMuted,
    },
    title: {
      fontSize: '1.25rem',
      fontWeight: '600',
      color: COLORS.text,
    },
    subtitle: {
      fontSize: '0.85rem',
      color: COLORS.textMuted,
    },
    phaseNav: {
      display: 'flex',
      gap: '0.5rem',
    },
    phaseTab: (isActive, isComplete) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.5rem 1rem',
      background: isActive ? COLORS.primary : isComplete ? COLORS.greenBg : COLORS.bg,
      color: isActive ? COLORS.white : isComplete ? COLORS.green : COLORS.textMuted,
      border: 'none',
      borderRadius: '6px',
      fontSize: '0.85rem',
      fontWeight: '500',
      cursor: 'default',
    }),
    content: {
      padding: '1.5rem',
      maxWidth: '1200px',
      margin: '0 auto',
    },
    loading: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '4rem',
      gap: '1rem',
    },
    error: {
      background: COLORS.redBg,
      border: `1px solid ${COLORS.red}`,
      borderRadius: '8px',
      padding: '1.5rem',
      margin: '2rem',
      textAlign: 'center',
    },
    errorTitle: {
      color: COLORS.red,
      fontWeight: '600',
      fontSize: '1.1rem',
      marginBottom: '0.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.5rem',
    },
    errorMessage: {
      color: COLORS.text,
      fontSize: '0.9rem',
    },
    retryBtn: {
      marginTop: '1rem',
      padding: '0.5rem 1rem',
      background: COLORS.red,
      color: COLORS.white,
      border: 'none',
      borderRadius: '6px',
      cursor: 'pointer',
      fontSize: '0.85rem',
    },
  };

  // Determine which phases are complete
  const isDataSourcesComplete = phase !== PHASES.DATA_SOURCES && phase !== PHASES.LOADING;
  const isExecutionComplete = phase === PHASES.FINDINGS;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <button style={styles.backBtn} onClick={onClose}>
            <ArrowLeft size={16} />
            Back
          </button>
          <div>
            <div style={styles.title}>{playbook?.name || 'Playbook'}</div>
            <div style={styles.subtitle}>
              {customerName} • {projectName}
            </div>
          </div>
        </div>
        
        {/* Phase Navigation */}
        {phase !== PHASES.LOADING && phase !== PHASES.ERROR && (
          <div style={styles.phaseNav}>
            {Object.entries(PHASE_CONFIG).map(([key, config]) => {
              const Icon = config.icon;
              const isActive = phase === key;
              const isComplete = (key === PHASES.DATA_SOURCES && isDataSourcesComplete) ||
                                (key === PHASES.EXECUTION && isExecutionComplete);
              
              return (
                <div key={key} style={styles.phaseTab(isActive, isComplete)}>
                  {isComplete && !isActive ? <CheckCircle size={16} /> : <Icon size={16} />}
                  {config.label}
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      {/* Content */}
      <div style={styles.content}>
        {/* Loading */}
        {phase === PHASES.LOADING && (
          <div style={styles.loading}>
            <Loader2 size={32} className="spin" color={COLORS.primary} />
            <div style={{ color: COLORS.textMuted }}>Loading playbook...</div>
          </div>
        )}
        
        {/* Error */}
        {phase === PHASES.ERROR && (
          <div style={styles.error}>
            <div style={styles.errorTitle}>
              <AlertTriangle size={20} />
              Failed to Load Playbook
            </div>
            <div style={styles.errorMessage}>{error}</div>
            <button style={styles.retryBtn} onClick={initializePlaybook}>
              Try Again
            </button>
          </div>
        )}
        
        {/* Phase 1: Data Sources Review */}
        {phase === PHASES.DATA_SOURCES && (
          <DataSourcesReview
            instanceId={instanceId}
            definition={definition}
            projectId={project.id}
            resolutions={resolutions}
            hasUnresolved={hasUnresolved}
            onResolutionChange={(stepId, newResolutions) => {
              setResolutions(prev => ({ ...prev, [stepId]: newResolutions }));
              // Recheck if any unresolved
              const stillUnresolved = Object.values({ ...resolutions, [stepId]: newResolutions })
                .some(stepRes => Object.values(stepRes).some(r => !r.resolved_table));
              setHasUnresolved(stillUnresolved);
            }}
            onConfirm={handleDataSourcesConfirmed}
            onBack={onClose}
          />
        )}
        
        {/* Phase 2: Step Execution */}
        {phase === PHASES.EXECUTION && (
          <PlaybookSteps
            instanceId={instanceId}
            definition={definition}
            projectId={project.id}
            progress={progress}
            onStepComplete={handleStepComplete}
            onAllComplete={handleAllStepsComplete}
            onBack={() => setPhase(PHASES.DATA_SOURCES)}
          />
        )}
        
        {/* Phase 3: Findings Review */}
        {phase === PHASES.FINDINGS && (
          <PlaybookFindings
            instanceId={instanceId}
            definition={definition}
            projectId={project.id}
            findings={allFindings}
            onBack={handleBackToSteps}
            onClose={onClose}
          />
        )}
      </div>
      
      <style>{`
        .spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
