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
  Layers,
  Eye,
  Table,
  FileSearch,
  BookOpen,
  Workflow,
  Users
} from 'lucide-react'

// H Logo SVG Component
const HLogo = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 570" style={{ width: '100%', height: '100%' }}>
    <path fill="#698f57" d="M492.04,500v-31.35l-36.53-35.01V163.76c0-15.8,.94-16.74,16.74-16.74h19.79v-31.36l-45.66-45.66H73v31.36l36.53,36.53V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35l45.66,45.66H492.04Zm-197.11-93.76c0,15.8-.94,16.74-16.74,16.74h-8.07v-103.81h24.81v87.07Zm-24.81-242.48c0-15.8,.94-16.74,16.74-16.74h8.07v95.13h-24.81v-78.39Z"/>
    <g>
      <rect fill="#a8ca99" x="134.8" y="348.24" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="324.95" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="302.12" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="279.29" width="64.39" height="11.87"/>
      <path fill="#a8ca99" d="M134.34,107.14h65.76c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
      <path fill="#a8ca99" d="M319.74,417.19c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.75Z"/>
      <rect fill="#a8ca99" x="134.8" y="371.08" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="393.91" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="118.1" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="164.22" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="140.93" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="256" width="64.39" height="11.87"/>
      <path fill="#a8ca99" d="M134.34,417.19c-.46,4.57-1.83,8.22-3.2,11.87h71.69c-1.37-3.65-2.28-7.31-2.74-11.87h-65.76Z"/>
      <rect fill="#a8ca99" x="134.8" y="140.93" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="233.17" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="187.05" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="134.8" y="210.34" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="371.08" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="324.95" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="348.24" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="279.29" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="302.12" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="393.91" width="64.39" height="11.87"/>
      <path fill="#a8ca99" d="M319.74,107.14h65.75c.46-4.57,1.37-8.68,2.74-11.87h-71.69c1.37,3.2,2.74,7.31,3.2,11.87Z"/>
      <rect fill="#a8ca99" x="320.19" y="164.22" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="118.1" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="187.05" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="210.34" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="256" width="64.39" height="11.87"/>
      <rect fill="#a8ca99" x="320.19" y="233.17" width="64.39" height="11.87"/>
    </g>
    <path fill="#84b26d" d="M426.59,95.27h13.7v-19.18h-173.52v19.18h11.42c19.18,0,22.83,3.65,22.83,22.83V248.24h-82.65V118.1c0-19.18,3.65-22.83,22.83-22.83h11.42v-19.18H79.09v19.18h13.7c19.18,0,22.83,3.65,22.83,22.83V406.24c0,19.18-3.65,22.83-22.83,22.83h-13.7v19.18H252.61v-19.18h-11.42c-19.18,0-22.83-3.65-22.83-22.83v-138.82h82.65v138.82c0,19.18-3.65,22.83-22.83,22.83h-11.42v19.18h173.52v-19.18h-13.7c-19.18,0-22.83-3.65-22.83-22.83V118.1c0-19.18,3.65-22.83,22.83-22.83Z"/>
    <path fill="#9cc28a" d="M426.59,101.36h19.79v-31.36h-183.7v31.36h15.5c15.8,0,16.74,.94,16.74,16.74v124.05h-70.47V118.1c0-15.8,.94-16.74,16.74-16.74h15.5v-31.36H73v31.36h19.79c15.8,0,16.74,.94,16.74,16.74V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35h183.7v-31.35h-15.5c-15.8,0-16.74-.94-16.74-16.74v-132.73h70.47v132.73c0,15.8,.94,16.74-16.74,16.74h-15.5v31.35h183.7v-31.35h-19.79c-15.8,0-16.74-.94-16.74-16.74V118.1c0-15.8,.94-16.74,16.74-16.74Z"/>
  </svg>
)

export default function Landing() {
  return (
    <div style={{ minHeight: '100vh', background: '#f6f5fa' }}>
      
      {/* Hero Section */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.95), rgba(104, 143, 87, 0.95))',
        color: 'white',
        padding: '5rem 2rem',
        textAlign: 'center'
      }}>
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
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
            marginBottom: '1.5rem',
            opacity: 0.95
          }}>
            Implementation Analysis Platform
          </h2>
          
          <p style={{
            fontFamily: "'Manrope', sans-serif",
            fontSize: '1.2rem',
            maxWidth: '750px',
            margin: '0 auto 2.5rem',
            lineHeight: '1.8',
            opacity: 0.92
          }}>
            Transform 6-8 weeks of manual analysis into hours. 
            Ingest any document, cross-reference all data sources, 
            generate deliverables. <strong>PII never leaves your environment.</strong>
          </p>
          
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link 
              to="/workspace" 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'white',
                color: '#83b16d',
                padding: '1rem 2rem',
                borderRadius: '12px',
                fontSize: '1.1rem',
                fontWeight: '600',
                textDecoration: 'none',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)',
                transition: 'transform 0.2s ease'
              }}
            >
              Get Started
              <ArrowRight style={{ width: 20, height: 20 }} />
            </Link>
            <Link 
              to="/playbooks" 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'transparent',
                color: 'white',
                padding: '1rem 2rem',
                borderRadius: '12px',
                fontSize: '1.1rem',
                fontWeight: '600',
                textDecoration: 'none',
                border: '2px solid rgba(255,255,255,0.5)',
                transition: 'all 0.2s ease'
              }}
            >
              View Playbooks
            </Link>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '4rem 2rem' }}>
        
        {/* The Problem / Solution */}
        <section style={{ marginBottom: '5rem', textAlign: 'center' }}>
          <h2 style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: '2rem',
            fontWeight: '700',
            color: '#2a3441',
            marginBottom: '3rem'
          }}>
            From Documents to Deliverables
          </h2>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '2rem',
            textAlign: 'left'
          }}>
            <div style={{
              background: 'white',
              borderRadius: '16px',
              padding: '2rem',
              boxShadow: '0 2px 8px rgba(42, 52, 65, 0.06)'
            }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📥</div>
              <h3 style={{ fontFamily: "'Sora', sans-serif", marginBottom: '0.75rem', color: '#2a3441' }}>
                Ingest Everything
              </h3>
              <p style={{ color: '#5f6c7b', lineHeight: 1.7 }}>
                PDFs, Excel files, Word docs, CSVs. 100+ source documents from your customer. 
                All processed, chunked, and made queryable automatically.
              </p>
            </div>
            
            <div style={{
              background: 'white',
              borderRadius: '16px',
              padding: '2rem',
              boxShadow: '0 2px 8px rgba(42, 52, 65, 0.06)'
            }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>🧠</div>
              <h3 style={{ fontFamily: "'Sora', sans-serif", marginBottom: '0.75rem', color: '#2a3441' }}>
                Intelligent Cross-Reference
              </h3>
              <p style={{ color: '#5f6c7b', lineHeight: 1.7 }}>
                AI reasons across all sources simultaneously. Structured data + documents + 
                global reference knowledge. Identifies conflicts and gaps.
              </p>
            </div>
            
            <div style={{
              background: 'white',
              borderRadius: '16px',
              padding: '2rem',
              boxShadow: '0 2px 8px rgba(42, 52, 65, 0.06)'
            }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📊</div>
              <h3 style={{ fontFamily: "'Sora', sans-serif", marginBottom: '0.75rem', color: '#2a3441' }}>
                Generate Deliverables
              </h3>
              <p style={{ color: '#5f6c7b', lineHeight: 1.7 }}>
                Output analysis workbooks, configuration templates, employee load files. 
                Structured, professional, ready for customer review.
              </p>
            </div>
          </div>
        </section>

        {/* Security Section */}
        <section style={{ marginBottom: '5rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
            <div style={{ 
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '64px',
              height: '64px',
              background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.15), rgba(147, 171, 217, 0.1))',
              borderRadius: '16px',
              marginBottom: '1rem'
            }}>
              <Shield style={{ width: 32, height: 32, color: '#83b16d' }} />
            </div>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '2rem',
              fontWeight: '700',
              color: '#2a3441',
              marginBottom: '0.5rem'
            }}>
              Security-First Architecture
            </h2>
            <p style={{ color: '#5f6c7b', fontSize: '1.1rem', maxWidth: '600px', margin: '0 auto' }}>
              PII protection isn't a feature — it's the foundation
            </p>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '1.5rem'
          }}>
            {[
              { 
                icon: <Lock style={{ width: 24, height: 24 }} />, 
                title: 'PII Detection & Encryption',
                desc: 'Automatic detection of SSN, DOB, salary, bank info. Encrypted at rest with AES-256. Decrypted only for authorized display.'
              },
              { 
                icon: <Eye style={{ width: 24, height: 24 }} />, 
                title: 'Local Processing',
                desc: 'Sensitive employee data processed by local LLM. Never sent to external APIs. Configuration data uses Claude for best results.'
              },
              { 
                icon: <Database style={{ width: 24, height: 24 }} />, 
                title: 'Project Isolation',
                desc: 'Complete data separation per customer. No cross-project data leakage. Isolated storage and query contexts.'
              },
              { 
                icon: <Server style={{ width: 24, height: 24 }} />, 
                title: 'Self-Hosted Option',
                desc: 'Deploy entirely within your infrastructure. Full control over data residency and compliance requirements.'
              }
            ].map((item, idx) => (
              <div key={idx} style={{
                background: 'white',
                borderRadius: '12px',
                padding: '1.5rem',
                boxShadow: '0 2px 8px rgba(42, 52, 65, 0.06)',
                display: 'flex',
                gap: '1rem'
              }}>
                <div style={{
                  flexShrink: 0,
                  width: '48px',
                  height: '48px',
                  background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.08))',
                  borderRadius: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#83b16d'
                }}>
                  {item.icon}
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1rem', fontWeight: '600', color: '#2a3441', marginBottom: '0.5rem' }}>
                    {item.title}
                  </h3>
                  <p style={{ fontSize: '0.9rem', color: '#5f6c7b', lineHeight: 1.6, margin: 0 }}>
                    {item.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Technology Stack */}
        <section style={{ marginBottom: '5rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
            <div style={{ 
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '64px',
              height: '64px',
              background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.15), rgba(147, 171, 217, 0.1))',
              borderRadius: '16px',
              marginBottom: '1rem'
            }}>
              <Layers style={{ width: 32, height: 32, color: '#83b16d' }} />
            </div>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '2rem',
              fontWeight: '700',
              color: '#2a3441',
              marginBottom: '0.5rem'
            }}>
              Built for Scale & Intelligence
            </h2>
            <p style={{ color: '#5f6c7b', fontSize: '1.1rem', maxWidth: '600px', margin: '0 auto' }}>
              Modern stack designed for self-healing, intelligent document processing
            </p>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '1.5rem'
          }}>
            {[
              { 
                icon: <Cpu style={{ width: 24, height: 24 }} />, 
                title: 'Dual-LLM Architecture',
                desc: 'Claude for configuration analysis, local LLM for employee data. Smart routing based on content sensitivity.'
              },
              { 
                icon: <Table style={{ width: 24, height: 24 }} />, 
                title: 'DuckDB + ChromaDB',
                desc: 'Structured data in DuckDB for SQL queries. Documents in ChromaDB for semantic search. Best of both worlds.'
              },
              { 
                icon: <FileSearch style={{ width: 24, height: 24 }} />, 
                title: 'Universal Document Processing',
                desc: 'OCR, table extraction, intelligent chunking. PDFs, Excel, Word, images — all normalized and queryable.'
              },
              { 
                icon: <Workflow style={{ width: 24, height: 24 }} />, 
                title: 'Playbook Engine',
                desc: 'Capture successful analysis patterns as reusable playbooks. Run against any customer data.'
              },
              { 
                icon: <Zap style={{ width: 24, height: 24 }} />, 
                title: 'Self-Healing Systems',
                desc: 'No brittle regex patterns. AI-driven detection and classification. Learns and adapts.'
              },
              { 
                icon: <Cloud style={{ width: 24, height: 24 }} />, 
                title: 'API Integration Ready',
                desc: 'Connect to UKG Pro, WFM, Ready via API. Pull configuration data directly from customer instances.'
              }
            ].map((item, idx) => (
              <div key={idx} style={{
                background: 'white',
                borderRadius: '12px',
                padding: '1.5rem',
                boxShadow: '0 2px 8px rgba(42, 52, 65, 0.06)',
                display: 'flex',
                gap: '1rem'
              }}>
                <div style={{
                  flexShrink: 0,
                  width: '48px',
                  height: '48px',
                  background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.08))',
                  borderRadius: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#83b16d'
                }}>
                  {item.icon}
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: '1rem', fontWeight: '600', color: '#2a3441', marginBottom: '0.5rem' }}>
                    {item.title}
                  </h3>
                  <p style={{ fontSize: '0.9rem', color: '#5f6c7b', lineHeight: 1.6, margin: 0 }}>
                    {item.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Platform Features */}
        <section style={{ marginBottom: '5rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '2rem',
              fontWeight: '700',
              color: '#2a3441',
              marginBottom: '0.5rem'
            }}>
              Platform Capabilities
            </h2>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '1.25rem'
          }}>
            {[
              { icon: <MessageSquare style={{ width: 20, height: 20 }} />, title: 'Intelligent Workspace', desc: 'Chat-based analysis across all data sources' },
              { icon: <FileText style={{ width: 20, height: 20 }} />, title: 'Multi-File Upload', desc: 'Batch upload with automatic processing' },
              { icon: <Table style={{ width: 20, height: 20 }} />, title: 'Vacuum Extractor', desc: 'Pull tables from PDFs and images' },
              { icon: <BookOpen style={{ width: 20, height: 20 }} />, title: 'Playbooks', desc: 'Pre-built analysis templates' },
              { icon: <BarChart3 style={{ width: 20, height: 20 }} />, title: 'Processing Dashboard', desc: 'Real-time job status and monitoring' },
              { icon: <Users style={{ width: 20, height: 20 }} />, title: 'Customer Workspaces', desc: 'Isolated customer workspaces' }
            ].map((feature, idx) => (
              <div key={idx} style={{
                background: 'white',
                borderRadius: '12px',
                padding: '1.25rem',
                boxShadow: '0 2px 8px rgba(42, 52, 65, 0.06)',
                display: 'flex',
                alignItems: 'center',
                gap: '1rem'
              }}>
                <div style={{
                  flexShrink: 0,
                  width: '40px',
                  height: '40px',
                  background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.1))',
                  borderRadius: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#83b16d'
                }}>
                  {feature.icon}
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Sora', sans-serif", fontSize: '0.95rem', fontWeight: '600', color: '#2a3441', marginBottom: '0.2rem' }}>
                    {feature.title}
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: '#5f6c7b', margin: 0 }}>
                    {feature.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA Section */}
        <section style={{
          background: 'linear-gradient(135deg, rgba(131, 177, 109, 0.12), rgba(147, 171, 217, 0.08))',
          borderRadius: '20px',
          padding: '4rem 2rem',
          textAlign: 'center'
        }}>
          <h2 style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: '2.25rem',
            fontWeight: '700',
            color: '#2a3441',
            marginBottom: '1rem'
          }}>
            Ready to accelerate your implementations?
          </h2>
          <p style={{
            fontSize: '1.1rem',
            color: '#5f6c7b',
            maxWidth: '600px',
            margin: '0 auto 2rem',
            lineHeight: '1.7'
          }}>
            Stop spending weeks on manual document analysis. 
            Let the platform do the heavy lifting while you focus on the decisions that matter.
          </p>
          <Link 
            to="/workspace" 
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: 'linear-gradient(135deg, #83b16d, #688f57)',
              color: 'white',
              padding: '1rem 2.5rem',
              borderRadius: '12px',
              fontSize: '1.1rem',
              fontWeight: '600',
              textDecoration: 'none',
              boxShadow: '0 4px 16px rgba(131, 177, 109, 0.3)'
            }}
          >
            Launch Workspace
            <ArrowRight style={{ width: 20, height: 20 }} />
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
        <p style={{ fontSize: '0.9rem', color: '#5f6c7b', margin: 0 }}>
          © 2025 HCMPACT. Built with security, intelligence, and speed in mind.
        </p>
      </footer>
    </div>
  )
}
