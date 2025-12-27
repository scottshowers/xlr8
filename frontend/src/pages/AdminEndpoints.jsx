/**
 * AdminEndpoints.jsx
 * ===================
 * 
 * Reference page for all API endpoints - kept up to date by Claude
 * 
 * Deploy to: frontend/src/pages/AdminEndpoints.jsx
 * 
 * Add route in App.jsx:
 *   import AdminEndpoints from './pages/AdminEndpoints';
 *   <Route path="/admin/endpoints" element={<AdminEndpoints />} />
 * 
 * Add to navigation (AdminLayout or sidebar):
 *   { path: '/admin/endpoints', label: 'API Endpoints', icon: '🔗' }
 * 
 * Last Updated: December 27, 2025
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ExternalLink, Copy, Check, RefreshCw, Trash2, Eye, Database, FileText, Zap, Shield, Settings } from 'lucide-react';

// =============================================================================
// CONFIGURATION - UPDATE THIS WHEN ENDPOINTS CHANGE
// =============================================================================

const PRODUCTION_URL = 'https://hcmpact-xlr8-production.up.railway.app';

const ENDPOINT_CATEGORIES = [
  {
    id: 'health',
    name: 'Health & Status',
    icon: '💚',
    description: 'System health checks and status endpoints',
    endpoints: [
      { method: 'GET', path: '/api/health', description: 'Full system health check', priority: 'high' },
      { method: 'GET', path: '/api/debug/imports', description: 'Check if all modules loaded correctly', priority: 'high' },
      { method: 'GET', path: '/api/status/structured', description: 'List all DuckDB tables', priority: 'high' },
      { method: 'GET', path: '/api/status/documents', description: 'List all ChromaDB documents', priority: 'medium' },
    ]
  },
  {
    id: 'classification',
    name: 'Classification (FIVE TRUTHS)',
    icon: '🔍',
    description: 'Table classification and transparency endpoints',
    endpoints: [
      { method: 'GET', path: '/api/classification/health', description: 'Classification service health', priority: 'high' },
      { method: 'GET', path: '/api/classification/tables', description: 'List all tables with classifications', priority: 'high' },
      { method: 'GET', path: '/api/classification/table/{table_name}', description: 'Full classification for one table', priority: 'high', param: 'table_name' },
      { method: 'GET', path: '/api/classification/column/{table_name}/{column_name}', description: 'Column detail with all values', priority: 'medium', param: 'table_name,column_name' },
      { method: 'GET', path: '/api/classification/chunks', description: 'List all documents with chunk counts', priority: 'medium' },
      { method: 'GET', path: '/api/classification/chunks/{document_name}', description: 'All chunks for a document', priority: 'medium', param: 'document_name' },
      { method: 'GET', path: '/api/classification/routing', description: 'Recent routing decisions (debug)', priority: 'low' },
    ]
  },
  {
    id: 'cleanup',
    name: 'Cleanup & Deletion',
    icon: '🗑️',
    description: 'Data deletion and cleanup endpoints',
    endpoints: [
      { method: 'GET', path: '/api/deep-clean/preview', description: 'Preview orphaned data (safe)', priority: 'high' },
      { method: 'POST', path: '/api/deep-clean?confirm=true', description: 'Deep clean all orphans (DESTRUCTIVE)', priority: 'high', dangerous: true },
      { method: 'POST', path: '/api/deep-clean?confirm=true&force=true', description: 'Force full wipe (VERY DESTRUCTIVE)', priority: 'low', dangerous: true },
      { method: 'DELETE', path: '/api/status/structured/table/{table_name}', description: 'Delete one DuckDB table by exact name', priority: 'medium', param: 'table_name', dangerous: true },
      { method: 'DELETE', path: '/api/status/structured/{project_id}/{filename}', description: 'Delete structured file by project + filename', priority: 'medium', param: 'project_id, filename', dangerous: true },
      { method: 'DELETE', path: '/api/status/documents/{filename}', description: 'Delete one document from ChromaDB', priority: 'medium', param: 'filename', dangerous: true },
      { method: 'DELETE', path: '/api/status/project/{project_id}/all', description: 'Delete ALL data for a project', priority: 'low', param: 'project_id', dangerous: true },
      { method: 'POST', path: '/api/status/refresh-metrics', description: 'Clean orphaned metadata entries', priority: 'medium' },
      { method: 'DELETE', path: '/api/jobs/{job_id}', description: 'Delete single job by ID', priority: 'low', param: 'job_id', dangerous: true },
      { method: 'DELETE', path: '/api/jobs/all', description: 'Delete all job history', priority: 'low', dangerous: true },
    ]
  },
  {
    id: 'intelligence',
    name: 'Intelligence Engine',
    icon: '🧠',
    description: 'Query routing and analysis endpoints',
    endpoints: [
      { method: 'POST', path: '/api/intelligence/query', description: 'Execute intelligent query', priority: 'high' },
      { method: 'GET', path: '/api/intelligence/schema/{project_id}', description: 'Get project schema for routing', priority: 'medium', param: 'project_id' },
    ]
  },
  {
    id: 'metrics',
    name: 'Metrics & Analytics',
    icon: '📊',
    description: 'Platform metrics for dashboards',
    endpoints: [
      { method: 'GET', path: '/api/metrics/summary', description: 'Platform summary metrics', priority: 'medium' },
      { method: 'GET', path: '/api/metrics/usage', description: 'Usage statistics', priority: 'low' },
    ]
  },
  {
    id: 'upload',
    name: 'Upload & Processing',
    icon: '📤',
    description: 'File upload and processing endpoints',
    endpoints: [
      { method: 'POST', path: '/api/upload/smart', description: 'Unified smart upload endpoint', priority: 'high' },
      { method: 'GET', path: '/api/progress/{job_id}', description: 'SSE progress stream for upload', priority: 'medium', param: 'job_id' },
    ]
  },
  {
    id: 'projects',
    name: 'Projects',
    icon: '📁',
    description: 'Project management endpoints',
    endpoints: [
      { method: 'GET', path: '/api/projects', description: 'List all projects', priority: 'medium' },
      { method: 'GET', path: '/api/projects/{project_id}', description: 'Get project details', priority: 'medium', param: 'project_id' },
    ]
  },
];

// =============================================================================
// COMPONENT
// =============================================================================

export default function AdminEndpoints() {
  const [copiedUrl, setCopiedUrl] = useState(null);
  const [expandedCategory, setExpandedCategory] = useState('health');
  const [filterPriority, setFilterPriority] = useState('all');

  const isDark = document.documentElement.classList.contains('dark') || 
                 window.matchMedia('(prefers-color-scheme: dark)').matches;

  const c = {
    background: isDark ? '#0a0a0a' : '#f8f9fa',
    cardBg: isDark ? '#141414' : '#ffffff',
    border: isDark ? '#262626' : '#e5e7eb',
    text: isDark ? '#f5f5f5' : '#1f2937',
    textMuted: isDark ? '#a3a3a3' : '#6b7280',
    primary: '#6366f1',
    accent: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
  };

  const copyToClipboard = (url) => {
    navigator.clipboard.writeText(url);
    setCopiedUrl(url);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

  const getFullUrl = (path) => `${PRODUCTION_URL}${path}`;

  const getPriorityBadge = (priority) => {
    const colors = {
      high: { bg: `${c.accent}20`, color: c.accent, label: 'HIGH' },
      medium: { bg: `${c.warning}20`, color: c.warning, label: 'MED' },
      low: { bg: `${c.textMuted}20`, color: c.textMuted, label: 'LOW' },
    };
    const style = colors[priority] || colors.medium;
    return (
      <span style={{
        background: style.bg,
        color: style.color,
        padding: '2px 6px',
        borderRadius: 4,
        fontSize: '0.65rem',
        fontWeight: 600,
        letterSpacing: '0.05em'
      }}>
        {style.label}
      </span>
    );
  };

  const getMethodBadge = (method) => {
    const colors = {
      GET: { bg: '#10b98120', color: '#10b981' },
      POST: { bg: '#3b82f620', color: '#3b82f6' },
      DELETE: { bg: '#ef444420', color: '#ef4444' },
      PUT: { bg: '#f59e0b20', color: '#f59e0b' },
    };
    const style = colors[method] || colors.GET;
    return (
      <span style={{
        background: style.bg,
        color: style.color,
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: '0.7rem',
        fontWeight: 700,
        fontFamily: 'monospace',
        minWidth: 55,
        display: 'inline-block',
        textAlign: 'center'
      }}>
        {method}
      </span>
    );
  };

  const filteredCategories = ENDPOINT_CATEGORIES.map(cat => ({
    ...cat,
    endpoints: cat.endpoints.filter(ep => 
      filterPriority === 'all' || ep.priority === filterPriority
    )
  })).filter(cat => cat.endpoints.length > 0);

  return (
    <div style={{ padding: '1.5rem', maxWidth: '1200px', margin: '0 auto', background: c.background, minHeight: '100vh' }}>
      {/* Breadcrumb */}
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/admin" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: c.textMuted, textDecoration: 'none', fontSize: '0.85rem' }}>
          <ArrowLeft size={16} /> Back to Admin
        </Link>
      </div>

      {/* Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, color: c.text, margin: 0, fontFamily: "'Sora', sans-serif" }}>
            🔗 API Endpoints
          </h1>
          <p style={{ fontSize: '0.85rem', color: c.textMuted, margin: '0.25rem 0 0' }}>
            All endpoints for testing • Production: <code style={{ background: c.border, padding: '2px 6px', borderRadius: 4, fontSize: '0.8rem' }}>{PRODUCTION_URL}</code>
          </p>
        </div>
        
        {/* Priority Filter */}
        <div style={{ display: 'flex', gap: '0.25rem', background: c.border, padding: 3, borderRadius: 8 }}>
          {['all', 'high', 'medium', 'low'].map(p => (
            <button
              key={p}
              onClick={() => setFilterPriority(p)}
              style={{
                padding: '0.4rem 0.75rem',
                border: 'none',
                background: filterPriority === p ? c.cardBg : 'transparent',
                color: filterPriority === p ? c.text : c.textMuted,
                borderRadius: 6,
                fontSize: '0.75rem',
                fontWeight: 500,
                cursor: 'pointer',
                textTransform: 'capitalize'
              }}
            >
              {p === 'all' ? 'All' : p}
            </button>
          ))}
        </div>
      </div>

      {/* Quick Links - High Priority Only */}
      <div style={{ 
        background: `${c.accent}10`, 
        border: `1px solid ${c.accent}30`, 
        borderRadius: 10, 
        padding: '1rem 1.25rem', 
        marginBottom: '1.5rem' 
      }}>
        <div style={{ fontWeight: 600, fontSize: '0.85rem', color: c.accent, marginBottom: '0.75rem' }}>
          🚀 Quick Test Links (Click to Open)
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {[
            { path: '/api/health', label: 'Health' },
            { path: '/api/debug/imports', label: 'Imports' },
            { path: '/api/classification/health', label: 'Classification' },
            { path: '/api/classification/tables', label: 'Tables' },
            { path: '/api/status/structured', label: 'DuckDB' },
            { path: '/api/deep-clean/preview', label: 'Orphan Preview' },
          ].map(link => (
            <a
              key={link.path}
              href={getFullUrl(link.path)}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.4rem 0.75rem',
                background: c.cardBg,
                border: `1px solid ${c.border}`,
                borderRadius: 6,
                color: c.text,
                textDecoration: 'none',
                fontSize: '0.8rem',
                fontWeight: 500
              }}
            >
              {link.label} <ExternalLink size={12} />
            </a>
          ))}
        </div>
      </div>

      {/* Endpoint Categories */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {filteredCategories.map(category => (
          <div 
            key={category.id}
            style={{ 
              background: c.cardBg, 
              border: `1px solid ${c.border}`, 
              borderRadius: 10, 
              overflow: 'hidden' 
            }}
          >
            {/* Category Header */}
            <button
              onClick={() => setExpandedCategory(expandedCategory === category.id ? null : category.id)}
              style={{
                width: '100%',
                padding: '1rem 1.25rem',
                background: c.background,
                border: 'none',
                borderBottom: expandedCategory === category.id ? `1px solid ${c.border}` : 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                textAlign: 'left'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ fontSize: '1.25rem' }}>{category.icon}</span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem', color: c.text }}>{category.name}</div>
                  <div style={{ fontSize: '0.75rem', color: c.textMuted }}>{category.description}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ 
                  background: c.border, 
                  padding: '2px 8px', 
                  borderRadius: 10, 
                  fontSize: '0.75rem', 
                  color: c.textMuted 
                }}>
                  {category.endpoints.length} endpoints
                </span>
                <span style={{ 
                  transform: expandedCategory === category.id ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s',
                  color: c.textMuted
                }}>
                  ▼
                </span>
              </div>
            </button>

            {/* Endpoints List */}
            {expandedCategory === category.id && (
              <div style={{ padding: '0.5rem' }}>
                {category.endpoints.map((endpoint, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      padding: '0.75rem 1rem',
                      borderRadius: 8,
                      background: endpoint.dangerous ? `${c.danger}08` : 'transparent',
                      borderLeft: endpoint.dangerous ? `3px solid ${c.danger}` : '3px solid transparent'
                    }}
                  >
                    {/* Method Badge */}
                    {getMethodBadge(endpoint.method)}
                    
                    {/* Path */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <code style={{ 
                        fontSize: '0.8rem', 
                        color: c.text,
                        fontFamily: 'monospace',
                        wordBreak: 'break-all'
                      }}>
                        {endpoint.path}
                      </code>
                      <div style={{ fontSize: '0.75rem', color: c.textMuted, marginTop: '0.15rem' }}>
                        {endpoint.description}
                        {endpoint.param && (
                          <span style={{ color: c.warning, marginLeft: '0.5rem' }}>
                            (requires: {endpoint.param})
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Priority */}
                    {getPriorityBadge(endpoint.priority)}

                    {/* Actions */}
                    <div style={{ display: 'flex', gap: '0.35rem' }}>
                      {/* Copy Button */}
                      <button
                        onClick={() => copyToClipboard(getFullUrl(endpoint.path))}
                        title="Copy URL"
                        style={{
                          padding: '0.35rem',
                          background: c.border,
                          border: 'none',
                          borderRadius: 4,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          color: copiedUrl === getFullUrl(endpoint.path) ? c.accent : c.textMuted
                        }}
                      >
                        {copiedUrl === getFullUrl(endpoint.path) ? <Check size={14} /> : <Copy size={14} />}
                      </button>

                      {/* Open Link (GET only) */}
                      {endpoint.method === 'GET' && !endpoint.param && (
                        <a
                          href={getFullUrl(endpoint.path)}
                          target="_blank"
                          rel="noopener noreferrer"
                          title="Open in new tab"
                          style={{
                            padding: '0.35rem',
                            background: c.border,
                            border: 'none',
                            borderRadius: 4,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            color: c.textMuted,
                            textDecoration: 'none'
                          }}
                        >
                          <ExternalLink size={14} />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer Note */}
      <div style={{ 
        marginTop: '2rem', 
        padding: '1rem', 
        background: c.border, 
        borderRadius: 8, 
        fontSize: '0.8rem', 
        color: c.textMuted,
        textAlign: 'center'
      }}>
        <strong>Note:</strong> DELETE and POST endpoints cannot be tested via browser link. Use the Data Cleanup page or curl commands.
        <br />
        Last updated: December 27, 2025 • Classification transparency + Display names release
      </div>
    </div>
  );
}
