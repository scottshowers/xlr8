/**
 * DashboardPage.jsx - Command Center (Clean Professional)
 * 
 * Clean, muted design with meaningful charts:
 * - Project health horizontal bars
 * - Weekly activity area chart
 * - Findings donut chart
 * 
 * Real data from existing endpoints
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import api from '../services/api';
import { 
  Upload, Zap, MessageSquare, FolderOpen, 
  AlertTriangle, CheckCircle, Clock, ArrowRight,
  FileText, Database, TrendingUp, Activity, BarChart3
} from 'lucide-react';

// Muted professional colors
const COLORS = {
  primary: '#83b16d',      // XLR8 green
  primaryMuted: '#a8ca99',
  blue: '#5b8fb9',
  amber: '#d4a054',
  red: '#c76b6b',
  purple: '#8b7bb8',
  text: '#2a3441',
  textMuted: '#6b7785',
  border: '#e2e8f0',
  bgCard: '#ffffff',
  bgPage: '#f8fafc',
};

// Simple horizontal bar component
function HealthBar({ label, value, maxValue = 100, color = COLORS.primary }) {
  const percentage = Math.min((value / maxValue) * 100, 100);
  
  return (
    <div style={{ marginBottom: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
        <span style={{ fontSize: '0.85rem', color: COLORS.text, fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: '0.85rem', color: COLORS.textMuted }}>{value}%</span>
      </div>
      <div style={{ 
        height: 8, 
        background: '#f1f5f9', 
        borderRadius: 4,
        overflow: 'hidden',
      }}>
        <div style={{ 
          height: '100%', 
          width: `${percentage}%`, 
          background: color,
          borderRadius: 4,
          transition: 'width 0.6s ease-out',
        }} />
      </div>
    </div>
  );
}

// Simple area chart component
function AreaChart({ data, width = 280, height = 120 }) {
  if (!data || data.length === 0) return null;
  
  const max = Math.max(...data.map(d => d.value), 1);
  const padding = { top: 10, right: 10, bottom: 25, left: 10 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  
  const points = data.map((d, i) => ({
    x: padding.left + (i / (data.length - 1)) * chartWidth,
    y: padding.top + chartHeight - (d.value / max) * chartHeight,
  }));
  
  // Create path for area
  const areaPath = `
    M ${points[0].x} ${padding.top + chartHeight}
    L ${points.map(p => `${p.x} ${p.y}`).join(' L ')}
    L ${points[points.length - 1].x} ${padding.top + chartHeight}
    Z
  `;
  
  // Create path for line
  const linePath = `M ${points.map(p => `${p.x} ${p.y}`).join(' L ')}`;
  
  return (
    <svg width={width} height={height}>
      {/* Gradient definition */}
      <defs>
        <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={COLORS.primary} stopOpacity="0.3" />
          <stop offset="100%" stopColor={COLORS.primary} stopOpacity="0.05" />
        </linearGradient>
      </defs>
      
      {/* Area fill */}
      <path d={areaPath} fill="url(#areaGradient)" />
      
      {/* Line */}
      <path d={linePath} fill="none" stroke={COLORS.primary} strokeWidth="2" strokeLinecap="round" />
      
      {/* Data points */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3" fill={COLORS.bgCard} stroke={COLORS.primary} strokeWidth="2" />
      ))}
      
      {/* X-axis labels */}
      {data.map((d, i) => (
        <text 
          key={i} 
          x={points[i].x} 
          y={height - 5} 
          textAnchor="middle" 
          fontSize="10" 
          fill={COLORS.textMuted}
        >
          {d.label}
        </text>
      ))}
    </svg>
  );
}

// Simple donut chart component
function DonutChart({ data, size = 140 }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  if (total === 0) {
    // Empty state
    return (
      <div style={{ width: size, height: size, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ 
          width: size * 0.7, 
          height: size * 0.7, 
          borderRadius: '50%', 
          border: `8px solid #f1f5f9`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: COLORS.textMuted,
          fontSize: '0.75rem',
        }}>
          No data
        </div>
      </div>
    );
  }
  
  const radius = size / 2;
  const strokeWidth = 24;
  const innerRadius = radius - strokeWidth / 2;
  const circumference = 2 * Math.PI * innerRadius;
  
  let currentOffset = 0;
  
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        {data.map((segment, i) => {
          const segmentLength = (segment.value / total) * circumference;
          const offset = currentOffset;
          currentOffset += segmentLength;
          
          return (
            <circle
              key={i}
              cx={radius}
              cy={radius}
              r={innerRadius}
              fill="none"
              stroke={segment.color}
              strokeWidth={strokeWidth}
              strokeDasharray={`${segmentLength} ${circumference}`}
              strokeDashoffset={-offset}
              style={{ transition: 'stroke-dasharray 0.6s ease-out' }}
            />
          );
        })}
      </svg>
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: '1.5rem', fontWeight: 700, color: COLORS.text }}>{total}</div>
        <div style={{ fontSize: '0.7rem', color: COLORS.textMuted }}>Total</div>
      </div>
    </div>
  );
}

// Stat card component
function StatCard({ label, value, icon: Icon, subtitle, onClick }) {
  return (
    <div 
      onClick={onClick}
      style={{ 
        background: COLORS.bgCard, 
        border: `1px solid ${COLORS.border}`, 
        borderRadius: 12, 
        padding: '1.25rem',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s ease',
      }}
      onMouseEnter={(e) => onClick && (e.currentTarget.style.borderColor = COLORS.primary)}
      onMouseLeave={(e) => onClick && (e.currentTarget.style.borderColor = COLORS.border)}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: COLORS.textMuted, marginBottom: '0.5rem', fontWeight: 500 }}>
            {label}
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: COLORS.text, lineHeight: 1 }}>
            {value}
          </div>
          {subtitle && (
            <div style={{ fontSize: '0.75rem', color: COLORS.textMuted, marginTop: '0.35rem' }}>
              {subtitle}
            </div>
          )}
        </div>
        <div style={{ 
          width: 40, 
          height: 40, 
          borderRadius: 10, 
          background: '#f1f5f9',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Icon size={20} style={{ color: COLORS.primary }} />
        </div>
      </div>
    </div>
  );
}

// Project row component
function ProjectRow({ project, onClick, isSelected }) {
  const healthColor = project.health >= 80 ? COLORS.primary : project.health >= 50 ? COLORS.amber : COLORS.red;
  
  return (
    <div 
      onClick={onClick}
      style={{ 
        display: 'flex', 
        alignItems: 'center', 
        padding: '0.875rem 1rem',
        borderBottom: `1px solid ${COLORS.border}`,
        cursor: 'pointer',
        background: isSelected ? '#f0fdf4' : 'transparent',
        transition: 'background 0.15s ease',
      }}
      onMouseEnter={(e) => !isSelected && (e.currentTarget.style.background = '#fafbfc')}
      onMouseLeave={(e) => !isSelected && (e.currentTarget.style.background = 'transparent')}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, color: COLORS.text, fontSize: '0.9rem' }}>{project.name}</div>
        <div style={{ fontSize: '0.75rem', color: COLORS.textMuted }}>{project.customer || 'No customer'}</div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.7rem', color: COLORS.textMuted }}>Playbooks</div>
          <div style={{ fontSize: '0.9rem', fontWeight: 600, color: COLORS.blue }}>{project.playbookCount || 0}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.7rem', color: COLORS.textMuted }}>Findings</div>
          <div style={{ fontSize: '0.9rem', fontWeight: 600, color: project.findingsCount > 0 ? COLORS.amber : COLORS.textMuted }}>
            {project.findingsCount || 0}
          </div>
        </div>
        <div style={{ 
          width: 50,
          height: 6, 
          background: '#f1f5f9', 
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
        <ArrowRight size={16} style={{ color: COLORS.textMuted }} />
      </div>
    </div>
  );
}

// Quick action button
function QuickAction({ icon: Icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '1rem',
        background: COLORS.bgCard,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 12,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        flex: 1,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = COLORS.primary;
        e.currentTarget.style.background = '#f0fdf4';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = COLORS.border;
        e.currentTarget.style.background = COLORS.bgCard;
      }}
    >
      <Icon size={22} style={{ color: COLORS.primary }} />
      <span style={{ fontSize: '0.8rem', fontWeight: 500, color: COLORS.text }}>{label}</span>
    </button>
  );
}


export default function DashboardPage() {
  const navigate = useNavigate();
  const { projects: realProjects, activeProject, selectProject } = useProject();
  
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalProjects: 0,
    activePlaybooks: 0,
    pendingFindings: 0,
    filesUploaded: 0,
  });
  const [projectsWithHealth, setProjectsWithHealth] = useState([]);
  const [weeklyActivity, setWeeklyActivity] = useState([]);
  const [findingsBreakdown, setFindingsBreakdown] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);

  useEffect(() => {
    loadDashboardData();
  }, [realProjects]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      // Get jobs for activity data
      const jobsRes = await api.get('/jobs').catch(() => ({ data: { jobs: [] } }));
      const jobs = jobsRes.data.jobs || [];
      
      // Get structured data for file counts
      const structuredRes = await api.get('/status/structured').catch(() => ({ data: { files: [], total_files: 0 } }));
      
      // Get playbook stats if available
      let playbookStats = { total: 0, findings: [] };
      try {
        const playbookRes = await api.get('/playbooks/stats');
        playbookStats = playbookRes.data || playbookStats;
      } catch {}
      
      // Calculate stats
      const totalProjects = realProjects?.length || 0;
      const filesUploaded = structuredRes.data.total_files || structuredRes.data.files?.length || 0;
      
      // Build projects with health scores
      const projectsHealth = (realProjects || []).map(p => ({
        ...p,
        health: 100, // Will be updated per-project if we have integrity data
        playbookCount: 0,
        findingsCount: 0,
      }));
      
      // Try to get per-project health
      for (const proj of projectsHealth) {
        try {
          const integrityRes = await api.get(`/status/data-integrity?project=${proj.id}`);
          if (integrityRes.data && !integrityRes.data.error) {
            const { tables_checked, tables_with_issues } = integrityRes.data;
            if (tables_checked > 0) {
              proj.health = Math.round(((tables_checked - tables_with_issues) / tables_checked) * 100);
            }
          }
        } catch {}
      }
      
      setProjectsWithHealth(projectsHealth.slice(0, 6));
      
      // Build weekly activity from jobs
      const now = new Date();
      const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const weekData = [];
      
      for (let i = 6; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        const dayStart = new Date(date.setHours(0, 0, 0, 0));
        const dayEnd = new Date(date.setHours(23, 59, 59, 999));
        
        const dayJobs = jobs.filter(j => {
          const jobDate = new Date(j.created_at);
          return jobDate >= dayStart && jobDate <= dayEnd;
        });
        
        weekData.push({
          label: dayNames[dayStart.getDay()],
          value: dayJobs.length,
        });
      }
      setWeeklyActivity(weekData);
      
      // Findings breakdown (mocked structure - would come from playbooks endpoint)
      const findings = playbookStats.findings || [];
      const resolved = findings.filter(f => f.status === 'resolved').length;
      const pending = findings.filter(f => f.status === 'pending' || !f.status).length;
      const newFindings = findings.filter(f => f.status === 'new').length;
      
      setFindingsBreakdown([
        { label: 'Resolved', value: resolved || 0, color: COLORS.primary },
        { label: 'Pending', value: pending || 0, color: COLORS.amber },
        { label: 'New', value: newFindings || 0, color: COLORS.blue },
      ]);
      
      // Recent activity from jobs
      const recent = jobs.slice(0, 5).map(j => ({
        type: j.job_type || 'upload',
        filename: j.input_data?.filename || j.filename || 'File',
        project: j.input_data?.project_name || j.project_id || 'Unknown',
        status: j.status,
        time: formatTimeAgo(j.created_at),
      }));
      setRecentActivity(recent);
      
      setStats({
        totalProjects,
        activePlaybooks: playbookStats.total || 0,
        pendingFindings: pending || 0,
        filesUploaded,
      });
      
    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
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
      background: COLORS.bgPage, 
      minHeight: 'calc(100vh - 60px)',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ 
          fontSize: '1.5rem', 
          fontWeight: 700, 
          margin: 0, 
          color: COLORS.text,
          fontFamily: "'Sora', sans-serif",
        }}>
          Command Center
        </h1>
        <p style={{ color: COLORS.textMuted, margin: '0.25rem 0 0 0', fontSize: '0.875rem' }}>
          Overview of your XLR8 workspace
        </p>
      </div>

      {/* Stats Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        <StatCard 
          label="Projects" 
          value={stats.totalProjects} 
          icon={FolderOpen}
          subtitle="Active engagements"
          onClick={() => navigate('/projects')}
        />
        <StatCard 
          label="Files Loaded" 
          value={stats.filesUploaded} 
          icon={Database}
          subtitle="Across all projects"
          onClick={() => navigate('/data')}
        />
        <StatCard 
          label="Playbooks" 
          value={stats.activePlaybooks} 
          icon={Zap}
          subtitle="Configured"
          onClick={() => navigate('/playbooks')}
        />
        <StatCard 
          label="Pending Findings" 
          value={stats.pendingFindings} 
          icon={AlertTriangle}
          subtitle="Require attention"
          onClick={() => navigate('/playbooks')}
        />
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: '1.5rem' }}>
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Projects List */}
          <div style={{ background: COLORS.bgCard, border: `1px solid ${COLORS.border}`, borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ 
              padding: '1rem 1.25rem', 
              borderBottom: `1px solid ${COLORS.border}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <h2 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: COLORS.text }}>Projects</h2>
              <button
                onClick={() => navigate('/projects')}
                style={{
                  background: 'none',
                  border: 'none',
                  color: COLORS.primary,
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
            
            {projectsWithHealth.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: COLORS.textMuted }}>
                <FolderOpen size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                <p style={{ margin: 0 }}>No projects yet</p>
                <button
                  onClick={() => navigate('/projects')}
                  style={{
                    marginTop: '1rem',
                    padding: '0.5rem 1rem',
                    background: COLORS.primary,
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
              projectsWithHealth.map(project => (
                <ProjectRow 
                  key={project.id} 
                  project={project} 
                  onClick={() => handleProjectClick(project)}
                  isSelected={activeProject?.id === project.id}
                />
              ))
            )}
          </div>

          {/* Recent Activity */}
          <div style={{ background: COLORS.bgCard, border: `1px solid ${COLORS.border}`, borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ 
              padding: '1rem 1.25rem', 
              borderBottom: `1px solid ${COLORS.border}`,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}>
              <Activity size={16} style={{ color: COLORS.primary }} />
              <h2 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: COLORS.text }}>Recent Activity</h2>
            </div>
            
            {recentActivity.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: COLORS.textMuted, fontSize: '0.85rem' }}>
                No recent activity
              </div>
            ) : (
              <div>
                {recentActivity.map((item, i) => (
                  <div key={i} style={{ 
                    padding: '0.75rem 1.25rem', 
                    borderBottom: i < recentActivity.length - 1 ? `1px solid ${COLORS.border}` : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                  }}>
                    {item.status === 'completed' ? (
                      <CheckCircle size={16} style={{ color: COLORS.primary }} />
                    ) : item.status === 'failed' ? (
                      <AlertTriangle size={16} style={{ color: COLORS.red }} />
                    ) : (
                      <Clock size={16} style={{ color: COLORS.amber }} />
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.85rem', color: COLORS.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.filename}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: COLORS.textMuted }}>{item.project}</div>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: COLORS.textMuted }}>{item.time}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Charts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Weekly Activity Chart */}
          <div style={{ background: COLORS.bgCard, border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <BarChart3 size={16} style={{ color: COLORS.primary }} />
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: COLORS.text }}>Weekly Activity</h3>
            </div>
            <AreaChart data={weeklyActivity} width={320} height={130} />
            <div style={{ fontSize: '0.75rem', color: COLORS.textMuted, marginTop: '0.5rem' }}>
              File uploads and processing jobs
            </div>
          </div>

          {/* Findings Breakdown */}
          <div style={{ background: COLORS.bgCard, border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: '1.25rem' }}>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '0.9rem', fontWeight: 600, color: COLORS.text }}>Findings Overview</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
              <DonutChart data={findingsBreakdown} size={120} />
              <div style={{ flex: 1 }}>
                {findingsBreakdown.map((item, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <div style={{ width: 10, height: 10, borderRadius: 2, background: item.color }} />
                    <span style={{ fontSize: '0.8rem', color: COLORS.textMuted, flex: 1 }}>{item.label}</span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: COLORS.text }}>{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Data Health Summary */}
          <div style={{ background: COLORS.bgCard, border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: COLORS.text }}>Data Health</h3>
              <button
                onClick={() => navigate('/data-health')}
                style={{
                  background: 'none',
                  border: 'none',
                  color: COLORS.primary,
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                Details →
              </button>
            </div>
            {projectsWithHealth.slice(0, 4).map((project, i) => (
              <HealthBar 
                key={i}
                label={project.name} 
                value={project.health} 
                color={project.health >= 80 ? COLORS.primary : project.health >= 50 ? COLORS.amber : COLORS.red}
              />
            ))}
            {projectsWithHealth.length === 0 && (
              <div style={{ fontSize: '0.85rem', color: COLORS.textMuted, textAlign: 'center', padding: '1rem' }}>
                No projects to analyze
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ marginTop: '1.5rem' }}>
        <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '0.8rem', fontWeight: 600, color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Quick Actions
        </h3>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <QuickAction icon={Upload} label="Upload Data" onClick={() => navigate('/data')} />
          <QuickAction icon={Zap} label="Run Playbook" onClick={() => navigate('/playbooks')} />
          <QuickAction icon={MessageSquare} label="AI Assist" onClick={() => navigate('/workspace')} />
          <QuickAction icon={FileText} label="Reference Library" onClick={() => navigate('/reference-library')} />
        </div>
      </div>
    </div>
  );
}
