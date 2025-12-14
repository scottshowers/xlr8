/**
 * customerColors.js - Consistent Customer Color System
 * 
 * IMPORTANT: getCustomerColor returns a COLOR STRING for backward compatibility.
 * Use getCustomerColorPalette if you need the full object.
 */

// Color palette
const PALETTE = {
  grassGreen: '#83b16d',
  skyBlue: '#93abd9',
  amber: '#f59e0b',
  purple: '#8b5cf6',
  teal: '#14b8a6',
  rose: '#f43f5e',
  indigo: '#6366f1',
  emerald: '#10b981',
  orange: '#f97316',
  cyan: '#06b6d4',
  gray: '#6b7280',
};

// Map customer names to colors (add your customers here)
const CUSTOMER_COLOR_MAP = {
  // By customer name
  'meyer corp': PALETTE.grassGreen,
  'acme industries': PALETTE.skyBlue,
  'global tech': PALETTE.amber,
  'techflow inc': PALETTE.purple,
  'techflow': PALETTE.purple,
  
  // By project code
  'mey1000': PALETTE.grassGreen,
  'acm2500': PALETTE.skyBlue,
  'glb3000': PALETTE.amber,
  'tec4000': PALETTE.purple,
  
  // Special
  'global': PALETTE.teal,
  '__standards__': PALETTE.teal,
};

// Color rotation for unknown customers (deterministic based on name)
const COLOR_ROTATION = [
  PALETTE.grassGreen,
  PALETTE.skyBlue,
  PALETTE.amber,
  PALETTE.purple,
  PALETTE.teal,
  PALETTE.rose,
  PALETTE.indigo,
  PALETTE.emerald,
  PALETTE.orange,
  PALETTE.cyan,
];

/**
 * Simple hash function for consistent color assignment
 */
function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

/**
 * Get color for a customer/project (returns STRING)
 * @param {string} name - Customer name or project code
 * @returns {string} Hex color string
 */
export function getCustomerColor(name) {
  if (!name) return PALETTE.gray;
  
  const key = String(name).toLowerCase().trim();
  
  // Check explicit mapping first
  if (CUSTOMER_COLOR_MAP[key]) {
    return CUSTOMER_COLOR_MAP[key];
  }
  
  // Fall back to deterministic color based on name hash
  const index = hashString(key) % COLOR_ROTATION.length;
  return COLOR_ROTATION[index];
}

/**
 * Get full color palette for a customer/project
 * @param {string} name - Customer name or project code  
 * @returns {object} { primary, secondary, bg, bgSolid }
 */
export function getCustomerColorPalette(name) {
  const primary = getCustomerColor(name);
  return {
    primary,
    secondary: primary + 'cc', // Slightly transparent
    bg: `linear-gradient(135deg, ${primary}15, ${primary}08)`,
    bgSolid: primary + '15',
  };
}

/**
 * Get initials from customer/project name
 * @param {string} name - Customer or project name
 * @returns {string} 2-character initials
 */
export function getCustomerInitials(name) {
  if (!name) return '??';
  
  const str = String(name).trim();
  
  // If it's a project code like MEY1000, take first 2 chars
  if (/^[A-Z]{3}\d+$/i.test(str)) {
    return str.slice(0, 2).toUpperCase();
  }
  
  // Otherwise split by space and take first letter of each word
  const words = str.split(/\s+/).filter(w => w.length > 0);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  
  // Single word - take first 2 chars
  return str.slice(0, 2).toUpperCase();
}

/**
 * Get contrasting text color (black or white) for a background
 * @param {string} hexColor - Hex color string
 * @returns {string} '#ffffff' or '#000000'
 */
export function getContrastText(hexColor) {
  // Handle null, undefined, objects, etc.
  if (!hexColor || typeof hexColor !== 'string') {
    return '#ffffff';
  }
  
  // Remove # if present
  const hex = hexColor.replace('#', '');
  
  // Validate hex format
  if (!/^[0-9A-Fa-f]{6}$/.test(hex) && !/^[0-9A-Fa-f]{3}$/.test(hex)) {
    return '#ffffff';
  }
  
  // Expand 3-char hex to 6-char
  const fullHex = hex.length === 3 
    ? hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2]
    : hex;
  
  // Parse RGB values
  const r = parseInt(fullHex.substr(0, 2), 16);
  const g = parseInt(fullHex.substr(2, 2), 16);
  const b = parseInt(fullHex.substr(4, 2), 16);
  
  // Calculate relative luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  
  // Return black or white based on luminance
  return luminance > 0.5 ? '#000000' : '#ffffff';
}

export default {
  getCustomerColor,
  getCustomerColorPalette,
  getCustomerInitials,
  getContrastText,
  PALETTE,
};
