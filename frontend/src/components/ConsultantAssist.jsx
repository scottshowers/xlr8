/**
 * ConsultantAssist.jsx - Help Claude understand new register formats
 * 
 * POLISHED: All purple → grassGreen for consistency
 */

import React, { useState, useEffect } from 'react';
import { 
  HelpCircle, 
  X, 
  Save, 
  Eye, 
  Plus, 
  Trash2, 
  ChevronDown, 
  ChevronUp,
  Wand2,
  FileText,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { COLORS } from '../components/ui';

const API_BASE = import.meta.env.VITE_API_URL || '';
const BRAND = COLORS?.grassGreen || '#5a8a4a';
const BRAND_DARK = '#4a7a3a';
const BRAND_LIGHT = 'rgba(90, 138, 74, 0.1)';

export default function ConsultantAssist({ 
  extractionId, 
  sourceFile,
  vendorType, 
  customerId,
  confidence,
  validationErrors,
  onClose,
  onRetry 
}) {
  const [activeTab, setActiveTab] = useState('overview');
  const [rawText, setRawText] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [sections, setSections] = useState([
    { name: 'employee_header', label: 'Employee Header', startPattern: '', endPattern: '', description: 'Where employee info begins' },
    { name: 'earnings', label: 'Earnings', startPattern: '', endPattern: '', description: 'Earnings section' },
    { name: 'taxes', label: 'Taxes', startPattern: '', endPattern: '', description: 'Tax withholdings' },
    { name: 'deductions', label: 'Deductions', startPattern: '', endPattern: '', description: 'Deductions section' },
  ]);
  
  const [fields, setFields] = useState([]);
  const [newField, setNewField] = useState({ table_name: 'employees', field_name: '', field_label: '', field_type: 'text', pattern: '' });
  
  const [hints, setHints] = useState({
    layout: 'vertical',
    employeeMarker: '',
    pageBreakHandling: '',
    specialInstructions: ''
  });

  useEffect(() => {
    loadRawText();
    loadFieldDefinitions();
  }, [extractionId, sourceFile]);

  const loadRawText = async () => {
    setLoading(true);
    try {
      let res;
      if (extractionId) {
        res = await fetch(`${API_BASE}/api/vacuum/extract/${extractionId}/raw`);
      } else if (sourceFile) {
        res = await fetch(`${API_BASE}/api/vacuum/extract-by-file/${encodeURIComponent(sourceFile)}/raw`);
      } else {
        setRawText('No extraction ID or source file available.');
        setLoading(false);
        return;
      }
      
      if (res.ok) {
        const data = await res.json();
        setRawText(data.raw_text || 'No raw text available. Run an extraction first.');
      }
    } catch (err) {
      console.error('Failed to load raw text:', err);
      setRawText('Failed to load raw text');
    }
    setLoading(false);
  };

  const loadFieldDefinitions = async () => {
    try {
      const url = customerId 
        ? `${API_BASE}/api/vacuum/field-definitions?customer_id=${customerId}`
        : `${API_BASE}/api/vacuum/field-definitions?vendor_type=${vendorType}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setFields(data.fields || []);
      }
    } catch (err) {
      console.error('Failed to load field definitions:', err);
    }
  };

  const handleAddField = () => {
    if (!newField.field_name || !newField.field_label) return;
    
    setFields([...fields, { ...newField, id: `temp-${Date.now()}` }]);
    setNewField({ table_name: 'employees', field_name: '', field_label: '', field_type: 'text', pattern: '' });
  };

  const handleRemoveField = (index) => {
    setFields(fields.filter((_, i) => i !== index));
  };

  const handleSaveTemplate = async () => {
    setSaving(true);
    try {
      const templateData = {
        vendor_type: vendorType,
        customer_id: customerId,
        sections,
        fields,
        hints
      };
      
      const res = await fetch(`${API_BASE}/api/vacuum/assist/save-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(templateData)
      });
      
      if (res.ok) {
        alert('Template saved successfully!');
      } else {
        throw new Error('Failed to save template');
      }
    } catch (err) {
      console.error('Failed to save template:', err);
      alert('Failed to save template: ' + err.message);
    }
    setSaving(false);
  };

  const handleRetryWithHints = async () => {
    if (onRetry) {
      onRetry({
        sections,
        fields,
        hints
      });
    }
  };

  const needsHelp = confidence < 0.7 || (validationErrors && validationErrors.length > 0);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-[90vw] max-w-5xl h-[85vh] flex flex-col">
        {/* Header */}
        <div 
          className="flex items-center justify-between p-4 border-b text-white rounded-t-xl"
          style={{ background: `linear-gradient(135deg, ${BRAND}, ${BRAND_DARK})` }}
        >
          <div className="flex items-center gap-3">
            <Wand2 className="w-6 h-6" />
            <div>
              <h2 className="text-lg font-semibold">Consultant Assist</h2>
              <p className="text-sm" style={{ color: '#c6e7b8' }}>Help Claude understand this register format</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-lg transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Banner */}
        {needsHelp && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-3 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            <div className="text-sm">
              <span className="font-medium text-amber-800">Extraction needs attention: </span>
              <span className="text-amber-700">
                {confidence < 0.7 && `Low confidence (${Math.round(confidence * 100)}%)`}
                {confidence < 0.7 && validationErrors?.length > 0 && ' • '}
                {validationErrors?.length > 0 && `${validationErrors.length} validation errors`}
              </span>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b">
          {[
            { id: 'overview', label: 'Overview', icon: HelpCircle },
            { id: 'raw_text', label: 'Raw Text', icon: FileText },
            { id: 'sections', label: 'Sections', icon: ChevronDown },
            { id: 'fields', label: 'Custom Fields', icon: Plus },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors"
              style={activeTab === tab.id ? {
                borderColor: BRAND,
                color: BRAND
              } : {
                borderColor: 'transparent',
                color: '#6b7280'
              }}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6 max-w-2xl">
              <div className="p-4 rounded-lg" style={{ background: BRAND_LIGHT, border: `1px solid ${BRAND}40` }}>
                <h3 className="font-medium mb-2" style={{ color: BRAND }}>What is Consultant Assist?</h3>
                <p className="text-sm text-gray-600">
                  When Claude struggles to parse a new register format, you can use this tool to provide hints 
                  about the document structure. Your hints help Claude learn and improve extraction accuracy.
                </p>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-3">Quick Settings</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Register Layout
                    </label>
                    <select
                      value={hints.layout}
                      onChange={(e) => setHints({ ...hints, layout: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 text-sm"
                    >
                      <option value="vertical">Vertical (one employee per section)</option>
                      <option value="horizontal">Horizontal (table format)</option>
                      <option value="mixed">Mixed layout</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Employee Marker Pattern
                    </label>
                    <input
                      type="text"
                      value={hints.employeeMarker}
                      onChange={(e) => setHints({ ...hints, employeeMarker: e.target.value })}
                      placeholder="e.g., 'Employee:' or SSN pattern"
                      className="w-full border rounded-lg px-3 py-2 text-sm"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Special Instructions for Claude
                </label>
                <textarea
                  value={hints.specialInstructions}
                  onChange={(e) => setHints({ ...hints, specialInstructions: e.target.value })}
                  placeholder="Any other hints about this register format..."
                  rows={3}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </div>
          )}

          {/* Raw Text Tab */}
          {activeTab === 'raw_text' && (
            <div className="h-full">
              <div className="bg-gray-900 text-gray-100 rounded-lg p-4 h-full overflow-auto font-mono text-xs whitespace-pre-wrap">
                {loading ? (
                  <div className="text-gray-400">Loading raw text...</div>
                ) : (
                  rawText || 'No raw text available. Run an extraction first.'
                )}
              </div>
            </div>
          )}

          {/* Sections Tab */}
          {activeTab === 'sections' && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Define patterns that mark the start and end of each section in the register.
              </p>
              
              {sections.map((section, index) => (
                <div key={section.name} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium text-gray-900">{section.label}</h4>
                    <span className="text-xs text-gray-500">{section.description}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Start Pattern</label>
                      <input
                        type="text"
                        value={section.startPattern}
                        onChange={(e) => {
                          const updated = [...sections];
                          updated[index].startPattern = e.target.value;
                          setSections(updated);
                        }}
                        placeholder="e.g., 'Earnings:' or 'EARNINGS'"
                        className="w-full border rounded px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">End Pattern</label>
                      <input
                        type="text"
                        value={section.endPattern}
                        onChange={(e) => {
                          const updated = [...sections];
                          updated[index].endPattern = e.target.value;
                          setSections(updated);
                        }}
                        placeholder="e.g., 'Taxes:' or next section"
                        className="w-full border rounded px-3 py-2 text-sm"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Fields Tab */}
          {activeTab === 'fields' && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Define custom fields that are unique to this vendor or customer. These will be stored in the extra_fields column.
              </p>

              {/* Existing fields */}
              {fields.length > 0 && (
                <div className="border rounded-lg divide-y">
                  {fields.map((field, index) => (
                    <div key={field.id || index} className="flex items-center justify-between p-3">
                      <div className="flex items-center gap-4">
                        <span className="text-xs bg-gray-100 px-2 py-1 rounded">{field.table_name}</span>
                        <span className="font-medium text-sm">{field.field_label}</span>
                        <span className="text-xs text-gray-500">({field.field_name})</span>
                        <span 
                          className="text-xs px-2 py-1 rounded"
                          style={{ background: BRAND_LIGHT, color: BRAND }}
                        >
                          {field.field_type}
                        </span>
                      </div>
                      <button
                        onClick={() => handleRemoveField(index)}
                        className="p-1 text-red-500 hover:bg-red-50 rounded"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add new field */}
              <div className="border rounded-lg p-4 bg-gray-50">
                <h4 className="font-medium text-sm mb-3">Add Custom Field</h4>
                <div className="grid grid-cols-5 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Table</label>
                    <select
                      value={newField.table_name}
                      onChange={(e) => setNewField({ ...newField, table_name: e.target.value })}
                      className="w-full border rounded px-2 py-1.5 text-sm"
                    >
                      <option value="employees">Employees</option>
                      <option value="earnings">Earnings</option>
                      <option value="taxes">Taxes</option>
                      <option value="deductions">Deductions</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Field Name</label>
                    <input
                      type="text"
                      value={newField.field_name}
                      onChange={(e) => setNewField({ ...newField, field_name: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
                      placeholder="accrual_balance"
                      className="w-full border rounded px-2 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Display Label</label>
                    <input
                      type="text"
                      value={newField.field_label}
                      onChange={(e) => setNewField({ ...newField, field_label: e.target.value })}
                      placeholder="Accrual Balance"
                      className="w-full border rounded px-2 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
                    <select
                      value={newField.field_type}
                      onChange={(e) => setNewField({ ...newField, field_type: e.target.value })}
                      className="w-full border rounded px-2 py-1.5 text-sm"
                    >
                      <option value="text">Text</option>
                      <option value="number">Number</option>
                      <option value="decimal">Decimal</option>
                      <option value="date">Date</option>
                      <option value="boolean">Yes/No</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <button
                      onClick={handleAddField}
                      disabled={!newField.field_name || !newField.field_label}
                      className="w-full px-3 py-1.5 text-white rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1"
                      style={{ background: BRAND }}
                    >
                      <Plus className="w-4 h-4" /> Add
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t bg-gray-50 rounded-b-xl">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={handleSaveTemplate}
              disabled={saving}
              className="px-4 py-2 border rounded-lg flex items-center gap-2"
              style={{ borderColor: BRAND, color: BRAND }}
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Template'}
            </button>
            <button
              onClick={handleRetryWithHints}
              className="px-4 py-2 text-white rounded-lg flex items-center gap-2"
              style={{ background: BRAND }}
            >
              <Wand2 className="w-4 h-4" />
              Retry with Hints
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
