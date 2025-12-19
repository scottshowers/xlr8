/**
 * DataObservatoryPage.jsx - Unified Data View
 * 
 * COMMAND CENTER AESTHETIC
 * Single view showing what's in all three data stores:
 * - DuckDB (structured data - Excel, CSV, PDF tables)
 * - Supabase (document metadata, jobs, users)
 * - ChromaDB (vector embeddings/chunks)
 * 
 * Route: /system or could be /data-observatory
 */

import React, { useState, useEffect } from 'react';
import api from '../services/api';
import {
  Sun, Moon, Database, FileText, Layers, RefreshCw, Trash2,
  HardDrive, Cloud, Box, ChevronDown, ChevronRight, Search,
  AlertTriangle, CheckCircle, Filter, Download, Eye, Table2
} from 'lucide-react';

// Brand colors
const BRAND = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
};

// Theme definitions
const themes = {
  light: {
    bg: '#f6f5fa',
    bgCard: '#ffffff',
    border: '#e2e8f0',
    text: '#2a3441',
    textDim: '#5f6c7b',
    accent: BRAND.grassGreen,
  },
  dark: {
    bg: '#1a2332',
    bgCard: '#232f42',
    border: '#334766',
    text: '#e5e7eb',
    textDim: '#9ca3af',
    accent: BRAND.grassGreen,
  },
};

const STATUS = {
  green: '#10b981',
  amber: '#f59e0b',
  red: '#ef4444',
  blue: '#3b82f6',
  purple: '#8b5cf6',
  cyan: '#06b6d4',
};

// Data store definitions
const DATA_STORES = {
  duckdb: { label: 'DuckDB', icon: Database, color: STATUS.amber, desc: 'Structured Data (Excel, CSV, PDF tables)' },
  supabase: { label: 'Supabase', icon: Cloud, color: STATUS.green, desc: 'Document Metadata & System Records' },
  chromadb: { label: 'ChromaDB', icon: Layers, color: STATUS.purple, desc: 'Vector Embeddings & Semantic Chunks' },
};

export default function DataObservatoryPage({ embedded = false }) {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('xlr8-theme');
    return saved ? saved === 'dark' : false; // Default to light when embedded
  });
  const [time, setTime] = useState(new Date());
  const [loading, setLoading] = useState(true);
  const [activeStore, setActiveStore] = useState('overview');
  
  // Data from each store
  const [duckdbData, setDuckdbData] = useState(null);
  const [supabaseData, setSupabaseData] = useState(null);
  const [chromadbData, setChromadbData] = useState(null);
  
  // When embedded, always use light theme
  const T = embedded ? themes.light : (darkMode ? themes.dark : themes.light);

  useEffect(() => {
    if (!embedded) {
      localStorage.setItem('xlr8-theme', darkMode ? 'dark' : 'light');
    }
  }, [darkMode, embedded]);

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    console.log('[Observatory] Loading data...');
    try {
      const [duckRes, docsRes, chromaRes] = await Promise.all([
        api.get('/status/structured').catch((err) => {
          console.error('[Observatory] DuckDB fetch failed:', err);
          return { data: { available: false, files: [], total_rows: 0 } };
        }),
        api.get('/status/documents').catch((err) => {
          console.error('[Observatory] Documents fetch failed:', err);
          return { data: { documents: [] } };
        }),
        api.get('/status/chromadb').catch((err) => {
          console.error('[Observatory] ChromaDB fetch failed:', err);
          return { data: { total_chunks: 0 } };
        }),
      ]);
      
      console.log('[Observatory] DuckDB response:', duckRes.data);
      console.log('[Observatory] Documents response:', docsRes.data);
      console.log('[Observatory] ChromaDB response:', chromaRes.data);
      
      setDuckdbData(duckRes.data);
      setSupabaseData(docsRes.data);
      setChromadbData(chromaRes.data);
    } catch (err) {
      console.error('[Observatory] Failed to load data:', err);
    } finally {
      setLoading(false);
      console.log('[Observatory] Loading complete');
    }
  };

  // Calculate totals
  const totals = {
    duckdb: {
      files: duckdbData?.total_files || 0,
      tables: duckdbData?.total_tables || 0,
      rows: duckdbData?.total_rows || 0,
    },
    supabase: {
      documents: supabaseData?.documents?.length || 0,
    },
    chromadb: {
      chunks: chromadbData?.total_chunks || 0,
    },
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Eye },
    { id: 'duckdb', label: 'DuckDB', icon: Database },
    { id: 'supabase', label: 'Documents', icon: FileText },
    { id: 'chromadb', label: 'Vectors', icon: Layers },
  ];

  return (
    <div style={{
      padding: embedded ? '0' : '1.5rem',
      background: embedded ? 'transparent' : T.bg,
      minHeight: embedded ? 'auto' : '100vh',
      color: T.text,
      fontFamily: "'Inter', system-ui, sans-serif",
      transition: 'background 0.3s ease, color 0.3s ease',
    }}>
      {/* Header - hidden when embedded */}
      {!embedded && (
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem',
      }}>
        <div>
          <h1 style={{
            fontSize: '1.5rem',
            fontWeight: 700,
            margin: 0,
            letterSpacing: '0.05em',
            fontFamily: "'Sora', sans-serif",
          }}>
            DATA OBSERVATORY
          </h1>
          <p style={{ color: T.textDim, margin: '0.25rem 0 0 0', fontSize: '0.85rem' }}>
            Unified view of all XLR8 data stores
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={loadAllData}
            disabled={loading}
            style={{
              background: T.bgCard,
              border: `1px solid ${T.border}`,
              borderRadius: '8px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              color: T.text,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
            }}
          >
            <RefreshCw size={16} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>

          <button
            onClick={() => setDarkMode(!darkMode)}
            style={{
              background: T.bgCard,
              border: `1px solid ${T.border}`,
              borderRadius: '8px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              color: T.text,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
            }}
          >
            {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            {darkMode ? 'Light' : 'Dark'}
          </button>

          <div style={{
            fontFamily: 'monospace',
            fontSize: '1.5rem',
            color: T.accent,
            textShadow: darkMode ? `0 0 20px ${T.accent}40` : 'none',
          }}>
            {time.toLocaleTimeString()}
          </div>
        </div>
      </div>
      )}

      {/* Embedded header - simplified */}
      {embedded && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: '#2a3441' }}>Data Observatory</h2>
          <button
            onClick={loadAllData}
            disabled={loading}
            style={{
              background: '#f8fafc',
              border: '1px solid #e1e8ed',
              borderRadius: '6px',
              padding: '0.4rem 0.75rem',
              cursor: 'pointer',
              color: '#5f6c7b',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              fontSize: '0.8rem',
            }}
          >
            <RefreshCw size={14} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>
      )}

      {/* Stats Bar - Three Stores */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '1rem',
        marginBottom: '2rem',
      }}>
        {Object.entries(DATA_STORES).map(([key, store]) => {
          const Icon = store.icon;
          let mainValue, subValue;
          
          if (key === 'duckdb') {
            mainValue = totals.duckdb.rows.toLocaleString();
            subValue = `${totals.duckdb.files} files • ${totals.duckdb.tables} tables`;
          } else if (key === 'supabase') {
            mainValue = totals.supabase.documents.toLocaleString();
            subValue = 'documents tracked';
          } else {
            mainValue = totals.chromadb.chunks.toLocaleString();
            subValue = 'vector chunks';
          }

          return (
            <div
              key={key}
              onClick={() => setActiveStore(key)}
              style={{
                background: T.bgCard,
                border: `1px solid ${activeStore === key ? store.color : T.border}`,
                borderRadius: '12px',
                padding: '1.25rem',
                cursor: 'pointer',
                position: 'relative',
                overflow: 'hidden',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: 3,
                background: store.color,
                boxShadow: `0 0 10px ${store.color}`,
              }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: T.textDim, marginBottom: '0.25rem', fontWeight: 600 }}>
                    {store.label}
                  </div>
                  <div style={{
                    fontSize: '2rem',
                    fontWeight: 700,
                    color: store.color,
                    textShadow: darkMode ? `0 0 20px ${store.color}40` : 'none',
                    fontFamily: 'monospace',
                  }}>
                    {loading ? '...' : mainValue}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: T.textDim, marginTop: '0.25rem' }}>
                    {loading ? 'Loading...' : subValue}
                  </div>
                </div>
                <Icon size={28} style={{ opacity: 0.5, color: store.color }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: '0.5rem',
        marginBottom: '1.5rem',
        borderBottom: `1px solid ${T.border}`,
        paddingBottom: '0.5rem',
      }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveStore(tab.id)}
            style={{
              background: activeStore === tab.id ? T.accent : 'transparent',
              border: 'none',
              borderRadius: '6px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              color: activeStore === tab.id ? 'white' : T.textDim,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
              fontWeight: activeStore === tab.id ? 600 : 400,
            }}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{
        background: T.bgCard,
        border: `1px solid ${T.border}`,
        borderRadius: '12px',
        overflow: 'hidden',
      }}>
        {loading ? (
          <div style={{ padding: '4rem', textAlign: 'center', color: T.textDim }}>
            <RefreshCw size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
            <p>Loading data stores...</p>
          </div>
        ) : (
          <div style={{ padding: '1.5rem' }}>
            {activeStore === 'overview' && (
              <OverviewPanel T={T} darkMode={darkMode} duckdbData={duckdbData} supabaseData={supabaseData} chromadbData={chromadbData} />
            )}
            {activeStore === 'duckdb' && (
              <DuckDBPanel T={T} darkMode={darkMode} data={duckdbData} onRefresh={loadAllData} />
            )}
            {activeStore === 'supabase' && (
              <SupabasePanel T={T} darkMode={darkMode} data={supabaseData} />
            )}
            {activeStore === 'chromadb' && (
              <ChromaDBPanel T={T} darkMode={darkMode} data={chromadbData} />
            )}
          </div>
        )}
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// Overview Panel - Summary of all stores
function OverviewPanel({ T, darkMode, duckdbData, supabaseData, chromadbData }) {
  const stores = [
    {
      name: 'DuckDB',
      icon: Database,
      color: STATUS.amber,
      status: duckdbData?.available !== false ? 'healthy' : 'offline',
      metrics: [
        { label: 'Files', value: duckdbData?.total_files || 0 },
        { label: 'Tables', value: duckdbData?.total_tables || 0 },
        { label: 'Total Rows', value: (duckdbData?.total_rows || 0).toLocaleString() },
      ],
      description: 'Structured analytics data from Excel, CSV, and PDF tables.',
    },
    {
      name: 'Supabase',
      icon: Cloud,
      color: STATUS.green,
      status: 'healthy',
      metrics: [
        { label: 'Documents', value: supabaseData?.documents?.length || 0 },
        { label: 'With Chunks', value: supabaseData?.documents?.filter(d => d.chunk_count > 0).length || 0 },
      ],
      description: 'Document metadata, processing jobs, and system records.',
    },
    {
      name: 'ChromaDB',
      icon: Layers,
      color: STATUS.purple,
      status: chromadbData?.error ? 'error' : 'healthy',
      metrics: [
        { label: 'Vector Chunks', value: (chromadbData?.total_chunks || 0).toLocaleString() },
      ],
      description: 'Semantic embeddings for AI-powered search and analysis.',
    },
  ];

  return (
    <div>
      <h3 style={{ margin: '0 0 1.5rem 0', fontSize: '1rem', fontWeight: 600 }}>
        System Overview
      </h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {stores.map((store, i) => {
          const Icon = store.icon;
          return (
            <div
              key={i}
              style={{
                background: T.bg,
                border: `1px solid ${T.border}`,
                borderRadius: '8px',
                padding: '1.25rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Icon size={24} style={{ color: store.color }} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '1rem' }}>{store.name}</div>
                    <div style={{ fontSize: '0.8rem', color: T.textDim }}>{store.description}</div>
                  </div>
                </div>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.25rem 0.75rem',
                  background: store.status === 'healthy' ? `${STATUS.green}20` : `${STATUS.red}20`,
                  borderRadius: '20px',
                }}>
                  {store.status === 'healthy' ? (
                    <CheckCircle size={14} style={{ color: STATUS.green }} />
                  ) : (
                    <AlertTriangle size={14} style={{ color: STATUS.red }} />
                  )}
                  <span style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: store.status === 'healthy' ? STATUS.green : STATUS.red,
                    textTransform: 'uppercase',
                  }}>
                    {store.status}
                  </span>
                </div>
              </div>
              
              <div style={{ display: 'flex', gap: '2rem' }}>
                {store.metrics.map((metric, j) => (
                  <div key={j}>
                    <div style={{
                      fontSize: '1.5rem',
                      fontWeight: 700,
                      color: store.color,
                      fontFamily: 'monospace',
                      textShadow: darkMode ? `0 0 15px ${store.color}40` : 'none',
                    }}>
                      {metric.value}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: T.textDim }}>{metric.label}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// DuckDB Panel - Structured data details
function DuckDBPanel({ T, darkMode, data, onRefresh }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [expanded, setExpanded] = useState({});

  const files = data?.files || [];
  const filteredFiles = files.filter(f =>
    f.filename?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    f.project?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const toggleExpand = (key) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>
          <Database size={18} style={{ verticalAlign: 'middle', marginRight: '0.5rem', color: STATUS.amber }} />
          Structured Data ({files.length} files, {(data?.total_rows || 0).toLocaleString()} rows)
        </h3>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <div style={{ position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: T.textDim }} />
            <input
              type="text"
              placeholder="Search files..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                background: T.bg,
                border: `1px solid ${T.border}`,
                borderRadius: '6px',
                padding: '0.5rem 0.75rem 0.5rem 2.25rem',
                color: T.text,
                fontSize: '0.85rem',
                width: '200px',
              }}
            />
          </div>
        </div>
      </div>

      {filteredFiles.length === 0 ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: T.textDim }}>
          <Table2 size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
          <p>No structured data files found.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {filteredFiles.map((file, i) => {
            const key = `${file.project}-${file.filename}`;
            const isExpanded = expanded[key];
            
            return (
              <div
                key={i}
                style={{
                  background: T.bg,
                  border: `1px solid ${T.border}`,
                  borderRadius: '8px',
                  overflow: 'hidden',
                }}
              >
                <div
                  onClick={() => toggleExpand(key)}
                  style={{
                    padding: '1rem',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <FileText size={20} style={{ color: STATUS.amber }} />
                    <div>
                      <div style={{ fontWeight: 600 }}>{file.filename}</div>
                      <div style={{ fontSize: '0.8rem', color: T.textDim }}>
                        Project: {file.project} • {file.total_rows?.toLocaleString() || 0} rows • {file.sheets?.length || 0} sheets
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ fontSize: '0.75rem', color: T.textDim }}>
                      {file.loaded_at ? new Date(file.loaded_at).toLocaleDateString() : 'N/A'}
                    </span>
                    {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                  </div>
                </div>
                
                {isExpanded && file.sheets && (
                  <div style={{ borderTop: `1px solid ${T.border}`, padding: '1rem' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                      <thead>
                        <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                          <th style={{ textAlign: 'left', padding: '0.5rem', color: T.textDim, fontWeight: 600 }}>Table</th>
                          <th style={{ textAlign: 'left', padding: '0.5rem', color: T.textDim, fontWeight: 600 }}>Sheet</th>
                          <th style={{ textAlign: 'right', padding: '0.5rem', color: T.textDim, fontWeight: 600 }}>Rows</th>
                          <th style={{ textAlign: 'right', padding: '0.5rem', color: T.textDim, fontWeight: 600 }}>Columns</th>
                        </tr>
                      </thead>
                      <tbody>
                        {file.sheets.map((sheet, j) => (
                          <tr key={j} style={{ borderBottom: `1px solid ${T.border}` }}>
                            <td style={{ padding: '0.5rem', fontFamily: 'monospace', fontSize: '0.8rem' }}>{sheet.table_name}</td>
                            <td style={{ padding: '0.5rem' }}>{sheet.sheet_name || '-'}</td>
                            <td style={{ padding: '0.5rem', textAlign: 'right', fontFamily: 'monospace' }}>{sheet.row_count?.toLocaleString()}</td>
                            <td style={{ padding: '0.5rem', textAlign: 'right' }}>{sheet.column_count || sheet.columns?.length || 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Supabase Panel - Documents
function SupabasePanel({ T, darkMode, data }) {
  const [searchTerm, setSearchTerm] = useState('');
  const documents = data?.documents || [];
  
  const filteredDocs = documents.filter(d =>
    d.filename?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.project?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>
          <Cloud size={18} style={{ verticalAlign: 'middle', marginRight: '0.5rem', color: STATUS.green }} />
          Documents ({documents.length})
        </h3>
        <div style={{ position: 'relative' }}>
          <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: T.textDim }} />
          <input
            type="text"
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              background: T.bg,
              border: `1px solid ${T.border}`,
              borderRadius: '6px',
              padding: '0.5rem 0.75rem 0.5rem 2.25rem',
              color: T.text,
              fontSize: '0.85rem',
              width: '200px',
            }}
          />
        </div>
      </div>

      {filteredDocs.length === 0 ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: T.textDim }}>
          <FileText size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
          <p>No documents found.</p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                <th style={{ textAlign: 'left', padding: '0.75rem', color: T.textDim, fontWeight: 600 }}>Filename</th>
                <th style={{ textAlign: 'left', padding: '0.75rem', color: T.textDim, fontWeight: 600 }}>Project</th>
                <th style={{ textAlign: 'left', padding: '0.75rem', color: T.textDim, fontWeight: 600 }}>Type</th>
                <th style={{ textAlign: 'right', padding: '0.75rem', color: T.textDim, fontWeight: 600 }}>Chunks</th>
                <th style={{ textAlign: 'right', padding: '0.75rem', color: T.textDim, fontWeight: 600 }}>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {filteredDocs.slice(0, 50).map((doc, i) => (
                <tr key={doc.id || i} style={{ borderBottom: `1px solid ${T.border}` }}>
                  <td style={{ padding: '0.75rem', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {doc.filename}
                  </td>
                  <td style={{ padding: '0.75rem' }}>{doc.project || '-'}</td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{
                      padding: '0.2rem 0.5rem',
                      background: darkMode ? `${STATUS.blue}20` : '#eff6ff',
                      color: STATUS.blue,
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                    }}>
                      {doc.file_type || 'unknown'}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace' }}>
                    {doc.chunk_count || 0}
                  </td>
                  <td style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.8rem', color: T.textDim }}>
                    {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredDocs.length > 50 && (
            <div style={{ padding: '1rem', textAlign: 'center', color: T.textDim, fontSize: '0.85rem' }}>
              Showing 50 of {filteredDocs.length} documents
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ChromaDB Panel - Vectors
function ChromaDBPanel({ T, darkMode, data }) {
  return (
    <div>
      <h3 style={{ margin: '0 0 1.5rem 0', fontSize: '1rem', fontWeight: 600 }}>
        <Layers size={18} style={{ verticalAlign: 'middle', marginRight: '0.5rem', color: STATUS.purple }} />
        Vector Store
      </h3>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        <div style={{
          background: T.bg,
          border: `1px solid ${T.border}`,
          borderRadius: '8px',
          padding: '1.5rem',
          textAlign: 'center',
        }}>
          <div style={{
            fontSize: '3rem',
            fontWeight: 700,
            color: STATUS.purple,
            fontFamily: 'monospace',
            textShadow: darkMode ? `0 0 20px ${STATUS.purple}40` : 'none',
          }}>
            {(data?.total_chunks || 0).toLocaleString()}
          </div>
          <div style={{ fontSize: '0.85rem', color: T.textDim, marginTop: '0.5rem' }}>
            Total Vector Chunks
          </div>
        </div>
        
        <div style={{
          background: T.bg,
          border: `1px solid ${T.border}`,
          borderRadius: '8px',
          padding: '1.5rem',
          textAlign: 'center',
        }}>
          <div style={{
            fontSize: '3rem',
            fontWeight: 700,
            color: STATUS.cyan,
            fontFamily: 'monospace',
            textShadow: darkMode ? `0 0 20px ${STATUS.cyan}40` : 'none',
          }}>
            384
          </div>
          <div style={{ fontSize: '0.85rem', color: T.textDim, marginTop: '0.5rem' }}>
            Embedding Dimensions
          </div>
        </div>
      </div>

      <div style={{
        background: T.bg,
        border: `1px solid ${T.border}`,
        borderRadius: '8px',
        padding: '1rem',
      }}>
        <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.9rem', fontWeight: 600 }}>About ChromaDB</h4>
        <p style={{ margin: 0, fontSize: '0.85rem', color: T.textDim, lineHeight: 1.6 }}>
          ChromaDB stores semantic embeddings of your documents, enabling AI-powered similarity search 
          and intelligent analysis. Each "chunk" represents a portion of a document converted to a 
          high-dimensional vector for semantic understanding.
        </p>
      </div>

      {data?.error && (
        <div style={{
          marginTop: '1rem',
          padding: '1rem',
          background: darkMode ? `${STATUS.red}20` : '#fef2f2',
          border: `1px solid ${STATUS.red}40`,
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          color: STATUS.red,
        }}>
          <AlertTriangle size={18} />
          <span>Connection issue: {data.error}</span>
        </div>
      )}
    </div>
  );
}
