/**
 * AuthContext - Authentication & Authorization State
 * 
 * Reads user profile directly from Supabase profiles table
 * 
 * FIXED: Proper error handling so loading always resolves
 * FIXED: Proper cleanup function registration
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { createClient } from '@supabase/supabase-js';

// Supabase client
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

console.log('[Auth] Supabase URL configured:', !!supabaseUrl);
console.log('[Auth] Supabase Key configured:', !!supabaseKey);

const supabase = supabaseUrl && supabaseKey ? createClient(supabaseUrl, supabaseKey) : null;

if (!supabase) {
  console.warn('[Auth] Supabase client not initialized');
}

// Context
const AuthContext = createContext(null);

// Permission constants
export const Permissions = {
  CHAT: 'chat',
  UPLOAD: 'upload',
  PLAYBOOKS: 'playbooks',
  VACUUM: 'vacuum',
  EXPORT: 'export',
  DATA_MODEL: 'data_model',
  PROJECTS_ALL: 'projects_all',
  PROJECTS_OWN: 'projects_own',
  DELETE_DATA: 'delete_data',
  OPS_CENTER: 'ops_center',
  SECURITY_SETTINGS: 'security_settings',
  USER_MANAGEMENT: 'user_management',
  ROLE_PERMISSIONS: 'role_permissions',
};

// Default permissions by role
const DEFAULT_PERMISSIONS = {
  admin: [
    'chat', 'upload', 'playbooks', 'vacuum', 'export', 'data_model',
    'projects_all', 'projects_own', 'delete_data',
    'ops_center', 'security_settings', 'user_management', 'role_permissions'
  ],
  consultant: [
    'chat', 'upload', 'playbooks', 'vacuum', 'export', 'data_model',
    'projects_all', 'projects_own'
  ],
  customer: ['chat', 'export', 'projects_own'],
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState(null);
  
  // Use ref to store subscription for cleanup
  const subscriptionRef = useRef(null);

  // Fetch user profile directly from Supabase
  const fetchUserProfile = useCallback(async (supabaseUser) => {
    if (!supabase || !supabaseUser) {
      console.log('[Auth] No supabase client or user, skipping profile fetch');
      return;
    }
    
    try {
      console.log('[Auth] Fetching profile for:', supabaseUser.email);
      
      const { data: profile, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', supabaseUser.id)
        .single();

      if (error) {
        console.error('[Auth] Profile fetch error:', error);
        // Fallback to basic user info
        setUser({
          id: supabaseUser.id,
          email: supabaseUser.email,
          full_name: supabaseUser.email,
          role: 'customer',
          project_id: null,
        });
        setPermissions(DEFAULT_PERMISSIONS.customer);
        return;
      }

      console.log('[Auth] Profile loaded:', profile);

      // Set user from profile
      setUser({
        id: profile.id,
        email: profile.email,
        full_name: profile.full_name || profile.email,
        role: profile.role || 'customer',
        project_id: profile.project_id,
        mfa_enabled: profile.mfa_enabled,
        mfa_method: profile.mfa_method,
      });

      // Set permissions based on role
      const role = profile.role || 'customer';
      setPermissions(DEFAULT_PERMISSIONS[role] || DEFAULT_PERMISSIONS.customer);
      
      console.log('[Auth] User role:', role, 'Permissions:', DEFAULT_PERMISSIONS[role]);
    } catch (error) {
      console.error('[Auth] Failed to fetch user data:', error);
      // FIXED: Still set a basic user on error so app doesn't hang
      setUser({
        id: supabaseUser.id,
        email: supabaseUser.email,
        full_name: supabaseUser.email,
        role: 'customer',
        project_id: null,
      });
      setPermissions(DEFAULT_PERMISSIONS.customer);
    }
  }, []);

  // Initialize auth state
  useEffect(() => {
    let isMounted = true;
    
    const initAuth = async () => {
      try {
        if (!supabase) {
          // Dev mode - auto-login as admin
          console.log('[Auth] Dev mode - using mock admin');
          if (isMounted) {
            setUser({
              id: 'dev-user',
              email: 'dev@xlr8.com',
              full_name: 'Dev User',
              role: 'admin',
              project_id: null,
            });
            setPermissions(DEFAULT_PERMISSIONS.admin);
          }
          return;
        }

        // Get initial session
        console.log('[Auth] Getting initial session...');
        const { data: { session: initialSession }, error: sessionError } = await supabase.auth.getSession();
        
        if (sessionError) {
          console.error('[Auth] Session error:', sessionError);
        }
        
        console.log('[Auth] Initial session:', !!initialSession);
        
        if (isMounted) {
          setSession(initialSession);
        }
        
        if (initialSession?.user && isMounted) {
          await fetchUserProfile(initialSession.user);
        }

      } catch (error) {
        console.error('[Auth] Init error:', error);
      } finally {
        // FIXED: ALWAYS set loading to false, even on error
        if (isMounted) {
          console.log('[Auth] Setting loading to false');
          setLoading(false);
        }
      }
    };

    // Run init
    initAuth();
    
    // FIXED: Set up auth listener separately (not inside async function)
    if (supabase) {
      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        async (event, newSession) => {
          console.log('[Auth] Auth state changed:', event);
          
          if (!isMounted) return;
          
          setSession(newSession);
          
          if (event === 'SIGNED_IN' && newSession?.user) {
            await fetchUserProfile(newSession.user);
          } else if (event === 'SIGNED_OUT') {
            setUser(null);
            setPermissions([]);
          }
        }
      );
      
      subscriptionRef.current = subscription;
    }

    // FIXED: Proper cleanup function
    return () => {
      isMounted = false;
      if (subscriptionRef.current) {
        subscriptionRef.current.unsubscribe();
      }
    };
  }, [fetchUserProfile]);

  // Login
  const login = async (email, password) => {
    if (!supabase) {
      throw new Error('Authentication not configured');
    }

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) throw error;
    return data;
  };

  // Logout
  const logout = async () => {
    if (!supabase) return;
    
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    
    setUser(null);
    setPermissions([]);
    setSession(null);
  };

  // Permission helpers
  const hasPermission = (permission) => {
    return permissions.includes(permission);
  };

  const canAccess = (permission) => {
    // Admins can access everything
    if (user?.role === 'admin') return true;
    return hasPermission(permission);
  };

  // Role helpers
  const isAdmin = user?.role === 'admin';
  const isConsultant = user?.role === 'consultant';
  const isCustomer = user?.role === 'customer';
  const isAuthenticated = !!user;

  // Auth header for API calls
  const getAuthHeader = () => {
    if (session?.access_token) {
      return { Authorization: `Bearer ${session.access_token}` };
    }
    return {};
  };

  const value = {
    user,
    permissions,
    loading,
    session,
    supabase,
    isAdmin,
    isConsultant,
    isCustomer,
    isAuthenticated,
    login,
    logout,
    hasPermission,
    canAccess,
    getAuthHeader,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
