/**
 * AI Assist - Chat Interface with Bessie
 * 
 * Clean professional design with:
 * - Light/dark mode support
 * - Customer color accents
 * - Consistent styling with Command Center
 */

import React from 'react';
import { useProject } from '../context/ProjectContext';
import { useTheme } from '../context/ThemeContext';
import { getCustomerColorPalette } from '../utils/customerColors';
import Chat from '../components/Chat';
import { MessageSquare, FolderOpen } from 'lucide-react';

// Theme-aware colors (Mission Control palette)
const getColors = (dark) => ({
  bg: dark ? '#1a1f2e' : '#f0f2f5',
  card: dark ? '#242b3d' : '#ffffff',
  cardBorder: dark ? '#2d3548' : '#e2e8f0',
  text: dark ? '#e8eaed' : '#1a2332',
  textMuted: dark ? '#8b95a5' : '#64748b',
  textLight: dark ? '#5f6a7d' : '#94a3b8',
  primary: '#83b16d',  // Mission Control green
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.1)',
});

// No-project placeholder
function SelectProjectPrompt({ colors }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '50vh',
      textAlign: 'center',
      padding: '2rem',
    }}>
      <div style={{
        width: 64,
        height: 64,
        borderRadius: 16,
        background: colors.primaryLight,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: '1.25rem',
      }}>
        <FolderOpen size={28} style={{ color: colors.primary }} />
      </div>
      <h2 style={{
        fontFamily: "'Sora', sans-serif",
        fontSize: '1.25rem',
        fontWeight: 700,
        color: colors.text,
        margin: '0 0 0.5rem 0',
      }}>
        Select a Project to Begin
      </h2>
      <p style={{
        color: colors.textMuted,
        fontSize: '0.85rem',
        maxWidth: '350px',
        lineHeight: 1.5,
        margin: 0,
      }}>
        Choose a project from the selector above to start chatting with AI Assist.
      </p>
    </div>
  );
}

export default function WorkspacePage() {
  const { activeProject, projectName, customerName, hasActiveProject, loading } = useProject();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);
  
  // Get customer colors if project is active
  const customerColors = hasActiveProject 
    ? getCustomerColorPalette(customerName || projectName)
    : null;

  if (loading) {
    return (
      <div style={{ 
        padding: '1.5rem', 
        background: colors.bg, 
        minHeight: 'calc(100vh - 60px)',
        fontFamily: "'Inter', system-ui, sans-serif",
        transition: 'background 0.2s ease',
        textAlign: 'center',
        color: colors.textMuted,
      }}>
        Loading...
      </div>
    );
  }

  return (
    <div style={{ 
      padding: '1.5rem', 
      background: colors.bg, 
      minHeight: 'calc(100vh - 60px)',
      fontFamily: "'Inter', system-ui, sans-serif",
      transition: 'background 0.2s ease',
    }}>
      {/* Header */}
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{
          fontFamily: "'Sora', sans-serif",
          fontSize: '1.5rem',
          fontWeight: 700,
          color: colors.text,
          margin: 0,
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
        }}>
          <MessageSquare size={24} style={{ color: colors.primary }} />
          AI Assist
          {hasActiveProject && customerColors && (
            <span style={{
              fontSize: '0.85rem',
              fontWeight: 500,
              color: customerColors.primary,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}>
              <span style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: customerColors.primary,
              }} />
              {customerName ? `${customerName} • ` : ''}{projectName || 'Project'}
            </span>
          )}
        </h1>
        {!hasActiveProject && (
          <p style={{ color: colors.textMuted, margin: '0.25rem 0 0 0', fontSize: '0.85rem' }}>
            Chat with your data and get intelligent insights
          </p>
        )}
      </div>

      {/* Chat Container */}
      <div style={{
        background: colors.card,
        border: `1px solid ${colors.cardBorder}`,
        borderRadius: 12,
        overflow: 'hidden',
        minHeight: '60vh',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
      }}>
        {hasActiveProject ? (
          <Chat />
        ) : (
          <SelectProjectPrompt colors={colors} />
        )}
      </div>
    </div>
  );
}
