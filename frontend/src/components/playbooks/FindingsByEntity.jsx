/**
 * FindingsByEntity.jsx - Multi-FEIN Findings Display Component
 * 
 * PLAYBOOK-AGNOSTIC: Works for any playbook type
 * 
 * LOCATION: frontend/src/components/playbooks/FindingsByEntity.jsx
 * 
 * USAGE:
 * 
 * // In YearEndPlaybook.jsx (or any playbook)
 * import { FindingsByEntity } from '../components/playbooks/FindingsByEntity';
 * 
 * // Replaces the old findings rendering
 * <FindingsByEntity
 *   findings={findings}  // Full findings object (may be single or multi-FEIN)
 *   projectId={project.id}
 *   playbookType="year_end"
 *   actionId={action.action_id}
 *   onFindingChange={() => loadProgress()}
 * />
 */

import React, { useState, useEffect } from 'react';
import { FindingsList } from './FindingItem';

// =============================================================================
// MAIN COMPONENT - Handles both Single and Multi-FEIN
// =============================================================================

export function FindingsByEntity({ 
  findings, 
  projectId, 
  playbookType, 
  actionId,
  onFindingChange 
}) {
  const [activeEntity, setActiveEntity] = useState(null);
  
  // Determine if this is multi-FEIN response
  const isMultiFein = findings?.is_multi_fein && findings?.entities;
  const entities = isMultiFein ? Object.entries(findings.entities) : null;
  const hasGlobalIssues = findings?.global_issues?.length > 0 || findings?.global_recommendations?.length > 0;
  
  // Set default active entity on load
  useEffect(() => {
    if (entities && !activeEntity) {
      // Default to primary entity or first one
      const primary = entities.find(([_, e]) => e.is_primary);
      setActiveEntity(primary ? primary[0] : entities[0]?.[0]);
    }
  }, [entities, activeEntity]);

  // Reset when findings change
  useEffect(() => {
    setActiveEntity(null);
  }, [findings?.fein_count]);

  // ===== SINGLE FEIN PATH =====
  if (!isMultiFein) {
    return (
      <div>
        {/* Key Values */}
        {findings?.key_values && Object.keys(findings.key_values).length > 0 && (
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ 
              fontSize: '0.75rem', 
              fontWeight: '600', 
              color: '#6b7280', 
              marginBottom: '0.35rem' 
            }}>
              📊 Key Values
            </div>
            <div style={{ 
              display: 'flex', 
              flexWrap: 'wrap', 
              gap: '0.4rem' 
            }}>
              {Object.entries(findings.key_values).map(([key, value]) => (
                <span key={key} style={{
                  background: '#f3f4f6',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  border: '1px solid #e5e7eb'
                }}>
                  <strong>{key}:</strong> {formatValue(value)}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Issues */}
        {findings?.issues?.length > 0 && (
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ 
              fontSize: '0.75rem', 
              fontWeight: '600', 
              color: '#991b1b', 
              marginBottom: '0.35rem' 
            }}>
              ⚠️ Issues Identified ({findings.issues.length})
            </div>
            <FindingsList
              findings={findings.issues}
              acknowledgedFindings={findings.acknowledged_issues || []}
              projectId={projectId}
              playbookType={playbookType}
              actionId={actionId}
              onFindingChange={onFindingChange}
            />
          </div>
        )}

        {/* Recommendations */}
        {findings?.recommendations?.length > 0 && (
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ 
              fontSize: '0.75rem', 
              fontWeight: '600', 
              color: '#1d4ed8', 
              marginBottom: '0.35rem' 
            }}>
              💡 Recommendations
            </div>
            <ul style={{ 
              margin: 0, 
              paddingLeft: '1.25rem', 
              fontSize: '0.85rem',
              color: '#1d4ed8'
            }}>
              {findings.recommendations.map((rec, i) => (
                <li key={i} style={{ marginBottom: '0.25rem' }}>{rec}</li>
              ))}
            </ul>
          </div>
        )}

        {/* No issues state */}
        {(!findings?.issues || findings.issues.length === 0) && (
          <div style={{
            color: '#059669',
            fontSize: '0.85rem',
            padding: '0.75rem',
            background: '#f0fdf4',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <span style={{ fontSize: '1rem' }}>✓</span>
            No issues identified
          </div>
        )}

        {/* Summary */}
        {findings?.summary && (
          <div style={{
            marginTop: '0.75rem',
            padding: '0.5rem 0.75rem',
            background: '#f9fafb',
            borderRadius: '6px',
            fontSize: '0.8rem',
            color: '#374151',
            borderLeft: '3px solid #d1d5db'
          }}>
            {findings.summary}
          </div>
        )}
      </div>
    );
  }

  // ===== MULTI-FEIN PATH =====
  return (
    <div>
      {/* Multi-Entity Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
        border: '1px solid #93c5fd',
        borderRadius: '8px',
        padding: '0.6rem 0.85rem',
        marginBottom: '0.75rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem'
      }}>
        <span style={{ fontSize: '1.2rem' }}>🏢</span>
        <div>
          <div style={{ 
            fontWeight: '600', 
            color: '#1e40af',
            fontSize: '0.9rem'
          }}>
            {findings.fein_count} Legal Entities Detected
          </div>
          <div style={{ 
            fontSize: '0.75rem', 
            color: '#3b82f6' 
          }}>
            Select an entity below to view its specific findings
          </div>
        </div>
      </div>

      {/* Entity Tabs */}
      <div style={{
        display: 'flex',
        gap: '0.35rem',
        marginBottom: '0.75rem',
        flexWrap: 'wrap'
      }}>
        {entities.map(([fein, entity]) => (
          <EntityTab
            key={fein}
            fein={fein}
            entity={entity}
            isActive={activeEntity === fein}
            onClick={() => setActiveEntity(fein)}
          />
        ))}
        
        {/* Global Issues Tab */}
        {hasGlobalIssues && (
          <button
            onClick={() => setActiveEntity('_global')}
            style={{
              padding: '0.4rem 0.75rem',
              border: activeEntity === '_global' ? '2px solid #8b5cf6' : '1px solid #d1d5db',
              borderRadius: '8px',
              background: activeEntity === '_global' ? '#ede9fe' : '#fff',
              cursor: 'pointer',
              fontSize: '0.8rem',
              transition: 'all 0.15s ease'
            }}
          >
            <div style={{ fontWeight: '600', color: '#7c3aed' }}>🌐 Cross-Entity</div>
            <div style={{ fontSize: '0.7rem', color: '#6b7280' }}>
              {(findings.global_issues?.length || 0) + (findings.global_recommendations?.length || 0)} items
            </div>
          </button>
        )}
      </div>

      {/* Active Entity Content */}
      {activeEntity && activeEntity !== '_global' && findings.entities[activeEntity] && (
        <EntityPanel
          fein={activeEntity}
          entity={findings.entities[activeEntity]}
          projectId={projectId}
          playbookType={playbookType}
          actionId={actionId}
          onFindingChange={onFindingChange}
        />
      )}

      {/* Global Issues Content */}
      {activeEntity === '_global' && (
        <GlobalPanel
          findings={findings}
          projectId={projectId}
          playbookType={playbookType}
          actionId={actionId}
          onFindingChange={onFindingChange}
        />
      )}

      {/* Overall Summary */}
      {findings.summary && (
        <div style={{
          marginTop: '0.75rem',
          padding: '0.6rem 0.85rem',
          background: '#f9fafb',
          borderRadius: '6px',
          fontSize: '0.8rem',
          color: '#374151',
          borderLeft: '3px solid #6b7280'
        }}>
          <strong>Summary:</strong> {findings.summary}
        </div>
      )}

      {/* Cross-Entity Notes */}
      {findings.cross_entity_notes && (
        <div style={{
          marginTop: '0.5rem',
          padding: '0.5rem 0.75rem',
          background: '#fefce8',
          borderRadius: '6px',
          fontSize: '0.8rem',
          color: '#854d0e',
          border: '1px solid #fde047'
        }}>
          <strong>📝 Cross-Entity Note:</strong> {findings.cross_entity_notes}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// ENTITY TAB BUTTON
// =============================================================================

function EntityTab({ fein, entity, isActive, onClick }) {
  const riskColors = {
    high: { bg: '#fee2e2', text: '#991b1b', border: '#fecaca' },
    medium: { bg: '#fef3c7', text: '#92400e', border: '#fde68a' },
    low: { bg: '#d1fae5', text: '#166534', border: '#86efac' }
  };
  
  const risk = riskColors[entity.risk_level] || riskColors.low;
  
  return (
    <button
      onClick={onClick}
      style={{
        padding: '0.5rem 0.75rem',
        border: isActive ? '2px solid #3b82f6' : '1px solid #d1d5db',
        borderRadius: '8px',
        background: isActive ? '#dbeafe' : '#fff',
        cursor: 'pointer',
        fontSize: '0.8rem',
        textAlign: 'left',
        minWidth: '140px',
        transition: 'all 0.15s ease',
        boxShadow: isActive ? '0 2px 4px rgba(59, 130, 246, 0.2)' : 'none'
      }}
    >
      <div style={{ 
        fontWeight: '600',
        display: 'flex',
        alignItems: 'center',
        gap: '0.25rem',
        marginBottom: '2px'
      }}>
        {entity.company_name || `Entity ${fein}`}
        {entity.is_primary && (
          <span style={{ color: '#3b82f6', fontSize: '0.9rem' }}>★</span>
        )}
      </div>
      <div style={{ 
        fontSize: '0.7rem', 
        color: '#6b7280',
        marginBottom: '4px'
      }}>
        {fein}
      </div>
      <span style={{
        fontSize: '0.65rem',
        padding: '2px 6px',
        borderRadius: '4px',
        background: risk.bg,
        color: risk.text,
        border: `1px solid ${risk.border}`,
        fontWeight: '500'
      }}>
        {(entity.risk_level || 'unknown').toUpperCase()} RISK
      </span>
      {entity.issues?.length > 0 && (
        <span style={{
          marginLeft: '0.35rem',
          fontSize: '0.65rem',
          padding: '2px 6px',
          borderRadius: '4px',
          background: '#fef2f2',
          color: '#991b1b'
        }}>
          {entity.issues.length} issue{entity.issues.length > 1 ? 's' : ''}
        </span>
      )}
    </button>
  );
}

// =============================================================================
// ENTITY PANEL
// =============================================================================

function EntityPanel({ fein, entity, projectId, playbookType, actionId, onFindingChange }) {
  return (
    <div style={{
      border: '1px solid #e5e7eb',
      borderRadius: '8px',
      padding: '0.85rem',
      background: '#fff'
    }}>
      {/* Entity Header */}
      <div style={{ 
        marginBottom: '0.75rem',
        paddingBottom: '0.5rem',
        borderBottom: '1px solid #f3f4f6'
      }}>
        <div style={{ 
          fontWeight: '600', 
          fontSize: '0.95rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.35rem'
        }}>
          {entity.company_name}
          {entity.is_primary && (
            <span style={{ 
              fontSize: '0.65rem',
              background: '#dbeafe',
              color: '#1d4ed8',
              padding: '2px 6px',
              borderRadius: '4px'
            }}>
              PRIMARY
            </span>
          )}
        </div>
        <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
          FEIN: {fein}
          {entity.data_quality && (
            <span style={{ marginLeft: '1rem' }}>
              Data Quality: {entity.data_quality}
            </span>
          )}
        </div>
      </div>
      
      {/* Key Values */}
      {entity.key_values && Object.keys(entity.key_values).length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ 
            fontSize: '0.75rem', 
            fontWeight: '600', 
            color: '#6b7280', 
            marginBottom: '0.35rem' 
          }}>
            📊 Key Values
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
            {Object.entries(entity.key_values).map(([key, value]) => (
              <span key={key} style={{
                background: '#f3f4f6',
                padding: '3px 8px',
                borderRadius: '4px',
                fontSize: '0.75rem',
                border: '1px solid #e5e7eb'
              }}>
                <strong>{key}:</strong> {formatValue(value)}
              </span>
            ))}
          </div>
        </div>
      )}
      
      {/* Issues */}
      {entity.issues?.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ 
            fontSize: '0.75rem', 
            fontWeight: '600', 
            color: '#991b1b', 
            marginBottom: '0.35rem' 
          }}>
            ⚠️ Issues ({entity.issues.length})
          </div>
          <FindingsList
            findings={entity.issues}
            acknowledgedFindings={entity.acknowledged_issues || []}
            projectId={projectId}
            playbookType={playbookType}
            actionId={actionId}
            feinFilter={fein}
            onFindingChange={onFindingChange}
          />
        </div>
      )}
      
      {/* Recommendations */}
      {entity.recommendations?.length > 0 && (
        <div>
          <div style={{ 
            fontSize: '0.75rem', 
            fontWeight: '600', 
            color: '#1d4ed8', 
            marginBottom: '0.35rem' 
          }}>
            💡 Recommendations
          </div>
          <ul style={{ 
            margin: 0, 
            paddingLeft: '1.25rem', 
            fontSize: '0.85rem',
            color: '#1d4ed8'
          }}>
            {entity.recommendations.map((rec, i) => (
              <li key={i} style={{ marginBottom: '0.25rem' }}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
      
      {/* No issues state */}
      {(!entity.issues || entity.issues.length === 0) && (
        <div style={{
          color: '#059669',
          fontSize: '0.85rem',
          padding: '0.6rem',
          background: '#f0fdf4',
          borderRadius: '6px',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <span>✓</span>
          No issues identified for this entity
        </div>
      )}
    </div>
  );
}

// =============================================================================
// GLOBAL PANEL (Cross-Entity Issues)
// =============================================================================

function GlobalPanel({ findings, projectId, playbookType, actionId, onFindingChange }) {
  return (
    <div style={{
      border: '1px solid #c4b5fd',
      borderRadius: '8px',
      padding: '0.85rem',
      background: 'linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%)'
    }}>
      <div style={{ 
        marginBottom: '0.75rem',
        paddingBottom: '0.5rem',
        borderBottom: '1px solid #ddd6fe'
      }}>
        <div style={{ fontWeight: '600', fontSize: '0.95rem', color: '#6b21a8' }}>
          🌐 Cross-Entity Issues & Recommendations
        </div>
        <div style={{ fontSize: '0.75rem', color: '#7c3aed' }}>
          These items apply to all entities or span multiple legal entities
        </div>
      </div>
      
      {/* Global Issues */}
      {findings.global_issues?.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ 
            fontSize: '0.75rem', 
            fontWeight: '600', 
            color: '#991b1b', 
            marginBottom: '0.35rem' 
          }}>
            ⚠️ Cross-Entity Issues ({findings.global_issues.length})
          </div>
          <FindingsList
            findings={findings.global_issues}
            projectId={projectId}
            playbookType={playbookType}
            actionId={actionId}
            feinFilter="_global"
            onFindingChange={onFindingChange}
          />
        </div>
      )}
      
      {/* Global Recommendations */}
      {findings.global_recommendations?.length > 0 && (
        <div>
          <div style={{ 
            fontSize: '0.75rem', 
            fontWeight: '600', 
            color: '#7c3aed', 
            marginBottom: '0.35rem' 
          }}>
            💡 Cross-Entity Recommendations
          </div>
          <ul style={{ 
            margin: 0, 
            paddingLeft: '1.25rem', 
            fontSize: '0.85rem',
            color: '#6b21a8'
          }}>
            {findings.global_recommendations.map((rec, i) => (
              <li key={i} style={{ marginBottom: '0.25rem' }}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
      
      {/* No global issues */}
      {(!findings.global_issues || findings.global_issues.length === 0) && 
       (!findings.global_recommendations || findings.global_recommendations.length === 0) && (
        <div style={{
          color: '#059669',
          fontSize: '0.85rem',
          padding: '0.6rem',
          background: '#f0fdf4',
          borderRadius: '6px'
        }}>
          ✓ No cross-entity issues identified
        </div>
      )}
    </div>
  );
}

// =============================================================================
// HELPERS
// =============================================================================

function formatValue(value) {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

export default FindingsByEntity;
