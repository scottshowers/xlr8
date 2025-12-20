/**
 * JourneyPage.jsx - The XLR8 Journey (Visual Infographic)
 * 
 * Connected flowchart-style visual journey with illustrations.
 * Route: /journey
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

const getColors = (dark) => ({
  bg: dark ? '#12151c' : '#f5f6f8',
  bgPattern: dark ? '#1a1e28' : '#e8eaef',
  card: dark ? '#1e232e' : '#ffffff',
  border: dark ? '#2a2f3a' : '#d4d9e1',
  text: dark ? '#e4e6ea' : '#2d3643',
  textMuted: dark ? '#8b95a5' : '#6b7a8f',
  primary: '#83b16d',
  primaryDark: '#6a9b5a',
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.12)',
  dustyBlue: '#7889a0',
  dustyBlueLight: dark ? 'rgba(120, 137, 160, 0.15)' : 'rgba(120, 137, 160, 0.12)',
  taupe: '#9b8f82',
  taupeLight: dark ? 'rgba(155, 143, 130, 0.15)' : 'rgba(155, 143, 130, 0.12)',
  slate: '#6b7a8f',
  error: '#a07070',
});

export default function JourneyPage() {
  const navigate = useNavigate();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);

  const ArrowDown = () => (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '1rem 0' }}>
      <div style={{ width: 3, height: 40, background: colors.primary }} />
      <div style={{
        width: 0, height: 0,
        borderLeft: '8px solid transparent',
        borderRight: '8px solid transparent',
        borderTop: `10px solid ${colors.primary}`,
      }} />
    </div>
  );

  const SectionDivider = ({ label }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', margin: '3rem 0' }}>
      <div style={{
        flex: 1, height: 2,
        background: `repeating-linear-gradient(90deg, ${colors.primary}, ${colors.primary} 8px, transparent 8px, transparent 16px)`,
      }} />
      <div style={{
        fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: '0.75rem',
        color: colors.primary, textTransform: 'uppercase', letterSpacing: 2,
        padding: '0.5rem 1rem', background: colors.card, border: `2px solid ${colors.primary}`,
        borderRadius: 20,
      }}>{label}</div>
      <div style={{
        flex: 1, height: 2,
        background: `repeating-linear-gradient(90deg, ${colors.primary}, ${colors.primary} 8px, transparent 8px, transparent 16px)`,
      }} />
    </div>
  );

  const StoryBlock = ({ chapter, title, children }) => (
    <div style={{ maxWidth: 500, margin: '0 auto', textAlign: 'center' }}>
      <div style={{
        fontFamily: "'Sora', sans-serif", fontSize: '0.7rem', fontWeight: 700,
        color: colors.primary, textTransform: 'uppercase', letterSpacing: 2, marginBottom: '0.5rem',
      }}>Chapter {chapter.toString().padStart(2, '0')}</div>
      <h2 style={{
        fontFamily: "'Sora', sans-serif", fontSize: '1.5rem', fontWeight: 800,
        marginBottom: '0.75rem', letterSpacing: '-0.01em', color: colors.text,
      }}>{title}</h2>
      <p style={{ color: colors.textMuted, fontSize: '0.9rem', lineHeight: 1.6 }}>{children}</p>
    </div>
  );

  return (
    <div style={{ background: colors.bg, minHeight: '100vh', fontFamily: "'Inter', system-ui, sans-serif" }}>
      <div style={{ maxWidth: 1000, margin: '0 auto', padding: '2rem' }}>
        
        {/* Header Banner */}
        <div style={{
          background: colors.primary,
          borderRadius: '12px 12px 0 0',
          padding: '1.5rem 2rem',
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}>
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
            background: `repeating-linear-gradient(90deg, transparent, transparent 20px, rgba(255,255,255,0.03) 20px, rgba(255,255,255,0.03) 40px)`,
          }} />
          <h1 style={{
            fontFamily: "'Sora', sans-serif", fontSize: '2rem', fontWeight: 800,
            color: 'white', letterSpacing: '0.1em', textTransform: 'uppercase',
            position: 'relative',
          }}>The XLR8 Journey</h1>
          <p style={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.85rem', marginTop: '0.5rem', position: 'relative' }}>
            How We Transformed Implementation Analysis
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            style={{
              position: 'absolute', top: '1rem', right: '1rem',
              padding: '0.4rem 0.8rem', background: 'rgba(255,255,255,0.2)',
              border: '1px solid rgba(255,255,255,0.3)', color: 'white',
              borderRadius: 6, fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
            }}
          >
            Skip →
          </button>
        </div>

        {/* Main Content */}
        <div style={{
          background: colors.card,
          border: `3px solid ${colors.primary}`,
          borderTop: 'none',
          borderRadius: '0 0 12px 12px',
          padding: '3rem 2rem',
          position: 'relative',
        }}>
          {/* Dot pattern overlay */}
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
            backgroundImage: `radial-gradient(circle at 20px 20px, ${colors.bgPattern} 2px, transparent 2px)`,
            backgroundSize: '40px 40px',
            opacity: 0.5,
            pointerEvents: 'none',
          }} />

          <div style={{ position: 'relative', zIndex: 1 }}>

            {/* Chapter 1: The Starting Point */}
            <StoryBlock chapter={1} title="The Starting Point">
              We were implementation consultants drowning in spreadsheets. Every project meant weeks of manual work, copy-paste validation, and hoping we didn't miss anything critical.
            </StoryBlock>

            {/* Illustration: Old way */}
            <div style={{ display: 'flex', justifyContent: 'center', margin: '1.5rem 0' }}>
              <svg width="300" height="100" viewBox="0 0 300 100">
                {/* Spreadsheet stack */}
                <rect x="20" y="35" width="50" height="40" rx="4" fill={colors.bg} stroke={colors.border} strokeWidth="2"/>
                <rect x="28" y="27" width="50" height="40" rx="4" fill={colors.bg} stroke={colors.border} strokeWidth="2"/>
                <rect x="36" y="19" width="50" height="40" rx="4" fill={colors.card} stroke={colors.border} strokeWidth="2"/>
                <line x1="44" y1="30" x2="78" y2="30" stroke={colors.border} strokeWidth="2"/>
                <line x1="44" y1="38" x2="72" y2="38" stroke={colors.border} strokeWidth="2"/>
                <line x1="44" y1="46" x2="68" y2="46" stroke={colors.border} strokeWidth="2"/>
                
                {/* Arrow */}
                <path d="M 105 45 L 135 45" stroke={colors.slate} strokeWidth="2" strokeDasharray="4,4"/>
                
                {/* Person stressed */}
                <circle cx="175" cy="40" r="18" fill={colors.bg} stroke={colors.slate} strokeWidth="2"/>
                <circle cx="169" cy="37" r="2" fill={colors.slate}/>
                <circle cx="181" cy="37" r="2" fill={colors.slate}/>
                <path d="M 169 47 Q 175 43 181 47" stroke={colors.slate} strokeWidth="2" fill="none"/>
                
                {/* Clock */}
                <circle cx="245" cy="45" r="22" fill={colors.bg} stroke={colors.border} strokeWidth="2"/>
                <circle cx="245" cy="45" r="3" fill={colors.slate}/>
                <line x1="245" y1="45" x2="245" y2="32" stroke={colors.slate} strokeWidth="2"/>
                <line x1="245" y1="45" x2="255" y2="50" stroke={colors.slate} strokeWidth="2"/>
                <text x="235" y="78" fontSize="10" fill={colors.textMuted}>WEEKS</text>
              </svg>
            </div>

            <ArrowDown />

            {/* Chapter 2: The Trigger */}
            <StoryBlock chapter={2} title="The Trigger">
              We asked ourselves: what if we could teach a system to do what we do? What if our expertise could scale without us?
            </StoryBlock>

            {/* Side by side comparison */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '1.5rem', margin: '2rem 0', alignItems: 'center' }}>
              <div style={{ background: colors.bg, borderRadius: 12, padding: '1.25rem', borderLeft: `4px solid ${colors.slate}` }}>
                <div style={{ fontFamily: "'Sora', sans-serif", fontSize: '0.7rem', fontWeight: 700, color: colors.slate, letterSpacing: 1, marginBottom: '0.75rem' }}>THE OLD WAY</div>
                {['Weeks in spreadsheets', 'Manual cross-referencing', 'Hope you didn\'t miss anything', 'Start over every project'].map((item, i) => (
                  <div key={i} style={{ fontSize: '0.75rem', color: colors.textMuted, padding: '0.4rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ color: colors.error }}>✗</span> {item}
                  </div>
                ))}
              </div>
              
              <div style={{ fontSize: '1.5rem', color: colors.primary }}>→</div>
              
              <div style={{ background: colors.bg, borderRadius: 12, padding: '1.25rem', borderLeft: `4px solid ${colors.primary}` }}>
                <div style={{ fontFamily: "'Sora', sans-serif", fontSize: '0.7rem', fontWeight: 700, color: colors.primary, letterSpacing: 1, marginBottom: '0.75rem' }}>THE XLR8 WAY</div>
                {['Minutes, not weeks', 'Automatic analysis', 'Nothing missed—ever', 'Patterns learned & reused'].map((item, i) => (
                  <div key={i} style={{ fontSize: '0.75rem', color: colors.textMuted, padding: '0.4rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ color: colors.primary }}>✓</span> {item}
                  </div>
                ))}
              </div>
            </div>

            <ArrowDown />

            {/* Chapter 3: The Insight */}
            <StoryBlock chapter={3} title="The Core Insight">
              Every engagement has three sources of truth. Connect them, and you see everything—including compliance gaps that could sink you.
            </StoryBlock>

            {/* Three Truths */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', margin: '2rem 0', flexWrap: 'wrap', alignItems: 'center' }}>
              {[
                { icon: '🗄️', label: 'Reality', sub: 'What exists', bg: colors.primaryLight, border: colors.primary, color: colors.primaryDark },
                { icon: '📋', label: 'Intent', sub: 'What was asked', bg: colors.dustyBlueLight, border: colors.dustyBlue, color: colors.dustyBlue },
                { icon: '⚖️', label: 'Reference', sub: 'Laws & Compliance', bg: colors.taupeLight, border: colors.taupe, color: colors.taupe },
              ].map((truth, i) => (
                <React.Fragment key={i}>
                  {i > 0 && <span style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.5rem', fontWeight: 800, color: colors.border }}>×</span>}
                  <div style={{
                    width: 120, padding: '1rem', borderRadius: 12, textAlign: 'center',
                    background: truth.bg, border: `2px solid ${truth.border}`,
                  }}>
                    <div style={{ fontSize: '1.75rem', marginBottom: '0.4rem' }}>{truth.icon}</div>
                    <div style={{ fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: '0.8rem', color: truth.color }}>{truth.label}</div>
                    <div style={{ fontSize: '0.65rem', color: colors.textMuted }}>{truth.sub}</div>
                  </div>
                </React.Fragment>
              ))}
            </div>

            {/* Connecting visual */}
            <div style={{ display: 'flex', justifyContent: 'center', margin: '1.5rem 0' }}>
              <svg width="300" height="70" viewBox="0 0 300 70">
                <line x1="60" y1="35" x2="150" y2="35" stroke={colors.primary} strokeWidth="2"/>
                <line x1="240" y1="35" x2="150" y2="35" stroke={colors.primary} strokeWidth="2"/>
                <circle cx="150" cy="35" r="25" fill={colors.primary} stroke={colors.primaryDark} strokeWidth="3"/>
                <text x="150" y="32" textAnchor="middle" fill="white" fontSize="9" fontWeight="bold">COMPLETE</text>
                <text x="150" y="43" textAnchor="middle" fill="rgba(255,255,255,0.8)" fontSize="8">PICTURE</text>
                <circle cx="150" cy="35" r="30" fill="none" stroke={colors.primary} strokeWidth="1" opacity="0.3"/>
                <circle cx="150" cy="35" r="36" fill="none" stroke={colors.primary} strokeWidth="1" opacity="0.15"/>
              </svg>
            </div>
            
            {/* Compliance callout */}
            <div style={{
              margin: '1.5rem auto',
              maxWidth: 500,
              padding: '1rem',
              background: colors.taupeLight,
              border: `2px solid ${colors.taupe}`,
              borderRadius: 10,
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.75rem',
            }}>
              <span style={{ fontSize: '1.25rem' }}>⚖️</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.8rem', color: colors.text, marginBottom: '0.3rem' }}>
                  Reference = Legs & Regs
                </div>
                <p style={{ fontSize: '0.7rem', color: colors.textMuted, margin: 0, lineHeight: 1.5 }}>
                  FLSA, ACA, state labor laws, data privacy. Not just best practice—legal exposure. 
                  Catch compliance gaps before they become audit findings.
                </p>
              </div>
            </div>

            <SectionDivider label="The Build" />

            {/* Chapter 4: Building Blocks */}
            <StoryBlock chapter={4} title="The Building Blocks">
              We built an intelligence layer that learns from every upload, every query, every validation.
            </StoryBlock>

            {/* Blocks grid */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap', margin: '2rem 0' }}>
              {[
                { icon: '🧠', label: 'Classifier' },
                { icon: '🔗', label: 'Linker' },
                { icon: '📊', label: 'Profiler' },
                { icon: '✅', label: 'Validator' },
                { icon: '⚖️', label: 'Compliance' },
                { icon: '💬', label: 'Query' },
                { icon: '📚', label: 'Learning' },
              ].map((block, i) => (
                <div key={i} style={{
                  width: 85, height: 70, background: colors.card, border: `2px solid ${colors.border}`,
                  borderRadius: 8, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                  transition: 'all 0.2s ease', cursor: 'default',
                }}>
                  <div style={{ fontSize: '1.4rem', marginBottom: '0.2rem' }}>{block.icon}</div>
                  <div style={{ fontSize: '0.6rem', fontWeight: 600, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{block.label}</div>
                </div>
              ))}
            </div>

            <ArrowDown />

            {/* Chapter 5: The Flow */}
            <StoryBlock chapter={5} title="How It Works">
              Upload → Analyze → Ask → Validate → Act. In minutes, not weeks.
            </StoryBlock>

            {/* Flow path */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', position: 'relative', padding: '2rem 0', marginTop: '1rem' }}>
              {/* Connecting line */}
              <div style={{
                position: 'absolute', top: 35, left: 55, right: 55, height: 3, background: colors.primary,
              }} />
              
              {[
                { icon: '📤', label: 'Upload', time: 'Instant' },
                { icon: '🧠', label: 'Analyze', time: '~30 sec' },
                { icon: '💬', label: 'Ask', time: '~2 sec' },
                { icon: '✅', label: 'Validate', time: '~1 min' },
                { icon: '🎯', label: 'Act', time: 'Ready' },
              ].map((step, i) => (
                <div key={i} style={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
                  <div style={{
                    width: 55, height: 55, borderRadius: '50%', background: colors.card,
                    border: `3px solid ${colors.primary}`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    margin: '0 auto 0.5rem', fontSize: '1.25rem',
                  }}>{step.icon}</div>
                  <div style={{ fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: '0.65rem', color: colors.text, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{step.label}</div>
                  <div style={{ fontSize: '0.6rem', color: colors.primary, fontWeight: 600, marginTop: '0.15rem' }}>{step.time}</div>
                </div>
              ))}
            </div>

            <SectionDivider label="The Result" />

            {/* Chapter 6: The Value */}
            <StoryBlock chapter={6} title="The Transformation">
              What used to take weeks now takes minutes. What used to slip through now gets caught. Every time.
            </StoryBlock>

            {/* Results grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', margin: '2rem 0' }}>
              {[
                { value: '80%', label: 'Faster Analysis' },
                { value: '3×', label: 'More Coverage' },
                { value: 'Zero', label: 'Missed Issues' },
              ].map((result, i) => (
                <div key={i} style={{ background: colors.bg, borderRadius: 10, padding: '1.25rem', textAlign: 'center' }}>
                  <div style={{ fontFamily: "'Sora', sans-serif", fontSize: '2rem', fontWeight: 800, color: colors.primary }}>{result.value}</div>
                  <div style={{ fontSize: '0.8rem', color: colors.textMuted, marginTop: '0.25rem' }}>{result.label}</div>
                </div>
              ))}
            </div>

            {/* Happy consultant illustration */}
            <div style={{ display: 'flex', justifyContent: 'center', margin: '2rem 0' }}>
              <svg width="280" height="80" viewBox="0 0 280 80">
                {/* Platform */}
                <rect x="90" y="15" width="80" height="50" rx="8" fill={colors.card} stroke={colors.primary} strokeWidth="3"/>
                <text x="130" y="35" textAnchor="middle" fill={colors.primary} fontWeight="bold" fontSize="12">XLR8</text>
                <rect x="102" y="42" width="56" height="4" rx="2" fill={colors.primaryLight}/>
                <rect x="102" y="50" width="40" height="4" rx="2" fill={colors.primaryLight}/>
                
                {/* Happy person */}
                <circle cx="220" cy="38" r="18" fill={colors.bg} stroke={colors.primary} strokeWidth="2"/>
                <circle cx="214" cy="35" r="2" fill={colors.primary}/>
                <circle cx="226" cy="35" r="2" fill={colors.primary}/>
                <path d="M 214 44 Q 220 50 226 44" stroke={colors.primary} strokeWidth="2" fill="none"/>
                
                {/* Arrow */}
                <path d="M 175 40 L 195 40" stroke={colors.primary} strokeWidth="2"/>
                <polygon points="195,35 205,40 195,45" fill={colors.primary}/>
              </svg>
            </div>

            {/* CTA */}
            <div style={{
              textAlign: 'center', marginTop: '2rem', padding: '2rem',
              background: colors.bg, borderRadius: 12,
            }}>
              <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem', color: colors.text }}>
                Ready to Experience It?
              </h3>
              <p style={{ color: colors.textMuted, fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                This isn't a brochure. This is the product. Let's go.
              </p>
              <button
                onClick={() => navigate('/dashboard')}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                  padding: '0.875rem 1.75rem', background: colors.primary, color: 'white',
                  border: 'none', borderRadius: 10, fontFamily: "'Sora', sans-serif",
                  fontSize: '0.95rem', fontWeight: 700, cursor: 'pointer',
                }}
              >
                Enter XLR8 →
              </button>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
