/**
 * DataPage.jsx - Single-Flow Data Management
 * ===========================================
 * 
 * Deploy to: frontend/src/pages/DataPage.jsx
 * 
 * Features:
 * - Two-column layout: Upload (sticky) | Files
 * - Truth type selection with hover tooltips
 * - Real-time upload progress
 * - "Just Added" immediate feedback
 * - Mission Control color scheme
 */

import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { 
  Upload as UploadIcon, FileText, Database, CheckCircle, XCircle, 
  Loader2, ChevronDown, ChevronRight, Trash2, RefreshCw, 
  HardDrive, User, Calendar, Sparkles, Clock, FileSpreadsheet, Search,
  Settings, BookOpen, AlertCircle, Target, BarChart3, Server
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useProject } from '../context/ProjectContext';
import { useUpload } from '../context/UploadContext';
import { Tooltip } from '../components/ui';
import api from '../services/api';
// import ProjectContext from '../components/ProjectContext'; // TODO: deploy component first

// ============================================================================
// BRAND COLORS (from Mission Control)
// ============================================================================
const brandColors = {
  primary: '#83b16d',
  accent: '#285390',
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

// Five Truths icon & color mapping (consistent across app - matches Dashboard)
const TRUTH_ICONS = {
  reality: { icon: Database, color: '#285390' },
  intent: { icon: Target, color: '#2766b1' },
  configuration: { icon: Server, color: '#7aa866' },
  reference: { icon: FileText, color: '#5f4282' },
  regulatory: { icon: AlertCircle, color: '#993c44' },
};

// File type icons and colors for upload differentiation
const FILE_TYPE_CONFIG = {
  xlsx: { bg: '#285390', label: 'XLS', icon: FileSpreadsheet },
  xls: { bg: '#285390', label: 'XLS', icon: FileSpreadsheet },
  csv: { bg: '#5f4282', label: 'CSV', icon: FileText },
  pdf: { bg: '#993c44', label: 'PDF', icon: FileText },
  docx: { bg: '#2766b1', label: 'DOC', icon: FileText },
  doc: { bg: '#2766b1', label: 'DOC', icon: FileText },
  txt: { bg: '#64748b', label: 'TXT', icon: FileText },
  md: { bg: '#64748b', label: 'MD', icon: FileText },
};

// Helper to get file type info from filename
const getFileTypeInfo = (filename) => {
  if (!filename) return { bg: '#64748b', label: 'FILE', icon: FileText };
  const ext = filename.split('.').pop()?.toLowerCase();
  return FILE_TYPE_CONFIG[ext] || { bg: '#64748b', label: ext?.toUpperCase() || 'FILE', icon: FileText };
};


// ============================================================================
// MAIN PAGE
// ============================================================================
export default function DataPage() {
  const { colors, darkMode } = useTheme();
  const { activeProject, projects, selectProject, loading: projectsLoading } = useProject();
  
  // Shared state for scope toggle - lifted up so FilesPanel can filter accordingly
  const [targetScope] = useState('project'); // Project-only scope (global moved to Admin > Global Knowledge)
  
  // Merge theme colors with brand colors
  const c = { ...colors, ...brandColors };
  
  // If no project selected, show project selector
  if (!activeProject && !projectsLoading) {
    return (
      <div style={{ padding: '2rem' }}>
        {/* Page Header */}
        <div style={{ marginBottom: '2rem' }}>
          <h1 style={{ 
            margin: 0, 
            fontSize: '20px', 
            fontWeight: 600, 
            color: c.text, 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px',
            fontFamily: "'Sora', sans-serif"
          }}>
            <div style={{ 
              width: '36px', 
              height: '36px', 
              borderRadius: '10px', 
              backgroundColor: c.primary, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}>
              <Database size={20} color="#ffffff" />
            </div>
            Project Data
          </h1>
          <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: c.textMuted }}>
            Select a project to upload and manage data
          </p>
        </div>
        
        {/* Project Selector */}
        <div style={{ 
          maxWidth: '600px',
          margin: '0 auto',
          padding: '2rem',
          background: c.cardBg,
          border: `1px solid ${c.border}`,
          borderRadius: '12px'
        }}>
          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '16px',
              background: `${c.primary}15`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1rem'
            }}>
              <HardDrive size={28} color={c.primary} />
            </div>
            <h2 style={{ 
              fontFamily: "'Sora', sans-serif",
              fontSize: '1.25rem',
              fontWeight: 600,
              color: c.text,
              marginBottom: '0.5rem'
            }}>
              Select a Project
            </h2>
            <p style={{ color: c.textMuted, fontSize: '0.9rem' }}>
              Choose a project to upload files and manage data
            </p>
          </div>
          
          {projects.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '1rem' }}>
              <p style={{ color: c.textMuted, marginBottom: '1rem' }}>No projects yet</p>
              <a 
                href="/projects/new"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem 1.5rem',
                  background: c.primary,
                  color: '#fff',
                  borderRadius: '8px',
                  textDecoration: 'none',
                  fontWeight: 500,
                  fontSize: '0.9rem'
                }}
              >
                Create Your First Project
              </a>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {projects.map(project => (
                <button
                  key={project.id}
                  onClick={() => selectProject(project)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    padding: '1rem',
                    background: c.background,
                    border: `1px solid ${c.border}`,
                    borderRadius: '8px',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.2s'
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.borderColor = c.primary;
                    e.currentTarget.style.background = `${c.primary}08`;
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.borderColor = c.border;
                    e.currentTarget.style.background = c.background;
                  }}
                >
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '8px',
                    background: `${c.accent}15`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}>
                    <User size={18} color={c.accent} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ 
                      fontWeight: 600, 
                      color: c.text,
                      fontSize: '0.95rem',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {project.name}
                    </div>
                    <div style={{ 
                      fontSize: '0.8rem', 
                      color: c.textMuted,
                      marginTop: '2px'
                    }}>
                      {project.customer || 'No customer'}
                      {project.code && <span style={{ marginLeft: '0.5rem', opacity: 0.7 }}>({project.code})</span>}
                    </div>
                  </div>
                  <ChevronRight size={18} color={c.textMuted} />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }
  
  return (
    <div>
      {/* Page Header */}
      <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ 
            margin: 0, 
            fontSize: '20px', 
            fontWeight: 600, 
            color: c.text, 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px',
            fontFamily: "'Sora', sans-serif"
          }}>
            <div style={{ 
              width: '36px', 
              height: '36px', 
              borderRadius: '10px', 
              backgroundColor: c.primary, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}>
              <Database size={20} color="#ffffff" />
            </div>
            Data Management
          </h1>
          <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: c.textMuted }}>
            {targetScope === 'project' 
              ? (activeProject ? `Project: ${activeProject.name}` : 'Select a project to get started')
              : 'Reference Library (Global)'}
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <Tooltip title="Data Explorer" detail="Explore tables, columns, relationships, and data health across your project." action="View classifications and run compliance checks">
            <Link 
              to="/data/explorer" 
              style={{ 
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.5rem 1rem', background: `${c.accent}15`, border: `1px solid ${c.accent}40`,
                borderRadius: 8, color: c.accent, fontSize: '0.85rem', textDecoration: 'none',
                transition: 'all 0.2s', fontWeight: 500, whiteSpace: 'nowrap'
              }}
            >
              <Search size={16} />
              Data Explorer
            </Link>
          </Tooltip>
          <Tooltip title="Register Extractor" detail="Extract structured data from PDF registers like payroll reports and tax documents." action="Upload PDFs to create queryable tables">
            <Link 
              to="/vacuum" 
              style={{ 
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.5rem 1rem', background: `${c.primary}15`, border: `1px solid ${c.primary}40`,
                borderRadius: 8, color: c.primary, fontSize: '0.85rem', textDecoration: 'none',
                transition: 'all 0.2s', fontWeight: 500, whiteSpace: 'nowrap'
              }}
            >
              <Sparkles size={16} />
              Register Extractor
            </Link>
          </Tooltip>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '1.5rem', alignItems: 'start' }}>
        <UploadPanel c={c} project={activeProject} targetScope={targetScope} />
        <FilesPanel c={c} project={activeProject} targetScope={targetScope} />
      </div>
    </div>
  );
}


// ============================================================================
// UPLOAD PANEL (Left - Sticky)
// ============================================================================
function UploadPanel({ c, project, targetScope }) {
  const { addUpload, uploads } = useUpload();
  const [truthType, setTruthType] = useState('reality');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);
  
  // Domain selection state
  const [selectedDomain, setSelectedDomain] = useState('auto');
  const [customDomains, setCustomDomains] = useState([]);
  const [showDomainModal, setShowDomainModal] = useState(false);
  const [newDomainName, setNewDomainName] = useState('');
  const [newDomainSignals, setNewDomainSignals] = useState('');
  
  // System selection state (for vendor docs)
  const [selectedSystem, setSelectedSystem] = useState('');
  const [allSystems, setAllSystems] = useState([]);
  
  // Fetch systems from API (same source as Projects page)
  useEffect(() => {
    api.get('/reference/systems')
      .then(res => {
        const systems = res.data || [];
        setAllSystems(systems);
        // Default to first system if available
        if (systems.length > 0 && !selectedSystem) {
          setSelectedSystem(systems[0].code);
        }
      })
      .catch(err => {
        console.error('Failed to load systems:', err);
        // Fallback to basic list
        setAllSystems([
          { code: 'ukg_pro', name: 'UKG Pro' },
          { code: 'ukg_ready', name: 'UKG Ready' },
          { code: 'ukg_wfm', name: 'UKG WFM' },
          { code: 'universal', name: 'Universal' }
        ]);
        setSelectedSystem('ukg_pro');
      });
  }, []);
  
  // Built-in domains
  const builtInDomains = [
    { value: 'auto', label: '🔮 Auto-detect', desc: 'Let AI determine the domain' },
    { value: 'hr', label: 'HR', desc: 'Employee, hire dates, terminations' },
    { value: 'payroll', label: 'Payroll', desc: 'Earnings, deductions, pay periods' },
    { value: 'tax', label: 'Tax', desc: 'Withholdings, W2, FICA, SUI' },
    { value: 'benefits', label: 'Benefits', desc: 'Plans, coverage, enrollment' },
    { value: 'time', label: '⏱️ Time', desc: 'Hours, timecards, PTO, overtime' },
  ];
  
  // Load custom domains on mount
  useEffect(() => {
    const loadCustomDomains = async () => {
      try {
        const res = await api.get('/custom-domains');
        if (res.data?.domains) {
          setCustomDomains(res.data.domains);
        }
      } catch (e) {
        console.log('Custom domains not available yet');
      }
    };
    loadCustomDomains();
  }, []);
  
  // Create custom domain
  const handleCreateDomain = async () => {
    if (!newDomainName.trim()) return;
    
    const signals = newDomainSignals.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
    
    try {
      const res = await api.post('/custom-domains', {
        name: newDomainName.trim().toLowerCase().replace(/\s+/g, '_'),
        label: newDomainName.trim(),
        signals: signals
      });
      
      if (res.data?.domain) {
        setCustomDomains(prev => [...prev, res.data.domain]);
        setSelectedDomain(res.data.domain.value);
      }
      
      setShowDomainModal(false);
      setNewDomainName('');
      setNewDomainSignals('');
    } catch (e) {
      console.error('Failed to create domain:', e);
      alert('Failed to create domain');
    }
  };

  // Truth type options with tooltip content
  const truthTypes = targetScope === 'project' 
    ? [
        { 
          value: 'reality', 
          label: 'Employee & Transactional Data', 
          desc: 'Demographics, payroll records, time entries',
          tooltip: {
            title: 'Reality Data',
            detail: 'The actual data - employee records, payroll transactions, time entries. What EXISTS in the system.',
            action: 'Upload employee files, payroll registers, demographic exports'
          }
        },
        { 
          value: 'intent', 
          label: 'Customer Requirements', 
          desc: 'SOWs, meeting notes, what they want',
          tooltip: {
            title: 'Customer Requirements',
            detail: 'Documents that describe what the customer wants to achieve. Used by AI to understand project goals.',
            action: 'Upload SOWs, requirements docs, meeting notes'
          }
        },
        { 
          value: 'configuration', 
          label: 'Customer Setup', 
          desc: 'Their code tables and configured values',
          tooltip: {
            title: 'Customer Configuration',
            detail: 'The customer\'s actual system setup - their code tables, mappings, and configured values.',
            action: 'Upload earnings codes, deduction mappings, org structure'
          }
        },
      ]
    : [
        { 
          value: 'reference', 
          label: 'Vendor Docs & How-To', 
          desc: 'Product docs, configuration guides',
          tooltip: {
            title: 'Vendor Documentation',
            detail: 'Product documentation and configuration guides from the software vendor. Explains HOW to configure the system.',
            action: 'Upload UKG guides, ADP manuals, Workday docs'
          }
        },
        { 
          value: 'regulatory', 
          label: 'Laws, Rules & Compliance', 
          desc: 'IRS, state, federal, audit requirements',
          tooltip: {
            title: 'Regulatory & Compliance',
            detail: 'Official government requirements, audit controls, and compliance mandates - IRS publications, state tax rules, SOC 2 checklists.',
            action: 'Upload IRS Pub 15, Secure 2.0, SOC 2, audit guides'
          }
        },
      ];

  useEffect(() => {
    setTruthType(targetScope === 'project' ? 'reality' : 'reference');
  }, [targetScope]);

  const handleFiles = (files) => {
    const projectId = targetScope === 'project' ? project?.id : 'Global/Universal';
    const projectName = targetScope === 'project' ? project?.name : 'Reference Library';
    
    if (targetScope === 'project' && !project?.id) {
      alert('Please select a project first');
      return;
    }
    
    Array.from(files).forEach(file => {
      // For regulatory docs, trigger rule extraction
      const isRuleSource = truthType === 'regulatory';
      const isVendorDocs = truthType === 'reference';
      
      addUpload(file, projectId, projectName, { 
        truth_type: truthType,
        standards_mode: isRuleSource,
        domain: selectedDomain !== 'auto' ? selectedDomain : (isRuleSource ? 'regulatory' : undefined),
        system: isVendorDocs ? selectedSystem : undefined  // Only for vendor docs
      });
    });
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  const activeUploads = uploads.filter(u => u.status === 'uploading' || u.status === 'processing');

  return (
    <div style={{ 
      position: 'sticky', top: '1rem',
      background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 12,
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
    }}>
      {/* Header - Project Files only */}
      <div style={{ 
        padding: '0.875rem 1rem', 
        background: c.background, 
        borderTopLeftRadius: 12, 
        borderTopRightRadius: 12,
        borderBottom: `1px solid ${c.border}`
      }}>
        <span style={{ fontWeight: 600, fontSize: '0.9rem', color: c.text }}>
          Project Data
        </span>
        <span style={{ fontSize: '0.75rem', color: c.textMuted, marginLeft: '0.5rem' }}>
          Customer-specific documents
        </span>
      </div>

      <div style={{ padding: '1rem' }}>
        {/* Truth Type Selection */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ 
            fontSize: '0.7rem', fontWeight: 600, color: c.textMuted, 
            textTransform: 'uppercase', letterSpacing: '0.05em', 
            display: 'block', marginBottom: '0.5rem' 
          }}>
            Document Type
          </label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {truthTypes.map(tt => {
              const truthColor = TRUTH_ICONS[tt.value]?.color || c.primary;
              const isSelected = truthType === tt.value;
              const TruthIcon = TRUTH_ICONS[tt.value]?.icon || FileText;
              return (
                <Tooltip 
                  key={tt.value}
                  title={tt.tooltip.title}
                  detail={tt.tooltip.detail}
                  action={tt.tooltip.action}
                  position="right"
                >
                  <button
                    onClick={() => setTruthType(tt.value)}
                    style={{
                      display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
                      padding: '0.75rem', borderRadius: 8, textAlign: 'left',
                      border: isSelected 
                        ? `2px solid ${truthColor}` 
                        : `1px solid ${c.border}`,
                      borderLeft: `4px solid ${truthColor}`,
                      background: isSelected ? `${truthColor}12` : 'transparent',
                      cursor: 'pointer', transition: 'all 0.15s', width: '100%'
                    }}
                  >
                    <div style={{
                      width: 32, height: 32, borderRadius: 6,
                      background: isSelected ? truthColor : `${truthColor}15`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0
                    }}>
                      <TruthIcon size={16} color={isSelected ? '#ffffff' : truthColor} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.85rem', color: c.text }}>{tt.label}</div>
                      <div style={{ fontSize: '0.75rem', color: c.textMuted, marginTop: '0.15rem' }}>{tt.desc}</div>
                    </div>
                  </button>
                </Tooltip>
              );
            })}
          </div>
        </div>

        {/* Domain Selection - Only for Reality/Configuration (structured data) */}
        {(truthType === 'reality' || truthType === 'configuration') && targetScope === 'project' && (
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              fontSize: '0.7rem', fontWeight: 600, color: c.textMuted, 
              textTransform: 'uppercase', letterSpacing: '0.05em', 
              display: 'block', marginBottom: '0.5rem' 
            }}>
              Domain (optional)
            </label>
            <select
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value)}
              style={{
                width: '100%',
                padding: '0.6rem 0.75rem',
                borderRadius: 8,
                border: `2px solid ${selectedDomain === 'auto' ? c.primary : c.border}`,
                background: selectedDomain === 'auto' ? `${c.primary}20` : c.background,
                color: c.text,
                fontSize: '0.85rem',
                cursor: 'pointer',
                marginBottom: '0.5rem',
                fontWeight: 600
              }}
            >
              {builtInDomains.map(d => (
                <option key={d.value} value={d.value}>{d.label} - {d.desc}</option>
              ))}
              {customDomains.length > 0 && (
                <optgroup label="Custom Domains">
                  {customDomains.map(d => (
                    <option key={d.value} value={d.value}>  {d.label}</option>
                  ))}
                </optgroup>
              )}
            </select>
            <button
              onClick={() => setShowDomainModal(true)}
              style={{
                width: '100%',
                padding: '0.6rem',
                borderRadius: 8,
                border: `2px solid ${c.accent}`,
                background: `${c.accent}`,
                color: c.white,
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.35rem',
                transition: 'all 0.2s'
              }}
            >
              <Sparkles size={14} /> Create Custom Domain
            </button>
          </div>
        )}

        {/* System Selection - Only for Vendor Docs (reference) */}
        {truthType === 'reference' && targetScope === 'global' && (
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              fontSize: '0.7rem', fontWeight: 600, color: c.textMuted, 
              textTransform: 'uppercase', letterSpacing: '0.05em', 
              display: 'block', marginBottom: '0.5rem' 
            }}>
              System <span style={{ color: c.primary }}>*</span>
            </label>
            <select
              value={selectedSystem}
              onChange={(e) => setSelectedSystem(e.target.value)}
              style={{
                width: '100%',
                padding: '0.6rem 0.75rem',
                borderRadius: 8,
                border: `2px solid ${c.primary}`,
                background: `${c.primary}10`,
                color: c.text,
                fontSize: '0.85rem',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              {allSystems.map(s => (
                <option key={s.code} value={s.code}>
                  {s.name}{s.vendor ? ` (${s.vendor})` : ''}
                </option>
              ))}
            </select>
            <p style={{ 
              fontSize: '0.7rem', color: c.textMuted, marginTop: '0.4rem', 
              lineHeight: 1.4 
            }}>
              Tag docs with their system so projects only see relevant vendor docs.
            </p>
          </div>
        )}

        {/* Custom Domain Modal */}
        {showDomainModal && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', zIndex: 1000
          }} onClick={() => setShowDomainModal(false)}>
            <div style={{
              background: c.cardBg, borderRadius: 12, padding: '1.5rem',
              width: '90%', maxWidth: 400, boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
            }} onClick={e => e.stopPropagation()}>
              <h3 style={{ margin: '0 0 1rem', color: c.text, fontSize: '1.1rem' }}>
                Create Custom Domain
              </h3>
              <p style={{ fontSize: '0.8rem', color: c.textMuted, marginBottom: '1rem' }}>
                Custom domains help AI classify your data. Signal words trigger auto-detection on future uploads.
              </p>
              
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: c.text, display: 'block', marginBottom: '0.35rem' }}>
                  Domain Name
                </label>
                <input
                  type="text"
                  placeholder="e.g., Workers Comp"
                  value={newDomainName}
                  onChange={(e) => setNewDomainName(e.target.value)}
                  style={{
                    width: '100%', padding: '0.6rem 0.75rem', borderRadius: 6,
                    border: `1px solid ${c.border}`, background: c.background,
                    color: c.text, fontSize: '0.85rem'
                  }}
                />
              </div>
              
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: c.text, display: 'block', marginBottom: '0.35rem' }}>
                  Signal Words (comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g., claim, injury, osha, incident, comp"
                  value={newDomainSignals}
                  onChange={(e) => setNewDomainSignals(e.target.value)}
                  style={{
                    width: '100%', padding: '0.6rem 0.75rem', borderRadius: 6,
                    border: `1px solid ${c.border}`, background: c.background,
                    color: c.text, fontSize: '0.85rem'
                  }}
                />
                <p style={{ fontSize: '0.7rem', color: c.textMuted, marginTop: '0.35rem' }}>
                  When columns contain these words, this domain will be auto-detected
                </p>
              </div>
              
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                  onClick={() => setShowDomainModal(false)}
                  style={{
                    flex: 1, padding: '0.6rem', borderRadius: 6,
                    border: `1px solid ${c.border}`, background: 'transparent',
                    color: c.text, cursor: 'pointer', fontSize: '0.85rem'
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateDomain}
                  disabled={!newDomainName.trim()}
                  style={{
                    flex: 1, padding: '0.6rem', borderRadius: 6,
                    border: 'none', background: c.primary,
                    color: '#fff', cursor: newDomainName.trim() ? 'pointer' : 'not-allowed',
                    fontSize: '0.85rem', fontWeight: 600,
                    opacity: newDomainName.trim() ? 1 : 0.5
                  }}
                >
                  Create Domain
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Drop Zone */}
        <input 
          type="file" ref={fileInputRef} style={{ display: 'none' }} 
          multiple accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md"
          onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }}
        />
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? c.primary : c.border}`,
            borderRadius: 10, padding: '1.5rem 1rem', textAlign: 'center',
            cursor: 'pointer', background: dragOver ? `${c.primary}10` : c.background,
            transition: 'all 0.2s'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '0.75rem' }}>
            <UploadIcon size={28} style={{ color: c.primary }} />
          </div>
          <p style={{ fontWeight: 600, color: c.text, margin: '0 0 0.5rem', fontSize: '0.9rem' }}>
            Drop files or click to browse
          </p>
          {/* File type badges */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            {[
              { label: 'XLS', bg: '#285390' },
              { label: 'CSV', bg: '#5f4282' },
              { label: 'PDF', bg: '#993c44' },
              { label: 'DOC', bg: '#2766b1' },
            ].map(ft => (
              <span key={ft.label} style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '0.2rem 0.5rem',
                borderRadius: 4,
                background: `${ft.bg}15`,
                color: ft.bg,
                letterSpacing: '0.03em'
              }}>
                {ft.label}
              </span>
            ))}
          </div>
        </div>

        {/* Active Uploads */}
        {activeUploads.length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <label style={{ 
              fontSize: '0.7rem', fontWeight: 600, color: c.electricBlue,
              textTransform: 'uppercase', letterSpacing: '0.05em',
              display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.5rem' 
            }}>
              <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />
              Processing ({activeUploads.length})
            </label>
            {activeUploads.map(upload => {
              const fileType = getFileTypeInfo(upload.filename);
              return (
                <div key={upload.id} style={{
                  display: 'flex', alignItems: 'center', gap: '0.75rem',
                  padding: '0.75rem', background: `${c.electricBlue}10`,
                  border: `1px solid ${c.electricBlue}30`, borderRadius: 8, marginBottom: '0.5rem'
                }}>
                  {/* File type badge */}
                  <div style={{
                    width: 32, height: 32, borderRadius: 6,
                    background: fileType.bg, color: '#fff',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '0.6rem', fontWeight: 700, flexShrink: 0
                  }}>
                    {fileType.label}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 500, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {upload.filename}
                    </div>
                    <div style={{ height: 4, background: c.border, borderRadius: 2, marginTop: '0.35rem', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${upload.progress || 0}%`, background: c.electricBlue, borderRadius: 2, transition: 'width 0.3s' }} />
                    </div>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: c.electricBlue, fontWeight: 600 }}>
                    {upload.status === 'uploading' ? `${upload.progress || 0}%` : 'Processing...'}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}


// ============================================================================
// FILES PANEL (Right)
// ============================================================================
function FilesPanel({ c, project, targetScope }) {
  const { uploads } = useUpload();
  const [structuredData, setStructuredData] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [referenceFiles, setReferenceFiles] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedSections, setExpandedSections] = useState({ structured: true, documents: true, reference: true });
  
  // Track completed uploads to auto-refresh
  const prevCompletedRef = useRef(new Set());

  useEffect(() => { loadData(); }, [project?.id, targetScope]);
  
  // Auto-refresh when uploads complete
  useEffect(() => {
    const completedIds = new Set(
      uploads.filter(u => u.status === 'completed').map(u => u.id)
    );
    
    // Check if there are NEW completions (not just existing ones)
    const hasNewCompletions = [...completedIds].some(id => !prevCompletedRef.current.has(id));
    
    if (hasNewCompletions && completedIds.size > 0) {
      // Small delay to let backend finish any async work
      const timer = setTimeout(() => {
        loadData();
      }, 1000);
      
      prevCompletedRef.current = completedIds;
      return () => clearTimeout(timer);
    }
    
    prevCompletedRef.current = completedIds;
  }, [uploads]);

  const loadData = async () => {
    setLoading(true);
    try {
      // Use fast /files endpoint instead of slow /platform
      // When in global scope (Reference Library), don't filter by project
      const projectName = project?.name || project?.id || '';
      const shouldFilterByProject = targetScope !== 'global' && projectName;
      
      const [filesRes, refRes] = await Promise.all([
        api.get(`/files${shouldFilterByProject ? `?project=${encodeURIComponent(projectName)}` : ''}`).catch(() => ({ data: {} })),
        api.get('/status/references').catch(() => ({ data: { files: [], rules: [] } })),
      ]);
      
      // Map files response to expected format
      const filesData = filesRes.data;
      const structuredData = {
        files: filesData?.files || [],
        total_rows: filesData?.total_rows || 0,
        total_files: filesData?.total_files || 0,
        total_tables: filesData?.total_tables || 0,
      };
      
      // Documents from files that have chunks (chromadb or hybrid)
      const documents = {
        documents: (filesData?.files || []).filter(f => 
          f.type === 'chromadb' || f.type === 'hybrid' || (f.chunks && f.chunks > 0)
        ),
        count: (filesData?.files || []).filter(f => f.chunks > 0).length,
      };
      
      setStructuredData(structuredData);
      setDocuments(documents);
      setReferenceFiles(refRes.data);
    } catch (err) {
      console.error('Failed to load:', err);
    } finally {
      setLoading(false);
    }
  };

  // Filter based on scope
  const isGlobalScope = targetScope === 'global';
  
  const structuredFiles = (structuredData?.files || []).filter(f => {
    if (isGlobalScope) {
      return f.is_global || f.project === 'Global/Universal' || f.project === 'Reference Library' || f.project === '__STANDARDS__';
    }
    return !project || f.project === project.id || f.project === project.name;
  });
  
  const docs = (documents?.documents || []).filter(d => {
    if (isGlobalScope) {
      return d.is_global || d.project === 'Global/Universal' || d.project === 'Reference Library' || d.project === '__STANDARDS__';
    }
    return !project || d.project === project.id || d.project === project.name;
  });
  
  // Reference library files (always global)
  const refFiles = referenceFiles?.files || [];
  const extractedRules = Array.isArray(referenceFiles?.rules) ? referenceFiles.rules : [];

  const recentlyCompleted = uploads.filter(u => u.status === 'completed').slice(0, 5);
  const totalTables = structuredFiles.reduce((sum, f) => sum + (f.sheets?.length || 1), 0);
  const totalRows = structuredData?.total_rows || 0;

  // Five Truths helpers
  const getTruthIcon = (tt) => {
    const config = TRUTH_ICONS[tt] || { icon: FileText, color: c.textMuted };
    const Icon = config.icon;
    return <Icon size={18} color={config.color} />;
  };
  const getTruthLabel = (tt) => ({ reality: 'Data', intent: 'Requirements', configuration: 'Setup', reference: 'Vendor', regulatory: 'Legal/Compliance' }[tt] || '');
  const toggleSection = (section) => setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem', color: c.textMuted }}>
        <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
        <p>Loading files...</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div>
      {/* Stats Bar */}
      <div style={{ 
        display: 'flex', gap: '1.5rem', marginBottom: '1rem',
        padding: '0.875rem 1rem', background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10
      }}>
        {isGlobalScope ? (
          <>
            <Tooltip title="Reference Files" detail="Global documents in the Reference Library." action="Standards, laws, vendor docs">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'help' }}>
                <FileText size={18} style={{ color: c.accent }} />
                <span style={{ fontSize: '0.9rem', color: c.text }}><strong>{refFiles.length}</strong> files</span>
              </div>
            </Tooltip>
            <Tooltip title="Extracted Rules" detail="Compliance rules extracted from regulatory documents." action="Used in Compliance Check">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'help' }}>
                <AlertCircle size={18} style={{ color: c.electricBlue }} />
                <span style={{ fontSize: '0.9rem', color: c.text }}><strong>{extractedRules.length}</strong> rules</span>
              </div>
            </Tooltip>
            <Tooltip title="Documents" detail="Global docs chunked for AI retrieval." action="Referenced across all projects">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'help' }}>
                <Database size={18} style={{ color: c.electricBlue }} />
                <span style={{ fontSize: '0.9rem', color: c.text }}><strong>{refFiles.reduce((sum, f) => sum + (f.chunk_count || 0), 0)}</strong> chunks</span>
              </div>
            </Tooltip>
          </>
        ) : (
          <>
            <Tooltip title="Tables" detail="Total structured tables created from uploaded files." action="Click Data Explorer to view details">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'help' }}>
                <Database size={18} style={{ color: c.primary }} />
                <span style={{ fontSize: '0.9rem', color: c.text }}><strong>{totalTables}</strong> tables</span>
              </div>
            </Tooltip>
            <Tooltip title="Rows" detail="Total data rows available for querying." action="Query in AI Chat">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'help' }}>
                <HardDrive size={18} style={{ color: c.electricBlue }} />
                <span style={{ fontSize: '0.9rem', color: c.text }}><strong>{totalRows.toLocaleString()}</strong> rows</span>
              </div>
            </Tooltip>
            <Tooltip title="Documents" detail="Documents chunked for AI retrieval." action="Referenced in AI responses">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'help' }}>
                <FileText size={18} style={{ color: c.accent }} />
                <span style={{ fontSize: '0.9rem', color: c.text }}><strong>{docs.length}</strong> documents</span>
              </div>
            </Tooltip>
          </>
        )}
        <div style={{ flex: 1 }} />
        <button 
          onClick={loadData}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.35rem',
            padding: '0.4rem 0.75rem', background: 'transparent', border: `1px solid ${c.border}`,
            borderRadius: 6, fontSize: '0.8rem', color: c.textMuted, cursor: 'pointer'
          }}
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Project Context - System/Domain Detection (TODO: uncomment after deploying ProjectContext.jsx)
      {!isGlobalScope && currentProject && (
        <div style={{ marginBottom: '1rem' }}>
          <ProjectContext projectName={currentProject} compact />
        </div>
      )}
      */}

      {/* Recently Completed */}
      {recentlyCompleted.length > 0 && (
        <div style={{
          background: `${c.accent}08`, border: `1px solid ${c.accent}30`,
          borderRadius: 10, marginBottom: '1rem', overflow: 'hidden'
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.65rem 1rem', background: `${c.accent}15`,
            borderBottom: `1px solid ${c.accent}20`,
            fontWeight: 600, fontSize: '0.8rem', color: c.accent
          }}>
            <CheckCircle size={16} /> Just Added
          </div>
          {recentlyCompleted.map(upload => {
            const fileType = getFileTypeInfo(upload.filename);
            return (
              <div key={upload.id} style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem',
                padding: '0.65rem 1rem', borderBottom: `1px solid ${c.accent}15`
              }}>
                {/* File type badge */}
                <div style={{
                  width: 28, height: 28, borderRadius: 5,
                  background: fileType.bg, color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.55rem', fontWeight: 700, flexShrink: 0
                }}>
                  {fileType.label}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 500, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {upload.filename}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: c.textMuted }}>
                    {upload.result?.tables_created 
                      ? `${upload.result.tables_created} table(s), ${upload.result.total_rows?.toLocaleString() || 0} rows`
                      : upload.result?.chunks_created ? `${upload.result.chunks_created} chunks` : 'Processed'}
                  </div>
                </div>
                <CheckCircle size={16} style={{ color: c.accent }} />
              </div>
            );
          })}
          {/* Start Analysis CTA */}
          <div style={{ padding: '0.75rem 1rem', borderTop: `1px solid ${c.accent}20` }}>
            <Link to="/workspace" style={{ textDecoration: 'none' }}>
              <button style={{
                width: '100%',
                padding: '0.65rem 1rem',
                background: c.primary,
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                fontWeight: 600,
                fontSize: '0.85rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                transition: 'background 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#6b9b5a'}
              onMouseLeave={(e) => e.currentTarget.style.background = c.primary}
              >
                <Sparkles size={16} />
                Start Analyzing
              </button>
            </Link>
          </div>
        </div>
      )}

      {/* Structured Data Section */}
      <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, marginBottom: '1rem', overflow: 'hidden' }}>
        <button
          onClick={() => toggleSection('structured')}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.75rem', width: '100%',
            padding: '0.875rem 1rem', background: c.background, border: 'none',
            borderBottom: expandedSections.structured ? `1px solid ${c.border}` : 'none',
            cursor: 'pointer', textAlign: 'left'
          }}
        >
          {expandedSections.structured ? <ChevronDown size={18} style={{ color: c.textMuted }} /> : <ChevronRight size={18} style={{ color: c.textMuted }} />}
          <FileSpreadsheet size={18} style={{ color: c.primary }} />
          <span style={{ fontWeight: 600, color: c.text, flex: 1 }}>Structured Data</span>
          <span style={{ background: `${c.primary}15`, color: c.primary, padding: '0.2rem 0.6rem', borderRadius: 10, fontSize: '0.75rem', fontWeight: 600 }}>
            {structuredFiles.length}
          </span>
        </button>
        
        {expandedSections.structured && (
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {structuredFiles.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <Database size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                <p style={{ margin: 0 }}>No structured data yet</p>
              </div>
            ) : (
              structuredFiles.map((file, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', borderBottom: `1px solid ${c.border}` }}>
                  {getTruthIcon(file.truth_type)}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 500, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.filename}</div>
                    <div style={{ fontSize: '0.75rem', color: c.textMuted }}>
                      {file.sheets?.length || 1} table(s) • {(file.row_count || 0).toLocaleString()} rows
                      {file.domain && ` • ${file.domain}`}
                      {file.truth_type && !file.domain && ` • ${getTruthLabel(file.truth_type)}`}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: c.textMuted, marginTop: '0.15rem' }}>
                      {(file.uploaded_at || file.loaded_at) && new Date(file.uploaded_at || file.loaded_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })}
                      {file.uploaded_by && ` • ${file.uploaded_by.split('@')[0]}`}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Documents Section */}
      <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
        <button
          onClick={() => toggleSection('documents')}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.75rem', width: '100%',
            padding: '0.875rem 1rem', background: c.background, border: 'none',
            borderBottom: expandedSections.documents ? `1px solid ${c.border}` : 'none',
            cursor: 'pointer', textAlign: 'left'
          }}
        >
          {expandedSections.documents ? <ChevronDown size={18} style={{ color: c.textMuted }} /> : <ChevronRight size={18} style={{ color: c.textMuted }} />}
          <FileText size={18} style={{ color: c.accent }} />
          <span style={{ fontWeight: 600, color: c.text, flex: 1 }}>Documents</span>
          <span style={{ background: `${c.accent}15`, color: c.accent, padding: '0.2rem 0.6rem', borderRadius: 10, fontSize: '0.75rem', fontWeight: 600 }}>
            {docs.length}
          </span>
        </button>
        
        {expandedSections.documents && (
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {docs.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <FileText size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                <p style={{ margin: 0 }}>No documents yet</p>
              </div>
            ) : (
              docs.map((doc, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', borderBottom: `1px solid ${c.border}` }}>
                  {getTruthIcon(doc.truth_type)}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 500, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.filename}</div>
                    <div style={{ fontSize: '0.75rem', color: c.textMuted }}>
                      {doc.chunk_count || doc.chunks || 0} chunks
                      {doc.truth_type && ` • ${getTruthLabel(doc.truth_type)}`}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: c.textMuted, marginTop: '0.15rem' }}>
                      {doc.created_at && new Date(doc.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })}
                      {doc.uploaded_by && ` • ${doc.uploaded_by.split('@')[0]}`}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Reference Library Section - Only shown in global scope */}
      {isGlobalScope && (
        <div style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden', marginTop: '1rem' }}>
          <button
            onClick={() => toggleSection('reference')}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.75rem', width: '100%',
              padding: '0.875rem 1rem', background: c.background, border: 'none',
              borderBottom: expandedSections.reference ? `1px solid ${c.border}` : 'none',
              cursor: 'pointer', textAlign: 'left'
            }}
          >
            {expandedSections.reference ? <ChevronDown size={18} style={{ color: c.textMuted }} /> : <ChevronRight size={18} style={{ color: c.textMuted }} />}
            <AlertCircle size={20} color={c.royalPurple} />
            <span style={{ fontWeight: 600, color: c.text, flex: 1 }}>Reference Library Files</span>
            <span style={{ background: `${c.royalPurple}15`, color: c.royalPurple, padding: '0.2rem 0.6rem', borderRadius: 10, fontSize: '0.75rem', fontWeight: 600 }}>
              {refFiles.length} files • {extractedRules.length} rules
            </span>
          </button>
          
          {expandedSections.reference && (
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {refFiles.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
                  <AlertCircle size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                  <p style={{ margin: '0 0 0.5rem', fontWeight: 500 }}>No reference files yet</p>
                  <p style={{ margin: 0, fontSize: '0.85rem' }}>Upload regulatory docs to extract compliance rules</p>
                </div>
              ) : (
                refFiles.map((file, i) => {
                  const fileRules = extractedRules.filter(r => r.source_document === file.filename);
                  return (
                    <div key={i} style={{ 
                      display: 'flex', alignItems: 'center', gap: '0.75rem', 
                      padding: '0.75rem 1rem', 
                      borderBottom: `1px solid ${c.border}`,
                      background: fileRules.length > 0 ? `${c.royalPurple}05` : 'transparent'
                    }}>
                      {getTruthIcon(file.truth_type)}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 500, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {file.filename}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: c.textMuted, display: 'flex', gap: '0.75rem', marginTop: '0.15rem' }}>
                          <span>{getTruthLabel(file.truth_type)}</span>
                          {file.chunk_count && <span>{file.chunk_count} chunks</span>}
                          {fileRules.length > 0 && (
                            <span style={{ color: c.royalPurple, fontWeight: 500 }}>
                              {fileRules.length} rules extracted
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={async () => {
                          if (window.confirm(`Delete "${file.filename}" and its extracted rules?`)) {
                            try {
                              await api.delete(`/status/references/${encodeURIComponent(file.filename)}?confirm=true`);
                              loadData();
                            } catch (err) {
                              alert('Delete failed: ' + (err.response?.data?.detail || err.message));
                            }
                          }
                        }}
                        style={{
                          padding: '0.35rem 0.5rem', background: 'transparent', border: `1px solid ${c.border}`,
                          borderRadius: 4, cursor: 'pointer', color: c.textMuted, fontSize: '0.75rem'
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
