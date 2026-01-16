/**
 * ProjectsPage.jsx - Projects List
 * 
 * WIRED TO REAL API - Fetches projects from /api/projects/list
 * Displays real projects + demo stats where available.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Loader2 } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Generate a consistent color based on string (customer name)
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

const ProjectsPage = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/list`);
      if (!res.ok) throw new Error('Failed to fetch projects');
      const data = await res.json();
      
      // Process projects with demo stats
      const processed = data.map(p => {
        const demoStats = parseDemoStats(p.notes);
        return {
          ...p,
          initials: getInitials(p.customer || p.name),
          demoStats,
          findings: demoStats?.findings || { critical: 0, warning: 0, info: 0, total: 0 },
          progress: demoStats?.progress || 0,
        };
      });
      
      setProjects(processed);
    } catch (err) {
      console.error('Failed to load projects:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filteredProjects = projects.filter(project => 
    (project.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (project.customer || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleProjectClick = (project) => {
    navigate(`/projects/${project.id}/hub`);
  };

  if (loading) {
    return (
      <div className="page-loading">
        <Loader2 size={24} className="spin" />
        <p>Loading projects...</p>
      </div>
    );
  }

  return (
    <div className="projects-page">
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title">Projects</h1>
          <p className="page-subtitle">{projects.length} total projects</p>
        </div>
        <button className="btn btn-primary btn-lg" onClick={() => navigate('/projects/new')}>
          <Plus size={18} />
          New Project
        </button>
      </div>

      {error && (
        <div className="alert alert--error mb-4">
          {error}
        </div>
      )}

      <div className="card mb-6">
        <div className="card-body" style={{ padding: 'var(--space-3)' }}>
          <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
            <Search size={18} />
            <input
              type="text"
              className="form-input"
              placeholder="Search projects by name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ border: 'none', padding: 0, background: 'transparent' }}
            />
          </div>
        </div>
      </div>

      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Project</th>
              <th>Systems</th>
              <th>Type</th>
              <th>Go-Live / End</th>
              <th>Findings</th>
              <th>Progress</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredProjects.map(project => (
              <tr 
                key={project.id} 
                onClick={() => handleProjectClick(project)}
                style={{ cursor: 'pointer' }}
              >
                <td>
                  <div className="flex items-center gap-3">
                    <div 
                      className="project-card__avatar" 
                      style={{ 
                        width: '32px', 
                        height: '32px', 
                        fontSize: 'var(--text-sm)',
                        background: getCustomerColor(project.customer || project.name),
                        flexShrink: 0
                      }}
                    >
                      {project.initials}
                    </div>
                    <span style={{ fontWeight: 'var(--weight-semibold)', marginLeft: '4px' }}>
                      {project.customer || project.name}
                    </span>
                  </div>
                </td>
                <td>
                  {(project.systems || []).map(s => s.replace(/-/g, ' ')).join(', ') || project.product || '-'}
                </td>
                <td>{project.engagement_type || project.type || '-'}</td>
                <td>{project.target_go_live || '-'}</td>
                <td>
                  <div className="flex items-center gap-2">
                    {project.findings.critical > 0 && (
                      <span className="badge badge--critical">{project.findings.critical}</span>
                    )}
                    {project.findings.warning > 0 && (
                      <span className="badge badge--warning">{project.findings.warning}</span>
                    )}
                    {project.findings.total > 0 && (
                      <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
                        {project.findings.total} total
                      </span>
                    )}
                    {project.findings.total === 0 && (
                      <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>-</span>
                    )}
                  </div>
                </td>
                <td>
                  {project.progress > 0 ? (
                    <div className="flex items-center gap-2">
                      <div className="progress-bar" style={{ width: '80px' }}>
                        <div className="progress-bar__fill" style={{ width: `${project.progress}%` }} />
                      </div>
                      <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
                        {project.progress}%
                      </span>
                    </div>
                  ) : (
                    <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>-</span>
                  )}
                </td>
                <td>
                  <span className={`badge badge--${project.status === 'completed' ? 'success' : 'info'}`}>
                    {project.status === 'completed' ? 'Completed' : 'Active'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredProjects.length === 0 && !loading && (
        <div className="card mt-4">
          <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
            <p className="text-muted">
              {searchTerm ? `No projects found matching "${searchTerm}"` : 'No projects yet. Create your first project!'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectsPage;
