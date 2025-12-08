/**
 * UserManagement - Admin component for managing users
 * 
 * Features:
 * - List all users
 * - Create new users
 * - Edit user roles
 * - Assign users to projects
 * - Delete users
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || '';

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
    fontSize: '0.85rem',
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
    background: role === 'admin' ? '#fef3c7' : role === 'consultant' ? '#dbeafe' : '#f3e8ff',
    color: role === 'admin' ? '#92400e' : role === 'consultant' ? '#1e40af' : '#6b21a8',
  }),
  actionButton: {
    padding: '0.375rem 0.75rem',
    background: 'transparent',
    border: '1px solid #e1e8ed',
    borderRadius: '6px',
    color: '#5f6c7b',
    fontSize: '0.8rem',
    cursor: 'pointer',
    marginRight: '0.5rem',
  },
  deleteButton: {
    padding: '0.375rem 0.75rem',
    background: '#fee2e2',
    border: '1px solid #fecaca',
    borderRadius: '6px',
    color: '#dc2626',
    fontSize: '0.8rem',
    cursor: 'pointer',
  },
  modal: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
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
    maxWidth: '500px',
    width: '90%',
    maxHeight: '80vh',
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
    marginBottom: '0.5rem',
    fontWeight: '500',
    color: '#2a3441',
    fontSize: '0.9rem',
  },
  input: {
    width: '100%',
    padding: '0.75rem',
    border: '1px solid #e1e8ed',
    borderRadius: '8px',
    fontSize: '1rem',
    boxSizing: 'border-box',
  },
  select: {
    width: '100%',
    padding: '0.75rem',
    border: '1px solid #e1e8ed',
    borderRadius: '8px',
    fontSize: '1rem',
    background: 'white',
  },
  modalButtons: {
    display: 'flex',
    gap: '0.75rem',
    marginTop: '1.5rem',
    justifyContent: 'flex-end',
  },
  cancelButton: {
    padding: '0.75rem 1.25rem',
    background: 'transparent',
    border: '1px solid #e1e8ed',
    borderRadius: '8px',
    color: '#5f6c7b',
    fontWeight: '600',
    cursor: 'pointer',
  },
  submitButton: {
    padding: '0.75rem 1.25rem',
    background: '#83b16d',
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    fontWeight: '600',
    cursor: 'pointer',
  },
  loading: {
    textAlign: 'center',
    padding: '3rem',
    color: '#5f6c7b',
  },
  empty: {
    textAlign: 'center',
    padding: '3rem',
    color: '#5f6c7b',
  },
};

export default function UserManagement() {
  const { getAuthHeader, user: currentUser } = useAuth();
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
    mfa_method: 'totp',  // 'totp' or 'sms'
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Fetch users
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await fetch(`${API_URL}/api/auth/users`, {
          headers: getAuthHeader(),
        });
        
        if (response.ok) {
          const data = await response.json();
          setUsers(data);
        }
      } catch (err) {
        console.error('Failed to fetch users:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, [getAuthHeader]);

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

  // Save user
  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      if (editingUser) {
        // Update existing user
        const response = await fetch(`${API_URL}/api/auth/users/${editingUser.id}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeader(),
          },
          body: JSON.stringify({
            full_name: formData.full_name,
            phone: formData.phone || null,
            role: formData.role,
            project_id: formData.project_id || null,
            mfa_method: formData.mfa_method,
          }),
        });

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || 'Failed to update user');
        }

        // Update local state
        setUsers(prev => prev.map(u => 
          u.id === editingUser.id 
            ? { ...u, full_name: formData.full_name, phone: formData.phone, role: formData.role, project_id: formData.project_id, mfa_method: formData.mfa_method }
            : u
        ));
      } else {
        // Create new user
        if (!formData.email || !formData.password) {
          throw new Error('Email and password are required');
        }

        const response = await fetch(`${API_URL}/api/auth/users`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeader(),
          },
          body: JSON.stringify(formData),
        });

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || 'Failed to create user');
        }

        const result = await response.json();
        
        // Add to local state
        setUsers(prev => [...prev, {
          id: result.user_id,
          email: formData.email,
          full_name: formData.full_name,
          role: formData.role,
          project_id: formData.project_id || null,
        }]);
      }

      setShowModal(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  // Delete user
  const handleDelete = async (userId) => {
    if (!confirm('Are you sure you want to delete this user?')) return;

    try {
      const response = await fetch(`${API_URL}/api/auth/users/${userId}`, {
        method: 'DELETE',
        headers: getAuthHeader(),
      });

      if (response.ok) {
        setUsers(prev => prev.filter(u => u.id !== userId));
      }
    } catch (err) {
      console.error('Failed to delete user:', err);
    }
  };

  if (loading) {
    return <div style={styles.loading}>Loading users...</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>User Management</h3>
        <button style={styles.addButton} onClick={handleAddUser}>
          <span>+</span> Add User
        </button>
      </div>

      {users.length === 0 ? (
        <div style={styles.empty}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>👥</div>
          <p>No users found. Click "Add User" to create the first one.</p>
        </div>
      ) : (
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
            {users.map(user => (
              <tr key={user.id}>
                <td style={styles.td}>{user.full_name || '—'}</td>
                <td style={styles.td}>{user.email}</td>
                <td style={styles.td}>
                  <span style={styles.roleBadge(user.role)}>
                    {user.role}
                  </span>
                </td>
                <td style={styles.td}>
                  {user.mfa_method === 'sms' ? '💬 SMS' : '📱 App'}
                </td>
                <td style={styles.td}>
                  <button 
                    style={styles.actionButton}
                    onClick={() => handleEditUser(user)}
                  >
                    Edit
                  </button>
                  {user.id !== currentUser?.id && (
                    <button 
                      style={styles.deleteButton}
                      onClick={() => handleDelete(user.id)}
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Modal */}
      {showModal && (
        <div style={styles.modal} onClick={() => setShowModal(false)}>
          <div style={styles.modalContent} onClick={e => e.stopPropagation()}>
            <h3 style={styles.modalTitle}>
              {editingUser ? 'Edit User' : 'Add New User'}
            </h3>

            {error && (
              <div style={{ 
                padding: '0.75rem', 
                background: '#fee2e2', 
                color: '#dc2626', 
                borderRadius: '8px',
                marginBottom: '1rem',
                fontSize: '0.9rem',
              }}>
                {error}
              </div>
            )}

            <div style={styles.formGroup}>
              <label style={styles.label}>Email</label>
              <input
                type="email"
                style={styles.input}
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
              <small style={{ color: '#5f6c7b', fontSize: '0.8rem' }}>
                Required if using SMS for two-factor authentication
              </small>
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>MFA Method</label>
              <select
                style={styles.select}
                value={formData.mfa_method}
                onChange={e => setFormData(prev => ({ ...prev, mfa_method: e.target.value }))}
              >
                <option value="totp">📱 Authenticator App (TOTP)</option>
                <option value="sms">💬 SMS Text Message</option>
              </select>
              <small style={{ color: '#5f6c7b', fontSize: '0.8rem' }}>
                {formData.mfa_method === 'totp' 
                  ? 'Uses Google Authenticator, Authy, or similar apps'
                  : 'Sends a code via text message (requires phone number)'
                }
              </small>
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
