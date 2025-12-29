import axios from 'axios';
import supabase from './supabaseClient';

const API_URL = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

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
