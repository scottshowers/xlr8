import React from 'react';
import './Button.css';

/**
 * Reusable Button Component
 * 
 * Variants:
 * - primary: Grass green gradient (main actions)
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
    'xlr8-button',
    `xlr8-button--${variant}`,
    `xlr8-button--${size}`,
    disabled && 'xlr8-button--disabled',
    loading && 'xlr8-button--loading',
    className
  ].filter(Boolean).join(' ');

  return (
    <button 
      className={classes} 
      disabled={disabled || loading}
      {...props}
    >
      {loading && <span className="xlr8-button__spinner" />}
      {!loading && icon && iconPosition === 'left' && (
        <span className="xlr8-button__icon xlr8-button__icon--left">{icon}</span>
      )}
      <span className="xlr8-button__text">{children}</span>
      {!loading && icon && iconPosition === 'right' && (
        <span className="xlr8-button__icon xlr8-button__icon--right">{icon}</span>
      )}
    </button>
  );
};

export default Button;
