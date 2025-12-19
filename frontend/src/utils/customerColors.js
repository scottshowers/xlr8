/**
 * customerColors.js - Customer Color Palette Generator
 * 
 * Professional, muted color palette for customer differentiation.
 * No neon, no teal, no bright orange - darker, sophisticated tones.
 */

// Muted, professional color palettes
const COLOR_PALETTES = [
  // Deep Forest Green (XLR8 primary family)
  { primary: '#5a8a4a', bg: 'rgba(90, 138, 74, 0.08)', border: 'rgba(90, 138, 74, 0.25)' },
  
  // Slate Blue
  { primary: '#4a6b8a', bg: 'rgba(74, 107, 138, 0.08)', border: 'rgba(74, 107, 138, 0.25)' },
  
  // Dusty Purple
  { primary: '#6b5a7a', bg: 'rgba(107, 90, 122, 0.08)', border: 'rgba(107, 90, 122, 0.25)' },
  
  // Terracotta (muted rust, not orange)
  { primary: '#8a5a4a', bg: 'rgba(138, 90, 74, 0.08)', border: 'rgba(138, 90, 74, 0.25)' },
  
  // Deep Teal (not bright)
  { primary: '#4a7a7a', bg: 'rgba(74, 122, 122, 0.08)', border: 'rgba(74, 122, 122, 0.25)' },
  
  // Warm Gray
  { primary: '#6a6a5a', bg: 'rgba(106, 106, 90, 0.08)', border: 'rgba(106, 106, 90, 0.25)' },
  
  // Navy
  { primary: '#3a4a6a', bg: 'rgba(58, 74, 106, 0.08)', border: 'rgba(58, 74, 106, 0.25)' },
  
  // Burgundy
  { primary: '#7a4a5a', bg: 'rgba(122, 74, 90, 0.08)', border: 'rgba(122, 74, 90, 0.25)' },
  
  // Olive
  { primary: '#5a6a4a', bg: 'rgba(90, 106, 74, 0.08)', border: 'rgba(90, 106, 74, 0.25)' },
  
  // Steel
  { primary: '#5a6a7a', bg: 'rgba(90, 106, 122, 0.08)', border: 'rgba(90, 106, 122, 0.25)' },
  
  // Espresso
  { primary: '#5a4a3a', bg: 'rgba(90, 74, 58, 0.08)', border: 'rgba(90, 74, 58, 0.25)' },
  
  // Plum
  { primary: '#5a4a6a', bg: 'rgba(90, 74, 106, 0.08)', border: 'rgba(90, 74, 106, 0.25)' },
];

/**
 * Generate a consistent color palette for a customer name.
 * Uses string hashing to ensure the same customer always gets the same color.
 */
export function getCustomerColorPalette(customerName) {
  if (!customerName) {
    // Default to XLR8 green for no customer
    return {
      primary: '#5a8a4a',
      bg: 'rgba(90, 138, 74, 0.08)',
      border: 'rgba(90, 138, 74, 0.25)',
    };
  }
  
  // Simple string hash
  let hash = 0;
  for (let i = 0; i < customerName.length; i++) {
    const char = customerName.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  
  // Use absolute value and mod to get palette index
  const index = Math.abs(hash) % COLOR_PALETTES.length;
  return COLOR_PALETTES[index];
}

/**
 * Get all available palettes (for admin/preview purposes)
 */
export function getAllPalettes() {
  return COLOR_PALETTES;
}

export default { getCustomerColorPalette, getAllPalettes };
