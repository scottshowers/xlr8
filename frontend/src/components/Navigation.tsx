import React from 'react';
import { Link, useLocation } from 'react-router-dom';

// H Logo SVG Component
const HLogo = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 570" style={{ width: '100%', height: '100%' }}>
    <path fill="#698f57" d="M492.04,500v-31.35l-36.53-35.01V163.76c0-15.8,.94-16.74,16.74-16.74h19.79v-31.36l-45.66-45.66H73v31.36l36.53,36.53V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35l45.66,45.66H492.04Zm-197.11-93.76c0,15.8-.94,16.74-16.74,16.74h-8.07v-103.81h24.81v87.07Zm-24.81-242.48c0-15.8,.94-16.74,16.74-16.74h8.07v95.13h-24.81v-78.39Z"/>
    <g>
      <rect fill="#a8ca99" x="134.8" y="348.24" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="324.95" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="302.12" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="279.29" width="64.39" height="11.87"/>
      <path fill="#a8ca99" d="M134.34,107.14h65.76c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
      <path fill="#a8ca99" d="M319.74,417.19c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.75Z"/>
      <rect fill="#a8ca99" x="134.8" y="371.08" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="393.91" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="118.1" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="164.22" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="140.93" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="256" width="64.39" height="11.87"/>
      <path fill="#a8ca99" d="M134.34,417.19c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.76Z"/>
      <rect fill="#a8ca99" x="134.8" y="140.93" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="233.17" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="187.05" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="210.34" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="371.08" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="324.95" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="348.24" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="279.29" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="302.12" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="393.91" width="64.39" height="11.87"/>
      <path fill="#a8ca99" d="M319.74,107.14h65.75c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
      <rect fill="#a8ca99" x="320.19" y="164.22" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="118.1" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="187.05" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="210.34" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="256" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="233.17" width="64.39" height="11.87"/>
    </g>
    <path fill="#84b26d" d="M426.59,95.27h13.7v-19.18h-173.52v19.18h11.42c19.18,0,22.83,3.65,22.83,22.83V248.24h-82.65V118.1c0-19.18,3.65-22.83,22.83-22.83h11.42v-19.18H79.09v19.18h13.7c19.18,0,22.83,3.65,22.83,22.83V406.24c0,19.18-3.65,22.83-22.83,22.83h-13.7v19.18H252.61v-19.18h-11.42c-19.18,0-22.83-3.65-22.83-22.83v-138.82h82.65v138.82c0,19.18-3.65,22.83-22.83,22.83h-11.42v19.18h173.52v-19.18h-13.7c-19.18,0-22.83-3.65-22.83-22.83V118.1c0-19.18,3.65-22.83,22.83-22.83Z"/>
    <path fill="#9cc28a" d="M426.59,101.36h19.79v-31.36h-183.7v31.36h15.5c15.8,0,16.74,.94,16.74,16.74v124.05h-70.47V118.1c0-15.8,.94-16.74,16.74-16.74h15.5v-31.36H73v31.36h19.79c15.8,0,16.74,.94,16.74,16.74V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35h183.7v-31.35h-15.5c-15.8,0-16.74-.94-16.74-16.74v-132.73h70.47v132.73c0,15.8-.94,16.74-16.74,16.74h-15.5v31.35h183.7v-31.35h-19.79c-15.8,0-16.74-.94-16.74-16.74V118.1c0-15.8,.94-16.74,16.74-16.74Z"/>
  </svg>
);

interface NavigationProps {
  // Add any props if needed
}

const Navigation: React.FC<NavigationProps> = () => {
  const location = useLocation();
  
  const isActive = (path: string): boolean => {
    return location.pathname === path || (path === '/chat' && location.pathname === '/');
  };

  return (
    <nav className="nav">
      <div className="container">
        <div className="nav-content">
          <Link to="/" className="logo">
            <div className="logo-mark">
              <HLogo />
            </div>
            <span className="logo-text">XLR8</span>
          </Link>
          <ul className="nav-links">
            <li>
              <Link 
                to="/chat" 
                className={isActive('/chat') ? 'active' : ''}
              >
                Chat
              </Link>
            </li>
            <li>
              <Link 
                to="/upload" 
                className={isActive('/upload') ? 'active' : ''}
              >
                Upload
              </Link>
            </li>
            <li>
              <Link 
                to="/status" 
                className={isActive('/status') ? 'active' : ''}
              >
                Status
              </Link>
            </li>
            <li>
              <Link 
                to="/projects" 
                className={isActive('/projects') ? 'active' : ''}
              >
                Projects
              </Link>
            </li>
            <li>
              <Link 
                to="/secure20" 
                className={isActive('/secure20') ? 'active' : ''}
              >
                SECURE 2.0
              </Link>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
