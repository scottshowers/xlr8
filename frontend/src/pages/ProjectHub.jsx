/**
 * ProjectHub.jsx - Project Workspace
 * 
 * WIRED TO REAL API - Fetches from /api/projects/list to get full metadata
 * Displays real project stats OR demo stats.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { 
  Upload, BookOpen, Play, Search, Download, MessageSquare,
  Users, MapPin, DollarSign, Building2, Loader2, Settings,
  Database, Columns, Layers
} from 'lucide-react';

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

export default function ProjectHub() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { selectProject } = useProject();
  
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchProject();
  }, [id]);

  const fetchProject = async () => {
    try {
      // Fetch from /list to get full metadata (single project endpoint doesn't include it)
      const res = await fetch(`${API_BASE}/api/projects/list`);
      if (!res.ok) throw new Error('Failed to fetch projects');
      const projects = await res.json();
      
      const found = projects.find(p => p.id === id);
      if (!found) throw new Error('Project not found');
      
      // Parse demo stats OR use real metadata
      const demoStats = parseDemoStats(found.notes);
      const metadata = found.metadata || {};
      const detectedDomains = metadata.detected_domains || {};
      
      // Build snapshot from real data if available
      let snapshot = null;
      if (demoStats) {
        snapshot = {
          employees: demoStats.employees,
          locations: demoStats.locations,
          annualPayroll: demoStats.annual_payroll,
          departments: demoStats.departments,
        };
      } else if (detectedDomains.tables_analyzed) {
        // Use real analysis data
        snapshot = {
          tables: detectedDomains.tables_analyzed,
          columns: detectedDomains.columns_analyzed,
          primaryDomain: detectedDomains.primary_domain,
          domains: (detectedDomains.domains || []).slice(0, 4),
        };
      }
      
      const processed = {
        ...found,
        demoStats,
        snapshot,
        findings: demoStats?.findings || { total: 0, critical: 0, warning: 0, info: 0 },
        progress: demoStats?.progress || 0,
        hasRealData: !!detectedDomains.tables_analyzed,
      };
      
      setProject(processed);
      selectProject(processed);
    } catch (err) {
      console.error('Failed to load project:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-loading">
        <Loader2 size={24} className="spin" />
        <p>Loading project...</p>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="card">
        <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
          <h2>Project Not Found</h2>
          <p className="text-muted mt-2">{error || 'The requested project could not be found.'}</p>
          <button className="btn btn-primary mt-4" onClick={() => navigate('/projects')}>
            Back to Projects
          </button>
        </div>
      </div>
    );
  }

  const customerColor = getCustomerColor(project.customer || project.name);
  const systemNames = (project.systems || []).map(s => s.replace(/_/g, ' ').replace(/-/g, ' ')).join(', ') || project.product || 'Unknown';

  return (
    <div className="project-hub-page">
      {/* Hub Header */}
      <div className="hub-header">
        <div className="hub-header__left">
          <div className="hub-avatar" style={{ background: customerColor }}>
            {getInitials(project.customer || project.name)}
          </div>
          <div>
            <h1 className="hub-title">{project.customer || project.name}</h1>
            <div className="hub-meta">
              <span>{systemNames}</span>
              <span>-</span>
              <span>{project.engagement_type || project.type || 'Engagement'}</span>
              {project.target_go_live && (
                <>
                  <span>-</span>
                  <span>Target: {project.target_go_live}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="hub-actions">
          <button className="btn btn-secondary" onClick={() => navigate(`/projects/${id}/edit`)}>
            <Settings size={16} />
            Edit
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/workspace')}>
            <MessageSquare size={16} />
            Ask AI
          </button>
          <button className="btn btn-primary" onClick={() => navigate('/findings')}>
            Continue to Findings
          </button>
        </div>
      </div>

      {/* Customer Snapshot - Demo Data */}
      {project.snapshot && !project.hasRealData && (
        <div className="card mb-6" style={{ borderLeft: `4px solid ${customerColor}` }}>
          <div className="card-body">
            <div className="flex items-center gap-6" style={{ flexWrap: 'wrap' }}>
              <div className="flex items-center gap-2">
                <Users size={18} style={{ color: customerColor }} />
                <div>
                  <div style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--weight-bold)' }}>{project.snapshot.employees}</div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Employees</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <MapPin size={18} style={{ color: customerColor }} />
                <div>
                  <div style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--weight-bold)' }}>{project.snapshot.locations}</div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Locations</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <DollarSign size={18} style={{ color: customerColor }} />
                <div>
                  <div style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--weight-bold)' }}>{project.snapshot.annualPayroll}</div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Annual Payroll</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Building2 size={18} style={{ color: customerColor }} />
                <div>
                  <div style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--weight-bold)' }}>{project.snapshot.departments}</div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Departments</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Data Analysis Snapshot - Real Data */}
      {project.hasRealData && project.snapshot && (
        <div className="card mb-6" style={{ borderLeft: `4px solid ${customerColor}` }}>
          <div className="card-header">
            <h3 className="card-title">Data Analysis Summary</h3>
            <span className="badge badge--success">Analyzed</span>
          </div>
          <div className="card-body">
            <div className="flex items-center gap-8" style={{ flexWrap: 'wrap' }}>
              <div className="flex items-center gap-2">
                <Database size={18} style={{ color: customerColor }} />
                <div>
                  <div style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--weight-bold)' }}>{project.snapshot.tables}</div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Tables</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Columns size={18} style={{ color: customerColor }} />
                <div>
                  <div style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--weight-bold)' }}>{project.snapshot.columns}</div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Columns</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Layers size={18} style={{ color: customerColor }} />
                <div>
                  <div style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--weight-bold)', textTransform: 'capitalize' }}>{project.snapshot.primaryDomain}</div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Primary Domain</div>
                </div>
              </div>
            </div>
            
            {/* Detected Domains */}
            {project.snapshot.domains && project.snapshot.domains.length > 0 && (
              <div className="mt-4">
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-2)' }}>
                  Detected Domains
                </div>
                <div className="flex gap-2 flex-wrap">
                  {project.snapshot.domains.map(d => (
                    <div key={d.domain} className="flex items-center gap-2 px-3 py-1" style={{ background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', fontSize: 'var(--text-sm)' }}>
                      <span style={{ textTransform: 'capitalize', fontWeight: 'var(--weight-medium)' }}>{d.domain}</span>
                      <span style={{ color: 'var(--text-muted)' }}>{Math.round(d.confidence * 100)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Hub Grid */}
      <div className="hub-grid">
        <div className="hub-main">
          {/* Quick Actions */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Quick Actions</h3>
            </div>
            <div className="card-body">
              <div className="quick-actions">
                <div className="quick-action" onClick={() => navigate('/upload')}>
                  <Upload size={24} />
                  <span className="quick-action__label">Upload Data</span>
                </div>
                <div className="quick-action" onClick={() => navigate('/playbooks/select')}>
                  <BookOpen size={24} />
                  <span className="quick-action__label">Select Playbooks</span>
                </div>
                <div className="quick-action" onClick={() => navigate('/processing')}>
                  <Play size={24} />
                  <span className="quick-action__label">Run Analysis</span>
                </div>
                <div className="quick-action" onClick={() => navigate('/findings')}>
                  <Search size={24} />
                  <span className="quick-action__label">View Findings</span>
                </div>
                <div className="quick-action" onClick={() => navigate('/export')}>
                  <Download size={24} />
                  <span className="quick-action__label">Export Report</span>
                </div>
                <div className="quick-action" onClick={() => navigate('/workspace')}>
                  <MessageSquare size={24} />
                  <span className="quick-action__label">Ask AI</span>
                </div>
              </div>
            </div>
          </div>

          {/* Findings Summary */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Findings Summary</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => navigate('/findings')}>
                View All
              </button>
            </div>
            <div className="card-body">
              <div className="findings-summary">
                <div className="finding-stat">
                  <div className="finding-stat__value">{project.findings.total}</div>
                  <div className="finding-stat__label">Total</div>
                </div>
                <div className="finding-stat">
                  <div className="finding-stat__value finding-stat__value--critical">{project.findings.critical}</div>
                  <div className="finding-stat__label">Critical</div>
                </div>
                <div className="finding-stat">
                  <div className="finding-stat__value finding-stat__value--warning">{project.findings.warning}</div>
                  <div className="finding-stat__label">Warning</div>
                </div>
                <div className="finding-stat">
                  <div className="finding-stat__value finding-stat__value--info">{project.findings.info}</div>
                  <div className="finding-stat__label">Info</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="hub-sidebar">
          {/* Review Progress */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Review Progress</h3>
            </div>
            <div className="card-body">
              <div className="mb-4">
                <div className="flex justify-between items-center mb-2">
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                    {Math.round(project.findings.total * project.progress / 100)} of {project.findings.total} reviewed
                  </span>
                  <span style={{ fontWeight: 'var(--weight-semibold)', color: 'var(--grass-green)' }}>
                    {project.progress}%
                  </span>
                </div>
                <div className="progress-bar">
                  <div className="progress-bar__fill" style={{ width: `${project.progress}%` }} />
                </div>
              </div>
            </div>
          </div>

          {/* Project Details */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Project Details</h3>
            </div>
            <div className="card-body">
              <div className="flex flex-col gap-3" style={{ fontSize: 'var(--text-sm)' }}>
                {project.lead_name && (
                  <div className="flex justify-between">
                    <span className="text-muted">Lead</span>
                    <span>{project.lead_name}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted">Domains</span>
                  <span>{(project.domains || []).join(', ') || '-'}</span>
                </div>
                {project.playbooks && project.playbooks.length > 0 && (
                  <div className="flex justify-between">
                    <span className="text-muted">Playbooks</span>
                    <span>{project.playbooks.length} assigned</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted">Status</span>
                  <span className={`badge badge--${project.status === 'completed' ? 'success' : 'info'}`}>
                    {project.status || 'Active'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Functional Areas */}
          {project.functional_areas && project.functional_areas.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Functional Areas</h3>
              </div>
              <div className="card-body">
                <div className="flex flex-wrap gap-2">
                  {project.functional_areas.slice(0, 8).map((fa, idx) => (
                    <span key={idx} className="badge" style={{ textTransform: 'capitalize' }}>
                      {fa.area?.replace(/_/g, ' ')}
                    </span>
                  ))}
                  {project.functional_areas.length > 8 && (
                    <span className="text-muted" style={{ fontSize: 'var(--text-sm)' }}>
                      +{project.functional_areas.length - 8} more
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
