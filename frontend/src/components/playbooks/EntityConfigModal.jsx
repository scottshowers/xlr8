/**
 * EntityConfigModal.jsx - Entity Configuration at Playbook Start
 * 
 * PLAYBOOK-AGNOSTIC: Works for any playbook type
 * 
 * LOCATION: frontend/src/components/playbooks/EntityConfigModal.jsx
 * 
 * PURPOSE:
 * - Detect US FEINs and Canada BNs in uploaded documents
 * - Let user select which entities to analyze
 * - Set primary entity
 * - Handle country routing (US playbook vs Canada playbook)
 * 
 * USAGE:
 * 
 * // In YearEndPlaybook.jsx
 * import { EntityConfigModal, EntityStatusBar } from '../components/playbooks/EntityConfigModal';
 * 
 * // Check if config needed on load
 * const [showConfig, setShowConfig] = useState(false);
 * const [entityConfig, setEntityConfig] = useState(null);
 * 
 * useEffect(() => {
 *   checkEntityConfig();
 * }, [project.id]);
 * 
 * const checkEntityConfig = async () => {
 *   const res = await api.get(`/playbooks/year_end/entity-config/${project.id}`);
 *   if (res.data.configured) {
 *     setEntityConfig(res.data.config);
 *   } else {
 *     setShowConfig(true);  // Show config modal
 *   }
 * };
 * 
 * // Render
 * {showConfig && (
 *   <EntityConfigModal
 *     projectId={project.id}
 *     playbookType="year_end"
 *     playbookCountry="us"  // This playbook is for US
 *     onConfigured={(config) => {
 *       setEntityConfig(config);
 *       setShowConfig(false);
 *     }}
 *     onCancel={() => setShowConfig(false)}
 *   />
 * )}
 * 
 * {entityConfig && (
 *   <EntityStatusBar 
 *     config={entityConfig}
 *     onReconfigure={() => setShowConfig(true)}
 *   />
 * )}
 */

import React, { useState, useEffect } from 'react';
import api from '../../services/api';

// =============================================================================
// CONFIGURATION MODAL
// =============================================================================

export function EntityConfigModal({ 
  projectId, 
  playbookType = 'year_end',
  playbookCountry = 'us',  // Which country this playbook is for
  onConfigured, 
  onCancel,
  onSkip  // Optional: allow skipping if no entities found
}) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  
  const [entities, setEntities] = useState({ us: [], canada: [] });
  const [selected, setSelected] = useState(new Set());
  const [scope, setScope] = useState('all');
  const [primary, setPrimary] = useState(null);
  const [warnings, setWarnings] = useState([]);

  // Detect entities on mount
  useEffect(() => {
    detectEntities();
  }, [projectId, playbookType]);

  const detectEntities = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const res = await api.post(`/playbooks/${playbookType}/detect-entities/${projectId}`);
      
      if (res.data.success) {
        const detected = res.data.entities || { us: [], canada: [] };
        setEntities(detected);
        setWarnings(res.data.warnings || []);
        
        // Default: select all entities matching playbook country
        const targetEntities = detected[playbookCountry] || [];
        const ids = targetEntities.map(e => e.id);
        setSelected(new Set(ids));
        
        // Set default primary (most mentioned)
        if (res.data.summary?.suggested_primary) {
          setPrimary(res.data.summary.suggested_primary);
        } else if (targetEntities.length > 0) {
          setPrimary(targetEntities[0].id);
        }
        
        // Auto-skip if no entities found and onSkip provided
        const total = (detected.us?.length || 0) + (detected.canada?.length || 0);
        if (total === 0 && onSkip) {
          onSkip();
        }
      } else {
        setError(res.data.message || 'Failed to detect entities');
      }
    } catch (err) {
      console.error('Entity detection failed:', err);
      setError(err.message || 'Failed to scan documents');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (selected.size === 0) {
      setError('Please select at least one entity');
      return;
    }
    
    setSaving(true);
    setError(null);
    
    try {
      const otherCountry = playbookCountry === 'us' ? 'canada' : 'us';
      const hasOtherCountry = (entities[otherCountry]?.length || 0) > 0;
      
      const config = {
        analysis_scope: scope,
        selected_entities: Array.from(selected),
        primary_entity: primary,
        country_mode: hasOtherCountry ? 'mixed' : `${playbookCountry}_only`
      };
      
      await api.post(`/playbooks/${playbookType}/entity-config/${projectId}`, config);
      onConfigured(config);
      
    } catch (err) {
      console.error('Save config failed:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const toggleEntity = (id) => {
    const newSelected = new Set(selected);
    if (newSelected.has(id)) {
      newSelected.delete(id);
      // If deselecting primary, clear it
      if (id === primary) {
        setPrimary(null);
      }
    } else {
      newSelected.add(id);
      // If no primary set, make this the primary
      if (!primary) {
        setPrimary(id);
      }
    }
    setSelected(newSelected);
  };

  const selectAll = (country) => {
    const ids = (entities[country] || []).map(e => e.id);
    setSelected(new Set([...selected, ...ids]));
  };

  const deselectAll = (country) => {
    const ids = new Set((entities[country] || []).map(e => e.id));
    setSelected(new Set([...selected].filter(id => !ids.has(id))));
  };

  // Loading state
  if (loading) {
    return (
      <div style={styles.overlay}>
        <div style={styles.modal}>
          <div style={styles.loadingContainer}>
            <div style={styles.spinner} />
            <div style={{ marginTop: '1rem', color: '#6b7280' }}>
              Scanning documents for entities...
            </div>
          </div>
        </div>
      </div>
    );
  }

  const usEntities = entities.us || [];
  const caEntities = entities.canada || [];
  const targetEntities = entities[playbookCountry] || [];
  const otherEntities = entities[playbookCountry === 'us' ? 'canada' : 'us'] || [];
  
  const totalTarget = targetEntities.length;
  const totalOther = otherEntities.length;
  const selectedCount = selected.size;

  // No entities found
  if (totalTarget === 0 && totalOther === 0) {
    return (
      <div style={styles.overlay}>
        <div style={styles.modal}>
          <h2 style={styles.title}>📋 Entity Configuration</h2>
          
          <div style={styles.emptyState}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🔍</div>
            <div style={{ fontWeight: '600', marginBottom: '0.5rem' }}>
              No entities detected
            </div>
            <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
              We couldn't find any FEINs or Business Numbers in your uploaded documents.
              You can still proceed with generic analysis.
            </div>
          </div>
          
          <div style={styles.actions}>
            <button onClick={onCancel} style={styles.cancelButton}>
              Cancel
            </button>
            <button onClick={() => onConfigured({ analysis_scope: 'none', selected_entities: [] })} style={styles.primaryButton}>
              Continue Without Entity Filter →
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.overlay}>
      <div style={{ ...styles.modal, maxWidth: '650px' }}>
        <h2 style={styles.title}>📋 Entity Configuration</h2>
        <p style={styles.subtitle}>
          Select which entities to include in this {playbookCountry.toUpperCase()} playbook analysis:
        </p>

        {/* Error Display */}
        {error && (
          <div style={styles.errorBox}>
            ⚠️ {error}
          </div>
        )}

        {/* Target Country Entities */}
        {totalTarget > 0 && (
          <div style={{ marginBottom: '1rem' }}>
            <div style={styles.sectionHeader}>
              <span>
                {playbookCountry === 'us' ? '🇺🇸' : '🇨🇦'} 
                {playbookCountry === 'us' ? ' United States' : ' Canada'} Entities ({totalTarget})
              </span>
              <div>
                <button 
                  onClick={() => selectAll(playbookCountry)} 
                  style={styles.linkButton}
                >
                  Select All
                </button>
                <span style={{ margin: '0 0.25rem', color: '#d1d5db' }}>|</span>
                <button 
                  onClick={() => deselectAll(playbookCountry)} 
                  style={styles.linkButton}
                >
                  Deselect All
                </button>
              </div>
            </div>
            <div style={styles.entityList}>
              {targetEntities.map(entity => (
                <EntityRow
                  key={entity.id}
                  entity={entity}
                  isSelected={selected.has(entity.id)}
                  isPrimary={entity.id === primary}
                  onToggle={() => toggleEntity(entity.id)}
                  onSetPrimary={() => {
                    setPrimary(entity.id);
                    if (!selected.has(entity.id)) {
                      toggleEntity(entity.id);
                    }
                  }}
                  disabled={false}
                />
              ))}
            </div>
          </div>
        )}

        {/* Other Country Entities (disabled) */}
        {totalOther > 0 && (
          <div style={{ marginBottom: '1rem' }}>
            <div style={styles.sectionHeader}>
              <span>
                {playbookCountry === 'us' ? '🇨🇦' : '🇺🇸'} 
                {playbookCountry === 'us' ? ' Canada' : ' United States'} Entities ({totalOther})
              </span>
            </div>
            <div style={{ ...styles.entityList, ...styles.disabledSection }}>
              {otherEntities.map(entity => (
                <EntityRow
                  key={entity.id}
                  entity={entity}
                  isSelected={false}
                  isPrimary={false}
                  onToggle={() => {}}
                  onSetPrimary={() => {}}
                  disabled={true}
                />
              ))}
              <div style={styles.disabledMessage}>
                ⚠️ {playbookCountry === 'us' ? 'Canada' : 'US'} entities require the{' '}
                {playbookCountry === 'us' ? 'Canada' : 'US'} Year-End Playbook
                {playbookCountry === 'us' && ' (coming soon)'}
              </div>
            </div>
          </div>
        )}

        {/* Scope Selection */}
        {totalTarget > 1 && (
          <div style={styles.scopeSection}>
            <div style={styles.scopeTitle}>Analysis Scope</div>
            <div style={styles.scopeOptions}>
              <label style={styles.radioLabel}>
                <input
                  type="radio"
                  name="scope"
                  value="all"
                  checked={scope === 'all'}
                  onChange={() => {
                    setScope('all');
                    selectAll(playbookCountry);
                  }}
                />
                <span>All {playbookCountry.toUpperCase()} entities ({totalTarget})</span>
              </label>
              <label style={styles.radioLabel}>
                <input
                  type="radio"
                  name="scope"
                  value="selected"
                  checked={scope === 'selected'}
                  onChange={() => setScope('selected')}
                />
                <span>Selected entities only ({selectedCount})</span>
              </label>
              {primary && (
                <label style={styles.radioLabel}>
                  <input
                    type="radio"
                    name="scope"
                    value="primary_only"
                    checked={scope === 'primary_only'}
                    onChange={() => {
                      setScope('primary_only');
                      if (primary) setSelected(new Set([primary]));
                    }}
                  />
                  <span>Primary entity only</span>
                </label>
              )}
            </div>
          </div>
        )}

        {/* Warnings */}
        {warnings.length > 0 && (
          <div style={styles.warningBox}>
            {warnings.map((w, i) => (
              <div key={i}>⚠️ {w}</div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div style={styles.actions}>
          <button onClick={onCancel} style={styles.cancelButton} disabled={saving}>
            Cancel
          </button>
          <button 
            onClick={handleSave}
            disabled={selectedCount === 0 || saving}
            style={{
              ...styles.primaryButton,
              opacity: (selectedCount === 0 || saving) ? 0.5 : 1,
              cursor: (selectedCount === 0 || saving) ? 'not-allowed' : 'pointer'
            }}
          >
            {saving ? 'Saving...' : `Configure & Continue (${selectedCount} entities) →`}
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// ENTITY ROW
// =============================================================================

function EntityRow({ entity, isSelected, isPrimary, onToggle, onSetPrimary, disabled }) {
  const idLabel = entity.type === 'fein' ? 'FEIN' : 'BN';
  
  return (
    <div style={{ 
      ...styles.entityRow,
      opacity: disabled ? 0.6 : 1,
      background: isSelected ? '#f0f9ff' : 'white'
    }}>
      <input
        type="checkbox"
        checked={isSelected}
        onChange={onToggle}
        disabled={disabled}
        style={{ marginRight: '0.75rem' }}
      />
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <strong>{entity.company_name || 'Unknown Company'}</strong>
          {isPrimary && (
            <span style={styles.primaryBadge}>★ PRIMARY</span>
          )}
        </div>
        <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
          {idLabel}: {entity.id}
          {entity.count > 1 && (
            <span style={{ marginLeft: '0.5rem', color: '#9ca3af' }}>
              ({entity.count} mentions)
            </span>
          )}
        </div>
      </div>
      {!disabled && !isPrimary && isSelected && (
        <button
          onClick={onSetPrimary}
          style={styles.setPrimaryButton}
        >
          Set Primary
        </button>
      )}
      {isPrimary && (
        <span style={{ fontSize: '0.75rem', color: '#3b82f6' }}>Primary</span>
      )}
    </div>
  );
}

// =============================================================================
// STATUS BAR (Show after configuration)
// =============================================================================

export function EntityStatusBar({ config, onReconfigure }) {
  if (!config || !config.selected_entities) {
    return null;
  }
  
  const count = config.selected_entities.length;
  const scope = config.analysis_scope;
  
  let message = '';
  if (scope === 'all') {
    message = `Analyzing all ${count} entities`;
  } else if (scope === 'primary_only') {
    message = `Analyzing primary entity only`;
  } else {
    message = `Analyzing ${count} selected entit${count === 1 ? 'y' : 'ies'}`;
  }
  
  return (
    <div style={styles.statusBar}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '1.1rem' }}>🏢</span>
        <span style={{ fontSize: '0.9rem' }}>{message}</span>
        {config.primary_entity && (
          <span style={{ fontSize: '0.75rem', color: '#6b7280', marginLeft: '0.5rem' }}>
            Primary: {config.primary_entity}
          </span>
        )}
      </div>
      <button onClick={onReconfigure} style={styles.changeButton}>
        ⚙️ Change
      </button>
    </div>
  );
}

// =============================================================================
// STYLES
// =============================================================================

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10000,
    padding: '1rem'
  },
  modal: {
    background: 'white',
    borderRadius: '12px',
    padding: '1.5rem',
    width: '100%',
    maxWidth: '550px',
    maxHeight: '90vh',
    overflow: 'auto',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
  },
  title: {
    margin: '0 0 0.5rem 0',
    fontSize: '1.25rem',
    fontWeight: '600'
  },
  subtitle: {
    margin: '0 0 1rem 0',
    color: '#6b7280',
    fontSize: '0.9rem'
  },
  loadingContainer: {
    padding: '3rem',
    textAlign: 'center'
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '3px solid #e5e7eb',
    borderTop: '3px solid #3b82f6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: '0 auto'
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontWeight: '600',
    fontSize: '0.9rem',
    marginBottom: '0.5rem',
    color: '#374151'
  },
  entityList: {
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    overflow: 'hidden'
  },
  entityRow: {
    display: 'flex',
    alignItems: 'center',
    padding: '0.75rem',
    borderBottom: '1px solid #f3f4f6',
    transition: 'background 0.15s ease'
  },
  primaryBadge: {
    background: '#dbeafe',
    color: '#1d4ed8',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '0.7rem',
    fontWeight: '600'
  },
  setPrimaryButton: {
    fontSize: '0.7rem',
    padding: '4px 8px',
    background: '#f3f4f6',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    cursor: 'pointer',
    color: '#6b7280'
  },
  disabledSection: {
    background: '#fefce8',
    border: '1px solid #fde047'
  },
  disabledMessage: {
    padding: '0.75rem',
    fontSize: '0.85rem',
    color: '#92400e',
    background: '#fef3c7'
  },
  scopeSection: {
    marginBottom: '1rem',
    padding: '0.75rem',
    background: '#f9fafb',
    borderRadius: '8px'
  },
  scopeTitle: {
    fontWeight: '600',
    fontSize: '0.85rem',
    marginBottom: '0.5rem',
    color: '#374151'
  },
  scopeOptions: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem'
  },
  radioLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.9rem',
    cursor: 'pointer'
  },
  warningBox: {
    background: '#fef3c7',
    border: '1px solid #fde68a',
    borderRadius: '8px',
    padding: '0.75rem',
    marginBottom: '1rem',
    fontSize: '0.85rem',
    color: '#92400e'
  },
  errorBox: {
    background: '#fee2e2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    padding: '0.75rem',
    marginBottom: '1rem',
    fontSize: '0.85rem',
    color: '#991b1b'
  },
  emptyState: {
    padding: '2rem',
    textAlign: 'center',
    background: '#f9fafb',
    borderRadius: '8px',
    marginBottom: '1rem'
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '0.5rem',
    marginTop: '1rem'
  },
  cancelButton: {
    padding: '0.6rem 1.25rem',
    background: 'white',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.9rem'
  },
  primaryButton: {
    padding: '0.6rem 1.25rem',
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.9rem',
    fontWeight: '500'
  },
  linkButton: {
    background: 'none',
    border: 'none',
    color: '#3b82f6',
    cursor: 'pointer',
    fontSize: '0.75rem',
    textDecoration: 'underline'
  },
  statusBar: {
    background: '#eff6ff',
    border: '1px solid #bfdbfe',
    borderRadius: '8px',
    padding: '0.6rem 0.85rem',
    marginBottom: '1rem',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  changeButton: {
    fontSize: '0.75rem',
    padding: '4px 10px',
    background: 'white',
    border: '1px solid #93c5fd',
    borderRadius: '4px',
    cursor: 'pointer',
    color: '#3b82f6'
  }
};

export default EntityConfigModal;
