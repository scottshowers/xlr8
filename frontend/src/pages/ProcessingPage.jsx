/**
 * ProcessingPage.jsx - Auto-Analysis Feedback Screen
 * ===================================================
 *
 * Phase 4A.3: Processing Feedback
 *
 * Shows visual progress during data analysis with:
 * - Animated spinner
 * - Step indicators (Schema Detection → Data Profiling → Pattern Analysis → Finding Generation)
 * - Cost Equivalent banner
 * - Auto-redirect to Findings Dashboard when complete
 *
 * Matches mockup Screen 3 design.
 *
 * Created: January 15, 2026
 */

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Loader2, CheckCircle, Circle, ArrowRight } from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

// =============================================================================
// COLORS
// =============================================================================

const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f6f5fa',
  card: dark ? '#242b3d' : '#ffffff',
  border: dark ? '#2d3548' : '#e1e8ed',
  text: dark ? '#e8eaed' : '#2a3441',
  textMuted: dark ? '#8b95a5' : '#5f6c7b',
  primary: '#83b16d',
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.08)',
  primaryBorder: dark ? 'rgba(131, 177, 109, 0.4)' : 'rgba(131, 177, 109, 0.25)',
  electricBlue: '#2766b1',
});

// =============================================================================
// PROCESSING STEPS
// =============================================================================

const PROCESSING_STEPS = [
  { id: 'schema', label: 'Schema Detection', description: 'Identifying tables and columns' },
  { id: 'profiling', label: 'Data Profiling', description: 'Analyzing data quality' },
  { id: 'patterns', label: 'Pattern Analysis', description: 'Finding anomalies' },
  { id: 'findings', label: 'Finding Generation', description: 'Creating recommendations' },
];

// =============================================================================
// STEP INDICATOR COMPONENT
// =============================================================================

function ProcessingStep({ step, status, colors }) {
  const getStepStyle = () => {
    switch (status) {
      case 'complete':
        return {
          iconBg: colors.primary,
          iconColor: '#fff',
          textColor: colors.primary,
          symbol: '✓'
        };
      case 'active':
        return {
          iconBg: colors.electricBlue,
          iconColor: '#fff',
          textColor: colors.electricBlue,
          symbol: '⋯'
        };
      default:
        return {
          iconBg: colors.border,
          iconColor: colors.textMuted,
          textColor: colors.textMuted,
          symbol: '○'
        };
    }
  };

  const style = getStepStyle();

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      color: style.textColor,
    }}>
      <div style={{
        width: 24,
        height: 24,
        borderRadius: '50%',
        background: style.iconBg,
        color: style.iconColor,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '0.75rem',
        fontWeight: 600,
      }}>
        {style.symbol}
      </div>
      <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>
        {step.label}
      </span>
    </div>
  );
}

// =============================================================================
// COST EQUIVALENT BANNER
// =============================================================================

function CostEquivalentBanner({ records, tables, hours, cost, colors, title, subtitle }) {
  return (
    <div style={{
      background: colors.primaryLight,
      border: `1px solid ${colors.primaryBorder}`,
      borderRadius: 12,
      padding: '1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: '1rem',
    }}>
      <div>
        <h3 style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: '1rem',
          fontWeight: 600,
          color: colors.text,
          marginBottom: '0.25rem',
        }}>
          {title || 'Consultant Time Equivalent'}
        </h3>
        <p style={{
          fontSize: '0.875rem',
          color: colors.textMuted,
          margin: 0,
        }}>
          {subtitle || `This analysis is processing ${records?.toLocaleString() || 0} records across ${tables || 0} tables`}
        </p>
      </div>

      <div style={{ textAlign: 'right' }}>
        <div style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: '2rem',
          fontWeight: 800,
          color: colors.primary,
          lineHeight: 1,
        }}>
          ${cost?.toLocaleString() || 0}
        </div>
        <div style={{
          fontSize: '0.75rem',
          color: colors.textMuted,
          marginTop: '0.25rem',
        }}>
          {hours || 0} hours @ $250/hr
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN PAGE COMPONENT
// =============================================================================

export default function ProcessingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { jobId: paramJobId } = useParams();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  const { activeProject, customerName } = useProject();

  // Get jobId from params or location state
  const jobId = paramJobId || location.state?.jobId;

  // State
  const [currentStep, setCurrentStep] = useState(0);
  const [status, setStatus] = useState('processing');
  const [progress, setProgress] = useState(null);
  const [costEquivalent, setCostEquivalent] = useState({
    records: 0,
    tables: 0,
    hours: 0,
    cost: 0,
  });
  const [error, setError] = useState(null);

  const pollIntervalRef = useRef(null);
  const stepIntervalRef = useRef(null);

  // Poll for job status
  useEffect(() => {
    if (!jobId) {
      // Demo mode - simulate processing
      simulateProcessing();
      return;
    }

    // Real mode - poll API
    pollJobStatus();
    pollIntervalRef.current = setInterval(pollJobStatus, 2000);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (stepIntervalRef.current) clearInterval(stepIntervalRef.current);
    };
  }, [jobId]);

  const pollJobStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/progress/${jobId}`);
      if (!res.ok) throw new Error('Job not found');

      const data = await res.json();
      setProgress(data);

      // Map progress to steps
      const percent = data.progress_percent || 0;
      if (percent < 25) setCurrentStep(0);
      else if (percent < 50) setCurrentStep(1);
      else if (percent < 75) setCurrentStep(2);
      else if (percent < 100) setCurrentStep(3);

      // Update cost equivalent from chunks
      if (data.chunks) {
        const rows = data.chunks.rows_so_far || 0;
        const tables = data.chunks.total || 1;
        const hours = Math.round((rows / 500 + tables * 2) * 10) / 10;
        setCostEquivalent({
          records: rows,
          tables,
          hours,
          cost: Math.round(hours * 250),
        });
      }

      // Check for completion
      if (data.status === 'completed') {
        clearInterval(pollIntervalRef.current);
        setCurrentStep(4);
        setStatus('complete');

        // Redirect to findings after brief delay
        setTimeout(() => {
          navigate('/findings');
        }, 1500);
      } else if (data.status === 'failed' || data.status === 'error') {
        clearInterval(pollIntervalRef.current);
        setStatus('error');
        setError(data.error || 'Processing failed');
      }
    } catch (err) {
      console.error('Error polling job:', err);
    }
  };

  // Demo mode simulation
  const simulateProcessing = () => {
    // Set initial cost equivalent
    setCostEquivalent({
      records: 47382,
      tables: 12,
      hours: 17,
      cost: 4250,
    });

    // Step through stages
    let step = 0;
    stepIntervalRef.current = setInterval(() => {
      step++;
      setCurrentStep(step);

      if (step >= 4) {
        clearInterval(stepIntervalRef.current);
        setStatus('complete');

        // Redirect to findings
        setTimeout(() => {
          navigate('/findings');
        }, 1500);
      }
    }, 2000);
  };

  // Get step status
  const getStepStatus = (index) => {
    if (index < currentStep) return 'complete';
    if (index === currentStep && status === 'processing') return 'active';
    if (status === 'complete') return 'complete';
    return 'pending';
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      {/* Page Header - matches mockup .page-header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: 28,
          fontWeight: 700,
          color: '#2a3441',
          marginBottom: 8,
        }}>
          {customerName || activeProject?.customer || activeProject?.name || 'Project'}
        </h1>
        <p style={{ color: '#5f6c7b', fontSize: 15, margin: 0 }}>
          {activeProject?.system_type || 'UKG Pro'} · {activeProject?.engagement_type || 'Implementation'} · Go-Live: {activeProject?.target_go_live || 'TBD'}
        </p>
      </div>

      {/* Processing Card */}
      <div style={{
        background: colors.card,
        border: `1px solid ${colors.border}`,
        borderRadius: 12,
        padding: '3rem',
        textAlign: 'center',
        marginBottom: '1.5rem',
      }}>
        {/* Spinner */}
        {status === 'processing' && (
          <div style={{
            width: 64,
            height: 64,
            margin: '0 auto 1.5rem',
            border: `4px solid ${colors.border}`,
            borderTopColor: colors.primary,
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }} />
        )}

        {/* Complete icon */}
        {status === 'complete' && (
          <div style={{
            width: 64,
            height: 64,
            margin: '0 auto 1.5rem',
            background: colors.primary,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <CheckCircle size={32} color="#fff" />
          </div>
        )}

        {/* Title */}
        <h2 style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: '1.5rem',
          fontWeight: 700,
          color: colors.text,
          marginBottom: '0.5rem',
        }}>
          {status === 'complete' ? 'Analysis Complete!' : 'Analyzing Your Data'}
        </h2>

        <p style={{
          fontSize: '0.9rem',
          color: colors.textMuted,
          marginBottom: '2rem',
        }}>
          {status === 'complete'
            ? 'Redirecting to your findings...'
            : 'This usually takes 2-5 minutes depending on data volume'}
        </p>

        {/* Processing Steps */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '2rem',
          flexWrap: 'wrap',
        }}>
          {PROCESSING_STEPS.map((step, index) => (
            <ProcessingStep
              key={step.id}
              step={step}
              status={getStepStatus(index)}
              colors={colors}
            />
          ))}
        </div>
      </div>

      {/* Cost Equivalent Banner */}
      <CostEquivalentBanner
        records={costEquivalent.records}
        tables={costEquivalent.tables}
        hours={costEquivalent.hours}
        cost={costEquivalent.cost}
        colors={colors}
        title={status === 'complete' ? 'Analysis Complete' : 'Consultant Time Equivalent'}
        subtitle={status === 'complete'
          ? `Analyzed ${costEquivalent.records.toLocaleString()} records across ${costEquivalent.tables} tables`
          : undefined}
      />

      {/* Error State */}
      {error && (
        <div style={{
          marginTop: '1.5rem',
          padding: '1rem 1.5rem',
          background: 'rgba(153, 60, 68, 0.1)',
          border: '1px solid rgba(153, 60, 68, 0.3)',
          borderRadius: 8,
          color: '#993c44',
        }}>
          {error}
        </div>
      )}

      {/* Manual navigation (in case auto-redirect fails) */}
      {status === 'complete' && (
        <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
          <button
            onClick={() => navigate('/findings')}
            style={{
              padding: '0.75rem 1.5rem',
              background: colors.primary,
              border: 'none',
              borderRadius: 8,
              color: '#fff',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            View Findings
            <ArrowRight size={16} />
          </button>
        </div>
      )}

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
