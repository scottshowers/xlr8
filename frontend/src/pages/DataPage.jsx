/**
 * DataPage.jsx - Data Hub
 * 
 * Clean professional design with:
 * - Light/dark mode support
 * - Customer color accents
 * - Consistent styling with Command Center
 * 
 * UPDATED: Added Deep Clean button to Files tab
 * 
 * Tabs: Upload | Files | Data Health | Observatory | Register Extractor
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
  Upload as UploadIcon, Sparkles, Database, RefreshCw,
  CheckCircle, XCircle, Clock, Loader2, Trash2,
  FileText, Table2, ChevronDown, ChevronUp, User, Calendar,
  CheckSquare, Square, Eye, AlertTriangle, Zap
} from 'lucide-react';
import DataHealthComponent from './DataHealthPage';
import DataObservatoryPage from './DataObservatoryPage';

// Theme-aware colors
const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f5f7fa',
  card: dark ? '#242b3d' : '#ffffff',
  cardBorder: dark ? '#2d3548' : '#e8ecf1',
  text: dark ? '#e8eaed' : '#2a3441',
  textMuted: dark ? '#8b95a5' : '#6b7280',
  textLight: dark ? '#5f6a7d' : '#9ca3af',
  primary: '#5a8a4a',  // Muted forest green
  primaryLight: dark ? 'rgba(90, 138, 74, 0.15)' : 'rgba(90, 138, 74, 0.1)',
  blue: '#4a6b8a',     // Slate blue
  blueLight: dark ? 'rgba(74, 107, 138, 0.15)' : 'rgba(74, 107, 138, 0.1)',
  amber: '#8a6b4a',    // Muted rust
  amberLight: dark ? 'rgba(138, 107, 74, 0.15)' : 'rgba(138, 107, 74, 0.1)',
  red: '#8a4a4a',      // Muted burgundy
  redLight: dark ? 'rgba(138, 74, 74, 0.15)' : 'rgba(138, 74, 74, 0.1)',
  green: '#5a8a5a',    // Muted green
  greenLight: dark ? 'rgba(90, 138, 90, 0.15)' : 'rgba(90, 138, 90, 0.1)',
  divider: dark ? '#2d3548' : '#e8ecf1',
  inputBg: dark ? '#1a1f2e' : '#f8fafc',
  tabBg: dark ? '#1e2433' : '#fafbfc',
});

const TABS = [
  { id: 'upload', label: 'Upload', icon: UploadIcon },
  { id: 'files', label: 'Files', icon: Database },
  { id: 'health', label: 'Data Health', icon: Database },
  { id: 'observatory', label: 'Observatory', icon: Eye },
  { id: 'vacuum', label: 'Register Extractor', icon: Sparkles },
];

export default function DataPage() {
  const { activeProject, projectName, customerName } = useProject();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  const [activeTab, setActiveTab] = useState('upload');
  
  const customerColors = activeProject ? getCustomerColorPalette(customerName || projectName) : null;

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.5rem', fontWeight: 700, color: colors.text, margin: 0 }}>
          Data
        </h1>
        <p style={{ color: colors.textMuted, marginTop: '0.25rem', fontSize: '0.875rem' }}>
          Upload and manage project data
          {projectName && customerColors && (
            <span style={{ color: customerColors.primary, fontWeight: 500 }}> • {projectName}</span>
          )}
        </p>
      </div>

      <div style={{ background: colors.card, border: `1px solid ${colors.cardBorder}`, borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <div style={{ display: 'flex', borderBottom: `1px solid ${colors.divider}`, background: colors.tabBg }}>
          {TABS.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '1rem 1.25rem',
                  border: 'none', background: isActive ? colors.card : 'transparent',
                  color: isActive ? colors.primary : colors.textMuted, fontWeight: 600, fontSize: '0.85rem',
                  cursor: 'pointer', borderBottom: isActive ? `2px solid ${colors.primary}` : '2px solid transparent',
                  marginBottom: '-1px', transition: 'all 0.15s ease',
                }}
              >
                <Icon size={18} />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div style={{ padding: '1.5rem' }}>
          {activeTab === 'upload' && <UploadTab project={activeProject} projectName={projectName} colors={colors} />}
          {activeTab === 'files' && <FilesTab colors={colors} />}
          {activeTab === 'health' && <DataHealthComponent embedded />}
          {activeTab === 'observatory' && <DataObservatoryPage embedded />}
          {activeTab === 'vacuum' && <VacuumTab colors={colors} />}
        </div>
      </div>
    </div>
  );
}

function UploadTab({ project, projectName, colors }) {
  const { addUpload } = useUpload();
  const [dragOver, setDragOver] = useState(false);
  const [targetProject, setTargetProject] = useState('current');
  const [truthType, setTruthType] = useState('intent');
  const fileInputRef = useRef(null);

  const getEffectiveProject = () => {
    if (targetProject === 'current') return { id: project, name: projectName };
    if (targetProject === 'reference') return { id: 'Global/Universal', name: 'Reference Library' };
    return { id: project, name: projectName };
  };

  // Truth types based on upload target
  const customerTruthTypes = [
    { value: 'intent', label: '📋 Customer Intent', desc: 'SOWs, requirements, meeting notes' },
    { value: 'configuration', label: '⚙️ Configuration', desc: 'Code tables, mappings, system setup' },
  ];
  
  const globalTruthTypes = [
    { value: 'reference', label: '📚 Reference', desc: 'Product docs, how-to guides, standards' },
    { value: 'regulatory', label: '⚖️ Regulatory', desc: 'Laws, IRS rules, federal mandates' },
    { value: 'compliance', label: '🔒 Compliance', desc: 'Audit requirements, SOC 2, controls' },
  ];
  
  const availableTruthTypes = targetProject === 'reference' ? globalTruthTypes : customerTruthTypes;
  
  // Reset truth_type when switching target
  useEffect(() => {
    if (targetProject === 'reference') {
      setTruthType('reference');
    } else {
      setTruthType('intent');
    }
  }, [targetProject]);

  const handleFiles = (files) => {
    const effective = getEffectiveProject();
    if (!effective.id && targetProject !== 'reference') { alert('Please select a project first'); return; }
    Array.from(files).forEach(file => addUpload(file, effective.id, effective.name, { truth_type: truthType }));
  };

  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); };
  const handleFileSelect = (e) => { handleFiles(e.target.files); e.target.value = ''; };

  return (
    <div>
      <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        <label style={{ fontWeight: 500, color: colors.text, fontSize: '0.9rem' }}>Upload to:</label>
        <select value={targetProject} onChange={(e) => setTargetProject(e.target.value)} style={{ padding: '0.5rem 1rem', borderRadius: 8, border: `1px solid ${colors.divider}`, fontSize: '0.9rem', cursor: 'pointer', minWidth: '200px', background: colors.card, color: colors.text }}>
          <option value="current">{projectName || 'Current Project'}{project ? '' : ' (select one above)'}</option>
          <option value="reference">📚 Reference Library (Global)</option>
        </select>
      </div>
      
      {/* Truth Type Selection */}
      <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'flex-start', gap: '0.75rem', flexWrap: 'wrap' }}>
        <label style={{ fontWeight: 500, color: colors.text, fontSize: '0.9rem', paddingTop: '0.5rem' }}>Document Type:</label>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {availableTruthTypes.map(tt => (
            <button
              key={tt.value}
              onClick={() => setTruthType(tt.value)}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: 8,
                border: `2px solid ${truthType === tt.value ? colors.primary : colors.divider}`,
                background: truthType === tt.value ? colors.primaryLight : colors.card,
                color: truthType === tt.value ? colors.primary : colors.text,
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: truthType === tt.value ? 600 : 400,
                transition: 'all 0.2s ease'
              }}
              title={tt.desc}
            >
              {tt.label}
            </button>
          ))}
        </div>
      </div>
      
      {/* Description of selected truth type */}
      <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: colors.inputBg, borderRadius: 8, border: `1px solid ${colors.divider}` }}>
        <span style={{ fontSize: '0.8rem', color: colors.textMuted }}>
          {availableTruthTypes.find(t => t.value === truthType)?.desc}
        </span>
      </div>

      <input type="file" ref={fileInputRef} style={{ display: 'none' }} multiple accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md" onChange={handleFileSelect} />
      <div onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop} onClick={() => fileInputRef.current?.click()} style={{ border: `2px dashed ${dragOver ? colors.primary : colors.divider}`, borderRadius: 12, padding: '3rem', textAlign: 'center', cursor: 'pointer', background: dragOver ? colors.primaryLight : colors.inputBg, transition: 'all 0.2s ease' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div style={{ width: 56, height: 56, borderRadius: 12, background: colors.primaryLight, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
            <UploadIcon size={24} style={{ color: colors.primary }} />
          </div>
          <p style={{ fontWeight: 600, color: colors.text, margin: '0 0 0.25rem' }}>Drop files here or click to browse</p>
          <p style={{ fontSize: '0.85rem', color: colors.textMuted, margin: 0 }}>PDF, Excel, Word, CSV supported</p>
        </div>
      </div>
    </div>
  );
}

function VacuumTab({ colors }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '2rem' }}>
      <div style={{ width: 72, height: 72, borderRadius: 16, background: colors.primaryLight, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.25rem' }}>
        <Sparkles size={32} style={{ color: colors.primary }} />
      </div>
      <h2 style={{ margin: '0 0 0.5rem', color: colors.text, fontFamily: "'Sora', sans-serif" }}>Register Extractor</h2>
      <p style={{ color: colors.textMuted, maxWidth: '500px', margin: '0 auto 1.5rem', lineHeight: 1.6, textAlign: 'center' }}>Deep extraction for payroll registers and complex documents.</p>
      <Link to="/vacuum" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.875rem 1.75rem', background: colors.primary, border: 'none', borderRadius: 10, color: 'white', fontSize: '1rem', fontWeight: 600, textDecoration: 'none' }}>
        <Sparkles size={18} />Open Register Extractor
      </Link>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', maxWidth: '600px', margin: '2rem auto 0', textAlign: 'left' }}>
        {[{ icon: '📊', text: 'Smart employee detection from PDFs' }, { icon: '💰', text: 'Earnings & deductions parsing' }, { icon: '✅', text: 'Automatic balance validation' }, { icon: '📋', text: 'Multi-vendor support' }].map((f, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem', background: colors.inputBg, border: `1px solid ${colors.divider}`, borderRadius: 8 }}>
            <span style={{ fontSize: '1.25rem' }}>{f.icon}</span>
            <span style={{ fontSize: '0.9rem', color: colors.text }}>{f.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function FilesTab({ colors }) {
  const { projects, activeProject } = useProject();
  const { darkMode } = useTheme();
  const [structuredData, setStructuredData] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedStructured, setSelectedStructured] = useState(new Set());
  const [selectedDocs, setSelectedDocs] = useState(new Set());
  const [expandedFiles, setExpandedFiles] = useState(new Set());
  const [tableProfiles, setTableProfiles] = useState({});
  const [loadingProfiles, setLoadingProfiles] = useState(new Set());
  const [showReferenceLibrary, setShowReferenceLibrary] = useState(false);
  
  // Deep Clean state
  const [deepCleanLoading, setDeepCleanLoading] = useState(false);
  const [deepCleanResult, setDeepCleanResult] = useState(null);
  const [showDeepCleanModal, setShowDeepCleanModal] = useState(false);
  const [forceClean, setForceClean] = useState(false);

  const toggleFileExpand = (key) => { const s = new Set(expandedFiles); if (s.has(key)) s.delete(key); else s.add(key); setExpandedFiles(s); };
  const loadTableProfile = async (tableName) => {
    if (tableProfiles[tableName] || loadingProfiles.has(tableName)) return;
    setLoadingProfiles(prev => new Set([...prev, tableName]));
    try { const res = await api.get(`/status/table-profile/${encodeURIComponent(tableName)}`); setTableProfiles(prev => ({ ...prev, [tableName]: res.data })); }
    catch (err) { setTableProfiles(prev => ({ ...prev, [tableName]: { error: err.message } })); }
    finally { setLoadingProfiles(prev => { const n = new Set(prev); n.delete(tableName); return n; }); }
  };

  useEffect(() => { loadData(); const i = setInterval(loadData, 30000); return () => clearInterval(i); }, [activeProject?.id]);

  const loadData = async () => {
    try {
      const [structRes, docsRes, jobsRes] = await Promise.all([
        api.get('/status/structured').catch(() => ({ data: { files: [], total_rows: 0 } })),
        api.get('/status/documents').catch(() => ({ data: { documents: [] } })),
        api.get('/jobs').catch(() => ({ data: { jobs: [] } })),
      ]);
      setStructuredData(structRes.data); setDocuments(docsRes.data); setJobs(jobsRes.data.jobs || []);
    } catch (err) { console.error('Failed to load:', err); } finally { setLoading(false); }
  };

  const structuredFiles = (structuredData?.files || []).filter(f => !activeProject || f.project === activeProject.id || f.project === activeProject.name);
  
  // Filter documents based on toggle
  const allDocs = documents?.documents || [];
  const projectDocs = allDocs.filter(d => !activeProject || d.project === activeProject.id || d.project === activeProject.name);
  const globalDocs = allDocs.filter(d => d.project === 'Global/Universal' || d.project === 'GLOBAL' || d.is_global);
  const docs = showReferenceLibrary ? globalDocs : projectDocs;
  
  const recentJobs = jobs.filter(j => !activeProject || j.project_id === activeProject.id).slice(0, 20);

  // Truth type labels for display
  const getTruthTypeLabel = (tt) => {
    const labels = {
      'intent': '📋 Intent',
      'configuration': '⚙️ Config',
      'reference': '📚 Reference',
      'regulatory': '⚖️ Regulatory',
      'compliance': '🔒 Compliance'
    };
    return labels[tt] || tt || '—';
  };

  const getProjectName = (pv) => { if (!pv) return 'Unknown'; if (pv === 'GLOBAL') return 'GLOBAL'; if (pv.length === 36 && pv.includes('-')) { const f = projects.find(p => p.id === pv); return f ? f.name : pv.slice(0, 8) + '...'; } return pv; };
  const formatDate = (dateStr) => { if (!dateStr) return '—'; try { return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); } catch { return '—'; } };
  const toggleStructured = (key) => { const s = new Set(selectedStructured); if (s.has(key)) s.delete(key); else s.add(key); setSelectedStructured(s); };
  const toggleDoc = (key) => { const s = new Set(selectedDocs); if (s.has(key)) s.delete(key); else s.add(key); setSelectedDocs(s); };
  const selectAllStructured = () => { if (selectedStructured.size === structuredFiles.length) setSelectedStructured(new Set()); else setSelectedStructured(new Set(structuredFiles.map(f => `${f.project}:${f.filename}`))); };
  const selectAllDocs = () => { if (selectedDocs.size === docs.length) setSelectedDocs(new Set()); else setSelectedDocs(new Set(docs.map(d => d.filename))); };

  const deleteSelectedStructured = async () => {
    if (selectedStructured.size === 0) return;
    if (!confirm(`Delete ${selectedStructured.size} structured file(s)?`)) return;
    setDeleting(true);
    try { for (const key of selectedStructured) { const [project, filename] = key.split(':'); await api.delete(`/status/structured/${encodeURIComponent(project)}/${encodeURIComponent(filename)}`); } setSelectedStructured(new Set()); loadData(); }
    catch (err) { alert('Error: ' + (err.response?.data?.detail || err.message)); } finally { setDeleting(false); }
  };

  const deleteSelectedDocs = async () => {
    if (selectedDocs.size === 0) return;
    if (!confirm(`Delete ${selectedDocs.size} document(s)?`)) return;
    setDeleting(true);
    try { for (const filename of selectedDocs) { await api.delete(`/status/documents/${encodeURIComponent(filename)}`); } setSelectedDocs(new Set()); loadData(); }
    catch (err) { alert('Error: ' + (err.response?.data?.detail || err.message)); } finally { setDeleting(false); }
  };

  const clearAllJobs = async () => { if (!confirm('Clear all processing history?')) return; setDeleting(true); try { await api.post('/jobs/clear-all'); loadData(); } catch (err) { alert('Error: ' + (err.response?.data?.detail || err.message)); } finally { setDeleting(false); } };
  const getStatusIcon = (status) => { if (status === 'completed') return <CheckCircle size={14} style={{ color: colors.green }} />; if (status === 'failed') return <XCircle size={14} style={{ color: colors.red }} />; if (status === 'processing') return <Loader2 size={14} style={{ color: colors.blue, animation: 'spin 1s linear infinite' }} />; return <Clock size={14} style={{ color: colors.amber }} />; };

  // Deep Clean functions
  const handleDeepClean = async () => {
    setDeepCleanLoading(true);
    setDeepCleanResult(null);
    try {
      const url = forceClean ? '/deep-clean?confirm=true&force=true' : '/deep-clean?confirm=true';
      const res = await api.post(url);
      setDeepCleanResult(res.data);
      // Reload data after cleanup
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

  const sectionStyle = { border: `1px solid ${colors.divider}`, borderRadius: 10, marginBottom: '1rem', overflow: 'hidden', background: colors.card };
  const headerStyle = { display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.875rem 1rem', background: colors.inputBg, borderBottom: `1px solid ${colors.divider}` };
  const colHeaderStyle = { display: 'grid', gridTemplateColumns: '30px 1fr 100px 100px 80px', gap: '0.75rem', padding: '0.5rem 1rem', background: colors.inputBg, fontSize: '0.7rem', fontWeight: 600, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: `1px solid ${colors.divider}` };
  const rowStyle = { display: 'grid', gridTemplateColumns: '30px 1fr 100px 100px 80px', gap: '0.75rem', padding: '0.6rem 1rem', alignItems: 'center', borderBottom: `1px solid ${colors.divider}` };

  if (loading) return <div style={{ textAlign: 'center', padding: '3rem', color: colors.textMuted }}><RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} /><p>Loading...</p><style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style></div>;

  return (
    <div>
      {/* DEEP CLEAN BUTTON */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'flex-end', 
        marginBottom: '1rem',
        gap: '0.5rem'
      }}>
        <button
          onClick={() => setShowDeepCleanModal(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            background: colors.amberLight,
            border: `1px solid ${colors.amber}40`,
            borderRadius: 8,
            color: colors.amber,
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <Zap size={16} />
          Deep Clean
        </button>
      </div>

      {/* DEEP CLEAN MODAL */}
      {showDeepCleanModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            background: colors.card,
            borderRadius: 12,
            padding: '1.5rem',
            maxWidth: 500,
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: colors.amberLight,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Zap size={20} style={{ color: colors.amber }} />
              </div>
              <div>
                <h3 style={{ margin: 0, color: colors.text }}>Deep Clean</h3>
                <p style={{ margin: 0, fontSize: '0.8rem', color: colors.textMuted }}>
                  Remove orphaned data across all storage systems
                </p>
              </div>
            </div>

            <div style={{
              background: colors.inputBg,
              border: `1px solid ${colors.divider}`,
              borderRadius: 8,
              padding: '1rem',
              marginBottom: '1rem',
            }}>
              <p style={{ margin: '0 0 0.75rem', fontSize: '0.85rem', color: colors.text, fontWeight: 500 }}>
                This will clean orphaned entries from:
              </p>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8rem', color: colors.textMuted }}>
                <li>ChromaDB vector chunks (deleted files)</li>
                <li>DuckDB metadata tables (_schema_metadata, _pdf_tables)</li>
                <li>DuckDB support tables (file_metadata, column_profiles)</li>
                <li>Supabase document records</li>
                <li>Playbook scan cache</li>
              </ul>
            </div>

            {/* Force Clean Option */}
            <label style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.75rem',
              padding: '0.75rem 1rem',
              background: forceClean ? colors.redLight : colors.inputBg,
              border: `1px solid ${forceClean ? colors.red + '40' : colors.divider}`,
              borderRadius: 8,
              marginBottom: '1rem',
              cursor: 'pointer',
            }}>
              <input
                type="checkbox"
                checked={forceClean}
                onChange={(e) => setForceClean(e.target.checked)}
                style={{ marginTop: 2 }}
              />
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 500, color: forceClean ? colors.red : colors.text }}>
                  Force clean (full wipe)
                </div>
                <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginTop: 2 }}>
                  Use this if Registry is empty and you want to clear all backend data. 
                  Normally, an empty Registry is treated as a connection error to prevent accidental data loss.
                </div>
              </div>
            </label>

            {deepCleanResult && (
              <div style={{
                background: deepCleanResult.success ? colors.greenLight : colors.redLight,
                border: `1px solid ${deepCleanResult.success ? colors.green : colors.red}40`,
                borderRadius: 8,
                padding: '1rem',
                marginBottom: '1rem',
              }}>
                {deepCleanResult.success ? (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                      <CheckCircle size={16} style={{ color: colors.green }} />
                      <span style={{ fontWeight: 600, color: colors.green }}>
                        Cleaned {deepCleanResult.total_cleaned} orphaned items
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>
                      {deepCleanResult.details?.chromadb?.cleaned > 0 && (
                        <div>• ChromaDB: {deepCleanResult.details.chromadb.cleaned} chunks</div>
                      )}
                      {deepCleanResult.details?.duckdb_metadata?.cleaned > 0 && (
                        <div>• DuckDB metadata: {deepCleanResult.details.duckdb_metadata.cleaned} entries</div>
                      )}
                      {deepCleanResult.details?.supabase?.cleaned > 0 && (
                        <div>• Supabase: {deepCleanResult.details.supabase.cleaned} records</div>
                      )}
                      {deepCleanResult.details?.playbook_cache?.cleaned > 0 && (
                        <div>• Playbook cache: cleared</div>
                      )}
                      {deepCleanResult.total_cleaned === 0 && (
                        <div>No orphaned data found - everything is clean!</div>
                      )}
                    </div>
                  </>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <XCircle size={16} style={{ color: colors.red }} />
                    <span style={{ color: colors.red }}>
                      Error: {deepCleanResult.error}
                    </span>
                  </div>
                )}
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowDeepCleanModal(false);
                  setDeepCleanResult(null);
                  setForceClean(false);
                }}
                style={{
                  padding: '0.6rem 1.25rem',
                  background: colors.inputBg,
                  border: `1px solid ${colors.divider}`,
                  borderRadius: 8,
                  color: colors.text,
                  fontSize: '0.85rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                {deepCleanResult ? 'Close' : 'Cancel'}
              </button>
              {!deepCleanResult && (
                <button
                  onClick={handleDeepClean}
                  disabled={deepCleanLoading}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.6rem 1.25rem',
                    background: colors.amber,
                    border: 'none',
                    borderRadius: 8,
                    color: 'white',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    cursor: deepCleanLoading ? 'wait' : 'pointer',
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

      {/* STRUCTURED DATA */}
      <div style={sectionStyle}>
        <div style={headerStyle}>
          <Table2 size={20} style={{ color: colors.blue }} />
          <span style={{ fontWeight: 600, color: colors.text, flex: 1 }}>Structured Data</span>
          <span style={{ background: colors.blueLight, color: colors.blue, padding: '0.2rem 0.6rem', borderRadius: 10, fontSize: '0.75rem', fontWeight: 600 }}>{structuredFiles.length} files</span>
          {selectedStructured.size > 0 && <button onClick={deleteSelectedStructured} disabled={deleting} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.75rem', background: darkMode ? 'rgba(199, 107, 107, 0.15)' : '#fef2f2', border: `1px solid ${colors.red}40`, borderRadius: 6, color: colors.red, fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}><Trash2 size={14} />Delete ({selectedStructured.size})</button>}
        </div>
        {structuredFiles.length > 0 && <div style={colHeaderStyle}><button onClick={selectAllStructured} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>{selectedStructured.size === structuredFiles.length ? <CheckSquare size={16} style={{ color: colors.primary }} /> : <Square size={16} style={{ color: colors.textMuted }} />}</button><span>File Name</span><span>Uploaded By</span><span>Date</span><span></span></div>}
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {structuredFiles.length === 0 ? <div style={{ padding: '2rem', textAlign: 'center', color: colors.textMuted }}><Table2 size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} /><p style={{ margin: 0 }}>No structured data</p></div> : structuredFiles.map((file, i) => {
            const key = `${file.project}:${file.filename}`;
            const isSelected = selectedStructured.has(key);
            const isExpanded = expandedFiles.has(key);
            return (
              <div key={i}>
                <div style={{ ...rowStyle, background: isSelected ? colors.primaryLight : 'transparent' }}>
                  <button onClick={() => toggleStructured(key)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>{isSelected ? <CheckSquare size={16} style={{ color: colors.primary }} /> : <Square size={16} style={{ color: colors.textMuted }} />}</button>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: colors.text }}>{file.filename}</div>
                      <button onClick={() => { toggleFileExpand(key); if (!isExpanded && file.sheets?.[0]?.table_name) loadTableProfile(file.sheets[0].table_name); }} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.15rem', color: colors.textMuted }}>{isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</button>
                    </div>
                    <div style={{ fontSize: '0.7rem', color: colors.textMuted }}>{file.sheets?.length || 0} sheet(s) • {(file.total_rows || 0).toLocaleString()} rows • {getProjectName(file.project)}</div>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted, display: 'flex', alignItems: 'center', gap: '0.35rem' }}><User size={12} />{file.uploaded_by || 'System'}</div>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted, display: 'flex', alignItems: 'center', gap: '0.35rem' }}><Calendar size={12} />{formatDate(file.loaded_at)}</div>
                  <div></div>
                </div>
                {isExpanded && <div style={{ padding: '0.75rem 1rem 0.75rem 2.5rem', background: colors.inputBg, borderBottom: `1px solid ${colors.divider}` }}>{file.sheets?.map((sheet, si) => { const profile = tableProfiles[sheet.table_name]; const isLoadingProfile = loadingProfiles.has(sheet.table_name); return (<div key={si} style={{ marginBottom: si < file.sheets.length - 1 ? '0.75rem' : 0 }}><div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}><span style={{ fontSize: '0.8rem', fontWeight: 600, color: colors.text }}>{sheet.sheet_name || 'Sheet'}</span><span style={{ fontSize: '0.7rem', color: colors.textMuted }}>{sheet.columns?.length || 0} cols • {(sheet.row_count || 0).toLocaleString()} rows</span>{!profile && !isLoadingProfile && <button onClick={() => loadTableProfile(sheet.table_name)} style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem', background: colors.primaryLight, border: `1px solid ${colors.primary}40`, borderRadius: 4, color: colors.primary, cursor: 'pointer' }}>Profile</button>}{isLoadingProfile && <Loader2 size={12} style={{ animation: 'spin 1s linear infinite', color: colors.primary }} />}</div>{profile && !profile.error && <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>{profile.columns?.slice(0, 8).map((col, ci) => <span key={ci} style={{ fontSize: '0.65rem', padding: '0.2rem 0.4rem', background: col.fill_rate < 50 ? `${colors.amber}20` : colors.inputBg, border: `1px solid ${col.fill_rate < 50 ? colors.amber : colors.divider}`, borderRadius: 4, color: col.fill_rate < 50 ? colors.amber : colors.textMuted }}>{col.name}: {col.fill_rate}%</span>)}{profile.columns?.length > 8 && <span style={{ fontSize: '0.65rem', color: colors.textMuted }}>+{profile.columns.length - 8} more</span>}</div>}</div>); })}</div>}
              </div>
            );
          })}
        </div>
      </div>

      {/* DOCUMENTS */}
      <div style={sectionStyle}>
        <div style={headerStyle}>
          <FileText size={20} style={{ color: colors.green }} />
          <span style={{ fontWeight: 600, color: colors.text }}>Documents</span>
          
          {/* Toggle between Project and Reference Library */}
          <div style={{ display: 'flex', background: colors.inputBg, borderRadius: 6, padding: '2px', marginLeft: '0.5rem' }}>
            <button 
              onClick={() => setShowReferenceLibrary(false)}
              style={{ 
                padding: '0.3rem 0.75rem', 
                borderRadius: 4, 
                border: 'none',
                background: !showReferenceLibrary ? colors.primary : 'transparent',
                color: !showReferenceLibrary ? 'white' : colors.textMuted,
                fontSize: '0.75rem',
                fontWeight: 500,
                cursor: 'pointer'
              }}
            >
              📁 Project
            </button>
            <button 
              onClick={() => setShowReferenceLibrary(true)}
              style={{ 
                padding: '0.3rem 0.75rem', 
                borderRadius: 4, 
                border: 'none',
                background: showReferenceLibrary ? colors.primary : 'transparent',
                color: showReferenceLibrary ? 'white' : colors.textMuted,
                fontSize: '0.75rem',
                fontWeight: 500,
                cursor: 'pointer'
              }}
            >
              📚 Reference Library
            </button>
          </div>
          
          <span style={{ flex: 1 }}></span>
          <span style={{ background: colors.greenLight, color: colors.green, padding: '0.2rem 0.6rem', borderRadius: 10, fontSize: '0.75rem', fontWeight: 600 }}>{docs.length}</span>
          {selectedDocs.size > 0 && <button onClick={deleteSelectedDocs} disabled={deleting} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.75rem', background: darkMode ? 'rgba(199, 107, 107, 0.15)' : '#fef2f2', border: `1px solid ${colors.red}40`, borderRadius: 6, color: colors.red, fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}><Trash2 size={14} />Delete ({selectedDocs.size})</button>}
        </div>
        {docs.length > 0 && <div style={{ ...colHeaderStyle, gridTemplateColumns: '30px 1fr 80px 100px 100px' }}><button onClick={selectAllDocs} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>{selectedDocs.size === docs.length ? <CheckSquare size={16} style={{ color: colors.primary }} /> : <Square size={16} style={{ color: colors.textMuted }} />}</button><span>Document Name</span><span>Type</span><span>Uploaded By</span><span>Date</span></div>}
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {docs.length === 0 ? <div style={{ padding: '2rem', textAlign: 'center', color: colors.textMuted }}><FileText size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} /><p style={{ margin: 0 }}>{showReferenceLibrary ? 'No Reference Library documents. Upload regulatory standards, compliance docs, or reference materials.' : 'No project documents'}</p></div> : docs.map((doc, i) => { const isSelected = selectedDocs.has(doc.filename); return (<div key={i} style={{ ...rowStyle, gridTemplateColumns: '30px 1fr 80px 100px 100px', background: isSelected ? colors.primaryLight : 'transparent' }}><button onClick={() => toggleDoc(doc.filename)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>{isSelected ? <CheckSquare size={16} style={{ color: colors.primary }} /> : <Square size={16} style={{ color: colors.textMuted }} />}</button><div style={{ minWidth: 0 }}><div style={{ fontSize: '0.85rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: colors.text }}>{doc.filename}</div><div style={{ fontSize: '0.7rem', color: colors.textMuted }}>{doc.chunk_count || doc.chunks || 0} chunks</div></div><div style={{ fontSize: '0.7rem', color: colors.textMuted }}>{getTruthTypeLabel(doc.truth_type)}</div><div style={{ fontSize: '0.75rem', color: colors.textMuted, display: 'flex', alignItems: 'center', gap: '0.35rem' }}><User size={12} />{doc.uploaded_by || 'System'}</div><div style={{ fontSize: '0.75rem', color: colors.textMuted, display: 'flex', alignItems: 'center', gap: '0.35rem' }}><Calendar size={12} />{formatDate(doc.uploaded_at || doc.created_at)}</div></div>); })}
        </div>
      </div>

      {/* PROCESSING HISTORY */}
      <div style={{ ...sectionStyle, marginBottom: 0 }}>
        <button onClick={() => setShowHistory(!showHistory)} style={{ ...headerStyle, cursor: 'pointer', width: '100%', border: 'none', borderBottom: showHistory ? `1px solid ${colors.divider}` : 'none' }}>
          <Clock size={20} style={{ color: colors.blue }} />
          <span style={{ fontWeight: 600, color: colors.text, flex: 1, textAlign: 'left' }}>Processing History</span>
          <span style={{ background: colors.blueLight, color: colors.blue, padding: '0.2rem 0.6rem', borderRadius: 10, fontSize: '0.75rem', fontWeight: 600 }}>{recentJobs.length}</span>
          {showHistory && recentJobs.length > 0 && <button onClick={(e) => { e.stopPropagation(); clearAllJobs(); }} disabled={deleting} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.35rem 0.6rem', background: colors.inputBg, border: `1px solid ${colors.divider}`, borderRadius: 6, color: colors.textMuted, fontSize: '0.75rem', cursor: 'pointer' }}>Clear All</button>}
          {showHistory ? <ChevronUp size={18} style={{ color: colors.textMuted }} /> : <ChevronDown size={18} style={{ color: colors.textMuted }} />}
        </button>
        {showHistory && <div style={{ maxHeight: '250px', overflowY: 'auto' }}>{recentJobs.length === 0 ? <div style={{ padding: '1.5rem', textAlign: 'center', color: colors.textMuted, fontSize: '0.85rem' }}>No processing history</div> : recentJobs.map((job) => { const filename = job.input_data?.filename || job.result_data?.filename || job.filename || 'Processing job'; const resultMsg = job.result_data?.chunks_created ? `${job.result_data.chunks_created} chunks` : job.result_data?.tables_created ? `${job.result_data.tables_created} table(s), ${(job.result_data.total_rows || 0).toLocaleString()} rows` : null; const projectNameVal = job.input_data?.project_name || job.project_id || job.project; const hasQualityIssues = job.result_data?.has_data_quality_issues; const validationIssues = job.result_data?.validation?.issues || []; return (<div key={job.id} style={{ padding: '0.6rem 1rem', borderBottom: `1px solid ${colors.divider}`, display: 'flex', alignItems: 'center', gap: '0.75rem', background: hasQualityIssues ? `${colors.amber}15` : 'transparent' }}>{getStatusIcon(job.status)}<div style={{ flex: 1, minWidth: 0 }}><div style={{ fontSize: '0.8rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: colors.text }}>{filename}{hasQualityIssues && <span style={{ marginLeft: '0.5rem', fontSize: '0.7rem', color: colors.amber }}>⚠️ Data issues</span>}</div><div style={{ fontSize: '0.7rem', color: colors.textMuted }}>{resultMsg && <span style={{ color: hasQualityIssues ? colors.amber : colors.primary }}>{resultMsg} • </span>}{getProjectName(projectNameVal)} • {formatDate(job.created_at)}{job.error_message && <span style={{ color: colors.red }}> • {job.error_message}</span>}</div>{hasQualityIssues && validationIssues.length > 0 && <div style={{ fontSize: '0.65rem', color: colors.amber, marginTop: '0.25rem' }}>Issues in: {validationIssues.slice(0, 3).map(i => i.table).join(', ')}{validationIssues.length > 3 && ` +${validationIssues.length - 3} more`} — Check Data Health tab</div>}</div></div>); })}</div>}
      </div>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
