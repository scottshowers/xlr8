/**
 * ProgressTrackerPage.jsx - Step 7: Track Progress
 * 
 * Track remediation progress on findings.
 * Uses design system classes - NO emojis.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Check, Clock, AlertCircle, ChevronRight } from 'lucide-react';

const MOCK_PROGRESS = {
  playbook: 'Year-End Readiness',
  totalFindings: 24,
  approved: 18,
  pending: 4,
  rejected: 2,
  actions: [
    { id: 'a1', name: 'Employee Data Validation', findings: 8, completed: 6, status: 'in_progress' },
    { id: 'a2', name: 'Tax Configuration Review', findings: 5, completed: 5, status: 'complete' },
    { id: 'a3', name: 'Earnings Code Audit', findings: 6, completed: 4, status: 'in_progress' },
    { id: 'a4', name: 'Benefits Reconciliation', findings: 5, completed: 3, status: 'in_progress' },
  ],
};

const ProgressTrackerPage = () => {
  const navigate = useNavigate();
  const { playbookId } = useParams();
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setProgress(MOCK_PROGRESS);
      setLoading(false);
    }, 500);
  }, [playbookId]);

  if (loading) return <div className="page-loading"><p>Loading progress...</p></div>;

  const completionPercent = Math.round((progress.approved / progress.totalFindings) * 100);

  return (
    <div className="progress-page">
      <button className="btn btn-secondary mb-4" onClick={() => navigate('/findings')}>
        <ArrowLeft size={16} />
        Back to Findings
      </button>

      <div className="page-header">
        <h1 className="page-title">{progress.playbook}</h1>
        <p className="page-subtitle">Remediation Progress Tracker</p>
      </div>

      {/* Summary */}
      <div className="card mb-6">
        <div className="card-body">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Overall Progress
              </div>
              <div style={{ fontSize: 'var(--text-3xl)', fontWeight: 'var(--weight-bold)' }}>
                {completionPercent}% Complete
              </div>
            </div>
            <div className="flex gap-6">
              <div className="finding-stat">
                <div className="finding-stat__value finding-stat__value--info">{progress.approved}</div>
                <div className="finding-stat__label">Approved</div>
              </div>
              <div className="finding-stat">
                <div className="finding-stat__value finding-stat__value--warning">{progress.pending}</div>
                <div className="finding-stat__label">Pending</div>
              </div>
              <div className="finding-stat">
                <div className="finding-stat__value" style={{ color: 'var(--text-muted)' }}>{progress.rejected}</div>
                <div className="finding-stat__label">Rejected</div>
              </div>
            </div>
          </div>
          <div className="progress-bar" style={{ height: '12px' }}>
            <div className="progress-bar__fill" style={{ width: `${completionPercent}%` }} />
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="section-header">
        <h2 className="section-title">Actions</h2>
      </div>

      <div className="findings-list">
        {progress.actions.map(action => {
          const actionPercent = Math.round((action.completed / action.findings) * 100);
          return (
            <div key={action.id} className="finding-item">
              <div className={`finding-item__indicator ${action.status === 'complete' ? 'finding-item__indicator--info' : 'finding-item__indicator--warning'}`}>
                {action.status === 'complete' ? <Check size={18} /> : <Clock size={18} />}
              </div>
              <div className="finding-item__content" style={{ flex: 1 }}>
                <div className="finding-item__title">{action.name}</div>
                <div className="finding-item__meta">
                  <span>{action.completed} of {action.findings} findings resolved</span>
                </div>
                <div className="progress-bar mt-2" style={{ height: '4px', maxWidth: '200px' }}>
                  <div className="progress-bar__fill" style={{ width: `${actionPercent}%` }} />
                </div>
              </div>
              <span style={{ fontWeight: 'var(--weight-semibold)', color: action.status === 'complete' ? 'var(--grass-green)' : 'var(--text-secondary)' }}>
                {actionPercent}%
              </span>
            </div>
          );
        })}
      </div>

      {/* Continue */}
      <div className="flex gap-4 mt-6">
        <button className="btn btn-primary btn-lg" onClick={() => navigate('/export')}>
          Continue to Export
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
};

export default ProgressTrackerPage;
