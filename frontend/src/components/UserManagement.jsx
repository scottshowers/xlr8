/**
 * UserManagement - Admin component for managing users
 * 
 * Reads directly from Supabase profiles table
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

// Styles
const styles = {
  container: {
    padding: '1rem',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1.5rem',
  },
  title: {
    fontSize: '1.25rem',
    fontWeight: '600',
    color: '#2a3441',
    margin: 0,
  },
  addButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.625rem 1rem',
    background: '#83b16d',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    background: 'white',
    borderRadius: '12px',
    overflow: 'hidden',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
  },
  th: {
    padding: '1rem',
    textAlign: 'left',
    background: '#fafbfc',
    borderBottom: '2px solid #e1e8ed',
    fontWeight: '600',
    color: '#2a3441',
    fontSize: '0.8rem',
  },
  td: {
    padding: '1rem',
    borderBottom: '1px solid #e1e8ed',
    color: '#2a3441',
  },
  roleBadge: (role) => ({
    display: 'inline-block',
    padding: '0.25rem 0.75rem',
    borderRadius: '999px',
    fontSize: '0.75rem',
    fontWeight: '600',
    background: role === 'admin' ? 'rgba(138, 107, 74, 0.15)' : role === 'consultant' ? 'rgba(74, 107, 138, 0.15)' : 'rgba(107, 90, 122, 0.15)',
    color: role === 'admin' ? '#d97706' : role === 'consultant' ? '#285390' : '#6b5a7a',
  }),
  actionButton: {
    padding: '0.375rem 0.75rem',
    fontSize: '0.8rem',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    marginRight: '0.5rem',
  },
  editButton: {
    background: 'rgba(74, 107, 138, 0.15)',
    color: '#285390',
  },
  deleteButton: {
    background: 'rgba(138, 74, 74, 0.15)',
    color: '#993c44',
  },
  modal: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modalContent: {
    background: 'white',
    borderRadius: '16px',
    padding: '2rem',
    width: '100%',
    maxWidth: '450px',
    maxHeight: '90vh',
    overflow: 'auto',
  },
  modalTitle: {
    fontSize: '1.25rem',
    fontWeight: '600',
    color: '#2a3441',
    marginBottom: '1.5rem',
  },
  formGroup: {
    marginBottom: '1rem',
  },
  label: {
    display: 'block',
    fontSize: '0.8rem',
    fontWeight: '600',
    color: '#5f6c7b',
    marginBottom: '0.375rem',
  },
  input: {
    width: '100%',
    padding: '0.75rem',
    fontSize: '0.95rem',
    border: '1px solid #e1e8ed',
    borderRadius: '8px',
    boxSizing: 'border-box',
  },
  select: {
    width: '100%',
    padding: '0.75rem',
    fontSize: '0.95rem',
    border: '1px solid #e1e8ed',
    borderRadius: '8px',
    background: 'white',
    boxSizing: 'border-box',
  },
  modalButtons: {
    display: 'flex',
    gap: '0.75rem',
    marginTop: '1.5rem',
  },
  cancelButton: {
    flex: 1,
    padding: '0.75rem',
    fontSize: '0.95rem',
    fontWeight: '600',
    border: '1px solid #e1e8ed',
    borderRadius: '8px',
    background: 'white',
    color: '#5f6c7b',
    cursor: 'pointer',
  },
  submitButton: {
    flex: 1,
    padding: '0.75rem',
    fontSize: '0.95rem',
    fontWeight: '600',
    border: 'none',
    borderRadius: '8px',
    background: '#83b16d',
    color: 'white',
    cursor: 'pointer',
  },
  error: {
    background: 'rgba(138, 74, 74, 0.1)',
    border: '1px solid rgba(138, 74, 74, 0.3)',
    color: '#993c44',
    padding: '0.75rem',
    borderRadius: '8px',
    marginBottom: '1rem',
    fontSize: '0.875rem',
  },
  empty: {
    textAlign: 'center',
    padding: '3rem',
    color: '#5f6c7b',
  },
};

export default function UserManagement() {
  const { user: currentUser, supabase, isAdmin } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    phone: '',
    role: 'customer',
    project_id: '',
    mfa_method: 'totp',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Fetch users from backend API
  useEffect(() => {
    const fetchUsers = async () => {
      if (!isAdmin || !supabase) {
        setLoading(false);
        return;
      }

      try {
        // Get current session for auth token
        const { data: { session } } = await supabase.auth.getSession();
        if (!session?.access_token) {
          setError('Authentication required');
          setLoading(false);
          return;
        }

        const response = await api.get('/auth/users', {
          headers: {
            'Authorization': `Bearer ${session.access_token}`
          }
        });
        setUsers(response.data || []);
      } catch (err) {
        console.error('Failed to fetch users:', err);
        setError(err.response?.data?.detail || 'Failed to load users');
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, [isAdmin, supabase]);

  // Open modal for new user
  const handleAddUser = () => {
    setEditingUser(null);
    setFormData({
      email: '',
      password: '',
      full_name: '',
      phone: '',
      role: 'customer',
      project_id: '',
      mfa_method: 'totp',
    });
    setError(null);
    setShowModal(true);
  };

  // Open modal for editing
  const handleEditUser = (user) => {
    setEditingUser(user);
    setFormData({
      email: user.email,
      password: '',
      full_name: user.full_name || '',
      phone: user.phone || '',
      role: user.role,
      project_id: user.project_id || '',
      mfa_method: user.mfa_method || 'totp',
    });
    setError(null);
    setShowModal(true);
  };

  // Save user (create or update)
  const handleSave = async () => {
    if (!supabase) return;
    
    setSaving(true);
    setError(null);

    try {
      // Get auth token
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        setError('Authentication required');
        setSaving(false);
        return;
      }
      const authHeaders = { 'Authorization': `Bearer ${session.access_token}` };

      if (editingUser) {
        // Update existing user via backend API
        const response = await api.patch(`/auth/users/${editingUser.id}`, {
          full_name: formData.full_name,
          phone: formData.phone || null,
          role: formData.role,
          project_id: formData.project_id || null,
          mfa_method: formData.mfa_method,
        }, { headers: authHeaders });

        if (response.data?.status === 'updated') {
          // Update local state
          setUsers(prev => prev.map(u => 
            u.id === editingUser.id 
              ? { ...u, ...formData, updated_at: new Date().toISOString() }
              : u
          ));
        }
      } else {
        // Create new user via backend API
        if (!formData.email || !formData.password) {
          setError('Email and password are required');
          setSaving(false);
          return;
        }

        const response = await api.post('/auth/users', {
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name,
          phone: formData.phone || null,
          role: formData.role,
          project_id: formData.project_id || null,
          mfa_method: formData.mfa_method,
        }, { headers: authHeaders });

        if (response.data?.status === 'created') {
          // Add new user to local state
          setUsers(prev => [...prev, {
            id: response.data.user_id,
            email: formData.email,
            full_name: formData.full_name,
            phone: formData.phone,
            role: formData.role,
            project_id: formData.project_id,
            mfa_method: formData.mfa_method,
            created_at: new Date().toISOString(),
          }]);
        }
      }

      setShowModal(false);
    } catch (err) {
      console.error('Save error:', err);
      const message = err.response?.data?.detail || err.message || 'Failed to save user';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  // Delete user
  const handleDelete = async (userId) => {
    if (!supabase) return;
    
    if (userId === currentUser?.id) {
      setError("You can't delete yourself");
      return;
    }

    if (!window.confirm('Are you sure you want to delete this user? This will remove them from the system.')) {
      return;
    }

    try {
      // Get auth token
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        setError('Authentication required');
        return;
      }

      await api.delete(`/auth/users/${userId}`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      });
      setUsers(prev => prev.filter(u => u.id !== userId));
    } catch (err) {
      console.error('Delete error:', err);
      const message = err.response?.data?.detail || err.message || 'Failed to delete user';
      setError(message);
    }
  };

  if (!isAdmin) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>Access denied. Admin role required.</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.empty}>Loading users...</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>User Management</h2>
        <button style={styles.addButton} onClick={handleAddUser}>
          + Add User
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Name</th>
            <th style={styles.th}>Email</th>
            <th style={styles.th}>Role</th>
            <th style={styles.th}>MFA</th>
            <th style={styles.th}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.length === 0 ? (
            <tr>
              <td colSpan={5} style={styles.empty}>No users found</td>
            </tr>
          ) : (
            users.map(user => (
              <tr key={user.id}>
                <td style={styles.td}>{user.full_name || '—'}</td>
                <td style={styles.td}>{user.email}</td>
                <td style={styles.td}>
                  <span style={styles.roleBadge(user.role)}>
                    {user.role}
                  </span>
                </td>
                <td style={styles.td}>
                  {user.mfa_method === 'sms' ? ' SMS' : '📱 App'}
                </td>
                <td style={styles.td}>
                  <button
                    style={{ ...styles.actionButton, ...styles.editButton }}
                    onClick={() => handleEditUser(user)}
                  >
                    Edit
                  </button>
                  {user.id !== currentUser?.id && (
                    <button
                      style={{ ...styles.actionButton, ...styles.deleteButton }}
                      onClick={() => handleDelete(user.id)}
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* Modal */}
      {showModal && (
        <div style={styles.modal} onClick={() => setShowModal(false)}>
          <div style={styles.modalContent} onClick={e => e.stopPropagation()}>
            <h3 style={styles.modalTitle}>
              {editingUser ? 'Edit User' : 'Add User'}
            </h3>

            {error && <div style={styles.error}>{error}</div>}

            <div style={styles.formGroup}>
              <label style={styles.label}>Email</label>
              <input
                type="email"
                style={{ ...styles.input, background: editingUser ? '#f5f5f5' : 'white' }}
                value={formData.email}
                onChange={e => setFormData(prev => ({ ...prev, email: e.target.value }))}
                disabled={!!editingUser}
                placeholder="user@example.com"
              />
            </div>

            {!editingUser && (
              <div style={styles.formGroup}>
                <label style={styles.label}>Password</label>
                <input
                  type="password"
                  style={styles.input}
                  value={formData.password}
                  onChange={e => setFormData(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="••••••••"
                />
              </div>
            )}

            <div style={styles.formGroup}>
              <label style={styles.label}>Full Name</label>
              <input
                type="text"
                style={styles.input}
                value={formData.full_name}
                onChange={e => setFormData(prev => ({ ...prev, full_name: e.target.value }))}
                placeholder="John Doe"
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Role</label>
              <select
                style={styles.select}
                value={formData.role}
                onChange={e => setFormData(prev => ({ ...prev, role: e.target.value }))}
              >
                <option value="admin">Admin</option>
                <option value="consultant">Consultant</option>
                <option value="customer">Customer</option>
              </select>
            </div>

            {formData.role === 'customer' && (
              <div style={styles.formGroup}>
                <label style={styles.label}>Project ID</label>
                <input
                  type="text"
                  style={styles.input}
                  value={formData.project_id}
                  onChange={e => setFormData(prev => ({ ...prev, project_id: e.target.value }))}
                  placeholder="proj-123"
                />
                <small style={{ color: '#5f6c7b', fontSize: '0.8rem' }}>
                  Customers can only access their assigned project
                </small>
              </div>
            )}

            <div style={styles.formGroup}>
              <label style={styles.label}>Phone Number (for SMS MFA)</label>
              <input
                type="tel"
                style={styles.input}
                value={formData.phone}
                onChange={e => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                placeholder="+1 555-123-4567"
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>MFA Method</label>
              <select
                style={styles.select}
                value={formData.mfa_method}
                onChange={e => setFormData(prev => ({ ...prev, mfa_method: e.target.value }))}
              >
                <option value="totp">📱 Authenticator App (TOTP)</option>
                <option value="sms"> SMS Text Message</option>
              </select>
            </div>

            <div style={styles.modalButtons}>
              <button 
                style={styles.cancelButton}
                onClick={() => setShowModal(false)}
                disabled={saving}
              >
                Cancel
              </button>
              <button 
                style={styles.submitButton}
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Saving...' : (editingUser ? 'Update' : 'Create User')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
