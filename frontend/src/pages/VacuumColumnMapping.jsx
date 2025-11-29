import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import ColumnSplitter from './ColumnSplitter';

const API_BASE = '/api';

// Section definitions with colors
const SECTIONS = [
  { id: 'employee_info', label: 'Employee Info', color: '#3b82f6', bgColor: '#eff6ff' },
  { id: 'earnings', label: 'Earnings', color: '#22c55e', bgColor: '#f0fdf4' },
  { id: 'taxes', label: 'Taxes', color: '#ef4444', bgColor: '#fef2f2' },
  { id: 'deductions', label: 'Deductions', color: '#f97316', bgColor: '#fff7ed' },
  { id: 'pay_info', label: 'Pay Info', color: '#8b5cf6', bgColor: '#f5f3ff' }
];

// Target fields by section
const TARGET_FIELDS = {
  employee_info: [
    'employee_id', 'employee_name', 'first_name', 'last_name', 'ssn',
    'department', 'location', 'job_title', 'hire_date', 'term_date', 'pay_rate'
  ],
  earnings: [
    'earning_code', 'earning_description', 'hours_current', 'hours_ytd',
    'rate', 'amount_current', 'amount_ytd'
  ],
  taxes: [
    'tax_code', 'tax_description', 'taxable_wages',
    'tax_amount_current', 'tax_amount_ytd', 'tax_er_current', 'tax_er_ytd'
  ],
  deductions: [
    'deduction_code', 'deduction_description',
    'deduction_ee_current', 'deduction_ee_ytd', 'deduction_er_current', 'deduction_er_ytd'
  ],
  pay_info: [
    'gross_pay', 'net_pay', 'total_taxes', 'total_deductions',
    'check_number', 'direct_deposit'
  ]
};

export default function VacuumColumnMapping() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const sourceFile = searchParams.get('file');

  // State
  const [extracts, setExtracts] = useState([]);
  const [activeSection, setActiveSection] = useState('employee_info');
  const [headerMetadata, setHeaderMetadata] = useState({
    company: '',
    pay_period_start: '',
    pay_period_end: '',
    check_date: ''
  });
  const [mappings, setMappings] = useState({});
  const [confirmedSections, setConfirmedSections] = useState({});
  const [rememberMapping, setRememberMapping] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  const [showSplitter, setShowSplitter] = useState(false);
  const [splitColumnInfo, setSplitColumnInfo] = useState(null);

  // Check if a cell looks merged (multiple values)
  const looksLikeMergedColumn = (headerStr, sampleData, colIdx) => {
    if (!sampleData || sampleData.length === 0) return false;
    
    // Check sample values for patterns suggesting merged data
    const values = sampleData.slice(0, 5).map(row => String(row[colIdx] || ''));
    
    for (const val of values) {
      // Multiple numbers with text between them
      const hasMultipleNumbers = (val.match(/\d+\.?\d*/g) || []).length >= 3;
      // Has code-like patterns followed by numbers
      const hasCodePattern = /[A-Z]{2,}\s+\d+\.?\d*\s+[A-Z]/i.test(val);
      // Very long for what should be a simple field
      const isTooLong = val.length > 40;
      
      if ((hasMultipleNumbers && isTooLong) || hasCodePattern) {
        return true;
      }
    }
    return false;
  };

  // Open column splitter
  const openSplitter = (headerStr, colIdx) => {
    const sampleData = getSampleData();
    const sampleValues = sampleData.slice(0, 10).map(row => String(row[colIdx] || ''));
    
    setSplitColumnInfo({
      extractId: currentExtract?.id,
      columnIndex: colIdx,
      columnHeader: headerStr,
      sampleValues: sampleValues,
      sectionType: activeSection
    });
    setShowSplitter(true);
  };

  // Handle split completion
  const handleSplitComplete = (result) => {
    setShowSplitter(false);
    setSplitColumnInfo(null);
    // Reload extracts to get updated data
    window.location.reload();
  };

  // Load extracts and header metadata
  useEffect(() => {
    if (!sourceFile) return;

    const loadData = async () => {
      setLoading(true);
      try {
        // Load extracts
        const extractsRes = await fetch(`${API_BASE}/vacuum/extracts?source_file=${encodeURIComponent(sourceFile)}`);
        const extractsData = await extractsRes.json();
        setExtracts(extractsData.extracts || []);

        // Load header metadata
        const metaRes = await fetch(`${API_BASE}/vacuum/header-metadata?source_file=${encodeURIComponent(sourceFile)}`);
        const metaData = await metaRes.json();
        if (metaData && !metaData.error) {
          setHeaderMetadata({
            company: metaData.company || '',
            pay_period_start: metaData.pay_period_start || '',
            pay_period_end: metaData.pay_period_end || '',
            check_date: metaData.check_date || ''
          });
        }
      } catch (err) {
        console.error('Error loading data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [sourceFile]);

  // Auto-select first section that has data
  useEffect(() => {
    if (extracts.length > 0) {
      const sectionOrder = ['employee_info', 'earnings', 'taxes', 'deductions', 'pay_info'];
      for (const section of sectionOrder) {
        const hasData = extracts.some(e => e.detected_section === section);
        if (hasData) {
          setActiveSection(section);
          break;
        }
      }
    }
  }, [extracts]);

  // Initialize mappings from column_classifications
  useEffect(() => {
    const newMappings = {};
    
    extracts.forEach(extract => {
      if (extract.detected_section && extract.column_classifications) {
        const sectionKey = extract.detected_section;
        if (!newMappings[sectionKey]) {
          newMappings[sectionKey] = {};
        }
        
        extract.column_classifications.forEach((col, idx) => {
          const header = extract.raw_headers?.[idx] || `Column ${idx}`;
          if (!newMappings[sectionKey][header]) {
            newMappings[sectionKey][header] = {
              targetField: col.type || '',
              confidence: col.confidence || 0,
              confirmed: false,
              columnIndex: idx
            };
          }
        });
      }
    });
    
    setMappings(newMappings);
  }, [extracts]);

  // Get extract for current section
  const getExtractForSection = (sectionId) => {
    // First try exact match
    const exactMatch = extracts.find(e => e.detected_section === sectionId);
    if (exactMatch) return exactMatch;
    
    return null;
  };

  const currentExtract = getExtractForSection(activeSection);
  const currentSection = SECTIONS.find(s => s.id === activeSection);
  const currentMappings = mappings[activeSection] || {};

  // Get sample data for preview
  const getSampleData = () => {
    if (!currentExtract) return [];
    return currentExtract.preview || currentExtract.raw_data || currentExtract.sample_data || [];
  };

  // Update a mapping
  const updateMapping = (header, targetField) => {
    setMappings(prev => ({
      ...prev,
      [activeSection]: {
        ...prev[activeSection],
        [header]: {
          ...prev[activeSection]?.[header],
          targetField,
          confirmed: true
        }
      }
    }));
  };

  // Confirm a single mapping
  const confirmMapping = (header) => {
    setMappings(prev => ({
      ...prev,
      [activeSection]: {
        ...prev[activeSection],
        [header]: {
          ...prev[activeSection]?.[header],
          confirmed: true
        }
      }
    }));
  };

  // Confirm all high-confidence mappings
  const confirmAllHigh = () => {
    setMappings(prev => {
      const updated = { ...prev[activeSection] };
      Object.keys(updated).forEach(header => {
        if (updated[header].confidence >= 0.7) {
          updated[header] = { ...updated[header], confirmed: true };
        }
      });
      return { ...prev, [activeSection]: updated };
    });
  };

  // Confirm entire section
  const confirmSection = () => {
    // Mark all mappings in section as confirmed
    setMappings(prev => {
      const updated = { ...prev[activeSection] };
      Object.keys(updated).forEach(header => {
        updated[header] = { ...updated[header], confirmed: true };
      });
      return { ...prev, [activeSection]: updated };
    });
    
    // Mark section as done
    setConfirmedSections(prev => ({ ...prev, [activeSection]: true }));
    
    // Move to next section
    const currentIdx = SECTIONS.findIndex(s => s.id === activeSection);
    if (currentIdx < SECTIONS.length - 1) {
      setActiveSection(SECTIONS[currentIdx + 1].id);
    }
  };

  // Save all mappings
  const saveAllMappings = async () => {
    setSaving(true);
    try {
      const sectionMappings = {};
      
      Object.keys(mappings).forEach(sectionId => {
        const sectionMap = mappings[sectionId];
        const columnMap = {};
        
        Object.keys(sectionMap).forEach(header => {
          const mapping = sectionMap[header];
          if (mapping.targetField && mapping.confirmed) {
            columnMap[mapping.columnIndex] = mapping.targetField;
          }
        });
        
        if (Object.keys(columnMap).length > 0) {
          sectionMappings[sectionId] = columnMap;
        }
      });

      const response = await fetch(`${API_BASE}/vacuum/apply-mappings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_file: sourceFile,
          header_metadata: headerMetadata,
          section_mappings: sectionMappings,
          remember_for_vendor: rememberMapping
        })
      });

      const result = await response.json();
      if (result.success) {
        alert('Mappings saved successfully!');
      } else {
        alert('Error saving mappings: ' + (result.error || 'Unknown error'));
      }
    } catch (err) {
      console.error('Error saving mappings:', err);
      alert('Error saving mappings: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  // Get confidence color
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.7) return '#22c55e';
    if (confidence >= 0.4) return '#eab308';
    return '#9ca3af';
  };

  // Count sections with data
  const getSectionStats = (sectionId) => {
    const sectionExtracts = extracts.filter(e => e.detected_section === sectionId);
    const rowCount = sectionExtracts.reduce((sum, e) => sum + (e.row_count || 0), 0);
    const colCount = sectionExtracts[0]?.column_count || 0;
    return { rowCount, colCount, hasData: sectionExtracts.length > 0 };
  };

  if (!sourceFile) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <h2>No file selected</h2>
        <button onClick={() => navigate('/vacuum')} style={styles.btn}>
          ← Back to Upload
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={styles.spinner}></div>
        <p>Loading extracts...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <button onClick={() => navigate('/vacuum/explore?file=' + encodeURIComponent(sourceFile))} style={styles.backBtn}>
            ← Back to Explore
          </button>
          <h1 style={styles.title}>Column Mapping</h1>
          <p style={styles.subtitle}>{sourceFile}</p>
        </div>
      </div>

      <div style={styles.mainContent}>
        {/* Left Panel - Sections */}
        <div style={styles.leftPanel}>
          {/* Header Metadata */}
          <div style={styles.metadataCard}>
            <h3 style={styles.metadataTitle}>📋 Header Metadata</h3>
            <div style={styles.metadataFields}>
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Company</label>
                <input
                  type="text"
                  value={headerMetadata.company}
                  onChange={(e) => setHeaderMetadata(prev => ({ ...prev, company: e.target.value }))}
                  style={styles.input}
                  placeholder="Company name"
                />
              </div>
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Pay Period Start</label>
                <input
                  type="text"
                  value={headerMetadata.pay_period_start}
                  onChange={(e) => setHeaderMetadata(prev => ({ ...prev, pay_period_start: e.target.value }))}
                  style={styles.input}
                  placeholder="MM/DD/YYYY"
                />
              </div>
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Pay Period End</label>
                <input
                  type="text"
                  value={headerMetadata.pay_period_end}
                  onChange={(e) => setHeaderMetadata(prev => ({ ...prev, pay_period_end: e.target.value }))}
                  style={styles.input}
                  placeholder="MM/DD/YYYY"
                />
              </div>
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Check Date</label>
                <input
                  type="text"
                  value={headerMetadata.check_date}
                  onChange={(e) => setHeaderMetadata(prev => ({ ...prev, check_date: e.target.value }))}
                  style={styles.input}
                  placeholder="MM/DD/YYYY"
                />
              </div>
            </div>
          </div>

          {/* Section Cards */}
          <div style={styles.sectionList}>
            {SECTIONS.map((section) => {
              const stats = getSectionStats(section.id);
              const isActive = activeSection === section.id;
              const isConfirmed = confirmedSections[section.id];
              
              return (
                <div
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  style={{
                    ...styles.sectionCard,
                    borderLeft: `4px solid ${section.color}`,
                    backgroundColor: isActive ? section.bgColor : '#fff',
                    opacity: stats.hasData ? 1 : 0.5
                  }}
                >
                  <div style={styles.sectionHeader}>
                    <span style={{ ...styles.sectionLabel, color: section.color }}>
                      {isConfirmed && '✓ '}{section.label}
                    </span>
                    {!stats.hasData && (
                      <span style={styles.noDataBadge}>No Data</span>
                    )}
                  </div>
                  {stats.hasData && (
                    <div style={styles.sectionStats}>
                      {stats.rowCount} rows • {stats.colCount} columns
                    </div>
                  )}
                  {stats.hasData && currentExtract && isActive && (
                    <div style={styles.headerPreview}>
                      {(currentExtract.raw_headers || []).slice(0, 3).map((h, i) => (
                        <span key={i} style={styles.headerChip}>
                          {String(h).substring(0, 20)}{String(h).length > 20 ? '...' : ''}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Panel - Mapping Interface */}
        <div style={styles.rightPanel}>
          {!currentExtract ? (
            /* Empty Section State */
            <div style={styles.emptySection}>
              <div style={styles.emptyIcon}>📋</div>
              <h3 style={styles.emptyTitle}>No Data Detected for {currentSection?.label}</h3>
              <p style={styles.emptyText}>
                This section wasn't automatically detected in the PDF.<br/>
                You can manually assign an extract from the Explore page.
              </p>
              <button 
                onClick={() => navigate('/vacuum/explore?file=' + encodeURIComponent(sourceFile))}
                style={styles.exploreBtn}
              >
                Go to Explore →
              </button>
            </div>
          ) : (
            <>
              {/* Section Title */}
              <div style={styles.rightHeader}>
                <h2 style={{ ...styles.rightTitle, color: currentSection?.color }}>
                  {currentSection?.label}
                </h2>
                <span style={styles.rowBadge}>{currentExtract.row_count} rows</span>
                <div style={styles.rightActions}>
                  <button onClick={confirmAllHigh} style={styles.confirmHighBtn}>
                    ✓ Confirm All High
                  </button>
                </div>
              </div>

              {/* Mapping Cards */}
              <div style={styles.mappingGrid}>
                {(currentExtract.raw_headers || []).map((header, idx) => {
                  const headerStr = String(header);
                  const mapping = currentMappings[headerStr] || {};
                  const classification = currentExtract.column_classifications?.[idx] || {};
                  
                  return (
                    <div key={idx} style={{
                      ...styles.mappingCard,
                      borderColor: mapping.confirmed ? '#22c55e' : '#e5e7eb'
                    }}>
                      {/* Source Column */}
                      <div style={styles.sourceColumn}>
                        <div style={styles.sourceLabel}>Source Column</div>
                        <div style={styles.sourceHeader}>
                          {headerStr.substring(0, 50)}{headerStr.length > 50 ? '...' : ''}
                        </div>
                        {/* Sample values */}
                        <div style={styles.sampleValues}>
                          {getSampleData().slice(0, 3).map((row, ri) => (
                            <span key={ri} style={styles.sampleValue}>
                              {String(row[idx] || '').substring(0, 25)}
                            </span>
                          ))}
                        </div>
                        {/* Merged column warning and split button */}
                        {looksLikeMergedColumn(headerStr, getSampleData(), idx) && (
                          <div style={styles.mergedWarning}>
                            <span style={styles.warningIcon}>⚠️</span>
                            <span>Looks merged</span>
                            <button 
                              onClick={() => openSplitter(headerStr, idx)}
                              style={styles.splitBtn}
                            >
                              Split Column
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Arrow */}
                      <div style={styles.arrow}>→</div>

                      {/* Target Field */}
                      <div style={styles.targetColumn}>
                        <div style={styles.targetLabel}>
                          Target Field
                          <span style={{
                            ...styles.confidenceDot,
                            backgroundColor: getConfidenceColor(classification.confidence || 0)
                          }} title={`Confidence: ${Math.round((classification.confidence || 0) * 100)}%`}></span>
                        </div>
                        <select
                          value={mapping.targetField || classification.type || ''}
                          onChange={(e) => updateMapping(headerStr, e.target.value)}
                          style={styles.select}
                        >
                          <option value="">-- Skip --</option>
                          {TARGET_FIELDS[activeSection]?.map(field => (
                            <option key={field} value={field}>{field}</option>
                          ))}
                        </select>
                        {!mapping.confirmed && (
                          <button
                            onClick={() => confirmMapping(headerStr)}
                            style={styles.confirmBtn}
                          >
                            Confirm
                          </button>
                        )}
                        {mapping.confirmed && (
                          <span style={styles.confirmedBadge}>✓ Confirmed</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Live Preview */}
              <div style={styles.previewSection}>
                <div 
                  style={styles.previewHeader}
                  onClick={() => setShowPreview(!showPreview)}
                >
                  <span>📊 Live Preview</span>
                  <span>{showPreview ? '▼' : '▶'}</span>
                </div>
                {showPreview && (
                  <div style={styles.previewTable}>
                    <table style={styles.table}>
                      <thead>
                        <tr>
                          {(currentExtract.raw_headers || []).map((h, i) => {
                            const mapping = currentMappings[String(h)] || {};
                            const targetField = mapping.targetField || currentExtract.column_classifications?.[i]?.type || '';
                            return (
                              <th key={i} style={styles.th}>
                                {targetField || `Col ${i}`}
                              </th>
                            );
                          })}
                        </tr>
                      </thead>
                      <tbody>
                        {getSampleData().slice(0, 5).map((row, ri) => (
                          <tr key={ri}>
                            {(Array.isArray(row) ? row : []).map((cell, ci) => (
                              <td key={ci} style={styles.td}>
                                {String(cell || '').substring(0, 30)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Confirm Section Button */}
              <div style={styles.sectionActions}>
                <button onClick={confirmSection} style={styles.confirmSectionBtn}>
                  Confirm Section & Continue →
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        <div style={styles.progressDots}>
          {SECTIONS.map((section, idx) => {
            const stats = getSectionStats(section.id);
            const isConfirmed = confirmedSections[section.id];
            const isActive = activeSection === section.id;
            return (
              <span
                key={section.id}
                style={{
                  ...styles.dot,
                  backgroundColor: isConfirmed ? '#22c55e' : isActive ? section.color : (stats.hasData ? '#e5e7eb' : '#f3f4f6'),
                  border: isActive ? `2px solid ${section.color}` : 'none'
                }}
                title={section.label}
              >
                {isConfirmed ? '✓' : ''}
              </span>
            );
          })}
        </div>
        <label style={styles.rememberLabel}>
          <input
            type="checkbox"
            checked={rememberMapping}
            onChange={(e) => setRememberMapping(e.target.checked)}
          />
          Remember mapping for similar files
        </label>
        <button
          onClick={saveAllMappings}
          disabled={saving}
          style={styles.saveBtn}
        >
          {saving ? 'Saving...' : '💾 Save All Mappings'}
        </button>
      </div>

      {/* Column Splitter Modal */}
      {showSplitter && splitColumnInfo && (
        <ColumnSplitter
          extractId={splitColumnInfo.extractId}
          columnIndex={splitColumnInfo.columnIndex}
          columnHeader={splitColumnInfo.columnHeader}
          sampleValues={splitColumnInfo.sampleValues}
          sectionType={splitColumnInfo.sectionType}
          onSplitComplete={handleSplitComplete}
          onCancel={() => setShowSplitter(false)}
        />
      )}
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    backgroundColor: '#f8fafc'
  },
  header: {
    padding: '16px 24px',
    backgroundColor: '#fff',
    borderBottom: '1px solid #e5e7eb',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  backBtn: {
    background: 'none',
    border: 'none',
    color: '#6b7280',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '4px 0',
    marginBottom: '4px'
  },
  title: {
    margin: 0,
    fontSize: '24px',
    fontWeight: '600',
    color: '#111827'
  },
  subtitle: {
    margin: '4px 0 0',
    fontSize: '14px',
    color: '#6b7280'
  },
  mainContent: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden'
  },
  leftPanel: {
    width: '320px',
    backgroundColor: '#fff',
    borderRight: '1px solid #e5e7eb',
    overflowY: 'auto',
    padding: '16px'
  },
  metadataCard: {
    backgroundColor: '#f9fafb',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '16px'
  },
  metadataTitle: {
    margin: '0 0 12px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151'
  },
  metadataFields: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px'
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px'
  },
  label: {
    fontSize: '12px',
    fontWeight: '500',
    color: '#6b7280'
  },
  input: {
    padding: '8px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px'
  },
  sectionList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  },
  sectionCard: {
    padding: '12px',
    borderRadius: '8px',
    border: '1px solid #e5e7eb',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  sectionLabel: {
    fontWeight: '600',
    fontSize: '14px'
  },
  noDataBadge: {
    fontSize: '10px',
    padding: '2px 6px',
    backgroundColor: '#f3f4f6',
    borderRadius: '4px',
    color: '#9ca3af'
  },
  sectionStats: {
    fontSize: '12px',
    color: '#6b7280',
    marginTop: '4px'
  },
  headerPreview: {
    marginTop: '8px',
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px'
  },
  headerChip: {
    fontSize: '10px',
    padding: '2px 6px',
    backgroundColor: '#f3f4f6',
    borderRadius: '4px',
    color: '#6b7280'
  },
  rightPanel: {
    flex: 1,
    overflowY: 'auto',
    padding: '24px'
  },
  emptySection: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 40px',
    backgroundColor: '#fff',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
    textAlign: 'center'
  },
  emptyIcon: {
    fontSize: '64px',
    marginBottom: '16px'
  },
  emptyTitle: {
    margin: '0 0 8px',
    fontSize: '20px',
    fontWeight: '600',
    color: '#374151'
  },
  emptyText: {
    margin: '0 0 24px',
    fontSize: '14px',
    color: '#6b7280',
    lineHeight: '1.5'
  },
  exploreBtn: {
    padding: '10px 20px',
    backgroundColor: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  rightHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '20px'
  },
  rightTitle: {
    margin: 0,
    fontSize: '20px',
    fontWeight: '600'
  },
  rowBadge: {
    padding: '4px 10px',
    backgroundColor: '#f3f4f6',
    borderRadius: '12px',
    fontSize: '12px',
    color: '#6b7280'
  },
  rightActions: {
    marginLeft: 'auto'
  },
  confirmHighBtn: {
    padding: '8px 16px',
    backgroundColor: '#22c55e',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  mappingGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px'
  },
  mappingCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px',
    backgroundColor: '#fff',
    borderRadius: '8px',
    border: '2px solid #e5e7eb'
  },
  sourceColumn: {
    flex: 1
  },
  sourceLabel: {
    fontSize: '11px',
    fontWeight: '500',
    color: '#9ca3af',
    textTransform: 'uppercase',
    marginBottom: '4px'
  },
  sourceHeader: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#374151',
    wordBreak: 'break-word'
  },
  sampleValues: {
    marginTop: '8px',
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px'
  },
  sampleValue: {
    fontSize: '11px',
    padding: '2px 6px',
    backgroundColor: '#f9fafb',
    borderRadius: '4px',
    color: '#6b7280',
    maxWidth: '150px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },
  mergedWarning: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginTop: '8px',
    padding: '6px 10px',
    backgroundColor: '#fef3c7',
    borderRadius: '4px',
    fontSize: '12px',
    color: '#92400e'
  },
  warningIcon: {
    fontSize: '14px'
  },
  splitBtn: {
    marginLeft: 'auto',
    padding: '4px 10px',
    backgroundColor: '#f59e0b',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  arrow: {
    fontSize: '20px',
    color: '#9ca3af'
  },
  targetColumn: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  },
  targetLabel: {
    fontSize: '11px',
    fontWeight: '500',
    color: '#9ca3af',
    textTransform: 'uppercase',
    display: 'flex',
    alignItems: 'center',
    gap: '6px'
  },
  confidenceDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    display: 'inline-block'
  },
  select: {
    padding: '8px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    backgroundColor: '#fff'
  },
  confirmBtn: {
    padding: '6px 12px',
    backgroundColor: '#f3f4f6',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
    alignSelf: 'flex-start'
  },
  confirmedBadge: {
    fontSize: '12px',
    color: '#22c55e',
    fontWeight: '500'
  },
  previewSection: {
    marginTop: '24px',
    backgroundColor: '#fff',
    borderRadius: '8px',
    border: '1px solid #e5e7eb',
    overflow: 'hidden'
  },
  previewHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    backgroundColor: '#f9fafb',
    cursor: 'pointer',
    fontWeight: '500',
    fontSize: '14px'
  },
  previewTable: {
    overflowX: 'auto',
    padding: '16px'
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
    fontWeight: '600',
    whiteSpace: 'nowrap'
  },
  td: {
    padding: '8px 12px',
    borderBottom: '1px solid #f3f4f6',
    maxWidth: '200px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },
  sectionActions: {
    marginTop: '24px',
    display: 'flex',
    justifyContent: 'flex-end'
  },
  confirmSectionBtn: {
    padding: '12px 24px',
    backgroundColor: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer'
  },
  footer: {
    padding: '16px 24px',
    backgroundColor: '#fff',
    borderTop: '1px solid #e5e7eb',
    display: 'flex',
    alignItems: 'center',
    gap: '24px'
  },
  progressDots: {
    display: 'flex',
    gap: '8px'
  },
  dot: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    color: '#fff',
    fontWeight: '600'
  },
  rememberLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    color: '#6b7280',
    cursor: 'pointer'
  },
  saveBtn: {
    marginLeft: 'auto',
    padding: '12px 24px',
    backgroundColor: '#22c55e',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer'
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '4px solid #f3f4f6',
    borderTop: '4px solid #3b82f6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 16px'
  },
  btn: {
    padding: '10px 20px',
    backgroundColor: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer'
  }
};
