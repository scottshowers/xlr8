/**
 * Tooltip.jsx - Shared Tooltip Component
 * 
 * Smart positioning tooltip that:
 * - Respects global tooltip enable/disable setting
 * - Positions above or below based on available space
 * - Stays within viewport bounds
 * - Uses Portal to render above all content
 * 
 * Deploy to: frontend/src/components/ui/Tooltip.jsx
 */

import React, { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useTooltips } from '../../context/TooltipContext';

// Mission Control Colors
const colors = {
  text: '#1a2332',
  white: '#ffffff',
  skyBlue: '#93abd9',
};

export function Tooltip({ 
  children, 
  title, 
  detail, 
  action, 
  width = 280,
  disabled = false  // Allow individual tooltips to be disabled
}) {
  const [show, setShow] = useState(false);
  const [coords, setCoords] = useState({ x: 0, y: 0, showBelow: false });
  const triggerRef = useRef(null);
  
  // Get global tooltip setting (hook returns defaults if no provider)
  const { tooltipsEnabled } = useTooltips();

  const handleMouseEnter = () => {
    if (!tooltipsEnabled || disabled) return;
    
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      const spaceAbove = rect.top;
      const showBelow = spaceAbove < 200;
      
      setCoords({
        x: rect.left + rect.width / 2,
        y: showBelow ? rect.bottom + 8 : rect.top - 8,
        showBelow
      });
    }
    setShow(true);
  };

  const handleMouseLeave = () => {
    setShow(false);
  };

  const shouldShow = show && tooltipsEnabled && !disabled;

  // Use Portal to render tooltip at body level (escapes all stacking contexts)
  const tooltipContent = shouldShow ? createPortal(
    <div style={{
      position: 'fixed',
      left: Math.min(Math.max(coords.x, width / 2 + 16), window.innerWidth - width / 2 - 16),
      top: coords.showBelow ? coords.y : 'auto',
      bottom: coords.showBelow ? 'auto' : `calc(100vh - ${coords.y}px)`,
      transform: 'translateX(-50%)',
      padding: '12px 16px', 
      backgroundColor: colors.text, 
      color: colors.white,
      borderRadius: '8px', 
      fontSize: '12px', 
      width: width, 
      zIndex: 999999, 
      boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
      lineHeight: 1.5,
      pointerEvents: 'none',
    }}>
      {title && <div style={{ fontWeight: 600, marginBottom: '6px', fontSize: '13px' }}>{title}</div>}
      <div style={{ opacity: 0.9 }}>{detail}</div>
      {action && (
        <div style={{ 
          marginTop: '10px', 
          paddingTop: '10px', 
          borderTop: '1px solid rgba(255,255,255,0.2)', 
          color: colors.skyBlue, 
          fontWeight: 500,
          fontSize: '11px'
        }}>
           {action}
        </div>
      )}
      {/* Arrow */}
      <div style={{ 
        position: 'absolute', 
        left: '50%', 
        transform: 'translateX(-50%)',
        ...(coords.showBelow 
          ? { top: '-6px', borderBottom: `6px solid ${colors.text}`, borderTop: 'none' }
          : { bottom: '-6px', borderTop: `6px solid ${colors.text}`, borderBottom: 'none' }
        ),
        width: 0, 
        height: 0, 
        borderLeft: '6px solid transparent', 
        borderRight: '6px solid transparent',
      }} />
    </div>,
    document.body
  ) : null;

  return (
    <div 
      ref={triggerRef}
      style={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={handleMouseEnter} 
      onMouseLeave={handleMouseLeave}
    >
      {children}
      {tooltipContent}
    </div>
  );
}

/**
 * Simple inline tooltip for smaller hints
 */
export function SimpleTooltip({ children, text, position = 'top' }) {
  const [show, setShow] = useState(false);
  const triggerRef = useRef(null);
  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const { tooltipsEnabled } = useTooltips();

  const handleMouseEnter = () => {
    if (!tooltipsEnabled) return;
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setCoords({
        x: rect.left + rect.width / 2,
        y: position === 'top' ? rect.top - 8 : rect.bottom + 8,
      });
    }
    setShow(true);
  };

  if (!tooltipsEnabled) {
    return children;
  }

  const tooltipContent = show ? createPortal(
    <div style={{
      position: 'fixed',
      left: coords.x,
      top: position === 'bottom' ? coords.y : 'auto',
      bottom: position === 'top' ? `calc(100vh - ${coords.y}px)` : 'auto',
      transform: 'translateX(-50%)',
      padding: '6px 10px',
      backgroundColor: colors.text,
      color: colors.white,
      borderRadius: '6px',
      fontSize: '11px',
      fontWeight: 500,
      whiteSpace: 'nowrap',
      zIndex: 999999,
      pointerEvents: 'none',
    }}>
      {text}
    </div>,
    document.body
  ) : null;

  return (
    <div 
      ref={triggerRef}
      style={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {tooltipContent}
    </div>
  );
}

// Default export for backward compatibility
export default Tooltip;
