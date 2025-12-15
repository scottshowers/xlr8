/**
 * App.jsx - Main Application Entry
 * 
 * NAV STRUCTURE:
 * Main: Dashboard | Projects | Data | Reference Library | Playbooks | Workspace
 * Admin: Admin | Learning (System moved to Admin tab)
 * 
 * PROVIDERS:
 * - AuthProvider
 * - ProjectProvider  
 * - ThemeProvider (consistent dark/light)
 * - UploadProvider (background uploads)
 * - OnboardingProvider (Joyride tours)
 * 
 * Updated: December 15, 2025 - Added WorkAdvisor (replaces PlaybookBuilderPage)
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Context Providers
import { ProjectProvider } from './context/ProjectContext';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { UploadProvider } from './context/UploadContext';
import { OnboardingProvider } from './context/OnboardingContext';

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
import WorkAdvisor from './pages/WorkAdvisor';  // Replaces PlaybookBuilderPage
import AdminPage from './pages/AdminPage';
import AdminDashboard from './pages/AdminDashboard';
import DataModelPage from './pages/DataModelPage';
import ReferenceLibraryPage from './pages/ReferenceLibraryPage';
import BIBuilderPage from './pages/BIBuilderPage';

// CSS
import './index.css';

// Inner app with router hooks available
function AppRoutes() {
  return (
    <OnboardingProvider>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<LoginPage />} />
        
        {/* ====== MAIN NAV ====== */}
        
        {/* Dashboard */}
        <Route path="/dashboard" element={
          <ProtectedRoute><Layout><DashboardPage /></Layout></ProtectedRoute>
        } />
        
        {/* Projects */}
        <Route path="/projects" element={
          <ProtectedRoute><Layout><ProjectsPage /></Layout></ProtectedRoute>
        } />
        <Route path="/projects/:id" element={
          <ProtectedRoute><Layout><ProjectsPage /></Layout></ProtectedRoute>
        } />
        
        {/* Data */}
        <Route path="/data" element={
          <ProtectedRoute><Layout><DataPage /></Layout></ProtectedRoute>
        } />
        
        {/* Vacuum (sub-pages of Data) */}
        <Route path="/vacuum" element={
          <ProtectedRoute><Layout><VacuumUploadPage /></Layout></ProtectedRoute>
        } />
        <Route path="/vacuum/explore/:jobId" element={
          <ProtectedRoute><Layout><VacuumExplore /></Layout></ProtectedRoute>
        } />
        <Route path="/vacuum/mapping/:jobId" element={
          <ProtectedRoute><Layout><VacuumColumnMapping /></Layout></ProtectedRoute>
        } />
        
        {/* Reference Library (was Standards) */}
        <Route path="/reference-library" element={
          <ProtectedRoute><Layout><ReferenceLibraryPage /></Layout></ProtectedRoute>
        } />
        
        {/* Playbooks */}
        <Route path="/playbooks" element={
          <ProtectedRoute><Layout><PlaybooksPage /></Layout></ProtectedRoute>
        } />
        
        {/* Work Advisor - Conversational guide to features/playbooks */}
        <Route path="/advisor" element={
          <ProtectedRoute><Layout><WorkAdvisor /></Layout></ProtectedRoute>
        } />
        
        {/* Workspace (Chat) */}
        <Route path="/workspace" element={
          <ProtectedRoute><Layout><WorkspacePage /></Layout></ProtectedRoute>
        } />
        
        {/* Analytics (BI Builder) */}
        <Route path="/analytics" element={
          <ProtectedRoute><Layout><BIBuilderPage /></Layout></ProtectedRoute>
        } />
        
        {/* ====== ADMIN NAV ====== */}
        
        {/* Admin (includes System tab now) */}
        <Route path="/admin" element={
          <ProtectedRoute><Layout><AdminPage /></Layout></ProtectedRoute>
        } />
        
        {/* Learning Admin */}
        <Route path="/learning-admin" element={
          <ProtectedRoute><Layout><AdminDashboard /></Layout></ProtectedRoute>
        } />
        
        {/* ====== UTILITY ROUTES ====== */}
        
        {/* Data Model */}
        <Route path="/data-model" element={
          <ProtectedRoute><Layout><DataModelPage /></Layout></ProtectedRoute>
        } />
        
        {/* ====== LEGACY REDIRECTS ====== */}
        
        <Route path="/standards" element={<Navigate to="/reference-library" replace />} />
        <Route path="/chat" element={<Navigate to="/workspace" replace />} />
        <Route path="/upload" element={<Navigate to="/data" replace />} />
        <Route path="/status" element={<Navigate to="/admin" replace />} />
        <Route path="/system" element={<Navigate to="/admin" replace />} />
        <Route path="/secure20" element={<Navigate to="/playbooks" replace />} />
        <Route path="/packs" element={<Navigate to="/playbooks" replace />} />
        <Route path="/playbooks/builder" element={<Navigate to="/advisor" replace />} />
        
        {/* 404 fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </OnboardingProvider>
  );
}

function App() {
  return (
    <AuthProvider>
      <ProjectProvider>
        <ThemeProvider>
          <UploadProvider>
            <Router>
              <AppRoutes />
            </Router>
          </UploadProvider>
        </ThemeProvider>
      </ProjectProvider>
    </AuthProvider>
  );
}

export default App;
