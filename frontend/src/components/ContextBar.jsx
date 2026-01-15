/**
 * ContextBar - Minimal Project Selector
 *
 * PHASE 4A UX REDESIGN - Subtle, minimal design
 *
 * Thin bar with project dropdown - doesn't dominate the header.
 * Customer colors derived from customer name.
 *
 * Updated: January 15, 2026 - Simplified to match mockup aesthetic
 */

import React, { useState, useRef, useEffect } from 'react';
import { useProject } from '../context/ProjectContext';
import { useAuth } from '../context/AuthContext';
import { getCustomerColor, getCustomerInitials, getContrastText } from '../utils/customerColors';
import { LoadingSpinner } from './ui';
import { ChevronDown, FolderOpen } from 'lucide-react';

export default function ContextBar() {
  const { activeProject, projects, selectProject, loading } = useProject();
  const { userRole } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef(null);

  const isCustomer = userRole === 'customer';

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

  const filteredProjects = projects.filter(p =>
    p.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.customer?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSelectProject = (project) => {
    selectProject(project);
    setDropdownOpen(false);
    setSearchTerm('');
  };

  // Customer locked view
  if (isCustomer && activeProject) {
    const color = getCustomerColor(activeProject.customer);
    return (
      <div style={{
        background: '#f8fafc',
        borderBottom: '1px solid #e1e8ed',
        padding: '6px 24px',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontSize: 13,
      }}>
        <div style={{
          width: 20,
          height: 20,
          background: color,
          borderRadius: 4,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 9,
          fontWeight: 700,
          color: getContrastText(color),
        }}>
          {getCustomerInitials(activeProject.customer)}
        </div>
        <span style={{ fontWeight: 600, color: '#2a3441' }}>{activeProject.customer}</span>
        <span style={{ color: '#5f6c7b' }}>·</span>
        <span style={{ color: '#5f6c7b' }}>{activeProject.name}</span>
      </div>
    );
  }

  return (
    <div style={{
      background: '#f8fafc',
      borderBottom: '1px solid #e1e8ed',
      padding: '6px 24px',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
    }}>
      <div ref={dropdownRef} style={{ position: 'relative' }}>
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '4px 10px',
            background: activeProject ? 'white' : 'transparent',
            border: `1px solid ${activeProject ? '#e1e8ed' : 'transparent'}`,
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 13,
          }}
        >
          {activeProject ? (
            <>
              <div style={{
                width: 20,
                height: 20,
                background: getCustomerColor(activeProject.customer),
                borderRadius: 4,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 9,
                fontWeight: 700,
                color: getContrastText(getCustomerColor(activeProject.customer)),
              }}>
                {getCustomerInitials(activeProject.customer)}
              </div>
              <span style={{ fontWeight: 600, color: '#2a3441' }}>{activeProject.customer}</span>
              <span style={{ color: '#5f6c7b' }}>·</span>
              <span style={{ color: '#5f6c7b', maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {activeProject.name}
              </span>
            </>
          ) : (
            <>
              <FolderOpen size={14} color="#5f6c7b" />
              <span style={{ color: '#5f6c7b' }}>Select Project</span>
            </>
          )}
          <ChevronDown size={14} color="#5f6c7b" style={{ transform: dropdownOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
        </button>

        {dropdownOpen && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            marginTop: 4,
            background: 'white',
            borderRadius: 8,
            boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
            minWidth: 280,
            zIndex: 1000,
            overflow: 'hidden',
          }}>
            {projects.length > 5 && (
              <input
                type="text"
                placeholder="Search projects..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: 'none',
                  borderBottom: '1px solid #e1e8ed',
                  fontSize: 13,
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
                autoFocus
              />
            )}

            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {/* All Projects option */}
              {!searchTerm && (
                <div
                  onClick={() => handleSelectProject(null)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '10px 12px',
                    cursor: 'pointer',
                    background: !activeProject ? 'rgba(131, 177, 109, 0.1)' : 'white',
                    borderBottom: '1px solid #e1e8ed',
                  }}
                  onMouseEnter={(e) => { if (activeProject) e.currentTarget.style.background = '#f8fafc'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = !activeProject ? 'rgba(131, 177, 109, 0.1)' : 'white'; }}
                >
                  <FolderOpen size={16} color="#5f6c7b" />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#2a3441' }}>All Projects</div>
                    <div style={{ fontSize: 11, color: '#5f6c7b' }}>Global view</div>
                  </div>
                  {!activeProject && <span style={{ color: '#83b16d', fontWeight: 600 }}>✓</span>}
                </div>
              )}

              {loading ? (
                <div style={{ padding: 20, textAlign: 'center' }}>
                  <LoadingSpinner size="sm" />
                </div>
              ) : filteredProjects.length === 0 ? (
                <div style={{ padding: 20, textAlign: 'center', color: '#5f6c7b', fontSize: 13 }}>
                  {searchTerm ? 'No matching projects' : 'No projects yet'}
                </div>
              ) : (
                filteredProjects.map((project) => {
                  const color = getCustomerColor(project.customer);
                  const isActive = activeProject?.id === project.id;
                  return (
                    <div
                      key={project.id}
                      onClick={() => handleSelectProject(project)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '10px 12px',
                        cursor: 'pointer',
                        background: isActive ? 'rgba(131, 177, 109, 0.1)' : 'white',
                        borderBottom: '1px solid #f0f0f0',
                      }}
                      onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = '#f8fafc'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = isActive ? 'rgba(131, 177, 109, 0.1)' : 'white'; }}
                    >
                      <div style={{
                        width: 24,
                        height: 24,
                        background: color,
                        borderRadius: 4,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 10,
                        fontWeight: 700,
                        color: getContrastText(color),
                      }}>
                        {getCustomerInitials(project.customer)}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 600, fontSize: 13, color: '#2a3441' }}>{project.customer}</div>
                        <div style={{ fontSize: 11, color: '#5f6c7b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{project.name}</div>
                      </div>
                      {isActive && <span style={{ color: '#83b16d', fontWeight: 600 }}>✓</span>}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* Project info when selected */}
      {activeProject && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#5f6c7b' }}>
          {activeProject.system_type && <span>{activeProject.system_type}</span>}
          {activeProject.engagement_type && (
            <>
              <span>·</span>
              <span>{activeProject.engagement_type}</span>
            </>
          )}
          {activeProject.target_go_live && (
            <>
              <span>·</span>
              <span>Go-Live: {activeProject.target_go_live}</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
