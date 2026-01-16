/**
 * CreateProjectPage.jsx - Step 1: Create Project
 * 
 * Form to create a new project.
 * Uses design system classes - NO emojis.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, AlertCircle } from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import { useAuth } from '../context/AuthContext';

const SYSTEMS = [
  { value: 'ukg-pro', label: 'UKG Pro' },
  { value: 'ukg-ready', label: 'UKG Ready' },
  { value: 'workday', label: 'Workday HCM' },
  { value: 'adp', label: 'ADP Workforce Now' },
  { value: 'oracle', label: 'Oracle HCM' },
  { value: 'sap', label: 'SAP SuccessFactors' },
  { value: 'other', label: 'Other' },
];

const ENGAGEMENT_TYPES = [
  { value: 'implementation', label: 'Implementation', desc: 'New system deployment' },
  { value: 'optimization', label: 'Optimization', desc: 'Improve existing setup' },
  { value: 'assessment', label: 'Assessment', desc: 'Health check & audit' },
  { value: 'migration', label: 'Migration', desc: 'System conversion' },
  { value: 'remediation', label: 'Remediation', desc: 'Fix known issues' },
];

const CreateProjectPage = () => {
  const navigate = useNavigate();
  const { createProject } = useProject();
  const { user } = useAuth();

  const [formData, setFormData] = useState({
    customer: '',
    system_type: 'ukg-pro',
    engagement_type: 'implementation',
    target_go_live: '',
    project_lead: user?.full_name || user?.email?.split('@')[0] || '',
    description: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.customer.trim()) {
      setError('Please enter a client name');
      return;
    }

    setSaving(true);
    try {
      const systemLabel = SYSTEMS.find(s => s.value === formData.system_type)?.label || formData.system_type;
      const engagementLabel = ENGAGEMENT_TYPES.find(t => t.value === formData.engagement_type)?.label || formData.engagement_type;
      
      await createProject({
        name: `${formData.customer} - ${engagementLabel}`,
        customer: formData.customer,
        system_type: formData.system_type,
        system_type_label: systemLabel,
        engagement_type: formData.engagement_type,
        engagement_type_label: engagementLabel,
        target_go_live: formData.target_go_live || null,
        project_lead: formData.project_lead || null,
        description: formData.description || null,
      });
      navigate('/upload');
    } catch (err) {
      setError(err.message || 'Failed to create project');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="create-project-page">
      <div className="page-header">
        <h1 className="page-title">Create New Project</h1>
        <p className="page-subtitle">Step 1: Set up your client engagement</p>
      </div>

      <div className="card" style={{ maxWidth: '640px' }}>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            {/* Client Name */}
            <div className="form-group">
              <label className="form-label">Client Name *</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g., Acme Corporation"
                value={formData.customer}
                onChange={(e) => handleChange('customer', e.target.value)}
              />
            </div>

            {/* System & Engagement */}
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">System</label>
                <select
                  className="form-select"
                  value={formData.system_type}
                  onChange={(e) => handleChange('system_type', e.target.value)}
                >
                  {SYSTEMS.map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Engagement Type</label>
                <select
                  className="form-select"
                  value={formData.engagement_type}
                  onChange={(e) => handleChange('engagement_type', e.target.value)}
                >
                  {ENGAGEMENT_TYPES.map(t => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Go-Live & Lead */}
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Target Go-Live</label>
                <input
                  type="date"
                  className="form-input"
                  value={formData.target_go_live}
                  onChange={(e) => handleChange('target_go_live', e.target.value)}
                />
              </div>
              <div className="form-group">
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

            {/* Description */}
            <div className="form-group">
              <label className="form-label">Notes (optional)</label>
              <textarea
                className="form-input"
                rows={3}
                placeholder="Any additional context..."
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                style={{ resize: 'vertical' }}
              />
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
                {saving ? 'Creating...' : 'Create Project'}
                <ChevronRight size={18} />
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => navigate('/projects')}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CreateProjectPage;
