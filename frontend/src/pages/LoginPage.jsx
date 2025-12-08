/**
 * LoginPage - Authentication with TOTP and SMS MFA support
 * 
 * Supports:
 * - Email/Password login
 * - TOTP (Authenticator app) MFA
 * - SMS (Text message) MFA
 */

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const COLORS = {
  grassGreen: '#83b16d',
  text: '#2a3441',
  textLight: '#5f6c7b',
  border: '#e1e8ed',
  bg: '#f6f5fa',
  white: '#ffffff',
  red: '#e74c3c',
  blue: '#3b82f6',
};

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, supabase } = useAuth();
  
  // Form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  
  // MFA state
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaMethod, setMfaMethod] = useState(null); // 'totp' or 'sms'
  const [mfaFactorId, setMfaFactorId] = useState(null);
  const [mfaChallengeId, setMfaChallengeId] = useState(null);
  const [smsSent, setSmsSent] = useState(false);
  const [phoneLastFour, setPhoneLastFour] = useState('');
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const from = location.state?.from?.pathname || '/dashboard';

  // Initial login attempt
  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Attempt password login
      const { data, error: loginError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (loginError) throw loginError;

      // Check if MFA is required
      if (data?.session) {
        // No MFA required, login successful
        navigate(from, { replace: true });
      } else if (data?.mfa) {
        // MFA required - check available factors
        const factors = data.mfa.factors || [];
        
        if (factors.length === 0) {
          throw new Error('MFA required but no factors enrolled');
        }

        // Find preferred factor (TOTP first, then phone)
        const totpFactor = factors.find(f => f.factor_type === 'totp');
        const phoneFactor = factors.find(f => f.factor_type === 'phone');
        
        if (totpFactor) {
          setMfaMethod('totp');
          setMfaFactorId(totpFactor.id);
          // Create challenge for TOTP
          const { data: challenge } = await supabase.auth.mfa.challenge({
            factorId: totpFactor.id,
          });
          setMfaChallengeId(challenge?.id);
        } else if (phoneFactor) {
          setMfaMethod('sms');
          setMfaFactorId(phoneFactor.id);
          setPhoneLastFour(phoneFactor.phone?.slice(-4) || '****');
        }
        
        setMfaRequired(true);
      }
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  // Send SMS code
  const handleSendSms = async () => {
    setError(null);
    setLoading(true);

    try {
      const { data: challenge, error: challengeError } = await supabase.auth.mfa.challenge({
        factorId: mfaFactorId,
      });

      if (challengeError) throw challengeError;

      setMfaChallengeId(challenge.id);
      setSmsSent(true);
    } catch (err) {
      console.error('SMS send error:', err);
      setError(err.message || 'Failed to send SMS code');
    } finally {
      setLoading(false);
    }
  };

  // Verify MFA code (TOTP or SMS)
  const handleVerifyMfa = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const { data, error: verifyError } = await supabase.auth.mfa.verify({
        factorId: mfaFactorId,
        challengeId: mfaChallengeId,
        code: mfaCode,
      });

      if (verifyError) throw verifyError;

      // MFA verified, login successful
      navigate(from, { replace: true });
    } catch (err) {
      console.error('MFA verify error:', err);
      setError(err.message || 'Invalid code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Reset to login screen
  const handleBack = () => {
    setMfaRequired(false);
    setMfaMethod(null);
    setMfaCode('');
    setSmsSent(false);
    setError(null);
  };

  const styles = {
    container: {
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: COLORS.bg,
      padding: '1rem',
    },
    card: {
      background: COLORS.white,
      borderRadius: 16,
      boxShadow: '0 4px 20px rgba(42, 52, 65, 0.1)',
      width: '100%',
      maxWidth: 400,
      padding: '2.5rem',
    },
    logo: {
      textAlign: 'center',
      marginBottom: '2rem',
    },
    logoText: {
      fontFamily: "'Ubuntu Mono', monospace",
      fontSize: '2rem',
      fontWeight: 700,
      color: COLORS.text,
    },
    logoSub: {
      fontSize: '0.875rem',
      color: COLORS.textLight,
      marginTop: '0.25rem',
    },
    title: {
      fontFamily: "'Sora', sans-serif",
      fontSize: '1.25rem',
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
      transition: 'opacity 0.2s ease',
    },
    buttonSecondary: {
      padding: '0.875rem',
      fontSize: '1rem',
      fontWeight: 600,
      color: COLORS.grassGreen,
      background: 'transparent',
      border: `2px solid ${COLORS.grassGreen}`,
      borderRadius: 8,
      cursor: 'pointer',
      transition: 'all 0.2s ease',
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
    info: {
      background: '#f0f9ff',
      border: '1px solid #bae6fd',
      color: '#0369a1',
      padding: '0.75rem 1rem',
      borderRadius: 8,
      fontSize: '0.875rem',
      textAlign: 'center',
      marginBottom: '1rem',
    },
    success: {
      background: '#f0fdf4',
      border: '1px solid #86efac',
      color: '#166534',
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
    link: {
      color: COLORS.grassGreen,
      textDecoration: 'none',
      fontWeight: 600,
      background: 'none',
      border: 'none',
      cursor: 'pointer',
    },
    mfaIcon: {
      fontSize: '3rem',
      textAlign: 'center',
      marginBottom: '1rem',
    },
    codeInput: {
      textAlign: 'center',
      letterSpacing: '0.5em',
      fontSize: '1.5rem',
      padding: '1rem',
    },
  };

  // ========== RENDER: MFA REQUIRED ==========
  if (mfaRequired) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.logo}>
            <div style={styles.logoText}>🚀 XLR8</div>
            <div style={styles.logoSub}>UKG Implementation Platform</div>
          </div>

          {/* TOTP MFA */}
          {mfaMethod === 'totp' && (
            <>
              <div style={styles.mfaIcon}>🔐</div>
              <h1 style={styles.title}>Enter Authenticator Code</h1>
              
              {error && <div style={styles.error}>{error}</div>}
              
              <div style={styles.info}>
                Open your authenticator app and enter the 6-digit code
              </div>

              <form style={styles.form} onSubmit={handleVerifyMfa}>
                <div style={styles.inputGroup}>
                  <input
                    type="text"
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    required
                    maxLength={6}
                    style={{ ...styles.input, ...styles.codeInput }}
                    autoFocus
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || mfaCode.length !== 6}
                  style={{
                    ...styles.button,
                    ...(loading || mfaCode.length !== 6 ? styles.buttonDisabled : {}),
                  }}
                >
                  {loading ? 'Verifying...' : 'Verify Code'}
                </button>
              </form>
            </>
          )}

          {/* SMS MFA */}
          {mfaMethod === 'sms' && (
            <>
              <div style={styles.mfaIcon}>📱</div>
              <h1 style={styles.title}>SMS Verification</h1>
              
              {error && <div style={styles.error}>{error}</div>}
              
              {!smsSent ? (
                <>
                  <div style={styles.info}>
                    We'll send a verification code to your phone ending in <strong>...{phoneLastFour}</strong>
                  </div>

                  <button
                    onClick={handleSendSms}
                    disabled={loading}
                    style={{
                      ...styles.button,
                      ...(loading ? styles.buttonDisabled : {}),
                    }}
                  >
                    {loading ? 'Sending...' : 'Send Code via SMS'}
                  </button>
                </>
              ) : (
                <>
                  <div style={styles.success}>
                    ✓ Code sent to ...{phoneLastFour}
                  </div>

                  <form style={styles.form} onSubmit={handleVerifyMfa}>
                    <div style={styles.inputGroup}>
                      <label style={styles.label}>Enter the 6-digit code</label>
                      <input
                        type="text"
                        value={mfaCode}
                        onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                        placeholder="000000"
                        required
                        maxLength={6}
                        style={{ ...styles.input, ...styles.codeInput }}
                        autoFocus
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={loading || mfaCode.length !== 6}
                      style={{
                        ...styles.button,
                        ...(loading || mfaCode.length !== 6 ? styles.buttonDisabled : {}),
                      }}
                    >
                      {loading ? 'Verifying...' : 'Verify Code'}
                    </button>

                    <button
                      type="button"
                      onClick={handleSendSms}
                      disabled={loading}
                      style={{
                        ...styles.buttonSecondary,
                        ...(loading ? styles.buttonDisabled : {}),
                      }}
                    >
                      Resend Code
                    </button>
                  </form>
                </>
              )}
            </>
          )}

          <div style={styles.footer}>
            <button onClick={handleBack} style={styles.link}>
              ← Back to login
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ========== RENDER: LOGIN FORM ==========
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.logo}>
          <div style={styles.logoText}>🚀 XLR8</div>
          <div style={styles.logoSub}>UKG Implementation Platform</div>
        </div>

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
        </div>
      </div>
    </div>
  );
}
