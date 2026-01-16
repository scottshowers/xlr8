/**
 * MainLayout.jsx - Unified Application Layout
 * ============================================
 * 
 * Professional layout for XLR8:
 * - Header: Logo + tagline, search, notifications, user menu
 * - Sidebar: Text labels + Lucide icons (NO emojis)
 * - FlowBar: 8-step workflow indicator (only in project context)
 * - Main content area
 * 
 * Design: Enterprise-professional for experienced consultants (35-55)
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useProject } from '../context/ProjectContext';
import { 
  LayoutDashboard,
  FolderKanban,
  BarChart3,
  Settings,
  BookOpen,
  Library,
  MessageSquare,
  HardDrive,
  ChevronLeft,
  ChevronRight,
  Search,
  Bell,
  LogOut,
  Check
} from 'lucide-react';
import logo from '../assets/logo.svg';

// ============================================================
// FLOW STEPS CONFIGURATION
// ============================================================

const FLOW_STEPS = [
  { num: 1, key: 'create', label: 'Create', path: '/projects/new' },
  { num: 2, key: 'upload', label: 'Upload', path: '/data' },
  { num: 3, key: 'playbooks', label: 'Playbooks', path: '/playbooks/select' },
  { num: 4, key: 'analysis', label: 'Analysis', path: '/processing' },
  { num: 5, key: 'findings', label: 'Findings', path: '/findings' },
  { num: 6, key: 'review', label: 'Review', path: null }, // Dynamic based on finding
  { num: 7, key: 'progress', label: 'Progress', path: null }, // Dynamic based on playbook
  { num: 8, key: 'export', label: 'Export', path: '/export' }
];

// ============================================================
// HEADER COMPONENT
// ============================================================

const Header = () => {
  const navigate = useNavigate();
  const { user, logout, isAdmin } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getInitials = (name) => {
    if (!name) return 'U';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  };

  return (
    <header className="xlr8-header">
      <div className="xlr8-header__left">
        <div className="xlr8-header__logo" onClick={() => navigate('/mission-control')}>
          <img src={logo} alt="XLR8" className="xlr8-header__logo-img" />
          <div className="xlr8-header__logo-text">
            <span className="xlr8-header__logo-name">XLR8</span>
            <span className="xlr8-header__logo-divider">|</span>
            <span className="xlr8-header__logo-tagline">INTELLIGENT ANALYSIS BY HCMPACT</span>
          </div>
        </div>
      </div>

      <div className="xlr8-header__center">
        <div className="xlr8-header__search">
          <Search size={16} />
          <span>Search projects, findings, playbooks...</span>
        </div>
      </div>

      <div className="xlr8-header__right">
        <button className="xlr8-header__btn" title="Notifications">
          <Bell size={18} />
          <span className="xlr8-header__notification-badge">3</span>
        </button>

        <div className="xlr8-header__user-menu">
          <div 
            className="xlr8-header__user"
            onClick={() => setShowUserMenu(!showUserMenu)}
          >
            <div className="xlr8-header__avatar">
              {getInitials(user?.full_name || user?.email)}
            </div>
            <div className="xlr8-header__user-info">
              <span className="xlr8-header__user-name">
                {user?.full_name || user?.email || 'User'}
              </span>
              <span className="xlr8-header__user-role">
                {isAdmin ? 'Admin' : 'User'}
              </span>
            </div>
          </div>

          {showUserMenu && (
            <div className="xlr8-header__dropdown">
              <button onClick={handleLogout} className="xlr8-header__dropdown-item">
                <LogOut size={16} />
                Logout
              </button>
            </div>
          )}
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
    if (path === '/mission-control') {
      return location.pathname === '/mission-control' || location.pathname === '/dashboard';
    }
    if (path === '/projects') {
      return location.pathname === '/projects' || location.pathname.startsWith('/projects/');
    }
    // /admin should only match exactly, not /admin/*
    if (path === '/admin') {
      return location.pathname === '/admin' || location.pathname === '/admin/settings';
    }
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const navItems = [
    { 
      section: 'Main',
      items: [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
        { icon: FolderKanban, label: 'Projects', path: '/projects' },
        { icon: HardDrive, label: 'Project Data', path: '/data' },
        { icon: MessageSquare, label: 'AI Assist', path: '/workspace' },
        { icon: BarChart3, label: 'Analytics', path: '/analytics' }
      ]
    },
    {
      section: 'Admin',
      items: [
        ...(isAdmin ? [{ icon: Settings, label: 'Platform Settings', path: '/admin' }] : []),
        { icon: BookOpen, label: 'Playbook Builder', path: '/admin/playbook-builder' },
        { icon: Library, label: 'Global Knowledge', path: '/admin/global-knowledge' }
      ]
    }
  ];

  return (
    <>
      <aside className={`xlr8-sidebar ${isCollapsed ? 'xlr8-sidebar--collapsed' : ''}`}>
        {navItems.map((section, sIdx) => (
          <div key={sIdx} className="xlr8-sidebar__section">
            <div className="xlr8-sidebar__section-title">
              {section.section}
            </div>
            {section.items.map((item, iIdx) => {
              const Icon = item.icon;
              return (
                <div
                  key={iIdx}
                  className={`xlr8-sidebar__item ${isActive(item.path) ? 'xlr8-sidebar__item--active' : ''}`}
                  onClick={() => navigate(item.path)}
                  data-tooltip={item.label}
                >
                  <Icon size={18} className="xlr8-sidebar__icon" />
                  <span className="xlr8-sidebar__label">{item.label}</span>
                </div>
              );
            })}
          </div>
        ))}
      </aside>

      <button
        className={`xlr8-sidebar-toggle ${isCollapsed ? 'xlr8-sidebar-toggle--collapsed' : ''}`}
        onClick={() => setIsCollapsed(!isCollapsed)}
        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </>
  );
};

// ============================================================
// FLOW BAR COMPONENT
// ============================================================

const FlowBar = ({ currentStep = 1, completedSteps = [], hasActiveProject = false }) => {
  const navigate = useNavigate();

  const getStepStatus = (stepNum) => {
    if (completedSteps.includes(stepNum)) return 'completed';
    if (stepNum === currentStep) return 'current';
    return 'pending';
  };

  const handleStepClick = (step) => {
    if (!step.path) return;
    navigate(step.path);
  };
  
  // Dynamic label for step 1 based on whether project exists
  const getStepLabel = (step) => {
    if (step.num === 1 && hasActiveProject) {
      return 'Modify';
    }
    return step.label;
  };

  return (
    <div className="xlr8-flow-bar">
      <div className="xlr8-flow-bar__steps">
        {FLOW_STEPS.map((step, index) => {
          const status = getStepStatus(step.num);
          return (
            <React.Fragment key={step.key}>
              <div
                className={`xlr8-flow-step xlr8-flow-step--${status}`}
                onClick={() => handleStepClick(step)}
              >
                <span className="xlr8-flow-step__num">
                  {status === 'completed' ? <Check size={12} /> : step.num}
                </span>
                <span className="xlr8-flow-step__label">{getStepLabel(step)}</span>
              </div>
              {index < FLOW_STEPS.length - 1 && (
                <span className="xlr8-flow-bar__arrow">-</span>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

// ============================================================
// MAIN LAYOUT COMPONENT
// ============================================================

const MainLayout = ({ children, showFlowBar = false, currentStep = 1, completedSteps = [] }) => {
  const { hasActiveProject } = useProject();
  
  return (
    <div className="xlr8-app">
      <Header />
      <Sidebar />
      
      {showFlowBar && (
        <FlowBar currentStep={currentStep} completedSteps={completedSteps} hasActiveProject={hasActiveProject} />
      )}
      
      <main className={`xlr8-main ${showFlowBar ? 'xlr8-main--with-flow' : ''}`}>
        {children}
      </main>
    </div>
  );
};

export default MainLayout;
