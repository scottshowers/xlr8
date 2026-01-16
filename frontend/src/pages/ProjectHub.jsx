/**
 * ProjectHub.jsx - Project Workspace
 */

import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';

export default function ProjectHub() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { projects, selectProject } = useProject();
  
  // Find project - handle string/number mismatch
  const project = projects?.find(p => String(p.id) === String(id));
  
  // If no project found, show message
  if (!project) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <h2>Project Not Found</h2>
        <p>Looking for project ID: {id}</p>
        <p>Available projects: {projects?.length || 0}</p>
        <button 
          onClick={() => navigate('/projects')}
          className="xlr8-btn xlr8-btn--primary"
          style={{ marginTop: 20 }}
        >
          Back to Projects
        </button>
      </div>
    );
  }

  // Set as active project
  React.useEffect(() => {
    if (project) {
      selectProject(project);
    }
  }, [project, selectProject]);

  return (
    <div style={{ padding: 40 }}>
      <h1>{project.customer || project.name || 'Unnamed Project'}</h1>
      <p>Project ID: {project.id}</p>
      <p>System: {project.system_type || 'Not set'}</p>
      
      <div style={{ marginTop: 30, display: 'flex', gap: 10 }}>
        <button 
          onClick={() => navigate('/upload')}
          className="xlr8-btn xlr8-btn--primary"
        >
          Upload Data
        </button>
        <button 
          onClick={() => navigate('/findings')}
          className="xlr8-btn xlr8-btn--secondary"
        >
          View Findings
        </button>
        <button 
          onClick={() => navigate('/projects')}
          className="xlr8-btn xlr8-btn--secondary"
        >
          Back to Projects
        </button>
      </div>
    </div>
  );
}
