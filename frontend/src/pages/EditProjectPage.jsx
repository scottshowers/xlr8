/**
 * EditProjectPage.jsx - Edit Project
 * 
 * WIRED TO REAL API - Fetches project, allows updates via PATCH /api/customers/{id}
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ChevronRight, AlertCircle, Check, Loader2, ArrowLeft, Trash2 } from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import { useAuth } from '../context/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

const ENGAGEMENT_TYPES = [
  { value: 'implementation', label: 'Implementation', desc: 'New system deployment' },
  { value: 'optimization', label: 'Optimization', desc: 'Improve existing setup' },
  { value: 'assessment', label: 'Assessment', desc: 'Health check & audit' },
  { value: 'migration', label: 'Migration', desc: 'System conversion' },
  { value: 'year-end', label: 'Year-End', desc: 'Annual compliance & close' },
  { value: 'support', label: 'Ongoing Support', desc: 'Continuous maintenance' },
  { value: 'remediation', label: 'Remediation', desc: 'Fix known issues' },
];

const EditProjectPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();

  // Reference data
  const [domains, setDomains] = useState([]);
  const [systems, setSystems] = useState([]);
  const [users, setUsers] = useState([]);
  const [loadingRef, setLoadingRef] = useState(true);
  const [loadingProject, setLoadingProject] = useState(true);

  // Form state
  const [formData, setFormData] = useState({
    customer: '',
    selectedDomains: [],
    selectedSystems: [],
    engagement_type: '',
    engagement_start: '',
    projected_end: '',
    lead_name: '',
    notes: '',
    status: 'active',
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    fetchReferenceData();
    fetchProject();
  }, [id]);

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

  const fetchProject = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/customers/list`);
      if (!res.ok) throw new Error('Failed to fetch projects');
      const projects = await res.json();
      
      const project = projects.find(p => p.id === id);
      if (!project) throw new Error('Project not found');
      
      // Populate form with existing data
      setFormData({
        customer: project.customer || '',
        selectedDomains: project.domains || [],
        selectedSystems: project.systems || [],
        engagement_type: project.engagement_type || project.type || '',
        engagement_start: project.start_date || '',
        projected_end: project.target_go_live || '',
        lead_name: project.lead_name || '',
        notes: project.notes?.replace(/\[DEMO_STATS\].*?\[\/DEMO_STATS\]/s, '').trim() || '',
        status: project.status || 'active',
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingProject(false);
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
    setSuccess(false);
  };

  const toggleDomain = (code) => {
    setFormData(prev => {
      const selected = prev.selectedDomains.includes(code)
        ? prev.selectedDomains.filter(d => d !== code)
        : [...prev.selectedDomains, code];
      
      const validSystems = prev.selectedSystems.filter(sysCode => {
        const sys = systems.find(s => s.code === sysCode);
        return sys && selected.includes(sys.domain_code);
      });
      
      return { ...prev, selectedDomains: selected, selectedSystems: validSystems };
    });
    setSuccess(false);
  };

  const toggleSystem = (code) => {
    setFormData(prev => ({
      ...prev,
      selectedSystems: prev.selectedSystems.includes(code)
        ? prev.selectedSystems.filter(s => s !== code)
        : [...prev.selectedSystems, code]
    }));
    setSuccess(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.customer.trim()) {
      setError('Please enter a client name');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const engagementLabel = ENGAGEMENT_TYPES.find(t => t.value === formData.engagement_type)?.label || formData.engagement_type;
      
      const res = await fetch(`${API_BASE}/api/customers/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `${formData.customer} - ${engagementLabel}`,
          customer: formData.customer,
          systems: formData.selectedSystems,
          domains: formData.selectedDomains,
          engagement_type: formData.engagement_type,
          type: engagementLabel,
          start_date: formData.engagement_start || null,
          target_go_live: formData.projected_end || null,
          lead_name: formData.lead_name || null,
          notes: formData.notes || null,
          status: formData.status,
        }),
      });

      if (!res.ok) throw new Error('Failed to update project');
      
      setSuccess(true);
      setTimeout(() => navigate(`/customers/${id}/hub`), 1500);
    } catch (err) {
      setError(err.message || 'Failed to update project');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this project? This cannot be undone.')) return;
    
    setDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/api/customers/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete project');
      navigate('/customers');
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleting(false);
    }
  };

  if (loadingRef || loadingProject) {
    return (
      <div className="page-loading">
        <Loader2 size={24} className="spin" />
        <p>Loading project...</p>
      </div>
    );
  }

  return (
    <div className="edit-project-page">
      <button className="btn btn-secondary mb-4" onClick={() => navigate(`/customers/${id}/hub`)}>
        <ArrowLeft size={16} />
        Back to Project
      </button>

      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title">Edit Project</h1>
          <p className="page-subtitle">Update project settings and scope</p>
        </div>
        <button 
          className="btn btn-secondary" 
          onClick={handleDelete}
          disabled={deleting}
          style={{ color: 'var(--critical)' }}
        >
          <Trash2 size={16} />
          {deleting ? 'Deleting...' : 'Delete Project'}
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Client Information */}
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
                  value={formData.customer}
                  onChange={(e) => handleChange('customer', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Project Lead</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.lead_name}
                  onChange={(e) => handleChange('lead_name', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Status</label>
                <select
                  className="form-select"
                  value={formData.status}
                  onChange={(e) => handleChange('status', e.target.value)}
                >
                  <option value="active">Active</option>
                  <option value="completed">Completed</option>
                  <option value="on_hold">On Hold</option>
                  <option value="archived">Archived</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Domain & Systems */}
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Domain & Systems</h3>
          </div>
          <div className="card-body">
            <div className="domain-columns">
              {domains.map(domain => {
                const isActive = formData.selectedDomains.includes(domain.code);
                const domainSystems = systemsByDomain[domain.code] || [];
                
                return (
                  <div key={domain.code} className={`domain-column ${isActive ? 'domain-column--active' : ''}`}>
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
                    
                    <div className={`domain-column__systems ${!isActive ? 'domain-column__systems--disabled' : ''}`}>
                      {domainSystems.map(sys => {
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
                      })}
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
            <div className="form-group mb-4">
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

        {/* Notes */}
        <div className="card mb-6">
          <div className="card-header">
            <h3 className="card-title">Notes</h3>
          </div>
          <div className="card-body">
            <textarea
              className="form-input"
              rows={4}
              value={formData.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              style={{ resize: 'vertical' }}
            />
          </div>
        </div>

        {/* Messages */}
        {error && (
          <div className="alert alert--error mb-4">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {success && (
          <div className="alert alert--info mb-4">
            <Check size={16} />
            Project updated! Redirecting...
          </div>
        )}

        {/* Submit */}
        <div className="flex gap-4">
          <button type="submit" className="btn btn-primary btn-lg" disabled={saving}>
            {saving ? (
              <>
                <Loader2 size={18} className="spin" />
                Saving...
              </>
            ) : (
              <>
                Save Changes
                <ChevronRight size={18} />
              </>
            )}
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate(`/customers/${id}/hub`)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default EditProjectPage;
