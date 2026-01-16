/**
 * CreateProjectPage.jsx - Step 1: Create Project
 * 
 * WIRED TO REAL API - Fetches domains and systems from backend.
 * Supports multi-domain, multi-system selection.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, AlertCircle, Check, X, Loader2 } from 'lucide-react';
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
  const { user } = useAuth();

  // Reference data from API
  const [domains, setDomains] = useState([]);
  const [systems, setSystems] = useState([]);
  const [loadingRef, setLoadingRef] = useState(true);

  // Form state
  const [formData, setFormData] = useState({
    customer: '',
    selectedDomains: [],
    selectedSystems: [],
    engagement_type: 'implementation',
    target_go_live: '',
    project_lead: user?.full_name || user?.email?.split('@')[0] || '',
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
      const [domainsRes, systemsRes] = await Promise.all([
        fetch(`${API_BASE}/api/reference/domains`),
        fetch(`${API_BASE}/api/reference/systems`),
      ]);
      
      if (domainsRes.ok) {
        const domainsData = await domainsRes.json();
        setDomains(domainsData);
      }
      
      if (systemsRes.ok) {
        const systemsData = await systemsRes.json();
        setSystems(systemsData);
      }
    } catch (err) {
      console.error('Failed to load reference data:', err);
      setError('Failed to load configuration. Please refresh.');
    } finally {
      setLoadingRef(false);
    }
  };

  // Filter systems by selected domains
  const filteredSystems = formData.selectedDomains.length === 0
    ? systems
    : systems.filter(s => 
        formData.selectedDomains.includes(s.domain_code) ||
        (s.additional_domains && s.additional_domains.some(d => formData.selectedDomains.includes(d)))
      );

  // Group systems by vendor for display
  const systemsByVendor = filteredSystems.reduce((acc, sys) => {
    if (!acc[sys.vendor]) acc[sys.vendor] = [];
    acc[sys.vendor].push(sys);
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
      
      // Clear systems that are no longer in selected domains
      const validSystems = prev.selectedSystems.filter(sysCode => {
        const sys = systems.find(s => s.code === sysCode);
        if (!sys) return false;
        if (selected.length === 0) return true;
        return selected.includes(sys.domain_code) || 
          (sys.additional_domains && sys.additional_domains.some(d => selected.includes(d)));
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
      const selectedSystemsData = systems.filter(s => formData.selectedSystems.includes(s.code));
      const engagementLabel = ENGAGEMENT_TYPES.find(t => t.value === formData.engagement_type)?.label || formData.engagement_type;
      const systemNames = selectedSystemsData.map(s => s.name).join(', ');
      
      await createProject({
        name: `${formData.customer} - ${engagementLabel}`,
        customer: formData.customer,
        // New multi-select fields
        systems: formData.selectedSystems,
        domains: formData.selectedDomains,
        engagement_type: formData.engagement_type,
        // Legacy fields for backwards compatibility
        product: selectedSystemsData[0]?.name || '',
        type: engagementLabel,
        // Additional fields
        target_go_live: formData.target_go_live || null,
        lead_name: formData.project_lead || null,
        notes: formData.notes || null,
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
        <p className="page-subtitle">Step 1: Define your client engagement scope</p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Client Name */}
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Client Information</h3>
          </div>
          <div className="card-body">
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
                <label className="form-label">Client Name *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g., Acme Corporation"
                  value={formData.customer}
                  onChange={(e) => handleChange('customer', e.target.value)}
                />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Project Lead</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Your name"
                  value={formData.project_lead}
                  onChange={(e) => handleChange('project_lead', e.target.value)}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Domain Selection */}
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Domain</h3>
            <span className="text-muted" style={{ fontSize: 'var(--text-sm)' }}>
              Select one or more domains
            </span>
          </div>
          <div className="card-body">
            <div className="domain-grid">
              {domains.map(domain => {
                const isSelected = formData.selectedDomains.includes(domain.code);
                return (
                  <div
                    key={domain.code}
                    className={`domain-card ${isSelected ? 'domain-card--selected' : ''}`}
                    onClick={() => toggleDomain(domain.code)}
                    style={{ '--domain-color': domain.color }}
                  >
                    <div className="domain-card__check">
                      {isSelected && <Check size={14} />}
                    </div>
                    <div className="domain-card__name">{domain.name}</div>
                    <div className="domain-card__desc">{domain.description}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* System Selection */}
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">System(s) *</h3>
            <span className="text-muted" style={{ fontSize: 'var(--text-sm)' }}>
              {filteredSystems.length} systems available
              {formData.selectedSystems.length > 0 && ` • ${formData.selectedSystems.length} selected`}
            </span>
          </div>
          <div className="card-body">
            {Object.keys(systemsByVendor).length === 0 ? (
              <p className="text-muted">No systems found. Try selecting a domain first.</p>
            ) : (
              <div className="system-list">
                {Object.entries(systemsByVendor).sort(([a], [b]) => a.localeCompare(b)).map(([vendor, vendorSystems]) => (
                  <div key={vendor} className="system-vendor-group">
                    <div className="system-vendor-label">{vendor}</div>
                    <div className="system-options">
                      {vendorSystems.map(sys => {
                        const isSelected = formData.selectedSystems.includes(sys.code);
                        return (
                          <div
                            key={sys.code}
                            className={`system-option ${isSelected ? 'system-option--selected' : ''}`}
                            onClick={() => toggleSystem(sys.code)}
                          >
                            <div className="system-option__check">
                              {isSelected && <Check size={12} />}
                            </div>
                            <span>{sys.name}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Engagement Type & Go-Live */}
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Engagement Details</h3>
          </div>
          <div className="card-body">
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
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
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Target Go-Live</label>
                <input
                  type="date"
                  className="form-input"
                  value={formData.target_go_live}
                  onChange={(e) => handleChange('target_go_live', e.target.value)}
                />
                <div className="form-group mt-4">
                  <label className="form-label">Notes (optional)</label>
                  <textarea
                    className="form-input"
                    rows={3}
                    placeholder="Any additional context..."
                    value={formData.notes}
                    onChange={(e) => handleChange('notes', e.target.value)}
                    style={{ resize: 'vertical' }}
                  />
                </div>
              </div>
            </div>
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
