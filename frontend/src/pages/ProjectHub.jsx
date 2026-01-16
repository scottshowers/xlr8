/**
 * ProjectHub.jsx - Project Workspace
 * ===================================
 * 
 * Dedicated hub for a specific project showing:
 * - Project header with details
 * - Quick actions grid
 * - Findings summary
 * - Progress and assigned playbooks
 * 
 * Flow bar is shown via MainLayout (showFlowBar prop from App.jsx)
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { 
  Upload, 
  BookOpen, 
  Play, 
  Search, 
  Download,
  MessageSquare
} from 'lucide-react';

export default function ProjectHub() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { projects, selectProject } = useProject();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [findings, setFindings] = useState({ total: 0, critical: 0, warning: 0, info: 0 });
  const [progress, setProgress] = useState({ reviewed: 0, total: 0, percent: 0 });
  const [playbooks, setPlaybooks] = useState([]);
  const [dataFiles, setDataFiles] = useState({ count: 0, lastUpload: null });

  useEffect(() => {
    const found = projects?.find(p => String(p.id) === String(id));
    if (found) {
      setProject(found);
      selectProject(found);
      // Load project-specific data
      loadProjectData(found);
    } else {
      // Mock project for demo
      const mockProject = {
        id: id,
        name: 'Acme Corp',
        customer: 'Acme Corporation',
        vendor: 'UKG',
        system_type: 'Pro',
        engagement_type: 'Implementation',
        go_live: 'March 15, 2026'
      };
      setProject(mockProject);
      loadProjectData(mockProject);
    }
    setLoading(false);
  }, [id, projects, selectProject]);

  const loadProjectData = (proj) => {
    // TODO: Replace with actual API calls
    setFindings({ total: 32, critical: 8, warning: 12, info: 12 });
    setProgress({ reviewed: 24, total: 32, percent: 75 });
    setPlaybooks([
      { id: 'pb1', name: 'Year-End Readiness' },
      { id: 'pb2', name: 'Data Quality Assessment' }
    ]);
    setDataFiles({ count: 12, lastUpload: 'Jan 14, 2026' });
  };

  const getInitials = (name) => {
    if (!name) return 'P';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  };

  if (loading) {
    return (
      <div className="page-loading">
        <p>Loading project...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="card">
        <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
          <h2>Project Not Found</h2>
          <p className="text-muted mt-2">The requested project could not be found.</p>
          <button className="btn btn-primary mt-4" onClick={() => navigate('/projects')}>
            Back to Projects
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="project-hub-page">
      {/* Hub Header */}
      <div className="hub-header">
        <div className="hub-header__left">
          <div className="hub-avatar">
            {getInitials(project.customer || project.name)}
          </div>
          <div>
            <h1 className="hub-title">{project.customer || project.name}</h1>
            <div className="hub-meta">
              <span>{project.vendor || 'UKG'}</span>
              <span>-</span>
              <span>{project.system_type || 'Pro'}</span>
              <span>-</span>
              <span>{project.engagement_type || 'Implementation'}</span>
              {project.go_live && (
                <>
                  <span>-</span>
                  <span>Go-live: {project.go_live}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="hub-actions">
          <button className="btn btn-secondary" onClick={() => navigate('/workspace')}>
            <MessageSquare size={16} />
            Ask AI
          </button>
          <button className="btn btn-primary" onClick={() => navigate('/findings')}>
            Continue to Findings
          </button>
        </div>
      </div>

      {/* Hub Grid */}
      <div className="hub-grid">
        {/* Main Column */}
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
                  <div className="finding-stat__value">{findings.total}</div>
                  <div className="finding-stat__label">Total</div>
                </div>
                <div className="finding-stat">
                  <div className="finding-stat__value finding-stat__value--critical">{findings.critical}</div>
                  <div className="finding-stat__label">Critical</div>
                </div>
                <div className="finding-stat">
                  <div className="finding-stat__value finding-stat__value--warning">{findings.warning}</div>
                  <div className="finding-stat__label">Warning</div>
                </div>
                <div className="finding-stat">
                  <div className="finding-stat__value finding-stat__value--info">{findings.info}</div>
                  <div className="finding-stat__label">Info</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Column */}
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
                    {progress.reviewed} of {progress.total} reviewed
                  </span>
                  <span style={{ fontWeight: 'var(--weight-semibold)', color: 'var(--grass-green)' }}>
                    {progress.percent}%
                  </span>
                </div>
                <div className="progress-bar">
                  <div className="progress-bar__fill" style={{ width: `${progress.percent}%` }} />
                </div>
              </div>
              <div className="flex gap-4" style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                <span><strong style={{ color: 'var(--grass-green)' }}>{progress.reviewed}</strong> Approved</span>
                <span><strong style={{ color: 'var(--critical)' }}>{progress.total - progress.reviewed}</strong> Pending</span>
              </div>
            </div>
          </div>

          {/* Assigned Playbooks */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Assigned Playbooks</h3>
            </div>
            <div className="card-body">
              <div className="flex flex-col gap-2">
                {playbooks.map(pb => (
                  <div 
                    key={pb.id}
                    className="flex items-center gap-2"
                    style={{ 
                      padding: 'var(--space-2) var(--space-3)', 
                      background: 'var(--bg-tertiary)', 
                      borderRadius: 'var(--radius-md)',
                      fontSize: 'var(--text-sm)'
                    }}
                  >
                    <BookOpen size={16} style={{ color: 'var(--grass-green)' }} />
                    {pb.name}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Uploaded Data */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Uploaded Data</h3>
            </div>
            <div className="card-body">
              <div className="flex items-center gap-3 mb-4">
                <Upload size={24} style={{ color: 'var(--grass-green)' }} />
                <div>
                  <div style={{ fontWeight: 'var(--weight-semibold)' }}>{dataFiles.count} files</div>
                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                    Last upload: {dataFiles.lastUpload}
                  </div>
                </div>
              </div>
              <button 
                className="btn btn-secondary" 
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => navigate('/upload')}
              >
                View Data
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
