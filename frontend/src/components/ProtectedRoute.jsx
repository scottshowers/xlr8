/**
 * ProtectedRoute - Route-level access control
 * 
 * Usage:
 *   <Route path="/admin" element={
 *     <ProtectedRoute permission="ops_center">
 *       <AdminPage />
 *     </ProtectedRoute>
 *   } />
 * 
 * Or with role check:
 *   <Route path="/admin" element={
 *     <ProtectedRoute role="admin">
 *       <AdminPage />
 *     </ProtectedRoute>
 *   } />
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ 
  children, 
  permission,  // Required permission to access
  role,        // Required role (alternative to permission)
  fallback = '/dashboard',  // Where to redirect if denied
  requireAuth = true,  // Whether authentication is required
}) {
  const { user, loading, hasPermission, isAuthenticated } = useAuth();
  const location = useLocation();

  // Still loading auth state
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        color: '#5f6c7b',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}></div>
          <div>Checking access...</div>
        </div>
      </div>
    );
  }

  // Not authenticated
  if (requireAuth && !isAuthenticated) {
    // Redirect to login, preserving intended destination
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role if specified
  if (role && user?.role !== role) {
    return <AccessDenied message={`This page requires ${role} access.`} fallback={fallback} />;
  }

  // Check permission if specified
  if (permission && !hasPermission(permission)) {
    return <AccessDenied message={`You don't have permission to access this page.`} fallback={fallback} />;
  }

  // All checks passed
  return children;
}

// Access denied component
function AccessDenied({ message, fallback }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '60vh',
      padding: '2rem',
    }}>
      <div style={{
        background: 'white',
        borderRadius: '16px',
        padding: '3rem',
        maxWidth: '400px',
        textAlign: 'center',
        boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
      }}>
        <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🚫</div>
        <h2 style={{ 
          color: '#2a3441', 
          marginBottom: '0.5rem',
          fontFamily: "'Sora', sans-serif",
        }}>
          Access Denied
        </h2>
        <p style={{ color: '#5f6c7b', marginBottom: '1.5rem' }}>
          {message}
        </p>
        <a
          href={fallback}
          style={{
            display: 'inline-block',
            padding: '0.75rem 1.5rem',
            background: '#83b16d',
            color: 'white',
            borderRadius: '8px',
            textDecoration: 'none',
            fontWeight: '600',
          }}
        >
          Go to Dashboard
        </a>
      </div>
    </div>
  );
}

// Higher-order component version
export function withPermission(WrappedComponent, permission) {
  return function PermissionWrapper(props) {
    return (
      <ProtectedRoute permission={permission}>
        <WrappedComponent {...props} />
      </ProtectedRoute>
    );
  };
}

// Hook for checking access in components
export function useRequirePermission(permission) {
  const { hasPermission, loading } = useAuth();
  
  if (loading) return { allowed: false, loading: true };
  
  return { 
    allowed: hasPermission(permission), 
    loading: false 
  };
}
