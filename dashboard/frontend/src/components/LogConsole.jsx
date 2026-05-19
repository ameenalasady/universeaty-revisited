// dashboard/frontend/src/components/LogConsole.jsx
import React, { useEffect, useState, useRef } from 'react';
import { getLogsStreamUrl } from '../utils/api';

export default function LogConsole() {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState('connecting'); // connecting, streaming, disconnected
  const consoleBodyRef = useRef(null);

  useEffect(() => {
    // Add initial system startup message
    const initialMsg = {
      id: Date.now() + Math.random(),
      text: `[SYSTEM] ${new Date().toISOString().replace('T', ' ').substring(0, 19)} - Opening connection to Server-Sent Events logs stream on Raspberry Pi...`,
      severity: 'info'
    };
    setLogs([initialMsg]);

    const logsUrl = getLogsStreamUrl();
    const source = new EventSource(logsUrl);

    source.onopen = () => {
      setStatus('streaming');
      const connMsg = {
        id: Date.now() + Math.random(),
        text: `[SYSTEM] ${new Date().toISOString().replace('T', ' ').substring(0, 19)} - Server-Sent Events logs stream initialized successfully.`,
        severity: 'info'
      };
      setLogs(prev => [...prev, connMsg]);
    };

    source.onmessage = (event) => {
      const rawLine = event.data;
      if (!rawLine.trim()) return;

      let severity = 'info';
      if (rawLine.includes(' - CRITICAL - ')) {
        severity = 'critical';
      } else if (rawLine.includes(' - ERROR - ')) {
        severity = 'error';
      } else if (rawLine.includes(' - WARNING - ')) {
        severity = 'warning';
      }

      const newLog = {
        id: Date.now() + Math.random(),
        text: rawLine,
        severity
      };

      setLogs(prev => {
        const updated = [...prev, newLog];
        // Capping logs buffer at 1000 lines for low memory footprint
        if (updated.length > 1000) {
          updated.shift();
        }
        return updated;
      });
    };

    source.onerror = () => {
      setStatus('disconnected');
      const errMsg = {
        id: Date.now() + Math.random(),
        text: `[SYSTEM] ${new Date().toISOString().replace('T', ' ').substring(0, 19)} - Stream disconnected. Attempting automatic reconnection...`,
        severity: 'error'
      };
      setLogs(prev => [...prev, errMsg]);
    };

    return () => {
      source.close();
    };
  }, []);

  // Auto-scroll effect
  useEffect(() => {
    if (consoleBodyRef.current) {
      consoleBodyRef.current.scrollTop = consoleBodyRef.current.scrollHeight;
    }
  }, [logs]);

  const severityStyles = {
    info: { borderLeft: '2px solid var(--accent-primary)', color: '#d1d5db' },
    warning: { borderLeft: '2px solid var(--accent-warning)', color: '#fcd34d' },
    error: { borderLeft: '2px solid var(--accent-error)', color: '#fca5a5' },
    critical: { borderLeft: '2px solid var(--accent-error)', color: '#f87171', fontWeight: 'bold', background: 'rgba(239, 68, 68, 0.05)' }
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          Connecting directly to logs stream. Logs are filtered and color-coded dynamically.
        </p>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span style={{
            display: 'inline-block',
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: status === 'streaming' ? 'var(--accent-success)' : status === 'connecting' ? 'var(--accent-warning)' : 'var(--accent-error)',
            boxShadow: status === 'streaming' ? '0 0 8px var(--accent-success)' : status === 'connecting' ? '0 0 8px var(--accent-warning)' : '0 0 8px var(--accent-error)'
          }}></span>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            {status === 'streaming' ? 'Streaming Live' : status === 'connecting' ? 'Connecting' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div className="console-header" style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.75rem 1.25rem',
        background: '#06050b',
        border: '1px solid var(--glass-border)',
        borderBottom: 'none',
        borderRadius: '12px 12px 0 0'
      }}>
        <div style={{ display: 'flex', gap: '6px' }}>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: 'var(--accent-error)' }}></div>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: 'var(--accent-warning)' }}></div>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: 'var(--accent-success)' }}></div>
        </div>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.75rem', color: 'var(--text-dimmed)', textTransform: 'uppercase' }}>
          timetable_checker.log
        </div>
        <div></div>
      </div>
      <div 
        ref={consoleBodyRef}
        className="console-body" 
        style={{
          background: '#030206',
          border: '1px solid var(--glass-border)',
          borderRadius: '0 0 12px 12px',
          padding: '1.25rem',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.85rem',
          height: '480px',
          overflowY: 'auto',
          color: '#d1d5db',
          lineHeight: 1.5,
          boxShadow: 'inset 0 4px 20px rgba(0, 0, 0, 0.8)'
        }}
      >
        {logs.map(log => (
          <div 
            key={log.id} 
            style={{
              marginBottom: '0.4rem',
              whiteSpace: 'pre-wrap',
              paddingLeft: '8px',
              ...severityStyles[log.severity]
            }}
          >
            {log.text}
          </div>
        ))}
      </div>
    </div>
  );
}
