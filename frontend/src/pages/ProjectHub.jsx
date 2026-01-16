/**
 * ProjectHub.jsx - Project Workspace
 * ===================================
 * 
 * Dedicated hub for a specific project showing:
 * - Flow progress (where are we in the 8 steps)
 * - Project details (vendor, product, playbooks)
 * - Quick actions to continue workflow
 * - Findings summary
 * - Chat contextual to this project
 * 
 * Phase 4A UX Overhaul - January 15, 2026
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
  AlertTriangle,
  CheckCircle,
  Clock,
  Building,
  Package,
  Clipboard
} from 'lucide-react';

// Flow steps configuration
const FLOW_STEPS = [
  { num: 1, label: 'Create Project', icon: '📁', path: '/projects/new', key: 'created' },
  { num: 2, label: 'Upload Data', icon: '📤', path: '/upload', key: 'has_data' },
  { num: 3, label: 'Select Playbooks', icon: '📚', path: '/playbooks/select', key: 'has_playbooks' },
  { num: 4, label: 'Analysis', icon: '⚙️', path: '/processing', key: 'analyzed' },
  { num: 5, label: 'Findings', icon: '🔍', path: '/findings', key: 'has_findings' },
  { num: 6, label: 'Drill-In', icon: '🎯', path: '/findings', key: 'reviewed' },
  { num: 7, label: 'Track Progress', icon: '📊', path: '/progress', key: 'tracking' },
  { num: 8, label: 'Export', icon: '📥', path: '/export', key: 'exported' },
];

export default function ProjectHub() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { projects, setActiveProject } = useProject();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Find project from context or fetch
    // Convert to string for comparison since URL params are strings
    const found = projects?.find(p => String(p.id) === String(id));
    if (found) {
      setProject(found);
      setActiveProject(found);
      setLoading(false);
    } else {
      // TODO: Fetch from API if not in context
      setLoading(false);
    }
  }, [id, projects, setActiveProject]);

  // Determine current step based on project state
  const getCurrentStep = () => {
    if (!project) return 1;
    // TODO: Base this on actual project state
    // For now, mock based on what data exists
    if (project.exported) return 8;
    if (project.tracking) return 7;
    if (project.reviewed) return 6;
    if (project.has_findings) return 5;
    if (project.analyzed) return 4;
    if (project.has_playbooks) return 3;
    if (project.has_data) return 2;
    return 1;
  };

  const currentStep = getCurrentStep();

  // Mock stats - TODO: Get from API
  const stats = {
    findings: { total: 12, critical: 3, warning: 5, info: 4 },
    progress: { approved: 8, pending: 4, rejected: 0 },
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
        <div className="project-hub__empty">
          <div className="empty-icon">📁</div>
          <h2>Project not found</h2>
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

  const nextStep = FLOW_STEPS[currentStep] || FLOW_STEPS[0];

  return (
    <div className="project-hub">
      {/* Project Header */}
      <div className="project-hub__header">
        <div className="project-hub__title-section">
          <div className="project-hub__avatar">
            {(project.customer || project.name || 'P').substring(0, 2).toUpperCase()}
          </div>
          <div>
            <h1 className="project-hub__title">{project.customer || project.name}</h1>
            <div className="project-hub__meta">
              <span><Building size={14} /> {project.vendor || 'UKG'}</span>
              <span><Package size={14} /> {project.system_type || 'UKG Pro'}</span>
              <span><Clipboard size={14} /> {project.engagement_type || 'Implementation'}</span>
            </div>
          </div>
        </div>
        <div className="project-hub__actions">
          <button 
            className="xlr8-btn xlr8-btn--secondary"
            onClick={() => navigate('/workspace')}
          >
            <MessageSquare size={16} />
            Chat
          </button>
          <button 
            className="xlr8-btn xlr8-btn--primary"
            onClick={() => navigate(nextStep.path)}
          >
            Continue to {nextStep.label}
            <ArrowRight size={16} />
          </button>
        </div>
      </div>

      {/* Flow Progress */}
      <div className="project-hub__flow">
        <h3 className="project-hub__section-title">Workflow Progress</h3>
        <div className="project-hub__flow-steps">
          {FLOW_STEPS.map((step, index) => {
            const isComplete = step.num < currentStep;
            const isCurrent = step.num === currentStep;
            const isPending = step.num > currentStep;

            return (
              <div 
                key={step.num}
                className={`flow-step ${isComplete ? 'flow-step--complete' : ''} ${isCurrent ? 'flow-step--current' : ''} ${isPending ? 'flow-step--pending' : ''}`}
                onClick={() => navigate(step.path)}
              >
                <div className="flow-step__indicator">
                  {isComplete ? <CheckCircle size={20} /> : step.num}
                </div>
                <div className="flow-step__label">{step.label}</div>
                {index < FLOW_STEPS.length - 1 && (
                  <div className={`flow-step__connector ${isComplete ? 'flow-step__connector--complete' : ''}`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="project-hub__grid">
        {/* Findings Summary */}
        <div className="project-hub__card">
          <div className="project-hub__card-header">
            <h3><Search size={18} /> Findings Summary</h3>
            <button 
              className="xlr8-btn xlr8-btn--ghost xlr8-btn--sm"
              onClick={() => navigate('/findings')}
            >
              View All
            </button>
          </div>
          <div className="project-hub__stats-row">
            <div className="project-hub__stat">
              <div className="project-hub__stat-value">{stats.findings.total}</div>
              <div className="project-hub__stat-label">Total</div>
            </div>
            <div className="project-hub__stat project-hub__stat--critical">
              <div className="project-hub__stat-value">{stats.findings.critical}</div>
              <div className="project-hub__stat-label">Critical</div>
            </div>
            <div className="project-hub__stat project-hub__stat--warning">
              <div className="project-hub__stat-value">{stats.findings.warning}</div>
              <div className="project-hub__stat-label">Warning</div>
            </div>
            <div className="project-hub__stat project-hub__stat--info">
              <div className="project-hub__stat-value">{stats.findings.info}</div>
              <div className="project-hub__stat-label">Info</div>
            </div>
          </div>
        </div>

        {/* Review Progress */}
        <div className="project-hub__card">
          <div className="project-hub__card-header">
            <h3><FileCheck size={18} /> Review Progress</h3>
            <button 
              className="xlr8-btn xlr8-btn--ghost xlr8-btn--sm"
              onClick={() => navigate(`/progress/${project.id}`)}
            >
              Track
            </button>
          </div>
          <div className="project-hub__stats-row">
            <div className="project-hub__stat project-hub__stat--success">
              <div className="project-hub__stat-value">{stats.progress.approved}</div>
              <div className="project-hub__stat-label">Approved</div>
            </div>
            <div className="project-hub__stat project-hub__stat--warning">
              <div className="project-hub__stat-value">{stats.progress.pending}</div>
              <div className="project-hub__stat-label">Pending</div>
            </div>
            <div className="project-hub__stat project-hub__stat--critical">
              <div className="project-hub__stat-value">{stats.progress.rejected}</div>
              <div className="project-hub__stat-label">Rejected</div>
            </div>
          </div>
          {/* Progress Bar */}
          <div className="project-hub__progress-bar">
            <div 
              className="project-hub__progress-fill"
              style={{ width: `${(stats.progress.approved / stats.findings.total) * 100}%` }}
            />
          </div>
          <div className="project-hub__progress-label">
            {Math.round((stats.progress.approved / stats.findings.total) * 100)}% Complete
          </div>
        </div>

        {/* Assigned Playbooks */}
        <div className="project-hub__card">
          <div className="project-hub__card-header">
            <h3><BookOpen size={18} /> Playbooks</h3>
            <button 
              className="xlr8-btn xlr8-btn--ghost xlr8-btn--sm"
              onClick={() => navigate('/playbooks/select')}
            >
              Manage
            </button>
          </div>
          <div className="project-hub__playbooks">
            {project.playbooks?.length > 0 ? (
              project.playbooks.map((pb, i) => (
                <div key={i} className="project-hub__playbook-item">
                  <span className="project-hub__playbook-icon">📋</span>
                  <span>{pb.name || pb}</span>
                </div>
              ))
            ) : (
              <div className="project-hub__empty-state">
                <p>No playbooks assigned</p>
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

        {/* Quick Actions */}
        <div className="project-hub__card">
          <div className="project-hub__card-header">
            <h3><Play size={18} /> Quick Actions</h3>
          </div>
          <div className="project-hub__quick-actions">
            <button 
              className="project-hub__action-btn"
              onClick={() => navigate('/upload')}
            >
              <Upload size={18} />
              Upload Data
            </button>
            <button 
              className="project-hub__action-btn"
              onClick={() => navigate('/processing')}
            >
              <Play size={18} />
              Run Analysis
            </button>
            <button 
              className="project-hub__action-btn"
              onClick={() => navigate('/export')}
            >
              <Download size={18} />
              Export Report
            </button>
            <button 
              className="project-hub__action-btn"
              onClick={() => navigate('/workspace')}
            >
              <MessageSquare size={18} />
              Ask AI
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
