/**
 * BeatLabWelcome_Jeremy.jsx - BEAT LABORATORY Welcome Film
 * 
 * "Welcome to the BEAT LABORATORY"
 * For: Jeremy Lamar Howard
 * 
 * Cinematic. Hard-hitting. Legendary entrance.
 * 
 * December 27, 2025
 */

import React, { useState, useEffect } from 'react';

const COLORS = {
  black: '#0a0a0a',
  white: '#ffffff',
  neonPink: '#ff2d92',
  electricBlue: '#00d4ff',
  purple: '#8b5cf6',
  gold: '#fbbf24',
  deepPurple: '#1a0a2e',
  fire: '#ff4500',
};

// Each scene in the welcome video
const SCENES = [
  // COLD OPEN - STATIC/INTERFERENCE
  { 
    duration: 1500,
    bg: COLORS.black,
    content: (
      <div style={{ 
        fontSize: '0.8rem', 
        letterSpacing: '0.4em', 
        textTransform: 'uppercase',
        opacity: 0.3,
        fontFamily: "'Courier New', monospace"
      }}>
        [ SIGNAL DETECTED ]
      </div>
    )
  },
  
  // THE SETUP
  { 
    duration: 2000,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '1.2rem', opacity: 0.5, fontWeight: 300, letterSpacing: '0.1em' }}>
        Somewhere in the cosmos of sound...
      </div>
    )
  },
  { 
    duration: 1800,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '1.2rem', opacity: 0.5, fontWeight: 300, letterSpacing: '0.1em' }}>
        A new force approaches.
      </div>
    )
  },
  
  // THE QUESTION
  { 
    duration: 800,
    bg: COLORS.black,
    content: null
  },
  { 
    duration: 2000,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '3rem', fontWeight: 900, letterSpacing: '-0.02em' }}>
        WHO'S THAT?
      </div>
    )
  },
  
  // THE BUILDUP
  { 
    duration: 1500,
    bg: COLORS.deepPurple,
    content: (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '0.5rem', 
        textAlign: 'center' 
      }}>
        <div style={{ fontSize: '1rem', opacity: 0.6, letterSpacing: '0.3em', textTransform: 'uppercase' }}>
          INCOMING TRANSMISSION
        </div>
        <div style={{ 
          fontSize: '4rem', 
          fontWeight: 200,
          fontFamily: "'Courier New', monospace",
          color: COLORS.electricBlue
        }}>
          ▓▓▓░░░░░░░
        </div>
      </div>
    )
  },
  { 
    duration: 1200,
    bg: COLORS.deepPurple,
    content: (
      <div style={{ 
        fontSize: '4rem', 
        fontWeight: 200,
        fontFamily: "'Courier New', monospace",
        color: COLORS.electricBlue
      }}>
        ▓▓▓▓▓▓░░░░
      </div>
    )
  },
  { 
    duration: 1000,
    bg: COLORS.deepPurple,
    content: (
      <div style={{ 
        fontSize: '4rem', 
        fontWeight: 200,
        fontFamily: "'Courier New', monospace",
        color: COLORS.neonPink
      }}>
        ▓▓▓▓▓▓▓▓▓▓
      </div>
    )
  },
  
  // THE NAME DROP - EPIC
  { 
    duration: 500,
    bg: COLORS.neonPink,
    content: null
  },
  { 
    duration: 600,
    bg: COLORS.black,
    content: null
  },
  { 
    duration: 500,
    bg: COLORS.electricBlue,
    content: null
  },
  { 
    duration: 3500,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
        <div style={{ 
          fontSize: '1rem', 
          letterSpacing: '0.5em', 
          textTransform: 'uppercase',
          opacity: 0.5 
        }}>
          WE WELCOME......
        </div>
        <div style={{ 
          fontSize: '5rem', 
          fontWeight: 900, 
          letterSpacing: '-0.02em',
          background: `linear-gradient(135deg, ${COLORS.neonPink}, ${COLORS.electricBlue}, ${COLORS.purple})`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          textShadow: `0 0 80px ${COLORS.neonPink}40`,
        }}>
          JEREMY
        </div>
      </div>
    )
  },
  { 
    duration: 2500,
    bg: COLORS.black,
    content: (
      <div style={{ 
        fontSize: '4rem', 
        fontWeight: 900, 
        letterSpacing: '0.05em',
        background: `linear-gradient(135deg, ${COLORS.electricBlue}, ${COLORS.purple})`,
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
      }}>
        LAMAR
      </div>
    )
  },
  { 
    duration: 3000,
    bg: COLORS.black,
    content: (
      <div style={{ 
        fontSize: '5rem', 
        fontWeight: 900, 
        letterSpacing: '0.02em',
        color: COLORS.gold,
        textShadow: `0 0 60px ${COLORS.gold}50`,
      }}>
        HOWARD
      </div>
    )
  },
  
  // THE HYPE
  { 
    duration: 800,
    bg: COLORS.black,
    content: null
  },
  { 
    duration: 1800,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', textAlign: 'center' }}>
        <div style={{ fontSize: '1.5rem', opacity: 0.6 }}>The one.</div>
      </div>
    )
  },
  { 
    duration: 1800,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', textAlign: 'center' }}>
        <div style={{ fontSize: '1.5rem', opacity: 0.6 }}>The only.</div>
      </div>
    )
  },
  { 
    duration: 2500,
    bg: COLORS.black,
    content: (
      <div style={{ 
        fontSize: '3.5rem', 
        fontWeight: 900,
        color: COLORS.gold
      }}>
        THE LEGEND.
      </div>
    )
  },
  
  // THE WELCOME
  { 
    duration: 600,
    bg: COLORS.purple,
    content: null
  },
  { 
    duration: 2500,
    bg: COLORS.black,
    content: (
      <div style={{ 
        fontSize: '1.2rem', 
        letterSpacing: '0.4em', 
        textTransform: 'uppercase',
        opacity: 0.6
      }}>
        NOW ENTERING
      </div>
    )
  },
  
  // THE LABORATORY REVEAL
  { 
    duration: 500,
    bg: COLORS.neonPink,
    content: null
  },
  { 
    duration: 4000,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
        <div style={{ 
          fontSize: '1.5rem', 
          letterSpacing: '0.3em', 
          textTransform: 'uppercase',
          opacity: 0.4
        }}>
          THE
        </div>
        <div style={{ 
          fontSize: '6rem', 
          fontWeight: 900, 
          letterSpacing: '0.05em',
          background: `linear-gradient(180deg, ${COLORS.white}, ${COLORS.electricBlue})`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          BEAT
        </div>
        <div style={{ 
          fontSize: '4rem', 
          fontWeight: 900, 
          letterSpacing: '0.15em',
          color: COLORS.neonPink,
          textShadow: `0 0 40px ${COLORS.neonPink}60`,
        }}>
          LABORATORY
        </div>
      </div>
    )
  },
  
  // THE ENERGY
  { 
    duration: 2000,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '3rem', fontWeight: 900 }}>
        NO LIMITS.
      </div>
    )
  },
  { 
    duration: 2000,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '3rem', fontWeight: 900 }}>
        NO BOUNDARIES.
      </div>
    )
  },
  { 
    duration: 2500,
    bg: COLORS.black,
    content: (
      <div style={{ 
        fontSize: '3.5rem', 
        fontWeight: 900,
        color: COLORS.neonPink,
        textShadow: `0 0 30px ${COLORS.neonPink}50`
      }}>
        JUST HEAT. 🔥
      </div>
    )
  },
  
  // THE PERSONAL TOUCH
  { 
    duration: 800,
    bg: COLORS.black,
    content: null
  },
  { 
    duration: 3000,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', textAlign: 'center' }}>
        <div style={{ fontSize: '1.5rem', fontWeight: 300, opacity: 0.7 }}>
          Jeremy Lamar Howard
        </div>
        <div style={{ fontSize: '2.5rem', fontWeight: 800, color: COLORS.electricBlue }}>
          THE LAB IS OURS.
        </div>
      </div>
    )
  },
  
  // THE CLOSE
  { 
    duration: 600,
    bg: COLORS.electricBlue,
    content: null
  },
  { 
    duration: 600,
    bg: COLORS.neonPink,
    content: null
  },
  { 
    duration: 600,
    bg: COLORS.purple,
    content: null
  },
  { 
    duration: 5000,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2rem' }}>
        <div style={{ 
          fontSize: '2.5rem', 
          fontWeight: 900,
          letterSpacing: '0.1em',
          background: `linear-gradient(135deg, ${COLORS.neonPink}, ${COLORS.electricBlue}, ${COLORS.gold})`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          WELCOME TO THE LAB
        </div>
        <div style={{ 
          fontSize: '5rem', 
          fontWeight: 900,
          letterSpacing: '0.05em',
          color: COLORS.white
        }}>
          JEREMY
        </div>
        <div style={{ 
          marginTop: '1rem',
          fontSize: '1.2rem',
          letterSpacing: '0.3em',
          opacity: 0.5,
          textTransform: 'uppercase'
        }}>
          BEAT LABORATORY • EST. 2025
        </div>
      </div>
    )
  },
];

export default function BeatLabWelcome_Jeremy() {
  const [currentScene, setCurrentScene] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [fadeIn, setFadeIn] = useState(true);

  useEffect(() => {
    if (!isPlaying) return;
    
    const scene = SCENES[currentScene];
    
    // Fade in
    setFadeIn(true);
    
    // After duration, fade out and move to next
    const timer = setTimeout(() => {
      setFadeIn(false);
      
      // Small delay for fade out, then next scene
      setTimeout(() => {
        if (currentScene < SCENES.length - 1) {
          setCurrentScene(prev => prev + 1);
        } else {
          setIsPlaying(false);
        }
      }, 200);
      
    }, scene.duration - 200);
    
    return () => clearTimeout(timer);
  }, [currentScene, isPlaying]);

  const startVideo = () => {
    setCurrentScene(0);
    setIsPlaying(true);
  };

  const scene = SCENES[currentScene];

  return (
    <div style={{
      width: '100%',
      height: '100vh',
      background: scene?.bg || COLORS.black,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: "'Inter', 'Sora', system-ui, sans-serif",
      color: COLORS.white,
      transition: 'background 0.3s ease',
      position: 'relative',
      overflow: 'hidden',
    }}>
      
      {/* Ambient glow effect */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '150%',
        height: '150%',
        background: `radial-gradient(circle, ${COLORS.purple}15 0%, transparent 60%)`,
        pointerEvents: 'none',
      }} />
      
      {/* Progress bar */}
      {isPlaying && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background: 'rgba(255,255,255,0.1)',
        }}>
          <div style={{
            height: '100%',
            width: `${((currentScene + 1) / SCENES.length) * 100}%`,
            background: `linear-gradient(90deg, ${COLORS.neonPink}, ${COLORS.electricBlue})`,
            transition: 'width 0.3s ease',
          }} />
        </div>
      )}
      
      {/* Content */}
      {!isPlaying ? (
        <div style={{ textAlign: 'center', zIndex: 1 }}>
          <div style={{ 
            fontSize: '1rem', 
            letterSpacing: '0.4em',
            textTransform: 'uppercase',
            opacity: 0.4,
            marginBottom: '1rem',
          }}>
            FROM THE MINDS AT HCMPACT
          </div>
          <div style={{ 
            fontSize: '3rem', 
            fontWeight: 900, 
            marginBottom: '0.5rem',
            background: `linear-gradient(135deg, ${COLORS.neonPink}, ${COLORS.electricBlue})`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            WELCOME VIDEO
          </div>
          <div style={{ 
            fontSize: '1.8rem', 
            fontWeight: 300,
            opacity: 0.7, 
            marginBottom: '3rem',
          }}>
            Jeremy Lamar Howard
          </div>
          <button
            onClick={startVideo}
            style={{
              padding: '1.25rem 3rem',
              fontSize: '1rem',
              fontWeight: 700,
              letterSpacing: '0.15em',
              textTransform: 'uppercase',
              background: `linear-gradient(135deg, ${COLORS.neonPink}, ${COLORS.purple})`,
              color: COLORS.white,
              border: 'none',
              borderRadius: 8,
              cursor: 'pointer',
              transition: 'transform 0.2s ease, box-shadow 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.target.style.transform = 'scale(1.05)';
              e.target.style.boxShadow = `0 0 40px ${COLORS.neonPink}50`;
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'scale(1)';
              e.target.style.boxShadow = 'none';
            }}
          >
            ▶ PLAY
          </button>
          <div style={{ 
            marginTop: '2rem', 
            fontSize: '0.8rem', 
            opacity: 0.3 
          }}>
            ~55 seconds
          </div>
        </div>
      ) : (
        <div style={{
          opacity: fadeIn ? 1 : 0,
          transform: fadeIn ? 'scale(1)' : 'scale(0.98)',
          transition: 'opacity 0.3s ease, transform 0.3s ease',
          padding: '2rem',
          textAlign: 'center',
          zIndex: 1,
        }}>
          {scene?.content}
        </div>
      )}
      
      {/* Skip button when playing */}
      {isPlaying && (
        <button
          onClick={() => setIsPlaying(false)}
          style={{
            position: 'absolute',
            bottom: '2rem',
            right: '2rem',
            padding: '0.5rem 1rem',
            fontSize: '0.8rem',
            background: 'rgba(255,255,255,0.1)',
            border: '1px solid rgba(255,255,255,0.2)',
            color: 'rgba(255,255,255,0.5)',
            borderRadius: 4,
            cursor: 'pointer',
            zIndex: 2,
          }}
        >
          Skip →
        </button>
      )}
      
      {/* Replay button at end */}
      {!isPlaying && currentScene === SCENES.length - 1 && (
        <button
          onClick={startVideo}
          style={{
            position: 'absolute',
            bottom: '2rem',
            padding: '0.75rem 1.5rem',
            fontSize: '0.9rem',
            background: 'transparent',
            border: `1px solid ${COLORS.neonPink}`,
            color: COLORS.neonPink,
            borderRadius: 6,
            cursor: 'pointer',
            zIndex: 2,
          }}
        >
          ↺ Replay
        </button>
      )}
    </div>
  );
}
