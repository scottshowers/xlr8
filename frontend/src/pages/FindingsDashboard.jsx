/**
 * FindingsDashboard.jsx - Auto-Surfaced Analysis Results
 * ======================================================
 * 
 * Phase 4A.4: Findings Dashboard
 * 
 * Shows analysis findings automatically after upload/processing.
 * No user query required - the platform surfaces what it found.
 * 
 * Created: January 14, 2026
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertTriangle, AlertCircle, Info, CheckCircle, ChevronRight,
  Filter, Download, RefreshCw, Loader2, BarChart3, FileText,
  Database, Settings, Shield, TrendingUp, Clock, Users, DollarSign,
  ArrowRight, Sparkles
} from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import { PageHeader } from '../components/ui';
import api from '../services/api';

// =============================================================================
// COLORS
// =============================================================================

const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f8fafc',
  card: dark ? '#242b3d' : '#ffffff',
  border: dark ? '#2d3548' : '#e2e8f0',
  text: dark ? '#e8eaed' : '#1a2332',
  textMuted: dark ? '#8b95a5' : '#64748b',
  primary: '#83b16d',
  critical: '#dc2626',
  criticalBg: dark ? 'rgba(220, 38, 38, 0.15)' : '#fef2f2',
  warning: '#d97706',
  warningBg: dark ? 'rgba(217, 119, 6, 0.15)' : '#fffbeb',
  info: '#0ea5e9',
  infoBg: dark ? 'rgba(14, 165, 233, 0.15)' : '#f0f9ff',
  success: '#16a34a',
  successBg: dark ? 'rgba(22, 163, 74, 0.15)' : '#f0fdf4',
});

// Category config
const CATEGORY_CONFIG = {
  data_quality: { icon: Database, label: 'Data Quality', color: '#3b82f6' },
  configuration: { icon: Settings, label: 'Configuration', color: '#8b5cf6' },
  compliance: { icon: Shield, label: 'Compliance', color: '#ef4444' },
  coverage: { icon: FileText, label: 'Coverage', color: '#f59e0b' },
  pattern: { icon: TrendingUp, label: 'Pattern', color: '#06b6d4' },
};

// Severity config
const SEVERITY_CONFIG = {
  critical: { icon: AlertTriangle, label: 'Critical', color: '#dc2626' },
  warning: { icon: AlertCircle, label: 'Warning', color: '#d97706' },
  info: { icon: Info, label: 'Info', color: '#0ea5e9' },
};

// =============================================================================
// COST EQUIVALENT BANNER
// =============================================================================

function CostEquivalentBanner({ costData, colors }) {
  if (!costData || costData.hours === 0) return null;
  
  return (
    <div style={{
      background: `linear-gradient(135deg, ${colors.primary}15 0%, ${colors.primary}05 100%)`,
      border: `1px solid ${colors.primary}40`,
      borderRadius: 12,
      padding: '1.25rem 1.5rem',
      marginBottom: '1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: '1rem',
    }}>
      <div>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.5rem',
          marginBottom: '0.25rem'
        }}>
          <Sparkles size={18} color={colors.primary} />
          <span style={{ 
            fontSize: '0.9rem', 
            fontWeight: 600, 
            color: colors.text 
          }}>
            Consultant Time Equivalent
          </span>
        </div>
        <p style={{ 
          fontSize: '0.8rem', 
          color: colors.textMuted, 
          margin: 0 
        }}>
          Analysis of {costData.inputs?.record_count?.toLocaleString() || 0} records 
          across {costData.inputs?.table_count || 0} tables
        </p>
      </div>
      
      <div style={{ textAlign: 'right' }}>
        <div style={{ 
          fontSize: '1.75rem', 
          fontWeight: 700, 
          color: colors.primary,
          lineHeight: 1
        }}>
          ${costData.cost?.toLocaleString() || 0}
        </div>
        <div style={{ 
          fontSize: '0.75rem', 
          color: colors.textMuted 
        }}>
          {costData.hours || 0} hours @ ${costData.hourly_rate || 250}/hr
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// SUMMARY STATS
// =============================================================================

function SummaryStats({ summary, colors }) {
  const stats = [
    { 
      label: 'Critical', 
      value: summary.critical, 
      color: colors.critical,
      bg: colors.criticalBg,
      icon: AlertTriangle 
    },
    { 
      label: 'Warnings', 
      value: summary.warning, 
      color: colors.warning,
      bg: colors.warningBg,
      icon: AlertCircle 
    },
    { 
      label: 'Info', 
      value: summary.info, 
      color: colors.info,
      bg: colors.infoBg,
      icon: Info 
    },
  ];
  
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(3, 1fr)',
      gap: '1rem',
      marginBottom: '1.5rem',
    }}>
      {stats.map(stat => {
        const Icon = stat.icon;
        return (
          <div key={stat.label} style={{
            background: stat.bg,
            border: `1px solid ${stat.color}30`,
            borderRadius: 10,
            padding: '1rem 1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
          }}>
            <div style={{
              width: 40,
              height: 40,
              borderRadius: 8,
              background: `${stat.color}20`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Icon size={20} color={stat.color} />
            </div>
            <div>
              <div style={{ 
                fontSize: '1.5rem', 
                fontWeight: 700, 
                color: stat.color,
                lineHeight: 1
              }}>
                {stat.value}
              </div>
              <div style={{ 
                fontSize: '0.75rem', 
                color: colors.textMuted,
                marginTop: '0.15rem'
              }}>
                {stat.label}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// =============================================================================
// FINDING CARD
// =============================================================================

function FindingCard({ finding, colors, onClick, selected, onToggleSelect }) {
  const severityConfig = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.info;
  const categoryConfig = CATEGORY_CONFIG[finding.category] || CATEGORY_CONFIG.pattern;
  const SeverityIcon = severityConfig.icon;
  const CategoryIcon = categoryConfig.icon;
  
  const severityColors = {
    critical: { bg: colors.criticalBg, border: colors.critical },
    warning: { bg: colors.warningBg, border: colors.warning },
    info: { bg: colors.infoBg, border: colors.info },
  };
  
  const sc = severityColors[finding.severity] || severityColors.info;
  
  return (
    <div
      style={{
        background: selected ? `${colors.primary}08` : colors.card,
        border: `1px solid ${selected ? colors.primary : colors.border}`,
        borderLeft: `4px solid ${sc.border}`,
        borderRadius: 8,
        padding: '1rem 1.25rem',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
        e.currentTarget.style.transform = 'translateY(-1px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'flex-start', 
        justifyContent: 'space-between',
        marginBottom: '0.75rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* Checkbox for selection */}
          <input
            type="checkbox"
            checked={selected}
            onChange={(e) => {
              e.stopPropagation();
              onToggleSelect(finding.id);
            }}
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 18,
              height: 18,
              accentColor: colors.primary,
              cursor: 'pointer',
              flexShrink: 0,
            }}
          />
          <div 
            onClick={onClick}
            style={{
              width: 32,
              height: 32,
              borderRadius: 6,
              background: sc.bg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
            <SeverityIcon size={16} color={sc.border} />
          </div>
          <div onClick={onClick}>
            <div style={{ 
              fontSize: '0.95rem', 
              fontWeight: 600, 
              color: colors.text,
              lineHeight: 1.2
            }}>
              {finding.title}
            </div>
            {finding.subtitle && (
              <div style={{ 
                fontSize: '0.75rem', 
                color: colors.textMuted,
                marginTop: '0.15rem'
              }}>
                {finding.subtitle}
              </div>
            )}
          </div>
        </div>
        
        <div 
          onClick={onClick}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem' 
          }}>
          <span style={{
            fontSize: '0.65rem',
            fontWeight: 600,
            padding: '0.2rem 0.5rem',
            borderRadius: 4,
            background: `${categoryConfig.color}15`,
            color: categoryConfig.color,
            textTransform: 'uppercase',
            letterSpacing: '0.03em',
          }}>
            {categoryConfig.label}
          </span>
          <ChevronRight size={16} color={colors.textMuted} />
        </div>
      </div>
      
      {/* Description */}
      <p 
        onClick={onClick}
        style={{ 
          fontSize: '0.8rem', 
          color: colors.textMuted, 
          margin: '0 0 0.75rem',
          lineHeight: 1.5
        }}>
        {finding.description}
      </p>
      
      {/* Footer stats */}
      <div 
        onClick={onClick}
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '1rem',
          flexWrap: 'wrap'
        }}>
        {finding.affected_count > 0 && (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.35rem',
            fontSize: '0.75rem',
            color: colors.textMuted
          }}>
            <Users size={12} />
            <span>{finding.affected_count.toLocaleString()} affected</span>
          </div>
        )}
        
        {finding.affected_percentage && (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.35rem',
            fontSize: '0.75rem',
            color: colors.textMuted
          }}>
            <BarChart3 size={12} />
            <span>{finding.affected_percentage.toFixed(1)}%</span>
          </div>
        )}
        
        {finding.effort_estimate && (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.35rem',
            fontSize: '0.75rem',
            color: colors.textMuted
          }}>
            <Clock size={12} />
            <span>{finding.effort_estimate}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// FINDING DETAIL MODAL
// =============================================================================

function FindingDetailModal({ finding, colors, onClose }) {
  if (!finding) return null;
  
  const severityConfig = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.info;
  const categoryConfig = CATEGORY_CONFIG[finding.category] || CATEGORY_CONFIG.pattern;
  const SeverityIcon = severityConfig.icon;
  
  return (
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
        zIndex: 1000,
        padding: '2rem',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: colors.card,
          borderRadius: 16,
          width: '100%',
          maxWidth: 600,
          maxHeight: '80vh',
          overflow: 'auto',
          boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{
          padding: '1.5rem',
          borderBottom: `1px solid ${colors.border}`,
          display: 'flex',
          alignItems: 'flex-start',
          gap: '1rem',
        }}>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: 10,
            background: `${severityConfig.color}15`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <SeverityIcon size={24} color={severityConfig.color} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ 
              fontSize: '1.1rem', 
              fontWeight: 600, 
              color: colors.text,
              marginBottom: '0.25rem'
            }}>
              {finding.title}
            </div>
            {finding.subtitle && (
              <div style={{ 
                fontSize: '0.85rem', 
                color: colors.textMuted 
              }}>
                {finding.subtitle}
              </div>
            )}
            <div style={{ 
              display: 'flex', 
              gap: '0.5rem', 
              marginTop: '0.5rem' 
            }}>
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 600,
                padding: '0.25rem 0.6rem',
                borderRadius: 4,
                background: `${severityConfig.color}15`,
                color: severityConfig.color,
                textTransform: 'uppercase',
              }}>
                {severityConfig.label}
              </span>
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 600,
                padding: '0.25rem 0.6rem',
                borderRadius: 4,
                background: `${categoryConfig.color}15`,
                color: categoryConfig.color,
                textTransform: 'uppercase',
              }}>
                {categoryConfig.label}
              </span>
            </div>
          </div>
        </div>
        
        {/* Body */}
        <div style={{ padding: '1.5rem' }}>
          {/* Description */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h4 style={{ 
              fontSize: '0.8rem', 
              fontWeight: 600, 
              color: colors.text,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: '0.5rem'
            }}>
              Description
            </h4>
            <p style={{ 
              fontSize: '0.9rem', 
              color: colors.text, 
              lineHeight: 1.6,
              margin: 0
            }}>
              {finding.description}
            </p>
          </div>
          
          {/* Impact */}
          {finding.impact_explanation && (
            <div style={{ marginBottom: '1.5rem' }}>
              <h4 style={{ 
                fontSize: '0.8rem', 
                fontWeight: 600, 
                color: colors.text,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '0.5rem'
              }}>
                Impact
              </h4>
              <p style={{ 
                fontSize: '0.9rem', 
                color: colors.text, 
                lineHeight: 1.6,
                margin: 0
              }}>
                {finding.impact_explanation}
              </p>
            </div>
          )}
          
          {/* Stats */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(3, 1fr)', 
            gap: '1rem',
            marginBottom: '1.5rem'
          }}>
            {finding.affected_count > 0 && (
              <div style={{
                background: colors.bg,
                borderRadius: 8,
                padding: '0.75rem',
                textAlign: 'center'
              }}>
                <div style={{ 
                  fontSize: '1.25rem', 
                  fontWeight: 700, 
                  color: colors.text 
                }}>
                  {finding.affected_count.toLocaleString()}
                </div>
                <div style={{ 
                  fontSize: '0.7rem', 
                  color: colors.textMuted 
                }}>
                  Records Affected
                </div>
              </div>
            )}
            
            {finding.affected_percentage && (
              <div style={{
                background: colors.bg,
                borderRadius: 8,
                padding: '0.75rem',
                textAlign: 'center'
              }}>
                <div style={{ 
                  fontSize: '1.25rem', 
                  fontWeight: 700, 
                  color: colors.text 
                }}>
                  {finding.affected_percentage.toFixed(1)}%
                </div>
                <div style={{ 
                  fontSize: '0.7rem', 
                  color: colors.textMuted 
                }}>
                  Of Total
                </div>
              </div>
            )}
            
            {finding.effort_estimate && (
              <div style={{
                background: colors.bg,
                borderRadius: 8,
                padding: '0.75rem',
                textAlign: 'center'
              }}>
                <div style={{ 
                  fontSize: '1.25rem', 
                  fontWeight: 700, 
                  color: colors.text 
                }}>
                  {finding.effort_estimate}
                </div>
                <div style={{ 
                  fontSize: '0.7rem', 
                  color: colors.textMuted 
                }}>
                  Est. Effort
                </div>
              </div>
            )}
          </div>
          
          {/* Recommended Actions */}
          {finding.recommended_actions?.length > 0 && (
            <div>
              <h4 style={{ 
                fontSize: '0.8rem', 
                fontWeight: 600, 
                color: colors.text,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '0.75rem'
              }}>
                Recommended Actions
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {finding.recommended_actions.map((action, idx) => (
                  <div key={idx} style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.75rem',
                    padding: '0.75rem',
                    background: colors.bg,
                    borderRadius: 8,
                  }}>
                    <div style={{
                      width: 20,
                      height: 20,
                      borderRadius: '50%',
                      background: colors.primary,
                      color: '#fff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      flexShrink: 0,
                    }}>
                      {idx + 1}
                    </div>
                    <span style={{ 
                      fontSize: '0.85rem', 
                      color: colors.text,
                      lineHeight: 1.4
                    }}>
                      {action}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div style={{
          padding: '1rem 1.5rem',
          borderTop: `1px solid ${colors.border}`,
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '0.75rem',
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '0.6rem 1.25rem',
              background: 'transparent',
              border: `1px solid ${colors.border}`,
              borderRadius: 6,
              color: colors.text,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            Close
          </button>
          <button
            style={{
              padding: '0.6rem 1.25rem',
              background: colors.primary,
              border: 'none',
              borderRadius: 6,
              color: '#fff',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            Add to Playbook
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// EMPTY STATE
// =============================================================================

function EmptyState({ colors, hasProject }) {
  if (!hasProject) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '4rem 2rem',
        background: colors.card,
        borderRadius: 12,
        border: `1px solid ${colors.border}`,
      }}>
        <AlertCircle size={48} color={colors.textMuted} style={{ marginBottom: '1rem' }} />
        <h3 style={{ 
          fontSize: '1.1rem', 
          fontWeight: 600, 
          color: colors.text,
          marginBottom: '0.5rem'
        }}>
          No Project Selected
        </h3>
        <p style={{ 
          fontSize: '0.9rem', 
          color: colors.textMuted,
          marginBottom: '1.5rem'
        }}>
          Select a project from the dropdown above to view findings.
        </p>
        <Link to="/projects">
          <button style={{
            padding: '0.75rem 1.5rem',
            background: colors.primary,
            border: 'none',
            borderRadius: 8,
            color: '#fff',
            fontWeight: 600,
            cursor: 'pointer',
          }}>
            Go to Projects
          </button>
        </Link>
      </div>
    );
  }
  
  return (
    <div style={{
      textAlign: 'center',
      padding: '4rem 2rem',
      background: colors.card,
      borderRadius: 12,
      border: `1px solid ${colors.border}`,
    }}>
      <CheckCircle size={48} color={colors.success} style={{ marginBottom: '1rem' }} />
      <h3 style={{ 
        fontSize: '1.1rem', 
        fontWeight: 600, 
        color: colors.text,
        marginBottom: '0.5rem'
      }}>
        No Issues Found
      </h3>
      <p style={{ 
        fontSize: '0.9rem', 
        color: colors.textMuted,
        marginBottom: '1.5rem'
      }}>
        Great news! No data quality issues or gaps were detected.
      </p>
      <Link to="/data">
        <button style={{
          padding: '0.75rem 1.5rem',
          background: colors.primary,
          border: 'none',
          borderRadius: 8,
          color: '#fff',
          fontWeight: 600,
          cursor: 'pointer',
        }}>
          Upload More Data
        </button>
      </Link>
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function FindingsDashboard() {
  const { activeProject } = useProject();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  const navigate = useNavigate();
  
  const [findings, setFindings] = useState([]);
  const [summary, setSummary] = useState({ total: 0, critical: 0, warning: 0, info: 0, by_category: {} });
  const [costEquivalent, setCostEquivalent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  
  // Filters
  const [severityFilter, setSeverityFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  
  // Toggle finding selection
  const toggleFindingSelection = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };
  
  // Navigate to build playbook with selected findings
  const handleBuildPlaybook = () => {
    navigate('/build-playbook', {
      state: { selectedFindingIds: Array.from(selectedIds) }
    });
  };
  
  // Load findings when project changes
  useEffect(() => {
    if (activeProject?.name) {
      loadFindings();
    } else {
      setFindings([]);
      setSummary({ total: 0, critical: 0, warning: 0, info: 0, by_category: {} });
      setCostEquivalent(null);
    }
  }, [activeProject?.name]);
  
  const loadFindings = async () => {
    if (!activeProject?.name) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get(`/findings/${activeProject.name}/findings`);
      setFindings(response.data.findings || []);
      setSummary(response.data.summary || { total: 0, critical: 0, warning: 0, info: 0, by_category: {} });
      setCostEquivalent(response.data.cost_equivalent || null);
    } catch (err) {
      console.error('Error loading findings:', err);
      setError(err.message || 'Failed to load findings');
    } finally {
      setLoading(false);
    }
  };
  
  // Apply filters
  const filteredFindings = useMemo(() => {
    let result = findings;
    
    if (severityFilter !== 'all') {
      result = result.filter(f => f.severity === severityFilter);
    }
    
    if (categoryFilter !== 'all') {
      result = result.filter(f => f.category === categoryFilter);
    }
    
    return result;
  }, [findings, severityFilter, categoryFilter]);
  
  return (
    <div>
      <PageHeader
        icon={AlertTriangle}
        title="Findings"
        subtitle={activeProject 
          ? `Analysis results for ${activeProject.customer || activeProject.name}`
          : "Auto-surfaced analysis results"
        }
      />
      
      {/* Cost Equivalent Banner */}
      {costEquivalent && (
        <CostEquivalentBanner costData={costEquivalent} colors={colors} />
      )}
      
      {/* Loading State */}
      {loading && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '4rem',
          gap: '0.75rem',
          color: colors.textMuted,
        }}>
          <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
          <span>Analyzing project data...</span>
        </div>
      )}
      
      {/* Error State */}
      {error && (
        <div style={{
          padding: '1rem 1.5rem',
          background: colors.criticalBg,
          border: `1px solid ${colors.critical}30`,
          borderRadius: 8,
          color: colors.critical,
          marginBottom: '1.5rem',
        }}>
          {error}
        </div>
      )}
      
      {/* Content */}
      {!loading && !error && (
        <>
          {/* Summary Stats */}
          {summary.total > 0 && (
            <SummaryStats summary={summary} colors={colors} />
          )}
          
          {/* Filters */}
          {findings.length > 0 && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
              marginBottom: '1.5rem',
              flexWrap: 'wrap',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Filter size={16} color={colors.textMuted} />
                <span style={{ fontSize: '0.85rem', color: colors.textMuted }}>Filter:</span>
              </div>
              
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                style={{
                  padding: '0.5rem 0.75rem',
                  borderRadius: 6,
                  border: `1px solid ${colors.border}`,
                  background: colors.card,
                  color: colors.text,
                  fontSize: '0.85rem',
                }}
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="warning">Warning</option>
                <option value="info">Info</option>
              </select>
              
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                style={{
                  padding: '0.5rem 0.75rem',
                  borderRadius: 6,
                  border: `1px solid ${colors.border}`,
                  background: colors.card,
                  color: colors.text,
                  fontSize: '0.85rem',
                }}
              >
                <option value="all">All Categories</option>
                {Object.entries(CATEGORY_CONFIG).map(([key, config]) => (
                  <option key={key} value={key}>{config.label}</option>
                ))}
              </select>
              
              <div style={{ flex: 1 }} />
              
              <button
                onClick={loadFindings}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 1rem',
                  background: 'transparent',
                  border: `1px solid ${colors.border}`,
                  borderRadius: 6,
                  color: colors.text,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                <RefreshCw size={14} />
                Refresh
              </button>
            </div>
          )}
          
          {/* Findings List */}
          {filteredFindings.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {filteredFindings.map(finding => (
                <FindingCard
                  key={finding.id}
                  finding={finding}
                  colors={colors}
                  onClick={() => setSelectedFinding(finding)}
                  selected={selectedIds.has(finding.id)}
                  onToggleSelect={toggleFindingSelection}
                />
              ))}
            </div>
          ) : (
            <EmptyState colors={colors} hasProject={!!activeProject} />
          )}
          
          {/* Build Playbook CTA */}
          {filteredFindings.length > 0 && (
            <div style={{
              marginTop: '2rem',
              padding: '1.5rem',
              background: `linear-gradient(135deg, ${colors.primary}10 0%, ${colors.primary}05 100%)`,
              border: `1px solid ${colors.primary}30`,
              borderRadius: 12,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '1rem',
            }}>
              <div>
                <h3 style={{ 
                  fontSize: '1rem', 
                  fontWeight: 600, 
                  color: colors.text,
                  margin: '0 0 0.25rem'
                }}>
                  Ready to take action?
                </h3>
                <p style={{ 
                  fontSize: '0.85rem', 
                  color: colors.textMuted,
                  margin: 0
                }}>
                  {selectedIds.size > 0 
                    ? `${selectedIds.size} finding${selectedIds.size !== 1 ? 's' : ''} selected — create a playbook to track remediation.`
                    : 'Select findings or click to build a playbook from all findings.'}
                </p>
              </div>
              <button 
                onClick={handleBuildPlaybook}
                style={{
                  padding: '0.75rem 1.5rem',
                  background: colors.primary,
                  border: 'none',
                  borderRadius: 8,
                  color: '#fff',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}>
                Build Playbook
                <ArrowRight size={16} />
              </button>
            </div>
          )}
        </>
      )}
      
      {/* Detail Modal */}
      {selectedFinding && (
        <FindingDetailModal
          finding={selectedFinding}
          colors={colors}
          onClose={() => setSelectedFinding(null)}
        />
      )}
      
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
