/**
 * ApiConnectionsPage - UKG Pro/WFM/Ready Integration
 * 
 * Features:
 * - Create/manage API connections per project
 * - Test connections
 * - Browse available reports
 * - Execute reports and save to DuckDB
 * 
 * Deploy to: frontend/src/pages/ApiConnectionsPage.jsx
 */

import React, { useState, useEffect } from 'react'
import { useProject } from '../context/ProjectContext'
import {
  Cloud, Plus, Trash2, RefreshCw, Check, X, ChevronRight, ChevronDown,
  Play, FileText, Database, Settings, AlertCircle, CheckCircle,
  Eye, EyeOff, Loader2, Download, Table, Plug, Server
} from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function ApiConnectionsPage() {
  const { activeProject } = useProject()
  const [connections, setConnections] = useState([])
  const [loading, setLoading] = useState(false)
  const [showNewConnection, setShowNewConnection] = useState(false)
  const [selectedConnection, setSelectedConnection] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (activeProject?.name) {
      loadConnections()
    }
  }, [activeProject?.name])

  const loadConnections = async () => {
    if (!activeProject?.name) return
    
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/connections/${encodeURIComponent(activeProject.name)}`)
      const data = await res.json()
      setConnections(data.connections || [])
    } catch (err) {
      console.error('Failed to load connections:', err)
    } finally {
      setLoading(false)
    }
  }

  if (!activeProject) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <Cloud className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>Select a project to manage API connections.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">API Connections</h1>
            <p className="text-sm text-gray-500 mt-1">
              {activeProject.name} • Connect to UKG Pro, WFM, or Ready
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={loadConnections}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              title="Refresh"
            >
              <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
            </button>
            <button
              onClick={() => setShowNewConnection(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus size={18} />
              New Connection
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-6">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center gap-2">
            <AlertCircle size={18} />
            {error}
            <button onClick={() => setError(null)} className="ml-auto">
              <X size={18} />
            </button>
          </div>
        )}

        {/* Connections List */}
        <div className="grid gap-4">
          {connections.length === 0 && !loading ? (
            <div className="bg-white rounded-xl border p-12 text-center">
              <Cloud className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-semibold text-gray-700 mb-2">No Connections Yet</h3>
              <p className="text-gray-500 mb-4">
                Connect to UKG Pro to pull reports directly into XLR8
              </p>
              <button
                onClick={() => setShowNewConnection(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Create Connection
              </button>
            </div>
          ) : (
            connections.map(conn => (
              <ConnectionCard
                key={conn.id}
                connection={conn}
                isSelected={selectedConnection?.id === conn.id}
                onSelect={() => setSelectedConnection(conn)}
                onRefresh={loadConnections}
                onError={setError}
              />
            ))
          )}
        </div>

        {/* Selected Connection Details */}
        {selectedConnection && (
          <div className="mt-6">
            <ConnectionDetails
              connection={selectedConnection}
              onClose={() => setSelectedConnection(null)}
              onRefresh={loadConnections}
            />
          </div>
        )}
      </div>

      {/* New Connection Modal */}
      {showNewConnection && (
        <NewConnectionModal
          projectName={activeProject.name}
          onClose={() => setShowNewConnection(false)}
          onCreated={() => {
            setShowNewConnection(false)
            loadConnections()
          }}
        />
      )}
    </div>
  )
}


// =============================================================================
// CONNECTION CARD
// =============================================================================

function ConnectionCard({ connection, isSelected, onSelect, onRefresh, onError }) {
  const [testing, setTesting] = useState(false)

  const testConnection = async (e) => {
    e.stopPropagation()
    setTesting(true)
    
    try {
      const res = await fetch(`${API_BASE}/api/connections/${connection.id}/test`, {
        method: 'POST'
      })
      const data = await res.json()
      
      if (!data.success) {
        onError(data.message || 'Connection test failed')
      }
      
      onRefresh()
    } catch (err) {
      onError(err.message)
    } finally {
      setTesting(false)
    }
  }

  const deleteConnection = async (e) => {
    e.stopPropagation()
    if (!confirm('Delete this connection?')) return
    
    try {
      await fetch(`${API_BASE}/api/connections/${connection.id}`, {
        method: 'DELETE'
      })
      onRefresh()
    } catch (err) {
      onError(err.message)
    }
  }

  const providerLabels = {
    ukg_pro: { name: 'UKG Pro', color: 'blue', icon: '🏢' },
    ukg_wfm: { name: 'UKG WFM', color: 'purple', icon: '⏰' },
    ukg_ready: { name: 'UKG Ready', color: 'green', icon: '✅' },
  }

  const provider = providerLabels[connection.provider] || { name: connection.provider, color: 'gray', icon: '🔌' }

  const statusColors = {
    active: 'bg-green-100 text-green-700',
    error: 'bg-red-100 text-red-700',
    pending: 'bg-amber-100 text-amber-700',
    disabled: 'bg-gray-100 text-gray-500',
  }

  return (
    <div
      onClick={onSelect}
      className={`bg-white rounded-xl border p-4 cursor-pointer transition-all ${
        isSelected ? 'ring-2 ring-blue-500 border-blue-500' : 'hover:border-gray-300'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 rounded-lg bg-${provider.color}-100 flex items-center justify-center text-2xl`}>
            {provider.icon}
          </div>
          
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900">
                {connection.connection_name || provider.name}
              </h3>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[connection.status]}`}>
                {connection.status}
              </span>
            </div>
            <p className="text-sm text-gray-500">{connection.base_url}</p>
            {connection.last_connected_at && (
              <p className="text-xs text-gray-400 mt-1">
                Last connected: {new Date(connection.last_connected_at).toLocaleString()}
              </p>
            )}
            {connection.last_error && connection.status === 'error' && (
              <p className="text-xs text-red-500 mt-1">
                Error: {connection.last_error}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={testConnection}
            disabled={testing}
            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-50"
            title="Test Connection"
          >
            {testing ? <Loader2 size={18} className="animate-spin" /> : <Plug size={18} />}
          </button>
          <button
            onClick={deleteConnection}
            className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
            title="Delete"
          >
            <Trash2 size={18} />
          </button>
          <ChevronRight size={20} className={`text-gray-400 transition-transform ${isSelected ? 'rotate-90' : ''}`} />
        </div>
      </div>
    </div>
  )
}


// =============================================================================
// CONNECTION DETAILS (Reports Browser)
// =============================================================================

function ConnectionDetails({ connection, onClose, onRefresh }) {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(false)
  const [currentPath, setCurrentPath] = useState('/content')
  const [selectedReport, setSelectedReport] = useState(null)

  useEffect(() => {
    loadReports()
  }, [connection.id, currentPath])

  const loadReports = async () => {
    setLoading(true)
    try {
      const res = await fetch(
        `${API_BASE}/api/connections/${connection.id}/reports?path=${encodeURIComponent(currentPath)}`
      )
      const data = await res.json()
      setReports(data.reports || [])
    } catch (err) {
      console.error('Failed to load reports:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border shadow-lg">
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="text-blue-600" size={20} />
          <span className="font-semibold">Available Reports</span>
          <span className="text-sm text-gray-500">({currentPath})</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadReports}
            className="p-1 text-gray-500 hover:text-gray-700"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
          <button onClick={onClose} className="p-1 text-gray-500 hover:text-gray-700">
            <X size={18} />
          </button>
        </div>
      </div>

      <div className="p-4">
        {/* Path navigation */}
        <div className="flex items-center gap-1 mb-4 text-sm">
          <button
            onClick={() => setCurrentPath('/content')}
            className="text-blue-600 hover:underline"
          >
            /content
          </button>
          {currentPath !== '/content' && (
            <>
              <ChevronRight size={14} className="text-gray-400" />
              <span className="text-gray-600">{currentPath.replace('/content/', '')}</span>
            </>
          )}
        </div>

        {/* Reports list */}
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="animate-spin text-blue-600" size={24} />
          </div>
        ) : reports.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No reports found at this path
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {reports.map((report, i) => (
              <div
                key={i}
                className={`p-3 border rounded-lg cursor-pointer transition-all ${
                  selectedReport?.path === report.path
                    ? 'border-blue-500 bg-blue-50'
                    : 'hover:border-gray-300 hover:bg-gray-50'
                }`}
                onClick={() => setSelectedReport(report)}
              >
                <div className="flex items-center gap-3">
                  <FileText className="text-blue-500 flex-shrink-0" size={18} />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 truncate">{report.name}</div>
                    <div className="text-xs text-gray-500 truncate">{report.path}</div>
                    {report.description && (
                      <div className="text-xs text-gray-400 mt-1">{report.description}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Selected report actions */}
        {selectedReport && (
          <div className="mt-4 pt-4 border-t">
            <ReportExecutor
              connectionId={connection.id}
              report={selectedReport}
              onExecuted={onRefresh}
            />
          </div>
        )}
      </div>
    </div>
  )
}


// =============================================================================
// REPORT EXECUTOR
// =============================================================================

function ReportExecutor({ connectionId, report, onExecuted }) {
  const [parameters, setParameters] = useState([])
  const [paramValues, setParamValues] = useState({})
  const [targetTable, setTargetTable] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingParams, setLoadingParams] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadParameters()
    // Auto-generate table name from report name
    const tableName = report.name
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '_')
      .replace(/_+/g, '_')
      .replace(/^_|_$/g, '')
    setTargetTable(`pro_${tableName}`)
  }, [report.path])

  const loadParameters = async () => {
    setLoadingParams(true)
    try {
      const res = await fetch(
        `${API_BASE}/api/connections/${connectionId}/reports/parameters?report_path=${encodeURIComponent(report.path)}`
      )
      const data = await res.json()
      setParameters(data.parameters || [])
      
      // Set default values
      const defaults = {}
      for (const p of data.parameters || []) {
        if (p.default_value) {
          defaults[p.name] = p.default_value
        }
      }
      setParamValues(defaults)
    } catch (err) {
      console.error('Failed to load parameters:', err)
    } finally {
      setLoadingParams(false)
    }
  }

  const executeReport = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    
    try {
      const res = await fetch(`${API_BASE}/api/connections/${connectionId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report_path: report.path,
          parameters: paramValues,
          target_table: targetTable || null
        })
      })
      
      const data = await res.json()
      
      if (!res.ok) {
        throw new Error(data.detail || 'Execution failed')
      }
      
      setResult(data)
      onExecuted()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Play className="text-green-600" size={18} />
        <span className="font-semibold">Execute: {report.name}</span>
      </div>

      {/* Parameters */}
      {loadingParams ? (
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="animate-spin" size={16} />
          Loading parameters...
        </div>
      ) : parameters.length > 0 ? (
        <div className="space-y-3">
          <div className="text-sm font-medium text-gray-700">Parameters</div>
          {parameters.map(param => (
            <div key={param.name} className="flex items-center gap-3">
              <label className="w-40 text-sm text-gray-600">
                {param.display_name}
                {param.required && <span className="text-red-500">*</span>}
              </label>
              <input
                type={param.data_type === 'Date' ? 'date' : 'text'}
                value={paramValues[param.name] || ''}
                onChange={(e) => setParamValues(prev => ({ ...prev, [param.name]: e.target.value }))}
                placeholder={param.default_value || ''}
                className="flex-1 px-3 py-1.5 border rounded-lg text-sm"
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="text-sm text-gray-500">No parameters required</div>
      )}

      {/* Target table */}
      <div className="flex items-center gap-3">
        <label className="w-40 text-sm text-gray-600">Save to table</label>
        <input
          type="text"
          value={targetTable}
          onChange={(e) => setTargetTable(e.target.value)}
          placeholder="pro_report_name"
          className="flex-1 px-3 py-1.5 border rounded-lg text-sm"
        />
      </div>

      {/* Execute button */}
      <button
        onClick={executeReport}
        disabled={loading}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
      >
        {loading ? (
          <>
            <Loader2 className="animate-spin" size={18} />
            Executing...
          </>
        ) : (
          <>
            <Play size={18} />
            Execute Report
          </>
        )}
      </button>

      {/* Error */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center gap-2 text-green-700 font-medium mb-2">
            <CheckCircle size={18} />
            Report Executed Successfully
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="text-gray-600">Rows returned:</div>
            <div className="font-medium">{result.row_count?.toLocaleString()}</div>
            <div className="text-gray-600">Columns:</div>
            <div className="font-medium">{result.columns?.length}</div>
            <div className="text-gray-600">Execution time:</div>
            <div className="font-medium">{result.execution_time_ms}ms</div>
            {result.saved_to_table && (
              <>
                <div className="text-gray-600">Saved to:</div>
                <div className="font-medium font-mono text-xs">{result.saved_to_table}</div>
              </>
            )}
          </div>

          {/* Preview */}
          {result.preview?.length > 0 && (
            <div className="mt-4">
              <div className="text-sm font-medium text-gray-700 mb-2">Preview (first {result.preview.length} rows)</div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead className="bg-gray-100">
                    <tr>
                      {result.columns?.slice(0, 6).map((col, i) => (
                        <th key={i} className="px-2 py-1 text-left font-medium text-gray-600">
                          {col}
                        </th>
                      ))}
                      {result.columns?.length > 6 && (
                        <th className="px-2 py-1 text-gray-400">+{result.columns.length - 6} more</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {result.preview.slice(0, 5).map((row, i) => (
                      <tr key={i} className="border-t">
                        {result.columns?.slice(0, 6).map((col, j) => (
                          <td key={j} className="px-2 py-1 truncate max-w-32">
                            {row[col]}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


// =============================================================================
// NEW CONNECTION MODAL
// =============================================================================

function NewConnectionModal({ projectName, onClose, onCreated }) {
  const [provider, setProvider] = useState('ukg_pro')
  const [connectionName, setConnectionName] = useState('Production')
  const [baseUrl, setBaseUrl] = useState('')
  const [customerApiKey, setCustomerApiKey] = useState('')
  const [webServicesKey, setWebServicesKey] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    try {
      const res = await fetch(`${API_BASE}/api/connections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: projectName,
          provider,
          connection_name: connectionName,
          base_url: baseUrl,
          customer_api_key: customerApiKey,
          web_services_key: webServicesKey,
          username,
          password
        })
      })
      
      const data = await res.json()
      
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create connection')
      }
      
      onCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold">New API Connection</h2>
          <button onClick={onClose} className="p-1 text-gray-500 hover:text-gray-700">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Provider */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'ukg_pro', label: 'UKG Pro', icon: '🏢' },
                { id: 'ukg_wfm', label: 'UKG WFM', icon: '⏰', disabled: true },
                { id: 'ukg_ready', label: 'UKG Ready', icon: '✅', disabled: true },
              ].map(p => (
                <button
                  key={p.id}
                  type="button"
                  disabled={p.disabled}
                  onClick={() => setProvider(p.id)}
                  className={`p-3 border rounded-lg text-center transition-all ${
                    provider === p.id
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : p.disabled
                        ? 'border-gray-200 bg-gray-50 text-gray-400 cursor-not-allowed'
                        : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="text-2xl mb-1">{p.icon}</div>
                  <div className="text-sm font-medium">{p.label}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Connection Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Connection Name</label>
            <input
              type="text"
              value={connectionName}
              onChange={(e) => setConnectionName(e.target.value)}
              placeholder="e.g., Production, Test, Sandbox"
              className="w-full px-3 py-2 border rounded-lg"
              required
            />
          </div>

          {/* Base URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="e.g., customer.ultipro.com"
              className="w-full px-3 py-2 border rounded-lg"
              required
            />
            <p className="text-xs text-gray-500 mt-1">Without https:// prefix</p>
          </div>

          {/* Customer API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Customer API Key</label>
            <input
              type="text"
              value={customerApiKey}
              onChange={(e) => setCustomerApiKey(e.target.value)}
              placeholder="Your UKG Customer API Key"
              className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
              required
            />
          </div>

          {/* Web Services Key (for RaaS) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Web Services Key</label>
            <input
              type="text"
              value={webServicesKey}
              onChange={(e) => setWebServicesKey(e.target.value)}
              placeholder="For Report-as-a-Service access"
              className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">Required for executing reports</p>
          </div>

          {/* Username */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Service account username"
              className="w-full px-3 py-2 border rounded-lg"
              required
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Service account password"
                className="w-full px-3 py-2 border rounded-lg pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin" size={18} />
                  Creating...
                </>
              ) : (
                <>
                  <Check size={18} />
                  Create & Test
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
