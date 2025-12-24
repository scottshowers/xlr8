/**
 * Layout.jsx - Main App Wrapper
 * 
 * UPDATED: December 23, 2025
 * - Mission Control color palette (#83b16d primary)
 * - Removed dark mode toggle
 * - Command Center → Mission Control
 * - Consistent styling with Dashboard/DataPage
 * 
 * NAV STRUCTURE:
 * Main: Mission Control | Projects | Data | Playbooks | Smart Analytics | AI Assist
 * Admin: Collapsible dropdown with Reference Library, Work Advisor, Playbook Builder, Learning, System
 */

import React, { useLayoutEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Rocket, HelpCircle, ChevronDown, ChevronUp, MessageSquare } from 'lucide-react';
import ContextBar from './ContextBar';
import { useAuth, Permissions } from '../context/AuthContext';
import { UploadStatusIndicator } from '../context/UploadContext';
import { useOnboarding } from '../context/OnboardingContext';
import { useTooltips } from '../context/TooltipContext';
import CustomerGenome, { GenomeButton } from './CustomerGenome';

// Mission Control Color Palette
const COLORS = {
  primary: '#83b16d',      // Grass green
  primaryDark: '#6b9b5a',  // Darker green for hover
  accent: '#285390',       // Turkish sea
  electricBlue: '#2766b1',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  silver: '#a2a1a0',
  white: '#f6f5fa',
  background: '#f0f2f5',
  cardBg: '#ffffff',
  text: '#1a2332',
  textMuted: '#64748b',
  textLight: '#94a3b8',
  border: '#e2e8f0',
  divider: '#e2e8f0',
};

// Sales/Demo page buttons for header
function SalesButtons() {
  const [hovered, setHovered] = useState(null);
  
  const buttons = [
    { id: 'story', path: '/story', icon: '📖', title: 'The Story' },
    { id: 'journey', path: '/journey', icon: '🗺️', title: 'The Journey' },
    { id: 'architecture', path: '/architecture', icon: '🏗️', title: 'Architecture' },
  ];
  
  return (
    <div style={{ display: 'flex', gap: '4px' }}>
      {buttons.map(btn => (
        <Link
          key={btn.id}
          to={btn.path}
          onMouseEnter={() => setHovered(btn.id)}
          onMouseLeave={() => setHovered(null)}
          title={btn.title}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 32,
            height: 32,
            background: hovered === btn.id ? `${COLORS.primary}15` : COLORS.cardBg,
            border: `1px solid ${hovered === btn.id ? COLORS.primary : COLORS.border}`,
            borderRadius: 6,
            cursor: 'pointer',
            transition: 'all 0.15s ease',
            textDecoration: 'none',
            fontSize: '14px',
          }}
        >
          {btn.icon}
        </Link>
      ))}
    </div>
  );
}

// Main nav items - core workflow
const MAIN_NAV = [
  { path: '/dashboard', label: 'Mission Control', icon: '🎯', permission: null },
  { path: '/projects', label: 'Projects', icon: '🏢', permission: null },
  { path: '/data', label: 'Data', icon: '📂', permission: Permissions.UPLOAD },
  { path: '/playbooks', label: 'Playbooks', icon: '📋', permission: Permissions.PLAYBOOKS },
  { path: '/analytics', label: 'Smart Analytics', icon: '📊', permission: null },
  { path: '/workspace', label: 'AI Assist', icon: '💬', permission: null },
];

// Admin nav items - collapsible
const ADMIN_NAV = [
  { path: '/reference-library', label: 'Reference Library', icon: '📚', permission: Permissions.OPS_CENTER },
  { path: '/advisor', label: 'Work Advisor', icon: '💡', permission: Permissions.OPS_CENTER },
  { path: '/playbooks/builder', label: 'Playbook Builder', icon: '🔧', permission: Permissions.OPS_CENTER },
  { path: '/learning-admin', label: 'Learning', icon: '🧠', permission: Permissions.OPS_CENTER },
  { path: '/admin', label: 'System', icon: '⚙️', permission: Permissions.OPS_CENTER },
];

// Logo SVG - Mission Control Green
const HLogoGreen = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 570" style={{ width: '100%', height: '100%' }}>
    <path fill="#6b9b5a" d="M492.04,500v-31.35l-36.53-35.01V163.76c0-15.8,.94-16.74,16.74-16.74h19.79v-31.36l-45.66-45.66H73v31.36l36.53,36.53V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35l45.66,45.66H492.04Z"/>
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
    <path fill="#83b16d" d="M426.59,95.27h13.7v-19.18h-173.52v19.18h11.42c19.18,0,22.83,3.65,22.83,22.83V248.24h-82.65V118.1c0-19.18,3.65-22.83,22.83-22.83h11.42v-19.18H79.09v19.18h13.7c19.18,0,22.83,3.65,22.83,22.83V406.24c0,19.18-3.65,22.83-22.83,22.83h-13.7v19.18H252.61v-19.18h-11.42c-19.18,0-22.83-3.65-22.83-22.83v-138.82h82.65v138.82c0,19.18-3.65,22.83-22.83,22.83h-11.42v19.18h173.52v-19.18h-13.7c-19.18,0-22.83-3.65-22.83-22.83V118.1c0-19.18,3.65-22.83,22.83-22.83Z"/>
    <path fill="#9cc28a" d="M426.59,101.36h19.79v-31.36h-183.7v31.36h15.5c15.8,0,16.74,.94,16.74,16.74v124.05h-70.47V118.1c0-15.8,.94-16.74,16.74-16.74h15.5v-31.36H73v31.36h19.79c15.8,0,16.74,.94,16.74,16.74V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35h183.7v-31.35h-15.5c-15.8,0-16.74-.94-16.74-16.74v-132.73h70.47v132.73c0,15.8,.94,16.74-16.74,16.74h-15.5v31.35h183.7v-31.35h-19.79c-15.8,0-16.74-.94-16.74-16.74V118.1c0-15.8,.94-16.74,16.74-16.74Z"/>
  </svg>
);

function Navigation({ onOpenGenome }) {
  const location = useLocation();
  const { hasPermission, user, isAdmin, logout } = useAuth();
  const { startCurrentPageTour, tourEnabled, setTourEnabled } = useOnboarding();
  const { tooltipsEnabled, toggleTooltips } = useTooltips();
  const [adminExpanded, setAdminExpanded] = useState(false);

  const isActive = (path) => {
    if (path === '/dashboard') return location.pathname === '/dashboard' || location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const isAdminActive = ADMIN_NAV.some(item => isActive(item.path));

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
      background: COLORS.cardBg,
      borderBottom: `1px solid ${COLORS.border}`,
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
      background: COLORS.iceFlow,
      margin: '0 0.75rem',
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
      color: active ? COLORS.primary : COLORS.textMuted,
      borderBottom: active ? `2px solid ${COLORS.primary}` : '2px solid transparent',
      marginBottom: '-1px',
      transition: 'color 0.2s ease',
      whiteSpace: 'nowrap',
    }),
    adminToggle: (active, expanded) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.35rem',
      padding: '0.875rem 0.75rem',
      background: 'transparent',
      border: 'none',
      cursor: 'pointer',
      fontSize: '0.85rem',
      fontWeight: '600',
      color: active || expanded ? COLORS.primary : COLORS.textMuted,
      borderBottom: active ? `2px solid ${COLORS.primary}` : '2px solid transparent',
      marginBottom: '-1px',
      transition: 'color 0.2s ease',
    }),
    adminDropdown: {
      position: 'absolute',
      top: '100%',
      left: 0,
      minWidth: '200px',
      background: COLORS.cardBg,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '8px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      marginTop: '4px',
      overflow: 'hidden',
      zIndex: 100,
    },
    adminDropdownItem: (active) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.75rem 1rem',
      textDecoration: 'none',
      fontSize: '0.85rem',
      fontWeight: active ? '600' : '500',
      color: active ? COLORS.primary : COLORS.text,
      background: active ? `${COLORS.primary}10` : 'transparent',
      borderBottom: `1px solid ${COLORS.divider}`,
      transition: 'background 0.2s ease',
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
      background: COLORS.cardBg,
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      cursor: 'pointer',
      color: COLORS.textMuted,
      transition: 'all 0.2s ease',
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
      color: COLORS.textMuted,
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    },
    logoutBtn: {
      padding: '0.5rem 1rem',
      background: 'transparent',
      border: `1px solid ${COLORS.border}`,
      borderRadius: '6px',
      color: COLORS.textMuted,
      fontSize: '0.8rem',
      cursor: 'pointer',
      transition: 'all 0.15s ease',
    },
  };

  const getTourAttr = (path) => `nav-${path.replace('/', '').replace('-', '')}`;

  return (
    <nav style={styles.nav}>
      <div style={styles.container}>
        <div style={styles.left}>
          <Link to="/dashboard" style={styles.logo}>
            <div style={styles.logoIcon}><HLogoGreen /></div>
            <div style={styles.logoText}>
              <span style={styles.logoName}>XLR8</span>
              <Rocket style={{ width: 14, height: 14, color: COLORS.primary }} />
            </div>
          </Link>

          <div style={styles.navGroup}>
            {/* Main Nav Items */}
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

            {/* Admin Dropdown */}
            {showAdminSection && (
              <>
                <div style={styles.navDivider} />
                <div style={{ position: 'relative' }}>
                  <button
                    onClick={() => setAdminExpanded(!adminExpanded)}
                    onBlur={() => setTimeout(() => setAdminExpanded(false), 200)}
                    style={styles.adminToggle(isAdminActive, adminExpanded)}
                  >
                    <span>🔧</span>
                    Admin
                    {adminExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>

                  {adminExpanded && (
                    <div style={styles.adminDropdown}>
                      {adminItems.map((item) => (
                        <Link
                          key={item.path}
                          to={item.path}
                          style={styles.adminDropdownItem(isActive(item.path))}
                          onMouseEnter={(e) => { if (!isActive(item.path)) e.currentTarget.style.background = `${COLORS.primary}08`; }}
                          onMouseLeave={(e) => { if (!isActive(item.path)) e.currentTarget.style.background = 'transparent'; }}
                        >
                          <span>{item.icon}</span>
                          {item.label}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        <div style={styles.rightSection}>
          {/* Upload Status Indicator */}
          <UploadStatusIndicator />
          
          {/* Sales/Demo Page Buttons */}
          <SalesButtons />
          
          {/* Divider */}
          <div style={{ width: 1, height: 20, background: COLORS.border }} />
          
          {/* Customer Genome Button */}
          <GenomeButton onClick={onOpenGenome} />
          
          {/* Tour Guide Toggle */}
          <button
            onClick={() => {
              if (tourEnabled) {
                setTourEnabled(false);
              } else {
                setTourEnabled(true);
                startCurrentPageTour();
              }
            }}
            style={{
              ...styles.helpBtn,
              background: tourEnabled ? COLORS.primary : COLORS.cardBg,
              color: tourEnabled ? 'white' : COLORS.textMuted,
              borderColor: tourEnabled ? COLORS.primary : COLORS.border,
            }}
            title={tourEnabled ? 'Turn off guide' : 'Turn on guide'}
          >
            <HelpCircle size={16} />
          </button>

          {/* Tooltip Toggle */}
          <button
            onClick={toggleTooltips}
            style={{
              ...styles.helpBtn,
              background: tooltipsEnabled ? COLORS.primary : COLORS.cardBg,
              color: tooltipsEnabled ? 'white' : COLORS.textMuted,
              borderColor: tooltipsEnabled ? COLORS.primary : COLORS.border,
            }}
            title={tooltipsEnabled ? 'Turn off tooltips' : 'Turn on tooltips'}
          >
            <MessageSquare size={16} />
          </button>

          {/* User menu */}
          {user && (
            <div style={styles.userMenu}>
              <div style={styles.userInfo}>
                <div style={styles.userName}>{user.full_name || user.email}</div>
                <div style={styles.userRole}>{user.role}</div>
              </div>
              <button 
                onClick={logout} 
                style={styles.logoutBtn}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = COLORS.primary; e.currentTarget.style.color = COLORS.primary; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = COLORS.border; e.currentTarget.style.color = COLORS.textMuted; }}
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

export default function Layout({ children }) {
  const location = useLocation();
  const [genomeOpen, setGenomeOpen] = useState(false);

  useLayoutEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div style={{ minHeight: '100vh', background: COLORS.background }}>
      {/* Sticky header container */}
      <div style={{ position: 'sticky', top: 0, zIndex: 100 }}>
        <ContextBar />
        <Navigation onOpenGenome={() => setGenomeOpen(true)} />
      </div>
      <main style={{ padding: '1.5rem', maxWidth: '1800px', margin: '0 auto' }}>
        {children}
      </main>
      
      {/* Customer Genome Panel */}
      <CustomerGenome isOpen={genomeOpen} onClose={() => setGenomeOpen(false)} />
    </div>
  );
}
