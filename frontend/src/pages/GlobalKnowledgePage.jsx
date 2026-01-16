/**
 * GlobalKnowledgePage.jsx - Global Knowledge Base
 * 
 * Unified admin page for cross-project knowledge:
 * - Regulatory & Compliance (laws, IRS pubs, audit requirements)
 * - Vendor Documentation (product guides, configuration manuals)
 * 
 * Uses design system CSS classes throughout.
 * Phase 4A UX Overhaul - January 2026
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useUpload } from '../context/UploadContext';
import api from '../services/api';
import {
  Scale, BookOpen, Upload, FileText, Trash2, RefreshCw,
  CheckCircle, XCircle, Loader2, ChevronDown, ChevronRight,
  AlertTriangle, Search, Filter, FolderOpen
} from 'lucide-react';

// =============================================================================
// KNOWLEDGE CATEGORIES
// =============================================================================

const CATEGORIES = {
  regulatory: {
    id: 'regulatory',
    label: 'Regulatory & Compliance',
    description: 'Federal, state, and local regulations. IRS publications, DOL guidelines, audit requirements.',
    icon: Scale,
    color: 'var(--scarlet)',
    bgColor: 'var(--scarlet-light)',
    truthType: 'regulatory',
    examples: ['IRS Pub 15', 'State Tax Guides', 'SOC 2 Controls', 'FLSA Requirements']
  },
  reference: {
    id: 'reference',
    label: 'Vendor Documentation',
    description: 'Product documentation, configuration guides, best practices from software vendors.',
    icon: BookOpen,
    color: 'var(--electric-blue)',
    bgColor: 'var(--electric-blue-alpha-10)',
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
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedDocs, setExpandedDocs] = useState({});
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

  // Filter documents by category and search
  const filteredDocs = documents.filter(doc => {
    const matchesCategory = doc.truth_type === CATEGORIES[activeCategory].truthType;
    const matchesSearch = !searchTerm || 
      doc.filename?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.domain?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  // Handle file upload
  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    files.forEach(file => {
      addUpload(file, null, 'Reference Library', {
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

  const toggleDocExpand = (docId) => {
    setExpandedDocs(prev => ({ ...prev, [docId]: !prev[docId] }));
  };

  const category = CATEGORIES[activeCategory];
  const CategoryIcon = category.icon;

  // Active uploads for this category
  const activeUploads = uploads.filter(u => 
    u.status === 'uploading' || u.status === 'processing'
  );

  return (
    <div className="page">
      {/* Page Header */}
      <div className="page__header">
        <div className="page__header-content">
          <div className="page__icon" style={{ background: 'var(--grass-green)' }}>
            <BookOpen size={20} color="white" />
          </div>
          <div>
            <h1 className="page__title">Global Knowledge</h1>
            <p className="page__subtitle">
              Cross-project reference materials for compliance and configuration guidance
            </p>
          </div>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="tabs">
        {Object.values(CATEGORIES).map(cat => {
          const Icon = cat.icon;
          const isActive = activeCategory === cat.id;
          return (
            <button
              key={cat.id}
              className={`tabs__tab ${isActive ? 'tabs__tab--active' : ''}`}
              onClick={() => setActiveCategory(cat.id)}
            >
              <Icon size={16} />
              <span>{cat.label}</span>
            </button>
          );
        })}
      </div>

      <div className="page__content" style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 'var(--space-6)' }}>
        {/* Left Panel - Upload */}
        <div className="card">
          <div className="card__header">
            <CategoryIcon size={18} style={{ color: category.color }} />
            <span>Upload {category.label}</span>
          </div>
          
          <div className="card__body">
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)', lineHeight: 1.6 }}>
              {category.description}
            </p>

            {/* Upload Zone */}
            <div
              className="upload-zone"
              onClick={() => fileInputRef.current?.click()}
              style={{ marginBottom: 'var(--space-4)' }}
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
            <div style={{ marginTop: 'var(--space-4)' }}>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Examples
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
                {category.examples.map(ex => (
                  <span key={ex} className="badge badge--muted">{ex}</span>
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
        <div className="card">
          <div className="card__header" style={{ justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <FileText size={18} style={{ color: 'var(--text-muted)' }} />
              <span>{category.label} Documents</span>
              <span className="badge badge--muted">{filteredDocs.length}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <div className="search-input" style={{ width: '200px' }}>
                <Search size={14} />
                <input
                  type="text"
                  placeholder="Search documents..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              <button className="btn btn--ghost btn--sm" onClick={loadDocuments}>
                <RefreshCw size={14} />
              </button>
            </div>
          </div>

          <div className="card__body" style={{ padding: 0 }}>
            {loading ? (
              <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
                <Loader2 size={24} className="spin" style={{ color: 'var(--grass-green)' }} />
                <p style={{ marginTop: 'var(--space-2)', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
                  Loading documents...
                </p>
              </div>
            ) : filteredDocs.length === 0 ? (
              <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
                <FolderOpen size={32} style={{ color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }} />
                <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                  {searchTerm ? 'No documents match your search' : `No ${category.label.toLowerCase()} documents uploaded yet`}
                </p>
                <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', marginTop: 'var(--space-1)' }}>
                  Upload documents using the panel on the left
                </p>
              </div>
            ) : (
              <div className="list">
                {filteredDocs.map(doc => {
                  const isExpanded = expandedDocs[doc.id || doc.filename];
                  return (
                    <div key={doc.id || doc.filename} className="list__item">
                      <div 
                        className="list__item-main"
                        onClick={() => toggleDocExpand(doc.id || doc.filename)}
                        style={{ cursor: 'pointer' }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flex: 1 }}>
                          {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                          <FileText size={16} style={{ color: category.color }} />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {doc.filename}
                            </div>
                            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: '2px' }}>
                              {doc.domain && <span className="badge badge--muted" style={{ marginRight: 'var(--space-2)' }}>{doc.domain}</span>}
                              {doc.chunk_count && `${doc.chunk_count} chunks`}
                              {doc.created_at && ` • ${new Date(doc.created_at).toLocaleDateString()}`}
                            </div>
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                          {doc.status === 'processed' ? (
                            <CheckCircle size={16} style={{ color: 'var(--success)' }} />
                          ) : doc.status === 'error' ? (
                            <XCircle size={16} style={{ color: 'var(--critical)' }} />
                          ) : (
                            <Loader2 size={16} className="spin" style={{ color: 'var(--warning)' }} />
                          )}
                          <button
                            className="btn btn--ghost btn--sm"
                            onClick={(e) => { e.stopPropagation(); handleDelete(doc); }}
                            title="Delete document"
                          >
                            <Trash2 size={14} style={{ color: 'var(--critical)' }} />
                          </button>
                        </div>
                      </div>
                      
                      {isExpanded && (
                        <div className="list__item-detail" style={{ marginLeft: 'var(--space-8)', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--border-light)' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-4)', fontSize: 'var(--text-xs)' }}>
                            <div>
                              <span style={{ color: 'var(--text-muted)' }}>Type</span>
                              <div style={{ color: 'var(--text-primary)', marginTop: '2px' }}>{doc.truth_type || 'Unknown'}</div>
                            </div>
                            <div>
                              <span style={{ color: 'var(--text-muted)' }}>Uploaded By</span>
                              <div style={{ color: 'var(--text-primary)', marginTop: '2px' }}>{doc.uploaded_by || 'System'}</div>
                            </div>
                            <div>
                              <span style={{ color: 'var(--text-muted)' }}>Size</span>
                              <div style={{ color: 'var(--text-primary)', marginTop: '2px' }}>{doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : 'Unknown'}</div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
