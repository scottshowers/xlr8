import { Link } from 'react-router-dom'
import { 
  Shield, 
  Lock, 
  Database, 
  Server,
  Cpu,
  Table,
  FileSearch,
  Workflow,
  Zap,
  Cloud,
  MessageSquare,
  FileText,
  BookOpen,
  BarChart3,
  Users,
  Eye,
  ArrowRight
} from 'lucide-react'

// Speed Lines Animation Styles (injected once)
const SpeedLinesStyles = () => (
  <style>{`
    @keyframes speedLine {
      0% { opacity: 0; transform: translateX(-20px); }
      50% { opacity: 1; }
      100% { opacity: 0; transform: translateX(40px); }
    }
    .speed-line {
      height: 3px;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.9), transparent);
      animation: speedLine 1.5s ease-out infinite;
      border-radius: 2px;
    }
    .speed-line:nth-child(1) { width: 30px; animation-delay: 0s; }
    .speed-line:nth-child(2) { width: 45px; animation-delay: 0.2s; }
    .speed-line:nth-child(3) { width: 25px; animation-delay: 0.4s; }
  `}</style>
)

// Speed Lines Component
const SpeedLines = () => (
  <div style={{
    position: 'absolute',
    left: '-25px',
    top: '50%',
    transform: 'translateY(-50%)',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  }}>
    <div className="speed-line" />
    <div className="speed-line" />
    <div className="speed-line" />
  </div>
)

// White H Logo SVG Component (for hero on green background)
const HLogoWhite = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 570" style={{ width: '100%', height: '100%' }}>
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
    <path fill="#dedde6" d="M430.31,107.52h19.79v-31.36h-183.7v31.36h15.5c15.8,0,16.74,.94,16.74,16.74v124.05h-70.47V124.26c0-15.8,.94-16.74,16.74-16.74h15.5v-31.36H76.72v31.36h19.79c15.8,0,16.74,.94,16.74,16.74V412.4c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35h183.7v-31.35h-15.5c-15.8,0-16.74-.94-16.74-16.74v-132.73h70.47v132.73c0,15.8-.94,16.74-16.74,16.74h-15.5v31.35h183.7v-31.35h-19.79c-15.8,0-16.74-.94-16.74-16.74V124.26c0-15.8,.94-16.74,16.74-16.74Z"/>
  </svg>
)

// Brand Colors
const COLORS = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  iceFlow: '#c9d3d4',
  clearwater: '#b2d6de',
  white: '#f6f5fa',
  silver: '#a2a1a0',
  aquamarine: '#a1c3d4',
  text: '#2a3441',
  textLight: '#5f6c7b',
}

export default function Landing() {
  return (
    <div style={{ minHeight: '100vh', background: COLORS.white }}>
      <SpeedLinesStyles />
      
      {/* HERO - Compact, clean */}
      <div style={{
        background: COLORS.grassGreen,
        color: 'white',
        padding: '2.5rem 2rem',
        textAlign: 'center'
      }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          {/* Logo + Name with Speed Lines */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            gap: '1rem',
            marginBottom: '0.5rem'
          }}>
            <div style={{ 
              position: 'relative',
              width: '55px', 
              height: '55px' 
            }}>
              <SpeedLines />
              <HLogoWhite />
            </div>
            <h1 style={{ 
              fontFamily: "'Sora', sans-serif",
              fontSize: '2.5rem',
              fontWeight: '700',
              margin: 0
            }}>
              XLR8
            </h1>
          </div>
          
          {/* Tagline - simple */}
          <p style={{
            fontFamily: "'Manrope', sans-serif",
            fontSize: '1rem',
            opacity: 0.9,
            margin: '0.5rem 0 1.5rem'
          }}>
            Implementation Analysis Platform
          </p>
          
          {/* CTA Buttons - SOLID colors */}
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link 
              to="/workspace" 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.5rem',
                background: 'white',
                color: COLORS.grassGreen,
                border: 'none',
                borderRadius: '8px',
                fontSize: '1rem',
                fontWeight: '600',
                textDecoration: 'none',
                cursor: 'pointer'
              }}
            >
              Get Started
              <ArrowRight style={{ width: 18, height: 18 }} />
            </Link>
            <Link 
              to="/playbooks" 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.5rem',
                background: 'transparent',
                color: 'white',
                border: '2px solid rgba(255,255,255,0.5)',
                borderRadius: '8px',
                fontSize: '1rem',
                fontWeight: '600',
                textDecoration: 'none',
                cursor: 'pointer'
              }}
            >
              View Playbooks
            </Link>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '3rem 2rem' }}>
        
        {/* Value Props - 3 columns */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem'
        }}>
          {[
            { icon: '📥', title: 'Ingest', desc: '100+ documents. PDFs, Excel, Word. All queryable.' },
            { icon: '🧠', title: 'Analyze', desc: 'AI cross-references all sources. Finds conflicts.' },
            { icon: '📊', title: 'Deliver', desc: 'Generate workbooks, templates, load files.' },
          ].map((item, i) => (
            <div key={i} style={{
              background: 'white',
              borderRadius: '12px',
              padding: '1.5rem',
              boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>{item.icon}</div>
              <h3 style={{ 
                fontFamily: "'Sora', sans-serif",
                margin: '0 0 0.5rem', 
                color: COLORS.text, 
                fontSize: '1.1rem' 
              }}>{item.title}</h3>
              <p style={{ 
                fontFamily: "'Manrope', sans-serif",
                margin: 0, 
                color: COLORS.textLight, 
                fontSize: '0.9rem', 
                lineHeight: 1.5 
              }}>{item.desc}</p>
            </div>
          ))}
        </div>

        {/* Security callout */}
        <div style={{
          background: COLORS.iceFlow,
          borderRadius: '12px',
          padding: '1.25rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          marginBottom: '3rem'
        }}>
          <span style={{ fontSize: '1.5rem' }}>🔒</span>
          <div>
            <strong style={{ color: COLORS.text }}>PII stays local.</strong>
            <span style={{ color: COLORS.textLight, marginLeft: '0.5rem' }}>
              Employee data encrypted, processed by local LLM. Never sent to external APIs.
            </span>
          </div>
        </div>

        {/* Security Section */}
        <section style={{ marginBottom: '3rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '1.5rem',
              fontWeight: '700',
              color: COLORS.text,
              marginBottom: '0.5rem'
            }}>
              Security-First Architecture
            </h2>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '1rem'
          }}>
            {[
              { icon: <Lock style={{ width: 20, height: 20 }} />, title: 'PII Detection & Encryption', desc: 'SSN, DOB, salary auto-detected. AES-256 encrypted at rest.' },
              { icon: <Eye style={{ width: 20, height: 20 }} />, title: 'Local Processing', desc: 'Sensitive data stays local. Config data uses Claude.' },
              { icon: <Database style={{ width: 20, height: 20 }} />, title: 'Project Isolation', desc: 'Complete data separation per customer.' },
              { icon: <Server style={{ width: 20, height: 20 }} />, title: 'Self-Hosted Option', desc: 'Deploy within your infrastructure.' }
            ].map((item, idx) => (
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
                  width: '40px',
                  height: '40px',
                  background: COLORS.iceFlow,
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: COLORS.grassGreen
                }}>
                  {item.icon}
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: '0.95rem', fontWeight: '600', color: COLORS.text, marginBottom: '0.25rem' }}>
                    {item.title}
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: COLORS.textLight, lineHeight: 1.5, margin: 0 }}>
                    {item.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Tech Stack Section */}
        <section style={{ marginBottom: '3rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '1.5rem',
              fontWeight: '700',
              color: COLORS.text,
              marginBottom: '0.5rem'
            }}>
              Built for Scale & Intelligence
            </h2>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '1rem'
          }}>
            {[
              { icon: <Cpu style={{ width: 20, height: 20 }} />, title: 'Dual-LLM Architecture', desc: 'Claude for config, local LLM for employee data.' },
              { icon: <Table style={{ width: 20, height: 20 }} />, title: 'DuckDB + ChromaDB', desc: 'SQL for structured, vectors for documents.' },
              { icon: <FileSearch style={{ width: 20, height: 20 }} />, title: 'Universal Processing', desc: 'OCR, table extraction, intelligent chunking.' },
              { icon: <Workflow style={{ width: 20, height: 20 }} />, title: 'Playbook Engine', desc: 'Capture patterns as reusable playbooks.' },
              { icon: <Zap style={{ width: 20, height: 20 }} />, title: 'Self-Healing Systems', desc: 'AI-driven detection. No brittle regex.' },
              { icon: <Cloud style={{ width: 20, height: 20 }} />, title: 'API Integration', desc: 'Connect to UKG Pro, WFM, Ready.' }
            ].map((item, idx) => (
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
                  width: '40px',
                  height: '40px',
                  background: COLORS.iceFlow,
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: COLORS.grassGreen
                }}>
                  {item.icon}
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: '0.95rem', fontWeight: '600', color: COLORS.text, marginBottom: '0.25rem' }}>
                    {item.title}
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: COLORS.textLight, lineHeight: 1.5, margin: 0 }}>
                    {item.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Features Section */}
        <section style={{ marginBottom: '3rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '1.5rem',
              fontWeight: '700',
              color: COLORS.text
            }}>
              Platform Capabilities
            </h2>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem'
          }}>
            {[
              { icon: <MessageSquare style={{ width: 18, height: 18 }} />, title: 'Intelligent Workspace', desc: 'Chat across all data' },
              { icon: <FileText style={{ width: 18, height: 18 }} />, title: 'Multi-File Upload', desc: 'Batch processing' },
              { icon: <Table style={{ width: 18, height: 18 }} />, title: 'Vacuum Extractor', desc: 'Tables from PDFs' },
              { icon: <BookOpen style={{ width: 18, height: 18 }} />, title: 'Playbooks', desc: 'Analysis templates' },
              { icon: <BarChart3 style={{ width: 18, height: 18 }} />, title: 'Processing Dashboard', desc: 'Real-time status' },
              { icon: <Users style={{ width: 18, height: 18 }} />, title: 'Project Management', desc: 'Isolated workspaces' }
            ].map((feature, idx) => (
              <div key={idx} style={{
                background: 'white',
                borderRadius: '10px',
                padding: '1rem',
                boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem'
              }}>
                <div style={{
                  flexShrink: 0,
                  width: '36px',
                  height: '36px',
                  background: COLORS.iceFlow,
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: COLORS.grassGreen
                }}>
                  {feature.icon}
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: '0.9rem', fontWeight: '600', color: COLORS.text, marginBottom: '0.1rem' }}>
                    {feature.title}
                  </h3>
                  <p style={{ fontSize: '0.8rem', color: COLORS.textLight, margin: 0 }}>
                    {feature.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA Section */}
        <section style={{
          background: COLORS.iceFlow,
          borderRadius: '16px',
          padding: '3rem 2rem',
          textAlign: 'center'
        }}>
          <h2 style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: '1.75rem',
            fontWeight: '700',
            color: COLORS.text,
            marginBottom: '0.75rem'
          }}>
            Ready to accelerate your implementations?
          </h2>
          <p style={{
            fontFamily: "'Manrope', sans-serif",
            fontSize: '1rem',
            color: COLORS.textLight,
            maxWidth: '500px',
            margin: '0 auto 1.5rem',
            lineHeight: '1.6'
          }}>
            Stop spending weeks on manual document analysis.
          </p>
          <Link 
            to="/workspace" 
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.875rem 2rem',
              background: COLORS.grassGreen,
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '1rem',
              fontWeight: '600',
              textDecoration: 'none',
              cursor: 'pointer'
            }}
          >
            Launch Workspace
            <ArrowRight style={{ width: 18, height: 18 }} />
          </Link>
        </section>
      </div>

      {/* Footer */}
      <footer style={{
        borderTop: `1px solid ${COLORS.iceFlow}`,
        padding: '1.5rem 2rem',
        textAlign: 'center',
        background: 'white'
      }}>
        <p style={{ 
          fontFamily: "'Manrope', sans-serif",
          fontSize: '0.85rem', 
          color: COLORS.textLight, 
          margin: 0 
        }}>
          © 2025 HCMPACT. Built with security, intelligence, and speed in mind.
        </p>
      </footer>
    </div>
  )
}
