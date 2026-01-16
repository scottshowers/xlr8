/**
 * ProcessingPage.jsx - Step 4: Analysis
 * 
 * Fourth step in the 8-step consultant workflow.
 * Shows visual progress during data analysis with animated steps,
 * cost equivalent banner, and auto-redirect on completion.
 * 
 * Flow: Create Project → Upload Data → Select Playbooks → [ANALYSIS] → Findings → ...
 * 
 * Updated: January 15, 2026 - Phase 4A UX Overhaul (proper rebuild)
 */

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { useProject } from '../context/ProjectContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Processing steps configuration
const PROCESSING_STEPS = [
  { id: 'schema', label: 'Schema Detection', description: 'Identifying tables and columns', icon: '🔍' },
  { id: 'profiling', label: 'Data Profiling', description: 'Analyzing data quality', icon: '📊' },
  { id: 'patterns', label: 'Pattern Analysis', description: 'Finding anomalies', icon: '🔎' },
  { id: 'findings', label: 'Finding Generation', description: 'Creating recommendations', icon: '✨' },
];

const ProcessingPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { jobId: paramJobId } = useParams();
  const { activeProject, customerName } = useProject();

  const jobId = paramJobId || location.state?.jobId;

  // State
  const [currentStep, setCurrentStep] = useState(0);
  const [status, setStatus] = useState('processing'); // processing, complete, error
  const [progress, setProgress] = useState(null);
  const [costEquivalent, setCostEquivalent] = useState({
    records: 0,
    tables: 0,
    hours: 0,
    cost: 0,
  });
  const [error, setError] = useState(null);

  const pollIntervalRef = useRef(null);
  const stepIntervalRef = useRef(null);

  // Poll for job status or simulate
  useEffect(() => {
    if (!jobId) {
      simulateProcessing();
      return;
    }

    pollJobStatus();
    pollIntervalRef.current = setInterval(pollJobStatus, 2000);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (stepIntervalRef.current) clearInterval(stepIntervalRef.current);
    };
  }, [jobId]);

  const pollJobStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/progress/${jobId}`);
      if (!res.ok) throw new Error('Job not found');

      const data = await res.json();
      setProgress(data);

      // Map progress to steps
      const percent = data.progress_percent || 0;
      if (percent < 25) setCurrentStep(0);
      else if (percent < 50) setCurrentStep(1);
      else if (percent < 75) setCurrentStep(2);
      else if (percent < 100) setCurrentStep(3);

      // Update cost equivalent
      if (data.chunks) {
        const rows = data.chunks.rows_so_far || 0;
        const tables = data.chunks.total || 1;
        const hours = Math.round((rows / 500 + tables * 2) * 10) / 10;
        setCostEquivalent({
          records: rows,
          tables,
          hours,
          cost: Math.round(hours * 250),
        });
      }

      // Check for completion
      if (data.status === 'completed') {
        clearInterval(pollIntervalRef.current);
        setCurrentStep(4);
        setStatus('complete');
        setTimeout(() => navigate('/findings'), 1500);
      } else if (data.status === 'failed' || data.status === 'error') {
        clearInterval(pollIntervalRef.current);
        setStatus('error');
        setError(data.error || 'Processing failed');
      }
    } catch (err) {
      console.error('Error polling job:', err);
    }
  };

  const simulateProcessing = () => {
    setCostEquivalent({
      records: 47382,
      tables: 12,
      hours: 17,
      cost: 4250,
    });

    let step = 0;
    stepIntervalRef.current = setInterval(() => {
      step++;
      setCurrentStep(step);

      if (step >= 4) {
        clearInterval(stepIntervalRef.current);
        setStatus('complete');
        setTimeout(() => navigate('/findings'), 1500);
      }
    }, 2000);
  };

  const getStepStatus = (index) => {
    if (index < currentStep) return 'complete';
    if (index === currentStep && status === 'processing') return 'active';
    if (status === 'complete') return 'complete';
    return 'pending';
  };

  return (
    
      <div className="processing-page">
        <PageHeader
          title={customerName || activeProject?.customer || 'Analyzing Data'}
          subtitle={`Step 4 of 8 • ${activeProject?.system_type || 'UKG Pro'} · ${activeProject?.engagement_type || 'Implementation'}`}
        />

        <div className="processing-page__content">
          {/* Main Processing Card */}
          <Card className="processing-page__main-card">
            {/* Spinner / Complete Icon */}
            <div className="processing-page__status-icon">
              {status === 'processing' ? (
                <div className="spinner-icon" />
              ) : status === 'complete' ? (
                <div className="complete-icon">✓</div>
              ) : (
                <div className="error-icon">!</div>
              )}
            </div>

            {/* Title */}
            <h2 className="processing-page__title">
              {status === 'complete' 
                ? 'Analysis Complete!' 
                : status === 'error'
                  ? 'Analysis Failed'
                  : 'Analyzing Your Data'}
            </h2>

            <p className="processing-page__subtitle">
              {status === 'complete'
                ? 'Redirecting to your findings...'
                : status === 'error'
                  ? error || 'An error occurred during processing'
                  : 'This usually takes 2-5 minutes depending on data volume'}
            </p>

            {/* Processing Steps */}
            <div className="processing-page__steps">
              {PROCESSING_STEPS.map((step, index) => {
                const stepStatus = getStepStatus(index);
                return (
                  <div 
                    key={step.id} 
                    className={`processing-step processing-step--${stepStatus}`}
                  >
                    <div className="processing-step__icon">
                      {stepStatus === 'complete' ? '✓' : stepStatus === 'active' ? '⋯' : step.icon}
                    </div>
                    <div className="processing-step__content">
                      <div className="processing-step__label">{step.label}</div>
                      <div className="processing-step__description">{step.description}</div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Manual Navigation */}
            {status === 'complete' && (
              <div className="processing-page__actions">
                <Button variant="primary" onClick={() => navigate('/findings')}>
                  View Findings →
                </Button>
              </div>
            )}

            {status === 'error' && (
              <div className="processing-page__actions">
                <Button variant="primary" onClick={() => navigate('/playbooks/select')}>
                  ← Try Again
                </Button>
              </div>
            )}
          </Card>

          {/* Cost Equivalent Banner */}
          <Card className="processing-page__cost-card">
            <div className="cost-banner">
              <div className="cost-banner__info">
                <h3 className="cost-banner__title">
                  {status === 'complete' ? 'Analysis Complete' : 'Consultant Time Equivalent'}
                </h3>
                <p className="cost-banner__subtitle">
                  {status === 'complete'
                    ? `Analyzed ${costEquivalent.records.toLocaleString()} records across ${costEquivalent.tables} tables`
                    : `Processing ${costEquivalent.records.toLocaleString()} records across ${costEquivalent.tables} tables`}
                </p>
              </div>
              <div className="cost-banner__value">
                <div className="cost-amount">${costEquivalent.cost.toLocaleString()}</div>
                <div className="cost-label">{costEquivalent.hours} hours @ $250/hr</div>
              </div>
            </div>
          </Card>

          {/* Sidebar */}
          <div className="processing-page__sidebar">
            {/* What's Happening Card */}
            <Card className="processing-page__info-card">
              <CardHeader>
                <CardTitle icon="🔬">What's Happening</CardTitle>
              </CardHeader>
              <ul className="info-list">
                <li><strong>Schema Detection</strong> - Identifying data structure and relationships</li>
                <li><strong>Data Profiling</strong> - Analyzing completeness, patterns, and quality</li>
                <li><strong>Pattern Analysis</strong> - Finding anomalies and inconsistencies</li>
                <li><strong>Finding Generation</strong> - Creating actionable recommendations</li>
              </ul>
            </Card>

            {/* Next Step Card */}
            <Card className="processing-page__next-card">
              <div className="next-step-preview">
                <div className="next-step-label">Next Step</div>
                <div className="next-step-title">📊 Findings Dashboard</div>
                <div className="next-step-description">
                  Review prioritized findings with severity ratings and impact analysis.
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    
  );
};

export default ProcessingPage;
