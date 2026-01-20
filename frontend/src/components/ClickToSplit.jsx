/**
 * ClickToSplit.jsx
 * Deploy to: frontend/src/components/ClickToSplit.jsx
 * 
 * Consultant-friendly column splitting.
 * Show sample data, click where to split, name the new columns.
 * No regex, no character positions, no developer nonsense.
 */

import React, { useState, useEffect } from 'react';
import { Scissors, Check, X, Sparkles, AlertCircle } from 'lucide-react';
import api from '../services/api';

/**
 * Props:
 * - tableName: DuckDB table name
 * - columnName: Column to split
 * - sampleValues: Array of sample values (strings)
 * - customerId: Customer UUID for API calls
 * - onComplete: Callback after successful split
 * - onCancel: Close without saving
 */
export default function ClickToSplit({ 
  tableName,
  columnName,
  sampleValues = [], 
  customerId,
  onComplete,
  onCancel 
}) {
  // Clean samples - first 5 non-empty values
  const samples = sampleValues
    .filter(v => v !== null && v !== undefined && String(v).trim())
    .slice(0, 5)
    .map(v => String(v));

  const [splitPositions, setSplitPositions] = useState(samples.map(() => null));
  const [leftName, setLeftName] = useState('code');
  const [rightName, setRightName] = useState('description');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Infer best split position from user clicks
  const getInferredPattern = () => {
    const validSplits = splitPositions
      .map((pos, idx) => ({ pos, value: samples[idx] }))
      .filter(s => s.pos !== null);

    if (validSplits.length === 0) return null;

    // Check: split after first word?
    const firstWordSplits = validSplits.filter(s => {
      const firstSpace = s.value.indexOf(' ');
      return firstSpace > 0 && Math.abs(s.pos - firstSpace) <= 1;
    });
    if (firstWordSplits.length === validSplits.length) {
      return { type: 'first_word', description: 'After first word' };
    }

    // Check: split at newline?
    const newlineSplits = validSplits.filter(s => {
      const nl = s.value.indexOf('\n');
      return nl > 0 && Math.abs(s.pos - nl) <= 1;
    });
    if (newlineSplits.length === validSplits.length) {
      return { type: 'newline', description: 'At line break' };
    }

    // Check: fixed position?
    const positions = validSplits.map(s => s.pos);
    if (positions.every(p => p === positions[0])) {
      return { type: 'position', position: positions[0], description: `At character ${positions[0]}` };
    }

    // Check: common delimiter?
    for (const delim of [' ', '-', '_', '/', '|', '\t']) {
      const delimSplits = validSplits.filter(s => {
        const delimIdx = s.value.indexOf(delim);
        return delimIdx > 0 && Math.abs(s.pos - delimIdx) <= 1;
      });
      if (delimSplits.length === validSplits.length) {
        const delimName = delim === ' ' ? 'space' : delim === '\t' ? 'tab' : `"${delim}"`;
        return { type: 'delimiter', delimiter: delim, description: `At first ${delimName}` };
      }
    }

    // Fallback: use average position
    const avgPos = Math.round(positions.reduce((a, b) => a + b, 0) / positions.length);
    return { type: 'position', position: avgPos, description: `At ~character ${avgPos}` };
  };

  // Apply pattern to get preview
  const getPreview = () => {
    const pattern = getInferredPattern();
    if (!pattern) return samples.map(v => ({ original: v, left: v, right: '' }));

    return samples.map((val, idx) => {
      // Use explicit position if set, otherwise infer
      let splitAt = splitPositions[idx];
      
      if (splitAt === null) {
        if (pattern.type === 'first_word') {
          splitAt = val.indexOf(' ');
        } else if (pattern.type === 'newline') {
          splitAt = val.indexOf('\n');
        } else if (pattern.type === 'delimiter') {
          splitAt = val.indexOf(pattern.delimiter);
        } else if (pattern.type === 'position') {
          splitAt = pattern.position;
        }
      }

      if (splitAt === null || splitAt < 0 || splitAt >= val.length) {
        return { original: val, left: val, right: '' };
      }

      return {
        original: val,
        left: val.substring(0, splitAt).trim(),
        right: val.substring(splitAt).trim().replace(/^[\s\-_\/|]+/, '') // Clean leading separators
      };
    });
  };

  const handlePositionClick = (sampleIdx, charIdx) => {
    const newPositions = [...splitPositions];
    // Toggle off if clicking same position
    newPositions[sampleIdx] = newPositions[sampleIdx] === charIdx ? null : charIdx;
    setSplitPositions(newPositions);
  };

  const handleApply = async () => {
    const pattern = getInferredPattern();
    if (!pattern) {
      setError('Click on at least one value to show where to split');
      return;
    }

    setSaving(true);
    setError('');

    try {
      const response = await api.post('/data-model/split-column', {
        customer_id: customerId,
        table_name: tableName,
        column_name: columnName,
        split_type: pattern.type,
        split_value: pattern.delimiter || pattern.position || null,
        new_column_names: [leftName, rightName]
      });

      if (response.data?.success) {
        onComplete && onComplete({
          originalColumn: columnName,
          newColumns: [leftName, rightName],
          rowsAffected: response.data.rows_affected
        });
      } else {
        setError(response.data?.error || 'Split failed');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to split column');
    } finally {
      setSaving(false);
    }
  };

  const pattern = getInferredPattern();
  const preview = getPreview();
  const hasValidSplit = preview.some(p => p.right);

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.headerTitle}>
            <Scissors size={20} style={{ color: '#3b82f6' }} />
            <h2 style={styles.title}>Split Column</h2>
          </div>
          <button onClick={onCancel} style={styles.closeBtn}>×</button>
        </div>

        {/* Instructions */}
        <div style={styles.instructions}>
          <strong>Click where you want to split.</strong> The platform will learn the pattern.
        </div>

        {/* Column info */}
        <div style={styles.columnInfo}>
          <span style={styles.columnLabel}>Splitting column:</span>
          <code style={styles.columnCode}>{columnName}</code>
          <span style={styles.columnLabel}>in table:</span>
          <code style={styles.columnCode}>{tableName}</code>
        </div>

        {/* Clickable samples */}
        <div style={styles.samplesSection}>
          <div style={styles.sectionTitle}>Click to mark split point</div>
          {samples.length === 0 ? (
            <div style={styles.noData}>No sample data available</div>
          ) : (
            <div style={styles.samplesList}>
              {samples.map((val, sampleIdx) => (
                <div key={sampleIdx} style={styles.sampleRow}>
                  <div style={styles.sampleValue}>
                    {val.split('').map((char, charIdx) => (
                      <React.Fragment key={charIdx}>
                        <span
                          onClick={() => handlePositionClick(sampleIdx, charIdx)}
                          style={{
                            ...styles.splitMarker,
                            backgroundColor: splitPositions[sampleIdx] === charIdx ? '#3b82f6' : 'transparent'
                          }}
                          title="Click to split here"
                        />
                        <span style={{
                          ...styles.char,
                          backgroundColor: splitPositions[sampleIdx] !== null && charIdx < splitPositions[sampleIdx] 
                            ? '#dbeafe' 
                            : splitPositions[sampleIdx] !== null && charIdx >= splitPositions[sampleIdx]
                            ? '#dcfce7'
                            : 'transparent'
                        }}>
                          {char === '\n' ? '↵' : char}
                        </span>
                      </React.Fragment>
                    ))}
                  </div>
                  {splitPositions[sampleIdx] !== null && (
                    <button 
                      onClick={() => handlePositionClick(sampleIdx, splitPositions[sampleIdx])}
                      style={styles.clearBtn}
                    >
                      <X size={12} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pattern detected */}
        {pattern && (
          <div style={styles.patternBox}>
            <Sparkles size={16} style={{ color: '#8b5cf6' }} />
            <span>Pattern: <strong>{pattern.description}</strong></span>
          </div>
        )}

        {/* Preview */}
        {hasValidSplit && (
          <div style={styles.previewSection}>
            <div style={styles.sectionTitle}>Preview - Name your new columns</div>
            <div style={styles.previewHeader}>
              <input
                type="text"
                value={leftName}
                onChange={(e) => setLeftName(e.target.value.toLowerCase().replace(/\s+/g, '_'))}
                style={styles.nameInput}
                placeholder="left column name"
              />
              <input
                type="text"
                value={rightName}
                onChange={(e) => setRightName(e.target.value.toLowerCase().replace(/\s+/g, '_'))}
                style={styles.nameInput}
                placeholder="right column name"
              />
            </div>
            <div style={styles.previewRows}>
              {preview.map((row, idx) => (
                <div key={idx} style={styles.previewRow}>
                  <div style={styles.previewCell}>{row.left || '—'}</div>
                  <div style={styles.previewCell}>{row.right || '—'}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={styles.error}>
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {/* Actions */}
        <div style={styles.actions}>
          <button onClick={onCancel} style={styles.cancelBtn}>
            Cancel
          </button>
          <button 
            onClick={handleApply}
            disabled={saving || !hasValidSplit || !leftName || !rightName}
            style={{
              ...styles.applyBtn,
              opacity: (saving || !hasValidSplit || !leftName || !rightName) ? 0.5 : 1
            }}
          >
            {saving ? 'Splitting...' : <><Check size={16} /> Split Column</>}
          </button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000
  },
  modal: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    width: '90%',
    maxWidth: '600px',
    maxHeight: '85vh',
    overflow: 'auto',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '1px solid #e5e7eb'
  },
  headerTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px'
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '24px',
    cursor: 'pointer',
    color: '#6b7280'
  },
  instructions: {
    padding: '12px 20px',
    backgroundColor: '#f0f9ff',
    color: '#1e40af',
    fontSize: '13px'
  },
  columnInfo: {
    padding: '12px 20px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
    borderBottom: '1px solid #e5e7eb',
    fontSize: '13px'
  },
  columnLabel: {
    color: '#6b7280'
  },
  columnCode: {
    backgroundColor: '#f3f4f6',
    padding: '2px 8px',
    borderRadius: '4px',
    fontWeight: 600
  },
  samplesSection: {
    padding: '16px 20px'
  },
  sectionTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#374151',
    marginBottom: '10px'
  },
  noData: {
    color: '#6b7280',
    fontStyle: 'italic',
    padding: '20px',
    textAlign: 'center'
  },
  samplesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  },
  sampleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    backgroundColor: '#f9fafb',
    borderRadius: '6px',
    padding: '8px 12px'
  },
  sampleValue: {
    display: 'flex',
    flexWrap: 'wrap',
    fontFamily: 'monospace',
    fontSize: '14px',
    flex: 1
  },
  splitMarker: {
    width: '3px',
    height: '20px',
    borderRadius: '1px',
    cursor: 'pointer',
    transition: 'background-color 0.15s'
  },
  char: {
    padding: '2px 0',
    transition: 'background-color 0.15s'
  },
  clearBtn: {
    background: 'none',
    border: '1px solid #e5e7eb',
    borderRadius: '4px',
    padding: '4px',
    cursor: 'pointer',
    color: '#6b7280',
    display: 'flex'
  },
  patternBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 20px',
    backgroundColor: '#faf5ff',
    color: '#6b21a8',
    fontSize: '13px',
    borderTop: '1px solid #e5e7eb',
    borderBottom: '1px solid #e5e7eb'
  },
  previewSection: {
    padding: '16px 20px'
  },
  previewHeader: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px',
    marginBottom: '8px'
  },
  nameInput: {
    padding: '8px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 500
  },
  previewRows: {
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    overflow: 'hidden'
  },
  previewRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    borderBottom: '1px solid #e5e7eb'
  },
  previewCell: {
    padding: '8px 12px',
    fontSize: '13px',
    fontFamily: 'monospace',
    backgroundColor: '#fff',
    borderRight: '1px solid #e5e7eb'
  },
  error: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    margin: '0 20px 16px',
    padding: '10px 12px',
    backgroundColor: '#fef2f2',
    color: '#dc2626',
    borderRadius: '6px',
    fontSize: '13px'
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    padding: '16px 20px',
    borderTop: '1px solid #e5e7eb'
  },
  cancelBtn: {
    padding: '8px 16px',
    backgroundColor: '#f3f4f6',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer'
  },
  applyBtn: {
    padding: '8px 20px',
    backgroundColor: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px'
  }
};
