/**
 * DataModelPage - Visual ERD for table relationships
 * 
 * Features:
 * - Draggable table boxes showing columns
 * - Visual connections between related columns
 * - Blue lines = key relationships (JOINs)
 * - Orange lines = semantic mappings
 * - Claude suggestions highlighted, drag to connect/remove
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useProject } from '../context/ProjectContext';
import api from '../services/api';

// Colors
const COLORS = {
  keyLine: '#3b82f6',      // Blue - key relationships
  semanticLine: '#f59e0b', // Orange - semantic mappings
  needsReview: '#ef4444',  // Red - needs review
  tableHeader: '#1e293b',
  tableBg: '#ffffff',
  tableBorder: '#e2e8f0',
  columnHover: '#f1f5f9',
  canvas: '#f8fafc',
};

const SEMANTIC_TYPES = [
  { id: 'employee_number', label: 'Employee Number', category: 'keys' },
  { id: 'company_code', label: 'Company Code', category: 'keys' },
  { id: 'employment_status_code', label: 'Employment Status', category: 'status' },
  { id: 'earning_code', label: 'Earning Code', category: 'codes' },
  { id: 'deduction_code', label: 'Deduction Code', category: 'codes' },
  { id: 'job_code', label: 'Job Code', category: 'codes' },
  { id: 'department_code', label: 'Department Code', category: 'codes' },
  { id: 'amount', label: 'Amount', category: 'values' },
  { id: 'rate', label: 'Rate', category: 'values' },
  { id: 'effective_date', label: 'Effective Date', category: 'dates' },
  { id: 'start_date', label: 'Start Date', category: 'dates' },
  { id: 'end_date', label: 'End Date', category: 'dates' },
  { id: 'employee_name', label: 'Employee Name', category: 'other' },
];

export default function DataModelPage() {
  const { activeProject } = useProject();
  const canvasRef = useRef(null);
  const [tables, setTables] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [mappings, setMappings] = useState([]);
  const [tablePositions, setTablePositions] = useState({});
  const [loading, setLoading] = useState(true);
  const [draggingTable, setDraggingTable] = useState(null);
  const [draggingLine, setDraggingLine] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [selectedConnection, setSelectedConnection] = useState(null);
  const [message, setMessage] = useState(null);
  const [pendingChanges, setPendingChanges] = useState([]);

  // Fetch data
  useEffect(() => {
    if (!activeProject?.name) return;
    fetchData();
  }, [activeProject?.name]);

  const fetchData = async () => {
    if (!activeProject?.name) return;
    setLoading(true);
    try {
      // Get structured data (tables)
      const structuredRes = await api.get('/status/structured');
      const projectTables = (structuredRes.data?.files || [])
        .filter(f => f.project === activeProject.name)
        .flatMap(f => (f.sheets || []).map(s => ({
          ...s,
          file: f.filename,
          fullTableName: `${activeProject.name.toLowerCase()}__${f.filename.toLowerCase().replace(/[^a-z0-9]/g, '_')}__${s.sheet_name.toLowerCase().replace(/[^a-z0-9]/g, '_')}`
        })));
      setTables(projectTables);

      // Initialize positions in a grid
      const positions = {};
      const cols = Math.ceil(Math.sqrt(projectTables.length));
      projectTables.forEach((t, i) => {
        const col = i % cols;
        const row = Math.floor(i / cols);
        positions[t.table_name] = {
          x: 50 + col * 320,
          y: 50 + row * 280
        };
      });
      setTablePositions(positions);

      // Get relationships
      try {
        const relRes = await api.get(`/status/relationships/${encodeURIComponent(activeProject.name)}`);
        setRelationships(relRes.data?.relationships || []);
      } catch (e) {
        console.warn('No relationships endpoint or error:', e);
        setRelationships([]);
      }

      // Get mappings
      try {
        const mapRes = await api.get(`/status/mappings/${encodeURIComponent(activeProject.name)}`);
        setMappings(mapRes.data?.mappings || []);
      } catch (e) {
        console.warn('No mappings:', e);
        setMappings([]);
      }

    } catch (err) {
      console.error('Failed to fetch data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Get column position for line drawing
  const getColumnPosition = useCallback((tableName, columnName, side = 'right') => {
    const tablePos = tablePositions[tableName];
    if (!tablePos) return null;

    const table = tables.find(t => t.table_name === tableName);
    if (!table) return null;

    const columns = table.columns || [];
    const colIndex = columns.findIndex(c => 
      (typeof c === 'string' ? c : c.name) === columnName
    );
    if (colIndex === -1) return null;

    const x = side === 'right' ? tablePos.x + 280 : tablePos.x;
    const y = tablePos.y + 40 + (colIndex * 24) + 12; // header + column offset

    return { x, y };
  }, [tablePositions, tables]);

  // Handle table drag
  const handleTableMouseDown = (e, tableName) => {
    if (e.target.closest('.column-row')) return; // Don't drag when clicking columns
    const rect = canvasRef.current.getBoundingClientRect();
    const pos = tablePositions[tableName];
    setDraggingTable(tableName);
    setDragOffset({
      x: e.clientX - rect.left - pos.x,
      y: e.clientY - rect.top - pos.y
    });
  };

  // Handle column drag (create connection)
  const handleColumnMouseDown = (e, tableName, columnName) => {
    e.stopPropagation();
    const rect = canvasRef.current.getBoundingClientRect();
    const startPos = getColumnPosition(tableName, columnName, 'right');
    if (!startPos) return;

    setDraggingLine({
      sourceTable: tableName,
      sourceColumn: columnName,
      startX: startPos.x,
      startY: startPos.y,
      endX: e.clientX - rect.left,
      endY: e.clientY - rect.top
    });
  };

  const handleMouseMove = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (draggingTable) {
      setTablePositions(prev => ({
        ...prev,
        [draggingTable]: {
          x: x - dragOffset.x,
          y: y - dragOffset.y
        }
      }));
    } else if (draggingLine) {
      setDraggingLine(prev => ({
        ...prev,
        endX: x,
        endY: y
      }));
    }
  };

  const handleMouseUp = (e) => {
    if (draggingLine) {
      // Check if dropped on a column
      const target = e.target.closest('.column-row');
      if (target) {
        const targetTable = target.dataset.table;
        const targetColumn = target.dataset.column;
        
        if (targetTable && targetColumn && 
            (targetTable !== draggingLine.sourceTable || targetColumn !== draggingLine.sourceColumn)) {
          // Create new relationship
          createRelationship(
            draggingLine.sourceTable,
            draggingLine.sourceColumn,
            targetTable,
            targetColumn
          );
        }
      }
    }
    setDraggingTable(null);
    setDraggingLine(null);
  };

  const createRelationship = async (sourceTable, sourceColumn, targetTable, targetColumn) => {
    // Add to pending changes
    const newRel = {
      id: `pending_${Date.now()}`,
      source_table: sourceTable,
      source_columns: [sourceColumn],
      target_table: targetTable,
      target_columns: [targetColumn],
      type: 'key',
      isPending: true
    };
    
    setRelationships(prev => [...prev, newRel]);
    setPendingChanges(prev => [...prev, { action: 'add', data: newRel }]);
    showMessage(`Connected ${sourceColumn} → ${targetColumn}`);
  };

  const removeRelationship = (rel) => {
    setRelationships(prev => prev.filter(r => r !== rel));
    if (!rel.isPending) {
      setPendingChanges(prev => [...prev, { action: 'remove', data: rel }]);
    } else {
      setPendingChanges(prev => prev.filter(p => p.data.id !== rel.id));
    }
    setSelectedConnection(null);
    showMessage('Connection removed');
  };

  const saveChanges = async () => {
    // TODO: Implement API call to save relationships
    try {
      for (const change of pendingChanges) {
        if (change.action === 'add') {
          await api.post(`/status/relationships/${encodeURIComponent(activeProject.name)}`, {
            source_table: change.data.source_table,
            source_columns: change.data.source_columns,
            target_table: change.data.target_table,
            target_columns: change.data.target_columns
          });
        } else if (change.action === 'remove') {
          await api.delete(`/status/relationships/${encodeURIComponent(activeProject.name)}`, {
            data: {
              source_table: change.data.source_table,
              target_table: change.data.target_table
            }
          });
        }
      }
      setPendingChanges([]);
      // Mark all as saved
      setRelationships(prev => prev.map(r => ({ ...r, isPending: false })));
      showMessage('Changes saved!', 'success');
      fetchData(); // Refresh
    } catch (err) {
      showMessage('Failed to save: ' + err.message, 'error');
    }
  };

  const showMessage = (text, type = 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  // Get mapping for a column
  const getColumnMapping = (tableName, columnName) => {
    return mappings.find(m => 
      m.table_name === tableName && m.original_column === columnName
    );
  };

  // Render connection lines
  const renderConnections = () => {
    const lines = [];

    // Render relationships (blue)
    relationships.forEach((rel, idx) => {
      const sourceCol = rel.source_columns?.[0];
      const targetCol = rel.target_columns?.[0];
      if (!sourceCol || !targetCol) return;

      const start = getColumnPosition(rel.source_table, sourceCol, 'right');
      const end = getColumnPosition(rel.target_table, targetCol, 'left');
      if (!start || !end) return;

      const isSelected = selectedConnection === rel;
      const midX = (start.x + end.x) / 2;

      lines.push(
        <g key={`rel-${idx}`} onClick={() => setSelectedConnection(isSelected ? null : rel)} style={{ cursor: 'pointer' }}>
          <path
            d={`M ${start.x} ${start.y} C ${midX} ${start.y}, ${midX} ${end.y}, ${end.x} ${end.y}`}
            fill="none"
            stroke={rel.isPending ? '#22c55e' : COLORS.keyLine}
            strokeWidth={isSelected ? 3 : 2}
            strokeDasharray={rel.isPending ? '5,5' : 'none'}
          />
          {isSelected && (
            <circle cx={midX} cy={(start.y + end.y) / 2} r={10} fill="#ef4444" onClick={(e) => { e.stopPropagation(); removeRelationship(rel); }} />
          )}
        </g>
      );
    });

    // Render dragging line
    if (draggingLine) {
      const midX = (draggingLine.startX + draggingLine.endX) / 2;
      lines.push(
        <path
          key="dragging"
          d={`M ${draggingLine.startX} ${draggingLine.startY} C ${midX} ${draggingLine.startY}, ${midX} ${draggingLine.endY}, ${draggingLine.endX} ${draggingLine.endY}`}
          fill="none"
          stroke={COLORS.keyLine}
          strokeWidth={2}
          strokeDasharray="5,5"
          opacity={0.6}
        />
      );
    }

    return lines;
  };

  // Render a table box
  const renderTable = (table) => {
    const pos = tablePositions[table.table_name] || { x: 0, y: 0 };
    const columns = table.columns || [];
    const displayColumns = columns.slice(0, 12); // Limit displayed columns
    const hasMore = columns.length > 12;

    return (
      <div
        key={table.table_name}
        style={{
          position: 'absolute',
          left: pos.x,
          top: pos.y,
          width: 280,
          background: COLORS.tableBg,
          border: `2px solid ${COLORS.tableBorder}`,
          borderRadius: 8,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          cursor: draggingTable === table.table_name ? 'grabbing' : 'grab',
          userSelect: 'none',
          zIndex: draggingTable === table.table_name ? 100 : 1
        }}
        onMouseDown={(e) => handleTableMouseDown(e, table.table_name)}
      >
        {/* Header */}
        <div style={{
          background: COLORS.tableHeader,
          color: 'white',
          padding: '8px 12px',
          borderRadius: '6px 6px 0 0',
          fontSize: '0.85rem',
          fontWeight: 600
        }}>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginBottom: 2 }}>{table.file}</div>
          {table.sheet_name}
        </div>

        {/* Columns */}
        <div style={{ maxHeight: 300, overflowY: 'auto' }}>
          {displayColumns.map((col, idx) => {
            const colName = typeof col === 'string' ? col : col.name;
            const mapping = getColumnMapping(table.table_name, colName);
            
            return (
              <div
                key={idx}
                className="column-row"
                data-table={table.table_name}
                data-column={colName}
                style={{
                  padding: '4px 12px',
                  fontSize: '0.75rem',
                  borderBottom: '1px solid #f1f5f9',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  cursor: 'crosshair',
                  background: mapping?.needs_review ? '#fef3c7' : 'transparent'
                }}
                onMouseDown={(e) => handleColumnMouseDown(e, table.table_name, colName)}
              >
                <span style={{ 
                  color: mapping ? COLORS.semanticLine : '#475569',
                  fontWeight: mapping ? 600 : 400
                }}>
                  {colName}
                </span>
                {mapping && (
                  <span style={{ 
                    fontSize: '0.65rem', 
                    color: mapping.needs_review ? COLORS.needsReview : COLORS.semanticLine,
                    background: mapping.needs_review ? '#fef3c7' : '#fef3c7',
                    padding: '1px 4px',
                    borderRadius: 3
                  }}>
                    {mapping.semantic_type}
                  </span>
                )}
              </div>
            );
          })}
          {hasMore && (
            <div style={{ padding: '4px 12px', fontSize: '0.7rem', color: '#94a3b8', fontStyle: 'italic' }}>
              +{columns.length - 12} more columns
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '6px 12px',
          fontSize: '0.7rem',
          color: '#64748b',
          borderTop: '1px solid #e2e8f0',
          background: '#f8fafc',
          borderRadius: '0 0 6px 6px'
        }}>
          {table.row_count?.toLocaleString() || 0} rows
        </div>
      </div>
    );
  };

  if (!activeProject) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
        Please select a project first.
      </div>
    );
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#f1f5f9' }}>
      {/* Header */}
      <div style={{
        padding: '1rem 1.5rem',
        background: 'white',
        borderBottom: '1px solid #e2e8f0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#1e293b', margin: 0 }}>
            Data Model
          </h1>
          <p style={{ fontSize: '0.85rem', color: '#64748b', margin: '4px 0 0 0' }}>
            {activeProject.name} • {tables.length} tables • Drag columns to connect
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {pendingChanges.length > 0 && (
            <>
              <span style={{ fontSize: '0.85rem', color: '#f59e0b' }}>
                {pendingChanges.length} unsaved changes
              </span>
              <button
                onClick={saveChanges}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: 6,
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                💾 Save Changes
              </button>
            </>
          )}
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem' }}>
            <span><span style={{ display: 'inline-block', width: 12, height: 3, background: COLORS.keyLine, marginRight: 4 }}></span> Key Relationship</span>
            <span><span style={{ display: 'inline-block', width: 12, height: 12, background: '#fef3c7', marginRight: 4, borderRadius: 2 }}></span> Semantic Mapping</span>
          </div>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div style={{
          position: 'absolute',
          top: 80,
          left: '50%',
          transform: 'translateX(-50%)',
          padding: '0.75rem 1.5rem',
          background: message.type === 'error' ? '#fee2e2' : message.type === 'success' ? '#dcfce7' : '#e0f2fe',
          color: message.type === 'error' ? '#991b1b' : message.type === 'success' ? '#166534' : '#1e40af',
          borderRadius: 8,
          zIndex: 1000,
          fontWeight: 500
        }}>
          {message.text}
        </div>
      )}

      {/* Canvas */}
      {loading ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <p>Loading data model...</p>
        </div>
      ) : tables.length === 0 ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
          <p style={{ color: '#64748b', marginBottom: '1rem' }}>No tables found in this project.</p>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Upload data files to see them here.</p>
        </div>
      ) : (
        <div
          ref={canvasRef}
          style={{
            flex: 1,
            position: 'relative',
            overflow: 'auto',
            background: COLORS.canvas
          }}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {/* SVG for lines */}
          <svg
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none',
              zIndex: 0
            }}
          >
            <g style={{ pointerEvents: 'auto' }}>
              {renderConnections()}
            </g>
          </svg>

          {/* Table boxes */}
          {tables.map(renderTable)}
        </div>
      )}
    </div>
  );
}
