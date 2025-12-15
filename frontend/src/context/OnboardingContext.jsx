/**
 * OnboardingContext.jsx - React Joyride Implementation
 * 
 * INSTALLATION: npm install react-joyride
 * 
 * Tours auto-trigger on first visit to each page (when enabled).
 * Completion tracked in localStorage.
 * Master toggle to enable/disable all tours.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import Joyride, { STATUS, EVENTS } from 'react-joyride';
import { useLocation } from 'react-router-dom';

// Light theme styling
const joyrideStyles = {
  options: {
    primaryColor: '#83b16d',
    backgroundColor: '#ffffff',
    textColor: '#2a3441',
    arrowColor: '#ffffff',
    overlayColor: 'rgba(42, 52, 65, 0.5)',
    zIndex: 10000,
    width: 380,
  },
  tooltip: {
    borderRadius: 12,
    boxShadow: '0 4px 20px rgba(42, 52, 65, 0.15)',
    padding: '1.25rem',
  },
  tooltipContainer: { textAlign: 'left' },
  tooltipTitle: { fontSize: '1.1rem', fontWeight: 700, color: '#2a3441', marginBottom: '0.5rem' },
  tooltipContent: { fontSize: '0.9rem', lineHeight: 1.6, color: '#5f6c7b' },
  buttonNext: { backgroundColor: '#83b16d', fontSize: '0.85rem', fontWeight: 600, padding: '0.6rem 1.25rem', borderRadius: 8 },
  buttonBack: { color: '#5f6c7b', fontSize: '0.85rem', marginRight: '0.5rem' },
  buttonSkip: { color: '#9ca3af', fontSize: '0.8rem' },
  spotlight: { borderRadius: 8 },
  beacon: { display: 'none' },
};

const locale = { back: 'Back', close: 'Close', last: 'Got it!', next: 'Next', skip: 'Skip tour' };

// Helper
const step = (target, title, content, options = {}) => ({
  target: `[data-tour="${target}"]`,
  title,
  content,
  disableBeacon: true,
  ...options,
});

// TOUR DEFINITIONS
export const dashboardTour = [
  { target: 'body', title: '👋 Welcome to XLR8!', content: 'Your implementation analysis platform. This quick tour shows you around.', placement: 'center', disableBeacon: true },
  step('nav-projects', '📁 Projects', 'Each customer engagement gets its own project. Start here to create or select one.'),
  step('nav-data', '📤 Data', 'Upload customer data - Excel, PDF, CSV. We extract and analyze it automatically.'),
  step('nav-referencelibrary', '📚 Reference Library', 'Compliance standards and best practices. Upload docs here to check data against.'),
  step('nav-playbooks', '📋 Playbooks', 'Run analysis playbooks to generate findings and insights from your data.'),
  step('nav-workspace', '💬 Workspace', 'Chat with AI to explore data, ask questions, and generate reports.'),
  step('dashboard-stats', '📊 Command Center', 'Your at-a-glance view of active projects, running playbooks, and pending findings.'),
  step('dashboard-projects', '🏢 Active Engagements', 'Quick access to your projects. Click any card to dive into that engagement.'),
  step('dashboard-actions', '⚡ Quick Actions', 'Keyboard shortcuts for power users.'),
  step('theme-toggle', '🌓 Theme Toggle', 'Switch between light and dark mode.'),
];

export const projectsTour = [
  step('projects-header', '📁 Project Management', 'All your customer engagements in one place.'),
  step('projects-create', '➕ Create Project', 'Start a new engagement with customer name and project type.'),
  step('projects-search', '🔍 Search & Filter', 'Find projects quickly by name or status.'),
  step('projects-list', '📋 Project Cards', 'Click any project to select it as your working context.'),
];

export const dataTour = [
  step('data-header', '📤 Data Management', 'This is where you get customer data into XLR8.'),
  step('data-tab-upload', '📁 Upload Tab', 'Drag and drop files or click to browse. Uploads continue in the background.'),
  step('data-tab-vacuum', '✨ Vacuum Tab', 'Deep extraction for complex documents with intelligent table detection.'),
  step('data-tab-jobs', '📋 Jobs Tab', 'Track processing status and manage uploaded files.'),
  step('data-project-context', '🎯 Project Context', 'Files upload to the currently selected project.'),
];

export const vacuumTour = [
  step('vacuum-header', '✨ Vacuum Extract', 'Deep extraction for complex documents.'),
  step('vacuum-upload', '📤 Upload Area', 'Drop your file here for analysis.'),
  step('vacuum-preview', '👁 Data Preview', 'See extracted tables and columns.'),
  step('vacuum-mapping', '🏷 Column Mapping', 'Map columns to semantic types.'),
  step('vacuum-confirm', '✅ Confirm & Load', 'Review and load the data.'),
];

export const playbooksTour = [
  step('playbooks-header', '📋 Analysis Playbooks', 'Pre-built analysis patterns that check your data.'),
  step('playbooks-categories', '📂 Categories', 'Playbooks organized by domain.'),
  step('playbooks-card', '🎯 Playbook Card', 'Shows what it checks and estimated run time.'),
  step('playbooks-run', '▶️ Run Playbook', 'Click to run against your project data.'),
  step('playbooks-results', '📊 Results', 'Findings appear with severity and recommendations.'),
  step('playbooks-export', '📥 Export', 'Download findings as Excel or PDF.'),
];

export const workspaceTour = [
  step('workspace-header', '💬 AI Workspace', 'Chat with XLR8 AI to explore your data.'),
  step('workspace-personas', '🎭 Personas', 'Switch AI personalities for different tasks.'),
  step('workspace-chat-input', '⌨️ Chat Input', 'Ask questions in natural language.'),
  step('workspace-context', '🎯 Project Context', 'AI knows about your selected project.'),
  step('workspace-history', '📜 Chat History', 'Previous conversations are saved.'),
];

export const referenceLibraryTour = [
  step('reference-header', '📚 Reference Library', 'Compliance standards and rules.'),
  step('reference-documents', '📄 Documents Tab', 'View uploaded compliance documents.'),
  step('reference-upload', '📤 Upload Tab', 'Add new compliance docs.'),
  step('reference-rules', '📋 Rules Tab', 'Browse extracted rules.'),
  step('reference-compliance', '🔍 Compliance Check', 'Run rules against project data.'),
];

export const adminTour = [
  step('admin-header', '⚙️ Admin Settings', 'System configuration and management.'),
  step('admin-tab-system', '📊 System', 'Live system health and data flow visualization.'),
  step('admin-tab-users', '👥 Users', 'Manage team members and permissions.'),
  step('admin-tab-integrations', '🔌 Integrations', 'Configure UKG API connections.'),
];

export const systemMonitorTour = [
  step('ops-header', '📊 Operations Center', 'Real-time system health and metrics.'),
  step('ops-tab-overview', '◉ Overview', 'Data flow visualization.'),
  step('ops-tab-security', '🛡️ Security', 'Threat detection and compliance.'),
  step('ops-tab-performance', '⚡ Performance', 'Response times and load.'),
  step('ops-tab-costs', '💰 Costs', 'API usage and budget.'),
  step('ops-tab-data', '🗄️ Data Stores', 'DuckDB, Supabase, ChromaDB contents.'),
];

// Tour Registry
const tourRegistry = {
  '/dashboard': { id: 'dashboard', steps: dashboardTour },
  '/projects': { id: 'projects', steps: projectsTour },
  '/data': { id: 'data', steps: dataTour },
  '/vacuum': { id: 'vacuum', steps: vacuumTour },
  '/playbooks': { id: 'playbooks', steps: playbooksTour },
  '/workspace': { id: 'workspace', steps: workspaceTour },
  '/reference-library': { id: 'reference-library', steps: referenceLibraryTour },
  '/admin': { id: 'admin', steps: adminTour },
  '/system': { id: 'system-monitor', steps: systemMonitorTour },
};

const OnboardingContext = createContext(null);

export function useOnboarding() {
  const context = useContext(OnboardingContext);
  if (!context) throw new Error('useOnboarding must be used within OnboardingProvider');
  return context;
}

export function OnboardingProvider({ children }) {
  const location = useLocation();
  const [runTour, setRunTour] = useState(false);
  const [currentSteps, setCurrentSteps] = useState([]);
  const [stepIndex, setStepIndex] = useState(0);

  // Master toggle for tours (persisted)
  const [tourEnabled, setTourEnabledState] = useState(() => {
    try {
      const saved = localStorage.getItem('xlr8-tour-enabled');
      return saved !== null ? JSON.parse(saved) : false; // Default OFF
    } catch { return false; }
  });

  const setTourEnabled = useCallback((enabled) => {
    setTourEnabledState(enabled);
    localStorage.setItem('xlr8-tour-enabled', JSON.stringify(enabled));
  }, []);

  const [completedTours, setCompletedTours] = useState(() => {
    try {
      const saved = localStorage.getItem('xlr8-completed-tours');
      return saved ? JSON.parse(saved) : {};
    } catch { return {}; }
  });

  useEffect(() => {
    localStorage.setItem('xlr8-completed-tours', JSON.stringify(completedTours));
  }, [completedTours]);

  // Auto-trigger tours only when enabled
  useEffect(() => {
    if (!tourEnabled) return; // Don't auto-trigger if disabled
    
    const path = location.pathname;
    const tourConfig = tourRegistry[path];
    if (tourConfig && tourConfig.steps.length > 0 && !completedTours[tourConfig.id]) {
      const timer = setTimeout(() => {
        setCurrentSteps(tourConfig.steps);
        setStepIndex(0);
        setRunTour(true);
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [location.pathname, completedTours, tourEnabled]);

  const handleJoyrideCallback = useCallback((data) => {
    const { status, index, type } = data;
    if (type === EVENTS.STEP_AFTER) setStepIndex(index + 1);
    if ([STATUS.FINISHED, STATUS.SKIPPED].includes(status)) {
      setRunTour(false);
      const path = location.pathname;
      const tourConfig = tourRegistry[path];
      if (tourConfig) setCompletedTours(prev => ({ ...prev, [tourConfig.id]: true }));
    }
  }, [location.pathname]);

  const startTour = useCallback((tourId) => {
    const entry = Object.entries(tourRegistry).find(([_, config]) => config.id === tourId);
    if (entry && entry[1].steps.length > 0) {
      setCurrentSteps(entry[1].steps);
      setStepIndex(0);
      setRunTour(true);
    }
  }, []);

  const startCurrentPageTour = useCallback(() => {
    const tourConfig = tourRegistry[location.pathname];
    if (tourConfig && tourConfig.steps.length > 0) {
      setCurrentSteps(tourConfig.steps);
      setStepIndex(0);
      setRunTour(true);
    }
  }, [location.pathname]);

  const resetAllTours = useCallback(() => {
    setCompletedTours({});
    localStorage.removeItem('xlr8-completed-tours');
  }, []);

  const resetTour = useCallback((tourId) => {
    setCompletedTours(prev => { const next = { ...prev }; delete next[tourId]; return next; });
  }, []);

  const value = {
    runTour,
    tourEnabled,
    setTourEnabled,
    completedTours,
    startTour,
    startCurrentPageTour,
    resetAllTours,
    resetTour,
    availableTours: Object.entries(tourRegistry).map(([path, config]) => ({
      id: config.id, path, stepCount: config.steps.length, completed: !!completedTours[config.id],
    })),
  };

  return (
    <OnboardingContext.Provider value={value}>
      <Joyride
        steps={currentSteps}
        run={runTour}
        stepIndex={stepIndex}
        continuous
        showProgress
        showSkipButton
        scrollToFirstStep
        disableOverlayClose
        callback={handleJoyrideCallback}
        styles={joyrideStyles}
        locale={locale}
      />
      {children}
    </OnboardingContext.Provider>
  );
}

export function RestartTourButton({ style }) {
  const { startCurrentPageTour, completedTours } = useOnboarding();
  const location = useLocation();
  const tourConfig = tourRegistry[location.pathname];
  if (!tourConfig || tourConfig.steps.length === 0) return null;

  return (
    <button
      onClick={startCurrentPageTour}
      style={{
        display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem',
        background: 'white', border: '1px solid #e1e8ed', borderRadius: '8px',
        color: '#5f6c7b', fontSize: '0.85rem', cursor: 'pointer', ...style,
      }}
    >
      🎓 {completedTours[tourConfig.id] ? 'Replay Tour' : 'Start Tour'}
    </button>
  );
}

export function TourStatusPanel() {
  const { availableTours, resetTour, resetAllTours } = useOnboarding();
  return (
    <div style={{ padding: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Onboarding Tours</h3>
        <button onClick={resetAllTours} style={{ background: 'none', border: '1px solid #e1e8ed', borderRadius: '6px', padding: '0.4rem 0.8rem', fontSize: '0.8rem', color: '#5f6c7b', cursor: 'pointer' }}>
          Reset All
        </button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {availableTours.filter(t => t.stepCount > 0).map(tour => (
          <div key={tour.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: '#f8fafc', borderRadius: '8px' }}>
            <div>
              <div style={{ fontWeight: 500, textTransform: 'capitalize' }}>{tour.id.replace('-', ' ')}</div>
              <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>{tour.stepCount} steps • {tour.path}</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {tour.completed ? <span style={{ color: '#10b981', fontSize: '0.8rem' }}>✓ Complete</span> : <span style={{ color: '#f59e0b', fontSize: '0.8rem' }}>Not started</span>}
              {tour.completed && <button onClick={() => resetTour(tour.id)} style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '0.8rem' }}>Reset</button>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default OnboardingProvider;
