import React from 'react';
import { Button } from './Button';
import './EmptyState.css';

/**
 * EmptyState Component
 * Display empty state with optional action
 */

export const EmptyState = ({ 
  icon = '📭',
  title = 'No data yet',
  message = 'Get started by adding your first item.',
  action,
  actionLabel = 'Get Started',
  className = ''
}) => {
  return (
    <div className={`xlr8-empty-state ${className}`}>
      <div className="xlr8-empty-state__icon">{icon}</div>
      <h3 className="xlr8-empty-state__title">{title}</h3>
      <p className="xlr8-empty-state__message">{message}</p>
      {action && (
        <Button onClick={action} variant="primary">
          {actionLabel}
        </Button>
      )}
    </div>
  );
};

export default EmptyState;
