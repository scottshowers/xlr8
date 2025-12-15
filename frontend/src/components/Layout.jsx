/**
 * Layout.jsx - Main App Wrapper
 * 
 * RESTRUCTURED NAV:
 * Main: Command Center | Projects | Data | Reference Library | Playbooks | Workspace
 * Admin: Admin | Learning (visually separated with thicker divider)
 * 
 * Includes: Upload status indicator, theme toggle, help button
 */

import React, { useLayoutEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Rocket, Sun, Moon, HelpCircle, X } from 'lucide-react';
import ContextBar from './ContextBar';
import { useAuth, Permissions } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { UploadStatusIndicator } from '../context/UploadContext';
import { RestartTourButton } from '../context/OnboardingContext';

const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  white: '#f6f5fa',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

// Main nav items
const MAIN_NAV = [
  { path: '/dashboard', label: 'Command Center', icon: '🏠', permission: null },
  { path: '/projects', label: 'Projects', icon: '🏢', permission: null },
  { path: '/data', label: 'Data', icon: '📁', permission: Permissions.UPLOAD },
  { path: '/reference-library', label: 'Reference Library', icon: '📚', permission: Permissions.PLAYBOOKS },
  { path: '/playbooks', label: 'Playbooks', icon: '📋', permission: Permissions.PLAYBOOKS },
  { path: '/workspace', label: 'Workspace', icon: '💬', permission: null },
];

// Admin nav items - simplified (System moved to Admin tab)
const ADMIN_NAV = [
  { path: '/admin', label: 'Admin', icon: '⚙️', permission: Permissions.OPS_CENTER },
  { path: '/learning-admin', label: 'Learning', icon: '🧠', permission: Permissions.OPS_CENTER },
];

// Logo SVG
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

// Help Panel Component
function HelpPanel({ isOpen, onClose }) {
  if (!isOpen) return null;

  const tips = [
    { icon: '🏠', title: 'Command Center', desc: 'Overview of all projects, recent activity, and quick actions' },
    { icon: '🏢', title: 'Projects', desc: 'Create and manage customer implementation projects' },
    { icon: '📁', title: 'Data', desc: 'Upload customer data files for analysis' },
    { icon: '📚', title: 'Reference Library', desc: 'Global standards and compliance documents' },
    { icon: '📋', title: 'Playbooks', desc: 'Run analysis playbooks against project data' },
    { icon: '💬', title: 'Workspace', desc: 'Chat with AI assistant about your data' },
  ];

  return (
    <div style={{
      position: 'fixed',
      top: '60px',
      right: '1rem',
      width: '320px',
      background: 'white',
      borderRadius: '12px',
      boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
      zIndex: 1000,
      overflow: 'hidden',
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '1rem',
        borderBottom: '1px solid #e1e8ed',
        background: COLORS.grassGreen,
      }}>
        <span style={{ fontWeight: 600, color: 'white' }}>Quick Tips</span>
        <button
          onClick={onClose}
          style={{
            background: 'rgba(255,255,255,0.2)',
            border: 'none',
            borderRadius: '4px',
            padding: '4px',
            cursor: 'pointer',
            display: 'flex',
          }}
        >
          <X size={16} color="white" />
        </button>
      </div>
      <div style={{ padding: '0.75rem', maxHeight: '400px', overflowY: 'auto' }}>
        {tips.map((tip, i) => (
          <div key={i} style={{
            display: 'flex',
            gap: '0.75rem',
            padding: '0.75rem',
            borderRadius: '8px',
            background: i % 2 === 0 ? '#f8fafc' : 'white',
          }}>
            <span style={{ fontSize: '1.25rem' }}>{tip.icon}</span>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', color: COLORS.text }}>{tip.title}</div>
              <div style={{ fontSize: '0.8rem', color: COLORS.textLight, marginTop: '2px' }}>{tip.desc}</div>
            </div>
          </div>
        ))}
        <div style={{
          marginTop: '0.75rem',
          padding: '0.75rem',
          background: `${COLORS.grassGreen}10`,
          borderRadius: '8px',
          fontSize: '0.8rem',
          color: COLORS.textLight,
        }}>
          <strong style={{ color: COLORS.grassGreen }}>Keyboard Shortcuts:</strong>
          <div style={{ marginTop: '0.5rem' }}>
            <div>⌘/Ctrl + K → Quick search</div>
            <div>⌘/Ctrl + N → New project</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Navigation() {
  const location = useLocation();
  const { hasPermission, user, isAdmin, logout } = useAuth();
  const { darkMode, toggle } = useTheme();
  const [helpOpen, setHelpOpen] = useState(false);

  const isActive = (path) => {
    if (path === '/dashboard') return location.pathname === '/dashboard' || location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const filterItems = (items) => items.filter(item => {
    if (!item.permission) return true;
    if (isAdmin) return true;
    return hasPermission(item.permission);
  });

  const mainItems = filterItems(MAIN_NAV);
  const adminItems = filterItems(ADMIN_NAV);
  const showAdminSection = adminItems.length > 0;

  const styles = {
    nav: {
      background: 'white',
      borderBottom: '1px solid #e1e8ed',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    },
    container: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '0 1.5rem',
      maxWidth: '1800px',
      margin: '0 auto',
    },
    left: {
      display: 'flex',
      alignItems: 'center',
      gap: '1.5rem',
    },
    logo: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      textDecoration: 'none',
      color: COLORS.text,
    },
    logoIcon: {
      width: '32px',
      height: '32px',
    },
    logoText: {
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
    },
    logoName: {
      fontFamily: "'Sora', sans-serif",
      fontWeight: 700,
      fontSize: '1.1rem',
      color: COLORS.text,
    },
    navGroup: {
      display: 'flex',
      alignItems: 'center',
    },
    navItems: {
      display: 'flex',
      alignItems: 'center',
    },
    navDivider: {
      width: '2px',
      height: '28px',
      background: '#c9d3d4',
      margin: '0 1rem',
      borderRadius: '1px',
    },
    navLink: (active) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.35rem',
      padding: '0.875rem 0.75rem',
      textDecoration: 'none',
      fontSize: '0.85rem',
      fontWeight: '600',
      color: active ? COLORS.grassGreen : COLORS.textLight,
      borderBottom: active ? `2px solid ${COLORS.grassGreen}` : '2px solid transparent',
      marginBottom: '-1px',
      transition: 'color 0.2s ease',
      whiteSpace: 'nowrap',
    }),
    // Admin links now use SAME font size as main nav
    adminLink: (active) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.35rem',
      padding: '0.875rem 0.75rem',
      textDecoration: 'none',
      fontSize: '0.85rem',
      fontWeight: '600',
      color: active ? COLORS.grassGreen : COLORS.textLight,
      borderBottom: active ? `2px solid ${COLORS.grassGreen}` : '2px solid transparent',
      marginBottom: '-1px',
      transition: 'color 0.2s ease',
      whiteSpace: 'nowrap',
    }),
    rightSection: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
    },
    helpBtn: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '32px',
      height: '32px',
      background: '#f8fafc',
      border: '1px solid #e1e8ed',
      borderRadius: '6px',
      cursor: 'pointer',
      color: COLORS.textLight,
      transition: 'all 0.2s ease',
    },
    themeBtn: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.4rem',
      padding: '0.4rem 0.75rem',
      background: '#f8fafc',
      border: '1px solid #e1e8ed',
      borderRadius: '6px',
      cursor: 'pointer',
      color: COLORS.textLight,
      fontSize: '0.8rem',
    },
    userMenu: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
    },
    userInfo: {
      textAlign: 'right',
    },
    userName: {
      fontSize: '0.85rem',
      fontWeight: '600',
      color: COLORS.text,
    },
    userRole: {
      fontSize: '0.7rem',
      color: COLORS.textLight,
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    },
    logoutBtn: {
      padding: '0.5rem 1rem',
      background: 'transparent',
      border: '1px solid #e1e8ed',
      borderRadius: '6px',
      color: COLORS.textLight,
      fontSize: '0.8rem',
      cursor: 'pointer',
    },
  };

  // Generate data-tour attribute
  const getTourAttr = (path) => `nav-${path.replace('/', '').replace('-', '')}`;

  return (
    <nav style={styles.nav}>
      <div style={styles.container}>
        <div style={styles.left}>
          <Link to="/dashboard" style={styles.logo}>
            <div style={styles.logoIcon}><HLogoGreen /></div>
            <div style={styles.logoText}>
              <span style={styles.logoName}>XLR8</span>
              <Rocket style={{ width: 14, height: 14, color: COLORS.grassGreen }} />
            </div>
          </Link>

          <div style={styles.navGroup}>
            <div style={styles.navItems}>
              {mainItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  data-tour={getTourAttr(item.path)}
                  style={styles.navLink(isActive(item.path))}
                >
                  <span>{item.icon}</span>
                  {item.label}
                </Link>
              ))}
            </div>

            {showAdminSection && (
              <>
                <div style={styles.navDivider} />
                <div style={styles.navItems}>
                  {adminItems.map((item) => (
                    <Link
                      key={item.path}
                      to={item.path}
                      style={styles.adminLink(isActive(item.path))}
                    >
                      <span>{item.icon}</span>
                      {item.label}
                    </Link>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        <div style={styles.rightSection}>
          {/* Upload Status Indicator */}
          <UploadStatusIndicator />
          
          {/* Help Button */}
          <button
            onClick={() => setHelpOpen(!helpOpen)}
            style={{
              ...styles.helpBtn,
              background: helpOpen ? COLORS.grassGreen : '#f8fafc',
              color: helpOpen ? 'white' : COLORS.textLight,
              borderColor: helpOpen ? COLORS.grassGreen : '#e1e8ed',
            }}
            title="Quick Tips"
          >
            <HelpCircle size={16} />
          </button>
          
          {/* Theme Toggle */}
          <button
            data-tour="theme-toggle"
            onClick={toggle}
            style={styles.themeBtn}
          >
            {darkMode ? <Sun size={14} /> : <Moon size={14} />}
            {darkMode ? 'Light' : 'Dark'}
          </button>

          {/* User menu */}
          {user && (
            <div style={styles.userMenu}>
              <div style={styles.userInfo}>
                <div style={styles.userName}>{user.full_name || user.email}</div>
                <div style={styles.userRole}>{user.role}</div>
              </div>
              <button onClick={logout} style={styles.logoutBtn}>Logout</button>
            </div>
          )}
        </div>
      </div>
      
      {/* Help Panel */}
      <HelpPanel isOpen={helpOpen} onClose={() => setHelpOpen(false)} />
    </nav>
  );
}

export default function Layout({ children }) {
  const location = useLocation();

  useLayoutEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div style={{ minHeight: '100vh', background: '#f6f5fa' }}>
      <ContextBar />
      <Navigation />
      <main style={{ padding: '1.5rem', maxWidth: '1800px', margin: '0 auto' }}>
        {children}
      </main>
    </div>
  );
}
