/**
 * FindingDetailPage.jsx - Step 6: Drill-In Detail
 * 
 * Sixth step in the 8-step consultant workflow.
 * Deep dive into a specific finding with impact analysis and recommendations.
 * 
 * Flow: ... → Findings → [DRILL-IN] → Track Progress → Export
 * 
 * Updated: January 15, 2026 - Phase 4A UX Overhaul (proper rebuild)
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import MainLayout from '../components/MainLayout';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useProject } from '../context/ProjectContext';
import './FindingDetailPage.css';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Severity configuration
const SEVERITY_CONFIG = {
  critical: { icon: '🔴', label: 'Critical', variant: 'critical', description: 'Requires immediate attention' },
  warning: { icon: '🟡', label: 'Warning', variant: 'warning', description: 'Should be addressed soon' },
  info: { icon: '🔵', label: 'Info', variant: 'info', description: 'For your awareness' },
};

// Mock finding data
const MOCK_FINDING = {
  id: 'f1',
  title: '457 employees missing tax filing status',
  description: 'Employee records are missing required federal tax filing status, which will cause W-2 generation errors during year-end processing.',
  severity: 'critical',
  category: 'data_quality',
  affected_count: 457,
  affected_label: 'employees',
  playbook: 'Year-End Playbook',
  action: 'Action 3A: Employee Data Validation',
  detected_at: '2026-01-14',
  why_it_matters: 'Missing tax filing status will prevent W-2 generation for affected employees. This could result in IRS penalties and delays in employee tax filing.',
  who_affected: [
    { department: 'Sales', count: 234 },
    { department: 'Engineering', count: 156 },
    { department: 'Operations', count: 67 },
  ],
  recommended_actions: [
    { id: 1, action: 'Export affected employee list', status: 'pending', effort: '5 min' },
    { id: 2, action: 'Send correction request to HR', status: 'pending', effort: '15 min' },
    { id: 3, action: 'Verify corrections in system', status: 'pending', effort: '30 min' },
    { id: 4, action: 'Re-run validation check', status: 'pending', effort: '5 min' },
  ],
  provenance: {
    source_table: 'EMPLOYEE_MASTER',
    source_column: 'TAX_FILING_STATUS',
    rule_applied: 'Required field check for year-end processing',
    detection_method: 'NULL value scan + business rule validation',
  },
  related_findings: [
    { id: 'f2', title: 'Missing state tax codes', severity: 'warning' },
    { id: 'f6', title: 'Missing supervisor assignments', severity: 'info' },
  ],
};

const FindingDetailPage = () => {
  const navigate = useNavigate();
  const { findingId } = useParams();
  const { activeProject } = useProject();

  const [finding, setFinding] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch finding details
  useEffect(() => {
    fetchFinding();
  }, [findingId]);

  const fetchFinding = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/findings/${findingId}`);
      if (res.ok) {
        const data = await res.json();
        setFinding(data);
      } else {
        setFinding(MOCK_FINDING);
      }
    } catch (err) {
      console.error('Failed to fetch finding:', err);
      setFinding(MOCK_FINDING);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    console.log('Approving finding:', findingId);
    navigate('/findings');
  };

  const handleReject = async () => {
    console.log('Rejecting finding:', findingId);
    navigate('/findings');
  };

  const handleMarkFalsePositive = async () => {
    console.log('Marking as false positive:', findingId);
    navigate('/findings');
  };

  if (loading) {
    return (
      <MainLayout showFlowBar={true} currentStep={6}>
        <div className="finding-detail finding-detail--loading">
          <LoadingSpinner />
          <p>Loading finding details...</p>
        </div>
      </MainLayout>
    );
  }

  if (!finding) {
    return (
      <MainLayout showFlowBar={true} currentStep={6}>
        <div className="finding-detail finding-detail--error">
          <h2>Finding not found</h2>
          <Button variant="secondary" onClick={() => navigate('/findings')}>
            ← Back to Findings
          </Button>
        </div>
      </MainLayout>
    );
  }

  const severityConfig = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.info;

  return (
    <MainLayout showFlowBar={true} currentStep={6}>
      <div className="finding-detail">
        <PageHeader
          title="Finding Detail"
          subtitle="Step 6 of 8 • Review and take action"
          actions={
            <Button variant="secondary" onClick={() => navigate('/findings')}>
              ← Back to Findings
            </Button>
          }
        />

        <div className="finding-detail__content">
          {/* Main Content */}
          <div className="finding-detail__main">
            {/* Finding Header Card */}
            <Card className="finding-detail__header-card">
              <div className="finding-header">
                <div className={`finding-severity-icon finding-severity-icon--${finding.severity}`}>
                  {severityConfig.icon}
                </div>
                <div className="finding-header-content">
                  <div className="finding-header-badges">
                    <Badge variant={severityConfig.variant}>{severityConfig.label}</Badge>
                    <Badge variant="neutral">{finding.category?.replace('_', ' ')}</Badge>
                    <Badge variant="info">{finding.playbook}</Badge>
                  </div>
                  <h1 className="finding-title">{finding.title}</h1>
                  <p className="finding-description">{finding.description}</p>
                  <div className="finding-meta">
                    <span>📅 Detected: {finding.detected_at}</span>
                    <span>•</span>
                    <span>⚙️ {finding.action}</span>
                  </div>
                </div>
              </div>
            </Card>

            {/* Impact Analysis */}
            <Card className="finding-detail__impact-card">
              <CardHeader>
                <CardTitle icon="📊">Impact Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="impact-stats">
                  <div className="impact-stat impact-stat--primary">
                    <div className="impact-value">{finding.affected_count}</div>
                    <div className="impact-label">{finding.affected_label} affected</div>
                  </div>
                </div>
                
                {finding.who_affected && finding.who_affected.length > 0 && (
                  <div className="impact-breakdown">
                    <h4>Breakdown by Department</h4>
                    <div className="breakdown-list">
                      {finding.who_affected.map((dept, idx) => (
                        <div key={idx} className="breakdown-row">
                          <span className="breakdown-name">{dept.department}</span>
                          <div className="breakdown-bar-container">
                            <div 
                              className="breakdown-bar" 
                              style={{ width: `${(dept.count / finding.affected_count) * 100}%` }}
                            />
                          </div>
                          <span className="breakdown-count">{dept.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Why It Matters */}
            <Card className="finding-detail__why-card">
              <CardHeader>
                <CardTitle icon="⚠️">Why It Matters</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="why-text">{finding.why_it_matters}</p>
              </CardContent>
            </Card>

            {/* Recommended Actions */}
            <Card className="finding-detail__actions-card">
              <CardHeader>
                <CardTitle icon="✅">Recommended Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="action-list">
                  {finding.recommended_actions?.map((action, idx) => (
                    <div key={action.id} className="action-item">
                      <div className="action-number">{idx + 1}</div>
                      <div className="action-content">
                        <div className="action-text">{action.action}</div>
                        <div className="action-meta">
                          <Badge variant="neutral" size="sm">{action.effort}</Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Provenance */}
            <Card className="finding-detail__provenance-card">
              <CardHeader>
                <CardTitle icon="🔍">Data Provenance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="provenance-grid">
                  <div className="provenance-item">
                    <div className="provenance-label">Source Table</div>
                    <div className="provenance-value">{finding.provenance?.source_table}</div>
                  </div>
                  <div className="provenance-item">
                    <div className="provenance-label">Source Column</div>
                    <div className="provenance-value">{finding.provenance?.source_column}</div>
                  </div>
                  <div className="provenance-item provenance-item--wide">
                    <div className="provenance-label">Rule Applied</div>
                    <div className="provenance-value">{finding.provenance?.rule_applied}</div>
                  </div>
                  <div className="provenance-item provenance-item--wide">
                    <div className="provenance-label">Detection Method</div>
                    <div className="provenance-value">{finding.provenance?.detection_method}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="finding-detail__sidebar">
            {/* Actions Card */}
            <Card className="finding-detail__decision-card">
              <CardHeader>
                <CardTitle icon="⚡">Take Action</CardTitle>
              </CardHeader>
              <div className="decision-actions">
                <Button variant="primary" onClick={handleApprove} className="decision-btn">
                  ✓ Approve Finding
                </Button>
                <Button variant="secondary" onClick={handleReject} className="decision-btn">
                  ✗ Reject Finding
                </Button>
                <Button variant="ghost" onClick={handleMarkFalsePositive} className="decision-btn">
                  🚫 False Positive
                </Button>
              </div>
            </Card>

            {/* Related Findings */}
            {finding.related_findings && finding.related_findings.length > 0 && (
              <Card className="finding-detail__related-card">
                <CardHeader>
                  <CardTitle icon="🔗">Related Findings</CardTitle>
                </CardHeader>
                <div className="related-list">
                  {finding.related_findings.map(related => (
                    <div 
                      key={related.id} 
                      className="related-item"
                      onClick={() => navigate(`/findings/${related.id}`)}
                    >
                      <span className="related-severity">
                        {SEVERITY_CONFIG[related.severity]?.icon}
                      </span>
                      <span className="related-title">{related.title}</span>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Next Step */}
            <Card className="finding-detail__next-card">
              <div className="next-step-preview">
                <div className="next-step-label">Next Step</div>
                <div className="next-step-title">📈 Track Progress</div>
                <div className="next-step-description">
                  Monitor remediation progress and track risk mitigation.
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default FindingDetailPage;
