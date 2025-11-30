/**
 * Vacuum Upload Page - Pay Register Extraction
 * 
 * Features:
 * - Project selector (required)
 * - Upload pay registers
 * - View extraction results with field coverage
 * - Employee data with full details
 * - Extraction history
 * 
 * Deploy to: frontend/src/pages/VacuumUploadPage.jsx
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Upload, FileText, Users, DollarSign, CheckCircle, XCircle, Loader2, Trash2, Eye, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react';

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
  const [maxPages, setMaxPages] = useState(3);

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
        // Handle different response formats
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
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('max_pages', maxPages.toString());
      formData.append('project_id', selectedProject);
      
      const res = await fetch(`${API_BASE}/api/vacuum/upload`, {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed');
      }
      
      setResult(data);
      loadExtracts();
      
    } catch (err) {
      setError(err.message);
    } finally {
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
          <h2 className="text-lg font-semibold mb-4">Upload Pay Register</h2>
          
          <div className="grid md:grid-cols-4 gap-4 mb-4">
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
                Pages to Process
              </label>
              <input
                type="number"
                value={maxPages}
                onChange={(e) => setMaxPages(parseInt(e.target.value) || 3)}
                min={1}
                max={500}
                className="w-full border rounded-lg px-3 py-2"
              />
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
          
          {/* Cost Estimate */}
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span>
              Estimated cost: <strong>${(maxPages * 0.015 + 0.05).toFixed(2)}</strong>
            </span>
            <span className="text-gray-300">|</span>
            <span>
              {maxPages} pages × $0.015 (Textract) + ~$0.05 (AI parsing)
            </span>
          </div>
          
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
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
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
                value={`$${result.cost_usd?.toFixed(3) || '0.00'}`}
              />
              <StatCard 
                icon={<Loader2 className="w-5 h-5 text-gray-600" />}
                label="Time"
                value={`${(result.processing_time_ms / 1000).toFixed(1)}s`}
              />
            </div>
            
            {/* Field Coverage */}
            {result.employees?.length > 0 && (
              <FieldCoverage employees={result.employees} />
            )}
            
            {/* Employee Table */}
            {result.employees?.length > 0 && (
              <div className="mt-6">
                <h3 className="font-semibold mb-3">Employee Data</h3>
                <div className="overflow-x-auto border rounded-lg">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="text-left p-3 font-medium">Name</th>
                        <th className="text-left p-3 font-medium">ID</th>
                        <th className="text-left p-3 font-medium">Department</th>
                        <th className="text-right p-3 font-medium">Gross</th>
                        <th className="text-right p-3 font-medium">Taxes</th>
                        <th className="text-right p-3 font-medium">Deductions</th>
                        <th className="text-right p-3 font-medium">Net</th>
                        <th className="text-center p-3 font-medium">Valid</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.employees.map((emp, i) => (
                        <tr key={i} className="border-t hover:bg-gray-50">
                          <td className="p-3 font-medium">{emp.name || <span className="text-red-400">Missing</span>}</td>
                          <td className="p-3 text-gray-600">{emp.id || '-'}</td>
                          <td className="p-3 text-gray-600">{emp.department || '-'}</td>
                          <td className="p-3 text-right">${emp.gross_pay?.toFixed(2) || '0.00'}</td>
                          <td className="p-3 text-right text-red-600">-${emp.total_taxes?.toFixed(2) || '0.00'}</td>
                          <td className="p-3 text-right text-orange-600">-${emp.total_deductions?.toFixed(2) || '0.00'}</td>
                          <td className="p-3 text-right font-semibold">${emp.net_pay?.toFixed(2) || '0.00'}</td>
                          <td className="p-3 text-center">
                            {emp.is_valid ? 
                              <CheckCircle className="w-4 h-4 text-green-500 mx-auto" /> : 
                              <XCircle className="w-4 h-4 text-red-500 mx-auto" title={emp.validation_errors?.join(', ')} />
                            }
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            
            {/* Validation Errors */}
            {result.validation_errors?.length > 0 && (
              <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <h4 className="font-medium text-amber-800 mb-2">Validation Notes</h4>
                <ul className="text-sm text-amber-700 space-y-1">
                  {result.validation_errors.slice(0, 10).map((err, i) => (
                    <li key={i}>• {err}</li>
                  ))}
                  {result.validation_errors.length > 10 && (
                    <li className="text-amber-600">... and {result.validation_errors.length - 10} more</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        )}
        
        {/* History Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Extraction History</h2>
          
          {extracts.length === 0 ? (
            <p className="text-gray-500 py-8 text-center">
              No extractions yet. Upload a pay register to get started.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left p-3 font-medium">File</th>
                    <th className="text-right p-3 font-medium">Employees</th>
                    <th className="text-right p-3 font-medium">Confidence</th>
                    <th className="text-right p-3 font-medium">Pages</th>
                    <th className="text-right p-3 font-medium">Cost</th>
                    <th className="text-left p-3 font-medium">Date</th>
                    <th className="text-center p-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {extracts.map((ext) => (
                    <tr key={ext.id} className="border-t hover:bg-gray-50">
                      <td className="p-3 font-medium">{ext.source_file}</td>
                      <td className="p-3 text-right">{ext.employee_count}</td>
                      <td className="p-3 text-right">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          ext.confidence >= 0.9 ? 'bg-green-100 text-green-700' :
                          ext.confidence >= 0.7 ? 'bg-yellow-100 text-yellow-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {(ext.confidence * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="p-3 text-right">{ext.pages_processed}</td>
                      <td className="p-3 text-right">${ext.cost_usd?.toFixed(3)}</td>
                      <td className="p-3 text-gray-600">
                        {new Date(ext.created_at).toLocaleDateString()} {new Date(ext.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </td>
                      <td className="p-3 text-center">
                        <button
                          onClick={() => viewExtract(ext.id)}
                          className="p-1.5 text-blue-600 hover:bg-blue-50 rounded mr-1"
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
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        
        {/* Detail Modal */}
        {selectedExtract && (
          <DetailModal 
            extract={selectedExtract} 
            onClose={() => setSelectedExtract(null)} 
          />
        )}
      </div>
    </div>
  );
}


// Stat Card Component
function StatCard({ icon, label, value }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-sm text-gray-600">{label}</span>
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}


// Field Coverage Component
function FieldCoverage({ employees }) {
  const [expanded, setExpanded] = useState(false);
  
  const fields = [
    { key: 'name', label: 'Employee Name', required: true },
    { key: 'id', label: 'Employee ID', required: true },
    { key: 'department', label: 'Department', required: false },
    { key: 'gross_pay', label: 'Gross Pay', required: true },
    { key: 'net_pay', label: 'Net Pay', required: true },
    { key: 'total_taxes', label: 'Total Taxes', required: true },
    { key: 'total_deductions', label: 'Total Deductions', required: false },
    { key: 'earnings', label: 'Earnings Breakdown', required: false, isArray: true },
    { key: 'taxes', label: 'Tax Breakdown', required: false, isArray: true },
    { key: 'deductions', label: 'Deduction Breakdown', required: false, isArray: true },
    { key: 'check_number', label: 'Check Number', required: false },
    { key: 'pay_method', label: 'Pay Method', required: false },
  ];
  
  const coverage = fields.map(field => {
    let populated = 0;
    employees.forEach(emp => {
      const value = emp[field.key];
      if (field.isArray) {
        if (value && Array.isArray(value) && value.length > 0) populated++;
      } else if (typeof value === 'number') {
        if (value > 0) populated++;
      } else {
        if (value && value.toString().trim()) populated++;
      }
    });
    
    return {
      ...field,
      populated,
      total: employees.length,
      percent: Math.round((populated / employees.length) * 100)
    };
  });
  
  const overallPercent = Math.round(
    coverage.reduce((sum, f) => sum + f.percent, 0) / coverage.length
  );
  
  return (
    <div className="border rounded-lg">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50"
      >
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          <span className="font-medium">Field Coverage</span>
          <span className={`px-2 py-0.5 rounded text-sm ${
            overallPercent >= 80 ? 'bg-green-100 text-green-700' :
            overallPercent >= 50 ? 'bg-yellow-100 text-yellow-700' :
            'bg-red-100 text-red-700'
          }`}>
            {overallPercent}% overall
          </span>
        </div>
        <span className="text-sm text-gray-500">
          {coverage.filter(f => f.percent === 100).length}/{coverage.length} fields complete
        </span>
      </button>
      
      {expanded && (
        <div className="border-t p-4">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {coverage.map((field, i) => (
              <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="flex items-center gap-2">
                  {field.required && <span className="text-red-500 text-xs">*</span>}
                  <span className="text-sm">{field.label}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-20 bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${
                        field.percent === 100 ? 'bg-green-500' :
                        field.percent >= 50 ? 'bg-yellow-500' :
                        field.percent > 0 ? 'bg-orange-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${field.percent}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-600 w-12 text-right">
                    {field.populated}/{field.total}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


// Detail Modal Component
function DetailModal({ extract, onClose }) {
  const employees = extract.employees || [];
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-gray-50">
          <div>
            <h2 className="text-xl font-semibold">{extract.source_file}</h2>
            <p className="text-sm text-gray-500">
              {employees.length} employees • {extract.pages_processed} pages • 
              {(extract.confidence * 100).toFixed(0)}% confidence
            </p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-200 rounded-lg text-gray-500"
          >
            ✕
          </button>
        </div>
        
        {/* Content */}
        <div className="p-4 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 80px)' }}>
          {employees.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No employees in this extraction</p>
          ) : (
            employees.map((emp, i) => (
              <EmployeeCard key={i} employee={emp} index={i} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}


// Employee Detail Card
function EmployeeCard({ employee, index }) {
  const [expanded, setExpanded] = useState(index === 0);
  
  return (
    <div className="border rounded-lg mb-3 overflow-hidden">
      {/* Summary Row */}
      <div 
        className={`flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 ${
          expanded ? 'bg-blue-50 border-b' : 'bg-gray-50'
        }`}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-medium">
            {index + 1}
          </div>
          <div>
            <div className="font-semibold">{employee.name || 'Unknown'}</div>
            <div className="text-sm text-gray-500">
              {employee.department || 'No Department'} 
              {employee.id && ` • ID: ${employee.id}`}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-6 text-right">
          <div>
            <div className="text-xs text-gray-500">Gross</div>
            <div className="font-semibold">${employee.gross_pay?.toFixed(2) || '0.00'}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Net</div>
            <div className="font-semibold text-green-600">${employee.net_pay?.toFixed(2) || '0.00'}</div>
          </div>
          <div className="text-gray-400">
            {expanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </div>
        </div>
      </div>
      
      {/* Expanded Details */}
      {expanded && (
        <div className="p-4 grid md:grid-cols-3 gap-6 text-sm bg-white">
          {/* Earnings */}
          <div>
            <h4 className="font-semibold mb-3 text-blue-600 flex items-center gap-2">
              <DollarSign className="w-4 h-4" /> Earnings
            </h4>
            {employee.earnings?.length > 0 ? (
              <>
                {employee.earnings.map((e, i) => (
                  <div key={i} className="flex justify-between py-1.5 border-b border-gray-100">
                    <span className="text-gray-700">{e.description}</span>
                    <span className="font-medium">
                      {e.hours ? (
                        <span className="text-gray-500 text-xs mr-2">
                          {e.hours}h @ ${e.rate}
                        </span>
                      ) : null}
                      ${e.amount?.toFixed(2)}
                    </span>
                  </div>
                ))}
                <div className="flex justify-between py-2 font-semibold text-blue-600">
                  <span>Gross Total</span>
                  <span>${employee.gross_pay?.toFixed(2)}</span>
                </div>
              </>
            ) : (
              <p className="text-gray-400 italic">No earnings breakdown</p>
            )}
          </div>
          
          {/* Taxes */}
          <div>
            <h4 className="font-semibold mb-3 text-red-600 flex items-center gap-2">
              <FileText className="w-4 h-4" /> Taxes
            </h4>
            {employee.taxes?.length > 0 ? (
              <>
                {employee.taxes.map((t, i) => (
                  <div key={i} className="flex justify-between py-1.5 border-b border-gray-100">
                    <span className="text-gray-700">{t.description}</span>
                    <span className="font-medium text-red-600">-${t.amount?.toFixed(2)}</span>
                  </div>
                ))}
                <div className="flex justify-between py-2 font-semibold text-red-600">
                  <span>Tax Total</span>
                  <span>-${employee.total_taxes?.toFixed(2)}</span>
                </div>
              </>
            ) : (
              <p className="text-gray-400 italic">No tax breakdown</p>
            )}
          </div>
          
          {/* Deductions */}
          <div>
            <h4 className="font-semibold mb-3 text-orange-600 flex items-center gap-2">
              <FileText className="w-4 h-4" /> Deductions
            </h4>
            {employee.deductions?.length > 0 ? (
              <>
                {employee.deductions.map((d, i) => (
                  <div key={i} className="flex justify-between py-1.5 border-b border-gray-100">
                    <span className="text-gray-700">{d.description}</span>
                    <span className="font-medium text-orange-600">-${d.amount?.toFixed(2)}</span>
                  </div>
                ))}
                <div className="flex justify-between py-2 font-semibold text-orange-600">
                  <span>Deduction Total</span>
                  <span>-${employee.total_deductions?.toFixed(2)}</span>
                </div>
              </>
            ) : (
              <p className="text-gray-400 italic">No deductions</p>
            )}
            
            {/* Pay Method */}
            {(employee.pay_method || employee.check_number) && (
              <div className="mt-4 pt-4 border-t">
                <div className="text-gray-500 text-xs mb-1">Payment</div>
                <div className="font-medium">
                  {employee.pay_method}
                  {employee.check_number && ` #${employee.check_number}`}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
