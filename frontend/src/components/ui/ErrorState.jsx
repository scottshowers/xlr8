import React from 'react';
import { Button } from './Button';
import './ErrorState.css';

/**
 * ErrorState Component
 * Display error messages with optional retry action
 */

export const ErrorState = ({ 
  title = 'Something went wrong',
  message = 'An error occurred. Please try again.',
  onRetry,
  className = ''
}) => {
  return (
    <div className={`xlr8-error-state ${className}`}>
      <div className="xlr8-error-state__icon">⚠️</div>
      <h3 className="xlr8-error-state__title">{title}</h3>
      <p className="xlr8-error-state__message">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="primary">
          Try Again
        </Button>
      )}
    </div>
  );
};

export default ErrorState;
