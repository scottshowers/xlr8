/**
 * WelcomePage.jsx - Sales backdrop / Onboarding page
 * 
 * UPDATED: December 23, 2025
 * - Mission Control color palette (#83b16d)
 * - Removed dark mode
 * 
 * Three presentation options:
 * 1. The Story - Narrative chapter-based
 * 2. The Journey - Visual infographic
 * 3. Watch It Think - Live intelligence demo
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  BookOpen, Map, Sparkles, ArrowRight, Shield, Lock, 
  Server, FileText, Rocket
} from 'lucide-react';

// Mission Control Colors
const colors = {
  bg: '#f0f2f5',
  bgAlt: '#e8ebf0',
  card: '#ffffff',
  border: '#e2e8f0',
  text: '#1a2332',
  textMuted: '#64748b',
  textLight: '#94a3b8',
  primary: '#83b16d',
  primaryLight: 'rgba(131, 177, 109, 0.1)',
  primaryDark: '#6b9b5a',
  accent: '#285390',
  accentLight: 'rgba(40, 83, 144, 0.1)',
  purple: '#5f4282',
  purpleLight: 'rgba(95, 66, 130, 0.1)',
};

export default function WelcomePage() {
  const navigate = useNavigate();
  const [hoveredCard, setHoveredCard] = useState(null);

  const presentations = [
    {
      id: 'story',
      route: '/story',
      icon: BookOpen,
      title: 'The Story',
      subtitle: 'Narrative Experience',
      description: 'A chapter-by-chapter journey through how XLR8 transforms data analysis. Best for those who want the full context.',
      duration: '~5 min read',
      color: colors.primary,
      colorLight: colors.primaryLight,
    },
    {
      id: 'journey',
      route: '/journey',
      icon: Map,
      title: 'The Journey',
      subtitle: 'Visual Infographic',
      description: 'Connected visual flowchart showing the transformation from manual work to intelligent automation.',
      duration: '~3 min',
      color: colors.accent,
      colorLight: colors.accentLight,
    },
    {
      id: 'think',
      route: '/intelligence-demo',
      icon: Sparkles,
      title: 'Watch It Think',
      subtitle: 'Live Demo',
      description: 'See the intelligence engine process data in real-time. Watch classifications, relationships, and patterns emerge.',
      duration: 'Interactive',
      color: colors.purple,
      colorLight: colors.purpleLight,
    },
  ];

  const securityPoints = [
    {
      icon: Server,
      title: 'Local Processing',
      description: 'All AI runs on local LLMs within your environment. No data sent to public APIs.',
    },
    {
      icon: Lock,
      title: 'Protected PII',
      description: 'Sensitive data stays encrypted. PII is detected and protected automatically.',
    },
    {
      icon: Shield,
      title: 'Your Data, Your Control',
      description: 'Data never leaves your infrastructure. Full audit trail of all processing.',
    },
    {
      icon: FileText,
      title: 'Regulatory Compliance',
      description: 'Validate against FLSA, ACA, state laws. Catch gaps before audits find them.',
    },
  ];

  return (
    <div style={{
      minHeight: '100vh',
      background: colors.bg,
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Header */}
      <div style={{
        background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryDark} 100%)`,
        padding: '1rem 2rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{
            fontFamily: "'Sora', sans-serif",
            fontSize: '1.5rem',
            fontWeight: 800,
            color: 'white',
          }}>
            XLR8
          </span>
          <Rocket size={20} color="white" />
        </div>
        <button
          onClick={() => navigate('/dashboard')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.6rem 1rem',
            background: 'rgba(255,255,255,0.15)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: 8,
            color: 'white',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Skip to Platform <ArrowRight size={16} />
        </button>
      </div>

      {/* Hero */}
      <div style={{
        padding: '4rem 2rem',
        textAlign: 'center',
        maxWidth: 800,
        margin: '0 auto',
      }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 1rem',
          background: colors.primaryLight,
          borderRadius: 20,
          marginBottom: '1.5rem',
        }}>
          <Shield size={14} style={{ color: colors.primary }} />
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: colors.primary }}>
            Secure AI · Local Processing · Your Data Stays Yours
          </span>
        </div>
        
        <h1 style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: '2.75rem',
          fontWeight: 800,
          lineHeight: 1.1,
          letterSpacing: '-0.03em',
          color: colors.text,
          margin: '0 0 1rem 0',
        }}>
          Intelligence Without<br />Compromise
        </h1>
        
        <p style={{
          fontSize: '1.15rem',
          color: colors.textMuted,
          lineHeight: 1.6,
          maxWidth: 600,
          margin: '0 auto',
        }}>
          XLR8 brings AI-powered analysis to your data—validating against regulations, catching compliance gaps, 
          and keeping everything secure, private, and under your control.
        </p>
      </div>

      {/* Presentation Options */}
      <div style={{
        maxWidth: 1100,
        margin: '0 auto',
        padding: '0 2rem 3rem',
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '1.5rem',
        }}>
          {presentations.map((pres) => (
            <div
              key={pres.id}
              onClick={() => navigate(pres.route)}
              onMouseEnter={() => setHoveredCard(pres.id)}
              onMouseLeave={() => setHoveredCard(null)}
              style={{
                background: colors.card,
                border: `2px solid ${hoveredCard === pres.id ? pres.color : colors.border}`,
                borderRadius: 16,
                padding: '2rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                transform: hoveredCard === pres.id ? 'translateY(-4px)' : 'translateY(0)',
                boxShadow: hoveredCard === pres.id ? '0 12px 32px rgba(0,0,0,0.1)' : 'none',
              }}
            >
              <div style={{
                width: 56,
                height: 56,
                borderRadius: 14,
                background: pres.colorLight,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1.25rem',
              }}>
                <pres.icon size={26} style={{ color: pres.color }} />
              </div>
              
              <h3 style={{
                fontFamily: "'Sora', sans-serif",
                fontSize: '1.25rem',
                fontWeight: 700,
                color: colors.text,
                margin: '0 0 0.25rem 0',
              }}>
                {pres.title}
              </h3>
              
              <div style={{
                fontSize: '0.8rem',
                fontWeight: 600,
                color: pres.color,
                marginBottom: '0.75rem',
              }}>
                {pres.subtitle}
              </div>
              
              <p style={{
                fontSize: '0.9rem',
                color: colors.textMuted,
                lineHeight: 1.5,
                marginBottom: '1.25rem',
              }}>
                {pres.description}
              </p>
              
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <span style={{
                  fontSize: '0.75rem',
                  color: colors.textLight,
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  {pres.duration}
                </span>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  color: hoveredCard === pres.id ? pres.color : colors.textMuted,
                  fontSize: '0.85rem',
                  fontWeight: 600,
                }}>
                  Start <ArrowRight size={16} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Security Section */}
      <div style={{
        background: colors.bgAlt,
        padding: '4rem 2rem',
        borderTop: `1px solid ${colors.border}`,
      }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
            <h2 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '1.75rem',
              fontWeight: 800,
              color: colors.text,
              marginBottom: '0.75rem',
            }}>
              Secure AI. Real Compliance.
            </h2>
            <p style={{
              fontSize: '1rem',
              color: colors.textMuted,
              maxWidth: 600,
              margin: '0 auto',
            }}>
              We built XLR8 with security and compliance as the foundation. 
              Your sensitive data gets intelligent analysis without exposure risk—and validation against the regulations that matter.
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '1.25rem',
          }}>
            {securityPoints.map((point, i) => (
              <div
                key={i}
                style={{
                  background: colors.card,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 12,
                  padding: '1.5rem',
                  textAlign: 'center',
                }}
              >
                <div style={{
                  width: 48,
                  height: 48,
                  borderRadius: 12,
                  background: colors.primaryLight,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 1rem',
                }}>
                  <point.icon size={22} style={{ color: colors.primary }} />
                </div>
                <h4 style={{
                  fontFamily: "'Sora', sans-serif",
                  fontSize: '0.95rem',
                  fontWeight: 700,
                  color: colors.text,
                  marginBottom: '0.5rem',
                }}>
                  {point.title}
                </h4>
                <p style={{
                  fontSize: '0.8rem',
                  color: colors.textMuted,
                  lineHeight: 1.5,
                  margin: 0,
                }}>
                  {point.description}
                </p>
              </div>
            ))}
          </div>

          {/* Technical Detail */}
          <div style={{
            marginTop: '2.5rem',
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 12,
            padding: '1.5rem 2rem',
            display: 'flex',
            alignItems: 'center',
            gap: '2rem',
          }}>
            <div style={{
              width: 64,
              height: 64,
              borderRadius: 16,
              background: `linear-gradient(135deg, ${colors.primary}, ${colors.accent})`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Server size={28} style={{ color: 'white' }} />
            </div>
            <div style={{ flex: 1 }}>
              <h4 style={{
                fontFamily: "'Sora', sans-serif",
                fontSize: '1rem',
                fontWeight: 700,
                color: colors.text,
                marginBottom: '0.5rem',
              }}>
                Local LLM Architecture
              </h4>
              <p style={{
                fontSize: '0.85rem',
                color: colors.textMuted,
                lineHeight: 1.6,
                margin: 0,
              }}>
                XLR8 runs AI models locally using Ollama with DeepSeek for SQL generation and Mistral for synthesis. 
                No OpenAI, no cloud APIs, no data leaving your environment. 
                The Claude API is available only as a fallback for complex edge cases—and even then, 
                only with explicit configuration. Your PII stays protected, period.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Start CTA */}
      <div style={{
        padding: '3rem 2rem',
        textAlign: 'center',
        background: colors.bg,
      }}>
        <p style={{
          fontSize: '1rem',
          color: colors.textMuted,
          marginBottom: '1rem',
        }}>
          Ready to dive in?
        </p>
        <button
          onClick={() => navigate('/dashboard')}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '1rem 2rem',
            background: colors.primary,
            color: 'white',
            border: 'none',
            borderRadius: 12,
            fontSize: '1rem',
            fontWeight: 700,
            fontFamily: "'Sora', sans-serif",
            cursor: 'pointer',
          }}
        >
          Go to Dashboard <ArrowRight size={18} />
        </button>
      </div>

      {/* Footer */}
      <footer style={{
        padding: '1.5rem 2rem',
        borderTop: `1px solid ${colors.border}`,
        textAlign: 'center',
        color: colors.textLight,
        fontSize: '0.8rem',
      }}>
        Built with  by <span style={{ color: colors.primary, fontWeight: 600 }}>XLR8</span> · 
        Intelligence without compromise
      </footer>
    </div>
  );
}
