/**
 * MainLayout.jsx - THE ONLY LAYOUT COMPONENT
 * ==========================================
 * 
 * Unified layout for ALL pages in XLR8:
 * - Header (fixed top)
 * - Sidebar (fixed left) 
 * - FlowBar (optional, for 8-step workflow)
 * - Main content area
 * 
 * Usage:
 *   <MainLayout>                         // No flow bar (Mission Control, Projects, Admin)
 *   <MainLayout showFlowBar currentStep={3}>  // With flow bar (workflow pages)
 * 
 * Phase 4A UX Overhaul - January 15, 2026
 */

import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// ============================================================
// FLOW STEPS CONFIGURATION
// ============================================================

const FLOW_STEPS = [
  { num: 1, label: 'Create Project', path: '/projects/new' },
  { num: 2, label: 'Upload Data', path: '/upload' },
  { num: 3, label: 'Select Playbooks', path: '/playbooks/select' },
  { num: 4, label: 'Analysis', path: '/processing' },
  { num: 5, label: 'Findings', path: '/findings' },
  { num: 6, label: 'Drill-In', path: '/findings' },
  { num: 7, label: 'Track Progress', path: '/progress' },
  { num: 8, label: 'Export', path: '/export' },
];

// ============================================================
// XLR8 LOGO SVG
// ============================================================

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

// ============================================================
// HEADER COMPONENT
// ============================================================

const Header = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  
  const getDisplayName = () => {
    if (!user) return 'User';
    if (user.full_name && user.full_name !== user.email) return user.full_name;
    if (user.email) {
      return user.email.split('@')[0]
        .split(/[._-]/)
        .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
        .join(' ');
    }
    return 'User';
  };

  const getInitials = () => {
    const name = getDisplayName();
    return name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase();
  };

  return (
    <header className="xlr8-header">
      <div className="xlr8-header__logo" onClick={() => navigate('/mission-control')}>
        <div className="xlr8-header__logo-icon">
          <XLR8Logo />
        </div>
        <div className="xlr8-header__brand-name">
          XLR8
          <span className="xlr8-header__brand-divider">|</span>
          <span className="xlr8-header__brand-tagline">INTELLIGENT ANALYSIS by HCMPACT</span>
        </div>
      </div>

      <div className="xlr8-header__center">
        <div className="xlr8-header__search">
          <span className="xlr8-header__search-icon">🔍</span>
          <input 
            type="text" 
            className="xlr8-header__search-input" 
            placeholder="Search projects, findings, playbooks..."
          />
        </div>
      </div>

      <div className="xlr8-header__actions">
        <button className="xlr8-header__icon-btn" title="Chat">💬</button>
        <button className="xlr8-header__icon-btn" title="Notifications">
          🔔
          <span className="xlr8-header__badge">3</span>
        </button>
        <button className="xlr8-header__icon-btn" title="Settings">⚙️</button>

        <div className="xlr8-header__user-menu">
          <div className="xlr8-header__user-avatar">{getInitials()}</div>
          <div className="xlr8-header__user-info">
            <div className="xlr8-header__user-name">{getDisplayName()}</div>
            <div className="xlr8-header__user-role">{user?.role || 'Consultant'}</div>
          </div>
          <button 
            onClick={logout}
            className="xlr8-btn xlr8-btn--secondary xlr8-btn--sm"
            style={{ marginLeft: '12px' }}
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
};

// ============================================================
// SIDEBAR COMPONENT
// ============================================================

const Sidebar = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { isAdmin } = useAuth();

  const isActive = (path) => {
    if (path === '/mission-control') return location.pathname === '/mission-control' || location.pathname === '/dashboard';
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  return (
    <>
      <aside className={`xlr8-sidebar ${isCollapsed ? 'xlr8-sidebar--collapsed' : ''}`}>
        {/* Navigation */}
        <div className="xlr8-sidebar__section">
          <div className="xlr8-sidebar__section-title">Navigation</div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/mission-control') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/mission-control')}
          >
            <span className="xlr8-sidebar__icon">🚀</span>
            <span className="xlr8-sidebar__label">Mission Control</span>
          </div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/projects') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/projects')}
          >
            <span className="xlr8-sidebar__icon">📁</span>
            <span className="xlr8-sidebar__label">Projects</span>
          </div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/analytics') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/analytics')}
          >
            <span className="xlr8-sidebar__icon">📊</span>
            <span className="xlr8-sidebar__label">Analytics</span>
          </div>
        </div>

        {/* System */}
        <div className="xlr8-sidebar__section">
          <div className="xlr8-sidebar__section-title">System</div>
          
          {isAdmin && (
            <div 
              className={`xlr8-sidebar__item ${isActive('/admin') ? 'xlr8-sidebar__item--active' : ''}`}
              onClick={() => navigate('/admin')}
            >
              <span className="xlr8-sidebar__icon">⚙️</span>
              <span className="xlr8-sidebar__label">Platform Health</span>
            </div>
          )}
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/admin/playbook-builder') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/admin/playbook-builder')}
          >
            <span className="xlr8-sidebar__icon">📚</span>
            <span className="xlr8-sidebar__label">Playbook Builder</span>
          </div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/standards') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/standards')}
          >
            <span className="xlr8-sidebar__icon">🗄️</span>
            <span className="xlr8-sidebar__label">Standards Library</span>
          </div>
        </div>
      </aside>

      <button 
        className="xlr8-sidebar-toggle"
        onClick={() => setIsCollapsed(!isCollapsed)}
        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        style={{ left: isCollapsed ? '48px' : 'calc(240px - 12px)' }}
      >
        {isCollapsed ? '▶' : '◀'}
      </button>
    </>
  );
};

// ============================================================
// FLOW BAR COMPONENT
// ============================================================

const FlowBar = ({ currentStep = 1 }) => {
  return (
    <div className="xlr8-flow-bar">
      {FLOW_STEPS.map((step, index) => {
        const isActive = step.num === currentStep;
        const isCompleted = step.num < currentStep;
        
        let className = 'xlr8-flow-bar__step';
        if (isActive) className += ' xlr8-flow-bar__step--active';
        if (isCompleted) className += ' xlr8-flow-bar__step--completed';

        return (
          <React.Fragment key={step.num}>
            <Link to={step.path} className={className}>
              <span className="xlr8-flow-bar__step-num">
                {isCompleted ? '✓' : step.num}
              </span>
              {step.label}
            </Link>
            {index < FLOW_STEPS.length - 1 && (
              <span className="xlr8-flow-bar__arrow">→</span>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

// ============================================================
// MAIN LAYOUT COMPONENT
// ============================================================

const MainLayout = ({ 
  children, 
  showFlowBar = false,
  currentStep = 1,
}) => {
  return (
    <div className="xlr8-app">
      <Header />
      <Sidebar />
      {showFlowBar && <FlowBar currentStep={currentStep} />}
      <main className={`xlr8-main ${showFlowBar ? 'xlr8-main--with-flow' : ''}`}>
        {children}
      </main>
    </div>
  );
};

export default MainLayout;
