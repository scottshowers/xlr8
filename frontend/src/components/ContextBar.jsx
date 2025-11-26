/**
 * ContextBar - Sticky Project Selector
 * 
 * Sits at top of all app pages (not Landing)
 * Shows current project, allows quick switch
 * 
 * Colors: Grass Green (#83b16d) solid background
 * Icons: Solid colors (Sky Blue, Aquamarine, Clearwater)
 */

import React, { useState, useRef, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';

// Brand Colors
const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  clearwater: '#b2d6de',
  aquamarine: '#a1c3d4',
  white: '#f6f5fa',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

// Color palette for project icons (solid colors, rotating)
const PROJECT_COLORS = [
  COLORS.skyBlue,
  COLORS.aquamarine,
  COLORS.clearwater,
  '#93abd9',  // sky blue variant
  '#a1c3d4',  // aquamarine variant
];

export default function ContextBar() {
  const { activeProject, projects, selectProject, loading } = useProject();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef(null);

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

  // Get initials for project icon
  const getInitials = (name) => {
    if (!name) return '??';
    return name.slice(0, 2).toUpperCase();
  };

  // Get consistent color for project (based on index)
  const getProjectColor = (projectId) => {
    const index = projects.findIndex(p => p.id === projectId);
    return PROJECT_COLORS[index % PROJECT_COLORS.length];
  };

  const handleSelectProject = (project) => {
    selectProject(project);
    setDropdownOpen(false);
    setSearchTerm('');
  };

  const styles = {
    bar: {
      background: COLORS.grassGreen,
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
    selectorHover: {
      background: 'rgba(255,255,255,0.25)',
    },
    projectIcon: (color) => ({
      width: '32px',
      height: '32px',
      background: color,
      borderRadius: '6px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontWeight: '700',
      fontSize: '0.8rem',
      color: 'white',
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
      zIndex: 200,
    },
    searchInput: {
      width: '100%',
      padding: '0.75rem 1rem',
      border: 'none',
      borderBottom: '1px solid #e1e8ed',
      fontSize: '0.9rem',
      outline: 'none',
    },
    projectList: {
      maxHeight: '280px',
      overflowY: 'auto',
    },
    projectItem: (isActive) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.75rem 1rem',
      cursor: 'pointer',
      background: isActive ? COLORS.iceFlow : 'white',
      borderBottom: '1px solid #f0f0f0',
      transition: 'background 0.15s ease',
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
    noProjects: {
      padding: '1.5rem',
      textAlign: 'center',
      color: COLORS.textLight,
      fontSize: '0.9rem',
    },
    status: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      color: 'white',
      fontSize: '0.85rem',
    },
    statusDot: {
      width: '8px',
      height: '8px',
      background: '#90EE90',
      borderRadius: '50%',
    },
    placeholder: {
      color: 'rgba(255,255,255,0.7)',
      fontStyle: 'italic',
    },
  };

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
                <div style={styles.projectIcon(getProjectColor(activeProject.id))}>
                  {getInitials(activeProject.name)}
                </div>
                <div style={styles.projectInfo}>
                  <div style={styles.projectName}>{activeProject.name}</div>
                  <div style={styles.projectCustomer}>{activeProject.customer}</div>
                </div>
              </>
            ) : (
              <span style={styles.placeholder}>Select a project...</span>
            )}
            <span style={{ ...styles.arrow, transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0)' }}>▼</span>
          </div>

          {dropdownOpen && (
            <div style={styles.dropdown}>
              {projects.length > 3 && (
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
                {loading ? (
                  <div style={styles.noProjects}>Loading...</div>
                ) : filteredProjects.length === 0 ? (
                  <div style={styles.noProjects}>
                    {searchTerm ? 'No matching projects' : 'No projects yet'}
                  </div>
                ) : (
                  filteredProjects.map((project) => (
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
                        e.currentTarget.style.background = activeProject?.id === project.id ? COLORS.iceFlow : 'white';
                      }}
                    >
                      <div style={styles.projectIcon(getProjectColor(project.id))}>
                        {getInitials(project.name)}
                      </div>
                      <div>
                        <div style={styles.projectItemName}>{project.name}</div>
                        <div style={styles.projectItemCustomer}>{project.customer}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Status indicator */}
      {activeProject && (
        <div style={styles.status}>
          <div style={styles.statusDot} />
          Active
        </div>
      )}
    </div>
  );
}
