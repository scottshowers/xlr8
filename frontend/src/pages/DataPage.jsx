/**
 * DataPage.jsx - Data Hub
 * 
 * REBUILT: December 23, 2025
 * - 3 clean tabs: Upload, Files, Health
 * - Metadata staging before upload with review
 * - Expandable uploads showing tables → fields
 * - Metrics everywhere (date, time, speed, who, duration)
 * - Mission Control styling (consistent with DashboardPage)
 * - Detailed tooltips explaining each classification option
 * 
 * Classification Options:
 * - Truth Type: reality, intent, reference, configuration
 * - Functional Area: Payroll, Benefits, HR Core, etc.
 * - Content Domains: payroll, tax, benefits, time_attendance, hr_core, recruiting, compliance
 */

import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { useUpload } from '../context/UploadContext';
import { useAuth } from '../context/AuthContext';
import { useTooltips } from '../context/TooltipContext';
import { getCustomerColorPalette } from '../utils/customerColors';
import api from '../services/api';
import {
  Upload as UploadIcon, Database, Activity, CheckCircle, XCircle, Clock,
  Loader2, Trash2, FileText, Table2, ChevronDown, ChevronRight, User,
  CheckSquare, Square, AlertTriangle, Zap, Sparkles, X, RefreshCw,
  HelpCircle, Info, Tag, Layers, Target
} from 'lucide-react';
import DataHealthComponent from './DataHealthPage';

// ============================================================================
// BRAND COLORS (Consistent with DashboardPage)
// ============================================================================
const colors = {
  primary: '#83b16d',      // Grass Green
  accent: '#285390',       // Turkish Sea
  electricBlue: '#2766b1',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  silver: '#a2a1a0',
  white: '#f6f5fa',
  scarletSage: '#993c44',
  royalPurple: '#5f4282',
  background: '#f0f2f5',
  cardBg: '#ffffff',
  text: '#1a2332',
  textMuted: '#64748b',
  border: '#e2e8f0',
  warning: '#d97706',
  success: '#285390',
};

// Extended colors object with all needed properties (no theme switching)
colors.bg = colors.background;
colors.card = colors.cardBg;
colors.cardBorder = colors.border;
colors.textLight = '#94a3b8';
colors.primaryLight = 'rgba(131, 177, 109, 0.1)';
colors.accentLight = 'rgba(40, 83, 144, 0.1)';
colors.warningLight = 'rgba(217, 119, 6, 0.1)';
colors.red = colors.scarletSage;
colors.redLight = 'rgba(153, 60, 68, 0.1)';
colors.divider = colors.border;
colors.inputBg = '#f8fafc';
colors.tabBg = colors.white;
colors.tooltipBg = colors.text;
colors.tooltipText = colors.white;

// ============================================================================
// TOOLTIP COMPONENT (Fixed positioning to avoid clipping)
// ============================================================================
function Tooltip({ children, title, detail, action, width = 280 }) {
  const [show, setShow] = useState(false);
  const [coords, setCoords] = useState({ x: 0, y: 0, showBelow: false });
  const triggerRef = useRef(null);
  
  // Get global tooltip setting
  let tooltipsEnabled = true;
  try {
    const context = useTooltips();
    tooltipsEnabled = context.tooltipsEnabled;
  } catch {
    // If not wrapped in TooltipProvider, default to enabled
    tooltipsEnabled = true;
  }

  const handleMouseEnter = () => {
    if (!tooltipsEnabled) return;
    
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      const spaceAbove = rect.top;
      const showBelow = spaceAbove < 200; // If less than 200px above, show below instead
      
      setCoords({
        x: rect.left + rect.width / 2,
        y: showBelow ? rect.bottom + 8 : rect.top - 8,
        showBelow
      });
    }
    setShow(true);
  };

  const shouldShow = show && tooltipsEnabled;

  return (
    <div 
      ref={triggerRef}
      style={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={handleMouseEnter} 
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {shouldShow && (
        <div style={{
          position: 'fixed',
          left: Math.min(Math.max(coords.x, width / 2 + 16), window.innerWidth - width / 2 - 16),
          top: coords.showBelow ? coords.y : 'auto',
          bottom: coords.showBelow ? 'auto' : `calc(100vh - ${coords.y}px)`,
          transform: 'translateX(-50%)',
          padding: '12px 16px', 
          backgroundColor: colors.text, 
          color: colors.white,
          borderRadius: '8px', 
          fontSize: '12px', 
          width: width, 
          zIndex: 99999, 
          boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
          lineHeight: 1.5,
          pointerEvents: 'none',
        }}>
          {title && <div style={{ fontWeight: 600, marginBottom: '6px', fontSize: '13px' }}>{title}</div>}
          <div style={{ opacity: 0.9 }}>{detail}</div>
          {action && (
            <div style={{ 
              marginTop: '10px', 
              paddingTop: '10px', 
              borderTop: '1px solid rgba(255,255,255,0.2)', 
              color: colors.skyBlue, 
              fontWeight: 500,
              fontSize: '11px'
            }}>
              💡 {action}
            </div>
          )}
          <div style={{ 
            position: 'absolute', 
            left: '50%', 
            transform: 'translateX(-50%)',
            ...(coords.showBelow 
              ? { top: '-6px', borderBottom: `6px solid ${colors.text}`, borderTop: 'none' }
              : { bottom: '-6px', borderTop: `6px solid ${colors.text}`, borderBottom: 'none' }
            ),
            width: 0, 
            height: 0, 
            borderLeft: '6px solid transparent', 
            borderRight: '6px solid transparent',
          }} />
        </div>
      )}
    </div>
  );
}

function HelpIcon({ title, detail, action }) {
  return (
    <Tooltip title={title} detail={detail} action={action}>
      <span style={{ 
        display: 'inline-flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        width: 16, 
        height: 16, 
        borderRadius: '50%', 
        backgroundColor: colors.border,
        color: colors.textMuted,
        fontSize: '10px',
        fontWeight: 700,
        cursor: 'help',
        marginLeft: '6px',
      }}>
        ?
      </span>
    </Tooltip>
  );
}

// ============================================================================
// METADATA CONFIGURATION
// ============================================================================
const TRUTH_TYPES = [
  { 
    value: 'reality', 
    label: 'Reality',
    shortLabel: 'Structured Data',
    icon: '📊',
    color: colors.primary,
    storage: 'DuckDB',
    title: 'Reality (Structured Data)',
    detail: 'Actual transactional data like payroll registers, employee rosters, benefits census files. This data gets parsed into DuckDB tables where it can be queried with SQL. This is your "source of truth" — the real data that reflects what actually happened or exists.',
    action: 'Best for: Excel files, CSVs, data exports from systems'
  },
  { 
    value: 'intent', 
    label: 'Intent',
    shortLabel: 'Customer Docs',
    icon: '📋',
    color: colors.electricBlue,
    storage: 'ChromaDB',
    title: 'Intent (Customer Documents)',
    detail: 'Customer-specific documents that describe what SHOULD happen — implementation guides, configuration specs, business requirements, SOWs, project plans. These get chunked and stored in ChromaDB for semantic search. Used to understand what the customer wants to achieve.',
    action: 'Best for: PDFs, Word docs describing requirements or configs'
  },
  { 
    value: 'reference', 
    label: 'Reference',
    shortLabel: 'Standards',
    icon: '📚',
    color: colors.royalPurple,
    storage: 'Reference Library',
    title: 'Reference (Standards & Best Practices)',
    detail: 'Industry standards, compliance checklists, best practices, vendor documentation, regulatory guidance. Goes to the Reference Library where it becomes shared knowledge. Used to compare customer intent against known standards and identify gaps.',
    action: 'Best for: Compliance docs, vendor manuals, industry guides'
  },
  { 
    value: 'configuration', 
    label: 'Config',
    shortLabel: 'System Setup',
    icon: '⚙️',
    color: colors.silver,
    storage: 'DuckDB',
    title: 'Configuration (System Setup)',
    detail: 'System configuration exports, setup files, mapping documents, code tables. Treated as structured data but flagged specially for configuration analysis. Useful for comparing current state vs. desired state.',
    action: 'Best for: Config exports, mapping tables, code lists'
  },
];

const CONTENT_DOMAINS = [
  { 
    value: 'payroll', 
    label: 'Payroll', 
    color: colors.primary,
    title: 'Payroll Domain',
    detail: 'Earnings, deductions, pay registers, compensation data, garnishments, direct deposits, check history. Column patterns: gross_pay, net_pay, earnings_code, deduction_code, pay_date.',
    action: 'Enables payroll-specific analysis and compliance checks'
  },
  { 
    value: 'tax', 
    label: 'Tax', 
    color: colors.scarletSage,
    title: 'Tax Domain',
    detail: 'Federal/state/local withholdings, W2/W4 data, FICA, SUI/SUTA/FUTA, tax jurisdictions, year-end tax processing. Column patterns: federal_tax, state_tax, fica, sui.',
    action: 'Enables tax compliance analysis and W2 reconciliation'
  },
  { 
    value: 'benefits', 
    label: 'Benefits', 
    color: colors.electricBlue,
    title: 'Benefits Domain',
    detail: 'Medical/dental/vision enrollment, 401k/403b contributions, HSA/FSA, life insurance, disability, COBRA, open enrollment, dependent coverage. Column patterns: plan_code, coverage_level, premium.',
    action: 'Enables benefits audit and ACA compliance'
  },
  { 
    value: 'time_attendance', 
    label: 'Time', 
    color: colors.warning,
    title: 'Time & Attendance Domain',
    detail: 'Hours worked, schedules, PTO/leave tracking, overtime, shift differentials, attendance records, accruals. Column patterns: hours, schedule, pto_balance, overtime.',
    action: 'Enables time-off analysis and scheduling optimization'
  },
  { 
    value: 'hr_core', 
    label: 'HR Core', 
    color: colors.accent,
    title: 'HR Core Domain',
    detail: 'Employee master data, demographics, job/position information, organizational hierarchy, reporting relationships, employment status. Column patterns: employee_id, hire_date, department, job_title.',
    action: 'Enables headcount analysis and org structure review'
  },
  { 
    value: 'recruiting', 
    label: 'Recruiting', 
    color: colors.royalPurple,
    title: 'Recruiting Domain',
    detail: 'Applicant tracking, requisitions, candidates, interview feedback, offer letters, onboarding checklists. Column patterns: applicant, requisition, offer_status.',
    action: 'Enables hiring funnel analysis'
  },
  { 
    value: 'compliance', 
    label: 'Compliance', 
    color: colors.scarletSage,
    title: 'Compliance Domain',
    detail: 'Audit trails, regulatory filings, EEO/AAP, OSHA, ACA reporting, SOX controls, policy acknowledgments. Column patterns: audit, compliance, filing.',
    action: 'Enables compliance gap analysis and audit prep'
  },
];

const FUNCTIONAL_AREAS = [
  { 
    value: 'Payroll', 
    title: 'Payroll Functional Area',
    detail: 'Pay processing, earnings calculations, deduction management, garnishments, direct deposits, check printing, pay statements.',
    action: 'Routes to payroll expertise and analysis templates'
  },
  { 
    value: 'Benefits', 
    title: 'Benefits Functional Area',
    detail: 'Health plans, retirement plans, open enrollment, COBRA administration, carrier feeds, premium calculations.',
    action: 'Routes to benefits expertise and enrollment analysis'
  },
  { 
    value: 'HR Core', 
    title: 'HR Core Functional Area',
    detail: 'Employee records, position management, organizational structure, workflow approvals, manager self-service.',
    action: 'Routes to core HR expertise and data quality checks'
  },
  { 
    value: 'Time & Attendance', 
    title: 'Time & Attendance Functional Area',
    detail: 'Timekeeping, scheduling, absence management, leave tracking, overtime rules, clock integration.',
    action: 'Routes to time tracking expertise'
  },
  { 
    value: 'Recruiting', 
    title: 'Recruiting Functional Area',
    detail: 'Talent acquisition, applicant tracking, job postings, interview scheduling, background checks, onboarding.',
    action: 'Routes to recruiting expertise'
  },
  { 
    value: 'Compliance', 
    title: 'Compliance Functional Area',
    detail: 'ACA reporting, EEO/AAP, OSHA, regulatory filings, audit support, policy management.',
    action: 'Routes to compliance expertise and audit checks'
  },
  { 
    value: 'Other', 
    title: 'Other / General',
    detail: 'Cross-functional or general documents that span multiple areas or don\'t fit a specific category.',
    action: 'Will be analyzed without domain-specific context'
  },
];

const TABS = [
  { id: 'upload', label: 'Upload', icon: UploadIcon, tooltip: { title: 'Upload Files', detail: 'Drag & drop or browse to upload files. AI classifies them by Truth Type, Functional Area, and Content Domain before processing.', action: 'Supports Excel, CSV, PDF, Word' } },
  { id: 'files', label: 'Files', icon: Database, tooltip: { title: 'Uploaded Files', detail: 'View all processed files with their tables, columns, and row counts. Expand to see detailed schema information.', action: 'Click to expand and explore data' } },
  { id: 'health', label: 'Health', icon: Activity, tooltip: { title: 'Data Health', detail: 'Monitor data integrity across DuckDB, ChromaDB, and Supabase. See relationship maps and run diagnostics.', action: 'Run Deep Clean to fix sync issues' } },
];

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function DataPage() {
  const { activeProject, projectName, customerName } = useProject();
  const themeColors = colors; // Use static Mission Control colors
  const [activeTab, setActiveTab] = useState('upload');
  const { uploads, hasActive } = useUpload();
  
  const customerColors = activeProject ? getCustomerColorPalette(customerName || projectName) : null;
  const [stagedCount, setStagedCount] = useState(0);

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ 
          margin: 0, fontSize: '20px', fontWeight: 600, color: themeColors.text, 
          display: 'flex', alignItems: 'center', gap: '10px',
          fontFamily: "'Sora', sans-serif"
        }}>
          <div style={{ 
            width: '36px', height: '36px', borderRadius: '10px', 
            backgroundColor: themeColors.primary, 
            display: 'flex', alignItems: 'center', justifyContent: 'center' 
          }}>
            <Database size={20} color="#ffffff" />
          </div>
          Data
        </h1>
        <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: themeColors.textMuted }}>
          Upload, classify, and manage your project data
          {projectName && (
            <span style={{ color: themeColors.primary, fontWeight: 600 }}> • {projectName}</span>
          )}
        </p>
      </div>

      {/* Main Card */}
      <div style={{ 
        backgroundColor: themeColors.card, 
        borderRadius: '12px', 
        border: `1px solid ${themeColors.cardBorder}`, 
        overflow: 'hidden', 
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)' 
      }}>
        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: `1px solid ${themeColors.divider}`, backgroundColor: themeColors.tabBg }}>
          {TABS.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const showBadge = tab.id === 'upload' && (hasActive || stagedCount > 0);
            return (
              <Tooltip key={tab.id} title={tab.tooltip.title} detail={tab.tooltip.detail} action={tab.tooltip.action}>
                <button
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '8px', padding: '16px 24px',
                    border: 'none', background: isActive ? themeColors.card : 'transparent',
                    color: isActive ? themeColors.primary : themeColors.textMuted, 
                    fontWeight: 600, fontSize: '14px', cursor: 'pointer', 
                    borderBottom: isActive ? `2px solid ${themeColors.primary}` : '2px solid transparent',
                    marginBottom: '-1px', transition: 'all 0.15s ease',
                  }}
                >
                  <Icon size={18} />
                  {tab.label}
                  {showBadge && (
                    <span style={{ 
                      minWidth: 18, height: 18, borderRadius: '50%', 
                      backgroundColor: hasActive ? themeColors.warning : themeColors.primary,
                      color: 'white', fontSize: '11px', fontWeight: 700,
                      display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                      {hasActive ? '•' : stagedCount}
                    </span>
                  )}
                </button>
              </Tooltip>
            );
          })}
        </div>

        {/* Tab Content */}
        <div style={{ padding: '24px' }}>
          {activeTab === 'upload' && <UploadTab colors={themeColors} onStagedCountChange={setStagedCount} />}
          {activeTab === 'files' && <FilesTab colors={themeColors} />}
          {activeTab === 'health' && <DataHealthComponent embedded />}
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }`}</style>
    </div>
  );
}

// ============================================================================
// UPLOAD TAB
// ============================================================================
function UploadTab({ colors, onStagedCountChange }) {
  const { activeProject, projectName } = useProject();
  const { user } = useAuth();
  const { uploads, addUpload } = useUpload();
  const fileInputRef = useRef(null);
  
  const [dragOver, setDragOver] = useState(false);
  const [uploadTarget, setUploadTarget] = useState('current');
  const [stagedFiles, setStagedFiles] = useState([]);
  const [expandedUploads, setExpandedUploads] = useState(new Set());
  const [expandedTables, setExpandedTables] = useState(new Set());
  const [completedUploads, setCompletedUploads] = useState([]);
  const [tableProfiles, setTableProfiles] = useState({});
  const [loadingProfiles, setLoadingProfiles] = useState(new Set());
  const [expandedStaged, setExpandedStaged] = useState(new Set());
  const [uploading, setUploading] = useState(false);

  // Notify parent of staged count
  useEffect(() => {
    onStagedCountChange?.(stagedFiles.length);
  }, [stagedFiles.length, onStagedCountChange]);

  // Load recent completed jobs on mount
  useEffect(() => {
    loadRecentJobs();
    const interval = setInterval(loadRecentJobs, 15000);
    return () => clearInterval(interval);
  }, [activeProject?.id]);

  const loadRecentJobs = async () => {
    try {
      const [jobsRes, structRes] = await Promise.all([
        api.get('/jobs').catch(() => ({ data: { jobs: [] } })),
        api.get('/status/structured').catch(() => ({ data: { files: [] } })),
      ]);
      
      const jobs = (jobsRes.data.jobs || [])
        .filter(j => j.status === 'completed' && (!activeProject || j.project_id === activeProject.id))
        .slice(0, 10);
      
      const enrichedJobs = jobs.map(job => {
        const filename = job.input_data?.filename || job.result_data?.filename || job.filename;
        const matchingFile = (structRes.data.files || []).find(f => f.filename === filename);
        return {
          ...job,
          filename,
          tables: matchingFile?.sheets || [],
          totalRows: matchingFile?.total_rows || job.result_data?.total_rows || 0,
        };
      });
      
      setCompletedUploads(enrichedJobs);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    }
  };

  const loadTableProfile = async (tableName) => {
    if (tableProfiles[tableName] || loadingProfiles.has(tableName)) return;
    setLoadingProfiles(prev => new Set([...prev, tableName]));
    try {
      const res = await api.get(`/status/table-profile/${encodeURIComponent(tableName)}`);
      setTableProfiles(prev => ({ ...prev, [tableName]: res.data }));
    } catch (err) {
      setTableProfiles(prev => ({ ...prev, [tableName]: { error: err.message } }));
    } finally {
      setLoadingProfiles(prev => { const n = new Set(prev); n.delete(tableName); return n; });
    }
  };

  // ========== AUTO-DETECTION ==========
  const detectTruthType = (file) => {
    const ext = file.name.split('.').pop().toLowerCase();
    const name = file.name.toLowerCase();
    
    if (['xlsx', 'xls', 'csv'].includes(ext)) return 'reality';
    if (name.includes('config') || name.includes('setup') || name.includes('mapping')) return 'configuration';
    if (name.includes('checklist') || name.includes('guide') || name.includes('standard') || name.includes('compliance') || name.includes('best practice')) return 'reference';
    return 'intent';
  };

  const detectFunctionalArea = (file) => {
    const name = file.name.toLowerCase();
    if (name.includes('payroll') || name.includes('pay_') || name.includes('earning') || name.includes('deduction')) return 'Payroll';
    if (name.includes('benefit') || name.includes('health') || name.includes('401k') || name.includes('insurance') || name.includes('enrollment')) return 'Benefits';
    if (name.includes('employee') || name.includes('roster') || name.includes('census') || name.includes('master') || name.includes('demographic')) return 'HR Core';
    if (name.includes('time') || name.includes('attendance') || name.includes('schedule') || name.includes('pto') || name.includes('leave')) return 'Time & Attendance';
    if (name.includes('compliance') || name.includes('audit') || name.includes('aca') || name.includes('eeo')) return 'Compliance';
    if (name.includes('recruit') || name.includes('applicant') || name.includes('candidate') || name.includes('hire')) return 'Recruiting';
    return 'Other';
  };

  const detectContentDomains = (file) => {
    const name = file.name.toLowerCase();
    const domains = [];
    
    if (name.includes('payroll') || name.includes('earning') || name.includes('deduction') || name.includes('pay_') || name.includes('compensation')) domains.push('payroll');
    if (name.includes('tax') || name.includes('w2') || name.includes('w4') || name.includes('withhold') || name.includes('fica')) domains.push('tax');
    if (name.includes('benefit') || name.includes('medical') || name.includes('dental') || name.includes('401k') || name.includes('hsa')) domains.push('benefits');
    if (name.includes('time') || name.includes('hour') || name.includes('schedule') || name.includes('pto') || name.includes('attendance')) domains.push('time_attendance');
    if (name.includes('employee') || name.includes('roster') || name.includes('census') || name.includes('demographic') || name.includes('master')) domains.push('hr_core');
    if (name.includes('recruit') || name.includes('applicant') || name.includes('candidate')) domains.push('recruiting');
    if (name.includes('compliance') || name.includes('audit') || name.includes('aca') || name.includes('eeo')) domains.push('compliance');
    
    return domains.length > 0 ? domains : ['hr_core'];
  };

  const getConfidence = (file) => {
    const ext = file.name.split('.').pop().toLowerCase();
    if (['xlsx', 'xls', 'csv'].includes(ext)) return 'high';
    const name = file.name.toLowerCase();
    if (name.includes('payroll') || name.includes('benefit') || name.includes('employee') || name.includes('checklist')) return 'high';
    if (name.includes('report') || name.includes('summary') || name.includes('export')) return 'medium';
    return 'low';
  };

  const handleFilesSelected = (files) => {
    const newStaged = Array.from(files).map((file, idx) => ({
      id: `${Date.now()}-${idx}`,
      file,
      filename: file.name,
      size: formatFileSize(file.size),
      truthType: detectTruthType(file),
      functionalArea: detectFunctionalArea(file),
      contentDomains: detectContentDomains(file),
      confidence: getConfidence(file),
    }));
    setStagedFiles(prev => [...prev, ...newStaged]);
    // Auto-expand new files
    newStaged.forEach(f => setExpandedStaged(prev => new Set([...prev, f.id])));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFilesSelected(e.dataTransfer.files);
  };

  const handleFileSelect = (e) => {
    handleFilesSelected(e.target.files);
    e.target.value = '';
  };

  const removeStaged = (id) => {
    setStagedFiles(prev => prev.filter(f => f.id !== id));
    setExpandedStaged(prev => { const n = new Set(prev); n.delete(id); return n; });
  };

  const updateStagedFile = (id, updates) => {
    setStagedFiles(prev => prev.map(f => f.id === id ? { ...f, ...updates } : f));
  };

  const toggleDomain = (fileId, domain) => {
    setStagedFiles(prev => prev.map(f => {
      if (f.id !== fileId) return f;
      const domains = f.contentDomains.includes(domain)
        ? f.contentDomains.filter(d => d !== domain)
        : [...f.contentDomains, domain];
      return { ...f, contentDomains: domains };
    }));
  };

  const toggleStagedExpand = (id) => {
    setExpandedStaged(prev => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  };

  const uploadAll = async () => {
    const target = uploadTarget === 'reference' 
      ? { id: 'reference_library', name: 'Reference Library' }
      : { id: activeProject?.id, name: projectName };
    
    if (!target.id && uploadTarget !== 'reference') {
      alert('Please select a project first');
      return;
    }

    setUploading(true);
    
    for (const staged of stagedFiles) {
      const formData = new FormData();
      formData.append('file', staged.file);
      formData.append('project', target.name || target.id);
      formData.append('functional_area', staged.functionalArea);
      formData.append('truth_type', staged.truthType);
      formData.append('content_domain', staged.contentDomains.join(','));
      
      if (staged.truthType === 'reference') {
        formData.append('standards_mode', 'true');
      }

      try {
        await api.post('/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      } catch (err) {
        console.error('Upload failed:', err);
      }
    }

    setStagedFiles([]);
    setExpandedStaged(new Set());
    setUploading(false);
    
    // Refresh jobs list
    setTimeout(loadRecentJobs, 2000);
  };

  const toggleUpload = (id) => {
    const next = new Set(expandedUploads);
    next.has(id) ? next.delete(id) : next.add(id);
    setExpandedUploads(next);
  };

  const toggleTable = (name) => {
    const next = new Set(expandedTables);
    next.has(name) ? next.delete(name) : next.add(name);
    setExpandedTables(next);
    if (!expandedTables.has(name)) {
      loadTableProfile(name);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleString('en-US', { 
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true 
      });
    } catch { return '—'; }
  };

  const getSemanticColor = (semantic) => {
    const map = {
      identifier: colors.accent,
      name: colors.primary,
      currency: '#059669',
      date: colors.electricBlue,
      category: colors.silver,
      code: colors.warning,
      quantity: colors.royalPurple,
      status: colors.skyBlue,
      text: colors.textMuted,
      number: '#059669',
    };
    return map[semantic] || colors.textMuted;
  };

  const getConfidenceBadge = (confidence) => {
    if (confidence === 'high') return { bg: `${colors.primary}15`, color: colors.primary, label: 'Auto-detected' };
    if (confidence === 'medium') return { bg: `${colors.warning}15`, color: colors.warning, label: 'Review suggested' };
    return { bg: `${colors.scarletSage}15`, color: colors.scarletSage, label: 'Needs review' };
  };

  const activeUploads = uploads.filter(u => u.status === 'uploading' || u.status === 'processing');

  return (
    <div>
      {/* Destination Selector */}
      <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>Upload to:</span>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setUploadTarget('current')}
            style={{
              padding: '10px 16px', borderRadius: '8px', 
              border: `1px solid ${uploadTarget === 'current' ? colors.primary : colors.border}`,
              backgroundColor: uploadTarget === 'current' ? `${colors.primary}15` : colors.cardBg,
              color: uploadTarget === 'current' ? colors.primary : colors.textMuted,
              fontWeight: 600, fontSize: '13px', cursor: 'pointer', 
              display: 'flex', alignItems: 'center', gap: '6px'
            }}
          >
            <Table2 size={16} /> {projectName || 'Current Project'}
          </button>
          <button
            onClick={() => setUploadTarget('reference')}
            style={{
              padding: '10px 16px', borderRadius: '8px', 
              border: `1px solid ${uploadTarget === 'reference' ? colors.royalPurple : colors.border}`,
              backgroundColor: uploadTarget === 'reference' ? `${colors.royalPurple}15` : colors.cardBg,
              color: uploadTarget === 'reference' ? colors.royalPurple : colors.textMuted,
              fontWeight: 600, fontSize: '13px', cursor: 'pointer', 
              display: 'flex', alignItems: 'center', gap: '6px'
            }}
          >
            <FileText size={16} /> Reference Library
          </button>
        </div>
        <HelpIcon 
          title="Upload Destination"
          detail="Current Project: Data specific to this implementation. Reference Library: Shared knowledge available across all projects (standards, compliance guides, best practices)."
          action="Reference docs become part of XLR8's knowledge base"
        />
      </div>

      {/* Dropzone */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        multiple
        accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md"
        onChange={handleFileSelect}
      />
      <div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        style={{
          border: `2px dashed ${dragOver ? colors.primary : colors.border}`,
          borderRadius: '12px', padding: '40px', textAlign: 'center', cursor: 'pointer',
          backgroundColor: dragOver ? `${colors.primary}10` : colors.white,
          transition: 'all 0.2s ease', marginBottom: '24px',
        }}
      >
        <div style={{ 
          width: 56, height: 56, borderRadius: '14px', 
          backgroundColor: `${colors.primary}15`, 
          display: 'flex', alignItems: 'center', justifyContent: 'center', 
          margin: '0 auto 12px' 
        }}>
          <UploadIcon size={28} color={colors.primary} />
        </div>
        <p style={{ margin: '0 0 4px', fontSize: '15px', fontWeight: 600, color: colors.text }}>
          {dragOver ? 'Drop files here' : 'Drop files here or click to browse'}
        </p>
        <p style={{ margin: 0, fontSize: '13px', color: colors.textMuted }}>
          PDF, Excel, Word, CSV • Up to 50MB per file
        </p>
      </div>

      {/* ========== STAGED FILES (Before Upload) ========== */}
      {stagedFiles.length > 0 && (
        <div style={{ 
          backgroundColor: `${colors.warning}08`, 
          border: `1px solid ${colors.warning}40`, 
          borderRadius: '12px', marginBottom: '24px', overflow: 'hidden' 
        }}>
          {/* Header */}
          <div style={{ 
            padding: '16px 20px', 
            borderBottom: `1px solid ${colors.warning}30`, 
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            backgroundColor: `${colors.warning}05`
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertTriangle size={18} color={colors.warning} />
              <span style={{ fontSize: '15px', fontWeight: 600, color: colors.text }}>
                Review & Classify Before Upload
              </span>
              <span style={{ fontSize: '12px', color: colors.textMuted }}>
                {stagedFiles.length} file{stagedFiles.length > 1 ? 's' : ''} staged
              </span>
              <HelpIcon 
                title="Why Classify?"
                detail="Proper classification helps XLR8 route your data correctly. Reality goes to DuckDB for queries, Intent/Reference go to ChromaDB for semantic search. Domains enable specialized analysis."
                action="Better classification = better insights"
              />
            </div>
            <button 
              onClick={uploadAll}
              disabled={uploading}
              style={{ 
                display: 'flex', alignItems: 'center', gap: '6px', padding: '10px 20px', 
                backgroundColor: uploading ? colors.textMuted : colors.primary, 
                color: 'white', border: 'none', 
                borderRadius: '8px', fontSize: '14px', fontWeight: 600, 
                cursor: uploading ? 'not-allowed' : 'pointer',
                opacity: uploading ? 0.7 : 1
              }}
            >
              {uploading ? (
                <>
                  <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                  Uploading...
                </>
              ) : (
                <>
                  <UploadIcon size={16} /> Upload All
                </>
              )}
            </button>
          </div>
          
          {/* Staged Files List */}
          {stagedFiles.map((file, idx) => {
            const conf = getConfidenceBadge(file.confidence);
            const truthType = TRUTH_TYPES.find(t => t.value === file.truthType);
            const isExpanded = expandedStaged.has(file.id);
            
            return (
              <div key={file.id} style={{ 
                borderBottom: idx < stagedFiles.length - 1 ? `1px solid ${colors.warning}20` : 'none',
                backgroundColor: colors.cardBg
              }}>
                {/* File Header Row */}
                <div style={{ 
                  padding: '16px 20px', 
                  display: 'flex', alignItems: 'center', gap: '12px',
                  cursor: 'pointer'
                }} onClick={() => toggleStagedExpand(file.id)}>
                  {isExpanded ? <ChevronDown size={18} color={colors.textMuted} /> : <ChevronRight size={18} color={colors.textMuted} />}
                  
                  <span style={{ fontSize: '18px' }}>{truthType?.icon}</span>
                  
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>{file.filename}</span>
                      <span style={{ fontSize: '12px', color: colors.textMuted }}>{file.size}</span>
                      <span style={{ 
                        padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                        backgroundColor: conf.bg, color: conf.color
                      }}>
                        {conf.label}
                      </span>
                    </div>
                    
                    {/* Summary when collapsed */}
                    {!isExpanded && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px', fontSize: '12px', color: colors.textMuted }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Target size={12} color={truthType?.color} /> {truthType?.label}
                        </span>
                        <span>→ {truthType?.storage}</span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Layers size={12} /> {file.functionalArea}
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Tag size={12} /> {file.contentDomains.length} domain{file.contentDomains.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                    )}
                  </div>
                  
                  <button 
                    onClick={(e) => { e.stopPropagation(); removeStaged(file.id); }} 
                    style={{ background: 'none', border: 'none', color: colors.textMuted, cursor: 'pointer', padding: '4px' }}
                  >
                    <X size={18} />
                  </button>
                </div>
                
                {/* Expanded Classification Options */}
                {isExpanded && (
                  <div style={{ padding: '0 20px 20px 52px' }}>
                    {/* Truth Type */}
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                        <Target size={14} color={colors.textMuted} />
                        <span style={{ fontSize: '12px', fontWeight: 600, color: colors.text }}>Truth Type</span>
                        <HelpIcon 
                          title="What is Truth Type?"
                          detail="Determines how XLR8 stores and uses this file. Reality = actual data (DuckDB). Intent = customer requirements (ChromaDB). Reference = standards/best practices (Reference Library). Config = system setup data."
                          action="This controls where data is stored and how it's queried"
                        />
                      </div>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {TRUTH_TYPES.map(tt => (
                          <Tooltip key={tt.value} title={tt.title} detail={tt.detail} action={tt.action} width={320}>
                            <button
                              onClick={() => updateStagedFile(file.id, { truthType: tt.value })}
                              style={{
                                padding: '8px 14px', borderRadius: '8px', cursor: 'pointer',
                                border: file.truthType === tt.value ? `2px solid ${tt.color}` : `1px solid ${colors.border}`,
                                backgroundColor: file.truthType === tt.value ? `${tt.color}12` : colors.cardBg,
                                color: file.truthType === tt.value ? tt.color : colors.textMuted,
                                fontWeight: 500, fontSize: '13px',
                                display: 'flex', alignItems: 'center', gap: '6px',
                              }}
                            >
                              <span>{tt.icon}</span>
                              <span>{tt.label}</span>
                              <span style={{ fontSize: '10px', opacity: 0.7 }}>→ {tt.storage}</span>
                            </button>
                          </Tooltip>
                        ))}
                      </div>
                    </div>
                    
                    {/* Functional Area */}
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                        <Layers size={14} color={colors.textMuted} />
                        <span style={{ fontSize: '12px', fontWeight: 600, color: colors.text }}>Functional Area</span>
                        <HelpIcon 
                          title="What is Functional Area?"
                          detail="The HCM module or business function this file relates to. Helps XLR8 apply the right expertise and analysis templates when processing your data."
                          action="Enables domain-specific insights and validations"
                        />
                      </div>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {FUNCTIONAL_AREAS.map(fa => (
                          <Tooltip key={fa.value} title={fa.title} detail={fa.detail} action={fa.action}>
                            <button
                              onClick={() => updateStagedFile(file.id, { functionalArea: fa.value })}
                              style={{
                                padding: '6px 12px', borderRadius: '6px', cursor: 'pointer',
                                border: file.functionalArea === fa.value ? `2px solid ${colors.accent}` : `1px solid ${colors.border}`,
                                backgroundColor: file.functionalArea === fa.value ? `${colors.accent}15` : colors.cardBg,
                                color: file.functionalArea === fa.value ? colors.accent : colors.textMuted,
                                fontWeight: 500, fontSize: '12px',
                              }}
                            >
                              {fa.value}
                            </button>
                          </Tooltip>
                        ))}
                      </div>
                    </div>
                    
                    {/* Content Domains (Multi-select) */}
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                        <Tag size={14} color={colors.textMuted} />
                        <span style={{ fontSize: '12px', fontWeight: 600, color: colors.text }}>Content Domains</span>
                        <span style={{ fontSize: '11px', color: colors.textMuted }}>(select all that apply)</span>
                        <HelpIcon 
                          title="What are Content Domains?"
                          detail="Tags that describe what data is IN this file. A payroll register might have payroll + tax domains. Multi-select allowed. These tags improve search relevance and enable cross-domain analysis."
                          action="More accurate tags = better semantic search results"
                        />
                      </div>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {CONTENT_DOMAINS.map(cd => {
                          const isSelected = file.contentDomains.includes(cd.value);
                          return (
                            <Tooltip key={cd.value} title={cd.title} detail={cd.detail} action={cd.action}>
                              <button
                                onClick={() => toggleDomain(file.id, cd.value)}
                                style={{
                                  padding: '6px 12px', borderRadius: '20px', cursor: 'pointer',
                                  border: isSelected ? `2px solid ${cd.color}` : `1px solid ${colors.border}`,
                                  backgroundColor: isSelected ? `${cd.color}15` : colors.cardBg,
                                  color: isSelected ? cd.color : colors.textMuted,
                                  fontWeight: 500, fontSize: '12px',
                                  display: 'flex', alignItems: 'center', gap: '4px',
                                }}
                              >
                                {isSelected && <CheckCircle size={12} />}
                                {cd.label}
                              </button>
                            </Tooltip>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Active Uploads */}
      {activeUploads.length > 0 && (
        <div style={{ 
          backgroundColor: colors.cardBg, 
          border: `1px solid ${colors.border}`, 
          borderRadius: '12px', marginBottom: '24px', overflow: 'hidden' 
        }}>
          <div style={{ 
            padding: '14px 20px', 
            borderBottom: `1px solid ${colors.border}`, 
            display: 'flex', justifyContent: 'space-between', alignItems: 'center' 
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Loader2 size={16} color={colors.warning} style={{ animation: 'spin 1s linear infinite' }} />
              <span style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>
                Active Uploads
              </span>
              <span style={{ 
                padding: '2px 8px', backgroundColor: `${colors.warning}15`, 
                color: colors.warning, borderRadius: '10px', fontSize: '11px', fontWeight: 600 
              }}>
                {activeUploads.length} processing
              </span>
            </div>
          </div>
          
          {activeUploads.map(upload => (
            <div key={upload.id} style={{ 
              padding: '14px 20px', 
              borderBottom: `1px solid ${colors.border}`,
              display: 'flex', alignItems: 'center', gap: '12px'
            }}>
              <Clock size={18} color={colors.warning} style={{ animation: 'pulse 2s infinite' }} />
              <span style={{ flex: 1, fontSize: '14px', fontWeight: 500, color: colors.text }}>
                {upload.filename}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: colors.textMuted }}>
                <span>{upload.status === 'processing' ? 'Processing...' : 'Uploading...'}</span>
                <div style={{ width: 80, height: 6, backgroundColor: colors.iceFlow, borderRadius: 3 }}>
                  <div style={{ 
                    width: `${upload.progress}%`, height: '100%', 
                    backgroundColor: colors.warning, borderRadius: 3,
                    transition: 'width 0.3s'
                  }} />
                </div>
                <span style={{ fontWeight: 600, color: colors.warning }}>{upload.progress}%</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <User size={12} /> {user?.email?.split('@')[0] || 'you'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Completed Uploads */}
      {completedUploads.length > 0 && (
        <div style={{ 
          backgroundColor: colors.cardBg, 
          border: `1px solid ${colors.border}`, 
          borderRadius: '12px', overflow: 'hidden' 
        }}>
          <div style={{ 
            padding: '14px 20px', 
            borderBottom: `1px solid ${colors.border}`, 
            display: 'flex', justifyContent: 'space-between', alignItems: 'center' 
          }}>
            <span style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>Recent Uploads</span>
            <button 
              onClick={loadRecentJobs}
              style={{ background: 'none', border: 'none', color: colors.textMuted, fontSize: '12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              <RefreshCw size={12} /> Refresh
            </button>
          </div>
          
          {completedUploads.map(job => (
            <div key={job.id}>
              <div 
                onClick={() => job.tables?.length > 0 && toggleUpload(job.id)}
                style={{ 
                  padding: '14px 20px', 
                  borderBottom: `1px solid ${colors.border}`,
                  cursor: job.tables?.length > 0 ? 'pointer' : 'default',
                  backgroundColor: expandedUploads.has(job.id) ? colors.background : 'transparent',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {job.tables?.length > 0 ? (
                    expandedUploads.has(job.id) ? 
                      <ChevronDown size={18} color={colors.textMuted} /> : 
                      <ChevronRight size={18} color={colors.textMuted} />
                  ) : <div style={{ width: 18 }} />}
                  <CheckCircle size={18} color={colors.success} />
                  <span style={{ flex: 1, fontSize: '14px', fontWeight: 500, color: colors.text }}>
                    {job.filename}
                  </span>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: colors.textMuted }}>
                    <span>{formatDate(job.created_at)}</span>
                    {job.result_data?.processing_time_seconds && (
                      <span style={{ fontWeight: 500 }}>
                        {job.result_data.processing_time_seconds.toFixed(1)}s
                      </span>
                    )}
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <User size={12} /> {job.input_data?.user?.split('@')[0] || 'system'}
                    </span>
                    {job.tables?.length > 0 && (
                      <span style={{ 
                        padding: '2px 8px', backgroundColor: `${colors.primary}15`, 
                        color: colors.primary, borderRadius: '4px', fontWeight: 600, fontSize: '11px'
                      }}>
                        {job.tables.length} table{job.tables.length > 1 ? 's' : ''} • {job.totalRows.toLocaleString()} rows
                      </span>
                    )}
                    {job.result_data?.chunks_created > 0 && (
                      <span style={{ 
                        padding: '2px 8px', backgroundColor: `${colors.accent}15`, 
                        color: colors.accent, borderRadius: '4px', fontWeight: 600, fontSize: '11px'
                      }}>
                        {job.result_data.chunks_created} chunks
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              {expandedUploads.has(job.id) && job.tables?.length > 0 && (
                <div style={{ backgroundColor: colors.background, borderBottom: `1px solid ${colors.border}` }}>
                  {job.tables.map(table => {
                    const profile = tableProfiles[table.table_name];
                    const isLoading = loadingProfiles.has(table.table_name);
                    return (
                      <div key={table.table_name}>
                        <div 
                          onClick={(e) => { e.stopPropagation(); toggleTable(table.table_name); }}
                          style={{ 
                            padding: '10px 20px 10px 52px', 
                            display: 'flex', alignItems: 'center', gap: '10px',
                            cursor: 'pointer', 
                            backgroundColor: expandedTables.has(table.table_name) ? `${colors.primary}10` : 'transparent'
                          }}
                        >
                          {expandedTables.has(table.table_name) ? 
                            <ChevronDown size={14} color={colors.primary} /> : 
                            <ChevronRight size={14} color={colors.textMuted} />
                          }
                          <Table2 size={14} color={colors.primary} />
                          <span style={{ fontSize: '13px', fontWeight: 600, color: colors.text }}>
                            {table.table_name || table.sheet_name}
                          </span>
                          <span style={{ fontSize: '12px', color: colors.textMuted }}>
                            ({(table.row_count || 0).toLocaleString()} rows)
                          </span>
                          <span style={{ fontSize: '11px', color: colors.textMuted, marginLeft: 'auto' }}>
                            {table.columns?.length || 0} columns
                          </span>
                          {isLoading && <Loader2 size={12} style={{ animation: 'spin 1s linear infinite', color: colors.primary }} />}
                        </div>
                        
                        {expandedTables.has(table.table_name) && (
                          <div style={{ padding: '8px 20px 12px 76px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                            {(profile?.columns || table.columns || []).slice(0, 20).map((col, ci) => {
                              const colName = typeof col === 'string' ? col : col.name;
                              const colType = typeof col === 'string' ? 'VARCHAR' : (col.dtype || col.type || 'VARCHAR');
                              const semantic = col.semantic_type || col.semantic || 'text';
                              const fillRate = col.fill_rate;
                              return (
                                <div key={ci} style={{ 
                                  display: 'flex', alignItems: 'center', gap: '6px',
                                  padding: '4px 10px', backgroundColor: colors.cardBg, 
                                  border: `1px solid ${colors.border}`, borderRadius: '6px',
                                  fontSize: '12px'
                                }}>
                                  <span style={{ fontWeight: 500, color: colors.text }}>{colName}</span>
                                  <span style={{ color: colors.textMuted, fontSize: '10px' }}>{colType}</span>
                                  {semantic && semantic !== 'text' && (
                                    <span style={{ 
                                      padding: '1px 6px', borderRadius: '3px', fontSize: '9px', fontWeight: 600,
                                      backgroundColor: `${getSemanticColor(semantic)}15`,
                                      color: getSemanticColor(semantic)
                                    }}>
                                      {semantic}
                                    </span>
                                  )}
                                  {fillRate !== undefined && (
                                    <span style={{ fontSize: '9px', color: fillRate < 50 ? colors.warning : colors.textMuted }}>
                                      {fillRate}%
                                    </span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Register Extractor Link */}
      <div style={{ 
        marginTop: '20px', padding: '16px 20px', 
        backgroundColor: `${colors.accent}10`, 
        border: `1px solid ${colors.accent}40`, 
        borderRadius: '12px', 
        display: 'flex', alignItems: 'center', gap: '12px' 
      }}>
        <Sparkles size={20} color={colors.accent} />
        <div style={{ flex: 1 }}>
          <span style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>
            Need to extract payroll registers?
          </span>
          <span style={{ fontSize: '13px', color: colors.textMuted, marginLeft: '8px' }}>
            Deep extraction for complex PDFs with embedded tables
          </span>
        </div>
        <Link 
          to="/vacuum"
          style={{ 
            display: 'flex', alignItems: 'center', gap: '6px', padding: '10px 16px', 
            backgroundColor: colors.accent, color: 'white', border: 'none', 
            borderRadius: '8px', fontSize: '13px', fontWeight: 600, textDecoration: 'none' 
          }}
        >
          Register Extractor <ChevronRight size={16} />
        </Link>
      </div>
    </div>
  );
}

// ============================================================================
// FILES TAB
// ============================================================================
function FilesTab({ colors }) {
  const { projects, activeProject } = useProject();
  const [structuredData, setStructuredData] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [selectedStructured, setSelectedStructured] = useState(new Set());
  const [selectedDocs, setSelectedDocs] = useState(new Set());
  const [fileFilter, setFileFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  const [deepCleanLoading, setDeepCleanLoading] = useState(false);
  const [deepCleanResult, setDeepCleanResult] = useState(null);
  const [showDeepCleanModal, setShowDeepCleanModal] = useState(false);
  const [forceClean, setForceClean] = useState(false);

  useEffect(() => { 
    loadData(); 
    const interval = setInterval(loadData, 30000); 
    return () => clearInterval(interval); 
  }, [activeProject?.id]);

  const loadData = async () => {
    try {
      const [structRes, docsRes] = await Promise.all([
        api.get('/status/structured').catch(() => ({ data: { files: [], total_rows: 0 } })),
        api.get('/status/documents').catch(() => ({ data: { documents: [] } })),
      ]);
      setStructuredData(structRes.data);
      setDocuments(docsRes.data);
    } catch (err) { 
      console.error('Failed to load:', err); 
    } finally { 
      setLoading(false); 
    }
  };

  const structuredFiles = (structuredData?.files || [])
    .filter(f => !activeProject || f.project === activeProject.id || f.project === activeProject.name);
  const docs = (documents?.documents || [])
    .filter(d => !activeProject || d.project === activeProject.id || d.project === activeProject.name);

  const totalTables = structuredFiles.reduce((sum, f) => sum + (f.sheets?.length || 1), 0);
  const totalRows = structuredFiles.reduce((sum, f) => sum + (f.total_rows || 0), 0);
  const totalDocs = docs.length;

  const allFiles = [
    ...structuredFiles.map(f => ({ ...f, type: 'structured', key: `${f.project}:${f.filename}` })),
    ...docs.map(d => ({ ...d, type: 'document', key: d.filename })),
  ].filter(f => {
    if (fileFilter !== 'all' && f.type !== fileFilter) return false;
    if (searchQuery && !f.filename?.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const getProjectName = (pv) => { 
    if (!pv) return 'Unknown'; 
    if (pv === 'GLOBAL') return 'GLOBAL'; 
    if (pv.length === 36 && pv.includes('-')) { 
      const f = projects.find(p => p.id === pv); 
      return f ? f.name : pv.slice(0, 8) + '...'; 
    } 
    return pv; 
  };

  const formatDate = (dateStr) => { 
    if (!dateStr) return '—'; 
    try { 
      return new Date(dateStr).toLocaleString('en-US', { 
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true 
      }); 
    } catch { return '—'; } 
  };

  const toggleSelect = (key, type) => {
    if (type === 'structured') {
      const s = new Set(selectedStructured);
      s.has(key) ? s.delete(key) : s.add(key);
      setSelectedStructured(s);
    } else {
      const s = new Set(selectedDocs);
      s.has(key) ? s.delete(key) : s.add(key);
      setSelectedDocs(s);
    }
  };

  const deleteSelected = async () => {
    if (selectedStructured.size === 0 && selectedDocs.size === 0) return;
    const total = selectedStructured.size + selectedDocs.size;
    if (!confirm(`Delete ${total} file(s)?`)) return;
    
    setDeleting(true);
    try {
      for (const key of selectedStructured) {
        const [project, filename] = key.split(':');
        await api.delete(`/status/structured/${encodeURIComponent(project)}/${encodeURIComponent(filename)}`);
      }
      for (const filename of selectedDocs) {
        await api.delete(`/status/documents/${encodeURIComponent(filename)}`);
      }
      setSelectedStructured(new Set());
      setSelectedDocs(new Set());
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(false);
    }
  };

  const handleDeepClean = async () => {
    setDeepCleanLoading(true);
    setDeepCleanResult(null);
    try {
      const url = forceClean ? '/deep-clean?confirm=true&force=true' : '/deep-clean?confirm=true';
      const res = await api.post(url);
      setDeepCleanResult(res.data);
      await loadData();
    } catch (err) {
      setDeepCleanResult({ 
        success: false, 
        error: err.response?.data?.detail || err.response?.data?.error || err.message 
      });
    } finally {
      setDeepCleanLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px', color: colors.textMuted }}>
        <RefreshCw size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: '16px', opacity: 0.5 }} />
        <p style={{ margin: 0 }}>Loading data...</p>
      </div>
    );
  }

  const selectedCount = selectedStructured.size + selectedDocs.size;

  return (
    <div>
      {/* Stats Bar */}
      <div style={{ 
        display: 'flex', gap: '24px', marginBottom: '20px', padding: '16px 20px', 
        backgroundColor: colors.card, border: `1px solid ${colors.divider}`, borderRadius: '12px' 
      }}>
        <Tooltip title="Structured Tables" detail="Tables created from Excel, CSV files stored in DuckDB. Queryable with SQL." action="Upload more Excel/CSV files to add tables">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'help' }}>
            <Table2 size={18} color={colors.primary} />
            <span style={{ fontSize: '20px', fontWeight: 700, color: colors.text }}>{totalTables}</span>
            <span style={{ fontSize: '13px', color: colors.textMuted }}>Tables</span>
          </div>
        </Tooltip>
        <div style={{ width: 1, backgroundColor: colors.divider }} />
        <Tooltip title="Documents" detail="PDFs and Word docs stored in ChromaDB. Searchable via semantic similarity." action="Upload PDFs to add to knowledge base">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'help' }}>
            <FileText size={18} color={colors.accent} />
            <span style={{ fontSize: '20px', fontWeight: 700, color: colors.text }}>{totalDocs}</span>
            <span style={{ fontSize: '13px', color: colors.textMuted }}>Documents</span>
          </div>
        </Tooltip>
        <div style={{ width: 1, backgroundColor: colors.divider }} />
        <Tooltip title="Total Rows" detail="Sum of all rows across all structured tables. This is your queryable data volume." action="More rows = richer analysis">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'help' }}>
            <Database size={18} color={colors.silver} />
            <span style={{ fontSize: '20px', fontWeight: 700, color: colors.text }}>
              {totalRows > 1000000 ? (totalRows / 1000000).toFixed(1) + 'M' : totalRows > 1000 ? (totalRows / 1000).toFixed(0) + 'K' : totalRows}
            </span>
            <span style={{ fontSize: '13px', color: colors.textMuted }}>Rows</span>
          </div>
        </Tooltip>
        <div style={{ flex: 1 }} />
        <Tooltip title="Deep Clean" detail="Removes orphaned data from ChromaDB, DuckDB metadata, and Supabase. Safe to run anytime." action="Use when data seems out of sync">
          <button
            onClick={() => setShowDeepCleanModal(true)}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px',
              background: `${colors.warning}15`, border: `1px solid ${colors.warning}40`,
              borderRadius: 8, color: colors.warning, fontSize: '13px', fontWeight: 600, cursor: 'pointer',
            }}
          >
            <Zap size={14} /> Deep Clean
          </button>
        </Tooltip>
      </div>

      {/* Filter & Search */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          {['all', 'structured', 'document'].map(filter => (
            <button
              key={filter}
              onClick={() => setFileFilter(filter)}
              style={{
                padding: '8px 14px', borderRadius: '6px',
                border: fileFilter === filter ? 'none' : `1px solid ${colors.border}`,
                backgroundColor: fileFilter === filter ? colors.primary : colors.card,
                color: fileFilter === filter ? 'white' : colors.textMuted,
                fontSize: '13px', fontWeight: 500, cursor: 'pointer', textTransform: 'capitalize'
              }}
            >
              {filter === 'all' ? 'All Files' : filter === 'structured' ? 'Tables' : 'Documents'}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Search files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ 
              padding: '8px 12px', border: `1px solid ${colors.border}`, 
              borderRadius: '6px', fontSize: '13px', width: 200,
              backgroundColor: colors.card, color: colors.text
            }}
          />
          {selectedCount > 0 && (
            <button 
              onClick={deleteSelected}
              disabled={deleting}
              style={{ 
                display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px', 
                backgroundColor: colors.scarletSage, color: 'white', border: 'none', 
                borderRadius: '6px', fontSize: '13px', fontWeight: 500, cursor: 'pointer' 
              }}
            >
              <Trash2 size={14} /> Delete ({selectedCount})
            </button>
          )}
        </div>
      </div>

      {/* File List */}
      <div style={{ 
        backgroundColor: colors.card, 
        border: `1px solid ${colors.border}`, 
        borderRadius: '12px', overflow: 'hidden' 
      }}>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: '40px 1fr 100px 140px 100px 80px', 
          padding: '10px 16px', 
          borderBottom: `1px solid ${colors.border}`, 
          backgroundColor: colors.white, 
          gap: '8px' 
        }}>
          <span></span>
          <span style={{ fontSize: '11px', fontWeight: 600, color: colors.textMuted, textTransform: 'uppercase' }}>Name</span>
          <span style={{ fontSize: '11px', fontWeight: 600, color: colors.textMuted, textTransform: 'uppercase' }}>Size</span>
          <span style={{ fontSize: '11px', fontWeight: 600, color: colors.textMuted, textTransform: 'uppercase' }}>Uploaded</span>
          <span style={{ fontSize: '11px', fontWeight: 600, color: colors.textMuted, textTransform: 'uppercase' }}>By</span>
          <span style={{ fontSize: '11px', fontWeight: 600, color: colors.textMuted, textTransform: 'uppercase' }}>Project</span>
        </div>
        
        {allFiles.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: colors.textMuted }}>
            <Database size={32} style={{ opacity: 0.3, marginBottom: '12px' }} />
            <p style={{ margin: 0 }}>No files found</p>
          </div>
        ) : (
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {allFiles.map((file) => {
              const isSelected = file.type === 'structured' 
                ? selectedStructured.has(file.key) 
                : selectedDocs.has(file.key);
              return (
                <div 
                  key={file.key} 
                  style={{ 
                    display: 'grid', 
                    gridTemplateColumns: '40px 1fr 100px 140px 100px 80px', 
                    padding: '12px 16px', 
                    borderBottom: `1px solid ${colors.border}`, 
                    alignItems: 'center', 
                    gap: '8px',
                    backgroundColor: isSelected ? `${colors.primary}10` : 'transparent'
                  }}
                >
                  <button 
                    onClick={() => toggleSelect(file.key, file.type)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                  >
                    {isSelected ? 
                      <CheckSquare size={16} color={colors.primary} /> : 
                      <Square size={16} color={colors.textMuted} />
                    }
                  </button>
                  <div>
                    <span style={{ fontSize: '13px', fontWeight: 500, color: colors.text }}>
                      {file.filename}
                    </span>
                    <span style={{ 
                      marginLeft: '8px', padding: '2px 6px', 
                      backgroundColor: file.type === 'structured' ? `${colors.primary}15` : `${colors.accent}15`, 
                      color: file.type === 'structured' ? colors.primary : colors.accent, 
                      borderRadius: '4px', fontSize: '10px', fontWeight: 600 
                    }}>
                      {file.type === 'structured' ? 'TABLE' : 'DOC'}
                    </span>
                  </div>
                  <span style={{ fontSize: '12px', color: colors.textMuted }}>
                    {file.type === 'structured' 
                      ? `${(file.total_rows || 0).toLocaleString()} rows` 
                      : `${file.chunk_count || file.chunks || 0} chunks`
                    }
                  </span>
                  <span style={{ fontSize: '12px', color: colors.textMuted }}>
                    {formatDate(file.loaded_at || file.uploaded_at || file.created_at)}
                  </span>
                  <span style={{ fontSize: '12px', color: colors.textMuted }}>
                    {(file.uploaded_by || 'system').split('@')[0]}
                  </span>
                  <span style={{ 
                    fontSize: '11px', padding: '3px 8px', 
                    backgroundColor: getProjectName(file.project) === 'GLOBAL' ? `${colors.accent}15` : `${colors.primary}15`, 
                    color: getProjectName(file.project) === 'GLOBAL' ? colors.accent : colors.primary, 
                    borderRadius: '4px', fontWeight: 500 
                  }}>
                    {getProjectName(file.project)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Deep Clean Modal */}
      {showDeepCleanModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div style={{
            background: colors.cardBg, borderRadius: 12, padding: '24px',
            maxWidth: 500, width: '90%', maxHeight: '80vh', overflow: 'auto',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: `${colors.warning}15`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Zap size={20} color={colors.warning} />
              </div>
              <div>
                <h3 style={{ margin: 0, color: colors.text }}>Deep Clean</h3>
                <p style={{ margin: 0, fontSize: '13px', color: colors.textMuted }}>
                  Remove orphaned data across all storage systems
                </p>
              </div>
            </div>

            <div style={{
              background: colors.background, border: `1px solid ${colors.border}`,
              borderRadius: 8, padding: '16px', marginBottom: '16px',
            }}>
              <p style={{ margin: '0 0 12px', fontSize: '14px', color: colors.text, fontWeight: 500 }}>
                This will clean orphaned entries from:
              </p>
              <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: colors.textMuted, lineHeight: 1.6 }}>
                <li>ChromaDB vector chunks (deleted files)</li>
                <li>DuckDB metadata tables</li>
                <li>Supabase document records</li>
                <li>Playbook scan cache</li>
              </ul>
            </div>

            <label style={{
              display: 'flex', alignItems: 'flex-start', gap: '12px',
              padding: '12px 16px',
              background: forceClean ? `${colors.scarletSage}15` : colors.background,
              border: `1px solid ${forceClean ? colors.scarletSage + '40' : colors.border}`,
              borderRadius: 8, marginBottom: '16px', cursor: 'pointer',
            }}>
              <input
                type="checkbox"
                checked={forceClean}
                onChange={(e) => setForceClean(e.target.checked)}
                style={{ marginTop: 2 }}
              />
              <div>
                <div style={{ fontSize: '14px', fontWeight: 500, color: forceClean ? colors.scarletSage : colors.text }}>
                  Force clean (full wipe)
                </div>
                <div style={{ fontSize: '12px', color: colors.textMuted, marginTop: 2 }}>
                  Use if Registry is empty and you want to clear all backend data.
                </div>
              </div>
            </label>

            {deepCleanResult && (
              <div style={{
                background: deepCleanResult.success ? `${colors.primary}15` : `${colors.scarletSage}15`,
                border: `1px solid ${deepCleanResult.success ? colors.primary : colors.scarletSage}40`,
                borderRadius: 8, padding: '16px', marginBottom: '16px',
              }}>
                {deepCleanResult.success ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CheckCircle size={16} color={colors.primary} />
                    <span style={{ fontWeight: 600, color: colors.primary }}>
                      Cleaned {deepCleanResult.total_cleaned} orphaned items
                    </span>
                  </div>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <XCircle size={16} color={colors.scarletSage} />
                    <span style={{ fontWeight: 600, color: colors.scarletSage }}>
                      {deepCleanResult.error || 'Clean failed'}
                    </span>
                  </div>
                )}
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => { setShowDeepCleanModal(false); setDeepCleanResult(null); setForceClean(false); }}
                style={{
                  padding: '10px 20px', border: `1px solid ${colors.border}`,
                  borderRadius: 8, background: colors.cardBg, color: colors.text,
                  fontSize: '14px', fontWeight: 500, cursor: 'pointer',
                }}
              >
                Close
              </button>
              {!deepCleanResult?.success && (
                <button
                  onClick={handleDeepClean}
                  disabled={deepCleanLoading}
                  style={{
                    padding: '10px 20px', border: 'none',
                    borderRadius: 8, background: colors.warning, color: 'white',
                    fontSize: '14px', fontWeight: 600, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: '8px',
                    opacity: deepCleanLoading ? 0.7 : 1,
                  }}
                >
                  {deepCleanLoading ? (
                    <>
                      <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                      Cleaning...
                    </>
                  ) : (
                    <>
                      <Zap size={16} />
                      Run Deep Clean
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
