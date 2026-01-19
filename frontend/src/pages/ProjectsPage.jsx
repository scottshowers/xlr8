/**
 * ProjectsPage.jsx - Projects List
 * 
 * WIRED TO REAL API - Fetches projects from /api/customers/list
 * Shows Start Date and Projected End as separate columns.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Loader2 } from 'lucide-react';

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

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch { return dateStr; }
};

const ProjectsPage = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => { fetchProjects(); }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/customers/list`);
      if (!res.ok) throw new Error('Failed to fetch projects');
      const data = await res.json();
      
      const processed = data.map(p => {
        const demoStats = parseDemoStats(p.notes);
        const metadata = p.metadata || {};
        const detectedDomains = metadata.detected_domains || {};
        
        return {
          ...p,
          initials: getInitials(p.customer || p.name),
          demoStats,
          findings: demoStats?.findings || { critical: 0, warning: 0, info: 0, total: 0 },
          progress: demoStats?.progress || 0,
          tablesAnalyzed: detectedDomains.tables_analyzed || 0,
          hasRealData: !!detectedDomains.tables_analyzed,
        };
      });
      
      setProjects(processed);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filteredProjects = projects.filter(project => 
    (project.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (project.customer || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return <div className="page-loading"><Loader2 size={24} className="spin" /><p>Loading projects...</p></div>;
  }

  return (
    <div className="projects-page">
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title">Customers</h1>
          <p className="page-subtitle">{projects.length} total customers</p>
        </div>
        <button className="btn btn-primary btn-lg" onClick={() => navigate('/customers/new')}>
          <Plus size={18} />
          New Customer
        </button>
      </div>

      {error && <div className="alert alert--error mb-4">{error}</div>}

      <div className="card mb-6">
        <div className="card-body" style={{ padding: 'var(--space-3)' }}>
          <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
            <Search size={18} />
            <input
              type="text"
              className="form-input"
              placeholder="Search customers..."
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
              <th>Customer</th>
              <th>Systems</th>
              <th>Type</th>
              <th>Start</th>
              <th>End</th>
              <th>Data / Findings</th>
              <th>Progress</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredProjects.map(project => (
              <tr key={project.id} onClick={() => navigate(`/customers/${project.id}/hub`)} style={{ cursor: 'pointer' }}>
                <td>
                  <div className="flex items-center">
                    <div className="project-card__avatar" style={{ width: '32px', height: '32px', fontSize: 'var(--text-sm)', background: getCustomerColor(project.customer || project.name), flexShrink: 0 }}>
                      {project.initials}
                    </div>
                    <span style={{ fontWeight: 'var(--weight-semibold)', marginLeft: '16px' }}>{project.customer || project.name}</span>
                  </div>
                </td>
                <td>{(project.systems || []).map(s => s.replace(/_/g, ' ').replace(/-/g, ' ')).join(', ') || project.product || '-'}</td>
                <td>{project.engagement_type || project.type || '-'}</td>
                <td>{formatDate(project.start_date)}</td>
                <td>{formatDate(project.target_go_live)}</td>
                <td>
                  {project.hasRealData ? (
                    <span style={{ color: 'var(--grass-green)', fontWeight: 'var(--weight-medium)' }}>
                      {project.tablesAnalyzed} tables
                    </span>
                  ) : project.findings.total > 0 ? (
                    <div className="flex items-center gap-2">
                      {project.findings.critical > 0 && <span className="badge badge--critical">{project.findings.critical}</span>}
                      {project.findings.warning > 0 && <span className="badge badge--warning">{project.findings.warning}</span>}
                      <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>{project.findings.total} total</span>
                    </div>
                  ) : (
                    <span className="text-muted">-</span>
                  )}
                </td>
                <td>
                  {project.progress > 0 ? (
                    <div className="flex items-center gap-2">
                      <div className="progress-bar" style={{ width: '60px' }}>
                        <div className="progress-bar__fill" style={{ width: `${project.progress}%` }} />
                      </div>
                      <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>{project.progress}%</span>
                    </div>
                  ) : project.hasRealData ? (
                    <span className="badge badge--success">Analyzed</span>
                  ) : (
                    <span className="text-muted">-</span>
                  )}
                </td>
                <td>
                  <span className={`badge badge--${project.status === 'completed' ? 'success' : 'info'}`}>
                    {project.status || 'Active'}
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
            <p className="text-muted">{searchTerm ? `No customers found matching "${searchTerm}"` : 'No customers yet.'}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectsPage;
