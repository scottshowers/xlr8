/**
 * RolePermissions - Admin page for managing role permissions
 * 
 * Displays a grid where admins can toggle permissions for each role.
 * Changes are saved to Supabase and take effect immediately.
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || '';

// Styles
const styles = {
  container: {
    padding: '1.5rem',
  },
  header: {
    marginBottom: '1.5rem',
  },
  title: {
    fontFamily: "'Sora', sans-serif",
    fontSize: '1.5rem',
    fontWeight: '700',
    color: '#2a3441',
    margin: 0,
  },
  subtitle: {
    color: '#5f6c7b',
    marginTop: '0.25rem',
    fontSize: '0.9rem',
  },
  card: {
    background: 'white',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(42, 52, 65, 0.08)',
    overflow: 'hidden',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    padding: '1rem',
    textAlign: 'left',
    borderBottom: '2px solid #e1e8ed',
    fontWeight: '600',
    color: '#2a3441',
    background: '#fafbfc',
  },
  thRole: {
    padding: '1rem',
    textAlign: 'center',
    borderBottom: '2px solid #e1e8ed',
    fontWeight: '600',
    color: '#2a3441',
    background: '#fafbfc',
    minWidth: '120px',
  },
  categoryRow: {
    background: '#f5f7f9',
  },
  categoryCell: {
    padding: '0.75rem 1rem',
    fontWeight: '700',
    color: '#5f6c7b',
    fontSize: '0.8rem',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    borderBottom: '1px solid #e1e8ed',
  },
  td: {
    padding: '0.75rem 1rem',
    borderBottom: '1px solid #e1e8ed',
    color: '#2a3441',
  },
  tdCenter: {
    padding: '0.75rem 1rem',
    borderBottom: '1px solid #e1e8ed',
    textAlign: 'center',
  },
  toggle: (enabled, locked) => ({
    width: '44px',
    height: '24px',
    borderRadius: '12px',
    background: enabled ? '#83b16d' : '#d1d5db',
    border: 'none',
    cursor: locked ? 'not-allowed' : 'pointer',
    position: 'relative',
    transition: 'background 0.2s ease',
    opacity: locked ? 0.5 : 1,
  }),
  toggleKnob: (enabled) => ({
    position: 'absolute',
    top: '2px',
    left: enabled ? '22px' : '2px',
    width: '20px',
    height: '20px',
    borderRadius: '50%',
    background: 'white',
    boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
    transition: 'left 0.2s ease',
  }),
  saveBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '1rem 1.5rem',
    background: '#fff9e6',
    borderTop: '1px solid #ffd700',
  },
  saveButton: {
    padding: '0.625rem 1.25rem',
    background: '#83b16d',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  discardButton: {
    padding: '0.625rem 1.25rem',
    background: 'transparent',
    color: '#5f6c7b',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontWeight: '600',
    cursor: 'pointer',
    marginLeft: '0.5rem',
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '4rem',
    color: '#5f6c7b',
  },
  error: {
    padding: '2rem',
    textAlign: 'center',
    color: '#dc2626',
  },
  roleBadge: (role) => ({
    display: 'inline-block',
    padding: '0.25rem 0.75rem',
    borderRadius: '999px',
    fontSize: '0.75rem',
    fontWeight: '600',
    background: role === 'admin' ? '#fef3c7' : role === 'consultant' ? '#dbeafe' : '#f3e8ff',
    color: role === 'admin' ? '#92400e' : role === 'consultant' ? '#1e40af' : '#6b21a8',
  }),
};

// Toggle component
function Toggle({ enabled, onChange, locked = false }) {
  return (
    <button
      onClick={() => !locked && onChange(!enabled)}
      style={styles.toggle(enabled, locked)}
      disabled={locked}
      title={locked ? 'This permission cannot be changed' : ''}
    >
      <span style={styles.toggleKnob(enabled)} />
    </button>
  );
}

export default function RolePermissions() {
  const { getAuthHeader } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [changes, setChanges] = useState({});
  const [saving, setSaving] = useState(false);

  // Fetch permission grid
  useEffect(() => {
    const fetchPermissions = async () => {
      try {
        const response = await fetch(`${API_URL}/api/auth/role-permissions`, {
          headers: getAuthHeader(),
        });
        
        if (!response.ok) throw new Error('Failed to load permissions');
        
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPermissions();
  }, [getAuthHeader]);

  // Handle toggle
  const handleToggle = (role, permission, newValue) => {
    // Admin role_permissions can't be disabled (would lock out)
    if (role === 'admin' && permission === 'role_permissions' && !newValue) {
      return;
    }

    setChanges(prev => ({
      ...prev,
      [`${role}-${permission}`]: { role, permission, allowed: newValue },
    }));
  };

  // Get current value (with pending changes)
  const getValue = (role, permission) => {
    const changeKey = `${role}-${permission}`;
    if (changes[changeKey] !== undefined) {
      return changes[changeKey].allowed;
    }
    return data?.grid?.[role]?.[permission] ?? false;
  };

  // Save changes
  const handleSave = async () => {
    setSaving(true);
    try {
      const updates = Object.values(changes);
      
      const response = await fetch(`${API_URL}/api/auth/role-permissions`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({ updates }),
      });

      if (!response.ok) throw new Error('Failed to save changes');

      // Update local data with changes
      setData(prev => {
        const newGrid = { ...prev.grid };
        updates.forEach(({ role, permission, allowed }) => {
          if (!newGrid[role]) newGrid[role] = {};
          newGrid[role][permission] = allowed;
        });
        return { ...prev, grid: newGrid };
      });

      setChanges({});
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  // Discard changes
  const handleDiscard = () => {
    setChanges({});
  };

  // Check if permission is locked
  const isLocked = (role, permission) => {
    // Admin's role_permissions can't be disabled
    return role === 'admin' && permission === 'role_permissions';
  };

  if (loading) {
    return (
      <div style={styles.loading}>
        <span>Loading permissions...</span>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div style={styles.error}>
        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⚠️</div>
        <div>{error}</div>
      </div>
    );
  }

  const hasChanges = Object.keys(changes).length > 0;
  const { roles = [], categories = {}, labels = {}, grid = {} } = data || {};

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Role Permissions</h2>
        <p style={styles.subtitle}>
          Configure what each role can access. Changes take effect immediately after saving.
        </p>
      </div>

      <div style={styles.card}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Permission</th>
              {roles.map(role => (
                <th key={role} style={styles.thRole}>
                  <span style={styles.roleBadge(role)}>
                    {role.charAt(0).toUpperCase() + role.slice(1)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.entries(categories).map(([category, permissions]) => (
              <React.Fragment key={category}>
                {/* Category header */}
                <tr style={styles.categoryRow}>
                  <td colSpan={roles.length + 1} style={styles.categoryCell}>
                    {category}
                  </td>
                </tr>
                
                {/* Permission rows */}
                {permissions.map(permission => (
                  <tr key={permission}>
                    <td style={styles.td}>
                      {labels[permission] || permission}
                    </td>
                    {roles.map(role => (
                      <td key={role} style={styles.tdCenter}>
                        <Toggle
                          enabled={getValue(role, permission)}
                          onChange={(val) => handleToggle(role, permission, val)}
                          locked={isLocked(role, permission)}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>

        {/* Save bar */}
        {hasChanges && (
          <div style={styles.saveBar}>
            <span style={{ color: '#92400e', fontWeight: '500' }}>
              ⚠️ You have {Object.keys(changes).length} unsaved change(s)
            </span>
            <div>
              <button
                style={styles.discardButton}
                onClick={handleDiscard}
                disabled={saving}
              >
                Discard
              </button>
              <button
                style={styles.saveButton}
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
