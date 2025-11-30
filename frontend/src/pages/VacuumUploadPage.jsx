/**
 * Vacuum Upload Page - Pay Register Extraction v12
 * 
 * Privacy-First Features:
 * - PyMuPDF (local extraction) as DEFAULT
 * - Textract toggle for scanned PDFs
 * - PII redaction indicator
 * - Async job polling with progress bar
 * - Full employee data with details
 * - XLSX Export
 * - Summary by Earnings/Taxes/Deductions type
 * 
 * Deploy to: frontend/src/pages/VacuumUploadPage.jsx
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Upload, FileText, Users, DollarSign, CheckCircle, XCircle, 
  Loader2, Trash2, Eye, AlertTriangle, ChevronDown, ChevronRight,
  Shield, Cloud, Lock, Download, BarChart3
} from 'lucide-react';
import * as XLSX from 'xlsx';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function VacuumUploadPage() {
  // State
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [extracts, setExtracts] = useState([]);
  const [selectedExtract, setSelectedExtract] = useState(null);
  const [error, setError] = useState(null);
  const [maxPages, setMaxPages] = useState(0); // 0 = all pages
  const [useTextract, setUseTextract] = useState(false); // PyMuPDF is default
  const [activeTab, setActiveTab] = useState('employees'); // 'employees' or 'summary'
  
  // Job polling state
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const pollIntervalRef = useRef(null);

  // Load projects
  useEffect(() => {
    const loadProjects = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/projects/list`);
        if (!res.ok) {
          console.error('Projects endpoint returned:', res.status);
          setProjects([]);
          return;
        }
        const data = await res.json();
        if (Array.isArray(data)) {
          setProjects(data);
        } else if (data.projects && Array.isArray(data.projects)) {
          setProjects(data.projects);
        } else {
          console.error('Unexpected projects format:', data);
          setProjects([]);
        }
      } catch (err) {
        console.error('Failed to load projects:', err);
        setProjects([]);
      }
    };
    loadProjects();
  }, []);

  // Load extraction history
  const loadExtracts = useCallback(async () => {
    try {
      const url = selectedProject 
        ? `${API_BASE}/api/vacuum/extracts?project_id=${selectedProject}`
        : `${API_BASE}/api/vacuum/extracts`;
      const res = await fetch(url);
      const data = await res.json();
      setExtracts(data.extracts || []);
    } catch (err) {
      console.error('Failed to load extracts:', err);
    }
  }, [selectedProject]);

  useEffect(() => {
    loadExtracts();
  }, [loadExtracts]);

  // Poll job status
  const pollJobStatus = useCallback(async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/job/${id}`);
      if (!res.ok) {
        throw new Error('Job not found');
      }
      const data = await res.json();
      setJobStatus(data);
      
      if (data.status === 'completed') {
        clearInterval(pollIntervalRef.current);
        setUploading(false);
        setJobId(null);
        if (data.result) {
          setResult(data.result);
          loadExtracts();
        }
      } else if (data.status === 'failed') {
        clearInterval(pollIntervalRef.current);
        setUploading(false);
        setJobId(null);
        setError(data.message || 'Extraction failed');
      }
    } catch (err) {
      console.error('Poll failed:', err);
    }
  }, [loadExtracts]);

  // Start polling when job is created
  useEffect(() => {
    if (jobId) {
      pollIntervalRef.current = setInterval(() => pollJobStatus(jobId), 1000);
      return () => clearInterval(pollIntervalRef.current);
    }
  }, [jobId, pollJobStatus]);

  // Handle file upload
  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }
    if (!selectedProject) {
      setError('Please select a project');
      return;
    }
    
    setUploading(true);
    setError(null);
    setResult(null);
    setJobStatus(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('max_pages', maxPages.toString());
      formData.append('project_id', selectedProject);
      formData.append('use_textract', useTextract.toString());
      formData.append('async_mode', 'true');
      
      const res = await fetch(`${API_BASE}/api/vacuum/upload`, {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed');
      }
      
      if (data.job_id) {
        // Async mode - start polling
        setJobId(data.job_id);
        setJobStatus({ status: 'processing', progress: 0, message: 'Starting...' });
      } else {
        // Sync mode - result is immediate
        setResult(data);
        setUploading(false);
        loadExtracts();
      }
      
    } catch (err) {
      setError(err.message);
      setUploading(false);
    }
  };

  // Load full extraction details
  const viewExtract = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/extract/${id}`);
      const data = await res.json();
      setSelectedExtract(data);
    } catch (err) {
      console.error('Failed to load extract:', err);
    }
  };

  // Delete extraction
  const deleteExtract = async (id) => {
    if (!confirm('Delete this extraction?')) return;
    
    try {
      await fetch(`${API_BASE}/api/vacuum/extract/${id}`, { method: 'DELETE' });
      loadExtracts();
      if (selectedExtract?.id === id) {
        setSelectedExtract(null);
      }
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  // Calculate summary data from employees
  const calculateSummary = (employees) => {
    if (!employees?.length) return { earnings: [], taxes: [], deductions: [] };
    
    const earningsMap = new Map();
    const taxesMap = new Map();
    const deductionsMap = new Map();
    
    employees.forEach(emp => {
      // Earnings
      (emp.earnings || []).forEach(e => {
        const key = e.type || e.description || 'Other';
        const existing = earningsMap.get(key) || { total: 0, count: 0 };
        earningsMap.set(key, { 
          total: existing.total + (e.amount || 0), 
          count: existing.count + 1 
        });
      });
      
      // Taxes
      (emp.taxes || []).forEach(t => {
        const key = t.type || t.description || 'Other';
        const existing = taxesMap.get(key) || { total: 0, count: 0 };
        taxesMap.set(key, { 
          total: existing.total + (t.amount || 0), 
          count: existing.count + 1 
        });
      });
      
      // Deductions
      (emp.deductions || []).forEach(d => {
        const key = d.type || d.description || 'Other';
        const existing = deductionsMap.get(key) || { total: 0, count: 0 };
        deductionsMap.set(key, { 
          total: existing.total + (d.amount || 0), 
          count: existing.count + 1 
        });
      });
    });
    
    const mapToArray = (map) => Array.from(map.entries())
      .map(([description, data]) => ({ description, ...data }))
      .sort((a, b) => b.total - a.total);
    
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

  // Export to XLSX
  const exportToXLSX = (employees, filename = 'pay_extract') => {
    if (!employees?.length) return;
    
    const summary = calculateSummary(employees);
    const wb = XLSX.utils.book_new();
    
    // Sheet 1: Employee Summary
    const empData = employees.map(emp => ({
      'Name': emp.name || '',
      'Employee ID': emp.employee_id || '',
      'Department': emp.department || '',
      'Tax Profile': emp.tax_profile || '',
      'Gross Pay': emp.gross_pay || 0,
      'Total Taxes': emp.total_taxes || 0,
      'Total Deductions': emp.total_deductions || 0,
      'Net Pay': emp.net_pay || 0,
      'Pay Method': emp.pay_method || '',
      'Check Number': emp.check_number || '',
      'Valid': emp.is_valid ? 'Yes' : 'No'
    }));
    const empSheet = XLSX.utils.json_to_sheet(empData);
    XLSX.utils.book_append_sheet(wb, empSheet, 'Employees');
    
    // Sheet 2: Earnings Detail (each earning by employee)
    const earningsDetail = [];
    employees.forEach(emp => {
      (emp.earnings || []).forEach(e => {
        earningsDetail.push({
          'Employee': emp.name || '',
          'Employee ID': emp.employee_id || '',
          'Department': emp.department || '',
          'Earning Code': e.type || e.code || '',
          'Description': e.description || '',
          'Hours': e.hours || '',
          'Rate': e.rate || '',
          'Amount': e.amount || 0
        });
      });
    });
    const earningsDetailSheet = XLSX.utils.json_to_sheet(earningsDetail);
    XLSX.utils.book_append_sheet(wb, earningsDetailSheet, 'Earnings');
    
    // Sheet 3: Deductions Detail (each deduction by employee)
    const deductionsDetail = [];
    employees.forEach(emp => {
      (emp.deductions || []).forEach(d => {
        deductionsDetail.push({
          'Employee': emp.name || '',
          'Employee ID': emp.employee_id || '',
          'Department': emp.department || '',
          'Deduction Code': d.type || d.code || '',
          'Description': d.description || '',
          'Amount': d.amount || 0
        });
      });
    });
    const deductionsDetailSheet = XLSX.utils.json_to_sheet(deductionsDetail);
    XLSX.utils.book_append_sheet(wb, deductionsDetailSheet, 'Deductions');
    
    // Sheet 4: Taxes Detail (each tax by employee)
    const taxesDetail = [];
    employees.forEach(emp => {
      (emp.taxes || []).forEach(t => {
        taxesDetail.push({
          'Employee': emp.name || '',
          'Employee ID': emp.employee_id || '',
          'Department': emp.department || '',
          'Tax Code': t.type || t.code || '',
          'Description': t.description || '',
          'Amount': t.amount || 0
        });
      });
    });
    const taxesDetailSheet = XLSX.utils.json_to_sheet(taxesDetail);
    XLSX.utils.book_append_sheet(wb, taxesDetailSheet, 'Taxes');
    
    // Sheet 5: Summary (all rollups on one sheet)
    const summaryData = [];
    
    // Earnings section
    summaryData.push({ 'Category': 'EARNINGS', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    summary.earnings.forEach(e => {
      summaryData.push({
        'Category': '',
        'Code': e.description,
        'Total Amount': e.total,
        'Employee Count': e.count
      });
    });
    summaryData.push({ 'Category': '', 'Code': 'EARNINGS TOTAL', 'Total Amount': summary.totals.grossPay, 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    
    // Taxes section
    summaryData.push({ 'Category': 'TAXES', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    summary.taxes.forEach(t => {
      summaryData.push({
        'Category': '',
        'Code': t.description,
        'Total Amount': t.total,
        'Employee Count': t.count
      });
    });
    summaryData.push({ 'Category': '', 'Code': 'TAXES TOTAL', 'Total Amount': summary.totals.totalTaxes, 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    
    // Deductions section
    summaryData.push({ 'Category': 'DEDUCTIONS', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    summary.deductions.forEach(d => {
      summaryData.push({
        'Category': '',
        'Code': d.description,
        'Total Amount': d.total,
        'Employee Count': d.count
      });
    });
    summaryData.push({ 'Category': '', 'Code': 'DEDUCTIONS TOTAL', 'Total Amount': summary.totals.totalDeductions, 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    
    // Grand totals
    summaryData.push({ 'Category': 'GRAND TOTALS', 'Code': '', 'Total Amount': '', 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': 'Total Gross Pay', 'Total Amount': summary.totals.grossPay, 'Employee Count': employees.length });
    summaryData.push({ 'Category': '', 'Code': 'Total Taxes', 'Total Amount': summary.totals.totalTaxes, 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': 'Total Deductions', 'Total Amount': summary.totals.totalDeductions, 'Employee Count': '' });
    summaryData.push({ 'Category': '', 'Code': 'Total Net Pay', 'Total Amount': summary.totals.netPay, 'Employee Count': '' });
    
    const summarySheet = XLSX.utils.json_to_sheet(summaryData);
    XLSX.utils.book_append_sheet(wb, summarySheet, 'Summary');
    
    // Download
    const timestamp = new Date().toISOString().split('T')[0];
    XLSX.writeFile(wb, `${filename}_${timestamp}.xlsx`);
  };

  // Calculate cost estimate
  const estimatedCost = useTextract 
    ? ((maxPages || 50) * 0.015 + 0.05).toFixed(2)
    : '0.05'; // PyMuPDF is free, only Claude cost

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Pay Register Extraction
        </h1>
        <p className="text-gray-600 mb-6">
          Upload pay registers to extract employee data using AI-powered parsing
        </p>
        
        {/* Upload Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Upload Pay Register</h2>
            
            {/* Privacy Badge */}
            <div className="flex items-center gap-2 text-sm">
              <div className={`flex items-center gap-1 px-3 py-1 rounded-full ${
                useTextract 
                  ? 'bg-yellow-100 text-yellow-800' 
                  : 'bg-green-100 text-green-800'
              }`}>
                {useTextract ? (
                  <><Cloud className="w-4 h-4" /> AWS Processing</>
                ) : (
                  <><Lock className="w-4 h-4" /> Local Processing</>
                )}
              </div>
            </div>
          </div>
          
          <div className="grid md:grid-cols-5 gap-4 mb-4">
            {/* Project Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Project <span className="text-red-500">*</span>
              </label>
              <select
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select a project...</option>
                {projects.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.name} {p.customer ? `(${p.customer})` : ''}
                  </option>
                ))}
              </select>
            </div>
            
            {/* File Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                PDF File <span className="text-red-500">*</span>
              </label>
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            
            {/* Max Pages */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Pages (0 = all)
              </label>
              <input
                type="number"
                value={maxPages}
                onChange={(e) => setMaxPages(parseInt(e.target.value) || 0)}
                min={0}
                max={2000}
                className="w-full border rounded-lg px-3 py-2"
              />
            </div>
            
            {/* OCR Method Toggle */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Extraction Method
              </label>
              <select
                value={useTextract ? 'textract' : 'pymupdf'}
                onChange={(e) => setUseTextract(e.target.value === 'textract')}
                className="w-full border rounded-lg px-3 py-2"
              >
                <option value="pymupdf">🔒 PyMuPDF (Local/Free)</option>
                <option value="textract">☁️ Textract (Scanned PDFs)</option>
              </select>
            </div>
            
            {/* Upload Button */}
            <div className="flex items-end">
              <button
                onClick={handleUpload}
                disabled={!file || !selectedProject || uploading}
                className="w-full px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {uploading ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Processing...</>
                ) : (
                  <><Upload className="w-4 h-4" /> Extract Data</>
                )}
              </button>
            </div>
          </div>
          
          {/* Method Info */}
          <div className="flex items-center gap-4 text-sm text-gray-500 mb-3">
            {useTextract ? (
              <>
                <span className="flex items-center gap-1">
                  <Cloud className="w-4 h-4" />
                  AWS Textract (for scanned/image PDFs)
                </span>
                <span className="text-gray-300">|</span>
                <span>
                  Estimated cost: <strong>${estimatedCost}</strong>
                </span>
                <span className="text-gray-300">|</span>
                <span className="text-yellow-600">
                  ⚠️ Data sent to AWS for OCR
                </span>
              </>
            ) : (
              <>
                <span className="flex items-center gap-1 text-green-600">
                  <Shield className="w-4 h-4" />
                  PII Redacted before AI processing
                </span>
                <span className="text-gray-300">|</span>
                <span>
                  Cost: <strong>~$0.05</strong> (AI parsing only)
                </span>
                <span className="text-gray-300">|</span>
                <span className="text-green-600">
                  ✓ Privacy-compliant extraction
                </span>
              </>
            )}
          </div>
          
          {/* Progress Bar (when processing) */}
          {uploading && jobStatus && (
            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-blue-700">
                  {jobStatus.message || 'Processing...'}
                </span>
                <span className="text-sm text-blue-600">
                  {jobStatus.current_page > 0 && jobStatus.total_pages > 0 
                    ? `Page ${jobStatus.current_page} of ${jobStatus.total_pages}`
                    : `${jobStatus.progress || 0}%`
                  }
                </span>
              </div>
              <div className="w-full bg-blue-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${jobStatus.progress || 0}%` }}
                />
              </div>
            </div>
          )}
          
          {/* Error */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              {error}
            </div>
          )}
        </div>
        
        {/* Results Section */}
        {result && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Extraction Results</h2>
              <div className="flex items-center gap-3">
                {result.pii_redacted > 0 && (
                  <span className="text-sm text-green-600 flex items-center gap-1">
                    <Shield className="w-4 h-4" /> {result.pii_redacted} PII redacted
                  </span>
                )}
                {result.saved_to_db && (
                  <span className="text-sm text-green-600 flex items-center gap-1">
                    <CheckCircle className="w-4 h-4" /> Saved
                  </span>
                )}
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {result.success ? 'Success' : 'Needs Review'}
                </span>
              </div>
            </div>
            
            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
              <StatCard 
                icon={<Users className="w-5 h-5 text-blue-600" />}
                label="Employees"
                value={result.employee_count}
              />
              <StatCard 
                icon={<FileText className="w-5 h-5 text-purple-600" />}
                label="Pages"
                value={result.pages_processed}
              />
              <StatCard 
                icon={<CheckCircle className="w-5 h-5 text-green-600" />}
                label="Confidence"
                value={`${(result.confidence * 100).toFixed(0)}%`}
              />
              <StatCard 
                icon={<DollarSign className="w-5 h-5 text-amber-600" />}
                label="Cost"
                value={`$${result.cost_usd?.toFixed(3) || '0.000'}`}
              />
              <StatCard 
                icon={<Shield className="w-5 h-5 text-green-600" />}
                label="Method"
                value={result.extraction_method === 'pymupdf' ? 'Local' : 'AWS'}
              />
              <StatCard 
                icon={<Loader2 className="w-5 h-5 text-gray-600" />}
                label="Time"
                value={`${((result.processing_time_ms || 0) / 1000).toFixed(1)}s`}
              />
            </div>
            
            {/* Validation Errors */}
            {result.validation_errors?.length > 0 && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <h3 className="font-medium text-yellow-800 mb-2">Validation Notes</h3>
                <ul className="text-sm text-yellow-700 space-y-1">
                  {result.validation_errors.slice(0, 5).map((err, i) => (
                    <li key={i}>• {err}</li>
                  ))}
                  {result.validation_errors.length > 5 && (
                    <li className="text-yellow-600">
                      ... and {result.validation_errors.length - 5} more
                    </li>
                  )}
                </ul>
              </div>
            )}
            
            {/* Tabs + Export */}
            <div className="flex items-center justify-between mb-4 border-b">
              <div className="flex">
                <button
                  onClick={() => setActiveTab('employees')}
                  className={`px-4 py-2 font-medium text-sm border-b-2 -mb-px ${
                    activeTab === 'employees' 
                      ? 'border-blue-600 text-blue-600' 
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <Users className="w-4 h-4 inline mr-1" />
                  Employees ({result.employee_count})
                </button>
                <button
                  onClick={() => setActiveTab('summary')}
                  className={`px-4 py-2 font-medium text-sm border-b-2 -mb-px ${
                    activeTab === 'summary' 
                      ? 'border-blue-600 text-blue-600' 
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <BarChart3 className="w-4 h-4 inline mr-1" />
                  Summary
                </button>
              </div>
              
              <button
                onClick={() => exportToXLSX(
                  result.employees, 
                  result.source_file?.replace('.pdf', '') || 'pay_extract'
                )}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2 text-sm"
              >
                <Download className="w-4 h-4" />
                Export XLSX
              </button>
            </div>
            
            {/* Tab Content */}
            {activeTab === 'employees' ? (
              <EmployeeTable employees={result.employees || []} />
            ) : (
              <SummaryView employees={result.employees || []} calculateSummary={calculateSummary} />
            )}
          </div>
        )}
        
        {/* History Section */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Extraction History */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Extraction History</h2>
            
            {extracts.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No extractions yet</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {extracts.map(ext => (
                  <div 
                    key={ext.id}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">{ext.source_file}</div>
                      <div className="text-xs text-gray-500">
                        {ext.employee_count} employees • {ext.pages_processed} pages 
                        • {ext.extraction_method === 'pymupdf' ? '🔒 Local' : '☁️ AWS'}
                        • {new Date(ext.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        ext.confidence >= 0.8 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {(ext.confidence * 100).toFixed(0)}%
                      </span>
                      <button
                        onClick={() => viewExtract(ext.id)}
                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => deleteExtract(ext.id)}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Selected Extract Details */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Extract Details</h2>
              
              {/* Export XLSX Button - shows when extract is selected */}
              {selectedExtract && selectedExtract.employees?.length > 0 && (
                <button
                  onClick={() => exportToXLSX(
                    selectedExtract.employees, 
                    selectedExtract.source_file?.replace('.pdf', '') || 'pay_extract'
                  )}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
                >
                  <Download className="w-4 h-4" />
                  Export XLSX
                </button>
              )}
            </div>
            
            {selectedExtract ? (
              <div>
                <div className="mb-4">
                  <h3 className="font-medium">{selectedExtract.source_file}</h3>
                  <p className="text-sm text-gray-500">
                    {selectedExtract.employee_count} employees extracted on{' '}
                    {new Date(selectedExtract.created_at).toLocaleString()}
                  </p>
                </div>
                
                <EmployeeTable employees={selectedExtract.employees || []} />
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">
                Select an extraction to view details
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({ icon, label, value }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 flex items-center gap-3">
      {icon}
      <div>
        <div className="text-xs text-gray-500">{label}</div>
        <div className="font-semibold">{value}</div>
      </div>
    </div>
  );
}

// Employee Table Component
function EmployeeTable({ employees }) {
  const [expandedRows, setExpandedRows] = useState(new Set());
  
  const toggleRow = (id) => {
    const next = new Set(expandedRows);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setExpandedRows(next);
  };
  
  if (!employees || employees.length === 0) {
    return <p className="text-gray-500 text-center py-4">No employee data</p>;
  }
  
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-gray-50">
            <th className="text-left p-2 w-8"></th>
            <th className="text-left p-2">Employee</th>
            <th className="text-left p-2">ID</th>
            <th className="text-left p-2">Department</th>
            <th className="text-left p-2">Tax Profile</th>
            <th className="text-right p-2">Gross</th>
            <th className="text-right p-2">Taxes</th>
            <th className="text-right p-2">Deductions</th>
            <th className="text-right p-2">Net</th>
            <th className="text-center p-2">Valid</th>
          </tr>
        </thead>
        <tbody>
          {employees.map((emp, idx) => {
            const isExpanded = expandedRows.has(idx);
            return (
              <React.Fragment key={idx}>
                <tr className={`border-b hover:bg-gray-50 cursor-pointer ${
                  !emp.is_valid ? 'bg-red-50' : ''
                }`} onClick={() => toggleRow(idx)}>
                  <td className="p-2">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </td>
                  <td className="p-2 font-medium">{emp.name || '(Unknown)'}</td>
                  <td className="p-2 text-gray-600">{emp.employee_id || '-'}</td>
                  <td className="p-2 text-gray-600">{emp.department || '-'}</td>
                  <td className="p-2 text-gray-600">{emp.tax_profile || '-'}</td>
                  <td className="p-2 text-right font-medium">${(emp.gross_pay || 0).toFixed(2)}</td>
                  <td className="p-2 text-right text-red-600">${(emp.total_taxes || 0).toFixed(2)}</td>
                  <td className="p-2 text-right text-orange-600">${(emp.total_deductions || 0).toFixed(2)}</td>
                  <td className="p-2 text-right font-medium text-green-600">${(emp.net_pay || 0).toFixed(2)}</td>
                  <td className="p-2 text-center">
                    {emp.is_valid ? (
                      <CheckCircle className="w-4 h-4 text-green-500 inline" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500 inline" />
                    )}
                  </td>
                </tr>
                
                {/* Expanded Details */}
                {isExpanded && (
                  <tr className="bg-gray-50">
                    <td colSpan={9} className="p-4">
                      <div className="grid md:grid-cols-3 gap-4">
                        {/* Earnings */}
                        <div>
                          <h4 className="font-medium mb-2 text-blue-700">Earnings</h4>
                          {emp.earnings?.length > 0 ? (
                            <ul className="space-y-1">
                              {emp.earnings.map((e, i) => (
                                <li key={i} className="flex justify-between text-xs">
                                  <span>{e.type || e.description || 'Earning'}</span>
                                  <span className="font-medium">${(e.amount || 0).toFixed(2)}</span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-xs text-gray-400">No earnings data</p>
                          )}
                        </div>
                        
                        {/* Taxes */}
                        <div>
                          <h4 className="font-medium mb-2 text-red-700">Taxes</h4>
                          {emp.taxes?.length > 0 ? (
                            <ul className="space-y-1">
                              {emp.taxes.map((t, i) => (
                                <li key={i} className="flex justify-between text-xs">
                                  <span>{t.type || t.description || 'Tax'}</span>
                                  <span className="font-medium">${(t.amount || 0).toFixed(2)}</span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-xs text-gray-400">No tax data</p>
                          )}
                        </div>
                        
                        {/* Deductions */}
                        <div>
                          <h4 className="font-medium mb-2 text-orange-700">Deductions</h4>
                          {emp.deductions?.length > 0 ? (
                            <ul className="space-y-1">
                              {emp.deductions.map((d, i) => (
                                <li key={i} className="flex justify-between text-xs">
                                  <span>{d.type || d.description || 'Deduction'}</span>
                                  <span className="font-medium">${(d.amount || 0).toFixed(2)}</span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-xs text-gray-400">No deduction data</p>
                          )}
                        </div>
                      </div>
                      
                      {/* Pay Method & Check */}
                      <div className="mt-3 flex gap-4 text-xs text-gray-600">
                        {emp.pay_method && (
                          <span>Payment: <strong>{emp.pay_method}</strong></span>
                        )}
                        {emp.check_number && (
                          <span>Check #: <strong>{emp.check_number}</strong></span>
                        )}
                      </div>
                      
                      {/* Validation Errors */}
                      {emp.validation_errors?.length > 0 && (
                        <div className="mt-3 p-2 bg-red-50 rounded text-xs text-red-700">
                          {emp.validation_errors.join(', ')}
                        </div>
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

// Summary View Component
function SummaryView({ employees, calculateSummary }) {
  const summary = calculateSummary(employees);
  
  return (
    <div className="space-y-6">
      {/* Grand Totals */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">
            ${summary.totals.grossPay.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-sm text-gray-500">Total Gross Pay</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-red-600">
            ${summary.totals.totalTaxes.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-sm text-gray-500">Total Taxes</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-orange-600">
            ${summary.totals.totalDeductions.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-sm text-gray-500">Total Deductions</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">
            ${summary.totals.netPay.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-sm text-gray-500">Total Net Pay</div>
        </div>
      </div>
      
      {/* Summary Tables */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* Earnings by Type */}
        <div>
          <h3 className="font-semibold text-blue-700 mb-3 flex items-center gap-2">
            <DollarSign className="w-5 h-5" />
            Earnings by Type
          </h3>
          {summary.earnings.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-blue-50">
                  <th className="text-left p-2">Type</th>
                  <th className="text-right p-2">Total</th>
                  <th className="text-right p-2"># Emp</th>
                </tr>
              </thead>
              <tbody>
                {summary.earnings.map((e, i) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="p-2 truncate max-w-[150px]" title={e.description}>{e.description}</td>
                    <td className="p-2 text-right font-medium">${e.total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="p-2 text-right text-gray-500">{e.count}</td>
                  </tr>
                ))}
                <tr className="bg-blue-100 font-semibold">
                  <td className="p-2">TOTAL</td>
                  <td className="p-2 text-right">${summary.totals.grossPay.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="p-2 text-right">{employees.length}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <p className="text-gray-400 text-sm">No earnings data</p>
          )}
        </div>
        
        {/* Taxes by Type */}
        <div>
          <h3 className="font-semibold text-red-700 mb-3 flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Taxes by Type
          </h3>
          {summary.taxes.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-red-50">
                  <th className="text-left p-2">Type</th>
                  <th className="text-right p-2">Total</th>
                  <th className="text-right p-2"># Emp</th>
                </tr>
              </thead>
              <tbody>
                {summary.taxes.map((t, i) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="p-2 truncate max-w-[150px]" title={t.description}>{t.description}</td>
                    <td className="p-2 text-right font-medium">${t.total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="p-2 text-right text-gray-500">{t.count}</td>
                  </tr>
                ))}
                <tr className="bg-red-100 font-semibold">
                  <td className="p-2">TOTAL</td>
                  <td className="p-2 text-right">${summary.totals.totalTaxes.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="p-2 text-right">{employees.length}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <p className="text-gray-400 text-sm">No tax data</p>
          )}
        </div>
        
        {/* Deductions by Type */}
        <div>
          <h3 className="font-semibold text-orange-700 mb-3 flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Deductions by Type
          </h3>
          {summary.deductions.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-orange-50">
                  <th className="text-left p-2">Type</th>
                  <th className="text-right p-2">Total</th>
                  <th className="text-right p-2"># Emp</th>
                </tr>
              </thead>
              <tbody>
                {summary.deductions.map((d, i) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="p-2 truncate max-w-[150px]" title={d.description}>{d.description}</td>
                    <td className="p-2 text-right font-medium">${d.total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="p-2 text-right text-gray-500">{d.count}</td>
                  </tr>
                ))}
                <tr className="bg-orange-100 font-semibold">
                  <td className="p-2">TOTAL</td>
                  <td className="p-2 text-right">${summary.totals.totalDeductions.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="p-2 text-right">{employees.length}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <p className="text-gray-400 text-sm">No deduction data</p>
          )}
        </div>
      </div>
    </div>
  );
}
