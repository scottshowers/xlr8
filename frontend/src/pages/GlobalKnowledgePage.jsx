/**
 * GlobalKnowledgePage.jsx - Global Knowledge Base
 * 
 * Unified admin page for cross-project knowledge:
 * - Regulatory & Compliance (laws, IRS pubs, audit requirements)
 * - Vendor Documentation (product guides, configuration manuals)
 * 
 * Styled to match DataPage for consistency.
 * Phase 4A UX Overhaul - January 2026
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useUpload } from '../context/UploadContext';
import api from '../services/api';
import {
  Scale, BookOpen, Upload, FileText, Trash2, RefreshCw,
  CheckCircle, XCircle, Loader2, ChevronDown, ChevronRight,
  FolderOpen, Database
} from 'lucide-react';

// =============================================================================
// KNOWLEDGE CATEGORIES
// =============================================================================

const CATEGORIES = {
  regulatory: {
    id: 'regulatory',
    label: 'Regulatory & Compliance',
    shortLabel: 'Regulatory',
    description: 'Federal, state, and local regulations. IRS publications, DOL guidelines, audit requirements.',
    icon: Scale,
    color: 'var(--scarlet)',
    truthType: 'regulatory',
    examples: ['IRS Pub 15', 'State Tax Guides', 'SOC 2 Controls', 'FLSA Requirements']
  },
  reference: {
    id: 'reference',
    label: 'Vendor Documentation',
    shortLabel: 'Vendor Docs',
    description: 'Product documentation, configuration guides, best practices from software vendors.',
    icon: BookOpen,
    color: 'var(--electric-blue)',
    truthType: 'reference',
    examples: ['UKG Pro Guides', 'Workday Config', 'ADP Manuals', 'Ceridian Docs']
  }
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function GlobalKnowledgePage() {
  const [activeCategory, setActiveCategory] = useState('regulatory');
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedSections, setExpandedSections] = useState({ documents: true });
  const fileInputRef = useRef(null);
  const { addUpload, uploads } = useUpload();

  // Load documents
  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/files', {
        params: { scope: 'global' }
      });
      
      const docs = response.data?.documents || response.data?.files || [];
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents:', err);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Filter documents by category
  const filteredDocs = documents.filter(doc => {
    return doc.truth_type === CATEGORIES[activeCategory].truthType;
  });

  // Handle file upload
  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    files.forEach(file => {
      addUpload(file, null, 'Global Knowledge', {
        truth_type: CATEGORIES[activeCategory].truthType,
        domain: activeCategory
      });
    });
    e.target.value = '';
  };

  // Handle delete
  const handleDelete = async (doc) => {
    if (!window.confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return;
    
    try {
      await api.delete(`/files/${encodeURIComponent(doc.filename)}`, {
        params: { scope: 'global' }
      });
      loadDocuments();
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete document');
    }
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const category = CATEGORIES[activeCategory];
  const CategoryIcon = category.icon;

  // Active uploads for this category
  const activeUploads = uploads.filter(u => 
    u.status === 'uploading' || u.status === 'processing'
  );

  return (
    <div style={{ padding: '0' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ 
            margin: 0, 
            fontSize: '20px', 
            fontWeight: 600, 
            color: 'var(--text-primary)', 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px',
            fontFamily: "'Sora', var(--font-body)"
          }}>
            <div style={{ 
              width: '36px', 
              height: '36px', 
              borderRadius: '10px', 
              backgroundColor: 'var(--grass-green)', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}>
              <BookOpen size={20} color="#ffffff" />
            </div>
            Global Knowledge
          </h1>
          <p style={{ margin: '6px 0 0 46px', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
            Cross-project reference materials for compliance and configuration
          </p>
        </div>
        
        <button 
          onClick={loadDocuments}
          style={{ 
            display: 'flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.5rem 1rem', 
            background: 'var(--bg-secondary)', 
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)', 
            color: 'var(--text-secondary)', 
            fontSize: 'var(--text-sm)', 
            cursor: 'pointer',
            fontFamily: 'var(--font-body)'
          }}
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Category Tabs */}
      <div style={{ 
        display: 'flex', 
        gap: 'var(--space-1)', 
        marginBottom: 'var(--space-6)',
        background: 'var(--bg-tertiary)',
        padding: 'var(--space-1)',
        borderRadius: 'var(--radius-lg)',
        width: 'fit-content'
      }}>
        {Object.values(CATEGORIES).map(cat => {
          const Icon = cat.icon;
          const isActive = activeCategory === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                padding: 'var(--space-2) var(--space-4)',
                border: 'none',
                background: isActive ? 'var(--bg-secondary)' : 'transparent',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--text-sm)',
                fontWeight: 500,
                color: isActive ? 'var(--grass-green)' : 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.15s',
                fontFamily: 'var(--font-body)',
                boxShadow: isActive ? 'var(--shadow-sm)' : 'none'
              }}
            >
              <Icon size={16} />
              <span>{cat.label}</span>
            </button>
          );
        })}
      </div>

      {/* Two Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 'var(--space-6)' }}>
        {/* Left Panel - Upload */}
        <div style={{ 
          position: 'sticky', 
          top: '1rem',
          background: 'var(--bg-secondary)', 
          border: '1px solid var(--border)', 
          borderRadius: '12px',
          boxShadow: 'var(--shadow-sm)'
        }}>
          {/* Header with grey background */}
          <div style={{ 
            padding: '1rem', 
            background: 'var(--bg-tertiary)',
            borderTopLeftRadius: '12px',
            borderTopRightRadius: '12px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)'
          }}>
            <CategoryIcon size={18} style={{ color: category.color }} />
            <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--text-primary)', fontFamily: 'var(--font-body)' }}>
              Upload {category.shortLabel}
            </span>
          </div>

          <div style={{ padding: '1rem' }}>
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)', lineHeight: 1.6 }}>
              {category.description}
            </p>

            {/* Upload Zone */}
            <div
              onClick={() => fileInputRef.current?.click()}
              style={{ 
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 'var(--space-6)',
                border: '2px dashed var(--border)',
                borderRadius: 'var(--radius-lg)',
                background: 'var(--bg-tertiary)',
                cursor: 'pointer',
                transition: 'all 0.15s',
                marginBottom: 'var(--space-4)'
              }}
            >
              <Upload size={24} style={{ color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }} />
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                Drop files here or click to browse
              </span>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-1)' }}>
                PDF, DOCX supported
              </span>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.doc"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
            </div>

            {/* Examples */}
            <div>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Examples
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
                {category.examples.map(ex => (
                  <span key={ex} style={{
                    padding: '2px var(--space-2)',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-full)',
                    fontSize: 'var(--text-xs)',
                    color: 'var(--text-secondary)'
                  }}>{ex}</span>
                ))}
              </div>
            </div>

            {/* Active Uploads */}
            {activeUploads.length > 0 && (
              <div style={{ marginTop: 'var(--space-4)', paddingTop: 'var(--space-4)', borderTop: '1px solid var(--border)' }}>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Uploading
                </span>
                {activeUploads.map(upload => (
                  <div key={upload.id} style={{ marginTop: 'var(--space-2)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <Loader2 size={14} className="spin" style={{ color: 'var(--grass-green)' }} />
                    <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {upload.filename}
                    </span>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                      {upload.progress}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Documents List */}
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '12px', overflow: 'hidden' }}>
          {/* Section Header with grey background */}
          <button
            onClick={() => toggleSection('documents')}
            style={{
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.75rem', 
              width: '100%',
              padding: '0.875rem 1rem', 
              background: 'var(--bg-tertiary)', 
              border: 'none',
              borderBottom: expandedSections.documents ? '1px solid var(--border)' : 'none',
              cursor: 'pointer', 
              textAlign: 'left'
            }}
          >
            {expandedSections.documents ? <ChevronDown size={18} style={{ color: 'var(--text-muted)' }} /> : <ChevronRight size={18} style={{ color: 'var(--text-muted)' }} />}
            <FileText size={18} style={{ color: category.color }} />
            <span style={{ fontWeight: 600, color: 'var(--text-primary)', flex: 1, fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)' }}>
              {category.label} Documents
            </span>
            <span style={{ 
              background: `${category.color}15`, 
              color: category.color, 
              padding: '0.2rem 0.6rem', 
              borderRadius: '10px', 
              fontSize: 'var(--text-xs)', 
              fontWeight: 600 
            }}>
              {filteredDocs.length}
            </span>
          </button>
          
          {expandedSections.documents && (
            <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
              {loading ? (
                <div style={{ padding: '2rem', textAlign: 'center' }}>
                  <Loader2 size={24} className="spin" style={{ color: 'var(--grass-green)' }} />
                  <p style={{ marginTop: 'var(--space-2)', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
                    Loading documents...
                  </p>
                </div>
              ) : filteredDocs.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                  <FolderOpen size={32} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
                  <p style={{ margin: 0, fontSize: 'var(--text-sm)' }}>No {category.shortLabel.toLowerCase()} documents yet</p>
                </div>
              ) : (
                filteredDocs.map((doc, i) => (
                  <div key={doc.id || doc.filename || i} style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '0.75rem', 
                    padding: '0.75rem 1rem', 
                    borderBottom: '1px solid var(--border-light)' 
                  }}>
                    <FileText size={16} style={{ color: category.color, flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ 
                        fontSize: 'var(--text-sm)', 
                        fontWeight: 500, 
                        color: 'var(--text-primary)', 
                        overflow: 'hidden', 
                        textOverflow: 'ellipsis', 
                        whiteSpace: 'nowrap' 
                      }}>
                        {doc.filename}
                      </div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                        {doc.chunk_count || doc.chunks || 0} chunks
                        {doc.created_at && ` • ${new Date(doc.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      {doc.status === 'error' ? (
                        <XCircle size={16} style={{ color: 'var(--critical)' }} />
                      ) : doc.status === 'processing' ? (
                        <Loader2 size={16} className="spin" style={{ color: 'var(--warning)' }} />
                      ) : (
                        <CheckCircle size={16} style={{ color: 'var(--success)' }} />
                      )}
                      <button
                        onClick={() => handleDelete(doc)}
                        style={{
                          padding: 'var(--space-1)',
                          background: 'transparent',
                          border: 'none',
                          cursor: 'pointer',
                          color: 'var(--text-muted)',
                          borderRadius: 'var(--radius-sm)'
                        }}
                        title="Delete document"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
