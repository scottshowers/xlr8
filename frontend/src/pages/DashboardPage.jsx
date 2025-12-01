/**
 * DashboardPage - Command Center for Implementation Consultants
 * 
 * - Hero with active project spotlight
 * - Playbook progress at a glance
 * - Smart quick actions based on context
 * - Activity feed with real insights
 */

import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import api from '../services/api';

// Brand Colors
const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  clearwater: '#b2d6de',
  turkishSea: '#285390',
  electricBlue: '#2766b1',
  iceFlow: '#c9d3d4',
  aquamarine: '#a1c3d4',
  white: '#f6f5fa',
  silver: '#a2a1a0',
  text: '#2a3441',
  textLight: '#5f6c7b',
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const { projects, selectProject, activeProject } = useProject();
  const [stats, setStats] = useState({ documents: 0, structured: 0, tables: 0, rows: 0 });
  const [recentJobs, setRecentJobs] = useState([]);
  const [playbookProgress, setPlaybookProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, [activeProject]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [docsRes, structuredRes, jobsRes] = await Promise.all([
        api.get('/status/documents'),
        api.get('/status/structured'),
        api.get('/jobs'),
      ]);

      setStats({
        documents: docsRes.data?.total || 0,
        chunks: docsRes.data?.total_chunks || 0,
        structured: structuredRes.data?.total_files || 0,
        tables: structuredRes.data?.total_tables || 0,
        rows: structuredRes.data?.total_rows || 0,
      });

      const jobs = jobsRes.data?.jobs || [];
      setRecentJobs(jobs.slice(0, 6));

      // Fetch playbook progress if active project
      if (activeProject?.id) {
        try {
          const progressRes = await api.get(`/playbooks/year-end/progress/${activeProject.id}`);
          const progress = progressRes.data?.progress || {};
          const total = 55; // Default action count
          const complete = Object.values(progress).filter(p => 
            p.status === 'complete' || p.status === 'na'
          ).length;
          const inProgress = Object.values(progress).filter(p => p.status === 'in_progress').length;
          
          setPlaybookProgress({ total, complete, inProgress });
        } catch (e) {
          setPlaybookProgress(null);
        }
      }
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const getProgressPercent = () => {
    if (!playbookProgress) return 0;
    return Math.round((playbookProgress.complete / playbookProgress.total) * 100);
  };

  const styles = {
    container: {
      maxWidth: '1400px',
      margin: '0 auto',
    },
    
    // Hero Section
    hero: {
      background: `linear-gradient(135deg, ${COLORS.turkishSea} 0%, ${COLORS.electricBlue} 100%)`,
      borderRadius: '20px',
      padding: '2.5rem',
      marginBottom: '2rem',
      color: 'white',
      position: 'relative',
      overflow: 'hidden',
    },
    heroPattern: {
      position: 'absolute',
      top: 0,
      right: 0,
      bottom: 0,
      width: '40%',
      opacity: 0.1,
      background: `repeating-linear-gradient(
        45deg,
        transparent,
        transparent 10px,
        rgba(255,255,255,0.1) 10px,
        rgba(255,255,255,0.1) 20px
      )`,
    },
    heroContent: {
      position: 'relative',
      zIndex: 1,
    },
    greeting: {
      fontSize: '0.9rem',
      opacity: 0.9,
      marginBottom: '0.5rem',
      fontWeight: '500',
    },
    heroTitle: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '2rem',
      fontWeight: '700',
      margin: '0 0 0.5rem 0',
    },
    heroSubtitle: {
      fontSize: '1rem',
      opacity: 0.9,
      maxWidth: '600px',
    },
    heroStats: {
      display: 'flex',
      gap: '3rem',
      marginTop: '2rem',
    },
    heroStat: {
      display: 'flex',
      flexDirection: 'column',
    },
    heroStatValue: {
      fontSize: '2rem',
      fontWeight: '700',
    },
    heroStatLabel: {
      fontSize: '0.85rem',
      opacity: 0.8,
    },

    // Main Grid
    mainGrid: {
      display: 'grid',
      gridTemplateColumns: '1fr 380px',
      gap: '1.5rem',
    },
    leftColumn: {
      display: 'flex',
      flexDirection: 'column',
      gap: '1.5rem',
    },
    rightColumn: {
      display: 'flex',
      flexDirection: 'column',
      gap: '1.5rem',
    },

    // Active Project Card
    projectSpotlight: {
      background: 'white',
      borderRadius: '16px',
      padding: '1.5rem',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
    },
    spotlightHeader: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      marginBottom: '1.5rem',
    },
    spotlightBadge: {
      background: COLORS.grassGreen,
      color: 'white',
      padding: '0.25rem 0.75rem',
      borderRadius: '20px',
      fontSize: '0.75rem',
      fontWeight: '600',
    },
    spotlightTitle: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.5rem',
      fontWeight: '700',
      color: COLORS.text,
      margin: '0.5rem 0 0.25rem 0',
    },
    spotlightCustomer: {
      color: COLORS.textLight,
      fontSize: '0.9rem',
    },
    changeProjectBtn: {
      background: 'none',
      border: `1px solid ${COLORS.iceFlow}`,
      padding: '0.4rem 0.75rem',
      borderRadius: '6px',
      fontSize: '0.8rem',
      color: COLORS.textLight,
      cursor: 'pointer',
    },

    // Playbook Progress
    progressSection: {
      marginTop: '1.5rem',
      padding: '1.25rem',
      background: `linear-gradient(135deg, ${COLORS.iceFlow}40 0%, ${COLORS.clearwater}40 100%)`,
      borderRadius: '12px',
    },
    progressHeader: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '1rem',
    },
    progressTitle: {
      fontWeight: '600',
      color: COLORS.text,
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    progressPercent: {
      fontSize: '1.25rem',
      fontWeight: '700',
      color: COLORS.grassGreen,
    },
    progressBar: {
      height: '10px',
      background: 'white',
      borderRadius: '5px',
      overflow: 'hidden',
      marginBottom: '0.75rem',
    },
    progressFill: (pct) => ({
      height: '100%',
      width: `${pct}%`,
      background: `linear-gradient(90deg, ${COLORS.grassGreen}, #6aa84f)`,
      borderRadius: '5px',
      transition: 'width 0.5s ease',
    }),
    progressStats: {
      display: 'flex',
      gap: '1.5rem',
      fontSize: '0.85rem',
    },
    progressStatItem: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.4rem',
      color: COLORS.textLight,
    },
    progressDot: (color) => ({
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      background: color,
    }),
    continueBtn: {
      marginTop: '1rem',
      width: '100%',
      padding: '0.75rem',
      background: COLORS.grassGreen,
      color: 'white',
      border: 'none',
      borderRadius: '8px',
      fontWeight: '600',
      fontSize: '0.9rem',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.5rem',
    },

    // Quick Actions Grid
    actionsCard: {
      background: 'white',
      borderRadius: '16px',
      padding: '1.5rem',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
    },
    cardTitle: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1rem',
      fontWeight: '700',
      color: COLORS.text,
      marginBottom: '1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    actionsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(3, 1fr)',
      gap: '1rem',
    },
    actionCard: (bg) => ({
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '1.25rem 1rem',
      background: bg,
      borderRadius: '12px',
      textDecoration: 'none',
      transition: 'transform 0.2s, box-shadow 0.2s',
      cursor: 'pointer',
    }),
    actionIcon: {
      fontSize: '1.75rem',
      marginBottom: '0.5rem',
    },
    actionLabel: {
      fontSize: '0.85rem',
      fontWeight: '600',
      color: COLORS.text,
      textAlign: 'center',
    },

    // Recent Projects Mini List
    projectsList: {
      background: 'white',
      borderRadius: '16px',
      padding: '1.5rem',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
    },
    projectItem: (isActive) => ({
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.75rem 1rem',
      marginBottom: '0.5rem',
      background: isActive ? `${COLORS.grassGreen}15` : '#f8fafc',
      border: isActive ? `2px solid ${COLORS.grassGreen}` : '2px solid transparent',
      borderRadius: '10px',
      cursor: 'pointer',
      transition: 'all 0.2s',
    }),
    projectInfo: {
      display: 'flex',
      flexDirection: 'column',
    },
    projectName: {
      fontWeight: '600',
      fontSize: '0.9rem',
      color: COLORS.text,
    },
    projectCustomer: {
      fontSize: '0.8rem',
      color: COLORS.textLight,
    },
    projectBadge: {
      fontSize: '0.7rem',
      padding: '0.2rem 0.5rem',
      borderRadius: '4px',
      background: COLORS.skyBlue + '30',
      color: COLORS.turkishSea,
      fontWeight: '600',
    },
    viewAllLink: {
      display: 'block',
      textAlign: 'center',
      marginTop: '0.75rem',
      color: COLORS.grassGreen,
      fontSize: '0.85rem',
      fontWeight: '600',
      textDecoration: 'none',
    },

    // Activity Feed
    activityCard: {
      background: 'white',
      borderRadius: '16px',
      padding: '1.5rem',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      flex: 1,
    },
    activityItem: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem',
      padding: '0.75rem 0',
      borderBottom: '1px solid #f0f4f7',
    },
    activityIcon: (status) => ({
      width: '32px',
      height: '32px',
      borderRadius: '8px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '1rem',
      background: status === 'complete' ? '#dcfce7' : status === 'failed' ? '#fee2e2' : '#fef3c7',
    }),
    activityContent: {
      flex: 1,
    },
    activityName: {
      fontSize: '0.9rem',
      fontWeight: '500',
      color: COLORS.text,
    },
    activityMeta: {
      fontSize: '0.8rem',
      color: COLORS.textLight,
      marginTop: '0.15rem',
    },
    activityStatus: (status) => ({
      fontSize: '0.7rem',
      padding: '0.15rem 0.4rem',
      borderRadius: '4px',
      fontWeight: '600',
      background: status === 'complete' ? '#dcfce7' : status === 'failed' ? '#fee2e2' : '#fef3c7',
      color: status === 'complete' ? '#166534' : status === 'failed' ? '#b91c1c' : '#92400e',
    }),
    
    // Empty State
    emptyState: {
      textAlign: 'center',
      padding: '2rem 1rem',
      color: COLORS.textLight,
    },
    emptyIcon: {
      fontSize: '2.5rem',
      marginBottom: '0.75rem',
      opacity: 0.3,
    },
    emptyText: {
      fontSize: '0.9rem',
      marginBottom: '1rem',
    },
    emptyAction: {
      display: 'inline-block',
      padding: '0.5rem 1rem',
      background: COLORS.grassGreen,
      color: 'white',
      borderRadius: '6px',
      textDecoration: 'none',
      fontWeight: '600',
      fontSize: '0.85rem',
    },

    // No project selected state
    noProjectHero: {
      background: `linear-gradient(135deg, ${COLORS.iceFlow} 0%, ${COLORS.clearwater} 100%)`,
      borderRadius: '20px',
      padding: '3rem 2.5rem',
      marginBottom: '2rem',
      textAlign: 'center',
    },
    noProjectTitle: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.75rem',
      fontWeight: '700',
      color: COLORS.text,
      marginBottom: '0.5rem',
    },
    noProjectText: {
      color: COLORS.textLight,
      marginBottom: '1.5rem',
    },
    selectProjectBtn: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.75rem 1.5rem',
      background: COLORS.turkishSea,
      color: 'white',
      border: 'none',
      borderRadius: '8px',
      fontWeight: '600',
      fontSize: '0.95rem',
      cursor: 'pointer',
      textDecoration: 'none',
    },
  };

  // No active project state
  if (!activeProject) {
    return (
      <div style={styles.container}>
        <div style={styles.noProjectHero}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🚀</div>
          <h1 style={styles.noProjectTitle}>{getGreeting()}! Ready to get started?</h1>
          <p style={styles.noProjectText}>Select a project to begin your implementation journey.</p>
          <Link to="/projects" style={styles.selectProjectBtn}>
            📁 Select a Project
          </Link>
        </div>

        {/* Still show recent projects for quick access */}
        <div style={styles.mainGrid}>
          <div style={styles.leftColumn}>
            <div style={styles.actionsCard}>
              <h3 style={styles.cardTitle}>⚡ Quick Actions</h3>
              <div style={styles.actionsGrid}>
                <Link to="/projects" style={styles.actionCard('#E8F5E9')}>
                  <span style={styles.actionIcon}>📁</span>
                  <span style={styles.actionLabel}>Projects</span>
                </Link>
                <Link to="/data" style={styles.actionCard('#E3F2FD')}>
                  <span style={styles.actionIcon}>📤</span>
                  <span style={styles.actionLabel}>Upload Data</span>
                </Link>
                <Link to="/playbooks" style={styles.actionCard('#FFF3E0')}>
                  <span style={styles.actionIcon}>📋</span>
                  <span style={styles.actionLabel}>Playbooks</span>
                </Link>
              </div>
            </div>
          </div>

          <div style={styles.rightColumn}>
            <div style={styles.projectsList}>
              <h3 style={styles.cardTitle}>🏢 Your Projects</h3>
              {projects.length === 0 ? (
                <div style={styles.emptyState}>
                  <div style={styles.emptyIcon}>📁</div>
                  <p style={styles.emptyText}>No projects yet</p>
                  <Link to="/projects" style={styles.emptyAction}>Create Project</Link>
                </div>
              ) : (
                <>
                  {projects.slice(0, 5).map((project) => (
                    <div
                      key={project.id}
                      style={styles.projectItem(false)}
                      onClick={() => selectProject(project)}
                    >
                      <div style={styles.projectInfo}>
                        <span style={styles.projectName}>{project.name}</span>
                        <span style={styles.projectCustomer}>{project.customer}</span>
                      </div>
                      <span style={styles.projectBadge}>{project.product || 'UKG Pro'}</span>
                    </div>
                  ))}
                  <Link to="/projects" style={styles.viewAllLink}>View All Projects →</Link>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const progressPct = getProgressPercent();

  return (
    <div style={styles.container}>
      {/* Hero Section */}
      <div style={styles.hero}>
        <div style={styles.heroPattern} />
        <div style={styles.heroContent}>
          <div style={styles.greeting}>{getGreeting()}</div>
          <h1 style={styles.heroTitle}>{activeProject.name}</h1>
          <p style={styles.heroSubtitle}>
            {activeProject.customer} • {activeProject.product || 'UKG Pro'} Implementation
          </p>
          <div style={styles.heroStats}>
            <div style={styles.heroStat}>
              <span style={styles.heroStatValue}>{stats.documents}</span>
              <span style={styles.heroStatLabel}>Documents</span>
            </div>
            <div style={styles.heroStat}>
              <span style={styles.heroStatValue}>{stats.structured}</span>
              <span style={styles.heroStatLabel}>Data Files</span>
            </div>
            <div style={styles.heroStat}>
              <span style={styles.heroStatValue}>{stats.tables}</span>
              <span style={styles.heroStatLabel}>Tables</span>
            </div>
            <div style={styles.heroStat}>
              <span style={styles.heroStatValue}>{(stats.rows || 0).toLocaleString()}</span>
              <span style={styles.heroStatLabel}>Rows</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div style={styles.mainGrid}>
        <div style={styles.leftColumn}>
          {/* Playbook Progress */}
          {playbookProgress && (
            <div style={styles.projectSpotlight}>
              <div style={styles.spotlightHeader}>
                <div>
                  <span style={styles.spotlightBadge}>📅 Year-End Playbook</span>
                  <h2 style={{ ...styles.spotlightTitle, fontSize: '1.1rem', marginTop: '0.75rem' }}>
                    Year-End Checklist Progress
                  </h2>
                </div>
                <span style={styles.progressPercent}>{progressPct}%</span>
              </div>
              
              <div style={styles.progressBar}>
                <div style={styles.progressFill(progressPct)} />
              </div>
              
              <div style={styles.progressStats}>
                <span style={styles.progressStatItem}>
                  <span style={styles.progressDot(COLORS.grassGreen)} />
                  {playbookProgress.complete} Complete
                </span>
                <span style={styles.progressStatItem}>
                  <span style={styles.progressDot('#f59e0b')} />
                  {playbookProgress.inProgress} In Progress
                </span>
                <span style={styles.progressStatItem}>
                  <span style={styles.progressDot('#e5e7eb')} />
                  {playbookProgress.total - playbookProgress.complete - playbookProgress.inProgress} Remaining
                </span>
              </div>
              
              <button 
                style={styles.continueBtn}
                onClick={() => navigate('/playbooks')}
              >
                Continue Playbook →
              </button>
            </div>
          )}

          {/* Quick Actions */}
          <div style={styles.actionsCard}>
            <h3 style={styles.cardTitle}>⚡ Quick Actions</h3>
            <div style={styles.actionsGrid}>
              <Link to="/data" style={styles.actionCard('#E3F2FD')}>
                <span style={styles.actionIcon}>📤</span>
                <span style={styles.actionLabel}>Upload Files</span>
              </Link>
              <Link to="/workspace" style={styles.actionCard('#F3E5F5')}>
                <span style={styles.actionIcon}>🤖</span>
                <span style={styles.actionLabel}>AI Assistant</span>
              </Link>
              <Link to="/playbooks" style={styles.actionCard('#FFF3E0')}>
                <span style={styles.actionIcon}>📋</span>
                <span style={styles.actionLabel}>Playbooks</span>
              </Link>
              <Link to="/vacuum" style={styles.actionCard('#E8F5E9')}>
                <span style={styles.actionIcon}>🧹</span>
                <span style={styles.actionLabel}>Vacuum Extract</span>
              </Link>
              <Link to="/data-model" style={styles.actionCard('#FFEBEE')}>
                <span style={styles.actionIcon}>🗂️</span>
                <span style={styles.actionLabel}>Data Model</span>
              </Link>
              <Link to="/projects" style={styles.actionCard('#ECEFF1')}>
                <span style={styles.actionIcon}>🔄</span>
                <span style={styles.actionLabel}>Switch Project</span>
              </Link>
            </div>
          </div>

          {/* Recent Activity */}
          <div style={styles.activityCard}>
            <h3 style={styles.cardTitle}>🕐 Recent Activity</h3>
            {recentJobs.length === 0 ? (
              <div style={styles.emptyState}>
                <div style={styles.emptyIcon}>📭</div>
                <p style={styles.emptyText}>No recent activity</p>
              </div>
            ) : (
              recentJobs.map((job) => (
                <div key={job.id} style={styles.activityItem}>
                  <div style={styles.activityIcon(job.status)}>
                    {job.status === 'complete' ? '✓' : job.status === 'failed' ? '✗' : '⏳'}
                  </div>
                  <div style={styles.activityContent}>
                    <div style={styles.activityName}>
                      {job.filename || job.job_type || 'Processing job'}
                    </div>
                    <div style={styles.activityMeta}>
                      {job.job_type} • {new Date(job.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <span style={styles.activityStatus(job.status)}>
                    {job.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div style={styles.rightColumn}>
          {/* Other Projects */}
          <div style={styles.projectsList}>
            <h3 style={styles.cardTitle}>🏢 Your Projects</h3>
            {projects.slice(0, 5).map((project) => (
              <div
                key={project.id}
                style={styles.projectItem(activeProject?.id === project.id)}
                onClick={() => selectProject(project)}
              >
                <div style={styles.projectInfo}>
                  <span style={styles.projectName}>{project.name}</span>
                  <span style={styles.projectCustomer}>{project.customer}</span>
                </div>
                {activeProject?.id === project.id ? (
                  <span style={{ ...styles.projectBadge, background: COLORS.grassGreen, color: 'white' }}>
                    Active
                  </span>
                ) : (
                  <span style={styles.projectBadge}>{project.product || 'UKG'}</span>
                )}
              </div>
            ))}
            <Link to="/projects" style={styles.viewAllLink}>Manage Projects →</Link>
          </div>

          {/* Tips or Help */}
          <div style={{ ...styles.actionsCard, background: `linear-gradient(135deg, ${COLORS.clearwater}30 0%, ${COLORS.aquamarine}30 100%)` }}>
            <h3 style={styles.cardTitle}>💡 Pro Tips</h3>
            <div style={{ fontSize: '0.85rem', color: COLORS.textLight, lineHeight: '1.6' }}>
              <p style={{ marginBottom: '0.75rem' }}>
                <strong>Year-End Checklist:</strong> Upload the Company Tax Verification and Earnings reports first — they unlock the most findings.
              </p>
              <p style={{ marginBottom: '0.75rem' }}>
                <strong>Scan Documents:</strong> Click "Scan" on each action to find relevant docs already uploaded.
              </p>
              <p>
                <strong>Export Anytime:</strong> Download your progress as an Excel workbook to share with the customer.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
