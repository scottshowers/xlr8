/**
 * ContextBar - Sticky Project Selector
 * 
 * POLISHED: Consistent loading states and styling
 * 
 * Single source of truth for project selection.
 * Customer colors derived from customer name (consistent across app).
 * 
 * For Admin/Consultant: Can navigate without project selected
 * For Customer: Auto-locked to their project (selector hidden)
 */

import React, { useState, useRef, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';
import { useAuth } from '../context/AuthContext';
import { getCustomerColor, getCustomerInitials, getContrastText } from '../utils/customerColors';
import { LoadingSpinner } from './ui';

// Brand Colors
const COLORS = {
  primary: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  clearwater: '#b2d6de',
  aquamarine: '#a1c3d4',
  white: '#f6f5fa',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

export default function ContextBar() {
  const { activeProject, projects, selectProject, clearProject, loading } = useProject();
  const { userRole } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef(null);

  // Customers are locked to their project - hide selector
  const isCustomer = userRole === 'customer';

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
        setSearchTerm('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter projects by search
  const filteredProjects = projects.filter(p => 
    p.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.customer?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSelectProject = (project) => {
    selectProject(project);
    setDropdownOpen(false);
    setSearchTerm('');
  };

  const styles = {
    bar: {
      background: COLORS.primary,
      padding: '0.75rem 1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    },
    left: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
    },
    label: {
      color: 'white',
      fontSize: '0.85rem',
      opacity: 0.9,
      fontWeight: '500',
    },
    selectorWrapper: {
      position: 'relative',
    },
    selector: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.5rem 1rem',
      background: 'rgba(255,255,255,0.15)',
      border: '1px solid rgba(255,255,255,0.3)',
      borderRadius: '8px',
      color: 'white',
      cursor: 'pointer',
      minWidth: '240px',
      transition: 'background 0.2s ease',
    },
    selectorLocked: {
      cursor: 'default',
      background: 'rgba(255,255,255,0.1)',
    },
    projectIcon: (bgColor) => ({
      width: '32px',
      height: '32px',
      background: bgColor,
      borderRadius: '6px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontWeight: '700',
      fontSize: '0.8rem',
      color: getContrastText(bgColor),
      flexShrink: 0,
    }),
    projectInfo: {
      textAlign: 'left',
      flex: 1,
      minWidth: 0,
    },
    projectName: {
      fontWeight: '600',
      fontSize: '0.9rem',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
    },
    projectCustomer: {
      fontSize: '0.75rem',
      opacity: 0.8,
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
    },
    arrow: {
      fontSize: '0.7rem',
      opacity: 0.8,
      transition: 'transform 0.2s ease',
    },
    dropdown: {
      position: 'absolute',
      top: '100%',
      left: 0,
      right: 0,
      marginTop: '4px',
      background: 'white',
      borderRadius: '10px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
      overflow: 'hidden',
      zIndex: 9999,
      minWidth: '280px',
    },
    searchInput: {
      width: '100%',
      padding: '0.75rem 1rem',
      border: 'none',
      borderBottom: '1px solid #e1e8ed',
      fontSize: '0.9rem',
      outline: 'none',
      boxSizing: 'border-box',
    },
    projectList: {
      maxHeight: '320px',
      overflowY: 'auto',
    },
    projectItem: (isActive) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.75rem 1rem',
      cursor: 'pointer',
      background: isActive ? `${COLORS.primary}15` : 'white',
      borderLeft: isActive ? `3px solid ${COLORS.primary}` : '3px solid transparent',
      borderBottom: '1px solid #f0f0f0',
      transition: 'all 0.15s ease',
    }),
    projectItemName: {
      fontWeight: '600',
      color: COLORS.text,
      fontSize: '0.9rem',
    },
    projectItemCustomer: {
      fontSize: '0.75rem',
      color: COLORS.textLight,
    },
    checkmark: {
      width: '20px',
      height: '20px',
      borderRadius: '50%',
      background: COLORS.primary,
      color: 'white',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '0.7rem',
      fontWeight: 'bold',
      flexShrink: 0,
    },
    noProjects: {
      padding: '1.5rem',
      textAlign: 'center',
      color: COLORS.textLight,
      fontSize: '0.9rem',
    },
    loadingState: {
      padding: '1.5rem',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
    },
    allProjectsOption: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.75rem 1rem',
      cursor: 'pointer',
      background: !activeProject ? `${COLORS.primary}15` : 'white',
      borderLeft: !activeProject ? `3px solid ${COLORS.primary}` : '3px solid transparent',
      borderBottom: '2px solid #e1e8ed',
      transition: 'all 0.15s ease',
    },
    allProjectsIcon: {
      width: '32px',
      height: '32px',
      background: COLORS.textLight,
      borderRadius: '6px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '0.9rem',
      color: 'white',
    },
    status: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      color: 'white',
      fontSize: '0.85rem',
    },
    statusDot: (color) => ({
      width: '8px',
      height: '8px',
      background: color || '#90EE90',
      borderRadius: '50%',
      border: '1px solid rgba(255,255,255,0.3)',
    }),
    globalMode: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      color: 'white',
      opacity: 0.9,
    },
  };

  // Customer role: show locked project, no dropdown
  if (isCustomer && activeProject) {
    const customerColor = getCustomerColor(activeProject.customer);
    return (
      <div style={styles.bar}>
        <div style={styles.left}>
          <span style={styles.label}>Project:</span>
          <div style={{ ...styles.selector, ...styles.selectorLocked }}>
            <div style={styles.projectIcon(customerColor)}>
              {getCustomerInitials(activeProject.customer)}
            </div>
            <div style={styles.projectInfo}>
              <div style={styles.projectName}>{activeProject.name}</div>
              <div style={styles.projectCustomer}>{activeProject.customer}</div>
            </div>
          </div>
        </div>
        <div style={styles.status}>
          <div style={styles.statusDot(customerColor)} />
          Active
        </div>
      </div>
    );
  }

  return (
    <div style={styles.bar}>
      <div style={styles.left}>
        <span style={styles.label}>Project:</span>
        
        <div style={styles.selectorWrapper} ref={dropdownRef}>
          <div 
            style={styles.selector}
            onClick={() => setDropdownOpen(!dropdownOpen)}
          >
            {activeProject ? (
              <>
                <div style={styles.projectIcon(getCustomerColor(activeProject.customer))}>
                  {getCustomerInitials(activeProject.customer)}
                </div>
                <div style={styles.projectInfo}>
                  <div style={styles.projectName}>{activeProject.name}</div>
                  <div style={styles.projectCustomer}>{activeProject.customer}</div>
                </div>
              </>
            ) : (
              <div style={styles.globalMode}>
                <span style={{ fontSize: '1.1rem' }}>🌐</span>
                <span>All Projects</span>
              </div>
            )}
            <span style={{ ...styles.arrow, transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0)' }}>▼</span>
          </div>

          {dropdownOpen && (
            <div style={styles.dropdown}>
              {projects.length > 5 && (
                <input
                  type="text"
                  placeholder="Search projects..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={styles.searchInput}
                  autoFocus
                />
              )}
              
              <div style={styles.projectList}>
                {/* "All Projects" option for admin/consultant */}
                {!searchTerm && (
                  <div
                    style={styles.allProjectsOption}
                    onClick={() => handleSelectProject(null)}
                    onMouseEnter={(e) => {
                      if (activeProject) e.currentTarget.style.background = '#f8fafc';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = !activeProject ? `${COLORS.primary}15` : 'white';
                    }}
                  >
                    <div style={styles.allProjectsIcon}>🌐</div>
                    <div style={{ flex: 1 }}>
                      <div style={styles.projectItemName}>All Projects</div>
                      <div style={styles.projectItemCustomer}>View global / aggregate data</div>
                    </div>
                    {!activeProject && (
                      <div style={styles.checkmark}>✓</div>
                    )}
                  </div>
                )}

                {loading ? (
                  <div style={styles.loadingState}>
                    <LoadingSpinner size="sm" message="Loading projects..." />
                  </div>
                ) : filteredProjects.length === 0 ? (
                  <div style={styles.noProjects}>
                    {searchTerm ? 'No matching projects' : 'No projects yet'}
                  </div>
                ) : (
                  filteredProjects.map((project) => {
                    const color = getCustomerColor(project.customer);
                    return (
                      <div
                        key={project.id}
                        style={styles.projectItem(activeProject?.id === project.id)}
                        onClick={() => handleSelectProject(project)}
                        onMouseEnter={(e) => {
                          if (activeProject?.id !== project.id) {
                            e.currentTarget.style.background = '#f8fafc';
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = activeProject?.id === project.id ? `${COLORS.primary}15` : 'white';
                        }}
                      >
                        <div style={styles.projectIcon(color)}>
                          {getCustomerInitials(project.customer)}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={styles.projectItemName}>{project.name}</div>
                          <div style={styles.projectItemCustomer}>{project.customer}</div>
                        </div>
                        {activeProject?.id === project.id && (
                          <div style={styles.checkmark}>✓</div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Status indicator */}
      {activeProject ? (
        <div style={styles.status}>
          <div style={styles.statusDot(getCustomerColor(activeProject.customer))} />
          Active
        </div>
      ) : (
        <div style={styles.status}>
          <div style={styles.statusDot('#90EE90')} />
          Global View
        </div>
      )}
    </div>
  );
}
