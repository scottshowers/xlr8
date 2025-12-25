/**
 * Landing.jsx - XLR8 Platform Landing Page
 * 
 * UPDATED: December 25, 2025
 * - Five Truths Architecture (upgraded from Three)
 * - Context Graph positioning
 * - Lifecycle framing (not just implementation)
 * - Investor-ready messaging
 */

import { Link } from 'react-router-dom'
import { 
  Database, 
  Cpu,
  Zap,
  MessageSquare,
  FileText,
  BookOpen,
  BarChart3,
  ArrowRight,
  Rocket,
  Target,
  Layers,
  Search,
  GitBranch,
  Shield,
  Clock,
  CheckCircle,
  Sparkles,
  Brain,
  Upload,
  Table2,
  Scale,
  FileCheck,
  Settings,
  Network
} from 'lucide-react'

// Mission Control Color Palette
const COLORS = {
  primary: '#83b16d',
  primaryDark: '#6b9b5a',
  accent: '#285390',
  electricBlue: '#4a7a9a',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  silver: '#a2a1a0',
  white: '#f6f5fa',
  background: '#f0f2f5',
  text: '#1a2332',
  textMuted: '#64748b',
  warning: '#d97706',
  purple: '#5f4282',
  scarlet: '#993c44',
}

// Speed Lines Animation
const SpeedLinesStyles = () => (
  <style>{`
    @keyframes speedLine {
      0% { opacity: 0; transform: translateX(-30px); }
      50% { opacity: 1; }
      100% { opacity: 0; transform: translateX(60px); }
    }
    .speed-line {
      height: 6px;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.7), transparent);
      animation: speedLine 1.8s ease-out infinite;
      border-radius: 3px;
    }
    .speed-line:nth-child(1) { animation-delay: 0s; }
    .speed-line:nth-child(2) { animation-delay: 0.25s; }
    .speed-line:nth-child(3) { animation-delay: 0.5s; }
    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.05); opacity: 0.9; }
    }
    .pulse-badge {
      animation: pulse 2s ease-in-out infinite;
    }
  `}</style>
)

const SpeedLines = () => (
  <div style={{
    position: 'absolute',
    left: '-50px',
    top: '50%',
    transform: 'translateY(-50%)',
    display: 'flex',
    flexDirection: 'column',
    gap: '18px',
    zIndex: 0
  }}>
    <div className="speed-line" style={{ width: '55px' }} />
    <div className="speed-line" style={{ width: '80px' }} />
    <div className="speed-line" style={{ width: '45px' }} />
  </div>
)

// H Logo SVG
const HLogoWhite = ({ size = 90 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 570" style={{ width: size, height: size, position: 'relative', zIndex: 1 }}>
    <path fill="#c5c4cc" d="M495.76,506.16v-31.35l-36.53-35.01V169.93c0-15.8,.94-16.74,16.74-16.74h19.79v-31.36l-45.66-45.66H76.72v31.36l36.53,36.53V412.4c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35l45.66,45.66H495.76Zm-197.11-93.76c0,15.8-.94,16.74-16.74,16.74h-8.07v-103.81h24.81v87.07Zm-24.81-242.48c0-15.8,.94-16.74,16.74-16.74h8.07v95.13h-24.81v-78.39Z"/>
    <g fill="#dedde6">
      <rect x="138.52" y="354.41" width="64.39" height="11.87"/>
      <rect x="138.52" y="331.12" width="64.39" height="11.87"/>
      <rect x="138.52" y="308.29" width="64.39" height="11.87"/>
      <rect x="138.52" y="285.46" width="64.39" height="11.87"/>
      <path d="M138.06,113.31h65.76c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
      <path d="M323.46,423.36c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.75Z"/>
      <rect x="138.52" y="377.24" width="64.39" height="11.87"/>
      <rect x="138.52" y="400.07" width="64.39" height="11.87"/>
      <rect x="138.52" y="124.26" width="64.39" height="11.87"/>
      <rect x="138.52" y="170.38" width="64.39" height="11.87"/>
      <rect x="323.91" y="147.1" width="64.39" height="11.87"/>
      <rect x="138.52" y="262.17" width="64.39" height="11.87"/>
      <path d="M138.06,423.36c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.76Z"/>
      <rect x="138.52" y="147.1" width="64.39" height="11.87"/>
      <rect x="138.52" y="239.34" width="64.39" height="11.87"/>
      <rect x="138.52" y="193.22" width="64.39" height="11.87"/>
      <rect x="138.52" y="216.5" width="64.39" height="11.87"/>
      <rect x="323.91" y="377.24" width="64.39" height="11.87"/>
      <rect x="323.91" y="331.12" width="64.39" height="11.87"/>
      <rect x="323.91" y="354.41" width="64.39" height="11.87"/>
      <rect x="323.91" y="285.46" width="64.39" height="11.87"/>
      <rect x="323.91" y="308.29" width="64.39" height="11.87"/>
      <rect x="323.91" y="400.07" width="64.39" height="11.87"/>
      <path d="M323.46,113.31h65.75c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
      <rect x="323.91" y="170.38" width="64.39" height="11.87"/>
      <rect x="323.91" y="124.26" width="64.39" height="11.87"/>
      <rect x="323.91" y="193.22" width="64.39" height="11.87"/>
      <rect x="323.91" y="216.5" width="64.39" height="11.87"/>
      <rect x="323.91" y="262.17" width="64.39" height="11.87"/>
      <rect x="323.91" y="239.34" width="64.39" height="11.87"/>
    </g>
    <path fill="#f9f8ff" d="M430.31,101.43h13.7v-19.18h-173.52v19.18h11.42c19.18,0,22.83,3.65,22.83,22.83V254.4h-82.65V124.26c0-19.18,3.65-22.83,22.83-22.83h11.42v-19.18H82.81v19.18h13.7c19.18,0,22.83,3.65,22.83,22.83V412.4c0,19.18-3.65,22.83-22.83,22.83h-13.7v19.18h173.52v-19.18h-11.42c-19.18,0-22.83-3.65-22.83-22.83v-138.82h82.65v138.82c0,19.18-3.65,22.83-22.83,22.83h-11.42v19.18h173.52v-19.18h-13.7c-19.18,0-22.83-3.65-22.83-22.83V124.26c0-19.18,3.65-22.83,22.83-22.83Zm-42.01,45.66v11.87h-64.39v-11.87h64.39Zm-64.39-10.96v-11.87h64.39v11.87h-64.39Zm64.39,34.25v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm.91,23.29c.46,4.57,1.37,8.22,2.74,11.87h-71.69c1.37-3.65,2.74-7.31,3.2-11.87h65.75Zm0-310.05h-65.75c-.46-4.57-1.83-8.68-3.2-11.87h71.69c-1.37,3.2-2.28,7.31-2.74,11.87Zm-186.31,33.79v11.87h-64.39v-11.87h64.39Zm-64.39-10.96v-11.87h64.39v11.87h-64.39Zm64.39,34.25v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm.91,23.29c.46,4.57,1.37,8.22,2.74,11.87h-71.69c1.37-3.65,2.74-7.31,3.2-11.87h65.76Zm0-310.05h-65.76c-.46-4.57-1.83-8.68-3.2-11.87h71.69c-1.37,3.2-2.28,7.31-2.74,11.87Z"/>
    <path fill="#dedde6" d="M430.31,107.52h19.79v-31.36h-183.7v31.36h15.5c15.8,0,16.74,.94,16.74,16.74v124.05h-70.47V124.26c0-15.8,.94-16.74,16.74-16.74h15.5v-31.36H76.72v31.36h19.79c15.8,0,16.74,.94,16.74,16.74V412.4c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35h183.7v-31.35h-15.5c-15.8,0-16.74-.94-16.74-16.74v-132.73h70.47v132.73c0,15.8,.94,16.74-16.74,16.74h-15.5v31.35h183.7v-31.35h-19.79c-15.8,0-16.74-.94-16.74-16.74V124.26c0-15.8,.94-16.74,16.74-16.74Zm0,327.71h13.7v19.18h-173.52v-19.18h11.42c19.18,0,22.83-3.65,22.83-22.83v-138.82h-82.65v138.82c0,19.18,3.65,22.83,22.83,22.83h11.42v19.18H82.81v-19.18h13.7c19.18,0,22.83-3.65,22.83-22.83V124.26c0-19.18-3.65-22.83-22.83-22.83h-13.7v-19.18h173.52v19.18h-11.42c-19.18,0-22.83,3.65-22.83,22.83V254.4h82.65V124.26c0-19.18-3.65-22.83-22.83-22.83h-11.42v-19.18h173.52v19.18h-13.7c-19.18,0-22.83,3.65-22.83,22.83V412.4c0,19.18,3.65,22.83,22.83,22.83Z"/>
  </svg>
)

export default function Landing() {
  return (
    <div style={{ minHeight: '100vh', background: COLORS.white }}>
      <SpeedLinesStyles />
      
      {/* HERO */}
      <div style={{
        background: `linear-gradient(135deg, ${COLORS.primary} 0%, ${COLORS.primaryDark} 100%)`,
        color: 'white',
        padding: '2rem 2rem 3rem'
      }}>
        <div style={{ 
          maxWidth: '1200px', 
          margin: '0 auto',
        }}>
          {/* Top Bar - Login only */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            marginBottom: '1rem'
          }}>
            <Link 
              to="/login" 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.625rem 1.5rem',
                background: 'white',
                color: COLORS.primary,
                borderRadius: '8px',
                fontWeight: '600',
                fontSize: '0.9rem',
                textDecoration: 'none',
              }}
            >
              Login
            </Link>
          </div>

          {/* Hero Content - Logo Centered and PROMINENT */}
          <div style={{ textAlign: 'center', maxWidth: '800px', margin: '0 auto' }}>
            {/* Big Beautiful Logo */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              gap: '1.5rem',
              marginBottom: '1.5rem'
            }}>
              <div style={{ position: 'relative' }}>
                <SpeedLines />
                <HLogoWhite size={140} />
              </div>
              <div style={{ textAlign: 'left' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ 
                    fontFamily: "'Ubuntu Mono', monospace",
                    fontSize: '3rem',
                    fontWeight: '700',
                    letterSpacing: '0.08em'
                  }}>
                    XLR8
                  </span>
                  <Rocket style={{ width: 32, height: 32 }} />
                </div>
                <div style={{ 
                  fontSize: '1.1rem', 
                  opacity: 0.9, 
                  fontWeight: '600',
                  letterSpacing: '0.08em',
                  marginTop: '0.25rem',
                  fontStyle: 'italic'
                }}>
                  Context That Compounds
                </div>
              </div>
            </div>
            <div className="pulse-badge" style={{ 
              display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.4rem 1rem', background: 'rgba(255,255,255,0.2)', 
              borderRadius: '20px', fontSize: '0.8rem', fontWeight: '600', marginBottom: '1rem'
            }}>
              <Network size={14} /> The Context Graph for Enterprise SaaS
            </div>
            <h1 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '2.5rem',
              fontWeight: '800',
              lineHeight: 1.2,
              marginBottom: '1rem',
              letterSpacing: '-0.02em'
            }}>
              The System of Record for<br />Configuration Decisions
            </h1>
            <p style={{
              fontSize: '1.1rem',
              opacity: 0.9,
              maxWidth: '600px',
              margin: '0 auto 1.5rem',
              lineHeight: '1.6'
            }}>
              Not just implementation analysis. A living record of every decision, exception, and precedent across the entire SaaS lifecycle.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <Link 
                to="/journey" 
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.875rem 1.75rem',
                  background: 'white',
                  color: COLORS.primary,
                  borderRadius: '8px',
                  fontWeight: '600',
                  fontSize: '0.95rem',
                  textDecoration: 'none',
                }}
              >
                See the Journey
                <ArrowRight size={18} />
              </Link>
              <Link 
                to="/login" 
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.875rem 1.75rem',
                  background: 'transparent',
                  color: 'white',
                  border: '2px solid rgba(255,255,255,0.5)',
                  borderRadius: '8px',
                  fontWeight: '600',
                  fontSize: '0.95rem',
                  textDecoration: 'none',
                }}
              >
                Launch Platform
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2.5rem 2rem' }}>
        
        {/* THE PROBLEM */}
        <section style={{ marginBottom: '3rem' }}>
          <div style={{ 
            background: `linear-gradient(135deg, ${COLORS.text} 0%, #2d3748 100%)`,
            borderRadius: '16px',
            padding: '2rem',
            color: 'white',
          }}>
            <div style={{ 
              display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.35rem 0.75rem', background: 'rgba(255,255,255,0.1)', 
              borderRadius: '20px', fontSize: '0.75rem', fontWeight: '600', marginBottom: '1rem'
            }}>
              The Problem
            </div>
            <h2 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.5rem', fontWeight: '700', margin: '0 0 1rem' }}>
              Enterprise decisions live in Slack threads and people's heads
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
              {[
                { title: 'Lost Tribal Knowledge', desc: '"We always configure it this way for healthcare companies" — never documented, lost when people leave.' },
                { title: 'No Decision Trail', desc: 'Why was this deduction code mapped to that GL? Who approved the exception? Nobody knows.' },
                { title: 'Repeated Mistakes', desc: 'Same configuration issues surface every audit. No system captures what was learned.' },
              ].map((item, i) => (
                <div key={i} style={{ padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: '600', marginBottom: '0.5rem' }}>{item.title}</h3>
                  <p style={{ fontSize: '0.85rem', opacity: 0.8, lineHeight: 1.5, margin: 0 }}>{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FIVE TRUTHS ARCHITECTURE */}
        <section style={{ marginBottom: '3rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <div style={{ 
              display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.35rem 0.75rem', background: `${COLORS.accent}15`, 
              borderRadius: '20px', fontSize: '0.75rem', fontWeight: '600', 
              color: COLORS.accent, marginBottom: '0.75rem'
            }}>
              <GitBranch size={14} /> Core Architecture
            </div>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '1.5rem',
              fontWeight: '700',
              color: COLORS.text,
              margin: 0
            }}>
              Five Truths Intelligence Engine
            </h2>
            <p style={{ fontSize: '0.95rem', color: COLORS.textMuted, marginTop: '0.5rem', maxWidth: '650px', margin: '0.5rem auto 0' }}>
              Every analysis synthesizes five canonical sources — not just data, but the reasoning that makes data actionable
            </p>
          </div>

          {/* Customer Truths */}
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ 
              fontSize: '0.7rem', fontWeight: '700', color: COLORS.textMuted, 
              textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.75rem',
              display: 'flex', alignItems: 'center', gap: '0.5rem'
            }}>
              <span style={{ width: 20, height: 2, background: COLORS.primary }}></span>
              Customer Context
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              {[
                { 
                  icon: <Database size={22} />, 
                  title: 'Reality', 
                  subtitle: 'What EXISTS',
                  storage: 'DuckDB',
                  color: COLORS.primary,
                  desc: 'Actual transactional data — payroll registers, employee rosters, benefits census. The facts.',
                  examples: 'Excel, CSV, exports'
                },
                { 
                  icon: <FileText size={22} />, 
                  title: 'Intent', 
                  subtitle: 'What They WANT',
                  storage: 'ChromaDB',
                  color: COLORS.electricBlue,
                  desc: 'Customer requirements — SOWs, meeting notes, project goals. What success looks like.',
                  examples: 'PDFs, Word docs, specs'
                },
                { 
                  icon: <Settings size={22} />, 
                  title: 'Configuration', 
                  subtitle: 'How It\'s SET UP',
                  storage: 'Both',
                  color: COLORS.warning,
                  desc: 'Customer\'s actual system setup — code tables, mappings, configured values. Current state.',
                  examples: 'Earnings codes, deductions'
                },
              ].map((truth, idx) => (
                <div key={idx} style={{
                  background: 'white',
                  borderRadius: '12px',
                  padding: '1.25rem',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                  border: `1px solid ${COLORS.iceFlow}`,
                  borderLeft: `4px solid ${truth.color}`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                    <div style={{
                      width: '42px', height: '42px', borderRadius: '10px',
                      background: `${truth.color}15`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: truth.color
                    }}>
                      {truth.icon}
                    </div>
                    <div>
                      <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '700', color: COLORS.text }}>{truth.title}</h3>
                      <span style={{ fontSize: '0.75rem', color: truth.color, fontWeight: '600' }}>{truth.subtitle}</span>
                    </div>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: COLORS.textMuted, lineHeight: 1.5, margin: '0 0 0.5rem' }}>{truth.desc}</p>
                  <div style={{ fontSize: '0.7rem', color: COLORS.silver }}>{truth.examples} → {truth.storage}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Reference Library Truths */}
          <div>
            <div style={{ 
              fontSize: '0.7rem', fontWeight: '700', color: COLORS.textMuted, 
              textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.75rem',
              display: 'flex', alignItems: 'center', gap: '0.5rem'
            }}>
              <span style={{ width: 20, height: 2, background: COLORS.purple }}></span>
              Reference Library (Global)
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              {[
                { 
                  icon: <BookOpen size={22} />, 
                  title: 'Reference', 
                  subtitle: 'HOW TO Configure',
                  color: COLORS.purple,
                  desc: 'Vendor documentation — product guides, configuration manuals. How the system works.',
                  examples: 'UKG guides, ADP manuals'
                },
                { 
                  icon: <Scale size={22} />, 
                  title: 'Regulatory', 
                  subtitle: 'What\'s REQUIRED',
                  color: COLORS.scarlet,
                  desc: 'Laws and mandates — IRS publications, state rules, FLSA, ACA. The legal requirements.',
                  examples: 'IRS Pub 15, Secure 2.0'
                },
                { 
                  icon: <Shield size={22} />, 
                  title: 'Compliance', 
                  subtitle: 'What Must Be PROVEN',
                  color: COLORS.accent,
                  desc: 'Audit requirements — SOC 2, internal controls, evidence checklists. What auditors need.',
                  examples: 'Audit guides, SOC 2'
                },
              ].map((truth, idx) => (
                <div key={idx} style={{
                  background: 'white',
                  borderRadius: '12px',
                  padding: '1.25rem',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                  border: `1px solid ${COLORS.iceFlow}`,
                  borderLeft: `4px solid ${truth.color}`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                    <div style={{
                      width: '42px', height: '42px', borderRadius: '10px',
                      background: `${truth.color}15`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: truth.color
                    }}>
                      {truth.icon}
                    </div>
                    <div>
                      <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '700', color: COLORS.text }}>{truth.title}</h3>
                      <span style={{ fontSize: '0.75rem', color: truth.color, fontWeight: '600' }}>{truth.subtitle}</span>
                    </div>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: COLORS.textMuted, lineHeight: 1.5, margin: '0 0 0.5rem' }}>{truth.desc}</p>
                  <div style={{ fontSize: '0.7rem', color: COLORS.silver }}>{truth.examples} → ChromaDB</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CONTEXT GRAPH CALLOUT */}
        <section style={{ marginBottom: '3rem' }}>
          <div style={{ 
            background: `linear-gradient(135deg, ${COLORS.accent} 0%, ${COLORS.purple} 100%)`,
            borderRadius: '16px',
            padding: '2rem',
            color: 'white',
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '2rem',
            alignItems: 'center'
          }}>
            <div>
              <div style={{ 
                display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.35rem 0.75rem', background: 'rgba(255,255,255,0.2)', 
                borderRadius: '20px', fontSize: '0.75rem', fontWeight: '600', marginBottom: '1rem'
              }}>
                <Network size={14} /> Context Graph
              </div>
              <h2 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.35rem', fontWeight: '700', margin: '0 0 0.75rem' }}>
                Decisions Become Searchable Precedent
              </h2>
              <p style={{ fontSize: '0.95rem', opacity: 0.9, lineHeight: 1.6, margin: '0 0 1.25rem' }}>
                Every configuration decision, every exception, every "we did it this way because..." becomes part of a queryable knowledge graph. Tribal knowledge turns into institutional memory.
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {['Decision Traces', 'Exception History', 'Approval Chains', 'Precedent Search'].map((tag, i) => (
                  <span key={i} style={{ 
                    padding: '0.35rem 0.75rem', background: 'rgba(255,255,255,0.2)', 
                    borderRadius: '20px', fontSize: '0.8rem', fontWeight: '500'
                  }}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            <div style={{ 
              background: 'rgba(255,255,255,0.1)', 
              borderRadius: '12px', 
              padding: '1.25rem',
            }}>
              <div style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.75rem' }}>Example: Why is earnings code 401K configured this way?</div>
              {[
                { label: 'Configuration', value: '401K mapped to GL 5200', icon: '⚙️' },
                { label: 'Regulatory', value: 'Secure 2.0 §603 applies', icon: '⚖️' },
                { label: 'Decision', value: 'VP Finance approved 12/14', icon: '✓' },
                { label: 'Precedent', value: 'Same as Acme Corp setup', icon: '🔗' },
              ].map((item, i) => (
                <div key={i} style={{ 
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '0.5rem 0', borderBottom: i < 3 ? '1px solid rgba(255,255,255,0.1)' : 'none'
                }}>
                  <span style={{ fontSize: '0.85rem', opacity: 0.9 }}>{item.icon} {item.label}</span>
                  <span style={{ fontSize: '0.85rem', fontWeight: '600' }}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* PLATFORM CAPABILITIES */}
        <section style={{ marginBottom: '3rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '1.35rem',
              fontWeight: '700',
              color: COLORS.text
            }}>
              Platform Capabilities
            </h2>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '1rem'
          }}>
            {[
              { 
                icon: <Sparkles size={20} />, 
                title: 'Intelligent Extraction', 
                desc: 'Deep extraction from complex PDFs. Parallel processing turns 6 minutes into 90 seconds.',
                color: COLORS.warning
              },
              { 
                icon: <BookOpen size={20} />, 
                title: 'Compliance Playbooks', 
                desc: 'Guided workflows that check configurations against regulatory requirements automatically.',
                color: COLORS.purple
              },
              { 
                icon: <MessageSquare size={20} />, 
                title: 'Intelligent Chat', 
                desc: 'Query across all five truths. Get answers with citations back to canonical sources.',
                color: COLORS.electricBlue
              },
              { 
                icon: <Brain size={20} />, 
                title: 'Hybrid LLM', 
                desc: 'Local models for speed & privacy. Cloud APIs for complex synthesis. Best of both.',
                color: COLORS.primary
              },
              { 
                icon: <Target size={20} />, 
                title: 'Mission Control', 
                desc: 'Real-time platform health, processing pipeline, and decision audit trail.',
                color: COLORS.accent
              },
              { 
                icon: <Layers size={20} />, 
                title: 'Domain Agnostic', 
                desc: 'Works across HCM, payroll, benefits, finance. Standards uploaded, not hardcoded.',
                color: COLORS.silver
              },
            ].map((feature, idx) => (
              <div key={idx} style={{
                background: 'white',
                borderRadius: '10px',
                padding: '1.25rem',
                boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
                display: 'flex',
                gap: '0.75rem'
              }}>
                <div style={{
                  flexShrink: 0,
                  width: '44px',
                  height: '44px',
                  background: `${feature.color}15`,
                  borderRadius: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: feature.color
                }}>
                  {feature.icon}
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: '0.95rem', fontWeight: '600', color: COLORS.text, marginBottom: '0.25rem' }}>
                    {feature.title}
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: COLORS.textMuted, lineHeight: 1.5, margin: 0 }}>
                    {feature.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* QUICK STATS */}
        <section style={{ marginBottom: '3rem' }}>
          <div style={{ 
            background: COLORS.background,
            borderRadius: '12px',
            padding: '1.5rem 2rem',
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '1.5rem',
            textAlign: 'center'
          }}>
            {[
              { value: '5', label: 'Truth Sources', sub: 'Canonical context graph' },
              { value: '90s', label: 'PDF Processing', sub: 'vs 6 min manual' },
              { value: '∞', label: 'Decision Memory', sub: 'Nothing gets lost' },
              { value: '1', label: 'Platform', sub: 'Implementation → Lifecycle' },
            ].map((stat, i) => (
              <div key={i}>
                <div style={{ fontSize: '2rem', fontWeight: '700', color: COLORS.primary, fontFamily: "'Ubuntu Mono', monospace" }}>
                  {stat.value}
                </div>
                <div style={{ fontSize: '0.9rem', fontWeight: '600', color: COLORS.text }}>{stat.label}</div>
                <div style={{ fontSize: '0.75rem', color: COLORS.textMuted }}>{stat.sub}</div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section style={{
          background: `linear-gradient(135deg, ${COLORS.primary} 0%, ${COLORS.primaryDark} 100%)`,
          borderRadius: '16px',
          padding: '2.5rem 2rem',
          textAlign: 'center',
          color: 'white'
        }}>
          <h2 style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: '1.5rem',
            fontWeight: '700',
            marginBottom: '0.5rem'
          }}>
            Ready to build your context graph?
          </h2>
          <p style={{
            fontSize: '1rem',
            opacity: 0.9,
            maxWidth: '550px',
            margin: '0 auto 1.5rem',
            lineHeight: '1.6'
          }}>
            Stop losing decisions to Slack threads and spreadsheets. Start building searchable institutional memory.
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link 
              to="/login" 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.875rem 2rem',
                background: 'white',
                color: COLORS.primary,
                border: 'none',
                borderRadius: '8px',
                fontSize: '1rem',
                fontWeight: '600',
                textDecoration: 'none'
              }}
            >
              Get Started
              <ArrowRight size={18} />
            </Link>
          </div>
        </section>
      </div>

      {/* FOOTER */}
      <footer style={{
        borderTop: `1px solid ${COLORS.iceFlow}`,
        padding: '1.25rem 2rem',
        textAlign: 'center',
        background: 'white'
      }}>
        <p style={{ 
          fontFamily: "'Manrope', sans-serif",
          fontSize: '0.85rem', 
          color: COLORS.textMuted, 
          margin: 0 
        }}>
          © 2025 HCMPACT. XLR8 — Context That Compounds.
        </p>
      </footer>
    </div>
  )
}
