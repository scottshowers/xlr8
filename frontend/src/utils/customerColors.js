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
  return CUSTOMER_COLORS[projectName] || DEFAULT_COLOR;
}

/**
 * Get just the primary color for a project
 * @param {string} projectName - The project code
 * @returns {string} Primary color hex value
 */
export function getCustomerPrimaryColor(projectName) {
  return getCustomerColor(projectName).primary;
}

export default CUSTOMER_COLORS;
