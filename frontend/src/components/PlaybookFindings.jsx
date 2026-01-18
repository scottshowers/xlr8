/**
 * PlaybookFindings - Phase 3 of Playbook Execution
 * 
 * Aggregate view of all findings across steps:
 * - Filter by severity
 * - Acknowledge / Suppress findings
 * - Re-analyze specific steps
 * - Export results
 * 
 * Created: January 18, 2026
 */

import React, { useState, useMemo } from 'react';
import api from '../services/api';
import { 
  FileSearch, AlertTriangle, CheckCircle, Filter, Download,
  ArrowLeft, Eye, EyeOff, RefreshCw, ChevronDown, X
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

const SEVERITY_CONFIG = {
  critical: { color: COLORS.red, bg: COLORS.redBg, label: 'Critical', priority: 1 },
  high: { color: COLORS.red, bg: COLORS.redBg, label: 'High', priority: 2 },
  medium: { color: COLORS.yellow, bg: COLORS.yellowBg, label: 'Medium', priority: 3 },
  low: { color: COLORS.green, bg: COLORS.greenBg, label: 'Low', priority: 4 },
  info: { color: COLORS.blue, bg: COLORS.blueBg, label: 'Info', priority: 5 },
};

const FINDING_STATUS = {
  active: { label: 'Active', icon: AlertTriangle },
  acknowledged: { label: 'Acknowledged', icon: Eye },
  suppressed: { label: 'Suppressed', icon: EyeOff },
  resolved: { label: 'Resolved', icon: CheckCircle },
};

// Single finding row
function FindingRow({ finding, stepName, onStatusChange }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [updating, setUpdating] = useState(false);
  
  const severityConfig = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.info;
  const status = finding.status || 'active';
  const isAcknowledged = status === 'acknowledged';
  const isSuppressed = status === 'suppressed';

  const handleStatusChange = async (newStatus) => {
    setUpdating(true);
    try {
      await onStatusChange(finding.id, newStatus);
    } finally {
      setUpdating(false);
    }
  };

  const styles = {
    row: {
      background: COLORS.white,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '8px',
      marginBottom: '0.5rem',
      overflow: 'hidden',
      opacity: isSuppressed ? 0.5 : 1,
    },
    header: {
      display: 'flex',
      alignItems: 'flex-start',
      padding: '0.75rem 1rem',
      gap: '0.75rem',
      cursor: 'pointer',
    },
    severityBadge: {
      padding: '0.2rem 0.5rem',
      borderRadius: '4px',
      fontSize: '0.7rem',
      fontWeight: '600',
      background: severityConfig.bg,
      color: severityConfig.color,
      flexShrink: 0,
    },
    content: {
      flex: 1,
    },
    message: {
      fontSize: '0.9rem',
      color: COLORS.text,
      lineHeight: 1.4,
      marginBottom: '0.25rem',
      textDecoration: isSuppressed ? 'line-through' : 'none',
    },
    meta: {
      fontSize: '0.75rem',
      color: COLORS.textMuted,
      display: 'flex',
      gap: '1rem',
    },
    actions: {
      display: 'flex',
      gap: '0.5rem',
      flexShrink: 0,
    },
    actionBtn: (active) => ({
      padding: '0.3rem 0.5rem',
      fontSize: '0.7rem',
      border: `1px solid ${active ? COLORS.blue : COLORS.border}`,
      borderRadius: '4px',
      background: active ? COLORS.blueBg : 'transparent',
      color: active ? COLORS.blue : COLORS.textMuted,
      cursor: updating ? 'not-allowed' : 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.25rem',
    }),
    expandedContent: {
      borderTop: `1px solid ${COLORS.border}`,
      padding: '0.75rem 1rem',
      background: COLORS.bg,
    },
    detail: {
      fontSize: '0.8rem',
      color: COLORS.text,
      marginBottom: '0.5rem',
    },
    detailLabel: {
      fontWeight: '600',
      color: COLORS.textMuted,
      marginRight: '0.5rem',
    },
  };

  return (
    <div style={styles.row}>
      <div style={styles.header} onClick={() => setIsExpanded(!isExpanded)}>
        <span style={styles.severityBadge}>
          {severityConfig.label.toUpperCase()}
        </span>
        <div style={styles.content}>
          <div style={styles.message}>{finding.message}</div>
          <div style={styles.meta}>
            <span>Step: {finding.stepId || stepName}</span>
            {finding.engine && <span>Engine: {finding.engine}</span>}
            {finding.source_table && <span>Source: {finding.source_table}</span>}
          </div>
        </div>
        <div style={styles.actions} onClick={(e) => e.stopPropagation()}>
          <button 
            style={styles.actionBtn(isAcknowledged)}
            onClick={() => handleStatusChange(isAcknowledged ? 'active' : 'acknowledged')}
            disabled={updating}
            title={isAcknowledged ? 'Mark as active' : 'Acknowledge'}
          >
            <Eye size={12} />
            {isAcknowledged ? 'Ack' : 'Ack'}
          </button>
          <button 
            style={styles.actionBtn(isSuppressed)}
            onClick={() => handleStatusChange(isSuppressed ? 'active' : 'suppressed')}
            disabled={updating}
            title={isSuppressed ? 'Show finding' : 'Suppress'}
          >
            <EyeOff size={12} />
            {isSuppressed ? 'Show' : 'Hide'}
          </button>
        </div>
        <ChevronDown 
          size={16} 
          style={{ 
            color: COLORS.textMuted, 
            transform: isExpanded ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.2s'
          }} 
        />
      </div>
      
      {isExpanded && (
        <div style={styles.expandedContent}>
          {finding.details && (
            <div style={styles.detail}>
              <span style={styles.detailLabel}>Details:</span>
              {typeof finding.details === 'string' 
                ? finding.details 
                : JSON.stringify(finding.details, null, 2)}
            </div>
          )}
          {finding.sql_query && (
            <div style={styles.detail}>
              <span style={styles.detailLabel}>SQL:</span>
              <code style={{ fontSize: '0.75rem', background: COLORS.white, padding: '0.25rem' }}>
                {finding.sql_query}
              </code>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Main component
export default function PlaybookFindings({
  instanceId,
  definition,
  projectId,
  findings,
  onBack,
  onClose
}) {
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [filterStatus, setFilterStatus] = useState('active');
  const [showSuppressed, setShowSuppressed] = useState(false);
  const [localFindings, setLocalFindings] = useState(findings);
  const [exporting, setExporting] = useState(false);

  // Build step lookup
  const stepLookup = useMemo(() => {
    const lookup = {};
    (definition?.steps || []).forEach(s => {
      lookup[s.id] = s.name;
    });
    return lookup;
  }, [definition]);

  // Filter findings
  const filteredFindings = useMemo(() => {
    return localFindings
      .filter(f => {
        if (filterSeverity !== 'all' && f.severity !== filterSeverity) return false;
        if (!showSuppressed && f.status === 'suppressed') return false;
        if (filterStatus !== 'all' && f.status !== filterStatus) return false;
        return true;
      })
      .sort((a, b) => {
        const aPriority = SEVERITY_CONFIG[a.severity]?.priority || 99;
        const bPriority = SEVERITY_CONFIG[b.severity]?.priority || 99;
        return aPriority - bPriority;
      });
  }, [localFindings, filterSeverity, filterStatus, showSuppressed]);

  // Count by severity
  const severityCounts = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    localFindings.forEach(f => {
      if (f.status !== 'suppressed' && counts[f.severity] !== undefined) {
        counts[f.severity]++;
      }
    });
    return counts;
  }, [localFindings]);

  const handleStatusChange = async (findingId, newStatus) => {
    try {
      await api.put(`/playbooks/instance/${instanceId}/finding/${findingId}`, {
        status: newStatus
      });
      
      setLocalFindings(prev => prev.map(f => 
        f.id === findingId ? { ...f, status: newStatus } : f
      ));
    } catch (err) {
      console.error('Failed to update finding:', err);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      // For now, just download as JSON
      const exportData = {
        playbook: definition?.name,
        exportedAt: new Date().toISOString(),
        totalFindings: localFindings.length,
        findings: filteredFindings
      };
      
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${definition?.id || 'playbook'}-findings-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  const styles = {
    container: {
      maxWidth: '1000px',
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
    summary: {
      display: 'flex',
      gap: '1rem',
      marginBottom: '1.5rem',
      flexWrap: 'wrap',
    },
    summaryCard: (color, bg) => ({
      padding: '1rem 1.25rem',
      background: bg,
      borderRadius: '8px',
      border: `1px solid ${color}`,
      minWidth: '100px',
      textAlign: 'center',
    }),
    summaryCount: (color) => ({
      fontSize: '1.75rem',
      fontWeight: '700',
      color: color,
    }),
    summaryLabel: {
      fontSize: '0.8rem',
      color: COLORS.textMuted,
    },
    filters: {
      display: 'flex',
      gap: '1rem',
      marginBottom: '1rem',
      padding: '1rem',
      background: COLORS.white,
      borderRadius: '8px',
      border: `1px solid ${COLORS.border}`,
      flexWrap: 'wrap',
      alignItems: 'center',
    },
    filterGroup: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    filterLabel: {
      fontSize: '0.8rem',
      color: COLORS.textMuted,
      fontWeight: '500',
    },
    filterSelect: {
      padding: '0.4rem 0.75rem',
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      fontSize: '0.85rem',
      background: COLORS.white,
    },
    filterToggle: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.35rem',
      padding: '0.4rem 0.75rem',
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      fontSize: '0.8rem',
      background: showSuppressed ? COLORS.blueBg : 'transparent',
      color: showSuppressed ? COLORS.blue : COLORS.textMuted,
      cursor: 'pointer',
    },
    findingsList: {
      marginBottom: '1.5rem',
    },
    noFindings: {
      padding: '3rem',
      textAlign: 'center',
      background: COLORS.greenBg,
      borderRadius: '8px',
      color: COLORS.green,
    },
    noFindingsIcon: {
      marginBottom: '0.75rem',
    },
    noFindingsTitle: {
      fontSize: '1.25rem',
      fontWeight: '600',
      marginBottom: '0.5rem',
    },
    noFindingsText: {
      fontSize: '0.9rem',
      opacity: 0.8,
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
    exportBtn: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.75rem 1.5rem',
      background: COLORS.primary,
      color: COLORS.white,
      border: 'none',
      borderRadius: '8px',
      fontSize: '0.95rem',
      fontWeight: '600',
      cursor: 'pointer',
    },
    doneBtn: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.75rem 1.5rem',
      background: COLORS.green,
      color: COLORS.white,
      border: 'none',
      borderRadius: '8px',
      fontSize: '0.95rem',
      fontWeight: '600',
      cursor: 'pointer',
    },
  };

  const totalActive = localFindings.filter(f => f.status !== 'suppressed').length;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.title}>
          <FileSearch size={24} />
          Review Findings
        </div>
        <div style={styles.subtitle}>
          {totalActive} finding{totalActive !== 1 ? 's' : ''} to review. 
          Acknowledge or suppress items as needed, then export your results.
        </div>
      </div>

      {/* Summary cards */}
      <div style={styles.summary}>
        {Object.entries(SEVERITY_CONFIG).map(([key, config]) => (
          <div key={key} style={styles.summaryCard(config.color, config.bg)}>
            <div style={styles.summaryCount(config.color)}>
              {severityCounts[key]}
            </div>
            <div style={styles.summaryLabel}>{config.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={styles.filters}>
        <div style={styles.filterGroup}>
          <Filter size={16} color={COLORS.textMuted} />
          <span style={styles.filterLabel}>Severity:</span>
          <select 
            style={styles.filterSelect}
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
          >
            <option value="all">All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>
        </div>
        
        <div style={styles.filterGroup}>
          <span style={styles.filterLabel}>Status:</span>
          <select 
            style={styles.filterSelect}
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="all">All</option>
            <option value="active">Active</option>
            <option value="acknowledged">Acknowledged</option>
          </select>
        </div>
        
        <button 
          style={styles.filterToggle}
          onClick={() => setShowSuppressed(!showSuppressed)}
        >
          <EyeOff size={14} />
          {showSuppressed ? 'Hide suppressed' : 'Show suppressed'}
        </button>
        
        <div style={{ marginLeft: 'auto', fontSize: '0.85rem', color: COLORS.textMuted }}>
          Showing {filteredFindings.length} of {localFindings.length}
        </div>
      </div>

      {/* Findings list */}
      <div style={styles.findingsList}>
        {filteredFindings.length === 0 ? (
          <div style={styles.noFindings}>
            <CheckCircle size={48} style={styles.noFindingsIcon} />
            <div style={styles.noFindingsTitle}>
              {localFindings.length === 0 ? 'No Findings' : 'No Matching Findings'}
            </div>
            <div style={styles.noFindingsText}>
              {localFindings.length === 0 
                ? 'All steps completed without any issues detected.'
                : 'Try adjusting your filters to see more findings.'}
            </div>
          </div>
        ) : (
          filteredFindings.map((finding, idx) => (
            <FindingRow
              key={finding.id || idx}
              finding={finding}
              stepName={stepLookup[finding.stepId] || finding.stepId}
              onStatusChange={handleStatusChange}
            />
          ))
        )}
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        <button style={styles.backBtn} onClick={onBack}>
          <ArrowLeft size={18} />
          Back to Steps
        </button>
        
        <button 
          style={styles.exportBtn} 
          onClick={handleExport}
          disabled={exporting}
        >
          <Download size={18} />
          {exporting ? 'Exporting...' : 'Export Report'}
        </button>
        
        <button style={styles.doneBtn} onClick={onClose}>
          <CheckCircle size={18} />
          Done
        </button>
      </div>
    </div>
  );
}
