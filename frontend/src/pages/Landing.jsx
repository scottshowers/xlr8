import { Link } from 'react-router-dom'
import { 
  Shield, 
  Zap, 
  Database, 
  Lock, 
  Cloud, 
  Code, 
  FileText, 
  MessageSquare, 
  BarChart3,
  CheckCircle2,
  ArrowRight,
  Server,
  Cpu,
  Layers
} from 'lucide-react'

// H Logo SVG Component - Silver Version
const HLogo = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 570" style={{ width: '100%', height: '100%' }}>
    <defs>
      <style>
        {`
          .cls-1 { fill: #b5b5b4; }
          .cls-2 { fill: #828281; }
          .cls-3 { fill: #bebebd; }
          .cls-4 { fill: #a2a2a1; }
        `}
      </style>
    </defs>
    <g id="Silver_H" data-name="Silver H">
      <path id="Drop_Shadow" data-name="Drop Shadow" className="cls-2" d="M495.76,500v-31.35l-36.53-35.01V163.76c0-15.8,.94-16.74,16.74-16.74h19.79v-31.36l-45.66-45.66H76.72v31.36l36.53,36.53V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35l45.66,45.66H495.76Zm-197.11-93.76c0,15.8-.94,16.74-16.74,16.74h-8.07v-103.81h24.81v87.07Zm-24.81-242.48c0-15.8,.94-16.74,16.74-16.74h8.07v95.13h-24.81v-78.39Z"/>
      <g id="Inner_Lines" data-name="Inner Lines">
        <g>
          <rect className="cls-3" x="138.52" y="348.24" width="64.39" height="11.87"/>
          <rect className="cls-3" x="138.52" y="324.96" width="64.39" height="11.87"/>
          <rect className="cls-3" x="138.52" y="302.12" width="64.39" height="11.87"/>
          <rect className="cls-3" x="138.52" y="279.29" width="64.39" height="11.87"/>
          <path className="cls-3" d="M138.06,107.14h65.76c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
          <path className="cls-3" d="M323.46,417.2c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.75Z"/>
          <rect className="cls-3" x="138.52" y="371.08" width="64.39" height="11.87"/>
          <rect className="cls-3" x="138.52" y="393.91" width="64.39" height="11.87"/>
          <rect className="cls-3" x="138.52" y="118.1" width="64.39" height="11.87"/>
          <rect className="cls-3" x="138.52" y="164.22" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="140.93" width="64.39" height="11.87"/>
          <rect className="cls-3" x="138.52" y="256" width="64.39" height="11.87"/>
          <path className="cls-3" d="M138.06,417.2c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.76Z"/>
          <rect className="cls-3" x="138.52" y="140.93" width="64.39" height="11.87"/>
          <rect className="cls-3" x="138.52" y="233.17" width="64.39" height="11.87"/>
          <rect className="cls-3" x="138.52" y="187.05" width="64.39" height="11.87"/>
          <rect className="cls-3" x="138.52" y="210.34" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="371.08" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="324.96" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="348.24" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="279.29" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="302.12" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="393.91" width="64.39" height="11.87"/>
          <path className="cls-3" d="M323.46,107.14h65.75c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
          <rect className="cls-3" x="323.91" y="164.22" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="118.1" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="187.05" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="210.34" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="256" width="64.39" height="11.87"/>
          <rect className="cls-3" x="323.91" y="233.17" width="64.39" height="11.87"/>
        </g>
      </g>
      <path id="Base_H" data-name="Base H" className="cls-4" d="M430.31,95.27h13.7v-19.18h-173.52v19.18h11.42c19.18,0,22.83,3.65,22.83,22.83V248.24h-82.65V118.1c0-19.18,3.65-22.83,22.83-22.83h11.42v-19.18H82.81v19.18h13.7c19.18,0,22.83,3.65,22.83,22.83V406.24c0,19.18-3.65,22.83-22.83,22.83h-13.7v19.18h173.52v-19.18h-11.42c-19.18,0-22.83-3.65-22.83-22.83v-138.82h82.65v138.82c0,19.18-3.65,22.83-22.83,22.83h-11.42v19.18h173.52v-19.18h-13.7c-19.18,0-22.83-3.65-22.83-22.83V118.1c0-19.18,3.65-22.83,22.83-22.83Zm-42.01,45.66v11.87h-64.39v-11.87h64.39Zm-64.39-10.96v-11.87h64.39v11.87h-64.39Zm64.39,34.25v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm.91,23.29c.46,4.57,1.37,8.22,2.74,11.87h-71.69c1.37-3.65,2.74-7.31,3.2-11.87h65.75Zm0-310.05h-65.75c-.46-4.57-1.83-8.68-3.2-11.87h71.69c-1.37,3.2-2.28,7.31-2.74,11.87Zm-186.31,33.79v11.87h-64.39v-11.87h64.39Zm-64.39-10.96v-11.87h64.39v11.87h-64.39Zm64.39,34.25v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,23.29v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm0,22.83v11.87h-64.39v-11.87h64.39Zm.91,23.29c.46,4.57,1.37,8.22,2.74,11.87h-71.69c1.37-3.65,2.74-7.31,3.2-11.87h65.76Zm0-310.05h-65.76c-.46-4.57-1.83-8.68-3.2-11.87h71.69c-1.37,3.2-2.28,7.31-2.74,11.87Z"/>
      <path id="Outer_Stroke" data-name="Outer Stroke" className="cls-1" d="M430.31,101.36h19.79v-31.36h-183.7v31.36h15.5c15.8,0,16.74,.94,16.74,16.74v124.05h-70.47V118.1c0-15.8,.94-16.74,16.74-16.74h15.5v-31.36H76.72v31.36h19.79c15.8,0,16.74,.94,16.74,16.74V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35h183.7v-31.35h-15.5c-15.8,0-16.74-.94-16.74-16.74v-132.73h70.47v132.73c0,15.8-.94,16.74-16.74,16.74h-15.5v31.35h183.7v-31.35h-19.79c-15.8,0-16.74-.94-16.74-16.74V118.1c0-15.8,.94-16.74,16.74-16.74Zm0,327.71h13.7v19.18h-173.52v-19.18h11.42c19.18,0,22.83-3.65,22.83-22.83v-138.82h-82.65v138.82c0,19.18,3.65,22.83,22.83,22.83h11.42v19.18H82.81v-19.18h13.7c19.18,0,22.83-3.65,22.83-22.83V118.1c0-19.18-3.65-22.83-22.83-22.83h-13.7v-19.18h173.52v19.18h-11.42c-19.18,0-22.83,3.65-22.83,22.83V248.24h82.65V118.1c0-19.18-3.65-22.83-22.83-22.83h-11.42v-19.18h173.52v19.18h-13.7c-19.18,0-22.83,3.65-22.83,22.83V406.24c0,19.18,3.65,22.83,22.83,22.83Z"/>
    </g>
  </svg>
)

export default function Landing() {
  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #f6f5fa 0%, #e8f5e9 100%)'
    }}>
      {/* Hero Section */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.95), rgba(104, 143, 87, 0.95))',
        color: 'white',
        padding: '4rem 2rem',
        textAlign: 'center'
      }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            gap: '1.5rem',
            marginBottom: '2rem'
          }}>
            <div style={{ 
              width: '80px', 
              height: '80px',
              filter: 'drop-shadow(0 4px 12px rgba(0, 0, 0, 0.3))'
            }}>
              <HLogo />
            </div>
            <h1 style={{ 
              fontFamily: "'Sora', sans-serif",
              fontSize: '4rem',
              fontWeight: '700',
              margin: 0,
              textShadow: '0 2px 16px rgba(255, 255, 255, 0.3)'
            }}>
              XLR8
            </h1>
          </div>
          
          <h2 style={{
            fontFamily: "'Manrope', sans-serif",
            fontSize: '1.5rem',
            fontWeight: '500',
            marginBottom: '1rem',
            opacity: 0.95
          }}>
            HCMPACT Analysis Engine
          </h2>
          
          <p style={{
            fontFamily: "'Manrope', sans-serif",
            fontSize: '1.125rem',
            maxWidth: '700px',
            margin: '0 auto 2.5rem',
            lineHeight: '1.7',
            opacity: 0.9
          }}>
            Enterprise-grade AI platform for HCM Technology Projects. 
            Secure, scalable, and purpose-built for HCM consultants.
          </p>
          
          <Link 
            to="/chat" 
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: 'white',
              color: '#83b16d',
              padding: '1rem 2rem',
              borderRadius: '12px',
              fontSize: '1.125rem',
              fontWeight: '600',
              textDecoration: 'none',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)',
              transition: 'transform 0.2s ease, box-shadow 0.2s ease'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.25)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.2)'
            }}
          >
            Get Started
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </div>

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '4rem 2rem' }}>
        
        {/* Technology Stack */}
        <section style={{ marginBottom: '5rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
            <div style={{ 
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '64px',
              height: '64px',
              background: 'linear-gradient(135deg, #83b16d, #93abd9)',
              borderRadius: '16px',
              marginBottom: '1rem'
            }}>
              <Layers className="w-8 h-8 text-white" />
            </div>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '2.5rem',
              fontWeight: '700',
              color: '#2a3441',
              marginBottom: '0.5rem'
            }}>
              Technology Stack
            </h2>
            <p style={{
              fontFamily: "'Manrope', sans-serif",
              fontSize: '1.125rem',
              color: '#5f6c7b',
              maxWidth: '600px',
              margin: '0 auto'
            }}>
              Built on modern, enterprise-grade infrastructure
            </p>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '2rem'
          }}>
            {[
              { 
                icon: <Server className="w-6 h-6" />, 
                title: 'FastAPI Backend',
                desc: 'High-performance Python API with async support'
              },
              { 
                icon: <Code className="w-6 h-6" />, 
                title: 'React Frontend',
                desc: 'Modern UI built with React & Vite for speed'
              },
              { 
                icon: <Database className="w-6 h-6" />, 
                title: 'PostgreSQL',
                desc: 'Supabase-hosted relational database'
              },
              { 
                icon: <Cpu className="w-6 h-6" />, 
                title: 'ChromaDB',
                desc: 'Vector database for semantic search'
              },
              { 
                icon: <Zap className="w-6 h-6" />, 
                title: 'Ollama LLM',
                desc: 'Self-hosted AI models (Mistral, DeepSeek)'
              },
              { 
                icon: <Cloud className="w-6 h-6" />, 
                title: 'Railway & Vercel',
                desc: 'Scalable cloud deployment infrastructure'
              }
            ].map((tech, idx) => (
              <div key={idx} style={{
                background: 'white',
                borderRadius: '16px',
                padding: '2rem',
                boxShadow: '0 2px 8px rgba(42, 52, 65, 0.08)',
                transition: 'transform 0.2s ease, box-shadow 0.2s ease'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)'
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(131, 177, 109, 0.15)'
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = '0 2px 8px rgba(42, 52, 65, 0.08)'
              }}>
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '48px',
                  height: '48px',
                  background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.1))',
                  borderRadius: '12px',
                  color: '#83b16d',
                  marginBottom: '1rem'
                }}>
                  {tech.icon}
                </div>
                <h3 style={{
                  fontFamily: "'Sora', sans-serif",
                  fontSize: '1.25rem',
                  fontWeight: '600',
                  color: '#2a3441',
                  marginBottom: '0.5rem'
                }}>
                  {tech.title}
                </h3>
                <p style={{
                  fontFamily: "'Manrope', sans-serif",
                  fontSize: '0.95rem',
                  color: '#5f6c7b',
                  lineHeight: '1.6'
                }}>
                  {tech.desc}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Security Features */}
        <section style={{ marginBottom: '5rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
            <div style={{ 
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '64px',
              height: '64px',
              background: 'linear-gradient(135deg, #83b16d, #93abd9)',
              borderRadius: '16px',
              marginBottom: '1rem'
            }}>
              <Shield className="w-8 h-8 text-white" />
            </div>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '2.5rem',
              fontWeight: '700',
              color: '#2a3441',
              marginBottom: '0.5rem'
            }}>
              Enterprise Security
            </h2>
            <p style={{
              fontFamily: "'Manrope', sans-serif",
              fontSize: '1.125rem',
              color: '#5f6c7b',
              maxWidth: '600px',
              margin: '0 auto'
            }}>
              Your data security is our top priority
            </p>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '2rem'
          }}>
            {[
              { 
                icon: <Lock className="w-6 h-6" />, 
                title: 'Self-Hosted AI',
                desc: 'All LLM processing happens on your infrastructure. No data sent to third-party AI services.',
                badge: 'Private'
              },
              { 
                icon: <Database className="w-6 h-6" />, 
                title: 'Isolated Storage',
                desc: 'Each project has isolated vector embeddings. Documents are segmented and never mixed.',
                badge: 'Isolated'
              },
              { 
                icon: <Shield className="w-6 h-6" />, 
                title: 'Secure Authentication',
                desc: 'HTTP Basic Auth for internal services. Row-level security on all database operations.',
                badge: 'Authenticated'
              },
              { 
                icon: <FileText className="w-6 h-6" />, 
                title: 'Audit Logging',
                desc: 'All document uploads, queries, and system actions are logged for compliance.',
                badge: 'Compliant'
              }
            ].map((feature, idx) => (
              <div key={idx} style={{
                background: 'white',
                borderRadius: '16px',
                padding: '2rem',
                boxShadow: '0 2px 8px rgba(42, 52, 65, 0.08)',
                border: '2px solid rgba(131, 177, 109, 0.1)'
              }}>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '1rem'
                }}>
                  <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '48px',
                    height: '48px',
                    background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.15), rgba(147, 171, 217, 0.15))',
                    borderRadius: '12px',
                    color: '#83b16d'
                  }}>
                    {feature.icon}
                  </div>
                  <span style={{
                    background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.1))',
                    color: '#83b16d',
                    padding: '0.25rem 0.75rem',
                    borderRadius: '8px',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    fontFamily: "'Manrope', sans-serif"
                  }}>
                    {feature.badge}
                  </span>
                </div>
                <h3 style={{
                  fontFamily: "'Sora', sans-serif",
                  fontSize: '1.25rem',
                  fontWeight: '600',
                  color: '#2a3441',
                  marginBottom: '0.5rem'
                }}>
                  {feature.title}
                </h3>
                <p style={{
                  fontFamily: "'Manrope', sans-serif",
                  fontSize: '0.95rem',
                  color: '#5f6c7b',
                  lineHeight: '1.6'
                }}>
                  {feature.desc}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Platform Features */}
        <section style={{ marginBottom: '5rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
            <div style={{ 
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '64px',
              height: '64px',
              background: 'linear-gradient(135deg, #83b16d, #93abd9)',
              borderRadius: '16px',
              marginBottom: '1rem'
            }}>
              <Zap className="w-8 h-8 text-white" />
            </div>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '2.5rem',
              fontWeight: '700',
              color: '#2a3441',
              marginBottom: '0.5rem'
            }}>
              Platform Features
            </h2>
            <p style={{
              fontFamily: "'Manrope', sans-serif",
              fontSize: '1.125rem',
              color: '#5f6c7b',
              maxWidth: '600px',
              margin: '0 auto'
            }}>
              Everything you need for HCM Technology Projects
            </p>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '1.5rem'
          }}>
            {[
              { 
                icon: <MessageSquare className="w-5 h-5" />, 
                title: 'AI Chat',
                desc: 'Query your documents with natural language'
              },
              { 
                icon: <FileText className="w-5 h-5" />, 
                title: 'Document Upload',
                desc: 'PDF, Excel, Word - all formats supported'
              },
              { 
                icon: <Database className="w-5 h-5" />, 
                title: 'Project Isolation',
                desc: 'Keep client data completely separated'
              },
              { 
                icon: <BarChart3 className="w-5 h-5" />, 
                title: 'Status Monitoring',
                desc: 'Real-time processing and job tracking'
              },
              { 
                icon: <Shield className="w-5 h-5" />, 
                title: 'SECURE 2.0',
                desc: 'Specialized analysis for HCM Technology Projects'
              },
              { 
                icon: <CheckCircle2 className="w-5 h-5" />, 
                title: 'Batch Processing',
                desc: 'Upload multiple documents simultaneously'
              }
            ].map((feature, idx) => (
              <div key={idx} style={{
                background: 'white',
                borderRadius: '12px',
                padding: '1.5rem',
                boxShadow: '0 2px 8px rgba(42, 52, 65, 0.06)',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '1rem'
              }}>
                <div style={{
                  flexShrink: 0,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '40px',
                  height: '40px',
                  background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.1))',
                  borderRadius: '10px',
                  color: '#83b16d'
                }}>
                  {feature.icon}
                </div>
                <div>
                  <h3 style={{
                    fontFamily: "'Sora', sans-serif",
                    fontSize: '1.05rem',
                    fontWeight: '600',
                    color: '#2a3441',
                    marginBottom: '0.25rem'
                  }}>
                    {feature.title}
                  </h3>
                  <p style={{
                    fontFamily: "'Manrope', sans-serif",
                    fontSize: '0.9rem',
                    color: '#5f6c7b',
                    lineHeight: '1.5',
                    margin: 0
                  }}>
                    {feature.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA Section */}
        <section style={{
          background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.05))',
          borderRadius: '20px',
          padding: '4rem 2rem',
          textAlign: 'center'
        }}>
          <h2 style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: '2.5rem',
            fontWeight: '700',
            color: '#2a3441',
            marginBottom: '1rem'
          }}>
            Ready to accelerate your analysis?
          </h2>
          <p style={{
            fontFamily: "'Manrope', sans-serif",
            fontSize: '1.125rem',
            color: '#5f6c7b',
            maxWidth: '600px',
            margin: '0 auto 2rem',
            lineHeight: '1.7'
          }}>
            Start using XLR8 to analyze HCM Technology Projects faster, 
            more accurately, and with complete data security.
          </p>
          <Link 
            to="/chat" 
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: 'linear-gradient(135deg, #83b16d, #688f57)',
              color: 'white',
              padding: '1rem 2.5rem',
              borderRadius: '12px',
              fontSize: '1.125rem',
              fontWeight: '600',
              textDecoration: 'none',
              boxShadow: '0 4px 16px rgba(131, 177, 109, 0.3)',
              transition: 'transform 0.2s ease, box-shadow 0.2s ease'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 6px 20px rgba(131, 177, 109, 0.4)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 4px 16px rgba(131, 177, 109, 0.3)'
            }}
          >
            Launch Platform
            <ArrowRight className="w-5 h-5" />
          </Link>
        </section>
      </div>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid #e1e8ed',
        padding: '2rem',
        textAlign: 'center',
        background: 'white'
      }}>
        <p style={{
          fontFamily: "'Manrope', sans-serif",
          fontSize: '0.9rem',
          color: '#5f6c7b',
          margin: 0
        }}>
          © 2025 HCMPACT. Built with security and performance in mind.
        </p>
      </footer>
    </div>
  )
}
