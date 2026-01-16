/**
 * ProjectsPage.jsx - Projects List
 * =================================
 *
 * Clean project list using design system CSS classes.
 * Shows all projects with click to select and view findings.
 *
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, ChevronRight, Clock, MoreVertical, Trash2, Edit2 } from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import { PageHeader } from '../components/ui/PageHeader';

export default function ProjectsPage() {
  const navigate = useNavigate();
  const { projects, loading, selectProject, deleteProject } = useProject();
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
    selectProject(project);
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
    <div className="projects-page">
      {/* Page Header */}
      <PageHeader
        title="Projects"
        subtitle="Manage your analysis engagements"
        actions={
          <button
            onClick={() => navigate('/projects/new')}
            className="xlr8-btn xlr8-btn--primary"
          >
            <Plus size={18} />
            New Project
          </button>
        }
      />

      {/* Search Bar */}
      <div className="projects-page__search">
        <Search size={18} className="projects-page__search-icon" />
        <input
          type="text"
          placeholder="Search projects..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="projects-page__search-input"
        />
      </div>

      {/* Projects Table */}
      <div className="xlr8-card">
        {loading ? (
          <div className="projects-page__loading">
            <div className="spinner" />
            Loading projects...
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="projects-page__empty">
            {searchQuery ? (
              <p>No projects matching "{searchQuery}"</p>
            ) : (
              <>
                <p>No projects yet</p>
                <button
                  onClick={() => navigate('/projects/new')}
                  className="xlr8-btn xlr8-btn--secondary"
                >
                  Create Your First Project
                </button>
              </>
            )}
          </div>
        ) : (
          <div className="projects-table">
            {/* Table Header */}
            <div className="projects-table__header">
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
                className="projects-table__row"
                onClick={() => handleProjectClick(project)}
              >
                {/* Project Name */}
                <div className="projects-table__project">
                  <div className="projects-table__avatar">
                    {getProjectInitials(project.customer || project.name)}
                  </div>
                  <div className="projects-table__info">
                    <div className="projects-table__name">
                      {project.customer || project.name}
                    </div>
                    {project.project_lead && (
                      <div className="projects-table__lead">
                        {project.project_lead}
                      </div>
                    )}
                  </div>
                </div>

                {/* Vendor */}
                <div className="projects-table__cell">
                  {project.vendor || 'UKG'}
                </div>

                {/* Product */}
                <div className="projects-table__cell">
                  {project.system_type || 'Pro'}
                </div>

                {/* Playbooks */}
                <div className="projects-table__cell">
                  {project.playbooks?.length > 0 ? (
                    <span className="projects-table__playbook-badge">
                      {project.playbooks.length} assigned
                    </span>
                  ) : (
                    <span className="projects-table__cell--muted">None</span>
                  )}
                </div>

                {/* Updated */}
                <div className="projects-table__cell projects-table__cell--date">
                  <Clock size={14} />
                  {formatDate(project.updated_at || project.created_at)}
                </div>

                {/* Actions Menu */}
                <div className="projects-table__actions">
                  <button
                    className="projects-table__menu-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuOpen(menuOpen === project.id ? null : project.id);
                    }}
                  >
                    <MoreVertical size={16} />
                  </button>

                  {menuOpen === project.id && (
                    <div className="projects-table__menu">
                      <button
                        className="projects-table__menu-item"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/projects/${project.id}/hub`);
                          setMenuOpen(null);
                        }}
                      >
                        <ChevronRight size={14} />
                        Open
                      </button>
                      <button
                        className="projects-table__menu-item"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/projects/${project.id}/hub`);
                          setMenuOpen(null);
                        }}
                      >
                        <Edit2 size={14} />
                        Edit Project
                      </button>
                      <button
                        className="projects-table__menu-item projects-table__menu-item--danger"
                        onClick={(e) => handleDelete(e, project)}
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
        <div className="projects-page__summary">
          Showing {filteredProjects.length} of {projects?.length || 0} projects
        </div>
      )}
    </div>
  );
}
