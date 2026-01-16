/**
 * ExportPage.jsx - Step 8: Export
 * 
 * Export findings and reports.
 * Uses design system classes - NO emojis.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, Table, FileSpreadsheet, Download, Check, Loader2 } from 'lucide-react';
import { useProject } from '../context/ProjectContext';

const EXPORT_OPTIONS = [
  { id: 'pdf', name: 'Executive Summary (PDF)', desc: 'High-level findings for stakeholders', Icon: FileText },
  { id: 'xlsx', name: 'Full Report (Excel)', desc: 'Detailed findings with affected records', Icon: FileSpreadsheet },
  { id: 'csv', name: 'Raw Data (CSV)', desc: 'All findings data for further analysis', Icon: Table },
];

const ExportPage = () => {
  const navigate = useNavigate();
  const { activeProject } = useProject();
  const [selectedFormat, setSelectedFormat] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exported, setExported] = useState(false);

  const handleExport = async () => {
    if (!selectedFormat) return;
    setExporting(true);
    // Simulate export
    await new Promise(r => setTimeout(r, 2000));
    setExporting(false);
    setExported(true);
  };

  return (
    <div className="export-page">
      <button className="btn btn-secondary mb-4" onClick={() => navigate('/findings')}>
        <ArrowLeft size={16} />
        Back to Findings
      </button>

      <div className="page-header">
        <h1 className="page-title">Export Report</h1>
        <p className="page-subtitle">{activeProject?.customer || 'Project'} - Final deliverables</p>
      </div>

      {/* Export Options */}
      <div className="card mb-6">
        <div className="card-header">
          <h3 className="card-title">Select Export Format</h3>
        </div>
        <div className="card-body">
          <div className="export-options">
            {EXPORT_OPTIONS.map(option => {
              const isSelected = selectedFormat === option.id;
              return (
                <div
                  key={option.id}
                  className={`export-option ${isSelected ? 'export-option--selected' : ''}`}
                  onClick={() => { setSelectedFormat(option.id); setExported(false); }}
                >
                  <div className="export-option__icon">
                    <option.Icon size={24} />
                  </div>
                  <div className="export-option__content">
                    <div className="export-option__name">{option.name}</div>
                    <div className="export-option__desc">{option.desc}</div>
                  </div>
                  <div className="export-option__check">
                    {isSelected && <Check size={16} />}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Export Button */}
      <div className="flex gap-4">
        <button
          className="btn btn-primary btn-lg"
          onClick={handleExport}
          disabled={!selectedFormat || exporting}
        >
          {exporting ? (
            <>
              <Loader2 size={18} className="spin" />
              Generating...
            </>
          ) : exported ? (
            <>
              <Check size={18} />
              Download Ready
            </>
          ) : (
            <>
              <Download size={18} />
              Generate Export
            </>
          )}
        </button>
      </div>

      {exported && (
        <div className="alert alert--info mt-4">
          <Check size={16} />
          Your export is ready! Click the button above to download.
        </div>
      )}

      {/* Summary */}
      <div className="card mt-6">
        <div className="card-header">
          <h3 className="card-title">Export Summary</h3>
        </div>
        <div className="card-body">
          <div className="flex gap-6">
            <div className="finding-stat">
              <div className="finding-stat__value">32</div>
              <div className="finding-stat__label">Total Findings</div>
            </div>
            <div className="finding-stat">
              <div className="finding-stat__value finding-stat__value--critical">8</div>
              <div className="finding-stat__label">Critical</div>
            </div>
            <div className="finding-stat">
              <div className="finding-stat__value finding-stat__value--warning">12</div>
              <div className="finding-stat__label">Warning</div>
            </div>
            <div className="finding-stat">
              <div className="finding-stat__value finding-stat__value--info">12</div>
              <div className="finding-stat__label">Info</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExportPage;
