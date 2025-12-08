/**
 * AuthContext - Authentication & Authorization State
 * 
 * Provides:
 * - user: Current authenticated user
 * - permissions: User's permission list
 * - hasPermission(perm): Check if user has permission
 * - isAdmin/isConsultant/isCustomer: Role helpers
 * - login/logout: Auth actions
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { createClient } from '@supabase/supabase-js';

// Supabase client
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
const supabase = supabaseUrl && supabaseKey ? createClient(supabaseUrl, supabaseKey) : null;

// API base URL
const API_URL = import.meta.env.VITE_API_URL || '';

// Context
const AuthContext = createContext(null);

// Default permissions by role (fallback when API unavailable)
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

  // Fetch user profile and permissions from backend
  const fetchUserData = useCallback(async (accessToken) => {
    try {
      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        
        // Fetch permissions
        const permResponse = await fetch(`${API_URL}/api/auth/permissions`, {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        });
        
        if (permResponse.ok) {
          const permData = await permResponse.json();
          setPermissions(permData.permissions || []);
        } else {
          // Fallback to default permissions
          setPermissions(DEFAULT_PERMISSIONS[userData.role] || []);
        }
      }
    } catch (error) {
      console.error('Failed to fetch user data:', error);
      // In dev mode, set admin user
      if (!supabase) {
        setUser({
          id: 'dev-user',
          email: 'dev@xlr8.com',
          full_name: 'Dev User',
          role: 'admin',
          project_id: null,
        });
        setPermissions(DEFAULT_PERMISSIONS.admin);
      }
    }
  }, []);

  // Initialize auth state
  useEffect(() => {
    const initAuth = async () => {
      if (!supabase) {
        // Dev mode - auto-login as admin
        setUser({
          id: 'dev-user',
          email: 'dev@xlr8.com',
          full_name: 'Dev User',
          role: 'admin',
          project_id: null,
        });
        setPermissions(DEFAULT_PERMISSIONS.admin);
        setLoading(false);
        return;
      }

      // Get initial session
      const { data: { session: initialSession } } = await supabase.auth.getSession();
      setSession(initialSession);
      
      if (initialSession?.access_token) {
        await fetchUserData(initialSession.access_token);
      }
      
      setLoading(false);

      // Listen for auth changes
      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        async (event, newSession) => {
          setSession(newSession);
          
          if (newSession?.access_token) {
            await fetchUserData(newSession.access_token);
          } else {
            setUser(null);
            setPermissions([]);
          }
        }
      );

      return () => subscription?.unsubscribe();
    };

    initAuth();
  }, [fetchUserData]);

  // Login with email/password
  const login = async (email, password) => {
    if (!supabase) {
      throw new Error('Supabase not configured');
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
    if (supabase) {
      await supabase.auth.signOut();
    }
    setUser(null);
    setSession(null);
    setPermissions([]);
  };

  // Check if user has a specific permission
  const hasPermission = useCallback((permission) => {
    return permissions.includes(permission);
  }, [permissions]);

  // Check if user can access a route/feature
  const canAccess = useCallback((requiredPermission) => {
    if (!user) return false;
    if (user.role === 'admin') return true; // Admin bypasses all checks
    return hasPermission(requiredPermission);
  }, [user, hasPermission]);

  // Role helpers
  const isAdmin = user?.role === 'admin';
  const isConsultant = user?.role === 'consultant';
  const isCustomer = user?.role === 'customer';

  // Get auth header for API calls
  const getAuthHeader = useCallback(() => {
    if (session?.access_token) {
      return { Authorization: `Bearer ${session.access_token}` };
    }
    return {};
  }, [session]);

  const value = {
    // State
    user,
    permissions,
    loading,
    session,
    
    // Role helpers
    isAdmin,
    isConsultant,
    isCustomer,
    isAuthenticated: !!user,
    
    // Methods
    login,
    logout,
    hasPermission,
    canAccess,
    getAuthHeader,
    
    // Supabase client (for advanced usage)
    supabase,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Hook for consuming auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Permission constants (match backend)
export const Permissions = {
  // Features
  CHAT: 'chat',
  UPLOAD: 'upload',
  PLAYBOOKS: 'playbooks',
  VACUUM: 'vacuum',
  EXPORT: 'export',
  DATA_MODEL: 'data_model',
  
  // Data access
  PROJECTS_ALL: 'projects_all',
  PROJECTS_OWN: 'projects_own',
  DELETE_DATA: 'delete_data',
  
  // Admin
  OPS_CENTER: 'ops_center',
  SECURITY_SETTINGS: 'security_settings',
  USER_MANAGEMENT: 'user_management',
  ROLE_PERMISSIONS: 'role_permissions',
};

export default AuthContext;
