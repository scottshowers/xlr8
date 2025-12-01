/**
 * DashboardPage - Overview Hub
 * 
 * Shows:
 * - Recent projects (quick select)
 * - Recent activity / uploads
 * - Processing jobs status
 * - Quick stats
 * - Shortcuts to common actions
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import api from '../services/api';

export default function DashboardPage() {
  const { projects, selectProject, activeProject } = useProject();
  const [stats, setStats] = useState({ documents: 0, chunks: 0, structured: 0, jobs: 0 });
  const [recentJobs, setRecentJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // Fetch documents stats
      const docsRes = await api.get('/status/documents');
      const structuredRes = await api.get('/status/structured');
      const jobsRes = await api.get('/jobs');

      setStats({
        documents: docsRes.data?.total || 0,
        chunks: docsRes.data?.total_chunks || 0,
        structured: structuredRes.data?.total_files || 0,
        tables: structuredRes.data?.total_tables || 0,
        rows: structuredRes.data?.total_rows || 0,
      });

      // Get recent jobs (last 5)
      const jobs = jobsRes.data?.jobs || [];
      setRecentJobs(jobs.slice(0, 5));
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const styles = {
    container: {
      maxWidth: '1200px',
    },
    header: {
      marginBottom: '1.5rem',
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.75rem',
      fontWeight: '700',
      color: '#2a3441',
      margin: 0,
    },
    subtitle: {
      color: '#5f6c7b',
      marginTop: '0.25rem',
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
      gap: '1.5rem',
      marginBottom: '1.5rem',
    },
    card: {
      background: 'white',
      borderRadius: '16px',
      boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
      padding: '1.5rem',
    },
    cardHeader: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '1rem',
    },
    cardTitle: {
      fontSize: '1rem',
      fontWeight: '700',
      color: '#2a3441',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    cardLink: {
      fontSize: '0.8rem',
      color: '#83b16d',
      textDecoration: 'none',
      fontWeight: '600',
    },
    statGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: '1rem',
    },
    stat: {
      textAlign: 'center',
      padding: '1rem',
      background: '#f8fafc',
      borderRadius: '12px',
    },
    statValue: {
      fontSize: '1.75rem',
      fontWeight: '700',
      color: '#83b16d',
    },
    statLabel: {
      fontSize: '0.8rem',
      color: '#5f6c7b',
      marginTop: '0.25rem',
    },
    projectCard: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.75rem 1rem',
      background: '#f8fafc',
      borderRadius: '8px',
      marginBottom: '0.5rem',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      border: '2px solid transparent',
    },
    projectCardActive: {
      border: '2px solid #83b16d',
      background: '#f0fdf4',
    },
    projectInfo: {
      display: 'flex',
      flexDirection: 'column',
    },
    projectName: {
      fontWeight: '600',
      color: '#2a3441',
      fontSize: '0.9rem',
    },
    projectCustomer: {
      fontSize: '0.8rem',
      color: '#5f6c7b',
    },
    projectBadge: {
      fontSize: '0.7rem',
      padding: '0.2rem 0.5rem',
      borderRadius: '4px',
      background: '#dbeafe',
      color: '#1e40af',
      fontWeight: '600',
    },
    jobItem: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.75rem 0',
      borderBottom: '1px solid #e1e8ed',
    },
    jobInfo: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
    },
    jobIcon: {
      fontSize: '1.25rem',
    },
    jobName: {
      fontSize: '0.9rem',
      color: '#2a3441',
      fontWeight: '500',
    },
    jobStatus: (status) => ({
      fontSize: '0.75rem',
      padding: '0.2rem 0.5rem',
      borderRadius: '4px',
      fontWeight: '600',
      background: status === 'complete' ? '#dcfce7' : status === 'failed' ? '#fee2e2' : '#fef3c7',
      color: status === 'complete' ? '#166534' : status === 'failed' ? '#b91c1c' : '#92400e',
    }),
    quickActions: {
      display: 'grid',
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: '0.75rem',
    },
    actionBtn: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '1rem',
      background: '#f8fafc',
      border: 'none',
      borderRadius: '10px',
      color: '#2a3441',
      fontSize: '0.9rem',
      fontWeight: '600',
      textDecoration: 'none',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
    },
    actionIcon: {
      fontSize: '1.25rem',
    },
    emptyState: {
      textAlign: 'center',
      padding: '2rem',
      color: '#5f6c7b',
    },
    emptyIcon: {
      fontSize: '2rem',
      marginBottom: '0.5rem',
      opacity: 0.5,
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>Dashboard</h1>
        <p style={styles.subtitle}>
          Welcome back! Here's an overview of your workspace.
          {activeProject && <span> • Active: <strong>{activeProject.name}</strong></span>}
        </p>
      </div>

      <div style={styles.grid}>
        {/* Quick Stats */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>📊 Quick Stats</h3>
          </div>
          {loading ? (
            <div style={styles.emptyState}>Loading...</div>
          ) : (
            <div style={styles.statGrid}>
              <div style={styles.stat}>
                <div style={styles.statValue}>{stats.documents}</div>
                <div style={styles.statLabel}>Documents</div>
              </div>
              <div style={styles.stat}>
                <div style={styles.statValue}>{stats.structured}</div>
                <div style={styles.statLabel}>Data Files</div>
              </div>
              <div style={styles.stat}>
                <div style={styles.statValue}>{stats.tables || 0}</div>
                <div style={styles.statLabel}>Tables</div>
              </div>
              <div style={styles.stat}>
                <div style={styles.statValue}>{(stats.rows || 0).toLocaleString()}</div>
                <div style={styles.statLabel}>Data Rows</div>
              </div>
            </div>
          )}
        </div>

        {/* Recent Projects */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>🏢 Recent Projects</h3>
            <Link to="/projects" style={styles.cardLink}>View All →</Link>
          </div>
          {projects.length === 0 ? (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>📁</div>
              <p>No projects yet</p>
              <Link to="/projects" style={{ color: '#83b16d', fontWeight: '600' }}>Create one →</Link>
            </div>
          ) : (
            projects.slice(0, 4).map((project) => (
              <div
                key={project.id}
                style={{
                  ...styles.projectCard,
                  ...(activeProject?.id === project.id ? styles.projectCardActive : {}),
                }}
                onClick={() => selectProject(project)}
              >
                <div style={styles.projectInfo}>
                  <span style={styles.projectName}>{project.name}</span>
                  <span style={styles.projectCustomer}>{project.customer}</span>
                </div>
                <span style={styles.projectBadge}>{project.product || 'UKG'}</span>
              </div>
            ))
          )}
        </div>

        {/* Quick Actions */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>⚡ Quick Actions</h3>
          </div>
          <div style={styles.quickActions}>
            <Link to="/data" style={styles.actionBtn}>
              <span style={styles.actionIcon}>📤</span>
              Upload Files
            </Link>
            <Link to="/vacuum" style={styles.actionBtn}>
              <span style={styles.actionIcon}>🧹</span>
              Vacuum Extract
            </Link>
            <Link to="/workspace" style={styles.actionBtn}>
              <span style={styles.actionIcon}>💬</span>
              Chat
            </Link>
            <Link to="/playbooks" style={styles.actionBtn}>
              <span style={styles.actionIcon}>📋</span>
              Playbooks
            </Link>
          </div>
        </div>

        {/* Recent Activity */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h3 style={styles.cardTitle}>🕐 Recent Activity</h3>
            <Link to="/data" style={styles.cardLink}>View All →</Link>
          </div>
          {recentJobs.length === 0 ? (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>📭</div>
              <p>No recent activity</p>
            </div>
          ) : (
            recentJobs.map((job) => (
              <div key={job.id} style={styles.jobItem}>
                <div style={styles.jobInfo}>
                  <span style={styles.jobIcon}>
                    {job.status === 'complete' ? '✅' : job.status === 'failed' ? '❌' : '⏳'}
                  </span>
                  <span style={styles.jobName}>{job.filename || job.job_type}</span>
                </div>
                <span style={styles.jobStatus(job.status)}>{job.status}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
