/**
 * YearEndPlaybook - Interactive Year-End Checklist
 * 
 * Guided journey through Year-End actions:
 * - Shows all steps/actions from parsed UKG doc
 * - Auto-scans for relevant documents per action
 * - Tracks status (not started, in progress, complete, n/a)
 * - Consultant can add notes, override status
 * - Export current state anytime
 */

import React, { useState, useEffect } from 'react';
import api from '../services/api';

// Brand Colors
const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  clearwater: '#b2d6de',
  turkishSea: '#285390',
  electricBlue: '#2766b1',
  iceFlow: '#c9d3d4',
  white: '#f6f5fa',
  silver: '#a2a1a0',
  scarletSage: '#993c44',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

const STATUS_OPTIONS = [
  { value: 'not_started', label: 'Not Started', color: '#9ca3af', bg: '#f3f4f6' },
  { value: 'in_progress', label: 'In Progress', color: '#d97706', bg: '#fef3c7' },
  { value: 'complete', label: 'Complete', color: '#059669', bg: '#d1fae5' },
  { value: 'na', label: 'N/A', color: '#6b7280', bg: '#e5e7eb' },
  { value: 'blocked', label: 'Blocked', color: '#dc2626', bg: '#fee2e2' },
];

// Tooltip type configuration
const TOOLTIP_TYPES = {
  best_practice: { icon: '⭐', label: 'Best Practice', color: '#eab308', bg: '#fef9c3' },
  mandatory: { icon: '🚨', label: 'Mandatory', color: '#dc2626', bg: '#fee2e2' },
  hint: { icon: '💡', label: 'Helpful Hint', color: '#3b82f6', bg: '#dbeafe' },
};

// Action dependencies - which actions inherit from which
const ACTION_DEPENDENCIES = {
  "2B": ["2A"], "2C": ["2A"], "2E": ["2A"],
  "2H": ["2F", "2G"], "2J": ["2G"], "2K": ["2G"], "2L": ["2G", "2J"],
  "3B": ["3A"], "3C": ["3A"], "3D": ["3A"],
  "5B": ["5A"], "5E": ["5C", "5D"],
  "6B": ["6A"], "6C": ["6A"],
};

// Get parent actions for an action
const getParentActions = (actionId) => ACTION_DEPENDENCIES[actionId] || [];

// =============================================================================
// AI SUMMARY DASHBOARD COMPONENT
// =============================================================================
function AISummaryDashboard({ summary, expanded, onToggle }) {
  if (!summary) return null;
  
  const { overall_risk, summary_text, stats, issues, recommendations, conflicts, review_flags, high_risk_actions } = summary;
  
  const riskColors = {
    high: { text: '#dc2626' },
    medium: { text: '#d97706' },
    low: { text: '#059669' }
  };
  
  const riskTextColor = riskColors[overall_risk]?.text || '#059669';
  
  return (
    <div style={{
      background: '#e8ede8',
      border: '1px solid #c5d1c5',
      borderRadius: '12px',
      marginBottom: '1rem',
      overflow: 'hidden'
    }}>
      <div 
        onClick={onToggle}
        style={{
          padding: '1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.5rem' }}>
            {overall_risk === 'high' ? '🔴' : overall_risk === 'medium' ? '🟡' : '🟢'}
          </span>
          <div>
            <div style={{ fontWeight: '600', color: COLORS.text }}>
              Analysis Summary (AI Assisted)
            </div>
            <div style={{ fontSize: '0.85rem', color: COLORS.textLight }}>
              {summary_text || 'No issues detected'}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ textAlign: 'right', fontSize: '0.8rem' }}>
            <div><strong>{stats?.actions_scanned || 0}</strong> scanned</div>
            <div><strong>{stats?.total_issues || 0}</strong> issues</div>
          </div>
          <span style={{ fontSize: '1.2rem' }}>{expanded ? '▼' : '▶'}</span>
        </div>
      </div>
      
      {expanded && (
        <div style={{ padding: '0 1rem 1rem', borderTop: '1px solid #e1e8ed' }}>
          {/* High Risk Actions */}
          {high_risk_actions?.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ fontWeight: '600', color: '#dc2626', marginBottom: '0.5rem' }}>
                🚨 High Risk Actions:
              </div>
              {high_risk_actions.map((action, i) => (
                <div key={i} style={{ 
                  background: 'white', 
                  padding: '0.5rem', 
                  borderRadius: '6px', 
                  marginBottom: '0.25rem',
                  fontSize: '0.85rem'
                }}>
                  <strong>{action.action_id}:</strong> {action.summary}
                </div>
              ))}
            </div>
          )}
          
          {/* Conflicts */}
          {conflicts?.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ fontWeight: '600', color: '#dc2626', marginBottom: '0.5rem' }}>
                ❗ Data Conflicts:
              </div>
              {conflicts.map((conflict, i) => (
                <div key={i} style={{ 
                  background: 'white', 
                  padding: '0.5rem', 
                  borderRadius: '6px', 
                  marginBottom: '0.25rem',
                  fontSize: '0.85rem'
                }}>
                  {conflict.message}
                </div>
              ))}
            </div>
          )}
          
          {/* Review Flags */}
          {review_flags?.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ fontWeight: '600', color: '#d97706', marginBottom: '0.5rem' }}>
                🔄 Actions Needing Review:
              </div>
              {review_flags.map((flag, i) => (
                <div key={i} style={{ 
                  background: 'white', 
                  padding: '0.5rem', 
                  borderRadius: '6px', 
                  marginBottom: '0.25rem',
                  fontSize: '0.85rem'
                }}>
                  <strong>{flag.action_id}:</strong> {flag.flag?.reason}
                </div>
              ))}
            </div>
          )}
          
          {/* Top Issues */}
          {issues?.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ fontWeight: '600', color: COLORS.text, marginBottom: '0.5rem' }}>
                ⚠️ Issues ({issues.length}):
              </div>
              <div style={{ maxHeight: '150px', overflow: 'auto' }}>
                {issues.slice(0, 10).map((issue, i) => (
                  <div key={i} style={{ 
                    background: 'white', 
                    padding: '0.5rem', 
                    borderRadius: '6px', 
                    marginBottom: '0.25rem',
                    fontSize: '0.8rem',
                    display: 'flex',
                    gap: '0.5rem'
                  }}>
                    <span style={{ 
                      background: issue.risk_level === 'high' ? '#fee2e2' : '#fef3c7',
                      padding: '0.1rem 0.4rem',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: '600'
                    }}>
                      {issue.action_id}
                    </span>
                    <span>{issue.issue}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Top Recommendations */}
          {recommendations?.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div style={{ fontWeight: '600', color: '#059669', marginBottom: '0.5rem' }}>
                ✅ Recommendations ({recommendations.length}):
              </div>
              <div style={{ maxHeight: '120px', overflow: 'auto' }}>
                {recommendations.slice(0, 8).map((rec, i) => (
                  <div key={i} style={{ 
                    background: 'white', 
                    padding: '0.5rem', 
                    borderRadius: '6px', 
                    marginBottom: '0.25rem',
                    fontSize: '0.8rem'
                  }}>
                    <span style={{ 
                      background: '#d1fae5',
                      padding: '0.1rem 0.4rem',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: '600',
                      marginRight: '0.5rem'
                    }}>
                      {rec.action_id}
                    </span>
                    {rec.recommendation}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// DOCUMENT CHECKLIST SIDEBAR COMPONENT
// =============================================================================
function DocumentChecklistSidebar({ checklist, collapsed, onToggle }) {
  if (!checklist) return null;
  
  const { checklist: docs, stats, processing_jobs } = checklist;
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'uploaded': return '✅';
      case 'processing': return '⏳';
      case 'missing': return '❌';
      default: return '❓';
    }
  };
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'uploaded': return '#059669';
      case 'processing': return '#d97706';
      case 'missing': return '#dc2626';
      default: return '#6b7280';
    }
  };
  
  if (collapsed) {
    return (
      <div 
        onClick={onToggle}
        style={{
          position: 'fixed',
          right: 0,
          top: '50%',
          transform: 'translateY(-50%)',
          background: stats?.required_complete ? '#d1fae5' : '#fef3c7',
          padding: '1rem 0.5rem',
          borderRadius: '8px 0 0 8px',
          cursor: 'pointer',
          writingMode: 'vertical-rl',
          textOrientation: 'mixed',
          fontWeight: '600',
          fontSize: '0.85rem',
          boxShadow: '-2px 0 8px rgba(0,0,0,0.1)'
        }}
      >
        📄 Documents ({stats?.total_uploaded || 0}/{stats?.total_documents || 0})
      </div>
    );
  }
  
  return (
    <div style={{
      position: 'fixed',
      right: 0,
      top: '100px',
      width: '280px',
      maxHeight: 'calc(100vh - 150px)',
      background: 'white',
      borderRadius: '12px 0 0 12px',
      boxShadow: '-4px 0 16px rgba(0,0,0,0.1)',
      overflow: 'hidden',
      zIndex: 100
    }}>
      {/* Header */}
      <div style={{
        padding: '1rem',
        background: stats?.required_complete ? '#d1fae5' : '#fef3c7',
        borderBottom: '1px solid #e1e8ed',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <div style={{ fontWeight: '600', fontSize: '0.9rem' }}>📄 Document Checklist</div>
          <div style={{ fontSize: '0.75rem', color: COLORS.textLight }}>
            {stats?.total_uploaded || 0} of {stats?.total_documents || 0} uploaded
          </div>
        </div>
        <button 
          onClick={onToggle}
          style={{
            background: 'none',
            border: 'none',
            fontSize: '1.2rem',
            cursor: 'pointer'
          }}
        >
          ✕
        </button>
      </div>
      
      {/* Progress bar */}
      <div style={{ padding: '0.5rem 1rem', background: '#f9fafb' }}>
        <div style={{
          height: '8px',
          background: '#e1e8ed',
          borderRadius: '4px',
          overflow: 'hidden'
        }}>
          <div style={{
            height: '100%',
            width: `${((stats?.total_uploaded || 0) / (stats?.total_documents || 1)) * 100}%`,
            background: stats?.required_complete ? COLORS.grassGreen : '#d97706',
            borderRadius: '4px',
            transition: 'width 0.3s ease'
          }} />
        </div>
      </div>
      
      {/* Processing jobs */}
      {processing_jobs?.length > 0 && (
        <div style={{ padding: '0.5rem 1rem', background: '#fffbeb', borderBottom: '1px solid #fcd34d' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#d97706', marginBottom: '0.25rem' }}>
            ⏳ Processing:
          </div>
          {processing_jobs.map((job, i) => (
            <div key={i} style={{ fontSize: '0.75rem', marginBottom: '0.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{job.filename?.slice(0, 25)}{job.filename?.length > 25 ? '...' : ''}</span>
                <span>{job.progress || 0}%</span>
              </div>
              <div style={{
                height: '4px',
                background: '#fcd34d',
                borderRadius: '2px',
                overflow: 'hidden'
              }}>
                <div style={{
                  height: '100%',
                  width: `${job.progress || 0}%`,
                  background: '#d97706',
                  transition: 'width 0.3s ease'
                }} />
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Document list */}
      <div style={{ overflow: 'auto', maxHeight: 'calc(100vh - 350px)' }}>
        {docs?.map((doc, i) => (
          <div 
            key={i}
            style={{
              padding: '0.75rem 1rem',
              borderBottom: '1px solid #f3f4f6',
              display: 'flex',
              gap: '0.5rem',
              alignItems: 'flex-start'
            }}
          >
            <span style={{ fontSize: '1rem' }}>{getStatusIcon(doc.status)}</span>
            <div style={{ flex: 1 }}>
              <div style={{ 
                fontWeight: doc.required ? '600' : '400',
                fontSize: '0.8rem',
                color: getStatusColor(doc.status)
              }}>
                {doc.document_name}
                {doc.required && <span style={{ color: '#dc2626' }}> *</span>}
              </div>
              <div style={{ fontSize: '0.7rem', color: COLORS.textLight }}>
                {doc.status === 'uploaded' && doc.matched_file 
                  ? `✓ ${doc.matched_file.slice(0, 30)}${doc.matched_file.length > 30 ? '...' : ''}`
                  : doc.status === 'processing'
                  ? 'Processing...'
                  : `Actions: ${doc.actions?.join(', ')}`
                }
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* Required indicator */}
      <div style={{ 
        padding: '0.5rem 1rem', 
        background: '#f9fafb', 
        borderTop: '1px solid #e1e8ed',
        fontSize: '0.7rem',
        color: COLORS.textLight 
      }}>
        <span style={{ color: '#dc2626' }}>*</span> = Required document
      </div>
    </div>
  );
}

// =============================================================================
// TOOLTIP COMPONENTS
// =============================================================================

// Tooltip Modal for Adding/Editing
function TooltipModal({ isOpen, onClose, onSave, actionId, existingTooltip }) {
  const [tooltipType, setTooltipType] = useState(existingTooltip?.tooltip_type || 'hint');
  const [title, setTitle] = useState(existingTooltip?.title || '');
  const [content, setContent] = useState(existingTooltip?.content || '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (existingTooltip) {
      setTooltipType(existingTooltip.tooltip_type || 'hint');
      setTitle(existingTooltip.title || '');
      setContent(existingTooltip.content || '');
    } else {
      setTooltipType('hint');
      setTitle('');
      setContent('');
    }
  }, [existingTooltip, isOpen]);

  if (!isOpen) return null;

  const handleSave = async () => {
    if (!content.trim()) return;
    setSaving(true);
    try {
      await onSave({
        action_id: actionId,
        tooltip_type: tooltipType,
        title: title.trim() || null,
        content: content.trim()
      });
      onClose();
    } catch (e) {
      console.error('Failed to save tooltip:', e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '1.5rem',
        width: '90%',
        maxWidth: '500px',
        maxHeight: '90vh',
        overflow: 'auto'
      }}>
        <h3 style={{ margin: '0 0 1rem', color: COLORS.text }}>
          {existingTooltip ? 'Edit' : 'Add'} Note for {actionId}
        </h3>

        {/* Type Selection */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
            Type
          </label>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {Object.entries(TOOLTIP_TYPES).map(([key, config]) => (
              <button
                key={key}
                onClick={() => setTooltipType(key)}
                style={{
                  padding: '0.5rem 1rem',
                  border: tooltipType === key ? `2px solid ${config.color}` : '2px solid #e1e8ed',
                  borderRadius: '8px',
                  background: tooltipType === key ? config.bg : 'white',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem'
                }}
              >
                <span>{config.icon}</span>
                <span>{config.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Title (optional) */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
            Title (optional)
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Brief title..."
            style={{
              width: '100%',
              padding: '0.5rem',
              border: '1px solid #e1e8ed',
              borderRadius: '6px',
              fontSize: '0.9rem'
            }}
          />
        </div>

        {/* Content */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
            Content *
          </label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Enter your note, best practice, or guidance..."
            rows={4}
            style={{
              width: '100%',
              padding: '0.5rem',
              border: '1px solid #e1e8ed',
              borderRadius: '6px',
              fontSize: '0.9rem',
              resize: 'vertical'
            }}
          />
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem 1rem',
              border: '1px solid #e1e8ed',
              borderRadius: '6px',
              background: 'white',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!content.trim() || saving}
            style={{
              padding: '0.5rem 1rem',
              border: 'none',
              borderRadius: '6px',
              background: content.trim() ? COLORS.grassGreen : '#ccc',
              color: 'white',
              cursor: content.trim() ? 'pointer' : 'not-allowed'
            }}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

// Tooltip Display - Shows icons and handles hover/click
function TooltipDisplay({ tooltips, onEdit, onDelete, isAdmin }) {
  const [activeTooltip, setActiveTooltip] = useState(null);
  const [hoveredIdx, setHoveredIdx] = useState(null);
  const [popoverPosition, setPopoverPosition] = useState({ top: 0, left: 0 });
  const iconRefs = React.useRef({});

  if (!tooltips || tooltips.length === 0) return null;

  const handleIconClick = (e, idx) => {
    e.stopPropagation();
    if (activeTooltip === idx) {
      setActiveTooltip(null);
    } else {
      // Calculate position relative to viewport
      const rect = iconRefs.current[idx]?.getBoundingClientRect();
      if (rect) {
        setPopoverPosition({
          top: rect.bottom + 8,
          left: Math.max(20, Math.min(rect.left - 150, window.innerWidth - 370))
        });
      }
      setActiveTooltip(idx);
    }
  };

  // Close on click outside
  React.useEffect(() => {
    const handleClickOutside = () => setActiveTooltip(null);
    if (activeTooltip !== null) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [activeTooltip]);

  return (
    <>
      <div style={{ display: 'flex', gap: '0.4rem', marginLeft: '0.5rem' }}>
        {tooltips.map((tip, idx) => {
          const config = TOOLTIP_TYPES[tip.tooltip_type] || TOOLTIP_TYPES.hint;
          const isActive = activeTooltip === idx;
          const isHovered = hoveredIdx === idx;

          return (
            <span
              key={tip.id || idx}
              ref={el => iconRefs.current[idx] = el}
              onClick={(e) => handleIconClick(e, idx)}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              style={{ 
                cursor: 'pointer', 
                fontSize: '1.1rem',
                transition: 'all 0.2s ease',
                transform: isHovered ? 'scale(1.3)' : 'scale(1)',
                filter: isHovered 
                  ? `drop-shadow(0 0 6px ${config.color})`
                  : 'drop-shadow(0 1px 2px rgba(0,0,0,0.2))',
                animation: tip.is_unread ? 'pulse 2s infinite' : 'none',
              }}
              title={`${config.label}: Click to view`}
            >
              {config.icon}
            </span>
          );
        })}
      </div>

      {/* Popover Portal - Fixed position, won't clip */}
      {activeTooltip !== null && tooltips[activeTooltip] && (
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            position: 'fixed',
            top: popoverPosition.top,
            left: popoverPosition.left,
            background: 'white',
            border: `2px solid ${(TOOLTIP_TYPES[tooltips[activeTooltip].tooltip_type] || TOOLTIP_TYPES.hint).color}`,
            borderRadius: '10px',
            padding: '1rem',
            width: '340px',
            maxHeight: '400px',
            overflowY: 'auto',
            boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
            zIndex: 9999
          }}
        >
          {(() => {
            const tip = tooltips[activeTooltip];
            const config = TOOLTIP_TYPES[tip.tooltip_type] || TOOLTIP_TYPES.hint;
            return (
              <>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '0.5rem',
                  marginBottom: '0.75rem',
                  paddingBottom: '0.5rem',
                  borderBottom: `1px solid ${config.color}40`
                }}>
                  <span style={{ fontSize: '1.3rem' }}>{config.icon}</span>
                  <span style={{ 
                    color: config.color,
                    fontWeight: '700',
                    fontSize: '0.95rem'
                  }}>
                    {tip.title || config.label}
                  </span>
                </div>
                <div style={{ 
                  fontSize: '0.9rem', 
                  color: COLORS.text,
                  lineHeight: '1.5',
                  whiteSpace: 'pre-wrap'
                }}>
                  {tip.content}
                </div>
                
                {isAdmin && (
                  <div style={{ 
                    display: 'flex', 
                    gap: '0.5rem', 
                    marginTop: '1rem',
                    paddingTop: '0.75rem',
                    borderTop: '1px solid #e1e8ed'
                  }}>
                    <button
                      onClick={() => { onEdit(tip); setActiveTooltip(null); }}
                      style={{
                        fontSize: '0.8rem',
                        padding: '0.35rem 0.75rem',
                        border: '1px solid #e1e8ed',
                        borderRadius: '4px',
                        background: 'white',
                        cursor: 'pointer'
                      }}
                    >
                      ✏️ Edit
                    </button>
                    <button
                      onClick={() => { onDelete(tip.id); setActiveTooltip(null); }}
                      style={{
                        fontSize: '0.8rem',
                        padding: '0.35rem 0.75rem',
                        border: '1px solid #fee2e2',
                        borderRadius: '4px',
                        background: '#fee2e2',
                        color: '#dc2626',
                        cursor: 'pointer'
                      }}
                    >
                      🗑️ Delete
                    </button>
                  </div>
                )}

                {/* Close X */}
                <button
                  onClick={() => setActiveTooltip(null)}
                  style={{
                    position: 'absolute',
                    top: '0.5rem',
                    right: '0.75rem',
                    border: 'none',
                    background: 'none',
                    cursor: 'pointer',
                    fontSize: '1.2rem',
                    color: '#999',
                    padding: '0.25rem'
                  }}
                >
                  ×
                </button>
              </>
            );
          })()}
        </div>
      )}

      {/* CSS Animation for pulse */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </>
  );
}

// Action Card Component
function ActionCard({ action, stepNumber, progress, projectId, onUpdate, tooltips, isAdmin, onAddTooltip, onEditTooltip, onDeleteTooltip }) {
  const [expanded, setExpanded] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [notes, setNotes] = useState(progress?.notes || '');
  const [localStatus, setLocalStatus] = useState(progress?.status || 'not_started');
  const [localDocsFound, setLocalDocsFound] = useState(progress?.documents_found || []);
  const fileInputRef = React.useRef(null);
  
  // Sync local docs with progress prop - MUST be before any conditional returns
  React.useEffect(() => {
    setLocalDocsFound(progress?.documents_found || []);
  }, [progress?.documents_found]);
  
  // Safety check - if no action, don't render (AFTER all hooks)
  if (!action) {
    return null;
  }
  
  const findings = progress?.findings;
  const reportsNeeded = action.reports_needed || [];
  const expectedCount = reportsNeeded.length || 1;
  
  const statusConfig = STATUS_OPTIONS.find(s => s.value === localStatus) || STATUS_OPTIONS[0];

  const handleScan = async () => {
    setScanning(true);
    try {
      const res = await api.post(`/playbooks/year-end/scan/${projectId}/${action.action_id}`);
      console.log('[SCAN] Response:', res.data);
      if (res.data) {
        const newDocs = res.data.documents?.map(d => d.filename) || [];
        console.log('[SCAN] Found docs:', newDocs);
        setLocalDocsFound(newDocs);
        setLocalStatus(res.data.suggested_status);
        onUpdate(action.action_id, {
          status: res.data.suggested_status,
          findings: res.data.findings,
          documents_found: newDocs
        });
      }
    } catch (err) {
      console.error('Scan failed:', err);
    } finally {
      setScanning(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    setUploading(true);
    setUploadStatus(null);
    
    try {
      const jobIds = [];
      
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('project', projectId);
        
        const res = await api.post('/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        if (res.data?.job_id) {
          jobIds.push(res.data.job_id);
        }
      }
      
      setUploading(false);
      setUploadStatus('processing');
      
      const pollJobs = async () => {
        let allComplete = false;
        let attempts = 0;
        const maxAttempts = 60;
        
        while (!allComplete && attempts < maxAttempts) {
          await new Promise(r => setTimeout(r, 2000));
          attempts++;
          
          try {
            const jobsRes = await api.get('/jobs');
            const jobs = jobsRes.data?.jobs || [];
            
            const ourJobs = jobs.filter(j => jobIds.includes(j.id));
            allComplete = ourJobs.length > 0 && ourJobs.every(j => 
              j.status === 'completed' || j.status === 'failed'
            );
            
            const failed = ourJobs.filter(j => j.status === 'failed');
            if (failed.length > 0) {
              setUploadStatus('error');
              setTimeout(() => setUploadStatus(null), 3000);
              return;
            }
          } catch (err) {
            console.error('Job poll failed:', err);
          }
        }
        
        if (allComplete) {
          setUploadStatus('scanning');
          await handleScan();
          setUploadStatus('success');
          setTimeout(() => setUploadStatus(null), 2000);
        } else {
          setUploadStatus(null);
        }
      };
      
      pollJobs();
      
    } catch (err) {
      console.error('Upload failed:', err);
      setUploadStatus('error');
      setTimeout(() => setUploadStatus(null), 3000);
      setUploading(false);
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleStatusChange = async (newStatus) => {
    setLocalStatus(newStatus);
    try {
      await api.post(`/playbooks/year-end/progress/${projectId}/${action.action_id}`, {
        status: newStatus,
        notes: notes,
        findings: findings
      });
      onUpdate(action.action_id, { status: newStatus });
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleNotesBlur = async () => {
    try {
      await api.post(`/playbooks/year-end/progress/${projectId}/${action.action_id}`, {
        status: localStatus,
        notes: notes,
        findings: findings
      });
      onUpdate(action.action_id, { notes });
    } catch (err) {
      console.error('Failed to save notes:', err);
    }
  };

  const getUploadButtonContent = () => {
    if (uploading) return '⏳ Uploading...';
    if (uploadStatus === 'processing') return '⏳ Processing...';
    if (uploadStatus === 'scanning') return '🔍 Scanning...';
    if (uploadStatus === 'success') return '✓ Done!';
    if (uploadStatus === 'error') return '✗ Failed';
    return (
      <>
        📤 Upload Document
        <span style={styles.docCount}>
          {localDocsFound.length}/{expectedCount}
        </span>
      </>
    );
  };

  const getUploadButtonStyle = () => {
    if (uploadStatus === 'success') {
      return { ...styles.uploadBtn, background: '#C6EFCE', color: '#006600' };
    }
    if (uploadStatus === 'error') {
      return { ...styles.uploadBtn, background: '#FFC7CE', color: '#9C0006' };
    }
    if (uploadStatus === 'processing' || uploadStatus === 'scanning') {
      return { ...styles.uploadBtn, background: '#FFEB9C', color: '#9C6500' };
    }
    return styles.uploadBtn;
  };

  const styles = {
    card: {
      background: 'white',
      borderRadius: '10px',
      border: '1px solid #e1e8ed',
      marginBottom: '0.75rem',
      overflow: 'hidden',
    },
    header: {
      display: 'flex',
      alignItems: 'flex-start',
      padding: '1rem',
      cursor: 'pointer',
      gap: '1rem',
    },
    actionId: {
      fontFamily: "'Ubuntu Mono', monospace",
      fontWeight: '700',
      fontSize: '0.9rem',
      color: COLORS.text,
      background: '#f0f4f7',
      padding: '0.25rem 0.5rem',
      borderRadius: '4px',
      flexShrink: 0,
    },
    content: {
      flex: 1,
    },
    description: {
      fontSize: '0.9rem',
      color: COLORS.text,
      lineHeight: '1.4',
      marginBottom: '0.5rem',
    },
    meta: {
      display: 'flex',
      gap: '1rem',
      flexWrap: 'wrap',
      alignItems: 'center',
    },
    dueDate: {
      fontSize: '0.75rem',
      color: '#dc2626',
      fontWeight: '600',
    },
    actionType: {
      fontSize: '0.7rem',
      padding: '0.15rem 0.4rem',
      borderRadius: '3px',
      fontWeight: '600',
      textTransform: 'uppercase',
      background: action.action_type === 'required' ? '#fee2e2' : '#e0f2fe',
      color: action.action_type === 'required' ? '#b91c1c' : '#0369a1',
    },
    statusBadge: {
      fontSize: '0.75rem',
      padding: '0.25rem 0.5rem',
      borderRadius: '4px',
      fontWeight: '600',
      background: statusConfig.bg,
      color: statusConfig.color,
      marginLeft: 'auto',
    },
    expandIcon: {
      fontSize: '1.25rem',
      color: COLORS.textLight,
      transition: 'transform 0.2s',
      transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
    },
    expandedContent: {
      padding: '0 1rem 1rem 1rem',
      borderTop: '1px solid #e1e8ed',
      background: '#fafbfc',
    },
    section: {
      marginBottom: '1rem',
    },
    sectionTitle: {
      fontSize: '0.75rem',
      fontWeight: '700',
      color: COLORS.textLight,
      textTransform: 'uppercase',
      marginBottom: '0.5rem',
    },
    findingsBox: {
      background: findings?.complete ? '#d1fae5' : '#fef3c7',
      border: `1px solid ${findings?.complete ? '#86efac' : '#fcd34d'}`,
      borderRadius: '8px',
      padding: '0.75rem',
    },
    keyValue: {
      display: 'flex',
      justifyContent: 'space-between',
      fontSize: '0.85rem',
      marginBottom: '0.25rem',
    },
    keyLabel: {
      color: COLORS.textLight,
    },
    keyVal: {
      fontWeight: '600',
      color: COLORS.text,
    },
    issuesList: {
      margin: '0.5rem 0 0 0',
      paddingLeft: '1.25rem',
    },
    issue: {
      fontSize: '0.85rem',
      color: '#b91c1c',
      marginBottom: '0.25rem',
    },
    docsFound: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '0.5rem',
    },
    docBadge: {
      fontSize: '0.75rem',
      padding: '0.25rem 0.5rem',
      background: '#dbeafe',
      color: '#1e40af',
      borderRadius: '4px',
    },
    statusSelect: {
      display: 'flex',
      gap: '0.5rem',
      flexWrap: 'wrap',
    },
    statusBtn: (isActive, config) => ({
      padding: '0.4rem 0.75rem',
      fontSize: '0.8rem',
      fontWeight: '600',
      border: `2px solid ${isActive ? config.color : '#e1e8ed'}`,
      background: isActive ? config.bg : 'white',
      color: isActive ? config.color : COLORS.textLight,
      borderRadius: '6px',
      cursor: 'pointer',
    }),
    notesArea: {
      width: '100%',
      padding: '0.5rem',
      border: '1px solid #e1e8ed',
      borderRadius: '6px',
      fontSize: '0.85rem',
      minHeight: '60px',
      resize: 'vertical',
      fontFamily: 'inherit',
    },
    buttonRow: {
      display: 'flex',
      gap: '0.75rem',
      flexWrap: 'wrap',
    },
    uploadBtn: {
      padding: '0.5rem 1rem',
      background: COLORS.clearwater,
      color: COLORS.text,
      border: 'none',
      borderRadius: '6px',
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      transition: 'background 0.2s, color 0.2s',
    },
    scanBtn: {
      padding: '0.5rem 1rem',
      background: COLORS.grassGreen,
      color: 'white',
      border: 'none',
      borderRadius: '6px',
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    reportsNeeded: {
      fontSize: '0.8rem',
      color: COLORS.textLight,
      fontStyle: 'italic',
    },
    hiddenInput: {
      display: 'none',
    },
    docCount: {
      fontSize: '0.7rem',
      background: COLORS.turkishSea,
      color: 'white',
      padding: '0.1rem 0.4rem',
      borderRadius: '10px',
    },
  };

  return (
    <div style={styles.card}>
      <div style={styles.header} onClick={() => setExpanded(!expanded)}>
        <span style={styles.actionId}>{action.action_id || '?'}</span>
        
        {/* Tooltip icons */}
        <TooltipDisplay 
          tooltips={tooltips} 
          onEdit={onEditTooltip}
          onDelete={onDeleteTooltip}
          isAdmin={isAdmin}
        />
        
        {/* Admin add button */}
        {isAdmin && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAddTooltip(action.action_id);
            }}
            style={{
              marginLeft: '0.3rem',
              padding: '0 0.4rem',
              border: '1px dashed #ccc',
              borderRadius: '4px',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: '0.9rem',
              color: '#999',
              lineHeight: '1.2'
            }}
            title="Add note"
          >
            +
          </button>
        )}
        
        <div style={styles.content}>
          <div style={styles.description}>{action.description || 'No description'}</div>
          <div style={styles.meta}>
            {action.due_date && (
              <span style={styles.dueDate}>📅 Due: {action.due_date}</span>
            )}
            <span style={styles.actionType}>{action.action_type || 'unknown'}</span>
            {localDocsFound.length > 0 && (
              <span style={{ fontSize: '0.75rem', color: COLORS.grassGreen }}>
                ✓ {localDocsFound.length} doc{localDocsFound.length > 1 ? 's' : ''} found
              </span>
            )}
          </div>
        </div>
        <span style={styles.statusBadge}>{statusConfig.label}</span>
        <span style={styles.expandIcon}>{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && (
        <div style={styles.expandedContent}>
          {reportsNeeded.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Reports Needed</div>
              <div style={styles.reportsNeeded}>
                {reportsNeeded.join(', ')}
              </div>
            </div>
          )}

          {/* Show dependency info if this action inherits from others */}
          {(() => {
            const parents = getParentActions(action.action_id);
            if (parents.length > 0 && reportsNeeded.length === 0) {
              return (
                <div style={{
                  background: '#eff6ff',
                  border: '1px solid #bfdbfe',
                  padding: '0.6rem 0.75rem',
                  borderRadius: '6px',
                  marginBottom: '0.75rem',
                  fontSize: '0.8rem',
                  color: '#1e40af',
                }}>
                  <span style={{ marginRight: '0.5rem' }}>💡</span>
                  <strong>No upload needed</strong> - This action uses data from action{parents.length > 1 ? 's' : ''} {parents.join(', ')}. 
                  Click "Scan Documents" to analyze.
                </div>
              );
            }
            return null;
          })()}

          <div style={styles.section}>
            <div style={styles.buttonRow}>
              <input
                type="file"
                ref={fileInputRef}
                style={styles.hiddenInput}
                onChange={handleFileChange}
                multiple
                accept=".pdf,.xlsx,.xls,.csv,.docx,.doc,.txt"
              />
              <button 
                style={getUploadButtonStyle()} 
                onClick={(e) => { e.stopPropagation(); handleUploadClick(); }}
                disabled={uploading || scanning || uploadStatus === 'processing' || uploadStatus === 'scanning'}
              >
                {getUploadButtonContent()}
              </button>
              <button 
                style={styles.scanBtn} 
                onClick={(e) => { e.stopPropagation(); handleScan(); }}
                disabled={scanning || uploading}
              >
                {scanning ? '⏳ Scanning...' : '🔍 Scan Documents'}
              </button>
            </div>
          </div>

          {localDocsFound.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Documents Found ({localDocsFound.length})</div>
              <div style={styles.docsFound}>
                {localDocsFound.map((doc, i) => (
                  <span key={i} style={styles.docBadge}>📄 {doc}</span>
                ))}
              </div>
            </div>
          )}

          {/* Show inherited indicator if applicable */}
          {progress?.inherited_from && progress.inherited_from.length > 0 && (
            <div style={{ 
              background: '#e0f2fe', 
              padding: '0.5rem 0.75rem', 
              borderRadius: '6px', 
              marginBottom: '0.75rem',
              fontSize: '0.8rem',
              color: '#0369a1',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <span>🔗</span>
              <span>Using data from action{progress.inherited_from.length > 1 ? 's' : ''}: <strong>{progress.inherited_from.join(', ')}</strong></span>
            </div>
          )}
          
          {/* Show review flag warning if action was impacted by new data */}
          {progress?.review_flag && (
            <div style={{ 
              background: '#fef3c7', 
              padding: '0.75rem', 
              borderRadius: '6px', 
              marginBottom: '0.75rem',
              fontSize: '0.85rem',
              color: '#92400e',
              border: '1px solid #fcd34d'
            }}>
              <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                🔄 Review Recommended
              </div>
              <div>{progress.review_flag.reason}</div>
              <div style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: '#b45309' }}>
                Triggered by update to action {progress.review_flag.triggered_by}
              </div>
            </div>
          )}
          
          {/* Show guidance for dependent actions */}
          {findings?.is_dependent && findings?.guidance && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>📋 Action Guidance</div>
              <div style={{
                background: '#f0f9ff',
                border: '1px solid #bae6fd',
                borderRadius: '8px',
                padding: '1rem',
                fontSize: '0.85rem',
                lineHeight: '1.6',
                whiteSpace: 'pre-wrap'
              }}>
                {findings.guidance}
              </div>
            </div>
          )}

          {findings && typeof findings === 'object' && (
            <div style={styles.section}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={styles.sectionTitle}>AI Analysis</div>
                {findings.risk_level && (
                  <span style={{
                    padding: '0.2rem 0.6rem',
                    borderRadius: '12px',
                    fontSize: '0.7rem',
                    fontWeight: '600',
                    textTransform: 'uppercase',
                    background: findings.risk_level === 'high' ? '#fee2e2' : 
                               findings.risk_level === 'medium' ? '#fef3c7' : '#d1fae5',
                    color: findings.risk_level === 'high' ? '#dc2626' : 
                           findings.risk_level === 'medium' ? '#d97706' : '#059669',
                  }}>
                    {findings.risk_level} risk
                  </span>
                )}
              </div>
              <div style={styles.findingsBox}>
                {findings.summary && (
                  <p style={{ margin: '0 0 0.75rem 0', fontSize: '0.85rem', lineHeight: '1.5' }}>
                    {typeof findings.summary === 'string' ? findings.summary : JSON.stringify(findings.summary)}
                  </p>
                )}
                {findings.key_values && typeof findings.key_values === 'object' && !Array.isArray(findings.key_values) && Object.keys(findings.key_values).length > 0 && (
                  <div style={{ marginBottom: '0.75rem' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#374151', marginBottom: '0.3rem' }}>Key Values:</div>
                    {Object.entries(findings.key_values).map(([key, val]) => (
                      <div key={key} style={styles.keyValue}>
                        <span style={styles.keyLabel}>{String(key)}:</span>
                        <span style={styles.keyVal}>
                          {val === null || val === undefined ? '-' : (typeof val === 'object' ? JSON.stringify(val) : String(val))}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {Array.isArray(findings.issues) && findings.issues.length > 0 && (
                  <div style={{ marginBottom: '0.75rem' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#dc2626', marginBottom: '0.3rem' }}>⚠️ Issues to Address:</div>
                    <ul style={styles.issuesList}>
                      {findings.issues.map((issue, i) => (
                        <li key={i} style={styles.issue}>
                          {typeof issue === 'string' ? issue : JSON.stringify(issue)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {Array.isArray(findings.recommendations) && findings.recommendations.length > 0 && (
                  <div style={{ marginBottom: '0.5rem' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#059669', marginBottom: '0.3rem' }}>✅ Recommendations:</div>
                    <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.8rem' }}>
                      {findings.recommendations.map((rec, i) => (
                        <li key={i} style={{ marginBottom: '0.3rem', color: '#065f46' }}>
                          {typeof rec === 'string' ? rec : JSON.stringify(rec)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          <div style={styles.section}>
            <div style={styles.sectionTitle}>Status</div>
            <div style={styles.statusSelect}>
              {STATUS_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  style={styles.statusBtn(localStatus === opt.value, opt)}
                  onClick={(e) => { e.stopPropagation(); handleStatusChange(opt.value); }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div style={styles.section}>
            <div style={styles.sectionTitle}>Consultant Notes</div>
            <textarea
              style={styles.notesArea}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              onBlur={handleNotesBlur}
              onClick={(e) => e.stopPropagation()}
              placeholder="Add notes, findings, or follow-up items..."
            />
          </div>
        </div>
      )}
    </div>
  );
}

// Step Accordion Component - WITH FULL SAFETY CHECKS
function StepAccordion({ step, progress, projectId, onUpdate, tooltipsByAction, isAdmin, onAddTooltip, onEditTooltip, onDeleteTooltip }) {
  const [expanded, setExpanded] = useState(true);
  
  // CRITICAL: Safety check FIRST before any property access
  if (!step) {
    console.warn('[StepAccordion] Received undefined step, skipping render');
    return null;
  }
  
  const actions = step.actions || [];
  const completedCount = actions.filter(a => 
    a && (progress[a.action_id]?.status === 'complete' || progress[a.action_id]?.status === 'na')
  ).length;
  const totalCount = actions.length;
  const allComplete = totalCount > 0 && completedCount === totalCount;

  // Safe phase check - MUST be after null check
  const isBefore = step.phase === 'before_final_payroll';

  const styles = {
    container: {
      marginBottom: '1.5rem',
    },
    header: {
      display: 'flex',
      alignItems: 'center',
      padding: '1rem',
      background: allComplete ? '#d1fae5' : 'white',
      borderRadius: '12px',
      border: '1px solid #e1e8ed',
      cursor: 'pointer',
      gap: '1rem',
    },
    stepNumber: {
      fontFamily: "'Sora', sans-serif",
      fontWeight: '700',
      fontSize: '1rem',
      color: 'white',
      background: allComplete ? '#059669' : COLORS.grassGreen,
      width: '36px',
      height: '36px',
      borderRadius: '8px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    },
    stepName: {
      flex: 1,
      fontFamily: "'Sora', sans-serif",
      fontWeight: '600',
      fontSize: '1rem',
      color: COLORS.text,
    },
    progressText: {
      fontSize: '0.85rem',
      color: COLORS.textLight,
    },
    phaseBadge: {
      fontSize: '0.7rem',
      padding: '0.2rem 0.5rem',
      borderRadius: '4px',
      fontWeight: '600',
      textTransform: 'uppercase',
      background: isBefore ? '#dbeafe' : '#fae8ff',
      color: isBefore ? '#1e40af' : '#86198f',
    },
    expandIcon: {
      fontSize: '1.25rem',
      color: COLORS.textLight,
    },
    actionsContainer: {
      marginTop: '0.75rem',
      paddingLeft: '1rem',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.header} onClick={() => setExpanded(!expanded)}>
        <div style={styles.stepNumber}>{step.step_number || '?'}</div>
        <div style={styles.stepName}>{step.step_name || 'Unknown Step'}</div>
        <span style={styles.phaseBadge}>
          {isBefore ? 'Before Final' : 'After Final'}
        </span>
        <span style={styles.progressText}>
          {completedCount}/{totalCount} {allComplete && '✓'}
        </span>
        <span style={styles.expandIcon}>{expanded ? '▼' : '▶'}</span>
      </div>
      
      {expanded && (
        <div style={styles.actionsContainer}>
          {actions.map(action => action ? (
            <ActionCard
              key={action.action_id}
              action={action}
              stepNumber={step.step_number}
              progress={progress[action.action_id] || {}}
              projectId={projectId}
              onUpdate={onUpdate}
              tooltips={tooltipsByAction[action.action_id] || []}
              isAdmin={isAdmin}
              onAddTooltip={onAddTooltip}
              onEditTooltip={onEditTooltip}
              onDeleteTooltip={onDeleteTooltip}
            />
          ) : null)}
        </div>
      )}
    </div>
  );
}

// Main Component
export default function YearEndPlaybook({ project, projectName, customerName, onClose }) {
  const [structure, setStructure] = useState(null);
  const [progress, setProgress] = useState({});
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeProgress, setAnalyzeProgress] = useState({ current: 0, total: 0 });
  const [activePhase, setActivePhase] = useState('all');
  
  // NEW: Document checklist and AI summary state
  const [docChecklist, setDocChecklist] = useState(null);
  const [aiSummary, setAiSummary] = useState(null);
  const [summaryExpanded, setSummaryExpanded] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // TOOLTIPS: State for consultant-driven notes
  const [tooltipsByAction, setTooltipsByAction] = useState({});
  const [tooltipModalOpen, setTooltipModalOpen] = useState(false);
  const [tooltipModalActionId, setTooltipModalActionId] = useState(null);
  const [editingTooltip, setEditingTooltip] = useState(null);
  
  // TODO: Replace with actual auth check
  const isAdmin = true;

  // SAFETY: Only load if project exists
  useEffect(() => {
    if (project?.id) {
      loadPlaybook();
      loadDocChecklist();
      loadAiSummary();
      loadTooltips();
    }
  }, [project]);
  
  // Poll for processing jobs updates
  useEffect(() => {
    if (!project?.id) return;
    
    const interval = setInterval(() => {
      // Only poll if there are processing jobs
      if (docChecklist?.processing_jobs?.length > 0) {
        loadDocChecklist();
      }
    }, 3000); // Poll every 3 seconds
    
    return () => clearInterval(interval);
  }, [project?.id, docChecklist?.processing_jobs?.length]);

  const loadPlaybook = async () => {
    setLoading(true);
    try {
      const [structRes, progressRes] = await Promise.all([
        api.get('/playbooks/year-end/structure'),
        api.get(`/playbooks/year-end/progress/${project.id}`)
      ]);
      
      setStructure(structRes.data);
      setProgress(progressRes.data?.progress || {});
    } catch (err) {
      console.error('Failed to load playbook:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const loadDocChecklist = async () => {
    try {
      const res = await api.get(`/playbooks/year-end/document-checklist/${project.id}`);
      setDocChecklist(res.data);
    } catch (err) {
      console.error('Failed to load document checklist:', err);
    }
  };
  
  const loadAiSummary = async () => {
    try {
      const res = await api.get(`/playbooks/year-end/summary/${project.id}`);
      setAiSummary(res.data);
    } catch (err) {
      console.error('Failed to load AI summary:', err);
    }
  };
  
  // TOOLTIP FUNCTIONS
  const loadTooltips = async () => {
    try {
      const res = await api.get('/playbooks/tooltips/bulk/year-end-2025');
      setTooltipsByAction(res.data?.tooltips_by_action || {});
    } catch (err) {
      console.error('Failed to load tooltips:', err);
    }
  };
  
  const handleAddTooltip = (actionId) => {
    setTooltipModalActionId(actionId);
    setEditingTooltip(null);
    setTooltipModalOpen(true);
  };
  
  const handleEditTooltip = (tooltip) => {
    setTooltipModalActionId(tooltip.action_id);
    setEditingTooltip(tooltip);
    setTooltipModalOpen(true);
  };
  
  const handleSaveTooltip = async (data) => {
    try {
      if (editingTooltip) {
        await api.put(`/playbooks/tooltips/${editingTooltip.id}`, data);
      } else {
        await api.post('/playbooks/tooltips', data);
      }
      await loadTooltips();
    } catch (err) {
      console.error('Failed to save tooltip:', err);
      throw err;
    }
  };
  
  const handleDeleteTooltip = async (tooltipId) => {
    if (!window.confirm('Delete this note?')) return;
    try {
      await api.delete(`/playbooks/tooltips/${tooltipId}`);
      await loadTooltips();
    } catch (err) {
      console.error('Failed to delete tooltip:', err);
    }
  };
  
  // Refresh all data
  const refreshAll = async () => {
    await Promise.all([loadPlaybook(), loadDocChecklist(), loadAiSummary()]);
  };

  const handleUpdate = (actionId, updates) => {
    setProgress(prev => ({
      ...prev,
      [actionId]: { ...prev[actionId], ...updates }
    }));
  };

  const handleReset = async () => {
    if (!window.confirm('Reset all progress for this playbook? This cannot be undone.')) {
      return;
    }
    
    try {
      await api.delete(`/playbooks/year-end/progress/${project.id}`);
      setProgress({});
      alert('Progress reset. Refreshing...');
      window.location.reload();
    } catch (err) {
      console.error('Reset failed:', err);
      alert('Failed to reset progress');
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await api.get(
        `/playbooks/year-end/export/${project.id}?customer_name=${encodeURIComponent(customerName || 'Customer')}`,
        { responseType: 'blob' }
      );
      
      const blob = new Blob([res.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${(customerName || 'Customer').replace(/[^a-zA-Z0-9]/g, '_')}_Year_End_Progress.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  const handleAnalyzeAll = async () => {
    if (!window.confirm('Analyze all documents for this playbook? This may take 1-2 minutes.')) {
      return;
    }
    
    setAnalyzing(true);
    setAnalyzeProgress({ current: 0, total: 0 });
    
    try {
      const res = await api.post(`/playbooks/year-end/scan-all/${project.id}`);
      const results = res.data;
      
      // Reload all data to show updated findings
      await refreshAll();
      
      const successful = results.successful || 0;
      const failed = results.failed || 0;
      
      if (failed > 0) {
        alert(`Analysis complete: ${successful} actions analyzed, ${failed} failed. Some actions may need manual review.`);
      } else {
        alert(`Analysis complete: ${successful} actions analyzed successfully!`);
      }
    } catch (err) {
      console.error('Analyze all failed:', err);
      alert('Analysis failed. Please try again.');
    } finally {
      setAnalyzing(false);
    }
  };
  
  const handleRefreshStructure = async () => {
    if (!window.confirm('Refresh playbook structure from Global Library and re-analyze all documents? This may take 1-2 minutes.')) {
      return;
    }
    
    setAnalyzing(true);
    
    try {
      // Step 1: Refresh structure
      const structRes = await api.post('/playbooks/year-end/refresh-structure');
      
      if (!structRes.data.success) {
        alert('Failed to refresh structure');
        setAnalyzing(false);
        return;
      }
      
      const actionCount = structRes.data.total_actions || 0;
      const sourceFile = structRes.data.source_file || 'source file';
      
      // Reload structure
      await loadPlaybook();
      
      // Step 2: Re-analyze all actions
      const scanRes = await api.post(`/playbooks/year-end/scan-all/${project.id}`);
      const results = scanRes.data;
      
      // Reload all data
      await refreshAll();
      
      const successful = results.successful || 0;
      const failed = results.failed || 0;
      
      alert(`Structure refreshed (${actionCount} actions from ${sourceFile}) and re-analyzed: ${successful} successful, ${failed} failed.`);
      
    } catch (err) {
      console.error('Refresh and analyze failed:', err);
      alert('Failed to refresh structure. Check that Year-End Checklist is in Global Library.');
    } finally {
      setAnalyzing(false);
    }
  };

  // Calculate progress stats
  const totalActions = structure?.total_actions || 0;
  const completedActions = Object.values(progress).filter(p => 
    p.status === 'complete' || p.status === 'na'
  ).length;
  const progressPercent = totalActions > 0 ? Math.round((completedActions / totalActions) * 100) : 0;

  // Filter steps by phase
  const filteredSteps = structure?.steps?.filter(step => {
    if (activePhase === 'all') return true;
    return step.phase === activePhase;
  }) || [];

  const styles = {
    container: {
      maxWidth: '1000px',
      margin: '0 auto',
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      marginBottom: '1.5rem',
      flexWrap: 'wrap',
      gap: '1rem',
    },
    titleSection: {},
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.75rem',
      fontWeight: '700',
      color: COLORS.text,
      margin: 0,
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    subtitle: {
      color: COLORS.textLight,
      marginTop: '0.25rem',
    },
    headerActions: {
      display: 'flex',
      gap: '0.75rem',
    },
    backBtn: {
      padding: '0.5rem 1rem',
      background: 'white',
      border: '1px solid #e1e8ed',
      borderRadius: '8px',
      color: COLORS.textLight,
      fontWeight: '600',
      cursor: 'pointer',
    },
    resetBtn: {
      padding: '0.5rem 1rem',
      background: '#fee2e2',
      border: '1px solid #fecaca',
      borderRadius: '8px',
      color: '#dc2626',
      fontWeight: '600',
      cursor: 'pointer',
    },
    exportBtn: {
      padding: '0.5rem 1rem',
      background: COLORS.grassGreen,
      border: 'none',
      borderRadius: '8px',
      color: 'white',
      fontWeight: '600',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    analyzeAllBtn: {
      padding: '0.5rem 1rem',
      background: analyzing ? '#9ca3af' : '#3b82f6',
      border: 'none',
      borderRadius: '8px',
      color: 'white',
      fontWeight: '600',
      cursor: analyzing ? 'not-allowed' : 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    refreshStructureBtn: {
      padding: '0.5rem 1rem',
      background: analyzing ? '#9ca3af' : '#8b5cf6',
      border: 'none',
      borderRadius: '8px',
      color: 'white',
      fontWeight: '600',
      cursor: analyzing ? 'not-allowed' : 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    progressCard: {
      background: 'white',
      borderRadius: '12px',
      padding: '1.25rem',
      marginBottom: '1.5rem',
      border: '1px solid #e1e8ed',
    },
    progressBar: {
      height: '12px',
      background: '#e1e8ed',
      borderRadius: '6px',
      overflow: 'hidden',
      marginBottom: '0.75rem',
    },
    progressFill: {
      height: '100%',
      background: `linear-gradient(90deg, ${COLORS.grassGreen}, #6aa84f)`,
      borderRadius: '6px',
      transition: 'width 0.3s ease',
      width: `${progressPercent}%`,
    },
    progressStats: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    progressText: {
      fontWeight: '600',
      color: COLORS.text,
    },
    progressPercent: {
      fontSize: '1.5rem',
      fontWeight: '700',
      color: COLORS.grassGreen,
    },
    phaseFilter: {
      display: 'flex',
      gap: '0.5rem',
      marginBottom: '1.5rem',
    },
    phaseBtn: (isActive) => ({
      padding: '0.5rem 1rem',
      background: isActive ? COLORS.grassGreen : 'white',
      border: `1px solid ${isActive ? COLORS.grassGreen : '#e1e8ed'}`,
      borderRadius: '20px',
      color: isActive ? 'white' : COLORS.textLight,
      fontWeight: '600',
      fontSize: '0.85rem',
      cursor: 'pointer',
    }),
    loadingState: {
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '300px',
      color: COLORS.textLight,
      gap: '1rem',
    },
  };

  // SAFETY CHECK: If no project, show error
  if (!project?.id) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingState}>
          <span>Error: No project selected. Please go back and select a project.</span>
          <button style={styles.backBtn} onClick={onClose}>← Back</button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingState}>
          <span>Loading Year-End Checklist...</span>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex' }}>
      {/* Main Content */}
      <div style={{ ...styles.container, marginRight: sidebarCollapsed ? '40px' : '300px', transition: 'margin-right 0.3s ease' }}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.titleSection}>
            <h1 style={styles.title}>📅 Year-End Checklist</h1>
            <p style={styles.subtitle}>
              {customerName || 'Customer'} → {projectName || 'Project'}
            </p>
          </div>
          <div style={styles.headerActions}>
            <button style={styles.backBtn} onClick={onClose}>
              ← Back
            </button>
            <button 
              style={styles.refreshStructureBtn} 
              onClick={handleRefreshStructure}
              disabled={analyzing}
              title="Refresh playbook structure from Global Library and re-analyze all documents"
            >
              {analyzing ? '⏳ Refreshing...' : '🔄 Refresh & Analyze'}
            </button>
            <button 
              style={styles.analyzeAllBtn} 
              onClick={handleAnalyzeAll}
              disabled={analyzing}
              title="Analyze all uploaded documents for the entire playbook"
            >
              {analyzing ? '⏳ Analyzing...' : '🔍 Analyze All'}
            </button>
            <button 
              style={styles.resetBtn} 
              onClick={handleReset}
              title="Reset all progress for this project"
            >
              🗑️ Reset
            </button>
            <button style={styles.exportBtn} onClick={handleExport} disabled={exporting}>
              {exporting ? '⏳ Exporting...' : '📥 Export Progress'}
            </button>
          </div>
        </div>
        
        {/* AI Summary Dashboard */}
        <AISummaryDashboard 
          summary={aiSummary} 
          expanded={summaryExpanded} 
          onToggle={() => setSummaryExpanded(!summaryExpanded)} 
        />

        {/* Progress Card */}
        <div style={styles.progressCard}>
          <div style={styles.progressBar}>
            <div style={styles.progressFill} />
          </div>
          <div style={styles.progressStats}>
            <span style={styles.progressText}>
              {completedActions} of {totalActions} actions complete
            </span>
            <span style={styles.progressPercent}>{progressPercent}%</span>
          </div>
        </div>

        {/* Phase Filter */}
        <div style={styles.phaseFilter}>
          <button 
            style={styles.phaseBtn(activePhase === 'all')} 
            onClick={() => setActivePhase('all')}
          >
            All Steps
          </button>
          <button 
            style={styles.phaseBtn(activePhase === 'before_final_payroll')} 
            onClick={() => setActivePhase('before_final_payroll')}
          >
            Before Final Payroll
          </button>
          <button 
            style={styles.phaseBtn(activePhase === 'after_final_payroll')} 
            onClick={() => setActivePhase('after_final_payroll')}
          >
            After Final Payroll
          </button>
        </div>

        {/* Steps */}
        {filteredSteps.map(step => (
          <StepAccordion
            key={step.step_number || Math.random()}
            step={step}
            progress={progress}
            projectId={project.id}
            onUpdate={handleUpdate}
            tooltipsByAction={tooltipsByAction}
            isAdmin={isAdmin}
            onAddTooltip={handleAddTooltip}
            onEditTooltip={handleEditTooltip}
            onDeleteTooltip={handleDeleteTooltip}
          />
        ))}
      </div>
      
      {/* Document Checklist Sidebar */}
      <DocumentChecklistSidebar 
        checklist={docChecklist} 
        collapsed={sidebarCollapsed} 
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} 
      />
      
      {/* Tooltip Add/Edit Modal */}
      <TooltipModal
        isOpen={tooltipModalOpen}
        onClose={() => {
          setTooltipModalOpen(false);
          setEditingTooltip(null);
        }}
        onSave={handleSaveTooltip}
        actionId={tooltipModalActionId}
        existingTooltip={editingTooltip}
      />
    </div>
  );
}
