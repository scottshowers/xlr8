/**
 * PlaybookSelectPage.jsx - Step 3: Select Playbooks + Data Source Review
 * 
 * Two-phase flow:
 * 1. Select which playbook to run
 * 2. Review/confirm data source mappings (via DataSourcesReview)
 * 
 * After confirmation, navigates to Step 4 (Processing) with instance_id.
 * 
 * Updated: January 18, 2026 - Integrated with Playbook Framework
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  BookOpen, Check, ChevronRight, ChevronLeft, Calendar, Shield, 
  Search, RefreshCw, Zap, ClipboardList, Database, Loader2,
  AlertTriangle, ArrowRight
} from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import DataSourcesReview from '../components/DataSourcesReview';
import api from '../services/api';

// =============================================================================
// CONSTANTS
// =============================================================================

const COLORS = {
  primary: '#83b16d',
  primaryLight: 'rgba(131, 177, 109, 0.1)',
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

const CATEGORY_ICONS = {
  'year-end': Calendar,
  'data-quality': Search,
  'compliance': Shield,
  'migration': RefreshCw,
  'optimization': Zap,
  'audit': ClipboardList,
  'vendor': BookOpen,
  'default': BookOpen,
};

// Fallback playbooks if API not available
const FALLBACK_PLAYBOOKS = [
  { 
    id: 'year-end', 
    name: 'Year-End Checklist', 
    description: 'W-2 validation, tax compliance, payroll reconciliation', 
    category: 'year-end', 
    type: 'vendor',
    available: true
  },
];

// =============================================================================
// PHASES
// =============================================================================

const PHASES = {
  SELECT: 'select',
  REVIEW: 'review',
};

// =============================================================================
// PLAYBOOK CARD COMPONENT
// =============================================================================

function PlaybookCard({ playbook, isSelected, onSelect }) {
  const Icon = CATEGORY_ICONS[playbook.category] || CATEGORY_ICONS[playbook.type] || CATEGORY_ICONS.default;
  
  const styles = {
    card: {
      background: isSelected ? COLORS.primaryLight : COLORS.white,
      border: `2px solid ${isSelected ? COLORS.primary : COLORS.border}`,
      borderRadius: '12px',
      padding: '1.25rem',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      position: 'relative',
    },
    header: {
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      marginBottom: '0.75rem',
    },
    iconWrap: {
      width: '40px',
      height: '40px',
      borderRadius: '10px',
      background: isSelected ? COLORS.primary : COLORS.bg,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: isSelected ? COLORS.white : COLORS.primary,
    },
    checkWrap: {
      width: '24px',
      height: '24px',
      borderRadius: '50%',
      background: isSelected ? COLORS.primary : COLORS.border,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: COLORS.white,
    },
    name: {
      fontSize: '1.1rem',
      fontWeight: '600',
      color: COLORS.text,
      marginBottom: '0.5rem',
    },
    desc: {
      fontSize: '0.9rem',
      color: COLORS.textMuted,
      lineHeight: 1.5,
    },
  };

  return (
    <div style={styles.card} onClick={() => onSelect(playbook)}>
      <div style={styles.header}>
        <div style={styles.iconWrap}>
          <Icon size={20} />
        </div>
        <div style={styles.checkWrap}>
          {isSelected && <Check size={14} />}
        </div>
      </div>
      <h4 style={styles.name}>{playbook.name}</h4>
      <p style={styles.desc}>{playbook.description || 'Analysis playbook'}</p>
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function PlaybookSelectPage() {
  const navigate = useNavigate();
  const { activeProject } = useProject();
  
  // Phase state
  const [phase, setPhase] = useState(PHASES.SELECT);
  
  // Selection phase state
  const [playbooks, setPlaybooks] = useState([]);
  const [selectedPlaybook, setSelectedPlaybook] = useState(null);
  const [loadingPlaybooks, setLoadingPlaybooks] = useState(true);
  
  // Review phase state
  const [instanceId, setInstanceId] = useState(null);
  const [definition, setDefinition] = useState(null);
  const [resolutions, setResolutions] = useState({});
  const [loadingInstance, setLoadingInstance] = useState(false);
  
  // General state
  const [error, setError] = useState(null);

  // =========================================================================
  // LOAD PLAYBOOKS
  // =========================================================================
  
  useEffect(() => {
    fetchPlaybooks();
  }, []);

  const fetchPlaybooks = async () => {
    setLoadingPlaybooks(true);
    setError(null);
    
    try {
      // Try the framework endpoint first
      const res = await api.get('/playbooks/list');
      if (res.data?.playbooks && res.data.playbooks.length > 0) {
        setPlaybooks(res.data.playbooks);
      } else {
        // Fall back to templates endpoint
        const templatesRes = await api.get('/playbooks/templates');
        if (templatesRes.data?.templates) {
          setPlaybooks(templatesRes.data.templates);
        } else {
          setPlaybooks(FALLBACK_PLAYBOOKS);
        }
      }
    } catch (err) {
      console.warn('Failed to load playbooks, using fallback:', err);
      setPlaybooks(FALLBACK_PLAYBOOKS);
    } finally {
      setLoadingPlaybooks(false);
    }
  };

  // =========================================================================
  // HANDLE PLAYBOOK SELECTION -> MOVE TO REVIEW
  // =========================================================================
  
  const handleSelectPlaybook = (playbook) => {
    setSelectedPlaybook(playbook);
  };

  const handleContinueToReview = async () => {
    if (!selectedPlaybook || !activeProject?.id) {
      setError('Please select a playbook');
      return;
    }

    setLoadingInstance(true);
    setError(null);

    try {
      // 1. Create/get instance
      const instanceRes = await api.post(
        `/playbooks/${selectedPlaybook.id}/instance/${activeProject.id}`,
        { create_if_missing: true }
      );
      
      const newInstanceId = instanceRes.data.instance_id;
      setInstanceId(newInstanceId);

      // 2. Load playbook definition
      const defRes = await api.get(`/playbooks/${selectedPlaybook.id}/definition`);
      const playbook = defRes.data.playbook;
      setDefinition(playbook);

      // 3. Load resolutions for all steps in parallel (batched)
      const allResolutions = {};
      const resolvePromises = playbook.steps.map(async (step) => {
        try {
          const resolveRes = await api.get(
            `/playbooks/instance/${newInstanceId}/step/${encodeURIComponent(step.id)}/resolve`
          );
          return { stepId: step.id, resolutions: resolveRes.data.resolutions || {} };
        } catch (err) {
          console.warn(`Failed to get resolutions for step ${step.id}:`, err);
          return { stepId: step.id, resolutions: {} };
        }
      });
      
      const results = await Promise.all(resolvePromises);
      results.forEach(({ stepId, resolutions: stepRes }) => {
        allResolutions[stepId] = stepRes;
      });
      setResolutions(allResolutions);

      // 4. Move to review phase
      setPhase(PHASES.REVIEW);

    } catch (err) {
      console.error('Failed to initialize playbook:', err);
      setError(err.response?.data?.detail || 'Failed to initialize playbook');
    } finally {
      setLoadingInstance(false);
    }
  };

  // =========================================================================
  // HANDLE RESOLUTION CHANGES
  // =========================================================================
  
  const handleResolutionChange = useCallback((stepId, newStepResolutions) => {
    setResolutions(prev => ({
      ...prev,
      [stepId]: newStepResolutions
    }));
  }, []);

  // =========================================================================
  // CHECK IF ALL RESOLVED
  // =========================================================================
  
  const hasUnresolved = useCallback(() => {
    if (!definition?.steps) return false;
    
    for (const step of definition.steps) {
      const stepRes = resolutions[step.id] || {};
      for (const placeholder of Object.keys(stepRes)) {
        const res = stepRes[placeholder];
        if (!res?.resolved_table) {
          return true;
        }
      }
    }
    return false;
  }, [definition, resolutions]);

  // =========================================================================
  // HANDLE CONFIRM -> NAVIGATE TO PROCESSING
  // =========================================================================
  
  const handleConfirm = () => {
    if (!instanceId) {
      setError('No instance created');
      return;
    }
    
    // Navigate to Step 4 with instance_id
    navigate(`/processing/${instanceId}`);
  };

  // =========================================================================
  // HANDLE BACK
  // =========================================================================
  
  const handleBack = () => {
    if (phase === PHASES.REVIEW) {
      setPhase(PHASES.SELECT);
      setInstanceId(null);
      setDefinition(null);
      setResolutions({});
    } else {
      navigate('/data');
    }
  };

  // =========================================================================
  // STYLES
  // =========================================================================
  
  const styles = {
    container: {
      maxWidth: '1000px',
      margin: '0 auto',
      padding: '1.5rem',
    },
    header: {
      marginBottom: '2rem',
    },
    title: {
      fontSize: '1.75rem',
      fontWeight: '600',
      color: COLORS.text,
      marginBottom: '0.5rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
    },
    subtitle: {
      fontSize: '1rem',
      color: COLORS.textMuted,
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
      gap: '1rem',
      marginBottom: '2rem',
    },
    footer: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '1rem 0',
      borderTop: `1px solid ${COLORS.border}`,
    },
    btn: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.75rem 1.5rem',
      borderRadius: '8px',
      fontSize: '1rem',
      fontWeight: '600',
      cursor: 'pointer',
      border: 'none',
      transition: 'all 0.2s ease',
    },
    btnPrimary: {
      background: COLORS.primary,
      color: COLORS.white,
    },
    btnSecondary: {
      background: 'transparent',
      color: COLORS.textMuted,
      border: `1px solid ${COLORS.border}`,
    },
    btnDisabled: {
      opacity: 0.5,
      cursor: 'not-allowed',
    },
    error: {
      padding: '1rem',
      background: COLORS.redBg,
      color: COLORS.red,
      borderRadius: '8px',
      marginBottom: '1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    loading: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '4rem 2rem',
      color: COLORS.textMuted,
      gap: '1rem',
    },
    selectedInfo: {
      padding: '0.75rem 1rem',
      background: COLORS.primaryLight,
      borderRadius: '8px',
      color: COLORS.text,
      fontWeight: '500',
    },
  };

  // =========================================================================
  // RENDER: LOADING STATE
  // =========================================================================
  
  if (loadingPlaybooks) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <Loader2 size={32} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
          <span>Loading playbooks...</span>
        </div>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // =========================================================================
  // RENDER: REVIEW PHASE (DataSourcesReview)
  // =========================================================================
  
  if (phase === PHASES.REVIEW) {
    if (loadingInstance) {
      return (
        <div style={styles.container}>
          <div style={styles.loading}>
            <Loader2 size={32} style={{ animation: 'spin 1s linear infinite' }} />
            <span>Initializing playbook and resolving data sources...</span>
          </div>
          <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        </div>
      );
    }

    return (
      <div style={styles.container}>
        {error && (
          <div style={styles.error}>
            <AlertTriangle size={18} />
            {error}
          </div>
        )}
        
        <DataSourcesReview
          instanceId={instanceId}
          definition={definition}
          projectId={activeProject?.id}
          resolutions={resolutions}
          hasUnresolved={hasUnresolved()}
          onResolutionChange={handleResolutionChange}
          onConfirm={handleConfirm}
          onBack={handleBack}
        />
      </div>
    );
  }

  // =========================================================================
  // RENDER: SELECT PHASE
  // =========================================================================
  
  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>
          <ClipboardList size={28} />
          Select Playbook
        </h1>
        <p style={styles.subtitle}>
          Choose which analysis to run{activeProject ? ` for ${activeProject.customer || activeProject.name}` : ''}
        </p>
      </div>

      {/* Error */}
      {error && (
        <div style={styles.error}>
          <AlertTriangle size={18} />
          {error}
        </div>
      )}

      {/* Playbook Grid */}
      <div style={styles.grid}>
        {playbooks.map(playbook => (
          <PlaybookCard
            key={playbook.id}
            playbook={playbook}
            isSelected={selectedPlaybook?.id === playbook.id}
            onSelect={handleSelectPlaybook}
          />
        ))}
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        <button
          style={{ ...styles.btn, ...styles.btnSecondary }}
          onClick={() => navigate('/data')}
        >
          <ChevronLeft size={18} />
          Back to Data
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {selectedPlaybook && (
            <span style={styles.selectedInfo}>
              Selected: {selectedPlaybook.name}
            </span>
          )}
          
          <button
            style={{
              ...styles.btn,
              ...styles.btnPrimary,
              ...((!selectedPlaybook || loadingInstance) ? styles.btnDisabled : {})
            }}
            onClick={handleContinueToReview}
            disabled={!selectedPlaybook || loadingInstance}
          >
            {loadingInstance ? (
              <>
                <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                Loading...
              </>
            ) : (
              <>
                Configure Data Sources
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
