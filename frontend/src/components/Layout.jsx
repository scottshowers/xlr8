/**
 * Layout - Main App Wrapper
 * 
 * Structure:
 * ┌─────────────────────────────────────┐
 * │ ContextBar (Project Selector)       │
 * ├─────────────────────────────────────┤
 * │ Navigation (4 items)                │
 * ├─────────────────────────────────────┤
 * │                                     │
 * │ Page Content                        │
 * │                                     │
 * └─────────────────────────────────────┘
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import ContextBar from './ContextBar';

// H Logo SVG Component
const HLogo = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 570" style={{ width: '100%', height: '100%' }}>
    <path fill="#698f57" d="M492.04,500v-31.35l-36.53-35.01V163.76c0-15.8,.94-16.74,16.74-16.74h19.79v-31.36l-45.66-45.66H73v31.36l36.53,36.53V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35l45.66,45.66H492.04Zm-197.11-93.76c0,15.8-.94,16.74-16.74,16.74h-8.07v-103.81h24.81v87.07Zm-24.81-242.48c0-15.8,.94-16.74,16.74-16.74h8.07v95.13h-24.81v-78.39Z"/>
    <g>
      <rect fill="#a8ca99" x="134.8" y="348.24" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="324.95" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="302.12" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="279.29" width="64.39" height="11.87"/>
      <path fill="#a8ca99" d="M134.34,107.14h65.76c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
      <path fill="#a8ca99" d="M319.74,417.19c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.75Z"/>
      <rect fill="#a8ca99" x="134.8" y="371.08" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="393.91" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="118.1" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="164.22" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="140.93" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="256" width="64.39" height="11.87"/>
      <path fill="#a8ca99" d="M134.34,417.19c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.76Z"/>
      <rect fill="#a8ca99" x="134.8" y="140.93" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="233.17" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="187.05" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="210.34" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="371.08" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="324.95" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="348.24" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="279.29" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="302.12" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="393.91" width="64.39" height="11.87"/>
      <path fill="#a8ca99" d="M319.74,107.14h65.75c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
      <rect fill="#a8ca99" x="320.19" y="164.22" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="118.1" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="187.05" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="210.34" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="256" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="233.17" width="64.39" height="11.87"/>
    </g>
    <path fill="#84b26d" d="M426.59,95.27h13.7v-19.18h-173.52v19.18h11.42c19.18,0,22.83,3.65,22.83,22.83V248.24h-82.65V118.1c0-19.18,3.65-22.83,22.83-22.83h11.42v-19.18H79.09v19.18h13.7c19.18,0,22.83,3.65,22.83,22.83V406.24c0,19.18-3.65,22.83-22.83,22.83h-13.7v19.18H252.61v-19.18h-11.42c-19.18,0-22.83-3.65-22.83-22.83v-138.82h82.65v138.82c0,19.18-3.65,22.83-22.83,22.83h-11.42v19.18h173.52v-19.18h-13.7c-19.18,0-22.83-3.65-22.83-22.83V118.1c0-19.18,3.65-22.83,22.83-22.83Z"/>
    <path fill="#9cc28a" d="M426.59,101.36h19.79v-31.36h-183.7v31.36h15.5c15.8,0,16.74,.94,16.74,16.74v124.05h-70.47V118.1c0-15.8,.94-16.74,16.74-16.74h15.5v-31.36H73v31.36h19.79c15.8,0,16.74,.94,16.74,16.74V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35h183.7v-31.35h-15.5c-15.8,0-16.74-.94-16.74-16.74v-132.73h70.47v132.73c0,15.8,.94,16.74-16.74,16.74h-15.5v31.35h183.7v-31.35h-19.79c-15.8,0-16.74-.94-16.74-16.74V118.1c0-15.8,.94-16.74,16.74-16.74Z"/>
  </svg>
);

// Navigation Items - 4 clean sections
const NAV_ITEMS = [
  { path: '/workspace', label: 'Workspace', icon: '💬', description: 'Chat & Analysis' },
  { path: '/data', label: 'Data', icon: '📁', description: 'Upload & Manage' },
  { path: '/playbooks', label: 'Playbooks', icon: '📋', description: 'Analysis Templates' },
  { path: '/admin', label: 'Admin', icon: '⚙️', description: 'Settings & Config' },
];

function Navigation() {
  const location = useLocation();
  
  const isActive = (path) => {
    if (path === '/workspace') {
      return location.pathname === '/' || location.pathname.startsWith('/workspace');
    }
    return location.pathname.startsWith(path);
  };

  const styles = {
    nav: {
      background: 'rgba(255, 255, 255, 0.98)',
      backdropFilter: 'blur(10px)',
      borderBottom: '1px solid #e1e8ed',
      padding: '0.75rem 0',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.04)',
    },
    container: {
      maxWidth: '1400px',
      margin: '0 auto',
      padding: '0 1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    logo: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      textDecoration: 'none',
    },
    logoMark: {
      width: '42px',
      height: '42px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      filter: 'drop-shadow(0 2px 8px rgba(131, 177, 109, 0.25))',
    },
    logoText: {
      display: 'flex',
      alignItems: 'baseline',
      gap: '0.5rem',
    },
    logoMain: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.5rem',
      fontWeight: '700',
      color: '#83b16d',
      letterSpacing: '-0.02em',
    },
    logoSub: {
      fontFamily: "'Manrope', sans-serif",
      fontSize: '0.85rem',
      fontWeight: '600',
      color: '#5f6c7b',
    },
    navLinks: {
      display: 'flex',
      gap: '0.5rem',
      listStyle: 'none',
      margin: 0,
      padding: 0,
    },
    navItem: (active) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.625rem 1.25rem',
      borderRadius: '8px',
      textDecoration: 'none',
      fontSize: '0.9rem',
      fontWeight: '600',
      transition: 'all 0.2s ease',
      color: active ? '#83b16d' : '#5f6c7b',
      background: active 
        ? 'linear-gradient(135deg, rgba(131, 177, 109, 0.12), rgba(147, 171, 217, 0.08))' 
        : 'transparent',
      borderBottom: active ? '2px solid #83b16d' : '2px solid transparent',
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
            <HLogo />
          </div>
          <div style={styles.logoText}>
            <span style={styles.logoMain}>XLR8</span>
            <span style={styles.logoSub}>Analysis Engine</span>
          </div>
        </Link>

        <ul style={styles.navLinks}>
          {NAV_ITEMS.map(item => (
            <li key={item.path}>
              <Link
                to={item.path}
                style={styles.navItem(isActive(item.path))}
                title={item.description}
              >
                <span style={styles.navIcon}>{item.icon}</span>
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}

export default function Layout({ children }) {
  return (
    <div style={{ minHeight: '100vh', background: '#f6f5fa', display: 'flex', flexDirection: 'column' }}>
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
