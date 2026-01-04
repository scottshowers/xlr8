/**
 * JourneyPage.jsx - The XLR8 Journey (Visual Infographic)
 * 
 * UPDATED: December 25, 2025
 * - Five Truths Architecture
 * - Context Graph positioning
 * - Lifecycle framing (not just implementation)
 * - Investor-ready storytelling
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Rocket, Database, FileText, Settings, BookOpen, Scale, Shield, Network, Sparkles, ArrowRight } from 'lucide-react';

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
  scarlet: '#993c44',
  scarletLight: 'rgba(153, 60, 68, 0.12)',
  electricBlue: '#4a7a9a',
};

export default function JourneyPage() {
  const navigate = useNavigate();

  const ArrowDown = () => (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '1.5rem 0' }}>
      <div style={{ width: 3, height: 50, background: `linear-gradient(to bottom, ${colors.primary}, ${colors.accent})` }} />
      <div style={{
        width: 0, height: 0,
        borderLeft: '10px solid transparent',
        borderRight: '10px solid transparent',
        borderTop: `12px solid ${colors.accent}`,
      }} />
    </div>
  );

  const SectionDivider = ({ label, color = colors.primary }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', margin: '3rem 0' }}>
      <div style={{
        flex: 1, height: 2,
        background: `repeating-linear-gradient(90deg, ${color}, ${color} 8px, transparent 8px, transparent 16px)`,
      }} />
      <div style={{
        fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: '0.75rem',
        color: color, textTransform: 'uppercase', letterSpacing: 2,
        padding: '0.5rem 1rem', background: colors.card, border: `2px solid ${color}`,
        borderRadius: 20,
      }}>{label}</div>
      <div style={{
        flex: 1, height: 2,
        background: `repeating-linear-gradient(90deg, ${color}, ${color} 8px, transparent 8px, transparent 16px)`,
      }} />
    </div>
  );

  const StoryBlock = ({ chapter, title, children, highlight }) => (
    <div style={{ maxWidth: 600, margin: '0 auto', textAlign: 'center' }}>
      <div style={{
        fontFamily: "'Sora', sans-serif", fontSize: '0.7rem', fontWeight: 700,
        color: highlight || colors.primary, textTransform: 'uppercase', letterSpacing: 2, marginBottom: '0.5rem',
      }}>Chapter {chapter.toString().padStart(2, '0')}</div>
      <h2 style={{
        fontFamily: "'Sora', sans-serif", fontSize: '1.6rem', fontWeight: 800,
        marginBottom: '0.75rem', letterSpacing: '-0.01em', color: colors.text,
      }}>{title}</h2>
      <p style={{ color: colors.textMuted, fontSize: '0.95rem', lineHeight: 1.7 }}>{children}</p>
    </div>
  );

  return (
    <div style={{ background: colors.bg, minHeight: '100vh', fontFamily: "'Inter', system-ui, sans-serif" }}>
      <div style={{ maxWidth: 1000, margin: '0 auto', padding: '2rem' }}>
        
        {/* Header Banner */}
        <div style={{
          background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryDark} 100%)`,
          borderRadius: '16px 16px 0 0',
          padding: '2rem',
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}>
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
            background: `repeating-linear-gradient(90deg, transparent, transparent 20px, rgba(255,255,255,0.03) 20px, rgba(255,255,255,0.03) 40px)`,
          }} />
          <div style={{ position: 'relative' }}>
            <div style={{ 
              display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.4rem 1rem', background: 'rgba(255,255,255,0.2)', 
              borderRadius: '20px', fontSize: '0.8rem', fontWeight: '600', marginBottom: '1rem',
              color: 'white'
            }}>
              <Network size={14} /> The Context Graph Story
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <h1 style={{
                fontFamily: "'Sora', sans-serif", fontSize: '2.25rem', fontWeight: 800,
                color: 'white', letterSpacing: '0.05em', textTransform: 'uppercase',
              }}>The XLR8 Journey</h1>
              <Rocket size={28} color="white" />
            </div>
            <p style={{ color: 'rgba(255,255,255,0.85)', fontSize: '1rem', maxWidth: 500, margin: '0 auto' }}>
              From drowning in spreadsheets to building the system of record for configuration decisions
            </p>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            style={{
              position: 'absolute', top: '1rem', right: '1rem',
              padding: '0.5rem 1rem', background: 'rgba(255,255,255,0.2)',
              border: '1px solid rgba(255,255,255,0.3)', color: 'white',
              borderRadius: 6, fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
            }}
          >
            Skip to Platform →
          </button>
        </div>

        {/* Main Content */}
        <div style={{
          background: colors.card,
          border: `3px solid ${colors.primary}`,
          borderTop: 'none',
          borderRadius: '0 0 16px 16px',
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

            {/* Chapter 1: The Problem */}
            <StoryBlock chapter={1} title="The Tribal Knowledge Problem">
              Enterprise SaaS decisions live in Slack threads, email chains, and people's heads. 
              "Why is this configured this way?" "Who approved that exception?" "Didn't we solve this before?" 
              Nobody knows. Every audit, every new team member, every system upgrade — we start from scratch.
            </StoryBlock>

            {/* Problem Illustration */}
            <div style={{ display: 'flex', justifyContent: 'center', margin: '2rem 0' }}>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '1rem',
                maxWidth: 500,
              }}>
                {[
                  { icon: '', label: 'Slack Threads', sub: 'Decisions buried' },
                  { icon: '', label: "People's Heads", sub: 'Knowledge walks out' },
                  { icon: '', label: 'Spreadsheets', sub: 'Version chaos' },
                ].map((item, i) => (
                  <div key={i} style={{
                    padding: '1rem',
                    background: colors.bg,
                    borderRadius: 10,
                    textAlign: 'center',
                    border: `1px dashed ${colors.border}`,
                  }}>
                    <div style={{ fontSize: '1.75rem', marginBottom: '0.5rem' }}>{item.icon}</div>
                    <div style={{ fontWeight: 600, fontSize: '0.8rem', color: colors.text }}>{item.label}</div>
                    <div style={{ fontSize: '0.7rem', color: colors.textMuted }}>{item.sub}</div>
                  </div>
                ))}
              </div>
            </div>

            <ArrowDown />

            {/* Chapter 2: The Insight */}
            <StoryBlock chapter={2} title="The Missing Layer" highlight={colors.accent}>
              Systems of record exist for customers (CRM), employees (HCM), and operations (ERP). 
              But there's no system of record for the <strong>decisions</strong> that connect them. 
              The reasoning that makes data actionable? That's the missing layer.
            </StoryBlock>

            {/* Insight callout */}
            <div style={{
              margin: '2rem auto',
              maxWidth: 550,
              padding: '1.25rem',
              background: `linear-gradient(135deg, ${colors.accentLight} 0%, ${colors.purpleLight} 100%)`,
              border: `2px solid ${colors.accent}`,
              borderRadius: 12,
              textAlign: 'center',
            }}>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: colors.accent, marginBottom: '0.5rem' }}>
                The Context Graph
              </div>
              <p style={{ fontSize: '0.85rem', color: colors.text, margin: 0, lineHeight: 1.6 }}>
                A living record of decision traces — the exceptions, approvals, precedents, and reasoning 
                that currently exist nowhere. Tribal knowledge transformed into institutional memory.
              </p>
            </div>

            <SectionDivider label="The Architecture" color={colors.accent} />

            {/* Chapter 3: Five Truths */}
            <StoryBlock chapter={3} title="Five Truths Intelligence">
              Every analysis requires context from multiple sources. We built an engine that synthesizes 
              five canonical truths — not just data, but the full picture needed to make decisions.
            </StoryBlock>

            {/* Five Truths Visual */}
            <div style={{ margin: '2rem 0' }}>
              {/* Customer Context Row */}
              <div style={{ 
                fontSize: '0.65rem', fontWeight: 700, color: colors.textMuted, 
                textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.75rem',
                textAlign: 'center'
              }}>
                Customer Context
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                {[
                  { icon: <Database size={18} />, label: 'Reality', sub: 'What EXISTS', color: colors.primary },
                  { icon: <FileText size={18} />, label: 'Intent', sub: 'What They WANT', color: colors.electricBlue },
                  { icon: <Settings size={18} />, label: 'Configuration', sub: "How It's SET UP", color: colors.warning },
                ].map((truth, i) => (
                  <div key={i} style={{
                    width: 130, padding: '1rem', background: colors.card,
                    border: `2px solid ${truth.color}`, borderRadius: 10,
                    textAlign: 'center',
                  }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: 8, margin: '0 auto 0.5rem',
                      background: `${truth.color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: truth.color,
                    }}>{truth.icon}</div>
                    <div style={{ fontWeight: 700, fontSize: '0.85rem', color: colors.text }}>{truth.label}</div>
                    <div style={{ fontSize: '0.65rem', color: truth.color, fontWeight: 600 }}>{truth.sub}</div>
                  </div>
                ))}
              </div>

              {/* Reference Library Row */}
              <div style={{ 
                fontSize: '0.65rem', fontWeight: 700, color: colors.textMuted, 
                textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.75rem',
                textAlign: 'center'
              }}>
                Reference Library (Global)
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem' }}>
                {[
                  { icon: <BookOpen size={18} />, label: 'Reference', sub: 'HOW TO Configure', color: colors.purple },
                  { icon: <Scale size={18} />, label: 'Regulatory', sub: "What's REQUIRED", color: colors.scarlet },
                  { icon: <Shield size={18} />, label: 'Compliance', sub: 'What Must Be PROVEN', color: colors.accent },
                ].map((truth, i) => (
                  <div key={i} style={{
                    width: 130, padding: '1rem', background: colors.card,
                    border: `2px solid ${truth.color}`, borderRadius: 10,
                    textAlign: 'center',
                  }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: 8, margin: '0 auto 0.5rem',
                      background: `${truth.color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: truth.color,
                    }}>{truth.icon}</div>
                    <div style={{ fontWeight: 700, fontSize: '0.85rem', color: colors.text }}>{truth.label}</div>
                    <div style={{ fontSize: '0.65rem', color: truth.color, fontWeight: 600 }}>{truth.sub}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Connecting lines visualization */}
            <div style={{ display: 'flex', justifyContent: 'center', margin: '1.5rem 0' }}>
              <svg width="400" height="60" viewBox="0 0 400 60">
                {/* Lines from all truths converging to center */}
                <path d="M 70 5 Q 70 30 200 50" stroke={colors.primary} strokeWidth="2" fill="none" strokeDasharray="4,4"/>
                <path d="M 200 5 L 200 50" stroke={colors.electricBlue} strokeWidth="2" fill="none" strokeDasharray="4,4"/>
                <path d="M 330 5 Q 330 30 200 50" stroke={colors.warning} strokeWidth="2" fill="none" strokeDasharray="4,4"/>
                
                {/* Center node */}
                <circle cx="200" cy="50" r="8" fill={colors.primary} />
                <text x="200" y="54" textAnchor="middle" fill="white" fontSize="8" fontWeight="bold">AI</text>
              </svg>
            </div>

            <ArrowDown />

            {/* Chapter 4: The Flow */}
            <StoryBlock chapter={4} title="How It Works">
              Upload any document. We classify it, extract structure, route it to the right truth store, 
              and make it queryable. Ask questions in plain English — get answers with citations.
            </StoryBlock>

            {/* Flow path */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', position: 'relative', padding: '2rem 1rem', marginTop: '1rem' }}>
              {/* Connecting line */}
              <div style={{
                position: 'absolute', top: 42, left: 70, right: 70, height: 4,
                background: `linear-gradient(90deg, ${colors.primary}, ${colors.accent}, ${colors.purple})`,
                borderRadius: 2,
              }} />
              
              {[
                { icon: '', label: 'Upload', time: 'Any file', color: colors.primary },
                { icon: '', label: 'Classify', time: 'Auto-detect', color: colors.electricBlue },
                { icon: '', label: 'Extract', time: '90 seconds', color: colors.warning },
                { icon: '', label: 'Query', time: 'Plain English', color: colors.purple },
                { icon: '', label: 'Cite', time: 'With sources', color: colors.accent },
              ].map((step, i) => (
                <div key={i} style={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
                  <div style={{
                    width: 60, height: 60, borderRadius: '50%', background: colors.card,
                    border: `3px solid ${step.color}`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    margin: '0 auto 0.5rem', fontSize: '1.5rem',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  }}>{step.icon}</div>
                  <div style={{ fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: '0.7rem', color: colors.text, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{step.label}</div>
                  <div style={{ fontSize: '0.65rem', color: step.color, fontWeight: 600, marginTop: '0.15rem' }}>{step.time}</div>
                </div>
              ))}
            </div>

            <SectionDivider label="The Difference" color={colors.purple} />

            {/* Chapter 5: Not Just Implementation */}
            <StoryBlock chapter={5} title="Beyond Implementation" highlight={colors.purple}>
              Implementation is the first deposit into your context graph. But the real value compounds over time.
              Year 2: regulations change — which configs are affected? Year 3: audit — show the decision trail.
              Year 5: new consultant — instant institutional memory.
            </StoryBlock>

            {/* Lifecycle visual */}
            <div style={{
              margin: '2rem auto',
              maxWidth: 600,
              padding: '1.5rem',
              background: `linear-gradient(135deg, ${colors.purpleLight} 0%, ${colors.primaryLight} 100%)`,
              borderRadius: 12,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
                {[
                  { time: 'Day 1', label: 'Initial Setup', desc: 'Decisions captured' },
                  { time: 'Year 2', label: 'Regulation Change', desc: 'Impact traced' },
                  { time: 'Year 3', label: 'Audit', desc: 'Evidence ready' },
                  { time: 'Year 5+', label: 'Team Turnover', desc: 'Knowledge retained' },
                ].map((phase, i) => (
                  <div key={i} style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.7rem', color: colors.purple, fontWeight: 700, marginBottom: '0.25rem' }}>{phase.time}</div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: colors.text }}>{phase.label}</div>
                    <div style={{ fontSize: '0.7rem', color: colors.textMuted }}>{phase.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            <SectionDivider label="The Result" color={colors.primary} />

            {/* Chapter 6: The Value */}
            <StoryBlock chapter={6} title="The Transformation">
              What used to take weeks now takes minutes. What used to walk out the door stays in the system.
              Every decision, every exception, every "we did it this way because..." becomes searchable precedent.
            </StoryBlock>

            {/* Results grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', margin: '2rem 0' }}>
              {[
                { value: '80%', label: 'Faster Analysis', icon: '' },
                { value: '5', label: 'Truth Sources', icon: '' },
                { value: '∞', label: 'Decision Memory', icon: '' },
                { value: 'Zero', label: 'Lost Context', icon: '' },
              ].map((result, i) => (
                <div key={i} style={{ background: colors.bg, borderRadius: 10, padding: '1.25rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>{result.icon}</div>
                  <div style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.75rem', fontWeight: 800, color: colors.primary }}>{result.value}</div>
                  <div style={{ fontSize: '0.8rem', color: colors.textMuted, marginTop: '0.25rem' }}>{result.label}</div>
                </div>
              ))}
            </div>

            {/* Final illustration */}
            <div style={{ display: 'flex', justifyContent: 'center', margin: '2rem 0' }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '2rem',
                padding: '1.5rem 2rem',
                background: `linear-gradient(135deg, ${colors.primaryLight} 0%, ${colors.accentLight} 100%)`,
                borderRadius: 16,
                border: `2px solid ${colors.primary}`,
              }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '0.25rem' }}></div>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Scattered Data</div>
                </div>
                <ArrowRight size={24} color={colors.primary} />
                <div style={{
                  padding: '1rem 1.5rem',
                  background: colors.card,
                  borderRadius: 10,
                  border: `3px solid ${colors.primary}`,
                  textAlign: 'center',
                }}>
                  <div style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.25rem', fontWeight: 800, color: colors.primary }}>XLR8</div>
                  <div style={{ fontSize: '0.7rem', color: colors.textMuted }}>Context Graph</div>
                </div>
                <ArrowRight size={24} color={colors.primary} />
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '0.25rem' }}></div>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Decisions + Proof</div>
                </div>
              </div>
            </div>

            {/* CTA */}
            <div style={{
              textAlign: 'center', marginTop: '2.5rem', padding: '2.5rem',
              background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryDark} 100%)`,
              borderRadius: 16,
              color: 'white',
            }}>
              <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                Ready to Build Your Context Graph?
              </h3>
              <p style={{ opacity: 0.9, fontSize: '1rem', marginBottom: '1.5rem', maxWidth: 450, margin: '0 auto 1.5rem' }}>
                This isn't a slideshow. This is the platform. Let's go.
              </p>
              <button
                onClick={() => navigate('/dashboard')}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                  padding: '1rem 2rem', background: 'white', color: colors.primary,
                  border: 'none', borderRadius: 10, fontFamily: "'Sora', sans-serif",
                  fontSize: '1rem', fontWeight: 700, cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                }}
              >
                Enter XLR8
                <Sparkles size={18} />
              </button>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
