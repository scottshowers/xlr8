/**
 * Customer Color Utility
 * 
 * Generates consistent, subtle colors from customer names.
 * Same customer always gets same color across the app.
 * 
 * Usage:
 *   import { getCustomerColor } from '../utils/customerColors';
 *   const color = getCustomerColor('Meyer Corporation');
 */

// Subtle color palette - muted, professional tones
const CUSTOMER_COLORS = [
  '#7c9eb5', // Steel blue
  '#8fa888', // Sage green
  '#b5a07c', // Warm tan
  '#9b8aa6', // Dusty purple
  '#7cb5a8', // Seafoam
  '#a88f8a', // Dusty rose
  '#8a9fa8', // Slate
  '#a8a07c', // Olive
  '#8aa8a6', // Teal gray
  '#a89b8a', // Taupe
  '#7c8fb5', // Periwinkle
  '#a88a9b', // Mauve
];

/**
 * Simple string hash function
 * Produces consistent hash for same input
 */
function hashString(str) {
  if (!str) return 0;
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash);
}

/**
 * Get consistent color for a customer name
 * @param {string} customerName - Customer/company name
 * @returns {string} Hex color code
 */
export function getCustomerColor(customerName) {
  if (!customerName) return CUSTOMER_COLORS[0];
  const hash = hashString(customerName.toLowerCase().trim());
  return CUSTOMER_COLORS[hash % CUSTOMER_COLORS.length];
}

/**
 * Get customer initials (first 2 chars of first word, or first char of first 2 words)
 * @param {string} customerName - Customer/company name
 * @returns {string} 2-character initials
 */
export function getCustomerInitials(customerName) {
  if (!customerName) return '??';
  const words = customerName.trim().split(/\s+/);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  return customerName.slice(0, 2).toUpperCase();
}

/**
 * Get text color (white or dark) based on background
 * @param {string} hexColor - Background color
 * @returns {string} 'white' or '#2a3441'
 */
export function getContrastText(hexColor) {
  // Convert hex to RGB
  const r = parseInt(hexColor.slice(1, 3), 16);
  const g = parseInt(hexColor.slice(3, 5), 16);
  const b = parseInt(hexColor.slice(5, 7), 16);
  // Calculate luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? '#2a3441' : 'white';
}

export default { getCustomerColor, getCustomerInitials, getContrastText };
