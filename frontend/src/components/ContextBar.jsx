/**
 * ContextBar - Sticky Project Context Selector
 * 
 * Always visible at top. Shows active project.
 * Quick switch between projects without leaving current page.
 */

import React, { useState, useRef, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';

export default function ContextBar() {
  const { 
    activeProject, 
    projects, 
    selectProject, 
    loading,
    customerName,
    projectName 
  } = useProject();
  
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchTerm('');
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter projects by search
  const filteredProjects = projects.filter(p => 
    p.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.customer?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSelect = (project) => {
    selectProject(project);
    setIsOpen(false);
    setSearchTerm('');
  };

  const styles = {
    bar: {
      background: 'linear-gradient(135deg, #2a3441 0%, #3d4f5f 100%)',
      padding: '0.625rem 1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 200,
      boxShadow: '0 2px 8px rgba(42, 52, 65, 0.15)',
    },
    left: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
    },
    label: {
      color: 'rgba(255, 255, 255, 0.6)',
      fontSize: '0.75rem',
      fontWeight: '600',
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
    },
    selectorWrapper: {
      position: 'relative',
    },
    selector: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      background: 'rgba(255, 255, 255, 0.1)',
      border: '1px solid rgba(255, 255, 255, 0.15)',
      borderRadius: '8px',
      padding: '0.5rem 1rem',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      minWidth: '280px',
    },
    selectorHover: {
      background: 'rgba(255, 255, 255, 0.15)',
      borderColor: 'rgba(131, 177, 109, 0.5)',
    },
    projectIcon: {
      width: '32px',
      height: '32px',
      background: 'linear-gradient(135deg, #83b16d 0%, #93abd9 100%)',
      borderRadius: '6px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '0.875rem',
      fontWeight: '700',
      color: 'white',
    },
    projectInfo: {
      flex: 1,
    },
    projectName: {
      color: 'white',
      fontWeight: '600',
      fontSize: '0.95rem',
    },
    customerName: {
      color: 'rgba(255, 255, 255, 0.6)',
      fontSize: '0.8rem',
    },
    placeholder: {
      color: 'rgba(255, 255, 255, 0.5)',
      fontStyle: 'italic',
    },
    chevron: {
      color: 'rgba(255, 255, 255, 0.6)',
      fontSize: '0.75rem',
      transition: 'transform 0.2s ease',
    },
    chevronOpen: {
      transform: 'rotate(180deg)',
    },
    dropdown: {
      position: 'absolute',
      top: 'calc(100% + 8px)',
      left: 0,
      right: 0,
      background: 'white',
      borderRadius: '10px',
      boxShadow: '0 8px 24px rgba(42, 52, 65, 0.2)',
      overflow: 'hidden',
      zIndex: 300,
      minWidth: '320px',
    },
    searchWrapper: {
      padding: '0.75rem',
      borderBottom: '1px solid #e1e8ed',
    },
    searchInput: {
      width: '100%',
      padding: '0.625rem 0.875rem',
      border: '1px solid #e1e8ed',
      borderRadius: '6px',
      fontSize: '0.875rem',
      outline: 'none',
    },
    projectList: {
      maxHeight: '300px',
      overflowY: 'auto',
    },
    projectItem: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.75rem 1rem',
      cursor: 'pointer',
      transition: 'background 0.15s ease',
      borderBottom: '1px solid #f0f4f7',
    },
    projectItemHover: {
      background: '#f8fafc',
    },
    projectItemActive: {
      background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.08))',
      borderLeft: '3px solid #83b16d',
    },
    itemIcon: {
      width: '36px',
      height: '36px',
      background: 'linear-gradient(135deg, #83b16d 0%, #93abd9 100%)',
      borderRadius: '6px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '0.8rem',
      fontWeight: '700',
      color: 'white',
    },
    itemInfo: {
      flex: 1,
    },
    itemName: {
      fontWeight: '600',
      color: '#2a3441',
      fontSize: '0.9rem',
    },
    itemCustomer: {
      color: '#5f6c7b',
      fontSize: '0.8rem',
    },
    emptyState: {
      padding: '2rem',
      textAlign: 'center',
      color: '#5f6c7b',
    },
    right: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
    },
    statusDot: {
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      background: activeProject ? '#83b16d' : '#a2a1a0',
    },
    statusText: {
      color: 'rgba(255, 255, 255, 0.7)',
      fontSize: '0.8rem',
    },
  };

  // Get initials for project icon
  const getInitials = (project) => {
    if (!project) return '?';
    const name = project.name || '';
    return name.substring(0, 2).toUpperCase();
  };

  return (
    <div style={styles.bar}>
      <div style={styles.left}>
        <span style={styles.label}>Working on</span>
        
        <div style={styles.selectorWrapper} ref={dropdownRef}>
          <div 
            style={styles.selector}
            onClick={() => !loading && setIsOpen(!isOpen)}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)';
              e.currentTarget.style.borderColor = 'rgba(131, 177, 109, 0.5)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.15)';
            }}
          >
            {activeProject ? (
              <>
                <div style={styles.projectIcon}>
                  {getInitials(activeProject)}
                </div>
                <div style={styles.projectInfo}>
                  <div style={styles.projectName}>{projectName}</div>
                  <div style={styles.customerName}>{customerName}</div>
                </div>
              </>
            ) : (
              <div style={styles.placeholder}>
                {loading ? 'Loading...' : 'Select a project to begin'}
              </div>
            )}
            <span style={{
              ...styles.chevron,
              ...(isOpen ? styles.chevronOpen : {})
            }}>
              ▼
            </span>
          </div>

          {isOpen && (
            <div style={styles.dropdown}>
              <div style={styles.searchWrapper}>
                <input
                  type="text"
                  placeholder="Search projects..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={styles.searchInput}
                  autoFocus
                />
              </div>
              
              <div style={styles.projectList}>
                {filteredProjects.length === 0 ? (
                  <div style={styles.emptyState}>
                    {searchTerm ? 'No matching projects' : 'No projects yet'}
                  </div>
                ) : (
                  filteredProjects.map(project => (
                    <div
                      key={project.id}
                      style={{
                        ...styles.projectItem,
                        ...(activeProject?.id === project.id ? styles.projectItemActive : {})
                      }}
                      onClick={() => handleSelect(project)}
                      onMouseEnter={(e) => {
                        if (activeProject?.id !== project.id) {
                          e.currentTarget.style.background = '#f8fafc';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (activeProject?.id !== project.id) {
                          e.currentTarget.style.background = 'transparent';
                        }
                      }}
                    >
                      <div style={styles.itemIcon}>
                        {getInitials(project)}
                      </div>
                      <div style={styles.itemInfo}>
                        <div style={styles.itemName}>{project.name}</div>
                        <div style={styles.itemCustomer}>{project.customer}</div>
                      </div>
                      {activeProject?.id === project.id && (
                        <span style={{ color: '#83b16d' }}>✓</span>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={styles.right}>
        <div style={styles.statusDot} />
        <span style={styles.statusText}>
          {activeProject ? 'Project Active' : 'No Project Selected'}
        </span>
      </div>
    </div>
  );
}
