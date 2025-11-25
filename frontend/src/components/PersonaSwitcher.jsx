import React, { useState, useEffect } from 'react';
import api from '../services/api';  // FIXED: Import api service

/**
 * Persona Switcher Component
 * 
 * Displays current persona and allows switching between personas
 */
export function PersonaSwitcher({ currentPersona, onPersonaChange }) {
  const [personas, setPersonas] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPersonas();
  }, []);

  const fetchPersonas = async () => {
    try {
      const response = await api.get('/chat/personas');  // FIXED: Use api service
      setPersonas(response.data.personas || []);
    } catch (error) {
      console.error('Error fetching personas:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (personaId) => {
    onPersonaChange(personaId);
    setIsOpen(false);
  };

  const currentP = personas.find(p => p.id === currentPersona) || personas[0];

  if (loading || !currentP) {
    return <div style={styles.loading}>Loading personas...</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.label}>Assistant:</div>
      
      {/* Current Persona Display */}
      <div 
        style={styles.current}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span style={styles.icon}>{currentP.icon}</span>
        <span style={styles.name}>{currentP.name}</span>
        <span style={styles.arrow}>{isOpen ? '▲' : '▼'}</span>
      </div>

      {/* Dropdown Menu */}
      {isOpen && (
        <div style={styles.dropdown}>
          {personas.map(persona => (
            <div
              key={persona.id}
              style={{
                ...styles.option,
                ...(persona.id === currentPersona ? styles.optionActive : {})
              }}
              onClick={() => handleSelect(persona.id)}
            >
              <span style={styles.optionIcon}>{persona.icon}</span>
              <div style={styles.optionContent}>
                <div style={styles.optionName}>
                  {persona.name}
                  {persona.custom && <span style={styles.customBadge}>Custom</span>}
                </div>
                <div style={styles.optionDesc}>{persona.description}</div>
                <div style={styles.optionExpertise}>
                  {persona.expertise.slice(0, 3).join(' • ')}
                </div>
              </div>
            </div>
          ))}
          
          {/* Create New Persona Button */}
          <div 
            style={styles.createButton}
            onClick={() => window.openPersonaCreator && window.openPersonaCreator()}
          >
            <span style={styles.optionIcon}>➕</span>
            <span style={styles.createText}>Create Custom Persona</span>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {isOpen && (
        <div 
          style={styles.overlay}
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}

const styles = {
  container: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '20px',
    zIndex: 1000
  },
  label: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#666'
  },
  current: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 15px',
    backgroundColor: '#f8f9fa',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    ':hover': {
      borderColor: '#83b16d',
      backgroundColor: '#f0f7ed'
    }
  },
  icon: {
    fontSize: '24px',
    lineHeight: 1
  },
  name: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#333'
  },
  arrow: {
    fontSize: '12px',
    color: '#666',
    marginLeft: '5px'
  },
  dropdown: {
    position: 'absolute',
    top: '100%',
    left: '80px',
    marginTop: '5px',
    backgroundColor: 'white',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
    minWidth: '400px',
    maxHeight: '500px',
    overflowY: 'auto',
    zIndex: 1001
  },
  option: {
    display: 'flex',
    gap: '12px',
    padding: '15px',
    cursor: 'pointer',
    borderBottom: '1px solid #f0f0f0',
    transition: 'background 0.2s',
    ':hover': {
      backgroundColor: '#f8f9fa'
    }
  },
  optionActive: {
    backgroundColor: '#e8f5e0',
    borderLeft: '4px solid #83b16d'
  },
  optionIcon: {
    fontSize: '32px',
    lineHeight: 1,
    flexShrink: 0
  },
  optionContent: {
    flex: 1
  },
  optionName: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#333',
    marginBottom: '4px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  customBadge: {
    fontSize: '11px',
    padding: '2px 6px',
    backgroundColor: '#ffc107',
    color: 'white',
    borderRadius: '3px',
    fontWeight: '500'
  },
  optionDesc: {
    fontSize: '13px',
    color: '#666',
    marginBottom: '6px',
    lineHeight: 1.4
  },
  optionExpertise: {
    fontSize: '11px',
    color: '#999',
    fontStyle: 'italic'
  },
  createButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '15px',
    cursor: 'pointer',
    backgroundColor: '#f0f7ed',
    borderTop: '2px solid #e0e0e0',
    ':hover': {
      backgroundColor: '#e8f5e0'
    }
  },
  createText: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#83b16d'
  },
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 999
  },
  loading: {
    padding: '10px 15px',
    color: '#666',
    fontSize: '14px'
  }
};

export default PersonaSwitcher;
