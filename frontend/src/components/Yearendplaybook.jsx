/**
 * YearEndPlaybook - Year-End Checklist Runner
 * 
 * Wizard flow:
 * 1. Check document readiness (query what's uploaded for project)
 * 2. Show readiness status with missing/available docs
 * 3. Generate workbook via backend
 * 4. Provide download
 * 5. Allow re-run after modifications
 */

import React, { useState, useEffect } from 'react';
import api from '../services/api';

// Brand Colors
const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  white: '#f6f5fa',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

// Document categories the playbook looks for
const DOCUMENT_CATEGORIES = [
  { id: 'company_tax', name: 'Company Tax Verification', required: true, keywords: ['tax verification', 'company tax', 'fein', 'tax code'] },
  { id: 'earnings', name: 'Earnings Codes / Tax Categories', required: true, keywords: ['earnings', 'earning code', 'tax category', 'earnings tax'] },
  { id: 'deductions', name: 'Deduction Codes', required: true, keywords: ['deduction', 'benefit code', 'deduction tax'] },
  { id: 'workers_comp', name: 'Workers Compensation Rates', required: false, keywords: ['workers comp', 'work comp', 'wc rate', 'risk rate'] },
  { id: 'outstanding_checks', name: 'Outstanding Checks', required: false, keywords: ['outstanding check', 'undelivered', 'payment services'] },
  { id: 'arrears', name: 'Arrears Report', required: false, keywords: ['arrears', 'outstanding arrears'] },
  { id: 'employee_data', name: 'Employee Data / Census', required: false, keywords: ['employee', 'census', 'headcount'] },
];

export default function YearEndPlaybook({ project, projectName, customerName, onClose }) {
  const [step, setStep] = useState('checking'); // checking, ready, generating, complete, error
  const [documents, setDocuments] = useState([]);
  const [docStatus, setDocStatus] = useState({});
  const [generateProgress, setGenerateProgress] = useState(0);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [error, setError] = useState(null);
  const [findings, setFindings] = useState(null);

  useEffect(() => {
    checkDocumentReadiness();
  }, [project]);

  const checkDocumentReadiness = async () => {
    setStep('checking');
    try {
      // Get all documents for this project
      const res = await api.get(`/status/documents?project_id=${project.id}`);
      const docs = res.data?.documents || [];
      setDocuments(docs);

      // Match documents against categories
      const status = {};
      DOCUMENT_CATEGORIES.forEach(cat => {
        const matched = docs.filter(doc => {
          const filename = (doc.filename || doc.source || '').toLowerCase();
          const content = (doc.content_preview || '').toLowerCase();
          return cat.keywords.some(kw => 
            filename.includes(kw.toLowerCase()) || content.includes(kw.toLowerCase())
          );
        });
        status[cat.id] = {
          found: matched.length > 0,
          count: matched.length,
          documents: matched,
          required: cat.required,
        };
      });
      setDocStatus(status);
      setStep('ready');
    } catch (err) {
      console.error('Error checking documents:', err);
      setError('Failed to check document readiness');
      setStep('error');
    }
  };

  const generateWorkbook = async () => {
    setStep('generating');
    setGenerateProgress(10);
    
    try {
      // Call backend to generate workbook
      setGenerateProgress(30);
      
      const res = await api.post('/playbooks/year-end/generate', {
        project_id: project.id,
        project_name: projectName,
        customer_name: customerName,
      }, {
        responseType: 'blob',
        timeout: 300000, // 5 min timeout for large analysis
        onDownloadProgress: (progressEvent) => {
          const progress = Math.round((progressEvent.loaded * 100) / (progressEvent.total || progressEvent.loaded));
          setGenerateProgress(30 + (progress * 0.6)); // 30-90%
        }
      });

      setGenerateProgress(95);

      // Create download URL
      const blob = new Blob([res.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      setDownloadUrl(url);
      
      // Try to get findings from headers
      const findingsHeader = res.headers['x-findings-summary'];
      if (findingsHeader) {
        try {
          setFindings(JSON.parse(decodeURIComponent(findingsHeader)));
        } catch (e) {
          // Ignore parse errors
        }
      }

      setGenerateProgress(100);
      setStep('complete');
    } catch (err) {
      console.error('Error generating workbook:', err);
      setError(err.response?.data?.detail || 'Failed to generate workbook');
      setStep('error');
    }
  };

  const downloadWorkbook = () => {
    if (downloadUrl) {
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${customerName.replace(/[^a-zA-Z0-9]/g, '_')}_Year_End_Checklist_2025.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const styles = {
    container: {
      maxWidth: '900px',
      margin: '0 auto',
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      marginBottom: '2rem',
    },
    backButton: {
      padding: '0.5rem 1rem',
      background: 'white',
      border: '1px solid #e1e8ed',
      borderRadius: '8px',
      color: COLORS.textLight,
      fontWeight: '600',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.75rem',
      fontWeight: '700',
      color: COLORS.text,
      margin: 0,
    },
    subtitle: {
      color: COLORS.textLight,
      marginTop: '0.25rem',
    },
    card: {
      background: 'white',
      borderRadius: '16px',
      padding: '2rem',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      marginBottom: '1.5rem',
    },
    cardTitle: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.1rem',
      fontWeight: '700',
      color: COLORS.text,
      marginBottom: '1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    docList: {
      display: 'flex',
      flexDirection: 'column',
      gap: '0.75rem',
    },
    docItem: (found, required) => ({
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.75rem 1rem',
      background: found ? '#f0fdf4' : (required ? '#fef2f2' : '#f8fafc'),
      borderRadius: '8px',
      border: `1px solid ${found ? '#86efac' : (required ? '#fecaca' : '#e1e8ed')}`,
    }),
    docName: {
      fontWeight: '600',
      color: COLORS.text,
    },
    docBadge: (found) => ({
      fontSize: '0.75rem',
      padding: '0.25rem 0.5rem',
      borderRadius: '4px',
      fontWeight: '600',
      background: found ? '#dcfce7' : '#fee2e2',
      color: found ? '#166534' : '#b91c1c',
    }),
    requiredTag: {
      fontSize: '0.7rem',
      color: '#dc2626',
      fontWeight: '600',
      marginLeft: '0.5rem',
    },
    progressBar: {
      width: '100%',
      height: '8px',
      background: '#e1e8ed',
      borderRadius: '4px',
      overflow: 'hidden',
      marginBottom: '1rem',
    },
    progressFill: (progress) => ({
      width: `${progress}%`,
      height: '100%',
      background: COLORS.grassGreen,
      transition: 'width 0.3s ease',
    }),
    progressText: {
      textAlign: 'center',
      color: COLORS.textLight,
      fontSize: '0.9rem',
    },
    actions: {
      display: 'flex',
      gap: '1rem',
      justifyContent: 'flex-end',
      marginTop: '1.5rem',
    },
    primaryBtn: {
      padding: '0.75rem 1.5rem',
      background: COLORS.grassGreen,
      border: 'none',
      borderRadius: '8px',
      color: 'white',
      fontWeight: '600',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    secondaryBtn: {
      padding: '0.75rem 1.5rem',
      background: 'white',
      border: `1px solid ${COLORS.grassGreen}`,
      borderRadius: '8px',
      color: COLORS.grassGreen,
      fontWeight: '600',
      cursor: 'pointer',
    },
    disabledBtn: {
      padding: '0.75rem 1.5rem',
      background: '#e1e8ed',
      border: 'none',
      borderRadius: '8px',
      color: '#9ca3af',
      fontWeight: '600',
      cursor: 'not-allowed',
    },
    successBox: {
      background: '#f0fdf4',
      border: '1px solid #86efac',
      borderRadius: '12px',
      padding: '1.5rem',
      textAlign: 'center',
    },
    successIcon: {
      fontSize: '3rem',
      marginBottom: '1rem',
    },
    successTitle: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.25rem',
      fontWeight: '700',
      color: '#166534',
      marginBottom: '0.5rem',
    },
    errorBox: {
      background: '#fef2f2',
      border: '1px solid #fecaca',
      borderRadius: '12px',
      padding: '1.5rem',
      textAlign: 'center',
    },
    errorIcon: {
      fontSize: '3rem',
      marginBottom: '1rem',
    },
    errorTitle: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.25rem',
      fontWeight: '700',
      color: '#b91c1c',
      marginBottom: '0.5rem',
    },
    findingsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
      gap: '1rem',
      marginTop: '1rem',
    },
    findingStat: {
      textAlign: 'center',
      padding: '1rem',
      background: '#f8fafc',
      borderRadius: '8px',
    },
    findingValue: {
      fontSize: '1.5rem',
      fontWeight: '700',
      color: COLORS.grassGreen,
    },
    findingLabel: {
      fontSize: '0.8rem',
      color: COLORS.textLight,
    },
  };

  const requiredMissing = DOCUMENT_CATEGORIES
    .filter(cat => cat.required && !docStatus[cat.id]?.found)
    .length;

  const totalFound = Object.values(docStatus).filter(s => s.found).length;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>📅 Year-End Checklist</h1>
          <p style={styles.subtitle}>
            {customerName} → {projectName}
          </p>
        </div>
        <button style={styles.backButton} onClick={onClose}>
          ← Back to Playbooks
        </button>
      </div>

      {/* Step: Checking */}
      {step === 'checking' && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>🔍 Checking Document Readiness...</h3>
          <div style={styles.progressBar}>
            <div style={styles.progressFill(50)} />
          </div>
          <p style={styles.progressText}>Scanning project documents...</p>
        </div>
      )}

      {/* Step: Ready */}
      {step === 'ready' && (
        <>
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>📄 Document Readiness</h3>
            <p style={{ color: COLORS.textLight, marginBottom: '1rem' }}>
              Found {totalFound} of {DOCUMENT_CATEGORIES.length} document categories. 
              {requiredMissing > 0 && (
                <span style={{ color: '#dc2626', fontWeight: '600' }}>
                  {' '}{requiredMissing} required categories missing.
                </span>
              )}
            </p>
            
            <div style={styles.docList}>
              {DOCUMENT_CATEGORIES.map(cat => {
                const status = docStatus[cat.id] || { found: false, count: 0 };
                return (
                  <div key={cat.id} style={styles.docItem(status.found, cat.required)}>
                    <div>
                      <span style={styles.docName}>{cat.name}</span>
                      {cat.required && <span style={styles.requiredTag}>REQUIRED</span>}
                      {status.found && status.count > 0 && (
                        <span style={{ fontSize: '0.8rem', color: COLORS.textLight, marginLeft: '0.5rem' }}>
                          ({status.count} doc{status.count > 1 ? 's' : ''} matched)
                        </span>
                      )}
                    </div>
                    <span style={styles.docBadge(status.found)}>
                      {status.found ? '✓ Found' : '✗ Missing'}
                    </span>
                  </div>
                );
              })}
            </div>

            <div style={styles.actions}>
              <button style={styles.secondaryBtn} onClick={checkDocumentReadiness}>
                🔄 Re-scan
              </button>
              <button 
                style={requiredMissing > 0 ? styles.disabledBtn : styles.primaryBtn}
                onClick={generateWorkbook}
                disabled={requiredMissing > 0}
              >
                {requiredMissing > 0 ? 'Upload Required Docs First' : '🚀 Generate Workbook'}
              </button>
            </div>
          </div>

          {requiredMissing > 0 && (
            <div style={{ ...styles.card, background: '#fffbeb', border: '1px solid #fcd34d' }}>
              <h3 style={{ ...styles.cardTitle, color: '#92400e' }}>⚠️ Missing Required Documents</h3>
              <p style={{ color: '#92400e' }}>
                Please upload the missing required documents via <strong>Data → Upload Files</strong> before generating the workbook.
              </p>
            </div>
          )}
        </>
      )}

      {/* Step: Generating */}
      {step === 'generating' && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>⚙️ Generating Workbook...</h3>
          <div style={styles.progressBar}>
            <div style={styles.progressFill(generateProgress)} />
          </div>
          <p style={styles.progressText}>
            {generateProgress < 30 && 'Querying documents...'}
            {generateProgress >= 30 && generateProgress < 60 && 'Analyzing data with AI...'}
            {generateProgress >= 60 && generateProgress < 90 && 'Building workbook...'}
            {generateProgress >= 90 && 'Finalizing...'}
          </p>
        </div>
      )}

      {/* Step: Complete */}
      {step === 'complete' && (
        <>
          <div style={styles.successBox}>
            <div style={styles.successIcon}>✅</div>
            <h3 style={styles.successTitle}>Workbook Generated Successfully!</h3>
            <p style={{ color: '#166534', marginBottom: '1.5rem' }}>
              Your Year-End Checklist workbook is ready for download.
            </p>
            <button style={styles.primaryBtn} onClick={downloadWorkbook}>
              📥 Download Workbook
            </button>
          </div>

          {findings && (
            <div style={{ ...styles.card, marginTop: '1.5rem' }}>
              <h3 style={styles.cardTitle}>📊 Quick Findings</h3>
              <div style={styles.findingsGrid}>
                {findings.total_actions && (
                  <div style={styles.findingStat}>
                    <div style={styles.findingValue}>{findings.total_actions}</div>
                    <div style={styles.findingLabel}>Total Actions</div>
                  </div>
                )}
                {findings.critical_items && (
                  <div style={{ ...styles.findingStat, background: '#fef2f2' }}>
                    <div style={{ ...styles.findingValue, color: '#dc2626' }}>{findings.critical_items}</div>
                    <div style={styles.findingLabel}>Critical Items</div>
                  </div>
                )}
                {findings.documents_analyzed && (
                  <div style={styles.findingStat}>
                    <div style={styles.findingValue}>{findings.documents_analyzed}</div>
                    <div style={styles.findingLabel}>Docs Analyzed</div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div style={{ ...styles.card, marginTop: '1.5rem' }}>
            <h3 style={styles.cardTitle}>🔄 Next Steps</h3>
            <ol style={{ color: COLORS.textLight, lineHeight: '1.8', paddingLeft: '1.25rem' }}>
              <li>Download and review the workbook</li>
              <li>Fact-check findings against source documents</li>
              <li>Add consultant notes and recommendations</li>
              <li>If modifications needed, re-upload updated documents and regenerate</li>
              <li>Deliver to customer</li>
            </ol>
            <div style={styles.actions}>
              <button style={styles.secondaryBtn} onClick={() => setStep('ready')}>
                ← Back to Readiness
              </button>
              <button style={styles.primaryBtn} onClick={generateWorkbook}>
                🔄 Regenerate
              </button>
            </div>
          </div>
        </>
      )}

      {/* Step: Error */}
      {step === 'error' && (
        <div style={styles.errorBox}>
          <div style={styles.errorIcon}>❌</div>
          <h3 style={styles.errorTitle}>Generation Failed</h3>
          <p style={{ color: '#b91c1c', marginBottom: '1.5rem' }}>
            {error || 'An unexpected error occurred.'}
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            <button style={styles.secondaryBtn} onClick={() => setStep('ready')}>
              ← Back
            </button>
            <button style={styles.primaryBtn} onClick={generateWorkbook}>
              🔄 Retry
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
