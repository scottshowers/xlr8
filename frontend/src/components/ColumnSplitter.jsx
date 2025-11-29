import React, { useState, useEffect } from 'react';

const API_BASE = '/api';

/**
 * ColumnSplitter Component
 * 
 * Allows users to manually split merged columns when auto-detection fails.
 * Provides pattern suggestions and live preview.
 */
export default function ColumnSplitter({ 
  extractId, 
  columnIndex, 
  columnHeader, 
  sampleValues, 
  sectionType,
  onSplitComplete,
  onCancel 
}) {
  // State
  const [splitMethod, setSplitMethod] = useState('pattern');
  const [pattern, setPattern] = useState('');
  const [newHeaders, setNewHeaders] = useState(['']);
  const [positions, setPositions] = useState('');
  const [delimiter, setDelimiter] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [preview, setPreview] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Load pattern suggestions on mount
  useEffect(() => {
    loadSuggestions();
  }, [sampleValues, sectionType]);

  // Update preview when pattern changes
  useEffect(() => {
    if (pattern && splitMethod === 'pattern') {
      generatePreview();
    }
  }, [pattern, splitMethod]);

  const loadSuggestions = async () => {
    try {
      const response = await fetch(`${API_BASE}/vacuum/detect-pattern`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sample_values: sampleValues,
          section_type: sectionType
        })
      });
      
      const data = await response.json();
      if (data.suggestions) {
        setSuggestions(data.suggestions);
        
        // Auto-select first suggestion
        if (data.suggestions.length > 0) {
          const first = data.suggestions[0];
          setPattern(first.pattern);
          setNewHeaders(first.headers);
        }
      }
    } catch (err) {
      console.error('Error loading suggestions:', err);
    }
  };

  const generatePreview = () => {
    if (!pattern || !sampleValues.length) return;
    
    try {
      const regex = new RegExp(pattern);
      const previews = sampleValues.slice(0, 5).map(val => {
        const match = regex.exec(val);
        if (match) {
          return match.slice(1); // Return capture groups
        }
        return ['(no match)'];
      });
      setPreview(previews);
      
      // Update headers count based on capture groups
      const firstMatch = regex.exec(sampleValues[0]);
      if (firstMatch && firstMatch.length - 1 !== newHeaders.length) {
        const count = firstMatch.length - 1;
        setNewHeaders(prev => {
          const updated = [...prev];
          while (updated.length < count) updated.push(`Column_${updated.length + 1}`);
          while (updated.length > count) updated.pop();
          return updated;
        });
      }
    } catch (err) {
      setPreview([['Invalid regex pattern']]);
    }
  };

  const applySuggestion = (suggestion) => {
    setPattern(suggestion.pattern);
    setNewHeaders(suggestion.headers);
    setSplitMethod('pattern');
  };

  const updateHeader = (index, value) => {
    setNewHeaders(prev => {
      const updated = [...prev];
      updated[index] = value;
      return updated;
    });
  };

  const executeSplit = async () => {
    setLoading(true);
    setError('');
    
    try {
      const body = {
        extract_id: extractId,
        column_index: columnIndex,
        split_method: splitMethod,
        new_headers: newHeaders.filter(h => h)
      };
      
      if (splitMethod === 'pattern') {
        body.pattern = pattern;
      } else if (splitMethod === 'positions') {
        body.positions = positions.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
      } else if (splitMethod === 'delimiter') {
        body.delimiter = delimiter;
      }
      
      const response = await fetch(`${API_BASE}/vacuum/split-column`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      const data = await response.json();
      
      if (data.success) {
        onSplitComplete(data);
      } else {
        setError(data.error || 'Split failed');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <h2 style={styles.title}>🔧 Split Merged Column</h2>
          <button onClick={onCancel} style={styles.closeBtn}>×</button>
        </div>

        {/* Current Column Info */}
        <div style={styles.infoBox}>
          <div style={styles.infoLabel}>Current Column</div>
          <div style={styles.infoValue}>{columnHeader}</div>
          <div style={styles.infoLabel}>Sample Values</div>
          <div style={styles.sampleList}>
            {sampleValues.slice(0, 3).map((val, i) => (
              <div key={i} style={styles.sampleItem}>
                {String(val).substring(0, 80)}{String(val).length > 80 ? '...' : ''}
              </div>
            ))}
          </div>
        </div>

        {/* AI Suggestions */}
        {suggestions.length > 0 && (
          <div style={styles.suggestionsBox}>
            <div style={styles.suggestionsTitle}>🤖 AI Detected Patterns</div>
            <div style={styles.suggestionsList}>
              {suggestions.map((sug, i) => (
                <div 
                  key={i} 
                  style={{
                    ...styles.suggestionCard,
                    borderColor: pattern === sug.pattern ? '#3b82f6' : '#e5e7eb'
                  }}
                  onClick={() => applySuggestion(sug)}
                >
                  <div style={styles.sugDescription}>{sug.description}</div>
                  <div style={styles.sugHeaders}>
                    → {sug.headers.join(' | ')}
                  </div>
                  {sug.is_row_merge && (
                    <div style={styles.rowMergeWarning}>
                      ⚠️ Multiple rows detected in single cell
                    </div>
                  )}
                  {sug.preview && (
                    <div style={styles.sugPreview}>
                      Preview: [{sug.preview.join(', ')}]
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Split Method Selection */}
        <div style={styles.methodSection}>
          <div style={styles.methodTitle}>Split Method</div>
          <div style={styles.methodButtons}>
            {['pattern', 'positions', 'delimiter'].map(method => (
              <button
                key={method}
                onClick={() => setSplitMethod(method)}
                style={{
                  ...styles.methodBtn,
                  backgroundColor: splitMethod === method ? '#3b82f6' : '#f3f4f6',
                  color: splitMethod === method ? '#fff' : '#374151'
                }}
              >
                {method === 'pattern' && '🎯 Pattern (Regex)'}
                {method === 'positions' && '📏 Character Positions'}
                {method === 'delimiter' && '✂️ Delimiter'}
              </button>
            ))}
          </div>
        </div>

        {/* Method-specific inputs */}
        <div style={styles.inputSection}>
          {splitMethod === 'pattern' && (
            <>
              <label style={styles.label}>Regex Pattern (with capture groups)</label>
              <input
                type="text"
                value={pattern}
                onChange={(e) => setPattern(e.target.value)}
                placeholder="([A-Z]+)\s+([\d.]+)\s+([\d.]+)"
                style={styles.input}
              />
              <div style={styles.hint}>
                Use parentheses () to define capture groups. Each group becomes a column.
              </div>
            </>
          )}

          {splitMethod === 'positions' && (
            <>
              <label style={styles.label}>Split at positions (comma-separated)</label>
              <input
                type="text"
                value={positions}
                onChange={(e) => setPositions(e.target.value)}
                placeholder="10, 20, 35, 50"
                style={styles.input}
              />
              <div style={styles.hint}>
                Character positions where to split. E.g., "10, 20" splits into 3 columns.
              </div>
            </>
          )}

          {splitMethod === 'delimiter' && (
            <>
              <label style={styles.label}>Delimiter</label>
              <input
                type="text"
                value={delimiter}
                onChange={(e) => setDelimiter(e.target.value)}
                placeholder="|  or  ,  or  tab"
                style={styles.input}
              />
              <div style={styles.hint}>
                Character(s) to split on. Use \t for tab.
              </div>
            </>
          )}
        </div>

        {/* New Column Headers */}
        <div style={styles.headersSection}>
          <div style={styles.headersTitle}>New Column Headers</div>
          <div style={styles.headerInputs}>
            {newHeaders.map((header, i) => (
              <input
                key={i}
                type="text"
                value={header}
                onChange={(e) => updateHeader(i, e.target.value)}
                placeholder={`Column ${i + 1}`}
                style={styles.headerInput}
              />
            ))}
          </div>
          <button 
            onClick={() => setNewHeaders([...newHeaders, `Column_${newHeaders.length + 1}`])}
            style={styles.addHeaderBtn}
          >
            + Add Column
          </button>
        </div>

        {/* Live Preview */}
        {preview.length > 0 && (
          <div style={styles.previewSection}>
            <div style={styles.previewTitle}>📊 Preview</div>
            <div style={styles.previewTable}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    {newHeaders.map((h, i) => (
                      <th key={i} style={styles.th}>{h || `Col ${i + 1}`}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.map((row, ri) => (
                    <tr key={ri}>
                      {(Array.isArray(row) ? row : [row]).map((cell, ci) => (
                        <td key={ci} style={styles.td}>{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={styles.error}>{error}</div>
        )}

        {/* Actions */}
        <div style={styles.actions}>
          <button onClick={onCancel} style={styles.cancelBtn}>
            Cancel
          </button>
          <button 
            onClick={executeSplit} 
            disabled={loading || !pattern}
            style={styles.applyBtn}
          >
            {loading ? 'Splitting...' : '✓ Apply Split'}
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
    maxWidth: '700px',
    maxHeight: '90vh',
    overflow: 'auto',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px',
    borderBottom: '1px solid #e5e7eb'
  },
  title: {
    margin: 0,
    fontSize: '20px',
    fontWeight: '600'
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '24px',
    cursor: 'pointer',
    color: '#6b7280'
  },
  infoBox: {
    padding: '16px 24px',
    backgroundColor: '#f9fafb',
    borderBottom: '1px solid #e5e7eb'
  },
  infoLabel: {
    fontSize: '12px',
    fontWeight: '500',
    color: '#6b7280',
    marginBottom: '4px'
  },
  infoValue: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#111827',
    marginBottom: '12px'
  },
  sampleList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px'
  },
  sampleItem: {
    fontSize: '12px',
    fontFamily: 'monospace',
    backgroundColor: '#fff',
    padding: '6px 10px',
    borderRadius: '4px',
    border: '1px solid #e5e7eb',
    wordBreak: 'break-all'
  },
  suggestionsBox: {
    padding: '16px 24px',
    borderBottom: '1px solid #e5e7eb'
  },
  suggestionsTitle: {
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '12px',
    color: '#374151'
  },
  suggestionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  },
  suggestionCard: {
    padding: '12px',
    backgroundColor: '#f9fafb',
    borderRadius: '8px',
    border: '2px solid #e5e7eb',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  sugDescription: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151'
  },
  sugHeaders: {
    fontSize: '12px',
    color: '#6b7280',
    marginTop: '4px'
  },
  rowMergeWarning: {
    fontSize: '11px',
    color: '#f59e0b',
    marginTop: '4px'
  },
  sugPreview: {
    fontSize: '11px',
    fontFamily: 'monospace',
    color: '#6b7280',
    marginTop: '4px'
  },
  methodSection: {
    padding: '16px 24px',
    borderBottom: '1px solid #e5e7eb'
  },
  methodTitle: {
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '12px',
    color: '#374151'
  },
  methodButtons: {
    display: 'flex',
    gap: '8px'
  },
  methodBtn: {
    flex: 1,
    padding: '10px 16px',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  inputSection: {
    padding: '16px 24px',
    borderBottom: '1px solid #e5e7eb'
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151',
    marginBottom: '6px'
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    fontFamily: 'monospace',
    boxSizing: 'border-box'
  },
  hint: {
    fontSize: '12px',
    color: '#6b7280',
    marginTop: '6px'
  },
  headersSection: {
    padding: '16px 24px',
    borderBottom: '1px solid #e5e7eb'
  },
  headersTitle: {
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '12px',
    color: '#374151'
  },
  headerInputs: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    marginBottom: '8px'
  },
  headerInput: {
    padding: '8px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '13px',
    width: '120px'
  },
  addHeaderBtn: {
    background: 'none',
    border: '1px dashed #d1d5db',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '12px',
    color: '#6b7280',
    cursor: 'pointer'
  },
  previewSection: {
    padding: '16px 24px',
    borderBottom: '1px solid #e5e7eb'
  },
  previewTitle: {
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '12px',
    color: '#374151'
  },
  previewTable: {
    overflowX: 'auto',
    border: '1px solid #e5e7eb',
    borderRadius: '6px'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '12px'
  },
  th: {
    textAlign: 'left',
    padding: '8px 12px',
    backgroundColor: '#f9fafb',
    borderBottom: '1px solid #e5e7eb',
    fontWeight: '600'
  },
  td: {
    padding: '8px 12px',
    borderBottom: '1px solid #f3f4f6',
    fontFamily: 'monospace'
  },
  error: {
    margin: '16px 24px',
    padding: '12px',
    backgroundColor: '#fef2f2',
    color: '#dc2626',
    borderRadius: '6px',
    fontSize: '13px'
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    padding: '16px 24px'
  },
  cancelBtn: {
    padding: '10px 20px',
    backgroundColor: '#f3f4f6',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer'
  },
  applyBtn: {
    padding: '10px 24px',
    backgroundColor: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer'
  }
};
