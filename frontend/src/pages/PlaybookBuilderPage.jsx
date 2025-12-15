/**
 * PlaybookBuilderPage - Admin UI for Creating/Editing Playbooks
 * 
 * Three creation modes:
 *   A. Template-based: Pick type, fill in blanks
 *   B. Component-based: Mix and match modules
 *   C. Clone and modify: Copy existing, customize
 * 
 * Deploy to: frontend/src/pages/PlaybookBuilderPage.jsx
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

// Brand Colors
const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  clearwater: '#b2d6de',
  white: '#f6f5fa',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

// Playbook type definitions
const PLAYBOOK_TYPES = [
  {
    id: 'checklist',
    name: 'Checklist',
    icon: '📋',
    description: 'Step-by-step workflow with actions and document requirements',
    example: 'Year-End Checklist',
  },
  {
    id: 'analysis',
    name: 'Analysis',
    icon: '🔍',
    description: 'Analyze uploaded data for insights, patterns, and issues',
    example: 'Data Quality Audit',
  },
  {
    id: 'compliance',
    name: 'Compliance',
    icon: '🏛️',
    description: 'Check data against standards rules for violations',
    example: 'SECURE 2.0 Check',
  },
  {
    id: 'hybrid',
    name: 'Hybrid',
    icon: '🔄',
    description: 'Combination of checklist structure with analysis capabilities',
    example: 'Implementation Validation',
  },
];

// =============================================================================
// START SCREEN - Choose creation mode
// =============================================================================

function StartScreen({ onSelectMode }) {
  const modes = [
    {
      id: 'template',
      icon: '📝',
      title: 'Create from Template',
      description: 'Pick a playbook type and fill in the details. Best for standard workflows.',
      color: COLORS.grassGreen,
    },
    {
      id: 'components',
      icon: '🧩',
      title: 'Build Custom',
      description: 'Mix and match components to create a unique playbook. For power users.',
      color: COLORS.skyBlue,
    },
    {
      id: 'clone',
      icon: '📋',
      title: 'Clone Existing',
      description: 'Copy an existing playbook and customize it. Fastest way to get started.',
      color: COLORS.clearwater,
    },
  ];

  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h2 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.5rem', color: COLORS.text, marginBottom: '0.5rem' }}>
          How do you want to create your playbook?
        </h2>
        <p style={{ color: COLORS.textLight }}>Choose the approach that fits your needs</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', maxWidth: '900px', margin: '0 auto' }}>
        {modes.map(mode => (
          <div
            key={mode.id}
            onClick={() => onSelectMode(mode.id)}
            style={{
              padding: '2rem 1.5rem',
              background: 'white',
              borderRadius: '16px',
              border: '2px solid #e1e8ed',
              cursor: 'pointer',
              textAlign: 'center',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = mode.color;
              e.currentTarget.style.transform = 'translateY(-4px)';
              e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = '#e1e8ed';
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>{mode.icon}</div>
            <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.1rem', color: COLORS.text, marginBottom: '0.5rem' }}>
              {mode.title}
            </h3>
            <p style={{ color: COLORS.textLight, fontSize: '0.9rem', lineHeight: '1.5' }}>
              {mode.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// TEMPLATE MODE - Pick type, fill in blanks
// =============================================================================

function TemplateMode({ onBack, onSave }) {
  const [step, setStep] = useState(1); // 1=pick type, 2=basic info, 3=configure, 4=review
  const [selectedType, setSelectedType] = useState(null);
  const [config, setConfig] = useState({
    playbook_id: '',
    name: '',
    description: '',
    category: 'Custom',
    icon: '📋',
    estimated_time: '10-15 minutes',
    modules: ['All'],
    inputs: {},
    steps: [],
    analysis_config: {},
    compliance_config: {},
    components: [],
  });

  const updateConfig = (field, value) => {
    setConfig(prev => ({ ...prev, [field]: value }));
  };

  // Step 1: Pick type
  if (step === 1) {
    return (
      <div>
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: COLORS.textLight, cursor: 'pointer', marginBottom: '1rem' }}>
          ← Back
        </button>
        <h2 style={{ fontFamily: "'Sora', sans-serif", marginBottom: '1.5rem' }}>What type of playbook?</h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', maxWidth: '700px' }}>
          {PLAYBOOK_TYPES.map(type => (
            <div
              key={type.id}
              onClick={() => {
                setSelectedType(type.id);
                updateConfig('playbook_type', type.id);
                updateConfig('icon', type.icon);
                // Set default components based on type
                if (type.id === 'checklist') {
                  updateConfig('components', ['document_scanner', 'findings_extractor', 'intelligence_hook', 'learning_hook']);
                } else if (type.id === 'analysis') {
                  updateConfig('components', ['data_analyzer', 'findings_extractor', 'learning_hook']);
                } else if (type.id === 'compliance') {
                  updateConfig('components', ['rule_checker', 'data_analyzer', 'findings_extractor']);
                } else {
                  updateConfig('components', ['document_scanner', 'data_analyzer', 'findings_extractor', 'learning_hook']);
                }
                setStep(2);
              }}
              style={{
                padding: '1.5rem',
                background: 'white',
                borderRadius: '12px',
                border: '2px solid #e1e8ed',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = COLORS.grassGreen;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e1e8ed';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '2rem' }}>{type.icon}</span>
                <h3 style={{ margin: 0, color: COLORS.text }}>{type.name}</h3>
              </div>
              <p style={{ color: COLORS.textLight, fontSize: '0.9rem', margin: '0 0 0.5rem 0' }}>{type.description}</p>
              <p style={{ color: COLORS.skyBlue, fontSize: '0.8rem', margin: 0 }}>Example: {type.example}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Step 2: Basic info
  if (step === 2) {
    return (
      <div style={{ maxWidth: '600px' }}>
        <button onClick={() => setStep(1)} style={{ background: 'none', border: 'none', color: COLORS.textLight, cursor: 'pointer', marginBottom: '1rem' }}>
          ← Back to type selection
        </button>
        <h2 style={{ fontFamily: "'Sora', sans-serif", marginBottom: '1.5rem' }}>Basic Information</h2>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Playbook ID *</label>
            <input
              type="text"
              value={config.playbook_id}
              onChange={(e) => updateConfig('playbook_id', e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
              placeholder="my-playbook-id"
              style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px', fontSize: '1rem' }}
            />
            <p style={{ color: COLORS.textLight, fontSize: '0.8rem', margin: '0.25rem 0 0 0' }}>Lowercase letters, numbers, and hyphens only</p>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Name *</label>
            <input
              type="text"
              value={config.name}
              onChange={(e) => updateConfig('name', e.target.value)}
              placeholder="My Playbook Name"
              style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px', fontSize: '1rem' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Description</label>
            <textarea
              value={config.description}
              onChange={(e) => updateConfig('description', e.target.value)}
              placeholder="What does this playbook do?"
              rows={3}
              style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px', fontSize: '1rem', resize: 'vertical' }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Category</label>
              <select
                value={config.category}
                onChange={(e) => updateConfig('category', e.target.value)}
                style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px', fontSize: '1rem' }}
              >
                <option value="Custom">Custom</option>
                <option value="Year-End">Year-End</option>
                <option value="Compliance">Compliance</option>
                <option value="Audit">Audit</option>
                <option value="Implementation">Implementation</option>
                <option value="Regulatory">Regulatory</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Estimated Time</label>
              <select
                value={config.estimated_time}
                onChange={(e) => updateConfig('estimated_time', e.target.value)}
                style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px', fontSize: '1rem' }}
              >
                <option value="1-3 minutes">1-3 minutes</option>
                <option value="3-5 minutes">3-5 minutes</option>
                <option value="5-10 minutes">5-10 minutes</option>
                <option value="10-15 minutes">10-15 minutes</option>
                <option value="15-30 minutes">15-30 minutes</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
            <button
              onClick={() => setStep(3)}
              disabled={!config.playbook_id || !config.name}
              style={{
                padding: '0.75rem 1.5rem',
                background: (!config.playbook_id || !config.name) ? '#ccc' : COLORS.grassGreen,
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '600',
                cursor: (!config.playbook_id || !config.name) ? 'not-allowed' : 'pointer',
              }}
            >
              Continue →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Step 3: Type-specific configuration
  if (step === 3) {
    return (
      <div style={{ maxWidth: '700px' }}>
        <button onClick={() => setStep(2)} style={{ background: 'none', border: 'none', color: COLORS.textLight, cursor: 'pointer', marginBottom: '1rem' }}>
          ← Back
        </button>
        <h2 style={{ fontFamily: "'Sora', sans-serif", marginBottom: '1.5rem' }}>
          Configure {PLAYBOOK_TYPES.find(t => t.id === selectedType)?.name} Playbook
        </h2>

        {selectedType === 'checklist' && (
          <ChecklistConfig config={config} updateConfig={updateConfig} />
        )}
        
        {selectedType === 'analysis' && (
          <AnalysisConfig config={config} updateConfig={updateConfig} />
        )}
        
        {selectedType === 'compliance' && (
          <ComplianceConfig config={config} updateConfig={updateConfig} />
        )}
        
        {selectedType === 'hybrid' && (
          <HybridConfig config={config} updateConfig={updateConfig} />
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '2rem' }}>
          <button
            onClick={() => setStep(4)}
            style={{
              padding: '0.75rem 1.5rem',
              background: COLORS.grassGreen,
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            Review & Save →
          </button>
        </div>
      </div>
    );
  }

  // Step 4: Review and save
  if (step === 4) {
    return (
      <div style={{ maxWidth: '700px' }}>
        <button onClick={() => setStep(3)} style={{ background: 'none', border: 'none', color: COLORS.textLight, cursor: 'pointer', marginBottom: '1rem' }}>
          ← Back
        </button>
        <h2 style={{ fontFamily: "'Sora', sans-serif", marginBottom: '1.5rem' }}>Review & Save</h2>

        <div style={{ background: '#f8f9fa', borderRadius: '12px', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '2.5rem' }}>{config.icon}</span>
            <div>
              <h3 style={{ margin: 0, color: COLORS.text }}>{config.name}</h3>
              <p style={{ margin: '0.25rem 0 0 0', color: COLORS.textLight, fontSize: '0.9rem' }}>{config.playbook_id}</p>
            </div>
          </div>
          
          <p style={{ color: COLORS.textLight, marginBottom: '1rem' }}>{config.description || 'No description'}</p>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', fontSize: '0.9rem' }}>
            <div><strong>Type:</strong> {selectedType}</div>
            <div><strong>Category:</strong> {config.category}</div>
            <div><strong>Time:</strong> {config.estimated_time}</div>
          </div>

          <div style={{ marginTop: '1rem' }}>
            <strong>Components:</strong>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
              {config.components.map(c => (
                <span key={c} style={{ padding: '0.25rem 0.5rem', background: COLORS.iceFlow, borderRadius: '4px', fontSize: '0.8rem' }}>
                  {c}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
          <button
            onClick={() => onSave(config)}
            style={{
              padding: '0.75rem 2rem',
              background: COLORS.grassGreen,
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontWeight: '600',
              fontSize: '1rem',
              cursor: 'pointer',
            }}
          >
            🚀 Create Playbook
          </button>
        </div>
      </div>
    );
  }
}

// Type-specific config components
function ChecklistConfig({ config, updateConfig }) {
  const [steps, setSteps] = useState(config.steps || []);

  const addStep = () => {
    const newStep = {
      step_number: String(steps.length + 1),
      step_name: `Step ${steps.length + 1}`,
      phase: 'Analysis',
      actions: [],
    };
    const updated = [...steps, newStep];
    setSteps(updated);
    updateConfig('steps', updated);
  };

  const addAction = (stepIndex) => {
    const updated = [...steps];
    const actionNum = updated[stepIndex].actions.length + 1;
    updated[stepIndex].actions.push({
      action_id: `${updated[stepIndex].step_number}${String.fromCharCode(64 + actionNum)}`,
      description: '',
      action_type: 'recommended',
      reports_needed: [],
      keywords: [],
    });
    setSteps(updated);
    updateConfig('steps', updated);
  };

  return (
    <div>
      <p style={{ color: COLORS.textLight, marginBottom: '1rem' }}>
        Define the steps and actions for your checklist. Each step can have multiple actions.
      </p>

      {steps.map((step, stepIdx) => (
        <div key={stepIdx} style={{ background: '#f8f9fa', borderRadius: '8px', padding: '1rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem' }}>
            <input
              value={step.step_number}
              onChange={(e) => {
                const updated = [...steps];
                updated[stepIdx].step_number = e.target.value;
                setSteps(updated);
                updateConfig('steps', updated);
              }}
              placeholder="Step #"
              style={{ width: '80px', padding: '0.5rem', border: '1px solid #e1e8ed', borderRadius: '6px' }}
            />
            <input
              value={step.step_name}
              onChange={(e) => {
                const updated = [...steps];
                updated[stepIdx].step_name = e.target.value;
                setSteps(updated);
                updateConfig('steps', updated);
              }}
              placeholder="Step Name"
              style={{ flex: 1, padding: '0.5rem', border: '1px solid #e1e8ed', borderRadius: '6px' }}
            />
          </div>

          {step.actions.map((action, actionIdx) => (
            <div key={actionIdx} style={{ marginLeft: '1rem', marginBottom: '0.5rem', display: 'flex', gap: '0.5rem' }}>
              <input
                value={action.action_id}
                onChange={(e) => {
                  const updated = [...steps];
                  updated[stepIdx].actions[actionIdx].action_id = e.target.value;
                  setSteps(updated);
                  updateConfig('steps', updated);
                }}
                placeholder="ID"
                style={{ width: '60px', padding: '0.5rem', border: '1px solid #e1e8ed', borderRadius: '6px', fontSize: '0.9rem' }}
              />
              <input
                value={action.description}
                onChange={(e) => {
                  const updated = [...steps];
                  updated[stepIdx].actions[actionIdx].description = e.target.value;
                  setSteps(updated);
                  updateConfig('steps', updated);
                }}
                placeholder="Action description"
                style={{ flex: 1, padding: '0.5rem', border: '1px solid #e1e8ed', borderRadius: '6px', fontSize: '0.9rem' }}
              />
            </div>
          ))}

          <button
            onClick={() => addAction(stepIdx)}
            style={{ marginLeft: '1rem', padding: '0.25rem 0.5rem', background: 'none', border: '1px dashed #ccc', borderRadius: '4px', color: COLORS.textLight, cursor: 'pointer', fontSize: '0.8rem' }}
          >
            + Add Action
          </button>
        </div>
      ))}

      <button
        onClick={addStep}
        style={{ padding: '0.5rem 1rem', background: 'none', border: '2px dashed #ccc', borderRadius: '8px', color: COLORS.textLight, cursor: 'pointer' }}
      >
        + Add Step
      </button>
    </div>
  );
}

function AnalysisConfig({ config, updateConfig }) {
  const [focusAreas, setFocusAreas] = useState(config.analysis_config?.focus_areas || []);

  const toggleArea = (area) => {
    const updated = focusAreas.includes(area)
      ? focusAreas.filter(a => a !== area)
      : [...focusAreas, area];
    setFocusAreas(updated);
    updateConfig('analysis_config', { ...config.analysis_config, focus_areas: updated });
  };

  const areas = [
    { id: 'missing_values', label: 'Missing Values', icon: '❓' },
    { id: 'duplicates', label: 'Duplicates', icon: '👯' },
    { id: 'format_issues', label: 'Format Issues', icon: '📝' },
    { id: 'outliers', label: 'Outliers', icon: '📊' },
    { id: 'referential_integrity', label: 'Referential Integrity', icon: '🔗' },
    { id: 'date_issues', label: 'Date Issues', icon: '📅' },
    { id: 'numeric_anomalies', label: 'Numeric Anomalies', icon: '🔢' },
    { id: 'text_quality', label: 'Text Quality', icon: '📄' },
  ];

  return (
    <div>
      <p style={{ color: COLORS.textLight, marginBottom: '1rem' }}>
        Select what the analysis should look for in the uploaded data.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
        {areas.map(area => (
          <div
            key={area.id}
            onClick={() => toggleArea(area.id)}
            style={{
              padding: '0.75rem 1rem',
              background: focusAreas.includes(area.id) ? COLORS.iceFlow : 'white',
              border: `2px solid ${focusAreas.includes(area.id) ? COLORS.grassGreen : '#e1e8ed'}`,
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <span>{area.icon}</span>
            <span>{area.label}</span>
            {focusAreas.includes(area.id) && <span style={{ marginLeft: 'auto', color: COLORS.grassGreen }}>✓</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

function ComplianceConfig({ config, updateConfig }) {
  const [domains, setDomains] = useState(config.compliance_config?.rule_domains || []);

  const toggleDomain = (domain) => {
    const updated = domains.includes(domain)
      ? domains.filter(d => d !== domain)
      : [...domains, domain];
    setDomains(updated);
    updateConfig('compliance_config', { ...config.compliance_config, rule_domains: updated });
  };

  const domainOptions = [
    { id: 'retirement', label: 'Retirement / 401(k)', icon: '🏦' },
    { id: 'tax', label: 'Tax Compliance', icon: '📋' },
    { id: 'benefits', label: 'Benefits', icon: '🏥' },
    { id: 'payroll', label: 'Payroll', icon: '💰' },
    { id: 'hr', label: 'HR / Employment', icon: '👥' },
    { id: 'general', label: 'General', icon: '📄' },
  ];

  return (
    <div>
      <p style={{ color: COLORS.textLight, marginBottom: '1rem' }}>
        Select which compliance domains this playbook should check against.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
        {domainOptions.map(domain => (
          <div
            key={domain.id}
            onClick={() => toggleDomain(domain.id)}
            style={{
              padding: '0.75rem 1rem',
              background: domains.includes(domain.id) ? COLORS.iceFlow : 'white',
              border: `2px solid ${domains.includes(domain.id) ? COLORS.grassGreen : '#e1e8ed'}`,
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <span>{domain.icon}</span>
            <span>{domain.label}</span>
            {domains.includes(domain.id) && <span style={{ marginLeft: 'auto', color: COLORS.grassGreen }}>✓</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

function HybridConfig({ config, updateConfig }) {
  return (
    <div>
      <p style={{ color: COLORS.textLight, marginBottom: '1rem' }}>
        Hybrid playbooks combine checklist structure with data analysis. Configure both aspects.
      </p>
      
      <div style={{ marginBottom: '2rem' }}>
        <h4 style={{ marginBottom: '0.5rem' }}>Checklist Steps</h4>
        <ChecklistConfig config={config} updateConfig={updateConfig} />
      </div>
      
      <div>
        <h4 style={{ marginBottom: '0.5rem' }}>Analysis Focus</h4>
        <AnalysisConfig config={config} updateConfig={updateConfig} />
      </div>
    </div>
  );
}

// =============================================================================
// CLONE MODE
// =============================================================================

function CloneMode({ onBack, onSave }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [newId, setNewId] = useState('');
  const [newName, setNewName] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get('/playbook-builder/configs?templates_only=true')
      .then(res => setTemplates(res.data.configs || []))
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false));
  }, []);

  const handleClone = async () => {
    if (!selected || !newId || !newName) return;
    setSaving(true);
    try {
      await api.post('/playbook-builder/clone', {
        source_playbook_id: selected.playbook_id,
        new_playbook_id: newId,
        new_name: newName,
      });
      onSave({ playbook_id: newId, name: newName, cloned: true });
    } catch (err) {
      alert(err.response?.data?.detail || 'Clone failed');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '3rem', color: COLORS.textLight }}>Loading templates...</div>;
  }

  return (
    <div style={{ maxWidth: '600px' }}>
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: COLORS.textLight, cursor: 'pointer', marginBottom: '1rem' }}>
        ← Back
      </button>
      <h2 style={{ fontFamily: "'Sora', sans-serif", marginBottom: '1.5rem' }}>Clone Existing Playbook</h2>

      {!selected ? (
        <div>
          <p style={{ color: COLORS.textLight, marginBottom: '1rem' }}>Select a playbook to clone:</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {templates.map(t => (
              <div
                key={t.playbook_id}
                onClick={() => {
                  setSelected(t);
                  setNewName(`${t.name} (Copy)`);
                  setNewId(`${t.playbook_id}-copy`);
                }}
                style={{
                  padding: '1rem',
                  background: 'white',
                  border: '2px solid #e1e8ed',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1rem',
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = COLORS.grassGreen}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = '#e1e8ed'}
              >
                <span style={{ fontSize: '1.5rem' }}>{t.icon}</span>
                <div>
                  <div style={{ fontWeight: '600', color: COLORS.text }}>{t.name}</div>
                  <div style={{ fontSize: '0.85rem', color: COLORS.textLight }}>{t.playbook_type} • {t.category}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div>
          <div style={{ background: '#f8f9fa', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem' }}>
            <strong>Cloning:</strong> {selected.name} ({selected.playbook_id})
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>New Playbook ID *</label>
              <input
                value={newId}
                onChange={(e) => setNewId(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
                style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>New Name *</label>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
              <button
                onClick={() => setSelected(null)}
                style={{ padding: '0.75rem 1.5rem', background: '#f0f0f0', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
              >
                Choose Different
              </button>
              <button
                onClick={handleClone}
                disabled={!newId || !newName || saving}
                style={{
                  padding: '0.75rem 1.5rem',
                  background: (!newId || !newName || saving) ? '#ccc' : COLORS.grassGreen,
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: '600',
                  cursor: (!newId || !newName || saving) ? 'not-allowed' : 'pointer',
                }}
              >
                {saving ? 'Cloning...' : '📋 Clone Playbook'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// COMPONENT MODE (simplified)
// =============================================================================

function ComponentMode({ onBack, onSave }) {
  const [components, setComponents] = useState([]);
  const [availableComponents, setAvailableComponents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState({
    playbook_id: '',
    name: '',
    description: '',
    playbook_type: 'hybrid',
    category: 'Custom',
    icon: '🧩',
    estimated_time: '10-15 minutes',
    components: [],
  });

  useEffect(() => {
    api.get('/playbook-builder/components')
      .then(res => setAvailableComponents(res.data.components || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const toggleComponent = (componentId) => {
    const updated = config.components.includes(componentId)
      ? config.components.filter(c => c !== componentId)
      : [...config.components, componentId];
    setConfig(prev => ({ ...prev, components: updated }));
  };

  const handleSave = () => {
    if (!config.playbook_id || !config.name) {
      alert('Please fill in Playbook ID and Name');
      return;
    }
    onSave(config);
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '3rem', color: COLORS.textLight }}>Loading components...</div>;
  }

  return (
    <div style={{ maxWidth: '700px' }}>
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: COLORS.textLight, cursor: 'pointer', marginBottom: '1rem' }}>
        ← Back
      </button>
      <h2 style={{ fontFamily: "'Sora', sans-serif", marginBottom: '1.5rem' }}>Build Custom Playbook</h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Playbook ID *</label>
            <input
              value={config.playbook_id}
              onChange={(e) => setConfig(prev => ({ ...prev, playbook_id: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') }))}
              style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Name *</label>
            <input
              value={config.name}
              onChange={(e) => setConfig(prev => ({ ...prev, name: e.target.value }))}
              style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px' }}
            />
          </div>
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Description</label>
          <textarea
            value={config.description}
            onChange={(e) => setConfig(prev => ({ ...prev, description: e.target.value }))}
            rows={2}
            style={{ width: '100%', padding: '0.75rem', border: '1px solid #e1e8ed', borderRadius: '8px', resize: 'vertical' }}
          />
        </div>
      </div>

      <h3 style={{ marginBottom: '1rem' }}>Select Components</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem', marginBottom: '2rem' }}>
        {availableComponents.map(comp => (
          <div
            key={comp.component_id}
            onClick={() => toggleComponent(comp.component_id)}
            style={{
              padding: '1rem',
              background: config.components.includes(comp.component_id) ? COLORS.iceFlow : 'white',
              border: `2px solid ${config.components.includes(comp.component_id) ? COLORS.grassGreen : '#e1e8ed'}`,
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong>{comp.name}</strong>
              {config.components.includes(comp.component_id) && <span style={{ color: COLORS.grassGreen }}>✓</span>}
            </div>
            <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.85rem', color: COLORS.textLight }}>{comp.description}</p>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={handleSave}
          disabled={!config.playbook_id || !config.name}
          style={{
            padding: '0.75rem 2rem',
            background: (!config.playbook_id || !config.name) ? '#ccc' : COLORS.grassGreen,
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontWeight: '600',
            cursor: (!config.playbook_id || !config.name) ? 'not-allowed' : 'pointer',
          }}
        >
          🚀 Create Playbook
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function PlaybookBuilderPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState(null); // null | 'template' | 'components' | 'clone'
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(null);

  const handleSave = async (config) => {
    setSaving(true);
    try {
      if (config.cloned) {
        // Already saved by clone function
        setSuccess(config);
      } else {
        await api.post('/playbook-builder/configs', config);
        setSuccess(config);
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to save playbook');
    } finally {
      setSaving(false);
    }
  };

  if (success) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 2rem' }}>
        <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🎉</div>
        <h2 style={{ fontFamily: "'Sora', sans-serif", color: COLORS.text, marginBottom: '0.5rem' }}>
          Playbook Created!
        </h2>
        <p style={{ color: COLORS.textLight, marginBottom: '2rem' }}>
          <strong>{success.name}</strong> ({success.playbook_id}) is ready to use.
        </p>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <button
            onClick={() => { setSuccess(null); setMode(null); }}
            style={{ padding: '0.75rem 1.5rem', background: '#f0f0f0', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
          >
            Create Another
          </button>
          <button
            onClick={() => navigate('/admin')}
            style={{ padding: '0.75rem 1.5rem', background: COLORS.grassGreen, color: 'white', border: 'none', borderRadius: '8px', fontWeight: '600', cursor: 'pointer' }}
          >
            Go to Admin →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.75rem', fontWeight: '700', color: COLORS.text, margin: 0 }}>
          🔧 Playbook Builder
        </h1>
        <p style={{ color: COLORS.textLight, marginTop: '0.25rem' }}>
          Create new playbooks for your team
        </p>
      </div>

      <div style={{ background: 'white', borderRadius: '16px', boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)', padding: '2rem' }}>
        {!mode && <StartScreen onSelectMode={setMode} />}
        {mode === 'template' && <TemplateMode onBack={() => setMode(null)} onSave={handleSave} />}
        {mode === 'components' && <ComponentMode onBack={() => setMode(null)} onSave={handleSave} />}
        {mode === 'clone' && <CloneMode onBack={() => setMode(null)} onSave={handleSave} />}
      </div>
    </div>
  );
            }
