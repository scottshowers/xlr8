/**
 * VacuumExplore.jsx - Intelligent Extract Explorer
 * ================================================
 * 
 * Browse extracted tables with section/column detection.
 * Confirm or correct detections to improve learning.
 * 
 * Author: XLR8 Team
 */

import React, { useState, useEffect, useCallback } from 'react';

// API base - adjust for your environment
const API_BASE = '/api';

// Confidence thresholds for visual indicators
const CONFIDENCE = {
  HIGH: 0.7,
  MEDIUM: 0.4
};

// Section type display info
const SECTION_INFO = {
  employee_info: { label: 'Employee Info', color: '#3b82f6', icon: '👤' },
  earnings: { label: 'Earnings', color: '#22c55e', icon: '💰' },
  taxes: { label: 'Taxes', color: '#ef4444', icon: '🏛️' },
  deductions: { label: 'Deductions', color: '#f59e0b', icon: '📋' },
  pay_info: { label: 'Pay Info', color: '#8b5cf6', icon: '💵' },
  unknown: { label: 'Unknown', color: '#6b7280', icon: '❓' }
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function VacuumExplore() {
  // State
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [extracts, setExtracts] = useState([]);
  const [selectedExtract, setSelectedExtract] = useState(null);
  const [extractDetail, setExtractDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sectionTypes, setSectionTypes] = useState([]);
  const [columnTypes, setColumnTypes] = useState({});
  const [learningStats, setLearningStats] = useState(null);

  // Load initial data
  useEffect(() => {
    loadFiles();
    loadTypeDefinitions();
    loadLearningStats();
  }, []);

  // Load files list
  const loadFiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/vacuum/files`);
      const data = await res.json();
      setFiles(data.files || []);
    } catch (err) {
      setError('Failed to load files');
    }
  };

  // Load type definitions
  const loadTypeDefinitions = async () => {
    try {
      const [sectRes, colRes] = await Promise.all([
        fetch(`${API_BASE}/vacuum/section-types`),
        fetch(`${API_BASE}/vacuum/column-types`)
      ]);
      const sectData = await sectRes.json();
      const colData = await colRes.json();
      setSectionTypes(sectData.section_types || []);
      setColumnTypes(colData.column_types || {});
    } catch (err) {
      console.error('Failed to load type definitions:', err);
    }
  };

  // Load learning stats
  const loadLearningStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/vacuum/learning-stats`);
      const data = await res.json();
      setLearningStats(data.stats);
    } catch (err) {
      console.error('Failed to load learning stats:', err);
    }
  };

  // Load extracts for a file
  const loadExtracts = async (sourceFile) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/vacuum/extracts?source_file=${encodeURIComponent(sourceFile)}`);
      const data = await res.json();
      setExtracts(data.extracts || []);
      setSelectedExtract(null);
      setExtractDetail(null);
    } catch (err) {
      setError('Failed to load extracts');
    } finally {
      setLoading(false);
    }
  };

  // Load extract detail
  const loadExtractDetail = async (extractId) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/vacuum/extract/${extractId}`);
      const data = await res.json();
      setExtractDetail(data);
    } catch (err) {
      setError('Failed to load extract detail');
    } finally {
      setLoading(false);
    }
  };

  // Handle file selection
  const handleFileSelect = (file) => {
    setSelectedFile(file);
    loadExtracts(file.source_file);
  };

  // Handle extract selection
  const handleExtractSelect = (extract) => {
    setSelectedExtract(extract);
    loadExtractDetail(extract.id);
  };

  // Confirm section
  const confirmSection = async (extractId, sectionType, isCorrection = false) => {
    try {
      const res = await fetch(`${API_BASE}/vacuum/confirm-section`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          extract_id: extractId,
          section_type: sectionType,
          user_corrected: isCorrection
        })
      });
      
      if (res.ok) {
        // Reload extract detail
        loadExtractDetail(extractId);
        loadLearningStats();
      }
    } catch (err) {
      setError('Failed to confirm section');
    }
  };

  // Confirm column
  const confirmColumn = async (extractId, colIndex, colType, isCorrection = false) => {
    try {
      const res = await fetch(`${API_BASE}/vacuum/confirm-column`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          extract_id: extractId,
          column_index: colIndex,
          column_type: colType,
          user_corrected: isCorrection
        })
      });
      
      if (res.ok) {
        loadExtractDetail(extractId);
        loadLearningStats();
      }
    } catch (err) {
      setError('Failed to confirm column');
    }
  };

  // Confirm all columns
  const confirmAllColumns = async () => {
    if (!extractDetail?.column_classifications) return;
    
    const mappings = {};
    extractDetail.column_classifications.forEach((col, idx) => {
      mappings[idx] = col.detected_type;
    });
    
    try {
      const res = await fetch(`${API_BASE}/vacuum/confirm-all-columns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          extract_id: extractDetail.id,
          column_mappings: mappings
        })
      });
      
      if (res.ok) {
        loadExtractDetail(extractDetail.id);
        loadLearningStats();
      }
    } catch (err) {
      setError('Failed to confirm columns');
    }
  };

  // Re-detect
  const redetect = async (extractId) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/vacuum/redetect/${extractId}`, {
        method: 'POST'
      });
      
      if (res.ok) {
        loadExtractDetail(extractId);
      }
    } catch (err) {
      setError('Failed to re-detect');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="vacuum-explore" style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>🔬 Vacuum Explorer</h1>
        {learningStats && (
          <div style={styles.statsBar}>
            <span style={styles.stat}>
              📚 {learningStats.section_patterns} section patterns
            </span>
            <span style={styles.stat}>
              📊 {learningStats.column_patterns} column patterns
            </span>
            <span style={styles.stat}>
              🏢 {learningStats.vendor_signatures} vendors
            </span>
            <span style={styles.stat}>
              ✅ {learningStats.confirmed_mappings} confirmed mappings
            </span>
          </div>
        )}
      </div>

      {error && (
        <div style={styles.error}>
          {error}
          <button onClick={() => setError(null)} style={styles.dismissBtn}>×</button>
        </div>
      )}

      <div style={styles.layout}>
        {/* Files Panel */}
        <div style={styles.panel}>
          <h3 style={styles.panelTitle}>📁 Files</h3>
          <div style={styles.fileList}>
            {files.length === 0 ? (
              <p style={styles.empty}>No files uploaded yet</p>
            ) : (
              files.map((file, idx) => (
                <div
                  key={idx}
                  style={{
                    ...styles.fileItem,
                    ...(selectedFile?.source_file === file.source_file ? styles.fileItemSelected : {})
                  }}
                  onClick={() => handleFileSelect(file)}
                >
                  <div style={styles.fileName}>{file.source_file}</div>
                  <div style={styles.fileMeta}>
                    {file.table_count} tables • {file.total_rows} rows
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Extracts Panel */}
        <div style={styles.panel}>
          <h3 style={styles.panelTitle}>📋 Extracts</h3>
          {loading && !extractDetail ? (
            <p style={styles.loading}>Loading...</p>
          ) : extracts.length === 0 ? (
            <p style={styles.empty}>Select a file to view extracts</p>
          ) : (
            <div style={styles.extractList}>
              {extracts.map((ext) => (
                <ExtractCard
                  key={ext.id}
                  extract={ext}
                  selected={selectedExtract?.id === ext.id}
                  onClick={() => handleExtractSelect(ext)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Detail Panel */}
        <div style={{ ...styles.panel, flex: 2 }}>
          <h3 style={styles.panelTitle}>🔍 Detail</h3>
          {extractDetail ? (
            <ExtractDetail
              extract={extractDetail}
              sectionTypes={sectionTypes}
              columnTypes={columnTypes}
              onConfirmSection={confirmSection}
              onConfirmColumn={confirmColumn}
              onConfirmAll={confirmAllColumns}
              onRedetect={redetect}
              loading={loading}
            />
          ) : (
            <p style={styles.empty}>Select an extract to view details</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// EXTRACT CARD COMPONENT
// ============================================================================

function ExtractCard({ extract, selected, onClick }) {
  const section = extract.detected_section || 'unknown';
  const info = SECTION_INFO[section] || SECTION_INFO.unknown;
  const confidence = extract.section_confidence || 0;
  
  return (
    <div
      style={{
        ...styles.extractCard,
        borderLeftColor: info.color,
        ...(selected ? styles.extractCardSelected : {})
      }}
      onClick={onClick}
    >
      <div style={styles.extractHeader}>
        <span style={styles.extractIcon}>{info.icon}</span>
        <span style={styles.extractSection}>{info.label}</span>
        <ConfidenceBadge confidence={confidence} />
      </div>
      <div style={styles.extractMeta}>
        Table {extract.table_index + 1} • {extract.row_count} rows • {extract.raw_headers?.length || 0} cols
      </div>
      {extract.raw_headers && (
        <div style={styles.extractHeaders}>
          {extract.raw_headers.slice(0, 4).join(', ')}
          {extract.raw_headers.length > 4 && '...'}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// EXTRACT DETAIL COMPONENT
// ============================================================================

function ExtractDetail({ 
  extract, 
  sectionTypes, 
  columnTypes, 
  onConfirmSection, 
  onConfirmColumn,
  onConfirmAll,
  onRedetect,
  loading 
}) {
  const [editingSection, setEditingSection] = useState(false);
  const [editingColumn, setEditingColumn] = useState(null);
  
  const section = extract.detected_section || 'unknown';
  const info = SECTION_INFO[section] || SECTION_INFO.unknown;
  const columns = extract.column_classifications || [];
  const preview = extract.preview || [];
  const headers = extract.raw_headers || [];

  // Get column types for current section
  const availableColumnTypes = [
    ...(columnTypes[section] || []),
    ...(columnTypes.universal || [])
  ];

  return (
    <div style={styles.detail}>
      {/* Section Detection */}
      <div style={styles.detectionBox}>
        <div style={styles.detectionHeader}>
          <span style={{ ...styles.sectionBadge, backgroundColor: info.color }}>
            {info.icon} {info.label}
          </span>
          <ConfidenceBadge confidence={extract.section_confidence} showLabel />
          
          <div style={styles.detectionActions}>
            {!editingSection ? (
              <>
                <button
                  style={styles.btnConfirm}
                  onClick={() => onConfirmSection(extract.id, section, false)}
                  title="Confirm this detection is correct"
                >
                  ✓ Confirm
                </button>
                <button
                  style={styles.btnCorrect}
                  onClick={() => setEditingSection(true)}
                  title="Correct this detection"
                >
                  ✎ Correct
                </button>
              </>
            ) : (
              <div style={styles.editRow}>
                <select
                  style={styles.select}
                  defaultValue={section}
                  onChange={(e) => {
                    onConfirmSection(extract.id, e.target.value, true);
                    setEditingSection(false);
                  }}
                >
                  {sectionTypes.map((st) => (
                    <option key={st.value} value={st.value}>{st.label}</option>
                  ))}
                </select>
                <button
                  style={styles.btnCancel}
                  onClick={() => setEditingSection(false)}
                >
                  Cancel
                </button>
              </div>
            )}
            <button
              style={styles.btnRedetect}
              onClick={() => onRedetect(extract.id)}
              disabled={loading}
              title="Re-run detection with updated patterns"
            >
              🔄 Re-detect
            </button>
          </div>
        </div>
        
        {extract.section_signals && (
          <div style={styles.signals}>
            Signals: {extract.section_signals.slice(0, 5).join(', ')}
            {extract.section_signals.length > 5 && '...'}
          </div>
        )}
      </div>

      {/* Column Classifications */}
      <div style={styles.columnsSection}>
        <div style={styles.columnsHeader}>
          <h4 style={styles.columnsTitle}>Column Classifications</h4>
          <button
            style={styles.btnConfirmAll}
            onClick={onConfirmAll}
            title="Confirm all column detections"
          >
            ✓ Confirm All
          </button>
        </div>
        
        <div style={styles.columnsGrid}>
          {columns.map((col, idx) => (
            <ColumnCard
              key={idx}
              column={col}
              header={headers[idx]}
              editing={editingColumn === idx}
              availableTypes={availableColumnTypes}
              onEdit={() => setEditingColumn(idx)}
              onConfirm={(type, isCorrection) => {
                onConfirmColumn(extract.id, idx, type, isCorrection);
                setEditingColumn(null);
              }}
              onCancel={() => setEditingColumn(null)}
            />
          ))}
        </div>
      </div>

      {/* Data Preview */}
      <div style={styles.previewSection}>
        <h4 style={styles.previewTitle}>
          Data Preview 
          {extract.truncated && <span style={styles.truncatedNote}> (showing {preview.length} of {extract.full_row_count} rows)</span>}
        </h4>
        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>
                {headers.map((h, idx) => (
                  <th key={idx} style={styles.th}>
                    <div style={styles.thHeader}>{h}</div>
                    {columns[idx] && (
                      <div style={styles.thType}>
                        → {columns[idx].detected_type}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.slice(0, 10).map((row, ridx) => (
                <tr key={ridx}>
                  {row.map((cell, cidx) => (
                    <td key={cidx} style={styles.td}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// COLUMN CARD COMPONENT
// ============================================================================

function ColumnCard({ column, header, editing, availableTypes, onEdit, onConfirm, onCancel }) {
  const [selectedType, setSelectedType] = useState(column.detected_type);
  
  return (
    <div style={styles.columnCard}>
      <div style={styles.columnHeader}>{header}</div>
      <div style={styles.columnDetected}>
        → {column.detected_type}
      </div>
      <ConfidenceBadge confidence={column.confidence} small />
      
      {!editing ? (
        <div style={styles.columnActions}>
          <button
            style={styles.btnSmallConfirm}
            onClick={() => onConfirm(column.detected_type, false)}
            title="Confirm"
          >
            ✓
          </button>
          <button
            style={styles.btnSmallEdit}
            onClick={onEdit}
            title="Correct"
          >
            ✎
          </button>
        </div>
      ) : (
        <div style={styles.columnEdit}>
          <select
            style={styles.selectSmall}
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            {availableTypes.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <button
            style={styles.btnSmallConfirm}
            onClick={() => onConfirm(selectedType, selectedType !== column.detected_type)}
          >
            ✓
          </button>
          <button
            style={styles.btnSmallCancel}
            onClick={onCancel}
          >
            ×
          </button>
        </div>
      )}
      
      {column.signals_matched && column.signals_matched.length > 0 && (
        <div style={styles.columnSignals}>
          {column.signals_matched.slice(0, 2).join(', ')}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// CONFIDENCE BADGE COMPONENT
// ============================================================================

function ConfidenceBadge({ confidence, showLabel = false, small = false }) {
  const pct = Math.round((confidence || 0) * 100);
  let color = '#ef4444'; // red
  let label = 'Low';
  
  if (confidence >= CONFIDENCE.HIGH) {
    color = '#22c55e'; // green
    label = 'High';
  } else if (confidence >= CONFIDENCE.MEDIUM) {
    color = '#f59e0b'; // amber
    label = 'Medium';
  }
  
  return (
    <span style={{
      ...styles.confidenceBadge,
      backgroundColor: color,
      fontSize: small ? '10px' : '12px',
      padding: small ? '1px 4px' : '2px 6px'
    }}>
      {pct}%{showLabel && ` (${label})`}
    </span>
  );
}

// ============================================================================
// STYLES
// ============================================================================

const styles = {
  container: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    padding: '20px',
    backgroundColor: '#f8fafc',
    minHeight: '100vh'
  },
  header: {
    marginBottom: '20px'
  },
  title: {
    margin: '0 0 10px 0',
    fontSize: '24px',
    color: '#1e293b'
  },
  statsBar: {
    display: 'flex',
    gap: '20px',
    fontSize: '13px',
    color: '#64748b'
  },
  stat: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px'
  },
  error: {
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    color: '#dc2626',
    padding: '12px 16px',
    borderRadius: '8px',
    marginBottom: '16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  dismissBtn: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    cursor: 'pointer',
    color: '#dc2626'
  },
  layout: {
    display: 'flex',
    gap: '16px',
    alignItems: 'flex-start'
  },
  panel: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    padding: '16px',
    maxHeight: 'calc(100vh - 150px)',
    overflow: 'auto'
  },
  panelTitle: {
    margin: '0 0 12px 0',
    fontSize: '14px',
    fontWeight: '600',
    color: '#475569'
  },
  empty: {
    color: '#94a3b8',
    fontSize: '13px',
    textAlign: 'center',
    padding: '20px'
  },
  loading: {
    color: '#64748b',
    fontSize: '13px',
    textAlign: 'center',
    padding: '20px'
  },
  fileList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  },
  fileItem: {
    padding: '12px',
    borderRadius: '8px',
    backgroundColor: '#f8fafc',
    cursor: 'pointer',
    transition: 'all 0.15s ease'
  },
  fileItemSelected: {
    backgroundColor: '#e0f2fe',
    boxShadow: '0 0 0 2px #0ea5e9'
  },
  fileName: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#1e293b',
    wordBreak: 'break-all'
  },
  fileMeta: {
    fontSize: '11px',
    color: '#64748b',
    marginTop: '4px'
  },
  extractList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  },
  extractCard: {
    padding: '12px',
    borderRadius: '8px',
    backgroundColor: '#f8fafc',
    borderLeft: '4px solid #cbd5e1',
    cursor: 'pointer',
    transition: 'all 0.15s ease'
  },
  extractCardSelected: {
    backgroundColor: '#f0f9ff',
    boxShadow: '0 0 0 2px #0ea5e9'
  },
  extractHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  extractIcon: {
    fontSize: '16px'
  },
  extractSection: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#1e293b'
  },
  extractMeta: {
    fontSize: '11px',
    color: '#64748b',
    marginTop: '4px'
  },
  extractHeaders: {
    fontSize: '10px',
    color: '#94a3b8',
    marginTop: '4px',
    fontStyle: 'italic'
  },
  confidenceBadge: {
    display: 'inline-block',
    padding: '2px 6px',
    borderRadius: '10px',
    color: '#fff',
    fontSize: '12px',
    fontWeight: '500'
  },
  detail: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px'
  },
  detectionBox: {
    backgroundColor: '#f8fafc',
    borderRadius: '8px',
    padding: '12px'
  },
  detectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap'
  },
  sectionBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    borderRadius: '6px',
    color: '#fff',
    fontSize: '14px',
    fontWeight: '500'
  },
  detectionActions: {
    display: 'flex',
    gap: '8px',
    marginLeft: 'auto',
    flexWrap: 'wrap'
  },
  signals: {
    fontSize: '11px',
    color: '#64748b',
    marginTop: '8px'
  },
  btnConfirm: {
    backgroundColor: '#22c55e',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  btnCorrect: {
    backgroundColor: '#f59e0b',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  btnRedetect: {
    backgroundColor: '#6366f1',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  btnCancel: {
    backgroundColor: '#94a3b8',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  btnConfirmAll: {
    backgroundColor: '#22c55e',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  editRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center'
  },
  select: {
    padding: '6px 10px',
    borderRadius: '6px',
    border: '1px solid #cbd5e1',
    fontSize: '12px',
    backgroundColor: '#fff'
  },
  columnsSection: {
    backgroundColor: '#f8fafc',
    borderRadius: '8px',
    padding: '12px'
  },
  columnsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px'
  },
  columnsTitle: {
    margin: 0,
    fontSize: '13px',
    fontWeight: '600',
    color: '#475569'
  },
  columnsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
    gap: '8px'
  },
  columnCard: {
    backgroundColor: '#fff',
    borderRadius: '6px',
    padding: '8px',
    border: '1px solid #e2e8f0'
  },
  columnHeader: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: '4px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },
  columnDetected: {
    fontSize: '11px',
    color: '#0ea5e9',
    marginBottom: '4px'
  },
  columnActions: {
    display: 'flex',
    gap: '4px',
    marginTop: '6px'
  },
  columnEdit: {
    display: 'flex',
    gap: '4px',
    marginTop: '6px',
    flexWrap: 'wrap'
  },
  columnSignals: {
    fontSize: '9px',
    color: '#94a3b8',
    marginTop: '4px'
  },
  btnSmallConfirm: {
    backgroundColor: '#22c55e',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '2px 6px',
    fontSize: '11px',
    cursor: 'pointer'
  },
  btnSmallEdit: {
    backgroundColor: '#f59e0b',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '2px 6px',
    fontSize: '11px',
    cursor: 'pointer'
  },
  btnSmallCancel: {
    backgroundColor: '#94a3b8',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '2px 6px',
    fontSize: '11px',
    cursor: 'pointer'
  },
  selectSmall: {
    padding: '2px 4px',
    borderRadius: '4px',
    border: '1px solid #cbd5e1',
    fontSize: '10px',
    flex: 1,
    minWidth: '80px'
  },
  previewSection: {
    backgroundColor: '#f8fafc',
    borderRadius: '8px',
    padding: '12px'
  },
  previewTitle: {
    margin: '0 0 12px 0',
    fontSize: '13px',
    fontWeight: '600',
    color: '#475569'
  },
  truncatedNote: {
    fontWeight: '400',
    color: '#94a3b8',
    fontSize: '11px'
  },
  tableWrapper: {
    overflow: 'auto',
    maxHeight: '300px'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '11px'
  },
  th: {
    backgroundColor: '#e2e8f0',
    padding: '8px 6px',
    textAlign: 'left',
    fontWeight: '500',
    color: '#475569',
    position: 'sticky',
    top: 0,
    whiteSpace: 'nowrap'
  },
  thHeader: {
    fontWeight: '600'
  },
  thType: {
    fontSize: '10px',
    color: '#0ea5e9',
    fontWeight: '400'
  },
  td: {
    padding: '6px',
    borderBottom: '1px solid #f1f5f9',
    color: '#1e293b',
    maxWidth: '150px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  }
};
