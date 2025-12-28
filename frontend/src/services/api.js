import axios from 'axios';
import { createClient } from '@supabase/supabase-js';

const API_URL = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

// Supabase client for auth
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
const supabase = supabaseUrl && supabaseKey ? createClient(supabaseUrl, supabaseKey) : null;

const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth interceptor - attaches JWT token to all requests
api.interceptors.request.use(
  async (config) => {
    try {
      if (supabase) {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
          config.headers.Authorization = `Bearer ${session.access_token}`;
        }
        // Also add user info as headers for backends that check headers
        if (session?.user) {
          config.headers['X-User-Id'] = session.user.id;
          config.headers['X-User-Email'] = session.user.email;
        }
      }
    } catch (error) {
      // Don't block requests if auth fails - just log it
      console.debug('[API] Auth header error:', error.message);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
