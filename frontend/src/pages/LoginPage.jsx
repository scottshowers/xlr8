/**
 * LoginPage - Clean login matching screenshot design
 */

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Rocket } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const COLORS = {
  grassGreen: '#83b16d',
  text: '#2a3441',
  textLight: '#5f6c7b',
  border: '#e1e8ed',
  bg: '#f6f5fa',
  white: '#ffffff',
  red: '#e74c3c',
};

// H Logo matching Landing page
const HLogo = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 570" style={{ width: '100%', height: '100%' }}>
    <path fill="rgba(255,255,255,0.3)" d="M492.04,500v-31.35l-36.53-35.01V163.76c0-15.8,.94-16.74,16.74-16.74h19.79v-31.36l-45.66-45.66H73v31.36l36.53,36.53V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35l45.66,45.66H492.04Z"/>
    <g fill="rgba(255,255,255,0.5)">
      <rect x="134.8" y="348.24" width="64.39" height="11.87"/>
      <rect x="134.8" y="324.95" width="64.39" height="11.87"/>
      <rect x="134.8" y="302.12" width="64.39" height="11.87"/>
      <rect x="134.8" y="279.29" width="64.39" height="11.87"/>
      <rect x="134.8" y="371.08" width="64.39" height="11.87"/>
      <rect x="134.8" y="393.91" width="64.39" height="11.87"/>
      <rect x="134.8" y="118.1" width="64.39" height="11.87"/>
      <rect x="134.8" y="164.22" width="64.39" height="11.87"/>
      <rect x="320.19" y="140.93" width="64.39" height="11.87"/>
      <rect x="134.8" y="256" width="64.39" height="11.87"/>
      <rect x="134.8" y="140.93" width="64.39" height="11.87"/>
      <rect x="134.8" y="233.17" width="64.39" height="11.87"/>
      <rect x="134.8" y="187.05" width="64.39" height="11.87"/>
      <rect x="134.8" y="210.34" width="64.39" height="11.87"/>
      <rect x="320.19" y="371.08" width="64.39" height="11.87"/>
      <rect x="320.19" y="324.95" width="64.39" height="11.87"/>
      <rect x="320.19" y="348.24" width="64.39" height="11.87"/>
      <rect x="320.19" y="279.29" width="64.39" height="11.87"/>
      <rect x="320.19" y="302.12" width="64.39" height="11.87"/>
      <rect x="320.19" y="393.91" width="64.39" height="11.87"/>
      <rect x="320.19" y="164.22" width="64.39" height="11.87"/>
      <rect x="320.19" y="118.1" width="64.39" height="11.87"/>
      <rect x="320.19" y="187.05" width="64.39" height="11.87"/>
      <rect x="320.19" y="210.34" width="64.39" height="11.87"/>
      <rect x="320.19" y="256" width="64.39" height="11.87"/>
      <rect x="320.19" y="233.17" width="64.39" height="11.87"/>
    </g>
    <path fill="rgba(255,255,255,0.7)" d="M426.59,95.27h13.7v-19.18h-173.52v19.18h11.42c19.18,0,22.83,3.65,22.83,22.83V248.24h-82.65V118.1c0-19.18,3.65-22.83,22.83-22.83h11.42v-19.18H79.09v19.18h13.7c19.18,0,22.83,3.65,22.83,22.83V406.24c0,19.18-3.65,22.83-22.83,22.83h-13.7v19.18H252.61v-19.18h-11.42c-19.18,0-22.83-3.65-22.83-22.83v-138.82h82.65v138.82c0,19.18-3.65,22.83-22.83,22.83h-11.42v19.18h173.52v-19.18h-13.7c-19.18,0-22.83-3.65-22.83-22.83V118.1c0-19.18,3.65-22.83,22.83-22.83Z"/>
    <path fill="rgba(255,255,255,0.9)" d="M426.59,101.36h19.79v-31.36h-183.7v31.36h15.5c15.8,0,16.74,.94,16.74,16.74v124.05h-70.47V118.1c0-15.8,.94-16.74,16.74-16.74h15.5v-31.36H73v31.36h19.79c15.8,0,16.74,.94,16.74,16.74V406.24c0,15.8-.94,16.74-16.74,16.74h-19.79v31.35h183.7v-31.35h-15.5c-15.8,0-16.74-.94-16.74-16.74v-132.73h70.47v132.73c0,15.8,.94,16.74,16.74,16.74h-15.5v31.35h183.7v-31.35h-19.79c-15.8,0-16.74-.94-16.74-16.74V118.1c0-15.8,.94-16.74,16.74-16.74Z"/>
  </svg>
);

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { supabase } = useAuth();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const from = location.state?.from?.pathname || '/dashboard';

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (!supabase) {
        throw new Error('Authentication service not configured. Please contact administrator.');
      }

      const { data, error: loginError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (loginError) throw loginError;

      if (data?.session) {
        navigate(from, { replace: true });
      }
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: COLORS.bg,
      padding: '1rem',
    }}>
      <div style={{
        width: '100%',
        maxWidth: 420,
        borderRadius: 16,
        overflow: 'hidden',
        boxShadow: '0 4px 20px rgba(42, 52, 65, 0.15)',
      }}>
        {/* Green Header */}
        <div style={{
          background: COLORS.grassGreen,
          padding: '1.25rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
        }}>
          <div style={{ width: 40, height: 40 }}>
            <HLogo />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{
              fontFamily: "'Ubuntu Mono', monospace",
              fontSize: '1.4rem',
              fontWeight: 700,
              color: COLORS.white,
            }}>XLR8</span>
            <Rocket size={18} color="white" style={{ opacity: 0.9 }} />
            <span style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '1.1rem',
              fontWeight: 300,
              color: 'rgba(255,255,255,0.9)',
            }}>Analysis Platform</span>
          </div>
        </div>

        {/* White Form Area */}
        <div style={{
          background: COLORS.white,
          padding: '2rem',
        }}>
          {error && (
            <div style={{
              background: '#fef2f2',
              border: '1px solid #fecaca',
              color: COLORS.red,
              padding: '0.75rem 1rem',
              borderRadius: 8,
              fontSize: '0.875rem',
              textAlign: 'center',
              marginBottom: '1.25rem',
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{
                display: 'block',
                fontSize: '0.85rem',
                fontWeight: 500,
                color: COLORS.text,
                marginBottom: '0.5rem',
              }}>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  fontSize: '1rem',
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: 8,
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                fontSize: '0.85rem',
                fontWeight: 500,
                color: COLORS.text,
                marginBottom: '0.5rem',
              }}>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  fontSize: '1rem',
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: 8,
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.875rem',
                fontSize: '1rem',
                fontWeight: 600,
                color: COLORS.white,
                background: COLORS.grassGreen,
                border: `2px solid ${COLORS.grassGreen}`,
                borderRadius: 8,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
                transition: 'all 0.2s ease',
              }}
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div style={{
            marginTop: '1.5rem',
            textAlign: 'center',
            fontSize: '0.85rem',
            color: COLORS.textLight,
          }}>
            <p style={{ margin: '0 0 0.5rem 0' }}>Need help? Contact your administrator.</p>
            <a 
              href="/" 
              style={{
                color: COLORS.grassGreen,
                textDecoration: 'none',
                fontWeight: 600,
              }}
            >
              ← Back to Home
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
