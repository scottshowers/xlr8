/**
 * useProgressStream - Real-time progress updates via SSE
 * 
 * Usage:
 *   const { progress, chunks, isComplete, error } = useProgressStream(jobId);
 * 
 * Returns live updates as PDF chunks are processed in parallel.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export function useProgressStream(jobId) {
  const [progress, setProgress] = useState({
    percent: 0,
    status: 'pending',
    currentStep: '',
  });
  const [chunks, setChunks] = useState({
    total: 0,
    done: 0,
    rowsSoFar: 0,
  });
  const [chunkUpdates, setChunkUpdates] = useState([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  
  const eventSourceRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 3;

  const connect = useCallback(() => {
    if (!jobId) return;
    
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const url = `${API_BASE}/api/progress/stream/${jobId}`;
    console.log('[SSE] Connecting to:', url);
    
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('[SSE] Connected');
      reconnectAttempts.current = 0;
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Update progress
        setProgress({
          percent: data.progress_percent || 0,
          status: data.status || 'processing',
          currentStep: data.current_step || '',
        });

        // Update chunk info
        if (data.chunks) {
          setChunks({
            total: data.chunks.total || 0,
            done: data.chunks.done || 0,
            rowsSoFar: data.chunks.rows_so_far || 0,
          });
        }

        // Append chunk updates
        if (data.chunk_updates && data.chunk_updates.length > 0) {
          setChunkUpdates(prev => [...prev, ...data.chunk_updates]);
        }

        // Check for completion
        if (data.final) {
          setIsComplete(true);
          if (data.result) {
            setResult(data.result);
          }
          if (data.error) {
            setError(data.error);
          }
          eventSource.close();
        }

        // Check for timeout
        if (data.timeout) {
          setError(data.message || 'Connection timed out');
          eventSource.close();
        }

      } catch (e) {
        console.error('[SSE] Parse error:', e);
      }
    };

    eventSource.onerror = (err) => {
      console.error('[SSE] Error:', err);
      eventSource.close();
      
      // Try to reconnect
      if (reconnectAttempts.current < maxReconnectAttempts && !isComplete) {
        reconnectAttempts.current++;
        console.log(`[SSE] Reconnecting (attempt ${reconnectAttempts.current})...`);
        setTimeout(connect, 2000 * reconnectAttempts.current);
      } else {
        setError('Connection lost');
      }
    };

    return () => {
      eventSource.close();
    };
  }, [jobId, isComplete]);

  // Connect when jobId changes
  useEffect(() => {
    if (jobId) {
      // Reset state
      setProgress({ percent: 0, status: 'pending', currentStep: '' });
      setChunks({ total: 0, done: 0, rowsSoFar: 0 });
      setChunkUpdates([]);
      setIsComplete(false);
      setError(null);
      setResult(null);
      
      connect();
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [jobId, connect]);

  // Fallback to polling if SSE fails
  useEffect(() => {
    if (error && !isComplete && jobId) {
      console.log('[SSE] Falling back to polling');
      
      const pollInterval = setInterval(async () => {
        try {
          const response = await fetch(`${API_BASE}/api/progress/${jobId}`);
          if (response.ok) {
            const data = await response.json();
            
            setProgress({
              percent: data.progress_percent || 0,
              status: data.status || 'processing',
              currentStep: data.current_step || '',
            });

            if (data.chunks) {
              setChunks({
                total: data.chunks.total || 0,
                done: data.chunks.done || 0,
                rowsSoFar: data.chunks.rows_so_far || 0,
              });
            }

            if (data.status === 'completed' || data.status === 'failed') {
              setIsComplete(true);
              setResult(data.result);
              if (data.error) setError(data.error);
              clearInterval(pollInterval);
            }
          }
        } catch (e) {
          console.error('[POLL] Error:', e);
        }
      }, 2000);

      return () => clearInterval(pollInterval);
    }
  }, [error, isComplete, jobId]);

  return {
    progress,
    chunks,
    chunkUpdates,
    isComplete,
    error,
    result,
    // Computed helpers
    isProcessing: progress.status === 'processing' || progress.status === 'pending',
    hasChunks: chunks.total > 0,
    chunkPercent: chunks.total > 0 ? Math.round((chunks.done / chunks.total) * 100) : 0,
  };
}

export default useProgressStream;
