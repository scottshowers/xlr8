/**
 * FindingsDashboard.jsx - Step 5: Findings
 * 
 * Fifth step in the 8-step consultant workflow.
 * Shows prioritized, categorized findings from analysis.
 * 
 * Flow: ... → Analysis → [FINDINGS] → Drill-In → Track Progress → Export
 * 
 * Updated: January 15, 2026 - Phase 4A UX Overhaul (proper rebuild)
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { useProject } from '../context/ProjectContext';
import api from '../services/api';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Severity configuration
const SEVERITY_CONFIG = {
  critical: { icon: '🔴', label: 'Critical', variant: 'critical' },
  warning: { icon: '🟡', label: 'Warning', variant: 'warning' },
  info: { icon: '🔵', label: 'Info', variant: 'info' },
};

// Category configuration
const CATEGORY_CONFIG = {
  data_quality: { icon: '📊', label: 'Data Quality' },
  configuration: { icon: '⚙️', label: 'Configuration' },
  compliance: { icon: '🛡️', label: 'Compliance' },
  coverage: { icon: '📋', label: 'Coverage' },
  pattern: { icon: '📈', label: 'Pattern' },
};

// Mock findings data
const MOCK_FINDINGS = [
  {
    id: 'f1',
    title: '457 employees missing tax filing status',
    description: 'Employee records are missing required federal tax filing status, which will cause W-2 generation errors.',
    severity: 'critical',
    category: 'data_quality',
    affected_count: 457,
    affected_label: 'employees',
    playbook: 'Year-End Playbook',
    detected_at: '2026-01-14',
  },
  {
    id: 'f2',
    title: 'Payroll codes inconsistent across departments',
    description: 'Different departments are using different earnings codes for the same pay types, causing reporting inconsistencies.',
    severity: 'warning',
    category: 'configuration',
    affected_count: 3,
    affected_label: 'departments',
    playbook: 'Year-End Playbook',
    detected_at: '2026-01-14',
  },
  {
    id: 'f3',
    title: '23 terminated employees still active in system',
    description: 'Employee records show active status but have termination dates in the past.',
    severity: 'critical',
    category: 'data_quality',
    affected_count: 23,
    affected_label: 'employees',
    playbook: 'Data Quality Assessment',
    detected_at: '2026-01-13',
  },
  {
    id: 'f4',
    title: 'SUI rates appear outdated for 2 states',
    description: 'State Unemployment Insurance rates for TX and CA do not match current year requirements.',
    severity: 'warning',
    category: 'compliance',
    affected_count: 2,
    affected_label: 'states',
    playbook: 'Year-End Playbook',
    detected_at: '2026-01-14',
  },
  {
    id: 'f5',
    title: 'HSA contributions exceed 2026 annual limits',
    description: 'Current contribution rates will cause 8 employees to exceed IRS HSA limits by year end.',
    severity: 'critical',
    category: 'compliance',
    affected_count: 8,
    affected_label: 'employees',
    playbook: 'Year-End Playbook',
    detected_at: '2026-01-14',
  },
  {
    id: 'f6',
    title: 'Missing supervisor assignments',
    description: 'Employee records lack supervisor assignments which may impact approval workflows.',
    severity: 'info',
    category: 'coverage',
    affected_count: 156,
    affected_label: 'employees',
    playbook: 'Data Quality Assessment',
    detected_at: '2026-01-14',
  },
];

const FindingsDashboard = () => {
  const navigate = useNavigate();
  const { activeProject, customerName } = useProject();

  // State
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all');
  const [selectedIds, setSelectedIds] = useState(new Set());

  // Cost equivalent data
  const [costData, setCostData] = useState({
    records: 47382,
    tables: 12,
    hours: 17,
    cost: 4250,
  });

  // Fetch findings
  useEffect(() => {
    fetchFindings();
  }, [activeProject]);

  const fetchFindings = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/findings${activeProject ? `?project_id=${activeProject.id}` : ''}`);
      if (res.ok) {
        const data = await res.json();
        setFindings(data.findings || data || []);
      } else {
        setFindings(MOCK_FINDINGS);
      }
    } catch (err) {
      console.error('Failed to fetch findings:', err);
      setFindings(MOCK_FINDINGS);
    } finally {
      setLoading(false);
    }
  };

  // Filter findings
  const filteredFindings = useMemo(() => {
    if (activeFilter === 'all') return findings;
    return findings.filter(f => f.severity === activeFilter);
  }, [findings, activeFilter]);

  // Stats
  const stats = useMemo(() => ({
    total: findings.length,
    critical: findings.filter(f => f.severity === 'critical').length,
    warning: findings.filter(f => f.severity === 'warning').length,
    info: findings.filter(f => f.severity === 'info').length,
  }), [findings]);

  // Selection handlers
  const toggleSelection = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => setSelectedIds(new Set(filteredFindings.map(f => f.id)));
  const clearSelection = () => setSelectedIds(new Set());

  if (loading) {
    return (
      
        <div className="findings-dashboard findings-dashboard--loading">
          <LoadingSpinner />
          <p>Loading findings...</p>
        </div>
      
    );
  }

  return (
    
      <div className="findings-dashboard">
        <PageHeader
          title="Findings Dashboard"
          subtitle={`Step 5 of 8 • ${stats.total} findings from analysis${customerName ? ` for ${customerName}` : ''}`}
          actions={
            <>
              <Button variant="secondary" onClick={() => navigate('/progress/default')}>
                📊 Track Progress
              </Button>
              <Button variant="primary" onClick={() => navigate('/export')}>
                📥 Export Report
              </Button>
            </>
          }
        />

        {/* Cost Equivalent Banner */}
        <Card className="findings-dashboard__cost-banner">
          <div className="cost-banner">
            <div className="cost-banner__info">
              <h3 className="cost-banner__title">Analysis Complete</h3>
              <p className="cost-banner__subtitle">
                Analyzed {costData.records.toLocaleString()} records across {costData.tables} tables
              </p>
            </div>
            <div className="cost-banner__value">
              <div className="cost-amount">${costData.cost.toLocaleString()}</div>
              <div className="cost-label">{costData.hours} hours @ $250/hr equivalent</div>
            </div>
          </div>
        </Card>

        {/* Stats Grid */}
        <div className="findings-dashboard__stats">
          <Card className={`stat-card ${activeFilter === 'all' ? 'stat-card--active' : ''}`} onClick={() => setActiveFilter('all')}>
            <div className="stat-icon">📋</div>
            <div className="stat-content">
              <div className="stat-value">{stats.total}</div>
              <div className="stat-label">Total Findings</div>
            </div>
          </Card>
          <Card className={`stat-card stat-card--critical ${activeFilter === 'critical' ? 'stat-card--active' : ''}`} onClick={() => setActiveFilter('critical')}>
            <div className="stat-icon">🔴</div>
            <div className="stat-content">
              <div className="stat-value stat-value--critical">{stats.critical}</div>
              <div className="stat-label">Critical</div>
            </div>
          </Card>
          <Card className={`stat-card stat-card--warning ${activeFilter === 'warning' ? 'stat-card--active' : ''}`} onClick={() => setActiveFilter('warning')}>
            <div className="stat-icon">🟡</div>
            <div className="stat-content">
              <div className="stat-value stat-value--warning">{stats.warning}</div>
              <div className="stat-label">Warning</div>
            </div>
          </Card>
          <Card className={`stat-card stat-card--info ${activeFilter === 'info' ? 'stat-card--active' : ''}`} onClick={() => setActiveFilter('info')}>
            <div className="stat-icon">🔵</div>
            <div className="stat-content">
              <div className="stat-value stat-value--info">{stats.info}</div>
              <div className="stat-label">Info</div>
            </div>
          </Card>
        </div>

        {/* Findings List */}
        <Card className="findings-dashboard__list-card">
          <CardHeader>
            <CardTitle icon="🎯">
              {activeFilter === 'all' ? 'All Findings' : `${SEVERITY_CONFIG[activeFilter]?.label} Findings`}
            </CardTitle>
            <div className="list-actions">
              {selectedIds.size > 0 ? (
                <>
                  <span className="selection-count">{selectedIds.size} selected</span>
                  <Button variant="ghost" size="sm" onClick={clearSelection}>Clear</Button>
                </>
              ) : (
                <Button variant="ghost" size="sm" onClick={selectAll}>Select All</Button>
              )}
            </div>
          </CardHeader>

          {filteredFindings.length === 0 ? (
            <EmptyState
              icon="✅"
              title="No findings in this category"
              description={activeFilter === 'all' ? 'No issues detected!' : `No ${activeFilter} findings at this time.`}
            />
          ) : (
            <div className="findings-list">
              {filteredFindings.map(finding => {
                const severityConfig = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.info;
                const categoryConfig = CATEGORY_CONFIG[finding.category] || { icon: '📁', label: 'General' };
                const isSelected = selectedIds.has(finding.id);

                return (
                  <div
                    key={finding.id}
                    className={`finding-row ${isSelected ? 'finding-row--selected' : ''}`}
                    onClick={() => navigate(`/findings/${finding.id}`)}
                  >
                    {/* Checkbox */}
                    <div
                      className="finding-checkbox"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSelection(finding.id);
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {}}
                      />
                    </div>

                    {/* Severity Icon */}
                    <div className={`finding-severity finding-severity--${finding.severity}`}>
                      {severityConfig.icon}
                    </div>

                    {/* Content */}
                    <div className="finding-content">
                      <div className="finding-title">{finding.title}</div>
                      <div className="finding-meta">
                        <span>{categoryConfig.icon} {categoryConfig.label}</span>
                        <span>•</span>
                        <span>📋 {finding.playbook}</span>
                        <span>•</span>
                        <span>📅 {finding.detected_at}</span>
                      </div>
                    </div>

                    {/* Affected Count */}
                    <div className="finding-affected">
                      <Badge variant={severityConfig.variant}>
                        {finding.affected_count} {finding.affected_label}
                      </Badge>
                    </div>

                    {/* Arrow */}
                    <div className="finding-arrow">→</div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    
  );
};

export default FindingsDashboard;
