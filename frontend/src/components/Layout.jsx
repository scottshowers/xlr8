/**
 * Layout - Main App Wrapper
 * 
 * Contains:
 * - ContextBar (project selector)
 * - Navigation (4 items)
 * - Page content
 * 
 * Used by all app pages except Landing
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import ContextBar from './ContextBar';

// Brand Colors
const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  white: '#f6f5fa',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

// Green H Logo SVG Component (for navigation)
const HLogoGreen = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 570" style={{ width: '100%', height: '100%' }}>
    <path fill="#698f57" d="M492.04,500v-31.35l-36.53-35.01V163.76c0-15.8,.94-16.74,16.74-16.74h19.79v-31.36l-45.66-45.66H73v31.36l36.53,36.53V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35l45.66,45.66H492.04Zm-197.11-93.76c0,15.8-.94,16.74-16.74,16.74h-8.07v-103.81h24.81v87.07Zm-24.81-242.48c0-15.8,.94-16.74,16.74-16.74h8.07v95.13h-24.81v-78.39Z"/>
    <g fill="#a8ca99">
      <rect x="134.8" y="348.24" width="64.39" height="11.87"/>
      <rect x="134.8" y="324.95" width="64.39" height="11.87"/>
      <rect x="134.8" y="302.12" width="64.39" height="11.87"/>
      <rect x="134.8" y="279.29" width="64.39" height="11.87"/>
      <path d="M134.34,107.14h65.76c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
      <path d="M319.74,417.19c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.75Z"/>
      <rect x="134.8" y="371.08" width="64.39" height="11.87"/>
      <rect x="134.8" y="393.91" width="64.39" height="11.87"/>
      <rect x="134.8" y="118.1" width="64.39" height="11.87"/>
      <rect x="134.8" y="164.22" width="64.39" height="11.87"/>
      <rect x="320.19" y="140.93" width="64.39" height="11.87"/>
      <rect x="134.8" y="256" width="64.39" height="11.87"/>
      <path d="M134.34,417.19c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.76Z"/>
      <rect x="134.8" y="140.93" width="64.39" height="11.87"/>
      <rect x="134.8" y="233.17" width="64.39" height="11.87"/>
      <rect x="134.8" y="187.05" width="64.39" height="11.87"/>
      <rect x="134.8" y="210.34" width="64.39" height="11.87"/>
      <rect x="320.19" y="371.08" width="64.39" height="11.87"/>
      <rect x="320.19" y="324.95" width="64.39" height="11.87"/>
      <rect x="320.19" y="348.24" width="64.39" height="11.87"/>
      <rect x="320.19" y="279.29" width="64.39" height="11.87"/>
      <rect x="320.19" y="302.12" width="64.39" height="11.87"/>
      <rect x="320.19" y="393.91" width="64.39" height="11.87"/>
      <path d="M319.74,107.14h65.75c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
      <rect x="320.19" y="164.22" width="64.39" height="11.87"/>
      <rect x="320.19" y="118.1" width="64.39" height="11.87"/>
      <rect x="320.19" y="187.05" width="64.39" height="11.87"/>
      <rect x="320.19" y="210.34" width="64.39" height="11.87"/>
      <rect x="320.19" y="256" width="64.39" height="11.87"/>
      <rect x="320.19" y="233.17" width="64.39" height="11.87"/>
    </g>
    <path fill="#84b26d" d="M426.59,95.27h13.7v-19.18h-173.52v19.18h11.42c19.18,0,22.83,3.65,22.83,22.83V248.24h-82.65V118.1c0-19.18,3.65-22.83,22.83-22.83h11.42v-19.18H79.09v19.18h13.7c19.18,0,22.83,3.65,22.83,22.83V406.24c0,19.18-3.65,22.83-22.83,22.83h-13.7v19.18H252.61v-19.18h-11.42c-19.18,0-22.83-3.65-22.83-22.83v-138.82h82.65v138.82c0,19.18-3.65,22.83-22.83,22.83h-11.42v19.18h173.52v-19.18h-13.7c-19.18,0-22.83-3.65-22.83-22.83V118.1c0-19.18,3.65-22.83,22.83-22.83Z"/>
    <path fill="#9cc28a" d="M426.59,101.36h19.79v-31.36h-183.7v31.36h15.5c15.8,0,16.74,.94,16.74,16.74v124.05h-70.47V118.1c0-15.8,.94-16.74,16.74-16.74h15.5v-31.36H73v31.36h19.79c15.8,0,16.74,.94,16.74,16.74V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35h183.7v-31.35h-15.5c-15.8,0-16.74-.94-16.74-16.74v-132.73h70.47v132.73c0,15.8,.94,16.74-16.74,16.74h-15.5v31.35h183.7v-31.35h-19.79c-15.8,0-16.74-.94-16.74-16.74V118.1c0-15.8,.94-16.74,16.74-16.74Z"/>
  </svg>
);

// Navigation items
const NAV_ITEMS = [
  { path: '/workspace', label: 'Workspace', icon: '💬' },
  { path: '/data', label: 'Data', icon: '📁' },
  { path: '/playbooks', label: 'Playbooks', icon: '📋' },
  { path: '/admin', label: 'Admin', icon: '⚙️' },
];

function Navigation() {
  const location = useLocation();

  const isActive = (path) => {
    if (path === '/workspace') {
      return location.pathname === '/workspace' || location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  const styles = {
    nav: {
      background: 'white',
      borderBottom: '1px solid #e1e8ed',
      padding: '0 1.5rem',
    },
    container: {
      display: 'flex',
      alignItems: 'center',
      gap: '2rem',
      maxWidth: '1400px',
      margin: '0 auto',
    },
    logo: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.75rem 0',
      textDecoration: 'none',
    },
    logoMark: {
      width: '36px',
      height: '36px',
    },
    logoText: {
      display: 'flex',
      flexDirection: 'column',
    },
    logoMain: {
      fontFamily: "'Sora', sans-serif",
      fontWeight: '700',
      fontSize: '1.1rem',
      color: COLORS.text,
      lineHeight: 1,
    },
    logoSub: {
      fontFamily: "'Manrope', sans-serif",
      fontSize: '0.65rem',
      color: COLORS.textLight,
      marginTop: '2px',
    },
    navItems: {
      display: 'flex',
      gap: '0.5rem',
    },
    navItem: (active) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '1rem 1.25rem',
      textDecoration: 'none',
      fontSize: '0.9rem',
      fontWeight: '600',
      color: active ? COLORS.grassGreen : COLORS.textLight,
      borderBottom: active ? `2px solid ${COLORS.grassGreen}` : '2px solid transparent',
      marginBottom: '-1px',
      transition: 'all 0.2s ease',
    }),
    navIcon: {
      fontSize: '1rem',
    },
  };

  return (
    <nav style={styles.nav}>
      <div style={styles.container}>
        <Link to="/" style={styles.logo}>
          <div style={styles.logoMark}>
            <HLogoGreen />
          </div>
          <div style={styles.logoText}>
            <span style={styles.logoMain}>XLR8</span>
            <span style={styles.logoSub}>Analysis Engine</span>
          </div>
        </Link>

        <div style={styles.navItems}>
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              style={styles.navItem(isActive(item.path))}
            >
              <span style={styles.navIcon}>{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}

export default function Layout({ children }) {
  return (
    <div style={{ 
      minHeight: '100vh', 
      background: COLORS.white, 
      display: 'flex', 
      flexDirection: 'column' 
    }}>
      <ContextBar />
      <Navigation />
      <main style={{ 
        flex: 1, 
        maxWidth: '1400px', 
        width: '100%',
        margin: '0 auto', 
        padding: '1.5rem',
      }}>
        {children}
      </main>
    </div>
  );
}
