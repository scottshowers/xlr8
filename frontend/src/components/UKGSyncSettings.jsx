/**
 * UKGSyncSettings.jsx - Sync Configuration Panel
 * ===============================================
 * 
 * Deploy to: frontend/src/components/UKGSyncSettings.jsx
 * 
 * Allows users to configure which UKG endpoints to sync and with what filters.
 */

import React, { useState, useEffect } from 'react';
import { Settings, Save, X, Loader2, CheckCircle, Calendar, Users, Briefcase, FileText, Clock, GraduationCap, Phone, Palmtree } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

// Endpoint metadata for display
const ENDPOINT_INFO = {
  person_details: {
    label: 'Person Details',
    description: 'Core employee demographics, names, addresses',
    icon: Users,
  },
  employment_details: {
    label: 'Employment Details',
    description: 'Job assignments, departments, supervisors',
    icon: Briefcase,
  },
  compensation_details: {
    label: 'Compensation Details',
    description: 'Pay rates, salary grades, shift codes',
    icon: FileText,
  },
  employee_job_history: {
    label: 'Job History',
    description: 'Promotions, transfers, position changes',
    icon: Clock,
  },
  employee_changes: {
    label: 'Employee Changes',
    description: 'Audit trail of all changes (rolling 6 months)',
    icon: Clock,
    noStatusFilter: true, // Uses rolling date instead
  },
  employee_demographic_details: {
    label: 'Demographic Details',
    description: 'EEO data, veteran status, disability',
    icon: Users,
  },
  employee_education: {
    label: 'Education',
    description: 'Degrees, certifications, training',
    icon: GraduationCap,
  },
  contacts: {
    label: 'Contacts',
    description: 'Emergency contacts, beneficiaries',
    icon: Phone,
  },
  pto_plans: {
    label: 'PTO Plans',
    description: 'Time off balances and accruals',
    icon: Palmtree,
    noTerms: true, // No terminated filter for PTO
  },
};

const STATUS_OPTIONS = [
  { value: 'A', label: 'Active', color: '#16a34a' },
  { value: 'L', label: 'Leave', color: '#eab308' },
  { value: 'T', label: 'Terminated', color: '#dc2626' },
];

export default function UKGSyncSettings({ projectId, isOpen, onClose, onSaved }) {
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  // Load config on mount
  useEffect(() => {
    if (!projectId || !isOpen) return;
    
    setLoading(true);
    fetch(`${API_BASE}/api/ukg/sync-settings/${projectId}`)
      .then(res => res.json())
      .then(data => {
        setConfig(data.endpoint_configs || {});
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load sync settings:', err);
        setError('Failed to load settings');
        setLoading(false);
      });
  }, [projectId, isOpen]);

  const handleToggleEndpoint = (endpoint) => {
    setConfig(prev => ({
      ...prev,
      [endpoint]: {
        ...prev[endpoint],
        enabled: !prev[endpoint]?.enabled
      }
    }));
    setSaved(false);
  };

  const handleToggleStatus = (endpoint, status) => {
    setConfig(prev => {
      const current = prev[endpoint]?.statuses || [];
      const newStatuses = current.includes(status)
        ? current.filter(s => s !== status)
        : [...current, status];
      return {
        ...prev,
        [endpoint]: {
          ...prev[endpoint],
          statuses: newStatuses
        }
      };
    });
    setSaved(false);
  };

  const handleDateChange = (endpoint, date) => {
    setConfig(prev => ({
      ...prev,
      [endpoint]: {
        ...prev[endpoint],
        term_cutoff_date: date
      }
    }));
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/ukg/sync-settings/${projectId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoint_configs: config })
      });
      
      if (!res.ok) throw new Error('Failed to save');
      
      setSaved(true);
      setSaving(false);
      setTimeout(() => setSaved(false), 3000);
      onSaved?.();
    } catch (err) {
      setError('Failed to save settings');
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
    }}>
      <div style={{
        background: '#fff',
        borderRadius: '12px',
        width: '90%',
        maxWidth: '700px',
        maxHeight: '85vh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Settings size={20} color="#3b82f6" />
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>UKG Sync Settings</h2>
          </div>
          <button 
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
          >
            <X size={20} color="#64748b" />
          </button>
        </div>

        {/* Content */}
        <div style={{ 
          flex: 1, 
          overflow: 'auto', 
          padding: '20px',
        }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <Loader2 size={24} className="spin" style={{ color: '#3b82f6' }} />
              <p style={{ marginTop: '8px', color: '#64748b' }}>Loading settings...</p>
            </div>
          ) : error ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#dc2626' }}>
              {error}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <p style={{ fontSize: '13px', color: '#64748b', margin: '0 0 8px 0' }}>
                Configure which employee data to sync and filter by employment status.
              </p>
              
              {Object.entries(ENDPOINT_INFO).map(([endpoint, info]) => {
                const endpointConfig = config[endpoint] || { enabled: true, statuses: ['A'], term_cutoff_date: '2025-01-01' };
                const Icon = info.icon;
                const showTermDate = !info.noStatusFilter && !info.noTerms && endpointConfig.statuses?.includes('T');
                
                return (
                  <div 
                    key={endpoint}
                    style={{
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      padding: '12px 16px',
                      background: endpointConfig.enabled ? '#fff' : '#f8fafc',
                      opacity: endpointConfig.enabled ? 1 : 0.6,
                    }}
                  >
                    {/* Endpoint header */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', flex: 1 }}>
                        <input
                          type="checkbox"
                          checked={endpointConfig.enabled !== false}
                          onChange={() => handleToggleEndpoint(endpoint)}
                          style={{ width: '16px', height: '16px', accentColor: '#3b82f6' }}
                        />
                        <Icon size={18} color="#64748b" />
                        <span style={{ fontWeight: 500, fontSize: '14px' }}>{info.label}</span>
                      </label>
                    </div>
                    
                    <p style={{ fontSize: '12px', color: '#64748b', margin: '0 0 10px 24px' }}>
                      {info.description}
                    </p>
                    
                    {/* Status filters */}
                    {endpointConfig.enabled !== false && !info.noStatusFilter && (
                      <div style={{ marginLeft: '24px', display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                        <span style={{ fontSize: '12px', color: '#64748b', marginRight: '4px' }}>Include:</span>
                        {STATUS_OPTIONS.map(status => {
                          if (info.noTerms && status.value === 'T') return null;
                          const isSelected = endpointConfig.statuses?.includes(status.value);
                          return (
                            <button
                              key={status.value}
                              onClick={() => handleToggleStatus(endpoint, status.value)}
                              style={{
                                padding: '4px 10px',
                                borderRadius: '4px',
                                border: `1px solid ${isSelected ? status.color : '#e5e7eb'}`,
                                background: isSelected ? `${status.color}15` : '#fff',
                                color: isSelected ? status.color : '#64748b',
                                fontSize: '12px',
                                fontWeight: isSelected ? 500 : 400,
                                cursor: 'pointer',
                                transition: 'all 0.15s',
                              }}
                            >
                              {status.label}
                            </button>
                          );
                        })}
                        
                        {/* Term cutoff date */}
                        {showTermDate && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '8px' }}>
                            <Calendar size={14} color="#64748b" />
                            <span style={{ fontSize: '12px', color: '#64748b' }}>since</span>
                            <input
                              type="date"
                              value={endpointConfig.term_cutoff_date || '2025-01-01'}
                              onChange={(e) => handleDateChange(endpoint, e.target.value)}
                              style={{
                                padding: '3px 6px',
                                border: '1px solid #e5e7eb',
                                borderRadius: '4px',
                                fontSize: '12px',
                              }}
                            />
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Special note for employee_changes */}
                    {info.noStatusFilter && endpointConfig.enabled !== false && (
                      <div style={{ marginLeft: '24px', fontSize: '12px', color: '#64748b', fontStyle: 'italic' }}>
                        Automatically pulls last 6 months of changes
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '12px 20px',
          borderTop: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '10px',
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              background: '#fff',
              color: '#64748b',
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || loading}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '6px',
              background: saved ? '#16a34a' : '#3b82f6',
              color: '#fff',
              fontSize: '13px',
              fontWeight: 500,
              cursor: saving ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            {saving ? (
              <><Loader2 size={14} className="spin" /> Saving...</>
            ) : saved ? (
              <><CheckCircle size={14} /> Saved!</>
            ) : (
              <><Save size={14} /> Save Settings</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
