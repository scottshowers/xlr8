/**
 * ProjectsPage - Project Management
 * 
 * Clean professional design with:
 * - Light/dark mode support
 * - Customer color palette for project rows
 * - Consistent styling with Command Center
 */

import React, { useState } from 'react';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import { getCustomerColorPalette } from '../utils/customerColors';
import { FolderOpen, Plus, Edit2, Trash2, Check, X } from 'lucide-react';

// Theme-aware colors
const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f5f7fa',
  card: dark ? '#242b3d' : '#ffffff',
  cardBorder: dark ? '#2d3548' : '#e8ecf1',
  text: dark ? '#e8eaed' : '#2a3441',
  textMuted: dark ? '#8b95a5' : '#6b7280',
  textLight: dark ? '#5f6a7d' : '#9ca3af',
  primary: '#5a8a4a',  // Muted forest green
  primaryLight: dark ? 'rgba(90, 138, 74, 0.15)' : 'rgba(90, 138, 74, 0.1)',
  blue: '#4a6b8a',     // Slate blue
  amber: '#8a6b4a',    // Muted rust
  red: '#8a4a4a',      // Muted burgundy
  divider: dark ? '#2d3548' : '#e8ecf1',
  inputBg: dark ? '#1a1f2e' : '#f8fafc',
  inputBorder: dark ? '#3d4555' : '#e1e8ed',
});

// Available playbooks - must match PlaybooksPage
const AVAILABLE_PLAYBOOKS = [
  { id: 'year-end-checklist', name: 'Year-End Checklist', icon: '📅' },
  { id: 'secure-2.0', name: 'SECURE 2.0 Compliance', icon: '🏛️' },
  { id: 'one-big-bill', name: 'One Big Beautiful Bill', icon: '📜' },
  { id: 'payroll-audit', name: 'Payroll Configuration Audit', icon: '🔎' },
  { id: 'data-validation', name: 'Pre-Load Data Validation', icon: '✅' },
];

export default function ProjectsPage() {
  const { projects, createProject, updateProject, deleteProject, selectProject, activeProject } = useProject();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  
  const [showForm, setShowForm] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    customer: '',
    product: '',
    type: 'Implementation',
    notes: '',
    playbooks: [],
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingProject) {
        await updateProject(editingProject.id, formData);
      } else {
        await createProject(formData);
      }
      setShowForm(false);
      setEditingProject(null);
      setFormData({ name: '', customer: '', product: '', type: 'Implementation', notes: '', playbooks: [] });
    } catch (err) {
      alert('Failed to save project: ' + err.message);
    }
  };

  const handleEdit = (project) => {
    setEditingProject(project);
    setFormData({
      name: project.name || '',
      customer: project.customer || '',
      product: project.product || '',
      type: project.type || 'Implementation',
      notes: project.notes || '',
      playbooks: project.playbooks || [],
    });
    setShowForm(true);
  };

  const handleDelete = async (project) => {
    if (window.confirm(`Delete project "${project.name}"? This cannot be undone.`)) {
      await deleteProject(project.id);
    }
  };

  const handlePlaybookToggle = (playbookId) => {
    setFormData(prev => {
      const current = prev.playbooks || [];
      if (current.includes(playbookId)) {
        return { ...prev, playbooks: current.filter(id => id !== playbookId) };
      } else {
        return { ...prev, playbooks: [...current, playbookId] };
      }
    });
  };

  const cancelForm = () => {
    setShowForm(false);
    setEditingProject(null);
    setFormData({ name: '', customer: '', product: '', type: 'Implementation', notes: '', playbooks: [] });
  };

  const getPlaybookName = (id) => {
    const pb = AVAILABLE_PLAYBOOKS.find(p => p.id === id);
    return pb ? pb.name : id;
  };

  const getPlaybookIcon = (id) => {
    const pb = AVAILABLE_PLAYBOOKS.find(p => p.id === id);
    return pb ? pb.icon : '📋';
  };

  return (
    <div style={{ maxWidth: '1200px' }}>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: '1.5rem',
          fontWeight: 700,
          color: colors.text,
          margin: 0,
        }}>
          Projects
        </h1>
        <p style={{ color: colors.textMuted, margin: '0.25rem 0 0 0', fontSize: '0.85rem' }}>
          Create and manage customer projects
        </p>
      </div>

      {/* Main Card */}
      <div style={{
        background: colors.card,
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: 12,
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
      }}>
        {/* Card Header */}
        <div style={{
          padding: '1rem 1.25rem',
          borderBottom: `1px solid ${colors.divider}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 600, color: colors.text }}>
            All Projects
          </h3>
          <button
            onClick={() => setShowForm(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.5rem 1rem',
              background: colors.primary,
              border: 'none',
              borderRadius: 8,
              color: 'white',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Plus size={16} />
            New Project
          </button>
        </div>

        {/* Form */}
        {showForm && (
          <div style={{
            padding: '1.5rem',
            background: colors.inputBg,
            borderBottom: `1px solid ${colors.divider}`,
          }}>
            <form onSubmit={handleSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text }}>
                    Customer AR# *
                  </label>
                  <input
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      border: `1px solid ${colors.inputBorder}`,
                      borderRadius: 6,
                      fontSize: '0.85rem',
                      background: colors.card,
                      color: colors.text,
                      boxSizing: 'border-box',
                    }}
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., MEY1000"
                    required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text }}>
                    Company Name *
                  </label>
                  <input
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      border: `1px solid ${colors.inputBorder}`,
                      borderRadius: 6,
                      fontSize: '0.85rem',
                      background: colors.card,
                      color: colors.text,
                      boxSizing: 'border-box',
                    }}
                    value={formData.customer}
                    onChange={(e) => setFormData({ ...formData, customer: e.target.value })}
                    placeholder="e.g., Meyer Corporation"
                    required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text }}>
                    Product *
                  </label>
                  <select
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      border: `1px solid ${colors.inputBorder}`,
                      borderRadius: 6,
                      fontSize: '0.85rem',
                      background: colors.card,
                      color: colors.text,
                      boxSizing: 'border-box',
                    }}
                    value={formData.product || ''}
                    onChange={(e) => setFormData({ ...formData, product: e.target.value })}
                    required
                  >
                    <option value="">Select Product...</option>
                    <option value="UKG Pro">UKG Pro</option>
                    <option value="WFM Dimensions">WFM Dimensions</option>
                    <option value="UKG Ready">UKG Ready</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text }}>
                    Type
                  </label>
                  <select
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      border: `1px solid ${colors.inputBorder}`,
                      borderRadius: 6,
                      fontSize: '0.85rem',
                      background: colors.card,
                      color: colors.text,
                      boxSizing: 'border-box',
                    }}
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                  >
                    <option value="Implementation">Implementation</option>
                    <option value="Support">Support</option>
                    <option value="Analysis">Analysis</option>
                  </select>
                </div>
                <div style={{ gridColumn: 'span 2' }}>
                  <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text }}>
                    Notes
                  </label>
                  <input
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      border: `1px solid ${colors.inputBorder}`,
                      borderRadius: 6,
                      fontSize: '0.85rem',
                      background: colors.card,
                      color: colors.text,
                      boxSizing: 'border-box',
                    }}
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="Optional notes..."
                  />
                </div>

                {/* Playbooks Selection */}
                <div style={{ gridColumn: 'span 2' }}>
                  <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text }}>
                    Assigned Playbooks
                  </label>
                  <p style={{ fontSize: '0.75rem', color: colors.textMuted, margin: '0 0 0.75rem 0' }}>
                    Select which playbooks this customer can access.
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem' }}>
                    {AVAILABLE_PLAYBOOKS.map(playbook => {
                      const isSelected = (formData.playbooks || []).includes(playbook.id);
                      return (
                        <div
                          key={playbook.id}
                          onClick={() => handlePlaybookToggle(playbook.id)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.6rem 0.75rem',
                            background: isSelected ? colors.primaryLight : colors.card,
                            border: `1px solid ${isSelected ? colors.primary : colors.inputBorder}`,
                            borderRadius: 6,
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            readOnly
                            style={{ accentColor: colors.primary }}
                          />
                          <span style={{ fontSize: '1rem' }}>{playbook.icon}</span>
                          <span style={{ fontSize: '0.8rem', color: colors.text }}>{playbook.name}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.25rem' }}>
                <button
                  type="submit"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.6rem 1.25rem',
                    background: colors.primary,
                    border: 'none',
                    borderRadius: 8,
                    color: 'white',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <Check size={16} />
                  {editingProject ? 'Update Project' : 'Create Project'}
                </button>
                <button
                  type="button"
                  onClick={cancelForm}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.6rem 1.25rem',
                    background: 'transparent',
                    border: `1px solid ${colors.inputBorder}`,
                    borderRadius: 8,
                    color: colors.textMuted,
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <X size={16} />
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Project List */}
        {projects.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: colors.textMuted }}>
            <FolderOpen size={40} style={{ opacity: 0.3, marginBottom: '1rem' }} />
            <p style={{ margin: 0, fontSize: '0.85rem' }}>No projects yet. Create one to get started.</p>
          </div>
        ) : (
          <div>
            {/* Table Header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1.3fr 1.5fr 0.9fr 1.6fr 0.7fr 1.5fr',
              padding: '0.75rem 1rem',
              background: colors.inputBg,
              borderBottom: `1px solid ${colors.divider}`,
              fontSize: '0.75rem',
              fontWeight: 600,
              color: colors.textMuted,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              <span>Customer AR#</span>
              <span>Company Name</span>
              <span>Product</span>
              <span>Playbooks</span>
              <span>Status</span>
              <span>Actions</span>
            </div>

            {/* Project Rows */}
            {projects.map((project) => {
              const customerColors = getCustomerColorPalette(project.customer || project.name);
              const isSelected = activeProject?.id === project.id;
              
              return (
                <div
                  key={project.id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1.3fr 1.5fr 0.9fr 1.6fr 0.7fr 1.5fr',
                    padding: '0.875rem 1rem',
                    borderBottom: `1px solid ${colors.divider}`,
                    borderLeft: `3px solid ${isSelected ? customerColors.primary : 'transparent'}`,
                    background: isSelected ? customerColors.bg : 'transparent',
                    alignItems: 'center',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.background = customerColors.bg;
                      e.currentTarget.style.borderLeftColor = customerColors.primary;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.borderLeftColor = 'transparent';
                    }
                  }}
                >
                  <span style={{ fontWeight: 600, color: customerColors.primary, fontSize: '0.85rem' }}>{project.name}</span>
                  <span style={{ color: colors.text, fontSize: '0.85rem' }}>{project.customer}</span>
                  <span style={{ color: colors.textMuted, fontSize: '0.85rem' }}>{project.product || '—'}</span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                    {(project.playbooks || []).length > 0 ? (
                      project.playbooks.map(pbId => (
                        <span
                          key={pbId}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.2rem',
                            padding: '0.15rem 0.4rem',
                            background: colors.primaryLight,
                            border: `1px solid ${colors.primary}40`,
                            borderRadius: 4,
                            fontSize: '0.75rem',
                            color: colors.primary,
                          }}
                        >
                          {getPlaybookIcon(pbId)} {getPlaybookName(pbId)}
                        </span>
                      ))
                    ) : (
                      <span style={{ color: colors.textLight, fontSize: '0.75rem' }}>None assigned</span>
                    )}
                  </div>
                  <span style={{
                    display: 'inline-block',
                    padding: '0.2rem 0.5rem',
                    borderRadius: 4,
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    background: project.status === 'active' ? colors.primaryLight : colors.inputBg,
                    color: project.status === 'active' ? colors.primary : colors.textMuted,
                  }}>
                    {project.status || 'active'}
                  </span>
                  <div style={{ display: 'flex', gap: '0.4rem' }}>
                    <button
                      onClick={() => selectProject(project)}
                      style={{
                        padding: '0.35rem 0.6rem',
                        background: isSelected ? colors.primary : 'transparent',
                        border: `1px solid ${colors.primary}`,
                        borderRadius: 4,
                        color: isSelected ? 'white' : colors.primary,
                        fontSize: '0.75rem',
                        fontWeight: 500,
                        cursor: 'pointer',
                      }}
                    >
                      {isSelected ? 'Selected' : 'Select'}
                    </button>
                    <button
                      onClick={() => handleEdit(project)}
                      style={{
                        padding: '0.35rem 0.5rem',
                        background: 'transparent',
                        border: `1px solid ${colors.blue}`,
                        borderRadius: 4,
                        color: colors.blue,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                      }}
                    >
                      <Edit2 size={12} />
                    </button>
                    <button
                      onClick={() => handleDelete(project)}
                      style={{
                        padding: '0.35rem 0.5rem',
                        background: 'transparent',
                        border: `1px solid ${colors.red}`,
                        borderRadius: 4,
                        color: colors.red,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                      }}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
