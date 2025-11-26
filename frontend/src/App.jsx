/**
 * App.jsx - Main Application Entry
 * 
 * STRUCTURE:
 * ┌─────────────────────────────────────┐
 * │ ProjectProvider (global context)    │
 * │ ┌─────────────────────────────────┐ │
 * │ │ Router                          │ │
 * │ │ ├── "/" → Landing (no layout)   │ │
 * │ │ └── Layout wrapper for app      │ │
 * │ │     ├── ContextBar              │ │
 * │ │     ├── Navigation              │ │
 * │ │     └── Page Content            │ │
 * │ └─────────────────────────────────┘ │
 * └─────────────────────────────────────┘
 * 
 * Routes:
 * /           → Landing (public, no layout)
 * /workspace  → WorkspacePage
 * /data       → DataPage (Upload, Vacuum link, Status tabs)
 * /vacuum     → VacuumUploadPage (full extraction tool)
 * /playbooks  → PlaybooksPage (Analysis Playbooks)
 * /admin      → AdminPage (Projects, Data, Global, Settings)
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Context
import { ProjectProvider } from './context/ProjectContext';

// Layout
import Layout from './components/Layout';

// Pages
import Landing from './pages/Landing';
import WorkspacePage from './pages/WorkspacePage';
import DataPage from './pages/DataPage';
import VacuumUploadPage from './pages/VacuumUploadPage';
import PlaybooksPage from './pages/PlaybooksPage';
import AdminPage from './pages/AdminPage';

// CSS
import './index.css';

function App() {
  return (
    <ProjectProvider>
      <Router>
        <Routes>
          {/* Landing page - no layout wrapper */}
          <Route path="/" element={<Landing />} />
          
          {/* App routes - with layout */}
          <Route path="/workspace" element={<Layout><WorkspacePage /></Layout>} />
          <Route path="/data" element={<Layout><DataPage /></Layout>} />
          <Route path="/vacuum" element={<Layout><VacuumUploadPage /></Layout>} />
          <Route path="/playbooks" element={<Layout><PlaybooksPage /></Layout>} />
          <Route path="/admin" element={<Layout><AdminPage /></Layout>} />
          
          {/* Legacy redirects */}
          <Route path="/chat" element={<Navigate to="/workspace" replace />} />
          <Route path="/upload" element={<Navigate to="/data" replace />} />
          <Route path="/status" element={<Navigate to="/data" replace />} />
          <Route path="/projects" element={<Navigate to="/admin" replace />} />
          <Route path="/secure20" element={<Navigate to="/playbooks" replace />} />
          <Route path="/packs" element={<Navigate to="/playbooks" replace />} />
          
          {/* 404 fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </ProjectProvider>
  );
}

export default App;
