/**
 * Dashboard.jsx - Home / Overview
 * 
 * WIRED TO REAL API - Aggregated stats across all projects.
 * Clickable stat cards route to relevant pages.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Plus, FolderOpen, Database, AlertTriangle, AlertCircle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

const getCustomerColor = (name) => {
  const colors = ['#83b16d', '#2766b1', '#285390', '#5f4282', '#993c44', '#d97706', '#93abd9', '#a1c3d4', '#b2d6de', '#6b9b5a'];
  let hash = 0;
  for (let i = 0; i < (name || '').length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
};

const parseDemoStats = (notes) => {
  if (!notes) return null;
  const match = notes.match(/\[DEMO_STATS\](.*?)\[\/DEMO_STATS\]/s);
  if (match) { try { return JSON.parse(match[1]); } catch { return null; } }
  return null;
};

const getInitials = (name) => {
  if (!name) return '??';
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
};

const Dashboard = () => {
  const navigate = useNavigate();
  const attentionRef = useRef(null);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchProjects(); }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/list`);
      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      
      const processed = data.map(p => {
        const demoStats = parseDemoStats(p.notes);
        const metadata = p.metadata || {};
        const detectedDomains = metadata.detected_domains || {};
        const hasRealData = !!detectedDomains.tables_analyzed;
        
        return {
          ...p,
          initials: getInitials(p.customer || p.name),
          demoStats,
          hasRealData,
          findings: demoStats?.findings || { critical: 0, warning: 0, info: 0, total: 0 },
          progress: demoStats?.progress || (hasRealData ? 100 : 0),
          tablesAnalyzed: detectedDomains.tables_analyzed || 0,
          columnsAnalyzed: detectedDomains.columns_analyzed || 0,
        };
      });
      
      setProjects(processed);
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      setLoading(false);
    }
  };

  // Aggregated stats (matching ProjectHub findings summary pattern)
  const activeProjects = projects.filter(p => p.status !== 'completed');
  const totalTablesAnalyzed = projects.reduce((sum, p) => sum + (p.tablesAnalyzed || 0), 0);
  const totalFindings = projects.reduce((sum, p) => sum + (p.findings.total || 0), 0);
  const totalCritical = projects.reduce((sum, p) => sum + (p.findings.critical || 0), 0);
  const totalWarning = projects.reduce((sum, p) => sum + (p.findings.warning || 0), 0);
  const totalInfo = projects.reduce((sum, p) => sum + (p.findings.info || 0), 0);
  const pendingReview = totalCritical + totalWarning;
  
  // Attention items
  const attentionItems = [
    ...projects.filter(p => p.findings.critical > 0).map(p => ({
      id: `critical-${p.id}`, type: 'critical',
      title: `${p.customer || p.name}`,
      subtitle: `${p.findings.critical} critical findings`,
      projectId: p.id
    })),
    ...projects.filter(p => p.hasRealData && (!p.playbooks || p.playbooks.length === 0)).map(p => ({
      id: `noplaybook-${p.id}`, type: 'warning',
      title: `${p.customer || p.name}`,
      subtitle: `${p.tablesAnalyzed} tables analyzed, no playbooks assigned`,
      projectId: p.id
    })),
  ].slice(0, 5);

  // Recent projects
  const recentProjects = [...projects]
    .sort((a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0))
    .slice(0, 6)
    .map(p => ({
      id: p.id,
      name: p.customer || p.name,
      initials: p.initials,
      system: (p.systems || []).map(s => s.replace(/_/g, ' ').replace(/-/g, ' ')).join(', ') || p.product || '-',
      type: p.engagement_type || p.type || '-',
      hasRealData: p.hasRealData,
      tablesAnalyzed: p.tablesAnalyzed,
      findings: p.findings,
      progress: p.progress || 0,
    }));

  const scrollToAttention = () => {
    attentionRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  if (loading) {
    return <div className="page-loading"><Loader2 size={24} className="spin" /><p>Loading...</p></div>;
  }

  return (
    <div className="dashboard">
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Overview of all projects and findings</p>
        </div>
        <button className="btn btn-primary btn-lg" onClick={() => navigate('/projects/new')}>
          <Plus size={18} />New Project
        </button>
      </div>

      {/* Stats Grid - Clickable */}
      <div className="stats-grid">
        <div className="stat-card stat-card--clickable" onClick={() => navigate('/projects')}>
          <div className="stat-card__icon"><FolderOpen size={20} /></div>
          <div className="stat-label">Active Projects</div>
          <div className="stat-value">{activeProjects.length}</div>
          <div className="stat-detail">{projects.length} total</div>
        </div>
        <div className="stat-card stat-card--clickable" onClick={() => navigate('/data')}>
          <div className="stat-card__icon"><Database size={20} /></div>
          <div className="stat-label">Tables Analyzed</div>
          <div className="stat-value">{totalTablesAnalyzed}</div>
          <div className="stat-detail">{projects.filter(p => p.hasRealData).length} projects with data</div>
        </div>
        <div className="stat-card stat-card--clickable" onClick={() => navigate('/findings')}>
          <div className="stat-card__icon"><AlertTriangle size={20} /></div>
          <div className="stat-label">Total Findings</div>
          <div className="stat-value">{totalFindings}</div>
          <div className="stat-detail">
            <span style={{ color: 'var(--critical)' }}>{totalCritical}</span> critical, 
            <span style={{ color: 'var(--warning)', marginLeft: '4px' }}>{totalWarning}</span> warning, 
            <span style={{ color: 'var(--info)', marginLeft: '4px' }}>{totalInfo}</span> info
          </div>
        </div>
        <div className="stat-card stat-card--clickable" onClick={scrollToAttention}>
          <div className="stat-card__icon"><AlertCircle size={20} /></div>
          <div className="stat-label">Needs Attention</div>
          <div className="stat-value stat-value--warning">{attentionItems.length}</div>
          <div className="stat-detail">Items requiring action</div>
        </div>
      </div>

      {/* Needs Attention */}
      <div ref={attentionRef}>
        {attentionItems.length > 0 && (
          <>
            <div className="section-header"><h2 className="section-title">Needs Attention</h2></div>
            <div className="attention-list">
              {attentionItems.map(item => (
                <div key={item.id} className="attention-item" onClick={() => navigate(`/projects/${item.projectId}/hub`)}>
                  <div className={`attention-indicator attention-indicator--${item.type}`} />
                  <div className="attention-content">
                    <div className="attention-title">{item.title}</div>
                    <div className="attention-meta">{item.subtitle}</div>
                  </div>
                  <div className="attention-action">Review</div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Recent Projects */}
      <div className="section-header">
        <h2 className="section-title">Recent Projects</h2>
        <button className="btn btn-secondary" onClick={() => navigate('/projects')}>View All</button>
      </div>

      {recentProjects.length === 0 ? (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
            <p className="text-muted">No customers yet.</p>
            <button className="btn btn-primary mt-4" onClick={() => navigate('/projects/new')}>Create Your First Project</button>
          </div>
        </div>
      ) : (
        <div className="projects-grid">
          {recentProjects.map(project => (
            <div key={project.id} className="project-card" onClick={() => navigate(`/projects/${project.id}/hub`)}>
              <div className="project-card__header">
                <div className="project-card__avatar" style={{ background: getCustomerColor(project.name) }}>{project.initials}</div>
                <div>
                  <div className="project-card__name">{project.name}</div>
                  <div className="project-card__system">{project.system}</div>
                </div>
              </div>
              <div className="project-card__stats">
                {project.hasRealData ? (
                  <>
                    <div className="project-stat">
                      <div className="project-stat__value project-stat__value--success">{project.tablesAnalyzed}</div>
                      <div className="project-stat__label">Tables</div>
                    </div>
                    <div className="project-stat">
                      <div className="project-stat__value">{project.findings.total}</div>
                      <div className="project-stat__label">Findings</div>
                    </div>
                    <div className="project-stat">
                      <div className="project-stat__value">{project.progress}%</div>
                      <div className="project-stat__label">Progress</div>
                    </div>
                  </>
                ) : project.findings.total > 0 ? (
                  <>
                    <div className="project-stat">
                      <div className={`project-stat__value ${project.findings.critical > 0 ? 'project-stat__value--critical' : 'project-stat__value--warning'}`}>
                        {project.findings.critical + project.findings.warning}
                      </div>
                      <div className="project-stat__label">Pending</div>
                    </div>
                    <div className="project-stat">
                      <div className="project-stat__value project-stat__value--success">
                        {Math.round(project.findings.total * project.progress / 100)}
                      </div>
                      <div className="project-stat__label">Approved</div>
                    </div>
                    <div className="project-stat">
                      <div className="project-stat__value">{project.progress}%</div>
                      <div className="project-stat__label">Progress</div>
                    </div>
                  </>
                ) : (
                  <div className="project-stat" style={{ flex: 1, textAlign: 'center' }}>
                    <div className="project-stat__label" style={{ color: 'var(--text-muted)' }}>{project.type}</div>
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

export default Dashboard;
