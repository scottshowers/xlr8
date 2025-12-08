/**
 * App.jsx - Main Application Entry
 * 
 * Routes:
 * /           → Landing (public)
 * /login      → LoginPage (public)
 * /dashboard  → DashboardPage (protected)
 * /workspace  → WorkspacePage (Chat + Personas)
 * /projects   → ProjectsPage (Project management)
 * /data       → DataPage (Upload, Vacuum, Status, Data Mgmt, Global, Connections)
 * /vacuum     → VacuumUploadPage (full extraction tool)
 * /vacuum/explore → VacuumExplore (intelligent detection UI)
 * /vacuum/map → VacuumColumnMapping (column mapping interface)
 * /playbooks  → PlaybooksPage (Analysis Playbooks)
 * /admin      → AdminPage (System Monitor + Settings only) - Admin only
 * /data-model → DataModelPage (Visual ERD for relationships)
 * /system     → SystemMonitorPage - Admin only
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
import AdminPage from './pages/AdminPage';
import DataModelPage from './pages/DataModelPage';
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
            
            {/* Protected routes - require authentication */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Layout><DashboardPage /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/workspace" element={
              <ProtectedRoute>
                <Layout><WorkspacePage /></Layout>
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
            
            <Route path="/playbooks" element={
              <ProtectedRoute permission="playbooks">
                <Layout><PlaybooksPage /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/data-model" element={
              <ProtectedRoute permission="data_model">
                <Layout><DataModelPage /></Layout>
              </ProtectedRoute>
            } />
            
            {/* Admin only routes */}
            <Route path="/admin" element={
              <ProtectedRoute permission="ops_center">
                <Layout><AdminPage /></Layout>
              </ProtectedRoute>
            } />
            
            <Route path="/system" element={
              <ProtectedRoute permission="ops_center">
                <Layout><SystemMonitorPage /></Layout>
              </ProtectedRoute>
            } />
            
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
    </AuthProvider>
  );
}

export default App;
