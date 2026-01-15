/**
 * ProjectsPage - Project Management
 * 
 * UPDATED: January 4, 2026
 * - Added multi-select for Systems, Domains, Functional Areas
 * - Fetches reference data from /api/reference/*
 * - Engagement type selector
 * - Mission Control color palette
 * - Added breadcrumb navigation for edit mode
 */

import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { getCustomerColorPalette } from '../utils/customerColors';
import { FolderOpen, Plus, Edit2, Trash2, Check, X, Server, Briefcase, Layers, ChevronDown, ChevronRight, Home, RefreshCw } from 'lucide-react';
import { Tooltip } from '../components/ui';
import api from '../services/api';

// Mission Control Colors
const colors = {
  bg: '#f0f2f5',
  card: '#ffffff',
  cardBorder: '#e2e8f0',
  text: '#1a2332',
  textMuted: '#64748b',
  textLight: '#94a3b8',
  primary: '#83b16d',
  primaryLight: 'rgba(131, 177, 109, 0.1)',
  accent: '#285390',
  accentLight: 'rgba(40, 83, 144, 0.1)',
  electricBlue: '#2766b1',
  royalPurple: '#5f4282',
  warning: '#d97706',
  warningLight: 'rgba(217, 119, 6, 0.1)',
  red: '#dc2626',
  redLight: 'rgba(220, 38, 38, 0.1)',
  divider: '#e2e8f0',
  inputBg: '#f8fafc',
  inputBorder: '#e2e8f0',
};

// Domain colors
const domainColors = {
  hcm: '#3B82F6',
  finance: '#10B981',
  compliance: '#8B5CF6',
  crm: '#F59E0B',
  procurement: '#EC4899',
  itsm: '#6366F1',
};

// Available playbooks - must match PlaybooksPage
const AVAILABLE_PLAYBOOKS = [
  { id: 'year-end-checklist', name: 'Year-End Checklist', icon: '' },
  { id: 'secure-2.0', name: 'SECURE 2.0 Compliance', icon: '' },
  { id: 'one-big-bill', name: 'One Big Beautiful Bill', icon: '' },
  { id: 'payroll-audit', name: 'Payroll Configuration Audit', icon: '' },
  { id: 'data-validation', name: 'Pre-Load Data Validation', icon: '' },
];

// ============================================================================
// MULTI-SELECT COMPONENT
// ============================================================================
function MultiSelect({ label, icon: Icon, items, selected, onChange, placeholder, groupBy, getColor, tooltip }) {
  const [isOpen, setIsOpen] = useState(false);
  
  const handleToggle = (code) => {
    if (selected.includes(code)) {
      onChange(selected.filter(c => c !== code));
    } else {
      onChange([...selected, code]);
    }
  };
  
  // Group items if groupBy function provided
  const grouped = groupBy ? items.reduce((acc, item) => {
    const group = groupBy(item);
    if (!acc[group]) acc[group] = [];
    acc[group].push(item);
    return acc;
  }, {}) : { all: items };
  
  const labelElement = (
    <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text, cursor: tooltip ? 'help' : 'default' }}>
      {label}
    </label>
  );
  
  return (
    <div style={{ position: 'relative' }}>
      {tooltip ? (
        <Tooltip title={tooltip.title} detail={tooltip.detail} action={tooltip.action}>
          {labelElement}
        </Tooltip>
      ) : labelElement}
      
      {/* Selected chips */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        style={{
          minHeight: '42px',
          padding: '0.4rem',
          border: `1px solid ${isOpen ? colors.primary : colors.inputBorder}`,
          borderRadius: 6,
          background: colors.card,
          cursor: 'pointer',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.35rem',
          alignItems: 'center',
        }}
      >
        {selected.length === 0 ? (
          <span style={{ color: colors.textMuted, fontSize: '0.85rem', padding: '0.2rem 0.4rem' }}>
            {placeholder}
          </span>
        ) : (
          selected.map(code => {
            const item = items.find(i => i.code === code);
            const color = getColor ? getColor(item) : colors.primary;
            return (
              <span
                key={code}
                onClick={(e) => { e.stopPropagation(); handleToggle(code); }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '0.2rem 0.5rem',
                  background: `${color}15`,
                  border: `1px solid ${color}40`,
                  borderRadius: 12,
                  fontSize: '0.8rem',
                  color: color,
                }}
              >
                {Icon && <Icon size={12} />}
                {item?.name || code}
                <X size={12} style={{ cursor: 'pointer' }} />
              </span>
            );
          })
        )}
        <ChevronDown size={16} style={{ marginLeft: 'auto', color: colors.textMuted }} />
      </div>
      
      {/* Dropdown */}
      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          maxHeight: '250px',
          overflowY: 'auto',
          background: colors.card,
          border: `1px solid ${colors.inputBorder}`,
          borderRadius: 6,
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          zIndex: 100,
          marginTop: '4px',
        }}>
          {Object.entries(grouped).map(([group, groupItems]) => (
            <div key={group}>
              {group !== 'all' && (
                <div style={{
                  padding: '0.5rem 0.75rem',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  color: colors.textMuted,
                  background: colors.inputBg,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  borderBottom: `1px solid ${colors.divider}`,
                }}>
                  {group}
                </div>
              )}
              {groupItems.map(item => {
                const isSelected = selected.includes(item.code);
                const color = getColor ? getColor(item) : colors.primary;
                return (
                  <div
                    key={item.code}
                    onClick={() => handleToggle(item.code)}
                    style={{
                      padding: '0.6rem 0.75rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      cursor: 'pointer',
                      background: isSelected ? `${color}10` : 'transparent',
                      borderLeft: `3px solid ${isSelected ? color : 'transparent'}`,
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = `${color}08`}
                    onMouseLeave={(e) => e.currentTarget.style.background = isSelected ? `${color}10` : 'transparent'}
                  >
                    <input 
                      type="checkbox" 
                      checked={isSelected} 
                      onChange={() => {}}
                      style={{ accentColor: color }}
                    />
                    <span style={{ fontSize: '0.85rem', color: colors.text }}>{item.name}</span>
                    {item.vendor && (
                      <span style={{ fontSize: '0.75rem', color: colors.textMuted, marginLeft: 'auto' }}>
                        {item.vendor}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
      
      {/* Click outside to close */}
      {isOpen && (
        <div 
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 99 }}
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function ProjectsPage() {
  const { projects, createProject, updateProject, deleteProject, selectProject, activeProject } = useProject();
  const location = useLocation();
  
  const [showForm, setShowForm] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    customer: '',
    systems: [],
    domains: [],
    functional_areas: [],
    engagement_type: '',
    target_go_live: '',
    lead_name: '',
    notes: '',
    playbooks: [],
  });
  
  // Reference data
  const [allSystems, setAllSystems] = useState([]);
  const [allDomains, setAllDomains] = useState([]);
  const [allFunctionalAreas, setAllFunctionalAreas] = useState([]);
  const [engagementTypes, setEngagementTypes] = useState([]);
  const [loadingRef, setLoadingRef] = useState(false);
  const [refreshingProject, setRefreshingProject] = useState(null);
  
  // Refresh analysis for a project
  const handleRefreshAnalysis = async (project) => {
    const projectName = project.name;
    setRefreshingProject(projectName);
    try {
      const response = await api.post(`/intelligence/${projectName}/analyze`);
      const data = response.data;
      const analysis = data?.analysis || {};
      const metricsCount = analysis?.organizational_metrics?.total || 0;
      const findingsCount = analysis?.findings?.length || 0;
      alert(`✅ Analysis complete for ${projectName}\n\n• ${metricsCount} metrics computed\n• ${findingsCount} findings detected`);
    } catch (err) {
      console.error('Failed to refresh analysis:', err);
      alert(`❌ Failed to refresh analysis: ${err.message}`);
    } finally {
      setRefreshingProject(null);
    }
  };
  
  // Reset form when navigating to this page (clicking Projects in nav)
  useEffect(() => {
    setShowForm(false);
    setEditingProject(null);
  }, [location.key]);
  
  // Load reference data
  useEffect(() => {
    const loadReferenceData = async () => {
      setLoadingRef(true);
      try {
        const [sysRes, domRes, faRes, etRes] = await Promise.all([
          api.get('/reference/systems'),
          api.get('/reference/domains'),
          api.get('/reference/functional-areas'),
          api.get('/reference/engagement-types'),
        ]);
        setAllSystems(sysRes.data || []);
        setAllDomains(domRes.data || []);
        setAllFunctionalAreas(faRes.data || []);
        setEngagementTypes(etRes.data || []);
      } catch (err) {
        console.error('Failed to load reference data:', err);
      } finally {
        setLoadingRef(false);
      }
    };
    loadReferenceData();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // Build project data
      const projectData = {
        name: formData.name,
        customer: formData.customer,
        notes: formData.notes,
        playbooks: formData.playbooks,
        // Legacy field for backwards compat
        product: allSystems.find(s => s.code === formData.systems[0])?.name || '',
        type: engagementTypes.find(t => t.code === formData.engagement_type)?.name || formData.engagement_type,
        // New fields
        systems: formData.systems,
        domains: formData.domains,
        functional_areas: formData.functional_areas.map(fa => {
          const area = allFunctionalAreas.find(a => a.code === fa);
          return area ? { domain: area.domain_code, area: fa } : { area: fa };
        }),
        engagement_type: formData.engagement_type,
        target_go_live: formData.target_go_live || null,
        lead_name: formData.lead_name || null,
      };
      
      if (editingProject) {
        await updateProject(editingProject.id, projectData);
      } else {
        await createProject(projectData);
      }
      setShowForm(false);
      setEditingProject(null);
      resetForm();
    } catch (err) {
      alert('Failed to save project: ' + err.message);
    }
  };
  
  const resetForm = () => {
    setFormData({
      name: '',
      customer: '',
      systems: [],
      domains: [],
      functional_areas: [],
      engagement_type: '',
      target_go_live: '',
      lead_name: '',
      notes: '',
      playbooks: [],
    });
  };

  const handleEdit = (project) => {
    setEditingProject(project);
    setFormData({
      name: project.name || '',
      customer: project.customer || '',
      systems: project.systems || [],
      domains: project.domains || [],
      functional_areas: (project.functional_areas || []).map(fa => fa.area || fa.code || fa),
      engagement_type: project.engagement_type || '',
      target_go_live: project.target_go_live || '',
      lead_name: project.lead_name || '',
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
    resetForm();
  };

  const getPlaybookName = (id) => {
    const pb = AVAILABLE_PLAYBOOKS.find(p => p.id === id);
    return pb ? pb.name : id;
  };

  const getPlaybookIcon = (id) => {
    const pb = AVAILABLE_PLAYBOOKS.find(p => p.id === id);
    return pb ? pb.icon : '';
  };
  
  const getSystemColor = () => colors.electricBlue;
  const getDomainColor = (item) => domainColors[item?.code] || colors.accent;
  const getFunctionalAreaColor = (item) => domainColors[item?.domain_code] || colors.accent;

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ 
          margin: 0, fontSize: '20px', fontWeight: 600, color: colors.text, 
          display: 'flex', alignItems: 'center', gap: '10px',
          fontFamily: "'Sora', sans-serif"
        }}>
          <div style={{ 
            width: '36px', height: '36px', borderRadius: '10px', 
            backgroundColor: colors.primary, 
            display: 'flex', alignItems: 'center', justifyContent: 'center' 
          }}>
            <FolderOpen size={20} color="#ffffff" />
          </div>
          Projects
        </h1>
        <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: colors.textMuted }}>
          Create and manage customer projects
        </p>
      </div>

      {/* Breadcrumb - shown when in form mode */}
      {showForm && (
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '8px', 
          marginBottom: '16px',
          fontSize: '13px'
        }}>
          <button
            onClick={() => { setShowForm(false); setEditingProject(null); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'none',
              border: 'none',
              padding: 0,
              color: colors.accent,
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            <Home size={14} />
            Projects
          </button>
          <ChevronRight size={14} color={colors.textMuted} />
          <span style={{ color: colors.text, fontWeight: 500 }}>
            {editingProject ? `Edit: ${editingProject.name}` : 'New Project'}
          </span>
        </div>
      )}

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
          <Tooltip 
            title="Project Management" 
            detail="Projects organize your customer implementation work. Each project has its own data, playbooks, and analysis."
            action="Select a project to work with its data"
          >
            <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 600, color: colors.text, cursor: 'help' }}>
              All Projects
            </h3>
          </Tooltip>
          <Tooltip 
            title="Create New Project" 
            detail="Set up a new customer project with systems, domains, and playbooks."
            action="Projects isolate data between customers"
          >
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
          </Tooltip>
        </div>

        {/* Form */}
        {showForm && (
          <div style={{
            padding: '1.5rem',
            background: colors.inputBg,
            borderBottom: `1px solid ${colors.divider}`,
          }}>
            {/* Form Header with Close */}
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              marginBottom: '1rem',
              paddingBottom: '0.75rem',
              borderBottom: `1px solid ${colors.divider}`
            }}>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: colors.text }}>
                {editingProject ? `Edit Project: ${editingProject.name}` : 'New Project'}
              </h3>
              <button
                type="button"
                onClick={cancelForm}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 32,
                  height: 32,
                  background: 'transparent',
                  border: `1px solid ${colors.inputBorder}`,
                  borderRadius: 6,
                  color: colors.textMuted,
                  cursor: 'pointer',
                }}
                title="Close form"
              >
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              {/* Row 1: AR# and Company */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <Tooltip title="Customer AR#" detail="Your internal project identifier or engagement number. Used to uniquely identify this customer's implementation." action="e.g., MEY1000, ABC-2024-001">
                    <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text, cursor: 'help' }}>
                      Customer AR# *
                    </label>
                  </Tooltip>
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
                  <Tooltip title="Company Name" detail="The customer's company name. This appears throughout the platform to identify whose data you're working with." action="Use official company name">
                    <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text, cursor: 'help' }}>
                      Company Name *
                    </label>
                  </Tooltip>
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
                    placeholder="e.g., Meyerhoff Industries"
                    required
                  />
                </div>
              </div>
              
              {/* Row 2: Systems and Engagement Type */}
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <MultiSelect
                  label="Systems"
                  icon={Server}
                  items={allSystems}
                  selected={formData.systems}
                  onChange={(systems) => setFormData({ ...formData, systems })}
                  placeholder="Select systems..."
                  groupBy={(item) => item.vendor}
                  getColor={getSystemColor}
                  tooltip={{ title: "Systems", detail: "HCM/ERP systems the customer is using or implementing. Determines which reference docs and validation rules apply.", action: "Select all systems in scope" }}
                />
                <div>
                  <Tooltip title="Engagement Type" detail="The type of consulting engagement. Affects which playbooks and analysis patterns are most relevant." action="Implementation, Optimization, Assessment, etc.">
                    <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text, cursor: 'help' }}>
                      Engagement Type
                    </label>
                  </Tooltip>
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
                      height: '42px',
                    }}
                    value={formData.engagement_type}
                    onChange={(e) => setFormData({ ...formData, engagement_type: e.target.value })}
                  >
                    <option value="">Select type...</option>
                    {engagementTypes.map(t => (
                      <option key={t.code} value={t.code}>{t.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              {/* Row 2.5: Go-Live and Project Lead */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <Tooltip title="Target Go-Live" detail="The planned go-live date for this implementation. Used for timeline tracking and milestone planning." action="Format: YYYY-MM-DD">
                    <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text, cursor: 'help' }}>
                      Target Go-Live
                    </label>
                  </Tooltip>
                  <input
                    type="date"
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      border: `1px solid ${colors.inputBorder}`,
                      borderRadius: 6,
                      fontSize: '0.85rem',
                      background: colors.card,
                      color: colors.text,
                      boxSizing: 'border-box',
                      height: '42px',
                    }}
                    value={formData.target_go_live}
                    onChange={(e) => setFormData({ ...formData, target_go_live: e.target.value })}
                  />
                </div>
                <div>
                  <Tooltip title="Project Lead" detail="The primary consultant or project manager responsible for this engagement. Shown in project listings and reports." action="Enter name or email">
                    <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text, cursor: 'help' }}>
                      Project Lead
                    </label>
                  </Tooltip>
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
                    value={formData.lead_name}
                    onChange={(e) => setFormData({ ...formData, lead_name: e.target.value })}
                    placeholder="e.g., John Smith"
                  />
                </div>
              </div>
              
              {/* Row 3: Domains */}
              <div style={{ marginBottom: '1rem' }}>
                <MultiSelect
                  label="Domains"
                  icon={Briefcase}
                  items={allDomains}
                  selected={formData.domains}
                  onChange={(domains) => setFormData({ ...formData, domains })}
                  placeholder="Select domains..."
                  getColor={getDomainColor}
                  tooltip={{ title: "Domains", detail: "Business domains being addressed in this project. Helps categorize data and focus analysis on relevant areas.", action: "Payroll, Time, Benefits, HR, etc." }}
                />
              </div>
              
              {/* Row 4: Functional Areas */}
              <div style={{ marginBottom: '1rem' }}>
                <MultiSelect
                  label="Functional Areas"
                  icon={Layers}
                  items={allFunctionalAreas}
                  selected={formData.functional_areas}
                  onChange={(functional_areas) => setFormData({ ...formData, functional_areas })}
                  placeholder="Select functional areas..."
                  groupBy={(item) => item.domain_name}
                  getColor={getFunctionalAreaColor}
                  tooltip={{ title: "Functional Areas", detail: "Specific functional areas within each domain. Provides granular categorization for targeted analysis and playbook selection.", action: "Grouped by domain for easy selection" }}
                />
              </div>

              {/* Row 5: Notes */}
              <div style={{ marginBottom: '1rem' }}>
                <Tooltip title="Project Notes" detail="Free-form notes about this project. Useful for context, special requirements, or key contacts." action="Visible to all users working on this project">
                  <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text, cursor: 'help' }}>
                    Notes
                  </label>
                </Tooltip>
                <textarea
                  style={{
                    width: '100%',
                    padding: '0.6rem',
                    border: `1px solid ${colors.inputBorder}`,
                    borderRadius: 6,
                    fontSize: '0.85rem',
                    background: colors.card,
                    color: colors.text,
                    boxSizing: 'border-box',
                    minHeight: '60px',
                    resize: 'vertical',
                  }}
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Optional project notes..."
                />
              </div>
              
              {/* Row 6: Playbooks */}
              <div style={{ marginBottom: '1rem' }}>
                <Tooltip title="Assign Playbooks" detail="Playbooks are pre-built analysis workflows. Each playbook guides you through a specific type of analysis like data validation, compliance checking, or optimization." action="Select playbooks relevant to this engagement">
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.8rem', fontWeight: 600, color: colors.text, cursor: 'help' }}>
                    Assign Playbooks
                  </label>
                </Tooltip>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {AVAILABLE_PLAYBOOKS.map((playbook) => {
                    const isSelected = (formData.playbooks || []).includes(playbook.id);
                    return (
                      <Tooltip key={playbook.id} title={playbook.name} detail={playbook.description || `Run the ${playbook.name} analysis workflow on this project's data.`} position="bottom">
                        <div
                          onClick={() => handlePlaybookToggle(playbook.id)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            padding: '0.4rem 0.75rem',
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
                            onChange={() => {}}
                            style={{ accentColor: colors.primary }}
                          />
                          <span style={{ fontSize: '1rem' }}>{playbook.icon}</span>
                          <span style={{ fontSize: '0.8rem', color: colors.text }}>{playbook.name}</span>
                        </div>
                      </Tooltip>
                    );
                  })}
                </div>
              </div>

              {/* Buttons */}
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
              gridTemplateColumns: '1fr 1.2fr 2fr 1.2fr 80px 140px',
              padding: '0.75rem 1rem',
              background: colors.inputBg,
              borderBottom: `1px solid ${colors.divider}`,
              fontSize: '0.75rem',
              fontWeight: 600,
              color: colors.textMuted,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              <Tooltip title="AR#" detail="Your internal project identifier or engagement number." position="bottom">
                <span style={{ cursor: 'help' }}>AR#</span>
              </Tooltip>
              <Tooltip title="Company" detail="The customer's company name." position="bottom">
                <span style={{ cursor: 'help' }}>Company</span>
              </Tooltip>
              <Tooltip title="Scope" detail="Systems, domains, and functional areas in scope for this project. Color coded: Blue=Systems, Purple=Domains, Teal=Functional Areas." position="bottom">
                <span style={{ cursor: 'help' }}>Scope</span>
              </Tooltip>
              <Tooltip title="Playbooks" detail="Analysis workflows assigned to this project. Click to run playbook analysis." position="bottom">
                <span style={{ cursor: 'help' }}>Playbooks</span>
              </Tooltip>
              <Tooltip title="Status" detail="Current project status. Green=Active, Yellow=In Progress, Gray=Inactive." position="bottom">
                <span style={{ cursor: 'help' }}>Status</span>
              </Tooltip>
              <Tooltip title="Actions" detail="Select to work with project data, Edit to modify settings, Delete to remove." position="bottom">
                <span style={{ cursor: 'help' }}>Actions</span>
              </Tooltip>
            </div>

            {/* Project Rows */}
            {projects.map((project) => {
              const customerColors = getCustomerColorPalette(project.customer || project.name);
              const isSelected = activeProject?.id === project.id;
              const projectSystems = project.systems || [];
              const projectDomains = project.domains || [];
              const projectFAs = project.functional_areas || [];
              
              return (
                <div
                  key={project.id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1.2fr 2fr 1.2fr 80px 140px',
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
                  
                  {/* Scope: Systems, Domains, Functional Areas */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                    {/* Systems - Blue */}
                    {projectSystems.slice(0, 2).map(code => {
                      const sys = allSystems.find(s => s.code === code);
                      return (
                        <span
                          key={`sys-${code}`}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.2rem',
                            padding: '0.15rem 0.4rem',
                            background: `${colors.electricBlue}10`,
                            border: `1px solid ${colors.electricBlue}30`,
                            borderRadius: 4,
                            fontSize: '0.7rem',
                            color: colors.electricBlue,
                          }}
                          title={`System: ${sys?.name || code}`}
                        >
                          <Server size={9} />
                          {sys?.name || code}
                        </span>
                      );
                    })}
                    {/* Domains - Purple */}
                    {projectDomains.slice(0, 2).map(code => {
                      const dom = allDomains.find(d => d.code === code);
                      return (
                        <span
                          key={`dom-${code}`}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.2rem',
                            padding: '0.15rem 0.4rem',
                            background: `${colors.royalPurple}10`,
                            border: `1px solid ${colors.royalPurple}30`,
                            borderRadius: 4,
                            fontSize: '0.7rem',
                            color: colors.royalPurple,
                          }}
                          title={`Domain: ${dom?.name || code}`}
                        >
                          <Briefcase size={9} />
                          {dom?.name || code}
                        </span>
                      );
                    })}
                    {/* Functional Areas - Teal */}
                    {projectFAs.slice(0, 2).map((fa, i) => {
                      const faCode = fa.area || fa.code || fa;
                      return (
                        <span
                          key={`fa-${faCode}-${i}`}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.2rem',
                            padding: '0.15rem 0.4rem',
                            background: `${colors.accent}10`,
                            border: `1px solid ${colors.accent}30`,
                            borderRadius: 4,
                            fontSize: '0.7rem',
                            color: colors.accent,
                          }}
                          title={`Functional Area: ${faCode}`}
                        >
                          <Layers size={9} />
                          {faCode}
                        </span>
                      );
                    })}
                    {/* Overflow indicator */}
                    {(projectSystems.length + projectDomains.length + projectFAs.length) > 6 && (
                      <span style={{ fontSize: '0.7rem', color: colors.textMuted }}>
                        +{(projectSystems.length + projectDomains.length + projectFAs.length) - 6}
                      </span>
                    )}
                    {/* Empty state */}
                    {projectSystems.length === 0 && projectDomains.length === 0 && projectFAs.length === 0 && (
                      project.product ? (
                        <span style={{ color: colors.textMuted, fontSize: '0.75rem' }}>{project.product}</span>
                      ) : (
                        <span style={{ color: colors.textLight, fontSize: '0.75rem' }}>—</span>
                      )
                    )}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                    {(project.playbooks || []).length > 0 ? (
                      project.playbooks.slice(0, 2).map(pbId => (
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
                      <span style={{ color: colors.textLight, fontSize: '0.75rem' }}>None</span>
                    )}
                    {(project.playbooks || []).length > 2 && (
                      <span style={{ fontSize: '0.75rem', color: colors.textMuted }}>+{project.playbooks.length - 2}</span>
                    )}
                  </div>
                  <div style={{ overflow: 'hidden' }}>
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
                  </div>
                  <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-start' }}>
                    <Tooltip title={isSelected ? "Currently Selected" : "Select Project"} detail={isSelected ? "This project is currently active. All data operations will use this project's data." : "Make this the active project. All data uploads and queries will be scoped to this project."} position="left">
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
                    </Tooltip>
                    <Tooltip title="Edit Project" detail="Modify project settings including systems, domains, functional areas, and playbook assignments." position="left">
                      <button
                        onClick={() => handleEdit(project)}
                        style={{
                          padding: '0.35rem 0.5rem',
                          background: 'transparent',
                          border: `1px solid ${colors.accent}`,
                          borderRadius: 4,
                          color: colors.accent,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        <Edit2 size={12} />
                      </button>
                    </Tooltip>
                    <Tooltip title="Refresh Analysis" detail="Re-run intelligence analysis to recompute metrics, detect issues, and update organizational insights." position="left">
                      <button
                        onClick={() => handleRefreshAnalysis(project)}
                        disabled={refreshingProject === project.name}
                        style={{
                          padding: '0.35rem 0.5rem',
                          background: 'transparent',
                          border: `1px solid ${colors.primary}`,
                          borderRadius: 4,
                          color: colors.primary,
                          cursor: refreshingProject === project.name ? 'wait' : 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          opacity: refreshingProject === project.name ? 0.6 : 1,
                        }}
                      >
                        <RefreshCw size={12} style={{ animation: refreshingProject === project.name ? 'xlr8-spin 1s linear infinite' : 'none' }} />
                      </button>
                    </Tooltip>
                    <Tooltip title="Delete Project" detail="Permanently remove this project and all associated data. This action cannot be undone." position="left">
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
                    </Tooltip>
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
