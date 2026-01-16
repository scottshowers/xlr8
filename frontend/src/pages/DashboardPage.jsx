/**
 * DashboardPage.jsx - Mission Control
 * ====================================
 *
 * Clean, simple dashboard matching mockup design language.
 * Shows:
 * - Quick action: Create New Project
 * - Recent projects list
 * - Simple project cards
 *
 * Phase 4A UX Redesign - January 15, 2026
 */

import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, ChevronRight, Clock, Users, FileText } from 'lucide-react';
import { useProject } from '../context/ProjectContext';
import { useAuth } from '../context/AuthContext';

// Get display name from user object
const getDisplayName = (user) => {
  if (!user) return '';
  if (user.full_name && user.full_name !== user.email) {
    return user.full_name.split(' ')[0]; // First name only
  }
  if (user.email) {
    // Parse from email: scott.showers@... -> Scott
    const localPart = user.email.split('@')[0];
    const firstName = localPart.split(/[._-]/)[0];
    return firstName.charAt(0).toUpperCase() + firstName.slice(1).toLowerCase();
  }
  return '';
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const { projects, loading, selectProject } = useProject();
  const { user } = useAuth();

  const displayName = getDisplayName(user);

  // Get recent projects (last 5)
  const recentProjects = (projects || [])
    .sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at))
    .slice(0, 5);

  const handleProjectClick = (project) => {
    selectProject(project);
    navigate('/findings');
  };

  const getProjectInitials = (name) => {
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
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      {/* Page Header */}
      <div className="xlr8-page-header">
        <h1>Welcome back{displayName ? `, ${displayName}` : ''}</h1>
        <p className="subtitle">Here's what's happening with your projects</p>
      </div>

      {/* Quick Actions */}
      <div style={{ marginBottom: 32 }}>
        <button
          onClick={() => navigate('/projects/new')}
          className="xlr8-btn xlr8-btn-primary"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '14px 24px',
            fontSize: 15,
          }}
        >
          <Plus size={18} />
          Create New Project
        </button>
      </div>

      {/* Recent Projects */}
      <div className="xlr8-card">
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 24,
        }}>
          <h2 style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: 18,
            fontWeight: 700,
            color: '#2a3441',
            margin: 0,
          }}>
            Recent Projects
          </h2>
          <Link
            to="/projects"
            style={{
              fontSize: 14,
              color: '#83b16d',
              textDecoration: 'none',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            View All
            <ChevronRight size={16} />
          </Link>
        </div>

        {loading ? (
          <div style={{ padding: '48px 0', textAlign: 'center', color: '#5f6c7b' }}>
            <div className="spinner" style={{ margin: '0 auto 16px' }} />
            Loading projects...
          </div>
        ) : recentProjects.length === 0 ? (
          <div style={{
            padding: '48px 0',
            textAlign: 'center',
            color: '#5f6c7b',
          }}>
            <FileText size={48} style={{ marginBottom: 16, opacity: 0.3 }} />
            <p style={{ margin: 0, marginBottom: 16 }}>No projects yet</p>
            <button
              onClick={() => navigate('/projects/new')}
              className="xlr8-btn xlr8-btn-secondary"
            >
              Create Your First Project
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {recentProjects.map((project) => (
              <div
                key={project.id}
                onClick={() => handleProjectClick(project)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  padding: 16,
                  background: '#f0f4f7',
                  borderRadius: 10,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(131, 177, 109, 0.1)';
                  e.currentTarget.style.transform = 'translateX(4px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#f0f4f7';
                  e.currentTarget.style.transform = 'translateX(0)';
                }}
              >
                {/* Project Avatar */}
                <div style={{
                  width: 48,
                  height: 48,
                  borderRadius: 10,
                  background: '#83b16d',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: "'Sora', sans-serif",
                  fontWeight: 700,
                  fontSize: 16,
                  flexShrink: 0,
                }}>
                  {getProjectInitials(project.customer || project.name)}
                </div>

                {/* Project Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 15,
                    fontWeight: 600,
                    color: '#2a3441',
                    marginBottom: 4,
                  }}>
                    {project.customer || project.name}
                  </div>
                  <div style={{
                    fontSize: 13,
                    color: '#5f6c7b',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                  }}>
                    <span>{project.system_type || 'UKG Pro'}</span>
                    <span>·</span>
                    <span>{project.engagement_type || 'Implementation'}</span>
                  </div>
                </div>

                {/* Last Updated */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  color: '#94a3b8',
                  fontSize: 13,
                }}>
                  <Clock size={14} />
                  {formatDate(project.updated_at || project.created_at)}
                </div>

                {/* Arrow */}
                <ChevronRight size={20} color="#94a3b8" />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stats Row - Simple summary */}
      {projects && projects.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 20,
          marginTop: 24,
        }}>
          <div className="xlr8-card" style={{ textAlign: 'center', padding: 24 }}>
            <div style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: 36,
              fontWeight: 800,
              color: '#83b16d',
              lineHeight: 1,
              marginBottom: 8,
            }}>
              {projects.length}
            </div>
            <div style={{
              fontSize: 12,
              color: '#5f6c7b',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              fontWeight: 600,
            }}>
              Total Projects
            </div>
          </div>

          <div className="xlr8-card" style={{ textAlign: 'center', padding: 24 }}>
            <div style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: 36,
              fontWeight: 800,
              color: '#285390',
              lineHeight: 1,
              marginBottom: 8,
            }}>
              {projects.filter(p => p.status === 'active' || !p.status).length}
            </div>
            <div style={{
              fontSize: 12,
              color: '#5f6c7b',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              fontWeight: 600,
            }}>
              Active
            </div>
          </div>

          <div className="xlr8-card" style={{ textAlign: 'center', padding: 24 }}>
            <div style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: 36,
              fontWeight: 800,
              color: '#d97706',
              lineHeight: 1,
              marginBottom: 8,
            }}>
              {recentProjects.filter(p => {
                const updated = new Date(p.updated_at || p.created_at);
                const weekAgo = new Date();
                weekAgo.setDate(weekAgo.getDate() - 7);
                return updated > weekAgo;
              }).length}
            </div>
            <div style={{
              fontSize: 12,
              color: '#5f6c7b',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              fontWeight: 600,
            }}>
              Updated This Week
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
