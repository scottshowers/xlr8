import React from 'react';
import './Header.css';

/**
 * Header Component
 * 
 * Top navigation bar with:
 * - XLR8 logo (proper H shape)
 * - Search bar (placeholder)
 * - Action icons (chat, notifications, settings)
 * - User menu
 */

export const Header = ({ user, onMenuClick }) => {
  return (
    <header className="xlr8-header">
      <div className="xlr8-header__logo" onClick={() => window.location.href = '/'}>
        {/* XLR8 H Logo SVG */}
        <div className="xlr8-header__logo-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 570">
            <path fill="#698f57" d="M492.04,500v-31.35l-36.53-35.01V163.76c0-15.8,.94-16.74,16.74-16.74h19.79v-31.36l-45.66-45.66H73v31.36l36.53,36.53V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35l45.66,45.66H492.04Z"/>
            <g fill="#a8ca99">
              <rect x="134.8" y="348.24" width="64.39" height="11.87"/>
              <rect x="134.8" y="324.95" width="64.39" height="11.87"/>
              <rect x="134.8" y="302.12" width="64.39" height="11.87"/>
              <rect x="134.8" y="279.29" width="64.39" height="11.87"/>
              <rect x="134.8" y="371.08" width="64.39" height="11.87"/>
              <rect x="134.8" y="393.91" width="64.39" height="11.87"/>
              <rect x="134.8" y="118.1" width="64.39" height="11.87"/>
              <rect x="134.8" y="164.22" width="64.39" height="11.87"/>
              <rect x="320.19" y="140.93" width="64.39" height="11.87"/>
              <rect x="134.8" y="256" width="64.39" height="11.87"/>
              <rect x="134.8" y="140.93" width="64.39" height="11.87"/>
              <rect x="134.8" y="233.17" width="64.39" height="11.87"/>
              <rect x="134.8" y="187.05" width="64.39" height="11.87"/>
              <rect x="134.8" y="210.34" width="64.39" height="11.87"/>
              <rect x="320.19" y="371.08" width="64.39" height="11.87"/>
              <rect x="320.19" y="324.95" width="64.39" height="11.87"/>
              <rect x="320.19" y="348.24" width="64.39" height="11.87"/>
              <rect x="320.19" y="279.29" width="64.39" height="11.87"/>
              <rect x="320.19" y="302.12" width="64.39" height="11.87"/>
              <rect x="320.19" y="393.91" width="64.39" height="11.87"/>
              <rect x="320.19" y="164.22" width="64.39" height="11.87"/>
              <rect x="320.19" y="118.1" width="64.39" height="11.87"/>
              <rect x="320.19" y="187.05" width="64.39" height="11.87"/>
              <rect x="320.19" y="210.34" width="64.39" height="11.87"/>
              <rect x="320.19" y="256" width="64.39" height="11.87"/>
              <rect x="320.19" y="233.17" width="64.39" height="11.87"/>
            </g>
            <path fill="#84b26d" d="M426.59,95.27h13.7v-19.18h-173.52v19.18h11.42c19.18,0,22.83,3.65,22.83,22.83V248.24h-82.65V118.1c0-19.18,3.65-22.83,22.83-22.83h11.42v-19.18H79.09v19.18h13.7c19.18,0,22.83,3.65,22.83,22.83V406.24c0,19.18-3.65,22.83-22.83,22.83h-13.7v19.18H252.61v-19.18h-11.42c-19.18,0-22.83-3.65-22.83-22.83v-138.82h82.65v138.82c0,19.18-3.65,22.83-22.83,22.83h-11.42v19.18h173.52v-19.18h-13.7c-19.18,0-22.83-3.65-22.83-22.83V118.1c0-19.18,3.65-22.83,22.83-22.83Z"/>
            <path fill="#9cc28a" d="M426.59,101.36h19.79v-31.36h-183.7v31.36h15.5c15.8,0,16.74,.94,16.74,16.74v124.05h-70.47V118.1c0-15.8,.94-16.74,16.74-16.74h15.5v-31.36H73v31.36h19.79c15.8,0,16.74,.94,16.74,16.74V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35h183.7v-31.35h-15.5c-15.8,0-16.74-.94-16.74-16.74v-132.73h70.47v132.73c0,15.8,.94,16.74-16.74,16.74h-15.5v31.35h183.7v-31.35h-19.79c-15.8,0-16.74-.94-16.74-16.74V118.1c0-15.8,.94-16.74,16.74-16.74Z"/>
          </svg>
        </div>
        <div className="xlr8-header__brand">
          <div className="xlr8-header__brand-name">
            XLR8 <span className="xlr8-header__brand-divider">|</span> <span className="xlr8-header__brand-tagline">INTELLIGENT ANALYSIS by HCMPACT</span>
          </div>
        </div>
      </div>

      <div className="xlr8-header__center">
        {/* Search bar - future feature */}
        <div className="xlr8-header__search">
          <span className="xlr8-header__search-icon">🔍</span>
          <input 
            type="text" 
            className="xlr8-header__search-input" 
            placeholder="Search projects, findings, playbooks..."
          />
        </div>
      </div>

      <div className="xlr8-header__actions">
        <button 
          className="xlr8-header__icon-btn" 
          title="Chat"
          onClick={() => console.log('Chat clicked')}
        >
          💬
        </button>
        
        <button 
          className="xlr8-header__icon-btn" 
          title="Notifications"
          onClick={() => console.log('Notifications clicked')}
        >
          🔔
          <span className="xlr8-header__badge">23</span>
        </button>
        
        <button 
          className="xlr8-header__icon-btn" 
          title="Settings"
          onClick={onMenuClick}
        >
          ⚙️
        </button>

        <div className="xlr8-header__user-menu">
          <div className="xlr8-header__user-avatar">
            {user?.initials || 'SM'}
          </div>
          <div className="xlr8-header__user-info">
            <div className="xlr8-header__user-name">{user?.name || 'Scott Miller'}</div>
            <div className="xlr8-header__user-role">{user?.role || 'CEO · Admin'}</div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
