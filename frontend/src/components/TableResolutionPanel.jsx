/**
 * TableResolutionPanel - Data Source Selection for Playbook Steps
 * 
 * Shows which data tables will be analyzed for a playbook step.
 * Allows consultants to verify or change the data source before running analysis.
 * 
 * Design: Non-technical, clear language. "Data Source" not "Table Resolution"
 * 
 * Created: January 18, 2026
 */

import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { 
  Database, CheckCircle, AlertTriangle, Search, 
  ChevronDown, RefreshCw, HelpCircle, FileSpreadsheet
} from 'lucide-react';

// Match YearEndPlaybook colors
const COLORS = {
  primary: '#83b16d',
  turkishSea: '#285390',
  text: '#2a3441',
  textLight: '#5f6c7b',
  border: '#e5e7eb',
  inputBg: '#f9fafb',
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

// Confidence levels with user-friendly labels
const CONFIDENCE_CONFIG = {
  high: { 
    min: 0.8, 
    color: COLORS.green, 
    bg: COLORS.greenBg, 
    icon: CheckCircle,
    label: 'Auto-matched',
    hint: 'System found a good match'
  },
  medium: { 
    min: 0.5, 
    color: COLORS.yellow, 
    bg: COLORS.yellowBg, 
    icon: AlertTriangle,
    label: 'Please verify',
    hint: 'System made a guess - please confirm'
  },
  low: { 
    min: 0, 
    color: COLORS.red, 
    bg: COLORS.redBg, 
    icon: AlertTriangle,
    label: 'Needs selection',
    hint: 'Could not find matching data'
  },
  manual: {
    min: 1,
    color: COLORS.blue,
    bg: COLORS.blueBg,
    icon: CheckCircle,
    label: 'You selected',
    hint: 'Manually chosen data source'
  }
};

const getConfidenceLevel = (resolution) => {
  if (resolution.manually_set) return CONFIDENCE_CONFIG.manual;
  if (!resolution.resolved_table) return CONFIDENCE_CONFIG.low;
  if (resolution.confidence >= 0.8) return CONFIDENCE_CONFIG.high;
  if (resolution.confidence >= 0.5) return CONFIDENCE_CONFIG.medium;
  return CONFIDENCE_CONFIG.low;
};

// Format table name for display (make it human-readable)
const formatTableName = (tableName, fileName) => {
  if (fileName) return fileName;
  if (!tableName) return 'No data selected';
  
  // Convert tea1000_employee_conversion_testing_team_us_1_fit → Employee Conversion Testing (FIT)
  let display = tableName
    .replace(/^[a-z]+\d+_/i, '')  // Remove project prefix
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
  
  return display;
};

// Single resolution row
function ResolutionRow({ 
  placeholder, 
  resolution, 
  availableTables, 
  onSelect, 
  onRefresh,
  isLoading 
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  const confidence = getConfidenceLevel(resolution);
  const ConfidenceIcon = confidence.icon;
  
  // Filter tables by search
  const filteredTables = availableTables.filter(t => 
    !searchTerm || 
    t.table_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (t.file_name && t.file_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );
  
  // Format the placeholder for display
  const dataLabel = placeholder
    .replace(/_data$/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());

  const styles = {
    row: {
      background: COLORS.white,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '8px',
      padding: '0.75rem',
      marginBottom: '0.5rem',
    },
    header: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '0.75rem',
    },
    labelSection: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      flex: 1,
    },
    icon: {
      color: COLORS.textLight,
      flexShrink: 0,
    },
    label: {
      fontSize: '0.85rem',
      fontWeight: '600',
      color: COLORS.text,
    },
    confidenceBadge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.25rem',
      padding: '0.2rem 0.5rem',
      borderRadius: '12px',
      fontSize: '0.7rem',
      fontWeight: '500',
      background: confidence.bg,
      color: confidence.color,
    },
    selector: {
      position: 'relative',
      minWidth: '280px',
    },
    selectorButton: {
      width: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.5rem 0.75rem',
      background: COLORS.inputBg,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      cursor: 'pointer',
      fontSize: '0.8rem',
      color: resolution.resolved_table ? COLORS.text : COLORS.textLight,
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
      maxHeight: '300px',
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
      paddingLeft: '2rem',
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      fontSize: '0.8rem',
      outline: 'none',
    },
    searchIcon: {
      position: 'absolute',
      left: '1rem',
      top: '50%',
      transform: 'translateY(-50%)',
      color: COLORS.textLight,
    },
    optionsList: {
      overflowY: 'auto',
      maxHeight: '240px',
    },
    option: (isSelected) => ({
      padding: '0.6rem 0.75rem',
      cursor: 'pointer',
      fontSize: '0.8rem',
      background: isSelected ? COLORS.blueBg : 'transparent',
      borderLeft: isSelected ? `3px solid ${COLORS.blue}` : '3px solid transparent',
      transition: 'background 0.15s',
    }),
    optionName: {
      fontWeight: '500',
      color: COLORS.text,
      marginBottom: '0.15rem',
    },
    optionMeta: {
      fontSize: '0.7rem',
      color: COLORS.textLight,
    },
    hint: {
      fontSize: '0.7rem',
      color: COLORS.textLight,
      marginTop: '0.35rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.25rem',
    },
  };

  return (
    <div style={styles.row}>
      <div style={styles.header}>
        {/* Label + Confidence */}
        <div style={styles.labelSection}>
          <FileSpreadsheet size={16} style={styles.icon} />
          <span style={styles.label}>{dataLabel} Data</span>
          <span style={styles.confidenceBadge}>
            <ConfidenceIcon size={12} />
            {confidence.label}
          </span>
        </div>
        
        {/* Selector Dropdown */}
        <div style={styles.selector}>
          <button 
            style={styles.selectorButton}
            onClick={() => setIsOpen(!isOpen)}
            disabled={isLoading}
          >
            <span style={{ 
              overflow: 'hidden', 
              textOverflow: 'ellipsis', 
              whiteSpace: 'nowrap',
              flex: 1 
            }}>
              {isLoading ? 'Loading...' : formatTableName(
                resolution.resolved_table,
                availableTables.find(t => t.table_name === resolution.resolved_table)?.file_name
              )}
            </span>
            <ChevronDown size={16} style={{ 
              flexShrink: 0,
              transform: isOpen ? 'rotate(180deg)' : 'none',
              transition: 'transform 0.2s'
            }} />
          </button>
          
          {isOpen && (
            <div style={styles.dropdown}>
              {/* Search */}
              <div style={styles.searchBox}>
                <div style={{ position: 'relative' }}>
                  <Search size={14} style={styles.searchIcon} />
                  <input
                    type="text"
                    placeholder="Search data sources..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={styles.searchInput}
                    autoFocus
                  />
                </div>
              </div>
              
              {/* Options */}
              <div style={styles.optionsList}>
                {filteredTables.length === 0 ? (
                  <div style={{ padding: '1rem', textAlign: 'center', color: COLORS.textLight, fontSize: '0.8rem' }}>
                    No matching data found
                  </div>
                ) : (
                  filteredTables.map((table) => (
                    <div
                      key={table.table_name}
                      style={styles.option(table.table_name === resolution.resolved_table)}
                      onClick={() => {
                        onSelect(placeholder, table.table_name);
                        setIsOpen(false);
                        setSearchTerm('');
                      }}
                      onMouseEnter={(e) => e.target.style.background = '#f3f4f6'}
                      onMouseLeave={(e) => e.target.style.background = table.table_name === resolution.resolved_table ? COLORS.blueBg : 'transparent'}
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
      
      {/* Hint text */}
      {!resolution.manually_set && resolution.confidence < 0.8 && (
        <div style={styles.hint}>
          <HelpCircle size={12} />
          {confidence.hint}
        </div>
      )}
    </div>
  );
}

// Main panel component
export default function TableResolutionPanel({ 
  instanceId, 
  stepId, 
  projectId,
  onResolutionsChange 
}) {
  const [resolutions, setResolutions] = useState({});
  const [availableTables, setAvailableTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hasUnresolved, setHasUnresolved] = useState(false);

  // Load resolutions and available tables
  useEffect(() => {
    loadData();
  }, [instanceId, stepId, projectId]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [resolutionRes, tablesRes] = await Promise.all([
        api.get(`/playbooks/instance/${instanceId}/step/${stepId}/resolve`),
        api.get(`/playbooks/tables/${projectId}`)
      ]);
      
      setResolutions(resolutionRes.data.resolutions || {});
      setHasUnresolved(resolutionRes.data.has_unresolved || false);
      setAvailableTables(tablesRes.data.tables || []);
      
    } catch (err) {
      console.error('Failed to load resolutions:', err);
      setError('Failed to load data sources');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async (placeholder, tableName) => {
    try {
      await api.post(`/playbooks/instance/${instanceId}/step/${stepId}/resolve`, {
        placeholder,
        table_name: tableName
      });
      
      // Update local state
      setResolutions(prev => ({
        ...prev,
        [placeholder]: {
          ...prev[placeholder],
          resolved_table: tableName,
          manually_set: true,
          confidence: 1.0
        }
      }));
      
      // Notify parent
      onResolutionsChange?.();
      
    } catch (err) {
      console.error('Failed to set resolution:', err);
    }
  };

  const placeholders = Object.keys(resolutions);
  
  // Don't show panel if no placeholders
  if (!loading && placeholders.length === 0) {
    return null;
  }

  const styles = {
    panel: {
      background: '#f8fafc',
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      padding: '1rem',
      marginBottom: '1rem',
    },
    header: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '0.75rem',
    },
    title: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '0.85rem',
      fontWeight: '600',
      color: COLORS.text,
    },
    subtitle: {
      fontSize: '0.75rem',
      color: COLORS.textLight,
      marginBottom: '0.75rem',
    },
    refreshBtn: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.25rem',
      padding: '0.35rem 0.6rem',
      background: 'transparent',
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      fontSize: '0.75rem',
      color: COLORS.textLight,
      cursor: 'pointer',
    },
    error: {
      background: COLORS.redBg,
      color: COLORS.red,
      padding: '0.75rem',
      borderRadius: '6px',
      fontSize: '0.8rem',
      marginBottom: '0.75rem',
    },
    warning: {
      background: COLORS.yellowBg,
      color: COLORS.yellow,
      padding: '0.6rem 0.75rem',
      borderRadius: '6px',
      fontSize: '0.8rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      marginTop: '0.75rem',
    },
    loading: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
      color: COLORS.textLight,
      gap: '0.5rem',
      fontSize: '0.85rem',
    },
  };

  if (loading) {
    return (
      <div style={styles.panel}>
        <div style={styles.loading}>
          <RefreshCw size={16} className="spin" />
          Loading data sources...
        </div>
      </div>
    );
  }

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <div style={styles.title}>
          <Database size={16} />
          Data Sources for This Step
        </div>
        <button style={styles.refreshBtn} onClick={loadData}>
          <RefreshCw size={12} />
          Refresh
        </button>
      </div>
      
      <div style={styles.subtitle}>
        Select which data to analyze. The system auto-matches when possible.
      </div>
      
      {error && <div style={styles.error}>{error}</div>}
      
      {placeholders.map(placeholder => (
        <ResolutionRow
          key={placeholder}
          placeholder={placeholder}
          resolution={resolutions[placeholder]}
          availableTables={availableTables}
          onSelect={handleSelect}
          onRefresh={loadData}
          isLoading={loading}
        />
      ))}
      
      {hasUnresolved && (
        <div style={styles.warning}>
          <AlertTriangle size={16} />
          Some data sources need to be selected before running analysis.
        </div>
      )}
      
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
