/**
 * EndpointPicker.jsx - Select and pull data from connected APIs
 * 
 * Used in Upload Data page as an alternative to file upload.
 * Shows only systems that have been connected in project setup.
 * 
 * Created: January 17, 2026
 */

import React, { useState, useEffect } from 'react';
import { 
  Database, CheckCircle, XCircle, Loader2, 
  Download, AlertTriangle, ChevronDown, ChevronRight, RefreshCw
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

// Truth bucket colors
const BUCKET_COLORS = {
  reality: { bg: '#dcfce7', text: '#166534', label: 'Reality' },
  configuration: { bg: '#dbeafe', text: '#1e40af', label: 'Configuration' },
  intent: { bg: '#fef3c7', text: '#92400e', label: 'Intent' },
  reference: { bg: '#f3e8ff', text: '#6b21a8', label: 'Reference' },
  regulatory: { bg: '#fee2e2', text: '#991b1b', label: 'Regulatory' },
};

export default function EndpointPicker({ projectId, onDataPulled }) {
  const [connections, setConnections] = useState([]);
  const [systems, setSystems] = useState({});  // { system_id: system_definition }
  const [loading, setLoading] = useState(true);
  const [expandedSystem, setExpandedSystem] = useState(null);
  const [selectedEndpoints, setSelectedEndpoints] = useState({});  // { system_id: [endpoint_ids] }
  const [pullStatus, setPullStatus] = useState(null);
  
  useEffect(() => {
    loadData();
  }, [projectId]);
  
  const loadData = async () => {
    try {
      // Load connections for this project
      const connResponse = await fetch(`${API_BASE}/api/integrations/connections/${projectId}`);
      const connData = await connResponse.json();
      const projectConnections = (connData.connections || []).filter(c => c.status === 'connected');
      setConnections(projectConnections);
      
      // Load system definitions for connected systems
      const systemDefs = {};
      for (const conn of projectConnections) {
        const sysResponse = await fetch(`${API_BASE}/api/integrations/systems/${conn.system_id}`);
        const sysData = await sysResponse.json();
        systemDefs[conn.system_id] = sysData;
      }
      setSystems(systemDefs);
      
      // Auto-expand first system
      if (projectConnections.length > 0) {
        setExpandedSystem(projectConnections[0].system_id);
      }
    } catch (err) {
      console.error('Failed to load connections:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const toggleEndpoint = (systemId, endpointId) => {
    setSelectedEndpoints(prev => {
      const current = prev[systemId] || [];
      const updated = current.includes(endpointId)
        ? current.filter(e => e !== endpointId)
        : [...current, endpointId];
      return { ...prev, [systemId]: updated };
    });
  };
  
  const selectAllEndpoints = (systemId) => {
    const system = systems[systemId];
    if (!system) return;
    
    const allIds = system.endpoints.map(e => e.id);
    setSelectedEndpoints(prev => ({ ...prev, [systemId]: allIds }));
  };
  
  const clearAllEndpoints = (systemId) => {
    setSelectedEndpoints(prev => ({ ...prev, [systemId]: [] }));
  };
  
  const getTotalSelected = () => {
    return Object.values(selectedEndpoints).reduce((sum, arr) => sum + arr.length, 0);
  };
  
  const pullData = async () => {
    const totalSelected = getTotalSelected();
    if (totalSelected === 0) return;
    
    setPullStatus({ status: 'pulling', current: null, results: [] });
    
    const allResults = [];
    
    // Pull from each system
    for (const [systemId, endpointIds] of Object.entries(selectedEndpoints)) {
      if (endpointIds.length === 0) continue;
      
      setPullStatus(prev => ({ ...prev, current: systems[systemId]?.name || systemId }));
      
      try {
        const response = await fetch(`${API_BASE}/api/integrations/connections/${projectId}/pull`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            system_id: systemId,
            endpoints: endpointIds
          })
        });
        
        const data = await response.json();
        allResults.push({
          system_id: systemId,
          system_name: systems[systemId]?.name || systemId,
          ...data
        });
      } catch (err) {
        allResults.push({
          system_id: systemId,
          system_name: systems[systemId]?.name || systemId,
          success: false,
          error: err.message
        });
      }
    }
    
    setPullStatus({ status: 'complete', results: allResults });
    
    // Clear selections
    setSelectedEndpoints({});
    
    if (onDataPulled) {
      onDataPulled(allResults);
    }
  };
  
  const resetPull = () => {
    setPullStatus(null);
  };
  
  if (loading) {
    return (
      <div className="ep-loading">
        <Loader2 size={20} className="ep-spin" />
        <span>Loading connected systems...</span>
      </div>
    );
  }
  
  // No connected systems
  if (connections.length === 0) {
    return (
      <div className="ep-empty">
        <Database size={40} style={{ opacity: 0.3 }} />
        <h4>No API Connections</h4>
        <p>Connect systems in Project Settings to pull data via API.</p>
      </div>
    );
  }
  
  // Show pull results
  if (pullStatus?.status === 'complete') {
    const totalRows = pullStatus.results.reduce((sum, r) => {
      return sum + (r.results?.reduce((s, res) => s + (res.rows_imported || 0), 0) || 0);
    }, 0);
    
    const totalSuccess = pullStatus.results.reduce((sum, r) => {
      return sum + (r.endpoints_successful || 0);
    }, 0);
    
    return (
      <div className="ep-results">
        <div className="ep-results-header">
          <CheckCircle size={32} style={{ color: 'var(--grass-green)' }} />
          <div>
            <h4>Pull Complete</h4>
            <p>{totalSuccess} endpoints pulled • {totalRows.toLocaleString()} total rows imported</p>
          </div>
        </div>
        
        <div className="ep-results-list">
          {pullStatus.results.map(sysResult => (
            <div key={sysResult.system_id} className="ep-result-system">
              <div className="ep-result-system-header">
                <Database size={16} />
                <span>{sysResult.system_name}</span>
                <span className="ep-result-count">
                  {sysResult.endpoints_successful}/{sysResult.endpoints_requested}
                </span>
              </div>
              
              {sysResult.results?.map(result => (
                <div 
                  key={result.endpoint_id}
                  className={`ep-result-item ${result.success ? 'success' : 'error'}`}
                >
                  {result.success ? <CheckCircle size={14} /> : <XCircle size={14} />}
                  <span className="ep-result-name">{result.endpoint_id}</span>
                  {result.success ? (
                    <span className="ep-result-detail">
                      {result.rows_imported} rows → {result.truth_bucket}
                    </span>
                  ) : (
                    <span className="ep-result-error">{result.error}</span>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
        
        <div className="ep-results-actions">
          <button className="btn btn-primary" onClick={resetPull}>
            <RefreshCw size={14} /> Pull More Data
          </button>
        </div>
      </div>
    );
  }
  
  // Show pulling status
  if (pullStatus?.status === 'pulling') {
    return (
      <div className="ep-pulling">
        <Loader2 size={40} className="ep-spin" />
        <h4>Pulling Data...</h4>
        <p>Fetching from {pullStatus.current || 'API'}...</p>
      </div>
    );
  }
  
  // Main picker UI
  const totalSelected = getTotalSelected();
  
  return (
    <div className="endpoint-picker">
      <div className="ep-header">
        <h4>Pull Data from Connected Systems</h4>
        <p>Select the data you want to import from your connected APIs.</p>
      </div>
      
      <div className="ep-systems">
        {connections.map(conn => {
          const system = systems[conn.system_id];
          const isExpanded = expandedSystem === conn.system_id;
          const selected = selectedEndpoints[conn.system_id] || [];
          
          if (!system) return null;
          
          // Group endpoints by truth bucket
          const endpointsByBucket = {};
          system.endpoints?.forEach(ep => {
            const bucket = ep.truth_bucket || 'reality';
            if (!endpointsByBucket[bucket]) endpointsByBucket[bucket] = [];
            endpointsByBucket[bucket].push(ep);
          });
          
          return (
            <div key={conn.system_id} className="ep-system-card">
              <div 
                className="ep-system-header"
                onClick={() => setExpandedSystem(isExpanded ? null : conn.system_id)}
              >
                {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                <Database size={18} />
                <span className="ep-system-name">{system.name}</span>
                <span className="ep-system-status">
                  <CheckCircle size={12} /> Connected
                </span>
                {selected.length > 0 && (
                  <span className="ep-selected-badge">{selected.length} selected</span>
                )}
              </div>
              
              {isExpanded && (
                <div className="ep-system-endpoints">
                  <div className="ep-select-actions">
                    <button onClick={() => selectAllEndpoints(conn.system_id)}>Select All</button>
                    <button onClick={() => clearAllEndpoints(conn.system_id)}>Clear</button>
                  </div>
                  
                  {Object.entries(endpointsByBucket).map(([bucket, endpoints]) => {
                    const bucketStyle = BUCKET_COLORS[bucket] || BUCKET_COLORS.reality;
                    
                    return (
                      <div key={bucket} className="ep-bucket-group">
                        <div 
                          className="ep-bucket-header"
                          style={{ background: bucketStyle.bg, color: bucketStyle.text }}
                        >
                          {bucketStyle.label}
                        </div>
                        
                        <div className="ep-endpoint-list">
                          {endpoints.map(endpoint => {
                            const isSelected = selected.includes(endpoint.id);
                            
                            return (
                              <div 
                                key={endpoint.id}
                                className={`ep-endpoint-item ${isSelected ? 'selected' : ''}`}
                                onClick={() => toggleEndpoint(conn.system_id, endpoint.id)}
                              >
                                <input 
                                  type="checkbox" 
                                  checked={isSelected}
                                  onChange={() => {}}
                                />
                                <div className="ep-endpoint-info">
                                  <div className="ep-endpoint-name">{endpoint.name}</div>
                                  <div className="ep-endpoint-desc">{endpoint.description}</div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      {/* Pull Button */}
      <div className="ep-actions">
        <div className="ep-selection-summary">
          {totalSelected > 0 
            ? `${totalSelected} endpoint(s) selected`
            : 'Select endpoints to pull'
          }
        </div>
        <button 
          className="btn btn-primary"
          onClick={pullData}
          disabled={totalSelected === 0}
        >
          <Download size={16} />
          Pull Selected Data
        </button>
      </div>
      
      <style>{`
        .endpoint-picker {
          padding: 16px 0;
        }
        
        .ep-loading, .ep-pulling {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 40px;
          color: var(--text-secondary);
        }
        .ep-pulling h4 { margin: 16px 0 4px; }
        .ep-pulling p { margin: 0; }
        
        .ep-spin { animation: ep-spin 1s linear infinite; }
        @keyframes ep-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        
        .ep-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 40px;
          text-align: center;
          color: var(--text-secondary);
        }
        .ep-empty h4 { margin: 12px 0 4px; color: var(--text-primary); }
        .ep-empty p { margin: 0; font-size: 13px; }
        
        .ep-header {
          margin-bottom: 16px;
        }
        .ep-header h4 { margin: 0 0 4px; font-size: 15px; }
        .ep-header p { margin: 0; font-size: 13px; color: var(--text-secondary); }
        
        .ep-systems {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-bottom: 16px;
        }
        
        .ep-system-card {
          border: 1px solid var(--border-color);
          border-radius: 8px;
          overflow: hidden;
        }
        
        .ep-system-header {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px 16px;
          background: var(--bg-secondary);
          cursor: pointer;
        }
        .ep-system-header:hover {
          background: var(--bg-primary);
        }
        
        .ep-system-name {
          font-weight: 500;
          flex: 1;
        }
        
        .ep-system-status {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 11px;
          color: #16a34a;
        }
        
        .ep-selected-badge {
          background: var(--grass-green);
          color: white;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 11px;
          font-weight: 500;
        }
        
        .ep-system-endpoints {
          padding: 12px;
          border-top: 1px solid var(--border-color);
        }
        
        .ep-select-actions {
          display: flex;
          gap: 8px;
          margin-bottom: 12px;
        }
        .ep-select-actions button {
          padding: 4px 10px;
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: 4px;
          font-size: 11px;
          cursor: pointer;
        }
        .ep-select-actions button:hover {
          background: var(--bg-primary);
        }
        
        .ep-bucket-group {
          margin-bottom: 12px;
        }
        
        .ep-bucket-header {
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 500;
          margin-bottom: 8px;
          display: inline-block;
        }
        
        .ep-endpoint-list {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        
        .ep-endpoint-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 8px 12px;
          border-radius: 6px;
          cursor: pointer;
          border: 1px solid transparent;
        }
        .ep-endpoint-item:hover {
          background: var(--bg-secondary);
        }
        .ep-endpoint-item.selected {
          background: rgba(131, 177, 109, 0.08);
          border-color: rgba(131, 177, 109, 0.3);
        }
        
        .ep-endpoint-info { flex: 1; }
        .ep-endpoint-name { font-size: 13px; font-weight: 500; }
        .ep-endpoint-desc { font-size: 11px; color: var(--text-secondary); }
        
        .ep-actions {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-top: 16px;
          border-top: 1px solid var(--border-color);
        }
        
        .ep-selection-summary {
          font-size: 13px;
          color: var(--text-secondary);
        }
        
        /* Results */
        .ep-results {
          padding: 20px;
        }
        
        .ep-results-header {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 16px;
          background: rgba(131, 177, 109, 0.1);
          border-radius: 8px;
          margin-bottom: 20px;
        }
        .ep-results-header h4 { margin: 0; }
        .ep-results-header p { margin: 4px 0 0; font-size: 13px; color: var(--text-secondary); }
        
        .ep-results-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-bottom: 20px;
        }
        
        .ep-result-system {
          border: 1px solid var(--border-color);
          border-radius: 8px;
          overflow: hidden;
        }
        
        .ep-result-system-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background: var(--bg-secondary);
          font-weight: 500;
          font-size: 13px;
        }
        .ep-result-count {
          margin-left: auto;
          font-size: 12px;
          color: var(--text-secondary);
        }
        
        .ep-result-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 8px 16px;
          font-size: 12px;
          border-top: 1px solid var(--border-color);
        }
        .ep-result-item.success { color: #16a34a; }
        .ep-result-item.error { color: #dc2626; }
        
        .ep-result-name { flex: 1; font-weight: 500; }
        .ep-result-detail { color: var(--text-secondary); }
        .ep-result-error { font-style: italic; }
        
        .ep-results-actions {
          display: flex;
          justify-content: center;
        }
      `}</style>
    </div>
  );
}
