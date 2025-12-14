/**
 * CreateProject.jsx - Project Creation Modal
 * 
 * POLISHED: All blue → grassGreen for consistency
 */

import { useState } from 'react';
import { X, Plus, Loader2 } from 'lucide-react';
import api from '../services/api';
import { COLORS } from './ui';

const BRAND = COLORS?.grassGreen || '#83b16d';

export default function CreateProject({ onProjectCreated, onClose }) {
  const [name, setName] = useState('');
  const [customer, setCustomer] = useState('');
  const [projectType, setProjectType] = useState('Implementation');
  const [startDate, setStartDate] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!name.trim()) {
      setError('Project name required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.post('/projects/create', {
        name: name.trim(),
        customer: customer.trim() || null,
        type: projectType,
        start_date: startDate || null,
        notes: notes.trim() || null
      });
      
      onProjectCreated(response.data);
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  const inputClass = `w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:border-transparent`;
  const inputStyle = { '--tw-ring-color': BRAND };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">Create New Project</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Project Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Meyer Company Implementation"
              className={inputClass}
              style={inputStyle}
              disabled={loading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Customer Name
            </label>
            <input
              type="text"
              value={customer}
              onChange={(e) => setCustomer(e.target.value)}
              placeholder="Meyer Company"
              className={inputClass}
              style={inputStyle}
              disabled={loading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Project Type *
            </label>
            <select
              value={projectType}
              onChange={(e) => setProjectType(e.target.value)}
              className={inputClass}
              style={inputStyle}
              disabled={loading}
            >
              <option value="Implementation">Implementation</option>
              <option value="Post Launch Support">Post Launch Support</option>
              <option value="Assessment/Analysis">Assessment/Analysis</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className={inputClass}
              style={inputStyle}
              disabled={loading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="SECURE 2.0 implementation with payroll focus..."
              rows={3}
              className={inputClass}
              style={inputStyle}
              disabled={loading}
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
              {error}
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2 text-white font-medium rounded-lg flex items-center justify-center gap-2 disabled:opacity-50"
              style={{ background: loading ? '#9ca3af' : BRAND }}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Create Project
                </>
              )}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-6 py-2 bg-gray-200 hover:bg-gray-300 disabled:bg-gray-100 text-gray-700 font-medium rounded-lg"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
