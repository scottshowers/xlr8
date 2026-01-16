/**
 * ProjectHub.jsx - Project Workspace
 * ===================================
 * 
 * Dedicated hub for a specific project showing:
 * - Flow progress (where are we in the 8 steps)
 * - Project details (vendor, product, playbooks)
 * - Quick actions to continue workflow
 * - Findings summary
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { 
  ArrowRight, 
  Upload, 
  BookOpen, 
  Play, 
  Search, 
  FileCheck, 
  Download,
  MessageSquare,
  CheckCircle,
  Building,
  Package,
  Calendar,
  Users,
  ChevronRight
} from 'lucide-react';

// Flow steps configuration
const FLOW_STEPS = [
  { num: 1, label: 'Create', path: '/projects/new', key: 'created' },
  { num: 2, label: 'Upload', path: '/upload', key: 'has_data' },
  { num: 3, label: 'Playbooks', path: '/playbooks/select', key: 'has_playbooks' },
  { num: 4, label: 'Analysis', path: '/processing', key: 'analyzed' },
  { num: 5, label: 'Findings', path: '/findings', key: 'has_findings' },
  { num: 6, label: 'Review', path: '/findings', key: 'reviewed' },
  { num: 7, label: 'Progress', path: '/progress', key: 'tracking' },
  { num: 8, label: 'Export', path: '/export', key: 'exported' },
];

export default function ProjectHub() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { projects, selectProject, activeProject } = useProject();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const found = projects?.find(p => String(p.id) === String(id));
    if (found) {
      setProject(found);
      selectProject(found);
    }
    setLoading(false);
  }, [id, projects, selectProject]);

  // Determine current step based on project state
  const getCurrentStep = () => {
    if (!project) return 1;
    if (project.exported) return 8;
    if (project.has_findings) return 5;
    if (project.analyzed) return 4;
    if (project.has_playbooks) return 3;
    if (project.has_data) return 2;
    return 2; // Default to Upload step for existing projects
  };

  const currentStep = getCurrentStep();

  // Mock stats - TODO: Get from API
  const stats = {
    findings: { total: 12, critical: 3, warning: 5, info: 4 },
    progress: { approved: 8, pending: 4 },
    files: project?.file_count || 0,
  };

  if (loading) {
    return (
      <div className="project-hub">
        <div className="project-hub__loading">
          <div className="spinner" />
          <p>Loading project...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="project-hub">
        <div className="project-hub__not-found">
          <div className="project-hub__not-found-icon">📁</div>
          <h2>Project Not Found</h2>
          <p>The project you're looking for doesn't exist or has been deleted.</p>
          <button 
            className="xlr8-btn xlr8-btn--primary"
            onClick={() => navigate('/projects')}
          >
            Back to Projects
          </button>
        </div>
      </div>
    );
  }

  const nextAction = FLOW_STEPS[currentStep] || FLOW_STEPS[1];

  return (
    <div className="project-hub">
      {/* Project Header */}
      <div className="project-hub__header">
        <div className="project-hub__header-left">
          <div className="project-hub__avatar">
            {(project.customer || project.name || 'P').substring(0, 2).toUpperCase()}
          </div>
          <div className="project-hub__header-info">
            <h1 className="project-hub__title">{project.customer || project.name}</h1>
            <div className="project-hub__meta">
              <span className="project-hub__meta-item">
                <Building size={14} />
                {project.vendor || 'UKG'}
              </span>
              <span className="project-hub__meta-item">
                <Package size={14} />
                {project.system_type || 'Pro'}
              </span>
              <span className="project-hub__meta-item">
                <Calendar size={14} />
                {project.engagement_type || 'Implementation'}
              </span>
              {project.project_lead && (
                <span className="project-hub__meta-item">
                  <Users size={14} />
                  {project.project_lead}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="project-hub__header-actions">
          <button 
            className="xlr8-btn xlr8-btn--secondary"
            onClick={() => navigate('/workspace')}
          >
            <MessageSquare size={16} />
            Chat
          </button>
          <button 
            className="xlr8-btn xlr8-btn--primary"
            onClick={() => navigate(nextAction.path)}
          >
            Continue to {nextAction.label}
            <ArrowRight size={16} />
          </button>
        </div>
      </div>

      {/* Flow Progress Bar */}
      <div className="project-hub__flow">
        <div className="project-hub__flow-steps">
          {FLOW_STEPS.map((step, index) => {
            const isComplete = step.num < currentStep;
            const isCurrent = step.num === currentStep;
            const isPending = step.num > currentStep;

            return (
              <React.Fragment key={step.num}>
                <div 
                  className={`project-hub__step ${isComplete ? 'project-hub__step--complete' : ''} ${isCurrent ? 'project-hub__step--current' : ''} ${isPending ? 'project-hub__step--pending' : ''}`}
                  onClick={() => navigate(step.path)}
                >
                  <div className="project-hub__step-indicator">
                    {isComplete ? <CheckCircle size={18} /> : step.num}
                  </div>
                  <span className="project-hub__step-label">{step.label}</span>
                </div>
                {index < FLOW_STEPS.length - 1 && (
                  <div className={`project-hub__step-connector ${isComplete ? 'project-hub__step-connector--complete' : ''}`} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="project-hub__grid">
        {/* Quick Actions Card */}
        <div className="project-hub__card project-hub__card--actions">
          <h3 className="project-hub__card-title">Quick Actions</h3>
          <div className="project-hub__actions-grid">
            <button className="project-hub__action" onClick={() => navigate('/upload')}>
              <Upload size={20} />
              <span>Upload Data</span>
            </button>
            <button className="project-hub__action" onClick={() => navigate('/playbooks/select')}>
              <BookOpen size={20} />
              <span>Select Playbooks</span>
            </button>
            <button className="project-hub__action" onClick={() => navigate('/processing')}>
              <Play size={20} />
              <span>Run Analysis</span>
            </button>
            <button className="project-hub__action" onClick={() => navigate('/findings')}>
              <Search size={20} />
              <span>View Findings</span>
            </button>
            <button className="project-hub__action" onClick={() => navigate('/export')}>
              <Download size={20} />
              <span>Export Report</span>
            </button>
            <button className="project-hub__action" onClick={() => navigate('/workspace')}>
              <MessageSquare size={20} />
              <span>Ask AI</span>
            </button>
          </div>
        </div>

        {/* Findings Summary Card */}
        <div className="project-hub__card">
          <div className="project-hub__card-header">
            <h3 className="project-hub__card-title">Findings Summary</h3>
            <button 
              className="project-hub__card-link"
              onClick={() => navigate('/findings')}
            >
              View All <ChevronRight size={14} />
            </button>
          </div>
          <div className="project-hub__stats">
            <div className="project-hub__stat">
              <span className="project-hub__stat-value">{stats.findings.total}</span>
              <span className="project-hub__stat-label">Total</span>
            </div>
            <div className="project-hub__stat project-hub__stat--critical">
              <span className="project-hub__stat-value">{stats.findings.critical}</span>
              <span className="project-hub__stat-label">Critical</span>
            </div>
            <div className="project-hub__stat project-hub__stat--warning">
              <span className="project-hub__stat-value">{stats.findings.warning}</span>
              <span className="project-hub__stat-label">Warning</span>
            </div>
            <div className="project-hub__stat project-hub__stat--info">
              <span className="project-hub__stat-value">{stats.findings.info}</span>
              <span className="project-hub__stat-label">Info</span>
            </div>
          </div>
        </div>

        {/* Review Progress Card */}
        <div className="project-hub__card">
          <div className="project-hub__card-header">
            <h3 className="project-hub__card-title">Review Progress</h3>
            <button 
              className="project-hub__card-link"
              onClick={() => navigate(`/progress/${id}`)}
            >
              Track <ChevronRight size={14} />
            </button>
          </div>
          <div className="project-hub__progress">
            <div className="project-hub__progress-bar">
              <div 
                className="project-hub__progress-fill"
                style={{ width: `${stats.findings.total > 0 ? (stats.progress.approved / stats.findings.total) * 100 : 0}%` }}
              />
            </div>
            <div className="project-hub__progress-stats">
              <span className="project-hub__progress-stat">
                <strong>{stats.progress.approved}</strong> Approved
              </span>
              <span className="project-hub__progress-stat">
                <strong>{stats.progress.pending}</strong> Pending
              </span>
              <span className="project-hub__progress-percent">
                {stats.findings.total > 0 ? Math.round((stats.progress.approved / stats.findings.total) * 100) : 0}%
              </span>
            </div>
          </div>
        </div>

        {/* Playbooks Card */}
        <div className="project-hub__card">
          <div className="project-hub__card-header">
            <h3 className="project-hub__card-title">Assigned Playbooks</h3>
            <button 
              className="project-hub__card-link"
              onClick={() => navigate('/playbooks/select')}
            >
              Manage <ChevronRight size={14} />
            </button>
          </div>
          <div className="project-hub__playbooks">
            {project.playbooks && project.playbooks.length > 0 ? (
              project.playbooks.map((pb, i) => (
                <div key={i} className="project-hub__playbook">
                  <BookOpen size={16} />
                  <span>{typeof pb === 'string' ? pb : pb.name}</span>
                </div>
              ))
            ) : (
              <div className="project-hub__empty">
                <p>No playbooks assigned yet</p>
                <button 
                  className="xlr8-btn xlr8-btn--secondary xlr8-btn--sm"
                  onClick={() => navigate('/playbooks/select')}
                >
                  Select Playbooks
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Data Files Card */}
        <div className="project-hub__card">
          <div className="project-hub__card-header">
            <h3 className="project-hub__card-title">Uploaded Data</h3>
            <button 
              className="project-hub__card-link"
              onClick={() => navigate('/upload')}
            >
              Upload <ChevronRight size={14} />
            </button>
          </div>
          <div className="project-hub__data-summary">
            {stats.files > 0 ? (
              <>
                <div className="project-hub__data-count">
                  <FileCheck size={24} />
                  <span><strong>{stats.files}</strong> files uploaded</span>
                </div>
                <button 
                  className="xlr8-btn xlr8-btn--secondary xlr8-btn--sm"
                  onClick={() => navigate('/data')}
                >
                  View Data
                </button>
              </>
            ) : (
              <div className="project-hub__empty">
                <p>No data uploaded yet</p>
                <button 
                  className="xlr8-btn xlr8-btn--secondary xlr8-btn--sm"
                  onClick={() => navigate('/upload')}
                >
                  Upload Data
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
