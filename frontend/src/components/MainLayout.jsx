import React from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import FlowBar from './FlowBar';
import './MainLayout.css';

/**
 * MainLayout Component
 * 
 * NEW layout system using Phase 4A design components
 * - Header: Fixed at top (64px) with H logo, search, actions
 * - Sidebar: Collapsible navigation (260px → 0px)
 * - FlowBar: Contextual 7-step indicator (conditional)
 * - Main: Content area with dynamic margins
 * 
 * Usage:
 * <MainLayout showFlowBar={false}>
 *   <YourPageContent />
 * </MainLayout>
 */

export const MainLayout = ({ 
  children, 
  showFlowBar = false,
  currentStep = 1,
  projectId = null,
  className = ''
}) => {
  return (
    <div className="xlr8-main-layout">
      <Header />
      
      <Sidebar />
      
      {showFlowBar && (
        <FlowBar 
          currentStep={currentStep} 
          projectId={projectId}
        />
      )}
      
      <main className={`xlr8-main-layout__content ${showFlowBar ? 'xlr8-main-layout__content--with-flow' : ''} ${className}`}>
        {children}
      </main>
    </div>
  );
};

export default MainLayout;
