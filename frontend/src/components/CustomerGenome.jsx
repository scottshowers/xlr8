/**
 * CustomerGenome.jsx - Visual DNA fingerprint for each customer
 * 
 * Shows unique intelligence profile that evolves over time.
 * Accessed from header DNA icon - opens as a slide-out panel.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useTheme } from '../context/ThemeContext';
import { useProject } from '../context/ProjectContext';
import { X, TrendingUp, Database, GitBranch, MessageSquare, Shield, Calendar, Lightbulb, Activity } from 'lucide-react';
import api from '../services/api';

const getColors = (dark) => ({
  bg: dark ? '#12151c' : '#f5f6f8',
  bgAlt: dark ? '#1a1e28' : '#eef0f4',
  card: dark ? '#1e232e' : '#ffffff',
  border: dark ? '#2a2f3a' : '#e4e7ec',
  text: dark ? '#e4e6ea' : '#2d3643',
  textMuted: dark ? '#8b95a5' : '#6b7a8f',
  textLight: dark ? '#5f6a7d' : '#9aa5b5',
  primary: '#83b16d',
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.12)',
  primaryDark: '#6a9b5a',
  dustyBlue: '#7889a0',
  dustyBlueLight: dark ? 'rgba(120, 137, 160, 0.15)' : 'rgba(120, 137, 160, 0.12)',
  taupe: '#9b8f82',
  taupeLight: dark ? 'rgba(155, 143, 130, 0.15)' : 'rgba(155, 143, 130, 0.12)',
  amber: '#b5956a',
  amberLight: dark ? 'rgba(181, 149, 106, 0.15)' : 'rgba(181, 149, 106, 0.12)',
});

// DNA Helix Canvas Component
function DNAHelix({ colors, dnaColors, animating = true }) {
  const canvasRef = useRef(null);
  const animationRef = useRef(0);
  const frameRef = useRef(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const w = canvas.width / 2;
    const h = canvas.height / 2;
    
    ctx.clearRect(0, 0, w, h);
    
    const centerY = h / 2;
    const amplitude = 35;
    const wavelength = 80;
    const nodeRadius = 5;
    
    // Draw helix strands
    for (let strand = 0; strand < 2; strand++) {
      const offset = strand * Math.PI;
      
      ctx.beginPath();
      for (let x = 0; x < w; x += 2) {
        const phase = (x / wavelength) * Math.PI * 2 + animationRef.current * 0.015 + offset;
        const y = centerY + Math.sin(phase) * amplitude;
        
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = dnaColors[strand % dnaColors.length];
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    
    // Draw connecting bars
    for (let x = 20; x < w - 20; x += 30) {
      const phase1 = (x / wavelength) * Math.PI * 2 + animationRef.current * 0.015;
      const phase2 = phase1 + Math.PI;
      
      const y1 = centerY + Math.sin(phase1) * amplitude;
      const y2 = centerY + Math.sin(phase2) * amplitude;
      
      const visibility = Math.abs(Math.cos(phase1));
      if (visibility > 0.3) {
        ctx.beginPath();
        ctx.moveTo(x, y1);
        ctx.lineTo(x, y2);
        ctx.strokeStyle = `rgba(107, 122, 143, ${visibility * 0.4})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        
        const colorIndex = Math.floor((x / 30) % dnaColors.length);
        
        ctx.beginPath();
        ctx.arc(x, y1, nodeRadius * visibility, 0, Math.PI * 2);
        ctx.fillStyle = dnaColors[colorIndex];
        ctx.fill();
        
        ctx.beginPath();
        ctx.arc(x, y2, nodeRadius * visibility, 0, Math.PI * 2);
        ctx.fillStyle = dnaColors[(colorIndex + 2) % dnaColors.length];
        ctx.fill();
      }
    }
    
    if (animating) {
      animationRef.current++;
      frameRef.current = requestAnimationFrame(draw);
    }
  }, [dnaColors, animating]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    const ctx = canvas.getContext('2d');
    ctx.scale(2, 2);
    
    draw();
    
    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [draw]);

  return (
    <canvas 
      ref={canvasRef} 
      style={{ width: '100%', height: '100%', borderRadius: 8 }}
    />
  );
}

// Radar Chart Component
function RadarChart({ values, colors, size = 140 }) {
  const labels = ['Data', 'Queries', 'Standards', 'Links', 'Activity'];
  const cx = size / 2, cy = size / 2, r = (size / 2) - 25;
  const angles = values.map((_, i) => (i * 2 * Math.PI / values.length) - Math.PI / 2);

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Background circles */}
      {[1, 2, 3, 4].map(i => (
        <circle key={i} cx={cx} cy={cy} r={r * i / 4} fill="none" stroke={colors.border} strokeWidth="1"/>
      ))}
      
      {/* Axis lines */}
      {angles.map((angle, i) => (
        <line key={i} x1={cx} y1={cy} x2={cx + Math.cos(angle) * r} y2={cy + Math.sin(angle) * r} stroke={colors.border} strokeWidth="1"/>
      ))}
      
      {/* Data polygon */}
      <polygon 
        points={values.map((v, i) => `${cx + Math.cos(angles[i]) * r * v},${cy + Math.sin(angles[i]) * r * v}`).join(' ')}
        fill={colors.primaryLight}
        stroke={colors.primary}
        strokeWidth="2"
      />
      
      {/* Data points */}
      {values.map((v, i) => (
        <circle key={i} cx={cx + Math.cos(angles[i]) * r * v} cy={cy + Math.sin(angles[i]) * r * v} r="4" fill={colors.primary}/>
      ))}
      
      {/* Labels */}
      {labels.map((label, i) => (
        <text 
          key={i}
          x={cx + Math.cos(angles[i]) * (r + 15)} 
          y={cy + Math.sin(angles[i]) * (r + 15)} 
          textAnchor="middle" 
          dominantBaseline="middle" 
          fontSize="8" 
          fill={colors.textMuted}
        >
          {label}
        </text>
      ))}
    </svg>
  );
}

// Trait Bar Component
function TraitBar({ label, value, color, colors }) {
  return (
    <div style={{ marginBottom: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
        <span style={{ fontSize: '0.75rem', color: colors.textMuted }}>{label}</span>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", color: colors.text }}>{value}%</span>
      </div>
      <div style={{ height: 5, background: colors.border, borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${value}%`, background: color, borderRadius: 3, transition: 'width 0.5s ease' }} />
      </div>
    </div>
  );
}

// Signature Component
function Signature({ values, colors }) {
  return (
    <div style={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
      {values.map((v, i) => {
        const height = 8 + (v / 100) * 16;
        const lightness = 40 + (v / 100) * 20;
        return (
          <div 
            key={i}
            style={{
              width: 5,
              height,
              borderRadius: 2,
              background: `hsl(90, 35%, ${lightness}%)`,
            }}
          />
        );
      })}
    </div>
  );
}

export default function CustomerGenome({ isOpen, onClose }) {
  const { darkMode } = useTheme();
  const { activeProject } = useProject();
  const colors = getColors(darkMode);
  
  const [genomeData, setGenomeData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      loadGenomeData();
    }
  }, [isOpen, activeProject]);

  const loadGenomeData = async () => {
    setLoading(true);
    try {
      // Try to load real data from API
      const projectParam = activeProject ? `?project_id=${activeProject.id}` : '';
      
      const [registryRes, structuredRes, statsRes] = await Promise.all([
        api.get(`/status/registry${projectParam}`).catch(() => ({ data: {} })),
        api.get(`/status/structured${projectParam}`).catch(() => ({ data: {} })),
        api.get('/chat/intelligent/learning/stats').catch(() => ({ data: {} })),
      ]);

      const registry = registryRes.data || {};
      const structured = structuredRes.data || {};
      const learning = statsRes.data || {};
      
      const docs = registry.documents || [];
      const files = structured.files || [];
      
      // Calculate traits from real data - show actual zeros when empty
      const totalDocs = docs.length;
      const totalFiles = files.length;
      const totalRows = files.reduce((sum, f) => sum + (f.total_rows || 0), 0);
      const patterns = learning.patterns_count || learning.cached_queries || 0;
      const queries = learning.total_queries || 0;
      
      // Only show real metrics, not inflated random values
      const hasData = totalDocs > 0 || totalFiles > 0;
      
      const dataComplexity = hasData ? Math.min(95, Math.round(20 + (totalFiles * 8) + (totalRows / 10000))) : 0;
      const relationships = structured.relationships_count || 0;
      const querySophistication = queries > 0 ? Math.min(95, Math.round(20 + (queries * 2) + (patterns * 5))) : 0;
      const standardsCoverage = hasData ? Math.min(98, Math.round(30 + (patterns * 3) + (totalDocs * 2))) : 0;
      const activityLevel = hasData ? Math.min(95, Math.round(30 + (totalDocs * 5) + (totalFiles * 3))) : 0;
      
      // Generate unique signature based on project
      const signatureSeed = activeProject?.id || 'default';
      const signature = Array(20).fill(0).map((_, i) => {
        const hash = (signatureSeed.charCodeAt(i % signatureSeed.length) || 65) + i * 7;
        return 50 + (hash % 45);
      });
      
      // DNA colors based on dominant traits
      const dnaColors = [colors.primary, colors.dustyBlue, colors.taupe, colors.amber];
      
      setGenomeData({
        name: activeProject?.name || 'Platform Overview',
        id: activeProject?.id ? `GENOME-${activeProject.id.slice(0, 8).toUpperCase()}` : 'GENOME-PLATFORM',
        score: Math.round((dataComplexity + querySophistication + standardsCoverage + activityLevel) / 4),
        traits: {
          complexity: dataComplexity,
          relationships: Math.min(95, relationships),
          queries: querySophistication,
          standards: standardsCoverage,
        },
        radar: [
          dataComplexity / 100,
          querySophistication / 100,
          standardsCoverage / 100,
          Math.min(95, relationships) / 100,
          activityLevel / 100,
        ],
        stats: {
          since: activeProject?.created_at ? new Date(activeProject.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 'Today',
          datapoints: totalRows > 0 ? totalRows.toLocaleString() : '0',
          files: totalFiles.toString(),
          queries: queries.toString(),
          patterns: patterns.toString(),
        },
        signature,
        dnaColors,
        insight: generateInsight(dataComplexity, querySophistication, standardsCoverage, relationships),
      });
    } catch (err) {
      console.error('Failed to load genome data:', err);
      // Fallback to demo data
      setGenomeData(getDemoData(colors));
    } finally {
      setLoading(false);
    }
  };

  const generateInsight = (complexity, queries, standards, relationships) => {
    if (queries > 80 && standards > 85) {
      return "Power user profile detected. High query sophistication combined with strong standards coverage indicates advanced platform utilization. Consider for beta features.";
    } else if (complexity > 75 && relationships < 50) {
      return "High data complexity but lower relationship mapping. Focus on connection discovery to unlock cross-table insights and more powerful queries.";
    } else if (standards < 60) {
      return "Standards coverage has room for growth. Uploading compliance rules and best practices will significantly improve validation capabilities.";
    } else {
      return "Healthy engagement pattern. Consistent usage across data upload, querying, and validation. Continue building patterns for faster future analysis.";
    }
  };

  const getDemoData = (colors) => ({
    name: 'Demo Customer',
    id: 'GENOME-DEMO-X7K9',
    score: 82,
    traits: { complexity: 75, relationships: 62, queries: 78, standards: 85 },
    radar: [0.75, 0.78, 0.85, 0.62, 0.80],
    stats: { since: 'Dec 2024', datapoints: '125K', files: '24', queries: '156', patterns: '34' },
    signature: Array(20).fill(0).map(() => 50 + Math.floor(Math.random() * 45)),
    dnaColors: [colors.primary, colors.dustyBlue, colors.taupe, colors.amber],
    insight: "New engagement with strong initial data upload. Building baseline patterns for optimized future analysis.",
  });

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        onClick={onClose}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.4)',
          zIndex: 998,
        }}
      />
      
      {/* Panel */}
      <div style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: 420,
        background: colors.bg,
        boxShadow: '-4px 0 24px rgba(0,0,0,0.15)',
        zIndex: 999,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: "'Inter', system-ui, sans-serif",
      }}>
        {/* Header */}
        <div style={{
          padding: '1.25rem',
          borderBottom: `1px solid ${colors.border}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: colors.card,
        }}>
          <div>
            <h2 style={{ 
              fontFamily: "'Sora', sans-serif", 
              fontSize: '1.1rem', 
              fontWeight: 800, 
              margin: 0,
              color: colors.text,
            }}>
              {genomeData?.name || activeProject?.name || 'Customer'} Genome
            </h2>
            <p style={{ fontSize: '0.75rem', color: colors.textMuted, margin: '0.25rem 0 0 0' }}>
              Unique intelligence fingerprint
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              border: `1px solid ${colors.border}`,
              background: colors.bg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: colors.textMuted,
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '1.25rem' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: colors.textMuted }}>
              Loading genome...
            </div>
          ) : genomeData && (
            <>
              {/* Customer Info */}
              <div style={{
                background: colors.card,
                border: `1px solid ${colors.border}`,
                borderRadius: 12,
                padding: '1rem',
                marginBottom: '1rem',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: '1rem', color: colors.text }}>
                      {genomeData.name}
                    </div>
                    <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.65rem', color: colors.textLight, marginTop: '0.2rem' }}>
                      {genomeData.id}
                    </div>
                  </div>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.4rem 0.75rem',
                    background: colors.primaryLight,
                    borderRadius: 16,
                  }}>
                    <span style={{ fontSize: '0.7rem', color: colors.primary, fontWeight: 600 }}>Score</span>
                    <span style={{ fontFamily: "'Sora', sans-serif", fontSize: '1rem', fontWeight: 800, color: colors.primary }}>
                      {genomeData.score}
                    </span>
                  </div>
                </div>
              </div>

              {/* DNA Helix */}
              <div style={{
                background: colors.card,
                border: `1px solid ${colors.border}`,
                borderRadius: 12,
                padding: '1rem',
                marginBottom: '1rem',
              }}>
                <div style={{ height: 120 }}>
                  <DNAHelix colors={colors} dnaColors={genomeData.dnaColors} />
                </div>
                
                {/* Signature */}
                <div style={{ marginTop: '1rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.6rem', color: colors.textLight, letterSpacing: 1, marginBottom: '0.4rem' }}>
                    UNIQUE SIGNATURE
                  </div>
                  <Signature values={genomeData.signature} colors={colors} />
                </div>
              </div>

              {/* Radar + Stats Row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                {/* Radar */}
                <div style={{
                  background: colors.card,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 12,
                  padding: '1rem',
                  display: 'flex',
                  justifyContent: 'center',
                }}>
                  <RadarChart values={genomeData.radar} colors={colors} size={130} />
                </div>
                
                {/* Quick Stats */}
                <div style={{
                  background: colors.card,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 12,
                  padding: '1rem',
                }}>
                  <div style={{ fontSize: '0.7rem', fontWeight: 700, color: colors.textMuted, marginBottom: '0.75rem' }}>
                    PROFILE
                  </div>
                  {[
                    { label: 'Since', value: genomeData.stats.since },
                    { label: 'Data Points', value: genomeData.stats.datapoints },
                    { label: 'Files', value: genomeData.stats.files },
                    { label: 'Queries', value: genomeData.stats.queries },
                    { label: 'Patterns', value: genomeData.stats.patterns },
                  ].map((stat, i) => (
                    <div key={i} style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '0.35rem 0',
                      borderBottom: i < 4 ? `1px solid ${colors.bg}` : 'none',
                      fontSize: '0.75rem',
                    }}>
                      <span style={{ color: colors.textMuted }}>{stat.label}</span>
                      <span style={{ fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", color: colors.text }}>{stat.value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Traits */}
              <div style={{
                background: colors.card,
                border: `1px solid ${colors.border}`,
                borderRadius: 12,
                padding: '1rem',
                marginBottom: '1rem',
              }}>
                <div style={{ fontSize: '0.7rem', fontWeight: 700, color: colors.textMuted, marginBottom: '0.75rem' }}>
                  GENOME TRAITS
                </div>
                <TraitBar label="Data Complexity" value={genomeData.traits.complexity} color={colors.primary} colors={colors} />
                <TraitBar label="Relationship Density" value={genomeData.traits.relationships} color={colors.dustyBlue} colors={colors} />
                <TraitBar label="Query Sophistication" value={genomeData.traits.queries} color={colors.taupe} colors={colors} />
                <TraitBar label="Standards Coverage" value={genomeData.traits.standards} color={colors.amber} colors={colors} />
              </div>

              {/* AI Insight */}
              <div style={{
                background: colors.primaryLight,
                border: `1px solid ${colors.primary}`,
                borderRadius: 12,
                padding: '1rem',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <Lightbulb size={14} style={{ color: colors.primary }} />
                  <span style={{ fontSize: '0.7rem', fontWeight: 700, color: colors.primary, letterSpacing: '0.5px' }}>
                    INSIGHT
                  </span>
                </div>
                <p style={{ fontSize: '0.8rem', color: colors.text, lineHeight: 1.5, margin: 0 }}>
                  {genomeData.insight}
                </p>
              </div>
            </>
          )}
        </div>

        {/* Footer - Security note */}
        <div style={{
          padding: '1rem 1.25rem',
          borderTop: `1px solid ${colors.border}`,
          background: colors.card,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Shield size={14} style={{ color: colors.primary }} />
            <span style={{ fontSize: '0.7rem', color: colors.textMuted }}>
              All analysis runs locally. Your data never leaves your environment.
            </span>
          </div>
        </div>
      </div>
    </>
  );
}

// Header Button Component (for use in Layout)
export function GenomeButton({ onClick }) {
  const [hovered, setHovered] = useState(false);
  
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title="Customer Genome"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 32,
        height: 32,
        background: hovered ? '#f0fdf4' : '#f8fafc',
        border: `1px solid ${hovered ? '#83b16d' : '#e1e8ed'}`,
        borderRadius: 6,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        color: hovered ? '#5a8a4a' : '#5f6c7b',
      }}
    >
      {/* DNA Icon */}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 15c6.667-6 13.333 0 20-6" />
        <path d="M9 22c1.798-1.998 2.518-3.995 2.807-5.993" />
        <path d="M15 2c-1.798 1.998-2.518 3.995-2.807 5.993" />
        <path d="M17 6l-2.5-2.5" />
        <path d="M14 8l-1-1" />
        <path d="M7 18l2.5 2.5" />
        <path d="M3.5 14.5l.5.5" />
        <path d="M20 9l.5.5" />
        <path d="M6.5 12.5l1 1" />
        <path d="M16.5 10.5l1 1" />
        <path d="M10 16l1.5 1.5" />
      </svg>
    </button>
  );
}
