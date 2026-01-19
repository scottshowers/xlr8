/**
 * CreateProjectPage.jsx - Step 1: Create Project
 * 
 * WIRED TO REAL API:
 * - Domains & Systems from /api/reference
 * - Users from /api/auth/users
 * 
 * Layout: 6 domain columns, systems listed under each
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, AlertCircle, Check, Loader2, X } from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import { useAuth } from '../context/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

const ENGAGEMENT_TYPES = [
  { value: 'implementation', label: 'Implementation', desc: 'New system deployment' },
  { value: 'optimization', label: 'Optimization', desc: 'Improve existing setup' },
  { value: 'assessment', label: 'Assessment', desc: 'Health check & audit' },
  { value: 'migration', label: 'Migration', desc: 'System conversion' },
  { value: 'year-end', label: 'Year-End', desc: 'Annual compliance & close' },
  { value: 'remediation', label: 'Remediation', desc: 'Fix known issues' },
];

const CreateProjectPage = () => {
  const navigate = useNavigate();
  const { createProject } = useProject();
  const { user, token } = useAuth();

  // Reference data from API
  const [domains, setDomains] = useState([]);
  const [systems, setSystems] = useState([]);
  const [users, setUsers] = useState([]);
  const [loadingRef, setLoadingRef] = useState(true);

  // Form state
  const [formData, setFormData] = useState({
    customer: '',
    selectedDomains: [],
    selectedSystems: [],
    engagement_type: 'implementation',
    engagement_start: '',
    projected_end: '',
    pm_id: '',
    consultant_ids: [],
    notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Fetch reference data on mount
  useEffect(() => {
    fetchReferenceData();
  }, []);

  const fetchReferenceData = async () => {
    try {
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
      
      const [domainsRes, systemsRes, usersRes] = await Promise.all([
        fetch(`${API_BASE}/api/reference/domains`),
        fetch(`${API_BASE}/api/reference/systems`),
        fetch(`${API_BASE}/api/auth/users`, { headers }).catch(() => ({ ok: false })),
      ]);
      
      if (domainsRes.ok) setDomains(await domainsRes.json());
      if (systemsRes.ok) setSystems(await systemsRes.json());
      if (usersRes.ok) {
        const usersData = await usersRes.json();
        setUsers(usersData.filter(u => u.role !== 'customer'));
      }
    } catch (err) {
      console.error('Failed to load reference data:', err);
    } finally {
      setLoadingRef(false);
    }
  };

  // Group systems by domain
  const systemsByDomain = systems.reduce((acc, sys) => {
    const domainCode = sys.domain_code || 'other';
    if (!acc[domainCode]) acc[domainCode] = [];
    acc[domainCode].push(sys);
    return acc;
  }, {});

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (error) setError(null);
  };

  const toggleDomain = (code) => {
    setFormData(prev => {
      const selected = prev.selectedDomains.includes(code)
        ? prev.selectedDomains.filter(d => d !== code)
        : [...prev.selectedDomains, code];
      
      // Clear systems from deselected domains
      const validSystems = prev.selectedSystems.filter(sysCode => {
        const sys = systems.find(s => s.code === sysCode);
        return sys && selected.includes(sys.domain_code);
      });
      
      return { ...prev, selectedDomains: selected, selectedSystems: validSystems };
    });
  };

  const toggleSystem = (code) => {
    setFormData(prev => ({
      ...prev,
      selectedSystems: prev.selectedSystems.includes(code)
        ? prev.selectedSystems.filter(s => s !== code)
        : [...prev.selectedSystems, code]
    }));
  };

  const toggleConsultant = (userId) => {
    setFormData(prev => ({
      ...prev,
      consultant_ids: prev.consultant_ids.includes(userId)
        ? prev.consultant_ids.filter(id => id !== userId)
        : [...prev.consultant_ids, userId]
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.customer.trim()) {
      setError('Please enter a client name');
      return;
    }
    if (formData.selectedSystems.length === 0) {
      setError('Please select at least one system');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const engagementLabel = ENGAGEMENT_TYPES.find(t => t.value === formData.engagement_type)?.label || formData.engagement_type;
      const selectedSystemsData = systems.filter(s => formData.selectedSystems.includes(s.code));
      
      // Create customer with the new schema
      // name = customer name (not combined with engagement type)
      // engagement_types = list of engagement types
      await createProject({
        name: formData.customer,  // Just the customer name
        engagement_types: [engagementLabel],  // List of engagement types
        systems: formData.selectedSystems,
        domains: formData.selectedDomains,
        product: selectedSystemsData[0]?.name || '',
        start_date: formData.engagement_start || null,
        target_go_live: formData.projected_end || null,
        lead_name: users.find(u => u.id === formData.pm_id)?.full_name || null,
        notes: formData.notes || null,
        // Team fields
        pm_id: formData.pm_id || null,
        consultant_ids: formData.consultant_ids,
      });
      
      navigate('/upload');
    } catch (err) {
      setError(err.message || 'Failed to create project');
    } finally {
      setSaving(false);
    }
  };

  if (loadingRef) {
    return (
      <div className="page-loading">
        <Loader2 size={24} className="spin" />
        <p>Loading configuration...</p>
      </div>
    );
  }

  return (
    <div className="create-project-page">
      <div className="page-header">
        <h1 className="page-title">Create New Project</h1>
        <p className="page-subtitle">Define your client engagement scope</p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Client Information */}
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Client Information</h3>
          </div>
          <div className="card-body">
            <div className="form-group">
              <label className="form-label">Client Name *</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g., Acme Corporation"
                value={formData.customer}
                onChange={(e) => handleChange('customer', e.target.value)}
                style={{ maxWidth: '400px' }}
              />
            </div>
          </div>
        </div>

        {/* Systems by Domain - 6 Column Layout */}
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Domain & Systems *</h3>
            <span className="text-muted" style={{ fontSize: 'var(--text-sm)' }}>
              Select domain(s) to enable systems, then select system(s)
            </span>
          </div>
          <div className="card-body">
            <div className="domain-columns">
              {domains.map(domain => {
                const isActive = formData.selectedDomains.includes(domain.code);
                const domainSystems = systemsByDomain[domain.code] || [];
                
                return (
                  <div 
                    key={domain.code} 
                    className={`domain-column ${isActive ? 'domain-column--active' : ''}`}
                  >
                    {/* Domain Header */}
                    <div 
                      className="domain-column__header"
                      onClick={() => toggleDomain(domain.code)}
                      style={{ '--domain-color': domain.color }}
                    >
                      <div className="domain-column__check">
                        {isActive && <Check size={12} />}
                      </div>
                      <span className="domain-column__name">{domain.name}</span>
                    </div>
                    
                    {/* Systems List */}
                    <div className={`domain-column__systems ${!isActive ? 'domain-column__systems--disabled' : ''}`}>
                      {domainSystems.length === 0 ? (
                        <div className="domain-column__empty">No systems</div>
                      ) : (
                        domainSystems.map(sys => {
                          const isSelected = formData.selectedSystems.includes(sys.code);
                          return (
                            <div
                              key={sys.code}
                              className={`system-row ${isSelected ? 'system-row--selected' : ''} ${!isActive ? 'system-row--disabled' : ''}`}
                              onClick={() => isActive && toggleSystem(sys.code)}
                            >
                              <div className="system-row__check">
                                {isSelected && <Check size={10} />}
                              </div>
                              <span className="system-row__name">{sys.name}</span>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Engagement Details */}
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Engagement Details</h3>
          </div>
          <div className="card-body">
            {/* Engagement Type */}
            <div className="form-group mb-6">
              <label className="form-label">Engagement Type</label>
              <div className="engagement-grid">
                {ENGAGEMENT_TYPES.map(type => {
                  const isSelected = formData.engagement_type === type.value;
                  return (
                    <div
                      key={type.value}
                      className={`engagement-option ${isSelected ? 'engagement-option--selected' : ''}`}
                      onClick={() => handleChange('engagement_type', type.value)}
                    >
                      <div className="engagement-option__check">
                        {isSelected && <Check size={12} />}
                      </div>
                      <div>
                        <div className="engagement-option__label">{type.label}</div>
                        <div className="engagement-option__desc">{type.desc}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Dates */}
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Engagement Start</label>
                <input
                  type="date"
                  className="form-input"
                  value={formData.engagement_start}
                  onChange={(e) => handleChange('engagement_start', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Projected End</label>
                <input
                  type="date"
                  className="form-input"
                  value={formData.projected_end}
                  onChange={(e) => handleChange('projected_end', e.target.value)}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Team Assignment */}
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Team Assignment</h3>
          </div>
          <div className="card-body">
            <div className="form-row">
              {/* PM */}
              <div className="form-group">
                <label className="form-label">Project Manager</label>
                <select
                  className="form-select"
                  value={formData.pm_id}
                  onChange={(e) => handleChange('pm_id', e.target.value)}
                >
                  <option value="">Select PM...</option>
                  {users.map(u => (
                    <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
                  ))}
                </select>
              </div>

              {/* Consultants */}
              <div className="form-group" style={{ flex: 2 }}>
                <label className="form-label">Consultants</label>
                <div className="consultant-chips">
                  {users.map(u => {
                    const isSelected = formData.consultant_ids.includes(u.id);
                    return (
                      <div
                        key={u.id}
                        className={`consultant-chip ${isSelected ? 'consultant-chip--selected' : ''}`}
                        onClick={() => toggleConsultant(u.id)}
                      >
                        {isSelected && <Check size={12} />}
                        <span>{u.full_name || u.email}</span>
                        {isSelected && <X size={12} className="consultant-chip__remove" />}
                      </div>
                    );
                  })}
                  {users.length === 0 && (
                    <span className="text-muted" style={{ fontSize: 'var(--text-sm)' }}>No team members available</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Notes */}
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Notes</h3>
          </div>
          <div className="card-body">
            <textarea
              className="form-input"
              rows={3}
              placeholder="Any additional context about this engagement..."
              value={formData.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              style={{ resize: 'vertical' }}
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="alert alert--error mb-4">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {/* Submit */}
        <div className="flex gap-4">
          <button type="submit" className="btn btn-primary btn-lg" disabled={saving}>
            {saving ? (
              <>
                <Loader2 size={18} className="spin" />
                Creating...
              </>
            ) : (
              <>
                Create Project
                <ChevronRight size={18} />
              </>
            )}
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/projects')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateProjectPage;
