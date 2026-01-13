/**
 * Metrics Pipeline Explainer
 * 
 * Architecture documentation page showing how XLR8 
 * transforms raw data into queryable intelligence.
 * 
 * Design: Matches XLR8 design system (light mode default)
 */

import React, { useState } from 'react';
import { useTheme } from '../context/ThemeContext';
import { 
  Database, 
  FileText, 
  FileSpreadsheet, 
  Search, 
  GitBranch, 
  BarChart3, 
  ChevronRight, 
  ChevronDown, 
  Zap, 
  Layers, 
  Brain,
  Activity 
} from 'lucide-react';

// Theme-aware colors (matching XLR8 design system)
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
  amberLight: dark ? 'rgba(212, 160, 84, 0.15)' : 'rgba(212, 160, 84, 0.1)',
  purple: '#8b5cf6',
  purpleLight: dark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(139, 92, 246, 0.1)',
  cyan: '#06b6d4',
  cyanLight: dark ? 'rgba(6, 182, 212, 0.15)' : 'rgba(6, 182, 212, 0.1)',
  green: '#10b981',
  greenLight: dark ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.1)',
  divider: dark ? '#2d3548' : '#e8ecf1',
  white: '#ffffff',
});

export default function MetricsPipelinePage() {
  const { isDark } = useTheme?.() || { isDark: false };
  const colors = getColors(isDark);
  const [expandedCards, setExpandedCards] = useState({});

  const toggleCard = (id) => {
    setExpandedCards(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const sections = [
    {
      id: 'ingest',
      title: 'Data Ingestion',
      subtitle: 'What goes in',
      icon: FileSpreadsheet,
      color: colors.blue,
      colorLight: colors.blueLight,
      items: [
        { label: 'Structured', desc: 'Excel, CSV files', detail: 'Parsed, validated, stored in DuckDB' },
        { label: 'Unstructured', desc: 'PDF documents', detail: 'Vision API extracts tables from pages 1-2' }
      ]
    },
    {
      id: 'profile',
      title: 'Automatic Profiling',
      subtitle: 'What we learn',
      icon: Search,
      color: colors.purple,
      colorLight: colors.purpleLight,
      items: [
        { label: 'Column Stats', desc: 'Distinct values, types, ranges', detail: '12+ metrics per column including nulls, samples, categories' },
        { label: 'Table Classification', desc: 'Domain, type, truth category', detail: 'Is it master data? Transactions? Config? We figure it out.' },
        { label: 'Term Index', desc: '11K+ searchable terms', detail: '"Texas" maps to stateprovince = \'TX\' automatically' }
      ]
    },
    {
      id: 'relate',
      title: 'Relationship Detection',
      subtitle: 'How data connects',
      icon: GitBranch,
      color: colors.primary,
      colorLight: colors.primaryLight,
      items: [
        { label: 'Self-References', desc: 'Supervisor → Employee', detail: 'Enables org chart queries and multi-hop navigation' },
        { label: 'Foreign Keys', desc: 'Table-to-table links', detail: 'Detected automatically without schema definitions' },
        { label: 'Multi-Hop Paths', desc: 'Chain queries together', detail: '"Reports to John\'s manager" traverses relationships' }
      ]
    },
    {
      id: 'intel',
      title: 'Intelligence Layer',
      subtitle: 'What it enables',
      icon: Brain,
      color: colors.amber,
      colorLight: colors.amberLight,
      items: [
        { label: 'Natural Language', desc: 'Ask questions in plain English', detail: 'Term index + SQL generation = answers, not code' },
        { label: 'Org Metrics', desc: 'Pre-computed breakdowns', detail: 'Headcounts, status, geography — instant access' },
        { label: 'Document Search', desc: 'Semantic retrieval', detail: 'ChromaDB embeddings find relevant policy/guidance' }
      ]
    }
  ];

  const metricHighlights = [
    { value: '12+', label: 'Metrics per column', color: colors.blue },
    { value: '11K+', label: 'Terms indexed', color: colors.purple },
    { value: '5', label: 'Truth types', color: colors.primary },
    { value: '<2min', label: 'Full analysis', color: colors.amber }
  ];

  return (
    <div style={{ 
      padding: '1.5rem', 
      background: colors.bg,
      minHeight: 'calc(100vh - 60px)',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Header - Standard XLR8 Pattern */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ 
          margin: 0, 
          fontSize: '20px', 
          fontWeight: 600, 
          color: colors.text, 
          display: 'flex', 
          alignItems: 'center', 
          gap: '10px',
          fontFamily: "'Sora', sans-serif"
        }}>
          <div style={{ 
            width: '36px', 
            height: '36px', 
            borderRadius: '10px', 
            backgroundColor: colors.primary, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center' 
          }}>
            <Activity size={20} color={colors.white} />
          </div>
          Metrics Pipeline
        </h1>
        <p style={{ margin: '6px 0 0 46px', fontSize: '13px', color: colors.textMuted }}>
          How XLR8 transforms raw data into queryable intelligence — automatically
        </p>
      </div>

      {/* Quick Stats Row */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(4, 1fr)', 
        gap: '16px', 
        marginBottom: '24px' 
      }}>
        {metricHighlights.map((stat, i) => (
          <div 
            key={i} 
            style={{ 
              background: colors.card, 
              border: `1px solid ${colors.cardBorder}`,
              borderRadius: '12px',
              padding: '16px',
              textAlign: 'center'
            }}
          >
            <div style={{ 
              fontSize: '28px', 
              fontWeight: 700, 
              color: stat.color,
              fontFamily: "'Sora', sans-serif",
              marginBottom: '4px'
            }}>
              {stat.value}
            </div>
            <div style={{ fontSize: '13px', color: colors.textMuted }}>
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* Pipeline Steps */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(4, 1fr)', 
        gap: '16px', 
        marginBottom: '24px',
        position: 'relative'
      }}>
        {sections.map((section, idx) => {
          const Icon = section.icon;
          const isExpanded = expandedCards[section.id];
          
          return (
            <div
              key={section.id}
              onClick={() => toggleCard(section.id)}
              style={{
                background: colors.card,
                border: `1px solid ${isExpanded ? section.color : colors.cardBorder}`,
                borderRadius: '12px',
                overflow: 'hidden',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: isExpanded ? `0 0 0 1px ${section.color}20` : 'none'
              }}
            >
              {/* Card Header */}
              <div style={{ 
                background: section.colorLight, 
                padding: '16px',
                borderBottom: `1px solid ${colors.cardBorder}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ 
                      width: '40px', 
                      height: '40px', 
                      borderRadius: '10px', 
                      backgroundColor: section.color,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <Icon size={20} color={colors.white} />
                    </div>
                    <div>
                      <div style={{ 
                        fontSize: '11px', 
                        color: colors.textMuted, 
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        marginBottom: '2px'
                      }}>
                        Step {idx + 1}
                      </div>
                      <div style={{ 
                        fontSize: '15px', 
                        fontWeight: 600, 
                        color: colors.text,
                        fontFamily: "'Sora', sans-serif"
                      }}>
                        {section.title}
                      </div>
                    </div>
                  </div>
                  {isExpanded ? 
                    <ChevronDown size={18} color={colors.textMuted} /> : 
                    <ChevronRight size={18} color={colors.textMuted} />
                  }
                </div>
              </div>
              
              {/* Card Content */}
              <div style={{ padding: '16px' }}>
                <p style={{ 
                  fontSize: '13px', 
                  color: colors.textMuted, 
                  margin: '0 0 12px 0' 
                }}>
                  {section.subtitle}
                </p>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {section.items.map((item, i) => (
                    <div key={i}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                        <div style={{ 
                          width: '6px', 
                          height: '6px', 
                          borderRadius: '50%', 
                          backgroundColor: section.color,
                          marginTop: '6px',
                          flexShrink: 0
                        }} />
                        <div>
                          <div style={{ 
                            fontSize: '13px', 
                            fontWeight: 500, 
                            color: colors.text 
                          }}>
                            {item.label}
                          </div>
                          <div style={{ 
                            fontSize: '12px', 
                            color: colors.textLight 
                          }}>
                            {item.desc}
                          </div>
                          {isExpanded && (
                            <div style={{ 
                              fontSize: '12px', 
                              color: colors.textMuted,
                              marginTop: '4px',
                              paddingLeft: '8px',
                              borderLeft: `2px solid ${colors.cardBorder}`
                            }}>
                              {item.detail}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Storage Architecture */}
      <div style={{ 
        background: colors.card, 
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '24px'
      }}>
        <h2 style={{ 
          margin: '0 0 16px 0',
          fontSize: '16px',
          fontWeight: 600,
          color: colors.text,
          fontFamily: "'Sora', sans-serif",
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <Layers size={18} color={colors.textMuted} />
          Storage Architecture
        </h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          {/* DuckDB */}
          <div style={{ 
            background: colors.bg, 
            borderRadius: '10px', 
            padding: '16px',
            border: `1px solid ${colors.cardBorder}`
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{ 
                width: '36px', 
                height: '36px', 
                borderRadius: '8px', 
                backgroundColor: colors.amber,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Database size={18} color={colors.white} />
              </div>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>DuckDB</div>
                <div style={{ fontSize: '11px', color: colors.textMuted }}>Structured Analytics</div>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {[
                { table: '_column_profiles', desc: 'Column-level stats' },
                { table: '_table_classifications', desc: 'Domain & type' },
                { table: '_term_index', desc: 'NL → SQL mapping' },
                { table: '_column_relationships', desc: 'Multi-hop paths' },
              ].map((row, i) => (
                <div key={i} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between',
                  fontSize: '12px'
                }}>
                  <code style={{ 
                    color: colors.amber,
                    background: colors.amberLight,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: '11px'
                  }}>
                    {row.table}
                  </code>
                  <span style={{ color: colors.textMuted }}>{row.desc}</span>
                </div>
              ))}
            </div>
          </div>
          
          {/* ChromaDB */}
          <div style={{ 
            background: colors.bg, 
            borderRadius: '10px', 
            padding: '16px',
            border: `1px solid ${colors.cardBorder}`
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{ 
                width: '36px', 
                height: '36px', 
                borderRadius: '8px', 
                backgroundColor: colors.purple,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <FileText size={18} color={colors.white} />
              </div>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: colors.text }}>ChromaDB</div>
                <div style={{ fontSize: '11px', color: colors.textMuted }}>Semantic Search</div>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {[
                { item: 'Document chunks', desc: 'PDF content' },
                { item: '1536-dim embeddings', desc: 'Vector search' },
                { item: 'Truth type metadata', desc: 'Reference, Regulatory...' },
                { item: 'Source tracking', desc: 'File, page, date' },
              ].map((row, i) => (
                <div key={i} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between',
                  fontSize: '12px'
                }}>
                  <span style={{ color: colors.text }}>{row.item}</span>
                  <span style={{ color: colors.textMuted }}>{row.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Summary */}
      <div style={{ 
        background: colors.primaryLight,
        border: `1px solid ${colors.primary}30`,
        borderRadius: '12px',
        padding: '20px',
        textAlign: 'center'
      }}>
        <BarChart3 size={24} color={colors.primary} style={{ marginBottom: '8px' }} />
        <h3 style={{ 
          margin: '0 0 8px 0',
          fontSize: '15px',
          fontWeight: 600,
          color: colors.text,
          fontFamily: "'Sora', sans-serif"
        }}>
          Zero Configuration Required
        </h3>
        <p style={{ 
          margin: 0,
          fontSize: '13px',
          color: colors.textMuted,
          maxWidth: '500px',
          marginLeft: 'auto',
          marginRight: 'auto'
        }}>
          Upload your data. XLR8 automatically profiles columns, detects relationships, 
          indexes searchable terms, and classifies documents — ready for natural language queries.
        </p>
      </div>
    </div>
  );
}
