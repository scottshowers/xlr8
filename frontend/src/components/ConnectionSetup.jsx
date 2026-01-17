/**
 * ConnectionSetup.jsx - Configure API connections for a project
 * 
 * Used in Project Setup / Edit Project page.
 * Allows selecting systems and entering credentials.
 * 
 * Created: January 17, 2026
 */

import React, { useState, useEffect } from 'react';
import { 
  Database, Lock, CheckCircle, XCircle, Loader2, 
  Plus, Trash2, ChevronDown, ChevronRight
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

// Status badges
const STATUS_BADGES = {
  ready: { bg: '#dcfce7', text: '#166534', label: 'Ready' },
  beta: { bg: '#fef3c7', text: '#92400e', label: 'Beta' },
  coming_soon: { bg: '#e5e7eb', text: '#374151', label: 'Coming Soon' },
  planned: { bg: '#f3e8ff', text: '#6b21a8', label: 'Planned' },
};

export default function ConnectionSetup({ projectId, onConnectionsChange }) {
  const [systems, setSystems] = useState([]);
  const [connections, setConnections] = useState([]);  // Systems added to this project
  const [loading, setLoading] = useState(true);
  const [expandedSystem, setExpandedSystem] = useState(null);
  const [credentials, setCredentials] = useState({});  // { system_id: { field: value } }
  const [testStatus, setTestStatus] = useState({});    // { system_id: 'testing' | 'connected' | 'failed' }
  const [showAddSystem, setShowAddSystem] = useState(false);
  
  useEffect(() => {
    loadData();
  }, [projectId]);
  
  const loadData = async () => {
    try {
      // Load available systems
      const sysResponse = await fetch(`${API_BASE}/api/integrations/systems`);
      const sysData = await sysResponse.json();
      setSystems(sysData.systems || []);
      
      // Load existing connections for this project
      if (projectId) {
        const connResponse = await fetch(`${API_BASE}/api/integrations/connections/${projectId}`);
        const connData = await connResponse.json();
        setConnections(connData.connections || []);
      }
    } catch (err) {
      console.error('Failed to load systems:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const addSystem = (system) => {
    if (connections.find(c => c.system_id === system.id)) return;
    
    setConnections(prev => [...prev, {
      system_id: system.id,
      system_name: system.name,
      status: 'not_configured',
      domain: system.domain
    }]);
    setCredentials(prev => ({ ...prev, [system.id]: {} }));
    setExpandedSystem(system.id);
    setShowAddSystem(false);
  };
  
  const removeSystem = (systemId) => {
    setConnections(prev => prev.filter(c => c.system_id !== systemId));
    setCredentials(prev => {
      const next = { ...prev };
      delete next[systemId];
      return next;
    });
    setTestStatus(prev => {
      const next = { ...prev };
      delete next[systemId];
      return next;
    });
  };
  
  const updateCredential = (systemId, field, value) => {
    setCredentials(prev => ({
      ...prev,
      [systemId]: {
        ...(prev[systemId] || {}),
        [field]: value
      }
    }));
  };
  
  const testConnection = async (systemId) => {
    const system = systems.find(s => s.id === systemId);
    if (!system) return;
    
    setTestStatus(prev => ({ ...prev, [systemId]: 'testing' }));
    
    try {
      const response = await fetch(`${API_BASE}/api/integrations/connections/${projectId}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          system_id: systemId,
          credentials: credentials[systemId] || {}
        })
      });
      
      const data = await response.json();
      const newStatus = data.success ? 'connected' : 'failed';
      setTestStatus(prev => ({ ...prev, [systemId]: newStatus }));
      
      if (data.success) {
        // Save credentials
        await fetch(`${API_BASE}/api/integrations/connections`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: projectId,
            system_id: systemId,
            credentials: credentials[systemId] || {}
          })
        });
        
        // Update connection status
        setConnections(prev => prev.map(c => 
          c.system_id === systemId ? { ...c, status: 'connected' } : c
        ));
        
        if (onConnectionsChange) {
          onConnectionsChange(connections);
        }
      }
    } catch (err) {
      console.error('Connection test failed:', err);
      setTestStatus(prev => ({ ...prev, [systemId]: 'failed' }));
    }
  };
  
  const getSystemDef = (systemId) => systems.find(s => s.id === systemId);
  
  // Available systems to add (ready ones not already added)
  const availableSystems = systems.filter(s => 
    s.status === 'ready' && !connections.find(c => c.system_id === s.id)
  );
  
  // Coming soon systems
  const comingSoonSystems = systems.filter(s => s.status !== 'ready');
  
  if (loading) {
    return (
      <div className="cs-loading">
        <Loader2 size={20} className="cs-spin" />
        <span>Loading systems...</span>
      </div>
    );
  }
  
  return (
    <div className="connection-setup">
      <div className="cs-header">
        <h3>API Connections</h3>
        <p>Connect external systems to pull data directly into this project.</p>
      </div>
      
      {/* Connected Systems */}
      <div className="cs-connections">
        {connections.length === 0 ? (
          <div className="cs-empty">
            <Database size={32} style={{ opacity: 0.3 }} />
            <p>No systems connected yet</p>
          </div>
        ) : (
          connections.map(conn => {
            const system = getSystemDef(conn.system_id);
            const isExpanded = expandedSystem === conn.system_id;
            const status = testStatus[conn.system_id] || conn.status;
            
            return (
              <div key={conn.system_id} className="cs-connection-card">
                <div 
                  className="cs-connection-header"
                  onClick={() => setExpandedSystem(isExpanded ? null : conn.system_id)}
                >
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <Database size={18} />
                  <span className="cs-connection-name">{conn.system_name}</span>
                  <span className="cs-connection-domain">{conn.domain}</span>
                  
                  {status === 'connected' && (
                    <span className="cs-status connected"><CheckCircle size={14} /> Connected</span>
                  )}
                  {status === 'testing' && (
                    <span className="cs-status testing"><Loader2 size={14} className="cs-spin" /> Testing...</span>
                  )}
                  {status === 'failed' && (
                    <span className="cs-status failed"><XCircle size={14} /> Failed</span>
                  )}
                  {(status === 'not_configured' || status === 'saved') && (
                    <span className="cs-status pending">Not tested</span>
                  )}
                  
                  <button 
                    className="cs-remove-btn"
                    onClick={(e) => { e.stopPropagation(); removeSystem(conn.system_id); }}
                    title="Remove"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                
                {isExpanded && system && (
                  <div className="cs-connection-form">
                    {system.auth_fields?.map(field => (
                      <div key={field.name} className="cs-form-group">
                        <label>
                          {field.label}
                          {field.required && <span className="cs-required">*</span>}
                        </label>
                        <input
                          type={field.type === 'password' ? 'password' : 'text'}
                          value={credentials[conn.system_id]?.[field.name] || ''}
                          onChange={(e) => updateCredential(conn.system_id, field.name, e.target.value)}
                          placeholder={field.help || ''}
                        />
                        {field.help && <span className="cs-field-help">{field.help}</span>}
                      </div>
                    ))}
                    
                    <div className="cs-form-actions">
                      <button 
                        className="btn btn-primary"
                        onClick={() => testConnection(conn.system_id)}
                        disabled={status === 'testing'}
                      >
                        <Lock size={14} />
                        {status === 'testing' ? 'Testing...' : 'Test & Save Connection'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
      
      {/* Add System Button */}
      {!showAddSystem ? (
        <button className="cs-add-btn" onClick={() => setShowAddSystem(true)}>
          <Plus size={16} /> Add System
        </button>
      ) : (
        <div className="cs-add-panel">
          <div className="cs-add-header">
            <span>Select a system to add</span>
            <button onClick={() => setShowAddSystem(false)}>×</button>
          </div>
          
          {availableSystems.length > 0 ? (
            <div className="cs-system-list">
              {availableSystems.map(system => (
                <div 
                  key={system.id}
                  className="cs-system-option"
                  onClick={() => addSystem(system)}
                >
                  <Database size={18} />
                  <div className="cs-system-info">
                    <div className="cs-system-name">{system.name}</div>
                    <div className="cs-system-desc">{system.description}</div>
                  </div>
                  <Plus size={16} style={{ color: 'var(--grass-green)' }} />
                </div>
              ))}
            </div>
          ) : (
            <div className="cs-no-systems">All available systems have been added.</div>
          )}
          
          {comingSoonSystems.length > 0 && (
            <>
              <div className="cs-divider">Coming Soon</div>
              <div className="cs-system-list coming-soon">
                {comingSoonSystems.map(system => {
                  const badge = STATUS_BADGES[system.status];
                  return (
                    <div key={system.id} className="cs-system-option disabled">
                      <Database size={18} />
                      <div className="cs-system-info">
                        <div className="cs-system-name">{system.name}</div>
                        <div className="cs-system-desc">{system.description}</div>
                      </div>
                      <span className="cs-coming-badge" style={{ background: badge?.bg, color: badge?.text }}>
                        {badge?.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
      
      <style>{`
        .connection-setup {
          padding: 16px 0;
        }
        
        .cs-loading {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 20px;
          color: var(--text-secondary);
        }
        
        .cs-spin { animation: cs-spin 1s linear infinite; }
        @keyframes cs-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        
        .cs-header {
          margin-bottom: 16px;
        }
        .cs-header h3 {
          margin: 0 0 4px;
          font-size: 16px;
        }
        .cs-header p {
          margin: 0;
          font-size: 13px;
          color: var(--text-secondary);
        }
        
        .cs-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 30px;
          color: var(--text-secondary);
          background: var(--bg-secondary);
          border-radius: 8px;
          border: 1px dashed var(--border-color);
        }
        .cs-empty p { margin: 8px 0 0; font-size: 13px; }
        
        .cs-connections {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 16px;
        }
        
        .cs-connection-card {
          border: 1px solid var(--border-color);
          border-radius: 8px;
          overflow: hidden;
        }
        
        .cs-connection-header {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px 16px;
          background: var(--bg-secondary);
          cursor: pointer;
        }
        .cs-connection-header:hover {
          background: var(--bg-primary);
        }
        
        .cs-connection-name {
          font-weight: 500;
          flex: 1;
        }
        .cs-connection-domain {
          font-size: 11px;
          color: var(--text-secondary);
          padding: 2px 8px;
          background: var(--bg-primary);
          border-radius: 10px;
        }
        
        .cs-status {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
          padding: 4px 10px;
          border-radius: 12px;
        }
        .cs-status.connected { background: #dcfce7; color: #166534; }
        .cs-status.testing { background: #fef3c7; color: #92400e; }
        .cs-status.failed { background: #fee2e2; color: #991b1b; }
        .cs-status.pending { background: #e5e7eb; color: #374151; }
        
        .cs-remove-btn {
          background: none;
          border: none;
          padding: 4px;
          cursor: pointer;
          color: var(--text-secondary);
          border-radius: 4px;
        }
        .cs-remove-btn:hover {
          background: #fee2e2;
          color: #dc2626;
        }
        
        .cs-connection-form {
          padding: 16px;
          border-top: 1px solid var(--border-color);
          background: var(--bg-primary);
        }
        
        .cs-form-group {
          margin-bottom: 12px;
        }
        .cs-form-group label {
          display: block;
          font-size: 12px;
          font-weight: 500;
          margin-bottom: 4px;
        }
        .cs-required { color: #dc2626; margin-left: 2px; }
        .cs-form-group input {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid var(--border-color);
          border-radius: 6px;
          font-size: 13px;
          background: var(--bg-secondary);
        }
        .cs-field-help {
          display: block;
          font-size: 11px;
          color: var(--text-secondary);
          margin-top: 2px;
        }
        
        .cs-form-actions {
          margin-top: 16px;
        }
        
        .cs-add-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 10px 16px;
          background: var(--bg-secondary);
          border: 1px dashed var(--border-color);
          border-radius: 8px;
          cursor: pointer;
          font-size: 13px;
          color: var(--text-secondary);
          width: 100%;
          justify-content: center;
        }
        .cs-add-btn:hover {
          border-color: var(--grass-green);
          color: var(--grass-green);
        }
        
        .cs-add-panel {
          border: 1px solid var(--border-color);
          border-radius: 8px;
          overflow: hidden;
        }
        
        .cs-add-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 16px;
          background: var(--bg-secondary);
          font-size: 13px;
          font-weight: 500;
        }
        .cs-add-header button {
          background: none;
          border: none;
          font-size: 18px;
          cursor: pointer;
          color: var(--text-secondary);
        }
        
        .cs-system-list {
          padding: 8px;
        }
        
        .cs-system-option {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 12px;
          border-radius: 6px;
          cursor: pointer;
        }
        .cs-system-option:hover {
          background: var(--bg-secondary);
        }
        .cs-system-option.disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        .cs-system-info { flex: 1; }
        .cs-system-name { font-size: 13px; font-weight: 500; }
        .cs-system-desc { font-size: 11px; color: var(--text-secondary); }
        
        .cs-no-systems {
          padding: 20px;
          text-align: center;
          font-size: 13px;
          color: var(--text-secondary);
        }
        
        .cs-divider {
          padding: 8px 16px;
          font-size: 11px;
          font-weight: 500;
          color: var(--text-secondary);
          text-transform: uppercase;
          background: var(--bg-secondary);
        }
        
        .cs-coming-badge {
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 10px;
          font-weight: 500;
        }
      `}</style>
    </div>
  );
}
