/**
 * ProjectsPage.jsx - Projects List
 * =================================
 *
 * Clean project list matching mockup design.
 * Shows all projects with click to select and view findings.
 *
 * Phase 4A UX Redesign - January 15, 2026
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, ChevronRight, Clock, MoreVertical, Trash2, Edit2 } from 'lucide-react';
import { useProject } from '../context/ProjectContext';

export default function ProjectsPage() {
  const navigate = useNavigate();
  const { projects, loading, setActiveProject, deleteProject } = useProject();
  const [searchQuery, setSearchQuery] = useState('');
  const [menuOpen, setMenuOpen] = useState(null);

  // Filter projects by search
  const filteredProjects = (projects || []).filter(p => {
    const query = searchQuery.toLowerCase();
    return (
      (p.customer || '').toLowerCase().includes(query) ||
      (p.name || '').toLowerCase().includes(query) ||
      (p.system_type || '').toLowerCase().includes(query)
    );
  });

  const handleProjectClick = (project) => {
    setActiveProject(project);
    navigate(`/projects/${project.id}/hub`);
  };

  const handleDelete = async (e, project) => {
    e.stopPropagation();
    if (confirm(`Delete project "${project.customer || project.name}"?`)) {
      await deleteProject(project.id);
    }
    setMenuOpen(null);
  };

  const getProjectInitials = (name) => {
    if (!name) return '??';
    return name
      .split(/[\s-]+/)
      .slice(0, 2)
      .map(w => w[0])
      .join('')
      .toUpperCase();
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Recently';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      {/* Page Header */}
      <div className="xlr8-page-header">
        <h1>Projects</h1>
        <p className="subtitle">Manage your analysis engagements</p>
      </div>

      {/* Actions Row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 24,
      }}>
        {/* Search */}
        <div style={{ position: 'relative', width: 300 }}>
          <Search
            size={18}
            style={{
              position: 'absolute',
              left: 12,
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#94a3b8',
            }}
          />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px 10px 40px',
              border: '1px solid #e1e8ed',
              borderRadius: 8,
              fontSize: 14,
              background: '#f0f4f7',
              color: '#2a3441',
            }}
          />
        </div>

        {/* Create Button */}
        <button
          onClick={() => navigate('/projects/new')}
          className="xlr8-btn xlr8-btn-primary"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <Plus size={18} />
          New Project
        </button>
      </div>

      {/* Projects List */}
      <div className="xlr8-card">
        {loading ? (
          <div style={{ padding: '48px 0', textAlign: 'center', color: '#5f6c7b' }}>
            <div className="spinner" style={{ margin: '0 auto 16px' }} />
            Loading projects...
          </div>
        ) : filteredProjects.length === 0 ? (
          <div style={{
            padding: '48px 0',
            textAlign: 'center',
            color: '#5f6c7b',
          }}>
            {searchQuery ? (
              <p>No projects matching "{searchQuery}"</p>
            ) : (
              <>
                <p style={{ marginBottom: 16 }}>No projects yet</p>
                <button
                  onClick={() => navigate('/projects/new')}
                  className="xlr8-btn xlr8-btn-secondary"
                >
                  Create Your First Project
                </button>
              </>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {/* Table Header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 120px 120px 150px 100px 40px',
              gap: 16,
              padding: '12px 16px',
              borderBottom: '1px solid #e1e8ed',
              fontSize: 12,
              fontWeight: 600,
              color: '#5f6c7b',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              <div>Project</div>
              <div>Vendor</div>
              <div>Product</div>
              <div>Playbooks</div>
              <div>Updated</div>
              <div></div>
            </div>

            {/* Project Rows */}
            {filteredProjects.map((project) => (
              <div
                key={project.id}
                onClick={() => handleProjectClick(project)}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 120px 120px 150px 100px 40px',
                  gap: 16,
                  padding: 16,
                  alignItems: 'center',
                  borderBottom: '1px solid #e1e8ed',
                  cursor: 'pointer',
                  transition: 'background 0.2s',
                  position: 'relative',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(131, 177, 109, 0.05)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                }}
              >
                {/* Project Name */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{
                    width: 40,
                    height: 40,
                    borderRadius: 8,
                    background: '#83b16d',
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontFamily: "'Sora', sans-serif",
                    fontWeight: 700,
                    fontSize: 14,
                    flexShrink: 0,
                  }}>
                    {getProjectInitials(project.customer || project.name)}
                  </div>
                  <div>
                    <div style={{
                      fontSize: 15,
                      fontWeight: 600,
                      color: '#2a3441',
                    }}>
                      {project.customer || project.name}
                    </div>
                    {project.project_lead && (
                      <div style={{ fontSize: 12, color: '#5f6c7b' }}>
                        {project.project_lead}
                      </div>
                    )}
                  </div>
                </div>

                {/* Vendor */}
                <div style={{ fontSize: 14, color: '#5f6c7b' }}>
                  {project.vendor || 'UKG'}
                </div>

                {/* Product */}
                <div style={{ fontSize: 14, color: '#5f6c7b' }}>
                  {project.system_type || 'Pro'}
                </div>

                {/* Playbooks */}
                <div style={{ fontSize: 13, color: '#5f6c7b' }}>
                  {project.playbooks?.length > 0 ? (
                    <span style={{
                      background: '#f0f4f7',
                      padding: '4px 8px',
                      borderRadius: 4,
                      fontSize: 12,
                    }}>
                      {project.playbooks.length} assigned
                    </span>
                  ) : (
                    <span style={{ color: '#94a3b8' }}>None</span>
                  )}
                </div>

                {/* Updated */}
                <div style={{
                  fontSize: 13,
                  color: '#94a3b8',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}>
                  <Clock size={14} />
                  {formatDate(project.updated_at || project.created_at)}
                </div>

                {/* Actions Menu */}
                <div style={{ position: 'relative' }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuOpen(menuOpen === project.id ? null : project.id);
                    }}
                    style={{
                      padding: 8,
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      borderRadius: 6,
                      color: '#94a3b8',
                    }}
                  >
                    <MoreVertical size={16} />
                  </button>

                  {menuOpen === project.id && (
                    <div style={{
                      position: 'fixed',
                      background: '#fff',
                      border: '1px solid #e1e8ed',
                      borderRadius: 8,
                      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                      zIndex: 9999,
                      minWidth: 140,
                    }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/projects/${project.id}/hub`);
                          setMenuOpen(null);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '10px 16px',
                          width: '100%',
                          border: 'none',
                          background: 'transparent',
                          cursor: 'pointer',
                          fontSize: 14,
                          color: '#2a3441',
                          textAlign: 'left',
                        }}
                      >
                        <ChevronRight size={14} />
                        Open
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/projects/${project.id}/edit`);
                          setMenuOpen(null);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '10px 16px',
                          width: '100%',
                          border: 'none',
                          background: 'transparent',
                          cursor: 'pointer',
                          fontSize: 14,
                          color: '#2a3441',
                          textAlign: 'left',
                        }}
                      >
                        <Edit2 size={14} />
                        Edit
                      </button>
                      <button
                        onClick={(e) => handleDelete(e, project)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '10px 16px',
                          width: '100%',
                          border: 'none',
                          background: 'transparent',
                          cursor: 'pointer',
                          fontSize: 14,
                          color: '#993c44',
                          textAlign: 'left',
                        }}
                      >
                        <Trash2 size={14} />
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Summary */}
      {filteredProjects.length > 0 && (
        <div style={{
          marginTop: 16,
          fontSize: 13,
          color: '#5f6c7b',
        }}>
          Showing {filteredProjects.length} of {projects?.length || 0} projects
        </div>
      )}
    </div>
  );
}
