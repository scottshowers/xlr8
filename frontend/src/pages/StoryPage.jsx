/**
 * StoryPage.jsx - The XLR8 Story (Narrative Version)
 * 
 * UPDATED: December 23, 2025
 * - Mission Control color palette (#83b16d)
 * - Removed dark mode
 * 
 * Scrolling chapter-based narrative explaining the platform.
 * Route: /story
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Rocket } from 'lucide-react';

// Mission Control Colors
const colors = {
  bg: '#f0f2f5',
  bgAlt: '#e8ebf0',
  card: '#ffffff',
  cardBorder: '#e2e8f0',
  text: '#1a2332',
  textMuted: '#64748b',
  textLight: '#94a3b8',
  primary: '#83b16d',
  primaryLight: 'rgba(131, 177, 109, 0.1)',
  primaryDark: '#6b9b5a',
  accent: '#285390',
  accentLight: 'rgba(40, 83, 144, 0.1)',
  warning: '#d97706',
  error: '#dc2626',
};

export default function StoryPage() {
  const navigate = useNavigate();
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const winScroll = document.documentElement.scrollTop;
      const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const scrolled = (winScroll / height) * 100;
      setScrollProgress(scrolled);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const Chapter = ({ num, title, children, style = {} }) => (
    <section style={{
      minHeight: '100vh',
      padding: '6rem 2rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      ...style
    }}>
      <div style={{ maxWidth: 1100, width: '100%' }}>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.7rem',
          fontWeight: 500,
          color: colors.primary,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
        }}>
          <span style={{ width: 24, height: 2, background: colors.primary }} />
          Chapter {num.toString().padStart(2, '0')}
        </div>
        <h2 style={{
          fontFamily: "'Sora', 'Inter', sans-serif",
          fontSize: '2.25rem',
          fontWeight: 800,
          lineHeight: 1.2,
          letterSpacing: '-0.02em',
          marginBottom: '1rem',
          color: colors.text,
        }}>{title}</h2>
        {children}
      </div>
    </section>
  );

  const Lead = ({ children, style = {} }) => (
    <p style={{
      fontSize: '1.15rem',
      color: colors.textMuted,
      maxWidth: 600,
      lineHeight: 1.7,
      ...style
    }}>{children}</p>
  );

  return (
    <div style={{ background: colors.bg, minHeight: '100vh', fontFamily: "'Inter', system-ui, sans-serif" }}>
      {/* Progress Bar */}
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        height: 3,
        background: colors.primary,
        width: `${scrollProgress}%`,
        zIndex: 1000,
        transition: 'width 0.1s ease',
      }} />

      {/* Nav */}
      <nav style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        padding: '1rem 2rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'rgba(240, 242, 245, 0.95)',
        backdropFilter: 'blur(10px)',
        zIndex: 100,
        borderBottom: `1px solid ${colors.cardBorder}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: '1.4rem',
            fontWeight: 800,
            color: colors.primary,
          }}>XLR8</span>
          <Rocket size={18} color={colors.primary} />
        </div>
        <button
          onClick={() => navigate('/dashboard')}
          style={{
            padding: '0.5rem 1rem',
            background: colors.card,
            border: `1px solid ${colors.cardBorder}`,
            color: colors.text,
            borderRadius: 8,
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Skip to Dashboard →
        </button>
      </nav>

      {/* Chapter 1: The Beginning */}
      <Chapter num={1} title="We Built This For Ourselves" style={{ paddingTop: '8rem', background: colors.bg }}>
        <Lead>We're implementation consultants. We spent years drowning in spreadsheets, validating data manually, and starting from scratch on every project.</Lead>
        <Lead style={{ marginTop: '1rem' }}>Then we built something better.</Lead>
        
        {/* Code block */}
        <div style={{
          marginTop: '2rem',
          background: colors.card,
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: 12,
          padding: '1.5rem',
          maxWidth: 400,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.85rem',
        }}>
          <div style={{ display: 'flex', gap: 6, marginBottom: '1rem', paddingBottom: '0.75rem', borderBottom: `1px solid ${colors.cardBorder}` }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: colors.cardBorder }} />
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: colors.cardBorder }} />
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: colors.cardBorder }} />
          </div>
          <div style={{ color: colors.textLight }}>// The question we asked</div>
          <div style={{ marginTop: '0.5rem' }}>
            <span style={{ color: colors.primary }}>const</span> problem = {'{'}
          </div>
          <div style={{ paddingLeft: '1rem', color: colors.textMuted }}>
            hours: <span style={{ color: colors.accent }}>"too many"</span>,
          </div>
          <div style={{ paddingLeft: '1rem', color: colors.textMuted }}>
            mistakes: <span style={{ color: colors.accent }}>"inevitable"</span>,
          </div>
          <div style={{ paddingLeft: '1rem', color: colors.textMuted }}>
            knowledge: <span style={{ color: colors.accent }}>"siloed"</span>,
          </div>
          <div>{'}'}</div>
        </div>
      </Chapter>

      {/* Chapter 2: The Problem */}
      <Chapter num={2} title="What We Were Fighting" style={{ background: colors.bgAlt }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.5rem', marginTop: '2rem' }}>
          {[
            { icon: '', label: 'Spreadsheet Hell', desc: 'Every project started with blank Excel. Copy. Paste. Pray.' },
            { icon: '', label: 'Time Drain', desc: 'Weeks spent on manual validation. Same checks, every time.' },
            { icon: '', label: 'Missed Issues', desc: 'Human eyes miss things. Compliance gaps slip through.' },
            { icon: '', label: 'Knowledge Loss', desc: 'Senior consultants leave. Expertise walks out the door.' },
          ].map((item, i) => (
            <div key={i} style={{
              background: colors.card,
              border: `1px solid ${colors.cardBorder}`,
              borderRadius: 12,
              padding: '1.5rem',
            }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>{item.icon}</div>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.5rem', color: colors.text }}>{item.label}</h3>
              <p style={{ fontSize: '0.85rem', color: colors.textMuted, lineHeight: 1.5 }}>{item.desc}</p>
            </div>
          ))}
        </div>
      </Chapter>

      {/* Chapter 3: The Solution */}
      <Chapter num={3} title="Three Truths Architecture" style={{ background: colors.bg }}>
        <Lead>Every question has three sides. We built a system that knows them all.</Lead>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem', marginTop: '2rem' }}>
          {[
            { 
              color: colors.primary, 
              title: 'Reality', 
              subtitle: 'What IS',
              desc: 'Your actual data. Employee rosters, pay registers, transactions. Parsed into queryable tables.',
              storage: '→ DuckDB'
            },
            { 
              color: colors.accent, 
              title: 'Intent', 
              subtitle: 'What SHOULD BE',
              desc: 'Customer documents describing requirements. Implementation guides, SOWs, specs.',
              storage: '→ ChromaDB'
            },
            { 
              color: '#5f4282', 
              title: 'Reference', 
              subtitle: 'Best Practice',
              desc: 'Industry standards, compliance rules, regulatory requirements. Shared knowledge base.',
              storage: '→ Reference Library'
            },
          ].map((item, i) => (
            <div key={i} style={{
              background: colors.card,
              border: `1px solid ${colors.cardBorder}`,
              borderTop: `4px solid ${item.color}`,
              borderRadius: 12,
              padding: '1.5rem',
            }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.25rem', color: colors.text }}>{item.title}</h3>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: item.color, marginBottom: '0.75rem' }}>{item.subtitle}</div>
              <p style={{ fontSize: '0.85rem', color: colors.textMuted, lineHeight: 1.5, marginBottom: '0.75rem' }}>{item.desc}</p>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: item.color }}>{item.storage}</span>
            </div>
          ))}
        </div>
      </Chapter>

      {/* Chapter 4: The Intelligence */}
      <Chapter num={4} title="It Learns. It Finds. It Validates." style={{ background: colors.bgAlt }}>
        <Lead>The platform gets smarter with every upload, every query, every validation.</Lead>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem', marginTop: '2rem' }}>
          {[
            { icon: '', title: 'Auto-Classification', desc: 'Documents routed to the right Truth layer automatically.', tag: 'ON UPLOAD' },
            { icon: '', title: 'Relationship Discovery', desc: 'Foreign keys found. Smart JOINs without config.', tag: 'AUTOMATIC' },
            { icon: '', title: 'Data Quality Scoring', desc: 'Every file gets a health score. Issues flagged instantly.', tag: 'REAL-TIME' },
            { icon: '', title: 'Pattern Learning', desc: 'Common queries cached. Gets faster with use.', tag: 'CONTINUOUS' },
            { icon: '', title: 'Natural Language', desc: 'Ask in plain English. "How many employees in CA?"', tag: 'NO SQL' },
            { icon: '', title: 'Standards Validation', desc: 'Upload compliance rules once. Validate forever.', tag: 'AUTOMATED' },
          ].map((item, i) => (
            <div key={i} style={{
              background: colors.card,
              border: `1px solid ${colors.cardBorder}`,
              borderRadius: 12,
              padding: '1.5rem',
            }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: colors.primaryLight,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '1.1rem', marginBottom: '1rem',
              }}>{item.icon}</div>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.5rem', color: colors.text }}>{item.title}</h3>
              <p style={{ fontSize: '0.8rem', color: colors.textMuted, lineHeight: 1.5 }}>{item.desc}</p>
              <span style={{
                display: 'inline-block', marginTop: '0.75rem',
                padding: '0.25rem 0.5rem', background: colors.bg, borderRadius: 4,
                fontFamily: "'JetBrains Mono', monospace", fontSize: '0.65rem', color: colors.textMuted,
              }}>{item.tag}</span>
            </div>
          ))}
        </div>
      </Chapter>

      {/* Chapter 5: The Workflow */}
      <Chapter num={5} title="The Workflow" style={{ background: colors.bg }}>
        <Lead>From raw data to actionable findings in minutes, not weeks.</Lead>
        
        <div style={{ marginTop: '2rem', position: 'relative' }}>
          {/* Timeline line */}
          <div style={{
            position: 'absolute',
            left: 24,
            top: 0,
            bottom: 0,
            width: 3,
            background: `linear-gradient(180deg, ${colors.primary}, ${colors.accent}, #5f4282)`,
          }} />
          
          {[
            { num: 1, title: 'Upload Your Data', time: 'INSTANT', desc: 'Drop employee exports, configs, requirements.', details: ['Excel', 'CSV', 'PDF', 'Word'] },
            { num: 2, title: 'Automatic Analysis', time: '~30 SEC', desc: 'Classification, profiling, relationships detected.', details: ['Classify', 'Profile', 'Detect', 'Score'] },
            { num: 3, title: 'Ask Questions', time: '~2 SEC', desc: 'Natural language queries across all your data.', details: ['"How many missing SSNs?"'] },
            { num: 4, title: 'Run Playbooks', time: '~1 MIN', desc: 'Execute standard validation workflows.', details: ['Quality Audit', 'Compliance Check'] },
            { num: 5, title: 'Get Findings', time: 'AUTOMATIC', desc: 'Issues surfaced with recommendations.', details: ['Prioritized', 'Actionable'] },
          ].map((step, i) => (
            <div key={i} style={{ display: 'flex', gap: '2rem', marginBottom: '2rem', position: 'relative' }}>
              <div style={{
                width: 50, height: 50, borderRadius: '50%',
                background: colors.card, border: `3px solid ${colors.primary}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: "'Sora', sans-serif", fontWeight: 800, fontSize: '1.1rem', color: colors.primary,
                flexShrink: 0, zIndex: 1,
              }}>{step.num}</div>
              <div style={{
                flex: 1, background: colors.card, border: `1px solid ${colors.cardBorder}`,
                borderRadius: 12, padding: '1.5rem',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                  <div style={{ fontWeight: 700, color: colors.text }}>{step.title}</div>
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace", fontSize: '0.7rem',
                    color: colors.primary, background: colors.primaryLight,
                    padding: '0.25rem 0.5rem', borderRadius: 4,
                  }}>{step.time}</span>
                </div>
                <p style={{ fontSize: '0.85rem', color: colors.textMuted, marginBottom: '0.75rem' }}>{step.desc}</p>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {step.details.map((d, j) => (
                    <span key={j} style={{
                      fontSize: '0.7rem', padding: '0.35rem 0.6rem',
                      background: colors.bgAlt, borderRadius: 4, color: colors.textMuted,
                    }}>{d}</span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Chapter>

      {/* Chapter 6: The Value */}
      <Chapter num={6} title="Who This Is For" style={{ background: colors.bgAlt }}>
        <Lead>Built by consultants for consultants—and the customers who trust them.</Lead>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginTop: '2rem' }}>
          {[
            {
              title: 'For Consultants',
              badge: 'YOU',
              subtitle: 'Deliver better work in less time.',
              items: ['Cut analysis time by 80%', 'Systematic validation', 'Playbooks capture methodology', 'Natural language queries', 'Standards validate automatically'],
            },
            {
              title: 'For Customers',
              badge: 'THEM',
              subtitle: 'Visibility, quality, and confidence.',
              items: ['See exactly where project stands', 'Higher quality implementations', 'Issues caught early', 'Evidence-based readiness', 'Audit-ready documentation'],
            },
          ].map((panel, i) => (
            <div key={i} style={{
              background: colors.card, border: `1px solid ${colors.cardBorder}`,
              borderRadius: 16, padding: '2rem',
            }}>
              <h3 style={{
                fontFamily: "'Sora', sans-serif", fontSize: '1.25rem', fontWeight: 700,
                marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem',
                color: colors.text,
              }}>
                {panel.title}
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace", fontSize: '0.6rem',
                  padding: '0.25rem 0.5rem', background: colors.primaryLight, color: colors.primary,
                  borderRadius: 4, letterSpacing: '0.5px',
                }}>{panel.badge}</span>
              </h3>
              <p style={{ fontSize: '0.85rem', color: colors.textMuted, marginBottom: '1.5rem' }}>{panel.subtitle}</p>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {panel.items.map((item, j) => (
                  <li key={j} style={{
                    display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
                    padding: '0.75rem 0', borderBottom: j < panel.items.length - 1 ? `1px solid ${colors.cardBorder}` : 'none',
                    fontSize: '0.9rem', color: colors.text,
                  }}>
                    <span style={{ color: colors.primary }}>✓</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Chapter>

      {/* Chapter 7: CTA */}
      <Chapter num={7} title="Ready to See It?" style={{ background: colors.bg, textAlign: 'center', minHeight: 'auto', padding: '6rem 2rem' }}>
        <div style={{
          background: colors.card, border: `2px solid ${colors.primary}`,
          borderRadius: 20, padding: '4rem', maxWidth: 700, margin: '0 auto',
        }}>
          <p style={{ color: colors.textMuted, fontSize: '1.1rem', marginBottom: '2rem' }}>
            This isn't a pitch deck. This is the product. Let's go.
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.75rem',
              padding: '1rem 2rem', background: colors.primary, color: 'white',
              border: 'none', borderRadius: 12, fontSize: '1rem', fontWeight: 700,
              cursor: 'pointer', fontFamily: "'Sora', sans-serif",
            }}
          >
            Enter XLR8 <span>→</span>
          </button>
        </div>
      </Chapter>

      {/* Footer */}
      <footer style={{
        padding: '2rem', textAlign: 'center', color: colors.textLight,
        fontSize: '0.8rem', background: colors.bg, borderTop: `1px solid ${colors.cardBorder}`,
      }}>
        Built with  by <span style={{ color: colors.primary }}>XLR8</span> · The platform that replaced our spreadsheets
      </footer>
    </div>
  );
}
