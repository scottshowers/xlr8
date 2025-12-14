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

const API_BASE = import.meta.env.VITE_API_URL || '';

/**
 * ConsultantAssist - Help Claude understand new register formats
 * 
 * Features:
 * - View raw extracted text
 * - Define section markers (where employees start/end)
 * - Map fields to patterns
 * - Add custom fields
 * - Save templates for reuse
 */
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
  const [activeTab, setActiveTab] = useState('overview'); // overview, raw_text, sections, fields
  const [rawText, setRawText] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Section definitions
  const [sections, setSections] = useState([
    { name: 'employee_header', label: 'Employee Header', startPattern: '', endPattern: '', description: 'Where employee info begins' },
    { name: 'earnings', label: 'Earnings', startPattern: '', endPattern: '', description: 'Earnings section' },
    { name: 'taxes', label: 'Taxes', startPattern: '', endPattern: '', description: 'Tax withholdings' },
    { name: 'deductions', label: 'Deductions', startPattern: '', endPattern: '', description: 'Deductions section' },
  ]);
  
  // Field definitions
  const [fields, setFields] = useState([]);
  const [newField, setNewField] = useState({ table_name: 'employees', field_name: '', field_label: '', field_type: 'text', pattern: '' });
  
  // Hints for prompt
  const [hints, setHints] = useState({
    layout: 'vertical', // vertical or horizontal
    employeeMarker: '',
    pageBreakHandling: '',
    specialInstructions: ''
  });

  // Load raw text when opened
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
        // Fallback: lookup by source file name
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
        <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-t-xl">
          <div className="flex items-center gap-3">
            <Wand2 className="w-6 h-6" />
            <div>
              <h2 className="text-lg font-semibold">Consultant Assist</h2>
              <p className="text-sm text-purple-200">Help Claude understand this register format</p>
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
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition ${
                activeTab === tab.id 
                  ? 'border-purple-600 text-purple-600' 
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-medium text-gray-900 mb-2">How Consultant Assist Works</h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
                  <li><strong>Review Raw Text</strong> - See exactly what was extracted from the PDF</li>
                  <li><strong>Define Sections</strong> - Tell Claude where to find employee data, earnings, taxes, etc.</li>
                  <li><strong>Add Custom Fields</strong> - Define any extra fields unique to this vendor</li>
                  <li><strong>Save Template</strong> - Reuse your definitions for future extractions</li>
                </ol>
              </div>

              {/* Layout Hint */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Register Layout</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="layout"
                      value="vertical"
                      checked={hints.layout === 'vertical'}
                      onChange={(e) => setHints({ ...hints, layout: e.target.value })}
                      className="text-purple-600"
                    />
                    <span className="text-sm">Vertical (sections stacked)</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="layout"
                      value="horizontal"
                      checked={hints.layout === 'horizontal'}
                      onChange={(e) => setHints({ ...hints, layout: e.target.value })}
                      className="text-purple-600"
                    />
                    <span className="text-sm">Horizontal (columns side-by-side)</span>
                  </label>
                </div>
              </div>

              {/* Employee Marker */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Employee Marker Pattern
                </label>
                <input
                  type="text"
                  value={hints.employeeMarker}
                  onChange={(e) => setHints({ ...hints, employeeMarker: e.target.value })}
                  placeholder="e.g., 'Emp #:' or employee name pattern"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
                <p className="text-xs text-gray-500 mt-1">What text marks the start of each employee?</p>
              </div>

              {/* Special Instructions */}
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
                        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">{field.field_type}</span>
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
                      className="w-full px-3 py-1.5 bg-purple-600 text-white rounded text-sm hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1"
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
              className="px-4 py-2 border border-purple-600 text-purple-600 rounded-lg hover:bg-purple-50 flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Template'}
            </button>
            <button
              onClick={handleRetryWithHints}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 flex items-center gap-2"
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
