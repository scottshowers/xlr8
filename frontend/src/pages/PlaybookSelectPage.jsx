/**
 * PlaybookSelectPage.jsx - Step 3: Select Playbooks
 * 
 * Select which analysis playbooks to run against uploaded data.
 * Uses design system classes - NO emojis.
 * 
 * Phase 4A UX Overhaul - January 16, 2026
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Check, ChevronRight, Calendar, Shield, Search, RefreshCw, Zap, ClipboardList } from 'lucide-react';
import { useProject } from '../context/ProjectContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

const CATEGORY_ICONS = {
  'year-end': Calendar,
  'data-quality': Search,
  'compliance': Shield,
  'migration': RefreshCw,
  'optimization': Zap,
  'audit': ClipboardList,
  'default': BookOpen,
};

const MOCK_PLAYBOOKS = [
  { id: 'year-end-readiness', name: 'Year-End Readiness', description: 'W-2 validation, tax compliance, payroll reconciliation', category: 'year-end', action_count: 24, recommended: true },
  { id: 'data-quality', name: 'Data Quality Assessment', description: 'Missing fields, duplicates, data inconsistencies', category: 'data-quality', action_count: 18, recommended: true },
  { id: 'migration-validation', name: 'Migration Validation', description: 'Pre/post migration data integrity checks', category: 'migration', action_count: 32 },
  { id: 'compliance-audit', name: 'Compliance Audit', description: 'Regulatory requirements and best practices', category: 'compliance', action_count: 15 },
  { id: 'benefits-review', name: 'Benefits Configuration Review', description: 'Benefit plans, eligibility, deduction mappings', category: 'audit', action_count: 20 },
];

const PlaybookSelectPage = () => {
  const navigate = useNavigate();
  const { activeProject } = useProject();
  
  const [playbooks, setPlaybooks] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPlaybooks();
  }, []);

  const fetchPlaybooks = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/playbooks/templates`);
      if (res.ok) {
        const data = await res.json();
        setPlaybooks(data.templates || data.playbooks || data || []);
      } else {
        setPlaybooks(MOCK_PLAYBOOKS);
      }
    } catch {
      setPlaybooks(MOCK_PLAYBOOKS);
    } finally {
      setLoading(false);
    }
  };

  const toggleSelection = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectRecommended = () => setSelectedIds(new Set(playbooks.filter(p => p.recommended).map(p => p.id)));
  const selectAll = () => setSelectedIds(new Set(playbooks.map(p => p.id)));
  const clearAll = () => setSelectedIds(new Set());

  const startAnalysis = async () => {
    if (selectedIds.size === 0) {
      setError('Please select at least one playbook');
      return;
    }
    setStarting(true);
    try {
      await fetch(`${API_BASE}/api/analysis/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: activeProject?.id, playbook_ids: Array.from(selectedIds) }),
      });
    } catch {}
    navigate('/processing');
  };

  const totalActions = playbooks.filter(p => selectedIds.has(p.id)).reduce((sum, p) => sum + (p.action_count || 0), 0);

  if (loading) {
    return <div className="page-loading"><p>Loading playbooks...</p></div>;
  }

  return (
    <div className="playbook-page">
      <div className="page-header">
        <h1 className="page-title">Select Playbooks</h1>
        <p className="page-subtitle">Choose which analysis to run{activeProject ? ` for ${activeProject.customer || activeProject.name}` : ''}</p>
      </div>

      {/* Controls */}
      <div className="card mb-4">
        <div className="card-body flex justify-between items-center">
          <div className="flex items-center gap-4">
            <span style={{ fontWeight: 'var(--weight-semibold)' }}>{selectedIds.size} of {playbooks.length} selected</span>
            {selectedIds.size > 0 && <span className="text-muted">({totalActions} actions)</span>}
          </div>
          <div className="flex gap-2">
            <button className="btn btn-secondary btn-sm" onClick={selectRecommended}>Recommended</button>
            <button className="btn btn-secondary btn-sm" onClick={selectAll}>Select All</button>
            {selectedIds.size > 0 && <button className="btn btn-secondary btn-sm" onClick={clearAll}>Clear</button>}
          </div>
        </div>
      </div>

      {/* Playbook Grid */}
      <div className="playbook-grid">
        {playbooks.map(playbook => {
          const isSelected = selectedIds.has(playbook.id);
          const Icon = CATEGORY_ICONS[playbook.category] || CATEGORY_ICONS.default;
          return (
            <div
              key={playbook.id}
              className={`playbook-card ${isSelected ? 'playbook-card--selected' : ''}`}
              onClick={() => toggleSelection(playbook.id)}
            >
              <div className="playbook-card__header">
                <div className="playbook-card__icon">
                  <Icon size={20} />
                </div>
                <div className="playbook-card__check">
                  {isSelected && <Check size={16} />}
                </div>
              </div>
              <h4 className="playbook-card__name">{playbook.name}</h4>
              <p className="playbook-card__desc">{playbook.description}</p>
              <div className="playbook-card__meta">
                <span>{playbook.action_count} actions</span>
                {playbook.recommended && <span className="badge badge--success">Recommended</span>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Error */}
      {error && <div className="alert alert--error mt-4">{error}</div>}

      {/* Actions */}
      <div className="flex gap-4 mt-6">
        <button className="btn btn-primary btn-lg" onClick={startAnalysis} disabled={selectedIds.size === 0 || starting}>
          {starting ? 'Starting...' : 'Run Analysis'}
          <ChevronRight size={18} />
        </button>
        <button className="btn btn-secondary" onClick={() => navigate('/upload')}>Back to Upload</button>
      </div>
    </div>
  );
};

export default PlaybookSelectPage;
