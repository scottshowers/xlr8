/**
 * MissionControl.jsx - Dashboard / Home
 * ======================================
 * 
 * Overview dashboard for consultants showing:
 * - High-level stats across all projects
 * - Items needing attention (projects with critical findings, approaching deadlines)
 * - Recent projects for quick access
 * 
 * This is INFORMATIONAL only - actual work happens in Project Hub.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const MissionControl = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    activeProjects: 0,
    pendingFindings: 0,
    approvedThisWeek: 0,
    upcomingGoLives: 0
  });
  const [attentionItems, setAttentionItems] = useState([]);
  const [recentProjects, setRecentProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // TODO: Replace with actual API calls
      setStats({
        activeProjects: 7,
        pendingFindings: 23,
        approvedThisWeek: 47,
        upcomingGoLives: 2
      });

      setAttentionItems([
        {
          id: 'a1',
          type: 'critical',
          title: 'Acme Corp - 8 critical findings awaiting review',
          meta: 'Year-End Playbook - Go-live: March 15, 2026',
          projectId: 'proj-acme'
        },
        {
          id: 'a2',
          type: 'warning',
          title: 'TechStart Inc - Analysis complete, 12 findings ready',
          meta: 'Data Quality Assessment - Started: Jan 10, 2026',
          projectId: 'proj-techstart'
        },
        {
          id: 'a3',
          type: 'critical',
          title: 'Global Retail Co - Go-live in 15 days, 5 items pending',
          meta: 'Year-End Playbook - Due: Jan 31, 2026',
          projectId: 'proj-global'
        }
      ]);

      setRecentProjects([
        {
          id: 'proj-acme',
          name: 'Acme Corp',
          initials: 'AC',
          system: 'UKG Pro',
          type: 'Implementation',
          pending: 8,
          approved: 24,
          total: 32
        },
        {
          id: 'proj-techstart',
          name: 'TechStart Inc',
          initials: 'TS',
          system: 'Workday',
          type: 'Migration',
          pending: 12,
          approved: 14,
          total: 26
        },
        {
          id: 'proj-global',
          name: 'Global Retail Co',
          initials: 'GR',
          system: 'UKG Pro',
          type: 'Year-End',
          pending: 5,
          approved: 22,
          total: 27
        }
      ]);

      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setLoading(false);
    }
  };

  const handleAttentionClick = (item) => {
    navigate(`/projects/${item.projectId}/hub`);
  };

  const handleProjectClick = (project) => {
    navigate(`/projects/${project.id}/hub`);
  };

  if (loading) {
    return (
      <div className="page-loading">
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="mission-control">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Mission Control</h1>
        <p className="page-subtitle">Overview of your active projects and items needing attention</p>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Active Projects</div>
          <div className="stat-value">{stats.activeProjects}</div>
          <div className="stat-detail">3 in implementation phase</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Findings Pending Review</div>
          <div className="stat-value stat-value--critical">{stats.pendingFindings}</div>
          <div className="stat-detail">8 critical, 15 warning</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Approved This Week</div>
          <div className="stat-value stat-value--success">{stats.approvedThisWeek}</div>
          <div className="stat-detail">+12% from last week</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Upcoming Go-Lives</div>
          <div className="stat-value stat-value--warning">{stats.upcomingGoLives}</div>
          <div className="stat-detail">Within 30 days</div>
        </div>
      </div>

      {/* Needs Attention */}
      <div className="section-header">
        <h2 className="section-title">Needs Attention</h2>
        <button className="btn btn-secondary" onClick={() => navigate('/findings')}>
          View All Findings
        </button>
      </div>

      <div className="attention-list">
        {attentionItems.map(item => (
          <div 
            key={item.id} 
            className="attention-item"
            onClick={() => handleAttentionClick(item)}
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

      {/* Recent Projects */}
      <div className="section-header">
        <h2 className="section-title">Recent Projects</h2>
        <button className="btn btn-secondary" onClick={() => navigate('/projects')}>
          View All Projects
        </button>
      </div>

      <div className="projects-grid">
        {recentProjects.map(project => (
          <div 
            key={project.id} 
            className="project-card"
            onClick={() => handleProjectClick(project)}
          >
            <div className="project-card__header">
              <div className="project-card__avatar">{project.initials}</div>
              <div>
                <div className="project-card__name">{project.name}</div>
                <div className="project-card__system">{project.system} - {project.type}</div>
              </div>
            </div>
            <div className="project-card__stats">
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
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MissionControl;
