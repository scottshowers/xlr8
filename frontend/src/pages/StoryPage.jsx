/**
 * StoryPage.jsx - The XLR8 Story (Narrative Version)
 * 
 * Scrolling chapter-based narrative explaining the platform.
 * Route: /story
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

const getColors = (dark) => ({
  bg: dark ? '#12151c' : '#f5f6f8',
  bgAlt: dark ? '#1a1e28' : '#eef0f4',
  card: dark ? '#1e232e' : '#ffffff',
  cardBorder: dark ? '#2a2f3a' : '#e4e7ec',
  text: dark ? '#e4e6ea' : '#2d3643',
  textMuted: dark ? '#8b95a5' : '#6b7a8f',
  textLight: dark ? '#5f6a7d' : '#9aa5b5',
  primary: '#83b16d',
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.1)',
  primaryDark: '#6a9b5a',
  dustyBlue: '#7889a0',
  dustyBlueLight: dark ? 'rgba(120, 137, 160, 0.15)' : 'rgba(120, 137, 160, 0.1)',
  taupe: '#9b8f82',
  taupeLight: dark ? 'rgba(155, 143, 130, 0.15)' : 'rgba(155, 143, 130, 0.1)',
  slate: '#6b7a8f',
  slateLight: dark ? 'rgba(107, 122, 143, 0.15)' : 'rgba(107, 122, 143, 0.1)',
  error: '#a07070',
  errorLight: dark ? 'rgba(160, 112, 112, 0.15)' : 'rgba(160, 112, 112, 0.1)',
});

export default function StoryPage() {
  const navigate = useNavigate();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
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

  const Lead = ({ children }) => (
    <p style={{
      fontSize: '1.15rem',
      color: colors.textMuted,
      maxWidth: 600,
      lineHeight: 1.7,
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
        background: darkMode ? 'rgba(18, 21, 28, 0.95)' : 'rgba(245, 246, 248, 0.95)',
        backdropFilter: 'blur(10px)',
        zIndex: 100,
        borderBottom: `1px solid ${colors.cardBorder}`,
      }}>
        <div style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: '1.4rem',
          fontWeight: 800,
          color: colors.primary,
        }}>XLR8</div>
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
          <div style={{ color: colors.slate }}>// The question we asked</div>
          <div style={{ marginTop: '0.5rem' }}>
            <span style={{ color: colors.primary }}>const</span> problem = {'{'}
          </div>
          <div style={{ paddingLeft: '1rem', color: colors.textMuted }}>
            hours: <span style={{ color: colors.dustyBlue }}>"too many"</span>,
          </div>
          <div style={{ paddingLeft: '1rem', color: colors.textMuted }}>
            mistakes: <span style={{ color: colors.dustyBlue }}>"inevitable"</span>,
          </div>
          <div style={{ paddingLeft: '1rem', color: colors.textMuted }}>
            knowledge: <span style={{ color: colors.dustyBlue }}>"trapped"</span>
          </div>
          <div>{'}'}</div>
        </div>
      </Chapter>

      {/* Chapter 2: The Transformation */}
      <Chapter num={2} title="The Transformation" style={{ background: colors.bgAlt }}>
        <Lead>Here's what changed when we stopped accepting "that's just how it's done."</Lead>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '2rem', marginTop: '2rem', alignItems: 'center' }}>
          {/* Old Way */}
          <div style={{ background: colors.card, border: `1px solid ${colors.cardBorder}`, borderRadius: 12, padding: '1.5rem' }}>
            <div style={{ fontFamily: "'Sora', sans-serif", fontSize: '0.75rem', fontWeight: 700, color: colors.slate, letterSpacing: 1, marginBottom: '1rem' }}>THE OLD WAY</div>
            {['Weeks in spreadsheets', 'Manual validation', 'Knowledge silos', 'Incomplete coverage'].map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 0', borderBottom: i < 3 ? `1px dashed ${colors.cardBorder}` : 'none' }}>
                <span style={{ color: colors.error }}>✗</span>
                <span style={{ fontSize: '0.85rem', color: colors.textMuted }}>{item}</span>
              </div>
            ))}
          </div>
          
          {/* Arrow */}
          <div style={{ fontSize: '2rem', color: colors.primary }}>→</div>
          
          {/* New Way */}
          <div style={{ background: colors.card, border: `2px solid ${colors.primary}`, borderRadius: 12, padding: '1.5rem' }}>
            <div style={{ fontFamily: "'Sora', sans-serif", fontSize: '0.75rem', fontWeight: 700, color: colors.primary, letterSpacing: 1, marginBottom: '1rem' }}>THE XLR8 WAY</div>
            {['Minutes, not weeks', 'Automatic validation', 'Knowledge captured', 'Complete coverage'].map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 0', borderBottom: i < 3 ? `1px dashed ${colors.primaryLight}` : 'none' }}>
                <span style={{ color: colors.primary }}>✓</span>
                <span style={{ fontSize: '0.85rem', color: colors.textMuted }}>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </Chapter>

      {/* Chapter 3: The Core Insight */}
      <Chapter num={3} title="The Core Insight" style={{ background: colors.bg }}>
        <Lead>Every engagement has three sources of truth. The magic happens when you connect them—especially when compliance is on the line.</Lead>
        
        <div style={{
          background: colors.card,
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: 16,
          padding: '3rem',
          marginTop: '2rem',
          textAlign: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
            {[
              { icon: '🗄️', label: 'Reality', sub: 'What exists', color: colors.primary, bg: colors.primaryLight },
              { icon: '📋', label: 'Intent', sub: 'What was asked', color: colors.dustyBlue, bg: colors.dustyBlueLight },
              { icon: '⚖️', label: 'Reference', sub: 'Laws & Compliance', color: colors.taupe, bg: colors.taupeLight },
            ].map((truth, i) => (
              <React.Fragment key={i}>
                {i > 0 && <span style={{ fontFamily: "'Sora', sans-serif", fontSize: '2rem', fontWeight: 800, color: colors.cardBorder }}>×</span>}
                <div style={{
                  padding: '1.5rem 2rem',
                  borderRadius: 12,
                  background: truth.bg,
                  border: `2px solid ${truth.color}`,
                  minWidth: 140,
                }}>
                  <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>{truth.icon}</div>
                  <div style={{ fontFamily: "'Sora', sans-serif", fontWeight: 700, color: truth.color }}>{truth.label}</div>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>{truth.sub}</div>
                </div>
              </React.Fragment>
            ))}
            <span style={{ fontFamily: "'Sora', sans-serif", fontSize: '2rem', fontWeight: 800, color: colors.cardBorder }}>=</span>
            <div style={{
              background: `linear-gradient(135deg, ${colors.primary}, ${colors.dustyBlue})`,
              color: 'white',
              padding: '1rem 2rem',
              borderRadius: 12,
              fontFamily: "'Sora', sans-serif",
              fontWeight: 700,
            }}>
              Complete Picture
            </div>
          </div>
          
          {/* Compliance callout */}
          <div style={{
            marginTop: '2rem',
            padding: '1.5rem',
            background: colors.taupeLight,
            border: `1px solid ${colors.taupe}`,
            borderRadius: 12,
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
              <span style={{ fontSize: '1.5rem' }}>⚖️</span>
              <div>
                <div style={{ fontWeight: 700, color: colors.text, marginBottom: '0.5rem' }}>
                  Reference = The "Oh Shit" Layer
                </div>
                <p style={{ fontSize: '0.9rem', color: colors.textMuted, margin: 0, lineHeight: 1.6 }}>
                  Legislation. Regulations. Compliance requirements. FLSA, ACA, state labor laws, data privacy rules. 
                  This isn't just best practice—it's legal exposure. XLR8 validates your data against the laws that 
                  matter, catching compliance gaps before they become audit findings or lawsuits.
                </p>
              </div>
            </div>
          </div>
        </div>
      </Chapter>

      {/* Chapter 4: Built-In Intelligence */}
      <Chapter num={4} title="Built-In Intelligence" style={{ background: colors.bgAlt }}>
        <Lead>Not just storage. Not just search. Actual understanding.</Lead>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem', marginTop: '2rem' }}>
          {[
            { icon: '🎯', title: 'Auto-Classification', desc: 'Documents routed to the right Truth layer automatically.', tag: 'ON UPLOAD' },
            { icon: '🔗', title: 'Relationship Discovery', desc: 'Foreign keys found. Smart JOINs without config.', tag: 'AUTOMATIC' },
            { icon: '📊', title: 'Data Quality Scoring', desc: 'Every file gets a health score. Issues flagged instantly.', tag: 'REAL-TIME' },
            { icon: '🧠', title: 'Pattern Learning', desc: 'Common queries cached. Gets faster with use.', tag: 'CONTINUOUS' },
            { icon: '💬', title: 'Natural Language', desc: 'Ask in plain English. "How many employees in CA?"', tag: 'NO SQL' },
            { icon: '✅', title: 'Standards Validation', desc: 'Upload compliance rules once. Validate forever.', tag: 'AUTOMATED' },
          ].map((item, i) => (
            <div key={i} style={{
              background: colors.card,
              border: `1px solid ${colors.cardBorder}`,
              borderRadius: 12,
              padding: '1.5rem',
              transition: 'all 0.2s ease',
              cursor: 'default',
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
            background: `linear-gradient(180deg, ${colors.primary}, ${colors.dustyBlue}, ${colors.taupe})`,
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
                  <div style={{ fontWeight: 700 }}>{step.title}</div>
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
              <ul style={{ listStyle: 'none' }}>
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
              transition: 'all 0.2s ease',
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
        Built with 💚 by <span style={{ color: colors.primary }}>XLR8</span> · The platform that replaced our spreadsheets
      </footer>
    </div>
  );
}
