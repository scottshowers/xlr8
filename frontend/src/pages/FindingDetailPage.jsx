/**
 * FindingDetailPage.jsx - Drill-In Detail Screen
 * ===============================================
 *
 * Phase 4A.5: Finding Detail View
 *
 * Shows deep dive on a single finding:
 * - What We Found
 * - Why It Matters
 * - Affected Records (sample table)
 * - Recommended Actions
 * - Sidebar with stats and Add to Playbook
 *
 * Matches mockup Screen 5 design.
 *
 * Created: January 15, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { ArrowLeft, Download, Plus, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

// =============================================================================
// COLORS
// =============================================================================

const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f6f5fa',
  card: dark ? '#242b3d' : '#ffffff',
  border: dark ? '#2d3548' : '#e1e8ed',
  text: dark ? '#e8eaed' : '#2a3441',
  textMuted: dark ? '#8b95a5' : '#5f6c7b',
  primary: '#83b16d',
  scarlet: '#993c44',
  amber: '#d97706',
  blue: '#285390',
});

// =============================================================================
// MOCK AFFECTED RECORDS (would come from API in production)
// =============================================================================

const MOCK_AFFECTED_RECORDS = [
  { id: 'EMP-10234', name: 'Johnson, Michael', state: 'CA', current: '(empty)', issue: 'Missing locality' },
  { id: 'EMP-10891', name: 'Williams, Sarah', state: 'TX', current: 'INVALID', issue: 'Invalid code' },
  { id: 'EMP-11456', name: 'Garcia, Maria', state: 'NY', current: '(empty)', issue: 'Missing locality' },
  { id: 'EMP-11892', name: 'Chen, David', state: 'CA', current: 'XX-000', issue: 'Invalid format' },
];

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function FindingDetailPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { findingId } = useParams();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  const { activeProject } = useProject();

  // Get finding from location state or fetch
  const [finding, setFinding] = useState(location.state?.finding || null);
  const [loading, setLoading] = useState(!finding);

  useEffect(() => {
    if (!finding && findingId) {
      // TODO: Fetch finding from API
      // For now, show placeholder
      setLoading(false);
    }
  }, [finding, findingId]);

  // Severity config
  const getSeverityConfig = (severity) => {
    switch (severity) {
      case 'critical':
        return { symbol: '!', bg: colors.scarlet, color: '#fff', label: 'Critical' };
      case 'warning':
        return { symbol: '!', bg: colors.amber, color: '#fff', label: 'Warning' };
      default:
        return { symbol: 'i', bg: colors.blue, color: '#fff', label: 'Info' };
    }
  };

  const getCategoryLabel = (category) => {
    const labels = {
      data_quality: 'Data Quality',
      configuration: 'Configuration',
      compliance: 'Compliance',
      coverage: 'Coverage',
      pattern: 'Pattern',
    };
    return labels[category] || category || 'General';
  };

  const handleAddToPlaybook = () => {
    // Navigate to build-playbook with this finding pre-selected
    navigate('/build-playbook', {
      state: {
        selectedFindings: [finding],
      },
    });
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: colors.textMuted }}>
        Loading finding details...
      </div>
    );
  }

  if (!finding) {
    return (
      <div style={{ padding: '2rem' }}>
        <button
          onClick={() => navigate('/findings')}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: colors.textMuted,
            background: 'none',
            border: 'none',
            fontSize: '0.85rem',
            cursor: 'pointer',
            marginBottom: '1rem',
          }}
        >
          <ArrowLeft size={16} />
          Back to Findings
        </button>
        <div style={{
          background: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: 12,
          padding: '3rem',
          textAlign: 'center',
        }}>
          <h2 style={{ color: colors.text, marginBottom: '0.5rem' }}>Finding Not Found</h2>
          <p style={{ color: colors.textMuted }}>The requested finding could not be loaded.</p>
        </div>
      </div>
    );
  }

  const severity = getSeverityConfig(finding.severity);

  return (
    <div style={{ padding: '2rem', maxWidth: 1200, margin: '0 auto' }}>
      {/* Back Link */}
      <button
        onClick={() => navigate('/findings')}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          color: colors.textMuted,
          background: 'none',
          border: 'none',
          fontSize: '0.85rem',
          cursor: 'pointer',
          marginBottom: '1rem',
          padding: 0,
        }}
      >
        <ArrowLeft size={16} />
        Back to Findings
      </button>

      {/* Detail Panel */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 300px',
        gap: '1.5rem',
      }}>
        {/* Main Content */}
        <div style={{
          background: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: 12,
          padding: '2rem',
        }}>
          {/* Header */}
          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '1rem',
            marginBottom: '2rem',
            paddingBottom: '1.5rem',
            borderBottom: `1px solid ${colors.border}`,
          }}>
            <div style={{
              width: 48,
              height: 48,
              borderRadius: 10,
              background: severity.bg,
              color: severity.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.25rem',
              fontWeight: 700,
              flexShrink: 0,
            }}>
              {severity.symbol}
            </div>
            <div>
              <h2 style={{
                fontFamily: "'Sora', sans-serif",
                fontSize: '1.5rem',
                fontWeight: 700,
                color: colors.text,
                margin: '0 0 0.25rem',
              }}>
                {finding.title}
              </h2>
              <p style={{
                fontSize: '0.95rem',
                color: colors.textMuted,
                margin: 0,
              }}>
                {finding.subtitle || `${finding.affected_count?.toLocaleString() || 0} affected records`}
              </p>
            </div>
          </div>

          {/* What We Found */}
          <div style={{ marginBottom: '1.75rem' }}>
            <h4 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '0.95rem',
              fontWeight: 600,
              color: colors.text,
              marginBottom: '0.75rem',
            }}>
              What We Found
            </h4>
            <p style={{
              fontSize: '0.9rem',
              color: colors.textMuted,
              lineHeight: 1.6,
            }}>
              {finding.description || `Analysis detected ${finding.affected_count?.toLocaleString() || 0} records with issues related to ${finding.title.toLowerCase()}. This represents ${finding.affected_percentage?.toFixed(1) || '0'}% of the total dataset.`}
            </p>
          </div>

          {/* Why It Matters */}
          <div style={{ marginBottom: '1.75rem' }}>
            <h4 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '0.95rem',
              fontWeight: 600,
              color: colors.text,
              marginBottom: '0.75rem',
            }}>
              Why It Matters
            </h4>
            <p style={{
              fontSize: '0.9rem',
              color: colors.textMuted,
              lineHeight: 1.6,
            }}>
              {finding.impact_explanation || 'This issue may affect data quality, compliance, or operational efficiency. Addressing it promptly can reduce risk and improve overall data integrity.'}
            </p>
          </div>

          {/* Affected Records Sample */}
          <div style={{ marginBottom: '1.75rem' }}>
            <h4 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '0.95rem',
              fontWeight: 600,
              color: colors.text,
              marginBottom: '0.75rem',
            }}>
              Affected Records (Sample)
            </h4>
            <div style={{
              background: colors.bg,
              border: `1px solid ${colors.border}`,
              borderRadius: 8,
              overflow: 'hidden',
            }}>
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '0.85rem',
              }}>
                <thead>
                  <tr style={{ background: colors.card }}>
                    <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600, color: colors.text, borderBottom: `1px solid ${colors.border}` }}>Record ID</th>
                    <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600, color: colors.text, borderBottom: `1px solid ${colors.border}` }}>Name</th>
                    <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600, color: colors.text, borderBottom: `1px solid ${colors.border}` }}>Table</th>
                    <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600, color: colors.text, borderBottom: `1px solid ${colors.border}` }}>Current Value</th>
                    <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600, color: colors.text, borderBottom: `1px solid ${colors.border}` }}>Issue</th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK_AFFECTED_RECORDS.map((record, i) => (
                    <tr key={record.id} style={{ background: i % 2 === 0 ? 'transparent' : colors.bg }}>
                      <td style={{ padding: '0.75rem 1rem', color: colors.text }}>{record.id}</td>
                      <td style={{ padding: '0.75rem 1rem', color: colors.text }}>{record.name}</td>
                      <td style={{ padding: '0.75rem 1rem', color: colors.textMuted }}>{finding.affected_table || record.state}</td>
                      <td style={{ padding: '0.75rem 1rem', color: colors.textMuted }}>{record.current}</td>
                      <td style={{ padding: '0.75rem 1rem', color: colors.scarlet }}>{record.issue}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p style={{
              marginTop: '0.75rem',
              fontSize: '0.8rem',
              color: colors.textMuted,
            }}>
              Showing 4 of {finding.affected_count?.toLocaleString() || 0} affected records ·{' '}
              <button
                style={{
                  background: 'none',
                  border: 'none',
                  color: colors.primary,
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  padding: 0,
                }}
              >
                Export Full List
              </button>
            </p>
          </div>

          {/* Recommended Actions */}
          <div>
            <h4 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '0.95rem',
              fontWeight: 600,
              color: colors.text,
              marginBottom: '0.75rem',
            }}>
              Recommended Actions
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {(finding.recommended_actions?.length > 0
                ? finding.recommended_actions
                : ['Review the affected records', 'Determine root cause', 'Apply corrections']
              ).map((action, i) => (
                <div key={i} style={{
                  display: 'flex',
                  gap: '1rem',
                  padding: '1rem',
                  background: colors.bg,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 8,
                }}>
                  <div style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: colors.primary,
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    flexShrink: 0,
                  }}>
                    {i + 1}
                  </div>
                  <div>
                    <div style={{
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      color: colors.text,
                      marginBottom: '0.25rem',
                    }}>
                      {action}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div style={{
          background: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: 12,
          padding: '1.5rem',
          height: 'fit-content',
        }}>
          <h3 style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: '1rem',
            fontWeight: 600,
            color: colors.text,
            marginBottom: '1.25rem',
          }}>
            Finding Details
          </h3>

          {/* Stats */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.8rem', color: colors.textMuted }}>Severity</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: severity.bg }}>{severity.label}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.8rem', color: colors.textMuted }}>Category</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 500, color: colors.text }}>{getCategoryLabel(finding.category)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.8rem', color: colors.textMuted }}>Affected Records</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 500, color: colors.text }}>{finding.affected_count?.toLocaleString() || 0}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.8rem', color: colors.textMuted }}>% of Total</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 500, color: colors.text }}>{finding.affected_percentage?.toFixed(1) || '—'}%</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.8rem', color: colors.textMuted }}>Risk Estimate</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: colors.scarlet }}>{finding.impact_value || '—'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.8rem', color: colors.textMuted }}>Remediation Effort</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 500, color: colors.text }}>{finding.effort_estimate || '2-4 hours'}</span>
            </div>
          </div>

          {/* Add to Playbook Button */}
          <button
            onClick={handleAddToPlaybook}
            style={{
              width: '100%',
              padding: '0.875rem',
              background: colors.primary,
              border: 'none',
              borderRadius: 8,
              color: '#fff',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
            }}
          >
            <Plus size={18} />
            Add to Playbook
          </button>
        </div>
      </div>
    </div>
  );
}
