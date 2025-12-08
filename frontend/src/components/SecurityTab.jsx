/**
 * SecurityTab.jsx
 * ================
 * Security administration panel for XLR8 Admin page.
 * 
 * Features:
 * - Toggle security features on/off
 * - View threat summary
 * - Configure rate limits
 * - View recent audit log
 * 
 * Author: XLR8 Platform
 * Date: December 8, 2025
 */

import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function SecurityTab() {
  const [config, setConfig] = useState(null);
  const [threats, setThreats] = useState(null);
  const [auditSummary, setAuditSummary] = useState(null);
  const [recentAudit, setRecentAudit] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState({});
  const [activeSection, setActiveSection] = useState('toggles');
  const [message, setMessage] = useState(null);

  // Fetch all security data
  useEffect(() => {
    fetchSecurityData();
  }, []);

  const fetchSecurityData = async () => {
    setLoading(true);
    try {
      const [configRes, threatsRes, auditRes, recentRes] = await Promise.all([
        api.get('/security/config').catch(() => ({ data: null })),
        api.get('/security/threats/summary').catch(() => ({ data: null })),
        api.get('/security/audit/summary?hours=24').catch(() => ({ data: null })),
        api.get('/security/audit/recent?limit=20').catch(() => ({ data: { entries: [] } })),
      ]);
      
      setConfig(configRes.data);
      setThreats(threatsRes.data);
      setAuditSummary(auditRes.data);
      setRecentAudit(recentRes.data?.entries || []);
    } catch (err) {
      console.error('Failed to fetch security data:', err);
      showMessage('Failed to load security data', 'error');
    }
    setLoading(false);
  };

  const showMessage = (text, type = 'success') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleToggle = async (key, currentValue) => {
    setSaving(prev => ({ ...prev, [key]: true }));
    try {
      await api.patch('/security/config', {
        updates: { [key]: !currentValue }
      });
      setConfig(prev => ({ ...prev, [key]: !currentValue }));
      showMessage(`${key.replace(/_/g, ' ')} ${!currentValue ? 'enabled' : 'disabled'}`);
    } catch (err) {
      console.error('Failed to toggle:', err);
      showMessage('Failed to update setting', 'error');
    }
    setSaving(prev => ({ ...prev, [key]: false }));
  };

  const handleResetDefaults = async () => {
    if (!window.confirm('Reset all security settings to defaults? This cannot be undone.')) {
      return;
    }
    try {
      const res = await api.post('/security/config/reset');
      setConfig(res.data.config);
      showMessage('Settings reset to defaults');
    } catch (err) {
      showMessage('Failed to reset settings', 'error');
    }
  };

  // Styles
  const styles = {
    container: {
      maxWidth: 1200,
    },
    message: {
      padding: '0.75rem 1rem',
      borderRadius: 8,
      marginBottom: '1rem',
      background: message?.type === 'error' ? '#fef2f2' : '#f0fdf4',
      color: message?.type === 'error' ? '#dc2626' : '#16a34a',
      border: `1px solid ${message?.type === 'error' ? '#fecaca' : '#bbf7d0'}`,
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '1.5rem',
    },
    title: {
      fontSize: '1.25rem',
      fontWeight: 600,
      color: '#1e293b',
      margin: 0,
    },
    subtitle: {
      fontSize: '0.875rem',
      color: '#64748b',
      margin: '0.25rem 0 0 0',
    },
    tabs: {
      display: 'flex',
      gap: '0.5rem',
      marginBottom: '1.5rem',
      borderBottom: '1px solid #e2e8f0',
      paddingBottom: '0.5rem',
    },
    tab: (active) => ({
      padding: '0.5rem 1rem',
      border: 'none',
      background: active ? '#f0fdf4' : 'transparent',
      color: active ? '#16a34a' : '#64748b',
      borderRadius: 6,
      cursor: 'pointer',
      fontWeight: 500,
      fontSize: '0.875rem',
      transition: 'all 0.2s ease',
    }),
    summaryGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
      gap: '1rem',
      marginBottom: '1.5rem',
    },
    summaryCard: (level) => ({
      padding: '1rem',
      borderRadius: 8,
      background: level === 2 ? '#fef2f2' : level === 1 ? '#fffbeb' : '#f0fdf4',
      border: `1px solid ${level === 2 ? '#fecaca' : level === 1 ? '#fde68a' : '#bbf7d0'}`,
    }),
    summaryValue: (level) => ({
      fontSize: '1.5rem',
      fontWeight: 700,
      color: level === 2 ? '#dc2626' : level === 1 ? '#d97706' : '#16a34a',
    }),
    summaryLabel: {
      fontSize: '0.75rem',
      color: '#64748b',
      marginTop: '0.25rem',
    },
    card: {
      background: '#fff',
      border: '1px solid #e2e8f0',
      borderRadius: 8,
      padding: '1.25rem',
      marginBottom: '1rem',
    },
    cardTitle: {
      fontSize: '0.875rem',
      fontWeight: 600,
      color: '#1e293b',
      marginBottom: '1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    toggleRow: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '0.75rem 0',
      borderBottom: '1px solid #f1f5f9',
    },
    toggleInfo: {
      flex: 1,
    },
    toggleLabel: {
      fontSize: '0.875rem',
      fontWeight: 500,
      color: '#1e293b',
    },
    toggleDesc: {
      fontSize: '0.75rem',
      color: '#64748b',
      marginTop: '0.25rem',
    },
    toggle: (enabled, saving) => ({
      width: 48,
      height: 26,
      borderRadius: 13,
      background: enabled ? '#16a34a' : '#cbd5e1',
      border: 'none',
      cursor: saving ? 'wait' : 'pointer',
      position: 'relative',
      transition: 'background 0.2s ease',
      opacity: saving ? 0.6 : 1,
    }),
    toggleKnob: (enabled) => ({
      width: 22,
      height: 22,
      borderRadius: '50%',
      background: '#fff',
      position: 'absolute',
      top: 2,
      left: enabled ? 24 : 2,
      transition: 'left 0.2s ease',
      boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
    }),
    badge: (type) => ({
      display: 'inline-block',
      padding: '0.125rem 0.5rem',
      borderRadius: 4,
      fontSize: '0.65rem',
      fontWeight: 600,
      background: type === 'safe' ? '#f0fdf4' : type === 'caution' ? '#fffbeb' : '#f1f5f9',
      color: type === 'safe' ? '#16a34a' : type === 'caution' ? '#d97706' : '#64748b',
      marginLeft: '0.5rem',
    }),
    auditTable: {
      width: '100%',
      borderCollapse: 'collapse',
      fontSize: '0.8rem',
    },
    auditTh: {
      textAlign: 'left',
      padding: '0.5rem',
      borderBottom: '2px solid #e2e8f0',
      color: '#64748b',
      fontWeight: 600,
    },
    auditTd: {
      padding: '0.5rem',
      borderBottom: '1px solid #f1f5f9',
      color: '#1e293b',
    },
    statusDot: (success) => ({
      display: 'inline-block',
      width: 8,
      height: 8,
      borderRadius: '50%',
      background: success ? '#16a34a' : '#dc2626',
      marginRight: '0.5rem',
    }),
    button: {
      padding: '0.5rem 1rem',
      border: '1px solid #e2e8f0',
      borderRadius: 6,
      background: '#fff',
      color: '#64748b',
      cursor: 'pointer',
      fontSize: '0.8rem',
      fontWeight: 500,
    },
    dangerButton: {
      padding: '0.5rem 1rem',
      border: '1px solid #fecaca',
      borderRadius: 6,
      background: '#fef2f2',
      color: '#dc2626',
      cursor: 'pointer',
      fontSize: '0.8rem',
      fontWeight: 500,
    },
    rateLimitRow: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
      padding: '0.5rem 0',
      borderBottom: '1px solid #f1f5f9',
    },
    rateLimitLabel: {
      flex: 1,
      fontSize: '0.875rem',
      fontWeight: 500,
      color: '#1e293b',
    },
    rateLimitInput: {
      width: 70,
      padding: '0.375rem 0.5rem',
      border: '1px solid #e2e8f0',
      borderRadius: 4,
      fontSize: '0.8rem',
      textAlign: 'center',
    },
    rateLimitUnit: {
      fontSize: '0.75rem',
      color: '#64748b',
    },
  };

  // Toggle item component
  const ToggleItem = ({ settingKey, label, description, badge }) => {
    const enabled = config?.[settingKey] ?? false;
    const isSaving = saving[settingKey];
    
    return (
      <div style={styles.toggleRow}>
        <div style={styles.toggleInfo}>
          <div style={styles.toggleLabel}>
            {label}
            {badge && <span style={styles.badge(badge)}>{badge === 'safe' ? 'SAFE' : 'USE CAUTION'}</span>}
          </div>
          <div style={styles.toggleDesc}>{description}</div>
        </div>
        <button
          style={styles.toggle(enabled, isSaving)}
          onClick={() => handleToggle(settingKey, enabled)}
          disabled={isSaving}
        >
          <div style={styles.toggleKnob(enabled)} />
        </button>
      </div>
    );
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
        Loading security settings...
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Message */}
      {message && <div style={styles.message}>{message.text}</div>}

      {/* Header */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>🔒 Security Settings</h2>
          <p style={styles.subtitle}>Configure security features and view threat status</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button style={styles.button} onClick={fetchSecurityData}>↻ Refresh</button>
          <button style={styles.dangerButton} onClick={handleResetDefaults}>Reset Defaults</button>
        </div>
      </div>

      {/* Threat Summary Cards */}
      {threats && (
        <div style={styles.summaryGrid}>
          <div style={styles.summaryCard(threats.overall_level)}>
            <div style={styles.summaryValue(threats.overall_level)}>
              {threats.status || 'UNKNOWN'}
            </div>
            <div style={styles.summaryLabel}>Overall Status</div>
          </div>
          <div style={styles.summaryCard(threats.open_issues > 3 ? 2 : threats.open_issues > 0 ? 1 : 0)}>
            <div style={styles.summaryValue(threats.open_issues > 3 ? 2 : threats.open_issues > 0 ? 1 : 0)}>
              {threats.open_issues || 0}
            </div>
            <div style={styles.summaryLabel}>Open Issues</div>
          </div>
          <div style={styles.summaryCard(threats.high_severity > 0 ? 2 : 0)}>
            <div style={styles.summaryValue(threats.high_severity > 0 ? 2 : 0)}>
              {threats.high_severity || 0}
            </div>
            <div style={styles.summaryLabel}>High Severity</div>
          </div>
          <div style={styles.summaryCard(0)}>
            <div style={styles.summaryValue(0)}>
              {auditSummary?.total_events || 0}
            </div>
            <div style={styles.summaryLabel}>Events (24h)</div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div style={styles.tabs}>
        <button style={styles.tab(activeSection === 'toggles')} onClick={() => setActiveSection('toggles')}>
          ⚡ Feature Toggles
        </button>
        <button style={styles.tab(activeSection === 'rates')} onClick={() => setActiveSection('rates')}>
          🚦 Rate Limits
        </button>
        <button style={styles.tab(activeSection === 'audit')} onClick={() => setActiveSection('audit')}>
          📋 Audit Log
        </button>
      </div>

      {/* Feature Toggles Section */}
      {activeSection === 'toggles' && (
        <>
          {/* Middleware Toggles */}
          <div style={styles.card}>
            <div style={styles.cardTitle}>
              🛡️ Security Middleware
              <span style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 'normal' }}>
                (applies to all API requests)
              </span>
            </div>
            
            <ToggleItem
              settingKey="rate_limiting_enabled"
              label="Rate Limiting"
              description="Limit how many requests per minute. Prevents abuse and flooding."
              badge="caution"
            />
            
            <ToggleItem
              settingKey="input_validation_enabled"
              label="Input Validation"
              description="Block potentially malicious inputs (SQL injection, path traversal)."
              badge="caution"
            />
            
            <ToggleItem
              settingKey="audit_logging_enabled"
              label="Audit Logging"
              description="Record all API requests for compliance and debugging."
              badge="safe"
            />
            
            <ToggleItem
              settingKey="security_headers_enabled"
              label="Security Headers"
              description="Add browser security headers (CSP, HSTS, X-Frame-Options)."
              badge="safe"
            />
          </div>

          {/* PII & Prompt */}
          <div style={styles.card}>
            <div style={styles.cardTitle}>
              🔐 Data Protection
            </div>
            
            <ToggleItem
              settingKey="prompt_sanitization_enabled"
              label="Prompt Sanitization"
              description="Block prompt injection attempts (ignore instructions, jailbreaks)."
              badge="safe"
            />
            
            <ToggleItem
              settingKey="prompt_sanitization_log_only"
              label="Log Only Mode (Prompt)"
              description="Log suspicious prompts but don't block them. Good for testing."
              badge="safe"
            />
            
            <ToggleItem
              settingKey="pii_scan_before_llm"
              label="PII Scan Before LLM"
              description="Scan for SSN/email/phone before sending to external AI."
              badge="safe"
            />
            
            <ToggleItem
              settingKey="pii_auto_scan_uploads"
              label="Auto-Scan Uploads for PII"
              description="Automatically scan all uploaded files for sensitive data."
              badge="caution"
            />
          </div>
        </>
      )}

      {/* Rate Limits Section */}
      {activeSection === 'rates' && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>🚦 Rate Limit Configuration</div>
          <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '1rem' }}>
            These limits only apply when Rate Limiting is enabled above.
          </p>
          
          {config?.rate_limits && Object.entries(config.rate_limits).map(([resource, limit]) => (
            <div key={resource} style={styles.rateLimitRow}>
              <div style={styles.rateLimitLabel}>
                {resource.replace(/_/g, ' ').toUpperCase()}
              </div>
              <input
                type="number"
                style={styles.rateLimitInput}
                value={limit.max_requests}
                readOnly
              />
              <span style={styles.rateLimitUnit}>requests per</span>
              <input
                type="number"
                style={styles.rateLimitInput}
                value={limit.period_seconds}
                readOnly
              />
              <span style={styles.rateLimitUnit}>seconds</span>
            </div>
          ))}
          
          <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '1rem' }}>
            To modify limits, use the API: PUT /api/security/config/rate-limits/[resource]
          </p>
        </div>
      )}

      {/* Audit Log Section */}
      {activeSection === 'audit' && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>📋 Recent Activity (Last 20 Events)</div>
          
          {recentAudit.length === 0 ? (
            <p style={{ color: '#64748b', textAlign: 'center', padding: '2rem' }}>
              No audit events recorded yet.
            </p>
          ) : (
            <table style={styles.auditTable}>
              <thead>
                <tr>
                  <th style={styles.auditTh}>Time</th>
                  <th style={styles.auditTh}>Action</th>
                  <th style={styles.auditTh}>Resource</th>
                  <th style={styles.auditTh}>User</th>
                  <th style={styles.auditTh}>Status</th>
                </tr>
              </thead>
              <tbody>
                {recentAudit.map((entry, i) => (
                  <tr key={i}>
                    <td style={styles.auditTd}>
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </td>
                    <td style={styles.auditTd}>{entry.action}</td>
                    <td style={styles.auditTd}>{entry.resource_type}</td>
                    <td style={styles.auditTd}>{entry.user_id || '-'}</td>
                    <td style={styles.auditTd}>
                      <span style={styles.statusDot(entry.success)} />
                      {entry.success ? 'OK' : 'FAILED'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Last Updated */}
      {config?.last_updated && (
        <p style={{ fontSize: '0.75rem', color: '#94a3b8', textAlign: 'right', marginTop: '1rem' }}>
          Last updated: {new Date(config.last_updated).toLocaleString()} by {config.updated_by || 'system'}
        </p>
      )}
    </div>
  );
}
