/**
 * Layout.jsx - Main App Layout
 * =============================
 *
 * EXACT match to mockup design:
 * - Step indicator ABOVE header (on project flow pages)
 * - Clean white header with border
 * - Left: Logo + "XLR8"
 * - Center: Nav links (text only, green when active)
 * - Right: User name + role + Logout
 *
 * Phase 4A UX Redesign - January 15, 2026
 */

import React, { useLayoutEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Settings } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

// Helper to derive display name from email if full_name not set
const getDisplayName = (user) => {
  if (!user) return '';
  if (user.full_name && user.full_name !== user.email) {
    return user.full_name;
  }
  if (user.email) {
    const localPart = user.email.split('@')[0];
    return localPart
      .split(/[._-]/)
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  }
  return 'User';
};

// Main nav items - EXACTLY matching mockup
const MAIN_NAV = [
  { path: '/dashboard', label: 'Mission Control' },
  { path: '/projects', label: 'Projects' },
  { path: '/data', label: 'Data' },
  { path: '/playbooks', label: 'Playbooks' },
  { path: '/analytics', label: 'Analytics' },
];

// Step indicator steps - each has a link for navigation
const FLOW_STEPS = [
  { num: 1, label: 'Create Project', link: '/projects/new' },
  { num: 2, label: 'Upload Data', link: '/upload' },
  { num: 3, label: 'Auto-Analysis', link: '/processing' },
  { num: 4, label: 'Findings', link: '/findings' },
  { num: 5, label: 'Drill-In', link: '/findings' },
  { num: 6, label: 'Build Playbook', link: '/build-playbook' },
  { num: 7, label: 'Track Progress', link: '/progress' },
];

// Determine current step based on pathname (for highlighting)
const getCurrentStep = (pathname) => {
  if (pathname === '/projects/new') return 1;
  if (pathname === '/upload' || pathname.startsWith('/data') || pathname.startsWith('/vacuum')) return 2;
  if (pathname.startsWith('/processing')) return 3;
  if (pathname === '/findings') return 4;
  if (pathname.startsWith('/findings/')) return 5;
  if (pathname.startsWith('/build-playbook') || pathname === '/playbooks') return 6;
  if (pathname.startsWith('/progress')) return 7;
  // Default - no step highlighted (dashboard, projects list, etc.)
  return null;
};

// Always show step indicator (it's on every page in the mockup)
const shouldShowStepIndicator = () => {
  return true;
};

// XLR8 Logo SVG (from mockup)
const XLR8Logo = () => (
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

// Step Indicator Component - fixed white bar at very top
function StepIndicator({ currentStep }) {
  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      padding: '12px 24px',
      background: '#ffffff',
      borderBottom: '1px solid #e1e8ed',
      boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      zIndex: 1000,
    }}>
      {FLOW_STEPS.map((step, index) => {
        const isActive = step.num === currentStep;
        const isCompleted = step.num < currentStep;

        return (
          <React.Fragment key={step.num}>
            <Link
              to={step.link}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 14px',
                borderRadius: 20,
                background: isActive ? '#83b16d' : isCompleted ? 'rgba(131, 177, 109, 0.15)' : 'transparent',
                color: isActive ? '#ffffff' : isCompleted ? '#83b16d' : '#5f6c7b',
                fontSize: 13,
                fontWeight: 500,
                border: isActive ? 'none' : '1px solid #e1e8ed',
                textDecoration: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              <span style={{
                width: 18,
                height: 18,
                borderRadius: '50%',
                background: isActive ? 'rgba(255,255,255,0.3)' : isCompleted ? '#83b16d' : '#e1e8ed',
                color: isActive ? '#fff' : isCompleted ? '#fff' : '#5f6c7b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                fontWeight: 700,
              }}>
                {isCompleted ? '✓' : step.num}
              </span>
              {step.label}
            </Link>

            {index < FLOW_STEPS.length - 1 && (
              <span style={{ color: '#c9d3d4', fontSize: 11 }}>→</span>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// Header component - EXACT mockup match
function Header() {
  const location = useLocation();
  const { user, isAdmin, logout } = useAuth();

  const isActive = (path) => {
    if (path === '/dashboard') {
      return location.pathname === '/dashboard' || location.pathname === '/';
    }
    if (path === '/projects') {
      return location.pathname.startsWith('/projects') ||
             location.pathname.startsWith('/findings') ||
             location.pathname.startsWith('/processing') ||
             location.pathname.startsWith('/upload') ||
             location.pathname.startsWith('/build-playbook') ||
             location.pathname.startsWith('/progress');
    }
    if (path === '/data') {
      return location.pathname.startsWith('/data') ||
             location.pathname.startsWith('/vacuum');
    }
    if (path === '/playbooks') {
      return location.pathname === '/playbooks';
    }
    if (path === '/analytics') {
      return location.pathname.startsWith('/analytics');
    }
    return location.pathname.startsWith(path);
  };

  return (
    <header style={{
      background: '#ffffff',
      borderBottom: '1px solid #e1e8ed',
      height: 60,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
    }}>
      {/* Left: Logo */}
      <Link
        to="/dashboard"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          textDecoration: 'none'
        }}
      >
        <div style={{ width: 32, height: 32 }}>
          <XLR8Logo />
        </div>
        <span style={{
          fontFamily: "'Sora', sans-serif",
          fontWeight: 700,
          fontSize: 18,
          color: '#2a3441',
        }}>
          XLR8
        </span>
      </Link>

      {/* Center: Navigation */}
      <nav style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {MAIN_NAV.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            style={{
              padding: '8px 16px',
              textDecoration: 'none',
              fontSize: 14,
              fontWeight: 500,
              color: isActive(item.path) ? '#83b16d' : '#5f6c7b',
              transition: 'color 0.2s',
            }}
          >
            {item.label}
          </Link>
        ))}

        {/* Admin link for admins only */}
        {isAdmin && (
          <Link
            to="/admin"
            style={{
              padding: '8px 16px',
              textDecoration: 'none',
              fontSize: 14,
              fontWeight: 500,
              color: location.pathname.startsWith('/admin') ? '#83b16d' : '#5f6c7b',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <Settings size={14} />
            Admin
          </Link>
        )}
      </nav>

      {/* Right: User info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {user && (
          <>
            <div style={{ textAlign: 'right' }}>
              <div style={{
                fontSize: 14,
                fontWeight: 600,
                color: '#2a3441',
              }}>
                {getDisplayName(user)}
              </div>
              <div style={{
                fontSize: 11,
                color: '#5f6c7b',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                {user.role || 'Consultant'}
              </div>
            </div>
            <button
              onClick={logout}
              style={{
                padding: '8px 16px',
                background: 'transparent',
                border: '1px solid #e1e8ed',
                borderRadius: 6,
                color: '#5f6c7b',
                fontSize: 13,
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#83b16d';
                e.currentTarget.style.color = '#83b16d';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e1e8ed';
                e.currentTarget.style.color = '#5f6c7b';
              }}
            >
              Logout
            </button>
          </>
        )}
      </div>
    </header>
  );
}

// Main Layout
export default function Layout({ children }) {
  const location = useLocation();
  const currentStep = getCurrentStep(location.pathname);
  const showSteps = shouldShowStepIndicator(location.pathname);

  useLayoutEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  // Calculate top padding based on whether step indicator is showing
  const topPadding = showSteps ? 80 : 24; // 80 = 24 padding + ~56 for fixed bar

  return (
    <div style={{
      minHeight: '100vh',
      background: '#f6f5fa',
      padding: 24,
      paddingTop: topPadding,
    }}>
      {/* Step indicator - fixed white bar at very top */}
      {showSteps && <StepIndicator currentStep={currentStep} />}

      {/* Main App Frame - matches mockup .mockup-frame */}
      <div style={{
        background: '#f6f5fa',
        borderRadius: 12,
        border: '1px solid #e1e8ed',
        boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
        minHeight: 'calc(100vh - 120px)',
        overflow: 'hidden',
      }}>
        {/* Header inside the frame - white background */}
        <Header />

        {/* Content area - matches mockup .app-content with 32px padding */}
        <main style={{ padding: 32 }}>
          {children}
        </main>
      </div>
    </div>
  );
}
