/**
 * App.jsx - Main Application Entry
 * 
 * ALL routes now use MainLayout (unified sidebar + header).
 * showFlowBar=true for 8-step workflow pages.
 * 
 * Phase 4A UX Overhaul - January 15, 2026
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

// Auth & Layout
import ProtectedRoute from './components/ProtectedRoute';
import MainLayout from './components/MainLayout';

// Pages
import Landing from './pages/Landing';
import LoginPage from './pages/LoginPage';
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

// Helper wrapper - MainLayout with no flow bar
const Page = ({ children }) => (
  <MainLayout>{children}</MainLayout>
);

// Helper wrapper - MainLayout with flow bar
const FlowPage = ({ children, step }) => (
  <MainLayout showFlowBar currentStep={step}>{children}</MainLayout>
);

function AppRoutes() {
  return (
    <OnboardingProvider>
      <Routes>
        {/* ====== PUBLIC ROUTES ====== */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<LoginPage />} />
        
        {/* ====== SALES / ONBOARDING (No layout) ====== */}
        <Route path="/welcome" element={<WelcomePage />} />
        <Route path="/story" element={<StoryPage />} />
        <Route path="/journey" element={<JourneyPage />} />
        <Route path="/hype" element={<HypeVideo />} />
        <Route path="/architecture" element={<ArchitecturePage />} />
        <Route path="/architecture/metrics-pipeline" element={<MetricsPipelinePage />} />
        
        {/* ====== MISSION CONTROL (Hub - no flow bar) ====== */}
        <Route path="/mission-control" element={
          <ProtectedRoute><Page><MissionControl /></Page></ProtectedRoute>
        } />
        <Route path="/dashboard" element={
          <ProtectedRoute><Page><MissionControl /></Page></ProtectedRoute>
        } />
        
        {/* ====== 8-STEP WORKFLOW (with flow bar) ====== */}
        
        {/* Step 1: Create Project */}
        <Route path="/projects/new" element={
          <ProtectedRoute><FlowPage step={1}><CreateProjectPage /></FlowPage></ProtectedRoute>
        } />
        
        {/* Step 2: Upload Data */}
        <Route path="/upload" element={
          <ProtectedRoute><FlowPage step={2}><UploadDataPage /></FlowPage></ProtectedRoute>
        } />
        
        {/* Step 3: Select Playbooks */}
        <Route path="/playbooks/select" element={
          <ProtectedRoute><FlowPage step={3}><PlaybookSelectPage /></FlowPage></ProtectedRoute>
        } />
        
        {/* Step 4: Analysis/Processing */}
        <Route path="/processing" element={
          <ProtectedRoute><FlowPage step={4}><ProcessingPage /></FlowPage></ProtectedRoute>
        } />
        <Route path="/processing/:jobId" element={
          <ProtectedRoute><FlowPage step={4}><ProcessingPage /></FlowPage></ProtectedRoute>
        } />
        
        {/* Step 5: Findings Dashboard */}
        <Route path="/findings" element={
          <ProtectedRoute><FlowPage step={5}><FindingsDashboard /></FlowPage></ProtectedRoute>
        } />
        
        {/* Step 6: Drill-In (Finding Detail) */}
        <Route path="/findings/:findingId" element={
          <ProtectedRoute><FlowPage step={6}><FindingDetailPage /></FlowPage></ProtectedRoute>
        } />
        
        {/* Step 7: Track Progress */}
        <Route path="/progress/:playbookId" element={
          <ProtectedRoute><FlowPage step={7}><ProgressTrackerPage /></FlowPage></ProtectedRoute>
        } />
        
        {/* Step 8: Export */}
        <Route path="/export" element={
          <ProtectedRoute><FlowPage step={8}><ExportPage /></FlowPage></ProtectedRoute>
        } />
        
        {/* ====== OTHER PAGES (no flow bar) ====== */}
        
        {/* Projects List */}
        <Route path="/projects" element={
          <ProtectedRoute><Page><ProjectsPage /></Page></ProtectedRoute>
        } />
        <Route path="/projects/:id" element={
          <ProtectedRoute><Page><ProjectsPage /></Page></ProtectedRoute>
        } />
        
        {/* Data Pages */}
        <Route path="/data" element={
          <ProtectedRoute><Page><DataPage /></Page></ProtectedRoute>
        } />
        <Route path="/data/explorer" element={
          <ProtectedRoute><Page><DataExplorer /></Page></ProtectedRoute>
        } />
        <Route path="/data/model" element={
          <ProtectedRoute><Page><DataModelPage /></Page></ProtectedRoute>
        } />
        
        {/* Vacuum Pages */}
        <Route path="/vacuum" element={
          <ProtectedRoute><Page><VacuumUploadPage /></Page></ProtectedRoute>
        } />
        <Route path="/vacuum/explore/:jobId" element={
          <ProtectedRoute><Page><VacuumExplore /></Page></ProtectedRoute>
        } />
        <Route path="/vacuum/mapping/:jobId" element={
          <ProtectedRoute><Page><VacuumColumnMapping /></Page></ProtectedRoute>
        } />
        
        {/* Playbooks */}
        <Route path="/playbooks" element={
          <ProtectedRoute><Page><PlaybooksPage /></Page></ProtectedRoute>
        } />
        <Route path="/build-playbook" element={
          <ProtectedRoute><Page><PlaybookWireupPage /></Page></ProtectedRoute>
        } />
        
        {/* Workspace (Chat) */}
        <Route path="/workspace" element={
          <ProtectedRoute><Page><WorkspacePage /></Page></ProtectedRoute>
        } />
        
        {/* Analytics */}
        <Route path="/analytics" element={
          <ProtectedRoute><Page><AnalyticsPage /></Page></ProtectedRoute>
        } />
        
        {/* Reference Library */}
        <Route path="/reference-library" element={
          <ProtectedRoute><Page><ReferenceLibraryPage /></Page></ProtectedRoute>
        } />
        
        {/* Standards */}
        <Route path="/standards" element={
          <ProtectedRoute><Page><StandardsPage /></Page></ProtectedRoute>
        } />
        
        {/* Data Health */}
        <Route path="/data-health" element={
          <ProtectedRoute><Page><DataHealthPage /></Page></ProtectedRoute>
        } />
        
        {/* ====== ADMIN PAGES (no flow bar) ====== */}
        
        <Route path="/admin" element={
          <ProtectedRoute><Page><AdminHub /></Page></ProtectedRoute>
        } />
        <Route path="/admin/settings" element={
          <ProtectedRoute><Page><AdminPage /></Page></ProtectedRoute>
        } />
        <Route path="/admin/data-cleanup" element={
          <ProtectedRoute><Page><DataCleanup /></Page></ProtectedRoute>
        } />
        <Route path="/admin/endpoints" element={
          <ProtectedRoute><Page><AdminEndpoints /></Page></ProtectedRoute>
        } />
        <Route path="/admin/intelligence-test" element={
          <ProtectedRoute><Page><IntelligenceTestPage /></Page></ProtectedRoute>
        } />
        <Route path="/admin/playbook-builder" element={
          <ProtectedRoute><Page><PlaybookBuilderPage /></Page></ProtectedRoute>
        } />
        <Route path="/learning-admin" element={
          <ProtectedRoute><Page><AdminDashboard /></Page></ProtectedRoute>
        } />
        
        {/* ====== LEGACY REDIRECTS ====== */}
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
