/**
 * CreateProjectPage.jsx - Mockup Screen 1
 * =========================================
 *
 * EXACT match to mockup "Create New Project" screen.
 * Clean, simple form with:
 * - Client Name
 * - System / Platform
 * - Engagement Type
 * - Target Go-Live
 * - Project Lead
 *
 * Created: January 15, 2026 - Phase 4A UX Redesign
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { useAuth } from '../context/AuthContext';
import StepIndicator from '../components/StepIndicator';

// System options
const SYSTEMS = [
  'UKG Pro',
  'UKG Ready',
  'Workday HCM',
  'ADP Workforce Now',
  'Oracle HCM',
  'SAP SuccessFactors',
];

// Engagement types
const ENGAGEMENT_TYPES = [
  'Implementation',
  'Optimization',
  'Assessment',
  'Migration',
  'Remediation',
];

export default function CreateProjectPage() {
  const navigate = useNavigate();
  const { createProject } = useProject();
  const { user } = useAuth();

  const [formData, setFormData] = useState({
    customer: '',
    system_type: 'UKG Pro',
    engagement_type: 'Implementation',
    target_go_live: '',
    project_lead: user?.full_name || user?.email?.split('@')[0] || '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
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
      const project = await createProject({
        name: `${formData.customer} - ${formData.engagement_type}`,
        customer: formData.customer,
        system_type: formData.system_type,
        engagement_type: formData.engagement_type,
        target_go_live: formData.target_go_live,
        project_lead: formData.project_lead,
      });

      // Navigate to upload page for this project
      navigate('/upload');
    } catch (err) {
      setError(err.message || 'Failed to create project');
      setSaving(false);
    }
  };

  return (
    <>
      <StepIndicator currentStep={1} />
      <div style={{ padding: 32, maxWidth: 1400, margin: '0 auto' }}>
        {/* Page Header */}
        <div className="xlr8-page-header">
        <h1>Create New Project</h1>
        <p className="subtitle">Start a new analysis engagement</p>
      </div>

      {/* Form Card */}
      <div className="xlr8-card" style={{ maxWidth: 700 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          marginBottom: 24,
        }}>
          <div style={{
            width: 32,
            height: 32,
            background: 'rgba(131, 177, 109, 0.12)',
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
          }}>
            📋
          </div>
          <h2 style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: 16,
            fontWeight: 700,
            color: '#2a3441',
            margin: 0,
          }}>
            Project Details
          </h2>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Client Name */}
          <div className="xlr8-form-group">
            <label>Client Name</label>
            <input
              type="text"
              value={formData.customer}
              onChange={(e) => handleChange('customer', e.target.value)}
              placeholder="Enter client name"
            />
          </div>

          {/* System & Engagement Type Row */}
          <div className="xlr8-form-row">
            <div className="xlr8-form-group">
              <label>System / Platform</label>
              <select
                value={formData.system_type}
                onChange={(e) => handleChange('system_type', e.target.value)}
              >
                {SYSTEMS.map(sys => (
                  <option key={sys} value={sys}>{sys}</option>
                ))}
              </select>
            </div>

            <div className="xlr8-form-group">
              <label>Engagement Type</label>
              <select
                value={formData.engagement_type}
                onChange={(e) => handleChange('engagement_type', e.target.value)}
              >
                {ENGAGEMENT_TYPES.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Go-Live & Project Lead Row */}
          <div className="xlr8-form-row">
            <div className="xlr8-form-group">
              <label>Target Go-Live</label>
              <input
                type="date"
                value={formData.target_go_live}
                onChange={(e) => handleChange('target_go_live', e.target.value)}
                placeholder="YYYY-MM-DD"
              />
            </div>

            <div className="xlr8-form-group">
              <label>Project Lead</label>
              <input
                type="text"
                value={formData.project_lead}
                onChange={(e) => handleChange('project_lead', e.target.value)}
                placeholder="Project lead name"
              />
            </div>
          </div>

          {/* Error */}
          {error && (
            <div style={{
              padding: '12px 16px',
              background: 'rgba(153, 60, 68, 0.1)',
              border: '1px solid rgba(153, 60, 68, 0.3)',
              borderRadius: 8,
              color: '#993c44',
              fontSize: 14,
              marginBottom: 20,
            }}>
              {error}
            </div>
          )}

          {/* Buttons */}
          <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
            <button
              type="submit"
              className="xlr8-btn xlr8-btn-primary"
              disabled={saving}
            >
              {saving ? 'Creating...' : 'Create Project →'}
            </button>
            <button
              type="button"
              className="xlr8-btn xlr8-btn-secondary"
              onClick={() => navigate('/projects')}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
    </>
  );
}
