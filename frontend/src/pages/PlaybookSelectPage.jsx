/**
 * PlaybookSelectPage.jsx - Step 3: Select Playbooks
 * 
 * Third step in the 8-step consultant workflow.
 * Select which analysis playbooks to run against uploaded data.
 * 
 * Flow: Create Project → Upload Data → [SELECT PLAYBOOKS] → Analysis → ...
 * 
 * Created: January 15, 2026 - Phase 4A UX Overhaul (proper rebuild)
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useProject } from '../context/ProjectContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Playbook category configuration
const CATEGORIES = {
  'year-end': { icon: '📅', label: 'Year-End', color: 'warning' },
  'data-quality': { icon: '🔍', label: 'Data Quality', color: 'info' },
  'compliance': { icon: '🛡️', label: 'Compliance', color: 'critical' },
  'migration': { icon: '🔄', label: 'Migration', color: 'success' },
  'optimization': { icon: '⚡', label: 'Optimization', color: 'info' },
  'audit': { icon: '📋', label: 'Audit', color: 'warning' },
  'default': { icon: '📁', label: 'General', color: 'neutral' },
};

// Mock playbooks (will be replaced by API)
const MOCK_PLAYBOOKS = [
  {
    id: 'year-end-readiness',
    name: 'Year-End Readiness',
    description: 'Comprehensive year-end audit including W-2 validation, tax compliance, and payroll reconciliation.',
    category: 'year-end',
    action_count: 24,
    estimated_hours: '8-12',
    recommended: true,
  },
  {
    id: 'data-quality',
    name: 'Data Quality Assessment',
    description: 'Identify missing fields, duplicate records, and data inconsistencies across employee records.',
    category: 'data-quality',
    action_count: 18,
    estimated_hours: '4-6',
    recommended: true,
  },
  {
    id: 'migration-validation',
    name: 'Migration Validation',
    description: 'Pre-migration and post-migration data integrity checks for system conversions.',
    category: 'migration',
    action_count: 32,
    estimated_hours: '12-16',
  },
  {
    id: 'compliance-audit',
    name: 'Compliance Audit',
    description: 'Check configuration against regulatory requirements and best practices.',
    category: 'compliance',
    action_count: 15,
    estimated_hours: '3-5',
  },
  {
    id: 'benefits-review',
    name: 'Benefits Configuration Review',
    description: 'Validate benefit plans, eligibility rules, and deduction mappings.',
    category: 'audit',
    action_count: 20,
    estimated_hours: '5-8',
  },
];

const PlaybookSelectPage = () => {
  const navigate = useNavigate();
  const { activeProject } = useProject();
  
  const [playbooks, setPlaybooks] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(null);

  // Fetch playbooks on mount
  useEffect(() => {
    fetchPlaybooks();
  }, []);

  const fetchPlaybooks = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/playbooks/templates`);
      if (res.ok) {
        const data = await res.json();
        setPlaybooks(data.templates || data.playbooks || data || []);
      } else {
        // Use mock data if API not available
        setPlaybooks(MOCK_PLAYBOOKS);
      }
    } catch (err) {
      console.error('Failed to load playbooks:', err);
      setPlaybooks(MOCK_PLAYBOOKS);
    } finally {
      setLoading(false);
    }
  };

  const getCategoryConfig = (category) => {
    return CATEGORIES[category] || CATEGORIES.default;
  };

  const toggleSelection = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedIds(new Set(playbooks.map(p => p.id)));
  };

  const selectRecommended = () => {
    const recommended = playbooks.filter(p => p.recommended).map(p => p.id);
    setSelectedIds(new Set(recommended));
  };

  const clearAll = () => {
    setSelectedIds(new Set());
  };

  const startAnalysis = async () => {
    if (selectedIds.size === 0) {
      setError('Please select at least one playbook');
      return;
    }

    setStarting(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/analysis/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: activeProject?.id,
          playbook_ids: Array.from(selectedIds),
        }),
      });

      // Navigate to processing regardless of API result (for demo)
      navigate('/processing');
    } catch (err) {
      console.error('Failed to start analysis:', err);
      navigate('/processing');
    } finally {
      setStarting(false);
    }
  };

  // Calculate totals
  const selectedPlaybooks = playbooks.filter(p => selectedIds.has(p.id));
  const totalActions = selectedPlaybooks.reduce((sum, p) => sum + (p.action_count || 0), 0);
  const hasRecommended = playbooks.some(p => p.recommended);

  if (loading) {
    return (
      
        <div className="playbook-select playbook-select--loading">
          <LoadingSpinner />
          <p>Loading available playbooks...</p>
        </div>
      
    );
  }

  return (
    
      <div className="playbook-select">
        <PageHeader
          title="Select Playbooks"
          subtitle={`Step 3 of 8 • Choose which analysis to run${activeProject ? ` for ${activeProject.customer || activeProject.name}` : ''}`}
        />

        <div className="playbook-select__content">
          {/* Main Content */}
          <div className="playbook-select__main">
            {/* Selection Controls */}
            <Card className="playbook-select__controls">
              <div className="controls-row">
                <div className="controls-left">
                  <span className="selection-count">
                    {selectedIds.size} of {playbooks.length} selected
                  </span>
                  {selectedIds.size > 0 && (
                    <span className="selection-actions">
                      ({totalActions} total actions)
                    </span>
                  )}
                </div>
                <div className="controls-right">
                  {hasRecommended && (
                    <Button variant="ghost" size="sm" onClick={selectRecommended}>
                      Select Recommended
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" onClick={selectAll}>
                    Select All
                  </Button>
                  {selectedIds.size > 0 && (
                    <Button variant="ghost" size="sm" onClick={clearAll}>
                      Clear
                    </Button>
                  )}
                </div>
              </div>
            </Card>

            {/* Playbook Grid */}
            <div className="playbook-select__grid">
              {playbooks.map(playbook => {
                const isSelected = selectedIds.has(playbook.id);
                const categoryConfig = getCategoryConfig(playbook.category);

                return (
                  <button
                    key={playbook.id}
                    className={`playbook-card ${isSelected ? 'playbook-card--selected' : ''}`}
                    onClick={() => toggleSelection(playbook.id)}
                  >
                    {/* Selection Indicator */}
                    <div className="playbook-card__checkbox">
                      {isSelected ? (
                        <span className="checkbox-checked">✓</span>
                      ) : (
                        <span className="checkbox-empty">○</span>
                      )}
                    </div>

                    {/* Icon */}
                    <div className="playbook-card__icon">
                      {categoryConfig.icon}
                    </div>

                    {/* Content */}
                    <div className="playbook-card__content">
                      <div className="playbook-card__header">
                        <h3 className="playbook-card__title">{playbook.name}</h3>
                        {playbook.recommended && (
                          <Badge variant="success" size="sm">Recommended</Badge>
                        )}
                      </div>
                      <p className="playbook-card__description">{playbook.description}</p>
                      <div className="playbook-card__meta">
                        <Badge variant={categoryConfig.color} size="sm">
                          {categoryConfig.label}
                        </Badge>
                        <span>{playbook.action_count || 0} actions</span>
                        <span>•</span>
                        <span>{playbook.estimated_hours || '2-4'} hours</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Error */}
            {error && (
              <div className="playbook-select__error">
                <span className="error-icon">⚠️</span>
                {error}
              </div>
            )}

            {/* Actions */}
            <div className="playbook-select__actions">
              <Button
                variant="primary"
                onClick={startAnalysis}
                disabled={selectedIds.size === 0 || starting}
              >
                {starting ? 'Starting...' : `Start Analysis (${selectedIds.size} playbooks) →`}
              </Button>
              <Button
                variant="secondary"
                onClick={() => navigate('/upload')}
              >
                ← Back to Upload
              </Button>
            </div>
          </div>

          {/* Sidebar */}
          <div className="playbook-select__sidebar">
            {/* Selection Summary */}
            {selectedIds.size > 0 && (
              <Card className="playbook-select__summary-card">
                <CardHeader>
                  <CardTitle icon="📊">Selection Summary</CardTitle>
                </CardHeader>
                <div className="summary-stats">
                  <div className="summary-stat">
                    <div className="summary-value">{selectedIds.size}</div>
                    <div className="summary-label">Playbooks</div>
                  </div>
                  <div className="summary-stat">
                    <div className="summary-value">{totalActions}</div>
                    <div className="summary-label">Actions</div>
                  </div>
                </div>
                <ul className="summary-list">
                  {selectedPlaybooks.map(p => (
                    <li key={p.id}>
                      <span>{getCategoryConfig(p.category).icon}</span>
                      <span>{p.name}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            )}

            {/* Help Card */}
            <Card className="playbook-select__help-card">
              <CardHeader>
                <CardTitle icon="💡">About Playbooks</CardTitle>
              </CardHeader>
              <p className="help-text">
                Playbooks are pre-defined analysis workflows that examine your data for specific issues and patterns.
              </p>
              <ul className="help-list">
                <li>Select multiple playbooks for comprehensive analysis</li>
                <li>Each playbook generates specific findings</li>
                <li>Analysis runs in parallel for efficiency</li>
              </ul>
            </Card>

            {/* Next Step */}
            <Card className="playbook-select__next-card">
              <div className="next-step-preview">
                <div className="next-step-label">Next Step</div>
                <div className="next-step-title">⚙️ Analysis</div>
                <div className="next-step-description">
                  XLR8 will analyze your data and generate findings based on selected playbooks.
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    
  );
};

export default PlaybookSelectPage;
