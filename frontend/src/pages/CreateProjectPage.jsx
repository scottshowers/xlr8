/**
 * CreateProjectPage.jsx - Step 1: Create Project
 * 
 * First step in the 8-step consultant workflow.
 * Clean form to capture: Client, System, Engagement Type, Go-Live, Lead
 * 
 * Flow: [CREATE PROJECT] → Upload → Select Playbooks → Analysis → ...
 * 
 * Updated: January 16, 2026 - Phase 4A UX Overhaul
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useProject } from '../context/ProjectContext';
import { useAuth } from '../context/AuthContext';

// System options
const SYSTEMS = [
  { value: 'ukg-pro', label: 'UKG Pro' },
  { value: 'ukg-ready', label: 'UKG Ready' },
  { value: 'workday', label: 'Workday HCM' },
  { value: 'adp', label: 'ADP Workforce Now' },
  { value: 'oracle', label: 'Oracle HCM' },
  { value: 'sap', label: 'SAP SuccessFactors' },
  { value: 'other', label: 'Other' },
];

// Engagement types
const ENGAGEMENT_TYPES = [
  { value: 'implementation', label: 'Implementation', description: 'New system deployment' },
  { value: 'optimization', label: 'Optimization', description: 'Improve existing setup' },
  { value: 'assessment', label: 'Assessment', description: 'Health check & audit' },
  { value: 'migration', label: 'Migration', description: 'System conversion' },
  { value: 'remediation', label: 'Remediation', description: 'Fix known issues' },
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
    
    // Validation
    if (!formData.customer.trim()) {
      setError('Please enter a client name');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const systemLabel = SYSTEMS.find(s => s.value === formData.system_type)?.label || formData.system_type;
      const engagementLabel = ENGAGEMENT_TYPES.find(e => e.value === formData.engagement_type)?.label || formData.engagement_type;
      
      const project = await createProject({
        name: `${formData.customer} - ${engagementLabel}`,
        customer: formData.customer,
        system_type: formData.system_type,
        system_label: systemLabel,
        engagement_type: formData.engagement_type,
        engagement_label: engagementLabel,
        target_go_live: formData.target_go_live || null,
        project_lead: formData.project_lead,
        description: formData.description,
      });

      // Navigate to upload page (Step 2)
      navigate('/upload');
    } catch (err) {
      setError(err.message || 'Failed to create project');
      setSaving(false);
    }
  };

  const selectedEngagement = ENGAGEMENT_TYPES.find(e => e.value === formData.engagement_type);

  return (
    <div className="create-project">
      <PageHeader
        title="Create New Project"
        subtitle="Step 1 of 8 • Start a new analysis engagement"
      />

      <div className="create-project__content">
        {/* Main Form Card */}
        <Card className="create-project__form-card">
          <CardHeader>
            <CardTitle icon="📋">Project Details</CardTitle>
          </CardHeader>

          <form onSubmit={handleSubmit} className="create-project__form">
            {/* Client Name */}
            <div className="xlr8-form-group">
              <label htmlFor="customer">Client Name</label>
              <input
                id="customer"
                type="text"
                value={formData.customer}
                onChange={(e) => handleChange('customer', e.target.value)}
                placeholder="e.g., Acme Corporation"
                autoFocus
              />
            </div>

            {/* System & Engagement Type Row */}
            <div className="xlr8-form-row">
              <div className="xlr8-form-group">
                <label htmlFor="system_type">System / Platform</label>
                <select
                  id="system_type"
                  value={formData.system_type}
                  onChange={(e) => handleChange('system_type', e.target.value)}
                >
                  {SYSTEMS.map(sys => (
                    <option key={sys.value} value={sys.value}>{sys.label}</option>
                  ))}
                </select>
              </div>

              <div className="xlr8-form-group">
                <label htmlFor="engagement_type">Engagement Type</label>
                <select
                  id="engagement_type"
                  value={formData.engagement_type}
                  onChange={(e) => handleChange('engagement_type', e.target.value)}
                >
                  {ENGAGEMENT_TYPES.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
                {selectedEngagement && (
                  <span className="xlr8-form-hint">{selectedEngagement.description}</span>
                )}
              </div>
            </div>

            {/* Go-Live & Project Lead Row */}
            <div className="xlr8-form-row">
              <div className="xlr8-form-group">
                <label htmlFor="target_go_live">Target Go-Live</label>
                <input
                  id="target_go_live"
                  type="date"
                  value={formData.target_go_live}
                  onChange={(e) => handleChange('target_go_live', e.target.value)}
                />
                <span className="xlr8-form-hint">Optional - helps prioritize work</span>
              </div>

              <div className="xlr8-form-group">
                <label htmlFor="project_lead">Project Lead</label>
                <input
                  id="project_lead"
                  type="text"
                  value={formData.project_lead}
                  onChange={(e) => handleChange('project_lead', e.target.value)}
                  placeholder="Lead consultant name"
                />
              </div>
            </div>

            {/* Description (optional) */}
            <div className="xlr8-form-group">
              <label htmlFor="description">Notes (Optional)</label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Any additional context about this engagement..."
                rows={3}
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="create-project__error">
                <span>⚠️</span>
                {error}
              </div>
            )}

            {/* Actions */}
            <div className="create-project__actions">
              <Button
                type="submit"
                variant="primary"
                disabled={saving}
              >
                {saving ? 'Creating...' : 'Create Project →'}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => navigate('/projects')}
              >
                Cancel
              </Button>
            </div>
          </form>
        </Card>

        {/* Help Sidebar */}
        <div className="create-project__sidebar">
          <Card className="create-project__help-card">
            <CardHeader>
              <CardTitle icon="💡">Quick Tips</CardTitle>
            </CardHeader>
            <ul className="create-project__help-list">
              <li>
                <strong>Client Name</strong> - Use the legal entity name for consistency across projects
              </li>
              <li>
                <strong>System</strong> - Select the HCM platform being implemented or assessed
              </li>
              <li>
                <strong>Engagement Type</strong> - This determines which playbooks are recommended
              </li>
              <li>
                <strong>Go-Live Date</strong> - Helps XLR8 prioritize critical findings
              </li>
            </ul>
          </Card>

          <Card className="create-project__next-card">
            <div className="create-project__next-preview">
              <div className="create-project__next-label">Next Step</div>
              <div className="create-project__next-title">📤 Upload Data</div>
              <div className="create-project__next-description">
                After creating the project, you'll upload customer data files for analysis.
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default CreateProjectPage;
