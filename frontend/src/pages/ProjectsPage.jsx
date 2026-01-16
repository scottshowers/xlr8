/**
 * ProjectsPage.jsx - Projects List
 * =================================
 * 
 * Full list of all projects with:
 * - Search/filter
 * - Status indicators
 * - Quick stats per project
 * - New Project button
 * - Unique customer colors
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';

// Generate a consistent color based on string (customer name)
// Uses HCMPACT brand palette
const getCustomerColor = (name) => {
  const colors = [
    '#83b16d', // grass green (primary)
    '#2766b1', // electric blue
    '#285390', // accent (deep blue)
    '#5f4282', // purple
    '#993c44', // scarlet
    '#d97706', // amber
    '#93abd9', // sky blue
    '#a1c3d4', // aquamarine
    '#b2d6de', // clearwater
    '#6b9b5a', // grass green dark
  ];
  
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
};

const ProjectsPage = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      // TODO: Replace with actual API call
      setProjects([
        {
          id: 'proj-acme',
          name: 'Acme Corp',
          initials: 'AC',
          system: 'UKG Pro',
          type: 'Implementation',
          status: 'active',
          goLive: 'March 15, 2026',
          findings: { critical: 8, warning: 12, info: 12, total: 32 },
          progress: 75
        },
        {
          id: 'proj-techstart',
          name: 'TechStart Inc',
          initials: 'TS',
          system: 'Workday',
          type: 'Data Migration',
          status: 'active',
          goLive: 'February 28, 2026',
          findings: { critical: 5, warning: 7, info: 14, total: 26 },
          progress: 54
        },
        {
          id: 'proj-global',
          name: 'Global Retail Co',
          initials: 'GR',
          system: 'UKG Pro',
          type: 'Year-End',
          status: 'active',
          goLive: 'January 31, 2026',
          findings: { critical: 2, warning: 3, info: 22, total: 27 },
          progress: 81
        },
        {
          id: 'proj-metro',
          name: 'Metro Health',
          initials: 'MH',
          system: 'Workday',
          type: 'Implementation',
          status: 'active',
          goLive: 'April 1, 2026',
          findings: { critical: 0, warning: 4, info: 8, total: 12 },
          progress: 38
        },
        {
          id: 'proj-first',
          name: 'First National Bank',
          initials: 'FN',
          system: 'UKG Pro',
          type: 'Optimization',
          status: 'completed',
          goLive: 'December 15, 2025',
          findings: { critical: 0, warning: 0, info: 5, total: 45 },
          progress: 100
        }
      ]);
      
      setLoading(false);
    } catch (error) {
      console.error('Error fetching projects:', error);
      setLoading(false);
    }
  };

  const filteredProjects = projects.filter(project => 
    project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    project.system.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleProjectClick = (project) => {
    navigate(`/projects/${project.id}/hub`);
  };

  if (loading) {
    return (
      <div className="page-loading">
        <p>Loading projects...</p>
      </div>
    );
  }

  return (
    <div className="projects-page">
      {/* Page Header */}
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

      {/* Search */}
      <div className="card mb-6">
        <div className="card-body" style={{ padding: 'var(--space-3)' }}>
          <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
            <Search size={18} />
            <input
              type="text"
              className="form-input"
              placeholder="Search projects by name or system..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ border: 'none', padding: 0, background: 'transparent' }}
            />
          </div>
        </div>
      </div>

      {/* Projects Table */}
      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Project</th>
              <th>System</th>
              <th>Type</th>
              <th>Go-Live</th>
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
                        background: getCustomerColor(project.name)
                      }}
                    >
                      {project.initials}
                    </div>
                    <span style={{ fontWeight: 'var(--weight-semibold)' }}>{project.name}</span>
                  </div>
                </td>
                <td>{project.system}</td>
                <td>{project.type}</td>
                <td>{project.goLive}</td>
                <td>
                  <div className="flex items-center gap-2">
                    {project.findings.critical > 0 && (
                      <span className="badge badge--critical">{project.findings.critical}</span>
                    )}
                    {project.findings.warning > 0 && (
                      <span className="badge badge--warning">{project.findings.warning}</span>
                    )}
                    <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
                      {project.findings.total} total
                    </span>
                  </div>
                </td>
                <td>
                  <div className="flex items-center gap-2">
                    <div className="progress-bar" style={{ width: '80px' }}>
                      <div 
                        className="progress-bar__fill" 
                        style={{ width: `${project.progress}%` }}
                      />
                    </div>
                    <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
                      {project.progress}%
                    </span>
                  </div>
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

      {filteredProjects.length === 0 && (
        <div className="card mt-4">
          <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
            <p className="text-muted">No projects found matching "{searchTerm}"</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectsPage;
