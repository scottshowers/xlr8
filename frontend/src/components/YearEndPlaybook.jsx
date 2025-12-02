/**
 * YearEndPlaybook - Interactive Year-End Checklist
 * 
 * Guided journey through Year-End actions:
 * - Shows all steps/actions from parsed UKG doc
 * - Auto-scans for relevant documents per action
 * - Tracks status (not started, in progress, complete, n/a)
 * - Consultant can add notes, override status
 * - Export current state anytime
 */

import React, { useState, useEffect } from 'react';
import api from '../services/api';

// Brand Colors
const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  clearwater: '#b2d6de',
  turkishSea: '#285390',
  electricBlue: '#2766b1',
  iceFlow: '#c9d3d4',
  white: '#f6f5fa',
  silver: '#a2a1a0',
  scarletSage: '#993c44',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

const STATUS_OPTIONS = [
  { value: 'not_started', label: 'Not Started', color: '#9ca3af', bg: '#f3f4f6' },
  { value: 'in_progress', label: 'In Progress', color: '#d97706', bg: '#fef3c7' },
  { value: 'complete', label: 'Complete', color: '#059669', bg: '#d1fae5' },
  { value: 'na', label: 'N/A', color: '#6b7280', bg: '#e5e7eb' },
  { value: 'blocked', label: 'Blocked', color: '#dc2626', bg: '#fee2e2' },
];

// Action Card Component
function ActionCard({ action, stepNumber, progress, projectId, onUpdate }) {
  const [expanded, setExpanded] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [notes, setNotes] = useState(progress?.notes || '');
  const [localStatus, setLocalStatus] = useState(progress?.status || 'not_started');
  const [localDocsFound, setLocalDocsFound] = useState(progress?.documents_found || []);
  const fileInputRef = React.useRef(null);
  
  // Sync local docs with progress prop - MUST be before any conditional returns
  React.useEffect(() => {
    setLocalDocsFound(progress?.documents_found || []);
  }, [progress?.documents_found]);
  
  // Safety check - if no action, don't render (AFTER all hooks)
  if (!action) {
    return null;
  }
  
  const findings = progress?.findings;
  const reportsNeeded = action.reports_needed || [];
  const expectedCount = reportsNeeded.length || 1;
  
  const statusConfig = STATUS_OPTIONS.find(s => s.value === localStatus) || STATUS_OPTIONS[0];

  const handleScan = async () => {
    setScanning(true);
    try {
      const res = await api.post(`/playbooks/year-end/scan/${projectId}/${action.action_id}`);
      console.log('[SCAN] Response:', res.data);
      if (res.data) {
        const newDocs = res.data.documents?.map(d => d.filename) || [];
        console.log('[SCAN] Found docs:', newDocs);
        setLocalDocsFound(newDocs);
        setLocalStatus(res.data.suggested_status);
        onUpdate(action.action_id, {
          status: res.data.suggested_status,
          findings: res.data.findings,
          documents_found: newDocs
        });
      }
    } catch (err) {
      console.error('Scan failed:', err);
    } finally {
      setScanning(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    setUploading(true);
    setUploadStatus(null);
    
    try {
      const jobIds = [];
      
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('project', projectId);
        
        const res = await api.post('/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        if (res.data?.job_id) {
          jobIds.push(res.data.job_id);
        }
      }
      
      setUploading(false);
      setUploadStatus('processing');
      
      const pollJobs = async () => {
        let allComplete = false;
        let attempts = 0;
        const maxAttempts = 60;
        
        while (!allComplete && attempts < maxAttempts) {
          await new Promise(r => setTimeout(r, 2000));
          attempts++;
          
          try {
            const jobsRes = await api.get('/jobs');
            const jobs = jobsRes.data?.jobs || [];
            
            const ourJobs = jobs.filter(j => jobIds.includes(j.id));
            allComplete = ourJobs.length > 0 && ourJobs.every(j => 
              j.status === 'completed' || j.status === 'failed'
            );
            
            const failed = ourJobs.filter(j => j.status === 'failed');
            if (failed.length > 0) {
              setUploadStatus('error');
              setTimeout(() => setUploadStatus(null), 3000);
              return;
            }
          } catch (err) {
            console.error('Job poll failed:', err);
          }
        }
        
        if (allComplete) {
          setUploadStatus('scanning');
          await handleScan();
          setUploadStatus('success');
          setTimeout(() => setUploadStatus(null), 2000);
        } else {
          setUploadStatus(null);
        }
      };
      
      pollJobs();
      
    } catch (err) {
      console.error('Upload failed:', err);
      setUploadStatus('error');
      setTimeout(() => setUploadStatus(null), 3000);
      setUploading(false);
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleStatusChange = async (newStatus) => {
    setLocalStatus(newStatus);
    try {
      await api.post(`/playbooks/year-end/progress/${projectId}/${action.action_id}`, {
        status: newStatus,
        notes: notes,
        findings: findings
      });
      onUpdate(action.action_id, { status: newStatus });
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleNotesBlur = async () => {
    try {
      await api.post(`/playbooks/year-end/progress/${projectId}/${action.action_id}`, {
        status: localStatus,
        notes: notes,
        findings: findings
      });
      onUpdate(action.action_id, { notes });
    } catch (err) {
      console.error('Failed to save notes:', err);
    }
  };

  const getUploadButtonContent = () => {
    if (uploading) return '⏳ Uploading...';
    if (uploadStatus === 'processing') return '⏳ Processing...';
    if (uploadStatus === 'scanning') return '🔍 Scanning...';
    if (uploadStatus === 'success') return '✓ Done!';
    if (uploadStatus === 'error') return '✗ Failed';
    return (
      <>
        📤 Upload Document
        <span style={styles.docCount}>
          {localDocsFound.length}/{expectedCount}
        </span>
      </>
    );
  };

  const getUploadButtonStyle = () => {
    if (uploadStatus === 'success') {
      return { ...styles.uploadBtn, background: '#C6EFCE', color: '#006600' };
    }
    if (uploadStatus === 'error') {
      return { ...styles.uploadBtn, background: '#FFC7CE', color: '#9C0006' };
    }
    if (uploadStatus === 'processing' || uploadStatus === 'scanning') {
      return { ...styles.uploadBtn, background: '#FFEB9C', color: '#9C6500' };
    }
    return styles.uploadBtn;
  };

  const styles = {
    card: {
      background: 'white',
      borderRadius: '10px',
      border: '1px solid #e1e8ed',
      marginBottom: '0.75rem',
      overflow: 'hidden',
    },
    header: {
      display: 'flex',
      alignItems: 'flex-start',
      padding: '1rem',
      cursor: 'pointer',
      gap: '1rem',
    },
    actionId: {
      fontFamily: "'Ubuntu Mono', monospace",
      fontWeight: '700',
      fontSize: '0.9rem',
      color: COLORS.text,
      background: '#f0f4f7',
      padding: '0.25rem 0.5rem',
      borderRadius: '4px',
      flexShrink: 0,
    },
    content: {
      flex: 1,
    },
    description: {
      fontSize: '0.9rem',
      color: COLORS.text,
      lineHeight: '1.4',
      marginBottom: '0.5rem',
    },
    meta: {
      display: 'flex',
      gap: '1rem',
      flexWrap: 'wrap',
      alignItems: 'center',
    },
    dueDate: {
      fontSize: '0.75rem',
      color: '#dc2626',
      fontWeight: '600',
    },
    actionType: {
      fontSize: '0.7rem',
      padding: '0.15rem 0.4rem',
      borderRadius: '3px',
      fontWeight: '600',
      textTransform: 'uppercase',
      background: action.action_type === 'required' ? '#fee2e2' : '#e0f2fe',
      color: action.action_type === 'required' ? '#b91c1c' : '#0369a1',
    },
    statusBadge: {
      fontSize: '0.75rem',
      padding: '0.25rem 0.5rem',
      borderRadius: '4px',
      fontWeight: '600',
      background: statusConfig.bg,
      color: statusConfig.color,
      marginLeft: 'auto',
    },
    expandIcon: {
      fontSize: '1.25rem',
      color: COLORS.textLight,
      transition: 'transform 0.2s',
      transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
    },
    expandedContent: {
      padding: '0 1rem 1rem 1rem',
      borderTop: '1px solid #e1e8ed',
      background: '#fafbfc',
    },
    section: {
      marginBottom: '1rem',
    },
    sectionTitle: {
      fontSize: '0.75rem',
      fontWeight: '700',
      color: COLORS.textLight,
      textTransform: 'uppercase',
      marginBottom: '0.5rem',
    },
    findingsBox: {
      background: findings?.complete ? '#d1fae5' : '#fef3c7',
      border: `1px solid ${findings?.complete ? '#86efac' : '#fcd34d'}`,
      borderRadius: '8px',
      padding: '0.75rem',
    },
    keyValue: {
      display: 'flex',
      justifyContent: 'space-between',
      fontSize: '0.85rem',
      marginBottom: '0.25rem',
    },
    keyLabel: {
      color: COLORS.textLight,
    },
    keyVal: {
      fontWeight: '600',
      color: COLORS.text,
    },
    issuesList: {
      margin: '0.5rem 0 0 0',
      paddingLeft: '1.25rem',
    },
    issue: {
      fontSize: '0.85rem',
      color: '#b91c1c',
      marginBottom: '0.25rem',
    },
    docsFound: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '0.5rem',
    },
    docBadge: {
      fontSize: '0.75rem',
      padding: '0.25rem 0.5rem',
      background: '#dbeafe',
      color: '#1e40af',
      borderRadius: '4px',
    },
    statusSelect: {
      display: 'flex',
      gap: '0.5rem',
      flexWrap: 'wrap',
    },
    statusBtn: (isActive, config) => ({
      padding: '0.4rem 0.75rem',
      fontSize: '0.8rem',
      fontWeight: '600',
      border: `2px solid ${isActive ? config.color : '#e1e8ed'}`,
      background: isActive ? config.bg : 'white',
      color: isActive ? config.color : COLORS.textLight,
      borderRadius: '6px',
      cursor: 'pointer',
    }),
    notesArea: {
      width: '100%',
      padding: '0.5rem',
      border: '1px solid #e1e8ed',
      borderRadius: '6px',
      fontSize: '0.85rem',
      minHeight: '60px',
      resize: 'vertical',
      fontFamily: 'inherit',
    },
    buttonRow: {
      display: 'flex',
      gap: '0.75rem',
      flexWrap: 'wrap',
    },
    uploadBtn: {
      padding: '0.5rem 1rem',
      background: COLORS.clearwater,
      color: COLORS.text,
      border: 'none',
      borderRadius: '6px',
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      transition: 'background 0.2s, color 0.2s',
    },
    scanBtn: {
      padding: '0.5rem 1rem',
      background: COLORS.grassGreen,
      color: 'white',
      border: 'none',
      borderRadius: '6px',
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    reportsNeeded: {
      fontSize: '0.8rem',
      color: COLORS.textLight,
      fontStyle: 'italic',
    },
    hiddenInput: {
      display: 'none',
    },
    docCount: {
      fontSize: '0.7rem',
      background: COLORS.turkishSea,
      color: 'white',
      padding: '0.1rem 0.4rem',
      borderRadius: '10px',
    },
  };

  return (
    <div style={styles.card}>
      <div style={styles.header} onClick={() => setExpanded(!expanded)}>
        <span style={styles.actionId}>{action.action_id || '?'}</span>
        <div style={styles.content}>
          <div style={styles.description}>{action.description || 'No description'}</div>
          <div style={styles.meta}>
            {action.due_date && (
              <span style={styles.dueDate}>📅 Due: {action.due_date}</span>
            )}
            <span style={styles.actionType}>{action.action_type || 'unknown'}</span>
            {localDocsFound.length > 0 && (
              <span style={{ fontSize: '0.75rem', color: COLORS.grassGreen }}>
                ✓ {localDocsFound.length} doc{localDocsFound.length > 1 ? 's' : ''} found
              </span>
            )}
          </div>
        </div>
        <span style={styles.statusBadge}>{statusConfig.label}</span>
        <span style={styles.expandIcon}>{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && (
        <div style={styles.expandedContent}>
          {reportsNeeded.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Reports Needed</div>
              <div style={styles.reportsNeeded}>
                {reportsNeeded.join(', ')}
              </div>
            </div>
          )}

          <div style={styles.section}>
            <div style={styles.buttonRow}>
              <input
                type="file"
                ref={fileInputRef}
                style={styles.hiddenInput}
                onChange={handleFileChange}
                multiple
                accept=".pdf,.xlsx,.xls,.csv,.docx,.doc,.txt"
              />
              <button 
                style={getUploadButtonStyle()} 
                onClick={(e) => { e.stopPropagation(); handleUploadClick(); }}
                disabled={uploading || scanning || uploadStatus === 'processing' || uploadStatus === 'scanning'}
              >
                {getUploadButtonContent()}
              </button>
              <button 
                style={styles.scanBtn} 
                onClick={(e) => { e.stopPropagation(); handleScan(); }}
                disabled={scanning || uploading}
              >
                {scanning ? '⏳ Scanning...' : '🔍 Scan Documents'}
              </button>
            </div>
          </div>

          {localDocsFound.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Documents Found ({localDocsFound.length})</div>
              <div style={styles.docsFound}>
                {localDocsFound.map((doc, i) => (
                  <span key={i} style={styles.docBadge}>📄 {doc}</span>
                ))}
              </div>
            </div>
          )}

          {findings && typeof findings === 'object' && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>AI Findings</div>
              <div style={styles.findingsBox}>
                {findings.summary && (
                  <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem' }}>
                    {typeof findings.summary === 'string' ? findings.summary : JSON.stringify(findings.summary)}
                  </p>
                )}
                {findings.key_values && typeof findings.key_values === 'object' && !Array.isArray(findings.key_values) && Object.keys(findings.key_values).length > 0 && (
                  <div style={{ marginBottom: '0.5rem' }}>
                    {Object.entries(findings.key_values).map(([key, val]) => (
                      <div key={key} style={styles.keyValue}>
                        <span style={styles.keyLabel}>{String(key)}:</span>
                        <span style={styles.keyVal}>
                          {val === null || val === undefined ? '-' : (typeof val === 'object' ? JSON.stringify(val) : String(val))}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {Array.isArray(findings.issues) && findings.issues.length > 0 && (
                  <ul style={styles.issuesList}>
                    {findings.issues.map((issue, i) => (
                      <li key={i} style={styles.issue}>
                        ⚠️ {typeof issue === 'string' ? issue : JSON.stringify(issue)}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          <div style={styles.section}>
            <div style={styles.sectionTitle}>Status</div>
            <div style={styles.statusSelect}>
              {STATUS_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  style={styles.statusBtn(localStatus === opt.value, opt)}
                  onClick={(e) => { e.stopPropagation(); handleStatusChange(opt.value); }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div style={styles.section}>
            <div style={styles.sectionTitle}>Consultant Notes</div>
            <textarea
              style={styles.notesArea}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              onBlur={handleNotesBlur}
              onClick={(e) => e.stopPropagation()}
              placeholder="Add notes, findings, or follow-up items..."
            />
          </div>
        </div>
      )}
    </div>
  );
}

// Step Accordion Component - WITH FULL SAFETY CHECKS
function StepAccordion({ step, progress, projectId, onUpdate }) {
  const [expanded, setExpanded] = useState(true);
  
  // CRITICAL: Safety check FIRST before any property access
  if (!step) {
    console.warn('[StepAccordion] Received undefined step, skipping render');
    return null;
  }
  
  const actions = step.actions || [];
  const completedCount = actions.filter(a => 
    a && (progress[a.action_id]?.status === 'complete' || progress[a.action_id]?.status === 'na')
  ).length;
  const totalCount = actions.length;
  const allComplete = totalCount > 0 && completedCount === totalCount;

  // Safe phase check - MUST be after null check
  const isBefore = step.phase === 'before_final_payroll';

  const styles = {
    container: {
      marginBottom: '1.5rem',
    },
    header: {
      display: 'flex',
      alignItems: 'center',
      padding: '1rem',
      background: allComplete ? '#d1fae5' : 'white',
      borderRadius: '12px',
      border: '1px solid #e1e8ed',
      cursor: 'pointer',
      gap: '1rem',
    },
    stepNumber: {
      fontFamily: "'Sora', sans-serif",
      fontWeight: '700',
      fontSize: '1rem',
      color: 'white',
      background: allComplete ? '#059669' : COLORS.grassGreen,
      width: '36px',
      height: '36px',
      borderRadius: '8px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    },
    stepName: {
      flex: 1,
      fontFamily: "'Sora', sans-serif",
      fontWeight: '600',
      fontSize: '1rem',
      color: COLORS.text,
    },
    progressText: {
      fontSize: '0.85rem',
      color: COLORS.textLight,
    },
    phaseBadge: {
      fontSize: '0.7rem',
      padding: '0.2rem 0.5rem',
      borderRadius: '4px',
      fontWeight: '600',
      textTransform: 'uppercase',
      background: isBefore ? '#dbeafe' : '#fae8ff',
      color: isBefore ? '#1e40af' : '#86198f',
    },
    expandIcon: {
      fontSize: '1.25rem',
      color: COLORS.textLight,
    },
    actionsContainer: {
      marginTop: '0.75rem',
      paddingLeft: '1rem',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.header} onClick={() => setExpanded(!expanded)}>
        <div style={styles.stepNumber}>{step.step_number || '?'}</div>
        <div style={styles.stepName}>{step.step_name || 'Unknown Step'}</div>
        <span style={styles.phaseBadge}>
          {isBefore ? 'Before Final' : 'After Final'}
        </span>
        <span style={styles.progressText}>
          {completedCount}/{totalCount} {allComplete && '✓'}
        </span>
        <span style={styles.expandIcon}>{expanded ? '▼' : '▶'}</span>
      </div>
      
      {expanded && (
        <div style={styles.actionsContainer}>
          {actions.map(action => action ? (
            <ActionCard
              key={action.action_id}
              action={action}
              stepNumber={step.step_number}
              progress={progress[action.action_id] || {}}
              projectId={projectId}
              onUpdate={onUpdate}
            />
          ) : null)}
        </div>
      )}
    </div>
  );
}

// Main Component
export default function YearEndPlaybook({ project, projectName, customerName, onClose }) {
  const [structure, setStructure] = useState(null);
  const [progress, setProgress] = useState({});
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [activePhase, setActivePhase] = useState('all');

  // SAFETY: Only load if project exists
  useEffect(() => {
    if (project?.id) {
      loadPlaybook();
    }
  }, [project]);

  const loadPlaybook = async () => {
    setLoading(true);
    try {
      const [structRes, progressRes] = await Promise.all([
        api.get('/playbooks/year-end/structure'),
        api.get(`/playbooks/year-end/progress/${project.id}`)
      ]);
      
      setStructure(structRes.data);
      setProgress(progressRes.data?.progress || {});
    } catch (err) {
      console.error('Failed to load playbook:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = (actionId, updates) => {
    setProgress(prev => ({
      ...prev,
      [actionId]: { ...prev[actionId], ...updates }
    }));
  };

  const handleReset = async () => {
    if (!window.confirm('Reset all progress for this playbook? This cannot be undone.')) {
      return;
    }
    
    try {
      await api.delete(`/playbooks/year-end/progress/${project.id}`);
      setProgress({});
      alert('Progress reset. Refreshing...');
      window.location.reload();
    } catch (err) {
      console.error('Reset failed:', err);
      alert('Failed to reset progress');
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await api.get(
        `/playbooks/year-end/export/${project.id}?customer_name=${encodeURIComponent(customerName || 'Customer')}`,
        { responseType: 'blob' }
      );
      
      const blob = new Blob([res.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${(customerName || 'Customer').replace(/[^a-zA-Z0-9]/g, '_')}_Year_End_Progress.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  // Calculate progress stats
  const totalActions = structure?.total_actions || 0;
  const completedActions = Object.values(progress).filter(p => 
    p.status === 'complete' || p.status === 'na'
  ).length;
  const progressPercent = totalActions > 0 ? Math.round((completedActions / totalActions) * 100) : 0;

  // Filter steps by phase
  const filteredSteps = structure?.steps?.filter(step => {
    if (activePhase === 'all') return true;
    return step.phase === activePhase;
  }) || [];

  const styles = {
    container: {
      maxWidth: '1000px',
      margin: '0 auto',
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      marginBottom: '1.5rem',
      flexWrap: 'wrap',
      gap: '1rem',
    },
    titleSection: {},
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.75rem',
      fontWeight: '700',
      color: COLORS.text,
      margin: 0,
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    subtitle: {
      color: COLORS.textLight,
      marginTop: '0.25rem',
    },
    headerActions: {
      display: 'flex',
      gap: '0.75rem',
    },
    backBtn: {
      padding: '0.5rem 1rem',
      background: 'white',
      border: '1px solid #e1e8ed',
      borderRadius: '8px',
      color: COLORS.textLight,
      fontWeight: '600',
      cursor: 'pointer',
    },
    resetBtn: {
      padding: '0.5rem 1rem',
      background: '#fee2e2',
      border: '1px solid #fecaca',
      borderRadius: '8px',
      color: '#dc2626',
      fontWeight: '600',
      cursor: 'pointer',
    },
    exportBtn: {
      padding: '0.5rem 1rem',
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
    progressCard: {
      background: 'white',
      borderRadius: '12px',
      padding: '1.25rem',
      marginBottom: '1.5rem',
      border: '1px solid #e1e8ed',
    },
    progressBar: {
      height: '12px',
      background: '#e1e8ed',
      borderRadius: '6px',
      overflow: 'hidden',
      marginBottom: '0.75rem',
    },
    progressFill: {
      height: '100%',
      background: `linear-gradient(90deg, ${COLORS.grassGreen}, #6aa84f)`,
      borderRadius: '6px',
      transition: 'width 0.3s ease',
      width: `${progressPercent}%`,
    },
    progressStats: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    progressText: {
      fontWeight: '600',
      color: COLORS.text,
    },
    progressPercent: {
      fontSize: '1.5rem',
      fontWeight: '700',
      color: COLORS.grassGreen,
    },
    phaseFilter: {
      display: 'flex',
      gap: '0.5rem',
      marginBottom: '1.5rem',
    },
    phaseBtn: (isActive) => ({
      padding: '0.5rem 1rem',
      background: isActive ? COLORS.grassGreen : 'white',
      border: `1px solid ${isActive ? COLORS.grassGreen : '#e1e8ed'}`,
      borderRadius: '20px',
      color: isActive ? 'white' : COLORS.textLight,
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
    }),
    loadingState: {
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '300px',
      color: COLORS.textLight,
      gap: '1rem',
    },
  };

  // SAFETY CHECK: If no project, show error
  if (!project?.id) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingState}>
          <span>Error: No project selected. Please go back and select a project.</span>
          <button style={styles.backBtn} onClick={onClose}>← Back</button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingState}>
          <span>Loading Year-End Checklist...</span>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.titleSection}>
          <h1 style={styles.title}>📅 Year-End Checklist</h1>
          <p style={styles.subtitle}>
            {customerName || 'Customer'} → {projectName || 'Project'}
          </p>
        </div>
        <div style={styles.headerActions}>
          <button style={styles.backBtn} onClick={onClose}>
            ← Back
          </button>
          <button 
            style={styles.resetBtn} 
            onClick={handleReset}
            title="Reset all progress for this project"
          >
            🔄 Reset
          </button>
          <button style={styles.exportBtn} onClick={handleExport} disabled={exporting}>
            {exporting ? '⏳ Exporting...' : '📥 Export Progress'}
          </button>
        </div>
      </div>

      {/* Progress Card */}
      <div style={styles.progressCard}>
        <div style={styles.progressBar}>
          <div style={styles.progressFill} />
        </div>
        <div style={styles.progressStats}>
          <span style={styles.progressText}>
            {completedActions} of {totalActions} actions complete
          </span>
          <span style={styles.progressPercent}>{progressPercent}%</span>
        </div>
      </div>

      {/* Phase Filter */}
      <div style={styles.phaseFilter}>
        <button 
          style={styles.phaseBtn(activePhase === 'all')} 
          onClick={() => setActivePhase('all')}
        >
          All Steps
        </button>
        <button 
          style={styles.phaseBtn(activePhase === 'before_final_payroll')} 
          onClick={() => setActivePhase('before_final_payroll')}
        >
          Before Final Payroll
        </button>
        <button 
          style={styles.phaseBtn(activePhase === 'after_final_payroll')} 
          onClick={() => setActivePhase('after_final_payroll')}
        >
          After Final Payroll
        </button>
      </div>

      {/* Steps */}
      {filteredSteps.map(step => (
        <StepAccordion
          key={step.step_number || Math.random()}
          step={step}
          progress={progress}
          projectId={project.id}
          onUpdate={handleUpdate}
        />
      ))}
    </div>
  );
}
