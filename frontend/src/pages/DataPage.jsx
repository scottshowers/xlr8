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
  HardDrive, User, Calendar, Sparkles, Clock, FileSpreadsheet, Search
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useProject } from '../context/ProjectContext';
import { useUpload } from '../context/UploadContext';
import api from '../services/api';

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

// ============================================================================
// TOOLTIP COMPONENT (from Mission Control)
// ============================================================================
function Tooltip({ children, title, detail, action, position = 'top' }) {
  const [show, setShow] = useState(false);
  
  // Position-specific styles
  const getPositionStyles = () => {
    switch (position) {
      case 'left':
        return {
          right: '100%',
          top: '50%',
          transform: 'translateY(-50%)',
          marginRight: '8px',
        };
      case 'right':
        return {
          left: '100%',
          top: '50%',
          transform: 'translateY(-50%)',
          marginLeft: '8px',
        };
      case 'bottom':
        return {
          top: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          marginTop: '8px',
        };
      default: // top
        return {
          bottom: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          marginBottom: '8px',
        };
    }
  };
  
  const getArrowStyles = () => {
    switch (position) {
      case 'left':
        return {
          right: '-6px',
          top: '50%',
          transform: 'translateY(-50%)',
          borderTop: '6px solid transparent',
          borderBottom: '6px solid transparent',
          borderLeft: `6px solid ${brandColors.text}`,
        };
      case 'right':
        return {
          left: '-6px',
          top: '50%',
          transform: 'translateY(-50%)',
          borderTop: '6px solid transparent',
          borderBottom: '6px solid transparent',
          borderRight: `6px solid ${brandColors.text}`,
        };
      case 'bottom':
        return {
          top: '-6px',
          left: '50%',
          transform: 'translateX(-50%)',
          borderLeft: '6px solid transparent',
          borderRight: '6px solid transparent',
          borderBottom: `6px solid ${brandColors.text}`,
        };
      default: // top
        return {
          bottom: '-6px',
          left: '50%',
          transform: 'translateX(-50%)',
          borderLeft: '6px solid transparent',
          borderRight: '6px solid transparent',
          borderTop: `6px solid ${brandColors.text}`,
        };
    }
  };
  
  return (
    <div 
      style={{ position: 'relative', display: 'inline-block', width: '100%' }}
      onMouseEnter={() => setShow(true)} 
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <div style={{
          position: 'absolute',
          ...getPositionStyles(),
          padding: '12px 16px',
          backgroundColor: brandColors.text,
          color: brandColors.white,
          borderRadius: '8px',
          fontSize: '12px',
          width: '260px',
          zIndex: 9999,
          boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
        }}>
          <div style={{ fontWeight: 600, marginBottom: '4px' }}>{title}</div>
          <div style={{ opacity: 0.85, lineHeight: 1.4 }}>{detail}</div>
          {action && (
            <div style={{ 
              marginTop: '8px', 
              paddingTop: '8px', 
              borderTop: '1px solid rgba(255,255,255,0.2)', 
              color: brandColors.skyBlue, 
              fontWeight: 500 
            }}>
              💡 {action}
            </div>
          )}
          <div style={{ 
            position: 'absolute', 
            width: 0, 
            height: 0,
            ...getArrowStyles(),
          }} />
        </div>
      )}
    </div>
  );
}

// ============================================================================
// MAIN PAGE
// ============================================================================
export default function DataPage() {
  const { colors, darkMode } = useTheme();
  const { activeProject } = useProject();
  
  // Shared state for scope toggle - lifted up so FilesPanel can filter accordingly
  const [targetScope, setTargetScope] = useState('project');
  
  // Merge theme colors with brand colors
  const c = { ...colors, ...brandColors };
  
  return (
    <div style={{ padding: '1.5rem', maxWidth: '1400px', margin: '0 auto', background: c.background, minHeight: '100vh' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, color: c.text, margin: 0, fontFamily: "'Sora', sans-serif" }}>
            Data Management
          </h1>
          <p style={{ fontSize: '0.85rem', color: c.textMuted, margin: '0.25rem 0 0' }}>
            {targetScope === 'project' 
              ? (activeProject ? `Project: ${activeProject.name}` : 'Select a project to get started')
              : 'Reference Library (Global)'}
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <Link 
            to="/data/explorer" 
            style={{ 
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.5rem 1rem', background: c.cardBg, border: `1px solid ${c.border}`,
              borderRadius: 8, color: c.text, fontSize: '0.85rem', textDecoration: 'none',
              transition: 'all 0.2s'
            }}
          >
            <Search size={16} style={{ color: c.accent }} />
            Data Explorer
          </Link>
          <Link 
            to="/vacuum" 
            style={{ 
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.5rem 1rem', background: c.cardBg, border: `1px solid ${c.border}`,
              borderRadius: 8, color: c.text, fontSize: '0.85rem', textDecoration: 'none',
              transition: 'all 0.2s'
            }}
          >
            <Sparkles size={16} style={{ color: c.primary }} />
            Register Extractor
          </Link>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '1.5rem', alignItems: 'start' }}>
        <UploadPanel c={c} project={activeProject} targetScope={targetScope} setTargetScope={setTargetScope} />
        <FilesPanel c={c} project={activeProject} targetScope={targetScope} />
      </div>
    </div>
  );
}


// ============================================================================
// UPLOAD PANEL (Left - Sticky)
// ============================================================================
function UploadPanel({ c, project, targetScope, setTargetScope }) {
  const { addUpload, uploads } = useUpload();
  const [truthType, setTruthType] = useState('intent');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  // Truth type options with tooltip content
  const truthTypes = targetScope === 'project' 
    ? [
        { 
          value: 'intent', 
          label: '📋 Customer Requirements', 
          desc: 'SOWs, meeting notes, what they want',
          tooltip: {
            title: 'Customer Requirements',
            detail: 'Documents that describe what the customer wants to achieve. Used by AI to understand project goals.',
            action: 'Upload SOWs, requirements docs, meeting notes'
          }
        },
        { 
          value: 'configuration', 
          label: '⚙️ Customer Setup', 
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
          label: '📚 Vendor Docs & How-To', 
          desc: 'Product docs, configuration guides',
          tooltip: {
            title: 'Vendor Documentation',
            detail: 'Product documentation and configuration guides from the software vendor. Explains HOW to configure the system.',
            action: 'Upload UKG guides, ADP manuals, Workday docs'
          }
        },
        { 
          value: 'regulatory', 
          label: '⚖️ Laws & Government Rules', 
          desc: 'IRS, state, federal requirements',
          tooltip: {
            title: 'Regulatory Requirements',
            detail: 'Official government requirements - IRS publications, state tax rules, federal mandates. The LAW.',
            action: 'Upload IRS Pub 15, Secure 2.0, FLSA rules'
          }
        },
        { 
          value: 'compliance', 
          label: '🔒 Audit & Controls', 
          desc: 'SOC 2, audit requirements',
          tooltip: {
            title: 'Compliance & Audit',
            detail: 'Audit requirements and internal controls. What must be PROVEN for compliance.',
            action: 'Upload SOC 2 checklists, audit guides'
          }
        },
      ];

  useEffect(() => {
    setTruthType(targetScope === 'project' ? 'intent' : 'reference');
  }, [targetScope]);

  const handleFiles = (files) => {
    const projectId = targetScope === 'project' ? project?.id : 'Global/Universal';
    const projectName = targetScope === 'project' ? project?.name : 'Reference Library';
    
    if (targetScope === 'project' && !project?.id) {
      alert('Please select a project first');
      return;
    }
    
    Array.from(files).forEach(file => {
      // For regulatory/compliance docs, trigger rule extraction
      const isRuleSource = truthType === 'regulatory' || truthType === 'compliance';
      addUpload(file, projectId, projectName, { 
        truth_type: truthType,
        standards_mode: isRuleSource,
        domain: isRuleSource ? 'regulatory' : undefined
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
      {/* Scope Toggle */}
      <div style={{ display: 'flex', background: c.background, borderTopLeftRadius: 12, borderTopRightRadius: 12, overflow: 'hidden' }}>
        {[
          { value: 'project', label: '📁 Project Files', tooltip: 'Customer-specific documents for this project' },
          { value: 'global', label: '📚 Reference Library', tooltip: 'Global docs shared across all projects' }
        ].map(scope => (
          <Tooltip 
            key={scope.value}
            title={scope.label} 
            detail={scope.tooltip}
            action={scope.value === 'project' ? 'Requirements & Config' : 'Vendor, Legal, Audit docs'}
          >
            <button
              onClick={() => setTargetScope(scope.value)}
              style={{
                flex: 1, padding: '0.875rem', border: 'none',
                background: targetScope === scope.value ? c.cardBg : 'transparent',
                borderBottom: `3px solid ${targetScope === scope.value ? c.primary : 'transparent'}`,
                color: targetScope === scope.value ? c.primary : c.textMuted,
                fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer', transition: 'all 0.2s'
              }}
            >
              {scope.label}
            </button>
          </Tooltip>
        ))}
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
            {truthTypes.map(tt => (
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
                    border: truthType === tt.value 
                      ? `2px solid ${c.primary}` 
                      : `1px solid ${c.border}`,
                    background: truthType === tt.value ? `${c.primary}15` : 'transparent',
                    cursor: 'pointer', transition: 'all 0.15s', width: '100%'
                  }}
                >
                  <div style={{
                    width: 18, height: 18, borderRadius: '50%',
                    border: `2px solid ${truthType === tt.value ? c.primary : c.border}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0, marginTop: 2
                  }}>
                    {truthType === tt.value && (
                      <div style={{ width: 8, height: 8, borderRadius: '50%', background: c.primary }} />
                    )}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem', color: c.text }}>{tt.label}</div>
                    <div style={{ fontSize: '0.75rem', color: c.textMuted, marginTop: '0.15rem' }}>{tt.desc}</div>
                  </div>
                </button>
              </Tooltip>
            ))}
          </div>
        </div>

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
          <UploadIcon size={28} style={{ color: c.primary, marginBottom: '0.5rem' }} />
          <p style={{ fontWeight: 600, color: c.text, margin: '0 0 0.25rem', fontSize: '0.9rem' }}>
            Drop files or click to browse
          </p>
          <p style={{ fontSize: '0.75rem', color: c.textMuted, margin: 0 }}>PDF, Excel, Word, CSV</p>
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
            {activeUploads.map(upload => (
              <div key={upload.id} style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem',
                padding: '0.75rem', background: `${c.electricBlue}10`,
                border: `1px solid ${c.electricBlue}30`, borderRadius: 8, marginBottom: '0.5rem'
              }}>
                <Loader2 size={16} style={{ color: c.electricBlue, animation: 'spin 1s linear infinite', flexShrink: 0 }} />
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
            ))}
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

  useEffect(() => { loadData(); }, [project?.id, targetScope]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [structRes, docsRes, refRes] = await Promise.all([
        api.get('/status/structured').catch(() => ({ data: { files: [], total_rows: 0 } })),
        api.get('/status/documents').catch(() => ({ data: { documents: [] } })),
        api.get('/status/references').catch(() => ({ data: { files: [], rules: [] } })),
      ]);
      setStructuredData(structRes.data);
      setDocuments(docsRes.data);
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
      return f.is_global || f.project === 'Global/Universal' || f.project === 'Reference Library';
    }
    return !project || f.project === project.id || f.project === project.name;
  });
  
  const docs = (documents?.documents || []).filter(d => {
    if (isGlobalScope) {
      return d.is_global || d.project === 'Global/Universal' || d.project === 'Reference Library';
    }
    return !project || d.project === project.id || d.project === project.name;
  });
  
  // Reference library files (always global)
  const refFiles = referenceFiles?.files || [];
  const extractedRules = Array.isArray(referenceFiles?.rules) ? referenceFiles.rules : [];

  const recentlyCompleted = uploads.filter(u => u.status === 'completed').slice(0, 5);
  const totalTables = structuredFiles.reduce((sum, f) => sum + (f.sheets?.length || 1), 0);
  const totalRows = structuredData?.total_rows || 0;

  const getTruthIcon = (tt) => ({ intent: '📋', configuration: '⚙️', reference: '📚', regulatory: '⚖️', compliance: '🔒' }[tt] || '📄');
  const getTruthLabel = (tt) => ({ intent: 'Requirements', configuration: 'Setup', reference: 'Vendor', regulatory: 'Legal', compliance: 'Audit' }[tt] || '');
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
                <span style={{ fontSize: '1rem' }}>⚖️</span>
                <span style={{ fontSize: '0.9rem', color: c.text }}><strong>{extractedRules.length}</strong> rules</span>
              </div>
            </Tooltip>
            <Tooltip title="Documents" detail="Global docs chunked for AI retrieval." action="Referenced across all projects">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'help' }}>
                <Database size={18} style={{ color: c.electricBlue }} />
                <span style={{ fontSize: '0.9rem', color: c.text }}><strong>{docs.length}</strong> chunks</span>
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
          {recentlyCompleted.map(upload => (
            <div key={upload.id} style={{
              display: 'flex', alignItems: 'center', gap: '0.75rem',
              padding: '0.65rem 1rem', borderBottom: `1px solid ${c.accent}15`
            }}>
              <CheckCircle size={16} style={{ color: c.accent }} />
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
              <span style={{ fontSize: '0.75rem', color: c.accent }}>✓</span>
            </div>
          ))}
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
              <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
                <Database size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                <p style={{ margin: 0 }}>No structured data yet</p>
              </div>
            ) : (
              structuredFiles.map((file, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', borderBottom: `1px solid ${c.border}` }}>
                  <span style={{ fontSize: '1.1rem' }}>{getTruthIcon(file.truth_type)}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 500, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.filename}</div>
                    <div style={{ fontSize: '0.75rem', color: c.textMuted, display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <span>{file.sheets?.length || file.table_count || 1} table(s)</span>
                      <span>•</span>
                      <span>{(file.row_count || file.total_rows || 0).toLocaleString()} rows</span>
                      {file.relationships_count > 0 && (
                        <>
                          <span>•</span>
                          <span>{file.relationships_count} relationships</span>
                        </>
                      )}
                      {file.truth_type && (
                        <>
                          <span>•</span>
                          <span>{getTruthLabel(file.truth_type)}</span>
                        </>
                      )}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: c.textMuted, marginTop: '0.25rem', display: 'flex', gap: '0.75rem' }}>
                      {file.created_at && (
                        <span title={new Date(file.created_at).toLocaleString()}>
                          📅 {new Date(file.created_at).toLocaleDateString()}
                        </span>
                      )}
                      {file.uploaded_by_email && (
                        <span title={file.uploaded_by_email}>
                          👤 {file.uploaded_by_email.split('@')[0]}
                        </span>
                      )}
                      {file.processing_time_ms && (
                        <span>⚡ {(file.processing_time_ms / 1000).toFixed(1)}s</span>
                      )}
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
              <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
                <FileText size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                <p style={{ margin: 0 }}>No documents yet</p>
              </div>
            ) : (
              docs.map((doc, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', borderBottom: `1px solid ${c.border}` }}>
                  <span style={{ fontSize: '1.1rem' }}>{getTruthIcon(doc.truth_type)}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 500, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.filename}</div>
                    <div style={{ fontSize: '0.75rem', color: c.textMuted, display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <span>{doc.chunk_count || doc.chunks || 0} chunks</span>
                      {doc.page_count > 0 && (
                        <>
                          <span>•</span>
                          <span>{doc.page_count} pages</span>
                        </>
                      )}
                      {doc.truth_type && (
                        <>
                          <span>•</span>
                          <span>{getTruthLabel(doc.truth_type)}</span>
                        </>
                      )}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: c.textMuted, marginTop: '0.25rem', display: 'flex', gap: '0.75rem' }}>
                      {doc.created_at && (
                        <span title={new Date(doc.created_at).toLocaleString()}>
                          📅 {new Date(doc.created_at).toLocaleDateString()}
                        </span>
                      )}
                      {doc.uploaded_by_email && (
                        <span title={doc.uploaded_by_email}>
                          👤 {doc.uploaded_by_email.split('@')[0]}
                        </span>
                      )}
                      {doc.content_domain?.length > 0 && (
                        <span>🏷️ {doc.content_domain.slice(0, 2).join(', ')}</span>
                      )}
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
            <span style={{ fontSize: '1.1rem' }}>⚖️</span>
            <span style={{ fontWeight: 600, color: c.text, flex: 1 }}>Reference Library Files</span>
            <span style={{ background: `${c.royalPurple}15`, color: c.royalPurple, padding: '0.2rem 0.6rem', borderRadius: 10, fontSize: '0.75rem', fontWeight: 600 }}>
              {refFiles.length} files • {extractedRules.length} rules
            </span>
          </button>
          
          {expandedSections.reference && (
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {refFiles.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: c.textMuted }}>
                  <span style={{ fontSize: '2rem', opacity: 0.3, display: 'block', marginBottom: '0.5rem' }}>⚖️</span>
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
                      <span style={{ fontSize: '1.1rem' }}>{getTruthIcon(file.truth_type)}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 500, color: c.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {file.filename}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: c.textMuted, display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.15rem' }}>
                          <span>{getTruthLabel(file.truth_type)}</span>
                          {(file.table_count > 0 || file.row_count > 0) && (
                            <>
                              <span>•</span>
                              <span>{file.table_count || 1} table(s)</span>
                              <span>•</span>
                              <span>{(file.row_count || 0).toLocaleString()} rows</span>
                            </>
                          )}
                          {file.chunk_count > 0 && (
                            <>
                              <span>•</span>
                              <span>{file.chunk_count} chunks</span>
                            </>
                          )}
                          {fileRules.length > 0 && (
                            <>
                              <span>•</span>
                              <span style={{ color: c.royalPurple, fontWeight: 500 }}>
                                {fileRules.length} rules
                              </span>
                            </>
                          )}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: c.textMuted, marginTop: '0.25rem', display: 'flex', gap: '0.75rem' }}>
                          {file.created_at && (
                            <span title={new Date(file.created_at).toLocaleString()}>
                              📅 {new Date(file.created_at).toLocaleDateString()}
                            </span>
                          )}
                          {file.uploaded_by_email && (
                            <span title={file.uploaded_by_email}>
                              👤 {file.uploaded_by_email.split('@')[0]}
                            </span>
                          )}
                          {file.content_domain?.length > 0 && (
                            <span>🏷️ {file.content_domain.join(', ')}</span>
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
