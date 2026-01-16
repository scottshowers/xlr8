import React from 'react';

/**
 * LoadingSpinner Component
 * Simple animated spinner for loading states
 */

export const LoadingSpinner = ({ size = 'md', className = '' }) => {
  return (
    <div className={`xlr8-spinner xlr8-spinner--${size} ${className}`}>
      <div className="xlr8-spinner__circle" />
    </div>
  );
};

export default LoadingSpinner;
