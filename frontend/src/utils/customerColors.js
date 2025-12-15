/**
 * customerColors.js - Consistent Customer Color System
 * 
 * IMPORTANT: getCustomerColor returns a COLOR STRING for backward compatibility.
 * Use getCustomerColorPalette if you need the full object.
 * 
 * Colors are assigned uniquely - no two customers will share a color
 * (until we run out of colors in the palette).
 */

// Color palette - 12 distinct colors
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
  slate: '#64748b',
  pink: '#ec4899',
};

// Map customer names to colors (explicit assignments)
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

// Color rotation for auto-assignment (order matters for visual distinction)
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
  PALETTE.slate,
  PALETTE.pink,
];

// Registry to track assigned colors (ensures uniqueness)
const colorRegistry = new Map(); // key (lowercase name) -> color
const usedColors = new Set();    // colors currently in use

/**
 * Clear the color registry (useful for testing or reset)
 */
export function resetColorRegistry() {
  colorRegistry.clear();
  usedColors.clear();
}

/**
 * Get the next available color that hasn't been used
 */
function getNextAvailableColor() {
  for (const color of COLOR_ROTATION) {
    if (!usedColors.has(color)) {
      return color;
    }
  }
  // All colors used - start reusing (but this shouldn't happen with 12 colors)
  return COLOR_ROTATION[usedColors.size % COLOR_ROTATION.length];
}

/**
 * Get color for a customer/project (returns STRING)
 * Colors are assigned uniquely per customer.
 * 
 * @param {string} name - Customer name or project code
 * @returns {string} Hex color string
 */
export function getCustomerColor(name) {
  if (!name) return PALETTE.slate;
  
  const key = String(name).toLowerCase().trim();
  
  // Already assigned? Return it
  if (colorRegistry.has(key)) {
    return colorRegistry.get(key);
  }
  
  // Check explicit mapping first
  if (CUSTOMER_COLOR_MAP[key]) {
    const color = CUSTOMER_COLOR_MAP[key];
    colorRegistry.set(key, color);
    usedColors.add(color);
    return color;
  }
  
  // Assign next available color (guarantees uniqueness)
  const color = getNextAvailableColor();
  colorRegistry.set(key, color);
  usedColors.add(color);
  
  return color;
}

/**
 * Pre-register multiple customers to ensure unique colors
 * Call this once with all customer names before rendering
 * 
 * @param {string[]} names - Array of customer/project names
 * @returns {Map} Map of name -> color
 */
export function registerCustomerColors(names) {
  const result = new Map();
  
  for (const name of names) {
    if (!name) continue;
    const color = getCustomerColor(name);
    result.set(name, color);
  }
  
  return result;
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
  registerCustomerColors,
  resetColorRegistry,
  PALETTE,
};
