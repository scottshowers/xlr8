/**
 * PlaybookSteps - Phase 2 of Playbook Execution
 * 
 * Step-by-step execution with:
 * - Expand each step to see details
 * - Run analysis per step
 * - See findings immediately
 * - Add context for re-analysis
 * 
 * Created: January 18, 2026
 */

import React, { useState } from 'react';
import api from '../services/api';
import { 
  ChevronDown, ChevronRight, Play, CheckCircle, AlertTriangle,
  Clock, ArrowRight, ArrowLeft, RefreshCw, FileText, Loader2,
  MessageSquare, XCircle
} from 'lucide-react';

const COLORS = {
  primary: '#83b16d',
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
  blue: '#3b82f6',
  blueBg: '#dbeafe',
  purple: '#8b5cf6',
};

const STATUS_CONFIG = {
  not_started: { color: COLORS.textMuted, bg: COLORS.bg, label: 'Not Started', icon: Clock },
  in_progress: { color: COLORS.yellow, bg: COLORS.yellowBg, label: 'In Progress', icon: RefreshCw },
  complete: { color: COLORS.green, bg: COLORS.greenBg, label: 'Complete', icon: CheckCircle },
  blocked: { color: COLORS.red, bg: COLORS.redBg, label: 'Blocked', icon: XCircle },
  skipped: { color: COLORS.textMuted, bg: COLORS.bg, label: 'Skipped', icon: XCircle },
};

const SEVERITY_CONFIG = {
  critical: { color: COLORS.red, bg: COLORS.redBg, label: 'Critical' },
  high: { color: COLORS.red, bg: COLORS.redBg, label: 'High' },
  medium: { color: COLORS.yellow, bg: COLORS.yellowBg, label: 'Medium' },
  low: { color: COLORS.green, bg: COLORS.greenBg, label: 'Low' },
  info: { color: COLORS.blue, bg: COLORS.blueBg, label: 'Info' },
};

// Single step card with execution
function StepCard({ 
  step, 
  progress, 
  instanceId, 
  onStepComplete,
  isExpanded,
  onToggle
}) {
  const [executing, setExecuting] = useState(false);
  const [aiContext, setAiContext] = useState(progress?.ai_context || '');
  const [findings, setFindings] = useState(progress?.findings || []);
  const [lastResult, setLastResult] = useState(null);

  const status = progress?.status || 'not_started';
  const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG.not_started;
  const StatusIcon = statusConfig.icon;

  const handleExecute = async (forceRefresh = false) => {
    setExecuting(true);
    setLastResult(null);
    
    try {
      const res = await api.post(`/playbooks/instance/${instanceId}/step/${step.id}/execute`, {
        force_refresh: forceRefresh,
        ai_context: aiContext || null
      });
      
      setLastResult(res.data);
      
      if (res.data.findings) {
        setFindings(res.data.findings);
      }
      
      onStepComplete(step.id, res.data.findings || []);
      
    } catch (err) {
      console.error('Execution failed:', err);
      setLastResult({ success: false, error: err.message });
    } finally {
      setExecuting(false);
    }
  };

  const styles = {
    card: {
      background: COLORS.white,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '10px',
      marginBottom: '0.75rem',
      overflow: 'hidden',
      borderLeft: `4px solid ${statusConfig.color}`,
    },
    header: {
      display: 'flex',
      alignItems: 'center',
      padding: '1rem',
      cursor: 'pointer',
      gap: '0.75rem',
    },
    expandIcon: {
      color: COLORS.textMuted,
      flexShrink: 0,
    },
    stepId: {
      fontWeight: '700',
      fontSize: '0.9rem',
      color: COLORS.primary,
      minWidth: '45px',
    },
    stepInfo: {
      flex: 1,
    },
    stepName: {
      fontWeight: '500',
      fontSize: '0.95rem',
      color: COLORS.text,
      marginBottom: '0.2rem',
    },
    stepDesc: {
      fontSize: '0.8rem',
      color: COLORS.textMuted,
      lineHeight: 1.4,
    },
    statusBadge: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.35rem',
      padding: '0.3rem 0.6rem',
      borderRadius: '12px',
      fontSize: '0.75rem',
      fontWeight: '500',
      background: statusConfig.bg,
      color: statusConfig.color,
    },
    content: {
      borderTop: `1px solid ${COLORS.border}`,
      padding: '1rem',
      background: COLORS.bg,
    },
    section: {
      marginBottom: '1rem',
    },
    sectionTitle: {
      fontSize: '0.75rem',
      fontWeight: '600',
      color: COLORS.textMuted,
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
      marginBottom: '0.5rem',
    },
    actionRow: {
      display: 'flex',
      gap: '0.75rem',
      alignItems: 'flex-start',
      flexWrap: 'wrap',
    },
    executeBtn: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.6rem 1rem',
      background: COLORS.purple,
      color: COLORS.white,
      border: 'none',
      borderRadius: '6px',
      fontSize: '0.85rem',
      fontWeight: '600',
      cursor: executing ? 'not-allowed' : 'pointer',
      opacity: executing ? 0.7 : 1,
    },
    rerunBtn: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.6rem 1rem',
      background: 'transparent',
      color: COLORS.textMuted,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      fontSize: '0.85rem',
      cursor: 'pointer',
    },
    contextWrapper: {
      flex: 1,
      minWidth: '200px',
    },
    contextInput: {
      width: '100%',
      padding: '0.5rem 0.75rem',
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      fontSize: '0.85rem',
      background: COLORS.white,
    },
    contextHint: {
      fontSize: '0.7rem',
      color: COLORS.textMuted,
      marginTop: '0.25rem',
    },
    findingsContainer: {
      background: COLORS.white,
      borderRadius: '6px',
      border: `1px solid ${COLORS.border}`,
      overflow: 'hidden',
    },
    findingsHeader: {
      padding: '0.6rem 0.75rem',
      background: COLORS.bg,
      borderBottom: `1px solid ${COLORS.border}`,
      fontWeight: '600',
      fontSize: '0.85rem',
      color: COLORS.text,
    },
    findingRow: {
      padding: '0.6rem 0.75rem',
      borderBottom: `1px solid ${COLORS.border}`,
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem',
    },
    severityBadge: (severity) => {
      const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.info;
      return {
        padding: '0.15rem 0.4rem',
        borderRadius: '4px',
        fontSize: '0.7rem',
        fontWeight: '600',
        background: config.bg,
        color: config.color,
        flexShrink: 0,
      };
    },
    findingMessage: {
      flex: 1,
      fontSize: '0.85rem',
      color: COLORS.text,
      lineHeight: 1.4,
    },
    noFindings: {
      padding: '1rem',
      textAlign: 'center',
      color: COLORS.green,
      fontSize: '0.85rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.5rem',
    },
    resultBanner: (success) => ({
      padding: '0.75rem',
      borderRadius: '6px',
      background: success ? COLORS.greenBg : COLORS.redBg,
      color: success ? COLORS.green : COLORS.red,
      fontSize: '0.85rem',
      marginBottom: '1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    }),
  };

  return (
    <div style={styles.card}>
      <div style={styles.header} onClick={onToggle}>
        <span style={styles.expandIcon}>
          {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
        </span>
        <span style={styles.stepId}>{step.id}</span>
        <div style={styles.stepInfo}>
          <div style={styles.stepName}>{step.name}</div>
          {step.description && (
            <div style={styles.stepDesc}>
              {step.description.length > 100 
                ? step.description.substring(0, 100) + '...' 
                : step.description}
            </div>
          )}
        </div>
        <span style={styles.statusBadge}>
          <StatusIcon size={14} />
          {statusConfig.label}
        </span>
      </div>
      
      {isExpanded && (
        <div style={styles.content}>
          {/* Analysis description */}
          {step.analysis_count > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Analysis</div>
              <div style={{ fontSize: '0.85rem', color: COLORS.text }}>
                {step.analysis_count} engine{step.analysis_count > 1 ? 's' : ''} configured for this step
              </div>
            </div>
          )}
          
          {/* Last result banner */}
          {lastResult && (
            <div style={styles.resultBanner(lastResult.success)}>
              {lastResult.success ? (
                <>
                  <CheckCircle size={16} />
                  Analysis complete - {lastResult.findings_count || 0} finding(s)
                </>
              ) : (
                <>
                  <XCircle size={16} />
                  {lastResult.error || lastResult.message || 'Analysis failed'}
                </>
              )}
            </div>
          )}
          
          {/* Execute action row */}
          <div style={styles.section}>
            <div style={styles.sectionTitle}>Run Analysis</div>
            <div style={styles.actionRow}>
              <button 
                style={styles.executeBtn}
                onClick={() => handleExecute(false)}
                disabled={executing}
              >
                {executing ? (
                  <>
                    <Loader2 size={16} className="spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    Analyze
                  </>
                )}
              </button>
              
              {status === 'complete' && (
                <button 
                  style={styles.rerunBtn}
                  onClick={() => handleExecute(true)}
                  disabled={executing}
                >
                  <RefreshCw size={16} />
                  Re-analyze
                </button>
              )}
              
              <div style={styles.contextWrapper}>
                <input
                  type="text"
                  placeholder="Add context for analysis (e.g., 'ignore PA warnings')..."
                  value={aiContext}
                  onChange={(e) => setAiContext(e.target.value)}
                  style={styles.contextInput}
                />
                <div style={styles.contextHint}>
                  <MessageSquare size={10} style={{ marginRight: '0.25rem' }} />
                  Optional: Guide the analysis with specific instructions
                </div>
              </div>
            </div>
          </div>
          
          {/* Findings */}
          {(findings.length > 0 || status === 'complete') && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Findings</div>
              <div style={styles.findingsContainer}>
                {findings.length === 0 ? (
                  <div style={styles.noFindings}>
                    <CheckCircle size={16} />
                    No issues found
                  </div>
                ) : (
                  <>
                    <div style={styles.findingsHeader}>
                      {findings.length} Finding{findings.length > 1 ? 's' : ''}
                    </div>
                    {findings.map((finding, idx) => (
                      <div key={finding.id || idx} style={styles.findingRow}>
                        <span style={styles.severityBadge(finding.severity)}>
                          {finding.severity?.toUpperCase() || 'INFO'}
                        </span>
                        <span style={styles.findingMessage}>
                          {finding.message}
                        </span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>
          )}
          
          {/* Guidance */}
          {step.guidance && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Guidance</div>
              <div style={{ 
                fontSize: '0.85rem', 
                color: COLORS.text, 
                background: COLORS.blueBg,
                padding: '0.75rem',
                borderRadius: '6px',
                border: `1px solid ${COLORS.blue}`,
                lineHeight: 1.5
              }}>
                {step.guidance}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Main component
export default function PlaybookSteps({
  instanceId,
  definition,
  projectId,
  progress,
  onStepComplete,
  onAllComplete,
  onBack
}) {
  const [expandedStep, setExpandedStep] = useState(null);
  const [localProgress, setLocalProgress] = useState(progress);

  const steps = definition?.steps || [];
  
  const handleStepComplete = (stepId, findings) => {
    setLocalProgress(prev => ({
      ...prev,
      [stepId]: { ...prev[stepId], status: 'complete', findings }
    }));
    onStepComplete(stepId, findings);
  };

  // Calculate stats
  const completedCount = steps.filter(s => 
    localProgress[s.id]?.status === 'complete'
  ).length;
  const allComplete = completedCount === steps.length;

  const styles = {
    container: {
      maxWidth: '900px',
      margin: '0 auto',
    },
    header: {
      marginBottom: '1.5rem',
    },
    title: {
      fontSize: '1.5rem',
      fontWeight: '600',
      color: COLORS.text,
      marginBottom: '0.5rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    subtitle: {
      fontSize: '0.95rem',
      color: COLORS.textMuted,
    },
    progressBar: {
      marginBottom: '1.5rem',
      padding: '1rem',
      background: COLORS.white,
      borderRadius: '8px',
      border: `1px solid ${COLORS.border}`,
    },
    progressText: {
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: '0.5rem',
      fontSize: '0.85rem',
      color: COLORS.text,
    },
    progressTrack: {
      height: '8px',
      background: COLORS.bg,
      borderRadius: '4px',
      overflow: 'hidden',
    },
    progressFill: {
      height: '100%',
      background: COLORS.primary,
      borderRadius: '4px',
      transition: 'width 0.3s ease',
    },
    stepsList: {
      marginBottom: '1.5rem',
    },
    footer: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '1rem',
      background: COLORS.white,
      borderRadius: '8px',
      border: `1px solid ${COLORS.border}`,
    },
    backBtn: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.75rem 1.5rem',
      background: 'transparent',
      color: COLORS.textMuted,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '8px',
      fontSize: '0.95rem',
      cursor: 'pointer',
    },
    continueBtn: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.75rem 1.5rem',
      background: allComplete ? COLORS.primary : COLORS.textMuted,
      color: COLORS.white,
      border: 'none',
      borderRadius: '8px',
      fontSize: '0.95rem',
      fontWeight: '600',
      cursor: allComplete ? 'pointer' : 'not-allowed',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.title}>
          <FileText size={24} />
          Execute Steps
        </div>
        <div style={styles.subtitle}>
          Work through each step. Run analysis and review findings as you go.
        </div>
      </div>

      <div style={styles.progressBar}>
        <div style={styles.progressText}>
          <span>Progress</span>
          <span>{completedCount} of {steps.length} complete</span>
        </div>
        <div style={styles.progressTrack}>
          <div 
            style={{ 
              ...styles.progressFill, 
              width: `${steps.length > 0 ? (completedCount / steps.length) * 100 : 0}%` 
            }} 
          />
        </div>
      </div>

      <div style={styles.stepsList}>
        {steps.map(step => (
          <StepCard
            key={step.id}
            step={step}
            progress={localProgress[step.id] || {}}
            instanceId={instanceId}
            onStepComplete={handleStepComplete}
            isExpanded={expandedStep === step.id}
            onToggle={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
          />
        ))}
      </div>

      <div style={styles.footer}>
        <button style={styles.backBtn} onClick={onBack}>
          <ArrowLeft size={18} />
          Back to Data Sources
        </button>
        <span style={{ color: COLORS.textMuted, fontSize: '0.85rem' }}>
          {allComplete ? 'All steps complete!' : `${steps.length - completedCount} step(s) remaining`}
        </span>
        <button 
          style={styles.continueBtn}
          onClick={onAllComplete}
          disabled={!allComplete}
        >
          Review Findings
          <ArrowRight size={18} />
        </button>
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
