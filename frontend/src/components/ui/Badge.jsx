import React from 'react';
import './Badge.css';

/**
 * Reusable Badge Component
 * 
 * Variants:
 * - critical: Red (critical findings, errors)
 * - warning: Amber (warnings, cautions)
 * - info: Blue (informational)
 * - success: Green (completed, success)
 * - neutral: Gray (default, neutral)
 */

export const Badge = ({ 
  children, 
  variant = 'neutral',
  dot = false,
  className = '',
  ...props 
}) => {
  const classes = [
    'xlr8-badge',
    `xlr8-badge--${variant}`,
    dot && 'xlr8-badge--with-dot',
    className
  ].filter(Boolean).join(' ');

  return (
    <span className={classes} {...props}>
      {dot && <span className="xlr8-badge__dot" />}
      {children}
    </span>
  );
};

export default Badge;
