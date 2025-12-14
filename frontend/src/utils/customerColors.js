/**
 * customerColors.js - Consistent Customer Color System
 * 
 * Use these colors for project/customer displays across the app
 * to maintain visual consistency.
 */

// Customer color system - maps project codes to color palettes
export const CUSTOMER_COLORS = {
  'MEY1000': { 
    primary: '#83b16d',   // grassGreen
    secondary: '#a8ca99', 
    bg: 'linear-gradient(135deg, #83b16d15, #a8ca9910)',
    bgSolid: '#83b16d15',
  },
  'ACM2500': { 
    primary: '#93abd9',   // skyBlue
    secondary: '#b4c7e7', 
    bg: 'linear-gradient(135deg, #93abd915, #b4c7e710)',
    bgSolid: '#93abd915',
  },
  'GLB3000': { 
    primary: '#f59e0b',   // amber
    secondary: '#fbbf24', 
    bg: 'linear-gradient(135deg, #f59e0b15, #fbbf2410)',
    bgSolid: '#f59e0b15',
  },
  'TEC4000': { 
    primary: '#8b5cf6',   // purple
    secondary: '#a78bfa', 
    bg: 'linear-gradient(135deg, #8b5cf615, #a78bfa10)',
    bgSolid: '#8b5cf615',
  },
  'GLOBAL':  { 
    primary: '#14b8a6',   // teal
    secondary: '#5eead4', 
    bg: 'linear-gradient(135deg, #14b8a615, #5eead410)',
    bgSolid: '#14b8a615',
  },
};

// Default color for unknown projects
const DEFAULT_COLOR = { 
  primary: '#6b7280',   // gray
  secondary: '#9ca3af', 
  bg: 'linear-gradient(135deg, #6b728015, #9ca3af10)',
  bgSolid: '#6b728015',
};

/**
 * Get consistent color palette for a project
 * @param {string} projectName - The project code (e.g., 'MEY1000')
 * @returns {object} Color palette { primary, secondary, bg, bgSolid }
 */
export function getCustomerColor(projectName) {
  if (!projectName) return DEFAULT_COLOR;
  const key = String(projectName);
  return CUSTOMER_COLORS[key] || DEFAULT_COLOR;
}

/**
 * Get just the primary color for a project
 * @param {string} projectName - The project code
 * @returns {string} Primary color hex value
 */
export function getCustomerPrimaryColor(projectName) {
  return getCustomerColor(projectName).primary;
}

/**
 * Get initials from customer/project name
 * @param {string} name - Customer or project name
 * @returns {string} 2-character initials
 */
export function getCustomerInitials(name) {
  if (!name) return '??';
  
  const str = String(name);
  
  // If it's a project code like MEY1000, take first 2 chars
  if (/^[A-Z]{3}\d+$/.test(str)) {
    return str.slice(0, 2);
  }
  
  // Otherwise split by space and take first letter of each word
  const words = str.trim().split(/\s+/);
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

export default CUSTOMER_COLORS;
