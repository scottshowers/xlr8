/**
 * TooltipContext.jsx - Global Tooltip Control
 * 
 * Provides ability to enable/disable tooltips across all pages.
 * Persists preference to localStorage.
 * 
 * Deploy to: frontend/src/context/TooltipContext.jsx
 */

import React, { createContext, useContext, useState, useEffect } from 'react';

const TooltipContext = createContext();

export function TooltipProvider({ children }) {
  const [tooltipsEnabled, setTooltipsEnabled] = useState(() => {
    // Check localStorage for saved preference, default to true
    const saved = localStorage.getItem('xlr8-tooltips-enabled');
    return saved !== null ? JSON.parse(saved) : true;
  });

  useEffect(() => {
    localStorage.setItem('xlr8-tooltips-enabled', JSON.stringify(tooltipsEnabled));
  }, [tooltipsEnabled]);

  const toggleTooltips = () => setTooltipsEnabled(prev => !prev);

  return (
    <TooltipContext.Provider value={{ tooltipsEnabled, setTooltipsEnabled, toggleTooltips }}>
      {children}
    </TooltipContext.Provider>
  );
}

export function useTooltips() {
  const context = useContext(TooltipContext);
  // Return default values if no provider (don't throw)
  if (!context) {
    return { tooltipsEnabled: true, setTooltipsEnabled: () => {}, toggleTooltips: () => {} };
  }
  return context;
}

export default TooltipContext;
