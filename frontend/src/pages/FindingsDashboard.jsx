/**
 * FindingsDashboard.jsx - Step 5: Findings
 * 
 * Shows prioritized findings from analysis.
 * Uses design system classes - NO emojis.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, AlertTriangle, Info, ChevronRight, Filter } from 'lucide-react';
import { useProject } from '../context/ProjectContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

const SEVERITY_ICONS = { critical: AlertCircle, warning: AlertTriangle, info: Info };

const MOCK_FINDINGS = [
  { id: 'f1', title: '457 employees missing tax filing status', description: 'Missing required federal tax filing status for W-2 generation.', severity: 'critical', affected: '457 employees', playbook: 'Year-End Playbook' },
  { id: 'f2', title: 'Payroll codes inconsistent across departments', description: 'Different earnings codes for same pay types causing reporting issues.', severity: 'warning', affected: '3 departments', playbook: 'Year-End Playbook' },
  { id: 'f3', title: '23 terminated employees still active', description: 'Records show active status with past termination dates.', severity: 'critical', affected: '23 employees', playbook: 'Data Quality' },
  { id: 'f4', title: 'SUI rates outdated for 2 states', description: 'TX and CA rates do not match current year requirements.', severity: 'warning', affected: '2 states', playbook: 'Year-End Playbook' },
  { id: 'f5', title: 'Benefit eligibility dates missing', description: '89 employees missing benefit start dates.', severity: 'info', affected: '89 employees', playbook: 'Benefits Review' },
];

const FindingsDashboard = () => {
  const navigate = useNavigate();
  const { activeProject } = useProject();
  
  const [findings, setFindings] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFindings();
  }, []);

  const fetchFindings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/findings?project_id=${activeProject?.id}`);
      if (res.ok) {
        const data = await res.json();
        setFindings(data.findings || data || []);
      } else {
        setFindings(MOCK_FINDINGS);
      }
    } catch {
      setFindings(MOCK_FINDINGS);
    } finally {
      setLoading(false);
    }
  };

  const filteredFindings = filter === 'all' ? findings : findings.filter(f => f.severity === filter);
  const counts = {
    all: findings.length,
    critical: findings.filter(f => f.severity === 'critical').length,
    warning: findings.filter(f => f.severity === 'warning').length,
    info: findings.filter(f => f.severity === 'info').length,
  };

  if (loading) {
    return <div className="page-loading"><p>Loading findings...</p></div>;
  }

  return (
    <div className="findings-page">
      <div className="page-header flex justify-between items-center">
        <div>
          <h1 className="page-title">Findings</h1>
          <p className="page-subtitle">{findings.length} findings from analysis</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/export')}>
          Export Report
          <ChevronRight size={18} />
        </button>
      </div>

      {/* Summary Stats */}
      <div className="stats-grid mb-6">
        <div className="stat-card">
          <div className="stat-label">Total Findings</div>
          <div className="stat-value">{counts.all}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Critical</div>
          <div className="stat-value stat-value--critical">{counts.critical}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Warning</div>
          <div className="stat-value stat-value--warning">{counts.warning}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Info</div>
          <div className="stat-value" style={{ color: 'var(--info)' }}>{counts.info}</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="card mb-4">
        <div className="card-body flex gap-2" style={{ padding: 'var(--space-2)' }}>
          {['all', 'critical', 'warning', 'info'].map(f => (
            <button
              key={f}
              className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)} ({counts[f]})
            </button>
          ))}
        </div>
      </div>

      {/* Findings List */}
      <div className="findings-list">
        {filteredFindings.map(finding => {
          const Icon = SEVERITY_ICONS[finding.severity] || Info;
          return (
            <div
              key={finding.id}
              className="finding-item"
              onClick={() => navigate(`/findings/${finding.id}`)}
            >
              <div className={`finding-item__indicator finding-item__indicator--${finding.severity}`}>
                <Icon size={18} />
              </div>
              <div className="finding-item__content">
                <div className="finding-item__title">{finding.title}</div>
                <div className="finding-item__meta">
                  <span>{finding.affected}</span>
                  <span>-</span>
                  <span>{finding.playbook}</span>
                </div>
              </div>
              <ChevronRight size={18} style={{ color: 'var(--text-muted)' }} />
            </div>
          );
        })}
      </div>

      {filteredFindings.length === 0 && (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
            <p className="text-muted">No {filter} findings</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default FindingsDashboard;
