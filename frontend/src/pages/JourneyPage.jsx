/**
 * JourneyPage.jsx - The XLR8 Journey (Visual Infographic)
 * 
 * UPDATED: December 23, 2025
 * - Mission Control color palette (#83b16d)
 * - Removed dark mode
 * 
 * Connected flowchart-style visual journey with illustrations.
 * Route: /journey
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Rocket } from 'lucide-react';

// Mission Control Colors
const colors = {
  bg: '#f0f2f5',
  bgPattern: '#e8ebf0',
  card: '#ffffff',
  border: '#e2e8f0',
  text: '#1a2332',
  textMuted: '#64748b',
  textLight: '#94a3b8',
  primary: '#83b16d',
  primaryDark: '#6b9b5a',
  primaryLight: 'rgba(131, 177, 109, 0.12)',
  accent: '#285390',
  accentLight: 'rgba(40, 83, 144, 0.12)',
  purple: '#5f4282',
  purpleLight: 'rgba(95, 66, 130, 0.12)',
  warning: '#d97706',
  warningLight: 'rgba(217, 119, 6, 0.12)',
};

export default function JourneyPage() {
  const navigate = useNavigate();

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
          background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryDark} 100%)`,
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
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', marginBottom: '0.5rem', position: 'relative' }}>
            <h1 style={{
              fontFamily: "'Sora', sans-serif", fontSize: '2rem', fontWeight: 800,
              color: 'white', letterSpacing: '0.1em', textTransform: 'uppercase',
            }}>The XLR8 Journey</h1>
            <Rocket size={24} color="white" />
          </div>
          <p style={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.85rem', position: 'relative' }}>
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
                <path d="M 105 45 L 135 45" stroke={colors.textLight} strokeWidth="2" strokeDasharray="4,4"/>
                
                {/* Person stressed */}
                <circle cx="175" cy="40" r="18" fill={colors.bg} stroke={colors.textLight} strokeWidth="2"/>
                <circle cx="169" cy="37" r="2" fill={colors.textLight}/>
                <circle cx="181" cy="37" r="2" fill={colors.textLight}/>
                <path d="M 169 47 Q 175 43 181 47" stroke={colors.textLight} strokeWidth="2" fill="none"/>
                
                {/* Clock */}
                <circle cx="245" cy="45" r="22" fill={colors.bg} stroke={colors.border} strokeWidth="2"/>
                <circle cx="245" cy="45" r="3" fill={colors.textLight}/>
                <line x1="245" y1="45" x2="245" y2="32" stroke={colors.textLight} strokeWidth="2"/>
                <line x1="245" y1="45" x2="257" y2="45" stroke={colors.textLight} strokeWidth="2"/>
              </svg>
            </div>

            <ArrowDown />

            {/* Chapter 2: The Insight */}
            <StoryBlock chapter={2} title="The Insight">
              Every question about a project has three sides: what IS (the data), what SHOULD BE (the requirements), and what's RIGHT (the standards).
            </StoryBlock>

            <SectionDivider label="Three Truths" />

            {/* Chapter 3: Three Truths */}
            <StoryBlock chapter={3} title="The Three Truths">
              We built a system that knows all three—and can compare them instantly.
            </StoryBlock>

            {/* Three Truths Diagram */}
            <div style={{ display: 'flex', justifyContent: 'center', margin: '2rem 0' }}>
              <svg width="320" height="80" viewBox="0 0 320 80">
                {/* Reality */}
                <rect x="10" y="15" width="80" height="50" rx="8" fill={colors.primaryLight} stroke={colors.primary} strokeWidth="2"/>
                <text x="50" y="35" textAnchor="middle" fill={colors.primary} fontWeight="bold" fontSize="10">REALITY</text>
                <text x="50" y="48" textAnchor="middle" fill={colors.primary} fontSize="8">What IS</text>

                {/* Intent */}
                <rect x="120" y="15" width="80" height="50" rx="8" fill={colors.accentLight} stroke={colors.accent} strokeWidth="2"/>
                <text x="160" y="35" textAnchor="middle" fill={colors.accent} fontWeight="bold" fontSize="10">INTENT</text>
                <text x="160" y="48" textAnchor="middle" fill={colors.accent} fontSize="8">What SHOULD BE</text>

                {/* Reference */}
                <rect x="230" y="15" width="80" height="50" rx="8" fill={colors.purpleLight} stroke={colors.purple} strokeWidth="2"/>
                <text x="270" y="35" textAnchor="middle" fill={colors.purple} fontWeight="bold" fontSize="10">REFERENCE</text>
                <text x="270" y="48" textAnchor="middle" fill={colors.purple} fontSize="8">Best Practice</text>

                {/* Connecting lines */}
                <line x1="90" y1="40" x2="120" y2="40" stroke={colors.border} strokeWidth="2"/>
                <line x1="200" y1="40" x2="230" y2="40" stroke={colors.border} strokeWidth="2"/>
              </svg>
            </div>
            
            {/* Compliance callout */}
            <div style={{
              margin: '1.5rem auto',
              maxWidth: 500,
              padding: '1rem',
              background: colors.warningLight,
              border: `2px solid ${colors.warning}`,
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
