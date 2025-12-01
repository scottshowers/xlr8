/**
 * App.jsx - Main Application Entry
 * 
 * Routes:
 * /           → Landing (public, no layout)
 * /dashboard  → DashboardPage (overview hub)
 * /workspace  → WorkspacePage (Chat + Personas)
 * /projects   → ProjectsPage (Project management)
 * /data       → DataPage (Upload, Vacuum, Status, Data Mgmt, Global, Connections)
 * /vacuum     → VacuumUploadPage (full extraction tool)
 * /vacuum/explore → VacuumExplore (intelligent detection UI)
 * /vacuum/map → VacuumColumnMapping (column mapping interface)
 * /playbooks  → PlaybooksPage (Analysis Playbooks)
 * /admin      → AdminPage (System Monitor + Settings only)
 * /data-model → DataModelPage (Visual ERD for relationships)
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Context
import { ProjectProvider } from './context/ProjectContext';

// Layout
import Layout from './components/Layout';

// Pages
import Landing from './pages/Landing';
import DashboardPage from './pages/DashboardPage';
import WorkspacePage from './pages/WorkspacePage';
import ProjectsPage from './pages/ProjectsPage';
import DataPage from './pages/DataPage';
import VacuumUploadPage from './pages/VacuumUploadPage';
import VacuumExplore from './pages/VacuumExplore';
import VacuumColumnMapping from './pages/VacuumColumnMapping';
import PlaybooksPage from './pages/PlaybooksPage';
import AdminPage from './pages/AdminPage';
import DataModelPage from './pages/DataModelPage';
import SystemMonitorPage from './pages/SystemMonitorPage';

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
          <Route path="/dashboard" element={<Layout><DashboardPage /></Layout>} />
          <Route path="/workspace" element={<Layout><WorkspacePage /></Layout>} />
          <Route path="/projects" element={<Layout><ProjectsPage /></Layout>} />
          <Route path="/data" element={<Layout><DataPage /></Layout>} />
          <Route path="/vacuum" element={<Layout><VacuumUploadPage /></Layout>} />
          <Route path="/vacuum/explore" element={<Layout><VacuumExplore /></Layout>} />
          <Route path="/vacuum/map" element={<Layout><VacuumColumnMapping /></Layout>} />
          <Route path="/playbooks" element={<Layout><PlaybooksPage /></Layout>} />
          <Route path="/admin" element={<Layout><AdminPage /></Layout>} />
          <Route path="/data-model" element={<Layout><DataModelPage /></Layout>} />
          <Route path="/system" element={<Layout><SystemMonitorPage /></Layout>} />
          
          {/* Legacy redirects */}
          <Route path="/chat" element={<Navigate to="/workspace" replace />} />
          <Route path="/upload" element={<Navigate to="/data" replace />} />
          <Route path="/status" element={<Navigate to="/data" replace />} />
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
