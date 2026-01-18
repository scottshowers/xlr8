/**
 * DataSourcesReview - Phase 1 of Playbook Execution
 * 
 * Shows all steps with their data source mappings.
 * Consultant reviews, fixes any issues, then confirms to proceed.
 * 
 * This is the "pre-flight check" before running any analysis.
 * 
 * Created: January 18, 2026
 */

import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { 
  Database, CheckCircle, AlertTriangle, ChevronDown, 
  ChevronRight, Search, ArrowRight, FileSpreadsheet,
  RefreshCw, HelpCircle
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
};

// Format table name for display
const formatTableName = (tableName, fileName) => {
  if (fileName) return fileName;
  if (!tableName) return 'Not selected';
  
  return tableName
    .replace(/^[a-z]+\d+_/i, '')
    .replace(/_/g, ' ')
    .split(' ')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
};

// Get status config for a resolution
const getResolutionStatus = (resolution) => {
  if (!resolution) return { status: 'none', color: COLORS.textMuted, bg: COLORS.bg, label: 'No data needed' };
  if (resolution.manually_set) return { status: 'manual', color: COLORS.blue, bg: COLORS.blueBg, label: 'You selected' };
  if (!resolution.resolved_table) return { status: 'missing', color: COLORS.red, bg: COLORS.redBg, label: 'Needs selection' };
  if (resolution.confidence >= 0.8) return { status: 'good', color: COLORS.green, bg: COLORS.greenBg, label: 'Auto-matched' };
  return { status: 'verify', color: COLORS.yellow, bg: COLORS.yellowBg, label: 'Please verify' };
};

// Single step row with its data sources
function StepRow({ step, resolutions, availableTables, onResolutionChange, instanceId }) {
  const [expanded, setExpanded] = useState(false);
  
  const placeholders = Object.keys(resolutions || {});
  const hasResolutions = placeholders.length > 0;
  
  // Calculate step status
  const stepStatuses = placeholders.map(p => getResolutionStatus(resolutions[p]));
  const hasMissing = stepStatuses.some(s => s.status === 'missing');
  const hasVerify = stepStatuses.some(s => s.status === 'verify');
  const allGood = stepStatuses.every(s => s.status === 'good' || s.status === 'manual' || s.status === 'none');
  
  const overallStatus = hasMissing ? 'missing' : hasVerify ? 'verify' : 'good';
  const statusConfig = {
    missing: { color: COLORS.red, bg: COLORS.redBg, icon: AlertTriangle, label: 'Needs attention' },
    verify: { color: COLORS.yellow, bg: COLORS.yellowBg, icon: AlertTriangle, label: 'Verify data' },
    good: { color: COLORS.green, bg: COLORS.greenBg, icon: CheckCircle, label: 'Ready' }
  }[overallStatus];
  
  const StatusIcon = statusConfig.icon;

  const styles = {
    row: {
      background: COLORS.white,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '8px',
      marginBottom: '0.5rem',
      overflow: 'hidden',
    },
    header: {
      display: 'flex',
      alignItems: 'center',
      padding: '0.75rem 1rem',
      cursor: hasResolutions ? 'pointer' : 'default',
      gap: '0.75rem',
    },
    stepId: {
      fontWeight: '700',
      fontSize: '0.85rem',
      color: COLORS.primary,
      minWidth: '40px',
    },
    stepName: {
      flex: 1,
      fontSize: '0.9rem',
      color: COLORS.text,
    },
    statusBadge: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.35rem',
      padding: '0.25rem 0.6rem',
      borderRadius: '12px',
      fontSize: '0.75rem',
      fontWeight: '500',
      background: statusConfig.bg,
      color: statusConfig.color,
    },
    expandIcon: {
      color: COLORS.textMuted,
    },
    content: {
      borderTop: `1px solid ${COLORS.border}`,
      padding: '1rem',
      background: COLORS.bg,
    },
    placeholder: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.6rem',
      background: COLORS.white,
      borderRadius: '6px',
      marginBottom: '0.5rem',
      border: `1px solid ${COLORS.border}`,
    },
    placeholderLabel: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '0.85rem',
      color: COLORS.text,
    },
    noData: {
      fontSize: '0.8rem',
      color: COLORS.textMuted,
      fontStyle: 'italic',
      padding: '0.5rem',
    },
  };

  if (!hasResolutions) {
    return (
      <div style={styles.row}>
        <div style={styles.header}>
          <span style={styles.stepId}>{step.id}</span>
          <span style={styles.stepName}>{step.name}</span>
          <span style={{ ...styles.statusBadge, background: COLORS.bg, color: COLORS.textMuted }}>
            No data needed
          </span>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.row}>
      <div style={styles.header} onClick={() => setExpanded(!expanded)}>
        <span style={styles.expandIcon}>
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </span>
        <span style={styles.stepId}>{step.id}</span>
        <span style={styles.stepName}>{step.name}</span>
        <span style={styles.statusBadge}>
          <StatusIcon size={14} />
          {statusConfig.label}
        </span>
      </div>
      
      {expanded && (
        <div style={styles.content}>
          {placeholders.map(placeholder => (
            <DataSourceSelector
              key={placeholder}
              placeholder={placeholder}
              resolution={resolutions[placeholder]}
              availableTables={availableTables}
              onSelect={(table) => onResolutionChange(step.id, placeholder, table)}
              instanceId={instanceId}
              stepId={step.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Individual data source selector
function DataSourceSelector({ placeholder, resolution, availableTables, onSelect, instanceId, stepId }) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [saving, setSaving] = useState(false);
  
  const status = getResolutionStatus(resolution);
  
  const filteredTables = availableTables.filter(t =>
    !searchTerm ||
    t.table_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (t.file_name && t.file_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );
  
  const dataLabel = placeholder
    .replace(/_data$/, '')
    .replace(/_/g, ' ')
    .split(' ')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');

  const handleSelect = async (tableName) => {
    setSaving(true);
    try {
      await api.post(`/playbooks/instance/${instanceId}/step/${stepId}/resolve`, {
        placeholder,
        table_name: tableName
      });
      onSelect(tableName);
    } catch (err) {
      console.error('Failed to save resolution:', err);
    } finally {
      setSaving(false);
      setIsOpen(false);
      setSearchTerm('');
    }
  };

  const styles = {
    container: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.6rem',
      background: COLORS.white,
      borderRadius: '6px',
      marginBottom: '0.5rem',
      border: `1px solid ${COLORS.border}`,
      flexWrap: 'wrap',
      gap: '0.5rem',
    },
    left: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      flex: '1 1 200px',
    },
    label: {
      fontSize: '0.85rem',
      fontWeight: '500',
      color: COLORS.text,
    },
    badge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.25rem',
      padding: '0.15rem 0.4rem',
      borderRadius: '10px',
      fontSize: '0.7rem',
      fontWeight: '500',
      background: status.bg,
      color: status.color,
    },
    selectorWrapper: {
      position: 'relative',
      minWidth: '250px',
      flex: '1 1 250px',
    },
    selectorBtn: {
      width: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.5rem 0.75rem',
      background: COLORS.bg,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      cursor: 'pointer',
      fontSize: '0.8rem',
      color: resolution?.resolved_table ? COLORS.text : COLORS.textMuted,
      textAlign: 'left',
    },
    dropdown: {
      position: 'absolute',
      top: '100%',
      left: 0,
      right: 0,
      marginTop: '4px',
      background: COLORS.white,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '8px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      zIndex: 100,
      maxHeight: '280px',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    },
    searchBox: {
      padding: '0.5rem',
      borderBottom: `1px solid ${COLORS.border}`,
    },
    searchInput: {
      width: '100%',
      padding: '0.5rem 0.75rem',
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      fontSize: '0.8rem',
      outline: 'none',
    },
    options: {
      overflowY: 'auto',
      maxHeight: '220px',
    },
    option: (isSelected) => ({
      padding: '0.6rem 0.75rem',
      cursor: 'pointer',
      fontSize: '0.8rem',
      background: isSelected ? COLORS.blueBg : 'transparent',
      borderLeft: isSelected ? `3px solid ${COLORS.blue}` : '3px solid transparent',
    }),
    optionName: {
      fontWeight: '500',
      color: COLORS.text,
      marginBottom: '0.1rem',
    },
    optionMeta: {
      fontSize: '0.7rem',
      color: COLORS.textMuted,
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.left}>
        <FileSpreadsheet size={16} color={COLORS.textMuted} />
        <span style={styles.label}>{dataLabel} Data</span>
        <span style={styles.badge}>
          {status.label}
        </span>
      </div>
      
      <div style={styles.selectorWrapper}>
        <button 
          style={styles.selectorBtn}
          onClick={() => setIsOpen(!isOpen)}
          disabled={saving}
        >
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
            {saving ? 'Saving...' : formatTableName(
              resolution?.resolved_table,
              availableTables.find(t => t.table_name === resolution?.resolved_table)?.file_name
            )}
          </span>
          <ChevronDown size={16} style={{ flexShrink: 0, transform: isOpen ? 'rotate(180deg)' : 'none' }} />
        </button>
        
        {isOpen && (
          <div style={styles.dropdown}>
            <div style={styles.searchBox}>
              <input
                type="text"
                placeholder="Search data sources..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={styles.searchInput}
                autoFocus
              />
            </div>
            <div style={styles.options}>
              {filteredTables.length === 0 ? (
                <div style={{ padding: '1rem', textAlign: 'center', color: COLORS.textMuted, fontSize: '0.8rem' }}>
                  No matching data found
                </div>
              ) : (
                filteredTables.map(table => (
                  <div
                    key={table.table_name}
                    style={styles.option(table.table_name === resolution?.resolved_table)}
                    onClick={() => handleSelect(table.table_name)}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f3f4f6'}
                    onMouseLeave={(e) => e.currentTarget.style.background = table.table_name === resolution?.resolved_table ? COLORS.blueBg : 'transparent'}
                  >
                    <div style={styles.optionName}>
                      {table.file_name || formatTableName(table.table_name)}
                    </div>
                    <div style={styles.optionMeta}>
                      {table.row_count?.toLocaleString() || '?'} rows
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Main component
export default function DataSourcesReview({
  instanceId,
  definition,
  projectId,
  resolutions,
  hasUnresolved,
  onResolutionChange,
  onConfirm,
  onBack
}) {
  const [availableTables, setAvailableTables] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTables();
  }, [projectId]);

  const loadTables = async () => {
    try {
      const res = await api.get(`/playbooks/tables/${projectId}`);
      setAvailableTables(res.data.tables || []);
    } catch (err) {
      console.error('Failed to load tables:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleResolutionChange = (stepId, placeholder, tableName) => {
    const newResolutions = {
      ...resolutions[stepId],
      [placeholder]: {
        ...resolutions[stepId]?.[placeholder],
        resolved_table: tableName,
        manually_set: true,
        confidence: 1.0
      }
    };
    onResolutionChange(stepId, newResolutions);
  };

  // Count stats
  const steps = definition?.steps || [];
  const stepsWithData = steps.filter(s => Object.keys(resolutions[s.id] || {}).length > 0);
  const stepsReady = stepsWithData.filter(s => {
    const stepRes = resolutions[s.id] || {};
    return Object.values(stepRes).every(r => r.resolved_table);
  });

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
      lineHeight: 1.5,
    },
    stats: {
      display: 'flex',
      gap: '1.5rem',
      marginBottom: '1.5rem',
      padding: '1rem',
      background: COLORS.white,
      borderRadius: '8px',
      border: `1px solid ${COLORS.border}`,
    },
    stat: {
      textAlign: 'center',
    },
    statValue: {
      fontSize: '1.5rem',
      fontWeight: '700',
      color: COLORS.text,
    },
    statLabel: {
      fontSize: '0.8rem',
      color: COLORS.textMuted,
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
    footerMessage: {
      fontSize: '0.9rem',
      color: hasUnresolved ? COLORS.yellow : COLORS.green,
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    confirmBtn: {
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
    backBtn: {
      padding: '0.75rem 1.5rem',
      background: 'transparent',
      color: COLORS.textMuted,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '8px',
      fontSize: '0.95rem',
      cursor: 'pointer',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.title}>
          <Database size={24} />
          Review Data Sources
        </div>
        <div style={styles.subtitle}>
          Before running analysis, confirm which data files will be used for each step.
          The system auto-matches when possible, but you should verify the selections are correct.
        </div>
      </div>

      <div style={styles.stats}>
        <div style={styles.stat}>
          <div style={styles.statValue}>{steps.length}</div>
          <div style={styles.statLabel}>Total Steps</div>
        </div>
        <div style={styles.stat}>
          <div style={styles.statValue}>{stepsWithData.length}</div>
          <div style={styles.statLabel}>Need Data</div>
        </div>
        <div style={styles.stat}>
          <div style={{ ...styles.statValue, color: stepsReady.length === stepsWithData.length ? COLORS.green : COLORS.yellow }}>
            {stepsReady.length}/{stepsWithData.length}
          </div>
          <div style={styles.statLabel}>Ready</div>
        </div>
        <div style={styles.stat}>
          <div style={styles.statValue}>{availableTables.length}</div>
          <div style={styles.statLabel}>Data Files</div>
        </div>
      </div>

      <div style={styles.stepsList}>
        {steps.map(step => (
          <StepRow
            key={step.id}
            step={step}
            resolutions={resolutions[step.id] || {}}
            availableTables={availableTables}
            onResolutionChange={handleResolutionChange}
            instanceId={instanceId}
          />
        ))}
      </div>

      <div style={styles.footer}>
        <button style={styles.backBtn} onClick={onBack}>
          Back
        </button>
        <div style={styles.footerMessage}>
          {hasUnresolved ? (
            <>
              <AlertTriangle size={18} />
              Some steps missing data - they'll be skipped
            </>
          ) : (
            <>
              <CheckCircle size={18} />
              All data sources confirmed
            </>
          )}
        </div>
        <button 
          style={styles.confirmBtn} 
          onClick={onConfirm}
        >
          Continue to Steps
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}
