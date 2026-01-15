import React from 'react';
import './PageHeader.css';

/**
 * Reusable PageHeader Component
 * 
 * Displays page title, subtitle, and optional action buttons.
 * Used at the top of every page for consistency.
 */

export const PageHeader = ({ 
  title,
  subtitle,
  actions,
  className = '',
  ...props 
}) => {
  return (
    <div className={`xlr8-page-header ${className}`} {...props}>
      <div className="xlr8-page-header__content">
        <h1 className="xlr8-page-header__title">{title}</h1>
        {subtitle && <p className="xlr8-page-header__subtitle">{subtitle}</p>}
      </div>
      {actions && (
        <div className="xlr8-page-header__actions">
          {actions}
        </div>
      )}
    </div>
  );
};

export default PageHeader;
