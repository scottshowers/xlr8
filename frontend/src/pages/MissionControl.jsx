/**
 * MissionControl.jsx - Dashboard / Home
 * 
 * WIRED TO REAL API - Shows ALL projects (real + demo)
 * Aggregates stats from metadata.detected_domains for real projects.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Plus } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Generate a consistent color based on string
const getCustomerColor = (name) => {
  const colors = [
    '#83b16d', '#2766b1', '#285390', '#5f4282', '#993c44',
    '#d97706', '#93abd9', '#a1c3d4', '#b2d6de', '#6b9b5a',
  ];
  let hash = 0;
  for (let i = 0; i < (name || '').length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
};

// Parse demo stats from notes field
const parseDemoStats = (notes) => {
  if (!notes) return null;
  const match = notes.match(/\[DEMO_STATS\](.*?)\[\/DEMO_STATS\]/s);
  if (match) {
    try {
      return JSON.parse(match[1]);
    } catch {
      return null;
    }
  }
  return null;
};

// Get initials from name
const getInitials = (name) => {
  if (!name) return '??';
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
};

const MissionControl = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/list`);
      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      
      // Process all projects
      const processed = data.map(p => {
        const demoStats = parseDemoStats(p.notes);
        const metadata = p.metadata || {};
        const detectedDomains = metadata.detected_domains || {};
        
        // Use demo stats if available, otherwise use real metadata
        const hasRealData = !!detectedDomains.tables_analyzed;
        
        return {
          ...p,
          initials: getInitials(p.customer || p.name),
          demoStats,
          hasRealData,
          // Stats - prefer demo, fallback to real data indicators
          findings: demoStats?.findings || { critical: 0, warning: 0, info: 0, total: 0 },
          progress: demoStats?.progress || 0,
          tablesAnalyzed: detectedDomains.tables_analyzed || 0,
          columnsAnalyzed: detectedDomains.columns_analyzed || 0,
          primaryDomain: detectedDomains.primary_domain || null,
        };
      });
      
      setProjects(processed);
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      setLoading(false);
    }
  };

  // Calculate aggregated stats
  const activeProjects = projects.filter(p => p.status !== 'completed');
  const projectsWithData = projects.filter(p => p.hasRealData || p.demoStats);
  const totalFindings = projects.reduce((sum, p) => sum + (p.findings.total || 0), 0);
  const pendingFindings = projects.reduce((sum, p) => sum + (p.findings.critical || 0) + (p.findings.warning || 0), 0);
  const totalTablesAnalyzed = projects.reduce((sum, p) => sum + (p.tablesAnalyzed || 0), 0);
  
  // Items needing attention
  const attentionItems = [
    // Projects with critical findings (demo)
    ...projects.filter(p => p.findings.critical > 0).map(p => ({
      id: `critical-${p.id}`,
      type: 'critical',
      title: `${p.customer || p.name} - ${p.findings.critical} critical findings`,
      meta: `${p.engagement_type || p.type || 'Engagement'}`,
      projectId: p.id
    })),
    // Projects with real data but no playbooks yet
    ...projects.filter(p => p.hasRealData && (!p.playbooks || p.playbooks.length === 0)).map(p => ({
      id: `noplaybook-${p.id}`,
      type: 'warning',
      title: `${p.customer || p.name} - No playbooks assigned`,
      meta: `${p.tablesAnalyzed} tables analyzed, ready for playbook selection`,
      projectId: p.id
    })),
  ].slice(0, 5);

  // Recent projects (all, sorted by updated_at)
  const recentProjects = [...projects]
    .sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at))
    .slice(0, 4)
    .map(p => ({
      id: p.id,
      name: p.customer || p.name,
      initials: p.initials,
      system: (p.systems || []).map(s => s.replace(/_/g, ' ').replace(/-/g, ' ')).join(', ') || p.product || 'Unknown',
      type: p.engagement_type || p.type || 'Engagement',
      hasData: p.hasRealData,
      tablesAnalyzed: p.tablesAnalyzed,
      pending: (p.findings.critical || 0) + (p.findings.warning || 0),
      approved: Math.round((p.findings.total || 0) * (p.progress || 0) / 100),
      total: p.findings.total || 0
    }));

  if (loading) {
    return (
      <div className="page-loading">
        <Loader2 size={24} className="spin" />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="mission-control">
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title">Mission Control</h1>
          <p className="page-subtitle">Overview of your active projects</p>
        </div>
        <button className="btn btn-primary btn-lg" onClick={() => navigate('/projects/new')}>
          <Plus size={18} />
          New Project
        </button>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Active Projects</div>
          <div className="stat-value">{activeProjects.length}</div>
          <div className="stat-detail">{projects.length} total</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Tables Analyzed</div>
          <div className="stat-value">{totalTablesAnalyzed}</div>
          <div className="stat-detail">{projectsWithData.length} projects with data</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Findings</div>
          <div className="stat-value">{totalFindings}</div>
          <div className="stat-detail">{pendingFindings} pending review</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Needs Attention</div>
          <div className="stat-value stat-value--warning">{attentionItems.length}</div>
          <div className="stat-detail">Items requiring action</div>
        </div>
      </div>

      {/* Needs Attention */}
      {attentionItems.length > 0 && (
        <>
          <div className="section-header">
            <h2 className="section-title">Needs Attention</h2>
          </div>

          <div className="attention-list">
            {attentionItems.map(item => (
              <div 
                key={item.id} 
                className="attention-item"
                onClick={() => navigate(`/projects/${item.projectId}/hub`)}
              >
                <div className={`attention-indicator attention-indicator--${item.type}`} />
                <div className="attention-content">
                  <div className="attention-title">{item.title}</div>
                  <div className="attention-meta">{item.meta}</div>
                </div>
                <div className="attention-action">Review</div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Recent Projects */}
      <div className="section-header">
        <h2 className="section-title">Recent Projects</h2>
        <button className="btn btn-secondary" onClick={() => navigate('/projects')}>
          View All Projects
        </button>
      </div>

      {recentProjects.length === 0 ? (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
            <p className="text-muted">No projects yet.</p>
            <button className="btn btn-primary mt-4" onClick={() => navigate('/projects/new')}>
              Create Your First Project
            </button>
          </div>
        </div>
      ) : (
        <div className="projects-grid">
          {recentProjects.map(project => (
            <div 
              key={project.id} 
              className="project-card"
              onClick={() => navigate(`/projects/${project.id}/hub`)}
            >
              <div className="project-card__header">
                <div 
                  className="project-card__avatar"
                  style={{ background: getCustomerColor(project.name) }}
                >
                  {project.initials}
                </div>
                <div>
                  <div className="project-card__name">{project.name}</div>
                  <div className="project-card__system">{project.system}</div>
                </div>
              </div>
              <div className="project-card__stats">
                {project.hasData ? (
                  <>
                    <div className="project-stat">
                      <div className="project-stat__value">{project.tablesAnalyzed}</div>
                      <div className="project-stat__label">Tables</div>
                    </div>
                    <div className="project-stat">
                      <div className={`project-stat__value ${project.pending > 0 ? 'project-stat__value--warning' : ''}`}>
                        {project.pending}
                      </div>
                      <div className="project-stat__label">Pending</div>
                    </div>
                    <div className="project-stat">
                      <div className="project-stat__value project-stat__value--success">{project.approved}</div>
                      <div className="project-stat__label">Approved</div>
                    </div>
                  </>
                ) : project.total > 0 ? (
                  <>
                    <div className="project-stat">
                      <div className={`project-stat__value ${project.pending > 5 ? 'project-stat__value--critical' : 'project-stat__value--warning'}`}>
                        {project.pending}
                      </div>
                      <div className="project-stat__label">Pending</div>
                    </div>
                    <div className="project-stat">
                      <div className="project-stat__value project-stat__value--success">{project.approved}</div>
                      <div className="project-stat__label">Approved</div>
                    </div>
                    <div className="project-stat">
                      <div className="project-stat__value">{project.total}</div>
                      <div className="project-stat__label">Total</div>
                    </div>
                  </>
                ) : (
                  <div className="project-stat" style={{ flex: 1, textAlign: 'center' }}>
                    <div className="project-stat__label" style={{ color: 'var(--text-muted)' }}>
                      {project.type}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MissionControl;
