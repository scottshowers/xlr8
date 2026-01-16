/**
 * ExportPage.jsx - Step 8: Export
 * 
 * Final step in the 8-step consultant workflow.
 * Generate and download client-ready deliverables.
 * 
 * Flow: ... → Track Progress → [EXPORT]
 * 
 * Created: January 15, 2026 - Phase 4A UX Overhaul
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { useProject } from '../context/ProjectContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Export format options
const EXPORT_FORMATS = [
  {
    id: 'excel',
    name: 'Excel Workbook',
    description: 'Complete findings with all data in spreadsheet format',
    icon: '📊',
    extension: '.xlsx',
    recommended: true,
  },
  {
    id: 'pdf',
    name: 'PDF Report',
    description: 'Formatted executive summary for client presentation',
    icon: '📄',
    extension: '.pdf',
  },
  {
    id: 'powerpoint',
    name: 'PowerPoint Deck',
    description: 'Presentation-ready slides with key findings',
    icon: '📽️',
    extension: '.pptx',
  },
  {
    id: 'csv',
    name: 'CSV Data',
    description: 'Raw findings data for further analysis',
    icon: '📋',
    extension: '.csv',
  },
];

// Export content options
const CONTENT_OPTIONS = [
  { id: 'findings', label: 'All Findings', description: 'Complete list of identified issues', default: true },
  { id: 'recommendations', label: 'Recommendations', description: 'Suggested actions and remediation steps', default: true },
  { id: 'affected_records', label: 'Affected Records', description: 'Detailed list of impacted data', default: false },
  { id: 'provenance', label: 'Data Provenance', description: 'Source tables and detection methods', default: false },
  { id: 'progress', label: 'Progress Summary', description: 'Current remediation status', default: true },
  { id: 'executive_summary', label: 'Executive Summary', description: 'High-level overview for leadership', default: true },
];

const ExportPage = () => {
  const navigate = useNavigate();
  const { activeProject, customerName } = useProject();

  const [selectedFormat, setSelectedFormat] = useState('excel');
  const [selectedContent, setSelectedContent] = useState(
    new Set(CONTENT_OPTIONS.filter(o => o.default).map(o => o.id))
  );
  const [generating, setGenerating] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState(null);

  const toggleContent = (id) => {
    setSelectedContent(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setDownloadUrl(null);

    try {
      // Simulate export generation
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // In real implementation, call API:
      // const res = await fetch(`${API_BASE}/api/export`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({
      //     project_id: activeProject?.id,
      //     format: selectedFormat,
      //     content: Array.from(selectedContent),
      //   }),
      // });
      // const data = await res.json();
      // setDownloadUrl(data.download_url);

      // Mock download URL
      setDownloadUrl(`/exports/findings-report-${Date.now()}.${EXPORT_FORMATS.find(f => f.id === selectedFormat)?.extension || 'xlsx'}`);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    if (downloadUrl) {
      // Trigger download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${customerName || 'Project'}-Findings-Report${EXPORT_FORMATS.find(f => f.id === selectedFormat)?.extension || '.xlsx'}`;
      link.click();
    }
  };

  const selectedFormatConfig = EXPORT_FORMATS.find(f => f.id === selectedFormat);

  return (
    
      <div className="export-page">
        <PageHeader
          title="Export Report"
          subtitle={`Step 8 of 8 • Generate client-ready deliverables${customerName ? ` for ${customerName}` : ''}`}
        />

        <div className="export-page__content">
          {/* Main Content */}
          <div className="export-page__main">
            {/* Format Selection */}
            <Card className="export-page__format-card">
              <CardHeader>
                <CardTitle icon="📥">Export Format</CardTitle>
              </CardHeader>
              <div className="format-grid">
                {EXPORT_FORMATS.map(format => (
                  <button
                    key={format.id}
                    className={`format-option ${selectedFormat === format.id ? 'format-option--selected' : ''}`}
                    onClick={() => setSelectedFormat(format.id)}
                  >
                    <div className="format-icon">{format.icon}</div>
                    <div className="format-content">
                      <div className="format-name">
                        {format.name}
                        {format.recommended && <Badge variant="success" size="sm">Recommended</Badge>}
                      </div>
                      <div className="format-description">{format.description}</div>
                    </div>
                    <div className="format-check">
                      {selectedFormat === format.id ? '✓' : '○'}
                    </div>
                  </button>
                ))}
              </div>
            </Card>

            {/* Content Selection */}
            <Card className="export-page__content-card">
              <CardHeader>
                <CardTitle icon="📋">Include in Export</CardTitle>
              </CardHeader>
              <div className="content-options">
                {CONTENT_OPTIONS.map(option => (
                  <label key={option.id} className="content-option">
                    <input
                      type="checkbox"
                      checked={selectedContent.has(option.id)}
                      onChange={() => toggleContent(option.id)}
                    />
                    <div className="content-option-info">
                      <div className="content-option-label">{option.label}</div>
                      <div className="content-option-description">{option.description}</div>
                    </div>
                  </label>
                ))}
              </div>
            </Card>

            {/* Generate / Download */}
            <Card className="export-page__action-card">
              {!downloadUrl ? (
                <div className="export-action">
                  <div className="export-summary">
                    <div className="export-summary-icon">{selectedFormatConfig?.icon}</div>
                    <div className="export-summary-info">
                      <div className="export-summary-format">{selectedFormatConfig?.name}</div>
                      <div className="export-summary-content">
                        {selectedContent.size} sections selected
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="primary"
                    onClick={handleGenerate}
                    disabled={generating || selectedContent.size === 0}
                    className="export-btn"
                  >
                    {generating ? '⏳ Generating...' : '✨ Generate Export'}
                  </Button>
                </div>
              ) : (
                <div className="export-ready">
                  <div className="export-ready-icon">✅</div>
                  <div className="export-ready-info">
                    <div className="export-ready-title">Export Ready!</div>
                    <div className="export-ready-subtitle">Your report has been generated</div>
                  </div>
                  <div className="export-ready-actions">
                    <Button variant="primary" onClick={handleDownload}>
                      📥 Download {selectedFormatConfig?.extension}
                    </Button>
                    <Button variant="secondary" onClick={() => setDownloadUrl(null)}>
                      Generate Another
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          </div>

          {/* Sidebar */}
          <div className="export-page__sidebar">
            {/* Export History */}
            <Card className="export-page__history-card">
              <CardHeader>
                <CardTitle icon="📁">Recent Exports</CardTitle>
              </CardHeader>
              <div className="history-list">
                <div className="history-item">
                  <span className="history-icon">📊</span>
                  <div className="history-info">
                    <div className="history-name">Findings Report</div>
                    <div className="history-date">Jan 14, 2026 • Excel</div>
                  </div>
                </div>
                <div className="history-item">
                  <span className="history-icon">📄</span>
                  <div className="history-info">
                    <div className="history-name">Executive Summary</div>
                    <div className="history-date">Jan 12, 2026 • PDF</div>
                  </div>
                </div>
              </div>
            </Card>

            {/* Help Card */}
            <Card className="export-page__help-card">
              <CardHeader>
                <CardTitle icon="💡">Export Tips</CardTitle>
              </CardHeader>
              <ul className="help-list">
                <li><strong>Excel</strong> - Best for detailed analysis and data manipulation</li>
                <li><strong>PDF</strong> - Best for client presentations and formal documentation</li>
                <li><strong>PowerPoint</strong> - Best for steering committee meetings</li>
              </ul>
            </Card>

            {/* Complete Card */}
            <Card className="export-page__complete-card">
              <div className="complete-preview">
                <div className="complete-icon">🎉</div>
                <div className="complete-title">Workflow Complete!</div>
                <div className="complete-description">
                  You've completed the full analysis workflow. Export your deliverables and share with the client.
                </div>
                <Button variant="secondary" onClick={() => navigate('/mission-control')}>
                  ← Back to Mission Control
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    
  );
};

export default ExportPage;
