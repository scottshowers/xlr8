/**
 * DashboardPage.jsx - COMMAND CENTER
 * 
 * Premium dashboard with:
 * - Radial gauges for health scores
 * - Consistent customer color coding
 * - Clickable project cards → select project
 * - Clickable feed items → navigate to relevant page
 * - Animated elements
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme, STATUS, BRAND } from '../context/ThemeContext';
import { useProject } from '../context/ProjectContext';
import { 
  Upload, Zap, MessageSquare, ClipboardList,
  FolderOpen, PlayCircle, AlertTriangle, Shield, Activity,
  TrendingUp, ArrowRight
} from 'lucide-react';

// Customer color system - consistent across all displays
export const CUSTOMER_COLORS = {
  'MEY1000': { primary: '#83b16d', secondary: '#a8ca99', bg: 'linear-gradient(135deg, #83b16d15, #a8ca9910)' },
  'ACM2500': { primary: '#93abd9', secondary: '#b4c7e7', bg: 'linear-gradient(135deg, #93abd915, #b4c7e710)' },
  'GLB3000': { primary: '#f59e0b', secondary: '#fbbf24', bg: 'linear-gradient(135deg, #f59e0b15, #fbbf2410)' },
  'TEC4000': { primary: '#8b5cf6', secondary: '#a78bfa', bg: 'linear-gradient(135deg, #8b5cf615, #a78bfa10)' },
  'GLOBAL':  { primary: '#14b8a6', secondary: '#5eead4', bg: 'linear-gradient(135deg, #14b8a615, #5eead410)' },
};

export const getCustomerColor = (projectName) => {
  return CUSTOMER_COLORS[projectName] || CUSTOMER_COLORS['GLOBAL'];
};

// Radial Gauge Component
function RadialGauge({ value, size = 80, strokeWidth = 8, color, label }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;
  
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          opacity={0.1}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ 
            transition: 'stroke-dashoffset 1s ease-out',
            filter: `drop-shadow(0 0 6px ${color}60)`,
          }}
        />
      </svg>
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        textAlign: 'center',
      }}>
        <div style={{ 
          fontSize: size * 0.25, 
          fontWeight: 700, 
          fontFamily: 'monospace',
          color: color,
          textShadow: `0 0 10px ${color}40`,
        }}>
          {value}%
        </div>
        {label && (
          <div style={{ fontSize: size * 0.12, opacity: 0.6, marginTop: 2 }}>{label}</div>
        )}
      </div>
    </div>
  );
}

// Mini Sparkline Component
function Sparkline({ data, color, width = 60, height = 24 }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  
  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((val - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} style={{ overflow: 'visible' }}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ filter: `drop-shadow(0 0 4px ${color}60)` }}
      />
    </svg>
  );
}

// Stat Card Component
function StatCard({ label, value, icon: Icon, color, trend, sparkData, T, darkMode }) {
  return (
    <div style={{ 
      background: T.bgCard, 
      border: `1px solid ${T.border}`, 
      borderRadius: '12px', 
      padding: '1.25rem', 
      position: 'relative', 
      overflow: 'hidden',
      transition: 'all 0.3s ease',
    }}>
      {/* Glow line */}
      <div style={{ 
        position: 'absolute', 
        top: 0, 
        left: 0, 
        right: 0, 
        height: 3, 
        background: `linear-gradient(90deg, ${color}, ${color}80)`,
        boxShadow: `0 0 20px ${color}60`,
      }} />
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ 
            fontSize: '0.7rem', 
            color: T.textDim, 
            marginBottom: '0.5rem', 
            textTransform: 'uppercase', 
            letterSpacing: '0.1em',
            fontWeight: 600,
          }}>
            {label}
          </div>
          <div style={{ 
            fontSize: '2.25rem', 
            fontWeight: 700, 
            color: color, 
            textShadow: darkMode ? `0 0 30px ${color}50` : 'none', 
            fontFamily: 'monospace',
            lineHeight: 1,
          }}>
            {value}
          </div>
          {trend && (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.25rem', 
              marginTop: '0.5rem',
              fontSize: '0.75rem',
              color: trend > 0 ? STATUS.green : STATUS.red,
            }}>
              <TrendingUp size={12} style={{ transform: trend < 0 ? 'rotate(180deg)' : 'none' }} />
              {Math.abs(trend)}% vs last week
            </div>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
          <Icon size={24} style={{ opacity: 0.4, color: T.textDim }} />
          {sparkData && <Sparkline data={sparkData} color={color} />}
        </div>
      </div>
    </div>
  );
}

// Project Card Component with Gauge
function ProjectCard({ project, T, darkMode, onClick, isSelected }) {
  const colors = getCustomerColor(project.name);
  const healthColor = project.health >= 80 ? STATUS.green : project.health >= 60 ? STATUS.amber : STATUS.red;
  
  return (
    <div 
      onClick={onClick}
      style={{ 
        background: darkMode ? T.bgCard : 'white',
        border: `2px solid ${isSelected ? colors.primary : T.border}`,
        borderRadius: '16px', 
        padding: '1.25rem', 
        cursor: 'pointer', 
        position: 'relative',
        overflow: 'hidden',
        transition: 'all 0.3s ease',
        boxShadow: isSelected ? `0 0 20px ${colors.primary}30` : 'none',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = `0 8px 30px ${colors.primary}20`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = isSelected ? `0 0 20px ${colors.primary}30` : 'none';
      }}
    >
      {/* Customer color indicator bar */}
      <div style={{ 
        position: 'absolute', 
        top: 0, 
        left: 0, 
        right: 0, 
        height: 4, 
        background: `linear-gradient(90deg, ${colors.primary}, ${colors.secondary})`,
      }} />
      
      {/* Background gradient */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: colors.bg,
        opacity: darkMode ? 0.5 : 1,
      }} />
      
      <div style={{ position: 'relative', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <div style={{ 
            fontWeight: 700, 
            fontSize: '1.1rem',
            color: colors.primary,
            marginBottom: '0.25rem',
          }}>
            {project.name}
          </div>
          <div style={{ fontSize: '0.85rem', color: T.textDim, marginBottom: '1rem' }}>
            {project.customer}
          </div>
          
          <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.8rem' }}>
            <div>
              <span style={{ color: T.textDim }}>Playbooks </span>
              <span style={{ 
                color: STATUS.blue, 
                fontWeight: 600,
                background: `${STATUS.blue}15`,
                padding: '0.15rem 0.5rem',
                borderRadius: '10px',
              }}>
                {project.activePlaybooks}
              </span>
            </div>
            <div>
              <span style={{ color: T.textDim }}>Findings </span>
              <span style={{ 
                color: project.pendingFindings > 10 ? STATUS.amber : STATUS.green,
                fontWeight: 600,
                background: project.pendingFindings > 10 ? `${STATUS.amber}15` : `${STATUS.green}15`,
                padding: '0.15rem 0.5rem',
                borderRadius: '10px',
              }}>
                {project.pendingFindings}
              </span>
            </div>
          </div>
        </div>
        
        <RadialGauge 
          value={project.health} 
          size={70} 
          strokeWidth={6} 
          color={healthColor}
          label="Health"
        />
      </div>
      
      {/* Click indicator */}
      <div style={{
        position: 'absolute',
        bottom: '0.75rem',
        right: '0.75rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.25rem',
        fontSize: '0.7rem',
        color: colors.primary,
        opacity: 0.7,
      }}>
        Select <ArrowRight size={12} />
      </div>
    </div>
  );
}

// Feed Item Component
function FeedItem({ item, T, darkMode, onClick }) {
  const colors = getCustomerColor(item.project);
  
  const getLevelStyle = (level) => {
    if (level === 'success') return { color: STATUS.green, bg: `${STATUS.green}15` };
    if (level === 'warning') return { color: STATUS.amber, bg: `${STATUS.amber}15` };
    return { color: STATUS.blue, bg: `${STATUS.blue}15` };
  };
  
  const style = getLevelStyle(item.level);
  
  return (
    <div 
      onClick={onClick}
      style={{ 
        background: darkMode ? T.bg : 'white', 
        border: `1px solid ${T.border}`, 
        borderLeft: `4px solid ${colors.primary}`,
        borderRadius: '8px', 
        padding: '0.875rem 1rem', 
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateX(4px)';
        e.currentTarget.style.borderLeftWidth = '6px';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateX(0)';
        e.currentTarget.style.borderLeftWidth = '4px';
      }}
    >
      {/* Subtle background gradient */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: colors.bg,
        opacity: 0.3,
      }} />
      
      <div style={{ position: 'relative' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>{item.msg}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {/* Mini progress bar */}
            <div style={{ 
              width: 60, 
              height: 6, 
              background: T.border, 
              borderRadius: 3,
              overflow: 'hidden',
            }}>
              <div style={{
                width: '100%',
                height: '100%',
                background: `linear-gradient(90deg, ${style.color}, ${style.color}60)`,
                borderRadius: 3,
                boxShadow: `0 0 8px ${style.color}60`,
              }} />
            </div>
            <span style={{ fontSize: '0.75rem', color: T.textDim, minWidth: 30, textAlign: 'right' }}>{item.time}</span>
          </div>
        </div>
        <div style={{ 
          marginTop: '0.4rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          <span style={{ 
            fontSize: '0.75rem',
            fontWeight: 700,
            color: colors.primary,
            background: colors.bg,
            padding: '0.2rem 0.6rem',
            borderRadius: '10px',
            border: `1px solid ${colors.primary}30`,
          }}>
            {item.project}
          </span>
          <span style={{
            fontSize: '0.7rem',
            color: style.color,
            background: style.bg,
            padding: '0.15rem 0.5rem',
            borderRadius: '8px',
            textTransform: 'capitalize',
          }}>
            {item.level}
          </span>
        </div>
      </div>
    </div>
  );
}

// Quick Action Button
function QuickAction({ icon: Icon, label, shortcut, onClick, T }) {
  return (
    <button 
      onClick={onClick}
      style={{ 
        background: T.bgCard, 
        border: `1px solid ${T.border}`, 
        borderRadius: '12px', 
        padding: '1rem 1.25rem', 
        cursor: 'pointer', 
        display: 'flex', 
        alignItems: 'center', 
        gap: '0.75rem', 
        color: T.text,
        transition: 'all 0.2s ease',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = BRAND.grassGreen;
        e.currentTarget.style.boxShadow = `0 4px 20px ${BRAND.grassGreen}20`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = T.border;
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <div style={{
        width: 36,
        height: 36,
        borderRadius: '10px',
        background: `${BRAND.grassGreen}15`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <Icon size={18} style={{ color: BRAND.grassGreen }} />
      </div>
      <span style={{ fontWeight: 600, flex: 1 }}>{label}</span>
      <span style={{ 
        fontSize: '0.7rem', 
        color: T.textDim, 
        padding: '0.3rem 0.5rem', 
        background: T.bg, 
        borderRadius: '6px', 
        fontFamily: 'monospace',
        fontWeight: 600,
      }}>
        {shortcut}
      </span>
    </button>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { darkMode, T } = useTheme();
  const { setActiveProject, activeProject } = useProject();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  // Mock data
  const stats = [
    { label: 'Active Projects', value: 4, icon: FolderOpen, color: BRAND.grassGreen, trend: 12, sparkData: [2, 3, 3, 4, 3, 4, 4] },
    { label: 'Playbooks Running', value: 6, icon: PlayCircle, color: STATUS.blue, trend: 8, sparkData: [4, 5, 6, 5, 7, 6, 6] },
    { label: 'Pending Findings', value: 44, icon: AlertTriangle, color: STATUS.amber, trend: -15, sparkData: [60, 55, 52, 48, 45, 44, 44] },
    { label: 'Compliance Score', value: '73%', icon: Shield, color: STATUS.green, trend: 5, sparkData: [65, 68, 70, 69, 72, 73, 73] },
  ];

  const projects = [
    { id: '1', name: 'MEY1000', customer: 'Meyer Corp', health: 92, activePlaybooks: 2, pendingFindings: 3 },
    { id: '2', name: 'ACM2500', customer: 'Acme Industries', health: 67, activePlaybooks: 1, pendingFindings: 12 },
    { id: '3', name: 'GLB3000', customer: 'Global Tech', health: 45, activePlaybooks: 0, pendingFindings: 28 },
    { id: '4', name: 'TEC4000', customer: 'TechFlow Inc', health: 88, activePlaybooks: 3, pendingFindings: 1 },
  ];

  const liveFeed = [
    { level: 'info', msg: 'Payroll register processed', project: 'MEY1000', time: '2m', path: '/data' },
    { level: 'warning', msg: 'SECURE 2.0 gap detected', project: 'ACM2500', time: '15m', path: '/playbooks' },
    { level: 'success', msg: 'Year-End Checklist passed', project: 'MEY1000', time: '1h', path: '/playbooks' },
    { level: 'warning', msg: 'Missing deduction codes', project: 'GLB3000', time: '2h', path: '/playbooks' },
    { level: 'info', msg: 'New standards doc uploaded', project: 'GLOBAL', time: '3h', path: '/reference-library' },
  ];

  const quickActions = [
    { icon: Upload, label: 'Upload Data', key: 'U', path: '/data' },
    { icon: Zap, label: 'Run Playbook', key: 'P', path: '/playbooks' },
    { icon: MessageSquare, label: 'Open Chat', key: 'C', path: '/workspace' },
    { icon: ClipboardList, label: 'View Findings', key: 'F', path: '/playbooks' },
  ];

  const handleProjectClick = (project) => {
    setActiveProject(project.id, project.name, project.customer);
    navigate('/data');
  };

  const handleFeedClick = (item) => {
    // Find project by name and select it
    const project = projects.find(p => p.name === item.project);
    if (project && item.project !== 'GLOBAL') {
      setActiveProject(project.id, project.name, project.customer);
    }
    navigate(item.path);
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ 
            fontSize: '1.75rem', 
            fontWeight: 700, 
            margin: 0, 
            letterSpacing: '0.05em', 
            fontFamily: "'Sora', sans-serif",
            background: `linear-gradient(135deg, ${T.text}, ${T.textDim})`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            COMMAND CENTER
          </h1>
          <p style={{ color: T.textDim, margin: '0.25rem 0 0 0', fontSize: '0.85rem' }}>XLR8 Operations Overview</p>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          {/* System Status */}
          <div style={{ 
            background: `${STATUS.green}15`, 
            border: `1px solid ${STATUS.green}30`,
            borderRadius: '12px',
            padding: '0.5rem 1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
          }}>
            <div style={{ 
              fontSize: '0.7rem', 
              color: T.textDim, 
              textTransform: 'uppercase', 
              letterSpacing: '0.05em' 
            }}>
              System Status
            </div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem',
              color: STATUS.green,
              fontWeight: 600,
              fontSize: '0.85rem',
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
            fontSize: '1.75rem', 
            fontWeight: 600,
            color: BRAND.grassGreen, 
            textShadow: darkMode ? `0 0 30px ${BRAND.grassGreen}50` : 'none',
            letterSpacing: '0.05em',
          }}>
            {time.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div data-tour="dashboard-stats" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        {stats.map((stat, i) => (
          <StatCard key={i} {...stat} T={T} darkMode={darkMode} />
        ))}
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1.5rem' }}>
        {/* Project Grid */}
        <div data-tour="dashboard-projects">
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            marginBottom: '1rem',
          }}>
            <h2 style={{ 
              fontSize: '0.8rem', 
              fontWeight: 600, 
              color: T.textDim, 
              margin: 0,
              textTransform: 'uppercase', 
              letterSpacing: '0.1em' 
            }}>
              Active Engagements
            </h2>
            <button
              onClick={() => navigate('/projects')}
              style={{
                background: 'none',
                border: 'none',
                color: BRAND.grassGreen,
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
              }}
            >
              View All <ArrowRight size={14} />
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            {projects.map(project => (
              <ProjectCard 
                key={project.id} 
                project={project} 
                T={T} 
                darkMode={darkMode}
                onClick={() => handleProjectClick(project)}
                isSelected={activeProject === project.id}
              />
            ))}
          </div>
        </div>

        {/* Live Feed */}
        <div>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem',
            marginBottom: '1rem',
          }}>
            <Activity size={16} style={{ color: STATUS.green }} />
            <h2 style={{ 
              fontSize: '0.8rem', 
              fontWeight: 600, 
              color: T.textDim, 
              margin: 0,
              textTransform: 'uppercase', 
              letterSpacing: '0.1em' 
            }}>
              Live Feed
            </h2>
            <div style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: STATUS.green,
              animation: 'pulse 1.5s infinite',
            }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {liveFeed.map((item, i) => (
              <FeedItem 
                key={i} 
                item={item} 
                T={T} 
                darkMode={darkMode}
                onClick={() => handleFeedClick(item)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div data-tour="dashboard-actions" style={{ marginTop: '2rem', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        {quickActions.map((action, i) => (
          <QuickAction 
            key={i} 
            icon={action.icon}
            label={action.label}
            shortcut={action.key}
            onClick={() => navigate(action.path)}
            T={T}
          />
        ))}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.95); }
        }
      `}</style>
    </div>
  );
}
