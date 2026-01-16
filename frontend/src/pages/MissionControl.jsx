import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

/**
 * Mission Control Page
 * 
 * Cross-project review queue hub for consultants
 * Shows all findings awaiting review across all active projects
 */

const MissionControl = () => {
  const navigate = useNavigate();
  const [findings, setFindings] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFindings, setSelectedFindings] = useState(new Set());
  const [activeFilter, setActiveFilter] = useState('all');

  // Fetch data on mount
  useEffect(() => {
    fetchMissionControlData();
  }, []);

  const fetchMissionControlData = async () => {
    try {
      // TODO: Replace with actual API calls
      // const findingsRes = await fetch('/api/findings?status=pending');
      // const projectsRes = await fetch('/api/projects?has_pending=true');
      
      // Mock data for now
      const mockFindings = [
        {
          id: 'f1',
          title: '457 employees missing tax filing status',
          project: 'Acme Corp - UKG Pro Implementation',
          playbook: 'Year-End Playbook',
          action: 'Action 3A: Employee Data Validation',
          severity: 'critical',
          affectedCount: 457,
          affectedLabel: 'employees',
          detectedAt: '2026-01-14',
        },
        {
          id: 'f2',
          title: 'Payroll codes inconsistent across departments',
          project: 'Acme Corp - UKG Pro Implementation',
          playbook: 'Year-End Playbook',
          action: 'Action 5A: Earnings Code Review',
          severity: 'warning',
          affectedCount: 3,
          affectedLabel: 'departments',
          detectedAt: '2026-01-14',
        },
        {
          id: 'f3',
          title: '23 terminated employees still active in system',
          project: 'TechStart Inc - Data Migration',
          playbook: 'Data Quality Assessment',
          action: 'Action 2A: Status Validation',
          severity: 'critical',
          affectedCount: 23,
          affectedLabel: 'employees',
          detectedAt: '2026-01-13',
        },
        {
          id: 'f4',
          title: 'SUI rates appear outdated for 2 states (TX, CA)',
          project: 'Global Retail Co - Year-End 2025',
          playbook: 'Year-End Playbook',
          action: 'Action 2A: Tax Verification',
          severity: 'warning',
          affectedCount: 2,
          affectedLabel: 'states',
          detectedAt: '2026-01-14',
        },
        {
          id: 'f5',
          title: 'HSA contributions exceed 2026 annual limits for 8 employees',
          project: 'Acme Corp - UKG Pro Implementation',
          playbook: 'Year-End Playbook',
          action: 'Action 4A: Benefits Review',
          severity: 'critical',
          affectedCount: 8,
          affectedLabel: 'employees',
          detectedAt: '2026-01-14',
        },
      ];

      const mockProjects = [
        {
          id: 'p1',
          name: 'Acme Corp - UKG Pro Implementation',
          playbook: 'Year-End Playbook',
          goLive: 'March 15, 2026',
          awaiting: 12,
          approved: 8,
          inProgress: 3,
        },
        {
          id: 'p2',
          name: 'TechStart Inc - Data Migration',
          playbook: 'Data Quality Assessment',
          started: 'Jan 10, 2026',
          awaiting: 6,
          approved: 14,
          inProgress: 2,
        },
        {
          id: 'p3',
          name: 'Global Retail Co - Year-End 2025',
          playbook: 'Year-End Playbook',
          due: 'Jan 31, 2026',
          awaiting: 5,
          approved: 22,
          inProgress: 1,
        },
      ];

      setFindings(mockFindings);
      setProjects(mockProjects);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching mission control data:', error);
      setLoading(false);
    }
  };

  // Calculate stats from findings
  const stats = {
    awaiting: findings.length,
    critical: findings.filter(f => f.severity === 'critical').length,
    inProgress: 8, // TODO: Get from API
    approved: 34, // TODO: Get from API
  };

  // Filter findings
  const filteredFindings = findings.filter(finding => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'critical') return finding.severity === 'critical';
    if (activeFilter === 'warning') return finding.severity === 'warning';
    if (activeFilter === 'info') return finding.severity === 'info';
    return true;
  });

  // Toggle finding selection
  const toggleFinding = (id) => {
    const newSelected = new Set(selectedFindings);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedFindings(newSelected);
  };

  // Batch actions
  const handleBatchApprove = () => {
    console.log('Approving findings:', Array.from(selectedFindings));
    // TODO: API call to approve
    setSelectedFindings(new Set());
  };

  const handleBatchReject = () => {
    console.log('Rejecting findings:', Array.from(selectedFindings));
    // TODO: API call to reject
    setSelectedFindings(new Set());
  };

  const handleMarkFalsePositive = () => {
    console.log('Marking false positive:', Array.from(selectedFindings));
    // TODO: API call
    setSelectedFindings(new Set());
  };

  if (loading) {
    return (
      
        <div className="mission-control-loading">
          <div className="spinner" />
          <p>Loading Mission Control...</p>
        </div>
      
    );
  }

  return (
    
      <div className="mission-control">
        {/* Page Header */}
        <PageHeader
          title="Mission Control"
          subtitle={`Cross-project review queue • ${stats.awaiting} findings awaiting approval across ${projects.length} active projects`}
          actions={
            <>
              <Button variant="secondary" icon="📥">
                Export Report
              </Button>
              <Button variant="primary" icon="✨">
                Generate Report
              </Button>
            </>
          }
        />

        {/* Stats Grid */}
        <div className="mission-control__stats">
          <Card className="mission-control__stat-card">
            <div className="stat-icon stat-icon--critical">⏳</div>
            <div className="stat-content">
              <div className="stat-label">Awaiting Review</div>
              <div className="stat-value stat-value--critical">{stats.awaiting}</div>
              <div className="stat-sublabel">Across {projects.length} projects</div>
              <div className="stat-trend stat-trend--up">↑ 5 from yesterday</div>
            </div>
          </Card>

          <Card className="mission-control__stat-card">
            <div className="stat-icon stat-icon--critical">🔴</div>
            <div className="stat-content">
              <div className="stat-label">Critical Findings</div>
              <div className="stat-value stat-value--critical">{stats.critical}</div>
              <div className="stat-sublabel">Require immediate attention</div>
              <div className="stat-trend stat-trend--up">↑ 3 new today</div>
            </div>
          </Card>

          <Card className="mission-control__stat-card">
            <div className="stat-icon stat-icon--warning">📝</div>
            <div className="stat-content">
              <div className="stat-label">In Progress</div>
              <div className="stat-value stat-value--warning">{stats.inProgress}</div>
              <div className="stat-sublabel">Currently reviewing</div>
              <div className="stat-trend stat-trend--neutral">→ No change</div>
            </div>
          </Card>

          <Card className="mission-control__stat-card">
            <div className="stat-icon stat-icon--success">✅</div>
            <div className="stat-content">
              <div className="stat-label">Approved Today</div>
              <div className="stat-value stat-value--success">{stats.approved}</div>
              <div className="stat-sublabel">Ready for export</div>
              <div className="stat-trend stat-trend--up">↑ 12 since morning</div>
            </div>
          </Card>
        </div>

        {/* Review Queue */}
        <Card>
          <CardHeader>
            <CardTitle icon="🎯">Cross-Project Review Queue</CardTitle>
            <div className="mission-control__filters">
              <Button 
                variant={activeFilter === 'all' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setActiveFilter('all')}
              >
                All Findings
              </Button>
              <Button 
                variant={activeFilter === 'critical' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setActiveFilter('critical')}
              >
                Critical
              </Button>
              <Button 
                variant={activeFilter === 'warning' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setActiveFilter('warning')}
              >
                Warning
              </Button>
              <Button 
                variant={activeFilter === 'info' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setActiveFilter('info')}
              >
                Info
              </Button>
            </div>
          </CardHeader>

          {/* Batch Actions */}
          {selectedFindings.size > 0 && (
            <div className="mission-control__batch-actions">
              <Button 
                variant="primary" 
                size="sm"
                onClick={handleBatchApprove}
              >
                ✓ Approve Selected ({selectedFindings.size})
              </Button>
              <Button 
                variant="secondary" 
                size="sm"
                onClick={handleBatchReject}
              >
                ✗ Reject Selected
              </Button>
              <Button 
                variant="secondary" 
                size="sm"
                onClick={handleMarkFalsePositive}
              >
                🚫 Mark False Positive
              </Button>
            </div>
          )}

          {/* Findings List */}
          <div className="mission-control__findings">
            {filteredFindings.map(finding => (
              <div 
                key={finding.id}
                className="finding-row"
                onClick={() => navigate(`/findings/${finding.id}`)}
              >
                <div 
                  className="finding-checkbox"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleFinding(finding.id);
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedFindings.has(finding.id)}
                    onChange={() => {}}
                  />
                </div>

                <div className="finding-content">
                  <div className="finding-title">{finding.title}</div>
                  <div className="finding-meta">
                    <span>🏢 {finding.project}</span>
                    <span>📋 {finding.playbook}</span>
                    <span>⚙️ {finding.action}</span>
                    <span>📅 Detected: {finding.detectedAt}</span>
                  </div>
                </div>

                <div className="finding-severity-col">
                  <Badge 
                    variant={finding.severity} 
                    dot
                  >
                    {finding.severity}
                  </Badge>
                  <div className="finding-affected">
                    {finding.affectedCount} {finding.affectedLabel}
                  </div>
                </div>
              </div>
            ))}

            {filteredFindings.length === 0 && (
              <div className="mission-control__empty">
                <div className="empty-icon">✅</div>
                <div className="empty-title">No findings in this category</div>
                <div className="empty-subtitle">
                  {activeFilter === 'all' 
                    ? 'All findings have been reviewed!'
                    : `No ${activeFilter} findings at this time.`}
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* Projects with Pending Work */}
        <Card>
          <CardHeader>
            <CardTitle icon="📁">Projects with Pending Work</CardTitle>
          </CardHeader>

          <div className="mission-control__projects">
            {projects.map(project => (
              <div 
                key={project.id}
                className="project-card"
                onClick={() => navigate(`/projects/${project.id}/hub`)}
              >
                <div className="project-name">{project.name}</div>
                <div className="project-meta">
                  <span>📋 {project.playbook}</span>
                  <span>•</span>
                  <span>
                    {project.goLive && `🎯 Go-Live: ${project.goLive}`}
                    {project.started && `🚀 Started: ${project.started}`}
                    {project.due && `⏰ Due: ${project.due}`}
                  </span>
                </div>
                <div className="project-stats">
                  <div className="project-stat">
                    <div className="project-stat-value project-stat-value--critical">
                      {project.awaiting}
                    </div>
                    <div className="project-stat-label">Awaiting</div>
                  </div>
                  <div className="project-stat">
                    <div className="project-stat-value project-stat-value--success">
                      {project.approved}
                    </div>
                    <div className="project-stat-label">Approved</div>
                  </div>
                  <div className="project-stat">
                    <div className="project-stat-value project-stat-value--neutral">
                      {project.inProgress}
                    </div>
                    <div className="project-stat-label">In Progress</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    
  );
};

export default MissionControl;
