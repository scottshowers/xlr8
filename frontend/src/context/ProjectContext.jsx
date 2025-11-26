/**
 * ProjectContext - Global Project State Management
 * 
 * Select a project ONCE, it flows everywhere.
 * Persists to localStorage for session continuity.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const ProjectContext = createContext(null);

export function ProjectProvider({ children }) {
  // Active project state
  const [activeProject, setActiveProject] = useState(null);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load projects from API
  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get('/projects/list');
      
      let projectsArray = [];
      if (Array.isArray(response.data)) {
        projectsArray = response.data;
      } else if (response.data?.projects) {
        projectsArray = response.data.projects;
      }
      
      setProjects(projectsArray);
      setError(null);
      
      // Restore active project from localStorage if valid
      const savedProjectId = localStorage.getItem('xlr8_active_project');
      if (savedProjectId) {
        const savedProject = projectsArray.find(p => p.id === savedProjectId);
        if (savedProject) {
          setActiveProject(savedProject);
        }
      }
      
    } catch (err) {
      console.error('Failed to load projects:', err);
      setError('Failed to load projects');
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Select a project
  const selectProject = useCallback((project) => {
    setActiveProject(project);
    if (project) {
      localStorage.setItem('xlr8_active_project', project.id);
    } else {
      localStorage.removeItem('xlr8_active_project');
    }
  }, []);

  // Clear active project
  const clearProject = useCallback(() => {
    setActiveProject(null);
    localStorage.removeItem('xlr8_active_project');
  }, []);

  // Refresh projects (after create/update/delete)
  const refreshProjects = useCallback(async () => {
    await loadProjects();
  }, [loadProjects]);

  // Create a new project
  const createProject = useCallback(async (projectData) => {
    try {
      const response = await api.post('/projects/create', projectData);
      await refreshProjects();
      
      // Auto-select the new project
      if (response.data?.project) {
        selectProject(response.data.project);
      }
      
      return response.data;
    } catch (err) {
      console.error('Failed to create project:', err);
      throw err;
    }
  }, [refreshProjects, selectProject]);

  // Update a project
  const updateProject = useCallback(async (projectId, updates) => {
    try {
      const response = await api.put(`/projects/${projectId}`, updates);
      await refreshProjects();
      
      // Update active project if it was the one updated
      if (activeProject?.id === projectId && response.data?.project) {
        setActiveProject(response.data.project);
      }
      
      return response.data;
    } catch (err) {
      console.error('Failed to update project:', err);
      throw err;
    }
  }, [refreshProjects, activeProject]);

  // Delete a project
  const deleteProject = useCallback(async (projectId) => {
    try {
      await api.delete(`/projects/${projectId}`);
      await refreshProjects();
      
      // Clear active project if it was deleted
      if (activeProject?.id === projectId) {
        clearProject();
      }
      
      return true;
    } catch (err) {
      console.error('Failed to delete project:', err);
      throw err;
    }
  }, [refreshProjects, activeProject, clearProject]);

  const value = {
    // State
    activeProject,
    projects,
    loading,
    error,
    
    // Actions
    selectProject,
    clearProject,
    refreshProjects,
    createProject,
    updateProject,
    deleteProject,
    
    // Computed
    hasActiveProject: !!activeProject,
    projectName: activeProject?.name || null,
    projectId: activeProject?.id || null,
    customerName: activeProject?.customer || null,
  };

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

// Hook to use project context
export function useProject() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
}

// Hook that requires an active project (shows selector if none)
export function useRequireProject() {
  const context = useProject();
  return {
    ...context,
    isReady: context.hasActiveProject && !context.loading,
    needsProject: !context.hasActiveProject && !context.loading,
  };
}

export default ProjectContext;
