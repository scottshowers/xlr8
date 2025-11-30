/**
 * Vacuum Page - Pay Register Extraction
 * 
 * Simple, functional interface for:
 * - Uploading pay registers
 * - Viewing extraction results
 * - Exploring employee data
 * 
 * Deploy to: frontend/src/pages/VacuumPage.jsx
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Upload, FileText, Users, DollarSign, CheckCircle, XCircle, Loader2, Trash2, Eye } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function VacuumPage() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [extracts, setExtracts] = useState([]);
  const [selectedExtract, setSelectedExtract] = useState(null);
  const [error, setError] = useState(null);
  const [maxPages, setMaxPages] = useState(3);

  // Load extraction history
  const loadExtracts = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/vacuum/extracts`);
      const data = await res.json();
      setExtracts(data.extracts || []);
    } catch (err) {
      console.error('Failed to load extracts:', err);
    }
  }, []);

  useEffect(() => {
    loadExtracts();
  }, [loadExtracts]);

  // Handle file upload
  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    setError(null);
    setResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('max_pages', maxPages.toString());
      
      const res = await fetch(`${API_BASE}/api/vacuum/upload`, {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed');
      }
      
      setResult(data);
      loadExtracts(); // Refresh history
      
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
        <h1 className="text-3xl font-bold text-gray-900 mb-6">
          Pay Register Extraction
        </h1>
        
        {/* Upload Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Upload Pay Register</h2>
          
          <div className="flex flex-wrap gap-4 items-end">
            {/* File Input */}
            <div className="flex-1 min-w-64">
              <label className="block text-sm text-gray-600 mb-1">PDF File</label>
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            
            {/* Max Pages */}
            <div className="w-32">
              <label className="block text-sm text-gray-600 mb-1">Max Pages</label>
              <input
                type="number"
                value={maxPages}
                onChange={(e) => setMaxPages(parseInt(e.target.value) || 3)}
                min={1}
                max={50}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            
            {/* Upload Button */}
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {uploading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Processing...</>
              ) : (
                <><Upload className="w-4 h-4" /> Extract</>
              )}
            </button>
          </div>
          
          {/* Cost Estimate */}
          <p className="text-sm text-gray-500 mt-2">
            Estimated cost: ${(maxPages * 0.015 + 0.05).toFixed(2)} ({maxPages} pages × $0.015 + $0.05 Claude)
          </p>
          
          {/* Error */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700">
              {error}
            </div>
          )}
        </div>
        
        {/* Results Section */}
        {result && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Extraction Results</h2>
              <span className={`px-3 py-1 rounded-full text-sm ${
                result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
                {result.success ? 'Success' : 'Failed'}
              </span>
            </div>
            
            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
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
            </div>
            
            {/* Employee Table */}
            {result.employees?.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-3">Name</th>
                      <th className="text-left p-3">ID</th>
                      <th className="text-left p-3">Department</th>
                      <th className="text-right p-3">Gross</th>
                      <th className="text-right p-3">Taxes</th>
                      <th className="text-right p-3">Deductions</th>
                      <th className="text-right p-3">Net</th>
                      <th className="text-center p-3">Valid</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.employees.map((emp, i) => (
                      <tr key={i} className="border-t hover:bg-gray-50">
                        <td className="p-3 font-medium">{emp.name}</td>
                        <td className="p-3 text-gray-600">{emp.id}</td>
                        <td className="p-3 text-gray-600">{emp.department}</td>
                        <td className="p-3 text-right">${emp.gross_pay?.toFixed(2)}</td>
                        <td className="p-3 text-right text-red-600">-${emp.total_taxes?.toFixed(2)}</td>
                        <td className="p-3 text-right text-orange-600">-${emp.total_deductions?.toFixed(2)}</td>
                        <td className="p-3 text-right font-semibold">${emp.net_pay?.toFixed(2)}</td>
                        <td className="p-3 text-center">
                          {emp.is_valid ? 
                            <CheckCircle className="w-4 h-4 text-green-500 mx-auto" /> : 
                            <XCircle className="w-4 h-4 text-red-500 mx-auto" />
                          }
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
        
        {/* History Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Extraction History</h2>
          
          {extracts.length === 0 ? (
            <p className="text-gray-500">No extractions yet</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3">File</th>
                    <th className="text-right p-3">Employees</th>
                    <th className="text-right p-3">Confidence</th>
                    <th className="text-right p-3">Pages</th>
                    <th className="text-right p-3">Cost</th>
                    <th className="text-left p-3">Date</th>
                    <th className="text-center p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {extracts.map((ext) => (
                    <tr key={ext.id} className="border-t hover:bg-gray-50">
                      <td className="p-3">{ext.source_file}</td>
                      <td className="p-3 text-right">{ext.employee_count}</td>
                      <td className="p-3 text-right">{(ext.confidence * 100).toFixed(0)}%</td>
                      <td className="p-3 text-right">{ext.pages_processed}</td>
                      <td className="p-3 text-right">${ext.cost_usd?.toFixed(3)}</td>
                      <td className="p-3 text-gray-600">
                        {new Date(ext.created_at).toLocaleDateString()}
                      </td>
                      <td className="p-3 text-center">
                        <button
                          onClick={() => viewExtract(ext.id)}
                          className="p-1 text-blue-600 hover:bg-blue-50 rounded mr-2"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => deleteExtract(ext.id)}
                          className="p-1 text-red-600 hover:bg-red-50 rounded"
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


// Detail Modal Component
function DetailModal({ extract, onClose }) {
  const employees = extract.employees || [];
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h2 className="text-xl font-semibold">{extract.source_file}</h2>
            <p className="text-sm text-gray-500">
              {employees.length} employees • {extract.pages_processed} pages
            </p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded"
          >
            ✕
          </button>
        </div>
        
        {/* Content */}
        <div className="p-4 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 120px)' }}>
          {employees.map((emp, i) => (
            <EmployeeCard key={i} employee={emp} />
          ))}
        </div>
      </div>
    </div>
  );
}


// Employee Detail Card
function EmployeeCard({ employee }) {
  const [expanded, setExpanded] = useState(false);
  
  return (
    <div className="border rounded-lg mb-3 overflow-hidden">
      {/* Summary Row */}
      <div 
        className="flex items-center justify-between p-4 bg-gray-50 cursor-pointer hover:bg-gray-100"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          <div>
            <div className="font-semibold">{employee.name}</div>
            <div className="text-sm text-gray-500">{employee.department} • {employee.id}</div>
          </div>
        </div>
        <div className="flex items-center gap-6 text-right">
          <div>
            <div className="text-sm text-gray-500">Gross</div>
            <div className="font-semibold">${employee.gross_pay?.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Net</div>
            <div className="font-semibold text-green-600">${employee.net_pay?.toFixed(2)}</div>
          </div>
          <div className="text-gray-400">{expanded ? '▲' : '▼'}</div>
        </div>
      </div>
      
      {/* Expanded Details */}
      {expanded && (
        <div className="p-4 grid md:grid-cols-3 gap-4 text-sm">
          {/* Earnings */}
          <div>
            <h4 className="font-semibold mb-2 text-blue-600">Earnings</h4>
            {employee.earnings?.map((e, i) => (
              <div key={i} className="flex justify-between py-1 border-b">
                <span>{e.description}</span>
                <span>
                  {e.hours && `${e.hours}h @ $${e.rate} = `}
                  ${e.amount?.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
          
          {/* Taxes */}
          <div>
            <h4 className="font-semibold mb-2 text-red-600">Taxes</h4>
            {employee.taxes?.map((t, i) => (
              <div key={i} className="flex justify-between py-1 border-b">
                <span>{t.description}</span>
                <span>-${t.amount?.toFixed(2)}</span>
              </div>
            ))}
            <div className="flex justify-between py-1 font-semibold">
              <span>Total</span>
              <span>-${employee.total_taxes?.toFixed(2)}</span>
            </div>
          </div>
          
          {/* Deductions */}
          <div>
            <h4 className="font-semibold mb-2 text-orange-600">Deductions</h4>
            {employee.deductions?.map((d, i) => (
              <div key={i} className="flex justify-between py-1 border-b">
                <span>{d.description}</span>
                <span>-${d.amount?.toFixed(2)}</span>
              </div>
            ))}
            <div className="flex justify-between py-1 font-semibold">
              <span>Total</span>
              <span>-${employee.total_deductions?.toFixed(2)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
