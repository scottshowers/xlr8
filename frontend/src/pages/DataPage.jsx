/**
 * DataPage.jsx - Data Hub
 * 
 * REBUILT: December 23, 2025
 * - 3 clean tabs: Upload, Files, Health
 * - Metadata staging before upload with review
 * - Expandable uploads showing tables → fields
 * - Metrics everywhere (date, time, speed, who, duration)
 * - Mission Control styling
 */

import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { useUpload } from '../context/UploadContext';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { getCustomerColorPalette } from '../utils/customerColors';
import api from '../services/api';
import {
  Upload as UploadIcon, Database, Activity, CheckCircle, XCircle, Clock,
  Loader2, Trash2, FileText, Table2, ChevronDown, ChevronRight, User,
  CheckSquare, Square, AlertTriangle, Zap, Sparkles, X, RefreshCw
} from 'lucide-react';
import DataHealthComponent from './DataHealthPage';

// Brand colors - Mission Control palette
const COLORS = {
  primary: '#83b16d',      // Grass green
  accent: '#285390',       // Turkish sea
  electricBlue: '#2766b1',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  silver: '#a2a1a0',
  warning: '#d97706',
  scarletSage: '#993c44',
};

// Theme-aware colors
const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f0f2f5',
  card: dark ? '#242b3d' : '#ffffff',
  cardBorder: dark ? '#2d3548' : '#e2e8f0',
  text: dark ? '#e8eaed' : '#1a2332',
  textMuted: dark ? '#8b95a5' : '#64748b',
  textLight: dark ? '#5f6a7d' : '#9ca3af',
  primary: COLORS.primary,
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.1)',
  accent: COLORS.accent,
  accentLight: dark ? 'rgba(40, 83, 144, 0.15)' : 'rgba(40, 83, 144, 0.1)',
  warning: COLORS.warning,
  warningLight: dark ? 'rgba(217, 119, 6, 0.15)' : 'rgba(217, 119, 6, 0.1)',
  red: COLORS.scarletSage,
  redLight: dark ? 'rgba(153, 60, 68, 0.15)' : 'rgba(153, 60, 68, 0.1)',
  divider: dark ? '#2d3548' : '#e2e8f0',
  inputBg: dark ? '#1a1f2e' : '#f8fafc',
  tabBg: dark ? '#1e2433' : '#f6f5fa',
  white: dark ? '#1a1f2e' : '#ffffff',
});

const TABS = [
  { id: 'upload', label: 'Upload', icon: UploadIcon },
  { id: 'files', label: 'Files', icon: Database },
  { id: 'health', label: 'Health', icon: Activity },
];

const FUNCTIONAL_AREAS = ['Payroll', 'Benefits', 'HR Core', 'Time & Attendance', 'Recruiting', 'Compliance', 'Other'];
const DOC_TYPES = [
  { value: 'structured', label: 'Structured Data (Reality)' },
  { value: 'intent', label: 'Customer Doc (Intent)' },
  { value: 'reference', label: 'Reference Doc (Standards)' },
];

export default function DataPage() {
  const { activeProject, projectName, customerName } = useProject();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  const [activeTab, setActiveTab] = useState('upload');
  const { uploads, hasActive } = useUpload();
  
  const customerColors = activeProject ? getCustomerColorPalette(customerName || projectName) : null;
  const stagedCount = 0; // Will come from staging logic

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ 
          margin: 0, fontSize: '28px', fontWeight: 700, color: colors.text, 
          display: 'flex', alignItems: 'center', gap: '12px',
          fontFamily: "'Sora', sans-serif"
        }}>
          <div style={{ 
            width: '48px', height: '48px', borderRadius: '12px', 
            backgroundColor: colors.primary, 
            display: 'flex', alignItems: 'center', justifyContent: 'center' 
          }}>
            <Database size={28} color="#ffffff" />
          </div>
          Data
        </h1>
        <p style={{ margin: '8px 0 0 60px', fontSize: '14px', color: colors.textMuted }}>
          Upload, manage, and monitor your project data
          {projectName && (
            <span style={{ color: colors.primary, fontWeight: 600 }}> • {projectName}</span>
          )}
        </p>
      </div>

      {/* Main Card */}
      <div style={{ 
        backgroundColor: colors.card, 
        borderRadius: '16px', 
        border: `1px solid ${colors.cardBorder}`, 
        overflow: 'hidden', 
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)' 
      }}>
        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: `1px solid ${colors.divider}`, backgroundColor: colors.tabBg }}>
          {TABS.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const showBadge = tab.id === 'upload' && (hasActive || stagedCount > 0);
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '8px', padding: '16px 24px',
                  border: 'none', background: isActive ? colors.card : 'transparent',
                  color: isActive ? colors.primary : colors.textMuted, 
                  fontWeight: 600, fontSize: '14px', cursor: 'pointer', 
                  borderBottom: isActive ? `2px solid ${colors.primary}` : '2px solid transparent',
                  marginBottom: '-1px', transition: 'all 0.15s ease',
                }}
              >
                <Icon size={18} />
                {tab.label}
                {showBadge && (
                  <span style={{ 
                    minWidth: 18, height: 18, borderRadius: '50%', 
                    backgroundColor: hasActive ? colors.warning : colors.primary,
                    color: 'white', fontSize: '11px', fontWeight: 700,
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                  }}>
                    {hasActive ? '•' : stagedCount}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div style={{ padding: '24px' }}>
          {activeTab === 'upload' && <UploadTab colors={colors} />}
          {activeTab === 'files' && <FilesTab colors={colors} />}
          {activeTab === 'health' && <DataHealthComponent embedded />}
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }`}</style>
    </div>
  );
}

// ============ UPLOAD TAB ============
function UploadTab({ colors }) {
  const { activeProject, projectName } = useProject();
  const { user } = useAuth();
  const { uploads, addUpload, clearCompleted } = useUpload();
  const fileInputRef = useRef(null);
  
  const [dragOver, setDragOver] = useState(false);
  const [uploadTarget, setUploadTarget] = useState('current');
  const [stagedFiles, setStagedFiles] = useState([]);
  const [expandedUploads, setExpandedUploads] = useState(new Set());
  const [expandedTables, setExpandedTables] = useState(new Set());
  const [completedUploads, setCompletedUploads] = useState([]);
  const [tableProfiles, setTableProfiles] = useState({});
  const [loadingProfiles, setLoadingProfiles] = useState(new Set());

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
      
      // Enrich jobs with table data from structured endpoint
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

  const detectFileType = (file) => {
    const ext = file.name.split('.').pop().toLowerCase();
    if (['xlsx', 'xls', 'csv'].includes(ext)) return 'structured';
    if (['pdf', 'docx', 'doc'].includes(ext)) {
      // Heuristic: reference docs often have these keywords
      const name = file.name.toLowerCase();
      if (name.includes('checklist') || name.includes('guide') || name.includes('standard') || name.includes('policy')) {
        return 'reference';
      }
      return 'intent';
    }
    return 'intent';
  };

  const detectFunctionalArea = (file) => {
    const name = file.name.toLowerCase();
    if (name.includes('payroll') || name.includes('pay_') || name.includes('earning') || name.includes('deduction')) return 'Payroll';
    if (name.includes('benefit') || name.includes('health') || name.includes('401k') || name.includes('insurance')) return 'Benefits';
    if (name.includes('employee') || name.includes('roster') || name.includes('census') || name.includes('master')) return 'HR Core';
    if (name.includes('time') || name.includes('attendance') || name.includes('schedule')) return 'Time & Attendance';
    if (name.includes('compliance') || name.includes('audit') || name.includes('checklist')) return 'Compliance';
    return 'Other';
  };

  const getConfidence = (file) => {
    const ext = file.name.split('.').pop().toLowerCase();
    if (['xlsx', 'xls', 'csv'].includes(ext)) return 'high';
    const name = file.name.toLowerCase();
    if (name.includes('checklist') || name.includes('payroll') || name.includes('benefit')) return 'high';
    if (name.includes('report') || name.includes('summary')) return 'medium';
    return 'low';
  };

  const handleFilesSelected = (files) => {
    const newStaged = Array.from(files).map((file, idx) => ({
      id: `${Date.now()}-${idx}`,
      file,
      filename: file.name,
      size: formatFileSize(file.size),
      detectedType: detectFileType(file),
      detectedArea: detectFunctionalArea(file),
      confidence: getConfidence(file),
    }));
    setStagedFiles(prev => [...prev, ...newStaged]);
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
  };

  const updateStagedFile = (id, updates) => {
    setStagedFiles(prev => prev.map(f => f.id === id ? { ...f, ...updates } : f));
  };

  const uploadAll = () => {
    const target = uploadTarget === 'reference' 
      ? { id: 'reference_library', name: 'Reference Library' }
      : { id: activeProject?.id, name: projectName };
    
    if (!target.id && uploadTarget !== 'reference') {
      alert('Please select a project first');
      return;
    }

    stagedFiles.forEach(staged => {
      // Add metadata to upload options
      const options = {
        functional_area: staged.detectedArea,
        doc_type: staged.detectedType,
      };
      if (staged.detectedType === 'reference') {
        options.standards_mode = true;
      }
      addUpload(staged.file, target.id, target.name, options);
    });

    setStagedFiles([]);
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
      date: COLORS.electricBlue,
      category: COLORS.silver,
      code: colors.warning,
      quantity: '#8b5cf6',
      status: COLORS.skyBlue,
      text: colors.textMuted,
      number: '#059669',
    };
    return map[semantic] || colors.textMuted;
  };

  const getConfidenceBadge = (confidence) => {
    if (confidence === 'high') return { bg: colors.primaryLight, color: colors.primary, label: 'Auto-detected', icon: <CheckCircle size={12} /> };
    if (confidence === 'medium') return { bg: colors.warningLight, color: colors.warning, label: 'Review suggested', icon: <AlertTriangle size={12} /> };
    return { bg: colors.redLight, color: colors.red, label: 'Needs review', icon: <AlertTriangle size={12} /> };
  };

  // Active uploads from context
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
              border: `1px solid ${uploadTarget === 'current' ? colors.primary : colors.divider}`,
              backgroundColor: uploadTarget === 'current' ? colors.primaryLight : colors.card,
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
              border: `1px solid ${uploadTarget === 'reference' ? colors.accent : colors.divider}`,
              backgroundColor: uploadTarget === 'reference' ? colors.accentLight : colors.card,
              color: uploadTarget === 'reference' ? colors.accent : colors.textMuted,
              fontWeight: 600, fontSize: '13px', cursor: 'pointer', 
              display: 'flex', alignItems: 'center', gap: '6px'
            }}
          >
            <FileText size={16} /> Reference Library
          </button>
        </div>
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
          border: `2px dashed ${dragOver ? colors.primary : colors.divider}`,
          borderRadius: '12px', padding: '40px', textAlign: 'center', cursor: 'pointer',
          backgroundColor: dragOver ? colors.primaryLight : colors.white,
          transition: 'all 0.2s ease', marginBottom: '24px',
        }}
      >
        <div style={{ 
          width: 56, height: 56, borderRadius: '14px', 
          backgroundColor: colors.primaryLight, 
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

      {/* Staged Files (Before Upload) */}
      {stagedFiles.length > 0 && (
        <div style={{ 
          backgroundColor: colors.warningLight, 
          border: `1px solid ${colors.warning}40`, 
          borderRadius: '12px', marginBottom: '24px', overflow: 'hidden' 
        }}>
          <div style={{ 
            padding: '14px 20px', 
            borderBottom: `1px solid ${colors.warning}30`, 
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            backgroundColor: `${colors.warning}08`
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertTriangle size={18} color={colors.warning} />
              <span style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>
                Review Before Upload
              </span>
              <span style={{ fontSize: '12px', color: colors.textMuted }}>
                {stagedFiles.length} file{stagedFiles.length > 1 ? 's' : ''} staged
              </span>
            </div>
            <button 
              onClick={uploadAll}
              style={{ 
                display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', 
                backgroundColor: colors.primary, color: 'white', border: 'none', 
                borderRadius: '8px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' 
              }}
            >
              <UploadIcon size={14} /> Upload All
            </button>
          </div>
          
          {stagedFiles.map((file, idx) => {
            const conf = getConfidenceBadge(file.confidence);
            return (
              <div key={file.id} style={{ 
                padding: '16px 20px', 
                borderBottom: idx < stagedFiles.length - 1 ? `1px solid ${colors.warning}20` : 'none',
                backgroundColor: colors.card
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                  <FileText size={20} color={colors.textMuted} style={{ marginTop: 2 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                      <span style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>{file.filename}</span>
                      <span style={{ fontSize: '12px', color: colors.textMuted }}>{file.size}</span>
                      <span style={{ 
                        display: 'flex', alignItems: 'center', gap: '4px',
                        padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                        backgroundColor: conf.bg, color: conf.color
                      }}>
                        {conf.icon} {conf.label}
                      </span>
                    </div>
                    
                    <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '12px', color: colors.textMuted }}>Type:</span>
                        <select 
                          value={file.detectedType}
                          onChange={(e) => updateStagedFile(file.id, { detectedType: e.target.value })}
                          style={{ 
                            padding: '4px 8px', borderRadius: '4px', border: `1px solid ${colors.divider}`,
                            fontSize: '12px', backgroundColor: colors.white, cursor: 'pointer', color: colors.text
                          }}
                        >
                          {DOC_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                        </select>
                      </div>
                      
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '12px', color: colors.textMuted }}>Area:</span>
                        <select 
                          value={file.detectedArea}
                          onChange={(e) => updateStagedFile(file.id, { detectedArea: e.target.value })}
                          style={{ 
                            padding: '4px 8px', borderRadius: '4px', border: `1px solid ${colors.divider}`,
                            fontSize: '12px', backgroundColor: colors.white, cursor: 'pointer', color: colors.text
                          }}
                        >
                          {FUNCTIONAL_AREAS.map(a => <option key={a} value={a}>{a}</option>)}
                        </select>
                      </div>
                    </div>
                  </div>
                  
                  <button 
                    onClick={() => removeStaged(file.id)} 
                    style={{ background: 'none', border: 'none', color: colors.textMuted, cursor: 'pointer', padding: '4px' }}
                  >
                    <X size={16} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Active Uploads */}
      {activeUploads.length > 0 && (
        <div style={{ 
          backgroundColor: colors.white, 
          border: `1px solid ${colors.divider}`, 
          borderRadius: '12px', marginBottom: '24px', overflow: 'hidden' 
        }}>
          <div style={{ 
            padding: '14px 20px', 
            borderBottom: `1px solid ${colors.divider}`, 
            display: 'flex', justifyContent: 'space-between', alignItems: 'center' 
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Loader2 size={16} color={colors.warning} style={{ animation: 'spin 1s linear infinite' }} />
              <span style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>
                Active Uploads
              </span>
              <span style={{ 
                padding: '2px 8px', backgroundColor: colors.warningLight, 
                color: colors.warning, borderRadius: '10px', fontSize: '11px', fontWeight: 600 
              }}>
                {activeUploads.length} processing
              </span>
            </div>
          </div>
          
          {activeUploads.map(upload => (
            <div key={upload.id} style={{ 
              padding: '14px 20px', 
              borderBottom: `1px solid ${colors.divider}`,
              display: 'flex', alignItems: 'center', gap: '12px'
            }}>
              <Clock size={18} color={colors.warning} style={{ animation: 'pulse 2s infinite' }} />
              <span style={{ flex: 1, fontSize: '14px', fontWeight: 500, color: colors.text }}>
                {upload.filename}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: colors.textMuted }}>
                <span>{upload.status === 'processing' ? 'Processing...' : 'Uploading...'}</span>
                <div style={{ width: 80, height: 6, backgroundColor: colors.divider, borderRadius: 3 }}>
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

      {/* Completed Uploads with Expandable Tables */}
      {completedUploads.length > 0 && (
        <div style={{ 
          backgroundColor: colors.white, 
          border: `1px solid ${colors.divider}`, 
          borderRadius: '12px', overflow: 'hidden' 
        }}>
          <div style={{ 
            padding: '14px 20px', 
            borderBottom: `1px solid ${colors.divider}`, 
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
              {/* Job Row */}
              <div 
                onClick={() => job.tables?.length > 0 && toggleUpload(job.id)}
                style={{ 
                  padding: '14px 20px', 
                  borderBottom: `1px solid ${colors.divider}`,
                  cursor: job.tables?.length > 0 ? 'pointer' : 'default',
                  backgroundColor: expandedUploads.has(job.id) ? colors.inputBg : 'transparent',
                  transition: 'background 0.15s'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {job.tables?.length > 0 ? (
                    expandedUploads.has(job.id) ? 
                      <ChevronDown size={18} color={colors.textMuted} /> : 
                      <ChevronRight size={18} color={colors.textMuted} />
                  ) : (
                    <div style={{ width: 18 }} />
                  )}
                  <CheckCircle size={18} color={colors.primary} />
                  <span style={{ flex: 1, fontSize: '14px', fontWeight: 500, color: colors.text }}>
                    {job.filename}
                  </span>
                  
                  {/* Metrics */}
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
                        padding: '2px 8px', backgroundColor: colors.primaryLight, 
                        color: colors.primary, borderRadius: '4px', fontWeight: 600, fontSize: '11px'
                      }}>
                        {job.tables.length} table{job.tables.length > 1 ? 's' : ''} • {job.totalRows.toLocaleString()} rows
                      </span>
                    )}
                    {job.result_data?.chunks_created > 0 && (
                      <span style={{ 
                        padding: '2px 8px', backgroundColor: colors.accentLight, 
                        color: colors.accent, borderRadius: '4px', fontWeight: 600, fontSize: '11px'
                      }}>
                        {job.result_data.chunks_created} chunks
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Expanded Tables & Columns */}
              {expandedUploads.has(job.id) && job.tables?.length > 0 && (
                <div style={{ backgroundColor: colors.inputBg, borderBottom: `1px solid ${colors.divider}` }}>
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
                            backgroundColor: expandedTables.has(table.table_name) ? colors.primaryLight : 'transparent'
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
                                  padding: '4px 10px', backgroundColor: colors.card, 
                                  border: `1px solid ${colors.divider}`, borderRadius: '6px',
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
                                    <span style={{ 
                                      fontSize: '9px', 
                                      color: fillRate < 50 ? colors.warning : colors.textMuted 
                                    }}>
                                      {fillRate}%
                                    </span>
                                  )}
                                </div>
                              );
                            })}
                            {((profile?.columns || table.columns || []).length > 20) && (
                              <span style={{ fontSize: '11px', color: colors.textMuted, padding: '4px' }}>
                                +{(profile?.columns || table.columns).length - 20} more
                              </span>
                            )}
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
        backgroundColor: colors.accentLight, 
        border: `1px solid ${colors.accent}40`, 
        borderRadius: '10px', 
        display: 'flex', alignItems: 'center', gap: '12px' 
      }}>
        <Sparkles size={20} color={colors.accent} />
        <div style={{ flex: 1 }}>
          <span style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>
            Need to extract payroll registers?
          </span>
          <span style={{ fontSize: '13px', color: colors.textMuted, marginLeft: '8px' }}>
            Deep extraction for complex PDFs
          </span>
        </div>
        <Link 
          to="/vacuum"
          style={{ 
            display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', 
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

// ============ FILES TAB ============
function FilesTab({ colors }) {
  const { projects, activeProject } = useProject();
  const { darkMode } = useTheme();
  const [structuredData, setStructuredData] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [selectedStructured, setSelectedStructured] = useState(new Set());
  const [selectedDocs, setSelectedDocs] = useState(new Set());
  const [fileFilter, setFileFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Deep Clean state
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
  const totalChunks = docs.reduce((sum, d) => sum + (d.chunk_count || d.chunks || 0), 0);

  // Combined file list for unified view
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
        backgroundColor: colors.white, border: `1px solid ${colors.divider}`, borderRadius: '10px' 
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Table2 size={18} color={colors.primary} />
          <span style={{ fontSize: '20px', fontWeight: 700, color: colors.text }}>{totalTables}</span>
          <span style={{ fontSize: '13px', color: colors.textMuted }}>Tables</span>
        </div>
        <div style={{ width: 1, backgroundColor: colors.divider }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileText size={18} color={colors.accent} />
          <span style={{ fontSize: '20px', fontWeight: 700, color: colors.text }}>{totalDocs}</span>
          <span style={{ fontSize: '13px', color: colors.textMuted }}>Documents</span>
        </div>
        <div style={{ width: 1, backgroundColor: colors.divider }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Database size={18} color={COLORS.silver} />
          <span style={{ fontSize: '20px', fontWeight: 700, color: colors.text }}>
            {totalRows > 1000000 ? (totalRows / 1000000).toFixed(1) + 'M' : totalRows > 1000 ? (totalRows / 1000).toFixed(0) + 'K' : totalRows}
          </span>
          <span style={{ fontSize: '13px', color: colors.textMuted }}>Rows</span>
        </div>
        <div style={{ flex: 1 }} />
        <button
          onClick={() => setShowDeepCleanModal(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px',
            background: colors.warningLight, border: `1px solid ${colors.warning}40`,
            borderRadius: 8, color: colors.warning, fontSize: '13px', fontWeight: 600, cursor: 'pointer',
          }}
        >
          <Zap size={14} /> Deep Clean
        </button>
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
                border: fileFilter === filter ? 'none' : `1px solid ${colors.divider}`,
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
              padding: '8px 12px', border: `1px solid ${colors.divider}`, 
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
                backgroundColor: colors.red, color: 'white', border: 'none', 
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
        backgroundColor: colors.white, 
        border: `1px solid ${colors.divider}`, 
        borderRadius: '10px', overflow: 'hidden' 
      }}>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: '40px 1fr 100px 140px 100px 80px', 
          padding: '10px 16px', 
          borderBottom: `1px solid ${colors.divider}`, 
          backgroundColor: colors.tabBg, 
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
            {allFiles.map((file, i) => {
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
                    borderBottom: `1px solid ${colors.divider}`, 
                    alignItems: 'center', 
                    gap: '8px',
                    backgroundColor: isSelected ? colors.primaryLight : 'transparent'
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
                      backgroundColor: file.type === 'structured' ? colors.primaryLight : colors.accentLight, 
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
                    backgroundColor: getProjectName(file.project) === 'GLOBAL' ? colors.accentLight : colors.primaryLight, 
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
            background: colors.card, borderRadius: 12, padding: '24px',
            maxWidth: 500, width: '90%', maxHeight: '80vh', overflow: 'auto',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: colors.warningLight,
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
              background: colors.inputBg, border: `1px solid ${colors.divider}`,
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
              background: forceClean ? colors.redLight : colors.inputBg,
              border: `1px solid ${forceClean ? colors.red + '40' : colors.divider}`,
              borderRadius: 8, marginBottom: '16px', cursor: 'pointer',
            }}>
              <input
                type="checkbox"
                checked={forceClean}
                onChange={(e) => setForceClean(e.target.checked)}
                style={{ marginTop: 2 }}
              />
              <div>
                <div style={{ fontSize: '14px', fontWeight: 500, color: forceClean ? colors.red : colors.text }}>
                  Force clean (full wipe)
                </div>
                <div style={{ fontSize: '12px', color: colors.textMuted, marginTop: 2 }}>
                  Use if Registry is empty and you want to clear all backend data.
                </div>
              </div>
            </label>

            {deepCleanResult && (
              <div style={{
                background: deepCleanResult.success ? colors.primaryLight : colors.redLight,
                border: `1px solid ${deepCleanResult.success ? colors.primary : colors.red}40`,
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
                    <XCircle size={16} color={colors.red} />
                    <span style={{ fontWeight: 600, color: colors.red }}>
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
                  padding: '10px 20px', border: `1px solid ${colors.divider}`,
                  borderRadius: 8, background: colors.card, color: colors.text,
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
