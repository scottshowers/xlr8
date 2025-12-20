/**
 * IntelligenceDemo.jsx - Watch XLR8 Think
 * 
 * Real-time visualization of the intelligence engine processing data.
 * Shows neural network activity, decision stream, and live logging.
 * Route: /intelligence-demo
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { 
  ArrowLeft, Play, RefreshCw, Shield, FileSpreadsheet,
  Zap, GitBranch, CheckCircle, AlertTriangle, Sparkles,
  Target, Brain, Link2
} from 'lucide-react';

const getColors = (dark) => ({
  bg: dark ? '#12151c' : '#f5f6f8',
  card: dark ? '#1e232e' : '#ffffff',
  border: dark ? '#2a2f3a' : '#e4e7ec',
  text: dark ? '#e4e6ea' : '#2d3643',
  textMuted: dark ? '#8b95a5' : '#6b7a8f',
  textLight: dark ? '#5f6a7d' : '#9aa5b5',
  primary: '#83b16d',
  primaryLight: dark ? 'rgba(131, 177, 109, 0.15)' : 'rgba(131, 177, 109, 0.12)',
  primaryDark: '#6a9b5a',
  dustyBlue: '#7889a0',
  dustyBlueLight: dark ? 'rgba(120, 137, 160, 0.15)' : 'rgba(120, 137, 160, 0.12)',
  taupe: '#9b8f82',
  taupeLight: dark ? 'rgba(155, 143, 130, 0.15)' : 'rgba(155, 143, 130, 0.12)',
  amber: '#b5956a',
  amberLight: dark ? 'rgba(181, 149, 106, 0.15)' : 'rgba(181, 149, 106, 0.12)',
});

// Neural Network Canvas
function NeuralNetwork({ colors, isProcessing }) {
  const canvasRef = useRef(null);
  const animationRef = useRef(0);
  const frameRef = useRef(null);
  const connectionsRef = useRef([]);
  const nodesRef = useRef([]);

  const initNodes = useCallback(() => {
    const layers = [
      { name: 'Input', x: 80, count: 5, color: colors.textMuted },
      { name: 'Classify', x: 200, count: 6, color: colors.primary },
      { name: 'Profile', x: 320, count: 6, color: colors.dustyBlue },
      { name: 'Link', x: 440, count: 6, color: colors.taupe },
      { name: 'Output', x: 560, count: 4, color: colors.primary },
    ];

    nodesRef.current = layers.map((layer, li) => ({
      ...layer,
      nodes: Array(layer.count).fill(0).map((_, i) => ({
        x: layer.x,
        y: 50 + (i * 200 / (layer.count - 1 || 1)),
        active: false,
        pulse: 0,
      })),
    }));
  }, [colors]);

  useEffect(() => {
    initNodes();
  }, [initNodes]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const w = canvas.width / 2;
    const h = canvas.height / 2;

    ctx.clearRect(0, 0, w, h);

    // Draw connections
    nodesRef.current.forEach((layer, li) => {
      if (li < nodesRef.current.length - 1) {
        const nextLayer = nodesRef.current[li + 1];
        layer.nodes.forEach((node1, n1) => {
          nextLayer.nodes.forEach((node2, n2) => {
            const isActive = connectionsRef.current.some(c =>
              c.from.layer === li && c.from.node === n1 &&
              c.to.layer === li + 1 && c.to.node === n2
            );

            ctx.beginPath();
            ctx.moveTo(node1.x, node1.y);
            ctx.lineTo(node2.x, node2.y);
            ctx.strokeStyle = isActive ? colors.primary : colors.border;
            ctx.lineWidth = isActive ? 2 : 1;
            ctx.stroke();

            // Pulse along active connections
            if (isActive) {
              const conn = connectionsRef.current.find(c =>
                c.from.layer === li && c.from.node === n1 &&
                c.to.layer === li + 1 && c.to.node === n2
              );
              if (conn) {
                const px = node1.x + (node2.x - node1.x) * conn.progress;
                const py = node1.y + (node2.y - node1.y) * conn.progress;
                ctx.beginPath();
                ctx.arc(px, py, 4, 0, Math.PI * 2);
                ctx.fillStyle = colors.primary;
                ctx.fill();
              }
            }
          });
        });
      }
    });

    // Draw nodes
    nodesRef.current.forEach((layer) => {
      layer.nodes.forEach(node => {
        if (node.active) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, 14 + node.pulse, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(131, 177, 109, ${0.2 - node.pulse * 0.015})`;
          ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(node.x, node.y, 10, 0, Math.PI * 2);
        ctx.fillStyle = node.active ? layer.color : colors.bg;
        ctx.strokeStyle = layer.color;
        ctx.lineWidth = 2;
        ctx.fill();
        ctx.stroke();
      });

      // Layer labels
      ctx.fillStyle = colors.textLight;
      ctx.font = '600 9px Inter';
      ctx.textAlign = 'center';
      ctx.fillText(layer.name.toUpperCase(), layer.x, h - 10);
    });

    // Update animations
    nodesRef.current.forEach(layer => {
      layer.nodes.forEach(node => {
        if (node.active && node.pulse < 10) node.pulse += 0.3;
      });
    });

    connectionsRef.current.forEach(conn => {
      conn.progress += 0.03;
    });
    connectionsRef.current = connectionsRef.current.filter(c => c.progress < 1);

    animationRef.current++;
    frameRef.current = requestAnimationFrame(draw);
  }, [colors]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    const ctx = canvas.getContext('2d');
    ctx.scale(2, 2);

    draw();

    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [draw]);

  // Expose activation method
  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(() => {
        // Activate random path
        nodesRef.current.forEach((layer, li) => {
          setTimeout(() => {
            const nodeIdx = Math.floor(Math.random() * layer.nodes.length);
            layer.nodes[nodeIdx].active = true;
            layer.nodes[nodeIdx].pulse = 0;

            if (li < nodesRef.current.length - 1) {
              const nextNodeIdx = Math.floor(Math.random() * nodesRef.current[li + 1].nodes.length);
              connectionsRef.current.push({
                from: { layer: li, node: nodeIdx },
                to: { layer: li + 1, node: nextNodeIdx },
                progress: 0,
              });
            }
          }, li * 150);
        });
      }, 800);

      return () => clearInterval(interval);
    } else {
      // Reset nodes
      nodesRef.current.forEach(layer => {
        layer.nodes.forEach(node => {
          node.active = false;
          node.pulse = 0;
        });
      });
      connectionsRef.current = [];
    }
  }, [isProcessing]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: '100%',
        height: '100%',
        borderRadius: 12,
        background: colors.bgAlt || colors.bg,
      }}
    />
  );
}

// Decision Item Component
function DecisionItem({ icon: Icon, iconColor, label, detail, confidence, colors }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.75rem',
      background: colors.bg,
      borderRadius: 8,
      marginBottom: '0.5rem',
      animation: 'slideIn 0.3s ease',
    }}>
      <div style={{
        width: 32,
        height: 32,
        borderRadius: 8,
        background: iconColor + '20',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <Icon size={16} style={{ color: iconColor }} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: colors.text }}>{label}</div>
        <div style={{ fontSize: '0.7rem', color: colors.textMuted }}>{detail}</div>
      </div>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '0.7rem',
        fontWeight: 600,
        color: colors.primary,
      }}>
        {confidence}%
      </div>
    </div>
  );
}

// Log Entry Component
function LogEntry({ time, message, type, colors }) {
  const typeColors = {
    success: colors.primary,
    info: colors.dustyBlue,
    warning: colors.amber,
    default: colors.textMuted,
  };

  return (
    <div style={{
      display: 'flex',
      gap: '0.75rem',
      padding: '0.4rem 0',
      borderBottom: `1px solid ${colors.bg}`,
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '0.7rem',
      animation: 'fadeIn 0.2s ease',
    }}>
      <span style={{ color: colors.textLight, flexShrink: 0 }}>{time}</span>
      <span style={{ color: typeColors[type] || typeColors.default }}>{message}</span>
    </div>
  );
}

export default function IntelligenceDemo() {
  const navigate = useNavigate();
  const { darkMode } = useTheme();
  const colors = getColors(darkMode);

  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressStage, setProgressStage] = useState('Ready');
  const [stats, setStats] = useState({ rows: 0, columns: 0, patterns: 0, issues: 0 });
  const [decisions, setDecisions] = useState([]);
  const [logs, setLogs] = useState([{ time: '--:--:--', message: 'System ready', type: 'default' }]);

  const addLog = (message, type = 'info') => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    setLogs(prev => [{ time, message, type }, ...prev.slice(0, 19)]);
  };

  const addDecision = (icon, iconColor, label, detail, confidence) => {
    setDecisions(prev => [{ icon, iconColor, label, detail, confidence }, ...prev.slice(0, 5)]);
  };

  const startAnalysis = async () => {
    if (isProcessing) return;

    setIsProcessing(true);
    setProgress(0);
    setDecisions([]);
    setStats({ rows: 0, columns: 0, patterns: 0, issues: 0 });

    const stages = [
      { name: 'Reading file structure', percent: 10, logs: ['Parsing Excel workbook...', 'Found 3 sheets'], stats: { rows: 2400, columns: 8 } },
      { name: 'Analyzing columns', percent: 25, logs: ['Detecting column types...', 'Profiling distributions'], stats: { rows: 5800, columns: 18 } },
      { name: 'Classifying document', percent: 40, logs: ['Running content analysis...', 'Matching Truth patterns'], stats: { rows: 8200, columns: 26 }, decision: { icon: Target, color: colors.primary, label: 'Classified as Reality', detail: 'Employee master data detected', conf: 94 } },
      { name: 'Profiling data quality', percent: 60, logs: ['Checking completeness...', 'Validating formats', 'Detecting anomalies'], stats: { rows: 10500, columns: 32 }, decision: { icon: CheckCircle, color: colors.dustyBlue, label: 'Quality Score: 87%', detail: '4 issues in SSN column', conf: 87 } },
      { name: 'Detecting relationships', percent: 75, logs: ['Scanning foreign keys...', 'Building relationship graph'], stats: { rows: 11800, columns: 34, patterns: 3 }, decision: { icon: Link2, color: colors.taupe, label: '3 Relationships Found', detail: 'Links to Dept, Location, PayGroup', conf: 91 } },
      { name: 'Learning patterns', percent: 90, logs: ['Caching query patterns...', 'Updating embeddings'], stats: { patterns: 8, issues: 2 }, decision: { icon: Brain, color: colors.primary, label: '12 Patterns Cached', detail: 'Common queries saved for reuse', conf: 98 } },
      { name: 'Generating insights', percent: 100, logs: ['Analysis complete!'], stats: { patterns: 12, issues: 4 }, decision: { icon: Sparkles, color: colors.amber, label: 'Insight Generated', detail: 'Duplicate SSN in rows 847, 1203', conf: 99 } },
    ];

    for (const stage of stages) {
      setProgressStage(stage.name);
      setProgress(stage.percent);

      for (const log of stage.logs) {
        addLog(log, stage.percent === 100 ? 'success' : 'info');
        await new Promise(r => setTimeout(r, 300));
      }

      if (stage.stats) {
        setStats(prev => ({
          rows: stage.stats.rows ?? prev.rows,
          columns: stage.stats.columns ?? prev.columns,
          patterns: stage.stats.patterns ?? prev.patterns,
          issues: stage.stats.issues ?? prev.issues,
        }));
      }

      if (stage.decision) {
        const d = stage.decision;
        addDecision(d.icon, d.color, d.label, d.detail, d.conf);
      }

      await new Promise(r => setTimeout(r, 800));
    }

    setIsProcessing(false);
    setProgressStage('Complete');
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: colors.bg,
      fontFamily: "'Inter', system-ui, sans-serif",
      padding: '1.5rem',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={() => navigate(-1)}
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              border: `1px solid ${colors.border}`,
              background: colors.card,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: colors.textMuted,
            }}
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '1.25rem',
              fontWeight: 800,
              color: colors.text,
              margin: 0,
            }}>
              Watch <span style={{ color: colors.primary }}>XLR8</span> Think
            </h1>
            <p style={{ fontSize: '0.8rem', color: colors.textMuted, margin: 0 }}>
              Real-time intelligence visualization
            </p>
          </div>
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 1rem',
          background: isProcessing ? colors.primaryLight : colors.bg,
          borderRadius: 20,
          border: `1px solid ${isProcessing ? colors.primary : colors.border}`,
        }}>
          <div style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: isProcessing ? colors.primary : colors.textLight,
            animation: isProcessing ? 'pulse 1.5s infinite' : 'none',
          }} />
          <span style={{
            fontSize: '0.8rem',
            fontWeight: 600,
            color: isProcessing ? colors.primary : colors.textMuted,
          }}>
            {isProcessing ? 'Processing' : 'Ready'}
          </span>
        </div>
      </div>

      {/* Stats Row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        {[
          { label: 'Rows Analyzed', value: stats.rows },
          { label: 'Columns Profiled', value: stats.columns },
          { label: 'Patterns Found', value: stats.patterns },
          { label: 'Issues Detected', value: stats.issues },
        ].map((stat, i) => (
          <div key={i} style={{
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 12,
            padding: '1.25rem',
            textAlign: 'center',
          }}>
            <div style={{
              fontFamily: "'Sora', sans-serif",
              fontSize: '1.75rem',
              fontWeight: 800,
              color: colors.primary,
            }}>
              {stat.value.toLocaleString()}
            </div>
            <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginTop: '0.25rem' }}>
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 340px',
        gap: '1.5rem',
      }}>
        {/* Neural Network */}
        <div style={{
          background: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: 16,
          padding: '1.25rem',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
          }}>
            <div>
              <div style={{ fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: '0.9rem', color: colors.text }}>
                Intelligence Network
              </div>
              <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>
                Processing pathways and connections
              </div>
            </div>
          </div>
          <div style={{ height: 320 }}>
            <NeuralNetwork colors={colors} isProcessing={isProcessing} />
          </div>
        </div>

        {/* Side Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* File + Trigger */}
          <div style={{
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 12,
            padding: '1rem',
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
              padding: '0.75rem',
              background: colors.bg,
              borderRadius: 8,
              marginBottom: '1rem',
            }}>
              <div style={{
                width: 40,
                height: 40,
                borderRadius: 8,
                background: colors.card,
                border: `1px solid ${colors.border}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <FileSpreadsheet size={20} style={{ color: colors.primary }} />
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: colors.text }}>Employee_Master.xlsx</div>
                <div style={{ fontSize: '0.7rem', color: colors.textMuted }}>12,847 rows • 34 columns</div>
              </div>
            </div>

            <button
              onClick={startAnalysis}
              disabled={isProcessing}
              style={{
                width: '100%',
                padding: '0.875rem',
                background: isProcessing ? colors.bg : colors.primary,
                color: isProcessing ? colors.textMuted : 'white',
                border: 'none',
                borderRadius: 10,
                fontFamily: "'Sora', sans-serif",
                fontSize: '0.9rem',
                fontWeight: 700,
                cursor: isProcessing ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
              }}
            >
              {isProcessing ? (
                <>
                  <RefreshCw size={16} style={{ animation: 'spin 1s linear infinite' }} />
                  Analyzing...
                </>
              ) : progress === 100 ? (
                <>
                  <CheckCircle size={16} />
                  Run Again
                </>
              ) : (
                <>
                  <Play size={16} />
                  Start Analysis
                </>
              )}
            </button>

            {/* Progress */}
            {isProcessing && (
              <div style={{ marginTop: '1rem' }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '0.7rem',
                  marginBottom: '0.4rem',
                }}>
                  <span style={{ color: colors.textMuted }}>{progressStage}</span>
                  <span style={{ color: colors.primary, fontWeight: 600 }}>{progress}%</span>
                </div>
                <div style={{
                  height: 5,
                  background: colors.bg,
                  borderRadius: 3,
                  overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%',
                    width: `${progress}%`,
                    background: `linear-gradient(90deg, ${colors.primary}, ${colors.dustyBlue})`,
                    borderRadius: 3,
                    transition: 'width 0.3s ease',
                  }} />
                </div>
              </div>
            )}
          </div>

          {/* Decisions */}
          <div style={{
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 12,
            padding: '1rem',
            flex: 1,
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '0.75rem',
            }}>
              <div style={{ fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: '0.85rem', color: colors.text }}>
                🧠 Decision Stream
              </div>
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '0.6rem',
                padding: '0.2rem 0.4rem',
                background: colors.bg,
                borderRadius: 4,
                color: colors.textMuted,
              }}>
                LIVE
              </span>
            </div>
            <div style={{ maxHeight: 200, overflow: 'auto' }}>
              {decisions.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: colors.textLight, fontSize: '0.8rem' }}>
                  Waiting for analysis...
                </div>
              ) : (
                decisions.map((d, i) => (
                  <DecisionItem
                    key={i}
                    icon={d.icon}
                    iconColor={d.iconColor}
                    label={d.label}
                    detail={d.detail}
                    confidence={d.confidence}
                    colors={colors}
                  />
                ))
              )}
            </div>
          </div>

          {/* Logs */}
          <div style={{
            background: colors.card,
            border: `1px solid ${colors.border}`,
            borderRadius: 12,
            padding: '1rem',
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '0.5rem',
            }}>
              <div style={{ fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: '0.85rem', color: colors.text }}>
                📋 Activity Log
              </div>
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '0.6rem',
                padding: '0.2rem 0.4rem',
                background: colors.bg,
                borderRadius: 4,
                color: colors.textMuted,
              }}>
                {logs.length} events
              </span>
            </div>
            <div style={{ maxHeight: 120, overflow: 'auto' }}>
              {logs.map((log, i) => (
                <LogEntry key={i} time={log.time} message={log.message} type={log.type} colors={colors} />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Security Footer */}
      <div style={{
        marginTop: '1.5rem',
        padding: '1rem 1.25rem',
        background: colors.card,
        border: `1px solid ${colors.border}`,
        borderRadius: 12,
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
      }}>
        <Shield size={18} style={{ color: colors.primary }} />
        <span style={{ fontSize: '0.8rem', color: colors.textMuted }}>
          <strong style={{ color: colors.text }}>100% Local Processing</strong> — 
          All AI runs on local LLMs. Your data never leaves your environment. No public APIs. No external exposure.
        </span>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-10px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
