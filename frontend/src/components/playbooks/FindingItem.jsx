/**
 * FindingItem.jsx - Reusable Finding Suppression Component
 * 
 * PLAYBOOK-AGNOSTIC: Works for year_end, post_live, assessment, and any future types.
 * Just change the 'playbookType' prop!
 * 
 * LOCATION: frontend/src/components/playbooks/FindingItem.jsx
 * 
 * USAGE:
 * 
 * // In YearEndPlaybook.jsx
 * import { FindingsList } from '../components/playbooks/FindingItem';
 * 
 * <FindingsList
 *   findings={findings.issues || []}
 *   acknowledgedFindings={findings.acknowledged_issues || []}
 *   projectId={project.id}
 *   playbookType="year_end"
 *   actionId={action.action_id}
 *   onFindingChange={() => loadProgress()}
 * />
 * 
 * // In PostLivePlaybook.jsx (future)
 * <FindingsList
 *   ...
 *   playbookType="post_live"  // <-- Only change needed!
 * />
 */

import React, { useState } from 'react';
import api from '../../services/api';

// =============================================================================
// SINGLE FINDING ITEM
// =============================================================================

/**
 * Single finding item with suppress/acknowledge controls.
 * 
 * @param {string} finding - The finding text
 * @param {string} projectId - Project UUID
 * @param {string} playbookType - 'year_end', 'post_live', etc.
 * @param {string} actionId - Action ID (e.g., '2A', '3B')
 * @param {function} onSuppressed - Callback when finding is suppressed
 * @param {boolean} isAcknowledged - If true, render as grayed/acknowledged
 * @param {string} acknowledgeReason - Reason text if acknowledged
 */
export function FindingItem({ 
  finding, 
  projectId, 
  playbookType, 
  actionId,
  onSuppressed,
  isAcknowledged = false,
  acknowledgeReason = null
}) {
  const [showActions, setShowActions] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showReasonModal, setShowReasonModal] = useState(false);
  const [reason, setReason] = useState('');
  const [suppressType, setSuppressType] = useState('acknowledge');

  // Handle button clicks - show modal for reason input
  const handleSuppress = async (type) => {
    setSuppressType(type);
    setReason(type === 'acknowledge' ? 'Client acknowledged' : '');
    setShowReasonModal(true);
  };

  // Submit the suppression to backend
  const submitSuppression = async () => {
    if (!reason.trim()) {
      return; // Reason required
    }
    
    setIsSubmitting(true);
    try {
      const response = await api.post(
        `/playbooks/${playbookType}/suppress/quick/${projectId}/${actionId}`,
        {
          finding_text: finding,
          reason: reason.trim(),
          suppress_type: suppressType
        }
      );
      
      if (response.data.success) {
        onSuppressed?.(finding, response.data.rule_id, suppressType);
        setShowReasonModal(false);
        setShowActions(false);
        setReason('');
      } else {
        console.error('Suppression failed:', response.data.message);
        alert('Failed to suppress: ' + (response.data.message || 'Unknown error'));
      }
    } catch (err) {
      console.error('Suppression error:', err);
      alert('Error: ' + (err.message || 'Network error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render acknowledged finding (grayed out)
  if (isAcknowledged) {
    return (
      <div style={{
        fontSize: '0.85rem',
        color: '#9ca3af',
        padding: '0.35rem 0',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.5rem',
        opacity: 0.7
      }}>
        <span style={{ color: '#10b981' }}>✓</span>
        <div style={{ flex: 1 }}>
          <span style={{ textDecoration: 'line-through' }}>{finding}</span>
          {acknowledgeReason && (
            <div style={{ 
              fontSize: '0.7rem', 
              fontStyle: 'italic', 
              marginTop: '2px',
              color: '#6b7280'
            }}>
              {acknowledgeReason}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Render active finding with action buttons
  return (
    <div 
      style={{
        fontSize: '0.85rem',
        color: '#991b1b',
        padding: '0.35rem 0',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.5rem',
        position: 'relative'
      }}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => !showReasonModal && setShowActions(false)}
    >
      <span style={{ color: '#dc2626' }}>•</span>
      <div style={{ flex: 1 }}>
        <span>{finding}</span>
        
        {/* Action buttons - show on hover */}
        {showActions && (
          <div style={{
            display: 'flex',
            gap: '0.5rem',
            marginTop: '0.35rem',
            flexWrap: 'wrap'
          }}>
            <button
              onClick={() => handleSuppress('acknowledge')}
              style={{
                fontSize: '0.65rem',
                padding: '3px 8px',
                background: '#f0fdf4',
                border: '1px solid #86efac',
                borderRadius: '4px',
                cursor: 'pointer',
                color: '#166534',
                display: 'flex',
                alignItems: 'center',
                gap: '3px'
              }}
              title="Mark as acknowledged - stays visible but grayed"
            >
              ✓ Acknowledge
            </button>
            <button
              onClick={() => handleSuppress('suppress')}
              style={{
                fontSize: '0.65rem',
                padding: '3px 8px',
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: '4px',
                cursor: 'pointer',
                color: '#991b1b',
                display: 'flex',
                alignItems: 'center',
                gap: '3px'
              }}
              title="Hide this finding completely"
            >
              ✕ Suppress
            </button>
            <button
              onClick={() => handleSuppress('pattern')}
              style={{
                fontSize: '0.65rem',
                padding: '3px 8px',
                background: '#eff6ff',
                border: '1px solid #bfdbfe',
                borderRadius: '4px',
                cursor: 'pointer',
                color: '#1d4ed8',
                display: 'flex',
                alignItems: 'center',
                gap: '3px'
              }}
              title="Create a rule to suppress similar findings"
            >
              ⚙ Suppress Pattern
            </button>
          </div>
        )}
      </div>

      {/* Reason Modal */}
      {showReasonModal && (
        <div 
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10000
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowReasonModal(false);
              setReason('');
            }
          }}
        >
          <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            maxWidth: '450px',
            width: '90%',
            boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)'
          }}>
            <h3 style={{ 
              margin: '0 0 1rem', 
              fontSize: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              {suppressType === 'acknowledge' && <span style={{ color: '#10b981' }}>✓</span>}
              {suppressType === 'suppress' && <span style={{ color: '#dc2626' }}>✕</span>}
              {suppressType === 'pattern' && <span style={{ color: '#3b82f6' }}>⚙</span>}
              {suppressType === 'acknowledge' ? 'Acknowledge Finding' : 
               suppressType === 'suppress' ? 'Suppress Finding' :
               'Create Suppression Rule'}
            </h3>
            
            <div style={{ 
              marginBottom: '1rem', 
              fontSize: '0.85rem', 
              color: '#6b7280',
              background: '#f9fafb',
              padding: '0.75rem',
              borderRadius: '4px',
              border: '1px solid #e5e7eb'
            }}>
              {finding}
            </div>
            
            <div style={{ marginBottom: '0.5rem' }}>
              <label style={{ 
                display: 'block', 
                marginBottom: '0.25rem', 
                fontSize: '0.85rem',
                fontWeight: '500'
              }}>
                Reason <span style={{ color: '#dc2626' }}>*</span>
              </label>
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && reason.trim()) {
                    submitSuppression();
                  }
                }}
                placeholder={
                  suppressType === 'acknowledge' ? 'e.g., Client is aware' :
                  suppressType === 'suppress' ? 'e.g., Using external system' :
                  'e.g., All WC rates are intentional placeholders'
                }
                autoFocus
                style={{
                  width: '100%',
                  padding: '0.6rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  fontSize: '0.85rem',
                  boxSizing: 'border-box'
                }}
              />
            </div>
            
            {suppressType === 'pattern' && (
              <div style={{ 
                fontSize: '0.75rem', 
                color: '#6b7280', 
                marginBottom: '1rem',
                background: '#eff6ff',
                padding: '0.5rem',
                borderRadius: '4px'
              }}>
                ℹ️ Pattern suppression will hide all similar findings (numbers normalized).
              </div>
            )}
            
            <div style={{ 
              display: 'flex', 
              gap: '0.5rem', 
              justifyContent: 'flex-end',
              marginTop: '1rem'
            }}>
              <button
                onClick={() => {
                  setShowReasonModal(false);
                  setReason('');
                }}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#f3f4f6',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.85rem'
                }}
              >
                Cancel
              </button>
              <button
                onClick={submitSuppression}
                disabled={!reason.trim() || isSubmitting}
                style={{
                  padding: '0.5rem 1rem',
                  background: reason.trim() ? '#3b82f6' : '#9ca3af',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: reason.trim() ? 'pointer' : 'not-allowed',
                  fontSize: '0.85rem',
                  fontWeight: '500'
                }}
              >
                {isSubmitting ? 'Saving...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// FINDINGS LIST CONTAINER
// =============================================================================

/**
 * Container for all findings with acknowledged section.
 * 
 * @param {string[]} findings - Array of finding strings
 * @param {object[]} acknowledgedFindings - Array of {text, reason, rule_id}
 * @param {string} projectId - Project UUID
 * @param {string} playbookType - 'year_end', 'post_live', etc.
 * @param {string} actionId - Action ID
 * @param {function} onFindingChange - Callback when a finding is suppressed
 */
export function FindingsList({
  findings = [],
  acknowledgedFindings = [],
  projectId,
  playbookType,
  actionId,
  onFindingChange
}) {
  const [localSuppressed, setLocalSuppressed] = useState(new Set());
  const [localAcknowledged, setLocalAcknowledged] = useState([]);

  const handleSuppressed = (findingText, ruleId, suppressType) => {
    if (suppressType === 'acknowledge') {
      // Move to acknowledged list
      setLocalAcknowledged(prev => [...prev, {
        text: findingText,
        reason: 'Just acknowledged',
        rule_id: ruleId
      }]);
    }
    // Mark as suppressed (removes from active list)
    setLocalSuppressed(prev => new Set([...prev, findingText]));
    onFindingChange?.();
  };

  // Combine server-side acknowledged with local
  const allAcknowledged = [
    ...acknowledgedFindings,
    ...localAcknowledged.filter(la => 
      !acknowledgedFindings.some(af => af.text === la.text)
    )
  ];

  // Filter out suppressed findings
  const activeFindings = findings.filter(f => !localSuppressed.has(f));

  return (
    <div>
      {/* Active Issues */}
      {activeFindings.length > 0 && (
        <div style={{ 
          background: '#fef2f2', 
          border: '1px solid #fecaca',
          borderRadius: '6px',
          padding: '0.5rem',
          marginBottom: allAcknowledged.length > 0 ? '0.5rem' : 0
        }}>
          {activeFindings.map((finding, i) => (
            <div 
              key={`finding-${i}`}
              style={{
                borderBottom: i < activeFindings.length - 1 ? '1px solid #fecaca' : 'none'
              }}
            >
              <FindingItem
                finding={finding}
                projectId={projectId}
                playbookType={playbookType}
                actionId={actionId}
                onSuppressed={handleSuppressed}
              />
            </div>
          ))}
        </div>
      )}

      {/* Acknowledged Issues (collapsed by default) */}
      {allAcknowledged.length > 0 && (
        <details style={{ marginTop: '0.5rem' }}>
          <summary style={{ 
            fontSize: '0.75rem', 
            color: '#6b7280', 
            cursor: 'pointer',
            padding: '0.35rem 0',
            userSelect: 'none'
          }}>
            <span style={{ color: '#10b981' }}>✓</span> {allAcknowledged.length} acknowledged issue{allAcknowledged.length > 1 ? 's' : ''}
          </summary>
          <div style={{ 
            background: '#f9fafb', 
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            padding: '0.5rem',
            marginTop: '0.25rem'
          }}>
            {allAcknowledged.map((item, i) => (
              <FindingItem
                key={`ack-${i}`}
                finding={typeof item === 'string' ? item : item.text}
                isAcknowledged={true}
                acknowledgeReason={typeof item === 'object' ? item.reason : null}
              />
            ))}
          </div>
        </details>
      )}

      {/* No issues state */}
      {activeFindings.length === 0 && allAcknowledged.length === 0 && (
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
    </div>
  );
}

// =============================================================================
// SUPPRESSION MANAGEMENT (Future - for settings page)
// =============================================================================

/**
 * Suppression rules management UI (for project settings).
 * 
 * Shows all suppression rules for a project with ability to:
 * - View rule details
 * - Deactivate/reactivate rules
 * - See match statistics
 */
export function SuppressionManager({ projectId, playbookType }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInactive, setShowInactive] = useState(false);

  React.useEffect(() => {
    loadRules();
  }, [projectId, playbookType, showInactive]);

  const loadRules = async () => {
    setLoading(true);
    try {
      const res = await api.get(
        `/playbooks/${playbookType}/suppressions/${projectId}`,
        { params: { include_inactive: showInactive } }
      );
      if (res.data.success) {
        setRules(res.data.rules || []);
      }
    } catch (err) {
      console.error('Failed to load suppressions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeactivate = async (ruleId) => {
    try {
      await api.delete(`/playbooks/${playbookType}/suppress/${ruleId}`);
      loadRules();
    } catch (err) {
      console.error('Failed to deactivate:', err);
    }
  };

  const handleReactivate = async (ruleId) => {
    try {
      await api.put(`/playbooks/${playbookType}/suppress/${ruleId}/reactivate`);
      loadRules();
    } catch (err) {
      console.error('Failed to reactivate:', err);
    }
  };

  if (loading) {
    return <div style={{ padding: '1rem', color: '#6b7280' }}>Loading...</div>;
  }

  return (
    <div style={{ padding: '1rem' }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '1rem'
      }}>
        <h3 style={{ margin: 0 }}>Suppression Rules</h3>
        <label style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input 
            type="checkbox" 
            checked={showInactive}
            onChange={(e) => setShowInactive(e.target.checked)}
          />
          Show inactive
        </label>
      </div>

      {rules.length === 0 ? (
        <div style={{ 
          padding: '2rem', 
          textAlign: 'center', 
          color: '#6b7280',
          background: '#f9fafb',
          borderRadius: '6px'
        }}>
          No suppression rules yet
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {rules.map(rule => (
            <div 
              key={rule.id}
              style={{
                padding: '0.75rem',
                background: rule.is_active ? '#fff' : '#f9fafb',
                border: '1px solid #e5e7eb',
                borderRadius: '6px',
                opacity: rule.is_active ? 1 : 0.6
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span style={{
                    background: rule.suppression_type === 'acknowledge' ? '#d1fae5' :
                               rule.suppression_type === 'suppress' ? '#fee2e2' : '#dbeafe',
                    color: rule.suppression_type === 'acknowledge' ? '#166534' :
                           rule.suppression_type === 'suppress' ? '#991b1b' : '#1d4ed8',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: '500',
                    textTransform: 'uppercase'
                  }}>
                    {rule.suppression_type}
                  </span>
                  {rule.action_id && (
                    <span style={{ 
                      marginLeft: '0.5rem', 
                      fontSize: '0.75rem', 
                      color: '#6b7280' 
                    }}>
                      Action {rule.action_id}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => rule.is_active ? handleDeactivate(rule.id) : handleReactivate(rule.id)}
                  style={{
                    fontSize: '0.7rem',
                    padding: '3px 8px',
                    background: 'transparent',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  {rule.is_active ? 'Deactivate' : 'Reactivate'}
                </button>
              </div>
              
              <div style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
                {rule.reason}
              </div>
              
              {rule.finding_hash && (
                <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: '0.25rem' }}>
                  Hash: {rule.finding_hash.slice(0, 12)}...
                </div>
              )}
              
              <div style={{ 
                fontSize: '0.7rem', 
                color: '#9ca3af', 
                marginTop: '0.5rem',
                display: 'flex',
                gap: '1rem'
              }}>
                <span>Matches: {rule.match_count || 0}</span>
                <span>Created: {new Date(rule.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default FindingItem;
