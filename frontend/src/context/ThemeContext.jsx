/**
 * ThemeContext.jsx - Shared Theme State
 * 
 * Provides consistent dark/light mode across all pages.
 * Persists to localStorage.
 */

import React, { createContext, useContext, useState, useEffect } from 'react';

// Brand colors
export const BRAND = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
};

// Theme definitions
export const themes = {
  light: {
    name: 'light',
    bg: '#f6f5fa',
    bgCard: '#ffffff',
    border: '#e2e8f0',
    text: '#2a3441',
    textDim: '#5f6c7b',
    accent: BRAND.grassGreen,
    panel: '#ffffff',
    panelBorder: '#e2e8f0',
    panelLight: '#f8fafc',
    textBright: '#2a3441',
  },
  dark: {
    name: 'dark',
    bg: '#1a2332',
    bgCard: '#232f42',
    border: '#334766',
    text: '#e5e7eb',
    textDim: '#9ca3af',
    accent: BRAND.grassGreen,
    panel: '#232f42',
    panelBorder: '#334766',
    panelLight: '#2a3a52',
    textBright: '#f3f4f6',
  },
};

// Semantic status colors (same for both themes)
export const STATUS = {
  green: '#10b981',
  amber: '#f59e0b',
  red: '#ef4444',
  blue: '#3b82f6',
  purple: '#8b5cf6',
};

const ThemeContext = createContext(null);

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}

export function ThemeProvider({ children }) {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('xlr8-theme');
    return saved ? saved === 'dark' : true;
  });

  useEffect(() => {
    localStorage.setItem('xlr8-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  const toggle = () => setDarkMode(!darkMode);
  const T = darkMode ? themes.dark : themes.light;

  return (
    <ThemeContext.Provider value={{ darkMode, toggle, T, themes, STATUS, BRAND }}>
      {children}
    </ThemeContext.Provider>
  );
}

export default ThemeProvider;
