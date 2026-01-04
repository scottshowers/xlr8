import React, { useState } from 'react';
import api from '../services/api';

/**
 * Custom Persona Creator
 * 
 * Modal for creating custom AI personas
 */
export function PersonaCreator({ isOpen, onClose, onPersonaCreated }) {
  const [formData, setFormData] = useState({
    name: '',
    icon: '🤖',
    description: '',
    system_prompt: '',
    expertise: '',
    tone: ''
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Common emoji options
  const emojiOptions = [
    '🤖', '👨‍', '👩‍', '🧑‍💻', '👨‍🏫', '👩‍🏫',
    '🦸', '🧙', '', '🦉', '🦊', '🐘', '🦁', '🐶',
    '', '', '', '', '', '', '', ''
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSaving(true);

    try {
      // Validate
      if (!formData.name || !formData.description || !formData.system_prompt) {
        throw new Error('Please fill in all required fields');
      }

      // Parse expertise (comma-separated)
      const expertiseArray = formData.expertise
        .split(',')
        .map(e => e.trim())
        .filter(e => e);

      // Create persona using api service
      const response = await api.post('/chat/personas', {
        name: formData.name,
        icon: formData.icon,
        description: formData.description,
        system_prompt: formData.system_prompt,
        expertise: expertiseArray,
        tone: formData.tone || 'Professional'
      });

      // Success - notify parent
      onPersonaCreated(response.data);
      
      // Reset form
      setFormData({
        name: '',
        icon: '🤖',
        description: '',
        system_prompt: '',
        expertise: '',
        tone: ''
      });
      
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to create persona');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <div style={styles.header}>
          <h2 style={styles.title}>Create Custom Persona</h2>
          <button style={styles.closeButton} onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          {/* Name */}
          <div style={styles.field}>
            <label style={styles.label}>
              Name <span style={styles.required}>*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              placeholder="e.g., Tech Guru, Dr. Data, Config Queen"
              style={styles.input}
              required
            />
          </div>

          {/* Icon Selector */}
          <div style={styles.field}>
            <label style={styles.label}>Icon</label>
            <div style={styles.emojiGrid}>
              {emojiOptions.map(emoji => (
                <div
                  key={emoji}
                  style={{
                    ...styles.emojiOption,
                    ...(formData.icon === emoji ? styles.emojiSelected : {})
                  }}
                  onClick={() => setFormData({...formData, icon: emoji})}
                >
                  {emoji}
                </div>
              ))}
            </div>
            <input
              type="text"
              value={formData.icon}
              onChange={(e) => setFormData({...formData, icon: e.target.value})}
              placeholder="Or paste any emoji"
              style={{...styles.input, marginTop: '10px', maxWidth: '100px'}}
            />
          </div>

          {/* Description */}
          <div style={styles.field}>
            <label style={styles.label}>
              Description <span style={styles.required}>*</span>
            </label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              placeholder="Brief description of this persona's purpose"
              style={styles.input}
              required
            />
            <div style={styles.hint}>One-line description shown in the dropdown</div>
          </div>

          {/* System Prompt */}
          <div style={styles.field}>
            <label style={styles.label}>
              System Prompt <span style={styles.required}>*</span>
            </label>
            <textarea
              value={formData.system_prompt}
              onChange={(e) => setFormData({...formData, system_prompt: e.target.value})}
              placeholder="You are [name], a [role] who [characteristics]...

Your approach:
- [How you think]
- [What you prioritize]

Your style:
- [How you communicate]"
              style={styles.textarea}
              rows={10}
              required
            />
            <div style={styles.hint}>
              Instructions that define how this persona thinks and responds
            </div>
          </div>

          {/* Expertise */}
          <div style={styles.field}>
            <label style={styles.label}>Expertise Areas</label>
            <input
              type="text"
              value={formData.expertise}
              onChange={(e) => setFormData({...formData, expertise: e.target.value})}
              placeholder="Configuration, Testing, Analysis, Training (comma-separated)"
              style={styles.input}
            />
          </div>

          {/* Tone */}
          <div style={styles.field}>
            <label style={styles.label}>Tone</label>
            <input
              type="text"
              value={formData.tone}
              onChange={(e) => setFormData({...formData, tone: e.target.value})}
              placeholder="e.g., Professional, Casual, Technical, Friendly"
              style={styles.input}
            />
          </div>

          {/* Error */}
          {error && (
            <div style={styles.error}>{error}</div>
          )}

          {/* Buttons */}
          <div style={styles.buttons}>
            <button
              type="button"
              onClick={onClose}
              style={styles.cancelButton}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="submit"
              style={styles.submitButton}
              disabled={saving}
            >
              {saving ? 'Creating...' : 'Create Persona'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2000
  },
  modal: {
    backgroundColor: 'white',
    borderRadius: '12px',
    width: '90%',
    maxWidth: '600px',
    maxHeight: '90vh',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 25px',
    borderBottom: '2px solid #e0e0e0'
  },
  title: {
    margin: 0,
    fontSize: '24px',
    fontWeight: '600',
    color: '#333'
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '24px',
    cursor: 'pointer',
    color: '#666',
    padding: '5px 10px'
  },
  form: {
    padding: '25px',
    overflowY: 'auto'
  },
  field: {
    marginBottom: '20px'
  },
  label: {
    display: 'block',
    marginBottom: '8px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#333'
  },
  required: {
    color: '#dc3545'
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    fontSize: '14px',
    border: '2px solid #e0e0e0',
    borderRadius: '6px',
    outline: 'none',
    transition: 'border 0.2s',
    ':focus': {
      borderColor: '#83b16d'
    }
  },
  textarea: {
    width: '100%',
    padding: '10px 12px',
    fontSize: '14px',
    border: '2px solid #e0e0e0',
    borderRadius: '6px',
    outline: 'none',
    fontFamily: 'monospace',
    resize: 'vertical',
    transition: 'border 0.2s',
    ':focus': {
      borderColor: '#83b16d'
    }
  },
  hint: {
    marginTop: '5px',
    fontSize: '12px',
    color: '#999',
    fontStyle: 'italic'
  },
  emojiGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(50px, 1fr))',
    gap: '8px'
  },
  emojiOption: {
    fontSize: '28px',
    padding: '10px',
    textAlign: 'center',
    cursor: 'pointer',
    borderRadius: '8px',
    border: '2px solid transparent',
    transition: 'all 0.2s',
    ':hover': {
      backgroundColor: '#f0f0f0'
    }
  },
  emojiSelected: {
    border: '2px solid #83b16d',
    backgroundColor: '#e8f5e0'
  },
  error: {
    padding: '12px',
    backgroundColor: '#fee',
    border: '1px solid #fcc',
    borderRadius: '6px',
    color: '#c33',
    fontSize: '14px',
    marginBottom: '15px'
  },
  buttons: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    marginTop: '25px',
    paddingTop: '20px',
    borderTop: '2px solid #e0e0e0'
  },
  cancelButton: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: '600',
    border: '2px solid #e0e0e0',
    backgroundColor: 'white',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  submitButton: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: '600',
    border: 'none',
    backgroundColor: '#83b16d',
    color: 'white',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    ':hover': {
      backgroundColor: '#6a9456'
    },
    ':disabled': {
      backgroundColor: '#ccc',
      cursor: 'not-allowed'
    }
  }
};

export default PersonaCreator;
