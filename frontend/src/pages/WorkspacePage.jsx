/**
 * WorkspacePage.jsx - AI Assist Chat Interface
 * 
 * Clean wrapper for Chat component using unified design system.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import Chat from '../components/Chat';
import { MessageSquare, FolderKanban, ArrowRight } from 'lucide-react';

export default function WorkspacePage() {
  const navigate = useNavigate();
  const { activeProject, projectName, customerName, hasActiveProject, loading } = useProject();

  if (loading) {
    return (
      <div className="chat-page">
        <div className="chat-page__loading">
          <div className="chat-page__spinner" />
          <span>Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-page">
      {/* Page Header */}
      <div className="chat-page__header">
        <div className="chat-page__title-row">
          <div className="chat-page__icon">
            <MessageSquare size={20} />
          </div>
          <div className="chat-page__title-text">
            <h1>AI Assist</h1>
            {hasActiveProject && (
              <span className="chat-page__project-badge">
                <span className="chat-page__project-dot" />
                {customerName && `${customerName} · `}{projectName}
              </span>
            )}
          </div>
        </div>
        <p className="chat-page__subtitle">
          Chat with your data and get intelligent insights
        </p>
      </div>

      {/* Chat Area */}
      <div className="chat-page__content">
        {hasActiveProject ? (
          <Chat />
        ) : (
          <div className="chat-page__empty">
            <div className="chat-page__empty-icon">
              <FolderKanban size={32} />
            </div>
            <h2>Select a Project to Begin</h2>
            <p>Choose a project from Projects to start chatting with AI Assist.</p>
            <button 
              className="chat-page__empty-btn"
              onClick={() => navigate('/customers')}
            >
              Go to Projects
              <ArrowRight size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
