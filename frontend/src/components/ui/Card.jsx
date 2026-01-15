import React from 'react';
import './Card.css';

/**
 * Reusable Card Component
 * 
 * White card with rounded corners, border, and hover effects.
 * Used throughout the app for containing content.
 */

export const Card = ({ 
  children, 
  className = '',
  hover = true,
  noPadding = false,
  ...props 
}) => {
  const classes = [
    'xlr8-card',
    hover && 'xlr8-card--hover',
    noPadding && 'xlr8-card--no-padding',
    className
  ].filter(Boolean).join(' ');

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  );
};

export const CardHeader = ({ children, className = '' }) => (
  <div className={`xlr8-card__header ${className}`}>
    {children}
  </div>
);

export const CardTitle = ({ children, icon, className = '' }) => (
  <h2 className={`xlr8-card__title ${className}`}>
    {icon && <span className="xlr8-card__title-icon">{icon}</span>}
    {children}
  </h2>
);

export const CardContent = ({ children, className = '' }) => (
  <div className={`xlr8-card__content ${className}`}>
    {children}
  </div>
);

export default Card;
