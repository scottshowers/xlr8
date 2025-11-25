import { useState, useEffect } from 'react'
import api from '../services/api'

/**
 * Persona Management Component
 * 
 * Full CRUD interface for managing AI personas
 */
export default function PersonaManagement() {
  const [personas, setPersonas] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedPersona, setSelectedPersona] = useState(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    loadPersonas()
  }, [])

  const loadPersonas = async () => {
    try {
      setLoading(true)
      const response = await api.get('/chat/personas')
      setPersonas(response.data.personas || [])
    } catch (err) {
      setError('Failed to load personas')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (personaId) => {
    if (!window.confirm('Are you sure you want to delete this persona?')) {
      return
    }

    try {
      await api.delete(`/chat/personas/${personaId}`)
      setSuccess('Persona deleted successfully')
      loadPersonas()
      setSelectedPersona(null)
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError('Failed to delete persona: ' + (err.response?.data?.detail || err.message))
    }
  }

  if (loading) {
    return (
      <div style={styles.section}>
        <div style={styles.loading}>Loading personas...</div>
      </div>
    )
  }

  return (
    <div style={styles.section}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>🎭 Persona Management</h1>
          <p style={styles.subtitle}>
            Manage AI personas - create custom personalities, edit existing ones
          </p>
        </div>
        <button
          style={styles.createButton}
          onClick={() => setIsCreating(true)}
        >
          + Create New Persona
        </button>
      </div>

      {error && (
        <div style={styles.errorBanner}>
          ❌ {error}
          <button onClick={() => setError('')} style={styles.closeBanner}>✕</button>
        </div>
      )}

      {success && (
        <div style={styles.successBanner}>
          ✅ {success}
          <button onClick={() => setSuccess('')} style={styles.closeBanner}>✕</button>
        </div>
      )}

      <div style={styles.layout}>
        {/* Persona List */}
        <div style={styles.personaList}>
          <h3 style={styles.listTitle}>All Personas ({personas.length})</h3>
          
          {personas.map(persona => (
            <button
              key={persona.id}
              style={{
                ...styles.personaCard,
                ...(selectedPersona?.id === persona.id ? styles.personaCardActive : {})
              }}
              onClick={() => {
                setSelectedPersona(persona)
                setIsEditing(false)
              }}
            >
              <div style={styles.personaIcon}>{persona.icon}</div>
              <div style={styles.personaInfo}>
                <div style={styles.personaName}>
                  {persona.name}
                  {persona.custom && <span style={styles.customBadge}>Custom</span>}
                </div>
                <div style={styles.personaDesc}>{persona.description}</div>
              </div>
            </button>
          ))}
        </div>

        {/* Details Panel */}
        <div style={styles.detailsPanel}>
          {!selectedPersona && !isCreating ? (
            <EmptyState />
          ) : isCreating ? (
            <PersonaEditor
              onSave={() => {
                setIsCreating(false)
                loadPersonas()
                setSuccess('Persona created!')
                setTimeout(() => setSuccess(''), 3000)
              }}
              onCancel={() => setIsCreating(false)}
            />
          ) : isEditing ? (
            <PersonaEditor
              persona={selectedPersona}
              onSave={() => {
                setIsEditing(false)
                loadPersonas()
                setSuccess('Persona updated!')
                setTimeout(() => setSuccess(''), 3000)
              }}
              onCancel={() => setIsEditing(false)}
            />
          ) : (
            <PersonaDetails
              persona={selectedPersona}
              onEdit={() => setIsEditing(true)}
              onDelete={handleDelete}
            />
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div style={styles.emptyState}>
      <div style={styles.emptyIcon}>🎭</div>
      <p style={styles.emptyText}>Select a persona to view details</p>
      <p style={styles.emptyHint}>or create a new one</p>
    </div>
  )
}

function PersonaDetails({ persona, onEdit, onDelete }) {
  return (
    <div style={styles.details}>
      <div style={styles.detailsHeader}>
        <div style={styles.detailsIcon}>{persona.icon}</div>
        <div style={styles.detailsHeaderInfo}>
          <h2 style={styles.detailsName}>
            {persona.name}
            {persona.custom && <span style={styles.customBadge}>Custom</span>}
          </h2>
          <p style={styles.detailsDesc}>{persona.description}</p>
        </div>
      </div>

      <div style={styles.detailsSection}>
        <h3 style={styles.sectionLabel}>Tone</h3>
        <p style={styles.sectionValue}>{persona.tone}</p>
      </div>

      <div style={styles.detailsSection}>
        <h3 style={styles.sectionLabel}>Expertise</h3>
        <div style={styles.tagList}>
          {persona.expertise.map((skill, i) => (
            <span key={i} style={styles.tag}>{skill}</span>
          ))}
        </div>
      </div>

      <div style={styles.detailsSection}>
        <h3 style={styles.sectionLabel}>System Prompt</h3>
        <pre style={styles.systemPrompt}>{persona.system_prompt || 'No system prompt'}</pre>
      </div>

      <div style={styles.detailsActions}>
        <button style={styles.editButton} onClick={onEdit}>
          ✏️ Edit Persona
        </button>
        {persona.custom && (
          <button style={styles.deleteButton} onClick={() => onDelete(persona.id)}>
            🗑️ Delete Persona
          </button>
        )}
      </div>
    </div>
  )
}

function PersonaEditor({ persona, onSave, onCancel }) {
  const [formData, setFormData] = useState({
    name: persona?.name || '',
    icon: persona?.icon || '🤖',
    description: persona?.description || '',
    system_prompt: persona?.system_prompt || '',
    expertise: persona?.expertise?.join(', ') || '',
    tone: persona?.tone || ''
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const emojis = [
    '🤖', '👨‍💼', '👩‍💼', '🧑‍💻', '👨‍🏫', '👩‍🏫',
    '🦸', '🧙', '🐮', '🦉', '🦊', '🐘', '🦁', '🐶',
    '💼', '⚡', '🚀', '🎯', '🔍', '💡', '🎓', '🏆',
    '👑', '🎨', '⚙️', '🔧', '📊', '💰', '🌟', '✨'
  ]

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)

    try {
      if (!formData.name || !formData.description || !formData.system_prompt) {
        throw new Error('Name, description, and system prompt are required')
      }

      const expertiseArray = formData.expertise
        .split(',')
        .map(e => e.trim())
        .filter(e => e)

      const payload = {
        name: formData.name,
        icon: formData.icon,
        description: formData.description,
        system_prompt: formData.system_prompt,
        expertise: expertiseArray,
        tone: formData.tone || 'Professional'
      }

      if (persona) {
        await api.put(`/chat/personas/${persona.id}`, payload)
      } else {
        await api.post('/chat/personas', payload)
      }

      onSave()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={styles.editor}>
      <h2 style={styles.editorTitle}>
        {persona ? '✏️ Edit Persona' : '+ Create New Persona'}
      </h2>

      <form onSubmit={handleSubmit} style={styles.form}>
        <div style={styles.field}>
          <label style={styles.label}>
            Name <span style={styles.required}>*</span>
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
            placeholder="e.g., Tech Guru"
            style={styles.input}
            required
          />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Icon</label>
          <div style={styles.emojiGrid}>
            {emojis.map(emoji => (
              <button
                type="button"
                key={emoji}
                style={{
                  ...styles.emojiOption,
                  ...(formData.icon === emoji ? styles.emojiSelected : {})
                }}
                onClick={() => setFormData({...formData, icon: emoji})}
              >
                {emoji}
              </button>
            ))}
          </div>
          <input
            type="text"
            value={formData.icon}
            onChange={(e) => setFormData({...formData, icon: e.target.value})}
            placeholder="Or paste emoji"
            style={{...styles.input, marginTop: '10px', maxWidth: '150px'}}
          />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>
            Description <span style={styles.required}>*</span>
          </label>
          <input
            type="text"
            value={formData.description}
            onChange={(e) => setFormData({...formData, description: e.target.value})}
            placeholder="Brief description"
            style={styles.input}
            required
          />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Tone</label>
          <input
            type="text"
            value={formData.tone}
            onChange={(e) => setFormData({...formData, tone: e.target.value})}
            placeholder="e.g., Professional, Friendly"
            style={styles.input}
          />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Expertise</label>
          <input
            type="text"
            value={formData.expertise}
            onChange={(e) => setFormData({...formData, expertise: e.target.value})}
            placeholder="Comma-separated"
            style={styles.input}
          />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>
            System Prompt <span style={styles.required}>*</span>
          </label>
          <textarea
            value={formData.system_prompt}
            onChange={(e) => setFormData({...formData, system_prompt: e.target.value})}
            placeholder="You are [name], a [role] who..."
            style={styles.textarea}
            rows={12}
            required
          />
          <div style={styles.hint}>
            This defines the persona's personality (the key!)
          </div>
        </div>

        {error && <div style={styles.errorBox}>{error}</div>}

        <div style={styles.formActions}>
          <button type="button" onClick={onCancel} style={styles.cancelButton} disabled={saving}>
            Cancel
          </button>
          <button type="submit" style={styles.saveButton} disabled={saving}>
            {saving ? 'Saving...' : (persona ? 'Save Changes' : 'Create Persona')}
          </button>
        </div>
      </form>
    </div>
  )
}

const styles = {
  section: { padding: '2rem', maxWidth: '1600px', margin: '0 auto' },
  loading: { textAlign: 'center', padding: '3rem', fontSize: '1.1rem', color: '#666' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' },
  title: { margin: '0 0 0.5rem 0', fontSize: '2rem', color: '#2a3441' },
  subtitle: { margin: 0, fontSize: '1rem', color: '#666', lineHeight: 1.5 },
  createButton: { padding: '0.75rem 1.5rem', fontSize: '1rem', fontWeight: '600', background: '#2a3441', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', transition: 'background 0.2s' },
  errorBanner: { background: '#fee', border: '1px solid #fcc', borderRadius: '8px', padding: '1rem 1.5rem', marginBottom: '1.5rem', color: '#c33', display: 'flex', justifyContent: 'space-between' },
  successBanner: { background: '#e8f5e0', border: '1px solid #83b16d', borderRadius: '8px', padding: '1rem 1.5rem', marginBottom: '1.5rem', color: '#2a3441', display: 'flex', justifyContent: 'space-between' },
  closeBanner: { background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer', color: 'inherit' },
  layout: { display: 'grid', gridTemplateColumns: '350px 1fr', gap: '2rem', minHeight: '600px' },
  personaList: { background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 2px 8px rgba(0,0,0,0.08)', maxHeight: '800px', overflowY: 'auto' },
  listTitle: { margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#2a3441' },
  personaCard: { width: '100%', display: 'flex', alignItems: 'center', gap: '1rem', padding: '1rem', marginBottom: '0.5rem', background: '#f8f9fa', border: '2px solid transparent', borderRadius: '8px', cursor: 'pointer', textAlign: 'left' },
  personaCardActive: { background: '#e8f5e0', border: '2px solid #83b16d' },
  personaIcon: { fontSize: '2.5rem', lineHeight: 1, flexShrink: 0 },
  personaInfo: { flex: 1, minWidth: 0 },
  personaName: { fontSize: '1rem', fontWeight: '600', color: '#2a3441', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' },
  personaDesc: { fontSize: '0.85rem', color: '#666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  customBadge: { fontSize: '0.7rem', padding: '2px 6px', background: '#ffc107', color: 'white', borderRadius: '3px', fontWeight: '500' },
  detailsPanel: { background: 'white', borderRadius: '12px', padding: '2rem', boxShadow: '0 2px 8px rgba(0,0,0,0.08)', maxHeight: '800px', overflowY: 'auto' },
  emptyState: { textAlign: 'center', padding: '4rem 2rem', color: '#999' },
  emptyIcon: { fontSize: '4rem', marginBottom: '1rem' },
  emptyText: { fontSize: '1.1rem', margin: '0 0 0.5rem 0' },
  emptyHint: { fontSize: '0.9rem', margin: 0 },
  details: { display: 'flex', flexDirection: 'column', gap: '2rem' },
  detailsHeader: { display: 'flex', alignItems: 'center', gap: '1.5rem', paddingBottom: '2rem', borderBottom: '2px solid #f0f0f0' },
  detailsIcon: { fontSize: '4rem', lineHeight: 1 },
  detailsHeaderInfo: { flex: 1 },
  detailsName: { margin: '0 0 0.5rem 0', fontSize: '1.75rem', color: '#2a3441', display: 'flex', alignItems: 'center', gap: '0.75rem' },
  detailsDesc: { margin: 0, fontSize: '1.05rem', color: '#666', lineHeight: 1.5 },
  detailsSection: { paddingBottom: '1.5rem', borderBottom: '1px solid #f0f0f0' },
  sectionLabel: { margin: '0 0 0.75rem 0', fontSize: '0.9rem', fontWeight: '600', color: '#999', textTransform: 'uppercase' },
  sectionValue: { margin: 0, fontSize: '1.05rem', color: '#2a3441' },
  tagList: { display: 'flex', flexWrap: 'wrap', gap: '0.5rem' },
  tag: { padding: '0.4rem 0.75rem', background: '#f0f7ed', color: '#83b16d', borderRadius: '6px', fontSize: '0.9rem', fontWeight: '500' },
  systemPrompt: { margin: 0, padding: '1rem', background: '#f8f9fa', border: '1px solid #e0e0e0', borderRadius: '8px', fontSize: '0.9rem', fontFamily: 'monospace', lineHeight: 1.6, whiteSpace: 'pre-wrap' },
  detailsActions: { display: 'flex', gap: '1rem', paddingTop: '1rem' },
  editButton: { padding: '0.75rem 1.5rem', fontSize: '1rem', fontWeight: '600', background: '#83b16d', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' },
  deleteButton: { padding: '0.75rem 1.5rem', fontSize: '1rem', fontWeight: '600', background: '#dc3545', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' },
  builtInNote: { padding: '1rem', background: '#f0f7ed', border: '1px solid #83b16d', borderRadius: '8px', color: '#666', fontSize: '0.95rem' },
  editor: { display: 'flex', flexDirection: 'column', gap: '1.5rem' },
  editorTitle: { margin: 0, fontSize: '1.5rem', color: '#2a3441', paddingBottom: '1.5rem', borderBottom: '2px solid #f0f0f0' },
  form: { display: 'flex', flexDirection: 'column', gap: '1.5rem' },
  field: { display: 'flex', flexDirection: 'column', gap: '0.5rem' },
  label: { fontSize: '0.95rem', fontWeight: '600', color: '#2a3441' },
  required: { color: '#dc3545' },
  input: { padding: '0.75rem 1rem', fontSize: '1rem', border: '2px solid #e0e0e0', borderRadius: '8px', outline: 'none' },
  textarea: { padding: '0.75rem 1rem', fontSize: '0.95rem', border: '2px solid #e0e0e0', borderRadius: '8px', outline: 'none', fontFamily: 'monospace', resize: 'vertical', lineHeight: 1.6 },
  hint: { fontSize: '0.85rem', color: '#999', fontStyle: 'italic' },
  emojiGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(50px, 1fr))', gap: '0.5rem' },
  emojiOption: { fontSize: '2rem', padding: '0.5rem', background: '#f8f9fa', border: '2px solid transparent', borderRadius: '8px', cursor: 'pointer' },
  emojiSelected: { border: '2px solid #83b16d', background: '#e8f5e0' },
  errorBox: { padding: '1rem', background: '#fee', border: '1px solid #fcc', borderRadius: '8px', color: '#c33', fontSize: '0.95rem' },
  formActions: { display: 'flex', justifyContent: 'flex-end', gap: '1rem', paddingTop: '1rem', borderBottom: '2px solid #f0f0f0' },
  cancelButton: { padding: '0.75rem 1.5rem', fontSize: '1rem', fontWeight: '600', background: 'white', color: '#666', border: '2px solid #e0e0e0', borderRadius: '8px', cursor: 'pointer' },
  saveButton: { padding: '0.75rem 1.5rem', fontSize: '1rem', fontWeight: '600', background: '#83b16d', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }
}
