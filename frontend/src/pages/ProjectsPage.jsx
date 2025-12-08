/**
 * ProjectsPage - Project Management
 * Extracted from AdminPage
 * Updated: Added playbook assignment
 */

import React, { useState } from 'react';
import { useProject } from '../context/ProjectContext';

// Available playbooks - must match PlaybooksPage
const AVAILABLE_PLAYBOOKS = [
  { id: 'year-end-checklist', name: 'Year-End Checklist', icon: '📅' },
  { id: 'secure-2.0', name: 'SECURE 2.0 Compliance', icon: '🏛️' },
  { id: 'one-big-bill', name: 'One Big Beautiful Bill', icon: '📜' },
  { id: 'payroll-audit', name: 'Payroll Configuration Audit', icon: '🔍' },
  { id: 'data-validation', name: 'Pre-Load Data Validation', icon: '✅' },
];

export default function ProjectsPage() {
  const { projects, createProject, updateProject, deleteProject, selectProject } = useProject();
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

  const styles = {
    container: {
      maxWidth: '1200px',
    },
    pageHeader: {
      marginBottom: '1.5rem',
    },
    pageTitle: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.75rem',
      fontWeight: '700',
      color: '#2a3441',
      margin: 0,
    },
    pageSubtitle: {
      color: '#5f6c7b',
      marginTop: '0.25rem',
    },
    card: {
      background: 'white',
      borderRadius: '16px',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      overflow: 'hidden',
      padding: '1.5rem',
    },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' },
    title: { fontSize: '1.1rem', fontWeight: '700', color: '#2a3441' },
    button: { padding: '0.6rem 1.2rem', background: '#83b16d', border: 'none', borderRadius: '8px', color: 'white', fontWeight: '600', cursor: 'pointer' },
    table: { width: '100%', borderCollapse: 'collapse' },
    th: { textAlign: 'left', padding: '0.75rem 1rem', background: '#f8fafc', fontWeight: '600', fontSize: '0.8rem', color: '#5f6c7b', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '1px solid #e1e8ed' },
    td: { padding: '0.75rem 1rem', borderBottom: '1px solid #e1e8ed' },
    actions: { display: 'flex', gap: '0.5rem' },
    actionBtn: (color) => ({ padding: '0.35rem 0.75rem', background: 'transparent', border: `1px solid ${color}`, borderRadius: '4px', color: color, fontSize: '0.8rem', cursor: 'pointer' }),
    form: { background: '#f8fafc', borderRadius: '12px', padding: '1.5rem', marginBottom: '1.5rem' },
    formGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' },
    formGroup: { marginBottom: '1rem' },
    label: { display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: '600', color: '#2a3441' },
    input: { width: '100%', padding: '0.65rem', border: '1px solid #e1e8ed', borderRadius: '6px', fontSize: '0.9rem', boxSizing: 'border-box' },
    formActions: { display: 'flex', gap: '0.75rem', marginTop: '1rem' },
    cancelBtn: { padding: '0.6rem 1.2rem', background: '#f0f4f7', border: 'none', borderRadius: '8px', color: '#5f6c7b', fontWeight: '600', cursor: 'pointer' },
    playbooksSection: {
      gridColumn: 'span 2',
      marginTop: '0.5rem',
    },
    playbooksGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
      gap: '0.75rem',
      marginTop: '0.5rem',
    },
    playbookItem: (selected) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.75rem',
      background: selected ? '#f0fdf4' : 'white',
      border: `1px solid ${selected ? '#83b16d' : '#e1e8ed'}`,
      borderRadius: '8px',
      cursor: 'pointer',
      transition: 'all 0.15s ease',
    }),
    playbookCheckbox: {
      width: '18px',
      height: '18px',
      accentColor: '#83b16d',
    },
    playbookLabel: {
      fontSize: '0.85rem',
      color: '#2a3441',
      cursor: 'pointer',
    },
    playbookIcon: {
      fontSize: '1.1rem',
    },
    playbookBadge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.25rem',
      padding: '0.2rem 0.5rem',
      background: '#f0fdf4',
      border: '1px solid #bbf7d0',
      borderRadius: '4px',
      fontSize: '0.7rem',
      color: '#166534',
      marginRight: '0.25rem',
      marginBottom: '0.25rem',
    },
    playbooksCell: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '0.25rem',
    },
  };

  // Get playbook name by ID
  const getPlaybookName = (id) => {
    const pb = AVAILABLE_PLAYBOOKS.find(p => p.id === id);
    return pb ? pb.name : id;
  };

  const getPlaybookIcon = (id) => {
    const pb = AVAILABLE_PLAYBOOKS.find(p => p.id === id);
    return pb ? pb.icon : '📋';
  };

  return (
    <div style={styles.container}>
      <div style={styles.pageHeader}>
        <h1 style={styles.pageTitle}>Projects</h1>
        <p style={styles.pageSubtitle}>Create and manage customer projects.</p>
      </div>

      <div style={styles.card}>
        <div style={styles.header}>
          <h3 style={styles.title}>Manage Projects</h3>
          <button style={styles.button} onClick={() => setShowForm(true)}>➕ New Project</button>
        </div>

        {showForm && (
          <form style={styles.form} onSubmit={handleSubmit}>
            <div style={styles.formGrid}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Customer AR# *</label>
                <input style={styles.input} value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} placeholder="e.g., MEY1000" required />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Company Name *</label>
                <input style={styles.input} value={formData.customer} onChange={(e) => setFormData({ ...formData, customer: e.target.value })} placeholder="e.g., Meyer Corporation" required />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Product *</label>
                <select style={styles.input} value={formData.product || ''} onChange={(e) => setFormData({ ...formData, product: e.target.value })} required>
                  <option value="">Select Product...</option>
                  <option value="UKG Pro">UKG Pro</option>
                  <option value="WFM Dimensions">WFM Dimensions</option>
                  <option value="UKG Ready">UKG Ready</option>
                </select>
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Type</label>
                <select style={styles.input} value={formData.type} onChange={(e) => setFormData({ ...formData, type: e.target.value })}>
                  <option value="Implementation">Implementation</option>
                  <option value="Support">Support</option>
                  <option value="Analysis">Analysis</option>
                </select>
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Notes</label>
                <input style={styles.input} value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} placeholder="Optional notes..." />
              </div>

              {/* Playbooks Selection */}
              <div style={styles.playbooksSection}>
                <label style={styles.label}>Assigned Playbooks</label>
                <p style={{ fontSize: '0.8rem', color: '#5f6c7b', margin: '0 0 0.75rem 0' }}>
                  Select which playbooks this customer can access.
                </p>
                <div style={styles.playbooksGrid}>
                  {AVAILABLE_PLAYBOOKS.map(playbook => {
                    const isSelected = (formData.playbooks || []).includes(playbook.id);
                    return (
                      <div
                        key={playbook.id}
                        style={styles.playbookItem(isSelected)}
                        onClick={() => handlePlaybookToggle(playbook.id)}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handlePlaybookToggle(playbook.id)}
                          style={styles.playbookCheckbox}
                        />
                        <span style={styles.playbookIcon}>{playbook.icon}</span>
                        <span style={styles.playbookLabel}>{playbook.name}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
            <div style={styles.formActions}>
              <button type="submit" style={styles.button}>{editingProject ? 'Update Project' : 'Create Project'}</button>
              <button type="button" style={styles.cancelBtn} onClick={() => { setShowForm(false); setEditingProject(null); setFormData({ name: '', customer: '', product: '', type: 'Implementation', notes: '', playbooks: [] }); }}>Cancel</button>
            </div>
          </form>
        )}

        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Customer AR#</th>
              <th style={styles.th}>Company Name</th>
              <th style={styles.th}>Product</th>
              <th style={styles.th}>Playbooks</th>
              <th style={styles.th}>Status</th>
              <th style={styles.th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => (
              <tr key={project.id}>
                <td style={styles.td}><strong>{project.name}</strong></td>
                <td style={styles.td}>{project.customer}</td>
                <td style={styles.td}>{project.product || '-'}</td>
                <td style={styles.td}>
                  <div style={styles.playbooksCell}>
                    {(project.playbooks || []).length > 0 ? (
                      project.playbooks.map(pbId => (
                        <span key={pbId} style={styles.playbookBadge}>
                          {getPlaybookIcon(pbId)} {getPlaybookName(pbId)}
                        </span>
                      ))
                    ) : (
                      <span style={{ color: '#9ca3af', fontSize: '0.8rem' }}>None assigned</span>
                    )}
                  </div>
                </td>
                <td style={styles.td}>
                  <span style={{ padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600', background: project.status === 'active' ? '#f0fdf4' : '#f8fafc', color: project.status === 'active' ? '#166534' : '#5f6c7b' }}>
                    {project.status || 'active'}
                  </span>
                </td>
                <td style={styles.td}>
                  <div style={styles.actions}>
                    <button style={styles.actionBtn('#83b16d')} onClick={() => selectProject(project)}>Select</button>
                    <button style={styles.actionBtn('#93abd9')} onClick={() => handleEdit(project)}>Edit</button>
                    <button style={styles.actionBtn('#e53e3e')} onClick={() => handleDelete(project)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
            {projects.length === 0 && (
              <tr>
                <td style={styles.td} colSpan={6}>
                  <div style={{ textAlign: 'center', padding: '2rem', color: '#5f6c7b' }}>No projects yet. Create one to get started.</div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
