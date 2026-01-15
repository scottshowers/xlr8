/**
 * VacuumUploadPage - Pay Register Extraction
 * Theme-aware with muted professional colors
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Upload, FileText, Users, DollarSign, CheckCircle, XCircle, 
  Loader2, Trash2, Eye, AlertTriangle, ChevronDown, ChevronRight,
  Shield, Cloud, Lock, Download, BarChart3, Wand2,
  Maximize2, Minimize2
} from 'lucide-react';
import * as XLSX from 'xlsx';
import ConsultantAssist from '../components/ConsultantAssist';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import { getCustomerColorPalette } from '../utils/customerColors';
import { PageHeader, Tooltip } from '../components/ui';

const API_BASE = import.meta.env.VITE_API_URL || '';

const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f5f7fa',
  card: dark ? '#242b3d' : '#ffffff',
  cardBorder: dark ? '#2d3548' : '#e8ecf1',
  text: dark ? '#e8eaed' : '#2a3441',
  textMuted: dark ? '#8b95a5' : '#6b7280',
  textLight: dark ? '#5f6a7d' : '#9ca3af',
  primary: '#83b16d',
  primaryHover: '#6b9b5a',
  primaryLight: dark ? 'rgba(90, 138, 74, 0.15)' : 'rgba(90, 138, 74, 0.1)',
  blue: '#285390',
  blueLight: dark ? 'rgba(74, 107, 138, 0.15)' : 'rgba(74, 107, 138, 0.1)',
  amber: '#d97706',
  amberLight: dark ? 'rgba(138, 107, 74, 0.15)' : 'rgba(138, 107, 74, 0.1)',
  red: '#993c44',
  redLight: dark ? 'rgba(138, 74, 74, 0.15)' : 'rgba(138, 74, 74, 0.1)',
  green: '#5a8a5a',
  greenLight: dark ? 'rgba(90, 138, 90, 0.15)' : 'rgba(90, 138, 90, 0.1)',
  divider: dark ? '#2d3548' : '#e8ecf1',
  inputBg: dark ? '#1a1f2e' : '#f8fafc',
  tableHeader: dark ? '#1e2433' : '#f9fafb',
  tableHover: dark ? 'rgba(90, 138, 74, 0.08)' : 'rgba(90, 138, 74, 0.05)',
});

export default function VacuumUploadPage() {
  const { activeProject } = useProject();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [extracts, setExtracts] = useState([]);
  const [selectedExtract, setSelectedExtract] = useState(null);
  const [error, setError] = useState(null);
  const [maxPages, setMaxPages] = useState(0);
  const [useTextract, setUseTextract] = useState(false);
  const [vendorType, setVendorType] = useState('unknown');
  const [activeTab, setActiveTab] = useState('employees');
  const [historyTab, setHistoryTab] = useState('employees');
  const [expandedDetails, setExpandedDetails] = useState(false);
  const [showAssist, setShowAssist] = useState(false);
  
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const pollIntervalRef = useRef(null);

  const loadExtracts = useCallback(async () => {
    try {
      const url = activeProject?.id 
        ? `${API_BASE}/api/vacuum/extracts?project_id=${activeProject.id}`
        : `${API_BASE}/api/vacuum/extracts`;
      const res = await fetch(url);
      const data = await res.json();
      setExtracts(data.extracts || []);
    } catch (err) {
      console.error('Failed to load extracts:', err);
    }
  }, [activeProject?.id]);

  useEffect(() => { loadExtracts(); }, [loadExtracts]);

  const pollJobStatus = useCallback(async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/job/${id}`);
      if (!res.ok) throw new Error('Job not found');
      const data = await res.json();
      setJobStatus(data);
      
      if (data.status === 'completed') {
        clearInterval(pollIntervalRef.current);
        setUploading(false);
        setJobId(null);
        if (data.result) { setResult(data.result); loadExtracts(); }
      } else if (data.status === 'failed') {
        clearInterval(pollIntervalRef.current);
        setUploading(false);
        setJobId(null);
        setError(data.message || 'Extraction failed');
      }
    } catch (err) { console.error('Poll failed:', err); }
  }, [loadExtracts]);

  useEffect(() => {
    if (jobId) {
      pollIntervalRef.current = setInterval(() => pollJobStatus(jobId), 1000);
      return () => clearInterval(pollIntervalRef.current);
    }
  }, [jobId, pollJobStatus]);

  const handleUpload = async () => {
    if (!file) { setError('Please select a file'); return; }
    if (!activeProject) { setError('Please select a project from the header'); return; }
    
    setUploading(true); setError(null); setResult(null); setJobStatus(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('max_pages', maxPages.toString());
      formData.append('project_id', activeProject.id);
      formData.append('use_textract', useTextract.toString());
      formData.append('vendor_type', vendorType);
      formData.append('async_mode', 'true');
      
      const res = await fetch(`${API_BASE}/api/vacuum/upload`, { method: 'POST', body: formData });
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      
      if (data.job_id) {
        setJobId(data.job_id);
        setJobStatus({ status: 'processing', progress: 0, message: 'Starting...' });
      } else {
        setResult(data); setUploading(false); loadExtracts();
      }
    } catch (err) { setError(err.message); setUploading(false); }
  };

  const viewExtract = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/extract/${id}`);
      const data = await res.json();
      setSelectedExtract(data);
    } catch (err) { console.error('Failed to load extract:', err); }
  };

  const deleteExtract = async (id) => {
    if (!confirm('Delete this extraction?')) return;
    try {
      await fetch(`${API_BASE}/api/vacuum/extract/${id}`, { method: 'DELETE' });
      loadExtracts();
      if (selectedExtract?.id === id) setSelectedExtract(null);
    } catch (err) { console.error('Failed to delete:', err); }
  };

  const calculateSummary = (employees) => {
    if (!employees?.length) return { earnings: [], taxes: [], deductions: [], totals: { grossPay: 0, netPay: 0, totalTaxes: 0, totalDeductions: 0 } };
    
    const earningsMap = new Map();
    const taxesMap = new Map();
    const deductionsMap = new Map();
    
    employees.forEach(emp => {
      (emp.earnings || []).forEach(e => {
        const key = e.type || e.description || 'Other';
        const existing = earningsMap.get(key) || { total: 0, count: 0 };
        earningsMap.set(key, { total: existing.total + (e.amount || 0), count: existing.count + 1 });
      });
      (emp.taxes || []).forEach(t => {
        const key = t.type || t.description || 'Other';
        const existing = taxesMap.get(key) || { total: 0, count: 0 };
        taxesMap.set(key, { total: existing.total + (t.amount || 0), count: existing.count + 1 });
      });
      (emp.deductions || []).forEach(d => {
        const key = d.type || d.description || 'Other';
        const existing = deductionsMap.get(key) || { total: 0, count: 0 };
        deductionsMap.set(key, { total: existing.total + (d.amount || 0), count: existing.count + 1 });
      });
    });
    
    const mapToArray = (map) => Array.from(map.entries()).map(([description, data]) => ({ description, ...data })).sort((a, b) => b.total - a.total);
    
    return {
      earnings: mapToArray(earningsMap),
      taxes: mapToArray(taxesMap),
      deductions: mapToArray(deductionsMap),
      totals: {
        grossPay: employees.reduce((sum, e) => sum + (e.gross_pay || 0), 0),
        netPay: employees.reduce((sum, e) => sum + (e.net_pay || 0), 0),
        totalTaxes: employees.reduce((sum, e) => sum + (e.total_taxes || 0), 0),
        totalDeductions: employees.reduce((sum, e) => sum + (e.total_deductions || 0), 0),
      }
    };
  };

  const exportToXLSX = (employees, filename = 'pay_extract') => {
    if (!employees?.length) return;
    const summary = calculateSummary(employees);
    const wb = XLSX.utils.book_new();
    
    const empData = employees.map(emp => ({
      'Company': emp.company_name || '', 'Client Code': emp.client_code || '',
      'Pay Period Start': emp.pay_period_start || '', 'Pay Period End': emp.pay_period_end || '',
      'Check Date': emp.check_date || '', 'Name': emp.name || '', 'Employee ID': emp.employee_id || '',
      'Department': emp.department || '', 'Status': emp.status || '', 'Hire Date': emp.hire_date || '',
      'Term Date': emp.term_date || '', 'Employee Type': emp.employee_type || '',
      'Pay Frequency': emp.pay_frequency || '', 'Hourly Rate': emp.hourly_rate || '',
      'Salary': emp.salary || '', 'Resident State': emp.resident_state || '',
      'Work State': emp.work_state || '', 'Federal Filing Status': emp.federal_filing_status || '',
      'State Filing Status': emp.state_filing_status || '', 'Tax Profile': emp.tax_profile || '',
      'Gross Pay': emp.gross_pay || 0, 'Total Taxes': emp.total_taxes || 0,
      'Total Deductions': emp.total_deductions || 0, 'Net Pay': emp.net_pay || 0,
      'Pay Method': emp.pay_method || '', 'Check Number': emp.check_number || '',
      'Valid': emp.is_valid ? 'Yes' : 'No'
    }));
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(empData), 'Employees');
    
    const earningsDetail = [];
    employees.forEach(emp => {
      (emp.earnings || []).forEach(e => {
        earningsDetail.push({
          'Company': emp.company_name || '', 'Period Ending': emp.period_ending || '',
          'Check Date': emp.check_date || '', 'Employee': emp.name || '',
          'Employee ID': emp.employee_id || '', 'Department': emp.department || '',
          'Earning Code': e.type || e.code || '', 'Description': e.description || '',
          'Hours': e.hours || '', 'Rate': e.rate || '', 'Amount': e.amount || 0,
          'Hours YTD': e.hours_ytd || '', 'Amount YTD': e.amount_ytd || ''
        });
      });
    });
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(earningsDetail), 'Earnings');
    
    const deductionsDetail = [];
    employees.forEach(emp => {
      (emp.deductions || []).forEach(d => {
        deductionsDetail.push({
          'Company': emp.company_name || '', 'Period Ending': emp.period_ending || '',
          'Check Date': emp.check_date || '', 'Employee': emp.name || '',
          'Employee ID': emp.employee_id || '', 'Department': emp.department || '',
          'Deduction Code': d.type || d.code || '', 'Description': d.description || '',
          'Category': d.is_employer ? 'Employer' : (d.category || 'Employee'),
          'Amount': d.amount || 0, 'Amount YTD': d.amount_ytd || ''
        });
      });
    });
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(deductionsDetail), 'Deductions');
    
    const taxesDetail = [];
    employees.forEach(emp => {
      (emp.taxes || []).forEach(t => {
        taxesDetail.push({
          'Company': emp.company_name || '', 'Period Ending': emp.period_ending || '',
          'Check Date': emp.check_date || '', 'Employee': emp.name || '',
          'Employee ID': emp.employee_id || '', 'Department': emp.department || '',
          'Tax Code': t.type || t.code || '', 'Description': t.description || '',
          'EE/ER': t.is_employer ? 'Employer' : 'Employee', 'Amount': t.amount || 0,
          'Taxable Wages': t.taxable_wages || '', 'Amount YTD': t.amount_ytd || '',
          'Taxable Wages YTD': t.taxable_wages_ytd || ''
        });
      });
    });
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(taxesDetail), 'Taxes');
    
    const summaryData = [];
    summaryData.push({ 'Category': 'EARNINGS', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    summary.earnings.forEach(e => summaryData.push({ 'Category': '', 'Code': e.description, 'Total Amount': e.total, 'Employee Count': e.count }));
    summaryData.push({ 'Category': '', 'Code': 'EARNINGS TOTAL', 'Total Amount': summary.totals.grossPay, 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    summaryData.push({ 'Category': 'TAXES', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    summary.taxes.forEach(t => summaryData.push({ 'Category': '', 'Code': t.description, 'Total Amount': t.total, 'Employee Count': t.count }));
    summaryData.push({ 'Category': '', 'Code': 'TAXES TOTAL', 'Total Amount': summary.totals.totalTaxes, 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    summaryData.push({ 'Category': 'DEDUCTIONS', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    summary.deductions.forEach(d => summaryData.push({ 'Category': '', 'Code': d.description, 'Total Amount': d.total, 'Employee Count': d.count }));
    summaryData.push({ 'Category': '', 'Code': 'DEDUCTIONS TOTAL', 'Total Amount': summary.totals.totalDeductions, 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    summaryData.push({ 'Category': 'GRAND TOTALS', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': 'Total Gross Pay', 'Total Amount': summary.totals.grossPay, 'Employee Count': employees.length });
    summaryData.push({ 'Category': '', 'Code': 'Total Taxes', 'Total Amount': summary.totals.totalTaxes, 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': 'Total Deductions', 'Total Amount': summary.totals.totalDeductions, 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': 'Total Net Pay', 'Total Amount': summary.totals.netPay, 'Employee Count': '' });
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(summaryData), 'Summary');
    
    const timestamp = new Date().toISOString().split('T')[0];
    XLSX.writeFile(wb, `${filename}_${timestamp}.xlsx`);
  };

  const estimatedCost = useTextract ? ((maxPages || 50) * 0.015 + 0.05).toFixed(2) : '0.05';

  const inputStyle = { width: '100%', padding: '0.5rem 0.75rem', border: `1px solid ${colors.divider}`, borderRadius: 6, background: colors.inputBg, color: colors.text, fontSize: '0.9rem' };
  const labelStyle = { display: 'block', fontSize: '0.85rem', fontWeight: 500, color: colors.text, marginBottom: '0.25rem' };
  const cardStyle = { background: colors.card, border: `1px solid ${colors.cardBorder}`, borderRadius: 12, padding: '1.5rem', marginBottom: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' };

  return (
    <div>
      <PageHeader
        icon={Upload}
        title="Pay Register Extraction"
        subtitle="Upload pay registers to extract employee data using AI-powered parsing"
        breadcrumbs={[
          { label: 'Data Management', to: '/data' },
          { label: 'Register Extractor' }
        ]}
      />
        
      {/* Upload Section */}
        <div style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: colors.text }}>Upload Pay Register</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', padding: '0.35rem 0.75rem', borderRadius: 20, background: useTextract ? colors.amberLight : colors.greenLight, color: useTextract ? colors.amber : colors.green }}>
              {useTextract ? <><Cloud size={14} /> AWS Processing</> : <><Lock size={14} /> Local Processing</>}
            </div>
          </div>
          
          {/* Project Badge */}
          {activeProject ? (
            (() => {
              const custColors = getCustomerColorPalette(activeProject.customer || activeProject.name);
              return (
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0.75rem', background: custColors.bg, border: `1px solid ${custColors.border}`, borderRadius: 8, marginBottom: '1rem' }}>
                  <span style={{ color: custColors.primary }}></span>
                  <span style={{ fontWeight: 600, color: custColors.primary }}>{activeProject.name}</span>
                  <span style={{ color: custColors.primary, fontSize: '0.85rem' }}>{activeProject.customer}</span>
                </div>
              );
            })()
          ) : (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0.75rem', background: colors.amberLight, border: `1px solid ${colors.amber}40`, borderRadius: 8, marginBottom: '1rem', color: colors.amber }}>
              <AlertTriangle size={16} />
              <span>Select a project from the header to continue</span>
            </div>
          )}
          
          {/* Form Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <Tooltip title="PDF File" detail="Upload a pay register PDF. Supports payroll reports, tax documents, and similar financial statements." action="Click to browse or drag and drop">
                <label style={{ ...labelStyle, cursor: 'help' }}>PDF File <span style={{ color: colors.red }}>*</span></label>
              </Tooltip>
              <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} style={inputStyle} />
            </div>
            <div>
              <Tooltip title="Page Limit" detail="Limit extraction to first N pages. Set to 0 to process all pages." action="Useful for testing large documents">
                <label style={{ ...labelStyle, cursor: 'help' }}>Pages (0 = all)</label>
              </Tooltip>
              <input type="number" value={maxPages} onChange={(e) => setMaxPages(parseInt(e.target.value) || 0)} min={0} max={2000} style={inputStyle} />
            </div>
            <div>
              <Tooltip title="Vendor Detection" detail="Specify the payroll vendor to improve extraction accuracy. Auto-detect works for most formats." action="Select if auto-detection fails">
                <label style={{ ...labelStyle, cursor: 'help' }}>Vendor</label>
              </Tooltip>
              <select value={vendorType} onChange={(e) => setVendorType(e.target.value)} style={inputStyle}>
                <option value="unknown"> Auto-Detect</option>
                <option value="paycom">Paycom</option>
                <option value="dayforce">Dayforce / Ceridian</option>
                <option value="adp">ADP</option>
                <option value="paychex">Paychex</option>
                <option value="ultipro">UKG Pro / UltiPro</option>
                <option value="workday">Workday</option>
                <option value="gusto">Gusto</option>
                <option value="quickbooks">QuickBooks</option>
              </select>
            </div>
            <div>
              <Tooltip title="Extraction Method" detail="PyMuPDF (local) is free and keeps data local. Textract (AWS) is better for scanned or low-quality PDFs." action="Use Textract for scanned documents">
                <label style={{ ...labelStyle, cursor: 'help' }}>Extraction Method</label>
              </Tooltip>
              <select value={useTextract ? 'textract' : 'pymupdf'} onChange={(e) => setUseTextract(e.target.value === 'textract')} style={inputStyle}>
                <option value="pymupdf"> PyMuPDF (Local/Free)</option>
                <option value="textract"> Textract (Scanned PDFs)</option>
              </select>
            </div>
          </div>
          
          {/* Upload Button */}
          <button onClick={handleUpload} disabled={!file || !activeProject || uploading} style={{ padding: '0.6rem 1.5rem', background: (!file || !activeProject || uploading) ? colors.textMuted : colors.primary, color: 'white', border: 'none', borderRadius: 8, fontWeight: 600, cursor: (!file || !activeProject || uploading) ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: (!file || !activeProject || uploading) ? 0.6 : 1 }}>
            {uploading ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Processing...</> : <><Upload size={16} /> Extract Data</>}
          </button>
          
          {/* Method Info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.8rem', color: colors.textMuted, marginTop: '0.75rem' }}>
            {useTextract ? (
              <>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><Cloud size={14} /> AWS Textract (for scanned PDFs)</span>
                <span style={{ color: colors.divider }}>|</span>
                <span>Est. cost: <strong>${estimatedCost}</strong></span>
                <span style={{ color: colors.divider }}>|</span>
                <span style={{ color: colors.amber }}> Data sent to AWS</span>
              </>
            ) : (
              <>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: colors.green }}><Shield size={14} /> PII Redacted before AI</span>
                <span style={{ color: colors.divider }}>|</span>
                <span>Cost: <strong>~$0.05</strong></span>
                <span style={{ color: colors.divider }}>|</span>
                <span style={{ color: colors.green }}>✓ Privacy-compliant</span>
              </>
            )}
          </div>
          
          {/* Progress Bar */}
          {uploading && jobStatus && (
            <div style={{ marginTop: '1rem', padding: '1rem', background: colors.blueLight, border: `1px solid ${colors.blue}40`, borderRadius: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 500, color: colors.blue }}>{jobStatus.message || 'Processing...'}</span>
                <span style={{ fontSize: '0.85rem', color: colors.primary }}>{jobStatus.current_page > 0 && jobStatus.total_pages > 0 ? `Page ${jobStatus.current_page} of ${jobStatus.total_pages}` : `${jobStatus.progress || 0}%`}</span>
              </div>
              <div style={{ width: '100%', background: `${colors.blue}30`, borderRadius: 4, height: 8 }}>
                <div style={{ width: `${jobStatus.progress || 0}%`, background: colors.primary, height: 8, borderRadius: 4, transition: 'width 0.3s ease' }} />
              </div>
            </div>
          )}
          
          {/* Error */}
          {error && (
            <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: colors.redLight, border: `1px solid ${colors.red}40`, borderRadius: 8, color: colors.red, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertTriangle size={18} /> {error}
            </div>
          )}
        </div>
        
        {/* Results Section */}
        {result && (
          <div style={cardStyle}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: colors.text }}>Extraction Results</h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                {result.pii_redacted > 0 && (
                  <span style={{ fontSize: '0.85rem', color: colors.green, display: 'flex', alignItems: 'center', gap: '0.25rem' }}><Shield size={14} /> {result.pii_redacted} PII redacted</span>
                )}
                {result.saved_to_db && (
                  <span style={{ fontSize: '0.85rem', color: colors.green, display: 'flex', alignItems: 'center', gap: '0.25rem' }}><CheckCircle size={14} /> Saved</span>
                )}
                <span style={{ padding: '0.25rem 0.75rem', borderRadius: 20, fontSize: '0.8rem', fontWeight: 600, background: result.success ? colors.greenLight : colors.redLight, color: result.success ? colors.green : colors.red }}>
                  {result.success ? 'Success' : 'Needs Review'}
                </span>
              </div>
            </div>
            
            {/* Stats Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
              <StatCard icon={<Users size={18} style={{ color: colors.primary }} />} label="Employees" value={result.employee_count} colors={colors} />
              <StatCard icon={<FileText size={18} style={{ color: colors.primary }} />} label="Pages" value={result.pages_processed} colors={colors} />
              <StatCard icon={<CheckCircle size={18} style={{ color: colors.green }} />} label="Confidence" value={`${(result.confidence * 100).toFixed(0)}%`} colors={colors} />
              <StatCard icon={<DollarSign size={18} style={{ color: colors.amber }} />} label="Cost" value={`$${result.cost_usd?.toFixed(3) || '0.000'}`} colors={colors} />
              <StatCard icon={<Shield size={18} style={{ color: colors.green }} />} label="Method" value={result.extraction_method === 'pymupdf' ? 'Local' : 'AWS'} colors={colors} />
              <StatCard icon={<Loader2 size={18} style={{ color: colors.textMuted }} />} label="Time" value={`${((result.processing_time_ms || 0) / 1000).toFixed(1)}s`} colors={colors} />
            </div>
            
            {/* Validation Errors */}
            {result.validation_errors?.length > 0 && (
              <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: colors.amberLight, border: `1px solid ${colors.amber}40`, borderRadius: 8 }}>
                <h3 style={{ fontWeight: 500, color: colors.amber, marginBottom: '0.5rem' }}>Validation Notes</h3>
                <ul style={{ fontSize: '0.85rem', color: colors.amber, margin: 0, paddingLeft: '1.25rem' }}>
                  {result.validation_errors.slice(0, 5).map((err, i) => <li key={i}>{err}</li>)}
                  {result.validation_errors.length > 5 && <li style={{ opacity: 0.7 }}>... and {result.validation_errors.length - 5} more</li>}
                </ul>
              </div>
            )}
            
            {/* Tabs + Export */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${colors.divider}`, marginBottom: '1rem' }}>
              <div style={{ display: 'flex' }}>
                <TabButton active={activeTab === 'employees'} onClick={() => setActiveTab('employees')} colors={colors}><Users size={14} style={{ marginRight: 4 }} /> Employees ({result.employee_count})</TabButton>
                <TabButton active={activeTab === 'summary'} onClick={() => setActiveTab('summary')} colors={colors}><BarChart3 size={14} style={{ marginRight: 4 }} /> Summary</TabButton>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {(result.confidence < 0.7 || result.validation_errors?.length > 0) && (
                  <button onClick={() => setShowAssist(true)} style={{ padding: '0.5rem 1rem', background: colors.primary, color: 'white', border: 'none', borderRadius: 6, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem' }}>
                    <Wand2 size={14} /> Help Claude
                  </button>
                )}
                <button onClick={() => exportToXLSX(result.employees, result.source_file?.replace('.pdf', '') || 'pay_extract')} style={{ padding: '0.5rem 1rem', background: colors.green, color: 'white', border: 'none', borderRadius: 6, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem' }}>
                  <Download size={14} /> Export XLSX
                </button>
              </div>
            </div>
            
            {activeTab === 'employees' ? (
              <EmployeeTable employees={result.employees || []} colors={colors} />
            ) : (
              <SummaryView employees={result.employees || []} calculateSummary={calculateSummary} colors={colors} />
            )}
          </div>
        )}
        
        {/* History Section */}
        <div style={{ display: expandedDetails ? 'block' : 'grid', gridTemplateColumns: expandedDetails ? '1fr' : '1fr 1fr', gap: '1.5rem' }}>
          {!expandedDetails && (
            <div style={cardStyle}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: colors.text, marginBottom: '1rem' }}>Extraction History</h2>
              {extracts.length === 0 ? (
                <p style={{ color: colors.textMuted, textAlign: 'center', padding: '2rem 0' }}>No extractions yet</p>
              ) : (
                <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                  {extracts.map(ext => (
                    <div key={ext.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem', border: `1px solid ${colors.divider}`, borderRadius: 8, marginBottom: '0.5rem' }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 500, fontSize: '0.9rem', color: colors.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ext.source_file}</div>
                        <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>{ext.employee_count} employees • {ext.pages_processed} pages • {ext.extraction_method === 'pymupdf' ? ' Local' : ' AWS'} • {new Date(ext.created_at).toLocaleDateString()}</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ padding: '0.15rem 0.5rem', borderRadius: 4, fontSize: '0.7rem', fontWeight: 600, background: ext.confidence >= 0.8 ? colors.greenLight : colors.amberLight, color: ext.confidence >= 0.8 ? colors.green : colors.amber }}>{(ext.confidence * 100).toFixed(0)}%</span>
                        <button onClick={() => viewExtract(ext.id)} style={{ padding: '0.35rem', background: 'transparent', border: 'none', cursor: 'pointer', color: colors.primary, borderRadius: 4 }} title="View"><Eye size={16} /></button>
                        <button onClick={() => deleteExtract(ext.id)} style={{ padding: '0.35rem', background: 'transparent', border: 'none', cursor: 'pointer', color: colors.red, borderRadius: 4 }} title="Delete"><Trash2 size={16} /></button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          
          {/* Selected Extract Details */}
          <div style={cardStyle}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: colors.text }}>Extract Details</h2>
              {selectedExtract && (
                <button onClick={() => setExpandedDetails(!expandedDetails)} style={{ padding: '0.35rem', background: 'transparent', border: 'none', cursor: 'pointer', color: colors.textMuted, borderRadius: 4 }} title={expandedDetails ? 'Collapse' : 'Expand'}>
                  {expandedDetails ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </button>
              )}
            </div>
            
            {selectedExtract ? (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <div>
                    <h3 style={{ fontWeight: 500, color: colors.text }}>{selectedExtract.source_file}</h3>
                    <p style={{ fontSize: '0.85rem', color: colors.textMuted }}>{selectedExtract.employee_count || selectedExtract.employees?.length || 0} employees extracted on {new Date(selectedExtract.created_at).toLocaleString()}</p>
                  </div>
                  <span style={{ padding: '0.25rem 0.75rem', borderRadius: 20, fontSize: '0.8rem', fontWeight: 600, background: colors.greenLight, color: colors.green }}>Success</span>
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                  <StatCard icon={<Users size={18} style={{ color: colors.primary }} />} label="Employees" value={selectedExtract.employee_count || selectedExtract.employees?.length || 0} colors={colors} />
                  <StatCard icon={<FileText size={18} style={{ color: colors.primary }} />} label="Pages" value={selectedExtract.pages_processed || '-'} colors={colors} />
                  <StatCard icon={<CheckCircle size={18} style={{ color: colors.green }} />} label="Confidence" value={selectedExtract.confidence ? `${(selectedExtract.confidence * 100).toFixed(0)}%` : '100%'} colors={colors} />
                  <StatCard icon={<DollarSign size={18} style={{ color: colors.amber }} />} label="Cost" value={`$${(selectedExtract.cost_usd || 0).toFixed(3)}`} colors={colors} />
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${colors.divider}`, marginBottom: '1rem' }}>
                  <div style={{ display: 'flex' }}>
                    <TabButton active={historyTab === 'employees'} onClick={() => setHistoryTab('employees')} colors={colors}><Users size={14} style={{ marginRight: 4 }} /> Employees ({selectedExtract.employees?.length || 0})</TabButton>
                    <TabButton active={historyTab === 'summary'} onClick={() => setHistoryTab('summary')} colors={colors}><BarChart3 size={14} style={{ marginRight: 4 }} /> Summary</TabButton>
                  </div>
                  <button onClick={() => exportToXLSX(selectedExtract.employees, selectedExtract.source_file?.replace('.pdf', '') || 'pay_extract')} disabled={!selectedExtract.employees?.length} style={{ padding: '0.5rem 1rem', background: selectedExtract.employees?.length ? colors.green : colors.textMuted, color: 'white', border: 'none', borderRadius: 6, fontWeight: 600, cursor: selectedExtract.employees?.length ? 'pointer' : 'not-allowed', display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem', opacity: selectedExtract.employees?.length ? 1 : 0.5 }}>
                    <Download size={14} /> Export XLSX
                  </button>
                </div>
                
                {historyTab === 'employees' ? (
                  <EmployeeTable employees={selectedExtract.employees || []} colors={colors} />
                ) : (
                  <SummaryView employees={selectedExtract.employees || []} calculateSummary={calculateSummary} colors={colors} />
                )}
              </div>
            ) : (
              <p style={{ color: colors.textMuted, textAlign: 'center', padding: '2rem 0' }}>Select an extraction to view details</p>
            )}
          </div>
        </div>
      
      {showAssist && result && (
        <ConsultantAssist extractionId={result.extract_id} sourceFile={result.source_file} vendorType={vendorType} customerId={null} confidence={result.confidence} validationErrors={result.validation_errors} onClose={() => setShowAssist(false)} onRetry={(hints) => { setShowAssist(false); console.log('Retry with hints:', hints); }} />
      )}
      
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function StatCard({ icon, label, value, colors }) {
  return (
    <div style={{ background: colors.inputBg, borderRadius: 8, padding: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
      {icon}
      <div>
        <div style={{ fontSize: '0.7rem', color: colors.textMuted, textTransform: 'uppercase' }}>{label}</div>
        <div style={{ fontWeight: 600, color: colors.text }}>{value}</div>
      </div>
    </div>
  );
}

function TabButton({ active, onClick, children, colors }) {
  return (
    <button onClick={onClick} style={{ padding: '0.5rem 1rem', fontWeight: 500, fontSize: '0.85rem', border: 'none', borderBottom: `2px solid ${active ? colors.primary : 'transparent'}`, background: 'transparent', color: active ? colors.primary : colors.textMuted, cursor: 'pointer', display: 'flex', alignItems: 'center', marginBottom: -1 }}>
      {children}
    </button>
  );
}

function EmployeeTable({ employees, colors }) {
  const [expandedRows, setExpandedRows] = useState(new Set());
  const toggleRow = (id) => { const next = new Set(expandedRows); if (next.has(id)) next.delete(id); else next.add(id); setExpandedRows(next); };
  
  if (!employees || employees.length === 0) return <p style={{ color: colors.textMuted, textAlign: 'center', padding: '1rem' }}>No employee data</p>;
  
  const thStyle = { textAlign: 'left', padding: '0.5rem', fontWeight: 600, fontSize: '0.75rem', color: colors.textMuted, textTransform: 'uppercase' };
  const tdStyle = { padding: '0.5rem', fontSize: '0.85rem', color: colors.text };
  
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
        <thead>
          <tr style={{ background: colors.tableHeader, borderBottom: `1px solid ${colors.divider}` }}>
            <th style={{ ...thStyle, width: 32 }}></th>
            <th style={thStyle}>Employee</th>
            <th style={thStyle}>ID</th>
            <th style={thStyle}>Department</th>
            <th style={thStyle}>Tax Profile</th>
            <th style={{ ...thStyle, textAlign: 'right' }}>Gross</th>
            <th style={{ ...thStyle, textAlign: 'right' }}>Taxes</th>
            <th style={{ ...thStyle, textAlign: 'right' }}>Deductions</th>
            <th style={{ ...thStyle, textAlign: 'right' }}>Net</th>
            <th style={{ ...thStyle, textAlign: 'center' }}>Valid</th>
          </tr>
        </thead>
        <tbody>
          {employees.map((emp, idx) => {
            const isExpanded = expandedRows.has(idx);
            return (
              <React.Fragment key={idx}>
                <tr onClick={() => toggleRow(idx)} style={{ borderBottom: `1px solid ${colors.divider}`, cursor: 'pointer', background: !emp.is_valid ? colors.redLight : 'transparent' }}>
                  <td style={tdStyle}>{isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</td>
                  <td style={{ ...tdStyle, fontWeight: 500 }}>{emp.name || '(Unknown)'}</td>
                  <td style={{ ...tdStyle, color: colors.textMuted }}>{emp.employee_id || '-'}</td>
                  <td style={{ ...tdStyle, color: colors.textMuted }}>{emp.department || '-'}</td>
                  <td style={{ ...tdStyle, color: colors.textMuted }}>{emp.tax_profile || '-'}</td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 500 }}>${parseFloat(emp.gross_pay || 0).toFixed(2)}</td>
                  <td style={{ ...tdStyle, textAlign: 'right', color: colors.red }}>${parseFloat(emp.total_taxes || 0).toFixed(2)}</td>
                  <td style={{ ...tdStyle, textAlign: 'right', color: colors.amber }}>${parseFloat(emp.total_deductions || 0).toFixed(2)}</td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 500, color: colors.green }}>${parseFloat(emp.net_pay || 0).toFixed(2)}</td>
                  <td style={{ ...tdStyle, textAlign: 'center' }}>{emp.is_valid ? <CheckCircle size={14} style={{ color: colors.green }} /> : <XCircle size={14} style={{ color: colors.red }} />}</td>
                </tr>
                {isExpanded && (
                  <tr style={{ background: colors.inputBg }}>
                    <td colSpan={10} style={{ padding: '1rem' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                        <div>
                          <h4 style={{ fontWeight: 500, marginBottom: '0.5rem', color: colors.blue }}>Earnings</h4>
                          {emp.earnings?.length > 0 ? (
                            <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                              {emp.earnings.map((e, i) => (
                                <li key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                                  <span style={{ color: colors.textMuted }}>{e.description || e.type || 'Earning'}</span>
                                  <span style={{ fontWeight: 500, color: colors.text }}>${parseFloat(e.amount || 0).toFixed(2)}</span>
                                </li>
                              ))}
                            </ul>
                          ) : <p style={{ fontSize: '0.8rem', color: colors.textLight }}>No earnings data</p>}
                        </div>
                        <div>
                          <h4 style={{ fontWeight: 500, marginBottom: '0.5rem', color: colors.red }}>Taxes</h4>
                          {emp.taxes?.length > 0 ? (
                            <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                              {emp.taxes.map((t, i) => (
                                <li key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                                  <span style={{ color: colors.textMuted }}>{t.description || t.type || 'Tax'}</span>
                                  <span style={{ fontWeight: 500, color: colors.text }}>${parseFloat(t.amount || 0).toFixed(2)}</span>
                                </li>
                              ))}
                            </ul>
                          ) : <p style={{ fontSize: '0.8rem', color: colors.textLight }}>No tax data</p>}
                        </div>
                        <div>
                          <h4 style={{ fontWeight: 500, marginBottom: '0.5rem', color: colors.amber }}>Deductions</h4>
                          {emp.deductions?.length > 0 ? (
                            <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                              {emp.deductions.map((d, i) => (
                                <li key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                                  <span style={{ color: colors.textMuted }}>{d.description || d.type || 'Deduction'}</span>
                                  <span style={{ fontWeight: 500, color: colors.text }}>${parseFloat(d.amount || 0).toFixed(2)}</span>
                                </li>
                              ))}
                            </ul>
                          ) : <p style={{ fontSize: '0.8rem', color: colors.textLight }}>No deduction data</p>}
                        </div>
                      </div>
                      <div style={{ marginTop: '0.75rem', display: 'flex', gap: '1rem', fontSize: '0.8rem', color: colors.textMuted }}>
                        {emp.pay_method && <span>Payment: <strong>{emp.pay_method}</strong></span>}
                        {emp.check_number && <span>Check #: <strong>{emp.check_number}</strong></span>}
                      </div>
                      {emp.validation_errors?.length > 0 && (
                        <div style={{ marginTop: '0.75rem', padding: '0.5rem', background: colors.redLight, borderRadius: 4, fontSize: '0.8rem', color: colors.red }}>{emp.validation_errors.join(', ')}</div>
                      )}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SummaryView({ employees, calculateSummary, colors }) {
  const summary = calculateSummary(employees);
  const formatCurrency = (val) => '$' + val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  
  return (
    <div>
      {/* Grand Totals */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', padding: '1rem', background: colors.inputBg, borderRadius: 8, marginBottom: '1.5rem' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: colors.primary }}>{formatCurrency(summary.totals.grossPay)}</div>
          <div style={{ fontSize: '0.8rem', color: colors.textMuted }}>Total Gross Pay</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: colors.red }}>{formatCurrency(summary.totals.totalTaxes)}</div>
          <div style={{ fontSize: '0.8rem', color: colors.textMuted }}>Total Taxes</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: colors.amber }}>{formatCurrency(summary.totals.totalDeductions)}</div>
          <div style={{ fontSize: '0.8rem', color: colors.textMuted }}>Total Deductions</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: colors.green }}>{formatCurrency(summary.totals.netPay)}</div>
          <div style={{ fontSize: '0.8rem', color: colors.textMuted }}>Total Net Pay</div>
        </div>
      </div>
      
      {/* Summary Tables */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
        <SummaryTable title="Earnings by Type" items={summary.earnings} total={summary.totals.grossPay} color={colors.blue} empCount={employees.length} colors={colors} icon={<DollarSign size={18} />} />
        <SummaryTable title="Taxes by Type" items={summary.taxes} total={summary.totals.totalTaxes} color={colors.red} empCount={employees.length} colors={colors} icon={<FileText size={18} />} />
        <SummaryTable title="Deductions by Type" items={summary.deductions} total={summary.totals.totalDeductions} color={colors.amber} empCount={employees.length} colors={colors} icon={<FileText size={18} />} />
      </div>
    </div>
  );
}

function SummaryTable({ title, items, total, color, empCount, colors, icon }) {
  const formatCurrency = (val) => '$' + val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const thStyle = { textAlign: 'left', padding: '0.5rem', fontWeight: 600, fontSize: '0.75rem', color: colors.textMuted };
  
  return (
    <div>
      <h3 style={{ fontWeight: 600, color: color, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>{icon} {title}</h3>
      {items.length > 0 ? (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ background: `${color}15`, borderBottom: `1px solid ${colors.divider}` }}>
              <th style={thStyle}>Type</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Total</th>
              <th style={{ ...thStyle, textAlign: 'right' }}># Emp</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr key={i} style={{ borderBottom: `1px solid ${colors.divider}` }}>
                <td style={{ padding: '0.5rem', color: colors.text, maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={item.description}>{item.description}</td>
                <td style={{ padding: '0.5rem', textAlign: 'right', fontWeight: 500, color: colors.text }}>{formatCurrency(item.total)}</td>
                <td style={{ padding: '0.5rem', textAlign: 'right', color: colors.textMuted }}>{item.count}</td>
              </tr>
            ))}
            <tr style={{ background: `${color}20`, fontWeight: 600 }}>
              <td style={{ padding: '0.5rem', color: colors.text }}>TOTAL</td>
              <td style={{ padding: '0.5rem', textAlign: 'right', color: colors.text }}>{formatCurrency(total)}</td>
              <td style={{ padding: '0.5rem', textAlign: 'right', color: colors.textMuted }}>{empCount}</td>
            </tr>
          </tbody>
        </table>
      ) : (
        <p style={{ fontSize: '0.85rem', color: colors.textLight }}>No data</p>
      )}
    </div>
  );
}
