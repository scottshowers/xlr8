/**
 * ProgressTrackerPage.jsx - Step 7: Track Progress
 * 
 * Seventh step in the 8-step consultant workflow.
 * Monitor remediation progress and track risk mitigation.
 * 
 * Flow: ... → Drill-In → [TRACK PROGRESS] → Export
 * 
 * Created: January 15, 2026 - Phase 4A UX Overhaul (proper rebuild)
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useProject } from '../context/ProjectContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Status configuration
const STATUS_CONFIG = {
  complete: { icon: '✅', label: 'Complete', variant: 'success' },
  in_progress: { icon: '🔄', label: 'In Progress', variant: 'warning' },
  blocked: { icon: '🚫', label: 'Blocked', variant: 'critical' },
  pending: { icon: '⏳', label: 'Pending', variant: 'neutral' },
};

// Mock progress data
const MOCK_PROGRESS = {
  playbook: {
    id: 'year-end-2026',
    name: 'Year-End Playbook 2026',
    project: 'Acme Corp - UKG Pro Implementation',
    started_at: '2026-01-10',
    due_date: '2026-01-31',
  },
  summary: {
    total_findings: 24,
    complete: 8,
    in_progress: 6,
    blocked: 2,
    pending: 8,
    risk_mitigated: 42500,
    risk_remaining: 58500,
  },
  findings: [
    { id: 'f1', title: '457 employees missing tax filing status', severity: 'critical', status: 'in_progress', owner: 'Sarah Chen', due: '2026-01-20' },
    { id: 'f2', title: 'Payroll codes inconsistent', severity: 'warning', status: 'complete', owner: 'Mike Johnson', due: '2026-01-18' },
    { id: 'f3', title: 'Terminated employees still active', severity: 'critical', status: 'blocked', owner: 'Sarah Chen', due: '2026-01-22', blocked_reason: 'Waiting on HR data' },
    { id: 'f4', title: 'SUI rates outdated', severity: 'warning', status: 'complete', owner: 'Lisa Park', due: '2026-01-15' },
    { id: 'f5', title: 'HSA contributions exceed limits', severity: 'critical', status: 'in_progress', owner: 'Mike Johnson', due: '2026-01-25' },
    { id: 'f6', title: 'Missing supervisor assignments', severity: 'info', status: 'pending', owner: 'Unassigned', due: '2026-01-30' },
  ],
};

const ProgressTrackerPage = () => {
  const navigate = useNavigate();
  const { playbookId } = useParams();
  const { activeProject, customerName } = useProject();

  const [progressData, setProgressData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('all');

  // Fetch progress data
  useEffect(() => {
    fetchProgress();
  }, [playbookId]);

  const fetchProgress = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/progress/${playbookId || 'default'}`);
      if (res.ok) {
        const data = await res.json();
        setProgressData(data);
      } else {
        setProgressData(MOCK_PROGRESS);
      }
    } catch (err) {
      console.error('Failed to fetch progress:', err);
      setProgressData(MOCK_PROGRESS);
    } finally {
      setLoading(false);
    }
  };

  // Filter findings
  const filteredFindings = useMemo(() => {
    if (!progressData?.findings) return [];
    if (activeFilter === 'all') return progressData.findings;
    return progressData.findings.filter(f => f.status === activeFilter);
  }, [progressData, activeFilter]);

  // Calculate completion percentage
  const completionPercent = useMemo(() => {
    if (!progressData?.summary) return 0;
    const { total_findings, complete } = progressData.summary;
    return total_findings > 0 ? Math.round((complete / total_findings) * 100) : 0;
  }, [progressData]);

  if (loading) {
    return (
      
        <div className="progress-tracker progress-tracker--loading">
          <LoadingSpinner />
          <p>Loading progress data...</p>
        </div>
      
    );
  }

  const { playbook, summary, findings } = progressData || MOCK_PROGRESS;

  return (
    
      <div className="progress-tracker">
        <PageHeader
          title="Track Progress"
          subtitle={`Step 7 of 8 • ${playbook?.name || 'Playbook Progress'}`}
          actions={
            <Button variant="primary" onClick={() => navigate('/export')}>
              📥 Export Report →
            </Button>
          }
        />

        {/* Overall Progress Card */}
        <Card className="progress-tracker__overview-card">
          <div className="progress-overview">
            <div className="progress-circle-container">
              <div className="progress-circle">
                <svg viewBox="0 0 100 100">
                  <circle className="progress-bg" cx="50" cy="50" r="45" />
                  <circle 
                    className="progress-fill" 
                    cx="50" cy="50" r="45"
                    style={{ strokeDashoffset: 283 - (283 * completionPercent / 100) }}
                  />
                </svg>
                <div className="progress-percent">{completionPercent}%</div>
              </div>
              <div className="progress-label">Complete</div>
            </div>

            <div className="progress-stats">
              <div className="progress-stat">
                <div className="progress-stat-value progress-stat-value--success">{summary?.complete || 0}</div>
                <div className="progress-stat-label">Complete</div>
              </div>
              <div className="progress-stat">
                <div className="progress-stat-value progress-stat-value--warning">{summary?.in_progress || 0}</div>
                <div className="progress-stat-label">In Progress</div>
              </div>
              <div className="progress-stat">
                <div className="progress-stat-value progress-stat-value--critical">{summary?.blocked || 0}</div>
                <div className="progress-stat-label">Blocked</div>
              </div>
              <div className="progress-stat">
                <div className="progress-stat-value">{summary?.pending || 0}</div>
                <div className="progress-stat-label">Pending</div>
              </div>
            </div>

            <div className="risk-mitigated">
              <div className="risk-label">Risk Mitigated</div>
              <div className="risk-value">${(summary?.risk_mitigated || 0).toLocaleString()}</div>
              <div className="risk-remaining">
                ${(summary?.risk_remaining || 0).toLocaleString()} remaining
              </div>
            </div>
          </div>
        </Card>

        {/* Status Filter Tabs */}
        <div className="progress-tracker__filters">
          {['all', 'complete', 'in_progress', 'blocked', 'pending'].map(status => (
            <button
              key={status}
              className={`filter-tab ${activeFilter === status ? 'filter-tab--active' : ''}`}
              onClick={() => setActiveFilter(status)}
            >
              {status === 'all' ? 'All' : STATUS_CONFIG[status]?.label}
              <span className="filter-count">
                {status === 'all' 
                  ? summary?.total_findings 
                  : summary?.[status] || 0}
              </span>
            </button>
          ))}
        </div>

        {/* Findings Progress List */}
        <Card className="progress-tracker__list-card">
          <CardHeader>
            <CardTitle icon="📋">Findings Progress</CardTitle>
          </CardHeader>
          
          <div className="progress-list">
            {filteredFindings.map(finding => {
              const statusConfig = STATUS_CONFIG[finding.status] || STATUS_CONFIG.pending;
              
              return (
                <div 
                  key={finding.id} 
                  className={`progress-item progress-item--${finding.status}`}
                  onClick={() => navigate(`/findings/${finding.id}`)}
                >
                  <div className="progress-item__status">
                    {statusConfig.icon}
                  </div>
                  
                  <div className="progress-item__content">
                    <div className="progress-item__title">{finding.title}</div>
                    <div className="progress-item__meta">
                      <Badge variant={finding.severity} size="sm">{finding.severity}</Badge>
                      <span>👤 {finding.owner}</span>
                      <span>📅 Due: {finding.due}</span>
                    </div>
                    {finding.blocked_reason && (
                      <div className="progress-item__blocked">
                        🚫 {finding.blocked_reason}
                      </div>
                    )}
                  </div>

                  <div className="progress-item__badge">
                    <Badge variant={statusConfig.variant}>{statusConfig.label}</Badge>
                  </div>
                </div>
              );
            })}

            {filteredFindings.length === 0 && (
              <div className="progress-empty">
                <p>No findings in this category</p>
              </div>
            )}
          </div>
        </Card>
      </div>
    
  );
};

export default ProgressTrackerPage;
