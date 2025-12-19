/**
 * DashboardPage.jsx - Command Center
 * 
 * Clean professional design with:
 * - Light/dark mode support
 * - Tab toggles (This Week / This Month)
 * - Bar charts for activity
 * - Stats with goals
 * - Project leaderboard by health
 * 
 * Style reference: Clean white cards, subtle shadows, green accents
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';
import { 
  Upload, Zap, MessageSquare, FolderOpen, 
  AlertTriangle, CheckCircle, Clock, ArrowRight,
  TrendingUp, TrendingDown, Calendar, RefreshCw
} from 'lucide-react';

// Theme-aware colors
const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f5f7fa',
  card: dark ? '#242b3d' : '#ffffff',
  cardBorder: dark ? '#2d3548' : '#e8ecf1',
  text: dark ? '#e8eaed' : '#2a3441',
  textMuted: dark ? '#8b95a5' : '#6b7280',
  textLight: dark ? '#5f6a7d' : '#9ca3af',
  primary: '#83b16d',
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.1)',
  blue: '#5b8fb9',
  blueLight: dark ? 'rgba(91, 143, 185, 0.15)' : 'rgba(91, 143, 185, 0.1)',
  amber: '#d4a054',
  red: '#c76b6b',
  divider: dark ? '#2d3548' : '#e8ecf1',
  inputBg: dark ? '#1a1f2e' : '#f8fafc',
});

// Tab Toggle Component
function TabToggle({ options, value, onChange, colors }) {
  return (
    <div style={{
      display: 'inline-flex',
      background: colors.inputBg,
      borderRadius: 8,
      padding: 3,
      gap: 2,
    }}>
      {options.map(opt => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          style={{
            padding: '0.5rem 1rem',
            borderRadius: 6,
            border: 'none',
            background: value === opt.value ? colors.primary : 'transparent',
            color: value === opt.value ? 'white' : colors.textMuted,
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

// Stat Card with Goal
function StatCard({ label, value, goal, icon: Icon, trend, colors, onClick }) {
  const percentage = goal ? Math.round((value / goal) * 100) : null;
  const isAboveGoal = goal && value >= goal;
  
  return (
    <div 
      onClick={onClick}
      style={{
        background: colors.card,
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: 12,
        padding: '1.25rem',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s ease',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
      }}
      onMouseEnter={(e) => onClick && (e.currentTarget.style.transform = 'translateY(-2px)')}
      onMouseLeave={(e) => onClick && (e.currentTarget.style.transform = 'translateY(0)')}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {label}
        </span>
        {Icon && (
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: colors.primaryLight,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Icon size={16} style={{ color: colors.primary }} />
          </div>
        )}
      </div>
      
      <div style={{ fontSize: '2rem', fontWeight: 700, color: colors.text, lineHeight: 1 }}>
        {value}
      </div>
      
      {goal && (
        <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', color: colors.textMuted }}>Goal: {goal}</span>
          {trend !== undefined && (
            <span style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.2rem',
              fontSize: '0.75rem', 
              fontWeight: 600,
              color: trend >= 0 ? colors.primary : colors.red,
            }}>
              {trend >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              {Math.abs(trend)}%
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// Simple Bar Chart
function BarChart({ data, colors, height = 160 }) {
  const max = Math.max(...data.map(d => d.value), 1);
  
  return (
    <div style={{ height, display: 'flex', alignItems: 'flex-end', gap: '0.5rem', padding: '0 0.5rem' }}>
      {data.map((item, i) => {
        const barHeight = (item.value / max) * (height - 30);
        return (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ fontSize: '0.7rem', fontWeight: 600, color: colors.text }}>{item.value}</span>
            <div style={{
              width: '100%',
              height: barHeight,
              background: item.type === 'playbook' ? colors.blue : colors.primary,
              borderRadius: '4px 4px 0 0',
              minHeight: 4,
              transition: 'height 0.3s ease',
            }} />
            <span style={{ fontSize: '0.65rem', color: colors.textMuted, fontWeight: 500 }}>{item.label}</span>
          </div>
        );
      })}
    </div>
  );
}

// Project Row for Leaderboard
function ProjectRow({ rank, project, colors, onClick, isSelected }) {
  const healthColor = project.health >= 80 ? colors.primary : project.health >= 50 ? colors.amber : colors.red;
  
  return (
    <div 
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '0.875rem 1rem',
        borderBottom: `1px solid ${colors.divider}`,
        cursor: 'pointer',
        background: isSelected ? colors.primaryLight : 'transparent',
        transition: 'background 0.15s ease',
      }}
      onMouseEnter={(e) => !isSelected && (e.currentTarget.style.background = colors.inputBg)}
      onMouseLeave={(e) => !isSelected && (e.currentTarget.style.background = 'transparent')}
    >
      <div style={{
        width: 28,
        height: 28,
        borderRadius: '50%',
        background: rank <= 3 ? colors.primaryLight : colors.inputBg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: '0.875rem',
        fontSize: '0.8rem',
        fontWeight: 700,
        color: rank <= 3 ? colors.primary : colors.textMuted,
      }}>
        #{rank}
      </div>
      
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, color: colors.text, fontSize: '0.9rem' }}>{project.name}</div>
        <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>{project.customer || 'No customer'}</div>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.65rem', color: colors.textMuted, marginBottom: 2 }}>FILES</div>
          <div style={{ fontSize: '0.9rem', fontWeight: 600, color: colors.text }}>{project.fileCount || 0}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.65rem', color: colors.textMuted, marginBottom: 2 }}>FINDINGS</div>
          <div style={{ fontSize: '0.9rem', fontWeight: 600, color: project.findingsCount > 0 ? colors.amber : colors.textMuted }}>
            {project.findingsCount || 0}
          </div>
        </div>
        <div style={{ width: 60 }}>
          <div style={{ fontSize: '0.65rem', color: colors.textMuted, marginBottom: 4, textAlign: 'right' }}>HEALTH</div>
          <div style={{ 
            height: 6, 
            background: colors.inputBg, 
            borderRadius: 3,
            overflow: 'hidden',
          }}>
            <div style={{ 
              height: '100%', 
              width: `${project.health || 0}%`, 
              background: healthColor,
              borderRadius: 3,
            }} />
          </div>
        </div>
      </div>
    </div>
  );
}

// Activity Item
function ActivityItem({ item, colors }) {
  const getIcon = () => {
    if (item.status === 'completed') return <CheckCircle size={14} style={{ color: colors.primary }} />;
    if (item.status === 'failed') return <AlertTriangle size={14} style={{ color: colors.red }} />;
    return <Clock size={14} style={{ color: colors.amber }} />;
  };
  
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.75rem 0',
      borderBottom: `1px solid ${colors.divider}`,
    }}>
      {getIcon()}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ 
          fontSize: '0.85rem', 
          color: colors.text,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {item.filename}
        </div>
        <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>{item.project}</div>
      </div>
      <div style={{ fontSize: '0.75rem', color: colors.textLight }}>{item.time}</div>
    </div>
  );
}

// Quick Action Button
function QuickAction({ icon: Icon, label, onClick, colors }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.75rem 1.25rem',
        background: colors.card,
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: 8,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        color: colors.text,
        fontSize: '0.85rem',
        fontWeight: 500,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = colors.primary;
        e.currentTarget.style.background = colors.primaryLight;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = colors.cardBorder;
        e.currentTarget.style.background = colors.card;
      }}
    >
      <Icon size={18} style={{ color: colors.primary }} />
      {label}
    </button>
  );
}


export default function DashboardPage() {
  const navigate = useNavigate();
  const { projects: realProjects, activeProject, selectProject } = useProject();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [timePeriod, setTimePeriod] = useState('week');
  const [lastUpdated, setLastUpdated] = useState(new Date());
  
  // Stats
  const [stats, setStats] = useState({
    projects: 0,
    files: 0,
    playbooks: 0,
    findings: 0,
  });
  
  // Goals (could come from settings/API later)
  const goals = {
    projects: 10,
    files: 50,
    playbooks: 20,
    findings: 0, // lower is better
  };
  
  const [projectsData, setProjectsData] = useState([]);
  const [activityData, setActivityData] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);

  useEffect(() => {
    loadDashboardData();
  }, [realProjects, timePeriod]);

  const loadDashboardData = async () => {
    if (!refreshing) setLoading(true);
    try {
      // Get jobs for activity
      const jobsRes = await api.get('/jobs').catch(() => ({ data: { jobs: [] } }));
      const jobs = jobsRes.data.jobs || [];
      
      // Get structured data
      const structuredRes = await api.get('/status/structured').catch(() => ({ data: { files: [], total_files: 0 } }));
      
      // Calculate stats
      const totalProjects = realProjects?.length || 0;
      const filesUploaded = structuredRes.data.total_files || structuredRes.data.files?.length || 0;
      
      setStats({
        projects: totalProjects,
        files: filesUploaded,
        playbooks: 0, // Would come from playbooks endpoint
        findings: 0,  // Would come from playbooks endpoint
      });
      
      // Build projects list with mock health scores
      const projectsList = (realProjects || []).map((p, i) => ({
        ...p,
        health: 100 - (i * 8), // Mock decreasing health for demo
        fileCount: Math.floor(Math.random() * 10) + 1,
        findingsCount: Math.floor(Math.random() * 5),
      })).sort((a, b) => b.health - a.health);
      
      setProjectsData(projectsList.slice(0, 5));
      
      // Build activity chart data
      const days = timePeriod === 'week' ? 7 : 30;
      const dayLabels = timePeriod === 'week' 
        ? ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        : Array.from({ length: 30 }, (_, i) => i + 1);
      
      const chartData = dayLabels.map((label, i) => ({
        label: String(label),
        value: Math.floor(Math.random() * 8) + 1, // Mock data
        type: 'upload',
      }));
      setActivityData(chartData);
      
      // Recent activity from jobs
      const recent = jobs.slice(0, 5).map(j => ({
        type: j.job_type || 'upload',
        filename: j.input_data?.filename || j.filename || 'File',
        project: j.input_data?.project_name || j.project_id || 'Unknown',
        status: j.status,
        time: formatTimeAgo(j.created_at),
      }));
      setRecentActivity(recent);
      
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };
  
  const handleRefresh = () => {
    setRefreshing(true);
    loadDashboardData();
  };
  
  const formatTimeAgo = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  const handleProjectClick = (project) => {
    selectProject(project);
    navigate('/data');
  };

  return (
    <div style={{ 
      padding: '1.5rem', 
      background: colors.bg, 
      minHeight: 'calc(100vh - 60px)',
      fontFamily: "'Inter', system-ui, sans-serif",
      transition: 'background 0.2s ease',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ 
            fontSize: '1.5rem', 
            fontWeight: 700, 
            margin: 0, 
            color: colors.text,
            fontFamily: "'Sora', sans-serif",
          }}>
            Command Center
          </h1>
          <p style={{ color: colors.textMuted, margin: '0.25rem 0 0 0', fontSize: '0.875rem' }}>
            Welcome back! Here's your overview.
          </p>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <TabToggle 
            options={[
              { value: 'week', label: 'This Week' },
              { value: 'month', label: 'This Month' },
            ]}
            value={timePeriod}
            onChange={setTimePeriod}
            colors={colors}
          />
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.5rem 0.875rem',
              background: colors.card,
              border: `1px solid ${colors.cardBorder}`,
              borderRadius: 8,
              cursor: 'pointer',
              color: colors.textMuted,
              fontSize: '0.8rem',
            }}
          >
            <RefreshCw size={14} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
          <span style={{ fontSize: '0.75rem', color: colors.textLight }}>
            Last updated {lastUpdated.toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Stats Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        <StatCard 
          label="Projects" 
          value={stats.projects} 
          goal={goals.projects}
          icon={FolderOpen}
          colors={colors}
          onClick={() => navigate('/projects')}
        />
        <StatCard 
          label="Files Loaded" 
          value={stats.files} 
          goal={goals.files}
          icon={Upload}
          trend={12}
          colors={colors}
          onClick={() => navigate('/data')}
        />
        <StatCard 
          label="Playbooks" 
          value={stats.playbooks} 
          goal={goals.playbooks}
          icon={Zap}
          colors={colors}
          onClick={() => navigate('/playbooks')}
        />
        <StatCard 
          label="Open Findings" 
          value={stats.findings} 
          icon={AlertTriangle}
          colors={colors}
          onClick={() => navigate('/playbooks')}
        />
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '1.5rem' }}>
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Activity Chart */}
          <div style={{
            background: colors.card,
            border: `1px solid ${colors.cardBorder}`,
            borderRadius: 12,
            padding: '1.25rem',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: colors.text }}>
                  Activity
                </h3>
                <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.75rem', color: colors.textMuted }}>
                  File uploads and processing
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.75rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <span style={{ width: 10, height: 10, borderRadius: 2, background: colors.primary }} />
                  <span style={{ color: colors.textMuted }}>Uploads</span>
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <span style={{ width: 10, height: 10, borderRadius: 2, background: colors.blue }} />
                  <span style={{ color: colors.textMuted }}>Playbooks</span>
                </span>
              </div>
            </div>
            <BarChart data={activityData} colors={colors} height={140} />
          </div>

          {/* Projects Leaderboard */}
          <div style={{
            background: colors.card,
            border: `1px solid ${colors.cardBorder}`,
            borderRadius: 12,
            overflow: 'hidden',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}>
            <div style={{ 
              padding: '1rem 1.25rem', 
              borderBottom: `1px solid ${colors.divider}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: colors.text }}>
                Projects by Health
              </h3>
              <button
                onClick={() => navigate('/projects')}
                style={{
                  background: 'none',
                  border: 'none',
                  color: colors.primary,
                  fontSize: '0.8rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                View All <ArrowRight size={14} />
              </button>
            </div>
            
            {projectsData.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: colors.textMuted }}>
                <FolderOpen size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                <p style={{ margin: 0, fontSize: '0.9rem' }}>No projects yet</p>
                <button
                  onClick={() => navigate('/projects')}
                  style={{
                    marginTop: '1rem',
                    padding: '0.5rem 1rem',
                    background: colors.primary,
                    color: 'white',
                    border: 'none',
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: 500,
                  }}
                >
                  Create Project
                </button>
              </div>
            ) : (
              projectsData.map((project, i) => (
                <ProjectRow 
                  key={project.id} 
                  rank={i + 1}
                  project={project} 
                  colors={colors}
                  onClick={() => handleProjectClick(project)}
                  isSelected={activeProject?.id === project.id}
                />
              ))
            )}
          </div>
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Recent Activity */}
          <div style={{
            background: colors.card,
            border: `1px solid ${colors.cardBorder}`,
            borderRadius: 12,
            padding: '1.25rem',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}>
            <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '0.9rem', fontWeight: 600, color: colors.text }}>
              Recent Activity
            </h3>
            
            {recentActivity.length === 0 ? (
              <div style={{ padding: '1.5rem', textAlign: 'center', color: colors.textMuted, fontSize: '0.85rem' }}>
                No recent activity
              </div>
            ) : (
              <div>
                {recentActivity.map((item, i) => (
                  <ActivityItem key={i} item={item} colors={colors} />
                ))}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div style={{
            background: colors.card,
            border: `1px solid ${colors.cardBorder}`,
            borderRadius: 12,
            padding: '1.25rem',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '0.9rem', fontWeight: 600, color: colors.text }}>
              Quick Actions
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <QuickAction icon={Upload} label="Upload Data" onClick={() => navigate('/data')} colors={colors} />
              <QuickAction icon={Zap} label="Run Playbook" onClick={() => navigate('/playbooks')} colors={colors} />
              <QuickAction icon={MessageSquare} label="AI Assist" onClick={() => navigate('/workspace')} colors={colors} />
            </div>
          </div>

          {/* Calendar placeholder */}
          <div style={{
            background: colors.card,
            border: `1px solid ${colors.cardBorder}`,
            borderRadius: 12,
            padding: '1.25rem',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <Calendar size={16} style={{ color: colors.primary }} />
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: colors.text }}>
                Upcoming
              </h3>
            </div>
            <div style={{ fontSize: '0.85rem', color: colors.textMuted, textAlign: 'center', padding: '1rem 0' }}>
              No upcoming deadlines
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
