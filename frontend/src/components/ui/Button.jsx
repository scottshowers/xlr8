import React from 'react';

/**
 * Reusable Button Component
 * 
 * Variants:
 * - primary: Grass green (main actions)
 * - secondary: White with border (secondary actions)
 * - danger: Red (destructive actions)
 * - ghost: Transparent (subtle actions)
 * 
 * Sizes:
 * - sm: Small (compact areas)
 * - md: Medium (default)
 * - lg: Large (hero CTAs)
 */

export const Button = ({ 
  children, 
  variant = 'primary', 
  size = 'md',
  icon,
  iconPosition = 'left',
  disabled = false,
  loading = false,
  className = '',
  ...props 
}) => {
  const classes = [
    'xlr8-btn',
    `xlr8-btn--${variant}`,
    size === 'sm' && 'xlr8-btn--sm',
    size === 'lg' && 'xlr8-btn--lg',
    disabled && 'xlr8-btn--disabled',
    loading && 'xlr8-btn--loading',
    className
  ].filter(Boolean).join(' ');

  return (
    <button 
      className={classes} 
      disabled={disabled || loading}
      {...props}
    >
      {loading && <span className="xlr8-spinner xlr8-spinner--sm" />}
      {!loading && icon && iconPosition === 'left' && (
        <span className="xlr8-btn__icon">{icon}</span>
      )}
      {children}
      {!loading && icon && iconPosition === 'right' && (
        <span className="xlr8-btn__icon">{icon}</span>
      )}
    </button>
  );
};

export default Button;
