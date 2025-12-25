/**
 * HypeVideo.jsx - XLR8 Cinematic Brand Film
 * 
 * "It's a Rolly not a Stop Watch"
 * Nike energy. Premium. Relentless.
 * 
 * December 25, 2025
 */

import React, { useState, useEffect } from 'react';

const COLORS = {
  black: '#0a0a0a',
  white: '#ffffff',
  primary: '#83b16d',
  accent: '#285390',
  purple: '#5f4282',
  scarlet: '#993c44',
  gold: '#d4af37',
};

// Each scene in the hype video
const SCENES = [
  // COLD OPEN
  { 
    duration: 2000,
    bg: COLORS.black,
    content: (
      <div style={{ opacity: 0.4, fontSize: '0.9rem', letterSpacing: '0.3em', textTransform: 'uppercase' }}>
        HCMPACT Presents
      </div>
    )
  },
  
  // THE PROBLEM - RAPID FIRE
  { 
    duration: 1500,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '4rem', fontWeight: 900, letterSpacing: '-0.03em' }}>
        WHERE DID IT GO?
      </div>
    )
  },
  { 
    duration: 1200,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '1.5rem', opacity: 0.6, fontWeight: 300 }}>
        The decision from last quarter.
      </div>
    )
  },
  { 
    duration: 1200,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '1.5rem', opacity: 0.6, fontWeight: 300 }}>
        The exception that was approved.
      </div>
    )
  },
  { 
    duration: 1200,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '1.5rem', opacity: 0.6, fontWeight: 300 }}>
        The reason behind the configuration.
      </div>
    )
  },
  { 
    duration: 2000,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '3.5rem', fontWeight: 900, color: COLORS.scarlet }}>
        GONE.
      </div>
    )
  },
  
  // THE PAIN
  { 
    duration: 1800,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', textAlign: 'center' }}>
        <div style={{ fontSize: '1.2rem', opacity: 0.5, letterSpacing: '0.2em', textTransform: 'uppercase' }}>Buried in</div>
        <div style={{ fontSize: '3rem', fontWeight: 800 }}>SLACK THREADS</div>
      </div>
    )
  },
  { 
    duration: 1800,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', textAlign: 'center' }}>
        <div style={{ fontSize: '1.2rem', opacity: 0.5, letterSpacing: '0.2em', textTransform: 'uppercase' }}>Trapped in</div>
        <div style={{ fontSize: '3rem', fontWeight: 800 }}>PEOPLE'S HEADS</div>
      </div>
    )
  },
  { 
    duration: 1800,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', textAlign: 'center' }}>
        <div style={{ fontSize: '1.2rem', opacity: 0.5, letterSpacing: '0.2em', textTransform: 'uppercase' }}>Lost in</div>
        <div style={{ fontSize: '3rem', fontWeight: 800 }}>VERSION 47.FINAL.FINAL2.xlsx</div>
      </div>
    )
  },
  
  // THE TURN
  { 
    duration: 800,
    bg: COLORS.black,
    content: null
  },
  { 
    duration: 2500,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '5rem', fontWeight: 900, letterSpacing: '-0.02em' }}>
        UNTIL NOW.
      </div>
    )
  },
  
  // THE REVEAL
  { 
    duration: 800,
    bg: COLORS.primary,
    content: null
  },
  { 
    duration: 3000,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
        <div style={{ 
          fontSize: '7rem', 
          fontWeight: 900, 
          fontFamily: "'Ubuntu Mono', monospace",
          letterSpacing: '0.1em',
          background: `linear-gradient(135deg, ${COLORS.primary}, ${COLORS.gold})`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          XLR8
        </div>
        <div style={{ 
          fontSize: '1.5rem', 
          fontWeight: 600,
          letterSpacing: '0.15em',
          opacity: 0.9,
          fontStyle: 'italic'
        }}>
          Context That Compounds
        </div>
      </div>
    )
  },
  
  // FIVE TRUTHS - RAPID BUILD
  { 
    duration: 1500,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '1rem', letterSpacing: '0.4em', textTransform: 'uppercase', opacity: 0.5 }}>
        FIVE TRUTHS
      </div>
    )
  },
  { 
    duration: 1200,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ width: 8, height: 50, background: COLORS.primary, borderRadius: 4 }}></div>
        <div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800 }}>REALITY</div>
          <div style={{ fontSize: '1rem', opacity: 0.5 }}>What exists</div>
        </div>
      </div>
    )
  },
  { 
    duration: 1200,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ width: 8, height: 50, background: '#4a7a9a', borderRadius: 4 }}></div>
        <div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800 }}>INTENT</div>
          <div style={{ fontSize: '1rem', opacity: 0.5 }}>What they want</div>
        </div>
      </div>
    )
  },
  { 
    duration: 1200,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ width: 8, height: 50, background: '#d97706', borderRadius: 4 }}></div>
        <div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800 }}>CONFIGURATION</div>
          <div style={{ fontSize: '1rem', opacity: 0.5 }}>How it's set up</div>
        </div>
      </div>
    )
  },
  { 
    duration: 1200,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ width: 8, height: 50, background: COLORS.purple, borderRadius: 4 }}></div>
        <div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800 }}>REFERENCE</div>
          <div style={{ fontSize: '1rem', opacity: 0.5 }}>How to configure</div>
        </div>
      </div>
    )
  },
  { 
    duration: 1200,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ width: 8, height: 50, background: COLORS.scarlet, borderRadius: 4 }}></div>
        <div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800 }}>REGULATORY</div>
          <div style={{ fontSize: '1rem', opacity: 0.5 }}>What's required</div>
        </div>
      </div>
    )
  },
  { 
    duration: 1200,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ width: 8, height: 50, background: COLORS.accent, borderRadius: 4 }}></div>
        <div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800 }}>COMPLIANCE</div>
          <div style={{ fontSize: '1rem', opacity: 0.5 }}>What must be proven</div>
        </div>
      </div>
    )
  },
  
  // THE VALUE PROPS - PUNCH
  { 
    duration: 2000,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '3rem', fontWeight: 900 }}>
        ONE PLATFORM.
      </div>
    )
  },
  { 
    duration: 2000,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '3rem', fontWeight: 900 }}>
        EVERY DECISION.
      </div>
    )
  },
  { 
    duration: 2000,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '3rem', fontWeight: 900 }}>
        FOREVER.
      </div>
    )
  },
  
  // THE DIFFERENTIATORS
  { 
    duration: 800,
    bg: COLORS.black,
    content: null
  },
  { 
    duration: 2200,
    bg: COLORS.black,
    content: (
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '4rem', fontWeight: 900, color: COLORS.primary }}>90 SECONDS</div>
        <div style={{ fontSize: '1.2rem', opacity: 0.6, marginTop: '0.5rem' }}>Not 6 minutes. Not 6 hours.</div>
      </div>
    )
  },
  { 
    duration: 2200,
    bg: COLORS.black,
    content: (
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '3.5rem', fontWeight: 900, color: COLORS.primary }}>SEARCHABLE</div>
        <div style={{ fontSize: '1.2rem', opacity: 0.6, marginTop: '0.5rem' }}>Every precedent. Every exception.</div>
      </div>
    )
  },
  { 
    duration: 2200,
    bg: COLORS.black,
    content: (
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '3.5rem', fontWeight: 900, color: COLORS.primary }}>CITED</div>
        <div style={{ fontSize: '1.2rem', opacity: 0.6, marginTop: '0.5rem' }}>Know exactly where answers come from.</div>
      </div>
    )
  },
  { 
    duration: 2200,
    bg: COLORS.black,
    content: (
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '3.5rem', fontWeight: 900, color: COLORS.primary }}>🔒 ENCRYPTED</div>
        <div style={{ fontSize: '1.2rem', opacity: 0.6, marginTop: '0.5rem' }}>Your data. Your control. Enterprise-grade security.</div>
      </div>
    )
  },
  { 
    duration: 2200,
    bg: COLORS.black,
    content: (
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '3.5rem', fontWeight: 900, color: COLORS.primary }}>LOCAL LLM</div>
        <div style={{ fontSize: '1.2rem', opacity: 0.6, marginTop: '0.5rem' }}>Sensitive data never leaves your environment.</div>
      </div>
    )
  },
  
  // THE TRANSFORMATION
  { 
    duration: 2500,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', textAlign: 'center' }}>
        <div style={{ fontSize: '1rem', letterSpacing: '0.3em', textTransform: 'uppercase', opacity: 0.4 }}>From</div>
        <div style={{ fontSize: '2rem', fontWeight: 300, opacity: 0.6, textDecoration: 'line-through' }}>Tribal knowledge</div>
        <div style={{ fontSize: '1rem', letterSpacing: '0.3em', textTransform: 'uppercase', opacity: 0.4 }}>To</div>
        <div style={{ fontSize: '2.5rem', fontWeight: 800, color: COLORS.primary }}>Institutional Memory</div>
      </div>
    )
  },
  
  // LIFECYCLE
  { 
    duration: 2500,
    bg: COLORS.black,
    content: (
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '1rem', letterSpacing: '0.3em', textTransform: 'uppercase', opacity: 0.5, marginBottom: '1rem' }}>Not just implementation</div>
        <div style={{ fontSize: '3.5rem', fontWeight: 900 }}>THE ENTIRE LIFECYCLE</div>
      </div>
    )
  },
  { 
    duration: 2000,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', justifyContent: 'center', gap: '2rem', fontSize: '1.1rem' }}>
        <span style={{ opacity: 0.7 }}>Day 1</span>
        <span style={{ color: COLORS.primary }}>→</span>
        <span style={{ opacity: 0.7 }}>Year 2</span>
        <span style={{ color: COLORS.primary }}>→</span>
        <span style={{ opacity: 0.7 }}>Year 5</span>
        <span style={{ color: COLORS.primary }}>→</span>
        <span style={{ fontWeight: 700 }}>Forever</span>
      </div>
    )
  },
  
  // THE CLOSE
  { 
    duration: 800,
    bg: COLORS.black,
    content: null
  },
  { 
    duration: 2500,
    bg: COLORS.black,
    content: (
      <div style={{ fontSize: '2.5rem', fontWeight: 300, lineHeight: 1.6, textAlign: 'center' }}>
        Every decision.<br/>
        <span style={{ fontWeight: 800, color: COLORS.primary }}>Captured.</span><br/>
        Every exception.<br/>
        <span style={{ fontWeight: 800, color: COLORS.primary }}>Searchable.</span><br/>
        Every answer.<br/>
        <span style={{ fontWeight: 800, color: COLORS.primary }}>Cited.</span>
      </div>
    )
  },
  
  // FINAL LOGO
  { 
    duration: 1000,
    bg: COLORS.primary,
    content: null
  },
  { 
    duration: 4000,
    bg: COLORS.black,
    content: (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.5rem' }}>
        <div style={{ 
          fontSize: '8rem', 
          fontWeight: 900, 
          fontFamily: "'Ubuntu Mono', monospace",
          letterSpacing: '0.1em',
          color: COLORS.white,
        }}>
          XLR8
        </div>
        <div style={{ 
          fontSize: '1.8rem', 
          fontWeight: 600,
          letterSpacing: '0.1em',
          color: COLORS.primary,
          fontStyle: 'italic'
        }}>
          Context That Compounds
        </div>
        <div style={{ 
          marginTop: '2rem',
          fontSize: '1rem',
          letterSpacing: '0.2em',
          opacity: 0.5,
          textTransform: 'uppercase'
        }}>
          The System of Record for Configuration Decisions
        </div>
      </div>
    )
  },
];

export default function HypeVideo() {
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
            background: COLORS.primary,
            transition: 'width 0.3s ease',
          }} />
        </div>
      )}
      
      {/* Content */}
      {!isPlaying ? (
        <div style={{ textAlign: 'center' }}>
          <div style={{ 
            fontSize: '5rem', 
            fontWeight: 900, 
            fontFamily: "'Ubuntu Mono', monospace",
            letterSpacing: '0.1em',
            marginBottom: '1rem',
          }}>
            XLR8
          </div>
          <div style={{ 
            fontSize: '1.2rem', 
            opacity: 0.6, 
            marginBottom: '3rem',
            fontStyle: 'italic'
          }}>
            Context That Compounds
          </div>
          <button
            onClick={startVideo}
            style={{
              padding: '1.25rem 3rem',
              fontSize: '1rem',
              fontWeight: 700,
              letterSpacing: '0.15em',
              textTransform: 'uppercase',
              background: COLORS.primary,
              color: COLORS.white,
              border: 'none',
              borderRadius: 8,
              cursor: 'pointer',
              transition: 'transform 0.2s ease, box-shadow 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.target.style.transform = 'scale(1.05)';
              e.target.style.boxShadow = `0 0 40px ${COLORS.primary}50`;
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'scale(1)';
              e.target.style.boxShadow = 'none';
            }}
          >
            ▶ Play
          </button>
          <div style={{ 
            marginTop: '2rem', 
            fontSize: '0.8rem', 
            opacity: 0.3 
          }}>
            ~60 seconds
          </div>
        </div>
      ) : (
        <div style={{
          opacity: fadeIn ? 1 : 0,
          transform: fadeIn ? 'scale(1)' : 'scale(0.98)',
          transition: 'opacity 0.3s ease, transform 0.3s ease',
          padding: '2rem',
          textAlign: 'center',
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
            border: `1px solid ${COLORS.primary}`,
            color: COLORS.primary,
            borderRadius: 6,
            cursor: 'pointer',
          }}
        >
          ↺ Replay
        </button>
      )}
    </div>
  );
}
