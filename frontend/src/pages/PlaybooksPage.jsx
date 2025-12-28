/**
 * PlaybooksPage - Analysis Playbooks
 * 
 * UPDATED: Added Configure button for admins to link standards to playbooks
 * 
 * - Run pre-built analysis playbooks against project data
 * - Create new playbooks via Work Advisor
 * - Configure playbooks to link standards (admin only)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useProject } from '../context/ProjectContext';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import YearEndPlaybook from '../components/YearEndPlaybook';
import { LoadingSpinner, ErrorState, EmptyState, PageHeader, Card } from '../components/ui';
import api from '../services/api';
import { getCustomerColorPalette } from '../utils/customerColors';

// Mission Control Colors
const colors = {
  bg: '#f0f2f5',
  card: '#ffffff',
  cardBorder: '#e2e8f0',
  text: '#1a2332',
  textMuted: '#64748b',
  textLight: '#94a3b8',
  primary: '#83b16d',
  primaryLight: 'rgba(131, 177, 109, 0.1)',
  accent: '#285390',
  accentLight: 'rgba(40, 83, 144, 0.1)',
  warning: '#d97706',
  warningLight: 'rgba(217, 119, 6, 0.1)',
  red: '#dc2626',
  redLight: 'rgba(220, 38, 38, 0.1)',
  green: '#16a34a',
  greenLight: 'rgba(22, 163, 74, 0.1)',
  purple: '#7c3aed',
  purpleLight: 'rgba(124, 58, 237, 0.1)',
  divider: '#e2e8f0',
  inputBg: '#f8fafc',
};

// Category colors - Mission Control palette
const CATEGORY_COLORS = {
  'Year-End': { color: '#83b16d', bg: 'rgba(131, 177, 109, 0.1)' },
  'Compliance': { color: '#285390', bg: 'rgba(40, 83, 144, 0.1)' },
  'Regulatory': { color: '#d97706', bg: 'rgba(217, 119, 6, 0.1)' },
  'Audit': { color: '#7c3aed', bg: 'rgba(124, 58, 237, 0.1)' },
  'Implementation': { color: '#0891b2', bg: 'rgba(8, 145, 178, 0.1)' },
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
    hasRunner: true,  // Now enabled with standards linkage!
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

// =============================================================================
// PLAYBOOK CONFIG MODAL - Link standards to playbooks
// =============================================================================

function PlaybookConfigModal({ playbook, projectId, onClose, onExecute }) {
  const [linkedStandards, setLinkedStandards] = useState([]);
  const [availableStandards, setAvailableStandards] = useState([]);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [showAvailable, setShowAvailable] = useState(false);
  const [showRules, setShowRules] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);

  const playbook_id = playbook?.id;

  useEffect(() => {
    if (playbook_id) {
      loadData();
    }
  }, [playbook_id]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Load playbook info with linked standards
      try {
        const infoRes = await api.get(`/playbooks/${playbook_id}/info`);
        setLinkedStandards(infoRes.data.linked_standards || []);
        setRules(infoRes.data.rules || []);
      } catch (e) {
        console.log('Playbook info not available yet:', e);
        setLinkedStandards([]);
        setRules([]);
      }
      
      // Load available standards
      try {
        const availRes = await api.get('/playbooks/available-standards');
        setAvailableStandards(availRes.data.standards || []);
      } catch (e) {
        console.log('Available standards not loaded:', e);
        setAvailableStandards([]);
      }
      
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleLink = async (standardId) => {
    setLinking(true);
    setError(null);
    try {
      await api.post(`/playbooks/${playbook_id}/standards`, {
        standard_id: standardId,
        usage_type: 'compliance'
      });
      setSuccessMsg('Standard linked!');
      setTimeout(() => setSuccessMsg(null), 3000);
      await loadData();
    } catch (err) {
      console.error('Failed to link standard:', err);
      setError('Failed to link standard');
    } finally {
      setLinking(false);
    }
  };

  const handleUnlink = async (standardId) => {
    setError(null);
    try {
      await api.delete(`/playbooks/${playbook_id}/standards/${standardId}`);
      setSuccessMsg('Standard unlinked');
      setTimeout(() => setSuccessMsg(null), 3000);
      await loadData();
    } catch (err) {
      console.error('Failed to unlink standard:', err);
      setError('Failed to unlink standard');
    }
  };

  const handleExecute = async () => {
    if (!projectId) {
      setError('No project selected');
      return;
    }
    
    setExecuting(true);
    setError(null);
    setExecutionResult(null);
    
    try {
      const res = await api.post(`/playbooks/execute/${playbook_id}`, {
        project_id: projectId,
        run_by: 'user'
      });
      setExecutionResult(res.data);
      setSuccessMsg(`Playbook complete! ${res.data.violations_found} issues found.`);
    } catch (err) {
      console.error('Execution failed:', err);
      setError('Failed to run playbook: ' + (err.response?.data?.detail || err.message));
    } finally {
      setExecuting(false);
    }
  };

  // Filter out already linked standards
  const linkedIds = linkedStandards.map(ls => ls.id);
  const unlinkedStandards = availableStandards.filter(s => !linkedIds.includes(s.id));

  const modalStyles = {
    overlay: {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '2rem',
    },
    modal: {
      background: 'white',
      borderRadius: '16px',
      width: '100%',
      maxWidth: '640px',
      maxHeight: '85vh',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
    },
    header: {
      padding: '1.5rem',
      borderBottom: '1px solid #e8ecef',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    headerLeft: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
    },
    icon: {
      width: '52px',
      height: '52px',
      borderRadius: '12px',
      background: 'linear-gradient(135deg, #83b16d 0%, #6b9b5a 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '1.5rem',
    },
    title: {
      margin: 0,
      fontSize: '1.25rem',
      fontWeight: '700',
      color: '#2a3441',
    },
    subtitle: {
      margin: 0,
      fontSize: '0.85rem',
      color: '#6b7280',
    },
    closeBtn: {
      padding: '0.5rem',
      background: '#f5f7f9',
      border: 'none',
      borderRadius: '8px',
      cursor: 'pointer',
      color: '#6b7280',
      fontSize: '1.25rem',
    },
    body: {
      flex: 1,
      overflow: 'auto',
      padding: '1.5rem',
    },
    section: {
      marginBottom: '1.5rem',
    },
    sectionHeader: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '0.75rem',
    },
    sectionTitle: {
      fontSize: '0.9rem',
      fontWeight: '600',
      color: '#2a3441',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    badge: {
      padding: '0.25rem 0.6rem',
      background: rules.length > 0 ? '#dcfce7' : '#f3f4f6',
      color: rules.length > 0 ? '#4a6a4a' : '#6b7280',
      borderRadius: '12px',
      fontSize: '0.75rem',
      fontWeight: '600',
    },
    linkedItem: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.75rem 1rem',
      background: '#f8faf9',
      borderRadius: '10px',
      border: '1px solid #e8ecef',
      marginBottom: '0.5rem',
    },
    linkedIcon: {
      width: '36px',
      height: '36px',
      borderRadius: '8px',
      background: '#285390',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'white',
      marginRight: '0.75rem',
    },
    unlinkBtn: {
      padding: '0.4rem 0.75rem',
      background: 'white',
      border: '1px solid #fecaca',
      borderRadius: '6px',
      color: '#8a4a4a',
      cursor: 'pointer',
      fontSize: '0.8rem',
    },
    addBtn: {
      width: '100%',
      padding: '0.75rem',
      background: showAvailable ? '#f0f4f7' : 'white',
      border: '2px dashed #d1d5db',
      borderRadius: '10px',
      color: '#6b7280',
      cursor: 'pointer',
      fontSize: '0.85rem',
      fontWeight: '600',
      marginTop: '0.5rem',
    },
    dropdown: {
      marginTop: '0.75rem',
      background: '#f8faf9',
      borderRadius: '10px',
      border: '1px solid #e8ecef',
      maxHeight: '180px',
      overflow: 'auto',
    },
    dropdownItem: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.75rem 1rem',
      borderBottom: '1px solid #e8ecef',
    },
    linkBtn: {
      padding: '0.35rem 0.75rem',
      background: '#83b16d',
      border: 'none',
      borderRadius: '6px',
      color: 'white',
      cursor: 'pointer',
      fontSize: '0.8rem',
      fontWeight: '600',
    },
    alert: (type) => ({
      padding: '0.75rem 1rem',
      background: type === 'error' ? '#fef2f2' : '#f0fdf4',
      border: `1px solid ${type === 'error' ? '#fecaca' : '#bbf7d0'}`,
      borderRadius: '8px',
      color: type === 'error' ? '#8a4a4a' : '#4a6a4a',
      fontSize: '0.85rem',
      marginBottom: '1rem',
    }),
    footer: {
      padding: '1rem 1.5rem',
      borderTop: '1px solid #e8ecef',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    executeBtn: {
      padding: '0.75rem 1.5rem',
      background: 'linear-gradient(135deg, #83b16d 0%, #6b9b5a 100%)',
      border: 'none',
      borderRadius: '8px',
      color: 'white',
      fontWeight: '600',
      fontSize: '0.9rem',
      cursor: 'pointer',
      boxShadow: '0 2px 8px rgba(131, 177, 109, 0.3)',
    },
    resultCard: {
      padding: '1rem',
      background: '#f0fdf4',
      border: '1px solid #bbf7d0',
      borderRadius: '10px',
      marginTop: '1rem',
    },
    resultTitle: {
      fontWeight: '700',
      color: '#4a6a4a',
      marginBottom: '0.5rem',
    },
    findingItem: {
      padding: '0.5rem 0',
      borderBottom: '1px solid #dcfce7',
      fontSize: '0.85rem',
    },
  };

  return (
    <div style={modalStyles.overlay} onClick={onClose}>
      <div style={modalStyles.modal} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={modalStyles.header}>
          <div style={modalStyles.headerLeft}>
            <div style={modalStyles.icon}>{playbook?.icon || '📋'}</div>
            <div>
              <h2 style={modalStyles.title}>{playbook?.name || 'Configure Playbook'}</h2>
              <p style={modalStyles.subtitle}>Link standards for compliance checking</p>
            </div>
          </div>
          <button style={modalStyles.closeBtn} onClick={onClose}>×</button>
        </div>

        {/* Body */}
        <div style={modalStyles.body}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>
              <p style={{ color: '#6b7280' }}>Loading...</p>
            </div>
          ) : (
            <>
              {/* Alerts */}
              {error && <div style={modalStyles.alert('error')}>{error}</div>}
              {successMsg && <div style={modalStyles.alert('success')}>{successMsg}</div>}

              {/* Linked Standards */}
              <div style={modalStyles.section}>
                <div style={modalStyles.sectionHeader}>
                  <div style={modalStyles.sectionTitle}>
                    🛡️ Linked Standards
                  </div>
                  <span style={modalStyles.badge}>{rules.length} rules</span>
                </div>

                {linkedStandards.length > 0 ? (
                  linkedStandards.map(ls => (
                    <div key={ls.id} style={modalStyles.linkedItem}>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <div style={modalStyles.linkedIcon}>📄</div>
                        <div>
                          <div style={{ fontWeight: '600', color: '#2a3441' }}>
                            {ls.name || `Standard ${ls.id}`}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                            {ls.domain || 'General'}
                          </div>
                        </div>
                      </div>
                      <button style={modalStyles.unlinkBtn} onClick={() => handleUnlink(ls.id)}>
                        Unlink
                      </button>
                    </div>
                  ))
                ) : (
                  <div style={{ padding: '1.5rem', textAlign: 'center', color: '#6b7280', background: '#f8faf9', borderRadius: '10px' }}>
                    <p style={{ margin: 0 }}>No standards linked yet</p>
                    <p style={{ fontSize: '0.8rem', margin: '0.25rem 0 0' }}>
                      Link a standard to enable compliance checking
                    </p>
                  </div>
                )}

                {/* Add Standard */}
                {availableStandards.length > 0 && (
                  <>
                    <button style={modalStyles.addBtn} onClick={() => setShowAvailable(!showAvailable)}>
                      ➕ Link a Standard {showAvailable ? '▲' : '▼'}
                    </button>

                    {showAvailable && (
                      <div style={modalStyles.dropdown}>
                        {unlinkedStandards.length > 0 ? (
                          unlinkedStandards.map(s => (
                            <div key={s.id} style={modalStyles.dropdownItem}>
                              <div>
                                <div style={{ fontWeight: '600', color: '#2a3441' }}>{s.title || s.filename}</div>
                                <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{s.domain || 'General'}</div>
                              </div>
                              <button style={modalStyles.linkBtn} onClick={() => handleLink(s.id)} disabled={linking}>
                                {linking ? '...' : 'Link'}
                              </button>
                            </div>
                          ))
                        ) : (
                          <div style={{ padding: '1rem', textAlign: 'center', color: '#6b7280' }}>
                            All standards are linked
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}

                {availableStandards.length === 0 && linkedStandards.length === 0 && (
                  <div style={{ padding: '1rem', background: '#fef3c7', borderRadius: '8px', marginTop: '0.75rem', fontSize: '0.85rem' }}>
                    ⚠️ No standards uploaded yet. Go to <strong>Standards</strong> page to upload compliance documents first.
                  </div>
                )}
              </div>

              {/* Rules Preview */}
              {rules.length > 0 && (
                <div style={modalStyles.section}>
                  <button 
                    style={{ ...modalStyles.addBtn, border: '1px solid #e8ecef' }}
                    onClick={() => setShowRules(!showRules)}
                  >
                    ✓ View {rules.length} Rules {showRules ? '▲' : '▼'}
                  </button>
                  
                  {showRules && (
                    <div style={{ ...modalStyles.dropdown, marginTop: '0.5rem' }}>
                      {rules.map((rule, i) => (
                        <div key={i} style={{ padding: '0.6rem 1rem', borderBottom: '1px solid #e8ecef', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{
                            width: '8px', height: '8px', borderRadius: '50%',
                            background: { critical: '#8a4a4a', high: '#8a6b4a', medium: '#7a6a3a', low: '#5a8a5a' }[rule.severity] || '#9ca3af'
                          }} />
                          <span style={{ fontSize: '0.85rem', color: '#2a3441' }}>{rule.title}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Execution Result */}
              {executionResult && (
                <div style={modalStyles.resultCard}>
                  <div style={modalStyles.resultTitle}>
                    ✅ Playbook Complete
                  </div>
                  <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                    <strong>{executionResult.total_rules_checked}</strong> rules checked • 
                    <strong style={{ color: executionResult.violations_found > 0 ? '#8a4a4a' : '#4a6a4a' }}> {executionResult.violations_found}</strong> violations • 
                    <strong style={{ color: '#8a6b4a' }}> {executionResult.warnings_found}</strong> warnings
                  </div>
                  {executionResult.findings?.length > 0 && (
                    <div style={{ marginTop: '0.75rem' }}>
                      <div style={{ fontWeight: '600', fontSize: '0.85rem', marginBottom: '0.5rem' }}>Findings:</div>
                      {executionResult.findings.slice(0, 5).map((f, i) => (
                        <div key={i} style={modalStyles.findingItem}>
                          <span style={{
                            display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', marginRight: '0.5rem',
                            background: { critical: '#8a4a4a', high: '#8a6b4a', medium: '#7a6a3a', low: '#5a8a5a' }[f.severity] || '#9ca3af'
                          }} />
                          {f.title} ({f.affected_count} affected)
                        </div>
                      ))}
                      {executionResult.findings.length > 5 && (
                        <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '0.5rem' }}>
                          ...and {executionResult.findings.length - 5} more
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div style={modalStyles.footer}>
          <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
            {linkedStandards.length > 0 
              ? `${linkedStandards.length} standard${linkedStandards.length > 1 ? 's' : ''} linked`
              : 'Link standards to run compliance checks'
            }
          </div>
          <button 
            style={{
              ...modalStyles.executeBtn,
              opacity: (rules.length === 0 || executing) ? 0.5 : 1,
              cursor: (rules.length === 0 || executing) ? 'not-allowed' : 'pointer',
            }}
            onClick={handleExecute}
            disabled={rules.length === 0 || executing}
          >
            {executing ? '⏳ Running...' : '▶️ Run Playbook'}
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// PLAYBOOK CARD COMPONENT
// =============================================================================

function PlaybookCard({ playbook, onRun, onConfigure, hasProgress, isAssigned, isAdmin }) {
  const styles = {
    card: {
      background: 'white',
      borderRadius: '12px',
      padding: '1.5rem',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      border: playbook.hasRunner ? `2px solid '#83b16d'` : '1px solid #e1e8ed',
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
      background: '#e8ecf1',
      borderRadius: '10px',
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.1rem',
      fontWeight: '700',
      color: '#2a3441',
      marginBottom: '0.25rem',
    },
    category: {
      fontSize: '0.75rem',
      color: '#83b16d',
      fontWeight: '600',
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
    },
    description: {
      color: '#6b7280',
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
      color: '#6b7280',
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
      color: '#6b7280',
    },
    buttons: {
      display: 'flex',
      gap: '0.5rem',
    },
    configBtn: {
      padding: '0.5rem 0.75rem',
      background: '#f5f7f9',
      border: '1px solid #e1e8ed',
      borderRadius: '6px',
      color: '#6b7280',
      fontWeight: '600',
      fontSize: '0.8rem',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.35rem',
    },
    button: {
      padding: '0.5rem 1rem',
      background: playbook.hasRunner ? '#83b16d' : '#6b7280',
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
        <div style={styles.buttons}>
          {isAdmin && (
            <button 
              style={styles.configBtn}
              onClick={(e) => {
                e.stopPropagation();
                onConfigure(playbook);
              }}
            >
              ⚙️ Configure
            </button>
          )}
          <button 
            style={styles.button} 
            onClick={() => onRun(playbook)}
            disabled={!playbook.hasRunner}
          >
            {playbook.hasRunner ? (hasProgress ? 'Continue →' : 'Kickoff →') : 'Coming Soon'}
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN PAGE COMPONENT
// =============================================================================

export default function PlaybooksPage() {
  const { activeProject, projectName, customerName, hasActiveProject, loading: projectLoading } = useProject();
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [activePlaybook, setActivePlaybook] = useState(null);
  const [configPlaybook, setConfigPlaybook] = useState(null);
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

  if (projectLoading || loading) {
    return <LoadingSpinner fullPage message="Loading playbooks..." />;
  }

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

  const assignedPlaybookIds = activeProject?.playbooks || [];
  const availablePlaybooks = PLAYBOOKS.filter(p => assignedPlaybookIds.includes(p.id));

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
      background: active ? '#83b16d' : '#f0f4f7',
      border: 'none',
      borderRadius: '20px',
      color: active ? 'white' : '#6b7280',
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
      <PageHeader
        title="Playbooks"
        subtitle="Run pre-built analysis templates to generate deliverables."
        breadcrumbs={[
          { label: customerName },
          { label: projectName },
        ]}
        action={isAdmin ? {
          label: 'Work Advisor',
          icon: '💡',
          to: '/advisor',
        } : null}
      />

      {error && (
        <ErrorState
          compact
          title="Failed to load progress"
          message={error}
          onRetry={fetchPlaybookProgress}
        />
      )}

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

      <div style={styles.grid}>
        {filteredPlaybooks.map(playbook => (
          <PlaybookCard 
            key={playbook.id}
            playbook={playbook} 
            onRun={handleRunPlaybook}
            onConfigure={setConfigPlaybook}
            hasProgress={playbookProgress[playbook.id] || false}
            isAssigned={true}
            isAdmin={isAdmin}
          />
        ))}
      </div>

      {configPlaybook && (
        <PlaybookConfigModal
          playbook={configPlaybook}
          projectId={activeProject?.id}
          onClose={() => setConfigPlaybook(null)}
          onExecute={(pb) => {
            setConfigPlaybook(null);
            handleRunPlaybook(pb);
          }}
        />
      )}
    </div>
  );
}
