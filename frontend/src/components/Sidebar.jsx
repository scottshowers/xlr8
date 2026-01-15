import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './Sidebar.css';

/**
 * Collapsible Sidebar Component
 * 
 * Fixed left side navigation (260px wide, collapsible to 0px)
 * Sections: Navigation, Recent Projects, System
 */

export const Sidebar = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

  const toggleSidebar = () => setIsCollapsed(!isCollapsed);

  return (
    <>
      <aside className={`xlr8-sidebar ${isCollapsed ? 'xlr8-sidebar--collapsed' : ''}`}>
        {/* Navigation Section */}
        <div className="xlr8-sidebar__section">
          <div className="xlr8-sidebar__section-title">Navigation</div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/mission-control') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/mission-control')}
          >
            <span className="xlr8-sidebar__icon">🚀</span>
            <span className="xlr8-sidebar__label">Mission Control</span>
            <span className="xlr8-sidebar__badge">23</span>
          </div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/projects') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/projects')}
          >
            <span className="xlr8-sidebar__icon">📁</span>
            <span className="xlr8-sidebar__label">Projects</span>
          </div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/analytics') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/analytics')}
          >
            <span className="xlr8-sidebar__icon">📊</span>
            <span className="xlr8-sidebar__label">Analytics</span>
          </div>
        </div>

        {/* Recent Projects Section */}
        <div className="xlr8-sidebar__section">
          <div className="xlr8-sidebar__section-title">Recent Projects</div>
          
          <div 
            className="xlr8-sidebar__item"
            onClick={() => navigate('/projects/acme-corp')}
          >
            <span className="xlr8-sidebar__icon">🏢</span>
            <span className="xlr8-sidebar__label">Acme Corp</span>
            <span className="xlr8-sidebar__badge xlr8-sidebar__badge--critical">12</span>
          </div>
          
          <div 
            className="xlr8-sidebar__item"
            onClick={() => navigate('/projects/techstart-inc')}
          >
            <span className="xlr8-sidebar__icon">🏢</span>
            <span className="xlr8-sidebar__label">TechStart Inc</span>
            <span className="xlr8-sidebar__badge xlr8-sidebar__badge--info">6</span>
          </div>
          
          <div 
            className="xlr8-sidebar__item"
            onClick={() => navigate('/projects/global-retail')}
          >
            <span className="xlr8-sidebar__icon">🏢</span>
            <span className="xlr8-sidebar__label">Global Retail Co</span>
            <span className="xlr8-sidebar__badge xlr8-sidebar__badge--info">5</span>
          </div>
          
          <div 
            className="xlr8-sidebar__item"
            onClick={() => navigate('/projects/medtech-sol')}
          >
            <span className="xlr8-sidebar__icon">🏢</span>
            <span className="xlr8-sidebar__label">MedTech Solutions</span>
          </div>
          
          <div 
            className="xlr8-sidebar__item"
            onClick={() => navigate('/projects/finserve')}
          >
            <span className="xlr8-sidebar__icon">🏢</span>
            <span className="xlr8-sidebar__label">FinServe Partners</span>
          </div>
        </div>

        {/* System Section */}
        <div className="xlr8-sidebar__section">
          <div className="xlr8-sidebar__section-title">System</div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/admin') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/admin')}
          >
            <span className="xlr8-sidebar__icon">⚙️</span>
            <span className="xlr8-sidebar__label">Platform Health</span>
          </div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/admin/playbook-builder') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/admin/playbook-builder')}
          >
            <span className="xlr8-sidebar__icon">📚</span>
            <span className="xlr8-sidebar__label">Playbook Builder</span>
          </div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/standards') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/standards')}
          >
            <span className="xlr8-sidebar__icon">🗄️</span>
            <span className="xlr8-sidebar__label">Standards Library</span>
          </div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/admin/api-connections') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/admin/api-connections')}
          >
            <span className="xlr8-sidebar__icon">🔌</span>
            <span className="xlr8-sidebar__label">API Connections</span>
          </div>
          
          <div 
            className={`xlr8-sidebar__item ${isActive('/admin/schemas') ? 'xlr8-sidebar__item--active' : ''}`}
            onClick={() => navigate('/admin/schemas')}
          >
            <span className="xlr8-sidebar__icon">🧬</span>
            <span className="xlr8-sidebar__label">Schema Viewer</span>
          </div>
        </div>
      </aside>

      {/* Toggle Button */}
      <button 
        className="xlr8-sidebar-toggle"
        onClick={toggleSidebar}
        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        <span className="xlr8-sidebar-toggle__icon">
          {isCollapsed ? '▶' : '◀'}
        </span>
      </button>
    </>
  );
};

export default Sidebar;
