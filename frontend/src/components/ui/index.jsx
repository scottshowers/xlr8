/**
 * XLR8 Shared UI Components
 * 
 * Unified patterns for:
 * - LoadingSpinner - Consistent loading indicators
 * - ErrorState - Error displays with retry
 * - EmptyState - No-data placeholders
 * - PageHeader - Consistent page headers with breadcrumbs
 * 
 * Usage:
 *   import { LoadingSpinner, ErrorState, EmptyState, PageHeader } from '../components/ui';
 */

import React from 'react';
import { Link } from 'react-router-dom';

// ============================================================
// BRAND COLORS (shared across all components)
// ============================================================
export const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  clearwater: '#b2d6de',
  turkishSea: '#285390',
  electricBlue: '#2766b1',
  iceFlow: '#c9d3d4',
  aquamarine: '#a1c3d4',
  white: '#f6f5fa',
  silver: '#a2a1a0',
  text: '#2a3441',
  textLight: '#5f6c7b',
  border: '#e1e8ed',
  error: '#dc3545',
  errorLight: '#fef2f2',
  errorBorder: '#fecaca',
  warning: '#f59e0b',
  warningLight: '#fffbeb',
  warningBorder: '#fde68a',
  success: '#10b981',
  successLight: '#ecfdf5',
  successBorder: '#a7f3d0',
};

// ============================================================
// LOADING SPINNER
// ============================================================
/**
 * LoadingSpinner - Unified loading indicator
 * 
 * Props:
 * - size: 'sm' | 'md' | 'lg' | 'xl' (default: 'md')
 * - message: Optional loading message
 * - fullPage: Center in viewport (default: false)
 * - inline: Display inline without centering (default: false)
 */
export function LoadingSpinner({ 
  size = 'md', 
  message = null, 
  fullPage = false,
  inline = false 
}) {
  const sizes = {
    sm: { spinner: 16, border: 2, fontSize: '0.75rem' },
    md: { spinner: 32, border: 3, fontSize: '0.875rem' },
    lg: { spinner: 48, border: 4, fontSize: '1rem' },
    xl: { spinner: 64, border: 5, fontSize: '1.125rem' },
  };

  const { spinner: spinnerSize, border: borderWidth, fontSize } = sizes[size] || sizes.md;

  const spinnerStyle = {
    width: spinnerSize,
    height: spinnerSize,
    border: `${borderWidth}px solid ${COLORS.iceFlow}`,
    borderTop: `${borderWidth}px solid ${COLORS.grassGreen}`,
    borderRadius: '50%',
    animation: 'xlr8-spin 0.8s linear infinite',
  };

  const containerStyle = fullPage ? {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '60vh',
    gap: '1rem',
  } : inline ? {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
  } : {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '3rem',
    gap: '1rem',
  };

  return (
    <div style={containerStyle}>
      <div style={spinnerStyle} />
      {message && (
        <span style={{ 
          color: COLORS.textLight, 
          fontSize,
          fontWeight: 500,
        }}>
          {message}
        </span>
      )}
    </div>
  );
}

// ============================================================
// ERROR STATE
// ============================================================
/**
 * ErrorState - Unified error display with optional retry
 * 
 * Props:
 * - title: Error title (default: 'Something went wrong')
 * - message: Error description
 * - onRetry: Callback for retry button (optional)
 * - retryLabel: Custom retry button text (default: 'Try Again')
 * - fullPage: Center in viewport (default: false)
 * - compact: Smaller inline version (default: false)
 */
export function ErrorState({ 
  title = 'Something went wrong',
  message = 'We encountered an error loading this content.',
  onRetry = null,
  retryLabel = 'Try Again',
  fullPage = false,
  compact = false,
}) {
  const containerStyle = fullPage ? {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '50vh',
    textAlign: 'center',
    padding: '2rem',
  } : compact ? {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    padding: '1rem',
    background: COLORS.errorLight,
    border: `1px solid ${COLORS.errorBorder}`,
    borderRadius: '8px',
  } : {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    padding: '3rem 2rem',
    background: COLORS.errorLight,
    border: `1px solid ${COLORS.errorBorder}`,
    borderRadius: '12px',
  };

  if (compact) {
    return (
      <div style={containerStyle}>
        <span style={{ fontSize: '1.25rem' }}>⚠️</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, color: COLORS.error, fontSize: '0.875rem' }}>{title}</div>
          <div style={{ color: COLORS.textLight, fontSize: '0.8rem' }}>{message}</div>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            style={{
              padding: '0.4rem 0.75rem',
              background: 'white',
              border: `1px solid ${COLORS.error}`,
              borderRadius: '6px',
              color: COLORS.error,
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {retryLabel}
          </button>
        )}
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={{ 
        fontSize: fullPage ? '4rem' : '3rem', 
        marginBottom: '1rem',
        opacity: 0.8,
      }}>
        ⚠️
      </div>
      <h2 style={{
        fontFamily: "'Sora', sans-serif",
        fontSize: fullPage ? '1.5rem' : '1.25rem',
        fontWeight: 700,
        color: COLORS.text,
        marginBottom: '0.5rem',
      }}>
        {title}
      </h2>
      <p style={{
        color: COLORS.textLight,
        fontSize: '0.95rem',
        maxWidth: '400px',
        lineHeight: 1.6,
        marginBottom: onRetry ? '1.5rem' : 0,
      }}>
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            padding: '0.75rem 1.5rem',
            background: COLORS.grassGreen,
            border: 'none',
            borderRadius: '8px',
            color: 'white',
            fontSize: '0.9rem',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          🔄 {retryLabel}
        </button>
      )}
    </div>
  );
}

// ============================================================
// EMPTY STATE
// ============================================================
/**
 * EmptyState - Unified empty/no-data placeholder
 * 
 * Props:
 * - icon: Emoji or icon string (default: '📭')
 * - title: Main message
 * - description: Secondary text
 * - action: { label, to?, onClick? } - optional CTA button
 * - fullPage: Center in viewport (default: false)
 */
export function EmptyState({ 
  icon = '📭',
  title = 'Nothing here yet',
  description = '',
  action = null,
  fullPage = false,
}) {
  const containerStyle = fullPage ? {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '50vh',
    textAlign: 'center',
    padding: '2rem',
  } : {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    padding: '3rem 2rem',
  };

  const buttonStyle = {
    padding: '0.6rem 1.25rem',
    background: COLORS.grassGreen,
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    fontSize: '0.875rem',
    fontWeight: 600,
    cursor: 'pointer',
    textDecoration: 'none',
    display: 'inline-block',
  };

  return (
    <div style={containerStyle}>
      <div style={{ 
        fontSize: fullPage ? '4rem' : '3rem', 
        marginBottom: '1rem',
        opacity: 0.6,
      }}>
        {icon}
      </div>
      <h3 style={{
        fontFamily: "'Sora', sans-serif",
        fontSize: fullPage ? '1.5rem' : '1.1rem',
        fontWeight: 700,
        color: COLORS.text,
        marginBottom: '0.5rem',
      }}>
        {title}
      </h3>
      {description && (
        <p style={{
          color: COLORS.textLight,
          fontSize: '0.95rem',
          maxWidth: '400px',
          lineHeight: 1.6,
          marginBottom: action ? '1.5rem' : 0,
        }}>
          {description}
        </p>
      )}
      {action && (
        action.to ? (
          <Link to={action.to} style={buttonStyle}>
            {action.label}
          </Link>
        ) : (
          <button onClick={action.onClick} style={buttonStyle}>
            {action.label}
          </button>
        )
      )}
    </div>
  );
}

// ============================================================
// PAGE HEADER
// ============================================================
/**
 * PageHeader - Consistent page header with breadcrumbs
 * 
 * Props:
 * - title: Page title
 * - subtitle: Optional subtitle text
 * - breadcrumbs: Array of { label, to? } for breadcrumb trail
 * - action: { label, icon?, onClick?, to? } - optional action button
 * - badge: { label, color? } - optional badge next to title
 */
export function PageHeader({ 
  title,
  subtitle = null,
  breadcrumbs = [],
  action = null,
  badge = null,
}) {
  const actionButtonStyle = {
    padding: '0.75rem 1.25rem',
    background: 'white',
    border: `2px solid ${COLORS.grassGreen}`,
    borderRadius: '8px',
    color: COLORS.grassGreen,
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.9rem',
    textDecoration: 'none',
    transition: 'all 0.2s ease',
  };

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      {/* Breadcrumbs */}
      {breadcrumbs.length > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.85rem',
          color: COLORS.textLight,
          marginBottom: '0.5rem',
        }}>
          {breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={idx}>
              {idx > 0 && <span style={{ opacity: 0.5 }}>→</span>}
              {crumb.to ? (
                <Link 
                  to={crumb.to} 
                  style={{ 
                    color: COLORS.textLight, 
                    textDecoration: 'none',
                  }}
                >
                  {crumb.label}
                </Link>
              ) : (
                <span style={{ 
                  color: idx === breadcrumbs.length - 1 ? COLORS.grassGreen : COLORS.textLight,
                  fontWeight: idx === breadcrumbs.length - 1 ? 600 : 400,
                }}>
                  {crumb.label}
                </span>
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      {/* Title row */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h1 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '1.75rem',
              fontWeight: 700,
              color: COLORS.text,
              margin: 0,
            }}>
              {title}
            </h1>
            {badge && (
              <span style={{
                padding: '0.25rem 0.75rem',
                background: badge.color || COLORS.grassGreen,
                color: 'white',
                fontSize: '0.7rem',
                fontWeight: 700,
                borderRadius: '20px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>
                {badge.label}
              </span>
            )}
          </div>
          {subtitle && (
            <p style={{
              color: COLORS.textLight,
              marginTop: '0.25rem',
              fontSize: '0.95rem',
            }}>
              {subtitle}
            </p>
          )}
        </div>

        {/* Action button */}
        {action && (
          action.to ? (
            <Link 
              to={action.to} 
              style={actionButtonStyle}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = COLORS.grassGreen;
                e.currentTarget.style.color = 'white';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'white';
                e.currentTarget.style.color = COLORS.grassGreen;
              }}
            >
              {action.icon && <span>{action.icon}</span>}
              {action.label}
            </Link>
          ) : (
            <button 
              onClick={action.onClick}
              style={actionButtonStyle}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = COLORS.grassGreen;
                e.currentTarget.style.color = 'white';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'white';
                e.currentTarget.style.color = COLORS.grassGreen;
              }}
            >
              {action.icon && <span>{action.icon}</span>}
              {action.label}
            </button>
          )
        )}
      </div>
    </div>
  );
}

// ============================================================
// CARD COMPONENT
// ============================================================
/**
 * Card - Consistent card wrapper
 */
export function Card({ children, padding = '1.5rem', style = {} }) {
  return (
    <div style={{
      background: 'white',
      borderRadius: '12px',
      padding,
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      ...style,
    }}>
      {children}
    </div>
  );
}

// ============================================================
// STATUS BADGE
// ============================================================
/**
 * StatusBadge - Consistent status indicator
 */
export function StatusBadge({ status, size = 'md' }) {
  const statusConfig = {
    complete: { bg: COLORS.successLight, color: '#065f46', border: COLORS.successBorder, label: 'Complete' },
    success: { bg: COLORS.successLight, color: '#065f46', border: COLORS.successBorder, label: 'Success' },
    active: { bg: COLORS.successLight, color: '#065f46', border: COLORS.successBorder, label: 'Active' },
    in_progress: { bg: COLORS.warningLight, color: '#92400e', border: COLORS.warningBorder, label: 'In Progress' },
    pending: { bg: COLORS.warningLight, color: '#92400e', border: COLORS.warningBorder, label: 'Pending' },
    processing: { bg: '#eff6ff', color: '#1e40af', border: '#bfdbfe', label: 'Processing' },
    failed: { bg: COLORS.errorLight, color: '#991b1b', border: COLORS.errorBorder, label: 'Failed' },
    error: { bg: COLORS.errorLight, color: '#991b1b', border: COLORS.errorBorder, label: 'Error' },
  };

  const config = statusConfig[status] || { bg: '#f3f4f6', color: '#6b7280', border: '#e5e7eb', label: status };
  const padding = size === 'sm' ? '0.2rem 0.5rem' : '0.3rem 0.75rem';
  const fontSize = size === 'sm' ? '0.7rem' : '0.75rem';

  return (
    <span style={{
      display: 'inline-block',
      padding,
      background: config.bg,
      color: config.color,
      border: `1px solid ${config.border}`,
      borderRadius: '4px',
      fontSize,
      fontWeight: 600,
      textTransform: 'capitalize',
    }}>
      {config.label}
    </span>
  );
}

export default {
  LoadingSpinner,
  ErrorState,
  EmptyState,
  PageHeader,
  Card,
  StatusBadge,
  COLORS,
};
