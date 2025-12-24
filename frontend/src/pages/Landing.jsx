/**
 * Landing.jsx - XLR8 Platform Landing Page
 * 
 * UPDATED: December 23, 2025
 * - Mission Control color palette
 * - Showcases Three Truths Architecture
 * - Smart Upload with metadata staging
 * - Domain-agnostic intelligence
 * - Register Extractor
 * - Playbook Framework
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
  Table2
} from 'lucide-react'

// Mission Control Color Palette
const COLORS = {
  primary: '#83b16d',
  primaryDark: '#6b9b5a',
  accent: '#285390',
  electricBlue: '#2766b1',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  silver: '#a2a1a0',
  white: '#f6f5fa',
  background: '#f0f2f5',
  text: '#1a2332',
  textMuted: '#64748b',
  warning: '#d97706',
  purple: '#5f4282',
}

// Speed Lines Animation
const SpeedLinesStyles = () => (
  <style>{`
    @keyframes speedLine {
      0% { opacity: 0; transform: translateX(-20px); }
      50% { opacity: 1; }
      100% { opacity: 0; transform: translateX(40px); }
    }
    .speed-line {
      height: 5px;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent);
      animation: speedLine 1.8s ease-out infinite;
      border-radius: 2px;
    }
    .speed-line:nth-child(1) { width: 40px; animation-delay: 0s; }
    .speed-line:nth-child(2) { width: 60px; animation-delay: 0.25s; }
    .speed-line:nth-child(3) { width: 32px; animation-delay: 0.5s; }
  `}</style>
)

const SpeedLines = () => (
  <div style={{
    position: 'absolute',
    left: '-35px',
    top: '50%',
    transform: 'translateY(-50%)',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    zIndex: 0
  }}>
    <div className="speed-line" />
    <div className="speed-line" />
    <div className="speed-line" />
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
    <path fill="#f9f8ff" d="M430.31,101.43h13.7v-19.18h-173.52v19.18h11.42c19.18,0,22.83,3.65,22.83,22.83V254.4h-82.65V124.26c0-19.18,3.65-22.83,22.83-22.83h11.42v-19.18H82.81v19.18h13.7c19.18,0,22.83,3.65,22.83,22.83V412.4c0,19.18-3.65,22.83-22.83,22.83h-13.7v19.18h173.52v-19.18h-11.42c-19.18,0-22.83-3.65-22.83-22.83v-138.82h82.65v138.82c0,19.18-3.65,22.83-22.83,22.83h-11.42v19.18h173.52v-19.18h-13.7c-19.18,0-22.83-3.65-22.83-22.83V124.26c0-19.18,3.65-22.83,22.83-22.83Z"/>
    <path fill="#dedde6" d="M430.31,107.52h19.79v-31.36h-183.7v31.36h15.5c15.8,0,16.74,.94,16.74,16.74v124.05h-70.47V124.26c0-15.8,.94-16.74,16.74-16.74h15.5v-31.36H76.72v31.36h19.79c15.8,0,16.74,.94,16.74,16.74V412.4c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35h183.7v-31.35h-15.5c-15.8,0-16.74-.94-16.74-16.74v-132.73h70.47v132.73c0,15.8,.94,16.74-16.74,16.74h-15.5v31.35h183.7v-31.35h-19.79c-15.8,0-16.74-.94-16.74-16.74V124.26c0-15.8,.94-16.74,16.74-16.74Z"/>
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
        padding: '1.5rem 2rem'
      }}>
        <div style={{ 
          maxWidth: '1200px', 
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1.5rem'
        }}>
          {/* Left - Logo + Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ position: 'relative' }}>
              <SpeedLines />
              <HLogoWhite size={90} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ 
                fontFamily: "'Ubuntu Mono', monospace",
                fontSize: '1.75rem',
                fontWeight: '700',
                letterSpacing: '0.05em'
              }}>
                XLR8
              </span>
              <Rocket style={{ width: 22, height: 22 }} />
              <span style={{ 
                fontFamily: "'Sora', sans-serif",
                fontSize: '1.25rem',
                fontWeight: '500',
                opacity: 0.9
              }}>
                Analysis Platform
              </span>
            </div>
          </div>
          
          {/* Right - CTAs */}
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <Link 
              to="/login" 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.625rem 1.25rem',
                background: 'white',
                color: COLORS.primary,
                borderRadius: '8px',
                fontWeight: '600',
                fontSize: '0.9rem',
                textDecoration: 'none',
                transition: 'transform 0.15s ease',
              }}
            >
              Login
            </Link>
            <div style={{ width: 1, height: 24, background: 'rgba(255,255,255,0.3)' }} />
            <Link 
              to="/dashboard" 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.625rem 1.25rem',
                background: 'rgba(255,255,255,0.15)',
                color: 'white',
                border: '1px solid rgba(255,255,255,0.3)',
                borderRadius: '8px',
                fontWeight: '600',
                fontSize: '0.9rem',
                textDecoration: 'none',
              }}
            >
              <Target size={16} /> Mission Control
            </Link>
            <Link 
              to="/workspace" 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.625rem 1.25rem',
                background: 'rgba(255,255,255,0.15)',
                color: 'white',
                border: '1px solid rgba(255,255,255,0.3)',
                borderRadius: '8px',
                fontWeight: '600',
                fontSize: '0.9rem',
                textDecoration: 'none',
              }}
            >
              <MessageSquare size={16} /> AI Assist
            </Link>
          </div>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
        
        {/* THREE TRUTHS ARCHITECTURE */}
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
              Three Truths Intelligence Engine
            </h2>
            <p style={{ fontSize: '0.95rem', color: COLORS.textMuted, marginTop: '0.5rem', maxWidth: '600px', margin: '0.5rem auto 0' }}>
              Every analysis combines three sources of truth for complete understanding
            </p>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '1rem'
          }}>
            {[
              { 
                icon: <Database size={24} />, 
                title: 'Reality', 
                subtitle: 'What IS',
                storage: 'DuckDB',
                color: COLORS.primary,
                desc: 'Actual transactional data — payroll registers, employee rosters, benefits census. Queryable with SQL.',
                examples: 'Excel, CSV, data exports'
              },
              { 
                icon: <FileText size={24} />, 
                title: 'Intent', 
                subtitle: 'What SHOULD BE',
                storage: 'ChromaDB',
                color: COLORS.electricBlue,
                desc: 'Customer documents describing requirements — implementation guides, config specs, SOWs. Semantic search.',
                examples: 'PDFs, Word docs, specs'
              },
              { 
                icon: <BookOpen size={24} />, 
                title: 'Reference', 
                subtitle: 'Best Practice',
                storage: 'Reference Library',
                color: COLORS.purple,
                desc: 'Industry standards, compliance checklists, vendor documentation. Shared knowledge base.',
                examples: 'Compliance docs, manuals'
              },
            ].map((truth, idx) => (
              <div key={idx} style={{
                background: 'white',
                borderRadius: '12px',
                padding: '1.5rem',
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                border: `1px solid ${COLORS.iceFlow}`,
                borderTop: `3px solid ${truth.color}`,
              }}>
                <div style={{ 
                  display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem'
                }}>
                  <div style={{
                    width: '48px', height: '48px', borderRadius: '12px',
                    background: `${truth.color}15`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: truth.color
                  }}>
                    {truth.icon}
                  </div>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '700', color: COLORS.text }}>
                      {truth.title}
                    </h3>
                    <span style={{ fontSize: '0.8rem', color: truth.color, fontWeight: '600' }}>
                      {truth.subtitle}
                    </span>
                  </div>
                </div>
                <p style={{ fontSize: '0.85rem', color: COLORS.textMuted, lineHeight: 1.6, margin: '0 0 0.75rem' }}>
                  {truth.desc}
                </p>
                <div style={{ 
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '0.5rem 0.75rem', background: COLORS.background, borderRadius: '6px',
                  fontSize: '0.75rem'
                }}>
                  <span style={{ color: COLORS.textMuted }}>{truth.examples}</span>
                  <span style={{ fontWeight: '600', color: truth.color }}>→ {truth.storage}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* SMART UPLOAD */}
        <section style={{ marginBottom: '3rem' }}>
          <div style={{ 
            background: `linear-gradient(135deg, ${COLORS.accent} 0%, ${COLORS.electricBlue} 100%)`,
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
                <Upload size={14} /> Smart Upload
              </div>
              <h2 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1.35rem', fontWeight: '700', margin: '0 0 0.75rem' }}>
                Intelligent File Classification
              </h2>
              <p style={{ fontSize: '0.95rem', opacity: 0.9, lineHeight: 1.6, margin: '0 0 1.25rem' }}>
                Drop any file and XLR8 auto-detects its type, domain, and optimal storage destination. 
                Review classifications before upload with detailed tooltips explaining each option.
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {['Truth Type', 'Functional Area', 'Content Domains'].map((tag, i) => (
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
              backdropFilter: 'blur(10px)'
            }}>
              <div style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.75rem' }}>Auto-detected classifications:</div>
              {[
                { label: 'Truth Type', value: '📊 Reality → DuckDB', confidence: 'high' },
                { label: 'Area', value: 'Payroll', confidence: 'high' },
                { label: 'Domains', value: 'payroll, tax', confidence: 'medium' },
              ].map((item, i) => (
                <div key={i} style={{ 
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '0.5rem 0', borderBottom: i < 2 ? '1px solid rgba(255,255,255,0.1)' : 'none'
                }}>
                  <span style={{ fontSize: '0.85rem', opacity: 0.9 }}>{item.label}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: '600' }}>{item.value}</span>
                    <span style={{ 
                      padding: '0.15rem 0.5rem', borderRadius: '4px', fontSize: '0.7rem', fontWeight: '600',
                      background: item.confidence === 'high' ? 'rgba(131,177,109,0.3)' : 'rgba(217,119,6,0.3)'
                    }}>
                      {item.confidence}
                    </span>
                  </div>
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
                title: 'Register Extractor', 
                desc: 'Deep extraction from complex PDFs. 4-worker parallel processing: 6 min → 90 seconds.',
                color: COLORS.warning
              },
              { 
                icon: <BookOpen size={20} />, 
                title: 'Playbook Framework', 
                desc: 'Guided compliance workflows with reusable analysis templates. Standards-driven, not hardcoded.',
                color: COLORS.purple
              },
              { 
                icon: <MessageSquare size={20} />, 
                title: 'Intelligent Chat', 
                desc: 'Query across all data sources. Auto-generates SQL, searches documents, applies domain expertise.',
                color: COLORS.electricBlue
              },
              { 
                icon: <Brain size={20} />, 
                title: 'Hybrid LLM', 
                desc: 'Local models (DeepSeek, Mistral) for speed & privacy. Claude API for complex edge cases.',
                color: COLORS.primary
              },
              { 
                icon: <Target size={20} />, 
                title: 'Mission Control', 
                desc: 'Real-time platform health, processing pipeline, performance metrics. Live system topology.',
                color: COLORS.accent
              },
              { 
                icon: <Layers size={20} />, 
                title: 'Domain Agnostic', 
                desc: 'Works across any industry. Standards uploaded, not hardcoded. Domain knowledge via Learning layer.',
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
              { value: '90s', label: 'PDF Processing', sub: 'vs 6 min manual' },
              { value: '3', label: 'Truth Sources', sub: 'Reality + Intent + Reference' },
              { value: '7', label: 'Content Domains', sub: 'Auto-detected' },
              { value: '4', label: 'Truth Types', sub: 'Smart routing' },
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
            Ready to accelerate your analysis?
          </h2>
          <p style={{
            fontSize: '1rem',
            opacity: 0.9,
            maxWidth: '500px',
            margin: '0 auto 1.5rem',
            lineHeight: '1.6'
          }}>
            Transform weeks of manual document analysis into minutes of intelligent insights.
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link 
              to="/dashboard" 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.875rem 1.75rem',
                background: 'white',
                color: COLORS.primary,
                border: 'none',
                borderRadius: '8px',
                fontSize: '1rem',
                fontWeight: '600',
                textDecoration: 'none'
              }}
            >
              Launch Mission Control
              <ArrowRight size={18} />
            </Link>
            <Link 
              to="/data" 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.875rem 1.75rem',
                background: 'rgba(255,255,255,0.15)',
                color: 'white',
                border: '1px solid rgba(255,255,255,0.3)',
                borderRadius: '8px',
                fontSize: '1rem',
                fontWeight: '600',
                textDecoration: 'none'
              }}
            >
              <Upload size={18} />
              Upload Data
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
          © 2025 HCMPACT. Built with intelligence, speed, and precision.
        </p>
      </footer>
    </div>
  )
}
