/**
 * ProgressTrackerPage.jsx - Playbook Execution Tracking
 * ======================================================
 * 
 * Phase 4A.7: Progress Tracker
 * 
 * Track playbook execution with stats bar + timeline.
 * Matches mockup Screen 7 design.
 * 
 * Created: January 15, 2026
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Activity, CheckCircle, Clock, AlertTriangle, Circle,
  Loader2, FileText, User, Calendar, Sparkles, ArrowLeft,
  MoreVertical, Edit2, MessageSquare
} from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import { PageHeader } from '../components/ui';
import api from '../services/api';

// =============================================================================
// COLORS
// =============================================================================

const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f8fafc',
  card: dark ? '#242b3d' : '#ffffff',
  border: dark ? '#2d3548' : '#e2e8f0',
  text: dark ? '#e8eaed' : '#1a2332',
  textMuted: dark ? '#8b95a5' : '#64748b',
  textLight: dark ? '#6b7280' : '#9ca3af',
  primary: '#83b16d',
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.1)',
  accent: '#285390',
  success: '#16a34a',
  successBg: dark ? 'rgba(22, 163, 74, 0.15)' : '#dcfce7',
  warning: '#d97706',
  warningBg: dark ? 'rgba(217, 119, 6, 0.15)' : '#fef3c7',
  danger: '#dc2626',
  dangerBg: dark ? 'rgba(220, 38, 38, 0.15)' : '#fee2e2',
  info: '#0ea5e9',
  infoBg: dark ? 'rgba(14, 165, 233, 0.15)' : '#e0f2fe',
  inputBg: dark ? '#1e2433' : '#f8fafc',
});

// =============================================================================
// STAT CARD COMPONENT
// =============================================================================

function TrackerStat({ value, label, variant, colors }) {
  const variants = {
    complete: { bg: colors.successBg, color: colors.success, icon: CheckCircle },
    progress: { bg: colors.infoBg, color: colors.info, icon: Clock },
    blocked: { bg: colors.dangerBg, color: colors.danger, icon: AlertTriangle },
    pending: { bg: colors.inputBg, color: colors.textMuted, icon: Circle },
  };
  
  const config = variants[variant] || variants.pending;
  const Icon = config.icon;
  
  return (
    <div style={{
      padding: '1rem 1.25rem',
      background: config.bg,
      borderRadius: 10,
      minWidth: 100,
      textAlign: 'center',
    }}>
      <div style={{ 
        fontSize: '1.75rem', 
        fontWeight: 700, 
        color: config.color,
        lineHeight: 1,
        marginBottom: '0.35rem',
      }}>
        {value}
      </div>
      <div style={{ 
        fontSize: '0.75rem', 
        color: colors.textMuted,
        fontWeight: 500,
      }}>
        {label}
      </div>
    </div>
  );
}

// =============================================================================
// TIMELINE ITEM COMPONENT
// =============================================================================

function TimelineItem({ action, colors, onStatusChange }) {
  const [showMenu, setShowMenu] = useState(false);
  
  const statusConfig = {
    complete: { 
      icon: CheckCircle, 
      color: colors.success, 
      bg: colors.successBg,
      label: 'Done',
      symbol: '✓'
    },
    in_progress: { 
      icon: Clock, 
      color: colors.info, 
      bg: colors.infoBg,
      label: 'In Progress',
      symbol: '⋯'
    },
    blocked: { 
      icon: AlertTriangle, 
      color: colors.danger, 
      bg: colors.dangerBg,
      label: 'Blocked',
      symbol: '!'
    },
    pending: { 
      icon: Circle, 
      color: colors.textMuted, 
      bg: colors.inputBg,
      label: 'Not Started',
      symbol: '○'
    },
  };
  
  const config = statusConfig[action.status] || statusConfig.pending;
  
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((date - now) / (1000 * 60 * 60 * 24));
    
    if (action.status === 'complete') {
      return 'Done';
    }
    
    if (diffDays < 0) {
      return 'Overdue';
    }
    
    return `Due ${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
  };
  
  const getDueDateColor = () => {
    if (action.status === 'complete') return colors.success;
    if (action.status === 'blocked') return colors.danger;
    
    const date = new Date(action.due_date);
    const now = new Date();
    if (date < now) return colors.danger;
    return colors.textMuted;
  };
  
  const handleStatusClick = (newStatus) => {
    onStatusChange(action.id, newStatus);
    setShowMenu(false);
  };
  
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: '1rem',
      padding: '1rem 0',
      borderBottom: `1px solid ${colors.border}`,
    }}>
      {/* Status indicator */}
      <div 
        onClick={() => setShowMenu(!showMenu)}
        style={{
          width: 36,
          height: 36,
          borderRadius: 8,
          background: config.bg,
          color: config.color,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: '1rem',
          cursor: 'pointer',
          position: 'relative',
          flexShrink: 0,
        }}
      >
        {config.symbol}
        
        {/* Status dropdown menu */}
        {showMenu && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            marginTop: 4,
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 8,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            zIndex: 100,
            minWidth: 140,
            overflow: 'hidden',
          }}>
            {Object.entries(statusConfig).map(([key, cfg]) => (
              <div
                key={key}
                onClick={() => handleStatusClick(key)}
                style={{
                  padding: '0.6rem 0.75rem',
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: action.status === key ? cfg.color : colors.text,
                  background: action.status === key ? cfg.bg : 'transparent',
                }}
                onMouseEnter={(e) => {
                  if (action.status !== key) {
                    e.currentTarget.style.background = colors.inputBg;
                  }
                }}
                onMouseLeave={(e) => {
                  if (action.status !== key) {
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                <span style={{ fontWeight: 600 }}>{cfg.symbol}</span>
                {cfg.label}
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ 
          fontSize: '0.95rem', 
          fontWeight: 500, 
          color: colors.text,
          marginBottom: '0.25rem',
        }}>
          {action.title}
        </div>
        <div style={{ 
          fontSize: '0.8rem', 
          color: colors.textMuted,
        }}>
          {action.status === 'complete' && action.completed_at ? (
            `Completed ${new Date(action.completed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`
          ) : action.status === 'blocked' && action.blocked_reason ? (
            `Blocked — ${action.blocked_reason}`
          ) : action.status === 'in_progress' ? (
            'In progress'
          ) : (
            action.description || 'Not started'
          )}
        </div>
      </div>
      
      {/* Owner */}
      <div style={{ 
        fontSize: '0.8rem', 
        color: colors.textMuted,
        minWidth: 100,
      }}>
        {action.assignee_name}
      </div>
      
      {/* Due date */}
      <div style={{ 
        fontSize: '0.8rem', 
        color: getDueDateColor(),
        fontWeight: 500,
        minWidth: 80,
        textAlign: 'right',
      }}>
        {formatDate(action.due_date)}
      </div>
    </div>
  );
}

// =============================================================================
// RISK MITIGATED BANNER
// =============================================================================

function RiskMitigatedBanner({ progress, colors }) {
  const formatCurrency = (value) => {
    return `$${value.toLocaleString()}`;
  };
  
  return (
    <div style={{
      background: `linear-gradient(135deg, ${colors.primary}15 0%, ${colors.primary}05 100%)`,
      border: `1px solid ${colors.primary}40`,
      borderRadius: 12,
      padding: '1.25rem 1.5rem',
      marginTop: '1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: '1rem',
    }}>
      <div>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.5rem',
          marginBottom: '0.25rem'
        }}>
          <Sparkles size={18} color={colors.primary} />
          <span style={{ 
            fontSize: '0.9rem', 
            fontWeight: 600, 
            color: colors.text 
          }}>
            Project Impact
          </span>
        </div>
        <p style={{ 
          fontSize: '0.8rem', 
          color: colors.textMuted, 
          margin: 0 
        }}>
          Remediation {progress.blocked > 0 ? 'partially blocked' : 'on track'} · Go-live readiness: {progress.go_live_readiness}%
        </p>
      </div>
      
      <div style={{ textAlign: 'right' }}>
        <div style={{ 
          fontSize: '1.75rem', 
          fontWeight: 700, 
          color: colors.primary,
          lineHeight: 1
        }}>
          {formatCurrency(progress.risk_mitigated)}
        </div>
        <div style={{ 
          fontSize: '0.75rem', 
          color: colors.textMuted 
        }}>
          Risk mitigated to date
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN PAGE COMPONENT
// =============================================================================

export default function ProgressTrackerPage() {
  const { playbookId } = useParams();
  const navigate = useNavigate();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  const { activeProject, customerName } = useProject();
  
  // State
  const [playbook, setPlaybook] = useState(null);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Load playbook and progress
  useEffect(() => {
    if (playbookId) {
      loadPlaybook();
    }
  }, [playbookId]);
  
  const loadPlaybook = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Load playbook details
      const pbResponse = await api.get(`/remediation/playbook/${playbookId}`);
      setPlaybook(pbResponse.data);
      
      // Load progress
      const progressResponse = await api.get(`/remediation/playbook/${playbookId}/progress`);
      setProgress(progressResponse.data);
    } catch (err) {
      console.error('Error loading playbook:', err);
      setError('Failed to load playbook');
    } finally {
      setLoading(false);
    }
  };
  
  // Update action status
  const handleStatusChange = async (actionId, newStatus, blockedReason = null) => {
    try {
      const response = await api.patch(`/remediation/playbook/${playbookId}/action/${actionId}/status`, {
        status: newStatus,
        blocked_reason: blockedReason,
      });
      
      // Update local state with response
      if (response.data.progress) {
        setProgress(response.data.progress);
      }
      
      // Update action in playbook
      setPlaybook(prev => ({
        ...prev,
        actions: prev.actions.map(a => 
          a.id === actionId ? { ...a, status: newStatus, blocked_reason: blockedReason } : a
        )
      }));
    } catch (err) {
      console.error('Error updating status:', err);
    }
  };
  
  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };
  
  // Loading state
  if (loading) {
    return (
      <div>
        <PageHeader
          icon={Activity}
          title="Progress Tracker"
          subtitle="Loading..."
        />
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '4rem',
          gap: '0.75rem',
          color: colors.textMuted,
        }}>
          <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
          <span>Loading playbook...</span>
        </div>
      </div>
    );
  }
  
  // Error state
  if (error || !playbook) {
    return (
      <div>
        <PageHeader
          icon={Activity}
          title="Progress Tracker"
          subtitle="Error loading playbook"
        />
        <div style={{
          padding: '1rem 1.5rem',
          background: colors.dangerBg,
          border: `1px solid ${colors.danger}30`,
          borderRadius: 8,
          color: colors.danger,
          marginBottom: '1.5rem',
        }}>
          {error || 'Playbook not found'}
        </div>
        <button
          onClick={() => navigate('/playbooks')}
          style={{
            padding: '0.75rem 1.25rem',
            background: colors.inputBg,
            border: `1px solid ${colors.border}`,
            borderRadius: 8,
            color: colors.text,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <ArrowLeft size={16} />
          Back to Playbooks
        </button>
      </div>
    );
  }
  
  return (
    <div>
      <PageHeader
        icon={Activity}
        title={`${playbook.customer_name} — Progress`}
        subtitle={`${playbook.name} · Started ${formatDate(playbook.created_at)}`}
        breadcrumbs={[
          { label: playbook.customer_name },
          { label: 'Progress' },
        ]}
      />
      
      {/* Stats Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '1rem',
      }}>
        <div style={{
          display: 'flex',
          gap: '0.75rem',
        }}>
          <TrackerStat 
            value={progress?.complete || 0} 
            label="Complete" 
            variant="complete" 
            colors={colors} 
          />
          <TrackerStat 
            value={progress?.in_progress || 0} 
            label="In Progress" 
            variant="progress" 
            colors={colors} 
          />
          <TrackerStat 
            value={progress?.blocked || 0} 
            label="Blocked" 
            variant="blocked" 
            colors={colors} 
          />
          <TrackerStat 
            value={progress?.pending || 0} 
            label="Not Started" 
            variant="pending" 
            colors={colors} 
          />
        </div>
        
        <button
          style={{
            padding: '0.75rem 1.25rem',
            background: colors.inputBg,
            border: `1px solid ${colors.border}`,
            borderRadius: 8,
            color: colors.text,
            fontWeight: 500,
            fontSize: '0.9rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <FileText size={16} />
          Export Report
        </button>
      </div>
      
      {/* Timeline */}
      <div style={{
        background: colors.card,
        border: `1px solid ${colors.border}`,
        borderRadius: 12,
        padding: '0.5rem 1.5rem',
      }}>
        {playbook.actions.map((action) => (
          <TimelineItem
            key={action.id}
            action={action}
            colors={colors}
            onStatusChange={handleStatusChange}
          />
        ))}
      </div>
      
      {/* Risk Mitigated Banner */}
      {progress && (
        <RiskMitigatedBanner progress={progress} colors={colors} />
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
