/**
 * DataObservatoryPage.jsx - Unified Data View
 * Clean professional design with theme support
 */

import React, { useState, useEffect } from 'react';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';
import { Database, FileText, Layers, RefreshCw, Cloud, ChevronDown, ChevronRight, Search, AlertTriangle, Eye, Table2 } from 'lucide-react';

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
  green: '#5a8a5a',    // Muted green
  greenLight: dark ? 'rgba(90, 138, 90, 0.15)' : 'rgba(90, 138, 90, 0.1)',
  purple: '#6b5a7a',   // Dusty purple
  purpleLight: dark ? 'rgba(107, 90, 122, 0.15)' : 'rgba(107, 90, 122, 0.1)',
  cyan: '#4a7a7a',     // Deep teal
  divider: dark ? '#2d3548' : '#e8ecf1',
  inputBg: dark ? '#1a1f2e' : '#f8fafc',
  tabBg: dark ? '#1e2433' : '#fafbfc',
});

export default function DataObservatoryPage({ embedded = false }) {
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  const [loading, setLoading] = useState(true);
  const [activeStore, setActiveStore] = useState('overview');
  const [duckdbData, setDuckdbData] = useState(null);
  const [supabaseData, setSupabaseData] = useState(null);
  const [chromadbData, setChromadbData] = useState(null);

  useEffect(() => { loadAllData(); }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [duckRes, docsRes, chromaRes] = await Promise.all([
        api.get('/platform').catch(() => ({ data: { files: [], total_rows: 0 } })),
        api.get('/status/documents').catch(() => ({ data: { documents: [] } })),
        api.get('/status/chromadb').catch(() => ({ data: { total_chunks: 0 } })),
      ]);
      setDuckdbData(duckRes.data);
      setSupabaseData(docsRes.data);
      setChromadbData(chromaRes.data);
    } catch (err) { console.error('[Observatory] Failed:', err); }
    finally { setLoading(false); }
  };

  const totals = {
    duckdb: { files: duckdbData?.total_files || 0, tables: duckdbData?.total_tables || 0, rows: duckdbData?.total_rows || 0 },
    supabase: { documents: supabaseData?.documents?.length || 0 },
    chromadb: { chunks: chromadbData?.total_chunks || 0 },
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Eye },
    { id: 'duckdb', label: 'DuckDB', icon: Database },
    { id: 'supabase', label: 'Documents', icon: FileText },
    { id: 'chromadb', label: 'Vectors', icon: Layers },
  ];

  return (
    <div>
      {!embedded && (
        <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.5rem', fontWeight: 700, color: colors.text, margin: 0 }}>Data Observatory</h1>
            <p style={{ color: colors.textMuted, marginTop: '0.25rem', fontSize: '0.875rem' }}>Unified view of all data stores</p>
          </div>
          <button onClick={loadAllData} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.5rem 1rem', background: 'transparent', border: `1px solid ${colors.divider}`, borderRadius: 8, color: colors.textMuted, fontSize: '0.85rem', cursor: 'pointer' }}>
            <RefreshCw size={16} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} /> Refresh
          </button>
        </div>
      )}

      <div style={{ background: embedded ? 'transparent' : colors.card, border: embedded ? 'none' : `1px solid ${colors.cardBorder}`, borderRadius: embedded ? 0 : 12, overflow: 'hidden', boxShadow: embedded ? 'none' : '0 1px 3px rgba(0,0,0,0.04)' }}>
        <div style={{ display: 'flex', borderBottom: `1px solid ${colors.divider}`, background: colors.tabBg }}>
          {tabs.map(tab => {
            const Icon = tab.icon;
            const isActive = activeStore === tab.id;
            return <button key={tab.id} onClick={() => setActiveStore(tab.id)} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '1rem 1.25rem', border: 'none', background: isActive ? colors.card : 'transparent', color: isActive ? colors.primary : colors.textMuted, fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer', borderBottom: isActive ? `2px solid ${colors.primary}` : '2px solid transparent', marginBottom: '-1px' }}><Icon size={18} />{tab.label}</button>;
          })}
        </div>
        <div style={{ padding: '1.5rem' }}>
          {activeStore === 'overview' && <OverviewPanel colors={colors} totals={totals} loading={loading} />}
          {activeStore === 'duckdb' && <DuckDBPanel colors={colors} data={duckdbData} />}
          {activeStore === 'supabase' && <SupabasePanel colors={colors} data={supabaseData} />}
          {activeStore === 'chromadb' && <ChromaDBPanel colors={colors} data={chromadbData} />}
        </div>
      </div>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function OverviewPanel({ colors, totals, loading }) {
  const stores = [
    { key: 'duckdb', label: 'DuckDB', icon: Database, color: colors.amber, desc: 'Structured Data', stats: [{ label: 'Files', value: totals.duckdb.files }, { label: 'Tables', value: totals.duckdb.tables }, { label: 'Rows', value: totals.duckdb.rows.toLocaleString() }] },
    { key: 'supabase', label: 'Supabase', icon: Cloud, color: colors.green, desc: 'Document Metadata', stats: [{ label: 'Documents', value: totals.supabase.documents }] },
    { key: 'chromadb', label: 'ChromaDB', icon: Layers, color: colors.purple, desc: 'Vector Embeddings', stats: [{ label: 'Chunks', value: totals.chromadb.chunks.toLocaleString() }] },
  ];
  if (loading) return <div style={{ padding: '3rem', textAlign: 'center', color: colors.textMuted }}><RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} /><p>Loading...</p></div>;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
      {stores.map(store => (
        <div key={store.key} style={{ background: colors.inputBg, border: `1px solid ${colors.divider}`, borderRadius: 10, padding: '1.25rem', borderTop: `3px solid ${store.color}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}><store.icon size={24} style={{ color: store.color }} /><div><div style={{ fontWeight: 600, color: colors.text }}>{store.label}</div><div style={{ fontSize: '0.75rem', color: colors.textMuted }}>{store.desc}</div></div></div>
          <div style={{ display: 'flex', gap: '1rem' }}>{store.stats.map((stat, i) => <div key={i} style={{ flex: 1, textAlign: 'center' }}><div style={{ fontSize: '1.5rem', fontWeight: 700, color: store.color, fontFamily: 'monospace' }}>{stat.value}</div><div style={{ fontSize: '0.7rem', color: colors.textMuted }}>{stat.label}</div></div>)}</div>
        </div>
      ))}
    </div>
  );
}

function DuckDBPanel({ colors, data }) {
  const [expandedFiles, setExpandedFiles] = useState(new Set());
  const files = data?.files || [];
  const toggleExpand = (f) => { const s = new Set(expandedFiles); if (s.has(f)) s.delete(f); else s.add(f); setExpandedFiles(s); };
  if (files.length === 0) return <div style={{ padding: '3rem', textAlign: 'center', color: colors.textMuted }}><Database size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} /><p>No structured data.</p></div>;
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Database size={18} style={{ color: colors.amber }} />Files ({files.length})</h3>
        <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.85rem', color: colors.textMuted }}><span><strong style={{ color: colors.text }}>{data?.total_tables || 0}</strong> tables</span><span><strong style={{ color: colors.text }}>{(data?.total_rows || 0).toLocaleString()}</strong> rows</span></div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {files.map((file, i) => { const isExpanded = expandedFiles.has(file.filename); return (
          <div key={i} style={{ border: `1px solid ${colors.divider}`, borderRadius: 8, overflow: 'hidden' }}>
            <div onClick={() => toggleExpand(file.filename)} style={{ padding: '0.875rem 1rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.75rem', background: colors.inputBg }}>
              {isExpanded ? <ChevronDown size={16} style={{ color: colors.textMuted }} /> : <ChevronRight size={16} style={{ color: colors.textMuted }} />}
              <Table2 size={16} style={{ color: colors.amber }} />
              <div style={{ flex: 1 }}><div style={{ fontWeight: 600, fontSize: '0.9rem', color: colors.text }}>{file.filename}</div><div style={{ fontSize: '0.75rem', color: colors.textMuted }}>{file.sheets?.length || 0} sheets • {(file.total_rows || 0).toLocaleString()} rows</div></div>
            </div>
            {isExpanded && file.sheets && <div style={{ borderTop: `1px solid ${colors.divider}`, padding: '1rem' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}><thead><tr style={{ borderBottom: `1px solid ${colors.divider}` }}><th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted, fontWeight: 600 }}>Table</th><th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted, fontWeight: 600 }}>Sheet</th><th style={{ textAlign: 'right', padding: '0.5rem', color: colors.textMuted, fontWeight: 600 }}>Rows</th><th style={{ textAlign: 'right', padding: '0.5rem', color: colors.textMuted, fontWeight: 600 }}>Cols</th></tr></thead><tbody>{file.sheets.map((sheet, j) => <tr key={j} style={{ borderBottom: `1px solid ${colors.divider}` }}><td style={{ padding: '0.5rem', fontFamily: 'monospace', fontSize: '0.8rem', color: colors.text }}>{sheet.table_name}</td><td style={{ padding: '0.5rem', color: colors.text }}>{sheet.sheet_name || '-'}</td><td style={{ padding: '0.5rem', textAlign: 'right', fontFamily: 'monospace', color: colors.text }}>{sheet.row_count?.toLocaleString()}</td><td style={{ padding: '0.5rem', textAlign: 'right', color: colors.text }}>{sheet.column_count || sheet.columns?.length || 0}</td></tr>)}</tbody></table></div>}
          </div>
        ); })}
      </div>
    </div>
  );
}

function SupabasePanel({ colors, data }) {
  const [searchTerm, setSearchTerm] = useState('');
  const documents = data?.documents || [];
  const filteredDocs = documents.filter(d => d.filename?.toLowerCase().includes(searchTerm.toLowerCase()) || d.project?.toLowerCase().includes(searchTerm.toLowerCase()));
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Cloud size={18} style={{ color: colors.green }} />Documents ({documents.length})</h3>
        <div style={{ position: 'relative' }}><Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: colors.textMuted }} /><input type="text" placeholder="Search..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} style={{ background: colors.inputBg, border: `1px solid ${colors.divider}`, borderRadius: 6, padding: '0.5rem 0.75rem 0.5rem 2.25rem', color: colors.text, fontSize: '0.85rem', width: '200px' }} /></div>
      </div>
      {filteredDocs.length === 0 ? <div style={{ padding: '3rem', textAlign: 'center', color: colors.textMuted }}><FileText size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} /><p>No documents.</p></div> : (
        <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}><thead><tr style={{ borderBottom: `1px solid ${colors.divider}` }}><th style={{ textAlign: 'left', padding: '0.75rem', color: colors.textMuted, fontWeight: 600 }}>Filename</th><th style={{ textAlign: 'left', padding: '0.75rem', color: colors.textMuted, fontWeight: 600 }}>Project</th><th style={{ textAlign: 'left', padding: '0.75rem', color: colors.textMuted, fontWeight: 600 }}>Type</th><th style={{ textAlign: 'right', padding: '0.75rem', color: colors.textMuted, fontWeight: 600 }}>Chunks</th></tr></thead><tbody>{filteredDocs.slice(0, 50).map((doc, i) => <tr key={doc.id || i} style={{ borderBottom: `1px solid ${colors.divider}` }}><td style={{ padding: '0.75rem', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: colors.text }}>{doc.filename}</td><td style={{ padding: '0.75rem', color: colors.text }}>{doc.project || '-'}</td><td style={{ padding: '0.75rem' }}><span style={{ padding: '0.2rem 0.5rem', background: colors.blueLight, color: colors.blue, borderRadius: 4, fontSize: '0.75rem', fontWeight: 600 }}>{doc.file_type || 'unknown'}</span></td><td style={{ padding: '0.75rem', textAlign: 'right', fontFamily: 'monospace', color: colors.text }}>{doc.chunk_count || 0}</td></tr>)}</tbody></table>{filteredDocs.length > 50 && <div style={{ padding: '1rem', textAlign: 'center', color: colors.textMuted, fontSize: '0.85rem' }}>Showing 50 of {filteredDocs.length}</div>}</div>
      )}
    </div>
  );
}

function ChromaDBPanel({ colors, data }) {
  return (
    <div>
      <h3 style={{ margin: '0 0 1.5rem 0', fontSize: '1rem', fontWeight: 600, color: colors.text, display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Layers size={18} style={{ color: colors.purple }} />Vector Store</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ background: colors.inputBg, border: `1px solid ${colors.divider}`, borderRadius: 8, padding: '1.5rem', textAlign: 'center' }}><div style={{ fontSize: '3rem', fontWeight: 700, color: colors.purple, fontFamily: 'monospace' }}>{(data?.total_chunks || 0).toLocaleString()}</div><div style={{ fontSize: '0.85rem', color: colors.textMuted, marginTop: '0.5rem' }}>Vector Chunks</div></div>
        <div style={{ background: colors.inputBg, border: `1px solid ${colors.divider}`, borderRadius: 8, padding: '1.5rem', textAlign: 'center' }}><div style={{ fontSize: '3rem', fontWeight: 700, color: colors.cyan, fontFamily: 'monospace' }}>384</div><div style={{ fontSize: '0.85rem', color: colors.textMuted, marginTop: '0.5rem' }}>Dimensions</div></div>
      </div>
      <div style={{ background: colors.inputBg, border: `1px solid ${colors.divider}`, borderRadius: 8, padding: '1rem' }}><h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.9rem', fontWeight: 600, color: colors.text }}>About ChromaDB</h4><p style={{ margin: 0, fontSize: '0.85rem', color: colors.textMuted, lineHeight: 1.6 }}>Stores semantic embeddings for AI-powered search.</p></div>
      {data?.error && <div style={{ marginTop: '1rem', padding: '1rem', background: colors.amberLight, border: `1px solid ${colors.amber}40`, borderRadius: 8, display: 'flex', alignItems: 'center', gap: '0.75rem', color: colors.amber }}><AlertTriangle size={18} /><span>{data.error}</span></div>}
    </div>
  );
}
