/**
 * Vacuum Upload Page - Pay Register Extraction v9
 * Deploy to: frontend/src/pages/VacuumUploadPage.jsx
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Upload, FileText, Users, DollarSign, CheckCircle, XCircle, Loader2, Trash2, Eye, AlertTriangle, ChevronDown, ChevronRight, Download, Cpu } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function VacuumUploadPage() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [result, setResult] = useState(null);
  const [extracts, setExtracts] = useState([]);
  const [selectedExtract, setSelectedExtract] = useState(null);
  const [error, setError] = useState(null);
  const [maxPages, setMaxPages] = useState(3);
  const [useLocalLLM, setUseLocalLLM] = useState(false);

  useEffect(() => {
    const loadProjects = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/projects/list`);
        if (!res.ok) { setProjects([]); return; }
        const data = await res.json();
        if (Array.isArray(data)) setProjects(data);
        else if (data.projects && Array.isArray(data.projects)) setProjects(data.projects);
        else setProjects([]);
      } catch (err) { setProjects([]); }
    };
    loadProjects();
  }, []);

  const loadExtracts = useCallback(async () => {
    try {
      const url = selectedProject ? `${API_BASE}/api/vacuum/extracts?project_id=${selectedProject}` : `${API_BASE}/api/vacuum/extracts`;
      const res = await fetch(url);
      const data = await res.json();
      setExtracts(data.extracts || []);
    } catch (err) { console.error('Failed to load extracts:', err); }
  }, [selectedProject]);

  useEffect(() => { loadExtracts(); }, [loadExtracts]);

  const handleUpload = async () => {
    if (!file) { setError('Please select a file'); return; }
    if (!selectedProject) { setError('Please select a project'); return; }
    
    setUploading(true);
    setError(null);
    setResult(null);
    setUploadStatus(`Processing ${maxPages} pages... This may take 1-2 minutes.`);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('max_pages', maxPages.toString());
      formData.append('project_id', selectedProject);
      formData.append('use_local_llm', useLocalLLM ? 'true' : 'false');
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000);
      
      const res = await fetch(`${API_BASE}/api/vacuum/upload`, {
        method: 'POST',
        body: formData,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch (parseErr) {
        throw new Error('Server returned invalid response. Check extraction history - it may have completed.');
      }
      
      if (data.validation_errors) {
        data.validation_errors = data.validation_errors.filter(
          err => !err.toLowerCase().includes('strategy') && !err.toLowerCase().includes('failed:') && !err.toLowerCase().includes('parse error')
        );
      }
      
      if (!res.ok && !data.success) throw new Error(data.error || data.detail || 'Upload failed');
      
      setResult(data);
      setUploadStatus('');
      loadExtracts();
    } catch (err) {
      if (err.name === 'AbortError') setError('Request timed out. Check extraction history.');
      else setError(err.message);
      setUploadStatus('');
      loadExtracts();
    } finally {
      setUploading(false);
    }
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

  const exportToCSV = (employees, filename = 'pay_extract') => {
    if (!employees || employees.length === 0) { alert('No data to export'); return; }
    let csv = 'EMPLOYEE SUMMARY\nName,Employee ID,Department,Gross Pay,Net Pay,Total Taxes,Total Deductions,Pay Method,Check Number,Valid\n';
    employees.forEach(emp => {
      csv += `"${emp.name || ''}","${emp.id || emp.employee_id || ''}","${emp.department || ''}",${emp.gross_pay?.toFixed(2) || '0.00'},${emp.net_pay?.toFixed(2) || '0.00'},${emp.total_taxes?.toFixed(2) || '0.00'},${emp.total_deductions?.toFixed(2) || '0.00'},"${emp.pay_method || ''}","${emp.check_number || ''}",${emp.is_valid ? 'Yes' : 'No'}\n`;
    });
    csv += '\nEARNINGS DETAIL\nEmployee Name,Employee ID,Earning Type,Rate,Hours,Amount\n';
    employees.forEach(emp => {
      (emp.earnings || []).forEach(e => { csv += `"${emp.name || ''}","${emp.id || emp.employee_id || ''}","${e.description || ''}",${e.rate || ''},${e.hours || ''},${e.amount?.toFixed(2) || '0.00'}\n`; });
    });
    csv += '\nTAXES DETAIL\nEmployee Name,Employee ID,Tax Type,Amount\n';
    employees.forEach(emp => {
      (emp.taxes || []).forEach(t => { csv += `"${emp.name || ''}","${emp.id || emp.employee_id || ''}","${t.description || ''}",${t.amount?.toFixed(2) || '0.00'}\n`; });
    });
    csv += '\nDEDUCTIONS DETAIL\nEmployee Name,Employee ID,Deduction Type,Amount\n';
    employees.forEach(emp => {
      (emp.deductions || []).forEach(d => { csv += `"${emp.name || ''}","${emp.id || emp.employee_id || ''}","${d.description || ''}",${d.amount?.toFixed(2) || '0.00'}\n`; });
    });
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${filename}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const exportToExcel = (employees, filename = 'pay_extract') => {
    if (!employees || employees.length === 0) { alert('No data to export'); return; }
    const esc = (s) => (s || '').toString().replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    let xml = '<?xml version="1.0"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">';
    xml += '<Styles><Style ss:ID="H"><Font ss:Bold="1"/></Style><Style ss:ID="C"><NumberFormat ss:Format="$#,##0.00"/></Style></Styles>';
    
    xml += '<Worksheet ss:Name="Summary"><Table>';
    xml += '<Row><Cell ss:StyleID="H"><Data ss:Type="String">Name</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">ID</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Dept</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Gross</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Net</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Taxes</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Deductions</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Pay Method</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Valid</Data></Cell></Row>';
    employees.forEach(emp => {
      xml += `<Row><Cell><Data ss:Type="String">${esc(emp.name)}</Data></Cell><Cell><Data ss:Type="String">${esc(emp.id||emp.employee_id)}</Data></Cell><Cell><Data ss:Type="String">${esc(emp.department)}</Data></Cell><Cell ss:StyleID="C"><Data ss:Type="Number">${emp.gross_pay||0}</Data></Cell><Cell ss:StyleID="C"><Data ss:Type="Number">${emp.net_pay||0}</Data></Cell><Cell ss:StyleID="C"><Data ss:Type="Number">${emp.total_taxes||0}</Data></Cell><Cell ss:StyleID="C"><Data ss:Type="Number">${emp.total_deductions||0}</Data></Cell><Cell><Data ss:Type="String">${esc(emp.pay_method)}</Data></Cell><Cell><Data ss:Type="String">${emp.is_valid?'Yes':'No'}</Data></Cell></Row>`;
    });
    xml += '</Table></Worksheet>';
    
    xml += '<Worksheet ss:Name="Earnings"><Table>';
    xml += '<Row><Cell ss:StyleID="H"><Data ss:Type="String">Employee</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">ID</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Type</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Rate</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Hours</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Amount</Data></Cell></Row>';
    employees.forEach(emp => {
      (emp.earnings||[]).forEach(e => {
        xml += `<Row><Cell><Data ss:Type="String">${esc(emp.name)}</Data></Cell><Cell><Data ss:Type="String">${esc(emp.id||emp.employee_id)}</Data></Cell><Cell><Data ss:Type="String">${esc(e.description)}</Data></Cell><Cell ss:StyleID="C"><Data ss:Type="Number">${e.rate||0}</Data></Cell><Cell><Data ss:Type="Number">${e.hours||0}</Data></Cell><Cell ss:StyleID="C"><Data ss:Type="Number">${e.amount||0}</Data></Cell></Row>`;
      });
    });
    xml += '</Table></Worksheet>';
    
    xml += '<Worksheet ss:Name="Taxes"><Table>';
    xml += '<Row><Cell ss:StyleID="H"><Data ss:Type="String">Employee</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">ID</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Tax Type</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Amount</Data></Cell></Row>';
    employees.forEach(emp => {
      (emp.taxes||[]).forEach(t => {
        xml += `<Row><Cell><Data ss:Type="String">${esc(emp.name)}</Data></Cell><Cell><Data ss:Type="String">${esc(emp.id||emp.employee_id)}</Data></Cell><Cell><Data ss:Type="String">${esc(t.description)}</Data></Cell><Cell ss:StyleID="C"><Data ss:Type="Number">${t.amount||0}</Data></Cell></Row>`;
      });
    });
    xml += '</Table></Worksheet>';
    
    xml += '<Worksheet ss:Name="Deductions"><Table>';
    xml += '<Row><Cell ss:StyleID="H"><Data ss:Type="String">Employee</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">ID</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Deduction Type</Data></Cell><Cell ss:StyleID="H"><Data ss:Type="String">Amount</Data></Cell></Row>';
    employees.forEach(emp => {
      (emp.deductions||[]).forEach(d => {
        xml += `<Row><Cell><Data ss:Type="String">${esc(emp.name)}</Data></Cell><Cell><Data ss:Type="String">${esc(emp.id||emp.employee_id)}</Data></Cell><Cell><Data ss:Type="String">${esc(d.description)}</Data></Cell><Cell ss:StyleID="C"><Data ss:Type="Number">${d.amount||0}</Data></Cell></Row>`;
      });
    });
    xml += '</Table></Worksheet></Workbook>';
    
    const blob = new Blob([xml], { type: 'application/vnd.ms-excel' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${filename}_${new Date().toISOString().split('T')[0]}.xls`;
    link.click();
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Pay Register Extraction</h1>
        <p className="text-gray-600 mb-6">Upload pay registers to extract employee data using AI-powered parsing</p>
        
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Upload Pay Register</h2>
          <div className="grid md:grid-cols-5 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Project <span className="text-red-500">*</span></label>
              <select value={selectedProject} onChange={(e) => setSelectedProject(e.target.value)} disabled={uploading} className="w-full border rounded-lg px-3 py-2">
                <option value="">Select a project...</option>
                {projects.map(p => <option key={p.id} value={p.id}>{p.name} {p.customer ? `(${p.customer})` : ''}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">PDF File <span className="text-red-500">*</span></label>
              <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} disabled={uploading} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Pages</label>
              <input type="number" value={maxPages} onChange={(e) => setMaxPages(parseInt(e.target.value) || 3)} min={1} max={500} disabled={uploading} className="w-full border rounded-lg px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">LLM</label>
              <button onClick={() => setUseLocalLLM(!useLocalLLM)} disabled={uploading} className={`w-full px-3 py-2 rounded-lg border flex items-center justify-center gap-2 ${useLocalLLM ? 'bg-purple-100 border-purple-300 text-purple-700' : 'bg-gray-50 border-gray-300 text-gray-600'}`}>
                <Cpu className="w-4 h-4" />{useLocalLLM ? 'Local' : 'Claude'}
              </button>
            </div>
            <div className="flex items-end">
              <button onClick={handleUpload} disabled={!file || !selectedProject || uploading} className="w-full px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2">
                {uploading ? <><Loader2 className="w-4 h-4 animate-spin" /> Processing...</> : <><Upload className="w-4 h-4" /> Extract</>}
              </button>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span>Est. cost: <strong>${(maxPages * 0.015 + (useLocalLLM ? 0 : 0.05)).toFixed(2)}</strong></span>
            <span className="text-gray-300">|</span>
            <span>{maxPages} pages × $0.015 {useLocalLLM ? '(no AI cost)' : '+ ~$0.05 AI'}</span>
          </div>
          {uploadStatus && <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 flex items-center gap-2"><Loader2 className="w-5 h-5 animate-spin" />{uploadStatus}</div>}
          {error && <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-2"><AlertTriangle className="w-5 h-5" />{error}</div>}
        </div>
        
        {result && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Extraction Results</h2>
              <div className="flex items-center gap-3">
                {result.employees?.length > 0 && <>
                  <button onClick={() => exportToCSV(result.employees, result.source_file?.replace('.pdf', ''))} className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 flex items-center gap-1"><Download className="w-4 h-4" /> CSV</button>
                  <button onClick={() => exportToExcel(result.employees, result.source_file?.replace('.pdf', ''))} className="px-3 py-1.5 text-sm bg-emerald-600 text-white rounded hover:bg-emerald-700 flex items-center gap-1"><Download className="w-4 h-4" /> Excel</button>
                </>}
                {result.saved_to_db && <span className="text-sm text-green-600 flex items-center gap-1"><CheckCircle className="w-4 h-4" /> Saved</span>}
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>{result.success ? 'Success' : 'Needs Review'}</span>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
              <StatCard icon={<Users className="w-5 h-5 text-blue-600" />} label="Employees" value={result.employee_count} />
              <StatCard icon={<FileText className="w-5 h-5 text-purple-600" />} label="Pages" value={result.pages_processed} />
              <StatCard icon={<CheckCircle className="w-5 h-5 text-green-600" />} label="Confidence" value={`${(result.confidence * 100).toFixed(0)}%`} />
              <StatCard icon={<DollarSign className="w-5 h-5 text-amber-600" />} label="Cost" value={`$${result.cost_usd?.toFixed(3) || '0.00'}`} />
              <StatCard icon={<Loader2 className="w-5 h-5 text-gray-600" />} label="Time" value={`${(result.processing_time_ms / 1000).toFixed(1)}s`} />
            </div>
            {result.employees?.length > 0 && <FieldCoverage employees={result.employees} />}
            {result.employees?.length > 0 && (
              <div className="mt-6">
                <h3 className="font-semibold mb-3">Employee Data</h3>
                <div className="overflow-x-auto border rounded-lg">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="text-left p-3 font-medium">Name</th><th className="text-left p-3 font-medium">ID</th><th className="text-left p-3 font-medium">Department</th>
                        <th className="text-right p-3 font-medium">Gross</th><th className="text-right p-3 font-medium">Taxes</th><th className="text-right p-3 font-medium">Deductions</th><th className="text-right p-3 font-medium">Net</th><th className="text-center p-3 font-medium">Valid</th>
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
                          <td className="p-3 text-center">{emp.is_valid ? <CheckCircle className="w-4 h-4 text-green-500 mx-auto" /> : <XCircle className="w-4 h-4 text-red-500 mx-auto" />}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {result.validation_errors?.length > 0 && (
              <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <h4 className="font-medium text-amber-800 mb-2">Validation Notes</h4>
                <ul className="text-sm text-amber-700 space-y-1">{result.validation_errors.slice(0, 10).map((err, i) => <li key={i}>• {err}</li>)}</ul>
              </div>
            )}
          </div>
        )}
        
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Extraction History</h2>
          {extracts.length === 0 ? <p className="text-gray-500 py-8 text-center">No extractions yet.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr><th className="text-left p-3 font-medium">File</th><th className="text-right p-3 font-medium">Employees</th><th className="text-right p-3 font-medium">Confidence</th><th className="text-right p-3 font-medium">Pages</th><th className="text-right p-3 font-medium">Cost</th><th className="text-left p-3 font-medium">Date</th><th className="text-center p-3 font-medium">Actions</th></tr>
                </thead>
                <tbody>
                  {extracts.map((ext) => (
                    <tr key={ext.id} className="border-t hover:bg-gray-50">
                      <td className="p-3 font-medium">{ext.source_file}</td>
                      <td className="p-3 text-right">{ext.employee_count}</td>
                      <td className="p-3 text-right"><span className={`px-2 py-0.5 rounded text-xs ${ext.confidence >= 0.9 ? 'bg-green-100 text-green-700' : ext.confidence >= 0.7 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>{(ext.confidence * 100).toFixed(0)}%</span></td>
                      <td className="p-3 text-right">{ext.pages_processed}</td>
                      <td className="p-3 text-right">${ext.cost_usd?.toFixed(3)}</td>
                      <td className="p-3 text-gray-600">{new Date(ext.created_at).toLocaleDateString()}</td>
                      <td className="p-3 text-center">
                        <button onClick={() => viewExtract(ext.id)} className="p-1.5 text-blue-600 hover:bg-blue-50 rounded mr-1"><Eye className="w-4 h-4" /></button>
                        <button onClick={() => deleteExtract(ext.id)} className="p-1.5 text-red-600 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        {selectedExtract && <DetailModal extract={selectedExtract} onClose={() => setSelectedExtract(null)} onExportCSV={exportToCSV} onExportExcel={exportToExcel} />}
      </div>
    </div>
  );
}

function StatCard({ icon, label, value }) {
  return <div className="bg-gray-50 rounded-lg p-4"><div className="flex items-center gap-2 mb-1">{icon}<span className="text-sm text-gray-600">{label}</span></div><div className="text-2xl font-bold">{value}</div></div>;
}

function FieldCoverage({ employees }) {
  const [expanded, setExpanded] = useState(false);
  const fields = [
    { key: 'name', label: 'Name', required: true }, { key: 'id', label: 'ID', required: true }, { key: 'department', label: 'Dept', required: false },
    { key: 'gross_pay', label: 'Gross', required: true }, { key: 'net_pay', label: 'Net', required: true }, { key: 'total_taxes', label: 'Taxes', required: true },
    { key: 'total_deductions', label: 'Deductions', required: false }, { key: 'earnings', label: 'Earnings Detail', required: false, isArray: true },
    { key: 'taxes', label: 'Tax Detail', required: false, isArray: true }, { key: 'deductions', label: 'Deduction Detail', required: false, isArray: true },
    { key: 'check_number', label: 'Check #', required: false }, { key: 'pay_method', label: 'Pay Method', required: false },
  ];
  const coverage = fields.map(f => {
    let pop = 0;
    employees.forEach(emp => {
      const v = emp[f.key];
      if (f.isArray) { if (v && Array.isArray(v) && v.length > 0) pop++; }
      else if (typeof v === 'number') { if (v > 0) pop++; }
      else { if (v && v.toString().trim()) pop++; }
    });
    return { ...f, populated: pop, total: employees.length, percent: Math.round((pop / employees.length) * 100) };
  });
  const overall = Math.round(coverage.reduce((s, f) => s + f.percent, 0) / coverage.length);
  return (
    <div className="border rounded-lg">
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center justify-between p-4 hover:bg-gray-50">
        <div className="flex items-center gap-3">{expanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}<span className="font-medium">Field Coverage</span><span className={`px-2 py-0.5 rounded text-sm ${overall >= 80 ? 'bg-green-100 text-green-700' : overall >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>{overall}%</span></div>
        <span className="text-sm text-gray-500">{coverage.filter(f => f.percent === 100).length}/{coverage.length} complete</span>
      </button>
      {expanded && <div className="border-t p-4"><div className="grid md:grid-cols-3 gap-3">{coverage.map((f, i) => (
        <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
          <span className="text-sm">{f.required && <span className="text-red-500">*</span>}{f.label}</span>
          <div className="flex items-center gap-2"><div className="w-16 bg-gray-200 rounded-full h-2"><div className={`h-2 rounded-full ${f.percent === 100 ? 'bg-green-500' : f.percent >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`} style={{ width: `${f.percent}%` }} /></div><span className="text-xs text-gray-600">{f.populated}/{f.total}</span></div>
        </div>
      ))}</div></div>}
    </div>
  );
}

function DetailModal({ extract, onClose, onExportCSV, onExportExcel }) {
  const employees = extract.employees || [];
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b bg-gray-50">
          <div><h2 className="text-xl font-semibold">{extract.source_file}</h2><p className="text-sm text-gray-500">{employees.length} employees • {extract.pages_processed} pages • {(extract.confidence * 100).toFixed(0)}%</p></div>
          <div className="flex items-center gap-2">
            {employees.length > 0 && <><button onClick={() => onExportCSV(employees, extract.source_file?.replace('.pdf', ''))} className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 flex items-center gap-1"><Download className="w-4 h-4" /> CSV</button><button onClick={() => onExportExcel(employees, extract.source_file?.replace('.pdf', ''))} className="px-3 py-1.5 text-sm bg-emerald-600 text-white rounded hover:bg-emerald-700 flex items-center gap-1"><Download className="w-4 h-4" /> Excel</button></>}
            <button onClick={onClose} className="p-2 hover:bg-gray-200 rounded-lg">✕</button>
          </div>
        </div>
        <div className="p-4 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 80px)' }}>{employees.length === 0 ? <p className="text-gray-500 text-center py-8">No employees</p> : employees.map((emp, i) => <EmployeeCard key={i} employee={emp} index={i} />)}</div>
      </div>
    </div>
  );
}

function EmployeeCard({ employee, index }) {
  const [expanded, setExpanded] = useState(index === 0);
  return (
    <div className="border rounded-lg mb-3 overflow-hidden">
      <div className={`flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 ${expanded ? 'bg-blue-50 border-b' : 'bg-gray-50'}`} onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-medium">{index + 1}</div>
          <div><div className="font-semibold">{employee.name || 'Unknown'}</div><div className="text-sm text-gray-500">{employee.department || ''}{employee.id && ` • ${employee.id}`}</div></div>
        </div>
        <div className="flex items-center gap-6 text-right">
          <div><div className="text-xs text-gray-500">Gross</div><div className="font-semibold">${employee.gross_pay?.toFixed(2) || '0.00'}</div></div>
          <div><div className="text-xs text-gray-500">Net</div><div className="font-semibold text-green-600">${employee.net_pay?.toFixed(2) || '0.00'}</div></div>
          {expanded ? <ChevronDown className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />}
        </div>
      </div>
      {expanded && (
        <div className="p-4 grid md:grid-cols-3 gap-6 text-sm bg-white">
          <div><h4 className="font-semibold mb-3 text-blue-600"><DollarSign className="w-4 h-4 inline" /> Earnings</h4>{employee.earnings?.length > 0 ? <>{employee.earnings.map((e, i) => <div key={i} className="flex justify-between py-1 border-b border-gray-100"><span>{e.description}</span><span>${e.amount?.toFixed(2)}</span></div>)}<div className="flex justify-between py-2 font-semibold text-blue-600"><span>Total</span><span>${employee.gross_pay?.toFixed(2)}</span></div></> : <p className="text-gray-400 italic">No detail</p>}</div>
          <div><h4 className="font-semibold mb-3 text-red-600"><FileText className="w-4 h-4 inline" /> Taxes</h4>{employee.taxes?.length > 0 ? <>{employee.taxes.map((t, i) => <div key={i} className="flex justify-between py-1 border-b border-gray-100"><span>{t.description}</span><span className="text-red-600">-${t.amount?.toFixed(2)}</span></div>)}<div className="flex justify-between py-2 font-semibold text-red-600"><span>Total</span><span>-${employee.total_taxes?.toFixed(2)}</span></div></> : <p className="text-gray-400 italic">No detail</p>}</div>
          <div><h4 className="font-semibold mb-3 text-orange-600"><FileText className="w-4 h-4 inline" /> Deductions</h4>{employee.deductions?.length > 0 ? <>{employee.deductions.map((d, i) => <div key={i} className="flex justify-between py-1 border-b border-gray-100"><span>{d.description}</span><span className="text-orange-600">-${d.amount?.toFixed(2)}</span></div>)}<div className="flex justify-between py-2 font-semibold text-orange-600"><span>Total</span><span>-${employee.total_deductions?.toFixed(2)}</span></div></> : <p className="text-gray-400 italic">No detail</p>}{employee.pay_method && <div className="mt-4 pt-4 border-t"><div className="text-xs text-gray-500">Payment</div><div className="font-medium">{employee.pay_method}{employee.check_number && ` #${employee.check_number}`}</div></div>}</div>
        </div>
      )}
    </div>
  );
}
