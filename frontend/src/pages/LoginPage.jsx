/**
 * LoginPage - Authentication with Landing-style header
 */

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Rocket } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const COLORS = {
  grassGreen: '#83b16d',
  grassGreenDark: '#6a9958',
  text: '#2a3441',
  textLight: '#5f6c7b',
  border: '#e1e8ed',
  bg: '#f6f5fa',
  white: '#ffffff',
  red: '#e74c3c',
};

// H Logo matching Landing page
const HLogoWhite = () => (
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

  const styles = {
    container: {
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: COLORS.bg,
    },
    header: {
      background: COLORS.grassGreen,
      padding: '1.5rem 2rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '1rem',
    },
    logoContainer: {
      width: '48px',
      height: '48px',
    },
    headerText: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    headerTitle: {
      fontFamily: "'Ubuntu Mono', monospace",
      fontSize: '1.5rem',
      fontWeight: '700',
      color: COLORS.white,
    },
    headerSub: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.25rem',
      fontWeight: '300',
      color: 'rgba(255,255,255,0.9)',
    },
    content: {
      flex: 1,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
    },
    card: {
      background: COLORS.white,
      borderRadius: 16,
      boxShadow: '0 4px 20px rgba(42, 52, 65, 0.1)',
      width: '100%',
      maxWidth: 400,
      padding: '2.5rem',
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.5rem',
      fontWeight: 600,
      color: COLORS.text,
      textAlign: 'center',
      marginBottom: '1.5rem',
    },
    form: {
      display: 'flex',
      flexDirection: 'column',
      gap: '1rem',
    },
    inputGroup: {
      display: 'flex',
      flexDirection: 'column',
      gap: '0.375rem',
    },
    label: {
      fontSize: '0.8rem',
      fontWeight: 600,
      color: COLORS.textLight,
    },
    input: {
      padding: '0.75rem 1rem',
      fontSize: '1rem',
      border: `1px solid ${COLORS.border}`,
      borderRadius: 8,
      outline: 'none',
      transition: 'border-color 0.2s ease',
    },
    button: {
      padding: '0.875rem',
      fontSize: '1rem',
      fontWeight: 600,
      color: COLORS.white,
      background: COLORS.grassGreen,
      border: 'none',
      borderRadius: 8,
      cursor: 'pointer',
      marginTop: '0.5rem',
      transition: 'background 0.2s ease',
    },
    buttonDisabled: {
      opacity: 0.6,
      cursor: 'not-allowed',
    },
    error: {
      background: '#fef2f2',
      border: '1px solid #fecaca',
      color: COLORS.red,
      padding: '0.75rem 1rem',
      borderRadius: 8,
      fontSize: '0.875rem',
      textAlign: 'center',
      marginBottom: '1rem',
    },
    footer: {
      marginTop: '1.5rem',
      textAlign: 'center',
      fontSize: '0.8rem',
      color: COLORS.textLight,
    },
    backLink: {
      color: COLORS.grassGreen,
      textDecoration: 'none',
      fontWeight: 600,
    },
  };

  return (
    <div style={styles.container}>
      {/* Header matching Landing page */}
      <div style={styles.header}>
        <div style={styles.logoContainer}>
          <HLogoWhite />
        </div>
        <div style={styles.headerText}>
          <span style={styles.headerTitle}>XLR8</span>
          <Rocket size={20} color="white" />
          <span style={styles.headerSub}>Analysis Platform</span>
        </div>
      </div>

      {/* Login Form */}
      <div style={styles.content}>
        <div style={styles.card}>
          <h1 style={styles.title}>Sign In</h1>

          {error && <div style={styles.error}>{error}</div>}

          <form style={styles.form} onSubmit={handleLogin}>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                style={styles.input}
              />
            </div>

            <div style={styles.inputGroup}>
              <label style={styles.label}>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={styles.input}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                ...styles.button,
                ...(loading ? styles.buttonDisabled : {}),
              }}
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div style={styles.footer}>
            <p>Need help? Contact your administrator.</p>
            <a href="/" style={styles.backLink}>← Back to Home</a>
          </div>
        </div>
      </div>
    </div>
  );
}
