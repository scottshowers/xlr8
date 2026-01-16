/**
 * FindingDetailPage.jsx - Step 6: Review (Drill-In)
 * 
 * Detailed view of a single finding with affected data.
 * Uses design system classes - NO emojis.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, AlertCircle, AlertTriangle, Info, Check, X, Download } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

const MOCK_FINDING = {
  id: 'f1',
  title: '457 employees missing tax filing status',
  description: 'Employee records are missing required federal tax filing status, which will cause W-2 generation errors. This field is required for year-end processing.',
  severity: 'critical',
  affected: '457 employees',
  playbook: 'Year-End Playbook',
  action: 'Action 3A: Employee Data Validation',
  recommendation: 'Export the affected employee list and work with HR to update tax filing status before W-2 generation deadline.',
  affectedRecords: [
    { id: 'E001', name: 'John Smith', department: 'Engineering', hire_date: '2023-05-15' },
    { id: 'E002', name: 'Sarah Johnson', department: 'Marketing', hire_date: '2022-08-01' },
    { id: 'E003', name: 'Michael Brown', department: 'Sales', hire_date: '2024-01-10' },
    { id: 'E004', name: 'Emily Davis', department: 'HR', hire_date: '2023-11-20' },
    { id: 'E005', name: 'Robert Wilson', department: 'Finance', hire_date: '2022-03-05' },
  ],
};

const FindingDetailPage = () => {
  const navigate = useNavigate();
  const { findingId } = useParams();
  const [finding, setFinding] = useState(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('pending'); // pending, approved, rejected

  useEffect(() => {
    fetchFinding();
  }, [findingId]);

  const fetchFinding = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/findings/${findingId}`);
      if (res.ok) {
        setFinding(await res.json());
      } else {
        setFinding({ ...MOCK_FINDING, id: findingId });
      }
    } catch {
      setFinding({ ...MOCK_FINDING, id: findingId });
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = () => setStatus('approved');
  const handleReject = () => setStatus('rejected');

  if (loading) return <div className="page-loading"><p>Loading finding...</p></div>;
  if (!finding) return <div className="page-loading"><p>Finding not found</p></div>;

  const SeverityIcon = { critical: AlertCircle, warning: AlertTriangle, info: Info }[finding.severity] || Info;

  return (
    <div className="finding-detail-page">
      {/* Back Button */}
      <button className="btn btn-secondary mb-4" onClick={() => navigate('/findings')}>
        <ArrowLeft size={16} />
        Back to Findings
      </button>

      {/* Header */}
      <div className="card mb-6">
        <div className="card-body">
          <div className="flex items-center gap-4 mb-4">
            <div className={`finding-item__indicator finding-item__indicator--${finding.severity}`}>
              <SeverityIcon size={20} />
            </div>
            <div style={{ flex: 1 }}>
              <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--weight-bold)', marginBottom: '4px' }}>{finding.title}</h1>
              <div className="flex gap-4" style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                <span>{finding.affected}</span>
                <span>-</span>
                <span>{finding.playbook}</span>
                <span>-</span>
                <span>{finding.action}</span>
              </div>
            </div>
            <span className={`badge badge--${finding.severity}`}>{finding.severity}</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{finding.description}</p>
        </div>
      </div>

      <div className="hub-grid">
        <div className="hub-main">
          {/* Affected Records */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Affected Records</h3>
              <button className="btn btn-secondary btn-sm">
                <Download size={14} />
                Export
              </button>
            </div>
            <div className="table-container" style={{ border: 'none' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Department</th>
                    <th>Hire Date</th>
                  </tr>
                </thead>
                <tbody>
                  {finding.affectedRecords?.map(record => (
                    <tr key={record.id}>
                      <td>{record.id}</td>
                      <td>{record.name}</td>
                      <td>{record.department}</td>
                      <td>{record.hire_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {finding.affectedRecords?.length > 5 && (
              <div className="card-body" style={{ borderTop: '1px solid var(--border)', textAlign: 'center' }}>
                <span className="text-muted">Showing 5 of {finding.affected}</span>
              </div>
            )}
          </div>
        </div>

        <div className="hub-sidebar">
          {/* Recommendation */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Recommendation</h3>
            </div>
            <div className="card-body">
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {finding.recommendation}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Review Status</h3>
            </div>
            <div className="card-body">
              {status === 'pending' ? (
                <div className="flex flex-col gap-2">
                  <button className="btn btn-primary" onClick={handleApprove} style={{ width: '100%', justifyContent: 'center' }}>
                    <Check size={16} />
                    Approve Finding
                  </button>
                  <button className="btn btn-secondary" onClick={handleReject} style={{ width: '100%', justifyContent: 'center' }}>
                    <X size={16} />
                    Reject / Not Applicable
                  </button>
                </div>
              ) : (
                <div className={`alert alert--${status === 'approved' ? 'info' : 'warning'}`}>
                  {status === 'approved' ? <Check size={16} /> : <X size={16} />}
                  {status === 'approved' ? 'Finding approved' : 'Finding rejected'}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FindingDetailPage;
