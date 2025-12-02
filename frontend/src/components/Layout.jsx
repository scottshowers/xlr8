/**
 * Layout - Main App Wrapper
 * Vertical logo, no Analysis Engine subtitle, fixed scroll
 */

import React, { useEffect, useLayoutEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Rocket } from 'lucide-react';
import ContextBar from './ContextBar';

const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  white: '#f6f5fa',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard', icon: '🏠' },
  { path: '/projects', label: 'Projects', icon: '🏢' },
  { path: '/data', label: 'Data', icon: '📁' },
  { path: '/data-model', label: 'Data Model', icon: '🔗' },
  { path: '/playbooks', label: 'Playbooks', icon: '📋' },
  { path: '/admin', label: 'Admin', icon: '⚙️' },
];

// Full Detail Green H Logo
const HLogoGreen = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 570" style={{ width: '100%', height: '100%' }}>
    <path fill="#698f57" d="M492.04,500v-31.35l-36.53-35.01V163.76c0-15.8,.94-16.74,16.74-16.74h19.79v-31.36l-45.66-45.66H73v31.36l36.53,36.53V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35l45.66,45.66H492.04Z"/>
    <g fill="#a8ca99">
      <rect x="134.8" y="348.24" width="64.39" height="11.87"/>
      <rect x="134.8" y="324.95" width="64.39" height="11.87"/>
      <rect x="134.8" y="302.12" width="64.39" height="11.87"/>
      <rect x="134.8" y="279.29" width="64.39" height="11.87"/>
      <rect x="134.8" y="371.08" width="64.39" height="11.87"/>
      <rect x="134.8" y="393.91" width="64.39" height="11.87"/>
      <rect x="134.8" y="118.1" width="64.39" height="11.87"/>
      <rect x="134.8" y="164.22" width="64.39" height="11.87"/>
      <rect x="320.19" y="140.93" width="64.39" height="11.87"/>
      <rect x="134.8" y="256" width="64.39" height="11.87"/>
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

function Navigation() {
  const location = useLocation();

  const isActive = (path) => {
    if (path === '/dashboard') {
      return location.pathname === '/dashboard';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <nav style={{
      background: 'white',
      borderBottom: '1px solid #e1e8ed',
      padding: '0 1.5rem',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1.5rem',
        maxWidth: '1400px',
        margin: '0 auto',
      }}>
        {/* Vertical Logo */}
        <Link to="/" style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 0',
          textDecoration: 'none',
        }}>
          <div style={{ width: '32px', height: '32px' }}>
            <HLogoGreen />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{
              fontFamily: "'Ubuntu Mono', monospace",
              fontWeight: '700',
              fontSize: '1.1rem',
              color: COLORS.text,
            }}>XLR8</span>
            <Rocket style={{ width: 14, height: 14, color: COLORS.grassGreen }} />
          </div>
        </Link>

        {/* Nav Items */}
        <div style={{ display: 'flex', gap: '0.25rem' }}>
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.875rem 1rem',
                textDecoration: 'none',
                fontSize: '0.875rem',
                fontWeight: '600',
                color: isActive(item.path) ? COLORS.grassGreen : COLORS.textLight,
                borderBottom: isActive(item.path) ? `2px solid ${COLORS.grassGreen}` : '2px solid transparent',
                marginBottom: '-1px',
              }}
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}

export default function Layout({ children }) {
  const location = useLocation();
  
  // useLayoutEffect fires BEFORE browser paint - more reliable for scroll
  useLayoutEffect(() => {
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }, [location.pathname]);

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
        padding: '1rem 1.5rem',
      }}>
        {children}
      </main>
    </div>
  );
}
