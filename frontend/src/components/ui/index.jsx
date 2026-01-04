/**
 * XLR8 Shared UI Components
 * 
 * COMPLETE UNIFIED LIBRARY:
 * - LoadingSpinner - Consistent loading indicators
 * - ErrorState - Error displays with retry
 * - EmptyState - No-data placeholders
 * - PageHeader - Consistent page headers with breadcrumbs
 * - Card - Wrapper component
 * - StatusBadge - Status indicators
 * - Toast / ToastProvider - Notification system
 * - ConfirmDialog - Confirmation modal
 * - Button - Consistent button styles
 * 
 * Usage:
 *   import { LoadingSpinner, ErrorState, Toast, useToast } from '../components/ui';
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';

// ============================================================
// BRAND COLORS (THE source of truth)
// ============================================================
export const COLORS = {
  // Primary
  grassGreen: '#83b16d',
  grassGreenDark: '#6b9a57',
  grassGreenLight: '#a8ca99',
  
  // Secondary
  skyBlue: '#93abd9',
  clearwater: '#b2d6de',
  turkishSea: '#285390',
  electricBlue: '#2766b1',
  iceFlow: '#c9d3d4',
  aquamarine: '#a1c3d4',
  
  // Neutrals
  white: '#f6f5fa',
  silver: '#a2a1a0',
  text: '#2a3441',
  textLight: '#5f6c7b',
  border: '#e1e8ed',
  
  // Semantic
  error: '#dc3545',
  errorLight: '#fef2f2',
  errorBorder: '#fecaca',
  warning: '#f59e0b',
  warningLight: '#fffbeb',
  warningBorder: '#fde68a',
  success: '#10b981',
  successLight: '#ecfdf5',
  successBorder: '#a7f3d0',
  info: '#3b82f6',
  infoLight: '#eff6ff',
  infoBorder: '#bfdbfe',
};

// ============================================================
// LOADING SPINNER
// ============================================================
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
        <span style={{ color: COLORS.textLight, fontSize, fontWeight: 500 }}>
          {message}
        </span>
      )}
    </div>
  );
}

// ============================================================
// ERROR STATE
// ============================================================
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
          <button onClick={onRetry} style={{
            padding: '0.4rem 0.75rem',
            background: 'white',
            border: `1px solid ${COLORS.error}`,
            borderRadius: '6px',
            color: COLORS.error,
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}>
            {retryLabel}
          </button>
        )}
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={{ fontSize: fullPage ? '4rem' : '3rem', marginBottom: '1rem', opacity: 0.8 }}>⚠️</div>
      <h2 style={{
        fontFamily: "'Sora', sans-serif",
        fontSize: fullPage ? '1.5rem' : '1.25rem',
        fontWeight: 700,
        color: COLORS.text,
        marginBottom: '0.5rem',
      }}>{title}</h2>
      <p style={{
        color: COLORS.textLight,
        fontSize: '0.95rem',
        maxWidth: '400px',
        lineHeight: 1.6,
        marginBottom: onRetry ? '1.5rem' : 0,
      }}>{message}</p>
      {onRetry && (
        <button onClick={onRetry} style={{
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
        }}>
          🔄 {retryLabel}
        </button>
      )}
    </div>
  );
}

// ============================================================
// EMPTY STATE
// ============================================================
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
      <div style={{ fontSize: fullPage ? '4rem' : '3rem', marginBottom: '1rem', opacity: 0.6 }}>{icon}</div>
      <h3 style={{
        fontFamily: "'Sora', sans-serif",
        fontSize: fullPage ? '1.5rem' : '1.1rem',
        fontWeight: 700,
        color: COLORS.text,
        marginBottom: '0.5rem',
      }}>{title}</h3>
      {description && (
        <p style={{
          color: COLORS.textLight,
          fontSize: '0.95rem',
          maxWidth: '400px',
          lineHeight: 1.6,
          marginBottom: action ? '1.5rem' : 0,
        }}>{description}</p>
      )}
      {action && (
        action.to ? (
          <Link to={action.to} style={buttonStyle}>{action.label}</Link>
        ) : (
          <button onClick={action.onClick} style={buttonStyle}>{action.label}</button>
        )
      )}
    </div>
  );
}

// ============================================================
// PAGE HEADER (Updated January 4, 2026 - Visual Standards Part 13.1)
// ============================================================
export function PageHeader({ 
  title,
  subtitle = null,
  icon: Icon = null,  // Lucide icon component
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
    <div style={{ marginBottom: '20px' }}>
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
                <Link to={crumb.to} style={{ color: COLORS.textLight, textDecoration: 'none' }}>
                  {crumb.label}
                </Link>
              ) : (
                <span style={{ 
                  color: idx === breadcrumbs.length - 1 ? COLORS.grassGreen : COLORS.textLight,
                  fontWeight: idx === breadcrumbs.length - 1 ? 600 : 400,
                }}>{crumb.label}</span>
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ 
            margin: 0, 
            fontSize: '20px', 
            fontWeight: 600, 
            color: COLORS.text, 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px',
            fontFamily: "'Sora', sans-serif"
          }}>
            {Icon && (
              <div style={{ 
                width: '36px', 
                height: '36px', 
                borderRadius: '10px', 
                backgroundColor: COLORS.grassGreen, 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center' 
              }}>
                <Icon size={20} color="#ffffff" />
              </div>
            )}
            {title}
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
                marginLeft: '8px',
              }}>{badge.label}</span>
            )}
          </h1>
          {subtitle && (
            <p style={{ 
              margin: '6px 0 0 46px', 
              fontSize: '13px', 
              color: COLORS.textLight 
            }}>{subtitle}</p>
          )}
        </div>

        {action && (
          action.to ? (
            <Link to={action.to} style={actionButtonStyle}>
              {action.icon && <span>{action.icon}</span>}
              {action.label}
            </Link>
          ) : (
            <button onClick={action.onClick} style={actionButtonStyle}>
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
// CARD
// ============================================================
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
export function StatusBadge({ status, size = 'md' }) {
  const statusConfig = {
    complete: { bg: COLORS.successLight, color: '#065f46', border: COLORS.successBorder, label: 'Complete' },
    success: { bg: COLORS.successLight, color: '#065f46', border: COLORS.successBorder, label: 'Success' },
    active: { bg: COLORS.successLight, color: '#065f46', border: COLORS.successBorder, label: 'Active' },
    in_progress: { bg: COLORS.warningLight, color: '#92400e', border: COLORS.warningBorder, label: 'In Progress' },
    pending: { bg: COLORS.warningLight, color: '#92400e', border: COLORS.warningBorder, label: 'Pending' },
    processing: { bg: COLORS.infoLight, color: '#1e40af', border: COLORS.infoBorder, label: 'Processing' },
    failed: { bg: COLORS.errorLight, color: '#991b1b', border: COLORS.errorBorder, label: 'Failed' },
    error: { bg: COLORS.errorLight, color: '#991b1b', border: COLORS.errorBorder, label: 'Error' },
  };

  const config = statusConfig[status] || { bg: '#f3f4f6', color: '#6b7280', border: '#e5e7eb', label: status };
  const padSize = size === 'sm' ? '0.2rem 0.5rem' : '0.3rem 0.75rem';
  const fontSz = size === 'sm' ? '0.7rem' : '0.75rem';

  return (
    <span style={{
      display: 'inline-block',
      padding: padSize,
      background: config.bg,
      color: config.color,
      border: `1px solid ${config.border}`,
      borderRadius: '4px',
      fontSize: fontSz,
      fontWeight: 600,
      textTransform: 'capitalize',
    }}>{config.label}</span>
  );
}

// ============================================================
// BUTTON
// ============================================================
export function Button({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  disabled = false,
  loading = false,
  onClick,
  type = 'button',
  style = {},
}) {
  const variants = {
    primary: {
      background: COLORS.grassGreen,
      color: 'white',
      border: 'none',
    },
    secondary: {
      background: 'white',
      color: COLORS.grassGreen,
      border: `2px solid ${COLORS.grassGreen}`,
    },
    danger: {
      background: COLORS.error,
      color: 'white',
      border: 'none',
    },
    ghost: {
      background: 'transparent',
      color: COLORS.textLight,
      border: `1px solid ${COLORS.border}`,
    },
  };

  const sizes = {
    sm: { padding: '0.4rem 0.8rem', fontSize: '0.8rem' },
    md: { padding: '0.6rem 1.2rem', fontSize: '0.9rem' },
    lg: { padding: '0.75rem 1.5rem', fontSize: '1rem' },
  };

  const variantStyle = variants[variant] || variants.primary;
  const sizeStyle = sizes[size] || sizes.md;

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      style={{
        ...variantStyle,
        ...sizeStyle,
        borderRadius: '8px',
        fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.5rem',
        transition: 'all 0.2s ease',
        ...style,
      }}
    >
      {loading && <span style={{ animation: 'xlr8-spin 0.8s linear infinite' }}>⏳</span>}
      {children}
    </button>
  );
}

// ============================================================
// TOAST SYSTEM
// ============================================================
const ToastContext = createContext(null);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback(({ type = 'info', title, message, duration = 4000 }) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, type, title, message }]);
    
    if (duration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, duration);
    }
    
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const toast = {
    success: (title, message) => addToast({ type: 'success', title, message }),
    error: (title, message) => addToast({ type: 'error', title, message }),
    warning: (title, message) => addToast({ type: 'warning', title, message }),
    info: (title, message) => addToast({ type: 'info', title, message }),
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

function ToastContainer({ toasts, onRemove }) {
  if (toasts.length === 0) return null;

  const typeStyles = {
    success: { bg: COLORS.successLight, border: COLORS.successBorder, icon: '✓', color: '#065f46' },
    error: { bg: COLORS.errorLight, border: COLORS.errorBorder, icon: '✕', color: '#991b1b' },
    warning: { bg: COLORS.warningLight, border: COLORS.warningBorder, icon: '⚠', color: '#92400e' },
    info: { bg: COLORS.infoLight, border: COLORS.infoBorder, icon: 'ℹ', color: '#1e40af' },
  };

  return (
    <div style={{
      position: 'fixed',
      top: '1rem',
      right: '1rem',
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column',
      gap: '0.5rem',
      maxWidth: '400px',
    }}>
      {toasts.map(toast => {
        const style = typeStyles[toast.type] || typeStyles.info;
        return (
          <div
            key={toast.id}
            style={{
              background: style.bg,
              border: `1px solid ${style.border}`,
              borderRadius: '8px',
              padding: '1rem',
              display: 'flex',
              gap: '0.75rem',
              alignItems: 'flex-start',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              animation: 'slideIn 0.3s ease',
            }}
          >
            <span style={{ 
              fontSize: '1.25rem', 
              color: style.color,
              fontWeight: 'bold',
            }}>{style.icon}</span>
            <div style={{ flex: 1 }}>
              {toast.title && (
                <div style={{ fontWeight: 600, color: style.color, marginBottom: '0.25rem' }}>
                  {toast.title}
                </div>
              )}
              {toast.message && (
                <div style={{ fontSize: '0.875rem', color: COLORS.text }}>
                  {toast.message}
                </div>
              )}
            </div>
            <button
              onClick={() => onRemove(toast.id)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: style.color,
                fontSize: '1rem',
                padding: 0,
                opacity: 0.7,
              }}
            >×</button>
          </div>
        );
      })}
    </div>
  );
}

// ============================================================
// CONFIRM DIALOG
// ============================================================
export function ConfirmDialog({
  open,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed?',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger',
  onConfirm,
  onCancel,
}) {
  if (!open) return null;

  const variantColors = {
    danger: COLORS.error,
    warning: COLORS.warning,
    primary: COLORS.grassGreen,
  };

  const confirmColor = variantColors[variant] || COLORS.grassGreen;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
    }}>
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '1.5rem',
        maxWidth: '400px',
        width: '90%',
        boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
      }}>
        <h3 style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: '1.25rem',
          fontWeight: 700,
          color: COLORS.text,
          marginBottom: '0.75rem',
        }}>{title}</h3>
        <p style={{
          color: COLORS.textLight,
          fontSize: '0.95rem',
          lineHeight: 1.6,
          marginBottom: '1.5rem',
        }}>{message}</p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{
              padding: '0.6rem 1.2rem',
              background: '#f0f4f7',
              border: 'none',
              borderRadius: '8px',
              color: COLORS.textLight,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >{cancelLabel}</button>
          <button
            onClick={onConfirm}
            style={{
              padding: '0.6rem 1.2rem',
              background: confirmColor,
              border: 'none',
              borderRadius: '8px',
              color: 'white',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// CSS NOTE: Add this to your index.css
// ============================================================
// @keyframes slideIn {
//   from { opacity: 0; transform: translateX(100%); }
//   to { opacity: 1; transform: translateX(0); }
// }

// ============================================================
// TABS COMPONENT
// ============================================================
export function Tabs({ tabs, activeTab, onChange }) {
  return (
    <div style={{
      display: 'flex',
      borderBottom: `1px solid ${COLORS.border}`,
      background: '#fafbfc',
      overflowX: 'auto',
    }}>
      {tabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '1rem 1.5rem',
            border: 'none',
            background: activeTab === tab.id ? 'white' : 'transparent',
            color: activeTab === tab.id ? COLORS.grassGreen : COLORS.textLight,
            fontWeight: 600,
            fontSize: '0.9rem',
            cursor: 'pointer',
            borderBottom: activeTab === tab.id ? `2px solid ${COLORS.grassGreen}` : '2px solid transparent',
            marginBottom: '-1px',
            transition: 'all 0.2s ease',
            whiteSpace: 'nowrap',
          }}
        >
          {tab.icon && <span>{tab.icon}</span>}
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// ============================================================
// TOOLTIP - Re-export from dedicated file
// ============================================================
export { default as Tooltip, SimpleTooltip } from './Tooltip';

export default {
  LoadingSpinner,
  ErrorState,
  EmptyState,
  PageHeader,
  Card,
  StatusBadge,
  Button,
  ToastProvider,
  useToast,
  ConfirmDialog,
  Tabs,
  COLORS,
};
