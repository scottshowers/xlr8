/**
 * App.jsx - Main Application Entry
 * 
 * RESTRUCTURED NAV:
 * Main: Dashboard | Projects | Data | Reference Library | Playbooks | Workspace
 * Admin: Admin | Learning | System
 * 
 * Routes:
 * /                  → Landing (public)
 * /login             → LoginPage (public)
 * /dashboard         → DashboardPage (Command Center)
 * /projects          → ProjectsPage
 * /data              → DataPage (Upload)
 * /reference-library → ReferenceLibraryPage (was Standards)
 * /playbooks         → PlaybooksPage
 * /workspace         → WorkspacePage (Chat)
 * 
 * Admin:
 * /admin             → AdminPage (Operations Center)
 * /learning-admin    → AdminDashboard (Learning Center)
 * /system            → DataObservatoryPage (Data Observatory)
 * 
 * Legacy routes redirect appropriately
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Context
import { ProjectProvider } from './context/ProjectContext';
import { AuthProvider } from './context/AuthContext';

// Auth Components
import ProtectedRoute from './components/ProtectedRoute';

// Layout
import Layout from './components/Layout';

// Pages
import Landing from './pages/Landing';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import WorkspacePage from './pages/WorkspacePage';
import ProjectsPage from './pages/ProjectsPage';
import DataPage from './pages/DataPage';
import VacuumUploadPage from './pages/VacuumUploadPage';
import VacuumExplore from './pages/VacuumExplore';
import VacuumColumnMapping from './pages/VacuumColumnMapping';
import PlaybooksPage from './pages/PlaybooksPage';
import PlaybookBuilderPage from './pages/PlaybookBuilderPage';
import AdminPage from './pages/AdminPage';
import AdminDashboard from './pages/AdminDashboard';
import DataModelPage from './pages/DataModelPage';
import ReferenceLibraryPage from './pages/ReferenceLibraryPage';
import SystemMonitorPage from './pages/SystemMonitorPage';

// CSS
import './index.css';

function App() {
  return (
    <AuthProvider>
      <ProjectProvider>
        <Router>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<LoginPage />} />
            
            {/* ====== MAIN NAV - Consultant workspace ====== */}
            
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Layout><DashboardPage /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/projects" element={
              <ProtectedRoute>
                <Layout><ProjectsPage /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/data" element={
              <ProtectedRoute permission="upload">
                <Layout><DataPage /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/reference-library" element={
              <ProtectedRoute permission="playbooks">
                <Layout><ReferenceLibraryPage /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/playbooks" element={
              <ProtectedRoute permission="playbooks">
                <Layout><PlaybooksPage /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/workspace" element={
              <ProtectedRoute>
                <Layout><WorkspacePage /></Layout>
              </ProtectedRoute>
            } />
            
            {/* ====== ADMIN NAV - Admin/Ops ====== */}
            
            <Route path="/admin" element={
              <ProtectedRoute permission="ops_center">
                <Layout><AdminPage /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/learning-admin" element={
              <ProtectedRoute permission="ops_center">
                <Layout><AdminDashboard /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/system" element={
              <ProtectedRoute permission="ops_center">
                <Layout><SystemMonitorPage /></Layout>
              </ProtectedRoute>
            } />
            
            {/* ====== OTHER PROTECTED ROUTES ====== */}
            
            <Route path="/vacuum" element={
              <ProtectedRoute permission="vacuum">
                <Layout><VacuumUploadPage /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/vacuum/explore" element={
              <ProtectedRoute permission="vacuum">
                <Layout><VacuumExplore /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/vacuum/map" element={
              <ProtectedRoute permission="vacuum">
                <Layout><VacuumColumnMapping /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/playbook-builder" element={
              <ProtectedRoute permission="ops_center">
                <Layout><PlaybookBuilderPage /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/data-model" element={
              <ProtectedRoute permission="data_model">
                <Layout><DataModelPage /></Layout>
              </ProtectedRoute>
            } />
            
            {/* ====== LEGACY REDIRECTS ====== */}
            
            {/* Standards → Reference Library */}
            <Route path="/standards" element={<Navigate to="/reference-library" replace />} />
            
            {/* Other legacy routes */}
            <Route path="/chat" element={<Navigate to="/workspace" replace />} />
            <Route path="/upload" element={<Navigate to="/data" replace />} />
            <Route path="/status" element={<Navigate to="/system" replace />} />
            <Route path="/secure20" element={<Navigate to="/playbooks" replace />} />
            <Route path="/packs" element={<Navigate to="/playbooks" replace />} />
            
            {/* 404 fallback - go to dashboard if logged in */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Router>
      </ProjectProvider>
    </AuthProvider>
  );
}

export default App;
