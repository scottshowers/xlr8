/**
 * DashboardPage.jsx - COMMAND CENTER
 * 
 * XLR8 Operations Dashboard with light/dark theme toggle
 * Dark theme: Soft Navy
 * Light theme: Brand colors
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Sun, Moon, Upload, Zap, MessageSquare, ClipboardList,
  FolderOpen, PlayCircle, AlertTriangle, Shield, Activity
} from 'lucide-react';

// Brand colors
const BRAND = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  text: '#2a3441',
};

// Theme definitions
const themes = {
  light: {
    bg: '#f6f5fa',
    bgCard: '#ffffff',
    border: '#e2e8f0',
    text: '#2a3441',
    textDim: '#5f6c7b',
    accent: BRAND.grassGreen,
  },
  dark: {
    bg: '#1a2332',        // Soft Navy
    bgCard: '#232f42',
    border: '#334766',
    text: '#e5e7eb',
    textDim: '#9ca3af',
    accent: BRAND.grassGreen,
  },
};

// Semantic colors (same for both themes)
const STATUS = {
  green: '#10b981',
  amber: '#f59e0b',
  red: '#ef4444',
  blue: '#3b82f6',
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('xlr8-theme');
    return saved ? saved === 'dark' : true; // Default to dark
  });
  const [time, setTime] = useState(new Date());

  // Update time every second
  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  // Persist theme preference
  useEffect(() => {
    localStorage.setItem('xlr8-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  const T = darkMode ? themes.dark : themes.light;

  // Mock data - replace with real API calls
  const stats = [
    { label: 'Active Projects', value: 4, icon: FolderOpen, color: BRAND.grassGreen },
    { label: 'Playbooks Running', value: 6, icon: PlayCircle, color: STATUS.blue },
    { label: 'Pending Findings', value: 44, icon: AlertTriangle, color: STATUS.amber },
    { label: 'Compliance Score', value: '73%', icon: Shield, color: STATUS.green },
  ];

  const projects = [
    { id: 1, name: 'MEY1000', customer: 'Meyer Corp', health: 92, activePlaybooks: 2, pendingFindings: 3 },
    { id: 2, name: 'ACM2500', customer: 'Acme Industries', health: 67, activePlaybooks: 1, pendingFindings: 12 },
    { id: 3, name: 'GLB3000', customer: 'Global Tech', health: 45, activePlaybooks: 0, pendingFindings: 28 },
    { id: 4, name: 'TEC4000', customer: 'TechFlow Inc', health: 88, activePlaybooks: 3, pendingFindings: 1 },
  ];

  const liveFeed = [
    { level: 'info', msg: 'Payroll register processed', project: 'MEY1000', time: '2m' },
    { level: 'warning', msg: 'SECURE 2.0 gap detected', project: 'ACM2500', time: '15m' },
    { level: 'success', msg: 'Year-End Checklist passed', project: 'MEY1000', time: '1h' },
    { level: 'warning', msg: 'Missing deduction codes', project: 'GLB3000', time: '2h' },
    { level: 'info', msg: 'New standards doc uploaded', project: 'GLOBAL', time: '3h' },
  ];

  const quickActions = [
    { icon: Upload, label: 'Upload Data', key: 'U', path: '/data' },
    { icon: Zap, label: 'Run Playbook', key: 'P', path: '/playbooks' },
    { icon: MessageSquare, label: 'Open Chat', key: 'C', path: '/workspace' },
    { icon: ClipboardList, label: 'View Findings', key: 'F', path: '/findings' },
  ];

  const getHealthColor = (health) => {
    if (health >= 80) return STATUS.green;
    if (health >= 60) return STATUS.amber;
    return STATUS.red;
  };

  const getLevelColor = (level) => {
    const colors = { info: STATUS.blue, warning: STATUS.amber, success: STATUS.green };
    return colors[level] || STATUS.blue;
  };

  return (
    <div style={{ 
      padding: '1.5rem', 
      background: T.bg, 
      minHeight: '100vh', 
      color: T.text, 
      fontFamily: "'Inter', system-ui, sans-serif",
      transition: 'background 0.3s ease, color 0.3s ease',
    }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '2rem' 
      }}>
        <div>
          <h1 style={{ 
            fontSize: '1.5rem', 
            fontWeight: 700, 
            margin: 0, 
            letterSpacing: '0.05em',
            fontFamily: "'Sora', sans-serif",
          }}>
            COMMAND CENTER
          </h1>
          <p style={{ color: T.textDim, margin: '0.25rem 0 0 0', fontSize: '0.85rem' }}>
            XLR8 Operations Overview
          </p>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {/* Theme Toggle */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            style={{
              background: T.bgCard,
              border: `1px solid ${T.border}`,
              borderRadius: '8px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              color: T.text,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
              transition: 'all 0.2s ease',
            }}
            aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            {darkMode ? 'Light' : 'Dark'}
          </button>

          {/* System Status */}
          <div style={{ textAlign: 'right' }}>
            <div style={{ 
              fontSize: '0.7rem', 
              color: T.textDim, 
              textTransform: 'uppercase', 
              letterSpacing: '0.1em' 
            }}>
              System Status
            </div>
            <div style={{ 
              fontSize: '0.85rem', 
              color: STATUS.green, 
              fontWeight: 600, 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem',
              justifyContent: 'flex-end',
            }}>
              <span style={{ 
                width: 8, 
                height: 8, 
                borderRadius: '50%', 
                background: STATUS.green, 
                boxShadow: `0 0 10px ${STATUS.green}`,
                animation: 'pulse 2s infinite',
              }} />
              OPERATIONAL
            </div>
          </div>

          {/* Live Clock */}
          <div style={{ 
            fontFamily: 'monospace', 
            fontSize: '1.5rem', 
            color: T.accent, 
            textShadow: darkMode ? `0 0 20px ${T.accent}40` : 'none',
          }}>
            {time.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(4, 1fr)', 
        gap: '1rem', 
        marginBottom: '2rem' 
      }}>
        {stats.map((stat, i) => (
          <div 
            key={i} 
            style={{ 
              background: T.bgCard, 
              border: `1px solid ${T.border}`, 
              borderRadius: '8px', 
              padding: '1.25rem', 
              position: 'relative', 
              overflow: 'hidden',
              transition: 'all 0.2s ease',
              cursor: 'pointer',
            }}
          >
            <div style={{ 
              position: 'absolute', 
              top: 0, 
              left: 0, 
              right: 0, 
              height: 2, 
              background: stat.color, 
              boxShadow: `0 0 10px ${stat.color}` 
            }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ 
                  fontSize: '0.75rem', 
                  color: T.textDim, 
                  marginBottom: '0.5rem', 
                  textTransform: 'uppercase', 
                  letterSpacing: '0.05em' 
                }}>
                  {stat.label}
                </div>
                <div style={{ 
                  fontSize: '2rem', 
                  fontWeight: 700, 
                  color: stat.color, 
                  textShadow: darkMode ? `0 0 20px ${stat.color}40` : 'none', 
                  fontFamily: 'monospace' 
                }}>
                  {stat.value}
                </div>
              </div>
              <stat.icon size={24} style={{ opacity: 0.5, color: T.textDim }} />
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Project Grid */}
        <div style={{ 
          background: T.bgCard, 
          border: `1px solid ${T.border}`, 
          borderRadius: '12px', 
          padding: '1.5rem',
          transition: 'all 0.2s ease',
        }}>
          <h2 style={{ 
            fontSize: '0.8rem', 
            fontWeight: 600, 
            color: T.textDim, 
            marginBottom: '1.25rem', 
            textTransform: 'uppercase', 
            letterSpacing: '0.1em' 
          }}>
            Active Engagements
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            {projects.map(project => (
              <div 
                key={project.id} 
                onClick={() => navigate(`/projects/${project.id}`)}
                style={{ 
                  background: T.bg, 
                  border: `1px solid ${T.border}`, 
                  borderRadius: '8px', 
                  padding: '1rem', 
                  cursor: 'pointer', 
                  position: 'relative',
                  transition: 'all 0.2s ease',
                }}
              >
                {/* Health bar */}
                <div style={{ 
                  position: 'absolute', 
                  top: 0, 
                  left: 0, 
                  width: `${project.health}%`, 
                  height: 3, 
                  background: getHealthColor(project.health), 
                  boxShadow: `0 0 8px ${getHealthColor(project.health)}`, 
                  borderRadius: '8px 0 0 0' 
                }} />
                
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'flex-start', 
                  marginBottom: '0.75rem' 
                }}>
                  <div>
                    <div style={{ fontWeight: 700, color: T.text, fontSize: '0.95rem' }}>
                      {project.name}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: T.textDim }}>
                      {project.customer}
                    </div>
                  </div>
                  <div style={{ 
                    padding: '0.25rem 0.5rem', 
                    background: getHealthColor(project.health) + '20', 
                    color: getHealthColor(project.health), 
                    fontSize: '0.75rem', 
                    fontWeight: 700, 
                    borderRadius: '4px', 
                    fontFamily: 'monospace' 
                  }}>
                    {project.health}%
                  </div>
                </div>
                
                <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem' }}>
                  <div>
                    <span style={{ color: T.textDim }}>Playbooks: </span>
                    <span style={{ color: STATUS.blue }}>{project.activePlaybooks}</span>
                  </div>
                  <div>
                    <span style={{ color: T.textDim }}>Findings: </span>
                    <span style={{ color: project.pendingFindings > 10 ? STATUS.amber : STATUS.green }}>
                      {project.pendingFindings}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Live Feed */}
        <div style={{ 
          background: T.bgCard, 
          border: `1px solid ${T.border}`, 
          borderRadius: '12px', 
          padding: '1.5rem', 
          display: 'flex', 
          flexDirection: 'column',
          transition: 'all 0.2s ease',
        }}>
          <h2 style={{ 
            fontSize: '0.8rem', 
            fontWeight: 600, 
            color: T.textDim, 
            marginBottom: '1.25rem', 
            textTransform: 'uppercase', 
            letterSpacing: '0.1em',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}>
            <Activity size={14} />
            Live Feed
          </h2>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {liveFeed.map((item, i) => (
              <div 
                key={i} 
                style={{ 
                  background: T.bg, 
                  border: `1px solid ${T.border}`, 
                  borderLeft: `3px solid ${getLevelColor(item.level)}`, 
                  borderRadius: '4px', 
                  padding: '0.75rem 1rem', 
                  fontSize: '0.85rem',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: T.text }}>{item.msg}</span>
                  <span style={{ fontSize: '0.7rem', color: T.textDim }}>{item.time}</span>
                </div>
                <div style={{ 
                  fontSize: '0.7rem', 
                  color: getLevelColor(item.level), 
                  marginTop: '0.25rem', 
                  fontWeight: 600 
                }}>
                  {item.project}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ 
        marginTop: '1.5rem', 
        display: 'grid', 
        gridTemplateColumns: 'repeat(4, 1fr)', 
        gap: '1rem' 
      }}>
        {quickActions.map((action, i) => (
          <button 
            key={i}
            onClick={() => navigate(action.path)}
            style={{ 
              background: T.bgCard, 
              border: `1px solid ${T.border}`, 
              borderRadius: '8px', 
              padding: '1rem', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.75rem', 
              color: T.text,
              transition: 'all 0.2s ease',
            }}
          >
            <action.icon size={20} style={{ color: T.accent }} />
            <span style={{ fontWeight: 600 }}>{action.label}</span>
            <span style={{ 
              marginLeft: 'auto', 
              fontSize: '0.7rem', 
              color: T.textDim, 
              padding: '0.2rem 0.4rem', 
              background: T.bg, 
              borderRadius: '3px', 
              fontFamily: 'monospace' 
            }}>
              {action.key}
            </span>
          </button>
        ))}
      </div>

      {/* Pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
