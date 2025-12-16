/**
 * PlaybookStandardsLinker
 * 
 * UI component for linking standards (compliance documents) to playbooks.
 * When a playbook runs, it uses rules from linked standards for compliance checks.
 * 
 * Usage:
 * <PlaybookStandardsLinker playbook_id="secure-2.0" onUpdate={handleUpdate} />
 */

import React, { useState, useEffect } from 'react'
import { 
  FileText, 
  Link2, 
  Unlink, 
  Plus, 
  Check, 
  AlertCircle,
  BookOpen,
  Shield,
  ChevronDown,
  ChevronUp,
  RefreshCw
} from 'lucide-react'
import api from '../services/api'

// Brand colors
const COLORS = {
  grassGreen: '#83b16d',
  grassGreenDark: '#6a9a54',
  skyBlue: '#93abd9',
  text: '#2a3441',
  textLight: '#5f6c7b',
}

export default function PlaybookStandardsLinker({ playbook_id, onUpdate }) {
  const [linkedStandards, setLinkedStandards] = useState([])
  const [availableStandards, setAvailableStandards] = useState([])
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [linking, setLinking] = useState(false)
  const [showAvailable, setShowAvailable] = useState(false)
  const [showRules, setShowRules] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (playbook_id) {
      loadData()
    }
  }, [playbook_id])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Load linked standards
      const linkedRes = await api.get(`/playbooks/${playbook_id}/standards`)
      setLinkedStandards(linkedRes.data.linked_standards || [])
      
      // Load available standards
      const availRes = await api.get('/playbooks/available-standards')
      setAvailableStandards(availRes.data.standards || [])
      
      // Load rules
      const infoRes = await api.get(`/playbooks/${playbook_id}/info`)
      setRules(infoRes.data.rules || [])
      
    } catch (err) {
      console.error('Failed to load standards:', err)
      setError('Failed to load standards')
    } finally {
      setLoading(false)
    }
  }

  const handleLink = async (standardId) => {
    setLinking(true)
    try {
      await api.post(`/playbooks/${playbook_id}/standards`, {
        standard_id: standardId,
        usage_type: 'compliance'
      })
      await loadData()
      onUpdate?.()
    } catch (err) {
      console.error('Failed to link standard:', err)
      setError('Failed to link standard')
    } finally {
      setLinking(false)
    }
  }

  const handleUnlink = async (standardId) => {
    try {
      await api.delete(`/playbooks/${playbook_id}/standards/${standardId}`)
      await loadData()
      onUpdate?.()
    } catch (err) {
      console.error('Failed to unlink standard:', err)
      setError('Failed to unlink standard')
    }
  }

  // Filter out already linked standards
  const linkedIds = linkedStandards.map(ls => ls.standard_id)
  const unlinkedStandards = availableStandards.filter(s => !linkedIds.includes(s.id))

  const styles = {
    container: {
      background: 'white',
      borderRadius: '14px',
      border: '1px solid #e8ecef',
      overflow: 'hidden',
    },
    header: {
      padding: '1.25rem',
      borderBottom: '1px solid #e8ecef',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    headerLeft: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
    },
    icon: {
      width: '40px',
      height: '40px',
      borderRadius: '10px',
      background: `linear-gradient(135deg, ${COLORS.skyBlue} 0%, #7b9acc 100%)`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    },
    title: {
      margin: 0,
      fontSize: '1rem',
      fontWeight: '700',
      color: COLORS.text,
    },
    subtitle: {
      margin: 0,
      fontSize: '0.8rem',
      color: COLORS.textLight,
    },
    badge: {
      padding: '0.35rem 0.75rem',
      background: rules.length > 0 ? '#dcfce7' : '#f3f4f6',
      color: rules.length > 0 ? '#166534' : COLORS.textLight,
      borderRadius: '20px',
      fontSize: '0.75rem',
      fontWeight: '600',
    },
    body: {
      padding: '1.25rem',
    },
    section: {
      marginBottom: '1.25rem',
    },
    sectionHeader: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '0.75rem',
      cursor: 'pointer',
    },
    sectionTitle: {
      fontSize: '0.85rem',
      fontWeight: '600',
      color: COLORS.text,
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    },
    linkedList: {
      display: 'flex',
      flexDirection: 'column',
      gap: '0.5rem',
    },
    linkedItem: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.75rem 1rem',
      background: '#f8faf9',
      borderRadius: '10px',
      border: '1px solid #e8ecef',
    },
    linkedInfo: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
    },
    linkedIcon: {
      width: '32px',
      height: '32px',
      borderRadius: '8px',
      background: COLORS.grassGreen,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    },
    linkedName: {
      fontWeight: '600',
      fontSize: '0.9rem',
      color: COLORS.text,
    },
    linkedDomain: {
      fontSize: '0.75rem',
      color: COLORS.textLight,
      textTransform: 'uppercase',
    },
    unlinkBtn: {
      padding: '0.4rem 0.75rem',
      background: 'white',
      border: '1px solid #e8ecef',
      borderRadius: '6px',
      color: '#dc2626',
      cursor: 'pointer',
      fontSize: '0.8rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.35rem',
    },
    addBtn: {
      width: '100%',
      padding: '0.75rem',
      background: showAvailable ? '#f0f4f7' : 'white',
      border: '2px dashed #d1d5db',
      borderRadius: '10px',
      color: COLORS.textLight,
      cursor: 'pointer',
      fontSize: '0.85rem',
      fontWeight: '600',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.5rem',
      transition: 'all 0.2s',
    },
    dropdown: {
      marginTop: '0.75rem',
      background: '#f8faf9',
      borderRadius: '10px',
      border: '1px solid #e8ecef',
      maxHeight: '200px',
      overflow: 'auto',
    },
    dropdownItem: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.75rem 1rem',
      borderBottom: '1px solid #e8ecef',
      cursor: 'pointer',
      transition: 'background 0.2s',
    },
    linkBtn: {
      padding: '0.35rem 0.75rem',
      background: COLORS.grassGreen,
      border: 'none',
      borderRadius: '6px',
      color: 'white',
      cursor: 'pointer',
      fontSize: '0.8rem',
      fontWeight: '600',
      display: 'flex',
      alignItems: 'center',
      gap: '0.35rem',
    },
    rulesList: {
      maxHeight: '200px',
      overflow: 'auto',
      background: '#f8faf9',
      borderRadius: '10px',
      border: '1px solid #e8ecef',
    },
    ruleItem: {
      padding: '0.65rem 1rem',
      borderBottom: '1px solid #e8ecef',
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
    },
    ruleSeverity: (severity) => ({
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      background: {
        critical: '#dc2626',
        high: '#f97316',
        medium: '#eab308',
        low: '#22c55e'
      }[severity] || '#9ca3af',
      flexShrink: 0,
    }),
    ruleTitle: {
      fontSize: '0.85rem',
      color: COLORS.text,
      flex: 1,
    },
    ruleSource: {
      fontSize: '0.7rem',
      color: COLORS.textLight,
    },
    empty: {
      padding: '2rem',
      textAlign: 'center',
      color: COLORS.textLight,
    },
    error: {
      padding: '0.75rem 1rem',
      background: '#fef2f2',
      border: '1px solid #fecaca',
      borderRadius: '8px',
      color: '#dc2626',
      fontSize: '0.85rem',
      marginBottom: '1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    }
  }

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={{ ...styles.body, textAlign: 'center', padding: '2rem' }}>
          <RefreshCw size={24} color={COLORS.textLight} style={{ animation: 'spin 1s linear infinite' }} />
          <p style={{ color: COLORS.textLight, marginTop: '0.5rem' }}>Loading standards...</p>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.icon}>
            <Shield size={20} color="white" />
          </div>
          <div>
            <h3 style={styles.title}>Linked Standards</h3>
            <p style={styles.subtitle}>Compliance rules used by this playbook</p>
          </div>
        </div>
        <span style={styles.badge}>
          {rules.length} rules
        </span>
      </div>

      {/* Body */}
      <div style={styles.body}>
        {/* Error */}
        {error && (
          <div style={styles.error}>
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {/* Linked Standards */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <Link2 size={16} />
            Active Standards ({linkedStandards.length})
          </div>
          
          {linkedStandards.length > 0 ? (
            <div style={styles.linkedList}>
              {linkedStandards.map(ls => (
                <div key={ls.standard_id} style={styles.linkedItem}>
                  <div style={styles.linkedInfo}>
                    <div style={styles.linkedIcon}>
                      <FileText size={16} color="white" />
                    </div>
                    <div>
                      <div style={styles.linkedName}>
                        {ls.standard?.title || ls.standard?.filename || `Standard ${ls.standard_id}`}
                      </div>
                      <div style={styles.linkedDomain}>
                        {ls.standard?.domain || 'General'}
                      </div>
                    </div>
                  </div>
                  <button 
                    style={styles.unlinkBtn}
                    onClick={() => handleUnlink(ls.standard_id)}
                  >
                    <Unlink size={14} />
                    Unlink
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div style={styles.empty}>
              <BookOpen size={32} color="#d1d5db" />
              <p>No standards linked yet</p>
              <p style={{ fontSize: '0.8rem' }}>Link a standard to enable compliance checking</p>
            </div>
          )}

          {/* Add Standard */}
          <button 
            style={styles.addBtn}
            onClick={() => setShowAvailable(!showAvailable)}
          >
            <Plus size={18} />
            Link a Standard
            {showAvailable ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {showAvailable && (
            <div style={styles.dropdown}>
              {unlinkedStandards.length > 0 ? (
                unlinkedStandards.map(s => (
                  <div 
                    key={s.id} 
                    style={styles.dropdownItem}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f0f4f7'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <div>
                      <div style={{ fontWeight: '600', fontSize: '0.9rem', color: COLORS.text }}>
                        {s.title || s.filename}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: COLORS.textLight }}>
                        {s.domain || 'General'}
                      </div>
                    </div>
                    <button 
                      style={styles.linkBtn}
                      onClick={() => handleLink(s.id)}
                      disabled={linking}
                    >
                      <Link2 size={14} />
                      Link
                    </button>
                  </div>
                ))
              ) : (
                <div style={{ padding: '1rem', textAlign: 'center', color: COLORS.textLight }}>
                  No more standards available
                </div>
              )}
            </div>
          )}
        </div>

        {/* Rules Preview */}
        {rules.length > 0 && (
          <div style={styles.section}>
            <div 
              style={{ ...styles.sectionHeader }}
              onClick={() => setShowRules(!showRules)}
            >
              <div style={styles.sectionTitle}>
                <Check size={16} />
                Rules ({rules.length})
              </div>
              {showRules ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>

            {showRules && (
              <div style={styles.rulesList}>
                {rules.map((rule, i) => (
                  <div key={i} style={styles.ruleItem}>
                    <div style={styles.ruleSeverity(rule.severity)} title={rule.severity} />
                    <div style={{ flex: 1 }}>
                      <div style={styles.ruleTitle}>{rule.title}</div>
                      <div style={styles.ruleSource}>{rule.source}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
