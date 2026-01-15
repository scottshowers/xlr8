/**
 * App.jsx - Main Application Entry
 * 
 * NAV STRUCTURE:
 * Main: Mission Control | Projects | Data | Reference Library | Playbooks | Workspace
 * Admin: Admin | Learning (System moved to Admin tab)
 * 
 * PROVIDERS:
 * - AuthProvider
 * - ProjectProvider  
 * - ThemeProvider (consistent dark/light)
 * - UploadProvider (background uploads)
 * - OnboardingProvider (Joyride tours)
 * - TooltipProvider (global tooltip toggle)
 * 
 * Updated: January 15, 2026 - Added Mission Control (Phase 4A UX Overhaul)
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Context Providers
import { ProjectProvider } from './context/ProjectContext';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { UploadProvider } from './context/UploadContext';
import { OnboardingProvider } from './context/OnboardingContext';
import { TooltipProvider } from './context/TooltipContext';

// Auth Components
import ProtectedRoute from './components/ProtectedRoute';

// Layout
import Layout from './components/Layout';

// Pages
import Landing from './pages/Landing';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import MissionControl from './pages/MissionControl';
import WorkspacePage from './pages/WorkspacePage';
import ProjectsPage from './pages/ProjectsPage';
import CreateProjectPage from './pages/CreateProjectPage';
import DataPage from './pages/DataPage';
import DataExplorer from './pages/DataExplorer';
import DataModelPage from './pages/DataModelPage';
import VacuumUploadPage from './pages/VacuumUploadPage';
import UploadDataPage from './pages/UploadDataPage';
import VacuumExplore from './pages/VacuumExplore';
import VacuumColumnMapping from './pages/VacuumColumnMapping';
import PlaybooksPage from './pages/PlaybooksPage';
import PlaybookSelectPage from './pages/PlaybookSelectPage';
import PlaybookBuilderPage from './pages/PlaybookBuilderPage';
import PlaybookWireupPage from './pages/PlaybookWireupPage';
import ProgressTrackerPage from './pages/ProgressTrackerPage';
import ExportPage from './pages/ExportPage';
import ProcessingPage from './pages/ProcessingPage';
import FindingsDashboard from './pages/FindingsDashboard';
import FindingDetailPage from './pages/FindingDetailPage';
import StandardsPage from './pages/StandardsPage';
import AdminPage from './pages/AdminPage';
import AdminHub from './pages/AdminHub';
import AdminDashboard from './pages/AdminDashboard';
import DataHealthPage from './pages/DataHealthPage';
import ReferenceLibraryPage from './pages/ReferenceLibraryPage';
import AnalyticsPage from './pages/AnalyticsPage';
import DataCleanup from './pages/DataCleanup';
import AdminEndpoints from './pages/AdminEndpoints';
import IntelligenceTestPage from './pages/IntelligenceTestPage';

// Sales/Onboarding Pages
import WelcomePage from './pages/WelcomePage';
import StoryPage from './pages/StoryPage';
import JourneyPage from './pages/JourneyPage';
import HypeVideo from './pages/HypeVideo';
import ArchitecturePage from './pages/ArchitecturePage';
import MetricsPipelinePage from './pages/MetricsPipelinePage';

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
        
        {/* ====== SALES / ONBOARDING PAGES ====== */}
        
        {/* Welcome - Sales landing with 3 presentation options */}
        <Route path="/welcome" element={<WelcomePage />} />
        
        {/* Story - Narrative chapter experience */}
        <Route path="/story" element={<StoryPage />} />
        
        {/* Journey - Visual infographic */}
        <Route path="/journey" element={<JourneyPage />} />
        
        {/* Intelligence Demo - Watch XLR8 Think */}
        
        {/* Hype Video */}
        <Route path="/hype" element={<HypeVideo />} />
        
        {/* Architecture - Level 5 DFD */}
        <Route path="/architecture" element={<ArchitecturePage />} />
        
        {/* Metrics Pipeline - Data flow explainer */}
        <Route path="/architecture/metrics-pipeline" element={<MetricsPipelinePage />} />
        
        {/* ====== MAIN NAV ====== */}
        
        {/* Mission Control - Cross-project review queue */}
        <Route path="/mission-control" element={
          <ProtectedRoute><MissionControl /></ProtectedRoute>
        } />
        
        {/* Dashboard - Points to Mission Control */}
        <Route path="/dashboard" element={
          <ProtectedRoute><MissionControl /></ProtectedRoute>
        } />
        
        {/* Projects */}
        <Route path="/projects" element={
          <ProtectedRoute><Layout><ProjectsPage /></Layout></ProtectedRoute>
        } />
        <Route path="/projects/new" element={
          <ProtectedRoute><Layout><CreateProjectPage /></Layout></ProtectedRoute>
        } />
        <Route path="/projects/:id" element={
          <ProtectedRoute><Layout><ProjectsPage /></Layout></ProtectedRoute>
        } />
        
        {/* Data */}
        <Route path="/data" element={
          <ProtectedRoute><Layout><DataPage /></Layout></ProtectedRoute>
        } />
        <Route path="/data/explorer" element={
          <ProtectedRoute><Layout><DataExplorer /></Layout></ProtectedRoute>
        } />
        <Route path="/data/model" element={
          <ProtectedRoute><Layout><DataModelPage /></Layout></ProtectedRoute>
        } />
        
        {/* Upload Data - Phase 4A Screen 2 */}
        <Route path="/upload" element={
          <ProtectedRoute><Layout><UploadDataPage /></Layout></ProtectedRoute>
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

        {/* Processing Feedback - Phase 4A.3 */}
        <Route path="/processing" element={
          <ProtectedRoute><Layout><ProcessingPage /></Layout></ProtectedRoute>
        } />
        <Route path="/processing/:jobId" element={
          <ProtectedRoute><Layout><ProcessingPage /></Layout></ProtectedRoute>
        } />

        {/* Reference Library (was Standards) */}
        <Route path="/reference-library" element={
          <ProtectedRoute><Layout><ReferenceLibraryPage /></Layout></ProtectedRoute>
        } />
        
        {/* Playbooks */}
        <Route path="/playbooks" element={
          <ProtectedRoute><Layout><PlaybooksPage /></Layout></ProtectedRoute>
        } />
        
        {/* Playbook Selection - Step 3 of Flow */}
        <Route path="/playbooks/select" element={
          <ProtectedRoute><PlaybookSelectPage /></ProtectedRoute>
        } />
        
        {/* Build Playbook - Phase 4A.6 */}
        <Route path="/build-playbook" element={
          <ProtectedRoute><Layout><PlaybookWireupPage /></Layout></ProtectedRoute>
        } />
        
        {/* Progress Tracker - Phase 4A.7 */}
        <Route path="/progress/:playbookId" element={
          <ProtectedRoute><ProgressTrackerPage /></ProtectedRoute>
        } />
        
        {/* Export - Step 8 of Flow */}
        <Route path="/export" element={
          <ProtectedRoute><ExportPage /></ProtectedRoute>
        } />
        
        {/* Findings Dashboard - Phase 4A.4 */}
        <Route path="/findings" element={
          <ProtectedRoute><Layout><FindingsDashboard /></Layout></ProtectedRoute>
        } />

        {/* Finding Detail - Phase 4A.5 */}
        <Route path="/findings/:findingId" element={
          <ProtectedRoute><Layout><FindingDetailPage /></Layout></ProtectedRoute>
        } />

        {/* Workspace (Chat) */}
        <Route path="/workspace" element={
          <ProtectedRoute><Layout><WorkspacePage /></Layout></ProtectedRoute>
        } />
        
        {/* Analytics Explorer - 3-way mode: Natural Language, Visual Builder, SQL */}
        <Route path="/analytics" element={
          <ProtectedRoute><Layout><AnalyticsPage /></Layout></ProtectedRoute>
        } />
        
        {/* ====== ADMIN NAV ====== */}
        
        {/* Admin Hub - Card navigation */}
        <Route path="/admin" element={
          <ProtectedRoute><Layout><AdminHub /></Layout></ProtectedRoute>
        } />
        
        {/* Admin Settings - Tabbed interface */}
        <Route path="/admin/settings" element={
          <ProtectedRoute><Layout><AdminPage /></Layout></ProtectedRoute>
        } />
        
        {/* Learning Admin */}
        <Route path="/learning-admin" element={
          <ProtectedRoute><Layout><AdminDashboard /></Layout></ProtectedRoute>
        } />
        
        {/* Data Cleanup - Admin tool for mass delete */}
        <Route path="/admin/data-cleanup" element={
          <ProtectedRoute><Layout><DataCleanup /></Layout></ProtectedRoute>
        } />
        
        {/* Admin Endpoints - API testing */}
        <Route path="/admin/endpoints" element={
          <ProtectedRoute><Layout><AdminEndpoints /></Layout></ProtectedRoute>
        } />
        
        {/* Intelligence Test - Pipeline testing */}
        <Route path="/admin/intelligence-test" element={
          <ProtectedRoute><Layout><IntelligenceTestPage /></Layout></ProtectedRoute>
        } />
        
        {/* Playbook Builder - Create/Edit Playbooks */}
        <Route path="/admin/playbook-builder" element={
          <ProtectedRoute><Layout><PlaybookBuilderPage /></Layout></ProtectedRoute>
        } />
        
        {/* Standards - Compliance document management */}
        <Route path="/standards" element={
          <ProtectedRoute><Layout><StandardsPage /></Layout></ProtectedRoute>
        } />
        
        {/* ====== UTILITY ROUTES ====== */}
        
        {/* Data Health (renamed from Data Model) */}
        <Route path="/data-health" element={
          <ProtectedRoute><Layout><DataHealthPage /></Layout></ProtectedRoute>
        } />
        
        {/* ====== LEGACY REDIRECTS ====== */}
        
        {/* Old admin tool paths redirect to new locations */}
        <Route path="/data-cleanup" element={<Navigate to="/admin/data-cleanup" replace />} />
        <Route path="/admin-endpoints" element={<Navigate to="/admin/endpoints" replace />} />
        
        <Route path="/data-model" element={<Navigate to="/data-health" replace />} />
        <Route path="/chat" element={<Navigate to="/workspace" replace />} />
        <Route path="/status" element={<Navigate to="/admin" replace />} />
        <Route path="/system" element={<Navigate to="/admin" replace />} />
        <Route path="/secure20" element={<Navigate to="/playbooks" replace />} />
        <Route path="/packs" element={<Navigate to="/playbooks" replace />} />
        <Route path="/playbooks/builder" element={<Navigate to="/admin/playbook-builder" replace />} />
        <Route path="/query-builder" element={<Navigate to="/analytics" replace />} />
        <Route path="/bi" element={<Navigate to="/analytics" replace />} />
        
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
          <TooltipProvider>
            <UploadProvider>
              <Router>
                <AppRoutes />
              </Router>
            </UploadProvider>
          </TooltipProvider>
        </ThemeProvider>
      </ProjectProvider>
    </AuthProvider>
  );
}

export default App;
