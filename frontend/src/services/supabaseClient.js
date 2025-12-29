/**
 * Supabase Client - SINGLE INSTANCE
 * 
 * This is the ONE AND ONLY Supabase client for the entire frontend.
 * Import this everywhere instead of calling createClient() multiple times.
 * 
 * Multiple GoTrueClient instances cause:
 * - "Multiple GoTrueClient instances" warning
 * - Session race conditions
 * - Auth timeout errors
 * - Intermittent loading failures
 */

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

// Create client ONCE
let supabase = null;

if (supabaseUrl && supabaseKey) {
  supabase = createClient(supabaseUrl, supabaseKey, {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true
    }
  });
  console.log('[Supabase] Client initialized (single instance)');
} else {
  console.warn('[Supabase] Missing URL or Key - client not initialized');
}

export default supabase;
