/**
 * ReferenceManager.jsx
 * ====================
 * 
 * UI component for managing reference/standards documents.
 * 
 * Features:
 * - List all reference/global documents
 * - Delete individual references
 * - Clear all references
 * - View rule registry status
 * 
 * Deploy to: frontend/src/components/ReferenceManager.jsx
 * 
 * Add to your page/router:
 *   import ReferenceManager from './components/ReferenceManager';
 *   <ReferenceManager />
 */

import React, { useState, useEffect } from 'react';

const API_BASE = '/api';

export default function ReferenceManager() {
  const [references, setReferences] = useState([]);
  const [rulesInfo, setRulesInfo] = useState({ available: false, documents: 0, total_rules: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [showConfirmClearAll, setShowConfirmClearAll] = useState(false);

  // Fetch references
  const fetchReferences = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/status/references`);
      if (!response.ok) throw new Error('Failed to fetch references');
      const data = await response.json();
      setReferences(data.files || []);
      setRulesInfo(data.rules || { available: false, documents: 0, total_rules: 0 });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReferences();
  }, []);

  // Delete single reference
  const handleDelete = async (filename) => {
    if (!window.confirm(`Delete "${filename}"?\n\nThis will remove it from:\n- Document Registry\n- ChromaDB\n- Lineage\n- Rule Registry`)) {
      return;
    }

    setDeleting(filename);
    try {
      const response = await fetch(
        `${API_BASE}/status/references/${encodeURIComponent(filename)}?confirm=true`,
        { method: 'DELETE' }
      );
      if (!response.ok) throw new Error('Delete failed');
      const result = await response.json();
      console.log('Delete result:', result);
      await fetchReferences();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleting(null);
    }
  };

  // Clear all references
  const handleClearAll = async () => {
    setShowConfirmClearAll(false);
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/status/references?confirm=true`,
        { method: 'DELETE' }
      );
      if (!response.ok) throw new Error('Clear all failed');
      const result = await response.json();
      console.log('Clear all result:', result);
      await fetchReferences();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Format date
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Format file size
  const formatSize = (bytes) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reference Documents</h1>
          <p className="text-gray-600 mt-1">
            Manage global standards, regulations, and reference materials
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchReferences}
            disabled={loading}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 font-medium transition-colors"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
          {references.length > 0 && (
            <button
              onClick={() => setShowConfirmClearAll(true)}
              className="px-4 py-2 bg-red-100 hover:bg-red-200 rounded-lg text-red-700 font-medium transition-colors"
            >
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Rules Info Card */}
      {rulesInfo.available && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2 text-blue-800">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="font-medium">Rule Registry</span>
          </div>
          <p className="text-blue-700 mt-1">
            {rulesInfo.documents} document(s) with {rulesInfo.total_rules} extracted rules
          </p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-700">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-red-600 underline text-sm mt-1"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* References Table */}
      {loading && references.length === 0 ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : references.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <svg className="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-gray-600">No reference documents found</p>
          <p className="text-gray-500 text-sm mt-1">Upload standards or reference materials to see them here</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Filename</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Type</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Storage</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Size</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Created</th>
                <th className="text-right px-4 py-3 text-sm font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {references.map((ref) => (
                <tr key={ref.id || ref.filename} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{ref.filename}</div>
                    {ref.content_domain && ref.content_domain.length > 0 && (
                      <div className="flex gap-1 mt-1">
                        {ref.content_domain.slice(0, 3).map((domain, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded"
                          >
                            {domain}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      ref.truth_type === 'reference' 
                        ? 'bg-purple-100 text-purple-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}>
                      {ref.truth_type || 'global'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {ref.storage_type || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {formatSize(ref.file_size_bytes)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {formatDate(ref.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(ref.filename)}
                      disabled={deleting === ref.filename}
                      className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                        deleting === ref.filename
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                          : 'bg-red-50 text-red-600 hover:bg-red-100'
                      }`}
                    >
                      {deleting === ref.filename ? 'Deleting...' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary */}
      {references.length > 0 && (
        <div className="mt-4 text-sm text-gray-500">
          {references.length} reference document(s)
        </div>
      )}

      {/* Clear All Confirmation Modal */}
      {showConfirmClearAll && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md mx-4 shadow-xl">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Clear All References?</h3>
            <p className="text-gray-600 mb-4">
              This will permanently delete all {references.length} reference document(s) from:
            </p>
            <ul className="text-sm text-gray-600 mb-4 space-y-1">
              <li>• Document Registry (Supabase)</li>
              <li>• Vector Store (ChromaDB)</li>
              <li>• Lineage Tracking</li>
              <li>• Rule Registry</li>
            </ul>
            <p className="text-red-600 font-medium text-sm mb-4">
              This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirmClearAll(false)}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleClearAll}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-white font-medium"
              >
                Yes, Clear All
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
